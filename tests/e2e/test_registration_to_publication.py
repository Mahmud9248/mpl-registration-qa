"""TC-E2E — complete business journeys across the public site, the API and the Authority console.

No mocks: the browser talks to the real Pages Functions backend and its D1 database.
"""

from __future__ import annotations

from collections.abc import Callable

import allure
import pytest
from playwright.sync_api import Browser, expect

from mpl_qa.api.client import RegistrationApi
from mpl_qa.config import Settings
from mpl_qa.data.factories import PlayerFactory
from mpl_qa.pages.admin_page import AdminPage
from mpl_qa.pages.players_page import PlayersPage
from mpl_qa.pages.registration_page import RegistrationPage

pytestmark = [pytest.mark.e2e, allure.feature("End-to-end journeys")]


@pytest.mark.smoke
@allure.title("TC-E2E-001 Register -> stored in the database -> listed on the Players page")
def test_registration_is_persisted_and_listed(
    registration_page: RegistrationPage,
    admin_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Callable[[str], str],
) -> None:
    player = factory.build()

    with allure.step("Player registers through the website"):
        result = registration_page.register(player)
        cleanup(result.registration_id)

    with allure.step("The database holds exactly what the player entered"):
        stored = admin_api.get(result.registration_id)
        assert stored is not None
        assert (stored.name, stored.mobile, stored.playerType) == (
            player.full_name,
            player.mobile,
            player.player_type,
        )
        assert stored.provisionalTier == result.tier == player.expected.tier
        assert stored.answers == {
            k: (v if isinstance(v, str) else list(v)) for k, v in player.answers.items()
        }
        assert stored.photo.startswith("data:image/jpeg;base64,")

    with allure.step("The player appears on the public Players page"):
        players = PlayersPage(registration_page.page)
        players.open()
        expect(players.card(player.full_name)).to_be_visible()
        assert players.tier_of(player.full_name) == result.tier


@pytest.mark.regression
@allure.title("TC-E2E-002 Authority finalises a different tier and the Players page follows")
def test_authority_review_changes_public_tier(
    browser: Browser,
    base_url: str,
    settings: Settings,
    admin_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Callable[[str], str],
) -> None:
    player = factory.with_tier("C", "Batter")
    reg = admin_api.create(player.to_api_payload())
    cleanup(reg.id)

    # The admin works in their own browser context — separate cookies from the public user.
    admin_ctx = browser.new_context(base_url=base_url)
    try:
        admin = AdminPage(admin_ctx.new_page())
        admin.open()
        admin.sign_in(settings.admin_username, settings.admin_password)
        admin.expect_signed_in()
        admin.open_registration(reg.id)
        admin.finalize("A", notes="Promoted after trial match")
    finally:
        admin_ctx.close()

    stored = admin_api.get(reg.id)
    assert stored is not None
    assert (stored.finalTier, stored.reviewStatus) == ("A", "Finalized")
    assert stored.authorityNotes == "Promoted after trial match"

    public_ctx = browser.new_context(base_url=base_url)
    try:
        players = PlayersPage(public_ctx.new_page())
        players.open()
        expect(players.card(player.full_name).locator(".tier-badge")).to_have_text("A")
    finally:
        public_ctx.close()


@pytest.mark.regression
@allure.title("TC-E2E-003 Wrong Authority password is refused with a visible error")
def test_admin_login_failure(admin_page: AdminPage, settings: Settings) -> None:
    admin_page.open()

    admin_page.sign_in(settings.admin_username, "definitely-not-the-password")

    expect(admin_page.login_error).not_to_be_empty()
    expect(admin_page.console).to_be_hidden()


@pytest.mark.regression
@allure.title("TC-E2E-004 Signing out ends the Authority session")
def test_admin_sign_out(admin_page: AdminPage, settings: Settings) -> None:
    admin_page.open()
    admin_page.sign_in(settings.admin_username, settings.admin_password)
    admin_page.expect_signed_in()

    admin_page.sign_out_button.click()
    expect(admin_page.sign_in_button).to_be_visible()

    admin_page.open()  # a fresh visit must not restore the old session
    expect(admin_page.sign_in_button).to_be_visible()
    expect(admin_page.console).to_be_hidden()


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-003: stored XSS via the photo field on the Players page")
@allure.issue("BUG-003")
@allure.title("TC-E2E-005 A malicious registration cannot run script for Players page visitors")
def test_stored_xss_through_real_backend(
    players_page: PlayersPage,
    public_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Callable[[str], str],
) -> None:
    body = {**factory.build().to_api_payload(), "photo": 'x" onerror="window.__xss=1'}
    cleanup(public_api.create(body).id)

    players_page.open()
    players_page.cards.first.wait_for()
    players_page.page.wait_for_load_state("networkidle")

    assert not players_page.page.evaluate("window.__xss === 1"), "attacker script executed"


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-003: stored XSS via the photo field in the Authority console")
@allure.issue("BUG-003")
@allure.title("TC-E2E-006 A malicious registration cannot run script in the admin's session")
def test_stored_xss_in_authority_console(
    admin_page: AdminPage,
    settings: Settings,
    public_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Callable[[str], str],
) -> None:
    body = {**factory.build().to_api_payload(), "photo": 'x" onerror="window.__xss=1'}
    reg_id = cleanup(public_api.create(body).id)

    admin_page.open()
    admin_page.sign_in(settings.admin_username, settings.admin_password)
    expect(admin_page.queue_item(reg_id)).to_be_visible()
    admin_page.page.wait_for_load_state("networkidle")

    assert not admin_page.page.evaluate("window.__xss === 1"), (
        "attacker script executed with an authenticated admin session"
    )
