"""
GMSİ Vergi Parametreleri
Kaynak: GİB – gib.gov.tr | GVK
Son güncelleme: 08 Mart 2026

Yeni yıl eklemek:
  python -m utils.gib_guncelle
"""

PARAMS = {
    2025: {
        "year": 2025,
        # kaynak: gib.gov.tr (resmi)
        "mesken_istisna": 47_000,
        "isyeri_beyan_esigi_stopajli": 330_000,
        "isyeri_beyan_esigi_stopajsiz": 18_000,
        "goturu_oran": 0.15,
        "isyeri_stopaj_orani": 0.20,
        "mesken_istisna_gelir_toplam_limiti": 1_200_000,
        "ucret_beyan_esigi": 230_000,
        "damga_vergisi": 167.20,
        "tarife_ucret_disi": [
            {"alt_sinir": 0,         "ust_sinir": 190_000,   "oran": 0.15, "taban": 0},
            {"alt_sinir": 190_000,   "ust_sinir": 400_000,   "oran": 0.20, "taban": 28_500},
            {"alt_sinir": 400_000,   "ust_sinir": 1_000_000, "oran": 0.27, "taban": 70_500},
            {"alt_sinir": 1_000_000, "ust_sinir": 5_300_000, "oran": 0.35, "taban": 232_500},
            {"alt_sinir": 5_300_000, "ust_sinir": None,      "oran": 0.40, "taban": 1_737_500},
        ],
    },
    2026: {
        "year": 2026,
        # kaynak: gib.gov.tr (resmi)
        "mesken_istisna": 58_000,
        "isyeri_beyan_esigi_stopajli": 400_000,
        "isyeri_beyan_esigi_stopajsiz": 22_000,
        "goturu_oran": 0.15,
        "isyeri_stopaj_orani": 0.20,
        "mesken_istisna_gelir_toplam_limiti": 1_400_000,
        "ucret_beyan_esigi": 280_000,
        "damga_vergisi": 185.00,
        "tarife_ucret_disi": [
            {"alt_sinir": 0,         "ust_sinir": 190_000,   "oran": 0.15, "taban": 0},
            {"alt_sinir": 190_000,   "ust_sinir": 400_000,   "oran": 0.20, "taban": 28_500},
            {"alt_sinir": 400_000,   "ust_sinir": 1_000_000, "oran": 0.27, "taban": 70_500},
            {"alt_sinir": 1_000_000, "ust_sinir": 5_300_000, "oran": 0.35, "taban": 232_500},
            {"alt_sinir": 5_300_000, "ust_sinir": None,      "oran": 0.40, "taban": 1_737_500},
        ],
    },
    2027: {
        "year": 2027,
        # kaynak: tahmin (gib.gov.tr taranıyor, önceki yıl x1.20)
        # GİB tebliğ yayımlandığında: python -m utils.gib_guncelle --yil 2027 --force
        "mesken_istisna": 70_000,
        "isyeri_beyan_esigi_stopajli": 480_000,
        "isyeri_beyan_esigi_stopajsiz": 27_000,
        "goturu_oran": 0.15,
        "isyeri_stopaj_orani": 0.20,
        "mesken_istisna_gelir_toplam_limiti": 1_680_000,
        "ucret_beyan_esigi": 336_000,
        "damga_vergisi": 222.00,
        "tarife_ucret_disi": [
            {"alt_sinir": 0,         "ust_sinir": 228_000,   "oran": 0.15, "taban": 0},
            {"alt_sinir": 228_000,   "ust_sinir": 480_000,   "oran": 0.20, "taban": 34_200},
            {"alt_sinir": 480_000,   "ust_sinir": 1_200_000, "oran": 0.27, "taban": 84_600},
            {"alt_sinir": 1_200_000, "ust_sinir": 6_360_000, "oran": 0.35, "taban": 279_000},
            {"alt_sinir": 6_360_000, "ust_sinir": None,      "oran": 0.40, "taban": 2_085_000},
        ],
    },
}