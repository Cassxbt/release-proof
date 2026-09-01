import { describe, expect, it } from "vitest";
import { GenLayerError, isTerminalFailure, verifyDecisionBinding, type Decision, type Policy } from "./genlayer";

const policy: Policy = {
  repo_owner: "Cassxbt",
  repo_name: "release-proof",
  required_marker: "Migration",
  release_note_rule: "rule",
  version: 1,
};

const decision: Decision = {
  policy_id: "release-proof-v1",
  policy_version: 1,
  request_id: "accepted-v1",
  commit_sha: "74b3e136f85d92ebe48465b0d259d6eaebc758ff",
  source_url: "https://raw.githubusercontent.com/Cassxbt/release-proof/74b3e136f85d92ebe48465b0d259d6eaebc758ff/fixtures/accepted/SOURCE.md",
  release_notes_url: "https://raw.githubusercontent.com/Cassxbt/release-proof/74b3e136f85d92ebe48465b0d259d6eaebc758ff/fixtures/accepted/RELEASE.md",
  decision: "ACCEPT",
  hard_check_passed: true,
  notes_match: true,
};

describe("release proof lifecycle guards", () => {
  it("treats all terminal failure states as fail-closed", () => {
    for (const status of ["UNDETERMINED", "CANCELED", "LEADER_TIMEOUT", "VALIDATORS_TIMEOUT"]) {
      expect(isTerminalFailure({ status, execution: "NOT_VOTED" })).toBe(true);
    }
    expect(isTerminalFailure({ status: "FINALIZED", execution: "FINISHED_WITH_ERROR" })).toBe(true);
    expect(isTerminalFailure({ status: "FINALIZED", execution: "FINISHED_WITH_RETURN" })).toBe(false);
  });

  it("requires exact policy and evidence binding", () => {
    expect(() => verifyDecisionBinding(decision, policy, {
      policyId: "release-proof-v1",
      requestId: "accepted-v1",
      commitSha: decision.commit_sha,
      sourceUrl: decision.source_url,
      releaseNotesUrl: decision.release_notes_url,
      repoOwner: "Cassxbt",
      repoName: "release-proof",
    })).not.toThrow();

    expect(() => verifyDecisionBinding(decision, { ...policy, version: 2 }, {
      policyId: "release-proof-v1",
      requestId: "accepted-v1",
      commitSha: decision.commit_sha,
      sourceUrl: decision.source_url,
      releaseNotesUrl: decision.release_notes_url,
      repoOwner: "Cassxbt",
      repoName: "release-proof",
    })).toThrow(GenLayerError);
  });
});
