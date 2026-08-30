#!/usr/bin/env python3
"""
FindMe — Comprehensive System Documentation PDF Generator
Uses reportlab 4.x (already installed). Produces a print-ready A4 PDF.
All technical details are sourced from the actual codebase:
  app.py, ai/matcher.py, schema.sql, config.py, templates/.
"""
from pathlib import Path
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, ListFlowable, ListItem,
    Image as RLImage, Frame, PageTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, Rect, String as GString
from reportlab.graphics.charts.piecharts import Pie

# ── Paths & meta ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent
OUT = ROOT / "output" / f"FindMe_Complete_System_Documentation_{datetime.now():%Y%m%d_%H%M%S}.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = A4
MARGIN = 1.9 * cm

# ── Brand palette (matches the live system) ──────────────────────────
NAVY       = HexColor("#1A274B")
NAVY_LIGHT = HexColor("#2D3F6B")
NAVY_FADE  = HexColor("#EEF2FF")
ACCENT     = HexColor("#2563EB")
ACCENT_DK  = HexColor("#1D4ED8")
ACCENT_LT  = HexColor("#60A5FA")
EMERALD    = HexColor("#10B981")
VIOLET     = HexColor("#8B5CF6")
AMBER      = HexColor("#F59E0B")
RED        = HexColor("#EF4444")
SLATE_900  = HexColor("#0F172A")
SLATE_700  = HexColor("#334155")
SLATE_500  = HexColor("#64748B")
SLATE_300  = HexColor("#CBD5E1")
SLATE_100  = HexColor("#F1F5F9")
SLATE_50   = HexColor("#F8FAFC")
GOLD       = HexColor("#F59E0B")

# ── Styles ────────────────────────────────────────────────────────────
ss = getSampleStyleSheet()

def _style(name, parent=None, **kw):
    base = ss["Normal"] if parent is None else parent
    return ParagraphStyle(name, parent=base, **kw)

S_COVER_TITLE = _style("CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6)
S_COVER_SUB   = _style("CoverSub",   fontName="Helvetica",      fontSize=11, leading=15, textColor=SLATE_700, alignment=TA_CENTER, spaceAfter=4)
S_COVER_META  = _style("CoverMeta",  fontName="Helvetica",      fontSize=8.5, leading=12, textColor=SLATE_500, alignment=TA_CENTER)
S_H1 = _style("H1", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=14, spaceAfter=6, keepWithNext=True)
S_H2 = _style("H2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=NAVY_LIGHT, spaceBefore=10, spaceAfter=4, keepWithNext=True)
S_H3 = _style("H3", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=SLATE_700, spaceBefore=7, spaceAfter=3, keepWithNext=True)
S_BODY = _style("Body", fontName="Helvetica", fontSize=8.7, leading=12.5, textColor=SLATE_700, alignment=TA_JUSTIFY, spaceAfter=4, spaceBefore=0)
S_BULLET = _style("Bullet", fontName="Helvetica", fontSize=8.7, leading=12.5, textColor=SLATE_700, leftIndent=14, bulletIndent=0, spaceAfter=2)
S_SMALL = _style("Small", fontName="Helvetica", fontSize=7.5, leading=10, textColor=SLATE_500, alignment=TA_CENTER)
S_CELL = _style("Cell", fontName="Helvetica", fontSize=7.2, leading=9, textColor=SLATE_700)
S_CELL_B = _style("CellB", parent=S_CELL, fontName="Helvetica-Bold", textColor=colors.white)
S_CELL_HEAD = _style("CellHead", parent=S_CELL_B, fontSize=7, leading=8)
S_CODE = _style("Code", fontName="Helvetica", fontSize=7.2, leading=9.5, textColor=HexColor("#1E293B"), backColor=SLATE_100, borderPadding=(4,6,4), spaceAfter=4)
S_CAPTION = _style("Caption", fontName="Helvetica-Oblique", fontSize=7, leading=9, textColor=SLATE_500, alignment=TA_CENTER, spaceBefore=2, spaceAfter=6)
S_TOC_ITEM = _style("TOCitem", fontName="Helvetica", fontSize=9, leading=13, textColor=SLATE_700, leftIndent=6)
S_TOC_SEC  = _style("TOCsec",  fontName="Helvetica-Bold", fontSize=9, leading=13, textColor=NAVY, leftIndent=0)

# ── Helpers ───────────────────────────────────────────────────────────
def hr():
    return HRFlowable(width="100%", thickness=0.6, color=SLATE_300, spaceAfter=6, spaceBefore=2)

def p(text, style=S_BODY):
    return Paragraph(text, style)

def bullet(text):
    return Paragraph(f'<bullet>&bull;</bullet> {text}', S_BULLET)

def bullets(items):
    return [bullet(x) for x in items]

def styled_table(headers, rows, col_widths=None, header_color=NAVY, zebra=True, fontsize=7.2,
                 header_fontsize=7, repeat_header=True):
    """Build a styled Table with header row."""
    hdr = [Paragraph(f"<b>{h}</b>", ParagraphStyle("h", parent=S_CELL, fontName="Helvetica-Bold", fontSize=header_fontsize, leading=header_fontsize+1, textColor=colors.white, alignment=TA_CENTER)) for h in headers]
    body = []
    for r in rows:
        body.append([Paragraph(str(c), ParagraphStyle("c", parent=S_CELL, fontSize=fontsize, leading=fontsize+1.2)) for c in r])
    data = [hdr] + body
    style_cmds = [
        ("BACKGROUND", (0,0), (-1,0), header_color),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), fontsize),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.4, SLATE_300),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SLATE_50] if zebra else [colors.white, colors.white]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]
    if repeat_header:
        style_cmds.append(("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SLATE_50] if zebra else [colors.white, colors.white]))
    t = Table(data, colWidths=col_widths, repeatRows=1 if repeat_header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t

def kv_table(pairs, col_widths=None):
    """Two-column key/value table."""
    rows = [[Paragraph(f"<b>{k}</b>", S_CELL), Paragraph(v, S_CELL)] for k,v in pairs]
    t = Table(rows, colWidths=col_widths or [3.2*cm, 13.2*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), NAVY_FADE),
        ("GRID", (0,0), (-1,-1), 0.4, SLATE_300),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, SLATE_50]),
    ]))
    return t

def note_box(text, icon="ℹ", bg=HexColor("#EFF6FF"), border=ACCENT, title="Note"):
    inner = [
        [Paragraph(f'<font color="{border.hexval() if hasattr(border,"hexval") else "#2563EB"}"><b>{icon}  {title}</b></font>', S_CELL),
         Paragraph(text, S_CELL)]
    ]
    # single-row two-col table acting as callout
    inner2 = [[Paragraph(f'<font size="8" color="{border.hexcolor() if hasattr(border,"hexcolor") else "#2563EB"}"><b>{title}</b></font><br/><font size="7.5" color="#334155">{text}</font>', S_BODY)]]
    t = Table(inner2, colWidths=[16.4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX", (0,0), (-1,-1), 0.7, border),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("ROUNDEDCORNERS", [3,3,3,3]),
    ]))
    return t

# ── Page chrome ───────────────────────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()
    # top hairline
    canvas.setStrokeColor(SLATE_300)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, H - 1.15*cm, W - MARGIN, H - 1.15*cm)
    # header text
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(MARGIN, H - 0.85*cm, "FindMe  —  Cavendish University Uganda  ·  AI-Powered Lost & Found")
    canvas.drawRightString(W - MARGIN, H - 0.85*cm, datetime.now().strftime("%B %Y"))
    # footer
    canvas.setStrokeColor(SLATE_300)
    canvas.line(MARGIN, 1.15*cm, W - MARGIN, 1.15*cm)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(SLATE_500)
    canvas.drawString(MARGIN, 0.75*cm, "Confidential  ·  Academic documentation  ·  Cavendish University Uganda")
    canvas.drawRightString(W - MARGIN, 0.75*cm, f"Page {doc.page}")
    # small accent bar in footer
    canvas.setFillColor(ACCENT)
    canvas.rect(MARGIN, 0.62*cm, 1.4*cm, 0.5*mm, stroke=0, fill=1)
    canvas.restoreState()

def _cover_footer(canvas, doc):
    # no header/footer on cover
    pass

# ── Document ──────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=1.7*cm, bottomMargin=1.5*cm,
    title="FindMe — Complete System Documentation",
    author="Cavendish University Uganda — FindMe Project",
    subject="AI-Powered Lost & Found Management System",
)

story = []

# ═══════════════════════════════════════════════════════════════════════
# COVER
# ═══════════════════════════════════════════════════════════════════════
# navy banner
banner_h = 3.8*cm
# We'll fake a banner with a colored table
banner = Table([[Paragraph(
    '<font color="#FFFFFF" size="8">CAVENDISH UNIVERSITY UGANDA  ·  SCHOOL OF SCIENCE & TECHNOLOGY</font>',
    ParagraphStyle("banner", parent=S_SMALL, textColor=colors.white, alignment=TA_CENTER, fontSize=7, leading=9)
)]], colWidths=[W - 2*MARGIN])
banner.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), NAVY),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ("ALIGN", (0,0), (-1,-1), "CENTER"),
]))
story.append(banner)
story.append(Spacer(1, 0.7*cm))

# magnifier icon (inline SVG-like drawing)
d = Drawing(3.2*cm, 3.2*cm)
# rounded square bg with gradient simulated as solid accent
d.add(Rect(0, 0, 3.2*cm, 3.2*cm, rx=6*mm, ry=6*mm, fillColor=ACCENT, strokeColor=None))
# lens circle
cx, cy, r = 1.45*cm, 1.65*cm, 0.68*cm
d.add(Rect(cx-r, cy-r, r*2, r*2, rx=r, ry=r, fillColor=None, strokeColor=colors.white, strokeWidth=2.2))
# handle
d.add(Line(1.92*cm, 1.18*cm, 2.52*cm, 0.58*cm, strokeColor=colors.white, strokeWidth=2.4))
# small highlight dot
d.add(Rect(1.15*cm, 1.95*cm, 0.18*cm, 0.18*cm, rx=2, ry=2, fillColor=colors.white, strokeColor=None))
story.append(d)
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph("FindMe", S_COVER_TITLE))
story.append(Paragraph("AI-Powered Lost &amp; Found Management System", ParagraphStyle("coverSub2", parent=S_COVER_SUB, fontSize=12, leading=15, textColor=NAVY_LIGHT, fontName="Helvetica-Bold")))
story.append(Spacer(1, 0.15*cm))
story.append(Paragraph("Complete System Documentation  ·  How the Entire Platform Works", S_COVER_SUB))
story.append(Spacer(1, 0.2*cm))
story.append(HRFlowable(width="22%", thickness=1.2, color=ACCENT, spaceAfter=6, spaceBefore=4, hAlign="CENTER"))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(
    "Cavendish University Uganda &nbsp;·&nbsp; Faculty of Science &amp; Technology<br/>"
    "Capstone Project  —  Bachelor of Science in Computer Science / Information Technology",
    ParagraphStyle("coverDept", parent=S_COVER_SUB, fontSize=8.5, leading=12, textColor=SLATE_500)
))
story.append(Spacer(1, 0.7*cm))

# key facts card
facts = [
    ["Version", "1.0  ·  August 2026"],
    ["Stack", "Python 3 · Flask · MySQL (utf8mb4) · Pillow · bcrypt · Vanilla JS/CSS"],
    ["AI Engine", "ai/matcher.py  —  12-factor weighted scoring  ·  background threading"],
    ["Database", "findme_db  ·  14 tables  ·  16 indexes  ·  role-based access"],
    ["Deployment", "PythonAnywhere / XAMPP  ·  WSGI (wsgi.py)  ·  16 MB upload limit"],
]
# build as styled table
hdr = [Paragraph("<b>Item</b>", S_CELL_HEAD), Paragraph("<b>Detail</b>", S_CELL_HEAD)]
rows = [[Paragraph(f"<b>{k}</b>", S_CELL), Paragraph(v, S_CELL)] for k,v in facts]
t = Table([hdr] + rows, colWidths=[3.6*cm, 12.8*cm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("ALIGN", (0,0), (-1,0), "LEFT"),
    ("GRID", (0,0), (-1,-1), 0.4, SLATE_300),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SLATE_50]),
    ("TOPPADDING", (0,0), (-1,-1), 4),
    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 6),
    ("RIGHTPADDING", (0,0), (-1,-1), 6),
]))
story.append(KeepTogether(t))
story.append(Spacer(1, 0.6*cm))

story.append(Paragraph(
    f"Document generated  {datetime.now():%d %B %Y  ·  %H:%M %Z}  &nbsp;|&nbsp;  Source-verified against <b>app.py</b>, <b>ai/matcher.py</b>, <b>schema.sql</b>, <b>config.py</b><br/>"
    "All weights, thresholds, routes, and status values are taken directly from the live codebase — not from the README.",
    ParagraphStyle("coverFoot", parent=S_COVER_META, fontSize=6.8, leading=9, textColor=SLATE_500, alignment=TA_CENTER)
))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph(
    '<font color="#64748B">Prepared for</font>  <font color="#1A274B"><b>Project Supervisors, External Examiners, and System Administrators</b></font>',
    ParagraphStyle("coverFor", parent=S_SMALL, fontSize=7.5, leading=10, textColor=SLATE_500, alignment=TA_CENTER)
))

# ── TOC ───────────────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("Contents", ParagraphStyle("tocTitle", parent=S_H1, fontSize=16, leading=18, spaceBefore=0)))
story.append(HRFlowable(width="100%", thickness=0.7, color=ACCENT, spaceAfter=8, spaceBefore=2))

