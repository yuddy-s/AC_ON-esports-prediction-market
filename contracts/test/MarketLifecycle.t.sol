// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketTestBase, MarketAccess, PredictionMarket, LMSR} from "./MarketTestBase.sol";

contract MarketLifecycleTest is MarketTestBase {
    function testFixtureIdentityMetadataAndOneMarketRule() public {
        uint256 id = _create(0);
        PredictionMarket.Market memory data = market.getMarket(id);
        bytes32 expected = keccak256(abi.encode("manual", "valorant", "0"));
        require(data.id == 0 && data.fixtureKey == expected, "fixture identity");
        require(keccak256(bytes(data.question)) == keccak256("Will Team A beat Team B?"), "question mapping");
        _state(id, PredictionMarket.MarketState.OPEN);
        PredictionMarket.Fixture memory fixture = market.getFixture(expected);
        require(fixture.hasMarket && fixture.marketId == id && fixture.registrar == REGISTRAR, "fixture link");
        vm.expectPartialRevert(PredictionMarket.MarketAlreadyExists.selector);
        vm.prank(CREATOR);
        market.createMarket(expected, block.timestamp + 1 days, fixture.revisionHash);
        PredictionMarket.FixtureData memory changed = fixture.data;
        changed.teamAId = "changed";
        vm.expectPartialRevert(PredictionMarket.FixtureLocked.selector);
        vm.prank(REGISTRAR);
        market.registerFixture(changed);
        _accounting();
    }

    function testOnlyRegistrarCanRegisterAndFixtureMustExist() public {
        PredictionMarket.FixtureData memory data = _data(0);
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        market.registerFixture(data);
        vm.expectPartialRevert(PredictionMarket.FixtureNotRegistered.selector);
        vm.prank(CREATOR);
        market.createMarket(bytes32(uint256(12)), block.timestamp + 1 days, bytes32(0));
    }

    function testInvalidFixtureIdentityTeamsAndEvidenceRevert() public {
        PredictionMarket.FixtureData memory data = _data(0);
        data.teamBId = data.teamAId;
        vm.expectRevert(PredictionMarket.InvalidFixture.selector);
        vm.prank(REGISTRAR);
        market.registerFixture(data);
        data = _data(0);
        data.evidenceHash = bytes32(0);
        vm.expectRevert(PredictionMarket.InvalidEvidence.selector);
        vm.prank(REGISTRAR);
        market.registerFixture(data);
    }

    function testFixtureRevisionProtectsCreationFromChangedMetadata() public {
        bytes32 key = _register(0);
        bytes32 beforeHash = market.getFixture(key).revisionHash;
        PredictionMarket.FixtureData memory data = _data(0);
        data.teamAName = "Corrected Team A";
        vm.prank(REGISTRAR);
        market.registerFixture(data);
        vm.expectRevert(PredictionMarket.FixtureRevisionMismatch.selector);
        vm.prank(CREATOR);
        market.createMarket(key, block.timestamp + 1 days, beforeHash);
        require(market.marketCount() == 0, "stale creation mutated state");
    }

    function testDeadlineMustBeFutureAndAtLeastFifteenMinutesBeforeStart() public {
        bytes32 key = _register(0);
        PredictionMarket.Fixture memory fixture = market.getFixture(key);
        vm.expectRevert(PredictionMarket.InvalidTradingDeadline.selector);
        vm.prank(CREATOR);
        market.createMarket(key, block.timestamp, fixture.revisionHash);
        vm.expectRevert(PredictionMarket.InvalidTradingDeadline.selector);
        vm.prank(CREATOR);
        market.createMarket(key, fixture.data.scheduledStart - 899, fixture.revisionHash);
        vm.prank(CREATOR);
        market.createMarket(key, fixture.data.scheduledStart - 900, fixture.revisionHash);
    }

    function testFundingFailureDoesNotConsumeFixtureOrMarketId() public {
        bytes32 key = _register(0);
        bytes32 revision = market.getFixture(key).revisionHash;
        vm.prank(CREATOR);
        token.approve(address(market), 0);
        vm.expectPartialRevert(PredictionMarket.InsufficientTokenAllowance.selector);
        vm.prank(CREATOR);
        market.createMarket(key, block.timestamp + 1 days, revision);
        require(!market.getFixture(key).hasMarket && market.marketCount() == 0, "creation partially stored");
        vm.expectPartialRevert(PredictionMarket.InsufficientTokenBalance.selector);
        vm.prank(address(0x9999));
        market.createMarket(key, block.timestamp + 1 days, revision);
        require(token.balanceOf(address(market)) == 0, "creation partially funded");
    }

    function testBuyAndSellTrackExactPaymentsAndHistoricalParticipation() public {
        uint256 id = _create(0);
        uint256 beforeBalance = token.balanceOf(TRADER);
        uint256 cost = _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        uint256 quote = market.quoteSell(id, PredictionMarket.Outcome.YES, 10e18);
        require(cost == quote + 1, "ceil-buy/floor-sell round trip must retain one base unit");
        vm.prank(TRADER);
        uint256 paid = market.sell(id, PredictionMarket.Outcome.YES, 10e18, quote);
        require(paid == quote && token.balanceOf(TRADER) == beforeBalance - 1, "sell payment mismatch");
        require(market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 0, "shares not consumed");
        require(market.hasTraded(id, TRADER), "historical conflict cleared by selling");
        _accounting();
    }

    function testRealCompetingBuyInvalidatesStaleMaxCostAtomically() public {
        uint256 id = _create(0);
        uint256 stale = market.quoteBuy(id, PredictionMarket.Outcome.YES, 10e18);
        _buy(OTHER, id, PredictionMarket.Outcome.YES, 30e18);
        uint256 current = market.quoteBuy(id, PredictionMarket.Outcome.YES, 10e18);
        require(current > stale, "competing buy must move cost");
        uint256 beforeBalance = token.balanceOf(TRADER);
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.SlippageExceeded.selector, current, stale));
        vm.prank(TRADER);
        market.buy(id, PredictionMarket.Outcome.YES, 10e18, stale);
        require(
            token.balanceOf(TRADER) == beforeBalance && market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 0,
            "stale buy changed holdings"
        );
        require(market.getMarket(id).yesQuantity == 30e18, "stale buy changed quantities");
    }

    function testSellRejectsUnownedSharesStaleMinReturnAndTradeSize() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 100e18);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        vm.expectPartialRevert(PredictionMarket.InsufficientShares.selector);
        vm.prank(OTHER);
        market.sell(id, PredictionMarket.Outcome.YES, WAD, 0);
        vm.expectPartialRevert(LMSR.TradeSizeLimitExceeded.selector);
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, 101e18, 0);
        uint256 quote = market.quoteSell(id, PredictionMarket.Outcome.YES, WAD);
        vm.expectPartialRevert(PredictionMarket.MinimumReturnNotMet.selector);
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, WAD, quote + 1);
        require(market.balanceOf(id, TRADER, PredictionMarket.Outcome.YES) == 110e18, "failed sell burned shares");
        vm.expectRevert(LMSR.ZeroShares.selector);
        market.quoteSell(id, PredictionMarket.Outcome.YES, 0);
        vm.expectRevert(LMSR.TradeTooSmall.selector);
        pricing.sellReturn(2_000e18, 1, false, 1);
    }

    function testTradeDeadlineBlocksBothDirectionsWithoutAutomaticStateMutation() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        vm.warp(market.getMarket(id).tradingDeadline);
        vm.expectRevert(PredictionMarket.TradingClosed.selector);
        market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        vm.expectRevert(PredictionMarket.TradingClosed.selector);
        market.quoteSell(id, PredictionMarket.Outcome.YES, WAD);
        _state(id, PredictionMarket.MarketState.OPEN);
        market.closeTrading(id, bytes32(0));
        _state(id, PredictionMarket.MarketState.CLOSED);
        vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        market.closeTrading(id, bytes32(0));
    }

    function testEarlyCloseIsRegistrarOnlyAndShortensTheDeadline() public {
        uint256 id = _create(0);
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        market.closeTrading(id, keccak256("early"));
        vm.expectRevert(PredictionMarket.InvalidEvidence.selector);
        vm.prank(REGISTRAR);
        market.closeTrading(id, bytes32(0));
        vm.prank(REGISTRAR);
        market.closeTrading(id, keccak256("early-start"));
        require(market.getMarket(id).tradingDeadline == block.timestamp, "early close did not shorten deadline");
        _state(id, PredictionMarket.MarketState.CLOSED);
    }

    function testImmutableProposalWindowAndPermissionlessFinalize() public {
        uint256 id = _create(0);
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        market.proposeOutcome(id, PredictionMarket.ResolutionChoice.YES, keccak256("r"), "uri");
        vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        vm.prank(PROPOSER);
        market.proposeOutcome(id, PredictionMarket.ResolutionChoice.YES, keccak256("r"), "uri");
        _proposal(id, PredictionMarket.ResolutionChoice.YES);
        uint256 deadline = market.getResolution(id).challengeDeadline;
        require(deadline == block.timestamp + 24 hours, "challenge window");
        vm.expectRevert(PredictionMarket.ProposalAlreadyExists.selector);
        vm.prank(PROPOSER);
        market.proposeOutcome(id, PredictionMarket.ResolutionChoice.NO, keccak256("correction"), "uri");
        vm.warp(deadline - 1);
        vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        market.finalize(id);
        vm.warp(deadline);
        vm.prank(OTHER);
        market.finalize(id);
        _state(id, PredictionMarket.MarketState.FINALIZED);
        vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        market.finalize(id);
    }

    function testLateProposalCannotRaceExpiredNoProposalPath() public {
        uint256 id = _create(0);
        vm.warp(market.getMarket(id).tradingDeadline + 7 days);
        vm.expectRevert(PredictionMarket.ProposalExpired.selector);
        vm.prank(PROPOSER);
        market.proposeOutcome(id, PredictionMarket.ResolutionChoice.YES, keccak256("late"), "uri");
        _state(id, PredictionMarket.MarketState.OPEN);
        vm.prank(OTHER);
        market.requestResolverSelection(id);
        _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
    }

    function testChallengeIsSingleBondedAndCannotBeSelfSubmitted() public {
        uint256 id = _create(0);
        _proposal(id, PredictionMarket.ResolutionChoice.VOID);
        vm.expectRevert(PredictionMarket.ChallengeNotAllowed.selector);
        vm.prank(PROPOSER);
        market.challengeOutcome(id, keccak256("c"));
        uint256 beforeBalance = token.balanceOf(CHALLENGER);
        vm.prank(CHALLENGER);
        market.challengeOutcome(id, keccak256("c"));
        require(token.balanceOf(CHALLENGER) == beforeBalance - 10e18, "bond charge");
        require(market.totalChallengeBonds() == 10e18, "bond escrow");
        require(market.getMarket(id).collateralBalance == market.REQUIRED_SUBSIDY(), "bond mixed with collateral");
        vm.expectRevert(PredictionMarket.ChallengeAlreadyExists.selector);
        vm.prank(OTHER);
        market.challengeOutcome(id, keccak256("second"));
        _state(id, PredictionMarket.MarketState.DISPUTED);
        _accounting();
    }

    function testChallengeAtExactDeadlineReverts() public {
        uint256 id = _create(0);
        _proposal(id, PredictionMarket.ResolutionChoice.NO);
        vm.warp(market.getResolution(id).challengeDeadline);
        vm.expectRevert(PredictionMarket.ChallengeWindowClosed.selector);
        vm.prank(CHALLENGER);
        market.challengeOutcome(id, keccak256("c"));
    }

    // Issue #53: the trading-deadline boundary at three points around it.
    function testTradingDeadlineThreePointBoundary() public {
        uint256 id = _create(0);
        uint256 deadline = market.getMarket(id).tradingDeadline;
        vm.warp(deadline - 1);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, WAD);
        vm.warp(deadline);
        vm.expectRevert(PredictionMarket.TradingClosed.selector);
        market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        vm.expectRevert(PredictionMarket.TradingClosed.selector);
        market.quoteSell(id, PredictionMarket.Outcome.YES, WAD);
        vm.warp(deadline + 1);
        vm.expectRevert(PredictionMarket.TradingClosed.selector);
        market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        // Time alone never advances storage: the market stays OPEN and must be closed by a transaction.
        _state(id, PredictionMarket.MarketState.OPEN);
    }

    // Issue #53: permissionless selection opens exactly seven days after the deadline, not before.
    function testNoProposalTimeoutBoundary() public {
        uint256 id = _create(0);
        uint256 deadline = market.getMarket(id).tradingDeadline;
        vm.warp(deadline + 7 days - 1);
        vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        market.requestResolverSelection(id);
        vm.warp(deadline + 7 days);
        vm.prank(OTHER);
        market.requestResolverSelection(id);
        _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
    }

    // Issue #53: a challenge one second before the window closes is still valid.
    function testChallengeOneSecondBeforeWindowCloseSucceeds() public {
        uint256 id = _create(0);
        _proposal(id, PredictionMarket.ResolutionChoice.NO);
        vm.warp(market.getResolution(id).challengeDeadline - 1);
        vm.prank(CHALLENGER);
        market.challengeOutcome(id, keccak256("c"));
        _state(id, PredictionMarket.MarketState.DISPUTED);
    }

    // Issue #53: the shared vector file (docs/agent/testing/vectors/market_deadline_vectors.json)
    // drives a real deployed-code check. Each expected action is evaluated on a fresh market in the
    // vector's stored state, so mutating actions cannot leak between assertions. Vector timestamps
    // are offsets from the canonical deadline 1000000; real markets warp to their own deadline
    // plus the same offset. frontendActions belong to the frontend consumer.
    function testSharedDeadlineVectors() public {
        string memory json = vm.readFile("../docs/agent/testing/vectors/market_deadline_vectors.json");
        // parseJson returns [offset][length][elements]; decoding as uint256[] yields the length
        // without interpreting the per-vector objects.
        uint256 count = abi.decode(vm.parseJson(json, ".vectors"), (uint256[])).length;
        require(vm.parseJsonUint(json, ".noProposalPeriodSeconds") == market.NO_PROPOSAL_PERIOD(), "vector period");

        uint256 seed;
        for (uint256 i; i < count; ++i) {
            string memory vector = string.concat(".vectors[", vm.toString(i), "]");
            string memory storedState = vm.parseJsonString(json, string.concat(vector, ".storedState"));
            uint256 vectorDeadline = vm.parseJsonUint(json, string.concat(vector, ".tradingDeadline"));
            uint256 vectorTimestamp = vm.parseJsonUint(json, string.concat(vector, ".blockTimestamp"));
            bool tradeAccepted = vm.parseJsonBool(json, string.concat(vector, ".expected.tradeAccepted"));
            bool proposalAccepted = vm.parseJsonBool(json, string.concat(vector, ".expected.proposalAccepted"));
            bool selectionAccepted =
                vm.parseJsonBool(json, string.concat(vector, ".expected.noProposalSelectionAccepted"));

            _assertVectorTrade(seed++, storedState, vectorDeadline, vectorTimestamp, tradeAccepted);
            _assertVectorProposal(seed++, storedState, vectorDeadline, vectorTimestamp, proposalAccepted);
            _assertVectorSelection(seed++, storedState, vectorDeadline, vectorTimestamp, selectionAccepted);
        }
    }

    function _stateIs(string memory storedState, string memory expected) internal pure returns (bool) {
        return keccak256(bytes(storedState)) == keccak256(bytes(expected));
    }

    // Builds a real market in the vector's stored state and returns it.
    function _marketInState(uint256 seed, string memory storedState) internal returns (uint256 id) {
        id = _create(seed);
        if (_stateIs(storedState, "OPEN")) {
            _state(id, PredictionMarket.MarketState.OPEN);
        } else if (_stateIs(storedState, "CLOSED")) {
            vm.prank(REGISTRAR);
            market.closeTrading(id, keccak256("vector-early-close"));
            _state(id, PredictionMarket.MarketState.CLOSED);
        } else if (_stateIs(storedState, "FINALIZED")) {
            _buy(TRADER, id, PredictionMarket.Outcome.YES, WAD);
            _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
            _state(id, PredictionMarket.MarketState.FINALIZED);
        } else {
            require(_stateIs(storedState, "VOID"), "unknown storedState");
            _unchallenged(id, PredictionMarket.ResolutionChoice.VOID);
            _state(id, PredictionMarket.MarketState.VOID);
        }
    }

    // Vector timestamps are absolute against the canonical deadline; warp the real market to the
    // same offset from its own deadline.
    function _warpVector(uint256 realDeadline, uint256 vectorDeadline, uint256 vectorTimestamp) internal {
        vm.warp(uint256(int256(realDeadline) + int256(vectorTimestamp) - int256(vectorDeadline)));
    }

    function _assertVectorTrade(
        uint256 seed,
        string memory storedState,
        uint256 vectorDeadline,
        uint256 vectorTimestamp,
        bool accepted
    ) internal {
        uint256 id = _marketInState(seed, storedState);
        _warpVector(market.getMarket(id).tradingDeadline, vectorDeadline, vectorTimestamp);
        if (accepted) {
            market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        } else if (_stateIs(storedState, "OPEN")) {
            vm.expectRevert(PredictionMarket.TradingClosed.selector);
            market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        } else {
            vm.expectPartialRevert(PredictionMarket.WrongState.selector);
            market.quoteBuy(id, PredictionMarket.Outcome.YES, WAD);
        }
    }

    function _assertVectorProposal(
        uint256 seed,
        string memory storedState,
        uint256 vectorDeadline,
        uint256 vectorTimestamp,
        bool accepted
    ) internal {
        uint256 id = _marketInState(seed, storedState);
        uint256 realDeadline = market.getMarket(id).tradingDeadline;
        _warpVector(realDeadline, vectorDeadline, vectorTimestamp);
        if (accepted) {
            vm.prank(PROPOSER);
            market.proposeOutcome(
                id, PredictionMarket.ResolutionChoice.NO, keccak256("vector-proposal"), "https://example.invalid/vector"
            );
            _state(id, PredictionMarket.MarketState.PROPOSED);
            return;
        }
        bool terminal = !_stateIs(storedState, "OPEN") && !_stateIs(storedState, "CLOSED");
        if (terminal) {
            // Terminal markets necessarily carry a settled resolution, so the proposal-exists
            // guard fires before the state check; the vector still requires rejection.
            vm.expectRevert(PredictionMarket.ProposalAlreadyExists.selector);
        } else if (block.timestamp >= realDeadline + market.NO_PROPOSAL_PERIOD()) {
            vm.expectRevert(PredictionMarket.ProposalExpired.selector);
        } else {
            vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        }
        vm.prank(PROPOSER);
        market.proposeOutcome(
            id, PredictionMarket.ResolutionChoice.NO, keccak256("vector-proposal"), "https://example.invalid/vector"
        );
    }

    function _assertVectorSelection(
        uint256 seed,
        string memory storedState,
        uint256 vectorDeadline,
        uint256 vectorTimestamp,
        bool accepted
    ) internal {
        uint256 id = _marketInState(seed, storedState);
        uint256 realDeadline = market.getMarket(id).tradingDeadline;
        _warpVector(realDeadline, vectorDeadline, vectorTimestamp);
        if (accepted) {
            market.requestResolverSelection(id);
            _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
            return;
        }
        bool terminal = !_stateIs(storedState, "OPEN") && !_stateIs(storedState, "CLOSED");
        if (terminal) {
            vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        } else {
            vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        }
        market.requestResolverSelection(id);
    }

    function testWinningClaimsAndSurplusReserveOutstandingLiability() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        _buy(OTHER, id, PredictionMarket.Outcome.NO, 7e18);
        _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
        require(market.claimableAmount(id, TRADER) == 10e18 && market.claimableAmount(id, OTHER) == 0, "claim reads");
        uint256 surplus = market.withdrawableSurplus(id);
        vm.expectRevert(PredictionMarket.CreatorOnly.selector);
        market.withdrawCreatorSurplus(id);
        vm.prank(CREATOR);
        require(market.withdrawCreatorSurplus(id) == surplus, "surplus amount");
        require(market.getMarket(id).collateralBalance == 10e18, "winning liability invaded");
        uint256 beforeBalance = token.balanceOf(TRADER);
        vm.prank(TRADER);
        require(market.claimPayout(id) == 10e18, "winning payout");
        require(token.balanceOf(TRADER) == beforeBalance + 10e18, "winning transfer");
        require(market.hasClaimed(id, TRADER) && market.claimableAmount(id, TRADER) == 0, "claimed flag");
        vm.expectRevert(PredictionMarket.AlreadyClaimed.selector);
        vm.prank(TRADER);
        market.claimPayout(id);
        vm.prank(OTHER);
        require(market.claimPayout(id) == 0, "losing payout");
        require(market.getMarket(id).yesQuantity == 0 && market.getMarket(id).noQuantity == 0, "positions not consumed");
        _accounting();
    }

    function testVoidProposalHasSameWindowAndCombinesBothHoldings() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        _buy(TRADER, id, PredictionMarket.Outcome.NO, 5e18);
        _unchallenged(id, PredictionMarket.ResolutionChoice.VOID);
        _state(id, PredictionMarket.MarketState.VOID);
        require(market.remainingLiability(id) == 75e17, "VOID reserve");
        vm.prank(CREATOR);
        market.withdrawCreatorSurplus(id);
        vm.prank(TRADER);
        require(market.claimPayout(id) == 75e17, "combined VOID claim");
        require(market.balanceOf(id, TRADER, PredictionMarket.Outcome.NO) == 0, "NO shares retained");
        vm.expectRevert(PredictionMarket.AlreadyClaimed.selector);
        vm.prank(TRADER);
        market.claimPayout(id);
        _accounting();
    }

    function testVoidOddBaseUnitsReserveCeilingAndPayFloorPerWallet() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, WAD + 1);
        _unchallenged(id, PredictionMarket.ResolutionChoice.VOID);
        require(market.remainingLiability(id) == WAD / 2 + 1, "reserve must round up");
        require(market.claimableAmount(id, TRADER) == WAD / 2, "payout must round down");
        vm.prank(CREATOR);
        market.withdrawCreatorSurplus(id);
        vm.prank(TRADER);
        market.claimPayout(id);
        require(
            market.remainingLiability(id) == 0 && market.withdrawableSurplus(id) == 1,
            "rounding dust must become surplus only after claim"
        );
        _accounting();
    }

    function testNoEarlyClaimsOrSurplusAndUnknownMarketReverts() public {
        uint256 id = _create(0);
        vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        vm.prank(TRADER);
        market.claimPayout(id);
        vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        vm.prank(CREATOR);
        market.withdrawCreatorSurplus(id);
        vm.expectPartialRevert(PredictionMarket.MarketNotFound.selector);
        market.balanceOf(99, TRADER, PredictionMarket.Outcome.YES);
        _unchallenged(id, PredictionMarket.ResolutionChoice.YES);
        vm.expectRevert(PredictionMarket.NoPosition.selector);
        vm.prank(OTHER);
        market.claimPayout(id);
    }

    function testSafeHandoffRevokesOldAdminAndRolesCanBeRecovered() public {
        market.transferAdministration(SAFE);
        registry.transferAdministration(SAFE);
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        vm.prank(OTHER);
        market.acceptAdministration();
        vm.prank(SAFE);
        market.acceptAdministration();
        vm.prank(SAFE);
        registry.acceptAdministration();
        require(market.admin() == SAFE && registry.admin() == SAFE, "Safe not owner");
        require(!market.hasRole(bytes32(0), address(this)), "deployer kept admin");
        bytes32 role = market.PROPOSER_ROLE();
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        market.grantRole(role, OTHER);
        vm.prank(SAFE);
        market.revokeRole(role, PROPOSER);
        vm.prank(SAFE);
        market.grantRole(role, OTHER);
        require(!market.hasRole(role, PROPOSER) && market.hasRole(role, OTHER), "role rotation failed");
        vm.expectPartialRevert(MarketAccess.Unauthorized.selector);
        registry.setResolverStatus(OTHER, true);
    }
}
