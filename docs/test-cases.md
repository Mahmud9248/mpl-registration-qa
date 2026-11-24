# Test cases

65 test cases, which run as 121 executions once parameters are expanded. Every row is automated. The id appears in the
test's Allure title, so a failure in the report links straight back here.

Priority: **P1** blocks release · **P2** should fix before release · **P3** nice to have.

## Registration journey: `tests/ui/test_registration_journey.py`

| ID | Scenario | Steps | Expected | Pri |
|----|----------|-------|----------|-----|
| TC-REG-001 | Complete registration | Fill all 8 steps with valid data, submit, let the assessment finish | Result shows `MPL7-xxxx` id, provisional tier and "View Players" | P1 |
| TC-REG-002 | Tier calculation (12 combinations) | For each role (Batter/Bowler/All-Rounder) × tier (A–D), answer so the scoring rules give that tier | Shown tier and section scores match the independent scoring model | P1 |
| TC-REG-003 | Payload contract | Complete a registration, capture the POST body | All fields, all 16 answers, JPEG photo, tier consistent with answers | P1 |
| TC-REG-004 | Review summary | Reach step 8 | Name, mobile, role, payment and receiver match the input | P2 |
| TC-REG-005 | Back navigation | From review, press Back to step 1 | Every step reachable, inputs still filled | P2 |
| TC-REG-006 | Step rail | Finish step 1 | Step 1 marked done, step 2 active, 8 steps listed | P3 |
| TC-REG-007 | Draft restore | Type name + mobile, reload | Values restored from the session draft | P2 |
| TC-REG-008 | Register another | Finish, press "Register another player" | Fresh form at step 1 | P3 |

## Validation: `tests/ui/test_registration_validation.py`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-VAL-001 | Continue with an empty profile | Errors for photo, name, mobile; stays on step 1 | P1 |
| TC-VAL-002 | Mobile rule (10 cases) | Accept `01XXXXXXXXX`, with or without spaces and dashes; reject 10/12 digits, wrong prefix, `+880`, letters, empty | P1 |
| TC-VAL-003 | Whitespace-only name | "Please enter your full name." | P2 |
| TC-VAL-004 | Bangla, apostrophe/hyphen, 120-char names | Accepted | P2 |
| TC-VAL-005 | 2400×1600 photo | Re-encoded JPEG, cropped to 640×640, under 650 KB | P2 |
| TC-VAL-006 | Photo picker filter | `accept="image/png,image/jpeg"` | P3 |
| TC-VAL-007 | Empty role step | Errors for player type, batting hand, bowling type | P1 |
| TC-VAL-008 | One unanswered question per section (4 cases) | Only that question shows "Choose at least one answer." | P1 |
| TC-VAL-009 | Multi-select bowling role | Two roles stay selected after navigating away and back | P2 |

## Payment: `tests/ui/test_payment.py`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-PAY-001 | No method chosen | "Choose a payment method." | P1 |
| TC-PAY-002 | Cash with a blank receiver | Receiver name required | P1 |
| TC-PAY-003 | bKash | Shows ৳500 fee and the bKash number; no receiver field | P1 |
| TC-PAY-004 | Copy bKash number | Clipboard holds `01910462545`; button says "Copied ✓" | P3 |
| TC-PAY-005 | Cash → bKash | Submitted `cashPaidTo` is empty: **BUG-005** | P2 |
| TC-PAY-006 | Tap selected option again | Stays selected: **BUG-007** | P2 |

## Resilience: `tests/ui/test_resilience.py`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-NET-001 | API returns 500 / 503 / 413 / 400 | Error banner, no assessment animation, stays on review | P1 |
| TC-NET-002 | Network drops on submit | Error shown, entered data intact | P1 |
| TC-NET-003 | Retry after failure | Succeeds; exactly one record created | P1 |
| TC-NET-004 | Three failed submits | One error banner: **BUG-006** | P3 |

