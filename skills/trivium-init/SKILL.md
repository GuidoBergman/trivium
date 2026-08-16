---
name: trivium-init
description: Set up a Trivium topic in any repository so books or papers can be studied and later discussed with their authors. Use when the user wants to start reading a new subject, add books to a new topic, or says "set up a topic", "start a new topic", "I want to read these books". Creates the folder structure and the config, and asks what the user wants out of the reading.
---

# Set up a Trivium topic

Creates a topic: a folder holding some books, their verified notes, and the
settings that shape how conversations about them will work.

Read `trivium-shared/CONFIG.md` before writing any config.

## Where the topic goes

Ask nothing about this, work it out.

- Inside the trivium repository: `topics/<slug>/`
- Any other repository: `.trivium/` at the repository root, or
  `.trivium/<slug>/` if a `.trivium/` already exists with a different topic

If a `trivium.config.yaml` already exists in scope, this topic exists. Do not
re-init it. Say so and offer to add books to it instead.

## Steps

**1. Find the sources.** The user usually already put files somewhere. Look for
PDFs and EPUBs in the working directory, in a `books/` or `sources/` folder, and
in `~/Downloads` if the user mentions having just downloaded something. Show what
you found and confirm before copying anything.

Move or copy the files into `<topic>/sources/`. Leave the originals alone if they
live somewhere the user cares about.

**2. Ask what they want out of it.** This is the most important question in the
whole system, because it decides what gets noted deeply, what gets noted briefly,
and what the coverage pass later counts as a gap.

Ask it as a real question, not a form. Something like: what do you want to be able
to do or understand after reading these? Are you after the practical techniques,
the underlying argument, the evidence, or the debate between them?

Push back if the answer is "everything". Everything is not an intent, it is the
absence of one, and it makes the coverage pass useless. Get to something that
could distinguish a relevant chapter from an irrelevant one.

Write the answer verbatim into the `intent` key.

**3. Pick a profile.** Use `AskUserQuestion` with the three presets from
`CONFIG.md`, described in terms of the user's actual situation rather than the key
names. Default to `study` if they do not care.

If the topic is a single research paper, suggest `research`. If the topic is
something they want to talk through rather than cite, suggest `immersive`, and say
plainly that it turns the gate off.

**4. Write the structure.**

```
<topic>/
  trivium.config.yaml
  sources/
  text/
  books/
```

Write `trivium.config.yaml` from the template in `CONFIG.md`, filled in with the
title, profile, overrides and intent.

**5. Write the router, if this repository is for the topic.** Per
`trivium-shared/ROUTER.md`, a topic repository gets a short `CLAUDE.md` so that
subject-matter questions load `trivium-converse` automatically instead of the
user having to invoke it every time. Symlink `AGENTS.md` to it.

Ask first, in one line, because it is the wrong move in a repository whose main
purpose is something else. "Is this repository mainly for this topic, or is the
reading a side activity in a project about something else?" Write the router only
for the first case.

Never restate the conversation contract inside the router. It routes.

**6. Report and hand off.** List the books found, the profile chosen, and the
intent as recorded. Then tell the user to run `trivium-study` on the first book,
and mention that studying is deliberately slow.

Do not start studying. Init sets up, study reads.
