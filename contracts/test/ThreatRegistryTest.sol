// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ThreatRegistryTest
 * @notice Remix IDE compatible test suite for the ThreatRegistry contract.
 *
 * @dev How to run in Remix IDE:
 *      1. Open both ThreatRegistry.sol and this file in Remix.
 *      2. Compile both files (Solidity ^0.8.20).
 *      3. Under "Solidity Unit Testing" plugin, run this test file.
 *      4. All `check*` functions prefixed with `check` will be executed.
 *
 *      Alternatively, deploy ThreatRegistryTest and call test functions
 *      manually from the Deploy & Run panel.
 */

import "../ThreatRegistry.sol";

contract ThreatRegistryTest {

    // ── Deterministic test hashes (no real messages/URLs) ────────
    bytes32 constant HASH_1 = 0x1111111111111111111111111111111111111111111111111111111111111111;
    bytes32 constant HASH_2 = 0x2222222222222222222222222222222222222222222222222222222222222222;
    bytes32 constant HASH_3 = 0x3333333333333333333333333333333333333333333333333333333333333333;
    bytes32 constant ZERO_HASH = bytes32(0);

    ThreatRegistry private registry;

    // ── Events (redeclared for log matching) ─────────────────────
    event ThreatSubmitted(
        bytes32   indexed threatHash,
        ThreatRegistry.ThreatType threatType,
        uint8     verdict,
        uint16    confidence,
        uint64    submittedAt,
        address   indexed submitter
    );

    // ══════════════════════════════════════════════════════════════
    //  Setup — deploy a fresh registry for each test batch
    // ══════════════════════════════════════════════════════════════

    /// @dev Called before the test functions execute.
    function beforeAll() public {
        registry = new ThreatRegistry();
    }

    // ══════════════════════════════════════════════════════════════
    //  1. Deployment
    // ══════════════════════════════════════════════════════════════

    /// @notice Owner should be the deployer (this contract).
    function checkDeploymentOwner() public view {
        assert(registry.owner() == address(this));
    }

    /// @notice Initial threat count should be zero.
    function checkInitialThreatCount() public view {
        assert(registry.threatCount() == 0);
    }

    // ══════════════════════════════════════════════════════════════
    //  2. Unknown hash returns false
    // ══════════════════════════════════════════════════════════════

    /// @notice An unregistered hash must return false.
    function checkUnknownHashReturnsFalse() public view {
        assert(registry.threatExists(HASH_1) == false);
    }

    // ══════════════════════════════════════════════════════════════
    //  3. Valid submission succeeds
    // ══════════════════════════════════════════════════════════════

    /// @notice Submit a MESSAGE threat with verdict=1, confidence=95.
    function checkValidSubmission() public {
        registry.submitThreat(
            HASH_1,
            ThreatRegistry.ThreatType.MESSAGE,
            1,   // verdict = threat
            95   // confidence = 95%
        );
        assert(registry.threatExists(HASH_1) == true);
        assert(registry.threatCount() == 1);
    }

    // ══════════════════════════════════════════════════════════════
    //  4. Metadata retrieval
    // ══════════════════════════════════════════════════════════════

    /// @notice getThreat should return correct metadata for HASH_1.
    function checkMetadataRetrieval() public view {
        (
            ThreatRegistry.ThreatType threatType,
            uint8  verdict,
            uint16 confidence,
            uint64 submittedAt,
            address submitter
        ) = registry.getThreat(HASH_1);

        assert(threatType  == ThreatRegistry.ThreatType.MESSAGE);
        assert(verdict     == 1);
        assert(confidence  == 95);
        assert(submittedAt > 0);
        assert(submitter   == address(this));
    }

    // ══════════════════════════════════════════════════════════════
    //  5. Duplicate submission reverts
    // ══════════════════════════════════════════════════════════════

    /// @notice Submitting the same hash twice must revert.
    function checkDuplicateReverts() public {
        // HASH_1 was already submitted in checkValidSubmission
        try registry.submitThreat(
            HASH_1,
            ThreatRegistry.ThreatType.MESSAGE,
            1,
            90
        ) {
            // If it does not revert, fail the test
            assert(false);
        } catch {
            // Expected: DuplicateHash revert
            assert(true);
        }
    }

    // ══════════════════════════════════════════════════════════════
    //  6. Zero hash submission reverts
    // ══════════════════════════════════════════════════════════════

    /// @notice bytes32(0) must be rejected.
    function checkZeroHashReverts() public {
        try registry.submitThreat(
            ZERO_HASH,
            ThreatRegistry.ThreatType.URL,
            1,
            80
        ) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    // ══════════════════════════════════════════════════════════════
    //  7. Unknown hash metadata lookup reverts
    // ══════════════════════════════════════════════════════════════

    /// @notice getThreat for an unregistered hash must revert.
    function checkGetUnknownThreatReverts() public {
        try registry.getThreat(HASH_3) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    // ══════════════════════════════════════════════════════════════
    //  8. URL threat type submission
    // ══════════════════════════════════════════════════════════════

    /// @notice Submit a URL threat and verify metadata.
    function checkUrlThreatSubmission() public {
        registry.submitThreat(
            HASH_2,
            ThreatRegistry.ThreatType.URL,
            1,
            88
        );

        assert(registry.threatExists(HASH_2) == true);
        assert(registry.threatCount() == 2);

        (
            ThreatRegistry.ThreatType threatType,
            uint8  verdict,
            ,
            ,

        ) = registry.getThreat(HASH_2);

        assert(threatType == ThreatRegistry.ThreatType.URL);
        assert(verdict    == 1);
    }

    // ══════════════════════════════════════════════════════════════
    //  9. Confidence bounds enforcement
    // ══════════════════════════════════════════════════════════════

    /// @notice Confidence = 101 must revert (out of range).
    function checkConfidenceOverflowReverts() public {
        bytes32 freshHash = 0x4444444444444444444444444444444444444444444444444444444444444444;
        try registry.submitThreat(
            freshHash,
            ThreatRegistry.ThreatType.MESSAGE,
            1,
            101  // Out of range
        ) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    /// @notice Confidence = 0 should be accepted (lower bound).
    function checkConfidenceZeroAccepted() public {
        bytes32 freshHash = 0x5555555555555555555555555555555555555555555555555555555555555555;
        registry.submitThreat(
            freshHash,
            ThreatRegistry.ThreatType.MESSAGE,
            1,
            0
        );
        assert(registry.threatExists(freshHash) == true);
    }

    /// @notice Confidence = 100 should be accepted (upper bound).
    function checkConfidenceHundredAccepted() public {
        bytes32 freshHash = 0x6666666666666666666666666666666666666666666666666666666666666666;
        registry.submitThreat(
            freshHash,
            ThreatRegistry.ThreatType.URL,
            1,
            100
        );
        assert(registry.threatExists(freshHash) == true);
    }

    // ══════════════════════════════════════════════════════════════
    //  10. Invalid verdict reverts
    // ══════════════════════════════════════════════════════════════

    /// @notice Verdict = 2 must revert (only 0 or 1 allowed).
    function checkInvalidVerdictReverts() public {
        bytes32 freshHash = 0x7777777777777777777777777777777777777777777777777777777777777777;
        try registry.submitThreat(
            freshHash,
            ThreatRegistry.ThreatType.MESSAGE,
            2,   // Invalid
            90
        ) {
            assert(false);
        } catch {
            assert(true);
        }
    }

    /// @notice Verdict = 0 (benign) should be accepted.
    function checkBenignVerdictAccepted() public {
        bytes32 freshHash = 0x8888888888888888888888888888888888888888888888888888888888888888;
        registry.submitThreat(
            freshHash,
            ThreatRegistry.ThreatType.MESSAGE,
            0,   // Benign
            50
        );
        (, uint8 verdict, , , ) = registry.getThreat(freshHash);
        assert(verdict == 0);
    }

    // ══════════════════════════════════════════════════════════════
    //  11. Contract treats hashes as opaque identifiers
    // ══════════════════════════════════════════════════════════════

    /// @notice The contract must NOT attempt to interpret hash content.
    ///         Both MESSAGE and URL hashes are simply bytes32 identifiers.
    function checkHashesAreOpaqueIdentifiers() public {
        // Submit same byte pattern as both MESSAGE and URL — both should work
        bytes32 hashA = 0x9999999999999999999999999999999999999999999999999999999999999999;
        bytes32 hashB = 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;

        registry.submitThreat(hashA, ThreatRegistry.ThreatType.MESSAGE, 1, 70);
        registry.submitThreat(hashB, ThreatRegistry.ThreatType.URL, 1, 80);

        (ThreatRegistry.ThreatType tA, , , , ) = registry.getThreat(hashA);
        (ThreatRegistry.ThreatType tB, , , , ) = registry.getThreat(hashB);

        assert(tA == ThreatRegistry.ThreatType.MESSAGE);
        assert(tB == ThreatRegistry.ThreatType.URL);
    }
}
