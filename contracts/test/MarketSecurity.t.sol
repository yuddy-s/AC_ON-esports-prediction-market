// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketTestBase, VmMarket, MarketAccess, PredictionMarket} from "./MarketTestBase.sol";

contract MarketSecurityTest is MarketTestBase {
    function testRawOutOfRangeOutcomesCannotReachTradeOrVoteAccounting() public {
        uint256 id = _create(0);
        vm.prank(TRADER);
        (bool traded,) =
            address(market).call(abi.encodeWithSignature("buy(uint256,uint8,uint256,uint256)", id, uint8(2), WAD, WAD));
        require(!traded && market.getMarket(id).yesQuantity == 0, "invalid trade outcome accepted");
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 1);
        address resolver = market.getResolverRound(id, 1).committee[0];
        vm.prank(resolver);
        (bool voted,) = address(market).call(abi.encodeWithSignature("voteOnOutcome(uint256,uint8)", id, uint8(3)));
        require(!voted && !market.hasVoted(id, 1, resolver), "invalid resolver choice accepted");
    }

    function testFalseReturningIncomingTransferRollsBackTokenAndMarketState() public {
        bytes32 key = _register(0);
        bytes32 revision = market.getFixture(key).revisionHash;
        uint256 subsidy = market.REQUIRED_SUBSIDY();
        vm.prank(CREATOR);
        token.approve(address(market), subsidy);
        uint256 beforeBalance = token.balanceOf(CREATOR);
        token.setFailures(true, false, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(CREATOR);
        market.createMarket(key, block.timestamp + 1 days, revision);
        require(
            token.balanceOf(CREATOR) == beforeBalance && token.balanceOf(address(market)) == 0,
            "token transfer not rolled back"
        );
        require(token.allowance(CREATOR, address(market)) == subsidy, "allowance not rolled back");
        require(market.marketCount() == 0 && !market.getFixture(key).hasMarket, "market state survived failure");
    }

    function testBuyPaymentFailureDoesNotCreateSharesOrParticipation() public {
        uint256 id = _create(0);
        uint256 cost = market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        uint256 beforeBalance = token.balanceOf(TRADER);
        bytes32 beforeMarket = keccak256(abi.encode(market.getMarket(id)));
        token.setFailures(true, false, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(TRADER);
        market.buy(id, PredictionMarket.Outcome.YES, WAD, cost);
        require(keccak256(abi.encode(market.getMarket(id))) == beforeMarket, "failed buy changed market");
        require(token.balanceOf(TRADER) == beforeBalance && !market.hasTraded(id, TRADER), "failed buy changed trader");
        require(market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 0, "failed buy credited shares");
    }

    function testFeeLikeIncomingTransferIsRejectedAtomically() public {
        bytes32 key = _register(0);
        bytes32 revision = market.getFixture(key).revisionHash;
        token.setSkim(true);
        vm.expectRevert(PredictionMarket.UnexpectedTokenTransfer.selector);
        vm.prank(CREATOR);
        market.createMarket(key, block.timestamp + 1 days, revision);
        require(market.marketCount() == 0 && token.balanceOf(address(market)) == 0, "fee token partially funded market");
    }

    function testSellTransferFailureRestoresPositionsCollateralAndPayment() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        uint256 quote = market.quoteSell(id, PredictionMarket.Outcome.YES, 5e18);
        bytes32 beforeMarket = keccak256(abi.encode(market.getMarket(id)));
        uint256 beforeBalance = token.balanceOf(TRADER);
        token.setFailures(false, true, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, 5e18, quote);
        require(keccak256(abi.encode(market.getMarket(id))) == beforeMarket, "failed sell changed market");
        require(
            token.balanceOf(TRADER) == beforeBalance
                && market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 10e18,
            "failed sell changed holdings"
        );
        _accounting();
    }

    function testRealCompetingTradeInvalidatesSellMinimumReturn() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        uint256 stale = market.quoteSell(id, PredictionMarket.Outcome.YES, 10e18);
        _buy(OTHER, id, PredictionMarket.Outcome.NO, 20e18);
        require(
            market.quoteSell(id, PredictionMarket.Outcome.YES, 10e18) < stale, "competing trade did not lower return"
        );
        vm.expectPartialRevert(PredictionMarket.MinimumReturnNotMet.selector);
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, 10e18, stale);
        require(market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 10e18, "stale sell consumed shares");
        _accounting();
    }

    function testClaimTransferFailureRestoresClaimedFlagAndAllEntitlements() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
        bytes32 beforeMarket = keccak256(abi.encode(market.getMarket(id)));
        token.setFailures(false, true, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(TRADER);
        market.claimPayout(id);
        require(
            !market.hasClaimed(id, TRADER) && market.claimableAmount(id, TRADER) == 10e18,
            "failed claim consumed entitlement"
        );
        require(keccak256(abi.encode(market.getMarket(id))) == beforeMarket, "failed claim changed quantities");
        token.setFailures(false, false, false);
        vm.prank(TRADER);
        require(market.claimPayout(id) == 10e18, "legitimate retry failed");
        _accounting();
    }

    function testBondRefundFailureRollsBackThirdVoteAndFinalization() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 123);
        PredictionMarket.ResolverRound memory round = market.getResolverRound(id, 1);
        vm.prank(round.committee[0]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.NO);
        vm.prank(round.committee[1]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.NO);
        token.setFailures(false, true, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(round.committee[2]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.NO);
        require(
            !market.hasVoted(id, 1, round.committee[2]) && market.getResolverRound(id, 1).voteCounts[1] == 2,
            "failed refund kept vote"
        );
        require(
            !market.getResolution(id).terminal && market.totalChallengeBonds() == 10e18,
            "failed refund finalized or consumed bond"
        );
        _state(id, PredictionMarket.MarketState.RESOLVER_VOTING);
        token.setFailures(false, false, false);
        vm.prank(round.committee[2]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.NO);
        _state(id, PredictionMarket.MarketState.FINALIZED);
        _accounting();
    }

    function testSurplusTransferFailureRestoresCreatorReserve() public {
        uint256 id = _create(0);
        _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
        uint256 surplus = market.withdrawableSurplus(id);
        token.setFailures(false, true, true);
        vm.expectRevert(PredictionMarket.PaymentTransferFailed.selector);
        vm.prank(CREATOR);
        market.withdrawCreatorSurplus(id);
        require(market.withdrawableSurplus(id) == surplus, "failed withdrawal consumed surplus");
        _accounting();
    }

    function testIncomingCallbackCannotReenterAnyMarketMutator() public {
        uint256 id = _create(0);
        token.setCallback(address(market), abi.encodeCall(market.closeTrading, (id, bytes32(uint256(1)))), true, false);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        require(
            !token.callbackSucceeded() && bytes4(token.callbackResult()) == PredictionMarket.ReentrantCall.selector,
            "incoming callback bypassed guard"
        );
        _state(id, PredictionMarket.MarketState.OPEN);
        _accounting();
    }

    function testOutgoingCallbackCannotReenterClaimOrSell() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
        token.setCallback(address(market), abi.encodeCall(market.claimPayout, (id)), false, true);
        vm.prank(TRADER);
        market.claimPayout(id);
        require(
            !token.callbackSucceeded() && bytes4(token.callbackResult()) == PredictionMarket.ReentrantCall.selector,
            "outgoing callback bypassed guard"
        );
        require(market.hasClaimed(id, TRADER) && market.claimableAmount(id, TRADER) == 0, "claim duplicated");
        _accounting();
    }

    function testMarketsCannotWithdrawEachOthersCollateral() public {
        uint256 a = _create(0);
        uint256 b = _create(1);
        _buy(TRADER, a, PredictionMarket.Outcome.YES, 10e18);
        _buy(TRADER, b, PredictionMarket.Outcome.NO, 7e18);
        bytes32 beforeB = keccak256(abi.encode(market.getMarket(b)));
        _unchallenged(a, PredictionMarket.ResolutionChoice.NO);
        vm.prank(CREATOR);
        market.withdrawCreatorSurplus(a);
        require(keccak256(abi.encode(market.getMarket(b))) == beforeB, "cross-market state changed");
        require(
            market.balanceOf(b, TRADER, PredictionMarket.Outcome.NO) == 7e18 && market.withdrawableSurplus(b) == 0,
            "cross-market funds exposed"
        );
        _accounting();
    }

    function testEveryRegistrarWhoEditedFixtureRemainsExcluded() public {
        bytes32 key = _register(0);
        market.grantRole(market.REGISTRAR_ROLE(), OTHER);
        PredictionMarket.FixtureData memory data = _data(0);
        data.teamAName = "Corrected A";
        vm.prank(OTHER);
        market.registerFixture(data);
        bytes32 revision = market.getFixture(key).revisionHash;
        vm.prank(CREATOR);
        uint256 id = market.createMarket(key, block.timestamp + 1 days, revision);
        registry.setResolverStatus(REGISTRAR, true);
        registry.setResolverStatus(OTHER, true);
        require(
            !market.isResolverEligible(id, REGISTRAR) && !market.isResolverEligible(id, OTHER),
            "registrar rotation erased conflict"
        );
    }

    function testAdminCannotRewriteProposalOrClaimUserFunds() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, WAD);
        _proposal(id, PredictionMarket.ResolutionChoice.YES);
        market.revokeRole(market.PROPOSER_ROLE(), PROPOSER);
        market.grantRole(market.PROPOSER_ROLE(), OTHER);
        vm.expectRevert(PredictionMarket.ProposalAlreadyExists.selector);
        vm.prank(OTHER);
        market.proposeOutcome(id, PredictionMarket.ResolutionChoice.NO, keccak256("changed"), "uri");
        vm.warp(market.getResolution(id).challengeDeadline);
        market.finalize(id);
        vm.expectRevert(PredictionMarket.NoPosition.selector);
        market.claimPayout(id);
        vm.expectRevert(PredictionMarket.CreatorOnly.selector);
        market.withdrawCreatorSurplus(id);
        require(market.claimableAmount(id, TRADER) == WAD, "admin changed user entitlement");
    }

    function testDefaultAdministrationCannotBeDuplicatedOrAccidentallyRenounced() public {
        vm.expectRevert(MarketAccess.UseAdministrationTransfer.selector);
        market.grantRole(bytes32(0), OTHER);
        vm.expectRevert(MarketAccess.UseAdministrationTransfer.selector);
        market.renounceRole(bytes32(0));
        vm.expectRevert(MarketAccess.ZeroAddress.selector);
        market.transferAdministration(address(0));
        require(market.admin() == address(this), "administration lost");
    }

    function testTradeAndSellEventsMatchPostTransactionState() public {
        uint256 id = _create(0);
        vm.recordLogs();
        uint256 cost = _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        VmMarket.Log[] memory logs = vm.getRecordedLogs();
        require(
            logs.length == 1
                && logs[0].topics[0]
                    == keccak256("TradeExecuted(uint256,address,uint8,uint256,uint256,uint256,uint256)"),
            "trade event"
        );
        (uint256 shares, uint256 amount, uint256 yes, uint256 no) =
            abi.decode(logs[0].data, (uint256, uint256, uint256, uint256));
        require(shares == 10e18 && amount == cost && yes == 10e18 && no == 0, "trade payload");
        uint256 quote = market.quoteSell(id, PredictionMarket.Outcome.YES, 4e18);
        vm.recordLogs();
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, 4e18, quote);
        logs = vm.getRecordedLogs();
        require(
            logs.length == 1
                && logs[0].topics[0]
                    == keccak256("SellExecuted(uint256,address,uint8,uint256,uint256,uint256,uint256)"),
            "sell event"
        );
        (shares, amount, yes, no) = abi.decode(logs[0].data, (uint256, uint256, uint256, uint256));
        require(shares == 4e18 && amount == quote && yes == 6e18 && no == 0, "sell payload");
    }

    function testProductionContractsFitEip170RuntimeLimit() public view {
        require(address(market).code.length <= 24_576, "market exceeds EIP-170");
        require(
            address(registry).code.length <= 24_576 && address(pricing).code.length <= 24_576, "helper exceeds EIP-170"
        );
    }

    /// @notice Integration property across real token/market accounting, not a replacement
    /// for Matthew's independent fixed-point economic proof.
    function testFuzzMixedMarketsTradesClaimsAndSurplusPreserveLedger(uint256 seed) public {
        _create(0);
        _create(1);
        for (uint256 i; i < 16; ++i) {
            uint256 entropy = uint256(keccak256(abi.encode(seed, i)));
            uint256 id = entropy % 2;
            address trader = (entropy >> 2) % 2 == 0 ? TRADER : OTHER;
            PredictionMarket.Outcome outcome =
                (entropy >> 3) % 2 == 0 ? PredictionMarket.Outcome.YES : PredictionMarket.Outcome.NO;
            uint256 owned = market.balanceOf(id, trader, outcome);
            if ((entropy >> 4) % 2 == 0 && owned >= WAD) {
                uint256 shares = owned > 20e18 ? 20e18 : owned / 2;
                uint256 quote = market.quoteSell(id, outcome, shares);
                vm.prank(trader);
                market.sell(id, outcome, shares, quote);
            } else {
                _buy(trader, id, outcome, (1 + ((entropy >> 5) % 20)) * WAD + entropy % 100);
            }
            _assertPositions(0);
            _assertPositions(1);
            _accounting();
        }
        _proposal(0, PredictionMarket.ResolutionChoice(seed % 3));
        _proposal(1, PredictionMarket.ResolutionChoice((seed / 3) % 3));
        vm.warp(market.getResolution(1).challengeDeadline);
        market.finalize(0);
        market.finalize(1);
        for (uint256 id; id < 2; ++id) {
            if (market.withdrawableSurplus(id) > 0) {
                vm.prank(CREATOR);
                market.withdrawCreatorSurplus(id);
            }
            _claimIfHeld(id, TRADER);
            _claimIfHeld(id, OTHER);
            require(market.remainingLiability(id) == 0, "liability survived all claims");
            if (market.withdrawableSurplus(id) > 0) {
                vm.prank(CREATOR);
                market.withdrawCreatorSurplus(id);
            }
        }
        require(
            token.balanceOf(address(market)) == 0 && market.totalCollateral() == 0, "ledger retained unexplained funds"
        );
    }

    function _assertPositions(uint256 id) private view {
        PredictionMarket.Market memory data = market.getMarket(id);
        require(
            data.yesQuantity
                == market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES)
                    + market.balanceOf(id, OTHER, PredictionMarket.Outcome.YES),
            "YES ledger"
        );
        require(
            data.noQuantity
                == market.balanceOf(id, TRADER, PredictionMarket.Outcome.NO)
                    + market.balanceOf(id, OTHER, PredictionMarket.Outcome.NO),
            "NO ledger"
        );
    }

    function _claimIfHeld(uint256 id, address account) private {
        uint256 held = market.balanceOf(id, account, PredictionMarket.Outcome.YES)
            + market.balanceOf(id, account, PredictionMarket.Outcome.NO);
        if (held > 0) {
            vm.prank(account);
            market.claimPayout(id);
        }
        _accounting();
    }
}
