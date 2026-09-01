# Adversarial testing

The test suite treats the contract boundary as hostile. It checks deterministic guards, failure normalization, validator agreement, verifier binding, and the operator client's transaction handling. The current repository has 25 passing cases across the direct and operator suites, plus four frontend unit cases.

## Current test coverage

| Attack or failure | Expected result | Current evidence |
| --- | --- | --- |
| Non-owner creates or evaluates | Revert with owner-only error | `test_only_owner_can_create_or_evaluate` |
| Duplicate policy ID | Revert | `test_rejects_duplicate_policy` |
| Mutable or foreign GitHub URL | Revert before web access | `test_rejects_mutable_or_untrusted_evidence_before_web_access` |
| Path traversal in evidence URL | Revert | `test_rejects_github_urls_with_path_traversal_segments` |
| Identical source and notes URLs | Revert | `test_rejects_identical_source_and_release_notes_urls` |
| Matching evidence and model result | Store `ACCEPT` | `test_accepts_matching_release_and_stores_compact_decision` |
| Missing required marker | Store `REJECT` even if model says accept | `test_hard_marker_failure_is_rejected_even_if_model_accepts` |
| Malformed model output | Store `INDETERMINATE` | `test_malformed_model_output_fails_closed_to_indeterminate` |
| Evidence or model unavailable | Store `INDETERMINATE` | `test_unavailable_model_or_evidence_fails_closed_to_indeterminate` |
| Prompt-injection-shaped source text | Model result remains authoritative | `test_prompt_injection_in_evidence_cannot_override_a_rejecting_model` |
| Reused request ID | Revert | `test_prevents_replaying_a_request_id` |
| Validator derives a different result | Consensus validator returns false | `test_validator_rejects_when_it_independently_derives_a_different_decision` |
| Non-accepted operator receipt | Raise an error | `test_write_requires_an_accepted_transaction_with_a_return` |

The integration test uses public, SHA-pinned fixtures and records both an `ACCEPT` and a `REJECT` result in GenLayer Studio or localnet, depending on the selected test network.

The read-only verifier tests cover exact policy repository and version binding, decision metadata mismatches, unsafe expected paths, wrong chain IDs, non-accepted decisions, and non-final transactions. They use an injected fake client, so no wallet key is needed.

## Reproduce current checks

```bash
.venv/bin/genvm-lint lint contracts/release_proof.py
.venv/bin/pytest tests/direct tests/operator -q
```

Expected current result: GenVM lint passes and the direct/operator suite reports `25 passed`.

The Studio integration test requires the GenLayer test environment and is not part of the fast command above:

```bash
.venv/bin/gltest tests/integration -v -s --network localnet
```

## Gaps that must be closed before a Project submission

The following are required for the V1 product evidence and are not claimed as complete by this document:

- Browser end-to-end tests covering owner wallet, policy creation, evaluation, pending state, and stored decision reads.
- A live Bradbury run of the read-only verifier proving that the deployed contract, policy, decision, and receipt match the submitted release.
- Deterministic request-ID or canonical submission-digest tests. The current contract prevents reuse of the same request ID only.
- Duplicate concurrent finalization tests if a new contract version adds an idempotent gate state.
- A semantic mismatch fixture that reaches the model path and produces a deterministic `REJECT`. The existing rejected fixture is a hard-marker rejection and should not be described as model-semantic proof.
- A CI run of the included workflow proving that the check never requires or prints a private key and fails closed on timeout or indeterminate state.
- A scoped browser walkthrough showing an allowed and a denied result with Explorer links.

## Evidence policy

No test result is promoted to a security guarantee. Test names and commands in the judge packet must continue to match the repository. If a check is planned, it is labeled planned until its output is committed or linked to a reproducible run.
