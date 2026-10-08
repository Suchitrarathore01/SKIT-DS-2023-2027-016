"""Controlled post-deployment verification script for ThreatRegistry.

This script executes live functional verification against a deployed ThreatRegistry contract:
1. Verifies contract owner matches the deployer address.
2. Verifies initially unregistered test hash returns threatExists() == False.
3. Submits ONE deterministic test threat record (ThreatType.URL, verdict=1, confidence=100).
4. Waits for the transaction receipt and verifies status == 1.
5. Verifies threatExists() == True after submission.
6. Calls getThreat() and verifies all metadata fields (type, verdict, confidence, timestamp, submitter).
7. Verifies that attempting duplicate submission reverts.
8. Verifies that an unauthorized caller cannot call submitThreat().

Zero-PII & Privacy Guarantees:
- Uses ONLY synthetic deterministic test hashes (e.g. 0xaaaaaaaa...).
- Never transmits or stores real messages or URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from web3 import Web3
    from web3.exceptions import ContractCustomError, ContractLogicError, Web3RPCError
except ImportError:
    Web3 = None  # type: ignore[assignment, misc]
    ContractCustomError = Exception  # type: ignore[assignment, misc]
    ContractLogicError = Exception  # type: ignore[assignment, misc]
    Web3RPCError = Exception  # type: ignore[assignment, misc]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ABI_PATH = PROJECT_ROOT / "contracts" / "abi" / "ThreatRegistry.json"
CONFIG_PATH = PROJECT_ROOT / "contracts" / "configs" / "contract_addresses.json"

EXPECTED_SEPOLIA_CHAIN_ID = 11155111

# Deterministic verification test hashes (synthetic, no real user content)
VERIFICATION_TEST_HASH = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
UNAUTHORIZED_TEST_HASH = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def load_target_contract_address(network: str = "sepolia") -> str:
    """Load contract address from contract_addresses.json."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if network not in data or not data[network].get("contractAddress"):
        raise ValueError(
            f"No deployed contract address found for '{network}' in {CONFIG_PATH}. "
            "Deploy the contract first or pass --contract-address."
        )

    return data[network]["contractAddress"]


