---
name: trivium-status
description: Show where a Trivium topic stands and what to run next - which books are studied, how many notes survived verification, whether the cross-book synthesis is stale, and which step of the pipeline comes next. Use when the user asks "where am I", "what should I run next", "is this done", "what's the status", or opens a topic after time away.
---

# Where does this topic stand

Answers one question: what do I run next.

```
python3 $TV/tv_status.py [topic-dir]
```

Resolve `$TV` and find the topic per `trivium-shared/SKILL.md`. The script walks
up from the working directory itself, so usually no argument is needed.

## Read the output, then say the one thing that matters

The script prints a table and a "Next" list. Do not simply paste it back. Say, in
one or two sentences, what the user should do now and why. Then show the table if
it adds anything.

## What the states mean

- `extracted` - the text is ready but no notes exist. Study has not run.
- `notes-only` - notes exist but no `BRIEF.md`. A study run stopped partway,
  probably interrupted. The notes may not have been fully verified, so say so and
  recommend rerunning study on that book rather than trusting them.
- `studied` - notes and brief both present.

Synthesis is `stale` when a book's notes changed after `SYNTHESIS.md` was last
written. Stale synthesis is worse than missing synthesis, because it looks
current and the conversation will trust it. Recommend rerunning it.

## Things worth flagging unprompted

- A book with a high `DROPPED` count relative to `NOTES`. That means verification
  is rejecting a lot, which usually points at bad extraction rather than at bad
  note-taking. Suggest checking its `EXTRACTION.md`.
- A book whose provenance is not `native`. Its quotes are only as good as the
  machine transcription underneath them.
- Books in `sources/` that were never extracted, which usually means someone
  added a file and forgot.

## What this skill does not do

It never studies, synthesises or changes anything. It reads and reports. If the
answer is "run study", say so and stop, rather than starting a study run the user
did not ask for.
