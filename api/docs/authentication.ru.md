# Авторизация

[English](authentication.md)

## Схема

Companion API аутентифицируется **заголовком** API-ключа:

```
access-token: <YOUR_TOKEN>
```

`Authorization: Bearer` **не** используется. Bearer не тестировали;
Android-подобный клиент evaconnect этот заголовок никогда не ставит.

OpenAPI: `components.securitySchemes.accessToken`.

Пошаговый вход, который пишет `~/.config/evolute/credentials.json`, есть в
[README репозитория](../../README.ru.md#авторизация). Ниже тот же поток как HTTP.

## Заголовки клиента (обязательность не доказана)

Каждый запрос evaconnect также шлёт:

| Заголовок | Значение в захватах |
| --- | --- |
| `content-type` | `application/json` (на телах) |
| `accept` | `application/json` |
| `cache-control` | `no-cache` |
| `x-device` | `android` |
| `x-app` | `mobile` |
| `x-app-version` | `5.1.22 (740)` |

Отвергает ли сервер другие строки device/app, A/B не проверяли.
`Time-Zone` evaconnect **не** шлёт; эффект отправки неизвестен.

## Получить пару токенов

Без авторизации. Только свой аккаунт. Каждый `sign-up` шлёт **одно SMS**.

Канонический формат телефона / `phoneCountry` **неизвестен**. Передавайте те
же строки, что официальное приложение.

```bash
BASE=https://app.evassist.ru
H='accept: application/json'
H2='content-type: application/json'
H3='cache-control: no-cache'
H4='x-device: android'
H5='x-app: mobile'
H6='x-app-version: 5.1.22 (740)'

# 1. Необязательно: флаг капчи (написание capcha)
curl -sS "$BASE/id-service/info" -H "$H" -H "$H3" -H "$H4" -H "$H5" -H "$H6"

# 2. Запросить OTP. capchaToken может быть "" когда capcha = false.
curl -sS -X POST "$BASE/id-service/auth/sign-up" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"phone":"00000000000","phoneCountry":"XX","capchaToken":""}'

# 3. Обменять SMS-код на токены
curl -sS -X POST "$BASE/id-service/auth/sign-in" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"phone":"00000000000","code":"000000"}'
```

JSON токенов (имена полей как на проводе):

```json
{
  "userId": "bbbbbbbbbbbbbbbbbbbbbbbb",
  "accessToken": "<YOUR_TOKEN>",
  "refreshToken": "<YOUR_REFRESH_TOKEN>",
  "userToken": "<YOUR_USER_TOKEN>",
  "widgetId": "widget-example"
}
```

Сохраните `accessToken` и `refreshToken`. `userToken` и `widgetId` были в
живом sign-in/refresh; дальнейшие вызовы данных использовали только
`access-token`.

Запускаемые копии: [`examples/api.http`](../examples/api.http) (`sign-up`,
`sign-in`, затем авторизованные запросы).

## Использовать access-токен

Шлите его на каждый авторизованный запрос:

```bash
curl -sS "$BASE/id-service/user" \
  -H "access-token: <YOUR_TOKEN>" \
  -H "$H" -H "$H3" -H "$H4" -H "$H5" -H "$H6"

curl -sS -X POST "$BASE/car-service/car/v2/search" \
  -H "access-token: <YOUR_TOKEN>" \
  -H "$H" -H "$H2" -H "$H3" -H "$H4" -H "$H5" -H "$H6" \
  -d '{"limit":20,"offset":0,"filters":[]}'
```

Дальше телеметрия берёт IMEI из карточки автомобиля, поездки — mongo `_id`.
Два идентификатора: [особенности](quirks.ru.md).

В evaconnect не вставляйте токены в каждую команду: `sign_in` пишет
`~/.config/evolute/credentials.json`, а `evolute status` / poller читают
этот файл.

## Refresh

`POST /id-service/auth/refresh-token` с `{ "refreshToken": "<YOUR_REFRESH_TOKEN>" }`.

- **Не** шлите `access-token` на этом вызове (evaconnect его снимает).
- Ответ **ротирует** `refreshToken`. Сохраните оба токена, иначе следующий
  refresh вернёт **401** и сессия умрёт.
- TTL access-токена не измеряли. Вызовы данных возвращают **401** по
  истечении; evaconnect один раз делает refresh и повторяет запрос.

## Идентификаторы

Два id автомобиля, не взаимозаменяемые:

| Id | Откуда | Куда |
| --- | --- | --- |
| Mongo `_id` (24 hex) | `Vehicle._id` | `/car-service/car/v2/{carId}`, поиск/детали поездок |
| IMEI | `Vehicle.imei` | `/client-bff-service/telemetry/{imei}` |

`POST /car-service/car/v2/search` возвращал `imei: null` для машины, у которой
`GET /car-service/car/v2/{carId}` содержал IMEI. Для телеметрии предпочтителен GET.

## Операции без `access-token`

Живые или подтверждённые клиентом неавторизованные вызовы:

- `GET /id-service/info`
- `POST /id-service/auth/sign-up`
- `POST /id-service/auth/sign-in`
- `POST /id-service/auth/refresh-token`
- `GET /config-service/config/flags` (клиент заголовок не шлёт; успех не захвачен)
