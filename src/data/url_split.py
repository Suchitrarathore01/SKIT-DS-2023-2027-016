from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import (
    StratifiedGroupKFold,
    train_test_split,
)


RANDOM_STATE = 42

INPUT_PATH = Path("data/processed/featured_url.csv")
OUTPUT_DIR = Path("data/processed/url_splits")

TARGET_COLUMN = "label"
DOMAIN_COLUMN = "Domain"
URL_COLUMN = "URL"


def validate_input(df: pd.DataFrame) -> None:
    """Validate the input dataset before creating splits."""

    required_columns = {
        URL_COLUMN,
        DOMAIN_COLUMN,
        TARGET_COLUMN,
    }

    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if df[URL_COLUMN].isna().any():
        raise ValueError("URL column contains missing values.")

    if df[DOMAIN_COLUMN].isna().any():
        raise ValueError("Domain column contains missing values.")

    if df[TARGET_COLUMN].isna().any():
        raise ValueError("Target column contains missing values.")

    unique_labels = set(df[TARGET_COLUMN].unique())

    if unique_labels != {0, 1}:
        raise ValueError(
            f"Expected target labels {{0, 1}}, "
            f"found {sorted(unique_labels)}."
        )

    if df[URL_COLUMN].duplicated().any():
        raise ValueError(
            "Duplicate URLs detected. "
            "The input dataset should already be deduplicated."
        )


def get_class_proportions(
    df: pd.DataFrame,
) -> pd.Series:
    """Return class proportions sorted by label."""
    return (
        df[TARGET_COLUMN]
        .value_counts(normalize=True)
        .sort_index()
    )


def print_split_summary(
    name: str,
    df: pd.DataFrame,
    global_class_ratio: pd.Series,
) -> None:
    """Print detailed statistics for a split."""

    class_counts = (
        df[TARGET_COLUMN]
        .value_counts()
        .sort_index()
    )

    class_proportions = get_class_proportions(df)

    phishing_ratio = class_proportions.get(0, 0.0)
    global_phishing_ratio = global_class_ratio.get(0, 0.0)

    deviation = phishing_ratio - global_phishing_ratio

    print(f"\n{name}")
    print("-" * 55)

    print(f"Rows: {len(df):,}")
    print(f"Unique URLs: {df[URL_COLUMN].nunique():,}")
    print(f"Unique domains: {df[DOMAIN_COLUMN].nunique():,}")

    print("\nClass distribution:")
    print(class_counts)

    print("\nClass proportions:")
    print(class_proportions.round(4))

    print(
        f"\nPhishing proportion deviation from global: "
        f"{deviation:+.4f}"
    )


def validate_class_presence(
    splits: dict[str, pd.DataFrame],
) -> None:
    """Ensure every split contains both target classes."""

    for name, split_df in splits.items():
        classes = set(split_df[TARGET_COLUMN].unique())

        if classes != {0, 1}:
            raise ValueError(
                f"{name} does not contain both classes. "
                f"Found classes: {sorted(classes)}"
            )


def validate_domain_overlap(
    splits: dict[str, pd.DataFrame],
) -> None:
    """
    Ensure that no domain appears in more than one split/fold.

    Multiple URLs from the same domain are allowed within the
    same split. The check only detects domains shared between
    different splits.
    """

    split_domains = {
        split_name: set(
            split_df[DOMAIN_COLUMN].dropna().unique()
        )
        for split_name, split_df in splits.items()
    }

    split_names = list(split_domains.keys())

    for i, first_name in enumerate(split_names):
        for second_name in split_names[i + 1:]:
            overlap = (
                split_domains[first_name]
                .intersection(
                    split_domains[second_name]
                )
            )

            if overlap:
                examples = sorted(overlap)[:10]

                raise ValueError(
                    f"Domain overlap detected between "
                    f"'{first_name}' and '{second_name}'. "
                    f"Overlapping domains: {len(overlap)}. "
                    f"Examples: {examples}"
                )

    print("Domain overlap check: PASSED")


