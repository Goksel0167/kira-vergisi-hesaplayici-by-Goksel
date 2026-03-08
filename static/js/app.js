/* ── State ────────────────────────────────────────────────────────────── */
const state = {
  year: 2025,
  giderYontemi: 'goturu',
  mulkler: [],
  mulkIdx: 0,
  isverenler: [],
  isvIdx: 0,
  ucretVar: false,
  lastResult: null,
  lastData: null,
};

/* ── Yardımcılar ─────────────────────────────────────────────────────── */
const fmt = (n) =>
  n == null ? '—' :
  '₺' + Number(n).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const $ = (id) => document.getElementById(id);

/* ── Adım Yönetimi ───────────────────────────────────────────────────── */
function goStep(n) {
  document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
  $(`step${n}`).classList.add('active');

  // Progress dots
  for (let i = 1; i <= 5; i++) {
    const dot = $(`pd${i}`);
    if (!dot) continue;
    dot.classList.remove('done', 'active');
    if (i < n)       dot.classList.add('done'),   dot.textContent = '✓';
    else if (i === n) dot.classList.add('active'), dot.textContent = String(i);
    else              dot.textContent = String(i);
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Adım 1: Yıl ─────────────────────────────────────────────────────── */
function selectYear(y, btn) {
  state.year = y;
  document.querySelectorAll('.year-card').forEach(c => {
    c.classList.remove('active');
    c.querySelector('.year-chk').style.display = 'none';
  });
  btn.classList.add('active');
  btn.querySelector('.year-chk').style.display = 'inline-block';

  // Ücret eşik bilgisini güncelle
  updateUcretEsikInfo();
}

/* ── Adım 2: Mülkler ─────────────────────────────────────────────────── */
function addMulk(tur = 'konut') {
  const id = ++state.mulkIdx;
  state.mulkler.push({ id, tur, gelir: 0, stopaj: 0, hisse: 100, ay: 12, iktisap_bedeli: 0 });
  renderMulkler();
}

function removeMulk(id) {
  state.mulkler = state.mulkler.filter(m => m.id !== id);
  renderMulkler();
}

function renderMulkler() {
  const c = $('mulklerContainer');
  c.innerHTML = '';

  state.mulkler.forEach((m, idx) => {
    const div = document.createElement('div');
    div.className = 'mulk-card';
    div.innerHTML = `
      <div class="mulk-head">
        <span class="mulk-no">Mülk #${idx + 1}</span>
        ${state.mulkler.length > 1 ? `<button class="btn-rem" onclick="removeMulk(${m.id})">✕ Sil</button>` : ''}
      </div>
      <div class="form-grid">
        <div class="fg">
          <label>Mülk Türü *</label>
          <select onchange="updateMulk(${m.id},'tur',this.value)">
            <option value="konut"            ${m.tur==='konut'?'selected':''}>🏠 Konut (Mesken)</option>
            <option value="isyeri_stopajli"  ${m.tur==='isyeri_stopajli'?'selected':''}>🏢 İşyeri – Stopajlı</option>
            <option value="isyeri_stopajsiz" ${m.tur==='isyeri_stopajsiz'?'selected':''}>🏗 İşyeri / Diğer – Stopajsız</option>
          </select>
        </div>
        <div class="fg">
          <label>${m.tur === 'isyeri_stopajli' ? 'Brüt Yıllık Kira (TL) *' : 'Yıllık Kira Geliri (TL) *'}</label>
          <input type="number" placeholder="Örn: 120000" value="${m.gelir || ''}"
                 onchange="updateMulk(${m.id},'gelir',this.value)"/>
        </div>
        ${m.tur === 'isyeri_stopajli' ? `
        <div class="fg">
          <label>Kesilen Stopaj (TL)</label>
          <small>Kiracının muhtasar ile ödediği vergi (Brüt × %20)</small>
          <input type="number" placeholder="0" value="${m.stopaj || ''}"
                 onchange="updateMulk(${m.id},'stopaj',this.value)"/>
        </div>` : ''}
        <div class="fg">
          <label>Hisse Oranı (%)</label>
          <small>Ortak mülkiyet varsa size düşen pay</small>
          <input type="number" min="1" max="100" value="${m.hisse}"
                 onchange="updateMulk(${m.id},'hisse',this.value)"/>
        </div>
        <div class="fg">
          <label>Kiralama Süresi</label>
          <select onchange="updateMulk(${m.id},'ay',this.value)">
            ${[1,2,3,4,5,6,7,8,9,10,11,12].map(a =>
              `<option value="${a}" ${m.ay==a?'selected':''}>${a} ay</option>`).join('')}
          </select>
        </div>
        ${m.tur === 'konut' ? `
        <div class="fg">
          <label>İktisap / Alış Bedeli (TL)</label>
          <small>GVK 74/7: Alış bedelinin %5'i gider — o konutun kira hasılatını aşamaz (5 yıl, tek konut)</small>
          <input type="number" placeholder="Konutun alış bedeli" value="${m.iktisap_bedeli || ''}"
                 onchange="updateMulk(${m.id},'iktisap_bedeli',this.value)"/>
        </div>` : ''}
      </div>`;
    c.appendChild(div);
  });
}

function updateMulk(id, field, value) {
  const m = state.mulkler.find(x => x.id === id);
  if (!m) return;
  m[field] = field === 'tur' ? value : (parseFloat(value) || 0);
  if (field === 'tur') renderMulkler();
}

/* ── Adım 3: Gider ────────────────────────────────────────────────────── */
function selectGider(method) {
  state.giderYontemi = method;
  ['goturu', 'gercek'].forEach(m => {
    const btn = $(`mc-${m}`);
    btn.classList.toggle('active', m === method);
    btn.querySelector('.method-chk').style.display = m === method ? 'inline-block' : 'none';
  });
  $('gercekPanel').style.display = method === 'gercek' ? 'block' : 'none';
}

/* ── Adım 4: Ücret ────────────────────────────────────────────────────── */
function toggleUcret(on) {
  state.ucretVar = on;
  $('ucretTxt').textContent = on ? 'Var' : 'Yok';
  $('ucretPanel').style.display = on ? 'block' : 'none';
  if (on && state.isverenler.length === 0) addIsveren(true);
  updateUcretEsikInfo();
}

function addIsveren(birinci = false) {
  const id = ++state.isvIdx;
  state.isverenler.push({ id, ad: '', brut_yillik: 0, stopaj: 0, birinci });
  renderIsverenler();
}

function removeIsveren(id) {
  state.isverenler = state.isverenler.filter(x => x.id !== id);
  renderIsverenler();
}

function updateIsveren(id, field, value) {
  const iv = state.isverenler.find(x => x.id === id);
  if (!iv) return;
  if (field === 'birinci') iv.birinci = value === 'true' || value === true;
  else if (field === 'ad') iv.ad = value;
  else iv[field] = parseFloat(value) || 0;
}

function renderIsverenler() {
  const c = $('isverenlerContainer');
  if (!c) return;
  c.innerHTML = '';

  state.isverenler.forEach((iv, idx) => {
    const div = document.createElement('div');
    div.className = 'mulk-card';
    div.innerHTML = `
      <div class="mulk-head">
        <span class="mulk-no" style="display:flex;align-items:center;gap:8px">
          İşveren #${idx + 1}
          ${iv.birinci ? '<span class="isveren-badge">1. İşveren</span>' : ''}
        </span>
        ${state.isverenler.length > 1 ? `<button class="btn-rem" onclick="removeIsveren(${iv.id})">✕ Sil</button>` : ''}
      </div>
      <div class="form-grid">
        <div class="fg">
          <label>İşveren Adı</label>
          <input type="text" placeholder="ABC Ltd." value="${iv.ad}"
                 onchange="updateIsveren(${iv.id},'ad',this.value)"/>
        </div>
        <div class="fg">
          <label>12 Aylık Brüt Ücret (TL) *</label>
          <small>Ocak–Aralık toplam, vergi öncesi bordro</small>
          <input type="number" placeholder="Yıllık brüt" value="${iv.brut_yillik || ''}"
                 onchange="updateIsveren(${iv.id},'brut_yillik',this.value)"/>
        </div>
        <div class="fg">
          <label>Yıl İçinde Kesilen Stopaj (TL) *</label>
          <small>Muhtasar beyanname ile ödenen vergi</small>
          <input type="number" placeholder="0" value="${iv.stopaj || ''}"
                 onchange="updateIsveren(${iv.id},'stopaj',this.value)"/>
        </div>
        <div class="fg">
          <label>İşveren Sırası</label>
          <small>En yüksek ücret aldığınız = 1. işveren</small>
          <div class="radio-group">
            <button class="rbtn ${iv.birinci ? 'active' : ''}"
                    onclick="updateIsveren(${iv.id},'birinci',true);renderIsverenler()">1. İşveren</button>
            <button class="rbtn ${!iv.birinci ? 'active' : ''}"
                    onclick="updateIsveren(${iv.id},'birinci',false);renderIsverenler()">2.+ İşveren</button>
          </div>
        </div>
      </div>`;
    c.appendChild(div);
  });
}

function updateUcretEsikInfo() {
  const el = $('ucretEsikInfo');
  if (!el) return;
  const esikMap = { 2025: 230000, 2026: 280000 };
  const esik = esikMap[state.year] || 230000;
  el.textContent = `📌 GVK Md.86: 2.+ işveren ücretleri toplamı ₺${esik.toLocaleString('tr-TR')}'yi aşarsa tüm ücretler beyan edilir.`;
}

/* ── Hesaplama ────────────────────────────────────────────────────────── */
async function hesaplaVeGoster() {
  const data = buildPayload();
  state.lastData = data;

  try {
    const res  = await fetch('/api/hesapla', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await res.json();

    if (!json.ok) {
      alert('Hesaplama hatası: ' + json.error);
      return;
    }

    state.lastResult = json.data;
    renderOzet(json.data);
    goStep(5);
  } catch (e) {
    alert('Sunucu bağlantı hatası: ' + e.message);
  }
}

function buildPayload() {
  return {
    year:          state.year,
    gider_yontemi: state.giderYontemi,
    mulkler:       state.mulkler.map(m => ({
      tur:            m.tur,
      gelir:          m.gelir,
      stopaj:         m.stopaj,
      hisse:          m.hisse,
      ay:             m.ay,
      iktisap_bedeli: m.iktisap_bedeli,
    })),
    gercek_gider: {
      aidat:      parseFloat($('g-aidat')?.value      || 0),
      sigorta:    parseFloat($('g-sigorta')?.value    || 0),
      vergiler:   parseFloat($('g-vergiler')?.value   || 0),
      amortisman: parseFloat($('g-amortisman')?.value || 0),
      diger:      parseFloat($('g-diger')?.value      || 0),
      kredi_faiz: parseFloat($('g-kredi')?.value      || 0),
    },
    ucret_var:  state.ucretVar,
    isverenler: state.isverenler.map(iv => ({
      ad:          iv.ad,
      brut_yillik: iv.brut_yillik,
      stopaj:      iv.stopaj,
      birinci:     iv.birinci,
    })),
    diger_gelirler: {
      msi:      parseFloat($('d-msi')?.value  || 0),
      dki:      parseFloat($('d-dki')?.value  || 0),
      faaliyet: $('faaliyetCb')?.checked || false,
    },
  };
}

/* ── Özet Render ─────────────────────────────────────────────────────── */
function renderOzet(d) {
  const year = d.year;

  // Uyarılar
  const wc = $('warnsContainer');
  wc.innerHTML = '';
  (d.warns || []).forEach(w => {
    const div = document.createElement('div');
    div.className = w.startsWith('💚') ? 'succ-box' : w.startsWith('ℹ️') ? 'info-box' : 'warn-box';
    div.innerHTML = w;
    wc.appendChild(div);
  });

  // Hero
  const isIade = d.iade > 0;
  $('resultHero').innerHTML = `
    <div class="rh-lbl">${isIade ? 'İade Edilecek Vergi' : 'Ödenecek Gelir Vergisi'}</div>
    <div class="rh-amount">${fmt(isIade ? d.iade : d.odeme)}</div>
    ${d.odeme > 0 ? `
    <div class="taksit-grid">
      <div class="taksit-card">
        <div class="tak-sub">1. Taksit + Damga</div>
        <div class="tak-date">31 Mart ${year + 1}</div>
        <div class="tak-amount">${fmt(d.taksit1 + d.damga)}</div>
      </div>
      <div class="taksit-card">
        <div class="tak-sub">2. Taksit</div>
        <div class="tak-date" style="color:#4ade80">31 Temmuz ${year + 1}</div>
        <div class="tak-amount">${fmt(d.taksit2)}</div>
      </div>
    </div>` : ''}`;

  // GMSİ Tablo
  const giderLbl = state.giderYontemi === 'goturu'
    ? 'Götürü Gider (%15)' : `Gerçek Gider${d.iktisap_acik || ''}`;

  $('gmsiCard').innerHTML = `
    <h3 class="sub-title">🏠 GMSİ Hesabı</h3>
    <table class="res-table"><tbody>
      ${tr('Konut Brüt Kira Geliri', fmt(d.konut_brut))}
      ${tr('İşyeri Kira Geliri (Stopajlı Brüt)', fmt(d.isyeri_s_brut))}
      ${tr('İşyeri Kira Geliri (Stopajsız)', fmt(d.isyeri_n_brut))}
      <tr class="divider"><td colspan="2"></td></tr>
      ${tr(`Mesken İstisnası (${year})`, d.istisna > 0 ? `– ${fmt(d.istisna)}` : 'Uygulanmadı', d.istisna > 0)}
      ${tr('Beyana Tabi GMSİ', fmt(d.toplam_gmsi_beyan))}
      <tr class="divider"><td colspan="2"></td></tr>
      ${tr(giderLbl, `– ${fmt(d.gmsi_gider)}`, true)}
      ${trTotal('GMSİ Vergi Matrahı', fmt(d.gmsi_matrah))}
    </tbody></table>`;

  // Ücret Tablo
  const uc = $('ucretCard');
  if (d.toplam_brut_ucret > 0) {
    uc.style.display = 'block';
    uc.innerHTML = `
      <h3 class="sub-title">👔 Ücret Hesabı</h3>
      ${!d.ucret_beyan_zorunlu ? `<div class="info-box">ℹ️ 2.+ işveren ücretleri beyan eşiğini aşmıyor. Beyana dahil edilmedi.</div>` : ''}
      <table class="res-table"><tbody>
        ${tr('Toplam Brüt Ücret (12 ay)', fmt(d.toplam_brut_ucret))}
        ${tr('Kesilen Ücret Stopajı', fmt(d.toplam_ucret_stopaj))}
        <tr class="divider"><td colspan="2"></td></tr>
        ${trTotal('Beyana Dahil Ücret Matrahı', fmt(d.ucret_matrah))}
      </tbody></table>`;
  } else {
    uc.style.display = 'none';
  }

  // Vergi Tablo
  $('vergCard').innerHTML = `
    <h3 class="sub-title">⚖ Toplam Vergi</h3>
    <table class="res-table"><tbody>
      ${tr('GMSİ Matrahı', fmt(d.gmsi_matrah))}
      ${d.ucret_matrah > 0 ? tr('Ücret Matrahı', fmt(d.ucret_matrah)) : ''}
      ${trTotal('Toplam Matrah', fmt(d.toplam_matrah))}
      <tr class="divider"><td colspan="2"></td></tr>
      ${tr('Hesaplanan Gelir Vergisi', fmt(d.hes_ver))}
      ${tr('Mahsup Stopaj', `– ${fmt(d.mahsup)}`, true)}
      <tr class="divider"><td colspan="2"></td></tr>
      ${trTotal('Ödenecek Vergi', fmt(d.odeme))}
      ${d.iade > 0 ? tr('İade Edilecek Vergi', fmt(d.iade), true) : ''}
      ${tr('Damga Vergisi', fmt(d.damga))}
    </tbody></table>`;

  // Takvim
  $('takvimCard').innerHTML = `
    <h3 class="sub-title">📅 Beyan ve Ödeme Takvimi</h3>
    <div class="takvim-grid">
      <div class="tak-item">
        <div class="tak-item-date">1–31 Mart ${year + 1}</div>
        <div class="tak-item-title">Beyanname</div>
        <div class="tak-item-desc">GİB Hazır Beyan Sistemi</div>
      </div>
      <div class="tak-item">
        <div class="tak-item-date">31 Mart ${year + 1}</div>
        <div class="tak-item-title">1. Taksit + Damga</div>
        <div class="tak-item-desc">Dijital Vergi Dairesi, GİB Mobil, Banka</div>
      </div>
      <div class="tak-item">
        <div class="tak-item-date">31 Temmuz ${year + 1}</div>
        <div class="tak-item-title">2. Taksit</div>
        <div class="tak-item-desc">Aynı ödeme kanalları</div>
      </div>
    </div>`;
}

function tr(label, value, green = false) {
  return `<tr class="${green ? 'green' : ''}">
    <td style="color:var(--muted)">${label}</td>
    <td>${value}</td>
  </tr>`;
}
function trTotal(label, value) {
  return `<tr class="total">
    <td>${label}</td><td>${value}
  </td></tr>`;
}

/* ── Export ──────────────────────────────────────────────────────────── */
async function exportFile(type) {
  if (!state.lastData) return;
  const btn = type === 'excel' ? $('btnExcel') : $('btnPdf');
  btn.disabled = true;
  btn.textContent = '⏳ Hazırlanıyor...';

  try {
    const res = await fetch(`/api/export/${type}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.lastData),
    });

    if (!res.ok) throw new Error('Sunucu hatası');

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `GMSI_Vergi_${state.year}.${type === 'excel' ? 'xlsx' : 'pdf'}`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('İndirme hatası: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = type === 'excel' ? '📊 Excel (.xlsx) İndir' : '📄 PDF İndir';
  }
}

/* ── Reset ────────────────────────────────────────────────────────────── */
function resetAll() {
  state.mulkler     = [];
  state.mulkIdx     = 0;
  state.isverenler  = [];
  state.isvIdx      = 0;
  state.ucretVar    = false;
  state.lastResult  = null;
  state.lastData    = null;
  state.giderYontemi = 'goturu';

  $('ucretVarCb').checked = false;
  toggleUcret(false);
  selectGider('goturu');

  goStep(0);
}

/* ── Init ─────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  addMulk('konut');
  updateUcretEsikInfo();
  goStep(0);
});
