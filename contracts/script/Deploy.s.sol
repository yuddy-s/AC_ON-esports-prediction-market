// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {PredictionMarket} from "../src/PredictionMarket.sol";
import {ACONTestToken} from "../src/ACONTestToken.sol";

interface VmDeploy {
    function envUint(string calldata key) external returns (uint256 value);
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployPredictionMarket {
    VmDeploy private constant vm = VmDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (ACONTestToken token, PredictionMarket market) {
        uint256 deployerKey = vm.envUint("SEPOLIA_PRIVATE_KEY");

        vm.startBroadcast(deployerKey);
        token = new ACONTestToken();
        market = new PredictionMarket(address(token));
        token.faucet();
        token.approve(address(market), market.REQUIRED_SUBSIDY());
        market.createMarket("Will Team A beat Team B?", block.timestamp + 7 days);
        vm.stopBroadcast();
    }
}
