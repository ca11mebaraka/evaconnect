# Deploy poller + Postgres (existing Grafana)

Same host as Grafana at `rn.melikhov.biz`. Compose starts **only** `db` and `poller`.
Do not publish Postgres beyond loopback.

## 1. Secrets on the server

```bash
git clone <this-repo> && cd evaconnect
cp .env.example .env
# fill POSTGRES_PASSWORD, GRAFANA_DB_PASSWORD, Evolute tokens
chmod 600 .env

# file must exist before compose up (otherwise Docker makes a directory)
cp /path/to/credentials.json ./credentials.json
chmod 600 credentials.json
```

`credentials.json` is writable: refresh **rotates** `refreshToken`. Env-only without this file loses the new pair after the first 401.

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

Heartbeat panel should stay green. 401 + refresh in poller logs is expected;
the cycle must keep writing rows. If refresh fails, replace `credentials.json`
from a machine that can still SMS-login and recreate the container.
