# Design notes

Why the framework looks the way it does. These are the decisions I would expect to be asked about.

## Layout

```
src/mpl_qa/            reusable library, imported by tests (installed via pythonpath)
  config.py            settings from env / .env
  domain/assessment.py independent model of the antorAI scoring rules (the test oracle)
  data/factories.py    seeded Faker-based Player builder
  api/                 typed API client + Pydantic response contracts
  pages/               page objects: registration wizard, admin console, players page
  support/             mock backend, axe wrapper, in-memory image generator
tests/                 ui / api / e2e / a11y; tests only call fixtures and page objects
scripts/               run the app locally, purge leftover test data
ai/  .vscode/mcp.json  AI-assisted exploration (see ai-assisted-testing.md)
```

Tests read like specifications. Everything with "how" in it (selectors, waits, HTTP details)
lives in `src/`.

## Page objects

* One class per page, and methods that describe what a user does: `choose_payment(player)`,
  `advance_to(step, player)`, `register(player)`.
* The page object never asserts business rules; it only waits for the UI to be ready.
  The tests do the asserting.
* `advance_to(step, player)` lets any test start at any wizard step with valid data, so each
  test only spells out the part it is actually checking.

## Locators

Priority: **role / label → stable id or data attribute → CSS**. The wizard renders custom
"choice cards" (a hidden radio plus a styled label), so choices are located by the radio's
`name` and `value`, which are stable and language-independent. The same test works in English
and Bangla. The labels for some controls are not linked to their inputs (BUG-008), so
those use ids.

## Three ways of handling the backend

1. **Mocked** (`MockBackend`, route interception): UI tests don't depend on a database, run in
   parallel without interfering with each other, and can simulate 500s, timeouts and offline.
   The mock also **records the payload**, so TC-REG-003 checks the front end against the API contract.
2. **Real local stack**: `wrangler pages dev` runs the real Functions code with a local D1. The
   API and E2E tests run here. Same code as production, but the database is thrown away.
3. **Never production.** Data-writing tests are skipped automatically if `BASE_URL` points there.

## Test oracle for the tier

The provisional tier is the most important output of the wizard. Comparing it with whatever the
page shows would prove nothing, so `domain/assessment.py` implements the scoring rules
separately (weights per role, thresholds A ≥ 80, B ≥ 65, C ≥ 50). TC-REG-002 checks all 12
role × tier combinations. `PlayerFactory.with_tier()` searches for answers that land on a
requested tier, using a seeded random search so the data is reproducible. One subtle point:
JavaScript's `Math.round` rounds .5 up and Python's `round` rounds half to even, so the model
has its own `js_round`.

## Time

The assessment screen animates for about 20 seconds. Waiting that long in every test would
cost many minutes per run, so the `registration_page` fixture installs Playwright's **fake
clock** and `wait_for_result()` jumps time forward in 1-second steps. The browser also runs
with `reduced_motion="reduce"`, which the site honours. Together these took the suite from
7m23s to about 2 minutes on a 4-core machine.

## Test data and isolation

* `factory` is seeded from the test's node id: same test → same data → a failure can be replayed.
* `cleanup` deletes what each test created, pass or fail.
* `public_api` and `admin_api` use separate request contexts, so cookies cannot leak between
  roles. This was a real bug in an early draft: anonymous calls were secretly authenticated.

## Known bugs as strict xfails

`@pytest.mark.xfail(strict=True)` + `known_bug` + `allure.issue("BUG-00x")`:

* The suite stays green while a bug is open and documented.
* When a developer fixes the bug, the test **unexpectedly passes** and strict mode fails the
  build, prompting someone to remove the marker. The test then becomes a regression check.
* `pytest -m known_bug --runxfail` shows the current status of every open bug.

## Things I would add next

* Visual regression for the result card (needs stable fonts in CI first).
* A k6 load profile for opening night, once BUG-001 is fixed.
* Contract tests shared with the app repo so API changes fail in its own CI.
