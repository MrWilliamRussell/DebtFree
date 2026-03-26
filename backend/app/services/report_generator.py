"""PDF report generator for monthly debt freedom progress reports."""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def generate_monthly_report(
    report_month: str,
    income: float,
    expenses: float,
    net: float,
    total_debt: float,
    debt_change: float,
    health_score: int,
    grade: str,
    expenses_by_category: dict[str, float],
    payoff_months_remaining: int,
    interest_saved: float,
    tips: list[str],
) -> bytes:
    """Generate a PDF monthly report and return as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#10b981"))
    story.append(Paragraph("DebtFree Monthly Report", title_style))
    story.append(Paragraph(f"<i>{report_month}</i>", styles["Normal"]))
    story.append(Spacer(1, 20))

    # Summary table
    summary_data = [
        ["Metric", "Value"],
        ["Monthly Income", f"${income:,.2f}"],
        ["Monthly Expenses", f"${expenses:,.2f}"],
        ["Net (Income - Expenses)", f"${net:,.2f}"],
        ["Total Debt", f"${total_debt:,.2f}"],
        ["Debt Change This Month", f"${debt_change:+,.2f}"],
        ["Health Score", f"{health_score}/100 ({grade})"],
        ["Months to Debt-Free", str(payoff_months_remaining)],
        ["Interest Saved (vs min payments)", f"${interest_saved:,.2f}"],
    ]

    t = Table(summary_data, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f9fafb"), colors.white]),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Expenses pie chart as matplotlib image
    if expenses_by_category:
        fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
        cats = list(expenses_by_category.keys())
        vals = list(expenses_by_category.values())
        ax.pie(vals, labels=cats, autopct='%1.0f%%', textprops={'fontsize': 7})
        ax.set_title("Expenses by Category", fontsize=12)
        plt.tight_layout()

        chart_buf = io.BytesIO()
        fig.savefig(chart_buf, format='png', dpi=120, bbox_inches='tight')
        plt.close(fig)
        chart_buf.seek(0)

        img = Image(chart_buf, width=4.5*inch, height=3*inch)
        story.append(img)
        story.append(Spacer(1, 15))

    # Tips
    story.append(Paragraph("<b>Action Items & Tips</b>", styles["Heading2"]))
    for i, tip in enumerate(tips, 1):
        story.append(Paragraph(f"{i}. {tip}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Footer
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey)
    story.append(Paragraph(
        f"Generated {date.today().isoformat()} by DebtFree Dashboard | Self-hosted, privacy-first",
        footer_style,
    ))

    doc.build(story)
    return buf.getvalue()
