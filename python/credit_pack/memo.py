"""Generate consistent Markdown and Word credit memos from calculated outputs."""

import math

import pandas as pd
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from . import config as cfg
from .config import C


def number(value, decimals=cfg.MONEY_DECIMALS) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (float, int)):
        return f"{value:,.{decimals}f}" if math.isfinite(value) else "unavailable"
    return str(value)


def display(value, column: str, record: dict, decimals=cfg.MONEY_DECIMALS) -> str:
    if column in (C.YEAR, C.GRADE, C.PRIOR_GRADE, C.CHANGE, C.MONTH, C.LOAN_COUNT, C.WATCH_COUNT):
        return str(int(value))
    if column == C.WEIGHT:
        return number(value, cfg.WEIGHT_DECIMALS)
    if column == C.VALUE and record.get(C.FACTOR) == C.MARGIN_STABILITY:
        return number(value, cfg.STABILITY_DECIMALS)
    if column == C.VALUE and record.get(C.METRIC) in cfg.PERCENTAGE_OUTPUT_METRICS:
        return f"{value:.2%}"
    return number(value, decimals)


def markdown_table(frame: pd.DataFrame, decimals=cfg.MONEY_DECIMALS) -> str:
    headers = list(frame.columns)
    lines = ["| " + " | ".join(str(header) for header in headers) + " |",
             "| " + " | ".join(":" + "-" * 2 for _ in headers) + " |"]
    lines.extend("| " + " | ".join(display(row[header], header, row, decimals) for header in headers) + " |"
                 for row in frame.to_dict("records"))
    return "\n".join(lines)


def document_style(document: Document) -> None:
    document.core_properties.author = cfg.AUTHOR
    document.core_properties.last_modified_by = cfg.AUTHOR
    for section in document.sections:
        section.top_margin = section.bottom_margin = Inches(cfg.DOC_MARGIN_INCHES)
        section.left_margin = section.right_margin = Inches(cfg.DOC_MARGIN_INCHES)
    normal = document.styles["Normal"]
    normal.font.name = cfg.DOC_FONT
    normal.font.size = Pt(cfg.DOC_FONT_SIZE)
    normal.paragraph_format.space_after = Pt(cfg.DOC_PARAGRAPH_SPACE)
    normal.paragraph_format.line_spacing = 1.0
    for name, size in cfg.DOC_HEADING_SIZES.items():
        style = document.styles[name]
        style.font.name = cfg.DOC_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = None
    document.styles["Title"].font.color.rgb = RGBColor(0, 0, 0)
    for border in list(document.styles.element.iter(qn("w:pBdr"))):
        border.getparent().remove(border)


def add_table(document: Document, frame: pd.DataFrame) -> None:
    table = document.add_table(rows=1, cols=len(frame.columns))
    table.style = "Table Grid"
    for cell, column in zip(table.rows[0].cells, frame.columns):
        cell.text = str(column).replace("_", " ")
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for record in frame.to_dict("records"):
        cells = table.add_row().cells
        for cell, column in zip(cells, frame.columns):
            cell.text = display(record[column], column, record)
            if column in (C.METRIC, C.FACTOR):
                cell.text = cell.text.replace("_", " ")
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(cfg.DOC_TABLE_SPACE)
                for run in paragraph.runs:
                    run.font.size = Pt(cfg.DOC_TABLE_SIZE)


