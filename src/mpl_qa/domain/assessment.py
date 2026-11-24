"""Independent model of the antorAI provisional-tier rules.

This is the test oracle: it is written from the scoring specification, not imported from
the application, so a regression in the app's scoring code shows up as a mismatch here.

Rules
-----
* Every answer option carries a score. A multi-select question scores the mean of the
  selected options. An unanswered question scores 50.
* Each section (batting, bowling, fielding, experience) is the rounded mean of its questions.
* Sections are weighted by primary role, rounded to one decimal place.
* Tier thresholds: A >= 80, B >= 65, C >= 50, otherwise D.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Tier = Literal["A", "B", "C", "D"]
Answer = str | Sequence[str]


class Section(StrEnum):
    BATTING = "bat"
    BOWLING = "bowl"
    FIELDING = "field"
    EXPERIENCE = "exp"


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    section: Section
    options: tuple[tuple[str, int], ...]
    multi: bool = False

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(label for label, _ in self.options)

    def score(self, answer: Answer | None) -> float:
        lookup = dict(self.options)
        if self.multi:
            picked = [answer] if isinstance(answer, str) else list(answer or [])
            if not picked:
                return 50
            return sum(lookup.get(p, 50) for p in picked) / len(picked)
        if not isinstance(answer, str):
            return 50
        return lookup.get(answer, 50)


def _q(qid: str, section: Section, *opts: tuple[str, int], multi: bool = False) -> Question:
    return Question(qid, section, tuple(opts), multi)


S = Section
QUESTIONS: tuple[Question, ...] = (
    _q(
        "bat_frequency",
        S.BATTING,
        ("Rarely", 35),
        ("Sometimes", 55),
        ("Usually", 75),
        ("Almost every match", 92),
    ),
    _q(
        "bat_position",
        S.BATTING,
        ("Lower order", 45),
        ("Middle order", 65),
        ("Top order", 82),
        ("Opener", 90),
    ),
    _q(
        "bat_power",
        S.BATTING,
        ("Rarely look for boundaries", 35),
        ("Can clear the field sometimes", 55),
        ("Regular boundary option", 78),
        ("Major strength", 94),
    ),
    _q(
        "bat_adapt",
        S.BATTING,
        ("Prefer one only", 40),
        ("Manage with adjustments", 60),
        ("Comfortable against both", 80),
        ("Strong against both", 93),
    ),
    _q(
        "bowl_frequency",
        S.BOWLING,
        ("Rarely", 30),
        ("1–2 overs", 55),
        ("3–4 overs", 77),
        ("Regular spell", 92),
    ),
    _q(
        "bowl_control",
        S.BOWLING,
        ("Still developing", 40),
        ("Decent", 60),
        ("Reliable", 80),
        ("Very consistent", 93),
    ),
    _q(
        "bowl_role",
        S.BOWLING,
        ("New ball", 78),
        ("Middle overs", 62),
        ("Death / pressure overs", 92),
        ("Part-time option", 40),
        multi=True,
    ),
    _q(
        "bowl_wickets",
        S.BOWLING,
        ("Not often", 35),
        ("Sometimes", 58),
        ("Often", 79),
        ("Regularly", 93),
    ),
    _q(
        "field_ground",
        S.FIELDING,
        ("Basic", 45),
        ("Decent", 62),
        ("Strong", 80),
        ("Standout strength", 93),
    ),
    _q(
        "field_catching",
        S.FIELDING,
        ("Needs work", 42),
        ("Usually okay", 62),
        ("Confident", 81),
        ("Very reliable", 94),
    ),
    _q(
        "field_throw",
        S.FIELDING,
        ("Average", 48),
        ("Decent", 64),
        ("Strong arm", 81),
        ("Very accurate", 93),
    ),
    _q(
        "field_keeper",
        S.FIELDING,
        ("No", 45),
        ("Occasionally", 60),
        ("Often", 80),
        ("Primary role", 94),
    ),
    _q(
        "exp_years",
        S.EXPERIENCE,
        ("Less than 1 year", 35),
        ("1–3 years", 55),
        ("4–7 years", 77),
        ("8+ years", 92),
    ),
    _q(
        "exp_matches",
        S.EXPERIENCE,
        ("Rarely", 35),
        ("Monthly", 55),
        ("Weekly", 78),
        ("Multiple times a week", 92),
    ),
    _q(
        "exp_tournament",
        S.EXPERIENCE,
        ("Very little", 35),
        ("Some local tournaments", 58),
        ("Regular tournaments", 78),
        ("Extensive tournament experience", 93),
    ),
    _q(
        "exp_mpl",
        S.EXPERIENCE,
        ("No", 45),
        ("Yes — once", 65),
        ("Yes — more than once", 82),
        ("Yes — regular MPL player", 92),
    ),
)
QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}

# Primary role -> section weights. Anything else (All-Rounder) uses the balanced profile.
ROLE_WEIGHTS: dict[str, dict[Section, float]] = {
    "Batter": {S.BATTING: 0.55, S.FIELDING: 0.20, S.EXPERIENCE: 0.15, S.BOWLING: 0.10},
    "Bowler": {S.BOWLING: 0.55, S.FIELDING: 0.20, S.EXPERIENCE: 0.15, S.BATTING: 0.10},
    "All-Rounder": {S.BATTING: 0.40, S.BOWLING: 0.40, S.FIELDING: 0.10, S.EXPERIENCE: 0.10},
}
TIER_THRESHOLDS: tuple[tuple[float, Tier], ...] = ((80, "A"), (65, "B"), (50, "C"))


def js_round(value: float) -> int:
    """Math.round semantics (half rounds up), unlike Python's banker's rounding."""
    return math.floor(value + 0.5)


@dataclass(frozen=True, slots=True)
class Assessment:
    bat: int
    bowl: int
    field: int
    exp: int
    overall: float
    tier: Tier


def section_score(section: Section, answers: Mapping[str, Answer]) -> int:
    scores = [q.score(answers.get(q.id)) for q in QUESTIONS if q.section is section]
    return js_round(sum(scores) / len(scores))


def tier_for(overall: float) -> Tier:
    return next((tier for floor, tier in TIER_THRESHOLDS if overall >= floor), "D")


def assess(player_type: str, answers: Mapping[str, Answer]) -> Assessment:
    sections = {s: section_score(s, answers) for s in Section}
    weights = ROLE_WEIGHTS.get(player_type, ROLE_WEIGHTS["All-Rounder"])
    overall = js_round(sum(sections[s] * w for s, w in weights.items()) * 10) / 10
    return Assessment(
        bat=sections[S.BATTING],
        bowl=sections[S.BOWLING],
        field=sections[S.FIELDING],
        exp=sections[S.EXPERIENCE],
        overall=overall,
        tier=tier_for(overall),
    )
