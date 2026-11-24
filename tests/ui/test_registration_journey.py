"""TC-REG-001..010 — happy-path registration journeys (backend mocked)."""

from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import expect

from mpl_qa.data.factories import PLAYER_TYPES, PlayerFactory, PlayerType
from mpl_qa.domain.assessment import QUESTIONS
from mpl_qa.pages.registration_page import TOTAL_STEPS, RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.mocked, allure.feature("Player registration")]


@pytest.mark.smoke
@allure.title("TC-REG-001 A complete registration shows the ID and provisional tier")
def test_complete_registration(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    player = factory.build()

    result = registration_page.register(player)

    assert result.registration_id == mock_backend.published[-1]["id"]
    assert result.tier == player.expected.tier
    expect(registration_page.result.get_by_role("link", name="View Players")).to_be_visible()


@pytest.mark.regression
@pytest.mark.parametrize("player_type", PLAYER_TYPES)
@pytest.mark.parametrize("tier", ["A", "B", "C", "D"])
@allure.title("TC-REG-002 Provisional tier matches the scoring rules: {player_type} / tier {tier}")
def test_tier_matches_scoring_rules(
    registration_page: RegistrationPage,
    mock_backend: MockBackend,
    factory: PlayerFactory,
    player_type: PlayerType,
    tier: str,
) -> None:
    player = factory.with_tier(tier, player_type)

    result = registration_page.register(player)

    assert result.tier == tier
    scores = mock_backend.last_payload["scores"]
    expected = player.expected
    assert (scores["bat"], scores["bowl"], scores["field"], scores["exp"]) == (
        expected.bat,
        expected.bowl,
        expected.field,
        expected.exp,
    )
    assert scores["overall"] == pytest.approx(expected.overall)


@pytest.mark.regression
@allure.title("TC-REG-003 The submitted payload matches the API contract")
def test_payload_contract(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    player = factory.build(payment_method="Cash", cash_paid_to="Rafi", wicketkeeper=True)

    registration_page.register(player)
    sent = mock_backend.last_payload

    expected = player.to_api_payload()
    for key in (
        "name",
        "mobile",
        "playerType",
        "wicketkeeper",
        "battingHand",
        "bowlingType",
        "paymentMethod",
        "cashPaidTo",
        "provisionalTier",
        "reviewStatus",
    ):
        assert sent[key] == expected[key], key
    assert set(sent["answers"]) == {q.id for q in QUESTIONS}
    assert sent["photo"].startswith("data:image/jpeg;base64,"), "photo should be re-encoded JPEG"


@pytest.mark.regression
@allure.title("TC-REG-004 The review step shows exactly what the player entered")
def test_review_step_summary(registration_page: RegistrationPage, factory: PlayerFactory) -> None:
    player = factory.build(payment_method="Cash", cash_paid_to="Nayeem")

    registration_page.complete_until_review(player)

    assert registration_page.review_value("Full name") == player.full_name
    assert registration_page.review_value("Mobile") == player.mobile
    assert registration_page.review_value("Player type") == player.player_type
    assert registration_page.review_value("Payment method") == "Cash"
    assert registration_page.review_value("Cash paid to") == "Nayeem"


@pytest.mark.regression
@allure.title("TC-REG-005 Back navigation keeps every answer")
def test_back_navigation_preserves_answers(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    player = factory.build()
    registration_page.complete_until_review(player)

    for step in range(TOTAL_STEPS - 1, 0, -1):
        registration_page.back()
        registration_page.expect_step(step)

    expect(registration_page.full_name).to_have_value(player.full_name)
    expect(registration_page.mobile).to_have_value(player.mobile)


@pytest.mark.regression
@allure.title("TC-REG-006 The step rail tracks progress")
def test_step_rail_progress(registration_page: RegistrationPage, factory: PlayerFactory) -> None:
    player = factory.build()
    registration_page.fill_profile(player)
    registration_page.next()

    expect(registration_page.step_rail.nth(0)).to_have_class(_has("done"))
    expect(registration_page.step_rail.nth(1)).to_have_class(_has("active"))
    expect(registration_page.step_rail).to_have_count(TOTAL_STEPS)


@pytest.mark.regression
@allure.title("TC-REG-007 Unfinished registration survives a page reload (session draft)")
def test_draft_survives_reload(registration_page: RegistrationPage, factory: PlayerFactory) -> None:
    player = factory.build()
    registration_page.full_name.fill(player.full_name)
    registration_page.mobile.fill(player.mobile)
    registration_page.mobile.blur()

    registration_page.page.reload()

    expect(registration_page.full_name).to_have_value(player.full_name)
    expect(registration_page.mobile).to_have_value(player.mobile)


@pytest.mark.regression
@allure.title("TC-REG-008 'Register another player' starts a fresh form")
def test_register_another(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    registration_page.register(factory.build())

    registration_page.result.get_by_role("button", name="Register another player").click()

    registration_page.expect_step(1)
    expect(registration_page.full_name).to_have_value("")


def _has(css_class: str) -> re.Pattern[str]:
    return re.compile(rf"(^|\s){css_class}(\s|$)")
