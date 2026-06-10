# Ship Changes as PR

Create a branch from dev, commit all pending changes, push, and open a PR targeting dev.

## Steps

1. **Check current state** — run `git fetch origin` to get the latest remote state, then run `git status` and `git diff` to understand what's changed. Also check the current branch with `git branch --show-current`. If we're on `dev` (or `main`/`master`), ensure the local branch is up to date with `git pull origin dev` before branching.

2. **Ensure we're working from dev** — if there are uncommitted changes on a non-dev branch already, proceed on the current branch. If we're on `dev` (or `main`/`master`) with uncommitted changes, we need to create a new branch before committing.

3. **Generate a branch name** — look at the staged and unstaged diffs to infer what the changes are about. Produce a short kebab-case branch name that describes the work (e.g., `fix-auth-redirect`, `add-gear-filter`, `update-api-constants`). Do not use generic names like `changes` or `update`. The branch name must not already exist remotely — check with `git branch -r`.

4. **Create and checkout the branch** — if needed, run `git checkout -b <branch-name>` from the current HEAD (which should be on dev or the existing feature branch).

5. **Stage all changes** — run `git add -A` unless the user specified particular files.

6. **Update CLAUDE.md** — read the current `CLAUDE.md` and the diff. Update only sections affected by the changes:
   - New or changed backend routes, models, services, or parsers
   - New or changed API endpoints or their behaviour
   - New architectural decisions, patterns, or key data flows
   - Removed features or deprecated paths
   Don't rewrite sections that are still accurate. If no structural changes were made, skip this step.

7. **Update README.md** — check if any user-facing behaviour changed:
   - New features or pages visible in the UI
   - Changes to how to run the app, install dependencies, or configure it
   - New upload flows or supported file types
   If README.md doesn't exist and the changes are user-facing, create a concise one. If nothing user-facing changed, skip this step.

8. **Re-stage** — run `git add -A` to pick up any doc changes from steps 6–7.

9. **Run backend lint** — run `docker compose exec web ruff check .` and `docker compose exec web ruff format --check .` from the project root. If either fails, auto-fix with `docker compose exec web ruff check . --fix` and `docker compose exec web ruff format .`, then re-stage with `git add -A` before committing. If Docker is not running, skip this step and note it in the response.

10. **Run frontend lint** — if a `frontend/` directory exists, run from the project root:
    ```
    cd frontend && npm run lint && npm run format:check
    ```
    If lint fails, auto-fix with `npm run format` then re-stage. If `node_modules` is missing, run `npm install` first. Skip if no `frontend/` directory exists.

11. **Commit** — write a concise commit message that summarises the work (imperative mood, present tense, under 72 chars). Use a heredoc to pass the message:
    ```
    git commit -m "$(cat <<'EOF'
    <message>
    EOF
    )"
    ```

12. **Push** — run `git push -u origin <branch-name>`.

13. **Create the PR** — run:
    ```
    gh pr create --title "Merge <branch-name> into dev" --base dev --head <branch-name> --body ""
    ```
    Fall back to `--base main` if dev doesn't exist remotely.

14. **Report** — print the PR URL so the user can see it.

## Notes

- If there are no uncommitted changes at all, tell the user and stop.
- If the current branch is already a feature branch (not dev/main/master) with no remote tracking branch, skip step 4 and just push it.
- If a pre-commit hook fails, fix the issue and retry rather than skipping the hook.
- Never force-push.
- Always confirm the PR was created successfully and share the URL.
