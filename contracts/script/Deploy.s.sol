// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {PredictionMarket} from "../src/PredictionMarket.sol";

interface VmDeploy {
    function envUint(string calldata key) external returns (uint256 value);
    function startBroadcast(uint256 privateKey) external;
    function stopBroadcast() external;
}

contract DeployPredictionMarket {
    VmDeploy private constant vm = VmDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (PredictionMarket market) {
        uint256 deployerKey = vm.envUint("SEPOLIA_PRIVATE_KEY");

        vm.startBroadcast(deployerKey);
        market = new PredictionMarket();
        market.createMarket("Will Team A beat Team B?", block.timestamp + 7 days);
        vm.stopBroadcast();
    }
}
