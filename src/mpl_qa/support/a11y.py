"""axe-core audits with readable failure output."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import Page

BLOCKING_IMPACTS = ("critical", "serious")
_axe = Axe()


@dataclass(frozen=True, slots=True)
class Violation:
    rule: str
    impact: str
    help: str
    targets: tuple[str, ...]

    def __str__(self) -> str:
        where = ", ".join(self.targets[:5])
        return f"[{self.impact}] {self.rule}: {self.help} -> {where}"


def audit(
    page: Page, *, impacts: Iterable[str] = BLOCKING_IMPACTS, context: str | None = None
) -> list[Violation]:
    """Run axe (WCAG 2.x A/AA rules) and return violations at the given impact levels."""
    options = {"runOnly": {"type": "tag", "values": ["wcag2a", "wcag2aa", "wcag21aa"]}}
    response = _axe.run(page, context=context, options=options).response
    wanted = set(impacts)
    return [
        Violation(
            v["id"], v["impact"], v["help"], tuple(t for n in v["nodes"] for t in n["target"])
        )
        for v in response["violations"]
        if v["impact"] in wanted
    ]


def format_report(violations: list[Violation]) -> str:
    return "\n".join(str(v) for v in violations) or "no violations"
