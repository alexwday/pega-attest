"""
Generates a single self-contained HTML slideshow report for EDA.
Each section is a full-viewport slide — one photo per slide.
Arrow keys to navigate between slides.
"""
import html
from datetime import datetime

# How many distribution cards fit on one slide
DIST_CARDS_PER_SLIDE = 6
# How many schema rows fit on one slide
SCHEMA_ROWS_PER_SLIDE = 18
# How many sample columns fit on one slide
SAMPLE_COLS_PER_SLIDE = 20


def _esc(val):
    return html.escape(str(val))


def _bar_width(count, max_count):
    if max_count == 0:
        return 0
    return max(1, int(count / max_count * 100))


def generate_report(data_profiles: dict | None, user_profiles: dict | None) -> str:
    slides = []

    for table in [data_profiles, user_profiles]:
        if table is None:
            continue
        slides.extend(_render_table_slides(table))

    total = len(slides)
    slides_html = []
    for i, (title, content) in enumerate(slides):
        slides_html.append(
            f'<div class="slide" id="slide-{i}">'
            f'<div class="slide-header">'
            f'<span class="page-num">Page {i+1} / {total}</span>'
            f'<span class="slide-title">{title}</span>'
            f'</div>'
            f'<div class="slide-body">{content}</div>'
            f'</div>'
        )

    body = "\n".join(slides_html)
    return _TEMPLATE.replace("{{SLIDES}}", body).replace("{{TOTAL}}", str(total))


