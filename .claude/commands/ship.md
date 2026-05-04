Review the current git state and prepare a clean commit, updating documentation as needed.

## Steps

1. **Understand what changed**
   - Run `git diff HEAD` to see all modifications
   - Run `git status --short` to see untracked files
   - Read `CLAUDE.md` and `README.md` (if it exists) to understand current documented state

2. **Update CLAUDE.md** if any of the following changed:
   - New backend routes, models, or services
   - Changes to how parsers, duplicate detection, or key algorithms work
   - New API endpoints or changes to existing ones
   - New architectural decisions or patterns
   - Changes to the data flow or key data structures
   Only edit the sections that are actually affected — don't rewrite sections that are still accurate.

3. **Update README.md** if any user-facing behaviour changed:
   - New features or pages visible in the UI
   - Changes to how to run the app, install dependencies, or configure it
   - New upload flows or supported file types
   If README.md doesn't exist yet, create a concise one covering: what the app does, how to run it (backend + frontend), and the main features.

4. **Stage and commit**
   - Stage all modified and untracked files relevant to the work (exclude `.venv/`, `node_modules/`, `*.db`, `__pycache__/`, temp files)
   - Write a concise commit message: imperative mood, ≤72 chars subject, no Claude attribution
   - Commit
