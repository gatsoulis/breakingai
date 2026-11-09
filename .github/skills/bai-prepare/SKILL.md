---
name: bai-prepare
description: Prepare a BreakingAI blog post for publishing. Checks the draft, moves its folder from drafts/ to published/ and sends unneeded files to leftovers/. Does not use git. Use when the user types /bai-prepare or asks to prepare a breakingai post or draft. The next step is /bai-publish.
---

# Prepare a BreakingAI post

Repository layout (at the repo root):
- `drafts/<post>/`: unpublished work in progress.
- `published/<post>/`: content ready to publish.
- `leftovers/<post>/`: draft files that must not be published.

## Procedure
1. Work from the repository root (the folder containing `drafts/`).
2. Determine the post: use the name the user gave, otherwise list `drafts/`. If exactly one folder exists use it; if several, ask the user which one.
3. Pre-checks. Stop and tell the user, changing nothing, if any fail:
   - The current git branch is not `main` or `master` (posts are written on their own branch). Never switch branches.
   - `drafts/<post>` is a directory.
   - `drafts/<post>/README.md` exists (required).
   - `drafts/<post>/post.md` exists (required).
   - `drafts/<post>/metadata.json` exists (required), is valid JSON (check by parsing it, e.g. `python3 -m json.tool`), and defines non-empty `title`, `subheading`, `seo_title`, `slug` and `tags` (a list), and `seo_title` is at most 60 characters.
   - The first level-1 heading (`# ...`) in `post.md` is identical to `title` in `metadata.json`. If they differ, show both and stop; do not edit either file.
   - `published/<post>` does not already exist (never overwrite).
   - `leftovers/<post>` does not already exist.
4. Create `published/<post>/` and move into it, keeping the same names:
   - `README.md` (required)
   - `post.md` (required)
   - `metadata.json` (required)
   - `post-abstract.md` (optional, only if present)
   - `src/` (optional, whole folder, only if present)
   - `pyproject.toml`, `uv.lock` and `.python-version` (optional, each only if present)
5. Create `leftovers/<post>/` and move every other remaining item in `drafts/<post>/` into it, including hidden files and folders (e.g. `.venv`, `gitignored/`). Skip creating `leftovers/<post>/` if nothing remains.
6. Remove the now-empty `drafts/<post>/`. If it is not empty, stop and report what remains.
7. Use `git mv` for tracked files and plain `mv` otherwise. Create `published/` and `leftovers/` if missing.
8. Report what went to `published/<post>/` and what went to `leftovers/<post>/`, and tell the user to review them. The next step is `/bai-publish`.

## Not included
Do not stage, commit or push, and do not open a pull request. That is `/bai-publish`.
