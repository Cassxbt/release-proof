import pytest

from backend.release_proof_client import ReleaseProofOperator
from genlayer_py.types import TransactionStatus


ADDRESS = "0x0000000000000000000000000000000000000001"


class FakeClient:
    def __init__(self, receipt=None):
        self.writes = []
        self.receipt = receipt or {
            "status_name": TransactionStatus.ACCEPTED,
            "tx_execution_result_name": "FINISHED_WITH_RETURN",
        }

    def read_contract(self, **kwargs):
        assert kwargs["function_name"] == "get_decision"
        return {"decision": "ACCEPT", "request_id": kwargs["args"][1]}

    def write_contract(self, **kwargs):
        self.writes.append(kwargs)
        return "0xabc"

    def wait_for_transaction_receipt(self, transaction_hash, status):
        assert transaction_hash == "0xabc"
        assert status.value == "ACCEPTED"
        return self.receipt


def test_create_policy_submits_contract_arguments_and_returns_evidence_link():
    client = FakeClient()
    operator = ReleaseProofOperator(client, ADDRESS)

    result = operator.create_policy(
        "release-proof-v1",
        "Cassxbt",
        "release-proof",
        "Migration",
        "Release notes must accurately describe the observable source change.",
    )

    assert client.writes[0]["function_name"] == "create_policy"
    assert result.explorer_url.endswith("tx/0xabc")


def test_evaluate_and_read_decision_use_the_contract_interface():
    client = FakeClient()
    operator = ReleaseProofOperator(client, ADDRESS)

    result = operator.evaluate_release(
        "release-proof-v1",
        "accepted-v1",
        "a" * 40,
        "https://raw.githubusercontent.com/Cassxbt/release-proof/a/SOURCE.md",
        "https://raw.githubusercontent.com/Cassxbt/release-proof/a/RELEASE.md",
    )

    assert client.writes[0]["function_name"] == "evaluate_release"
    assert result.transaction_hash == "0xabc"
    assert operator.get_decision("release-proof-v1", "accepted-v1") == {
        "decision": "ACCEPT",
        "request_id": "accepted-v1",
    }


@pytest.mark.parametrize(
    ("receipt", "message"),
    [
        (
            {
                "status_name": TransactionStatus.UNDETERMINED,
                "tx_execution_result_name": "FINISHED_WITH_RETURN",
            },
            "Transaction was not accepted",
        ),
        (
            {"status_name": TransactionStatus.ACCEPTED},
            "Contract execution failed",
        ),
    ],
)
def test_write_requires_an_accepted_transaction_with_a_return(receipt, message):
    operator = ReleaseProofOperator(FakeClient(receipt), ADDRESS)

    with pytest.raises(RuntimeError, match=message):
        operator.create_policy(
            "release-proof-v1",
            "Cassxbt",
            "release-proof",
            "Migration",
            "Release notes must accurately describe the observable source change.",
        )
