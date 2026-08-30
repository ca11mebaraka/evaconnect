from __future__ import annotations

import json

import httpx
import pytest

from evaconnect.mcp_server import (
    FORBIDDEN_TOOL_NAMES,
    TOOL_SPECS,
    dispatch_tool,
    list_tool_names,
    list_tools,
)

from tests.fakes import FAKE_CAR_ID, FAKE_IMEI, telemetry_payload, trip_row, vehicle_row


def test_tool_list_includes_status_and_trips() -> None:
    names = list_tool_names()
    assert "evolute_status" in names
    assert "evolute_trips" in names
    assert "evolute_vehicles" in names
    assert "evolute_trip" in names
    assert "evolute_charge" in names
    assert "evolute_auth_status" in names
    assert names == [spec.name for spec in list_tools()]
    assert names == [spec.name for spec in TOOL_SPECS]


def test_tool_list_excludes_commands_and_otp() -> None:
    names = set(list_tool_names())
    assert names.isdisjoint(FORBIDDEN_TOOL_NAMES)
    for spec in TOOL_SPECS:
        blob = (spec.name + spec.description).lower()
        assert "send_command" not in blob
        assert "request_otp" not in blob


@pytest.mark.asyncio
async def test_mcp_server_list_tools() -> None:
    from evaconnect.mcp_server import build_server

    server = build_server()
    tools = await server.list_tools()
    names = [t.name for t in tools]
    assert "evolute_status" in names
    assert "evolute_trips" in names
    assert "send_command" not in names
    assert "request_otp" not in names


def test_mcp_types_tool_conversion() -> None:
    from evaconnect.mcp_server import _mcp_tools

    tools = _mcp_tools()
    names = [t.name for t in tools]
    assert "evolute_status" in names
    assert "evolute_trips" in names
    status = next(t for t in tools if t.name == "evolute_status")
    schema = getattr(status, "input_schema", None) or getattr(status, "inputSchema", None)
    assert schema["type"] == "object"


def test_dispatch_status_and_trips(mocked_api, token_store, monkeypatch) -> None:
    monkeypatch.setenv("EVOLUTE_ACCESS_TOKEN", token_store.access_token or "")
    monkeypatch.setenv("EVOLUTE_REFRESH_TOKEN", token_store.refresh_token or "")
    monkeypatch.setenv("EVOLUTE_CAR_ID", FAKE_CAR_ID)
    monkeypatch.setenv("EVOLUTE_CREDENTIALS", str(token_store.path))

    mocked_api.get(f"/car-service/car/v2/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json=vehicle_row())
    )
    mocked_api.get(f"/client-bff-service/telemetry/{FAKE_IMEI}").mock(
        return_value=httpx.Response(200, json=telemetry_payload())
    )
    mocked_api.post(f"/car-service/travels/search/{FAKE_CAR_ID}").mock(
        return_value=httpx.Response(200, json={"rows": [trip_row()], "total": 1})
    )

    status = json.loads(dispatch_tool("evolute_status", {"car_id": FAKE_CAR_ID}))
    assert status["charge"]["battery_percentage"] == 64
    assert status["climate"]["target"] == 22
    assert "lat" not in json.dumps(status)

    trips = json.loads(dispatch_tool("evolute_trips", {"car_id": FAKE_CAR_ID, "limit": 5}))
    assert trips["rows"][0]["id"] == 101
    assert trips["rows"][0]["distance"] == 8500
    assert "description" not in trips["rows"][0]


def test_dispatch_unknown_tool() -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        dispatch_tool("send_command", {})
