from __future__ import annotations

from evaconnect.auth import TokenStore


def test_file_tokens_win_over_stale_env(creds_path, monkeypatch) -> None:
    store = TokenStore(creds_path)
    store.access_token = "file-access"
    store.refresh_token = "file-refresh"
    store.save()
    monkeypatch.setenv("EVOLUTE_ACCESS_TOKEN", "stale-access")
    monkeypatch.setenv("EVOLUTE_REFRESH_TOKEN", "stale-refresh")
    loaded = TokenStore.from_env_or_file(creds_path)
    assert loaded.access_token == "file-access"
    assert loaded.refresh_token == "file-refresh"


def test_env_fills_when_file_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EVOLUTE_ACCESS_TOKEN", "env-access")
    monkeypatch.setenv("EVOLUTE_REFRESH_TOKEN", "env-refresh")
    loaded = TokenStore.from_env_or_file(tmp_path / "missing.json")
    assert loaded.access_token == "env-access"
    assert loaded.refresh_token == "env-refresh"


def test_warns_when_creds_path_is_directory(tmp_path, caplog, monkeypatch) -> None:
    monkeypatch.delenv("EVOLUTE_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("EVOLUTE_REFRESH_TOKEN", raising=False)
    directory = tmp_path / "credentials.json"
    directory.mkdir()
    store = TokenStore.from_env_or_file(directory)
    assert store.access_token is None
    assert "directory" in caplog.text.lower()
