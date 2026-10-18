
"""Prepare phishing URL datasets for classical ML baselines."""

from pathlib import Path
from typing import Tuple

import pandas as pd

from src.features.url_features_schema import URL_ONLY_FEATURES, TARGET


VALID_LABELS = {0, 1}


def validate_url_dataset(
    dataframe: pd.DataFrame,
    split_name: str = "dataset",
) -> None:
    """Validate the required URL features and binary target labels."""

    if dataframe.empty:
        raise ValueError(f"{split_name} dataset is empty.")

    required_columns = set(URL_ONLY_FEATURES) | {TARGET}
    missing_columns = sorted(required_columns - set(dataframe.columns))

    if missing_columns:
        raise ValueError(
            f"{split_name} dataset is missing required columns: "
            f"{missing_columns}"
        )

    labels = pd.to_numeric(dataframe[TARGET], errors="coerce")

    if labels.isna().any():
        raise ValueError(
            f"{split_name} dataset contains missing or invalid labels."
        )

    if not set(labels.unique()).issubset(VALID_LABELS):
        raise ValueError(
            f"{split_name} dataset must use labels 0 (phishing) "
            "and 1 (legitimate)."
        )


def prepare_url_features(
    dataframe: pd.DataFrame,
    split_name: str = "dataset",
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Select URL-only features and separate the target.

    Invalid numeric feature values are converted to NaN.
    Imputation and scaling must be fitted later on training data only.
    """

    validate_url_dataset(dataframe, split_name)

    features = dataframe[URL_ONLY_FEATURES].copy()

    for column in URL_ONLY_FEATURES:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    # Replace infinite values so they can be handled by the imputer.
    features = features.replace([float("inf"), float("-inf")], float("nan"))

    labels = pd.to_numeric(dataframe[TARGET]).astype("int8")

    return features, labels


def load_url_split(
    split_directory: str | Path,
    filename: str,
    split_name: str,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Load and prepare one previously generated URL dataset split."""

    file_path = Path(split_directory) / filename

    if not file_path.is_file():
        raise FileNotFoundError(
            f"URL split file not found: {file_path}"
        )

    dataframe = pd.read_csv(file_path)

    return prepare_url_features(dataframe, split_name)