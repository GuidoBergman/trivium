# The router

A topic repository gets a short `CLAUDE.md` so that questions about its subject
matter are answered from the notes by default, without the user having to invoke
`trivium-converse` every time.

The router **routes**. It does not restate the conversation contract. The contract
lives in `CONVERSATION-CONTRACT.md` and nowhere else, for three reasons:

- It is thousands of words, and a repository's `CLAUDE.md` is loaded on every turn
  in that repository, including turns that have nothing to do with the books.
- A second copy of a safety-critical contract drifts from the first. With one
  topic that is a nuisance. With five it is a guarantee that one of them is wrong.
- The skill works in any repository with no setup. A copied contract only works
  where it was pasted.

## What it cannot do

A `CLAUDE.md` instruction is a strong default, not a mechanism. It can be missed
in a long session, and it does not itself run the grounding gate.

So the router's job is to get the skill loaded. Enforcement stays inside the
skill, where the gate actually spawns a checker against the draft. Never write a
router that implies the grounding guarantee holds without the skill.

## Template

`trivium-init` writes this into the topic root as `CLAUDE.md`, with
`AGENTS.md` symlinked to it so both conventions find the same file. Substitute
the topic's real title and book list.

```markdown
# <Topic title>

This directory is a Trivium topic. It holds books in `sources/`, their extracted
text in `text/`, and verified notes in `books/<slug>/`.

## Answering questions about <subject>

Any substantive question about <subject> must be answered from the verified notes,
not from general knowledge. **Load the `trivium-converse` skill before answering
the first such question in a session**, and follow it for the rest of the session.

That includes questions that look casual. "Is it normal that X" is a question
about what these books say, and answering it from memory is exactly the failure
this repository exists to prevent.

Books here: <slug: short title, one per line>

## Everything else

Editing scripts, fixing files, tidying directories and general work in this
repository proceed normally. The rule above is about the subject matter, not about
the repository.

## Never

- Never answer a <subject> question from general knowledge without saying, in the
  sentence itself, that it is not from the books.
- Never present anything from `books/_conversation/` as something an author said.
- Never edit `notes.jsonl` by hand. It is the verified record.
```

## When the router is wrong

Do not write one into a repository whose main purpose is something else, for
example a research project where one paper is being read on the side. There, the
default should stay normal and `trivium-converse` should be invoked deliberately.
Ask the user which kind of repository it is rather than assuming.
