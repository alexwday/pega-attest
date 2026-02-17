#!/usr/bin/env python3
"""
Pega Attestations - Exploratory Data Analysis
==============================================

Generates numbered PNG report pages for each input table.
Output is designed to be photographed from screen and shared.

Usage:
  1. Create eda/input/pega_input.xlsx with two sheets:
     - "data"  — paste your attestation data extract
     - "users" — paste your user directory extract
  2. Run:  python eda/run_eda.py
  3. Find output PNGs in eda/output/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from eda.config import (
    INPUT_FILE, DATA_SHEET, USER_SHEET,
    OUTPUT_DIR, DPI, CATEGORICAL_THRESHOLD,
    TOP_N_VALUES, SAMPLE_ROWS, COLS_PER_SCHEMA_PAGE,
)
from eda.analysis import profile_dataframe
from eda.rendering import ReportRenderer


def clear_output_dir(output_dir: Path):
    for f in output_dir.glob("*.png"):
        f.unlink()
    print(f"  Cleared {output_dir}")


def load_sheet(filepath: Path, sheet_name: str) -> pd.DataFrame:
    print(f"  Loading sheet '{sheet_name}' from {filepath.name}...")
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        print(f"  Loaded: {len(df):,} rows x {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"  ERROR loading sheet '{sheet_name}': {e}")
        return None


def run_eda_for_table(df: pd.DataFrame, table_name: str, prefix: str):
    print(f"\n{'=' * 60}")
    print(f"  Analyzing: {table_name}")
    print(f"{'=' * 60}")

    renderer = ReportRenderer(OUTPUT_DIR, prefix=prefix, dpi=DPI)

    # Profile all columns
    print("\n  Profiling columns...")
    profiles = profile_dataframe(df, CATEGORICAL_THRESHOLD, TOP_N_VALUES)

    # Overview
    print("\n  Rendering overview...")
    renderer.render_overview(table_name, prefix, df, profiles)

    # Schema pages
    print("\n  Rendering schema...")
    total_schema_pages = (len(profiles) + COLS_PER_SCHEMA_PAGE - 1) // COLS_PER_SCHEMA_PAGE
    for i in range(total_schema_pages):
        start = i * COLS_PER_SCHEMA_PAGE
        end = min(start + COLS_PER_SCHEMA_PAGE, len(profiles))
        renderer.render_schema_page(
            table_name, profiles[start:end],
            page_num=i + 1, total_pages=total_schema_pages,
        )

    # Null analysis
    print("\n  Rendering null analysis...")
    renderer.render_null_analysis(table_name, profiles)

    # Categorical distributions
    categoricals = [p for p in profiles
                    if p["col_type"] in ("categorical", "boolean")]
    if categoricals:
        print(f"\n  Rendering {len(categoricals)} categorical distributions...")
        for p in categoricals:
            renderer.render_categorical_distribution(table_name, p)

    # Numeric summary
    print("\n  Rendering numeric summary...")
    renderer.render_numeric_summary(table_name, profiles)

    # Date summary
    print("\n  Rendering date summary...")
    renderer.render_date_summary(table_name, profiles)

    # Sample rows
    print("\n  Rendering sample rows...")
    renderer.render_sample_rows(table_name, df, SAMPLE_ROWS)

    print(f"\n  Done: {renderer.page_counter} pages generated for {table_name}")
    return renderer.page_counter


def main():
    print("=" * 60)
    print("  PEGA ATTESTATIONS - EDA REPORT GENERATOR")
    print("=" * 60)

    # Check input file exists
    if not INPUT_FILE.exists():
        print(f"\n  ERROR: Input file not found: {INPUT_FILE}")
        print(f"\n  Create {INPUT_FILE.name} in {INPUT_FILE.parent}/")
        print(f"  with two sheets: '{DATA_SHEET}' and '{USER_SHEET}'")
        sys.exit(1)

    # Clear previous output
    print("\nClearing previous output...")
    clear_output_dir(OUTPUT_DIR)

    total_pages = 0

    # Data table
    df_data = load_sheet(INPUT_FILE, DATA_SHEET)
    if df_data is not None:
        total_pages += run_eda_for_table(df_data, "Data Table", "data")

    # User table
    df_user = load_sheet(INPUT_FILE, USER_SHEET)
    if df_user is not None:
        total_pages += run_eda_for_table(df_user, "User Directory", "user")

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {total_pages} total pages generated")
    print(f"  Output:   {OUTPUT_DIR.resolve()}")
    print(f"{'=' * 60}")
    print(f"\n  Browse the output/ folder and photograph the pages to share.")


if __name__ == "__main__":
    main()
