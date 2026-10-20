// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {SD59x18, sd} from "@prb/math/src/SD59x18.sol";

/// @title LMSR
/// @notice Pure binary logarithmic market scoring rule math using 18-decimal fixed point values.
/// @dev Quantities, prices, costs, and the liquidity parameter all use WAD precision.
library LMSR {
    uint256 internal constant WAD = 1e18;
    uint256 internal constant B = 50e18;
    uint256 internal constant REQUIRED_SUBSIDY = 34_657_359_027_997_265_471;

    // Keeping |qYes - qNo| / B at or below 40 prevents PRBMath's negative
    // exponential from rounding to zero and leaves ample headroom in SD59x18.
    uint256 internal constant MAX_QUANTITY = 2_000e18;
    uint256 internal constant MAX_TRADE_SHARES = 100e18;

    error ZeroShares();
    error TradeTooSmall();
    error QuantityLimitExceeded(uint256 quantity, uint256 maximum);
    error TradeSizeLimitExceeded(uint256 shares, uint256 maximum);

    /// @notice Returns the LMSR cost-function value for the supplied outstanding quantities.
    /// @dev Uses stable log-sum-exp: max(q) + b*ln(1 + exp(-abs(qYes-qNo)/b)).
    function cost(uint256 qYes, uint256 qNo) internal pure returns (uint256) {
        _validateQuantity(qYes);
        _validateQuantity(qNo);

        uint256 maximum = qYes >= qNo ? qYes : qNo;
        SD59x18 exponential = _negativeImbalanceExp(qYes, qNo);
        SD59x18 correction = sd(50e18) * (sd(1e18) + exponential).ln();

        return maximum + correction.intoUint256();
    }

    /// @notice Returns the amount due for buying `shares` of one outcome.
    /// @dev The returned value is exactly C(after) - C(before), so quotes telescope across trades.
    function buyCost(uint256 qYes, uint256 qNo, bool buyYes, uint256 shares) internal pure returns (uint256) {
        if (shares == 0) revert ZeroShares();
        if (shares > MAX_TRADE_SHARES) revert TradeSizeLimitExceeded(shares, MAX_TRADE_SHARES);

        _validateQuantity(qYes);
        _validateQuantity(qNo);

        uint256 currentQuantity = buyYes ? qYes : qNo;
        if (shares > MAX_QUANTITY - currentQuantity) {
            revert QuantityLimitExceeded(currentQuantity + shares, MAX_QUANTITY);
        }

        uint256 beforeCost = cost(qYes, qNo);
        uint256 afterCost = buyYes ? cost(qYes + shares, qNo) : cost(qYes, qNo + shares);

        // At sub-wei economic values, fixed-point rounding may leave the potential unchanged.
        if (afterCost <= beforeCost) revert TradeTooSmall();
        return afterCost - beforeCost;
    }

    /// @notice Returns the instantaneous YES and NO prices, each in WAD precision.
    /// @dev One side is calculated and the other is its complement, so the sum is exactly WAD.
    function prices(uint256 qYes, uint256 qNo) internal pure returns (uint256 yesPrice, uint256 noPrice) {
        _validateQuantity(qYes);
        _validateQuantity(qNo);

        uint256 exponential = _negativeImbalanceExp(qYes, qNo).intoUint256();
        uint256 lowerPrice = exponential * WAD / (WAD + exponential);
        uint256 higherPrice = WAD - lowerPrice;

        if (qYes >= qNo) {
            return (higherPrice, lowerPrice);
        }
        return (lowerPrice, higherPrice);
    }

    /// @notice Returns ceil(B * ln(2)), the collateral required to initialize a binary market.
    function requiredSubsidy() internal pure returns (uint256) {
        return REQUIRED_SUBSIDY;
    }

    function _negativeImbalanceExp(uint256 qYes, uint256 qNo) private pure returns (SD59x18) {
        uint256 difference = qYes >= qNo ? qYes - qNo : qNo - qYes;
        // Safe because both quantities are bounded by MAX_QUANTITY (2_000e18).
        // forge-lint: disable-next-line(unsafe-typecast)
        SD59x18 normalizedDifference = sd(int256(difference)) / sd(50e18);
        return (-normalizedDifference).exp();
    }

    function _validateQuantity(uint256 quantity) private pure {
        if (quantity > MAX_QUANTITY) revert QuantityLimitExceeded(quantity, MAX_QUANTITY);
    }
}
