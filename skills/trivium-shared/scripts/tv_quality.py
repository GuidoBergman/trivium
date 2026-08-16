#!/usr/bin/env python3
"""Extraction quality gate.

Scores every page or chapter of an extracted book and flags the ones that came
out empty, truncated or garbled. Sections that fail the gate are excluded from
study rather than quietly half-read.

Usage:
  tv_quality.py <topic>/text/<slug>.txt [--md EXTRACTION.md] [--json out.json]
"""

import argparse
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tvlib  # noqa: E402

# A genuinely blank page yields almost nothing. Scattered blank pages are normal
# in any book (part openers, end matter), so this threshold is deliberately low
# and the overall judgement below cares about the *rate*, not the individual page.
MIN_CHARS = 80
SHORT_RATIO = 0.25       # fraction of the median length that counts as short
MIN_ALNUM_RATIO = 0.55   # letters and digits as a share of non-space characters
MAX_AVG_WORD = 12.0      # average token length, high means spaces were lost
MAX_LONG_TOKENS = 0.04   # share of tokens over 25 characters
MAX_REPLACEMENT = 0.002  # share of U+FFFD, the "extraction lost this" character

TOKEN = re.compile(r"\S+")

# Runs of one repeated punctuation mark are typography, not damage: dot leaders
# in a table of contents, underscore blanks on a form, rules made of dashes.
# Scoring them as text made a page of VA intake form look like garbled OCR.
# Note the class is "not a letter, digit or space" rather than \W: underscore is
# a word character to Python, and underscore runs are the single most common
# fill-in blank on a printed form.
LEADER = re.compile(r"([^\sa-zA-Z0-9])\1{2,}")


def is_wordlike(token):
    """A token is word-like when most of it is letters or digits.

    Fill-in blanks and rules are not words, and letting them into the word-length
    average is what made forms look like extraction failures.
    """
    if not token:
        return False
    alnum = sum(1 for c in token if c.isalnum())
    return alnum >= len(token) / 2


def score(text):
    chars = len(text)
    # Collapse each run to a single character so the run counts once.
    flattened = LEADER.sub(r"\1", text)

    stripped = re.sub(r"\s", "", flattened)
    words = [t for t in TOKEN.findall(flattened) if is_wordlike(t)]

    alnum = sum(1 for c in stripped if c.isalnum())
    alnum_ratio = alnum / len(stripped) if stripped else 0.0
    avg_word = (sum(len(t) for t in words) / len(words)) if words else 0.0
    long_ratio = (sum(1 for t in words if len(t) > 25) / len(words)) if words else 0.0
    replacement = text.count("�") / chars if chars else 0.0

    return {
        "chars": chars,
        "tokens": len(words),
        "alnum_ratio": round(alnum_ratio, 3),
        "avg_word_len": round(avg_word, 2),
        "long_token_ratio": round(long_ratio, 3),
        "replacement_ratio": round(replacement, 4),
    }


