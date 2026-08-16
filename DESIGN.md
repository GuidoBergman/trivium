# Trivium: design

## Executive summary

Trivium is a set of Claude Code skills that turn a folder of books or papers into a verified set of notes, and then let you have a grounded conversation with the authors.

**What it is.** Four skills, installed once in `~/.claude/skills`, usable from any repository. You point one at a book, it reads it, takes structured notes, and then attacks its own notes with independent checker agents until every surviving note is provably tied to a verbatim quote from the source. A second skill lets you talk to the authors using only those notes.

**Why it matters.** The point is not summarising. The point is that nothing the assistant tells you is ever silently invented. Every factual claim traces to a quote that mechanically exists in the source text. Anything that is not so traceable gets said out loud, in ordinary language, at the moment it is said.

**Key takeaways.**

- Notes are claims with verbatim quotes and locations, not prose summaries. This is what makes verification possible at all.
- Verification runs in four stages, three of which use independent subagents that never see each other's work. One stage is purely mechanical and cannot hallucinate.
- The most dangerous error class is not invention, it is attributing to an author a view they were describing in order to reject it. Stage 3 exists specifically to catch that.
- Conversation strictness is configurable per project. A research paper gets a checker agent auditing every reply before you see it. A therapy-books conversation runs looser so it can actually flow.
- Search stays as plain files plus ripgrep plus study-time index files. No embeddings, no vector database. The design has one seam so a real index can drop in later without touching anything else.

**What I need from you before building.** Confirmation of this document, plus a first book to test against.

---

## Terms

Defined once so nothing below is ambiguous.

- **Topic.** One subject you are reading about. Holds one or more books, their notes, and its own configuration. Example: `topics/therapy`.
- **Book.** Any source document. A PDF, an EPUB, an AZW3, or a single research
  paper.
- **Note.** The atomic unit. One claim the book makes, plus the verbatim quote supporting it, plus where in the book it came from.
- **Brief.** The one-page summary of a book. What it argues, who it is for, what it assumes.
- **Section map.** The chapter-by-chapter navigation aid. What each section covers, in the book's own vocabulary, so you know where to dig.
- **Profile.** Per-project configuration controlling how strict and how formal the conversation is.
- **Panel.** A conversation where authors of several books respond to each other rather than one at a time.
- **Gate.** A checker agent that audits a reply before you see it and blocks it if any factual sentence is unsupported and unflagged.

---

## Layout

The machinery lives in `trivium/skills/` and is synced to `~/.claude/skills/`, which makes it available in every repository automatically.

Notes live wherever the reading happens. Personal topics live in this repo. A paper you read for a research project lives in that project's repo.

```
trivium/
  skills/                        # source of truth for the machinery
    trivium-init/
    trivium-study/
    trivium-synthesize/
    trivium-converse/
    _shared/                     # templates, note schema, search interface
  topics/
    <topic-name>/
      trivium.config.yaml        # profile for this topic
      sources/                   # original PDF and EPUB files, untouched
      text/                      # extracted plain text, permanent
      books/
        <book-slug>/
          BRIEF.md
          MAP.md
          NOTES.md
          EXTRACTION.md          # extraction quality report
          REJECTED.md            # claims that failed verification
      INDEX.md                   # topic-level routing and vocabulary index
      SYNTHESIS.md               # cross-book, only when >1 book
      overview.html              # generated, published on request
  DESIGN.md
```

In any other repository, the same structure lives under `.trivium/`. The skills locate a topic by walking up from the working directory looking for `trivium.config.yaml`, so they work identically inside and outside this repo.

---

## The note schema

This is the load-bearing decision. Everything else follows from it.

```
### N-042
claim:     Deliberate practice requires immediate feedback to produce improvement.
quote:     "Without feedback, efficient or otherwise, improvement is minimal, even
            for highly motivated subjects."
locator:   ch3 / p.87
kind:      claim
scope:     core
speaker:   author
verified:  quote-exact + entailment + context
```

- `claim` is one sentence, in plain language, stating what the book asserts.
- `quote` is verbatim, copied byte for byte from the extracted text.
- `locator` is chapter plus page, or EPUB position when there is no page number.
- `kind` is one of claim, definition, technique, example, caveat.
- `scope` is core or adjacent, relative to what you said you wanted from the book.
- `speaker` records whose view this is. This matters enormously. A book quoting a position it goes on to demolish must never produce a note attributed to the author.
- `verified` records which checks the note passed.

