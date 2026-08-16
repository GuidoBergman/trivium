#!/usr/bin/env python3
"""Stage 1 verification: does every quote actually exist in the book?

This is the only stage with no model in the loop. A quote either appears in the
extracted text or it does not, and no amount of confident prose can change that.
Everything else in Trivium is a judgement call layered on top of this floor.

It also checks the locator, which catches notes whose quote is real but whose
chapter or page is wrong.

Matching ladder, strictest first:
  EXACT       byte-for-byte
  NORMALIZED  unicode punctuation folded, whitespace runs collapsed
  PUNCT       letters and digits only, case-insensitive (survives hyphenation
              across line breaks, quote styles and lost spacing)
  FAIL        the quote is not in the book

Quotes may elide with "..." between kept fragments. Each fragment must appear,
in order, within a reasonable window.

Usage:
  tv_verify.py <book>/notes.jsonl --text <topic>/text/<slug>.txt
               [--report verification.json] [--strict]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402

ELISION_WINDOW = 3000   # characters allowed between elided fragments
MIN_FRAGMENT = 12       # a fragment shorter than this is not evidence of anything


def split_elisions(quote):
    parts = []
    for chunk in quote.replace("[...]", "...").replace("…", "...").split("..."):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts or [quote.strip()]


def search_level(text, idx, fragments, mode):
    """Find fragments in order. Returns (start_offset, end_offset) or None."""
    cursor = 0
    first = last = None

    for i, fragment in enumerate(fragments):
        frag, _ = tvlib.build(fragment, mode)
        frag = frag.strip()
        if len(frag) < MIN_FRAGMENT and len(fragments) > 1:
            return None
        if not frag:
            return None

        pos = text.find(frag, cursor)
        if pos < 0:
            return None
        if i > 0 and pos - cursor > ELISION_WINDOW:
            return None

        if first is None:
            first = idx[pos]
        last = idx[min(pos + len(frag) - 1, len(idx) - 1)]
        cursor = pos + len(frag)

    return (first, last)


def verify_figure(note, notes_dir):
    """A figure note is checked differently, and the difference is honest.

    There is no quote to match, because the content never existed as text. What
    can be checked mechanically is that the evidence image exists, so a reader
    can open the same picture the claim was written from. Whether the claim is
    true of that picture is a judgement, and it belongs to the second reader in
    stage 2v, not here.
    """
    result = {"id": note["id"], "status": "FIGURE", "level": "IMAGE",
              "found_at": None, "found_locator": note.get("locator"),
              "issues": []}

    evidence = note.get("evidence", "")
    path = evidence if os.path.isabs(evidence) else \
        os.path.normpath(os.path.join(notes_dir, evidence))

    if not os.path.exists(path):
        result["status"] = "FAIL"
        result["issues"].append(f"evidence image not found: {evidence}")
    else:
        result["evidence_path"] = path
        result["issues"].append(
            "evidence is a page image, not a quote. Weaker than a text note, "
            "and the brief must say so."
        )
    return result


def verify_note(note, levels, mapping):
    fragments = split_elisions(note["quote"])
    result = {"id": note["id"], "status": "FAIL", "level": None,
              "found_at": None, "found_locator": None, "issues": []}

    for name, (text, idx) in levels:
        span = search_level(text, idx, fragments, "alnum" if name == "PUNCT" else "norm")
        if span:
            result["status"] = "PASS"
            result["level"] = name
            result["found_at"] = span[0]
            result["found_locator"] = tvlib.locate(mapping, span[0])
            break

    if result["status"] == "FAIL":
        result["issues"].append("quote not found in the extracted text")
        return result

    claimed = tvlib.locator_tokens(note["locator"])
    actual = tvlib.locator_tokens(result["found_locator"])
    if claimed and actual and not (claimed & actual):
        result["issues"].append(
            f"locator says {note['locator']!r} but the quote is at "
            f"{result['found_locator']!r}"
        )
        result["status"] = "LOCATOR_MISMATCH"

    if result["level"] == "PUNCT":
        result["issues"].append(
            "matched only after stripping punctuation, so the quote's "
            "punctuation does not match the book verbatim"
        )

    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes")
    ap.add_argument("--text", required=True)
    ap.add_argument("--report", help="write the full report here")
    ap.add_argument("--strict", action="store_true",
                    help="treat locator mismatches and PUNCT matches as failures")
    args = ap.parse_args()

    map_path = args.text.replace(".txt", ".map.json")
    for path in (args.text, map_path):
        if not os.path.exists(path):
            tvlib.die(f"no such file: {path}")

    with open(args.text, encoding="utf-8") as fh:
        raw = fh.read()
    mapping = tvlib.load_map(map_path)

    notes, errors = tvlib.read_notes(args.notes)
    if errors:
        for err in errors:
            print(f"notes error: {err}", file=sys.stderr)
        if not notes:
            tvlib.die("no readable notes")

    norm_text, norm_idx = tvlib.build(raw, "norm")
    alnum_text, alnum_idx = tvlib.build(raw, "alnum")
    levels = [
        ("EXACT", (raw, list(range(len(raw))))),
        ("NORMALIZED", (norm_text, norm_idx)),
        ("PUNCT", (alnum_text, alnum_idx)),
    ]

    notes_dir = os.path.dirname(os.path.abspath(args.notes))
    results = [
        verify_figure(note, notes_dir) if note.get("kind") == "figure"
        else verify_note(note, levels, mapping)
        for note in notes
    ]

    by_status = {}
    for res in results:
        by_status[res["status"]] = by_status.get(res["status"], 0) + 1

    failing = [r for r in results if r["status"] == "FAIL"]
    if args.strict:
        failing += [r for r in results if r["status"] == "LOCATOR_MISMATCH"]
        failing += [r for r in results if r["level"] == "PUNCT"
                    and r["status"] == "PASS"]

    report = {
        "notes_file": os.path.abspath(args.notes),
        "text_file": os.path.abspath(args.text),
        "note_errors": errors,
        "counts": by_status,
        "levels": {name: sum(1 for r in results if r["level"] == name)
                   for name in ("EXACT", "NORMALIZED", "PUNCT")},
        "must_drop": sorted({r["id"] for r in failing}),
        "results": results,
    }

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"{len(results)} notes checked")
    for status, count in sorted(by_status.items()):
        print(f"  {status}: {count}")
    print(f"  match levels: {report['levels']}")

    if failing:
        print(f"\n{len(failing)} note(s) must be dropped:")
        for res in failing:
            print(f"  {res['id']}: {'; '.join(res['issues'])}")

    raise SystemExit(1 if failing else 0)


if __name__ == "__main__":
    main()
