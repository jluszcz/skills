---
name: rip-rename
allowed-tools:
  # The episode listing usually arrives as a photo of the disc case, which
  # means reading an image.
  - Read
  - Bash(find:*)
  - Bash(stat:*)
  - Bash(ls:*)
  - Bash(mkdir:*)
  - Bash(mv:*)
  - Bash(rmdir:*)
  - Bash(echo:*)
description: >
  Rename ripped TV show disc files into properly named episode files using a disc/episode listing
  (from a photo/image of the disc case or a typed list). Use this skill whenever the user wants to
  rename MKV, MP4, M2TS, or other video files from disc rips (e.g. title_t00.mkv, title_t01.mkv)
  into standard episode filenames like "Show Name - s01e01.mkv". Trigger for any of: renaming disc
  rip files, organizing ripped TV episodes, mapping disc track files to episode names,
  bulk-renaming MKVs from a Blu-ray or DVD rip, "I took a photo of my disc case, rename the
  files". Handles double-length episodes, duplicate detection, and multi-disc seasons.
---

# Rip Rename

Rename ripped disc files (e.g. `title_t00.mkv`) into properly named episode files
(e.g. `Star Trek The Next Generation - s01e01.mkv`) using a disc/episode listing.

## Inputs

The user will provide one of:
- A **photo/image** of the disc case or insert listing episodes per disc
- A **typed list** mapping disc → episodes in order

They will also tell you (or you should ask):
- Show name (for output filenames)
- Season number
- Source directory containing the disc folders
- Destination directory for renamed files

**Collect all four pieces of information before scanning the filesystem.** If any are missing,
ask for them upfront rather than mid-process.

### Deriving and confirming the show name

The show name goes into every output filename, so getting it right matters — and the folder names
left by ripping tools are a poor source for it. Those tools replace characters that filesystems
dislike, so `Star Trek: The Next Generation` becomes a folder like
`Star Trek- The Next Generation Season 3 Disc 1` — that `-` is a sanitized colon. Copy the folder
name straight into filenames and you get `Star Trek- The Next Generation - s03e01.mkv`, with a
dangling hyphen that media servers (Plex, Jellyfin) won't match cleanly.

So derive a **clean** show name rather than inheriting the folder's punctuation:
- Strip the `Season N` / `Disc N` suffix portion first.
- Ripping tools sanitize `": "` → `"- "`, so after stripping you may still have a dangling hyphen
  in the middle: `Star Trek- The Next Generation`. **Delete the hyphen character** (not the space
  after it) wherever a `- ` appears inside or at the end of the base name:
  `Star Trek- The Next Generation` → `Star Trek The Next Generation`.
  The test is simple: if you see a `-` directly glued to the preceding word (no space before it)
  and followed by a space or end-of-string, remove that `-`.
- Drop any remaining colons, underscores, or doubled spaces and trim leading/trailing whitespace.

Then show the user the exact name and a sample filename, and confirm before building the plan:

> "I'll name the files like `Star Trek The Next Generation - s03e01.mkv` — good?"

A one-line confirmation here prevents renaming a whole season wrong.

## Running shell commands

This skill is pre-approved to run `find`, `stat`, `ls`, `mkdir`, `mv`, `rmdir`, and `echo` without
prompting. To keep the **whole** workflow prompt-free, build commands only from those binaries —
the permission system checks each segment of a compound command independently and re-prompts the
moment it sees anything else (a pipe to another tool, a loop, a variable assignment). The earlier
version of this skill leaned on `for` loops, `set -e`, `$dest` variables, and `| sort`, and every
one of those forced a permission prompt.

Concretely:
- **No pipes to other tools** (`| sort`, `| awk`, `| grep`). Run the `find` / `stat` on its own and
  do the sorting, filtering, and median yourself from the output — that work belongs in your head
  and in the plan, not in a shell pipeline.
- **No `for` / `while` / `if` loops, and no `set -e`.** Control flow is opaque to the matcher and
  always prompts. Glob across folders in a single `stat` / `mv` call instead of looping, and chain
  steps with `&&` — which also stops on the first failure, so `set -e` isn't needed.
- **No shell variables.** `dest="…"; mv a "$dest"` prompts because the assignment isn't an approved
  command. Write the full literal paths into each `mv`.

## Step 1: Parse the Episode Listing

If given an image, read it carefully — extract every episode title listed under each disc heading,
in order. Ignore special features. Build a mapping like:

```
Disc 1: Episode A, Episode B, Episode C
Disc 2: Episode D, Episode E, Episode F, Episode G, Episode H
...
```

Assign sequential episode numbers starting at 1 across all discs.

**If any text in the image is unclear, blurry, cut off, or ambiguous**, do not guess — stop and
ask the user for clarification before proceeding. Be specific about what you cannot read:

> "I can read most of the episode listing, but I'm having trouble with:
> - Disc 2, episode 3: the title looks like 'The ??? of ???' — can you type it out?
> - Disc 4 heading: partially cut off, could be Disc 4 or Disc 6 — which is it?
>
> Please clarify these entries and I'll continue."

Only proceed once every disc heading and every episode title is confirmed.

