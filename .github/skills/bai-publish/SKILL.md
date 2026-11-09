---
name: bai-publish
description: Publish a prepared BreakingAI blog post. Given a keyword or folder name (e.g. /bai-publish effort_level), stages and commits every file in published/<folder>, lets the user accept a suggested commit message or write their own, pushes the branch, gives the link to open the pull request, and prints the values to paste into Hashnode. Use when the user types /bai-publish or asks to publish a breakingai post. Run /bai-prepare first.
---

# Publish a BreakingAI post

Run after `/bai-prepare`, which puts the post in `published/<post>/`.

## Procedure
1. Work from the repository root.
2. Determine the post from the user's keyword or folder name:
   - An exact match with a folder in `published/` wins; otherwise a folder whose name contains the keyword, if exactly one does.
   - If nothing matches or several match, list `published/` and ask the user which one.
   - If no keyword was given, use the folders in `published/` that have uncommitted changes (`git status --short published`). If exactly one, use it; if several, ask.
3. Pre-checks. Stop and tell the user, changing nothing, if any fail:
   - The current git branch is not `main` or `master`. Never switch branches.
   - `published/<post>` has uncommitted changes, or the branch has commits not yet pushed (`git status -sb`). If neither, tell the user to run `/bai-prepare` first (or that everything is already pushed). If there are no uncommitted changes but unpushed commits, skip steps 4 and 5.
   - `published/<post>/post.md` and `published/<post>/metadata.json` exist, and `metadata.json` is valid JSON (check by parsing it, e.g. `python3 -m json.tool`) with non-empty `title`, `subheading`, `seo_title`, `slug` and `tags` (a list).
   - `seo_title` is at most 60 characters.
   - The first level-1 heading (`# ...`) in `post.md` is identical to `title`. If they differ, show both and stop; do not edit either file.
4. Stage every file in the folder: `git add published/<post>`. This includes new, modified and deleted files in that folder and nothing outside it. Never use `git add -A`; `leftovers/` and `drafts/` are gitignored and must stay out. Show `git status --short published/<post>` so the user sees what is staged.
5. Commit message:
   - Write a suggested message. One short line in plain words, based on `git diff --cached --stat`: for a folder that is new in git use `Publish <post>: <title>`; for changes to an already committed folder use `Update <post>: <what changed>` (for example the fields or files touched).
   - Ask the user with the ask_user tool: use the suggested message, or write their own (free text). Show the suggestion in the question.
   - Commit with the chosen message: `git commit -m "<message>"`. Never add a Co-authored-by trailer or any other attribution to the message.
6. Push the current branch: `git push -u origin <branch>`. Never force-push. If the push fails, report the error and stop; the commit stays, so the user can fix it and run `/bai-publish <post>` again.
7. Do not create the pull request yourself: the user's tooling is signed in to a different GitHub account than the one that owns this repo, and `gh` is not installed on purpose. Give the user the link to open it in the browser: `https://github.com/gatsoulis/breakingai/compare/<branch>?expand=1`, plus a suggested title (`Publish: <title from metadata.json>`) and a short body listing the post folder and the tags.
8. Print the values to paste into Hashnode's editor, taken from `published/<post>/metadata.json`: `title`, `subheading`, `seo_title` (goes in the SEO title box of the draft settings), `slug` and `tags`. The body is `post.md` without its first `# <title>` line, since Hashnode shows the title itself. Publishing on Hashnode is manual, because its API requires a paid plan.

## Not included
There is no automated Hashnode publishing. Do not move files (that is `/bai-prepare`) and do not perform any steps beyond the ones above.
