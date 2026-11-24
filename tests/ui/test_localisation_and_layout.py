"""TC-L10N / TC-RWD — Bangla language support and small-screen layout."""

from __future__ import annotations

import re

import allure
import pytest
from playwright.sync_api import Browser, expect

from mpl_qa.data.factories import PlayerFactory
from mpl_qa.pages.registration_page import RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.mocked]

BENGALI = re.compile(r"[\u0980-\u09FF]{3,}")


@pytest.mark.regression
@allure.feature("Localisation")
@allure.title("TC-L10N-001 Switching to Bangla translates the wizard and keeps typed data")
def test_switch_to_bangla(registration_page: RegistrationPage, factory: PlayerFactory) -> None:
    player = factory.build()
    registration_page.full_name.fill(player.full_name)

    registration_page.switch_language("bn")

    heading = registration_page.active_step.get_by_role("heading", level=2)
    expect(heading).to_have_text(BENGALI)
    expect(heading).not_to_have_text("Player profile")
    expect(registration_page.step_rail.first).to_contain_text(BENGALI)
    expect(registration_page.full_name).to_have_value(player.full_name)


@pytest.mark.regression
@allure.feature("Localisation")
@allure.title("TC-L10N-002 Validation messages are shown in Bangla")
def test_bangla_validation_messages(registration_page: RegistrationPage) -> None:
    registration_page.switch_language("bn")

    registration_page.next()

    expect(registration_page.error_for("fullName")).to_have_text("পূর্ণ নাম দিন।")
    expect(registration_page.error_for("mobile")).to_have_text("সঠিক বাংলাদেশি মোবাইল নম্বর দিন।")


@pytest.mark.regression
@allure.feature("Localisation")
@allure.title("TC-L10N-003 A full registration works end to end in Bangla")
def test_register_in_bangla(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    player = factory.build()
    registration_page.switch_language("bn")

    result = registration_page.register(player)

    assert result.tier == player.expected.tier
    # Stored values stay canonical English regardless of UI language.
    assert mock_backend.last_payload["playerType"] == player.player_type


@pytest.mark.regression
@pytest.mark.only_browser("chromium")  # device emulation with isMobile is Chromium-only
@allure.feature("Responsive layout")
@pytest.mark.parametrize("device", ["iPhone 13", "Pixel 7", "Galaxy S9+"])
@allure.title("TC-RWD-001 Registration completes on {device} without horizontal scrolling")
def test_mobile_devices(
    browser: Browser,
    playwright_devices: dict[str, dict[str, object]],
    base_url: str,
    factory: PlayerFactory,
    device: str,
) -> None:
    profile = {k: v for k, v in playwright_devices[device].items() if k != "default_browser_type"}
    context = browser.new_context(**profile, base_url=base_url)  # type: ignore[arg-type]
    try:
        page = context.new_page()
        page.clock.install()
        MockBackend(page).install()
        registration = RegistrationPage(page)
        registration.open()

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0, f"page scrolls sideways by {overflow}px on {device}"

        result = registration.register(factory.build())
        assert result.registration_id.startswith("MPL7-")
    finally:
        context.close()


@pytest.fixture(scope="session")
def playwright_devices(playwright):  # type: ignore[no-untyped-def]
    return playwright.devices
