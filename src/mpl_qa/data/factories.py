"""Test-data builders.

Every generated player uses a mobile number from the reserved range ``0190000xxxx`` so test
records are recognisable at a glance and can be purged safely (see scripts/purge_test_data.py).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Literal, Self

from faker import Faker

from mpl_qa.domain.assessment import QUESTIONS, Answer, Assessment, assess

PlayerType = Literal["Batter", "Bowler", "All-Rounder"]
PaymentMethod = Literal["Cash", "bKash"]
BowlingType = Literal["Off spin", "Leg spin", "Other spin", "No regular bowling"]

TEST_MOBILE_PREFIX = "0190000"
PLAYER_TYPES: tuple[PlayerType, ...] = ("Batter", "Bowler", "All-Rounder")

_fake = Faker()


def reserved_mobile(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{TEST_MOBILE_PREFIX}{r.randint(0, 9999):04d}"


@dataclass(frozen=True, slots=True)
class Player:
    full_name: str
    mobile: str
    player_type: PlayerType
    batting_hand: Literal["Right", "Left"]
    bowling_type: BowlingType
    answers: dict[str, Answer]
    payment_method: PaymentMethod
    cash_paid_to: str = ""
    wicketkeeper: bool = False
    tags: frozenset[str] = field(default_factory=frozenset)

    @property
    def expected(self) -> Assessment:
        return assess(self.player_type, self.answers)

    def but(self, **changes: object) -> Self:
        """Return a copy with some fields changed: ``player.but(payment_method="bKash")``."""
        return replace(self, **changes)  # type: ignore[arg-type]

    def to_api_payload(self) -> dict[str, object]:
        """The JSON body the registration page sends to POST /api/registrations."""
        a = self.expected
        return {
            "name": self.full_name,
            "mobile": self.mobile,
            "playerType": self.player_type,
            "wicketkeeper": self.wicketkeeper,
            "battingHand": self.batting_hand,
            "bowlingType": self.bowling_type,
            "paymentMethod": self.payment_method,
            "cashPaidTo": self.cash_paid_to if self.payment_method == "Cash" else "",
            "photo": "",
            "answers": {q.id: self.answers.get(q.id, "") for q in QUESTIONS},
            "scores": {
                "bat": a.bat,
                "bowl": a.bowl,
                "field": a.field,
                "exp": a.exp,
                "overall": a.overall,
                "tier": a.tier,
            },
            "provisionalTier": a.tier,
            "reviewStatus": "Pending",
            "published": True,
        }


class PlayerFactory:
    """Builds valid players. Seeded, so a failing test can be replayed with the same data."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.faker = Faker()
        self.faker.seed_instance(seed)

    def answers(self, level: int | None = None) -> dict[str, Answer]:
        """Answer every question. ``level`` 0-3 picks that option everywhere; None is random."""
        out: dict[str, Answer] = {}
        for q in QUESTIONS:
            idx = self.rng.randrange(len(q.options)) if level is None else level
            out[q.id] = [q.labels[idx]] if q.multi else q.labels[idx]
        return out

    def build(self, **overrides: object) -> Player:
        method: PaymentMethod = self.rng.choice(("Cash", "bKash"))
        base = Player(
            full_name=self.faker.name(),
            mobile=reserved_mobile(self.rng),
            player_type=self.rng.choice(PLAYER_TYPES),
            batting_hand=self.rng.choice(("Right", "Left")),
            bowling_type=self.rng.choice(
                ("Off spin", "Leg spin", "Other spin", "No regular bowling")
            ),
            answers=self.answers(),
            payment_method=method,
            cash_paid_to=self.faker.first_name() if method == "Cash" else "",
        )
        return base.but(**overrides) if overrides else base

    def with_tier(
        self, tier: str, player_type: PlayerType = "All-Rounder", attempts: int = 2_000
    ) -> Player:
        """A player whose answers land in ``tier`` for ``player_type``.

        Tries uniform answer levels first (readable data), then a seeded random search,
        so the result is still reproducible from the test's seed.
        """
        for level in [*range(4), *([None] * attempts)]:
            candidate = self.build(player_type=player_type, answers=self.answers(level))
            if candidate.expected.tier == tier:
                return candidate
        raise ValueError(f"No answer set produces tier {tier} for {player_type}")
