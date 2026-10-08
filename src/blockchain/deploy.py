"""Sepolia deployment script for ChainShield ThreatRegistry.

This module automates the secure deployment of the ThreatRegistry Solidity contract
to Ethereum Sepolia testnet using Web3.py.

Security & Safety Guarantees:
- Reads credentials strictly from environment variables or .env file.
- NEVER logs, prints, or exposes private keys.
- Validates RPC connectivity and network Chain ID (default Sepolia: 11155111) before deploying.
- Verifies wallet balance to ensure sufficient gas.
- Validates deployed contract ownership matches the deployer address.
- Updates contracts/configs/contract_addresses.json upon verified deployment.
- Deployment and dataset seeding remain completely separated.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from web3 import Web3
    from web3.exceptions import Web3Exception
except ImportError:
    Web3 = None  # type: ignore[assignment, misc]

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = PROJECT_ROOT / "contracts" / "ThreatRegistry.sol"
ABI_PATH = PROJECT_ROOT / "contracts" / "abi" / "ThreatRegistry.json"
CONFIG_PATH = PROJECT_ROOT / "contracts" / "configs" / "contract_addresses.json"

EXPECTED_SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_CHAIN_ID = EXPECTED_SEPOLIA_CHAIN_ID


def load_environment() -> Tuple[str, str]:
    """Load and validate required environment variables for deployment.

    Returns:
        Tuple of (rpc_url, private_key).

    Raises:
        ValueError: If required environment variables are missing.
    """
    rpc_url = os.getenv("SEPOLIA_RPC_URL") or os.getenv("WEB3_PROVIDER_URI")
    private_key = os.getenv("SIGNER_PRIVATE_KEY") or os.getenv("ETH_PRIVATE_KEY")

    missing = []
    if not rpc_url:
        missing.append("SEPOLIA_RPC_URL")
    if not private_key:
        missing.append("SIGNER_PRIVATE_KEY")

    if missing:
        raise ValueError(
            f"Missing required deployment environment variable(s): {', '.join(missing)}.\n"
            "Set them in your environment or in a local .env file (see .env.example).\n"
            "DO NOT commit real keys to version control."
        )

    # Clean private key string
    clean_key = private_key.strip()
    return rpc_url.strip(), clean_key


def load_abi_and_bytecode() -> Tuple[list, str]:
    """Load contract ABI and compile bytecode using solcx.

    Returns:
        Tuple of (abi_list, bytecode_hex_str).
    """
    if not ABI_PATH.exists():
        raise FileNotFoundError(f"ABI file not found at {ABI_PATH}")

    with open(ABI_PATH, "r", encoding="utf-8") as f:
        abi = json.load(f)

    # Compile bytecode using solcx
    try:
        import solcx

        target = "0.8.20"
        solc_dir = Path("/tmp/solcx")
        if (solc_dir / f"solc-v{target}").exists():
            os.environ["SOLCX_BINARY_PATH"] = str(solc_dir)

        installed = solcx.get_installed_solc_versions()
        if not any(str(v).startswith(target) for v in installed):
            solcx.install_solc(target)

        source = CONTRACT_PATH.read_text(encoding="utf-8")
        compiled = solcx.compile_source(
            source,
            output_values=["bin"],
            solc_version=target,
        )

        contract_key = None
        for key in compiled:
            if "ThreatRegistry" in key:
                contract_key = key
                break

        if contract_key is None:
            raise RuntimeError("ThreatRegistry contract not found in compilation output.")

        bytecode = compiled[contract_key]["bin"]
        if not bytecode:
            raise RuntimeError("Compiled bytecode is empty.")

        return abi, bytecode

    except Exception as e:
        raise RuntimeError(f"Failed to compile ThreatRegistry bytecode: {e}") from e


def update_contract_config(
    network_name: str,
    chain_id: int,
    contract_address: str,
    deployment_tx: str,
    block_number: int,
) -> None:
    """Update contracts/configs/contract_addresses.json with deployed address."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    formatted_tx = deployment_tx if deployment_tx.startswith("0x") else f"0x{deployment_tx}"
    data[network_name] = {
        "chainId": chain_id,
        "contractAddress": contract_address,
        "deploymentTx": formatted_tx,
        "blockNumber": block_number,
        "deployedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def deploy_contract(
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    expected_chain_id: int = SEPOLIA_CHAIN_ID,
    confirmations: int = 1,
) -> Dict[str, Any]:
    """Execute ThreatRegistry smart contract deployment to EVM network.

    Args:
        rpc_url: RPC provider URL (loads from env if None).
        private_key: Private key of deployer (loads from env if None).
        expected_chain_id: Expected network Chain ID (default Sepolia: 11155111).
        confirmations: Number of block confirmations to wait for.

    Returns:
        Dict with deployment details (address, tx_hash, block, deployer, chain_id).
    """
    if Web3 is None:
        raise RuntimeError("Web3 is required. Install via pip install web3")

    active_rpc, active_key = (rpc_url, private_key) if (rpc_url and private_key) else load_environment()

    # 1. Connect to node
    w3 = Web3(Web3.HTTPProvider(active_rpc))
    if not w3.is_connected():
        raise ConnectionError(f"Could not connect to EVM RPC at {active_rpc}")

    # 2. Verify Chain ID
    chain_id = w3.eth.chain_id
    if chain_id != EXPECTED_SEPOLIA_CHAIN_ID:
        raise ValueError(
            f"Unexpected Chain ID {chain_id}. Expected Sepolia "
            f"({EXPECTED_SEPOLIA_CHAIN_ID}). Aborting."
        )

    # 3. Derive deployer account
    account = w3.eth.account.from_key(active_key)
    deployer_address = account.address
    print(f"Connected to Network: Chain ID {chain_id}")
    print(f"Deployer Public Address: {deployer_address}")

    # 4. Check balance
    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"Deployer Balance:        {balance_eth:.6f} ETH")

    if balance_wei == 0:
        raise RuntimeError(
            f"Deployer wallet {deployer_address} has 0 ETH. "
            "Fund this account with SepoliaETH from a faucet before deploying."
        )

    # 5. Load ABI and Bytecode
    abi, bytecode = load_abi_and_bytecode()

    # 6. Build deployment transaction
    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer_address)

    # Estimate gas and fees
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.to_wei(20, "gwei"))
    priority_fee = w3.to_wei(2, "gwei")
    max_fee = base_fee * 2 + priority_fee

    deploy_tx = contract_factory.constructor().build_transaction({
        "from": deployer_address,
        "nonce": nonce,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
        "chainId": chain_id,
    })

    print("Signing deployment transaction...")
    signed_tx = w3.eth.account.sign_transaction(deploy_tx, private_key=active_key)

    print("Broadcasting transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    print(f"Transaction Hash: {tx_hash_hex}")

    print(f"Waiting for receipt ({confirmations} confirmation)...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

    if receipt.status != 1:
        raise RuntimeError(f"Deployment transaction failed: {tx_hash_hex}")

    contract_address = receipt.contractAddress
    block_number = receipt.blockNumber
    print("=" * 60)
    print("DEPLOYMENT SUCCESSFUL")
    print("=" * 60)
    print(f"Contract Address:  {contract_address}")
    print(f"Transaction Hash:  {tx_hash_hex}")
    print(f"Block Number:      {block_number}")
    print(f"Gas Used:          {receipt.gasUsed:,}")
    print(f"Deployer:          {deployer_address}")
    print(f"Chain ID:          {chain_id}")
    print("=" * 60)

    # 7. Verify deployed owner
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)
    contract_owner = deployed_contract.functions.owner().call()
    if contract_owner.lower() != deployer_address.lower():
        raise RuntimeError(
            f"Post-deployment verification error: owner() {contract_owner} != deployer {deployer_address}"
        )
    print("Contract ownership verified.")

    # 8. Update configuration
    network_label = "sepolia" if chain_id == EXPECTED_SEPOLIA_CHAIN_ID else f"chain_{chain_id}"
    update_contract_config(
        network_name=network_label,
        chain_id=chain_id,
        contract_address=contract_address,
        deployment_tx=tx_hash_hex,
        block_number=block_number,
    )
    print(f"Updated configuration at {CONFIG_PATH}")

    return {
        "contractAddress": contract_address,
        "transactionHash": tx_hash_hex,
        "blockNumber": block_number,
        "deployer": deployer_address,
        "chainId": chain_id,
        "gasUsed": receipt.gasUsed,
    }


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy ChainShield ThreatRegistry to Sepolia Testnet",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--rpc-url", type=str, default=None, help="EVM RPC endpoint URL")
    parser.add_argument("--chain-id", type=int, default=SEPOLIA_CHAIN_ID, help="Expected network Chain ID")
    parser.add_argument("--check-only", action="store_true", help="Validate environment and balance without deploying")
    return parser.parse_args(args)


def main(cli_args: Optional[list] = None) -> int:
    args = parse_args(cli_args)

    try:
        rpc_url, private_key = load_environment()
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1

    if args.check_only:
        print("Validating environment and network connectivity...")
        if Web3 is None:
            print("Web3 is not installed.", file=sys.stderr)
            return 1
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            print(f"Failed to connect to {rpc_url}", file=sys.stderr)
            return 1
        chain_id = w3.eth.chain_id
        if chain_id != EXPECTED_SEPOLIA_CHAIN_ID:
            raise ValueError(
                f"Unexpected Chain ID {chain_id}. Expected Sepolia "
                f"({EXPECTED_SEPOLIA_CHAIN_ID}). Aborting."
            )
        account = w3.eth.account.from_key(private_key)
        balance = w3.from_wei(w3.eth.get_balance(account.address), "ether")
        print(f"Network:  Chain ID {chain_id}")
        print(f"Deployer: {account.address}")
        print(f"Balance:  {balance:.6f} ETH")
        print("Ready for deployment.")
        return 0

    try:
        deploy_contract(
            rpc_url=rpc_url,
            private_key=private_key,
            expected_chain_id=args.chain_id,
        )
        return 0
    except Exception as e:
        print(f"Deployment failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
