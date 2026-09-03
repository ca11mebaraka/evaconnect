# Как дополнять

[English](CONTRIBUTING.md)

Это дерево описывает **reverse-engineered** закрытый companion API. Критерий —
доказательства, не полнота.

## Правила

1. Не добавляйте эндпоинт, поле, заголовок или код статуса, которые не
   наблюдали. Если нужно набросать форму, ставьте `x-status: guessed` и
   скажите об этом в `x-notes`.
2. `verified` требует живой вызов (HAR, curl или evaconnect) с датой в
   `x-discovered` и указателем в `x-source`.
3. `partial`, если вызов был, но тело, статус или набор полей неполны
   (charge 200, flags 200, статус sign-up).
4. Вырезайте токены, cookies, телефоны, VIN, IMEI, координаты, id аккаунтов
   и email из захватов и примеров. Используйте `<YOUR_TOKEN>`,
   `00000000000`, `aaaaaaaaaaaaaaaaaaaaaaaa`, `user@example.com`.
5. Источник истины — `openapi.yaml`. В том же изменении обновляйте таблицу
   эндпоинтов в README и `docs/quirks.md` (и русские копии `*.ru.md`).
6. Английские файлы в этом каталоге — канон. Русские `*.ru.md` — перевод;
   не добавляйте в них факты, которых нет в английской версии.

## Захваты

Кладёте отредактированный HAR или curl в `captures/`. Каталог в gitignore
кроме `.gitkeep`. Сырые экспорты приложения не коммитить.

## Lint

Из корня репозитория:

```bash
npx --yes @stoplight/spectral-cli lint api/openapi.yaml
```

GitHub Actions запускает ту же команду на push и pull request.
