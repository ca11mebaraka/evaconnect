from __future__ import annotations

from pathlib import Path

import pytest
import respx

from evaconnect.auth import TokenStore
from evaconnect.client import EvoluteClient
from evaconnect.constants import BASE_URL
from tests.fakes import FAKE_ACCESS, FAKE_CAR_ID, FAKE_REFRESH, FAKE_USER_ID


@pytest.fixture
def creds_path(tmp_path: Path) -> Path:
    return tmp_path / "credentials.json"


@pytest.fixture
def token_store(creds_path: Path) -> TokenStore:
    store = TokenStore(creds_path)
    store.access_token = FAKE_ACCESS
    store.refresh_token = FAKE_REFRESH
    store.user_id = FAKE_USER_ID
    store.car_id = FAKE_CAR_ID
    store.save()
    return store


@pytest.fixture
def client(token_store: TokenStore) -> EvoluteClient:
    return EvoluteClient(
        base_url=BASE_URL,
        token_store=token_store,
        min_telemetry_interval=0,
    )


@pytest.fixture
def mocked_api():
    with respx.mock(base_url=BASE_URL, assert_all_mocked=True) as router:
        yield router
