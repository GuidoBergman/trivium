# The note schema

One note is one thing a source says, plus the evidence that it says it.

`notes.jsonl` holds one JSON object per line and is the source of truth.
`NOTES.md` is generated from it by `tv_render.py`.

```json
{
  "id": "N-042",
  "claim": "Deliberate practice requires immediate feedback to produce improvement.",
  "quote": "Without feedback, efficient or otherwise, improvement is minimal, even for highly motivated subjects.",
  "locator": "ch3 / p.87",
  "kind": "claim",
  "scope": "core",
  "speaker": "author",
  "verified": "quote-exact+entailment+context",
  "topic_tags": ["feedback", "practice design"]
}
```

## Fields

**id** - `N-001` upward, unique within the book. Never reuse an id, even after a
note is dropped. Conversation-derived notes use `C-001` upward.

**claim** - one sentence, plain language, stating what the source asserts. Not a
paraphrase of the quote's wording, a statement of its content. If you cannot say
it in one sentence, it is two notes.

**quote** - verbatim, copied from `text/<slug>.txt`. Not from memory, not from the
PDF viewer, not retyped. Elision is allowed with `...` between kept fragments, and
each fragment must be at least a dozen characters. Keep quotes short enough to be
evidence and long enough to be unambiguous, usually one or two sentences.

**locator** - `ch3 / p.87` for PDFs with pages, `ch3` for EPUBs. Must match where
`tv_verify.py` actually finds the quote, and the script checks this.

**kind** - one of:

- `claim` - an assertion about how things are
- `definition` - the source fixing the meaning of a term
- `technique` - something to do, a method or procedure
- `example` - a case, study or anecdote used as support
- `caveat` - a limit, exception or hedge the source states
- `figure` - content that exists only as a picture, see below

Caveats matter more than they look. A conversation that reproduces an author's
claims without their hedges misrepresents them just as surely as inventing a
claim would.

**scope** - `core` if it bears on what the user said they wanted from the book,
`adjacent` otherwise. Set during the intent interview, and it decides what the
coverage pass treats as a gap.

**speaker** - whose view this is. The most important field, and the one that
prevents the worst error Trivium can make.

- `author` - the author asserts this in their own voice
- `cited` - the author is reporting someone else's view, neutrally
- `rejected` - the author states this in order to argue against it
- `hypothetical` - stated as a possibility or a thought experiment, not asserted
- `conversation` - came out of a conversation with the user, not from any book

A quote can be perfectly real and perfectly support a claim while the claim is
still a lie about the author, because the author was quoting an opponent. Stage 3
of verification exists entirely to catch this. When in doubt, read more context
before choosing.

**verified** - which stages the note passed, joined with `+`. Written by the
study skill after verification, never by hand.

**topic_tags** - free-form, lowercase, for cross-book synthesis. Use the topic's
existing tags where they fit rather than inventing near-duplicates.

## Figure notes

Worksheets, diagrams, decision tables and forms carry real content that text
extraction never sees. A book of protocols can keep its most actionable material
entirely in pictures, and text-only notes would miss all of it without anything
noticing, because the coverage pass reads the same text.

A figure note has no `quote`. Its evidence is a rendered page image.

```json
{
  "id": "F-003",
  "claim": "The Constructive Worry Worksheet is a two-column form, concerns on the left and up to three solutions for each concern on the right.",
  "evidence": "../../pages/edinger/p0079.png",
  "locator": "p.79",
  "kind": "figure",
  "scope": "core",
  "speaker": "author",
  "verified": "image-exists+second-reader"
}
```

**evidence** - path to the rendered page, relative to the book's notes directory.
Produced by `tv_pages.py` and kept, never cleaned up, because the image is the
only thing that makes the claim checkable.

Use the `F-001` id series so figure notes are obvious at a glance.

Figure notes are **weaker evidence than quotes and must be treated as such**.
`tv_verify.py` can only confirm the image exists. Whether the claim is true of
the image is a judgement made by a second reader in stage 2v. Any brief or
conversation resting on a figure note says where it came from.

Describe what the figure *is and shows*. Do not infer a claim the figure merely
hints at, and never transcribe numbers off a low-resolution render without
re-rendering at higher dpi and checking twice.

## What is not a note

- A chapter summary. That belongs in `MAP.md`.
- Your opinion about the book. That belongs nowhere in `notes.jsonl`.
- A claim you are confident about but cannot quote. Drop it, or find the quote.
- A statement stitched together from two distant passages. That is an inference,
  and if it matters, make it a synthesis entry with both note ids, not a note.
