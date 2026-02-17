# EDA - Quick Start

## Setup (one time)
```bash
cd pega-attest
python3 -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run
1. Drop your two Excel files into `eda/input/`
2. Edit `eda/config.py` — update the two file names to match yours
3. (Optional) Paste column descriptions into `eda/column_descriptions.txt`
   - Format: `column_name | One sentence description`
4. Run:
```bash
source .venv/bin/activate
python eda/run_eda.py
```
5. Output PNGs appear in `eda/output/` — numbered and ready to photograph
