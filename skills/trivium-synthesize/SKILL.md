---
name: trivium-synthesize
description: Build the cross-book layer for a Trivium topic - where the authors agree, where they genuinely disagree, and where they talk past each other. Also builds the topic index and the browsable HTML overview. Use when a topic has more than one studied book and the user wants the whole picture, says "synthesize", "compare these books", "where do they disagree", or asks for a topic overview.
---

# Synthesize a topic

Per-book study answers what each author says. This answers what the topic looks
like when you hold the books next to each other. It is a separate skill because it
is a different job, and because it only makes sense once at least two books are
studied.

Read `trivium-shared/NOTE-SCHEMA.md` and `trivium-shared/CONFIG.md`.

## Preconditions

Every book in `<topic>/books/` must have a `verification.json` showing no
outstanding failures. If one does not, say which and stop. Synthesising unverified
notes launders unverified claims into a document that looks authoritative.

## 1. Gather

Read every `BRIEF.md`, every `MAP.md`, and every `notes.jsonl`. Do not read the
full text of the books at this stage.

Cluster notes across books by `topic_tags` and by subject. Where tags have drifted
into near-duplicates across books, normalise them and rewrite the tags in the
`notes.jsonl` files so the next synthesis is cleaner.

## 2. Classify each cluster

Every cluster where two or more books have something to say falls into one of
four categories. Getting this classification right is the whole value of the
skill, and the third category is the one everyone misses.

**Agreement.** The authors assert compatible things. Record the shared claim and
the note ids from each book. Note whether they agree for the same reasons, because
agreeing on a conclusion via incompatible arguments is not really agreement.

**Disagreement.** The authors assert incompatible things about the same question.
Record both positions in their own terms, both sets of note ids, and what each one
would need to be true for. Do not resolve it. Do not pick a winner. Do not average
them into a bland middle position that neither author holds.

**Talking past each other.** The authors appear to disagree but are not answering
the same question, or are using the same word for different things. This is the
most common case in any real topic and the least visible. Record what each author
means by the shared term, and what question each is actually answering.

**Only one covers it.** One book treats something substantial that the others do
not touch. Worth recording, because silence from the others must never be read as
agreement in a later conversation.

## 3. Write SYNTHESIS.md

Structure it as the four categories above, most consequential first.

Every entry carries the note ids it rests on. A synthesis claim with no note ids
behind it is your opinion, and it does not belong in the file.

Where you draw an inference the books do not state, mark it as an inference in the
text. The synthesis is allowed to reason across books, but the reasoning has to be
visible as reasoning.

End with what the topic as a whole does not cover, kept short. This section makes
out-of-scope detection much sharper during conversation.

## 4. Write INDEX.md

The topic's routing table. For each significant subject:

- which books cover it, with chapter locators
- the vocabulary each book uses for it, taken from the `MAP.md` entries
- the cross-book category from step 2, when there is one

This is the file consulted first during conversation, before any search. Keep it
compact enough to load into context whole.

## 5. Build the overview

Write `overview.html` as a single self-contained file with no external requests.
Include:

- the topic, the intent, and what the books collectively cover
- one card per book, from its `BRIEF.md`
- the disagreements section, given prominence, since it is what rereading a
  synthesis is usually for
- a section map per book, collapsed by default

Then publish it with the `Artifact` tool so the user gets a URL. Publishing
uploads the content to claude.ai, where it is private to the user's account.
Mention that once, the first time you publish for a topic, and do not belabour it.

Keep the same file path across runs so republishing updates the same URL.

## 6. Report

Say how many clusters fell into each category, and name the two or three
disagreements that most change how the topic should be understood.

If the books turn out to agree on almost everything, say that plainly. It usually
means the reading list is too narrow, and that is worth the user knowing before
they build a view on it.

## 7. Offer the next step

Synthesis is the last thing that has to happen before the topic is usable. End by
telling the user they can now run `trivium-converse`, and give the URL of the
overview you published.

If any book in the topic is still unstudied, say which, and say that the
synthesis will need rerunning once it is done. Synthesis over an incomplete
topic is not wrong, it is just provisional, and the user should know which it is.
