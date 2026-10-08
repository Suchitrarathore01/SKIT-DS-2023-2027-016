# ChainShield Blockchain Integration Specification

This specification defines the contract interface, deterministic canonicalization pipeline, and Keccak-256 threat fingerprinting protocol for the ChainShield threat registry.

---

## 1. Architecture Overview & Threat Workflow

The blockchain component in ChainShield functions exclusively as an **immutable, tamper-evident registry of known threat fingerprints**.

```text
Chrome Extension
      ↓
Incoming message / URL
      ↓
Deterministic Canonicalization (OFF-CHAIN)
      ↓
Domain Separator Prefix ('message:' / 'url:')
      ↓
UTF-8 Byte Encoding
      ↓
Keccak-256 Hash (OFF-CHAIN)
      ↓
bytes32 threat hash (0x-prefixed 64 hex characters)
      ↓
Blockchain threatExists(hash)
      ↓
 ┌───────────────┴───────────────┐
 │                               │
 EXISTS                         NOT EXISTS
 │                               │
 ▼                               ▼
Known Threat (Fast Path)        ML Pipeline (Slow Path)
                                  ↓
                             ML classification
                                  ↓
                             If confirmed threat → submitThreat(hash)
```

### Why Canonicalization & Hashing Happen Off-Chain
- **Gas & Compute Constraints**: NLP tokenization, Unicode normalization, regular expression parsing, and string manipulation in Solidity on Ethereum/EVM are prohibitively expensive and impractical in terms of gas execution.
- **Privacy & Data Minimization**: Raw messages, user text, and URLs can contain PII (Personally Identifiable Information), private account IDs, or sensitive communication. Storing or processing raw text on a public ledger violates privacy. The blockchain must **never** receive raw text, URLs, NLP tokens, or PII.
- **Pure Cryptographic Registry**: The Solidity smart contract only receives and stores fixed 32-byte Keccak-256 hashes (`bytes32`). Solidity does NOT execute NLTK, NLP, or tokenization.

### Division of Responsibility: Blockchain vs. Machine Learning
- **The Blockchain Registry**: Performs **EXACT fingerprint matching** for known, confirmed threats. It operates in $O(1)$ lookup time as a fast path.
- **The Machine Learning Pipeline**: Handles **semantic similarity, novel threats, paraphrasing, and unseen variants**.
- **Intentional Non-Goals for the Blockchain**:
  - The blockchain does NOT perform semantic normalization or fuzzy matching.
  - The blockchain does NOT implement user reputation, voting, confirmation staking, dispute resolution, or community verification.
  - Semantically similar threats that have not yet been registered are routed to the ML pipeline. If the ML model classifies an unknown message/URL as a confirmed threat, its canonical Keccak-256 hash is subsequently registered on-chain for instantaneous future recognition.

---

## 2. Cross-Environment Consistency Requirement

The exact same canonicalization and hashing logic must be implemented across all interacting layers:
1. **Initial Dataset Seeding**: Hashing historical datasets (`PhiUSIIL_Phishing_URL_Dataset.csv`, `cleaned_url.csv`, SMS corpora) to populate the registry.
2. **Chrome Extension Lookup**: Pre-processing user-encountered URLs or message clips in the browser before querying `threatExists(hash)`.
3. **Backend Lookup**: Pre-processing incoming scan requests before querying the blockchain node or local cache.
4. **Future Threat Submission**: Generating the canonical hash for newly identified threats flagged by the ML pipeline.

If any environment deviates in tokenization, punctuation handling, casing, parameter ordering, or hashing prefixes, hash verification will fail.

---

## 3. Message Canonicalization Rules

Message canonicalization converts free-form text into a strictly deterministic, normalized token sequence using NLTK:

### Algorithm Steps (`canonicalize_message`)
1. **Input Validation**: Null or empty strings return an empty string `""`.
2. **Unicode Normalization (NFKC)**: Normalize all characters using Unicode Normalization Form KC (Compatibility Decomposition followed by Canonical Composition). Standardizes compatibility glyphs, fullwidth characters, ligatures, and combining marks.
3. **Typographic Quote Normalization**: Standardize mobile/OS smart quotes to ASCII:
   - `’` (U+2019), `‘` (U+2018), `‚` (U+201A), `` ` `` (U+0060), `´` (U+00B4) $\rightarrow$ `'` (U+0027)
   - `“` (U+201C), `”` (U+201D), `„` (U+201E) $\rightarrow$ `"` (U+0022)
