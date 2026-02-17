"""
Data analysis functions for EDA.
Profiles DataFrames and classifies columns.
"""
import pandas as pd
import numpy as np
from pathlib import Path


def load_descriptions(filepath: Path) -> dict:
    """Load column descriptions from text file. Returns {column_name: description}."""
    descriptions = {}
    if not filepath.exists():
        return descriptions

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                parts = line.split("|", 1)
                col_name = parts[0].strip()
                desc = parts[1].strip()
                if col_name and desc:
                    descriptions[col_name] = desc
    return descriptions


def classify_column(series: pd.Series, categorical_threshold: int) -> str:
    """
    Classify a column into one of: 'date', 'numeric', 'boolean', 'categorical', 'text'.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Try to detect dates stored as strings
    non_null = series.dropna()
    if len(non_null) > 0:
        sample = non_null.head(100)
        try:
            parsed = pd.to_datetime(sample, format="mixed", dayfirst=False)
            if parsed.notna().sum() > len(sample) * 0.8:
                return "date"
        except (ValueError, TypeError):
            pass

    # Categorical vs high-cardinality text
    n_unique = series.nunique()
    if n_unique <= categorical_threshold:
        return "categorical"
    return "text"


def profile_column(series: pd.Series, col_type: str, top_n: int) -> dict:
    """Generate a profile dict for a single column."""
    total = len(series)
    non_null = series.dropna()
    null_count = series.isna().sum()
    n_unique = series.nunique()

    profile = {
        "name": series.name,
        "dtype": str(series.dtype),
        "col_type": col_type,
        "total": total,
        "non_null": len(non_null),
        "null_count": int(null_count),
        "null_pct": round(null_count / total * 100, 1) if total > 0 else 0,
        "n_unique": int(n_unique),
    }

    # Top values
    if len(non_null) > 0:
        value_counts = series.value_counts(dropna=True).head(top_n)
        profile["top_values"] = [
            (str(val)[:60], int(cnt)) for val, cnt in value_counts.items()
        ]
    else:
        profile["top_values"] = []

    # Type-specific stats
    if col_type == "numeric" and len(non_null) > 0:
        profile["min"] = float(non_null.min())
        profile["max"] = float(non_null.max())
        profile["mean"] = float(non_null.mean())
        profile["median"] = float(non_null.median())
        profile["std"] = float(non_null.std()) if len(non_null) > 1 else 0
        profile["values"] = non_null.values

    if col_type == "date" and len(non_null) > 0:
        try:
            dates = pd.to_datetime(non_null, format="mixed", dayfirst=False)
            profile["date_min"] = str(dates.min())
            profile["date_max"] = str(dates.max())
            profile["date_values"] = dates
        except (ValueError, TypeError):
            profile["date_min"] = "parse error"
            profile["date_max"] = "parse error"

    return profile


def profile_dataframe(df: pd.DataFrame, categorical_threshold: int, top_n: int) -> list:
    """Profile all columns in a DataFrame. Returns list of column profile dicts."""
    profiles = []
    for col in df.columns:
        col_type = classify_column(df[col], categorical_threshold)
        profile = profile_column(df[col], col_type, top_n)
        profiles.append(profile)
    return profiles


def get_sample_rows(df: pd.DataFrame, n_rows: int) -> pd.DataFrame:
    """Get first N rows, truncating long string values for display."""
    sample = df.head(n_rows).copy()
    for col in sample.columns:
        if sample[col].dtype == object:
            sample[col] = sample[col].astype(str).str[:50]
    return sample