def _render_table_slides(t: dict) -> list:
    """Returns list of (title, html_content) tuples — one per slide."""
    slides = []
    name = t["name"]

    # --- Slide: Overview ---
    type_counts = {}
    for p in t["profiles"]:
        ct = p["col_type"]
        type_counts[ct] = type_counts.get(ct, 0) + 1
    type_badges = "  ".join(
        f'<span class="badge">{ct}: {n}</span>'
        for ct, n in sorted(type_counts.items())
    )
    null_pct = t["total_nulls"] / t["total_cells"] * 100 if t["total_cells"] > 0 else 0

    # Column list in 3 columns
    cols = [p["name"] for p in t["profiles"]]
    col_len = (len(cols) + 2) // 3
    col_lists = ""
    for chunk_i in range(3):
        chunk = cols[chunk_i * col_len:(chunk_i + 1) * col_len]
        items = "".join(
            f'<div class="col-item">{chunk_i * col_len + j + 1}. {_esc(c)}</div>'
            for j, c in enumerate(chunk)
        )
        col_lists += f'<div class="col-list">{items}</div>'

    slides.append((f"{name} — Overview", f'''
        <div class="stats-grid">
            <div class="stat"><span class="stat-val">{t["rows"]:,}</span><span class="stat-lbl">Rows</span></div>
            <div class="stat"><span class="stat-val">{t["cols"]}</span><span class="stat-lbl">Columns</span></div>
            <div class="stat"><span class="stat-val">{t["memory_mb"]:.1f} MB</span><span class="stat-lbl">Memory</span></div>
            <div class="stat"><span class="stat-val">{t["duplicated_rows"]:,}</span><span class="stat-lbl">Duplicate Rows</span></div>
            <div class="stat"><span class="stat-val">{t["total_nulls"]:,} ({null_pct:.1f}%)</span><span class="stat-lbl">Null Cells</span></div>
        </div>
        <div style="margin-top:12px">{type_badges}</div>
        <h3 style="margin-top:16px;font-size:14px;color:#666">All Columns</h3>
        <div class="col-grid">{col_lists}</div>
    '''))

    # --- Slides: Schema (paginated) ---
    profiles = t["profiles"]
    total_schema = (len(profiles) + SCHEMA_ROWS_PER_SLIDE - 1) // SCHEMA_ROWS_PER_SLIDE
    for page_i in range(total_schema):
        start = page_i * SCHEMA_ROWS_PER_SLIDE
        end = min(start + SCHEMA_ROWS_PER_SLIDE, len(profiles))
        chunk = profiles[start:end]

        rows_html = ""
        for i, p in enumerate(chunk):
            bg = ' class="even"' if i % 2 == 0 else ""
            top_val = ""
            if p["top_values"]:
                val, cnt = p["top_values"][0]
                vd = val[:40] + "..." if len(val) > 40 else val
                top_val = f"{_esc(vd)} ({cnt:,})"
            null_cls = ""
            if p["null_pct"] > 50:
                null_cls = ' class="null-high"'
            elif p["null_pct"] > 0:
                null_cls = ' class="null-mid"'

            rows_html += f'''<tr{bg}>
                <td class="num">{start+i+1}</td>
                <td class="col-name">{_esc(p["name"])}</td>
                <td>{p["col_type"]}</td>
                <td class="mono">{_esc(p["dtype"][:12])}</td>
                <td class="num">{p["non_null"]:,}</td>
                <td{null_cls}>{p["null_pct"]}%</td>
                <td class="num">{p["n_unique"]:,}</td>
                <td class="mono top-val">{top_val}</td>
            </tr>'''

        pg_label = f" ({page_i+1}/{total_schema})" if total_schema > 1 else ""
        slides.append((f"{name} — Schema{pg_label}", f'''
            <table class="data-table">
                <thead><tr>
                    <th>#</th><th>Column</th><th>Type</th><th>Dtype</th>
                    <th>Non-Null</th><th>Null%</th><th>Unique</th><th>Top Value (count)</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        '''))

    # --- Slides: Distributions (paginated, N cards per slide) ---
    categoricals = [p for p in profiles
                    if p["col_type"] in ("categorical", "boolean") and p["top_values"]]
    if categoricals:
        total_dist = (len(categoricals) + DIST_CARDS_PER_SLIDE - 1) // DIST_CARDS_PER_SLIDE
        for page_i in range(total_dist):
            start = page_i * DIST_CARDS_PER_SLIDE
            end = min(start + DIST_CARDS_PER_SLIDE, len(categoricals))
            chunk = categoricals[start:end]

            cards = ""
            for p in chunk:
                max_count = p["top_values"][0][1] if p["top_values"] else 1
                bars = ""
                for val, cnt in p["top_values"][:10]:
                    pct = cnt / p["non_null"] * 100 if p["non_null"] > 0 else 0
                    w = _bar_width(cnt, max_count)
                    vd = val[:28] + ".." if len(val) > 28 else val
                    bars += (
                        f'<div class="bar-row">'
                        f'<span class="bar-label">{_esc(vd)}</span>'
                        f'<span class="bar-track"><span class="bar-fill" style="width:{w}%"></span></span>'
                        f'<span class="bar-count">{cnt:,} ({pct:.0f}%)</span>'
                        f'</div>'
                    )
                cards += (
                    f'<div class="dist-card">'
                    f'<div class="dist-header">{_esc(p["name"])}'
                    f'<span class="dist-meta">{p["n_unique"]} unique · {p["null_pct"]}% null</span></div>'
                    f'{bars}</div>'
                )

            pg_label = f" ({page_i+1}/{total_dist})" if total_dist > 1 else ""
            slides.append((f"{name} — Distributions{pg_label}",
                           f'<div class="dist-grid">{cards}</div>'))

    # --- Slide: Numeric summary ---
    numerics = [p for p in profiles if p["col_type"] == "numeric"]
    if numerics:
        rows_html = ""
        for i, p in enumerate(numerics):
            bg = ' class="even"' if i % 2 == 0 else ""
            def fmt(v):
                if abs(v) >= 1000:
                    return f"{v:,.1f}"
                return f"{v:.4g}"
            rows_html += f'''<tr{bg}>
                <td class="col-name">{_esc(p["name"])}</td>
                <td class="num">{p["non_null"]:,}</td>
                <td class="num">{p["null_pct"]}%</td>
                <td class="num">{fmt(p.get("min", 0))}</td>
                <td class="num">{fmt(p.get("max", 0))}</td>
                <td class="num">{fmt(p.get("mean", 0))}</td>
                <td class="num">{fmt(p.get("median", 0))}</td>
                <td class="num">{fmt(p.get("std", 0))}</td>
            </tr>'''
        slides.append((f"{name} — Numeric Summary", f'''
            <table class="data-table">
                <thead><tr>
                    <th>Column</th><th>Non-Null</th><th>Null%</th>
                    <th>Min</th><th>Max</th><th>Mean</th><th>Median</th><th>Std</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        '''))

    # --- Slide: Date summary ---
    dates = [p for p in profiles if p["col_type"] == "date"]
    if dates:
        rows_html = ""
        for i, p in enumerate(dates):
            bg = ' class="even"' if i % 2 == 0 else ""
            rows_html += f'''<tr{bg}>
                <td class="col-name">{_esc(p["name"])}</td>
                <td class="num">{p["non_null"]:,}</td>
                <td class="num">{p["null_pct"]}%</td>
                <td class="num">{p["n_unique"]:,}</td>
                <td class="mono">{_esc(p.get("date_min", "N/A"))}</td>
                <td class="mono">{_esc(p.get("date_max", "N/A"))}</td>
            </tr>'''
        slides.append((f"{name} — Date Columns", f'''
            <table class="data-table">
                <thead><tr>
                    <th>Column</th><th>Non-Null</th><th>Null%</th>
                    <th>Unique</th><th>Min</th><th>Max</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        '''))

    # --- Slides: Sample rows (paginated) ---
    if t.get("sample_rows") is not None:
        df_sample = t["sample_rows"]
        n_rows = t["sample_count"]
        all_cols = list(df_sample.columns)
        total_sample = (len(all_cols) + SAMPLE_COLS_PER_SLIDE - 1) // SAMPLE_COLS_PER_SLIDE

        for page_i in range(total_sample):
            start = page_i * SAMPLE_COLS_PER_SLIDE
            end = min(start + SAMPLE_COLS_PER_SLIDE, len(all_cols))
            page_cols = all_cols[start:end]

            headers = "".join(f"<th>Row {r+1}</th>" for r in range(n_rows))
            rows_html = ""
            for i, col in enumerate(page_cols):
                bg = ' class="even"' if i % 2 == 0 else ""
                cells = "".join(
                    f"<td class='mono'>{_esc(str(df_sample[col].iloc[r])[:40])}</td>"
                    for r in range(n_rows)
                )
                rows_html += f"<tr{bg}><td class='col-name'>{_esc(str(col))}</td>{cells}</tr>"

            pg_label = f" ({page_i+1}/{total_sample})" if total_sample > 1 else ""
            col_range = f"columns {start+1}-{end} of {len(all_cols)}"
            slides.append((f"{name} — Sample Rows{pg_label}", f'''
                <p style="color:#666;font-size:12px;margin-bottom:8px">First {n_rows} rows, {col_range}</p>
                <table class="data-table sample-table">
                    <thead><tr><th>Column</th>{headers}</tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            '''))

    return slides


