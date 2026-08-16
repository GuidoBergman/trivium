# Verification

Four stages. Stage 1 is mechanical. Stages 2 to 4 use subagents that must be
independent of each other and of whoever wrote the notes.

Independence is the whole point. A checker that can see the note-taker's
reasoning will agree with it. Give each subagent the narrowest slice of evidence
that lets it do its job, and nothing about why the note was written.

## Stage 1: does the quote exist

```
python3 $TV/tv_verify.py <book>/notes.jsonl --text <topic>/text/<slug>.txt \
    --report <book>/verification.json
```

No model is involved. A quote is in the file or it is not.

Outcomes:

- `PASS` at level `EXACT` or `NORMALIZED` - good
- `PASS` at level `PUNCT` - the words are there but the punctuation differs. Fix
  the quote by copying it again from the text file. Do not leave it.
- `LOCATOR_MISMATCH` - the quote is real but in a different chapter or page. Fix
  the locator to what the script reports.
- `FAIL` - the quote is not in the book. **Drop the note.** No exceptions, no
  rewriting the quote until it passes. A quote you had to hunt for is a quote you
  invented.

Move every dropped note to `REJECTED.jsonl` with a `reason` field.

If many notes from one chapter fail together, stop and check `EXTRACTION.md`.
That pattern means broken extraction, not a careless note-taker.

## Stage 1v: figure notes and the visual pass

Runs when `EXTRACTION.md` lists pages under "Visual pass". Those pages carry
content inside an image, so text extraction saw nothing and the coverage pass
cannot detect the hole either, because it reads the same text.

Render them:

```
python3 $TV/tv_pages.py <topic>/text/<slug>.map.json \
    --from-report <topic>/books/<slug>/extraction.json
```

Read each image yourself and write `figure` notes per `NOTE-SCHEMA.md`. Describe
what the figure is and shows. Do not infer beyond it.

`tv_verify.py` confirms only that the evidence image exists. The judgement is
made by a **second reader**, one subagent per figure note, given the image and
the claim but not your reasoning:

> Look at this page image. Here is a claim someone wrote from it.
>
> Claim: `<claim>`
>
> Answer: does the image show this, does it show something different, or is the
> claim reading in more than the image supports? Reply ACCURATE, WRONG or
> OVERREACHES, then one sentence. If any number, threshold or dose in the claim
> is not clearly legible in the image, say so explicitly.

`WRONG` drops the note. `OVERREACHES` narrows it. If the second reader cannot
read a number, re-render that page at 300 dpi and check again, or drop the
number rather than guessing at it.

Figure notes never get promoted to the strength of quote-backed notes. Say where
they came from wherever they are used.

## Stage 1o: the OCR audit

Runs when the map records `provenance` as `ocr` or `ocr-suspected`. The text
layer was machine-read off a scan, so a verified quote proves the quote is in
*this transcription*, not in the book. Every stage downstream inherits that.

Measure it rather than assuming:

```
python3 $TV/tv_pages.py <topic>/text/<slug>.map.json --sample 12
```

For each sampled page, compare the extracted text for that page against the
rendered image. Count, and report:

- pages where the text matches the image with no material error
- pages with wrong or dropped words that change meaning
- **pages where a number, dose, threshold or duration is wrong**, counted
  separately, because those are the errors that cause harm rather than confusion

Record the result in `BRIEF.md` and in the study report. If any number is wrong,
every numeric claim from this book must be checked against the page image before
it is stated in conversation, and the brief must say so.

Do not average the error rate into a reassuring percentage. Nine clean pages and
one wrong dose is not a 10% problem.

## Stage 2: does the quote support the claim

One subagent per note, batched. Run these in parallel.

Give the subagent **only the claim and the quote**. No chapter, no book title, no
surrounding text, no note id, no explanation.

> Here is a claim and a quotation. Judge only whether the quotation, on its own,
> supports the claim. Do not use anything you know about the subject. Do not be
> charitable about what the author probably meant.
>
> Claim: `<claim>`
> Quotation: "`<quote>`"
>
> Answer with one of: SUPPORTS, OVERREACHES, UNRELATED. Then one sentence of
> reason. If the claim is broader, stronger or more general than the quotation,
> that is OVERREACHES.

`SUPPORTS` passes. `OVERREACHES` means narrow the claim to what the quote
actually says, then re-run. `UNRELATED` drops the note.

Withholding context here is deliberate. It is what makes the check adversarial
rather than a second opinion from someone who already agrees.

## Stage 3: is the claim a misreading of context

One subagent per note. This stage catches the error that matters most.

Give the subagent the quote, the claim, the proposed `speaker` value, and roughly
two paragraphs of text either side. Pull that window from `text/<slug>.txt` using
the offset in `verification.json`.

> Below is a passage from a book, and a claim someone drew from the sentence
> marked between >>> and <<<.
>
> Passage: `<window>`
> Claim: `<claim>`
> The claim attributes this to: `<speaker>`
>
> Answer these in order:
> 1. Is the marked sentence the author speaking in their own voice, or are they
>    quoting someone, describing a view they go on to reject, speaking
>    hypothetically, or setting up a position to knock down?
> 2. Does the surrounding text reverse, limit or qualify the claim in a way the
>    claim does not carry?
> 3. Verdict: SOUND, WRONG-SPEAKER, MISSING-QUALIFIER, or REVERSED.

- `SOUND` passes.
- `WRONG-SPEAKER` means fix the `speaker` field. If the correct value is
  `rejected` or `cited`, the claim wording must change too, because
  "the author argues X" is false when the author was demolishing X.
- `MISSING-QUALIFIER` means add the qualifier to the claim, or add a separate
  `caveat` note and link it.
- `REVERSED` drops the note.

## Stage 4: coverage

Runs on every book. Driven by the book, not by the notes, which is why it cannot
be folded into the stages above. A checker that has read the notes is anchored by
them and will not notice what is absent.

For each chapter that passed the quality gate, one subagent that has **never seen
the notes**:

> Read this chapter and list the major arguments it makes, in your own words,
> most important first. An argument is major if removing it would change what the
> chapter is for. Ignore examples that only illustrate a point already listed.
> Return at most 12.
>
> `<chapter text>`

Then diff that list against the notes for the chapter yourself.

For each item on the fresh list with no corresponding note:

- If it bears on **what the user said they wanted from the book**, write a new
  note for it and send it through stages 1 to 3 like any other.
- If it does not, add one short line to `BRIEF.md` under "Also covered, not
  noted in depth". Do not develop it.

Record the gap count in the study report. A high gap rate means the note-taking
pass was too shallow, and the user should know that.

## Reporting

At the end of study, tell the user plainly:

- notes written, notes kept, notes dropped, and at which stage
- match levels from stage 1, since a pile of `PUNCT` matches suggests messy
  extraction
- coverage gaps found and how many became notes
- any chapter excluded by the quality gate

Never report a clean run that was not clean.
