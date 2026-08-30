"""Pydantic models for the Evolute companion API.

Sensor values often arrive as strings; we coerce to numbers where possible
and keep the raw map. VIN/IMEI/phone/tokens never appear in ``__repr__``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def coerce_sensor_value(value: Any) -> Any:
    """Parse sensor scalars that the API sends as strings."""
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text == "":
        return value
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return value


def _car_model_name(car_model: Any) -> str | None:
    if car_model is None:
        return None
    if isinstance(car_model, str):
        return car_model
    if isinstance(car_model, dict):
        for key in ("name", "title", "model", "modification"):
            found = car_model.get(key)
            if found:
                return str(found)
    return None


class AuthTokens(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    user_id: str | None = Field(default=None, alias="userId")
    access_token: str | None = Field(default=None, alias="accessToken")
    refresh_token: str | None = Field(default=None, alias="refreshToken")
    user_token: str | None = Field(default=None, alias="userToken")
    widget_id: str | None = Field(default=None, alias="widgetId")

    def __repr__(self) -> str:
        return (
            f"AuthTokens(user_id={self.user_id!r}, "
            f"has_access={bool(self.access_token)}, "
            f"has_refresh={bool(self.refresh_token)})"
        )


class ServiceInfo(BaseModel):
    """GET /id-service/info. API typo is ``capcha``, not captcha."""

    model_config = ConfigDict(extra="allow")

    capcha: bool | None = None
    enable_chat: bool | None = Field(default=None, alias="enableChat")
    yandex_api_key: str | None = Field(default=None, alias="yandexApiKey")
    ios: dict[str, Any] | None = None
    android: dict[str, Any] | None = None


class User(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    phone: str | None = None
    user_groups_ids: list[Any] | None = Field(default=None, alias="userGroupsIds")
    push_tokens: list[Any] | None = Field(default=None, alias="pushTokens")

    def __repr__(self) -> str:
        return f"User(id={self.id!r})"


class CarModelOptions(BaseModel):
    model_config = ConfigDict(extra="allow")

    heater: bool | None = None
    ready_mode: bool | None = Field(default=None, alias="readyMode")
    hidden_key: bool | None = Field(default=None, alias="hiddenKey")
    can_disable_location: bool | None = Field(default=None, alias="canDisableLocation")
    mim: bool | None = None


class Vehicle(BaseModel):
    """Two identifiers: ``id`` (mongo ``_id``) for REST/trips, ``imei`` for telemetry."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(alias="_id")
    vin: str | None = None
    imei: str | None = None
    plate: str | None = Field(default=None, alias="licensePlate")
    brand: str | None = None
    car_model: Any = Field(default=None, alias="carModel")
    options: CarModelOptions | None = None
    location_status: Any = Field(default=None, alias="locationStatus")
    available_script_time: Any = Field(default=None, alias="availableScriptTime")
    current_script_time: Any = Field(default=None, alias="currentScriptTime")

    @model_validator(mode="before")
    @classmethod
    def _lift_options(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        car_model = data.get("carModel")
        if data.get("options") is None and isinstance(car_model, dict):
            opts = car_model.get("options")
            if opts is not None:
                data["options"] = opts
        return data

    @property
    def model(self) -> str | None:
        return _car_model_name(self.car_model)

    def __repr__(self) -> str:
        return (
            f"Vehicle(id={self.id!r}, plate={self.plate!r}, "
            f"brand={self.brand!r}, model={self.model!r})"
        )


class VehiclePage(BaseModel):
    model_config = ConfigDict(extra="allow")

    rows: list[Vehicle] = Field(default_factory=list)
    total: int | None = None
    offset: int | None = None
    limit: int | None = None


class TelemetryButton(BaseModel):
    """Read-only command catalog. Names are not a send API."""

    model_config = ConfigDict(extra="allow")

    title: str | None = None
    status: Any = None
    enabled: bool | None = None
    activate_command: str | None = Field(default=None, alias="activateCommand")
    deactivate_command: str | None = Field(default=None, alias="deactivateCommand")
    run_on_schedule: Any = Field(default=None, alias="runOnSchedule")


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sensors_raw: dict[str, Any] = Field(default_factory=dict)
    sensors: dict[str, Any] = Field(default_factory=dict)
    buttons: list[TelemetryButton] = Field(default_factory=list)
    is_online: bool | None = Field(default=None, alias="isOnline")
    online_state: Any = Field(default=None, alias="onlineState")
    is_car_state_ready: bool | None = Field(default=None, alias="isCarStateReady")
    car_state_updated_at: Any = Field(default=None, alias="carStateUpdatedAt")
    automations: Any = None
    warnings: Any = None
    firmware_check: Any = Field(default=None, alias="firmwareCheck")
    settings_check: Any = Field(default=None, alias="settingsCheck")

    @model_validator(mode="before")
    @classmethod
    def _coerce_sensors(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        raw = data.get("sensors_raw")
        incoming = data.get("sensors")
        if raw is None:
            raw = incoming if isinstance(incoming, dict) else {}
            data["sensors_raw"] = dict(raw)
        if not isinstance(raw, dict):
            raw = {}
            data["sensors_raw"] = {}
        # Always expose a coerced map; keep incoming raw untouched.
        if incoming is None or incoming is raw or incoming == raw:
            data["sensors"] = {key: coerce_sensor_value(val) for key, val in raw.items()}
        elif isinstance(incoming, dict) and "sensors_raw" in data:
            # Caller supplied both; still coerce the public map if values look raw.
            data["sensors"] = {key: coerce_sensor_value(val) for key, val in incoming.items()}
        return data


class ChargeSession(BaseModel):
    """Shape of a non-empty session is not fully specified; keep extras."""

    model_config = ConfigDict(extra="allow")


class FirstLast(BaseModel):
    model_config = ConfigDict(extra="allow")

    first: int | None = None
    last: int | None = None

    @field_validator("first", "last", mode="before")
    @classmethod
    def _int_or_none(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None


class TripSummary(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: int
    segment_start_time: int | None = Field(default=None, alias="segmentStartTime")
    segment_end_time: int | None = Field(default=None, alias="segmentEndTime")
    start_date: int | None = Field(default=None, alias="startDate")
    end_date: int | None = Field(default=None, alias="endDate")
    title: str | None = None
    description: str | None = None
    duration: str | None = None
    distance: int | None = None  # units unknown (m vs km); expose raw
    battery_consumption: int | None = Field(default=None, alias="batteryConsumption")
    odometer: FirstLast | None = None
    battery: FirstLast | None = None
    fuel: FirstLast | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _travel_id_int(cls, value: Any) -> int:
        return int(value)

    @field_validator("distance", "battery_consumption", mode="before")
    @classmethod
    def _raw_int(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)


class TripPoint(BaseModel):
    model_config = ConfigDict(extra="allow")

    lat: float | None = None
    lon: float | None = None
    time: Any = None


class TripDetails(TripSummary):
    start_addr: str | None = Field(default=None, alias="startAddr")
    end_addr: str | None = Field(default=None, alias="endAddr")
    points_total: int | None = Field(default=None, alias="pointsTotal")
    points: list[TripPoint] = Field(default_factory=list)


class TripPage(BaseModel):
    model_config = ConfigDict(extra="allow")

    rows: list[TripSummary] = Field(default_factory=list)
    total: int | None = None
    offset: int | None = None
    limit: int | None = None
    filters: Any = None


class TripFilter(BaseModel):
    model_config = ConfigDict(extra="allow")

    key: str | None = None
    type: str | None = None
    options: list[Any] = Field(default_factory=list)
    name: str | None = None


class FeatureFlags(BaseModel):
    model_config = ConfigDict(extra="allow")

    flags: dict[str, Any] = Field(default_factory=dict)
