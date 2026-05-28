---
name: rip-rename
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
- `SHOW NAME S1 D1`, `SHOW NAME S1 D2`, ...
- `Show Name Season 1 Disc 1`, ...
- `S01D01`, `S01D02`, ...

```bash
find "<source_dir>" -maxdepth 1 -type d -iname "*D[0-9]*" | sort
```

List the **episode files** in each disc directory. Episode files are video files (`.mkv`, `.mp4`,
`.m2ts`) that are **at least 200 MB** — this excludes menu tracks, trailers, and featurettes.

```bash
find "<source_dir>/DISC FOLDER NAME" -maxdepth 1 -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.m2ts" \) | sort
```

Then filter by size (bytes), keeping only files ≥ 200 MB (209715200 bytes):

```bash
# macOS
stat -f "%z %N" "<source_dir>/DISC FOLDER NAME"/title_t*.mkv | awk '$1 >= 209715200 {print $2}' | sort

# Linux
stat -c "%s %n" "<source_dir>/DISC FOLDER NAME"/title_t*.mkv | awk '$1 >= 209715200 {print $2}' | sort
```

Files will typically be named `title_t00.mkv`, `title_t01.mkv`, etc. The numeric order of the
filenames corresponds to episode order on that disc.

**Stop and tell the user if:**
- Fewer disc folders are found than the listing specifies (e.g., listing has 6 discs but only 5
  folders exist)
- The number of episode-sized files on a disc doesn't match the episode count for that disc in the
  listing

Do not proceed until the user clarifies.

## Step 3: Check File Sizes for Multi-Episode Files

Get byte-exact sizes for all episode-sized files across every disc:

```bash
# macOS — prints size in bytes then filename
stat -f "%z %N" "<source_dir>/DISC FOLDER"/title_t*.mkv

# Linux
stat -c "%s %n" "<source_dir>/DISC FOLDER"/title_t*.mkv
```

Calculate the **median file size** (in bytes) across all episode files:
1. Collect all sizes into a list
2. Sort the list numerically
3. Take the middle value (or average of the two middle values if the count is even)

If any file is **1.7× or more** the median size, it may span multiple episodes.

Estimate the episode count for each oversized file by rounding to the nearest whole multiple:
- ~2× median → likely 2 episodes
- ~3× median → likely 3 episodes
- etc.

For each oversized file, **stop and ask the user**:

> "The file `title_t02.mkv` in Disc 3 is about 3× the size of other episodes (~6.3 GB vs ~2.1 GB
> median). Should this be treated as a multi-episode file?
> - **Single** → `Show - s01e09.mkv` (one episode number used)
> - **Double** → `Show - s01e09-e10.mkv` (two episode numbers consumed, next episode becomes e11)
> - **Triple** → `Show - s01e09-e11.mkv` (three episode numbers consumed, next episode becomes e12)"

Present only the options that make sense given the file size. Wait for the user's answer before
proceeding. The episode counter advances by the chosen count, and subsequent episodes shift up
accordingly.

## Step 4: Build the Rename Plan

Construct the full mapping of source path → destination filename. Episode numbering is sequential
across all discs, starting at e01.

Output format: `<Show Name> - s<SS>e<EE>.mkv`
- Season number zero-padded to 2 digits: `s01`, `s02`
- Episode number zero-padded to 2 digits: `e01`, `e09`, `e10`
- Multi-episode file: `s01e09-e10.mkv` (double), `s01e09-e11.mkv` (triple), etc.

Show the user the full plan before executing. For each file include the size and, for
multi-episode files, the episode count rationale:

```
Disc 1/title_t00.mkv  (2.1 GB)      →  Show Name - s01e01.mkv  (Episode A)
Disc 1/title_t01.mkv  (2.0 GB)      →  Show Name - s01e02.mkv  (Episode B)
Disc 1/title_t02.mkv  (8.2 GB, 2×)  →  Show Name - s01e03-e04.mkv  (Episode C + D)
Disc 2/title_t00.mkv  (2.1 GB)      →  Show Name - s01e05.mkv  (Episode E)
...
```

## Step 5: Duplicate Check

Before moving any files, verify the destination directory has no conflicts by running a real shell
check for each planned destination file:

```bash
conflicts=0
for dest in \
  "<destination_dir>/Show Name - s01e01.mkv" \
  "<destination_dir>/Show Name - s01e02.mkv" \
  "<destination_dir>/Show Name - s01e03.mkv"; do
  if [ -e "$dest" ]; then
    echo "CONFLICT: $dest already exists"
    conflicts=1
  fi
done
if [ "$conflicts" -eq 1 ]; then
  echo "Stopping — resolve conflicts before proceeding"
fi
```

Generate this script with the actual planned destination paths filled in. If **any** conflict is
found, **stop entirely** — do not move any files. Report which files conflict and ask the user how
to proceed.

## Step 6: Create Destination and Execute

```bash
mkdir -p "<destination_dir>"
```

Move each file individually, one at a time, reporting each move before executing it:

```bash
mv "<source_dir>/DISC FOLDER 1/title_t00.mkv" "<destination_dir>/Show Name - s01e01.mkv"
echo "Moved: Show Name - s01e01.mkv (Episode A)"

mv "<source_dir>/DISC FOLDER 1/title_t01.mkv" "<destination_dir>/Show Name - s01e02.mkv"
echo "Moved: Show Name - s01e02.mkv (Episode B)"

mv "<source_dir>/DISC FOLDER 1/title_t02.mkv" "<destination_dir>/Show Name - s01e03-e04.mkv"
echo "Moved: Show Name - s01e03-e04.mkv (Episode C + D)"

# ... one mv + echo per file
```

Issue each `mv` and `echo` as a separate command. Do not batch moves.

## Step 7: Verify

```bash
ls "<destination_dir>/"
```

Confirm all expected files are present and print a summary of what was done.

## Important Rules

- **Never overwrite** — always check for conflicts before moving anything
- **Never guess episode order** — use the listing from the image/text exactly
- **Never guess unreadable image text** — ask for clarification on any blurry, cut-off, or
  ambiguous text before building the episode mapping
- **Ask about multi-episode files** before building the rename plan, not after
- If source files are missing or the count doesn't match the episode listing, tell the user
  before proceeding
- If the user provides a partial listing (e.g., only some discs), only rename those discs
- **Skip small files** — any file under 200 MB is not an episode (it's a menu, trailer, or
  featurette); never assign it an episode number
