---
name: movie-report
allowed-tools:
  - Bash(python3:*)
  - Bash(ls:*)
  - Bash(grep:*)
  - Read
  - Write
  - Glob
description: >
  Generate a movie taste-profile report, ranked-list-vs-star-rating consistency analysis, and
  disc-purchase recommendations (including blind buys) by cross-referencing a Plex/Synology
  library export, a Letterboxd data export, and the MovieList ranked-lists JSON. Use this skill
  whenever the user asks to analyze their movie taste, compare their movie rankings to their
  Letterboxd ratings, find movies to buy on disc/Blu-ray/4K, refresh their taste profile or
  recommendations, or re-run "the movie analysis" on new exports — even if they only mention one
  or two of the data sources by name (synology.json, Letterboxd export, movielist.json).
---

# Movie Taste Report

Cross-reference three data sources into (1) a taste profile, (2) an analysis of whether the
user's stack-ranked yearly lists agree with their Letterboxd star ratings, and (3) disc-purchase
recommendations, including "blind buys" the user has never seen. TV shows are always ignored.

## Inputs

Three files/directories. Ask only if a source can't be found:

1. **Plex/Synology library export** — JSON with `libraries[].type == "movie"` and
   `movies[] = {title, year}`. Usually `~/Downloads/synology.json`. Duplicate title+year
   entries mean multiple disc formats (DVD/Blu-ray/4K) — the script dedupes them.
2. **Letterboxd export directory** — contains `ratings.csv`, `watched.csv`, `watchlist.csv`,
   `diary.csv`. Usually the most recent `~/Downloads/letterboxd-*-utc/` directory (find it with
   `ls -dt` if there are several).
3. **MovieList ranked lists** — `~/Documents/MovieList/movielist.json`: per-year lists ordered
   best→worst, with tooltip entries marking tier boundaries ("Great/Good Divide",
   "Good/OK Divide", "OK/Bad Divide").

## Step 1 — Run the analysis script

```
python3 <skill-dir>/scripts/analyze.py --synology <synology.json> --letterboxd <letterboxd-dir> --movielist <movielist.json> --out <workdir>/analysis.json
```

For a consistency-only question (rankings vs ratings), `--synology` may be omitted — ownership
analysis is then skipped and `owned` fields come back null.

The stdout summary contains most of what the reports need; the JSON holds the full lists
(`four_star_not_owned`, `watchlist_not_owned_unseen`, `owned_never_logged`, `top5_per_year`,
`loved_4.5_plus` with owned flags). Read specific keys from the JSON rather than the whole file
if it's large.

The script's title matching is year-aware for a reason — bare titles collide (*Road House*
1989/2024, *Suicide Squad* vs *The Suicide Squad*) and Letterboxd uses short canonical titles
(*Glass Onion*, *F1*). Don't hand-match titles; extend the script if a new edge case appears.

## Step 2 — Verify before claiming

Two known failure modes to check before writing the reports:

- **False "not owned"**: abbreviated library titles can defeat matching (e.g. a disc filed as
  "E.T." won't match "E.T. the Extra-Terrestrial"). Before recommending a purchase, grep the
  Plex export for a distinctive fragment of any surprising title in `loved_4.5_plus` where
  `owned` is false.
- **Low match years**: `consistency_by_year` rows with few matched films (typically pre-2021)
  reflect films logged without star ratings, not missing data. Say so rather than treating those
  correlations as reliable.

## Step 3 — Write the two reports

Write both files to the directory the user asks for (default: alongside the input data). Date
them in the intro line. Interpret, don't dump — every list in the report should be filtered or
explained by the model, with the script output as evidence.

**`movie-taste-profile.md`**
- Short-version paragraph: the one-paragraph read on their taste.
- What they love: 4–6 themes, each grounded in named 5★/4.5★ films, rewatch counts, top-of-year
  ranks, and what the *collection itself* shows (franchise runs, director shelves, niche buys
  like concert films).
- What they don't: low ratings plus the list tooltips (they annotate strong opinions there).
- Rating behavior: distribution table, mean, decade skew.
- Consistency section: Spearman-by-year table, tier-average table (Great/Good/OK/Bad vs mean
  stars), and the genuine mismatches worth a re-rank or re-rate. Explain drift on sparse years.

**`movie-recommendations.md`** — tiered by confidence:
1. Rated 4.5–5★ but not owned (strongest signal). Flag streaming-only titles that have no disc
   so the user doesn't hunt for them.
2. Ranked high in yearly lists but unowned and unrated (pre-rating-era favorites).
3. Canon/collection gaps: infer from what the collection clearly collects (complete franchises,
   director runs) and 4★ ratings.
4. Blind buys: unseen films from the watchlist plus taste-matched picks, grouped by *why* they
   fit, referencing films the user demonstrably loves.
- End with a suggested "first order" top 10.
- Hedge edition/availability claims (Criterion, 4K) — training data goes stale; suggest the user
  verify pricing/print status, or check the web if search tools are available.

## Output expectations

Final chat message: lead with the consistency verdict (it's the one quantitative question),
then a compressed taste read and the top recommendation tiers. Keep the full detail in the files.