def build_sample_data(df, n_rows: int) -> tuple:
    """Return (sample_df, actual_row_count) for use in slides."""
    n_rows = min(n_rows, len(df))
    sample = df.head(n_rows).copy()
    for col in sample.columns:
        if sample[col].dtype == object:
            sample[col] = sample[col].astype(str).str[:40]
    return sample, n_rows


# Kept for backwards compat but not used in slideshow mode
def build_sample_html(df, n_rows: int) -> str:
    return ""


_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pega Attestations — EDA Report</title>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { height: 100%; overflow: hidden; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: #1a1a2e; color: #2c3e50;
    }

    /* Slide container */
    .slide {
        display: none; position: absolute; top: 0; left: 0;
        width: 100%; height: 100%;
        background: #fff;
        flex-direction: column;
    }
    .slide.active { display: flex; }

    .slide-header {
        background: #2c3e50; padding: 12px 24px;
        display: flex; align-items: center; gap: 20px;
        flex-shrink: 0;
    }
    .page-num {
        font-family: monospace; font-size: 14px; color: #95a5a6;
        font-weight: bold; min-width: 100px;
    }
    .slide-title { font-size: 18px; font-weight: 700; color: #fff; }

    .slide-body {
        flex: 1; padding: 20px 24px; overflow: auto;
        line-height: 1.5;
    }

    /* Stats */
    .stats-grid { display: flex; gap: 14px; flex-wrap: wrap; }
    .stat {
        background: #f8f9fa; padding: 14px 22px; border-radius: 6px;
        border-left: 4px solid #3498db;
    }
    .stat-val { display: block; font-size: 22px; font-weight: bold; font-family: monospace; }
    .stat-lbl { font-size: 11px; color: #95a5a6; text-transform: uppercase; }
    .badge {
        display: inline-block; background: #eee; padding: 2px 10px;
        border-radius: 12px; font-size: 13px; margin: 2px;
    }
    .col-grid { display: flex; gap: 8px; margin-top: 8px; }
    .col-list { flex: 1; }
    .col-item { font-family: monospace; font-size: 12px; padding: 1px 0; color: #444; }

    /* Tables */
    .data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .data-table th {
        background: #2c3e50; color: #fff; padding: 7px 10px;
        text-align: left; font-weight: 600; position: sticky; top: 0;
    }
    .data-table td { padding: 5px 10px; border-bottom: 1px solid #eee; }
    .data-table tr.even td { background: #f8f9fa; }
    .data-table .num { text-align: right; }
    .data-table .mono { font-family: monospace; font-size: 12px; }
    .data-table .col-name { font-weight: 600; white-space: nowrap; }
    .data-table .top-val { max-width: 320px; overflow: hidden; text-overflow: ellipsis; }
    .null-high { color: #e74c3c; font-weight: bold; }
    .null-mid { color: #e67e22; }
    .sample-table td { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sample-table { font-size: 12px; }

    /* Distribution cards */
    .dist-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
        gap: 14px;
    }
    .dist-card {
        background: #f8f9fa; border-radius: 6px; padding: 10px 12px;
        border: 1px solid #e0e0e0;
    }
    .dist-header {
        font-weight: 700; font-size: 13px; margin-bottom: 6px;
        padding-bottom: 5px; border-bottom: 1px solid #ddd;
    }
    .dist-meta { font-weight: 400; font-size: 11px; color: #95a5a6; margin-left: 8px; }
    .bar-row { display: flex; align-items: center; margin: 2px 0; font-size: 11px; }
    .bar-label {
        width: 120px; min-width: 120px; text-align: right; padding-right: 6px;
        font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .bar-track {
        flex: 1; height: 14px; background: #e8e8e8; border-radius: 3px; overflow: hidden;
    }
    .bar-fill { display: block; height: 100%; background: #3498db; border-radius: 3px; }
    .bar-count {
        width: 90px; min-width: 90px; text-align: right; padding-left: 6px;
        font-family: monospace; font-size: 10px; color: #666;
    }

    /* Navigation controls */
    .nav-bar {
        background: #2c3e50; padding: 8px 24px;
        display: flex; align-items: center; justify-content: center; gap: 16px;
        flex-shrink: 0; border-top: 1px solid #34495e;
    }
    .nav-bar button {
        background: #3498db; color: #fff; border: none; padding: 8px 20px;
        border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: 600;
    }
    .nav-bar button:hover { background: #2980b9; }
    .nav-bar button:disabled { background: #555; cursor: default; }
    .nav-bar .nav-info { color: #95a5a6; font-size: 13px; min-width: 200px; text-align: center; }
    .nav-bar kbd {
        background: #4a6785; padding: 1px 5px; border-radius: 3px;
        font-family: monospace; font-size: 11px; color: #ccc;
    }
    h3 { font-size: 14px; color: #666; }
</style>
</head>
<body>

{{SLIDES}}

<div class="nav-bar">
    <button id="btn-prev" onclick="go(-1)">&larr; Prev</button>
    <span class="nav-info">
        <span id="nav-current">1</span> / <span id="nav-total">{{TOTAL}}</span>
        &nbsp;&nbsp; <kbd>&larr;</kbd> <kbd>&rarr;</kbd> to navigate
    </span>
    <button id="btn-next" onclick="go(1)">Next &rarr;</button>
</div>

<script>
const slides = document.querySelectorAll('.slide');
let current = 0;

function show(idx) {
    slides.forEach(s => s.classList.remove('active'));
    current = Math.max(0, Math.min(idx, slides.length - 1));
    slides[current].classList.add('active');
    document.getElementById('nav-current').textContent = current + 1;
    document.getElementById('btn-prev').disabled = current === 0;
    document.getElementById('btn-next').disabled = current === slides.length - 1;
}

function go(delta) { show(current + delta); }

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); go(1); }
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); go(-1); }
});

show(0);
</script>
</body>
</html>'''
