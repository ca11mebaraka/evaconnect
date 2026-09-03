# evaconnect

[Русский](README.ru.md)

Typed Python client and stdio MCP server for the Evolute companion API
(`https://app.evassist.ru`). Own account / own vehicle only.

Read telemetry (charge, climate, doors, online) and recent trips without the
official Android app. **Vehicle commands are not implemented** — the command
channel is unconfirmed.

## Install

Python 3.12+.

```bash
cd evaconnect
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

Do **not** use `pip install -e` on Python 3.14 / macOS. Hatchling marks the
`.pth` as Finder-hidden; 3.14 then skips it. `import evaconnect` hits a
namespace leftover in `site-packages/evaconnect` (often only `schema.sql`),
and the CLI dies:

```text
ModuleNotFoundError: No module named 'evaconnect'
ModuleNotFoundError: No module named 'evaconnect.cli'
```

Install a regular wheel (`pip install .` or `pip install ".[dev]"`). If you
already used `-e`, either reinstall without it, or:

```bash
chflags nohidden .venv/lib/python*/site-packages/*.pth
```

Then `evolute --help` should print the subcommands. Repeating `pip install -e`
puts the hidden flag back.
Entry points after install:

- `evolute` — small CLI (`status`, `trips`, `vehicles`, `info`)
- `evaconnect-mcp` — stdio MCP server
- `evaconnect-poller` — write telemetry/trips to Postgres for Grafana

Remote poller + Postgres next to an existing Grafana: see [deploy/README.md](deploy/README.md)
([RU](deploy/README.ru.md)).
Grafana dashboard JSON: [deploy/grafana/dashboards/evolute.json](deploy/grafana/dashboards/evolute.json)
(folder **Evolute**, uid `evaconnect-evolute`, timezone `Europe/Moscow`).

Unofficial reverse-engineered HTTP spec (CC0, not vendor docs): [api/README.md](api/README.md)
([RU](api/README.ru.md)).

## Auth

There is no password. The official app logs in with an SMS code. evaconnect
does the same: one SMS, then a token pair. The CLI has **no** `login`
command (and MCP never requests OTP). Use a short Python snippet.

### 1. Get tokens

`phone` / `phoneCountry` are whatever the official app sends. The vendor does
not document the mask; a live login used an 11-digit number (country code +
national number, no `+`) and a two-letter `phoneCountry`.

```python
from evaconnect import EvoluteClient

phone = "00000000000"
phone_country = "XX"

with EvoluteClient() as client:
    client.get_info()  # optional; field is capcha, not captcha
    client.request_otp(phone, phone_country)  # sends one SMS
```

When the SMS arrives:

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.sign_in("00000000000", "000000")  # phone, SMS code
```

That writes `~/.config/evolute/credentials.json` (`chmod 600`):

```json
{
  "accessToken": "<YOUR_TOKEN>",
  "refreshToken": "<YOUR_REFRESH_TOKEN>",
  "userId": "",
  "userToken": "",
  "widgetId": "",
  "carId": null
}
```

Override the path with `EVOLUTE_CREDENTIALS`. `carId` is optional: if empty,
the client uses the first vehicle on the account. Set it after
`evolute vehicles` if you have more than one car.

Do not commit this file, the phone number, VIN, IMEI, or coordinates.

### 2. Use the tokens

Later calls send header `access-token: <accessToken>`, **not**
`Authorization: Bearer`. The client loads the file automatically. Env vars
`EVOLUTE_ACCESS_TOKEN` / `EVOLUTE_REFRESH_TOKEN` / `EVOLUTE_CAR_ID` fill
**empty** fields only — they do not override tokens already in the file.

```bash
evolute vehicles
evolute status
evolute trips -n 5
```

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.refresh()   # optional; also happens automatically on HTTP 401
    print(client.list_vehicles())
    print(client.get_telemetry(car_id=client.default_car_id()))
```

curl (same headers the Android client sends):

```bash
TOKEN=$(python3 -c "import json,pathlib; p=pathlib.Path.home()/'.config/evolute/credentials.json'; print(json.loads(p.read_text())['accessToken'])")
curl -sS 'https://app.evassist.ru/id-service/user' \
  -H "access-token: $TOKEN" \
  -H 'accept: application/json' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Poller / Grafana: copy that `credentials.json` onto the server **after** the
last local use (refresh **rotates** `refreshToken`). See
[deploy/README.md](deploy/README.md) ([RU](deploy/README.ru.md)).

MCP: point `EVOLUTE_CREDENTIALS` at the file, or leave tokens out of
`mcp.json` so the default path is used. Do not put live tokens in git.

When a data request returns **401**, the client refreshes once, writes the
**new** pair back to the file, and retries. If refresh itself returns 401,
the pair is dead — run `sign_in` again. HTTP details:
[api/docs/authentication.md](api/docs/authentication.md)
([RU](api/docs/authentication.ru.md)).

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

Trip addresses and coordinates are not stored. See [deploy/README.md](deploy/README.md) ([RU](deploy/README.ru.md)).

## Spec gaps (explicit parameters, no guessing)

- Phone / `phoneCountry` format is unknown — pass them as strings.
- Trip `sort.by` / `dir` default to live-confirmed `DATE` / `DESC`
  (`DURATION` / `DISTANCE` and `ASC` are also valid).
- `distance` units (m vs km) are unknown — raw `int`, no conversion.
- Access-token TTL is unknown — one auto-refresh on HTTP 401, no loop.
- Charge-session body when charging is not fully specified. See [api/docs/quirks.md](api/docs/quirks.md)
([RU](api/docs/quirks.ru.md)).
- `Time-Zone` header is unused (not confirmed).

Full endpoint table and `x-status` markers: [api/README.md](api/README.md)
([RU](api/README.ru.md)).

## License

MIT for the Python client, MCP server, and poller.

The unofficial API description under [`api/`](api/) is [CC0-1.0](api/LICENSE).
