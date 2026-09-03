# Authentication

[Русский](authentication.ru.md)

## Scheme

The companion API authenticates with an API key **header**:

```
access-token: <YOUR_TOKEN>
```

It does **not** use `Authorization: Bearer`. Sending Bearer was not tested;
the Android-shaped client used by evaconnect never sets that header.

OpenAPI: `components.securitySchemes.accessToken`.

A step-by-step login that writes `~/.config/evolute/credentials.json` is in
the repository [README](../../README.md#auth). Below is the same flow as HTTP.

## Client headers (not proven required)

Every evaconnect request also sends:

| Header | Value used in captures |
| --- | --- |
| `content-type` | `application/json` (on bodies) |
| `accept` | `application/json` |
| `cache-control` | `no-cache` |
| `x-device` | `android` |
| `x-app` | `mobile` |
| `x-app-version` | `5.1.22 (740)` |

Whether the server rejects other device/app strings was not A/B tested.
`Time-Zone` is **not** sent by evaconnect; effect of sending it is unknown.

## Obtain a token pair

Unauthenticated. Own account only. Each `sign-up` sends **one SMS**.

Phone / `phoneCountry` canonical format is **unknown**. Pass the same strings
the official app would.

```bash
BASE=https://app.evassist.ru
H='accept: application/json'
H2='content-type: application/json'
H3='cache-control: no-cache'
H4='x-device: android'
H5='x-app: mobile'
H6='x-app-version: 5.1.22 (740)'

# 1. Optional: captcha flag (spelling is capcha)
curl -sS "$BASE/id-service/info" -H "$H" -H "$H3" -H "$H4" -H "$H5" -H "$H6"

# 2. Request OTP. capchaToken may be "" when capcha is false.
curl -sS -X POST "$BASE/id-service/auth/sign-up" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"phone":"00000000000","phoneCountry":"XX","capchaToken":""}'

# 3. Exchange the SMS code for tokens
curl -sS -X POST "$BASE/id-service/auth/sign-in" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"phone":"00000000000","code":"000000"}'
```

Token JSON (field names as on the wire):

```json
{
  "userId": "bbbbbbbbbbbbbbbbbbbbbbbb",
  "accessToken": "<YOUR_TOKEN>",
  "refreshToken": "<YOUR_REFRESH_TOKEN>",
  "userToken": "<YOUR_USER_TOKEN>",
  "widgetId": "widget-example"
}
```

Save `accessToken` and `refreshToken`. `userToken` and `widgetId` were present
on live sign-in/refresh; later data calls used `access-token` only.

Runnable copies: [`examples/api.http`](../examples/api.http) (`sign-up`,
`sign-in`, then authenticated requests).

## Use the access token

Send it on every authenticated request:

```bash
curl -sS "$BASE/id-service/user" \
  -H "access-token: <YOUR_TOKEN>" \
  -H "$H" -H "$H3" -H "$H4" -H "$H5" -H "$H6"

curl -sS -X POST "$BASE/car-service/car/v2/search" \
  -H "access-token: <YOUR_TOKEN>" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"limit":20,"offset":0,"filters":[]}'
```

Then telemetry uses IMEI from the vehicle card, trips use mongo `_id`. See
[quirks](quirks.md) for the two identifiers.

With evaconnect, do not paste tokens into each command: `sign_in` writes
`~/.config/evolute/credentials.json`, and `evolute status` / the poller read
that file.

## Refresh

`POST /id-service/auth/refresh-token` with `{ "refreshToken": "<YOUR_REFRESH_TOKEN>" }`.

- Do **not** send `access-token` on this call (evaconnect strips it).
- The response **rotates** `refreshToken`. Persist both tokens or the next
  refresh returns **401** and the session is dead.
- Access-token TTL was not measured. Data calls return **401** when expired;
  evaconnect refreshes once and retries.

## Identifiers

Two vehicle ids, not interchangeable:

| Id | Where | Use |
| --- | --- | --- |
| Mongo `_id` (24 hex) | `Vehicle._id` | `/car-service/car/v2/{carId}`, trip search/details |
| IMEI | `Vehicle.imei` | `/client-bff-service/telemetry/{imei}` |

`POST /car-service/car/v2/search` has returned `imei: null` for a car whose
`GET /car-service/car/v2/{carId}` included an IMEI. Prefer GET when resolving
telemetry.

## Operations without `access-token`

Live or client-confirmed unauthenticated calls:

- `GET /id-service/info`
- `POST /id-service/auth/sign-up`
- `POST /id-service/auth/sign-in`
- `POST /id-service/auth/refresh-token`
- `GET /config-service/config/flags` (client omits the header; success not captured)
