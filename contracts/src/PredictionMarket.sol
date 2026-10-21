// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20Minimal} from "./IERC20Minimal.sol";
import {LMSR} from "./LMSR.sol";

/// @title PredictionMarket
/// @notice Ethereum Sepolia binary LMSR market with creator-funded liquidity and guarded buys.
contract PredictionMarket {
    enum MarketState {
        CREATED,
        OPEN,
        CLOSED,
        PROPOSED,
        DISPUTED,
        FINALIZED,
        VOID
    }

    enum Outcome {
        YES,
        NO
    }

    struct Market {
        string question;
        uint256 tradingDeadline;
        MarketState state;
        address creator;
        uint256 yesQuantity;
        uint256 noQuantity;
        uint256 collateralBalance;
    }

    uint256 public constant REQUIRED_SUBSIDY = 34_657_359_027_997_265_471;

    IERC20Minimal public immutable paymentToken;
    uint256 public marketCount;

    mapping(uint256 marketId => Market market) private markets;
    mapping(uint256 marketId => mapping(address account => mapping(Outcome outcome => uint256 shares))) private
        positions;

    uint256 private reentrancyStatus = 1;

    event MarketCreated(uint256 indexed marketId, address indexed creator, string question, uint256 tradingDeadline);
    event TradeExecuted(
        uint256 indexed marketId,
        address indexed trader,
        uint8 indexed outcome,
        uint256 shares,
        uint256 cost,
        uint256 yesQuantity,
        uint256 noQuantity
    );

    error InvalidPaymentToken();
    error EmptyQuestion();
    error InvalidTradingDeadline();
    error MarketNotFound(uint256 marketId);
    error MarketNotOpen();
    error TradingClosed();
    error SlippageExceeded(uint256 actualCost, uint256 maxCost);
    error InsufficientTokenBalance(uint256 required, uint256 available);
    error InsufficientTokenAllowance(uint256 required, uint256 available);
    error PaymentTransferFailed();
    error ReentrantCall();

    modifier nonReentrant() {
        if (reentrancyStatus != 1) revert ReentrantCall();
        reentrancyStatus = 2;
        _;
        reentrancyStatus = 1;
    }

    constructor(address paymentTokenAddress) {
        if (paymentTokenAddress == address(0)) revert InvalidPaymentToken();
        paymentToken = IERC20Minimal(paymentTokenAddress);
    }

    /// @notice Creates an open market and atomically collects the required LMSR subsidy.
    function createMarket(string calldata question, uint256 tradingDeadline)
        external
        nonReentrant
        returns (uint256 marketId)
    {
        if (bytes(question).length == 0) revert EmptyQuestion();
        // Block time is the approved source for market trading deadlines.
        // forge-lint: disable-next-line(block-timestamp)
        if (tradingDeadline <= block.timestamp) revert InvalidTradingDeadline();

        uint256 subsidy = LMSR.requiredSubsidy();
        _collectPayment(msg.sender, subsidy);

        marketId = marketCount;
        markets[marketId] = Market({
            question: question,
            tradingDeadline: tradingDeadline,
            state: MarketState.OPEN,
            creator: msg.sender,
            yesQuantity: 0,
            noQuantity: 0,
            collateralBalance: subsidy
        });
        marketCount = marketId + 1;

        // The nonReentrant guard protects this post-transfer event from callback reordering.
        // forge-lint: disable-next-line(reentrancy-events)
        emit MarketCreated(marketId, msg.sender, question, tradingDeadline);
    }

    /// @notice Quotes the current LMSR cost for buying YES or NO shares.
    function quoteBuy(uint256 marketId, Outcome outcome, uint256 shares) external view returns (uint256 cost) {
        Market storage market = _requireTradableMarket(marketId);
        return _buyCost(market, outcome, shares);
    }

    /// @notice Buys YES or NO shares only if their current cost is within maxCost.
    function buy(uint256 marketId, Outcome outcome, uint256 shares, uint256 maxCost)
        external
        nonReentrant
        returns (uint256 cost)
    {
        Market storage market = _requireTradableMarket(marketId);
        cost = _buyCost(market, outcome, shares);
        if (cost > maxCost) revert SlippageExceeded(cost, maxCost);

        _collectPayment(msg.sender, cost);
        positions[marketId][msg.sender][outcome] += shares;

        if (outcome == Outcome.YES) {
            market.yesQuantity += shares;
        } else {
            market.noQuantity += shares;
        }
        market.collateralBalance += cost;

        // The nonReentrant guard protects this post-transfer event from callback reordering.
        // forge-lint: disable-next-line(reentrancy-events)
        emit TradeExecuted(marketId, msg.sender, uint8(outcome), shares, cost, market.yesQuantity, market.noQuantity);
    }

    /// @notice Returns an account's outstanding YES or NO position in a market.
    function balanceOf(uint256 marketId, address account, Outcome outcome) external view returns (uint256 shares) {
        if (marketId >= marketCount) revert MarketNotFound(marketId);
        return positions[marketId][account][outcome];
    }

    /// @notice Reads market details and the LMSR quantities needed by clients and the indexer.
    function getMarket(uint256 marketId)
        external
        view
        returns (
            string memory question,
            uint256 tradingDeadline,
            MarketState state,
            address creator,
            uint256 yesQuantity,
            uint256 noQuantity
        )
    {
        if (marketId >= marketCount) revert MarketNotFound(marketId);

        Market storage market = markets[marketId];
        return
            (
                market.question,
                market.tradingDeadline,
                market.state,
                market.creator,
                market.yesQuantity,
                market.noQuantity
            );
    }

    function _buyCost(Market storage market, Outcome outcome, uint256 shares) private view returns (uint256) {
        return LMSR.buyCost(market.yesQuantity, market.noQuantity, outcome == Outcome.YES, shares);
    }

    function _requireTradableMarket(uint256 marketId) private view returns (Market storage market) {
        if (marketId >= marketCount) revert MarketNotFound(marketId);

        market = markets[marketId];
        if (market.state != MarketState.OPEN) revert MarketNotOpen();
        // Block time is the approved source for market trading deadlines.
        // forge-lint: disable-next-line(block-timestamp)
        if (block.timestamp >= market.tradingDeadline) revert TradingClosed();
    }

    function _collectPayment(address payer, uint256 amount) private {
        uint256 availableBalance = paymentToken.balanceOf(payer);
        if (availableBalance < amount) revert InsufficientTokenBalance(amount, availableBalance);

        uint256 availableAllowance = paymentToken.allowance(payer, address(this));
        if (availableAllowance < amount) revert InsufficientTokenAllowance(amount, availableAllowance);

        // ACON is an immutable fee-free token; public mutators hold the reentrancy guard.
        // forge-lint: disable-next-line(reentrancy-no-eth)
        if (!paymentToken.transferFrom(payer, address(this), amount)) revert PaymentTransferFailed();
    }
}
