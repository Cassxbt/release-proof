<script setup lang="ts">
import { computed, ref } from "vue";
import {
  CONTRACT_ADDRESS,
  BRADBURY_CHAIN_ID,
  explorerTransactionUrl,
} from "./config";
import {
  connectWallet,
  createPolicy,
  evaluateRelease,
  readDecision,
  readPolicy,
  switchToBradbury,
  waitForFinalized,
  isTerminalFailure,
  verifyDecisionBinding,
  TransactionTimeoutError,
  type Decision,
  type Policy,
  type TransactionSnapshot,
} from "./genlayer";
import {
  buildEvidenceUrls,
  validateEvidenceInput,
  validatePolicyInput,
} from "./validation";

const walletAddress = ref("");
const walletError = ref("");
const busy = ref(false);
const notice = ref("");
const error = ref("");
const policy = ref<Policy | null>(null);
const decision = ref<Decision | null>(null);
const transaction = ref<TransactionSnapshot | null>(null);

const policyForm = ref({
  policyId: "release-proof-v1",
  repoOwner: "Cassxbt",
  repoName: "release-proof",
  requiredMarker: "Migration",
  releaseNoteRule: "Release notes must accurately describe the source artifact's observable change.",
});

const evidenceForm = ref({
  policyId: "release-proof-v1",
  requestId: "accepted-v1",
  commitSha: "74b3e136f85d92ebe48465b0d259d6eaebc758ff",
  repoOwner: "Cassxbt",
  repoName: "release-proof",
  sourcePath: "fixtures/accepted/SOURCE.md",
  releaseNotesPath: "fixtures/accepted/RELEASE.md",
});

const decisionForm = ref({ policyId: "release-proof-v1", requestId: "accepted-v1" });

const evidenceUrls = computed(() => {
  if (!evidenceForm.value.commitSha || !evidenceForm.value.repoOwner || !evidenceForm.value.repoName) return null;
  return buildEvidenceUrls(evidenceForm.value);
});

const isConfigured = computed(() => /^0x[0-9a-fA-F]{40}$/.test(CONTRACT_ADDRESS));
const shortWallet = computed(() =>
  walletAddress.value ? `${walletAddress.value.slice(0, 6)}...${walletAddress.value.slice(-4)}` : "Connect wallet",
);

function clearMessages() {
  notice.value = "";
  error.value = "";
}

function displayError(value: unknown): string {
  return value instanceof Error ? value.message : String(value);
}

async function handleConnect() {
  clearMessages();
  walletError.value = "";
  try {
    walletAddress.value = await connectWallet();
    notice.value = "Wallet connected to GenLayer Bradbury.";
  } catch (value) {
    walletError.value = displayError(value);
  }
}

async function handleSwitchNetwork() {
  clearMessages();
  try {
    await switchToBradbury();
    walletError.value = "Network switched. Connect the wallet again to confirm the account.";
  } catch (value) {
    walletError.value = displayError(value);
  }
}

async function handleCreatePolicy() {
  clearMessages();
  const errors = validatePolicyInput(policyForm.value);
  if (errors.length) {
    error.value = errors.join(" ");
    return;
  }
  if (!walletAddress.value) {
    error.value = "Connect the deploying wallet before creating a policy.";
    return;
  }
  busy.value = true;
  try {
    const hash = await createPolicy(walletAddress.value, policyForm.value);
    transaction.value = { hash, status: "PENDING", execution: "NOT_VOTED" };
    notice.value = "Policy transaction submitted. Waiting for finalization.";
    const result = await waitForFinalized(hash, (snapshot) => {
      transaction.value = snapshot;
    });
    if (isTerminalFailure(result)) {
      error.value = "The policy transaction did not finalize successfully.";
      return;
    }
    policy.value = await readPolicy(policyForm.value.policyId);
    notice.value = "Policy finalized and readable from Bradbury.";
  } catch (value) {
    error.value = displayError(value);
  } finally {
    busy.value = false;
  }
}

async function handleLoadPolicy() {
  clearMessages();
  busy.value = true;
  try {
    policy.value = await readPolicy(policyForm.value.policyId);
    notice.value = "Policy loaded from the contract.";
  } catch (value) {
    error.value = displayError(value);
  } finally {
    busy.value = false;
  }
}