def validate_row_coverage(
    original_df: pd.DataFrame,
    splits: dict[str, pd.DataFrame],
) -> None:
    """
    Ensure every URL appears exactly once across the supplied splits.
    """

    original_urls = set(original_df[URL_COLUMN])

    split_urls = set()

    total_rows = 0

    for split_df in splits.values():
        split_urls.update(split_df[URL_COLUMN])
        total_rows += len(split_df)

    if total_rows != len(original_df):
        raise ValueError(
            "Row coverage check failed. "
            f"Original rows: {len(original_df):,}, "
            f"split rows: {total_rows:,}."
        )

    if split_urls != original_urls:
        missing_urls = original_urls - split_urls
        extra_urls = split_urls - original_urls

        raise ValueError(
            "URL coverage check failed. "
            f"Missing URLs: {len(missing_urls):,}, "
            f"Unexpected URLs: {len(extra_urls):,}."
        )

    if len(split_urls) != total_rows:
        raise ValueError(
            "Duplicate URL detected across splits."
        )

    print("URL coverage check: PASSED")


def create_stratified_split(
    df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Create a standard 70/15/15 stratified split.

    The target label distribution is preserved across
    train, validation, and test sets.
    """

    train_df, temporary_df = train_test_split(
        df,
        test_size=0.30,
        stratify=df[TARGET_COLUMN],
        random_state=RANDOM_STATE,
    )

    validation_df, test_df = train_test_split(
        temporary_df,
        test_size=0.50,
        stratify=temporary_df[TARGET_COLUMN],
        random_state=RANDOM_STATE,
    )

    return {
        "train": train_df.copy(),
        "validation": validation_df.copy(),
        "test": test_df.copy(),
    }


def create_domain_aware_folds(
    df: pd.DataFrame,
    n_splits: int = 5,
) -> dict[str, pd.DataFrame]:
    """
    Create stratified group folds using Domain as the group.

    URLs belonging to the same domain are kept within the same fold.
    Class proportions are approximately preserved across folds.
    """

    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    folds: dict[str, pd.DataFrame] = {}

    for fold_number, (_, fold_indices) in enumerate(
        splitter.split(
            X=df,
            y=df[TARGET_COLUMN],
            groups=df[DOMAIN_COLUMN],
        ),
        start=1,
    ):
        fold_name = f"fold_{fold_number}"

        folds[fold_name] = (
            df.iloc[fold_indices]
            .copy()
            .reset_index(drop=True)
        )

    return folds


def save_splits(
    splits: dict[str, pd.DataFrame],
    prefix: str,
) -> None:
    """Save generated datasets to the local processed-data directory."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for split_name, split_df in splits.items():

        output_path = (
            OUTPUT_DIR
            / f"{prefix}_{split_name}.csv"
        )

        split_df.to_csv(
            output_path,
            index=False,
        )

        print(
            f"Saved {split_name}: "
            f"{output_path}"
        )


def main() -> None:
    print(f"Loading dataset: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)

    print(f"Input shape: {df.shape}")

    validate_input(df)

    global_class_ratio = get_class_proportions(df)

    print("\nGlobal class distribution:")
    print(
        df[TARGET_COLUMN]
        .value_counts()
        .sort_index()
    )

    print("\nGlobal class proportions:")
    print(global_class_ratio.round(4))

    # =========================================================
    # STANDARD STRATIFIED SPLIT
    # =========================================================

    print("\n" + "=" * 70)
    print("STANDARD STRATIFIED SPLIT")
    print("=" * 70)

    stratified_splits = create_stratified_split(df)

    validate_class_presence(stratified_splits)
    validate_row_coverage(
        df,
        stratified_splits,
    )

    for name, split_df in stratified_splits.items():
        print_split_summary(
            name,
            split_df,
            global_class_ratio,
        )

    save_splits(
        stratified_splits,
        "stratified",
    )

    # =========================================================
    # DOMAIN-AWARE STRATIFIED FOLDS
    # =========================================================

    print("\n" + "=" * 70)
    print("DOMAIN-AWARE STRATIFIED FOLDS")
    print("=" * 70)

    domain_folds = create_domain_aware_folds(
        df,
        n_splits=5,
    )

    validate_class_presence(domain_folds)

    validate_domain_overlap(domain_folds)

    validate_row_coverage(
        df,
        domain_folds,
    )

    for fold_name, fold_df in domain_folds.items():
        print_split_summary(
            fold_name,
            fold_df,
            global_class_ratio,
        )

    save_splits(
        domain_folds,
        "domain_aware",
    )

    print("\n" + "=" * 70)
    print("URL SPLITTING COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()