toc = [
    ("1", "Introduction — What FindMe Is and Why It Exists", "3"),
    ("2", "System Overview & Objectives", "3"),
    ("3", "Technology Stack & Architecture", "4"),
    ("4", "Project Structure (Every File, Its Job)", "5"),
    ("5", "Database Design — 14 Tables, Relationships & Indexes", "6"),
    ("6", "User Roles, Registration & Authentication", "9"),
    ("7", "Security Architecture", "10"),
    ("8", "Core User Workflows (Step-by-Step)", "11"),
    ("  8.1", "Dashboard", "11"),
    ("  8.2", "Report Lost Item", "12"),
    ("  8.3", "Report Found Item", "12"),
    ("  8.4", "Search & Item Detail", "13"),
    ("  8.5", "My Reports, Matches & Notifications", "13"),
    ("  8.6", "Settings, Profile & Password", "14"),
    ("9", "AI Matching Engine — Deep Dive (ai/matcher.py)", "14"),
    ("  9.1", "Design Philosophy — AI Assists, It Does Not Decide", "14"),
    ("  9.2", "The 12 Weighted Factors (Actual Code Weights)", "15"),
    ("  9.3", "How Each Factor Is Scored (Formulas & Code Logic)", "15"),
    ("  9.4", "Overall Confidence Formula & Match Levels", "17"),
    ("  9.5", "Matching Pipeline — find_potential_matches()", "17"),
    ("  9.6", "Notifications, Deduplication & Rerun", "18"),
    ("10", "Administration Module (Every Admin Screen)", "18"),
    ("11", "End-to-End Lifecycle — From Report to Recovery", "21"),
    ("12", "Route Reference — All 40+ Endpoints", "22"),
    ("13", "Configuration, Deployment & Operations", "24"),
    ("14", "Limitations, Risks & Future Roadmap", "25"),
    ("A", "Appendix A — Demo Accounts & Quick-Start Script", "26"),
    ("B", "Appendix B — Status & Enum Reference", "26"),
]
toc_rows = []
for num, title, pg in toc:
    is_sec = "." not in num and not num.startswith("A") and not num.startswith("B")
    style = S_TOC_SEC if is_sec or num in ("A","B") else S_TOC_ITEM
    left = Paragraph(f"<b>{num}</b> &nbsp; {title}", style)
    right = Paragraph(pg, ParagraphStyle("pg", parent=style, alignment=TA_RIGHT))
    toc_rows.append([left, right])

toc_table = Table(toc_rows, colWidths=[15.0*cm, 1.4*cm])
toc_table.setStyle(TableStyle([
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 2),
    ("RIGHTPADDING", (0,0), (-1,-1), 2),
    ("TOPPADDING", (0,0), (-1,-1), 1),
    ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ("LINEBELOW", (0,0), (-1,-1), 0.25, HexColor("#E2E8F0")),
]))
story.append(toc_table)
story.append(Spacer(1, 0.4*cm))
story.append(note_box(
    "Page numbers in this TOC are approximate. Use your PDF reader's search (Ctrl+F) to jump to any heading. "
    "All technical claims in this document were verified against the live source files listed on the cover.",
    title="How to use this document", bg=SLATE_50, border=SLATE_300
))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    '<font color="#64748B" size="7">Conventions:</font>  '
    '<font color="#334155" size="7"><b>Bold</b> = UI label / DB table / route &nbsp;|&nbsp;  <i>Italic</i> = file path &nbsp;|&nbsp;  '
    '<font face="Helvetica-Bold" color="#2563EB">Blue</font> = cross-reference &nbsp;|&nbsp;  '
    'Weights shown as decimals (0.20) and as percentages (20 %) where helpful.</font>',
    S_SMALL
))

# ═══════════════════════════════════════════════════════════════════════
# 1. INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("1 &nbsp; Introduction — What FindMe Is and Why It Exists", S_H1))
story.append(hr())
story.append(p(
    "FindMe is a centralised, web-based <b>Lost &amp; Found Management System</b> built for <b>Cavendish University Uganda (CUU)</b>. "
    "It replaces noticeboards, WhatsApp groups, and word-of-mouth with a single, searchable, auditable platform where every lost or found "
    "item is reported once, stored securely, and automatically compared by an <b>AI matching engine</b> that surfaces likely lost↔found pairs "
    "for an administrator to review. Students, lecturers, and staff share the same system; administrators govern it."
))
story.append(p(
    "The university community loses personal property every day — phones, IDs, wallets, books, chargers, clothing — across lecture rooms, "
    "libraries, hostels, and sports grounds. Without a central record, recovery depends on chance. FindMe solves this with three principles:"
))
for b in bullets([
    "<b>Report once, match automatically</b> — every new report is compared against up to 200 opposite-type reports in the background, without blocking the user.",
    "<b>AI assists, it does not decide</b> — the engine proposes; a human administrator approves or rejects. Sensitive contact details stay hidden until approval.",
    "<b>Everything is auditable</b> — every login, report, approval, and recovery is written to <i>activity_logs</i> with the actor's IP.",
]):
    story.append(b)
story.append(p(
    "FindMe is a <b>capstone project</b> for the School of Science &amp; Technology. It is intentionally built with vanilla, well-understood "
    "technologies (Flask, MySQL, Pillow) so that the university IT team can maintain it without specialist ML infrastructure, while the AI layer "
    "remains isolated in a single module (<i>ai/matcher.py</i>) that can be upgraded to a real ML model later without touching the rest of the app."
))

# ═══════════════════════════════════════════════════════════════════════
# 2. SYSTEM OVERVIEW & OBJECTIVES
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("2 &nbsp; System Overview &amp; Objectives", S_H1))
story.append(hr())
story.append(Paragraph("2.1 &nbsp; Objectives", S_H2))
for b in bullets([
    "Give every member of CUU a <b>single place</b> to report lost and found items with photos, location, and identifying marks.",
    "Use AI to <b>automatically surface likely matches</b> (lost ↔ found) with an explainable confidence score and human-readable breakdown.",
    "Keep a <b>human in the loop</b> — no match is revealed as \"approved\" until an administrator reviews it.",
    "Protect privacy — item details and owner/finder contact are masked until a match is approved or ownership is verified.",
    "Provide <b>recovery tracking</b> from verification → collection → archival, with notifications at every transition.",
    "Maintain a complete <b>audit trail</b> for accountability and reporting.",
]):
    story.append(b)

story.append(Paragraph("2.2 &nbsp; Who the system serves", S_H2))
story.append(styled_table(
    ["Actor", "What they can do", "What they cannot do"],
    [
        ["Student / Lecturer<br/><font size=\"6.5\" color=\"#64748B\">role_id 1 / 2</font>", "Register, log in, report lost/found, search, view own reports & matches, receive notifications, edit profile, change password", "Access any admin screen; approve/reject matches; manage other users"],
        ["Administrator<br/><font size=\"6.5\" color=\"#64748B\">role_id 3</font>", "Everything above, plus: manage users, faculties, courses, categories, locations; review & approve/reject AI matches; handle verifications & recoveries; view reports & activity logs; reset data", "Bypass bcrypt / change another user's password directly"],
        ["Guest<br/><font size=\"6.5\" color=\"#64748B\">no session</font>", "View landing page (/), About, Login, Register, Forgot Password", "Any authenticated route — redirected to /login with a flash warning"],
    ],
    col_widths=[3.2*cm, 7.1*cm, 6.1*cm]
))
story.append(Paragraph("Registration is open to <b>Student</b> and <b>Lecturer</b> only; the Administrator account is seeded directly in the database (see Appendix A). Role checks use two decorators — <i>login_required</i> and <i>admin_required</i> (role_id == 3) — and a generic <i>role_required(*names)</i>.", S_BODY))

story.append(Paragraph("2.3 &nbsp; High-level data flow", S_H2))
story.append(p(
    "The diagram below shows the lifecycle of a single item. The AI step runs in a <b>daemon thread</b> so the HTTP response is not blocked "
    "(<i>app.py: _run_matcher_async</i>). If the thread crashes, the report is still saved; matches can be regenerated with <i>rerun_all_matches()</i>."
))
# Flow as a table to avoid graphics dependency
flow_steps = [
    ["1", "User", "Fills <b>Report Lost</b> or <b>Report Found</b> form (name, category, colour, brand, location, date, photo …) and submits."],
    ["2", "Flask", "Validates required fields, generates a reference (<b>FM-YYYY-NNNNN</b>), resizes photo to 1200 px / 85 % quality, inserts row with status <b>reported</b>, logs activity, spawns matcher thread."],
    ["3", "AI Engine", "Loads the new item + up to 200 opposite-type items (<b>reported / under_review / potential_match / match_pending_approval</b>), scores each pair on 12 factors, keeps pairs with <b>confidence ≥ 30 %</b>, inserts into <i>matches</i> as <b>pending</b>."],
    ["4", "Notifications", "Both the reporter and the finder receive an in-app notification: <i>\"Potential Match Found — Confidence: N%\"</i>."],
    ["5", "Administrator", "Opens <b>Match Review</b>, compares the two items side-by-side (including images &amp; explanation breakdown), clicks <b>Approve</b> or <b>Reject</b>."],
    ["6", "On Approve", "<i>matches.status → approved</i>, both items → <b>match_approved</b>, both users notified, match becomes visible as approved in <b>/matches</b>."],
    ["7", "Verification (if needed)", "If ownership is disputed, a <i>verification_requests</i> row is created; admin approves/rejects it, which in turn approves the underlying match."],
    ["8", "Recovery", "A <i>recoveries</i> row is created; admin marks it <b>completed</b> → both items → <b>recovered</b>, match stays approved, case is effectively closed."],
]
story.append(styled_table(["Step", "Actor", "What happens"], flow_steps, col_widths=[1.1*cm, 2.2*cm, 13.1*cm], header_color=NAVY))
story.append(Paragraph("Figure 1 — End-to-end lifecycle. Every transition writes to <i>activity_logs</i> and (where user-visible) to <i>notifications</i>.", S_CAPTION))

# ═══════════════════════════════════════════════════════════════════════
# 3. TECH STACK & ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("3 &nbsp; Technology Stack &amp; Architecture", S_H1))
story.append(hr())
story.append(styled_table(
    ["Layer", "Technology", "Version / Notes"],
    [
        ["Backend", "Python + Flask", "3.x  ·  Flask 3.0.3  ·  WSGI entry <i>wsgi.py</i>"],
        ["Database", "MySQL / MariaDB", "findme_db  ·  utf8mb4 / utf8mb4_unicode_ci  ·  flask-mysqldb 2.0.0 + PyMySQL 1.1.1"],
        ["Auth & crypto", "bcrypt", "4.2.1  ·  gensalt + hashpw; passwords never stored in clear"],
        ["Images", "Pillow (PIL)", "11.1.0  ·  thumbnail 1200 px, RGB conversion, quality 85, 5 MB / 16 MB limits"],
        ["Frontend", "HTML5 + CSS3 + Vanilla JS", "No build step; Inter font; Font Awesome 6.5.0; light/dark theme via localStorage"],
        ["AI", "Pure-Python engine", "<i>ai/matcher.py</i>  ·  difflib.SequenceMatcher, Jaccard, colour/shape groups"],
        ["Mail (optional)", "Flask-Mail", "0.9.1  ·  configured but email sending not yet wired in production"],
        ["Docs tooling", "python-pptx / python-docx / reportlab", "Used by <i>generate_deliverables.py</i> and this PDF generator"],
    ],
    col_widths=[2.8*cm, 4.2*cm, 9.4*cm]
))
story.append(Paragraph("Table 1 — Technology stack. All dependencies are listed in <i>requirements.txt</i>.", S_CAPTION))

story.append(Paragraph("3.1 &nbsp; Runtime architecture", S_H2))
story.append(p(
    "FindMe follows the classic <b>Flask MVC-ish</b> pattern without an ORM. <i>app.py</i> owns every route, helper, and decorator; "
    "templates in <i>templates/</i> are Jinja2 views; <i>static/</i> holds CSS, JS, and uploads. There is no separate API layer — every "
    "interaction is a server-rendered page or a form POST that redirects with a flash message. This keeps the deployment trivial: a single "
    "WSGI callable (<i>wsgi.py</i>) and a MySQL database."
))
story.append(kv_table([
    ["Entry point", "<i>wsgi.py</i> imports <b>app</b> from <i>app.py</i>; PythonAnywhere / gunicorn point at <b>wsgi:app</b>."],
    ["Config", "<i>config.py: Config</i> — reads <b>SECRET_KEY, MYSQL_*</b> from environment with safe defaults; <b>UPLOAD_FOLDER = static/uploads</b>, <b>MAX_CONTENT_LENGTH = 16 MB</b>, <b>ALLOWED_EXTENSIONS = {jpg, jpeg, png, webp}</b>."],
    ["Sessions", "Flask signed cookies (<b>SECRET_KEY</b>). Keys stored: <b>user_id, full_name, email, role_id, role_name, student_staff_id, phone, faculty_id, course_id, profile_image</b>. <b>_unread_count</b> is refreshed on /dashboard."],
    ["Uploads", "<i>save_image(file, folder)</i> — secrets.token_hex(16) filename, Pillow thumbnail 1200×1200, RGBA→RGB, optimize + quality 85. Subfolders: <b>lost / found / avatars</b>. Returns a forward-slash path for URL generation."],
    ["Pagination", "<i>paginated_query(cursor, base_query, count_query, params, page, per_page)</i> — two-query pattern (COUNT + LIMIT/OFFSET), default 20 rows, returns (items, page, total_pages, total). Used by admin lists and search."],
    ["Logging", "<i>log_activity(user_id, action, description, entity_type, entity_id)</i> — inserts into <i>activity_logs</i> with <b>request.remote_addr</b> IP. Called on login, logout, registration, report, profile update, and every admin action."],
]))
story.append(Paragraph("3.2 &nbsp; Concurrency model", S_H2))
story.append(p(
    "Report submission must stay fast even though matching scans up to 200 rows and runs 12 scoring functions per pair. "
    "FindMe solves this with <b>threading.Thread(daemon=True, target=_run_matcher_async)</b> — the HTTP handler commits the new item, "
    "starts the thread with <i>app.app_context()</i>, and immediately redirects. The thread opens its own DB cursor, calls "
    "<i>ai.matcher.find_potential_matches(item_type, item_id, db)</i>, and silently ignores exceptions so a matcher bug never rolls back the report."
))
story.append(note_box(
    "This is <b>not</b> a task queue (no Celery/RQ). If the process restarts mid-match, pending pairs are simply regenerated on the next report or by calling <i>rerun_all_matches(db)</i> (which deletes and recomputes all pending matches). For a production deployment with multiple workers, replace the thread with a proper queue.",
    title="Operational note", bg=HexColor("#FFFBEB"), border=AMBER
))