async function handleEvaluate() {
  clearMessages();
  const errors = validateEvidenceInput(evidenceForm.value);
  if (errors.length) {
    error.value = errors.join(" ");
    return;
  }
  if (!walletAddress.value) {
    error.value = "Connect the deploying wallet before evaluating a release.";
    return;
  }
  if (!evidenceUrls.value) {
    error.value = "Complete the repository and commit fields first.";
    return;
  }
  if (
    policy.value &&
    (policy.value.repo_owner !== evidenceForm.value.repoOwner || policy.value.repo_name !== evidenceForm.value.repoName)
  ) {
    error.value = "The evidence repository does not match the loaded policy.";
    return;
  }
  busy.value = true;
  decision.value = null;
  try {
    const hash = await evaluateRelease(walletAddress.value, {
      policyId: evidenceForm.value.policyId,
      requestId: evidenceForm.value.requestId,
      commitSha: evidenceForm.value.commitSha.toLowerCase(),
      sourceUrl: evidenceUrls.value.sourceUrl,
      releaseNotesUrl: evidenceUrls.value.releaseNotesUrl,
    });
    transaction.value = { hash, status: "PENDING", execution: "NOT_VOTED" };
    localStorage.setItem("releaseproof:lastTransaction", JSON.stringify({
      hash,
      policyId: evidenceForm.value.policyId,
      requestId: evidenceForm.value.requestId,
    }));
    notice.value = "Evaluation submitted. Consensus may take several minutes.";
    const result = await waitForFinalized(hash, (snapshot) => {
      transaction.value = snapshot;
    });
    if (isTerminalFailure(result)) {
      error.value = result.status === "UNDETERMINED"
        ? "Consensus was undetermined. No ACCEPT decision was recorded."
        : "The transaction did not execute successfully. No decision was read.";
      return;
    }
    const storedPolicy = await readPolicy(evidenceForm.value.policyId);
    const loadedDecision = await readDecision(evidenceForm.value.policyId, evidenceForm.value.requestId);
    verifyDecisionBinding(loadedDecision, storedPolicy, {
      policyId: evidenceForm.value.policyId,
      requestId: evidenceForm.value.requestId,
      commitSha: evidenceForm.value.commitSha,
      sourceUrl: evidenceUrls.value.sourceUrl,
      releaseNotesUrl: evidenceUrls.value.releaseNotesUrl,
      repoOwner: evidenceForm.value.repoOwner,
      repoName: evidenceForm.value.repoName,
    });
    decision.value = loadedDecision;
    decisionForm.value = {
      policyId: evidenceForm.value.policyId,
      requestId: evidenceForm.value.requestId,
    };
    notice.value = "Decision finalized and read back from contract state.";
  } catch (value) {
    if (value instanceof TransactionTimeoutError && transaction.value) {
      transaction.value = { ...transaction.value, status: "TIMEOUT" };
    }
    error.value = displayError(value);
  } finally {
    busy.value = false;
  }
}

