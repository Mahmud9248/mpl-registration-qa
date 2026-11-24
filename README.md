# MPL Season 7 · Registration QA

[![tests](https://github.com/Mahmud9248/mpl-registration-qa/actions/workflows/tests.yml/badge.svg)](https://github.com/Mahmud9248/mpl-registration-qa/actions/workflows/tests.yml)
[![Allure report](https://img.shields.io/badge/report-Allure-orange)](https://mahmud9248.github.io/mpl-registration-qa/)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Playwright](https://img.shields.io/badge/playwright-1.65-2EAD33)

Test automation for the player registration of **Mojo Premier League Season 7**, a local
cricket tournament site that runs on Cloudflare Pages + D1. Players sign up through an
8-step wizard, get a provisional tier from the "antorAI" assessment, and the tournament
authority reviews and publishes them.

This repo tests that workflow from test design through to automation: UI, API, end-to-end
and accessibility, running in CI on every push.

**Testing found 8 real bugs, including two critical ones** → [docs/bug-reports.md](docs/bug-reports.md)

| | |
|---|---|
| **Test cases** | 65 cases, 121 automated runs: [docs/test-cases.md](docs/test-cases.md) |
| **Strategy** | risks, levels, environments, data: [docs/test-strategy.md](docs/test-strategy.md) |
| **Design** | why the framework is built this way: [docs/design-notes.md](docs/design-notes.md) |
| **AI-assisted** | Playwright MCP exploration + reviewed test drafts: [docs/ai-assisted-testing.md](docs/ai-assisted-testing.md) |

## Stack

Python · pytest · Playwright (`pytest-playwright`) · Pydantic · Faker · axe-core ·
pytest-xdist · Allure · GitHub Actions · Cloudflare Wrangler (local D1) · Playwright MCP ·
ruff + mypy (strict)

## What is covered

```
tests/
├── ui/     wizard journeys, validation, Cash/bKash branching, network failures,
│           Bangla localisation, phone layouts, XSS             (backend mocked)
├── api/    contract (Pydantic), auth & sessions, validation,
│           concurrency, authority review                      (real API + local D1)
├── e2e/    register → database → Players page; authority review → public tier
└── a11y/   WCAG 2.1 AA audit of every wizard step, keyboard-only use
```

Some details I like:

* **The tier is checked against an independent scoring model**, not against what the page
  shows. All 12 role × tier combinations are covered (`src/mpl_qa/domain/assessment.py`).
* **No sleeps.** The 20-second assessment animation is skipped with Playwright's fake clock.
* **Mock backend that records the requests.** UI tests check the exact JSON the page sends, and
  can inject 500s or drop the network mid-submit.
* **Reproducible data.** Faker seeded per test; reserved phone range `0190000xxxx`; every
  record a test creates is deleted afterwards.
* **Known bugs are strict xfails.** CI stays green while a bug is documented, and goes red the
  moment it is fixed, so the test gets promoted to a regression check.
* **Never touches production.** The real app code runs locally against a throwaway database.

## Bugs found

| | Severity | |
|---|---|---|
| BUG-001 | Critical | 7–8 of 10 simultaneous registrations fail with 500 (id race) |
| BUG-003 | Critical | Stored XSS via `photo`: runs on the Players page *and* in the admin console |
| BUG-002 | High | API accepts a self-assigned tier "A" and status "Finalized" |
| BUG-004 | Medium | Mobile number not validated server-side |
| BUG-005 | Medium | Cash receiver name submitted after switching to bKash |
| BUG-007 | Medium | Tapping the selected payment option un-selects it |
| BUG-008 | Medium | Unlabelled photo input and dropdowns (screen readers) |
| BUG-006 | Low | Error banners stack on repeated failures |

## Running it

Requirements: Python 3.11+, Node 20+, and a checkout of the app
([mpl-season7](https://github.com/Mahmud9248/mpl-season7)) next to this repo.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
cp .env.example .env
```

Start the app (static site + Functions + fresh local database):

```bash
APP_DIR=../mpl-season7 ./scripts/run_local_app.sh --detach
```

Run the tests:

```bash
pytest -n auto                       # everything, in parallel (~2 min)
pytest -m smoke                      # fast critical checks
pytest tests/api                     # one layer
pytest -m known_bug --runxfail       # current state of every open bug
pytest --headed --slowmo 300 -k test_complete_registration tests/ui   # watch one journey
pytest --alluredir=allure-results && allure serve allure-results
python scripts/build_summary_report.py   # quick one-page summary -> reports/summary.html
```

Failed tests keep a Playwright trace in `test-results/`; open it with
`playwright show-trace test-results/<test>/trace.zip`.

## CI

`.github/workflows/tests.yml`

* **static-checks:** ruff, ruff format, mypy --strict
* **test:** ui / api / e2e / a11y as a parallel matrix against the real app; JUnit summary
  on the run, traces uploaded on failure
* **cross-browser** (nightly): Firefox and WebKit smoke runs
* **report:** Allure report with history, published to GitHub Pages

The workflow checks out the private app repo, so it needs one secret: `APP_REPO_TOKEN`, a
fine-grained token with read-only *Contents* access to `mpl-season7`.

## Project layout

```
src/mpl_qa/        config · domain model · data factories · API client + contracts
                   page objects · mock backend · accessibility helper
tests/             ui · api · e2e · a11y (+ shared fixtures in conftest.py)
scripts/           run_local_app.sh · purge_test_data.py
docs/              strategy · test cases · bug reports · design notes · AI-assisted testing
ai/prompts/        prompts used for exploratory sessions and test drafting
.vscode/mcp.json   Playwright MCP server for AI-assisted exploration
```
