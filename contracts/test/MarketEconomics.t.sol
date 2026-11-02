// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketPricing} from "../src/MarketPricing.sol";
import {PredictionMarket} from "../src/PredictionMarket.sol";
import {MarketTestBase} from "./MarketTestBase.sol";

struct FuzzSelector {
    address addr;
    bytes4[] selectors;
}

/// @notice Locks the M4 rule to mathematical floor-sell / ceiling-buy rounding.
contract MarketPricingSemanticsTest {
    function testSellFloorsAndReverseBuyCeilsTheMathematicalDifference() public {
        MarketPricing pricing = new MarketPricing();

        uint256 proceeds = pricing.sellReturn(50e18, 50e18, true, 10e18);
        uint256 buyBack = pricing.buyCost(40e18, 50e18, true, 10e18);

        // Independent 160/220-digit references fix the mathematical result between
        // these two states. The sale floors it and the reverse buy ceilings it, so
        // the inverse pair retains exactly one base unit in collateral.
        require(proceeds == 4_750_415_558_917_673_486, "unexpected mathematical floor");
        require(buyBack == 4_750_415_558_917_673_487, "unexpected mathematical ceiling");
        require(buyBack == proceeds + 1, "inverse trade did not retain rounding residue");
    }
}

/// @notice Stateful handler for reachable OPEN-market buy/sell accounting.
contract MarketTradingHandler is MarketTestBase {
    uint256 private constant INITIAL_MINTED = 50_000e18;
    uint256 private constant MAX_TRADE = 100e18;
    uint256 private constant MAX_QUANTITY = 2_000e18;
    bool private initialized;

    function setUp() public override {
        if (initialized) return;
        initialized = true;
        super.setUp();
        _create(0);
        _create(1);
    }

    function buyYes(uint256 marketSeed, uint256 actorSeed, uint256 sharesSeed) external {
        _buyAction(marketSeed, actorSeed, PredictionMarket.Outcome.YES, sharesSeed);
    }

    function buyNo(uint256 marketSeed, uint256 actorSeed, uint256 sharesSeed) external {
        _buyAction(marketSeed, actorSeed, PredictionMarket.Outcome.NO, sharesSeed);
    }

    function sellYes(uint256 marketSeed, uint256 actorSeed, uint256 sharesSeed) external {
        _sellAction(marketSeed, actorSeed, PredictionMarket.Outcome.YES, sharesSeed);
    }

    function sellNo(uint256 marketSeed, uint256 actorSeed, uint256 sharesSeed) external {
        _sellAction(marketSeed, actorSeed, PredictionMarket.Outcome.NO, sharesSeed);
    }

    function assertTradingInvariants() external view {
        uint256 subsidy = market.REQUIRED_SUBSIDY();
        uint256 collateralSum;

        for (uint256 id; id < 2; ++id) {
            PredictionMarket.Market memory data = market.getMarket(id);
            uint256 yesHeld = market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES)
                + market.balanceOf(id, OTHER, PredictionMarket.Outcome.YES);
            uint256 noHeld = market.balanceOf(id, TRADER, PredictionMarket.Outcome.NO)
                + market.balanceOf(id, OTHER, PredictionMarket.Outcome.NO);
            require(data.yesQuantity == yesHeld, "YES quantity is not conserved");
            require(data.noQuantity == noHeld, "NO quantity is not conserved");

            uint256 winningCeiling = data.yesQuantity >= data.noQuantity ? data.yesQuantity : data.noQuantity;
            uint256 total = data.yesQuantity + data.noQuantity;
            uint256 voidCeiling = total / 2 + total % 2;
            require(data.collateralBalance >= subsidy, "successful trade rounding consumed subsidy");
            require(data.collateralBalance >= winningCeiling, "winning liability is underfunded");
            require(data.collateralBalance >= voidCeiling, "VOID liability is underfunded");
            collateralSum += data.collateralBalance;
        }

        require(collateralSum == market.totalCollateral(), "market collateral is not isolated");
        require(market.totalChallengeBonds() == 0, "trading handler created a challenge bond");
        require(token.balanceOf(address(market)) == collateralSum, "contract token ledger mismatch");
        require(_knownBalances() == INITIAL_MINTED, "token conservation failed");
    }

    function _buyAction(uint256 marketSeed, uint256 actorSeed, PredictionMarket.Outcome outcome, uint256 sharesSeed)
        private
    {
        uint256 id = marketSeed % 2;
        address actor = _actor(actorSeed);
        PredictionMarket.Market memory beforeMarket = market.getMarket(id);
        uint256 current = outcome == PredictionMarket.Outcome.YES ? beforeMarket.yesQuantity : beforeMarket.noQuantity;
        if (current >= MAX_QUANTITY) return;
        uint256 available = MAX_QUANTITY - current;
        uint256 maximum = available < MAX_TRADE ? available : MAX_TRADE;
        uint256 shares = 1 + (sharesSeed % maximum);

        try market.quoteBuy(id, outcome, shares) returns (uint256 quote) {
            uint256 otherId = 1 - id;
            uint256 otherCollateral = market.getMarket(otherId).collateralBalance;
            uint256 selectedCollateral = beforeMarket.collateralBalance;
            vm.prank(actor);
            uint256 paid = market.buy(id, outcome, shares, quote);
            require(paid == quote, "buy did not use the quoted ceiling");
            require(
                market.getMarket(id).collateralBalance == selectedCollateral + quote,
                "buy collateral did not increase by rounded payment"
            );
            require(market.getMarket(otherId).collateralBalance == otherCollateral, "buy crossed markets");
        } catch {}
    }

    function _sellAction(uint256 marketSeed, uint256 actorSeed, PredictionMarket.Outcome outcome, uint256 sharesSeed)
        private
    {
        uint256 id = marketSeed % 2;
        address actor = _actor(actorSeed);
        uint256 owned = market.balanceOf(id, actor, outcome);
        if (owned == 0) return;
        uint256 maximum = owned < MAX_TRADE ? owned : MAX_TRADE;
        uint256 shares = 1 + (sharesSeed % maximum);

        try market.quoteSell(id, outcome, shares) returns (uint256 quote) {
            uint256 otherId = 1 - id;
            uint256 otherCollateral = market.getMarket(otherId).collateralBalance;
            uint256 selectedCollateral = market.getMarket(id).collateralBalance;
            vm.prank(actor);
            uint256 paid = market.sell(id, outcome, shares, quote);
            require(paid == quote, "sell did not use the quoted floor");
            require(
                market.getMarket(id).collateralBalance + quote == selectedCollateral,
                "sell collateral did not decrease by rounded proceeds"
            );
            require(market.getMarket(otherId).collateralBalance == otherCollateral, "sell crossed markets");
        } catch {}
    }

    function _actor(uint256 seed) private pure returns (address) {
        return seed % 2 == 0 ? TRADER : OTHER;
    }

    function _knownBalances() private view returns (uint256) {
        return token.balanceOf(CREATOR) + token.balanceOf(PROPOSER) + token.balanceOf(CHALLENGER)
            + token.balanceOf(TRADER) + token.balanceOf(OTHER) + token.balanceOf(address(market));
    }
}

