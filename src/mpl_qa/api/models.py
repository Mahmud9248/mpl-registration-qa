"""Response contracts for /api/*. A schema drift fails validation with a precise field path."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

REGISTRATION_ID = re.compile(r"^MPL7-\d{4,}$")


class Scores(BaseModel):
    model_config = ConfigDict(extra="allow")
    bat: int | None = None
    bowl: int | None = None
    field: int | None = None
    exp: int | None = None
    overall: float | None = None
    tier: str | None = None


class Registration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    createdAt: datetime
    name: str
    mobile: str
    playerType: str
    wicketkeeper: bool
    battingHand: str
    bowlingType: str
    paymentMethod: str
    cashPaidTo: str
    photo: str
    answers: dict[str, str | list[str]]
    scores: Scores
    provisionalTier: Literal["A", "B", "C", "D"]
    finalTier: Literal["", "A", "B", "C", "D"]
    reviewStatus: str
    published: bool
    authorityNotes: str
    publicEdit: dict[str, object]

    @field_validator("id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not REGISTRATION_ID.match(v):
            raise ValueError(f"unexpected registration id format: {v!r}")
        return v


class RegistrationEnvelope(BaseModel):
    registration: Registration


class RegistrationList(BaseModel):
    registrations: list[Registration]


class ErrorBody(BaseModel):
    error: str = Field(min_length=1)


class Health(BaseModel):
    ok: Literal[True]
    service: str
