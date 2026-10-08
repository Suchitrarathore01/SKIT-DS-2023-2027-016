"""Unit tests for ThreatRegistry Solidity smart contract.

Tests verify:
    - Contract compiles successfully with solc ^0.8.20
    - ABI contains expected functions, events, and types
    - Contract bytecode is non-empty (deployable)
    - Interface matches the BLOCKCHAIN_INTEGRATION_SPEC

These tests validate the contract artifact WITHOUT requiring a running
blockchain or Hardhat/Foundry installation. Full integration testing
is performed via the Remix IDE Solidity test suite at:
    contracts/test/ThreatRegistryTest.sol

Requirements:
    pip install py-solc-x
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = PROJECT_ROOT / "contracts" / "ThreatRegistry.sol"
ABI_PATH = PROJECT_ROOT / "contracts" / "abi" / "ThreatRegistry.json"


# ══════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def solc_compile():
    """Compile ThreatRegistry.sol using py-solc-x and return contract data."""
    solcx = pytest.importorskip("solcx", reason="py-solc-x required for contract compilation tests")

    target = "0.8.20"
    # Ensure solc binary path points to writable /tmp/solcx if available
    solc_dir = Path("/tmp/solcx")
    if (solc_dir / f"solc-v{target}").exists():
        os.environ["SOLCX_BINARY_PATH"] = str(solc_dir)
    else:
        home_solcx = Path.home() / ".solcx" / f"solc-v{target}"
        if home_solcx.exists():
            solc_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy(home_solcx, solc_dir / f"solc-v{target}")
            (solc_dir / f"solc-v{target}").chmod(0o755)
            os.environ["SOLCX_BINARY_PATH"] = str(solc_dir)

    installed = solcx.get_installed_solc_versions()
    if not any(str(v).startswith(target) for v in installed):
        solcx.install_solc(target)

    source = CONTRACT_PATH.read_text(encoding="utf-8")

    compiled = solcx.compile_source(
        source,
        output_values=["abi", "bin"],
        solc_version=target,
    )

    # The key format is "<stdin>:ThreatRegistry"
    contract_key = None
    for key in compiled:
        if "ThreatRegistry" in key:
            contract_key = key
            break

    assert contract_key is not None, "ThreatRegistry not found in compiled output"
    return compiled[contract_key]


@pytest.fixture(scope="module")
def abi(solc_compile):
    """Extract the ABI from compiled contract."""
    return solc_compile["abi"]


@pytest.fixture(scope="module")
def bytecode(solc_compile):
    """Extract the bytecode from compiled contract."""
    return solc_compile["bin"]


# ══════════════════════════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════════════════════════

def _find_abi_entry(abi: list, entry_type: str, name: str) -> dict | None:
    """Find an ABI entry by type and name."""
    for entry in abi:
        if entry.get("type") == entry_type and entry.get("name") == name:
            return entry
    return None


def _get_function_names(abi: list) -> set[str]:
    """Get all function names from ABI."""
    return {e["name"] for e in abi if e.get("type") == "function"}


def _get_event_names(abi: list) -> set[str]:
    """Get all event names from ABI."""
    return {e["name"] for e in abi if e.get("type") == "event"}


# ══════════════════════════════════════════════════════════════════════
#  1. Compilation Tests
# ══════════════════════════════════════════════════════════════════════

class TestContractCompilation:
    """Verify the contract compiles and produces deployable bytecode."""

    def test_contract_file_exists(self):
        """ThreatRegistry.sol must exist at the expected path."""
        assert CONTRACT_PATH.exists(), f"Contract not found at {CONTRACT_PATH}"

    def test_pragma_version(self):
        """Contract pragma must be ^0.8.20."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        assert re.search(r"pragma\s+solidity\s+\^0\.8\.20", source), \
            "Contract must use pragma solidity ^0.8.20"

    def test_spdx_license(self):
        """Contract must have an SPDX license identifier."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "SPDX-License-Identifier" in source

    def test_compiles_successfully(self, solc_compile):
        """Contract must compile without errors."""
        assert solc_compile is not None

    def test_bytecode_non_empty(self, bytecode):
        """Compiled bytecode must be non-empty (deployable)."""
        assert bytecode and len(bytecode) > 0, "Bytecode is empty — contract is not deployable"

    def test_abi_non_empty(self, abi):
        """ABI must contain entries."""
        assert len(abi) > 0, "ABI is empty"


# ══════════════════════════════════════════════════════════════════════
#  2. ABI Structure Tests
# ══════════════════════════════════════════════════════════════════════

class TestABIFunctions:
    """Verify the ABI exposes the required public interface."""

    def test_has_threatExists(self, abi):
        """ABI must contain threatExists(bytes32) -> bool."""
        fn = _find_abi_entry(abi, "function", "threatExists")
        assert fn is not None, "Missing function: threatExists"
        assert fn["stateMutability"] == "view"
        inputs = fn["inputs"]
        assert len(inputs) == 1
        assert inputs[0]["type"] == "bytes32"
        outputs = fn["outputs"]
        assert any(o["type"] == "bool" for o in outputs)

    def test_has_submitThreat(self, abi):
        """ABI must contain submitThreat(bytes32, uint8, uint8, uint16)."""
        fn = _find_abi_entry(abi, "function", "submitThreat")
        assert fn is not None, "Missing function: submitThreat"
        assert fn["stateMutability"] == "nonpayable"
        input_types = [i["type"] for i in fn["inputs"]]
        assert "bytes32" in input_types, "submitThreat must accept bytes32"

    def test_has_getThreat(self, abi):
        """ABI must contain getThreat(bytes32) returning metadata."""
        fn = _find_abi_entry(abi, "function", "getThreat")
        assert fn is not None, "Missing function: getThreat"
        assert fn["stateMutability"] == "view"
        inputs = fn["inputs"]
        assert len(inputs) == 1
        assert inputs[0]["type"] == "bytes32"
        # Must return multiple values (struct-like)
        assert len(fn["outputs"]) >= 5, "getThreat must return at least 5 fields"

    def test_has_owner(self, abi):
        """ABI must contain owner() -> address."""
        fn = _find_abi_entry(abi, "function", "owner")
        assert fn is not None, "Missing function: owner"
        assert fn["stateMutability"] == "view"

    def test_has_threatCount(self, abi):
        """ABI must contain threatCount() -> uint256."""
        fn = _find_abi_entry(abi, "function", "threatCount")
        assert fn is not None, "Missing function: threatCount"

    def test_has_transferOwnership(self, abi):
        """ABI must contain transferOwnership(address)."""
        fn = _find_abi_entry(abi, "function", "transferOwnership")
        assert fn is not None, "Missing function: transferOwnership"
        input_types = [i["type"] for i in fn["inputs"]]
        assert "address" in input_types

    def test_no_unexpected_write_functions(self, abi):
        """Only submitThreat and transferOwnership should be state-changing."""
        write_fns = {
            e["name"] for e in abi
            if e.get("type") == "function"
            and e.get("stateMutability") == "nonpayable"
        }
        expected_writes = {"submitThreat", "transferOwnership"}
        assert write_fns == expected_writes, \
            f"Unexpected write functions: {write_fns - expected_writes}"


class TestABIEvents:
    """Verify events are defined correctly."""

    def test_has_ThreatSubmitted_event(self, abi):
        """ABI must contain ThreatSubmitted event."""
        ev = _find_abi_entry(abi, "event", "ThreatSubmitted")
        assert ev is not None, "Missing event: ThreatSubmitted"
        input_names = {i["name"] for i in ev["inputs"]}
        assert "threatHash" in input_names
        assert "submitter" in input_names

    def test_threatSubmitted_indexed_fields(self, abi):
        """ThreatSubmitted must index threatHash and submitter."""
        ev = _find_abi_entry(abi, "event", "ThreatSubmitted")
        indexed = {i["name"] for i in ev["inputs"] if i.get("indexed")}
        assert "threatHash" in indexed, "threatHash must be indexed"
        assert "submitter" in indexed, "submitter must be indexed"

    def test_has_OwnershipTransferred_event(self, abi):
        """ABI must contain OwnershipTransferred event."""
        ev = _find_abi_entry(abi, "event", "OwnershipTransferred")
        assert ev is not None, "Missing event: OwnershipTransferred"


class TestABIErrors:
    """Verify custom errors are defined."""

    def test_has_custom_errors(self, abi):
        """ABI must contain custom error definitions."""
        error_names = {e["name"] for e in abi if e.get("type") == "error"}
        expected = {"NotOwner", "ZeroHash", "DuplicateHash",
                    "ConfidenceOutOfRange", "InvalidVerdict", "ThreatNotFound",
                    "ZeroAddress"}
        assert expected.issubset(error_names), \
            f"Missing custom errors: {expected - error_names}"


# ══════════════════════════════════════════════════════════════════════
#  3. Contract Source Validation
# ══════════════════════════════════════════════════════════════════════

class TestContractSourceIntegrity:
    """Validate contract source code properties without compilation."""

    def test_no_raw_text_storage(self):
        """Contract must not store raw messages or URLs."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        # Should not have string storage for messages/URLs
        assert "string" not in source or "string" in source.split("//")[0] is False or True
        # More precise: no state variable of type string
        lines = source.split("\n")
        string_state = [
            line.strip() for line in lines
            if re.match(r"\s*(string\s+(public|private|internal)\s+\w+)", line)
        ]
        assert len(string_state) == 0, \
            f"Contract stores raw strings in state: {string_state}"

    def test_no_nlp_references(self):
        """Contract must not reference NLP, NLTK, or tokenization in code."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        source_no_comments = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        source_no_comments = re.sub(r"//.*", "", source_no_comments).lower()
        forbidden = ["nltk", "tokenize", "lemmatiz", "stemm", "nlp"]
        for term in forbidden:
            assert term not in source_no_comments, \
                f"Contract code references forbidden NLP term: {term}"

    def test_no_pii_fields(self):
        """Contract must not define fields for PII."""
        source = CONTRACT_PATH.read_text(encoding="utf-8").lower()
        pii_terms = ["email", "phone", "username", "password", "ssn"]
        for term in pii_terms:
            assert term not in source, f"Contract contains PII-related field: {term}"

    def test_uses_mapping_for_storage(self):
        """Contract must use mapping(bytes32 => ...) for threat storage."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "mapping(bytes32 =>" in source, \
            "Contract must use mapping(bytes32 => ...) for threat storage"

    def test_enum_threat_type_exists(self):
        """Contract must define ThreatType enum with MESSAGE and URL."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "enum ThreatType" in source
        assert "MESSAGE" in source
        assert "URL" in source

    def test_struct_threat_exists(self):
        """Contract must define Threat struct."""
        source = CONTRACT_PATH.read_text(encoding="utf-8")
        assert "struct Threat" in source


# ══════════════════════════════════════════════════════════════════════
#  4. ABI Export Test
# ══════════════════════════════════════════════════════════════════════

class TestABIExport:
    """Verify the ABI can be exported to the expected path."""

    def test_abi_is_valid_json(self, abi):
        """ABI must be serializable to valid JSON."""
        json_str = json.dumps(abi, indent=2)
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_abi_export_path_exists(self):
        """ABI export directory must exist."""
        assert ABI_PATH.parent.exists(), \
            f"ABI directory does not exist: {ABI_PATH.parent}"

    def test_write_abi_artifact(self, abi):
        """Write compiled ABI to contracts/abi/ThreatRegistry.json."""
        ABI_PATH.write_text(json.dumps(abi, indent=2) + "\n", encoding="utf-8")
        assert ABI_PATH.exists()
        # Verify round-trip
        loaded = json.loads(ABI_PATH.read_text(encoding="utf-8"))
        assert loaded == abi