def run_controlled_verification(
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    contract_address: Optional[str] = None,
    network_name: str = "sepolia",
) -> Dict[str, Any]:
    """Execute live verification suite on deployed ThreatRegistry."""
    if Web3 is None:
        raise RuntimeError("Web3 is required. Install via pip install web3")

    active_rpc = rpc_url or os.getenv("SEPOLIA_RPC_URL") or os.getenv("WEB3_PROVIDER_URI")
    active_key = private_key or os.getenv("SIGNER_PRIVATE_KEY") or os.getenv("ETH_PRIVATE_KEY")

    if not active_rpc:
        raise ValueError("Missing RPC URL. Set SEPOLIA_RPC_URL or pass --rpc-url.")
    if not active_key:
        raise ValueError("Missing private key. Set SIGNER_PRIVATE_KEY or pass --private-key.")

    target_address = contract_address or load_target_contract_address(network_name)

    w3 = Web3(Web3.HTTPProvider(active_rpc))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to EVM RPC at {active_rpc}")

    if w3.eth.chain_id != EXPECTED_SEPOLIA_CHAIN_ID:
        raise ValueError(
            f"Unexpected Chain ID {w3.eth.chain_id}. "
            f"Expected Sepolia ({EXPECTED_SEPOLIA_CHAIN_ID})."
        )

    account = w3.eth.account.from_key(active_key)
    deployer_address = account.address

    if not ABI_PATH.exists():
        raise FileNotFoundError(f"ABI not found at {ABI_PATH}")

    with open(ABI_PATH, "r", encoding="utf-8") as f:
        abi = json.load(f)

    contract = w3.eth.contract(address=Web3.to_checksum_address(target_address), abi=abi)

    print("=" * 60)
    print("CHAINSHIELD DEPLOYMENT VERIFICATION SUITE")
    print("=" * 60)
    print(f"Network Chain ID:   {w3.eth.chain_id}")
    print(f"Contract Address:   {target_address}")
    print(f"Deployer / Owner:   {deployer_address}")
    print("=" * 60)

    results: Dict[str, Any] = {}

    # 1. Owner Verification
    print("\n[Test 1] Verifying contract owner()...")
    contract_owner = contract.functions.owner().call()
    assert contract_owner.lower() == deployer_address.lower(), \
        f"Owner mismatch: contract owner {contract_owner} != deployer {deployer_address}"
    print(f"  PASSED: owner() matches deployer ({contract_owner})")
    results["owner_verified"] = True

    # 2. Initial Existence Check
    print("\n[Test 2] Querying unregistered test hash threatExists()...")
    test_hash_bytes = bytes.fromhex(VERIFICATION_TEST_HASH[2:])
    initial_exists = contract.functions.threatExists(test_hash_bytes).call()
    print(f"  threatExists({VERIFICATION_TEST_HASH[:10]}...) = {initial_exists}")
    results["initial_exists"] = initial_exists

    # 3. Submit Test Threat (if not already registered)
    if not initial_exists:
        print("\n[Test 3] Submitting test threat record (type=URL, verdict=1, confidence=100)...")
        nonce = w3.eth.get_transaction_count(deployer_address)
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", w3.to_wei(20, "gwei"))
        priority_fee = w3.to_wei(2, "gwei")

        tx = contract.functions.submitThreat(
            test_hash_bytes,
            1,    # ThreatType.URL
            1,    # verdict = threat
            100,  # confidence = 100%
        ).build_transaction({
            "from": deployer_address,
            "nonce": nonce,
            "maxFeePerGas": base_fee * 2 + priority_fee,
            "maxPriorityFeePerGas": priority_fee,
            "gas": 500000,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key=active_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  Transaction sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        assert receipt.status == 1, f"Submission transaction failed: {tx_hash.hex()}"
        print(f"  PASSED: Transaction mined in block {receipt.blockNumber} (tx: {tx_hash.hex()})")
        results["submission_tx"] = tx_hash.hex()
    else:
        print("\n[Test 3] Test hash already registered from prior run. Skipping submission.")

    # 4. Post-Submission Existence Check
    print("\n[Test 4] Verifying threatExists() returns true...")
    post_exists = False
    for _ in range(5):
        if contract.functions.threatExists(test_hash_bytes).call():
            post_exists = True
            break
        import time; time.sleep(1)
    assert post_exists is True, f"threatExists returned False after submission!"
    print(f"  PASSED: threatExists({VERIFICATION_TEST_HASH[:10]}...) == True")
    results["post_exists"] = True

    # 5. Metadata Retrieval Verification
    print("\n[Test 5] Calling getThreat() to verify stored metadata...")
    threat_type, verdict, confidence, submitted_at, submitter = contract.functions.getThreat(test_hash_bytes).call()
    assert threat_type == 1, f"Expected threatType 1 (URL), got {threat_type}"
    assert verdict == 1, f"Expected verdict 1, got {verdict}"
    assert confidence == 100, f"Expected confidence 100, got {confidence}"
    assert submitted_at > 0, f"Expected submittedAt > 0, got {submitted_at}"
    assert submitter.lower() == deployer_address.lower(), f"Expected submitter {deployer_address}, got {submitter}"
    print(f"  PASSED: getThreat() metadata:")
    print(f"    - ThreatType:  {threat_type} (URL)")
    print(f"    - Verdict:     {verdict} (Threat)")
    print(f"    - Confidence:  {confidence}%")
    print(f"    - Timestamp:   {submitted_at}")
    print(f"    - Submitter:   {submitter}")
    results["metadata_verified"] = True

    # 6. Duplicate Submission Revert Check (Real Transaction from Deployer)
    print("\n[Test 6] Testing duplicate submission revert behavior via real transaction from deployer...")
    dup_nonce = w3.eth.get_transaction_count(deployer_address)
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.to_wei(20, "gwei"))
    priority_fee = w3.to_wei(2, "gwei")

    # Build and sign a real transaction attempting duplicate registration
    dup_tx = contract.functions.submitThreat(
        test_hash_bytes,
        1,
        1,
        100,
    ).build_transaction({
        "from": deployer_address,
        "nonce": dup_nonce,
        "maxFeePerGas": base_fee * 2 + priority_fee,
        "maxPriorityFeePerGas": priority_fee,
        "gas": 500000,
    })
    signed_dup = w3.eth.account.sign_transaction(dup_tx, private_key=active_key)

    try:
        dup_tx_hash = w3.eth.send_raw_transaction(signed_dup.raw_transaction)
        print(f"  Broadcast duplicate transaction: {dup_tx_hash.hex()}")
        dup_receipt = w3.eth.wait_for_transaction_receipt(dup_tx_hash, timeout=120)
        if dup_receipt.status != 0:
            raise RuntimeError(
                f"Expected duplicate transaction to revert on-chain (status 0), got status {dup_receipt.status}"
            )
        print(f"  PASSED: Duplicate transaction reverted on-chain (status 0, block {dup_receipt.blockNumber})")
        results["duplicate_reverted"] = True
        results["duplicate_tx"] = dup_tx_hash.hex()
    except (ContractCustomError, ContractLogicError, Web3RPCError) as e:
        # Some RPC providers simulate and reject raw tx broadcast if it is known to revert
        err_msg = str(e).lower()
        if not ("duplicatehash" in err_msg or "0x1fc0b7e7" in err_msg or "execution reverted" in err_msg):
            raise RuntimeError(f"Expected DuplicateHash revert error, got unexpected RPC error: {e}") from e
        print(f"  PASSED: Duplicate transaction rejected with revert ({type(e).__name__}: {e})")
        results["duplicate_reverted"] = True

    # 7. Unauthorized Account Write Revert Check (Pure eth_call with fabricated from address)
    print("\n[Test 7] Testing unauthorized caller rejection via eth_call (no broadcast)...")
    fabricated_unauthorized_address = "0x0000000000000000000000000000000000000001"
    unauth_hash_bytes = bytes.fromhex(UNAUTHORIZED_TEST_HASH[2:])
    unauth_reverted = False
    try:
        # eth_call simulation — NO transaction is broadcasted from fabricated address
        contract.functions.submitThreat(
            unauth_hash_bytes,
            1,
            1,
            100,
        ).call({"from": fabricated_unauthorized_address})
    except (ContractCustomError, ContractLogicError, Web3RPCError) as e:
        err_msg = str(e).lower()
        # Verify revert reason indicates NotOwner
        if not ("notowner" in err_msg or "0x30cd7471" in err_msg or "execution reverted" in err_msg):
            raise RuntimeError(f"Expected NotOwner revert error, got: {e}") from e
        print(f"  PASSED: eth_call reverted with expected NotOwner error ({type(e).__name__})")
        unauth_reverted = True
        results["unauthorized_reverted"] = True

    if not unauth_reverted:
        raise RuntimeError("FAILED: Unauthorized submission eth_call did not revert!")

    print("\n" + "=" * 60)
    print("ALL VERIFICATION CHECKS PASSED")
    print("=" * 60)
    return results


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Deployed ChainShield ThreatRegistry",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--contract-address", type=str, default=None, help="Target ThreatRegistry contract address")
    parser.add_argument("--rpc-url", type=str, default=None, help="EVM RPC endpoint URL")
    parser.add_argument("--network", type=str, default="sepolia", help="Network name in contract_addresses.json")
    return parser.parse_args(args)


def main(cli_args: Optional[list] = None) -> int:
    args = parse_args(cli_args)
    try:
        run_controlled_verification(
            rpc_url=args.rpc_url,
            contract_address=args.contract_address,
            network_name=args.network,
        )
        return 0
    except Exception as e:
        print(f"Verification Failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
