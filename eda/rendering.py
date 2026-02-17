"""
PNG report page rendering.
Generates large, clear images designed to be photographed from a screen.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime


# -- Color palette --
HEADER_BG = "#2c3e50"
HEADER_TEXT = "#ffffff"
ROW_EVEN = "#f8f9fa"
ROW_ODD = "#ffffff"
ACCENT = "#3498db"
ACCENT_DARK = "#2980b9"
MUTED = "#95a5a6"
TEXT_DARK = "#2c3e50"
BAR_COLOR = "#3498db"
BAR_ALT = "#e74c3c"

PAGE_W = 18
PAGE_H = 11


class ReportRenderer:
    """Generates numbered PNG report pages."""

    def __init__(self, output_dir: Path, prefix: str, dpi: int = 150):
        self.output_dir = output_dir
        self.prefix = prefix
        self.dpi = dpi
        self.page_counter = 0
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _new_page(self, title: str, subtitle: str = ""):
        self.page_counter += 1
        fig = plt.figure(figsize=(PAGE_W, PAGE_H), facecolor="white")

        # Header bar
        fig.patches.append(FancyBboxPatch(
            (0.01, 0.93), 0.98, 0.06,
            boxstyle="round,pad=0.005",
            facecolor=HEADER_BG, edgecolor="none",
            transform=fig.transFigure, figure=fig,
        ))
        fig.text(0.03, 0.955, f"Page {self.page_counter:02d}",
                 fontsize=13, color=MUTED, fontweight="bold", fontfamily="monospace")
        fig.text(0.09, 0.955, title,
                 fontsize=17, color=HEADER_TEXT, fontweight="bold")
        if subtitle:
            fig.text(0.09, 0.935, subtitle,
                     fontsize=11, color=MUTED)

        # Footer
        fig.text(0.5, 0.008,
                 f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Pega Attestations EDA",
                 fontsize=8, color=MUTED, ha="center")

        return fig

    def _save(self, fig, tag: str):
        fname = f"{self.prefix}_{self.page_counter:02d}_{tag}.png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        print(f"    Saved: {fname}")
        return path

    # ----------------------------------------------------------------
    # Page types
    # ----------------------------------------------------------------

    def render_overview(self, table_name: str, filepath: str, df: pd.DataFrame,
                        n_profiles: list):
        """Page 1: high-level overview of the table."""
        fig = self._new_page(f"OVERVIEW: {table_name}", filepath)

        type_counts = {}
        for p in n_profiles:
            t = p["col_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        lines = [
            f"Rows:            {len(df):,}",
            f"Columns:         {len(df.columns)}",
            f"Memory:          {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB",
            "",
            "Column types:",
        ]
        for t, c in sorted(type_counts.items()):
            lines.append(f"  {t:<16} {c}")
        lines += [
            "",
            f"Duplicated rows: {df.duplicated().sum():,}",
        ]
        total_nulls = df.isna().sum().sum()
        total_cells = df.shape[0] * df.shape[1]
        lines.append(f"Total null cells: {total_nulls:,} / {total_cells:,}  "
                      f"({total_nulls/total_cells*100:.1f}%)")

        fig.text(0.05, 0.88, "\n".join(lines),
                 fontsize=16, fontfamily="monospace", color=TEXT_DARK,
                 verticalalignment="top", linespacing=1.6)

        # Column list (compact, multi-column)
        cols = list(df.columns)
        n_cols_display = 3
        col_len = (len(cols) + n_cols_display - 1) // n_cols_display
        fig.text(0.05, 0.42, "All columns:", fontsize=14,
                 fontweight="bold", color=TEXT_DARK)
        for i in range(n_cols_display):
            chunk = cols[i * col_len:(i + 1) * col_len]
            text = "\n".join(f"  {j + i * col_len + 1:>3}. {c}" for j, c in enumerate(chunk))
            fig.text(0.05 + i * 0.33, 0.39, text,
                     fontsize=11, fontfamily="monospace", color=TEXT_DARK,
                     verticalalignment="top", linespacing=1.4)

        return self._save(fig, "overview")

    def render_schema_page(self, table_name: str, profiles: list,
                           descriptions: dict, page_num: int, total_pages: int):
        """Schema detail page — shows column metadata in a table."""
        fig = self._new_page(
            f"SCHEMA: {table_name}",
            f"Page {page_num}/{total_pages}"
        )
        ax = fig.add_axes([0.03, 0.04, 0.94, 0.86])
        ax.axis("off")

        # Table header
        headers = ["#", "Column Name", "Type", "Dtype", "Non-Null", "Null%",
                    "Unique", "Top Value (count)", "Description"]
        col_widths = [0.03, 0.16, 0.07, 0.07, 0.06, 0.05, 0.05, 0.25, 0.26]

        n_rows = len(profiles) + 1  # +1 for header
        row_height = min(0.07, 0.92 / n_rows)

        for col_i, (header, width) in enumerate(zip(headers, col_widths)):
            x = sum(col_widths[:col_i])
            # Header cell
            ax.add_patch(plt.Rectangle((x, 1 - row_height), width, row_height,
                                       facecolor=HEADER_BG, edgecolor="white", lw=0.5))
            ax.text(x + width / 2, 1 - row_height / 2, header,
                    ha="center", va="center", fontsize=10,
                    fontweight="bold", color=HEADER_TEXT)

        # Data rows
        for row_i, p in enumerate(profiles):
            y = 1 - (row_i + 2) * row_height
            bg = ROW_EVEN if row_i % 2 == 0 else ROW_ODD

            desc = descriptions.get(p["name"], "")
            if len(desc) > 45:
                desc = desc[:42] + "..."

            top_val = ""
            if p["top_values"]:
                val, cnt = p["top_values"][0]
                if len(val) > 30:
                    val = val[:27] + "..."
                top_val = f"{val} ({cnt:,})"

            cells = [
                str(row_i + 1),
                p["name"][:25],
                p["col_type"],
                p["dtype"][:10],
                f"{p['non_null']:,}",
                f"{p['null_pct']}%",
                f"{p['n_unique']:,}",
                top_val,
                desc,
            ]

            for col_i, (cell, width) in enumerate(zip(cells, col_widths)):
                x = sum(col_widths[:col_i])
                ax.add_patch(plt.Rectangle((x, y), width, row_height,
                                           facecolor=bg, edgecolor="#dee2e6", lw=0.5))
                ha = "center" if col_i < 7 else "left"
                x_text = x + width / 2 if col_i < 7 else x + 0.005
                ax.text(x_text, y + row_height / 2, cell,
                        ha=ha, va="center", fontsize=9,
                        fontfamily="monospace", color=TEXT_DARK)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return self._save(fig, f"schema_{page_num}")

    def render_null_analysis(self, table_name: str, profiles: list):
        """Bar chart of null percentages for all columns."""
        fig = self._new_page(f"NULL ANALYSIS: {table_name}")
        ax = fig.add_axes([0.18, 0.06, 0.78, 0.84])

        names = [p["name"] for p in profiles]
        nulls = [p["null_pct"] for p in profiles]

        # Sort by null pct descending
        sorted_pairs = sorted(zip(names, nulls), key=lambda x: x[1], reverse=True)
        names = [p[0] for p in sorted_pairs]
        nulls = [p[1] for p in sorted_pairs]

        colors = [BAR_ALT if n > 50 else ACCENT if n > 0 else MUTED for n in nulls]

        y_pos = range(len(names))
        ax.barh(y_pos, nulls, color=colors, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=8, fontfamily="monospace")
        ax.set_xlabel("Null %", fontsize=12)
        ax.set_xlim(0, max(max(nulls) * 1.1, 1))
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

        # Value labels
        for i, v in enumerate(nulls):
            if v > 0:
                ax.text(v + 0.5, i, f"{v}%", va="center", fontsize=8, color=TEXT_DARK)

        return self._save(fig, "nulls")

    def render_categorical_distribution(self, table_name: str, profile: dict,
                                        description: str = ""):
        """Bar chart for a single categorical column."""
        fig = self._new_page(
            f"DISTRIBUTION: {profile['name']}",
            f"{table_name} | Type: {profile['col_type']} | "
            f"Unique: {profile['n_unique']} | Null: {profile['null_pct']}%"
        )

        if description:
            fig.text(0.05, 0.91, f"Description: {description}",
                     fontsize=12, color=TEXT_DARK, style="italic")

        ax = fig.add_axes([0.25, 0.06, 0.70, 0.80])

        values = profile["top_values"]
        if not values:
            ax.text(0.5, 0.5, "No non-null values", ha="center", va="center",
                    fontsize=16, color=MUTED)
            return self._save(fig, f"cat_{profile['name'][:30]}")

        labels = [v[0] for v in values]
        counts = [v[1] for v in values]
        total_non_null = profile["non_null"]

        y_pos = range(len(labels))
        ax.barh(y_pos, counts, color=BAR_COLOR, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=10, fontfamily="monospace")
        ax.set_xlabel("Count", fontsize=12)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

        for i, v in enumerate(counts):
            pct = v / total_non_null * 100 if total_non_null > 0 else 0
            ax.text(v + max(counts) * 0.01, i, f"{v:,} ({pct:.1f}%)",
                    va="center", fontsize=9, color=TEXT_DARK)

        return self._save(fig, f"cat_{_safe_name(profile['name'])}")

    def render_numeric_summary(self, table_name: str, profiles: list):
        """Summary table for all numeric columns."""
        numeric = [p for p in profiles if p["col_type"] == "numeric"]
        if not numeric:
            return None

        fig = self._new_page(f"NUMERIC SUMMARY: {table_name}",
                             f"{len(numeric)} numeric columns")
        ax = fig.add_axes([0.03, 0.04, 0.94, 0.86])
        ax.axis("off")

        headers = ["Column", "Non-Null", "Min", "Max", "Mean", "Median", "Std Dev"]
        col_widths = [0.22, 0.1, 0.13, 0.13, 0.13, 0.13, 0.13]

        n_rows = len(numeric) + 1
        row_height = min(0.07, 0.92 / n_rows)

        for col_i, (header, width) in enumerate(zip(headers, col_widths)):
            x = sum(col_widths[:col_i])
            ax.add_patch(plt.Rectangle((x, 1 - row_height), width, row_height,
                                       facecolor=HEADER_BG, edgecolor="white", lw=0.5))
            ax.text(x + width / 2, 1 - row_height / 2, header,
                    ha="center", va="center", fontsize=11,
                    fontweight="bold", color=HEADER_TEXT)

        for row_i, p in enumerate(numeric):
            y = 1 - (row_i + 2) * row_height
            bg = ROW_EVEN if row_i % 2 == 0 else ROW_ODD

            def fmt_num(v):
                if abs(v) >= 1000:
                    return f"{v:,.1f}"
                return f"{v:.4g}"

            cells = [
                p["name"][:30],
                f"{p['non_null']:,}",
                fmt_num(p["min"]),
                fmt_num(p["max"]),
                fmt_num(p["mean"]),
                fmt_num(p["median"]),
                fmt_num(p["std"]),
            ]

            for col_i, (cell, width) in enumerate(zip(cells, col_widths)):
                x = sum(col_widths[:col_i])
                ax.add_patch(plt.Rectangle((x, y), width, row_height,
                                           facecolor=bg, edgecolor="#dee2e6", lw=0.5))
                ha = "left" if col_i == 0 else "center"
                x_text = x + 0.005 if col_i == 0 else x + width / 2
                ax.text(x_text, y + row_height / 2, cell,
                        ha=ha, va="center", fontsize=10,
                        fontfamily="monospace", color=TEXT_DARK)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        return self._save(fig, "numeric_summary")

    def render_date_summary(self, table_name: str, profiles: list):
        """Summary for all date columns."""
        dates = [p for p in profiles if p["col_type"] == "date"]
        if not dates:
            return None

        fig = self._new_page(f"DATE COLUMNS: {table_name}",
                             f"{len(dates)} date columns")

        lines = []
        for p in dates:
            lines.append(f"Column:   {p['name']}")
            lines.append(f"  Non-null: {p['non_null']:,}  |  Null: {p['null_pct']}%")
            lines.append(f"  Min:      {p.get('date_min', 'N/A')}")
            lines.append(f"  Max:      {p.get('date_max', 'N/A')}")
            lines.append(f"  Unique:   {p['n_unique']:,}")
            lines.append("")

        fig.text(0.05, 0.88, "\n".join(lines),
                 fontsize=14, fontfamily="monospace", color=TEXT_DARK,
                 verticalalignment="top", linespacing=1.5)

        return self._save(fig, "date_summary")

    def render_sample_rows(self, table_name: str, df: pd.DataFrame, n_rows: int):
        """
        Show first N rows transposed — each column as a row,
        with values for row 1, row 2, etc. as columns.
        Split across multiple pages if needed.
        """
        sample = df.head(n_rows)
        cols = list(df.columns)
        cols_per_page = 20
        pages = (len(cols) + cols_per_page - 1) // cols_per_page
        paths = []

        for page_i in range(pages):
            start = page_i * cols_per_page
            end = min(start + cols_per_page, len(cols))
            page_cols = cols[start:end]

            fig = self._new_page(
                f"SAMPLE ROWS: {table_name}",
                f"First {n_rows} rows (columns {start + 1}-{end} of {len(cols)})"
            )
            ax = fig.add_axes([0.02, 0.04, 0.96, 0.86])
            ax.axis("off")

            # Headers
            headers = ["Column"] + [f"Row {i + 1}" for i in range(n_rows)]
            n_data_cols = n_rows + 1
            col_widths = [0.20] + [0.80 / n_rows] * n_rows
            n_table_rows = len(page_cols) + 1
            row_height = min(0.055, 0.95 / n_table_rows)

            for col_i, (header, width) in enumerate(zip(headers, col_widths)):
                x = sum(col_widths[:col_i])
                ax.add_patch(plt.Rectangle((x, 1 - row_height), width, row_height,
                                           facecolor=HEADER_BG, edgecolor="white", lw=0.5))
                ax.text(x + width / 2, 1 - row_height / 2, header,
                        ha="center", va="center", fontsize=9,
                        fontweight="bold", color=HEADER_TEXT)

            for row_i, col_name in enumerate(page_cols):
                y = 1 - (row_i + 2) * row_height
                bg = ROW_EVEN if row_i % 2 == 0 else ROW_ODD

                cells = [col_name[:28]] + [
                    str(sample[col_name].iloc[i])[:25] for i in range(n_rows)
                ]

                for col_i, (cell, width) in enumerate(zip(cells, col_widths)):
                    x = sum(col_widths[:col_i])
                    ax.add_patch(plt.Rectangle((x, y), width, row_height,
                                               facecolor=bg, edgecolor="#dee2e6", lw=0.5))
                    ha = "left" if col_i == 0 else "center"
                    x_text = x + 0.005 if col_i == 0 else x + width / 2
                    ax.text(x_text, y + row_height / 2, cell,
                            ha=ha, va="center", fontsize=8,
                            fontfamily="monospace", color=TEXT_DARK)

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            paths.append(self._save(fig, f"samples_{page_i + 1}"))

        return paths

    def render_descriptions_page(self, table_name: str, descriptions: dict,
                                 columns: list):
        """Page showing column descriptions alongside column names."""
        # Only show descriptions for columns that exist in this table
        relevant = [(col, descriptions.get(col, "")) for col in columns]
        if not any(desc for _, desc in relevant):
            return None

        pages = []
        per_page = 25
        total_pages = (len(relevant) + per_page - 1) // per_page

        for page_i in range(total_pages):
            start = page_i * per_page
            end = min(start + per_page, len(relevant))
            chunk = relevant[start:end]

            fig = self._new_page(
                f"COLUMN DESCRIPTIONS: {table_name}",
                f"Page {page_i + 1}/{total_pages}"
            )

            lines = []
            for i, (col, desc) in enumerate(chunk):
                num = start + i + 1
                marker = " " if desc else "*"
                desc_text = desc if desc else "(no description)"
                lines.append(f" {num:>3}. {col:<35} {marker} {desc_text}")

            fig.text(0.04, 0.88, "\n".join(lines),
                     fontsize=11, fontfamily="monospace", color=TEXT_DARK,
                     verticalalignment="top", linespacing=1.4)

            if page_i == 0:
                fig.text(0.04, 0.04,
                         "* = no description provided in column_descriptions.txt",
                         fontsize=10, color=MUTED, style="italic")

            pages.append(self._save(fig, f"descriptions_{page_i + 1}"))

        return pages


def _safe_name(name: str) -> str:
    """Make a column name safe for use in filenames."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)[:30]
