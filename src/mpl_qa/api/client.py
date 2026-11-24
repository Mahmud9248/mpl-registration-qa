"""Thin, typed wrapper over Playwright's APIRequestContext for the registration API."""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import APIRequestContext, APIResponse

from mpl_qa.api.models import Registration, RegistrationEnvelope, RegistrationList

SESSION_COOKIE = "mpl_admin_session"


class ApiError(AssertionError):
    def __init__(self, response: APIResponse) -> None:
        super().__init__(f"{response.url} -> {response.status}: {response.text()[:300]}")
        self.response = response


class RegistrationApi:
    def __init__(self, request: APIRequestContext, session: str | None = None) -> None:
        self.request = request
        self.session = session

    # -- raw calls (return the response so negative tests can inspect status codes) ----------
    def _headers(self) -> dict[str, str]:
        return {"cookie": f"{SESSION_COOKIE}={self.session}"} if self.session else {}

    def post_raw(self, body: Any, *, raw: bool = False) -> APIResponse:
        data = body if raw else json.dumps(body)
        return self.request.post(
            "/api/registrations",
            data=data,
            headers={"content-type": "application/json", **self._headers()},
        )

    def list_raw(self, *, published: bool = False) -> APIResponse:
        params: dict[str, str | float | bool] | None = {"published": "1"} if published else None
        return self.request.get("/api/registrations", params=params, headers=self._headers())

    def patch_raw(self, reg_id: str, patch: dict[str, Any]) -> APIResponse:
        return self.request.patch(
            f"/api/registrations/{reg_id}",
            data=json.dumps(patch),
            headers={"content-type": "application/json", **self._headers()},
        )

    def delete_raw(self, reg_id: str) -> APIResponse:
        return self.request.delete(f"/api/registrations/{reg_id}", headers=self._headers())

    # -- happy-path helpers (raise with full context when the call fails) ---------------------
    def login(self, username: str, password: str) -> RegistrationApi:
        res = self.request.post(
            "/api/auth/login",
            data=json.dumps({"username": username, "password": password}),
            headers={"content-type": "application/json"},
        )
        if not res.ok:
            raise ApiError(res)
        cookie = res.headers.get("set-cookie", "")
        token = cookie.split(f"{SESSION_COOKIE}=", 1)[-1].split(";", 1)[0]
        return RegistrationApi(self.request, session=token)

    def create(self, body: dict[str, Any]) -> Registration:
        res = self.post_raw(body)
        if res.status != 201:
            raise ApiError(res)
        return RegistrationEnvelope.model_validate(res.json()).registration

    def all(self, *, published: bool = False) -> list[Registration]:
        res = self.list_raw(published=published)
        if not res.ok:
            raise ApiError(res)
        return RegistrationList.model_validate(res.json()).registrations

    def get(self, reg_id: str) -> Registration | None:
        return next((r for r in self.all() if r.id == reg_id), None)

    def update(self, reg_id: str, patch: dict[str, Any]) -> Registration:
        res = self.patch_raw(reg_id, patch)
        if not res.ok:
            raise ApiError(res)
        return RegistrationEnvelope.model_validate(res.json()).registration

    def delete(self, reg_id: str) -> None:
        res = self.delete_raw(reg_id)
        if res.status not in (200, 404):
            raise ApiError(res)
