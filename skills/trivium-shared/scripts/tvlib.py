"""Shared helpers for the Trivium scripts.

Nothing here uses a model. These functions are the deterministic floor that the
factual guarantee rests on: text normalisation, offset mapping, segment lookup
and note IO. Keep it stdlib-only so the skills work in any repository without
an install step.
"""

import json
import os
import re
import sys
import unicodedata

# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------

# Characters that PDF and EPUB extraction mangles, mapped to a plain form.
_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "′": "'", "″": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-",
    "—": "-", "―": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
    " ": " ", " ": " ", " ": " ", "　": " ",
    "­": "",  # soft hyphen
    "​": "", "‌": "", "‍": "", "﻿": "",
    "…": "...",
}

_WS = re.compile(r"\s")


def build(text, mode):
    """Return (transformed_text, index_map).

    index_map[i] is the offset in `text` that produced transformed_text[i], so
    a match found in the transformed text can always be located in the original.

    mode="norm"  folds unicode punctuation and collapses whitespace runs to one
                 space. Preserves case and punctuation.
    mode="alnum" keeps only lowercase letters and digits. Survives hyphenation,
                 line breaks and every quote style, at the cost of no longer
                 checking punctuation.
    """
    out = []
    idx = []
    prev_space = False

    for i, ch in enumerate(text):
        folded = _FOLD.get(ch)
        if folded is None:
            folded = unicodedata.normalize("NFKC", ch)

        for c in folded:
            if mode == "alnum":
                if c.isalnum():
                    # Strip accents so cafe and café match.
                    d = unicodedata.normalize("NFKD", c.lower())
                    for e in d:
                        if e.isalnum():
                            out.append(e)
                            idx.append(i)
                continue

            if _WS.match(c):
                if prev_space:
                    continue
                out.append(" ")
                idx.append(i)
                prev_space = True
            else:
                out.append(c)
                idx.append(i)
                prev_space = False

    return "".join(out), idx


def find_all(haystack, needle, limit=50):
    """Every start offset of needle in haystack."""
    hits = []
    start = 0
    while len(hits) < limit:
        pos = haystack.find(needle, start)
        if pos < 0:
            break
        hits.append(pos)
        start = pos + 1
    return hits


# --------------------------------------------------------------------------
# Segment maps
# --------------------------------------------------------------------------

def load_map(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def segment_at(segments, offset):
    """The segment containing a character offset, or None."""
    for seg in segments:
        if seg["start"] <= offset < seg["end"]:
            return seg
    return None


def locate(mapping, offset):
    """Human-readable locator for an offset, e.g. 'ch3 / p.87'."""
    parts = []
    chapter = segment_at(mapping.get("chapters", []), offset)
    if chapter:
        parts.append(chapter["label"])
    page = segment_at(mapping.get("pages", []), offset)
    if page:
        parts.append(page["label"])
    return " / ".join(parts) if parts else "unknown"


_LOCATOR_TOKEN = re.compile(r"(ch|p|loc)\.?\s*([0-9ivxlcIVXLC]+)", re.I)


def locator_tokens(text):
    """Normalise a locator string into a comparable set, e.g. {'ch3', 'p87'}."""
    found = set()
    for kind, num in _LOCATOR_TOKEN.findall(text or ""):
        found.add(f"{kind.lower()}{num.lower()}")
    return found


# --------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------

REQUIRED_FIELDS = ("id", "claim", "locator", "kind", "scope", "speaker")
VALID_KINDS = {"claim", "definition", "technique", "example", "caveat", "figure"}
VALID_SCOPES = {"core", "adjacent"}
VALID_SPEAKERS = {"author", "cited", "rejected", "hypothetical", "conversation"}


def read_notes(path):
    """Read notes.jsonl. Returns (notes, errors)."""
    notes, errors = [], []
    if not os.path.exists(path):
        return notes, [f"missing notes file: {path}"]

    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                note = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {lineno}: invalid JSON ({exc.msg})")
                continue

            missing = [f for f in REQUIRED_FIELDS if not note.get(f)]
            # A figure note's evidence is a rendered page image rather than a
            # quote, because its content never existed as text.
            if note.get("kind") == "figure":
                if not note.get("evidence"):
                    missing.append("evidence")
            elif not note.get("quote"):
                missing.append("quote")
            if missing:
                errors.append(f"line {lineno}: missing fields {', '.join(missing)}")
                continue
            if note["kind"] not in VALID_KINDS:
                errors.append(f"line {lineno}: bad kind {note['kind']!r}")
            if note["scope"] not in VALID_SCOPES:
                errors.append(f"line {lineno}: bad scope {note['scope']!r}")
            if note["speaker"] not in VALID_SPEAKERS:
                errors.append(f"line {lineno}: bad speaker {note['speaker']!r}")

            note["_line"] = lineno
            notes.append(note)

    return notes, errors


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            clean = {k: v for k, v in row.items() if not k.startswith("_")}
            fh.write(json.dumps(clean, ensure_ascii=False) + "\n")


def die(message):
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)
