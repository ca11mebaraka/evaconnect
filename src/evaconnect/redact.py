"""Redact PII before MCP/CLI output or logs.

Never log tokens, cookies, full VIN, IMEI, exact lat/lon, or phone.
"""

from __future__ import annotations

from typing import Any

GEO_SENSOR_KEYS = frozenset({"lat", "lon", "course"})
TOKEN_KEYS = frozenset(
    {
        "accessToken",
        "refreshToken",
        "userToken",
        "access_token",
        "refresh_token",
        "user_token",
        "capchaToken",
        "cookie",
    }
)
IDENTIFIER_KEYS = frozenset({"vin", "imei", "phone", "licensePlate"})


def mask_tail(value: str | None, *, keep: int = 4) -> str | None:
    if value is None:
        return None
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]


def mask_vin(vin: str | None) -> str | None:
    return mask_tail(vin, keep=4)


def mask_imei(imei: str | None) -> str | None:
    return mask_tail(imei, keep=4)


def mask_phone(phone: str | None) -> str | None:
    return mask_tail(phone, keep=2)


def drop_geo(sensors: dict[str, Any]) -> dict[str, Any]:
    return {key: val for key, val in sensors.items() if key not in GEO_SENSOR_KEYS}


def redact_mapping(data: dict[str, Any], *, include_pii: bool = False) -> dict[str, Any]:
    """Shallow-plus nested redact of common secret / PII keys."""
    out: dict[str, Any] = {}
    for key, val in data.items():
        if key in TOKEN_KEYS:
            out[key] = "***" if val else None
            continue
        if not include_pii and key in GEO_SENSOR_KEYS:
            continue
        if not include_pii and key in IDENTIFIER_KEYS and isinstance(val, str):
            if key == "vin":
                out[key] = mask_vin(val)
            elif key == "imei":
                out[key] = mask_imei(val)
            elif key == "phone":
                out[key] = mask_phone(val)
            else:
                out[key] = mask_tail(val)
            continue
        if isinstance(val, dict):
            out[key] = redact_mapping(val, include_pii=include_pii)
        elif isinstance(val, list):
            out[key] = [
                redact_mapping(item, include_pii=include_pii) if isinstance(item, dict) else item
                for item in val
            ]
        else:
            out[key] = val
    return out


def public_vehicle(vehicle: Any, *, include_pii: bool = False) -> dict[str, Any]:
    payload = {
        "id": getattr(vehicle, "id", None),
        "plate": getattr(vehicle, "plate", None),
        "brand": getattr(vehicle, "brand", None),
        "model": getattr(vehicle, "model", None),
    }
    if include_pii:
        payload["vin"] = getattr(vehicle, "vin", None)
        payload["imei"] = getattr(vehicle, "imei", None)
    else:
        payload["vin"] = mask_vin(getattr(vehicle, "vin", None))
        payload["imei"] = mask_imei(getattr(vehicle, "imei", None))
    return payload


def public_trip_summary(trip: Any, *, include_pii: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": getattr(trip, "id", None),
        "segment_start_time": getattr(trip, "segment_start_time", None),
        "segment_end_time": getattr(trip, "segment_end_time", None),
        "start_date": getattr(trip, "start_date", None),
        "end_date": getattr(trip, "end_date", None),
        "duration": getattr(trip, "duration", None),
        "distance": getattr(trip, "distance", None),
        "battery_consumption": getattr(trip, "battery_consumption", None),
        "odometer": _first_last(getattr(trip, "odometer", None)),
        "battery": _first_last(getattr(trip, "battery", None)),
        "fuel": _first_last(getattr(trip, "fuel", None)),
        "title": getattr(trip, "title", None),
    }
    if include_pii:
        payload["description"] = getattr(trip, "description", None)
    return payload


def public_trip_details(
    trip: Any, *, include_pii: bool = False, include_track: bool = False
) -> dict[str, Any]:
    payload = public_trip_summary(trip, include_pii=include_pii)
    payload["points_total"] = getattr(trip, "points_total", None)
    if include_pii:
        payload["start_addr"] = getattr(trip, "start_addr", None)
        payload["end_addr"] = getattr(trip, "end_addr", None)
    if include_track:
        points = getattr(trip, "points", None) or []
        payload["points"] = [
            {"lat": getattr(p, "lat", None), "lon": getattr(p, "lon", None), "time": getattr(p, "time", None)}
            for p in points
        ]
    return payload


def public_status(telemetry: Any, *, include_pii: bool = False) -> dict[str, Any]:
    sensors = dict(getattr(telemetry, "sensors", None) or {})
    if not include_pii:
        sensors = drop_geo(sensors)
    buttons = getattr(telemetry, "buttons", None) or []
    return {
        "online": getattr(telemetry, "is_online", None),
        "online_state": getattr(telemetry, "online_state", None),
        "car_state_updated_at": getattr(telemetry, "car_state_updated_at", None),
        "charge": {
            "battery_percentage": sensors.get("batteryPercentage"),
            "range": sensors.get("remainsBatteryMileage"),
            "charging_gun": sensors.get("isChargingGunInserted"),
            "battery_temp": sensors.get("batteryTemp"),
            "voltage_12v": sensors.get("12VBatteryVoltage"),
        },
        "climate": {
            "target": sensors.get("climateTargetTemp"),
            "fan": sensors.get("climateFanSpeed"),
            "inside": sensors.get("inBoardTemp"),
            "outside": sensors.get("outsideTemp"),
            "coolant": sensors.get("coolantTemp"),
        },
        "body": {
            "locked": sensors.get("isCentralLockingOn"),
            "door_fl": sensors.get("doorFLStatus"),
            "door_fr": sensors.get("doorFRStatus"),
            "door_rl": sensors.get("doorRLStatus"),
            "door_rr": sensors.get("doorRRStatus"),
            "trunk": sensors.get("trunkStatus"),
            "headlights": sensors.get("headLightsStatus"),
        },
        "drive": {
            "ignition": sensors.get("isIgnitionOn"),
            "parked": sensors.get("isParkedOn"),
            "odometer": sensors.get("odometer"),
            "signal": sensors.get("signalLevel"),
        },
        "buttons": [
            {
                "title": getattr(b, "title", None),
                "status": getattr(b, "status", None),
                "enabled": getattr(b, "enabled", None),
            }
            for b in buttons
        ],
        "warnings": getattr(telemetry, "warnings", None),
    }


def _first_last(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return {"first": getattr(value, "first", None), "last": getattr(value, "last", None)}
