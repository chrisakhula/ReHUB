"""Document Engine: Server-side PDF generation, institutional branding, and spreadsheet exports for ReHUB Finance."""

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)

# Colors
PRIMARY_COLOR = colors.HexColor("#1e293b")   # Slate 800
SECONDARY_COLOR = colors.HexColor("#475569") # Slate 600
ACCENT_COLOR = colors.HexColor("#0284c7")    # Sky 600
LIGHT_BG = colors.HexColor("#f8fafc")        # Slate 50
BORDER_COLOR = colors.HexColor("#e2e8f0")    # Slate 200

DEFAULT_BRANDING = {
    "org_name": "ARS Rehabilitation Centre",
    "facility_name": "Main Campus",
    "physical_address": "Karen, Off Langata Road, Nairobi, Kenya",
    "postal_address": "P.O. Box 45021 - 00100, Nairobi",
    "phone": "+254 700 000 000 / +254 711 000 000",
    "email": "finance@arsrehab.org",
    "website": "www.arsrehab.org",
    "kra_pin": "P051234567Z",
    "paybill": "Paybill: 522522 | Account: ARS-[Client Number]",
    "bank_details": "KCB Bank | Karen Branch | A/C 1234567890",
}


def fmt_money(val: Any) -> str:
    """Format decimal/float currency safely without raw floats."""
    if val is None:
        return "KES 0.00"
    try:
        d = Decimal(str(val))
        return f"KES {d:,.2f}"
    except Exception:
        return f"KES {val}"


def fmt_date(val: Any) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, (date, datetime)):
        return val.strftime("%d %b %Y")
    return str(val)[:10]


class NumberedCanvas:
    """ReportLab canvas callback to draw professional institutional headers, footers and page numbers."""
    def __init__(self, canvas, doc, branding=None, title=""):
        self.canvas = canvas
        self.doc = doc
        self.branding = branding or DEFAULT_BRANDING
        self.title = title


