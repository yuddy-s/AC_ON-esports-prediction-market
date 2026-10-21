// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ACONTestToken} from "../src/ACONTestToken.sol";
import {LMSR} from "../src/LMSR.sol";
import {PredictionMarket} from "../src/PredictionMarket.sol";

interface VmMarketTest {
    function warp(uint256 timestamp) external;
    function prank(address caller) external;
    function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData, address emitter) external;
    function expectRevert(bytes calldata revertData) external;
}

contract PredictionMarketTest {
    VmMarketTest private constant vm = VmMarketTest(address(uint160(uint256(keccak256("hevm cheat code")))));
    uint256 private constant WAD = 1e18;

    ACONTestToken private token;
    PredictionMarket private market;

    function setUp() public {
        token = new ACONTestToken();
        market = new PredictionMarket(address(token));
        token.faucet();
        token.approve(address(market), type(uint256).max);
    }

    function testConstructorRejectsZeroPaymentToken() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidPaymentToken.selector));
        new PredictionMarket(address(0));
    }

    function testCreateMarketCollectsSubsidyAndStoresMarket() public {
        string memory question = "Will Team A beat Team B?";
        uint256 deadline = block.timestamp + 1 days;

        vm.expectEmit(true, true, false, true, address(market));
        emit PredictionMarket.MarketCreated(0, address(this), question, deadline);
        uint256 marketId = market.createMarket(question, deadline);

        (
            string memory storedQuestion,
            uint256 storedDeadline,
            PredictionMarket.MarketState state,
            address creator,
            uint256 yesQuantity,
            uint256 noQuantity
        ) = market.getMarket(marketId);

        require(marketId == 0, "first market id should be zero");
        require(market.marketCount() == 1, "market count should increment");
        require(keccak256(bytes(storedQuestion)) == keccak256(bytes(question)), "question mismatch");
        require(storedDeadline == deadline, "deadline mismatch");
        require(state == PredictionMarket.MarketState.OPEN, "new market should be OPEN");
        require(creator == address(this), "creator mismatch");
        require(yesQuantity == 0 && noQuantity == 0, "new market quantities should be zero");
        require(token.balanceOf(address(market)) == market.REQUIRED_SUBSIDY(), "subsidy mismatch");
        require(LMSR.requiredSubsidy() == market.REQUIRED_SUBSIDY(), "subsidy must match LMSR");
    }

    function testCreateMarketRejectsEmptyQuestion() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.EmptyQuestion.selector));
        market.createMarket("", block.timestamp + 1 days);
    }

    function testCreateMarketRejectsDeadlineInPastOrPresent() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidTradingDeadline.selector));
        market.createMarket("Will Team A beat Team B?", block.timestamp);
    }

    function testCreateMarketRejectsInsufficientCreatorBalanceAtomically() public {
        address unfundedCreator = address(0xBEEF);
        uint256 subsidy = market.REQUIRED_SUBSIDY();
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenBalance.selector, subsidy, 0));
        vm.prank(unfundedCreator);
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);

        require(market.marketCount() == 0, "failed creation must not store a market");
        require(token.balanceOf(address(market)) == 0, "failed creation must not transfer tokens");
    }

    function testCreateMarketRejectsInsufficientCreatorAllowanceAtomically() public {
        token.approve(address(market), 0);

        vm.expectRevert(
            abi.encodeWithSelector(PredictionMarket.InsufficientTokenAllowance.selector, market.REQUIRED_SUBSIDY(), 0)
        );
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);

        require(market.marketCount() == 0, "failed creation must not store a market");
        require(token.balanceOf(address(market)) == 0, "failed creation must not transfer tokens");
    }

    function testGetMarketRejectsUnknownId() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.MarketNotFound.selector, 0));
        market.getMarket(0);
    }

    function testQuoteBuyMatchesLmsrCostAndBuyUpdatesYesState() public {
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);
        uint256 shares = 10e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        uint256 expected = LMSR.buyCost(0, 0, true, shares);
        uint256 balanceBefore = token.balanceOf(address(this));

        require(quote == expected, "quote must use LMSR buyCost");
        vm.expectEmit(true, true, true, true, address(market));
        emit PredictionMarket.TradeExecuted(0, address(this), 0, shares, quote, shares, 0);
        uint256 charged = market.buy(0, PredictionMarket.Outcome.YES, shares, quote);

        require(charged == quote, "buy cost must match quote");
        require(token.balanceOf(address(this)) == balanceBefore - quote, "buyer payment mismatch");
        require(token.balanceOf(address(market)) == market.REQUIRED_SUBSIDY() + quote, "market collateral mismatch");
        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.YES) == shares, "YES position mismatch");

        (,,,, uint256 yesQuantity, uint256 noQuantity) = market.getMarket(0);
        require(yesQuantity == shares && noQuantity == 0, "post-buy quantities mismatch");
    }

    function testBuyNoUpdatesNoPositionAndQuantity() public {
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);
        uint256 shares = 7e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.NO, shares);

        market.buy(0, PredictionMarket.Outcome.NO, shares, quote);

        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.NO) == shares, "NO position mismatch");
        (,,,, uint256 yesQuantity, uint256 noQuantity) = market.getMarket(0);
        require(yesQuantity == 0 && noQuantity == shares, "post-buy NO quantity mismatch");
    }

    function testStaleQuoteExceedingMaxCostRevertsAtomically() public {
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);
        uint256 shares = 10e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        uint256 balanceBefore = token.balanceOf(address(this));

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.SlippageExceeded.selector, quote, quote - 1));
        market.buy(0, PredictionMarket.Outcome.YES, shares, quote - 1);

        require(token.balanceOf(address(this)) == balanceBefore, "failed buy must not charge tokens");
        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.YES) == 0, "failed buy must not add shares");
    }

    function testBuyRejectsInsufficientBalance() public {
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);
        address unfundedTrader = address(0xCAFE);
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, WAD);
        vm.prank(unfundedTrader);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenBalance.selector, quote, 0));
        market.buy(0, PredictionMarket.Outcome.YES, WAD, quote);
    }

    function testBuyRejectsInsufficientAllowance() public {
        market.createMarket("Will Team A beat Team B?", block.timestamp + 1 days);
        uint256 shares = WAD;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        token.approve(address(market), quote - 1);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenAllowance.selector, quote, quote - 1));
        market.buy(0, PredictionMarket.Outcome.YES, shares, quote);
    }

    function testQuoteAndBuyRejectAtTradingDeadline() public {
        uint256 deadline = block.timestamp + 1 days;
        market.createMarket("Will Team C beat Team D?", deadline);
        vm.warp(deadline);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.TradingClosed.selector));
        market.quoteBuy(0, PredictionMarket.Outcome.YES, WAD);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.TradingClosed.selector));
        market.buy(0, PredictionMarket.Outcome.YES, WAD, type(uint256).max);
    }

    function testQuoteRejectsUnknownMarket() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.MarketNotFound.selector, 0));
        market.quoteBuy(0, PredictionMarket.Outcome.YES, WAD);
    }
}
