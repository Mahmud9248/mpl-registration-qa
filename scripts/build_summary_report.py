"""Build a single, dependency-free HTML summary from allure-results/.

    pytest --alluredir=allure-results
    python scripts/build_summary_report.py            # -> reports/summary.html

The full Allure report is the place for steps, traces and history. This page is the quick
look: totals, a breakdown by area, and every test in a filterable table. It is plain HTML and a
few lines of inline JS, so it opens anywhere, including viewers that block external scripts.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BUG = re.compile(r"BUG-\d{3}")


def load(results_dir: Path) -> list[dict[str, object]]:
    rows = []
    for f in results_dir.glob("*-result.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        labels = {lb["name"]: lb["value"] for lb in d.get("labels", [])}
        details = d.get("statusDetails") or {}
        message = (details.get("message") or "").strip()
        known_bug = d["status"] == "skipped" and message.startswith("XFAIL")
        status = "known bug" if known_bug else d["status"]
        params = ", ".join(
            f"{p['name']}={p['value']}"
            for p in d.get("parameters", [])
            if p["name"] != "browser_name"
        )
        rows.append(
            {
                "name": d["name"],
                "params": params,
                "status": status,
                "area": labels.get("parentSuite", "").removeprefix("tests."),
                "feature": labels.get("feature", ""),
                "ms": max(0, d.get("stop", 0) - d.get("start", 0)),
                "start": d.get("start", 0),
                "stop": d.get("stop", 0),
                "bug": (BUG.search(message) or [""])[0] if known_bug else "",
                "message": message.removeprefix("XFAIL ").split("\n")[0][:300],
            }
        )
    rows.sort(key=lambda r: (r["area"], r["name"], r["params"]))
    return rows


CSS = """
:root{--bg:#f6f7f5;--panel:#fff;--fg:#17211b;--muted:#5d6b62;--line:#dde3de;--accent:#0f6b45;
--pass:#1f8a4c;--pass-bg:#e3f3e9;--bug:#9a5b00;--bug-bg:#fbf0dc;--fail:#b42318;--fail-bg:#fde7e5;
--mono:"JetBrains Mono",ui-monospace,Menlo,monospace;--sans:"Inter",system-ui,sans-serif;
--display:"Space Grotesk","Inter",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1512;--panel:#16201b;
--fg:#e5ece7;--muted:#9aaba0;--line:#26332c;--accent:#4cc38a;--pass:#4cc38a;--pass-bg:#15301f;
--bug:#f0b35a;--bug-bg:#33270f;--fail:#ff8a80;--fail-bg:#3a1714;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f1512;--panel:#16201b;--fg:#e5ece7;--muted:#9aaba0;--line:#26332c;
--accent:#4cc38a;--pass:#4cc38a;--pass-bg:#15301f;--bug:#f0b35a;--bug-bg:#33270f;--fail:#ff8a80;
--fail-bg:#3a1714;color-scheme:dark}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:14px/1.5 var(--sans);margin:0}
.wrap{max-width:1100px;margin:0 auto;padding-block:32px 48px;
padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1{font:600 28px/1.2 var(--display);margin:0;text-wrap:balance}h2{font:600 17px var(--display);margin:0 0 12px}
.sub{color:var(--muted);margin:6px 0 24px}.mono{font-family:var(--mono);font-size:12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.tile small{display:block;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-size:11px}
.tile b{font:600 30px var(--display);font-variant-numeric:tabular-nums}
.tile.pass b{color:var(--pass)}.tile.bug b{color:var(--bug)}.tile.fail b{color:var(--fail)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
@media (max-width:760px){.grid2{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
.bar-row{display:grid;grid-template-columns:120px 1fr 64px;gap:10px;align-items:center;margin:8px 0}
.bar{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--line)}
.bar i{display:block;height:100%}.bar .p{background:var(--pass)}.bar .k{background:var(--bug)}.bar .f{background:var(--fail)}
.num{text-align:right;font-variant-numeric:tabular-nums;color:var(--muted)}
.bugs li{margin:6px 0}.bugs{padding-left:18px;margin:0}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.controls input,.controls select{font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px;
background:var(--panel);color:var(--fg)}.controls input{flex:1;min-width:200px}
.controls :focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.table-wrap{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;min-width:680px}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}td.t{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.pill.passed{background:var(--pass-bg);color:var(--pass)}.pill.known{background:var(--bug-bg);color:var(--bug)}
.pill.failed,.pill.broken{background:var(--fail-bg);color:var(--fail)}
.why{color:var(--muted);font-size:12px;margin-top:2px}.params{color:var(--muted)}
footer{color:var(--muted);font-size:12px;margin-top:20px}
"""

JS = """
const q=document.getElementById('q'),a=document.getElementById('area'),s=document.getElementById('status');
const rows=[...document.querySelectorAll('tbody tr')],count=document.getElementById('count');
function apply(){const t=q.value.toLowerCase();let n=0;rows.forEach(r=>{const ok=
(!t||r.textContent.toLowerCase().includes(t))&&(!a.value||r.dataset.area===a.value)&&
(!s.value||r.dataset.status===s.value);r.hidden=!ok;if(ok)n++});count.textContent=n+' shown'}
[q,a,s].forEach(e=>e.addEventListener('input',apply));apply();
"""


def render(rows: list[dict[str, object]], title: str) -> str:
    e = html.escape
    totals = Counter(r["status"] for r in rows)
    by_area: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        by_area[str(r["area"])][str(r["status"])] += 1
    start = min(int(r["start"]) for r in rows) / 1000
    wall = (max(int(r["stop"]) for r in rows) - min(int(r["start"]) for r in rows)) / 1000
    failed = totals["failed"] + totals["broken"]
    bugs: dict[str, str] = {}
    for r in rows:
        if r["bug"] and r["bug"] not in bugs:
            bugs[str(r["bug"])] = str(r["message"]).split(": ", 1)[-1]

    bars = "".join(
        f'<div class="bar-row"><span>{e(area)}</span><div class="bar">'
        f'<i class="p" style="width:{c["passed"] / sum(c.values()) * 100:.1f}%"></i>'
        f'<i class="k" style="width:{c["known bug"] / sum(c.values()) * 100:.1f}%"></i>'
        f'<i class="f" style="width:{(c["failed"] + c["broken"]) / sum(c.values()) * 100:.1f}%"></i>'
        f'</div><span class="num">{c["passed"]}/{sum(c.values())}</span></div>'
        for area, c in sorted(by_area.items())
    )
    bug_list = "".join(
        f"<li><b class='mono'>{e(b)}</b> {e(m)}</li>" for b, m in sorted(bugs.items())
    )
    body = "".join(
        f'<tr data-area="{e(str(r["area"]))}" data-status="{e(str(r["status"]))}">'
        f'<td><span class="pill {e(str(r["status"]).split()[0])}">{e(str(r["status"]))}</span></td>'
        f"<td>{e(str(r['name']))}"
        + (f' <span class="params mono">[{e(str(r["params"]))}]</span>' if r["params"] else "")
        + (
            f'<div class="why">{e(str(r["message"]))}</div>'
            if r["bug"] or r["status"] in ("failed", "broken")
            else ""
        )
        + f"</td><td>{e(str(r['area']))}</td><td>{e(str(r['feature']))}</td>"
        f'<td class="t">{int(r["ms"]) / 1000:.1f}s</td></tr>'
        for r in rows
    )
    areas = "".join(f'<option value="{e(a)}">{e(a)}</option>' for a in sorted(by_area))
    return f"""<title>{e(title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono&family=Space+Grotesk:wght@600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<h1>{e(title)}</h1>
<p class="sub">MPL Season 7 player registration · run {datetime.fromtimestamp(start):%d %b %Y, %H:%M} · {wall:.0f}s wall time</p>
<div class="tiles">
<div class="tile"><small>Tests run</small><b>{len(rows)}</b></div>
<div class="tile pass"><small>Passed</small><b>{totals["passed"]}</b></div>
<div class="tile bug"><small>Known bugs (expected fail)</small><b>{totals["known bug"]}</b></div>
<div class="tile fail"><small>Unexpected failures</small><b>{failed}</b></div>
</div>
<div class="grid2">
<section class="panel"><h2>By test layer</h2>{bars}</section>
<section class="panel"><h2>Open bugs pinned by tests</h2><ul class="bugs">{bug_list or "<li>None</li>"}</ul></section>
</div>
<h2>All tests</h2>
<div class="controls">
<input id="q" type="search" placeholder="Search name, TC id, bug…" aria-label="Search tests">
<select id="area" aria-label="Layer"><option value="">All layers</option>{areas}</select>
<select id="status" aria-label="Status"><option value="">All statuses</option>
<option value="passed">passed</option><option value="known bug">known bug</option>
<option value="failed">failed</option><option value="broken">broken</option></select>
<span id="count" class="num" style="align-self:center"></span>
</div>
<div class="table-wrap"><table><thead><tr><th>Status</th><th>Test</th><th>Layer</th>
<th>Feature</th><th style="text-align:right">Time</th></tr></thead><tbody>{body}</tbody></table></div>
<footer>Generated from allure-results by scripts/build_summary_report.py. Full report with steps and traces: Allure.</footer>
</div>
<script>{JS}</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=Path("allure-results"))
    ap.add_argument("--out", type=Path, default=Path("reports/summary.html"))
    ap.add_argument("--title", default="Registration Test Run")
    args = ap.parse_args()
    rows = load(args.results)
    if not rows:
        raise SystemExit(f"no results in {args.results}; run pytest --alluredir={args.results}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(rows, args.title), encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} tests)")


if __name__ == "__main__":
    main()
