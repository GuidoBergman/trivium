# Configuration

Every topic has a `trivium.config.yaml`. It is read by the skills, not by the
scripts, so it never needs a YAML parser to be installed.

```yaml
title: Deliberate practice
profile: study            # research | study | immersive
grounding: gated          # gated | prompted
citations: on-request     # inline | on-request | footer
panel: true               # authors respond to each other
extrapolation: flagged    # flagged | off
coverage: full            # full | sampled | off
depth: normal             # quick | normal | deep
intent: |
  What the user said they wanted out of this topic. Written during init and
  updated whenever it changes. Study and coverage both key off this.
```

## Presets

Pick with `profile`, then override any single key beneath it.

**research** - `grounding: gated`, `citations: inline`, `extrapolation: flagged`,
`coverage: full`, `panel: true`. For papers and anything the user will cite
elsewhere. Every factual sentence carries its source in the text.

**study** - `grounding: gated`, `citations: on-request`, `extrapolation: flagged`,
`coverage: full`, `panel: true`. The default. Reading books to learn a subject.
The gate still runs, the citations stay out of the way until asked for.

**immersive** - `grounding: prompted`, `citations: on-request`,
`extrapolation: flagged`, `coverage: full`, `panel: true`. For conversations where
flow matters more than footnotes, such as talking to a shelf of therapy books. The
gate is off, so grounding rests on instruction alone. Everything else is unchanged,
including that unsupported statements must still be flagged in the prose.

## Keys

**grounding**

- `gated` - a checker subagent audits every draft reply before the user sees it,
  per `CONVERSATION-CONTRACT.md`. Roughly doubles response latency.
- `prompted` - the same rules apply by instruction only. Faster and more natural.
  Compliance is high, not guaranteed. Say so if the user asks.

**citations**

- `inline` - note ids or locators appear in the reply text
- `on-request` - no citations until the user asks, and they can always ask
- `footer` - a short source list at the end of the reply

Quotes are stored for every note regardless. This key only controls display.

**extrapolation**

- `flagged` - "she does not take this up directly, but given X she would probably
  say Y" is allowed, marked in the sentence
- `off` - refuse to extrapolate, say the books do not cover it and stop

**coverage**

- `full` - stage 4 runs over every chapter
- `sampled` - stage 4 runs over a fifth of chapters and reports the gap rate as a
  signal for whether to run the full pass
- `off` - no coverage checking. Accuracy checking always runs regardless.

**depth** - how much work study does per chapter.

| | chapter chunking | stage 2 and 3 checkers per note | target notes per chapter |
|---|---|---|---|
| `quick` | whole chapter | 1 each | 5 to 10 |
| `normal` | halves | 1 each | 10 to 20 |
| `deep` | sections | 2 each, disagreement drops the note | 20 to 40 |

At `deep`, two checkers run per stage and any disagreement between them drops the
note rather than triggering a tiebreak. Disagreement is itself evidence the claim
is not clearly supported.
