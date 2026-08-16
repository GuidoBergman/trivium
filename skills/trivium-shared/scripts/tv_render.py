#!/usr/bin/env python3
"""Render notes.jsonl into NOTES.md for human reading.

notes.jsonl is the source of truth. NOTES.md is generated and should never be
edited by hand, because the next render overwrites it.

Usage:
  tv_render.py <book>/notes.jsonl [--out NOTES.md] [--rejected REJECTED.jsonl]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402

SPEAKER_WARNING = {
    "cited": "someone the author is quoting, not the author",
    "rejected": "a position the author sets up in order to reject",
    "hypothetical": "stated hypothetically, not asserted",
    "conversation": "came out of a conversation, not from the book",
}


def sort_key(note):
    tokens = tvlib.locator_tokens(note.get("locator", ""))
    chapter = next((t for t in sorted(tokens) if t.startswith("ch")), "ch999")
    digits = "".join(c for c in chapter if c.isdigit())
    return (int(digits) if digits else 999, note.get("id", ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes")
    ap.add_argument("--out")
    ap.add_argument("--rejected")
    args = ap.parse_args()

    notes, errors = tvlib.read_notes(args.notes)
    for err in errors:
        print(f"notes error: {err}", file=sys.stderr)

    book_dir = os.path.dirname(os.path.abspath(args.notes))
    out = args.out or os.path.join(book_dir, "NOTES.md")
    rejected_path = args.rejected or os.path.join(book_dir, "REJECTED.jsonl")

    notes.sort(key=sort_key)

    unverified = [n for n in notes if not n.get("verified")]

    lines = [
        "# Notes",
        "",
        "Generated from `notes.jsonl`. Do not edit by hand.",
        "",
        f"{len(notes)} notes.",
        "",
    ]
    if unverified:
        # Rendering does not verify anything. Saying so here stops a rendered
        # file from looking more trustworthy than the notes behind it.
        lines += [
            f"**{len(unverified)} of these carry no verification record.** "
            "Run `tv_verify.py` and the stage 2 and 3 checks before relying on "
            "them.",
            "",
        ]

    current = None
    for note in notes:
        tokens = tvlib.locator_tokens(note["locator"])
        chapter = next((t for t in sorted(tokens) if t.startswith("ch")), "unplaced")
        if chapter != current:
            current = chapter
            lines += [f"## {chapter}", ""]

        warning = SPEAKER_WARNING.get(note["speaker"])
        lines.append(f"### {note['id']}")
        lines.append("")
        lines.append(note["claim"])
        lines.append("")
        if warning:
            lines.append(f"**Attribution: {warning}.**")
            lines.append("")
        if note["kind"] == "figure":
            lines.append(f"**From a page image, not from text.** "
                         f"Evidence: `{note['evidence']}`")
            lines.append("")
            lines.append(f"![{note['id']}]({note['evidence']})")
        else:
            quote = note.get("quote", "").strip().replace("\n", " ")
            lines.append(f"> {quote}")
        lines.append("")
        meta = f"`{note['locator']}` · {note['kind']} · {note['scope']}"
        if note.get("verified"):
            meta += f" · verified: {note['verified']}"
        lines.append(meta)
        lines.append("")

    if os.path.exists(rejected_path):
        dropped, _ = [], None
        with open(rejected_path, encoding="utf-8") as fh:
            dropped = [line for line in fh if line.strip()]
        if dropped:
            lines += [
                "## Dropped",
                "",
                f"{len(dropped)} claim(s) failed verification and were removed. "
                "See `REJECTED.jsonl` for the reasons. A cluster of drops in one "
                "chapter usually means an extraction problem, not an author problem.",
                "",
            ]

    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {out} ({len(notes)} notes)")


if __name__ == "__main__":
    main()
