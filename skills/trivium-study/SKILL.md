---
name: trivium-study
description: Study one book or paper end to end and produce verified notes, a one-page brief and a chapter map. Extracts the text from PDF, EPUB or AZW3, checks extraction quality, reads worksheets and diagrams that exist only as images, audits machine-read text from scans, takes structured notes with verbatim quotes, then attacks those notes with independent checker subagents until every surviving note is provably grounded in the source. Use when the user says "study this book", "read this paper", "take notes on X", or points at a book file in a Trivium topic. This is a long process by design.
---

# Study a book

Produce notes that can be trusted later, because a conversation is only as honest
as the notes underneath it.

Read first:

- `trivium-shared/NOTE-SCHEMA.md`
- `trivium-shared/VERIFICATION.md`
- `trivium-shared/CONFIG.md`

Resolve `$TV` to the shared scripts directory, and find the topic, both per
`trivium-shared/SKILL.md`.

Tell the user up front roughly how long this will take and that you will report
what was dropped. Then work without asking for permission at each step.

## 1. Extract

```
python3 $TV/tv_extract.py "<topic>/sources/<file>" --out <topic>/text
```

Note the slug it prints. Everything downstream uses it.

If it exits non-zero with almost no text, the file is image-only. Stop. Tell the
user Trivium does not handle scanned books and they need a text-based copy. Do not
try to work around it.

## 2. Quality gate

```
python3 $TV/tv_quality.py <topic>/text/<slug>.txt \
    --md <topic>/books/<slug>/EXTRACTION.md \
    --json <topic>/books/<slug>/extraction.json
```

- `OK` - proceed.
- `DEGRADED` - proceed, but the excluded sections are off limits for notes, and
  `BRIEF.md` must say which parts of the book were not read.
- `UNUSABLE` - stop and tell the user why.

Never take a note from an excluded section. If a chapter you needed was excluded,
say so rather than filling the gap from general knowledge.

Then read two more things in the report before going on.

**Provenance.** If it is not `native`, the text was machine-read off a scan. Run
the OCR audit, stage 1o of `VERIFICATION.md`, before taking notes, because its
result decides how much the rest of the run can be trusted.

**Visual pass.** If the report lists pages under "Visual pass", those pages hold
content inside images. Plan to run stage 1v. In a workbook or a manual this is
often where the actual protocol lives, in forms and decision tables, so skipping
it produces notes that are accurate and useless.

## 3. Confirm intent

Read `intent` from `trivium.config.yaml`. Restate it in one sentence and ask
whether it holds for this particular book, since a topic's intent and a single
book's role in it can differ.

If the topic has no intent recorded, ask now. Do not start noting without one.

## 4. Take notes

Work chapter by chapter, in order, chunked per the `depth` table in `CONFIG.md`.

For each chunk:

1. Read the actual text from `text/<slug>.txt` at the offsets in
   `<slug>.map.json`. Do not read the PDF or work from what you already know
   about the book.
2. Write notes to `books/<slug>/notes.jsonl` in the schema. Copy every quote out
   of the text. Never retype from memory.
3. Set `scope` against the intent, and `speaker` with care. When a passage reports
   or criticises someone else's view, that is `cited` or `rejected`, and the claim
   wording must not say the author argues it.
4. Write the `MAP.md` entry for the chapter as you go, while the chapter is fresh.

The `MAP.md` entry per chapter is three things:

- what the chapter is for, in one or two sentences
- the terms this chapter uses, in the book's own vocabulary
- the obvious synonyms and adjacent phrasings a reader might search for instead

That last line is what lets keyword search find a chapter about compassion fatigue
when the user searches for burnout. It is not optional and it is not decoration.

Do not write `BRIEF.md` yet. It is written from verified notes, at the end.

## 5. Verify

Follow `trivium-shared/VERIFICATION.md` exactly. Summary of the order:

1. Run `tv_verify.py`. Fix `PUNCT` matches and locator mismatches. Drop `FAIL`s to
   `REJECTED.jsonl` with reasons.
2. Stage 1o, the OCR audit, if provenance is not `native`.
3. Stage 1v, the visual pass, for every page the quality gate listed, including a
   second reader per figure note.
4. Stage 2 entailment subagents, one per note, in parallel, given only the claim
   and the quote.
5. Stage 3 context subagents, one per note, in parallel, given the quote inside a
   window of surrounding text.
6. Re-run `tv_verify.py` after any edits, because a rewritten claim can shift the
   quote.

Spawn subagents in batches, in parallel, in one message per batch. A batch of
twenty notes is reasonable. Do not check notes one at a time in sequence.

Give each checker only what `VERIFICATION.md` specifies. Adding context to be
helpful destroys the independence that makes the check worth running.

## 6. Coverage

Per `coverage` in the config, and stage 4 of `VERIFICATION.md`.

One subagent per chapter, none of which has seen the notes, each listing the
chapter's major arguments cold. Diff against the notes yourself.

Gaps inside the intent become notes and go through stages 1 to 3. Gaps outside it
become one short line each under "Also covered, not noted in depth" in `BRIEF.md`.

## 7. Write the brief

`BRIEF.md`, one page, built only from verified notes:

- what the book argues, in a short paragraph
- who it is written for and what it assumes the reader knows
- its main claims, as a short list, each carrying its note id
- what it hedges on or explicitly does not claim
- also covered, not noted in depth
- what was not read, if the quality gate excluded anything
- **how this book's text was obtained**, when provenance is not `native`,
  together with the OCR audit result, stated as counts rather than a soothing
  percentage
- **which material came from page images rather than text**, listing the figure
  notes, since they are weaker evidence and stay weaker wherever they are used

Every factual sentence in the brief must trace to a note. The brief is not a place
to be more confident than the notes allow.

## 8. Render and report

```
python3 $TV/tv_render.py <topic>/books/<slug>/notes.jsonl
```

Then report to the user, plainly:

- notes written, kept, and dropped, with the stage each drop happened at
- stage 1 match levels, since many `PUNCT` matches suggest messy extraction
- coverage gaps found, and how many became notes
- sections excluded by the quality gate
- provenance, and the OCR audit result if one was run
- how many notes rest on page images rather than quotes
- how long it took, so `depth` can be calibrated against real numbers

Never report a clean run that was not clean. A dropped note is the system working,
not a failure to hide.

## 9. Offer the next step

If this is the topic's only book, suggest `trivium-converse`. If the topic now has
more than one, suggest `trivium-synthesize` first, since the conversation is much
better when it knows where the authors disagree.
