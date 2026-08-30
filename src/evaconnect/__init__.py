"""Typed Evolute companion client (own account / own vehicle)."""

from evaconnect.auth import TokenStore
from evaconnect.client import EvoluteClient
from evaconnect.constants import APP_VERSION, BASE_URL
from evaconnect.errors import EvoluteAPIError, EvoluteAuthError, EvoluteError
from evaconnect.models import (
    AuthTokens,
    ChargeSession,
    ServiceInfo,
    Telemetry,
    TripDetails,
    TripSummary,
    User,
    Vehicle,
)

__all__ = [
    "APP_VERSION",
    "BASE_URL",
    "AuthTokens",
    "ChargeSession",
    "EvoluteAPIError",
    "EvoluteAuthError",
    "EvoluteClient",
    "EvoluteError",
    "ServiceInfo",
    "Telemetry",
    "TokenStore",
    "TripDetails",
    "TripSummary",
    "User",
    "Vehicle",
]

__version__ = "0.1.0"
