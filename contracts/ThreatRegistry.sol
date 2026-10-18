// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ThreatRegistry
 * @notice ChainShield immutable threat-fingerprint registry.
 *
 * @dev The blockchain acts ONLY as a tamper-evident lookup of known threat
 *      hashes. Every entry is a Keccak-256 digest (`bytes32`) produced
 *      off-chain by the deterministic canonicalization + hashing pipeline:
 *
 *          raw input → canonicalize → domain-prefix → UTF-8 → keccak256
 *
 *      The contract NEVER receives, stores, or processes raw messages,
 *      URLs, NLP tokens, or PII.
 *
 *      This contract does NOT implement:
 *        - reputation / voting / dispute / community confirmation
 *        - ML inference or semantic analysis
 *        - user identity or profile management
 *
 * @dev Access-control decision: Submission is restricted to the contract
 *      owner. This prevents spam-flooding the registry with arbitrary
 *      hashes. The owner is the deployer address and can be transferred
 *      via `transferOwnership`. There is no multi-sig, governance, or
 *      role hierarchy — intentionally minimal for an academic project
 *      deployed on Sepolia.
 */
contract ThreatRegistry {

    // ──────────────────────────────────────────────────────────────
    //  Enums
    // ──────────────────────────────────────────────────────────────

    /// @notice Classification of the threat source.
    enum ThreatType {
        MESSAGE,    // 0 – canonicalized message fingerprint
        URL         // 1 – canonicalized URL fingerprint
    }

    // ──────────────────────────────────────────────────────────────
    //  Structs
    // ──────────────────────────────────────────────────────────────

    /// @notice Minimal metadata stored alongside each threat hash.
    /// @dev    No raw text, URL, or PII is stored — only the hash key
    ///         identifies the threat.
    struct Threat {
        ThreatType  threatType;   // MESSAGE or URL
        uint8       verdict;      // 0 = benign, 1 = threat  (binary)
        uint16      confidence;   // 0–100 inclusive (percentage)
        uint64      submittedAt;  // block.timestamp cast to uint64
        address     submitter;    // msg.sender at submission time
    }

    // ──────────────────────────────────────────────────────────────
    //  State
    // ──────────────────────────────────────────────────────────────

    /// @dev Owner address — only this address may submit threats.
    address private _owner;

    /// @dev Primary storage: threatHash → Threat metadata.
    mapping(bytes32 => Threat) private _threats;

    /// @dev Existence bitmap. Separating existence from the struct avoids
    ///      the need to rely on a default-value sentinel in Threat.
    mapping(bytes32 => bool) private _exists;

    /// @notice Running count of registered threats (informational).
    uint256 public threatCount;

    // ──────────────────────────────────────────────────────────────
    //  Events
    // ──────────────────────────────────────────────────────────────

    /// @notice Emitted when a new threat hash is registered.
    event ThreatSubmitted(
        bytes32   indexed threatHash,
        ThreatType        threatType,
        uint8             verdict,
        uint16            confidence,
        uint64            submittedAt,
        address   indexed submitter
    );

    /// @notice Emitted when contract ownership is transferred.
    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    // ──────────────────────────────────────────────────────────────
    //  Errors
    // ──────────────────────────────────────────────────────────────

    /// @notice Caller is not the contract owner.
    error NotOwner();

    /// @notice Attempted to submit `bytes32(0)` as a threat hash.
    error ZeroHash();

    /// @notice The threat hash has already been registered.
    error DuplicateHash(bytes32 threatHash);

    /// @notice Confidence value exceeds the maximum of 100.
    error ConfidenceOutOfRange(uint16 confidence);

    /// @notice Verdict value is not 0 or 1.
    error InvalidVerdict(uint8 verdict);

    /// @notice The requested threat hash does not exist in the registry.
    error ThreatNotFound(bytes32 threatHash);

    /// @notice New owner address is the zero address.
    error ZeroAddress();

    // ──────────────────────────────────────────────────────────────
    //  Modifiers
    // ──────────────────────────────────────────────────────────────

    /// @dev Restricts function access to the contract owner.
    modifier onlyOwner() {
        if (msg.sender != _owner) revert NotOwner();
        _;
    }

    // ──────────────────────────────────────────────────────────────
    //  Constructor
    // ──────────────────────────────────────────────────────────────

    /// @notice Deploys the registry and sets the deployer as owner.
    constructor() {
        _owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    // ──────────────────────────────────────────────────────────────
    //  Write Functions
    // ──────────────────────────────────────────────────────────────

    /**
     * @notice Register a new threat fingerprint.
     *
     * @param threatHash   The Keccak-256 `bytes32` digest produced off-chain.
     * @param threatType   MESSAGE (0) or URL (1).
     * @param verdict      0 = benign, 1 = threat.
     * @param confidence   Percentage confidence, 0–100 inclusive.
     *
     * @dev Reverts if:
     *      - caller is not the owner (`NotOwner`)
     *      - `threatHash` is `bytes32(0)` (`ZeroHash`)
     *      - `threatHash` already exists (`DuplicateHash`)
     *      - `confidence > 100` (`ConfidenceOutOfRange`)
     *      - `verdict > 1` (`InvalidVerdict`)
     */
    function submitThreat(
        bytes32    threatHash,
        ThreatType threatType,
        uint8      verdict,
        uint16     confidence
    )
        external
        onlyOwner
    {
        // --- Validation ------------------------------------------------
        if (threatHash == bytes32(0))  revert ZeroHash();
        if (_exists[threatHash])       revert DuplicateHash(threatHash);
        if (verdict > 1)               revert InvalidVerdict(verdict);
        if (confidence > 100)          revert ConfidenceOutOfRange(confidence);

        // --- Storage ---------------------------------------------------
        uint64 ts = uint64(block.timestamp);

        _threats[threatHash] = Threat({
            threatType:  threatType,
            verdict:     verdict,
            confidence:  confidence,
            submittedAt: ts,
            submitter:   msg.sender
        });
        _exists[threatHash] = true;

        unchecked { threatCount++; }

        // --- Event -----------------------------------------------------
        emit ThreatSubmitted(
            threatHash,
            threatType,
            verdict,
            confidence,
            ts,
            msg.sender
        );
    }

    /**
     * @notice Transfer ownership to a new address.
     * @param newOwner The address to transfer ownership to.
     *
     * @dev Reverts if:
     *      - caller is not the current owner (`NotOwner`)
     *      - `newOwner` is the zero address (`ZeroAddress`)
     */
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(_owner, newOwner);
        _owner = newOwner;
    }

    // ──────────────────────────────────────────────────────────────
    //  Read Functions
    // ──────────────────────────────────────────────────────────────

    /**
     * @notice Check whether a threat hash has been registered.
     * @param threatHash The `bytes32` digest to look up.
     * @return exists `true` if the hash is in the registry, `false` otherwise.
     */
    function threatExists(bytes32 threatHash) external view returns (bool exists) {
        return _exists[threatHash];
    }

    /**
     * @notice Retrieve the full metadata for a registered threat.
     * @param threatHash The `bytes32` digest to retrieve.
     * @return threatType  MESSAGE or URL.
     * @return verdict     0 = benign, 1 = threat.
     * @return confidence  0–100.
     * @return submittedAt UNIX timestamp of submission.
     * @return submitter   Address that submitted the threat.
     *
     * @dev Reverts with `ThreatNotFound` if the hash has not been registered.
     */
    function getThreat(bytes32 threatHash)
        external
        view
        returns (
            ThreatType threatType,
            uint8      verdict,
            uint16     confidence,
            uint64     submittedAt,
            address    submitter
        )
    {
        if (!_exists[threatHash]) revert ThreatNotFound(threatHash);

        Threat storage t = _threats[threatHash];
        return (t.threatType, t.verdict, t.confidence, t.submittedAt, t.submitter);
    }

    /**
     * @notice Returns the current owner of the contract.
     * @return The owner address.
     */
    function owner() external view returns (address) {
        return _owner;
    }
}