## Step 2: Find Source Directories

Look in the source directory for folders matching the disc pattern. Common patterns:
- `Show Name Season 1 Disc 1`, `Show Name Season 1 Disc 2`, ...
- `SHOW NAME S1 D1`, `SHOW NAME S1 D2`, ...
- `S01D01`, `S01D02`, ...

```bash
find "<source_dir>" -maxdepth 1 -type d -iname "*disc*"
```

For the compact forms (`S1 D1`, `S01D01`), use `-iname "*d[0-9]*"` instead. If neither pattern fits
the folder names you see, drop the `-iname` filter, list all directories, and pick out the disc
folders yourself. Order the discs numerically when you build the plan (the output isn't sorted, and
piping to `sort` would trigger a prompt).

## Step 3: List and Size the Episode Files

Get byte-exact sizes for every video file across all disc folders in a **single** `stat` call —
the glob expands to every match, so you don't need a loop:

```bash
# macOS — prints size in bytes then full path
stat -f "%z %N" "<source_dir>"/*Disc*/*.mkv 2>/dev/null

# Linux
stat -c "%s %n" "<source_dir>"/*Disc*/*.mkv 2>/dev/null
```

Adjust the folder glob (`*Disc*`, `*D[0-9]*`, …) to match the real names, and add `*.mp4` / `*.m2ts`
globs to the same command if those extensions are present. The `2>/dev/null` suppresses errors for
globs that match nothing.

From this one listing you can do everything that follows — no per-disc loop needed.

**Filter to episode files.** Episode files are at least **200 MB** (209,715,200 bytes); anything
smaller is a menu, trailer, or featurette. **Explicitly report what you excluded** so gaps in track
numbering (e.g. a missing `t01` between `t00` and `t02`) aren't a mystery:

> "Skipped as menus/featurettes (<200 MB): Disc 1/t00.mkv, Disc 5/t01.mkv …"

If nothing was excluded, say so.

Files may be named `title_t00.mkv`, `title_t01.mkv`, etc., or carry a show-name prefix like
`Show Name Season 1 Disc 1_t03.mkv`. The numeric suffix determines episode order on that disc
regardless of the prefix.

**Stop and tell the user if** fewer disc folders are found than the listing specifies, or the number
of episode-sized files on a disc doesn't match the episode count for that disc. Do not proceed until
the user clarifies.

**Report sizes in decimal GB** (bytes ÷ 1,000,000,000) consistently, so the plan and your narration
agree — don't mix GB and GiB.

### Check for multi-episode (oversized) files

Calculate the **median** episode-file size (in bytes): collect the sizes, sort them, take the middle
value (or the average of the two middle values if the count is even).

If any file is **1.7× or more** the median, it may span multiple episodes. Estimate the count by
rounding to the nearest whole multiple (~2× → 2 episodes, ~3× → 3 episodes, …) and **stop to ask**:

> "The file `title_t02.mkv` in Disc 3 is about 3× the size of the others (~6.3 GB vs ~2.1 GB
> median). Should this be treated as a multi-episode file?
> - **Double** → `Show - s01e09-e10.mkv` (next episode becomes e11)
> - **Triple** → `Show - s01e09-e11.mkv` (next episode becomes e12)"

Present only the options that fit the size. The episode counter advances by the chosen count, and
later episodes shift up accordingly.

### Flag files that are suspiciously small, too

The 200 MB floor only catches obvious menus. A featurette, recap, or "play all" stub can clear
200 MB yet be nowhere near a real episode — e.g. a 768 MB file sitting beside 8 GB episodes. These
also slip past the count check: if a real episode wasn't ripped but a featurette was, the per-disc
count can still match by coincidence and the whole mapping silently shifts by one.

So after computing the median, also flag any file **below ~0.5× the median** (while still over
200 MB) as a likely non-episode. Real episodes in a season cluster tightly — often within 1.1× of
each other — so a genuine episode rarely trips this. Don't auto-drop it (a short episode is
possible) — **stop and ask**:

> "`…_t04.mkv` in Disc 1 is only 768 MB — about 0.09× the ~8.6 GB median of the other files. That's
> almost certainly a featurette, not an episode. Exclude it, or is it a genuinely short episode?"

## Step 4: Build the Rename Plan

Construct the full mapping of source path → destination filename. Episode numbering is sequential
across all discs, starting at e01.

Output format: `<Clean Show Name> - s<SS>e<EE>.<ext>`
- Show name cleaned per the rules above (colon dropped, no sanitized-character artifacts)
- Season number zero-padded to 2 digits: `s01`, `s02`
- Episode number zero-padded to 2 digits: `e01`, `e09`, `e10`
- Multi-episode file: `s01e09-e10.mkv` (double), `s01e09-e11.mkv` (triple), etc.
- **Keep each source file's extension**: a `.mp4` or `.m2ts` rip stays `.mp4`/`.m2ts` — never
  relabel it `.mkv`. The extension describes the container format, and a mismatched one breaks
  some players and media servers.

Show the user the full plan before executing. Include each file's size and, for multi-episode
files, the episode-count rationale:

