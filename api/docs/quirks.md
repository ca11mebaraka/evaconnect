# Quirks

Behavior that does not match a typical REST companion API. All items below
were seen live unless marked otherwise.

## Auth

- Header is `access-token`, not `Authorization: Bearer`.
- `POST /id-service/auth/refresh-token` rotates **both** tokens. Losing the
  new `refreshToken` ends the session.
- Refresh is called **without** `access-token`.
- Access-token TTL is unknown. One 401 → one refresh → one retry is the
  observed client policy, not a vendor guarantee.
- Field `capcha` / body `capchaToken` (missing `t`) on info and sign-up.

## Two vehicle identifiers

Mongo `_id` (24 hex) is used for cars and trips. IMEI is used only for
`GET /client-bff-service/telemetry/{imei}`. They are not interchangeable.

`POST /car-service/car/v2/search` may return `imei: null` while
`GET /car-service/car/v2/{carId}` for the same `_id` includes IMEI
(observed 2026-09-02).

## Telemetry

- JSON sensor values are often **strings** (`"64"`, `"true"`).
- When `onlineState` is `notFound` / `isOnline` is false, the same keys were
  boolean `false` (not null, not omitted). Charts that coerce false → 0 will
  look like empty battery.
- `sensors.isOnline` duplicates top-level `isOnline`.
- `lat` / `lon` / `course` are present; treat as location PII.
- `buttons[]` lists official-app commands (`heatingOn`, `centralLockingOff`,
  `trunkOpen`, `search`, `tripPreparationOn`, …). **No HTTP send** of those
  names was captured. The Android app appears to use Socket.IO
  (`/car-service/ws`) and/or `car-service/tbox/v1`; path and payload are
  **unconfirmed**. Do not invent a POST body.

Buttons captured 2026-09-02 (titles may be localized):

| title (RU) | activateCommand | deactivateCommand | runOnSchedule |
| --- | --- | --- | --- |
| Центральный замок | centralLockingOff | centralLockingOn | false |
| Прогрев | heatingOn | heatingOff | false |
| Охлаждение | coolingOn | coolingOff | false |
| Открыть багажник | trunkOpen | trunkClose | false |
| Поиск | search | search | false |
| Подготовка к поездке | tripPreparationOn | tripPreparationOff | true |

`enabled` was false while the vehicle was `notFound`.

## Charge session

`GET /charge-service/session/v2/current` returns **HTTP 404** when not
charging. That is an empty state, not a missing route. HTTP 200 body while
charging was **not** captured.

## Trips

- Sort must be `sort.by` ∈ `DATE` \| `DURATION` \| `DISTANCE` and
  `sort.dir` ∈ `ASC` \| `DESC`. `startDate` / `desc` → **400**.
- `title` is a UTC clock range (`"08:38 - 09:00"`) aligned with
  `startDate` / `endDate` (**milliseconds**), not with `segmentStartTime`
  (**seconds**). `segmentStartTime` minutes did not match `title`.
- Search vs details (same trip, 2026-09-02): details omitted `title`,
  `startDate`, `endDate`, `batteryConsumption`; included `points[]`
  (`lat`, `lon`, `time` in ms) and empty `startAddr` / `endAddr`.
- Details requires query `startTime=<segmentStartTime>`.
- `distance` is a raw integer; unit (m vs km) unknown. Live value `3` on a
  ~3 km trip is consistent with kilometers but **not** proven.
- `description` on search is typically an address (PII).
- `fuel.first` / `fuel.last` were `100` on an EV; likely unused noise.
- Filter catalog (`PERIOD`, `DATE_START`, `DATE_END`) was fetched; applying
  filters on search was not tested (`filters: []` only).

## User document vs telemetry

`GET /id-service/user` includes `buttons` as a **boolean ACL map**
(`travelsVisible`, `addCar`, …). Telemetry `buttons` is a **command catalog**.
Same JSON key, different types.

## Config flags

`GET /config-service/config/flags` without query params returned **400**.
A successful document was not captured. The client sends `brand`,
`modification`, `userId`, `vin` and omits `access-token`.

## Misc

- `lastSensorsRecieved` (sic) on the vehicle GET.
- `availableScriptTime` on the vehicle card was `[5, 15, 30, 60, 90, 120]`
  with `currentScriptTime: 120`. Meaning not tested (likely preset durations).
- `GET /id-service/org/my` returned `rows: []` on a private owner account;
  `headers` still present.
- Feature `GET /config-service/config/flags` 200 schema is unknown; do not
  copy mock `{ "flags": { "newTelemetryEnabled": true } }` from unit tests
  into production assumptions.
