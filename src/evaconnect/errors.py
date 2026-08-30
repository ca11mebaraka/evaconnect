"""Client errors. Messages must never include tokens, VIN, IMEI, phone, or coordinates."""


class EvoluteError(Exception):
    """Base error for the Evolute client."""


class EvoluteAuthError(EvoluteError):
    """Missing credentials or a failed refresh/sign-in."""


class EvoluteAPIError(EvoluteError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
