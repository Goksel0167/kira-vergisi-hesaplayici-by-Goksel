"""
GMSİ Vergi Parametreleri
Kaynak: GİB – gib.gov.tr | GVK 332 No'lu Tebliğ
Son güncelleme: Mart 2026

Yeni yıl eklemek için bu dosyaya yeni bir sözlük anahtarı ekleyin.
"""

PARAMS = {
    2025: {
        "year": 2025,
        "mesken_istisna": 47_000,
        "isyeri_beyan_esigi_stopajli": 330_000,
        "isyeri_beyan_esigi_stopajsiz": 18_000,
        "goturu_oran": 0.15,
        "isyeri_stopaj_orani": 0.20,
        "mesken_istisna_gelir_toplam_limiti": 1_200_000,
        "ucret_beyan_esigi": 230_000,          # GVK Md. 86/1-b
        "damga_vergisi": 167.20,
        "tarife_ucret_disi": [
            {"alt_sinir": 0,         "ust_sinir": 190_000,  "oran": 0.15, "taban": 0},
            {"alt_sinir": 190_000,   "ust_sinir": 400_000,  "oran": 0.20, "taban": 28_500},
            {"alt_sinir": 400_000,   "ust_sinir": 1_000_000,"oran": 0.27, "taban": 70_500},
            {"alt_sinir": 1_000_000, "ust_sinir": 5_300_000,"oran": 0.35, "taban": 232_500},
            {"alt_sinir": 5_300_000, "ust_sinir": None,     "oran": 0.40, "taban": 1_737_500},
        ],
    },
    2026: {
        "year": 2026,
        "mesken_istisna": 58_000,
        "isyeri_beyan_esigi_stopajli": 400_000,
        "isyeri_beyan_esigi_stopajsiz": 22_000,
        "goturu_oran": 0.15,
        "isyeri_stopaj_orani": 0.20,
        "mesken_istisna_gelir_toplam_limiti": 1_400_000,
        "ucret_beyan_esigi": 280_000,
        "damga_vergisi": 185.00,               # tahmini 2026
        "tarife_ucret_disi": [
            {"alt_sinir": 0,         "ust_sinir": 190_000,  "oran": 0.15, "taban": 0},
            {"alt_sinir": 190_000,   "ust_sinir": 400_000,  "oran": 0.20, "taban": 28_500},
            {"alt_sinir": 400_000,   "ust_sinir": 1_000_000,"oran": 0.27, "taban": 70_500},
            {"alt_sinir": 1_000_000, "ust_sinir": 5_300_000,"oran": 0.35, "taban": 232_500},
            {"alt_sinir": 5_300_000, "ust_sinir": None,     "oran": 0.40, "taban": 1_737_500},
        ],
    },
}