# ═══════════════════════════════════════════════════════════════════════
# 4. PROJECT STRUCTURE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("4 &nbsp; Project Structure — Every File, Its Job", S_H1))
story.append(hr())
story.append(p("The repository is intentionally flat — one Flask app, one AI module, one stylesheet, one JS file. Every file is accounted for below."))
story.append(styled_table(
    ["Path", "Purpose — what it does, why it exists"],
    [
        ["<b>app.py</b>  <font size=\"6.5\" color=\"#64748B\">~1,754 lines</font>", "The entire web application: all helpers, decorators, and 40+ routes. No blueprints — single-file Flask app for capstone simplicity."],
        ["<b>config.py</b>", "Flask config object (SECRET_KEY, MySQL credentials, UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS, charset). Env-var overrides for PythonAnywhere."],
        ["<b>wsgi.py</b>", "Two-line WSGI entry: <font face=\"Helvetica\" size=\"7\">from app import app</font>. Point gunicorn / PythonAnywhere here."],
        ["<b>schema.sql</b>", "Idempotent DDL: CREATE DATABASE + 14 tables + 16 indexes. The canonical schema — run via <i>init_db.py</i> or mysql SOURCE."],
        ["<b>seed.sql</b>", "Demo data: 3 roles, faculties, courses, categories, locations, and sample users/items."],
        ["<b>init_db.py</b> / <b>reset_db.py</b>", "Bootstrap helpers: create DB, run schema.sql + seed.sql, optionally wipe and reseed."],
        ["<b>verify_db.py</b>", "Sanity checker: connects and counts rows per table; used after deployment."],
        ["<b>migration_add_indexes.sql</b>", "Standalone index migration for existing deployments that were created before indexes were added to schema.sql."],
        ["<b>ai/__init__.py</b>", "Package marker (empty)."],
        ["<b>ai/matcher.py</b>  <font size=\"6.5\" color=\"#64748B\">~513 lines</font>", "The AI engine — all scoring functions, <i>compute_match_score()</i>, <i>find_potential_matches()</i>, <i>rerun_all_matches()</i>. Pure Python, no external ML deps."],
        ["<b>static/css/style.css</b>", "Single stylesheet: CSS variables, layout (sidebar + navbar), cards, forms, tables, dark-mode overrides. Inter font + FA 6.5.0."],
        ["<b>static/js/main.js</b>", "Vanilla JS: sidebar toggle, theme switch (localStorage), form UX (spinner on submit), scroll effects. Uses FA icons <i>fa-sun / fa-moon / fa-spinner</i>."],
        ["<b>static/uploads/</b>", "Runtime uploads — <b>lost/</b>, <b>found/</b>, <b>avatars/</b>. Filenames are random hex; original names are discarded. Served via <i>/uploads/&lt;path&gt;</i>."],
        ["<b>static/img/</b>", "Brand assets: <b>favicon.svg</b>, <b>favicon-32.png</b>, <b>apple-touch-icon.png</b> (gradient magnifier, #2563EB → #1D4ED8)."],
        ["<b>templates/base.html</b>", "Master layout: &lt;head&gt; (FA CDN, Inter, favicons, theme script), sidebar (role-aware), top bar, flash messages, footer, main.js include."],
        ["<b>templates/index.html</b> etc.", "5 standalone public pages (index, about, login, register, forgot_password) with their own &lt;head&gt;; all other pages extend <i>base.html</i>."],
        ["<b>templates/admin/</b>", "12 admin templates: dashboard, users, faculties, courses, categories, locations, lost_items, found_items, ai_matches, verifications, recoveries, reports, activity_logs."],
        ["<b>generate_deliverables.py</b>", "Existing PPTX/DOCX generator (python-pptx / python-docx). Produces the presentation + Word report in <i>output/</i>."],
        ["<b>generate_findme_pdf.py</b>", "This PDF generator (reportlab). Complements the PPTX/DOCX outputs with a print-ready A4 document."],
        ["<b>requirements.txt</b>", "Pinned deps: Flask 3.0.3, flask-mysqldb 2.0.0, bcrypt 4.2.1, Pillow 11.1.0, python-pptx/docx, Flask-Mail, PyMySQL."],
        ["<b>run.bat</b> / <b>deploy.txt</b>", "Windows quick-start and PythonAnywhere step-by-step deploy guide."],
        ["<b>output/</b>", "Generated artefacts: PPTX, DOCX, this PDF, and optional screenshots. Not committed."],
    ],
    col_widths=[4.6*cm, 11.8*cm]
))
story.append(Paragraph("Table 2 — Repository map. Templates not listed individually are standard Jinja2 views that extend <i>base.html</i>.", S_CAPTION))

# ═══════════════════════════════════════════════════════════════════════
# 5. DATABASE DESIGN
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("5 &nbsp; Database Design — 14 Tables, Relationships &amp; Indexes", S_H1))
story.append(hr())
story.append(p(
    "The schema lives in <i>schema.sql</i> and is created as <b>findme_db</b> (utf8mb4 / utf8mb4_unicode_ci). Foreign keys enforce "
    "referential integrity; indexes accelerate the hot paths (reporter/finder lookups, status filters, match joins, notification inbox). "
    "All timestamps are server-side <b>TIMESTAMP DEFAULT CURRENT_TIMESTAMP</b> with <b>ON UPDATE CURRENT_TIMESTAMP</b> where appropriate."
))

# 5.1 ER overview (text)
story.append(Paragraph("5.1 &nbsp; Entity overview", S_H2))
story.append(styled_table(
    ["Table", "Rows hold…", "Key relations"],
    [
        ["<b>roles</b>", "3 fixed roles: Student (1), Lecturer (2), Administrator (3)", "Referenced by <i>users.role_id</i>"],
        ["<b>faculties</b>", "University faculties (e.g. Science &amp; Technology)", "Parent of <i>courses.faculty_id</i>; referenced by <i>users.faculty_id</i>"],
        ["<b>courses</b>", "Academic programmes, each belonging to a faculty", "<i>faculty_id → faculties.id</i>; referenced by <i>users.course_id</i>"],
        ["<b>users</b>", "Every account: name, email (UNIQUE), phone, student/staff ID, bcrypt hash, role, faculty/course, avatar, active flag", "<i>role_id → roles</i>, <i>faculty_id → faculties</i>, <i>course_id → courses</i>"],
        ["<b>categories</b>", "Item categories (Electronics, Documents, Clothing …)", "Referenced by <i>lost_items.category_id</i> &amp; <i>found_items.category_id</i>"],
        ["<b>locations</b>", "Named campus locations (Library, Hostel A, Lecture Block …)", "Referenced by <i>lost_items.location_id</i> &amp; <i>found_items.location_id</i>"],
        ["<b>lost_items</b>", "Lost reports — reference, reporter, item attrs, dates, images, status", "<i>reporter_id → users</i>, <i>category_id</i>, <i>location_id</i>, <i>verified_by → users</i>"],
        ["<b>found_items</b>", "Found reports — same shape as lost plus <i>current_location</i>", "<i>finder_id → users</i>, same FKs as lost"],
        ["<b>item_images</b>", "Extra images per item (multi-image support; currently single image via <i>image_path</i> on the item row)", "<i>(item_id, item_type)</i> — type is lost/found"],
        ["<b>matches</b>", "AI-generated lost↔found pairs with confidence, level, explanation, review state", "<i>lost_item_id → lost_items</i>, <i>found_item_id → found_items</i>, <i>reviewed_by → users</i>"],
        ["<b>notifications</b>", "Inbox entries per user (info / warning / success / match / recovery)", "<i>user_id → users</i>; polymorphic <i>(related_type, related_id)</i> points at matches etc."],
        ["<b>verification_requests</b>", "Ownership claims against a match (claimer identity, secret identifier, admin review)", "<i>match_id → matches</i>, <i>requester/claimer/reviewed_by → users</i>"],
        ["<b>recoveries</b>", "Collection records tying a match to a recovery date, notes, and actor", "<i>match_id → matches</i>, <i>recovered_by_id → users</i>"],
        ["<b>activity_logs</b>", "Append-only audit trail: who did what, on which entity, from which IP, when", "<i>user_id → users</i> (nullable for system actions)"],
    ],
    col_widths=[2.9*cm, 6.6*cm, 6.9*cm]
))
story.append(Paragraph("Table 3 — The 14 tables. <i>lost_items</i> and <i>found_items</i> are structurally parallel by design so the matcher can compare them field-for-field.", S_CAPTION))

# 5.2 Detailed columns for the two central tables
story.append(Paragraph("5.2 &nbsp; Central tables — lost_items &amp; found_items", S_H2))
story.append(p(
    "Both tables share the same attribute columns so the AI can score them uniformly. The only structural difference is "
    "<b>reporter_id</b> vs <b>finder_id</b>, <b>date_lost / time_lost</b> vs <b>date_found / time_found</b>, and the extra "
    "<b>current_location</b> on found items (where the finder is keeping the item)."
))
story.append(styled_table(
    ["Column", "Type", "Meaning"],
    [
        ["id", "INT PK AUTO", "Row identity"],
        ["reference", "VARCHAR(30) UNIQUE", "Human reference: <b>FM-YYYY-NNNNN</b> (generated from MAX(id)+1 per table)"],
        ["reporter_id / finder_id", "INT FK → users", "Who filed the report"],
        ["item_name", "VARCHAR(200)", "Short name — the highest-weighted AI signal (20 %)"],
        ["category_id", "INT FK → categories", "Category — 10 % weight; exact match = 1.0, mismatch = 0.3"],
        ["brand / model", "VARCHAR(100)", "Brand (8 %) supports substring bonus; model (6 %) uses text similarity"],
        ["color / shape", "VARCHAR(50)", "Colour uses 10 colour groups (black, white, blue …); shape uses 8 alias groups"],
        ["serial_number", "VARCHAR(100)", "Part of <i>identical_features</i> — exact match = 1.0, else 0.0, null → excluded"],
        ["unique_marks", "TEXT", "Scratches, engravings etc. — scored by text similarity within <i>identical_features</i>"],
        ["approximate_value", "DECIMAL(12,2)", "UGX estimate — ratio-based scoring within <i>identical_features</i>"],
        ["description", "TEXT", "Free text — Jaccard (60 %) + SequenceMatcher (40 %) — 10 % weight"],
        ["date_lost / date_found", "DATE", "Date proximity decay: 0 d→1.0, 1 d→0.95, 3 d→0.85, 7 d→0.7, 14 d→0.5, 30 d→0.3, &gt;30 d→0.1"],
        ["time_lost / time_found", "TIME nullable", "Time proximity: ≤30 m→1.0, ≤60 m→0.9, ≤120 m→0.7, ≤360 m→0.5, &gt;360 m→0.2"],
        ["location_id", "INT FK → locations", "Named location — same id = 1.0, else 0.2, plus 0.3× detail similarity bonus"],
        ["location_detail", "TEXT nullable", "Free-text detail (\"near Room 3B\") — used for the bonus above"],
        ["additional_details", "TEXT nullable", "Any extra context; not scored by AI (stored for human review)"],
        ["current_location", "VARCHAR(255) nullable", "<b>Found only</b> — where the item is being kept"],
        ["image_path / shape_data", "VARCHAR(300) / TEXT", "Primary photo path (random hex filename) + optional shape JSON"],
        ["status", "ENUM", "11 values: reported → under_review → potential_match → match_pending_approval → match_approved / match_rejected → owner_verification_pending → owner_verified → recovered → closed → archived"],
        ["verified_by / verified_at", "INT FK / TIMESTAMP", "Who/when the item was verified (admin action)"],
        ["created_at / updated_at", "TIMESTAMP", "Auto-managed; updated_at has ON UPDATE CURRENT_TIMESTAMP"],
    ],
    col_widths=[3.1*cm, 3.0*cm, 10.3*cm]
))
story.append(Paragraph("Table 4 — Item columns. Enum values are enforced by MySQL; the app also validates them before writing.", S_CAPTION))

