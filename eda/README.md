# EDA - Quick Start

## Setup (one time)
```bash
cd pega-attest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Prepare input
1. Open `eda/input/pega_input.xlsx` (template already there)
2. Paste your attestation data into the **"data"** sheet
3. Paste your user directory into the **"users"** sheet
4. Save

## Run
```bash
source .venv/bin/activate
python eda/run_eda.py
```

## Output
Opens `eda/output/eda_report.html` in your browser.
Single page — scroll through or press **J/K** to jump between sections.
Screenshot what you need.
