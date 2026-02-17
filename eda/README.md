# EDA - Quick Start

## Setup (one time)
```bash
cd pega-attest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Prepare input
1. Create an Excel file called `pega_input.xlsx` in `eda/input/`
2. It needs two sheets:
   - Sheet named **"data"** — paste your attestation data extract here
   - Sheet named **"users"** — paste your user directory extract here

## Run
```bash
source .venv/bin/activate
python eda/run_eda.py
```

## Output
Numbered PNGs appear in `eda/output/` — photograph and share back.
