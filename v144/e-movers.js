/* ═══ v147 · TOMORROW'S LIKELY MOVERS · WHAT CHANGED · THE RESULTS CALENDAR ═══ */
(function (E) {
  const F = E.f, L = E.live;
  const M = E.movers = {};
  M.get = function () { return (E.lite && E.lite.movers) || null; };
  M.card = function (m, i) {
    const lean = m.lean === 'UP' ? '<span class="e-word buy">LEAN UP</span>' : m.lean === 'DOWN' ? '<span class="e-word sell">LEAN DOWN</span>' : '<span class="e-word hold">EITHER WAY</span>';
    return '<div class="e-pick ' + (m.lean === 'UP' ? 'buy' : m.lean === 'DOWN' ? 'sell' : 'none') + '" onclick="E.openShare(\'' + F.esc(m.sym) + '\')"><div class="top"><div>' + (i != null ? '<span class="e-rank">' + (i + 1) + '</span>' : '') + '<span class="nm">' + F.esc(m.nm) + '</span><div class="sy">' + F.esc(m.sym) + ' · ' + F.esc(m.sector || '') + (m.fno ? ' · F&O' : '') + '</div></div><div><div class="px" data-live-px="' + F.esc(m.sym) + '">' + F.inr(L.px(m.sym)) + '</div><div class="d ' + F.tone(L.d1(m.sym)) + '" data-live-d="' + F.esc(m.sym) + '">' + F.pct(L.d1(m.sym), 2) + '</div></div></div>' +
      '<div class="e-row" style="margin-top:8px">' + lean + (m.event ? '<span class="e-word avoid">' + F.esc(m.event).toUpperCase() + '</span>' : '') + '</div>' +
      '<div class="plan"><div><div class="k">P(move ≥ 1.5σ)</div><div class="v">' + m.p_move + '%</div><div style="font-size:10.5px;color:var(--dim)">model ' + m.p_ml + '%</div></div><div><div class="k">Expected swing</div><div class="v">±' + F.n(m.exp_pct, 1) + '%</div><div style="font-size:10.5px;color:var(--dim)">' + F.inr((L.px(m.sym) || m.px) * (1 - m.exp_pct / 100)) + ' – ' + F.inr((L.px(m.sym) || m.px) * (1 + m.exp_pct / 100)) + '</div></div><div><div class="k">P(up)</div><div class="v">' + m.p_up + '%</div><div style="font-size:10.5px;color:var(--dim)">σ ' + m.sig20 + '%/day' + (m.implied_1d ? ' · chain ±' + m.implied_1d + '%' : '') + '</div></div></div>' +
      ((m.drivers || []).length ? '<div class="why">' + m.drivers.map(F.esc).join(' · ') + '</div>' : '<div class="why" style="color:var(--mut)">the model alone — no event, no unusual tape</div>') + '</div>';
  };
  M.section = function (full) {
    const mv = M.get();
    let h = E.sectionHead('Tomorrow\'s likely movers', (mv && mv.list && mv.list.length) ? ('the names most likely to move ≥ 1.5σ in the next session — a model trained every pass on the daily panel (' + (mv.names || '—') + ' names · ' + (mv.sessions || '—') + ' sessions), plus what only today knows: results dates, the chain\'s implied move, futures OI · out-of-sample AUC ' + (mv.auc_move != null ? mv.auc_move : '—') + ' for the move, ' + (mv.auc_dir != null ? mv.auc_dir : '—') + ' for the direction (0.5 = a coin; base rate ' + (mv.base_rate || '—') + '%)') : 'the next-session movers model arrives with the first v147 pass', (full ? '' : '<span class="act" onclick="E.go(\'micro\',\'today\')">all twelve →</span>'));
    if (!mv || !mv.list || !mv.list.length) return h + '<div class="e-empty">' + F.esc((mv && (mv.note || mv.error)) || 'not on this pass') + '</div>';
    h += '<div class="e-grid e-auto">' + mv.list.slice(0, full ? 12 : 6).map(function (m, i) { return M.card(m, i); }).join('') + '</div>';
    if (full) h += '<div class="note">' + F.esc(mv.how || '') + ' The direction model is barely better than a coin on its own (it never is, one day out); the lean also uses the engine\'s intraday read. Scored next session in the record: did it move ≥ 1.5σ, did the lean hold.</div>';
    return h;
  };
  /* what changed since yesterday */
  M.changes = function (full) {
    const C = (E.lite && E.lite.changes) || null;
    let h = E.sectionHead('What changed since ' + F.esc((C && C.since) || 'the last snapshot'), 'the verdicts that flipped — every name\'s sides are snapshotted once a day and compared', (full ? '' : ''));
    if (!C || !C.since) return h + '<div class="e-empty">the first comparison prints on the second day of v147 — nothing to diff before then</div>';
    const row = function (r, word, cls) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(r.sym) + '\')"><div class="n">' + F.esc(r.nm) + '<small>' + F.esc(r.sym) + ' · ' + F.esc(r.sector || '') + (r.now ? ' · now ' + F.esc(r.now) : '') + '</small></div><div><span class="e-word ' + cls + '">' + word + '</span></div><div class="px"><span data-live-px="' + F.esc(r.sym) + '">' + F.inr(L.px(r.sym)) + '</span><small class="' + F.tone(L.d1(r.sym)) + '" data-live-d="' + F.esc(r.sym) + '">' + F.pct(L.d1(r.sym), 2) + '</small></div></div>'; };
    const blocks = [['Turned BUY', 'to_buy', 'BUY', 'buy'], ['Left BUY', 'from_buy', 'WAS BUY', 'hold'], ['Turned SELL', 'to_sell', 'SELL', 'sell'], ['Left SELL', 'from_sell', 'WAS SELL', 'hold'], ['Turned ACCUMULATE', 'to_acc', 'ACCUMULATE', 'acc'], ['Left ACCUMULATE', 'from_acc', 'WAS ACC.', 'hold'], ['Turned AVOID', 'to_avoid', 'AVOID', 'avoid'], ['Left AVOID', 'from_avoid', 'WAS AVOID', 'hold']];
    const lim = full ? 12 : 4;
    const some = blocks.filter(function (b) { return (C[b[1]] || []).length; });
    if (!some.length) return h + '<div class="e-empty">no verdict flipped on a liquid name since ' + F.esc(C.since) + '</div>';
    h += '<div class="e-grid e-g2">' + some.slice(0, full ? 8 : 4).map(function (b) { return '<div><div class="lbl">' + b[0] + ' · ' + (C['n_' + b[1]] || (C[b[1]] || []).length) + '</div><div class="e-list">' + (C[b[1]] || []).slice(0, lim).map(function (r) { return row(r, b[2], b[3]); }).join('') + '</div></div>'; }).join('') + '</div>';
    return h;
  };
  /* the results calendar */
  M.events = function (n) {
    const EV = (E.lite && E.lite.events) || null;
    let h = E.sectionHead('Results this week', EV && EV.n ? (EV.n + ' names report within ten sessions · a results day is the biggest single-day mover there is — stops are not safe through it') : 'results dates arrive with the profiles rotation (Yahoo) over the first day');
    if (!EV || !(EV.rows || []).length) return h + '<div class="e-empty">no results date on file within ten days yet</div>';
    const rows = EV.rows.slice(0, n || 24);
    h += '<div class="e-list">' + rows.map(function (r) { const lt = E.lt(r.sym) || {}; return '<div class="e-li" onclick="E.openShare(\'' + F.esc(r.sym) + '\')"><div class="n">' + F.esc(r.nm) + '<small>' + F.esc(r.sym) + ' · ' + F.esc(r.sector || '') + (r.fno ? ' · F&O' : '') + '</small></div><div><span class="e-word ' + (r.days <= 0 ? 'avoid' : r.days <= 2 ? 'sell' : 'hold') + '">' + (r.days < 0 ? 'REPORTED' : r.days === 0 ? 'TODAY' : r.days === 1 ? 'TOMORROW' : 'IN ' + r.days + ' SESSIONS') + '</span>' + (lt.ss ? ' ' + F.word(lt.ss) : '') + '</div><div class="px"><span data-live-px="' + F.esc(r.sym) + '">' + F.inr(L.px(r.sym)) + '</span><small class="' + F.tone(L.d1(r.sym)) + '" data-live-d="' + F.esc(r.sym) + '">' + F.pct(L.d1(r.sym), 2) + '</small></div></div>'; }).join('') + '</div>';
    return h;
  };
  /* a badge for a share page / card: results within 3 sessions */
  M.badge = function (sym) { try { const EV = (E.lite && E.lite.events) || {}; const r = (EV.rows || []).find(function (x) { return x.sym === sym; }); if (!r) return ''; return '<span class="e-word avoid" title="a results day moves more than any stop allows for">' + (r.days < 0 ? 'REPORTED YESTERDAY' : r.days === 0 ? 'RESULTS TODAY' : r.days === 1 ? 'RESULTS TOMORROW' : 'RESULTS IN ' + r.days + ' SESSIONS') + '</span>'; } catch (e) { return ''; } };
})(window.E);
