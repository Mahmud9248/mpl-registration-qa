"""In-browser fake of /api/registrations built on Playwright request routing.

UI tests use it to (1) isolate the front end from the database, (2) capture the exact
payload the page sends so it can be checked against the contract, and (3) inject failures
— 500s, timeouts, slow responses — that are hard to provoke on a real server.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from playwright.sync_api import Page, Route


@dataclass
class MockBackend:
    page: Page
    status: int = 201
    delay_ms: int = 0
    abort: bool = False
    received: list[dict[str, Any]] = field(default_factory=list)
    published: list[dict[str, Any]] = field(default_factory=list)
    _ids: itertools.count[int] = field(default_factory=lambda: itertools.count(9001))

    def install(self) -> MockBackend:
        self.page.route("**/api/registrations*", self._handle)
        return self

    # -- failure injection -------------------------------------------------------------------
    def fail_with(self, status: int) -> None:
        self.status = status

    def go_offline(self) -> None:
        self.abort = True

    # -- assertions --------------------------------------------------------------------------
    @property
    def last_payload(self) -> dict[str, Any]:
        assert self.received, "The page never called POST /api/registrations"
        return self.received[-1]

    # -- route handler -----------------------------------------------------------------------
    def _handle(self, route: Route) -> None:
        req = route.request
        if req.method == "GET":
            route.fulfill(json={"registrations": self.published})
            return
        if req.method != "POST":
            route.fallback()
            return
        body = json.loads(req.post_data or "{}")
        self.received.append(body)
        if self.delay_ms:
            self.page.wait_for_timeout(self.delay_ms)
        if self.abort:
            route.abort("internetdisconnected")
            return
        if self.status >= 400:
            route.fulfill(status=self.status, json={"error": "Injected failure"})
            return
        saved = {
            **body,
            "id": f"MPL7-{next(self._ids):04d}",
            "createdAt": datetime.now(UTC).isoformat(),
        }
        self.published.append(saved)
        route.fulfill(status=201, json={"registration": saved})
