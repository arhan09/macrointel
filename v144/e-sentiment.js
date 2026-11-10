/* ═══ v149 · SENTIMENT, MEASURED — the market's mood on ten counted things, what reads like today's meant next, the crowd on a
   name, regime × mood, the ledger of every graded call, and why believe this. engine.json carries sentiment / crowd / regsent;
   ledger.json carries every row. ═══ */
(function (E) {
  const F = E.f, L = E.live;

  /* ── the gauge ── */
  const S = E.sent = {};
  S.get = function () { return (E.lite && E.lite.sentiment) || null; };
  S.cls = function (w) { return w === 'EXTREME FEAR' ? 'sell' : w === 'FEAR' ? 'avoid' : w === 'NEUTRAL' ? 'hold' : w === 'GREED' ? 'acc' : 'buy'; };
  S.gauge = function (v, word, small) {
    const x = Math.max(0, Math.min(100, v == null ? 50 : v));
    return '<div class="e-gauge' + (small ? ' sm' : '') + '"><div class="bar"><i style="left:' + x + '%"></i></div><div class="lab"><span>fear</span><span>neutral</span><span>greed</span></div></div>';
  };
  S.mountMenu = function () { try { const m = document.querySelector('.e-more-menu'); if (!m || m.querySelector('[data-why]') || Array.from(m.querySelectorAll('button')).some(function (b) { return /Why believe/.test(b.textContent); })) return; const ref = Array.from(m.querySelectorAll('button')).find(function (b) { return /Records/.test(b.textContent); }); const b = document.createElement('button'); b.setAttribute('data-why', '1'); b.textContent = '🛡 Why believe this · the record'; b.onclick = function () { E.go('micro', 'why'); }; if (ref) m.insertBefore(b, ref); else m.appendChild(b); } catch (e) { } };
  S.card = function () {
    const s = S.get();
    let h = '<div class="cd e-sentcard" onclick="E.go(\'macro\',\'sentiment\')" style="cursor:pointer">';
    if (!s || s.value == null) return h + '<div class="lbl">The market\'s mood</div><div class="e-empty">the sentiment read arrives with the first v149 pass</div></div>';
    const nf = (s.now || {})['4w'];
    h += '<div class="e-between" style="gap:12px;flex-wrap:wrap"><div><div class="lbl">The market\'s mood · measured, not vibed</div><div class="e-row" style="gap:10px;margin-top:4px"><span class="big">' + s.value + '</span><span class="e-word ' + S.cls(s.word) + ' mid">' + F.esc(s.word) + '</span><span style="font-size:12px;color:var(--dim)">' + (s.n_components || 0) + ' of 10 reads</span></div></div><div style="flex:1;min-width:220px;max-width:420px">' + S.gauge(s.value, s.word, true) + '</div></div>';
    h += '<div style="font-size:13px;color:var(--tx);line-height:1.55;margin-top:8px">' + F.esc(s.sentence || '') + '</div>';
    if (nf) h += '<div class="e-row" style="margin-top:8px;gap:8px;flex-wrap:wrap"><span class="e-tag">reads like today\'s: next 4 weeks ' + F.pct(nf.avg, 1) + ' avg · up ' + nf.hit + '% of the time · n ' + nf.n + '</span><span class="act">the components, the history, the table →</span></div>';
    return h + '</div>';
  };
  S.components = function (s) {
    return '<div class="e-comps">' + (s.components || []).map(function (c) {
      const v = c.value; const on = v != null;
      return '<div class="e-comp' + (on ? '' : ' off') + '"><div class="n">' + F.esc(c.label) + '</div><div class="b"><div class="t"><i style="width:' + (on ? v : 0) + '%"></i></div></div><div class="v ' + (on ? S.cls(c.read) : '') + '">' + (on ? v : '—') + '</div><div class="d">' + F.esc(c.detail || '') + '</div></div>';
    }).join('') + '</div>';
  };
  S.table = function (s) {
    const F4 = (s.forward || {})['4w'] || {}, F13 = (s.forward || {})['13w'] || {}; const base = (s.forward || {}).base || {};
    const rows = ['EXTREME FEAR', 'FEAR', 'NEUTRAL', 'GREED', 'EXTREME GREED'].filter(function (b) { return F4[b] || F13[b]; });
    if (!rows.length) return '';
    let h = '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>the read was</th><th style="text-align:right">weeks</th><th style="text-align:right">next 4 weeks · avg</th><th style="text-align:right">up</th><th style="text-align:right">worst</th><th style="text-align:right">next 13 weeks · avg</th><th style="text-align:right">up</th></tr></thead><tbody>';
    rows.forEach(function (b) { const a = F4[b] || {}, c = F13[b] || {}; const cur = s.word === b; h += '<tr' + (cur ? ' style="background:rgba(255,255,255,.04)"' : '') + '><td><span class="e-word ' + S.cls(b) + '" style="font-size:10.5px;padding:2px 7px">' + b + '</span>' + (cur ? ' <small style="color:var(--dim)">← now</small>' : '') + '</td><td style="text-align:right">' + (a.n || c.n || '—') + '</td><td style="text-align:right"><b class="' + F.tone(a.avg) + '">' + F.pct(a.avg, 1) + '</b></td><td style="text-align:right">' + (a.hit != null ? a.hit + '%' : '—') + '</td><td style="text-align:right;color:var(--dim)">' + F.pct(a.worst, 1) + '</td><td style="text-align:right"><b class="' + F.tone(c.avg) + '">' + F.pct(c.avg, 1) + '</b></td><td style="text-align:right">' + (c.hit != null ? c.hit + '%' : '—') + '</td></tr>'; });
    if (base['4w']) h += '<tr><td style="color:var(--dim)">every week since 2014</td><td style="text-align:right">' + base['4w'].n + '</td><td style="text-align:right">' + F.pct(base['4w'].avg, 1) + '</td><td style="text-align:right">' + base['4w'].hit + '%</td><td></td><td style="text-align:right">' + F.pct((base['13w'] || {}).avg, 1) + '</td><td style="text-align:right">' + ((base['13w'] || {}).hit != null ? base['13w'].hit + '%' : '—') + '</td></tr>';
    return h + '</tbody></table></div>';
  };
  S.chart = function (id, s) {
    try {
      const cv = document.getElementById(id); if (!cv || !(s.hist || []).length) return;
      const dpr = window.devicePixelRatio || 1; const W = cv.clientWidth || 800, H = 170; cv.width = W * dpr; cv.height = H * dpr; const g = cv.getContext('2d'); g.scale(dpr, dpr);
      const pad = { l: 34, r: 10, t: 10, b: 22 }; const w = W - pad.l - pad.r, h = H - pad.t - pad.b;
      const pts = s.hist; const n = pts.length;
      const y = function (v) { return pad.t + h - (Math.max(0, Math.min(100, v)) / 100) * h; }; const x = function (i) { return pad.l + (i / Math.max(1, n - 1)) * w; };
      /* bands */
      const bands = [[0, 20, 'rgba(255,92,92,.10)'], [20, 40, 'rgba(255,138,76,.07)'], [60, 80, 'rgba(47,210,125,.06)'], [80, 100, 'rgba(47,210,125,.12)']];
      bands.forEach(function (b) { g.fillStyle = b[2]; g.fillRect(pad.l, y(b[1]), w, y(b[0]) - y(b[1])); });
      g.strokeStyle = 'rgba(255,255,255,.08)'; g.lineWidth = 1; [20, 40, 60, 80].forEach(function (v) { g.beginPath(); g.moveTo(pad.l, y(v)); g.lineTo(pad.l + w, y(v)); g.stroke(); });
      g.fillStyle = 'rgba(255,255,255,.45)'; g.font = '10px IBM Plex Mono'; g.textAlign = 'right'; [0, 20, 40, 60, 80, 100].forEach(function (v) { g.fillText(String(v), pad.l - 6, y(v) + 3); });
      /* years */
      g.textAlign = 'center'; let lastY = null; pts.forEach(function (p, i) { const yr = p[0].slice(0, 4); if (yr !== lastY) { lastY = yr; if (i > 0) { g.fillStyle = 'rgba(255,255,255,.35)'; g.fillText(yr, x(i), H - 6); g.strokeStyle = 'rgba(255,255,255,.05)'; g.beginPath(); g.moveTo(x(i), pad.t); g.lineTo(x(i), pad.t + h); g.stroke(); } } });
      /* the line */
      g.strokeStyle = '#e8e8ef'; g.lineWidth = 1.4; g.beginPath(); pts.forEach(function (p, i) { if (p[1] == null) return; const px = x(i), py = y(p[1]); if (i === 0) g.moveTo(px, py); else g.lineTo(px, py); }); g.stroke();
      const last = pts[n - 1]; g.fillStyle = last[1] >= 60 ? '#2fd27d' : last[1] < 40 ? '#ff5c5c' : '#ffc14d'; g.beginPath(); g.arc(x(n - 1), y(last[1]), 4, 0, Math.PI * 2); g.fill();
    } catch (e) { }
  };
  S.regsent = function () {
    const r = (E.lite && E.lite.regsent) || null; if (!r || !r.n) return '';
    let h = E.sectionHead('Regime × mood', 'the Nifty\'s next four weeks after reads in the <b>' + F.esc(r.bucket || '') + '</b> bucket while the regime was <b>' + F.esc(r.regime || '') + '</b> — and which industries did best in those weeks (since 2014)');
    const nf = r.nifty || {}, ro = r.regime_only || {};
    h += '<div class="e-record"><div class="e-stat"><div class="k">' + F.esc(r.regime) + ' × ' + F.esc(r.bucket) + ' · the Nifty</div><div class="v ' + F.tone(nf.avg) + '">' + F.pct(nf.avg, 1) + '</div><div class="s">next four weeks, ' + nf.n + ' such weeks · up ' + nf.hit + '% · worst ' + F.pct(nf.worst, 1) + ' · best ' + F.pct(nf.best, 1) + '</div></div>' + (ro.n ? '<div class="e-stat"><div class="k">' + F.esc(r.regime) + ' alone</div><div class="v ' + F.tone(ro.avg) + '">' + F.pct(ro.avg, 1) + '</div><div class="s">' + ro.n + ' weeks · up ' + ro.hit + '% — the mood adds ' + F.sgn((nf.avg || 0) - (ro.avg || 0), 1) + ' pts to the regime\'s own read</div></div>' : '') + '</div>';
    const rows = r.rows || [];
    if (rows.length) {
      const top = rows.slice(0, 6), bot = rows.slice(-6).reverse();
      const li = function (x) { return '<div class="e-li" onclick="E.industry.open(\'' + F.esc(x.sector) + '\')"><div class="n">' + F.esc(x.sector) + '<small>' + x.members + ' members · ' + x.n + ' such weeks</small></div><div><b class="' + F.tone(x.avg) + ' e-mono">' + F.pct(x.avg, 1) + '</b></div><div class="px"><small>up ' + x.hit + '%</small></div></div>'; };
      h += '<div class="e-grid e-g2"><div><div class="lbl">Industries that did best in such weeks</div><div class="e-list">' + top.map(li).join('') + '</div></div><div><div class="lbl">…and worst</div><div class="e-list">' + bot.map(li).join('') + '</div></div></div>';
    }
    /* the whole table: four regimes by five moods */
    const T = r.table || {}; const regs = ['Goldilocks', 'Reflation', 'Stagflation', 'Disinflation'], moods = ['EXTREME FEAR', 'FEAR', 'NEUTRAL', 'GREED', 'EXTREME GREED'];
    if (Object.keys(T).length) {
      h += '<div class="cd" style="padding:0;overflow-x:auto;margin-top:10px"><table class="tbl" style="width:100%"><thead><tr><th>Nifty, next 4 weeks</th>' + moods.map(function (m) { return '<th style="text-align:right">' + m.toLowerCase() + '</th>'; }).join('') + '</tr></thead><tbody>' + regs.map(function (rg) { return '<tr><td>' + rg + (rg === r.regime ? ' <small style="color:var(--dim)">← now</small>' : '') + '</td>' + moods.map(function (m) { const c = T[rg + '|' + m]; const cur = rg === r.regime && m === r.bucket; return '<td style="text-align:right' + (cur ? ';background:rgba(255,255,255,.05)' : '') + '">' + (c ? '<b class="' + F.tone(c.avg) + '">' + F.pct(c.avg, 1) + '</b><div style="font-size:10.5px;color:var(--mut)">' + c.n + ' wks · up ' + c.hit + '%</div>' : '<span style="color:var(--mut)">—</span>') + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
    }
    h += '<div class="note">' + F.esc(r.how || '') + '</div>';
    return h;
  };
  S.crowdLists = function () {
    const c = (E.lite && E.lite.crowd) || null; if (!c || !c.n) return '';
    let h = E.sectionHead('The crowd', 'seven measured reads per name — the crowd is in or out: ' + Object.keys(c.counts || {}).map(function (k) { return c.counts[k] + ' ' + k.toLowerCase(); }).join(', '));
    const li = function (x) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(x.sym) + '\')"><div class="n">' + F.esc(x.nm) + '<small>' + F.esc(x.sym) + ' · ' + F.esc(x.sector || '') + ' · ' + (x.why || []).slice(0, 3).map(F.esc).join(' · ') + '</small></div><div><span class="e-word ' + (x.word === 'CROWDED' ? 'avoid' : 'acc') + '">' + x.word + ' ' + (x.score > 0 ? '+' : '') + x.score + '</span></div><div class="px"><span data-live-px="' + F.esc(x.sym) + '">' + F.inr(L.px(x.sym) || x.px) + '</span><small class="' + F.tone(L.d1(x.sym)) + '" data-live-d="' + F.esc(x.sym) + '">' + F.pct(L.d1(x.sym), 2) + '</small></div></div>'; };
    h += '<div class="e-grid e-g2"><div><div class="lbl">Crowded — everyone is already in</div><div class="e-list">' + ((c.crowded || []).map(li).join('') || '<div class="e-empty">no name reads crowded today</div>') + '</div></div><div><div class="lbl">Hated — the crowd has left</div><div class="e-list">' + ((c.hated || []).map(li).join('') || '<div class="e-empty">no name reads hated today</div>') + '</div></div></div>';
    h += '<div class="note">' + F.esc(c.how || '') + '</div>';
    return h;
  };
  S.section = function () {
    const s = S.get();
    let h = '<div id="e-sentiment"></div>' + E.sectionHead('Sentiment, measured', s && s.value != null ? ('the market\'s mood from ten counted things — ' + (s.n_components || 0) + ' answered this pass — and what reads like today\'s have meant since 2014') : 'arrives with the first v149 pass');
    if (!s || s.value == null) return h + '<div class="e-empty">' + F.esc((s && s.error) || 'no read yet') + '</div>';
    h += '<div class="cd"><div class="e-between" style="gap:14px;flex-wrap:wrap"><div><div class="e-row" style="gap:10px"><span class="big" style="font-size:34px">' + s.value + '</span><span class="e-word ' + S.cls(s.word) + ' mid">' + F.esc(s.word) + '</span></div><div style="font-size:12px;color:var(--dim);margin-top:4px">the core five (with a history since 2014) read ' + (s.core_now != null ? s.core_now : '—') + '</div></div><div style="flex:1;min-width:260px;max-width:520px">' + S.gauge(s.value, s.word) + '</div></div><div style="font-size:13px;color:var(--tx);line-height:1.55;margin-top:10px">' + F.esc(s.sentence || '') + '</div></div>';
    h += '<div class="lbl" style="margin-top:12px">The ten reads</div>' + S.components(s);
    h += '<div class="lbl" style="margin-top:12px">The core read since 2014</div><div class="cd" style="padding:8px"><canvas id="e-sent-chart" style="width:100%;height:170px;display:block"></canvas></div>';
    h += '<div class="lbl" style="margin-top:12px">What a read like this has meant — the Nifty afterwards</div>' + S.table(s);
    h += '<div class="note">' + F.esc(s.how || '') + '</div>';
    try { h += S.regsent(); } catch (e) { }
    try { h += S.crowdLists(); } catch (e) { }
    setTimeout(function () { S.chart('e-sent-chart', s); }, 50);
    return h;
  };

  /* ── the crowd on a name (the research page) ── */
  E.crowdLine = function (sym, r) {
    let c = r && r.crowd; const lite = (E.lite && E.lite.crowd && E.lite.crowd.by && E.lite.crowd.by[sym]) || null;
    if (!c && lite) c = { score: lite[0], word: lite[1], parts: [] };
    if (!c) return '';
    const cls = c.word === 'CROWDED' ? 'avoid' : c.word === 'WARM' ? 'acc' : c.word === 'HATED' ? 'sell' : c.word === 'COLD' ? 'hold' : 'hold';
    const what = c.word === 'CROWDED' ? 'everyone is already in — a crowded name needs new buyers to go on, and unwinds hard when they do not come' : c.word === 'HATED' ? 'the crowd has left — with the numbers behind it, the sellers it was going to lose are gone; without them, a value trap' : c.word === 'WARM' ? 'the crowd leans in, not yet crowded' : c.word === 'COLD' ? 'the crowd leans out' : 'the crowd has no strong view';
    return '<div class="e-line"><b>The crowd on it:</b> <span class="e-word ' + cls + '" style="font-size:10.5px;padding:1px 7px">' + F.esc(c.word) + ' ' + (c.score > 0 ? '+' : '') + c.score + '</span> ' + what + (c.parts && c.parts.length ? ' — ' + c.parts.map(function (p) { return F.esc(p.t); }).join('; ') : '') + '.</div>';
  };

  /* ── the ledger: every call, graded ── */
  const LG = E.ledger = { data: null, _p: null, kind: 'all', only: 'all' };
  LG.load = function () { if (LG._p) return LG._p; LG._p = fetch(E.url('ledger.json'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { LG.data = j; return j; }).catch(function () { return null; }); return LG._p; };
  LG.LABEL = { intraday: 'Intraday · 1 session', fno: 'F&O · 10 sessions', today_buys: "Today's buys · 10 sessions", short_buy: 'Short-term BUY · 20 sessions', short_sell: 'Short-term SELL · 20 sessions', long: 'Long · 60 sessions', pairs: 'Pairs · 10 sessions', macro: 'Macro call · 5 sessions', movers: 'Likely movers · next session', calls_short: 'The short call · 20 sessions', calls_long: 'The long call · 60 sessions', street: 'The Street vs the engine · 60 sessions' };
  LG.section = function () {
    let h = '<div id="e-ledger"></div>' + E.sectionHead('Every call, graded', 'the ledger behind the strip: each call the engine froze, at the price it froze it, and what happened — nothing dropped, a miss stays a miss');
    h += '<div id="e-ledger-body"><div class="e-empty">loading the ledger…</div></div>';
    LG.load().then(function () { LG.render(); });
    return h;
  };
  LG.render = function () {
    const el = document.getElementById('e-ledger-body'); if (!el) return;
    const d = LG.data; if (!d || !(d.rows || []).length) { el.innerHTML = '<div class="e-empty">the ledger fills as calls reach their horizons — the first rows print a session after the first v149 pass</div>'; return; }
    const kinds = ['all'].concat(d.kinds || []);
    let rows = d.rows.filter(function (r) { return (LG.kind === 'all' || r.kind === LG.kind) && (LG.only === 'all' || (LG.only === 'hit' ? (r.ret || 0) > 0 : (r.ret || 0) <= 0)); });
    const n = rows.length; const hits = rows.filter(function (r) { return (r.ret || 0) > 0; }).length; const avg = n ? rows.reduce(function (a, r) { return a + (r.ret || 0); }, 0) / n : null; const ex = rows.filter(function (r) { return r.excess != null; }); const avgx = ex.length ? ex.reduce(function (a, r) { return a + r.excess; }, 0) / ex.length : null;
    let h = '<div class="e-row" style="gap:8px;flex-wrap:wrap;margin-bottom:10px">' + kinds.map(function (k) { return '<span class="e-chip' + (LG.kind === k ? ' a' : '') + '" onclick="E.ledger.kind=\'' + k + '\';E.ledger.render()">' + (k === 'all' ? 'all' : F.esc(LG.LABEL[k] || k)) + '</span>'; }).join('') + '<span style="flex:1"></span>' + ['all', 'hit', 'miss'].map(function (k) { return '<span class="e-chip' + (LG.only === k ? ' a' : '') + '" onclick="E.ledger.only=\'' + k + '\';E.ledger.render()">' + k + '</span>'; }).join('') + '</div>';
    h += '<div class="e-record"><div class="e-stat"><div class="k">Rows</div><div class="v">' + n + '</div><div class="s">of ' + d.n + ' graded · as of ' + F.esc(d.asof || '') + '</div></div><div class="e-stat"><div class="k">In the money</div><div class="v">' + (n ? Math.round(100 * hits / n) + '%' : '—') + '</div><div class="s">' + hits + ' of ' + n + '</div></div><div class="e-stat"><div class="k">Average</div><div class="v ' + F.tone(avg) + '">' + F.pct(avg, 2) + '</div><div class="s">per call, at its horizon</div></div><div class="e-stat"><div class="k">Against the Nifty</div><div class="v ' + F.tone(avgx) + '">' + F.pct(avgx, 2) + '</div><div class="s">average excess, where scored</div></div></div>';
    rows = rows.slice(0, 400);
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>date</th><th>kind</th><th>name</th><th>side</th><th style="text-align:right">at</th><th style="text-align:right">then</th><th style="text-align:right">return</th><th style="text-align:right">vs Nifty</th><th>note</th></tr></thead><tbody>' + rows.map(function (r) {
      const nm = r.nm || r.sym || (r.a ? r.a + ' / ' + r.b : '') || '—';
      return '<tr' + (r.sym ? ' style="cursor:pointer" onclick="E.openShare(\'' + F.esc(r.sym) + '\')"' : '') + '><td class="e-mono" style="color:var(--dim)">' + F.esc(r.date || '') + '</td><td style="font-size:11px;color:var(--dim)">' + F.esc((LG.LABEL[r.kind] || r.kind || '').split(' · ')[0]) + '</td><td><b style="color:#fff">' + F.esc(nm) + '</b></td><td>' + (r.side ? '<span class="e-word ' + F.cls(r.side) + '" style="font-size:10px;padding:1px 6px">' + F.esc(String(r.side).slice(0, 24)) + '</span>' : '') + '</td><td style="text-align:right" class="e-mono">' + (r.px != null ? F.inr(r.px) : '') + '</td><td style="text-align:right" class="e-mono">' + (r.px1 != null ? F.inr(r.px1) : '') + '</td><td style="text-align:right"><b class="' + F.tone(r.ret) + '">' + F.pct(r.ret, 2) + '</b></td><td style="text-align:right" class="' + F.tone(r.excess) + '">' + (r.excess != null ? F.pct(r.excess, 2) : '') + '</td><td style="font-size:11px;color:var(--mut)">' + F.esc(r.how || '') + (r.tgt_hit === true ? ' · target first' : r.stopped === true ? ' · stopped first' : '') + (r.moved != null ? (r.moved ? ' · moved ≥1.5σ' : ' · did not move') : '') + '</td></tr>';
    }).join('') + '</tbody></table></div>' + (n > 400 ? '<div class="note">the first 400 of ' + n + ' rows</div>' : '') + '<div class="note">' + F.esc(d.how || '') + '</div>';
    el.innerHTML = h;
  };

  /* ── why believe this ── */
  E.why = {};
  E.recordVerdict = function () {
    const R = (E.lite && E.lite.record) || {}; const good = [], bad = [];
    const L2 = { fno: 'the F&O setups', today_buys: "today's buys", short_buy: 'the short-term BUYs', long: 'the twelve-month ACCUMULATEs', intraday: 'the intraday reads', pairs: 'the pairs', macro: 'the macro call', calls_short: 'the short calls of the day', calls_long: 'the long calls of the day' };
    Object.keys(L2).forEach(function (k) { const r = R[k]; if (!r || !r.n || r.n < 10) return; const ok = (k === 'macro' ? (r.call_hit || 0) >= 55 : ((r.hit || 0) >= 55 && (r.avg_excess == null || r.avg_excess >= -1))); (ok ? good : bad).push(L2[k] + ' (' + (k === 'macro' ? r.call_hit : r.hit) + '% on ' + r.n + (r.avg_excess != null ? ', ' + F.pct(r.avg_excess, 1) + ' vs the Nifty' : '') + ')'); });
    const mv = R.movers; if (mv && mv.n >= 30) (mv.hit >= 30 ? good : bad).push('the movers model (' + mv.hit + '% of ' + mv.n + ' moved ≥1.5σ against a ~16% base rate)');
    if (!good.length && !bad.length) return '';
    return '<div class="e-line"><b>Read it straight:</b> ' + (good.length ? 'what is working — ' + good.join('; ') + '. ' : '') + (bad.length ? 'What is not — ' + bad.join('; ') + '. ' : '') + 'The strip updates every pass; nothing is dropped.</div>';
  };
  E.why.section = function () {
    let h = '<div id="e-why"></div>' + E.sectionHead('Why believe this', 'a channel gives you a call and never tells you how its last hundred went — this page does, every pass');
    h += '<div class="e-grid e-g2"><div class="cd"><div class="lbl">What is different here</div><ul class="e-ul">' +
      '<li><b>Every call is frozen and graded in public.</b> The price it was made at, the price at its horizon, the return, the excess over the Nifty — the ledger below has every row, misses included. A tip you cannot grade is an opinion.</li>' +
      '<li><b>Macro first, then the share.</b> The regime, each share\'s DNA (how it has moved with the Nifty, the rupee, Brent, rates and the VIX for three years), its record in this regime over ten, its industry\'s wind this month — and only then the verdict.</li>' +
      '<li><b>The mood is measured, not vibed.</b> Ten counted things — breadth, momentum, the VIX, mid & small against large, gold, positioning in the chain, headlines, highs against lows — and what reads like today\'s have meant since 2014.</li>' +
      '<li><b>Expectations are capped.</b> No path on this page expects more than a Sharpe-1 bet; P(higher) cannot read 100%. A target is a line to trade against, not a forecast.</li>' +
      '<li><b>Evidence is written out.</b> The calls of the day list every support and every objection — the company\'s numbers, the Street, the news, the delivery, the crowd — and are never made against the week\'s news, into results, or on a name the crowd is already in.</li>' +
      '<li><b>The model reads the micro too.</b> ROE, margins, growth, leverage, valuation against the sector, promoter holding — a quarter of the twelve-month score.</li></ul></div>' +
      '<div class="cd"><div class="lbl">What this page does not do</div><ul class="e-ul">' +
      '<li>No "multibagger" lists, no target without a stop, no call without a horizon.</li>' +
      '<li>No number from a feed it cannot check: prices are Yahoo\'s and NSE\'s, fundamentals are Yahoo\'s profiles, delivery is NSE\'s file, headlines are Google News\' — each named where it is used.</li>' +
      '<li>No feature learns on the news. Headlines are evidence behind a call and context on a move; a wire\'s mood cannot move a verdict.</li>' +
      '<li>No quiet edits to the record. A frozen file is written once a day; the grading runs on the next passes; what was wrong stays wrong on the page.</li>' +
      '<li>It is a personal research desk — model output, not advice; prices may be delayed; F&O can lose all of it.</li></ul></div></div>';
    h += '<div style="margin-top:12px">' + (E.lite ? E.recordVerdict() : '') + '</div>';
    return h;
  };
})(window.E);
