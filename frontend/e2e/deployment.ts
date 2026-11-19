// Expected public M4 deployment for the hosted (PLAYWRIGHT_EXPECT_API=1) journeys. Values come from
// deployments/sepolia-2026-11-02/manifest.post-setup.json and are checked against chain receipts,
// so a test cannot pass by trusting whatever the API happens to return.
export const SEPOLIA_CHAIN_ID = 11155111;
export const M4_MARKET_ADDRESS = "0x03ae48f03C7822540a91DA2168602bd49dC510E9";

// Market 0's indexed buys and sells. Each hash is a successful Sepolia receipt sent to the M4
// market (verified with `cast receipt`); market 0 is VOID, so this history can no longer change.
export const MARKET_0_RECEIPTS = [
  { block: 12052315, hash: "0x2d512622352ddd5e52dff710d2f2d3a00bf5ab84583ed7889fa7b1f9ec0f6400" },
  { block: 12052387, hash: "0x68717be6a33690b8d81b6b56e51e8ce5a296c872ee40353d80c308cce7ae9ff5" },
  { block: 12052394, hash: "0xee62a9261634b031ce84f94f7964f2b53fab46c55cefbb3442ce0312334bc701" },
  { block: 12052699, hash: "0x6906d816e7e0ab2f6fbac6a84018817d790b98a6c925ccaadb1b4ce18696e0f0" },
  { block: 12052758, hash: "0x8ec71340ba555e32d0b99ef0ede79cbf27293dfff83da5aacec1be7a1a105a1f" },
  { block: 12052761, hash: "0xdfb0ea6b839d2bda2ea66a998b4e99579e864d48b59d9174073c97593f5b997e" },
] as const;

interface StatusBody {
  configured?: boolean;
  chain_id?: number;
  contract_address?: string | null;
}

// Why an /api/v2/indexer/status body does not describe the expected deployment (empty = OK).
// A wrong-chain or wrong-contract body is still HTTP 200, so the HTTP status alone proves nothing.
export function indexerStatusProblems(body: StatusBody): string[] {
  const problems: string[] = [];
  if (body.configured !== true) problems.push("indexer is not configured");
  if (body.chain_id !== SEPOLIA_CHAIN_ID) problems.push(`chain_id is ${body.chain_id}, expected ${SEPOLIA_CHAIN_ID}`);
  if (body.contract_address?.toLowerCase() !== M4_MARKET_ADDRESS.toLowerCase()) {
    problems.push(`contract_address is ${body.contract_address}, expected ${M4_MARKET_ADDRESS}`);
  }
  return problems;
}

// Messages RecentTrades shows instead of trustworthy rows (loading, unverified or wrong deployment,
// unreachable API). The stale-worker notice is not here: it keeps rows visible and only warns.
export const UNTRUSTED_HISTORY_TEXT =
  /Checking indexer deployment|Loading trades|Cannot verify the indexer deployment|Recent trades are hidden|Indexer API unreachable/;
