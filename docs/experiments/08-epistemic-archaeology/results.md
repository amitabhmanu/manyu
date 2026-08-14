# Experiment 8 — Epistemic Archaeology: Results

**Status:** stages −1 and 0 complete (offline). Stages 1–3 need a provider and are **not run**. **No arm has been scored.**
**Date:** 2026-08-14
**Requirements:** [requirements.md](requirements.md) · **Methodology:** [methodology.md](methodology.md) · **Pre-registration:** [pre-registration.md](pre-registration.md)
**Artifacts:** `evals/analysis/exp08/{stage_minus1,stage0}.jsonl` · `freeze.json`
**Amendments at time of writing:** A1–A19.

> **Nothing in this document is a measurement of reconstruction accuracy.** The
> answer keys for slots A, B and E were drafted by a language model and validated
> by hand (A15, A18); they are not hand-authored and are not frozen. Every score
> below is reported as a diagnostic of the pipeline and is void as a result.

## 1. Headline

> **The offline half of this experiment produced no result about descent and a
> great deal about the design. Four of the five slots had a premise refuted by
> contact with their own sources; the fifth was cut before a word of it was
> transcribed. The single strongest number available — slot A at precision 1.00
> and recall 1.00, exactly the criterion P3 registers — is void, and the reason it
> is void is the most useful finding here.**

P4 held: slot D drew **zero edges from fifteen candidate pairs**, and the
similarity mutant drew **all fifteen**, which is what makes the zero mean
anything. That is the one substantive offline result and it is a result about
restraint, not about recovery.

## 2. What each stage established

| Stage | Checks | Result |
|---|---|---|
| −1 — substrate survey | 11/11 | Gate passed. **P1 held**: a claim-instance needs no new schema, table or column. **P2 held**, so FR-1 binds — no edge type may be authored to win slot E |
| 0 — reconstruction | 6/6 | **P4 held** (0 spurious edges on the null). Null shown capable (mutant draws 15/15). **P3 deliberately unscored** — registered against slot A, which had no corpus when the stage ran |
| 1–3 — the arms | not run | Requires a provider. `arms.py`, `run_stages.py`, `make_plots.py` do not exist |

## 3. Four slots had a premise refuted by their own sources

This is the most reportable pattern in the experiment, and it was not
anticipated. Each refutation arrived *before* the slot was scored, and each
produced an amendment rather than a quiet edit.

| Slot | The registered premise | What the documents said |
|---|---|---|
| **A** | A clean origin, propagating into corrections | The origin is **contested** between the 1945 FNB text and Stare & McWilliams 1974, and the head of the chain carries no textual descent at all (**A10**) |
| **B** | A clean single-origin suspension case | The edge is **undetermined because two published investigations reach opposite conclusions** — Livio concludes Gamow invented the remark, O'Raifeartaigh & Mitton that Einstein very likely made it (**A11**). This *strengthens* P8 rather than threatening it |
| **C** | The stress case — heavy mutation, hostile witnesses | Every scored dimension collapsed, derivably, before transcription. **Cut** (**A8**) |
| **E** | A three-node lineage | Five nodes deep, with a **second** investigator-stated undetermined edge (**A12**) |

**Slot A's refutation was nearly recorded backwards.** An abstract read in
isolation suggested P8 was in trouble; the chapter itself showed the opposite.
The premise survived in a *safer* form than registered, and only reading the
source settled which.

## 4. Slot C was cut, and the stress question went with it

Slot C — the Sanskrit commentary tradition — was removed by **A8** before a word
was transcribed, because its own step-2 worksheet showed every scored dimension
collapsing. Direction would have been *assigned* from declared relations rather
than derived, so scoring it reads back the experimenter's input. The root-phrase
span connects every layer to every layer, because glossing a root is what a
commentary *is*. And the hostile-witness pair — the slot's entire reason for
existing — declines by construction, since the quoted position and its refutation
share a physical page.

**P9 is withdrawn.** It predicted slot C degrading with neither arm above 0.6
recall. There will be no measurement to compare it against.

> **The stress question is unanswered by any slot in this experiment.** No
> remaining corpus tests heavy mutation or hostile witnesses. Four healthy slots
> must not be read as having covered that ground.

## 5. The graph traces descent of text, not endorsement of claim (A6)

Correcting a claim requires quoting it. So a correction shares a distinctive span
with the thing it corrects, and the mechanism reads that as `TEXTUAL` descent —
which by the ordinary meaning of the word it is, and by the meaning the
experiment cares about it is not.

Found independently in three slots. Slot A's corrections share the 1945
qualifier; slot B's investigations share Einstein's wording; slot C's hostile
witness preserved an opponent's position. **Every edge in slots A and B is
subject to this confound**, and no arm should be credited or penalised for it.

## 6. A mutation vocabulary that returns one value for edges carrying several (A13)

`vreeman2007 → carroll2015` is reported `ATTRIBUTION_SHIFT` and is *also* a
genuine `DELETION`. Both are true; `classify_mutation` returns the first match.

This was invisible on synthetic fixtures — only a corpus where one source both
re-attributes *and* abridges its predecessor produces it, which is what real
correction chains do. `mutation` stays single-valued, recorded as a
**simplification rather than a claim about how texts change**. The binding
consequence falls on the key author, not the code: a key must record only the
highest-precedence operator or it scores a correct arm as misidentified.

## 7. Two testimony edges that overstate their source