```
Disc 1/title_t00.mkv  (2.1 GB)      →  Star Trek The Next Generation - s01e01.mkv  (Episode A)
Disc 1/title_t01.mkv  (2.0 GB)      →  Star Trek The Next Generation - s01e02.mkv  (Episode B)
Disc 1/title_t02.mkv  (8.2 GB, 2×)  →  Star Trek The Next Generation - s01e03-e04.mkv  (Episode C + D)
Disc 2/title_t00.mkv  (2.1 GB)      →  Star Trek The Next Generation - s01e05.mkv  (Episode E)
...
```

## Step 5: Duplicate Check

Before moving anything, list what's already in the destination and compare against your planned
filenames:

```bash
ls "<destination_dir>/" 2>/dev/null
```

If the directory doesn't exist yet (the command prints nothing or an error), there are no conflicts.
If **any** planned filename already appears in the listing, **stop entirely** — do not move any
files. Report which files conflict and ask the user how to proceed. (Comparing the listing yourself
keeps this to a single approved `ls`; a `for`/`if` loop would trigger a prompt.)

## Step 6: Create Destination and Execute

Emit **all moves as one `&&`-chained command** — every segment is a `mkdir`, `mv`, or `echo`, so the
whole thing runs without a prompt, and `&&` stops the chain on the first failure (no `set -e`
needed). Use **full literal paths**, not variables:

```bash
mkdir -p "<destination_dir>" && \
mv "<source_dir>/DISC FOLDER 1/prefix_t00.mkv" "<destination_dir>/Show Name - s01e01.mkv" && echo "Moved: s01e01 (Episode A)" && \
mv "<source_dir>/DISC FOLDER 1/prefix_t01.mkv" "<destination_dir>/Show Name - s01e02.mkv" && echo "Moved: s01e02 (Episode B)" && \
mv "<source_dir>/DISC FOLDER 1/prefix_t02.mkv" "<destination_dir>/Show Name - s01e03-e04.mkv" && echo "Moved: s01e03-e04 (Episode C + D)" && \
mv "<source_dir>/DISC FOLDER 2/prefix_t00.mkv" "<destination_dir>/Show Name - s01e05.mkv" && echo "Moved: s01e05 (Episode E)"
# ... one `mv … && echo …` per file, all in the same chained command
```

Keep it to a single tool call — do not split into one call per file, and do not introduce a loop or
variables (either would force a permission prompt and defeat the point).

## Step 7: Clean Up Empty Disc Folders

**Only run this if the Step 6 command exited successfully (exit code 0).** Because the chain is
joined with `&&`, a failed `mv` aborts the rest — if that happened, report the failure and stop
rather than cleaning up.

After the moves succeed, remove the now-empty disc folders with a single `rmdir` that lists every
folder as an argument:

```bash
rmdir "<source_dir>/DISC FOLDER 1" "<source_dir>/DISC FOLDER 2" "<source_dir>/DISC FOLDER 3" "<source_dir>/DISC FOLDER 4" "<source_dir>/DISC FOLDER 5" "<source_dir>/DISC FOLDER 6"
```

`rmdir` only removes a directory if it is empty, and it skips (with a harmless error) any folder that
still holds menus or featurettes, continuing to the rest — so this is safe without `rm -rf` and
without a loop. Report which folders were removed and which were kept.

## Step 8: Verify

```bash
ls "<destination_dir>/"
```

Confirm all expected files are present and print a summary of what was done.

## Important Rules

- **Derive a clean show name and confirm it** — ripping tools sanitize `": "` → `"- "`, so delete
  any `-` that is directly glued to the preceding word (e.g. `Star Trek- The Next Generation` →
  `Star Trek The Next Generation`); never carry a dangling hyphen into output filenames; confirm
  the exact clean name with the user before building filenames
- **Keep the run prompt-free** — build commands only from the approved binaries (`find`, `stat`,
  `ls`, `mkdir`, `mv`, `rmdir`, `echo`); avoid pipes to other tools, `for`/`if` loops, `set -e`, and
  shell variables, since each forces a permission prompt
- **Preserve the source extension** — the destination filename keeps the source file's
  extension (`.mkv`, `.mp4`, `.m2ts`); never relabel the container
- **Never overwrite** — always check the destination for conflicts before moving anything
- **Never guess episode order** — use the listing from the image/text exactly
- **Never guess unreadable image text** — ask for clarification on any blurry, cut-off, or
  ambiguous text before building the episode mapping
- **Ask about multi-episode files** before building the rename plan, not after
- **Flag suspiciously small files** — a file over 200 MB but below ~0.5× the median is probably a
  featurette, not an episode; ask before excluding it
- If source files are missing or the count doesn't match the episode listing, tell the user before
  proceeding
- If the user provides a partial listing (e.g. only some discs), only rename those discs
- **Skip small files** — anything under 200 MB is a menu, trailer, or featurette, never an episode
- **Always disclose filtered files** — explicitly tell the user which files were excluded and why
- **Batch all moves into one `&&`-chained command** — do not issue one tool call per file
- **Never force-remove source folders** — use `rmdir` (not `rm -rf`) so only empty directories are
  deleted after the rename
