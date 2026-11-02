// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {mulDiv} from "@prb/math/src/Common.sol";

/// @notice Directed bounds for the mathematical LMSR trade cost, not rounded potentials.
/// @dev Callers validate quantities <= 2000e18 and positive shares <= 100e18.
/// Every returned floor/ceiling is certified by an enclosing interval. If its endpoints
/// disagree on rounding, fail rather than guess. See docs/agent/testing/PRICING_ROUNDING.md.
library LMSRBounds {
    uint256 internal constant SCALE = 1e72;
    uint256 private constant B = 50e18;

    struct Interval {
        uint256 lower;
        uint256 upper;
    }

    error PricingPrecisionExceeded();

    /// @notice Floor and ceiling of C(after a buy) - C(before), in ACON base units.
    /// @dev The reverse sale uses this same positive mathematical difference.
    function trade(uint256 yes, uint256 no, bool buyYes, uint256 shares)
        internal
        pure
        returns (uint256 floorAmount, uint256 ceilAmount)
    {
        uint256 afterYes = buyYes ? yes + shares : yes;
        uint256 afterNo = buyYes ? no : no + shares;
        uint256 beforeMaximum = yes >= no ? yes : no;
        uint256 afterMaximum = afterYes >= afterNo ? afterYes : afterNo;
        uint256 beforeDifference = yes >= no ? yes - no : no - yes;
        uint256 afterDifference = afterYes >= afterNo ? afterYes - afterNo : afterNo - afterYes;
        uint256 integerPart = afterMaximum - beforeMaximum;

        // Symmetric states have exactly identical logarithmic corrections. Preserve the
        // exact integer result rather than enclosing it with two independently rounded bounds.
        if (beforeDifference == afterDifference) return (integerPart, integerPart);

        Interval memory beforeLog = correction(beforeDifference);
        Interval memory afterLog = correction(afterDifference);
        return certify(integerPart, beforeLog, afterLog);
    }

    /// @dev Certifies both directions of rounding for an enclosed trade difference.
    function certify(uint256 integerPart, Interval memory beforeLog, Interval memory afterLog)
        internal
        pure
        returns (uint256 floorAmount, uint256 ceilAmount)
    {
        floorAmount = _round(integerPart, afterLog.lower, beforeLog.upper, false);
        ceilAmount = _round(integerPart, afterLog.upper, beforeLog.lower, true);
        if (
            floorAmount != _round(integerPart, afterLog.upper, beforeLog.lower, false)
                || ceilAmount != _round(integerPart, afterLog.lower, beforeLog.upper, true)
        ) revert PricingPrecisionExceeded();
    }

    /// @notice Bounds on ln(1 + exp(-difference / B)), scaled by SCALE.
    function correction(uint256 difference) internal pure returns (Interval memory result) {
        Interval memory exponential = _negativeExp(difference);
        // ln(1+x) = 2 * atanh(x/(2+x)); 0 <= x <= 1, so z <= 1/3.
        uint256 zLower = mulDiv(exponential.lower, SCALE, 2 * SCALE + exponential.lower);
        uint256 zUpper = _mulDivUp(exponential.upper, SCALE, 2 * SCALE + exponential.upper);
        uint256 squareLower = mulDiv(zLower, zLower, SCALE);
        uint256 squareUpper = _mulDivUp(zUpper, zUpper, SCALE);
        uint256 powerLower = zLower;
        uint256 powerUpper = zUpper;
        for (uint256 i; i < 80; ++i) {
            uint256 denominator = 2 * i + 1;
            result.lower += 2 * (powerLower / denominator);
            result.upper += 2 * _divUp(powerUpper, denominator);
            powerLower = mulDiv(powerLower, squareLower, SCALE);
            powerUpper = _mulDivUp(powerUpper, squareUpper, SCALE);
        }
        // The omitted positive series is <= 2*z^161/(161*(1-z^2)) < 3*z^161.
        // powerUpper bounds z^161 even after all intermediate upward rounding.
        result.upper += 3 * powerUpper;
    }

    function _negativeExp(uint256 difference) private pure returns (Interval memory result) {
        if (difference == 0) return Interval(SCALE, SCALE);
        // SCALE is divisible by B*64. This input conversion is exact, and x <= 40/64.
        uint256 x = difference * (SCALE / (B * 64));
        uint256 termLower = SCALE;
        uint256 termUpper = SCALE;
        uint256 sumLower = SCALE;
        uint256 sumUpper = SCALE;
        for (uint256 n = 1; n <= 56; ++n) {
            termLower = mulDiv(termLower, x, SCALE * n);
            termUpper = _mulDivUp(termUpper, x, SCALE * n);
            sumLower += termLower;
            sumUpper += termUpper;
        }
        // exp(x)'s tail after n=56 is bounded by twice its first omitted term:
        // every subsequent term ratio is <= (40/64)/58 < 1/2.
        sumUpper += 2 * _mulDivUp(termUpper, x, SCALE * 57);
        result.lower = mulDiv(SCALE, SCALE, sumUpper);
        result.upper = _mulDivUp(SCALE, SCALE, sumLower);
        // Recover exp(-difference/B) = exp(-x)^64, preserving direction at every square.
        for (uint256 i; i < 6; ++i) {
            result.lower = mulDiv(result.lower, result.lower, SCALE);
            result.upper = _mulDivUp(result.upper, result.upper, SCALE);
        }
    }

    function _round(uint256 integerPart, uint256 addedLog, uint256 removedLog, bool up) private pure returns (uint256) {
        if (addedLog >= removedLog) {
            uint256 increase = addedLog - removedLog;
            return integerPart + (up ? _mulDivUp(B, increase, SCALE) : mulDiv(B, increase, SCALE));
        }
        uint256 difference = removedLog - addedLog;
        // floor(n-x) = n-ceil(x); ceil(n-x) = n-floor(x) for integer n.
        uint256 deduction = up ? mulDiv(B, difference, SCALE) : _mulDivUp(B, difference, SCALE);
        // Intersect the interval with the independently known nonnegative trade domain.
        return deduction > integerPart ? 0 : integerPart - deduction;
    }

    function _mulDivUp(uint256 x, uint256 y, uint256 denominator) private pure returns (uint256) {
        uint256 quotient = mulDiv(x, y, denominator);
        return quotient + (mulmod(x, y, denominator) == 0 ? 0 : 1);
    }

    function _divUp(uint256 value, uint256 denominator) private pure returns (uint256) {
        return value / denominator + (value % denominator == 0 ? 0 : 1);
    }
}
