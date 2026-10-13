/* ═══ v144 · THE RESEARCH PAGE — tap any share ═══ */
(function (E) {
  const F = E.f, L = E.live;
  const S = E.share = { open: false, sym: null, row: null, range: '1d', timer: null, seen: {}, qty: 0, cost: 0 };

  function ensure() {
    let el = document.getElementById('e-share'); if (el) return el;
    el = document.createElement('div'); el.id = 'e-share'; el.className = 'e-share';
    el.innerHTML = '<div class="e-sh-bar"><button class="e-sh-x" onclick="E.closeShare()" title="back (Esc)">←</button><div><div class="nm" id="e-sh-nm"></div><div class="sy" id="e-sh-sy"></div></div><div class="px"><div class="v" id="e-sh-px"></div><div class="d" id="e-sh-d"></div><div class="s" id="e-sh-s"></div></div></div><div class="e-sh-body" id="e-sh-body"></div>';
    document.body.appendChild(el);
    document.addEventListener('keydown', function (e) { try { if (e.key === 'Escape' && S.open) E.closeShare(); } catch (x) { } });
    window.addEventListener('popstate', function (e) { try { const st = e.state || {}; if (st.e_share) E.openShare(st.e_share, { nopush: true, quick: true }); else if (st.e_ind) E.industry.open(st.e_ind, { nopush: true }); else if (S.open) E.closeShare({ nopop: true }); } catch (x) { } });
    return el;
  }
  E.closeShare = function (opt) { opt = opt || {}; const el = document.getElementById('e-share'); if (el) el.classList.remove('open'); document.body.classList.remove('e-share-open'); S.open = false; S.sym = null; if (S.timer) { clearTimeout(S.timer); S.timer = null; } try { if (!opt.nopop && history.state && history.state.e_share) history.back(); } catch (e) { } try { E.industry.close({ nopop: true }); } catch (e) { } };

  /* every old click handler calls openShare(name) — route it here */
  E.openShare = async function (q, opt) {
    opt = opt || {}; const Q = String(q || '').trim(); if (!Q) return;
    if (!E.lite) { try { if (typeof window.__oldOpenShare === 'function') return window.__oldOpenShare(Q, opt); } catch (e) { } E.toast('the engine is not on the page yet'); return; }
    let sym = (E.lite.names[Q.toUpperCase()] ? Q.toUpperCase() : null) || E.one(Q);
    if (!sym) { const ind = E.industry.find(Q); if (ind.length) return E.industry.open(ind[0], opt); E.toast('Nothing listed as "' + Q + '"'); return; }
    const el = ensure(); const body = document.getElementById('e-sh-body');
    if (S.timer) { clearTimeout(S.timer); S.timer = null; }
    S.open = true; S.sym = sym; S.range = '1d'; S.row = null; S._fell = false; S._fellNote = '';
    el.classList.add('open'); document.body.classList.add('e-share-open'); el.scrollTop = 0;
    try { if (!opt.nopush) history.pushState({ e_share: sym }, '', '#s=' + encodeURIComponent(sym)); } catch (e) { }
    const lt = E.lt(sym) || {};
    document.getElementById('e-sh-nm').textContent = lt.nm || sym;
    document.getElementById('e-sh-sy').textContent = sym + (lt.sector ? ' · ' + lt.sector : '') + (lt.fno ? ' · F&O' : '') + (lt.x === 'BSE' ? ' · BSE only' : '');
    S.paintPrice();
    L.want([sym]);
    const quick = !!opt.quick || !!S.seen[sym]; S.seen[sym] = 1;
    const steps = [['Reading the regime', 'regime'], ['Placing the sector', 'sector'], ['Reading the tape', 'tape'], ['Measuring macro DNA', 'dna'], ['Reading the company', 'company'], ['Running the models and the books', 'models'], ['Writing the verdict', 'verdict']];
    body.innerHTML = '<div class="e-work"><div class="t"><span class="e-spin"></span> Working — building the research on <b>' + F.esc(lt.nm || sym) + '</b> <span style="margin-left:auto;font-size:12px;color:var(--dim);cursor:pointer" onclick="E.share.skip()">skip →</span></div><div class="e-steps" id="e-steps">' + steps.map(function (s, i) { return '<div class="st" id="e-st-' + i + '"><div class="ic"></div><div><div>' + s[0] + '</div><div class="out" id="e-st-out-' + i + '"></div></div></div>'; }).join('') + '</div></div>';
    const rowP = E.row(sym); const fullP = E.loadFull();
    let i = 0; const dt = quick ? 120 : 650; S._skip = false;
    const tick = async function () {
      if (!S.open || S.sym !== sym) return;
      const row = await rowP; S.row = row; await fullP;
      if (i < steps.length) {
        const st = document.getElementById('e-st-' + i); if (st) { st.classList.add('on'); const out = document.getElementById('e-st-out-' + i); if (out) out.textContent = S.stepLine(steps[i][1], row, lt); }
        if (i > 0) { const p = document.getElementById('e-st-' + (i - 1)); if (p) { p.classList.remove('on'); p.classList.add('done'); p.querySelector('.ic').textContent = '✓'; } }
        i++;
        if (S._skip) { S.render(); return; }
        S.timer = setTimeout(tick, dt);
      } else { S.render(); }
    };
    tick();
  };
  S.skip = function () { S._skip = true; };
  S.paintPrice = function () {
    try { const sym = S.sym; if (!sym) return; const p = L.px(sym), d = L.d1(sym); const q = L.q(sym);
      document.getElementById('e-sh-px').textContent = F.inr(p); const dd = document.getElementById('e-sh-d'); dd.textContent = F.pct(d, 2); dd.className = 'd ' + F.tone(d);
      document.getElementById('e-sh-s').textContent = q ? ('live · ' + F.ist(q.t) + ' IST · ' + F.ago(q.t)) : ('last close · ' + ((E.lite && E.lite.bhav_date) || ''));
      const hp = document.getElementById('e-sh-hold'); if (hp && S.qty) S.holdLine();
    } catch (e) { } };
  E.onLiveHook(function () { if (S.open) { S.paintPrice(); if (S.range === '1d' && L.inHours()) S.drawChart(); } });

  S.stepLine = function (k, r, lt) {
    const M = E.lite.market || {}; const sec = (E.lite.sectors || {})[lt.sector] || null;
    try {
      if (k === 'regime') return (M.regime || '—') + ' · the page\'s regime engine' + (sec && sec.edge && sec.edge.ann_pct != null ? ' · ' + lt.sector + ' has returned ' + F.pct(sec.edge.ann_pct, 0) + '/yr in ' + M.regime + ' regimes (t ' + sec.edge.t + ')' : '');
      if (k === 'sector') return sec ? (lt.sector + ': ' + sec.word + ' · ' + sec.above200 + '% of ' + sec.n + ' names above the 200-day · ' + F.pct(sec.rel60, 1) + ' vs the Nifty over 60 sessions') : (lt.sector || 'unmapped') + ' · too few names to read as a sector';
      if (!r) return 'only a price and a day on file';
      const t = r.tape || {};
      if (k === 'tape') return F.pct(t.r20) + ' over 20 sessions · ' + F.pct(t.r60) + ' over 60 · ' + F.pct(t.r250, 0) + ' over a year · ' + (t.vs200 != null ? (t.vs200 >= 0 ? 'above' : 'below') + ' the 200-day (' + F.pct(t.vs200) + ')' : '') + ' · σ ' + (t.sig1d || '—') + '%/day';
      if (k === 'dna') { const d = r.dna; if (!d) return 'not enough weekly history for betas'; const b = d.b || {}; return 'β Nifty ' + F.n(b.nifty, 2) + ' · rupee ' + F.sgn(b.inr, 2) + ' · crude ' + F.sgn(b.brent, 2) + ' · rates ' + F.sgn(b.rates, 2) + ' · VIX ' + F.sgn(b.vix, 2) + ' · R² ' + F.n(d.r2, 2) + ' on ' + d.n + ' weeks'; }
      if (k === 'company') { const f = r.fund; if (!f) return 'the profile arrives with the fundamentals rotation (Yahoo) — scored on the tape and the macro meanwhile'; return (f.industry || '') + ' · mcap ' + F.big(f.mcap) + ' · P/E ' + F.n(f.pe, 1) + ' · ROE ' + F.n(f.roe, 0) + '% · revenue ' + F.pct(f.revg, 0); }
      if (k === 'models') { const c = r.cont; const held = S.held(S.sym); return (c ? ('contenders: ' + Math.round(100 * (c.p_move || 0)) + '% odds of a ≥1.5σ move, p(up) ' + Math.round(100 * (c.p_up || 0.5)) + '%') : 'the contenders model has no read on it this pass') + ' · ' + (held.length ? held.length + ' book' + (held.length > 1 ? 's hold' : ' holds') + ' it' : 'no book holds it'); }
      if (k === 'verdict') { const v = r.v || {}; return 'today ' + (((v.intra || {}).side) || 'no trade') + ' · 5–60 sessions ' + (((v.short || {}).side) || 'no trade') + ' · 12 months ' + (((v.long || {}).side) || 'no view'); }
    } catch (e) { }
    return '';
  };
  S.held = function (sym) { const out = []; try { const A = (window.AGENTS && AGENTS.agents) || {}; Object.keys(A).forEach(function (k) { (A[k].positions || []).forEach(function (p) { if (String(p.key || p.name).toUpperCase().replace('.NS', '') === sym) out.push({ book: A[k].nm || k, side: p.side, entry: p.entry, ret: p.ret_pct, why: p.why || p.reason, at: p.entry_at }); }); }); } catch (e) { } return out; };

  E.loadFull = function () { if (E.full) return Promise.resolve(E.full); if (E._fullP) return E._fullP; E._fullP = fetch(E.url('engine_full.json'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { E.full = j || { sectors_members: {} }; return E.full; }).catch(function () { E.full = { sectors_members: {} }; return E.full; }); return E._fullP; };

  /* ── the page ── */
  S.render = function () {
    const sym = S.sym, r = S.row, lt = E.lt(sym) || {}; const body = document.getElementById('e-sh-body'); if (!body) return;
    if (!r) { body.innerHTML = S.thin(sym, lt); return; }
    const v = r.v || {}; const vs = v.short || {}, vl = v.long || {}, vi = v.intra || {}; const t = r.tape || {}; const M = E.lite.market || {};
    let h = '';
    /* 1 · the verdict */
    h += '<div class="e-verd">';
    h += S.vcard('Today · intraday', vi.side, vi.score, null, vi.side ? [['Entry zone', F.inr(vi.entry && vi.entry[0]) + ' – ' + F.inr(vi.entry && vi.entry[1])], ['Stop', F.inr(vi.stop)], ['Target', F.inr(vi.target)], ['Expected range', F.inr(vi.range && vi.range[0]) + ' – ' + F.inr(vi.range && vi.range[1])], ['Flat by', vi.flat_by || '15:20']] : [['Expected range', vi.range ? (F.inr(vi.range[0]) + ' – ' + F.inr(vi.range[1])) : '—'], ['σ a day', (vi.sig1d != null ? vi.sig1d + '%' : (t.sig1d != null ? t.sig1d + '%' : '—'))]], vi.side ? ['the intraday screen: ' + (vi.lean > 0 ? 'a long lean' : 'a short lean') + ' of ' + F.n(Math.abs(vi.lean || 0), 2) + ' from the futures book, yesterday\'s direction and the contenders'] : [v.intra ? 'no clear lean today — the range is the plan' : 'not liquid enough for intraday'], 'intra');
    h += S.vcard('Short term · 5–60 sessions', vs.side, vs.score, vs.conv, vs.side ? [['Entry', F.inr(vs.entry)], ['Stop', F.inr(vs.stop) + ' (' + F.pct(vs.side === 'SELL' ? vs.stop_pct : -vs.stop_pct, 1) + ')'], ['Target', F.inr(vs.target) + ' (' + F.pct(vs.side === 'SELL' ? -vs.tgt_pct : vs.tgt_pct, 1) + ')'], ['Horizon', (vs.h || '—') + ' sessions'], ['Size', (vs.size_pct != null ? vs.size_pct + '% of capital' : '—')], ['Reward : risk', '2 : 1']] : [['Score', (vs.score != null ? Math.round(vs.score) + '/100' : '—')], ['Buy above', '80 · sell below 10 (F&O)']], vs.why || (vs.thin ? ['too little history to score'] : vs.illiquid ? ['below the liquidity floor (₹5 cr a day) — scored, not traded'] : ['no trade: the score sits between the bars']), 'short');
    h += S.vcard('Long term · 12 months', vl.side, vl.score, vl.conv, (vl.target != null) ? [['12-month target', F.inr(vl.target) + ' (' + F.pct(vl.exp_pct, 0) + ')'], ['Band', F.inr(vl.band && vl.band[0]) + ' – ' + F.inr(vl.band && vl.band[1])], ['Exit below', F.inr(vl.stop) + ' · ' + (vl.stop_note || '')]] : [['Score', (vl.score != null ? Math.round(vl.score) + '/100' : '—')]], vl.why || (vl.thin ? ['too little history to score'] : ['no view: the score sits between the bars (accumulate above 80, avoid below 20)']), 'long');
    h += '</div>';
    h += '<div class="e-note">' + F.esc(E.note(v.note)) + (M.gate ? ' · the gate is on today: sizes are halved' : '') + '</div>';
    if (v.fno) h += '<div class="cd" style="margin-top:10px"><div class="e-between"><div><div class="lbl">F&O · the trade in lots</div><div style="font-size:15px;color:#fff;font-weight:600">' + F.esc(v.fno.side) + ' ' + v.fno.lots + ' lot' + (v.fno.lots > 1 ? 's' : '') + ' of ' + F.esc(v.fno.contract) + ' <span class="e-tag">lot ' + v.fno.lot + ' · ' + F.esc(v.fno.lot_src) + '</span></div></div><div class="e-kv" style="min-width:320px"><div class="c"><div class="k">Risk per lot</div><div class="v">' + F.big(v.fno.risk_lot) + '</div></div><div class="c"><div class="k">Potential per lot</div><div class="v e-up">' + F.big(v.fno.pot_lot) + '</div></div><div class="c"><div class="k">Margin (est.)</div><div class="v">' + F.big(v.fno.margin_est) + '</div></div></div></div><div class="note">lots sized so one stop costs 1% of a ₹10 lakh book · basis ' + F.n(v.fno.basis, 1) + ' · OI ' + F.pct(v.fno.oi_chg, 1) + ' on the day · the chain is on Markets → F&O</div></div>';
    /* 2 · the score, in parts */
    const sc = r.sc || {};
    h += E.sectionHead('The score, in parts', 'every leg is a percentile of the market — the composite is what the cards show');
    h += '<div class="cd"><div class="e-grid e-g2"><div class="e-bars">' + [['Trend · short', sc.T], ['Trend · long', sc.TL], ['Macro · short', sc.M], ['Macro · long', sc.ML], ['Quality', sc.Q], ['Futures flow', sc.F], ['Contenders', sc.C], ['Risk (calm = high)', sc.R]].map(function (x) { return '<div class="r"><div class="k">' + x[0] + '</div><div class="e-bar"><i style="width:' + Math.max(2, Math.min(100, x[1] || 0)) + '%;background:' + ((x[1] || 50) >= 65 ? 'var(--grn)' : (x[1] || 50) <= 35 ? 'var(--red)' : 'var(--blu)') + '"></i></div><div class="v">' + (x[1] != null ? Math.round(x[1]) : '—') + '</div></div>'; }).join('') + '</div><div>' +
      '<div class="e-kv">' + [['Short-term score', sc.short != null ? Math.round(sc.short) : '—', 'buy ≥ 80 · sell ≤ 10'], ['Long-term score', sc.long != null ? Math.round(sc.long) : '—', 'accumulate ≥ 80 · avoid ≤ 20'], ['Intraday score', sc.intra != null ? Math.round(sc.intra) : '—', 'how much it is in play'], ['Quality', (r.fund ? Math.round(sc.Q) : 'n/a'), r.fund ? 'from the profile' : 'no profile yet — neutral 50']].map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div><div class="s">' + x[2] + '</div></div>'; }).join('') + '</div>' +
      (r.wind ? '<div class="note" style="margin-top:10px"><b>The macro wind this month: ' + F.pct(r.wind.total, 1) + '</b> — what the last four weeks of macro moves explained of this share\'s move: ' + (r.wind.parts || []).map(function (p) { return E.FACTOR[p[0]] + ' ' + F.pct(p[1], 1); }).join(', ') + '.</div>' : '') + '</div></div></div>';
    /* 3 · the chart */
    h += E.sectionHead('The chart', 'today live when a door is open · one year with the model\'s levels · five years weekly');
    h += '<div class="subtabs">' + [['1d', 'Today · live'], ['1y', '1 year · the levels'], ['5y', 'Long · weekly']].map(function (x) { return '<button class="subtab' + (S.range === x[0] ? ' a' : '') + '" onclick="E.share.setRange(\'' + x[0] + '\')">' + x[1] + '</button>'; }).join('') + '<span style="flex:1"></span>' + L.chip() + '</div>';
    h += '<div class="e-chart" id="e-sh-chart"><canvas id="e-sh-cv"></canvas><div class="lg" id="e-sh-lg"></div></div>';
    /* 4 · the company */
    h += E.sectionHead('The company', r.fund ? ('the profile · Yahoo Finance · ' + F.esc(r.fund.asof || '')) : 'the profile arrives with the fundamentals rotation after the first pass');
    h += S.company(sym, r, lt);
    /* 5 · macro DNA */
    h += E.sectionHead('Macro DNA', 'how this share moves with the five things that move India — measured on weekly returns, with its record in every regime');
    h += S.dna(r, lt);
    /* 6 · the shock simulator */
    h += E.sectionHead('What if…', 'the shock simulator — the share, its sector and your holding under a macro shock');
    h += S.simulator(sym, r, lt);
    /* 7 · derivatives */
    if (r.fut || r.opt) { h += E.sectionHead('Derivatives', 'the future and what options price'); h += S.derivs(r); }
    /* 8 · the contenders */
    if (r.cont) { h += E.sectionHead('The contenders model', 'odds of a move, the side, the distribution of outcomes'); h += S.contenders(r); }
    /* 9 · peers, the industry, the books, the wire */
    h += E.sectionHead('Peers · ' + F.esc(lt.sector || ''), 'the sector by turnover, each with its own verdict', '<span class="act" onclick="E.industry.open(\'' + F.esc(lt.sector || '') + '\')">the industry overview →</span>');
    h += S.peers(sym, lt);
    const held = S.held(sym);
    h += E.sectionHead('The books', held.length ? (held.length + ' of the twelve hold it') : 'no book holds it today', '<span class="act" onclick="E.closeShare();E.go(\'agents\')">the arena →</span>');
    h += held.length ? '<div class="e-list">' + held.map(function (x) { return '<div class="e-li" style="cursor:default"><div class="n">' + F.esc(x.book) + '<small>' + F.esc(x.side) + ' from ' + F.inr(x.entry) + (x.at ? ' · ' + F.esc(x.at) : '') + '</small><div style="font-size:11.5px;color:var(--dim);font-weight:400;margin-top:2px">' + F.esc(x.why || '') + '</div></div><div class="' + F.tone(x.ret) + ' e-mono">' + F.pct(x.ret, 2) + '</div><div></div></div>'; }).join('') + '</div>' : '<div class="e-empty">the books choose from the engine\'s buys and sells with their own temperament — none has taken this one</div>';
    h += E.sectionHead('The wire', 'headlines that name it · the models read price and macro, not news', '<a class="act" target="_blank" rel="noopener" href="https://news.google.com/search?q=' + encodeURIComponent((lt.nm || sym) + ' stock') + '">Google News →</a>');
    h += S.wire(sym, lt);
    /* 10 · what would change this */
    h += E.sectionHead('What would change this', 'the levels and the turns that flip the verdict');
    h += '<div class="cd" style="font-size:13px;line-height:1.6">' + S.changes(r, lt) + '</div>';
    /* 11 · in plain words */
    h += E.sectionHead('In plain words', 'the same numbers as a message', '<span class="act" onclick="E.copy(document.getElementById(\'e-sh-plain\').innerText)">copy for WhatsApp</span>');
    h += '<div class="cd" id="e-sh-plain" style="white-space:pre-wrap;font-size:13px;line-height:1.6">' + F.esc(S.plain(sym, r, lt)) + '</div>';
    /* 12 · ask */
    h += '<div style="margin-top:22px">' + E.ask.box('e-sh-ask', sym) + '</div>';
    h += '<div class="e-row" style="margin-top:16px;gap:8px"><button class="e-btn" data-watch="' + F.esc(sym) + '" onclick="E.watchToggle(\'' + F.esc(sym) + '\')">' + (E.watchHas(sym) ? '★ On my list' : '☆ Add to my list') + '</button><button class="e-btn" onclick="E.closeShare();E.go(\'micro\',\'short\')">more like this →</button></div>';
    h += '<div class="e-foot">built ' + F.ist() + ' IST from the engine (' + F.esc(E.lite.generated || '') + ') · bhavcopy ' + F.esc(E.lite.bhav_date || '') + ' · prices live when a door is open · educational, not investment advice · nothing typed, nothing a broker said</div>';
    body.innerHTML = h;
    S.drawChart();
    S.simRun();
  };
  S.vcard = function (title, side, score, conv, kv, why, kind) {
    const cls = F.cls(side);
    return '<div class="e-vc ' + cls + '"><div class="h"><span>' + title + '</span><span class="e-score">' + (score != null ? Math.round(score) + '/100' : '') + '</span></div><div class="w">' + F.word(side, 'big') + (conv ? '<span class="conv">' + conv + ' conviction</span>' : '') + '</div><div class="kv">' + (kv || []).map(function (x) { return '<div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div>'; }).join('') + '</div>' + ((why && why.length) ? '<div class="why"><ul>' + why.map(function (w) { return '<li>' + F.esc(w) + '</li>'; }).join('') + '</ul></div>' : '') + '</div>';
  };
  S.thin = function (sym, lt) {
    let h = '<div class="e-verd"><div class="e-vc none"><div class="h"><span>Today</span></div><div class="w">' + F.word(null, 'big') + '</div><div class="why">only a price and a day on file for this listing</div></div><div class="e-vc none"><div class="h"><span>Short term</span></div><div class="w">' + F.word(null, 'big') + '</div><div class="why">not scored — no weekly history reaches the engine for it yet</div></div><div class="e-vc none"><div class="h"><span>Long term</span></div><div class="w">' + F.word(null, 'big') + '</div><div class="why">not scored</div></div></div>';
    h += '<div class="e-note">' + F.esc(E.note(9)) + (lt.x === 'BSE' ? ' · a BSE-only listing (scrip ' + F.esc(lt.code || '') + ')' : '') + '</div>';
    h += '<div class="e-kv" style="margin-top:12px"><div class="c"><div class="k">Last close</div><div class="v">' + F.inr(lt.px) + '</div></div><div class="c"><div class="k">The day</div><div class="v ' + F.tone(lt.d1) + '">' + F.pct(lt.d1, 2) + '</div></div><div class="c"><div class="k">Turnover</div><div class="v">' + F.cr(lt.turn) + '</div></div></div>';
    h += E.sectionHead('Elsewhere', 'the profile and the news'); h += S.links(sym, lt);
    h += '<div style="margin-top:22px">' + E.ask.box('e-sh-ask', sym) + '</div>';
    return h;
  };
  S.links = function (sym, lt) {
    const nm = lt.nm || sym; const bse = lt.x === 'BSE';
    const links = [['Google Finance', bse ? ('https://www.google.com/finance/quote/' + encodeURIComponent(lt.code || sym) + ':BOM') : ('https://www.google.com/finance/quote/' + encodeURIComponent(sym) + ':NSE')], ['Wikipedia', 'https://en.wikipedia.org/w/index.php?search=' + encodeURIComponent(nm + ' company')], ['Screener', 'https://www.screener.in/company/' + encodeURIComponent(bse ? (lt.code || sym) : sym) + '/consolidated/'], [bse ? 'BSE' : 'NSE', bse ? ('https://www.bseindia.com/stock-share-price/x/x/' + encodeURIComponent(lt.code || '') + '/') : ('https://www.nseindia.com/get-quotes/equity?symbol=' + encodeURIComponent(sym))], ['Yahoo Finance', 'https://finance.yahoo.com/quote/' + encodeURIComponent(sym + (bse ? '.BO' : '.NS'))], ['TradingView', 'https://www.tradingview.com/symbols/' + (bse ? 'BSE' : 'NSE') + '-' + encodeURIComponent(sym) + '/'], ['Trendlyne', 'https://trendlyne.com/equity/' + encodeURIComponent(sym) + '/'], ['Google News', 'https://news.google.com/search?q=' + encodeURIComponent(nm + ' stock')]];
    return '<div class="e-links">' + links.map(function (l) { return '<a target="_blank" rel="noopener" href="' + l[1] + '">' + l[0] + ' ↗</a>'; }).join('') + '</div>';
  };
  S.company = function (sym, r, lt) {
    const f = r.fund; const t = r.tape || {};
    let h = '<div class="cd">';
    if (f) {
      h += '<div class="e-between"><div><div class="e-h3">' + F.esc(f.lname || lt.nm || sym) + '</div><div class="e-sub">' + F.esc(f.industry || '') + (f.ysector ? ' · ' + F.esc(f.ysector) : '') + (f.staff ? ' · ' + F.n(f.staff, 0) + ' employees' : '') + (f.web ? ' · <a target="_blank" rel="noopener" href="' + F.esc(f.web) + '">' + F.esc(String(f.web).replace(/^https?:\/\/(www\.)?/, '')) + '</a>' : '') + '</div></div></div>';
      if (f.summary) h += '<div style="font-size:13px;color:var(--tx);line-height:1.6;margin:10px 0 12px;max-width:900px">' + F.esc(f.summary) + '</div>';
      const kv = [['Market cap', F.big(f.mcap), ''], ['P/E', F.n(f.pe, 1), f.fpe ? 'forward ' + F.n(f.fpe, 1) : ''], ['P/B', F.n(f.pb, 2), f.bv ? 'book ' + F.inr(f.bv) : ''], ['ROE', f.roe != null ? F.n(f.roe, 1) + '%' : '—', ''], ['Net margin', f.margin != null ? F.n(f.margin, 1) + '%' : '—', f.opm != null ? 'operating ' + F.n(f.opm, 1) + '%' : ''], ['Revenue growth', F.pct(f.revg, 1), f.rev ? F.big(f.rev) + ' trailing' : ''], ['EPS growth', F.pct(f.epsg, 1), f.eps != null ? 'EPS ' + F.inr(f.eps) : ''], ['Debt / equity', f.de != null ? F.n(f.de, 0) + '%' : '—', ''], ['Dividend yield', f.divy != null ? F.n(f.divy, 2) + '%' : '—', ''], ['Promoter / insiders', f.promoter != null ? F.n(f.promoter, 1) + '%' : '—', ''], ['EV / EBITDA', F.n(f.ev_ebitda, 1), ''], ['52-week range', F.inr(f.lo52 || t.lo52) + ' – ' + F.inr(f.hi52 || t.hi52), t.pos52 != null ? Math.round(t.pos52 * 100) + '% of the range' : '']];
      if (f.street_tgt) kv.push(['Street target', F.inr(f.street_tgt), (f.street_n ? f.street_n + ' analysts' : '') + (f.street_rec ? ' · ' + F.esc(f.street_rec) : '')]);
      h += '<div class="e-kv">' + kv.map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div>' + (x[2] ? '<div class="s">' + x[2] + '</div>' : '') + '</div>'; }).join('') + '</div>';
      const sp = (E.lite.sector_pe || {})[lt.sector];
      if (sp && f.pe > 0) h += '<div class="note">P/E ' + F.n(f.pe, 1) + ' against the sector median ' + F.n(sp, 1) + ' — ' + (f.pe < sp * 0.8 ? 'cheaper than its peers' : f.pe > sp * 1.25 ? 'dearer than its peers' : 'in line with its peers') + '. Quality score ' + Math.round(r.sc.Q) + '/100' + ((r.sc.qwhy || []).length ? ' (' + r.sc.qwhy.join(', ') + ')' : '') + '.</div>';
    } else {
      h += '<div class="e-sub">The business profile — P/E, ROE, margins, growth, debt, promoter holding, what the company does — is read from Yahoo Finance on a rotation after each pipeline pass (≈150 names a pass, the whole market over a day). Until it arrives this name is scored on the tape, the macro and the derivatives, and its quality leg sits at neutral.</div>';
      h += '<div class="e-kv" style="margin-top:10px">' + [['Last close', F.inr(lt.px)], ['Turnover / day', F.cr(lt.turn)], ['52-week range', F.inr(t.lo52) + ' – ' + F.inr(t.hi52)], ['σ a day', t.sig1d != null ? t.sig1d + '%' : '—']].map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div></div>'; }).join('') + '</div>';
    }
    h += S.links(sym, lt) + '</div>';
    return h;
  };
  S.dna = function (r, lt) {
    const d = r.dna; if (!d) return '<div class="e-empty">not enough weekly history to measure betas — the DNA appears once the engine has a year of weekly returns</div>';
    const b = d.b || {}, tt = d.t || {}; const sec = (E.lite.sectors || {})[lt.sector] || {}; const sd = sec.dna || {};
    const read = function (k, v) { const a = Math.abs(v || 0); const w = (Math.abs(tt[k] || 0) < 1.5) ? 'weak' : (Math.abs(tt[k] || 0) >= 2.5 ? 'strong' : 'fair'); if (k === 'nifty') return v >= 1.2 ? 'a high-beta name' : v >= 0.8 ? 'moves with the market' : v >= 0.4 ? 'a low-beta name' : 'barely tracks the index'; if (k === 'inr') return v > 0.3 ? 'gains when the rupee weakens (an exporter\'s profile)' : v < -0.3 ? 'hurt by a weaker rupee (imports, dollar debt)' : 'rupee-neutral'; if (k === 'brent') return v > 0.15 ? 'rises with crude' : v < -0.15 ? 'hurt by dearer crude' : 'crude-neutral'; if (k === 'rates') return v < -0.3 ? 'hurt by rising yields (rate-sensitive)' : v > 0.3 ? 'gains when yields rise' : 'rate-neutral'; if (k === 'vix') return v < -0.1 ? 'sells off when fear rises' : v > 0.1 ? 'holds up in fear' : 'indifferent to VIX'; return ''; };
    let h = '<div class="cd"><div class="e-grid e-g2"><div class="e-dna">' + ['nifty', 'inr', 'brent', 'rates', 'vix'].map(function (k) { const v = b[k]; const mx = k === 'nifty' ? 2 : 1; const pct = Math.max(-1, Math.min(1, (v || 0) / mx)); const left = pct >= 0 ? 50 : 50 + pct * 50; const w = Math.abs(pct) * 50; return '<div class="r"><div class="k">' + E.FACTOR[k] + '</div><div class="bar"><b></b><i style="left:' + left + '%;width:' + w + '%;background:' + ((v || 0) >= 0 ? 'var(--grn)' : 'var(--red)') + '"></i></div><div class="v">' + F.sgn(v, 2) + '</div><div class="t">t ' + F.n(tt[k], 1) + '</div></div>'; }).join('') + '<div style="font-size:11px;color:var(--mut);margin-top:6px">β = % move of the share per 1% move of the factor (weekly, ' + d.n + ' weeks, ridge) · R² ' + F.n(d.r2, 2) + ' · |t| &lt; 1.5 is weak evidence</div></div>';
    h += '<div><div class="lbl">What it means</div><ul style="margin:4px 0 10px 18px;font-size:12.5px;line-height:1.6;color:var(--tx)">' + ['nifty', 'inr', 'brent', 'rates', 'vix'].map(function (k) { return '<li><b>' + E.FACTOR_SHORT[k] + '</b> — ' + read(k, b[k]) + (Math.abs(tt[k] || 0) < 1.5 ? ' <span style="color:var(--mut)">(weak)</span>' : '') + '</li>'; }).join('') + '</ul>';
    if (sd && sd.nifty != null) h += '<div class="lbl">The sector\'s DNA · ' + F.esc(lt.sector) + '</div><div style="font-size:12px;color:var(--dim)">' + ['nifty', 'inr', 'brent', 'rates', 'vix'].map(function (k) { return E.FACTOR_SHORT[k] + ' ' + F.sgn(sd[k], 2); }).join(' · ') + '</div>';
    const rg = d.regime || {}; const M = E.lite.market || {};
    if (Object.keys(rg).length) h += '<div class="lbl" style="margin-top:10px">Its record by regime · excess over the Nifty, annualised</div><table class="tbl" style="width:100%"><thead><tr><th>regime</th><th>vs Nifty /yr</th><th>weeks</th><th>hit</th></tr></thead><tbody>' + ['Reflation', 'Goldilocks', 'Stagflation', 'Disinflation'].map(function (k) { const x = rg[k]; if (!x) return ''; return '<tr' + (k === M.regime ? ' style="background:rgba(78,161,255,.08)"' : '') + '><td>' + k + (k === M.regime ? ' <span class="e-tag">now</span>' : '') + '</td><td class="' + F.tone(x.ann) + '">' + F.pct(x.ann, 0) + '</td><td>' + x.n + '</td><td>' + (x.hit != null ? x.hit + '%' : '—') + '</td></tr>'; }).join('') + '</tbody></table>';
    h += '</div></div></div>';
    return h;
  };
  /* ── the shock simulator ── */
  S.simulator = function (sym, r, lt) {
    const P = (E.lite.shock || {}).presets || {}; const lv = (E.lite.shock || {}).levels || {};
    let h = '<div class="cd"><div class="e-row" style="margin-bottom:10px">' + Object.keys(P).map(function (k) { return '<span class="e-chip" onclick="E.share.simPreset(\'' + k + '\')">' + F.esc(P[k].label) + '</span>'; }).join('') + '<span class="e-chip" onclick="E.share.simPreset(null)">reset</span></div>';
    h += '<div class="e-sim"><div>' + [['nifty', 'Nifty', -10, 10, 0.5, '%'], ['inr', 'USD/INR', -6, 6, 0.25, '%'], ['brent', 'Brent', -30, 30, 1, '%'], ['rates10', '10Y yield', -100, 100, 5, 'bp'], ['vix', 'India VIX', -40, 60, 5, '%']].map(function (x) { return '<div class="e-sl"><div class="k">' + x[1] + '</div><input type="range" id="e-sim-' + x[0] + '" min="' + x[2] + '" max="' + x[3] + '" step="' + x[4] + '" value="0" oninput="E.share.simRun()"><div class="v" id="e-sim-v-' + x[0] + '">0' + x[5] + '</div></div>'; }).join('') +
      '<div class="e-sl" style="margin-top:8px"><div class="k">Your holding</div><div class="e-row" style="gap:6px"><input class="e-input" style="padding:7px 10px;font-size:13px;width:110px" type="number" placeholder="shares" id="e-sim-qty" oninput="E.share.simRun()" value="' + (S.qty || '') + '"><input class="e-input" style="padding:7px 10px;font-size:13px;width:130px" type="number" placeholder="avg cost ₹" id="e-sim-cost" oninput="E.share.simRun()" value="' + (S.cost || '') + '"></div><div></div></div>' +
      '<div style="font-size:11px;color:var(--mut);margin-top:8px">now: Nifty ' + F.n(lv.nifty, 0) + ' · USD/INR ' + F.n(lv.inr, 2) + ' · Brent $' + F.n(lv.brent, 0) + ' · 10Y ' + F.n(lv.gsec10, 2) + '% · VIX ' + F.n(lv.vix, 1) + ' · repo ' + F.n(lv.repo, 2) + '%</div></div>';
    h += '<div class="e-sim-out" id="e-sim-out"></div></div><div class="note" id="e-sim-note"></div></div>';
    return h;
  };
  S.simPreset = function (k) {
    const P = (E.lite.shock || {}).presets || {}; const p = k ? P[k] : null;
    const set = function (id, v) { const el = document.getElementById('e-sim-' + id); if (el) el.value = v || 0; };
    set('nifty', p ? p.nifty : 0); set('inr', p ? p.inr : 0); set('brent', p ? p.brent : 0); set('vix', p ? p.vix : 0);
    set('rates10', p ? Math.round((p.rates || 0) / 4.5 * 100) : 0);
    const nt = document.getElementById('e-sim-note'); if (nt) nt.textContent = p ? p.note : '';
    S.simRun();
  };
  S.simRun = function () {
    try {
      const r = S.row; if (!r) return; const out = document.getElementById('e-sim-out'); if (!out) return;
      const g = function (id) { const el = document.getElementById('e-sim-' + id); return el ? +el.value : 0; };
      const x = { nifty: g('nifty'), inr: g('inr'), brent: g('brent'), vix: g('vix'), rates: 4.5 * g('rates10') / 100 };
      ['nifty', 'inr', 'brent', 'vix'].forEach(function (k) { const el = document.getElementById('e-sim-v-' + k); if (el) el.textContent = F.sgn(x[k], k === 'inr' ? 2 : 1) + '%'; });
      const rel = document.getElementById('e-sim-v-rates10'); if (rel) rel.textContent = F.sgn(g('rates10'), 0) + 'bp';
      const b = (r.dna && r.dna.b) || null; const lt = E.lt(S.sym) || {}; const sd = ((E.lite.sectors || {})[lt.sector] || {}).dna || null;
      if (!b) { out.innerHTML = '<div class="e-sub">no betas for this name yet</div>'; return; }
      let d = 0; const parts = []; ['nifty', 'inr', 'brent', 'rates', 'vix'].forEach(function (k) { const c = (b[k] || 0) * x[k]; d += c; if (Math.abs(x[k]) > 0) parts.push([k, c]); });
      let ds = null; if (sd) { ds = 0; ['nifty', 'inr', 'brent', 'rates', 'vix'].forEach(function (k) { ds += (sd[k] || 0) * x[k]; }); }
      const px = L.px(S.sym) || lt.px || 0; S.qty = +(document.getElementById('e-sim-qty') || {}).value || 0; S.cost = +(document.getElementById('e-sim-cost') || {}).value || 0;
      const val = S.qty * px; const dv = val * d / 100;
      out.innerHTML = '<div class="k" style="font:600 10.5px IBM Plex Sans;color:var(--dim);text-transform:uppercase;letter-spacing:.5px">' + F.esc(lt.nm || S.sym) + ' under this shock</div><div class="big ' + F.tone(d) + '">' + F.pct(d, 1) + '</div><div style="font-size:12px;color:var(--dim);margin:4px 0 10px">≈ ' + F.inr(px * (1 + d / 100)) + ' from ' + F.inr(px) + (parts.length ? ' · ' + parts.sort(function (a, b) { return Math.abs(b[1]) - Math.abs(a[1]); }).slice(0, 3).map(function (p) { return E.FACTOR_SHORT[p[0]] + ' ' + F.pct(p[1], 1); }).join(', ') : ' · move a slider or pick a shock') + '</div>' +
        '<div class="r"><span>the Nifty</span><b class="' + F.tone(x.nifty) + '">' + F.pct(x.nifty, 1) + '</b></div>' + (ds != null ? '<div class="r"><span>the sector · ' + F.esc(lt.sector) + '</span><b class="' + F.tone(ds) + '">' + F.pct(ds, 1) + '</b></div>' : '') + '<div class="r"><span>this share vs the index</span><b class="' + F.tone(d - x.nifty) + '">' + F.pct(d - x.nifty, 1) + '</b></div>' +
        (S.qty ? '<div class="r"><span>your ' + F.n(S.qty, 0) + ' shares (' + F.big(val) + ')</span><b class="' + F.tone(dv) + '">' + (dv >= 0 ? '+' : '−') + F.big(Math.abs(dv)) + '</b></div>' + (S.cost ? '<div class="r"><span>P&L from your cost ' + F.inr(S.cost) + ' after the shock</span><b class="' + F.tone(S.qty * (px * (1 + d / 100) - S.cost)) + '">' + F.big(S.qty * (px * (1 + d / 100) - S.cost)) + '</b></div>' : '') : '<div class="r"><span>enter a holding to see it in rupees</span><b></b></div>') +
        '<div style="font-size:10.5px;color:var(--mut);margin-top:8px">Δ ≈ Σ β × Δfactor · betas from ' + ((r.dna || {}).n || '—') + ' weeks · R² ' + F.n((r.dna || {}).r2, 2) + ' — a first-order estimate, not a forecast</div>';
    } catch (e) { console.warn('sim', e && e.message); }
  };
  S.derivs = function (r) {
    const f = r.fut || {}, o = r.opt || {};
    const kv = [];
    if (r.fut) { const tag = (f.d > 0 && f.doi_pct > 0) ? 'long build-up' : (f.d > 0 && f.doi_pct < 0) ? 'short covering' : (f.d < 0 && f.doi_pct > 0) ? 'short build-up' : 'long unwinding'; kv.push(['Future', F.inr(f.c), 'expiry ' + F.esc(f.xp || '')], ['Basis', F.n(f.b, 1), 'future − spot'], ['OI', F.n(f.oi, 0), F.pct(f.doi_pct, 1) + ' on the day · ' + tag]); }
    if (r.opt) kv.push(['ATM IV', F.n(o.atm_iv, 1) + '%', 'expiry ' + F.esc(o.expiry || '') + ' · ' + (o.dte || '—') + ' days'], ['Implied move', '±' + F.n(o.implied_move_pct, 1) + '%', '±' + F.n(o.implied_1d_pct, 2) + '% a day'], ['PCR (OI)', F.n(o.pcr_oi, 2), o.pcr_oi > 1.2 ? 'puts heavy — a floor' : o.pcr_oi < 0.6 ? 'calls heavy — a lid' : 'balanced'], ['Max pain', F.inr(o.max_pain), ''], ['The walls', F.inr(o.put_wall) + ' / ' + F.inr(o.call_wall), 'put wall / call wall'], ['Skew (25Δ)', F.n(o.skew_25d, 1), o.skew_25d > 1.5 ? 'puts bid — hedged' : 'flat']);
    return '<div class="cd"><div class="e-kv">' + kv.map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div>' + (x[2] ? '<div class="s">' + x[2] + '</div>' : '') + '</div>'; }).join('') + '</div>' + (r.v && r.v.fno && r.v.fno.opt_trade ? '<div style="margin-top:10px">' + E.optLine(r.v.fno.opt_trade, r.v.fno.side) + '</div>' : '') + '</div>';
  };
  S.contenders = function (r) {
    const c = r.cont; const px = L.px(S.sym) || 0;
    let h = '<div class="cd"><div class="e-kv">' + [['Odds of a move', Math.round(100 * (c.p_move || 0)) + '%', '≥ 1.5σ in five sessions'], ['p(up)', Math.round(100 * (c.p_up || 0.5)) + '%', 'the side'], ['5-session median', F.pct(c.q50, 1), 'Monte Carlo · ' + F.pct(c.q10, 1) + ' to ' + F.pct(c.q90, 1)], ['Target before stop', c.tgt_before_stop != null ? Math.round(100 * c.tgt_before_stop) + '%' : '—', 'within 20 sessions']].map(function (x) { return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + x[1] + '</div><div class="s">' + x[2] + '</div></div>'; }).join('') + '</div>';
    if (c.q10 != null && c.q90 != null && px) { h += '<div class="e-chart" style="margin-top:10px"><canvas id="e-sh-cone" style="height:180px"></canvas><div class="lg"><span><i style="background:var(--blu)"></i>median path</span><span><i style="background:rgba(78,161,255,.3)"></i>10th–90th percentile</span></div></div>'; setTimeout(function () { try { const cv = document.getElementById('e-sh-cone'); if (!cv) return; const n = 6; const med = [], lo = [], hi = []; for (let i = 0; i < n; i++) { const f = i / (n - 1); med.push(px * (1 + c.q50 / 100 * f)); lo.push(px * (1 + c.q10 / 100 * Math.sqrt(f))); hi.push(px * (1 + c.q90 / 100 * Math.sqrt(f))); } E.chart.line(cv, [{ v: med, color: '#4ea1ff', w: 2 }, { v: hi, color: 'rgba(78,161,255,.5)', dash: [3, 3] }, { v: lo, color: 'rgba(78,161,255,.5)', dash: [3, 3] }], { xl: ['now', '+1', '+2', '+3', '+4', '+5'] }); } catch (e) { } }, 50); }
    h += '</div>'; return h;
  };
  S.peers = function (sym, lt) {
    const N = E.lite.names; const mem = (E.full && E.full.sectors_members && E.full.sectors_members[lt.sector]) || Object.keys(N).filter(function (s) { return N[s].sector === lt.sector && !N[s].x; });
    const rows = mem.filter(function (s) { return s !== sym; }).map(function (s) { return Object.assign({ sym: s }, N[s]); }).sort(function (a, b) { return (b.turn || 0) - (a.turn || 0); }).slice(0, 8);
    if (!rows.length) return '<div class="e-empty">no peers mapped</div>';
    return '<div class="e-list e-peers">' + rows.map(function (p) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(p.sym) + '\')"><div class="n">' + F.esc(p.nm) + '<small>' + F.esc(p.sym) + ' · ' + F.cr(p.turn) + '</small></div><div>' + F.word(p.ss) + '</div><div>' + F.word(p.ls) + '</div><div class="px"><span data-live-px="' + F.esc(p.sym) + '">' + F.inr(L.px(p.sym)) + '</span><small class="' + F.tone(L.d1(p.sym)) + '" data-live-d="' + F.esc(p.sym) + '">' + F.pct(L.d1(p.sym), 2) + '</small></div></div>'; }).join('') + '</div>';
  };
  S.wire = function (sym, lt) {
    try { const items = ((window.NEWS_LIVE || {}).items) || []; const nm = String(lt.nm || '').toLowerCase().split(/\s+/)[0]; const hits = items.filter(function (it) { const t = String(it.t || '').toLowerCase(); return t.indexOf(String(sym).toLowerCase()) >= 0 || (nm && nm.length >= 4 && t.indexOf(nm) >= 0); }).slice(0, 6); if (!hits.length) return '<div class="e-empty">no headline on the wire names it in the last pass</div>'; return '<div class="e-list">' + hits.map(function (it) { return '<a class="e-li" style="text-decoration:none" target="_blank" rel="noopener" href="' + F.esc(it.link) + '"><div class="n">' + F.esc(it.t) + '<small>' + F.esc(it.src || '') + ' · ' + (it.age_h != null ? (it.age_h < 1 ? Math.round(it.age_h * 60) + ' min ago' : Math.round(it.age_h) + ' h ago') : '') + '</small></div><div></div><div></div></a>'; }).join('') + '</div>'; } catch (e) { return ''; }
  };
  S.changes = function (r, lt) {
    const v = r.v || {}, vs = v.short || {}, vl = v.long || {}, t = r.tape || {}; const out = [];
    if (vs.side === 'BUY') out.push('<b>Short term:</b> a close below the stop ' + F.inr(vs.stop) + ' ends the trade; the target ' + F.inr(vs.target) + ' books it; after ' + vs.h + ' sessions it is closed whatever happens.');
    else if (vs.side === 'SELL') out.push('<b>Short term:</b> a close above the stop ' + F.inr(vs.stop) + ' ends the short; the target ' + F.inr(vs.target) + ' books it; ' + vs.h + ' sessions at most.');
    else out.push('<b>Short term:</b> the score is ' + (vs.score != null ? Math.round(vs.score) : '—') + '/100 — it becomes a buy above 80 (momentum, the macro wind, the futures flow turning up together) or a sell below 10.');
    if (vl.side === 'ACCUMULATE') out.push('<b>Long term:</b> a close below ' + F.inr(vl.stop) + ' (' + (vl.stop_note || 'the 200-day') + ') ends the accumulate; the sector turning to AVOID or the regime changing lowers it.');
    else if (vl.side === 'AVOID') out.push('<b>Long term:</b> a close back above the 200-day (' + F.inr(t.m200) + ') with the sector turning starts the case; until then nothing to buy for the year.');
    else out.push('<b>Long term:</b> the score is ' + (vl.score != null ? Math.round(vl.score) : '—') + '/100 — above 80 (trend, quality and the sector\'s regime record lining up) it becomes an accumulate.');
    out.push('<b>The macro:</b> the regime is ' + F.esc((E.lite.market || {}).regime || '') + '; the next CPI and IIP prints can move it, and this name\'s record differs by regime (see its DNA).');
    return out.join('<br>');
  };
  S.plain = function (sym, r, lt) {
    const v = r.v || {}, vs = v.short || {}, vl = v.long || {}, vi = v.intra || {}; const px = L.px(sym);
    const lines = [(lt.nm || sym) + ' (' + sym + ') — MacroIntel, ' + F.ist() + ' IST', 'Price ₹' + F.n(px, 2) + ' (' + F.pct(L.d1(sym), 2) + ')', ''];
    lines.push('TODAY: ' + (vi.side ? (vi.side + ' · entry ' + F.inr(vi.entry && vi.entry[0]) + '–' + F.inr(vi.entry && vi.entry[1]) + ' · stop ' + F.inr(vi.stop) + ' · target ' + F.inr(vi.target) + ' · flat by 15:20') : 'no trade — expected range ' + (vi.range ? F.inr(vi.range[0]) + '–' + F.inr(vi.range[1]) : '—')));
    lines.push('SHORT TERM (5–60 sessions): ' + (vs.side ? (vs.side + ' ' + Math.round(vs.score) + '/100 · stop ' + F.inr(vs.stop) + ' · target ' + F.inr(vs.target) + ' · ' + vs.h + ' sessions · size ' + vs.size_pct + '%') : 'no trade (' + (vs.score != null ? Math.round(vs.score) : '—') + '/100)'));
    if (vs.why) lines.push('  because: ' + vs.why.join('; '));
    lines.push('LONG TERM (12 months): ' + (vl.side ? (vl.side + ' ' + Math.round(vl.score) + '/100 · target ' + F.inr(vl.target) + ' (' + F.pct(vl.exp_pct, 0) + ') · exit below ' + F.inr(vl.stop)) : 'no view (' + (vl.score != null ? Math.round(vl.score) : '—') + '/100)'));
    if (vl.why) lines.push('  because: ' + vl.why.join('; '));
    if (v.fno) lines.push('F&O: ' + v.fno.side + ' ' + v.fno.lots + ' lot(s) ' + v.fno.contract + ' · risk/lot ' + F.big(v.fno.risk_lot) + ' · potential/lot ' + F.big(v.fno.pot_lot));
    lines.push('', E.note(v.note), 'Regime ' + ((E.lite.market || {}).regime || '') + ' · educational, not advice · macrointel');
    return lines.join('\n');
  };
  /* ── the chart ── */
  S.setRange = function (r) { S.range = r; S._fell = (r !== '1d'); S._fellNote = ''; document.querySelectorAll('#e-sh-body .subtabs .subtab').forEach(function (b) { b.classList.toggle('a', b.getAttribute('onclick').indexOf("'" + r + "'") >= 0); }); S.drawChart(); };
  S.drawChart = async function () {
    const sym = S.sym; const cv = document.getElementById('e-sh-cv'); const lg = document.getElementById('e-sh-lg'); if (!cv || !sym) return;
    const r = S.row || {}; const t = r.tape || {}; const v = r.v || {}; const vs = v.short || {}, vl = v.long || {};
    const range = S.range; const ser = await E.series.get(sym, range);
    if (S.sym !== sym || S.range !== range) return;
    if (!ser) {
      if (range === '1d' && !S._fell) { S._fell = true; S.range = '1y'; document.querySelectorAll('#e-sh-body .subtabs .subtab').forEach(function (b) { b.classList.toggle('a', b.getAttribute('onclick').indexOf("'1y'") >= 0); }); S._fellNote = L.inHours() ? 'today\'s bars need a live door (⚙ in More → paste your worker URL) — showing one year' : 'the market is closed — today\'s bars draw in the session when a door is open; showing one year'; return S.drawChart(); }
      cv.style.display = 'none'; lg.innerHTML = '<div class="empty">' + (range === '1d' ? 'no bars for today reach this browser' : 'no series for this range — a live door (Yahoo through the worker) draws it') + '</div>'; return;
    }
    cv.style.display = 'block';
    const vals = ser.pairs.map(function (p) { return p[1]; }); const xl = E.series.xl(ser.pairs, range === '1d');
    const series = [{ v: vals, color: (vals[vals.length - 1] >= vals[0]) ? '#2fd27d' : '#ff5c5c', w: 1.8, fill: (vals[vals.length - 1] >= vals[0]) ? 'rgba(47,210,125,.08)' : 'rgba(255,92,92,.08)' }]; const levels = []; let legend = '<span><i style="background:' + series[0].color + '"></i>' + F.esc(ser.src) + '</span>';
    if (range === '1d') { if (ser.prev) levels.push({ y: ser.prev, label: 'prev close ' + F.inr(ser.prev), color: '#8d99aa' }); const vi = v.intra || {}; if (vi.side) { levels.push({ y: vi.stop, label: 'stop', color: '#ff5c5c' }, { y: vi.target, label: 'target', color: '#2fd27d' }); } else if (vi.range) { levels.push({ y: vi.range[0], label: 'expected floor', color: '#5d6878' }, { y: vi.range[1], label: 'expected ceiling', color: '#5d6878' }); } }
    else if (range === '1y') { const w = ser.weekly; series.push({ v: E.series.sma(vals, w ? 10 : 50), color: '#f5b81a', w: 1 }, { v: E.series.sma(vals, w ? 40 : 200), color: '#9b8cff', w: 1 }); legend += '<span><i style="background:#f5b81a"></i>50-day</span><span><i style="background:#9b8cff"></i>200-day</span>'; if (vs.side) { levels.push({ y: vs.stop, label: 'stop ' + F.inr(vs.stop), color: '#ff5c5c' }, { y: vs.target, label: 'target ' + F.inr(vs.target), color: '#2fd27d' }); legend += '<span><i style="background:#ff5c5c"></i>stop</span><span><i style="background:#2fd27d"></i>target</span>'; } if (vl.side === 'ACCUMULATE' && vl.target) { levels.push({ y: vl.target, label: '12-m target ' + F.inr(vl.target), color: '#4ea1ff' }); } }
    else { series.push({ v: E.series.sma(vals, 40), color: '#9b8cff', w: 1 }); legend += '<span><i style="background:#9b8cff"></i>40-week (≈200-day)</span>'; if (vl.side === 'ACCUMULATE' && vl.target) levels.push({ y: vl.target, label: '12-m target ' + F.inr(vl.target), color: '#4ea1ff' }); if (vl.stop) levels.push({ y: vl.stop, label: 'exit ' + F.inr(vl.stop), color: '#ff8a4c' }); }
    E.chart.line(cv, series, { levels: levels, xl: xl });
    lg.innerHTML = legend + (S._fellNote ? '<span style="color:var(--amb)">' + F.esc(S._fellNote) + '</span>' : '') + (range !== '1d' && t.hi52 ? '<span style="margin-left:auto">52w ' + F.inr(t.lo52) + ' – ' + F.inr(t.hi52) + '</span>' : ''); S._fellNote = '';
  };
})(window.E);
