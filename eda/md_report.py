"""
Generates per-table Markdown EDA reports designed for copy/paste into an LLM chat.

Each table produces two files:
  1. Profile MD  — prompt + schema/distributions/stats, ends by telling the LLM
                   to expect example rows in the next message.
  2. Samples MD  — just the example rows, designed to paste as a follow-up message.
"""
from datetime import datetime


def generate_table_profile_md(t: dict) -> str:
    """Generate the profile markdown for one table (no sample rows).

    Includes the full LLM prompt and all schema/distribution/numeric/date data.
    Ends by telling the LLM that example rows will follow in the next message.
    """
    sections = []
    sections.append(_build_prompt(t["name"]))
    sections.append("---\n")
    sections.append(_render_profile_data(t))
    sections.append(_build_closing(t["name"]))
    return "\n".join(sections)


def generate_table_samples_md(t: dict) -> str:
    """Generate just the sample rows markdown for one table.

    Designed to be pasted as a follow-up message after the profile.
    """
    parts = []
    name = t["name"]

    parts.append(f"Here are the example data rows for the **{name}** as promised.\n")

    if t.get("sample_rows") is not None:
        df_sample = t["sample_rows"]
        n_rows = t["sample_count"]
        parts.append(f"### {name} — Sample Rows (first {n_rows})\n")
        for r in range(n_rows):
            parts.append(f"**Row {r+1}:**")
            for col in df_sample.columns:
                val = str(df_sample[col].iloc[r])[:80]
                parts.append(f"  {col}: {val}")
            parts.append("")
    else:
        parts.append("No sample rows available for this table.\n")

    parts.append("---\n")
    parts.append("Please now proceed with the full written narrative summary as described "
                 "in my previous message, incorporating these example rows into your "
                 "sample data observations section.")
    return "\n".join(parts)


def _build_prompt(table_name: str) -> str:
    return f"""# EDA Data Profile — {table_name}

**Instructions:** You are a senior data analyst. Below is a complete exploratory data analysis (EDA) profile of the **{table_name}** from a financial attestation system used by a bank's CFO group. The data covers monthly transit attestations across approximately 2,000 users.

**Your task:** Read all of the data profile information below and then produce a **written narrative summary** of this dataset. Follow these rules strictly:

1. **Output format: prose paragraphs only.** Do NOT produce tables, bullet lists, code blocks, or formatted metrics. Write in complete sentences organized into paragraphs. This summary will be photographed and OCR'd, so plain flowing text is critical.
2. **Structure your summary in this order:**
   - **Dataset overview** — Row count, column count. What the data appears to represent at a high level.
   - **Data quality assessment** — Overall null rates, duplicate rows, any columns with severe missing data (>30% null). Call out specific column names and their null percentages.
   - **Column type breakdown** — How many columns are categorical, numeric, date, text, boolean. What this tells us about the data structure.
   - **Key categorical columns** — For each categorical/boolean column, describe the distribution in words. Name the top values and their approximate shares. Flag any columns with suspicious distributions (e.g., one value dominates 90%+, or many near-equal values).
   - **Numeric columns** — For each numeric column, describe the range, central tendency, and spread in words. Flag any with extreme ranges, high standard deviations, or unusual min/max values.
   - **Date columns** — Describe the date ranges observed. Note any gaps or unexpected date boundaries.
   - **Sample data observations** — Based on the example rows (which I will provide in my next message), note any patterns, formatting issues, or data quality concerns visible in the raw values.
   - **Potential data issues and recommendations** — Summarize any red flags: high nulls, potential duplicates, columns that may need cleaning, suspicious distributions, or columns that might be misclassified.
3. **Be specific.** Always name the exact columns, values, and numbers you are referring to. Vague statements like "some columns have nulls" are not useful.
4. **Be concise but thorough.** Aim for roughly 400-800 words. Do not pad with filler.
5. **Use plain language.** Avoid jargon where possible. Write as if briefing a non-technical executive who needs to understand the data landscape.

**Important:** I will provide the example data rows in my **next message** because of input length limits. After reviewing all of the profile data below, please respond with: "Understood. I have reviewed the {table_name} profile data. Please provide the example data rows and I will produce the full written narrative summary."

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def _build_closing(table_name: str) -> str:
    return f"""---