4. **Case Normalization**: Convert all characters to lowercase (`text.lower()`).
5. **NLTK Tokenization**: Tokenize deterministically using `nltk.tokenize.WordPunctTokenizer()`.
   - `WordPunctTokenizer` matches alphanumeric sequences `\w+` and punctuation sequences `[^\w\s]+`.
   - Does NOT rely on downloadable external corpus files (unlike `punkt`), ensuring 100% offline reproducibility across environments.
6. **Token Preservation Rules**:
   - **Preserve EVERY token**: No words, tokens, or numbers are discarded.
   - **Preserve token ORDER**: Tokens must remain in their original sequence.
   - **Preserve repeated tokens**: Repeated words (e.g. `"free free free"`) are retained in full.
   - **Preserve numbers and financial figures**: Digits, phone numbers, and currency values are preserved verbatim.
   - **Stopwords are strictly PRESERVED**: Words such as `is`, `the`, `at`, `your`, `to`, `now` must NEVER be removed.
   - **NO token sorting**: Tokens must NEVER be alphabetically sorted.
   - **NO bag-of-words**: Word frequencies or unordered sets are strictly forbidden.
   - **NO stemming or lemmatization**: Stems (e.g. Porter/Snowball) or lemmas (WordNet) mutate tokens and induce false-positive hash collisions.
7. **Canonical Delimitation**: Join all extracted tokens with a single ASCII space: `" ".join(tokens)`.

### Why Stopword Removal is Forbidden
Removing stopwords (e.g. removing `is`, `your`) would collapse fundamentally different phrases into the same fingerprint:
- `"your account is blocked"` would collapse to `"account blocked"`.
- `"your account blocked"` would also collapse to `"account blocked"`.
- `"your account is blocked is"` would collapse to `"account blocked"`.
Because the blockchain is an exact threat registry, distinct messages must retain distinct fingerprints. Stopword removal creates unacceptable collision risk.

### Why Token Sorting is Forbidden
Sorting tokens would convert phrases into unordered bags of words:
- `"your account is blocked"` would become `"account blocked is your"`.
- `"blocked is your account"` would also become `"account blocked is your"`.
Phishing attackers routinely craft sentences where word order changes semantic meaning or targets specific social engineering triggers. Word order must be preserved.

---

## 4. Explicit Punctuation Policy

Punctuation carries vital structural information in phishing messages (e.g. delimiters, urgency indicators, URLs, currency symbols).
- **Rule**: Every punctuation character or punctuation sequence recognized by NLTK's `WordPunctTokenizer` (e.g., `!`, `?`, `:`, `://`, `$`, `#`, `@`, `,`, `-`) is preserved as a distinct token and separated by spaces in the canonical output.
- **No Silent Stripping**: Punctuation is NEVER stripped, discarded, or ignored.
- **Distinct Collisions Avoided**:
  - `"urgent: action required"` $\rightarrow$ `urgent : action required`
  - `"urgent action required"` $\rightarrow$ `urgent action required` (distinct!)
  - `"account blocked!"` $\rightarrow$ `account blocked !`
  - `"account blocked?"` $\rightarrow$ `account blocked ?` (distinct!)

---

## 5. URL Canonicalization Rules

URLs follow RFC 3986 standards and must **NOT** use NLTK message tokenization.

### Algorithm Steps (`canonicalize_url`)
1. **Whitespace & Unicode**: Strip leading/trailing whitespace and apply Unicode NFKC normalization.
2. **Scheme Normalization**:
   - Lowercase the scheme (`HTTPS://` $\rightarrow$ `https://`, `HTTP://` $\rightarrow$ `http://`).
   - If no scheme is provided (e.g. `example.com/login`), default to `http://`.
   - Protocol-relative URLs (e.g. `//example.com`) preserve leading `//`.
