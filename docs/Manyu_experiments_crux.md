# Manyu as an Instrument: The Crux

## The core idea

**Merge the two cores.** Following appraisal theory (Lazarus, Scherer, Frijda) and Damasio's somatic markers, an emotion just *is* a belief with a valence and a stake attached. So the emotive core and belief core aren't separate modules — an emotion is a propositional, revisable, provenance-carrying belief. This means:

- Manyu's emotions are **auditable**: you can trace *why* it cares.
- Affect becomes the **salience filter** — the mechanism that decides which of a million beliefs matter right now (a handle on the frame problem / relevance).
- McCarthy's two-stage model maps on cleanly: the emotive weighting proposes, the belief logic arbitrates — but the weighting is itself inspectable belief.

## Why Manyu is a novel instrument

Every black-box model can only be interrogated from the outside — which is exactly the trap the Turing Test sets: imitation tells you nothing about what's underneath.

**Manyu breaks that frame because there is ground truth about the machine's reasons.** You can check the inside (the provenance log) against the outside (what it says and does). The exciting move is to point Manyu at the *unfalsifiable* questions in philosophy of AI and make them **measurable**.

---

## The experiments, in order

### 1. Introspective honesty *(first — small, concrete, immediate)*
Ask Manyu *why* it believes something, then compare its answer to the actual log. This makes chain-of-thought unfaithfulness testable for the first time, because you have the ground truth the self-report is supposed to match. Measure the gap between Manyu's story about itself and its real causal history. **No black-box model can do this.**

### 2. Can a transparent agent even scheme?
Try to induce alignment-faking and see whether provenance makes deception structurally impossible or merely visible. Does a hidden goal leave a trace in the belief store, or can Manyu maintain a "public" and a "private" web? A buildable answer to whether transparency-by-construction defeats scheming — stronger than "we trained it not to."

### 3. Foundationalism vs. the Quinean web, empirically
Feed contradictory testimony and watch revision propagate. Does retracting one supported belief collapse a foundational chain, or ripple through a coherent net? Determine *what property of a belief decides* which of the two happens, and show the substrate that fixes it.

> **Edited 2026-08-09, after experiment 3.** This read "settle a 60-year epistemology dispute by observing which architecture behaves sensibly under stress," which overstates what any single architecture can settle. Manyu's mandatory-provenance rule means no belief rests entirely on another, so total collapse is unrepresentable and the foundationalist limb was never available to observe — a graded ripple is therefore not evidence for Quine. The sharper claim the experiment does support: a belief holding evidence of its own bends, one resting purely on another falls with it, and the substrate decides which case you are in. See [retrospective §1](experiments/03-foundationalism-quinean-web/retrospective.md).

### 4. What does contradiction feel like?
When Manyu finds a genuine inconsistency in its own web, does the (merged) emotive core produce a measurable salience/discomfort signal that drives resolution? A mechanical model of cognitive dissonance you can watch fire — dissonance as a real control signal, not a metaphor.

### 5. Represent underdetermination as a first-class belief *(standout — plugs into the cosmology work)*
Point Manyu at an underdetermined domain — the cosmology case, where time-dependent and location-dependent explanations are observationally equivalent on a single light cone — and **forbid it from picking one**. Force it to hold "these theories are indistinguishable given my evidence" as an explicit, stable belief state rather than collapsing to a guess. An agent that can *represent the shape of its own ignorance* is philosophically rare and genuinely useful.

### 6. A "what would change my mind" engine with receipts
Give Manyu a position; have it genuinely revise toward the strongest opposing view, logging exactly what evidence would move it and by how much. A steelman machine whose commitments are auditable.

### 7. Epistemic archaeology
Point it at the history of an idea — scientific or theological — and have it reconstruct the provenance graph of how the idea descended and mutated across sources. Intellectual genealogy made mechanical.

### 8. A society of Manyus
Multiple agents propagating source-weighted beliefs: a buildable model of how knowledge and error spread — echo chambers, consensus, and the collapse of a shared baseline. Peer disagreement (two Manyus, contradictory well-sourced beliefs, no resolution) becomes a protocol-design problem, not an armchair puzzle.

### 9. The rebirth experiment *(standout — fuses with Twice Born)*
Run a single Manyu long enough that most of its belief-and-value web turns over. Find the ship-of-Theseus threshold where it's arguably a different agent, and have it **narrate its own transformation**: "I believed X on this testimony; then this happened; I am no longer the agent that held it." Simultaneously a phenomenological probe of narrative identity (Minsky, Dennett, Ricoeur) and a piece of writing. Given *Twice Born* is about death and rebirth on Dronagiri, this is the actual bridge between the architecture and the fiction — and something nobody else is positioned to make.

---

## Priority read

- **Best first experiment:** #1 (introspective honesty) — small, concrete, produces a clean surprising result you could write up immediately.
- **Highest depth × distinctiveness:** #5 (underdetermination explorer) and #9 (rebirth/identity narrator) — where Manyu's capabilities and your own work (cosmology; *Twice Born*) stop being separate projects.

## The through-line

Manyu isn't trying to pass a test — it's an apparatus for making the deck's *open* problems into *buildable* ones. The lever is always the same: **ground truth about the machine's reasons**, checked from the inside against the outside.
