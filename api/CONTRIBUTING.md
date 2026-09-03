# Contributing

[Русский](CONTRIBUTING.ru.md)

This tree documents a **reverse-engineered** private companion API. The bar
is evidence, not completeness.

## Rules

1. Do not add an endpoint, field, header, or status code that you did not
   observe. If you must sketch a shape, set `x-status: guessed` and say so
   in `x-notes`.
2. `verified` requires a live call (HAR, curl, or evaconnect) with date in
   `x-discovered` and a pointer in `x-source`.
3. `partial` if the call happened but the body, status, or field set is
   incomplete (charge 200, flags 200, sign-up status).
4. Strip tokens, cookies, phone numbers, VIN, IMEI, coordinates, account
   ids, and emails from captures and examples. Use `<YOUR_TOKEN>`,
   `00000000000`, `aaaaaaaaaaaaaaaaaaaaaaaa`, `user@example.com`.
5. Keep `openapi.yaml` as the source of truth. Update README endpoint table
   and `docs/quirks.md` in the same change (and the `*.ru.md` translations).
6. English files in this directory are canonical. Russian `*.ru.md` files are
   translations; do not add facts there that are missing from English.

## Captures

Drop redacted HAR or curl under `captures/`. The directory is gitignored
except `.gitkeep`. Do not commit raw app exports.

## Lint

From the repository root:

```bash
npx --yes @stoplight/spectral-cli lint api/openapi.yaml
```

GitHub Actions runs the same command on push and pull request.
