"""
EDA Configuration
=================
Update the file names below to match your Excel files in eda/input/.
"""
from pathlib import Path

# --- Directory paths (no need to edit) ---
EDA_DIR = Path(__file__).parent
INPUT_DIR = EDA_DIR / "input"
OUTPUT_DIR = EDA_DIR / "output"
DESCRIPTIONS_FILE = EDA_DIR / "column_descriptions.txt"

# ============================================================
# === UPDATE THESE FILE NAMES TO MATCH YOUR EXCEL FILES ======
# ============================================================

# Attestation data extract (the ~50 column data table)
DATA_TABLE_FILE = INPUT_DIR / "data_table.xlsx"

# User directory extract (employee ID to first/last name)
USER_TABLE_FILE = INPUT_DIR / "user_table.xlsx"

# Sheet names — use None to read the first sheet
DATA_TABLE_SHEET = None
USER_TABLE_SHEET = None

# ============================================================
# === OUTPUT SETTINGS ========================================
# ============================================================

# Image quality (150 = good for photos, 100 = smaller files)
DPI = 150

# Max unique values before a column is classified as "high cardinality"
CATEGORICAL_THRESHOLD = 50

# How many top values to show for high-cardinality columns
TOP_N_VALUES = 15

# How many sample rows to display
SAMPLE_ROWS = 5

# Columns per schema page
COLS_PER_SCHEMA_PAGE = 12
