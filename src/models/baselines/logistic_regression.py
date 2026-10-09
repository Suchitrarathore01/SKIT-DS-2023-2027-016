
"""Logistic Regression baseline for phishing URL classification."""

from pathlib import Path

import joblib
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.evaluate.url_metrics import (
    evaluate_url_classifier,
    print_url_metrics,
)
from src.features.preprocessing import load_url_split


def build_logistic_regression(random_state: int = 42) -> Pipeline:
    """Build a reproducible preprocessing and classification pipeline."""

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_state,
                ),
            ),
        ]
    )


def train_logistic_regression(
    split_directory: str = "data/processed/url_splits",
    train_file: str = "stratified_train.csv",
    validation_file: str = "stratified_validation.csv",
    model_directory: str = "models/url_baselines",
    random_state: int = 42,
) -> dict:
    """Train on the training split and evaluate on validation data."""

    X_train, y_train = load_url_split(
        split_directory, train_file, "train"
    )
    X_val, y_val = load_url_split(
        split_directory, validation_file, "validation"
    )

    # Fit imputation, scaling, and the classifier on training data only.
    model = build_logistic_regression(random_state=random_state)
    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    # The probability column for class 0 represents phishing.
    class_labels = list(model.named_steps["classifier"].classes_)
    phishing_index = class_labels.index(0)
    phishing_scores = model.predict_proba(X_val)[:, phishing_index]

    results = evaluate_url_classifier(
        y_true=y_val,
        y_pred=predictions,
        phishing_scores=phishing_scores,
    )

    print_url_metrics(results)

    output_directory = Path(model_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    model_path = output_directory / "logistic_regression.joblib"
    joblib.dump(model, model_path)

    print(f"\nSaved model to: {model_path}")

    return results


if __name__ == "__main__":
    train_logistic_regression()
