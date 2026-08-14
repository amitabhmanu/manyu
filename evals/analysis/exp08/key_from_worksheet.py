"""Convert a filled key worksheet to `key_<slot>.json`, and validate it.

Mechanical transcription only. This script makes no judgement about any edge; it
reads the table the author filled in, checks it for the mistakes that are
checkable without opening a document, and writes JSON. That is what keeps FR-2
true through the whole pipeline rather than only at the worksheet.

What it CANNOT check, and nobody should read a clean run as evidence of: whether
an edge is real, whether the direction is right, or whether the mutation is the
one the documents show.

Usage:  python evals/analysis/exp08/key_from_worksheet.py A [--write]

Deterministic. No clock, no randomness, no provider.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "evals" / "fixtures" / "exp08"
WORKSHEETS = REPO / "docs" / "experiments" / "08-epistemic-archaeology" / "key-worksheets"

SUPPORT = {"textual", "testimony"}
# Precedence order matters: the index is used to report a suspicious pairing.
OPERATORS = ["attribution_shift", "deletion", "qualification", "rewording", "none"]
ROW = re.compile(r"^\|\s*(\d+)\s*\|(.+)\|\s*$")


def _cell(text: str) -> str:
    return text.strip().strip("`").strip()


def parse(slot: str) -> tuple[list[dict], list[str]]:
    path = WORKSHEETS / f"key_worksheet_{slot}.md"
    if not path.exists():
        raise SystemExit(f"no worksheet at {path}")
    corpus = json.loads((FIXTURES / f"corpus_{slot}.json").read_text(encoding="utf-8"))
    known = {i["instance_id"] for i in corpus["claim_instances"]}
    sources = {s["source_id"]: s["published"] for s in corpus["sources"]}
    pub = {
        i["instance_id"]: sources[i["source_id"]] for i in corpus["claim_instances"]
    }

    edges: list[dict] = []
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    blank = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        cells = [_cell(c) for c in m.group(2).split("|")]
        if len(cells) < 7:
            problems.append(f"row {m.group(1)}: expected 7 columns, found {len(cells)}")
            continue
        anc, desc, is_edge, support, mutation, undet, why = cells[:7]
        n = m.group(1)

        for iid in (anc, desc):
            if iid not in known:
                problems.append(f"row {n}: `{iid}` is not a claim-instance in corpus_{slot}")

        if is_edge.lower() not in {"y", "n", ""}:
            problems.append(f"row {n}: edge? is {is_edge!r}, expected y or n")
        if is_edge.lower() != "y":
            if not is_edge:
                blank += 1
            continue

        if (anc, desc) in seen:
            problems.append(f"row {n}: duplicate pair {anc} -> {desc}")
        seen.add((anc, desc))

        if anc in pub and desc in pub and pub[anc] > pub[desc]:
            problems.append(
                f"row {n}: DIRECTION — `{anc}` ({pub[anc]}) is later than `{desc}` "
                f"({pub[desc]}). Ancestor must not postdate descendant."
            )
        if support not in SUPPORT:
            problems.append(f"row {n}: support is {support!r}, expected one of {sorted(SUPPORT)}")
        ops = [o for o in OPERATORS if o in mutation.lower()]
        if len(ops) > 1:
            problems.append(
                f"row {n}: {len(ops)} mutation operators ({', '.join(ops)}). A13 requires "
                f"exactly one — the highest precedence, here `{ops[0]}`."
            )
        elif not ops:
            problems.append(f"row {n}: mutation is {mutation!r}, expected one of {OPERATORS}")
        if undet.lower() not in {"y", "n", ""}:
            problems.append(f"row {n}: undet is {undet!r}, expected y or blank")
        if not why:
            problems.append(f"row {n}: no `why`. Every asserted edge needs its reason recorded.")

        entry = {
            "ancestor": anc, "descendant": desc,
            "support": support or "textual",
            "mutation": ops[0] if ops else "none",
            "why": why,
        }
        if undet.lower() == "y":
            entry["undetermined"] = True
        edges.append(entry)

    if blank:
        problems.append(f"{blank} row(s) have an empty `edge?` cell — undecided, not decided `n`.")
    return edges, problems


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    slot = sys.argv[1].upper()
    edges, problems = parse(slot)

    print(f"slot {slot}: {len(edges)} edge(s) asserted")
    testimony = sum(1 for e in edges if e["support"] == "testimony")
    undet = sum(1 for e in edges if e.get("undetermined"))
    print(f"  textual={len(edges) - testimony}  testimony={testimony}  undetermined={undet}")
    for op in OPERATORS:
        c = sum(1 for e in edges if e["mutation"] == op)
        if c:
            print(f"  {op}: {c}")

    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        print("\nNot written. Fix the worksheet and re-run.")
        return 1

    key = {
        "fixture_id": f"key_{slot}", "role": "answer_key", "slot": slot,
        "authored_by": (
            "HAND-AUTHORED from the documents by the experimenter (FR-2). Transcribed to "
            f"JSON by key_from_worksheet.py from key_worksheet_{slot}.md, which makes no "
            "judgement about any edge. No model chose an edge, a direction or a mutation."
        ),
        "edges": edges,
    }
    print("\nOK — no checkable problems.")
    if "--write" in sys.argv:
        path = FIXTURES / f"key_{slot}.json"
        path.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    else:
        print("Dry run. Pass --write to emit the key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
