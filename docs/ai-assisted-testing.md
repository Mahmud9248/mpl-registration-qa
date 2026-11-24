# AI-assisted testing

AI speeds up two parts of this project: **exploring the app** and **drafting tests**. It does
not decide what is correct. Every expected value comes from the spec, the domain model in
`src/mpl_qa/domain/`, or my own judgement, and every generated test is reviewed before it is
merged.

## Setup

The [Playwright MCP server](https://github.com/microsoft/playwright-mcp) lets an LLM agent
drive a real browser through Playwright: it clicks, types and reads the page's accessibility
tree instead of guessing from screenshots. It is configured in `.vscode/mcp.json`, so any
MCP-capable client (VS Code agent mode, or another MCP client) picks it up.

```bash
./scripts/run_local_app.sh --detach   # app under test on :8788
# open the repo in VS Code -> agent mode -> the "playwright" MCP server is listed
```

The prompts I use are versioned in `ai/prompts/` so the process can be repeated:

| Prompt | Purpose |
|--------|---------|
| `01-explore.md` | Exploratory session: happy path, then try to break every step; report observations only |
| `02-draft-tests.md` | Turn selected observations into pytest drafts that follow this repo's patterns |
| `03-review-checklist.md` | What I check before a draft is allowed into `tests/` |

## Workflow

```
 explore (agent + MCP) ──► observations table ──► I triage: bug? duplicate? noise?
                                                        │
                       review checklist ◄── drafts ◄────┘
                              │
                              ▼
                   fail-for-the-right-reason check ──► merge (bugs get a BUG-xxx + strict xfail)
```

## What this produced, and where the AI was wrong

**Useful**

* The exploratory pass flagged that tapping an already-selected payment option cleared it.
  Reproduced it in a focused script, and it became **BUG-007** (TC-PAY-006).
* Reading the accessibility tree showed that the batting-hand and bowling-type dropdowns have no
  name. axe-core confirmed it, and it became **BUG-008**.
* Drafts for the parametrised validation tables (mobile formats, missing API fields) saved
  the most typing.

**Corrected during review**

* The drafts located dropdowns with `get_by_label("Batting hand")`, which assumes the labels
  are linked to their controls. They are not (that is BUG-008), so the page object uses the
  element ids and documents why.
* The first concurrency draft started one Playwright instance per thread. Start-up time spread
  the requests out, so the race only reproduced some of the time and the strict xfail flipped
  to a pass. I rewrote it with a `threading.Barrier` so all requests leave together; it now
  reproduces 5/5.
* Generated expectations for the provisional tier were copied from what the page displayed.
  That is circular: it can never catch a scoring bug. They were replaced by the independent
  model in `domain/assessment.py`, which also handles the JavaScript-vs-Python rounding
  difference (`Math.round(80.5)` is 81; Python's `round(80.5)` is 80).
* A draft shared one API client between the anonymous and admin tests. After the admin logged
  in, the "anonymous" requests carried the session cookie and passed for the wrong reason.
  The fixtures now give each role its own isolated request context.

## Rules I keep

1. AI output is a draft, not an oracle.
2. A test that has never failed has not been tested; break the behaviour once and watch it go red.
3. Prompts live in the repo, so the process can be repeated and improved.
4. Nothing from an AI session is committed without review (`ai/sessions/` is git-ignored).
