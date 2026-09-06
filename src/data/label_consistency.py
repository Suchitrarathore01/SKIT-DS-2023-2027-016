"""Check labeling consistency and category distribution on categorized.csv."""
import re
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd

# Ensure project root is on sys.path for direct script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_PATH = Path("data/processed/categorized.csv")

# Categories and their keyword definitions
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "prize_premium_scam": [
        "ringtone",
        "tone",
        "chat",
        "dating",
        "admirer",
        "txt",
        "reply",
        "club",
        "per msg",
        "rcvd",
        "landline",
        "win",
        "won",
        "winner",
        "prize",
        "draw",
        "congratulations",
        "claim",
    ],
    "free_offer_scam": [
        "free",
        "upgrade",
        "upto",
        "mobile",
        "camera",
        "minutes",
        "entitled",
    ],
    "payment_scam": [
        "gov",
        "payment",
        "covid",
        "tap here",
        "apply",
        "bank",
        "account",
        "verify",
        "suspended",
    ],
}

# Precompile category regexes with word boundaries
CATEGORY_PATTERNS = {
    cat: re.compile(
        r"\b(" + "|".join(re.escape(kw) for kw in kws) + r")\b",
        re.IGNORECASE,
    )
    for cat, kws in CATEGORY_KEYWORDS.items()
}

# Individual keyword patterns to extract exact matches
INDIVIDUAL_KEYWORD_PATTERNS = {
    cat: {
        kw: re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in kws
    }
    for cat, kws in CATEGORY_KEYWORDS.items()
}


def get_matching_keywords(text: str) -> Dict[str, List[str]]:
    """Return dictionary of categories and their specific matched keywords."""
    text_str = str(text)
    matched_by_cat: Dict[str, List[str]] = {}
    for cat, kw_dict in INDIVIDUAL_KEYWORD_PATTERNS.items():
        matched_kws = [kw for kw, pat in kw_dict.items() if pat.search(text_str)]
        if matched_kws:
            matched_by_cat[cat] = matched_kws
    return matched_by_cat


def check_missing_keywords(df: pd.DataFrame) -> Dict[str, int]:
    """Check for messages assigned to a category but containing zero of that category's keywords."""
    print("=" * 70)
    print("1. ZERO-KEYWORD CHECK FOR ASSIGNED CATEGORIES")
    print("=" * 70)

    issues: Dict[str, int] = {}
    for cat, pattern in CATEGORY_PATTERNS.items():
        cat_df = df[df["category"] == cat]
        has_kw = cat_df["text"].apply(lambda t: bool(pattern.search(str(t))))
        zero_kw_count = int((~has_kw).sum())
        issues[cat] = zero_kw_count

        status = "PASSED (0 violations)" if zero_kw_count == 0 else f"FAILED ({zero_kw_count} violations)"
        print(f"  [{cat}]: total={len(cat_df):>4} | zero-keyword messages={zero_kw_count:>2} -> {status}")

    total_issues = sum(issues.values())
    if total_issues == 0:
        print("\n  Result: All categorized messages contain at least one valid keyword.")
    else:
        print(f"\n  Result: Found {total_issues} messages missing assigned category keywords.")

    return issues