3. **Hostname & Port Normalization**:
   - Hostname is lowercased (`MYBANK.COM` $\rightarrow$ `mybank.com`).
   - Trailing DNS root dots are stripped (`example.com.` $\rightarrow$ `example.com`).
   - Default ports are removed: `:80` for `http`, `:443` for `https`, `:21` for `ftp`.
   - Non-default ports are preserved (`:8080`, `:8443`).
   - User credentials (`user:pass@`) in netloc are preserved; only hostname is lowercased.
4. **Path Normalization**:
   - Dot segments (`.` and `..`) are resolved per RFC 3986 section 5.2.4.
   - Root empty path normalizes to `/` (`http://example.com` $\rightarrow$ `http://example.com/`).
   - Trailing slash is **PRESERVED** on non-empty paths (`/login` and `/login/` remain distinct endpoints).
   - Percent-encoding normalization: Unreserved characters (`[A-Za-z0-9_.~-]`) are unquoted (`%7E` $\rightarrow$ `~`). Reserved characters retain uppercase hex digits (`%2f` $\rightarrow$ `%2F`).
   - Unencoded illegal characters (spaces, brackets) are percent-encoded safely.
5. **Query Parameter Normalization**:
   - Query string is parsed into key-value pairs (`parse_qsl`), preserving blank values.
   - Pairs are sorted deterministically: first by key ascending, then by value ascending.
   - Duplicate parameter keys are retained in sorted order.
   - Empty queries omit the `?` delimiter.
6. **Fragment Policy**:
   - Modern Web3 phishing and single-page applications often route exploits through fragments (e.g. `#/claim`, `#/drainer`).
   - Non-empty fragments are normalized and preserved (`#...`).
   - Empty fragments or trailing `#` are stripped.

---

## 6. Examples of Inputs and Canonical Outputs

### Message Canonicalization Examples

| Raw Input Message | Canonicalized Message Output (`canonicalize_message`) |
| :--- | :--- |
| `"Your Account Is Blocked"` | `your account is blocked` |
| `"your   account   is   blocked"` | `your account is blocked` |
| `"your account is blocked is"` | `your account is blocked is` *(distinct!)* |
| `"your account blocked"` | `your account blocked` *(distinct!)* |
| `"your account is blocked now"` | `your account is blocked now` *(distinct!)* |
| `"don’t click this link"` | `don ' t click this link` |
| `"win win win $500 now!"` | `win win win $ 500 now !` |
| `"URGENT: Call 1800-555-0199"` | `urgent : call 1800 - 555 - 0199` |
| `"Click https://bank.com/login immediately!"` | `click https :// bank . com / login immediately !` |

### URL Canonicalization Examples

| Raw Input URL | Canonicalized URL Output (`canonicalize_url`) |
| :--- | :--- |
| `"HTTP://EXAMPLE.COM"` | `http://example.com/` |
| `"http://example.com:80/"` | `http://example.com/` |
| `"https://example.com:443/login"` | `https://example.com/login` |
| `"https://example.com/login/"` | `https://example.com/login/` *(trailing slash preserved!)* |
| `"https://example.com/a/b/../c"` | `https://example.com/a/c` |
| `"https://example.com/search?b=2&a=1"` | `https://example.com/search?a=1&b=2` |
| `"https://example.com/api?tag=b&tag=a"` | `https://example.com/api?tag=a&tag=b` |
| `"http://example.com/%7Ealice/%61bc"` | `http://example.com/~alice/abc` |
| `"https://dapp.io:443/app#/claim?u=1"` | `https://dapp.io/app#/claim?u=1` |
| `"example.com/verify"` | `http://example.com/verify` |

---

## 7. Deterministic Keccak-256 Threat Hashing

Threat hashing transforms canonical strings into fixed 32-byte Ethereum digests (`bytes32`).

### 1. The Hashing Pipeline
1. **Canonicalize**: Run `canonicalize_message()` or `canonicalize_url()` first.
2. **Domain Separation**: Prepend domain prefix:
   - For messages: `"message:" + canonical_message`
   - For URLs: `"url:" + canonical_url`
3. **UTF-8 Encoding**: Convert the prefixed string to a UTF-8 byte array (`.encode("utf-8")`).
4. **Ethereum Keccak-256**: Hash the complete byte array as a single contiguous sequence using Ethereum-compatible Keccak-256.
5. **Hex Representation**: Format as lowercase `0x` + 64 hexadecimal characters.

