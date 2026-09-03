# evaconnect

Typed Python client and stdio MCP server for the Evolute companion API
(`https://app.evassist.ru`). Own account / own vehicle only.

Read telemetry (charge, climate, doors, online) and recent trips without the
official Android app. **Vehicle commands are not implemented** — the command
channel is unconfirmed.

## Install

Python 3.12+.

```bash
cd /Users/nmel/Documents/Projects/evaconnect
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

Editable (`pip install -e`) is optional. On Python 3.14 / macOS the hatchling
`.pth` is often marked hidden, and 3.14 then skips it — `evolute` fails with
`No module named 'evaconnect'`. Either install without `-e`, or after `-e` run:

```bash
chflags nohidden .venv/lib/python*/site-packages/*.pth
```

Entry points after install:

- `evolute` — small CLI (`status`, `trips`, `vehicles`, `info`)
- `evaconnect-mcp` — stdio MCP server
- `evaconnect-poller` — write telemetry/trips to Postgres for Grafana

Remote poller + Postgres next to an existing Grafana: see [deploy/README.md](deploy/README.md).
Grafana dashboard JSON: [deploy/grafana/dashboards/evolute.json](deploy/grafana/dashboards/evolute.json)
(folder **Evolute**, uid `evaconnect-evolute`, timezone `Europe/Moscow`).

Unofficial reverse-engineered HTTP spec (CC0, not vendor docs): [api/README.md](api/README.md).

## Auth

Preferred for the poller: `credentials.json` (created `chmod 600`). Refresh
**rotates** `refreshToken`; the file is the source of truth.

```json
{
  "accessToken": "",
  "refreshToken": "",
  "carId": ""
}
```

Override the path with `EVOLUTE_CREDENTIALS`. Env vars
(`EVOLUTE_ACCESS_TOKEN` / `EVOLUTE_REFRESH_TOKEN` / `EVOLUTE_CAR_ID`) fill
missing fields only — they do not override tokens already in the file. After
refresh the new pair is written back to the file and into the process env.

Do not commit tokens, phone, VIN, IMEI, or coordinates.

Library login (CLI / scripts only — **not** exposed as MCP tools):

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    info = client.get_info()          # no token; field is capcha, not captcha
    client.request_otp(phone, phone_country)  # one SMS; formats are caller-supplied
    client.sign_in(phone, code)
```

Auth header is `access-token: <token>`, not `Authorization: Bearer`.

## Library

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.refresh()
    me = client.me()
    cars = client.list_vehicles()          # id, plate, model; VIN/IMEI not in repr
    car = client.get_vehicle(cars[0].id)
    tel = client.get_telemetry(car_id=car.id)  # or imei=…
    session = client.get_charge_session()      # may be None
    trips = client.list_trips(car.id, limit=5, offset=0)
    trip = client.get_trip(car.id, trips.rows[0].id, trips.rows[0].segment_start_time)
```

`get_telemetry` accepts an IMEI or a mongo car `_id` (24 hex chars) and
resolves IMEI when needed. Those two IDs are not interchangeable.

`send_command` exists only as a stub and always raises `NotImplementedError`.

## CLI

```bash
evolute info          # GET /id-service/info (no token)
evolute status
evolute trips -n 5
evolute vehicles
```

## MCP (Cursor)

stdio server. Tools (read-only):

| Tool | What it returns |
|---|---|
| `evolute_status` | Charge, climate, doors, online. Geo hidden unless `include_pii` |
| `evolute_vehicles` | List; VIN/IMEI masked unless `include_pii` |
| `evolute_trips` | Last N trips; no addresses/track |
| `evolute_trip` | One trip; track only if `include_track=true` |
| `evolute_charge` | Current charge session (or empty) |
| `evolute_auth_status` | Session present/valid; **no raw tokens** |

There is **no** `request_otp` and **no** command-sending tool.

Cursor `mcp.json` example (`~/.cursor/mcp.json` or project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "evaconnect": {
      "command": "/Users/nmel/Documents/Projects/evaconnect/.venv/bin/evaconnect-mcp",
      "env": {
        "EVOLUTE_ACCESS_TOKEN": "",
        "EVOLUTE_REFRESH_TOKEN": "",
        "EVOLUTE_CAR_ID": ""
      }
    }
  }
}
```

If the venv is on `PATH`, `"command": "evaconnect-mcp"` is enough.

Default MCP output redacts VIN, IMEI, phone, tokens, and exact coordinates
(`include_pii` off). Do not poll telemetry faster than once per 5 seconds
(the client caches within that window).

## Tests

Mocks only — tests never call production. GitHub Actions runs `pytest` and
Spectral on `api/openapi.yaml`.

```bash
pytest
```

## Grafana dashboard

Provisioned JSON: [`deploy/grafana/dashboards/evolute.json`](deploy/grafana/dashboards/evolute.json).
Datasource uid `evaconnect-pg`. Rows:

| Row | Content |
|---|---|
| Обзор | Original nine panels: Battery, Remaining range, Temperatures (cabin/outside/battery), 12V, Online, Central lock, Odometer, Poller heartbeat, Recent trips |
| Сейчас | Ignition, park, charge gun, signal, climate target/fan, last snapshot, command catalog |
| Зарядка | Charge-gun timeseries |
| Климат | Coolant, climate target, fan |
| Кузов | Doors, trunk, headlights from `telemetry.raw` JSONB |
| Движение | Odometer timeseries, ignition/park/signal |
| Служебные сенсоры | Fuel % / firmware / settings (often unused on EV) |
| Поездки | Extra table (`battery_first`/`last`) and distance/consumption chart. Overview trips `title` is MSK from `start_date`/`end_date` |
| Poller | Cycle duration and errors |

Trip addresses and coordinates are not stored. See [deploy/README.md](deploy/README.md).

## Spec gaps (explicit parameters, no guessing)

- Phone / `phoneCountry` format is unknown — pass them as strings.
- Trip `sort.by` / `dir` default to live-confirmed `DATE` / `DESC`
  (`DURATION` / `DISTANCE` and `ASC` are also valid).
- `distance` units (m vs km) are unknown — raw `int`, no conversion.
- Access-token TTL is unknown — one auto-refresh on HTTP 401, no loop.
- Charge-session body when charging is not fully specified. See [api/docs/quirks.md](api/docs/quirks.md).
- `Time-Zone` header is unused (not confirmed).

Full endpoint table and `x-status` markers: [api/README.md](api/README.md).

## License

MIT for the Python client, MCP server, and poller.

The unofficial API description under [`api/`](api/) is [CC0-1.0](api/LICENSE).
