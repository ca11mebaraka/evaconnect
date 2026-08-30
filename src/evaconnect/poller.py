"""Scheduled Evolute poller: write telemetry and trips into Postgres for Grafana."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Json

from evaconnect.auth import TokenStore, default_credentials_path
from evaconnect.client import EvoluteClient
from evaconnect.constants import MIN_TELEMETRY_INTERVAL_S
from evaconnect.errors import EvoluteError
from evaconnect.models import Telemetry, TripSummary
from evaconnect.redact import drop_geo, public_status

log = logging.getLogger("evaconnect.poller")

DEFAULT_TELEMETRY_INTERVAL_S = 30.0
DEFAULT_TRIPS_INTERVAL_S = 900.0
DEFAULT_TRIP_LIMIT = 20


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


def telemetry_row(car_id: str, telemetry: Telemetry, ts: datetime) -> dict[str, Any]:
    """Map a redacted status snapshot onto the ``telemetry`` table."""
    status = public_status(telemetry, include_pii=False)
    charge = status.get("charge") or {}
    climate = status.get("climate") or {}
    body = status.get("body") or {}
    drive = status.get("drive") or {}
    sensors = drop_geo(dict(telemetry.sensors or {}))
    return {
        "ts": ts,
        "car_id": car_id,
        "online": status.get("online"),
        "online_state": status.get("online_state"),
        "battery_pct": _float(charge.get("battery_percentage")),
        "range_km": _float(charge.get("range")),
        "charging_gun": _bool(charge.get("charging_gun")),
        "battery_temp": _float(charge.get("battery_temp")),
        "voltage_12v": _float(charge.get("voltage_12v")),
        "climate_target": _float(climate.get("target")),
        "climate_fan": _float(climate.get("fan")),
        "temp_inside": _float(climate.get("inside")),
        "temp_outside": _float(climate.get("outside")),
        "coolant_temp": _float(climate.get("coolant")),
        "locked": _bool(body.get("locked")),
        "ignition": _bool(drive.get("ignition")),
        "parked": _bool(drive.get("parked")),
        "odometer": _float(drive.get("odometer")),
        "signal_level": _float(drive.get("signal")),
        "raw": {"status": status, "sensors": sensors},
    }


def trip_row(car_id: str, trip: TripSummary) -> dict[str, Any]:
    odo = trip.odometer
    batt = trip.battery
    return {
        "car_id": car_id,
        "travel_id": trip.id,
        "segment_start_time": trip.segment_start_time,
        "segment_end_time": trip.segment_end_time,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "duration": trip.duration,
        "distance": trip.distance,
        "battery_consumption": trip.battery_consumption,
        "odo_first": None if odo is None else odo.first,
        "odo_last": None if odo is None else odo.last,
        "battery_first": None if batt is None else batt.first,
        "battery_last": None if batt is None else batt.last,
        "title": trip.title,
    }


def schema_sql() -> str:
    override = os.environ.get("SCHEMA_PATH")
    if override:
        return Path(override).read_text(encoding="utf-8")
    packaged = files("evaconnect").joinpath("schema.sql")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    repo = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"
    return repo.read_text(encoding="utf-8")


def apply_schema(conn: psycopg.Connection) -> None:
    for statement in schema_sql().split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)
    conn.commit()


def insert_telemetry(conn: psycopg.Connection, row: dict[str, Any]) -> None:
    payload = dict(row)
    payload["raw"] = Json(payload["raw"])
    conn.execute(
        """
        INSERT INTO telemetry (
            ts, car_id, online, online_state, battery_pct, range_km, charging_gun,
            battery_temp, voltage_12v, climate_target, climate_fan, temp_inside,
            temp_outside, coolant_temp, locked, ignition, parked, odometer,
            signal_level, raw
        ) VALUES (
            %(ts)s, %(car_id)s, %(online)s, %(online_state)s, %(battery_pct)s,
            %(range_km)s, %(charging_gun)s, %(battery_temp)s, %(voltage_12v)s,
            %(climate_target)s, %(climate_fan)s, %(temp_inside)s, %(temp_outside)s,
            %(coolant_temp)s, %(locked)s, %(ignition)s, %(parked)s, %(odometer)s,
            %(signal_level)s, %(raw)s
        )
        """,
        payload,
    )


def upsert_trip(conn: psycopg.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO trips (
            car_id, travel_id, segment_start_time, segment_end_time, start_date,
            end_date, duration, distance, battery_consumption, odo_first, odo_last,
            battery_first, battery_last, title
        ) VALUES (
            %(car_id)s, %(travel_id)s, %(segment_start_time)s, %(segment_end_time)s,
            %(start_date)s, %(end_date)s, %(duration)s, %(distance)s,
            %(battery_consumption)s, %(odo_first)s, %(odo_last)s, %(battery_first)s,
            %(battery_last)s, %(title)s
        )
        ON CONFLICT (car_id, travel_id, segment_start_time) DO UPDATE SET
            segment_end_time = EXCLUDED.segment_end_time,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            duration = EXCLUDED.duration,
            distance = EXCLUDED.distance,
            battery_consumption = EXCLUDED.battery_consumption,
            odo_first = EXCLUDED.odo_first,
            odo_last = EXCLUDED.odo_last,
            battery_first = EXCLUDED.battery_first,
            battery_last = EXCLUDED.battery_last,
            title = EXCLUDED.title
        """,
        row,
    )


