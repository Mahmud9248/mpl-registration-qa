# Bug reports

Defects found while testing the Season 7 registration workflow. Each one has an automated test
marked `known_bug` + `xfail(strict=True)`: it is expected to fail while the bug exists, and the
build goes red as soon as the bug is fixed so the marker gets removed and the test becomes a
normal regression check.

Environment for all reports: `mpl-season7` @ `main`, served locally with `wrangler pages dev`
and a fresh local D1 database; Chromium via Playwright 1.65, Ubuntu.

| ID | Title | Severity | Area | Test |
|----|-------|----------|------|------|
| BUG-001 | Simultaneous registrations fail with 500 | **Critical** | API | TC-API-020 |
| BUG-002 | Server trusts client-supplied tier, scores and review status | **High** | API / security | TC-API-021, TC-API-013 |
| BUG-003 | Stored XSS through the `photo` field (Players page + Authority console) | **Critical** | Security | TC-SEC-003, TC-E2E-005, TC-E2E-006 |
| BUG-004 | Mobile number is validated only in the browser | Medium | API | TC-API-022 |
| BUG-005 | Cash receiver name is kept after switching to bKash | Medium | Payment | TC-PAY-005 |
| BUG-006 | Error banners pile up on repeated submit failures | Low | UI | TC-NET-004 |
| BUG-007 | Tapping the selected payment option un-selects it | Medium | Payment / mobile | TC-PAY-006 |
| BUG-008 | Photo input and two dropdowns have no accessible name | Medium | Accessibility | TC-A11Y-001 |

---

## BUG-001 — Simultaneous registrations fail with 500

**Severity:** Critical: registrations are lost on launch day, exactly when traffic peaks.

**Steps**
1. Send 10 valid `POST /api/registrations` requests at the same instant
   (TC-API-020 uses a thread barrier to release them together).

**Expected:** 10 × `201 Created`, 10 distinct ids.
**Actual:** typically 2–3 × `201` and 7–8 × `500`. Reproduced 5/5 runs, e.g.
`[500, 500, 500, 201, 500, 500, 201, 500, 500, 500]`.

**Cause:** `nextRegistrationId()` reads `MAX(id) + 1` and a separate statement inserts it.
Concurrent requests read the same max and all but one hit the primary-key constraint.
The player sees "Registration could not be saved".

**Suggested fix:** let the database allocate the number (an `INTEGER PRIMARY KEY AUTOINCREMENT`
sequence column, format the `MPL7-0001` display id from it), or retry on constraint failure.

---

## BUG-002 — Server trusts client-supplied tier, scores and review status

**Severity:** High: anyone can skip the assessment and the Authority review.

**Steps**
1. `POST /api/registrations` with a valid body but `"provisionalTier": "A"`,
   `"reviewStatus": "Finalized"` and answers that score tier D.
2. Read the record back as admin.

**Expected:** the server computes the tier from the answers, and every new record starts as `Pending`.
**Actual:** record stored with tier **A** and status **Finalized**. Omitting `scores` entirely
is also accepted, because the server defaults it to `{}`, which passes the "required" check.

**Suggested fix:** compute `scores`/`provisionalTier` on the server from `answers`, and ignore
`reviewStatus`, `finalTier`, `published` and `authorityNotes` on public create.

---

## BUG-003 — Stored XSS through the `photo` field

**Severity:** Critical (security).

**Steps**
1. `POST /api/registrations` with a valid body and
   `"photo": "x\" onerror=\"window.__xss=1"`.
2. Open `/players.html`, or sign in to `/admin.html`.

**Expected:** the value is treated as data; nothing executes.
**Actual:** the script runs on the public Players page **and inside the Authority console
with an authenticated admin session**. The session cookie is `HttpOnly`, but injected code
does not need to read it: same-origin `fetch` calls carry it, so the script can modify or
delete every registration.

**Cause:** `players-live.js` and `admin.js` build `<img src="${r.photo}">` with no escaping,
and the API accepts any string as `photo`.

**Suggested fix:** escape the attribute (`esc(r.photo)`) or build the `<img>` with DOM APIs, and
make the API accept only `data:image/(jpeg|png);base64,` values.

---

## BUG-004 — Mobile number is validated only in the browser

**Severity:** Medium.

**Steps:** `POST /api/registrations` with `"mobile": "abc"`.
**Expected:** `400` with a validation message (same rule as the form: `^01\d{9}$`).
**Actual:** `201 Created`; the Authority sees an unusable contact number.

---

## BUG-005 — Cash receiver name is kept after switching to bKash

**Severity:** Medium: the Authority sees contradictory payment information.

**Steps**
1. On the payment step choose **Cash** and type a receiver name, e.g. "Rafi".
2. Change your mind and choose **bKash**. The receiver field disappears.
3. Submit.

**Expected:** `paymentMethod: "bKash"`, `cashPaidTo: ""`.
**Actual:** `paymentMethod: "bKash"`, `cashPaidTo: "Rafi"`.

---

## BUG-006 — Error banners pile up on repeated submit failures

**Severity:** Low.

**Steps:** make the API fail (e.g. offline), then press **Submit** three times.
**Expected:** one error message.
**Actual:** three identical red banners stacked under the form.

---

## BUG-007 — Tapping the selected payment option un-selects it

**Severity:** Medium on mobile, where double taps are common.

**Steps:** on the payment step tap **Cash** and then tap **Cash** again.
**Expected:** Cash stays selected (standard radio-button behaviour).
**Actual:** nothing is selected and the "Cash paid to" field disappears, along with what was typed.

---

## BUG-008 — Photo input and two dropdowns have no accessible name

**Severity:** Medium: screen-reader users cannot tell what these fields are (WCAG 2.1
1.3.1 / 4.1.2; axe rules `label` and `select-name`, impact *critical*).

**Where:** `#profilePhoto` (step 1), `#battingHand` and `#bowlingType` (step 2). The visible
`<label>` elements are siblings without a `for` attribute.

**Suggested fix:** add `for="profilePhoto"`, `for="battingHand"` and `for="bowlingType"` to the existing labels.
