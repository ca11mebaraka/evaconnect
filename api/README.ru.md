# Companion API Evolute (неофициально)

[English](README.md)

[![lint](https://github.com/ca11mebaraka/evaconnect/actions/workflows/lint.yml/badge.svg)](https://github.com/ca11mebaraka/evaconnect/actions/workflows/lint.yml)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)

Этот каталог — неофициальное, reverse-engineered описание HTTP API
companion-приложения Evolute (`https://app.evassist.ru`). Его **не** публикуют
Evolute, Motorinvest и операторы evassist.ru. **Аффилиации нет**. Используйте
только против своего аккаунта.

Машиночитаемый источник истины: [`openapi.yaml`](openapi.yaml) (OpenAPI 3.1).

## Быстрый старт

Получите `accessToken` / `refreshToken` по SMS OTP, затем шлите заголовок
`access-token` (не Bearer). Полная последовательность:
[authentication.ru.md](docs/authentication.ru.md).

Bootstrap (без токена):

```bash
curl -sS 'https://app.evassist.ru/id-service/info' \
  -H 'accept: application/json' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Пример с авторизацией (подставьте плейсхолдеры):

```bash
curl -sS 'https://app.evassist.ru/id-service/user' \
  -H 'accept: application/json' \
  -H 'access-token: <YOUR_TOKEN>' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Запускаемые файлы запросов: [`examples/api.http`](examples/api.http).
Bruno: откройте [`examples/`](examples/) (`collection.bru` + запросы `*.bru`).

## Эндпоинты

| Method | Path | Auth | Status |
| --- | --- | --- | --- |
| `GET` | `/id-service/info` | нет | verified |
| `POST` | `/id-service/auth/sign-up` | нет | partial |
| `POST` | `/id-service/auth/sign-in` | нет | verified |
| `POST` | `/id-service/auth/refresh-token` | нет | verified |
| `GET` | `/id-service/user` | да | verified |
| `GET` | `/id-service/org/my` | да | verified |
| `POST` | `/car-service/car/v2/search` | да | verified |
| `GET` | `/car-service/car/v2/{carId}` | да | verified |
| `GET` | `/client-bff-service/telemetry/{imei}` | да | verified |
| `GET` | `/charge-service/session/v2/current` | да | partial |
| `GET` | `/car-service/travels/filters` | да | verified |
| `POST` | `/car-service/travels/search/{carId}` | да | verified |
| `GET` | `/car-service/travels/details/{carId}/{travelId}` | да | verified |
| `GET` | `/config-service/config/flags` | нет | partial |

**Отправка** команд автомобилю не перечислена. Имена команд есть в телеметрии
`buttons`; транспорт не подтверждён. См. [особенности](docs/quirks.ru.md).

### Легенда статусов

| `x-status` | Значение |
| --- | --- |
| `verified` | Воспроизведено против продакшена клиентом evaconnect |
| `partial` | Живой вызов был, но код статуса, тело или набор полей неполны |
| `guessed` | Только вывод. Ни одна операция выше не `guessed` |

## Документация

- [Авторизация](docs/authentication.ru.md)
- [Лимиты](docs/rate-limits.ru.md)
- [Ошибки](docs/errors.ru.md)
- [Особенности](docs/quirks.ru.md)

## Как дополнять

См. [CONTRIBUTING.ru.md](CONTRIBUTING.ru.md). Правки OpenAPI должны честно
держать `x-status` / `x-discovered` / `x-source`. Не выдумывайте эндпоинты.
