"""Threat registry seeding pipeline for ChainShield.

This module processes threat datasets (URLs and Messages), canonicalizes and
hashes each threat record using the exact ChainShield pipeline, deduplicates
by Keccak-256 threat hash, and prepares/submits seed records to the
ThreatRegistry smart contract.

Architecture & Privacy Guarantees:
- Uses the EXACT SAME canonicalization and hashing functions from
  `src.blockchain.canonicalize` and `src.blockchain.hashing`.
- Seeding registers ONLY confirmed threats (verdict = 1, confidence = 100).
- Benign records are strictly excluded.
- Deduplication is performed on the final Keccak-256 `bytes32` hash.
- Zero raw text, URLs, or PII are ever sent in blockchain transactions,
  stored on-chain, or exported into generated seed payloads.
- Default execution is strictly DRY RUN. Blockchain writes require the
  explicit `--submit` flag.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

from src.blockchain.canonicalize import canonicalize_message, canonicalize_url
from src.blockchain.hashing import generate_message_hash, generate_url_hash

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ThreatTypeEnum(IntEnum):
    """Solidity ThreatType enum mapping."""
    MESSAGE = 0
    URL = 1


@dataclass(frozen=True)
class ThreatSeedRecord:
    """Minimal on-chain seed record containing ZERO raw data or PII."""
    threatHash: str      # 0x-prefixed 64 hex characters (bytes32)
    threatType: int      # 0 = MESSAGE, 1 = URL
    verdict: int         # Always 1 for known threats
    confidence: int      # 100 for dataset-confirmed threats
    sourceRow: int       # Source row index (for local debugging/traceability)

    def to_contract_args(self) -> Dict[str, Any]:
        """Return parameters formatted for ThreatRegistry.submitThreat."""
        return {
            "threatHash": self.threatHash,
            "threatType": self.threatType,
            "verdict": self.verdict,
            "confidence": self.confidence,
        }

    def to_clean_dict(self) -> Dict[str, Any]:
        """Export dictionary without internal sourceRow, safe for sharing."""
        return {
            "threatHash": self.threatHash,
            "threatType": "URL" if self.threatType == ThreatTypeEnum.URL else "MESSAGE",
            "threatTypeInt": self.threatType,
            "verdict": self.verdict,
            "confidence": self.confidence,
        }


@dataclass
class SeedingStatistics:
    """Summary metrics of a dataset seeding run."""
    dataset_path: str
    total_records: int = 0
    threat_records: int = 0
    benign_records: int = 0
    invalid_records: int = 0
    raw_duplicate_records: int = 0
    canonical_duplicate_records: int = 0
    unique_threat_hashes: int = 0
    message_threats: int = 0
    url_threats: int = 0

    def print_summary(self) -> None:
        """Print formatted terminal report."""
        print("=" * 60)
        print("CHAINSHIELD THREAT REGISTRY SEEDING REPORT")
        print("=" * 60)
        print(f"Dataset Path:                {self.dataset_path}")
        print(f"Total dataset records:       {self.total_records:,}")
        print(f"Threat records (eligible):   {self.threat_records:,}")
        print(f"Benign records (skipped):    {self.benign_records:,}")
        print(f"Invalid / missing records:   {self.invalid_records:,}")
        print("-" * 60)
        print(f"Raw duplicate records:       {self.raw_duplicate_records:,}")
        print(f"Canonical duplicates:        {self.canonical_duplicate_records:,}")
        print(f"Total duplicate instances:   {self.raw_duplicate_records + self.canonical_duplicate_records:,}")
        print("-" * 60)
        print(f"Unique threat hashes:        {self.unique_threat_hashes:,}")
        print(f"  - URL threats:             {self.url_threats:,}")
        print(f"  - Message threats:         {self.message_threats:,}")
        print("=" * 60)


def detect_columns(header: List[str]) -> Tuple[str, str, ThreatTypeEnum]:
    """Detect text/URL column, label column, and ThreatType from CSV header.

    Returns:
        Tuple of (content_col, label_col, ThreatTypeEnum).
    """
    clean_cols = [c.replace("\ufeff", "").replace("ï»¿", "").strip() for c in header]
    cols_lower = {c.lower(): original for c, original in zip(clean_cols, header)}

    # Check for URL column first
    url_candidates = ["url", "urls", "phishing_url"]
    for cand in url_candidates:
        if cand in cols_lower:
            content_col = cols_lower[cand]
            threat_type = ThreatTypeEnum.URL
            break
    else:
        # Check for message / text column
        msg_candidates = ["text", "message", "sms", "body", "content", "v2"]
        for cand in msg_candidates:
            if cand in cols_lower:
                content_col = cols_lower[cand]
                threat_type = ThreatTypeEnum.MESSAGE
                break
        else:
            raise ValueError(
                f"Could not automatically detect text or URL column from header: {header}. "
                "Specify explicitly via --content-col."
            )

    # Detect label column
    label_candidates = ["label", "category", "class", "target", "v1"]
    for cand in label_candidates:
        if cand in cols_lower:
            label_col = cols_lower[cand]
            break
    else:
        raise ValueError(
            f"Could not automatically detect label column from header: {header}. "
            "Specify explicitly via --label-col."
        )

    return content_col, label_col, threat_type


def is_threat_label(label: str, threat_type: ThreatTypeEnum, explicit_threat_label: Optional[str] = None) -> bool:
    """Determine whether a dataset label indicates a confirmed threat.

    Policy:
    - If explicit_threat_label is provided, matches that value (case-insensitive).
    - For PhiUSIIL URL dataset: '0' = Phishing (threat), '1' = Legitimate (benign).
    - For message datasets: '1', 'spam', 'malicious', 'smishing', 'phishing' = threat.
      '0', 'ham', 'benign', 'legitimate' = benign.
    """
    cleaned = str(label).strip().lower()

    if explicit_threat_label is not None:
        return cleaned == explicit_threat_label.strip().lower()

    if threat_type == ThreatTypeEnum.URL:
        # PhiUSIIL benchmark convention: 0 is phishing threat, 1 is legitimate
        if cleaned in ("0", "phishing", "malicious", "threat"):
            return True
        elif cleaned in ("1", "legitimate", "benign", "safe"):
            return False
        else:
            raise ValueError(f"Ambiguous URL dataset label: '{label}'. Specify --threat-label explicitly.")
    else:
        # SMS / message benchmark convention
        if cleaned in ("1", "spam", "malicious", "smishing", "phishing"):
            return True
        elif cleaned in ("0", "ham", "benign", "legitimate", "safe"):
            return False
        else:
            raise ValueError(f"Ambiguous message dataset label: '{label}'. Specify --threat-label explicitly.")


def process_dataset(
    dataset_path: str | Path,
    content_col: Optional[str] = None,
    label_col: Optional[str] = None,
    threat_type_override: Optional[ThreatTypeEnum] = None,
    explicit_threat_label: Optional[str] = None,
    limit: Optional[int] = None,
) -> Tuple[List[ThreatSeedRecord], SeedingStatistics]:
    """Process a dataset CSV, canonicalize, hash, and deduplicate threat records.

    Args:
        dataset_path: Path to dataset CSV file.
        content_col: Name of column containing URL or text (auto-detected if None).
        label_col: Name of column containing label (auto-detected if None).
        threat_type_override: Explicit ThreatTypeEnum (MESSAGE or URL).
        explicit_threat_label: Custom label string representing a threat.
        limit: Maximum number of unique threat records to extract.

    Returns:
        Tuple of (list of unique ThreatSeedRecord, SeedingStatistics).
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")

    stats = SeedingStatistics(dataset_path=str(path))
    unique_records: List[ThreatSeedRecord] = []
    seen_hashes: Set[str] = set()
    seen_raw_content: Set[str] = set()

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return unique_records, stats

        # Clean header column names
        cleaned_header = [c.replace("\ufeff", "").replace("ï»¿", "").strip() for c in header]

        # Determine columns and ThreatType
        auto_content, auto_label, detected_type = detect_columns(header)
        active_content_col = content_col or auto_content
        active_label_col = label_col or auto_label
        active_threat_type = threat_type_override if threat_type_override is not None else detected_type

        # Find column indices
        try:
            content_idx = cleaned_header.index(active_content_col)
        except ValueError:
            content_idx = header.index(active_content_col)

        try:
            label_idx = cleaned_header.index(active_label_col)
        except ValueError:
            label_idx = header.index(active_label_col)

        for row_num, row in enumerate(reader, start=1):
            stats.total_records += 1

            if len(row) <= max(content_idx, label_idx):
                stats.invalid_records += 1
                continue

            raw_content = row[content_idx].strip()
            raw_label = row[label_idx].strip()

            if not raw_content or not raw_label:
                stats.invalid_records += 1
                continue

            # Classify threat vs benign
            try:
                is_threat = is_threat_label(raw_label, active_threat_type, explicit_threat_label)
            except ValueError:
                stats.invalid_records += 1
                continue

            if not is_threat:
                stats.benign_records += 1
                continue

            stats.threat_records += 1

            # Check raw duplicate
            if raw_content in seen_raw_content:
                stats.raw_duplicate_records += 1
            else:
                seen_raw_content.add(raw_content)

            # Generate Keccak-256 hash using the EXACT ChainShield pipeline
            try:
                if active_threat_type == ThreatTypeEnum.URL:
                    threat_hash = generate_url_hash(raw_content)
                else:
                    threat_hash = generate_message_hash(raw_content)
            except (ValueError, TypeError):
                stats.invalid_records += 1
                continue

            # Check hash-based duplicate (catches both raw dupes and canonicalization dupes)
            if threat_hash in seen_hashes:
                stats.canonical_duplicate_records += 1
                continue

            # Valid unique threat record
            seen_hashes.add(threat_hash)
            record = ThreatSeedRecord(
                threatHash=threat_hash,
                threatType=int(active_threat_type),
                verdict=1,        # Known threat
                confidence=100,   # Dataset-confirmed ground truth
                sourceRow=row_num,
            )
            unique_records.append(record)

            if active_threat_type == ThreatTypeEnum.URL:
                stats.url_threats += 1
            else:
                stats.message_threats += 1

            stats.unique_threat_hashes += 1

            if limit is not None and len(unique_records) >= limit:
                break

    return unique_records, stats


