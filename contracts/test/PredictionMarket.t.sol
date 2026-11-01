// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ACONTestToken} from "../src/ACONTestToken.sol";
import {LMSR} from "../src/LMSR.sol";
import {PredictionMarket} from "../src/PredictionMarket.sol";
import {MarketPricing} from "../src/MarketPricing.sol";
import {ResolverRegistry} from "../src/ResolverRegistry.sol";
import {VRFCoordinatorMock} from "./MarketTestBase.sol";

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
    PredictionMarket.DeploymentConfig private config;
    bytes32 private fixtureKey;
    bytes32 private fixtureRevision;

    function setUp() public {
        token = new ACONTestToken();
        config = PredictionMarket.DeploymentConfig({
            paymentToken: address(token),
            pricing: address(new MarketPricing()),
            resolverRegistry: address(new ResolverRegistry(address(this))),
            coordinator: address(new VRFCoordinatorMock()),
            initialAdmin: address(this),
            keyHash: bytes32(uint256(1)),
            subscriptionId: 1,
            callbackGasLimit: 2_000_000
        });
        market = new PredictionMarket(config);
        market.grantRole(market.REGISTRAR_ROLE(), address(this));
        fixtureKey = market.registerFixture(_fixture());
        fixtureRevision = market.getFixture(fixtureKey).revisionHash;
        token.faucet();
        token.approve(address(market), type(uint256).max);
    }

    function testConstructorRejectsZeroPaymentToken() public {
        PredictionMarket.DeploymentConfig memory invalid = config;
        invalid.paymentToken = address(0);
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidConfiguration.selector));
        new PredictionMarket(invalid);
    }

    function testCreateMarketCollectsSubsidyAndStoresMarket() public {
        string memory question = "Will Team A beat Team B?";
        uint256 deadline = block.timestamp + 1 days;

        vm.expectEmit(true, true, true, true, address(market));
        emit PredictionMarket.MarketCreated(0, address(this), question, deadline, fixtureKey);
        uint256 marketId = market.createMarket(fixtureKey, deadline, fixtureRevision);
        PredictionMarket.Market memory data = market.getMarket(marketId);

        require(marketId == 0, "first market id should be zero");
        require(market.marketCount() == 1, "market count should increment");
        require(keccak256(bytes(data.question)) == keccak256(bytes(question)), "question mismatch");
        require(data.tradingDeadline == deadline, "deadline mismatch");
        require(data.state == PredictionMarket.MarketState.OPEN, "new market should be OPEN");
        require(data.creator == address(this), "creator mismatch");
        require(data.yesQuantity == 0 && data.noQuantity == 0, "new market quantities should be zero");
        require(token.balanceOf(address(market)) == market.REQUIRED_SUBSIDY(), "subsidy mismatch");
        require(LMSR.requiredSubsidy() == market.REQUIRED_SUBSIDY(), "subsidy must match LMSR");
    }

    function testRegistrationRejectsEmptyTeamName() public {
        PredictionMarket.FixtureData memory data = _fixture();
        data.teamAName = "";
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidFixture.selector));
        market.registerFixture(data);
    }

    function testCreateMarketRejectsDeadlineInPastOrPresent() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidTradingDeadline.selector));
        market.createMarket(fixtureKey, block.timestamp, fixtureRevision);
    }

    function testCreateMarketRejectsInsufficientCreatorBalanceAtomically() public {
        address unfundedCreator = address(0xBEEF);
        uint256 subsidy = market.REQUIRED_SUBSIDY();
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenBalance.selector, subsidy, 0));
        vm.prank(unfundedCreator);
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);

        require(market.marketCount() == 0, "failed creation must not store a market");
        require(token.balanceOf(address(market)) == 0, "failed creation must not transfer tokens");
    }

    function testCreateMarketRejectsInsufficientCreatorAllowanceAtomically() public {
        token.approve(address(market), 0);

        vm.expectRevert(
            abi.encodeWithSelector(PredictionMarket.InsufficientTokenAllowance.selector, market.REQUIRED_SUBSIDY(), 0)
        );
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);

        require(market.marketCount() == 0, "failed creation must not store a market");
        require(token.balanceOf(address(market)) == 0, "failed creation must not transfer tokens");
    }

    function testGetMarketRejectsUnknownId() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.MarketNotFound.selector, 0));
        market.getMarket(0);
    }

    function testQuoteBuyUsesMathematicalCeilingAndBuyUpdatesYesState() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 shares = 10e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        // Independent high-precision mathematical ceil, not a call to the pricing implementation.
        uint256 expected = 5_249_584_441_082_326_514;
        uint256 balanceBefore = token.balanceOf(address(this));

        require(quote == expected, "quote must round mathematical buy cost up");
        vm.expectEmit(true, true, true, true, address(market));
        emit PredictionMarket.TradeExecuted(0, address(this), 0, shares, quote, shares, 0);
        uint256 charged = market.buy(0, PredictionMarket.Outcome.YES, shares, quote);

        require(charged == quote, "buy cost must match quote");
        require(token.balanceOf(address(this)) == balanceBefore - quote, "buyer payment mismatch");
        require(token.balanceOf(address(market)) == market.REQUIRED_SUBSIDY() + quote, "market collateral mismatch");
        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.YES) == shares, "YES position mismatch");

        PredictionMarket.Market memory data = market.getMarket(0);
        require(data.yesQuantity == shares && data.noQuantity == 0, "post-buy quantities mismatch");
    }

    function testBuyNoUpdatesNoPositionAndQuantity() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 shares = 7e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.NO, shares);

        market.buy(0, PredictionMarket.Outcome.NO, shares, quote);

        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.NO) == shares, "NO position mismatch");
        PredictionMarket.Market memory data = market.getMarket(0);
        require(data.yesQuantity == 0 && data.noQuantity == shares, "post-buy NO quantity mismatch");
    }

    function testRepeatedRealTokenRoundTripsCannotIncreaseWalletBalance() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 beforeBalance = token.balanceOf(address(this));
        for (uint256 i; i < 16; ++i) {
            uint256 cost = market.quoteBuy(0, PredictionMarket.Outcome.YES, 10e18);
            market.buy(0, PredictionMarket.Outcome.YES, 10e18, cost);
            uint256 proceeds = market.quoteSell(0, PredictionMarket.Outcome.YES, 10e18);
            market.sell(0, PredictionMarket.Outcome.YES, 10e18, proceeds);
        }
        require(token.balanceOf(address(this)) == beforeBalance - 16, "repeated rounding gain");
        PredictionMarket.Market memory data = market.getMarket(0);
        require(data.yesQuantity == 0 && data.noQuantity == 0, "round trip retained shares");
        require(data.collateralBalance == market.REQUIRED_SUBSIDY() + 16, "rounding reserve mismatch");
        require(token.balanceOf(address(market)) == data.collateralBalance, "token ledger mismatch");
    }

    function testBaseUnitBuyRoundsUpAndZeroProceedsSellPreservesShares() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 beforeBalance = token.balanceOf(address(this));
        require(market.buy(0, PredictionMarket.Outcome.YES, 1, 1) == 1, "sub-base-unit buy must round up");
        vm.expectRevert(abi.encodeWithSelector(LMSR.TradeTooSmall.selector));
        market.sell(0, PredictionMarket.Outcome.YES, 1, 0);
        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.YES) == 1, "zero sell burned shares");
        require(token.balanceOf(address(this)) == beforeBalance - 1, "zero sell moved tokens");
        require(market.getMarket(0).collateralBalance == market.REQUIRED_SUBSIDY() + 1, "zero sell changed collateral");
    }

    function testStaleQuoteExceedingMaxCostRevertsAtomically() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 shares = 10e18;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        uint256 balanceBefore = token.balanceOf(address(this));

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.SlippageExceeded.selector, quote, quote - 1));
        market.buy(0, PredictionMarket.Outcome.YES, shares, quote - 1);

        require(token.balanceOf(address(this)) == balanceBefore, "failed buy must not charge tokens");
        require(market.balanceOf(0, address(this), PredictionMarket.Outcome.YES) == 0, "failed buy must not add shares");
    }

    function testBuyRejectsInsufficientBalance() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        address unfundedTrader = address(0xCAFE);
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, WAD);
        vm.prank(unfundedTrader);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenBalance.selector, quote, 0));
        market.buy(0, PredictionMarket.Outcome.YES, WAD, quote);
    }

    function testBuyRejectsInsufficientAllowance() public {
        market.createMarket(fixtureKey, block.timestamp + 1 days, fixtureRevision);
        uint256 shares = WAD;
        uint256 quote = market.quoteBuy(0, PredictionMarket.Outcome.YES, shares);
        token.approve(address(market), quote - 1);

        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InsufficientTokenAllowance.selector, quote, quote - 1));
        market.buy(0, PredictionMarket.Outcome.YES, shares, quote);
    }

    function testQuoteAndBuyRejectAtTradingDeadline() public {
        uint256 deadline = block.timestamp + 1 days;
        market.createMarket(fixtureKey, deadline, fixtureRevision);
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

    function _fixture() private view returns (PredictionMarket.FixtureData memory) {
        return PredictionMarket.FixtureData({
            providerId: "manual",
            gameId: "valorant",
            externalMatchId: "token-integration",
            teamAId: "a",
            teamBId: "b",
            teamAName: "Team A",
            teamBName: "Team B",
            scheduledStart: block.timestamp + 2 days,
            evidenceHash: keccak256("fixture"),
            evidenceURI: "https://example.invalid/fixture"
        });
    }
}