# 5.3 matches, notifications, etc.
story.append(Paragraph("5.3 &nbsp; Supporting tables", S_H2))
story.append(styled_table(
    ["Table", "Key columns &amp; meaning"],
    [
        ["<b>matches</b>", "<b>lost_item_id, found_item_id</b> (FKs) · <b>confidence_score</b> DECIMAL(5,2) 0–100 · <b>match_level</b> ENUM(very_high, high, possible, low) · <b>explanation</b> TEXT (bullet list + Overall Confidence) · <b>status</b> ENUM(pending, approved, rejected, uncertain) · <b>reviewed_by / reviewed_at / review_notes</b>"],
        ["<b>notifications</b>", "<b>user_id</b> FK · <b>title</b> VARCHAR(200) · <b>message</b> TEXT · <b>type</b> ENUM(info, warning, success, match, recovery) · <b>is_read</b> BOOL · <b>related_type / related_id</b> (polymorphic pointer, e.g. match/42) · <b>created_at</b>"],
        ["<b>verification_requests</b>", "<b>match_id</b> FK · <b>requester_id / claimer_id</b> FKs · <b>claimer_name / email / phone</b> (denormalised) · <b>additional_info</b> TEXT · <b>secret_identifier</b> VARCHAR(255) (private proof) · <b>status</b> ENUM(pending, approved, rejected) · <b>reviewed_by/at/notes</b>"],
        ["<b>recoveries</b>", "<b>match_id</b> FK · <b>recovered_by_id</b> FK · <b>recovered_date</b> DATE · <b>recovery_notes</b> TEXT · <b>recovered_by_name</b> VARCHAR(150) · <b>status</b> ENUM(pending, completed, cancelled)"],
        ["<b>activity_logs</b>", "<b>user_id</b> FK nullable · <b>action</b> VARCHAR(100) (login, report_lost, approve_match …) · <b>description</b> TEXT · <b>entity_type / entity_id</b> (e.g. lost_items/7) · <b>ip_address</b> VARCHAR(50) · <b>created_at</b>"],
        ["<b>users</b>", "<b>full_name, email UNIQUE, phone, student_staff_id, password_hash</b> (bcrypt), <b>role_id, faculty_id, course_id</b> FKs, <b>is_active, email_verified</b> BOOL, <b>profile_image</b> VARCHAR(500), timestamps"],
        ["<b>item_images</b>", "<b>item_id, item_type</b> ENUM(lost, found), <b>image_path</b> — reserved for multi-image galleries (the current UI uses the single <i>image_path</i> on the item row)."],
    ],
    col_widths=[3.2*cm, 13.2*cm]
))

story.append(Paragraph("5.4 &nbsp; Indexes", S_H2))
story.append(p("Sixteen indexes accelerate the queries that run on every page load. They were added to <i>schema.sql</i> and back-ported via <i>migration_add_indexes.sql</i> for older databases:"))
story.append(styled_table(
    ["Index", "Table(column)", "Why it exists"],
    [
        ["idx_lost_items_reporter", "lost_items(reporter_id)", "My Reports + dashboard recents"],
        ["idx_lost_items_status", "lost_items(status)", "Matcher scan + admin filters"],
        ["idx_lost_items_created", "lost_items(created_at)", "ORDER BY created_at DESC LIMIT"],
        ["idx_found_items_finder", "found_items(finder_id)", "My Reports + dashboard"],
        ["idx_found_items_status", "found_items(status)", "Matcher scan + admin filters"],
        ["idx_found_items_created", "found_items(created_at)", "ORDER BY recents"],
        ["idx_matches_status", "matches(status)", "Admin Match Review filter"],
        ["idx_matches_lost / found", "matches(lost_item_id / found_item_id)", "JOINs in /matches and admin views"],
        ["idx_matches_created", "matches(created_at)", "ORDER BY newest matches"],
        ["idx_notifications_user", "notifications(user_id)", "Inbox query"],
        ["idx_notifications_read", "notifications(is_read)", "Unread badge count"],
        ["idx_notifications_created", "notifications(created_at)", "ORDER BY newest"],
        ["idx_users_role / active", "users(role_id / is_active)", "Login + admin user list"],
        ["idx_activity_logs_created", "activity_logs(created_at)", "Admin activity log pagination"],
    ],
    col_widths=[4.3*cm, 5.0*cm, 7.1*cm]
))

# ═══════════════════════════════════════════════════════════════════════
# 6. ROLES & AUTH
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("6 &nbsp; User Roles, Registration &amp; Authentication", S_H1))
story.append(hr())
story.append(Paragraph("6.1 &nbsp; Roles", S_H2))
story.append(p(
    "Roles are stored in <i>roles</i> and referenced by <i>users.role_id</i>. Only three exist; the app checks them by name via "
    "<i>get_role_name(role_id)</i> and by id (<b>3 == Administrator</b>) in the <i>admin_required</i> decorator."
))
story.append(styled_table(
    ["ID", "Name", "How you get it", "Session key"],
    [
        ["1", "Student", "Self-registration (user_type = Student)", "role_name = \"Student\""],
        ["2", "Lecturer", "Self-registration (user_type = Lecturer)", "role_name = \"Lecturer\""],
        ["3", "Administrator", "Inserted directly in DB (seed.sql / manual INSERT); cannot self-register", "role_name = \"Administrator\"; admin_required checks role_id == 3"],
    ],
    col_widths=[1.2*cm, 2.8*cm, 7.5*cm, 4.9*cm]
))
story.append(p(
    "The registration form (<b>POST /register</b>) validates: passwords match, length ≥ 6, email not already taken, role is Student/Lecturer, "
    "then hashes with <b>bcrypt.hashpw + gensalt</b> and inserts. Faculties and courses are loaded from active rows for the dropdowns. "
    "On success the user is redirected to <b>/login</b> with a success flash; no auto-login."
))
story.append(Paragraph("6.2 &nbsp; Login &amp; session", S_H2))
story.append(p(
    "POST /login looks up the user by email, checks <b>bcrypt.checkpw</b>, rejects deactivated accounts (<i>is_active = FALSE</i>), "
    "then populates the Flask session and calls <i>log_activity(user_id, 'login')</i>. The session lives in a signed cookie; there is no "
    "server-side session store. <b>GET /logout</b> logs the event and calls <i>session.clear()</i>."
))
story.append(styled_table(
    ["Route", "Method", "Auth", "What it does"],
    [
        ["<b>/</b>  (index)", "GET", "Public", "Landing page — hero, how-it-works, stats, CTA. Standalone template (no base.html)."],
        ["<b>/about</b>", "GET", "Public", "Mission, features, team. Standalone template."],
        ["<b>/login</b>", "GET / POST", "Public", "Email + password form; sets session on success; flashes errors."],
        ["<b>/register</b>", "GET / POST", "Public", "Full name, email, phone, student/staff ID, password×2, role (Student/Lecturer), faculty, course."],
        ["<b>/forgot-password</b>", "GET / POST", "Public", "Accepts email, always flashes the same message (\"If an account exists …\") — does not reveal whether the email exists. No email is actually sent (Flask-Mail not wired)."],
        ["<b>/logout</b>", "GET", "Any session", "Clears session; logs activity."],
        ["<b>/change-password</b>", "GET / POST", "login_required", "Verifies current password, checks new passwords match &amp; length ≥ 6, re-hashes, updates row."],
        ["<b>/settings</b>", "GET / POST", "login_required", "Edit full_name, phone, student_staff_id, avatar (jpg/jpeg/png/webp, ≤5 MB, saved via save_image to avatars/). Updates session keys."],
        ["<b>/profile</b>", "GET / POST", "login_required", "Alias — redirects to /settings."],
    ],
    col_widths=[3.6*cm, 1.9*cm, 2.3*cm, 8.6*cm]
))
story.append(Paragraph("Table 5 — Auth &amp; account routes. Every login_required route redirects to /login with a warning flash if no session.", S_CAPTION))
story.append(note_box(
    "<b>Forgot-password</b> is intentionally vague (same message whether the email exists or not) to avoid user-enumeration. "
    "Actual email delivery is a planned extension — the Flask-Mail dependency is already in <i>requirements.txt</i> but not yet used in <i>app.py</i>.",
    title="Privacy note", bg=SLATE_50, border=SLATE_300
))

# ═══════════════════════════════════════════════════════════════════════
# 7. SECURITY
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("7 &nbsp; Security Architecture", S_H1))
story.append(hr())
story.append(styled_table(
    ["Concern", "How FindMe handles it (code reference)"],
    [
        ["Password storage", "<b>bcrypt</b> with per-password salt (gensalt). Hashes stored in <i>users.password_hash</i> VARCHAR(255). Plaintext never logged or compared with ==."],
        ["SQL injection", "Every query uses <b>parameterised placeholders (%s)</b> via flask-mysqldb. The only f-string interpolation is for the table name in <i>get_reference_name</i> and the WHERE clause in <i>/search</i> — both use a fixed allowlist, never user input."],
        ["Access control", "<b>login_required</b> (session has user_id) and <b>admin_required</b> (role_id == 3) decorators on every protected route. <i>role_required(*names)</i> for finer checks. Direct URL access without the right role redirects to /dashboard with a danger flash."],
        ["Deactivated users", "Login checks <b>is_active</b>; deactivated users get \"Your account has been deactivated\" and no session is created. Admin can toggle active/inactive per user."],
        ["File uploads", "<b>allowed_file()</b> checks extension against {jpg, jpeg, png, webp}; <b>secure_filename</b> is imported (defence in depth); Pillow re-encodes every image (thumbnail 1200 px, RGB conversion, optimize + quality 85) — stripping EXIF and preventing polyglot payloads. Avatar limit 5 MB, global MAX_CONTENT_LENGTH 16 MB. Filenames are random hex, not user-supplied."],
        ["Session security", "Flask signed cookies with <b>SECRET_KEY</b> (env-var override; default is a dev key that must be changed in production — see <i>config.py</i>). No sensitive data beyond display names is kept in the cookie."],
        ["Enumeration", "Forgot-password returns the same message whether the email exists; login returns generic \"Invalid email or password\" without distinguishing which field was wrong."],
        ["Audit trail", "Every state-changing action calls <b>log_activity()</b> → <i>activity_logs</i> with user_id, action, description, entity_type/id, and <b>request.remote_addr</b>. Viewable at /admin/activity-logs (paginated, 50/page)."],
        ["XSS (stored)", "Jinja2 auto-escapes all template variables by default. User-supplied text (names, descriptions) is rendered through <b>{{ var }}</b> without |safe, so HTML is escaped."],
        ["CSRF", "State-changing admin actions are <b>POST-only</b> with a confirmation step in the UI. Full CSRF tokens (Flask-WTF) are a recommended hardening (see §14)."],
    ],
    col_widths=[3.4*cm, 13.0*cm]
))
story.append(Paragraph("Table 6 — Security controls mapped to code.", S_CAPTION))
story.append(note_box(
    "Rate limiting on login, CSRF tokens, and email verification are not yet implemented (see §14 Future Roadmap). "
    "For a public deployment, add Flask-Limiter on <b>POST /login</b> and <b>POST /register</b>, and enable Flask-WTF CSRF on every POST form.",
    title="Hardening recommendations", bg=HexColor("#FFFBEB"), border=AMBER
))

# ═══════════════════════════════════════════════════════════════════════
# 8. CORE USER WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("8 &nbsp; Core User Workflows — Step by Step", S_H1))
story.append(hr())
story.append(p(
    "Every workflow below is described exactly as it is implemented in <i>app.py</i> and the corresponding template. "
    "Status values, reference formats, and limits are quoted from code, not from the README."
))

# 8.1 Dashboard
story.append(Paragraph("8.1 &nbsp; Dashboard  —  <font size=\"8\" color=\"#64748B\">GET /dashboard  ·  login_required</font>", S_H2))
story.append(p(
    "The dashboard is the first page after login. It runs <b>8 count queries in one round-trip</b> plus three \"recent\" lists:"
))
for b in bullets([
    "<b>Stats row</b> — total_lost (COUNT lost_items WHERE reporter_id = you), total_found (WHERE finder_id = you), pending_reports (lost WHERE status = 'reported'), pending_matches (JOIN matches WHERE status = 'pending' AND you are reporter or finder), approved_matches, recovered (JOIN recoveries WHERE status = 'completed').",
    "<b>Recent Lost / Found</b> — last 5 rows each, ORDER BY created_at DESC.",
    "<b>Recent Matches</b> — last 5 matches involving you, with lost_ref/found_ref and names via JOINs.",
    "<b>Notifications preview</b> — last 10 for you, plus <b>unread_count</b> (WHERE is_read = FALSE) stored as <i>session['_unread_count']</i> for the bell badge in the top bar.",
]):
    story.append(b)
story.append(p("Cards use Font Awesome icons (e.g. fa-circle-exclamation, fa-magnifying-glass, fa-brain) on gradient backgrounds. Empty states show a friendly inbox illustration."))

