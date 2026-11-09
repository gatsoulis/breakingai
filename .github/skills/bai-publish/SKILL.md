---
name: bai-publish
description: Publish a prepared BreakingAI blog post. Commits published/<post>, pushes the branch, gives the link to open the pull request, and prints the values to paste into Hashnode. Use when the user types /bai-publish or asks to publish a breakingai post. Run /bai-prepare first.
---

# Publish a BreakingAI post

Run after `/bai-prepare`, which puts the post in `published/<post>/`.

## Procedure
1. Work from the repository root.
2. Determine the post: use the name the user gave, otherwise the folders in `published/` that have uncommitted changes (`git status --short published`). If exactly one, use it; if several, ask the user which one.
3. Pre-checks. Stop and tell the user, changing nothing, if any fail:
   - The current git branch is not `main` or `master`. Never switch branches.
   - `published/<post>` has uncommitted changes, or the branch has commits not yet pushed (`git status -sb`). If neither, tell the user to run `/bai-prepare` first (or that everything is already pushed). If there are no uncommitted changes but unpushed commits, skip step 4.
   - `published/<post>/post.md` and `published/<post>/metadata.json` exist, and `metadata.json` is valid JSON with non-empty `title`, `subtitle`, `slug` and `tags`.
4. Commit only the post: `git add published/<post>` then `git commit -m "Publish <post>"` (never add a Co-authored-by trailer or any other attribution to the message). Never use `git add -A`, and never add `leftovers/` or `drafts/` (both are gitignored).
5. Push the current branch: `git push -u origin <branch>`. Never force-push. If the push fails, report the error and stop; the commit stays, so the user can fix it and run `/bai-publish` again.
6. Do not create the pull request yourself: the user's tooling is signed in to a different GitHub account than the one that owns this repo, and `gh` is not installed on purpose. Give the user the link to open it in the browser: `https://github.com/gatsoulis/breakingai/compare/<branch>?expand=1`, plus a suggested title (`Publish: <title from metadata.json>`) and a short body listing the post folder and the tags.
7. Print the values to paste into Hashnode's editor, taken from `published/<post>/metadata.json`: `title`, `subtitle`, `slug` and `tags`. The body is `post.md` without its first `# <title>` line, since Hashnode shows the title itself. Publishing on Hashnode is manual, because its API requires a paid plan.

## Not included
There is no automated Hashnode publishing. Do not move files (that is `/bai-prepare`) and do not perform any steps beyond the ones above.
