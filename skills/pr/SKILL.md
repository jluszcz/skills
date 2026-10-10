---
name: pr
description: >
  Take local work all the way to an open pull request: run a code review (medium effort by default,
  or low/high/xhigh/max if asked), fix what it finds, commit with the commit skill, push, and open
  the PR. Trigger whenever the user wants their current changes turned into a PR — "/pr", "open a
  PR", "make a PR for this", "review and PR", "ship this", "get this up for review", "put up a PR
  with a high-effort review" — even if they don't mention reviewing. Not for reviewing someone
  else's existing PR (use code-review) or for committing without opening a PR (use commit).
license: MIT
allowed-tools:
  # Steps 2 and 4 delegate to the code-review and commit skills; Read/Edit/Glob/Grep cover
  # checking and touching up the review's fixes.
  - Skill
  - Read
  - Edit
  - Glob
  - Grep
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git branch:*)
  - Bash(git rev-parse:*)
  - Bash(git rev-list:*)
  - Bash(git symbolic-ref:*)
  - Bash(git push:*)
  - Bash(gh pr view:*)
  - Bash(gh pr create:*)
---

# PR

Review → fix → commit → push → open a PR, in that order. Each stage hands off to an existing tool
where one exists (`code-review`, `jluszcz:commit`, `gh`) so behavior stays consistent with running
them by hand.

## 1. Parse the effort level and survey the work

The review effort is `medium` unless the user's request names another: `low`, `medium`, `high`,
`xhigh`, or `max` (accept natural phrasing like "thorough review" → `high`, "quick review" →
`low`). Always pass the level explicitly in step 2 — with no level, `code-review` silently reuses
whatever level was used last, which is not what this skill promises.

`ultra` is a billed, multi-agent cloud review that only the user can launch. If they ask for it,
tell them to run `/code-review ultra` themselves and offer to continue with `max` instead.

Then see what the PR will contain:

```bash
git status --porcelain
git branch --show-current
git symbolic-ref --short refs/remotes/origin/HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
```

`symbolic-ref` gives the default branch (e.g. `origin/main`; if it errors, assume `main` or
`master`, whichever exists). Use it to count commits not yet on the default branch:

```bash
git rev-list --count origin/main..HEAD
```

If the working tree is clean **and** nothing is ahead of the default branch, there is nothing to
PR — say so and stop. If you're in a detached HEAD, stop and ask where the work should go.

## 2. Review and fix

Invoke the `code-review` skill with the effort level and `--fix`, so findings are applied to the
working tree rather than just listed:

- Uncommitted changes present → args `<effort> --fix` (reviews the current diff).
- Clean tree, commits ahead of the default branch → args `<effort> <current-branch> --fix`, so the
  committed work is what gets reviewed.

The review should cover everything the PR will contain; if the branch has both commits and
uncommitted changes, make sure neither half is skipped.

After it finishes, look at what `--fix` changed (`git diff`). Fixes are suggestions applied
mechanically, so sanity-check them: revert or adjust any that are wrong, and finish any that were
only partly applied. If the repo documents a check command (AGENTS.md, CLAUDE.md, README) and the
fixes touched code it covers, run it — a fix that breaks the build shouldn't go into the PR. If the
review found nothing, carry on.

Keep a short list of what the review found and what you did about each (fixed / skipped and why) —
it goes in the final report and, if non-trivial, the PR body.

## 3. Commit

Invoke the `jluszcz:commit` skill. It handles staging, doc sync, the commit message, and creating a
feature branch if you're on the default branch — don't duplicate any of that here. If the original
work was already committed and the review fixed things, this is a follow-up commit (e.g.
`fix: address review findings`); the commit skill will pick the message from the diff.

If the tree is clean after review (work already committed, no fixes), skip this step.

## 4. Determine the base and push

Re-read the branch and its upstream — the commit skill may have just created the branch:

```bash
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
```

Pick the PR base from the upstream:

| Upstream                          | Base                                                     |
|-----------------------------------|----------------------------------------------------------|
| `origin/main` (the default)       | `main` — the commit skill's normal setup                 |
| a local branch, e.g. `parent`     | `parent` — a stacked PR; push `parent` first if needed   |
| `origin/<this-branch>` or none    | the default branch                                       |

Push the branch by name without `-u`:

```bash
git push origin HEAD
```

Avoid bare `git push` and `-u`: branches here deliberately track their *base* (that's how the
commit skill and stacked PRs are set up), so a bare push targets the wrong branch and `-u` would
rewrite that tracking. Never force-push; if the push is rejected, report why and stop.

## 5. Open the PR

Check whether one already exists for this branch:

```bash
gh pr view <branch> --json url,state
```

If an open PR exists, the push already updated it — report its URL and stop.

Otherwise create it, passing `--head` and `--base` explicitly (gh guesses from upstream tracking,
which points at the base here):

```bash
gh pr create --head <branch> --base <base> --title "<title>" --body "<body>"
```

- **Title**: for a single commit, its subject line. For several, a summary in the same style as
  the repo's commit subjects.
- **Body**: a short `## Summary` of what changed and why (bullets are fine), then — if the review
  changed anything — a `## Review` section listing what it found and fixed. Add a `## Test plan`
  only if you actually ran something or there's a concrete manual check worth listing. Pass the
  body as one quoted string with real newlines; no heredoc or `$()`, which break the `gh pr
  create` permission match.

## 6. Report

Give the PR URL, the effort level used, and a one-line-per-finding summary of what the review
found and what happened to each. If anything was skipped or failed (a check, a push), say so.
