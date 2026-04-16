"""
PDFService: Generate estimate sheets, invoices, and work orders as PDF.
Uses ReportLab for PDF generation.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def _fmt(n):
    """Format number as currency."""
    if n is None:
        return "$0.00"
    return f"${float(n):,.2f}"


def _date(d):
    if not d:
        return "—"
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").strftime("%m/%d/%Y")
    except Exception:
        return d or "—"


def _build_header(story, styles, shop, doc_type, doc_number, date_str):
    """Build common document header with shop info."""
    shop_name = shop.get("shop_name", "Auto Body Shop") if shop else "Auto Body Shop"
    shop_addr = ""
    if shop:
        parts = [shop.get("address", ""), shop.get("city", ""), shop.get("state", "")]
        shop_addr = ", ".join(p for p in parts if p)
        if shop.get("zip_code"):
            shop_addr += " " + shop["zip_code"]
    shop_phone = shop.get("phone", "") if shop else ""
    shop_email = shop.get("email", "") if shop else ""

    # Shop name
    title_style = ParagraphStyle("ShopTitle", parent=styles["Title"],
                                  fontSize=20, textColor=colors.HexColor("#1a5c2a"),
                                  spaceAfter=2)
    story.append(Paragraph(shop_name, title_style))

    if shop_addr:
        story.append(Paragraph(shop_addr, styles["Normal"]))
    contact_parts = [p for p in [shop_phone, shop_email] if p]
    if contact_parts:
        story.append(Paragraph(" | ".join(contact_parts), styles["Normal"]))

    story.append(Spacer(1, 8))

    # Document type header
    header_style = ParagraphStyle("DocHeader", parent=styles["Heading1"],
                                   fontSize=16, textColor=colors.HexColor("#1e293b"),
                                   alignment=TA_LEFT)
    story.append(Paragraph(f"{doc_type}: {doc_number}", header_style))
    story.append(Paragraph(f"Date: {date_str}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 12))


def _build_info_table(story, styles, left_data, right_data):
    """Build a two-column info section (customer/vehicle or insurance info)."""
    left_rows = [[Paragraph(f"<b>{k}:</b>", styles["Normal"]),
                   Paragraph(str(v), styles["Normal"])] for k, v in left_data]
    right_rows = [[Paragraph(f"<b>{k}:</b>", styles["Normal"]),
                    Paragraph(str(v), styles["Normal"])] for k, v in right_data]

    max_len = max(len(left_rows), len(right_rows))
    while len(left_rows) < max_len:
        left_rows.append(["", ""])
    while len(right_rows) < max_len:
        right_rows.append(["", ""])

    combined = []
    for i in range(max_len):
        combined.append(left_rows[i] + [""] + right_rows[i])

    col_widths = [90, 170, 20, 90, 170]
    t = Table(combined, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))


def _build_lines_table(story, styles, lines, show_cost=False):
    """Build the line items table."""
    header = ["#", "Type", "Operation", "Description", "Qty", "Hours", "Rate", "Total"]
    if show_cost:
        header.insert(-1, "Cost")

    rows = [header]
    for line in lines:
        ln = line.get("line_number", "")
        lt = (line.get("line_type", "") or "").title()
        op = (line.get("operation", "") or "").title()
        desc = line.get("description", "")
        qty = line.get("quantity", 1)
        hours = line.get("labor_hours", 0) or line.get("paint_hours", 0) or 0
        rate = line.get("labor_rate", 0) or line.get("paint_rate", 0) or 0
        total = line.get("line_total", 0) or 0

        row = [str(ln), lt, op, desc, f"{qty:.0f}",
               f"{hours:.1f}" if hours else "—",
               _fmt(rate) if rate else "—",
               _fmt(total)]
        if show_cost:
            cost = line.get("part_cost", 0) or 0
            row.insert(-1, _fmt(cost) if cost else "—")
        rows.append(row)

    if show_cost:
        col_widths = [25, 50, 55, 145, 30, 40, 50, 50, 55]
    else:
        col_widths = [25, 55, 60, 175, 35, 45, 55, 60]

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))


def _build_totals(story, styles, data, is_invoice=False):
    """Build the totals summary section."""
    right_style = ParagraphStyle("RightAlign", parent=styles["Normal"],
                                  alignment=TA_RIGHT, fontSize=10)
    bold_right = ParagraphStyle("BoldRight", parent=right_style,
                                 fontName="Helvetica-Bold", fontSize=11)

    totals_data = [
        ["Labor:", _fmt(data.get("subtotal_labor", 0))],
        ["Parts:", _fmt(data.get("subtotal_parts", 0))],
        ["Paint:", _fmt(data.get("subtotal_paint", 0))],
    ]
    if data.get("subtotal_sublet"):
        totals_data.append(["Sublet:", _fmt(data["subtotal_sublet"])])
    if data.get("subtotal_other"):
        totals_data.append(["Other:", _fmt(data["subtotal_other"])])
    totals_data.append(["Tax (parts):", _fmt(data.get("tax_amount", 0))])
    totals_data.append(["TOTAL:", _fmt(data.get("total_amount", 0))])

    if is_invoice:
        totals_data.append(["Amount Paid:", _fmt(data.get("amount_paid", 0))])
        totals_data.append(["BALANCE DUE:", _fmt(data.get("balance_due", 0))])
        if data.get("deductible"):
            totals_data.append(["Deductible:", _fmt(data["deductible"])])

    totals_rows = []
    for label, val in totals_data:
        is_bold = label in ("TOTAL:", "BALANCE DUE:")
        s = bold_right if is_bold else right_style
        totals_rows.append([
            Paragraph(f"<b>{label}</b>" if is_bold else label, s),
            Paragraph(f"<b>{val}</b>" if is_bold else val, s),
        ])

    t = Table(totals_rows, colWidths=[120, 100])
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (0, -1 if not is_invoice else -3), (-1, -1 if not is_invoice else -3),
         1.5, colors.HexColor("#1e293b")),
    ]))

    # Right-align the totals table
    wrapper = Table([[None, t]], colWidths=[320, 220])
    wrapper.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(wrapper)


def generate_estimate_pdf(estimate, lines, shop=None):
    """Generate an estimate PDF document."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    est_num = estimate.get("estimate_number", "")
    est_date = _date(estimate.get("estimate_date") or estimate.get("created_at", "")[:10])

    _build_header(story, styles, shop, "ESTIMATE", est_num, est_date)

    # Customer / Vehicle info
    cust_name = estimate.get("company_name") or \
        f"{estimate.get('customer_first', '')} {estimate.get('customer_last', '')}".strip() or \
        f"{estimate.get('first_name', '')} {estimate.get('last_name', '')}".strip() or "—"

    veh = " ".join(str(x) for x in [
        estimate.get("vehicle_year") or estimate.get("year"),
        estimate.get("vehicle_make") or estimate.get("make"),
        estimate.get("vehicle_model") or estimate.get("model"),
    ] if x) or "—"

    left_data = [
        ("Customer", cust_name),
        ("Vehicle", veh),
        ("VIN", estimate.get("vin", "—")),
        ("Color", estimate.get("color", "—")),
    ]
    right_data = [
        ("Insurance", estimate.get("insurance_name") or estimate.get("company_name_ins", "—")),
        ("Claim #", estimate.get("claim_number", "—")),
        ("Deductible", _fmt(estimate.get("deductible", 0))),
        ("Status", (estimate.get("status", "") or "").title()),
    ]

    _build_info_table(story, styles, left_data, right_data)

    # Damage description
    if estimate.get("damage_description"):
        story.append(Paragraph("<b>Damage Description:</b>", styles["Normal"]))
        story.append(Paragraph(estimate["damage_description"], styles["Normal"]))
        story.append(Spacer(1, 10))

    # Line items
    if lines:
        story.append(Paragraph("<b>Line Items</b>", styles["Heading3"]))
        _build_lines_table(story, styles, lines)

    # Totals
    _build_totals(story, styles, estimate)

    # Footer
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 8))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
                                   fontSize=8, textColor=colors.HexColor("#94a3b8"))
    story.append(Paragraph("This estimate is valid for 30 days from the date above. "
                           "Actual repair costs may vary upon teardown and inspection.", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf


def generate_invoice_pdf(ro, lines, payments=None, shop=None):
    """Generate an invoice/final bill PDF from a repair order."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    ro_num = ro.get("ro_number", "")
    ro_date = _date(ro.get("create_date") or ro.get("created_at", "")[:10])

    _build_header(story, styles, shop, "INVOICE", ro_num, ro_date)

    # Customer / Vehicle info
    cust_name = ro.get("company_name") or \
        f"{ro.get('customer_first', '')} {ro.get('customer_last', '')}".strip() or "—"

    veh = " ".join(str(x) for x in [
        ro.get("vehicle_year") or ro.get("year"),
        ro.get("vehicle_make") or ro.get("make"),
        ro.get("vehicle_model") or ro.get("model"),
    ] if x) or "—"

    left_data = [
        ("Customer", cust_name),
        ("Vehicle", veh),
        ("VIN", ro.get("vin", "—")),
        ("Mileage", str(ro.get("mileage", "—"))),
    ]
    right_data = [
        ("Insurance", ro.get("insurance_name", "—")),
        ("Claim #", ro.get("claim_number", "—")),
        ("Deductible", _fmt(ro.get("deductible", 0))),
        ("Date In", _date(ro.get("vehicle_arrived_date"))),
    ]

    _build_info_table(story, styles, left_data, right_data)

    # Line items
    if lines:
        story.append(Paragraph("<b>Repair Operations</b>", styles["Heading3"]))
        _build_lines_table(story, styles, lines, show_cost=False)

    # Totals
    _build_totals(story, styles, ro, is_invoice=True)

    # Payments
    if payments:
        story.append(Spacer(1, 16))
        story.append(Paragraph("<b>Payments Received</b>", styles["Heading3"]))
        pay_rows = [["Date", "Method", "Payer", "Reference", "Amount"]]
        for p in payments:
            pay_rows.append([
                _date(p.get("payment_date")),
                (p.get("payment_method", "") or "").replace("_", " ").title(),
                p.get("payer_name", "—"),
                p.get("reference_number", "—"),
                _fmt(p.get("amount", 0)),
            ])
        t = Table(pay_rows, colWidths=[80, 80, 120, 100, 80])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(t)

    # Signature lines
    story.append(Spacer(1, 30))
    sig_data = [
        ["Customer Signature: ______________________________", "",
         "Date: ________________"],
    ]
    sig = Table(sig_data, colWidths=[250, 40, 200])
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(sig)

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1")))
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
                                   fontSize=8, textColor=colors.HexColor("#94a3b8"))
    story.append(Paragraph("Thank you for your business. Payment is due upon delivery of vehicle.", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf


def generate_work_order_pdf(ro, lines, shop=None):
    """Generate a work order PDF for the shop floor."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    story = []

    ro_num = ro.get("ro_number", "")
    _build_header(story, styles, shop, "WORK ORDER", ro_num,
                  _date(ro.get("create_date") or ro.get("created_at", "")[:10]))

    # Vehicle and assignment info
    veh = " ".join(str(x) for x in [
        ro.get("vehicle_year") or ro.get("year"),
        ro.get("vehicle_make") or ro.get("make"),
        ro.get("vehicle_model") or ro.get("model"),
    ] if x) or "—"

    left_data = [
        ("Vehicle", veh),
        ("Color", ro.get("color", "—")),
        ("VIN", ro.get("vin", "—")),
        ("Priority", (ro.get("priority", "normal") or "normal").title()),
    ]
    right_data = [
        ("Technician", f"{ro.get('tech_first', '')} {ro.get('tech_last', '')}".strip() or "—"),
        ("Painter", f"{ro.get('painter_first', '')} {ro.get('painter_last', '')}".strip() or "—"),
        ("Target Date", _date(ro.get("target_delivery_date"))),
        ("Status", (ro.get("status", "") or "").replace("_", " ").title()),
    ]

    _build_info_table(story, styles, left_data, right_data)

    # Line items with checkboxes
    if lines:
        story.append(Paragraph("<b>Operations</b>", styles["Heading3"]))
        header = ["Done", "#", "Type", "Description", "Hours", "Notes"]
        rows = [header]
        for line in lines:
            hours = line.get("labor_hours", 0) or line.get("paint_hours", 0) or 0
            rows.append([
                "[ ]",
                str(line.get("line_number", "")),
                (line.get("line_type", "") or "").title(),
                line.get("description", ""),
                f"{hours:.1f}" if hours else "—",
                "",
            ])

        t = Table(rows, colWidths=[35, 25, 50, 220, 45, 120])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ]))
        story.append(t)

    # Notes section
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Notes:</b>", styles["Normal"]))
    if ro.get("notes"):
        story.append(Paragraph(ro["notes"], styles["Normal"]))
    story.append(Spacer(1, 8))
    for _ in range(4):
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"),
                                spaceBefore=12))

    doc.build(story)
    buf.seek(0)
    return buf
