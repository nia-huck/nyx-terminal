"""Generate PDF from the Diaricat Live integration doc."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, KeepTogether, PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re

OUTPUT = "DIARICAT-LIVE-INTEGRATION.pdf"

# Colors
BG_DARK = HexColor("#1a1a2e")
PURPLE = HexColor("#7c3aed")
PURPLE_LIGHT = HexColor("#a78bfa")
GRAY_BG = HexColor("#f3f4f6")
GRAY_BORDER = HexColor("#d1d5db")
TEXT_DARK = HexColor("#111827")
TEXT_MID = HexColor("#374151")
CODE_BG = HexColor("#f8f9fa")

styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle(
    "DocTitle", parent=styles["Title"],
    fontSize=22, leading=28, textColor=PURPLE,
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    "H2Custom", parent=styles["Heading2"],
    fontSize=16, leading=20, textColor=PURPLE,
    spaceBefore=18, spaceAfter=8,
    borderWidth=0, borderPadding=0,
))
styles.add(ParagraphStyle(
    "H3Custom", parent=styles["Heading3"],
    fontSize=12, leading=16, textColor=TEXT_DARK,
    spaceBefore=12, spaceAfter=6,
))
styles.add(ParagraphStyle(
    "BodyCustom", parent=styles["Normal"],
    fontSize=9.5, leading=13, textColor=TEXT_MID,
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    "CodeBlock", parent=styles["Code"],
    fontSize=7.5, leading=10, textColor=TEXT_DARK,
    backColor=CODE_BG, borderWidth=0.5, borderColor=GRAY_BORDER,
    borderPadding=6, spaceBefore=4, spaceAfter=8,
    leftIndent=8, rightIndent=8,
))
styles.add(ParagraphStyle(
    "BulletCustom", parent=styles["Normal"],
    fontSize=9.5, leading=13, textColor=TEXT_MID,
    leftIndent=16, bulletIndent=6,
    spaceAfter=3,
))


def escape(text):
    """Escape XML special chars for ReportLab."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_md_to_flowables(md_text):
    """Parse the markdown into ReportLab flowables."""
    flowables = []
    lines = md_text.split("\n")
    i = 0
    in_code = False
    code_buf = []

    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith("```"):
            if in_code:
                code_text = "\n".join(code_buf)
                flowables.append(Preformatted(escape(code_text), styles["CodeBlock"]))
                code_buf = []
                in_code = False
            else:
                in_code = True
                code_buf = []
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Skip horizontal rules
        if line.strip() == "---":
            flowables.append(HRFlowable(
                width="100%", thickness=0.5, color=GRAY_BORDER,
                spaceBefore=8, spaceAfter=8,
            ))
            i += 1
            continue

        # H1
        if line.startswith("# "):
            text = line[2:].strip()
            # Replace special chars
            text = text.replace("↔", "<->")
            flowables.append(Paragraph(escape(text), styles["DocTitle"]))
            i += 1
            continue

        # H2
        if line.startswith("## "):
            text = line[3:].strip()
            flowables.append(Paragraph(escape(text), styles["H2Custom"]))
            i += 1
            continue

        # H3
        if line.startswith("### "):
            text = line[4:].strip()
            flowables.append(Paragraph(escape(text), styles["H3Custom"]))
            i += 1
            continue

        # Table
        if line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1

            # Parse table
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                if cells and not all(c.replace("-", "").strip() == "" for c in cells):
                    rows.append(cells)

            if rows:
                # Style table
                t_style = TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 11),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRAY_BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GRAY_BG]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
                # Convert cells to Paragraphs for wrapping
                p_rows = []
                for ri, row in enumerate(rows):
                    p_row = []
                    for cell in row:
                        s = styles["BodyCustom"] if ri > 0 else ParagraphStyle(
                            "tcell", parent=styles["BodyCustom"],
                            textColor=white, fontSize=8.5,
                        )
                        p_row.append(Paragraph(escape(cell), s))
                    p_rows.append(p_row)

                ncols = max(len(r) for r in p_rows)
                col_w = (A4[0] - 40) / ncols
                t = Table(p_rows, colWidths=[col_w] * ncols)
                t.setStyle(t_style)
                flowables.append(t)
                flowables.append(Spacer(1, 8))
            continue

        # Bullet
        if line.strip().startswith("- "):
            text = line.strip()[2:]
            # Handle inline code
            text = re.sub(r"`([^`]+)`", r"<font face='Courier' size='8'>\1</font>", escape(text))
            flowables.append(Paragraph(
                text, styles["BulletCustom"], bulletText="\u2022"
            ))
            i += 1
            continue

        # Empty line
        if not line.strip():
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # Regular paragraph
        text = line.strip()
        if text:
            # Handle inline code
            text = re.sub(r"`([^`]+)`", r"<font face='Courier' size='8'>\1</font>", escape(text))
            # Handle bold
            text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
            flowables.append(Paragraph(text, styles["BodyCustom"]))

        i += 1

    return flowables


def build_pdf():
    md_text = open(
        r"C:\Users\Niahu\OneDrive\Desktop\Nyx Terminal\DIARICAT-LIVE-INTEGRATION.md",
        encoding="utf-8",
    ).read()

    output_path = r"C:\Users\Niahu\OneDrive\Desktop\Nyx Terminal\DIARICAT-LIVE-INTEGRATION.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="Diaricat Live - Integration Guide",
        author="Nia Huck",
    )

    flowables = parse_md_to_flowables(md_text)
    doc.build(flowables)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    build_pdf()
