"""TC-SEC-UI — untrusted input must never execute as script in the browser."""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import Page

from mpl_qa.data.factories import PlayerFactory
from mpl_qa.pages.players_page import PlayersPage
from mpl_qa.pages.registration_page import RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.mocked, allure.feature("Security")]

XSS_PAYLOADS = [
    '<img src=x onerror="window.__xss=1">',
    '"><svg onload="window.__xss=1">',
    "<script>window.__xss=1</script>",
]


def _xss_fired(page: Page) -> bool:
    return bool(page.evaluate("window.__xss === 1"))


@pytest.mark.regression
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=["img-onerror", "svg-onload", "script"])
@allure.title("TC-SEC-001 Script in the name field is rendered as text on review and result")
def test_name_is_escaped_in_wizard(
    registration_page: RegistrationPage,
    mock_backend: MockBackend,
    factory: PlayerFactory,
    payload: str,
) -> None:
    player = factory.build(full_name=payload)

    registration_page.complete_until_review(player)
    assert registration_page.review_value("Full name") == payload
    registration_page.submit()
    registration_page.wait_for_result()

    assert not _xss_fired(registration_page.page)


@pytest.mark.regression
@pytest.mark.parametrize("payload", XSS_PAYLOADS, ids=["img-onerror", "svg-onload", "script"])
@allure.title("TC-SEC-002 Script in a player's name is not executed on the Players page")
def test_players_page_escapes_name(page: Page, factory: PlayerFactory, payload: str) -> None:
    backend = MockBackend(page).install()
    backend.published.append(
        {
            **factory.build(full_name=payload).to_api_payload(),
            "id": "MPL7-9100",
            "createdAt": "2026-12-15T12:00:00Z",
        }
    )

    players = PlayersPage(page)
    players.open()

    players.card(payload).wait_for()
    assert not _xss_fired(page)


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-003: photo is interpolated into <img src> without escaping")
@allure.issue("BUG-003")
@allure.title("TC-SEC-003 A crafted photo value cannot inject script on the Players page")
def test_players_page_escapes_photo(page: Page, factory: PlayerFactory) -> None:
    backend = MockBackend(page).install()
    record = factory.build().to_api_payload()
    record.update(
        id="MPL7-9101", createdAt="2026-12-15T12:00:00Z", photo='x" onerror="window.__xss=1'
    )
    backend.published.append(record)

    players = PlayersPage(page)
    players.open()
    players.cards.first.wait_for()
    page.wait_for_load_state("networkidle")

    assert not _xss_fired(page)