class FinancialDocumentPdfBuilder:
    """Builder for official, reproducible, privacy-safe financial PDFs."""

    def __init__(self, branding: Optional[dict] = None, page_size=A4):
        self.branding = branding or DEFAULT_BRANDING
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name="DocTitle",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=PRIMARY_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="DocSubtitle",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=SECONDARY_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=PRIMARY_COLOR,
            spaceAfter=4,
        ))
        self.styles.add(ParagraphStyle(
            name="BodySmall",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=PRIMARY_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="BodySmallBold",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=PRIMARY_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="TableHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.whitesmoke,
            alignment=0,
        ))
        self.styles.add(ParagraphStyle(
            name="TableCell",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=PRIMARY_COLOR,
        ))
        self.styles.add(ParagraphStyle(
            name="TableCellRight",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=PRIMARY_COLOR,
            alignment=2,
        ))
        self.styles.add(ParagraphStyle(
            name="TableCellBoldRight",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=PRIMARY_COLOR,
            alignment=2,
        ))

    def _build_header(self, doc_type: str, doc_reference: str, status: str = "") -> list:
        elements = []
        b = self.branding

        header_data = [
            [
                Paragraph(f"<b>{b['org_name']}</b><br/>{b['physical_address']}<br/>Phone: {b['phone']}<br/>Email: {b['email']}<br/>KRA PIN: {b['kra_pin']}", self.styles["DocSubtitle"]),
                Paragraph(f"<font color='{ACCENT_COLOR.hexval()}'><b>{doc_type.upper()}</b></font><br/><b>Ref:</b> {doc_reference}<br/><b>Date:</b> {fmt_date(date.today())}<br/>" + (f"<b>Status:</b> {status}" if status else ""), self.styles["DocSubtitle"]),
            ]
        ]

        t = Table(header_data, colWidths=[10 * cm, 7 * cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT_COLOR, spaceBefore=4, spaceAfter=10))
        return elements

    def _build_footer(self) -> list:
        b = self.branding
        elements = [
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceBefore=4, spaceAfter=6),
            Paragraph(f"<b>Payment Instructions:</b> {b['paybill']} | {b['bank_details']}", self.styles["DocSubtitle"]),
            Paragraph("This is an official computer-generated financial document. Strictly confidential.", self.styles["DocSubtitle"]),
        ]
        return elements

    def generate_invoice_pdf(self, invoice_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=self.page_size, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []

        elements.extend(self._build_header("TAX INVOICE", invoice_data.get("invoice_number", ""), invoice_data.get("status", "")))

        # Client / Admission info box
        client_info = [
            [
                Paragraph("<b>BILL TO:</b>", self.styles["BodySmallBold"]),
                Paragraph("<b>INVOICE DETAILS:</b>", self.styles["BodySmallBold"]),
            ],
            [
                Paragraph(f"<b>Client Name:</b> {invoice_data.get('client_name', 'N/A')}<br/><b>Client Ref:</b> {invoice_data.get('client_number', 'N/A')}<br/><b>Admission Ref:</b> {invoice_data.get('admission_number', 'N/A')}<br/><b>Payer / Sponsor:</b> {invoice_data.get('payer_name', 'Self / Private')}", self.styles["BodySmall"]),
                Paragraph(f"<b>Issue Date:</b> {fmt_date(invoice_data.get('issue_date'))}<br/><b>Due Date:</b> {fmt_date(invoice_data.get('due_date'))}<br/><b>Payment Terms:</b> 30 Days", self.styles["BodySmall"]),
            ]
        ]
        info_table = Table(client_info, colWidths=[9 * cm, 8 * cm])
        info_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        # Items Table
        items_data = [
            [
                Paragraph("<b>Item Description</b>", self.styles["TableHeader"]),
                Paragraph("<b>Qty</b>", self.styles["TableHeader"]),
                Paragraph("<b>Unit Price</b>", self.styles["TableHeader"]),
                Paragraph("<b>Discount</b>", self.styles["TableHeader"]),
                Paragraph("<b>Total</b>", self.styles["TableHeader"]),
            ]
        ]

        for item in invoice_data.get("items", []):
            items_data.append([
                Paragraph(item.get("description", ""), self.styles["TableCell"]),
                Paragraph(str(item.get("quantity", "1")), self.styles["TableCell"]),
                Paragraph(fmt_money(item.get("unit_price", 0)), self.styles["TableCellRight"]),
                Paragraph(fmt_money(item.get("discount", 0)), self.styles["TableCellRight"]),
                Paragraph(fmt_money(item.get("total_price", 0)), self.styles["TableCellRight"]),
            ])

        # Summary rows
        subtotal = invoice_data.get("subtotal", 0)
        discount = invoice_data.get("discount_amount", 0)
        tax = invoice_data.get("tax_amount", 0)
        total = invoice_data.get("total_amount", 0)
        paid = invoice_data.get("amount_paid", 0)
        balance = invoice_data.get("balance_due", total)

        items_data.append(["", "", "", Paragraph("<b>Subtotal:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(subtotal), self.styles["TableCellBoldRight"])])
        items_data.append(["", "", "", Paragraph("<b>Discount:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(discount), self.styles["TableCellBoldRight"])])
        items_data.append(["", "", "", Paragraph("<b>Tax / VAT:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(tax), self.styles["TableCellBoldRight"])])
        items_data.append(["", "", "", Paragraph("<b>Total Amount:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(total), self.styles["TableCellBoldRight"])])
        items_data.append(["", "", "", Paragraph("<b>Amount Paid:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(paid), self.styles["TableCellBoldRight"])])
        items_data.append(["", "", "", Paragraph("<b>Balance Due:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(balance), self.styles["TableCellBoldRight"])])

        item_table = Table(items_data, colWidths=[7.5 * cm, 1.5 * cm, 2.8 * cm, 2.2 * cm, 3 * cm])
        item_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -7), 0.5, BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -7), [colors.white, LIGHT_BG]),
            ("LINEABOVE", (3, -6), (4, -1), 0.5, BORDER_COLOR),
            ("LINEBELOW", (3, -1), (4, -1), 1.5, PRIMARY_COLOR),
        ]))
        elements.append(item_table)

        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()

    def generate_receipt_pdf(self, receipt_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A5, leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
        elements = []

        elements.extend(self._build_header("PAYMENT RECEIPT", receipt_data.get("receipt_number", ""), "COMPLETED"))

        receipt_rows = [
            [Paragraph("<b>Received From:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("received_from", "N/A"), self.styles["BodySmall"])],
            [Paragraph("<b>Client Reference:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("client_number", "N/A"), self.styles["BodySmall"])],
            [Paragraph("<b>Admission Ref:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("admission_number", "N/A"), self.styles["BodySmall"])],
            [Paragraph("<b>Payment Date:</b>", self.styles["BodySmallBold"]), Paragraph(fmt_date(receipt_data.get("payment_date")), self.styles["BodySmall"])],
            [Paragraph("<b>Payment Method:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("payment_method", "CASH"), self.styles["BodySmall"])],
            [Paragraph("<b>Transaction Ref:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("transaction_reference", "N/A"), self.styles["BodySmall"])],
            [Paragraph("<b>Amount Paid:</b>", self.styles["BodySmallBold"]), Paragraph(f"<font color='{ACCENT_COLOR.hexval()}'><b>{fmt_money(receipt_data.get('amount', 0))}</b></font>", self.styles["BodySmall"])],
            [Paragraph("<b>Invoice(s) Settled:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("invoices_settled", "Direct Payment"), self.styles["BodySmall"])],
            [Paragraph("<b>Remaining Balance:</b>", self.styles["BodySmallBold"]), Paragraph(fmt_money(receipt_data.get("remaining_balance", 0)), self.styles["BodySmall"])],
            [Paragraph("<b>Received By:</b>", self.styles["BodySmallBold"]), Paragraph(receipt_data.get("received_by", "Authorized Cashier"), self.styles["BodySmall"])],
        ]

        t = Table(receipt_rows, colWidths=[4 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()

    def generate_quotation_pdf(self, quote_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=self.page_size, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []

        elements.extend(self._build_header("COST ESTIMATE / QUOTATION", quote_data.get("reference_code", ""), quote_data.get("status", "")))

        info_data = [
            [
                Paragraph(f"<b>Client:</b> {quote_data.get('client_name', 'N/A')}<br/><b>Client Ref:</b> {quote_data.get('client_number', 'N/A')}<br/><b>Programme:</b> {quote_data.get('programme_name', 'N/A')}", self.styles["BodySmall"]),
                Paragraph(f"<b>Estimated Duration:</b> {quote_data.get('duration_days', 90)} Days<br/><b>Valid Until:</b> {fmt_date(quote_data.get('valid_until'))}<br/><b>Deposit Required:</b> {fmt_money(quote_data.get('deposit_required', 0))}", self.styles["BodySmall"]),
            ]
        ]
        t = Table(info_data, colWidths=[9 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

        items_data = [
            [
                Paragraph("<b>Category</b>", self.styles["TableHeader"]),
                Paragraph("<b>Service Description</b>", self.styles["TableHeader"]),
                Paragraph("<b>Qty</b>", self.styles["TableHeader"]),
                Paragraph("<b>Rate</b>", self.styles["TableHeader"]),
                Paragraph("<b>Total</b>", self.styles["TableHeader"]),
            ]
        ]

        for it in quote_data.get("items", []):
            items_data.append([
                Paragraph(it.get("category", ""), self.styles["TableCell"]),
                Paragraph(it.get("description", ""), self.styles["TableCell"]),
                Paragraph(str(it.get("quantity", 1)), self.styles["TableCell"]),
                Paragraph(fmt_money(it.get("unit_price", 0)), self.styles["TableCellRight"]),
                Paragraph(fmt_money(it.get("total_price", 0)), self.styles["TableCellRight"]),
            ])

        total = quote_data.get("total_amount", 0)
        items_data.append(["", "", "", Paragraph("<b>Estimated Total:</b>", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(total), self.styles["TableCellBoldRight"])])

        item_table = Table(items_data, colWidths=[3.5 * cm, 6.5 * cm, 1.5 * cm, 2.5 * cm, 3 * cm])
        item_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("GRID", (0, 0), (-1, -2), 0.5, BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_BG]),
            ("LINEABOVE", (3, -1), (4, -1), 1, PRIMARY_COLOR),
        ]))
        elements.append(item_table)

        if quote_data.get("terms_and_conditions"):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("<b>Terms & Conditions:</b>", self.styles["BodySmallBold"]))
            elements.append(Paragraph(quote_data.get("terms_and_conditions"), self.styles["BodySmall"]))

        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()

    def generate_statement_pdf(self, statement_data: dict, is_final: bool = False) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=self.page_size, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []

        title = "FINAL CLIENT STATEMENT" if is_final else "CLIENT ACCOUNT STATEMENT"
        summary = statement_data.get("summary", {})
        elements.extend(self._build_header(title, summary.get("client_reference", ""), summary.get("financial_clearance_status", "")))

        info_box = [
            [
                Paragraph(f"<b>Client:</b> {summary.get('client_name', 'N/A')}<br/><b>Client Code:</b> {summary.get('client_reference', 'N/A')}<br/><b>Admission Ref:</b> {summary.get('admission_number', 'N/A')}", self.styles["BodySmall"]),
                Paragraph(f"<b>Total Charges:</b> {fmt_money(summary.get('total_charges', 0))}<br/><b>Total Payments:</b> {fmt_money(summary.get('total_payments', 0))}<br/><b>Outstanding Balance:</b> <b>{fmt_money(summary.get('outstanding_balance', 0))}</b>", self.styles["BodySmall"]),
            ]
        ]
        t = Table(info_box, colWidths=[9 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

        # Ledger Table
        table_rows = [
            [
                Paragraph("<b>Date</b>", self.styles["TableHeader"]),
                Paragraph("<b>Reference</b>", self.styles["TableHeader"]),
                Paragraph("<b>Description</b>", self.styles["TableHeader"]),
                Paragraph("<b>Debit</b>", self.styles["TableHeader"]),
                Paragraph("<b>Credit</b>", self.styles["TableHeader"]),
                Paragraph("<b>Balance</b>", self.styles["TableHeader"]),
            ]
        ]

        for tx in statement_data.get("transactions", []):
            table_rows.append([
                Paragraph(fmt_date(tx.get("date")), self.styles["TableCell"]),
                Paragraph(tx.get("reference", ""), self.styles["TableCell"]),
                Paragraph(tx.get("description", ""), self.styles["TableCell"]),
                Paragraph(fmt_money(tx.get("debit", 0)) if tx.get("debit") else "-", self.styles["TableCellRight"]),
                Paragraph(fmt_money(tx.get("credit", 0)) if tx.get("credit") else "-", self.styles["TableCellRight"]),
                Paragraph(fmt_money(tx.get("running_balance", 0)), self.styles["TableCellBoldRight"]),
            ])

        table = Table(table_rows, colWidths=[2.5 * cm, 3 * cm, 5 * cm, 2.2 * cm, 2.2 * cm, 2.1 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(table)
        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()

    def generate_discharge_clearance_pdf(self, clearance_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=self.page_size, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        elements.extend(self._build_header("DISCHARGE FINANCIAL CLEARANCE", clearance_data.get("reference_code", ""), clearance_data.get("status", "")))

        info_box = [
            [
                Paragraph(f"<b>Client:</b> {clearance_data.get('client_name', 'N/A')}<br/><b>Client Code:</b> {clearance_data.get('client_code', 'N/A')}<br/><b>Admission Ref:</b> {clearance_data.get('admission_code', 'N/A')}", self.styles["BodySmall"]),
                Paragraph(f"<b>Clearance Status:</b> <b>{clearance_data.get('status', 'PENDING')}</b><br/><b>Clearance Date:</b> {fmt_date(clearance_data.get('clearance_date'))}<br/><b>Approved By:</b> {clearance_data.get('approved_by', 'N/A')}", self.styles["BodySmall"]),
            ]
        ]
        t = Table(info_box, colWidths=[9 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Financial breakdown table
        financial_rows = [
            [Paragraph("<b>Financial Metric</b>", self.styles["TableHeader"]), Paragraph("<b>Amount (KES)</b>", self.styles["TableHeader"])],
            [Paragraph("Total Cumulative Charges", self.styles["TableCell"]), Paragraph(fmt_money(clearance_data.get("total_charges", 0)), self.styles["TableCellRight"])],
            [Paragraph("Total Cumulative Payments", self.styles["TableCell"]), Paragraph(fmt_money(clearance_data.get("total_payments", 0)), self.styles["TableCellRight"])],
            [Paragraph("Total Credits / Adjustments", self.styles["TableCell"]), Paragraph(fmt_money(clearance_data.get("total_credits", 0)), self.styles["TableCellRight"])],
            [Paragraph("Total Write-Offs", self.styles["TableCell"]), Paragraph(fmt_money(clearance_data.get("total_writeoffs", 0)), self.styles["TableCellRight"])],
            [Paragraph("<b>Outstanding Balance at Discharge</b>", self.styles["TableCellBoldRight"]), Paragraph(f"<b>{fmt_money(clearance_data.get('outstanding_balance', 0))}</b>", self.styles["TableCellBoldRight"])],
        ]
        ft = Table(financial_rows, colWidths=[12 * cm, 5 * cm])
        ft.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, PRIMARY_COLOR),
        ]))
        elements.append(ft)

        if clearance_data.get("is_authorized_exception") or clearance_data.get("exception_reason"):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("<b>Authorized Outstanding Balance Exception:</b>", self.styles["BodySmallBold"]))
            elements.append(Paragraph(f"Reason: {clearance_data.get('exception_reason', 'N/A')}", self.styles["BodySmall"]))
            if clearance_data.get("collection_owner"):
                elements.append(Paragraph(f"Collection Owner: {clearance_data.get('collection_owner')}", self.styles["BodySmall"]))

        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()

    def generate_agreement_pdf(self, agreement_data: dict) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=self.page_size, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        elements = []
        elements.extend(self._build_header("FINANCIAL ADMISSION AGREEMENT", agreement_data.get("reference_code", ""), f"v{agreement_data.get('version', 1)} - {agreement_data.get('status', 'ACTIVE')}"))

        info_box = [
            [
                Paragraph(f"<b>Client:</b> {agreement_data.get('client_name', 'N/A')}<br/><b>Client Code:</b> {agreement_data.get('client_number', 'N/A')}<br/><b>Admission Ref:</b> {agreement_data.get('admission_number', 'N/A')}", self.styles["BodySmall"]),
                Paragraph(f"<b>Programme:</b> {agreement_data.get('programme_name', 'N/A')}<br/><b>Effective Date:</b> {fmt_date(agreement_data.get('effective_date'))}<br/><b>Total Agreed Price:</b> {fmt_money(agreement_data.get('agreed_price', 0))}", self.styles["BodySmall"]),
            ]
        ]
        t = Table(info_box, colWidths=[9 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 10))

        terms_data = [
            [Paragraph("<b>Agreement Terms</b>", self.styles["TableHeader"]), Paragraph("<b>Details</b>", self.styles["TableHeader"])],
            [Paragraph("Required Initial Deposit", self.styles["TableCellBoldRight"]), Paragraph(fmt_money(agreement_data.get("deposit_amount", 0)), self.styles["TableCell"])],
            [Paragraph("Installment Schedule", self.styles["TableCellBoldRight"]), Paragraph(agreement_data.get("installment_terms", "N/A"), self.styles["TableCell"])],
            [Paragraph("Credit Terms", self.styles["TableCellBoldRight"]), Paragraph(agreement_data.get("credit_terms", "30 Days"), self.styles["TableCell"])],
            [Paragraph("Programme Inclusions", self.styles["TableCellBoldRight"]), Paragraph(agreement_data.get("inclusions", "Standard Programme Inclusions"), self.styles["TableCell"])],
            [Paragraph("Programme Exclusions", self.styles["TableCellBoldRight"]), Paragraph(agreement_data.get("exclusions", "None noted"), self.styles["TableCell"])],
            [Paragraph("Refund Terms", self.styles["TableCellBoldRight"]), Paragraph(agreement_data.get("refund_terms", "Standard institutional refund policy"), self.styles["TableCell"])],
        ]
        tt = Table(terms_data, colWidths=[6 * cm, 11 * cm])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ]))
        elements.append(tt)
        elements.extend(self._build_footer())
        doc.build(elements)
        return buf.getvalue()


class FinancialSpreadsheetExporter:
    """Server-side structured export generator for CSV and XLSX reports."""

    @staticmethod
    def export_to_xlsx(sheet_title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:31]

        # Header formatting
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )

        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Row formatting
        row_font = Font(name="Arial", size=9)
        for row_idx, row_data in enumerate(rows, start=2):
            ws.append([str(v) if isinstance(v, (UUID, Decimal)) else v for v in row_data])
            for col_idx in range(1, len(row_data) + 1):
                c = ws.cell(row=row_idx, column=col_idx)
                c.font = row_font
                c.border = thin_border

        # Adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @staticmethod
    def export_to_csv(headers: list[str], rows: list[list[Any]]) -> str:
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for r in rows:
            writer.writerow([str(v) if isinstance(v, (UUID, Decimal)) else v for v in r])
        return output.getvalue()

    # Convenience aliases
    generate_xlsx = export_to_xlsx
    generate_csv = export_to_csv

