---
name: commit-worker
description: >
  Internal worker for the `commit` skill — do not invoke this directly, invoke `jluszcz:commit`
  instead, which writes the context brief this expects and then calls here. Given that brief, it
  does the actual work: reading the diff, auto-detecting scope, intelligent staging, checking that
  documentation (README.md, CLAUDE.md, etc.) is up to date, generating a semantic commit message,
  creating a feature branch when you'd otherwise commit onto the default branch, giving a branch a
  missing upstream (the remote default, or the parent branch when the work is stacked), and
  enforcing git safety rules. It runs forked and cannot see the conversation, so whatever calls it
  must pass the reason the change was made as the argument.
license: MIT
# Runs as a forked subagent on Sonnet: the diff, the doc scan, and the git
# plumbing all stay out of the caller's context, and none of it needs Opus.
# `background: false` keeps the caller blocked until the commit actually lands —
# this skill mutates the working tree and branch, so its result is not something
# to collect later.
model: sonnet
context: fork
background: false
argument-hint: "[context brief from the commit skill: why this change was made, scoping, branch decisions]"
allowed-tools:
  # Reading and updating stale docs is part of step 3, so the file tools are
  # needed as much as the git ones.
  - Read
  - Edit
  - Glob
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git ls-files:*)
  - Bash(git branch:*)
  - Bash(git symbolic-ref:*)
  - Bash(git switch:*)
  - Bash(git add:*)
  - Bash(git commit:*)
---

# Commit Worker

## Overview

Create standardized, semantic git commits. Analyze the actual diff to determine appropriate scope, and message.

## Execution Context

You are running as a forked subagent, dispatched by the `commit` skill. Two consequences shape
everything below:

- **You cannot see the conversation that triggered this.** The diff, `git log`, and the caller's
  brief are your only evidence. Don't invent a "why" you can't support from them.
- **You cannot ask the user anything mid-run.** When a step says you'd need a decision from them,
  stop before committing and report why — don't guess and commit anyway.

Caller-supplied brief (why the change was made, plus any scoping or branch decisions already
settled; may be empty):

$ARGUMENTS

Treat that as the "why" for the commit body when the diff alone doesn't explain the change, and
honor any scoping it gives — files to leave unstaged, a branch already chosen. If it's empty, derive
everything from the diff.

## Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Common types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`. Scope is optional but
encouraged when the change is clearly scoped to a module, component, or area. Match the repo's
recent history: if its commits use type prefixes (`feat(auth): …`), use them; if they don't
(`auth: …` or plain descriptions), don't introduce them.

## Workflow

### 1. Analyze Changes

```bash
# Check what's staged and unstaged
git status --porcelain

# If files are staged, use staged diff
git diff --staged

# If nothing staged, use working tree diff
git diff

# Check recent commits to match project style
git log --oneline -5

# Note the current branch — you'll create a feature branch later if this is the default branch
git branch --show-current
```

### 2. Stage Files (if needed)

If nothing is staged or you want to group changes logically:

```bash
# Stage specific files
git add path/to/file1 path/to/file2

# Stage by pattern
git add src/components/*
```

**Never commit secrets** (.env, credentials.json, private keys).

### 3. Check Documentation is Up to Date

Before generating the message, verify that documentation reflects the changes being committed. Compare the staged diff against project docs and flag anything now stale.

```bash
# Find docs that may need updating
git ls-files '*README*' '*CLAUDE.md' 'docs/**' '*.md'
```

Check whether the diff invalidates any of:

- **README.md** — installation/usage/examples, feature lists, supported options, badges, project structure.
- **CLAUDE.md** (and `AGENTS.md`, `.cursorrules`, etc.) — build/test/lint commands, conventions, architecture notes.
- **Other equivalent docs** — `docs/`, `CONTRIBUTING.md`, `CHANGELOG.md`, API docs, config samples (`.env.example`), inline help/usage text, and version numbers in manifests.

Triggers that usually require a doc update:

- Added/removed/renamed a command, flag, script, env var, or public API.
- Changed install steps, dependencies, or supported versions.
- Changed default behavior or configuration described in docs.

If docs are stale, update them and stage the changes so they land in the **same commit** as the code they describe. If a doc change is genuinely out of scope, commit without it and name the stale doc in your final report rather than silently skipping it.

### 4. Generate Commit Message

Analyze the diff and recent commit history to determine:

- **Type**: feat, fix, chore, etc. — only if recent commits use type prefixes.
- **Scope**: What area/module is affected? Match casing/style from recent commits.
- **Description**: One-line summary of what changed (present tense, imperative mood)
- **Body**: Include when the change is complex, has multiple parts, or the "why" isn't obvious from the description alone. Simple, self-evident changes don't need a body.
- **Length**: First line at most 80 characters; wrap body at 80 characters.

