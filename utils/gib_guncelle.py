"""
GİB Otomatik Parametre Güncelleyici
====================================
gib.gov.tr / hazirbeyan.gib.gov.tr kaynaklarından yıllık vergi
parametrelerini çeker ve params.py dosyasını günceller.

Çalıştırma:
    python -m utils.gib_guncelle          # yeni yılı kontrol et + güncelle
    python -m utils.gib_guncelle --force  # sor olmadan güncelle
    python -m utils.gib_guncelle --check  # sadece kontrol et, dosya yazmaz

GİB sayfaları değişirse KAYNAK_URL sabitleri ve parse fonksiyonları güncellenmelidir.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("gib_guncelle")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ── Sabitler ─────────────────────────────────────────────────────────────
PARAMS_PATH = Path(__file__).parent.parent / "params.py"

# GİB'in yıllık beyan duyurularının yayımlandığı sayfalar
GIB_KIRA_URL      = "https://www.gib.gov.tr/kira-geliri"
GIB_HAZIRBEYAN    = "https://hazirbeyan.gib.gov.tr"
GIB_TEBLIG_URL    = "https://www.gib.gov.tr/gibmevzuat"   # tebliğ listesi

# İsteklerde kullanılacak başlık (bot engelini atlatmak için tarayıcı gibi görün)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# Timeout (saniye)
REQUEST_TIMEOUT = 15


# ── HTML Çekme ────────────────────────────────────────────────────────────
def _fetch(url: str) -> str:
    """URL'den HTML metnini döner. Hata durumunda boş string."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        logger.warning(f"GİB sayfasına erişilemedi ({url}): {exc}")
        return ""


# ── GİB Sayfasından Parametre Parse ──────────────────────────────────────

def _parse_sayi(metin: str) -> float | None:
    """
    'XX.XXX TL', 'XX.XXX,XX', '47.000' gibi formatlardaki sayıyı float'a çevirir.
    Türkçe format: nokta = binlik ayrac, virgül = ondalık.
    """
    if not metin:
        return None
    temiz = re.sub(r"[^\d.,]", "", metin.strip())
    # Türkçe format: 47.000 → 47000 | 1.200.000 → 1200000
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", temiz):
        temiz = temiz.replace(".", "").replace(",", ".")
    elif "," in temiz and "." in temiz:
        # belirsiz: 1.200,50 → Türkçe
        temiz = temiz.replace(".", "").replace(",", ".")
    elif "," in temiz:
        temiz = temiz.replace(",", ".")
    try:
        return float(temiz)
    except ValueError:
        return None


