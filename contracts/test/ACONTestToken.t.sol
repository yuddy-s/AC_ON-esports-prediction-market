// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ACONTestToken} from "../src/ACONTestToken.sol";

interface VmAconTest {
    function prank(address caller) external;
    function expectRevert(bytes calldata revertData) external;
}

contract ACONTestTokenTest {
    VmAconTest private constant vm = VmAconTest(address(uint160(uint256(keccak256("hevm cheat code")))));

    ACONTestToken private token;

    function setUp() public {
        token = new ACONTestToken();
    }

    function testFaucetMintsOneThousandAconOnce() public {
        uint256 minted = token.faucet();

        require(minted == 1_000e18, "faucet amount mismatch");
        require(token.balanceOf(address(this)) == 1_000e18, "wallet balance mismatch");
        require(token.totalSupply() == 1_000e18, "total supply mismatch");
        require(token.decimals() == 18, "ACON must use 18 decimals");

        vm.expectRevert(abi.encodeWithSelector(ACONTestToken.FaucetAlreadyClaimed.selector));
        token.faucet();
    }

    function testFaucetMintsToCaller() public {
        address tester = address(0xCAFE);
        vm.prank(tester);
        token.faucet();

        require(token.balanceOf(tester) == 1_000e18, "faucet should mint to caller");
    }

    function testApproveAndTransferFromRespectAllowanceAndBalances() public {
        token.faucet();
        address spender = address(0xBEEF);
        address recipient = address(0xCAFE);
        token.approve(spender, 25e18);

        vm.prank(spender);
        token.transferFrom(address(this), recipient, 10e18);

        require(token.balanceOf(address(this)) == 990e18, "sender balance mismatch");
        require(token.balanceOf(recipient) == 10e18, "recipient balance mismatch");
        require(token.allowance(address(this), spender) == 15e18, "remaining allowance mismatch");
    }

    function testTransferFromRejectsInsufficientAllowance() public {
        token.faucet();
        address spender = address(0xBEEF);

        vm.prank(spender);
        vm.expectRevert(abi.encodeWithSelector(ACONTestToken.InsufficientAllowance.selector, spender, 0, 1));
        token.transferFrom(address(this), spender, 1);
    }
}
