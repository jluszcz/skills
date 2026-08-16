---
name: commit
description: >
  Create a git commit. Trigger whenever the user asks to commit — "commit", "/commit", "make a
  commit", "stage and commit", "commit my changes", "commit this", "save my work to git". Handles
  auto-detecting scope from the diff, generating a semantic commit message, intelligent staging,
  checking that documentation (README.md, CLAUDE.md, etc.) is up to date, creating a feature branch
  when you'd otherwise commit onto the default branch, and enforcing git safety rules.
license: MIT
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

# Commit

## Overview

Create standardized, semantic git commits. Analyze the actual diff to determine appropriate scope, and message.

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

If docs are stale, update them and stage the changes so they land in the **same commit** as the code they describe. If a doc change is genuinely out of scope, tell the user rather than silently skipping it.

### 4. Generate Commit Message

Analyze the diff and recent commit history to determine:

- **Type**: feat, fix, chore, etc. — only if recent commits use type prefixes.
- **Scope**: What area/module is affected? Match casing/style from recent commits.
- **Description**: One-line summary of what changed (present tense, imperative mood)
- **Body**: Include when the change is complex, has multiple parts, or the "why" isn't obvious from the description alone. Simple, self-evident changes don't need a body.
- **Length**: First line at most 80 characters; wrap body at 80 characters.

### 5. Create a Feature Branch if on the Default Branch

Committing straight onto a project's default branch (`main`, `master`, or whatever the repo uses)
is almost never what you want — it makes the change harder to review, harder to open a PR from, and
harder to undo. If step 1 showed you're on the default branch, create a feature branch first. Git
carries your staged and unstaged changes across a branch switch, so doing this after staging loses
no work.

Determine the remote's default branch:

```bash
git symbolic-ref --short refs/remotes/origin/HEAD
```

This prints something like `origin/main`. You're on the default branch when `git branch
--show-current` matches its short name (`main` here). If that command errors — some repos don't set
`origin/HEAD` — treat a current branch of `main` or `master` as the default.

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

If you're in a detached HEAD state (`git branch --show-current` prints nothing), don't guess — tell
the user and let them decide where the commit should land. If you're already on a feature branch
(not the default), skip this step and commit as normal.

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
- NEVER add Co-Authored-By trailers or any reference to being AI-generated in commit messages
- If a hook fails or modifies files, fix the underlying issue, restage, and run a fresh `git commit` — never amend, never `--no-verify`