## Localisation and layout: `tests/ui/test_localisation_and_layout.py`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-L10N-001 | Switch to বাংলা mid-form | Headings and step rail in Bangla; typed data kept | P2 |
| TC-L10N-002 | Validation in Bangla | Bangla error messages | P2 |
| TC-L10N-003 | Full registration in Bangla | Works; stored values stay canonical English | P2 |
| TC-RWD-001 | iPhone 13, Pixel 7, Galaxy S9+ | No horizontal scroll; registration completes | P1 |

## Security (browser): `tests/ui/test_security.py`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-SEC-001 | Script payloads as the name (3 payloads) | Rendered as text on review and result; nothing executes | P1 |
| TC-SEC-002 | Script payloads as the name, on the Players page | Nothing executes | P1 |
| TC-SEC-003 | Crafted `photo` value on the Players page | Nothing executes: **BUG-003** | P1 |

## API: `tests/api/`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-API-001 | `GET /api/health` | 200, schema valid, `no-store` | P1 |
| TC-API-002 | Anonymous full list | 401 | P1 |
| TC-API-003 | Bad credentials (4 cases) | 401, no cookie | P1 |
| TC-API-004 | Session cookie flags | `HttpOnly; Secure; SameSite=Lax; Path=/` | P2 |
| TC-API-005 | Empty / garbage / forged token | 401 | P1 |
| TC-API-006 | Anonymous PATCH / DELETE | 401, record untouched | P1 |
| TC-API-010 | Create | 201, valid schema, `Pending`, no final tier | P1 |
| TC-API-011 | Create then read back | Stored record equals the response | P1 |
| TC-API-012 | Two creates | Sequential ids | P3 |
| TC-API-013 | Missing required field (5 cases) | 400. Missing `scores` is accepted: **BUG-002** | P1 |
| TC-API-014 | Malformed / empty / array / null body | 400 | P2 |
| TC-API-015 | Photo exactly at and 1 byte over 650 000 | 201 / 413 | P2 |
| TC-API-020 | 10 simultaneous creates | All 201: **BUG-001** | P1 |
| TC-API-021 | Forged tier A + Finalized | Ignored or rejected: **BUG-002** | P1 |
| TC-API-022 | Invalid mobile (3 cases) | 400: **BUG-004** | P2 |
| TC-API-030 | Finalise review | Final tier, status, notes stored; provisional tier unchanged | P1 |
| TC-API-031 | Unpublish | Gone from the public list | P1 |
| TC-API-032 | PATCH name / mobile | 400, unchanged | P2 |
| TC-API-033 | Unknown id | 404 for PATCH and DELETE | P3 |
| TC-API-034 | Delete | 200, record gone | P2 |

## End-to-end: `tests/e2e/`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-E2E-001 | Register in the browser → database → Players page | Stored record matches input; card shows the right tier | P1 |
| TC-E2E-002 | Authority sets the final tier to A | Database updated; Players page shows A | P1 |
| TC-E2E-003 | Wrong admin password | Error shown; console hidden | P1 |
| TC-E2E-004 | Sign out | Session gone, even on a fresh visit | P1 |
| TC-E2E-005 | Malicious record → Players page | No script runs: **BUG-003** | P1 |
| TC-E2E-006 | Malicious record → Authority console | No script runs: **BUG-003** | P1 |

## Accessibility: `tests/a11y/`

| ID | Scenario | Expected | Pri |
|----|----------|----------|-----|
| TC-A11Y-001 | axe audit of each wizard step (8) | No critical/serious issues. Steps 1–2 fail: **BUG-008** | P2 |
| TC-A11Y-002 | Result screen | No critical/serious issues | P2 |
| TC-A11Y-003 | Players page | No critical/serious issues | P2 |
| TC-A11Y-004 | Authority sign-in | No critical/serious issues | P2 |
| TC-A11Y-005 | Keyboard only, step 1 | Can type and continue without a mouse | P2 |