def check_ambiguous_matches(df: pd.DataFrame, num_examples: int = 10) -> pd.DataFrame:
    """Check for messages matching keywords from two or more different categories."""
    print("\n" + "=" * 70)
    print("2. AMBIGUOUS CATEGORY CHECK (MATCHING 2+ CATEGORIES)")
    print("=" * 70)

    # Compute matches for every message
    df_matches = df.copy()
    df_matches["cat_matches"] = df_matches["text"].apply(get_matching_keywords)
    df_matches["match_count"] = df_matches["cat_matches"].apply(len)

    ambiguous_df = df_matches[df_matches["match_count"] >= 2].copy()
    total_ambiguous = len(ambiguous_df)

    malicious_ambiguous = len(ambiguous_df[ambiguous_df["label"] == "malicious"])
    benign_ambiguous = len(ambiguous_df[ambiguous_df["label"] == "benign"])

    print(f"  Total messages matching 2+ categories: {total_ambiguous}")
    print(f"    - Malicious rows (scam classification affected): {malicious_ambiguous}")
    print(f"    - Benign rows (assigned 'benign' despite scam keywords): {benign_ambiguous}")

    print(f"\n  Showing {min(num_examples, total_ambiguous)} Ambiguous Examples:")
    print("  " + "-" * 66)

    # Prefer displaying malicious ambiguous examples as they demonstrate categorization conflicts
    display_df = ambiguous_df[ambiguous_df["label"] == "malicious"]
    if len(display_df) < num_examples:
        display_df = ambiguous_df

    for idx, (_, row) in enumerate(display_df.head(num_examples).iterrows(), 1):
        assigned = row["category"]
        matches = row["cat_matches"]
        assigned_kws = matches.get(assigned, [])
        other_matches = {cat: kws for cat, kws in matches.items() if cat != assigned}

        text_snippet = str(row["text"]).strip()
        if len(text_snippet) > 85:
            text_snippet = text_snippet[:82] + "..."

        print(f"  Example {idx}:")
        print(f"    Text: \"{text_snippet}\"")
        print(f"    Assigned Category: {assigned} (keywords: {assigned_kws})")
        print("    Other Matching Categories:")
        for other_cat, kws in other_matches.items():
            print(f"      - {other_cat}: {kws}")
        print()

    return ambiguous_df


def check_category_sizes(df: pd.DataFrame, threshold: int = 50) -> pd.Series:
    """Check category sizes and flag categories with fewer than threshold examples."""
    print("=" * 70)
    print("3. CATEGORY SIZE & TRAINING SUPPORT CHECK")
    print("=" * 70)

    cat_counts = df["category"].value_counts()
    flagged_cats: List[str] = []

    for cat, count in cat_counts.items():
        if count < threshold:
            flag = f" [FLAGGED: Limited training support (< {threshold})]"
            flagged_cats.append(cat)
        else:
            flag = " [Adequate support]"
        print(f"  {cat:<25}: {count:>5} examples {flag}")

    if flagged_cats:
        print(f"\n  Warning: {len(flagged_cats)} category/categories flagged with < {threshold} examples: {flagged_cats}")
    else:
        print(f"\n  Result: All categories meet or exceed the minimum threshold of {threshold} examples.")

    return cat_counts


def run_consistency_checks(data_path: Path = DATA_PATH) -> None:
    """Run full labeling consistency and quality audit."""
    if not data_path.exists():
        raise FileNotFoundError(f"{data_path} not found. Run categorization first.")

    df = pd.read_csv(data_path)

    print("\n" + "#" * 70)
    print(f" LABEL CONSISTENCY REPORT: {data_path.as_posix()}")
    print(f" Total rows analyzed: {len(df)}")
    print("#" * 70 + "\n")

    issues = check_missing_keywords(df)
    ambiguous_df = check_ambiguous_matches(df, num_examples=10)
    cat_counts = check_category_sizes(df, threshold=50)

    mal_ambiguous = len(ambiguous_df[ambiguous_df["label"] == "malicious"])
    flagged = [cat for cat, count in cat_counts.items() if count < 50]
    total_issues = sum(issues.values())

    print("\n" + "=" * 70)
    print("SUMMARY AUDIT CONCLUSION")
    print("=" * 70)
    if total_issues == 0:
        print("  - Keyword Integrity: 100% compliant. No messages lack assigned category keywords.")
    else:
        print(f"  - Keyword Integrity: Found {total_issues} messages missing assigned category keywords.")
    print(f"  - Disambiguation Impact: {mal_ambiguous} malicious messages contain keywords from multiple")
    print("    categories and were resolved using rule evaluation order.")
    if flagged:
        print(f"  - Class Support: Warning: {len(flagged)} category/categories below threshold (< 50): {flagged}")
    else:
        print("  - Class Support: All categories currently meet the >= 50 threshold.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_consistency_checks()
