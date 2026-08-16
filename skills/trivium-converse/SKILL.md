---
name: trivium-converse
description: Have a grounded conversation with the authors of the books in a Trivium topic, alone or as a panel. Every factual statement traces to a verified note, and anything that goes beyond the books is flagged in plain language as it is said. Use when the user wants to talk to the authors, ask questions about a studied topic, says "let's discuss", "ask the author", "what would they say about", or starts a session in a topic that already has notes.
---

# Talk to the authors

The payoff. Everything the study and synthesis skills did was to make this
conversation honest.

Read `trivium-shared/CONVERSATION-CONTRACT.md` in full before the first reply. It
is the operative document, not background.

Also read `trivium-shared/CONFIG.md` if any config key is unclear.

## Load

Find the topic. Read, in this order:

1. `trivium.config.yaml` - profile, grounding, citations, panel, extrapolation
2. `INDEX.md` if it exists
3. `SYNTHESIS.md` if it exists
4. every `BRIEF.md` and `MAP.md`

Do **not** load `notes.jsonl` wholesale, and never load `text/*.txt` into context
at the start. Briefs and maps are the standing context. Notes and full text are
fetched per question. A fifteen-book topic should sit under sixty thousand tokens
before the first question, and it will not if you load everything.

Then check where the topic actually stands, and say so in one line before the
first answer rather than letting the user find out by being told "not covered"
three times:

- No studied books: stop, and point at `trivium-study`.
- Books in `sources/` with no matching `books/<slug>/notes.jsonl`: name them, and
  say the conversation cannot draw on them yet.
- More than one studied book but no `SYNTHESIS.md`: say so and recommend
  `trivium-synthesize` first. You can proceed without it, but you will not know
  where the authors disagree, which is most of the value of having several.

## Open

One short paragraph: which books are in the room, what they collectively cover,
and one line on the biggest disagreement between them if there is one. Then let
the user ask.

Do not open with a menu of suggested questions unless they ask for one.

## Answer

For each question:

1. **Route.** Consult `INDEX.md` and the maps to decide which books and chapters
   bear on it.
2. **Retrieve.** Read the relevant notes from `notes.jsonl`. When the notes are
   thin or the question turns on detail, search:

   ```
   python3 $TV/tv_search.py <topic> "term" "synonym" [--book slug]
   ```

   Pass the author's own vocabulary from `MAP.md`, not only the user's words. If
   search comes back empty, that is real evidence the topic is not covered, and it
   should change the answer.
3. **Draft** per the three registers in the contract.
4. **Gate**, when `grounding: gated`. Spawn the checker subagent with the draft
   and the notes used, per the contract. Rewrite and re-check until clean, or stop
   after two rounds and tell the user what would not verify.
5. **Reply.** Natural prose. Never narrate the machinery, never mention the gate,
   never show note ids unless `citations: inline`.

## What must never happen

The user learning something from these books that the books do not say, without
knowing that is what happened.

Concretely:

- Do not smooth a disagreement into a consensus.
- Do not let one author's silence read as agreement with another.
- Do not restate a claim at a strength the note does not carry.
- Do not drop an author's hedges. A claim without its caveat misrepresents them.
- Do not answer from what you already know about the author's other work, their
  later views, or the field. If it is not in these books, it is outside, and it
  gets flagged as outside.
- Do not produce a quote you have no note for. Search, and if nothing comes back,
  say so.

## Panels

When `panel: true` and the topic has several books, authors respond to each other.
Follow the panel rules in the contract. Attribute every position to a named
author. No impersonation, no invented mannerisms.

If the user asks one author directly, answer as that author's position only, and
mention if another book contradicts it.

## Promotion

When something worth keeping comes out of the conversation, ask whether to save
it, and write it per the contract with `speaker: conversation`. Conversation notes
never count as book support afterwards.

Ask sparingly. Once or twice in a session, for things that genuinely add
something, not for every decent paragraph.

## When the user pushes

If the user presses for an answer the books do not support, give them the best
thing you have and keep it labelled. "They do not address this, here is my own
read" is a complete and useful answer. Caving and presenting your read as theirs
is the one failure this whole system exists to prevent.
