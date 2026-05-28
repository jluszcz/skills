# jluszcz Claude Code Plugin

A Claude Code plugin providing skills and agents for code review, git commits, and media organization.

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

### `/rip-rename`

Renames ripped TV show disc files (e.g. `title_t00.mkv`) into properly named episode files
(e.g. `Show Name - s01e01.mkv`) using a disc/episode listing from a photo or typed list.

- Parses episode listings from disc case photos or typed input
- Detects multi-episode files by comparing file sizes against the median
- Asks for confirmation before treating any file as multi-episode
- Checks for destination conflicts before moving anything
- Skips menu tracks and featurettes (files under 200 MB)
- Supports MKV, MP4, and M2TS sources

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
