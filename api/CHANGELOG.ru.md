# Журнал изменений

[English](CHANGELOG.md)

Здесь фиксируются заметные изменения этого неофициального описания API.

Формат — [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
для поля OpenAPI `info.version` используется
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Добавлено

- Описание OpenAPI 3.1 для `https://app.evassist.ru` по живым захватам
  evaconnect (2026-08-30, 2026-09-02): auth, пользователь, организации,
  автомобили, телеметрия, charge 404, поиск/детали/фильтры поездок.
- `x-status` / `x-discovered` / `x-source` / `x-notes` на каждой операции.
- Документация по авторизации, ошибкам, лимитам (не наблюдались) и особенностям.
- REST Client (`examples/api.http`) и переменные коллекции Bruno
  (`examples/collection.bru`).
- Spectral lint workflow на `api/openapi.yaml`.
