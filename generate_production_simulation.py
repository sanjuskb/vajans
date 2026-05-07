"""
VAJANS -- Production Simulation Dataset Generator
==================================================

Generates a realistic Indian-government tender package for end-to-end
production-grade verification:

  Tender:
    tender_morth_sh275.pdf
        Multi-page MoRTH/NHAI-style state highway widening RFP for the
        Karnataka SH-275 corridor with full eligibility, technical,
        financial, certification, compliance and legal sections.

  Bidders (5 distinct realistic profiles):
    bidder_maharashtra_infra.pdf       (digital, all 6 criteria pass)
    bidder_sahyadri_construction.pdf   (digital, fails financial threshold)
    bidder_vidhya_builders.pdf         (digital, fails technical threshold)
    bidder_konkan_engineering.pdf      (SCANNED PDF, missing certifications)
    bidder_deccan_civil_works.pdf      (SCANNED PDF, ambiguous / inconsistent)

The two scanned bidders are rendered as image-only PDFs (no text layer)
so the system MUST drive them through Tesseract OCR + OpenCV preprocessing
to recover the text.  This stresses the entire OCR -> chunking ->
embedding -> retrieval -> extraction -> evaluation pipeline.

Run from the project root:
    python generate_production_simulation.py
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image, ImageFilter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "sample_prod"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Paragraph styles -- reused across all documents
# ---------------------------------------------------------------------------
_STYLES = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "Title", parent=_STYLES["Title"], fontSize=15, spaceAfter=10,
    textColor=colors.HexColor("#0d1b2a"), alignment=TA_CENTER,
)
SUBTITLE = ParagraphStyle(
    "Sub", parent=_STYLES["Heading2"], fontSize=11, spaceAfter=10,
    textColor=colors.HexColor("#1b263b"), alignment=TA_CENTER,
)
H1 = ParagraphStyle(
    "H1", parent=_STYLES["Heading1"], fontSize=12.5, spaceAfter=6,
    spaceBefore=14, textColor=colors.HexColor("#0d3b66"),
)
H2 = ParagraphStyle(
    "H2", parent=_STYLES["Heading2"], fontSize=10.5, spaceAfter=4,
    spaceBefore=10, textColor=colors.HexColor("#1a5276"),
)
BODY = ParagraphStyle(
    "Body", parent=_STYLES["Normal"], fontSize=9.7, spaceAfter=5,
    leading=13.2, alignment=TA_JUSTIFY,
)
BODY_LEFT = ParagraphStyle("BodyL", parent=BODY, alignment=TA_LEFT)
BOLD = ParagraphStyle(
    "Bold", parent=BODY, fontName="Helvetica-Bold", spaceAfter=3,
)
NOTE = ParagraphStyle(
    "Note", parent=BODY, fontSize=9, textColor=colors.HexColor("#444"),
    leftIndent=12,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _new_doc(path: Path) -> tuple[SimpleDocTemplate, list]:
    return (
        SimpleDocTemplate(
            str(path),
            pagesize=A4,
            rightMargin=2.2 * cm,
            leftMargin=2.2 * cm,
            topMargin=2.0 * cm,
            bottomMargin=2.0 * cm,
            title=path.stem,
            author="Government of India",
        ),
        [],
    )


def _kv_table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    if col_widths is None:
        col_widths = [5.5 * cm, 11.0 * cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f8")),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.grey),
        ("PADDING",    (0, 0), (-1, -1), 5),
    ]))
    return t


def _summary_table(header: list[str], data: list[list[str]],
                   col_widths: list[float] | None = None) -> Table:
    rows = [header] + data
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("PADDING",        (0, 0), (-1, -1), 5),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _rasterise_to_scanned_pdf(
    src_pdf: Path,
    dst_pdf: Path,
    *,
    dpi: int = 200,
    blur: bool = False,
    rotate_deg: float = 0.0,
    jpeg_quality: int = 70,
) -> None:
    """
    Convert a digital PDF into a SCANNED-LOOKING PDF by:
      1. Rendering each page to a JPEG image (no text layer).
      2. Optionally rotating slightly and applying a tiny blur to mimic
         a low-quality scanner.
      3. Embedding the JPEG into a fresh PDF page.

    The result has no selectable text -- the ingestion engine will be
    forced to detect it as DocumentKind.SCANNED and run Tesseract OCR.
    """
    pages = convert_from_path(str(src_pdf), dpi=dpi)
    out = fitz.open()
    for img in pages:
        if rotate_deg:
            img = img.rotate(rotate_deg, expand=True, fillcolor=(255, 255, 255),
                             resample=Image.BICUBIC)
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
        buf.seek(0)

        # Page size in PDF points (1 inch = 72 points). Image is `dpi` DPI.
        w_pt = img.width * 72.0 / dpi
        h_pt = img.height * 72.0 / dpi
        page = out.new_page(width=w_pt, height=h_pt)
        page.insert_image(fitz.Rect(0, 0, w_pt, h_pt), stream=buf.read())
    out.save(str(dst_pdf), garbage=4, deflate=True)
    out.close()


# ---------------------------------------------------------------------------
# 1.  TENDER -- MoRTH / KSRDC State Highway widening RFP
# ---------------------------------------------------------------------------
def generate_tender() -> Path:
    path = OUTPUT_DIR / "tender_morth_sh275.pdf"
    doc, story = _new_doc(path)

    # ============ Cover page ===========================================
    story.append(Paragraph("GOVERNMENT OF INDIA", TITLE))
    story.append(Paragraph(
        "MINISTRY OF ROAD TRANSPORT AND HIGHWAYS<br/>"
        "Karnataka State Road Development Corporation (KSRDC)<br/>"
        "Regional Office, Bengaluru -- 560001",
        SUBTITLE,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph("REQUEST FOR PROPOSAL (RFP)", TITLE))
    story.append(Paragraph(
        "Widening and Strengthening of State Highway SH-275<br/>"
        "Bengaluru -- Mysuru -- Madikeri Section (Km 0.000 to Km 87.450)",
        SUBTITLE,
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_kv_table([
        ["Tender Reference",      "MoRTH/KSRDC/SH-275/2024-25/CW-014"],
        ["Tender Issue Date",     "12-April-2024"],
        ["Last Date of Submission", "20-May-2024, 15:00 hrs IST"],
        ["Date of Bid Opening",   "21-May-2024, 11:00 hrs IST"],
        ["Estimated Project Cost",
         "Rs. 184.50 Crore (Rupees One Hundred Eighty-Four Crore Fifty Lakh only)"],
        ["Period of Completion",  "24 calendar months from date of work order"],
        ["Earnest Money Deposit", "Rs. 1.85 Crore (1.0% of estimated cost)"],
        ["Performance Security",  "5% of contract value"],
        ["Mode of Submission",    "Online via Central Public Procurement Portal (CPPP)"],
    ]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This document is issued by the Karnataka State Road "
        "Development Corporation (KSRDC) on behalf of the Government of India, "
        "Ministry of Road Transport and Highways. Bidders are advised to read all "
        "sections carefully before submission. Any incomplete bid or non-compliance "
        "with the Mandatory Eligibility Criteria shall result in summary "
        "disqualification of the bid without any further reference to the bidder.",
        BODY,
    ))
    story.append(PageBreak())

    # ============ Section A: Project Overview ==========================
    story.append(Paragraph("SECTION A -- PROJECT OVERVIEW", H1))
    story.append(Paragraph(
        "The Karnataka State Road Development Corporation (hereinafter referred to "
        "as 'the Authority') invites sealed bids in two-cover system (Technical Bid "
        "and Financial Bid) from eligible contractors for the widening of State "
        "Highway SH-275 from existing two-lane to four-lane configuration with "
        "paved shoulders, including reconstruction of cross-drainage works, "
        "rehabilitation of two minor bridges, and construction of one new "
        "ROB at Channapatna town (Km 41.200).",
        BODY,
    ))
    story.append(Paragraph("A.1  Scope of Work", H2))
    story.append(Paragraph(
        "The Scope of Work shall include but not be limited to: (a) earthwork in "
        "embankment and cutting; (b) sub-grade preparation and granular sub-base; "
        "(c) Wet Mix Macadam (WMM) base course; (d) Dense Bituminous Macadam (DBM) "
        "binder course of 80 mm thickness; (e) Bituminous Concrete (BC) wearing "
        "course of 40 mm thickness; (f) construction of paved shoulders, drains, "
        "and median; (g) road furniture including signage, marking, crash barriers; "
        "(h) reconstruction of 14 minor cross-drainage structures; (i) rehabilitation "
        "of two minor bridges at Km 18.500 and Km 64.300; (j) construction of one "
        "Road-Over-Bridge (ROB) at Channapatna; and (k) any allied works as per "
        "the technical specifications of MoRTH (5th Revision, 2013).",
        BODY,
    ))
    story.append(Paragraph("A.2  Project Location and Stretch", H2))
    story.append(Paragraph(
        "The project corridor traverses the districts of Bengaluru Rural, Ramanagara, "
        "Mandya, Mysuru, Hassan and Kodagu in the State of Karnataka. The total "
        "length of the corridor is 87.450 km. Right-of-Way (ROW) of 30.0 m to "
        "45.0 m is available for the entire stretch.",
        BODY,
    ))
    story.append(PageBreak())

    # ============ Section B: Mandatory Eligibility Criteria ============
    story.append(Paragraph("SECTION B -- MANDATORY ELIGIBILITY CRITERIA", H1))
    story.append(Paragraph(
        "Only bidders who satisfy <b>ALL</b> of the following mandatory eligibility "
        "criteria shall be considered for technical and financial evaluation. "
        "Failure to meet ANY mandatory criterion shall result in summary "
        "disqualification of the bid without any further reference to the bidder. "
        "The Authority reserves the right to verify any claim made in the bid by "
        "independent enquiry. Submission of false or misleading information shall "
        "lead to immediate disqualification, forfeiture of EMD and may result in "
        "blacklisting of the bidder under the Government of India procurement rules.",
        BODY,
    ))

    # B.1 Annual Turnover --------------------------------------------------
    story.append(Paragraph("B.1  Financial Capacity -- Annual Turnover", H2))
    story.append(Paragraph(
        "The bidder shall have a minimum average annual turnover of "
        "<b>Rs. 50.00 Crore (Rupees Fifty Crore only)</b> calculated as the "
        "arithmetic mean of the audited annual turnover for the last three "
        "completed financial years, namely FY 2021-22, FY 2022-23, and FY 2023-24. "
        "This criterion is <b>MANDATORY</b>.",
        BODY,
    ))
    story.append(Paragraph(
        "<b>Threshold: Rs. 50.00 Crore minimum average annual turnover (3 years).</b>",
        BODY,
    ))
    story.append(Paragraph(
        "Documentary evidence required: (i) audited Profit &amp; Loss statements "
        "for the three years certified by a Chartered Accountant holding a valid "
        "ICAI membership; (ii) a CA-certified summary statement showing the "
        "computed three-year arithmetic mean.",
        BODY,
    ))

    # B.2 Similar Projects -------------------------------------------------
    story.append(Paragraph("B.2  Technical Capacity -- Similar Projects Completed", H2))
    story.append(Paragraph(
        "The bidder shall have successfully completed at least "
        "<b>3 (three) similar projects</b>, each of value not less than "
        "<b>Rs. 25.00 Crore (Rupees Twenty-Five Crore only)</b>, during the "
        "<b>last 7 (seven) financial years</b> ending 31 March 2024. "
        "This criterion is <b>MANDATORY</b>.",
        BODY,
    ))
    story.append(Paragraph(
        "<b>Threshold: Minimum 3 similar projects, each of Rs. 25.00 Crore or more.</b>",
        BODY,
    ))
    story.append(Paragraph(
        "'Similar Projects' shall mean construction or widening of National "
        "Highways, State Highways, urban arterials, or other bituminous-surface "
        "roads of similar nature, executed for any Central / State Government "
        "authority, PSU, or autonomous body. Completion certificates issued by "
        "the Engineer-in-Charge of the respective client department shall be "
        "submitted as documentary evidence.",
        BODY,
    ))

    # B.3 GST Registration -------------------------------------------------
    story.append(Paragraph("B.3  Compliance -- GST Registration", H2))
    story.append(Paragraph(
        "The bidder shall be registered under the Goods and Services Tax (GST) "
        "regime and shall hold a valid 15-character alphanumeric GSTIN issued by "
        "the competent authority. The registration shall be in <b>Active</b> "
        "status as on the bid submission date. This criterion is <b>MANDATORY</b>.",
        BODY,
    ))
    story.append(Paragraph(
        "Documentary evidence: a copy of the GST registration certificate "
        "(Form GST REG-06) and the GSTIN. Bidders not registered under GST shall "
        "be summarily disqualified.",
        BODY,
    ))

    # B.4 ISO 9001:2015 ----------------------------------------------------
    story.append(Paragraph("B.4  Certification -- ISO 9001:2015 Quality Management", H2))
    story.append(Paragraph(
        "The bidder shall hold a valid <b>ISO 9001:2015</b> Quality Management "
        "System certification issued by an accreditation-body-approved "
        "certification authority (NABCB / IAF MLA member). The certificate "
        "must be <b>valid and not expired</b> as on the date of bid submission. "
        "This criterion is <b>MANDATORY</b>.",
        BODY,
    ))
    story.append(Paragraph(
        "Expired ISO certificates shall not be accepted under any circumstances. "
        "Bidders shall submit a colour-scanned copy of the ISO certificate clearly "
        "showing the issue date, expiry date, scope of certification and the "
        "name of the issuing certification body.",
        BODY,
    ))
    story.append(PageBreak())

    # B.5 EPF / ESI --------------------------------------------------------
    story.append(Paragraph("B.5  Compliance -- EPF and ESI Registration", H2))
    story.append(Paragraph(
        "The bidder shall hold valid registration under the Employees' Provident "
        "Funds and Miscellaneous Provisions Act, 1952 (EPF) <b>AND</b> the "
        "Employees' State Insurance Act, 1948 (ESI). Both registrations are "
        "<b>MANDATORY</b>. The bidder shall submit the EPF establishment code "
        "and the ESI code as proof of compliance with applicable labour laws.",
        BODY,
    ))
    story.append(Paragraph(
        "Documentary evidence: EPF allotment letter or coverage proceedings "
        "(Form 5A) and ESI registration certificate (Form C-11).",
        BODY,
    ))

    # B.6 Blacklist --------------------------------------------------------
    story.append(Paragraph("B.6  Integrity -- Blacklisting and Debarment Status", H2))
    story.append(Paragraph(
        "The bidder shall <b>NOT</b> be blacklisted, debarred, suspended, or "
        "banned by any Central Government department, State Government "
        "department, public sector undertaking, autonomous body or international "
        "lending agency (World Bank, ADB, JICA, etc.) at the time of bid "
        "submission. This criterion is <b>MANDATORY</b>.",
        BODY,
    ))
    story.append(Paragraph(
        "The bidder shall furnish a notarised self-declaration on the company "
        "letterhead stating that the firm is <b>NOT</b> blacklisted and "
        "<b>NOT</b> debarred by any government authority as on the date of bid "
        "submission. Submission of a false declaration shall lead to immediate "
        "disqualification, forfeiture of Earnest Money Deposit, blacklisting "
        "of the firm for a minimum period of three years, and may attract "
        "penal action under Section 415 of the Indian Penal Code, 1860.",
        BODY,
    ))

    # ============ Section C: Eligibility Summary table =================
    story.append(Paragraph("SECTION C -- ELIGIBILITY CRITERIA -- SUMMARY TABLE", H1))
    story.append(_summary_table(
        ["S.No.", "Criterion", "Type", "Status", "Threshold / Requirement"],
        [
            ["B.1", "Average Annual Turnover (3-yr)", "Financial",
             "Mandatory", "Rs. 50.00 Crore minimum"],
            ["B.2", "Similar Projects Completed (7-yr)", "Technical",
             "Mandatory", "Min. 3 projects, Rs. 25 Cr each"],
            ["B.3", "GST Registration", "Compliance",
             "Mandatory", "Valid Active GSTIN"],
            ["B.4", "ISO 9001:2015 Certification", "Certification",
             "Mandatory", "Valid (not expired)"],
            ["B.5", "EPF & ESI Registration", "Compliance",
             "Mandatory", "Both EPF and ESI codes"],
            ["B.6", "Not Blacklisted / Debarred", "Integrity",
             "Mandatory", "Clean record (declaration)"],
        ],
        col_widths=[1.3 * cm, 5.0 * cm, 2.2 * cm, 2.0 * cm, 6.2 * cm],
    ))
    story.append(PageBreak())

    # ============ Section D: Legal & Compliance ========================
    story.append(Paragraph("SECTION D -- LEGAL AND COMPLIANCE FRAMEWORK", H1))
    story.append(Paragraph(
        "The successful bidder shall comply with all applicable Indian laws, "
        "rules and regulations including but not limited to the Contract Labour "
        "(Regulation and Abolition) Act 1970, Building and Other Construction "
        "Workers (Regulation of Employment and Conditions of Service) Act 1996, "
        "the Environment (Protection) Act 1986, the Air (Prevention and Control "
        "of Pollution) Act 1981, the Water (Prevention and Control of Pollution) "
        "Act 1974, the Right to Fair Compensation and Transparency in Land "
        "Acquisition, Rehabilitation and Resettlement Act 2013, and the General "
        "Financial Rules (GFR) 2017 of the Government of India.",
        BODY,
    ))
    story.append(Paragraph(
        "Any disputes arising out of or in connection with the contract shall be "
        "settled by arbitration under the provisions of the Arbitration and "
        "Conciliation Act, 1996, with the seat of arbitration at Bengaluru, "
        "Karnataka. The Courts at Bengaluru shall have exclusive jurisdiction.",
        BODY,
    ))

    # ============ Section E: Timelines & Milestones =====================
    story.append(Paragraph("SECTION E -- TIMELINES AND MILESTONES", H1))
    story.append(_summary_table(
        ["Milestone", "Target Date", "% of Contract Value"],
        [
            ["Mobilisation and site survey",      "T0 + 30 days",  "5%"],
            ["Earthwork and sub-grade complete",  "T0 + 6 months", "20%"],
            ["WMM and DBM base courses laid",     "T0 + 12 months", "45%"],
            ["BC wearing course and shoulders",   "T0 + 18 months", "75%"],
            ["ROB at Channapatna -- substructure", "T0 + 14 months", "60%"],
            ["ROB at Channapatna -- superstructure","T0 + 22 months", "90%"],
            ["Punch-list rectification, defect-liability handover",
                                                  "T0 + 24 months", "100%"],
        ],
        col_widths=[7.2 * cm, 4.5 * cm, 4.0 * cm],
    ))
    story.append(Paragraph(
        "T0 = date of issue of Letter of Award (LoA) by the Authority. "
        "Liquidated Damages of 0.05% of contract value per day of delay shall "
        "apply, subject to a maximum of 10% of the contract value.",
        BODY,
    ))

    # ============ Section F: Submission Process ========================
    story.append(Paragraph("SECTION F -- SUBMISSION PROCESS", H1))
    story.append(Paragraph(
        "Bids shall be submitted ONLY through the Central Public Procurement "
        "Portal (https://eprocure.gov.in) in two-cover system: (i) Technical "
        "Bid -- containing all eligibility-criteria evidence and technical "
        "compliance statements; (ii) Financial Bid -- containing the priced "
        "Bill of Quantities (BoQ) in the prescribed format. Physical bids "
        "shall not be entertained.",
        BODY,
    ))
    story.append(Paragraph(
        "Each bidder shall upload all supporting documents in PDF format with "
        "digital signature. The total upload size shall not exceed 50 MB per "
        "cover. Bids received after the deadline shall be rejected by the "
        "system automatically and no representation in this regard shall be "
        "entertained.",
        BODY,
    ))

    # ============ Section G: Authority Signature =======================
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>"
        "(Sri. Ramachandra Rao, IRS)<br/>"
        "Chief Engineer (Technical)<br/>"
        "Karnataka State Road Development Corporation<br/>"
        "Bengaluru -- 560001",
        BODY_LEFT,
    ))

    doc.build(story)
    print(f"  generated tender:  {path}")
    return path


# ---------------------------------------------------------------------------
# 2.  BIDDER #1  -- Maharashtra Infra Engineering Ltd.   (STRONG / PASS-ALL)
# ---------------------------------------------------------------------------
def generate_bidder_strong() -> Path:
    path = OUTPUT_DIR / "bidder_maharashtra_infra.pdf"
    doc, story = _new_doc(path)

    story.append(Paragraph("BID SUBMISSION DOCUMENT -- TECHNICAL COVER", TITLE))
    story.append(Paragraph(
        "Maharashtra Infra Engineering Limited<br/>"
        "Corporate Identity Number: U45200MH2002PLC135789<br/>"
        "Registered Office: Plot 47, Hiranandani Business Park, Powai, Mumbai 400076",
        SUBTITLE,
    ))
    story.append(_kv_table([
        ["Tender Reference",   "MoRTH/KSRDC/SH-275/2024-25/CW-014"],
        ["Date of Submission", "18-May-2024"],
        ["Bidder Class",       "AA-class registered contractor (PWD Maharashtra)"],
        ["Year of Incorporation", "2002"],
    ]))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("1.  COMPANY PROFILE", H1))
    story.append(Paragraph(
        "Maharashtra Infra Engineering Limited (hereinafter 'MIEL') is a Limited "
        "Public Company incorporated under the Companies Act, 1956 with its "
        "registered office at Powai, Mumbai. MIEL has executed road, highway and "
        "bridge projects across Maharashtra, Karnataka, Goa and Madhya Pradesh "
        "since 2002. The Company is enlisted as an AA-class contractor with the "
        "Public Works Department, Government of Maharashtra and as Class-I "
        "contractor with the National Highways Authority of India.",
        BODY,
    ))

    story.append(Paragraph("2.  FINANCIAL CAPACITY -- ANNUAL TURNOVER", H1))
    story.append(Paragraph(
        "The audited annual turnover of the Company for the last three completed "
        "financial years, certified by M/s. S. R. Batliboi &amp; Associates, "
        "Chartered Accountants (ICAI Firm Reg. No. 101049W) is as follows:",
        BODY,
    ))
    story.append(_summary_table(
        ["Financial Year", "Annual Turnover (Rs. Crore)", "Source"],
        [
            ["FY 2021-22", "62.40", "Audited P&L statement, page 27 of Annual Report"],
            ["FY 2022-23", "71.85", "Audited P&L statement, page 31 of Annual Report"],
            ["FY 2023-24", "78.20", "Provisional audited statement, certified 25-Apr-2024"],
            ["3-year average", "70.82", "Arithmetic mean of above three years"],
        ],
        col_widths=[4.5 * cm, 5.5 * cm, 7.5 * cm],
    ))
    story.append(Paragraph(
        "The three-year arithmetic mean of <b>Rs. 70.82 Crore</b> exceeds the "
        "minimum required average annual turnover of Rs. 50.00 Crore as stipulated "
        "in clause B.1 of the tender document. Annual turnover certificates and "
        "audited financial statements are enclosed as Annexures F-1, F-2 and F-3.",
        BODY,
    ))

    story.append(Paragraph("3.  TECHNICAL CAPACITY -- SIMILAR PROJECTS COMPLETED", H1))
    story.append(Paragraph(
        "The following similar projects, each of value not less than "
        "Rs. 25.00 Crore, have been completed by MIEL during the last seven "
        "financial years ending 31 March 2024. Completion certificates issued "
        "by the respective Engineer-in-Charge of the client department are "
        "enclosed as Annexures T-1 to T-6:",
        BODY,
    ))
    story.append(_summary_table(
        ["Project", "Client", "Value (Rs. Cr)", "Year Completed"],
        [
            ["Widening of MH-SH 30, Pune-Saswad section",
             "PWD Maharashtra",            "47.20", "2018"],
            ["Strengthening of NH-66, Ratnagiri-Sindhudurg",
             "NHAI Konkan Region",         "62.10", "2020"],
            ["Four-laning of MH-SH 4, Nashik-Trimbak",
             "MSRDC",                      "38.50", "2021"],
            ["Construction of bypass at Karad",
             "PWD Maharashtra",            "29.85", "2022"],
            ["Bituminous overlay, NH-65 (Solapur stretch)",
             "NHAI Mumbai PIU",            "33.20", "2023"],
            ["Widening of NH-50, Sangamner section",
             "NHAI Nashik PIU",            "55.40", "2023"],
        ],
        col_widths=[6.5 * cm, 4.5 * cm, 3.0 * cm, 3.5 * cm],
    ))
    story.append(Paragraph(
        "<b>We have completed 6 qualifying projects</b>, each of value not "
        "less than Rs. 25 Crore, within the last seven financial years ending "
        "31 March 2024. <b>Total qualifying projects: 6 (six)</b>. This "
        "exceeds the minimum requirement of three similar projects under "
        "clause B.2 of the tender document.",
        BODY,
    ))

    story.append(PageBreak())
    story.append(Paragraph("4.  STATUTORY COMPLIANCE -- GST REGISTRATION", H1))
    story.append(Paragraph(
        "Maharashtra Infra Engineering Limited is duly registered under the "
        "Goods and Services Tax (GST) Act, 2017. The relevant details are as "
        "under:",
        BODY,
    ))
    story.append(_kv_table([
        ["Legal Name of Business",  "Maharashtra Infra Engineering Limited"],
        ["GSTIN",                   "27AABCM4567P1Z3"],
        ["Date of Registration",    "01-July-2017"],
        ["Status",                  "ACTIVE"],
        ["Constitution of Business", "Public Limited Company"],
        ["Principal Place of Business", "Plot 47, Hiranandani Business Park, "
                                        "Powai, Mumbai 400076"],
    ]))
    story.append(Paragraph(
        "A copy of the GST registration certificate (Form GST REG-06) issued by "
        "the Office of the Commissioner, CGST &amp; Central Excise, Mumbai is "
        "enclosed as Annexure C-1.",
        BODY,
    ))

    story.append(Paragraph("5.  CERTIFICATION -- ISO 9001:2015", H1))
    story.append(Paragraph(
        "The Company holds a valid <b>ISO 9001:2015</b> Quality Management System "
        "certification issued by Bureau Veritas India Private Limited, an IAF "
        "MLA-recognised certification body. Details:",
        BODY,
    ))
    story.append(_kv_table([
        ["Certificate Number",  "BV-IND-QMS-2023-118476"],
        ["Issued To",           "Maharashtra Infra Engineering Limited"],
        ["Issuing Body",        "Bureau Veritas (India) Pvt. Ltd. (IAF/NABCB)"],
        ["Standard",            "ISO 9001:2015 -- Quality Management Systems"],
        ["Date of Issue",       "15-March-2023"],
        ["Date of Expiry",      "14-March-2026"],
        ["Status",              "VALID and IN FORCE"],
        ["Scope of Certification",
         "Design and Construction of Roads, Highways and Bridges"],
    ]))
    story.append(Paragraph(
        "The ISO 9001:2015 certificate is valid up to 14 March 2026, and is "
        "therefore not expired as on the bid submission date. A colour-scanned "
        "copy of the certificate is enclosed as Annexure C-2.",
        BODY,
    ))

    story.append(Paragraph("6.  LABOUR-LAW COMPLIANCE -- EPF AND ESI", H1))
    story.append(Paragraph(
        "The Company is duly registered under both the Employees' Provident Fund "
        "Act, 1952 and the Employees' State Insurance Act, 1948.",
        BODY,
    ))
    story.append(_kv_table([
        ["EPF Establishment Code",     "MH/MUM/2317698/000"],
        ["EPF Date of Coverage",       "01-October-2002"],
        ["ESI Code (Sub-Code)",        "31-12345-67-1100"],
        ["ESI Date of Coverage",       "12-November-2002"],
        ["Both Registrations Active?", "YES -- both EPF and ESI registrations active"],
    ]))
    story.append(Paragraph(
        "EPF allotment letter and ESI registration certificate are enclosed as "
        "Annexure C-3.",
        BODY,
    ))

    story.append(Paragraph("7.  INTEGRITY -- NON-BLACKLISTING DECLARATION", H1))
    story.append(Paragraph(
        "We, Maharashtra Infra Engineering Limited, having our registered office "
        "at Plot 47, Hiranandani Business Park, Powai, Mumbai 400076, "
        "hereby <b>DECLARE</b> that the Company is <b>NOT</b> blacklisted, debarred, "
        "suspended or banned by any Central Government department, State Government "
        "department, Public Sector Undertaking, autonomous body, or international "
        "lending agency as on the date of this declaration (18 May 2024). The "
        "Company has a clean record with respect to all past contracts and there "
        "is no pending arbitration or litigation that materially affects the "
        "Company's ability to perform the proposed contract.",
        BODY,
    ))
    story.append(Paragraph(
        "We further declare that any false or misleading information furnished "
        "in this bid shall render the bid liable for summary disqualification, "
        "forfeiture of EMD and blacklisting of the Company under the GFR 2017.",
        BODY,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>(Sri. R. K. Deshpande)<br/>"
        "Managing Director and Authorised Signatory<br/>"
        "Maharashtra Infra Engineering Limited<br/>Date: 18-May-2024",
        BODY_LEFT,
    ))

    doc.build(story)
    print(f"  generated bidder:  {path}  (strong / pass-all)")
    return path


# ---------------------------------------------------------------------------
# 3.  BIDDER #2  -- Sahyadri Construction Co.   (FINANCIALLY WEAK)
# ---------------------------------------------------------------------------
def generate_bidder_financially_weak() -> Path:
    path = OUTPUT_DIR / "bidder_sahyadri_construction.pdf"
    doc, story = _new_doc(path)

    story.append(Paragraph("TECHNICAL BID -- COVER LETTER AND ELIGIBILITY ANNEXURES", TITLE))
    story.append(Paragraph(
        "M/s. Sahyadri Construction Company<br/>"
        "Partnership Firm (Reg. under Indian Partnership Act, 1932)<br/>"
        "PAN: AAFFS1234K   |   Pune, Maharashtra",
        SUBTITLE,
    ))
    story.append(Paragraph("Tender: MoRTH/KSRDC/SH-275/2024-25/CW-014", BODY))
    story.append(Paragraph("Date of Submission: 19-May-2024", BODY))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Sub: Submission of Technical Bid", H1))
    story.append(Paragraph(
        "We, M/s. Sahyadri Construction Company, a registered partnership firm "
        "operating since 2011, hereby submit our technical bid for the captioned "
        "tender. We confirm that we have read and understood the tender conditions "
        "and our bid is in compliance with the same to the extent of the documents "
        "enclosed herewith.",
        BODY,
    ))

    story.append(Paragraph("ANNEXURE -- 1  : ANNUAL TURNOVER STATEMENT", H1))
    story.append(Paragraph(
        "The annual turnover of the firm for the last three financial years as "
        "per the audited Profit &amp; Loss statements certified by M/s. R. Joshi "
        "&amp; Co., Chartered Accountants (ICAI Firm Reg. No. 117823W) is "
        "presented below. Audited financial statements for FY 2021-22, FY 2022-23 "
        "and FY 2023-24 are appended:",
        BODY,
    ))
    story.append(_summary_table(
        ["Financial Year", "Audited Annual Turnover (Rs. Crore)"],
        [
            ["FY 2021-22",    "2.10"],
            ["FY 2022-23",    "2.85"],
            ["FY 2023-24",    "4.20"],
            ["Average (3 yr)", "3.05"],
        ],
        col_widths=[5.0 * cm, 7.0 * cm],
    ))
    story.append(Paragraph(
        "The three-year average annual turnover of <b>Rs. 3.05 Crore</b> is on "
        "the lower side relative to the threshold prescribed in clause B.1. The "
        "firm has, however, witnessed consistent growth over the period under "
        "review and its order book for FY 2024-25 stands at Rs. 12.40 Crore.",
        BODY,
    ))

    story.append(Paragraph("ANNEXURE -- 2  : SIMILAR PROJECTS COMPLETED", H1))
    story.append(Paragraph(
        "The following similar road / highway works have been completed by the "
        "firm during the last seven years (2017-18 to 2023-24):",
        BODY,
    ))
    story.append(_summary_table(
        ["Project", "Client", "Value (Rs. Cr)", "Year Completed"],
        [
            ["Resurfacing, MDR-12, Satara district",
             "PWD Maharashtra",        "26.40", "2019"],
            ["Strengthening of MDR-7, Sangli",
             "PWD Maharashtra",        "31.20", "2020"],
            ["Bypass road, Karad-Patan",
             "Karad Municipal Council", "27.85", "2022"],
            ["Widening of approach roads, MIDC Lonand",
             "MIDC",                   "29.10", "2023"],
        ],
        col_widths=[6.5 * cm, 4.5 * cm, 3.0 * cm, 3.5 * cm],
    ))
    story.append(Paragraph(
        "Four similar projects have been completed during the qualifying period, "
        "each of value not less than Rs. 25 Crore, with completion certificates "
        "from the respective client departments enclosed.",
        BODY,
    ))

    story.append(PageBreak())
    story.append(Paragraph("ANNEXURE -- 3  : GST AND STATUTORY COMPLIANCE", H1))
    story.append(_kv_table([
        ["GSTIN",                "27AAFFS1234K1Z6"],
        ["Date of Registration", "12-September-2017"],
        ["Status",               "ACTIVE"],
        ["State of Registration", "Maharashtra"],
    ]))
    story.append(Paragraph(
        "Copy of GST registration certificate (Form GST REG-06) is enclosed "
        "herewith.",
        BODY,
    ))

    story.append(Paragraph("ANNEXURE -- 4  : ISO 9001:2015 CERTIFICATION", H1))
    story.append(Paragraph(
        "The firm holds a valid ISO 9001:2015 Quality Management System "
        "certification issued by TUV India Pvt. Ltd. (IAF MLA member).",
        BODY,
    ))
    story.append(_kv_table([
        ["Certificate No.", "TUV-IN-QMS-2022-04781"],
        ["Issuing Body",    "TUV India Pvt. Ltd."],
        ["Standard",        "ISO 9001:2015"],
        ["Date of Issue",   "08-April-2022"],
        ["Date of Expiry",  "07-April-2025"],
        ["Status",          "VALID"],
    ]))

    story.append(Paragraph("ANNEXURE -- 5  : EPF AND ESI REGISTRATION", H1))
    story.append(_kv_table([
        ["EPF Code",   "MH/PUN/0987654/000"],
        ["ESI Code",   "33-78901-23-1100"],
        ["Both Registrations Active", "Yes (since 2012)"],
    ]))

    story.append(Paragraph("ANNEXURE -- 6  : NON-BLACKLISTING DECLARATION", H1))
    story.append(Paragraph(
        "We, M/s. Sahyadri Construction Company, hereby declare that the firm "
        "is <b>NOT</b> blacklisted, debarred or banned by any Central Government, "
        "State Government, Public Sector Undertaking or autonomous body as on "
        "the date of this declaration. We have a clean record with respect to "
        "all past and current contracts.",
        BODY,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>(Sri. Vikas Jadhav)<br/>"
        "Managing Partner and Authorised Signatory<br/>"
        "M/s. Sahyadri Construction Company<br/>Date: 19-May-2024",
        BODY_LEFT,
    ))

    doc.build(story)
    print(f"  generated bidder:  {path}  (financially weak: turnover Rs.3.05 Cr < 50)")
    return path


# ---------------------------------------------------------------------------
# 4.  BIDDER #3  -- Vidhya Builders & Contractors   (TECHNICALLY WEAK)
# ---------------------------------------------------------------------------
def generate_bidder_technically_weak() -> Path:
    path = OUTPUT_DIR / "bidder_vidhya_builders.pdf"
    doc, story = _new_doc(path)

    story.append(Paragraph("VIDHYA BUILDERS &amp; CONTRACTORS PVT. LTD.", TITLE))
    story.append(Paragraph(
        "TECHNICAL BID -- ELIGIBILITY DOCUMENTATION<br/>"
        "Tender: MoRTH/KSRDC/SH-275/2024-25/CW-014<br/>"
        "Date: 19-May-2024",
        SUBTITLE,
    ))

    story.append(Paragraph("1.  ABOUT US", H1))
    story.append(Paragraph(
        "Vidhya Builders &amp; Contractors Pvt. Ltd., incorporated in 2014 with "
        "CIN U70109TN2014PTC094321, is engaged in commercial real-estate, "
        "industrial buildings, and selective road / civil works in Tamil Nadu "
        "and Andhra Pradesh. Our registered office is at No. 18, Anna Salai, "
        "Chennai 600002.",
        BODY,
    ))

    story.append(Paragraph("2.  FINANCIAL POSITION -- ANNUAL TURNOVER", H1))
    story.append(Paragraph(
        "The audited annual turnover of the Company for the last three financial "
        "years, as certified by M/s. Sundar &amp; Sundar Chartered Accountants "
        "(ICAI Firm Reg. No. 005612S), is presented below:",
        BODY,
    ))
    story.append(_summary_table(
        ["Financial Year", "Annual Turnover (Rs. Crore)"],
        [
            ["FY 2021-22", "55.30"],
            ["FY 2022-23", "63.40"],
            ["FY 2023-24", "68.10"],
            ["3-yr average", "62.27"],
        ],
        col_widths=[5.0 * cm, 7.0 * cm],
    ))
    story.append(Paragraph(
        "The three-year arithmetic mean of <b>Rs. 62.27 Crore</b> is comfortably "
        "above the minimum threshold of Rs. 50 Crore prescribed in clause B.1 "
        "of the tender document.",
        BODY,
    ))

    story.append(Paragraph("3.  TECHNICAL EXPERIENCE -- SIMILAR PROJECTS", H1))
    story.append(Paragraph(
        "We bring forward the following <b>1 (one)</b> qualifying highway / "
        "road project completed during the last 7 financial years. Our "
        "experience is otherwise focused on commercial buildings and "
        "industrial structures, which are not classified as 'similar projects' "
        "under clause B.2 of the tender:",
        BODY,
    ))
    story.append(_summary_table(
        ["Project", "Client", "Value (Rs. Cr)", "Year Completed"],
        [
            ["Strengthening of MDR-216, Salem-Yercaud section",
             "PWD Tamil Nadu",       "32.40", "2022"],
        ],
        col_widths=[6.5 * cm, 4.5 * cm, 3.0 * cm, 3.5 * cm],
    ))
    story.append(Paragraph(
        "We respectfully submit that we have executed several commercial-building "
        "and industrial-construction projects of larger contract value, but as "
        "those works do not strictly satisfy the 'similar projects' definition "
        "under clause B.2, only the qualifying project of Rs. 32.40 Crore has "
        "been disclosed above.",
        BODY,
    ))

    story.append(Paragraph("4.  GST REGISTRATION", H1))
    story.append(_kv_table([
        ["Legal Name", "Vidhya Builders & Contractors Pvt. Ltd."],
        ["GSTIN",      "33AABCV9876N1Z2"],
        ["Date of Registration", "01-July-2017"],
        ["Status",     "ACTIVE"],
    ]))

    story.append(Paragraph("5.  ISO 9001:2015 CERTIFICATION", H1))
    story.append(Paragraph(
        "The Company holds a valid ISO 9001:2015 certification issued by "
        "Intertek India Pvt. Ltd.:",
        BODY,
    ))
    story.append(_kv_table([
        ["Certificate Number", "INTK-IN-QMS-2023-09823"],
        ["Issuing Body",       "Intertek India Pvt. Ltd."],
        ["Date of Issue",      "21-June-2023"],
        ["Date of Expiry",     "20-June-2026"],
        ["Status",             "VALID and IN FORCE"],
    ]))

    story.append(Paragraph("6.  EPF AND ESI", H1))
    story.append(_kv_table([
        ["EPF Code", "TN/CHN/0123456/000"],
        ["ESI Code", "51-23456-78-1100"],
        ["Status",   "Both registrations active and in compliance"],
    ]))

    story.append(Paragraph("7.  BLACKLISTING DECLARATION", H1))
    story.append(Paragraph(
        "We, Vidhya Builders &amp; Contractors Pvt. Ltd., hereby declare that "
        "the Company is <b>NOT</b> blacklisted, debarred, suspended or banned "
        "by any Central Government department, State Government department, "
        "PSU or autonomous body as on the date of this declaration.",
        BODY,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>(Sri. K. Subramaniam)<br/>"
        "Managing Director and Authorised Signatory<br/>"
        "Vidhya Builders &amp; Contractors Pvt. Ltd.<br/>Date: 19-May-2024",
        BODY_LEFT,
    ))

    doc.build(story)
    print(f"  generated bidder:  {path}  (technically weak: only 1 similar project)")
    return path


# ---------------------------------------------------------------------------
# 5.  BIDDER #4  -- Konkan Engineering Pvt Ltd   (MISSING CERTIFICATIONS)
#                   Will be RASTERISED -> scanned-PDF for OCR stress
# ---------------------------------------------------------------------------
def generate_bidder_missing_certs(intermediate_dir: Path) -> Path:
    """
    Build the digital draft, then convert it to a SCANNED PDF (no text layer)
    so that the ingestion pipeline must use Tesseract OCR.
    """
    digital = intermediate_dir / "_konkan_digital.pdf"
    final   = OUTPUT_DIR / "bidder_konkan_engineering.pdf"

    doc, story = _new_doc(digital)

    story.append(Paragraph("KONKAN ENGINEERING PVT. LTD.", TITLE))
    story.append(Paragraph("BID DOCUMENTS -- TECHNICAL COVER", SUBTITLE))
    story.append(Paragraph(
        "Tender Reference: MoRTH/KSRDC/SH-275/2024-25/CW-014",
        BODY,
    ))
    story.append(Paragraph("Date of Submission: 20-May-2024", BODY))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("1.  COMPANY DETAILS", H1))
    story.append(Paragraph(
        "Konkan Engineering Private Limited (CIN U45200GA2009PTC067432) is a "
        "Goa-based civil-engineering company specialising in coastal road, "
        "drainage and shore-protection works. The company has been in operation "
        "for over fifteen years and operates principally in the states of Goa, "
        "Maharashtra coastal districts, and Karnataka coastal districts.",
        BODY,
    ))

    story.append(Paragraph("2.  ANNUAL TURNOVER STATEMENT", H1))
    story.append(Paragraph(
        "Audited annual turnover for the last three financial years, certified "
        "by M/s. Pereira &amp; Associates, Chartered Accountants:",
        BODY,
    ))
    story.append(_summary_table(
        ["Financial Year", "Annual Turnover (Rs. Crore)"],
        [
            ["FY 2021-22", "58.40"],
            ["FY 2022-23", "67.30"],
            ["FY 2023-24", "72.85"],
            ["3-yr average", "66.18"],
        ],
        col_widths=[5.0 * cm, 7.0 * cm],
    ))
    story.append(Paragraph(
        "The three-year arithmetic mean of <b>Rs. 66.18 Crore</b> exceeds the "
        "minimum required average annual turnover of Rs. 50 Crore.",
        BODY,
    ))

    story.append(Paragraph("3.  EXPERIENCE -- SIMILAR PROJECTS COMPLETED", H1))
    story.append(_summary_table(
        ["Project", "Client", "Value (Rs. Cr)", "Year"],
        [
            ["Coastal road, Panaji-Dona Paula",
             "PWD Goa",            "42.50", "2019"],
            ["Drainage and pavement, NH-66 Karwar-Ankola",
             "NHAI Mangaluru PIU", "31.85", "2021"],
            ["Strengthening of MDR-3, Margao-Cancona",
             "PWD Goa",            "28.40", "2022"],
            ["Shore-protection works, Anjuna-Vagator",
             "PWD Goa",            "26.10", "2023"],
        ],
        col_widths=[6.5 * cm, 4.5 * cm, 3.0 * cm, 3.5 * cm],
    ))
    story.append(Paragraph(
        "<b>Total qualifying projects: 4 (four)</b> similar road / coastal "
        "civil-engineering projects, each of value not less than Rs. 25 Crore, "
        "completed during the last seven financial years. This count exceeds "
        "the minimum requirement of three similar projects under clause B.2.",
        BODY,
    ))

    story.append(Paragraph("4.  GST REGISTRATION", H1))
    story.append(_kv_table([
        ["GSTIN",  "30AABCK1234Q1Z9"],
        ["Status", "ACTIVE"],
        ["State",  "Goa"],
    ]))

    story.append(Paragraph("5.  ISO 9001:2015 CERTIFICATION", H1))
    story.append(_kv_table([
        ["Certification Status",
         "NOT HELD -- Company does NOT hold a valid ISO 9001:2015 certificate"],
        ["Reason",
         "Application filed with TUV-Nord India; audit scheduled August 2024"],
        ["Certificate Number",  "Not applicable -- no certificate yet issued"],
        ["Expiry Date",         "Not applicable"],
    ]))
    story.append(Paragraph(
        "<b>ISO 9001:2015 status: NOT HELD.</b> Konkan Engineering Pvt. Ltd. "
        "explicitly declares that the Company <b>does not hold</b> any valid "
        "ISO 9001:2015 certification as on the date of bid submission. The "
        "ISO audit is pending. We respectfully request the Authority to "
        "consider our bid in view of our project experience.",
        BODY,
    ))

    story.append(Paragraph("6.  EPF AND ESI REGISTRATION", H1))
    story.append(_kv_table([
        ["EPF Status",
         "NOT REGISTERED -- EPF code not yet allotted; application pending"],
        ["EPF Code",
         "Not yet allotted (application filed January 2024 -- pending)"],
        ["ESI Status",          "Registered (active)"],
        ["ESI Code",             "30-45678-90-1100"],
    ]))
    story.append(Paragraph(
        "<b>EPF registration: NOT REGISTERED.</b> The Company explicitly "
        "declares that EPF registration <b>has not yet been issued</b> to "
        "Konkan Engineering Pvt. Ltd. Coverage formalities are still in "
        "process with the Regional Provident Fund Commissioner, Goa. ESI "
        "registration is active but EPF is pending and not yet allotted.",
        BODY,
    ))

    story.append(Paragraph("7.  NON-BLACKLISTING DECLARATION", H1))
    story.append(Paragraph(
        "Konkan Engineering Pvt. Ltd. hereby declares that the Company is NOT "
        "blacklisted, debarred or banned by any Central Government, State "
        "Government, Public Sector Undertaking or autonomous body as on the "
        "date of this declaration.",
        BODY,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>(Smt. Anjali D'Souza)<br/>"
        "Director and Authorised Signatory<br/>"
        "Konkan Engineering Pvt. Ltd.<br/>Date: 20-May-2024",
        BODY_LEFT,
    ))
    doc.build(story)

    # Now rasterise into a scanned-looking PDF (no text layer)
    _rasterise_to_scanned_pdf(
        digital, final,
        dpi=200, blur=False, rotate_deg=0.0, jpeg_quality=78,
    )
    digital.unlink(missing_ok=True)
    print(f"  generated bidder:  {final}  (SCANNED, missing ISO + EPF)")
    return final


# ---------------------------------------------------------------------------
# 6.  BIDDER #5  -- Deccan Civil Works   (AMBIGUOUS / INCONSISTENT)
#                   Rasterised + slight rotation + blur (low-quality scan)
# ---------------------------------------------------------------------------
def generate_bidder_ambiguous(intermediate_dir: Path) -> Path:
    digital = intermediate_dir / "_deccan_digital.pdf"
    final   = OUTPUT_DIR / "bidder_deccan_civil_works.pdf"

    doc, story = _new_doc(digital)

    story.append(Paragraph("DECCAN CIVIL WORKS -- TECHNICAL BID SUBMISSION", TITLE))
    story.append(Paragraph(
        "Tender: MoRTH/KSRDC/SH-275/2024-25/CW-014<br/>"
        "Submitted on: 20-May-2024",
        SUBTITLE,
    ))

    story.append(Paragraph("Company Particulars", H1))
    story.append(Paragraph(
        "M/s. Deccan Civil Works is a sole proprietorship establishment "
        "registered with the Department of Industries, Telangana. The "
        "establishment has been operational since 2009 and is engaged in "
        "general civil-engineering services across Telangana and parts of "
        "Andhra Pradesh.",
        BODY,
    ))

    story.append(Paragraph("Financials", H1))
    story.append(Paragraph(
        "We submit that our annual turnover for the recent financial years is "
        "in the order of approximately fifty-five crore rupees. Detailed "
        "audited statements for FY 2022-23 indicated a turnover of "
        "Rs. 51.20 Crore. The figures for FY 2023-24 are still being finalised "
        "by our auditors and may be in the range of Rs. 48 to 60 Crore. "
        "FY 2021-22 turnover, as per our internal accounts, was approximately "
        "Rs. 42 Crore though the audited figure may vary.",
        BODY,
    ))
    story.append(Paragraph(
        "Estimated 3-year average turnover: <b>Rs. 49 Crore (approximate)</b>. "
        "Please note that the actual audited mean may differ marginally from "
        "this estimate.",
        BODY,
    ))

    story.append(Paragraph("Project Experience", H1))
    story.append(Paragraph(
        "Over the past several years we have completed many road, drainage, "
        "and pavement works across Telangana. Major projects include the "
        "Hyderabad Outer Ring Road service-road improvements (value not less "
        "than Rs. 30 Crore, exact figure to be retrieved from records), the "
        "Karimnagar bypass strengthening works (value approximately "
        "Rs. 26 Crore as per memory), and several smaller works each in the "
        "range of Rs. 8-15 Crore. Total of approximately five major works "
        "have been executed during the relevant period; documentary "
        "completion certificates are being arranged and will be submitted "
        "as soon as they are received from the respective client departments.",
        BODY,
    ))
    story.append(_summary_table(
        ["Project (approx.)", "Client", "Value (Cr)", "Year"],
        [
            ["Hyderabad ORR service-road improvements",
             "HMDA",          "30+",  "2020"],
            ["Karimnagar bypass strengthening",
             "PWD Telangana", "~26",  "2021"],
            ["Pavement works -- ORR Patancheru-Shamshabad",
             "HMDA",          "~22",  "2022"],
        ],
        col_widths=[6.5 * cm, 4.0 * cm, 2.5 * cm, 2.5 * cm],
    ))

    story.append(Paragraph("GST and Statutory Registrations", H1))
    story.append(Paragraph(
        "We hold an active GST registration in Telangana. GSTIN: "
        "36AABFD7654L1Z3. Date of registration on file with the GST Department.",
        BODY,
    ))

    story.append(Paragraph("ISO Certification", H1))
    story.append(Paragraph(
        "The proprietor confirms that an ISO 9001 certification was obtained "
        "earlier and is being renewed by the certification authority. "
        "Renewal documentation is awaited.",
        BODY,
    ))

    story.append(Paragraph("EPF / ESI", H1))
    story.append(Paragraph(
        "EPF and ESI compliance is being maintained as applicable to the "
        "establishment. Specific code numbers can be furnished on request.",
        BODY,
    ))

    story.append(Paragraph("Blacklisting Declaration", H1))
    story.append(Paragraph(
        "We confirm that the establishment has not been formally blacklisted "
        "by any government authority. There may be a past matter of contract "
        "dispute with a municipal authority which was settled amicably; the "
        "matter is not pending and does not amount to debarment.",
        BODY,
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<b>Sd/-</b><br/>(Sri. M. Venkat Reddy)<br/>Sole Proprietor<br/>"
        "M/s. Deccan Civil Works<br/>Date: 20-May-2024",
        BODY_LEFT,
    ))
    doc.build(story)

    # Rasterise with slight rotation + blur (low-quality scanner simulation).
    _rasterise_to_scanned_pdf(
        digital, final,
        dpi=180, blur=True, rotate_deg=0.6, jpeg_quality=62,
    )
    digital.unlink(missing_ok=True)
    print(f"  generated bidder:  {final}  (SCANNED + rotated, ambiguous)")
    return final


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def main() -> None:
    print("VAJANS Production Simulation -- generating dataset")
    print(f"Output directory: {OUTPUT_DIR}")

    # Clean output dir for reproducibility (verify_all relies on the file
    # checksums staying constant across consecutive verify-runs).
    if OUTPUT_DIR.exists():
        for p in OUTPUT_DIR.iterdir():
            if p.is_file():
                p.unlink()

    intermediate_dir = OUTPUT_DIR / "_intermediate"
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    try:
        generate_tender()
        generate_bidder_strong()
        generate_bidder_financially_weak()
        generate_bidder_technically_weak()
        generate_bidder_missing_certs(intermediate_dir)
        generate_bidder_ambiguous(intermediate_dir)
    finally:
        if intermediate_dir.exists():
            shutil.rmtree(intermediate_dir, ignore_errors=True)

    print("\nDataset generation complete:")
    for p in sorted(OUTPUT_DIR.iterdir()):
        size_kb = p.stat().st_size // 1024
        print(f"  {p.name:42s}  {size_kb:5d} KB")


if __name__ == "__main__":
    main()
