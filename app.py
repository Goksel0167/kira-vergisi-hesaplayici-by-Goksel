"""
GMSİ Vergi Hesaplayıcı — Flask Web Uygulaması
Çalıştır: python app.py  →  http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, send_file
import io, importlib, json

import params as _params_module
from params import PARAMS
from utils.gib_guncelle import kontrol_et as _gib_kontrol
from utils.hesapla import (
    gmsi_hesapla, HesaplamaGirdisi,
    Mulk, Isveren, GercekGider, DigerGelirler, format_tl
)
from utils.export_excel import export_excel
from utils.export_pdf   import export_pdf

app = Flask(__name__)
app.secret_key = "gmsi-2025-secret"


# ── Yardımcı: form verisini Python nesnelerine dönüştür ───────────────────

def _parse_float(val, default=0.0) -> float:
    try:
        return float(str(val).replace(".", "").replace(",", ".").strip())
    except (ValueError, TypeError):
        return default


def _build_girdi(data: dict) -> HesaplamaGirdisi:
    year   = int(data.get("year", 2025))
    params = PARAMS[year]

    # Mülkler
    mulkler = []
    for m in data.get("mulkler", []):
        mulkler.append(Mulk(
            tur            = m.get("tur", "konut"),
            gelir          = _parse_float(m.get("gelir")),
            stopaj         = _parse_float(m.get("stopaj")),
            hisse          = _parse_float(m.get("hisse", 100)),
            ay             = int(m.get("ay", 12)),
            iktisap_bedeli = _parse_float(m.get("iktisap_bedeli")),
        ))

    # Gerçek gider
    g = data.get("gercek_gider", {})
    gercek = GercekGider(
        aidat       = _parse_float(g.get("aidat")),
        sigorta     = _parse_float(g.get("sigorta")),
        vergiler    = _parse_float(g.get("vergiler")),
        amortisman  = _parse_float(g.get("amortisman")),
        diger       = _parse_float(g.get("diger")),
        kredi_faiz  = _parse_float(g.get("kredi_faiz")),
    )

    # İşverenler
    ucret_var  = bool(data.get("ucret_var", False))
    isverenler = []
    for iv in data.get("isverenler", []):
        isverenler.append(Isveren(
            ad          = iv.get("ad", ""),
            brut_yillik = _parse_float(iv.get("brut_yillik")),
            stopaj      = _parse_float(iv.get("stopaj")),
            birinci     = bool(iv.get("birinci", True)),
        ))

    # Diğer gelirler
    dg = data.get("diger_gelirler", {})
    diger = DigerGelirler(
        msi      = _parse_float(dg.get("msi")),
        dki      = _parse_float(dg.get("dki")),
        faaliyet = bool(dg.get("faaliyet", False)),
    )

    return HesaplamaGirdisi(
        year           = year,
        mulkler        = mulkler,
        gider_yontemi  = data.get("gider_yontemi", "goturu"),
        gercek_gider   = gercek,
        ucret_var      = ucret_var,
        isverenler     = isverenler,
        diger_gelirler = diger,
        params         = params,
    )


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", params=PARAMS, years=list(PARAMS.keys()))


@app.route("/api/hesapla", methods=["POST"])
def api_hesapla():
    """JSON POST → hesaplama sonucu JSON döner."""
    try:
        data   = request.get_json(force=True)
        girdi  = _build_girdi(data)
        sonuc  = gmsi_hesapla(girdi)
        result = sonuc.as_dict()

        # Format edilmiş değerleri de ekle (frontend display için)
        result["fmt"] = {k: format_tl(v) for k, v in result.items()
                         if isinstance(v, float)}
        result["year"] = girdi.year

        # Parametre özeti (frontend'de göster)
        p = girdi.params
        result["params_ozet"] = {
            "mesken_istisna":             p["mesken_istisna"],
            "isyeri_beyan_esigi_stopajli":p["isyeri_beyan_esigi_stopajli"],
            "ucret_beyan_esigi":          p["ucret_beyan_esigi"],
            "goturu_oran":                p["goturu_oran"],
        }

        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/export/excel", methods=["POST"])
def api_export_excel():
    """JSON POST → .xlsx dosyası döner."""
    try:
        data       = request.get_json(force=True)
        girdi      = _build_girdi(data)
        sonuc      = gmsi_hesapla(girdi)
        xlsx_bytes = export_excel(
            sonuc         = sonuc,
            year          = girdi.year,
            gider_yontemi = girdi.gider_yontemi,
            params        = girdi.params,
            isverenler    = girdi.isverenler,
            ucret_var     = girdi.ucret_var,
        )
        return send_file(
            io.BytesIO(xlsx_bytes),
            mimetype    = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment = True,
            download_name = f"GMSI_Vergi_{girdi.year}.xlsx",
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/export/pdf", methods=["POST"])
def api_export_pdf():
    """JSON POST → .pdf dosyası döner."""
    try:
        data      = request.get_json(force=True)
        girdi     = _build_girdi(data)
        sonuc     = gmsi_hesapla(girdi)
        pdf_bytes = export_pdf(
            sonuc         = sonuc,
            year          = girdi.year,
            gider_yontemi = girdi.gider_yontemi,
            params        = girdi.params,
        )
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype      = "application/pdf",
            as_attachment = True,
            download_name = f"GMSI_Vergi_{girdi.year}.pdf",
        )
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/params/<int:year>")
def api_params(year: int):
    """Belirli bir yılın parametrelerini döner."""
    _reload_params()
    if year not in PARAMS:
        return jsonify({"ok": False, "error": "Yıl bulunamadı"}), 404
    return jsonify({"ok": True, "data": PARAMS[year]})


# ── Parametre reload yardımcısı ───────────────────────────────────────────
def _reload_params():
    """params.py değiştiyse modülü canlı olarak yeniden yükler."""
    global PARAMS
    importlib.reload(_params_module)
    PARAMS = _params_module.PARAMS


# ── GİB Güncelleme Endpoint'leri ─────────────────────────────────────────
@app.route("/api/admin/gib-guncelle", methods=["POST"])
def api_gib_guncelle():
    """
    GİB'den yeni yıl parametrelerini çeker ve params.py'yi günceller.
    POST body (opsiyonel): {"yil": 2027, "force": false}
    """
    try:
        body      = request.get_json(silent=True) or {}
        hedef_yil = body.get("yil")  # None → otomatik
        force     = bool(body.get("force", False))

        from utils.gib_guncelle import guncelle
        yeni = guncelle(hedef_yil=hedef_yil, force=force)
        _reload_params()

        if yeni:
            return jsonify({"ok": True, "guncellendi": True,  "yeni_params": yeni})
        else:
            return jsonify({"ok": True, "guncellendi": False, "mesaj": "Güncelleme gerekmedi."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/admin/gib-kontrol")
def api_gib_kontrol():
    """Yeni yıl parametresi gerekli mi kontrol eder."""
    try:
        durum = _gib_kontrol()
        _reload_params()
        durum["mevcut_yillar"] = sorted(PARAMS.keys())
        return jsonify({"ok": True, "data": durum})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Uygulama başlarken yeni yıl kontrolü yap
    try:
        durum = _gib_kontrol()
        if durum.get("guncelleme_gerekli") and durum.get("yeni_params"):
            _reload_params()
    except Exception:
        pass
    app.run(debug=True, port=5000)
