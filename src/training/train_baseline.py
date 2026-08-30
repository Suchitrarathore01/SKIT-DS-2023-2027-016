"""Train TF-IDF + LogisticRegression and LinearSVC baselines. Logs macro-F1 to experiments.csv."""
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, f1_score

DATA_DIR = Path("data/processed")
EXPERIMENTS_PATH = Path("experiments.csv")


def load_split(name):
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    return df["text"], df["label"]


def log_experiment(model_name, macro_f1, report_dict):
    row = {"model": model_name, "macro_f1": macro_f1}
    df = pd.DataFrame([row])
    if EXPERIMENTS_PATH.exists():
        df.to_csv(EXPERIMENTS_PATH, mode="a", header=False, index=False)
    else:
        df.to_csv(EXPERIMENTS_PATH, index=False)


def train_baseline():
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")

    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)

    models = {
        "logistic_regression": LogisticRegression(class_weight="balanced", max_iter=1000),
        "linear_svc": LinearSVC(class_weight="balanced"),
    }

    for name, model in models.items():
        model.fit(X_train_vec, y_train)
        preds = model.predict(X_val_vec)
        macro_f1 = f1_score(y_val, preds, average="macro")
        report = classification_report(y_val, preds, output_dict=True)

        print(f"\n=== {name} ===")
        print(f"macro-F1: {macro_f1:.4f}")
        print(classification_report(y_val, preds))

        log_experiment(name, macro_f1, report)

    print(f"\nResults logged to {EXPERIMENTS_PATH}")


if __name__ == "__main__":
    train_baseline()
