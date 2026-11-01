// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {LMSR} from "../src/LMSR.sol";
import {LMSRBounds} from "../src/LMSRBounds.sol";
import {MarketPricing} from "../src/MarketPricing.sol";
import {VmMarket} from "./MarketTestBase.sol";
import {PricingVectors} from "./PricingVectors.sol";

contract PricingBoundsHarness {
    function correction(uint256 difference) external pure returns (LMSRBounds.Interval memory) {
        return LMSRBounds.correction(difference);
    }

    function ambiguousRounding() external pure returns (uint256, uint256) {
        // This interval encloses both 1 and 1 + a positive fraction of one base unit.
        // Its ceiling cannot be certified, even though its floor is known.
        return LMSRBounds.certify(1, LMSRBounds.Interval(0, 0), LMSRBounds.Interval(0, 1));
    }
}

contract MarketPricingTest {
    VmMarket private constant vm = VmMarket(address(uint160(uint256(keccak256("hevm cheat code")))));
    MarketPricing private pricing;
    PricingBoundsHarness private bounds;

    function setUp() public {
        pricing = new MarketPricing();
        bounds = new PricingBoundsHarness();
    }

    function testReportedSellVectorUsesMathematicalFloor() public view {
        require(pricing.sellReturn(50e18, 50e18, true, 10e18) == 4_750_415_558_917_673_486, "reported YES vector");
        require(pricing.sellReturn(50e18, 50e18, false, 10e18) == 4_750_415_558_917_673_486, "reported NO vector");
        require(pricing.buyCost(40e18, 50e18, true, 10e18) == 4_750_415_558_917_673_487, "reverse buy ceiling");
    }

    function testMatchedBuyCeilingClosesReverseTradeGain() public view {
        uint256 paid = pricing.buyCost(0, 0, true, 10e18);
        uint256 received = pricing.sellReturn(10e18, 0, true, 10e18);
        require(paid == 5_249_584_441_082_326_514, "mathematical buy ceiling");
        require(received == 5_249_584_441_082_326_513, "mathematical sell floor");
        require(paid - received == 1, "profitable inverse trade");
    }

    function testIndependentReferenceVectorsBothOutcomes() public {
        PricingVectors.Vector[] memory vectors = PricingVectors.trades();
        for (uint256 i; i < vectors.length; ++i) {
            PricingVectors.Vector memory vector = vectors[i];
            require(pricing.buyCost(vector.yes, vector.no, true, vector.shares) == vector.ceilAmount, "YES ceil");
            require(pricing.buyCost(vector.no, vector.yes, false, vector.shares) == vector.ceilAmount, "NO ceil");
            if (vector.floorAmount == 0) {
                vm.expectRevert(LMSR.TradeTooSmall.selector);
                pricing.sellReturn(vector.yes + vector.shares, vector.no, true, vector.shares);
                vm.expectRevert(LMSR.TradeTooSmall.selector);
                pricing.sellReturn(vector.no, vector.yes + vector.shares, false, vector.shares);
            } else {
                require(
                    pricing.sellReturn(vector.yes + vector.shares, vector.no, true, vector.shares)
                        == vector.floorAmount,
                    "YES floor"
                );
                require(
                    pricing.sellReturn(vector.no, vector.yes + vector.shares, false, vector.shares)
                        == vector.floorAmount,
                    "NO floor"
                );
            }
        }
    }

    function testNumericalIntervalsEncloseIndependentHighPrecisionCorrections() public view {
        PricingVectors.Correction[] memory vectors = PricingVectors.corrections();
        for (uint256 i; i < vectors.length; ++i) {
            LMSRBounds.Interval memory interval = bounds.correction(vectors[i].difference);
            require(interval.lower <= vectors[i].floorAtScale, "lower bound exceeds mathematical value");
            require(interval.upper >= vectors[i].floorAtScale + 1, "upper bound below mathematical value");
        }
    }

    function testSymmetricCrossingRetainsExactIntegerPrice() public view {
        require(pricing.buyCost(0, 1, true, 2) == 1, "exact integer buy");
        require(pricing.sellReturn(2, 1, true, 2) == 1, "exact integer sell");
        require(pricing.buyCost(49e18, 50e18, true, 2e18) == 1e18, "reflected whole-share buy");
        require(pricing.sellReturn(51e18, 50e18, true, 2e18) == 1e18, "reflected whole-share sell");
    }

    function testUncertifiableRoundingRevertsInsteadOfGuessing() public {
        vm.expectRevert(LMSRBounds.PricingPrecisionExceeded.selector);
        bounds.ambiguousRounding();
    }

    function testFuzzNearIntegerBoundaries(uint256 yesSeed, uint256 noSeed, uint256 shareSeed) public {
        uint256 yes = 50e18 + yesSeed % 1001;
        uint256 no = 50e18 + noSeed % 1001;
        uint256 shares = 2 + shareSeed % 1000;
        // Logistic slope <= 1/(4*B) bounds |delta - shares/2| below 1e-13 base units here.
        // Its sign is determined analytically by which side of the reflected midpoint we end on.
        uint256 expectedFloor = shares / 2;
        uint256 expectedCeil = expectedFloor + shares % 2;
        if (shares % 2 == 0) {
            if (2 * yes + shares > 2 * no) ++expectedCeil;
            else if (2 * yes + shares < 2 * no) --expectedFloor;
        }
        require(pricing.buyCost(yes, no, true, shares) == expectedCeil, "near-integer buy rounding");
        if (expectedFloor == 0) {
            vm.expectRevert(LMSR.TradeTooSmall.selector);
            pricing.sellReturn(yes + shares, no, true, shares);
        } else {
            require(pricing.sellReturn(yes + shares, no, true, shares) == expectedFloor, "near-integer sell rounding");
        }
    }

    function testQuantityAndTradeLimitsApplyToBothDirections() public {
        vm.expectRevert(LMSR.ZeroShares.selector);
        pricing.buyCost(0, 0, true, 0);
        vm.expectPartialRevert(LMSR.TradeSizeLimitExceeded.selector);
        pricing.sellReturn(200e18, 0, true, 100e18 + 1);
        vm.expectPartialRevert(LMSR.QuantityLimitExceeded.selector);
        pricing.buyCost(2_000e18, 0, true, 1);
        vm.expectPartialRevert(LMSR.QuantityLimitExceeded.selector);
        pricing.sellReturn(2_000e18 + 1, 0, true, 1);
        vm.expectPartialRevert(LMSR.QuantityLimitExceeded.selector);
        pricing.sellReturn(1, 2_000e18 + 1, true, 1);
        vm.expectPartialRevert(MarketPricing.InsufficientQuantity.selector);
        pricing.sellReturn(0, 1e18, true, 1);
    }

    function testFuzzExactInverseTradesCannotCreateValue(uint256 yesSeed, uint256 noSeed, uint256 shareSeed)
        public
        view
    {
        uint256 yes = yesSeed % (1_900e18 + 1);
        uint256 no = noSeed % (2_000e18 + 1);
        // At least one whole share: even the lowest supported price exceeds one base unit.
        uint256 shares = 1e18 + shareSeed % (99e18 + 1);
        uint256 paid = pricing.buyCost(yes, no, true, shares);
        uint256 received = pricing.sellReturn(yes + shares, no, true, shares);
        require(paid >= received && paid - received <= 1, "inverse trade rounding gain/spread");
        require(pricing.buyCost(no, yes, false, shares) == paid, "buy outcome asymmetry");
        require(pricing.sellReturn(no, yes + shares, false, shares) == received, "sell outcome asymmetry");
    }
}