def export_seed_json(records: List[ThreatSeedRecord], output_path: str | Path) -> None:
    """Export clean seed payload to JSON. Guarantees ZERO raw content or PII."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_clean_dict() for r in records]
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def submit_seeds_to_blockchain(
    records: List[ThreatSeedRecord],
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    contract_address: Optional[str] = None,
    abi_path: Optional[str | Path] = None,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """Submit unique threat seeds to the deployed ThreatRegistry contract.

    Safety:
    - Requires Web3 to be installed.
    - Requires explicit RPC URL, private key, and contract address.
    - Checks `threatExists(hash)` to avoid redundant transactions or reverts.
    - Emits clear progress and transaction hashes.
    """
    try:
        from web3 import Web3
    except ImportError:
        raise RuntimeError(
            "Web3.py is required for on-chain submission. "
            "Install with: pip install web3"
        )

    active_rpc = rpc_url or os.getenv("SEPOLIA_RPC_URL") or os.getenv("WEB3_PROVIDER_URI")
    active_key = private_key or os.getenv("SIGNER_PRIVATE_KEY") or os.getenv("ETH_PRIVATE_KEY")

    if not active_rpc:
        raise ValueError("Missing RPC URL. Provide --rpc-url or set SEPOLIA_RPC_URL.")
    if not active_key:
        raise ValueError("Missing private key. Provide --private-key or set SIGNER_PRIVATE_KEY.")
    if not contract_address:
        config_path = Path("contracts/configs/contract_addresses.json")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    contract_address = cfg.get("sepolia", {}).get("contractAddress")
            except Exception:
                pass

    if not contract_address:
        raise ValueError("Missing contract address. Provide --contract-address.")

    w3 = Web3(Web3.HTTPProvider(active_rpc))
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to RPC node at {active_rpc}")

    account = w3.eth.account.from_key(active_key)
    caller_address = account.address

    # Load ABI
    active_abi_path = Path(abi_path) if abi_path else Path("contracts/abi/ThreatRegistry.json")
    if not active_abi_path.exists():
        raise FileNotFoundError(f"ABI file not found at {active_abi_path}")

    with open(active_abi_path, "r", encoding="utf-8") as f:
        abi = json.load(f)

    contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

    # Verify owner
    contract_owner = contract.functions.owner().call()
    if contract_owner.lower() != caller_address.lower():
        raise PermissionError(
            f"Signer {caller_address} is not contract owner {contract_owner}. Submission rejected."
        )

    print(f"Connected to network. Chain ID: {w3.eth.chain_id}")
    print(f"Contract: {contract_address}")
    print(f"Signer:   {caller_address}")
    print(f"Submitting {len(records)} seed records in batches of {batch_size}...")

    submitted_count = 0
    skipped_count = 0
    tx_hashes: List[str] = []

    current_nonce = max(
        w3.eth.get_transaction_count(caller_address, "pending"),
        w3.eth.get_transaction_count(caller_address, "latest"),
    )

    for i, record in enumerate(records, start=1):
        # Convert hex string to bytes32 bytes
        hash_bytes = bytes.fromhex(record.threatHash[2:]) if record.threatHash.startswith("0x") else bytes.fromhex(record.threatHash)

        # Check existence first
        already_exists = contract.functions.threatExists(hash_bytes).call()
        if already_exists:
            skipped_count += 1
            continue

        # Prepare transaction with dynamic EIP-1559 gas pricing
        nonce = current_nonce
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", w3.to_wei(20, "gwei"))
        priority_fee = w3.to_wei(2, "gwei")
        tx = contract.functions.submitThreat(
            hash_bytes,
            record.threatType,
            record.verdict,
            record.confidence,
        ).build_transaction({
            "from": caller_address,
            "nonce": nonce,
            "gas": 500000,
            "maxFeePerGas": base_fee * 2 + priority_fee,
            "maxPriorityFeePerGas": priority_fee,
        })

        signed = w3.eth.account.sign_transaction(tx, private_key=active_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        current_nonce += 1

        if tx_receipt.status != 1:
            raise RuntimeError(f"Transaction failed for record {record.threatHash}: tx={tx_hash.hex()}")

        submitted_count += 1
        tx_hashes.append(tx_hash.hex())

        if submitted_count % 10 == 0:
            print(f"  Submitted {submitted_count}/{len(records)} threats (tx: {tx_hash.hex()[:10]}...)")

    return {
        "total_records": len(records),
        "submitted": submitted_count,
        "skipped_existing": skipped_count,
        "tx_hashes": tx_hashes,
    }


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ChainShield Threat Registry Dataset Seeding Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="data/processed/cleaned_url.csv",
        help="Path to dataset CSV to seed from",
    )
    parser.add_argument(
        "--content-col",
        type=str,
        default=None,
        help="Column containing raw text or URL (auto-detected if omitted)",
    )
    parser.add_argument(
        "--label-col",
        type=str,
        default=None,
        help="Column containing threat/benign label (auto-detected if omitted)",
    )
    parser.add_argument(
        "--threat-type",
        type=str,
        choices=["MESSAGE", "URL"],
        default=None,
        help="Explicit ThreatType override (auto-detected if omitted)",
    )
    parser.add_argument(
        "--threat-label",
        type=str,
        default=None,
        help="Explicit value representing a threat in the label column (default: '0' for PhiUSIIL URL)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of unique threat records to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Perform dry-run analysis without blockchain writes (DEFAULT)",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        default=False,
        help="Explicitly submit threat seeds to deployed blockchain contract",
    )
    parser.add_argument(
        "--contract-address",
        type=str,
        default=None,
        help="Target ThreatRegistry contract address on Sepolia/EVM",
    )
    parser.add_argument(
        "--rpc-url",
        type=str,
        default=None,
        help="EVM RPC endpoint URL (or via SEPOLIA_RPC_URL env var)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to export clean deduplicated seed records JSON",
    )
    return parser.parse_args(args)


def main(cli_args: Optional[List[str]] = None) -> int:
    """Entry point for the threat registry seeding CLI."""
    args = parse_args(cli_args)

    # Resolve threat type override if specified
    type_override = None
    if args.threat_type:
        type_override = ThreatTypeEnum.MESSAGE if args.threat_type == "MESSAGE" else ThreatTypeEnum.URL

    # Resolve dataset path: fallback to data/raw if data/processed is missing
    target_path = Path(args.dataset_path)
    if not target_path.exists():
        fallback = Path("data/raw/PhiUSIIL_Phishing_URL_Dataset.csv")
        if fallback.exists():
            print(f"Warning: {target_path} not found. Falling back to {fallback}")
            target_path = fallback

    records, stats = process_dataset(
        dataset_path=target_path,
        content_col=args.content_col,
        label_col=args.label_col,
        threat_type_override=type_override,
        explicit_threat_label=args.threat_label,
        limit=args.limit,
    )

    # Print dry-run summary
    stats.print_summary()

    # Print debug samples without exposing sensitive raw content
    sample_count = min(5, len(records))
    if sample_count > 0:
        print("\nRepresentative Seed Fingerprints (Zero-PII Sample):")
        for i in range(sample_count):
            r = records[i]
            type_name = "URL" if r.threatType == ThreatTypeEnum.URL else "MESSAGE"
            print(f"  [{i + 1}] row={r.sourceRow:<6} type={type_name:<7} hash={r.threatHash}  verdict={r.verdict}  confidence={r.confidence}")

    # Export seed JSON if requested
    if args.output:
        export_seed_json(records, args.output)
        print(f"\nExported {len(records)} clean seed records to {args.output}")

    # Handle on-chain submission
    if args.submit:
        print("\n" + "!" * 60)
        print("ON-CHAIN SUBMISSION REQUESTED")
        print("!" * 60)
        res = submit_seeds_to_blockchain(
            records=records,
            rpc_url=args.rpc_url,
            contract_address=args.contract_address,
        )
        print("\n" + "=" * 60)
        print("SEED SUBMISSION SUMMARY")
        print("=" * 60)
        print(f"Total records processed: {res['total_records']}")
        print(f"Submitted on-chain:      {res['submitted']}")
        print(f"Skipped (already exist): {res['skipped_existing']}")
        if res["tx_hashes"]:
            print("Transaction Hashes:")
            for tx_h in res["tx_hashes"]:
                print(f"  - {tx_h}")
        print("=" * 60)
    else:
        print("\nDRY RUN COMPLETE — No blockchain transactions were sent.")
        print("To submit to an EVM network, run with --submit and provide contract credentials.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
