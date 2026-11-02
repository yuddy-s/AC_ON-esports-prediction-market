// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @notice Small, single-administrator role boundary with an explicit two-step Safe handoff.
abstract contract MarketAccess {
    bytes32 public constant DEFAULT_ADMIN_ROLE = bytes32(0);
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
    bytes32 public constant PROPOSER_ROLE = keccak256("PROPOSER_ROLE");

    address public admin;
    address public pendingAdmin;
    mapping(bytes32 role => mapping(address account => bool granted)) private roles;

    error ZeroAddress();
    error Unauthorized(bytes32 role, address account);
    error UseAdministrationTransfer();

    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);
    event AdministrationTransferStarted(address indexed previousAdmin, address indexed newAdmin);
    event AdministrationTransferred(address indexed previousAdmin, address indexed newAdmin);

    constructor(address initialAdmin) {
        if (initialAdmin == address(0)) revert ZeroAddress();
        admin = initialAdmin;
        emit RoleGranted(DEFAULT_ADMIN_ROLE, initialAdmin, msg.sender);
    }

    modifier onlyAdmin() {
        if (msg.sender != admin) revert Unauthorized(DEFAULT_ADMIN_ROLE, msg.sender);
        _;
    }

    modifier onlyRole(bytes32 role) {
        if (!hasRole(role, msg.sender)) revert Unauthorized(role, msg.sender);
        _;
    }

    function hasRole(bytes32 role, address account) public view returns (bool) {
        return role == DEFAULT_ADMIN_ROLE ? account == admin : roles[role][account];
    }

    function grantRole(bytes32 role, address account) external onlyAdmin {
        if (role == DEFAULT_ADMIN_ROLE) revert UseAdministrationTransfer();
        if (account == address(0)) revert ZeroAddress();
        if (!roles[role][account]) {
            roles[role][account] = true;
            emit RoleGranted(role, account, msg.sender);
        }
    }

    function revokeRole(bytes32 role, address account) external onlyAdmin {
        if (role == DEFAULT_ADMIN_ROLE) revert UseAdministrationTransfer();
        _revoke(role, account);
    }

    function renounceRole(bytes32 role) external {
        if (role == DEFAULT_ADMIN_ROLE) revert UseAdministrationTransfer();
        _revoke(role, msg.sender);
    }

    function transferAdministration(address newAdmin) external onlyAdmin {
        if (newAdmin == address(0)) revert ZeroAddress();
        pendingAdmin = newAdmin;
        emit AdministrationTransferStarted(admin, newAdmin);
    }

    /// @notice Called by the Safe itself. The old administrator loses power atomically.
    function acceptAdministration() external {
        if (msg.sender != pendingAdmin || pendingAdmin == address(0)) {
            revert Unauthorized(DEFAULT_ADMIN_ROLE, msg.sender);
        }
        address previous = admin;
        admin = msg.sender;
        pendingAdmin = address(0);
        emit RoleRevoked(DEFAULT_ADMIN_ROLE, previous, msg.sender);
        emit RoleGranted(DEFAULT_ADMIN_ROLE, msg.sender, msg.sender);
        emit AdministrationTransferred(previous, msg.sender);
    }

    function _revoke(bytes32 role, address account) private {
        if (roles[role][account]) {
            roles[role][account] = false;
            emit RoleRevoked(role, account, msg.sender);
        }
    }
}
