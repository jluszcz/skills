---
name: commit
description: 'Execute git commit with commit message analysis, intelligent staging, and message generation. Use when user asks to commit changes, create a git commit, or mentions "/commit". Supports: (1) Auto-detecting scope from changes, (2) Generating commit messages from diff, (3) Interactive commit with optional scope/description overrides, (4) Intelligent file staging for logical grouping'
license: MIT
permissions:
  allow:
    - Bash(git status*)
    - Bash(git diff*)
    - Bash(git log*)
    - Bash(git add*)
    - Bash(git commit*)
---

# Commit

## Overview

Create standardized, semantic git commits. Analyze the actual diff to determine appropriate scope, and message.

## Commit Format

```
[scope]: <description>

[optional body]

[optional footer(s)]
```

Scope is optional but encouraged when the change is clearly scoped to a module, component, or area.

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

### 3. Generate Commit Message

Analyze the diff and recent commit history to determine:

- **Scope**: What area/module is affected? Match casing/style from recent commits.
- **Description**: One-line summary of what changed (present tense, imperative mood)
- **Body**: Include when the change is complex, has multiple parts, or the "why" isn't obvious from the description alone. Simple, self-evident changes don't need a body.
- **Length**: First line at most 80 characters; wrap body at 80 characters.

### 4. Execute Commit

```bash
# Single line (for simple, self-evident changes)
git commit -m "scope: description"

# Multi-line with body/footer (for complex changes)
git commit -m "$(cat <<'EOF'
scope: description

Body explaining why or what isn't obvious from the title.

Closes #123
EOF
)"
```

### 5. Verify

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

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (`--force`, hard reset) without explicit request
- NEVER skip hooks (`--no-verify`) unless user asks
- NEVER force push to main/master
- NEVER add Co-Authored-By trailers or any reference to being AI-generated in commit messages
- If commit fails due to hooks, fix and create NEW commit (don't amend)
