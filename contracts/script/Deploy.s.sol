// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {ACONTestToken} from "../src/ACONTestToken.sol";
import {MarketPricing} from "../src/MarketPricing.sol";
import {MarketAccess} from "../src/MarketAccess.sol";
import {ResolverRegistry} from "../src/ResolverRegistry.sol";
import {PredictionMarket} from "../src/PredictionMarket.sol";

interface VmDeploy {
    function envUint(string calldata) external returns (uint256);
    function envAddress(string calldata) external returns (address);
    function envBytes32(string calldata) external returns (bytes32);
    function addr(uint256) external returns (address);
    function startBroadcast(uint256) external;
    function stopBroadcast() external;
}

interface ISafe {
    function getThreshold() external view returns (uint256);
    function getOwners() external view returns (address[] memory);
}

interface IVRFSubscription {
    function getSubscription(uint256 subId)
        external
        view
        returns (uint96 balance, uint96 nativeBalance, uint64 requestCount, address owner, address[] memory consumers);
    function addConsumer(uint256 subId, address consumer) external;
}

/// @notice Creates fresh contracts and proposes their Safe administration handoff.
/// @dev No fictitious live fixture or resolver identity is inserted. The Safe must execute
/// the setup calls below before the deployment is reported as release-ready.
contract DeployPredictionMarket {
    VmDeploy private constant vm = VmDeploy(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run()
        external
        returns (ACONTestToken token, MarketPricing pricing, ResolverRegistry registry, PredictionMarket market)
    {
        require(block.chainid == 11155111, "deployment targets Ethereum Sepolia");
        address safe = vm.envAddress("SAFE_ADDRESS");
        address coordinator = vm.envAddress("VRF_COORDINATOR");
        uint256 subscription = vm.envUint("VRF_SUBSCRIPTION_ID");
        uint256 callbackGas = vm.envUint("VRF_CALLBACK_GAS_LIMIT");
        require(callbackGas > 0 && callbackGas <= type(uint32).max, "invalid callback gas limit");
        _verifySafe(safe);
        (uint96 linkBalance,,, address owner,) = IVRFSubscription(coordinator).getSubscription(subscription);
        require(owner == safe && linkBalance > 0, "Safe must own a funded test-LINK subscription");
        uint256 key = vm.envUint("SEPOLIA_PRIVATE_KEY");
        address deployer = vm.addr(key);
        bytes32 keyHash = vm.envBytes32("VRF_KEY_HASH");
        vm.startBroadcast(key);
        token = new ACONTestToken();
        pricing = new MarketPricing();
        registry = new ResolverRegistry(deployer);
        market = new PredictionMarket(
            PredictionMarket.DeploymentConfig({
                paymentToken: address(token),
                pricing: address(pricing),
                resolverRegistry: address(registry),
                coordinator: coordinator,
                initialAdmin: deployer,
                keyHash: keyHash,
                subscriptionId: subscription,
                callbackGasLimit: uint32(callbackGas)
            })
        );
        market.transferAdministration(safe);
        registry.transferAdministration(safe);
        vm.stopBroadcast();
    }

    function _verifySafe(address safe) private {
        require(safe.code.length > 0 && ISafe(safe).getThreshold() == 2, "expected a deployed 2-of-3 Safe");
        address[] memory owners = ISafe(safe).getOwners();
        require(owners.length == 3, "Safe must have exactly three owners");
        address[3] memory expected = [
            vm.envAddress("SAFE_OWNER_BENNY"), vm.envAddress("SAFE_OWNER_MATTHEW"), vm.envAddress("SAFE_OWNER_ADRIEL")
        ];
        for (uint256 i; i < 3; ++i) {
            require(expected[i] != address(0), "zero Safe owner");
            for (uint256 j; j < i; ++j) {
                require(expected[i] != expected[j], "duplicate Safe owner");
            }
            bool found;
            for (uint256 j; j < 3; ++j) {
                if (owners[j] == expected[i]) found = true;
            }
            require(found, "Safe owner differs from team handoff");
        }
    }
}

/// @notice Produces ordinary CALL payloads for a Safe batch; never signs or submits it.
contract SafeSetupPlan {
    struct SafeCall {
        address to;
        uint256 value;
        bytes data;
    }

    function calls(PredictionMarket market, address registrar, address proposer, address[] calldata resolverAddresses)
        external
        view
        returns (SafeCall[] memory result)
    {
        require(
            registrar != address(0) && proposer != address(0) && registrar != proposer,
            "separate operational keys required"
        );
        require(resolverAddresses.length >= 10, "at least ten resolver-only addresses required");
        ResolverRegistry registry = market.resolverRegistry();
        address safe = market.pendingAdmin();
        require(safe != address(0) && registry.pendingAdmin() == safe, "Safe handoff not pending");
        require(registrar != safe && proposer != safe, "operational roles must be separate");
        result = new SafeCall[](5 + resolverAddresses.length);
        result[0] = SafeCall(address(market), 0, abi.encodeCall(MarketAccess.acceptAdministration, ()));
        result[1] = SafeCall(address(registry), 0, abi.encodeCall(MarketAccess.acceptAdministration, ()));
        result[2] =
            SafeCall(address(market), 0, abi.encodeCall(MarketAccess.grantRole, (market.REGISTRAR_ROLE(), registrar)));
        result[3] =
            SafeCall(address(market), 0, abi.encodeCall(MarketAccess.grantRole, (market.PROPOSER_ROLE(), proposer)));
        result[4] = SafeCall(
            address(market.vrfCoordinator()),
            0,
            abi.encodeCall(IVRFSubscription.addConsumer, (market.vrfSubscriptionId(), address(market)))
        );
        for (uint256 i; i < resolverAddresses.length; ++i) {
            address resolver = resolverAddresses[i];
            require(
                resolver != address(0) && resolver != safe && resolver != registrar && resolver != proposer,
                "conflicted resolver-only address"
            );
            for (uint256 j; j < i; ++j) {
                require(resolver != resolverAddresses[j], "duplicate resolver");
            }
            result[5 + i] =
                SafeCall(address(registry), 0, abi.encodeCall(ResolverRegistry.setResolverStatus, (resolver, true)));
        }
    }
}

contract VerifyAdministration {
    function verify(PredictionMarket market, address safe, address formerDeployer, address registrar, address proposer)
        external
        view
        returns (bool)
    {
        require(safe != formerDeployer && safe.code.length > 0, "invalid Safe/deployer");
        require(ISafe(safe).getThreshold() == 2 && ISafe(safe).getOwners().length == 3, "expected 2-of-3 Safe");
        require(market.admin() == safe && market.resolverRegistry().admin() == safe, "Safe does not own both contracts");
        require(!market.hasRole(market.DEFAULT_ADMIN_ROLE(), formerDeployer), "deployer retained market admin");
        require(!market.resolverRegistry().hasRole(bytes32(0), formerDeployer), "deployer retained registry admin");
        require(
            market.hasRole(market.REGISTRAR_ROLE(), registrar) && market.hasRole(market.PROPOSER_ROLE(), proposer),
            "operational roles missing"
        );
        require(
            registrar != address(0) && proposer != address(0) && registrar != proposer && registrar != safe
                && proposer != safe,
            "operational roles must be separate"
        );
        (uint96 balance,,, address owner, address[] memory consumers) =
            IVRFSubscription(address(market.vrfCoordinator())).getSubscription(market.vrfSubscriptionId());
        require(owner == safe && balance > 0, "VRF ownership/funding incomplete");
        bool found;
        for (uint256 i; i < consumers.length; ++i) {
            if (consumers[i] == address(market)) found = true;
        }
        address[] memory active = market.resolverRegistry().getActiveResolvers();
        require(found && active.length >= 10, "consumer or resolver pool missing");
        for (uint256 i; i < active.length; ++i) {
            require(
                active[i] != safe && active[i] != registrar && active[i] != proposer, "conflicted resolver-only address"
            );
        }
        return true;
    }
}
