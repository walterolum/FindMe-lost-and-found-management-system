"""Match report PDF generator (fpdf2).

Produces a clean one-page A4 "Item Match Report" for a lost/found match.
Text is sanitized to latin-1 (the size of the built-in core fonts) so any
user input - including names with non-latin characters - can never crash
the renderer. The PDF is generated in memory; nothing is written to disk.
"""
from fpdf import FPDF

BRAND = 'FindMe'
SUBBRAND = 'Cavendish University Uganda'

ACCENT = (30, 58, 138)       # deep blue
ACCENT_LIGHT = (219, 231, 249)
GREEN = (22, 101, 52)
GREY = (90, 96, 102)
DARK = (34, 38, 42)
LINE = (224, 228, 233)


def _latin(text):
    """Make arbitrary text safe for core fonts."""
    if text is None:
        return ''
    return str(text).encode('latin-1', 'replace').decode('latin-1')


class _MatchPDF(FPDF):
    def header(self):
        # Brand band
        self.set_fill_color(*ACCENT)
        self.set_text_color(255, 255, 255)
        self.rect(10, 10, 190, 22, style='F')
        self.set_font('helvetica', 'B', 18)
        self.set_xy(14, 14)
        self.cell(0, 9, f'{BRAND} - Item Match Report')
        self.set_font('helvetica', '', 9.5)
        self.set_xy(14, 23)
        self.cell(0, 6, SUBBRAND + ' | Lost & Found Management System')
        self.set_y(36)

    def footer(self):
        self.set_y(-16)
        self.set_text_color(*GREY)
        self.set_font('helvetica', '', 8)
        self.cell(0, 8, f'Generated {self._generated} - page {self.page_no()}/{{nb}}', align='C')


def _section_title(pdf, text):
    pdf.ln(3)
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(*ACCENT)
    pdf.set_x(24)
    pdf.cell(0, 8, text)
    pdf.ln(8)


