Review what changed since the last commit and update any affected documentation to reflect the current state of the codebase.

## Steps

1. **Understand what changed**: run `git diff --stat HEAD` and `git status` to get the full picture of modified, added, and deleted files.

2. **Read the affected source files**: for any non-trivial changes (new features, new models, new routes, new RQ tasks, new agents, changed architecture), read the relevant source files to understand what was actually built before touching docs.

3. **Identify which docs need updating** using this map:

   | Changed area | Docs to consider updating |
   |---|---|
   | New feature / major capability | `docs/vision.md` (move from Planned → Current if shipped) |
   | New RQ task or job type | `docs/background_jobs.md` — Job Types table + description |
   | New files, models, routes, agents | `CLAUDE.md` — Key Architecture section |
   | LangGraph agents / AI features | `tech_design/` — relevant design doc |
   | Deployment / infra changes | `devops/` — `render_hosting.md`, `memory.md` as appropriate |
   | New known bug (not yet scheduled) | `BUGS.md` — add an entry |
   | Bug fixed | `BUGS.md` — mark closed or remove entry |
   | `requirements.txt` changes | Note in relevant tech design doc |

4. **Apply targeted edits**: update only the sections that are actually stale. Do not rewrite sections that are still accurate. Prefer `Edit` over `Write` to minimise diff noise.

5. **Do not update**:
   - Docs whose content is still accurate
   - `devops/` docs for infrastructure not yet built (e.g. cron job docs before the cron exists)
   - `README.md` unless the setup instructions or architecture overview genuinely changed

6. **Report**: briefly list which files you updated and what changed in each. If nothing needed updating, say so explicitly.
