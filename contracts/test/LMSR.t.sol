// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {LMSR} from "../src/LMSR.sol";

interface VmLMSR {
    function expectRevert(bytes calldata revertData) external;
}

contract LMSRHarness {
    function cost(uint256 qYes, uint256 qNo) external pure returns (uint256) {
        return LMSR.cost(qYes, qNo);
    }

    function buyCost(uint256 qYes, uint256 qNo, bool buyYes, uint256 shares) external pure returns (uint256) {
        return LMSR.buyCost(qYes, qNo, buyYes, shares);
    }

    function prices(uint256 qYes, uint256 qNo) external pure returns (uint256 yesPrice, uint256 noPrice) {
        return LMSR.prices(qYes, qNo);
    }

    function requiredSubsidy() external pure returns (uint256) {
        return LMSR.requiredSubsidy();
    }
}

contract LMSRTest {
    VmLMSR private constant vm = VmLMSR(address(uint160(uint256(keccak256("hevm cheat code")))));

    uint256 private constant WAD = 1e18;
    uint256 private constant B = 50e18;
    uint256 private constant MAX_QUANTITY = 2_000e18;
    uint256 private constant MAX_TRADE_SHARES = 100e18;
    uint256 private constant REQUIRED_SUBSIDY = 34_657_359_027_997_265_471;

    LMSRHarness private lmsr;

    function setUp() public {
        lmsr = new LMSRHarness();
    }

    function testRequiredSubsidyIsFrozenValue() public view {
        require(lmsr.requiredSubsidy() == REQUIRED_SUBSIDY, "subsidy mismatch");
    }

    function testInitialCostIsCoveredByRequiredSubsidy() public view {
        uint256 initialCost = lmsr.cost(0, 0);
        require(initialCost == 34_657_359_027_997_265_450, "initial potential vector mismatch");
        require(REQUIRED_SUBSIDY - initialCost == 21, "subsidy rounding margin mismatch");
    }

    function testInitialPricesAreEqual() public view {
        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(0, 0);
        require(yesPrice == WAD / 2, "YES should start at 0.5");
        require(noPrice == WAD / 2, "NO should start at 0.5");
    }

    function testKnownPriceVectorAtOneLiquidityUnit() public view {
        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(B, 0);
        _assertApproxEqAbs(yesPrice, 731_058_578_630_004_879, 100, "YES price vector mismatch");
        _assertApproxEqAbs(noPrice, 268_941_421_369_995_121, 100, "NO price vector mismatch");
    }

    function testBuyYesRaisesYesPrice() public view {
        (uint256 beforePrice,) = lmsr.prices(0, 0);
        (uint256 afterPrice,) = lmsr.prices(10e18, 0);
        require(afterPrice > beforePrice, "YES price should rise");
    }

    function testBuyNoRaisesNoPrice() public view {
        (, uint256 beforePrice) = lmsr.prices(0, 0);
        (, uint256 afterPrice) = lmsr.prices(0, 10e18);
        require(afterPrice > beforePrice, "NO price should rise");
    }

    function testOutcomeSymmetry() public view {
        uint256 qYes = 137e18;
        uint256 qNo = 42e18;

        require(lmsr.cost(qYes, qNo) == lmsr.cost(qNo, qYes), "cost should be symmetric");

        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(qYes, qNo);
        (uint256 swappedYesPrice, uint256 swappedNoPrice) = lmsr.prices(qNo, qYes);
        require(yesPrice == swappedNoPrice, "swapped YES price mismatch");
        require(noPrice == swappedYesPrice, "swapped NO price mismatch");
    }

    function testLargerBuyCostsMore() public view {
        uint256 oneShareCost = lmsr.buyCost(0, 0, true, 1e18);
        uint256 tenShareCost = lmsr.buyCost(0, 0, true, 10e18);
        require(tenShareCost > oneShareCost, "larger buy should cost more");
    }

    function testBuyCostIsExactPotentialDifference() public view {
        uint256 qYes = 30e18;
        uint256 qNo = 15e18;
        uint256 shares = 7e18;
        uint256 expected = lmsr.cost(qYes + shares, qNo) - lmsr.cost(qYes, qNo);

        require(lmsr.buyCost(qYes, qNo, true, shares) == expected, "buy cost should telescope exactly");
    }

    function testPricesSumExactlyToWad() public view {
        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(1_999e18, 3e18);
        require(yesPrice + noPrice == WAD, "prices should sum to WAD");
    }

    function testMaximumSupportedImbalanceRemainsRepresentable() public view {
        uint256 marketCost = lmsr.cost(MAX_QUANTITY, 0);
        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(MAX_QUANTITY, 0);

        require(marketCost >= MAX_QUANTITY, "cost must cover maximum payout");
        require(yesPrice < WAD, "YES price must remain below one");
        require(noPrice > 0, "NO price must remain positive");
        require(yesPrice + noPrice == WAD, "boundary prices should sum to WAD");
    }

    function testMaximumTradeReachesQuantityBoundary() public view {
        uint256 payment = lmsr.buyCost(MAX_QUANTITY - MAX_TRADE_SHARES, 0, true, MAX_TRADE_SHARES);
        require(payment > 0, "boundary trade should have a positive cost");
    }

    function testZeroSharesReverts() public {
        vm.expectRevert(abi.encodeWithSelector(LMSR.ZeroShares.selector));
        lmsr.buyCost(0, 0, true, 0);
    }

    function testSubWeiEconomicTradeReverts() public {
        vm.expectRevert(abi.encodeWithSelector(LMSR.TradeTooSmall.selector));
        lmsr.buyCost(MAX_QUANTITY, 0, false, 1);
    }

    function testTradeAbovePerTransactionLimitReverts() public {
        vm.expectRevert(
            abi.encodeWithSelector(LMSR.TradeSizeLimitExceeded.selector, MAX_TRADE_SHARES + 1, MAX_TRADE_SHARES)
        );
        lmsr.buyCost(0, 0, true, MAX_TRADE_SHARES + 1);
    }

    function testTradeAboveQuantityLimitReverts() public {
        vm.expectRevert(abi.encodeWithSelector(LMSR.QuantityLimitExceeded.selector, MAX_QUANTITY + 1, MAX_QUANTITY));
        lmsr.buyCost(MAX_QUANTITY, 0, true, 1);
    }

    function testCostAboveQuantityLimitReverts() public {
        vm.expectRevert(abi.encodeWithSelector(LMSR.QuantityLimitExceeded.selector, MAX_QUANTITY + 1, MAX_QUANTITY));
        lmsr.cost(MAX_QUANTITY + 1, 0);
    }

    function testFuzzPricesAreSymmetricAndSumExactly(uint256 qYesSeed, uint256 qNoSeed) public view {
        uint256 qYes = qYesSeed % (MAX_QUANTITY + 1);
        uint256 qNo = qNoSeed % (MAX_QUANTITY + 1);

        (uint256 yesPrice, uint256 noPrice) = lmsr.prices(qYes, qNo);
        (uint256 swappedYesPrice, uint256 swappedNoPrice) = lmsr.prices(qNo, qYes);

        require(yesPrice + noPrice == WAD, "price sum drift");
        require(yesPrice == swappedNoPrice, "fuzzed YES symmetry failure");
        require(noPrice == swappedYesPrice, "fuzzed NO symmetry failure");
    }

    function testFuzzBuyCostMatchesPotentialDifference(
        uint256 qYesSeed,
        uint256 qNoSeed,
        uint256 sharesSeed,
        bool buyYes
    ) public {
        uint256 qYes = qYesSeed % (MAX_QUANTITY + 1);
        uint256 qNo = qNoSeed % (MAX_QUANTITY + 1);
        uint256 currentQuantity = buyYes ? qYes : qNo;
        uint256 remaining = MAX_QUANTITY - currentQuantity;
        uint256 maximumTrade = remaining < MAX_TRADE_SHARES ? remaining : MAX_TRADE_SHARES;
        if (maximumTrade == 0) return;

        uint256 shares = 1 + (sharesSeed % maximumTrade);
        uint256 beforeCost = lmsr.cost(qYes, qNo);
        uint256 afterCost = buyYes ? lmsr.cost(qYes + shares, qNo) : lmsr.cost(qYes, qNo + shares);

        if (afterCost <= beforeCost) {
            vm.expectRevert(abi.encodeWithSelector(LMSR.TradeTooSmall.selector));
            lmsr.buyCost(qYes, qNo, buyYes, shares);
        } else {
            require(lmsr.buyCost(qYes, qNo, buyYes, shares) == afterCost - beforeCost, "cost drift");
        }
    }

    function testFuzzBoundedLoss(uint256 qYesSeed, uint256 qNoSeed) public view {
        uint256 qYes = qYesSeed % (MAX_QUANTITY + 1);
        uint256 qNo = qNoSeed % (MAX_QUANTITY + 1);
        uint256 initialCost = lmsr.cost(0, 0);
        uint256 finalCost = lmsr.cost(qYes, qNo);
        // PRBMath can move the potential down by a few wei when both quantities
        // are themselves only a few wei. Such a transition is not executable:
        // buyCost rejects every non-increasing rounded potential.
        uint256 collected = finalCost > initialCost ? finalCost - initialCost : 0;
        uint256 maximumPayout = qYes >= qNo ? qYes : qNo;

        require(maximumPayout <= collected + REQUIRED_SUBSIDY, "market-maker loss exceeds subsidy");
    }

    function _assertApproxEqAbs(uint256 actual, uint256 expected, uint256 tolerance, string memory message)
        private
        pure
    {
        uint256 difference = actual >= expected ? actual - expected : expected - actual;
        require(difference <= tolerance, message);
    }
}

