"""stdio MCP server — read-only Evolute tools. No commands, no OTP."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from evaconnect.auth import TokenStore
from evaconnect.client import EvoluteClient
from evaconnect.errors import EvoluteAuthError, EvoluteError
from evaconnect.redact import public_status, public_trip_details, public_trip_summary, public_vehicle

log = logging.getLogger("evaconnect.mcp")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="evolute_status",
        description=(
            "Telemetry of the default (or given) vehicle: charge, climate, doors, online. "
            "Coordinates are hidden unless include_pii is true."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "car_id": {
                    "type": "string",
                    "description": "Mongo car _id. Defaults to EVOLUTE_CAR_ID or the first vehicle.",
                },
                "include_pii": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, include exact lat/lon.",
                },
            },
        },
    ),
    ToolSpec(
        name="evolute_vehicles",
        description="List vehicles. VIN/IMEI are masked unless include_pii is true.",
        input_schema={
            "type": "object",
            "properties": {
                "include_pii": {"type": "boolean", "default": False},
            },
        },
    ),
    ToolSpec(
        name="evolute_trips",
        description=(
            "Recent trips for the default (or given) vehicle. "
            "Addresses and track are omitted. Distance is a raw integer (units unknown)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "car_id": {"type": "string"},
                "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                "offset": {"type": "integer", "default": 0, "minimum": 0},
                "sort_by": {
                    "type": "string",
                    "description": "DATE, DURATION, or DISTANCE. Default DATE.",
                },
                "sort_dir": {
                    "type": "string",
                    "description": "ASC or DESC. Default DESC.",
                },
                "include_pii": {
                    "type": "boolean",
                    "default": False,
                    "description": "If true, include trip description (often an address).",
                },
            },
        },
    ),
    ToolSpec(
        name="evolute_trip",
        description=(
            "One trip. Track points only if include_track=true. "
            "Addresses only if include_pii=true. start_time is segmentStartTime."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "travel_id": {"type": "integer", "description": "Trip id (int)."},
                "start_time": {
                    "type": "integer",
                    "description": "segmentStartTime of that trip (required by the API).",
                },
                "car_id": {"type": "string"},
                "include_track": {"type": "boolean", "default": False},
                "include_pii": {"type": "boolean", "default": False},
            },
            "required": ["travel_id", "start_time"],
        },
    ),
    ToolSpec(
        name="evolute_charge",
        description="Current charge session, if any. Empty when not charging.",
        input_schema={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="evolute_auth_status",
        description="Whether a session looks valid. Never returns raw tokens.",
        input_schema={"type": "object", "properties": {}},
    ),
)

FORBIDDEN_TOOL_NAMES = frozenset({"send_command", "request_otp", "evolute_command"})


def list_tool_names() -> list[str]:
    return [spec.name for spec in TOOL_SPECS]


def list_tools() -> list[ToolSpec]:
    return list(TOOL_SPECS)


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def _client() -> EvoluteClient:
    return EvoluteClient()


def dispatch_tool(name: str, arguments: dict[str, Any] | None) -> str:
    """Synchronous tool handler used by the MCP server and by unit tests."""
    args = arguments or {}
    if name == "evolute_status":
        return _tool_status(args)
    if name == "evolute_vehicles":
        return _tool_vehicles(args)
    if name == "evolute_trips":
        return _tool_trips(args)
    if name == "evolute_trip":
        return _tool_trip(args)
    if name == "evolute_charge":
        return _tool_charge(args)
    if name == "evolute_auth_status":
        return _tool_auth_status(args)
    raise ValueError(f"unknown tool: {name}")


def _tool_status(args: dict[str, Any]) -> str:
    include_pii = bool(args.get("include_pii", False))
    with _client() as client:
        car_id = args.get("car_id") or client.default_car_id()
        telemetry = client.get_telemetry(car_id=car_id)
        return _json_text(public_status(telemetry, include_pii=include_pii))


def _tool_vehicles(args: dict[str, Any]) -> str:
    include_pii = bool(args.get("include_pii", False))
    with _client() as client:
        vehicles = client.list_vehicles()
        return _json_text([public_vehicle(v, include_pii=include_pii) for v in vehicles])


def _tool_trips(args: dict[str, Any]) -> str:
    include_pii = bool(args.get("include_pii", False))
    limit = int(args.get("limit", 5))
    offset = int(args.get("offset", 0))
    kwargs: dict[str, Any] = {"limit": limit, "offset": offset}
    if args.get("sort_by"):
        kwargs["sort_by"] = args["sort_by"]
    if args.get("sort_dir"):
        kwargs["sort_dir"] = args["sort_dir"]
    with _client() as client:
        car_id = args.get("car_id") or client.default_car_id()
        page = client.list_trips(car_id, **kwargs)
        return _json_text(
            {
                "car_id": car_id,
                "total": page.total,
                "offset": page.offset,
                "limit": page.limit,
                "rows": [public_trip_summary(t, include_pii=include_pii) for t in page.rows],
            }
        )


def _tool_trip(args: dict[str, Any]) -> str:
    travel_id = int(args["travel_id"])
    start_time = int(args["start_time"])
    include_track = bool(args.get("include_track", False))
    include_pii = bool(args.get("include_pii", False))
    with _client() as client:
        car_id = args.get("car_id") or client.default_car_id()
        trip = client.get_trip(car_id, travel_id, start_time)
        return _json_text(
            public_trip_details(trip, include_pii=include_pii, include_track=include_track)
        )


def _tool_charge(_args: dict[str, Any]) -> str:
    with _client() as client:
        session = client.get_charge_session()
        if session is None:
            return _json_text({"session": None})
        return _json_text({"session": session.model_dump(mode="json")})


def _tool_auth_status(_args: dict[str, Any]) -> str:
    store = TokenStore.from_env_or_file()
    payload: dict[str, Any] = {
        "has_access_token": store.has_access(),
        "has_refresh_token": store.has_refresh(),
        "has_default_car_id": bool(store.car_id),
        "session_valid": False,
    }
    if not store.has_access() and not store.has_refresh():
        return _json_text(payload)
    try:
        with EvoluteClient(token_store=store) as client:
            user = client.me()
        payload["session_valid"] = True
        payload["user_id"] = user.id
    except EvoluteAuthError:
        payload["session_valid"] = False
    except EvoluteError:
        payload["session_valid"] = False
    return _json_text(payload)


def _mcp_tools():
    from mcp.types import Tool

    tools = []
    for spec in TOOL_SPECS:
        try:
            tools.append(
                Tool(name=spec.name, description=spec.description, input_schema=spec.input_schema)
            )
        except TypeError:
            tools.append(
                Tool(name=spec.name, description=spec.description, inputSchema=spec.input_schema)
            )
    return tools


def build_server():
    """stdio MCP server (mcp 2.x MCPServer). Tools are read-only."""
    from mcp.server.mcpserver import MCPServer

    specs = {spec.name: spec for spec in TOOL_SPECS}
    server = MCPServer(
        "evaconnect",
        instructions="Read-only Evolute companion tools for your own vehicle. No commands, no OTP.",
    )

    @server.tool(description=specs["evolute_status"].description)
    def evolute_status(car_id: str | None = None, include_pii: bool = False) -> str:
        return dispatch_tool("evolute_status", {"car_id": car_id, "include_pii": include_pii})

    @server.tool(description=specs["evolute_vehicles"].description)
    def evolute_vehicles(include_pii: bool = False) -> str:
        return dispatch_tool("evolute_vehicles", {"include_pii": include_pii})

    @server.tool(description=specs["evolute_trips"].description)
    def evolute_trips(
        car_id: str | None = None,
        limit: int = 5,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        include_pii: bool = False,
    ) -> str:
        return dispatch_tool(
            "evolute_trips",
            {
                "car_id": car_id,
                "limit": limit,
                "offset": offset,
                "sort_by": sort_by,
                "sort_dir": sort_dir,
                "include_pii": include_pii,
            },
        )

    @server.tool(description=specs["evolute_trip"].description)
    def evolute_trip(
        travel_id: int,
        start_time: int,
        car_id: str | None = None,
        include_track: bool = False,
        include_pii: bool = False,
    ) -> str:
        return dispatch_tool(
            "evolute_trip",
            {
                "travel_id": travel_id,
                "start_time": start_time,
                "car_id": car_id,
                "include_track": include_track,
                "include_pii": include_pii,
            },
        )

    @server.tool(description=specs["evolute_charge"].description)
    def evolute_charge() -> str:
        return dispatch_tool("evolute_charge", {})

    @server.tool(description=specs["evolute_auth_status"].description)
    def evolute_auth_status() -> str:
        return dispatch_tool("evolute_auth_status", {})

    return server


async def _run_stdio() -> None:
    server = build_server()
    await server.run_stdio_async()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
