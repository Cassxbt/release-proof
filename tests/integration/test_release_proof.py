"""Studio integration tests using public, SHA-pinned ReleaseProof fixtures."""

import pytest
from gltest import get_contract_factory
from gltest.assertions import tx_execution_succeeded


SHA = "74b3e136f85d92ebe48465b0d259d6eaebc758ff"
RAW_ROOT = f"https://raw.githubusercontent.com/Cassxbt/release-proof/{SHA}/fixtures"
POLICY_ID = "release-proof-fixtures"
RULE = "Release notes must accurately describe the source artifact's observable change."


@pytest.mark.integration
def test_records_accepted_and_rejected_release_evidence(default_account):
    factory = get_contract_factory("ReleaseProof")
    contract = factory.deploy(args=[])

    create_policy = contract.create_policy(
        args=[POLICY_ID, "Cassxbt", "release-proof", "Migration", RULE]
    ).transact()
    assert tx_execution_succeeded(create_policy)

    accepted = contract.evaluate_release(
        args=[
            POLICY_ID,
            "accepted-fixture-v1",
            SHA,
            f"{RAW_ROOT}/accepted/SOURCE.md",
            f"{RAW_ROOT}/accepted/RELEASE.md",
        ]
    ).transact()
    assert tx_execution_succeeded(accepted)
    assert contract.get_decision(
        args=[POLICY_ID, "accepted-fixture-v1"]
    ).call()["decision"] == "ACCEPT"

    rejected = contract.evaluate_release(
        args=[
            POLICY_ID,
            "rejected-fixture-v1",
            SHA,
            f"{RAW_ROOT}/rejected/SOURCE.md",
            f"{RAW_ROOT}/rejected/RELEASE.md",
        ]
    ).transact()
    assert tx_execution_succeeded(rejected)
    assert contract.get_decision(
        args=[POLICY_ID, "rejected-fixture-v1"]
    ).call()["decision"] == "REJECT"