# 8.2 Report Lost
story.append(Paragraph("8.2 &nbsp; Report Lost Item  —  <font size=\"8\" color=\"#64748B\">GET/POST /report-lost  ·  login_required</font>", S_H2))
story.append(p("The form collects the richest set of attributes in the system — every field maps 1:1 to a column in <i>lost_items</i> or to an AI scoring signal:"))
story.append(styled_table(
    ["Field (form name)", "Required", "AI role"],
    [
        ["item_name", "Yes", "20 % — text_similarity via SequenceMatcher (case-insensitive)"],
        ["category_id", "No", "10 % — exact id match = 1.0, else 0.3"],
        ["brand / model", "No", "8 % / 6 % — brand supports substring bonus; model is pure similarity"],
        ["color / shape", "No", "8 % / 4 % — colour via 10 colour groups; shape via 8 alias groups"],
        ["serial_number", "No", "Part of identical_features (6 %) — exact = 1.0, else 0.0, null → excluded"],
        ["unique_marks", "No", "Part of identical_features — text similarity"],
        ["approximate_value", "No", "Part of identical_features — ratio tiers (≥0.9 → 1.0, ≥0.7 → 0.8 …)"],
        ["description", "No", "10 % — Jaccard 60 % + SequenceMatcher 40 %"],
        ["date_lost / time_lost", "Date yes", "4 % / 2 % — decay curves (see §9.3)"],
        ["location_id / location_detail", "No", "10 % — same location = 1.0 else 0.2 + 0.3× detail similarity"],
        ["additional_details", "No", "Not scored — shown to admin for human judgement"],
        ["image (file)", "No", "Part of appearance (8 %) — simulated similarity (see §9.3)"],
    ],
    col_widths=[3.8*cm, 1.6*cm, 11.0*cm]
))
story.append(p(
    "On POST: the handler validates <b>item_name + date_lost</b>, saves the image (if any) to <b>static/uploads/lost/&lt;hex&gt;.ext</b> via "
    "<i>save_image</i>, generates a reference <b>FM-YYYY-NNNNN</b> (<i>generate_reference('FM','lost')</i> — MAX(id)+1, zero-padded to 5), "
    "inserts with <b>status = 'reported'</b>, logs <i>report_lost</i>, spawns the matcher thread (<i>threading.Thread → _run_matcher_async('lost', item_id)</i>), "
    "and redirects to <b>/my-reports</b> with a success flash. Categories and locations for the dropdowns come from active rows only."
))

# 8.3 Report Found
story.append(Paragraph("8.3 &nbsp; Report Found Item  —  <font size=\"8\" color=\"#64748B\">GET/POST /report-found  ·  login_required</font>", S_H2))
story.append(p(
    "Identical to Report Lost except: the date field is <b>date_found</b>, the time field is <b>time_found</b>, there is an extra "
    "<b>current_location</b> text field (where the finder is keeping the item), images go to <b>static/uploads/found/</b>, "
    "and the reference still uses prefix <b>FM</b> but counts from <i>found_items</i>. The matcher is spawned as <i>('found', item_id)</i> "
    "and scans <i>lost_items</i> instead."
))

# 8.4 Search & Item Detail
story.append(Paragraph("8.4 &nbsp; Search &amp; Item Detail", S_H2))
story.append(Paragraph("Search  —  GET /search  ·  login_required", S_H3))
story.append(p(
    "Search is a <b>filtered union</b> over both tables. Query parameters: <b>q</b> (keyword), <b>category_id</b>, <b>location_id</b>, "
    "<b>type</b> (lost/found/any), <b>status</b>. If none are set, no results are shown (prevents an expensive full scan). When filters exist, "
    "the handler builds a WHERE clause with <b>LIKE %q%</b> over (item_name, description, brand, color) and appends category/location/status "
    "equality checks. It then runs one SELECT per table (up to 100 each), merges the lists, and renders them with their type badge. "
    "Categories and locations for the filter dropdowns are loaded from active rows."
))
story.append(Paragraph("Item Detail  —  GET /item/&lt;lost|found&gt;/&lt;id&gt;  ·  login_required", S_H3))
story.append(p(
    "Loads the single item by id (404 if missing), resolves the reporter/finder's name and email, and renders all columns including the image, "
    "status badge, and action buttons. No edit/delete is exposed here — status changes happen only through admin screens."
))

# 8.5 My Reports, Matches, Notifications
story.append(Paragraph("8.5 &nbsp; My Reports, Matches &amp; Notifications", S_H2))
story.append(Paragraph("My Reports  —  GET /my-reports", S_H3))
story.append(p("Two queries: <b>lost_items WHERE reporter_id = you</b> and <b>found_items WHERE finder_id = you</b> (each LIMIT 50, LEFT JOIN categories for the name), rendered as two tabbed lists with status badges and reference codes."))
story.append(Paragraph("Matches  —  GET /matches  and  GET /match/&lt;id&gt;", S_H3))
story.append(p(
    "<b>/matches</b> shows every match where you are the reporter of the lost item <b>or</b> the finder of the found item "
    "(JOIN lost_items + found_items + users for names, LIMIT 100, ORDER BY created_at DESC). Each row shows the confidence score, "
    "level badge, and status. <b>/match/&lt;id&gt;</b> shows the full side-by-side comparison: both references, names, descriptions, colours, "
    "shapes, serials, marks, values, brands, images, and location details, plus the AI explanation text."
))
story.append(Paragraph("Notifications  —  GET /notifications", S_H3))
story.append(p(
    "A simple inbox: <b>SELECT * FROM notifications WHERE user_id = you ORDER BY created_at DESC</b>. Types are <b>info, warning, success, match, recovery</b>; "
    "unread rows are highlighted and counted for the bell badge. Notifications are created by the matcher (potential match), by admin approval/rejection, "
    "and by verification/recovery transitions. There is no email delivery yet — all notifications are in-app only."
))

# 8.6 Settings
story.append(Paragraph("8.6 &nbsp; Settings, Profile &amp; Password", S_H2))
story.append(p(
    "<b>/settings</b> (also aliased as <b>/profile</b>) loads the current <i>users</i> row plus active faculties/courses. POST updates "
    "<b>full_name, phone, student_staff_id</b> and optionally an avatar image (same validation as item images but with a <b>5 MB</b> limit and "
    "saved to <b>avatars/</b>). On success the session keys are refreshed so the sidebar reflects the new name/avatar immediately. "
    "<b>/change-password</b> verifies the current password with bcrypt, checks the two new passwords match and are ≥ 6 chars, re-hashes, and updates the row."
))

# ═══════════════════════════════════════════════════════════════════════
# 9. AI MATCHING ENGINE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("9 &nbsp; AI Matching Engine — Deep Dive  (<i>ai/matcher.py</i>)", S_H1))
story.append(hr())
story.append(Paragraph("9.1 &nbsp; Design philosophy — AI assists, it does not decide", S_H2))
story.append(p(
    "The engine is deliberately <b>not</b> a black-box ML model. Every score is a weighted sum of explainable, rule-based signals, and every match "
    "stores a <b>human-readable explanation</b> (bullet list of per-factor percentages + overall confidence). An administrator must review the "
    "explanation and the two items side-by-side before any match becomes \"approved\". This satisfies the academic requirement for "
    "<b>AI governance</b> and keeps the system auditable even without data-science expertise."
))
story.append(p(
    "The module is also <b>isolated</b>: only two functions are called from <i>app.py</i> — <i>find_potential_matches(item_type, item_id, db)</i> "
    "and <i>rerun_all_matches(db)</i>. Replacing the internals with a real embedding model or an external API requires changing only this file."
))

story.append(Paragraph("9.2 &nbsp; The 12 weighted factors (actual code weights)", S_H2))
story.append(p(
    "Weights are defined in <i>compute_match_score(lost, found)</i> as a dict that sums to <b>0.96</b>. Each factor's raw score is in [0, 1]; "
    "the final confidence is <b>(Σ score_i × weight_i) × 100</b>, clamped to [0, 100]. A perfect match therefore scores <b>96 %</b> (not 100 %) — "
    "a deliberate consequence of the current weight table. Only pairs with <b>confidence ≥ 30 %</b> are persisted."
))
story.append(styled_table(
    ["#", "Factor (key)", "Weight", "What it compares", "Scoring function"],
    [
        ["1", "item_name", "0.20  (20 %)", "Short item name", "text_similarity — SequenceMatcher ratio, case-insensitive"],
        ["2", "category", "0.10  (10 %)", "Category id", "category_match — exact = 1.0, else 0.3"],
        ["3", "description", "0.10  (10 %)", "Free-text description", "description_similarity — Jaccard 60 % + SequenceMatcher 40 %"],
        ["4", "location", "0.10  (10 %)", "Location id + detail", "location_match — same id 1.0 else 0.2 + 0.3× detail similarity"],
        ["5", "color", "0.08  (8 %)", "Colour string", "color_match — exact 1.0; same colour group 0.8; else 0.0"],
        ["6", "brand", "0.08  (8 %)", "Brand string", "brand_match — exact 1.0; substring 0.9; else similarity"],
        ["7", "appearance", "0.08  (8 %)", "Image + shape (combined)", "appearance_match — image_sim 60 % + shape 40 %"],
        ["8", "model", "0.06  (6 %)", "Model string", "text_similarity"],
        ["9", "identical_features", "0.06  (6 %)", "Serial + marks + value (avg)", "identical_features_match — mean of available sub-scores"],
        ["10", "date", "0.04  (4 %)", "Date lost vs found", "date_proximity — decay curve (0 d→1.0 … >30 d→0.1)"],
        ["11", "shape", "0.04  (4 %)", "Shape string", "shape_match — exact 1.0; same alias group 0.85; else similarity"],
        ["12", "time", "0.02  (2 %)", "Time lost vs found", "time_proximity — ≤30 m→1.0 … >360 m→0.2"],
        ["", "<b>Total</b>", "<b>0.96</b>", "Maximum achievable confidence = <b>96 %</b>", ""],
    ],
    col_widths=[0.7*cm, 2.8*cm, 1.9*cm, 4.8*cm, 6.2*cm],
    header_color=NAVY
))
story.append(Paragraph("Table 7 — The 12 factors as coded in <i>ai/matcher.py:285–298</i>. The README's weight table (25/15/…) is outdated; the PDF documents the live values.", S_CAPTION))
story.append(note_box(
    "Why 0.96 and not 1.00? The weights were likely intended to sum to 1.00 but currently total 0.96 due to a missing 0.04 allocation. "
    "This is harmless (scores are simply capped at 96 %) but worth correcting to 1.00 if you want a true 100 % ceiling — e.g. move 0.04 to <i>identical_features</i> or <i>shape</i>.",
    title="Weight sum note", bg=HexColor("#FFFBEB"), border=AMBER
))

story.append(Paragraph("9.3 &nbsp; How each factor is scored", S_H2))

story.append(Paragraph("Text similarity — <i>text_similarity(s1, s2)</i>", S_H3))
story.append(p("Lowercases and strips both strings; returns 0.0 if either is empty; otherwise <b>difflib.SequenceMatcher(None, s1, s2).ratio()</b> in [0, 1]. Used for item_name, model, and as a fallback for brand/shape."))

story.append(Paragraph("Category — <i>category_match(c1, c2)</i>", S_H3))
story.append(p("Tries <b>int(c1) == int(c2)</b> → 1.0. On any mismatch, ValueError, or null → <b>0.3</b> (not 0.0) — so a category mismatch still leaves 30 % of the category weight, reflecting that categories can be mislabelled."))

story.append(Paragraph("Colour — <i>color_match(c1, c2)</i>", S_H3))
story.append(p("Exact string match → 1.0. Otherwise checks 10 colour groups:"))
# colour groups as a compact table
story.append(styled_table(
    ["Group", "Members (any match within the group → 0.8)"],
    [
        ["black", "black, dark, charcoal, midnight"],
        ["white", "white, light, cream, ivory"],
        ["blue", "blue, navy, cyan, azure"],
        ["red", "red, darkred, crimson, scarlet"],
        ["green", "green, darkgreen, forest, olive"],
        ["silver", "silver, gray, grey, metallic"],
        ["gold", "gold, golden, yellow, brass"],
        ["brown", "brown, tan, beige, darkbrown"],
        ["pink", "pink, rose, magenta"],
        ["purple", "purple, violet, lavender"],
    ],
    col_widths=[2.2*cm, 14.2*cm], header_color=HexColor("#334155"), fontsize=6.8, header_fontsize=6.5
))
story.append(p("If neither exact nor grouped → 0.0. Null → 0.0."))

story.append(Paragraph("Brand — <i>brand_match(b1, b2)</i>", S_H3))
story.append(p("Exact → 1.0; substring (one contains the other) → 0.9; otherwise text_similarity. Null → 0.0."))

story.append(Paragraph("Description — <i>description_similarity(d1, d2)</i>", S_H3))
story.append(p(
    "Tokenises both descriptions into word sets, computes <b>Jaccard = |intersection| / |union|</b>, computes <b>SequenceMatcher</b> on the full strings, "
    "then returns <b>Jaccard × 0.6 + SequenceMatcher × 0.4</b>. This rewards both shared keywords and overall phrasing. Null → 0.0."
))

story.append(Paragraph("Location — <i>location_match(id1, id2, detail1, detail2)</i>", S_H3))
story.append(p(
    "Base score: same <i>location_id</i> → 1.0, different → 0.2, either null → 0.0. Bonus: if both <i>location_detail</i> strings exist, "
    "adds <b>text_similarity(detail1, detail2) × 0.3</b>, capped at 1.0. So \"Library, near Room 3B\" vs \"Library, Room 3B entrance\" gets close to 1.0 even with the same location_id."
))

story.append(Paragraph("Date proximity — <i>date_proximity(d1, d2)</i>", S_H3))
story.append(styled_table(
    ["Δ days", "Score", "Δ days", "Score"],
    [
        ["0", "1.00", "≤ 7", "0.70"],
        ["≤ 1", "0.95", "≤ 14", "0.50"],
        ["≤ 3", "0.85", "≤ 30", "0.30"],
        ["null / parse error", "0.30", "> 30", "0.10"],
    ],
    col_widths=[3.4*cm, 2.2*cm, 3.4*cm, 2.2*cm], header_color=HexColor("#334155")
))
story.append(Paragraph("Dates are parsed as <b>%Y-%m-%d</b>; any failure returns 0.3.", S_CAPTION))

