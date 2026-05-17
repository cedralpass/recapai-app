# Dependency Upgrade Plan

Three third-party packages emit `DeprecationWarning: datetime.utcnow()` warnings during
the test suite. All have major-version upgrades available. Handle them in two phases —
`rq` is independent; `environs` + `marshmallow` are coupled and must be done together.

---

## Phase 1 — rq 1.16.2 → 2.x

**Why:** rq 2.x fixes the `datetime.utcnow()` deprecation in `rq/utils.py`. Independent
of the marshmallow stack.

### Steps

1. Review the [rq changelog](https://github.com/rq/rq/blob/master/CHANGELOG.md) for
   breaking changes between 1.16 and 2.x, noting any API removals or queue/worker
   behaviour changes.

2. Upgrade in the venv:
   ```bash
   .venv/bin/pip install "rq>=2,<3"
   ```

3. Run the full test suite:
   ```bash
   .venv/bin/pytest tests/ -v
   ```

4. Spot-check the RQ integration manually:
   - Start Redis (`brew services start redis`)
   - Start `rq-worker` via `preview_start`
   - Submit a URL via the UI and confirm classification completes

5. Update `requirements.txt` (and `requirements-dev.txt` if pinned there):
   ```
   rq>=2,<3
   ```

6. Commit: `chore: upgrade rq 1.16 → 2.x`

---

## Phase 2 — environs 10 → 15 + marshmallow 3 → 4 (coupled)

**Why:** `environs 15` requires `marshmallow 4`. Both emit deprecation warnings on the
current marshmallow `__version_info__` attribute. These must be upgraded together.

**marshmallow 4 breaking changes to watch for:**
- `Schema.Meta` options removed or renamed
- `fields.List` / `fields.Nested` signature changes
- `pre_load` / `post_load` decorator changes
- `ValidationError.messages` structure differences

### Steps

1. Review changelogs:
   - [marshmallow 4 migration guide](https://marshmallow.readthedocs.io/en/stable/upgrading.html)
   - [environs changelog](https://github.com/sloria/environs/blob/main/CHANGELOG.rst)

2. Search the codebase for all marshmallow/environs usage:
   ```bash
   grep -r "marshmallow\|environs\|Schema\|fields\." recap/ aiapi/ --include="*.py" -l
   ```
   Review each file for patterns affected by marshmallow 4 breaking changes.

3. Upgrade together:
   ```bash
   .venv/bin/pip install "environs>=15,<16" "marshmallow>=4,<5"
   ```

4. Run the full test suite:
   ```bash
   .venv/bin/pytest tests/ -v
   ```
   Fix any failures before proceeding.

5. Manually smoke-test config loading (environs is used for `Config` class — confirm
   all env vars load correctly on app startup).

6. Update `requirements.txt`:
   ```
   environs>=15,<16
   marshmallow>=4,<5
   ```

7. Commit: `chore: upgrade environs 10 → 15 and marshmallow 3 → 4`

---

## Acceptance Criteria

- `248 passed` (or more) with **0 DeprecationWarning** lines from rq, environs, or
  marshmallow in the test output
- App starts cleanly in dev mode (recap + aiapi servers)
- A classified article can be submitted and processed end-to-end via RQ worker
