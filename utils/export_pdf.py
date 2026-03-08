"""
PDF (A4) Dışa Aktarma Modülü
reportlab kullanır — profesyonel A4 rapor
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from utils.hesapla import HesaplaSonucu, format_tl

# ── Renk sabitleri ────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1A2744")
GOLD   = colors.HexColor("#C49A2B")
LGRAY  = colors.HexColor("#F5F1EB")
DGRAY  = colors.HexColor("#6B7280")
GREEN  = colors.HexColor("#27AE60")
RED    = colors.HexColor("#C0392B")
AMBER  = colors.HexColor("#FFF8E1")
LGREEN = colors.HexColor("#E8F5E9")
WHITE  = colors.white
BLACK  = colors.black

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _style(name, **kwargs) -> ParagraphStyle:
    base = {
        "fontName": "Helvetica",
        "fontSize": 10,
        "leading": 14,
        "textColor": BLACK,
    }
    base.update(kwargs)
    return ParagraphStyle(name, **base)


STYLE_TITLE   = _style("title",  fontSize=16, fontName="Helvetica-Bold", textColor=WHITE,  alignment=TA_CENTER, leading=20)
STYLE_SUB     = _style("sub",    fontSize=8,  textColor=colors.HexColor("#A0AEC0"), alignment=TA_CENTER)
STYLE_SEC     = _style("sec",    fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE,  alignment=TA_LEFT)
STYLE_LABEL   = _style("lbl",    fontSize=9,  textColor=DGRAY,   alignment=TA_LEFT)
STYLE_VALUE   = _style("val",    fontSize=9,  textColor=NAVY,    alignment=TA_RIGHT)
STYLE_TOTAL_L = _style("totL",   fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_LEFT)
STYLE_TOTAL_V = _style("totV",   fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT)
STYLE_GREEN   = _style("grn",    fontSize=9,  fontName="Helvetica-Bold", textColor=GREEN, alignment=TA_RIGHT)
STYLE_WARN    = _style("warn",   fontSize=8,  textColor=DGRAY,   alignment=TA_LEFT,  leading=12)
STYLE_LEGAL   = _style("legal",  fontSize=8,  textColor=RED,     alignment=TA_LEFT)


def _num(val: float) -> str:
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sec_table(title: str) -> Table:
    t = Table([[Paragraph(title, STYLE_SEC)]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    return t


def _data_table(rows: list, col_widths=None) -> Table:
    """
    rows: list of (label_str, value_str, is_total, is_green)
    """
    CW = PAGE_W - 2 * MARGIN
    if col_widths is None:
        col_widths = [CW * 0.65, CW * 0.35]

    table_data = []
    styles = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5DDC8")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ]

    for ri, (lbl, val, is_total, is_green) in enumerate(rows):
        bg = NAVY if is_total else (LGRAY if ri % 2 == 0 else WHITE)
        styles.append(("BACKGROUND", (0, ri), (-1, ri), bg))

        if is_total:
            l_style = STYLE_TOTAL_L
            v_style = STYLE_TOTAL_V
        elif is_green:
            l_style = STYLE_LABEL
            v_style = STYLE_GREEN
        else:
            l_style = STYLE_LABEL
            v_style = STYLE_VALUE

        table_data.append([Paragraph(lbl, l_style), Paragraph(val, v_style)])

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle(styles))
    return t


def _tarife_table(params: dict, sonuc: HesaplaSonucu) -> Table:
    CW = PAGE_W - 2 * MARGIN
    cw = [CW * 0.25, CW * 0.25, CW * 0.15, CW * 0.35]

    hdr_style = _style("th", fontSize=8, fontName="Helvetica-Bold",
                        textColor=WHITE, alignment=TA_CENTER)
    hdr = ["Alt Sinir (TL)", "Ust Sinir (TL)", "Oran", "Taban Vergi (TL)"]

    data = [[Paragraph(h, hdr_style) for h in hdr]]
    table_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5DDC8")),
    ]

    for ri, d in enumerate(params["tarife_ucret_disi"], 1):
        bg = LGRAY if ri % 2 == 0 else WHITE
        table_styles.append(("BACKGROUND", (0, ri), (-1, ri), bg))
        cell_style = _style(f"tc{ri}", fontSize=8, alignment=TA_RIGHT,
                            textColor=NAVY)
        ust = _num(d["ust_sinir"]) if d["ust_sinir"] else "Sinirsiz"
        data.append([
            Paragraph(_num(d["alt_sinir"]), cell_style),
            Paragraph(ust,                 cell_style),
            Paragraph(f"%{int(d['oran']*100)}", cell_style),
            Paragraph(_num(d["taban"]),    cell_style),
        ])

    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle(table_styles))
    return t


# ── Sayfa numarası canvas callback ───────────────────────────────────────

class _PageNumCanvas:
    def __init__(self, year: int):
        self.year = year

    def __call__(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, 10 * mm, fill=True, stroke=False)
        canvas.setFillColor(DGRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(
            MARGIN,
            4 * mm,
            f"Bilgilendirme amaclidir | YMM'ye danisiniz | GIB: gib.gov.tr | {self.year}"
        )
        canvas.drawRightString(
            PAGE_W - MARGIN,
            4 * mm,
            f"Sayfa {doc.page}"
        )
        canvas.restoreState()


# ── Ana export fonksiyonu ─────────────────────────────────────────────────

def export_pdf(
    sonuc: HesaplaSonucu,
    year: int,
    gider_yontemi: str,
    params: dict,
) -> bytes:
    """
    Hesaplama sonuçlarını PDF formatına dönüştürür.
    Returns: bytes — doğrudan HTTP response olarak gönderilebilir.
    """
    buf  = io.BytesIO()
    doc  = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=16 * mm,
    )

    story = []
    CW = PAGE_W - 2 * MARGIN

    # ── Üst bant ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"GMSi VERGI HESAPLAMA OZETI - {year}", STYLE_TITLE),
    ]]
    header_tbl = Table(header_data, colWidths=[CW])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header_tbl)

    sub_data = [[Paragraph(
        f"Beyan Yili: {year}  |  "
        f"Hesaplama: {datetime.now().strftime('%d.%m.%Y')}  |  "
        "Bilgilendirme amaclidir",
        STYLE_SUB
    )]]
    sub_tbl = Table(sub_data, colWidths=[CW])
    sub_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── GMSİ Gelirleri ─────────────────────────────────────────────────────
    story.append(_sec_table("GMSi (KIRA GELIRI) HESABI"))
    story.append(_data_table([
        ("Konut Brut Kira Geliri",           f"{_num(sonuc.konut_brut)} TL",    False, False),
        ("Isyeri Kira Geliri (Stopajli)",     f"{_num(sonuc.isyeri_s_brut)} TL", False, False),
        ("Isyeri Kira Geliri (Stopajsiz)",    f"{_num(sonuc.isyeri_n_brut)} TL", False, False),
        (f"Mesken Istisnasi ({year})",
         f"- {_num(sonuc.istisna)} TL" if sonuc.istisna else "Uygulanmadi",
         False, sonuc.istisna > 0),
        ("Beyana Tabi GMSi Toplami",          f"{_num(sonuc.toplam_gmsi_beyan)} TL", False, False),
        (f"Gider ({'Goturu %' + str(int(params['goturu_oran']*100)) if gider_yontemi=='goturu' else 'Gercek Gider'})"
         f"{sonuc.iktisap_acik}",
         f"- {_num(sonuc.gmsi_gider)} TL",   False, True),
        ("GMSi VERGI MATRAHI",                f"{_num(sonuc.gmsi_matrah)} TL",  True,  False),
    ]))
    story.append(Spacer(1, 4 * mm))

    # ── Ücret ──────────────────────────────────────────────────────────────
    if sonuc.toplam_brut_ucret > 0:
        story.append(_sec_table("UCRET GELIRI"))
        story.append(_data_table([
            ("Toplam Brut Ucret (12 ay)",          f"{_num(sonuc.toplam_brut_ucret)} TL",   False, False),
            ("Kesilen Ucret Stopaji",               f"{_num(sonuc.toplam_ucret_stopaj)} TL", False, False),
            ("BEYANA DAHIL UCRET MATRAHI",          f"{_num(sonuc.ucret_matrah)} TL",        True,  False),
        ]))
        story.append(Spacer(1, 4 * mm))

    # ── Toplam Vergi ────────────────────────────────────────────────────────
    story.append(_sec_table("TOPLAM VERGI HESABI"))
    vergi_rows = [
        ("Toplam Vergi Matrahi",              f"{_num(sonuc.toplam_matrah)} TL",  False, False),
        ("Hesaplanan Gelir Vergisi",          f"{_num(sonuc.hes_ver)} TL",        False, False),
        ("Mahsup Edilen Stopaj",         f"- {_num(sonuc.mahsup)} TL",            False, True),
        ("ODENECEK GELIR VERGISI",            f"{_num(sonuc.odeme)} TL",          True,  False),
    ]
    if sonuc.iade > 0:
        vergi_rows.append(("IADE EDILECEK VERGI", f"{_num(sonuc.iade)} TL", False, True))
    vergi_rows.append(("Damga Vergisi (yaklasik)", f"{_num(sonuc.damga)} TL", False, False))
    story.append(_data_table(vergi_rows))
    story.append(Spacer(1, 4 * mm))

    # ── Taksit planı ────────────────────────────────────────────────────────
    story.append(_sec_table("TAKSIT PLANI"))
    taksit_style = TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), AMBER),
        ("BACKGROUND", (1, 0), (1, -1), LGREEN),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("LINEAFTER", (0, 0), (0, -1), 1, WHITE),
    ])
    t1_style = _style("t1lbl", fontSize=9, fontName="Helvetica-Bold", textColor=NAVY)
    t1_sub   = _style("t1sub", fontSize=8, textColor=GOLD)
    t2_style = _style("t2lbl", fontSize=9, fontName="Helvetica-Bold", textColor=NAVY)
    t2_sub   = _style("t2sub", fontSize=8, textColor=GREEN)

    taksit_tbl = Table(
        [[
            Paragraph(
                f"1. Taksit + Damga<br/>"
                f"<font size=8 color='#C49A2B'>31 Mart {year+1}</font><br/>"
                f"<b>{_num(sonuc.taksit1 + sonuc.damga)} TL</b>",
                _style("tx1", fontSize=10, textColor=NAVY, alignment=TA_LEFT, leading=14)
            ),
            Paragraph(
                f"2. Taksit<br/>"
                f"<font size=8 color='#27AE60'>31 Temmuz {year+1}</font><br/>"
                f"<b>{_num(sonuc.taksit2)} TL</b>",
                _style("tx2", fontSize=10, textColor=NAVY, alignment=TA_LEFT, leading=14)
            ),
        ]],
        colWidths=[CW / 2, CW / 2]
    )
    taksit_tbl.setStyle(taksit_style)
    story.append(taksit_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── GVK Tarifesi ────────────────────────────────────────────────────────
    story.append(_sec_table(f"GVK TARIFESI (UCRET DISI) - {year}"))
    story.append(_tarife_table(params, sonuc))
    story.append(Spacer(1, 4 * mm))

    # ── Uyarılar ────────────────────────────────────────────────────────────
    if sonuc.warns:
        story.append(_sec_table("UYARILAR VE BILGILENDIRMELER"))
        for w in sonuc.warns:
            clean = w.replace("⚠️", "[!]").replace("💚", "[+]").replace("ℹ️", "[i]")
            story.append(Paragraph(clean, STYLE_WARN))
            story.append(Spacer(1, 2 * mm))
        story.append(Spacer(1, 2 * mm))

    # ── Yasal uyarı ─────────────────────────────────────────────────────────
    legal = Table(
        [[Paragraph(
            "[!] Bu hesaplama bilgilendirme amaclidir. "
            "Kesin vergi yukumlulugu icin YMM/SMMM'ye danisiniz. "
            f"Parametre kaynagi: GIB — gib.gov.tr | {datetime.now().strftime('%d.%m.%Y')}",
            STYLE_LEGAL
        )]],
        colWidths=[CW]
    )
    legal.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AMBER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(legal)

    # ── Build ───────────────────────────────────────────────────────────────
    doc.build(story, onLaterPages=_PageNumCanvas(year), onFirstPage=_PageNumCanvas(year))
    buf.seek(0)
    return buf.read()
