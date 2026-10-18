// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title PredictionMarket
/// @notice Milestone 2 market registry; this prototype does not accept funds or bets.
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

    struct Market {
        string question;
        uint256 tradingDeadline;
        MarketState state;
        address creator;
    }

    uint256 public marketCount;
    mapping(uint256 marketId => Market market) private markets;

    event MarketCreated(uint256 indexed marketId, address indexed creator, string question, uint256 tradingDeadline);

    error EmptyQuestion();
    error InvalidTradingDeadline();
    error MarketNotFound(uint256 marketId);

    /// @notice Creates a demo market. Anyone may create markets on this testnet prototype.
    /// @dev No collateral is collected and no trading functionality is implemented.
    function createMarket(string calldata question, uint256 tradingDeadline) external returns (uint256 marketId) {
        if (bytes(question).length == 0) revert EmptyQuestion();
        if (tradingDeadline <= block.timestamp) revert InvalidTradingDeadline();

        marketId = marketCount;
        markets[marketId] = Market({
            question: question, tradingDeadline: tradingDeadline, state: MarketState.CREATED, creator: msg.sender
        });
        marketCount = marketId + 1;

        emit MarketCreated(marketId, msg.sender, question, tradingDeadline);
    }

    /// @notice Reads the fields currently displayed by the Milestone 2 frontend.
    function getMarket(uint256 marketId)
        external
        view
        returns (string memory question, uint256 tradingDeadline, MarketState state, address creator)
    {
        if (marketId >= marketCount) revert MarketNotFound(marketId);

        Market storage market = markets[marketId];
        return (market.question, market.tradingDeadline, market.state, market.creator);
    }
}
