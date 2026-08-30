from __future__ import annotations

from evaconnect.models import Telemetry, TripDetails, Vehicle
from evaconnect.redact import (
    drop_geo,
    mask_imei,
    mask_phone,
    mask_vin,
    public_status,
    public_trip_details,
    public_trip_summary,
    public_vehicle,
)

from tests.fakes import FAKE_CAR_ID, FAKE_IMEI, FAKE_VIN, telemetry_payload, trip_row, vehicle_row


def test_masks() -> None:
    assert mask_imei(FAKE_IMEI).endswith("0000")
    assert FAKE_IMEI not in (mask_imei(FAKE_IMEI) or "")
    assert mask_vin(FAKE_VIN).endswith("0001")
    assert mask_phone("0000000000") == "********00"


def test_drop_geo() -> None:
    sensors = drop_geo({"batteryPercentage": 64, "lat": 1.0, "lon": 2.0, "course": 90})
    assert "lat" not in sensors
    assert "lon" not in sensors
    assert sensors["batteryPercentage"] == 64


def test_public_vehicle_masks_identifiers() -> None:
    car = Vehicle.model_validate(vehicle_row())
    public = public_vehicle(car, include_pii=False)
    assert public["id"] == FAKE_CAR_ID
    assert public["imei"] != FAKE_IMEI
    assert public["vin"] != FAKE_VIN
    raw = public_vehicle(car, include_pii=True)
    assert raw["imei"] == FAKE_IMEI


def test_public_status_hides_geo() -> None:
    tel = Telemetry.model_validate(telemetry_payload())
    public = public_status(tel, include_pii=False)
    blob = str(public)
    assert "55.000000" not in blob
    assert "37.000000" not in blob
    assert public["charge"]["battery_percentage"] == 64
    assert public["climate"]["inside"] == 19


def test_public_trip_hides_addresses_and_track() -> None:
    details = TripDetails.model_validate(
        {
            **trip_row(),
            "startAddr": "secret-start",
            "endAddr": "secret-end",
            "pointsTotal": 2,
            "points": [{"lat": 1.0, "lon": 2.0, "time": 1}],
        }
    )
    summary = public_trip_summary(details, include_pii=False)
    assert "description" not in summary
    hidden = public_trip_details(details, include_pii=False, include_track=False)
    assert "start_addr" not in hidden
    assert "points" not in hidden
    tracked = public_trip_details(details, include_pii=False, include_track=True)
    assert tracked["points"][0]["lat"] == 1.0
    shown = public_trip_details(details, include_pii=True, include_track=False)
    assert shown["start_addr"] == "secret-start"
