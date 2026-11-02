// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketAccess} from "./MarketAccess.sol";

/// @notice Administrator-managed allowlist. Markets snapshot it, so edits do not rewrite a round.
contract ResolverRegistry is MarketAccess {
    mapping(address resolver => bool active) public isActiveResolver;
    mapping(address resolver => bool known) private known;
    address[] private resolverAddresses;

    event ResolverStatusChanged(address indexed resolver, bool active, address indexed administrator);

    constructor(address initialAdmin) MarketAccess(initialAdmin) {}

    function setResolverStatus(address resolver, bool active) external onlyAdmin {
        if (resolver == address(0)) revert ZeroAddress();
        if (!known[resolver]) {
            known[resolver] = true;
            resolverAddresses.push(resolver);
        }
        isActiveResolver[resolver] = active;
        emit ResolverStatusChanged(resolver, active, msg.sender);
    }

    function getResolvers() external view returns (address[] memory) {
        return resolverAddresses;
    }

    function getActiveResolvers() external view returns (address[] memory active) {
        uint256 length = resolverAddresses.length;
        uint256 count = 0;
        for (uint256 i; i < length; ++i) {
            if (isActiveResolver[resolverAddresses[i]]) ++count;
        }
        active = new address[](count);
        uint256 index = 0;
        for (uint256 i; i < length; ++i) {
            address account = resolverAddresses[i];
            if (isActiveResolver[account]) active[index++] = account;
        }
    }
}
