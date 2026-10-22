/* ═══ v144 · HOME · MARKETS · RESEARCH (the lists) ═══ */
(function (E) {
  const F = E.f, L = E.live;

  /* ── shared pieces ── */
  E.pickCard = function (p, kind, i) {
    const n = E.lt(p.sym) || {}; const side = p.side || (kind === 'long' ? n.ls : n.ss) || null; const cls = F.cls(side);
    let plan = '';
    if (kind === 'intraday') plan = '<div class="plan"><div><div class="k">Entry zone</div><div class="v">' + F.inr(p.entry && p.entry[0]) + '–' + F.inr(p.entry && p.entry[1]) + '</div></div><div><div class="k">Stop</div><div class="v">' + F.inr(p.stop) + '</div></div><div><div class="k">Target</div><div class="v">' + F.inr(p.target) + '</div></div></div>';
    else if (kind === 'fno') plan = '<div class="plan"><div><div class="k">' + (side === 'BUY' ? 'Buy' : 'Sell') + '</div><div class="v">' + p.lots + ' lot' + (p.lots > 1 ? 's' : '') + '</div><div style="font-size:10.5px;color:var(--dim)">lot of ' + p.lot + '</div></div><div><div class="k">Risk / lot</div><div class="v">' + F.big(p.risk_lot) + '</div><div style="font-size:10.5px;color:var(--dim)">' + (p.risk_pct_book != null ? p.risk_pct_book + '% of ₹10 L' : '') + '</div></div><div><div class="k">Potential / lot</div><div class="v e-up">' + F.big(p.pot_lot) + '</div><div style="font-size:10.5px;color:var(--dim)">stop ' + F.inr(p.stop) + '</div></div></div>' + (function () { try { return E.optLine(p.opt_trade, side); } catch (e) { return ''; } })();
    else if (kind === 'short') plan = '<div class="plan"><div><div class="k">Stop</div><div class="v">' + F.inr(p.stop) + '</div></div><div><div class="k">Target</div><div class="v">' + F.inr(p.target) + '</div></div><div><div class="k">Horizon</div><div class="v">' + (p.h || '—') + ' sessions</div></div></div>' + (p.size_pct != null ? '<div class="foot"><span>size ' + p.size_pct + '% of capital</span><span>reward : risk 2 : 1</span></div>' : '');
    else if (kind === 'long') plan = '<div class="plan"><div><div class="k">12-m target</div><div class="v">' + F.inr(p.target) + '</div></div><div><div class="k">Expected</div><div class="v ' + F.tone(p.exp_pct) + '">' + F.pct(p.exp_pct, 0) + '</div></div><div><div class="k">Exit below</div><div class="v">' + F.inr(p.stop) + '</div></div></div>';
    const why = (p.why && p.why.length) ? '<div class="why">' + F.esc(p.why.slice(0, 2).join(' · ')) + '</div>' : '';
    return '<div class="e-pick ' + cls + '" onclick="E.openShare(\'' + F.esc(p.sym) + '\')">' +
      '<div class="top"><div>' + (i != null ? '<span class="e-rank">' + (i + 1) + '</span>' : '') + '<span class="nm">' + F.esc(p.nm || n.nm || p.sym) + '</span><div class="sy">' + F.esc(p.sym) + ' · ' + F.esc(p.sector || n.sector || '') + (p.contract ? ' · ' + F.esc(p.contract) : '') + '</div></div>' +
      '<div><div class="px" data-live-px="' + F.esc(p.sym) + '">' + F.inr(L.px(p.sym)) + '</div><div class="d ' + F.tone(L.d1(p.sym)) + '" data-live-d="' + F.esc(p.sym) + '">' + F.pct(L.d1(p.sym), 2) + '</div></div></div>' +
      '<div class="e-row" style="margin-top:8px">' + F.word(side) + (kind === 'intraday' ? '<span class="e-score" style="color:var(--dim);font-size:12px">lean ' + F.sgn(p.lean, 2) + ' · σ ' + (p.sig1d != null ? p.sig1d + '%' : '—') + '</span>' : '<span class="e-score" style="color:var(--dim);font-size:12px">' + (p.score != null ? Math.round(p.score) + '/100' : '') + '</span>') + (p.conv ? '<span class="e-tag">' + p.conv + '</span>' : '') + (p.held_from && kind !== 'intraday' && kind !== 'fno' ? '<span class="e-tag" title="on the list since">since ' + p.held_from.slice(5) + '</span>' : '') + '</div>' +
      plan + why + '</div>';
  };
  E.sectionHead = function (t, s, act) { return '<div class="e-sec"><div><div class="t">' + t + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>' + (act || '') + '</div>'; };
  E.notReady = function (what) { return '<div class="e-empty">' + (what || 'The engine') + ' arrives with the first pipeline pass after this upload — engine.json is not on the site yet. Everything else on the page works now.</div>'; };
  E.todayBuys = function (n) {
    const P = (E.lite && E.lite.picks) || {}; const L0 = (P.today_buys || []).slice(0, n || 8);
    let h = E.sectionHead('The model\'s buys today · ' + F.esc((E.lite && E.lite.asof) || ''), 'the engine\'s strongest BUYs right now, ranked — refreshed every pass, NEW = not on yesterday\'s list · entry, stop, target, horizon', '<span class="act" onclick="E.go(\'micro\',\'short\')">every buy →</span>');
    if (!L0.length) return h + '<div class="e-empty">no name clears the bar today</div>';
    h += '<div class="e-grid e-auto">' + L0.map(function (p, i) { const card = E.pickCard(p, 'short', i); return p.new ? card.replace('<span class="nm">', '<span class="e-tag" style="background:rgba(47,210,125,.15);color:var(--grn);margin-right:6px">NEW</span><span class="nm">') : card; }).join('') + '</div>';
    return h;
  };
  E.recordStrip = function () {
    const R = (E.lite && E.lite.record) || {}; const lab = { calls_short: 'The short call · 20 sessions', calls_long: 'The long call · 60 sessions', today_buys: 'Today\'s buys · 10 sessions', movers: 'Likely movers · next session', intraday: 'Intraday · next session', fno: 'F&O · 10 sessions', pairs: 'Pairs · 10 sessions', short_buy: 'Short-term buys · 20 sessions', short_sell: 'Short-term sells · 20 sessions', long: 'Long-term · 60 sessions', macro: 'The macro call · 5 sessions' };
    return '<div class="e-record">' + Object.keys(lab).map(function (k) { const r = R[k] || {}; if (k === 'movers') return '<div class="e-stat"><div class="k">' + lab[k] + '</div><div class="v">' + (r.n ? (r.hit + '%') : '—') + '</div><div class="s">' + (r.n ? ('moved ≥ 1.5σ on ' + r.n + ' scored (base rate ~16%) · avg |move| ' + F.pct(r.avg, 1) + (r.dir_hit != null ? ' · lean right ' + r.dir_hit + '% of ' + r.n_dir : '')) : 'scored the session after each list') + '</div></div>'; return '<div class="e-stat"><div class="k">' + lab[k] + '</div><div class="v">' + (r.n ? (r.hit + '%') : '—') + '</div><div class="s">' + (r.n ? ('hit rate on ' + r.n + ' scored · avg ' + F.pct(r.avg, 2) + (r.avg_excess != null ? ' · vs Nifty ' + F.pct(r.avg_excess, 2) : '')) : 'no pick has reached its horizon yet — scoring starts automatically') + '</div></div>'; }).join('') + '</div>';
  };

  /* ═══ HOME ═══ */
  E.home = {};
  E.home.render = function () {
    const el = document.getElementById('e-home'); if (!el) return;
    const M = (E.lite && E.lite.market) || {}; const P = (E.lite && E.lite.picks) || {};
    let h = '<div class="e-hero"><div class="e-h1">What is the macro about to do to your stocks?</div>' +
      '<div class="e-sub">Every listed share, scored on one engine — the regime, the sector, the tape, the fundamentals — with a verdict for today, the next 5–60 sessions and the year. Every call frozen and scored in public.</div>' +
      E.searchBox('e-home-search', 'any share, sector or question — Radico, Cupid, HDFC Bank, Pharma…', true) +
      '<div class="hint">press <span class="e-kbd">/</span> to search from anywhere · ask it anything you hold: "I have 50 shares of Cupid, do I sell?"</div>' +
      '<div class="e-session">' + (M.nifty != null ? '<span>Nifty <b data-live-px="NIFTY">' + F.n(L.px('NIFTY'), 0) + '</b> <span class="' + F.tone(L.d1('NIFTY')) + ' e-mono" data-live-d="NIFTY">' + F.pct(L.d1('NIFTY'), 2) + '</span></span>' : '') +
      (M.regime ? '<span>Regime <b>' + F.esc(M.regime) + '</b></span>' : '') + (M.call ? '<span>The session <b>' + F.esc(M.call) + '</b></span>' : '') + L.chip() + (function () { try { return E.pipe.chip(); } catch (e) { return ''; } })() + '</div></div>';
    if (!E.lite) { h += E.notReady('The engine'); }
    else {
      try { h += E.calls.section(false); } catch (e) { }
      h += E.todayBuys(8);
      try { h += E.movers.section(false); } catch (e) { }
      try { h += E.attr.section(false); } catch (e) { }
      try { h += E.movers.changes(false); } catch (e) { }
      try { h += E.pf.strip(); } catch (e) { }
      try { h += E.alloc.card(); } catch (e) { }
      h += '<div id="e-funds-strip">' + (function () { try { return E.funds.strip(); } catch (e) { return ''; } })() + '</div>';
      try { h += E.nowcast.card(true).replace('margin-bottom:12px', 'margin-top:14px'); } catch (e) { }
      try { h += E.street.section(false); } catch (e) { }
      h += E.sectionHead('Top picks today', 'from one engine, one score — ' + (E.lite.generated || '') + ' · the short and long lists stay until the score says otherwise', '<span class="act" onclick="E.go(\'research\',\'picks\')">all the lists →</span>');
      h += '<div class="e-grid e-g4">';
      h += '<div><div class="lbl">⚡ Intraday · today</div><div class="e-list">' + ((P.intraday || []).map(function (p, i) { return E.miniRow(p, i, 'intraday'); }).join('') || '<div class="e-empty">nothing in play with a clear lean</div>') + '</div></div>';
      h += '<div><div class="lbl">📈 F&O · lots</div><div class="e-list">' + ((P.fno || []).map(function (p, i) { return E.miniRow(p, i, 'fno'); }).join('') || '<div class="e-empty">no futures idea today</div>') + '</div></div>';
      h += '<div><div class="lbl">📅 Short term · 5–60 sessions</div><div class="e-list">' + ((P.short_buy || []).map(function (p, i) { return E.miniRow(p, i, 'short'); }).join('') || '<div class="e-empty">no buy clears the bar today</div>') + '</div></div>';
      h += '<div><div class="lbl">🌱 Long term · 12 months</div><div class="e-list">' + ((P.long || []).map(function (p, i) { return E.miniRow(p, i, 'long'); }).join('') || '<div class="e-empty">no accumulate clears the bar today</div>') + '</div></div>';
      h += '</div>';
      h += '<div style="margin-top:22px">' + E.ask.box('e-home-ask', null) + '</div>';
      h += E.sectionHead('Our record', 'every pick is frozen the day it prints and scored when its horizon arrives — the page grades itself');
      h += E.recordStrip();
    }
    h += '<div class="e-why-us">' +
      '<div class="c"><div class="t">Macro DNA on every share</div><div class="s">How each name moves with the Nifty, the rupee, crude, rates and VIX — measured, not assumed — and how it did in every regime.</div></div>' +
      '<div class="c"><div class="t">A shock simulator</div><div class="s">Crude to $120, RBI +50bp, rupee to 100, FII selling: what it does to any share, any sector, your holding.</div></div>' +
      '<div class="c"><div class="t">One engine, three horizons</div><div class="s">Today · 5–60 sessions · 12 months. BUY, SELL, ACCUMULATE or AVOID — never "wait". Nothing on the page contradicts anything else.</div></div>' +
      '<div class="c"><div class="t">Scored in public</div><div class="s">A broker sends a target and never grades it. Every call here is frozen before the fact and scored after.</div></div>' +
      '<div class="c"><div class="t">Twelve books trade it live</div><div class="s">₹10 lakh to ₹1 crore, an emotion level each, every fill with its minute and its reason.</div></div>' +
      '<div class="c"><div class="t">Your whole book, X-rayed</div><div class="s">Paste your holdings: the model\'s word on each, the book\'s macro DNA, what every shock costs you in rupees.</div></div>' +
      '<div class="c"><div class="t">Beyond stocks</div><div class="s">The regime → asset map across equity, gold, silver, gilts, cash and the Nasdaq — and market-neutral pairs inside F&O.</div></div>' +
      '</div>';
    h += '<div class="e-foot">MacroIntel · educational information computed from public data (NSE, BSE, RBI, MoSPI, Yahoo Finance) — not investment advice. Prices are live when a door is open, otherwise the last close. ' + (E.lite ? 'Engine ' + F.esc(E.lite.version) + ' · ' + F.esc(E.lite.generated) + ' · ' + F.n(E.lite.universe_n, 0) + ' names.' : '') + '</div>';
    el.innerHTML = h;
    try { E.pf.fillStrip(); } catch (e) { }
    try { E.funds.load().then(function () { const s = document.getElementById('e-funds-strip'); if (s) s.innerHTML = E.funds.strip(); }); } catch (e) { }
  };
  E.miniRow = function (p, i, kind) {
    const side = p.side; const sub = kind === 'fno' ? (p.lots + ' lot' + (p.lots > 1 ? 's' : '') + ' · stop ' + F.inr(p.stop) + ' · target ' + F.inr(p.target)) : kind === 'intraday' ? ('stop ' + F.inr(p.stop) + ' · target ' + F.inr(p.target)) : kind === 'short' ? ('stop ' + F.inr(p.stop) + ' · target ' + F.inr(p.target) + ' · ' + (p.h || '—') + ' sessions') : ('12-m target ' + F.inr(p.target) + (p.exp_pct != null ? ' (' + F.pct(p.exp_pct, 0) + ')' : '') + ' · exit ' + F.inr(p.stop));
    return '<div class="e-li" onclick="E.openShare(\'' + F.esc(p.sym) + '\')"><div class="n"><span class="e-rank">' + (i + 1) + '</span>' + F.esc(p.nm || p.sym) + '<small>' + F.esc(p.sym) + '</small><div style="font-size:11px;color:var(--dim);font-weight:400;margin-top:1px">' + sub + '</div></div><div>' + F.word(side) + '</div><div class="px"><span data-live-px="' + F.esc(p.sym) + '">' + F.inr(L.px(p.sym)) + '</span><small class="' + F.tone(L.d1(p.sym)) + '" data-live-d="' + F.esc(p.sym) + '">' + F.pct(L.d1(p.sym), 2) + '</small></div></div>';
  };

  /* ═══ MARKETS ═══ */
  E.markets = { sub: 'today', sector: '', side: 'BUY' };
  E.markets.show = function (s) { E.markets.sub = s; E.markets.render(); };
  E.markets.render = function () {
    const el = document.getElementById('e-markets'); if (!el) return;
    const sub = E.markets.sub;
    let h = E.searchBox('e-mk-search', 'any of ' + F.n((E.lite && E.lite.universe_n) || 4600, 0) + ' listed shares — the verdict comes first');
    h += '<div class="subtabs" style="margin-top:12px">' + [['today', '⚡ Intraday · today'], ['short', '📅 Short term · 5–60 sessions'], ['long', '🌱 Long term · 12 months'], ['fno', '📈 F&O & pairs'], ['where', '🧭 Where to be'], ['street', '🏛 The Street'], ['records', '🧾 Records & the desk']].map(function (t) { return '<button class="subtab' + (sub === t[0] ? ' a' : '') + '" onclick="E.markets.show(\'' + t[0] + '\')">' + t[1] + '</button>'; }).join('') + '<span style="flex:1"></span>' + L.chip() + '</div>';
    if (!E.lite && sub !== 'records') h += E.notReady('The engine');
    else if (sub === 'street') { h += '<div class="mi-defn"><b>The Street against the engine.</b> Yahoo carries the analysts\' mean target and the consensus word for every covered name. Here it meets the engine\'s twelve-month expectation, name by name — where the two disagree most, and a record of who turned out closer sixty sessions on. A broker never grades his target; this board grades both.</div>'; h += E.street.section(true); try { h += E.calls.section(true); } catch (e) { } }
    else if (sub === 'today') h += E.markets.today();
    else if (sub === 'short') h += E.markets.short();
    else if (sub === 'long') h += E.markets.long();
    else if (sub === 'fno') h += E.markets.fno();
    else if (sub === 'where') h += E.alloc.render();
    else if (sub === 'records') h += E.markets.records();
    /* the legacy F&O desk (index cards, the option chain) and BUILD & SIZE stay reachable under their tabs */
    const legF = document.getElementById('e-legacy-fno'), legD = document.getElementById('e-legacy-desk');
    if (legF) legF.classList.toggle('show', sub === 'fno');
    if (legD) legD.classList.toggle('show', sub === 'records');
    if (sub === 'fno') { try { if (typeof msw === 'function') msw(null, 'fno'); } catch (e) { } }
    if (sub === 'records') { try { if (typeof msw === 'function') msw(null, 'build'); } catch (e) { } }
    el.innerHTML = h;
    /* ask the live loop for every name on this screen */
    /* every liquid name (≥ ₹5 cr a day, ≈1,200) plus every F&O name rides the live loop while Markets is open — 15 batched calls a minute through the worker, cached at the edge */
    try { const N = E.lite.names; const want = Object.keys(N).filter(function (s) { return !N[s].x && ((N[s].turn || 0) >= 5 || N[s].fno); }).sort(function (a, b) { return (N[b].turn || 0) - (N[a].turn || 0); }).slice(0, 1400); L.want(want.concat(['NIFTY', 'BANKNIFTY', 'VIX'])); } catch (e) { }
  };
  E.markets.sessionCard = function () {
    const M = E.lite.market || {}; const B = M.breadth || {};
    const live = E.markets.liveBreadth();
    const idx = [['NIFTY', 'Nifty 50'], ['BANKNIFTY', 'Bank Nifty'], ['VIX', 'India VIX']].map(function (x) { return '<div><div class="k">' + x[1] + '</div><div class="v" data-live-px="' + x[0] + '">' + F.n(L.px(x[0]) || (x[0] === 'VIX' ? M.vix : null), x[0] === 'VIX' ? 2 : 0) + '</div><div class="d ' + F.tone(L.d1(x[0])) + '" data-live-d="' + x[0] + '">' + F.pct(L.d1(x[0]), 2) + '</div></div>'; }).join('');
    return '<div class="e-sess"><div class="idx">' + idx + '</div><div class="call"><div class="lbl">The session\'s call</div><div class="w">' + F.esc(M.call || '—') + '</div><div class="s">' + F.esc(M.call_how || '') + ' · regime <b>' + F.esc(M.regime || '') + '</b>' + (M.state ? ' · market state ' + F.esc(M.state) : '') + (M.stress != null ? ' · stress ' + M.stress + '/100' : '') + '</div>' +
      '<div class="s" style="margin-top:6px">' + (live ? ('breadth now: <b class="e-up">' + live.up + '</b> up · <b class="e-dn">' + live.dn + '</b> down of ' + live.n + ' liquid names (live)') : ('last session\'s breadth: <b class="e-up">' + (B.up || 0) + '</b> up · <b class="e-dn">' + (B.down || 0) + '</b> down · ' + F.esc(E.lite.bhav_date || ''))) + ' · the engine prints <b>' + (M.n_buy || 0)+ '</b> buys, <b>' + (M.n_sell || 0) + '</b> sells, <b>' + (M.n_accumulate || 0) + '</b> accumulates today' + (M.gate ? ' · <span style="color:var(--amb)">the gate is on — sizes halved</span>' : '') + '</div></div></div>';
  };
  E.markets.liveBreadth = function () { try { const N = E.lite.names; let up = 0, dn = 0, n = 0; for (const s in N) { if (N[s].x || (N[s].turn || 0) < 5) continue; const q = L.q(s); if (!q || q.d == null) continue; n++; if (q.d > 0) up++; else if (q.d < 0) dn++; } return n >= 50 ? { up: up, dn: dn, n: n } : null; } catch (e) { return null; } };
  E.markets.liveMovers = function () {
    const N = E.lite.names; const rows = [];
    for (const s in N) { if (N[s].x || (N[s].turn || 0) < 5) continue; const q = L.q(s); if (!q || q.d == null) continue; rows.push({ sym: s, nm: N[s].nm, d: q.d, p: q.p, turn: N[s].turn }); }
    if (rows.length < 30) return null;
    rows.sort(function (a, b) { return b.d - a.d; });
    return { up: rows.slice(0, 8), dn: rows.slice(-8).reverse(), n: rows.length };
  };
  E.markets.moverTile = function (m) { return '<div class="m" onclick="E.openShare(\'' + F.esc(m.sym) + '\')"><div class="n">' + F.esc(m.nm || m.sym) + '<small>' + F.esc(m.sym) + (m.turn ? ' · ' + F.cr(m.turn) : '') + '</small></div><div class="d ' + F.tone(m.d) + '">' + F.pct(m.d, 2) + '<small>' + F.inr(m.p) + '</small></div></div>'; };
  E.markets.today = function () {
    const P = E.lite.picks || {}; const MV = (typeof MOVERS_LIVE !== 'undefined' && MOVERS_LIVE) || {};
    let h = E.markets.sessionCard();
    h += E.sectionHead('In play today', 'the names the engine expects to move, with a side — entry zone, stop, target, flat by 15:20 · ' + ((E.lite.counts || {}).intraday || 0) + ' names have a lean today');
    h += '<div class="e-grid e-auto">' + ((P.intraday || []).map(function (p, i) { return E.pickCard(p, 'intraday', i); }).join('') || '<div class="e-empty">no name shows a clear lean for today</div>') + '</div>';
    try { h += E.movers.section(true); } catch (e) { }
    try { h += E.attr.section(true); } catch (e) { }
    try { h += E.movers.events(24); } catch (e) { }
    try { h += E.movers.changes(true); } catch (e) { }
    const lm = E.markets.liveMovers();
    h += E.sectionHead('Big movers · this session', lm ? ('live across ' + lm.n + ' liquid names · ' + L.state().label) : (L.inHours() ? 'waiting for the live door — the last session\'s movers are below' : 'the market is closed — the last session\'s movers are below'));
    if (lm) h += '<div class="e-mv">' + lm.up.map(E.markets.moverTile).join('') + '</div><div class="e-mv" style="margin-top:6px">' + lm.dn.map(E.markets.moverTile).join('') + '</div>';
    h += E.sectionHead('Big movers · the last session', 'the whole market on ₹5 cr+ turnover · bhavcopy ' + F.esc(MV.date || ''));
    const tl = function (r) { return E.markets.moverTile({ sym: r.s, nm: (E.lt(r.s) || {}).nm, d: r.d, p: r.c, turn: r.t }); };
    h += '<div class="e-mv">' + (MV.top_day || []).map(tl).join('') + '</div><div class="e-mv" style="margin-top:6px">' + (MV.bot_day || []).map(tl).join('') + '</div>';
    h += E.sectionHead('The week', 'biggest moves over five sessions');
    h += '<div class="e-mv">' + (MV.top_wk || []).slice(0, 8).map(function (r) { return E.markets.moverTile({ sym: r.s, nm: (E.lt(r.s) || {}).nm, d: r.w, p: r.c, turn: r.t }); }).join('') + '</div>';
    h += '<div class="note" style="margin-top:14px">Intraday is where the models have the least edge and say so: the engine\'s record for next-session calls is on the Research tab. Use the levels, respect the stop, be flat by 15:20.</div>';
    return h;
  };
  E.markets.filterBar = function (kind) {
    const N = E.lite.names; const secs = {}; for (const s in N) { if (N[s].sector) secs[N[s].sector] = (secs[N[s].sector] || 0) + 1; }
    const opts = Object.keys(secs).sort().map(function (s) { return '<option value="' + F.esc(s) + '"' + (E.markets.sector === s ? ' selected' : '') + '>' + F.esc(s) + ' (' + secs[s] + ')</option>'; }).join('');
    return '<div class="e-filter"><select onchange="E.markets.sector=this.value;E.markets.render()"><option value="">every sector</option>' + opts + '</select>' + (kind === 'short' ? '<span class="e-chip' + (E.markets.side === 'BUY' ? ' a' : '') + '" onclick="E.markets.side=\'BUY\';E.markets.render()">BUY</span><span class="e-chip' + (E.markets.side === 'SELL' ? ' a' : '') + '" onclick="E.markets.side=\'SELL\';E.markets.render()">SELL · F&O</span>' : '') + (kind === 'long' ? '<span class="e-chip' + (E.markets.side !== 'AVOID' ? ' a' : '') + '" onclick="E.markets.side=\'BUY\';E.markets.render()">ACCUMULATE</span><span class="e-chip' + (E.markets.side === 'AVOID' ? ' a' : '') + '" onclick="E.markets.side=\'AVOID\';E.markets.render()">AVOID</span>' : '') + '</div>';
  };
  E.markets.listOf = function (sideKey, side, min) {
    const N = E.lite.names; const out = [];
    for (const s in N) { const n = N[s]; if (n[sideKey] !== side) continue; if (E.markets.sector && n.sector !== E.markets.sector) continue; if ((n.turn || 0) < (min || 5)) continue; out.push({ sym: s, nm: n.nm, sector: n.sector, score: sideKey === 'ss' ? n.s : n.l, side: side, lots: n.lots }); }
    out.sort(function (a, b) { return (side === 'SELL' || side === 'AVOID') ? (a.score - b.score) : (b.score - a.score); });
    return out;
  };
  E.markets.short = function () {
    const side = E.markets.side === 'SELL' ? 'SELL' : 'BUY';
    const list = E.markets.listOf('ss', side, 5);
    let h = '<div class="mi-defn"><b>Short term · 5 to 60 sessions.</b> One score for every liquid name: trend (risk-adjusted momentum, the 50-day, the 52-week position), the macro wind and the sector\'s regime edge, the futures flow, the contenders model, quality. <b>BUY</b> is the top 20% of the market, <b>SELL</b> the bottom 10% where a future exists to short. Stop 1.5× the 5-day σ, target 2R, the horizon by volatility. Nothing else is a trade.</div>';
    if (side === 'BUY' && !E.markets.sector) h += E.todayBuys(8);
    h += E.markets.filterBar('short');
    h += E.sectionHead((side === 'BUY' ? 'Buy' : 'Sell') + ' · ' + list.length + ' names', 'ranked by score · click a card for the research page', '<span class="act" onclick="E.markets.renderCards(\'short\',40)">show more</span>');
    h += '<div class="e-grid e-auto" id="e-mk-cards">' + (list.slice(0, 16).map(function (p, i) { return E.cardFromLite(p, 'short', i); }).join('') || '<div class="e-empty">nothing clears the bar in this sector today</div>') + '</div>';
    E.markets._list = list;
    return h;
  };
  E.markets.long = function () {
    const side = E.markets.side === 'AVOID' ? 'AVOID' : 'ACCUMULATE';
    const list = E.markets.listOf('ls', side, 5);
    let h = '<div class="mi-defn"><b>Long term · twelve months.</b> Trend over six and twelve months and the 200-day, the sector\'s record in this regime and the name\'s own, quality (ROE, margins, growth, debt, P/E against the sector, promoter holding), drawdown, liquidity. <b>ACCUMULATE</b> is the top 20%, <b>AVOID</b> the bottom 20%. The exit is the 200-day; the target is a twelve-month expectation with its band, not a promise.</div>';
    h += E.markets.filterBar('long');
    h += E.sectionHead((side === 'ACCUMULATE' ? 'Accumulate' : 'Avoid') + ' · ' + list.length + ' names', 'ranked by score · the list is sticky — a name stays until its score says otherwise', '<span class="act" onclick="E.markets.renderCards(\'long\',40)">show more</span>');
    h += '<div class="e-grid e-auto" id="e-mk-cards">' + (list.slice(0, 16).map(function (p, i) { return E.cardFromLite(p, 'long', i); }).join('') || '<div class="e-empty">nothing clears the bar in this sector today</div>') + '</div>';
    E.markets._list = list;
    return h;
  };
  E.markets.renderCards = function (kind, n) { const el = document.getElementById('e-mk-cards'); if (!el || !E.markets._list) return; el.innerHTML = E.markets._list.slice(0, n).map(function (p, i) { return E.cardFromLite(p, kind, i); }).join(''); E.markets.hydrate(kind); };
  E.cardFromLite = function (p, kind, i) {
    /* a card from the lite row now; the full row (stop, target, why) is filled in when the shard arrives */
    const n = E.lt(p.sym) || {}; const side = p.side; const cls = F.cls(side);
    return '<div class="e-pick ' + cls + '" data-card="' + F.esc(p.sym) + '" data-kind="' + kind + '" onclick="E.openShare(\'' + F.esc(p.sym) + '\')"><div class="top"><div>' + (i != null ? '<span class="e-rank">' + (i + 1) + '</span>' : '') + '<span class="nm">' + F.esc(n.nm || p.sym) + '</span><div class="sy">' + F.esc(p.sym) + ' · ' + F.esc(n.sector || '') + (n.fno ? ' · F&O' : '') + '</div></div><div><div class="px" data-live-px="' + F.esc(p.sym) + '">' + F.inr(L.px(p.sym)) + '</div><div class="d ' + F.tone(L.d1(p.sym)) + '" data-live-d="' + F.esc(p.sym) + '">' + F.pct(L.d1(p.sym), 2) + '</div></div></div>' +
      '<div class="e-row" style="margin-top:8px">' + F.word(side) + '<span class="e-score" style="color:var(--dim);font-size:12px">' + (p.score != null ? Math.round(p.score) + '/100' : '') + '</span></div><div class="e-hyd"><div class="plan"><div><div class="k">…</div><div class="v">&nbsp;</div></div></div></div></div>';
  };
  E.markets.hydrate = async function (kind) {
    const cards = Array.from(document.querySelectorAll('[data-card]')); if (!cards.length) return;
    const syms = cards.map(function (c) { return c.getAttribute('data-card'); });
    await Promise.all(Array.from(new Set(syms.map(E.shardOf))).map(function (k) { return E.loadShard(k); }));
    cards.forEach(function (c) {
      const r = E.rowSync(c.getAttribute('data-card')); const hy = c.querySelector('.e-hyd'); if (!r || !hy) return; const kd = c.getAttribute('data-kind');
      const v = kd === 'long' ? (r.v.long || {}) : (r.v.short || {});
      let plan;
      if (kd === 'long') plan = '<div class="plan"><div><div class="k">12-m target</div><div class="v">' + F.inr(v.target) + '</div></div><div><div class="k">Expected</div><div class="v ' + F.tone(v.exp_pct) + '">' + F.pct(v.exp_pct, 0) + '</div></div><div><div class="k">Exit below</div><div class="v">' + F.inr(v.stop) + '</div></div></div>';
      else plan = '<div class="plan"><div><div class="k">Stop</div><div class="v">' + F.inr(v.stop) + '</div><div style="font-size:10.5px;color:var(--dim)">' + F.pct(-(v.stop_pct || 0) * (v.side === 'SELL' ? -1 : 1), 1) + '</div></div><div><div class="k">Target</div><div class="v">' + F.inr(v.target) + '</div><div style="font-size:10.5px;color:var(--dim)">' + F.pct((v.tgt_pct || 0) * (v.side === 'SELL' ? -1 : 1), 1) + '</div></div><div><div class="k">Horizon</div><div class="v">' + (v.h || '—') + ' sessions</div></div></div>';
      hy.innerHTML = plan + ((v.why && v.why.length) ? '<div class="why">' + F.esc(v.why.slice(0, 2).join(' · ')) + '</div>' : '') + (kd !== 'long' && r.v.fno && r.v.fno.opt_trade ? E.optLine(r.v.fno.opt_trade, r.v.fno.side) : '') + '<div class="foot"><span>' + (v.conv ? v.conv + ' conviction' : '') + (kd !== 'long' && v.size_pct != null ? ' · size ' + v.size_pct + '%' : '') + '</span><span style="text-align:right;max-width:60%">' + F.esc(E.note(r.v.note)) + '</span></div>';
    });
  };
  E.markets.fno = function () {
    const P = E.lite.picks || {}; const N = E.lite.names; const all = [];
    for (const s in N) { if (N[s].fno && N[s].lots && (N[s].ss === 'BUY' || N[s].ss === 'SELL')) all.push({ sym: s, nm: N[s].nm, sector: N[s].sector, side: N[s].ss, score: N[s].s, lots: N[s].lots }); }
    all.sort(function (a, b) { return Math.abs(b.score - 50) - Math.abs(a.score - 50); });
    let h = '<div class="mi-defn"><b>F&O.</b> Either there is a trade or there is not. A future is bought or sold in lots sized so that one stop costs 1% of a ₹10 lakh book; the card says how many lots, what a lot risks and what it can pay. No "hold", no "wait". Under each idea, <b>the option</b>: a defined-risk vertical spread priced off the real chain — buy the strike at the spot, sell the strike at the target — with the debit, the maximum, the breakeven and the probability. The index cards and the option chain are below the ideas.</div>';
    h += E.sectionHead('Today\'s five', 'the strongest short-term sides among the names with a future · lots on a ₹10 lakh book');
    h += '<div class="e-grid e-auto">' + ((P.fno || []).map(function (p, i) { return E.pickCard(p, 'fno', i); }).join('') || '<div class="e-empty">no futures idea clears the bar today</div>') + '</div>';
    try { h += E.pairs.section(true); } catch (e) { }
    h += E.sectionHead('Every futures idea · ' + all.length, 'buy or sell, with lots · click for the contract, the margin estimate, the chain');
    h += '<div class="e-grid e-auto" id="e-mk-cards">' + all.slice(0, 24).map(function (p, i) { return E.cardFromLite(p, 'short', i); }).join('') + '</div>';
    h += E.sectionHead('The indices and the option chain', 'NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY — live spot, the future and basis, PCR, max pain, the walls; tap an index for the chain');
    E.markets._list = all;
    return h;
  };
  E.markets.records = function () {
    let h = '<div class="mi-defn"><b>The records.</b> The engine\'s own scorecard first (every pick frozen in history/engine_&lt;date&gt;.json and scored at its horizon), then the desk\'s ledger, the proof and the bench from BUILD &amp; SIZE.</div>';
    h += E.sectionHead('The engine\'s record', 'hit rate and average return by list');
    h += E.lite ? E.recordStrip() : E.notReady('The record');
    try { if (E.lite) h += E.calls.record(); } catch (e) { }
    if (E.lite && E.lite.record) { const R = E.lite.record; const rows = []; Object.keys(R).forEach(function (k) { (R[k].last || []).forEach(function (x) { rows.push(Object.assign({ list: k }, x)); }); }); if (rows.length) { h += '<div class="cd" style="padding:0;overflow-x:auto;margin-top:10px"><table class="tbl"><thead><tr><th>list</th><th>date</th><th>name</th><th>side</th><th>at</th><th>then</th><th>return</th><th>vs Nifty</th></tr></thead><tbody>' + rows.slice(-40).reverse().map(function (x) { return '<tr><td>' + F.esc(x.list) + '</td><td>' + F.esc(x.date) + '</td><td><b style="cursor:pointer" onclick="E.openShare(\'' + F.esc(x.sym) + '\')">' + F.esc(x.sym) + '</b></td><td>' + F.esc(x.side) + '</td><td>' + F.inr(x.px) + '</td><td>' + F.inr(x.px1) + '</td><td class="' + F.tone(x.ret) + '">' + F.pct(x.ret, 2) + '</td><td class="' + F.tone(x.excess) + '">' + F.pct(x.excess, 2) + '</td></tr>'; }).join('') + '</tbody></table></div>'; } }
    try { h += E.nowcast.postmortems(); } catch (e) { }
    try { h += E.pipe.section(); } catch (e) { }
    h += E.sectionHead('How we pick', 'the method, in one place');
    if (E.lite && E.lite.method) { const M = E.lite.method; h += '<div class="cd"><div class="lbl">Short term</div><div style="font-size:12.5px;color:var(--dim);margin-bottom:10px">' + F.esc(M.short) + '</div><div class="lbl">Long term</div><div style="font-size:12.5px;color:var(--dim);margin-bottom:10px">' + F.esc(M.long) + '</div><div class="lbl">Intraday</div><div style="font-size:12.5px;color:var(--dim)">' + F.esc(M.intraday) + '</div></div>'; }
    h += E.sectionHead('The desk · BUILD & SIZE', 'the frozen ledger, the proof, the bench, the paper book — as before');
    return h;
  };
  E.markets.afterRender = function () { if (E.markets.sub === 'short' || E.markets.sub === 'long' || E.markets.sub === 'fno') E.markets.hydrate(E.markets.sub === 'long' ? 'long' : 'short'); };

  /* ═══ RESEARCH · the lists in one place ═══ */
  E.research = { sub: 'picks' };
  E.research.show = function (s) { E.research.sub = s; E.research.render(); };
  E.research.render = function () {
    const el = document.getElementById('e-research'); if (!el) return;
    const sub = E.research.sub;
    let h = '<div class="e-between"><div><div class="e-h2">Research</div><div class="e-sub">every recommendation the engine makes, in one place — never a broker\'s opinion, always scored</div></div>' + L.chip() + '</div>';
    h += '<div class="subtabs" style="margin-top:12px">' + [['picks', 'Top picks'], ['buys', 'All buys'], ['sells', 'All sells'], ['accumulate', 'Accumulate'], ['industries', 'Industries'], ['portfolio', '🩻 My portfolio'], ['mylist', 'My list'], ['record', 'The record']].map(function (t) { return '<button class="subtab' + (sub === t[0] ? ' a' : '') + '" onclick="E.research.show(\'' + t[0] + '\')">' + t[1] + '</button>'; }).join('') + '</div>';
    if (!E.lite) { el.innerHTML = h + E.notReady('Research'); return; }
    const P = E.lite.picks || {};
    if (sub === 'picks') {
      h += E.sectionHead('Intraday · today', 'five names in play with a side and a plan'); h += '<div class="e-grid e-auto">' + ((P.intraday || []).map(function (p, i) { return E.pickCard(p, 'intraday', i); }).join('') || '<div class="e-empty">none today</div>') + '</div>';
      try { h += E.movers.section(false); } catch (e) { }
      h += E.sectionHead('F&O · lots', 'buy or sell N lots, ₹ risk and ₹ potential per lot'); h += '<div class="e-grid e-auto">' + ((P.fno || []).map(function (p, i) { return E.pickCard(p, 'fno', i); }).join('') || '<div class="e-empty">none today</div>') + '</div>';
      try { h += E.pairs.section(false); } catch (e) { }
      h += E.sectionHead('Short term · buys', '5–60 sessions · sticky'); h += '<div class="e-grid e-auto" id="e-mk-cards">' + ((P.short_buy || []).map(function (p, i) { return E.cardFromLite(p, 'short', i); }).join('') || '<div class="e-empty">none today</div>') + '</div>';
      h += E.sectionHead('Short term · sells', 'where a future exists to short'); h += '<div class="e-grid e-auto">' + ((P.short_sell || []).map(function (p, i) { return E.cardFromLite(p, 'short', i); }).join('') || '<div class="e-empty">none today</div>') + '</div>';
      h += E.sectionHead('Long term · accumulate', 'twelve months · sticky'); h += '<div class="e-grid e-auto">' + ((P.long || []).map(function (p, i) { return E.cardFromLite(p, 'long', i); }).join('') || '<div class="e-empty">none today</div>') + '</div>';
    } else if (sub === 'buys' || sub === 'sells' || sub === 'accumulate') {
      const side = sub === 'buys' ? 'BUY' : sub === 'sells' ? 'SELL' : 'ACCUMULATE'; const key = sub === 'accumulate' ? 'ls' : 'ss';
      E.markets.sector = ''; const list = E.markets.listOf(key, side, 5);
      h += E.sectionHead(side.charAt(0) + side.slice(1).toLowerCase() + ' · ' + list.length + ' names', 'the whole market, ranked');
      h += '<div class="e-list">' + list.slice(0, 80).map(function (p, i) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(p.sym) + '\')"><div class="n"><span class="e-rank">' + (i + 1) + '</span>' + F.esc(p.nm) + '<small>' + F.esc(p.sym) + ' · ' + F.esc(p.sector || '') + '</small></div><div>' + F.word(side) + ' <span class="e-score" style="color:var(--dim);font-size:12px;margin-left:6px">' + Math.round(p.score) + '</span></div><div class="px"><span data-live-px="' + F.esc(p.sym) + '">' + F.inr(L.px(p.sym)) + '</span><small class="' + F.tone(L.d1(p.sym)) + '" data-live-d="' + F.esc(p.sym) + '">' + F.pct(L.d1(p.sym), 2) + '</small></div></div>'; }).join('') + '</div>';
    } else if (sub === 'industries') {
      h += E.industry.grid();
    } else if (sub === 'portfolio') {
      h += '<div id="e-pf-host"></div>';
    } else if (sub === 'mylist') {
      h += E.sectionHead('My list', 'saved in this browser · ☆ on any research page'); h += E.watch.length ? '<div class="e-list">' + E.watch.map(function (s, i) { const n = E.lt(s) || {}; return '<div class="e-li" onclick="E.openShare(\'' + F.esc(s) + '\')"><div class="n">' + F.esc(n.nm || s) + '<small>' + F.esc(s) + ' · ' + F.esc(n.sector || '') + '</small></div><div>' + F.word(n.ss) + ' ' + F.word(n.ls) + '</div><div class="px"><span data-live-px="' + F.esc(s) + '">' + F.inr(L.px(s)) + '</span><small class="' + F.tone(L.d1(s)) + '" data-live-d="' + F.esc(s) + '">' + F.pct(L.d1(s), 2) + '</small></div></div>'; }).join('') + '</div>' : '<div class="e-empty">nothing on your list yet — open any share and tap ☆</div>';
    } else if (sub === 'record') {
      h += E.markets.records();
    }
    el.innerHTML = h;
    if (sub === 'portfolio') { try { E.pf.render(document.getElementById('e-pf-host')); } catch (e) { } }
    if (sub === 'picks') E.markets.hydrate('short');
    try { const syms = []; Object.keys(P).forEach(function (k) { (P[k] || []).forEach(function (p) { syms.push(p.sym); }); }); L.want(syms.concat(E.watch)); } catch (e) { }
  };
})(window.E);
