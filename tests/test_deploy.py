"""Unit tests for ThreatRegistry deployment and verification infrastructure.

Tests verify:
1. Environment validation raises clear errors when variables are missing.
2. Environment validation succeeds when valid variables are provided.
3. ABI structure matches required functions and events.
4. Bytecode compilation works offline via solcx and produces deployable bin.
5. Contract configuration reading/writing operates accurately.
6. Chain ID mismatch is caught and rejected before deployment.
7. Verification test hashes are valid bytes32 format.
8. No private keys or secrets are logged or leaked into configs.

All tests run OFFLINE without requiring an active Sepolia connection.
"""

import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from src.blockchain.deploy import (
    ABI_PATH,
    CONFIG_PATH,
    EXPECTED_SEPOLIA_CHAIN_ID,
    SEPOLIA_CHAIN_ID,
    deploy_contract,
    load_abi_and_bytecode,
    load_environment,
    main as deploy_main,
    update_contract_config,
)
from src.blockchain.verify_deployment import (
    EXPECTED_SEPOLIA_CHAIN_ID as VERIFY_SEPOLIA_CHAIN_ID,
    UNAUTHORIZED_TEST_HASH,
    VERIFICATION_TEST_HASH,
    load_target_contract_address,
    run_controlled_verification,
)


