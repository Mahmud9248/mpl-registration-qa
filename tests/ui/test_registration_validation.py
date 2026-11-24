"""TC-VAL-001..012 — field validation and step gating (backend mocked)."""

from __future__ import annotations

import allure
import pytest
from playwright.sync_api import expect

from mpl_qa.data.factories import PlayerFactory
from mpl_qa.domain.assessment import QUESTIONS, Section
from mpl_qa.pages.registration_page import SECTION_STEPS, RegistrationPage
from mpl_qa.support.images import png

pytestmark = [pytest.mark.mocked, allure.feature("Validation")]

MOBILE_ERROR = "Use a valid Bangladeshi mobile number."


@pytest.mark.smoke
@allure.title("TC-VAL-001 An empty profile step shows all three required-field errors")
def test_empty_profile_is_blocked(registration_page: RegistrationPage) -> None:
    registration_page.next()

    registration_page.expect_step(1)
    assert registration_page.visible_errors() == {
        "photo": "Please add a profile picture.",
        "fullName": "Please enter your full name.",
        "mobile": MOBILE_ERROR,
    }


@pytest.mark.regression
@pytest.mark.parametrize(
    ("mobile", "accepted"),
    [
        pytest.param("01712345678", True, id="valid-11-digits"),
        pytest.param("01312345678", True, id="valid-013-prefix"),
        pytest.param("017-1234-5678", True, id="dashes-are-stripped"),
        pytest.param("017 1234 5678", True, id="spaces-are-stripped"),
        pytest.param("0171234567", False, id="10-digits"),
        pytest.param("017123456789", False, id="12-digits"),
        pytest.param("02712345678", False, id="wrong-prefix"),
        pytest.param("+8801712345678", False, id="country-code"),
        pytest.param("abcdefghijk", False, id="letters"),
        pytest.param("", False, id="empty"),
    ],
)
@allure.title("TC-VAL-002 Mobile number rule: {mobile!r} accepted={accepted}")
def test_mobile_number_rules(
    registration_page: RegistrationPage, factory: PlayerFactory, mobile: str, accepted: bool
) -> None:
    registration_page.fill_profile(factory.build(mobile=mobile))

    registration_page.next()

    if accepted:
        registration_page.expect_step(2)
    else:
        registration_page.expect_step(1)
        expect(registration_page.error_for("mobile")).to_have_text(MOBILE_ERROR)


@pytest.mark.regression
@pytest.mark.parametrize("name", ["   ", "\t"], ids=["spaces", "tab"])
@allure.title("TC-VAL-003 A whitespace-only name is rejected")
def test_blank_name_rejected(
    registration_page: RegistrationPage, factory: PlayerFactory, name: str
) -> None:
    registration_page.fill_profile(factory.build(full_name=name))

    registration_page.next()

    expect(registration_page.error_for("fullName")).to_have_text("Please enter your full name.")


@pytest.mark.regression
@pytest.mark.parametrize(
    "name",
    ["মাহমুদ হাসান", "O'Brien-Smith", "A" * 120],
    ids=["bangla", "apostrophe-hyphen", "120-chars"],
)
@allure.title("TC-VAL-004 Real-world names are accepted")
def test_real_world_names_accepted(
    registration_page: RegistrationPage, factory: PlayerFactory, name: str
) -> None:
    registration_page.fill_profile(factory.build(full_name=name))

    registration_page.next()

    registration_page.expect_step(2)


@pytest.mark.regression
@allure.title("TC-VAL-005 A large photo is cropped and compressed in the browser")
def test_large_photo_is_compressed(registration_page: RegistrationPage) -> None:
    registration_page.upload_photo(png(2400, 1600), name="huge.png")

    src = registration_page.photo_preview.get_attribute("src") or ""
    assert src.startswith("data:image/jpeg"), "photo should be re-encoded as JPEG"
    assert len(src) < 650_000, "compressed photo must fit the API's 650 KB limit"
    natural = registration_page.photo_preview.evaluate(
        "img => [img.naturalWidth, img.naturalHeight]"
    )
    assert natural == [640, 640], "photo should be centre-cropped to a 640x640 square"


@pytest.mark.regression
@allure.title("TC-VAL-006 The photo picker only offers PNG and JPEG")
def test_photo_input_accept_filter(registration_page: RegistrationPage) -> None:
    expect(registration_page.photo_input).to_have_attribute("accept", "image/png,image/jpeg")


@pytest.mark.regression
@allure.title("TC-VAL-007 The role step requires a player type, batting hand and bowling type")
def test_role_step_requires_all_fields(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    registration_page.advance_to(2, factory.build())

    registration_page.next()

    registration_page.expect_step(2)
    assert set(registration_page.visible_errors()) == {"playerType", "battingHand", "bowlingType"}


@pytest.mark.regression
@pytest.mark.parametrize("section", list(SECTION_STEPS), ids=lambda s: s.name.lower())
@allure.title("TC-VAL-008 Every assessment question is mandatory: {section}")
def test_each_question_is_mandatory(
    registration_page: RegistrationPage, factory: PlayerFactory, section: Section
) -> None:
    player = factory.build()
    registration_page.advance_to(SECTION_STEPS[section], player)

    # Answer everything except the last question of the section under test.
    questions = [q for q in QUESTIONS if q.section is section]
    skipped = questions[-1]
    registration_page.answer_section(
        section, {q.id: player.answers[q.id] for q in questions if q is not skipped}
    )
    registration_page.next()

    registration_page.expect_step(SECTION_STEPS[section])
    assert registration_page.visible_errors() == {skipped.id: "Choose at least one answer."}


@pytest.mark.regression
@allure.title("TC-VAL-009 The bowling-role question accepts several roles")
def test_bowling_role_multi_select(
    registration_page: RegistrationPage, factory: PlayerFactory
) -> None:
    roles = ["New ball", "Death / pressure overs"]
    player = factory.build(answers={**factory.answers(), "bowl_role": roles})
    registration_page.complete_until_review(player)
    while registration_page.current_step() > SECTION_STEPS[Section.BOWLING]:
        registration_page.back()

    registration_page.expect_step(SECTION_STEPS[Section.BOWLING])
    for role in roles:
        expect(
            registration_page.active_step.locator(f"input[name='bowl_role[]'][value='{role}']")
        ).to_be_checked()
