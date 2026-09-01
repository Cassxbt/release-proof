# Security and trust boundaries

ReleaseProof Gate treats release artifacts and model output as untrusted input. Its security objective is limited: record a consensus result for a narrow notes-to-source comparison, then expose that result to a read-only verifier.

## Trust model

| Component | Trust and authority | Boundary |
| --- | --- | --- |
| Contract owner wallet | Controls policy and evaluation writes. | Owner authorization is enforced by the contract. The private key remains outside this repository. |
| ReleaseProof contract | Stores policies and normalized decisions. | It does not execute submitted code or call a deployment system. |
| GitHub raw-content endpoint | Supplies evidence at a caller-selected commit path. | URLs must be bound to the policy repository and a full commit SHA. Retrieved text remains untrusted. |
| Leader and validators | Independently retrieve and classify evidence. | Only equal canonical decisions can finalize consensus. |
| V1 console | Presents and signs owner actions. | It must not become an alternative source of truth. |
| V1 read-only verifier | Reads the contract and evaluates configured identifiers. | It has no write key and no authority to deploy or publish. |
| CI check | Polls the verifier after an evaluation exists. | It may pass or fail a check; it must not store a wallet key or trigger an irreversible action. |

## Guarantees implemented by the current contract

- `create_policy` and `evaluate_release` reject callers other than the deploying owner.
- Policy IDs are immutable after creation.
- Evidence must use two distinct raw GitHub URLs in the policy repository, pinned to a full 40-character commit SHA.
- Query strings, fragments, traversal segments, empty path segments, and unsupported path characters are rejected.
- A missing required marker returns `REJECT` before model execution.
- Malformed model output and web or model failures normalize to `INDETERMINATE` rather than `ACCEPT`.
- Validators compare a compact canonical object with exactly `decision`, `hard_check_passed`, and `notes_match`.
- A previously used `policy_id:request_id` cannot be evaluated again.
- Stored decisions contain metadata and the normalized result, not raw artifacts or model prose.

## Known limitations

These are boundaries, not hidden guarantees:

- Writes are owner-only. The current contract has no delegated operator or multi-tenant authorization model.
- Request replay protection is keyed by `policy_id:request_id`; the current contract does not index a canonical digest of all submission fields. V1 must derive deterministic request IDs or clearly disclose that owner-controlled duplicate evidence remains possible. A stronger digest index belongs in a separately approved contract version.
- Evidence is truncated to `MAX_ARTIFACT_CHARS` before classification. An `ACCEPT` result does not prove the complete repository or release.
- The contract stores URLs, not content hashes of retrieved text. The commit-pinned URL is the evidence reference, not a code attestation.
- An LLM classifier can be wrong. Prompt construction treats artifacts as data, but it cannot make arbitrary text trustworthy.
- Consensus and web retrieval may take time or fail. `INDETERMINATE` must never be treated as approval.
- The contract has no deployment authority, payment authority, wallet control, or external side effects.

## V1 verifier rules

The verifier must read the configured contract directly and check all of the following before returning success:

1. The chain and contract address match configuration.
2. The policy exists and its version and repository match the request.
3. The decision request, commit SHA, and evidence URLs match the expected release.
4. The stored decision is exactly `ACCEPT` with both boolean checks true.
5. The read is not missing, stale, `REJECT`, or `INDETERMINATE`.

Any failed check returns a non-zero status. The verifier must not accept caller-supplied decision JSON, transaction hashes, or screenshots as proof.

## Explicit non-goals

ReleaseProof Gate is not a code scanner, software supply-chain attestation, compliance certificate, security audit, deployment controller, payment system, or autonomous release authority. Any integration that performs an irreversible action must add its own deterministic checks and explicit human approval outside this V1 scope.