```python
# Exact Python implementation reference
from Crypto.Hash import keccak

def generate_message_hash(message: str) -> str:
    canonical = canonicalize_message(message)
    if not canonical:
        raise ValueError("Canonicalized message is empty and cannot be hashed.")
    payload = f"message:{canonical}".encode("utf-8")
    k = keccak.new(digest_bits=256)
    k.update(payload)
    return "0x" + k.hexdigest()

def generate_url_hash(url: str) -> str:
    canonical = canonicalize_url(url)
    if not canonical:
        raise ValueError("Canonicalized URL is empty and cannot be hashed.")
    payload = f"url:{canonical}".encode("utf-8")
    k = keccak.new(digest_bits=256)
    k.update(payload)
    return "0x" + k.hexdigest()
```

### 2. Ethereum Keccak-256 vs. NIST SHA3-256
Standard Python `hashlib.sha3_256()` implements NIST FIPS 202 SHA-3 (using domain padding `0x06`). **This is incompatible with Ethereum.**
Ethereum pre-dates the NIST standard and uses the original Keccak specification (with padding `0x01`), implemented in Solidity's native `keccak256()` opcode.
ChainShield uses `pycryptodome` (`Crypto.Hash.keccak` with `digest_bits=256`), which implements the exact Ethereum Keccak-256 algorithm.

#### Known Test Vectors
- **Empty Byte String `b""`**:
  - Ethereum Keccak-256: `0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470`
  - (Contrast with NIST SHA3-256: `0xa7ffc6f8...` — do NOT use!)
- **`b"hello"`**:
  - Ethereum Keccak-256: `0x1c8aff950685c2ed4bc3174f3472287b56d9517b9c948127319a09a7a36deac8`

### 3. Solidity `bytes32` Compatibility
All hashes generated by `generate_message_hash` and `generate_url_hash` are formatted as:
`0x` followed by exactly 64 lowercase hexadecimal characters (total length 66 characters).
This maps 1:1 to Solidity's `bytes32` type in EVM transactions and memory:
```solidity
function threatExists(bytes32 threatHash) external view returns (bool);
```

### 4. Empty and Invalid Input Policy
- If an input message or URL is `None`, empty `""`, or contains only whitespace, the API **raises a `ValueError`**.
- It does **NOT** silently hash an empty string into `0xc5d24601...`.
- This fail-fast policy protects against registering misleading empty fingerprints in the smart contract registry.

### 5. Domain Separation Rationale
Explicit prefixes (`"message:"` and `"url:"`) guarantee domain separation:
- Even if a canonical message string and a canonical URL string are identical (e.g. `https://example.com/`), their resulting Keccak-256 hashes will **never** collide.
- The scheme is straightforward to reproduce across languages:
  - **Python**: `keccak.new(digest_bits=256).update(f"url:{url}".encode("utf-8")).hexdigest()`
  - **JavaScript/TypeScript**: `ethers.keccak256(ethers.toUtf8Bytes("url:" + canonicalUrl))`
  - **Solidity**: `keccak256(abi.encodePacked("url:", canonicalUrl))`

### 6. Representative Threat Hash Examples

