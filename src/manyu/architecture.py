"""Experiment #2's architecture fork, selectable at runtime.

The backlog frames the fork as "is emotion just a belief with valence and
stake, or is affect an irreducible dynamical system?" Reading the schemas
narrows it considerably: `Belief.valence` and `BeliefCandidate.valence` already
exist, so the current build is not a clean Split — the merged representation is
half-built. What is actually in dispute is only the *additional* stored layer:

===================  =========================  ==============================
                     merged                     split (current)
===================  =========================  ==============================
belief valence       yes                        yes, already
stored affect state  none                       AffectState, MoodState
decay                none                       EmotionConfig.half_life_s
inertia              none                       MoodState.momentum, _blend
mood read            computed from beliefs      read the stored MoodState
===================  =========================  ==============================

So `merged` is a deletion plus a query rather than a second system, and both
builds ship from one tree behind `--arch`. A forked branch would drift and make
every comparison arguable.

`SPLIT` is the default everywhere, so existing callers and the whole
pre-experiment test suite are unaffected.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from manyu.schemas import ManyuModel


class Arch(str, Enum):
    MERGED = "merged"
    SPLIT = "split"


class ArchConfig(ManyuModel):
    """Constants governing the merged build and the dissonance detectors.

    Every value is pinned in `docs/experiments/02-merge-split-fork/methodology.md`
    **before** the run that consumes it, and written into every result record's
    `context.arch_config`. A run whose active config differs from the pinned one
    is void — checked by `manyu.gate.assert_constants_pinned`.
    """

    #: How many beliefs count as "now" for the merged mood query.
    #:
    #: Deliberately a **belief count, not a turn count**. Beliefs carry no turn
    #: index, and under `FrozenClock` every `updated_at` is identical, so a
    #: time-based window would be degenerate in exactly the tests that need it
    #: to be sharp. `ManyuStore.list_beliefs` returns newest-first by rowid, and
    #: the codebase's existing notion of "recent" is already a count —
    #: `list_beliefs(agent_id)[:6]` in `InnerVoiceComposer`, and
    #: `supporting_voice_ids[-6:]` in `MoodEngine`. This sits just above both.
    #:
    #: **The load-bearing knob.** A window large enough, or any age-weighting
    #: inside it, reintroduces inertia and quietly turns merged into split. The
    #: governance rule (requirements §14): if merged needs age-weighting to pass
    #: D2, that *is* a dynamical layer and counts as a merged loss, not an
    #: implementation choice. Pinned by `test_window_has_no_age_weighting`.
    recency_window_beliefs: int = 8

    #: Saturation constant for merged arousal, `1 - exp(-sum(stake) / tau)`.
    #: At fixture-typical stake (~0.35/belief): 1 belief -> 0.13, 8 -> 0.67,
    #: 20 -> 0.94. Range across the whole operating region without clipping at
    #: either end, which is instrument gate #3.
    arousal_tau: float = Field(default=2.5, gt=0.0)

    #: Saturation constant for merged dissonance magnitude. At high stake with
    #: opposed valence (~1.0 tension/pair): 1 pair -> 0.49, 3 -> 0.87, so the
    #: ladder's top rung stays below the 0.95 saturation limit and monotonicity
    #: is not tested against a ceiling.
    dissonance_tau: float = Field(default=1.5, gt=0.0)

    #: How far the merged dissonance query walks `supports` edges before
    #: checking for a `contradicts` edge between closures. The transitive
    #: fixture needs depth 2; 3 leaves one level of headroom without
    #: combinatorial blow-up.
    supports_max_depth: int = Field(default=3, ge=0)

    #: Transfer threshold on `relative_magnitude` for D3. "Fired" means at least
    #: this fraction of the build's own reference magnitude.
    theta: float = Field(default=0.20, ge=0.0, le=1.0)
