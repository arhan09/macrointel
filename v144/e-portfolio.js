/* ═══ v145 · THE PORTFOLIO X-RAY — paste your holdings; the whole book under the macro ═══
   Nobody shows a retail holder what their book is made of: its beta to the Nifty, the rupee, crude, rates and
   VIX; what a shock costs in rupees; which holdings the engine would sell today and where the money would go.
   Everything here is computed in the browser from the engine's rows and the live price; the holdings never
   leave this browser (localStorage 'mi_portfolio'). */
(function (E) {
  const F = E.f, L = E.live;
  const PF = E.pf = { rows: [], loaded: false, name: '' };
  const FACTORS = ['nifty', 'inr', 'brent', 'rates', 'vix'];

  /* ── storage ── */
  PF.load = function () { if (PF.loaded) return PF.rows; try { PF.rows = JSON.parse(localStorage.getItem('mi_portfolio') || '[]'); PF.name = localStorage.getItem('mi_portfolio_name') || ''; } catch (e) { PF.rows = []; } PF.loaded = true; return PF.rows; };
  PF.save = function () { try { localStorage.setItem('mi_portfolio', JSON.stringify(PF.rows)); localStorage.setItem('mi_portfolio_name', PF.name || ''); } catch (e) { E.toast('could not save in this browser'); } };
  PF.has = function (sym) { PF.load(); const S = String(sym || '').toUpperCase(); for (const r of PF.rows) if (r.sym === S) return r; return null; };
  PF.clear = function () { if (!confirm('Remove the saved portfolio from this browser?')) return; PF.rows = []; PF.save(); E.toast('portfolio cleared'); PF.rerender(); };

  /* ── the decision for a holder: one rule for Ask, the research page and the X-ray ──
     HOLD exists only for a holder; the two horizons decide */
  E.decide = function (vs, vl, px, stopL) {
    vs = vs || {}; vl = vl || {};
    const S = Math.round(vs.score || 0), Lg = Math.round(vl.score || 0);
    if (vl.side === 'AVOID' && vs.side === 'SELL') return { word: 'SELL', cls: 'sell', act: 'SELL', lead: 'Both horizons are against it: the tape is a short-term SELL (' + S + '/100) and the twelve-month case reads AVOID (' + Lg + '/100). Sell it; if you want to stagger, sell half now and the rest on any bounce toward ' + F.inr(vs.stop) + '.' };
    if (vl.side === 'AVOID' && vs.side === 'BUY') return { word: 'SELL INTO STRENGTH', cls: 'avoid', act: 'SELL', lead: 'The tape is bid for a few weeks (short-term BUY, ' + S + '/100) but the year does not hold (AVOID, ' + Lg + '/100). Use the bounce: book on the way to ' + F.inr(vs.target) + ' and be out by then.' };
    if (vl.side === 'AVOID') return { word: 'SELL', cls: 'sell', act: 'SELL', lead: 'The twelve-month case reads AVOID (' + Lg + '/100): ' + (vl.why || []).slice(0, 2).join('; ') + '. No short-term reason to wait. Sell, or at the very least sell half and keep a stop at ' + F.inr(stopL) + ' on the rest.' };
    if (vl.side === 'ACCUMULATE' && vs.side === 'SELL') return { word: 'HOLD · DON\'T ADD', cls: 'hold', act: 'HOLD', lead: 'The year is on your side (ACCUMULATE, ' + Lg + '/100) but the next weeks are not (short-term SELL). Keep it, do not add yet, and treat ' + F.inr(stopL) + ' (' + (vl.stop_note || 'the 200-day') + ') as the line that ends the case. Add once the short-term read clears.' };
    if (vl.side === 'ACCUMULATE') return { word: vs.side === 'BUY' ? 'HOLD · ADD' : 'HOLD', cls: vs.side === 'BUY' ? 'buy' : 'acc', act: vs.side === 'BUY' ? 'ADD' : 'HOLD', lead: 'Keep it. The twelve-month case is an ACCUMULATE (' + Lg + '/100) with a target of ' + F.inr(vl.target) + ' (' + F.pct(vl.exp_pct, 0) + ')' + (vs.side === 'BUY' ? ', and the tape agrees for the next weeks — adding here is in order, with a stop at ' + F.inr(vs.stop) + ' on the new piece.' : '.') + ' The exit for the whole position is a close below ' + F.inr(stopL) + '.' };
    if (vs.side === 'SELL') return { word: 'SELL HALF', cls: 'sell', act: 'SELL_HALF', lead: 'The short-term read is SELL (' + S + '/100) and there is no long-term case to lean on (' + Lg + '/100). Sell half now; hold the rest with a stop at ' + F.inr(vs.stop) + ' and let the market decide.' };
    if (vs.side === 'BUY') return { word: 'HOLD WITH A STOP', cls: 'buy', act: 'HOLD', lead: 'The next weeks read BUY (' + S + '/100) with a target of ' + F.inr(vs.target) + '; the twelve-month case is not made yet (' + Lg + '/100). Hold it as a trade: stop ' + F.inr(vs.stop) + ', book at the target or after ' + vs.h + ' sessions.' };
    return { word: 'HOLD WITH A STOP', cls: 'hold', act: 'HOLD', lead: 'Neither horizon has a strong view (short ' + S + ', long ' + Lg + ' out of 100). There is no reason to sell today and no reason to add. Keep it with a stop at ' + F.inr(stopL) + ' (' + (vl.stop_note || 'the 200-day') + ') and revisit when a score crosses a bar.' };
  };

  /* ── the parser: plain lines, a Zerodha / Groww / Upstox export, any CSV with a symbol, a quantity, an average ── */
  const num = function (x) { if (x == null) return null; const v = parseFloat(String(x).replace(/[₹,\s]/g, '').replace(/^rs\.?/i, '')); return isFinite(v) ? v : null; };
  const splitCSV = function (ln, sep) { const out = []; let cur = '', q = false; for (let i = 0; i < ln.length; i++) { const c = ln[i]; if (c === '"') { q = !q; continue; } if (c === sep && !q) { out.push(cur); cur = ''; continue; } cur += c; } out.push(cur); return out.map(function (s) { return s.trim(); }); };
  PF.resolve = function (txt) {
    const T = String(txt || '').trim().toUpperCase().replace(/\.NS$|\.BO$|-EQ$|-BE$|-BZ$|-SM$/, '').replace(/\s+/g, ' ');
    if (!T) return null;
    if (E.ALIAS[T] && E.lt(E.ALIAS[T])) return E.ALIAS[T];
    if (E.lt(T)) return T;
    const r = E.resolve(T, 1);
    if (r.length && (r[0].score >= 500 || (T.length >= 5 && r[0].score >= 300))) return r[0].sym;
    return null;
  };
  PF.parse = function (text) {
    const lines = String(text || '').split(/\r?\n/).map(function (s) { return s.trim(); }).filter(Boolean);
    if (!lines.length) return [];
    const sep = lines[0].indexOf('\t') >= 0 ? '\t' : (lines[0].split(',').length >= 3 ? ',' : null);
    let head = null, start = 0, iS = -1, iQ = -1, iA = -1;
    if (sep) {
      const h = splitCSV(lines[0], sep).map(function (s) { return s.toLowerCase(); });
      iS = h.findIndex(function (x) { return /tradingsymbol|instrument|^symbol|scrip|stock name|^stock$|^name$|company/.test(x); });
      iQ = h.findIndex(function (x) { return /^qty\.?$|quantity|^qty|shares|units|^net qty/.test(x); });
      iA = h.findIndex(function (x) { return /avg|average|buy price|cost|purchase/.test(x); });
      if (iS >= 0 && iQ >= 0) { head = h; start = 1; }
    }
    const out = []; const seen = {};
    for (let i = start; i < lines.length; i++) {
      const ln = lines[i]; let sym = null, qty = null, cost = null, raw = ln;
      if (head) {
        const c = splitCSV(ln, sep); raw = c[iS]; qty = num(c[iQ]); cost = iA >= 0 ? num(c[iA]) : null;
        sym = PF.resolve(c[iS]);
      } else {
        /* "RELIANCE 50 2400" · "50 Cupid at 180" · "ITC x 200 @ 410" · "TCS, 10, 3500" · "Radico Khaitan 25" */
        const t = ln.replace(/[,|;\t]+/g, ' ').replace(/\s+/g, ' ');
        const numRe = /(?:₹|rs\.?\s*)?-?\d[\d,]*(?:\.\d+)?/gi;
        const nums = (t.match(numRe) || []).map(function (x) { return num(x); }).filter(function (v) { return v != null; });
        const words = t.replace(numRe, ' ').replace(/\b(at|x|avg|average|cost|shares?|stocks?|qty|of|units?|price|buy|bought|hold|holding|have|i|my|nos?|rs|inr)\b|@|₹/gi, ' ').replace(/\s+/g, ' ').trim();
        if (!words || !nums.length) { if (words) out.push({ raw: ln, sym: null, qty: null, cost: null }); continue; }
        qty = nums[0]; cost = nums.length > 1 ? nums[1] : null;
        if (nums.length > 1 && !Number.isInteger(nums[0]) && Number.isInteger(nums[1])) { qty = nums[1]; cost = nums[0]; }
        raw = words; sym = PF.resolve(words);
      }
      if (!qty || qty <= 0) continue;
      if (!sym) {
        /* v147 · a mutual fund? (Zerodha Coin / Groww exports name the scheme) */
        let fr = null; try { if (E.funds && E.funds.loaded && String(raw).length >= 6) { const R = E.funds.resolve(raw, 1); if (R.length && R[0].score >= 300) fr = R[0]; } } catch (e) { }
        if (fr) { const key = 'MF:' + fr.code; if (seen[key] != null) { out[seen[key]].qty += qty; continue; } seen[key] = out.length; out.push({ sym: key, fund: fr.code, nm: fr.nm, qty: qty, cost: cost || null }); continue; }
        out.push({ raw: raw, sym: null, qty: qty, cost: cost }); continue;
      }
      if (seen[sym] != null) { const o = out[seen[sym]]; const tq = o.qty + qty; if (o.cost && cost) o.cost = +((o.cost * o.qty + cost * qty) / tq).toFixed(2); o.qty = tq; continue; }
      seen[sym] = out.length; out.push({ sym: sym, qty: qty, cost: cost || null });
    }
    return out;
  };
  PF.apply = async function (id) {
    const ta = document.getElementById(id); if (!ta) return;
    try { await E.funds.load(); } catch (e) { }
    const rows = PF.parse(ta.value); const good = rows.filter(function (r) { return r.sym; }); const bad = rows.filter(function (r) { return !r.sym; });
    if (!good.length) { E.toast('no listed name found in that — try "RELIANCE 50 2400", one a line'); return; }
    PF.rows = good; PF.unknown = bad; PF.save();
    E.toast(good.length + ' holding' + (good.length > 1 ? 's' : '') + ' saved in this browser' + (bad.length ? ' · ' + bad.length + ' line' + (bad.length > 1 ? 's' : '') + ' not listed' : ''));
    PF.rerender();
  };
  PF.sample = function (id) { const ta = document.getElementById(id); if (ta) ta.value = 'RELIANCE 50 2400\nHDFC Bank 40 1650\nITC 200 410\nCupid 100 180\nRadico Khaitan 25 2100\nTata Motors 60 700\nGOLDBEES 300 95' + (function () { try { const r = (E.funds.list || []).find(function (x) { return !x.pending && x.r1y != null; }); return r ? '\n' + E.funds.short(r.nm) + ' 500 ' + Math.round(r.nav * 0.8) : ''; } catch (e) { return ''; } })(); };

  /* ── the numbers ── */
  PF.compute = async function () {
    const rows = PF.load(); if (!rows.length) return null;
    await Promise.all(Array.from(new Set(rows.filter(function (r) { return !r.fund; }).map(function (r) { return E.shardOf(r.sym); }))).map(function (k) { return E.loadShard(k); }));
    if (rows.some(function (r) { return r.fund; })) { try { await E.funds.load(); } catch (e) { } }
    const H = []; let value = 0, dayPnl = 0, cost = 0, costed = 0;
    rows.forEach(function (r) {
      if (r.fund) {
        /* v147 · a mutual fund holding: NAV, the category word, the fund's own DNA */
        const fr = (E.funds.byCode || {})[r.fund]; const nav = fr ? fr.nav : 0; const val = r.qty * (nav || 0); value += val; if (r.cost && nav) { cost += r.qty * r.cost; costed += val; }
        const C = fr ? ((E.funds.data || {}).cats || {})[fr.cat] || {} : {}; const lead = fr ? (fr.word === 'LAGGARD' ? 'a laggard in ' + fr.cat + ' (rank ' + fr.rank + ' of ' + (C.scored || '—') + '): consider the category\'s leaders' : fr.word === 'LEADER' ? 'a leader in ' + fr.cat + ' (rank ' + fr.rank + ' of ' + (C.scored || '—') + ') — keep the SIP' : 'mid-table in ' + fr.cat + ' (rank ' + (fr.rank || '—') + ') — hold') : 'not on the funds table';
        H.push({ sym: r.sym, nm: fr ? E.funds.short(fr.nm) : (r.nm || r.sym), sector: 'Fund · ' + (fr ? fr.cat : '—'), qty: r.qty, cost: r.cost, px: nav, d1: null, val: val, pnl: (r.cost && nav) ? r.qty * (nav - r.cost) : null, pnl_pct: (r.cost && nav) ? (nav / r.cost - 1) * 100 : null,
          vs: {}, vl: {}, dec: { word: fr ? fr.word : 'NO DATA', cls: fr ? (fr.word === 'LEADER' ? 'buy' : fr.word === 'LAGGARD' ? 'sell' : 'hold') : 'none', act: fr && fr.word === 'LAGGARD' ? 'SWITCH' : 'HOLD', lead: lead }, stopL: null, dna: (fr && fr.dna && fr.dna.b) || null, sig: fr && fr.vol ? fr.vol / Math.sqrt(252) : 1, fno: false, scored: !!fr, note: null, row: null, isFund: true, fund: fr });
        return;
      }
      const lt = E.lt(r.sym) || {}; const row = E.rowSync(r.sym); const px = L.px(r.sym) || lt.px || 0; const d1 = L.d1(r.sym);
      const val = r.qty * px; value += val; if (d1 != null) dayPnl += val - val / (1 + d1 / 100); if (r.cost) { cost += r.qty * r.cost; costed += val; }
      const v = (row && row.v) || {}; const vs = v.short || {}, vl = v.long || {}; const t = (row && row.tape) || {};
      const stopL = vl.stop || t.m200 || (px ? px * 0.85 : null);
      const scored = !!(row && row.v && v.note !== 9 && (vs.score != null || vl.score != null));
      const dec = scored ? E.decide(vs, vl, px, stopL) : { word: 'NOT SCORED', cls: 'none', act: 'NONE', lead: 'too little history for the engine to score — a price and a day only' };
      H.push({ sym: r.sym, nm: lt.nm || r.sym, sector: lt.sector || '—', qty: r.qty, cost: r.cost, px: px, d1: d1, val: val, pnl: r.cost ? r.qty * (px - r.cost) : null, pnl_pct: r.cost ? (px / r.cost - 1) * 100 : null,
        vs: vs, vl: vl, dec: dec, stopL: stopL, dna: (row && row.dna && row.dna.b) || null, sig: t.sig1d || null, fno: lt.fno, scored: scored, note: v.note, row: row });
    });
    H.forEach(function (h) { h.w = value ? h.val / value * 100 : 0; });
    H.sort(function (a, b) { return b.val - a.val; });
    /* the book's DNA: value-weighted betas (names without betas take the sector's, else the index's 1/0) */
    const S = (E.lite && E.lite.sectors) || {}; const beta = {}; let covered = 0;
    FACTORS.forEach(function (k) { beta[k] = 0; });
    H.forEach(function (h) { let b = h.dna; if (!b) { const sd = (S[h.sector] || {}).dna; b = sd || { nifty: 1, inr: 0, brent: 0, rates: 0, vix: 0 }; } else covered += h.val; FACTORS.forEach(function (k) { beta[k] += (b[k] || 0) * (value ? h.val / value : 0); }); });
    /* shocks */
    const P = ((E.lite && E.lite.shock) || {}).presets || {}; const shocks = [];
    Object.keys(P).forEach(function (k) {
      const p = P[k]; let d = 0; const per = [];
      H.forEach(function (h) { let b = h.dna || (S[h.sector] || {}).dna || { nifty: 1, inr: 0, brent: 0, rates: 0, vix: 0 }; let x = 0; FACTORS.forEach(function (f) { x += (b[f] || 0) * (p[f] || 0); }); const inr = h.val * x / 100; d += inr; per.push({ sym: h.sym, nm: h.nm, pct: x, inr: inr }); });
      per.sort(function (a, b) { return a.inr - b.inr; });
      shocks.push({ key: k, label: p.label, note: p.note, inr: d, pct: value ? d / value * 100 : 0, nifty: p.nifty, worst: per.slice(0, 2), best: per.slice(-2).reverse() });
    });
    shocks.sort(function (a, b) { return a.inr - b.inr; });
    /* sectors */
    const sec = {}; H.forEach(function (h) { sec[h.sector] = (sec[h.sector] || 0) + h.val; });
    const sectors = Object.keys(sec).map(function (k) { return { sector: k, val: sec[k], w: value ? sec[k] / value * 100 : 0, word: (S[k] || {}).word || null }; }).sort(function (a, b) { return b.val - a.val; });
    /* actions */
    const acts = [];
    H.forEach(function (h) {
      if (h.dec.act === 'SELL') acts.push({ kind: 'SELL', h: h, qty: h.qty, inr: h.val, txt: 'sell all ' + F.n(h.qty, 0) + ' → ' + F.big(h.val) });
      else if (h.dec.act === 'SELL_HALF') acts.push({ kind: 'SELL_HALF', h: h, qty: Math.ceil(h.qty / 2), inr: h.val / 2, txt: 'sell ' + F.n(Math.ceil(h.qty / 2), 0) + ' of ' + F.n(h.qty, 0) + ' → ' + F.big(h.val / 2) + ' · stop ' + F.inr(h.vs.stop) + ' on the rest' });
      else if (h.dec.act === 'SWITCH') acts.push({ kind: 'SWITCH', h: h, qty: h.qty, inr: h.val, txt: 'a laggard — switch to a leader in ' + (h.fund ? h.fund.cat : 'its category') });
      else if (h.dec.act === 'ADD') { const sz = (h.vs.size_pct || 2) / 100 * value; const cap = Math.max(0, Math.min(sz, value * 0.1 - h.val)); const q = h.px ? Math.floor(cap / h.px) : 0; if (cap > 0 && q > 0) acts.push({ kind: 'ADD', h: h, qty: q, inr: cap, txt: 'add up to ' + F.big(cap) + ' (' + F.n(q, 0) + ' shares) · stop ' + F.inr(h.vs.stop) + ' on the new piece' }); else acts.push({ kind: 'FULL', h: h, qty: 0, inr: 0, txt: 'a full position already (10% of the book) — hold, do not add · exit below ' + F.inr(h.stopL) }); }
    });
    const freed = acts.filter(function (a) { return a.kind === 'SELL' || a.kind === 'SELL_HALF'; }).reduce(function (s, a) { return s + a.inr; }, 0);
    const held = {}; H.forEach(function (h) { held[h.sym] = 1; });
    const buys = (((E.lite || {}).picks || {}).today_buys || []).filter(function (p) { return !held[p.sym]; }).slice(0, 3).map(function (p) { const sz = (p.size_pct || 2) / 100 * value; return { p: p, inr: sz, qty: (L.px(p.sym) || p.px) ? Math.floor(sz / (L.px(p.sym) || p.px)) : 0 }; });
    const counts = { SELL: 0, SELL_HALF: 0, HOLD: 0, ADD: 0, NONE: 0 }; H.forEach(function (h) { const a = h.dec.act === 'ADD' && !acts.some(function (x) { return x.h === h && x.kind === 'ADD'; }) ? 'HOLD' : h.dec.act; counts[a] = (counts[a] || 0) + 1; });
    const sigma = H.reduce(function (s, h) { return s + (h.sig || 2) * h.val; }, 0) / (value || 1);
    return { H: H, value: value, dayPnl: dayPnl, dayPct: value ? dayPnl / (value - dayPnl) * 100 : 0, cost: cost, costed: costed, pnl: costed ? costed - cost : null, beta: beta, covered: value ? covered / value * 100 : 0, shocks: shocks, sectors: sectors, acts: acts, freed: freed, buys: buys, counts: counts, top: H[0], sigma: sigma, n: H.length, unscored: H.filter(function (h) { return !h.scored; }).length };
  };

  /* ── the view ── */
  PF.box = function (id, open) {
    const rows = PF.load();
    return '<div class="cd" id="' + id + '-wrap"' + (rows.length && !open ? ' style="display:none"' : '') + '><div class="e-between"><div><div class="lbl" style="margin:0">Your holdings</div><div class="e-sub" style="margin-top:2px">one a line — "RELIANCE 50 2400" (name, shares, average cost) — or paste the holdings export from Zerodha Console / Kite, Groww or Upstox as it is. Saved only in this browser.</div></div><span class="e-chip" onclick="E.pf.sample(\'' + id + '\')">try a sample</span></div>' +
      '<textarea class="e-input" id="' + id + '" rows="6" style="width:100%;margin-top:10px;font-family:IBM Plex Mono,monospace;font-size:12.5px;resize:vertical" placeholder="RELIANCE 50 2400&#10;HDFC Bank 40 1650&#10;ITC 200 410&#10;Cupid 100 180">' + F.esc(rows.map(function (r) { return (r.fund ? (r.nm || r.sym) : r.sym) + ' ' + r.qty + (r.cost ? ' ' + r.cost : ''); }).join('\n')) + '</textarea>' +
      '<div class="e-row" style="margin-top:10px"><button class="e-btn p" onclick="E.pf.apply(\'' + id + '\')">X-ray my book →</button>' + (rows.length ? '<button class="e-btn sm" onclick="E.pf.clear()">clear</button>' : '') + '<span style="font-size:11px;color:var(--mut)">nothing is uploaded anywhere — the page computes it here</span></div></div>';
  };
  PF.rerender = function () { try { if (E.tab === 'research') { E.research.sub = 'portfolio'; E.research.render(); } else if (E.tab === 'home') E.home.render(); else E.pf.render(document.getElementById('e-pf-host')); } catch (e) { } };
  PF.render = async function (el) {
    if (!el) return;
    const rows = PF.load();
    if (!E.lite) { el.innerHTML = E.notReady('The X-ray'); return; }
    if (!rows.length) {
      el.innerHTML = '<div class="e-h2">The portfolio X-ray</div><div class="e-sub" style="margin-bottom:12px">paste what you hold and the page tells you, in rupees: the model\'s word on every holding, what your whole book is made of (its beta to the Nifty, the rupee, crude, rates and VIX), what each shock costs you, how concentrated you are, and where the model would move the money today.</div>' + PF.box('e-pf-ta', true) +
        '<div class="e-why-us" style="margin-top:14px"><div class="c"><div class="t">The book\'s DNA</div><div class="s">A holder sees P&L. Nobody shows the macro exposure of the whole book — until now.</div></div><div class="c"><div class="t">Shocks in rupees</div><div class="s">Crude to $120, RBI +50bp, rupee to 100, FII selling — the cost to your book, and the two names that take the hit.</div></div><div class="c"><div class="t">One word per holding</div><div class="s">SELL, SELL HALF, HOLD, ADD — the same engine that scores every listed share, applied to what you own.</div></div></div>';
      return;
    }
    el.innerHTML = '<div class="e-h2">The portfolio X-ray</div><div class="e-ans" style="margin-top:10px"><span class="e-spin"></span> reading ' + rows.length + ' holdings against the engine…</div>';
    const X = await PF.compute(); if (!X) return;
    const M = (E.lite.market || {});
    let h = '<div class="e-between"><div><div class="e-h2">The portfolio X-ray' + (PF.name ? ' · ' + F.esc(PF.name) : '') + '</div><div class="e-sub">' + X.n + ' holdings · computed from the engine\'s rows and the live price · ' + F.esc(E.lite.generated || '') + '</div></div><div class="e-row">' + L.chip() + '<button class="e-btn sm" onclick="document.getElementById(\'e-pf-ta-wrap\').style.display=\'block\';window.scrollTo({top:document.getElementById(\'e-pf-ta-wrap\').offsetTop-80})">edit holdings</button></div></div>';
    /* 1 · the book */
    h += '<div class="e-record" style="margin-top:12px;grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">' +
      '<div class="e-stat"><div class="k">The book</div><div class="v">' + F.big(X.value) + '</div><div class="s">' + X.n + ' names · top ' + F.esc(X.top.sym) + ' ' + F.n(X.top.w, 0) + '%</div></div>' +
      '<div class="e-stat"><div class="k">Today</div><div class="v ' + F.tone(X.dayPnl) + '">' + (X.dayPnl >= 0 ? '+' : '−') + F.big(Math.abs(X.dayPnl)) + '</div><div class="s">' + F.pct(X.dayPct, 2) + ' · Nifty ' + F.pct(L.d1('NIFTY'), 2) + '</div></div>' +
      (X.pnl != null ? '<div class="e-stat"><div class="k">P&L from cost</div><div class="v ' + F.tone(X.pnl) + '">' + (X.pnl >= 0 ? '+' : '−') + F.big(Math.abs(X.pnl)) + '</div><div class="s">' + F.pct(X.cost ? (X.costed / X.cost - 1) * 100 : null, 1) + ' on ' + F.big(X.cost) + ' invested</div></div>' : '') +
      '<div class="e-stat"><div class="k">The model says</div><div class="v" style="font-size:15px;line-height:1.4"><span class="e-dn">' + (X.counts.SELL + X.counts.SELL_HALF) + ' sell</span> · ' + X.counts.HOLD + ' hold · <span class="e-up">' + X.counts.ADD + ' add</span></div><div class="s">' + (X.unscored ? X.unscored + ' not scored · ' : '') + 'frees ' + F.big(X.freed) + ' if followed</div></div>' +
      '<div class="e-stat"><div class="k">A day\'s swing</div><div class="v">±' + F.big(X.value * X.sigma / 100) + '</div><div class="s">σ ' + F.n(X.sigma, 1) + '% · Nifty beta ' + F.n(X.beta.nifty, 2) + '</div></div></div>';
    /* 2 · the holdings */
    h += E.sectionHead('Every holding, the model\'s word', 'the same engine that scores every listed share, applied to what you own · tap a name for its research page');
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>holding</th><th style="text-align:right">qty</th><th style="text-align:right">price</th><th style="text-align:right">value · weight</th><th style="text-align:right">P&L</th><th>the word</th><th style="text-align:right">short · long</th><th style="text-align:right">stop</th><th>the action</th></tr></thead><tbody>' +
      X.H.map(function (x) {
        if (x.isFund) return '<tr><td><b style="cursor:pointer;color:#fff" onclick="E.funds.open(\'' + F.esc(x.fund ? x.fund.code : '') + '\')">' + F.esc(x.nm) + '</b><div style="font-size:10.5px;color:var(--mut)">' + F.esc(x.sector) + '</div></td><td style="text-align:right">' + F.n(x.qty, 2) + ' units</td><td style="text-align:right">NAV ' + F.n(x.px, 2) + '</td><td style="text-align:right">' + F.big(x.val) + '<div style="font-size:10.5px;color:var(--mut)">' + F.n(x.w, 1) + '%</div></td><td style="text-align:right" class="' + F.tone(x.pnl) + '">' + (x.pnl != null ? (F.big(x.pnl) + '<div style="font-size:10.5px">' + F.pct(x.pnl_pct, 1) + '</div>') : '<span style="color:var(--mut)">no cost given</span>') + '</td><td><span class="e-word ' + x.dec.cls + '">' + F.esc(x.dec.word) + '</span></td><td style="text-align:right;color:var(--dim)">' + (x.fund && x.fund.score != null ? 'score ' + Math.round(x.fund.score) : '—') + '</td><td style="text-align:right">—</td><td style="font-family:IBM Plex Sans,sans-serif;font-size:12px;color:var(--tx);max-width:260px">' + F.esc(x.dec.lead) + '</td></tr>';
        const act = X.acts.find(function (a) { return a.h === x; });
        return '<tr><td><b style="cursor:pointer;color:#fff" onclick="E.openShare(\'' + F.esc(x.sym) + '\')">' + F.esc(x.nm) + '</b><div style="font-size:10.5px;color:var(--mut)">' + F.esc(x.sym) + ' · ' + F.esc(x.sector) + (x.fno ? ' · F&O' : '') + '</div></td><td style="text-align:right">' + F.n(x.qty, 0) + '</td><td style="text-align:right"><span data-live-px="' + F.esc(x.sym) + '">' + F.inr(x.px) + '</span><div class="' + F.tone(x.d1) + '" style="font-size:10.5px" data-live-d="' + F.esc(x.sym) + '">' + F.pct(x.d1, 2) + '</div></td><td style="text-align:right">' + F.big(x.val) + '<div style="font-size:10.5px;color:var(--mut)">' + F.n(x.w, 1) + '%</div></td><td style="text-align:right" class="' + F.tone(x.pnl) + '">' + (x.pnl != null ? (F.big(x.pnl) + '<div style="font-size:10.5px">' + F.pct(x.pnl_pct, 1) + '</div>') : '<span style="color:var(--mut)">no cost given</span>') + '</td><td><span class="e-word ' + x.dec.cls + '">' + F.esc(x.dec.word) + '</span></td><td style="text-align:right;color:var(--dim)">' + (x.scored ? (Math.round(x.vs.score || 0) + ' · ' + Math.round(x.vl.score || 0)) : '—') + '</td><td style="text-align:right">' + F.inr(x.stopL) + '</td><td style="font-family:IBM Plex Sans,sans-serif;font-size:12px;color:var(--tx);max-width:260px">' + (act ? F.esc(act.txt) : (x.scored ? 'hold · the exit is a close below ' + F.inr(x.stopL) : 'not scored')) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
    if (PF.unknown && PF.unknown.length) h += '<div class="note">not on the exchange list, left out: ' + PF.unknown.map(function (u) { return F.esc(u.raw); }).join(' · ') + '</div>';
    /* 3 · the DNA */
    h += E.sectionHead('What your book is made of', 'value-weighted betas of your holdings to the five macro factors · ' + F.n(X.covered, 0) + '% of the book has its own measured betas (the rest takes its sector\'s)');
    const nb = X.beta; const read = [];
    read.push('<b>Nifty beta ' + F.n(nb.nifty, 2) + '</b> — ' + (nb.nifty >= 1.2 ? 'a high-beta book: it moves ' + F.n(nb.nifty, 1) + '× the index' : nb.nifty >= 0.8 ? 'it moves with the market' : 'a defensive book') + '; a 1% Nifty day is about <b>' + F.big(X.value * nb.nifty / 100) + '</b>');
    read.push('<b>Rupee ' + F.sgn(nb.inr, 2) + '</b> — a 1% slide in the rupee (USD/INR up) ' + (nb.inr > 0.05 ? 'pays' : nb.inr < -0.05 ? 'costs' : 'barely moves') + ' you about <b>' + F.big(Math.abs(X.value * nb.inr / 100)) + '</b>' + (nb.inr < -0.2 ? ' · an importer\'s book' : nb.inr > 0.2 ? ' · an exporter\'s book' : ''));
    read.push('<b>Crude ' + F.sgn(nb.brent, 2) + '</b> — Brent +10% ' + (nb.brent < -0.03 ? 'costs' : nb.brent > 0.03 ? 'pays' : 'barely moves') + ' about <b>' + F.big(Math.abs(X.value * nb.brent * 10 / 100)) + '</b>');
    read.push('<b>Rates ' + F.sgn(nb.rates, 2) + '</b> — 25bp more on yields (the 5-year gilt −1.1%) ' + (nb.rates < -0.05 ? 'costs' : nb.rates > 0.05 ? 'pays' : 'barely moves') + ' about <b>' + F.big(Math.abs(X.value * nb.rates * 1.125 / 100)) + '</b>' + (nb.rates < -0.3 ? ' · a rate-sensitive book' : ''));
    read.push('<b>VIX ' + F.sgn(nb.vix, 2) + '</b> — a fear spike (VIX +20%) ' + (nb.vix < -0.02 ? 'costs' : nb.vix > 0.02 ? 'pays' : 'barely moves') + ' about <b>' + F.big(Math.abs(X.value * nb.vix * 20 / 100)) + '</b>');
    h += '<div class="cd"><div class="e-grid e-g2"><div class="e-dna">' + FACTORS.map(function (k) { const v = nb[k]; const mx = k === 'nifty' ? 2 : 1; const pct = Math.max(-1, Math.min(1, (v || 0) / mx)); const left = pct >= 0 ? 50 : 50 + pct * 50; const w = Math.abs(pct) * 50; return '<div class="r"><div class="k">' + E.FACTOR[k] + '</div><div class="bar"><b></b><i style="left:' + left + '%;width:' + w + '%;background:' + ((v || 0) >= 0 ? 'var(--grn)' : 'var(--red)') + '"></i></div><div class="v">' + F.sgn(v, 2) + '</div><div class="t">' + (k === 'nifty' ? 'index 1.00' : 'index 0') + '</div></div>'; }).join('') + '<div style="font-size:11px;color:var(--mut);margin-top:6px">β = % move of your book per 1% move of the factor · value-weighted from each holding\'s weekly betas (3 years, ridge)</div></div><div><div class="lbl">In rupees</div><ul style="margin:4px 0 0 18px;font-size:12.5px;line-height:1.7;color:var(--tx)">' + read.map(function (r) { return '<li>' + r + '</li>'; }).join('') + '</ul></div></div></div>';
    /* 4 · the shocks */
    h += E.sectionHead('What a shock costs you', 'the engine\'s presets applied to your book, name by name · Δ ≈ Σ β × Δfactor, a first-order estimate');
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>shock</th><th style="text-align:right">your book</th><th style="text-align:right">the Nifty</th><th>takes the hit</th><th>holds up</th></tr></thead><tbody>' + X.shocks.map(function (s) { return '<tr><td><b style="color:#fff">' + F.esc(s.label) + '</b><div style="font-size:10.5px;color:var(--mut);max-width:320px;white-space:normal">' + F.esc(s.note) + '</div></td><td style="text-align:right" class="' + F.tone(s.inr) + '"><b>' + (s.inr >= 0 ? '+' : '−') + F.big(Math.abs(s.inr)) + '</b><div style="font-size:10.5px">' + F.pct(s.pct, 1) + '</div></td><td style="text-align:right" class="' + F.tone(s.nifty) + '">' + F.pct(s.nifty, 1) + '</td><td style="font-size:11px">' + s.worst.map(function (w) { return F.esc(w.nm) + ' <span class="' + F.tone(w.inr) + '">' + F.pct(w.pct, 1) + '</span>'; }).join('<br>') + '</td><td style="font-size:11px">' + s.best.map(function (w) { return F.esc(w.nm) + ' <span class="' + F.tone(w.inr) + '">' + F.pct(w.pct, 1) + '</span>'; }).join('<br>') + '</td></tr>'; }).join('') + '</tbody></table></div>';
    /* 5 · concentration */
    h += E.sectionHead('Concentration', 'by sector, with the engine\'s word on each sector today');
    h += '<div class="cd"><div class="e-bars">' + X.sectors.map(function (s) { return '<div class="r"><div class="k">' + F.esc(s.sector) + (s.word ? ' <span class="e-tag" style="margin-left:4px">' + F.esc(s.word) + '</span>' : '') + '</div><div class="e-bar"><i style="width:' + Math.min(100, s.w) + '%;background:' + (s.w > 40 ? 'var(--org)' : 'var(--blu)') + '"></i></div><div class="v">' + F.n(s.w, 0) + '%</div></div>'; }).join('') + '</div><div style="font-size:12px;color:var(--dim);margin-top:8px">' + (X.top.w > 25 ? '<b style="color:var(--org)">' + F.esc(X.top.nm) + ' is ' + F.n(X.top.w, 0) + '% of the book</b> — the engine caps any one name at 10% of capital. ' : '') + (X.sectors[0].w > 40 ? '<b style="color:var(--org)">' + F.esc(X.sectors[0].sector) + ' is ' + F.n(X.sectors[0].w, 0) + '%</b> — the desk\'s rule is 30% in one sector at most. ' : 'No sector above 40%: the concentration is tolerable. ') + (X.n < 5 ? 'Under five names, a single stop is a large part of the book.' : '') + '</div></div>';
    /* 6 · what the model would do today */
    h += E.sectionHead('What the model would do today', 'the sells first, then the adds, then where the freed money would go — ' + F.esc(M.call || '') + (M.gate ? ' · the gate is on, sizes halved' : ''));
    const sells = X.acts.filter(function (a) { return a.kind === 'SELL' || a.kind === 'SELL_HALF' || a.kind === 'SWITCH'; }), adds = X.acts.filter(function (a) { return a.kind === 'ADD'; });
    h += '<div class="e-grid e-g2"><div><div class="lbl">Sell</div><div class="e-list">' + (sells.map(function (a) { return '<div class="e-li" onclick="' + (a.h.isFund ? 'E.funds.open(\'' + F.esc(a.h.fund ? a.h.fund.code : '') + '\')' : 'E.openShare(\'' + F.esc(a.h.sym) + '\')') + '"><div class="n">' + F.esc(a.h.nm) + '<small>' + F.esc(a.txt) + '</small></div><div><span class="e-word ' + a.h.dec.cls + '">' + F.esc(a.h.dec.word) + '</span></div><div class="px">' + F.big(a.inr) + '</div></div>'; }).join('') || '<div class="e-empty">nothing to sell today</div>') + '</div>' +
      (sells.length ? '<div style="font-size:12px;color:var(--dim);margin-top:6px">frees <b style="color:#fff">' + F.big(X.freed) + '</b></div>' : '') + '</div>' +
      '<div><div class="lbl">Add · and where the money would go</div><div class="e-list">' + (adds.map(function (a) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(a.h.sym) + '\')"><div class="n">' + F.esc(a.h.nm) + '<small>' + F.esc(a.txt) + '</small></div><div><span class="e-word buy">ADD</span></div><div class="px">' + F.big(a.inr) + '</div></div>'; }).join('')) +
      (X.buys.map(function (b) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(b.p.sym) + '\')"><div class="n">' + F.esc(b.p.nm) + ' <span class="e-tag">not held</span><small>' + F.n(b.qty, 0) + ' sh · stop ' + F.inr(b.p.stop) + ' · tgt ' + F.inr(b.p.target) + ' · ' + b.p.h + ' s</small><div style="font-size:11px;color:var(--dim);font-weight:400;margin-top:1px">the model\'s buy today, sized at ' + (b.p.size_pct || 2) + '% of your book</div></div><div>' + F.word('BUY') + '</div><div class="px">' + F.big(b.inr) + '</div></div>'; }).join('')) + ((adds.length + X.buys.length) ? '' : '<div class="e-empty">no add clears the bar today</div>') + '</div></div></div>';
    h += '<div class="e-row" style="margin-top:12px"><button class="e-btn sm" onclick="E.go(\'micro\',\'where\')">where the regime says to be →</button><button class="e-btn sm" onclick="E.ask.fill(\'e-pf-ask\',\'what should I do with my portfolio?\')">ask about the book →</button></div>';
    h += '<div style="margin-top:14px">' + E.ask.box('e-pf-ask', null) + '</div>';
    h += '<div style="margin-top:14px">' + PF.box('e-pf-ta', false) + '</div>';
    h += '<div class="note" style="margin-top:12px">The X-ray is computed from the engine\'s rows (verdicts, stops, betas) and the live price; the holdings stay in this browser. Betas are first-order and weekly; a shock\'s rupee figure is an estimate of the same order as the day\'s swing above, not a promise.</div>';
    el.innerHTML = h;
    try { L.want(X.H.filter(function (x) { return !x.isFund; }).map(function (x) { return x.sym; })); } catch (e) { }
  };

  /* ── the home strip ── */
  PF.strip = function () {
    const rows = PF.load();
    if (!rows.length) return '<div class="cd e-between" style="margin-top:14px"><div><div class="lbl" style="margin:0">Your book</div><div class="e-sub" style="margin-top:2px">paste what you hold — the model\'s word on every holding, your book\'s macro DNA, what each shock costs you in rupees</div></div><button class="e-btn p sm" onclick="E.go(\'research\',\'portfolio\')">X-ray my portfolio →</button></div>';
    return '<div class="cd e-between" style="margin-top:14px" id="e-pf-strip"><div><div class="lbl" style="margin:0">Your book · ' + rows.length + ' holdings</div><div class="e-sub" style="margin-top:2px" id="e-pf-strip-s"><span class="e-spin"></span> reading…</div></div><button class="e-btn sm" onclick="E.go(\'research\',\'portfolio\')">the X-ray →</button></div>';
  };
  PF.fillStrip = async function () {
    try {
      const el = document.getElementById('e-pf-strip-s'); if (!el) return; const X = await PF.compute(); if (!X) return;
      el.innerHTML = '<b style="color:#fff">' + F.big(X.value) + '</b> · today <b class="' + F.tone(X.dayPnl) + '">' + (X.dayPnl >= 0 ? '+' : '−') + F.big(Math.abs(X.dayPnl)) + '</b> · the model: <b class="e-dn">' + (X.counts.SELL + X.counts.SELL_HALF) + ' sell</b>, ' + X.counts.HOLD + ' hold, <b class="e-up">' + X.counts.ADD + ' add</b> · Nifty beta ' + F.n(X.beta.nifty, 2) + ' · worst shock ' + F.esc(X.shocks[0].label) + ' <b class="' + F.tone(X.shocks[0].inr) + '">' + (X.shocks[0].inr >= 0 ? '+' : '−') + F.big(Math.abs(X.shocks[0].inr)) + '</b>';
    } catch (e) { }
  };

  /* ── Ask: the whole book ── */
  PF.answer = async function () {
    const rows = PF.load();
    if (!rows.length) return { html: E.ask.card('<span class="e-word none big">NO PORTFOLIO SAVED</span>', 'Paste your holdings once (one a line — "RELIANCE 50 2400" — or a broker export) and Ask will answer about the whole book: what to sell, what to add, what a shock costs you.', [], [], '<div class="e-row" style="margin-top:12px"><button class="e-btn sm p" onclick="E.go(\'research\',\'portfolio\')">paste my holdings →</button></div>'), ctx: null };
    const X = await PF.compute(); if (!X) return E.ask.unknown({ q: '' });
    const sells = X.acts.filter(function (a) { return a.kind === 'SELL' || a.kind === 'SELL_HALF'; }), adds = X.acts.filter(function (a) { return a.kind === 'ADD'; });
    const word = sells.length ? (sells.length >= Math.max(2, X.n / 2) ? 'TRIM THE BOOK' : 'SELL ' + sells.length + ', KEEP THE REST') : adds.length ? 'HOLD · ADD TO ' + adds.length : 'HOLD';
    const cls = sells.length ? 'sell' : adds.length ? 'buy' : 'hold';
    const lead = 'Your ' + X.n + ' holdings are worth <b>' + F.big(X.value) + '</b>' + (X.pnl != null ? ' (' + (X.pnl >= 0 ? '+' : '−') + F.big(Math.abs(X.pnl)) + ' from cost)' : '') + '. The engine would ' + (sells.length ? 'sell ' + sells.map(function (a) { return a.h.nm + (a.kind === 'SELL_HALF' ? ' (half)' : ''); }).join(', ') + ', freeing ' + F.big(X.freed) : 'sell nothing') + (adds.length ? '; add to ' + adds.map(function (a) { return a.h.nm; }).join(', ') : '') + '. The book carries a Nifty beta of ' + F.n(X.beta.nifty, 2) + ' — a 1% index day is ' + F.big(X.value * X.beta.nifty / 100) + ' — and its worst preset is <b>' + F.esc(X.shocks[0].label) + '</b> at <b class="' + F.tone(X.shocks[0].inr) + '">' + (X.shocks[0].inr >= 0 ? '+' : '−') + F.big(Math.abs(X.shocks[0].inr)) + '</b>.' + (X.top.w > 25 ? ' ' + X.top.nm + ' is ' + F.n(X.top.w, 0) + '% of the book — too much for one name.' : '');
    const kv = [['The book', F.big(X.value)], ['Today', (X.dayPnl >= 0 ? '+' : '−') + F.big(Math.abs(X.dayPnl)), F.tone(X.dayPnl)], ['Sell · hold · add', (X.counts.SELL + X.counts.SELL_HALF) + ' · ' + X.counts.HOLD + ' · ' + X.counts.ADD], ['A day\'s swing', '±' + F.big(X.value * X.sigma / 100)]];
    const why = X.H.slice(0, 6).map(function (x) { return F.esc(x.nm) + ': <b>' + F.esc(x.dec.word) + '</b> · ' + F.n(x.w, 0) + '% of the book' + (x.scored ? ' · short ' + Math.round(x.vs.score || 0) + ', long ' + Math.round(x.vl.score || 0) : ''); });
    const more = '<div class="e-row" style="margin-top:12px"><button class="e-btn sm p" onclick="E.go(\'research\',\'portfolio\')">the full X-ray →</button></div>';
    return { html: E.ask.card('<span class="e-word ' + cls + ' big">' + F.esc(word) + '</span>', lead, kv, why, more), ctx: { portfolio: X.H.map(function (x) { return { sym: x.sym, name: x.nm, qty: x.qty, cost: x.cost, px: x.px, value: x.val, weight_pct: x.w, decision: x.dec.word, short: x.vs.side, long: x.vl.side, stop: x.stopL }; }), value: X.value, beta: X.beta, shocks: X.shocks.map(function (s) { return { label: s.label, inr: s.inr, pct: s.pct }; }), actions: X.acts.map(function (a) { return a.txt; }), market: E.lite.market } };
  };
})(window.E);
