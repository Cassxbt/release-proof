export const SHA_PATTERN = /^[0-9a-f]{40}$/i;
const IDENTIFIER_PATTERN = /^[A-Za-z0-9._-]+$/;
const PATH_SEGMENT_PATTERN = /^[A-Za-z0-9._-]+$/;

export type PolicyInput = {
  policyId: string;
  repoOwner: string;
  repoName: string;
  requiredMarker: string;
  releaseNoteRule: string;
};

export type EvidenceInput = {
  policyId: string;
  requestId: string;
  commitSha: string;
  repoOwner: string;
  repoName: string;
  sourcePath: string;
  releaseNotesPath: string;
};

export function validateIdentifier(value: string, label: string): string | null {
  if (!value || value.length > 80 || !IDENTIFIER_PATTERN.test(value)) {
    return `${label} must use letters, numbers, dots, hyphens, or underscores and be at most 80 characters.`;
  }
  return null;
}

export function validatePolicyInput(input: PolicyInput): string[] {
  const errors: string[] = [];
  for (const [value, label] of [
    [input.policyId, "Policy ID"],
    [input.repoOwner, "Repository owner"],
    [input.repoName, "Repository name"],
  ] as const) {
    const error = validateIdentifier(value, label);
    if (error) errors.push(error);
  }
  if (!input.requiredMarker.trim() || input.requiredMarker.length > 120) {
    errors.push("Required marker must be present and at most 120 characters.");
  }
  if (!input.releaseNoteRule.trim() || input.releaseNoteRule.length > 600) {
    errors.push("Release-note rule must be present and at most 600 characters.");
  }
  return errors;
}

function validatePath(path: string, label: string): string | null {
  const segments = path.split("/");
  if (!path || segments.some((segment) => segment === "." || segment === ".." || !PATH_SEGMENT_PATTERN.test(segment))) {
    return `${label} must contain non-empty path segments using letters, numbers, dots, hyphens, or underscores.`;
  }
  return null;
}

export function buildEvidenceUrls(input: EvidenceInput): {
  sourceUrl: string;
  releaseNotesUrl: string;
} {
  const sha = input.commitSha.toLowerCase();
  return {
    sourceUrl: `https://raw.githubusercontent.com/${input.repoOwner}/${input.repoName}/${sha}/${input.sourcePath}`,
    releaseNotesUrl: `https://raw.githubusercontent.com/${input.repoOwner}/${input.repoName}/${sha}/${input.releaseNotesPath}`,
  };
}

export function validateEvidenceInput(input: EvidenceInput): string[] {
  const errors: string[] = [];
  for (const [value, label] of [
    [input.policyId, "Policy ID"],
    [input.requestId, "Request ID"],
    [input.repoOwner, "Repository owner"],
    [input.repoName, "Repository name"],
  ] as const) {
    const error = validateIdentifier(value, label);
    if (error) errors.push(error);
  }
  if (!SHA_PATTERN.test(input.commitSha)) {
    errors.push("Commit SHA must be a full 40-character hexadecimal hash.");
  }
  for (const [value, label] of [
    [input.sourcePath, "Source path"],
    [input.releaseNotesPath, "Release-notes path"],
  ] as const) {
    const error = validatePath(value, label);
    if (error) errors.push(error);
  }
  if (input.sourcePath === input.releaseNotesPath) {
    errors.push("Source and release-notes paths must differ.");
  }
  return errors;
}