def build_match_report_pdf(data):
    """Render the match PDF and return the bytes.

    Expects a dict (see app._load_match_pdf_data):
        match_id, score, confidence, status, explanation, matched_at,
        lost_{name,ref,category,brand,model,color,shape,serial,marks,value,
                desc,date,time,location,location_detail,detected},
        found_{...same...},
        owner_{name,email,phone}, finder_{name,email,phone}
    """
    pdf = _MatchPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    d = data
    pdf._generated = ''  # set lazily (class has no __init__ override)
    pdf.add_page()
    pdf._generated = _latin(d.get('generated', ''))

    # ---- Status banner --------------------------------------------------
    pdf.set_fill_color(*GREEN)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('helvetica', 'B', 13)
    pdf.set_x(10)
    pdf.cell(190, 10, 'MATCH FOUND - YOUR ITEM MAY HAVE BEEN LOCATED', border=0, fill=True, align='C', ln=1)
    pdf.ln(2)

    # ---- Match meta (key/value strip) -----------------------------------
    pdf.set_text_color(*DARK)
    pdf.set_font('helvetica', '', 9.5)
    pdf.set_draw_color(*LINE)
    col_w = 95.0
    meta = [
        ('Match Reference', f'FM-MATCH-{int(d["match_id"]):05d}'),
        ('Match Confidence', f'{d.get("score", 0)}% ({d.get("confidence", "")})'),
        ('Match Status', str(d.get('status', '')).upper()),
        ('Matched On', str(d.get('matched_at', ''))),
    ]
    y = pdf.get_y()
    for i, (k, v) in enumerate(meta):
        x = 10 if i % 2 == 0 else 105
        pdf.set_xy(x, y + (i // 2) * 12)
        pdf.set_font('helvetica', 'B', 8.5)
        pdf.set_text_color(*GREY)
        pdf.cell(col_w, 5, k.upper())
        pdf.set_xy(x, y + (i // 2) * 12 + 5)
        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(*DARK)
        pdf.cell(col_w, 7, _latin(v))
    pdf.set_y(y + 26)

    # ---- Lost + Found item tables ---------------------------------------
    def item_block(title, prefix, color):
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_text_color(*color)
        pdf.set_x(10)
        pdf.cell(0, 8, title, ln=1)
        pdf.set_draw_color(*LINE)
        rows = [
            ('Reference', d.get(f'{prefix}ref')),
            ('Item Name', d.get(f'{prefix}name')),
            ('Category', d.get(f'{prefix}category')),
            ('Brand / Model', ' '.join(x for x in (d.get(f'{prefix}brand'), d.get(f'{prefix}model')) if x)),
            ('Colour', d.get(f'{prefix}color')),
            ('Shape', d.get(f'{prefix}shape')),
            ('Serial Number', d.get(f'{prefix}serial')),
            ('Unique Marks', d.get(f'{prefix}marks')),
            ('Approx. Value (UGX)', d.get(f'{prefix}value')),
            ('Date / Time', ' '.join(str(x) for x in (d.get(f'{prefix}date'), d.get(f'{prefix}time')) if x)),
            ('Reported Location', d.get(f'{prefix}location')),
            ('Location Detail', d.get(f'{prefix}location_detail')),
            ('GPS Detected Location', d.get(f'{prefix}detected')),
        ]
        for i, (k, v) in enumerate(rows):
            v = v or ''
            if not v:
                continue
            shaded = i % 2 == 0
            pdf.set_fill_color(*ACCENT_LIGHT)
            pdf.set_draw_color(*LINE)
            x0 = pdf.get_x()
            y0 = pdf.get_y()
            pdf.set_font('helvetica', 'B', 8.8)
            pdf.set_text_color(*GREY)
            pdf.multi_cell(45, 7, k, border='D', fill=shaded)
            pdf.set_xy(x0 + 45, y0)
            pdf.set_font('helvetica', '', 9.5)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(145, 7, _latin(v), border='D', fill=shaded, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

    item_block('LOST ITEM DETAILS (OWNER REPORT)', 'lost_', ACCENT)
    item_block('FOUND ITEM DETAILS', 'found_', GREEN)

    # ---- People ----------------------------------------------------------
    _section_title(pdf, 'CONTACTS')
    pdf.set_draw_color(*LINE)
    people = [
        ('Owner / Reporter', 'owner'),
        ('Finder / Reporter', 'finder'),
    ]
    for title, pfx in people:
        name = d.get(f'{pfx}name') or 'N/A'
        email = d.get(f'{pfx}email')
        phone = d.get(f'{pfx}phone')
        line = f'{name}' + (f'   |   {email}' if email else '') + (f'   |   {phone}' if phone else '')
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_text_color(*GREY)
        pdf.cell(42, 7, title)
        pdf.set_font('helvetica', '', 9.5)
        pdf.set_text_color(*DARK)
        pdf.cell(0, 7, _latin(line), new_x='LMARGIN', new_y='NEXT')

    # ---- Owner instructions ---------------------------------------------
    pdf.ln(4)
    pdf.set_fill_color(252, 248, 227)
    pdf.set_draw_color(245, 214, 125)
    pdf.set_text_color(122, 88, 8)
    pdf.set_font('helvetica', '', 9)
    steps = (
        '1. Confirm the details above are yours (serial number, unique marks, colour).'
        '\n2. Contact the university lost & found office with this document and a student/staff ID.'
        '\n3. Present this report when picking up your item - it is required for release.'
    )
    pdf.multi_cell(190, 6, 'NEXT STEPS FOR THE OWNER\n\n' + _latin(steps), border=1, fill=True)

    # ---- AI analysis ------------------------------------------------------
    explanation = (d.get('explanation') or '').strip()
    if explanation:
        if pdf.get_y() > 180:
            pdf.add_page()
        _section_title(pdf, 'AI MATCH REASONING')
        pdf.set_font('helvetica', '', 8.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(190, 4.5, _latin(explanation[:1800]))
    else:
        _section_title(pdf, 'AI MATCH REASONING')
        pdf.set_font('helvetica', '', 8.5)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 5, 'Detailed reasoning included by the AI matching engine.')

    return bytes(pdf.output())