def write_credit_memo(ticker: str, history: pd.DataFrame, rating: dict,
                      factors: pd.DataFrame, facility: dict, recommendation: str) -> None:
    latest = history.tail(1).to_dict("records")[0]
    assumptions = cfg.BORROWERS[ticker]
    title = f"{ticker} credit underwriting memo"
    document = Document()
    document_style(document)
    document.core_properties.title = title
    document.add_paragraph(title, "Title")
    markdown = [f"# {title}"]

    def paragraph(text):
        document.add_paragraph(text)
        markdown.append(text)

    def heading(text):
        document.add_heading(text, level=1)
        markdown.append(f"## {text}")

    def table(frame):
        add_table(document, frame)
        markdown.append(markdown_table(frame))

    paragraph(f"Recommendation: {recommendation}. Source: {latest[C.SOURCE]}. "
              "All policy judgments and proposed terms are illustrative. No real credit decision is made.")
    heading("Business and decision")
    paragraph(assumptions["summary"] + f" Industry: {assumptions[C.INDUSTRY]}.")
    paragraph(f"Obligor grade {rating[C.GRADE]}, illustrative PD {rating[C.PD]:.2%}, "
              f"classification {rating[C.CLASSIFICATION]}. Weighted score {rating[C.SCORE]:.2f}.")
    paragraph("Decision rule: decline for incomplete required inputs, a grade above the conditional limit, "
              "or a proposed base covenant breach. Otherwise require conditions for weaker grades, "
              "a downside breach, or refinancing equity. Approve only when none applies.")
    heading("Financial trends")
    trend = history.loc[:, [C.YEAR, C.REVENUE, C.EBITDA, C.DEBT, C.LEVERAGE, C.FCCR]].copy()
    table(trend)
    heading("Current financial ratios")
    metrics = (C.NET_LEVERAGE, C.COVERAGE, C.CAPITALIZATION, C.CURRENT_RATIO,
               C.GROSS_MARGIN, C.MARGIN, C.FCF_DEBT, C.DSO, C.DIO, C.DPO)
    table(pd.DataFrame([{C.METRIC: metric, C.VALUE: latest[metric]} for metric in metrics]))
    paragraph("Dollar amounts are USD. Margins and capitalization are decimal fractions. "
              "Working-capital days use average opening and closing balances. "
              f"Spread flags: {latest[C.FLAGS] or 'none'}.")
    document.add_page_break()
    markdown.append("<!-- page break -->")
    heading("Rating rationale")
    table(factors.loc[:, [C.FACTOR, C.VALUE, C.FACTOR_SCORE, C.WEIGHT]])
    paragraph("Quantitative weights and qualitative judgments are model inputs. "
              "Unavailable quantitative factors receive the worst factor score. "
              "The grade is rounded upward and is not a regulatory determination.")
    heading("Facility and covenant analysis")
    facility_metrics = (C.REVOLVER, C.TERM, C.PROPOSED_DEBT, C.PRINCIPAL, C.INTEREST,
                        C.RATE, C.AMORT_YEARS, C.EQUITY_CALL, C.LGD, C.MAX_LEVERAGE,
                        C.MIN_FCCR, C.LEVERAGE, C.FCCR, C.LEVERAGE_HEADROOM,
                        C.FCCR_HEADROOM, C.CUSHION, C.BREAK_EVEN)
    table(pd.DataFrame([{C.METRIC: metric, C.VALUE: facility[metric]} for metric in facility_metrics]))
    paragraph("The package replaces existing debt. Closing equity covers any refinancing gap. "
              "Term principal amortizes equally; the revolver is partially drawn. "
              "FCCR includes proposed term amortization. Headroom, cushions, and LGD are percentages. "
              "A negative cushion means an existing breach.")
    heading("Downside and conditions")
    paragraph(f"Stress assumptions: revenue {facility[C.REVENUE_STRESS]:.0%}; "
              f"margin {facility[C.MARGIN_STRESS] * 10000:.0f} basis points. "
              f"Downside revenue {number(facility[C.DOWN_REVENUE])}; EBITDA {number(facility[C.DOWN_EBITDA])}; "
              f"leverage {number(facility[C.DOWN_LEVERAGE])}; FCCR {number(facility[C.DOWN_FCCR])}; "
              f"covenant breach {facility[C.DOWN_BREACH]}. Capex and cash taxes remain fixed.")
    paragraph(f"Risk: {assumptions['risk']} Mitigant: {assumptions['mitigant']} "
              "Any conditional approval requires evidence of closing equity, verified collateral, "
              "and covenant capacity before funding.")
    cfg.OUTPUTS.mkdir(parents=True, exist_ok=True)
    (cfg.OUTPUTS / f"memo_{ticker}.md").write_text("\n\n".join(markdown) + "\n", encoding="utf-8")
    document.save(cfg.OUTPUTS / f"memo_{ticker}.docx")
