/* ═══ v148 · THE BELL — the day's major updates · THE CALLS OF THE DAY · WHY IT MOVED · THE STREET · THE NEWS · DELIVERY ═══
   engine.json carries brief (the items), calls (one LONG call for twelve months, one SHORT call for one month, each with its
   supports and objections), attr (every big move split into market / sector / own), street (the analysts against the engine).
   news.json carries the headlines behind them. The bell keeps what you have seen in this browser. */
(function (E) {
  const F = E.f, L = E.live;

  /* ── the bell and the drawer ── */
  const B = E.brief = { open: false, seen: null, KEY: 'mi_brief_seen' };
  B.load = function () { if (B.seen) return; try { B.seen = new Set(JSON.parse(localStorage.getItem(B.KEY) || '[]')); } catch (e) { B.seen = new Set(); } };
  B.save = function () { try { localStorage.setItem(B.KEY, JSON.stringify(Array.from(B.seen).slice(-600))); } catch (e) { } };
  B.data = function () { return (E.lite && E.lite.brief) || null; };
  B.items = function () { return (B.data() || {}).items || []; };
  B.unread = function () { B.load(); return B.items().filter(function (i) { return !B.seen.has(i.id); }).length; };
  B.badge = function () { try { const el = document.getElementById('e-bell-n'); if (!el) return; const n = B.unread(); el.textContent = n ? (n > 9 ? '9+' : String(n)) : ''; el.style.display = n ? 'inline-flex' : 'none'; const bell = document.getElementById('e-bell'); if (bell) bell.classList.toggle('has', n > 0); } catch (e) { } };
  B.toggle = function () { if (B.open) B.close(); else B.show(); };
  B.show = function () { let d = document.getElementById('e-drawer'); if (!d) { d = document.createElement('div'); d.id = 'e-drawer'; d.className = 'e-drawer'; document.body.appendChild(d); } B.render(); d.scrollTop = 0; d.classList.add('open'); B.open = true; document.body.classList.add('e-drawer-open'); };
  B.close = function () { const d = document.getElementById('e-drawer'); if (d) d.classList.remove('open'); B.open = false; document.body.classList.remove('e-drawer-open'); };
  B.markAll = function () { B.load(); B.items().forEach(function (i) { B.seen.add(i.id); }); B.save(); B.badge(); B.render(); };
  B.pick = function (id, sym, tab, sub) { B.load(); if (id) { B.seen.add(id); B.save(); B.badge(); } B.close(); try { if (sym) E.openShare(sym); else if (tab === 'home' && sub === 'calls') { E.go('home'); setTimeout(function () { const c = document.getElementById('e-calls'); if (c) c.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 80); } else if (tab) E.go(tab, sub || undefined); } catch (e) { } };
  B.ICON = { call: '📣', market: '📊', regime: '🧭', flows: '🌊', changes: '🔁', movers: '⚡', results: '📅', moved: '❓', record: '🧾', street: '🏛', alloc: '🗺', pairs: '⚖', news: '📰', pass: '⏱' };
  B.render = function () {
    const d = document.getElementById('e-drawer'); if (!d) return;
    B.load();
    const D = B.data(); const items = B.items();
    let h = '<div class="hd"><div><div class="t">Today\'s major updates</div><div class="s">' + (D ? ('as of the pass at ' + F.esc((D.at || '').slice(11)) + ' IST · ' + F.esc(D.asof || '')) : 'the brief arrives with the first v148 pass') + '</div></div><div class="e-row"><button class="e-btn" style="padding:6px 10px;font-size:12px" onclick="E.brief.markAll()">read all</button><button class="e-btn" style="padding:6px 10px;font-size:12px" onclick="E.brief.close()">✕</button></div></div>';
    if (!D) { h += '<div class="e-empty" style="margin:14px">engine.json has no brief yet — the bell fills with the first v148 pass</div>'; d.innerHTML = h; return; }
    /* the calls first */
    try { h += '<div class="e-dsec"><div class="lbl">The calls of the day</div>' + E.calls.section(false, true) + '</div>'; } catch (e) { }
    h += '<div class="e-dsec"><div class="lbl">Updates · ' + items.length + '</div><div class="e-bl">' + items.filter(function (i) { return i.k !== 'call'; }).map(function (i) {
      const seen = B.seen.has(i.id);
      return '<div class="e-bi' + (seen ? ' seen' : '') + '" onclick="E.brief.pick(\'' + i.id + '\',' + (i.sym ? '\'' + F.esc(i.sym) + '\'' : 'null') + ',' + (i.go ? '\'' + F.esc(i.go[0]) + '\',' + (i.go[1] ? '\'' + F.esc(i.go[1]) + '\'' : 'null') : 'null,null') + ')"><div class="ic">' + (B.ICON[i.k] || '•') + '</div><div><div class="t">' + F.esc(i.t) + '</div>' + (i.d ? '<div class="d">' + F.esc(i.d) + '</div>' : '') + '</div>' + (seen ? '' : '<i class="dot"></i>') + '</div>';
    }).join('') + '</div></div>';
    /* notifications */
    const nOn = B.notify.isOn();
    h += '<div class="e-dsec"><div class="lbl">Desktop notifications</div><div class="e-row" style="gap:10px;flex-wrap:wrap"><button class="e-btn' + (nOn ? ' p' : '') + '" style="padding:7px 12px;font-size:12.5px" onclick="E.brief.notify.toggle()">' + (nOn ? '🔔 On — a new pass pings this browser' : '🔕 Off — turn on') + '</button><span style="font-size:12px;color:var(--dim)">' + (B.notify.supported() ? 'while this page is open in a tab, each new pass raises a notification with the calls and the top updates (the browser asks once)' : 'this browser does not offer notifications') + '</span></div></div>';
    h += '<div class="note" style="margin:0 14px 14px">' + F.esc(D.how || '') + '</div>';
    d.innerHTML = h;
  };
  /* desktop notifications + the new-pass watcher */
  B.notify = { KEY: 'mi_notify', timer: null, last: null };
  B.notify.supported = function () { return typeof Notification !== 'undefined'; };
  B.notify.isOn = function () { try { return localStorage.getItem(B.notify.KEY) === '1' && B.notify.supported() && Notification.permission === 'granted'; } catch (e) { return false; } };
  B.notify.toggle = async function () {
    try {
      if (B.notify.isOn()) { localStorage.setItem(B.notify.KEY, '0'); B.render(); return; }
      if (!B.notify.supported()) return;
      let p = Notification.permission; if (p === 'default') p = await Notification.requestPermission();
      if (p === 'granted') { localStorage.setItem(B.notify.KEY, '1'); try { new Notification('MacroIntel', { body: 'Notifications are on. A new pass will ping here with the calls of the day.', silent: true }); } catch (e) { } }
      B.render();
    } catch (e) { }
  };
  B.notify.fire = function (lite) {
    try {
      if (!B.notify.isOn()) return;
      const c = (lite.calls || {}); const items = ((lite.brief || {}).items || []).filter(function (i) { return i.k !== 'call' && i.k !== 'pass'; }).slice(0, 3);
      const lines = []; if (c.long) lines.push('LONG · Buy ' + c.long.nm + ' → ₹' + F.inr(c.long.target).replace('₹', '') + ' in 12 months (' + c.long.conv + '/5)'); if (c.short) lines.push('SHORT · Buy ' + c.short.nm + ' → ₹' + F.inr(c.short.target).replace('₹', '') + ' in 1 month (' + c.short.conv + '/5)');
      items.forEach(function (i) { lines.push(i.t); });
      const n = new Notification('MacroIntel · new pass ' + F.esc(((lite.brief || {}).at || '').slice(11)) + ' IST', { body: lines.join('\n'), tag: 'mi-pass' });
      n.onclick = function () { try { window.focus(); B.show(); } catch (e) { } };
    } catch (e) { }
  };
  B.watch = function () {
    if (B.notify.timer) return;
    B.notify.last = (E.lite && E.lite.generated) || null;
    const check = async function () {
      try {
        const r = await fetch(E.url('engine.json'), { cache: 'no-store' }); if (!r.ok) return; const j = await r.json();
        if (j && j.generated && j.generated !== B.notify.last) {
          B.notify.last = j.generated; E.lite = j; B.badge(); B.notify.fire(j);
          B.toast('A new pass landed at ' + F.esc(((j.brief || {}).at || '').slice(11)) + ' IST — the page\'s numbers are refreshed; open the bell for the calls.');
          try { if (B.open) B.render(); } catch (e) { }
          try { if (E.tab === 'home' && E.home) E.home.render(); } catch (e) { }
        }
      } catch (e) { }
    };
    B.notify.timer = setInterval(check, 10 * 60 * 1000);
  };
  B.toast = function (msg) { try { let t = document.getElementById('e-toast'); if (!t) { t = document.createElement('div'); t.id = 'e-toast'; t.className = 'e-toast'; document.body.appendChild(t); } t.innerHTML = '<span>' + msg + '</span><button class="e-btn" style="padding:4px 9px;font-size:12px" onclick="E.brief.show();this.parentNode.classList.remove(\'show\')">open</button><button class="e-btn" style="padding:4px 9px;font-size:12px" onclick="this.parentNode.classList.remove(\'show\')">✕</button>'; t.classList.add('show'); setTimeout(function () { t.classList.remove('show'); }, 20000); } catch (e) { } };
  B.bellHtml = function () { return '<button class="e-bell" id="e-bell" title="today\'s major updates" onclick="E.brief.toggle()">🔔<span class="e-badge" id="e-bell-n" style="display:none"></span></button>'; };
  B.mount = function () { try { const nav = document.getElementById('e-nav'); if (!nav || document.getElementById('e-bell')) return; const sp = nav.querySelector('.sp'); const wrap = document.createElement('span'); wrap.innerHTML = B.bellHtml(); if (sp && sp.nextSibling) nav.insertBefore(wrap.firstChild, sp.nextSibling); else nav.appendChild(wrap.firstChild); B.badge(); } catch (e) { } };

  /* ── the calls of the day ── */
  const C = E.calls = {};
  C.get = function () { return (E.lite && E.lite.calls) || null; };
  C.dots = function (n) { n = Math.max(0, Math.min(5, n || 0)); return '<span class="e-dots" title="' + n + ' of 5 independent supports">' + '●'.repeat(n) + '<span>' + '●'.repeat(5 - n) + '</span></span>'; };
  C.card = function (c, kind, compact) {
    const label = kind === 'long' ? 'LONG · 12 months' : 'SHORT · 1 month';
    if (!c) {
      const K = C.get() || {}; const n = kind === 'long' ? K.n_long_tested : K.n_short_tested;
      return '<div class="e-call none"><div class="hd"><span class="k">' + label + '</span></div><div class="nm" style="color:var(--dim)">No ' + (kind === 'long' ? 'long' : 'short') + ' call today</div><div class="s">nothing stacked three independent supports without an objection' + (n ? ' (' + n + ' candidates tested)' : '') + ' — the desk waits rather than forces one</div></div>';
    }
    const px = L.px(c.sym) || c.px; const up = c.target && px ? (c.target / px - 1) * 100 : null;
    let h = '<div class="e-call ' + kind + (c.conv >= 5 ? ' top' : '') + '" onclick="E.openShare(\'' + F.esc(c.sym) + '\')">';
    h += '<div class="hd"><span class="k">' + label + '</span>' + C.dots(c.conv) + '<span class="cw ' + (c.conv >= 4 ? 'hi' : '') + '">' + F.esc(c.conv_word || '') + ' · ' + c.conv + '/5</span></div>';
    h += '<div class="nm"><span class="e-word buy mid">BUY</span> ' + F.esc(c.nm) + ' <small>' + F.esc(c.sym) + ' · ' + F.esc(c.sector || '') + (c.fno ? ' · F&O' : '') + '</small></div>';
    h += '<div class="plan"><div><div class="k">Now</div><div class="v" data-live-px="' + F.esc(c.sym) + '">' + F.inr(px) + '</div><div class="d ' + F.tone(L.d1(c.sym)) + '" data-live-d="' + F.esc(c.sym) + '">' + F.pct(L.d1(c.sym), 2) + '</div></div><div><div class="k">Target · ' + F.esc(c.label) + '</div><div class="v e-up">' + F.inr(c.target) + '</div><div class="d">' + (up != null ? F.pct(up, 1) : '') + '</div></div><div><div class="k">' + (kind === 'long' ? 'Exit below' : 'Stop') + '</div><div class="v e-dn">' + F.inr(c.stop) + '</div><div class="d">' + (c.stop && px ? F.pct((c.stop / px - 1) * 100, 1) : '') + '</div></div>' + (c.cone && c.cone.p_up != null ? '<div><div class="k">P(higher)</div><div class="v">' + c.cone.p_up + '%</div><div class="d">at ' + c.h + ' sessions</div></div>' : '') + '</div>';
    const sup = (c.supports || []).slice(0, compact ? 3 : 7), agn = (c.against || []).slice(0, compact ? 1 : 4);
    h += '<ul class="ev">' + sup.map(function (x) { return '<li class="y"><i>✓</i>' + F.esc(x.t) + '</li>'; }).join('') + agn.map(function (x) { return '<li class="n"><i>!</i>' + F.esc(x.t) + '</li>'; }).join('') + '</ul>';
    if (!compact && (c.news || []).length) h += '<div class="nw">' + c.news.map(function (x) { return '<a target="_blank" rel="noopener" href="' + F.esc(x.link || '#') + '" onclick="event.stopPropagation()">' + (x.tone > 0 ? '<b class="e-up">▲</b>' : x.tone < 0 ? '<b class="e-dn">▼</b>' : '<b style="color:var(--mut)">•</b>') + ' ' + F.esc(x.t) + ' <small>' + F.esc(x.src || '') + (x.age_d != null ? ' · ' + (x.age_d <= 1 ? 'today' : Math.round(x.age_d) + 'd ago') : '') + '</small></a>'; }).join('') + '</div>';
    h += '<div class="ft"><span>' + (kind === 'short' && c.size_pct != null ? 'size ' + c.size_pct + '% of capital' + (c.lots ? ' · ' + c.lots + ' lot' + (c.lots > 1 ? 's' : '') : '') : (kind === 'long' ? 'a holding, sized for a year — the exit is the line, not a day' : '')) + (c.gate ? ' · the gate is on: half size' : '') + '</span><span>frozen with the day · scored at ' + (kind === 'long' ? '60 sessions, and at 250 when the year is up' : c.h + ' sessions') + '</span></div>';
    return h + '</div>';
  };
  C.section = function (full, compact) {
    const K = C.get();
    let h = '';
    if (!compact) h += E.sectionHead('The calls of the day', K ? ('one long call for twelve months and one short call for one month — made only when the evidence stacks: the verdict, the company\'s numbers, the regime fit, the Street, the week\'s news, the delivery read, the engine\'s own record on the name · ' + F.esc(K.asof || '')) : 'the calls arrive with the first v148 pass', full ? '' : '<span class="act" onclick="E.go(\'micro\',\'records\')">the calls\' record →</span>');
    if (!K) return h + (compact ? '<div class="e-empty">no calls on the page yet</div>' : '');
    h += '<div class="e-grid e-g2" id="e-calls">' + C.card(K.long, 'long', compact) + C.card(K.short, 'short', compact) + '</div>';
    if (full) {
      const also = (K.long_also || []).map(function (c) { return C.mini(c, 'long'); }).concat((K.short_also || []).map(function (c) { return C.mini(c, 'short'); }));
      if (also.length) h += '<div class="lbl" style="margin-top:12px">Also considered</div><div class="e-list">' + also.join('') + '</div>';
      h += '<div class="note">' + F.esc(K.how || '') + '</div>';
      try { h += C.record(); } catch (e) { }
    }
    return h;
  };
  C.mini = function (c, kind) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(c.sym) + '\')"><div class="n">' + F.esc(c.nm) + '<small>' + F.esc(c.sym) + ' · ' + (kind === 'long' ? '12 months' : '1 month') + ' · target ' + F.inr(c.target) + ' · ' + F.esc(c.conv_word) + ' ' + c.conv + '/5</small></div><div>' + C.dots(c.conv) + '</div><div class="px"><span data-live-px="' + F.esc(c.sym) + '">' + F.inr(L.px(c.sym) || c.px) + '</span><small class="' + F.tone(L.d1(c.sym)) + '" data-live-d="' + F.esc(c.sym) + '">' + F.pct(L.d1(c.sym), 2) + '</small></div></div>'; };
  C.record = function () {
    const R = (E.lite && E.lite.record) || {}; const a = R.calls_short || {}, b = R.calls_long || {};
    let h = E.sectionHead('The calls\' record', 'the short call at twenty sessions (did it reach the target before the stop?), the long call at sixty sessions and, when the year is up, at 250');
    h += '<div class="e-record">' + [['Short calls · 20 sessions', a], ['Long calls · 60 sessions → 250', b]].map(function (x) { const r = x[1]; return '<div class="e-stat"><div class="k">' + x[0] + '</div><div class="v">' + (r.n ? r.hit + '%' : '—') + '</div><div class="s">' + (r.n ? ('in the money on ' + r.n + ' scored · avg ' + F.pct(r.avg, 2) + (r.avg_excess != null ? ' · vs Nifty ' + F.pct(r.avg_excess, 2) : '') + (r.tgt_hit != null ? ' · target first ' + r.tgt_hit + '% · stopped first ' + r.stopped + '%' : '') + (r.n_final ? ' · ' + r.n_final + ' at the full year' : '')) : 'no call has reached its horizon yet — scoring starts automatically') + '</div></div>'; }).join('') + '</div>';
    return h;
  };

  /* ── why it moved ── */
  const A = E.attr = {};
  A.get = function () { return (E.lite && E.lite.attr) || null; };
  A.of = function (sym) { const a = A.get(); return a && a.by && a.by[sym] || null; };
  A.kindCls = function (k) { return k === 'STOCK-SPECIFIC' ? 'avoid' : k === 'SECTOR' ? 'acc' : k === 'ADJUSTMENT?' ? 'sell' : 'hold'; };
  A.bar = function (r) {
    const a = Math.abs(r.d1) || 1e-9; const parts = [['mkt', r.mkt, 'var(--blu)', 'market'], ['sec', r.sec, 'var(--vio, #9b8cff)', 'sector'], ['own', r.own, 'var(--amb)', 'own']];
    return '<div class="e-abar" title="market ' + F.pct(r.mkt, 1) + ' · sector ' + F.pct(r.sec, 1) + ' · own ' + F.pct(r.own, 1) + '">' + parts.map(function (p) { const w = Math.min(100, Math.abs(p[1] || 0) / a * 100); return w > 1 ? '<i style="width:' + w + '%;background:' + p[2] + '" title="' + p[3] + ' ' + F.pct(p[1], 1) + '"></i>' : ''; }).join('') + '</div>';
  };
  A.tile = function (r) {
    return '<div class="e-amv" onclick="E.openShare(\'' + F.esc(r.sym) + '\')"><div class="e-between"><div class="n">' + F.esc(r.nm) + '<small>' + F.esc(r.sym) + ' · ' + F.esc(r.sector || '') + '</small></div><div class="d ' + F.tone(r.d1) + '">' + F.pct(r.d1, 1) + '<small>' + F.n(r.z, 1) + 'σ</small></div></div>' + A.bar(r) + '<div class="e-row" style="margin-top:6px;gap:6px"><span class="e-word ' + A.kindCls(r.kind) + '" style="font-size:10.5px;padding:2px 7px">' + F.esc(r.kind) + '</span>' + (r.dlv ? '<span class="e-word hold" style="font-size:10.5px;padding:2px 7px" title="' + F.esc(r.dlv_note || '') + '">' + F.esc(r.dlv) + '</span>' : '') + '<span style="font-size:11px;color:var(--dim)">market ' + F.pct(r.mkt, 1) + ' · sector ' + F.pct(r.sec, 1) + ' · own ' + F.pct(r.own, 1) + '</span></div>' + ((r.news || []).length ? '<div class="nw">“' + F.esc(r.news[0].t) + '” <small>' + F.esc(r.news[0].src || '') + '</small></div>' : '') + '</div>';
  };
  A.section = function (full) {
    const a = A.get();
    let h = E.sectionHead('Why it moved', a && a.n ? ('every move ≥ 1.5σ on a liquid name, split into the market\'s part (β × ' + F.esc(a.ref || 'the Nifty') + ', ' + F.pct(a.nifty_d1, 2) + ' today), the sector\'s part and the stock\'s own — ' + a.n + ' big moves: ' + Object.keys(a.kinds || {}).map(function (k) { return a.kinds[k] + ' ' + k.toLowerCase(); }).join(', ')) : 'the attribution arrives with the first v148 pass', full ? '' : '<span class="act" onclick="E.go(\'micro\',\'today\')">all of them →</span>');
    if (!a || !(a.rows || []).length) return h + '<div class="e-empty">no move cleared 1.5σ on a liquid name this session</div>';
    h += '<div class="e-grid e-auto">' + a.rows.slice(0, full ? 16 : 6).map(A.tile).join('') + '</div>';
    if (full) h += '<div class="note">' + F.esc(a.how || '') + '</div>';
    return h;
  };
  A.line = function (sym) {
    const r = A.of(sym); if (!r) return '';
    return '<div class="cd" style="margin-top:10px"><div class="e-between" style="gap:10px;flex-wrap:wrap"><div><div class="lbl">Today\'s move, explained</div><div style="font-size:13.5px;color:#fff;margin-top:2px">' + F.esc(r.note) + '</div>' + (r.dlv_note ? '<div style="font-size:12px;color:var(--dim);margin-top:4px">' + F.esc(r.dlv_note) + '</div>' : '') + '</div><div style="min-width:220px;flex:1;max-width:360px">' + A.bar(r) + '<div style="font-size:11px;color:var(--dim);margin-top:4px">market ' + F.pct(r.mkt, 1) + ' · sector ' + F.pct(r.sec, 1) + ' · own ' + F.pct(r.own, 1) + ' · <span class="e-word ' + A.kindCls(r.kind) + '" style="font-size:10px;padding:1px 6px">' + F.esc(r.kind) + '</span></div></div></div></div>';
  };

  /* ── the Street ── */
  const ST = E.street = {};
  ST.get = function () { return (E.lite && E.lite.street) || null; };
  ST.of = function (sym) { const s = ST.get(); return s && s.by && s.by[sym] || null; };
  ST.row = function (r) { return '<div class="e-li" onclick="E.openShare(\'' + F.esc(r.sym) + '\')"><div class="n">' + F.esc(r.nm) + '<small>' + F.esc(r.sym) + ' · ' + F.esc(r.sector || '') + ' · ' + r.street_n + ' analysts' + (r.street_rec ? ' · ' + F.esc(r.street_rec) : '') + '</small></div><div style="text-align:right;font-size:12px"><div><span style="color:var(--dim)">Street</span> <b class="' + F.tone(r.up_street) + ' e-mono">' + F.pct(r.up_street, 0) + '</b> <span style="color:var(--dim)">· engine</span> <b class="' + F.tone(r.up_engine) + ' e-mono">' + F.pct(r.up_engine, 0) + '</b></div><div style="color:var(--dim)">gap <b class="e-mono" style="color:#fff">' + F.sgn(r.gap, 0) + ' pts</b>' + (r.ls ? ' · ' + F.word(r.ls) : '') + '</div></div><div class="px"><span data-live-px="' + F.esc(r.sym) + '">' + F.inr(L.px(r.sym) || r.px) + '</span><small>Street ₹' + F.inr(r.street).replace('₹', '') + '</small></div></div>'; };
  ST.section = function (full) {
    const s = ST.get();
    let h = E.sectionHead('The Street against the engine', s && s.n ? (s.n + ' names with five or more analysts · the two agree on direction ' + s.agree_pct + '% of the time · rank correlation ' + (s.corr != null ? s.corr : '—') + ' · the Street\'s median upside ' + F.pct(s.street_up_median, 0) + ', the engine\'s ' + F.pct(s.engine_up_median, 0)) : 'the Street arrives with the profiles rotation', full ? '' : '<span class="act" onclick="E.go(\'micro\',\'street\')">the whole board →</span>');
    if (!s || !s.n) return h + '<div class="e-empty">no analyst targets on file yet</div>';
    const n = full ? 10 : 4;
    h += '<div class="e-grid e-g2"><div><div class="lbl">Where the engine is more bullish than the Street</div><div class="e-list">' + (s.bull || []).slice(0, n).map(ST.row).join('') + '</div></div><div><div class="lbl">Where the engine is more bearish than the Street</div><div class="e-list">' + (s.bear || []).slice(0, n).map(ST.row).join('') + '</div></div></div>';
    if (full) {
      h += '<div class="note">' + F.esc(s.how || '') + '</div>';
      const R = ((E.lite && E.lite.record) || {}).street || {};
      h += E.sectionHead('Who was right', 'sixty sessions after each board, whose implied path did the price come closer to?');
      h += '<div class="e-record"><div class="e-stat"><div class="k">The engine closer · 60 sessions</div><div class="v">' + (R.n ? R.engine_closer + '%' : '—') + '</div><div class="s">' + (R.n ? ('of ' + R.n + ' scored disagreements · average miss: engine ' + F.n(R.err_engine, 1) + ' pts, Street ' + F.n(R.err_street, 1) + ' pts') : 'the first board is scored sixty sessions after it prints') + '</div></div></div>';
    }
    return h;
  };
  ST.line = function (sym, r) {
    const s = ST.of(sym); const vl = (r && r.v && r.v.long) || {};
    if (!s) return '';
    const who = s.gap >= 8 ? 'the engine is the more bullish' : s.gap <= -8 ? 'the Street is the more bullish' : 'the two broadly agree';
    return '<div class="e-line"><b>The Street against the engine:</b> ' + s.street_n + ' analysts put the mean target at ₹' + F.inr(s.street).replace('₹', '') + ' (' + F.pct(s.up_street, 0) + ' from here' + (s.street_rec ? ', consensus “' + F.esc(s.street_rec) + '”' : '') + '); the engine\'s twelve-month expectation is ' + F.pct(s.up_engine, 0) + (vl.target ? ' (₹' + F.inr(vl.target).replace('₹', '') + ')' : '') + ' — ' + who + ' by ' + Math.abs(Math.round(s.gap)) + ' points. The record of who turns out closer is on Markets → The Street.</div>';
  };

  /* ── the news per name ── */
  const NW = E.news = { data: null, loaded: false, _p: null };
  NW.load = function () { if (NW._p) return NW._p; NW._p = fetch(E.url('news.json'), { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { NW.data = j; NW.loaded = true; return j; }).catch(function () { NW.loaded = true; return null; }); return NW._p; };
  NW.of = function (sym) { return NW.data && NW.data.names && NW.data.names[sym] || null; };
  NW.list = function (items, n) { return '<div class="e-nws">' + (items || []).slice(0, n || 6).map(function (x) { return '<a class="e-nw" target="_blank" rel="noopener" href="' + F.esc(x.link || '#') + '"><span class="tn ' + (x.tone > 0 ? 'e-up' : x.tone < 0 ? 'e-dn' : '') + '">' + (x.tone > 0 ? '▲' : x.tone < 0 ? '▼' : '•') + '</span><span class="t">' + F.esc(x.t) + '</span><span class="m">' + F.esc(x.src || '') + (x.age_d != null ? ' · ' + (x.age_d <= 1 ? 'today' : Math.round(x.age_d) + 'd ago') : '') + ((x.tags || []).length ? ' · ' + x.tags.map(F.esc).join(', ') : '') + '</span></a>'; }).join('') + '</div>'; };
  NW.section = function (sym, lt) {
    const rec = NW.of(sym);
    if (!rec || !(rec.items || []).length) return null;
    const tone = rec.tone || 0;
    return '<div class="cd"><div class="e-between" style="flex-wrap:wrap;gap:8px"><div class="lbl" style="margin:0">' + rec.items.length + ' headline' + (rec.items.length > 1 ? 's' : '') + ' in the last week · the week reads <b class="' + (tone > 0 ? 'e-up' : tone < 0 ? 'e-dn' : '') + '">' + (tone > 0 ? 'positive' : tone < 0 ? 'negative' : 'neutral') + '</b> (' + (rec.pos || 0) + ' for, ' + (rec.neg || 0) + ' against)</div><span style="font-size:11px;color:var(--mut)">Google News · fetched ' + F.esc((rec.at || '').slice(11)) + ' IST · scored by a small finance lexicon, not read by the models</span></div>' + NW.list(rec.items, 6) + '</div>';
  };

  /* ── delivery and the history line (the share page) ── */
  E.deliveryLine = function (t, d1) {
    if (!t || t.dlv == null) return '';
    const z = t.dlv_z; const word = (z != null && z >= 1 && d1 > 0) ? ['ACCUMULATION', 'buy'] : (z != null && z >= 1 && d1 < 0) ? ['DISTRIBUTION', 'sell'] : (z != null && z <= -1 && Math.abs(d1 || 0) >= 2) ? ['SPECULATIVE', 'avoid'] : null;
    return '<div class="e-line"><b>Delivery ' + F.n(t.dlv, 0) + '%</b> of the day\'s volume was taken home' + (t.dlv_avg != null ? ' against a ' + F.n(t.dlv_avg, 0) + '% average over twenty sessions' + (z != null ? ' (' + F.sgn(z, 1) + 'σ)' : '') : '') + (word ? ' — <span class="e-word ' + word[1] + '" style="font-size:10.5px;padding:1px 7px">' + word[0] + '</span> ' + (word[0] === 'ACCUMULATION' ? 'buyers are keeping the stock, not flipping it' : word[0] === 'DISTRIBUTION' ? 'holders are leaving for keeps, not day-traders' : 'an intraday move — little of it was positional') : '') + '. NSE\'s own figure (sec_bhavdata_full), a day late like the bhavcopy.</div>';
  };
  E.historyLine = function (t) {
    if (!t || !t.since) return '';
    const s = String(t.since); const y = s.slice(0, 4), m = +s.slice(4, 6); const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1] || '';
    const yrs = t.yrs;
    if (t.trunc) return '<span style="color:var(--dim)">the engine\'s tape runs from ' + mon + ' ' + y + ' (as far back as its panel reaches — the chart\'s “Since listing” goes further through the live door)</span>';
    if (yrs != null && yrs < 1.5) return '<span style="color:var(--amb)">history on the tape since ' + mon + ' ' + y + ' (' + Math.max(1, Math.round(yrs * 12)) + ' months, ' + (t.n || 0) + ' ' + (t.src === 'daily' ? 'sessions' : 'weeks') + ') — a young listing: the twelve-month side has no full year to lean on and the regime record is thin</span>';
    return '<span style="color:var(--dim)">the tape runs from ' + mon + ' ' + y + (yrs != null ? ' (' + (yrs >= 9.5 ? '10+' : F.n(yrs, 1)) + ' years)' : '') + '</span>';
  };
})(window.E);