story.append(Paragraph("Time proximity — <i>time_proximity(t1, t2)</i>", S_H3))
story.append(styled_table(
    ["Δ minutes", "Score", "Δ minutes", "Score"],
    [
        ["≤ 30", "1.00", "≤ 360 (6 h)", "0.50"],
        ["≤ 60", "0.90", "> 360", "0.20"],
        ["≤ 120 (2 h)", "0.70", "null / parse error", "0.30"],
    ],
    col_widths=[3.4*cm, 2.2*cm, 3.4*cm, 2.2*cm], header_color=HexColor("#334155")
))
story.append(Paragraph("Times are parsed as <b>%H:%M</b>.", S_CAPTION))

story.append(Paragraph("Appearance — <i>appearance_match(lost, found)</i> + <i>image_similarity_simulated</i>", S_H3))
story.append(p(
    "Appearance is a composite: <b>image_score × 0.6 + shape_score × 0.4</b>, rounded to 4 decimals. <i>image_similarity_simulated</i> is explicitly "
    "a placeholder (the docstring says \"simulated\") — it compares <b>filenames</b>, not pixels:"
))
for b in bullets([
    "Same basename (no ext) → 1.0; one basename contains the other → 0.85; same extension only → 0.45.",
    "Keyword heuristic over {phone, laptop, tablet, wallet, bag, watch, ring, keys, book, glasses, camera, headphones} — both contain same keyword → 0.6; one contains → 0.35; neither → 0.25.",
    "Either image null → 0.3.",
]):
    story.append(b)
story.append(note_box(
    "This is the most obvious upgrade point. Replace <i>image_similarity_simulated</i> with a real embedding model (e.g. CLIP, ResNet cosine) "
    "and keep the same 0.6/0.4 blend. The rest of the pipeline does not need to change.",
    title="Upgrade path", bg=SLATE_50, border=SLATE_300
))

story.append(Paragraph("Shape — <i>shape_match(s1, s2)</i>", S_H3))
story.append(p("Exact → 1.0. Otherwise checks 8 alias groups (any two members of the same group → 0.85):"))
story.append(styled_table(
    ["Group", "Aliases"],
    [
        ["rectangular", "rectangular, rectangle, oblong, rectangular-shaped"],
        ["round", "round, circular, circle, oval, elliptical"],
        ["cylindrical", "cylindrical, cylinder, tube, tubular"],
        ["square", "square, box-shaped, cubical"],
        ["triangular", "triangular, triangle, pyramid"],
        ["irregular", "irregular, asymmetric, irregularly shaped"],
        ["flat", "flat, thin, pancake, disc-shaped"],
        ["compact", "compact, small, tiny, miniature"],
    ],
    col_widths=[2.4*cm, 14.0*cm], header_color=HexColor("#334155"), fontsize=6.8, header_fontsize=6.5
))
story.append(p("No group match → text_similarity. Null → 0.0."))

story.append(Paragraph("Identical features — <i>identical_features_match(lost, found)</i>", S_H3))
story.append(p(
    "Averages up to three sub-scores, but <b>only those where both sides are non-null</b> are included. If none are available, the factor scores 0.0 and contributes nothing:"
))
story.append(styled_table(
    ["Sub-factor", "Logic"],
    [
        ["serial_number", "Both present → exact string equality: 1.0 if equal, else 0.0. Either null → excluded (returns None)."],
        ["unique_marks", "Both present → text_similarity (lowercased). Either null → excluded."],
        ["approximate_value", "Both present → ratio = min/max: ≥0.9→1.0, ≥0.7→0.8, ≥0.5→0.5, ≥0.3→0.3, else 0.1. Either 0 → 0.1 (or 1.0 if both 0). Either null/invalid → excluded."],
    ],
    col_widths=[3.2*cm, 13.2*cm]
))
story.append(p("Example: if only <i>serial_number</i> is filled on both sides and it matches, identical_features = 1.0 → contributes 0.06 × 1.0 = 6 points. If all three are present, the mean of the three is used."))

story.append(Paragraph("9.4 &nbsp; Overall confidence formula &amp; match levels", S_H2))
story.append(p("After all 12 raw scores are computed:"))
# formula box
formula = Table([[Paragraph(
    '<font face="Helvetica-Bold" size="8" color="#1A274B">confidence = clamp( Σ (score<sub>i</sub> × weight<sub>i</sub>) × 100 ,  0 , 100 )</font><br/>'
    '<font size="7" color="#64748B">Each score<sub>i</sub> ∈ [0,1], each weight<sub>i</sub> from Table 7. The explanation text is built as a bullet list of '
    '“Label: N%” lines (one per factor plus any identical-feature sub-lines) followed by “Overall Confidence: N%”.</font>',
    S_BODY
)]], colWidths=[16.4*cm])
formula.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), SLATE_100),
    ("BOX", (0,0), (-1,-1), 0.6, SLATE_300),
    ("TOPPADDING", (0,0), (-1,-1), 8),
    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
]))
story.append(formula)
story.append(Spacer(1, 0.2*cm))
story.append(styled_table(
    ["Confidence", "match_level (DB enum)", "Meaning in the UI"],
    [
        ["≥ 90 %", "very_high", "Very High — strong match, shown with a green/emerald badge"],
        ["75 – 89 %", "high", "High — likely match, blue badge"],
        ["50 – 74 %", "possible", "Possible — potential match, amber badge"],
        ["< 50 % (but ≥ 30 % stored)", "low", "Low — weak match, grey badge; still reviewable but unlikely"],
        ["< 30 %", "(not stored)", "Discarded — no <i>matches</i> row is created"],
    ],
    col_widths=[3.2*cm, 4.2*cm, 9.0*cm], header_color=NAVY
))
story.append(Paragraph("Table 8 — Confidence → match_level mapping (<i>matcher.py:354–361</i>). The 30 % storage threshold is in <i>find_potential_matches</i>.", S_CAPTION))

story.append(Paragraph("9.5 &nbsp; Matching pipeline — <i>find_potential_matches(item_type, item_id, db)</i>", S_H2))
story.append(p("This is the function the background thread calls. Its steps, line-for-line from <i>ai/matcher.py:371–478</i>:"))

steps = [
    ["1", "Load the triggering item", "SELECT * FROM lost_items WHERE id = %s  (if item_type=='lost')  or  found_items (if 'found'). If not found, return []."],
    ["2", "Load existing pairs", "SELECT lost_item_id, found_item_id FROM matches WHERE status IN ('pending','approved') → set of (lost,found) tuples for deduplication."],
    ["3a", "If lost → scan found", "SELECT * FROM found_items WHERE status IN ('reported','under_review','potential_match','match_pending_approval') ORDER BY created_at DESC LIMIT 200."],
    ["3b", "If found → scan lost", "Mirror of 3a over lost_items."],
    ["4", "Score each candidate", "For each candidate not already in the dedup set, call <i>compute_match_score(trigger, candidate)</i>."],
    ["5", "Persist if ≥ 30 %", "INSERT INTO matches (lost_item_id, found_item_id, confidence_score, match_level, explanation, status='pending'). Capture lastrowid."],
    ["6", "Notify both parties", "Two INSERTs into <i>notifications</i>: one for the reporter, one for the finder, each with title 'Potential Match Found', type='match', related_type='match', related_id=match_id, and a message containing the confidence integer."],
    ["7", "Commit &amp; return", "COMMIT after each insert; return the list of new match dicts. The thread then exits."],
]
story.append(styled_table(["Step", "Action", "Detail"], steps, col_widths=[1.0*cm, 3.2*cm, 12.2*cm]))
story.append(p("Key properties: <b>deduplication</b> prevents the same lost↔found pair from being inserted twice; <b>LIMIT 200</b> caps work per report; "
               "the scan is ordered by <b>created_at DESC</b> so recent items are checked first. The function is called once per report, not as a batch job."))

story.append(Paragraph("9.6 &nbsp; Notifications, deduplication &amp; rerun", S_H2))
story.append(Paragraph("Deduplication", S_H3))
story.append(p(
    "Before scoring, the function builds a set of all (lost_item_id, found_item_id) pairs whose match status is <b>pending</b> or <b>approved</b>. "
    "Rejected/uncertain pairs are intentionally not in the set, so a previously rejected pair <i>can</i> be re-proposed if a new report triggers a re-scan — "
    "this is a deliberate design choice to allow a second chance after more data arrives."
))
story.append(Paragraph("Rerun — <i>rerun_all_matches(db)</i>", S_H3))
story.append(p(
    "A utility for admins/developers: <b>DELETE FROM matches</b>, then load up to 200 lost + 200 found items with the same status filter, "
    "score every cross-product pair (up to 40,000 comparisons), keep those ≥ 30 %, and bulk-insert them as <b>pending</b>. Returns the count. "
    "No notifications are sent during a rerun — it is a silent recomputation. Use it after fixing scoring weights or after a bulk import."
))
story.append(note_box(
    "Because <i>rerun_all_matches</i> deletes all matches first, call it only during maintenance windows. "
    "Approved matches will be regenerated as pending and will need re-approval.",
    title="Caution", bg=HexColor("#FEF2F2"), border=RED
))

# ═══════════════════════════════════════════════════════════════════════
# 10. ADMIN MODULE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("10 &nbsp; Administration Module — Every Admin Screen", S_H1))
story.append(hr())
story.append(p(
    "All admin routes are under <b>/admin/*</b> and protected by <b>login_required + admin_required</b>. The sidebar adds an <i>Administration</i> "
    "section only when <b>session.role_name == 'Administrator'</b>. Every admin action writes to <i>activity_logs</i> and, where user-visible, to <i>notifications</i>."
))
story.append(Paragraph("10.1 &nbsp; Admin Dashboard — <i>GET /admin/dashboard</i>", S_H2))
story.append(p("Aggregates counts for the overview cards and recent activity. Key queries:"))
for b in bullets([
    "User counts by role, active/inactive split.",
    "Lost/found totals and by-status breakdowns.",
    "Pending / approved / rejected match counts.",
    "Completed recoveries count.",
    "Recent activity_logs (latest 10) and recent matches.",
    "Category-wise lost vs found distribution (for the bar chart in the template).",
]):
    story.append(b)

story.append(Paragraph("10.2 &nbsp; User Management — <i>/admin/users</i>", S_H2))
story.append(p("Paginated table of all users (JOIN roles for the name, faculties/courses for display). Actions per row:"))
for b in bullets([
    "<b>Toggle active/inactive</b> — <i>POST /admin/users/&lt;id&gt;/toggle</i> flips <i>is_active</i>, logs <i>toggle_user</i>. Deactivated users cannot log in.",
    "<b>Delete</b> — <i>POST /admin/users/&lt;id&gt;/delete</i> — hard delete (use with care; foreign keys will block deletion if the user owns items/matches).",
]):
    story.append(b)

story.append(Paragraph("10.3 &nbsp; Taxonomy — Faculties, Courses, Categories, Locations", S_H2))
story.append(p("Four CRUD screens with identical patterns (<i>/admin/faculties</i>, <i>/admin/courses</i>, <i>/admin/categories</i>, <i>/admin/locations</i>):"))
for b in bullets([
    "List active/inactive rows with counts of linked users/items.",
    "<b>Add</b> — inline form (POST to the same URL) inserts with <i>is_active = TRUE</i>.",
    "<b>Toggle</b> — <i>POST /admin/&lt;entity&gt;/&lt;id&gt;/toggle</i> flips <i>is_active</i>; inactive options disappear from user-facing dropdowns but historical reports keep their FK.",
    "Courses additionally require a <i>faculty_id</i> foreign key; the form shows a faculty dropdown.",
]):
    story.append(b)

story.append(Paragraph("10.4 &nbsp; Item Management — <i>/admin/lost-items</i> &amp; <i>/admin/found-items</i>", S_H2))
story.append(p(
    "Paginated lists of all lost/found reports (JOIN users for reporter/finder, categories/locations for display). "
    "Each row shows reference, item name, status badge, date, and thumbnail. Actions:"
))
for b in bullets([
    "<b>Edit status</b> — <i>POST /admin/lost-items/&lt;id&gt;/edit-status</i> (and found equivalent) — admin can move an item through the 11-value status enum (reported → … → recovered/closed/archived). Validated against ITEM_STATUSES in <i>app.py:1644</i>.",
    "Item detail is viewable via the same <b>/item/&lt;type&gt;/&lt;id&gt;</b> route as regular users.",
]):
    story.append(b)

story.append(Paragraph("10.5 &nbsp; AI Match Review — <i>/admin/matches</i>  (the governance gate)", S_H2))
story.append(p(
    "The most important admin screen. It lists AI-generated matches with a <b>status filter</b> (pending / approved / rejected / uncertain / all), "
    "paginated (20/page via <i>paginated_query</i>). Each card shows both items side-by-side: references, names, colours, shapes, serials, marks, "
    "values, images, the confidence score and level badge, and the full <b>explanation</b> text (the bullet breakdown from the engine). Actions:"
))
story.append(styled_table(
    ["Action", "Route", "What it does"],
    [
        ["Approve", "POST /admin/match/&lt;id&gt;/approve", "UPDATE matches SET status='approved', reviewed_by=you, reviewed_at=NOW(); UPDATE both items SET status='match_approved'; INSERT two <i>notifications</i> (Match Approved → reporter &amp; finder); log <i>approve_match</i>."],
        ["Reject", "POST /admin/match/&lt;id&gt;/reject", "UPDATE matches SET status='rejected', reviewed_by=you, reviewed_at=NOW(); log <i>reject_match</i>. Items keep their current status."],
    ],
    col_widths=[1.8*cm, 5.0*cm, 9.6*cm]
))
story.append(p("Only <b>pending</b> matches are actionable; approved/rejected rows are shown for audit. The side-by-side image comparison is the primary human signal — the AI explanation is secondary."))

