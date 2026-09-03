# evaconnect

[English](README.md)

Типизированный Python-клиент и stdio MCP-сервер для companion API Evolute
(`https://app.evassist.ru`). Только свой аккаунт / свой автомобиль.

Читает телеметрию (заряд, климат, двери, онлайн) и недавние поездки без
официального Android-приложения. **Команды автомобилю не реализованы** —
канал команд не подтверждён.

## Установка

Python 3.12+.

```bash
cd evaconnect
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

**Не** ставьте `pip install -e` на Python 3.14 / macOS. Hatchling помечает
`.pth` как скрытый в Finder; 3.14 его пропускает. `import evaconnect` цепляет
остаток namespace в `site-packages/evaconnect` (часто только `schema.sql`),
и CLI падает:

```text
ModuleNotFoundError: No module named 'evaconnect'
ModuleNotFoundError: No module named 'evaconnect.cli'
```

Ставьте обычный wheel (`pip install .` или `pip install ".[dev]"`). Если уже
ставили `-e`, переустановите без него или:

```bash
chflags nohidden .venv/lib/python*/site-packages/*.pth
```

После этого `evolute --help` должен показать подкоманды. Повторный
`pip install -e` снова ставит скрытый флаг.

Точки входа после установки:

- `evolute` — небольшой CLI (`status`, `trips`, `vehicles`, `info`)
- `evaconnect-mcp` — stdio MCP-сервер
- `evaconnect-poller` — пишет телеметрию и поездки в Postgres для Grafana

Удалённый poller + Postgres рядом с уже существующей Grafana:
[deploy/README.ru.md](deploy/README.ru.md).
JSON дашборда: [deploy/grafana/dashboards/evolute.json](deploy/grafana/dashboards/evolute.json)
(папка **Evolute**, uid `evaconnect-evolute`, часовой пояс `Europe/Moscow`).

Неофициальная reverse-engineered HTTP-спека (CC0, не документация вендора):
[api/README.ru.md](api/README.ru.md).

## Авторизация

Пароля нет. Официальное приложение входит по SMS-коду. evaconnect делает то
же: одно SMS, затем пара токенов. В CLI **нет** команды `login` (MCP тоже
никогда не запрашивает OTP). Используйте короткий фрагмент на Python.

### 1. Получить токены

`phone` / `phoneCountry` — те же строки, что шлёт официальное приложение.
Вендор маску не документирует; в живом входе был 11-значный номер (код страны
+ национальный номер, без `+`) и двухбуквенный `phoneCountry`.

```python
from evaconnect import EvoluteClient

phone = "00000000000"
phone_country = "XX"

with EvoluteClient() as client:
    client.get_info()  # необязательно; поле capcha, не captcha
    client.request_otp(phone, phone_country)  # одно SMS
```

Когда SMS пришло:

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.sign_in("00000000000", "000000")  # телефон, код из SMS
```

Это записывает `~/.config/evolute/credentials.json` (`chmod 600`):

```json
{
  "accessToken": "<YOUR_TOKEN>",
  "refreshToken": "<YOUR_REFRESH_TOKEN>",
  "userId": "",
  "userToken": "",
  "widgetId": "",
  "carId": null
}
```

Путь можно переопределить через `EVOLUTE_CREDENTIALS`. `carId` необязателен:
если пусто, клиент берёт первый автомобиль на аккаунте. Задайте его после
`evolute vehicles`, если машин больше одной.

Не коммитьте этот файл, номер телефона, VIN, IMEI и координаты.

### 2. Использовать токены

Дальнейшие запросы шлют заголовок `access-token: <accessToken>`, **не**
`Authorization: Bearer`. Клиент читает файл сам. Переменные окружения
`EVOLUTE_ACCESS_TOKEN` / `EVOLUTE_REFRESH_TOKEN` / `EVOLUTE_CAR_ID` заполняют
только **пустые** поля — они не перезаписывают токены, уже лежащие в файле.

```bash
evolute vehicles
evolute status
evolute trips -n 5
```

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.refresh()   # необязательно; также срабатывает автоматически на HTTP 401
    print(client.list_vehicles())
    print(client.get_telemetry(car_id=client.default_car_id()))
```

curl (те же заголовки, что шлёт Android-клиент):

```bash
TOKEN=$(python3 -c "import json,pathlib; p=pathlib.Path.home()/'.config/evolute/credentials.json'; print(json.loads(p.read_text())['accessToken'])")
curl -sS 'https://app.evassist.ru/id-service/user' \
  -H "access-token: $TOKEN" \
  -H 'accept: application/json' \
  -H 'x-device: android' \
  -H 'x-app: mobile' \
  -H 'x-app-version: 5.1.22 (740)'
```

Poller / Grafana: скопируйте этот `credentials.json` на сервер **после**
последнего локального использования (refresh **ротирует** `refreshToken`).
См. [deploy/README.ru.md](deploy/README.ru.md).

MCP: укажите `EVOLUTE_CREDENTIALS` на файл или не кладите токены в `mcp.json`,
чтобы использовался путь по умолчанию. Живые токены в git не класть.

Если запрос данных вернул **401**, клиент один раз делает refresh, пишет
**новую** пару в файл и повторяет запрос. Если сам refresh вернул 401, пара
мертва — снова выполните `sign_in`. HTTP-подробности:
[api/docs/authentication.ru.md](api/docs/authentication.ru.md).

## Библиотека

```python
from evaconnect import EvoluteClient

with EvoluteClient() as client:
    client.refresh()
    me = client.me()
    cars = client.list_vehicles()          # id, номер, модель; VIN/IMEI нет в repr
    car = client.get_vehicle(cars[0].id)
    tel = client.get_telemetry(car_id=car.id)  # или imei=…
    session = client.get_charge_session()      # может быть None
    trips = client.list_trips(car.id, limit=5, offset=0)
    trip = client.get_trip(car.id, trips.rows[0].id, trips.rows[0].segment_start_time)
```

`get_telemetry` принимает IMEI или mongo `_id` автомобиля (24 hex) и при
необходимости резолвит IMEI. Эти два идентификатора не взаимозаменяемы.

`send_command` существует только как заглушка и всегда бросает
`NotImplementedError`.

## CLI

```bash
evolute info          # GET /id-service/info (без токена)
evolute status
evolute trips -n 5
evolute vehicles
```

## MCP (Cursor)

stdio-сервер. Инструменты (только чтение):

| Инструмент | Что возвращает |
|---|---|
| `evolute_status` | Заряд, климат, двери, онлайн. Гео скрыто, пока не `include_pii` |
| `evolute_vehicles` | Список; VIN/IMEI маскируются, пока не `include_pii` |
| `evolute_trips` | Последние N поездок; без адресов и трека |
| `evolute_trip` | Одна поездка; трек только при `include_track=true` |
| `evolute_charge` | Текущая сессия зарядки (или пусто) |
| `evolute_auth_status` | Есть ли сессия / валидна ли; **сырых токенов нет** |

Нет инструмента `request_otp` и нет инструмента отправки команд.

Пример Cursor `mcp.json` (`~/.cursor/mcp.json` или проектный `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "evaconnect": {
      "command": "/Users/nmel/Documents/Projects/evaconnect/.venv/bin/evaconnect-mcp",
      "env": {
        "EVOLUTE_ACCESS_TOKEN": "",
        "EVOLUTE_REFRESH_TOKEN": "",
        "EVOLUTE_CAR_ID": ""
      }
    }
  }
}
```

Если venv в `PATH`, достаточно `"command": "evaconnect-mcp"`.

По умолчанию MCP скрывает VIN, IMEI, телефон, токены и точные координаты
(`include_pii` выключен). Не опрашивайте телеметрию чаще раза в 5 секунд
(клиент кэширует в этом окне).

## Тесты

Только моки — тесты никогда не ходят в продакшен. GitHub Actions гоняет
`pytest` и Spectral по `api/openapi.yaml`.

```bash
pytest
```

## Дашборд Grafana

Провайженный JSON: [`deploy/grafana/dashboards/evolute.json`](deploy/grafana/dashboards/evolute.json).
Datasource uid `evaconnect-pg`. Ряды:

| Ряд | Содержание |
|---|---|
| Обзор | Исходные девять панелей: Battery, Remaining range, Temperatures (салон/улица/батарея), 12V, Online, Central lock, Odometer, Poller heartbeat, Recent trips |
| Сейчас | Зажигание, парк, пистолет, сигнал, климат target/fan, последний снимок, каталог команд |
| Зарядка | Таймсерия пистолета |
| Климат | Охлаждающая жидкость, цель климата, вентилятор |
| Кузов | Двери, багажник, фары из JSONB `telemetry.raw` |
| Движение | Таймсерия одометра, зажигание/парк/сигнал |
| Служебные сенсоры | Fuel % / прошивка / настройки (на EV часто не используются) |
| Поездки | Доп. таблица (`battery_first`/`last`) и график дистанции/расхода. `title` в Обзоре — МСК из `start_date`/`end_date` |
| Poller | Длительность цикла и ошибки |

Адреса поездок и координаты не хранятся. См. [deploy/README.ru.md](deploy/README.ru.md).

## Пробелы в спеке (явные параметры, без догадок)

- Формат телефона / `phoneCountry` неизвестен — передавайте как строки.
- `sort.by` / `dir` поездок по умолчанию — подтверждённые живьём `DATE` / `DESC`
  (`DURATION` / `DISTANCE` и `ASC` тоже валидны).
- Единицы `distance` (м или км) неизвестны — сырой `int`, без конвертации.
- TTL access-токена неизвестен — один авто-refresh на HTTP 401, без цикла.
- Тело сессии зарядки во время зарядки полностью не описано. См.
  [api/docs/quirks.ru.md](api/docs/quirks.ru.md).
- Заголовок `Time-Zone` не используется (не подтверждён).

Полная таблица эндпоинтов и маркеры `x-status`: [api/README.ru.md](api/README.ru.md).

## Лицензия

MIT для Python-клиента, MCP-сервера и poller.

Неофициальное описание API в [`api/`](api/) — [CC0-1.0](api/LICENSE).
