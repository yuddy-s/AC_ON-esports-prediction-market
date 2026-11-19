# FE-B3 fresh Sepolia approval and buy — November 19, 2026

Result: **passed on real Sepolia using the local PR #70 production build**, commit
`2809636ab93600439d8ca927c11d2987f2550dcc`. The app was served at `http://127.0.0.1:4175` with the M4
contracts and no indexer API. MetaMask account ending `2093b` confirmed both transactions.

The app moved from approval to the buy confirmation automatically. No page refresh, second
approval, or repeated buy was needed. The final UI reported the mined buy and one YES share.

| Step | Receipt | Block | Result |
|---|---|---|---|
| Approve exact max cost | [Approval](https://sepolia.etherscan.io/tx/0x78e0dddb98318dbcf1b9a35caa5c527ada662bb1c7eea72b242bb1a7a87849ad) | 12168815 | 0.417516952439497612 ACON cap |
| Buy 1 YES on market 1 | [Buy](https://sepolia.etherscan.io/tx/0x1152a2174c7c31fb05f0788e2b6ec66ac82f17de4895c828bd653f3ecf817137) | 12168823 | 0.413383121227225358 ACON paid |

The starting allowance, 0.310078048318727968 ACON, was insufficient for the buy cap, so this run
exercised the approval step. The remaining allowance was 0.004133831212272254 ACON. The wallet's
ACON balance changed from 1,000 to 999.586616878772774642, and its market-1 YES position changed
from zero to one. The decoded buy arguments, TradeExecuted event and ACON transfer agree.

- [Verification and checks](verification.json)
- [Preflight chain reads](preflight.json)
- [Approval transaction, receipt and allowance](approval-receipt.json)
- [Buy transaction, receipt and wallet balances](buy-receipt.json)
- [Final UI screenshot](final-ui.png) and [captured accessibility-state changes](final-ui-ax-diff.txt)

The form's quote updates after the trade; use the receipt and verification JSON for the executed
cost. The screenshot's indexed step is skipped because this local test deliberately has no API
configured. This verifies FE-B3's wallet journey on the tested build; it does not complete hosted
Vercel/Render acceptance for ECON-05 or establish resolution of the public-domain MetaMask warning.
No live browser RPC trace was captured. The explicit simulation-block behavior is covered by the
source and deterministic regression tests; the original intermittent provider response is unknown.
