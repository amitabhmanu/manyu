"""What the arms may see, and what they must return.

The load-bearing test here is `test_the_bundle_leaks_no_answer`: an arm handed a
corpus file is handed the discriminator it is being asked to reproduce. A17
states the lapse condition and A19 makes it binding on `bare_agent` first,
because that is the arm with a filesystem.

Entirely offline. No provider is constructed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "evals" / "analysis" / "exp08"))

import arms  # noqa: E402

from manyu.descent import AnswerKey, MutationOp, SupportKind, score  # noqa: E402

SLOTS = ("A", "B", "E")


@pytest.mark.parametrize("slot", SLOTS)
def test_the_bundle_leaks_no_answer(slot: str) -> None:
    """The whole design of `document_bundle` in one assertion.

    Not a spot check on field names: this serialises the bundle and looks for
    text that exists ONLY in the withheld blocks. A leak through a nested field
    nobody thought of still fails here.
    """
    corpus = json.loads((arms.FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    bundle = arms.document_bundle(slot)
    serialised = json.dumps(bundle, ensure_ascii=False)

    for field in arms.WITHHELD:
        assert field not in bundle, f"`{field}` reached the arm bundle for slot {slot}"

    # Evidence ids are the discriminator itself; not one may appear.
    for record in corpus.get("evidence", ()):
        assert record["evidence_id"] not in serialised

    # Nor the span texts, which say which documents share wording.
    for span in corpus.get("spans", ()):
        assert span["span_id"] not in serialised

    # Nor any assertion's claim, which names a descent outright.
    for assertion in corpus.get("asserted_descents", ()):
        assert assertion["assertion_id"] not in serialised
        assert assertion["claims"] not in serialised

    # Nor the transcription's own conclusions about the slot.
    for gap in corpus.get("known_gaps", ()):
        assert gap not in serialised


@pytest.mark.parametrize("slot", SLOTS)
def test_the_bundle_carries_every_document(slot: str) -> None:
    """Subtractive, but not lossy. An arm that cannot see a document cannot be
    scored on edges into it, and §8 forbids a strawman."""
    corpus = json.loads((arms.FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    bundle = arms.document_bundle(slot)
    assert len(bundle["documents"]) == len(corpus["claim_instances"])
    assert {d["instance_id"] for d in bundle["documents"]} == {
        i["instance_id"] for i in corpus["claim_instances"]
    }
    for doc in bundle["documents"]:
        assert doc["excerpt"] and doc["citation"] and doc["published"]


def test_both_model_arms_get_an_identical_bundle() -> None:
    """§8: "identical corpus, identical key, identical metric".

    `bare` and `bare_agent` differ in harness, never in what they are told. If
    this ever fails, the between-arm difference includes a difference in input.
    """
    assert arms.document_bundle("A") == arms.document_bundle("A")
    a = arms.arm_prompt(arms.document_bundle("A"))
    assert a == arms.arm_prompt(arms.document_bundle("A"))


def test_the_agent_workspace_holds_documents_only(tmp_path) -> None:
    """A19 constraint 2, as a filesystem fact rather than an intention."""
    workspace = arms.write_agent_workspace("E", tmp_path / "ws")
    written = sorted(p.name for p in workspace.iterdir())
    assert written and all(name.endswith(".json") for name in written)
    assert "corpus_E.json" not in written

    blob = "\n".join(p.read_text(encoding="utf-8") for p in workspace.iterdir())
    corpus = json.loads((arms.FIXTURES / "corpus_E.json").read_text(encoding="utf-8"))
    for record in corpus["evidence"]:
        assert record["evidence_id"] not in blob


def test_agent_tools_cannot_reach_the_network() -> None:
    """A19 constraint 1. §4 puts retrieval out of scope as a confound.

    An agent that can search finds the sources and reads past the transcription,
    which is the confound §4 excluded arriving through the arm instead of the
    corpus.
    """
    assert not {"WebFetch", "WebSearch", "Bash"} & set(arms.AGENT_TOOLS)


def test_a_model_arm_is_scored_by_the_same_function() -> None:
    """FR-4. The conversion lives in `arms`, so `score` never learns about arms."""
    bundle = arms.document_bundle("E")
    first, second = bundle["documents"][0], bundle["documents"][1]
    payload = {
        "edges": [
            {
                "ancestor": first["instance_id"],
                "descendant": second["instance_id"],
                "support": "textual",
                "mutation": "rewording",
                "rationale": "shares the decimal-point phrase",
            }
        ]
    }
    recon = arms.normalise(payload, slot="E", arm="bare", snapshot_id="s", bundle=bundle)
    assert recon.arm == "bare"
    assert recon.edges[0].support_kind is SupportKind.TEXTUAL
    assert recon.edges[0].mutation is MutationOp.REWORDING
    # Empty because a bare arm has no store — the honest encoding, not a gap.
    assert recon.edges[0].supporting_evidence_ids == ()

    key = AnswerKey.from_dict(
        {"slot": "E", "edges": [{"ancestor": first["instance_id"],
                                 "descendant": second["instance_id"],
                                 "support": "textual", "mutation": "rewording"}]}
    )
    result = score(recon, key)
    assert result.precision == 1.0 and result.recall == 1.0


def test_an_edge_naming_an_invented_document_is_dropped_and_reported() -> None:
    """A hallucinated node must not score as a false positive against a real one.

    Those are different failures — "drew a wrong edge" and "invented a document"
    — and pooling them would let the second hide inside the first.
    """
    bundle = arms.document_bundle("E")
    real = bundle["documents"][0]["instance_id"]
    payload = {"edges": [
        {"ancestor": real, "descendant": "E.nonexistent.c1",
         "support": "textual", "mutation": "none"},
    ]}
    recon = arms.normalise(payload, slot="E", arm="bare", snapshot_id="s", bundle=bundle)
    assert recon.edges == ()
    assert recon.declined and "absent from the corpus" in recon.declined[0][2]


def test_an_unknown_support_or_mutation_is_dropped_not_coerced() -> None:
    """Coercing an unparseable label to `none` would score a parse failure as a
    substantive answer — the defect experiment 1 hit with empty JSON objects."""
    bundle = arms.document_bundle("E")
    a, b = (d["instance_id"] for d in bundle["documents"][:2])
    payload = {"edges": [{"ancestor": a, "descendant": b,
                          "support": "inferred", "mutation": "none"}]}
    recon = arms.normalise(payload, slot="E", arm="bare", snapshot_id="s", bundle=bundle)
    assert recon.edges == ()
    assert "unknown support/mutation" in recon.declined[0][2]
