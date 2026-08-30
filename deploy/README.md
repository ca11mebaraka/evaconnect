# Deploy poller + Postgres (existing Grafana)

Same host as Grafana at `rn.melikhov.biz`. Compose starts **only** `db` and `poller`.
Do not publish Postgres beyond loopback.

## 1. Secrets on the server

```bash
git clone <this-repo> && cd evaconnect
cp .env.example .env
# fill POSTGRES_PASSWORD and GRAFANA_DB_PASSWORD only
chmod 600 .env

# file MUST exist before compose up (otherwise Docker makes a directory)
# copy AFTER the last local evolute/poller use — refresh rotates the pair
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

**Grafana in Docker on this host**

```bash
docker network connect evaconnect <grafana-container>
```

Set the datasource URL to `db:5432` (compose service name on network `evaconnect`).

## 4. After a day

Heartbeat panel should stay green. A 401 on telemetry then a **200** refresh
is expected. A 401 on `/id-service/auth/refresh-token` means the refresh
token is dead — replace `credentials.json` (see above) and restart poller.