def _parse_mesken_istisna(html: str, yil: int) -> float | None:
    """
    GİB kira geliri sayfasından mesken istisna tutarını çeker.
    Sayfa formatı: '... XXXX yılında elde edilen kira gelirlerinde
    konut istisnası XX.XXX TL olarak uygulanacaktır ...'
    """
    patterns = [
        # Örn: "2026 yılı 58.000 TL"  veya  "58.000 TL istisna"
        rf"{yil}\s*y[ıi]l[ıi]?[^0-9]{{0,60}}(\d[\d.,]+)\s*TL\s*[içi{{{{]?stisnası?",
        rf"konut\s*istisnası?\s*(\d[\d.,]+)\s*TL",
        rf"mesken\s*istisnası?\s*(\d[\d.,]+)\s*TL",
        rf"istisna\s*tutar[ıi]\s*(\d[\d.,]+)\s*TL",
        rf"(\d[\d.,]+)\s*TL.*?istisna",
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            val = _parse_sayi(m.group(1))
            if val and 10_000 < val < 500_000:  # makul aralık
                return val
    return None


def _parse_ucret_esigi(html: str, yil: int) -> float | None:
    """2. işveren ücret beyan eşiği."""
    patterns = [
        rf"(\d[\d.,]+)\s*TL.*?(?:ikinci|2\.)\s*işveren",
        rf"(?:ikinci|2\.)\s*işveren.*?(\d[\d.,]+)\s*TL",
        rf"ücret\s*beyan.*?(\d[\d.,]+)\s*TL",
        rf"86.*?1.*?b.*?(\d[\d.,]+)\s*TL",
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE | re.DOTALL)
        if m:
            val = _parse_sayi(m.group(1))
            if val and 50_000 < val < 2_000_000:
                return val
    return None


def _parse_tarife(html: str) -> list[dict] | None:
    """
    GVK gelir vergisi tarifesini parse eder.
    Tablo formatı genellikle:
      0 – 190.000 TL için %15
      190.000 – 400.000 TL için %20
      ...
    """
    # Dilim pattern: iki sayı + oran (veya "üzeri")
    pattern = re.compile(
        r"(\d[\d.,]+)\s*[-–—]\s*(\d[\d.,]+)\s*TL.*?%\s*(\d+)"
        r"|(\d[\d.,]+)\s*TL.*?(?:fazlas[ıi]|üzer[ıi]|aşan).*?%\s*(\d+)",
        re.IGNORECASE,
    )
    dilimler = []
    for m in pattern.finditer(html):
        if m.group(1):
            alt = _parse_sayi(m.group(1))
            ust = _parse_sayi(m.group(2))
            oran = int(m.group(3)) / 100
        else:
            alt = _parse_sayi(m.group(4))
            ust = None
            oran = int(m.group(5)) / 100
        if alt is not None and 0 < oran < 1:
            dilimler.append((alt, ust, oran))

    if len(dilimler) < 4:
        return None

    # Sırala ve taban vergisini hesapla
    dilimler.sort(key=lambda x: x[0])
    tarife = []
    taban = 0.0
    for i, (alt, ust, oran) in enumerate(dilimler):
        if i > 0:
            prev_alt, prev_ust, prev_oran = dilimler[i - 1]
            if prev_ust:
                taban += (prev_ust - prev_alt) * prev_oran
        tarife.append({
            "alt_sinir": int(alt),
            "ust_sinir": int(ust) if ust else None,
            "oran": oran,
            "taban": round(taban, 2),
        })
    return tarife


def _parse_damga(html: str) -> float | None:
    """Damga vergisi tutarı."""
    patterns = [
        r"damga\s*vergisi.*?(\d[\d.,]+)\s*TL",
        r"(\d[\d.,]+)\s*TL.*?damga\s*vergisi",
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            val = _parse_sayi(m.group(1))
            if val and 50 < val < 5_000:
                return val
    return None


# ── Mevcut params.py Okuma ────────────────────────────────────────────────
def _load_mevcut_params() -> dict[int, dict]:
    """params.py dosyasını Python exec ile güvenli okur."""
    try:
        src = PARAMS_PATH.read_text(encoding="utf-8-sig")  # BOM'lu UTF-8 de okunur
        ns: dict[str, Any] = {}
        exec(compile(src, PARAMS_PATH.name, "exec"), ns)  # noqa: S102
        return ns.get("PARAMS", {})
    except Exception as exc:
        logger.error(f"params.py okunamadı: {exc}")
        return {}


# ── Yeni Yıl Parametresi Oluştur ─────────────────────────────────────────
def _onceki_yil_baz_al(mevcut: dict[int, dict], yil: int) -> dict:
    """
    GİB'den tam veri alınamazsa bir önceki yılı baz alarak
    enflasyon tahmini ile makul değerler üretir (~%20 artış).
    """
    onceki = mevcut.get(yil - 1, {})
    if not onceki:
        raise ValueError(f"{yil-1} yılı parametresi bulunamadı, baz alınamıyor.")

    ARTIS = 1.20  # yüzde 20 enflasyon tahmini

    def _yukari_yuvarlat(val: float, basamak: int = 1000) -> int:
        import math
        return int(math.ceil(val / basamak) * basamak)

    def _tarife_artir(tarife: list[dict]) -> list[dict]:
        yeni = []
        taban = 0.0
        for i, d in enumerate(tarife):
            yeni_alt = _yukari_yuvarlat(d["alt_sinir"] * ARTIS) if d["alt_sinir"] > 0 else 0
            yeni_ust = _yukari_yuvarlat(d["ust_sinir"] * ARTIS) if d["ust_sinir"] else None
            if i > 0:
                prev = yeni[i - 1]
                ust_prev = prev["ust_sinir"]
                if ust_prev:
                    taban += (ust_prev - prev["alt_sinir"]) * prev["oran"]
            yeni.append({
                "alt_sinir": yeni_alt,
                "ust_sinir": yeni_ust,
                "oran": d["oran"],
                "taban": round(taban, 2),
            })
        return yeni

    return {
        "year": yil,
        "mesken_istisna":                   _yukari_yuvarlat(onceki["mesken_istisna"] * ARTIS),
        "isyeri_beyan_esigi_stopajli":       _yukari_yuvarlat(onceki["isyeri_beyan_esigi_stopajli"] * ARTIS),
        "isyeri_beyan_esigi_stopajsiz":      _yukari_yuvarlat(onceki["isyeri_beyan_esigi_stopajsiz"] * ARTIS),
        "goturu_oran":                        onceki["goturu_oran"],
        "isyeri_stopaj_orani":                onceki["isyeri_stopaj_orani"],
        "mesken_istisna_gelir_toplam_limiti": _yukari_yuvarlat(onceki["mesken_istisna_gelir_toplam_limiti"] * ARTIS),
        "ucret_beyan_esigi":                 _yukari_yuvarlat(onceki["ucret_beyan_esigi"] * ARTIS),
        "damga_vergisi":                      round(onceki["damga_vergisi"] * ARTIS, 2),
        "tarife_ucret_disi":                  _tarife_artir(onceki["tarife_ucret_disi"]),
        "_kaynak":                            f"tahmini_{yil} (önceki yıl x{ARTIS})",
    }


def _gib_den_cek(yil: int, mevcut: dict[int, dict]) -> dict:
    """
    GİB sayfasından yıla ait parametreleri çekmeye çalışır.
    Veri bulunamazsa önceki yıl tahminiyle doldurur.
    """
    logger.info(f"GİB sayfaları taranıyor (hedef yıl: {yil})…")
    kira_html     = _fetch(GIB_KIRA_URL)
    hazir_html    = _fetch(GIB_HAZIRBEYAN)
    teblig_html   = _fetch(GIB_TEBLIG_URL)
    birlesik_html = kira_html + hazir_html + teblig_html

    onceki = mevcut.get(yil - 1) or mevcut.get(max(mevcut.keys(), default=yil - 1), {})

    mesken  = _parse_mesken_istisna(birlesik_html, yil)
    esik    = _parse_ucret_esigi(birlesik_html, yil)
    tarife  = _parse_tarife(birlesik_html)
    damga   = _parse_damga(birlesik_html)

    bulunanlar = []
    if mesken:  bulunanlar.append(f"mesken_istisna={mesken:,.0f}")
    if esik:    bulunanlar.append(f"ucret_beyan_esigi={esik:,.0f}")
    if tarife:  bulunanlar.append(f"tarife({len(tarife)} dilim)")
    if damga:   bulunanlar.append(f"damga={damga}")

    if bulunanlar:
        logger.info(f"GİB'den bulunan: {', '.join(bulunanlar)}")
    else:
        logger.warning("GİB'den veri çekilemedi — önceki yıl tahmini kullanılıyor.")

    # Tahmini baz oluştur, sonra gerçek değerleri üzerine yaz
    yeni = _onceki_yil_baz_al(mevcut, yil)
    yeni["_kaynak"] = f"gib.gov.tr + tahmin_{yil}"

    if mesken:
        yeni["mesken_istisna"] = int(mesken)
    if esik:
        yeni["ucret_beyan_esigi"] = int(esik)
    if tarife:
        yeni["tarife_ucret_disi"] = tarife
    if damga:
        yeni["damga_vergisi"] = damga

    return yeni


# ── params.py Yazma ───────────────────────────────────────────────────────
def _params_py_yaz(params: dict[int, dict]) -> None:
    """params.py dosyasını sıfırdan yeniden yazar."""

    def _tarife_satirlari(tarife: list[dict], girinti: str) -> str:
        satirlar = []
        for d in tarife:
            ust = "None" if d["ust_sinir"] is None else str(d["ust_sinir"])
            satirlar.append(
                f'{girinti}    {{"alt_sinir": {d["alt_sinir"]:<10}, '
                f'"ust_sinir": {ust:<10}, '
                f'"oran": {d["oran"]}, '
                f'"taban": {d["taban"]}}},'
            )
        return "\n".join(satirlar)

    def _blok(yil: int, p: dict) -> str:
        kaynak = p.get("_kaynak", "manuel")
        tarife_satirlar = []
        for d in p["tarife_ucret_disi"]:
            ust = "None" if d["ust_sinir"] is None else str(d["ust_sinir"])
            tarife_satirlar.append(
                f'            {{"alt_sinir": {d["alt_sinir"]:<10}, '
                f'"ust_sinir": {ust:<10}, '
                f'"oran": {d["oran"]}, '
                f'"taban": {d["taban"]}}},'
            )
        tarife_str = "\n".join(tarife_satirlar)
        return (
            f"    {yil}: {{\n"
            f'        "year": {yil},\n'
            f"        # kaynak: {kaynak}\n"
            f'        "mesken_istisna": {p["mesken_istisna"]},\n'
            f'        "isyeri_beyan_esigi_stopajli": {p["isyeri_beyan_esigi_stopajli"]},\n'
            f'        "isyeri_beyan_esigi_stopajsiz": {p["isyeri_beyan_esigi_stopajsiz"]},\n'
            f'        "goturu_oran": {p["goturu_oran"]},\n'
            f'        "isyeri_stopaj_orani": {p["isyeri_stopaj_orani"]},\n'
            f'        "mesken_istisna_gelir_toplam_limiti": {p["mesken_istisna_gelir_toplam_limiti"]},\n'
            f'        "ucret_beyan_esigi": {p["ucret_beyan_esigi"]},\n'
            f'        "damga_vergisi": {p["damga_vergisi"]},\n'
            f'        "tarife_ucret_disi": [\n'
            f"{tarife_str}\n"
            f"        ],\n"
            f"    }},\n"
        )

    yillar_blok = "".join(_blok(y, p) for y, p in sorted(params.items()))

    icerik = (
        '"""\n'
        "GMSİ Vergi Parametreleri\n"
        "Kaynak: GİB – gib.gov.tr | GVK\n"
        f"Son güncelleme: {datetime.now().strftime('%d %B %Y %H:%M')}\n\n"
        "Yeni yıl eklemek:\n"
        "  python -m utils.gib_guncelle\n"
        '"""\n\n'
        "PARAMS = {\n"
        f"{yillar_blok}"
        "}\n"
    )

    PARAMS_PATH.write_text(icerik, encoding="utf-8")
    logger.info(f"params.py güncellendi → {PARAMS_PATH}")


# ── Ana Fonksiyon ─────────────────────────────────────────────────────────
def guncelle(hedef_yil: int | None = None, force: bool = False) -> dict | None:
    """
    Yeni yılın parametre bloğunu oluşturur / günceller.

    Returns:
        Eklenen/güncellenen parametre sözlüğü, değişiklik yoksa None.
    """
    mevcut = _load_mevcut_params()
    if not mevcut:
        logger.error("Mevcut parametreler yüklenemedi, devam edilemiyor.")
        return None

    if hedef_yil is None:
        # Bir sonraki yılı hedef al (mevcut max yıl + 1)
        hedef_yil = max(mevcut.keys()) + 1

    if hedef_yil in mevcut and not force:
        logger.info(f"{hedef_yil} parametreleri zaten mevcut. --force ile üzerine yaz.")
        return None

    yeni_params = _gib_den_cek(hedef_yil, mevcut)

    # Güncelleme
    mevcut[hedef_yil] = yeni_params
    _params_py_yaz(mevcut)

    return yeni_params


def kontrol_et() -> dict:
    """
    Yıl başlarında çalıştırılır; yeni yıl gerekli mi kontrol eder.
    Streamlit / Flask'tan çağrılabilir.

    Returns:
        {
          "guncelleme_gerekli": bool,
          "hedef_yil": int,
          "mevcut_max_yil": int,
          "yeni_params": dict | None  # güncelleme yapıldıysa
        }
    """
    mevcut = _load_mevcut_params()
    mevcut_max  = max(mevcut.keys()) if mevcut else 0
    cari_yil    = datetime.now().year
    # Beyan dönemi: önceki yıl geliri → cari yılda beyan
    hedef_yil   = cari_yil - 1   # örn. 2026'da 2025 geliri beyan ediliyor

    # Bir ileri yıl parametresi de varsa zaten güncel
    ihtiyac_yili = hedef_yil + 1   # hesaplamada gelecek yıl da seçilebilir
    guncelleme_gerekli = ihtiyac_yili > mevcut_max

    durum = {
        "guncelleme_gerekli": guncelleme_gerekli,
        "hedef_yil":          ihtiyac_yili,
        "mevcut_max_yil":     mevcut_max,
        "yeni_params":        None,
    }

    if guncelleme_gerekli:
        logger.info(f"{ihtiyac_yili} yılı parametresi eksik — GİB güncellemesi başlatılıyor…")
        yeni = guncelle(ihtiyac_yili, force=False)
        durum["yeni_params"] = yeni

    return durum


# ── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GİB'den yıllık vergi parametrelerini günceller."
    )
    parser.add_argument(
        "--yil", type=int, default=None,
        help="Hedef yıl (varsayılan: mevcut max + 1)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Var olan yılın üzerine yaz",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Sadece kontrol et, params.py yazma",
    )
    args = parser.parse_args()

    if args.check:
        durum = kontrol_et()
        print(json.dumps(durum, ensure_ascii=False, indent=2, default=str))
    else:
        sonuc = guncelle(hedef_yil=args.yil, force=args.force)
        if sonuc:
            print(json.dumps(sonuc, ensure_ascii=False, indent=2, default=str))
        else:
            print("Güncelleme yapılmadı.")
