"""Emit a blank key-authoring worksheet per slot, from the corpus alone.

**This script must never import `descent.reconstruct`.** A key exists to be an
independent reading of the documents; if it is authored from the mechanism's
output then `precision` and `recall` measure agreement with the thing being
tested and mean nothing. So the worksheets carry the corpus -- excerpts, dates,
attributions, spans, assertions -- and no verdict of any kind.

The author fills the decision columns by reading the excerpts. `key_from_worksheet.py`
converts the filled table to JSON mechanically, so no judgement enters at that step
either (FR-2).

Deterministic. No clock, no randomness, no provider.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "evals" / "fixtures" / "exp08"
OUT = REPO / "docs" / "experiments" / "08-epistemic-archaeology" / "key-worksheets"

LADDER = """1. `attribution_shift` — `attributed_to` differs
2. `deletion` — the descendant's sentences are a proper subset of the ancestor's
3. `qualification` — the hedge set differs
4. `rewording` — the excerpts differ and nothing above applies
5. `none` — identical modulo whitespace and case"""


def _esc(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def worksheet(slot: str) -> str:
    d = json.loads((FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    sources = {s["source_id"]: s for s in d["sources"]}
    inst = d["claim_instances"]
    published = {i["instance_id"]: sources[i["source_id"]]["published"] for i in inst}
    by_id = {i["instance_id"]: i for i in inst}
    order = sorted(inst, key=lambda i: (published[i["instance_id"]], i["instance_id"]))

    L: list[str] = []
    L.append(f"# Key worksheet — slot {slot}")
    L.append("")
    L.append("**Authored by hand, from the documents (FR-2).** This worksheet deliberately does")
    L.append("not tell you what the mechanism drew. If the key agrees with the mechanism because")
    L.append("it was copied from it, precision and recall measure nothing.")
    L.append("")
    L.append(f"Corpus status: **{d.get('status', 'GENERATED')}**")
    L.append("")

    L.append("## 1. The documents")
    L.append("")
    L.append("| source_id | published | citation |")
    L.append("|---|---|---|")
    for sid, s in sorted(sources.items(), key=lambda kv: kv[1]["published"]):
        L.append(f"| `{sid}` | {s['published']} | {_esc(s['citation'])} |")
    L.append("")

    L.append("## 2. The claim-instances, oldest first")
    L.append("")
    L.append("Direction comes from these dates and nothing else.")
    L.append("")
    for i in order:
        iid = i["instance_id"]
        L.append(f"### `{iid}`")
        L.append("")
        L.append(f"- **published** {published[iid]} · **locus** {i.get('locus', '')}")
        attr = i.get("attributed_to")
        L.append(f"- **attributed_to** {'`' + attr + '`' if attr else '*(none)*'}")
        if i.get("attribution_note"):
            L.append(f"- **note** {_esc(i['attribution_note'])}")
        L.append("")
        L.append(f"> {i['excerpt']}")
        L.append("")

    spans = d.get("spans") or []
    if spans:
        L.append("## 3. Spans as transcribed")
        L.append("")
        L.append("Your own transcription, repeated here so you need not open the corpus file.")
        L.append("A shared span is evidence, not a verdict — you decide whether it means descent.")
        L.append("")
        L.append("| span | appears in | text |")
        L.append("|---|---|---|")
        for s in spans:
            docs = ", ".join(f"`{x}`" for x in s["appears_in"])
            L.append(f"| `{s['span_id']}` | {docs} | {_esc(s['text'])[:90]} |")
        L.append("")

    asserts = d.get("asserted_descents") or []
    if asserts:
        L.append("## 4. Asserted descents")
        L.append("")
        L.append("A **third** document asserting a descent is what makes an edge `testimony`")
        L.append("rather than `textual`. An assertion by one of the endpoints is not testimony.")
        L.append("")
        for a in asserts:
            L.append(f"- **`{a['assertion_id']}`** — asserted by `{a['asserted_by']}`  ")
            L.append(f"  claims: {_esc(a['claims'])}")
        L.append("")

    L.append("## 5. Decisions")
    L.append("")
    L.append("One row per ordered pair, older → newer. Same-document pairs are listed but need")
    L.append("no decision: two loci of one document are siblings, never ancestor and descendant.")
    L.append("")
    L.append("`edge?` — `y` / `n`. `support` — `textual` / `testimony`. `undet` — `y` if the")
    L.append("sources raise this descent and decline to settle it. `mutation` — **one** operator,")
    L.append("highest precedence only:")
    L.append("")
    L.append(LADDER)
    L.append("")
    L.append("| # | ancestor | descendant | edge? | support | mutation | undet | why (quote the documents) |")
    L.append("|---|---|---|---|---|---|---|---|")

    n = 0
    skipped: list[str] = []
    for a, b in combinations(order, 2):
        ia, ib = a["instance_id"], b["instance_id"]
        if a["source_id"] == b["source_id"]:
            skipped.append(f"`{ia}` / `{ib}` — both in `{a['source_id']}`")
            continue
        n += 1
        L.append(f"| {n} | `{ia}` | `{ib}` |  |  |  |  |  |")
    L.append("")
    L.append(f"**{n} decisions.**")
    L.append("")
    if skipped:
        L.append(f"Not decidable ({len(skipped)} same-document pairs):")
        L.append("")
        for s in skipped:
            L.append(f"- {s}")
        L.append("")

    L.append("## 6. Before you call it done")
    L.append("")
    L.append("- [ ] Every `y` row has a `why` that quotes or cites the documents.")
    L.append("- [ ] No row has two mutation operators.")
    L.append("- [ ] `testimony` only where a document that is **neither endpoint** asserts it.")
    L.append("- [ ] Direction checked against the dates in §1, not against plausibility.")
    L.append("- [ ] You have not looked at any reconstruction output.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for slot in ("A", "B", "E"):
        path = OUT / f"key_worksheet_{slot}.md"
        path.write_text(worksheet(slot), encoding="utf-8")
        rows = worksheet(slot).count("\n|  |  |  |  |  |")
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
