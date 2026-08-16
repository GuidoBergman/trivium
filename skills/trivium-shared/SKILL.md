---
name: trivium-shared
description: Shared contracts for the Trivium skills - note schema, verification protocol, configuration profiles and the conversation contract. Read by trivium-init, trivium-study, trivium-synthesize and trivium-converse. Not invoked directly by the user.
---

# Trivium shared contracts

Trivium turns a folder of books or papers into verified notes, then lets the user
have a grounded conversation with the authors. This skill holds the contracts the
other four share. Read the file you need, do not read all of them.

- `NOTE-SCHEMA.md` - the shape of a note, and why each field exists
- `VERIFICATION.md` - the four verification stages and how to run them
- `CONFIG.md` - profiles and every configuration key
- `CONVERSATION-CONTRACT.md` - how grounded answers are written and enforced

## The one rule

**Nothing reaches the user as fact unless it traces to a verbatim quote from a
source.** Everything else in Trivium is machinery for keeping that true.

Anything that is not so traceable can still be said. It must be marked as
unsupported in the flow of the sentence, in ordinary language, so the user cannot
read past it without noticing. Silence about the gap is the only real failure.

## Where things live

A **topic** is one subject with one or more books. Inside this repository topics
live at `topics/<name>/`. In any other repository they live at `.trivium/`.

```
<topic>/
  trivium.config.yaml     profile and settings
  sources/                original PDF and EPUB files, never modified
  text/
    <slug>.txt            extracted plain text, what quotes are checked against
    <slug>.map.json       page and chapter offsets into that text
  books/<slug>/
    notes.jsonl           source of truth for notes
    NOTES.md              generated from notes.jsonl, never hand-edited
    BRIEF.md              one page: what this book argues
    MAP.md                chapter by chapter, what is where
    EXTRACTION.md         extraction quality report
    REJECTED.jsonl        claims dropped in verification, with reasons
    verification.json     latest stage 1 report
  INDEX.md                topic-level routing and vocabulary
  SYNTHESIS.md            cross-book, only when there is more than one book
  overview.html           generated on request
```

## Finding the topic

Walk up from the working directory looking for `trivium.config.yaml`, then for a
`.trivium/` directory, then for a `topics/` directory. If several topics exist and
the user has not said which, ask. Never guess between topics.

## Scripts

The deterministic work is done by scripts, not by reading and judging. Use them.

Resolve `$TV` once at the start of a run:

- `~/.claude/skills/trivium-shared/scripts` when the skills are installed
- `skills/trivium-shared/scripts` when working inside the trivium repository itself

| Script | Job |
|---|---|
| `tv_extract.py` | PDF, EPUB or AZW3 to `text/<slug>.txt` plus `.map.json` |
| `tv_quality.py` | extraction quality gate, writes `EXTRACTION.md` |
| `tv_pages.py` | render PDF pages to PNG for the visual pass and the OCR audit |
| `tv_verify.py` | stage 1, does each quote really exist in the book |
| `tv_search.py` | the only way to search the books |
| `tv_render.py` | `notes.jsonl` to `NOTES.md` |
| `tv_kf8.py` | AZW3 and MOBI decoding, imported by `tv_extract.py` |

All are stdlib-only Python 3. `tv_extract.py` prefers `pdftotext` and falls back
to `pypdf`. `tv_pages.py` needs `pdftoppm`. If a needed tool is missing, say so
and stop rather than improvising.

AZW3 and MOBI are read directly, with no Calibre and no conversion step. DRM'd
files are refused, and removing the protection is not something Trivium does.

## Two things text extraction cannot do

Both are recorded in `<slug>.map.json` and reported by the quality gate. Neither
is optional to think about, because both fail silently.

**Provenance.** `native` means the publisher's own text layer, so a verified
quote is a quote from the book. `ocr` or `ocr-suspected` means the text was
machine-read off a scan, and a verified quote only proves the quote is in that
transcription. Books in the second category get the OCR audit and say so in
their brief.

**Figures.** Worksheets, diagrams and forms hold content that never becomes text.
The coverage pass cannot catch the omission, because it reads the same text a
note-taker did. Pages carrying figures are listed for the visual pass.

`tv_search.py` is a seam. Every search goes through it, so it can be replaced with
a real index later without touching any skill.

## Never do these

- Never take a note from a section the quality gate excluded.
- Never edit `NOTES.md` by hand. Edit `notes.jsonl` and re-render.
- Never write a quote from memory. Copy it out of `text/<slug>.txt`.
- Never keep a note that failed verification. Move it to `REJECTED.jsonl`.
- Never present an inference, an extrapolation or outside knowledge without
  saying so in the sentence itself.
