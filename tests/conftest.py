"""Shared fixtures. Test files only ask for what they need: a page object, a player, an API."""

from __future__ import annotations

import hashlib
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

import allure
import pytest
from playwright.sync_api import APIRequestContext, Page, Playwright

from mpl_qa.api.client import RegistrationApi
from mpl_qa.config import Settings, get_settings
from mpl_qa.data.factories import Player, PlayerFactory
from mpl_qa.pages.admin_page import AdminPage
from mpl_qa.pages.players_page import PlayersPage
from mpl_qa.pages.registration_page import RegistrationPage
from mpl_qa.support.mock_backend import MockBackend

WRITES_DATA = ("e2e", "api")


# --------------------------------------------------------------------------------------------
# Session guards
# --------------------------------------------------------------------------------------------
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Refuse to run data-writing tests against production, whatever the CLI flags say."""
    settings = get_settings()
    if not settings.is_production:
        return
    guard = pytest.mark.skip(reason="data-writing tests never run against production")
    for item in items:
        if any(item.get_closest_marker(m) for m in WRITES_DATA):
            item.add_marker(guard)


def pytest_sessionstart(session: pytest.Session) -> None:
    if session.config.option.collectonly:
        return
    url = f"{get_settings().base_url}/api/health"
    try:
        urllib.request.urlopen(url, timeout=10)
    except OSError as exc:
        pytest.exit(
            f"App under test is not reachable at {url} ({exc}). "
            "Start it with scripts/run_local_app.sh or set BASE_URL.",
            returncode=3,
        )


# --------------------------------------------------------------------------------------------
# Browser configuration
# --------------------------------------------------------------------------------------------
@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    return settings.base_url


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any], settings: Settings
) -> dict[str, Any]:
    if settings.chromium_executable:
        return {**browser_type_launch_args, "executable_path": settings.chromium_executable}
    return browser_type_launch_args


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any]) -> dict[str, Any]:
    return {
        **browser_context_args,
        # The site honours prefers-reduced-motion; turning its decorative CSS animations off
        # removes most rendering work and makes screenshots stable.
        "reduced_motion": "reduce",
        "locale": "en-US",
        "timezone_id": "Asia/Dhaka",
        "viewport": {"width": 1366, "height": 900},
    }


@pytest.fixture(autouse=True)
def _fail_on_page_errors(request: pytest.FixtureRequest) -> Iterator[None]:
    """Any uncaught JavaScript exception fails the UI test that triggered it."""
    if "page" not in request.fixturenames:
        yield
        return
    page: Page = request.getfixturevalue("page")
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    yield
    assert not errors, f"Uncaught JavaScript errors: {errors}"


# --------------------------------------------------------------------------------------------
# Test data
# --------------------------------------------------------------------------------------------
@pytest.fixture
def factory(request: pytest.FixtureRequest) -> PlayerFactory:
    """Deterministic per test: same test name -> same generated data, so failures replay."""
    seed = int(hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:8], 16)
    allure.dynamic.parameter("data seed", seed)
    return PlayerFactory(seed)


@pytest.fixture
def player(factory: PlayerFactory) -> Player:
    return factory.build()


# --------------------------------------------------------------------------------------------
# Page objects
# --------------------------------------------------------------------------------------------
@pytest.fixture
def registration_page(page: Page) -> RegistrationPage:
    # Fake clock: lets tests fast-forward the antorAI animation instead of sleeping ~20 s.
    page.clock.install()
    rp = RegistrationPage(page)
    rp.open()
    return rp


@pytest.fixture
def mock_backend(page: Page) -> MockBackend:
    return MockBackend(page).install()


@pytest.fixture
def players_page(page: Page) -> PlayersPage:
    return PlayersPage(page)


@pytest.fixture
def admin_page(page: Page) -> AdminPage:
    return AdminPage(page)


# --------------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------------
def _new_api_context(playwright: Playwright, settings: Settings) -> APIRequestContext:
    return playwright.request.new_context(base_url=settings.base_url)


@pytest.fixture
def api_context(playwright: Playwright, settings: Settings) -> Iterator[APIRequestContext]:
    """A fresh cookie jar per test, for tests that log in or inspect auth behaviour."""
    ctx = _new_api_context(playwright, settings)
    yield ctx
    ctx.dispose()


@pytest.fixture(scope="session")
def public_api(playwright: Playwright, settings: Settings) -> Iterator[RegistrationApi]:
    """Anonymous caller. Never logs in, so its cookie jar can never hold an admin session."""
    ctx = _new_api_context(playwright, settings)
    yield RegistrationApi(ctx)
    ctx.dispose()


@pytest.fixture(scope="session")
def admin_api(playwright: Playwright, settings: Settings) -> Iterator[RegistrationApi]:
    ctx = _new_api_context(playwright, settings)
    yield RegistrationApi(ctx).login(settings.admin_username, settings.admin_password)
    ctx.dispose()


@pytest.fixture
def cleanup(admin_api: RegistrationApi) -> Iterator[Callable[[str], str]]:
    """Register created ids with ``cleanup(id)``; they are deleted after the test, pass or fail."""
    ids: list[str] = []

    def track(reg_id: str) -> str:
        ids.append(reg_id)
        return reg_id

    yield track
    for reg_id in ids:
        admin_api.delete(reg_id)
