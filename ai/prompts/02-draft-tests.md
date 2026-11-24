# Prompt: turn observations into test drafts

---

Here is the project's page object for the registration page and one existing test file as a
style reference: [paste `src/mpl_qa/pages/registration_page.py` and
`tests/ui/test_payment.py`]

Write pytest-playwright tests for these observations: [paste rows from the exploratory report]

Rules:
- use the existing fixtures (`registration_page`, `mock_backend`, `factory`) and page-object
  methods; add a page-object method only if nothing existing fits, and show it separately
- no `wait_for_timeout`, no `time.sleep`; use `expect(...)` assertions
- one behaviour per test; Arrange / Act / Assert separated by blank lines
- give every test an `@allure.title("TC-XXX-NNN ...")`; leave the id as `NNN` for me to assign
- if an observation looks like a bug, write the test for the *correct* behaviour