story.append(Paragraph("10.6 &nbsp; Verification Requests — <i>/admin/verifications</i>", S_H2))
story.append(p(
    "When ownership is disputed or additional proof is needed, a row is inserted into <i>verification_requests</i> (match_id, requester, claimer identity, "
    "<b>secret_identifier</b> — a private detail only the true owner would know, plus additional_info). The admin screen lists pending verifications with the "
    "linked match's references and the requester's name. Actions:"
))
story.append(styled_table(
    ["Action", "Route", "Effect"],
    [
        ["Approve", "POST /admin/verification/&lt;id&gt;/approve", "UPDATE verification_requests → approved; also UPDATE matches → approved; notify both requester and claimer (Verification Approved); log <i>approve_verification</i>."],
        ["Reject", "POST /admin/verification/&lt;id&gt;/reject", "UPDATE verification_requests → rejected; log <i>reject_verification</i>."],
    ],
    col_widths=[1.8*cm, 5.8*cm, 8.8*cm]
))

story.append(Paragraph("10.7 &nbsp; Recoveries — <i>/admin/recoveries</i>", S_H2))
story.append(p(
    "Tracks the physical handover. Each <i>recoveries</i> row ties a <b>match_id</b> to a <b>recovered_by_id</b>, a <b>recovered_date</b>, notes, and a status "
    "(pending / completed / cancelled). The list is ordered by created_at DESC. Action:"
))
for b in bullets([
    "<b>Mark completed</b> — <i>POST /admin/recovery/&lt;id&gt;/complete</i> sets <i>recoveries.status='completed', recovered_date=CURDATE()</i>, then updates the underlying <b>lost_items</b> and <b>found_items</b> to <b>'recovered'</b> via subqueries on <i>matches</i>, and logs <i>complete_recovery</i>.",
]):
    story.append(b)

story.append(Paragraph("10.8 &nbsp; Reports &amp; Activity Logs", S_H2))
story.append(Paragraph("Reports — <i>GET /admin/reports</i>", S_H3))
story.append(p("Read-only analytics: total lost/found, pending/approved/rejected matches, completed recoveries, and a <b>by-category</b> breakdown (LEFT JOIN counts per category, so categories with zero items still appear). Rendered as stat cards and a table; no export yet."))
story.append(Paragraph("Activity Logs — <i>GET /admin/activity-logs</i>", S_H3))
story.append(p("Paginated (50/page) append-only log: <b>SELECT al.*, u.full_name FROM activity_logs LEFT JOIN users ORDER BY created_at DESC</b>. Shows who did what, on which entity, from which IP, when. No delete/edit — the log is the audit trail."))

story.append(Paragraph("10.9 &nbsp; Admin Settings &amp; Reset", S_H2))
story.append(p(
    "<b>GET /admin/settings</b> renders system settings (currently minimal). <b>POST /admin/reset</b> is a destructive maintenance action: it wipes transactional data "
    "(items, matches, notifications, verifications, recoveries, logs) while preserving users/roles/taxonomy — intended for demo resets between presentations. "
    "It is POST-only and should be guarded by an additional confirmation in production."
))

# ═══════════════════════════════════════════════════════════════════════
# 11. END-TO-END LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("11 &nbsp; End-to-End Lifecycle — From Report to Recovery", S_H1))
story.append(hr())
story.append(p("The sequence below follows a single lost phone through the system, naming every status transition and DB write. It is the canonical demo script (see README §Demo Workflow) expanded with the actual code paths."))

lifecycle = [
    ["1", "Student A reports lost", "POST /report-lost → lost_items(status='reported', ref FM-2026-00001) · save_image(lost/) · thread → find_potential_matches('lost',1) scans found_items → no found yet → no matches.", "Student A sees the report in /my-reports (reported badge)."],
    ["2", "Student B reports found", "POST /report-found → found_items(status='reported', ref FM-2026-00002) · save_image(found/) · thread → find_potential_matches('found',2) scans lost_items → scores FM-2026-00001 vs FM-2026-00002 → e.g. 87 % (high) → INSERT matches(status='pending', explanation=…) + 2 notifications.", "Both students get a bell notification: \"Potential Match Found — Confidence: 87%\"."],
    ["3", "Admin reviews", "GET /admin/matches?status=pending → sees the 87 % card with side-by-side images and the explanation breakdown (Item name 95 %, Category 100 %, Colour 100 %, …).", "Admin compares the photos and the explanation; decides to approve."],
    ["4", "Admin approves", "POST /admin/match/1/approve → matches.status='approved', both items → 'match_approved', 2× notifications (Match Approved), activity_logs(approve_match).", "Both students' /matches now shows the match as approved; the match detail reveals full contact/location."],
    ["5a", "If ownership is clear", "No verification needed — proceed to recovery.", ""],
    ["5b", "If disputed", "A verification_requests row is created (secret_identifier = e.g. \"IMEI ending 4821\"). Admin reviews at /admin/verifications and approves → matches stays approved, both parties notified.", ""],
    ["6", "Recovery", "A recoveries row is created (match_id=1, recovered_by_id=…, status='pending'). Admin marks completed at POST /admin/recovery/1/complete → recoveries.status='completed', both items → 'recovered'.", "Case is closed. Reports still visible in /my-reports with recovered badge; activity_logs has the full chain."],
]
story.append(styled_table(
    ["Step", "What happens (code)", "What the user sees"],
    lifecycle,
    col_widths=[0.9*cm, 9.4*cm, 6.1*cm]
))
story.append(Paragraph("Figure 2 — Lifecycle with status transitions. Every arrow that changes a status also writes to <i>activity_logs</i>.", S_CAPTION))

# status diagram as a table
story.append(Paragraph("Status progression (visual summary)", S_H2))
story.append(p("Items move forward through statuses; matches have a simpler four-state lifecycle. The diagram below summarises the allowed transitions as implemented:"))
story.append(styled_table(
    ["Entity", "Status flow"],
    [
        ["lost_items /\nfound_items", "reported → under_review → potential_match → match_pending_approval → match_approved ─┬─→ owner_verification_pending → owner_verified ─┐\n"
         "                                                                                    └─→ match_rejected ──────────────────────┘\n"
         "                                                                                    └─→ recovered → closed → archived"],
        ["matches", "pending (AI-created) → approved (admin)  |  pending → rejected  |  pending → uncertain"],
        ["verification_requests", "pending → approved (also approves the match)  |  pending → rejected"],
        ["recoveries", "pending → completed (also sets items to recovered)  |  pending → cancelled"],
    ],
    col_widths=[3.0*cm, 13.4*cm]
))
story.append(Paragraph("The app enforces these transitions only through the admin POST routes; there is no direct status editing from the user side.", S_BODY))

# ═══════════════════════════════════════════════════════════════════════
# 12. ROUTE REFERENCE
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("12 &nbsp; Route Reference — All Endpoints", S_H1))
story.append(hr())
story.append(p("Every route in <i>app.py</i> with its method, auth requirement, and purpose. Decorators: <b>L</b> = login_required, <b>A</b> = admin_required."))
story.append(styled_table(
    ["#", "Route", "Method", "Auth", "Purpose"],
    [
        ["1", "/", "GET", "—", "Landing page"],
        ["2", "/about", "GET", "—", "About page"],
        ["3", "/login", "GET, POST", "—", "Sign in; sets session"],
        ["4", "/register", "GET, POST", "—", "Create Student/Lecturer account"],
        ["5", "/forgot-password", "GET, POST", "—", "Request reset (no email sent yet)"],
        ["6", "/logout", "GET", "L*", "Clear session (*logs even if no session)"],
        ["7", "/change-password", "GET, POST", "L", "Verify current, set new (≥6)"],
        ["8", "/profile", "GET, POST", "L", "Redirects to /settings"],
        ["9", "/settings", "GET, POST", "L", "Edit profile + avatar (≤5 MB)"],
        ["10", "/dashboard", "GET", "L", "Stats, recents, notifications preview"],
        ["11", "/report-lost", "GET, POST", "L", "Report lost item + spawn matcher"],
        ["12", "/report-found", "GET, POST", "L", "Report found item + spawn matcher"],
        ["13", "/my-reports", "GET", "L", "Your lost + found lists (LIMIT 50 each)"],
        ["14", "/search", "GET", "L", "Filtered union search (q, category, location, type, status)"],
        ["15", "/item/<type>/<id>", "GET", "L", "Single item detail (404 if missing)"],
        ["16", "/matches", "GET", "L", "Your matches (involving you, LIMIT 100)"],
        ["17", "/match/<id>", "GET", "L", "Match side-by-side detail"],
        ["18", "/notifications", "GET", "L", "Inbox (all for you, newest first)"],
        ["19", "/uploads/<path>", "GET", "—", "Serve uploaded image (send_from_directory)"],
        ["20", "/admin/dashboard", "GET", "L+A", "Admin overview + analytics"],
        ["21", "/admin/users", "GET", "L+A", "User table (paginated)"],
        ["22", "/admin/users/<id>/toggle", "POST", "L+A", "Flip is_active"],
        ["23", "/admin/users/<id>/delete", "POST", "L+A", "Hard delete user"],
        ["24", "/admin/faculties", "GET, POST", "L+A", "List + add faculties"],
        ["25", "/admin/faculties/<id>/toggle", "POST", "L+A", "Flip faculty is_active"],
        ["26", "/admin/courses", "GET, POST", "L+A", "List + add courses (with faculty)"],
        ["27", "/admin/courses/<id>/toggle", "POST", "L+A", "Flip course is_active"],
        ["28", "/admin/categories", "GET, POST", "L+A", "List + add categories"],
        ["29", "/admin/categories/<id>/toggle", "POST", "L+A", "Flip category is_active"],
        ["30", "/admin/locations", "GET, POST", "L+A", "List + add locations"],
        ["31", "/admin/locations/<id>/toggle", "POST", "L+A", "Flip location is_active"],
        ["32", "/admin/lost-items", "GET", "L+A", "All lost reports (paginated)"],
        ["33", "/admin/found-items", "GET", "L+A", "All found reports (paginated)"],
        ["34", "/admin/matches", "GET", "L+A", "AI matches with status filter (paginated)"],
        ["35", "/admin/match/<id>/approve", "POST", "L+A", "Approve match → items match_approved + notify"],
        ["36", "/admin/match/<id>/reject", "POST", "L+A", "Reject match"],
        ["37", "/admin/verifications", "GET", "L+A", "Pending verification requests"],
        ["38", "/admin/verification/<id>/approve", "POST", "L+A", "Approve verification → also approve match"],
        ["39", "/admin/verification/<id>/reject", "POST", "L+A", "Reject verification"],
        ["40", "/admin/recoveries", "GET", "L+A", "Recovery list"],
        ["41", "/admin/recovery/<id>/complete", "POST", "L+A", "Mark recovery completed → items recovered"],
        ["42", "/admin/reports", "GET", "L+A", "Aggregated stats + by-category breakdown"],
        ["43", "/admin/activity-logs", "GET", "L+A", "Audit trail (50/page)"],
        ["44", "/admin/lost-items/<id>/edit-status", "POST", "L+A", "Set lost item status (validated enum)"],
        ["45", "/admin/found-items/<id>/edit-status", "POST", "L+A", "Set found item status"],
        ["46", "/admin/settings", "GET", "L+A", "System settings page"],
        ["47", "/admin/reset", "POST", "L+A", "Wipe transactional data (demo reset)"],
    ],
    col_widths=[0.7*cm, 4.6*cm, 1.7*cm, 1.2*cm, 8.2*cm], header_color=NAVY, fontsize=6.7, header_fontsize=6.5
))
story.append(Paragraph("Table 9 — Complete route map. “L*” on /logout means it logs the event only if a session exists, then always clears and redirects.", S_CAPTION))
story.append(p(
    "Helpers not exposed as routes: <i>get_db(), allowed_file(), save_image(), log_activity(), paginated_query(), "
    "get_role_name(), get_*_name(), generate_reference(), _run_matcher_async()</i> and the three decorators. "
    "Error handlers: <b>413 Request Entity Too Large</b> (upload exceeds 16 MB) and <b>inject_now()</b> context processor (injects <i>now</i> for footer year)."
))

