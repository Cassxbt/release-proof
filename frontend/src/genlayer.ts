import { createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";
import type { TransactionHash } from "genlayer-js/types";
import type { Address } from "viem";
import {
  BRADBURY_CHAIN_ID,
  BRADBURY_CHAIN_ID_HEX,
  CONTRACT_ADDRESS,
  isAddress,
} from "./config";

export type Decision = {
  policy_id: string;
  policy_version: number;
  request_id: string;
  commit_sha: string;
  source_url: string;
  release_notes_url: string;
  decision: "ACCEPT" | "REJECT" | "INDETERMINATE";
  hard_check_passed: boolean;
  notes_match: boolean;
};

export type Policy = {
  repo_owner: string;
  repo_name: string;
  required_marker: string;
  release_note_rule: string;
  version: number;
};

export type TransactionSnapshot = {
  hash: string;
  status: string;
  execution: string;
};

export class GenLayerError extends Error {}
export class TransactionTimeoutError extends GenLayerError {}

const TERMINAL_FAILURE_STATUSES = new Set([
  "UNDETERMINED",
  "CANCELED",
  "LEADER_TIMEOUT",
  "VALIDATORS_TIMEOUT",
]);

export function isTerminalFailure(snapshot: Pick<TransactionSnapshot, "status" | "execution">): boolean {
  return TERMINAL_FAILURE_STATUSES.has(snapshot.status) || snapshot.execution === "FINISHED_WITH_ERROR";
}

function requirePolicy(value: unknown): Policy {
  if (!value || typeof value !== "object") throw new GenLayerError("Contract returned an invalid policy.");
  const policy = value as Record<string, unknown>;
  const required = ["repo_owner", "repo_name", "required_marker", "release_note_rule", "version"];
  if (required.some((field) => !(field in policy))) throw new GenLayerError("Contract returned an incomplete policy.");
  if (typeof policy.version !== "number") throw new GenLayerError("Contract returned an invalid policy version.");
  return policy as unknown as Policy;
}

function requireDecision(value: unknown): Decision {
  if (!value || typeof value !== "object") throw new GenLayerError("Contract returned an invalid decision.");
  const decision = value as Record<string, unknown>;
  const required = [
    "policy_id", "policy_version", "request_id", "commit_sha", "source_url",
    "release_notes_url", "decision", "hard_check_passed", "notes_match",
  ];
  if (required.some((field) => !(field in decision))) throw new GenLayerError("Contract returned an incomplete decision.");
  if (!["ACCEPT", "REJECT", "INDETERMINATE"].includes(String(decision.decision))) {
    throw new GenLayerError("Contract returned an unknown decision state.");
  }
  if (typeof decision.hard_check_passed !== "boolean" || typeof decision.notes_match !== "boolean") {
    throw new GenLayerError("Contract returned invalid decision checks.");
  }
  return decision as unknown as Decision;
}

function requireAddress(): Address {
  if (!isAddress(CONTRACT_ADDRESS)) {
    throw new GenLayerError("Set VITE_CONTRACT_ADDRESS to the deployed Bradbury contract address.");
  }
  return CONTRACT_ADDRESS as Address;
}

function provider() {
  if (!window.ethereum) {
    throw new GenLayerError("No browser wallet found. Install a wallet that exposes an EIP-1193 provider.");
  }
  return window.ethereum;
}

export async function connectWallet(): Promise<string> {
  const wallet = provider();
  const accounts = (await wallet.request({ method: "eth_requestAccounts" })) as string[];
  const address = accounts?.[0];
  if (!address) throw new GenLayerError("The wallet did not return an account.");
  const chainId = String(await wallet.request({ method: "eth_chainId" })).toLowerCase();
  if (chainId !== BRADBURY_CHAIN_ID_HEX) {
    throw new GenLayerError(
      `Wrong network. Switch the wallet to GenLayer Bradbury (chain ${BRADBURY_CHAIN_ID}) before writing.`,
    );
  }
  return address;
}

export async function switchToBradbury(): Promise<void> {
  const wallet = provider();
  try {
    await wallet.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: BRADBURY_CHAIN_ID_HEX }],
    });
  } catch (error) {
    const code = typeof error === "object" && error !== null && "code" in error ? error.code : undefined;
    if (String(code) !== "4902") throw error;
    await wallet.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: BRADBURY_CHAIN_ID_HEX,
          chainName: "Genlayer Bradbury Testnet",
          rpcUrls: ["https://rpc-bradbury.genlayer.com"],
          nativeCurrency: { name: "GEN Token", symbol: "GEN", decimals: 18 },
          blockExplorerUrls: ["https://explorer-bradbury.genlayer.com"],
        },
      ],
    });
    await wallet.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: BRADBURY_CHAIN_ID_HEX }],
    });
  }
}

