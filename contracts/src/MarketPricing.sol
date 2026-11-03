// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {LMSR} from "./LMSR.sol";
import {LMSRBounds} from "./LMSRBounds.sol";

/// @notice Mathematical LMSR pricing: ceil buys and floor sells in ACON base units.
/// @dev Directed numerical intervals certify rounding before a quote is returned.
/// The matched buy-rounding correction and payout invariants still require team review.
contract MarketPricing {
    uint256 internal constant MAX_TRADE_SHARES = 100e18;
    uint256 internal constant MAX_QUANTITY = 2_000e18;

    error InsufficientQuantity(uint256 requested, uint256 available);

    function buyCost(uint256 yesQuantity, uint256 noQuantity, bool buyYes, uint256 shares)
        external
        pure
        returns (uint256)
    {
        _validate(yesQuantity, noQuantity, shares);
        uint256 current = buyYes ? yesQuantity : noQuantity;
        if (shares > MAX_QUANTITY - current) revert LMSR.QuantityLimitExceeded(current + shares, MAX_QUANTITY);
        (, uint256 ceilAmount) = LMSRBounds.trade(yesQuantity, noQuantity, buyYes, shares);
        return ceilAmount;
    }

    function sellReturn(uint256 yesQuantity, uint256 noQuantity, bool sellYes, uint256 shares)
        external
        pure
        returns (uint256)
    {
        _validate(yesQuantity, noQuantity, shares);
        uint256 available = sellYes ? yesQuantity : noQuantity;
        if (shares > available) revert InsufficientQuantity(shares, available);
        (uint256 floorAmount,) = LMSRBounds.trade(
            sellYes ? yesQuantity - shares : yesQuantity, sellYes ? noQuantity : noQuantity - shares, sellYes, shares
        );
        if (floorAmount == 0) revert LMSR.TradeTooSmall();
        return floorAmount;
    }

    function _validate(uint256 yes, uint256 no, uint256 shares) private pure {
        if (shares == 0) revert LMSR.ZeroShares();
        if (shares > MAX_TRADE_SHARES) revert LMSR.TradeSizeLimitExceeded(shares, MAX_TRADE_SHARES);
        if (yes > MAX_QUANTITY) revert LMSR.QuantityLimitExceeded(yes, MAX_QUANTITY);
        if (no > MAX_QUANTITY) revert LMSR.QuantityLimitExceeded(no, MAX_QUANTITY);
    }
}
