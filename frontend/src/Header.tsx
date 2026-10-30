import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  ProviderNotFoundError,
  useAccount,
  useBalance,
  useConnect,
  useDisconnect,
  useReadContracts,
  useSwitchChain,
  useWaitForTransactionReceipt,
  useWriteContract,
} from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, CHAIN_MODE, NETWORK_LABEL } from "./config";
import { formatTokenAmount, shortenAddress } from "./format";
import { aconTokenAbi } from "./predictionMarket";
import type { Route } from "./router";
import { Dots } from "./ui";
import {
  connectorLabel,
  isWrongNetwork,
  SEPOLIA_SMART_WALLET_NOTE,
  smartWalletCannotTransact,
  visibleConnectors,
} from "./walletSupport";

const NAV = [
  { href: "#/", label: "Markets", pages: ["markets", "market"] },
  { href: "#/fixtures", label: "Fixtures", pages: ["fixtures", "fixture"] },
] as const;

export function Header({ route }: { route: Route }) {
  return (
    <header className="sticky top-0 z-20 border-b border-bronze/60 bg-ink-900/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <a href="#/" className="flex items-center gap-3">
          <span className="hud-sm bg-gold px-2 py-1 font-display text-sm font-bold tracking-wider text-ink-900">AC_ON</span>
          <span className="hidden flex-col leading-none sm:flex">
            <span className="font-display text-sm font-semibold uppercase tracking-[0.2em] text-paper">Esports</span>
            <span className="font-display text-[10px] uppercase tracking-[0.3em] text-sand">Prediction Market</span>
          </span>
          <Dots size="h-1.5 w-1.5" />
        </a>

        <nav className="order-3 flex w-full gap-1 sm:order-none sm:w-auto">
          {NAV.map((item) => {
            const active = (item.pages as readonly string[]).includes(route.page);
            return (
              <a
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`border-b-2 px-3 py-1.5 font-display text-sm font-semibold uppercase tracking-wider ${
                  active ? "border-gold text-gold" : "border-transparent text-sand hover:text-paper"
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <NetworkChip />
          <AconChip />
          <WalletMenu />
        </div>
      </div>
      <WalletBanners />
    </header>
  );
}

function NetworkChip() {
  return (
    <span className="hidden items-center gap-1.5 border border-bronze px-2 py-1 font-mono text-[11px] text-sand md:inline-flex">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" />
      {NETWORK_LABEL.toUpperCase()}
    </span>
  );
}

// ACON balance with the one-time faucet claim (1,000 ACON per address).
function AconChip() {
  const { address, isConnected, chainId } = useAccount();
  const reads = useReadContracts({
    contracts: [
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "balanceOf", args: [address!], chainId: CHAIN.id },
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "hasClaimedFaucet", args: [address!], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: isConnected && address !== undefined && ACON_TOKEN_ADDRESS !== undefined },
  });
  const claim = useWriteContract();
  const receipt = useWaitForTransactionReceipt({ hash: claim.data, chainId: CHAIN.id });

  // Once the faucet transaction is mined, refresh every read on the page
  // (the header and the trade box both show the ACON balance).
  const queryClient = useQueryClient();
  useEffect(() => {
    if (receipt.isSuccess) void queryClient.invalidateQueries();
  }, [receipt.isSuccess, queryClient]);

  if (!isConnected || !ACON_TOKEN_ADDRESS) return null;
  const token = ACON_TOKEN_ADDRESS;
  const [balance, hasClaimed] = reads.data ?? [];
  const claiming = claim.isPending || (claim.data !== undefined && receipt.isLoading);
  const failed = claim.error || receipt.error || receipt.data?.status === "reverted";

  return (
    <div className="flex items-center border border-bronze">
      <span className="num px-2 py-1 font-mono text-xs text-paper" title="ACON pays for trades">
        {balance !== undefined ? formatTokenAmount(balance) : "…"} <span className="text-gold">ACON</span>
      </span>
      {hasClaimed === false && (
        <button
          onClick={() => claim.writeContract({ address: token, abi: aconTokenAbi, functionName: "faucet", chainId: CHAIN.id })}
          disabled={claiming || isWrongNetwork(chainId, CHAIN.id)}
          title={failed ? "The last claim failed. Try again." : "One-time claim of 1,000 test ACON"}
          className={`px-2 py-1 font-display text-[11px] font-bold uppercase tracking-wider ${
            failed ? "bg-signal-soft text-paper" : "bg-gold text-ink-900 hover:bg-paper"
          } disabled:bg-ink-600 disabled:text-dust`}
        >
          {claim.isPending ? "Confirm…" : claiming ? "Claiming…" : failed ? "Retry claim" : "Claim 1,000"}
        </button>
      )}
    </div>
  );
}

function WalletMenu() {
  const { address, isConnected, connector } = useAccount();
  const { connect, connectors, isPending, error } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: gas } = useBalance({ address, chainId: CHAIN.id, query: { enabled: isConnected } });
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  // Coinbase Smart Wallet is first in wagmi.ts (no extension needed).
  const options = visibleConnectors(connectors);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={isConnected ? "btn-ghost num font-mono normal-case tracking-normal" : "btn-gold py-1.5"}
      >
        {isConnected && address ? shortenAddress(address) : isPending ? "Connecting…" : "Connect"}
      </button>

      {open && (
        <div className="hud absolute right-0 top-full z-30 mt-2 w-72 border-t-2 border-gold bg-ink-600 p-4 shadow-2xl shadow-black/60">
          {isConnected && address ? (
            <div className="flex flex-col gap-3">
              <div>
                <p className="label">Wallet · {connector?.name}</p>
                <p className="mt-1 break-all font-mono text-xs text-paper">{address}</p>
              </div>
              <div>
                <p className="label">Gas balance</p>
                <p className="num mt-1 font-mono text-sm text-paper">
                  {gas ? `${formatTokenAmount(gas.value, gas.decimals, 4)} ${gas.symbol}` : "…"}
                </p>
              </div>
              <button
                onClick={() => {
                  disconnect();
                  setOpen(false);
                }}
                className="btn-ghost self-start"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="label">Choose a wallet</p>
              {options.map((c, i) => (
                <button
                  key={c.uid}
                  onClick={() => {
                    connect({ connector: c });
                    setOpen(false);
                  }}
                  disabled={isPending}
                  className="flex flex-col items-start border border-bronze bg-ink-700 px-3 py-2 text-left hover:border-gold"
                >
                  <span className="font-display text-sm font-semibold text-paper">{i === 0 ? c.name : connectorLabel(c)}</span>
                  {i === 0 && <span className="text-xs text-dust">No extension needed: passkey or email</span>}
                </button>
              ))}
              {CHAIN_MODE === "sepolia" && <p className="text-xs text-gold/80">{SEPOLIA_SMART_WALLET_NOTE}</p>}
            </div>
          )}
        </div>
      )}
      {error && !isConnected && (
        <p className="absolute right-0 top-full mt-2 w-72 bg-signal-deep p-2 text-xs text-paper">
          {error instanceof ProviderNotFoundError
            ? "No browser wallet found. Install or unlock MetaMask in this browser, then refresh the page."
            : error.message.split("\n")[0]}
        </p>
      )}
    </div>
  );
}

// Full-width warnings under the header: wrong network, smart wallet limits.
function WalletBanners() {
  const { isConnected, chainId, connector } = useAccount();
  const switchChain = useSwitchChain();
  if (!isConnected) return null;

  if (isWrongNetwork(chainId, CHAIN.id)) {
    return (
      <div className="border-t border-signal bg-signal-deep">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-2 text-sm text-paper sm:px-6">
          <span>
            Wrong network: your wallet is on chain {chainId}, but this app uses {CHAIN.name}.
          </span>
          <button
            onClick={() => switchChain.switchChain({ chainId: CHAIN.id })}
            disabled={switchChain.isPending}
            className="bg-paper px-3 py-1 font-display text-xs font-bold uppercase tracking-wider text-signal-deep hover:bg-white disabled:opacity-50"
          >
            {switchChain.isPending ? "Confirm in wallet…" : `Switch to ${CHAIN.name}`}
          </button>
          {switchChain.error && <span className="text-xs">Could not switch automatically. Choose {CHAIN.name} in your wallet.</span>}
        </div>
      </div>
    );
  }
  if (smartWalletCannotTransact(CHAIN_MODE, connector?.id)) {
    return (
      <div className="border-t border-gold/50 bg-gold-deep/60">
        <p className="mx-auto max-w-6xl px-4 py-2 text-xs text-paper sm:px-6">{SEPOLIA_SMART_WALLET_NOTE}</p>
      </div>
    );
  }
  return null;
}