# ═══════════════════════════════════════════════════════════════════════
# 13. CONFIG & DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("13 &nbsp; Configuration, Deployment &amp; Operations", S_H1))
story.append(hr())
story.append(Paragraph("13.1 &nbsp; Configuration — <i>config.py</i>", S_H2))
story.append(styled_table(
    ["Key", "Default", "Env override", "Notes"],
    [
        ["SECRET_KEY", "findme-cavendish-secret-key-change-in-production", "SECRET_KEY", "Must be a long random string in production; used to sign session cookies."],
        ["MYSQL_HOST", "localhost", "MYSQL_HOST", "PythonAnywhere: yourusername.mysql.pythonanywhere-services.com"],
        ["MYSQL_PORT", "3306", "MYSQL_PORT", "int() cast"],
        ["MYSQL_USER", "root", "MYSQL_USER", ""],
        ["MYSQL_PASSWORD", "\"\"", "MYSQL_PASSWORD", "Empty for XAMPP default"],
        ["MYSQL_DB", "findme_db", "MYSQL_DB", "Created by schema.sql"],
        ["MYSQL_CHARSET", "utf8mb4", "—", "Full Unicode incl. emoji"],
        ["MYSQL_COLLATION", "utf8mb4_unicode_ci", "—", "Case-insensitive"],
        ["MYSQL_CONNECT_TIMEOUT", "30", "—", "Seconds"],
        ["UPLOAD_FOLDER", "static/uploads", "—", "BASE_DIR + static/uploads"],
        ["MAX_CONTENT_LENGTH", "16 MB", "—", "Flask aborts with 413 if exceeded"],
        ["ALLOWED_EXTENSIONS", "{jpg, jpeg, png, webp}", "—", "Checked in allowed_file() + re-validated in /settings avatar upload"],
    ],
    col_widths=[3.4*cm, 5.2*cm, 2.8*cm, 5.0*cm], header_color=NAVY, fontsize=6.7, header_fontsize=6.5
))

story.append(Paragraph("13.2 &nbsp; Local development (XAMPP / standalone MySQL)", S_H2))
for i, step in enumerate([
    "Start MySQL (XAMPP Control Panel → Start MySQL, or <b>net start MySQL</b>).",
    "Create a virtualenv and install deps: <b>pip install -r requirements.txt</b>.",
    "Configure <i>config.py</i> or set env vars for your MySQL credentials.",
    "Initialise the DB: <b>python init_db.py</b> — creates <i>findme_db</i>, runs <i>schema.sql</i> + <i>seed.sql</i>, creates upload subfolders.",
    "Run: <b>python app.py</b> → <b>http://localhost:5000</b>. Or double-click <b>run.bat</b> on Windows.",
    "Verify: <b>python verify_db.py</b> prints row counts per table.",
    "Reset demo data any time: <b>python reset_db.py</b>.",
], 1):
    story.append(Paragraph(f"<b>{i}.</b> &nbsp; {step}", S_BULLET))

story.append(Paragraph("13.3 &nbsp; PythonAnywhere deployment", S_H2))
story.append(p("The steps in <i>deploy.txt</i>, summarised:"))
for i, step in enumerate([
    "Sign up at pythonanywhere.com; open a Bash console.",
    "<b>git clone &lt;repo&gt; && cd findme && pip install --user virtualenv && virtualenv venv && source venv/bin/activate && pip install -r requirements.txt && mkdir -p static/uploads/{avatars,lost,found}</b>",
    "Databases tab → create MySQL DB <b>yourusername$findme_db</b> → open MySQL console → <b>SOURCE ~/findme/schema.sql</b>.",
    "Edit <i>config.py</i> (or set env vars) with your PythonAnywhere MySQL host/user/password and a strong SECRET_KEY.",
    "Web tab → Add web app (Manual, Python 3.10) → set <b>Source code / Working directory = ~/findme</b>, <b>WSGI file → ~/findme/wsgi.py</b>, <b>Virtualenv = ~/findme/venv</b>.",
    "Static files: <b>/static/ → ~/findme/static/</b> and <b>/uploads/ → ~/findme/static/uploads/</b>.",
    "Create the admin account in the MySQL console (INSERT with a bcrypt hash for password123 — see <i>deploy.txt:40</i>).",
    "Reload the web app → live at <b>yourusername.pythonanywhere.com</b>.",
], 1):
    story.append(Paragraph(f"<b>{i}.</b> &nbsp; {step}", S_BULLET))
story.append(note_box(
    "On PythonAnywhere free tier, background threads may be killed after the request returns. If matches are not appearing, "
    "call <i>rerun_all_matches(db)</i> from a console or replace the thread with a scheduled task that runs every few minutes.",
    title="PythonAnywhere caveat", bg=HexColor("#FFFBEB"), border=AMBER
))

story.append(Paragraph("13.4 &nbsp; Operations", S_H2))
story.append(styled_table(
    ["Task", "How"],
    [
        ["Health check", "Visit <b>/</b> (no DB needed) and <b>/dashboard</b> (DB + session). Run <b>verify_db.py</b> for row counts."],
        ["Backups", "MySQL dump: <b>mysqldump -u root findme_db > backup.sql</b>. Uploads: copy <b>static/uploads/</b>."],
        ["Recompute matches", "From a Flask shell: <b>from ai.matcher import rerun_all_matches; from app import app; … rerun_all_matches(db)</b> (deletes all matches first — see caution in §9.6)."],
        ["View audit trail", "<b>/admin/activity-logs</b> in the UI, or <b>SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 100</b> in MySQL."],
        ["Reset demo", "<b>POST /admin/reset</b> (admin only) or <b>python reset_db.py</b> locally."],
    ],
    col_widths=[3.4*cm, 13.0*cm]
))

# ═══════════════════════════════════════════════════════════════════════
# 14. LIMITATIONS & ROADMAP
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("14 &nbsp; Limitations, Risks &amp; Future Roadmap", S_H1))
story.append(hr())
story.append(Paragraph("14.1 &nbsp; Known limitations (as shipped)", S_H2))
for b in bullets([
    "<b>Image similarity is simulated</b> — <i>image_similarity_simulated()</i> compares filenames and keywords, not pixels. Two different phones with similar filenames can score 0.6. Replace with a real vision model (see §9.3).",
    "<b>No email delivery</b> — forgot-password and match notifications are in-app only. Flask-Mail is installed but not wired; <i>forgot_password()</i> always shows the same flash and returns.",
    "<b>No rate limiting</b> — login, registration, and report endpoints have no throttling. Add Flask-Limiter before public exposure.",
    "<b>No CSRF tokens</b> — POST forms rely on POST-only + UI confirmation. Add Flask-WTF CSRF for production.",
    "<b>Weight sum = 0.96</b> — maximum confidence is 96 %, not 100 % (see §9.2). Harmless but worth fixing to 1.00.",
    "<b>Single-file app</b> — <i>app.py</i> is ~1,750 lines with no blueprints. Fine for a capstone; consider splitting into blueprints for long-term maintenance.",
    "<b>No pagination on /my-reports and /matches</b> — capped at LIMIT 50/100 but not paginated; large histories will truncate.",
    "<b>Thread-based matching</b> — may be killed on PythonAnywhere free tier; no retry queue.",
    "<b>Demo credentials</b> — all seeded users share password123; must be changed or removed before production.",
]):
    story.append(b)

story.append(Paragraph("14.2 &nbsp; Recommended roadmap", S_H2))
story.append(styled_table(
    ["Priority", "Improvement", "Effort / Notes"],
    [
        ["P0 — Security", "Rate limiting (Flask-Limiter) + CSRF (Flask-WTF) + strong SECRET_KEY enforcement", "Low — config + decorator changes"],
        ["P0 — Correctness", "Fix weight sum to 1.00; add server-side validation for all enum transitions", "Low — one-line weight fix + validation helpers"],
        ["P1 — AI", "Real image embeddings (CLIP / ResNet cosine) replacing image_similarity_simulated", "Medium — new deps, keep the same 0.6/0.4 blend"],
        ["P1 — Comms", "Wire Flask-Mail for password reset + match/recovery emails; add email_verified flow", "Medium — SMTP config + token generation"],
        ["P1 — Reliability", "Replace daemon thread with a task queue (RQ/Celery) or a scheduled rerun cron", "Medium — infra change"],
        ["P2 — UX", "Pagination on /my-reports + /matches; advanced search filters; map-based location picker", "Low–Medium"],
        ["P2 — Ops", "REST API for a mobile app; Elasticsearch for full-text search; QR-code verification", "High — new subsystems"],
        ["P2 — Analytics", "Charts on /admin/reports (Chart.js already available via CDN pattern); export to CSV/PDF", "Low–Medium"],
    ],
    col_widths=[2.4*cm, 7.6*cm, 6.4*cm]
))

# ═══════════════════════════════════════════════════════════════════════
# APPENDIX A
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("Appendix A &nbsp; Demo Accounts &amp; Quick-Start Script", S_H1))
story.append(hr())
story.append(styled_table(
    ["Email", "Password", "Role", "Faculty / Course (seeded)"],
    [
        ["admin@cavendish.ac.ug", "password123", "Administrator", "—"],
        ["john.musinguzi@cavendish.ac.ug", "password123", "Student", "Science & Technology / BCS"],
        ["sarah.nakamya@cavendish.ac.ug", "password123", "Student", "Science & Technology / BIT"],
        ["peter.okello@cavendish.ac.ug", "password123", "Lecturer", "Science & Technology"],
        ["grace.tumusiime@cavendish.ac.ug", "password123", "Student", "Business & Management"],
    ],
    col_widths=[5.5*cm, 2.8*cm, 2.6*cm, 5.5*cm]
))
story.append(Paragraph("All demo passwords are bcrypt-hashed in the DB. Change them before any public deployment.", S_CAPTION))
story.append(Paragraph("Demo walkthrough (the script examiners will follow)", S_H2))
for i, step in enumerate([
    "Log in as <b>john.musinguzi@cavendish.ac.ug / password123</b>.",
    "Go to <b>Report Lost</b> → submit: <i>\"Black Samsung Galaxy A32, lost near Library, 2026-08-10\"</i> with a photo.",
    "Log in as <b>sarah.nakamya@cavendish.ac.ug / password123</b>.",
    "Go to <b>Report Found</b> → submit: <i>\"Black Samsung phone found near Library, 2026-08-11\"</i> with a similar photo.",
    "Both users receive a notification: <i>Potential Match Found — Confidence: ~85 %</i>.",
    "Log in as <b>admin@cavendish.ac.ug / password123</b> → <b>Match Review</b> → see the pending 85 % card side-by-side.",
    "Click <b>Approve</b> → both users get <i>Match Approved</i> notifications; the match appears as approved in <b>/matches</b>.",
    "Create a recovery (if the flow requires it) → admin marks <b>Completed</b> → both items become <b>recovered</b>.",
], 1):
    story.append(Paragraph(f"<b>{i}.</b> &nbsp; {step}", S_BULLET))

# ═══════════════════════════════════════════════════════════════════════
# APPENDIX B
# ═══════════════════════════════════════════════════════════════════════
story.append(Paragraph("Appendix B &nbsp; Status &amp; Enum Reference", S_H1))
story.append(hr())
story.append(styled_table(
    ["Enum", "Values (as stored in MySQL)"],
    [
        ["lost_items.status / found_items.status", "reported, under_review, potential_match, match_pending_approval, match_approved, match_rejected, owner_verification_pending, owner_verified, recovered, closed, archived"],
        ["matches.status", "pending, approved, rejected, uncertain"],
        ["matches.match_level", "very_high (≥90), high (≥75), possible (≥50), low (<50)"],
        ["notifications.type", "info, warning, success, match, recovery"],
        ["verification_requests.status", "pending, approved, rejected"],
        ["recoveries.status", "pending, completed, cancelled"],
        ["item_images.item_type", "lost, found"],
        ["users.is_active / email_verified", "TRUE / FALSE (BOOLEAN)"],
        ["categories / locations / faculties / courses .is_active", "TRUE / FALSE"],
    ],
    col_widths=[5.0*cm, 11.4*cm]
))
story.append(Paragraph("All enums are enforced by MySQL; the app validates them again before writing (ITEM_STATUSES in <i>app.py:1644</i>).", S_CAPTION))
story.append(Spacer(1, 0.4*cm))
story.append(kv_table([
    ["Reference format", "<b>FM-YYYY-NNNNN</b> — e.g. FM-2026-00042. Prefix FM, year, zero-padded sequence per table (MAX(id)+1). Generated by <i>generate_reference('FM', 'lost'|'found')</i>."],
    ["Image extensions", "<b>jpg, jpeg, png, webp</b> — checked in <i>allowed_file()</i>; re-validated for avatars."],
    ["Upload limits", "Global <b>16 MB</b> (MAX_CONTENT_LENGTH → 413); avatar <b>5 MB</b> (explicit check in /settings)."],
    ["Pagination defaults", "<b>20</b> rows (paginated_query), <b>50</b> for activity logs."],
    ["Matcher scan cap", "<b>200</b> opposite-type rows per report, ordered by created_at DESC."],
    ["Matcher storage threshold", "<b>≥ 30 %</b> confidence — below this, no matches row is created."],
]))
story.append(Spacer(1, 0.6*cm))
story.append(HRFlowable(width="100%", thickness=0.6, color=SLATE_300, spaceAfter=6, spaceBefore=4))
story.append(Paragraph(
    "<b>End of document.</b> &nbsp; This PDF was generated from the live codebase on "
    f"{datetime.now():%d %B %Y}. &nbsp; For the latest code, see the repository root. &nbsp; "
    "Questions? Contact the FindMe development team at Cavendish University Uganda.",
    ParagraphStyle("end", parent=S_SMALL, fontSize=7, leading=9, textColor=SLATE_500, alignment=TA_CENTER)
))
story.append(Spacer(1, 0.15*cm))
story.append(Paragraph(
    "FindMe — Cavendish University Uganda  ·  AI-Powered Lost &amp; Found Management System  ·  Complete System Documentation  ·  v1.0",
    ParagraphStyle("end2", parent=S_SMALL, fontSize=6.5, leading=8, textColor=SLATE_500, alignment=TA_CENTER)
))

# ── Build ─────────────────────────────────────────────────────────────
doc.build(story, onFirstPage=_cover_footer, onLaterPages=_header_footer)
print(f"Wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
