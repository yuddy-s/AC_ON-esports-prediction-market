// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20Minimal} from "../src/IERC20Minimal.sol";
import {LMSR} from "../src/LMSR.sol";
import {MarketAccess} from "../src/MarketAccess.sol";
import {MarketPricing} from "../src/MarketPricing.sol";
import {ResolverRegistry} from "../src/ResolverRegistry.sol";
import {IVRFCoordinatorV2Plus} from "../src/IVRFCoordinatorV2Plus.sol";
import {PredictionMarket} from "../src/PredictionMarket.sol";

interface VmMarket {
    struct Log {
        bytes32[] topics;
        bytes data;
        address emitter;
    }
    function warp(uint256) external;
    function prank(address) external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
    function expectPartialRevert(bytes4) external;
    function recordLogs() external;
    function getRecordedLogs() external returns (Log[] memory);
    function toString(uint256) external pure returns (string memory);
}

contract PaymentTokenMock is IERC20Minimal {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    bool public failIncoming;
    bool public failOutgoing;
    bool public changeBeforeFailure;
    bool public skim;
    address public callbackTarget;
    bytes public callbackData;
    bool public callbackIncoming;
    bool public callbackOutgoing;
    bool public callbackSucceeded;
    bytes public callbackResult;

    function mint(address account, uint256 amount) external {
        balanceOf[account] += amount;
    }

    function setFailures(bool incoming, bool outgoing, bool mutateFirst) external {
        failIncoming = incoming;
        failOutgoing = outgoing;
        changeBeforeFailure = mutateFirst;
    }

    function setSkim(bool value) external {
        skim = value;
    }

    function setCallback(address target, bytes calldata data, bool incoming, bool outgoing) external {
        callbackTarget = target;
        callbackData = data;
        callbackIncoming = incoming;
        callbackOutgoing = outgoing;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        if (failIncoming && !changeBeforeFailure) return false;
        require(allowance[from][msg.sender] >= amount, "allowance");
        if (allowance[from][msg.sender] != type(uint256).max) allowance[from][msg.sender] -= amount;
        _move(from, to, amount);
        if (callbackIncoming) _callback();
        return !failIncoming;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        if (failOutgoing && !changeBeforeFailure) return false;
        _move(msg.sender, to, amount);
        if (callbackOutgoing) _callback();
        return !failOutgoing;
    }

    function _move(address from, address to, uint256 amount) private {
        require(balanceOf[from] >= amount, "balance");
        balanceOf[from] -= amount;
        balanceOf[to] += skim && amount > 0 ? amount - 1 : amount;
    }

    function _callback() private {
        (callbackSucceeded, callbackResult) = callbackTarget.call(callbackData);
    }
}

contract VRFCoordinatorMock is IVRFCoordinatorV2Plus {
    uint256 public nextId = 1;
    bool public failRequests;
    bytes32 public lastKeyHash;
    uint256 public lastSubscription;
    uint16 public lastConfirmations;
    uint32 public lastCallbackGas;
    uint32 public lastWordCount;
    bytes public lastExtraArgs;
    address public lastConsumer;
    address public callbackTarget;
    bytes public callbackData;
    bool public callbackSucceeded;
    bytes public callbackResult;
    error RequestFailed();

    function setFailure(bool value) external {
        failRequests = value;
    }

    function setNextId(uint256 value) external {
        nextId = value;
    }

    function setCallback(address target, bytes calldata data) external {
        callbackTarget = target;
        callbackData = data;
    }

    function requestRandomWords(RandomWordsRequest calldata request) external returns (uint256 id) {
        if (failRequests) revert RequestFailed();
        lastKeyHash = request.keyHash;
        lastSubscription = request.subId;
        lastConfirmations = request.requestConfirmations;
        lastCallbackGas = request.callbackGasLimit;
        lastWordCount = request.numWords;
        lastExtraArgs = request.extraArgs;
        lastConsumer = msg.sender;
        if (callbackTarget != address(0)) (callbackSucceeded, callbackResult) = callbackTarget.call(callbackData);
        return nextId++;
    }

    function fulfill(PredictionMarket market, uint256 requestId, uint256 word) external {
        uint256[] memory words = new uint256[](1);
        words[0] = word;
        market.rawFulfillRandomWords(requestId, words);
    }

    function malformed(PredictionMarket market, uint256 requestId) external {
        market.rawFulfillRandomWords(requestId, new uint256[](0));
    }
}

