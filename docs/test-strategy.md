# Test strategy: MPL Season 7 player registration

## What is being tested

The public **Player Registration** wizard (`/registration.html`), the API behind it
(`/api/registrations`, `/api/auth/*`), and the two places a registration ends up: the
**Authority console** (`/admin.html`) and the public **Players** page (`/players.html`).

```
Player ──► 8-step wizard ──► POST /api/registrations ──► D1 database
             │                                              │
             └─ antorAI animation + provisional tier        ├─► Authority console: review, final tier, publish
                                                            └─► Players page: public directory
```

Out of scope: the auction pages, the season archive, Cloudflare platform behaviour.

## Risks, and how they are covered

| Risk | Likelihood | Impact | Covered by |
|------|-----------|--------|------------|
| A player cannot finish registering (validation, navigation, payment branch) | Medium | High | UI journeys, validation tests, payment tests |
| Wrong provisional tier | Medium | High | TC-REG-002: every role × tier against an independent scoring model |
| Registrations lost under load on opening night | Medium | **Critical** | TC-API-020 (concurrency) |
| Data tampering / injection by a malicious user | Low–Medium | **Critical** | API contract and security tests, XSS tests |
| Authority changes not reflected publicly | Low | High | TC-E2E-002 |
| Unusable on phones or for Bangla speakers | Medium | Medium | Device emulation, localisation tests |
| Excludes screen-reader users | Medium | Medium | axe-core audits on every step |

## Test levels

| Level | Backend | Why | Runs |
|-------|---------|-----|------|
| **UI (mocked)** | Playwright route interception | Fast and deterministic. Can inject 500s, timeouts and offline failures, and records the exact payload the page sends | every push |
| **API** | Real Functions + local D1 | Contract (Pydantic), auth, validation, concurrency | every push |
| **End-to-end** | Real Functions + local D1 | Business journeys across the public site, the database and the admin console | every push |
| **Accessibility** | Mocked | WCAG 2.1 AA via axe-core, keyboard-only completion | every push |
| **Cross-browser** | Mocked | Firefox + WebKit smoke | nightly |

## Environments

Tests never write to production. `scripts/run_local_app.sh` serves the real application code
(static pages and Pages Functions) with a throwaway **local D1** database, both locally and in CI.
An extra guard in `tests/conftest.py` skips every data-writing test if `BASE_URL` points at
the production domain.

## Test data

* Generated with Faker through `PlayerFactory`, **seeded from the test id**, so a failure
  replays with identical data. The seed is attached to the Allure report.
* All generated mobiles use the reserved range `0190000xxxx`; `scripts/purge_test_data.py`
  can find and remove anything left behind.
* Every record a test creates is deleted by the `cleanup` fixture, whether the test passes or fails.

## Entry / exit criteria

* **Entry:** the app starts and `/api/health` answers.
* **Exit for a release:** no failures in smoke/regression. Known bugs are tracked as strict
  xfails. A Critical bug (currently BUG-001 and BUG-003) should block release.

## Flakiness policy

* No fixed sleeps. Every wait is a web-first assertion (`expect(...)`) or uses Playwright's fake clock.
* The ~20 s antorAI animation is skipped with `page.clock` rather than waited out.
* CI retries once, and only on `TimeoutError`. A test that fails twice is a real failure.
