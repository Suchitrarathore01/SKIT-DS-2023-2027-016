
"""XGBoost baseline for phishing URL classification."""

from pathlib import Path

import joblib
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.evaluate.url_metrics import (
    evaluate_url_classifier,
    print_url_metrics,
)
from src.features.preprocessing import load_url_split


def build_xgboost(random_state: int = 42) -> Pipeline:
    """Build an XGBoost classification pipeline."""

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=300,
                    max_depth=6,
                    learning_rate=0.1,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_xgboost(
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

    model = build_xgboost(random_state=random_state)
    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    # Label 0 represents phishing, so select its probability explicitly.
    classifier = model.named_steps["classifier"]
    phishing_index = list(classifier.classes_).index(0)
    phishing_scores = model.predict_proba(X_val)[:, phishing_index]

    results = evaluate_url_classifier(
        y_true=y_val,
        y_pred=predictions,
        phishing_scores=phishing_scores,
    )

    print_url_metrics(results)

    output_directory = Path(model_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    model_path = output_directory / "xgboost.joblib"
    joblib.dump(model, model_path)

    print(f"\nSaved model to: {model_path}")

    return results


if __name__ == "__main__":
    train_xgboost()
