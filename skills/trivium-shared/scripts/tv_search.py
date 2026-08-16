#!/usr/bin/env python3
"""The search seam.

Every skill that needs to find something in the books calls this and nothing
else. Today it scans the extracted text directly, which is fast enough for the
scale Trivium targets and completely auditable. If a topic ever outgrows it,
swap the body of `search()` for a real index and no skill has to change.

Search runs on normalised text, so curly quotes, hyphenation across line breaks
and lost spacing do not cause misses.

Usage:
  tv_search.py <topic-dir> "term" ["another term" ...] [--book slug]
               [--context 240] [--max 20] [--json]
"""

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402


def load_books(topic_dir, only=None):
    books = []
    for txt in sorted(glob.glob(os.path.join(topic_dir, "text", "*.txt"))):
        slug = os.path.basename(txt)[:-4]
        if only and slug not in only:
            continue
        map_path = txt[:-4] + ".map.json"
        if not os.path.exists(map_path):
            continue
        with open(txt, encoding="utf-8") as fh:
            raw = fh.read()
        norm, norm_idx = tvlib.build(raw, "norm")
        alnum, alnum_idx = tvlib.build(raw, "alnum")
        books.append({
            "slug": slug, "raw": raw,
            "norm": norm.lower(), "norm_idx": norm_idx,
            "alnum": alnum, "alnum_idx": alnum_idx,
            "map": tvlib.load_map(map_path),
        })
    return books


def search(books, terms, context=240, limit=20):
    """Search twice per term.

    The normalised pass respects word boundaries and punctuation. The alnum
    pass strips both, which is what finds a word the extractor split across a
    line break, such as "improve-\\nment". PDFs are full of these, so skipping
    the second pass silently loses real matches.
    """
    hits, section_scores, seen = [], {}, set()

    for book in books:
        for term in terms:
            for mode in ("norm", "alnum"):
                needle, _ = tvlib.build(term, mode)
                needle = needle.strip()
                if mode == "norm":
                    needle = needle.lower()
                if not needle:
                    continue

                haystack = book[mode]
                index = book["norm_idx" if mode == "norm" else "alnum_idx"]

                for pos in tvlib.find_all(haystack, needle, limit=200):
                    offset = index[pos]
                    # The two passes find the same occurrence twice.
                    key = (book["slug"], offset // 8)
                    if key in seen:
                        continue
                    seen.add(key)

                    locator = tvlib.locate(book["map"], offset)
                    skey = (book["slug"], locator)
                    section_scores[skey] = section_scores.get(skey, 0) + 1

                    start = max(0, offset - context // 2)
                    end = min(len(book["raw"]), offset + len(term) + context // 2)
                    snippet = re.sub(r"\s+", " ", book["raw"][start:end]).strip()

                    hits.append({
                        "book": book["slug"],
                        "term": term,
                        "locator": locator,
                        "offset": offset,
                        "matched_via": mode,
                        "snippet": snippet,
                    })

    hits.sort(key=lambda h: (h["book"], h["offset"]))
    sections = [
        {"book": b, "locator": loc, "hits": n}
        for (b, loc), n in sorted(section_scores.items(),
                                  key=lambda kv: -kv[1])
    ]
    return hits[:limit], sections, len(hits)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic")
    ap.add_argument("terms", nargs="+")
    ap.add_argument("--book", action="append", help="restrict to this slug")
    ap.add_argument("--context", type=int, default=240)
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    books = load_books(args.topic, set(args.book) if args.book else None)
    if not books:
        tvlib.die(f"no extracted books found under {args.topic}/text/")

    hits, sections, total = search(books, args.terms, args.context, args.max)

    if args.json:
        print(json.dumps({"total": total, "sections": sections, "hits": hits},
                         indent=2, ensure_ascii=False))
        return

    if not hits:
        print(f"No matches for {', '.join(repr(t) for t in args.terms)} "
              f"in {len(books)} book(s).")
        print("The words may not be the ones these authors use. Check the "
              "vocabulary lines in each MAP.md and search their terms instead.")
        return

    print(f"{total} match(es), showing {len(hits)}.\n")
    print("Densest sections:")
    for sec in sections[:8]:
        print(f"  {sec['book']} {sec['locator']}: {sec['hits']}")
    print()
    for hit in hits:
        print(f"[{hit['book']} {hit['locator']}] ...{hit['snippet']}...")
        print()


if __name__ == "__main__":
    main()
