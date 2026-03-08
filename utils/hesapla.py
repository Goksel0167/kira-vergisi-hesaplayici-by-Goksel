"""
GMSİ Vergi Hesaplama Motoru
GVK Md. 21, 70, 74, 86, 94 esas alınarak hazırlanmıştır.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ── Yardımcı ──────────────────────────────────────────────────────────────

def format_tl(val: float | None) -> str:
    if val is None:
        return "—"
    return f"₺{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gelir_vergisi_hesapla(matrah: float, tarife: list[dict]) -> float:
    """Kademeli vergi tarifesini uygula."""
    if matrah <= 0:
        return 0.0
    for dilim in tarife:
        ust = dilim["ust_sinir"]
        if ust is None or matrah <= ust:
            return dilim["taban"] + (matrah - dilim["alt_sinir"]) * dilim["oran"]
    return 0.0


# ── Veri sınıfları ────────────────────────────────────────────────────────

@dataclass
class Mulk:
    tur: str                    # 'konut' | 'isyeri_stopajli' | 'isyeri_stopajsiz'
    gelir: float                # Yıllık kira geliri (hisseye düşen)
    stopaj: float = 0.0         # Kesilen stopaj (hisseye düşen)
    hisse: float = 100.0        # Yüzde
    ay: int = 12
    iktisap_bedeli: float = 0.0 # Konut alış bedeli (gerçek gider için)

    @property
    def gelir_tl(self) -> float:
        return self.gelir * (self.hisse / 100)

    @property
    def stopaj_tl(self) -> float:
        return self.stopaj * (self.hisse / 100)

    @property
    def iktisap_tl(self) -> float:
        return self.iktisap_bedeli


@dataclass
class Isveren:
    ad: str = ""
    brut_yillik: float = 0.0
    stopaj: float = 0.0
    birinci: bool = True          # True = 1. işveren (en yüksek ücret)


@dataclass
class GercekGider:
    aidat: float = 0.0
    sigorta: float = 0.0
    vergiler: float = 0.0
    amortisman: float = 0.0
    diger: float = 0.0
    kredi_faiz: float = 0.0       # 2025+ konut için indirilemez!

    @property
    def toplam_gecerli(self) -> float:
        """Kredi faizini dahil etme."""
        return self.aidat + self.sigorta + self.vergiler + self.amortisman + self.diger


@dataclass
class DigerGelirler:
    msi: float = 0.0              # Menkul sermaye iradı
    dki: float = 0.0              # Diğer kazanç ve iratlar
    faaliyet: bool = False        # Ticari/zirai/mesleki kazanç var mı?


@dataclass
class HesaplamaGirdisi:
    year: int
    mulkler: list[Mulk]
    gider_yontemi: str            # 'goturu' | 'gercek'
    gercek_gider: GercekGider
    ucret_var: bool
    isverenler: list[Isveren]
    diger_gelirler: DigerGelirler
    params: dict


@dataclass
class HesaplaSonucu:
    # GMSİ Gelirleri
    konut_brut: float = 0.0
    isyeri_s_brut: float = 0.0
    isyeri_n_brut: float = 0.0
    gmsi_stopaj: float = 0.0

    # Ücret
    toplam_brut_ucret: float = 0.0
    toplam_ucret_stopaj: float = 0.0
    birinci_isveren: float = 0.0
    diger_isverenler: float = 0.0
    ucret_beyan_zorunlu: bool = False

    # İstisna
    istisna: float = 0.0

    # Beyan
    toplam_gmsi_beyan: float = 0.0
    gmsi_gider: float = 0.0
    iktisap_acik: str = ""

    # Matrah
    gmsi_matrah: float = 0.0
    ucret_matrah: float = 0.0
    toplam_matrah: float = 0.0

    # Vergi
    hes_ver: float = 0.0
    mahsup: float = 0.0
    toplam_stopaj: float = 0.0
    odeme: float = 0.0
    iade: float = 0.0
    damga: float = 0.0
    taksit1: float = 0.0
    taksit2: float = 0.0

    # Uyarılar
    warns: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


# ── Ana Hesaplama ─────────────────────────────────────────────────────────

def gmsi_hesapla(girdi: HesaplamaGirdisi) -> HesaplaSonucu:
    """
    GMSİ + ücret vergi hesaplaması.

    Kurallar:
    - İktisap bedeli %5 o konutun kira hasılatını aşamaz (zarar oluşturulamaz)
    - 2025+ konut kredi faizi indirilemez (7566 s.K.)
    - GMSİ zararı diğer gelirlere mahsup edilemez
    - GVK Md. 86/1-b: 2.+ işveren toplamı eşiği aşarsa tüm ücretler beyan
    """
    p = girdi.params
    sonuc = HesaplaSonucu()

    # ── Mülk hesapları ────────────────────────────────────────────────────
    konut_mulkler = [m for m in girdi.mulkler if m.tur == "konut"]
    sonuc.konut_brut  = sum(m.gelir_tl for m in konut_mulkler)
    sonuc.isyeri_s_brut = sum(m.gelir_tl for m in girdi.mulkler if m.tur == "isyeri_stopajli")
    sonuc.isyeri_n_brut = sum(m.gelir_tl for m in girdi.mulkler if m.tur == "isyeri_stopajsiz")
    sonuc.gmsi_stopaj   = sum(m.stopaj_tl for m in girdi.mulkler)

    # ── Ücret hesapları ───────────────────────────────────────────────────
    iv_list = girdi.isverenler if girdi.ucret_var else []
    sonuc.toplam_brut_ucret   = sum(iv.brut_yillik for iv in iv_list)
    sonuc.toplam_ucret_stopaj = sum(iv.stopaj for iv in iv_list)
    sonuc.birinci_isveren     = sum(iv.brut_yillik for iv in iv_list if iv.birinci)
    sonuc.diger_isverenler    = sum(iv.brut_yillik for iv in iv_list if not iv.birinci)
    sonuc.ucret_beyan_zorunlu = girdi.ucret_var and sonuc.diger_isverenler > p["ucret_beyan_esigi"]

    if sonuc.ucret_beyan_zorunlu:
        sonuc.warns.append(
            f"⚠️ 2. ve sonraki işverenlerden alınan ücret toplamı "
            f"({format_tl(sonuc.diger_isverenler)}), beyan eşiğini "
            f"({format_tl(p['ucret_beyan_esigi'])}) aşıyor. Beyan zorunludur."
        )

    # ── Mesken istisnası kontrolü ─────────────────────────────────────────
    toplam_gelir_kontrol = (
        sonuc.konut_brut + sonuc.isyeri_s_brut + sonuc.isyeri_n_brut +
        sonuc.toplam_brut_ucret + girdi.diger_gelirler.msi + girdi.diger_gelirler.dki
    )

    if sonuc.konut_brut > 0:
        if girdi.diger_gelirler.faaliyet:
            sonuc.warns.append(
                "⚠️ Ticari/zirai/mesleki kazancı beyan edenler mesken istisnasından yararlanamaz."
            )
        elif toplam_gelir_kontrol > p["mesken_istisna_gelir_toplam_limiti"]:
            sonuc.warns.append(
                f"⚠️ Toplam brüt geliriniz ({format_tl(toplam_gelir_kontrol)}), "
                f"mesken istisnası sınırını ({format_tl(p['mesken_istisna_gelir_toplam_limiti'])}) "
                f"aşıyor. İstisna uygulanmadı."
            )
        else:
            sonuc.istisna = min(sonuc.konut_brut, p["mesken_istisna"])

    # ── Beyana tabi tutarlar ──────────────────────────────────────────────
    beyan_konut = max(0.0, sonuc.konut_brut - sonuc.istisna)

    beyan_isyeri_s = 0.0
    if sonuc.isyeri_s_brut >= p["isyeri_beyan_esigi_stopajli"]:
        beyan_isyeri_s = sonuc.isyeri_s_brut
    elif sonuc.isyeri_s_brut > 0:
        sonuc.warns.append(
            f"ℹ️ Stopajlı işyeri kira geliriniz ({format_tl(sonuc.isyeri_s_brut)}), "
            f"beyan eşiğinin ({format_tl(p['isyeri_beyan_esigi_stopajli'])}) altında. "
            "Beyana dahil edilmedi."
        )

    beyan_isyeri_n = (
        sonuc.isyeri_n_brut
        if sonuc.isyeri_n_brut >= p["isyeri_beyan_esigi_stopajsiz"]
        else 0.0
    )

    sonuc.toplam_gmsi_beyan = beyan_konut + beyan_isyeri_s + beyan_isyeri_n

    # ── Gider hesabı ──────────────────────────────────────────────────────
    if girdi.gider_yontemi == "goturu":
        sonuc.gmsi_gider = sonuc.toplam_gmsi_beyan * p["goturu_oran"]

    else:  # gerçek gider
        temel = girdi.gercek_gider.toplam_gecerli

        # Konut kredi faizi — 2025'ten itibaren indirilemez
        if girdi.gercek_gider.kredi_faiz > 0:
            sonuc.warns.append(
                "⚠️ 2025'ten itibaren konut için kredi/ipotek faizi gider olarak indirilemez "
                "(7566 sayılı Kanun). Bu tutar hariç tutuldu."
            )

        # İktisap bedeli %5 — SINIR: o konutun kira hasılatını aşamaz
        toplam_iktisap = 0.0
        for m in konut_mulkler:
            indirimi = m.iktisap_tl * 0.05
            sinir    = m.gelir_tl
            gecerli  = min(indirimi, sinir)
            toplam_iktisap += gecerli
            if indirimi > sinir > 0:
                sonuc.warns.append(
                    f"⚠️ İktisap bedeli %5 indirimi ({format_tl(indirimi)}), "
                    f"bu konutun yıllık kira hasılatını ({format_tl(sinir)}) aşıyor. "
                    f"Aşan kısım ({format_tl(indirimi - sinir)}) indirilmedi — "
                    "GMSİ'de zarar/aktarma yapılamaz."
                )

        sonuc.gmsi_gider = temel + toplam_iktisap
        sonuc.iktisap_acik = (
            f" (iktisap %5: {format_tl(toplam_iktisap)} dahil)" if toplam_iktisap > 0 else ""
        )

        # GMSİ'de zarar diğer gelirlere mahsup edilemez
        if sonuc.gmsi_gider > sonuc.toplam_gmsi_beyan > 0:
            sonuc.warns.append(
                f"⚠️ Gerçek gider toplamı ({format_tl(sonuc.gmsi_gider)}), beyana tabi GMSİ "
                f"gelirini ({format_tl(sonuc.toplam_gmsi_beyan)}) aşıyor. "
                "GMSİ zararı diğer gelirlere mahsup edilemez; gider sınırlandırıldı."
            )
            sonuc.gmsi_gider = sonuc.toplam_gmsi_beyan

    # ── Matrah ve vergi ───────────────────────────────────────────────────
    sonuc.gmsi_matrah   = max(0.0, sonuc.toplam_gmsi_beyan - sonuc.gmsi_gider)
    sonuc.ucret_matrah  = sonuc.toplam_brut_ucret if sonuc.ucret_beyan_zorunlu else 0.0
    sonuc.toplam_matrah = sonuc.gmsi_matrah + sonuc.ucret_matrah

    sonuc.hes_ver       = gelir_vergisi_hesapla(sonuc.toplam_matrah, p["tarife_ucret_disi"])
    sonuc.toplam_stopaj = sonuc.gmsi_stopaj + (
        sonuc.toplam_ucret_stopaj if sonuc.ucret_beyan_zorunlu else 0.0
    )
    sonuc.mahsup  = min(sonuc.toplam_stopaj, sonuc.hes_ver)
    sonuc.odeme   = max(0.0, sonuc.hes_ver - sonuc.mahsup)
    sonuc.iade    = max(0.0, sonuc.mahsup - sonuc.hes_ver)
    sonuc.damga   = p["damga_vergisi"] if sonuc.odeme > 0 else 0.0
    sonuc.taksit1 = sonuc.odeme / 2
    sonuc.taksit2 = sonuc.odeme / 2

    if sonuc.iade > 0:
        sonuc.warns.append(
            f"💚 Fazla kesilen {format_tl(sonuc.iade)} için vergi dairesine "
            "iade başvurusunda bulunabilirsiniz."
        )

    return sonuc