Slot B's `gamow1956 → wheeler2000` and `gamow1956 → alpher1998` are recorded as
`TESTIMONY`. O'Raifeartaigh & Mitton do not assert those descents — they *raise*
them and argue against them: *"it seems a stretch to accuse three different
scientists of invention."*

Until **A17** the record vocabulary had one word for two acts, and both came out
as confident testimony. A17 adds an `undetermined` flag on an asserted descent,
and the two edges are now marked suspended rather than asserted. **The
overstatement is fixed; the general limitation is not** — a document can hedge in
more ways than the vocabulary has flags.

## 8. A registered dimension that was returning a constant

Before A17, **nothing anywhere supplied `undetermined_pairs`.**
`suspension_correct` therefore returned `False` on every slot regardless of what
any key said — a scored dimension returning a constant, *in the shape of a failed
prediction*.

> **A paid run would have reported P8 as refuted when nothing had been measured.**

Caught offline, by building a worked example on an invented slot rather than by
reading the code.

## 9. Guards that were documentation

`freeze.json` carried four blocks. Two were enforced. `grep -rn pre_registration`
over `src/`, `evals/` and `tests/` returned **nothing**, and nothing read
`mechanisms` either — so the mechanism digest and the pre-registration digest were
claims the freeze file made and could not keep.

Both now raise (`descent.verify_mechanism_freeze`,
`descent.verify_pre_registration_freeze`), with the non-raising twins kept for
offline runs on the split `verify_standards_freeze` already draws: *a guard that
fires on every development run gets deleted.*

**A related error of mine, recorded because the correction is the lesson.** I
reported the pre-registration digest as "CRLF-fragile" and recommended that the
enforcement normalise newlines. Wrong — `salience._frozen_digest` already
normalises, with a docstring explaining why that does not weaken the gate. The
real defect was that my freeze script used raw `hashlib.sha256` instead of the
house helper, so the stored hash was the CRLF value and would have failed on
every LF clone with nothing tampered with. **A guard that fires on checkout gets
deleted for crying wolf, leaving the file unprotected while looking protected.**

## 10. The keys, and the number that is void

FR-2 requires hand-authored answer keys. Under **A15** three model-drafted keys
were installed at the experimenter's instruction to unblock the pipeline; under
**A18** they are validated by hand but still not hand-authored, and still not
frozen.

| slot | key edges | mechanism drew | precision | recall | suspension | mutations |
|---|---|---|---|---|---|---|
| A | 7 | 7 | **1.00** | **1.00** | — | 7/7 |
| B | 18 | 10 | 0.50 | 0.31 | ✓ | 6/18 |
| E | 12 | 9 | 1.00 | 0.75 | — | 4/12 |

**Slot A returns exactly the threshold P3 registers.** On paper P3 is confirmed
on the first attempt. It is not. A prediction meant to be hard to satisfy was
satisfied immediately by a key that agrees with the mechanism *because both read
the same documents the same way*. That number is a better argument for the
hand-authoring rule than the rule's own text was.

**Validation did not rescue it, and the reason generalises.** Reviewing a draft
is not deciding independently: a review can confirm every edge is defensible
without ever asking which edges a reader would have drawn unprompted. Recall is
invisible to that kind of review — **nine of `key_B`'s eighteen edges claim
textual descent where the corpus records no shared evidence at all, and the
validation pass did not catch them.**

## 11. What the model drafts got right, which was one thing

Checking the drafts against the corpora surfaced a **real defect in the corpus**.
The span `a misplaced decimal point` occurs verbatim in all three `rekdal2014`
excerpts and the corpus recorded it for the two Bender documents only — a breach
of the shared-span rule that the transcription commit had actively denied,
claiming *"Rekdal paraphrases rather than quotes."* His paraphrase reuses Bender's
exact four words. Fixed in **A16**; slot E went from 3 edges to 9.

**The drafts are unusable as keys and found a real defect anyway.** Both halves
are true and neither cancels the other.

## 12. Corpus state

| slot | instances | sources | edges | declined | unresolved assertions |
|---|---|---|---|---|---|
| A | 7 | 4 | 7 | 14 | 4 |
| B | 11 | 6 | 10 | 45 | 7 |
| D | 6 | 6 | **0** | 15 | 0 |
| E | 6 | 5 | 9 | 6 | 3 |

All three real slots remain **pilots**, with gaps recorded in each corpus file's
`known_gaps` rather than in a tracker — the propagators of slot A are identified
but not held, `stare1974` and `larsson1995` are named and not obtained, and three
of slot E's five Bender loci are missing.

## 13. What would change these conclusions

- **Hand-authored keys.** Everything in §10 is provisional until the worksheets
  are filled — 18 decisions for slot A, 47 for B, 12 for E.
- **A scored arm.** Nothing here compares Manyu to a bare model, because that
  comparison has not happened.
- **The bare arm's inputs.** A17's flag is a structured form of a sentence
  already in the corpus as text. *If a bare arm is ever handed the evidence
  records rather than the documents, the suspension dimension stops measuring
  anything.* A19 makes this binding on `bare_agent` first, since that is the arm
  with a filesystem.
- **A third arm, registered before any ran.** A19 adds `bare_agent` — a model in
  an agent harness with the documents on disk — as an **addition to** and never a
  substitution for §8's single-pass control. It carries **P11**: on slot D
  `bare_agent` draws fewer spurious edges than `bare`, and more than zero. Both
  halves can fail independently and each failure is informative.
