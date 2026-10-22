/* ═══ v145.1 · THE PIPELINE'S OWN PUNCTUALITY — which hourly passes ran, which were late, which never came ═══
   history/passes.json is written by the workflow itself (one line per run). The page shows it so a stale
   page is never a mystery: the expected slots, the passes that landed, the watchdog's rescues. */
(function (E) {
  const F = E.f;
  const P = E.pipe = { log: null, loaded: false };
  P.SLOTS = ['08:07', '09:07', '10:07', '11:07', '12:07', '13:07', '14:07', '15:07', '15:37', '16:07', '17:07', '18:07', '19:07', '20:07'];
  P.load = async function () {
    if (P.loaded) return P.log;
    for (let i = 0; i < 2 && !P.log; i++) {
      try { const r = await fetch(E.url('history/passes.json'), { cache: 'no-store' }); if (r.ok) P.log = await r.json(); else if (r.status === 404) break; } catch (e) { P.log = null; }
      if (!P.log && i === 0) await new Promise(function (ok) { setTimeout(ok, 4000); });
    }
    P.loaded = true; return P.log;
  };
  P.istNow = function () { const d = new Date(Date.now() + (330 + new Date().getTimezoneOffset()) * 60000); return d; };
  P.today = function () {
    const L = P.log || []; const d = P.istNow(); const day = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    const rows = L.filter(function (x) { return (x.started || '').slice(0, 10) === day; });
    const wd = d.getDay(); const weekday = wd >= 1 && wd <= 5; const nowMin = d.getHours() * 60 + d.getMinutes();
    const used = new Set();
    const slots = P.SLOTS.map(function (s) {
      const m = +s.slice(0, 2) * 60 + +s.slice(3); const due = weekday && nowMin >= m + 50;
      /* a slot is served by the first pass that started within 50 minutes of it */
      const hit = rows.find(function (r) { const t = r.started.slice(11); const mm = +t.slice(0, 2) * 60 + +t.slice(3); return mm >= m - 3 && mm <= m + 50 && !used.has(r); });
      if (hit) used.add(hit);
      return { slot: s, due: due, pass: hit || null, late: hit ? Math.max(0, (+hit.started.slice(11, 13) * 60 + +hit.started.slice(14)) - m) : null };
    });
    const last = rows.length ? rows[rows.length - 1] : (L.length ? L[L.length - 1] : null);
    return { rows: rows, slots: slots, last: last, extra: rows.filter(function (r) { return !used.has(r); }), missed: slots.filter(function (s) { return s.due && !s.pass; }).length, served: slots.filter(function (s) { return s.pass; }).length, due: slots.filter(function (s) { return s.due; }).length, weekday: weekday };
  };
  P.chip = function () {
    if (!P.log) return '<span class="e-live" title="the pipeline\'s pass log arrives with the first v145.1 pass"><i></i>pipeline · pass log not on the site yet</span>';
    const T = P.today(); const last = T.last; const fin = last && (last.finished || last.started);
    const ago = fin ? F.ago(new Date(fin.replace(' ', 'T') + ':00+05:30').getTime()) : '';
    const cls = T.missed === 0 ? 'on' : (T.missed <= 2 ? 'feed' : '');
    return '<span class="e-live ' + cls + '" style="cursor:pointer" onclick="E.go(\'micro\',\'records\')" title="' + (T.weekday ? (T.served + ' of ' + T.due + ' scheduled passes landed today · ' + T.missed + ' missed') : 'no scheduled passes on a weekend') + '"><i></i>pipeline · last pass ' + (fin ? fin.slice(11) + ' IST (' + ago + ')' : '—') + (T.weekday && T.due ? ' · ' + T.served + '/' + T.due + ' today' + (T.missed ? ' · <b>' + T.missed + ' missed</b>' : '') : '') + '</span>';
  };
  P.section = function () {
    let h = E.sectionHead('The pipeline\'s own punctuality', 'every hourly pass is logged by the workflow itself — the slot, when it actually started, how long it took, who triggered it (schedule · watchdog · manual) · a missed slot is a GitHub cron that never arrived; the watchdog re-fires it within fifteen minutes');
    if (!P.log) return h + '<div class="e-empty">the pass log arrives with the first v145.1 pass</div>';
    const T = P.today();
    const dur = function (r) { if (!r || !r.finished) return '—'; const a = new Date(r.started.replace(' ', 'T') + ':00+05:30').getTime(), b = new Date(r.finished.replace(' ', 'T') + ':00+05:30').getTime(); return Math.round((b - a) / 60000) + ' min'; };
    h += '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%"><thead><tr><th>slot (IST)</th><th>pass</th><th>started</th><th>took</th><th>trigger</th></tr></thead><tbody>' +
      T.slots.map(function (s) { const r = s.pass; return '<tr><td><b style="color:#fff">' + s.slot + '</b></td><td>' + (r ? '<span class="e-word buy" style="font-size:10.5px">LANDED' + (s.late > 20 ? ' · ' + s.late + ' min late' : '') + '</span>' : (s.due ? '<span class="e-word sell" style="font-size:10.5px">MISSED</span>' : '<span style="color:var(--mut)">not yet</span>')) + '</td><td>' + (r ? r.started.slice(11) : '—') + '</td><td>' + dur(r) + '</td><td style="color:var(--dim)">' + (r ? F.esc(r.kind) + (r.n ? ' · run #' + r.n : '') : '') + '</td></tr>'; }).join('') + '</tbody></table></div>';
    const extra = T.extra;
    if (extra.length) h += '<div class="note">also today, outside the slots: ' + extra.map(function (r) { return F.esc(r.kind) + ' at ' + r.started.slice(11) + (r.finished ? ' (' + dur(r) + ')' : ''); }).join(' · ') + '</div>';
    const all = (P.log || []).slice(-60).reverse();
    h += '<details style="margin-top:10px"><summary style="cursor:pointer;color:var(--dim);font-size:12px">the last ' + all.length + ' passes</summary><div class="cd" style="padding:0;overflow-x:auto;margin-top:8px"><table class="tbl" style="width:100%"><thead><tr><th>started (IST)</th><th>finished</th><th>took</th><th>trigger</th><th>cron</th></tr></thead><tbody>' + all.map(function (r) { return '<tr><td>' + F.esc(r.started) + '</td><td>' + F.esc(r.finished || '—') + '</td><td>' + dur(r) + '</td><td>' + F.esc(r.kind) + '</td><td style="color:var(--mut)">' + F.esc(r.cron || '') + '</td></tr>'; }).join('') + '</tbody></table></div></details>';
    return h;
  };
})(window.E);
