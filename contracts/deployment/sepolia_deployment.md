# Sepolia Testnet Deployment Documentation

## Network Details
- **Network Name**: Sepolia Testnet
- **Chain ID**: `11155111`
- **Currency Symbol**: `ETH` (SepoliaETH)
- **Block Explorer**: [Sepolia Etherscan](https://sepolia.etherscan.io)

## Acquiring Testnet ETH
- Google Cloud Web3 Sepolia Faucet
- Alchemy Sepolia Faucet
- Infura Sepolia Faucet
- PoW Sepolia Faucet

## Deployment Verification
1. Verify the deployed contract address on [Sepolia Etherscan](https://sepolia.etherscan.io).
2. Validate read functions (`threatExists(bytes32)`).
3. Ensure the address is recorded in `contracts/configs/contract_addresses.json`.
