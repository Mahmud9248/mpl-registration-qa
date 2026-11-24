"""TC-API-030.. — Authority review operations (PATCH / DELETE)."""

from __future__ import annotations

from collections.abc import Callable

import allure
import pytest

from mpl_qa.api.client import RegistrationApi
from mpl_qa.api.models import Registration
from mpl_qa.data.factories import PlayerFactory

pytestmark = [pytest.mark.api, allure.feature("Authority review API")]


@pytest.fixture
def registration(
    admin_api: RegistrationApi, factory: PlayerFactory, cleanup: Callable[[str], str]
) -> Registration:
    reg = admin_api.create(factory.build().to_api_payload())
    cleanup(reg.id)
    return reg


@pytest.mark.smoke
@allure.title("TC-API-030 Finalising a review stores tier, status and notes")
def test_finalize_review(admin_api: RegistrationApi, registration: Registration) -> None:
    updated = admin_api.update(
        registration.id,
        {
            "finalTier": "B",
            "reviewStatus": "Finalized",
            "authorityNotes": "Strong keeper, moved up",
        },
    )

    assert (updated.finalTier, updated.reviewStatus) == ("B", "Finalized")
    assert updated.authorityNotes == "Strong keeper, moved up"
    assert updated.provisionalTier == registration.provisionalTier, "provisional tier must not move"


@pytest.mark.regression
@allure.title("TC-API-031 Unpublished players disappear from the public list")
def test_unpublish_hides_from_public(
    admin_api: RegistrationApi, public_api: RegistrationApi, registration: Registration
) -> None:
    assert registration.id in {r.id for r in public_api.all(published=True)}

    admin_api.update(registration.id, {"published": False})

    assert registration.id not in {r.id for r in public_api.all(published=True)}


@pytest.mark.regression
@allure.title("TC-API-032 Fields outside the editable set cannot be changed by PATCH")
def test_patch_ignores_non_editable_fields(
    admin_api: RegistrationApi, registration: Registration
) -> None:
    res = admin_api.patch_raw(registration.id, {"name": "Renamed", "mobile": "01999999999"})

    assert res.status == 400
    assert res.json()["error"] == "No editable fields supplied"
    stored = admin_api.get(registration.id)
    assert stored is not None
    assert (stored.name, stored.mobile) == (registration.name, registration.mobile)


@pytest.mark.regression
@allure.title("TC-API-033 Updating or deleting an unknown id returns 404")
def test_unknown_id(admin_api: RegistrationApi) -> None:
    assert admin_api.patch_raw("MPL7-999999", {"finalTier": "A"}).status == 404
    assert admin_api.delete_raw("MPL7-999999").status == 404


@pytest.mark.regression
@allure.title("TC-API-034 Delete removes the record")
def test_delete(admin_api: RegistrationApi, registration: Registration) -> None:
    res = admin_api.delete_raw(registration.id)

    assert res.status == 200
    assert admin_api.get(registration.id) is None
