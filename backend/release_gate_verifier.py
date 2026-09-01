"""Read-only verification for a finalized ReleaseProof decision.

This module deliberately creates an in-memory account because the current
GenLayer Python SDK requires a sender address for ``gen_call``. The account is
never persisted, used to sign, or printed. No private key is needed to verify
a decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from eth_account import Account
from genlayer_py.chains import testnet_bradbury
from genlayer_py.client import GenLayerClient
from web3 import Web3


BRADBURY_CHAIN_ID = 4221
BRADBURY_EXPLORER_URL = "https://explorer-bradbury.genlayer.com"
SHA_PATTERN = r"^[0-9a-f]{40}$"


class ReleaseGateVerificationError(RuntimeError):
    """Raised when a decision cannot prove the expected release."""


@dataclass(frozen=True)
class GateExpectation:
    contract_address: str
    policy_id: str
    request_id: str
    commit_sha: str
    source_url: str
    release_notes_url: str
    repo_owner: str
    repo_name: str
    policy_version: int = 1
    required_marker: str | None = None
    release_note_rule: str | None = None
    transaction_hash: str | None = None


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _validate_expectation(expectation: GateExpectation) -> str:
    if not Web3.is_address(expectation.contract_address):
        raise ValueError("contract address must be a valid EVM address")
    if not expectation.policy_id or not expectation.request_id:
        raise ValueError("policy_id and request_id are required")
    if not re.fullmatch(SHA_PATTERN, expectation.commit_sha):
        raise ValueError("commit_sha must be a lowercase 40-character hexadecimal hash")
    if not expectation.repo_owner or not expectation.repo_name:
        raise ValueError("repo_owner and repo_name are required")
    if expectation.policy_version < 1:
        raise ValueError("policy_version must be positive")
    for label, url in (
        ("source_url", expectation.source_url),
        ("release_notes_url", expectation.release_notes_url),
    ):
        if not url.startswith("https://raw.githubusercontent.com/"):
            raise ValueError(f"{label} must use raw.githubusercontent.com")
        if "?" in url or "#" in url:
            raise ValueError(f"{label} must not contain a query string or fragment")
        prefix = (
            f"https://raw.githubusercontent.com/{expectation.repo_owner}/"
            f"{expectation.repo_name}/{expectation.commit_sha}/"
        )
        if not url.startswith(prefix):
            raise ValueError(f"{label} must be pinned to the expected repository and commit")
        relative_path = url[len(prefix) :]
        segments = relative_path.split("/")
        if not relative_path or any(
            not segment or segment in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9._-]+", segment)
            for segment in segments
        ):
            raise ValueError(f"{label} contains an unsafe path")
        if f"/{expectation.commit_sha}/" not in url:
            raise ValueError(f"{label} must be pinned to commit_sha")
    if expectation.source_url == expectation.release_notes_url:
        raise ValueError("source_url and release_notes_url must differ")
    return Web3.to_checksum_address(expectation.contract_address)


def _require_decision_fields(decision: Mapping[str, Any]) -> None:
    required = {
        "policy_id",
        "policy_version",
        "request_id",
        "commit_sha",
        "source_url",
        "release_notes_url",
        "decision",
        "hard_check_passed",
        "notes_match",
    }
    missing = sorted(required.difference(decision))
    if missing:
        raise ReleaseGateVerificationError(
            "decision is missing required fields: " + ", ".join(missing)
        )
    if not isinstance(decision["policy_id"], str) or not isinstance(decision["request_id"], str):
        raise ReleaseGateVerificationError("decision identifiers must be strings")
    if not isinstance(decision["policy_version"], int) or isinstance(decision["policy_version"], bool):
        raise ReleaseGateVerificationError("decision policy_version must be an integer")
    for field in ("commit_sha", "source_url", "release_notes_url", "decision"):
        if not isinstance(decision[field], str):
            raise ReleaseGateVerificationError(f"decision field {field} must be a string")
    if not isinstance(decision["hard_check_passed"], bool) or not isinstance(decision["notes_match"], bool):
        raise ReleaseGateVerificationError("decision checks must be booleans")


def _require_policy_fields(policy: Mapping[str, Any]) -> None:
    required = {
        "repo_owner",
        "repo_name",
        "required_marker",
        "release_note_rule",
        "version",
    }
    missing = sorted(required.difference(policy))
    if missing:
        raise ReleaseGateVerificationError(
            "policy is missing required fields: " + ", ".join(missing)
        )
    for field in ("repo_owner", "repo_name", "required_marker", "release_note_rule"):
        if not isinstance(policy[field], str):
            raise ReleaseGateVerificationError(f"policy field {field} must be a string")
    if not isinstance(policy["version"], int) or isinstance(policy["version"], bool):
        raise ReleaseGateVerificationError("policy version must be an integer")


def verify_finalized_decision(
    expectation: GateExpectation, client: Any | None = None
) -> dict[str, Any]:
    """Verify a finalized ACCEPT decision against exact release evidence.

    The returned mapping is suitable for JSON output. Any mismatch raises a
    ``ReleaseGateVerificationError`` and callers should fail the release.
    """

    contract_address = _validate_expectation(expectation)
    if client is None:
        # genlayer-py 0.18 requires a sender for read calls. This account is
        # ephemeral and cannot sign because this code never invokes write APIs.
        client = GenLayerClient(testnet_bradbury, Account.create())

    chain_id = int(client.chain_id)
    if chain_id != BRADBURY_CHAIN_ID:
        raise ReleaseGateVerificationError(
            f"wrong network: expected Bradbury chain {BRADBURY_CHAIN_ID}, got {chain_id}"
        )

    policy = client.read_contract(
        address=contract_address,
        function_name="get_policy",
        args=[expectation.policy_id],
    )
    if not isinstance(policy, Mapping):
        raise ReleaseGateVerificationError("contract returned a non-object policy")
    _require_policy_fields(policy)
    expected_policy = {
        "repo_owner": expectation.repo_owner,
        "repo_name": expectation.repo_name,
        "version": expectation.policy_version,
    }
    if expectation.required_marker is not None:
        expected_policy["required_marker"] = expectation.required_marker
    if expectation.release_note_rule is not None:
        expected_policy["release_note_rule"] = expectation.release_note_rule
    for field, expected in expected_policy.items():
        if policy.get(field) != expected:
            raise ReleaseGateVerificationError(
                f"policy field {field} does not match the expected policy"
            )

    decision = client.read_contract(
        address=contract_address,
        function_name="get_decision",
        args=[expectation.policy_id, expectation.request_id],
    )
    if not isinstance(decision, Mapping):
        raise ReleaseGateVerificationError("contract returned a non-object decision")
    _require_decision_fields(decision)

    expected_fields = {
        "policy_id": expectation.policy_id,
        "request_id": expectation.request_id,
        "commit_sha": expectation.commit_sha,
        "source_url": expectation.source_url,
        "release_notes_url": expectation.release_notes_url,
    }
    for field, expected in expected_fields.items():
        if decision.get(field) != expected:
            raise ReleaseGateVerificationError(
                f"decision field {field} does not match the expected release"
            )
    if decision.get("decision") != "ACCEPT":
        raise ReleaseGateVerificationError(
            f"release gate returned {decision.get('decision')!r}, expected 'ACCEPT'"
        )
    if decision.get("hard_check_passed") is not True:
        raise ReleaseGateVerificationError("hard_check_passed is not true")
    if decision.get("notes_match") is not True:
        raise ReleaseGateVerificationError("notes_match is not true")

    transaction_status = None
    execution_result = None
    if expectation.transaction_hash:
        transaction = client.get_transaction(expectation.transaction_hash)
        transaction_status = _enum_value(
            transaction.get("status_name", transaction.get("status"))
        )
        execution_result = _enum_value(
            transaction.get(
                "tx_execution_result_name", transaction.get("tx_execution_result")
            )
        )
        if transaction_status != "FINALIZED":
            raise ReleaseGateVerificationError(
                f"transaction is {transaction_status!r}, not FINALIZED"
            )
        if execution_result != "FINISHED_WITH_RETURN":
            raise ReleaseGateVerificationError(
                f"transaction execution is {execution_result!r}, not FINISHED_WITH_RETURN"
            )

    return {
        "network": "GenLayer Bradbury",
        "chain_id": chain_id,
        "contract_address": contract_address,
        "explorer_url": (
            f"{BRADBURY_EXPLORER_URL}/tx/{expectation.transaction_hash}"
            if expectation.transaction_hash
            else None
        ),
        "transaction_status": transaction_status,
        "execution_result": execution_result,
        "policy": dict(policy),
        "decision": dict(decision),
    }
