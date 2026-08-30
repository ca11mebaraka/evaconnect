"""Typed HTTP client for https://app.evassist.ru (own account / own vehicle)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from evaconnect.auth import TokenStore
from evaconnect.constants import (
    BASE_URL,
    DEFAULT_PAGE_LIMIT,
    DEFAULT_TRIP_SORT_BY,
    DEFAULT_TRIP_SORT_DIR,
    HEADER_ACCESS_TOKEN,
    MIN_TELEMETRY_INTERVAL_S,
    MONGO_ID_LEN,
    default_headers,
)
from evaconnect.errors import EvoluteAPIError, EvoluteAuthError
from evaconnect.models import (
    AuthTokens,
    ChargeSession,
    FeatureFlags,
    ServiceInfo,
    Telemetry,
    TripDetails,
    TripFilter,
    TripPage,
    User,
    Vehicle,
    VehiclePage,
)

log = logging.getLogger("evaconnect.client")

_MONGO_ID = re.compile(rf"^[0-9a-fA-F]{{{MONGO_ID_LEN}}}$")


def looks_like_car_id(value: str) -> bool:
    """Mongo ``_id`` is 24 hex chars. IMEI is a different identifier."""
    return bool(_MONGO_ID.fullmatch(value))


class EvoluteClient:
    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        token_store: TokenStore | None = None,
        timeout: float = 30.0,
        min_telemetry_interval: float = MIN_TELEMETRY_INTERVAL_S,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tokens = token_store if token_store is not None else TokenStore.from_env_or_file()
        self.min_telemetry_interval = min_telemetry_interval
        self._http = httpx.Client(
            base_url=self.base_url,
            headers=default_headers(),
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self._refreshing = False
        self._telemetry_cache: dict[str, tuple[float, Telemetry]] = {}

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> EvoluteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- low-level ---------------------------------------------------------

    def _apply_access_token(self) -> None:
        token = self.tokens.access_token
        if token:
            self._http.headers[HEADER_ACCESS_TOKEN] = token
        else:
            self._http.headers.pop(HEADER_ACCESS_TOKEN, None)

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if auth:
            if not self.tokens.access_token:
                raise EvoluteAuthError("missing access token")
            self._apply_access_token()
        else:
            self._http.headers.pop(HEADER_ACCESS_TOKEN, None)

        log.debug("%s %s", method, path)
        response = self._http.request(method, path, json=json, params=params)

        if response.status_code == 401 and auth and not self._refreshing:
            log.debug("401 on %s %s; refreshing once", method, path)
            self.refresh()
            self._apply_access_token()
            response = self._http.request(method, path, json=json, params=params)

        if response.status_code >= 400:
            raise EvoluteAPIError(
                f"{method} {path} failed ({response.status_code})",
                status_code=response.status_code,
            )
        return response

    def _json(self, response: httpx.Response) -> Any:
        if response.status_code == 204:
            return None
        text = response.text.strip()
        if not text or text == "null":
            return None
        return response.json()

    # --- auth --------------------------------------------------------------

    def get_info(self) -> ServiceInfo:
        """GET /id-service/info — no token. Field is ``capcha`` (API typo)."""
        response = self._request("GET", "/id-service/info", auth=False)
        data = self._json(response) or {}
        return ServiceInfo.model_validate(data)

    def request_otp(
        self,
        phone: str,
        phone_country: str,
        *,
        capcha_token: str = "",
    ) -> None:
        """POST /id-service/auth/sign-up. Sends one SMS. Phone format is caller-supplied."""
        self._request(
            "POST",
            "/id-service/auth/sign-up",
            auth=False,
            json={
                "phone": phone,
                "phoneCountry": phone_country,
                "capchaToken": capcha_token,
            },
        )

    def sign_in(self, phone: str, code: str) -> AuthTokens:
        """POST /id-service/auth/sign-in. Persists the token pair."""
        response = self._request(
            "POST",
            "/id-service/auth/sign-in",
            auth=False,
            json={"phone": phone, "code": code},
        )
        tokens = AuthTokens.model_validate(self._json(response) or {})
        self.tokens.apply_tokens(tokens)
        self._apply_access_token()
        return tokens

    def refresh(self) -> AuthTokens:
        """POST /id-service/auth/refresh-token. Refresh token rotates — persist both."""
        if not self.tokens.refresh_token:
            raise EvoluteAuthError("missing refresh token")
        if self._refreshing:
            raise EvoluteAuthError("refresh already in progress")
        self._refreshing = True
        try:
            response = self._request(
                "POST",
                "/id-service/auth/refresh-token",
                auth=False,
                json={"refreshToken": self.tokens.refresh_token},
            )
            tokens = AuthTokens.model_validate(self._json(response) or {})
            self.tokens.apply_tokens(tokens)
            self._apply_access_token()
            return tokens
        finally:
            self._refreshing = False

    def me(self) -> User:
        response = self._request("GET", "/id-service/user")
        return User.model_validate(self._json(response) or {})

    def list_orgs(self) -> Any:
        response = self._request("GET", "/id-service/org/my")
        return self._json(response)

    # --- vehicles ----------------------------------------------------------

    def list_vehicles(
        self, *, limit: int = DEFAULT_PAGE_LIMIT, offset: int = 0
    ) -> list[Vehicle]:
        page = self.search_vehicles(limit=limit, offset=offset)
        return page.rows

    def search_vehicles(
        self, *, limit: int = DEFAULT_PAGE_LIMIT, offset: int = 0
    ) -> VehiclePage:
        response = self._request(
            "POST",
            "/car-service/car/v2/search",
            json={"limit": limit, "offset": offset, "filters": []},
        )
        return VehiclePage.model_validate(self._json(response) or {})

    def get_vehicle(self, car_id: str) -> Vehicle:
        response = self._request("GET", f"/car-service/car/v2/{car_id}")
        return Vehicle.model_validate(self._json(response) or {})

    def default_car_id(self) -> str:
        if self.tokens.car_id:
            return self.tokens.car_id
        vehicles = self.list_vehicles()
        if not vehicles:
            raise EvoluteAPIError("no vehicles on this account")
        return vehicles[0].id

    def get_flags(
        self,
        *,
        brand: str = "",
        modification: str = "",
        user_id: str = "",
        vin: str = "",
    ) -> FeatureFlags:
        """GET /config-service/config/flags. Origin often omits access-token."""
        response = self._request(
            "GET",
            "/config-service/config/flags",
            auth=False,
            params={
                "brand": brand,
                "modification": modification,
                "userId": user_id,
                "vin": vin,
            },
        )
        return FeatureFlags.model_validate(self._json(response) or {})

    # --- telemetry ---------------------------------------------------------

    def _resolve_imei(self, imei: str | None, car_id: str | None, positional: str | None) -> str:
        if imei:
            return imei
        if car_id:
            return self._imei_for_car(car_id)
        if positional:
            if looks_like_car_id(positional):
                return self._imei_for_car(positional)
            return positional
        if self.tokens.car_id:
            return self._imei_for_car(self.tokens.car_id)
        vehicles = self.list_vehicles()
        if not vehicles:
            raise EvoluteAPIError("no vehicles on this account")
        if not vehicles[0].imei:
            raise EvoluteAPIError("vehicle has no telemetry id")
        return vehicles[0].imei

    def _imei_for_car(self, car_id: str) -> str:
        vehicle = self.get_vehicle(car_id)
        if not vehicle.imei:
            raise EvoluteAPIError("vehicle has no telemetry id")
        return vehicle.imei

    def get_telemetry(
        self,
        vehicle_or_imei: str | None = None,
        *,
        imei: str | None = None,
        car_id: str | None = None,
    ) -> Telemetry:
        """GET /client-bff-service/telemetry/{imei}. Resolves mongo ``_id`` to IMEI."""
        telemetry_id = self._resolve_imei(imei, car_id, vehicle_or_imei)
        now = time.monotonic()
        cached = self._telemetry_cache.get(telemetry_id)
        if cached and (now - cached[0]) < self.min_telemetry_interval:
            return cached[1]
        response = self._request("GET", f"/client-bff-service/telemetry/{telemetry_id}")
        telemetry = Telemetry.model_validate(self._json(response) or {})
        self._telemetry_cache[telemetry_id] = (time.monotonic(), telemetry)
        return telemetry

    def get_charge_session(self) -> ChargeSession | None:
        """GET /charge-service/session/v2/current. 404 means not charging."""
        try:
            response = self._request("GET", "/charge-service/session/v2/current")
        except EvoluteAPIError as exc:
            if exc.status_code == 404:
                return None
            raise
        data = self._json(response)
        if data is None or data == {}:
            return None
        return ChargeSession.model_validate(data)

    # --- trips -------------------------------------------------------------

    def list_trip_filters(self) -> list[TripFilter]:
        response = self._request("GET", "/car-service/travels/filters")
        data = self._json(response) or []
        if not isinstance(data, list):
            return []
        return [TripFilter.model_validate(item) for item in data]

    def list_trips(
        self,
        car_id: str,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
        sort_by: str = DEFAULT_TRIP_SORT_BY,
        sort_dir: str = DEFAULT_TRIP_SORT_DIR,
        filters: list[dict[str, Any]] | None = None,
    ) -> TripPage:
        """POST /car-service/travels/search/{carId}.

        ``sort_by`` / ``sort_dir`` default to live-confirmed ``DATE`` / ``DESC``.
        Allowed ``by``: ``DATE``, ``DURATION``, ``DISTANCE``. Allowed ``dir``:
        ``ASC``, ``DESC``. ``distance`` is a raw int; units are unknown.
        """
        response = self._request(
            "POST",
            f"/car-service/travels/search/{car_id}",
            json={
                "sort": {"by": sort_by, "dir": sort_dir},
                "filters": filters if filters is not None else [],
                "limit": limit,
                "offset": offset,
            },
        )
        return TripPage.model_validate(self._json(response) or {})

    def get_trip(self, car_id: str, travel_id: int, start_time: int) -> TripDetails:
        """GET /car-service/travels/details/{carId}/{travelId}?startTime=.

        ``travel_id`` is int. ``start_time`` must be that trip's ``segmentStartTime``.
        """
        response = self._request(
            "GET",
            f"/car-service/travels/details/{car_id}/{int(travel_id)}",
            params={"startTime": start_time},
        )
        return TripDetails.model_validate(self._json(response) or {})

    # --- commands (not implemented) ----------------------------------------

    def send_command(self, *args: Any, **kwargs: Any) -> None:
        """Do not call this against a live car.

        The official app appears to use Socket.IO (``/car-service/ws``) and/or
        ``car-service/tbox/v1``. That channel is unconfirmed; payloads are
        unknown. Live vehicle commands are intentionally not implemented.
        """
        raise NotImplementedError(
            "Vehicle command channel is unconfirmed; live commands are not implemented."
        )
