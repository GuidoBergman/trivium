#!/usr/bin/env python3
"""Where does this topic stand, and what should happen next.

Reads the filesystem rather than any record of what was supposed to happen, so it
cannot report a book as studied because something said it was. A book is studied
when its notes exist.

Usage:
  tv_status.py [topic-dir]     defaults to walking up from the current directory
  tv_status.py --json
"""

import argparse
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402

BOOK_EXT = (".pdf", ".epub", ".azw3", ".azw", ".mobi", ".prc")
ACTIVE_WINDOW = 15 * 60  # notes touched this recently: a run is probably still going
FLAT_KEY = re.compile(r"^([a-z_]+):[ \t]*([^\n#]+?)[ \t]*(?:#.*)?$", re.M)


def find_topic(start):
    """Walk up looking for a config, the way the skills do."""
    here = os.path.abspath(start)
    while True:
        for candidate in (here, os.path.join(here, ".trivium")):
            if os.path.exists(os.path.join(candidate, "trivium.config.yaml")):
                return candidate
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def read_config(path):
    """Pull the flat scalar settings. Deliberately not a YAML parser."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {}
    wanted = {"title", "profile", "grounding", "citations", "depth",
              "coverage", "extrapolation", "panel"}
    return {k: v.strip().strip('"\'') for k, v in FLAT_KEY.findall(text)
            if k in wanted}


def newest(paths):
    times = [os.path.getmtime(p) for p in paths if os.path.exists(p)]
    return max(times) if times else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    topic = find_topic(args.topic)
    if not topic:
        tvlib.die("no trivium.config.yaml found here or above. "
                  "Run trivium-init to start a topic.")

    config = read_config(os.path.join(topic, "trivium.config.yaml"))

    sources = sorted(p for p in glob.glob(os.path.join(topic, "sources", "*"))
                     if p.lower().endswith(BOOK_EXT))
    extracted = {os.path.basename(p)[:-4]
                 for p in glob.glob(os.path.join(topic, "text", "*.txt"))}

    books, unextracted = [], []
    for slug in sorted(extracted):
        book_dir = os.path.join(topic, "books", slug)
        notes_path = os.path.join(book_dir, "notes.jsonl")
        notes, _ = tvlib.read_notes(notes_path) if os.path.exists(notes_path) else ([], [])

        rejected = 0
        rej_path = os.path.join(book_dir, "REJECTED.jsonl")
        if os.path.exists(rej_path):
            with open(rej_path, encoding="utf-8") as fh:
                rejected = sum(1 for line in fh if line.strip())

        provenance = "unknown"
        map_path = os.path.join(topic, "text", f"{slug}.map.json")
        if os.path.exists(map_path):
            provenance = tvlib.load_map(map_path).get("provenance", "unknown")

        state = "extracted"
        if notes:
            if os.path.exists(os.path.join(book_dir, "BRIEF.md")):
                state = "studied"
            elif time.time() - os.path.getmtime(notes_path) < ACTIVE_WINDOW:
                # Notes without a brief usually means an interrupted run. But a
                # run still in progress looks identical, and telling someone to
                # restart a healthy run is worse than waiting.
                state = "in-progress"
            else:
                state = "notes-only"

        books.append({
            "slug": slug,
            "state": state,
            "notes": len(notes),
            "figure_notes": sum(1 for n in notes if n.get("kind") == "figure"),
            "rejected": rejected,
            "provenance": provenance,
            "brief": os.path.exists(os.path.join(book_dir, "BRIEF.md")),
            "map": os.path.exists(os.path.join(book_dir, "MAP.md")),
            "notes_mtime": newest([notes_path]),
        })

    for src in sources:
        stem = os.path.splitext(os.path.basename(src))[0]
        if not any(b["slug"] in stem or stem.startswith(b["slug"]) for b in books):
            unextracted.append(os.path.basename(src))

    synthesis = os.path.join(topic, "SYNTHESIS.md")
    index = os.path.join(topic, "INDEX.md")
    overview = os.path.join(topic, "overview.html")
    studied = [b for b in books if b["state"] == "studied"]

    synth_state = "missing"
    if os.path.exists(synthesis):
        synth_state = "stale" if os.path.getmtime(synthesis) < newest(
            [os.path.join(topic, "books", b["slug"], "notes.jsonl") for b in books]
        ) else "current"

    # What to do next, in the order the pipeline actually runs.
    todo = []
    if unextracted:
        todo.append(f"study the {len(unextracted)} book(s) not yet extracted: "
                    + ", ".join(unextracted))
    active = [b for b in books if b["state"] == "in-progress"]
    for b in active:
        todo.append(f"wait: {b['slug']} looks like a study run still in progress "
                    f"({b['notes']} notes so far). Do not restart it.")
    pending = [b for b in books if b["state"] not in ("studied", "in-progress")]
    for b in pending:
        why = "notes exist but no brief, so the run was interrupted" \
            if b["state"] == "notes-only" else "extracted but never studied"
        todo.append(f"run trivium-study on {b['slug']} ({why})")
    if not pending and not unextracted and not active:
        if len(studied) > 1 and synth_state == "missing":
            todo.append("run trivium-synthesize, every book is studied")
        elif synth_state == "stale":
            todo.append("rerun trivium-synthesize, the notes changed after it last ran")
        else:
            todo.append("run trivium-converse, the topic is ready")

    report = {
        "topic": topic,
        "config": config,
        "books": books,
        "unextracted": unextracted,
        "synthesis": synth_state,
        "index": os.path.exists(index),
        "overview": os.path.exists(overview),
        "next": todo,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Topic: {config.get('title', os.path.basename(topic))}   ({topic})")
    print(f"Profile: {config.get('profile', '?')}, grounding "
          f"{config.get('grounding', '?')}, citations "
          f"{config.get('citations', '?')}, depth {config.get('depth', '?')}")
    print()

    if books:
        print(f"{'BOOK':22s} {'STATE':11s} {'NOTES':>6s} {'FIG':>4s} "
              f"{'DROPPED':>8s}  PROVENANCE")
        for b in books:
            print(f"{b['slug']:22s} {b['state']:11s} {b['notes']:>6d} "
                  f"{b['figure_notes']:>4d} {b['rejected']:>8d}  {b['provenance']}")
    else:
        print("No books extracted yet.")

    if unextracted:
        print()
        print("Not extracted: " + ", ".join(unextracted))

    print()
    print(f"Synthesis: {synth_state}"
          + ("   (rerun it, the notes have changed since)" if synth_state == "stale" else ""))
    print(f"Overview:  {'published' if report['overview'] else 'not built'}")
    print()
    print("Next:")
    for item in todo:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
