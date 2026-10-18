# Remix IDE Deployment Guide

This guide details how to compile and deploy the `ThreatRegistry` smart contract to the Sepolia testnet using the Remix IDE.

## Prerequisites
- Web browser with access to [Remix IDE](https://remix.ethereum.org)
- MetaMask browser extension installed and configured
- Sepolia testnet ETH in the deployer wallet (via a Sepolia faucet)

## Deployment Steps
1. **Load Contract**: Import `contracts/ThreatRegistry.sol` into Remix IDE.
2. **Compile**: Under the Solidity Compiler tab, select compiler version `0.8.20` or higher and compile `ThreatRegistry.sol`.
3. **Environment**: Under the Deploy & Run Transactions tab, select **Injected Provider - MetaMask**.
4. **Network**: Ensure MetaMask is connected to the **Sepolia** network (Chain ID: 11155111).
5. **Deploy**: Click **Deploy** and confirm the transaction in MetaMask.
6. **Record Deployment**: Copy the deployed contract address and transaction hash into `contracts/configs/contract_addresses.json`.
7. **Export ABI**: Export the contract ABI and save to `contracts/abi/ThreatRegistry.json`.
