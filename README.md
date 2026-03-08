# 🏠 Kira Vergisi Hesaplayıcı

**Türkiye'de Gayrimenkul Sermaye İradı (GMSİ) Kira Geliri Vergi Hesaplama Web Uygulaması**  
GVK Md. 21, 70, 74, 86, 94 | GİB Hazır Beyan Uyumlu | 2025–2026

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://kira-vergisi-hesaplayici.streamlit.app)

> Türkiye'de kira geliri olan herkese yönelik, 2025-2026 GİB vergi parametrelerine göre GMSİ beyannamesini adım adım hesaplayan **ücretsiz web uygulaması**.

---

## 🚀 Kurulum ve Çalıştırma

### Streamlit (Önerilen)
```bash
git clone https://github.com/KULLANICI_ADIN/kira-vergisi-hesaplayici.git
cd kira-vergisi-hesaplayici
pip install -r requirements.txt
streamlit run streamlit_app.py
# → http://localhost:8501
```

### Flask (Lokal / API)
```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

---

## 📁 Proje Yapısı

```
kira-vergisi-hesaplayici/
├── streamlit_app.py         # Streamlit Cloud uygulaması (deploy için)
├── app.py                   # Flask uygulaması — tüm route'lar
├── params.py                # GVK vergi parametreleri (2025, 2026)
├── requirements.txt
├── README.md
├── utils/
│   ├── __init__.py
│   ├── hesapla.py           # Ana vergi hesaplama motoru (dataclass + pure Python)
│   ├── export_excel.py      # openpyxl ile .xlsx üretimi (3 sekme)
│   └── export_pdf.py        # reportlab ile A4 PDF üretimi
├── templates/
│   └── index.html           # Jinja2 şablonu — 5 adımlı sihirbaz
└── static/
    ├── css/style.css        # Tüm stiller
    └── js/app.js            # Frontend state ve API istekleri
```

---

## ⚙️ API Endpoint'leri

| Method | URL | Açıklama |
|--------|-----|----------|
| `GET`  | `/` | Ana sayfa (sihirbaz) |
| `POST` | `/api/hesapla` | JSON → hesaplama sonucu JSON |
| `POST` | `/api/export/excel` | JSON → `.xlsx` dosyası |
| `POST` | `/api/export/pdf`   | JSON → `.pdf` dosyası |
| `GET`  | `/api/params/<year>` | Yıl parametrelerini döner |

### POST `/api/hesapla` — Örnek İstek

```json
{
  "year": 2025,
  "gider_yontemi": "goturu",
  "mulkler": [
    {
      "tur": "konut",
      "gelir": 180000,
      "stopaj": 0,
      "hisse": 100,
      "ay": 12,
      "iktisap_bedeli": 0
    }
  ],
  "gercek_gider": { "aidat": 0, "sigorta": 0, "vergiler": 0, "amortisman": 0, "diger": 0, "kredi_faiz": 0 },
  "ucret_var": false,
  "isverenler": [],
  "diger_gelirler": { "msi": 0, "dki": 0, "faaliyet": false }
}
```

---

## ⚖️ Hesaplama Kuralları

| Kural | Kaynak |
|-------|--------|
| Mesken istisnası | GVK Md. 21 |
| Götürü gider %15 | GVK Md. 74 |
| İktisap bedeli %5 (kira hasılatı sınırlı) | GVK Md. 74/7 |
| Konut kredi faizi yasağı | 7566 s.K. (2025+) |
| GMSİ zararı mahsup edilemez | GVK Md. 88 |
| Ücret beyanı (2.+ işveren eşiği) | GVK Md. 86/1-b |
| İşyeri stopaj oranı %20 | GVK Md. 94 |

---

## 🔧 Yeni Yıl Parametresi Eklemek

`params.py` dosyasına yeni bir yıl anahtarı ekleyin:

```python
PARAMS[2027] = {
    "year": 2027,
    "mesken_istisna": 70_000,
    "isyeri_beyan_esigi_stopajli": 480_000,
    ...
}
```

---

## 📚 Yasal Kaynaklar

- GİB Kira Geliri: https://www.gib.gov.tr/kira-geliri  
- GİB Hazır Beyan: https://hazirbeyan.gib.gov.tr  
- Mevzuat: https://www.mevzuat.gov.tr  

---

## ⚠️ Yasal Uyarı

Bilgilendirme amaçlıdır. Kesin vergi yükümlülüğü için **YMM/SMMM**'ye danışınız.
