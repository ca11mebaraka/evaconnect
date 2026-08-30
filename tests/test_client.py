from __future__ import annotations

import httpx
import pytest

from evaconnect.auth import TokenStore
from evaconnect.client import EvoluteClient, looks_like_car_id
from evaconnect.constants import APP_VERSION, HEADER_ACCESS_TOKEN, default_headers
from evaconnect.errors import EvoluteAuthError
from evaconnect.models import Telemetry

from tests.fakes import (
    FAKE_ACCESS,
    FAKE_ACCESS_2,
    FAKE_CAR_ID,
    FAKE_IMEI,
    FAKE_PHONE,
    FAKE_REFRESH,
    FAKE_REFRESH_2,
    FAKE_USER_ID,
    FAKE_VIN,
    telemetry_payload,
    trip_row,
    vehicle_row,
)


def test_app_version_constant() -> None:
    assert APP_VERSION == "5.1.22 (740)"
    assert default_headers()["x-app-version"] == APP_VERSION
    assert "authorization" not in {k.lower() for k in default_headers()}


def test_looks_like_car_id() -> None:
    assert looks_like_car_id(FAKE_CAR_ID)
    assert not looks_like_car_id(FAKE_IMEI)


def test_get_info_without_token(mocked_api) -> None:
    route = mocked_api.get("/id-service/info").mock(
        return_value=httpx.Response(
            200,
            json={
                "capcha": False,
                "enableChat": True,
                "android": {"minRequiredVersion": "5.0.0"},
                "ios": {"minRequiredVersion": "5.0.0"},
            },
        )
    )
    store = TokenStore(path=None)
    with EvoluteClient(token_store=store, min_telemetry_interval=0) as client:
        info = client.get_info()
    assert info.capcha is False
    assert info.android is not None
    assert info.android["minRequiredVersion"] == "5.0.0"
    sent = route.calls.last.request
    assert HEADER_ACCESS_TOKEN not in sent.headers
    assert sent.headers["x-app-version"] == APP_VERSION
    assert sent.headers["x-device"] == "android"


def test_request_otp_uses_capcha_typo(mocked_api) -> None:
    route = mocked_api.post("/id-service/auth/sign-up").mock(
        return_value=httpx.Response(201, content=b"")
    )
    store = TokenStore(path=None)
    with EvoluteClient(token_store=store) as client:
        client.request_otp(FAKE_PHONE, "RU", capcha_token="")
    body = route.calls.last.request.content.decode()
    assert "capchaToken" in body
    assert "captchaToken" not in body
    assert "phoneCountry" in body


def test_sign_in_persists_tokens(mocked_api, creds_path) -> None:
    mocked_api.post("/id-service/auth/sign-in").mock(
        return_value=httpx.Response(
            200,
            json={
                "userId": FAKE_USER_ID,
                "accessToken": FAKE_ACCESS,
                "refreshToken": FAKE_REFRESH,
                "userToken": "user-token",
                "widgetId": "widget-1",
            },
        )
    )
    store = TokenStore(creds_path)
    with EvoluteClient(token_store=store) as client:
        tokens = client.sign_in(FAKE_PHONE, "000000")
    assert tokens.access_token == FAKE_ACCESS
    reloaded = TokenStore(creds_path)
    reloaded.load()
    assert reloaded.access_token == FAKE_ACCESS
    assert reloaded.refresh_token == FAKE_REFRESH
    assert creds_path.stat().st_mode & 0o777 == 0o600


def test_refresh_rotates_and_persists(mocked_api, client, creds_path) -> None:
    route = mocked_api.post("/id-service/auth/refresh-token").mock(
        return_value=httpx.Response(
            200,
            json={
                "userId": FAKE_USER_ID,
                "accessToken": FAKE_ACCESS_2,
                "refreshToken": FAKE_REFRESH_2,
                "userToken": "user-token-2",
                "widgetId": "widget-2",
            },
        )
    )
    tokens = client.refresh()
    assert tokens.access_token == FAKE_ACCESS_2
    assert tokens.refresh_token == FAKE_REFRESH_2
    body = route.calls.last.request.content.decode()
    assert FAKE_REFRESH in body
    assert HEADER_ACCESS_TOKEN not in route.calls.last.request.headers
    reloaded = TokenStore(creds_path)
    reloaded.load()
    assert reloaded.access_token == FAKE_ACCESS_2
    assert reloaded.refresh_token == FAKE_REFRESH_2


def test_list_vehicles(mocked_api, client) -> None:
    mocked_api.post("/car-service/car/v2/search").mock(
        return_value=httpx.Response(
            200,
            json={"rows": [vehicle_row()], "total": 1, "offset": 0, "limit": 20},
        )
    )
    vehicles = client.list_vehicles()
    assert len(vehicles) == 1
    car = vehicles[0]
    assert car.id == FAKE_CAR_ID
    assert car.imei == FAKE_IMEI
    assert car.plate == "TEST-000"
    assert car.model == "i-PRO"
    text = repr(car)
    assert FAKE_IMEI not in text
    assert FAKE_VIN not in text
    assert "Vehicle(" in text


def test_get_vehicle(mocked_api, client) -> None:
    mocked_api.get(f"/car-service/car/v2/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json=vehicle_row())
    )
    car = client.get_vehicle(FAKE_CAR_ID)
    assert car.id == FAKE_CAR_ID
    assert car.imei == FAKE_IMEI


