// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20Minimal} from "./IERC20Minimal.sol";

/// @title ACONTestToken
/// @notice Test-only 18-decimal collateral token for Milestone 3 on Sepolia.
/// @dev ACON has no real monetary value, transfer fees, or rebasing behavior.
contract ACONTestToken is IERC20Minimal {
    string public constant name = "ACON Test Token";
    string public constant symbol = "ACON";
    uint8 public constant decimals = 18;
    uint256 public constant FAUCET_AMOUNT = 1_000e18;

    uint256 public totalSupply;
    mapping(address account => uint256 amount) public override balanceOf;
    mapping(address owner => mapping(address spender => uint256 amount)) public override allowance;
    mapping(address account => bool claimed) public hasClaimedFaucet;

    event Transfer(address indexed from, address indexed to, uint256 amount);
    event Approval(address indexed owner, address indexed spender, uint256 amount);
    event FaucetClaimed(address indexed account, uint256 amount);

    error ZeroAddress();
    error InsufficientBalance(address account, uint256 available, uint256 required);
    error InsufficientAllowance(address spender, uint256 available, uint256 required);
    error FaucetAlreadyClaimed();

    /// @notice Gives each address a one-time faucet allocation for testnet use.
    function faucet() external returns (uint256 amount) {
        if (hasClaimedFaucet[msg.sender]) revert FaucetAlreadyClaimed();

        hasClaimedFaucet[msg.sender] = true;
        amount = FAUCET_AMOUNT;
        totalSupply += amount;
        balanceOf[msg.sender] += amount;

        emit Transfer(address(0), msg.sender, amount);
        emit FaucetClaimed(msg.sender, amount);
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        if (spender == address(0)) revert ZeroAddress();

        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        uint256 availableAllowance = allowance[from][msg.sender];
        if (availableAllowance < amount) {
            revert InsufficientAllowance(msg.sender, availableAllowance, amount);
        }

        if (availableAllowance != type(uint256).max) {
            allowance[from][msg.sender] = availableAllowance - amount;
            emit Approval(from, msg.sender, availableAllowance - amount);
        }

        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) private {
        if (from == address(0) || to == address(0)) revert ZeroAddress();

        uint256 availableBalance = balanceOf[from];
        if (availableBalance < amount) revert InsufficientBalance(from, availableBalance, amount);

        balanceOf[from] = availableBalance - amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
