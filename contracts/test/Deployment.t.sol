// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {MarketTestBase, VRFCoordinatorMock, PredictionMarket, ResolverRegistry} from "./MarketTestBase.sol";
import {SafeSetupPlan, VerifyAdministration} from "../script/Deploy.s.sol";

/// @dev Execution/ABI mock only; this is not a Safe implementation or signature test.
contract SafeExecutionMock {
    function getThreshold() external pure returns (uint256) {
        return 2;
    }

    function getOwners() external pure returns (address[] memory owners) {
        owners = new address[](3);
        owners[0] = address(0x101);
        owners[1] = address(0x102);
        owners[2] = address(0x103);
    }

    function execute(SafeSetupPlan.SafeCall[] calldata calls) external {
        for (uint256 i; i < calls.length; ++i) {
            require(calls[i].value == 0, "unexpected value");
            (bool success,) = calls[i].to.call(calls[i].data);
            require(success, "Safe payload failed");
        }
    }
}

contract SubscriptionMock is VRFCoordinatorMock {
    address public owner;
    address[] private consumers;

    constructor(address safe) {
        owner = safe;
    }

    function getSubscription(uint256 id) external view returns (uint96, uint96, uint64, address, address[] memory) {
        require(id == 1, "unknown subscription");
        return (1e18, 0, 0, owner, consumers);
    }

    function addConsumer(uint256 id, address consumer) external {
        require(msg.sender == owner && id == 1, "subscription owner required");
        consumers.push(consumer);
    }
}

contract DeploymentTest is MarketTestBase {
    SafeExecutionMock private safe;
    SafeSetupPlan private planner;
    VerifyAdministration private verifier;

    function setUp() public override {
        super.setUp();
        safe = new SafeExecutionMock();
        vrf = new SubscriptionMock(address(safe));
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
        planner = new SafeSetupPlan();
        verifier = new VerifyAdministration();
        market.transferAdministration(address(safe));
        registry.transferAdministration(address(safe));
    }

    function testSafeBatchHandsOffBothContractsGrantsNarrowRolesAndAddsConsumer() public {
        SafeSetupPlan.SafeCall[] memory calls = planner.calls(market, REGISTRAR, PROPOSER, _pool());
        require(calls.length == 15, "incomplete setup plan");
        safe.execute(calls);
        require(verifier.verify(market, address(safe), address(this), REGISTRAR, PROPOSER), "handoff incomplete");
        require(
            !market.hasRole(bytes32(0), address(this)) && !registry.hasRole(bytes32(0), address(this)),
            "old admin retained"
        );
        require(!market.hasRole(market.PROPOSER_ROLE(), REGISTRAR), "registrar got proposer role");
        require(!market.hasRole(market.REGISTRAR_ROLE(), PROPOSER), "proposer got registrar role");
    }

    function testVerifierRejectsPendingHandoff() public {
        vm.expectRevert(bytes("Safe does not own both contracts"));
        verifier.verify(market, address(safe), address(this), REGISTRAR, PROPOSER);
    }

    function testPlanRejectsOverlappingRolesDuplicatesAndUndersizedPool() public {
        address[] memory pool = _pool();
        vm.expectRevert(bytes("operational roles must be separate"));
        planner.calls(market, address(safe), PROPOSER, pool);
        vm.expectRevert(bytes("separate operational keys required"));
        planner.calls(market, REGISTRAR, REGISTRAR, pool);
        pool[9] = pool[0];
        vm.expectRevert(bytes("duplicate resolver"));
        planner.calls(market, REGISTRAR, PROPOSER, pool);
        pool[9] = PROPOSER;
        vm.expectRevert(bytes("conflicted resolver-only address"));
        planner.calls(market, REGISTRAR, PROPOSER, pool);
        vm.expectRevert(bytes("at least ten resolver-only addresses required"));
        planner.calls(market, REGISTRAR, PROPOSER, new address[](9));
    }

    function testVerifierRejectsOperationalAddressInResolverPool() public {
        safe.execute(planner.calls(market, REGISTRAR, PROPOSER, _pool()));
        vm.prank(address(safe));
        registry.setResolverStatus(REGISTRAR, true);
        vm.expectRevert(bytes("conflicted resolver-only address"));
        verifier.verify(market, address(safe), address(this), REGISTRAR, PROPOSER);
    }

    function testPlanRequiresMatchingPendingAdministrators() public {
        registry.transferAdministration(OTHER);
        vm.expectRevert(bytes("Safe handoff not pending"));
        planner.calls(market, REGISTRAR, PROPOSER, _pool());
    }

    function _pool() private pure returns (address[] memory pool) {
        pool = new address[](10);
        for (uint256 i; i < 10; ++i) {
            pool[i] = _resolver(i);
        }
    }
}
