"""Contract tests for the provisioned Grafana dashboard JSON."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "deploy" / "grafana" / "dashboards" / "evolute.json"
SCHEMA = ROOT / "sql" / "schema.sql"

OVERVIEW_PANELS = (
    "Battery",
    "Remaining range (API units, unconverted)",
    "Temperatures",
    "12V battery",
    "Online",
    "Central lock",
    "Odometer (raw)",
    "Poller heartbeat",
    "Recent trips (no addresses)",
)

ROWS = (
    "Обзор",
    "Сейчас",
    "Зарядка",
    "Климат",
    "Кузов: двери, багажник, свет, замок",
    "Движение",
    "Служебные сенсоры API (не в колонках)",
    "Поездки",
    "Poller",
)


def test_dashboard_identity_and_datasource() -> None:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    assert data["uid"] == "evaconnect-evolute"
    assert data["title"] == "Evolute"
    assert data["timezone"] == "Europe/Moscow"
    titles = [p["title"] for p in data["panels"]]
    for name in OVERVIEW_PANELS:
        assert name in titles
    for name in ROWS:
        assert name in titles
    for panel in data["panels"]:
        ds = panel.get("datasource") or {}
        if ds:
            assert ds.get("uid") == "evaconnect-pg"


def test_overview_trips_sql_is_msk_from_start_date() -> None:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    trips = next(p for p in data["panels"] if p["title"] == "Recent trips (no addresses)")
    sql = trips["targets"][0]["rawSql"]
    assert "Europe/Moscow" in sql
    assert "start_date" in sql
    assert "end_date" in sql
    assert "description" not in sql.lower()


def test_body_panels_read_raw_sensors_not_geo() -> None:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    doors = next(p for p in data["panels"] if p["title"] == "Кузов во времени (0/1)")
    sql = doors["targets"][0]["rawSql"]
    assert "doorFLStatus" in sql
    assert "trunkStatus" in sql
    assert "lat" not in sql
    assert "lon" not in sql


def test_dashboard_sql_uses_schema_columns() -> None:
    schema = SCHEMA.read_text(encoding="utf-8")
    for col in (
        "battery_pct",
        "range_km",
        "voltage_12v",
        "battery_first",
        "battery_last",
        "duration_ms",
    ):
        assert col in schema
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    sql_blob = " ".join(
        t.get("rawSql", "")
        for p in data["panels"]
        for t in p.get("targets") or []
    )
    assert "battery_pct" in sql_blob
    assert "battery_first" in sql_blob
    assert "collector_heartbeats" in sql_blob
