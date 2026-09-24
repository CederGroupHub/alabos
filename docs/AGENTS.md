# Agent practices

This file is for humans and coding agents working in this repository.

The sections **Commit and push**, **`agent_temp/`**, **Git**, **CI hygiene**, and **Working style** are generic and may be copied to other repos. The **Data page reports** section is **mandatory for this repository** (alab_management).

## Data page reports (mandatory in this repo)

When the user wants a **Data page report**, **reusable dashboard CSV**, or **custom sample/task/experiment table** for operators (not an explicit one-off chat dump):

1. Implement `alab_management/dashboard/user_reports/<slug>.py` with  
   `run(*, start, end, live_db, completed_db) -> {columns, rows}`  
   (**read-only** against lab data; prefer `report_db.find_union` for Alab + Alab(completed)).
2. Upsert `Alab.data_reports` with  
   `generator: { "type": "module", "module": "<slug>" }`  
   (`saved: true` unless they only want a draft). Do not set `builtin: true`.
3. Tell the user: open **Data** → select the report → **Refresh** (date range) → **Download CSV**.

**Do not** finish with only a markdown/CSV table in chat or an `agent_temp/` one-off as the operator deliverable.

Full contract: [`docs/data-reports-cursor.md`](data-reports-cursor.md).  
Workflow checklist: [`.cursor/skills/alab-data-report/SKILL.md`](../.cursor/skills/alab-data-report/SKILL.md) (Cursor); other agents should follow the same steps from this section and `data-reports-cursor.md`.

---

## Commit and push regularly

Do not let a large pile of uncommitted work accumulate.

- After a coherent unit of work (a fix, a feature slice, a completed experiment that belongs in git), **prompt the user** to add, commit, and push.
- The agent must not commit or push on its own unless the user has asked for that (including “yes” to the prompt).
- Prefer several small commits over one giant catch-up at the end of a session.
- If the session is ending or switching tasks and the working tree is dirty with work the user intends to keep, prompt before moving on.

## `agent_temp/`

Use **`agent_temp/`** for all agent scratch:

- backups of files before a risky edit
- dumps, logs, unpacked binaries, one-off probe scripts
- anything that should not ship

Do **not** drop `_tmp_*` folders, `*.bak_*` next to source, or experiment dumps in `src/`, example folders, or the repo root.

`agent_temp/*` is gitignored except `agent_temp/README.md`. Never `git add` its contents. When the experiment is done, delete the scratch or leave it local. Promote finished work into the real project tree, then prompt for a commit.

## Git

- Do not commit secrets, `.env`, credentials, or `agent_temp/` contents.
- Do not force-push the default branch. Do not skip hooks (`--no-verify`).
- Do not `git add -A` or `git add .` from the repo root. Stage named files that belong in the commit.
- Prefer one focused commit per concern. Message: why, not a file list.
- If the remote default branch has moved, rebase or merge as the human prefers; do not rewrite published history.
- Treat other checkouts and remotes as separate: commit and push each repo on its own; do not assume write access to every remote.

## CI hygiene

- Before asking to commit or push, run the repo's relevant quality checks for the files you changed.
- Prefer fast, local checks first, especially Ruff or other configured linters on changed Python files.
- If a formatter or linter can auto-fix an issue safely, apply the fix before committing.
- If a change causes a CI-relevant check to fail, either fix it in the same session or call it out clearly before pushing.
- Do not knowingly push code that fails the repo's configured lint or test gates unless the human explicitly asks you to.

## Working style

- Keep diffs scoped to the request. Do not drive-by reformat or edit unrelated files.
- Match surrounding code. Do not add comments that only narrate the diff.
- Ask before force-pushing, deleting branches/tags, or any other destructive git operation.
