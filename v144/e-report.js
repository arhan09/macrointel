/* ═══ v150 · THE RESEARCH NOTE — every listed company gets one: written from the engine, regenerated every pass, printable ═══ */
(function (E) {
  const F = E.f, L = E.live;
  const R = E.report = { sym: null, open_: false };
  const esc = F.esc;
  const H = { '1m': '1 month', '3m': '3 months', '6m': '6 months', '12m': '12 months' };
  function ensure() {
    let el = document.getElementById('e-report'); if (el) return el;
    el = document.createElement('div'); el.id = 'e-report'; el.className = 'e-report';
    el.innerHTML = '<div class="e-rp-bar"><button class="e-sh-x" onclick="E.report.close()" title="back (Esc)">←</button><div class="e-rp-title"><b>MacroIntel · Research note</b><span id="e-rp-sub"></span></div><div class="e-row" style="margin-left:auto;gap:6px"><button class="e-btn sm" onclick="E.report.copy()">copy as text</button><button class="e-btn sm" onclick="E.report.link()">copy link</button><button class="e-btn sm p" onclick="E.report.print()">print · save as PDF</button></div></div><div class="e-rp-body" id="e-rp-body"></div>';
    document.body.appendChild(el);
    document.addEventListener('keydown', function (e) { try { if (e.key === 'Escape' && R.open_) R.close(); } catch (x) { } });
    return el;
  }
  R.close = function () { const el = document.getElementById('e-report'); if (el) el.classList.remove('open'); document.body.classList.remove('e-report-open'); R.open_ = false; try { if (history.state && history.state.e_report) history.back(); } catch (e) { } };
  R.print = function () { try { window.print(); } catch (e) { E.toast('print is not available here'); } };
  R.link = function () { try { const u = location.href.split('#')[0] + '#r=' + encodeURIComponent(R.sym || ''); E.copy(u); } catch (e) { } };
  R.copy = function () { try { const b = document.getElementById('e-rp-body'); E.copy(b ? b.innerText : ''); } catch (e) { } };
  R.open = async function (q, opt) {
    opt = opt || {}; const Q = String(q || '').trim(); if (!Q) return;
    if (!E.lite) { E.toast('the engine is not on the page yet'); return; }
    const sym = (E.lite.names[Q.toUpperCase()] ? Q.toUpperCase() : null) || E.one(Q);
    if (!sym) { E.toast('Nothing listed as "' + Q + '"'); return; }
    const el = ensure(); const body = document.getElementById('e-rp-body');
    R.sym = sym; R.open_ = true; el.classList.add('open'); document.body.classList.add('e-report-open'); el.scrollTop = 0;
    try { if (!opt.nopush) history.pushState({ e_report: sym }, '', '#r=' + encodeURIComponent(sym)); } catch (e) { }
    const lt = E.lt(sym) || {};
    document.getElementById('e-rp-sub').textContent = (lt.nm || sym) + ' · ' + sym;
    body.innerHTML = '<div class="e-work"><div class="t"><span class="e-spin"></span> Writing the note on <b>' + esc(lt.nm || sym) + '</b></div></div>';
    let r = null;
    try { r = await E.row(sym); await E.loadFull(); } catch (e) { }
    try { await E.news.load(); } catch (e) { }
    if (R.sym !== sym) return;
    L.want([sym]);
    body.innerHTML = R.html(sym, r, lt);
  };
  /* ── the writer ── */
  const sent = function (arr) { const a = (arr || []).filter(Boolean).map(function (s) { return String(s).trim().replace(/\.$/, ''); }); if (!a.length) return ''; let out = a[0].charAt(0).toUpperCase() + a[0].slice(1); if (a.length > 1) out += '; ' + a.slice(1).join('; '); return out + '.'; };
  const pctw = function (x, nd) { return x == null ? '—' : F.pct(x, nd == null ? 1 : nd); };
  R.verdictWords = function (v) {
    const vs = v.short || {}, vl = v.long || {}, vi = v.intra || {};
    return { s: vs.side || 'NO TRADE', l: vl.side || 'NO VIEW', i: vi.side || 'no trade', ss: vs.score, ls: vl.score };
  };
  R.dnaWords = function (d) {
    if (!d || !d.b) return [];
    const b = d.b, t = d.t || {}; const out = [];
    const strong = function (k) { return Math.abs(t[k] || 0) >= 1.5; };
    out.push('it moves ' + (b.nifty >= 1.2 ? 'harder than the market' : b.nifty >= 0.8 ? 'with the market' : b.nifty >= 0.4 ? 'at a fraction of the market' : 'largely on its own') + ' (β ' + F.n(b.nifty, 2) + ' to the Nifty)');
    if (strong('inr')) out.push(b.inr > 0 ? 'a weaker rupee helps it (β ' + F.sgn(b.inr, 2) + ')' : 'a weaker rupee hurts it (β ' + F.sgn(b.inr, 2) + ')');
    if (strong('brent')) out.push(b.brent > 0 ? 'dearer crude helps it (β ' + F.sgn(b.brent, 2) + ')' : 'dearer crude hurts it (β ' + F.sgn(b.brent, 2) + ')');
    if (strong('rates')) out.push(b.rates > 0 ? 'rising yields help it (β ' + F.sgn(b.rates, 2) + ')' : 'rising yields hurt it (β ' + F.sgn(b.rates, 2) + ')');
    if (strong('vix')) out.push(b.vix > 0 ? 'it gains when fear rises (β ' + F.sgn(b.vix, 2) + ')' : 'it sells off when fear rises (β ' + F.sgn(b.vix, 2) + ')');
    return out;
  };
  R.html = function (sym, r, lt) {
    const M = E.lite.market || {}; const nc = E.lite.nowcast || {}; const probs = nc.probs || {}; const px = L.px(sym) || lt.px; const d1 = L.d1(sym);
    const sec = (E.lite.sectors || {})[lt.sector] || {}; const now = F.ist();
    let h = '<article class="e-rp">';
    h += '<header class="e-rp-head"><div class="k">MacroIntel · research note · ' + esc(now) + ' IST · engine ' + esc(E.lite.generated || '') + '</div><h1>' + esc(lt.nm || sym) + '</h1><div class="m">' + esc(sym) + ' · ' + esc(lt.sector || 'unmapped') + (lt.fno ? ' · F&O' : '') + (lt.x === 'BSE' ? ' · BSE only' : '') + ' · last ' + F.inr(px) + ' <span class="' + F.tone(d1) + '">' + F.pct(d1, 2) + '</span> · turnover ' + F.cr(lt.turn) + ' a day · regime ' + esc(M.regime || '') + (M.gate ? ' · gate on' : '') + '</div></header>';
    if (!r) {
      h += '<section><h2>The verdict</h2><p>Only a price and a day are on file for this listing — no weekly history reaches the engine for it yet, so there is no score, no path and no case. The note fills in once the tape accrues' + (lt.x === 'BSE' ? ' (a BSE-only name: the engine accrues its own daily tape from the bhavcopy, sixty sessions before it counts)' : '') + '.</p></section>';
      return h + R.foot();
    }
    const v = r.v || {}; const vs = v.short || {}, vl = v.long || {}, vi = v.intra || {}; const t = r.tape || {}; const p = r.path || null; const I = r.ind || null; const f = r.fund || null; const sc = r.sc || {};
    const W = R.verdictWords(v);
    /* 1 · the verdict and the path */
    h += '<section><h2>1 · The verdict</h2>';
    h += '<div class="e-rp-verd">' + [['Today', W.i, vi.score], ['5–60 sessions', W.s, W.ss], ['12 months', W.l, W.ls]].map(function (x) { return '<div><div class="k">' + x[0] + '</div><div class="w">' + F.word(x[1] === 'NO TRADE' || x[1] === 'NO VIEW' || x[1] === 'no trade' ? null : x[1], 'mid') + '</div><div class="s">' + (x[2] != null ? Math.round(x[2]) + '/100' : '') + '</div></div>'; }).join('') + '</div>';
    h += '<p>' + esc(String(E.note(v.note) || '').replace(/\.?\s*$/, '.')) + (M.gate ? ' The gate is on today: every size is halved and the bar for a buy is higher.' : '') + '</p>';
    if (p && p.rows) {
      h += '<h3>The path</h3><p class="lead">' + esc(p.head || '') + '</p>' + E.path.ladder(p) + '<ul class="e-rp-ul">' + p.rows.map(function (x) { return '<li>' + esc(x.line) + '</li>'; }).join('') + '</ul>';
    } else h += '<p class="dim">No path: the tape is too short to read stretches of six and twelve months from.</p>';
    h += '</section>';
    /* 2 · the case */
    h += '<section><h2>2 · The case</h2>';
    h += '<h3>Short term · 5–60 sessions · ' + esc(W.s) + (vs.conv ? ' · ' + esc(vs.conv) + ' conviction' : '') + '</h3>';
    if (vs.side) h += '<p>' + esc(sent(vs.why)) + ' The trade: entry ' + F.inr(vs.entry) + ', stop ' + F.inr(vs.stop) + ' (' + pctw(vs.side === 'SELL' ? vs.stop_pct : -vs.stop_pct) + '), target ' + F.inr(vs.target) + ' (' + pctw(vs.side === 'SELL' ? -vs.tgt_pct : vs.tgt_pct) + '), ' + vs.h + ' sessions at most, ' + (vs.size_pct != null ? vs.size_pct + '% of capital' : '') + ' — two to one.</p>';
    else h += '<p>' + esc(vs.thin ? 'Too little history to score.' : vs.illiquid ? 'Below the liquidity floor (₹5 crore a day): scored from the tape, not traded.' : 'No trade: the short-term score is ' + (vs.score != null ? Math.round(vs.score) : '—') + '/100 — a buy needs 80 (momentum, the macro wind and the futures flow turning up together), a sell needs 10.') + (vs.why && vs.why.length ? ' ' + esc(sent(vs.why)) : '') + '</p>';
    h += '<h3>Long term · 12 months · ' + esc(W.l) + (vl.conv ? ' · ' + esc(vl.conv) + ' conviction' : '') + '</h3>';
    if (vl.side) h += '<p>' + esc(sent(vl.why)) + ' The twelve-month expectation is ' + pctw(vl.exp_pct, 0) + ' (' + F.inr(vl.target) + '), with a one-σ band of ' + F.inr(vl.band && vl.band[0]) + ' – ' + F.inr(vl.band && vl.band[1]) + '; the exit is a close below ' + F.inr(vl.stop) + ' (' + esc(vl.stop_note || 'the 200-day') + ').</p>';
    else h += '<p>' + esc(vl.thin ? 'Too little history to score.' : 'No view: the long-term score is ' + (vl.score != null ? Math.round(vl.score) : '—') + '/100 — accumulate needs 80 (trend, quality and the sector\'s regime record lining up), avoid is 20 or less.') + (vl.why && vl.why.length ? ' ' + esc(sent(vl.why)) : '') + '</p>';
    h += '<p class="dim">The score in parts (percentiles of the market): trend ' + F.n(sc.T, 0) + ' / ' + F.n(sc.TL, 0) + ' (short / long), macro ' + F.n(sc.M, 0) + ' / ' + F.n(sc.ML, 0) + ', quality ' + F.n(sc.Q, 0) + ', futures flow ' + F.n(sc.F, 0) + ', contenders ' + F.n(sc.C, 0) + ', risk ' + F.n(sc.R, 0) + '. The tape: ' + pctw(t.r20) + ' over 20 sessions, ' + pctw(t.r60) + ' over 60, ' + pctw(t.r250, 0) + ' over a year; ' + (t.vs200 != null ? (t.vs200 >= 0 ? 'above' : 'below') + ' the 200-day by ' + pctw(Math.abs(t.vs200)) + '; ' : '') + 'σ ' + F.n(t.sig1d, 1) + '% a day; ' + (t.dd != null ? 'drawdown from the high ' + pctw(t.dd, 0) + '; ' : '') + '52-week range ' + F.inr(t.lo52) + ' – ' + F.inr(t.hi52) + '.</p>';
    h += '</section>';
    /* 3 · the macro and the industry */
    h += '<section><h2>3 · What the macro does to it</h2>';
    const pl = Object.keys(probs).length ? Object.keys(probs).sort(function (a, b) { return probs[b] - probs[a]; }).slice(0, 2).map(function (k) { return k + ' ' + Math.round(probs[k]) + '%'; }).join(', ') : '';
    h += '<p>The regime is <b>' + esc(M.regime || '') + '</b>' + (pl ? ' (the market\'s own lean: ' + esc(pl) + ')' : '') + '. ' + (sec.edge && sec.edge.ann_pct != null ? esc(lt.sector) + ' has returned ' + pctw(sec.edge.ann_pct, 0) + ' a year in ' + esc(M.regime) + ' regimes' + (Math.abs(sec.edge.t || 0) < 1.5 ? ' (weak evidence)' : ' (t ' + F.n(sec.edge.t, 1) + ')') + '. ' : '') + (r.wind && r.wind.total != null ? 'This month\'s macro moves gave it ' + pctw(r.wind.total) + (I && I.mkt_wind != null ? ' against the market\'s own ' + pctw(I.mkt_wind) + (I.sec_wind != null ? ' and the industry\'s ' + pctw(I.sec_wind) : '') : '') + ' — ' + (r.wind.parts || []).map(function (x) { return E.FACTOR[x[0]] + ' ' + pctw(x[1]); }).join(', ') + '.' : '') + '</p>';
    const dw = R.dnaWords(r.dna);
    if (dw.length) h += '<p><b>Its macro DNA</b> (weekly returns on the five things that move India, ' + (r.dna.n || 0) + ' weeks, R² ' + F.n(r.dna.r2, 2) + '): ' + esc(sent(dw)) + (r.dna.regime ? ' Its record by regime, excess over the Nifty a year: ' + esc(Object.keys(r.dna.regime).map(function (k) { const x = r.dna.regime[k]; return k + ' ' + pctw(x.ann, 0) + ' (' + x.n + ' weeks, hit ' + x.hit + '%)'; }).join('; ')) + '.' : '') + '</p>';
    if (I) h += '<p><b>Within its industry</b> (' + I.n + ' ' + esc(I.sector) + ' names): #' + (I.rank_s || '—') + ' on the short-term score, #' + (I.rank_l || '—') + ' on the long-term; ' + ((I.rel || {}).r60 != null ? ((I.rel.r60 >= 3 ? 'outperforming' : I.rel.r60 <= -3 ? 'lagging' : 'moving with') + ' its industry over sixty sessions (' + F.sgn(I.rel.r60, 1) + ' points)') : '') + (I.sec_word ? '; the industry itself reads ' + esc(I.sec_word) : '') + '. The macro is a <b>' + esc((I.ind_word || '').toLowerCase()) + '</b> for the industry and a <b>' + esc((I.co_word || '').toLowerCase()) + '</b> for the name' + (I.catches === 'MORE' ? ', which catches more of it than its peers' : I.catches === 'LESS' ? ', which catches less of it than its peers' : '') + '. ' + esc(sent((I.ind_why || []).concat(I.co_why || []))) + '</p>';
    /* the shocks, from the DNA — the simulator's arithmetic, in a line */
    try {
      const b = r.dna && r.dna.b; const P = (E.lite.shock || {}).presets || {};
      if (b) {
        const run = function (x) { let d = 0; ['nifty', 'inr', 'brent', 'rates', 'vix'].forEach(function (k) { d += (b[k] || 0) * (x[k] || 0); }); return d; };
        const fixed = [['Nifty −10%', { nifty: -10 }], ['USD/INR +5%', { inr: 5 }], ['Brent +20%', { brent: 20 }], ['10-year yield +50bp', { rates: 4.5 * 0.5 }], ['India VIX +50%', { vix: 50 }]];
        const pre = Object.keys(P).slice(0, 4).map(function (k) { const q = P[k]; return [q.label, { nifty: q.nifty, inr: q.inr, brent: q.brent, vix: q.vix, rates: q.rates }]; });
        h += '<p><b>Under a shock</b> (its DNA, one factor at a time, then the desk\'s presets): ' + esc(fixed.concat(pre).map(function (x) { return x[0] + ' → ' + F.pct(run(x[1]), 1); }).join(' · ')) + '. The simulator on the research page takes any mix.</p>';
      }
    } catch (e) { }
    /* the peers at a glance, with their twelve-month path words */
    try {
      const mem = ((E.full && E.full.sectors_members) || {})[lt.sector] || [];
      const peers = mem.filter(function (x) { return x !== sym; }).map(function (x) { return E.lt(x); }).filter(Boolean).sort(function (a, b) { return (b.turn || 0) - (a.turn || 0); }).slice(0, 6);
      if (peers.length) h += '<p><b>Peers at a glance</b> (the most traded in ' + esc(lt.sector) + '): ' + peers.map(function (x) { const d = E.path.decode(x.pt); const w12 = d.length ? d[d.length - 1] : null; return esc(x.nm) + ' ' + (x.ss || x.ls ? '(' + esc([x.ss, x.ls].filter(Boolean).join(' / ').toLowerCase()) + ')' : '') + (w12 ? ' — 12 months ' + w12.word.toLowerCase() + (w12.dip ? ', may dip' : '') : ''); }).join('; ') + '.</p>';
    } catch (e) { }
    const mp = E.lite.mpath;
    if (mp && mp.rows) { const r6 = mp.rows.find(function (x) { return x.h === '6m'; }) || {}; const r12 = mp.rows.find(function (x) { return x.h === '12m'; }) || {}; h += '<p><b>The market\'s own path</b> from here: six months ' + esc(r6.word || '') + (r6.may_dip ? ' (may dip)' : '') + ', twelve months ' + esc(r12.word || '') + (r12.may_dip ? ' (may dip)' : '') + (r12.p_same != null ? '; the odds ' + esc(M.regime) + ' still holds in a year ' + r12.p_same + '%' : '') + '. ' + esc(mp.head || '') + '</p>'; }
    h += '</section>';
    /* 4 · the company */
    h += '<section><h2>4 · The company</h2>';
    if (f) {
      h += (f.summary ? '<p>' + esc(f.summary) + '</p>' : '');
      const sp = (E.lite.sector_pe || {})[lt.sector];
      h += '<table class="e-rp-t"><tbody>' + [['Market cap', F.big(f.mcap)], ['P/E · forward', F.n(f.pe, 1) + (f.fpe ? ' · ' + F.n(f.fpe, 1) : '') + (sp && f.pe > 0 ? ' (sector median ' + F.n(sp, 1) + ' — ' + (f.pe < sp * 0.8 ? 'cheaper than peers' : f.pe > sp * 1.25 ? 'dearer than peers' : 'in line') + ')' : '')], ['P/B · book', F.n(f.pb, 2) + (f.bv ? ' · ' + F.inr(f.bv) : '')], ['ROE', f.roe != null ? F.n(f.roe, 1) + '%' : '—'], ['Margins · net / operating', (f.margin != null ? F.n(f.margin, 1) + '%' : '—') + ' / ' + (f.opm != null ? F.n(f.opm, 1) + '%' : '—')], ['Growth · revenue / EPS', pctw(f.revg) + ' / ' + pctw(f.epsg) + (f.rev ? ' · revenue ' + F.big(f.rev) : '')], ['Debt / equity', f.de != null ? F.n(f.de, 0) + '%' : '—'], ['Dividend yield', f.divy != null ? F.n(f.divy, 2) + '%' : '—'], ['Promoter / insiders', f.promoter != null ? F.n(f.promoter * 100, 0) + '%' : '—'], ['Quality score', Math.round(sc.Q || 50) + '/100' + ((sc.qwhy || []).length ? ' (' + esc(sc.qwhy.join(', ')) + ')' : '')]].map(function (x) { return '<tr><th>' + x[0] + '</th><td>' + x[1] + '</td></tr>'; }).join('') + '</tbody></table>';
      h += '<p class="dim">Yahoo Finance profile as of ' + esc(f.asof || '') + '.</p>';
    } else h += '<p class="dim">The business profile (P/E, ROE, margins, growth, debt, promoter holding) arrives with the fundamentals rotation; until then the quality leg sits at neutral and the name is scored on the tape, the macro and the derivatives.</p>';
    h += '</section>';
    /* 5 · the Street, the crowd, the wire */
    h += '<section><h2>5 · The Street, the crowd, the wire</h2>';
    try { const sl = E.street.line(sym, r); h += sl ? '<p>' + sl.replace(/^<div class="e-line">/, '').replace(/<\/div>$/, '') + '</p>' : '<p class="dim">No analyst targets on file for it.</p>'; } catch (e) { }
    try { const cl = E.crowdLine(sym, r); if (cl) h += '<p>' + cl.replace(/^<div class="e-line">/, '').replace(/<\/div>$/, '') + '</p>'; } catch (e) { }
    try { const dl = E.deliveryLine(t, lt.d1); if (dl) h += '<p>' + dl.replace(/^<div class="e-line">/, '').replace(/<\/div>$/, '') + '</p>'; } catch (e) { }
    try { const al = E.attr.line(sym); if (al) h += '<p>' + al.replace(/^<div class="e-line">/, '').replace(/<\/div>$/, '') + '</p>'; } catch (e) { }
    try {
      const nw = E.news.of(sym);
      if (nw && (nw.items || []).length) h += '<p><b>The wire:</b> ' + nw.items.length + ' headline' + (nw.items.length > 1 ? 's' : '') + ' in the last week, the week reading ' + (nw.tone > 0 ? 'positive' : nw.tone < 0 ? 'negative' : 'neutral') + ' (' + (nw.pos || 0) + ' for, ' + (nw.neg || 0) + ' against).</p><ul class="e-rp-ul">' + nw.items.slice(0, 6).map(function (x) { return '<li>' + (x.tone > 0 ? '▲ ' : x.tone < 0 ? '▼ ' : '• ') + '<a target="_blank" rel="noopener" href="' + esc(x.link || '#') + '">' + esc(x.t) + '</a> <span class="dim">' + esc(x.src || '') + (x.age_d != null ? ' · ' + (x.age_d <= 1 ? 'today' : Math.round(x.age_d) + 'd ago') : '') + '</span></li>'; }).join('') + '</ul>';
      else h += '<p class="dim">No headline named it this week — the models read price and macro, not news.</p>';
    } catch (e) { }
    if (r.opt || r.fut) { const o = r.opt || {}, fu = r.fut || {}; h += '<p><b>Derivatives:</b> ' + (fu.c ? 'the future at ' + F.inr(fu.c) + ' (basis ' + F.n(fu.b, 1) + ', OI ' + pctw(fu.doi_pct) + ' on the day); ' : '') + (o.atm_iv ? 'ATM implied volatility ' + F.n(o.atm_iv, 0) + '%, an implied move of ' + pctw(o.implied_move_pct) + ' to expiry' + (o.pcr_oi ? ', put-call ratio ' + F.n(o.pcr_oi, 2) : '') + (o.max_pain ? ', max pain ' + F.inr(o.max_pain) : '') + '.' : '') + '</p>'; }
    h += '</section>';
    /* 6 · what would change this, the risks */
    h += '<section><h2>6 · What would change this view</h2><p>' + E.share.changes(r, lt) + '</p>';
    const risks = [];
    if (p && p.rows) { const r12 = p.rows.find(function (x) { return x.h === '12m'; }) || {}; const r6 = p.rows.find(function (x) { return x.h === '6m'; }) || {}; const st = (r12.st || r6.st); if (st && st.worst_med != null) risks.push('by its own history the typical worst dip inside ' + (r12.st ? 'a year' : 'six months') + ' is ' + Math.abs(st.worst_med) + '%' + (st.p_dip != null ? ', and a dip of ' + st.dip + '%+ came in ' + st.p_dip + '% of such stretches' : '') + ' — a holder should expect to sit through one'); }
    try { const ev = ((E.lite.events || {}).rows || []).find(function (x) { return x.sym === sym; }); if (ev) risks.push('results ' + (ev.days === 0 ? 'today' : ev.days === 1 ? 'tomorrow' : ev.days < 0 ? 'were ' + Math.abs(ev.days) + ' day(s) ago' : 'in ' + ev.days + ' days') + ' — the short-term read is suspended around a print'); } catch (e) { }
    if (r.crowd && r.crowd.word === 'CROWDED') risks.push('the crowd is already in — a crowded name needs new buyers to go on and unwinds hard when they do not come');
    if (t.ext20 != null && Math.abs(t.ext20) >= 2) risks.push('stretched ' + F.n(Math.abs(t.ext20), 1) + 'σ ' + (t.ext20 > 0 ? 'above' : 'below') + ' its 20-day mean — chase nothing');
    if ((lt.turn || 0) < 5) risks.push('thin turnover (' + F.cr(lt.turn) + ' a day) — the exit is the risk');
    if (risks.length) h += '<p><b>The risks the note can see:</b> ' + esc(sent(risks)) + '</p>';
    h += '</section>';
    /* 7 · the record */
    h += '<section><h2>7 · The record</h2>' + R.record(sym) + '</section>';
    h += R.foot();
    return h + '</article>';
  };
  R.record = function (sym) {
    const rec = (E.lite && E.lite.record) || {}; const by = (rec.by_sym || {})[sym];
    const line = function (k, lab) { const x = rec[k]; if (!x || !x.n) return null; return lab + ': ' + x.n + ' graded, hit ' + x.hit + '%, average ' + F.pct(x.avg, 2) + (x.avg_excess != null ? ' (' + F.pct(x.avg_excess, 2) + ' against the Nifty)' : ''); };
    const ls = [line('short_buy', 'Short-term buys, 20 sessions on'), line('short_sell', 'Short-term sells'), line('long', 'Long-term accumulates, 60 sessions on'), line('calls_long', 'The calls of the day, long'), line('calls_short', 'The calls of the day, short'), line('path_6m', 'The path, six months on'), line('path_12m', 'The path, twelve months on')].filter(Boolean);
    let h = '<p>' + (by ? 'On ' + esc(E.lt(sym) ? E.lt(sym).nm : sym) + ' itself the engine has ' + by.n + ' graded buy-side calls: hit ' + by.hit + '%, average ' + F.pct(by.avg, 2) + '. ' : 'The engine has no graded call on this name yet. ') + (ls.length ? 'Across the market: ' + esc(ls.join('; ')) + '.' : 'The market-wide record is on Markets → Why believe this.') + '</p>';
    h += '<p class="dim">Every call is frozen the day it is made and graded when its horizon elapses; nothing is rewritten. The path\'s own record (was the six- and twelve-month lean right, did the called dip come) starts grading six months after the first v150 pass. The whole ledger is on Markets → Why believe this.</p>';
    return h;
  };
  R.foot = function () {
    return '<footer class="e-rp-foot">Written by rules from the MacroIntel engine (v' + esc(String((E.lite && E.lite.version) || '').replace(/^v/, '')) + ') — the regime, the tape, the macro DNA, the industry, the profile, the Street, the crowd, the wire. Nothing here was typed by a person. A personal research tool, free, not SEBI-registered · model output, not investment advice · prices may be delayed · the record is public and graded.</footer>';
  };
  /* the button on the research page's bar, the Home card, the Ask intent */
  R.button = function (sym) { return '<button class="e-btn sm" onclick="E.report.open(\'' + esc(sym) + '\')" title="the written note — print or save as PDF">📄 Note</button>'; };
  R.card = function () {
    return '<div class="cd e-rpcard"><div class="e-between" style="flex-wrap:wrap;gap:10px"><div><div class="lbl" style="margin:0">A research note for every company</div><div style="font-size:13px;color:var(--tx);line-height:1.55;margin-top:4px">Every listed name gets a written note — the verdict, the path (one month to twelve, with the dips), the case, what the macro does to it, the company, the Street and the crowd, what would change the view, and the engine\'s own graded record. Regenerated every pass; print it or save it as a PDF.</div></div></div><div class="e-row" style="margin-top:10px;gap:8px"><input class="e-in" id="e-rp-q" placeholder="a company — HDFC Bank, Reliance, Cupid…" onkeydown="if(event.key===\'Enter\')E.report.open(this.value)" style="flex:1;min-width:200px"><button class="e-btn p" onclick="E.report.open(document.getElementById(\'e-rp-q\').value)">open the note</button></div></div>';
  };
})(window.E);
