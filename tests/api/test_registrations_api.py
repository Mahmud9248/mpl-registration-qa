"""TC-API — /api/registrations against a real backend + database.

Every record created here is deleted again by the ``cleanup`` fixture.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import allure
import pytest
from playwright.sync_api import APIRequestContext

from mpl_qa.api.client import RegistrationApi
from mpl_qa.api.models import ErrorBody, Health, Registration
from mpl_qa.config import Settings
from mpl_qa.data.factories import PlayerFactory

pytestmark = [pytest.mark.api, allure.feature("Registration API")]

Cleanup = Any  # Callable[[str], str]; kept loose so test signatures stay readable


# -- health & auth ---------------------------------------------------------------------------
@pytest.mark.smoke
@allure.title("TC-API-001 Health endpoint reports the service is up")
def test_health(api_context: APIRequestContext) -> None:
    res = api_context.get("/api/health")

    assert res.status == 200
    Health.model_validate(res.json())
    assert res.headers["cache-control"] == "no-store"


@pytest.mark.smoke
@allure.title("TC-API-002 The full registration list is admin-only")
def test_full_list_requires_admin(public_api: RegistrationApi) -> None:
    res = public_api.list_raw()

    assert res.status == 401
    assert ErrorBody.model_validate(res.json()).error == "Unauthorized"


@pytest.mark.regression
@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("admin", "wrong-password"),
        ("root", "qa-admin-pass"),
        ("", ""),
        ("admin", " qa-admin-pass"),
    ],
    ids=["wrong-password", "wrong-user", "empty", "leading-space"],
)
@allure.title("TC-API-003 Login rejects bad credentials ({username!r})")
def test_login_rejects_bad_credentials(
    api_context: APIRequestContext, username: str, password: str
) -> None:
    res = api_context.post(
        "/api/auth/login",
        data=json.dumps({"username": username, "password": password}),
        headers={"content-type": "application/json"},
    )

    assert res.status == 401
    assert "set-cookie" not in res.headers


@pytest.mark.regression
@allure.title("TC-API-004 The session cookie is HttpOnly, Secure and SameSite")
def test_session_cookie_flags(api_context: APIRequestContext, settings: Settings) -> None:
    res = api_context.post(
        "/api/auth/login",
        data=json.dumps({"username": settings.admin_username, "password": settings.admin_password}),
        headers={"content-type": "application/json"},
    )

    cookie = res.headers["set-cookie"]
    for flag in ("HttpOnly", "Secure", "SameSite=Lax", "Path=/"):
        assert flag in cookie, f"session cookie is missing {flag}: {cookie}"


@pytest.mark.regression
@pytest.mark.parametrize(
    "token",
    ["", "garbage", "eyJyb2xlIjoiYWRtaW4ifQ.forged-signature"],
    ids=["empty", "garbage", "forged-signature"],
)
@allure.title("TC-API-005 Tampered session tokens are rejected")
def test_forged_session_rejected(api_context: APIRequestContext, token: str) -> None:
    res = RegistrationApi(api_context, session=token or None).list_raw()

    assert res.status == 401


@pytest.mark.regression
@allure.title("TC-API-006 Write endpoints reject anonymous callers")
def test_anonymous_cannot_modify(
    public_api: RegistrationApi,
    admin_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Cleanup,
) -> None:
    reg = admin_api.create(factory.build().to_api_payload())
    cleanup(reg.id)

    assert public_api.patch_raw(reg.id, {"finalTier": "A"}).status == 401
    assert public_api.delete_raw(reg.id).status == 401
    assert admin_api.get(reg.id) is not None


# -- create ----------------------------------------------------------------------------------
@pytest.mark.smoke
@allure.title("TC-API-010 Creating a registration returns 201 and a well-formed record")
def test_create_registration(
    public_api: RegistrationApi, factory: PlayerFactory, cleanup: Cleanup
) -> None:
    player = factory.build()

    reg = public_api.create(player.to_api_payload())
    cleanup(reg.id)

    assert reg.name == player.full_name
    assert reg.mobile == player.mobile
    assert reg.provisionalTier == player.expected.tier
    assert reg.reviewStatus == "Pending"
    assert reg.finalTier == ""


@pytest.mark.regression
@allure.title("TC-API-011 What the API returns is what it stored")
def test_create_then_read_back(
    public_api: RegistrationApi,
    admin_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Cleanup,
) -> None:
    created = public_api.create(factory.build().to_api_payload())
    cleanup(created.id)

    stored = admin_api.get(created.id)

    assert stored is not None
    assert stored.model_dump(exclude={"createdAt"}) == created.model_dump(exclude={"createdAt"})


@pytest.mark.regression
@allure.title("TC-API-012 Registration ids are sequential")
def test_ids_are_sequential(
    public_api: RegistrationApi, factory: PlayerFactory, cleanup: Cleanup
) -> None:
    first = cleanup(public_api.create(factory.build().to_api_payload()).id)
    second = cleanup(public_api.create(factory.build().to_api_payload()).id)

    assert int(second.split("-")[1]) == int(first.split("-")[1]) + 1


@pytest.mark.regression
@pytest.mark.parametrize(
    "missing",
    [
        "name",
        "mobile",
        "playerType",
        "provisionalTier",
        pytest.param(
            "scores",
            marks=[
                pytest.mark.known_bug,
                pytest.mark.xfail(
                    reason="BUG-002: a missing scores object is defaulted to {} and accepted"
                ),
            ],
        ),
    ],
)
@allure.title("TC-API-013 Missing required field '{missing}' -> 400")
def test_missing_required_field(
    public_api: RegistrationApi, factory: PlayerFactory, missing: str
) -> None:
    body = factory.build().to_api_payload()
    body.pop(missing)

    res = public_api.post_raw(body)

    assert res.status == 400
    assert ErrorBody.model_validate(res.json()).error == "Missing required registration data"


@pytest.mark.regression
@pytest.mark.parametrize(
    "raw", ["{not json", "", "[]", "null"], ids=["malformed", "empty", "array", "null"]
)
@allure.title("TC-API-014 Non-object bodies are rejected with 400 ({raw!r})")
def test_invalid_json(public_api: RegistrationApi, raw: str) -> None:
    res = public_api.post_raw(raw, raw=True)

    assert res.status == 400


@pytest.mark.regression
@allure.title("TC-API-015 Photos over the 650 KB limit are rejected with 413")
def test_photo_size_limit(
    public_api: RegistrationApi, factory: PlayerFactory, cleanup: Cleanup
) -> None:
    body = factory.build().to_api_payload()
    prefix = "data:image/jpeg;base64,"

    at_limit = public_api.post_raw({**body, "photo": prefix + "A" * (650_000 - len(prefix))})
    over_limit = public_api.post_raw({**body, "photo": prefix + "A" * (650_001 - len(prefix))})

    assert at_limit.status == 201
    cleanup(at_limit.json()["registration"]["id"])
    assert over_limit.status == 413
    assert "too large" in over_limit.json()["error"]


# -- known defects ---------------------------------------------------------------------------
@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-001: concurrent registrations collide on the generated id")
@allure.issue("BUG-001")
@allure.title("TC-API-020 Ten players registering at the same moment all succeed")
def test_concurrent_registrations(
    settings: Settings, factory: PlayerFactory, cleanup: Cleanup
) -> None:
    bodies = [json.dumps(factory.build().to_api_payload()).encode() for _ in range(10)]
    start_line = threading.Barrier(len(bodies))

    def register(body: bytes) -> tuple[int, str]:
        req = urllib.request.Request(
            f"{settings.base_url}/api/registrations",
            data=body,
            headers={"content-type": "application/json"},
        )
        start_line.wait()  # release all requests at the same instant
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.load(res)["registration"]["id"]
        except urllib.error.HTTPError as err:
            return err.code, ""

    with ThreadPoolExecutor(max_workers=len(bodies)) as pool:
        results = list(pool.map(register, bodies))
    for _, reg_id in results:
        if reg_id:
            cleanup(reg_id)

    statuses = [status for status, _ in results]
    assert statuses == [201] * len(bodies), f"lost registrations: {statuses}"


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-002: client controls provisionalTier and reviewStatus")
@allure.issue("BUG-002")
@allure.title("TC-API-021 A client cannot self-assign tier A or mark itself 'Finalized'")
def test_client_cannot_forge_assessment(
    public_api: RegistrationApi,
    admin_api: RegistrationApi,
    factory: PlayerFactory,
    cleanup: Cleanup,
) -> None:
    player = factory.with_tier("D", "Batter")
    forged = {**player.to_api_payload(), "provisionalTier": "A", "reviewStatus": "Finalized"}

    res = public_api.post_raw(forged)
    if res.status == 201:
        reg: Registration = admin_api.get(cleanup(res.json()["registration"]["id"]))  # type: ignore[assignment]
        assert reg.provisionalTier == "D", "server trusted a client-supplied tier"
        assert reg.reviewStatus == "Pending", "server trusted a client-supplied review status"
    else:
        assert res.status == 400


@pytest.mark.regression
@pytest.mark.known_bug
@pytest.mark.xfail(reason="BUG-004: mobile number is only validated in the browser")
@allure.issue("BUG-004")
@pytest.mark.parametrize("mobile", ["abc", "123", "01712345678901234"])
@allure.title("TC-API-022 The API rejects an invalid mobile number ({mobile!r})")
def test_server_validates_mobile(
    public_api: RegistrationApi, factory: PlayerFactory, cleanup: Cleanup, mobile: str
) -> None:
    res = public_api.post_raw({**factory.build().to_api_payload(), "mobile": mobile})
    if res.status == 201:
        cleanup(res.json()["registration"]["id"])

    assert res.status == 400
