/* ═══ v147 · THE FUNDS — every Direct-Growth scheme by AMFI category, ranked; a fund page with the chart, the
   macro DNA, the regime record and the shock simulator — what no fund site gives a fund ═══ */
(function (E) {
  const F = E.f;
  const FU = E.funds = { data: null, series: null, loaded: false, list: [], byCode: {}, cls: 'Equity', cat: null, code: null, pending: null };
  const CLASSES = ['Equity', 'Index', 'Hybrid', 'Debt', 'Global', 'Commodity'];
  FU.load = async function () {
    if (FU.loaded) return FU.data;
    if (FU.pending) return FU.pending;
    FU.pending = fetch(E.url('funds.json'), { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.json(); }).then(function (j) {
      FU.data = j; FU.list = []; FU.byCode = {};
      Object.keys(j.cats || {}).forEach(function (cat) { (j.cats[cat].rows || []).forEach(function (r) { r.cat = cat; r.cls = j.cats[cat].cls; FU.list.push(r); FU.byCode[r.code] = r; }); });
      FU.loaded = true; return j;
    }).catch(function (e) { console.warn('funds.json', e && e.message); FU.loaded = true; FU.data = null; return null; }).finally(function () { FU.pending = null; });
    return FU.pending;
  };
  FU.loadSeries = async function () { if (FU.series) return FU.series; try { const r = await fetch(E.url('funds_series.json'), { cache: 'no-store' }); if (r.ok) FU.series = (await r.json()).series || {}; } catch (e) { FU.series = {}; } return FU.series || {}; };
  FU.wcls = function (w) { return w === 'LEADER' ? 'buy' : w === 'LAGGARD' ? 'sell' : w ? 'hold' : 'none'; };
  FU.short = function (nm) { return String(nm || '').replace(/\s*-\s*Direct( Plan)?\s*-?\s*Growth( Option)?/i, '').replace(/\s*Direct( Plan)?\s*-?\s*Growth/i, '').replace(/\s+Fund$/i, ' Fund').trim(); };
  /* resolve a typed name to schemes (token overlap, best first) */
  FU.resolve = function (q, n) {
    const Q = String(q || '').toUpperCase().replace(/[^A-Z0-9 &]/g, ' ').split(/\s+/).filter(function (w) { return w && ['FUND', 'MUTUAL', 'PLAN', 'DIRECT', 'GROWTH', 'THE', 'IS', 'A', 'GOOD', 'SHOULD', 'I', 'BUY', 'SIP', 'IN', 'INVEST', 'MF', 'SCHEME', 'OPTION'].indexOf(w) < 0; });
    if (!Q.length) return [];
    const out = [];
    FU.list.forEach(function (r) {
      const nm = String(r.nm || '').toUpperCase(); let hit = 0;
      Q.forEach(function (w) { if (nm.indexOf(w) >= 0) hit += (w.length >= 4 ? 2 : 1); });
      if (hit) out.push({ code: r.code, nm: r.nm, cat: r.cat, score: hit * 100 + (r.score || 0) / 10 - (r.pending ? 50 : 0), row: r });
    });
    out.sort(function (a, b) { return b.score - a.score; });
    return out.slice(0, n || 8);
  };
  FU.catOf = function (q) { const U = String(q || '').toUpperCase(); const cats = Object.keys((FU.data || {}).cats || {}); return cats.find(function (c) { const C = c.toUpperCase().replace(/ \(.*\)/, ''); return U.indexOf(C) >= 0 || (C === 'ELSS' && /TAX SAV/.test(U)) || (C === 'LARGE CAP' && /BLUE ?CHIP/.test(U)); }) || null; };

  /* ── the tab ── */
  FU.renderTab = async function () {
    const el = document.getElementById('e-funds'); if (!el) return;
    el.innerHTML = '<div class="e-h2">Funds</div><div class="e-ans" style="margin-top:10px"><span class="e-spin"></span> loading the funds table…</div>';
    await FU.load();
    if (!FU.data) { el.innerHTML = '<div class="e-h2">Funds</div>' + E.notReady('The funds table'); return; }
    if (FU.code) { el.innerHTML = FU.page(FU.code); FU.afterPage(FU.code); return; }
    const D = FU.data; const cats = D.cats || {};
    if (!FU.cat || !cats[FU.cat]) { const first = Object.keys(cats).filter(function (c) { return cats[c].cls === FU.cls; }).sort(function (a, b) { return (cats[b].scored || 0) - (cats[a].scored || 0); })[0]; FU.cat = first || Object.keys(cats)[0]; FU.cls = cats[FU.cat] ? cats[FU.cat].cls : FU.cls; }
    let h = '<div class="e-between"><div><div class="e-h2">Funds</div><div class="e-sub">' + F.n(D.n_universe, 0) + ' Direct-Growth schemes across ' + Object.keys(cats).length + ' AMFI categories · ' + F.n(D.n_scored, 0) + ' scored' + (D.n_pending ? ' · ' + D.n_pending + ' awaiting history (the rotation fills them within a week)' : '') + ' · NAVs from AMFI · ' + F.esc(D.generated || '') + '</div></div></div>';
    h += '<div class="e-search" id="e-fund-search"><span class="ico">🔎</span><input class="e-input" type="text" placeholder="any fund — Parag Parikh Flexi, HDFC Mid Cap, SBI Gilt…" oninput="E.funds.suggest()" onkeydown="if(event.key===\'Enter\')E.funds.searchGo()"><button class="e-btn p sm go" onclick="E.funds.searchGo()">Open →</button><div class="e-sugg" id="e-fund-search-sugg"></div></div>';
    h += '<div class="subtabs" style="margin-top:12px">' + CLASSES.filter(function (c) { return Object.keys(cats).some(function (k) { return cats[k].cls === c; }); }).map(function (c) { return '<button class="subtab' + (FU.cls === c ? ' a' : '') + '" onclick="E.funds.cls=\'' + c + '\';E.funds.cat=null;E.funds.renderTab()">' + c + '</button>'; }).join('') + '</div>';
    h += '<div class="e-row" style="margin-top:8px;flex-wrap:wrap">' + Object.keys(cats).filter(function (k) { return cats[k].cls === FU.cls; }).sort().map(function (k) { return '<span class="e-chip' + (FU.cat === k ? ' a' : '') + '" onclick="E.funds.cat=\'' + F.esc(k) + '\';E.funds.renderTab()">' + F.esc(k) + ' <small style="color:var(--mut)">' + (cats[k].scored || 0) + '</small></span>'; }).join('') + '</div>';
    h += FU.table(FU.cat);
    h += '<div class="note" style="margin-top:12px">' + F.esc((D.how || {}).score || '') + ' · ' + F.esc((D.how || {}).source || '') + '</div>';
    el.innerHTML = h;
  };
  FU.table = function (cat) {
    const C = ((FU.data || {}).cats || {})[cat]; if (!C) return '';
    const med = C.median || {}; const reg = (FU.data || {}).regime || '';
    let h = E.sectionHead(F.esc(cat) + ' · ' + (C.scored || 0) + ' schemes ranked', 'category median: 1y ' + F.pct(med.r1y, 1) + ' · 3y ' + F.pct(med.r3y, 1) + ' a year · σ ' + F.n(med.vol, 1) + '% · worst drawdown ' + F.pct(med.dd, 1) + ' · LEADER = top fifth with a three-year record at or above the category · tap a fund');
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>#</th><th>fund</th><th>word</th><th style="text-align:right">score</th><th style="text-align:right">1 year</th><th style="text-align:right">3 years /yr</th><th style="text-align:right">σ</th><th style="text-align:right">drawdown</th><th style="text-align:right">in ' + F.esc(reg) + '</th><th style="text-align:right">NAV</th></tr></thead><tbody>' +
      (C.rows || []).map(function (r) { if (r.pending || r.r1y == null) return '<tr style="opacity:.55"><td>—</td><td>' + F.esc(FU.short(r.nm)) + '<div style="font-size:10px;color:var(--mut)">' + F.esc(r.amc || '') + ' · history arriving</div></td><td colspan="8" style="color:var(--mut)">awaiting NAV history</td></tr>'; return '<tr style="cursor:pointer" onclick="E.funds.open(\'' + F.esc(r.code) + '\')"><td>' + r.rank + '</td><td><b style="color:#fff">' + F.esc(FU.short(r.nm)) + '</b><div style="font-size:10px;color:var(--mut)">' + F.esc(r.amc || '') + '</div></td><td><span class="e-word ' + FU.wcls(r.word) + '">' + F.esc(r.word || '') + '</span></td><td style="text-align:right">' + (r.score != null ? Math.round(r.score) : '—') + '</td><td style="text-align:right" class="' + F.tone(r.r1y) + '">' + F.pct(r.r1y, 1) + '<div style="font-size:10px;color:var(--mut)">' + F.pct((r.vs_cat || {}).r1y, 1) + ' vs cat</div></td><td style="text-align:right" class="' + F.tone(r.r3y) + '">' + F.pct(r.r3y, 1) + '</td><td style="text-align:right">' + F.n(r.vol, 1) + '%</td><td style="text-align:right" class="e-dn">' + F.pct(r.dd, 1) + '</td><td style="text-align:right" class="' + F.tone(r.rfit) + '">' + (r.rfit != null ? F.pct(r.rfit, 1) : '—') + '</td><td style="text-align:right">' + F.n(r.nav, 2) + '<div style="font-size:10px;color:var(--mut)">' + F.esc(r.date || '') + '</div></td></tr>'; }).join('') + '</tbody></table></div>';
    return h;
  };
  FU.suggest = function () {
    const box = document.getElementById('e-fund-search'); if (!box) return; const q = box.querySelector('input').value.trim(); const out = document.getElementById('e-fund-search-sugg');
    if (!q) { out.classList.remove('show'); out.innerHTML = ''; return; }
    const R = FU.resolve(q, 8);
    out.innerHTML = R.length ? R.map(function (r, i) { return '<div class="it' + (i === 0 ? ' sel' : '') + '" onmousedown="E.funds.open(\'' + F.esc(r.code) + '\')"><div class="n">' + F.esc(FU.short(r.nm)) + '<small>' + F.esc(r.cat) + '</small></div><div class="sec">' + F.esc(r.row.word || '') + '</div><div class="px">' + (r.row.score != null ? Math.round(r.row.score) : '') + '</div></div>'; }).join('') : '<div class="it"><div class="n">no fund matches "' + F.esc(q) + '"</div></div>';
    out.classList.add('show');
  };
  FU.searchGo = function () { const box = document.getElementById('e-fund-search'); if (!box) return; const q = box.querySelector('input').value.trim(); const R = FU.resolve(q, 1); if (R.length) FU.open(R[0].code); else E.toast('no fund matches "' + q + '"'); };
  FU.open = async function (code) { await FU.load(); if (!FU.byCode[code]) { E.toast('fund not on the table'); return; } FU.code = code; if (E.tab !== 'funds') E.go('funds'); else FU.renderTab(); try { history.replaceState(null, '', '#funds/' + code); } catch (e) { } window.scrollTo({ top: 0 }); };
  FU.back = function () { FU.code = null; FU.renderTab(); };

  /* ── the fund page ── */
  FU.page = function (code) {
    const r = FU.byCode[code]; const D = FU.data; const C = (D.cats || {})[r.cat] || {}; const med = C.median || {}; const reg = D.regime || '';
    let h = '<div class="e-row" style="margin-bottom:8px"><button class="e-btn sm" onclick="E.funds.back()">← ' + F.esc(r.cat) + '</button><span style="font-size:11.5px;color:var(--mut)">' + F.esc(r.amc || '') + '</span></div>';
    h += '<div class="e-hero" style="padding:18px 0 10px"><div class="e-between"><div><div class="e-h1" style="font-size:26px;text-align:left">' + F.esc(FU.short(r.nm)) + '</div><div class="e-sub" style="text-align:left">' + F.esc(r.cat) + ' · ' + F.esc(r.cls || '') + ' · Direct plan, growth · NAV since ' + F.esc(r.since || '—') + ' · AMFI code ' + F.esc(r.code) + '</div></div><div style="text-align:right"><div class="e-mono" style="font-size:26px;color:#fff;font-weight:600">' + F.n(r.nav, 2) + '</div><div style="font-size:11px;color:var(--mut)">NAV · ' + F.esc(r.date || '') + '</div></div></div></div>';
    if (r.pending || r.r1y == null) return h + '<div class="e-empty">the NAV history for this scheme arrives with the rotation (every scheme within a week) — nothing to grade yet</div>';
    h += '<div class="e-verd" style="grid-template-columns:1fr 2fr"><div class="e-vc ' + FU.wcls(r.word) + '"><div class="h"><span>The word · within ' + F.esc(r.cat) + '</span><span>rank ' + r.rank + ' of ' + (C.scored || '—') + '</span></div><div class="w"><span class="e-word ' + FU.wcls(r.word) + ' big">' + F.esc(r.word || '') + '</span><span class="conv">score ' + Math.round(r.score || 0) + '/100</span></div><ul class="why">' + (r.why || []).map(function (w) { return '<li>' + F.esc(w) + '</li>'; }).join('') + '</ul></div>' +
      '<div class="e-vc none"><div class="h"><span>The numbers · against the category median</span></div><div class="e-kv" style="margin-top:10px">' + [['1 month', F.pct(r.r1m, 1), ''], ['3 months', F.pct(r.r3m, 1), ''], ['6 months', F.pct(r.r6m, 1), ''], ['1 year', F.pct(r.r1y, 1), 'median ' + F.pct(med.r1y, 1)], ['3 years a year', F.pct(r.r3y, 1), 'median ' + F.pct(med.r3y, 1)], ['Volatility (σ, annual)', F.n(r.vol, 1) + '%', 'median ' + F.n(med.vol, 1) + '%'], ['Worst 1-year drawdown', F.pct(r.dd, 1), 'median ' + F.pct(med.dd, 1)], ['Return per unit of risk', F.n(r.sharpe, 2), 'median ' + F.n(med.sharpe, 2)], ['In ' + F.esc(reg), (r.rfit != null ? F.pct(r.rfit, 1) + ' /yr vs cat' : '—'), 'the regime record']].map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div>' + (x[2] ? '<div class="s">' + x[2] + '</div>' : '') + '</div>'; }).join('') + '</div></div></div>';
    h += E.sectionHead('The chart', 'NAV · the full history from AMFI (via mfapi.in) when reachable, else three years weekly');
    h += '<div class="subtabs">' + [['1y', '1 year'], ['3y', '3 years'], ['max', 'Since inception']].map(function (x) { return '<button class="subtab' + ((FU.range || '3y') === x[0] ? ' a' : '') + '" onclick="E.funds.range=\'' + x[0] + '\';E.funds.drawChart(\'' + F.esc(code) + '\')">' + x[1] + '</button>'; }).join('') + '</div>';
    h += '<div class="e-chart" id="e-fu-chart"><canvas id="e-fu-cv"></canvas><div class="lg" id="e-fu-lg"></div></div>';
    h += E.sectionHead('Macro DNA', 'how this fund moves with the five things that move India — weekly NAV returns, the same ridge as every share · what no fund site shows');
    h += FU.dna(r);
    h += E.sectionHead('What if…', 'the shock presets on this fund, from its betas');
    h += FU.shocks(r);
    h += E.sectionHead('Its record by regime', 'average return, annualised, in each regime of the CPI × IIP path');
    h += FU.regime(r);
    h += E.sectionHead('Peers · ' + F.esc(r.cat), 'the category\'s top ten by score');
    h += '<div class="e-list">' + (C.rows || []).filter(function (x) { return !x.pending && x.r1y != null; }).slice(0, 10).map(function (x) { return '<div class="e-li' + (x.code === code ? ' a' : '') + '" onclick="E.funds.open(\'' + F.esc(x.code) + '\')"><div class="n"><span class="e-rank">' + x.rank + '</span>' + F.esc(FU.short(x.nm)) + '<small>' + F.esc(x.amc || '') + '</small></div><div><span class="e-word ' + FU.wcls(x.word) + '">' + F.esc(x.word) + '</span></div><div class="px">' + F.pct(x.r1y, 1) + '<small style="color:var(--dim)">1y · ' + F.pct(x.r3y, 1) + ' 3y</small></div></div>'; }).join('') + '</div>';
    h += E.sectionHead('Elsewhere', 'the factsheet and the news');
    h += '<div class="e-links">' + [['Google', 'https://www.google.com/search?q=' + encodeURIComponent(FU.short(r.nm) + ' direct growth')], ['Value Research', 'https://www.valueresearchonline.com/search/?q=' + encodeURIComponent(FU.short(r.nm))], ['Morningstar India', 'https://www.morningstar.in/search.aspx?q=' + encodeURIComponent(FU.short(r.nm))], ['AMFI', 'https://www.amfiindia.com/net-asset-value/nav-history'], ['mfapi (the NAV feed)', 'https://api.mfapi.in/mf/' + encodeURIComponent(r.code)]].map(function (x) { return '<a class="e-btn sm" target="_blank" rel="noopener" href="' + x[1] + '">' + x[0] + ' ↗</a>'; }).join('') + '</div>';
    h += '<div class="note" style="margin-top:12px">' + F.esc((D.how || {}).score || '') + ' Past NAVs; expense ratios and exit loads are on the factsheet, not here. Nothing on this page is a recommendation to buy a scheme.</div>';
    return h;
  };
  FU.dna = function (r) {
    const d = r.dna; if (!d) return '<div class="e-empty">not enough weekly history against the factors yet</div>';
    const b = d.b || {}, tt = d.t || {};
    const read = function (k, v) { if (k === 'nifty') return v >= 1.0 ? 'a high-beta fund' : v >= 0.7 ? 'moves with the market' : v >= 0.3 ? 'a low-beta fund' : 'barely tracks the index'; if (k === 'inr') return v > 0.2 ? 'gains when the rupee weakens (exporters, overseas assets)' : v < -0.2 ? 'hurt by a weaker rupee' : 'rupee-neutral'; if (k === 'brent') return v > 0.1 ? 'rises with crude' : v < -0.1 ? 'hurt by dearer crude' : 'crude-neutral'; if (k === 'rates') return v < -0.2 ? 'hurt by rising yields (rate-sensitive)' : v > 0.2 ? 'gains when yields rise' : 'rate-neutral'; if (k === 'vix') return v < -0.05 ? 'sells off when fear rises' : v > 0.05 ? 'holds up in fear' : 'indifferent to VIX'; return ''; };
    return '<div class="cd"><div class="e-grid e-g2"><div class="e-dna">' + ['nifty', 'inr', 'brent', 'rates', 'vix'].map(function (k) { const v = b[k]; const mx = k === 'nifty' ? 2 : 1; const pct = Math.max(-1, Math.min(1, (v || 0) / mx)); const left = pct >= 0 ? 50 : 50 + pct * 50; const w = Math.abs(pct) * 50; return '<div class="r"><div class="k">' + E.FACTOR[k] + '</div><div class="bar"><b></b><i style="left:' + left + '%;width:' + w + '%;background:' + ((v || 0) >= 0 ? 'var(--grn)' : 'var(--red)') + '"></i></div><div class="v">' + F.sgn(v, 2) + '</div><div class="t">t ' + F.n(tt[k], 1) + '</div></div>'; }).join('') + '<div style="font-size:11px;color:var(--mut);margin-top:6px">β = % move of the NAV per 1% move of the factor (weekly, ' + d.n + ' weeks, ridge) · R² ' + F.n(d.r2, 2) + '</div></div><div><div class="lbl">What it means</div><ul style="margin:4px 0 0 18px;font-size:12.5px;line-height:1.6;color:var(--tx)">' + ['nifty', 'inr', 'brent', 'rates', 'vix'].map(function (k) { return '<li><b>' + E.FACTOR_SHORT[k] + '</b> — ' + read(k, b[k] || 0) + (Math.abs(tt[k] || 0) < 1.5 ? ' <span style="color:var(--mut)">(weak)</span>' : '') + '</li>'; }).join('') + '</ul></div></div></div>';
  };
  FU.shocks = function (r) {
    const P = ((E.lite || {}).shock || {}).presets || {}; const b = (r.dna || {}).b; if (!b) return '<div class="e-empty">no betas yet</div>';
    const rows = Object.keys(P).map(function (k) { const p = P[k]; let d = 0; ['nifty', 'inr', 'brent', 'rates', 'vix'].forEach(function (f) { d += (b[f] || 0) * (p[f] || 0); }); return [p.label, d, p.nifty, p.note]; });
    return '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>shock</th><th style="text-align:right">this fund</th><th style="text-align:right">the Nifty</th><th>what it is</th></tr></thead><tbody>' + rows.map(function (x) { return '<tr><td><b style="color:#fff">' + F.esc(x[0]) + '</b></td><td style="text-align:right" class="' + F.tone(x[1]) + '"><b>' + F.pct(x[1], 1) + '</b></td><td style="text-align:right" class="' + F.tone(x[2]) + '">' + F.pct(x[2], 1) + '</td><td style="font-size:11px;color:var(--dim);white-space:normal">' + F.esc(x[3]) + '</td></tr>'; }).join('') + '</tbody></table></div>';
  };
  FU.regime = function (r) {
    const rg = r.regime || {}; const reg = (FU.data || {}).regime; if (!Object.keys(rg).length) return '<div class="e-empty">fewer than a year of weekly NAVs against the regime path</div>';
    return '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>regime</th><th style="text-align:right">a year, annualised</th><th style="text-align:right">weeks</th><th style="text-align:right">up weeks</th></tr></thead><tbody>' + ['Reflation', 'Goldilocks', 'Stagflation', 'Disinflation'].map(function (k) { const x = rg[k]; if (!x) return ''; return '<tr' + (k === reg ? ' style="background:rgba(78,161,255,.08)"' : '') + '><td>' + k + (k === reg ? ' <span class="e-tag">now</span>' : '') + '</td><td style="text-align:right" class="' + F.tone(x.ann) + '">' + F.pct(x.ann, 1) + '</td><td style="text-align:right">' + x.n + '</td><td style="text-align:right">' + (x.hit != null ? x.hit + '%' : '—') + '</td></tr>'; }).join('') + '</tbody></table></div>';
  };
  FU.afterPage = function (code) { FU.drawChart(code); };
  FU.drawChart = async function (code) {
    const cv = document.getElementById('e-fu-cv'); const lg = document.getElementById('e-fu-lg'); if (!cv) return;
    const rng = FU.range || '3y'; let pairs = null, src = '';
    try {
      const r = await fetch('https://api.mfapi.in/mf/' + encodeURIComponent(code), { cache: 'default' });
      if (r.ok) { const j = await r.json(); const rows = (j.data || []).slice().reverse(); pairs = rows.map(function (x) { const p = x.date.split('-'); return [Date.UTC(+p[2], +p[1] - 1, +p[0]) / 1000, +x.nav]; }).filter(function (p) { return p[1] > 0; }); src = 'AMFI via mfapi.in · daily'; }
    } catch (e) { pairs = null; }
    if (!pairs || pairs.length < 10) { const S = await FU.loadSeries(); const s = S[code]; if (s) { pairs = s.d.map(function (d, i) { return [E.series.dnum(d), s.v[i]]; }); src = 'the engine\'s weekly panel'; } }
    if (!pairs || !pairs.length) { if (lg) lg.textContent = 'no NAV series reachable'; return; }
    const n = rng === '1y' ? 260 : rng === '3y' ? 780 : pairs.length; const P = pairs.slice(-n);
    const v = P.map(function (p) { return p[1]; });
    E.chart.line(cv, [{ v: v, color: '#4ea1ff', w: 1.6, fill: 'rgba(78,161,255,.08)' }], { xl: E.series.xl(P, false), levels: [] });
    if (lg) lg.innerHTML = '<span>' + F.esc(src) + ' · ' + P.length + ' points</span><span>' + F.n(v[0], 2) + ' → ' + F.n(v[v.length - 1], 2) + ' (' + F.pct((v[v.length - 1] / v[0] - 1) * 100, 1) + ')</span>';
  };
  /* the home strip: the category leaders at a glance */
  FU.strip = function () {
    if (!FU.data) return '';
    const cats = FU.data.cats || {}; const pick = ['Large cap', 'Mid cap', 'Small cap', 'Flexi cap', 'ELSS (tax saver)', 'Gilt'].filter(function (c) { return cats[c] && (cats[c].leaders || []).length; });
    if (!pick.length) return '';
    return '<div class="cd" style="margin-top:14px"><div class="e-between"><div><div class="lbl" style="margin:0">Funds · the category leaders</div><div class="e-sub" style="margin-top:2px">' + pick.map(function (c) { const r = FU.byCode[cats[c].leaders[0]]; return '<b style="color:#fff">' + F.esc(c) + '</b>: <span style="cursor:pointer;color:var(--blu)" onclick="E.funds.open(\'' + F.esc(r.code) + '\')">' + F.esc(FU.short(r.nm)) + '</span> ' + F.pct(r.r1y, 0); }).join(' · ') + '</div></div><button class="e-btn sm" onclick="E.go(\'funds\')">every fund →</button></div></div>';
  };
})(window.E);
