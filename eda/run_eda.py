#!/usr/bin/env python3
"""
Pega Attestations - Exploratory Data Analysis
==============================================

Generates a single HTML report for data exploration.
Open in browser, scroll through, screenshot what you need.

Usage:
  1. Paste your data into eda/input/pega_input.xlsx
     - Sheet "data"  = attestation data extract
     - Sheet "users" = user directory extract
  2. Run:  python eda/run_eda.py
  3. Open: eda/output/eda_report.html in your browser
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from eda.config import (
    INPUT_FILE, DATA_SHEET, USER_SHEET,
    OUTPUT_DIR, CATEGORICAL_THRESHOLD,
    TOP_N_VALUES, SAMPLE_ROWS,
)
from eda.analysis import profile_dataframe
from eda.html_report import generate_report, build_sample_html


def load_sheet(filepath: Path, sheet_name: str) -> pd.DataFrame:
    print(f"  Loading sheet '{sheet_name}' from {filepath.name}...")
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        print(f"  Loaded: {len(df):,} rows x {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"  ERROR loading sheet '{sheet_name}': {e}")
        return None


def build_table_profiles(df: pd.DataFrame, table_name: str) -> dict:
    print(f"\n  Profiling: {table_name}...")
    profiles = profile_dataframe(df, CATEGORICAL_THRESHOLD, TOP_N_VALUES)
    sample_html = build_sample_html(df, SAMPLE_ROWS)

    return {
        "name": table_name,
        "rows": len(df),
        "cols": len(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        "duplicated_rows": int(df.duplicated().sum()),
        "total_nulls": int(df.isna().sum().sum()),
        "total_cells": df.shape[0] * df.shape[1],
        "profiles": profiles,
        "sample_html": sample_html,
        "sample_count": min(SAMPLE_ROWS, len(df)),
    }


def main():
    print("=" * 60)
    print("  PEGA ATTESTATIONS - EDA REPORT GENERATOR")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"\n  ERROR: Input file not found: {INPUT_FILE}")
        print(f"\n  Paste your data into: {INPUT_FILE}")
        print(f"  Sheets needed: '{DATA_SHEET}' and '{USER_SHEET}'")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data_profiles = None
    user_profiles = None

    # Data table
    df_data = load_sheet(INPUT_FILE, DATA_SHEET)
    if df_data is not None and len(df_data) > 0:
        data_profiles = build_table_profiles(df_data, "Data Table")

    # User table
    df_user = load_sheet(INPUT_FILE, USER_SHEET)
    if df_user is not None and len(df_user) > 0:
        user_profiles = build_table_profiles(df_user, "User Directory")

    # Generate HTML report
    print("\n  Generating HTML report...")
    html = generate_report(data_profiles, user_profiles)

    output_path = OUTPUT_DIR / "eda_report.html"
    output_path.write_text(html, encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE")
    print(f"  Open in browser: {output_path.resolve()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