def verdict(metrics, median_chars, has_figure):
    reasons = []
    if metrics["chars"] < MIN_CHARS:
        if has_figure:
            # Not an extraction failure. The page is a worksheet, a diagram or a
            # table, and its content is real but lives where text extraction
            # cannot reach. Calling this EMPTY would quietly delete content.
            return "IMAGE_ONLY", ["little text, but the page carries an image"]
        return "EMPTY", ["under %d characters" % MIN_CHARS]

    if metrics["alnum_ratio"] < MIN_ALNUM_RATIO:
        reasons.append("only %.0f%% letters and digits" % (metrics["alnum_ratio"] * 100))
    if metrics["avg_word_len"] > MAX_AVG_WORD:
        reasons.append("average word length %.1f, spaces likely lost"
                       % metrics["avg_word_len"])
    if metrics["long_token_ratio"] > MAX_LONG_TOKENS:
        reasons.append("%.0f%% of tokens over 25 characters"
                       % (metrics["long_token_ratio"] * 100))
    if metrics["replacement_ratio"] > MAX_REPLACEMENT:
        reasons.append("unreadable characters present")
    if reasons:
        return "GARBLED", reasons

    if median_chars and metrics["chars"] < median_chars * SHORT_RATIO:
        return "SHORT", ["well below the typical section length"]

    return "OK", []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text")
    ap.add_argument("--md", help="write a Markdown report here")
    ap.add_argument("--json", dest="json_out", help="write the raw report here")
    args = ap.parse_args()

    map_path = args.text.replace(".txt", ".map.json")
    if not os.path.exists(args.text):
        tvlib.die(f"no such file: {args.text}")
    if not os.path.exists(map_path):
        tvlib.die(f"missing map file: {map_path}")

    with open(args.text, encoding="utf-8") as fh:
        text = fh.read()
    mapping = tvlib.load_map(map_path)

    # Pages first. Extraction fails a page at a time, so scoring whole chapters
    # lets one scanned page hide inside twenty good ones.
    segments = mapping.get("pages") or mapping.get("chapters") or []
    unit = "page" if mapping.get("pages") else "chapter"
    if not segments:
        segments = [{"label": "whole book", "start": 0, "end": len(text)}]
        unit = "book"

    rows = [dict(seg, **score(text[seg["start"]:seg["end"]])) for seg in segments]
    median_chars = statistics.median([r["chars"] for r in rows]) if rows else 0

    provenance = mapping.get("provenance", "native")
    figures = {i["label"]: i for i in mapping.get("images", []) if i.get("figure")}

    for row in rows:
        row["has_figure"] = row["label"] in figures
        row["verdict"], row["reasons"] = verdict(row, median_chars, row["has_figure"])

    # On a scan every page is a full-page image, so "this page has an image" says
    # nothing on its own. What marks a worksheet there is an image plus text that
    # is thin for this book.
    thin = median_chars * 0.4
    visual = [r["label"] for r in rows if r["has_figure"] and
              (provenance == "native" or r["chars"] < thin)]

    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    garbled = [r for r in rows if r["verdict"] == "GARBLED"]
    empty = [r for r in rows if r["verdict"] == "EMPTY"]
    image_only = [r for r in rows if r["verdict"] == "IMAGE_ONLY"]
    # IMAGE_ONLY is not a failure. Those pages hold content and are handed to the
    # visual pass, so counting them as failures would condemn a workbook.
    excluded = garbled + empty
    fail_rate = len(excluded) / len(rows) if rows else 0.0

    # A few blank pages mean nothing. Garbled text, or blankness at scale, means
    # the extraction is not trustworthy and the book must not be studied as is.
    # In a short document a single sparse page is a large percentage, so require
    # a real cluster before calling a paper degraded.
    material = len(excluded) >= (2 if len(rows) < 20 else 1)
    if garbled or (fail_rate > 0.10 and material):
        overall = "UNUSABLE" if fail_rate > 0.35 else "DEGRADED"
    else:
        overall = "OK"

    report = {
        "overall": overall,
        "provenance": provenance,
        "provenance_evidence": mapping.get("provenance_evidence", []),
        "visual_pass_pages": visual,
        "image_only": [r["label"] for r in image_only],
        "fail_rate": round(fail_rate, 3),
        "slug": mapping.get("slug"),
        "unit": unit,
        "total_chars": len(text),
        "sections": len(rows),
        "counts": counts,
        "excluded": [r["label"] for r in excluded],
        "rows": rows,
    }

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)

    lines = [
        f"# Extraction report: {mapping.get('slug')}",
        "",
        f"Source: `{mapping.get('source')}`",
        "",
        f"Extracted {len(text):,} characters across {len(rows)} {unit}s.",
        "",
    ]

    if provenance == "native":
        lines += ["Text provenance: **native**. This is the publisher's own text "
                  "layer, so a verified quote is a quote from the book.", ""]
    else:
        why = "; ".join(report_evidence := mapping.get("provenance_evidence", []))
        lines += [
            f"Text provenance: **{provenance}**"
            + (f" ({why})" if report_evidence else "") + ".",
            "",
            "This text was machine-read off a scan, not published as text. A "
            "verified quote therefore proves the quote is in *this transcription* "
            "of the book, which is weaker than proving it is in the book. Record "
            "this in the brief, and audit a sample of pages against the page "
            "images before relying on any number, dose or threshold.",
            "",
            "```",
            f"python3 $TV/tv_pages.py {map_path} --sample 12",
            "```",
            "",
        ]

    lines += [
        "| Section | Chars | Alnum | Avg word | Fig | Verdict | Why |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        title = row.get("title", "")
        label = f"{row['label']} {title}".strip()
        lines.append(
            f"| {label} | {row['chars']:,} | {row['alnum_ratio']:.0%} | "
            f"{row['avg_word_len']:.1f} | {'yes' if row['has_figure'] else ''} | "
            f"{row['verdict']} | {'; '.join(row['reasons']) or ''} |"
        )

    lines += ["", f"## Verdict: {overall}", ""]
    if overall == "UNUSABLE":
        lines.append(
            f"**{fail_rate:.0%} of sections are unreadable. Do not study this "
            "book.** This is almost always an image-only or scanned PDF, which "
            "Trivium does not handle. Get a text-based copy."
        )
    elif overall == "DEGRADED":
        lines.append(
            f"**{len(excluded)} of {len(rows)} sections failed the gate and are "
            "excluded from study.** Notes must not be taken from them, and the "
            "brief must state which parts of the book were not read."
        )
    else:
        lines.append("The book is readable and study can proceed.")
        if empty:
            lines.append("")
            lines.append(
                f"{len(empty)} near-blank section(s) were skipped. At this rate "
                "that is normal, and usually means part dividers or end matter."
            )

    if excluded:
        lines.append("")
        lines.append("Excluded sections:")
        lines.append("")
        for row in excluded:
            lines.append(f"- `{row['label']}` {row.get('title', '')}: "
                         f"{'; '.join(row['reasons'])}")

    if visual:
        lines += [
            "",
            "## Visual pass",
            "",
            f"{len(visual)} {unit}s carry content inside an image, which text "
            "extraction cannot reach. Text-only notes from this book will be "
            "incomplete in a way the coverage pass cannot detect, because the "
            "coverage pass reads the same text.",
            "",
            f"{len(image_only)} of them have almost no text at all, so whatever "
            "they contain exists only as a picture.",
            "",
            "Render them and read them:",
            "",
            "```",
            f"python3 $TV/tv_pages.py {map_path} \\\n    --from-report {args.json_out or 'extraction.json'}",
            "```",
            "",
            "Pages: " + ", ".join(f"`{v}`" for v in visual[:60])
            + (" ..." if len(visual) > 60 else ""),
        ]
    lines.append("")

    md = "\n".join(lines)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(md)
    else:
        print(md)

    print(json.dumps({"overall": overall, "counts": counts,
                      "excluded": report["excluded"]}), file=sys.stderr)
    raise SystemExit(0 if overall == "OK" else 1)


if __name__ == "__main__":
    main()
