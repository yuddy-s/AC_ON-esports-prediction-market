import { ProviderNotFoundError, useAccount, useConnect, useDisconnect, useBalance, useSwitchChain } from "wagmi";
import { CHAIN, CHAIN_MODE } from "./config";
import { formatTokenAmount, shortenAddress } from "./format";
import {
  connectorLabel,
  isWrongNetwork,
  SEPOLIA_SMART_WALLET_NOTE,
  smartWalletCannotTransact,
  visibleConnectors,
} from "./walletSupport";

export function WalletConnect() {
  const { address, isConnected, connector: activeConnector, chainId: walletChainId } = useAccount();
  const switchChain = useSwitchChain();
  const { connect, connectors, isPending, error } = useConnect();
  const { disconnect } = useDisconnect();

  // Native ETH balance (pays gas). The ACON trading balance is in AconPanel.
  const { data: balance } = useBalance({
    address,
    chainId: CHAIN.id,
    query: { enabled: isConnected },
  });

  if (!isConnected) {
    // Coinbase Smart Wallet is first in wagmi.ts, so it's connectors[0].
    // No extension or app required — opens a popup, sign in with a
    // passkey or email. This is the option most users (and any demo
    // machine) should use.
    const [primary, ...rest] = visibleConnectors(connectors);

    return (
      <div className="flex flex-col items-start gap-3">
        {primary && (
          <button
            onClick={() => connect({ connector: primary })}
            disabled={isPending}
            className="rounded-lg bg-amber-400 px-5 py-2.5 font-semibold text-neutral-900 hover:bg-amber-300 disabled:opacity-50"
          >
            {isPending ? "Connecting..." : "Connect Wallet"}
          </button>
        )}
        <p className="text-xs text-neutral-500">
          No wallet app or extension needed — sign in with a passkey or
          email.
        </p>
        {CHAIN_MODE === "sepolia" && (
          <p className="max-w-md text-xs text-amber-300/80">{SEPOLIA_SMART_WALLET_NOTE}</p>
        )}

        {rest.length > 0 && (
          <div className="mt-2 flex flex-col items-start gap-1.5">
            <p className="text-xs text-neutral-500">
              Already have a wallet extension?
            </p>
            {rest.map((connector) => (
              <button
                key={connector.uid}
                onClick={() => connect({ connector })}
                disabled={isPending}
                className="text-sm text-amber-300 underline underline-offset-2 hover:text-amber-200 disabled:opacity-50"
              >
                Connect {connectorLabel(connector)}
              </button>
            ))}
          </div>
        )}

        {error && (
          <p className="text-sm text-red-400">
            {error instanceof ProviderNotFoundError
              ? "No browser wallet found. Install or unlock MetaMask in this browser, then refresh the page."
              : error.message}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2 rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <p className="text-sm text-neutral-400">Connected wallet</p>
      <p className="font-mono text-lg text-amber-300">{shortenAddress(address!)}</p>

      <p className="mt-2 text-sm text-neutral-400">Gas balance</p>
      <p className="font-mono text-lg">
        {balance ? `${formatTokenAmount(balance.value, balance.decimals, 4)} ${balance.symbol}` : "Loading..."}
      </p>

      {isWrongNetwork(walletChainId, CHAIN.id) && (
        <div className="mt-2 flex max-w-md flex-col items-start gap-2 rounded-md border border-red-800 bg-red-950 p-3 text-sm text-red-200">
          <p>Wrong network: your wallet is on chain {walletChainId}, but this app uses {CHAIN.name}.</p>
          <button
            onClick={() => switchChain.switchChain({ chainId: CHAIN.id })}
            disabled={switchChain.isPending}
            className="rounded-md bg-red-200 px-3 py-1.5 font-semibold text-red-950 hover:bg-white disabled:opacity-50"
          >
            {switchChain.isPending ? "Confirm in wallet…" : `Switch to ${CHAIN.name}`}
          </button>
          {switchChain.error && (
            <p className="text-xs">Could not switch automatically. Choose {CHAIN.name} in your wallet's network menu.</p>
          )}
        </div>
      )}

      {smartWalletCannotTransact(CHAIN_MODE, activeConnector?.id) && (
        <p className="mt-2 max-w-md rounded-md border border-amber-700 bg-amber-950 p-2 text-xs text-amber-200">
          {SEPOLIA_SMART_WALLET_NOTE}
        </p>
      )}

      <button
        onClick={() => disconnect()}
        className="mt-3 rounded-lg border border-neutral-600 px-4 py-1.5 text-sm hover:bg-neutral-800"
      >
        Disconnect
      </button>
    </div>
  );
}
