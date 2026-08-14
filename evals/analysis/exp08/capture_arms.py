"""Capture `bare` and `bare_agent` output to JSON. **The only file here that spends.**

Split from scoring on the house pattern (`exp07/run_stages.py`: *"Entirely
offline. No provider call, no spend."*). This script calls a provider and writes
raw arm output; `run_stages.py` reads those files and is deterministic. That
separation is what lets a re-score happen without re-spending, and what lets
FR-4's "scored by the same function" be checked rather than intended.

**Dry by default.** Without `--live` nothing is sent: the bundle and prompt are
built, the withheld-field check runs, and the invocation is printed. A capture
script whose default costs money is one that costs money by accident.

    python evals/analysis/exp08/capture_arms.py --slot E --arm bare
    python evals/analysis/exp08/capture_arms.py --slot E --arm bare --live

**Before any live run, read `freeze.json` and the pre-registration.** A19
constraint 3: the harness configuration is part of the experimental condition.
Everything this script can see about it is written into the artifact.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arms  # noqa: E402

from manyu.descent import (  # noqa: E402
    verify_freeze,
    verify_mechanism_freeze,
    verify_pre_registration_freeze,
)

OUT = Path(__file__).resolve().parent / "arm_captures"

#: Pinned, as the house pins it (`exp03/run_stage4.py`: MODEL = "claude-opus-5").
BARE_MODEL = "claude-opus-5"


def _guard() -> None:
    """Every freeze block, raising, before a single token is spent.

    `mechanisms` and `pre_registration` were documentation until 2026-08-14;
    this is the caller their docstrings name.
    """
    verify_freeze()
    verify_mechanism_freeze()
    verify_pre_registration_freeze()


def _provider(arm: str, workspace: Path | None) -> Any:
    if arm == "bare":
        from manyu.providers import AnthropicAPIJSONProvider

        return AnthropicAPIJSONProvider(model=BARE_MODEL, max_tokens=8192)

    from manyu.providers import ClaudeCodeJSONProvider

    # A19 constraints 1 and 2: no retrieval tool, and the only readable
    # directory holds documents.
    return ClaudeCodeJSONProvider(
        cwd=workspace, allowed_tools=list(arms.AGENT_TOOLS), model=BARE_MODEL
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slot", required=True, choices=["A", "B", "D", "E"])
    parser.add_argument("--arm", required=True, choices=["bare", "bare_agent"])
    parser.add_argument("--live", action="store_true", help="actually call a provider — SPENDS")
    args = parser.parse_args()

    bundle = arms.document_bundle(args.slot)
    prompt = arms.arm_prompt(bundle)

    # The leak check runs on every invocation, live or dry. It is cheap and it
    # is the one failure that cannot be noticed by reading the output.
    for field in arms.WITHHELD:
        if field in bundle:
            raise SystemExit(f"REFUSING: `{field}` is in the arm bundle (A17, A19)")

    workspace = None
    if args.arm == "bare_agent":
        workspace = arms.write_agent_workspace(args.slot, OUT / f"workspace_{args.slot}")

    print(f"slot {args.slot} · arm {args.arm} · {len(bundle['documents'])} documents")
    print(f"  withheld and verified absent: {', '.join(arms.WITHHELD)}")
    if workspace:
        print(f"  workspace: {workspace}  tools={list(arms.AGENT_TOOLS)}")
    print(f"  prompt characters: {len(prompt)}")

    if not args.live:
        print("\nDRY RUN — nothing sent. Re-run with --live to spend.")
        return 0

    _guard()
    provider = _provider(args.arm, workspace)
    payload = provider.generate_json(
        prompt, arms.ARM_SCHEMA, system_message=arms.ARM_SYSTEM, temperature=0.0
    )

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{args.arm}_{args.slot}.json"
    path.write_text(
        json.dumps(
            {
                "slot": args.slot,
                "arm": args.arm,
                # A19 constraint 3: the harness IS the condition. What this
                # script can see of it goes in the artifact; what it cannot see
                # — Claude Code's own system prompt, which the provider's
                # docstring records as uncontrolled and version-dependent — is
                # named here as absent rather than left implicit.
                "model": BARE_MODEL,
                "tools": list(arms.AGENT_TOOLS) if args.arm == "bare_agent" else [],
                "harness_system_prompt_captured": args.arm != "bare_agent",
                "document_count": len(bundle["documents"]),
                "payload": payload,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