| Type | Input | Canonical Output | Generated Keccak-256 `bytes32` Hash |
| :--- | :--- | :--- | :--- |
| **Message** | `"Your Account Is Blocked"` | `your account is blocked` | `0x72b23a3e7d22a2d1b739b106232625ab7da41df0aab77c4b2808fd2c3dc02a1f` |
| **Message** | `"your   account   is   blocked"` | `your account is blocked` | `0x72b23a3e7d22a2d1b739b106232625ab7da41df0aab77c4b2808fd2c3dc02a1f` *(Identical)* |
| **Message** | `"your account is blocked is"` | `your account is blocked is` | `0x1e3e7845f95f403be49e913d65b7fc4066bf4cb1f46399066497ecdf32223706` *(Distinct!)* |
| **Message** | `"your account blocked"` | `your account blocked` | `0x1f0be3a6c38ce2452243d4c728e5dbec011d0fc8e1245a1c1d9f8df5b617ff1c` *(Distinct!)* |
| **Message** | `"your account is blocked now"` | `your account is blocked now` | `0x5fdb3eb3ca8593be2a9b3a0c64c23179294e7c7a1c97a55c26b64b19c237c093` *(Distinct!)* |
| **URL** | `"HTTP://EXAMPLE.COM:80"` | `http://example.com/` | `0x3ec488dfef911dbcc0d4daddec0e7acb656282479e308c95702ed699b2138321` |
| **URL** | `"http://example.com/"` | `http://example.com/` | `0x3ec488dfef911dbcc0d4daddec0e7acb656282479e308c95702ed699b2138321` *(Identical)* |
| **URL** | `"https://example.com:443/login?b=2&a=1"` | `https://example.com/login?a=1&b=2` | `0x7c73fa93433d944c6934cbbca689ca6485e94b819fbc746140e06001a4e21a24` |
| **URL** | `"https://example.com/login"` | `https://example.com/login` | `0x44bfbc050e6ebfd7f474cf70b6d34e9e0d1b32d1ef1066c0d829141be3f6da21` |

---

## 8. Solidity Threat Registry Smart Contract (`ThreatRegistry.sol`)

### 1. Architectural Purpose & Exact-Hash Registry Model
The `ThreatRegistry` smart contract functions as a tamper-evident, decentralized key-value registry of known threat fingerprints on Ethereum/EVM networks (e.g. Sepolia testnet).

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   ARCHITECTURAL SEPARATION OF DUTIES                  │
├───────────────────────────────────┬────────────────────────────────────┤
│       BLOCKCHAIN REGISTRY         │        MACHINE LEARNING            │
│   (Immutable Exact-Hash Lookup)   │     (Generalization & Inference)   │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Fast-path exact lookup          │ • Slow-path inference & heuristics │
│ • O(1) deterministic check        │ • Semantic classification          │
│ • Zero false positives for known  │ • Paraphrase / mutation detection  │
│ • No NLP, tokenization, or ML     │ • Analyzes previously unseen data  │
│ • Stores only fixed bytes32 keys  │ • Computes verdict & confidence    │
└───────────────────────────────────┴────────────────────────────────────┘
```

The smart contract acts purely as an on-chain ledger of previously verified threat fingerprints. It never evaluates similarity, never parses natural language, and never alters or inspects message contents.

### 2. Identifier Type: `bytes32`
- Every threat is uniquely keyed by a `bytes32` value (`threatHash`), matching the 256-bit Keccak digest output of the off-chain pipeline (`generate_message_hash` or `generate_url_hash`).
- Domain separation is incorporated off-chain before hashing (`message:...` vs `url:...`), ensuring that the contract handles all identifiers uniformly as opaque 32-byte values.

### 3. Contract State & Storage Layout

```solidity
enum ThreatType {
    MESSAGE, // 0
    URL      // 1
}

struct Threat {
    ThreatType threatType;   // MESSAGE (0) or URL (1)
    uint8      verdict;      // 0 = benign, 1 = threat
    uint16     confidence;   // 0–100 (percentage)
    uint64     submittedAt;  // block.timestamp (UNIX seconds)
    address    submitter;    // msg.sender at submission
}
```

Storage mapping:
```solidity
mapping(bytes32 => Threat) private _threats;
mapping(bytes32 => bool)   private _exists;
uint256                    public  threatCount;
```
- An explicit `_exists` boolean mapping avoids relying on default/zero-value struct members as sentinel existence markers.
- `threatCount` tracks total registrations.

### 4. Public Interface

#### A. Read-Only Existence Query (`threatExists`)
```solidity
function threatExists(bytes32 threatHash) external view returns (bool exists);
```
- Returns `true` if `threatHash` was previously registered; `false` otherwise.
- Gas cost: Single EVM `SLOAD` operation (~2,100 gas un-warmed, ~100 gas warm).
- Does not revert on unregistered hashes.

#### B. Metadata Query (`getThreat`)
```solidity
function getThreat(bytes32 threatHash)
    external
    view
    returns (
        ThreatType threatType,
        uint8      verdict,
        uint16     confidence,
        uint64     submittedAt,
        address    submitter
    );