contract LMSRBuyHandler {
    uint256 private constant MAX_QUANTITY = 2_000e18;
    uint256 private constant MAX_TRADE_SHARES = 100e18;

    uint256 public qYes;
    uint256 public qNo;
    uint256 public collected;

    function buyYes(uint256 sharesSeed) external {
        _buy(true, sharesSeed);
    }

    function buyNo(uint256 sharesSeed) external {
        _buy(false, sharesSeed);
    }

    function _buy(bool buyYesOutcome, uint256 sharesSeed) private {
        uint256 currentQuantity = buyYesOutcome ? qYes : qNo;
        uint256 remaining = MAX_QUANTITY - currentQuantity;
        uint256 maximumTrade = remaining < MAX_TRADE_SHARES ? remaining : MAX_TRADE_SHARES;
        if (maximumTrade == 0) return;

        uint256 shares = 1 + (sharesSeed % maximumTrade);
        uint256 payment;
        try this.quote(qYes, qNo, buyYesOutcome, shares) returns (uint256 quotedPayment) {
            payment = quotedPayment;
        } catch {
            return;
        }

        collected += payment;
        if (buyYesOutcome) {
            qYes += shares;
        } else {
            qNo += shares;
        }
    }

    function quote(uint256 currentYes, uint256 currentNo, bool buyYesOutcome, uint256 shares)
        external
        pure
        returns (uint256)
    {
        return LMSR.buyCost(currentYes, currentNo, buyYesOutcome, shares);
    }
}

