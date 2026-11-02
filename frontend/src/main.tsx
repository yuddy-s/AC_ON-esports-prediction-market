import React from "react";
import ReactDOM from "react-dom/client";
import { WagmiProvider } from "wagmi";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { config } from "./wagmi";
import App from "./App";
import "./index.css";

// viem's HTTP transport already retries each RPC call, so a failed read is
// retried once here (not react-query's default three times with back-off).
// Otherwise an unreachable RPC keeps pages on "loading" for half a minute
// and interval refetches restart the cycle before an error can show.
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1 } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </WagmiProvider>
  </React.StrictMode>
);
