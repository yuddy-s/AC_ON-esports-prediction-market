// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketTestBase, VmMarket, PredictionMarket} from "./MarketTestBase.sol";

contract ResolverTest is MarketTestBase {
    function testCoordinatorRequestCannotReenterSelection() public {
        uint256 id = _create(0);
        vrf.setCallback(address(market), abi.encodeCall(market.retryResolverSelection, (id)));
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        require(
            !vrf.callbackSucceeded() && bytes4(vrf.callbackResult()) == PredictionMarket.ReentrantCall.selector,
            "coordinator bypassed lock"
        );
        require(vrf.nextId() == 2 && market.getResolverRound(id, 1).currentRequestId == 1, "nested request installed");
    }

    function testRequestUsesV25LinkBillingAndThreeConfirmations() public {
        uint256 id = _create(0);
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        require(vrf.lastConsumer() == address(market), "wrong consumer");
        require(vrf.lastSubscription() == 1 && vrf.lastKeyHash() == bytes32(uint256(1)), "VRF config");
        require(vrf.lastConfirmations() == 3 && vrf.lastWordCount() == 1, "VRF request shape");
        require(vrf.lastCallbackGas() == 2_000_000, "callback gas");
        require(
            keccak256(vrf.lastExtraArgs())
                == keccak256(abi.encodeWithSelector(bytes4(keccak256("VRF ExtraArgsV1")), false)),
            "must bill LINK"
        );
    }

    function testSnapshotExcludesEveryParticipantAndAdmin() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        _buy(OTHER, id, PredictionMarket.Outcome.NO, 3e18);
        uint256 proceeds = market.quoteSell(id, PredictionMarket.Outcome.YES, 10e18);
        vm.prank(TRADER);
        market.sell(id, PredictionMarket.Outcome.YES, 10e18, proceeds);
        address[6] memory excluded = [CREATOR, REGISTRAR, PROPOSER, CHALLENGER, TRADER, OTHER];
        for (uint256 i; i < excluded.length; ++i) {
            registry.setResolverStatus(excluded[i], true);
        }
        registry.setResolverStatus(address(this), true);
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        PredictionMarket.ResolverRound memory selection = market.getResolverRound(id, 1);
        require(selection.candidates.length == 10, "conflict entered snapshot");
        for (uint256 i; i < excluded.length; ++i) {
            require(!market.isResolverEligible(id, excluded[i]), "conflict considered eligible");
        }
        require(!market.isResolverEligible(id, address(this)), "registry admin eligible");
        for (uint256 i; i < 10; ++i) {
            require(selection.candidates[i] == _resolver(i), "snapshot membership");
        }
    }

    function testUndersizedPoolCanBeReplenishedWithoutExtendingDeadline() public {
        for (uint256 i = 4; i < 10; ++i) {
            registry.setResolverStatus(_resolver(i), false);
        }
        uint256 id = _create(0);
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        PredictionMarket.ResolverRound memory before = market.getResolverRound(id, 1);
        require(!before.snapshotFrozen && !before.hasRequest, "undersized pool was frozen");
        vm.warp(block.timestamp + 1 hours);
        registry.setResolverStatus(_resolver(4), true);
        market.retryResolverSelection(id);
        PredictionMarket.ResolverRound memory afterRound = market.getResolverRound(id, 1);
        require(afterRound.snapshotFrozen && afterRound.candidates.length == 5, "replenishment not used");
        require(afterRound.selectionDeadline == before.selectionDeadline, "deadline extended");
        vrf.fulfill(market, afterRound.currentRequestId, 123);
        _distinct(afterRound.candidates, market.getResolverRound(id, 1).committee);
    }

    function testInsufficientPoolExpiresToVoidAndRefundsChangedProposalBond() public {
        for (uint256 i; i < 10; ++i) {
            registry.setResolverStatus(_resolver(i), false);
        }
        uint256 id = _create(0);
        uint256 beforeBalance = token.balanceOf(CHALLENGER);
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        uint256 deadline = market.getResolverRound(id, 1).selectionDeadline;
        vm.warp(deadline - 1);
        vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        market.advanceResolution(id);
        vm.warp(deadline);
        vm.prank(OTHER);
        market.advanceResolution(id);
        _state(id, PredictionMarket.MarketState.VOID);
        require(token.balanceOf(CHALLENGER) == beforeBalance && market.totalChallengeBonds() == 0, "bond not refunded");
        _accounting();
    }

    function testRequestFailureKeepsSnapshotAndCanRetryAtThirtyMinutes() public {
        vrf.setFailure(true);
        uint256 id = _create(0);
        _dispute(id, PredictionMarket.ResolutionChoice.YES);
        PredictionMarket.ResolverRound memory before = market.getResolverRound(id, 1);
        require(before.snapshotFrozen && !before.hasRequest, "failed request lost selection state");
        vm.warp(before.lastRequestAt + 30 minutes - 1);
        vm.expectPartialRevert(PredictionMarket.RetryTooSoon.selector);
        market.retryResolverSelection(id);
        registry.setResolverStatus(_resolver(0), false);
        registry.setResolverStatus(address(0x7777), true);
        vrf.setFailure(false);
        vm.warp(before.lastRequestAt + 30 minutes);
        market.retryResolverSelection(id);
        PredictionMarket.ResolverRound memory afterRound = market.getResolverRound(id, 1);
        require(
            keccak256(abi.encode(before.candidates)) == keccak256(abi.encode(afterRound.candidates)),
            "retry changed snapshot"
        );
        require(
            afterRound.selectionDeadline == before.selectionDeadline && afterRound.hasRequest, "retry deadline/request"
        );
    }

    function testOnlyCurrentRequestCanInstallCommitteeAndIgnoredCallbackDoesNotMutateRound() public {
        uint256 id = _create(0);
        uint256 stale = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vm.warp(block.timestamp + 30 minutes);
        market.retryResolverSelection(id);
        PredictionMarket.ResolverRound memory selection = market.getResolverRound(id, 1);
        bytes32 before = keccak256(abi.encode(selection));
        vm.recordLogs();
        vrf.fulfill(market, stale, 17);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.SUPERSEDED);
        require(keccak256(abi.encode(market.getResolverRound(id, 1))) == before, "ignored callback changed round");
        vrf.fulfill(market, selection.currentRequestId, 17);
        _state(id, PredictionMarket.MarketState.RESOLVER_VOTING);
        _distinct(selection.candidates, market.getResolverRound(id, 1).committee);
    }

    function testRetryFailureAlsoInvalidatesOlderOutstandingRequest() public {
        uint256 id = _create(0);
        uint256 stale = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vm.warp(block.timestamp + 30 minutes);
        vrf.setFailure(true);
        market.retryResolverSelection(id);
        vm.recordLogs();
        vrf.fulfill(market, stale, 17);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.SUPERSEDED);
        _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
    }

    function testUnauthorizedUnknownAndMalformedCallbacksCannotInstall() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        uint256[] memory words = new uint256[](1);
        vm.expectRevert(PredictionMarket.OnlyCoordinator.selector);
        market.rawFulfillRandomWords(requestId, words);
        vm.recordLogs();
        vrf.fulfill(market, 987654, 1);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.UNKNOWN_REQUEST);
        vm.recordLogs();
        vrf.malformed(market, requestId);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.INVALID_WORD_COUNT);
        _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
    }

    function testRequestIdZeroIsNotConfusedWithMissingRequest() public {
        vrf.setNextId(0);
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        require(requestId == 0 && market.getResolverRound(id, 1).hasRequest, "zero request ID not represented");
        vrf.fulfill(market, requestId, 99);
        _state(id, PredictionMarket.MarketState.RESOLVER_VOTING);
    }

    function testDuplicateCallbackEmitsIgnoredWithoutChangingCommittee() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 1);
        bytes32 before = keccak256(abi.encode(market.getResolverRound(id, 1)));
        vm.recordLogs();
        vrf.fulfill(market, requestId, 999);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.CONSUMED);
        require(keccak256(abi.encode(market.getResolverRound(id, 1))) == before, "duplicate changed round");
    }

    function testCallbackAtSelectionDeadlineIsIgnoredThenAnyoneCanVoid() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vm.warp(market.getResolverRound(id, 1).selectionDeadline);
        vm.recordLogs();
        vrf.fulfill(market, requestId, 1);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.EXPIRED);
        _state(id, PredictionMarket.MarketState.RESOLVER_SELECTION);
        vm.expectRevert(PredictionMarket.SelectionExpired.selector);
        market.retryResolverSelection(id);
        vm.prank(OTHER);
        market.advanceResolution(id);
        vm.recordLogs();
        vrf.fulfill(market, requestId, 1);
        _ignored(vm.getRecordedLogs(), PredictionMarket.IgnoreReason.WRONG_PHASE);
    }

    function testRequestIdentitySeparatesMarkets() public {
        uint256 first = _create(0);
        uint256 second = _create(1);
        uint256 firstRequest = _dispute(first, PredictionMarket.ResolutionChoice.YES);
        uint256 secondRequest = _dispute(second, PredictionMarket.ResolutionChoice.NO);
        vrf.fulfill(market, secondRequest, 42);
        _state(first, PredictionMarket.MarketState.RESOLVER_SELECTION);
        _state(second, PredictionMarket.MarketState.RESOLVER_VOTING);
        vrf.fulfill(market, firstRequest, 123);
        _state(first, PredictionMarket.MarketState.RESOLVER_VOTING);
    }

    function testRegistryChangesDoNotRewriteFrozenPoolOrAssignedVotingAuthority() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        address[] memory snapshot = market.getResolverRound(id, 1).candidates;
        for (uint256 i; i < 10; ++i) {
            registry.setResolverStatus(_resolver(i), false);
        }
        vrf.fulfill(market, requestId, 73);
        PredictionMarket.ResolverRound memory round = market.getResolverRound(id, 1);
        _distinct(snapshot, round.committee);
        require(!market.isResolverEligible(id, round.committee[0]), "removed resolver still currently eligible");
        _quorum(id, PredictionMarket.ResolutionChoice.YES);
        _state(id, PredictionMarket.MarketState.FINALIZED);
    }

    function testOnlySelectedResolversVoteOnceAndDeadlineIsStrict() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 51);
        PredictionMarket.ResolverRound memory round = market.getResolverRound(id, 1);
        require(round.voteDeadline == block.timestamp + 48 hours, "vote duration");
        vm.expectRevert(PredictionMarket.ResolverNotSelected.selector);
        vm.prank(TRADER);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.YES);
        vm.prank(round.committee[0]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.YES);
        vm.expectRevert(PredictionMarket.AlreadyVoted.selector);
        vm.prank(round.committee[0]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.NO);
        vm.warp(round.voteDeadline);
        vm.expectRevert(PredictionMarket.VotingClosed.selector);
        vm.prank(round.committee[1]);
        market.voteOnOutcome(id, PredictionMarket.ResolutionChoice.YES);
    }

    function testChangedOutcomeRefundsBondAndUpheldOutcomeAddsSurplusOnlyAfterReserve() public {
        uint256 first = _create(0);
        uint256 second = _create(1);
        _buy(TRADER, first, PredictionMarket.Outcome.NO, 10e18);
        _buy(OTHER, second, PredictionMarket.Outcome.YES, 10e18);
        uint256 before = token.balanceOf(CHALLENGER);
        uint256 requestId = _dispute(first, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 8);
        _quorum(first, PredictionMarket.ResolutionChoice.NO);
        require(token.balanceOf(CHALLENGER) == before, "changed result not refunded");
        uint256 collateralBefore = market.getMarket(second).collateralBalance;
        requestId = _dispute(second, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 9);
        _quorum(second, PredictionMarket.ResolutionChoice.YES);
        require(market.getMarket(second).collateralBalance == collateralBefore + 10e18, "upheld bond not collateral");
        require(
            market.withdrawableSurplus(second) == collateralBefore + 10e18 - 10e18, "surplus ignored winning reserve"
        );
        require(market.totalChallengeBonds() == 0, "bond not disposed");
        _accounting();
    }

    function testThreeVoidVotesProduceVoidAndCombinedClaim() public {
        uint256 id = _create(0);
        _buy(TRADER, id, PredictionMarket.Outcome.YES, 10e18);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 32);
        _quorum(id, PredictionMarket.ResolutionChoice.VOID);
        _state(id, PredictionMarket.MarketState.VOID);
        vm.prank(TRADER);
        require(market.claimPayout(id) == 5e18, "VOID payout");
        _accounting();
    }

    function testReplacementUsesFreshCandidatesWhenFiveAlternativesExist() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 22);
        PredictionMarket.ResolverRound memory first = market.getResolverRound(id, 1);
        vm.warp(first.voteDeadline);
        market.advanceResolution(id);
        PredictionMarket.ResolverRound memory second = market.getResolverRound(id, 2);
        require(
            second.candidates.length == 5 && second.selectionDeadline == block.timestamp + 7 days,
            "replacement snapshot/deadline"
        );
        for (uint256 i; i < 5; ++i) {
            for (uint256 j; j < 5; ++j) {
                require(second.candidates[i] != first.committee[j], "old resolver reused unnecessarily");
            }
        }
        vrf.fulfill(market, second.currentRequestId, 23);
        _quorum(id, PredictionMarket.ResolutionChoice.NO);
        _state(id, PredictionMarket.MarketState.FINALIZED);
    }

    function testReplacementReusesEligibleAddressesWhenFreshPoolIsTooSmall() public {
        for (uint256 i = 6; i < 10; ++i) {
            registry.setResolverStatus(_resolver(i), false);
        }
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 22);
        vm.warp(market.getResolverRound(id, 1).voteDeadline);
        market.advanceResolution(id);
        require(market.getResolverRound(id, 2).candidates.length == 6, "eligible reuse fallback missing");
    }

    function testRoundTwoNoQuorumEndsVoidWithoutThirdRound() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 3);
        vm.warp(market.getResolverRound(id, 1).voteDeadline);
        market.advanceResolution(id);
        PredictionMarket.ResolverRound memory second = market.getResolverRound(id, 2);
        vrf.fulfill(market, second.currentRequestId, 4);
        second = market.getResolverRound(id, 2);
        for (uint256 i; i < 5; ++i) {
            vm.prank(second.committee[i]);
            market.voteOnOutcome(id, PredictionMarket.ResolutionChoice(i % 3));
        }
        vm.warp(second.voteDeadline);
        market.advanceResolution(id);
        _state(id, PredictionMarket.MarketState.VOID);
        require(market.getResolution(id).round == 2, "third round opened");
        vm.expectPartialRevert(PredictionMarket.WrongState.selector);
        market.advanceResolution(id);
    }

    function testReplacementFormationExpiryAlsoEndsVoid() public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        vrf.fulfill(market, requestId, 3);
        for (uint256 i; i < 10; ++i) {
            registry.setResolverStatus(_resolver(i), false);
        }
        vm.warp(market.getResolverRound(id, 1).voteDeadline);
        market.advanceResolution(id);
        require(!market.getResolverRound(id, 2).snapshotFrozen, "empty replacement frozen");
        vm.warp(market.getResolverRound(id, 2).selectionDeadline);
        market.advanceResolution(id);
        _state(id, PredictionMarket.MarketState.VOID);
    }

    function testNoProposalTimeoutStartsResolverPathWithoutBond() public {
        uint256 id = _create(0);
        uint256 timeout = market.getMarket(id).tradingDeadline + 7 days;
        vm.warp(timeout - 1);
        vm.expectRevert(PredictionMarket.DeadlineNotReached.selector);
        market.requestResolverSelection(id);
        vm.warp(timeout);
        market.requestResolverSelection(id);
        vrf.fulfill(market, market.getResolverRound(id, 1).currentRequestId, 12);
        _quorum(id, PredictionMarket.ResolutionChoice.YES);
        require(!market.getResolution(id).proposed && market.totalChallengeBonds() == 0, "phantom proposal/bond");
        _state(id, PredictionMarket.MarketState.FINALIZED);
        _accounting();
    }

    function testFuzzCommitteeIsDistinctAndWithinFrozenPool(uint256 randomWord) public {
        uint256 id = _create(0);
        uint256 requestId = _dispute(id, PredictionMarket.ResolutionChoice.YES);
        address[] memory snapshot = market.getResolverRound(id, 1).candidates;
        vrf.fulfill(market, requestId, randomWord);
        _distinct(snapshot, market.getResolverRound(id, 1).committee);
    }

    function _distinct(address[] memory pool, address[5] memory committee) private pure {
        for (uint256 i; i < 5; ++i) {
            bool found;
            for (uint256 j; j < pool.length; ++j) {
                if (committee[i] == pool[j]) found = true;
            }
            require(found && committee[i] != address(0), "selection outside snapshot");
            for (uint256 j; j < i; ++j) {
                require(committee[i] != committee[j], "duplicate committee member");
            }
        }
    }

    function _ignored(VmMarket.Log[] memory logs, PredictionMarket.IgnoreReason reason) private view {
        require(logs.length == 1 && logs[0].emitter == address(market), "expected only ignored event");
        require(logs[0].topics[0] == keccak256("VRFFulfillmentIgnored(uint256,uint256,uint8,uint8)"), "wrong event");
        require(abi.decode(logs[0].data, (uint8)) == uint8(reason), "wrong ignored reason");
    }
}
