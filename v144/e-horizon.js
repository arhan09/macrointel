/* ═══ v147 · ANY HORIZON — the cone for any share at any number of sessions, from four numbers the engine
   writes on every scored name: the daily σ, the short drift and its horizon, the long drift. Consistent with the
   verdicts by construction: the short target at its horizon, the 12-month expectation at 250 sessions. ═══ */
(function (E) {
  const F = E.f;
  const H = E.hz = {};
  H.STD = [1, 5, 20, 40, 60, 100, 200, 250, 400];
  H.phi = function (z) { /* Φ(z) · Abramowitz–Stegun */ const t = 1 / (1 + 0.2316419 * Math.abs(z)); const d = 0.3989423 * Math.exp(-z * z / 2); const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274)))); return z > 0 ? 1 - p : p; };
  H.drift = function (hz, t) { const hs = hz.hs || 20; if (t <= hs) return hz.ds || 0; if (t <= hs + 40) { const w = (t - hs) / 40; return (hz.ds || 0) * (1 - w) + (hz.dl || 0) * w; } return hz.dl || 0; };
  H.calc = function (hz, h, px) {
    h = Math.max(1, Math.round(h)); let e = 0; for (let t = 1; t <= h; t++) e += H.drift(hz, t);
    const sd = (hz.sig || 2) * Math.sqrt(h);                       /* % */
    /* v148.2 · the Sharpe cap: no path expects more than cap · σ_day · h / √250 at any horizon (a Sharpe-1 bet) */
    const capE = (hz.cap || 1.0) * (hz.sig || 2) * h / Math.sqrt(250); e = Math.max(-capE, Math.min(capE, e));
    const mu = Math.log(1 + e / 100) - 0.5 * Math.pow(sd / 100, 2);  /* log drift, volatility drag */
    const s = sd / 100;
    const p = H.phi(mu / s);
    const price = px * Math.exp(mu);
    return { h: h, exp: (price / px - 1) * 100, exp_arith: e, sd: sd, p_up: p, price: price, lo1: px * Math.exp(mu - s), hi1: px * Math.exp(mu + s), lo2: px * Math.exp(mu - 2 * s), hi2: px * Math.exp(mu + 2 * s) };
  };
  H.label = function (h) { const d = Math.round(h * 7 / 5); if (h === 1) return 'next session'; if (h < 20) return h + ' sessions · ~' + d + ' days'; if (h < 60) return h + ' sessions · ~' + Math.round(d / 7) + ' weeks'; if (h < 250) return h + ' sessions · ~' + Math.round(h / 21) + ' months'; return h + ' sessions · ~' + (h / 250).toFixed(1).replace('.0', '') + ' year' + (h >= 375 ? 's' : ''); };
  H.row = function (hz, h, px) {
    const c = H.calc(hz, h, px);
    return '<tr><td><b style="color:#fff">' + F.esc(H.label(h)) + '</b></td><td style="text-align:right"><b class="' + F.tone(c.exp) + '">' + F.inr(c.price) + '</b><div style="font-size:10.5px;color:var(--mut)">' + F.pct(c.exp, 1) + '</div></td><td style="text-align:right">' + F.inr(c.lo1) + ' – ' + F.inr(c.hi1) + '</td><td style="text-align:right;color:var(--dim)">' + F.inr(c.lo2) + ' – ' + F.inr(c.hi2) + '</td><td style="text-align:right"><b class="' + (c.p_up >= 0.6 ? 'e-up' : c.p_up <= 0.4 ? 'e-dn' : '') + '">' + Math.round(c.p_up * 100) + '%</b></td></tr>';
  };
  H.table = function (sym, hz, px, id) {
    if (!hz || !hz.sig) return '<div class="e-empty">no horizon cone yet — the engine writes it once the name has a tape</div>';
    let h = '<div class="cd" style="padding:0;overflow-x:auto"><table class="tbl" style="width:100%" id="' + (id || 'e-hz-tbl') + '"><thead><tr><th>horizon</th><th style="text-align:right">expected</th><th style="text-align:right">likely range (±1σ)</th><th style="text-align:right">wide range (±2σ)</th><th style="text-align:right">P(higher)</th></tr></thead><tbody>' + H.STD.map(function (x) { return H.row(hz, x, px); }).join('') + '</tbody></table></div>';
    h += '<div class="e-row" style="margin-top:10px"><span style="font-size:12.5px;color:var(--dim)">any number of sessions:</span><input class="e-input" type="number" min="1" max="2000" value="120" style="width:120px;padding:7px 10px;font-size:13px" id="' + (id || 'e-hz-tbl') + '-n" oninput="E.hz.custom(\'' + F.esc(sym) + '\',\'' + (id || 'e-hz-tbl') + '\')"><span id="' + (id || 'e-hz-tbl') + '-out" style="font-size:13px;color:var(--tx)"></span></div>';
    h += '<div class="e-line">σ ' + F.n(hz.sig, 2) + '% a session · the expected path: ' + F.sgn(hz.ds, 3) + '%/session for the first ' + hz.hs + ' sessions (' + (hz.src === 'prior' || !hz.src ? 'a modest prior for the short verdict\'s side — 2.5% per twenty sessions, 3.5% at HIGH conviction — until the engine\'s own record has thirty scored calls' : 'the engine\'s own ' + F.esc(hz.src)) + '), then ' + F.sgn(hz.dl, 3) + '%/session (the twelve-month expectation, clipped to ±30%/yr). <b>Never the target</b>: a target is a line to trade against; the path is what the evidence expects. Every horizon is capped at a Sharpe-1 path (no more than σ·h/√250), and the expected price is the median (the drift less the volatility drag — on a volatile name the median sits below the mean, and a long horizon can read flat). The likely range is ±σ√h; P(higher) is the chance of being above today\'s price, and it cannot exceed ~84% at a year. A cone, not a promise.</div>';
    return h;
  };
  H.custom = function (sym, id) {
    try {
      const n = +document.getElementById(id + '-n').value; const out = document.getElementById(id + '-out'); const r = E.rowSync(sym); const lt = E.lt(sym) || {}; const px = E.live.px(sym) || lt.px; const hz = r && r.v && r.v.hz;
      if (!hz || !n || !px) { out.textContent = ''; return; }
      const c = H.calc(hz, n, px);
      out.innerHTML = '<b style="color:#fff">' + F.esc(H.label(n)) + '</b>: ' + F.inr(c.price) + ' (' + F.pct(c.exp, 1) + '), likely ' + F.inr(c.lo1) + ' – ' + F.inr(c.hi1) + ', P(higher) ' + Math.round(c.p_up * 100) + '%';
    } catch (e) { }
  };
  /* the cone on a chart: points for ±1σ / ±2σ over n sessions from px */
  H.cone = function (hz, n, px, step) { const lo1 = [], hi1 = [], lo2 = [], hi2 = [], mid = []; for (let t = 0; t <= n; t += (step || 1)) { if (t === 0) { lo1.push(px); hi1.push(px); lo2.push(px); hi2.push(px); mid.push(px); continue; } const c = H.calc(hz, t, px); lo1.push(c.lo1); hi1.push(c.hi1); lo2.push(c.lo2); hi2.push(c.hi2); mid.push(c.price); } return { lo1: lo1, hi1: hi1, lo2: lo2, hi2: hi2, mid: mid }; };
})(window.E);