function readClient() {
  return createClient({ chain: testnetBradbury });
}

function writeClient(address: string) {
  type ClientConfig = NonNullable<Parameters<typeof createClient>[0]>;
  type ClientProvider = NonNullable<ClientConfig["provider"]>;
  return createClient({
    chain: testnetBradbury,
    account: address as Address,
    provider: provider() as ClientProvider,
  });
}

export async function readPolicy(policyId: string): Promise<Policy> {
  const result = await readClient().readContract({
    address: requireAddress(),
    functionName: "get_policy",
    args: [policyId],
  });
  return requirePolicy(result);
}

export async function readDecision(policyId: string, requestId: string): Promise<Decision> {
  const result = await readClient().readContract({
    address: requireAddress(),
    functionName: "get_decision",
    args: [policyId, requestId],
  });
  return requireDecision(result);
}

export function verifyDecisionBinding(
  decision: Decision,
  policy: Policy,
  expected: {
    policyId: string;
    requestId: string;
    commitSha: string;
    sourceUrl: string;
    releaseNotesUrl: string;
    repoOwner: string;
    repoName: string;
  },
): void {
  const expectedFields: Record<string, string> = {
    policy_id: expected.policyId,
    request_id: expected.requestId,
    commit_sha: expected.commitSha.toLowerCase(),
    source_url: expected.sourceUrl,
    release_notes_url: expected.releaseNotesUrl,
  };
  for (const [field, value] of Object.entries(expectedFields)) {
    if (decision[field as keyof Decision] !== value) {
      throw new GenLayerError(`Decision field ${field} does not match the expected release.`);
    }
  }
  if (policy.version !== decision.policy_version) throw new GenLayerError("Decision policy version does not match the stored policy.");
  if (policy.repo_owner !== expected.repoOwner || policy.repo_name !== expected.repoName) {
    throw new GenLayerError("Stored policy repository does not match the expected release.");
  }
}

export async function createPolicy(
  walletAddress: string,
  policy: { policyId: string; repoOwner: string; repoName: string; requiredMarker: string; releaseNoteRule: string },
): Promise<string> {
  return String(
    await writeClient(walletAddress).writeContract({
      address: requireAddress(),
      functionName: "create_policy",
      args: [policy.policyId, policy.repoOwner, policy.repoName, policy.requiredMarker, policy.releaseNoteRule],
      value: 0n,
    }),
  );
}

export async function evaluateRelease(
  walletAddress: string,
  input: { policyId: string; requestId: string; commitSha: string; sourceUrl: string; releaseNotesUrl: string },
): Promise<string> {
  return String(
    await writeClient(walletAddress).writeContract({
      address: requireAddress(),
      functionName: "evaluate_release",
      args: [input.policyId, input.requestId, input.commitSha, input.sourceUrl, input.releaseNotesUrl],
      value: 0n,
    }),
  );
}

function normalizeTransaction(hash: string, transaction: Record<string, unknown>): TransactionSnapshot {
  return {
    hash,
    status: String(transaction.statusName ?? transaction.status ?? "PENDING"),
    execution: String(transaction.txExecutionResultName ?? transaction.txExecutionResult ?? "NOT_VOTED"),
  };
}

export async function waitForFinalized(
  hash: string,
  onUpdate: (snapshot: TransactionSnapshot) => void,
  options: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<TransactionSnapshot> {
  const intervalMs = options.intervalMs ?? 5000;
  const timeoutMs = options.timeoutMs ?? 10 * 60 * 1000;
  const client = readClient();
  const startedAt = Date.now();
  let consecutiveReadFailures = 0;

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const transaction = (await client.getTransaction({ hash: hash as TransactionHash })) as unknown as Record<string, unknown>;
      const snapshot = normalizeTransaction(hash, transaction);
      consecutiveReadFailures = 0;
      onUpdate(snapshot);
      if (isTerminalFailure(snapshot)) return snapshot;
      if (snapshot.status === "FINALIZED" && snapshot.execution === "FINISHED_WITH_RETURN") return snapshot;
    } catch {
      consecutiveReadFailures += 1;
      onUpdate({ hash, status: "PENDING", execution: "NOT_VOTED" });
      if (consecutiveReadFailures >= 5) {
        throw new GenLayerError("Bradbury transaction status is unavailable after five consecutive reads.");
      }
    }
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs));
  }
  throw new TransactionTimeoutError("Consensus did not finalize before the ten-minute client deadline.");
}
