#!/usr/bin/env python3
"""
Pega Attestations - Exploratory Data Analysis
==============================================

Generates per-table HTML slideshows and Markdown reports for LLM analysis.

Usage:
  1. Paste your data into eda/input/pega_input.xlsx
     - Sheet "data"  = attestation data extract
     - Sheet "users" = user directory extract
  2. Run:  python eda/run_eda.py
  3. Outputs in eda/output/:
     - HTML slideshows (one per table, for browsing/screenshots)
     - Markdown profiles (one per table, paste into LLM as message 1)
     - Markdown samples (one per table, paste into LLM as message 2)
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
from eda.html_report import generate_report, build_sample_data
from eda.md_report import generate_table_profile_md, generate_table_samples_md


# Map table names to filename-safe slugs
TABLE_SLUGS = {
    "Data Table": "data_table",
    "User Directory": "user_directory",
}


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
    sample_df, sample_count = build_sample_data(df, SAMPLE_ROWS)

    return {
        "name": table_name,
        "rows": len(df),
        "cols": len(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        "duplicated_rows": int(df.duplicated().sum()),
        "total_nulls": int(df.isna().sum().sum()),
        "total_cells": df.shape[0] * df.shape[1],
        "profiles": profiles,
        "sample_rows": sample_df,
        "sample_count": sample_count,
    }


def write_table_outputs(table_profiles: dict) -> list:
    """Write HTML + Markdown outputs for one table. Returns list of output paths."""
    slug = TABLE_SLUGS[table_profiles["name"]]
    paths = []

    # HTML slideshow (just this table)
    html_path = OUTPUT_DIR / f"eda_{slug}.html"
    html_content = generate_report(table_profiles, None)
    html_path.write_text(html_content, encoding="utf-8")
    paths.append(("HTML slideshow", html_path))

    # Markdown profile (message 1 — paste first)
    profile_path = OUTPUT_DIR / f"eda_{slug}_profile.md"
    profile_content = generate_table_profile_md(table_profiles)
    profile_path.write_text(profile_content, encoding="utf-8")
    paths.append(("MD profile (msg 1)", profile_path))

    # Markdown samples (message 2 — paste after LLM responds)
    samples_path = OUTPUT_DIR / f"eda_{slug}_samples.md"
    samples_content = generate_table_samples_md(table_profiles)
    samples_path.write_text(samples_content, encoding="utf-8")
    paths.append(("MD samples (msg 2)", samples_path))

    return paths


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

    all_outputs = []

    df_data = load_sheet(INPUT_FILE, DATA_SHEET)
    if df_data is not None and len(df_data) > 0:
        data_profiles = build_table_profiles(df_data, "Data Table")
        print("\n  Writing Data Table outputs...")
        all_outputs.extend(write_table_outputs(data_profiles))

    df_user = load_sheet(INPUT_FILE, USER_SHEET)
    if df_user is not None and len(df_user) > 0:
        user_profiles = build_table_profiles(df_user, "User Directory")
        print("\n  Writing User Directory outputs...")
        all_outputs.extend(write_table_outputs(user_profiles))

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE — {len(all_outputs)} files generated:")
    print(f"{'=' * 60}")
    for label, path in all_outputs:
        print(f"  {label:20s}  {path.name}")
    print()
    print("  LLM workflow per table:")
    print("    1. Copy the *_profile.md into a new LLM chat")
    print("    2. LLM will respond asking for example rows")
    print("    3. Copy the *_samples.md as your next message")
    print("    4. LLM produces a written prose summary")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
