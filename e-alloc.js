/* ═══ v145 · WHERE TO BE — the regime → asset map · and THE PAIRS — market-neutral ideas inside F&O ═══ */
(function (E) {
  const F = E.f, L = E.live;
  const AL = E.alloc = {};
  const REG = ['Goldilocks', 'Reflation', 'Stagflation', 'Disinflation'];
  AL.cls = function (w) { return w === 'OVERWEIGHT' ? 'buy' : w === 'UNDERWEIGHT' ? 'sell' : w === 'CASH' ? 'none' : 'hold'; };
  AL.cell = function (x, cur) {
    if (!x || x.avg13 == null) return '<td class="e-heat" style="color:var(--mut)">—</td>';
    const v = x.avg13; const a = Math.min(1, Math.abs(v) / 8); const bg = v >= 0 ? 'rgba(47,210,125,' + (0.08 + a * 0.45) + ')' : 'rgba(255,92,92,' + (0.08 + a * 0.45) + ')';
    return '<td class="e-heat' + (cur ? ' cur' : '') + '" style="background:' + bg + '" title="' + x.n + ' weeks · up ' + (x.hit13 != null ? x.hit13 : '—') + '% of the time"><b>' + F.pct(v, 1) + '</b><small>' + (x.hit13 != null ? x.hit13 + '% up' : '') + ' · n ' + x.n + '</small></td>';
  };
  AL.render = function () {
    const A = (E.lite && E.lite.alloc) || null;
    if (!A || !(A.alloc || []).length) return '<div class="mi-defn"><b>Where to be.</b> The regime → asset map: what each Indian asset has paid in each regime since 2015 and a model allocation for today\'s regime.</div>' + E.notReady('The map');
    const B = A.base || {}; const rows = A.rows || [];
    let h = '<div class="mi-defn"><b>Where to be · ' + F.esc(A.regime) + '.</b> Prometheus-style: the regime decides the shape of the book, the trend decides which sleeve gets the money, the record since 2015 confirms or vetoes it. Measured on each sleeve\'s long index in rupees; the ETF named is what you trade. A map of what each regime has paid — not a forecast.</div>';
    /* the model book */
    h += E.sectionHead('The model book · ₹10 lakh', 'equity ' + B.equity + '% · metals ' + B.metals + '% · bonds ' + B.bonds + '% · cash ' + B.cash + '%' + (A.blended && A.probs ? ' · base weights blended by the nowcast: ' + Object.keys(A.probs).filter(function (k) { return A.probs[k] >= 5; }).sort(function (a, b) { return A.probs[b] - A.probs[a]; }).map(function (k) { return k + ' ' + Math.round(A.probs[k]) + '%'; }).join(', ') : '') + (A.gate ? ' · the gate is on: ten points moved from equity to cash' : '') + ' · scale it to your own book');
    const seg = [['Equity', B.equity, 'var(--blu)'], ['Metals', B.metals, 'var(--amb, #e0b341)'], ['Bonds', B.bonds, 'var(--pur, #a78bfa)'], ['Cash', B.cash, 'var(--s3)']];
    h += '<div class="cd"><div class="e-stack">' + seg.map(function (s) { return s[1] ? '<div style="width:' + s[1] + '%;background:' + s[2] + '" title="' + s[0] + ' ' + s[1] + '%"><span>' + s[0] + ' ' + Math.round(s[1]) + '%</span></div>' : ''; }).join('') + '</div>';
    h += '<div class="e-list" style="margin-top:12px">' + (A.alloc || []).map(function (a) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(a.sym) + '\')"><div class="n">' + F.esc(a.nm) + '<small>' + F.esc(a.sym) + ' · ' + F.esc(a.cls || '') + '</small><div style="font-size:11px;color:var(--dim);font-weight:400;margin-top:1px">' + F.esc(a.why) + '</div></div><div>' + (a.word ? '<span class="e-word ' + AL.cls(a.word) + '">' + F.esc(a.word) + '</span>' : '') + '</div><div class="px">' + F.big(a.inr) + '<small style="color:var(--dim)">' + a.pct + '% · ' + (a.units ? F.n(a.units, 0) + ' units at ' + F.inr(a.px) : '—') + '</small></div></div>'; }).join('') + '</div>';
    h += '<div style="font-size:11.5px;color:var(--dim);margin-top:10px">' + F.esc(A.rule || '') + '</div></div>';
    /* every sleeve */
    h += E.sectionHead('Every sleeve · the word, the trend, the regime\'s record', 'OVERWEIGHT = trending and not vetoed by the record in ' + F.esc(A.regime) + ' · UNDERWEIGHT = trending down and not rescued by it · tap for the ETF\'s own research page');
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>sleeve</th><th>ETF</th><th style="text-align:right">price</th><th>word</th><th style="text-align:right">vs 40-wk</th><th style="text-align:right">13 weeks</th><th style="text-align:right">in ' + F.esc(A.regime) + ' · a quarter</th><th style="text-align:right">all regimes</th><th style="text-align:right">edge</th></tr></thead><tbody>' +
      rows.map(function (r) { const t = r.trend || {}, s = r.study || {}; return '<tr><td><b style="color:#fff">' + F.esc(r.nm) + '</b><div style="font-size:10.5px;color:var(--mut)">' + F.esc(r.cls || '') + (s.on ? ' · study on ' + F.esc(s.on) + ' since ' + F.esc(s.since || '') : (r.key === 'cash' ? '' : ' · no long study yet')) + '</div></td><td><b style="cursor:pointer;color:var(--blu)" onclick="E.openShare(\'' + F.esc(r.sym) + '\')">' + F.esc(r.sym) + '</b>' + (r.thin ? '<div style="font-size:10px;color:var(--org)">thin</div>' : '') + '</td><td style="text-align:right"><span data-live-px="' + F.esc(r.sym) + '">' + F.inr(r.px) + '</span><div class="' + F.tone(r.d1) + '" style="font-size:10.5px" data-live-d="' + F.esc(r.sym) + '">' + F.pct(r.d1, 2) + '</div></td><td><span class="e-word ' + AL.cls(r.word) + '">' + F.esc(r.word) + '</span></td><td style="text-align:right" class="' + F.tone(t.vs40) + '">' + F.pct(t.vs40, 1) + '</td><td style="text-align:right" class="' + F.tone(t.r13) + '">' + F.pct(t.r13, 1) + '</td><td style="text-align:right" class="' + F.tone(s.avg13) + '">' + (s.avg13 != null ? (F.pct(s.avg13, 1) + '<div style="font-size:10px;color:var(--mut)">' + (s.hit13 != null ? s.hit13 + '% up · ' : '') + (s.n13 != null ? 'n ' + s.n13 : '') + (s.note ? F.esc(s.note) : '') + '</div>') : '—') + '</td><td style="text-align:right" class="' + F.tone(s.all13) + '">' + F.pct(s.all13, 1) + '</td><td style="text-align:right" class="' + F.tone(s.edge13) + '">' + F.pct(s.edge13, 1) + '</td></tr>'; }).join('') + '</tbody></table></div>';
    /* the regime map */
    h += E.sectionHead('The regime map', 'average forward 13-week return of each sleeve in each regime since 2015 · the column for today\'s regime is marked · this is the table a macro desk keeps on the wall');
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl e-map" style="width:100%"><thead><tr><th>sleeve</th>' + REG.map(function (R) { return '<th style="text-align:center' + (R === A.regime ? ';color:#fff' : '') + '">' + R + (R === A.regime ? ' <span class="e-tag">now</span>' : '') + '</th>'; }).join('') + '</tr></thead><tbody>' +
      rows.filter(function (r) { return r.study && r.study.by; }).map(function (r) { return '<tr><td><b style="color:#fff;cursor:pointer" onclick="E.openShare(\'' + F.esc(r.sym) + '\')">' + F.esc(r.nm) + '</b><div style="font-size:10px;color:var(--mut)">' + F.esc(r.sym) + '</div></td>' + REG.map(function (R) { return AL.cell((r.study.by || {})[R], R === A.regime); }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
    h += '<div class="note" style="margin-top:12px">' + F.esc(A.how || '') + (A.source ? ' · data: ' + F.esc(A.source) : '') + '</div>';
    return h;
  };
  /* the home card: three lines */
  AL.card = function () {
    const A = (E.lite && E.lite.alloc) || null; if (!A || !(A.alloc || []).length) return '';
    const B = A.base || {}; const over = (A.rows || []).filter(function (r) { return r.word === 'OVERWEIGHT'; }).slice(0, 5);
    return '<div class="cd" style="margin-top:14px"><div class="e-between"><div><div class="lbl" style="margin:0">Where to be · ' + F.esc(A.regime) + '</div><div class="e-sub" style="margin-top:2px">the model book: <b style="color:#fff">' + B.equity + '% equity · ' + B.metals + '% metals · ' + B.bonds + '% bonds · ' + B.cash + '% cash</b>' + (over.length ? ' · trending and favoured: ' + over.map(function (r) { return F.esc(r.nm); }).join(', ') : '') + '</div></div><button class="e-btn sm" onclick="E.go(\'micro\',\'where\')">the map →</button></div></div>';
  };

  /* ═══ THE PAIRS ═══ */
  const PR = E.pairs = {};
  PR.card = function (p, i) {
    return '<div class="e-pick acc"><div class="top"><div>' + (i != null ? '<span class="e-rank">' + (i + 1) + '</span>' : '') + '<span class="nm">LONG ' + F.esc(p.nm_a) + ' · SHORT ' + F.esc(p.nm_b) + '</span><div class="sy">' + F.esc(p.a) + ' / ' + F.esc(p.b) + ' · ' + F.esc(p.sector) + ' · ' + F.esc(p.conv) + ' conviction</div></div><div><div class="px">' + F.n(Math.abs(p.z), 1) + 'σ</div><div class="d" style="color:var(--dim)">half-life ' + p.hl + 'd · ρ ' + F.n(p.corr, 2) + '</div></div></div>' +
      '<div class="e-row" style="margin-top:8px"><span class="e-word buy">BUY ' + p.lots_a + ' lot' + (p.lots_a > 1 ? 's' : '') + ' ' + F.esc(p.a) + '</span><span class="e-word sell">SELL ' + p.lots_b + ' lot' + (p.lots_b > 1 ? 's' : '') + ' ' + F.esc(p.b) + '</span></div>' +
      '<div class="plan"><div><div class="k">Pays at the mean</div><div class="v e-up">+' + F.big(p.exp_inr) + '</div><div style="font-size:10.5px;color:var(--dim)">' + F.pct(p.exp_pct, 1) + ' on the long leg</div></div><div><div class="k">Stop at ' + p.stop_z + 'σ</div><div class="v e-dn">−' + F.big(p.loss_inr) + '</div><div style="font-size:10.5px;color:var(--dim)">' + F.pct(-p.loss_pct, 1) + '</div></div><div><div class="k">Horizon</div><div class="v">' + p.h + ' sessions</div><div style="font-size:10.5px;color:var(--dim)">2 × half-life</div></div></div>' +
      '<div class="foot"><span>' + F.big(p.not_a) + ' long · ' + F.big(p.not_b) + ' short · margin ≈ ' + F.big(p.margin_est) + '</span><span>lots: ' + F.esc(p.lot_src || '') + '</span></div>' +
      '<div class="why">' + (p.why || []).slice(0, 3).map(F.esc).join(' · ') + '</div>' +
      '<div class="e-row" style="margin-top:8px"><button class="e-btn sm" onclick="E.openShare(\'' + F.esc(p.a) + '\')">' + F.esc(p.a) + ' →</button><button class="e-btn sm" onclick="E.openShare(\'' + F.esc(p.b) + '\')">' + F.esc(p.b) + ' →</button></div></div>';
  };
  PR.section = function (full) {
    const P = (E.lite && E.lite.pairs) || {}; const ideas = P.ideas || [];
    let h = E.sectionHead('Pairs · market-neutral', 'two names in one sector, the spread stretched beyond 2σ: long the cheap leg, short the rich one, in rupee-balanced lots — pays when the spread returns to its mean, whatever the index does · ' + (P.n_tested || 0) + ' pairs tested, ' + (P.n_fit || 0) + ' fit the model');
    if (!ideas.length) return h + '<div class="e-empty">no pair is stretched beyond 2σ today — the page prints no idea it cannot defend' + (P.note ? ' · ' + F.esc(P.note) : '') + '</div>';
    h += '<div class="e-grid e-auto">' + ideas.map(function (p, i) { return PR.card(p, i); }).join('') + '</div>';
    if (full) h += '<div class="note">' + F.esc(P.how || '') + ' Both legs are futures; the margin estimate is 18% of gross notional. Scored in the record as the long leg\'s return minus the short leg\'s over ten sessions.</div>';
    return h;
  };
})(window.E);
