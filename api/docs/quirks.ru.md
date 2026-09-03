# Особенности

[English](quirks.md)

Поведение, которое не совпадает с типичным REST companion API. Всё ниже
видено живьём, если не помечено иначе.

## Авторизация

- Заголовок — `access-token`, не `Authorization: Bearer`.
- `POST /id-service/auth/refresh-token` ротирует **оба** токена. Потеря нового
  `refreshToken` убивает сессию.
- Refresh вызывается **без** `access-token`.
- TTL access-токена неизвестен. Один 401 → один refresh → один повтор —
  наблюдаемая политика клиента, не гарантия вендора.
- Поле `capcha` / тело `capchaToken` (без `t`) на info и sign-up.

## Два идентификатора автомобиля

Mongo `_id` (24 hex) используется для машин и поездок. IMEI — только для
`GET /client-bff-service/telemetry/{imei}`. Они не взаимозаменяемы.

`POST /car-service/car/v2/search` может вернуть `imei: null`, тогда как
`GET /car-service/car/v2/{carId}` для того же `_id` содержит IMEI
(наблюдено 2026-09-02).

## Телеметрия

- Значения сенсоров в JSON часто **строки** (`"64"`, `"true"`).
- Когда `onlineState` = `notFound` / `isOnline` = false, те же ключи были
  булевым `false` (не null и не опущены). Графики, которые приводят false → 0,
  покажут пустую батарею.
- `sensors.isOnline` дублирует верхнеуровневый `isOnline`.
- `lat` / `lon` / `course` присутствуют; это гео-PII.
- `buttons[]` перечисляет команды официального приложения (`heatingOn`,
  `centralLockingOff`, `trunkOpen`, `search`, `tripPreparationOn`, …).
  **HTTP-отправка** этих имён не захватывалась. Android-приложение, похоже,
  использует Socket.IO (`/car-service/ws`) и/или `car-service/tbox/v1`; путь
  и payload **не подтверждены**. Не выдумывайте тело POST.

Кнопки, захваченные 2026-09-02 (заголовки могут быть локализованы):

| title (RU) | activateCommand | deactivateCommand | runOnSchedule |
| --- | --- | --- | --- |
| Центральный замок | centralLockingOff | centralLockingOn | false |
| Прогрев | heatingOn | heatingOff | false |
| Охлаждение | coolingOn | coolingOff | false |
| Открыть багажник | trunkOpen | trunkClose | false |
| Поиск | search | search | false |
| Подготовка к поездке | tripPreparationOn | tripPreparationOff | true |

`enabled` был false, пока автомобиль был `notFound`.

## Сессия зарядки

`GET /charge-service/session/v2/current` возвращает **HTTP 404**, когда не
заряжается. Это пустое состояние, не отсутствующий маршрут. Тело HTTP 200
во время зарядки **не** захватывалось.

## Поездки

- Сортировка: `sort.by` ∈ `DATE` \| `DURATION` \| `DISTANCE` и
  `sort.dir` ∈ `ASC` \| `DESC`. `startDate` / `desc` → **400**.
- `title` — диапазон часов UTC (`"08:38 - 09:00"`), согласованный с
  `startDate` / `endDate` (**миллисекунды**), не с `segmentStartTime`
  (**секунды**). Минуты `segmentStartTime` не совпадали с `title`.
- Поиск vs детали (та же поездка, 2026-09-02): детали опустили `title`,
  `startDate`, `endDate`, `batteryConsumption`; включили `points[]`
  (`lat`, `lon`, `time` в мс) и пустые `startAddr` / `endAddr`.
- Детали требуют query `startTime=<segmentStartTime>`.
- `distance` — сырое целое; единица (м или км) неизвестна. Живое значение `3`
  на поездке ~3 км согласуется с километрами, но **не** доказано.
- `description` в поиске обычно адрес (PII).
- `fuel.first` / `fuel.last` были `100` на EV; скорее неиспользуемый шум.
- Каталог фильтров (`PERIOD`, `DATE_START`, `DATE_END`) забирали; применение
  фильтров на поиске не тестировали (только `filters: []`).

## Документ пользователя vs телеметрия

`GET /id-service/user` содержит `buttons` как **булеву ACL-карту**
(`travelsVisible`, `addCar`, …). Телеметрия `buttons` — **каталог команд**.
Один и тот же JSON-ключ, разные типы.

## Флаги конфига

`GET /config-service/config/flags` без query-параметров вернул **400**.
Успешный документ не захватывался. Клиент шлёт `brand`, `modification`,
`userId`, `vin` и не ставит `access-token`.

## Разное

- `lastSensorsRecieved` (sic) на GET автомобиля.
- `availableScriptTime` на карточке автомобиля было `[5, 15, 30, 60, 90, 120]`
  при `currentScriptTime: 120`. Смысл не тестировали (скорее пресеты длительности).
- `GET /id-service/org/my` вернул `rows: []` на частном аккаунте владельца;
  `headers` всё равно были.
- Схема 200 у `GET /config-service/config/flags` неизвестна; не копируйте мок
  `{ "flags": { "newTelemetryEnabled": true } }` из юнит-тестов в продакшен-догадки.
