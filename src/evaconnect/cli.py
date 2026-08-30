"""Minimal CLI: ``evolute status`` and ``evolute trips``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from evaconnect.client import EvoluteClient
from evaconnect.redact import public_status, public_trip_summary, public_vehicle


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def cmd_status(args: argparse.Namespace) -> int:
    with EvoluteClient() as client:
        car_id = args.car_id or client.default_car_id()
        telemetry = client.get_telemetry(car_id=car_id)
        _print(public_status(telemetry, include_pii=args.include_pii))
    return 0


def cmd_trips(args: argparse.Namespace) -> int:
    with EvoluteClient() as client:
        car_id = args.car_id or client.default_car_id()
        page = client.list_trips(car_id, limit=args.limit, offset=args.offset)
        _print(
            {
                "car_id": car_id,
                "total": page.total,
                "rows": [
                    public_trip_summary(t, include_pii=args.include_pii) for t in page.rows
                ],
            }
        )
    return 0


def cmd_vehicles(args: argparse.Namespace) -> int:
    with EvoluteClient() as client:
        vehicles = client.list_vehicles()
        _print([public_vehicle(v, include_pii=args.include_pii) for v in vehicles])
    return 0


def cmd_info(_: argparse.Namespace) -> int:
    with EvoluteClient() as client:
        info = client.get_info()
        _print(info.model_dump(mode="json", by_alias=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evolute",
        description="Read-only Evolute companion CLI (own account / own vehicle).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Charge, climate, doors, online.")
    p_status.add_argument("--car-id")
    p_status.add_argument("--include-pii", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_trips = sub.add_parser("trips", help="Recent trips (no addresses/track).")
    p_trips.add_argument("--car-id")
    p_trips.add_argument("-n", "--limit", type=int, default=5)
    p_trips.add_argument("--offset", type=int, default=0)
    p_trips.add_argument("--include-pii", action="store_true")
    p_trips.set_defaults(func=cmd_trips)

    p_vehicles = sub.add_parser("vehicles", help="List vehicles.")
    p_vehicles.add_argument("--include-pii", action="store_true")
    p_vehicles.set_defaults(func=cmd_vehicles)

    p_info = sub.add_parser("info", help="Public /id-service/info (no token).")
    p_info.set_defaults(func=cmd_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s %(message)s",
    )
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
