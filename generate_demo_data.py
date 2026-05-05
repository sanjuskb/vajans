"""
VAJANS — Demo PDF Generator
Creates 3 realistic government tender evaluation PDFs.

Usage:
    cd ~/vajans
    source backend/.venv/bin/activate
    python generate_demo_data.py
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

OUTPUT_DIR = Path("data/sample")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_styles():
    styles = getSampleStyleSheet()
    heading1 = ParagraphStyle(
        "Heading1Custom",
        parent=styles["Heading1"],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=14,
        textColor=HexColor("#1a237e"),
    )
    heading2 = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=10,
        textColor=HexColor("#283593"),
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        spaceBefore=4,
        leading=14,
        alignment=TA_JUSTIFY,
    )
    bold_body = ParagraphStyle(
        "BoldBody",
        parent=body,
        fontName="Helvetica-Bold",
    )
    centered = ParagraphStyle(
        "Centered",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=16,
        textColor=HexColor("#0d47a1"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    return {
        "h1": heading1,
        "h2": heading2,
        "body": body,
        "bold": bold_body,
        "centered": centered,
        "title": title_style,
        "normal": styles["Normal"],
    }


def para(text, style):
    return Paragraph(text, style)


def spacer(h=0.3):
    return Spacer(1, h * cm)


# ─────────────────────────────────────────────────────────────────────────────
# FILE 1: CRPF Construction Tender
# ─────────────────────────────────────────────────────────────────────────────

def create_tender_crpf(styles):
    path = OUTPUT_DIR / "tender_crpf_2024.pdf"
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []

    story.append(para("CENTRAL RESERVE POLICE FORCE (CRPF)", styles["title"]))
    story.append(para("MINISTRY OF HOME AFFAIRS — GOVERNMENT OF INDIA", styles["centered"]))
    story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#1a237e")))
    story.append(spacer(0.4))
    story.append(para("TENDER NOTICE", styles["h1"]))
    story.append(para("Tender Reference No.: CRPF/PWD/CON/2024/001", styles["bold"]))
    story.append(para("Date of Issue: 15 January 2024", styles["body"]))
    story.append(para("Last Date of Submission: 28 February 2024", styles["body"]))
    story.append(para("Type: Open Competitive Tender (National Level)", styles["body"]))
    story.append(spacer())

    story.append(para("1. INTRODUCTION AND SCOPE OF WORK", styles["h1"]))
    story.append(para(
        "The Central Reserve Police Force (CRPF), under the aegis of the Ministry of Home Affairs, "
        "Government of India, invites sealed tenders from eligible and experienced civil construction "
        "contractors for the construction of a new Residential Complex and Administrative Block at "
        "CRPF Group Centre, Rampur, Uttar Pradesh. The project encompasses construction of multi-storey "
        "residential quarters, a central administrative block, internal roads, drainage systems, "
        "water supply infrastructure, and compound boundary walls.",
        styles["body"]))
    story.append(para(
        "The total estimated project cost is approximately Rs. 18.5 Crore (Rupees Eighteen Crore "
        "Fifty Lakhs only), inclusive of all civil, electrical, plumbing, and finishing works. "
        "The project duration is 24 months from the date of award of work. Contractors are expected "
        "to deploy a dedicated project team including a qualified Civil Engineer and Site Supervisor "
        "throughout the project lifecycle.",
        styles["body"]))
    story.append(para(
        "The scope of work includes but is not limited to: site preparation and excavation, "
        "RCC frame construction for G+3 residential blocks, brick masonry works, plastering and "
        "finishing, flooring and tiling, roofing, electrical installations (including LT supply, "
        "earthing, and solar panel provision), plumbing and sanitary works, firefighting systems, "
        "CCTV surveillance infrastructure, construction of boundary walls and security cabins, "
        "internal roads with interlocking paver blocks, storm water drainage, sewage treatment "
        "plant of capacity 100 KLD, rainwater harvesting pits, and all allied civil works.",
        styles["body"]))
    story.append(spacer())

    story.append(para("2. ELIGIBILITY CRITERIA", styles["h1"]))
    story.append(para(
        "All bidders must strictly satisfy the following eligibility criteria. Non-compliance with "
        "any mandatory criterion will result in summary rejection of the bid. The decision of the "
        "Tender Evaluation Committee shall be final and binding. Bidders must submit documentary "
        "evidence in support of each criterion along with the technical bid.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.1 Financial Eligibility — Annual Turnover", styles["h2"]))
    story.append(para(
        "The bidder must have an average annual turnover of not less than Rs. 5 Crore (Rupees Five "
        "Crore only) from civil construction activities during the last three consecutive financial "
        "years, i.e., 2021-22, 2022-23, and 2023-24. The turnover requirement applies to construction "
        "activities only; income from trading, manufacturing, or other non-construction activities "
        "shall not be considered. Annual turnover shall be certified by a Chartered Accountant with "
        "membership number and UDIN, supported by audited balance sheets and profit & loss accounts "
        "for each of the three financial years. Bidders who do not meet the Rs. 5 Crore minimum "
        "annual turnover threshold for any of the three years shall be treated as ineligible.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.2 Technical Eligibility — Similar Work Experience", styles["h2"]))
    story.append(para(
        "The bidder must have successfully completed at least three (3) similar civil construction "
        "projects, each of contract value not less than Rs. 2 Crore (Rupees Two Crore only) during "
        "the last five financial years ending 31 March 2024. Similar work is defined as construction "
        "of residential or institutional buildings involving RCC frame structure and brick masonry. "
        "Works of smaller value shall not be clubbed to meet the minimum threshold. Only projects "
        "that have received the Completion Certificate from the competent authority shall be considered "
        "as completed. Projects that are still in progress or have been abandoned shall not be counted.",
        styles["body"]))
    story.append(para(
        "The bidder must submit Completion Certificates issued by the client organisation (Government "
        "department, PSU, or autonomous body) for each qualifying project. The certificate must clearly "
        "state the project name, scope, contract value, and date of completion. Self-attested copies "
        "from private sector clients will require additional verification by the Evaluation Committee. "
        "In case of joint ventures, the lead partner must individually meet at least 50% of the "
        "experience criteria.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.3 Goods and Services Tax (GST) Registration", styles["h2"]))
    story.append(para(
        "Every bidder must hold a valid Goods and Services Tax (GST) registration under the "
        "Central Goods and Services Tax Act, 2017 and the State/Union Territory Goods and Services "
        "Tax Act. The GST registration certificate must be valid as on the date of bid submission. "
        "A copy of the GST registration certificate bearing the GSTIN (15-digit alphanumeric number) "
        "must be submitted with the bid. Bidders who are exempted from GST registration under "
        "applicable rules must provide a certificate from the concerned GST authority confirming "
        "the exemption.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.4 ISO 9001:2015 Quality Management Certification", styles["h2"]))
    story.append(para(
        "The bidder must hold a valid ISO 9001:2015 Quality Management System (QMS) certification "
        "from an accredited certification body. The ISO certificate must be currently valid as on "
        "the date of bid submission and must not have expired. The certification scope must cover "
        "civil construction activities. Bidders are required to submit a copy of the ISO 9001:2015 "
        "certificate along with evidence of its current validity, such as the latest surveillance "
        "audit report or renewal certificate. Expired certificates or certificates under renewal "
        "process shall NOT be accepted.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.5 EPF and ESI Registration", styles["h2"]))
    story.append(para(
        "The bidder must be duly registered under the Employees Provident Fund and Miscellaneous "
        "Provisions Act, 1952 and must hold a valid EPF registration number (Establishment Code). "
        "Additionally, the bidder must be registered under the Employees State Insurance Act, 1948 "
        "and must hold a valid ESI registration number. Copies of the EPF registration letter/allotment "
        "certificate and ESI registration certificate must be submitted. The bidder must also submit "
        "the latest EPF and ESI monthly remittance challan to demonstrate active compliance. Bidders "
        "employing fewer than 20 workers may be exempt from EPF; however, ESI compliance is mandatory "
        "for all bidders employing five or more employees.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("2.6 Blacklisting and Debarment Declaration", styles["h2"]))
    story.append(para(
        "The bidder must not be blacklisted, debarred, or placed on any holiday list by any "
        "Government department (Central or State), Public Sector Undertaking (PSU), Autonomous Body, "
        "or any other Government entity in India as on the date of bid submission. The bidder must "
        "submit a self-declaration on company letterhead, duly signed by the authorised signatory, "
        "certifying that the firm has not been blacklisted by any government body. This declaration "
        "must be supported by an affidavit on stamp paper of minimum Rs. 100 value, notarised by a "
        "competent Notary Public. Any misrepresentation in the declaration shall lead to immediate "
        "disqualification and may result in legal action.",
        styles["body"]))
    story.append(spacer())

    story.append(para("3. BID SECURITY AND PERFORMANCE SECURITY", styles["h1"]))
    story.append(para(
        "Every bidder must submit an Earnest Money Deposit (EMD) of Rs. 18.50 Lakhs (Rupees Eighteen "
        "Lakh Fifty Thousand only) in the form of a Demand Draft or Bank Guarantee from a nationalised "
        "bank in favour of the Commandant, CRPF Group Centre Rampur, payable at Rampur, Uttar Pradesh. "
        "The EMD shall be valid for 180 days from the last date of bid submission. The successful bidder "
        "shall be required to furnish a Performance Security of 5% of the contract value within 15 days "
        "of receipt of Letter of Intent. Failure to submit the Performance Security shall result in "
        "forfeiture of the EMD and cancellation of the award.",
        styles["body"]))
    story.append(spacer())

    story.append(para("4. DOCUMENT REQUIREMENTS", styles["h1"]))
    story.append(para(
        "Technical bid must include: (a) Tender form with all required declarations, "
        "(b) Copy of PAN card of the firm, (c) Copy of GST registration certificate, "
        "(d) Copy of ISO 9001:2015 certificate, (e) Copy of EPF and ESI registration certificates, "
        "(f) Audited financial statements (Balance Sheet and P&L) for last 3 financial years certified "
        "by a CA with UDIN, (g) List of completed similar works with Completion Certificates, "
        "(h) Non-blacklisting declaration and affidavit, (i) List of key technical personnel to be "
        "deployed with their qualification certificates, (j) List of major equipment available with "
        "the firm, (k) Solvency certificate from a scheduled bank for minimum Rs. 5 Crore.",
        styles["body"]))
    story.append(spacer())

    story.append(para("5. TERMS AND CONDITIONS", styles["h1"]))
    story.append(para(
        "All bids must be submitted in sealed envelopes separately for Technical Bid and Financial Bid. "
        "Bids received after the closing date and time shall not be entertained. CRPF reserves the right "
        "to reject any or all bids without assigning any reason whatsoever. The Purchaser also reserves "
        "the right to cancel the tender process at any stage without incurring any obligation to bidders. "
        "All prices must be quoted in Indian Rupees only and must be inclusive of all applicable taxes, "
        "duties, levies and charges except GST which shall be extra as applicable.",
        styles["body"]))
    story.append(para(
        "The contractor shall be responsible for compliance with all applicable labour laws, including "
        "but not limited to the Minimum Wages Act, Building and Other Construction Workers Act, "
        "Contract Labour Act, and all State Government notifications. Any penalties arising from "
        "non-compliance with labour laws shall be the sole responsibility of the contractor. "
        "The contractor must also maintain a Register of Contractors at the site and display all "
        "required notices under the Contract Labour (Regulation and Abolition) Act.",
        styles["body"]))
    story.append(para(
        "Disputes arising from this contract shall be resolved through arbitration in accordance with "
        "the Arbitration and Conciliation Act, 1996. The venue of arbitration shall be New Delhi. "
        "The language of arbitration proceedings shall be English or Hindi. The award of the Arbitral "
        "Tribunal shall be final and binding on both parties. Courts in New Delhi shall have exclusive "
        "jurisdiction over any legal proceedings arising from this tender.",
        styles["body"]))
    story.append(spacer())

    story.append(para("6. CONTACT INFORMATION", styles["h1"]))
    story.append(para(
        "For any queries or clarifications related to this tender, please contact: The Deputy "
        "Commandant (Works), CRPF Group Centre, Rampur, Uttar Pradesh — 244901. Phone: 0595-2350XXX, "
        "Email: crpf.gcrpr.works@gov.in. All queries must be submitted in writing at least 7 days "
        "before the last date of submission. Verbal queries shall not be entertained.",
        styles["body"]))

    doc.build(story)
    print(f"Created: {path} ({path.stat().st_size // 1024} KB)")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# FILE 2: InfraTech Solutions — ELIGIBLE bidder
# ─────────────────────────────────────────────────────────────────────────────

def create_bidder_infratech(styles):
    path = OUTPUT_DIR / "bidder_infratech_solutions.pdf"
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []

    story.append(para("INFRATECH SOLUTIONS PVT. LTD.", styles["title"]))
    story.append(para("Pre-Qualification Bid Document", styles["centered"]))
    story.append(para(
        "Tender Reference: CRPF/PWD/CON/2024/001 | Date: 10 February 2024",
        styles["centered"]))
    story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#1b5e20")))
    story.append(spacer(0.4))

    story.append(para("1. COMPANY OVERVIEW", styles["h1"]))
    story.append(para(
        "InfraTech Solutions Pvt. Ltd. is a registered civil construction company incorporated "
        "under the Companies Act, 2013. The company was founded in 2008 and has over 16 years of "
        "experience in executing residential, institutional, and industrial construction projects "
        "across Uttar Pradesh, Uttarakhand, and Delhi NCR. Our registered office is located at "
        "Plot No. 42, Sector 18, Noida, Uttar Pradesh — 201301. CIN: U45200UP2008PTC034256.",
        styles["body"]))
    story.append(para(
        "The company employs over 350 permanent staff including qualified civil engineers, "
        "structural designers, quantity surveyors, site supervisors, and skilled workers. "
        "We have a dedicated Quality Assurance division that ensures all projects comply with "
        "IS codes and client specifications. Our fleet includes 12 JCB excavators, 8 concrete "
        "batching plants, 15 transit mixers, and extensive scaffolding and shuttering equipment.",
        styles["body"]))
    story.append(para(
        "InfraTech Solutions has successfully delivered projects for government clients including "
        "CRPF, ITBP, Border Security Force, CPWD, UPRNN, and various municipal corporations. "
        "We have a proven track record of on-time delivery and have never been issued a notice "
        "for delay beyond the permissible extension period in any government project.",
        styles["body"]))
    story.append(spacer())

    story.append(para("2. FINANCIAL ELIGIBILITY — ANNUAL TURNOVER", styles["h1"]))
    story.append(para(
        "InfraTech Solutions Pvt. Ltd. has consistently maintained a strong financial position "
        "with turnover growing year-on-year. The annual turnover from civil construction activities "
        "for the last three financial years, as certified by our statutory auditors M/s Sharma & "
        "Associates (CA Firm Registration No. 012345N), is as follows:",
        styles["body"]))
    story.append(spacer(0.2))

    turnover_data = [
        ["Financial Year", "Annual Turnover (Civil Construction)", "Growth"],
        ["2021-22", "Rs. 8.20 Crore", "—"],
        ["2022-23", "Rs. 9.10 Crore", "+10.97%"],
        ["2023-24", "Rs. 10.40 Crore", "+14.29%"],
        ["3-Year Average", "Rs. 9.23 Crore", "(Minimum required: Rs. 5 Crore)"],
    ]
    table = Table(turnover_data, colWidths=[5*cm, 7*cm, 5*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1b5e20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#e8f5e9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, HexColor("#f1f8e9")]),
    ]))
    story.append(table)
    story.append(spacer(0.3))

    story.append(para(
        "The turnover figures are supported by audited financial statements (Balance Sheet and "
        "Profit & Loss Account) for each financial year, duly certified by the statutory auditor "
        "with UDIN numbers: FY 2021-22 — UDIN: 22ABCDE1234F5G, FY 2022-23 — UDIN: 23ABCDE5678H9J, "
        "FY 2023-24 — UDIN: 24ABCDE9012K3L. The turnover figures are exclusively from civil "
        "construction activities and exclude any income from trading or other non-construction businesses.",
        styles["body"]))
    story.append(spacer())

    story.append(para("3. TECHNICAL ELIGIBILITY — SIMILAR WORK EXPERIENCE", styles["h1"]))
    story.append(para(
        "InfraTech Solutions has successfully completed five (5) similar civil construction projects "
        "within the last five financial years (2019-24), all involving construction of residential "
        "or institutional buildings with RCC frame structure. Each project was completed on time "
        "and received a Completion Certificate from the respective client organisation. "
        "All five projects individually exceed the minimum threshold of Rs. 2 Crore.",
        styles["body"]))
    story.append(spacer(0.2))

    projects_data = [
        ["S.No.", "Project Name", "Client", "Value (Rs.)", "Completion Date"],
        ["1", "Construction of 48 Type-III Qtrs, ITBP Dehradun", "ITBP / MHA", "5.80 Crore", "March 2020"],
        ["2", "Residential Qtrs G+3, CRPF Lucknow", "CRPF / MHA", "6.20 Crore", "November 2021"],
        ["3", "Admin Block + Residential, UPRNN Phase-I", "UPRNN", "4.50 Crore", "August 2022"],
        ["4", "Construction of BSF Camp, Pilibhit", "BSF / MHA", "3.90 Crore", "January 2023"],
        ["5", "Residential Complex 64 Units, AWHO Meerut", "AWHO", "7.10 Crore", "September 2023"],
    ]
    table2 = Table(projects_data, colWidths=[1.2*cm, 6*cm, 3.5*cm, 2.8*cm, 3*cm])
    table2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1b5e20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#f1f8e9")]),
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ]))
    story.append(table2)
    story.append(spacer(0.3))

    story.append(para(
        "Completion Certificates for all five projects are enclosed as Annexure-C. Each certificate "
        "is issued on the official letterhead of the client organisation and bears the signature of "
        "the competent authority (not below the rank of Executive Engineer or equivalent). "
        "All projects have been completed without any arbitration or litigation.",
        styles["body"]))
    story.append(spacer())

    story.append(para("4. STATUTORY REGISTRATIONS AND CERTIFICATIONS", styles["h1"]))
    story.append(para("4.1 GST Registration", styles["h2"]))
    story.append(para(
        "InfraTech Solutions Pvt. Ltd. is duly registered under the Goods and Services Tax Act. "
        "GSTIN: 29AABCI1234F1Z5. The GST registration is valid and active. The company regularly "
        "files monthly GST returns (GSTR-1 and GSTR-3B) and is fully compliant with all GST "
        "obligations. GST registration certificate is enclosed as Annexure-D.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.2 ISO 9001:2015 Certification", styles["h2"]))
    story.append(para(
        "InfraTech Solutions Pvt. Ltd. holds a valid ISO 9001:2015 Quality Management System "
        "certification issued by Bureau Veritas Certification India Pvt. Ltd. (Accreditation Body: "
        "NABCB, India). Certificate Number: BVC-IND-QMS-2021-0456. The certification scope covers: "
        "Design, Engineering, Procurement and Construction of Residential and Institutional Buildings. "
        "Certificate issued date: 15 March 2021. Valid up to: 14 March 2026. The certificate is "
        "current and fully valid as on the date of this bid submission. Latest surveillance audit "
        "was successfully completed in November 2023 with zero major non-conformities.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.3 EPF Registration", styles["h2"]))
    story.append(para(
        "The company is registered under the Employees Provident Fund and Miscellaneous Provisions "
        "Act, 1952. EPF Establishment Code: UP/LKO/0012345/XXX. The company regularly contributes "
        "to PF on behalf of all eligible employees and has never defaulted on PF payments. "
        "Monthly EPF remittance challans for the last 6 months are enclosed as Annexure-F.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.4 ESI Registration", styles["h2"]))
    story.append(para(
        "The company is registered under the Employees State Insurance Act, 1948. "
        "ESI Registration Number: 42-00-123456-000-0001. The company is fully compliant with ESI "
        "contribution requirements for all eligible employees. Monthly ESI remittance challans for "
        "the last 6 months are enclosed as Annexure-G.",
        styles["body"]))
    story.append(spacer())

    story.append(para("5. BLACKLISTING AND DEBARMENT DECLARATION", styles["h1"]))
    story.append(para(
        "InfraTech Solutions Pvt. Ltd. hereby declares, on our company letterhead duly signed by "
        "the authorised signatory Shri Rajesh Kumar Gupta, Director (Works), that the company has "
        "NOT been blacklisted, debarred, or placed on any holiday list by any Government department "
        "(Central or State), Public Sector Undertaking, Autonomous Body, or any other Government "
        "entity in India as on the date of this bid submission dated 10 February 2024.",
        styles["body"]))
    story.append(para(
        "This declaration is supported by a notarised affidavit on Rs. 100 stamp paper (Notary "
        "Public Registration No. UP/NOI/2024/001234). The company has a clean record with no pending "
        "litigation or arbitration proceedings against any Government entity. We have never been "
        "issued a show cause notice for blacklisting by any authority.",
        styles["body"]))
    story.append(spacer())

    story.append(para("6. SUMMARY OF ELIGIBILITY COMPLIANCE", styles["h1"]))
    summary_data = [
        ["Criterion", "Requirement", "Our Compliance", "Status"],
        ["Annual Turnover", "Min Rs. 5 Crore (3-yr avg)", "Rs. 9.23 Crore avg", "ELIGIBLE"],
        ["Similar Works", "3 projects >= Rs. 2 Cr each", "5 projects (Rs. 3.9-7.1 Cr)", "ELIGIBLE"],
        ["GST Registration", "Valid GSTIN mandatory", "29AABCI1234F1Z5 (Valid)", "ELIGIBLE"],
        ["ISO 9001:2015", "Valid certificate mandatory", "Valid till March 2026", "ELIGIBLE"],
        ["EPF Registration", "Mandatory", "UP/LKO/0012345/XXX", "ELIGIBLE"],
        ["ESI Registration", "Mandatory", "42-00-123456-000-0001", "ELIGIBLE"],
        ["Blacklisting", "Not blacklisted", "Clean record, declared", "ELIGIBLE"],
    ]
    table3 = Table(summary_data, colWidths=[4*cm, 4.5*cm, 5*cm, 2.5*cm])
    table3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1b5e20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
        ("BACKGROUND", (-1, 1), (-1, -1), HexColor("#e8f5e9")),
        ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (-1, 1), (-1, -1), HexColor("#1b5e20")),
        ("ROWBACKGROUNDS", (0, 1), (-2, -1), [colors.white, HexColor("#f9fbe7")]),
    ]))
    story.append(table3)
    story.append(spacer())

    story.append(para(
        "InfraTech Solutions Pvt. Ltd. satisfies ALL eligibility criteria set forth in the "
        "tender document CRPF/PWD/CON/2024/001. We are fully eligible to submit our technical "
        "and financial bids for this project.",
        styles["bold"]))

    doc.build(story)
    print(f"Created: {path} ({path.stat().st_size // 1024} KB)")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# FILE 3: BuildQuick Construction — NOT ELIGIBLE bidder
# ─────────────────────────────────────────────────────────────────────────────

def create_bidder_buildquick(styles):
    path = OUTPUT_DIR / "bidder_buildquick_construction.pdf"
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
    )
    story = []

    story.append(para("BUILDQUICK CONSTRUCTION LTD.", styles["title"]))
    story.append(para("Pre-Qualification Bid Document", styles["centered"]))
    story.append(para(
        "Tender Reference: CRPF/PWD/CON/2024/001 | Date: 12 February 2024",
        styles["centered"]))
    story.append(HRFlowable(width="100%", thickness=2, color=HexColor("#b71c1c")))
    story.append(spacer(0.4))

    story.append(para("1. COMPANY OVERVIEW", styles["h1"]))
    story.append(para(
        "BuildQuick Construction Ltd. is a civil construction company registered under the "
        "Companies Act, 2013. The company was incorporated in 2014 and is engaged in residential "
        "and commercial construction activities. Our registered office is at 78, Industrial Area, "
        "Mohan Nagar, Ghaziabad, Uttar Pradesh — 201007. CIN: U45200UP2014PLC067890.",
        styles["body"]))
    story.append(para(
        "The company currently employs 85 permanent staff and approximately 200 daily wage workers. "
        "Our equipment fleet includes 4 JCB excavators, 2 concrete batching plants, 5 transit mixers, "
        "and standard construction tools. We have executed several residential and commercial projects "
        "in Ghaziabad, Noida, and Meerut districts.",
        styles["body"]))
    story.append(para(
        "BuildQuick Construction has been expanding its operations and has recently entered into "
        "government sector construction. While our primary experience has been in private sector "
        "real estate development, we have increasingly sought government tenders over the past "
        "three years.",
        styles["body"]))
    story.append(spacer())

    story.append(para("2. FINANCIAL ELIGIBILITY — ANNUAL TURNOVER", styles["h1"]))
    story.append(para(
        "BuildQuick Construction Ltd. provides the following annual turnover figures from "
        "construction activities for the last three financial years, certified by our auditor "
        "M/s Verma & Co., Chartered Accountants (CA Firm Registration No. 098765N):",
        styles["body"]))
    story.append(spacer(0.2))

    turnover_data = [
        ["Financial Year", "Annual Turnover (Construction)", "Remarks"],
        ["2021-22", "Rs. 2.10 Crore", "Primarily private sector"],
        ["2022-23", "Rs. 2.80 Crore", "Mix of private and govt"],
        ["2023-24", "Rs. 3.10 Crore", "Growing govt portfolio"],
        ["3-Year Average", "Rs. 2.67 Crore", "(Minimum required: Rs. 5 Crore)"],
    ]
    table = Table(turnover_data, colWidths=[5*cm, 6.5*cm, 5*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#b71c1c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#ffebee")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, HexColor("#fff8e1")]),
    ]))
    story.append(table)
    story.append(spacer(0.3))

    story.append(para(
        "We acknowledge that our current turnover of Rs. 2.67 Crore average for the last three "
        "financial years is below the minimum threshold of Rs. 5 Crore specified in the tender. "
        "However, we would like to request the Evaluation Committee to consider the strong growth "
        "trajectory of our company (47% growth from FY 2021-22 to FY 2023-24) and the fact that "
        "our turnover is expected to exceed Rs. 6 Crore in FY 2024-25 based on confirmed orders. "
        "We have submitted our bids in good faith and hope for a favourable consideration.",
        styles["body"]))
    story.append(spacer())

    story.append(para("3. TECHNICAL ELIGIBILITY — SIMILAR WORK EXPERIENCE", styles["h1"]))
    story.append(para(
        "BuildQuick Construction has completed one (1) similar government construction project "
        "within the last five years. We have also completed several private sector residential "
        "projects which, while not qualifying under the tender criteria, demonstrate our technical "
        "competence.",
        styles["body"]))
    story.append(spacer(0.2))

    projects_data = [
        ["S.No.", "Project Name", "Client", "Value (Rs.)", "Completion Date", "Remarks"],
        ["1", "Construction of Community Hall, Ghaziabad Nagar Nigam", "GNN / UP Govt", "1.80 Crore",
         "May 2022", "Does not meet Rs. 2 Cr threshold"],
        ["2", "Residential Complex (50 Flats), Private Developer", "M/s Skyline Builders", "4.20 Crore",
         "October 2023", "Private sector — may not qualify"],
        ["3", "Factory Shed Construction, Industrial Area", "M/s Rapid Mfg. Pvt.", "0.95 Crore",
         "March 2023", "Below threshold, non-residential"],
    ]
    table2 = Table(projects_data, colWidths=[1*cm, 4.5*cm, 3*cm, 2.3*cm, 2.3*cm, 3.5*cm])
    table2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#b71c1c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#fff8e1")]),
        ("WORDWRAP", (0, 0), (-1, -1), True),
    ]))
    story.append(table2)
    story.append(spacer(0.3))

    story.append(para(
        "We note that only one government construction project (Ghaziabad Nagar Nigam Community Hall) "
        "qualifies as a 'similar work' under the tender definition, and its value of Rs. 1.80 Crore "
        "is below the minimum threshold of Rs. 2 Crore per project. The private sector projects, "
        "while demonstrating our construction capability, may not be accepted as qualifying works "
        "under the tender criteria which requires government/PSU client completion certificates.",
        styles["body"]))
    story.append(spacer())

    story.append(para("4. STATUTORY REGISTRATIONS AND CERTIFICATIONS", styles["h1"]))
    story.append(para("4.1 GST Registration", styles["h2"]))
    story.append(para(
        "BuildQuick Construction Ltd. is duly registered under the Goods and Services Tax Act. "
        "GSTIN: 07AABCB5678G1Z3. The GST registration is valid and active. The company files all "
        "required GST returns on time. GST registration certificate is enclosed as Annexure-D.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.2 ISO 9001:2015 Certification — EXPIRED", styles["h2"]))
    story.append(para(
        "BuildQuick Construction Ltd. had obtained ISO 9001:2015 Quality Management System "
        "certification from the certification body SGS India Pvt. Ltd. Certificate Number: "
        "SGS-IND-9001-2019-0892. The certification scope covered: Construction of Residential "
        "and Commercial Buildings.",
        styles["body"]))
    story.append(para(
        "However, we regret to inform the Evaluation Committee that our ISO 9001:2015 certificate "
        "expired on 30 September 2023 and we have not yet obtained renewal. Our previous certificate "
        "was issued on 01 October 2019 and was valid for three years until 30 September 2022. "
        "We obtained a one-year extension (30 September 2022 to 30 September 2023) but were unable "
        "to complete the recertification audit due to internal restructuring and key personnel changes. "
        "We are currently in the process of recertification with Bureau Veritas India, and expect "
        "to receive the renewed certificate by April 2024. A copy of the expired certificate "
        "and the renewal application acknowledgement are enclosed as Annexure-E.",
        styles["body"]))
    story.append(para(
        "We kindly request the Evaluation Committee to consider our application on the basis of our "
        "commitment to quality and the pending recertification process, and to grant a conditional "
        "approval subject to submission of the renewed ISO certificate within 60 days of award.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.3 EPF Registration", styles["h2"]))
    story.append(para(
        "The company is registered under the Employees Provident Fund and Miscellaneous Provisions "
        "Act, 1952. EPF Establishment Code: UP/GZB/0056789/XXX. The company is compliant with "
        "all EPF contribution and filing requirements. Monthly EPF remittance challans are enclosed.",
        styles["body"]))
    story.append(spacer(0.2))

    story.append(para("4.4 ESI Registration", styles["h2"]))
    story.append(para(
        "BuildQuick Construction Ltd. is registered under the Employees State Insurance Act, 1948. "
        "ESI Registration Number: 42-00-789012-000-0002. The company is fully compliant with all "
        "ESI contribution and filing requirements for eligible employees.",
        styles["body"]))
    story.append(spacer())

    story.append(para("5. BLACKLISTING AND DEBARMENT DECLARATION", styles["h1"]))
    story.append(para(
        "BuildQuick Construction Ltd. hereby declares that the company has NOT been blacklisted, "
        "debarred, or placed on any holiday list by any Government department (Central or State), "
        "Public Sector Undertaking, Autonomous Body, or any other Government entity in India as on "
        "the date of this bid submission dated 12 February 2024.",
        styles["body"]))
    story.append(para(
        "This declaration is duly signed by the authorised signatory Mr. Suresh Prakash Sharma, "
        "Managing Director, on company letterhead. A notarised affidavit on Rs. 100 stamp paper "
        "is enclosed as Annexure-H.",
        styles["body"]))
    story.append(spacer())

    story.append(para("6. SUMMARY OF ELIGIBILITY COMPLIANCE", styles["h1"]))
    summary_data = [
        ["Criterion", "Requirement", "Our Status", "Assessment"],
        ["Annual Turnover", "Min Rs. 5 Crore (3-yr avg)", "Rs. 2.67 Crore avg", "BELOW THRESHOLD"],
        ["Similar Works", "3 projects >= Rs. 2 Cr each", "1 project at Rs. 1.80 Cr", "DOES NOT MEET"],
        ["GST Registration", "Valid GSTIN mandatory", "07AABCB5678G1Z3 (Valid)", "MEETS"],
        ["ISO 9001:2015", "Valid certificate mandatory", "EXPIRED Sept 2023", "EXPIRED / FAILS"],
        ["EPF Registration", "Mandatory", "UP/GZB/0056789/XXX", "MEETS"],
        ["ESI Registration", "Mandatory", "42-00-789012-000-0002", "MEETS"],
        ["Blacklisting", "Not blacklisted", "Clean record, declared", "MEETS"],
    ]
    table3 = Table(summary_data, colWidths=[4*cm, 4.5*cm, 4.5*cm, 3*cm])
    table3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#b71c1c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
        ("BACKGROUND", (-1, 2), (-1, 2), HexColor("#ffebee")),
        ("BACKGROUND", (-1, 3), (-1, 3), HexColor("#ffebee")),
        ("BACKGROUND", (-1, 5), (-1, 5), HexColor("#ffebee")),
        ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-2, -1), [colors.white, HexColor("#fff8e1")]),
    ]))
    story.append(table3)
    story.append(spacer())

    story.append(para(
        "BuildQuick Construction Ltd. acknowledges that it does not currently meet two mandatory "
        "eligibility criteria: (1) minimum annual turnover of Rs. 5 Crore, and (2) valid ISO 9001:2015 "
        "certification. We are submitting this bid in the hope that the Evaluation Committee may "
        "consider conditional eligibility based on our growth trajectory and pending recertification.",
        styles["bold"]))

    doc.build(story)
    print(f"Created: {path} ({path.stat().st_size // 1024} KB)")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    styles = make_styles()
    print("Generating demo PDFs...")
    p1 = create_tender_crpf(styles)
    p2 = create_bidder_infratech(styles)
    p3 = create_bidder_buildquick(styles)
    print(f"\nAll 3 PDFs created in: {OUTPUT_DIR.resolve()}")
    print("Expected results:")
    print("  tender_crpf_2024.pdf        — 6 criteria, detailed tender document")
    print("  bidder_infratech_solutions.pdf — ELIGIBLE (all criteria met)")
    print("  bidder_buildquick_construction.pdf — NOT ELIGIBLE (turnover + ISO fail)")
