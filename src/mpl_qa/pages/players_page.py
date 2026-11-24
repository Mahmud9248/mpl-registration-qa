from __future__ import annotations

from playwright.sync_api import Locator, Page

from mpl_qa.pages.base_page import BasePage


class PlayersPage(BasePage):
    path = "/players.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.grid = page.locator("#season7PlayerGrid")
        self.cards = self.grid.locator(".public-player-card")
        self.stats = page.locator("#directoryStats")

    def card(self, name: str) -> Locator:
        return self.cards.filter(has=self.page.get_by_role("heading", name=name, exact=True))

    def tier_of(self, name: str) -> str:
        return self.card(name).locator(".tier-badge").inner_text().strip()

    def stat(self, label: str) -> int:
        tile = self.stats.locator(".directory-stat").filter(has_text=label).first
        return int(tile.locator("strong").inner_text())