**End of {table_name} profile data.** Remember: do NOT produce the summary yet. Please respond confirming you have reviewed this data and ask me to provide the example rows in my next message."""


def _render_profile_data(t: dict) -> str:
    """Render schema, distributions, numeric, and date data (no sample rows)."""
    parts = []
    name = t["name"]

    # --- Overview ---
    null_pct = t["total_nulls"] / t["total_cells"] * 100 if t["total_cells"] > 0 else 0
    type_counts = {}
    for p in t["profiles"]:
        ct = p["col_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1
    type_summary = ", ".join(f"{ct}: {n}" for ct, n in sorted(type_counts.items()))

    parts.append(f"## {name} — Overview\n")
    parts.append(f"Rows: {t['rows']:,} | Columns: {t['cols']} | "
                 f"Memory: {t['memory_mb']:.1f} MB | "
                 f"Duplicate rows: {t['duplicated_rows']:,} | "
                 f"Total null cells: {t['total_nulls']:,} ({null_pct:.1f}%)\n")
    parts.append(f"Column types — {type_summary}\n")

    # --- Schema ---
    parts.append(f"### {name} — Schema\n")
    parts.append("| # | Column | Type | Dtype | Non-Null | Null% | Unique | Top Value (count) |")
    parts.append("|---|--------|------|-------|----------|-------|--------|--------------------|")
    for i, p in enumerate(t["profiles"]):
        top_val = ""
        if p["top_values"]:
            val, cnt = p["top_values"][0]
            vd = val[:40] + "..." if len(val) > 40 else val
            top_val = f"{vd} ({cnt:,})"
        parts.append(
            f"| {i+1} | {p['name']} | {p['col_type']} | {p['dtype'][:12]} | "
            f"{p['non_null']:,} | {p['null_pct']}% | {p['n_unique']:,} | {top_val} |"
        )
    parts.append("")

    # --- Categorical/Boolean distributions ---
    categoricals = [p for p in t["profiles"]
                    if p["col_type"] in ("categorical", "boolean") and p["top_values"]]
    if categoricals:
        parts.append(f"### {name} — Value Distributions (Categorical/Boolean)\n")
        for p in categoricals:
            parts.append(f"**{p['name']}** ({p['n_unique']} unique, {p['null_pct']}% null)")
            for val, cnt in p["top_values"][:10]:
                pct = cnt / p["non_null"] * 100 if p["non_null"] > 0 else 0
                parts.append(f"  {val}: {cnt:,} ({pct:.1f}%)")
            if len(p["top_values"]) > 10:
                parts.append(f"  ... and {p['n_unique'] - 10} more values")
            parts.append("")

    # --- Numeric summary ---
    numerics = [p for p in t["profiles"] if p["col_type"] == "numeric"]
    if numerics:
        parts.append(f"### {name} — Numeric Summary\n")
        parts.append("| Column | Non-Null | Null% | Min | Max | Mean | Median | Std |")
        parts.append("|--------|----------|-------|-----|-----|------|--------|-----|")
        for p in numerics:
            def fmt(v):
                if abs(v) >= 1000:
                    return f"{v:,.1f}"
                return f"{v:.4g}"
            parts.append(
                f"| {p['name']} | {p['non_null']:,} | {p['null_pct']}% | "
                f"{fmt(p.get('min', 0))} | {fmt(p.get('max', 0))} | "
                f"{fmt(p.get('mean', 0))} | {fmt(p.get('median', 0))} | "
                f"{fmt(p.get('std', 0))} |"
            )
        parts.append("")

    # --- Date summary ---
    dates = [p for p in t["profiles"] if p["col_type"] == "date"]
    if dates:
        parts.append(f"### {name} — Date Columns\n")
        parts.append("| Column | Non-Null | Null% | Unique | Min | Max |")
        parts.append("|--------|----------|-------|--------|-----|-----|")
        for p in dates:
            parts.append(
                f"| {p['name']} | {p['non_null']:,} | {p['null_pct']}% | "
                f"{p['n_unique']:,} | {p.get('date_min', 'N/A')} | {p.get('date_max', 'N/A')} |"
            )
        parts.append("")

    return "\n".join(parts)
