import type { Address } from "viem";

// PredictionMarket deployment on Ethereum Sepolia (chain ID 11155111).
export const PREDICTION_MARKET_ADDRESS: Address =
  "0x5fc55783fD777BA52253E985078C3326E6ea9554";

export const predictionMarketAbi = [
  {
    type: "function",
    name: "getMarket",
    stateMutability: "view",
    inputs: [{ name: "marketId", type: "uint256" }],
    outputs: [
      { name: "question", type: "string" },
      { name: "tradingDeadline", type: "uint256" },
      { name: "state", type: "uint8" },
      { name: "creator", type: "address" },
    ],
  },
] as const;

export const MARKET_STATES = [
  "Created",
  "Open",
  "Closed",
  "Proposed",
  "Disputed",
  "Finalized",
  "Void",
] as const;
