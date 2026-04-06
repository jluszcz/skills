# jluszcz Claude Code Plugin

A Claude Code plugin providing skills and agents for code review and git commits.

## Skills

### `/commit`

Analyzes your staged/unstaged changes, generates a semantic commit message, and executes the commit.

- Infers scope from the diff
- Matches message style from recent commits
- Stages files intelligently for logical grouping
- Follows git safety protocols (no `--no-verify`, no force pushes)

### `/code-review`

Dispatches a `code-reviewer` subagent to review completed work against requirements. Designed to run after each significant
implementation step.

- Compares implementation against plan or requirements
- Categorizes issues as Critical / Important / Minor
- Preserves your session context by running review in a focused subagent
- Gives a clear merge-readiness verdict

## Agents

### `code-reviewer`

A Senior Code Reviewer agent used internally by the `/code-review` skill. Reviews a git diff range for plan alignment, code
quality, architecture, and production readiness.

## Installation

```shell
claude plugin marketplace add jluszcz/skills
claude plugin install jluszcz@jluszcz
```

## License

MIT
