"""
Fine-tune DistilBERT on the smish dataset.
RUN THIS ON KAGGLE (GPU notebook) -- not locally, unless you have a GPU.
After training, download models/model_v1/ back into the local repo.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from sklearn.utils.class_weight import compute_class_weight
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    Trainer, TrainingArguments, EarlyStoppingCallback,
)
from datasets import Dataset

MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 96
OUT_DIR = Path("models/model_v1")
DATA_DIR = Path("data/processed")


def load_split(name):
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    labels = sorted(df["label"].unique())
    label2id = {l: i for i, l in enumerate(labels)}
    df["label_id"] = df["label"].map(label2id)
    return df, label2id


def main():
    train_df, label2id = load_split("train")
    val_df, _ = load_split("val")
    id2label = {v: k for k, v in label2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, padding="max_length", max_length=MAX_LEN)

    train_ds = Dataset.from_pandas(train_df[["text", "label_id"]].rename(columns={"label_id": "label"}))
    val_ds = Dataset.from_pandas(val_df[["text", "label_id"]].rename(columns={"label_id": "label"}))
    train_ds = train_ds.map(tokenize, batched=True)
    val_ds = val_ds.map(tokenize, batched=True)

    class_weights = compute_class_weight(
        "balanced", classes=np.array(list(label2id.values())), y=train_df["label_id"].values
    )
    class_weights = torch.tensor(class_weights, dtype=torch.float)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(label2id), id2label=id2label, label2id=label2id
    )

    class WeightedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.pop("labels")
            outputs = model(**inputs)
            loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights.to(outputs.logits.device))
            loss = loss_fct(outputs.logits, labels)
            return (loss, outputs) if return_outputs else loss

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {"macro_f1": f1_score(labels, preds, average="macro")}

    args = TrainingArguments(
        output_dir="checkpoints",
        learning_rate=3e-5,
        num_train_epochs=5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        weight_decay=0.01,
    )

    trainer = WeightedTrainer(
        model=model, args=args,
        train_dataset=train_ds, eval_dataset=val_ds,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    trainer.train()
    metrics = trainer.evaluate()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(OUT_DIR))
    tokenizer.save_pretrained(str(OUT_DIR))

    metadata = {
        "version": "v1",
        "base_model": MODEL_NAME,
        "hyperparameters": {"lr": 3e-5, "epochs": 5, "max_len": MAX_LEN},
        "metrics": metrics,
        "label2id": label2id,
        "drive_link": "PASTE_YOUR_DRIVE_LINK_HERE_AFTER_UPLOAD",
    }
    (OUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
