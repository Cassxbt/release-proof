#!/usr/bin/env python3
"""Operate a deployed ReleaseProof contract on GenLayer Bradbury."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.release_proof_client import operator_from_environment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create policies, evaluate releases, and read decisions on Bradbury."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create_policy = commands.add_parser("create-policy")
    create_policy.add_argument("policy_id")
    create_policy.add_argument("repo_owner")
    create_policy.add_argument("repo_name")
    create_policy.add_argument("required_marker")
    create_policy.add_argument("release_note_rule")

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("policy_id")
    evaluate.add_argument("request_id")
    evaluate.add_argument("commit_sha")
    evaluate.add_argument("source_url")
    evaluate.add_argument("release_notes_url")

    get_decision = commands.add_parser("get-decision")
    get_decision.add_argument("policy_id")
    get_decision.add_argument("request_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        operator = operator_from_environment()
        if args.command == "create-policy":
            result = operator.create_policy(
                args.policy_id,
                args.repo_owner,
                args.repo_name,
                args.required_marker,
                args.release_note_rule,
            )
            payload = result.as_dict()
        elif args.command == "evaluate":
            result = operator.evaluate_release(
                args.policy_id,
                args.request_id,
                args.commit_sha,
                args.source_url,
                args.release_notes_url,
            )
            payload = result.as_dict()
        else:
            payload = operator.get_decision(args.policy_id, args.request_id)
    except (RuntimeError, ValueError) as error:
        print(f"ReleaseProof error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
