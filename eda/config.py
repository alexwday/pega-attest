"""
EDA Configuration
=================
"""
from pathlib import Path

# --- Directory paths (no need to edit) ---
EDA_DIR = Path(__file__).parent
INPUT_DIR = EDA_DIR / "input"
OUTPUT_DIR = EDA_DIR / "output"

# ============================================================
# === INPUT FILE =============================================
# ============================================================

# Single Excel workbook with two sheets:
#   Sheet 1: "data"  — the attestation data table
#   Sheet 2: "users" — the user directory table
INPUT_FILE = INPUT_DIR / "pega_input.xlsx"

DATA_SHEET = "data"
USER_SHEET = "users"

# ============================================================
# === OUTPUT SETTINGS ========================================
# ============================================================

DPI = 150
CATEGORICAL_THRESHOLD = 50
TOP_N_VALUES = 15
SAMPLE_ROWS = 5
COLS_PER_SCHEMA_PAGE = 12
