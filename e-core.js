/* ═══════════════════════════════════════════════════════════════════════════
   MacroIntel v144 · E — the engine-driven front end
   One namespace. Reads engine.json (the lists) and engine_n<k>.json (a name in
   full) that engine.py writes every pass; every verdict on the page comes from
   there. Rides the page's existing live layer (liveQuotes / LIVE_Q / the feed).
   ═══════════════════════════════════════════════════════════════════════════ */
window.E = (function () {
  const E = { v: 'v146', lite: null, shards: {}, pending: {}, full: null, ready: false, t0: Date.now(), tab: 'home', sub: {}, watch: [] };
  const NOTE = {
    1: 'a long-term accumulate inside a short-term decline: wait for the short-term stop or horizon to clear, then buy',
    2: 'a trade, not an investment: the tape says buy for the horizon, the long-term case does not hold',
    3: 'the tape and the long-term case agree — buy, and the position can stay',
    4: 'nothing here for a buyer at any horizon',
    5: 'a short-term buy; no long-term view yet',
    6: 'a short-term sell; the long-term read is neutral',
    7: 'no short-term trade; accumulate for the year',
    8: 'no trade; avoid for the year',
    0: 'no position at any horizon — scored, watched, not traded',
    9: 'not scored: only a price and a day on file'
  };
  E.NOTE = NOTE;
  E.TAPE_KEYS = ['src', 'r1', 'r5', 'r20', 'r60', 'r120', 'r250', 'vs50', 'vs200', 'pos52', 'sig1d', 'sig5d', 'ext20', 'dd', 'hi52', 'lo52', 'm50', 'm200', 'vol_ratio', 'n'];
  E.SC_KEYS = ['short', 'long', 'intra', 'T', 'TL', 'M', 'ML', 'Q', 'F', 'C', 'R'];
  E.FACTOR = { nifty: 'the Nifty', inr: 'the rupee (USD/INR)', brent: 'Brent crude', rates: 'rates (10Y yields)', vix: 'India VIX' };
  E.FACTOR_SHORT = { nifty: 'Nifty', inr: 'Rupee', brent: 'Crude', rates: 'Rates', vix: 'VIX' };

  /* ── formatting ── */
  const F = {};
  F.n = function (x, d) { if (x == null || !isFinite(x)) return '—'; d = (d == null) ? (Math.abs(x) >= 1000 ? 0 : 2) : d; return Number(x).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d }); };
  F.inr = function (x, d) { if (x == null || !isFinite(x)) return '—'; return '₹' + F.n(x, d == null ? (Math.abs(x) >= 1000 ? 0 : 2) : d); };
  F.pct = function (x, d) { if (x == null || !isFinite(x)) return '—'; d = d == null ? 1 : d; return (x > 0 ? '+' : '') + Number(x).toFixed(d) + '%'; };
  F.sgn = function (x, d) { if (x == null || !isFinite(x)) return '—'; d = d == null ? 1 : d; return (x > 0 ? '+' : '') + Number(x).toFixed(d); };
  F.big = function (x) { if (x == null || !isFinite(x)) return '—'; const a = Math.abs(x); if (a >= 1e12) return '₹' + (x / 1e12).toFixed(2) + ' L cr'; if (a >= 1e7) return '₹' + (x / 1e7).toFixed(a >= 1e9 ? 0 : 1) + ' cr'; if (a >= 1e5) return '₹' + (x / 1e5).toFixed(1) + ' L'; return '₹' + F.n(x, 0); };
  F.cr = function (x) { if (x == null || !isFinite(x)) return '—'; return '₹' + (x >= 100 ? F.n(x, 0) : Number(x).toFixed(1)) + ' cr'; };
  F.tone = function (x) { return x == null ? 'e-flat' : x > 0 ? 'e-up' : x < 0 ? 'e-dn' : 'e-flat'; };
  F.esc = function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
  F.word = function (side, size) { const s = side || 'NONE'; const cls = s === 'BUY' ? 'buy' : s === 'SELL' ? 'sell' : s === 'ACCUMULATE' ? 'acc' : s === 'AVOID' ? 'avoid' : 'none'; const txt = s === 'NONE' ? 'NO TRADE' : s; return '<span class="e-word ' + cls + (size ? ' ' + size : '') + '">' + txt + '</span>'; };
  F.cls = function (side) { return side === 'BUY' ? 'buy' : side === 'SELL' ? 'sell' : side === 'ACCUMULATE' ? 'acc' : side === 'AVOID' ? 'avoid' : 'none'; };
  F.ago = function (ms) { if (!ms) return ''; const s = Math.max(0, Math.round((Date.now() - ms) / 1000)); if (s < 60) return s + 's ago'; const m = Math.round(s / 60); if (m < 60) return m + ' min ago'; const h = Math.round(m / 60); return h + ' h ago'; };
  F.ist = function (ms) { const d = new Date((ms || Date.now()) + (330 + new Date().getTimezoneOffset()) * 60000); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); };
  E.f = F;

  /* ── data ── */
  E.url = function (f) { const b = (location.protocol === 'file:') ? '' : ''; return b + f + '?t=' + Math.floor(Date.now() / 600000); };
  E.load = async function () {
    try {
      const r = await fetch(E.url('engine.json'), { cache: 'no-store' });
      if (!r.ok) throw new Error('http ' + r.status);
      E.lite = await r.json();
      E.ready = true;
    } catch (e) {
      console.warn('engine.json', e && e.message);
      E.lite = (window.ENGINE_LITE || null);
      E.ready = !!E.lite;
    }
    try { E.watch = JSON.parse(localStorage.getItem('mi_watch') || '[]'); } catch (e) { E.watch = []; }
    return E.ready;
  };
  E.shardOf = function (sym) { let s = 0; for (const c of String(sym)) s += c.charCodeAt(0); return s % 8; };
  E.decode = function (row) {
    if (!row || row.__d) return row;
    if (Array.isArray(row.tape)) { const t = {}; E.TAPE_KEYS.forEach(function (k, i) { t[k] = row.tape[i]; }); t.src = ['bhavcopy', 'weekly', 'daily'][t.src] || 'bhavcopy'; row.tape = t; }
    if (Array.isArray(row.sc)) { const s = {}; E.SC_KEYS.forEach(function (k, i) { s[k] = row.sc[i]; }); row.sc = s; }
    row.v = row.v || {}; row.__d = true; return row;
  };
  E.loadShard = function (k) {
    if (E.shards[k]) return Promise.resolve(E.shards[k]);
    if (!E.pending[k]) E.pending[k] = fetch(E.url('engine_n' + k + '.json'), { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.json(); }).then(function (j) { E.shards[k] = j.names || {}; return E.shards[k]; }).catch(function (e) { console.warn('shard', k, e && e.message); E.shards[k] = {}; return E.shards[k]; }).finally(function () { delete E.pending[k]; });
    return E.pending[k];
  };
  E.row = async function (sym) {
    sym = String(sym || '').toUpperCase(); if (!sym) return null;
    const k = E.shardOf(sym);
    await E.loadShard(k);
    const r = E.shards[k][sym]; if (!r) return null;
    return E.decode(r);
  };
  E.rowSync = function (sym) { const k = E.shardOf(sym); const r = E.shards[k] && E.shards[k][String(sym).toUpperCase()]; return r ? E.decode(r) : null; };
  E.lt = function (sym) { return (E.lite && E.lite.names && E.lite.names[String(sym || '').toUpperCase()]) || null; };
  E.note = function (code) { return NOTE[code] || NOTE[0]; };

  /* ── names: resolve anything typed to a symbol ── */
  const ALIAS = { 'HDFC BANK': 'HDFCBANK', 'ICICI BANK': 'ICICIBANK', 'KOTAK': 'KOTAKBANK', 'KOTAK BANK': 'KOTAKBANK', 'SBI': 'SBIN', 'STATE BANK': 'SBIN', 'L&T': 'LT', 'LARSEN': 'LT', 'M&M': 'M&M', 'MAHINDRA': 'M&M', 'BAJAJ FINANCE': 'BAJFINANCE', 'BAJAJ FINSERV': 'BAJAJFINSV', 'MARUTI': 'MARUTI', 'INFOSYS': 'INFY', 'RELIANCE': 'RELIANCE', 'AIRTEL': 'BHARTIARTL', 'BHARTI': 'BHARTIARTL', 'TATA MOTORS': 'TATAMOTORS', 'TATA STEEL': 'TATASTEEL', 'TATA POWER': 'TATAPOWER', 'TITAN': 'TITAN', 'ASIAN PAINTS': 'ASIANPAINT', 'HUL': 'HINDUNILVR', 'HINDUSTAN UNILEVER': 'HINDUNILVR', 'ITC': 'ITC', 'ULTRATECH': 'ULTRACEMCO', 'ZOMATO': 'ETERNAL', 'ETERNAL': 'ETERNAL', 'JIO': 'JIOFIN', 'JIO FINANCIAL': 'JIOFIN', 'ADANI PORTS': 'ADANIPORTS', 'ADANI ENT': 'ADANIENT', 'ADANI ENTERPRISES': 'ADANIENT', 'SUN PHARMA': 'SUNPHARMA', 'DR REDDY': 'DRREDDY', 'DR REDDYS': 'DRREDDY', 'HCL': 'HCLTECH', 'TECH MAHINDRA': 'TECHM', 'POWER GRID': 'POWERGRID', 'COAL INDIA': 'COALINDIA', 'ONGC': 'ONGC', 'NTPC': 'NTPC', 'AXIS': 'AXISBANK', 'AXIS BANK': 'AXISBANK', 'INDUSIND': 'INDUSINDBK', 'INDUSIND BANK': 'INDUSINDBK', 'BAJAJ AUTO': 'BAJAJ-AUTO', 'HERO': 'HEROMOTOCO', 'HERO MOTOCORP': 'HEROMOTOCO', 'EICHER': 'EICHERMOT', 'NESTLE': 'NESTLEIND', 'BRITANNIA': 'BRITANNIA', 'DIVIS': 'DIVISLAB', 'CIPLA': 'CIPLA', 'APOLLO': 'APOLLOHOSP', 'APOLLO HOSPITALS': 'APOLLOHOSP', 'GRASIM': 'GRASIM', 'JSW STEEL': 'JSWSTEEL', 'HINDALCO': 'HINDALCO', 'VEDANTA': 'VEDL', 'BPCL': 'BPCL', 'IOC': 'IOC', 'HPCL': 'HINDPETRO', 'GAIL': 'GAIL', 'SHRIRAM': 'SHRIRAMFIN', 'SHRIRAM FINANCE': 'SHRIRAMFIN', 'TRENT': 'TRENT', 'DMART': 'DMART', 'AVENUE': 'DMART', 'PIDILITE': 'PIDILITIND', 'HAVELLS': 'HAVELLS', 'SIEMENS': 'SIEMENS', 'ABB': 'ABB', 'BEL': 'BEL', 'HAL': 'HAL', 'BHEL': 'BHEL', 'IRCTC': 'IRCTC', 'IRFC': 'IRFC', 'RVNL': 'RVNL', 'LIC': 'LICI', 'SBI LIFE': 'SBILIFE', 'HDFC LIFE': 'HDFCLIFE', 'ICICI PRU': 'ICICIPRULI', 'ICICI LOMBARD': 'ICICIGI', 'PAYTM': 'PAYTM', 'NYKAA': 'NYKAA', 'POLICYBAZAAR': 'POLICYBZR', 'SWIGGY': 'SWIGGY', 'OLA': 'OLAELEC', 'OLA ELECTRIC': 'OLAELEC', 'RADICO': 'RADICO', 'RADICO KHAITAN': 'RADICO', 'CUPID': 'CUPID', 'TCS': 'TCS', 'WIPRO': 'WIPRO', 'LTIMINDTREE': 'LTIM', 'LTIM': 'LTIM', 'MPHASIS': 'MPHASIS', 'PERSISTENT': 'PERSISTENT', 'COFORGE': 'COFORGE', 'ZEE': 'ZEEL', 'DLF': 'DLF', 'GODREJ PROPERTIES': 'GODREJPROP', 'LODHA': 'LODHA', 'OBEROI': 'OBEROIRLTY', 'PRESTIGE': 'PRESTIGE', 'INDIGO': 'INDIGO', 'INTERGLOBE': 'INDIGO', 'VARUN': 'VBL', 'VARUN BEVERAGES': 'VBL', 'UNITED SPIRITS': 'UNITDSPR', 'MCDOWELL': 'UNITDSPR', 'UBL': 'UBL', 'UNITED BREWERIES': 'UBL', 'MANKIND': 'MANKIND', 'ZYDUS': 'ZYDUSLIFE', 'LUPIN': 'LUPIN', 'AUROBINDO': 'AUROPHARMA', 'TORRENT': 'TORNTPHARM', 'ALKEM': 'ALKEM', 'GLAND': 'GLAND', 'BIOCON': 'BIOCON', 'MAX': 'MAXHEALTH', 'MAX HEALTHCARE': 'MAXHEALTH', 'FORTIS': 'FORTIS', 'NIFTY': 'NIFTY', 'BANK NIFTY': 'BANKNIFTY', 'BANKNIFTY': 'BANKNIFTY', 'SENSEX': 'SENSEX' };
  E.ALIAS = ALIAS;
  E.resolve = function (q, n) {
    const Q = String(q || '').trim().toUpperCase().replace(/\.NS$|\.BO$/, '').replace(/\s+/g, ' ');
    if (!Q || !E.lite) return [];
    const N = E.lite.names; const out = []; const seen = {};
    const push = function (s, sc) { if (!N[s] || seen[s]) return; seen[s] = 1; out.push({ sym: s, nm: N[s].nm, sector: N[s].sector, px: N[s].px, d1: N[s].d1, turn: N[s].turn || 0, x: N[s].x || 'NSE', score: sc + Math.min(20, Math.log10((N[s].turn || 0.01) + 1) * 8) }); };
    if (ALIAS[Q]) push(ALIAS[Q], 1000);
    if (N[Q]) push(Q, 900);
    const Q2 = Q.replace(/[^A-Z0-9& ]/g, '');
    const words = Q2.split(' ').filter(Boolean);
    for (const s in N) {
      const nm = String(N[s].nm || '').toUpperCase();
      if (nm === Q) push(s, 800);
      else if (s.indexOf(Q2.replace(/ /g, '')) === 0 && Q2.length >= 2) push(s, 600 - (s.length - Q2.length) * 4);
      else if (nm.indexOf(Q) === 0) push(s, 500 - (nm.length - Q.length));
      else if (words.length && words.every(function (w) { return nm.indexOf(w) >= 0 || s.indexOf(w) >= 0; }) && Q.length >= 3) push(s, 300 - nm.length * 0.5);
      else if (Q.length >= 4 && (nm.indexOf(Q) > 0)) push(s, 150 - nm.length * 0.5);
      if (out.length > 400) break;
    }
    out.sort(function (a, b) { return b.score - a.score; });
    return out.slice(0, n || 8);
  };
  E.one = function (q) { const r = E.resolve(q, 1); return r.length ? r[0].sym : null; };

  /* ── live ── */
  const L = {};
  L.key = function (sym) { const S = String(sym).toUpperCase(); try { const n = E.lt(S); if (n && n.x === 'BSE' && n.code) return String(n.code) + '.BO'; } catch (e) { } if (S === 'NIFTY' || S === 'NIFTY 50') return '^NSEI'; if (S === 'BANKNIFTY' || S === 'BANK NIFTY') return '^NSEBANK'; if (S === 'SENSEX') return '^BSESN'; if (S === 'VIX' || S === 'INDIA VIX') return '^INDIAVIX'; if (S === 'USDINR') return 'INR=X'; if (S === 'BRENT') return 'BZ=F'; if (S.indexOf('^') === 0 || S.indexOf('=') >= 0) return S; return S + '.NS'; };
  L.q = function (sym) { try { const Q = window.LIVE_Q || {}; const q = Q[L.key(sym)]; if (q && q.p != null && (Date.now() - (q.t || 0)) < 36e5) return q; } catch (e) { } return null; };
  const IDX_TILE = { NIFTY: 'Nifty 50', BANKNIFTY: 'Bank Nifty', SENSEX: 'BSE Sensex', MIDCAP: 'Midcap 100' };
  L.tile = function (sym) { try { const S = String(sym).toUpperCase(); if (IDX_TILE[S] && typeof IN_IDX !== 'undefined' && IN_IDX[IDX_TILE[S]]) return IN_IDX[IDX_TILE[S]]; if (S === 'VIX' && typeof MACRO_X !== 'undefined' && MACRO_X.vix) return { p: MACRO_X.vix.v, d: null }; if (S === 'USDINR' && typeof FX !== 'undefined' && FX['USD/INR']) return FX['USD/INR']; if (S === 'BRENT' && typeof ENERGY !== 'undefined' && ENERGY['Brent Oil']) return ENERGY['Brent Oil']; } catch (e) { } return null; };
  L.px = function (sym) { const q = L.q(sym); if (q) return q.p; const n = E.lt(sym); if (n && n.px != null) return n.px; const t = L.tile(sym); if (t) return t.p; const M = (E.lite && E.lite.market) || {}; if (String(sym).toUpperCase() === 'NIFTY') return M.nifty; if (String(sym).toUpperCase() === 'VIX') return M.vix; return null; };
  L.d1 = function (sym) { const q = L.q(sym); if (q && q.d != null) return q.d; const n = E.lt(sym); if (n && n.d1 != null) return n.d1; const t = L.tile(sym); if (t && t.d != null) return t.d; const M = (E.lite && E.lite.market) || {}; if (String(sym).toUpperCase() === 'NIFTY') return M.nifty_d1; return null; };
  L.isLive = function (sym) { return !!L.q(sym); };
  L.state = function () { try { const n = (window.LIVE && (LIVE.head + LIVE.stk)) || 0; const src = window.LIVE && LIVE.src; const at = window.LIVE && LIVE.at; if (n && src && src !== 'feed') return { on: true, kind: 'door', label: 'live · updated ' + F.ago(at) + ' · ' + n + ' quotes · Yahoo (NSE ~15 min delayed)', at: at, n: n }; if (n && src === 'feed') return { on: true, kind: 'feed', label: 'the feed · updated ' + F.ago(at), at: at, n: n }; } catch (e) { } const door = (typeof NET_OK !== 'undefined') ? NET_OK : null; return { on: false, kind: 'none', label: door === false ? 'no live door — last close' : 'connecting…', at: 0, n: 0 }; };
  L.want = function (syms) { try { window.__LIVE_EXTRA = Array.from(new Set((window.__LIVE_EXTRA || []).concat((syms || []).map(L.key)))); } catch (e) { } };
  L.inHours = function () { try { return inMktHours(); } catch (e) { return false; } };
  L.chip = function () { const s = L.state(); return '<span class="e-live ' + (s.kind === 'door' ? 'on' : s.kind === 'feed' ? 'feed' : '') + '" data-live-chip><i></i>' + F.esc(s.label) + '</span>'; };
  L.refreshNow = function () { try { if (typeof liveRefresh === 'function') liveRefresh(true); } catch (e) { } };
  E.live = L;
  /* after every pass of the page's live loop, repaint every live number on screen */
  E.onLive = function () {
    try {
      document.querySelectorAll('[data-live-px]').forEach(function (el) { const s = el.getAttribute('data-live-px'); const p = L.px(s); if (p == null) return; const idx = /^(NIFTY|BANKNIFTY|SENSEX|VIX|MIDCAP)$/.test(String(s).toUpperCase()); const txt = idx ? F.n(p, s.toUpperCase() === 'VIX' ? 2 : 0) : F.inr(p); if (el.textContent !== txt) { el.textContent = txt; el.classList.remove('e-flash'); void el.offsetWidth; el.classList.add('e-flash'); } });
      document.querySelectorAll('[data-live-d]').forEach(function (el) { const s = el.getAttribute('data-live-d'); const d = L.d1(s); if (d == null) return; el.textContent = F.pct(d, 2); el.className = el.className.replace(/e-up|e-dn|e-flat/g, '').trim() + ' ' + F.tone(d); });
      document.querySelectorAll('[data-live-chip]').forEach(function (el) { el.outerHTML = L.chip(); });
      (E._liveHooks || []).forEach(function (fn) { try { fn(); } catch (e) { } });
    } catch (e) { console.warn('onLive', e && e.message); }
  };
  E.onLiveHook = function (fn) { E._liveHooks = E._liveHooks || []; E._liveHooks.push(fn); };

  /* ── navigation ── */
  E.go = function (tab, sub) {
    try { if (typeof sw === 'function') sw(null, tab); } catch (e) { }
    E.tab = tab;
    document.querySelectorAll('.e-nav .tab').forEach(function (b) { b.classList.toggle('a', b.getAttribute('data-tab') === tab); });
    document.querySelectorAll('#e-bnav button').forEach(function (b) { b.classList.toggle('a', b.getAttribute('data-t') === tab); });
    document.querySelectorAll('.e-more').forEach(function (m) { m.classList.remove('open'); });
    try { history.replaceState(null, '', '#' + tab + (sub ? '/' + sub : '')); } catch (e) { }
    if (tab === 'micro' && sub) E.markets.show(sub);
    if (tab === 'research' && sub) E.research.show(sub);
    window.scrollTo({ top: 0 });
    E.render(tab);
  };
  E.render = function (tab) {
    try {
      if (tab === 'home') E.home.render();
      else if (tab === 'micro') E.markets.render();
      else if (tab === 'research') E.research.render();
      else if (tab === 'industries') E.industry.renderTab();
      else if (tab === 'agents') E.arena.render();
      else if (tab === 'ask') E.ask.renderTab();
      else if (tab === 'macro') E.macro.render();
      E.macro.bar(tab);
    } catch (e) { console.warn('render', tab, e && e.message, e && e.stack); }
  };
  E.toast = function (msg, ms) { try { let t = document.getElementById('e-toast'); if (!t) { t = document.createElement('div'); t.id = 'e-toast'; t.className = 'e-toast'; document.body.appendChild(t); } t.textContent = msg; t.style.display = 'block'; clearTimeout(E._tt); E._tt = setTimeout(function () { t.style.display = 'none'; }, ms || 2200); } catch (e) { } };
  E.copy = function (txt) { try { navigator.clipboard.writeText(txt); E.toast('copied'); } catch (e) { E.toast('could not copy'); } };

  /* ── the search box (one component, used everywhere) ── */
  E.searchBox = function (id, placeholder, big) {
    return '<div class="e-search" id="' + id + '"><span class="ico">🔎</span><input class="e-input" type="text" autocomplete="off" spellcheck="false" placeholder="' + F.esc(placeholder || 'any share — ITC, Radico, HDFC Bank, a sector…') + '" oninput="E.suggest(\'' + id + '\')" onkeydown="E.searchKey(event,\'' + id + '\')" onfocus="E.suggest(\'' + id + '\')"><button class="e-btn p sm go" onclick="E.searchGo(\'' + id + '\')">Verdict →</button><div class="e-sugg" id="' + id + '-sugg"></div></div>';
  };
  E.suggest = function (id) {
    const box = document.getElementById(id); if (!box) return; const inp = box.querySelector('input'); const out = document.getElementById(id + '-sugg');
    const q = inp.value.trim(); if (!q) { out.classList.remove('show'); out.innerHTML = ''; return; }
    const R = E.resolve(q, 8); const S = E.industry.find(q);
    let h = '';
    if (S.length) h += S.slice(0, 2).map(function (s) { return '<div class="it" onmousedown="E.industry.open(\'' + F.esc(s) + '\');E.hideSugg(\'' + id + '\')"><div class="n">' + F.esc(s) + '<small>industry</small></div><div class="sec">' + F.esc((E.lite.sectors[s] || {}).word || '') + '</div><div class="px"></div></div>'; }).join('');
    h += R.map(function (r, i) { return '<div class="it' + (i === 0 && !S.length ? ' sel' : '') + '" onmousedown="E.openShare(\'' + F.esc(r.sym) + '\');E.hideSugg(\'' + id + '\')"><div class="n">' + F.esc(r.nm) + '<small>' + F.esc(r.sym) + (r.x === 'BSE' ? ' · BSE' : '') + '</small></div><div class="sec">' + F.esc(r.sector || '') + '</div><div class="px">' + F.inr(L.px(r.sym)) + '<br><span class="' + F.tone(L.d1(r.sym)) + '">' + F.pct(L.d1(r.sym), 2) + '</span></div></div>'; }).join('');
    if (!h) h = '<div class="it"><div class="n">Nothing listed as "' + F.esc(q) + '"</div></div>';
    out.innerHTML = h; out.classList.add('show');
  };
  E.hideSugg = function (id) { const out = document.getElementById(id + '-sugg'); if (out) setTimeout(function () { out.classList.remove('show'); }, 120); };
  E.searchKey = function (ev, id) { if (ev.key === 'Enter') { ev.preventDefault(); E.searchGo(id); } if (ev.key === 'Escape') E.hideSugg(id); };
  E.searchGo = function (id) {
    const box = document.getElementById(id); const inp = box && box.querySelector('input'); const q = inp ? inp.value.trim() : ''; if (!q) return;
    const S = E.industry.find(q); const R = E.resolve(q, 1);
    const exactInd = S.length && S[0].toUpperCase() === q.toUpperCase();
    if (exactInd || (S.length && !R.length)) { E.industry.open(S[0]); }
    else if (R.length) { E.openShare(R[0].sym); }
    else E.toast('Nothing listed as "' + q + '"');
    E.hideSugg(id);
  };
  document.addEventListener('click', function (ev) { try { if (!ev.target.closest('.e-search')) document.querySelectorAll('.e-sugg.show').forEach(function (o) { o.classList.remove('show'); }); if (!ev.target.closest('.e-more')) document.querySelectorAll('.e-more.open').forEach(function (o) { o.classList.remove('open'); }); } catch (e) { } });
  document.addEventListener('keydown', function (ev) { try { if (ev.key === '/' && !ev.target.closest('input,textarea')) { ev.preventDefault(); const i = document.querySelector('.tp.a .e-search input') || document.querySelector('.e-search input'); if (i) { i.focus(); i.select(); } } } catch (e) { } });

  /* ── watchlist ── */
  E.watchHas = function (s) { return E.watch.indexOf(String(s).toUpperCase()) >= 0; };
  E.watchToggle = function (s) { s = String(s).toUpperCase(); const i = E.watch.indexOf(s); if (i >= 0) E.watch.splice(i, 1); else E.watch.unshift(s); try { localStorage.setItem('mi_watch', JSON.stringify(E.watch.slice(0, 60))); } catch (e) { } E.toast(i >= 0 ? s + ' removed from My list' : s + ' added to My list'); try { document.querySelectorAll('[data-watch="' + s + '"]').forEach(function (b) { b.textContent = E.watchHas(s) ? '★ On my list' : '☆ Add to my list'; }); } catch (e) { } };

  /* ── a small canvas line chart ── */
  E.chart = {};
  E.chart.line = function (cv, series, opt) {
    try {
      opt = opt || {}; const dpr = window.devicePixelRatio || 1; const W = cv.clientWidth || 600, H = cv.clientHeight || 300; cv.width = W * dpr; cv.height = H * dpr; const c = cv.getContext('2d'); c.scale(dpr, dpr); c.clearRect(0, 0, W, H);
      const pl = 8, pr = 58, pt = 12, pb = 24; const iw = W - pl - pr, ih = H - pt - pb;
      let ys = []; series.forEach(function (s) { (s.v || []).forEach(function (p) { if (p != null && isFinite(p)) ys.push(p); }); }); (opt.levels || []).forEach(function (l) { if (l.y != null) ys.push(l.y); }); if (opt.band) ys.push(opt.band[0], opt.band[1]);
      if (!ys.length) { c.fillStyle = '#8d99aa'; c.font = '12px IBM Plex Sans'; c.fillText(opt.empty || 'no data', pl + 10, H / 2); return; }
      let lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys); if (hi === lo) { hi += 1; lo -= 1; } const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
      const n = Math.max.apply(null, series.map(function (s) { return (s.v || []).length; })); const x = function (i, len) { return pl + (len > 1 ? i / (len - 1) : 0.5) * iw; }; const y = function (v) { return pt + (1 - (v - lo) / (hi - lo)) * ih; };
      /* grid */
      c.strokeStyle = 'rgba(255,255,255,.06)'; c.lineWidth = 1; c.fillStyle = '#5d6878'; c.font = '10px IBM Plex Mono';
      for (let g = 0; g <= 4; g++) { const v = lo + (hi - lo) * g / 4; const yy = y(v); c.beginPath(); c.moveTo(pl, yy); c.lineTo(pl + iw, yy); c.stroke(); c.fillText(F.n(v, v < 100 ? 2 : 0), pl + iw + 6, yy + 3); }
      /* band */
      if (opt.band) { c.fillStyle = opt.bandColor || 'rgba(78,161,255,.08)'; c.fillRect(pl, y(opt.band[1]), iw, y(opt.band[0]) - y(opt.band[1])); }
      /* x labels */
      if (opt.xl && opt.xl.length) { c.fillStyle = '#5d6878'; const step = Math.max(1, Math.round(opt.xl.length / Math.min(6, Math.floor(iw / 80)))); for (let i = 0; i < opt.xl.length; i += step) { const xx = x(i, opt.xl.length); c.fillText(String(opt.xl[i]), Math.min(xx, pl + iw - 40), H - 8); } }
      /* series */
      series.forEach(function (s) { const v = s.v || []; if (!v.length) return; c.beginPath(); c.strokeStyle = s.color || '#4ea1ff'; c.lineWidth = s.w || 1.6; c.setLineDash(s.dash || []); let started = false; for (let i = 0; i < v.length; i++) { if (v[i] == null || !isFinite(v[i])) continue; const xx = x(i, v.length), yy = y(v[i]); if (!started) { c.moveTo(xx, yy); started = true; } else c.lineTo(xx, yy); } c.stroke(); c.setLineDash([]); if (s.fill) { c.lineTo(x(v.length - 1, v.length), pt + ih); c.lineTo(x(0, v.length), pt + ih); c.closePath(); c.fillStyle = s.fill; c.fill(); } });
      /* levels */
      (opt.levels || []).forEach(function (l) { if (l.y == null) return; const yy = y(l.y); c.beginPath(); c.strokeStyle = l.color || '#8d99aa'; c.lineWidth = 1; c.setLineDash(l.dash || [4, 4]); c.moveTo(pl, yy); c.lineTo(pl + iw, yy); c.stroke(); c.setLineDash([]); c.fillStyle = l.color || '#8d99aa'; c.font = '10px IBM Plex Mono'; c.fillText(l.label || '', pl + 4, yy - 3); });
      /* last point */
      const main = series[0]; if (main && main.v && main.v.length) { let li = main.v.length - 1; while (li >= 0 && (main.v[li] == null)) li--; if (li >= 0) { const xx = x(li, main.v.length), yy = y(main.v[li]); c.beginPath(); c.fillStyle = main.color || '#4ea1ff'; c.arc(xx, yy, 3, 0, Math.PI * 2); c.fill(); } }
    } catch (e) { console.warn('chart', e && e.message); }
  };
  E.chart.spark = function (vals, w, h, color) { try { const cv = document.createElement('canvas'); const dpr = window.devicePixelRatio || 1; cv.width = w * dpr; cv.height = h * dpr; cv.style.width = w + 'px'; cv.style.height = h + 'px'; const c = cv.getContext('2d'); c.scale(dpr, dpr); const v = (vals || []).filter(function (x) { return x != null && isFinite(x); }); if (v.length < 2) return cv; const lo = Math.min.apply(null, v), hi = Math.max.apply(null, v); c.beginPath(); c.strokeStyle = color || (v[v.length - 1] >= v[0] ? '#2fd27d' : '#ff5c5c'); c.lineWidth = 1.3; v.forEach(function (p, i) { const x = i / (v.length - 1) * (w - 2) + 1, y = h - 1 - (hi === lo ? h / 2 : (p - lo) / (hi - lo) * (h - 2)); if (i) c.lineTo(x, y); else c.moveTo(x, y); }); c.stroke(); return cv; } catch (e) { return document.createElement('span'); } };

  /* ── series for the charts: the door (Yahoo through the worker), the feed, the page's history ── */
  E.series = { shards: {}, pending: {} };
  E.series.shard = function (k) { if (E.series.shards[k]) return Promise.resolve(E.series.shards[k]); if (!E.series.pending[k]) E.series.pending[k] = fetch(E.url('engine_s' + k + '.json'), { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.json(); }).then(function (j) { E.series.shards[k] = j; return j; }).catch(function () { E.series.shards[k] = { names: {} }; return E.series.shards[k]; }).finally(function () { delete E.series.pending[k]; }); return E.series.pending[k]; };
  E.series.engine = async function (sym, range) {
    /* the engine's own panel: weekly closes for every name (3 years online), daily for the most traded */
    try {
      const S = String(sym).toUpperCase(); const j = await E.series.shard(E.shardOf(S)); const r = (j.names || {})[S]; if (!r) return null;
      if (range !== '5y' && r.d && r.d.length > 30) { const pairs = []; (j.ddates || []).forEach(function (d, i) { if (r.d[i] != null) pairs.push([E.series.dnum(d), r.d[i]]); }); if (pairs.length > 30) return { pairs: pairs, src: 'the engine\'s daily panel (one year)', live: false }; }
      if (r.w && r.w.length > 8) { const pairs = []; (j.wdates || []).forEach(function (d, i) { if (r.w[i] != null) pairs.push([E.series.dnum(d), r.w[i]]); }); if (pairs.length > 8) { const yrs = Math.round(pairs.length / 52 * 10) / 10; return { pairs: pairs, src: 'the engine\'s weekly panel (' + (yrs >= 2 ? yrs + ' years' : 'one year') + ')', live: false, weekly: true }; } }
    } catch (e) { }
    return null;
  };
  E.series.get = async function (sym, range) {
    const key = L.key(sym);
    if (range === '1d') {
      try { if (typeof yqNet === 'function' && typeof _chartUrl === 'function') { const q = await yqNet(_chartUrl(key, '1d', '1m')); if (q && q.pairs && q.pairs.length > 3) return { pairs: q.pairs, prev: q.prev, src: 'live · 1-minute bars', live: true }; } } catch (e) { }
      try { if (typeof feedBars === 'function') { const q = await feedBars(key); if (q && q.pairs && q.pairs.length > 3) return { pairs: q.pairs, prev: q.prev, src: 'the feed · 5-minute bars', live: true }; } } catch (e) { }
      try { const B = (window.LIVE_BARS || {})[key]; if (B && B.pairs && B.pairs.length > 3) return { pairs: B.pairs, prev: B.prev, src: 'live · 5-minute bars', live: true }; } catch (e) { }
      return null;
    }
    const want = range === '5y' ? ['5y', '1wk'] : ['1y', '1d'];
    try { if (typeof yqNet === 'function' && typeof _chartUrl === 'function') { const q = await yqNet(_chartUrl(key, want[0], want[1])); if (q && q.pairs && q.pairs.length > 20) return { pairs: q.pairs, src: 'Yahoo · ' + (range === '5y' ? 'five years, weekly' : 'one year, daily'), live: false, weekly: range === '5y' }; } } catch (e) { }
    const eng = await E.series.engine(sym, range); if (eng) return eng;
    try {
      const H = (typeof HIST !== 'undefined' && HIST) ? HIST : (window.HIST || null); if (H) {
        const S = H.series && (H.series[key] || H.series[String(sym).toUpperCase() + '.NS']);
        if (S && range !== '5y') { const pairs = []; (H.dates || []).forEach(function (d, i) { if (S[i] != null) pairs.push([E.series.dnum(d), S[i]]); }); if (pairs.length > 20) return { pairs: pairs, src: 'the page\'s daily history', live: false }; }
        const Wd = H.wide && (H.wide[key] || H.wide[String(sym).toUpperCase() + '.NS']);
        if (Wd) { const pairs = []; (H.wdates || []).forEach(function (d, i) { if (Wd[i] != null) pairs.push([E.series.dnum(d), Wd[i]]); }); if (pairs.length > 8) return { pairs: pairs, src: 'the page\'s weekly history (one year)', live: false, weekly: true }; }
      }
    } catch (e) { }
    return null;
  };
  E.series.dnum = function (d) { const s = String(d); if (/^\d{8}$/.test(s)) return Math.floor(Date.UTC(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8)) / 1000); const t = Date.parse(s); return isFinite(t) ? Math.floor(t / 1000) : 0; };
  E.series.xl = function (pairs, intraday) { return pairs.map(function (p) { const d = new Date(p[0] * 1000 + (intraday ? (330 + new Date().getTimezoneOffset()) * 60000 : 0)); return intraday ? (String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0')) : (['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getUTCMonth()] + ' ' + String(d.getUTCFullYear()).slice(2)); }); };
  E.series.sma = function (v, n) { const o = []; let s = 0; const q = []; for (let i = 0; i < v.length; i++) { const x = v[i]; if (x == null) { o.push(null); continue; } q.push(x); s += x; if (q.length > n) s -= q.shift(); o.push(q.length === n ? s / n : null); } return o; };

  return E;
})();
