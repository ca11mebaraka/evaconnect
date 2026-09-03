from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest

from evaconnect.constants import MIN_TELEMETRY_INTERVAL_S
from evaconnect.models import Telemetry, TripSummary
from evaconnect.poller import poll_once, run_loop, telemetry_row, trip_row
from evaconnect.redact import public_status

from tests.fakes import FAKE_CAR_ID, FAKE_IMEI, telemetry_payload, trip_row as fake_trip, vehicle_row


class FakeConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def execute(self, sql: str, params: object = None):
        self.calls.append((sql, params))
        return self

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def test_telemetry_row_drops_geo() -> None:
    tel = Telemetry.model_validate(telemetry_payload())
    ts = datetime(2026, 8, 30, tzinfo=timezone.utc)
    row = telemetry_row(FAKE_CAR_ID, tel, ts)
    assert row["battery_pct"] == 64
    assert row["range_km"] == 212
    assert row["locked"] is True
    assert row["online"] is True
    blob = json.dumps(row["raw"])
    assert "lat" not in blob
    assert "lon" not in blob
    assert "55.000000" not in blob
    status = public_status(tel, include_pii=False)
    assert "lat" not in json.dumps(status)


def test_trip_row_omits_description() -> None:
    trip = TripSummary.model_validate(fake_trip())
    row = trip_row(FAKE_CAR_ID, trip)
    assert row["travel_id"] == 101
    assert row["distance"] == 8500
    assert row["odo_first"] == 1000
    assert row["odo_last"] == 1008
    assert row["battery_first"] == 80
    assert row["battery_last"] == 74
    assert "description" not in row
    assert "redacted-address-placeholder" not in json.dumps(row)


def test_poll_once_writes_telemetry_and_trips(mocked_api, client) -> None:
    mocked_api.get(f"/car-service/car/v2/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json=vehicle_row())
    )
    mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        return_value=httpx.Response(200, json=telemetry_payload())
    )
    mocked_api.post(f"/car-service/travels/search/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json={"rows": [fake_trip()], "total": 1})
    )
    mocked_api.get("/charge-service/session/v2/current").mock(
        return_value=httpx.Response(404, json={})
    )
    conn = FakeConn()
    poll_once(client, conn, include_trips=True)  # type: ignore[arg-type]
    sql = " ".join(sql for sql, _ in conn.calls)
    assert "INSERT INTO telemetry" in sql
    assert "INSERT INTO trips" in sql
    tel_params = next(params for sql, params in conn.calls if "INSERT INTO telemetry" in sql)
    assert tel_params["car_id"] == FAKE_CAR_ID
    assert tel_params["battery_pct"] == 64


def test_run_loop_rejects_fast_poll() -> None:
    with pytest.raises(ValueError, match="telemetry interval"):
        run_loop(
            database_url="postgresql://unused",
            telemetry_interval=MIN_TELEMETRY_INTERVAL_S - 1,
        )
