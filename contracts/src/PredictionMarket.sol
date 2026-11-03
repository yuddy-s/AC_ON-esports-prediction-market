// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20Minimal} from "./IERC20Minimal.sol";
import {MarketPricing} from "./MarketPricing.sol";
import {MarketAccess} from "./MarketAccess.sol";
import {ResolverRegistry} from "./ResolverRegistry.sol";
import {IVRFCoordinatorV2Plus} from "./IVRFCoordinatorV2Plus.sol";

/// @notice Fixture-based prediction market. ACON is a fixed, fee-free payment asset.
/// @dev Requires a fresh deployment. ABI consumer review and Matthew's economic sign-off
/// are release gates, not claims established by these contract-side checks.
contract PredictionMarket is MarketAccess {
    enum MarketState {
        OPEN,
        CLOSED,
        PROPOSED,
        DISPUTED,
        RESOLVER_SELECTION,
        RESOLVER_VOTING,
        FINALIZED,
        VOID
    }
    enum Outcome {
        YES,
        NO
    }
    enum ResolutionChoice {
        YES,
        NO,
        VOID
    }
    enum IgnoreReason {
        UNKNOWN_REQUEST,
        SUPERSEDED,
        CONSUMED,
        WRONG_PHASE,
        EXPIRED,
        INVALID_WORD_COUNT
    }

    struct DeploymentConfig {
        address paymentToken;
        address pricing;
        address resolverRegistry;
        address coordinator;
        address initialAdmin;
        bytes32 keyHash;
        uint256 subscriptionId;
        uint32 callbackGasLimit;
    }

    struct FixtureData {
        string providerId;
        string gameId;
        string externalMatchId;
        string teamAId;
        string teamBId;
        string teamAName;
        string teamBName;
        uint256 scheduledStart;
        bytes32 evidenceHash;
        string evidenceURI;
    }

    struct Fixture {
        FixtureData data;
        address registrar;
        bytes32 revisionHash;
        bool registered;
        bool hasMarket;
        uint256 marketId;
    }

    struct Market {
        uint256 id;
        bytes32 fixtureKey;
        string question;
        uint256 tradingDeadline;
        MarketState state;
        address creator;
        uint256 yesQuantity;
        uint256 noQuantity;
        uint256 collateralBalance;
    }

    struct Resolution {
        bool proposed;
        ResolutionChoice proposal;
        address proposer;
        bytes32 proposalEvidenceHash;
        string proposalEvidenceURI;
        uint256 challengeDeadline;
        address challenger;
        bytes32 challengeEvidenceHash;
        uint256 bondEscrow;
        uint8 round;
        bool terminal;
        ResolutionChoice finalOutcome;
    }

    struct ResolverRound {
        uint256 selectionDeadline;
        uint256 voteDeadline;
        uint256 lastRequestAt;
        uint256 currentRequestId;
        bool snapshotFrozen;
        bool hasRequest;
        bool fulfilled;
        address[] candidates;
        address[5] committee;
        uint8[3] voteCounts;
    }

    struct VRFRequest {
        bool exists;
        bool consumed;
        uint256 marketId;
        uint8 round;
    }

    uint256 public constant REQUIRED_SUBSIDY = 34_657_359_027_997_265_471;
    uint256 public constant CHALLENGE_BOND = 10e18;
    uint256 public constant MIN_START_MARGIN = 15 minutes;
    uint256 public constant CHALLENGE_PERIOD = 24 hours;
    uint256 public constant NO_PROPOSAL_PERIOD = 7 days;
    uint256 public constant SELECTION_PERIOD = 7 days;
    uint256 public constant VOTING_PERIOD = 48 hours;
    uint256 public constant RETRY_DELAY = 30 minutes;
    uint16 public constant VRF_CONFIRMATIONS = 3;

    IERC20Minimal public immutable paymentToken;
    MarketPricing public immutable pricing;
    ResolverRegistry public immutable resolverRegistry;
    IVRFCoordinatorV2Plus public immutable vrfCoordinator;
    bytes32 public immutable vrfKeyHash;
    uint256 public immutable vrfSubscriptionId;
    uint32 public immutable vrfCallbackGasLimit;
    uint256 public marketCount;
    uint256 public totalCollateral;
    uint256 public totalChallengeBonds;
    uint256 private reentrancyStatus = 1;

    mapping(bytes32 => Fixture) private fixtures;
    mapping(bytes32 => mapping(address => bool)) public fixtureRegistrars;
    mapping(uint256 => Market) private markets;
    mapping(uint256 => Resolution) private resolutions;
    mapping(uint256 => mapping(address => mapping(Outcome => uint256))) private positions;
    mapping(uint256 => mapping(address => bool)) public hasTraded;
    mapping(uint256 => mapping(address => bool)) public hasClaimed;
    mapping(uint256 => mapping(uint8 => ResolverRound)) private rounds;
    mapping(uint256 => mapping(uint8 => mapping(address => bool))) public hasVoted;
    mapping(uint256 => VRFRequest) public vrfRequests;

    error InvalidConfiguration();
    error InvalidFixture();
    error FixtureNotRegistered(bytes32 fixtureKey);
    error FixtureLocked(bytes32 fixtureKey);
    error FixtureRevisionMismatch();
    error MarketAlreadyExists(bytes32 fixtureKey);
    error InvalidTradingDeadline();
    error MarketNotFound(uint256 marketId);
    error WrongState(MarketState actual);
    error TradingClosed();
    error DeadlineNotReached();
    error ProposalExpired();
    error ProposalAlreadyExists();
    error InvalidEvidence();
    error ChallengeNotAllowed();
    error ChallengeAlreadyExists();
    error ChallengeWindowClosed();
    error SlippageExceeded(uint256 actualCost, uint256 maxCost);
    error MinimumReturnNotMet(uint256 proceeds, uint256 minReturn);
    error InsufficientShares(uint256 required, uint256 available);
    error InsufficientTokenBalance(uint256 required, uint256 available);
    error InsufficientTokenAllowance(uint256 required, uint256 available);
    error PaymentTransferFailed();
    error UnexpectedTokenTransfer();
    error InsufficientCollateral();
    error ReentrantCall();
    error OnlyCoordinator();
    error RetryTooSoon(uint256 retryAfter);
    error SelectionExpired();
    error RequestIdCollision();
    error ResolverNotSelected();
    error AlreadyVoted();
    error VotingClosed();
    error AlreadyClaimed();
    error NoPosition();
    error CreatorOnly();
    error NoSurplus();

    event FixtureRegistered(
        bytes32 indexed fixtureKey, address indexed registrar, FixtureData data, bytes32 revisionHash
    );
    event MarketCreated(
        uint256 indexed marketId,
        address indexed creator,
        string question,
        uint256 tradingDeadline,
        bytes32 indexed fixtureKey
    );
    event TradeExecuted(
        uint256 indexed marketId,
        address indexed trader,
        uint8 indexed outcome,
        uint256 shares,
        uint256 cost,
        uint256 yesQuantity,
        uint256 noQuantity
    );
    event SellExecuted(
        uint256 indexed marketId,
        address indexed trader,
        uint8 indexed outcome,
        uint256 shares,
        uint256 proceeds,
        uint256 yesQuantity,
        uint256 noQuantity
    );
    event MarketClosed(uint256 indexed marketId, uint256 tradingDeadline, address indexed caller, bytes32 evidenceHash);
    event OutcomeProposed(
        uint256 indexed marketId,
        address indexed proposer,
        uint8 indexed outcome,
        bytes32 evidenceHash,
        string evidenceURI,
        uint256 challengeDeadline
    );
    event OutcomeChallenged(uint256 indexed marketId, address indexed challenger, bytes32 evidenceHash, uint256 bond);
    event ResolverSelectionPending(
        uint256 indexed marketId, uint8 indexed round, uint256 eligibleCount, uint256 deadline
    );
    event ResolverSelectionRequested(
        uint256 indexed marketId,
        uint8 indexed round,
        uint256 indexed requestId,
        uint256 selectionDeadline,
        bytes32 snapshotHash
    );
    event ResolverSelectionRequestFailed(
        uint256 indexed marketId, uint8 indexed round, bytes32 reasonHash, uint256 retryAfter
    );
    event ResolverCommitteeSelected(
        uint256 indexed marketId,
        uint8 indexed round,
        uint256 indexed requestId,
        address[5] committee,
        uint256 voteDeadline
    );
    event VRFFulfillmentIgnored(uint256 indexed requestId, uint256 indexed marketId, uint8 indexed round, uint8 reason);
    event ResolverVoteCast(
        uint256 indexed marketId, address indexed resolver, uint8 indexed round, uint8 outcome, uint8 votes
    );
    event MarketFinalized(uint256 indexed marketId, uint8 outcome, uint256 remainingLiability);
    event MarketVoided(uint256 indexed marketId, uint256 remainingLiability);
    event ChallengeBondResolved(uint256 indexed marketId, address indexed challenger, uint256 amount, bool refunded);
    event PayoutClaimed(
        uint256 indexed marketId,
        address indexed account,
        uint256 payout,
        uint256 yesShares,
        uint256 noShares,
        uint256 remainingLiability
    );
    event CreatorSurplusWithdrawn(uint256 indexed marketId, address indexed creator, uint256 amount);

    constructor(DeploymentConfig memory config) MarketAccess(config.initialAdmin) {
        if (
            config.paymentToken.code.length == 0 || config.pricing.code.length == 0
                || config.resolverRegistry.code.length == 0 || config.coordinator.code.length == 0
                || config.keyHash == bytes32(0) || config.subscriptionId == 0 || config.callbackGasLimit == 0
        ) {
            revert InvalidConfiguration();
        }
        paymentToken = IERC20Minimal(config.paymentToken);
        pricing = MarketPricing(config.pricing);
        resolverRegistry = ResolverRegistry(config.resolverRegistry);
        vrfCoordinator = IVRFCoordinatorV2Plus(config.coordinator);
        vrfKeyHash = config.keyHash;
        vrfSubscriptionId = config.subscriptionId;
        vrfCallbackGasLimit = config.callbackGasLimit;
    }

    modifier nonReentrant() {
        if (reentrancyStatus != 1) revert ReentrantCall();
        reentrancyStatus = 2;
        _;
        reentrancyStatus = 1;
    }

    function computeFixtureKey(string memory providerId, string memory gameId, string memory externalMatchId)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encode(providerId, gameId, externalMatchId));
    }

    /// @notice Corrections are allowed before funding; creation binds the reviewed revision hash.
    function registerFixture(FixtureData calldata data)
        external
        nonReentrant
        onlyRole(REGISTRAR_ROLE)
        returns (bytes32 key)
    {
        if (
            bytes(data.providerId).length == 0 || bytes(data.gameId).length == 0
                || bytes(data.externalMatchId).length == 0 || bytes(data.teamAId).length == 0
                || bytes(data.teamBId).length == 0 || bytes(data.teamAName).length == 0
                || bytes(data.teamBName).length == 0 || keccak256(bytes(data.teamAId)) == keccak256(bytes(data.teamBId))
                || data.scheduledStart <= block.timestamp + MIN_START_MARGIN
        ) revert InvalidFixture();
        _requireEvidence(data.evidenceHash, data.evidenceURI);
        key = computeFixtureKey(data.providerId, data.gameId, data.externalMatchId);
        Fixture storage fixture = fixtures[key];
        if (fixture.hasMarket) revert FixtureLocked(key);
        fixture.data = data;
        fixture.registrar = msg.sender;
        fixture.revisionHash = keccak256(abi.encode(data));
        fixture.registered = true;
        fixtureRegistrars[key][msg.sender] = true;
        emit FixtureRegistered(key, msg.sender, data, fixture.revisionHash);
    }

    function getFixture(bytes32 key) external view returns (Fixture memory) {
        if (!fixtures[key].registered) revert FixtureNotRegistered(key);
        return fixtures[key];
    }

    function createMarket(bytes32 key, uint256 tradingDeadline, bytes32 expectedFixtureHash)
        external
        nonReentrant
        returns (uint256 marketId)
    {
        Fixture storage fixture = fixtures[key];
        if (!fixture.registered) revert FixtureNotRegistered(key);
        if (fixture.hasMarket) revert MarketAlreadyExists(key);
        if (expectedFixtureHash != fixture.revisionHash) revert FixtureRevisionMismatch();
        if (
            tradingDeadline <= block.timestamp || tradingDeadline > fixture.data.scheduledStart - MIN_START_MARGIN
                || tradingDeadline > type(uint256).max - NO_PROPOSAL_PERIOD
        ) revert InvalidTradingDeadline();
        marketId = marketCount++;
        Market storage market = markets[marketId];
        market.id = marketId;
        market.fixtureKey = key;
        market.question = string.concat("Will ", fixture.data.teamAName, " beat ", fixture.data.teamBName, "?");
        market.tradingDeadline = tradingDeadline;
        market.state = MarketState.OPEN;
        market.creator = msg.sender;
        market.collateralBalance = REQUIRED_SUBSIDY;
        totalCollateral += REQUIRED_SUBSIDY;
        fixture.hasMarket = true;
        fixture.marketId = marketId;
        // Effects precede interaction; every effect rolls back if the exact payment fails.
        _collectPayment(msg.sender, REQUIRED_SUBSIDY);
        emit MarketCreated(marketId, msg.sender, market.question, tradingDeadline, key);
    }

    function getMarket(uint256 marketId) external view returns (Market memory) {
        return _market(marketId);
    }

    function getResolution(uint256 marketId) external view returns (Resolution memory) {
        _market(marketId);
        return resolutions[marketId];
    }

    function getResolverRound(uint256 marketId, uint8 round) external view returns (ResolverRound memory) {
        _market(marketId);
        return rounds[marketId][round];
    }

    function balanceOf(uint256 marketId, address account, Outcome outcome) public view returns (uint256) {
        _market(marketId);
        return positions[marketId][account][outcome];
    }

    function quoteBuy(uint256 marketId, Outcome outcome, uint256 shares) external view returns (uint256) {
        Market storage market = _tradable(marketId);
        return pricing.buyCost(market.yesQuantity, market.noQuantity, outcome == Outcome.YES, shares);
    }

    function buy(uint256 marketId, Outcome outcome, uint256 shares, uint256 maxCost)
        external
        nonReentrant
        returns (uint256 cost)
    {
        Market storage market = _tradable(marketId);
        cost = pricing.buyCost(market.yesQuantity, market.noQuantity, outcome == Outcome.YES, shares);
        if (cost > maxCost) revert SlippageExceeded(cost, maxCost);
        positions[marketId][msg.sender][outcome] += shares;
        hasTraded[marketId][msg.sender] = true;
        if (outcome == Outcome.YES) market.yesQuantity += shares;
        else market.noQuantity += shares;
        market.collateralBalance += cost;
        totalCollateral += cost;
        _collectPayment(msg.sender, cost);
        emit TradeExecuted(marketId, msg.sender, uint8(outcome), shares, cost, market.yesQuantity, market.noQuantity);
    }

    function quoteSell(uint256 marketId, Outcome outcome, uint256 shares) external view returns (uint256) {
        Market storage market = _tradable(marketId);
        return pricing.sellReturn(market.yesQuantity, market.noQuantity, outcome == Outcome.YES, shares);
    }

    function sell(uint256 marketId, Outcome outcome, uint256 shares, uint256 minReturn)
        external
        nonReentrant
        returns (uint256 proceeds)
    {
        Market storage market = _tradable(marketId);
        uint256 owned = positions[marketId][msg.sender][outcome];
        if (owned < shares) revert InsufficientShares(shares, owned);
        proceeds = pricing.sellReturn(market.yesQuantity, market.noQuantity, outcome == Outcome.YES, shares);
        if (proceeds < minReturn) revert MinimumReturnNotMet(proceeds, minReturn);
        positions[marketId][msg.sender][outcome] = owned - shares;
        hasTraded[marketId][msg.sender] = true;
        if (outcome == Outcome.YES) market.yesQuantity -= shares;
        else market.noQuantity -= shares;
        _decreaseCollateral(market, proceeds);
        _sendPayment(msg.sender, proceeds);
        emit SellExecuted(marketId, msg.sender, uint8(outcome), shares, proceeds, market.yesQuantity, market.noQuantity);
    }

    /// @notice Anyone can close an expired market. Only a registrar can shorten its deadline.
    function closeTrading(uint256 marketId, bytes32 evidenceHash) external nonReentrant {
        Market storage market = _market(marketId);
        if (market.state != MarketState.OPEN) revert WrongState(market.state);
        if (block.timestamp < market.tradingDeadline) {
            if (!hasRole(REGISTRAR_ROLE, msg.sender)) revert Unauthorized(REGISTRAR_ROLE, msg.sender);
            if (evidenceHash == bytes32(0)) revert InvalidEvidence();
            market.tradingDeadline = block.timestamp;
        }
        _close(market, evidenceHash);
    }

    function proposeOutcome(
        uint256 marketId,
        ResolutionChoice outcome,
        bytes32 evidenceHash,
        string calldata evidenceURI
    ) external nonReentrant onlyRole(PROPOSER_ROLE) {
        Market storage market = _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        if (resolution.proposed) revert ProposalAlreadyExists();
        if (market.state == MarketState.OPEN) {
            if (block.timestamp < market.tradingDeadline) revert DeadlineNotReached();
            _close(market, bytes32(0));
        }
        if (market.state != MarketState.CLOSED) revert WrongState(market.state);
        if (block.timestamp >= market.tradingDeadline + NO_PROPOSAL_PERIOD) revert ProposalExpired();
        _requireEvidence(evidenceHash, evidenceURI);
        resolution.proposed = true;
        resolution.proposal = outcome;
        resolution.proposer = msg.sender;
        resolution.proposalEvidenceHash = evidenceHash;
        resolution.proposalEvidenceURI = evidenceURI;
        resolution.challengeDeadline = block.timestamp + CHALLENGE_PERIOD;
        market.state = MarketState.PROPOSED;
        emit OutcomeProposed(
            marketId, msg.sender, uint8(outcome), evidenceHash, evidenceURI, resolution.challengeDeadline
        );
    }

    function challengeOutcome(uint256 marketId, bytes32 evidenceHash) external nonReentrant {
        Market storage market = _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        if (resolution.challenger != address(0)) revert ChallengeAlreadyExists();
        if (market.state != MarketState.PROPOSED) revert WrongState(market.state);
        if (block.timestamp >= resolution.challengeDeadline) revert ChallengeWindowClosed();
        if (msg.sender == resolution.proposer) revert ChallengeNotAllowed();
        if (evidenceHash == bytes32(0)) revert InvalidEvidence();
        resolution.challenger = msg.sender;
        resolution.challengeEvidenceHash = evidenceHash;
        resolution.bondEscrow = CHALLENGE_BOND;
        totalChallengeBonds += CHALLENGE_BOND;
        market.state = MarketState.DISPUTED;
        _collectPayment(msg.sender, CHALLENGE_BOND);
        emit OutcomeChallenged(marketId, msg.sender, evidenceHash, CHALLENGE_BOND);
    }

    function finalize(uint256 marketId) external nonReentrant {
        Market storage market = _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        if (market.state != MarketState.PROPOSED) revert WrongState(market.state);
        if (block.timestamp < resolution.challengeDeadline) revert DeadlineNotReached();
        _settle(market, resolution.proposal);
    }

    function requestResolverSelection(uint256 marketId) external nonReentrant {
        Market storage market = _market(marketId);
        if (market.state != MarketState.DISPUTED) {
            if (market.state != MarketState.OPEN && market.state != MarketState.CLOSED) {
                revert WrongState(market.state);
            }
            if (block.timestamp < market.tradingDeadline + NO_PROPOSAL_PERIOD) revert DeadlineNotReached();
            if (market.state == MarketState.OPEN) _close(market, bytes32(0));
        }
        _beginRound(market, 1);
    }

    function retryResolverSelection(uint256 marketId) external nonReentrant {
        Market storage market = _market(marketId);
        if (market.state != MarketState.RESOLVER_SELECTION) revert WrongState(market.state);
        _requestRandomness(market);
    }

    /// @notice Permissionless deadline processing; time alone never changes storage.
    function advanceResolution(uint256 marketId) external nonReentrant {
        Market storage market = _market(marketId);
        uint8 round = resolutions[marketId].round;
        ResolverRound storage selection = rounds[marketId][round];
        if (market.state == MarketState.RESOLVER_SELECTION) {
            if (block.timestamp < selection.selectionDeadline) revert DeadlineNotReached();
            _settle(market, ResolutionChoice.VOID);
        } else if (market.state == MarketState.RESOLVER_VOTING) {
            if (block.timestamp < selection.voteDeadline) revert DeadlineNotReached();
            if (round == 1) _beginRound(market, 2);
            else _settle(market, ResolutionChoice.VOID);
        } else {
            revert WrongState(market.state);
        }
    }

    /// @notice Only the configured v2.5 coordinator can supply randomness.
    function rawFulfillRandomWords(uint256 requestId, uint256[] calldata randomWords) external nonReentrant {
        if (msg.sender != address(vrfCoordinator)) revert OnlyCoordinator();
        VRFRequest storage request = vrfRequests[requestId];
        if (!request.exists) {
            _ignore(requestId, request, IgnoreReason.UNKNOWN_REQUEST);
            return;
        }
        ResolverRound storage selection = rounds[request.marketId][request.round];
        if (request.consumed) {
            _ignore(requestId, request, IgnoreReason.CONSUMED);
            return;
        }
        if (!selection.hasRequest || selection.currentRequestId != requestId) {
            _ignore(requestId, request, IgnoreReason.SUPERSEDED);
            return;
        }
        Market storage market = markets[request.marketId];
        if (market.state != MarketState.RESOLVER_SELECTION || resolutions[request.marketId].round != request.round) {
            _ignore(requestId, request, IgnoreReason.WRONG_PHASE);
            return;
        }
        if (block.timestamp >= selection.selectionDeadline) {
            _ignore(requestId, request, IgnoreReason.EXPIRED);
            return;
        }
        if (randomWords.length != 1) {
            _ignore(requestId, request, IgnoreReason.INVALID_WORD_COUNT);
            return;
        }
        address[] memory pool = selection.candidates;
        uint256 remaining = pool.length;
        for (uint256 i; i < 5; ++i) {
            uint256 random = uint256(keccak256(abi.encode(randomWords[0], request.marketId, request.round, i)));
            uint256 limit = type(uint256).max - (type(uint256).max % remaining);
            while (random >= limit) random = uint256(keccak256(abi.encode(random)));
            uint256 index = random % remaining;
            selection.committee[i] = pool[index];
            pool[index] = pool[--remaining];
        }
        request.consumed = true;
        selection.fulfilled = true;
        selection.voteDeadline = block.timestamp + VOTING_PERIOD;
        market.state = MarketState.RESOLVER_VOTING;
        emit ResolverCommitteeSelected(
            request.marketId, request.round, requestId, selection.committee, selection.voteDeadline
        );
    }

    function voteOnOutcome(uint256 marketId, ResolutionChoice outcome) external nonReentrant {
        Market storage market = _market(marketId);
        if (market.state != MarketState.RESOLVER_VOTING) revert WrongState(market.state);
        uint8 round = resolutions[marketId].round;
        ResolverRound storage selection = rounds[marketId][round];
        if (block.timestamp >= selection.voteDeadline) revert VotingClosed();
        if (!_inCommittee(selection.committee, msg.sender)) revert ResolverNotSelected();
        if (hasVoted[marketId][round][msg.sender]) revert AlreadyVoted();
        hasVoted[marketId][round][msg.sender] = true;
        uint8 votes = ++selection.voteCounts[uint8(outcome)];
        emit ResolverVoteCast(marketId, msg.sender, round, uint8(outcome), votes);
        if (votes == 3) _settle(market, outcome);
    }

    function isResolverEligible(uint256 marketId, address account) public view returns (bool) {
        Market storage market = _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        return resolverRegistry.isActiveResolver(account)
            && _notConflicted(market, resolution, account, resolverRegistry.admin());
    }

    function _notConflicted(
        Market storage market,
        Resolution storage resolution,
        address account,
        address registryAdmin
    ) private view returns (bool) {
        uint256 marketId = market.id;
        return account != address(0) && account != registryAdmin && account != market.creator
            && !fixtureRegistrars[market.fixtureKey][account] && account != resolution.proposer
            && account != resolution.challenger && !hasTraded[marketId][account]
            && positions[marketId][account][Outcome.YES] == 0 && positions[marketId][account][Outcome.NO] == 0;
    }

    function isSelectedResolver(uint256 marketId, uint8 round, address account) external view returns (bool) {
        _market(marketId);
        return rounds[marketId][round].fulfilled && _inCommittee(rounds[marketId][round].committee, account);
    }

    function claimableAmount(uint256 marketId, address account) public view returns (uint256) {
        _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        if (!resolution.terminal || hasClaimed[marketId][account]) return 0;
        uint256 yes = positions[marketId][account][Outcome.YES];
        uint256 no = positions[marketId][account][Outcome.NO];
        if (resolution.finalOutcome == ResolutionChoice.VOID) return (yes + no) / 2;
        return resolution.finalOutcome == ResolutionChoice.YES ? yes : no;
    }

    function remainingLiability(uint256 marketId) public view returns (uint256) {
        Market storage market = _market(marketId);
        Resolution storage resolution = resolutions[marketId];
        if (!resolution.terminal) {
            return market.yesQuantity >= market.noQuantity ? market.yesQuantity : market.noQuantity;
        }
        if (resolution.finalOutcome == ResolutionChoice.VOID) {
            uint256 total = market.yesQuantity + market.noQuantity;
            return total / 2 + total % 2;
        }
        return resolution.finalOutcome == ResolutionChoice.YES ? market.yesQuantity : market.noQuantity;
    }

    function withdrawableSurplus(uint256 marketId) public view returns (uint256) {
        Market storage market = _market(marketId);
        if (!resolutions[marketId].terminal) return 0;
        uint256 liability = remainingLiability(marketId);
        return market.collateralBalance > liability ? market.collateralBalance - liability : 0;
    }

    function claimPayout(uint256 marketId) external nonReentrant returns (uint256 payout) {
        Market storage market = _market(marketId);
        if (!resolutions[marketId].terminal) revert WrongState(market.state);
        if (hasClaimed[marketId][msg.sender]) revert AlreadyClaimed();
        uint256 yes = positions[marketId][msg.sender][Outcome.YES];
        uint256 no = positions[marketId][msg.sender][Outcome.NO];
        if (yes + no == 0) revert NoPosition();
        payout = claimableAmount(marketId, msg.sender);
        hasClaimed[marketId][msg.sender] = true;
        delete positions[marketId][msg.sender][Outcome.YES];
        delete positions[marketId][msg.sender][Outcome.NO];
        market.yesQuantity -= yes;
        market.noQuantity -= no;
        _decreaseCollateral(market, payout);
        if (payout != 0) _sendPayment(msg.sender, payout);
        emit PayoutClaimed(marketId, msg.sender, payout, yes, no, remainingLiability(marketId));
    }

    function withdrawCreatorSurplus(uint256 marketId) external nonReentrant returns (uint256 amount) {
        Market storage market = _market(marketId);
        if (msg.sender != market.creator) revert CreatorOnly();
        if (!resolutions[marketId].terminal) revert WrongState(market.state);
        amount = withdrawableSurplus(marketId);
        if (amount == 0) revert NoSurplus();
        _decreaseCollateral(market, amount);
        _sendPayment(msg.sender, amount);
        emit CreatorSurplusWithdrawn(marketId, msg.sender, amount);
    }

    function _beginRound(Market storage market, uint8 round) private {
        Resolution storage resolution = resolutions[market.id];
        resolution.round = round;
        ResolverRound storage selection = rounds[market.id][round];
        selection.selectionDeadline = block.timestamp + SELECTION_PERIOD;
        market.state = MarketState.RESOLVER_SELECTION;
        _requestRandomness(market);
    }

    function _requestRandomness(Market storage market) private {
        uint8 round = resolutions[market.id].round;
        ResolverRound storage selection = rounds[market.id][round];
        if (block.timestamp >= selection.selectionDeadline) revert SelectionExpired();
        if (!selection.snapshotFrozen) {
            address[] memory eligible = _eligibleCandidates(market.id, round);
            if (eligible.length < 5) {
                emit ResolverSelectionPending(market.id, round, eligible.length, selection.selectionDeadline);
                return;
            }
            selection.candidates = eligible;
            selection.snapshotFrozen = true;
        } else if (block.timestamp < selection.lastRequestAt + RETRY_DELAY) {
            revert RetryTooSoon(selection.lastRequestAt + RETRY_DELAY);
        }
        selection.lastRequestAt = block.timestamp;
        // A retry supersedes the old ID even if the new coordinator request fails.
        selection.hasRequest = false;
        IVRFCoordinatorV2Plus.RandomWordsRequest memory request = IVRFCoordinatorV2Plus.RandomWordsRequest({
            keyHash: vrfKeyHash,
            subId: vrfSubscriptionId,
            requestConfirmations: VRF_CONFIRMATIONS,
            callbackGasLimit: vrfCallbackGasLimit,
            numWords: 1,
            extraArgs: abi.encodeWithSelector(bytes4(keccak256("VRF ExtraArgsV1")), false)
        });
        try vrfCoordinator.requestRandomWords(request) returns (uint256 requestId) {
            if (vrfRequests[requestId].exists) revert RequestIdCollision();
            selection.currentRequestId = requestId;
            selection.hasRequest = true;
            vrfRequests[requestId] = VRFRequest(true, false, market.id, round);
            emit ResolverSelectionRequested(
                market.id, round, requestId, selection.selectionDeadline, keccak256(abi.encode(selection.candidates))
            );
        } catch (bytes memory reason) {
            emit ResolverSelectionRequestFailed(market.id, round, keccak256(reason), block.timestamp + RETRY_DELAY);
        }
    }

    function _eligibleCandidates(uint256 marketId, uint8 round) private view returns (address[] memory) {
        address[] memory all = resolverRegistry.getActiveResolvers();
        address registryAdmin = resolverRegistry.admin();
        Market storage market = markets[marketId];
        Resolution storage resolution = resolutions[marketId];
        address[] memory eligible = new address[](all.length);
        uint256 count = 0;
        uint256 fresh = 0;
        for (uint256 i; i < all.length; ++i) {
            if (_notConflicted(market, resolution, all[i], registryAdmin)) {
                eligible[count++] = all[i];
                if (round != 2 || !_inCommittee(rounds[marketId][1].committee, all[i])) ++fresh;
            }
        }
        bool excludePrevious = round == 2 && fresh >= 5;
        address[] memory result = new address[](excludePrevious ? fresh : count);
        uint256 index = 0;
        for (uint256 i; i < count; ++i) {
            if (!excludePrevious || !_inCommittee(rounds[marketId][1].committee, eligible[i])) {
                result[index++] = eligible[i];
            }
        }
        return result;
    }

    function _settle(Market storage market, ResolutionChoice outcome) private {
        Resolution storage resolution = resolutions[market.id];
        resolution.terminal = true;
        resolution.finalOutcome = outcome;
        market.state = outcome == ResolutionChoice.VOID ? MarketState.VOID : MarketState.FINALIZED;
        uint256 bond = resolution.bondEscrow;
        if (bond != 0) {
            resolution.bondEscrow = 0;
            totalChallengeBonds -= bond;
            bool refund = outcome != resolution.proposal;
            if (refund) {
                _sendPayment(resolution.challenger, bond);
            } else {
                market.collateralBalance += bond;
                totalCollateral += bond;
            }
            emit ChallengeBondResolved(market.id, resolution.challenger, bond, refund);
        }
        uint256 liability = remainingLiability(market.id);
        if (market.collateralBalance < liability) revert InsufficientCollateral();
        if (outcome == ResolutionChoice.VOID) emit MarketVoided(market.id, liability);
        else emit MarketFinalized(market.id, uint8(outcome), liability);
    }

    function _ignore(uint256 requestId, VRFRequest storage request, IgnoreReason reason) private {
        emit VRFFulfillmentIgnored(requestId, request.marketId, request.round, uint8(reason));
    }

    function _inCommittee(address[5] storage committee, address account) private view returns (bool) {
        for (uint256 i; i < 5; ++i) {
            if (committee[i] == account) return true;
        }
        return false;
    }

    function _market(uint256 marketId) private view returns (Market storage market) {
        if (marketId >= marketCount) revert MarketNotFound(marketId);
        return markets[marketId];
    }

    function _tradable(uint256 marketId) private view returns (Market storage market) {
        market = _market(marketId);
        if (market.state != MarketState.OPEN) revert WrongState(market.state);
        if (block.timestamp >= market.tradingDeadline) revert TradingClosed();
    }

    function _close(Market storage market, bytes32 evidenceHash) private {
        market.state = MarketState.CLOSED;
        emit MarketClosed(market.id, market.tradingDeadline, msg.sender, evidenceHash);
    }

    function _requireEvidence(bytes32 evidenceHash, string memory evidenceURI) private pure {
        if (evidenceHash == bytes32(0) || bytes(evidenceURI).length == 0) revert InvalidEvidence();
    }

    function _decreaseCollateral(Market storage market, uint256 amount) private {
        if (amount > market.collateralBalance) revert InsufficientCollateral();
        market.collateralBalance -= amount;
        totalCollateral -= amount;
    }

    function _collectPayment(address payer, uint256 amount) private {
        uint256 balance = paymentToken.balanceOf(payer);
        if (balance < amount) revert InsufficientTokenBalance(amount, balance);
        uint256 allowance = paymentToken.allowance(payer, address(this));
        if (allowance < amount) revert InsufficientTokenAllowance(amount, allowance);
        uint256 beforeBalance = paymentToken.balanceOf(address(this));
        if (!paymentToken.transferFrom(payer, address(this), amount)) revert PaymentTransferFailed();
        if (paymentToken.balanceOf(address(this)) != beforeBalance + amount) revert UnexpectedTokenTransfer();
    }

    function _sendPayment(address recipient, uint256 amount) private {
        uint256 beforeBalance = paymentToken.balanceOf(address(this));
        uint256 recipientBefore = paymentToken.balanceOf(recipient);
        if (beforeBalance < amount) revert InsufficientCollateral();
        if (!paymentToken.transfer(recipient, amount)) revert PaymentTransferFailed();
        if (
            paymentToken.balanceOf(address(this)) != beforeBalance - amount
                || paymentToken.balanceOf(recipient) != recipientBefore + amount
        ) {
            revert UnexpectedTokenTransfer();
        }
    }
}
