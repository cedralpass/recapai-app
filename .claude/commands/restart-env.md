Restart the RecapAI dev environment so all servers run from the current worktree.

Steps:
1. Sync .env files: run this shell command to copy missing .env files from the main repo into the current worktree:
   `MAIN="/Users/geoffreysmalling/development/recapai-app"; CWD=$(pwd); [ -f "$CWD/recap/.env" ] || cp "$MAIN/recap/.env" "$CWD/recap/.env" 2>/dev/null; [ -f "$CWD/aiapi/.env" ] || cp "$MAIN/aiapi/.env" "$CWD/aiapi/.env" 2>/dev/null`

2. Check running servers: call preview_list and inspect the `cwd` field of each server.

3. Stop any server whose `cwd` does not match the current worktree directory. Stop `recap` first, then `aiapi` if it is also wrong. Leave `tailwind` and `rq-worker` running unless they are also from the wrong worktree.

4. Start any stopped servers using preview_start — use the same names as defined in .claude/launch.json (`recap`, `aiapi`).

5. Confirm by calling preview_list again and reporting which servers are running and from which directory.
