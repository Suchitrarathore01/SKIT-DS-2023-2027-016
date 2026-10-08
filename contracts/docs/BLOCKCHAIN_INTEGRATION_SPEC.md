# ChainShield Blockchain Integration Specification

This specification defines the contract interface, deterministic canonicalization pipeline, and Keccak-256 threat hashing protocol for the ChainShield threat registry.

## Architecture Overview
The blockchain serves exclusively as an immutable, tamper-evident registry of known threat hashes.
- **Off-chain NLP**: Deterministic canonicalization runs entirely off-chain (NLTK in Python / standard equivalent in Chrome Extension / backend).
- **On-chain Pure Registry**: Solidity strictly receives precomputed `bytes32` hashes and verifies existence via `threatExists(bytes32)`.
- **Non-goals**: No reputation, voting, confirmation, dispute, community scoring, or ML inference on-chain.

## Threat Hash Generation Rules
To ensure strict cross-environment consistency:
1. **Preserve Token Order**: Token sequence is strictly maintained.
2. **Preserve All Tokens**: Stopwords are NOT removed.
3. **No Bag-of-Words**: Frequencies/sets are not used.
4. **No Token Sorting**: Tokens must remain in their original order.
5. **Single Keccak-256 Hash**: Exactly one Keccak-256 hash across the full canonical token representation.
6. **Deterministic Hash**: e.g., `"your account is blocked"` and `"your account is blocked is"` yield distinct hashes.
