#!/usr/bin/env python3
"""
Pega Attestations - Exploratory Data Analysis
==============================================

Generates numbered PNG report pages for each input table.
Output is designed to be photographed from screen and shared.

Usage:
  1. Place your Excel files in eda/input/
  2. Update file names in eda/config.py
  3. Optionally paste column descriptions in eda/column_descriptions.txt
  4. Run:  python eda/run_eda.py
  5. Find output PNGs in eda/output/
"""
import sys
import shutil
from pathlib import Path

# Ensure project root is on path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from eda.config import (
    DATA_TABLE_FILE, USER_TABLE_FILE,
    DATA_TABLE_SHEET, USER_TABLE_SHEET,
    OUTPUT_DIR, DESCRIPTIONS_FILE,
    DPI, CATEGORICAL_THRESHOLD, TOP_N_VALUES,
    SAMPLE_ROWS, COLS_PER_SCHEMA_PAGE,
)
from eda.analysis import (
    load_descriptions, profile_dataframe, get_sample_rows,
)
from eda.rendering import ReportRenderer


def clear_output_dir(output_dir: Path):
    """Remove all existing PNGs from output directory."""
    for f in output_dir.glob("*.png"):
        f.unlink()
    print(f"  Cleared {output_dir}")


def load_excel(filepath: Path, sheet_name=None) -> pd.DataFrame:
    """Load an Excel file and return a DataFrame."""
    print(f"  Loading: {filepath.name}")
    if not filepath.exists():
        print(f"  ERROR: File not found: {filepath}")
        print(f"  Place your Excel file in: {filepath.parent}/")
        return None

    df = pd.read_excel(filepath, sheet_name=sheet_name or 0)
    print(f"  Loaded: {len(df):,} rows x {len(df.columns)} columns")
    return df


def run_eda_for_table(df: pd.DataFrame, table_name: str, prefix: str,
                      descriptions: dict):
    """Run full EDA for a single table."""
    print(f"\n{'=' * 60}")
    print(f"  Analyzing: {table_name}")
    print(f"{'=' * 60}")

    renderer = ReportRenderer(OUTPUT_DIR, prefix=prefix, dpi=DPI)

    # 1. Profile all columns
    print("\n  Profiling columns...")
    profiles = profile_dataframe(df, CATEGORICAL_THRESHOLD, TOP_N_VALUES)

    # 2. Overview page
    print("\n  Rendering overview...")
    renderer.render_overview(table_name, prefix, df, profiles)

    # 3. Schema pages
    print("\n  Rendering schema...")
    total_schema_pages = (len(profiles) + COLS_PER_SCHEMA_PAGE - 1) // COLS_PER_SCHEMA_PAGE
    for i in range(total_schema_pages):
        start = i * COLS_PER_SCHEMA_PAGE
        end = min(start + COLS_PER_SCHEMA_PAGE, len(profiles))
        renderer.render_schema_page(
            table_name, profiles[start:end], descriptions,
            page_num=i + 1, total_pages=total_schema_pages,
        )

    # 4. Column descriptions
    print("\n  Rendering descriptions...")
    renderer.render_descriptions_page(table_name, descriptions, list(df.columns))

    # 5. Null analysis
    print("\n  Rendering null analysis...")
    renderer.render_null_analysis(table_name, profiles)

    # 6. Categorical distributions
    categoricals = [p for p in profiles
                    if p["col_type"] in ("categorical", "boolean")]
    if categoricals:
        print(f"\n  Rendering {len(categoricals)} categorical distributions...")
        for p in categoricals:
            desc = descriptions.get(p["name"], "")
            renderer.render_categorical_distribution(table_name, p, desc)

    # 7. Numeric summary
    print("\n  Rendering numeric summary...")
    renderer.render_numeric_summary(table_name, profiles)

    # 8. Date summary
    print("\n  Rendering date summary...")
    renderer.render_date_summary(table_name, profiles)

    # 9. Sample rows
    print("\n  Rendering sample rows...")
    renderer.render_sample_rows(table_name, df, SAMPLE_ROWS)

    print(f"\n  Done: {renderer.page_counter} pages generated for {table_name}")
    return renderer.page_counter


def main():
    print("=" * 60)
    print("  PEGA ATTESTATIONS - EDA REPORT GENERATOR")
    print("=" * 60)

    # Clear previous output
    print("\nClearing previous output...")
    clear_output_dir(OUTPUT_DIR)

    # Load column descriptions
    print("\nLoading column descriptions...")
    descriptions = load_descriptions(DESCRIPTIONS_FILE)
    print(f"  Found {len(descriptions)} descriptions")

    total_pages = 0

    # Data table
    if DATA_TABLE_FILE.exists():
        df_data = load_excel(DATA_TABLE_FILE, DATA_TABLE_SHEET)
        if df_data is not None:
            total_pages += run_eda_for_table(
                df_data, "Data Table", "data", descriptions
            )
    else:
        print(f"\n  SKIPPING data table - file not found: {DATA_TABLE_FILE.name}")
        print(f"  Place your file in: {DATA_TABLE_FILE.parent}/")

    # User table
    if USER_TABLE_FILE.exists():
        df_user = load_excel(USER_TABLE_FILE, USER_TABLE_SHEET)
        if df_user is not None:
            total_pages += run_eda_for_table(
                df_user, "User Directory", "user", descriptions
            )
    else:
        print(f"\n  SKIPPING user table - file not found: {USER_TABLE_FILE.name}")
        print(f"  Place your file in: {USER_TABLE_FILE.parent}/")

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE: {total_pages} total pages generated")
    print(f"  Output:   {OUTPUT_DIR.resolve()}")
    print(f"{'=' * 60}")
    print(f"\n  Browse the output/ folder and photograph the pages to share.")


if __name__ == "__main__":
    main()
