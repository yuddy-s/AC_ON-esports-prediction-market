import { expect, test, type Page } from "@playwright/test";

// LOC-08: wrong network and rejected wallet requests (M5). A scripted EIP-1193 provider stands in
// for MetaMask so the failure paths run without a real wallet, key or transaction. It never signs:
// every write and network-switch request is rejected with the standard code 4001, and read calls
// go to a public Sepolia RPC. The reverted-receipt path stays covered by tradeStatus unit tests and
// manual MetaMask runs, because a receipt comes from the chain, not the wallet.

const TEST_ADDRESS = "0x1111111111111111111111111111111111111111"; // has never claimed the faucet
const SEPOLIA_HEX = "0xaa36a7";
const MAINNET_HEX = "0x1";
const READ_RPC = "https://ethereum-sepolia-rpc.publicnode.com";

async function installFakeWallet(page: Page, chainIdHex: string) {
  await page.addInitScript(
    ({ address, chainId, rpc }) => {
      const reject = (method: string) =>
        Promise.reject(Object.assign(new Error(`User rejected the request (${method}).`), { code: 4001 }));
      const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};
      const provider = {
        isMetaMask: true,
        on(event: string, fn: (...args: unknown[]) => void) {
          (listeners[event] ??= []).push(fn);
          return provider;
        },
        removeListener(event: string, fn: (...args: unknown[]) => void) {
          listeners[event] = (listeners[event] ?? []).filter((f) => f !== fn);
          return provider;
        },
        async request({ method, params }: { method: string; params?: unknown[] }) {
          switch (method) {
            case "eth_requestAccounts":
            case "eth_accounts":
              return [address];
            case "eth_chainId":
              return chainId;
            case "net_version":
              return String(parseInt(chainId, 16));
            case "wallet_requestPermissions":
            case "wallet_getPermissions":
              return [{ parentCapability: "eth_accounts" }];
            case "eth_sendTransaction":
            case "personal_sign":
            case "eth_signTypedData_v4":
            case "wallet_switchEthereumChain":
            case "wallet_addEthereumChain":
              return reject(method);
            default: {
              const res = await fetch(rpc, {
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params: params ?? [] }),
              });
              const body = await res.json();
              if (body.error) throw Object.assign(new Error(body.error.message), { code: body.error.code });
              return body.result;
            }
          }
        },
      };
      (window as unknown as { ethereum: unknown }).ethereum = provider;
    },
    { address: TEST_ADDRESS, chainId: chainIdHex, rpc: READ_RPC },
  );
}

async function connectBrowserWallet(page: Page) {
  await page.goto("#/");
  await page.getByRole("button", { name: /^connect$/i }).click();
  await page.getByRole("button", { name: /metamask \(browser wallet\)/i }).click();
  await expect(page.getByRole("button", { name: /0x1111/i })).toBeVisible();
}

test("LOC-08a wrong network: warns, blocks the faucet and survives a refused switch", async ({ page }) => {
  await installFakeWallet(page, MAINNET_HEX);
  await connectBrowserWallet(page);

  await expect(page.getByText(/Wrong network: your wallet is on chain 1, but this app uses Sepolia/)).toBeVisible();
  await expect(page.getByRole("button", { name: /claim 1,000/i })).toBeDisabled();

  await page.getByRole("button", { name: /switch to sepolia/i }).click();
  await expect(page.getByText(/Could not switch automatically\. Choose Sepolia in your wallet\./)).toBeVisible();
  // Still blocked: a refused switch must not enable writes.
  await expect(page.getByRole("button", { name: /claim 1,000/i })).toBeDisabled();
});

test("LOC-08b rejected request: faucet claim shows a retryable failure and sends nothing", async ({ page }) => {
  const sent: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && (r.postData() ?? "").includes("eth_sendRawTransaction")) sent.push(r.url());
  });
  await installFakeWallet(page, SEPOLIA_HEX);
  await connectBrowserWallet(page);

  await expect(page.getByText(/Wrong network/)).toHaveCount(0);
  const claim = page.getByRole("button", { name: /claim 1,000/i });
  await expect(claim).toBeEnabled();
  await claim.click();

  const retry = page.getByRole("button", { name: /retry claim/i });
  await expect(retry).toBeVisible();
  await expect(retry).toHaveAttribute("title", "The last claim failed. Try again.");
  await expect(retry).toBeEnabled();
  expect(sent).toEqual([]);
});
