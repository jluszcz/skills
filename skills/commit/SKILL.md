---
name: commit
description: >
  Create a git commit. Trigger whenever the user asks to commit — "commit", "/commit", "make a
  commit", "stage and commit", "commit my changes", "commit this", "save my work to git". Gathers
  the "why" from the conversation and hands off to the `commit-worker` skill, which auto-detects
  scope from the diff, generates a semantic commit message, stages intelligently, checks that
  documentation (README.md, CLAUDE.md, etc.) is up to date, creates a feature branch when you'd
  otherwise commit onto the default branch, gives a branch a missing upstream (the remote default,
  or the parent branch when the work is stacked), and enforces git safety rules.
license: MIT
argument-hint: "[why this change was made, if the diff doesn't show it]"
allowed-tools:
  - Skill
---

# Commit

## Overview

The commit itself is done by `jluszcz:commit-worker`, a subagent that runs forked on Sonnet so the
diff, the doc scan, and the git plumbing never enter this conversation. Your job is the one thing
that fork cannot do: supply the context that lives in this conversation and nowhere in the diff.

**Do not run git yourself.** No `git diff`, no `git status`, no staging — reading any of that here
defeats the point of the fork. Write the brief, hand off, relay the result.

Caller-supplied context, if any (may be empty):

$ARGUMENTS

## 1. Write the Context Brief

Two to five lines, from what you already know in this conversation. Cover whichever of these apply:

- **Why the change was made** — the bug that was reported, the decision behind an approach, the
  constraint that forced an odd-looking fix. This is what the fork is blind to and what the commit
  body needs.
- **Scoping the worker would otherwise get wrong** — files to leave unstaged (scratch plans,
  unrelated work in progress), or a set of changes that should land as more than one commit.
- **Branch decisions already settled** — a branch name the user chose, work that's stacked on a
  parent branch, an explicit instruction to stay put.

Rules:

- Only what you actually know. A guessed "why" in a commit message is worse than none, and the
  worker is instructed not to invent one either.
- Don't restate the diff — the worker reads it. Give it what the diff can't tell it.
- `$ARGUMENTS` above takes precedence over your own reading of the conversation; fold it in rather
  than replacing it.
- If there's genuinely no context — a fresh session where `/commit` is the first thing said — say
  exactly that: "No conversation context; derive everything from the diff." An empty brief is a
  fine answer, and better than padding.

## 2. Hand Off

Invoke the Skill tool with skill `jluszcz:commit-worker`, passing the brief as `args`. It runs
blocking, so wait for it.

## 3. Report Back

Relay the worker's report. Don't re-run git to verify it — the worker already did, and re-reading
the repo here pulls back the context the fork exists to keep out.

If it stopped without committing (detached HEAD, a decision it couldn't make alone), surface that
decision to the user and resolve it with them before invoking the worker again — this time with the
answer in the brief.
