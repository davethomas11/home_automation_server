# Samsung TV Integration Prompt (Architecture-Aligned)

Use this prompt in your IDE AI to generate implementation diffs that fit this codebase.

## Prompt

```text
You are extending an existing FastAPI + SQLModel home automation server that is currently Apple-TV-centric.

IMPORTANT:
- Inspect the existing project structure first.
- Preserve backward compatibility for current Apple TV routes and flows.
- Return only focused diffs/new files; do not rewrite unrelated modules.

Current architecture to align with:
- SQLModel models in `home_automation_server/models/models.py`
- Routers under `home_automation_server/api/` (`devices.py`, `controls.py`, `apps.py`, `automations.py`, `webhooks.py`, `ui.py`)
- Service layer under `home_automation_server/services/` (`pyatv_service.py`, `automation_engine.py`)
- Device operations are currently database-driven by `device_id` (not room registry)

Goal:
Add Samsung TV support in a way that scales to additional device types later (Roku/LG/etc.) without route explosion.

Requirements:

1) Multi-device foundation (minimal refactor, maximum compatibility)
- Introduce a provider abstraction layer:
  - `DeviceKind` enum (at least `APPLE_TV`, `SAMSUNG_TV`)
  - `DeviceCapability` enum
  - `BaseDeviceProvider` protocol/ABC with async methods for shared controls
- Keep existing Apple TV behavior through an adapter/provider wrapper over current pyatv logic.
- Avoid global mutable singleton state; use dependency-injected factories/resolvers.

2) Samsung provider implementation
- Add `SamsungTVProvider` service using:
  - `samsungtvws` for model years 2016-2023
  - `py-samsungtv` for 2024+
- Constructor should accept host, port, display name, model_year (plus optional auth/token fields if needed).
- Provide unified async methods:
  - `power_on`, `power_off`
  - `volume_up`, `volume_down`, `mute`, `unmute`
  - `home`, `back`, `play`, `pause`
  - `launch_app(app_id)`, `send_key(key)`
- Create normalized key enum/mapping (e.g. `SamsungTVKey`) so routes/automations use stable internal names.
- Handle unsupported methods with typed exceptions and capability checks.

3) Data model + migration integration
- Extend schema to support multiple device kinds while keeping current Apple TV records valid.
- Add Alembic migration(s) for any schema changes.
- Keep `AutomationFlow` compatible and ensure execution dispatches by device kind.

4) API integration
- Keep existing routes working:
  - `/devices/*`
  - `/controls/*`
  - `/apps/*`
  - `/automations/*`
- Extend control/app behavior so Samsung devices execute via the provider resolver based on device kind.
- Add a launch endpoint consistent with existing style, e.g.:
  - `POST /device/{device_id}/launch/{app_id}`
  - or a route under `/apps` if that fits existing router conventions better
- If new generic endpoints are added, keep legacy endpoints as compatibility aliases.

5) Automation engine integration
- Update `automation_engine.py` to route actions through provider abstractions by device kind.
- Preserve current payload formats where possible.
- Document Samsung-specific payload fields only when necessary.

6) Quality, tests, and docs
- Strong typing, async-first methods, concise logging, robust error-to-HTTP mapping.
- Add/update tests for:
  - Samsung device create/list/get/delete
  - command dispatch for Samsung
  - app launch endpoint for Samsung
  - automation sequence dispatch by device kind
- Update dependency manifest (`pyproject.toml`) with Samsung libraries.
- Add brief docs section in `README.md` for Samsung setup and limitations.

Output format:
1. Show changed/new files only (diff-style snippets).
2. Brief rationale per file.
3. Include migration name and upgrade/downgrade snippets.
4. Include runnable test command(s).
5. Do not print unrelated files.
```

## Optional Follow-up Prompt (Phase-by-Phase)

```text
Implement in 3 PR-sized phases:
- Phase 1: Provider abstractions + Apple adapter + schema extension
- Phase 2: Samsung provider + API wiring + tests
- Phase 3: Automation dispatch refactor + docs + cleanup
For each phase, return: files changed, risks, and rollback notes.
```

## Acceptance Checklist

- [ ] Existing Apple TV tests still pass
- [ ] New Samsung tests pass
- [ ] Alembic migration applies cleanly on a fresh DB
- [ ] Existing `/controls/*` and `/apps/*` endpoints remain functional
- [ ] Samsung launch + command endpoints work by `device_id`
- [ ] Automation flow dispatches to correct provider by device kind