### 5. Settle the Branch and Its Upstream

Two things have to hold before you commit: you're not on the default branch, and the branch you're
on has an upstream. Git carries staged and unstaged changes across a branch switch, so doing this
after staging loses no work.

Determine the remote's default branch:

```bash
git symbolic-ref --short refs/remotes/origin/HEAD
```

This prints something like `origin/main`. You're on the default branch when `git branch
--show-current` matches its short name (`main` here). If that command errors — some repos don't set
`origin/HEAD` — treat a current branch of `main` or `master` as the default.

If you're in a detached HEAD state (`git branch --show-current` prints nothing), don't guess — stop
without committing and report that the caller needs to decide where the commit should land.

#### 5a. On the default branch: create a feature branch

Committing straight onto a project's default branch is almost never what you want — it makes the
change harder to review, harder to open a PR from, and harder to undo.

Name the branch after the commit you just wrote: take the description, drop the `type(scope):`
prefix, lowercase it, and join the words with hyphens. `feat(auth): implement JWT auth` becomes
`implement-jwt-auth`. Keep it to a few words and strip characters that are awkward in branch names
(spaces, slashes, punctuation).

Create the branch off the remote default and set that default as its upstream in one step:

```bash
git switch -c implement-jwt-auth -t origin/main
```

The `-t origin/main` gives the new branch a valid upstream immediately with no push, so `git
status` and `git pull` track against the default branch. Use `origin/master` (or whatever the
actual default is) to match the repo.

If the repo has no `origin` remote or no matching remote-tracking branch, create the branch without
tracking and tell the user its upstream will be set on their first push:

```bash
git switch -c implement-jwt-auth
```

#### 5b. On a feature branch: make sure it has the right upstream

A branch created without `-t` (or off another local branch) can have no upstream at all, which
leaves `git status` and `git pull` with nothing to compare against. Check it:

```bash
git status -sb
```

The first line reads `## branch...origin/branch` when an upstream is set — leave it alone and
commit. A bare `## branch` means there's no upstream, so pick one.

The upstream is the remote default (`origin/main` or equivalent) unless this work is **stacked** on
another local branch that hasn't landed yet — in which case it's that parent branch, so diffs and
PRs show only this branch's commits. Detect that by listing the local branches whose tips are
ancestors of `HEAD`:

```bash
git branch --merged HEAD --sort=-committerdate
```

Ignore the current branch (the one marked `*`) and the default branch. If any branch remains, the
work is stacked on it — the first one listed is the most recently committed, so take that:

```bash
git branch --set-upstream-to=parent-branch
```

Otherwise the branch came off the default, so track that:

```bash
git branch --set-upstream-to=origin/main
```

If neither exists — no `origin` remote and no parent branch — commit anyway and report that the
upstream will be set on the caller's first push.

### 6. Execute Commit

```bash
# Single line (for simple, self-evident changes)
git commit -m "type(scope): description"

# Multi-line with body/footer (for complex changes) — each -m adds a paragraph
git commit -m "type(scope): description" -m "Body explaining why or what isn't obvious from the title." -m "Closes #123"
```

Use multiple `-m` flags rather than a heredoc or `$()` substitution — command substitution
breaks the `Bash(git commit:*)` permission match and forces a prompt the allowlist exists to
avoid.

### 7. Verify

```bash
git log --oneline -1
```

Confirm the commit landed correctly.

### 8. Report Back

Your final message is all the caller sees — it gets relayed to the user verbatim, while the diff,
the file reads, and the git output stay in this subagent. Keep it to a few lines covering:

- The commit line from step 7, and the branch it landed on (say so explicitly if you created one, or
  if you set an upstream — name the upstream you chose).
- Any docs you updated into the commit, or any you found stale and left alone.
- Anything you stopped on instead of committing, and what decision the caller needs to make.

## Best Practices

- One logical change per commit
- Present tense: "add" not "added"
- Imperative mood: "fix bug" not "fixes bug"
- Reference issues: `Closes #123`, `Refs #456`
- Keep description under 80 characters
- Match scope style and casing from recent commits in the repo
- Keep docs (README.md, CLAUDE.md, etc.) in sync — commit doc updates alongside the code that changed them

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (`--force`, hard reset) without explicit request
- NEVER skip hooks (`--no-verify`) unless user asks
- NEVER force push to main/master
- NEVER commit directly onto the default branch (main/master/…) — create a feature branch first (see step 5)
- NEVER leave a branch without an upstream — it tracks the remote default, or the parent branch when the work is stacked (see step 5b)
- NEVER add Co-Authored-By trailers or any reference to being AI-generated in commit messages
- If a hook fails or modifies files, fix the underlying issue, restage, and run a fresh `git commit` — never amend, never `--no-verify`
