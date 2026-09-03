# Changelog

All notable changes to this unofficial API description are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
for the OpenAPI `info.version` field.

## [Unreleased]

### Added

- OpenAPI 3.1 description of `https://app.evassist.ru` from live evaconnect
  captures (2026-08-30, 2026-09-02): auth, user, orgs, vehicles, telemetry,
  charge 404, trip search/details/filters.
- `x-status` / `x-discovered` / `x-source` / `x-notes` on every operation.
- Docs for authentication, errors, rate limits (none observed), and quirks.
- REST Client (`examples/api.http`) and Bruno collection vars
  (`examples/collection.bru`).
- Spectral lint workflow on `api/openapi.yaml`.
