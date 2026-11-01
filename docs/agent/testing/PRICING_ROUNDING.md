# Mathematical trade rounding correction

Status: **local correction authorized by Benny and reconciled with Matthew's revised economic
proof; final reviewer and consumer sign-off remain pending**. This selects mathematical floor for
sells and matched ceiling for buys, replacing the superseded integer-potential draft.

## Rule and motivating regressions

Let `C(q) = b * ln(exp(qYes/b) + exp(qNo/b))`, with `b = 50e18` and quantities/costs in base units.
For an accepted trade the current `MarketPricing` computes:

- buy: `ceil(C(after) - C(before))`;
- sell: `floor(C(before) - C(after))`.

Both are evaluated from the same positive mathematical difference. Sells whose mathematical
floor is zero revert `TradeTooSmall`; a positive buy costs at least one base unit because it
rounds up. Zero shares and existing size/quantity bounds remain enforced. Exact integer differences have identical buy and reverse-sell prices.
Otherwise the inverse pair differs by exactly one base unit, retained in collateral as rounding
reserve. There is no platform fee or fixed per-trade error buffer.

| Regression | Old integer-potential amount | Correct mathematical amount |
|---|---:|---:|
| Sell 10 YES from `(50e18,50e18)` | 4,750,415,558,917,673,950 | **4,750,415,558,917,673,486** (floor) |
| Buy 10 YES from `(0,0)` | 5,249,584,441,082,326,050 | **5,249,584,441,082,326,514** (ceiling) |
| Sell those 10 YES back to `(0,0)` | 5,249,584,441,082,326,050 | **5,249,584,441,082,326,513** (floor) |

Changing only the sell calculation would let that second/third pair gain 463 base units per
round trip under the old buy calculation. Benny explicitly authorized the corresponding buy
correction. This changes executable numeric quotes from the original draft; it is a proposed
numeric amendment for team review, not an assertion that PR #28 already approved ceil-buy pricing.

## Directed interval calculation

`LMSRBounds.sol` uses exact integer operations and PRBMath's full-width `mulDiv` as a floor
primitive. `mulmod` determines whether an extra unit is needed for ceiling division. It does
not rely on an assumed error bound for PRBMath's 18-decimal `exp`/`ln` approximations.

The computation encloses the stable correction `L(d) = ln(1 + exp(-d/b))`, where `d` is the
absolute quantity imbalance, using scale `Q = 10^72`:

1. **Exponent range reduction.** `x = d/(64*b)` is in `[0, 0.625]`. Because `Q` is divisible
   by `64*b`, `d * (Q/(64*b))` represents `x` exactly.
2. **Exponential enclosure.** Sum `exp(x) = sum(x^n/n!)` through `n=56`. Each lower term is
   rounded down; each upper term is rounded up. The omitted positive tail is at most twice
   the first omitted term: all subsequent ratios are at most `0.625/58 < 1/2`. Add that
   explicit upper tail; the partial lower sum needs no tail adjustment.
3. **Reciprocal and squaring.** The reciprocal of the upper sum bounds `exp(-x)` below;
   the reciprocal of the lower sum bounds it above. Round each in its corresponding direction
   and square six times with directed rounding to enclose `exp(-d/b)`.
4. **Logarithm enclosure.** For exponential value `u`, set `z = u/(2+u)`. Monotonicity gives
   directed bounds on `z`, with its true value in `[0,1/3]`. Evaluate
   `ln(1+u) = 2 * sum(z^(2k+1)/(2k+1))` for `k=0..79`, bounding every product/division.
   The remainder is at most `2*z^161/(161*(1-z^2)) < 3*z^161`; add the corresponding
   upward-rounded power bound to the upper sum.
5. **Difference before base-unit rounding.** Represent the trade as the exact change in
   `max(qYes,qNo)` plus `b * (L_after - L_before)`. Its lower endpoint uses the after-lower
   and before-upper bounds; its upper endpoint uses after-upper and before-lower. The
   logarithmic values are never independently rounded to ACON base units.
6. **Certified result.** Apply mathematical floor to both endpoints and require equal results;
   do the same for ceiling. Only then return the pair. Equal absolute imbalances before/after
   are handled by the exact reflection identity, which cancels identical corrections and
   returns the integer change in `max(q)` directly.

The public pricing wrapper enforces the supported domain before calling these internal helpers.
All scaled inputs, sums and denominators fit uint256: `Q=10^72`, `x<=0.625Q`, exponential sums
are below `2Q`, and the largest exponential denominator is `57Q`. Products use 512-bit `mulDiv`.
Quantity maxima are never multiplied by `Q`; the integer part of the cost stays separate.

### Ambiguous rounding

A large precision alone is not a proof of exact rounding. If the interval does not certify
both floor and ceiling, the calculation reverts `PricingPrecisionExceeded` instead of guessing
or paying an arbitrary underestimate. This is an additional pricing error in the exported ABI.
The regression and fuzz cases pass without this error, but they do not establish that it is
unreachable for every supported input. Review of availability near integer boundaries remains
part of the numerical-method review. No token or position change occurs when quoting fails.

## Collateral argument

For each successful buy, the collected integer amount is at least the real cost increase.
For each successful sell, the integer payout is at most the real cost decrease. Inductively,
before settlement and excluding separate bonds:

```text
collateral >= S + C(q) - C(0) >= max(qYes, qNo),
S = ceil(C(0)).
```

The real potential changes telescope; the nonnegative per-trade rounding residues accumulate
in collateral. This is an **inequality**, not the old exact equality with the contract-rounded
18-decimal potential. It also covers VOID because `ceil((qYes+qNo)/2) <= max(qYes,qNo)` for
integer quantities. Existing bond separation, terminal liability reserves, claims and surplus
checks still apply. Surplus can include accumulated rounding reserve only after terminal
liabilities are protected.

Matthew's revised [economic proof](M4_ECONOMIC_PROOF.md) derives this inequality over the rounded
trade ledger. Its sell-inclusive state machine directly checks quote-to-collateral changes,
winning/VOID coverage, conservation, and market isolation while the separate settlement campaign
checks claims, bond disposition, and surplus. Final sign-off still applies to the reviewed exact
source/build rather than this design note alone.

## Independent evidence and maintenance

`script/pricing_reference.py` evaluates the direct real-valued log-sum-exp formula with Python
Decimal at **160 and 220 digits**, requiring identical integer results. It generates 72 trade
vectors and 85 logarithmic-correction references in `test/PricingVectors.sol`. Forge only formats
the generated fixture; it does not compute the expected values.

`MarketPricing.t.sol` checks both outcomes and directions against those vectors, enclosure of the
high-precision corrections, the reported 464-unit discrepancy, exact symmetric prices, rejection
of uncertifiable intervals, quantity/size limits, inverse-trade rounding and analytically derived
near-integer boundaries. `PredictionMarket.t.sol` additionally checks 16 actual ACON buy/sell
round trips retain exactly 16 base units rather than increasing the trader's balance, and that a
one-base-unit buy charges one base unit while a zero-proceeds sell reverts without consuming shares.

From `contracts/`:

```bash
python3 script/pricing_reference.py --check
forge test --match-contract MarketPricingTest -vv
forge test
```

The interval algorithm costs more gas than the old 18-decimal potential subtraction. The local
Anvil smoke and production-size checks must accompany the updated build, and deployment gas
estimates must use this implementation. The generated ABI/errors, source hashes and event
examples must be refreshed before consumer approval of the corrected build.