```
- Returns the complete recorded metadata for a registered hash.
- **Revert Behavior**: Reverts with custom error `ThreatNotFound(bytes32 threatHash)` if `threatExists(threatHash) == false`.

#### C. Threat Submission (`submitThreat`)
```solidity
function submitThreat(
    bytes32    threatHash,
    ThreatType threatType,
    uint8      verdict,
    uint16     confidence
) external;
```
- Callable only by the contract owner (`onlyOwner`).
- Reverts on:
  - `threatHash == bytes32(0)` $\rightarrow$ `ZeroHash()`
  - `_exists[threatHash] == true` $\rightarrow$ `DuplicateHash(threatHash)`
  - `verdict > 1` $\rightarrow$ `InvalidVerdict(verdict)`
  - `confidence > 100` $\rightarrow$ `ConfidenceOutOfRange(confidence)`
  - `msg.sender != owner` $\rightarrow$ `NotOwner()`

#### D. Ownership Management (`transferOwnership` / `owner`)
```solidity
function owner() external view returns (address);
function transferOwnership(address newOwner) external;
```
- Single-step ownership transfer protected against `address(0)` via `ZeroAddress()`.

### 5. Events Emitted
```solidity
event ThreatSubmitted(
    bytes32 indexed threatHash,
    ThreatType      threatType,
    uint8           verdict,
    uint16          confidence,
    uint64          submittedAt,
    address indexed submitter
);

event OwnershipTransferred(
    address indexed previousOwner,
    address indexed newOwner
);
```

### 6. Validation and Revert Semantics
The contract uses custom Solidity errors (`revert CustomError()`) for gas efficiency and clear debugging:
- `ZeroHash`: Rejects `0x0000000000000000000000000000000000000000000000000000000000000000`.
- `DuplicateHash(bytes32)`: Rejects re-registration of existing hashes to maintain idempotency.
- `InvalidVerdict(uint8)`: Rejects values outside binary `0` (benign) or `1` (threat).
- `ConfidenceOutOfRange(uint16)`: Enforces percentage range `0` to `100`.
- `ThreatNotFound(bytes32)`: Rejects metadata queries for unregistered hashes.
- `NotOwner()`: Rejects unauthorized submissions.
- `ZeroAddress()`: Prevents accidental loss of contract ownership.

### 7. Access Control & Permission Model
- **Owner-Only Submissions**: Threat submission is restricted to the contract owner via the `onlyOwner` modifier.
- **Architectural Rationale**: On a public network like Sepolia or Ethereum mainnet, open permissionless write access would allow malicious actors to flood the registry with arbitrary or false-positive hashes, polluting the fast-path cache. By restricting submissions to the deployer / backend worker address, ChainShield maintains registry integrity without complex staking, voting, or governance overhead.
- **Academic Context**: No DAO, governance token, staking, dispute mechanism, or multi-signature scheme is implemented, keeping the contract auditable, gas-efficient, and easy to deploy via Remix IDE.

### 8. Privacy Model
- **Strict Zero-PII Policy**: The contract never accepts, stores, or emits raw text, URLs, usernames, phone numbers, IP addresses, or sender identities.
- The off-chain pipeline irreversibly converts sensitive messages and URLs into one-way cryptographic Keccak-256 hashes before interacting with the chain.
- Even if a phishing message contains private personal details, only the one-way hash `0x...` reaches the public ledger.

### 9. What the Contract Explicitly Does NOT Do
- Does **NOT** tokenize text, run NLTK, or perform natural language processing.
- Does **NOT** execute machine learning models or inference.
- Does **NOT** calculate fuzzy hashes or assess semantic similarity.
- Does **NOT** implement user reputation, community voting, or confirmation disputes.
- Does **NOT** store raw messages or URLs.
- Does **NOT** provide wildcard, substring, or regex queries.

---

## 9. Threat Registry Dataset Seeding Pipeline

### 1. Architectural Purpose & Role of Seeding
The seeding pipeline (`src/blockchain/seed_registry.py`) populates the smart contract with initial cryptographic fingerprints of verified threats sourced from historical benchmark datasets (such as the PhiUSIIL Phishing URL dataset).

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   SEEDING VS. MACHINE LEARNING WORKFLOW                │
├───────────────────────────────────┬────────────────────────────────────┤
│          DATASET SEEDING          │        MACHINE LEARNING            │
│  (Initial Ground-Truth Fingerprints) (Classification of Unseen Variants)│
├───────────────────────────────────┼────────────────────────────────────┤
│ • Offline, batch pipeline         │ • Real-time, per-request inference │
│ • Ingests verified threat records │ • Evaluates newly observed content │
│ • Runs BEFORE production queries  │ • Runs when threatExists() == false│
│ • Verdict = 1, Confidence = 100   │ • Model outputs predicted scores   │
│ • One-way Keccak-256 fingerprints │ • Newly confirmed threats appended │
└───────────────────────────────────┴────────────────────────────────────┘
```

