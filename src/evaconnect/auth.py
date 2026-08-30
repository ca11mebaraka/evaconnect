"""Token store: env vars and optional ~/.config/evolute/credentials.json (chmod 600)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from evaconnect.models import AuthTokens

log = logging.getLogger("evaconnect.auth")

ENV_ACCESS = "EVOLUTE_ACCESS_TOKEN"
ENV_REFRESH = "EVOLUTE_REFRESH_TOKEN"
ENV_CAR_ID = "EVOLUTE_CAR_ID"
ENV_CREDENTIALS = "EVOLUTE_CREDENTIALS"


def default_credentials_path() -> Path:
    override = os.environ.get(ENV_CREDENTIALS)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "evolute" / "credentials.json"


class TokenStore:
    """In-memory tokens, optionally persisted to a chmod-600 JSON file.

    Environment variables override file values on load. After refresh, the
    new pair is written back to the file (if a path is set) and into env
    so the current process keeps using the rotated tokens.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.user_id: str | None = None
        self.user_token: str | None = None
        self.widget_id: str | None = None
        self.car_id: str | None = None

    @classmethod
    def from_env_or_file(cls, path: Path | None = None) -> TokenStore:
        store = cls(path if path is not None else default_credentials_path())
        store.load()
        return store

    def load(self) -> None:
        if self.path and self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("credentials file unreadable")
                data = {}
                _ = exc
            if isinstance(data, dict):
                self.access_token = data.get("accessToken") or data.get("access_token")
                self.refresh_token = data.get("refreshToken") or data.get("refresh_token")
                self.user_id = data.get("userId") or data.get("user_id")
                self.user_token = data.get("userToken") or data.get("user_token")
                self.widget_id = data.get("widgetId") or data.get("widget_id")
                self.car_id = data.get("carId") or data.get("car_id")
        if os.environ.get(ENV_ACCESS):
            self.access_token = os.environ[ENV_ACCESS]
        if os.environ.get(ENV_REFRESH):
            self.refresh_token = os.environ[ENV_REFRESH]
        if os.environ.get(ENV_CAR_ID):
            self.car_id = os.environ[ENV_CAR_ID]

    def apply_tokens(self, tokens: AuthTokens) -> None:
        if tokens.access_token:
            self.access_token = tokens.access_token
        if tokens.refresh_token:
            self.refresh_token = tokens.refresh_token
        if tokens.user_id:
            self.user_id = tokens.user_id
        if tokens.user_token:
            self.user_token = tokens.user_token
        if tokens.widget_id:
            self.widget_id = tokens.widget_id
        self.save()

    def save(self) -> None:
        if self.access_token:
            os.environ[ENV_ACCESS] = self.access_token
        if self.refresh_token:
            os.environ[ENV_REFRESH] = self.refresh_token
        if not self.path:
            return
        payload = {
            "accessToken": self.access_token,
            "refreshToken": self.refresh_token,
            "userId": self.user_id,
            "userToken": self.user_token,
            "widgetId": self.widget_id,
            "carId": self.car_id,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.chmod(0o600)
        tmp.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def has_access(self) -> bool:
        return bool(self.access_token)

    def has_refresh(self) -> bool:
        return bool(self.refresh_token)