def test_telemetry_coerces_string_sensors(mocked_api, client) -> None:
    mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        return_value=httpx.Response(200, json=telemetry_payload())
    )
    tel = client.get_telemetry(imei=FAKE_IMEI)
    assert tel.sensors["batteryPercentage"] == 64
    assert tel.sensors["batteryTemp"] == 21.5
    assert tel.sensors["isChargingGunInserted"] is False
    assert tel.sensors["isCentralLockingOn"] is True
    assert tel.sensors_raw["batteryPercentage"] == "64"
    assert tel.is_online is True


def test_telemetry_resolves_car_id(mocked_api, client) -> None:
    mocked_api.get(f"/car-service/car/v2/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json=vehicle_row())
    )
    mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        return_value=httpx.Response(200, json=telemetry_payload())
    )
    tel = client.get_telemetry(FAKE_CAR_ID)
    assert tel.sensors["batteryPercentage"] == 64


def test_telemetry_positional_imei_skips_vehicle_lookup(mocked_api, client) -> None:
    mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        return_value=httpx.Response(200, json=telemetry_payload())
    )
    tel = client.get_telemetry(FAKE_IMEI)
    assert isinstance(tel, Telemetry)


def test_auto_refresh_on_401_once(mocked_api, client) -> None:
    tel_route = mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        side_effect=[
            httpx.Response(401, json={"error": "expired"}),
            httpx.Response(200, json=telemetry_payload()),
        ]
    )
    mocked_api.post("/id-service/auth/refresh-token").mock(
        return_value=httpx.Response(
            200,
            json={
                "userId": FAKE_USER_ID,
                "accessToken": FAKE_ACCESS_2,
                "refreshToken": FAKE_REFRESH_2,
                "userToken": "u",
                "widgetId": "w",
            },
        )
    )
    tel = client.get_telemetry(imei=FAKE_IMEI)
    assert tel.sensors["batteryPercentage"] == 64
    assert tel_route.call_count == 2
    assert client.tokens.access_token == FAKE_ACCESS_2
    assert tel_route.calls.last.request.headers[HEADER_ACCESS_TOKEN] == FAKE_ACCESS_2


def test_refresh_without_token_raises() -> None:
    store = TokenStore(path=None)
    with EvoluteClient(token_store=store) as client:
        with pytest.raises(EvoluteAuthError):
            client.refresh()


def test_refresh_401_is_auth_error(mocked_api, client) -> None:
    mocked_api.post("/id-service/auth/refresh-token").mock(
        return_value=httpx.Response(401, json={"error": "rejected"})
    )
    with pytest.raises(EvoluteAuthError, match="replace credentials.json"):
        client.refresh()


def test_charge_session_empty(mocked_api, client) -> None:
    mocked_api.get("/charge-service/session/v2/current").mock(
        return_value=httpx.Response(200, content=b"")
    )
    assert client.get_charge_session() is None


def test_charge_session_404_is_empty(mocked_api, client) -> None:
    mocked_api.get("/charge-service/session/v2/current").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    assert client.get_charge_session() is None


def test_charge_session_present(mocked_api, client) -> None:
    mocked_api.get("/charge-service/session/v2/current").mock(
        return_value=httpx.Response(200, json={"status": "charging", "power": 7})
    )
    session = client.get_charge_session()
    assert session is not None
    assert session.model_dump()["status"] == "charging"


def test_list_trips_uses_confirmed_sort(mocked_api, client) -> None:
    route = mocked_api.post(f"/car-service/travels/search/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(
            200,
            json={"rows": [trip_row()], "total": 1, "offset": 0, "limit": 20},
        )
    )
    page = client.list_trips(FAKE_CAR_ID, limit=5, offset=0)
    assert page.rows[0].id == 101
    assert page.rows[0].distance == 8500
    body = route.calls.last.request.content.decode()
    assert '"by":"DATE"' in body.replace(" ", "")
    assert '"dir":"DESC"' in body.replace(" ", "")


def test_list_trips_sort_is_parameterized(mocked_api, client) -> None:
    route = mocked_api.post(f"/car-service/travels/search/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json={"rows": [], "total": 0})
    )
    client.list_trips(FAKE_CAR_ID, sort_by="endDate", sort_dir="asc")
    body = route.calls.last.request.content.decode()
    assert "endDate" in body
    assert "asc" in body


def test_get_trip_requires_start_time_query(mocked_api, client) -> None:
    details = {**trip_row(), "startAddr": "A", "endAddr": "B", "pointsTotal": 2, "points": []}
    route = mocked_api.get(f"/car-service/travels/details/{FAKE_CAR_ID}/101").mock(
        return_value=httpx.Response(200, json=details)
    )
    trip = client.get_trip(FAKE_CAR_ID, 101, 1_700_000_100)
    assert trip.id == 101
    assert trip.start_addr == "A"
    assert route.calls.last.request.url.params["startTime"] == "1700000100"


def test_me(mocked_api, client) -> None:
    mocked_api.get("/id-service/user").mock(
        return_value=httpx.Response(200, json={"_id": FAKE_USER_ID, "phone": FAKE_PHONE})
    )
    user = client.me()
    assert user.id == FAKE_USER_ID
    assert "0000000000" not in repr(user)


def test_send_command_not_implemented(client) -> None:
    with pytest.raises(NotImplementedError, match="unconfirmed"):
        client.send_command("climateOn")


def test_get_flags_omits_access_token(mocked_api, client) -> None:
    route = mocked_api.get("/config-service/config/flags").mock(
        return_value=httpx.Response(200, json={"flags": {"newTelemetryEnabled": True}})
    )
    flags = client.get_flags(brand="Evolute", vin="TESTVIN0000000001")
    assert flags.flags["newTelemetryEnabled"] is True
    assert HEADER_ACCESS_TOKEN not in route.calls.last.request.headers
