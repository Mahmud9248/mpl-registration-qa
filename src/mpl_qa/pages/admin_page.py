from __future__ import annotations

from typing import Literal

from playwright.sync_api import Locator, Page, expect

from mpl_qa.pages.base_page import BasePage

StatusFilter = Literal["all", "pending", "finalized", "hidden"]


class AdminPage(BasePage):
    """Authority console (/admin.html): sign-in, review queue and per-player review panel."""

    path = "/admin.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username = page.locator("#adminUsername")
        self.password = page.locator("#adminPassword")
        self.sign_in_button = page.get_by_role("button", name="Sign in")
        self.login_error = page.locator("#adminLoginError")
        self.console = page.locator("#adminApp")
        self.search = page.locator("#playerSearch")
        self.status_filter = page.locator("#statusFilter")
        self.queue = page.locator("#adminPlayerList .admin-player-item")
        self.detail = page.locator("#adminDetail")
        self.final_tier = page.locator("#finalTier")
        self.notes = page.locator("#authorityNotes")
        self.save_button = page.locator("#savePlayer")
        self.publish_toggle_button = page.locator("#togglePublish")
        self.delete_button = page.locator("#deletePlayer")
        self.save_status = page.locator("#saveStatus")
        self.sign_out_button = page.locator("#logoutBtn")

    def sign_in(self, username: str, password: str) -> None:
        self.username.fill(username)
        self.password.fill(password)
        self.sign_in_button.click()

    def expect_signed_in(self) -> None:
        expect(self.console).to_be_visible()

    def queue_item(self, registration_id: str) -> Locator:
        return self.page.locator(
            f"#adminPlayerList .admin-player-item[data-id='{registration_id}']"
        )

    def open_registration(self, registration_id: str) -> None:
        self.queue_item(registration_id).click()
        expect(self.detail).to_contain_text(registration_id)

    def finalize(self, tier: str, notes: str = "") -> None:
        self.final_tier.select_option(tier)
        if notes:
            self.notes.fill(notes)
        with self.page.expect_response(
            lambda r: "/api/registrations/" in r.url and r.request.method == "PATCH"
        ) as resp:
            self.save_button.click()
        assert resp.value.ok, f"Saving review failed: {resp.value.status}"