contract MarketTradingInvariantTest {
    MarketTradingHandler private handler;

    function setUp() public {
        handler = new MarketTradingHandler();
        handler.setUp();
    }

    function targetContracts() external view returns (address[] memory targets) {
        targets = new address[](1);
        targets[0] = address(handler);
    }

    function targetSelectors() external view returns (FuzzSelector[] memory targeted) {
        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = MarketTradingHandler.buyYes.selector;
        selectors[1] = MarketTradingHandler.buyNo.selector;
        selectors[2] = MarketTradingHandler.sellYes.selector;
        selectors[3] = MarketTradingHandler.sellNo.selector;
        targeted = new FuzzSelector[](1);
        targeted[0] = FuzzSelector({addr: address(handler), selectors: selectors});
    }

    fallback() external {
        assembly ("memory-safe") {
            mstore(0x00, 0x20)
            mstore(0x20, 0)
            return(0x00, 0x40)
        }
    }

    function invariantRepeatedBuysAndSellsPreserveEconomics() public view {
        handler.assertTradingInvariants();
    }
}

/// @notice Stateful handler for terminal liabilities, claims, surplus and bonds.
contract MarketSettlementHandler is MarketTestBase {
    uint256 private constant INITIAL_MINTED = 50_000e18;
    bool private initialized;

    function setUp() public override {
        if (initialized) return;
        initialized = true;
        super.setUp();
        for (uint256 id; id < 4; ++id) {
            _create(id);
        }

        _buy(TRADER, 0, PredictionMarket.Outcome.YES, 10e18);
        _buy(OTHER, 0, PredictionMarket.Outcome.NO, 7e18);
        _buy(TRADER, 1, PredictionMarket.Outcome.YES, 4e18);
        _buy(OTHER, 1, PredictionMarket.Outcome.NO, 9e18);
        _buy(TRADER, 2, PredictionMarket.Outcome.YES, 5e18 + 1);
        _buy(TRADER, 2, PredictionMarket.Outcome.NO, 2e18);
        _buy(OTHER, 2, PredictionMarket.Outcome.YES, 3e18);
        _buy(OTHER, 2, PredictionMarket.Outcome.NO, 6e18 + 1);
        _buy(TRADER, 3, PredictionMarket.Outcome.YES, 8e18);
        _buy(OTHER, 3, PredictionMarket.Outcome.NO, 6e18);

        vm.warp(market.getMarket(0).tradingDeadline);
        _proposeWithoutWarp(0, PredictionMarket.ResolutionChoice.YES);
        _proposeWithoutWarp(1, PredictionMarket.ResolutionChoice.NO);
        _proposeWithoutWarp(2, PredictionMarket.ResolutionChoice.VOID);
        _proposeWithoutWarp(3, PredictionMarket.ResolutionChoice.YES);
        vm.prank(CHALLENGER);
        market.challengeOutcome(3, keccak256("stateful-bond"));

        vm.warp(market.getResolution(0).challengeDeadline);
        market.finalize(0);
        market.finalize(1);
        market.finalize(2);
    }

    function claim(uint256 marketSeed, uint256 actorSeed) external {
        uint256 id = marketSeed % 4;
        address actor = _actor(actorSeed);
        PredictionMarket.Resolution memory resolution = market.getResolution(id);
        if (!resolution.terminal || market.hasClaimed(id, actor)) return;
        uint256 yes = market.balanceOf(id, actor, PredictionMarket.Outcome.YES);
        uint256 no = market.balanceOf(id, actor, PredictionMarket.Outcome.NO);
        if (yes + no == 0) return;

        uint256 expected = resolution.finalOutcome == PredictionMarket.ResolutionChoice.VOID
            ? (yes + no) / 2
            : resolution.finalOutcome == PredictionMarket.ResolutionChoice.YES ? yes : no;
        uint256 recipientBefore = token.balanceOf(actor);
        uint256 selectedBefore = market.getMarket(id).collateralBalance;
        uint256[4] memory otherBefore = _collateralSnapshot();
        vm.prank(actor);
        uint256 paid = market.claimPayout(id);
        require(paid == expected, "claim used wrong payout units");
        require(token.balanceOf(actor) == recipientBefore + expected, "claim transferred wrong amount");
        require(market.getMarket(id).collateralBalance + expected == selectedBefore, "claim collateral mismatch");
        _requireOtherMarketsUnchanged(id, otherBefore);
    }

    function attemptDuplicateClaim(uint256 marketSeed, uint256 actorSeed) external {
        uint256 id = marketSeed % 4;
        address actor = _actor(actorSeed);
        if (!market.hasClaimed(id, actor)) return;
        vm.prank(actor);
        (bool success,) = address(market).call(abi.encodeCall(market.claimPayout, (id)));
        require(!success, "duplicate claim succeeded");
    }

    function withdrawSurplus(uint256 marketSeed) external {
        uint256 id = marketSeed % 4;
        uint256 amount = market.withdrawableSurplus(id);
        if (amount == 0) return;
        uint256[4] memory otherBefore = _collateralSnapshot();
        vm.prank(CREATOR);
        require(market.withdrawCreatorSurplus(id) == amount, "wrong creator surplus");
        _requireOtherMarketsUnchanged(id, otherBefore);
    }

    function settleBondedMarket(uint256 outcomeSeed, uint256 word) external {
        if (market.getMarket(3).state != PredictionMarket.MarketState.DISPUTED) return;
        uint256 challengerBefore = token.balanceOf(CHALLENGER);
        market.requestResolverSelection(3);
        uint256 requestId = market.getResolverRound(3, 1).currentRequestId;
        vrf.fulfill(market, requestId, word);
        PredictionMarket.ResolutionChoice outcome = PredictionMarket.ResolutionChoice(outcomeSeed % 3);
        _quorum(3, outcome);
        require(market.totalChallengeBonds() == 0, "settled bond remains escrowed");
        if (outcome == PredictionMarket.ResolutionChoice.YES) {
            require(token.balanceOf(CHALLENGER) == challengerBefore, "upheld bond was refunded");
        } else {
            require(token.balanceOf(CHALLENGER) == challengerBefore + market.CHALLENGE_BOND(), "bond not refunded");
        }
    }

    function assertSettlementInvariants() external view {
        uint256 collateralSum;
        for (uint256 id; id < 4; ++id) {
            PredictionMarket.Market memory data = market.getMarket(id);
            uint256 yesHeld = market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES)
                + market.balanceOf(id, OTHER, PredictionMarket.Outcome.YES);
            uint256 noHeld = market.balanceOf(id, TRADER, PredictionMarket.Outcome.NO)
                + market.balanceOf(id, OTHER, PredictionMarket.Outcome.NO);
            require(data.yesQuantity == yesHeld, "settlement YES quantity mismatch");
            require(data.noQuantity == noHeld, "settlement NO quantity mismatch");
            require(data.collateralBalance >= market.remainingLiability(id), "remaining liability is underfunded");
            collateralSum += data.collateralBalance;

            if (market.hasClaimed(id, TRADER)) {
                require(
                    market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 0
                        && market.balanceOf(id, TRADER, PredictionMarket.Outcome.NO) == 0
                        && market.claimableAmount(id, TRADER) == 0,
                    "TRADER claim was not consumed"
                );
            }
            if (market.hasClaimed(id, OTHER)) {
                require(
                    market.balanceOf(id, OTHER, PredictionMarket.Outcome.YES) == 0
                        && market.balanceOf(id, OTHER, PredictionMarket.Outcome.NO) == 0
                        && market.claimableAmount(id, OTHER) == 0,
                    "OTHER claim was not consumed"
                );
            }
        }

        require(collateralSum == market.totalCollateral(), "settlement markets are not isolated");
        require(
            market.totalChallengeBonds() == market.getResolution(3).bondEscrow,
            "challenge bond is not separately accounted"
        );
        require(
            token.balanceOf(address(market)) == market.totalCollateral() + market.totalChallengeBonds(),
            "settlement token ledger mismatch"
        );
        require(_knownBalances() == INITIAL_MINTED, "settlement token conservation failed");
    }

    function _proposeWithoutWarp(uint256 id, PredictionMarket.ResolutionChoice outcome) private {
        vm.prank(PROPOSER);
        market.proposeOutcome(id, outcome, keccak256(abi.encode("result", id)), "https://example.invalid/result");
    }

    function _actor(uint256 seed) private pure returns (address) {
        return seed % 2 == 0 ? TRADER : OTHER;
    }

    function _collateralSnapshot() private view returns (uint256[4] memory values) {
        for (uint256 id; id < 4; ++id) {
            values[id] = market.getMarket(id).collateralBalance;
        }
    }

    function _requireOtherMarketsUnchanged(uint256 selected, uint256[4] memory beforeValues) private view {
        for (uint256 id; id < 4; ++id) {
            if (id != selected) {
                require(market.getMarket(id).collateralBalance == beforeValues[id], "operation crossed markets");
            }
        }
    }

    function _knownBalances() private view returns (uint256) {
        return token.balanceOf(CREATOR) + token.balanceOf(PROPOSER) + token.balanceOf(CHALLENGER)
            + token.balanceOf(TRADER) + token.balanceOf(OTHER) + token.balanceOf(address(market));
    }
}

contract MarketSettlementInvariantTest {
    MarketSettlementHandler private handler;

    function setUp() public {
        handler = new MarketSettlementHandler();
        handler.setUp();
    }

    function targetContracts() external view returns (address[] memory targets) {
        targets = new address[](1);
        targets[0] = address(handler);
    }

    function targetSelectors() external view returns (FuzzSelector[] memory targeted) {
        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = MarketSettlementHandler.claim.selector;
        selectors[1] = MarketSettlementHandler.attemptDuplicateClaim.selector;
        selectors[2] = MarketSettlementHandler.withdrawSurplus.selector;
        selectors[3] = MarketSettlementHandler.settleBondedMarket.selector;
        targeted = new FuzzSelector[](1);
        targeted[0] = FuzzSelector({addr: address(handler), selectors: selectors});
    }

    fallback() external {
        assembly ("memory-safe") {
            mstore(0x00, 0x20)
            mstore(0x20, 0)
            return(0x00, 0x40)
        }
    }

    function invariantClaimsBondsAndSurplusPreserveLiabilities() public view {
        handler.assertSettlementInvariants();
    }
}
