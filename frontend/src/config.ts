export const BRADBURY_CHAIN_ID = 4221;
export const BRADBURY_CHAIN_ID_HEX = `0x${BRADBURY_CHAIN_ID.toString(16)}`;
export const BRADBURY_RPC_URL = "https://rpc-bradbury.genlayer.com";
export const BRADBURY_EXPLORER_URL = "https://explorer-bradbury.genlayer.com";
export const CONTRACT_ADDRESS = (import.meta.env.VITE_CONTRACT_ADDRESS ?? "").trim();

export function explorerTransactionUrl(hash: string): string {
  return `${BRADBURY_EXPLORER_URL}/tx/${hash}`;
}

export function isAddress(value: string): boolean {
  return /^0x[0-9a-fA-F]{40}$/.test(value);
}