Prose summaries cannot be verified, because there is nothing to check a sentence against. Claims with quotes can. That is the whole reason for the format.

---

## Skill 1: `trivium-study`

Studies one book. This is the long process.

**Step 1, ingest and extraction quality gate.** Extract text from the PDF or EPUB into `text/`. Then measure per chapter: character count, proportion of alphanumeric characters, average word length, presence of the expected structure. Chapters that come out empty, garbled, or suspiciously short are reported loudly in `EXTRACTION.md` and excluded from study rather than quietly half-read. You said image-only PDFs are out of scope, so a chapter that yields nothing is treated as an error to surface, not a case to handle.

**Step 2, intent interview.** Before any notes are taken, I ask what you want out of this book. The answer shapes what gets noted in depth, what gets noted briefly, and what coverage checking counts as a gap later. This is a short conversation, not a form.

**Step 3, note-taking.** Chapter by chapter, produce notes in the schema above, plus the section map entry for that chapter. The section map entry records the chapter's own vocabulary and the obvious synonyms, which is what lets keyword search find a chapter about compassion fatigue when you search for burnout.

**Step 4, verification.** Four stages. Stages 2 through 4 fan out across independent subagents that do not see each other's results.

1. **Quote-exact, mechanical.** Does the quote string literally appear in the extracted text file? This is a string match, no model involved, so it cannot hallucinate. Failures are dropped immediately.
2. **Entailment.** A subagent sees only the quote and the claim, with no surrounding context and no knowledge of what the note is for. Does the quote actually support the claim, or does the claim overreach? Failures are dropped.
3. **Context.** A subagent sees the quote plus roughly two paragraphs either side. Is the claim a misreading of context? This catches the error class that matters most: the author was describing someone else's position, or setting up a view to reject it, or speaking hypothetically. Failures are dropped or corrected to a different `speaker`.
4. **Coverage.** Runs on every book, per your decision. For each chapter, a subagent reads the raw text cold, having never seen the notes, and lists the major arguments. That list is diffed against the notes. Gaps that fall inside your stated intent are written up as new notes and sent back through stages 1 to 3. Gaps outside your intent are recorded as a single short line in the brief, not developed.

Failed claims are dropped entirely, as you asked. They are also logged in `REJECTED.md` with the reason, which costs nothing and means a systematic extraction problem shows up as a pattern rather than as silence.

