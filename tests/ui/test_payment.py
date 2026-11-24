"""TC-PAY-001..006 — Cash / bKash branching on the payment step (backend mocked)."""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import BrowserContext, expect

from mpl_qa.data.factories import Player, PlayerFactory
from mpl_qa.pages.registration_page import PAYMENT_STEP, RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.mocked, allure.feature("Payment")]

BKASH_NUMBER = "01910462545"


def _go_to_payment(page: RegistrationPage, player: Player, *, choose: bool = True) -> None:
    page.advance_to(PAYMENT_STEP, player)
    if choose:
        page.choose_payment(player)


@pytest.mark.smoke
@allure.title("TC-PAY-001 Choosing a payment method is required")
def test_payment_method_required(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    _go_to_payment(registration_page, factory.build(), choose=False)

    registration_page.next()

    registration_page.expect_step(PAYMENT_STEP)
    expect(registration_page.error_for("paymentMethod")).to_have_text("Choose a payment method.")


@pytest.mark.regression
@allure.title("TC-PAY-002 Cash asks who received the money, and that field is required")
def test_cash_requires_receiver(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    _go_to_payment(registration_page, factory.build(payment_method="Cash", cash_paid_to="Rafi"))

    registration_page.cash_paid_to.fill("   ")
    registration_page.next()

    registration_page.expect_step(PAYMENT_STEP)
    expect(registration_page.error_for("cashPaidTo")).to_have_text(
        "Enter the name of the person who received the cash."
    )


@pytest.mark.regression
@allure.title("TC-PAY-003 bKash shows the fee and number and needs no receiver name")
def test_bkash_details(registration_page: RegistrationPage, factory: PlayerFactory) -> None:
    _go_to_payment(registration_page, factory.build(payment_method="bKash"))

    expect(registration_page.payment_details).to_contain_text("Registration fee: ৳500")
    expect(registration_page.payment_details).to_contain_text("+880 1910-462545")
    expect(registration_page.cash_paid_to).to_have_count(0)


@pytest.mark.regression
@pytest.mark.only_browser("chromium")  # clipboard permissions are Chromium-specific
@allure.title("TC-PAY-004 'Copy number' puts the bKash number on the clipboard")
def test_copy_bkash_number(
    registration_page: RegistrationPage, context: BrowserContext, factory: PlayerFactory
) -> None:
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    _go_to_payment(registration_page, factory.build(payment_method="bKash"))

    registration_page.copy_bkash.click()

    expect(registration_page.copy_bkash).to_have_text("Copied ✓")
    clipboard = registration_page.page.evaluate("navigator.clipboard.readText()")
    assert clipboard == BKASH_NUMBER


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-005: cashPaidTo is submitted even when bKash is chosen")
@allure.issue("BUG-005")
@allure.title("TC-PAY-005 Switching Cash -> bKash does not submit a stale receiver name")
def test_switching_method_clears_cash_receiver(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    cash_player = factory.build(payment_method="Cash", cash_paid_to="Rafi")
    _go_to_payment(registration_page, cash_player)

    registration_page.choose_payment(cash_player.but(payment_method="bKash"))
    registration_page.next()
    registration_page.submit()
    registration_page.wait_for_result()

    sent = mock_backend.last_payload
    assert sent["paymentMethod"] == "bKash"
    assert sent["cashPaidTo"] == "", "receiver name from the abandoned Cash choice leaked"


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-007: tapping a selected payment option deselects it")
@allure.issue("BUG-007")
@allure.title("TC-PAY-006 Tapping the already-selected payment method keeps it selected")
def test_reselecting_payment_keeps_choice(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    player = factory.build(payment_method="Cash", cash_paid_to="Rafi")
    _go_to_payment(registration_page, player)

    registration_page.choose_payment(player)  # e.g. an accidental double tap on mobile

    expect(registration_page.page.get_by_role("radio", name="Cash")).to_be_checked()
    expect(registration_page.cash_paid_to).to_be_visible()