def insert_heartbeat(
    conn: psycopg.Connection,
    *,
    ok: bool,
    error: str | None,
    duration_ms: int,
    ts: datetime | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO collector_heartbeats (ts, ok, error, duration_ms)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (ts) DO UPDATE SET
            ok = EXCLUDED.ok,
            error = EXCLUDED.error,
            duration_ms = EXCLUDED.duration_ms
        """,
        (ts or datetime.now(timezone.utc), ok, error, duration_ms),
    )


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def poll_once(
    client: EvoluteClient,
    conn: psycopg.Connection,
    *,
    include_trips: bool,
    trip_limit: int = DEFAULT_TRIP_LIMIT,
    now: datetime | None = None,
) -> None:
    ts = now or datetime.now(timezone.utc)
    car_id = client.default_car_id()
    telemetry = client.get_telemetry(car_id=car_id)
    insert_telemetry(conn, telemetry_row(car_id, telemetry, ts))
    if include_trips:
        page = client.list_trips(car_id, limit=trip_limit)
        for trip in page.rows:
            upsert_trip(conn, trip_row(car_id, trip))
    # Charge is sampled via telemetry.charging_gun; 404 must not fail the cycle.
    client.get_charge_session()


def run_loop(
    *,
    database_url: str,
    telemetry_interval: float = DEFAULT_TELEMETRY_INTERVAL_S,
    trips_interval: float = DEFAULT_TRIPS_INTERVAL_S,
    trip_limit: int = DEFAULT_TRIP_LIMIT,
    sleep_fn: Any = time.sleep,
) -> None:
    if telemetry_interval < MIN_TELEMETRY_INTERVAL_S:
        raise ValueError(
            f"telemetry interval must be >= {MIN_TELEMETRY_INTERVAL_S} seconds"
        )
    trip_every = max(1, int(trips_interval // telemetry_interval))
    creds = default_credentials_path()
    store = TokenStore.from_env_or_file(creds)
    cycle = 0
    with (
        EvoluteClient(token_store=store) as client,
        psycopg.connect(database_url) as conn,
    ):
        apply_schema(conn)
        log.info("poller started; telemetry every %ss; trips every %s cycles", telemetry_interval, trip_every)
        while True:
            started = time.monotonic()
            ok = False
            error: str | None = None
            try:
                poll_once(
                    client,
                    conn,
                    include_trips=(cycle % trip_every == 0),
                    trip_limit=trip_limit,
                )
                ok = True
            except EvoluteError as exc:
                error = f"{type(exc).__name__}: {exc}"
                log.warning("poll cycle failed: %s", error)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                log.exception("poll cycle failed")
            duration_ms = int((time.monotonic() - started) * 1000)
            try:
                insert_heartbeat(conn, ok=ok, error=error, duration_ms=duration_ms)
                conn.commit()
            except Exception:
                conn.rollback()
                log.exception("failed to persist heartbeat")
            cycle += 1
            sleep_fn(telemetry_interval)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    run_loop(
        database_url=database_url,
        telemetry_interval=_env_float("POLL_TELEMETRY_INTERVAL_S", DEFAULT_TELEMETRY_INTERVAL_S),
        trips_interval=_env_float("POLL_TRIPS_INTERVAL_S", DEFAULT_TRIPS_INTERVAL_S),
        trip_limit=_env_int("POLL_TRIP_LIMIT", DEFAULT_TRIP_LIMIT),
    )


if __name__ == "__main__":
    main()