### 2. Strict Threat-Only Selection (Zero-Benign Policy)
ChainShield's smart contract is strictly a registry of **known threats**, not a database of the entire internet or benign communications:
- Only records labeled as confirmed threats (`phishing`, `smishing`, `spam`, or PhiUSIIL `label == 0`) are selected for seeding.
- **Benign records are NEVER registered**: Registering benign content on-chain would waste transaction gas and subvert the registry's fast-path query logic.
- If a queried hash is absent (`threatExists(hash) == false`), the client immediately routes the input to the ML classification pipeline.

### 3. URL vs. Message Handling
The seeding pipeline supports both data modalities, directing inputs to the appropriate canonicalizer and domain separator:
- **URL Records (`ThreatType.URL = 1`)**:
  - Normalized via `canonicalize_url()` (RFC 3986, port stripping, query sorting, trailing slash retention).
  - Hashed via `generate_url_hash()` (`"url:"` prefix + Keccak-256).
- **Message Records (`ThreatType.MESSAGE = 0`)**:
  - Normalized via `canonicalize_message()` (NFKC, smart quotes, lowercase, NLTK `WordPunctTokenizer` token order, stopwords preserved).
  - Hashed via `generate_message_hash()` (`"message:"` prefix + Keccak-256).

### 4. Hash-Based Deduplication (Two-Tier)
Deduplication operates on the final `bytes32` Keccak-256 digest, capturing two distinct classes of duplicates:
1. **Raw Duplicates**: Records with identical raw string values in the dataset.
2. **Canonical Duplicates**: Distinct raw strings that normalize to identical canonical forms (e.g. `HTTPS://PHISH.XYZ:443/login` vs `https://phish.xyz/login`, or `"Your Account Is Blocked"` vs `"your   account   is   blocked"`).

By deduplicating on `threatHash`, the pipeline guarantees that the smart contract's `DuplicateHash` revert is never triggered during seeding.

### 5. Verdict and Confidence Policy
- **`verdict = 1`**: Represents a confirmed threat.
- **`confidence = 100`**: Represents dataset-confirmed ground-truth knowledge, distinct from a probabilistic ML confidence score.

### 6. Execution Modes: Dry-Run vs. Submit
- **Default Mode (`--dry-run`)**:
  - Inspects and parses the dataset, calculates statistics, performs canonicalization and hashing, and prints summary metrics.
  - **GUARANTEE**: Zero blockchain transactions, zero network calls, and zero state mutations.
- **Explicit Submission Mode (`--submit`)**:
  - Requires target `--contract-address` and environment variables for RPC node and signing credentials (`SEPOLIA_RPC_URL` and `SIGNER_PRIVATE_KEY`).
  - Pre-queries `threatExists(hash)` to skip already-registered fingerprints.
  - Submits batched transactions and waits for transaction receipts.

### 7. Strict Zero-PII & Privacy Constraints
The seeding pipeline enforces complete data minimization:
- Raw message bodies and raw URLs are strictly retained in volatile local memory during hash computation.
- No raw text is included in transaction calldata, events, or on-chain storage.
- Exported JSON artifacts generated by `--output` contain only:
  ```json
  {
    "threatHash": "0x0a5721f2e3f0aec7d02b1c6c0d09aedef7be58f1c2617e1b177a113ca762a1d6",
    "threatType": "URL",
    "threatTypeInt": 1,
    "verdict": 1,
    "confidence": 100
  }
  ```
