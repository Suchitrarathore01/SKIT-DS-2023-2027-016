"""Unit tests for the threat registry seeding pipeline.

Tests verify:
1. Threat records are selected correctly.
2. Benign records are excluded.
3. Message hashing calls the existing message hash function.
4. URL hashing calls the existing URL hash function.
5. Hash-based deduplication works.
6. Canonicalization-equivalent records produce one seed.
7. Missing values are handled safely.
8. Invalid labels are rejected rather than silently interpreted.
9. Every seed has verdict = 1 and confidence = 100.
10. Dry-run mode performs ZERO blockchain writes.
11. No raw message/URL is included in the generated seed payload.
12. Output hashes are valid bytes32 values.
"""

import csv
import json
import re
from pathlib import Path
import pytest

from src.blockchain.canonicalize import canonicalize_message, canonicalize_url
from src.blockchain.hashing import generate_message_hash, generate_url_hash
from src.blockchain.seed_registry import (
    SeedingStatistics,
    ThreatSeedRecord,
    ThreatTypeEnum,
    detect_columns,
    export_seed_json,
    is_threat_label,
    main,
    process_dataset,
)

_BYTES32_PATTERN = re.compile(r"^0x[0-9a-f]{64}$")


@pytest.fixture
def sample_url_csv(tmp_path: Path) -> Path:
    """Create a temporary CSV file with URL data."""
    csv_path = tmp_path / "urls.csv"
    rows = [
        ["URL", "label"],
        # Threats (label 0 in PhiUSIIL)
        ["https://evil-phish.com/login", "0"],
        ["http://phish-clone.xyz/claim", "0"],
        # Equivalent URL (different casing/port/slashes) -> canonical duplicate
        ["HTTPS://EVIL-PHISH.COM:443/login", "0"],
        # Exact duplicate
        ["http://phish-clone.xyz/claim", "0"],
        # Benign (label 1)
        ["https://google.com/", "1"],
        ["https://wikipedia.org/wiki/Main_Page", "1"],
        # Invalid / missing rows
        ["", "0"],
        ["https://missing-label.org", ""],
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return csv_path


@pytest.fixture
def sample_message_csv(tmp_path: Path) -> Path:
    """Create a temporary CSV file with SMS message data."""
    csv_path = tmp_path / "messages.csv"
    rows = [
        ["message", "label"],
        # Threats (spam/smishing)
        ["Your account is blocked! Call 1800-NOW", "spam"],
        ["URGENT: Click http://claim.me to collect prize", "smishing"],
        # Canonicalization equivalent: differing only in casing and whitespace
        ["your   account is  blocked! call 1800-now", "spam"],
        # Benign (ham)
        ["Hey, what time are we meeting tonight?", "ham"],
        ["Ok sounds good, see you later", "ham"],
        # Missing values
        ["", "spam"],
        ["No label message", ""],
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return csv_path


# ══════════════════════════════════════════════════════════════════════
#  1. Column Detection & Label Logic
# ══════════════════════════════════════════════════════════════════════

class TestDetectionAndLabels:
    """Test header column detection and threat label classification."""

    def test_detect_columns_url(self):
        """Auto-detects URL and label columns."""
        header = ["URL", "Domain", "label"]
        content_col, label_col, t_type = detect_columns(header)
        assert content_col == "URL"
        assert label_col == "label"
        assert t_type == ThreatTypeEnum.URL

    def test_detect_columns_message(self):
        """Auto-detects message text and label columns."""
        header = ["id", "text", "category"]
        content_col, label_col, t_type = detect_columns(header)
        assert content_col == "text"
        assert label_col == "category"
        assert t_type == ThreatTypeEnum.MESSAGE

    def test_detect_columns_missing_raises(self):
        """Raises ValueError if neither URL nor message columns are present."""
        with pytest.raises(ValueError, match="Could not automatically detect"):
            detect_columns(["col_a", "col_b"])

    def test_is_threat_label_url_convention(self):
        """PhiUSIIL convention: 0 is threat, 1 is benign."""
        assert is_threat_label("0", ThreatTypeEnum.URL) is True
        assert is_threat_label("phishing", ThreatTypeEnum.URL) is True
        assert is_threat_label("1", ThreatTypeEnum.URL) is False
        assert is_threat_label("legitimate", ThreatTypeEnum.URL) is False

    def test_is_threat_label_message_convention(self):
        """SMS convention: spam/malicious/1 is threat, ham/0 is benign."""
        assert is_threat_label("spam", ThreatTypeEnum.MESSAGE) is True
        assert is_threat_label("smishing", ThreatTypeEnum.MESSAGE) is True
        assert is_threat_label("1", ThreatTypeEnum.MESSAGE) is True
        assert is_threat_label("ham", ThreatTypeEnum.MESSAGE) is False
        assert is_threat_label("benign", ThreatTypeEnum.MESSAGE) is False

    def test_ambiguous_label_raises(self):
        """Ambiguous/unknown labels raise ValueError."""
        with pytest.raises(ValueError, match="Ambiguous"):
            is_threat_label("unknown_class", ThreatTypeEnum.URL)


# ══════════════════════════════════════════════════════════════════════
#  2. URL Dataset Processing
# ══════════════════════════════════════════════════════════════════════

class TestUrlProcessing:
    """Test URL dataset filtering, canonicalization, and deduplication."""

    def test_threat_records_selected_correctly(self, sample_url_csv: Path):
        """Threat records are selected; benign records are skipped."""
        records, stats = process_dataset(sample_url_csv)
        assert stats.threat_records == 4
        assert stats.benign_records == 2

    def test_benign_records_excluded(self, sample_url_csv: Path):
        """No benign URL is included in the unique threat hashes."""
        records, _ = process_dataset(sample_url_csv)
        google_hash = generate_url_hash("https://google.com/")
        seeded_hashes = {r.threatHash for r in records}
        assert google_hash not in seeded_hashes

    def test_hash_based_deduplication_and_canonical_equivalence(self, sample_url_csv: Path):
        """Canonicalization-equivalent URLs produce exactly one seed hash."""
        records, stats = process_dataset(sample_url_csv)
        # Expected unique threats:
        # 1. evil-phish.com/login (matches both HTTP and HTTPS variants after canonicalization)
        # 2. phish-clone.xyz/claim
        assert stats.unique_threat_hashes == 2
        assert len(records) == 2
        assert stats.canonical_duplicate_records >= 1

    def test_url_hashing_matches_existing_pipeline(self, sample_url_csv: Path):
        """Hashes match the exact generate_url_hash function output."""
        records, _ = process_dataset(sample_url_csv)
        expected_hash = generate_url_hash("https://evil-phish.com/login")
        seeded_hashes = {r.threatHash for r in records}
        assert expected_hash in seeded_hashes

    def test_missing_values_handled_safely(self, sample_url_csv: Path):
        """Rows with missing URLs or labels are skipped safely."""
        _, stats = process_dataset(sample_url_csv)
        assert stats.invalid_records == 2


# ══════════════════════════════════════════════════════════════════════
#  3. Message Dataset Processing
# ══════════════════════════════════════════════════════════════════════

class TestMessageProcessing:
    """Test message dataset filtering, canonicalization, and deduplication."""

    def test_message_threat_selection(self, sample_message_csv: Path):
        """Threat messages are selected; ham messages are skipped."""
        records, stats = process_dataset(sample_message_csv)
        assert stats.threat_records == 3
        assert stats.benign_records == 2

    def test_message_canonical_deduplication(self, sample_message_csv: Path):
        """Messages differing only by casing/whitespace are deduplicated."""
        records, stats = process_dataset(sample_message_csv)
        # 1. "Your account is blocked! Call 1800-NOW" (and lowercase variant)
        # 2. "URGENT: Click http://claim.me to collect prize"
        assert stats.unique_threat_hashes == 2
        assert len(records) == 2
        assert stats.canonical_duplicate_records == 1

    def test_message_hashing_matches_existing_pipeline(self, sample_message_csv: Path):
        """Hashes match the exact generate_message_hash function output."""
        records, _ = process_dataset(sample_message_csv)
        expected_hash = generate_message_hash("Your account is blocked! Call 1800-NOW")
        seeded_hashes = {r.threatHash for r in records}
        assert expected_hash in seeded_hashes


# ══════════════════════════════════════════════════════════════════════
#  4. Payload & Privacy Integrity
# ══════════════════════════════════════════════════════════════════════

class TestPayloadAndPrivacy:
    """Verify that seeds contain only bytes32 and minimal metadata."""

    def test_every_seed_has_verdict_1_and_confidence_100(self, sample_url_csv: Path):
        """Every generated seed must have verdict=1 and confidence=100."""
        records, _ = process_dataset(sample_url_csv)
        for r in records:
            assert r.verdict == 1, f"Expected verdict 1, got {r.verdict}"
            assert r.confidence == 100, f"Expected confidence 100, got {r.confidence}"

    def test_hashes_are_valid_bytes32(self, sample_url_csv: Path):
        """Output hashes are 0x-prefixed 64 hex character strings."""
        records, _ = process_dataset(sample_url_csv)
        for r in records:
            assert _BYTES32_PATTERN.match(r.threatHash), \
                f"Invalid bytes32 hash: {r.threatHash}"

    def test_zero_raw_content_in_export_payload(self, sample_url_csv: Path, tmp_path: Path):
        """Exported JSON seed payload must NEVER contain raw URLs or messages."""
        records, _ = process_dataset(sample_url_csv)
        out_json = tmp_path / "seeds.json"
        export_seed_json(records, out_json)

        content = out_json.read_text(encoding="utf-8")
        # Ensure raw URL strings are not anywhere in the JSON
        assert "evil-phish.com" not in content
        assert "phish-clone.xyz" not in content

        # Ensure JSON parses and only has clean keys
        data = json.loads(content)
        for item in data:
            assert set(item.keys()) == {"threatHash", "threatType", "threatTypeInt", "verdict", "confidence"}
            assert _BYTES32_PATTERN.match(item["threatHash"])


# ══════════════════════════════════════════════════════════════════════
#  5. Dry-Run & CLI Safety
# ══════════════════════════════════════════════════════════════

class TestDryRunSafety:
    """Verify dry-run mode and CLI safety."""

    def test_dry_run_cli_execution(self, sample_url_csv: Path, capsys):
        """Running CLI in dry-run mode prints report and sends zero transactions."""
        exit_code = main(["--dataset-path", str(sample_url_csv), "--dry-run"])
        assert exit_code == 0
        captured = capsys.readouterr().out
        assert "DRY RUN COMPLETE — No blockchain transactions were sent." in captured
        assert "Unique threat hashes:        2" in captured
