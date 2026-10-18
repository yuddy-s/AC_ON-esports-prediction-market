// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {PredictionMarket} from "../src/PredictionMarket.sol";

interface Vm {
    function warp(uint256 timestamp) external;
    function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData, address emitter) external;
    function expectRevert(bytes calldata revertData) external;
}

contract PredictionMarketTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    PredictionMarket private market;

    function setUp() public {
        market = new PredictionMarket();
    }

    function testCreateMarketStoresFrontendFieldsAndIncrementsCount() public {
        string memory question = "Will Team A beat Team B?";
        uint256 deadline = block.timestamp + 1 days;

        uint256 marketId = market.createMarket(question, deadline);
        (string memory storedQuestion, uint256 storedDeadline, PredictionMarket.MarketState state, address creator) =
            market.getMarket(marketId);

        require(marketId == 0, "first market id should be zero");
        require(market.marketCount() == 1, "market count should increment");
        require(keccak256(bytes(storedQuestion)) == keccak256(bytes(question)), "question mismatch");
        require(storedDeadline == deadline, "deadline mismatch");
        require(state == PredictionMarket.MarketState.CREATED, "new market should be CREATED");
        require(creator == address(this), "creator mismatch");
    }

    function testCreateMarketEmitsEvent() public {
        string memory question = "Will Team A beat Team B?";
        uint256 deadline = block.timestamp + 1 days;

        vm.expectEmit(true, true, false, true, address(market));
        emit PredictionMarket.MarketCreated(0, address(this), question, deadline);

        market.createMarket(question, deadline);
    }

    function testCreateMarketRejectsEmptyQuestion() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.EmptyQuestion.selector));
        market.createMarket("", block.timestamp + 1 days);
    }

    function testCreateMarketRejectsDeadlineInPastOrPresent() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidTradingDeadline.selector));
        market.createMarket("Will Team A beat Team B?", block.timestamp);
    }

    function testGetMarketRejectsUnknownId() public {
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.MarketNotFound.selector, 0));
        market.getMarket(0);
    }

    function testTradingDeadlineValidationUsesCurrentBlockTime() public {
        vm.warp(1_800_000_000);
        vm.expectRevert(abi.encodeWithSelector(PredictionMarket.InvalidTradingDeadline.selector));
        market.createMarket("Will Team A beat Team B?", 1_799_999_999);
    }
}
