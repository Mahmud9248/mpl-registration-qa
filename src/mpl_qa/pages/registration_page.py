"""Page object for /registration.html — an eight-step wizard followed by the antorAI result.

Locator strategy: the wizard renders inputs inside custom "choice cards", and several
labels are not programmatically linked to their controls (see BUG-004). Where a role or
label locator is not possible we anchor on stable ids / data-attributes rather than CSS
classes that exist only for styling.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from playwright.sync_api import Locator, Page, expect

from mpl_qa.data.factories import Player
from mpl_qa.domain.assessment import QUESTIONS, Answer, Section
from mpl_qa.pages.base_page import BasePage
from mpl_qa.support.images import file_payload, png

TOTAL_STEPS = 8
PAYMENT_STEP = 7
ANTORAI_ANIMATION_MS = 30_000
DATA_URL = re.compile(r"^data:image/")
SECTION_STEPS = {Section.BATTING: 3, Section.BOWLING: 4, Section.FIELDING: 5, Section.EXPERIENCE: 6}


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    registration_id: str
    tier: str
    text: str


class RegistrationPage(BasePage):
    path = "/registration.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.form = page.locator("#playerRegistrationForm")
        self.active_step = page.locator(".step-pane.active")
        self.step_rail = page.locator("#stepList .step-item")
        self.next_button = self.active_step.locator("[data-next]")
        self.back_button = self.active_step.locator("[data-back]")
        self.photo_input = page.locator("#profilePhoto")
        self.photo_preview = page.locator("#photoPreview")
        self.full_name = page.locator("#fullName")
        self.mobile = page.locator("#mobile")
        self.batting_hand = page.locator("#battingHand")
        self.bowling_type = page.locator("#bowlingType")
        self.wicketkeeper = page.locator("label[for='wicketkeeperRole']")
        self.payment_details = page.locator("#paymentDetails")
        self.cash_paid_to = page.locator("#cashPaidTo")
        self.copy_bkash = page.locator("#copyBkashNumber")
        self.review = page.locator("#reviewContent")
        self.antorai_stage = page.locator("#antorAIStage")
        self.result = page.locator("#registrationResult")
        self.reveal_button = page.locator("#revealRating")
        self.error_banner = page.locator(".status-banner.error")

    # -- navigation --------------------------------------------------------------------------
    def current_step(self) -> int:
        return int(self.active_step.get_attribute("data-step") or 0)

    def next(self) -> None:
        self.next_button.click()

    def back(self) -> None:
        self.back_button.click()

    def expect_step(self, step: int) -> None:
        expect(self.active_step).to_have_attribute("data-step", str(step))

    # -- step 1: profile ---------------------------------------------------------------------
    def upload_photo(
        self, data: bytes | None = None, name: str = "player.png", mime: str = "image/png"
    ) -> None:
        self.photo_input.set_input_files(file_payload(name, data or png(), mime))  # type: ignore[arg-type]
        # The page crops/compresses on a canvas asynchronously; wait for the data URL.
        expect(self.photo_preview).to_have_attribute("src", DATA_URL)

    def fill_profile(self, player: Player, *, photo: bool = True) -> None:
        if photo:
            self.upload_photo()
        self.full_name.fill(player.full_name)
        self.mobile.fill(player.mobile)

    # -- step 2: cricket role ----------------------------------------------------------------
    def choose_role(self, player: Player) -> None:
        self._choice("playerType", player.player_type).click()
        if player.wicketkeeper:
            self.wicketkeeper.click()
        self.batting_hand.select_option(player.batting_hand)
        self.bowling_type.select_option(player.bowling_type)

    # -- steps 3-6: assessment questions -----------------------------------------------------
    def answer(self, question_id: str, answer: Answer) -> None:
        picks: Sequence[str] = [answer] if isinstance(answer, str) else answer
        name = f"{question_id}[]" if not isinstance(answer, str) else question_id
        for option in picks:
            self._choice(name, option).click()

    def answer_section(self, section: Section, answers: dict[str, Answer]) -> None:
        for q in QUESTIONS:
            if q.section is section and q.id in answers:
                self.answer(q.id, answers[q.id])

    # -- step 7: payment ---------------------------------------------------------------------
    def choose_payment(self, player: Player) -> None:
        self._choice("paymentMethod", player.payment_method).click()
        if player.payment_method == "Cash" and self.cash_paid_to.is_visible():
            self.cash_paid_to.fill(player.cash_paid_to)

    # -- whole journey -----------------------------------------------------------------------
    def advance_to(self, step: int, player: Player) -> None:
        """Fill every step before ``step`` with ``player``'s data and stop on ``step``."""
        sections = {n: sec for sec, n in SECTION_STEPS.items()}
        while (current := self.current_step()) < step:
            if current == 1:
                self.fill_profile(player)
            elif current == 2:
                self.choose_role(player)
            elif current in sections:
                self.answer_section(sections[current], player.answers)
            elif current == PAYMENT_STEP:
                self.choose_payment(player)
            self.next()
            self.expect_step(current + 1)

    def complete_until_review(self, player: Player) -> None:
        self.advance_to(TOTAL_STEPS, player)

    def submit(self) -> None:
        self.expect_step(TOTAL_STEPS)
        self.next()

    def wait_for_result(self) -> RegistrationResult:
        """Skip the ~20 s antorAI animation with the fake clock installed by the fixture.

        The page may stop on a "View Your Rating" reveal card before the final result;
        both paths are handled so the test does not depend on animation timing.
        """
        expect(self.antorai_stage).to_be_visible()
        final = self.page.locator("#registrationResult.is-final")
        # Jump in 1 s hops: each hop fires the next chained setTimeout without rendering
        # every intermediate animation frame (run_for would, and costs ~3 s of CPU).
        for _ in range(ANTORAI_ANIMATION_MS // 1000):
            if self.reveal_button.is_visible() or final.is_visible():
                break
            self.page.clock.fast_forward(1000)
        expect(self.reveal_button.or_(final)).to_be_visible()
        if self.reveal_button.is_visible():
            self.reveal_button.click()
        expect(final).to_be_visible()
        return RegistrationResult(
            registration_id=self.result.locator(".result-id").inner_text().strip(),
            tier=self.result.locator(".result-tier").inner_text().strip(),
            text=self.result.inner_text(),
        )

    def register(self, player: Player) -> RegistrationResult:
        self.complete_until_review(player)
        self.submit()
        return self.wait_for_result()

    # -- validation helpers ------------------------------------------------------------------
    def error_for(self, field: str) -> Locator:
        return self.page.locator(f"[data-error='{field}']")

    def visible_errors(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for el in self.active_step.locator(".error-text").all():
            text = el.inner_text().strip()
            if text:
                out[el.get_attribute("data-error") or "?"] = text
        return out

    def review_value(self, label: str) -> str:
        """Value shown next to a label on the review step, e.g. review_value('Mobile')."""
        text = self.review.inner_text()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, ln in enumerate(lines[:-1]):
            if ln.casefold() == label.casefold():
                return lines[i + 1]
        raise AssertionError(f"{label!r} not found on review step:\n{text}")

    def _choice(self, input_name: str, value: str) -> Locator:
        return self.active_step.locator(
            f".choice:has(input[name='{input_name}'][value='{value}']) label"
        )
