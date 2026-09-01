#!/usr/bin/env python3
"""Fail closed unless a finalized Bradbury decision proves an ACCEPT release."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.release_gate_verifier import (  # noqa: E402
    GateExpectation,
    ReleaseGateVerificationError,
    verify_finalized_decision,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a finalized ReleaseProof ACCEPT decision without a private key."
    )
    parser.add_argument("policy_id")
    parser.add_argument("request_id")
    parser.add_argument("commit_sha")
    parser.add_argument("source_url")
    parser.add_argument("release_notes_url")
    parser.add_argument("repo_owner")
    parser.add_argument("repo_name")
    parser.add_argument("--policy-version", type=int, default=1)
    parser.add_argument("--required-marker")
    parser.add_argument("--release-note-rule")
    parser.add_argument(
        "--contract",
        default=os.environ.get("RELEASE_PROOF_ADDRESS", ""),
        help="Bradbury contract address, or RELEASE_PROOF_ADDRESS",
    )
    parser.add_argument("--tx-hash", help="Require this transaction to be FINALIZED")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_finalized_decision(
            GateExpectation(
                contract_address=args.contract,
                policy_id=args.policy_id,
                request_id=args.request_id,
                commit_sha=args.commit_sha,
                source_url=args.source_url,
                release_notes_url=args.release_notes_url,
                repo_owner=args.repo_owner,
                repo_name=args.repo_name,
                policy_version=args.policy_version,
                required_marker=args.required_marker,
                release_note_rule=args.release_note_rule,
                transaction_hash=args.tx_hash,
            )
        )
    except (ReleaseGateVerificationError, ValueError) as error:
        print(f"ReleaseProof verification failed: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # pragma: no cover - network/provider failures
        print(f"ReleaseProof verification unavailable: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
