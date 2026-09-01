import { describe, expect, it } from "vitest";
import { buildEvidenceUrls, validateEvidenceInput } from "./validation";

const baseEvidence = {
  policyId: "release-proof-v1",
  requestId: "accepted-v1",
  commitSha: "74b3e136f85d92ebe48465b0d259d6eaebc758ff",
  repoOwner: "Cassxbt",
  repoName: "release-proof",
  sourcePath: "fixtures/accepted/SOURCE.md",
  releaseNotesPath: "fixtures/accepted/RELEASE.md",
};

describe("evidence validation", () => {
  it("builds immutable raw GitHub URLs from a lowercase SHA", () => {
    const result = buildEvidenceUrls({ ...baseEvidence, commitSha: baseEvidence.commitSha.toUpperCase() });
    expect(result.sourceUrl).toBe(
      "https://raw.githubusercontent.com/Cassxbt/release-proof/74b3e136f85d92ebe48465b0d259d6eaebc758ff/fixtures/accepted/SOURCE.md",
    );
  });

  it("rejects malformed hashes and unsafe paths before a wallet call", () => {
    const errors = validateEvidenceInput({
      ...baseEvidence,
      commitSha: "deadbeef",
      sourcePath: "../SOURCE.md",
    });
    expect(errors).toEqual([
      "Commit SHA must be a full 40-character hexadecimal hash.",
      "Source path must contain non-empty path segments using letters, numbers, dots, hyphens, or underscores.",
    ]);
  });
});
