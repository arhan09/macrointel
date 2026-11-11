/* ═══ v150 · THE PATH — one, three, six and twelve months: what the engine expects, what the name's own stretches did, the dips on the way ═══ */
(function (E) {
  const F = E.f, L = E.live;
  const P = E.path = {};
  P.H = { '1m': '1 month', '3m': '3 months', '6m': '6 months', '12m': '12 months' };
  P.cls = function (w) { return w === 'GOOD' ? 'buy' : w === 'LEANS GOOD' ? 'lean-buy' : w === 'WEAK' ? 'sell' : w === 'LEANS WEAK' ? 'lean-sell' : w === 'NEUTRAL' ? 'hold' : 'none'; };
  P.word = function (w, size) { return '<span class="e-word ' + P.cls(w) + (size ? ' ' + size : '') + '">' + F.esc(w || 'NO READ') + '</span>'; };
  P.dipTag = function (r) { const st = r && r.st; if (!st || st.p_dip == null) return ''; return r.may_dip ? '<span class="e-tag e-dip">may dip ' + st.dip + '%+ · ' + st.p_dip + '%</span>' : '<span class="e-tag">dips ' + st.dip + '%+ in ' + st.p_dip + '%</span>'; };
  /* the four-digit code on every lite row: lean 0..4 (WEAK..GOOD), +5 when a dip is the likelier thing */
  P.decode = function (code) { const out = []; String(code || '').split('').forEach(function (ch, i) { const d = +ch; if (isNaN(d)) return; const lean = d % 5; out.push({ h: ['1m', '3m', '6m', '12m'][i], lean: lean, dip: d >= 5, word: ['WEAK', 'LEANS WEAK', 'NEUTRAL', 'LEANS GOOD', 'GOOD'][lean] }); }); return out; };
  P.mini = function (code, opt) {
    const rows = P.decode(code); if (!rows.length) return '';
    const col = function (l) { return l >= 4 ? 'var(--grn)' : l === 3 ? 'rgba(47,210,125,.55)' : l === 1 ? 'rgba(255,92,92,.55)' : l === 0 ? 'var(--red)' : 'var(--mut)'; };
    return '<span class="e-pmini" title="' + rows.map(function (r) { return P.H[r.h] + ' ' + r.word + (r.dip ? ', may dip' : ''); }).join(' · ') + '">' + rows.map(function (r) { return '<i style="background:' + col(r.lean) + (r.dip ? ';box-shadow:inset 0 0 0 1.5px var(--amb)' : '') + '"></i>'; }).join('') + ((opt && opt.label) ? '<small>' + rows.map(function (r) { return r.h; }).join('·') + '</small>' : '') + '</span>';
  };
  P.strip = function (p) {
    if (!p || !p.rows) return '';
    return '<div class="e-row" style="gap:6px;flex-wrap:wrap">' + p.rows.map(function (r) { return '<span class="e-pstep"><span class="k">' + r.h + '</span>' + P.word(r.word) + (r.may_dip ? '<span class="e-tag e-dip">dip</span>' : '') + '</span>'; }).join('') + '</div>';
  };
  P.ladder = function (p, opt) {
    opt = opt || {};
    if (!p || !p.rows || !p.rows.length) return '<div class="e-empty">no path — too little history on the tape</div>';
    let h = '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl e-ptbl" style="width:100%"><thead><tr><th>horizon</th><th>the read</th><th>the engine expects</th><th>its own stretches</th><th>the dips on the way</th></tr></thead><tbody>';
    p.rows.forEach(function (r) {
      const st = r.st || {};
      h += '<tr><td style="white-space:nowrap"><b>' + P.H[r.h] + '</b></td><td style="white-space:nowrap">' + P.word(r.word) + (r.may_dip ? ' <span class="e-tag e-dip">may dip</span>' : '') + '</td>';
      h += '<td>' + (r.exp != null ? '<b class="' + F.tone(r.exp) + '">' + F.pct(r.exp, 0) + '</b> <span style="color:var(--dim)">· P(higher) ' + r.p_up + '%</span><div style="font-size:11px;color:var(--mut)">one σ: ' + F.inr(r.lo1) + ' – ' + F.inr(r.hi1) + '</div>' : '<span style="color:var(--mut)">—</span>') + '</td>';
      h += '<td>' + (st.hit != null ? 'ended higher <b>' + st.hit + '%</b> of the time · median <b class="' + F.tone(st.med) + '">' + F.pct(st.med, 0) + '</b><div style="font-size:11px;color:var(--mut)">quartiles ' + F.pct(st.q1, 0) + ' … ' + F.pct(st.q3, 0) + ' · n ' + st.n + ' · ' + F.esc(r.src || '') + '</div>' : '<span style="color:var(--mut)">' + (opt.thin || 'not enough history') + '</span>') + '</td>';
      h += '<td>' + (st.p_dip != null ? '<b>' + st.p_dip + '%</b> saw a dip of ' + st.dip + '%+<div style="font-size:11px;color:var(--mut)">typical worst dip ' + Math.abs(st.worst_med || 0) + '%' + (st.worst_up != null ? ' · ' + Math.abs(st.worst_up) + '% even when it ended higher' : '') + '</div>' : '<span style="color:var(--mut)">—</span>') + '</td></tr>';
    });
    h += '</tbody></table></div>';
    return h;
  };
  /* the research page's block: the head line, the ladder, the method */
  P.section = function (sym, r) {
    const p = r && r.path; const lt = E.lt(sym) || {};
    let h = E.sectionHead('The path · one month to twelve', 'what the engine expects at each horizon, what this name\'s own stretches of that length did, and the dips that came on the way — so "good" and "may dip" can both be true', '<span class="act" onclick="E.report.open(\'' + F.esc(sym) + '\')">the research note →</span>');
    if (!p || !p.rows) return h + '<div class="e-empty">no path for ' + F.esc(lt.nm || sym) + ' — the tape is too short to read stretches from (a young listing, or a BSE-only name the engine has not accrued yet)</div>';
    h += '<div class="e-phead"><div class="t">' + F.esc(p.head || '') + '</div>' + P.strip(p) + '</div>';
    h += P.ladder(p);
    h += '<div class="e-line" style="margin-top:8px">' + p.rows.map(function (x) { return '<div style="margin:3px 0">' + F.esc(x.line) + '</div>'; }).join('') + '</div>';
    h += '<div class="note">' + F.esc(p.how || '') + ' · the path\'s own record (six and twelve months on: was the lean right, did the called dip come) grades on Markets → Why believe this</div>';
    return h;
  };
  /* the market's path (the Macro tab, Home, Ask) */
  P.mkt = function () { return (E.lite && E.lite.mpath) || null; };
  P.market = function (full) {
    const m = P.mkt();
    if (!m || !m.rows || !m.rows.length) return '<div class="cd"><div class="lbl">The market\'s path</div><div class="e-empty">arrives with the first v150 pass</div></div>';
    let h = '<div class="cd e-mpath">';
    h += '<div class="e-between" style="flex-wrap:wrap;gap:8px"><div><div class="lbl" style="margin:0">The market\'s path · the Nifty from ' + F.esc(m.regime) + ', one month to twelve</div><div style="font-size:12.5px;color:var(--dim);margin-top:4px">read from every stretch of that length that began in a ' + F.esc(m.regime) + ' since 2014, the odds the regime still holds that far out, and what a turn would mean</div></div>' + (full ? '' : '<span class="act" onclick="E.go(\'macro\',\'path\')">the full read →</span>') + '</div>';
    h += '<div style="margin:10px 0 8px">' + P.strip(m) + '</div>';
    h += '<div style="font-size:13px;color:var(--tx);line-height:1.55">' + F.esc(m.head || '') + '</div>';
    if (full) {
      h += '<div style="margin-top:12px;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>horizon</th><th>the read</th><th>' + F.esc(m.regime) + ' stretches</th><th>the dips on the way</th><th>regime holds</th><th>if it turns</th></tr></thead><tbody>';
      m.rows.forEach(function (r) {
        const st = r.st || r.all || {}; const br = r.by_regime || {};
        h += '<tr><td><b>' + P.H[r.h] + '</b></td><td style="white-space:nowrap">' + P.word(r.word) + (r.may_dip ? ' <span class="e-tag e-dip">may dip</span>' : '') + '</td>';
        h += '<td>' + (st.hit != null ? 'up <b>' + st.hit + '%</b> · median <b class="' + F.tone(st.med) + '">' + F.pct(st.med, 1) + '</b><div style="font-size:11px;color:var(--mut)">quartiles ' + F.pct(st.q1, 0) + ' … ' + F.pct(st.q3, 0) + ' · n ' + st.n + '</div>' : '—') + '</td>';
        h += '<td>' + (st.p_dip != null ? '<b>' + st.p_dip + '%</b> saw ' + st.dip + '%+<div style="font-size:11px;color:var(--mut)">typical worst ' + Math.abs(st.worst_med || 0) + '%' + (st.worst_up != null ? ' · ' + Math.abs(st.worst_up) + '% even when up' : '') + '</div>' : '—') + '</td>';
        h += '<td>' + (r.p_same != null ? '<b>' + r.p_same + '%</b>' : '—') + '</td>';
        h += '<td style="font-size:11.5px;color:var(--dim)">' + Object.keys(br).filter(function (k) { return k !== m.regime; }).map(function (k) { const v = br[k]; return k + ' up ' + v.hit + '% · ' + F.pct(v.med, 0); }).join('<br>') + '</td></tr>';
      });
      h += '</tbody></table></div>';
      h += '<div class="e-line" style="margin-top:8px">' + m.rows.map(function (x) { return '<div style="margin:3px 0">' + F.esc(x.line) + '</div>'; }).join('') + '</div>';
      const sx = m.sectors || {};
      ['6m', '12m'].forEach(function (k) {
        const s = sx[k]; if (!s || !(s.best || []).length) return;
        h += '<div class="e-grid e-g2" style="margin-top:10px;gap:12px"><div><div class="lbl">paid over ' + P.H[k] + ' from ' + F.esc(m.regime) + ' starts</div>' + s.best.map(function (r) { return '<div class="e-between" style="font-size:12.5px;padding:3px 0;border-bottom:1px solid var(--brd)"><span class="act" onclick="E.industry.open(\'' + F.esc(r.sector) + '\')">' + F.esc(r.sector) + '</span><span><b class="' + F.tone(r.med) + '">' + F.pct(r.med, 0) + '</b> <span style="color:var(--mut)">· up ' + r.hit + '% · n ' + r.n + '</span></span></div>'; }).join('') + '</div>';
        h += '<div><div class="lbl">did not</div>' + (s.worst || []).map(function (r) { return '<div class="e-between" style="font-size:12.5px;padding:3px 0;border-bottom:1px solid var(--brd)"><span class="act" onclick="E.industry.open(\'' + F.esc(r.sector) + '\')">' + F.esc(r.sector) + '</span><span><b class="' + F.tone(r.med) + '">' + F.pct(r.med, 0) + '</b> <span style="color:var(--mut)">· up ' + r.hit + '% · n ' + r.n + '</span></span></div>'; }).join('') + '</div></div>';
      });
      if ((m.drivers || []).length) h += '<div style="font-size:12px;color:var(--dim);margin-top:10px">the market\'s impulses now: ' + F.esc(m.drivers.join(' · ')) + (m.alt ? ' · second lean ' + F.esc(m.alt) + ' ' + Math.round(m.alt_p || 0) + '%' : '') + '</div>';
      h += '<div class="note">' + F.esc(m.how || '') + '</div>';
    }
    h += '</div>';
    return h;
  };
  P.marketSection = function () {
    return E.sectionHead('The market\'s path', 'the Nifty one month to twelve months out, read from the regime — with the odds the regime holds and what a turn would mean') + P.market(true);
  };
  /* Ask */
  P.askName = async function (sym) {
    const lt = E.lt(sym) || {}; const r = await E.row(sym); const p = r && r.path;
    if (!p || !p.rows) return { html: E.ask.card('<span class="e-word hold big">NO PATH</span>', F.esc(lt.nm || sym) + ' has too little history on the tape for a path.', [], [], ''), ctx: { sym: sym } };
    const by = {}; p.rows.forEach(function (x) { by[x.h] = x; });
    const w12 = (by['12m'] || {}).word || (by['6m'] || {}).word || 'NEUTRAL';
    const kv = p.rows.map(function (x) { return [P.H[x.h], x.word + (x.may_dip ? ', may dip' : ''), x.word === 'GOOD' || x.word === 'LEANS GOOD' ? 'up' : x.word === 'WEAK' || x.word === 'LEANS WEAK' ? 'dn' : '']; });
    const html = E.ask.card('<span class="e-word ' + P.cls(w12) + ' big">' + F.esc(w12) + ' · 12 MONTHS</span>', F.esc(p.head || ''), kv, p.rows.map(function (x) { return F.esc(x.line); }), P.ladder(p), '<span class="act" onclick="E.openShare(\'' + F.esc(sym) + '\')">the research page →</span> · <span class="act" onclick="E.report.open(\'' + F.esc(sym) + '\')">the research note →</span>');
    return { html: html, ctx: { sym: sym, path: p.head } };
  };
  P.askMarket = function () {
    const m = P.mkt();
    if (!m || !m.rows) return { html: E.ask.card('<span class="e-word hold big">THE MARKET\'S PATH</span>', 'arrives with the first v150 pass', [], [], ''), ctx: {} };
    const w12 = (m.rows.find(function (x) { return x.h === '12m'; }) || {}).word || 'NEUTRAL';
    return { html: E.ask.card('<span class="e-word ' + P.cls(w12) + ' big">' + F.esc(w12) + ' · 12 MONTHS</span>', F.esc(m.head || ''), m.rows.map(function (x) { return [P.H[x.h], x.word + (x.may_dip ? ', may dip' : ''), '']; }), m.rows.map(function (x) { return F.esc(x.line); }), P.market(true), ''), ctx: { mpath: m.head } };
  };
})(window.E);
