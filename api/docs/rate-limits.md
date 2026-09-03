# Rate limits

[Русский](rate-limits.ru.md)

No server-side rate limit, quota header, or HTTP 429 was observed in the
2026-08-30 / 2026-09-02 captures.

Do not infer a limit from evaconnect:

- Telemetry HTTP cache in the client is **5 seconds** (`MIN_TELEMETRY_INTERVAL_S`).
  That is a client guard, not a documented API rule.
- The optional poller defaults to 30 s telemetry / 900 s trips. Same caveat.

If you measure `Retry-After`, 429, or WAF throttling, record status, headers,
and the endpoint in `openapi.yaml` as `partial` until reproduced twice.
