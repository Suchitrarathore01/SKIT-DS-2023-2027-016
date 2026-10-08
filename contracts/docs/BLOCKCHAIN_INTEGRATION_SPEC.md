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
Keccak-256 Hash (OFF-CHAIN)
      ↓
bytes32 threat hash
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

### Why Canonicalization Happens Off-Chain
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

If any environment deviates in tokenization, punctuation handling, casing, or parameter ordering, hash verification will fail.

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
