# Deploy poller + Postgres (existing Grafana)

[Русский](README.ru.md)

Same host as Grafana at `rn.melikhov.biz`. Compose starts **only** `db` and `poller`.
Do not publish Postgres beyond loopback.

## 1. Secrets on the server

```bash
git clone <this-repo> && cd evaconnect
cp .env.example .env
# fill POSTGRES_PASSWORD and GRAFANA_DB_PASSWORD only
chmod 600 .env

# file MUST exist before compose up (otherwise Docker makes a directory)
# Obtain it locally first (README.md → Auth: request_otp + sign_in),
# then copy AFTER the last local evolute/poller use — refresh rotates the pair
cp /path/to/credentials.json ./credentials.json
chmod 600 credentials.json
test -f credentials.json   # must be a file, not a directory
```

`credentials.json` is the source of truth. Do not put `EVOLUTE_ACCESS_TOKEN` /
`EVOLUTE_REFRESH_TOKEN` in `.env`. If refresh returns 401, the pair is dead:
SMS-login again on a trusted machine, scp the new file, `docker compose restart poller`.

Do not commit `.env` or `credentials.json`.

## 2. Start

```bash
docker compose up -d --build
docker compose logs -f poller
```

Postgres listens on `127.0.0.1:5432` only. Check:

```bash
ss -lntp | grep 5432   # 127.0.0.1:5432, not 0.0.0.0
```

Telemetry every 30s, trips every 15m. Override with `POLL_TELEMETRY_INTERVAL_S` /
`POLL_TRIPS_INTERVAL_S` (telemetry must stay >= 5).

## 3. Point existing Grafana at the DB

Read-only user `grafana_ro` is created on first Postgres init (password =
`GRAFANA_DB_PASSWORD`).

**Grafana on the host**

1. Copy [`grafana/datasource.yaml`](grafana/datasource.yaml) into Grafana
   datasources provisioning (or add the same Postgres datasource in the UI):
   host `127.0.0.1:5432`, user `grafana_ro`, database `evaconnect`, TLS off.
2. Copy [`grafana/dashboards/evolute.json`](grafana/dashboards/evolute.json)
   via [`grafana/dashboard-provider.yaml`](grafana/dashboard-provider.yaml)
   or import the JSON. Datasource uid must stay `evaconnect-pg`.
   Provider folder name is **Evolute**. Dashboard uid `evaconnect-evolute`,
   timezone `Europe/Moscow`, refresh 30s.

**Grafana in Docker on this host**

```bash
docker network connect evaconnect <grafana-container>
```

Set the datasource URL to `db:5432` (compose service name on network `evaconnect`).

## 4. Dashboard layout

JSON: [`grafana/dashboards/evolute.json`](grafana/dashboards/evolute.json).

**Обзор** (same nine panels as the first dashboard revision):

- Battery % and remaining range (raw API units)
- Temperatures: cabin, outside, battery
- 12V battery
- Stats: Online, Central lock, Odometer (raw), Poller heartbeat
- Recent trips: `title` is `HH:MM - HH:MM` in Europe/Moscow from `start_date` /
  `end_date` (milliseconds). No addresses.

Additional rows use poller columns plus `telemetry.raw`:

- **Сейчас** — ignition, park, charge gun, signal, climate setpoints, last
  snapshot table, read-only command catalog from `raw.status.buttons`
- **Зарядка** — charge-gun 0/1 over time
- **Климат** — coolant, climate target, fan
- **Кузов** — `doorFLStatus` / `FR` / `RL` / `RR`, trunk, headlights
  (`raw->sensors`)
- **Движение** — odometer, ignition, park, signal
- **Служебные сенсоры** — fuel / firmware / settings keys as the API sent them
- **Поездки** — `battery_first` / `battery_last` plus distance chart
- **Poller** — cycle duration_ms and error rows

Doors and extra sensors are not columns; they live in JSONB `telemetry.raw`
(geo keys `lat`/`lon`/`course` are stripped by the poller).

## 5. After a day

Heartbeat panel should stay green. A 401 on telemetry then a **200** refresh
is expected. A 401 on `/id-service/auth/refresh-token` means the refresh
token is dead — replace `credentials.json` (see above) and restart poller.
