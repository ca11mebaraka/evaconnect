# Evolute companion API (unofficial)

[Русский](README.ru.md)

[![lint](https://github.com/ca11mebaraka/evaconnect/actions/workflows/lint.yml/badge.svg)](https://github.com/ca11mebaraka/evaconnect/actions/workflows/lint.yml)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)

This directory is an unofficial, reverse-engineered description of the HTTP API
behind the Evolute companion app (`https://app.evassist.ru`). It is **not**
published by Evolute, Motorinvest, or the operators of evassist.ru. There is
**no affiliation** with those parties. Use against your own account only.

Machine-readable source of truth: [`openapi.yaml`](openapi.yaml) (OpenAPI 3.1).

## Quickstart

Get `accessToken` / `refreshToken` with SMS OTP, then send header
`access-token` (not Bearer). Full sequence: [authentication.md](docs/authentication.md).

Bootstrap (no token):

```bash
curl -sS 'https://app.evassist.ru/id-service/info' \
  -H 'accept: application/json' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Authenticated example (replace placeholders):

```bash
curl -sS 'https://app.evassist.ru/id-service/user' \
  -H 'accept: application/json' \
  -H 'access-token: <YOUR_TOKEN>' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Runnable request files: [`examples/api.http`](examples/api.http).
Bruno: open [`examples/`](examples/) (`collection.bru` + request `*.bru`).

## Endpoints

| Method | Path | Auth | Status |
| --- | --- | --- | --- |
| `GET` | `/id-service/info` | no | verified |
| `POST` | `/id-service/auth/sign-up` | no | partial |
| `POST` | `/id-service/auth/sign-in` | no | verified |
| `POST` | `/id-service/auth/refresh-token` | no | verified |
| `GET` | `/id-service/user` | yes | verified |
| `GET` | `/id-service/org/my` | yes | verified |
| `POST` | `/car-service/car/v2/search` | yes | verified |
| `GET` | `/car-service/car/v2/{carId}` | yes | verified |
| `GET` | `/client-bff-service/telemetry/{imei}` | yes | verified |
| `GET` | `/charge-service/session/v2/current` | yes | partial |
| `GET` | `/car-service/travels/filters` | yes | verified |
| `POST` | `/car-service/travels/search/{carId}` | yes | verified |
| `GET` | `/car-service/travels/details/{carId}/{travelId}` | yes | verified |
| `GET` | `/config-service/config/flags` | no | partial |

Vehicle command **send** is not listed. Command names appear on telemetry
`buttons`; the transport was not confirmed. See [quirks](docs/quirks.md).

### Status legend

| `x-status` | Meaning |
| --- | --- |
| `verified` | Reproduced against production with the evaconnect client |
| `partial` | Called live, but status code, body, or field set is incomplete |
| `guessed` | Inferred only. None of the operations above are `guessed` |

## Docs

- [Authentication](docs/authentication.md) ([RU](docs/authentication.ru.md))
- [Rate limits](docs/rate-limits.md) ([RU](docs/rate-limits.ru.md))
- [Errors](docs/errors.md) ([RU](docs/errors.ru.md))
- [Quirks](docs/quirks.md) ([RU](docs/quirks.ru.md))

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) ([RU](CONTRIBUTING.ru.md)). OpenAPI changes must keep `x-status` /
`x-discovered` / `x-source` honest. Do not invent endpoints.
