# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A Claude Code plugin (`jluszcz`) that is also its own marketplace: `.claude-plugin/marketplace.json`
points at `./` as the sole plugin, and `.claude-plugin/plugin.json` defines it. It ships skills
(`skills/<name>/SKILL.md`) and no application code. There is no `agents/` directory — the last agent
was removed in `9fb1319` — though the version-bump workflow still watches that path in case one
returns.

## Versioning — Do Not Bump Manually

The plugin version lives in three places: `plugin.json` `.version`, and `marketplace.json`
`.metadata.version` and `.plugins[0].version`. **A GitHub workflow keeps them in sync** —
`.github/workflows/bump-version.yml` runs on every push to `main`, and if the pushed commits touch
`agents/` or `skills/`, it bumps the patch version in all three fields and pushes a
`chore: bump plugin version to X.Y.Z` commit as `github-actions[bot]`.

Consequences:

- Never bump the version by hand as part of a skill/agent change; the bot handles it.
- After pushing to `main`, the bot adds a commit — `git pull` before pushing again.
- Doc-only or workflow-only changes (nothing under `agents/` or `skills/`) do not trigger a bump.

### Why the bot's push doesn't get blocked by branch protection

`main` is covered by a repository ruleset (id `18803372`) requiring every change to go through a PR
with a passing `claude-review` status check — `bump-version.yml`'s direct push would normally be
rejected under that rule, the way any other direct push is. To keep working, the workflow pushes
using the `BUMP_VERSION_PAT` secret (a PAT scoped to this repo, owned by `jluszcz`) instead of the
default `GITHUB_TOKEN`, and the ruleset has a `RepositoryRole: Admin` bypass actor (mode `always`)
that matches that PAT's identity. `Integration`-type bypass (exempting the GitHub Actions app
directly) isn't an option here — GitHub only allows it on organization-owned repos, and this one is
personal.

**Pwn-request caution**: the `RepositoryRole: Admin` bypass isn't scoped to `bump-version.yml` — it
applies to *any* push authenticated as an Admin-role identity on this repo. Don't add a workflow that
combines a PAT/token with `contents: write` and a fork-triggerable event (e.g. `pull_request_target`
checking out PR head content) — that's the classic "pwn request" pattern, and here it would inherit
this same branch-protection bypass.

## Layout

- `skills/<name>/SKILL.md` — one skill per directory; frontmatter `name`, `description`, and
  `allowed-tools` (a YAML list; the older `permissions` key is unsupported — see commit `c3bdf1c`).
  Optionally `evals/evals.json` for skill-creator test prompts — `rip-rename` is the only skill
  using it. Claude Code also supports a `references/` directory for docs loaded on demand, but no
  skill here has one yet.
- `skills/*-workspace/` — gitignored scratch dirs from skill-creator eval runs; never commit them.

## Skill-Authoring Conventions

Skills here are written to run without permission prompts: every shell command in a SKILL.md must
stay within the prefixes granted by its `allowed-tools` (e.g. `Bash(git diff:*)`). Pipes to other
tools, `for`/`if` loops, shell variables, heredocs, and `$()` substitution all break the prefix
match and force a prompt — avoid them in skill instructions and examples. `rip-rename/SKILL.md`
documents this in depth; keep new skills consistent with it.

**`allowed-tools` must cover every tool the body tells the model to use, not just the shell
commands.** A skill that says to read a file, edit one, or look at an image needs `Read`/`Edit`/
`Glob` listed alongside its `Bash(...)` prefixes. Both `commit` (which updates stale docs) and
`rip-rename` (which reads a photo of a disc case) instructed work their frontmatter did not permit,
which surfaces as a permission prompt in the middle of the task — exactly what these grants exist to
avoid. When editing a skill body, re-read its frontmatter.

### Running a Skill Forked and On a Cheaper Model

`commit` sets `model: sonnet` + `context: fork` + `background: false`. `model` accepts a family
alias (`haiku`/`sonnet`/`opus`/`fable`), a full model ID, or `inherit`, and applies whether the
skill runs inline or forked; if an org policy restricts the model, the parent model runs instead and
Claude Code warns rather than failing.

`context: fork` spawns a **fresh** subagent whose prompt is the skill body plus the invocation
arguments — it does *not* inherit the caller's conversation. That's the point (the diff and file
reads never enter the caller's context), but it means a forked skill has no memory of why the work
was done and cannot ask the user anything mid-run. Write forked bodies accordingly: take the missing
context through `$ARGUMENTS`, stop-and-report instead of prompting, and end with an explicit report
step, since the final message is all the caller sees. Forks default to background; `background:
false` keeps the caller blocked, which is what you want for anything that mutates the working tree.

## Checks

No build or test suite. Pre-commit hooks (`.pre-commit-config.yaml`: check-json, end-of-file-fixer,
trailing-whitespace, merge-conflict check) are the only gate:

```bash
pre-commit run --all-files
```

Skill evals are run via the skill-creator skill against `skills/<name>/evals/evals.json`.