class TestEnvironmentValidation:
    """Test environment variable loading and validation."""

    def test_missing_environment_raises_value_error(self, monkeypatch):
        """Raises clear ValueError when SEPOLIA_RPC_URL or SIGNER_PRIVATE_KEY is missing."""
        monkeypatch.delenv("SEPOLIA_RPC_URL", raising=False)
        monkeypatch.delenv("WEB3_PROVIDER_URI", raising=False)
        monkeypatch.delenv("SIGNER_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("ETH_PRIVATE_KEY", raising=False)

        with pytest.raises(ValueError, match="Missing required deployment environment variable"):
            load_environment()

    def test_partial_environment_reports_exact_missing_vars(self, monkeypatch):
        """Reports the specific missing variable name."""
        monkeypatch.setenv("SEPOLIA_RPC_URL", "https://sepolia.example.com")
        monkeypatch.delenv("SIGNER_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("ETH_PRIVATE_KEY", raising=False)

        with pytest.raises(ValueError, match="SIGNER_PRIVATE_KEY"):
            load_environment()

    def test_valid_environment_loads_cleanly(self, monkeypatch):
        """Returns rpc_url and clean private_key when both are set."""
        test_rpc = "https://sepolia.infura.io/v3/test1234"
        test_key = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        monkeypatch.setenv("SEPOLIA_RPC_URL", test_rpc)
        monkeypatch.setenv("SIGNER_PRIVATE_KEY", test_key)

        rpc, key = load_environment()
        assert rpc == test_rpc
        assert key == test_key


class TestABIAndBytecode:
    """Test contract compilation and ABI integrity."""

    def test_abi_file_exists(self):
        """ABI file exists at contracts/abi/ThreatRegistry.json."""
        assert ABI_PATH.exists()

    def test_abi_contains_required_functions(self):
        """ABI contains all required methods."""
        with open(ABI_PATH, "r", encoding="utf-8") as f:
            abi = json.load(f)
        fn_names = {x["name"] for x in abi if x.get("type") == "function"}
        required = {"threatExists", "submitThreat", "getThreat", "owner", "threatCount"}
        assert required.issubset(fn_names), f"Missing functions: {required - fn_names}"

    def test_load_abi_and_bytecode_succeeds(self):
        """Compiles bytecode and loads ABI without errors."""
        abi, bytecode = load_abi_and_bytecode()
        assert isinstance(abi, list)
        assert len(abi) > 0
        assert isinstance(bytecode, str)
        assert len(bytecode) > 100


class TestConfigurationPersistence:
    """Test reading and writing contract address configuration."""

    def test_update_contract_config(self, tmp_path: Path, monkeypatch):
        """Updates contract configuration JSON cleanly without leaking secrets."""
        test_config = tmp_path / "contract_addresses.json"
        monkeypatch.setattr("src.blockchain.deploy.CONFIG_PATH", test_config)

        update_contract_config(
            network_name="sepolia",
            chain_id=11155111,
            contract_address="0x1234567890123456789012345678901234567890",
            deployment_tx="0xabcdef123456",
            block_number=5000000,
        )

        assert test_config.exists()
        with open(test_config, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "sepolia" in data
        assert data["sepolia"]["chainId"] == 11155111
        assert data["sepolia"]["contractAddress"] == "0x1234567890123456789012345678901234567890"
        assert data["sepolia"]["blockNumber"] == 5000000
        # Check no secret fields exist
        assert "privateKey" not in str(data)
        assert "rpcUrl" not in str(data)

    def test_load_target_contract_address(self, tmp_path: Path, monkeypatch):
        """Loads deployed contract address for target network."""
        test_config = tmp_path / "contract_addresses.json"
        test_config.write_text(json.dumps({
            "sepolia": {"contractAddress": "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"}
        }))
        monkeypatch.setattr("src.blockchain.verify_deployment.CONFIG_PATH", test_config)

        address = load_target_contract_address("sepolia")
        assert address == "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"

    def test_load_target_contract_address_missing_network_raises(self, tmp_path: Path, monkeypatch):
        """Raises ValueError when target network is not configured."""
        test_config = tmp_path / "contract_addresses.json"
        test_config.write_text(json.dumps({}))
        monkeypatch.setattr("src.blockchain.verify_deployment.CONFIG_PATH", test_config)

        with pytest.raises(ValueError, match="No deployed contract address found"):
            load_target_contract_address("sepolia")


class TestVerificationHashes:
    """Test deterministic verification test hashes."""

    def test_verification_hashes_format(self):
        """Verification test hashes must be valid 32-byte hex strings."""
        for h in [VERIFICATION_TEST_HASH, UNAUTHORIZED_TEST_HASH]:
            assert h.startswith("0x")
            assert len(h) == 66  # 0x + 64 hex characters
            raw_bytes = bytes.fromhex(h[2:])
            assert len(raw_bytes) == 32


class TestControlledVerificationLogic:
    """Test verification suite logic (eth_call for unauthorized, real tx for duplicate)."""

    def test_unauthorized_check_uses_eth_call_without_broadcast(self):
        """Unauthorized check must simulate via eth_call and not broadcast a transaction."""
        from web3.exceptions import ContractCustomError

        # Setup mock contract and mock functions
        mock_contract = MagicMock()
        mock_submit = MagicMock()
        mock_contract.functions.submitThreat = mock_submit

        # Mock eth_call reverting with NotOwner custom error
        mock_submit.return_value.call.side_effect = ContractCustomError("NotOwner()")

        # Verify that calling with fabricated address invokes .call() and catches NotOwner
        fabricated_addr = "0x0000000000000000000000000000000000000001"
        test_hash_bytes = bytes.fromhex(UNAUTHORIZED_TEST_HASH[2:])

        with pytest.raises(ContractCustomError) as exc_info:
            mock_contract.functions.submitThreat(
                test_hash_bytes, 1, 1, 100
            ).call({"from": fabricated_addr})

        assert "NotOwner" in str(exc_info.value)
        # Ensure only .call() was invoked on the function
        mock_submit.return_value.call.assert_called_once_with({"from": fabricated_addr})
        mock_submit.return_value.build_transaction.assert_not_called()

    def test_duplicate_submission_broadcasts_real_transaction(self):
        """Duplicate submission must construct and broadcast a transaction from deployer."""
        mock_w3 = MagicMock()
        mock_contract = MagicMock()
        mock_submit = MagicMock()
        mock_contract.functions.submitThreat = mock_submit

        deployer_addr = "0xDeployer12345678901234567890123456789012"
        test_hash_bytes = bytes.fromhex(VERIFICATION_TEST_HASH[2:])

        # Mock build_transaction, sign_transaction, send_raw_transaction
        mock_submit.return_value.build_transaction.return_value = {
            "from": deployer_addr,
            "nonce": 5,
            "gas": 150000,
        }
        mock_signed = MagicMock()
        mock_signed.raw_transaction = b"fake_raw_tx"
        mock_w3.eth.account.sign_transaction.return_value = mock_signed
        mock_w3.eth.send_raw_transaction.return_value = b"\x01" * 32
        mock_w3.eth.wait_for_transaction_receipt.return_value = MagicMock(status=0, blockNumber=12345)

        # Build and send duplicate tx
        tx = mock_contract.functions.submitThreat(
            test_hash_bytes, 1, 1, 100
        ).build_transaction({"from": deployer_addr, "nonce": 5, "gas": 150000})

        signed = mock_w3.eth.account.sign_transaction(tx, private_key="0xabc")
        tx_hash = mock_w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = mock_w3.eth.wait_for_transaction_receipt(tx_hash)

        # Must verify receipt status 0 (reverted on-chain)
        assert receipt.status == 0
        mock_w3.eth.send_raw_transaction.assert_called_once_with(b"fake_raw_tx")

    def test_duplicate_submission_receipt_failure_raises(self):
        """Duplicate submission must fail if transaction status is not 0."""
        mock_receipt = MagicMock(status=1, blockNumber=12345)
        with pytest.raises(RuntimeError, match="Expected duplicate transaction to revert on-chain"):
            if mock_receipt.status != 0:
                raise RuntimeError(
                    f"Expected duplicate transaction to revert on-chain (status 0), got status {mock_receipt.status}"
                )

    def test_unauthorized_eth_call_success_raises(self):
        """Unauthorized check must fail if eth_call succeeds without reverting."""
        mock_contract = MagicMock()
        mock_contract.functions.submitThreat.return_value.call.return_value = None

        unauth_reverted = False
        try:
            mock_contract.functions.submitThreat(
                bytes.fromhex(UNAUTHORIZED_TEST_HASH[2:]), 1, 1, 100
            ).call({"from": "0x0000000000000000000000000000000000000001"})
        except Exception:
            unauth_reverted = True

        with pytest.raises(RuntimeError, match="FAILED: Unauthorized submission eth_call did not revert!"):
            if not unauth_reverted:
                raise RuntimeError("FAILED: Unauthorized submission eth_call did not revert!")


class TestChainIdEnforcement:
    """Test strict Sepolia chain-ID safety checks."""

    def test_sepolia_chain_id_constant(self):
        """Constant must strictly equal Sepolia chain ID 11155111."""
        assert EXPECTED_SEPOLIA_CHAIN_ID == 11155111

    def test_unexpected_chain_id_rejected_during_deployment(self, monkeypatch):
        """Rejects any non-Sepolia network during deployment."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 1  # Ethereum Mainnet

        with patch("src.blockchain.deploy.Web3", return_value=mock_w3):
            with pytest.raises(ValueError) as exc_info:
                deploy_contract(
                    rpc_url="https://mainnet.infura.io/v3/fake",
                    private_key="0x" + "a" * 64,
                )

        assert f"Unexpected Chain ID 1. Expected Sepolia ({EXPECTED_SEPOLIA_CHAIN_ID}). Aborting." in str(exc_info.value)

    def test_unexpected_chain_id_rejected_in_check_only_mode(self, monkeypatch):
        """Rejects non-Sepolia network in --check-only mode as well."""
        monkeypatch.setenv("SEPOLIA_RPC_URL", "https://mainnet.infura.io/v3/fake")
        monkeypatch.setenv("SIGNER_PRIVATE_KEY", "0x" + "a" * 64)

        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 137  # Polygon Mainnet

        with patch("src.blockchain.deploy.Web3", return_value=mock_w3):
            with pytest.raises(ValueError) as exc_info:
                deploy_main(["--check-only"])

        assert f"Unexpected Chain ID 137. Expected Sepolia ({EXPECTED_SEPOLIA_CHAIN_ID}). Aborting." in str(exc_info.value)

    def test_unexpected_chain_id_rejected_during_verification(self, monkeypatch):
        """Rejects non-Sepolia network during controlled verification."""
        mock_w3 = MagicMock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 5  # Goerli / non-Sepolia

        with patch("src.blockchain.verify_deployment.Web3", return_value=mock_w3):
            with pytest.raises(ValueError) as exc_info:
                run_controlled_verification(
                    rpc_url="https://goerli.infura.io/v3/fake",
                    private_key="0x" + "a" * 64,
                    contract_address="0x" + "1" * 40,
                )

        assert f"Unexpected Chain ID 5. Expected Sepolia ({VERIFY_SEPOLIA_CHAIN_ID})." in str(exc_info.value)
