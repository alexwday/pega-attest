"""
Generates a single self-contained HTML report for EDA.
No external dependencies — just open in a browser.
"""
import html
from datetime import datetime


def _esc(val):
    """HTML-escape a value."""
    return html.escape(str(val))


def _bar_width(count, max_count):
    """Calculate CSS width percentage for an inline bar."""
    if max_count == 0:
        return 0
    return max(1, int(count / max_count * 100))


def generate_report(data_profiles: dict | None, user_profiles: dict | None) -> str:
    """
    Generate full HTML report.

    Each *_profiles dict has keys:
        name, rows, cols, memory_mb, duplicated_rows,
        total_nulls, total_cells, profiles, sample_html
    """
    sections = []
    nav_items = []

    for table in [data_profiles, user_profiles]:
        if table is None:
            continue
        prefix = table["name"].lower().replace(" ", "-")
        sections.append(_render_table_section(table, prefix))
        nav_items.append(
            f'<a href="#{prefix}-overview">{_esc(table["name"])}</a>'
        )

    nav_html = " | ".join(nav_items) if nav_items else ""
    body = "\n".join(sections)

    return _TEMPLATE.replace("{{NAV}}", nav_html).replace("{{BODY}}", body)


def _render_table_section(t: dict, prefix: str) -> str:
    """Render all sections for one table."""
    parts = []

    # Overview
    type_counts = {}
    for p in t["profiles"]:
        ct = p["col_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1
    type_lines = "  ".join(f'<span class="badge">{ct}: {n}</span>' for ct, n in sorted(type_counts.items()))

    null_pct = t["total_nulls"] / t["total_cells"] * 100 if t["total_cells"] > 0 else 0
    parts.append(f'''
    <section id="{prefix}-overview">
        <h2>{_esc(t["name"])} — Overview</h2>
        <div class="stats-grid">
            <div class="stat"><span class="stat-val">{t["rows"]:,}</span><span class="stat-lbl">Rows</span></div>
            <div class="stat"><span class="stat-val">{t["cols"]}</span><span class="stat-lbl">Columns</span></div>
            <div class="stat"><span class="stat-val">{t["memory_mb"]:.1f} MB</span><span class="stat-lbl">Memory</span></div>
            <div class="stat"><span class="stat-val">{t["duplicated_rows"]:,}</span><span class="stat-lbl">Duplicate Rows</span></div>
            <div class="stat"><span class="stat-val">{t["total_nulls"]:,} ({null_pct:.1f}%)</span><span class="stat-lbl">Null Cells</span></div>
        </div>
        <p style="margin-top:12px">{type_lines}</p>
    </section>
    ''')

    # Schema table
    schema_rows = []
    for i, p in enumerate(t["profiles"]):
        bg = ' class="even"' if i % 2 == 0 else ""
        top_val = ""
        if p["top_values"]:
            val, cnt = p["top_values"][0]
            val_display = val[:40] + "..." if len(val) > 40 else val
            top_val = f"{_esc(val_display)} ({cnt:,})"

        null_cls = ""
        if p["null_pct"] > 50:
            null_cls = ' class="null-high"'
        elif p["null_pct"] > 0:
            null_cls = ' class="null-mid"'

        schema_rows.append(f'''<tr{bg}>
            <td class="num">{i+1}</td>
            <td class="col-name">{_esc(p["name"])}</td>
            <td>{p["col_type"]}</td>
            <td class="mono">{_esc(p["dtype"][:12])}</td>
            <td class="num">{p["non_null"]:,}</td>
            <td{null_cls}>{p["null_pct"]}%</td>
            <td class="num">{p["n_unique"]:,}</td>
            <td class="mono top-val">{top_val}</td>
        </tr>''')

    parts.append(f'''
    <section id="{prefix}-schema">
        <h2>{_esc(t["name"])} — Schema</h2>
        <table class="schema-table">
            <thead><tr>
                <th>#</th><th>Column</th><th>Type</th><th>Dtype</th>
                <th>Non-Null</th><th>Null%</th><th>Unique</th><th>Top Value (count)</th>
            </tr></thead>
            <tbody>{"".join(schema_rows)}</tbody>
        </table>
    </section>
    ''')

    # Distributions — compact cards, 3 per row
    categoricals = [p for p in t["profiles"]
                    if p["col_type"] in ("categorical", "boolean") and p["top_values"]]
    if categoricals:
        cards = []
        for p in categoricals:
            max_count = p["top_values"][0][1] if p["top_values"] else 1
            bar_rows = []
            for val, cnt in p["top_values"][:15]:
                pct = cnt / p["non_null"] * 100 if p["non_null"] > 0 else 0
                w = _bar_width(cnt, max_count)
                val_display = val[:30] + "..." if len(val) > 30 else val
                bar_rows.append(
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{_esc(val_display)}</span>'
                    f'<span class="bar-track"><span class="bar-fill" style="width:{w}%"></span></span>'
                    f'<span class="bar-count">{cnt:,} ({pct:.0f}%)</span>'
                    f'</div>'
                )
            bars_html = "".join(bar_rows)
            cards.append(
                f'<div class="dist-card">'
                f'<div class="dist-header">{_esc(p["name"])}'
                f'<span class="dist-meta">{p["n_unique"]} unique · {p["null_pct"]}% null</span></div>'
                f'{bars_html}'
                f'</div>'
            )

        parts.append(f'''
        <section id="{prefix}-distributions">
            <h2>{_esc(t["name"])} — Value Distributions</h2>
            <div class="dist-grid">{"".join(cards)}</div>
        </section>
        ''')

    # Numeric summary
    numerics = [p for p in t["profiles"] if p["col_type"] == "numeric"]
    if numerics:
        num_rows = []
        for i, p in enumerate(numerics):
            bg = ' class="even"' if i % 2 == 0 else ""
            def fmt(v):
                if abs(v) >= 1000:
                    return f"{v:,.1f}"
                return f"{v:.4g}"
            num_rows.append(f'''<tr{bg}>
                <td class="col-name">{_esc(p["name"])}</td>
                <td class="num">{p["non_null"]:,}</td>
                <td class="num">{p["null_pct"]}%</td>
                <td class="num">{fmt(p.get("min", 0))}</td>
                <td class="num">{fmt(p.get("max", 0))}</td>
                <td class="num">{fmt(p.get("mean", 0))}</td>
                <td class="num">{fmt(p.get("median", 0))}</td>
                <td class="num">{fmt(p.get("std", 0))}</td>
            </tr>''')

        parts.append(f'''
        <section id="{prefix}-numeric">
            <h2>{_esc(t["name"])} — Numeric Summary</h2>
            <table class="schema-table">
                <thead><tr>
                    <th>Column</th><th>Non-Null</th><th>Null%</th>
                    <th>Min</th><th>Max</th><th>Mean</th><th>Median</th><th>Std</th>
                </tr></thead>
                <tbody>{"".join(num_rows)}</tbody>
            </table>
        </section>
        ''')

    # Date summary
    dates = [p for p in t["profiles"] if p["col_type"] == "date"]
    if dates:
        date_rows = []
        for i, p in enumerate(dates):
            bg = ' class="even"' if i % 2 == 0 else ""
            date_rows.append(f'''<tr{bg}>
                <td class="col-name">{_esc(p["name"])}</td>
                <td class="num">{p["non_null"]:,}</td>
                <td class="num">{p["null_pct"]}%</td>
                <td class="num">{p["n_unique"]:,}</td>
                <td class="mono">{_esc(p.get("date_min", "N/A"))}</td>
                <td class="mono">{_esc(p.get("date_max", "N/A"))}</td>
            </tr>''')

        parts.append(f'''
        <section id="{prefix}-dates">
            <h2>{_esc(t["name"])} — Date Columns</h2>
            <table class="schema-table">
                <thead><tr>
                    <th>Column</th><th>Non-Null</th><th>Null%</th>
                    <th>Unique</th><th>Min</th><th>Max</th>
                </tr></thead>
                <tbody>{"".join(date_rows)}</tbody>
            </table>
        </section>
        ''')

    # Sample rows
    if t.get("sample_html"):
        parts.append(f'''
        <section id="{prefix}-samples">
            <h2>{_esc(t["name"])} — Sample Rows (first {t.get("sample_count", "?")})</h2>
            {t["sample_html"]}
        </section>
        ''')

    return "\n".join(parts)


def build_sample_html(df, n_rows: int) -> str:
    """Build transposed sample rows as an HTML table."""
    import pandas as pd
    n_rows = min(n_rows, len(df))
    sample = df.head(n_rows)

    rows = []
    for i, col in enumerate(df.columns):
        bg = ' class="even"' if i % 2 == 0 else ""
        cells = "".join(
            f"<td class='mono'>{_esc(str(sample[col].iloc[r])[:45])}</td>"
            for r in range(n_rows)
        )
        rows.append(f"<tr{bg}><td class='col-name'>{_esc(str(col))}</td>{cells}</tr>")

    headers = "".join(f"<th>Row {r+1}</th>" for r in range(n_rows))
    return (
        f'<table class="schema-table sample-table">'
        f'<thead><tr><th>Column</th>{headers}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


# ---- HTML Template ----

_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pega Attestations — EDA Report</title>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #f5f6fa; color: #2c3e50; line-height: 1.5;
    }
    nav {
        position: sticky; top: 0; z-index: 100;
        background: #2c3e50; padding: 10px 24px;
        display: flex; gap: 16px; align-items: center; flex-wrap: wrap;
    }
    nav a { color: #ecf0f1; text-decoration: none; font-size: 14px; }
    nav a:hover { text-decoration: underline; }
    nav .title { font-weight: bold; font-size: 16px; color: #fff; margin-right: 24px; }
    nav .gen { color: #95a5a6; font-size: 12px; margin-left: auto; }

    section {
        background: #fff; margin: 16px 24px; padding: 24px;
        border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    h2 {
        font-size: 18px; margin-bottom: 16px; padding-bottom: 8px;
        border-bottom: 2px solid #3498db; color: #2c3e50;
    }

    /* Stats grid */
    .stats-grid { display: flex; gap: 16px; flex-wrap: wrap; }
    .stat {
        background: #f8f9fa; padding: 12px 20px; border-radius: 6px;
        border-left: 4px solid #3498db;
    }
    .stat-val { display: block; font-size: 20px; font-weight: bold; font-family: monospace; }
    .stat-lbl { font-size: 12px; color: #95a5a6; text-transform: uppercase; }
    .badge {
        display: inline-block; background: #eee; padding: 2px 10px;
        border-radius: 12px; font-size: 13px; margin: 2px;
    }

    /* Tables */
    .schema-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .schema-table th {
        background: #2c3e50; color: #fff; padding: 8px 10px;
        text-align: left; font-weight: 600; position: sticky; top: 48px;
    }
    .schema-table td { padding: 6px 10px; border-bottom: 1px solid #eee; }
    .schema-table tr.even td { background: #f8f9fa; }
    .schema-table .num { text-align: right; }
    .schema-table .mono { font-family: monospace; font-size: 12px; }
    .schema-table .col-name { font-weight: 600; white-space: nowrap; }
    .schema-table .top-val { max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
    .null-high { color: #e74c3c; font-weight: bold; }
    .null-mid { color: #e67e22; }

    .sample-table { font-size: 12px; }
    .sample-table td { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    /* Distribution cards */
    .dist-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 16px; }
    .dist-card {
        background: #f8f9fa; border-radius: 6px; padding: 12px;
        border: 1px solid #e0e0e0;
    }
    .dist-header {
        font-weight: 700; font-size: 14px; margin-bottom: 8px;
        padding-bottom: 6px; border-bottom: 1px solid #ddd;
    }
    .dist-meta { font-weight: 400; font-size: 11px; color: #95a5a6; margin-left: 8px; }
    .bar-row { display: flex; align-items: center; margin: 3px 0; font-size: 12px; }
    .bar-label {
        width: 130px; min-width: 130px; text-align: right; padding-right: 8px;
        font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .bar-track {
        flex: 1; height: 16px; background: #e8e8e8; border-radius: 3px; overflow: hidden;
    }
    .bar-fill { display: block; height: 100%; background: #3498db; border-radius: 3px; }
    .bar-count {
        width: 100px; min-width: 100px; text-align: right; padding-left: 8px;
        font-family: monospace; font-size: 11px; color: #666;
    }

    /* Keyboard nav hint */
    .nav-hint {
        position: fixed; bottom: 16px; right: 16px; background: #2c3e50;
        color: #fff; padding: 8px 14px; border-radius: 6px; font-size: 12px;
        opacity: 0.8;
    }
    .nav-hint kbd {
        background: #4a6785; padding: 1px 6px; border-radius: 3px;
        font-family: monospace;
    }
</style>
</head>
<body>
<nav>
    <span class="title">Pega Attestations EDA</span>
    {{NAV}}
    <span class="gen">''' + datetime.now().strftime('%Y-%m-%d %H:%M') + '''</span>
</nav>

{{BODY}}

<div class="nav-hint"><kbd>&uarr;</kbd> <kbd>&darr;</kbd> scroll &nbsp; | &nbsp; <kbd>J</kbd> <kbd>K</kbd> next/prev section</div>

<script>
// Keyboard navigation between sections
const sections = document.querySelectorAll('section');
document.addEventListener('keydown', (e) => {
    if (e.key === 'j' || e.key === 'k') {
        const scrollY = window.scrollY + 60;
        let target = null;
        if (e.key === 'j') {
            for (const s of sections) { if (s.offsetTop > scrollY + 10) { target = s; break; } }
        } else {
            for (let i = sections.length - 1; i >= 0; i--) {
                if (sections[i].offsetTop < scrollY - 10) { target = sections[i]; break; }
            }
        }
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});
</script>
</body>
</html>'''
