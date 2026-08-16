# Trivium

Read books properly, then talk to their authors without being lied to.

Point Trivium at a PDF, EPUB or AZW3. It extracts the text, takes structured notes, and
then attacks those notes with independent checker agents until every surviving
note is provably tied to a verbatim quote from the source. Afterwards you can have
a conversation with the authors, alone or as a panel, in which every factual
statement traces back to one of those notes.

Anything that goes beyond the books can still be said. It just gets flagged as it
is said, in plain language, so you always know which register you are reading.

See `DESIGN.md` for the reasoning behind the design.

## Install

```sh
./install.sh
```

Symlinks six skills into `~/.claude/skills`, so they work in any repository.
Editing a skill here takes effect immediately.

Needs Python 3. PDFs need `pdftotext` (poppler-utils) or `pypdf`, and `pdftoppm`
plus `pdfimages` for reading figures. EPUB and AZW3 work with the standard
library alone.

## Formats

| Format | How |
|---|---|
| EPUB | spine order, one chapter per document |
| PDF | `pdftotext`, with page and outline mapping |
| AZW3, MOBI | decoded directly, no Calibre and no conversion step |

DRM'd Kindle files are refused. Removing the protection is not something Trivium
does.

Scanned PDFs are handled when they carry an OCR text layer, but they are marked
as machine-read and audited rather than trusted. Image-only PDFs with no text at
all are refused.

## Use

| Skill | What it does |
|---|---|
| `trivium-init` | Set up a topic, ask what you want out of it, pick a profile |
| `trivium-status` | Where does this topic stand, and what should I run next |
| `trivium-study` | Study one book: extract, note, verify, brief, map |
| `trivium-synthesize` | Cross-book layer: agreements, disagreements, the index, the HTML overview |
| `trivium-converse` | Talk to the authors |

## The pipeline

Four steps, run in order, once per topic. Each skill ends by telling you what
comes next, so you should never have to remember this. It is written down anyway.

```
   your books
        |
   /trivium-init            once per topic
        |                   asks what you want out of the reading, writes the config
        v
   /trivium-study           once per BOOK, repeat until every book is done
        |                   the long one: extract, note, verify, brief, map
        v
   /trivium-synthesize      once, after the last book
        |                   agreements, disagreements, index, HTML overview
        v
   /trivium-converse        as often as you like, forever
                            talk to the authors

   /trivium-status          any time: which books are studied, what runs next
```

In a repository that exists for one topic, `trivium-init` also writes a short
`CLAUDE.md` router so questions about the subject load `trivium-converse`
automatically. The router routes; the contract stays in the skill.

**What each step leaves behind**, so you can tell where you are by looking:

| After | You have | Where |
|---|---|---|
| init | `trivium.config.yaml`, empty folders | topic root |
| study | `notes.jsonl`, `NOTES.md`, `BRIEF.md`, `MAP.md`, `EXTRACTION.md` | `books/<slug>/` |
| synthesize | `SYNTHESIS.md`, `INDEX.md`, `overview.html` | topic root |
| converse | nothing, unless you promote something into the notes | — |

**Rules about order.** Study is per book, so it repeats. Synthesize needs at
least two studied books and must never run while a study run is going, since it
writes into every book's notes. Converse works with one book, but without
synthesis it cannot tell you where the authors disagree.

**Going back.** Adding a book later means running study on it and then rerunning
synthesize. Changing what you want out of the topic means editing `intent` in the
config, and any book already studied was noted against the old intent, so it may
need restudying.

A typical run:

```
/trivium-init          drop your books in, say what you're after
/trivium-study         once per book, deliberately slow
/trivium-synthesize    once there are two or more
/trivium-converse      the point of the whole thing
```

Topics in this repository live under `topics/`. In any other repository they live
under `.trivium/`, which is how the same machinery works inside a research project
without dragging your personal library along.

## How the guarantee works

Four verification stages, only the first of which involves no model at all.

1. **Quote exists.** A script checks the quote against the extracted text. A quote
   is in the file or it is not, and nothing can talk its way past this.
2. **Quote supports claim.** A subagent sees only the claim and the quote, with no
   context and no idea why the note was written, and judges whether the quote
   actually carries the claim.
3. **Context is not being misread.** A subagent sees the quote inside the
   surrounding text and checks whether the author was actually asserting it, or
   quoting someone, or setting up a view to demolish. This catches the worst error
   the system can make: attributing to an author a position they were arguing
   against.
4. **Coverage.** A subagent that has never seen the notes reads each chapter cold
   and lists its major arguments. Anything on that list with no matching note is a
   gap, and gaps that matter get filled.

Failed notes are dropped, not rewritten until they pass, and the reasons are kept
in `REJECTED.jsonl`.

In conversation, strict profiles add a fifth check: a separate agent audits every
draft reply before you see it and blocks any unsupported statement that is not
flagged.

Two extra passes run when the book needs them. Pages whose content lives inside
an image are rendered and read directly, producing figure notes whose evidence is
the page image rather than a quote, checked by a second reader looking at the same
image. Books whose text was machine-read off a scan get audited against a sample
of page images, with wrong numbers counted separately from wrong words, because
those are the errors that cause harm rather than confusion.

## Honest limits

Stage 1 is genuinely deterministic. The rest are models checking models, made much
harder to fool by keeping them independent and by giving each one the narrowest
slice of evidence that lets it do its job. That is a very different risk level from
a model summarising freely, but it is not a proof.

A scan that carries an OCR text layer is usable, but a verified quote from it only
proves the quote is in that transcription. Those books are marked, audited against
their page images, and say so in their brief. A PDF with no text layer at all is
refused rather than transcribed, because a text layer this system generated would
be a model artifact sitting underneath every later guarantee.
