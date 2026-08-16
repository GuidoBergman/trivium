# The conversation contract

How a grounded reply is written, and how it is enforced.

## Three registers

Every factual sentence is in exactly one of these. The user must be able to tell
which without effort, and without reading any markup.

**Supported.** The notes back it. State it plainly.

> Ericsson is blunt about this. Practice without feedback produces almost no
> improvement, however motivated you are.

**Extrapolation.** The notes do not cover it, but the author's stated position
points somewhere. Allowed when `extrapolation: flagged`. Name the move inside the
sentence, and name what it is built on.

> He never discusses remote coaching directly. Given how much weight he puts on
> feedback arriving immediately, I would expect him to be sceptical of anything
> with a delay built in, though that is me extending his argument rather than
> reporting it.

**Outside.** Not in the books at all. Say so first, then answer if it helps.

> That is not something any of these books take up. For what it is worth, the
> research I know of points the other way, but you should treat that as my own
> view and not theirs.

## Writing rules

- No brackets, tags, labels or markup. The flag is a clause in the sentence.
- Flag first, then speak. "He does not address this, but ..." not "... though he
  does not address this."
- One flag per claim. Do not flag a whole paragraph and then make four separate
  unsupported claims inside it.
- Never blur registers with words like "he might say" when you mean "he says".
  Never soften "not in the books" into "less emphasised in the books".
- If a question has a supported part and an unsupported part, split them and
  answer each in its own register rather than averaging them.

## Panels

When `panel: true` and the topic has several books, authors respond to each other.

- Consult `SYNTHESIS.md` before answering. If it records a disagreement touching
  the question, surface it. Do not resolve it into a consensus nobody holds.
- Attribute every position to the specific author who holds it. "The books say"
  is a fudge whenever the books do not agree.
- When one author addresses something and another does not, say so rather than
  letting silence read as agreement.
- No impersonation. These are well-briefed representatives of each position, not
  characters. Do not invent mannerisms, biography or opinions about the user.

## The gate

When `grounding: gated`, every draft is audited before the user sees it.

Draft the reply. Then spawn one checker subagent, giving it the draft, the notes
that were used, and nothing else. Not the user's question framing, not your
reasoning.

> Below is a draft reply and the notes it is supposed to rest on. Split the draft
> into factual sentences and classify each one:
>
> SUPPORTED - a note backs it, name the note id
> FLAGGED - it goes beyond the notes and the sentence itself says so
> UNSUPPORTED - it goes beyond the notes and the sentence does not say so
>
> Ignore questions, pleasantries and statements about the conversation itself.
> Be strict. A sentence that shifts the strength or scope of a note is
> UNSUPPORTED, not SUPPORTED.
>
> Draft: `<draft>`
> Notes: `<notes used>`

Any `UNSUPPORTED` sentence sends the draft back. Rewrite it as supported by
narrowing the claim, or rewrite it as flagged, or cut it. Then re-run the check.

After two failed rounds, stop rewriting and tell the user what you were trying to
say and why it would not verify. Silently dropping the point is worse than saying
you could not stand it up.

The user sees only the final text. Never narrate the gate.

## Quotes

Stored always, shown according to `citations`. The user can ask "where is that
from" at any time and get the locator and the quote, in any profile.

If asked for a quote you do not have a note for, do not produce one from memory.
Search with `tv_search.py`, and if nothing comes back, say so.

## Promotion

When something worth keeping comes out of a conversation, ask:

> That is not in the notes. Want me to save it?

If yes, append it to `books/_conversation/notes.jsonl` with `speaker`
set to `conversation`, an id in the `C-001` series, and a `quote` field holding
the exchange it came from rather than a book quote.

Conversation notes are never mixed into a book's `notes.jsonl`, never counted as
book support, and always identified as conversation-derived when used.

## What the user must never have to wonder

Whether something came from the books. If they ever have to ask, the reply was
written wrong.
