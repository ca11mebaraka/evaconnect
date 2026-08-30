"""Protocol constants. App version lives in one place."""

from typing import Final

BASE_URL: Final[str] = "https://app.evassist.ru"
APP_VERSION: Final[str] = "5.1.22 (740)"

# Origin header set. Auth uses access-token, not Authorization: Bearer.
HEADER_CONTENT_TYPE: Final[str] = "content-type"
HEADER_ACCEPT: Final[str] = "accept"
HEADER_CACHE_CONTROL: Final[str] = "cache-control"
HEADER_DEVICE: Final[str] = "x-device"
HEADER_APP: Final[str] = "x-app"
HEADER_APP_VERSION: Final[str] = "x-app-version"
HEADER_ACCESS_TOKEN: Final[str] = "access-token"

# Telemetry must not be polled faster than this (prefer on-demand).
MIN_TELEMETRY_INTERVAL_S: Final[float] = 5.0

# Confirmed against live evy-car-service: by in DATE|DURATION|DISTANCE, dir in ASC|DESC.
DEFAULT_TRIP_SORT_BY: Final[str] = "DATE"
DEFAULT_TRIP_SORT_DIR: Final[str] = "DESC"

DEFAULT_PAGE_LIMIT: Final[int] = 20

# Mongo car _id is 24 hex chars; IMEI is not.
MONGO_ID_LEN: Final[int] = 24


def default_headers() -> dict[str, str]:
    return {
        HEADER_CONTENT_TYPE: "application/json",
        HEADER_ACCEPT: "application/json",
        HEADER_CACHE_CONTROL: "no-cache",
        HEADER_DEVICE: "android",
        HEADER_APP: "mobile",
        HEADER_APP_VERSION: APP_VERSION,
    }
