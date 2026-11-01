// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {LMSR} from "./LMSR.sol";

/// @notice Contract-side adapter for the approved cost-decrease sell rule.
/// @dev Reuses Matthew's potential. This is a reviewable integration draft,
/// not a substitute for his rounding/solvency proof and payout sign-off.
contract MarketPricing {
    uint256 internal constant MAX_TRADE_SHARES = 100e18;

    error InsufficientQuantity(uint256 requested, uint256 available);

    function buyCost(uint256 yesQuantity, uint256 noQuantity, bool buyYes, uint256 shares)
        external
        pure
        returns (uint256)
    {
        return LMSR.buyCost(yesQuantity, noQuantity, buyYes, shares);
    }

    function sellReturn(uint256 yesQuantity, uint256 noQuantity, bool sellYes, uint256 shares)
        external
        pure
        returns (uint256)
    {
        if (shares == 0) revert LMSR.ZeroShares();
        if (shares > MAX_TRADE_SHARES) revert LMSR.TradeSizeLimitExceeded(shares, MAX_TRADE_SHARES);
        uint256 available = sellYes ? yesQuantity : noQuantity;
        if (shares > available) revert InsufficientQuantity(shares, available);
        uint256 beforeCost = LMSR.cost(yesQuantity, noQuantity);
        uint256 afterCost =
            sellYes ? LMSR.cost(yesQuantity - shares, noQuantity) : LMSR.cost(yesQuantity, noQuantity - shares);
        // Benny's local clarification: do not consume shares for zero-rounded proceeds.
        if (afterCost >= beforeCost) revert LMSR.TradeTooSmall();
        return beforeCost - afterCost;
    }
}
