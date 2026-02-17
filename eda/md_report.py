"""
Generates a Markdown EDA report designed for copy/paste into an LLM chat interface.
Includes an analysis prompt that instructs the LLM to produce a written prose summary.
"""
from datetime import datetime


def generate_md_report(data_profiles: dict | None, user_profiles: dict | None) -> str:
    """Generate complete markdown report with LLM prompt + data."""
    sections = []
    sections.append(_build_prompt())
    sections.append("---\n")

    for table in [data_profiles, user_profiles]:
        if table is None:
            continue
        sections.append(_render_table_md(table))

    return "\n".join(sections)


def _build_prompt() -> str:
    return f"""# EDA Data Profile — Analyze and Summarize

**Instructions for the LLM:** You are a senior data analyst. Below is a complete exploratory data analysis (EDA) profile of one or two database tables from a financial attestation system used by a bank's CFO group. The data covers monthly transit attestations across ~2,000 users.

**Your task:** Read all of the data profile information below and produce a **written narrative summary** of the dataset. Follow these rules strictly:

1. **Output format: prose paragraphs only.** Do NOT produce tables, bullet lists, code blocks, or formatted metrics. Write in complete sentences organized into paragraphs. This summary will be photographed and OCR'd, so plain flowing text is critical.
2. **Structure your summary in this order:**
   - **Dataset overview** — How many tables, rows, columns. What the data appears to represent at a high level.
   - **Data quality assessment** — Overall null rates, duplicate rows, any columns with severe missing data (>30% null). Call out specific column names and their null percentages.
   - **Column type breakdown** — How many columns are categorical, numeric, date, text, boolean. What this tells us about the data structure.
   - **Key categorical columns** — For each categorical/boolean column, describe the distribution in words. Name the top values and their approximate shares. Flag any columns with suspicious distributions (e.g., one value dominates 90%+, or many near-equal values).
   - **Numeric columns** — For each numeric column, describe the range, central tendency, and spread in words. Flag any with extreme ranges, high standard deviations, or unusual min/max values.
   - **Date columns** — Describe the date ranges observed. Note any gaps or unexpected date boundaries.
   - **Sample data observations** — Based on the sample rows, note any patterns, formatting issues, or data quality concerns visible in the raw values.
   - **Potential data issues and recommendations** — Summarize any red flags: high nulls, potential duplicates, columns that may need cleaning, suspicious distributions, or columns that might be misclassified.
3. **Be specific.** Always name the exact columns, values, and numbers you are referring to. Vague statements like "some columns have nulls" are not useful.
4. **Be concise but thorough.** Aim for roughly 400-800 words per table. Do not pad with filler.
5. **Use plain language.** Avoid jargon where possible. Write as if briefing a non-technical executive who needs to understand the data landscape.

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def _render_table_md(t: dict) -> str:
    """Render all profile data for one table as markdown."""
    parts = []
    name = t["name"]

    # --- Overview ---
    null_pct = t["total_nulls"] / t["total_cells"] * 100 if t["total_cells"] > 0 else 0
    type_counts = {}
    for p in t["profiles"]:
        ct = p["col_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1
    type_summary = ", ".join(f"{ct}: {n}" for ct, n in sorted(type_counts.items()))

    parts.append(f"## {name}\n")
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

    # --- Sample rows ---
    if t.get("sample_rows") is not None:
        df_sample = t["sample_rows"]
        n_rows = t["sample_count"]
        parts.append(f"### {name} — Sample Rows (first {n_rows})\n")
        for r in range(n_rows):
            parts.append(f"**Row {r+1}:**")
            for col in df_sample.columns:
                val = str(df_sample[col].iloc[r])[:60]
                parts.append(f"  {col}: {val}")
            parts.append("")

    parts.append("---\n")
    return "\n".join(parts)
