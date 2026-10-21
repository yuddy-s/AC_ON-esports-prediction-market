import { useAccount, useConnect, useDisconnect, useBalance } from "wagmi";

// TODO: replace with the deployed test-token address once Benny/Matthew
// have it on the testnet (leave undefined to just show native testnet ETH for now).
const TEST_TOKEN_ADDRESS = undefined as `0x${string}` | undefined;

function shortenAddress(address: string) {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function WalletConnect() {
  const { address, isConnected } = useAccount();
  const { connect, connectors, isPending, error } = useConnect();
  const { disconnect } = useDisconnect();

  const { data: balance } = useBalance({
    address,
    token: TEST_TOKEN_ADDRESS,
    query: { enabled: isConnected },
  });

  if (!isConnected) {
    // Coinbase Smart Wallet is first in wagmi.ts, so it's connectors[0].
    // No extension or app required — opens a popup, sign in with a
    // passkey or email. This is the option most users (and any demo
    // machine) should use.
    const [primary, ...rest] = connectors;

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
                Connect{" "}
                {connector.type === "mock" ? "Anvil test wallet (local only)" : connector.name}
              </button>
            ))}
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error.message}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start gap-2 rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <p className="text-sm text-neutral-400">Connected wallet</p>
      <p className="font-mono text-lg text-amber-300">{shortenAddress(address!)}</p>

      <p className="mt-2 text-sm text-neutral-400">Balance</p>
      <p className="font-mono text-lg">
        {balance ? `${balance.formatted} ${balance.symbol}` : "Loading..."}
      </p>

      <button
        onClick={() => disconnect()}
        className="mt-3 rounded-lg border border-neutral-600 px-4 py-1.5 text-sm hover:bg-neutral-800"
      >
        Disconnect
      </button>
    </div>
  );
}
