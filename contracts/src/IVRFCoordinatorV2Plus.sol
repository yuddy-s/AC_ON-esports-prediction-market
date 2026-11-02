// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice Minimal request ABI matching @chainlink/contracts 1.4.0 VRF v2.5.
/// @dev Field order/types and the ExtraArgsV1 tag match VRFV2PlusClient. Subscription
/// administration remains in the coordinator/Safe; this interface does not reimplement it.
interface IVRFCoordinatorV2Plus {
    struct RandomWordsRequest {
        bytes32 keyHash;
        uint256 subId;
        uint16 requestConfirmations;
        uint32 callbackGasLimit;
        uint32 numWords;
        bytes extraArgs;
    }

    function requestRandomWords(RandomWordsRequest calldata request) external returns (uint256 requestId);
}
