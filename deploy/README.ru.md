# Деплой poller + Postgres (уже существующая Grafana)

[English](README.md)

Тот же хост, что и Grafana на `rn.melikhov.biz`. Compose поднимает **только**
`db` и `poller`. Postgres наружу дальше loopback не публиковать.

## 1. Секреты на сервере

```bash
git clone <this-repo> && cd evaconnect
cp .env.example .env
# заполните только POSTGRES_PASSWORD и GRAFANA_DB_PASSWORD
chmod 600 .env

# файл ДОЛЖЕН существовать до compose up (иначе Docker создаст каталог)
# Сначала получите его локально (README.ru.md → Авторизация: request_otp + sign_in),
# затем копируйте ПОСЛЕ последнего локального использования evolute/poller —
# refresh ротирует пару
cp /path/to/credentials.json ./credentials.json
chmod 600 credentials.json
test -f credentials.json   # должен быть файл, не каталог
```

`credentials.json` — источник истины. Не кладите `EVOLUTE_ACCESS_TOKEN` /
`EVOLUTE_REFRESH_TOKEN` в `.env`. Если refresh вернул 401, пара мертва:
снова SMS-вход на доверенной машине, scp нового файла,
`docker compose restart poller`.

Не коммитьте `.env` и `credentials.json`.

## 2. Запуск

```bash
docker compose up -d --build
docker compose logs -f poller
```

Postgres слушает только `127.0.0.1:5432`. Проверка:

```bash
ss -lntp | grep 5432   # 127.0.0.1:5432, не 0.0.0.0
```

Телеметрия каждые 30 с, поездки каждые 15 мин. Переопределение:
`POLL_TELEMETRY_INTERVAL_S` / `POLL_TRIPS_INTERVAL_S` (телеметрия не ниже 5).

## 3. Подключить существующую Grafana к БД

Пользователь только на чтение `grafana_ro` создаётся при первой инициализации
Postgres (пароль = `GRAFANA_DB_PASSWORD`).

**Grafana на хосте**

1. Скопируйте [`grafana/datasource.yaml`](grafana/datasource.yaml) в
   provisioning datasources Grafana (или добавьте тот же Postgres datasource
   в UI): хост `127.0.0.1:5432`, пользователь `grafana_ro`, база
   `evaconnect`, TLS выключен.
2. Скопируйте [`grafana/dashboards/evolute.json`](grafana/dashboards/evolute.json)
   через [`grafana/dashboard-provider.yaml`](grafana/dashboard-provider.yaml)
   или импортируйте JSON. uid datasource должен остаться `evaconnect-pg`.
   Имя папки провайдера — **Evolute**. uid дашборда `evaconnect-evolute`,
   часовой пояс `Europe/Moscow`, refresh 30 с.

**Grafana в Docker на этом хосте**

```bash
docker network connect evaconnect <grafana-container>
```

URL datasource — `db:5432` (имя сервиса compose в сети `evaconnect`).

## 4. Раскладка дашборда

JSON: [`grafana/dashboards/evolute.json`](grafana/dashboards/evolute.json).

**Обзор** (те же девять панелей, что в первой ревизии дашборда):

- Battery % и оставшийся запас хода (сырые единицы API)
- Температуры: салон, улица, батарея
- 12V батарея
- Статы: Online, Central lock, Odometer (сырой), Poller heartbeat
- Недавние поездки: `title` — `HH:MM - HH:MM` в Europe/Moscow из
  `start_date` / `end_date` (миллисекунды). Без адресов.

Дополнительные ряды используют колонки poller плюс `telemetry.raw`:

- **Сейчас** — зажигание, парк, пистолет зарядки, сигнал, уставки климата,
  таблица последнего снимка, каталог команд только для чтения из
  `raw.status.buttons`
- **Зарядка** — пистолет 0/1 во времени
- **Климат** — охлаждающая жидкость, цель климата, вентилятор
- **Кузов** — `doorFLStatus` / `FR` / `RL` / `RR`, багажник, фары
  (`raw->sensors`)
- **Движение** — одометр, зажигание, парк, сигнал
- **Служебные сенсоры** — ключи топлива / прошивки / настроек как прислал API
- **Поездки** — `battery_first` / `battery_last` плюс график дистанции
- **Poller** — длительность цикла `duration_ms` и строки ошибок

Двери и лишние сенсоры — не колонки; они живут в JSONB `telemetry.raw`
(гео-ключи `lat`/`lon`/`course` poller вырезает).

## 5. Через сутки

Панель heartbeat должна оставаться зелёной. 401 на телеметрии, затем **200**
на refresh — ожидаемо. 401 на `/id-service/auth/refresh-token` значит, что
refresh-токен мёртв — замените `credentials.json` (см. выше) и перезапустите
poller.
