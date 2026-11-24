# Review checklist for generated tests

Nothing generated goes into `tests/` until it passes this checklist.

- [ ] **Does it fail for the right reason?** Break the behaviour (or run it against the
      known bug with `--runxfail`) and read the failure message.
- [ ] **Assertions check behaviour, not implementation.** No asserting on CSS classes unless
      the class *is* the behaviour (e.g. step rail state).
- [ ] **Locators**: role/label first; ids or data-attributes when the page offers nothing
      better. No positional `nth()` on lists that can change.
- [ ] **No hidden waits.** No sleeps, no timeouts raised to make it pass.
- [ ] **Data** comes from `PlayerFactory`, not hard-coded people or real phone numbers.
- [ ] **Cleanup**: anything written to the database is passed to `cleanup()`.
- [ ] **Duplicates**: does an existing test already cover this? Extend it with a parameter instead.
- [ ] **Oracle**: expected values come from the spec or the domain model, not from running
      the app and copying what it printed.