async function handleReadDecision() {
  clearMessages();
  if (!decisionForm.value.policyId || !decisionForm.value.requestId) {
    error.value = "Enter both a policy ID and request ID.";
    return;
  }
  busy.value = true;
  try {
    if (!evidenceUrls.value) throw new Error("Complete the expected release fields before reading a decision.");
    const storedPolicy = await readPolicy(decisionForm.value.policyId);
    const storedDecision = await readDecision(decisionForm.value.policyId, decisionForm.value.requestId);
    verifyDecisionBinding(storedDecision, storedPolicy, {
      policyId: decisionForm.value.policyId,
      requestId: decisionForm.value.requestId,
      commitSha: evidenceForm.value.commitSha,
      sourceUrl: evidenceUrls.value.sourceUrl,
      releaseNotesUrl: evidenceUrls.value.releaseNotesUrl,
      repoOwner: evidenceForm.value.repoOwner,
      repoName: evidenceForm.value.repoName,
    });
    decision.value = storedDecision;
    notice.value = "Decision loaded and matched against the expected policy and evidence.";
  } catch (value) {
    error.value = displayError(value);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">GENLAYER BRADBURY</p>
        <h1>ReleaseProof Gate</h1>
        <p class="lede">Pinned release evidence goes through consensus before it becomes a green light.</p>
      </div>
      <button class="wallet-button" :disabled="busy" @click="handleConnect">{{ shortWallet }}</button>
    </header>

    <section v-if="!isConfigured" class="banner danger">
      Set <code>VITE_CONTRACT_ADDRESS</code> to the deployed Bradbury contract before using the console.
    </section>
    <section v-if="walletError" class="banner danger">
      <span>{{ walletError }}</span>
      <button class="text-button" @click="handleSwitchNetwork">Switch to Bradbury</button>
    </section>
    <section v-if="notice" class="banner success">{{ notice }}</section>
    <section v-if="error" class="banner danger">{{ error }}</section>

    <section class="grid">
      <article class="card intro-card">
        <p class="eyebrow">ONE GATE</p>
        <h2>Source and release notes must agree.</h2>
        <p>
          The deploying wallet is the only writer. Evidence is restricted to two raw GitHub files at the same full commit SHA.
          The contract stores only ACCEPT, REJECT, or INDETERMINATE.
        </p>
        <div class="limits">
          <span>Owner writes only</span>
          <span>SHA pinned</span>
          <span>Fail closed</span>
        </div>
      </article>

      <article class="card">
        <div class="card-heading">
          <div><p class="eyebrow">01 / POLICY</p><h2>Bind a repository</h2></div>
          <span class="method">create_policy</span>
        </div>
        <label>Policy ID<input v-model="policyForm.policyId" autocomplete="off" /></label>
        <div class="two-up">
          <label>Repository owner<input v-model="policyForm.repoOwner" autocomplete="off" /></label>
          <label>Repository name<input v-model="policyForm.repoName" autocomplete="off" /></label>
        </div>
        <label>Required marker<input v-model="policyForm.requiredMarker" autocomplete="off" /></label>
        <label>Release-note rule<textarea v-model="policyForm.releaseNoteRule" rows="3" /></label>
        <div class="actions"><button :disabled="busy || !isConfigured" @click="handleCreatePolicy">Create policy</button><button class="secondary" :disabled="busy || !isConfigured" @click="handleLoadPolicy">Read policy</button></div>
        <pre v-if="policy" class="result">{{ JSON.stringify(policy, null, 2) }}</pre>
      </article>

      <article class="card evaluate-card">
        <div class="card-heading">
          <div><p class="eyebrow">02 / EVALUATION</p><h2>Submit immutable evidence</h2></div>
          <span class="method">evaluate_release</span>
        </div>
        <div class="two-up">
          <label>Policy ID<input v-model="evidenceForm.policyId" autocomplete="off" /></label>
          <label>Request ID<input v-model="evidenceForm.requestId" autocomplete="off" /></label>
        </div>
        <label>Commit SHA<input v-model="evidenceForm.commitSha" spellcheck="false" autocomplete="off" /></label>
        <div class="two-up">
          <label>Repository owner<input v-model="evidenceForm.repoOwner" autocomplete="off" /></label>
          <label>Repository name<input v-model="evidenceForm.repoName" autocomplete="off" /></label>
        </div>
        <div class="two-up">
          <label>Source path<input v-model="evidenceForm.sourcePath" spellcheck="false" autocomplete="off" /></label>
          <label>Release notes path<input v-model="evidenceForm.releaseNotesPath" spellcheck="false" autocomplete="off" /></label>
        </div>
        <div v-if="evidenceUrls" class="url-preview"><span>Source</span><code>{{ evidenceUrls.sourceUrl }}</code><span>Notes</span><code>{{ evidenceUrls.releaseNotesUrl }}</code></div>
        <button :disabled="busy || !isConfigured" @click="handleEvaluate">Evaluate release</button>
      </article>
    </section>

    <section class="card status-card">
      <div class="card-heading"><div><p class="eyebrow">03 / PROOF</p><h2>Consensus status</h2></div><span v-if="transaction" class="status-pill" :class="transaction.status.toLowerCase()">{{ transaction.status }}</span></div>
      <div v-if="transaction" class="transaction-row">
        <div><span class="muted">Transaction</span><a :href="explorerTransactionUrl(transaction.hash)" target="_blank" rel="noreferrer">{{ transaction.hash }}</a></div>
        <div><span class="muted">Execution</span><strong>{{ transaction.execution }}</strong></div>
      </div>
      <p v-else class="muted">Submit an evaluation to watch the transaction move through consensus.</p>
      <div class="decision-reader">
        <div><p class="eyebrow">READ STORED DECISION</p><div class="two-up"><label>Policy ID<input v-model="decisionForm.policyId" autocomplete="off" /></label><label>Request ID<input v-model="decisionForm.requestId" autocomplete="off" /></label></div></div>
        <button class="secondary" :disabled="busy || !isConfigured" @click="handleReadDecision">Read decision</button>
      </div>
      <div v-if="decision" class="decision" :class="decision.decision.toLowerCase()"><span class="decision-label">{{ decision.decision }}</span><p>{{ decision.decision === "ACCEPT" ? "The evidence passed the configured gate." : decision.decision === "REJECT" ? "The evidence did not satisfy the configured gate." : "Consensus could not establish a safe decision." }}</p><pre>{{ JSON.stringify(decision, null, 2) }}</pre></div>
    </section>

    <footer>Contract <code>{{ CONTRACT_ADDRESS || "not configured" }}</code> · Chain {{ BRADBURY_CHAIN_ID }} · No private keys are handled by this app.</footer>
  </main>
</template>
