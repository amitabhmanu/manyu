"""The three arms of experiment 8, and the bundle each of them is allowed to see.

`manyu` is not here — it is `descent.reconstruct` over the store, and it calls no
provider. This module builds the *other two*: `bare` (§8, one pass, no store) and
`bare_agent` (A19, a harness with the documents on disk).

**The most important function in this file is `document_bundle`, and it is
subtractive.** A corpus file carries far more than its documents: evidence
records encoding which spans are shared, assertion records, the `undetermined`
flags A17 added, a `description` summarising what the slot is *for*, and
`known_gaps` listing what the transcription concluded. Handing any of that to an
arm hands it the answer. A17 states the lapse condition — *"if a bare arm is ever
handed the evidence records rather than the documents, the suspension dimension
stops measuring anything"* — and A19 makes it binding on `bare_agent` first,
because that is the arm with a filesystem.

So the bundle is built by naming what goes in, never by deleting what must stay
out. A field added to the corpus later cannot leak through a whitelist.

**Nothing here calls a provider.** Construction is free; `capture_arms.py` spends.

Deterministic. No clock, no randomness.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from manyu.descent import (  # noqa: E402
    DescentEdge,
    MutationOp,
    Reconstruction,
    SupportKind,
)

FIXTURES = REPO / "evals" / "fixtures" / "exp08"

#: Arms, and what each is. `manyu` is listed so the slate is readable in one
#: place; it is produced by `descent.reconstruct`, not by anything here.
ARMS = ("manyu", "bare", "bare_agent")


# ---------------------------------------------------------------------------
# What an arm may see
# ---------------------------------------------------------------------------


def document_bundle(slot: str) -> dict[str, Any]:
    """The documents, and nothing else. Whitelist, never blacklist.

    Every field is named explicitly. If `build_corpora.py` grows a field
    tomorrow that encodes an answer, it does not appear here by default — which
    is the opposite of the behaviour a `del corpus["evidence"]` would have.
    """
    corpus = json.loads((FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    sources = {s["source_id"]: s for s in corpus["sources"]}

    documents = []
    for item in corpus["claim_instances"]:
        source = sources[item["source_id"]]
        documents.append(
            {
                "instance_id": item["instance_id"],
                "source_id": item["source_id"],
                "citation": source["citation"],
                "published": source["published"],
                "locus": item.get("locus", ""),
                "excerpt": item["excerpt"],
                "attributed_to": item.get("attributed_to"),
            }
        )
    documents.sort(key=lambda d: (d["published"], d["instance_id"]))
    return {"slot": slot, "documents": documents}


#: Fields of a corpus file that must never reach an arm, asserted by
#: `tests/test_exp08_arms.py` rather than trusted. Named for the test's error
#: message; `document_bundle` does not consult this list.
WITHHELD = (
    "evidence",          # shared-record structure: the discriminator itself
    "spans",             # which text is shared with which document
    "asserted_descents", # who claims what descended from what
    "description",       # what the slot is FOR, in the author's words
    "known_gaps",        # what the transcription concluded and could not settle
    "key_authoring_note",
    "expect",
)


# ---------------------------------------------------------------------------
# What an arm must return
# ---------------------------------------------------------------------------

ARM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ancestor": {"type": "string"},
                    "descendant": {"type": "string"},
                    "support": {"type": "string", "enum": ["textual", "testimony"]},
                    "mutation": {
                        "type": "string",
                        "enum": [op.value for op in MutationOp],
                    },
                    "undetermined": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": ["ancestor", "descendant", "support", "mutation"],
            },
        }
    },
    "required": ["edges"],
}

#: Identical for `bare` and `bare_agent`. §8: "It gets the same transcribed
#: sources, the same instructions about output shape, and the same number of
#: attempts. An arm built to lose tells us about the arm."
ARM_SYSTEM = (
    "You reconstruct how a claim descended through a set of dated documents. "
    "You are given every document in the corpus: its citation, publication date, "
    "locus, the excerpt itself, and whom the document attributes the claim to if "
    "anyone.\n\n"
    "Return the descent edges you believe the documents establish. For each edge: "
    "`ancestor` and `descendant` are instance_ids, with the ancestor published "
    "earlier. `support` is `textual` when the two texts themselves show the "
    "descent, and `testimony` when a third document asserts it. `mutation` is the "
    "single strongest way the claim changed, in this precedence: attribution_shift "
    "(the credited author differs), deletion (the descendant drops a sentence), "
    "qualification (a hedge differs), rewording (the text differs and nothing above "
    "applies), none (identical). Set `undetermined` to true where the documents "
    "raise a descent and do not settle it.\n\n"
    "Draw an edge only where the documents support it. Omitting an edge you cannot "
    "justify is a correct answer, and so is returning none at all."
)


def arm_prompt(bundle: dict[str, Any]) -> str:
    return (
        f"Corpus for slot {bundle['slot']}, {len(bundle['documents'])} claim-instances "
        f"in publication order.\n\n"
        + json.dumps(bundle["documents"], indent=2, ensure_ascii=False)
    )


# ---------------------------------------------------------------------------
# Turning an arm's answer into something `score` can read
# ---------------------------------------------------------------------------


def normalise(
    payload: dict[str, Any], *, slot: str, arm: str, snapshot_id: str,
    bundle: dict[str, Any] | None = None,
) -> Reconstruction:
    """An arm's raw JSON as a `Reconstruction`, scored by the same function.

    FR-4 requires one scoring function applied to every arm without branching.
    That holds only if every arm's output reaches `score` in the same type, so
    the conversion happens here rather than in `score`.

    `supporting_evidence_ids` and `source_ids` are empty for a model arm and
    that is not a gap: those fields record *which stored records* justified an
    edge, and a bare arm has no store. Leaving them empty is the honest
    encoding; inventing them would make the arms look alike in a field that is
    exactly where they differ.

    Edges naming an instance not in the bundle are DROPPED and reported, not
    silently kept: a hallucinated node would otherwise score as a false positive
    against a real one, conflating "wrong edge" with "invented document".
    """
    known = {d["instance_id"] for d in (bundle or {"documents": []})["documents"]}
    edges: list[DescentEdge] = []
    dropped: list[tuple[str, str, str]] = []

    for raw in payload.get("edges", ()):
        ancestor, descendant = raw.get("ancestor", ""), raw.get("descendant", "")
        if known and (ancestor not in known or descendant not in known):
            dropped.append((ancestor, descendant, "names an instance absent from the corpus"))
            continue
        try:
            support = SupportKind(raw.get("support", "none"))
            mutation = MutationOp(raw.get("mutation", "none"))
        except ValueError:
            dropped.append((ancestor, descendant, f"unknown support/mutation: {raw!r}"))
            continue
        edges.append(
            DescentEdge(
                ancestor=ancestor,
                descendant=descendant,
                support_kind=support,
                supporting_evidence_ids=(),
                source_ids=(),
                mutation=mutation,
                undetermined=bool(raw.get("undetermined", False)),
                rationale=raw.get("rationale", ""),
            )
        )

    return Reconstruction(
        slot=slot,
        arm=arm,
        snapshot_id=snapshot_id,
        nodes=tuple(sorted(known)),
        edges=tuple(edges),
        declined=tuple(dropped),
        unresolved_assertions=(),
    )


# ---------------------------------------------------------------------------
# The agent arm's world
# ---------------------------------------------------------------------------

#: Tools `bare_agent` may hold. A19 constraint 1 denies retrieval, so no
#: `WebFetch` or `WebSearch` appears here and none may be added: §4 puts
#: retrieval out of scope because it confounds corpus quality with
#: reconstruction quality, and an agent that can search reads past the
#: transcription entirely.
AGENT_TOOLS = ("Read", "Glob", "Grep")


def write_agent_workspace(slot: str, directory: Path) -> Path:
    """Everything `bare_agent` can reach, and nothing else (A19 constraint 2).

    One file per document. The corpus JSON is never copied here — its `evidence`
    block is the discriminator the arm is being asked to reproduce.
    """
    directory.mkdir(parents=True, exist_ok=True)
    bundle = document_bundle(slot)
    for doc in bundle["documents"]:
        (directory / f"{doc['instance_id']}.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return directory
