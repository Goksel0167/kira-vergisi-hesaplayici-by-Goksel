"""
GMSİ Vergi Hesaplayıcı — Streamlit Web Uygulaması
Streamlit Cloud'da çalıştır → https://share.streamlit.io
"""

import streamlit as st

from params import PARAMS
from utils.hesapla import (
    gmsi_hesapla, HesaplamaGirdisi,
    Mulk, Isveren, GercekGider, DigerGelirler, format_tl,
)
from utils.export_excel import export_excel
from utils.export_pdf import export_pdf

# ── Sayfa yapılandırması ──────────────────────────────────────────────────
st.set_page_config(
    page_title="GMSİ Vergi Hesaplayıcı",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Küçük stil ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state başlangıcı ──────────────────────────────────────────────
if "n_mulk" not in st.session_state:
    st.session_state.n_mulk = 1
if "n_isveren" not in st.session_state:
    st.session_state.n_isveren = 1


# ── Yardımcı ─────────────────────────────────────────────────────────────
def _fmt(val: float) -> str:
    """Türk lirası formatı: 1.234,56 TL"""
    return f"₺{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖ GMSİ Hesaplayıcı")
    st.caption("Gayrimenkul Sermaye İradı · Kira Vergisi")
    st.divider()

    st.subheader("📅 Beyan Yılı")
    year = st.selectbox(
        "Yıl seçin",
        sorted(PARAMS.keys(), reverse=True),
        label_visibility="collapsed",
    )
    params = PARAMS[year]

    st.divider()
    st.subheader("📊 Gider Yöntemi")
    gider_yontemi = st.radio(
        "Gider yöntemi",
        ["goturu", "gercek"],
        format_func=lambda x: f"📊 Götürü (%{params['goturu_oran']*100:.0f})" if x == "goturu"
                              else "🧾 Gerçek Gider (Belgeli)",
        help="Seçiminiz 2 yıl değiştirilemez (GVK Md. 74)",
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader(f"💡 {year} Parametreleri")
    col_a, col_b = st.columns(2)
    col_a.metric("Mesken İstisnası", _fmt(params["mesken_istisna"]))
    col_b.metric("İşyeri Eşiği",     _fmt(params["isyeri_beyan_esigi_stopajli"]))
    col_a.metric("Ücret Eşiği",      _fmt(params["ucret_beyan_esigi"]))
    col_b.metric("Damga Vergisi",     _fmt(params["damga_vergisi"]))

    st.divider()
    st.caption(
        "⚠️ Bu araç **bilgilendirme amaçlıdır**. "
        "Kesin yükümlülük için YMM'ye danışınız."
    )

# ─────────────────────────────────────────────────────────────────────────
# BAŞLIK
# ─────────────────────────────────────────────────────────────────────────
st.title("🏠 GMSİ Vergi Hesaplayıcı")
st.caption(f"GİB {year} Parametreleri · GVK Md. 21, 70, 74, 86, 94 · Mart 2026")
st.divider()

# ─────────────────────────────────────────────────────────────────────────
# SEKMELER
# ─────────────────────────────────────────────────────────────────────────
tab_mulk, tab_gider, tab_ucret, tab_sonuc = st.tabs([
    "🏠 Mülkler",
    "💸 Giderler",
    "👔 Ücret & Diğer",
    "📊 Hesapla & Sonuçlar",
])

# ═════════════════════════════════════════════════════════════════════════
# TAB 1 — MÜLKLER
# ═════════════════════════════════════════════════════════════════════════
with tab_mulk:
    st.subheader("🏠 Mülk ve Kira Bilgileri")
    st.info(
        "💡 **Tahsil esasına göre** yıl içinde tahsil ettiğiniz "
        "brüt kira gelirlerini giriniz."
    )
    st.warning(
        "🏦 **Tevsik Zorunluluğu:** 500 TL üzerindeki tahsilatlar "
        "banka veya PTT üzerinden yapılmalıdır."
    )

    col_ekle, col_sil = st.columns(2)
    with col_ekle:
        if st.button("➕ Mülk Ekle", use_container_width=True):
            st.session_state.n_mulk += 1
            st.rerun()
    with col_sil:
        if st.button(
            "➖ Mülk Sil",
            use_container_width=True,
            disabled=st.session_state.n_mulk <= 1,
        ):
            st.session_state.n_mulk -= 1
            st.rerun()

    st.divider()

    TUR_ETIKET = {
        "konut":             "🏠 Konut",
        "isyeri_stopajli":   "🏢 İşyeri (Stopajlı — %20 stopaj kesildi)",
        "isyeri_stopajsiz":  "🏪 İşyeri (Stopajsız)",
    }

    for i in range(st.session_state.n_mulk):
        with st.expander(f"🏠 Mülk {i + 1}", expanded=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                tur = st.selectbox(
                    "Mülk Türü",
                    list(TUR_ETIKET.keys()),
                    format_func=lambda x: TUR_ETIKET[x],
                    key=f"tur_{i}",
                )
            with c2:
                hisse = st.number_input(
                    "Hisse %", min_value=1, max_value=100, value=100, key=f"hisse_{i}"
                )
            with c3:
                ay = st.number_input(
                    "Kira Ayı", min_value=1, max_value=12, value=12, key=f"ay_{i}"
                )

            c4, c5 = st.columns(2)
            with c4:
                st.number_input(
                    "Yıllık Kira Geliri (TL)",
                    min_value=0.0, value=0.0, step=1000.0, format="%.2f",
                    key=f"gelir_{i}",
                )
            with c5:
                st.number_input(
                    "Kesilen Stopaj (TL)",
                    min_value=0.0, value=0.0, step=100.0, format="%.2f",
                    key=f"stopaj_{i}",
                )

            if gider_yontemi == "gercek" and tur == "konut":
                st.number_input(
                    "İktisap Bedeli / Alış Fiyatı (TL) — %5 oran uygulanır",
                    min_value=0.0, value=0.0, step=10_000.0, format="%.2f",
                    key=f"iktisap_{i}",
                    help="Alış bedelinin %5'i gider olarak indirilebilir; "
                         "ancak o konutun yıllık kira hasılatını aşamaz.",
                )

# ═════════════════════════════════════════════════════════════════════════
# TAB 2 — GİDERLER
# ═════════════════════════════════════════════════════════════════════════
with tab_gider:
    st.subheader("💸 Gider Detayı")

    if gider_yontemi == "goturu":
        st.success(
            f"✅ **Götürü Gider** seçildiniz.\n\n"
            f"Beyana tabi kira gelirinin **%{params['goturu_oran']*100:.0f}'i** "
            "otomatik olarak gider sayılır — belge gerekmez. "
            "Bu sekmede yapılacak işlem yok."
        )
    else:
        st.info("🧾 **Gerçek Gider** — GVK Md. 74 kapsamındaki belgeli giderleri giriniz.")
        st.warning(
            f"⚠️ **{year} / {year+1}:** Konut için kredi / ipotek faizi "
            "gider olarak **indirilemez** (7566 sayılı Kanun)."
        )
        st.info(
            "📌 **İktisap %5 kuralı:** Alış bedelinin %5'i gider olarak "
            "indirilebilir — ancak o konutun yıllık kira hasılatını **aşamaz** "
            "(GMSİ'de zarar oluşturulamaz)."
        )

        c1, c2 = st.columns(2)
        with c1:
            st.number_input(
                "Aidat, Aydınlatma, Isıtma, Su (TL)",
                min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_aidat",
            )
            st.number_input(
                "Sigorta Giderleri (TL)",
                min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_sigorta",
            )
            st.number_input(
                "Vergi, Harç, Şerefiyeler (TL)",
                min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_vergiler",
            )
        with c2:
            st.number_input(
                "Amortisman (TL) — tipik %2/yıl",
                min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_amortisman",
            )
            st.number_input(
                "Diğer GVK Md. 74 Giderleri (TL)",
                min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_diger",
            )

        st.divider()
        st.markdown(f"**⛔ Konut Kredi Faizi — {year}'de İndirilemez**")
        st.number_input(
            "Kredi Faizi (TL) — bilgi amaçlı girebilirsiniz, hesaba dahil edilmez",
            min_value=0.0, value=0.0, step=100.0, format="%.2f", key="g_kredi",
            help=f"{year} itibariyle konut için kredi faizi gider olarak indirilemez.",
        )

# ═════════════════════════════════════════════════════════════════════════
# TAB 3 — ÜCRET & DİĞER
# ═════════════════════════════════════════════════════════════════════════
with tab_ucret:
    st.subheader("👔 Ücret Geliri")

    ucret_var = st.toggle("Ücret gelirim var", value=False, key="ucret_var")

    if ucret_var:
        st.info(
            f"ℹ️ 2. ve sonraki işverenden alınan ücret toplamı "
            f"**{_fmt(params['ucret_beyan_esigi'])}** eşiğini aşarsa "
            "tüm ücretler beyana dahil edilmek zorundadır (GVK Md. 86/1-b)."
        )

        col_e, col_s = st.columns(2)
        with col_e:
            if st.button("➕ İşveren Ekle", use_container_width=True):
                st.session_state.n_isveren += 1
                st.rerun()
        with col_s:
            if st.button(
                "➖ İşveren Sil",
                use_container_width=True,
                disabled=st.session_state.n_isveren <= 1,
            ):
                st.session_state.n_isveren -= 1
                st.rerun()

        st.divider()

        for i in range(st.session_state.n_isveren):
            with st.expander(f"👔 İşveren {i + 1}", expanded=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.text_input(
                        "İşveren Adı",
                        placeholder=f"İşveren {i + 1}",
                        key=f"iv_ad_{i}",
                    )
                with c2:
                    st.checkbox(
                        "1. İşveren (en yüksek ücret)",
                        value=(i == 0),
                        key=f"birinci_{i}",
                    )
                c3, c4 = st.columns(2)
                with c3:
                    st.number_input(
                        "Yıllık Brüt Ücret (TL)",
                        min_value=0.0, value=0.0, step=1000.0, format="%.2f",
                        key=f"iv_brut_{i}",
                    )
                with c4:
                    st.number_input(
                        "Yıllık Stopaj (TL)",
                        min_value=0.0, value=0.0, step=1000.0, format="%.2f",
                        key=f"iv_stopaj_{i}",
                    )

    st.divider()
    st.subheader("🏦 Diğer Gelirler")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "Menkul Sermaye İradı (TL)",
            min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="d_msi",
        )
    with c2:
        st.number_input(
            "Diğer Kazanç ve İratlar (TL)",
            min_value=0.0, value=0.0, step=1000.0, format="%.2f", key="d_dki",
        )
    st.checkbox(
        "Ticari / Zirai / Mesleki kazancım var "
        "→ Mesken istisnasından yararlanamam",
        value=False,
        key="faaliyet",
    )

# ═════════════════════════════════════════════════════════════════════════
# TAB 4 — HESAPLA & SONUÇLAR
# ═════════════════════════════════════════════════════════════════════════
with tab_sonuc:
    st.subheader("📊 Vergi Hesaplaması")
    st.caption(
        "Tüm sekmelerdeki verileri girdikten sonra butona tıklayın."
    )

    if st.button("🚀 Hesapla", type="primary", use_container_width=True):

        # ── Mülkleri topla ─────────────────────────────────────────────
        mulkler = []
        for i in range(st.session_state.n_mulk):
            tur    = st.session_state.get(f"tur_{i}",    "konut")
            gelir  = float(st.session_state.get(f"gelir_{i}",  0) or 0)
            stopaj = float(st.session_state.get(f"stopaj_{i}", 0) or 0)
            hisse  = float(st.session_state.get(f"hisse_{i}",  100) or 100)
            ay     = int(st.session_state.get(f"ay_{i}", 12) or 12)
            iktisap = 0.0
            if gider_yontemi == "gercek" and tur == "konut":
                iktisap = float(st.session_state.get(f"iktisap_{i}", 0) or 0)
            mulkler.append(
                Mulk(
                    tur=tur, gelir=gelir, stopaj=stopaj,
                    hisse=hisse, ay=ay, iktisap_bedeli=iktisap,
                )
            )

        # ── Gerçek gider ───────────────────────────────────────────────
        if gider_yontemi == "gercek":
            gercek = GercekGider(
                aidat      = float(st.session_state.get("g_aidat",     0) or 0),
                sigorta    = float(st.session_state.get("g_sigorta",   0) or 0),
                vergiler   = float(st.session_state.get("g_vergiler",  0) or 0),
                amortisman = float(st.session_state.get("g_amortisman",0) or 0),
                diger      = float(st.session_state.get("g_diger",     0) or 0),
                kredi_faiz = float(st.session_state.get("g_kredi",     0) or 0),
            )
        else:
            gercek = GercekGider()

        # ── İşverenler ─────────────────────────────────────────────────
        _ucret_var = bool(st.session_state.get("ucret_var", False))
        isverenler = []
        if _ucret_var:
            for i in range(st.session_state.n_isveren):
                brut = float(st.session_state.get(f"iv_brut_{i}", 0) or 0)
                isverenler.append(
                    Isveren(
                        ad          = st.session_state.get(f"iv_ad_{i}", f"İşveren {i+1}") or f"İşveren {i+1}",
                        brut_yillik = brut,
                        stopaj      = float(st.session_state.get(f"iv_stopaj_{i}", 0) or 0),
                        birinci     = bool(st.session_state.get(f"birinci_{i}", i == 0)),
                    )
                )

        # ── Diğer gelirler ─────────────────────────────────────────────
        diger = DigerGelirler(
            msi      = float(st.session_state.get("d_msi",   0) or 0),
            dki      = float(st.session_state.get("d_dki",   0) or 0),
            faaliyet = bool(st.session_state.get("faaliyet", False)),
        )

        girdi = HesaplamaGirdisi(
            year           = year,
            mulkler        = mulkler,
            gider_yontemi  = gider_yontemi,
            gercek_gider   = gercek,
            ucret_var      = _ucret_var,
            isverenler     = isverenler,
            diger_gelirler = diger,
            params         = params,
        )

        try:
            st.session_state["_sonuc"] = gmsi_hesapla(girdi)
            st.session_state["_girdi"] = girdi
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

    # ── Sonuçları göster ───────────────────────────────────────────────
    if "_sonuc" not in st.session_state:
        st.info("Yukarıdaki sekmeleri doldurun ve **Hesapla** butonuna tıklayın.")
    else:
        sonuc: object = st.session_state["_sonuc"]
        girdi: object = st.session_state["_girdi"]

        st.divider()

        # Uyarılar / bilgiler
        for warn in sonuc.warns:
            if warn.startswith("⚠️"):
                st.warning(warn)
            elif warn.startswith("ℹ️"):
                st.info(warn)
            elif warn.startswith("💚"):
                st.success(warn)

        # ── GMSİ Gelir Özeti ──────────────────────────────────────────
        st.subheader("🏠 GMSİ Gelir Özeti")
        c1, c2, c3 = st.columns(3)
        c1.metric("Konut Kira Geliri",    format_tl(sonuc.konut_brut))
        c2.metric("İşyeri (Stopajlı)",    format_tl(sonuc.isyeri_s_brut))
        c3.metric("İşyeri (Stopajsız)",   format_tl(sonuc.isyeri_n_brut))

        c1, c2, c3 = st.columns(3)
        c1.metric("Mesken İstisnası",     format_tl(sonuc.istisna))
        c2.metric("Beyana Tabi GMSİ",     format_tl(sonuc.toplam_gmsi_beyan))
        c3.metric("Gider İndirimi",       format_tl(sonuc.gmsi_gider))

        # ── Ücret ────────────────────────────────────────────────────
        if sonuc.ucret_beyan_zorunlu:
            st.subheader("👔 Ücret")
            c1, c2 = st.columns(2)
            c1.metric("Toplam Brüt Ücret",    format_tl(sonuc.toplam_brut_ucret))
            c2.metric("Ücret Stopajı",         format_tl(sonuc.toplam_ucret_stopaj))

        # ── Vergi Hesabı ─────────────────────────────────────────────
        st.subheader("💰 Vergi Hesabı")
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Vergi Matrahı",  format_tl(sonuc.toplam_matrah))
        c2.metric("Hesaplanan Vergi",      format_tl(sonuc.hes_ver))
        c3.metric("Mahsup Stopaj",         format_tl(sonuc.mahsup))

        st.divider()

        # ── Sonuç kutusu ─────────────────────────────────────────────
        if sonuc.odeme > 0:
            st.error(f"### 💸 Ödenecek Vergi: {format_tl(sonuc.odeme)}")
            c1, c2, c3 = st.columns(3)
            c1.metric("🗓️ 1. Taksit (Mart)",    format_tl(sonuc.taksit1))
            c2.metric("🗓️ 2. Taksit (Temmuz)",  format_tl(sonuc.taksit2))
            c3.metric("🏛️ Damga Vergisi",        format_tl(sonuc.damga))
        elif sonuc.iade > 0:
            st.success(f"### 💚 İade Tutarı: {format_tl(sonuc.iade)}")
        else:
            st.success("### ✅ Ödenecek Ek Vergi Yok")

        st.divider()

        # ── İndir ────────────────────────────────────────────────────
        st.subheader("📥 Sonuçları İndir")
        c1, c2 = st.columns(2)

        try:
            xlsx_bytes = export_excel(
                sonuc         = sonuc,
                year          = girdi.year,
                gider_yontemi = girdi.gider_yontemi,
                params        = girdi.params,
                isverenler    = girdi.isverenler,
                ucret_var     = girdi.ucret_var,
            )
            c1.download_button(
                label            = "📊 Excel (.xlsx) İndir",
                data             = xlsx_bytes,
                file_name        = f"GMSI_Vergi_{girdi.year}.xlsx",
                mime             = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width = True,
            )
        except Exception as e:
            c1.error(f"Excel hatası: {e}")

        try:
            pdf_bytes = export_pdf(
                sonuc         = sonuc,
                year          = girdi.year,
                gider_yontemi = girdi.gider_yontemi,
                params        = girdi.params,
            )
            c2.download_button(
                label            = "📄 PDF İndir",
                data             = pdf_bytes,
                file_name        = f"GMSI_Vergi_{girdi.year}.pdf",
                mime             = "application/pdf",
                use_container_width = True,
            )
        except Exception as e:
            c2.error(f"PDF hatası: {e}")
