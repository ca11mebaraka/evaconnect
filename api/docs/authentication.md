# Authentication

## Scheme

The companion API authenticates with an API key **header**:

```
access-token: <YOUR_TOKEN>
```

It does **not** use `Authorization: Bearer`. Sending Bearer was not tested;
the Android-shaped client used by evaconnect never sets that header.

OpenAPI: `components.securitySchemes.accessToken`.

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

## Login

Unauthenticated:

1. `GET /id-service/info` — read `capcha`. If false, `capchaToken` may be `""`.
2. `POST /id-service/auth/sign-up` with `{ "phone", "phoneCountry", "capchaToken" }` — one SMS.
3. `POST /id-service/auth/sign-in` with `{ "phone", "code" }` — tokens.

Phone / `phoneCountry` canonical format is **unknown**. Pass the same strings
the official app would; do not invent a mask.

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

`userToken` and `widgetId` are stored by evaconnect and were present on live
sign-in/refresh. Their use on later requests was not observed (data calls use
`access-token` only).

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
