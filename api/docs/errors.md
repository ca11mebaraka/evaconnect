# Errors

[Русский](errors.ru.md)

Only these HTTP statuses were seen on production. Response **bodies** were not
captured as a stable schema; do not assume `{ "error": "..." }`.

| Status | Where | Meaning (as observed) |
| --- | --- | --- |
| 400 | `POST /car-service/travels/search/{carId}` | Invalid `sort.by` / `sort.dir` (`startDate` / `desc` rejected) |
| 400 | `GET /config-service/config/flags` | Empty query string (2026-09-02) |
| 401 | `POST /id-service/auth/refresh-token` | Refresh token rejected / already rotated |
| 401 | Authenticated GET/POST | Access token missing or expired |
| 404 | `GET /charge-service/session/v2/current` | No current charge session (vehicle not charging) |

Not observed (do not document as API behavior): 403, 409, 422, 429, 5xx.

## 404 is not always "unknown route"

Charge `.../session/v2/current` **404** is a normal empty state. Treat it as
"no session", not as a wrong path.

## 401 recovery

Data request 401 → `POST /id-service/auth/refresh-token` (no `access-token`
header) → retry once with the new access token. A 401 on refresh itself means
re-login. Refresh **rotates** `refreshToken`; reusing the old refresh token
yields 401.
