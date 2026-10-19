
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

from src.blockchain.hashing import generate_url_hash

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

CONFIG_PATH = PROJECT_ROOT / "contracts" / "configs" / "contract_addresses.json"
ABI_PATH = PROJECT_ROOT / "contracts" / "abi" / "ThreatRegistry.json"


def check_blockchain_threat(url: str) -> dict:
    """Check a URL against the blockchain registry using read-only calls."""

    result = {
        "available": False,
        "found": False,
        "verdict": None,
        "threat_type": None,
        "confidence": None,
        "error": None,
    }

    try:
        rpc_url = (
            os.getenv("SEPOLIA_RPC_URL")
            or os.getenv("WEB3_PROVIDER_URI")
        )

        if not rpc_url:
            result["error"] = "RPC endpoint is not configured"
            return result

        with open(CONFIG_PATH, encoding="utf-8") as file:
            config = json.load(file)

        with open(ABI_PATH, encoding="utf-8") as file:
            abi = json.load(file)

        network_config = config["sepolia"]
        contract_address = Web3.to_checksum_address(
            network_config["contractAddress"]
        )

        web3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": 10},
            )
        )

        if not web3.is_connected():
            result["error"] = "Could not connect to Sepolia RPC"
            return result

        if web3.eth.chain_id != network_config["chainId"]:
            result["error"] = "Connected network does not match Sepolia"
            return result

        if not web3.eth.get_code(contract_address):
            result["error"] = "ThreatRegistry contract is not deployed"
            return result

        contract = web3.eth.contract(
            address=contract_address,
            abi=abi,
        )

        url_hash = generate_url_hash(url)
        hash_bytes = bytes.fromhex(url_hash[2:])

        exists = contract.functions.threatExists(hash_bytes).call()
        result["available"] = True

        if not exists:
            return result

        threat = contract.functions.getThreat(hash_bytes).call()

        result["found"] = True
        result["threat_type"] = int(threat[0])
        result["verdict"] = int(threat[1])
        result["confidence"] = int(threat[2])

        return result

    except Exception:
        logger.warning("Blockchain lookup failed.")
        result["available"] = False
        result["error"] = "Blockchain lookup failed"
        return result
