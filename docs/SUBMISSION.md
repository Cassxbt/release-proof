# Builder Project submission packet

This packet is the reviewer map for the proposed ReleaseProof Gate Builder Project. It is intentionally honest about what is deployed today and what must be completed before submission.

## One-sentence pitch

ReleaseProof Gate turns a narrow release-note claim into a SHA-pinned, validator-agreed GenLayer decision that a read-only CI check can verify without holding a wallet key.

## Reviewer path

1. Open the public repository: [github.com/Cassxbt/release-proof](https://github.com/Cassxbt/release-proof).
2. Read [HOW_IT_WORKS.md](HOW_IT_WORKS.md) for the mechanism and boundaries.
3. Read [SECURITY.md](SECURITY.md) for owner authority, verifier rules, and non-goals.
4. Read [ADVERSARIAL_TESTING.md](ADVERSARIAL_TESTING.md) for current tests and explicit evidence gaps.
5. Open the deployed contract and the accepted and rejected transaction receipts below.
6. Open the V1 hosted console and its two-to-four-minute walkthrough once those artifacts exist.

## Current deployed evidence

The current contract was validated in GenLayer Studio using Normal full consensus. The deployment and policy transaction hashes below are the evidence recorded for the existing contract, not evidence that the V1 console is already complete.

| Artifact | Evidence |
| --- | --- |
| Contract | `0x9cB79Ef2a8123A28e05399c7bEd75eD85e0a70B6` |
| Deployment transaction hash | `0x29add50bde39606d695b81d55c3a5218f572226388a4aa19b980b0dca49c659b` |
| Policy transaction hash | `0x2e13e03cf9eddf17b784f46c345e1359f6c960d4428161160d8726a686272362` |
| Rejected fixture transaction hash | `0x9f173d8b636a834d55b9972c941f33fe368e94cb12f51066ca8f84608e6b8d2a` |
| Accepted fixture transaction hash | `0xefbd5ae91f3ba7f94219043d645e7adadf956b044ffbd4bc70e40aa95cce881c` |
| Fixture commit | [`74b3e136f85d92ebe48465b0d259d6eaebc758ff`](https://github.com/Cassxbt/release-proof/tree/74b3e136f85d92ebe48465b0d259d6eaebc758ff) |

Observed fixture results:

- `accepted-v1` stored `ACCEPT` with both checks true.
- `rejected-v1` stored `REJECT` with both checks false because the required marker is absent.

## Project acceptance boundary

Do not submit the Builder Project until all of the following are true:

- A public hosted console creates policies, submits evaluations, and reads stored decisions through the real contract.
- The console handles pending, accepted, rejected, and indeterminate states without presenting indeterminate as success.
- A read-only verifier and CI check validate the trusted contract state without a private key.
- Browser, verifier, and CI tests are reproducible and included in the judge packet.
- The public README links the live URL, repository, walkthrough, contract, and both allowed and denied transaction proofs on its first screen.
- The walkthrough shows the full user path in under four minutes, including one accepted and one rejected outcome.
- Security limits are visible: owner-only writes, no auto-deploy, no code execution, no payment or wallet control, and narrow release-note proof.

## Planned V1 claims

| Claim | Required proof | Status |
| --- | --- | --- |
| GenLayer is central to the decision | Real contract calls and Explorer receipts | Current contract proven; console pending |
| A release can be accepted or rejected | Accepted and rejected pinned fixtures | Proven in Studio |
| CI can enforce the result without a key | Read-only verifier and CI test run | Verifier and workflow implemented; live run pending |
| The system fails closed | Direct tests plus verifier mismatch and terminal-state tests | Local tests proven; live run pending |
| The product is safe for production deploys | No valid proof | Explicitly not claimed |

## Submission assets still missing

- Public hosted console URL.
- Live read-only verifier and CI check output.
- Browser and CI test output from the final deployment.
- Two-to-four-minute scoped walkthrough recording.
- Fresh Project deployment and transaction receipts for the final V1 build.

Until these assets exist, this packet is a build and evidence plan, not a completed Project submission.
