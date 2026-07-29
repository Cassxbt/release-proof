"""A minimal Bradbury client for the ReleaseProof intelligent contract."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

from eth_account import Account
from genlayer_py.chains import testnet_bradbury
from genlayer_py.client import GenLayerClient
from genlayer_py.types import TransactionStatus
from web3 import Web3


BRADBURY_EXPLORER_URL = "https://explorer-bradbury.genlayer.com/"
PRIVATE_KEY_ENV = "RELEASE_PROOF_PRIVATE_KEY"
CONTRACT_ADDRESS_ENV = "RELEASE_PROOF_ADDRESS"


class ContractClient(Protocol):
    def read_contract(
        self, address: str, function_name: str, args: list[Any]
    ) -> Any: ...

    def write_contract(
        self, address: str, function_name: str, args: list[Any]
    ) -> Any: ...

    def wait_for_transaction_receipt(
        self, transaction_hash: Any, status: TransactionStatus
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class OperationResult:
    transaction_hash: str
    receipt: dict[str, Any]

    @property
    def explorer_url(self) -> str:
        return f"{BRADBURY_EXPLORER_URL}tx/{self.transaction_hash}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "transaction_hash": self.transaction_hash,
            "explorer_url": self.explorer_url,
            "receipt": self.receipt,
        }


class ReleaseProofOperator:
    """Sends owner-authorized writes and reads stored release decisions."""

    def __init__(self, client: ContractClient, contract_address: str):
        if not Web3.is_address(contract_address):
            raise ValueError("RELEASE_PROOF_ADDRESS must be a valid EVM address")
        self._client = client
        self._contract_address = Web3.to_checksum_address(contract_address)

    def create_policy(
        self,
        policy_id: str,
        repo_owner: str,
        repo_name: str,
        required_marker: str,
        release_note_rule: str,
    ) -> OperationResult:
        return self._write(
            "create_policy",
            [policy_id, repo_owner, repo_name, required_marker, release_note_rule],
        )

    def evaluate_release(
        self,
        policy_id: str,
        request_id: str,
        commit_sha: str,
        source_url: str,
        release_notes_url: str,
    ) -> OperationResult:
        return self._write(
            "evaluate_release",
            [policy_id, request_id, commit_sha, source_url, release_notes_url],
        )

    def get_decision(self, policy_id: str, request_id: str) -> dict[str, Any]:
        decision = self._client.read_contract(
            address=self._contract_address,
            function_name="get_decision",
            args=[policy_id, request_id],
        )
        if not isinstance(decision, dict):
            raise RuntimeError("Contract returned an invalid decision payload")
        return decision

    def _write(self, function_name: str, args: list[Any]) -> OperationResult:
        transaction_hash = self._client.write_contract(
            address=self._contract_address,
            function_name=function_name,
            args=args,
        )
        receipt = self._client.wait_for_transaction_receipt(
            transaction_hash, status=TransactionStatus.ACCEPTED
        )
        status = receipt.get("status_name")
        status_name = getattr(status, "value", status)
        if status_name != TransactionStatus.ACCEPTED.value:
            raise RuntimeError(f"Transaction was not accepted: {status_name}")
        execution_result = receipt.get("tx_execution_result_name")
        execution_name = getattr(execution_result, "value", execution_result)
        if execution_name != "FINISHED_WITH_RETURN":
            raise RuntimeError(f"Contract execution failed: {execution_name}")
        return OperationResult(transaction_hash=str(transaction_hash), receipt=receipt)


def operator_from_environment() -> ReleaseProofOperator:
    """Load the Bradbury signing account without printing or persisting its key."""
    private_key = os.environ.get(PRIVATE_KEY_ENV, "")
    contract_address = os.environ.get(CONTRACT_ADDRESS_ENV, "")
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", private_key):
        raise ValueError(f"{PRIVATE_KEY_ENV} must contain a 32-byte hexadecimal key")
    if not contract_address:
        raise ValueError(f"{CONTRACT_ADDRESS_ENV} is required")

    account = Account.from_key(private_key)
    client = GenLayerClient(testnet_bradbury, account)
    return ReleaseProofOperator(client, contract_address)
