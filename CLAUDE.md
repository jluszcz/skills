# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A Claude Code plugin (`jluszcz`) that is also its own marketplace: `.claude-plugin/marketplace.json`
points at `./` as the sole plugin, and `.claude-plugin/plugin.json` defines it. It ships skills
(`skills/<name>/SKILL.md`) and agents (`agents/<name>.md`), no application code.

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

## Layout

- `skills/<name>/SKILL.md` — one skill per directory; frontmatter `name`, `description`, and
  `allowed-tools` (a YAML list; the older `permissions` key is unsupported — see commit `c3bdf1c`).
  Optional `references/` for docs loaded on demand and `evals/evals.json` for skill-creator test
  prompts (rip-rename has both patterns in use).
- `agents/<name>.md` — subagent definitions. The `code-review` skill dispatches
  `agents/code-reviewer.md`; the agent file owns the review rubric and output format, while the
  skill's `references/reviewer-prompt.md` supplies only per-review context. Keep it that way —
  don't duplicate the rubric back into the template.
- `skills/*-workspace/` — gitignored scratch dirs from skill-creator eval runs; never commit them.

## Skill-Authoring Conventions

Skills here are written to run without permission prompts: every shell command in a SKILL.md must
stay within the prefixes granted by its `allowed-tools` (e.g. `Bash(git diff:*)`). Pipes to other
tools, `for`/`if` loops, shell variables, heredocs, and `$()` substitution all break the prefix
match and force a prompt — avoid them in skill instructions and examples. `rip-rename/SKILL.md`
documents this in depth; keep new skills consistent with it.

## Checks

No build or test suite. Pre-commit hooks (`.pre-commit-config.yaml`: check-json, end-of-file-fixer,
trailing-whitespace, merge-conflict check) are the only gate:

```bash
pre-commit run --all-files
```

Skill evals are run via the skill-creator skill against `skills/<name>/evals/evals.json`.