**Step 5, brief and map.** Write `BRIEF.md` (one page, what the book argues and who it is for) and `MAP.md` (chapter by chapter, what is where, in the book's vocabulary). Both are built only from verified notes.

---

## Skill 2: `trivium-synthesize`

Runs across all books in a topic once there is more than one. Separate skill, because per-book study and cross-book work are different jobs.

Produces `SYNTHESIS.md` covering:

- Where the books **agree**, with the note IDs from each.
- Where they **disagree**, stated as a real disagreement rather than smoothed into a consensus that nobody actually holds.
- Where they **talk past each other**, meaning they use the same word for different things, or answer different questions while appearing to answer the same one. This is the most common and least obvious case.
- What the topic as a whole **does not cover**, kept short.

Also builds `INDEX.md`, the topic-level routing table, and generates `overview.html`.

Every synthesis statement carries note IDs internally, so a claim about what two authors share can itself be traced back to quotes.

---

## Skill 3: `trivium-converse`

The conversation. Loads briefs, section maps and the index into context, roughly two to five thousand tokens per book. Full text stays on disk and is read on demand when a question needs detail. A fifteen-book topic stays under sixty thousand tokens of standing context, which is where quality holds up.

**How flagging reads.** No labels, no brackets, no machine syntax. Three registers, in ordinary prose:

- Supported by the notes: stated plainly, as the author's view.
- Extrapolation: "She doesn't take this up directly, but given her argument that feedback has to be immediate, she'd probably say ..."
- Outside the books: "That isn't in any of these books. For what it's worth, my own read is ..."

The rule is that the flag is impossible to miss when reading normally, and never looks like machinery.

**Enforcement.** In strict profiles, a checker agent receives the draft reply plus the relevant notes before you see it, and marks every factual sentence as supported, extrapolated, or unsupported. Any unsupported sentence that is not flagged in the prose sends the draft back to be rewritten. You see only the final text. Cost is roughly double the response latency. In immersive profiles the gate is off and the same rules apply by instruction only, which is faster and more natural but not guaranteed.

**Panels.** With several books, authors respond to each other. Where the synthesis recorded a disagreement, the conversation surfaces it rather than blending it into a single voice. Not in character, per your call, so this is closer to a well-briefed representative of each position than to impersonation.

**Quotes.** Stored always, since they are the verification substrate. Shown according to profile, defaulting to on-request in immersive mode and inline in research mode. You can always ask "where is that from" and get chapter and page.

**Promotion.** When something useful comes up that is not in the notes, I ask whether to save it. If yes, it becomes a note marked as conversation-derived, kept structurally separate from book notes so it can never later be mistaken for something an author said.

---

## Skill 4: `trivium-init`

Sets up a topic anywhere. Creates the folder structure, writes `trivium.config.yaml`, and asks the handful of questions needed to pick a profile.

---

## Configuration

```yaml
profile: research          # research | study | immersive
grounding: gated           # gated | prompted
citations: inline          # inline | on-request | footer
panel: true
extrapolation: flagged     # flagged | off
coverage: full             # full | sampled | off
depth: normal              # quick | normal | deep
```

Three presets, all overridable field by field:

- **research.** Gated, inline citations, extrapolation flagged hard. For papers and anything you will cite elsewhere.
- **study.** Gated, citations on request, panel on. The default for reading books to learn a subject.
- **immersive.** Prompted only, citations on request, panel on. For the therapist case, where you want a good conversation more than a footnoted one. Still flags anything outside the books in prose, but without the gate.

`depth` controls how much time study spends: how finely chapters are subdivided, and how many independent checkers run per note.

---

## Priorities

**Must have**

- Topic layout, config discovery by walking up from the working directory, so skills work in any repo.
- Text extraction from PDF, EPUB and AZW3, with a quality gate that fails loudly.
- Intent interview before note-taking.
- Note schema with verbatim quotes, locators and speaker attribution.
- Verification stages 1 to 3, with independent subagents.
- Coverage pass on every book, scoped to stated intent.
- Brief and section map per book.
- Conversation with natural-language flagging and the gate active in strict profiles.
- Provenance tracking, so a text layer machine-read off a scan is never mistaken for the publisher's own, and is audited against page images before its numbers are trusted.
- The visual pass, so worksheets, forms and diagrams are read rather than silently skipped. Figure notes carry a page image as evidence instead of a quote, are checked by a second reader looking at that image, and stay marked as weaker evidence wherever they are used.

**Should have**

- Cross-book synthesis including disagreements and talking-past-each-other.
- Topic index with the vocabulary bridge.
- Generated `overview.html`, published as an artifact on request.
- Rejection log.
- Conversation-to-note promotion.

**Could have**

- SQLite FTS5 index behind the existing search interface, if a topic outgrows ripgrep.
- Cross-topic search.

**Won't have, and why**

- Embeddings or a vector database. Wrong tool at this scale, adds dependencies that break the portability requirement, and the least auditable option available. Revisit only if a topic passes roughly twenty books.
- In-character roleplay. Your call, and it raises drift risk for little gain.
- Automatic detection of new files. You run skills manually.
- Saved transcripts. Promotion covers the parts worth keeping.
- Running OCR ourselves. A scan that already carries an OCR text layer is used,
  marked and audited. A PDF with no text layer at all is refused rather than
  transcribed, because a text layer this system generated would be a model
  artifact sitting underneath every later guarantee.
- Stripping DRM from Kindle files.

---

## Honest caveats

**The guarantee is strong, not absolute.** Stage 1 is genuinely deterministic: a quote either exists in the file or it does not, and no model gets a vote. Stages 2, 3 and 4 are models checking models. Independence and fan-out make them much better than a single pass, and the gate makes silent failure much less likely, but "impossible" would require a formal system that does not exist for natural language. What this design does deliver is that any failure has to survive several independent checks that were each looking for it, which is a very different risk level from a model summarising freely.

**Gating costs real time.** Doubling latency per turn is noticeable in a flowing conversation. Split profiles exist for exactly this reason, and you may find you want study mode ungated once you trust the notes.

**Coverage on every book is expensive.** It roughly adds half again to study time. It is also the only thing standing between you and a note set that is entirely accurate and quietly missing the book's central argument.

**Study-time vocabulary bridges are a bet.** They replace semantic search with a synonym list built once by a model that read the chapter. If they turn out to be too thin in practice, that is the signal to build the index.

---

## What happens next

On your approval I build the four skills, then we test the whole chain end to end on one real book of your choosing, then adjust before touching a second.
