# jluszcz Claude Code Plugin

A Claude Code plugin providing skills for git commits and media organization.

## Skills

### `/commit`

Analyzes your staged/unstaged changes, generates a semantic commit message, and executes the commit.

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

## Installation

```shell
claude plugin marketplace add jluszcz/skills
claude plugin install jluszcz@jluszcz
```

## License

MIT