contract LMSRInvariantTest {
    uint256 private constant REQUIRED_SUBSIDY = 34_657_359_027_997_265_471;

    LMSRBuyHandler private handler;

    function setUp() public {
        handler = new LMSRBuyHandler();
    }

    function targetContracts() external view returns (address[] memory targets) {
        targets = new address[](1);
        targets[0] = address(handler);
    }

    /// @dev Foundry probes optional StdInvariant selector methods. The project does
    /// not depend on forge-std, so unsupported probes return an empty ABI array.
    fallback() external {
        assembly ("memory-safe") {
            mstore(0x00, 0x20)
            mstore(0x20, 0)
            return(0x00, 0x40)
        }
    }

    function invariantMarketMakerLossIsBoundedBySubsidy() public view {
        uint256 maximumPayout = handler.qYes() >= handler.qNo() ? handler.qYes() : handler.qNo();
        require(maximumPayout <= handler.collected() + REQUIRED_SUBSIDY, "stateful loss bound exceeded");
    }

    function invariantPaymentsTelescopeToPotentialDifference() public view {
        uint256 expectedCollected = LMSR.cost(handler.qYes(), handler.qNo()) - LMSR.cost(0, 0);
        require(handler.collected() == expectedCollected, "stateful payments do not telescope");
    }
}
