import pandas as pd
import pytest
from pathlib import Path
from src.data.load_data import load_raw


def test_load_raw_utf8_sig_and_bom_stripping(tmp_path: Path):
    # Test CSV containing BOM in column name and whitespace
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("ï»¿Class, Message \nham,hello world\n", encoding="utf-8")

    df = load_raw(csv_file)
    assert list(df.columns) == ["text", "label"]
    assert len(df) == 1
    assert df.iloc[0]["text"] == "hello world"
    assert df.iloc[0]["label"] == "ham"


def test_load_raw_actual_utf8_bom(tmp_path: Path):
    # Test CSV with UTF-8 BOM encoding
    csv_file = tmp_path / "test_bom.csv"
    csv_file.write_text("Class,Message\nspam,win money\n", encoding="utf-8-sig")

    df = load_raw(csv_file)
    assert list(df.columns) == ["text", "label"]
    assert len(df) == 1
    assert df.iloc[0]["text"] == "win money"
    assert df.iloc[0]["label"] == "spam"
