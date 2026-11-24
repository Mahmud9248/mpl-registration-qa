"""TC-NET-001..004 — behaviour when the backend misbehaves (failures injected via routing)."""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import expect

from mpl_qa.data.factories import PlayerFactory
from mpl_qa.pages.registration_page import RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

pytestmark = [pytest.mark.mocked, allure.feature("Resilience")]

SAVE_ERROR = "Registration could not be saved. Please check your connection and try again."


@pytest.mark.smoke
@pytest.mark.parametrize("status", [500, 503, 413, 400])
@allure.title("TC-NET-001 A server error ({status}) is shown and the player stays on review")
def test_server_error_is_reported(
    registration_page: RegistrationPage,
    mock_backend: MockBackend,
    factory: PlayerFactory,
    status: int,
) -> None:
    mock_backend.fail_with(status)
    registration_page.complete_until_review(factory.build())

    registration_page.submit()

    expect(registration_page.error_banner).to_have_text(SAVE_ERROR)
    expect(registration_page.antorai_stage).to_be_hidden()
    registration_page.expect_step(8)


@pytest.mark.regression
@allure.title("TC-NET-002 Losing the connection on submit keeps the player's data")
def test_offline_submit_keeps_data(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    player = factory.build()
    mock_backend.go_offline()
    registration_page.complete_until_review(player)

    registration_page.submit()

    expect(registration_page.error_banner).to_be_visible()
    assert registration_page.review_value("Full name") == player.full_name


@pytest.mark.regression
@allure.title("TC-NET-003 Retrying after a failure succeeds and registers exactly once")
def test_retry_after_failure(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    mock_backend.fail_with(503)
    registration_page.complete_until_review(factory.build())
    registration_page.submit()
    expect(registration_page.error_banner).to_be_visible()

    mock_backend.fail_with(0)
    registration_page.submit()
    registration_page.wait_for_result()

    assert len(mock_backend.published) == 1


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-006: repeated failures stack duplicate error banners")
@allure.issue("BUG-006")
@allure.title("TC-NET-004 Repeated failures show one error message, not a pile of them")
def test_repeated_failures_single_banner(
    registration_page: RegistrationPage, mock_backend: MockBackend, factory: PlayerFactory
) -> None:
    mock_backend.fail_with(500)
    registration_page.complete_until_review(factory.build())

    for _ in range(3):
        registration_page.submit()
        expect(registration_page.error_banner.first).to_be_visible()

    expect(registration_page.error_banner).to_have_count(1)
