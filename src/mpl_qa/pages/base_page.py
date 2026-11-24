from __future__ import annotations

from typing import Literal

from playwright.sync_api import Locator, Page

Language = Literal["en", "bn"]


class BasePage:
    path = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self) -> BasePage:
        self.page.goto(self.path)
        return self

    def nav_link(self, name: str) -> Locator:
        return self.page.get_by_role("navigation", name="MPL navigation").get_by_role(
            "link", name=name
        )

    def switch_language(self, lang: Language) -> None:
        self.page.locator(f".lang-btn[data-lang='{lang}']").click()
