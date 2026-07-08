#!/usr/bin/env python3
"""Movie taste analysis: joins a Plex/Synology library export, a Letterboxd export,
and a MovieList ranked-list JSON into one analysis JSON + printed summary.

Matching is year-aware because bare titles collide (Road House 1989/2024,
"Suicide Squad" vs "The Suicide Squad") and Letterboxd uses short canonical
titles ("Glass Onion", "F1", "The Accountant2" with a superscript 2).
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def norm(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    t = t.replace('&', 'and')
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def keys(t):
    """Alias keys for a title: full, article-stripped, subtitle-stripped, no-space."""
    n = norm(t)
    if not n:
        # All-non-Latin title normalizes to '' — fall back to the raw title so
        # such titles only match themselves instead of sharing one empty key.
        return {t.strip().lower()}
    out = {n, n.replace(' ', '')}
    na = re.sub(r'^(the|a|an) ', '', n)
    out |= {na, na.replace(' ', '')}
    # Split on subtitle separators only; a bare hyphen is part of the title (Spider-Man).
    parts = re.split(r'[:–—]|\s-\s', t)
    if len(parts) > 1 and len(norm(parts[0])) >= 4:
        p = norm(parts[0])
        out |= {p, re.sub(r'^(the|a|an) ', '', p)}
    return out


class Index:
    """Title index with year-aware fuzzy matching."""

    def __init__(self):
        self.m = defaultdict(list)
        self.records = []

    def add(self, title, year, payload):
        rec = (title, year, payload)
        self.records.append(rec)
        for k in keys(title):
            if rec not in self.m[k]:
                self.m[k].append(rec)

    def match(self, title, year_hint):
        cands = []
        for k in keys(title):
            for rec in self.m.get(k, []):
                if rec not in cands:
                    cands.append(rec)
        if not cands:
            return None
        if year_hint is not None:
            exact = [r for r in cands if r[1] == year_hint]
            near = [r for r in cands if r[1] is not None and abs(r[1] - year_hint) <= 1]
            if exact:
                return exact[0]
            if near:
                return near[0]
            # Years known on both sides but far apart -> likely a different film.
            if all(r[1] is not None for r in cands):
                return None
        return cands[0] if len(cands) == 1 else None


def spearman(pairs):
    n = len(pairs)
    if n < 5:
        return None

    def rankify(vals):
        s = sorted(range(n), key=lambda i: vals[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[s[j + 1]] == vals[s[i]]:
                j += 1
            for k in range(i, j + 1):
                rk[s[k]] = (i + j) / 2 + 1
            i = j + 1
        return rk

    xs = rankify([p[0] for p in pairs])
    ys = rankify([p[1] for p in pairs])
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    return cov / (vx * vy) ** 0.5 if vx and vy else None


# Tooltips mostly hold freeform opinions; only this exact shape marks a tier boundary.
DIVIDE = re.compile(r'(Great|Good|OK|Bad)/(Great|Good|OK|Bad) Divide')


def load_owned(path):
    with open(path, encoding='utf-8') as f:
        syn = json.load(f)
    owned = Index()
    seen = set()
    dupes = 0
    for lib in syn.get('libraries', []):
        if lib.get('type') != 'movie':
            continue
        for m in lib.get('movies', []):
            t, y = m['title'], m.get('year')
            if (norm(t), y) in seen:
                dupes += 1
                continue
            seen.add((norm(t), y))
            owned.add(t, y, None)
    return owned, dupes


def load_letterboxd(lb_dir):
    lb = Path(lb_dir)
    for req in ('ratings.csv', 'watched.csv'):
        if not (lb / req).exists():
            sys.exit(f'Letterboxd export is missing {req}: {lb / req}')
    ratings, watched = Index(), Index()
    watchlist, rewatch = [], Counter()
    with open(lb / 'ratings.csv', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            ratings.add(r['Name'], int(r['Year']), float(r['Rating']))
    with open(lb / 'watched.csv', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            watched.add(r['Name'], int(r['Year']) if r['Year'] else None, None)
    wl = lb / 'watchlist.csv'
    if wl.exists():
        with open(wl, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                watchlist.append((r['Name'], int(r['Year']) if r['Year'] else None))
    diary = lb / 'diary.csv'
    if diary.exists():
        with open(diary, encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                if r.get('Rewatch') == 'Yes':
                    rewatch[(r['Name'], int(r['Year']) if r['Year'] else None)] += 1
    return ratings, watched, watchlist, rewatch


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--synology',
                    help='Plex/Synology library JSON export (omit to skip ownership analysis)')
    ap.add_argument('--letterboxd', required=True, help='Letterboxd export directory')
    ap.add_argument('--movielist', required=True, help='MovieList ranked-lists JSON')
    ap.add_argument('--out', required=True, help='Path to write analysis JSON')
    args = ap.parse_args()

    owned, dupes = load_owned(args.synology) if args.synology else (None, 0)
    ratings, watched, watchlist, rewatch = load_letterboxd(args.letterboxd)
    with open(args.movielist, encoding='utf-8') as f:
        ml = json.load(f)

    def owned_flag(name, year):
        """True/False when a library export was provided, else None (unknown)."""
        return owned.match(name, year) is not None if owned else None

    # --- Ranked lists vs ratings ---
    consistency, tier_avgs, mismatches, unmatched = {}, {}, [], []
    top_ranked = []
    for lst in ml.get('lists', []):
        year = lst['title']
        try:
            yh = int(year)
        except ValueError:
            yh = None
        pairs, yr_items = [], []
        seg, segs = 'Great', defaultdict(list)
        for i, it in enumerate(lst['list']):
            title = it['item'] if isinstance(it, dict) else it
            tip = it.get('tooltip', '') if isinstance(it, dict) else ''
            rec = ratings.match(title, yh)
            if rec:
                pairs.append((i + 1, -rec[2]))
                yr_items.append((i + 1, title, rec[2]))
                segs[seg].append(rec[2])
            else:
                unmatched.append((year, title))
            # A divide tooltip sits on the LAST film of the upper tier, so this film's
            # tier was already recorded above; the tooltip advances seg for the next film.
            m = DIVIDE.search(tip)
            if m:
                seg = m.group(2)
            if i < 5:
                top_ranked.append({
                    'year': year, 'rank': i + 1, 'title': title,
                    'rating': rec[2] if rec else None,
                    'owned': owned_flag(title, yh),
                })
        rho = spearman(pairs)
        consistency[year] = {'matched': len(pairs), 'total': len(lst['list']),
                             'spearman': round(rho, 3) if rho is not None else None}
        if len(segs) > 1:
            tier_avgs[year] = {k: {'avg': round(sum(v) / len(v), 2), 'n': len(v)}
                               for k, v in segs.items()}
        n = len(lst['list'])
        for rank, title, rating in yr_items:
            if rank <= n / 3 and rating <= 2.5:
                mismatches.append({'year': year, 'rank': rank, 'of': n, 'title': title,
                                   'rating': rating, 'kind': 'ranked high, rated low'})
            elif rank > 2 * n / 3 and rating >= 4:
                mismatches.append({'year': year, 'rank': rank, 'of': n, 'title': title,
                                   'rating': rating, 'kind': 'ranked low, rated high'})

    # --- Taste stats ---
    dist = Counter(r[2] for r in ratings.records)
    by_decade = defaultdict(list)
    for _, y, rating in ratings.records:
        by_decade[y // 10 * 10].append(rating)

    loved = sorted([{'rating': r, 'year': y, 'title': n, 'owned': owned_flag(n, y)}
                    for n, y, r in ratings.records if r >= 4.5],
                   key=lambda x: (-x['rating'], x['year']))
    low = sorted([(r, y, n) for n, y, r in ratings.records if r <= 1.0])
    if owned:
        four_not_owned = sorted([(y, n) for n, y, r in ratings.records
                                 if r == 4 and not owned_flag(n, y)])
        wl_not_owned = sorted(
            [(y, n) for n, y in watchlist
             if not owned_flag(n, y) and not watched.match(n, y)],
            key=lambda x: (x[0] is None, x[0]))
        owned_unlogged = sorted(
            [(y, t) for t, y, _ in owned.records
             if not ratings.match(t, y) and not watched.match(t, y)],
            key=lambda x: (x[0] is None, x[0]))
    else:
        four_not_owned, wl_not_owned, owned_unlogged = [], [], []
    rewatched = sorted(
        [{'times': c, 'title': n, 'year': y,
          'rating': (ratings.match(n, y) or (None, None, None))[2]}
         for (n, y), c in rewatch.items()],
        key=lambda x: (-x['times'], -(x['rating'] or 0)))

    report = {
        'counts': {'owned_unique': len(owned.records) if owned else None,
                   'owned_duplicate_entries': dupes if owned else None,
                   'rated': len(ratings.records), 'watched': len(watched.records),
                   'watchlist': len(watchlist)},
        'rating_distribution': {str(k): v for k, v in sorted(dist.items())},
        'rating_mean': round(sum(r[2] for r in ratings.records) / len(ratings.records), 2),
        'by_decade': {str(d): {'n': len(v), 'avg': round(sum(v) / len(v), 2)}
                      for d, v in sorted(by_decade.items())},
        'consistency_by_year': consistency,
        'tier_averages_by_year': tier_avgs,
        'mismatches': mismatches,
        'unmatched_list_entries': len(unmatched),
        'top5_per_year': top_ranked,
        'loved_4.5_plus': loved,
        'four_star_not_owned': four_not_owned,
        'low_rated_1_or_less': low,
        'watchlist_not_owned_unseen': wl_not_owned,
        'owned_never_logged': owned_unlogged,
        'rewatched': rewatched[:30],
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)

    # --- Printed summary (compact; full detail lives in the JSON) ---
    p = print
    c = report['counts']
    if owned:
        p(f"Owned {c['owned_unique']} unique movies ({c['owned_duplicate_entries']} duplicate format entries); "
          f"rated {c['rated']}, watched {c['watched']}, watchlist {c['watchlist']}.")
    else:
        p(f"No library export given, ownership analysis skipped; "
          f"rated {c['rated']}, watched {c['watched']}, watchlist {c['watchlist']}.")
    p(f"Rating mean {report['rating_mean']}; distribution {report['rating_distribution']}")
    p('\nConsistency (list rank vs stars, Spearman):')
    for y, v in consistency.items():
        p(f"  {y}: rho={v['spearman']} ({v['matched']}/{v['total']} matched)")
    p('\nTier averages (Great/Good/OK/Bad):')
    for y, segs in tier_avgs.items():
        p(f"  {y}: " + ', '.join(f"{k}={v['avg']} (n={v['n']})" for k, v in segs.items()))
    p(f'\nMismatches ({len(mismatches)}):')
    for m in mismatches:
        p(f"  {m['year']} #{m['rank']}/{m['of']} {m['title']} rated {m['rating']} — {m['kind']}")
    p(f"\nRated 4.5+ ({len(loved)}{'; * = not owned' if owned else ''}):")
    for x in loved:
        p(f"  {x['rating']} {x['year']} {x['title']}{' *' if x['owned'] is False else ''}")
    if owned:
        p(f"\n4.0-rated and not owned: {len(four_not_owned)} (see JSON)")
        p(f"Watchlist, unseen, not owned: {len(wl_not_owned)} (see JSON)")
        p(f"Owned but never logged: {len(owned_unlogged)} (see JSON)")
    p('\nMost rewatched:')
    for x in rewatched[:15]:
        p(f"  {x['times']}x [{x['rating']}] {x['title']} ({x['year']})")
    p(f"\nWrote full analysis to {args.out}")


if __name__ == '__main__':
    sys.exit(main())
