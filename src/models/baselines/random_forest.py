
"""Random Forest baseline for phishing URL classification."""

from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from src.evaluate.url_metrics import (
    evaluate_url_classifier,
    print_url_metrics,
)
from src.features.preprocessing import load_url_split


def build_random_forest(random_state: int = 42) -> Pipeline:
    """Build a Random Forest pipeline."""

    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=None,
                    class_weight="balanced",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_random_forest(
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

    model = build_random_forest(random_state=random_state)
    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    # Probability for class 0 represents the phishing score.
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

    model_path = output_directory / "random_forest.joblib"
    joblib.dump(model, model_path)

    print(f"\nSaved model to: {model_path}")

    return results


if __name__ == "__main__":
    train_random_forest()