abstract contract MarketTestBase {
    VmMarket internal constant vm = VmMarket(address(uint160(uint256(keccak256("hevm cheat code")))));
    address internal constant CREATOR = address(0xC0FE);
    address internal constant REGISTRAR = address(0xA11);
    address internal constant PROPOSER = address(0xB0B);
    address internal constant CHALLENGER = address(0xCAFE);
    address internal constant TRADER = address(0xD00D);
    address internal constant OTHER = address(0xD0D2);
    address internal constant SAFE = address(0x5AFE);
    uint256 internal constant WAD = 1e18;

    PaymentTokenMock internal token;
    VRFCoordinatorMock internal vrf;
    MarketPricing internal pricing;
    ResolverRegistry internal registry;
    PredictionMarket internal market;

    function setUp() public virtual {
        vm.warp(1_800_000_000);
        token = new PaymentTokenMock();
        vrf = new VRFCoordinatorMock();
        pricing = new MarketPricing();
        registry = new ResolverRegistry(address(this));
        market = new PredictionMarket(
            PredictionMarket.DeploymentConfig({
                paymentToken: address(token),
                pricing: address(pricing),
                resolverRegistry: address(registry),
                coordinator: address(vrf),
                initialAdmin: address(this),
                keyHash: bytes32(uint256(1)),
                subscriptionId: 1,
                callbackGasLimit: 2_000_000
            })
        );
        market.grantRole(market.REGISTRAR_ROLE(), REGISTRAR);
        market.grantRole(market.PROPOSER_ROLE(), PROPOSER);
        _fund(CREATOR);
        _fund(PROPOSER);
        _fund(CHALLENGER);
        _fund(TRADER);
        _fund(OTHER);
        _addResolvers(10);
    }

    function _fund(address account) internal {
        token.mint(account, 10_000e18);
        vm.prank(account);
        token.approve(address(market), type(uint256).max);
    }

    function _resolver(uint256 index) internal pure returns (address) {
        return address(uint160(0x1000 + index));
    }

    function _addResolvers(uint256 count) internal {
        for (uint256 i; i < count; ++i) {
            registry.setResolverStatus(_resolver(i), true);
        }
    }

    function _data(uint256 seed) internal view returns (PredictionMarket.FixtureData memory) {
        return PredictionMarket.FixtureData({
            providerId: "manual",
            gameId: "valorant",
            externalMatchId: vm.toString(seed),
            teamAId: "team-a",
            teamBId: "team-b",
            teamAName: "Team A",
            teamBName: "Team B",
            scheduledStart: block.timestamp + 2 days,
            evidenceHash: keccak256("organizer-evidence"),
            evidenceURI: "https://example.invalid/organizer/demo"
        });
    }

    function _register(uint256 seed) internal returns (bytes32 key) {
        PredictionMarket.FixtureData memory data = _data(seed);
        vm.prank(REGISTRAR);
        return market.registerFixture(data);
    }

    function _create(uint256 seed) internal returns (uint256 id) {
        bytes32 key = _register(seed);
        bytes32 revision = market.getFixture(key).revisionHash;
        vm.prank(CREATOR);
        return market.createMarket(key, block.timestamp + 1 days, revision);
    }

    function _buy(address account, uint256 id, PredictionMarket.Outcome outcome, uint256 shares)
        internal
        returns (uint256 cost)
    {
        cost = market.quoteBuy(id, outcome, shares);
        vm.prank(account);
        return market.buy(id, outcome, shares, cost);
    }

    function _proposal(uint256 id, PredictionMarket.ResolutionChoice outcome) internal {
        vm.warp(market.getMarket(id).tradingDeadline);
        vm.prank(PROPOSER);
        market.proposeOutcome(id, outcome, keccak256("result"), "https://example.invalid/result");
    }

    function _unchallenged(uint256 id, PredictionMarket.ResolutionChoice outcome) internal {
        _proposal(id, outcome);
        vm.warp(market.getResolution(id).challengeDeadline);
        market.finalize(id);
    }

    function _dispute(uint256 id, PredictionMarket.ResolutionChoice outcome) internal returns (uint256 requestId) {
        _proposal(id, outcome);
        vm.prank(CHALLENGER);
        market.challengeOutcome(id, keccak256("challenge"));
        market.requestResolverSelection(id);
        return market.getResolverRound(id, 1).currentRequestId;
    }

    function _quorum(uint256 id, PredictionMarket.ResolutionChoice choice) internal {
        uint8 round = market.getResolution(id).round;
        PredictionMarket.ResolverRound memory info = market.getResolverRound(id, round);
        for (uint256 i; i < 3; ++i) {
            vm.prank(info.committee[i]);
            market.voteOnOutcome(id, choice);
        }
    }

    function _state(uint256 id, PredictionMarket.MarketState expected) internal view {
        require(market.getMarket(id).state == expected, "state mismatch");
    }

    function _accounting() internal view {
        require(
            token.balanceOf(address(market)) == market.totalCollateral() + market.totalChallengeBonds(),
            "global funds mismatch"
        );
        uint256 total = 0;
        for (uint256 i; i < market.marketCount(); ++i) {
            PredictionMarket.Market memory data = market.getMarket(i);
            total += data.collateralBalance;
            require(data.collateralBalance >= market.remainingLiability(i), "market liability not reserved");
        }
        require(total == market.totalCollateral(), "per-market collateral mismatch");
    }
}
