from __future__ import annotations

import pytest

from backend.release_gate_verifier import (
    GateExpectation,
    ReleaseGateVerificationError,
    verify_finalized_decision,
)


SHA = "74b3e136f85d92ebe48465b0d259d6eaebc758ff"
SOURCE = (
    "https://raw.githubusercontent.com/Cassxbt/release-proof/"
    f"{SHA}/fixtures/accepted/SOURCE.md"
)
NOTES = (
    "https://raw.githubusercontent.com/Cassxbt/release-proof/"
    f"{SHA}/fixtures/accepted/RELEASE.md"
)
EXPECTATION = GateExpectation(
    contract_address="0x9cB79Ef2a8123A28e05399c7bEd75eD85e0a70B6",
    policy_id="release-proof-v1",
    request_id="accepted-v1",
    commit_sha=SHA,
    source_url=SOURCE,
    release_notes_url=NOTES,
    repo_owner="Cassxbt",
    repo_name="release-proof",
    transaction_hash="0xefbd5ae91f3ba7f94219043d645e7adadf956b044ffbd4bc70e40aa95cce881c",
)


class FakeClient:
    chain_id = 4221

    def __init__(self, decision: dict, transaction: dict | None = None):
        self.decision = decision
        self.policy = {
            "repo_owner": "Cassxbt",
            "repo_name": "release-proof",
            "required_marker": "Migration",
            "release_note_rule": "rule",
            "version": 1,
        }
        self.transaction = transaction or {
            "status_name": "FINALIZED",
            "tx_execution_result_name": "FINISHED_WITH_RETURN",
        }

    def read_contract(self, **kwargs):
        if kwargs["function_name"] == "get_policy":
            return self.policy
        assert kwargs["function_name"] == "get_decision"
        return self.decision

    def get_transaction(self, transaction_hash):
        return self.transaction


def valid_decision() -> dict:
    return {
        "policy_id": EXPECTATION.policy_id,
        "policy_version": 1,
        "request_id": EXPECTATION.request_id,
        "commit_sha": EXPECTATION.commit_sha,
        "source_url": EXPECTATION.source_url,
        "release_notes_url": EXPECTATION.release_notes_url,
        "decision": "ACCEPT",
        "hard_check_passed": True,
        "notes_match": True,
    }


def test_verifies_exact_finalized_accept():
    result = verify_finalized_decision(EXPECTATION, FakeClient(valid_decision()))
    assert result["chain_id"] == 4221
    assert result["decision"]["decision"] == "ACCEPT"


@pytest.mark.parametrize(
    "field,value",
    [
        ("commit_sha", "0" * 40),
        ("source_url", "https://raw.githubusercontent.com/Cassxbt/release-proof/" + SHA + "/fixtures/rejected/SOURCE.md"),
        ("decision", "REJECT"),
    ],
)
def test_rejects_mismatched_release_proof(field, value):
    decision = valid_decision()
    decision[field] = value
    with pytest.raises(ReleaseGateVerificationError):
        verify_finalized_decision(EXPECTATION, FakeClient(decision))


def test_rejects_non_final_transaction():
    with pytest.raises(ReleaseGateVerificationError, match="not FINALIZED"):
        verify_finalized_decision(
            EXPECTATION,
            FakeClient(valid_decision(), {"status_name": "ACCEPTED", "tx_execution_result_name": "FINISHED_WITH_RETURN"}),
        )


def test_rejects_policy_bound_to_different_repository():
    client = FakeClient(valid_decision())
    client.policy["repo_name"] = "other-repo"
    with pytest.raises(ReleaseGateVerificationError, match="repo_name"):
        verify_finalized_decision(EXPECTATION, client)


def test_rejects_policy_version_mismatch():
    client = FakeClient(valid_decision())
    client.policy["version"] = 2
    with pytest.raises(ReleaseGateVerificationError, match="version"):
        verify_finalized_decision(EXPECTATION, client)


def test_rejects_unsafe_expected_url():
    unsafe = GateExpectation(
        **{
            **EXPECTATION.__dict__,
            "source_url": SOURCE.replace("fixtures/accepted/SOURCE.md", "fixtures/../SOURCE.md"),
            "transaction_hash": None,
        }
    )
    with pytest.raises(ValueError, match="unsafe path"):
        verify_finalized_decision(unsafe, FakeClient(valid_decision()))
