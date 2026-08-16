# jluszcz Claude Code Plugin

A Claude Code plugin providing skills for git commits and media organization.

## Skills

### `/commit [why this change was made]`

Analyzes your staged/unstaged changes, generates a semantic commit message, and executes the commit.

- Summarizes why the change was made from the current conversation, then hands the work to
  `commit-worker`, a subagent forked on Sonnet — so the diff and doc scan stay out of your context
  while the commit body still knows the "why"
- Takes optional context as an argument, which takes precedence over what it reads from the session
- Infers scope from the diff
- Matches message style from recent commits
- Stages files intelligently for logical grouping
- Checks that documentation (README.md, CLAUDE.md, etc.) is up to date before committing
- Follows git safety protocols (no `--no-verify`, no force pushes)

### `/movie-report`

Builds a movie taste profile, a ranked-list-vs-Letterboxd-stars consistency analysis, and tiered
disc-purchase recommendations (including blind buys) from a Plex/Synology library export, a
Letterboxd export, and MovieList ranked lists.

- Bundles a year-aware title-matching script (avoids collisions like Road House 1989/2024)
- Computes per-year Spearman rank correlation and tier calibration (Great/Good/OK/Bad vs stars)
- Verifies "not owned" claims against the library before recommending purchases
- Flags streaming-only titles with no disc release
- Ignores TV shows

### `/rip-rename`

Renames ripped TV show disc files (e.g. `title_t00.mkv`) into properly named episode files
(e.g. `Show Name - s01e01.mkv`) using a disc/episode listing from a photo or typed list.

- Parses episode listings from disc case photos or typed input
- Detects multi-episode files by comparing file sizes against the median
- Asks for confirmation before treating any file as multi-episode
- Checks for destination conflicts before moving anything
- Skips menu tracks and featurettes (files under 200 MB)
- Supports MKV, MP4, and M2TS sources

## CI

`main` requires PRs and a passing Claude review check. The automated version-bump workflow is exempted
from that via a repository-role bypass tied to a repo-scoped PAT, not a blanket exemption for GitHub
Actions — see `CLAUDE.md` for how it's wired up and the "pwn request" risk of extending that bypass to
other workflows.

### Rotating the `BUMP_VERSION_PAT` secret

When the PAT nears its expiration (GitHub emails the account it's scoped to), regenerate and reset it:

1. [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) → find the
   existing fine-grained token → regenerate it (or create a new one scoped to just `jluszcz/skills`
   with repository permission **Contents: Read and write**, then delete the old one after the secret
   is updated).
2. `gh secret set BUMP_VERSION_PAT --repo jluszcz/skills` — run in your own terminal so the token
   value never passes through a Claude Code session; it prompts for hidden input.

No other changes are needed — `bump-version.yml` and the ruleset bypass actor both key off the secret
name and the account's Admin role, not the token's value.

## Installation

```shell
claude plugin marketplace add jluszcz/skills
claude plugin install jluszcz@jluszcz
```

## License

MIT
