/* ═══ v146 · THE NOWCAST — the regime as probabilities, the market's impulses, the macro post-mortems ═══ */
(function (E) {
  const F = E.f;
  const N = E.nowcast = {};
  const REG = ['Reflation', 'Goldilocks', 'Stagflation', 'Disinflation'];
  const COL = { Reflation: 'var(--grn)', Goldilocks: 'var(--blu)', Stagflation: 'var(--org)', Disinflation: 'var(--pur, #a78bfa)' };
  N.get = function () { return (E.lite && E.lite.nowcast) || null; };
  N.bar = function (probs, h) {
    if (!probs) return '';
    return '<div class="e-stack" style="height:' + (h || 22) + 'px">' + REG.map(function (R) { const p = probs[R] || 0; return p >= 1 ? '<div style="width:' + p + '%;background:' + COL[R] + '" title="' + R + ' ' + p + '%"><span>' + (p >= 12 ? R + ' ' + Math.round(p) + '%' : (p >= 6 ? Math.round(p) + '%' : '')) + '</span></div>' : ''; }).join('') + '</div>';
  };
  N.zword = function (z) { if (z == null) return '<span style="color:var(--mut)">no read</span>'; const a = Math.abs(z); return '<b class="' + (z > 0.75 ? 'e-up' : z < -0.75 ? 'e-dn' : '') + '">' + F.sgn(z, 2) + 'σ</b> ' + (a >= 2 ? 'extreme' : a >= 1.25 ? 'strong' : a >= 0.75 ? 'clear' : 'faint'); };
  /* the card on the Macro tab and (short) on Home */
  N.card = function (short) {
    const nc = N.get(); if (!nc || !nc.probs) return '';
    const I = nc.impulses || {}; const O = nc.official || {}; const W = nc.words || {};
    let h = '<div class="cd" style="margin-bottom:12px"><div class="e-between"><div><div class="lbl" style="margin:0">The regime, as probabilities · the market\'s nowcast</div><div class="e-sub" style="margin-top:2px">official: <b style="color:#fff">' + F.esc(O.label || '') + '</b> (CPI ' + F.n(O.cpi, 2) + '% · IIP ' + F.n(O.iip, 1) + '%' + (O.as_of ? ' · prints ' + F.esc(String(O.as_of).replace(/^\|/, '').replace(/\|/g, ' · ')) : '') + ') · the market leans <b style="color:#fff">' + F.esc(nc.lean) + ' ' + (nc.probs[nc.lean] || 0) + '%</b>' + (nc.agree ? ' — in agreement' : ' — <span style="color:var(--org)">against the label</span>') + '</div></div>' + (short ? '<button class="e-btn sm" onclick="E.go(\'macro\')">the nowcast →</button>' : '') + '</div>';
    h += '<div style="margin-top:10px">' + N.bar(nc.probs, 24) + '</div>';
    if (!short) {
      h += '<div class="e-grid e-g2" style="margin-top:12px"><div class="e-kv">' +
        [['Growth impulse', I.growth, W.growth], ['Inflation impulse', I.inflation, W.inflation], ['Liquidity impulse', I.liquidity, W.liquidity]].map(function (x) { const im = x[1] || {}; return '<div class="c"><div class="k">' + x[0] + '</div><div class="v">' + N.zword(im.z) + '</div><div class="s">' + F.esc(x[2] || '') + (im.parts && im.parts.length ? ' · ' + im.parts.map(function (p) { return F.esc(p.label.split(' (')[0]) + ' ' + F.sgn(p.z, 1); }).join(', ') : '') + '</div></div>'; }).join('') +
        '<div class="c"><div class="k">Nowcast · CPI / IIP</div><div class="v">' + F.n((nc.now || {}).cpi, 2) + '% / ' + F.n((nc.now || {}).iip, 1) + '%</div><div class="s">P(inflation above 4%) ' + (nc.p_hot != null ? nc.p_hot + '%' : '—') + ' · P(growth above 3%) ' + (nc.p_grow != null ? nc.p_grow + '%' : '—') + '</div></div></div>' +
        '<div><div class="lbl">What it changes</div><div style="font-size:12.5px;color:var(--tx);line-height:1.6">The label on the page stays the official one (the sector edges, the regime record, the shock presets all read it). The probabilities are the market\'s lean this quarter: the model book on <span style="cursor:pointer;color:var(--blu)" onclick="E.go(\'micro\',\'where\')">Where to be</span> blends its base weights by them, so it never jumps on a label change, and each week\'s call is scored below.</div></div></div>';
      h += '<div style="font-size:11px;color:var(--mut);margin-top:10px">' + F.esc(nc.how || '') + '</div>';
    }
    return h + '</div>';
  };
  /* the post-mortems: five sessions on, what the regime call paid */
  N.postmortems = function () {
    const R = ((E.lite || {}).record || {}).macro || {};
    let h = E.sectionHead('The macro post-mortems · five sessions on', 'every day the regime, its probabilities, the session\'s call and the model book are frozen; five sessions later they are scored — the call\'s hit rate, the book against the Nifty, the OVERWEIGHT sleeves minus the UNDERWEIGHT ones');
    if (!R.n) return h + '<div class="e-empty">the first post-mortem prints five sessions after the first v146 pass — nothing is graded before its time</div>';
    h += '<div class="e-record"><div class="e-stat"><div class="k">The session\'s call</div><div class="v">' + (R.call_hit != null ? R.call_hit + '%' : '—') + '</div><div class="s">right on ' + R.n + ' scored days</div></div><div class="e-stat"><div class="k">The model book vs the Nifty</div><div class="v ' + F.tone(R.book_vs_nifty) + '">' + F.pct(R.book_vs_nifty, 2) + '</div><div class="s">average over five sessions</div></div><div class="e-stat"><div class="k">Overweight − underweight</div><div class="v ' + F.tone(R.over_minus_under) + '">' + F.pct(R.over_minus_under, 2) + '</div><div class="s">the sleeves\' words, five sessions on (n ' + (R.n_spread || 0) + ')</div></div><div class="e-stat"><div class="k">The Nifty itself</div><div class="v ' + F.tone(R.avg) + '">' + F.pct(R.avg, 2) + '</div><div class="s">average five-session move on those days</div></div></div>';
    h += '<div class="cd" style="padding:0;overflow-x:auto;margin-top:10px"><table class="tbl" style="width:100%"><thead><tr><th>day</th><th>regime · probabilities</th><th>the call</th><th style="text-align:right">Nifty · 5s</th><th style="text-align:right">the book</th><th style="text-align:right">over · under</th></tr></thead><tbody>' + (R.last || []).slice().reverse().map(function (x) { return '<tr><td>' + F.esc(x.date) + '</td><td><b style="color:#fff">' + F.esc(x.sym) + '</b>' + (x.probs ? '<div style="width:140px;margin-top:3px">' + N.bar(x.probs, 8) + '</div>' : '') + '</td><td>' + F.esc(x.side) + ' <span class="e-word ' + (x.call_ok ? 'buy' : 'sell') + '" style="font-size:10px">' + (x.call_ok ? 'RIGHT' : 'WRONG') + '</span></td><td style="text-align:right" class="' + F.tone(x.ret) + '">' + F.pct(x.ret, 2) + '</td><td style="text-align:right" class="' + F.tone(x.book) + '">' + F.pct(x.book, 2) + '<div style="font-size:10px;color:var(--mut)">vs Nifty ' + F.pct(x.excess, 2) + '</div></td><td style="text-align:right"><span class="' + F.tone(x.over) + '">' + F.pct(x.over, 1) + '</span> · <span class="' + F.tone(x.under) + '">' + F.pct(x.under, 1) + '</span></td></tr>'; }).join('') + '</tbody></table></div>';
    return h;
  };
  /* the option on an F&O idea, one line */
  E.optLine = function (ot, side) {
    if (!ot) return '';
    const fits = ot.fits_book !== false;
    return '<div class="e-opt' + (fits ? '' : ' warn') + '"><b>Or the option · ' + F.esc(ot.kind) + '</b> ' + F.esc(ot.expiry || '') + (ot.dte ? ' (' + ot.dte + 'd)' : '') + ' · buy ' + F.n(ot.buy, 0) + ' / sell ' + F.n(ot.sell, 0) + ' ' + (side === 'BUY' ? 'CE' : 'PE') + ' · pay <b>' + F.big(ot.debit_lot) + '</b> a lot · max <b class="e-up">' + F.big(ot.max_lot) + '</b> (' + (ot.rr != null ? ot.rr + ' : 1' : '—') + ') · breakeven ' + F.inr(ot.be) + ' · p ≈ ' + (ot.p_profit != null ? ot.p_profit + '%' : '—') + ' · IV ' + F.n(ot.iv, 1) + '%' + (fits ? '' : ' · <span style="color:var(--org)">one lot risks more than the 1% rule — the future is the sized expression</span>') + '<div style="font-size:10.5px;color:var(--mut);margin-top:2px">' + F.esc(ot.src || '') + (ot.naked ? ' · naked: the ' + F.n(ot.naked.k, 0) + ' at ' + F.inr(ot.naked.px) + ' (' + F.big(ot.naked.lot) + ' a lot, breakeven ' + F.inr(ot.naked.be) + ')' : '') + '</div></div>';
  };
})(window.E);
