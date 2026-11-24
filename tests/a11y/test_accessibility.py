"""TC-A11Y — WCAG 2.1 AA audits (axe-core) on every wizard step and the public pages.

Only critical/serious findings fail a test; moderate/minor ones are attached to the report.
"""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from mpl_qa.data.factories import PlayerFactory
from mpl_qa.pages.admin_page import AdminPage
from mpl_qa.pages.players_page import PlayersPage
from mpl_qa.pages.registration_page import TOTAL_STEPS, RegistrationPage
from mpl_qa.support.a11y import audit, format_report
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.a11y, pytest.mark.mocked, allure.feature("Accessibility")]

UNLABELLED_CONTROLS = pytest.mark.xfail(
    reason="BUG-008: photo input and the two selects have no accessible name"
)


def _assert_clean(page: Page, context: str | None = None) -> None:
    allure.attach(
        format_report(audit(page, impacts=("moderate", "minor"), context=context)),
        "non-blocking findings",
        allure.attachment_type.TEXT,
    )
    blocking = audit(page, context=context)
    assert not blocking, "Accessibility violations:\n" + format_report(blocking)


@pytest.mark.regression
@pytest.mark.parametrize(
    "step",
    [
        pytest.param(1, marks=[pytest.mark.known_bug, UNLABELLED_CONTROLS]),
        pytest.param(2, marks=[pytest.mark.known_bug, UNLABELLED_CONTROLS]),
        *range(3, TOTAL_STEPS + 1),
    ],
)
@allure.title("TC-A11Y-001 Wizard step {step} has no critical/serious WCAG violations")
def test_wizard_step(
    registration_page: RegistrationPage, factory: PlayerFactory, step: int
) -> None:
    player = factory.build(payment_method="Cash", cash_paid_to="Rafi")
    registration_page.advance_to(step, player)
    if step == 7:
        registration_page.choose_payment(player)  # audit the expanded Cash details too

    _assert_clean(registration_page.page, context="#playerRegistrationForm")


@pytest.mark.regression
@allure.title("TC-A11Y-002 The antorAI result screen is accessible")
def test_result_screen(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    registration_page.register(factory.build())

    _assert_clean(registration_page.page, context="#registrationResult")


@pytest.mark.regression
@allure.title("TC-A11Y-003 The Players page is accessible")
def test_players_page(
    players_page: PlayersPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    mock_backend.published.append(
        {**factory.build().to_api_payload(), "id": "MPL7-9200", "createdAt": "2026-12-15T12:00:00Z"}
    )
    players_page.open()
    players_page.cards.first.wait_for()

    _assert_clean(players_page.page)


@pytest.mark.regression
@allure.title("TC-A11Y-004 The Authority sign-in page is accessible")
def test_admin_login_page(admin_page: AdminPage) -> None:
    admin_page.open()

    _assert_clean(admin_page.page)


@pytest.mark.regression
@allure.title("TC-A11Y-005 The wizard can be completed with the keyboard alone")
def test_keyboard_only_profile_step(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    player = factory.build()
    registration_page.upload_photo()
    page = registration_page.page

    registration_page.full_name.focus()
    page.keyboard.type(player.full_name)
    page.keyboard.press("Tab")
    page.keyboard.type(player.mobile)
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")

    registration_page.expect_step(2)
