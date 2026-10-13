/* ═══ v144 · MACRO — the view first, the deep tabs underneath, one bar ═══ */
(function (E) {
  const F = E.f;
  const M = E.macro = {};
  M.TABS = [['macro', 'The view'], ['ois', 'Rates'], ['forex', 'The rupee'], ['comm', 'Gold & oil'], ['intl', 'Global'], ['charts', 'Chart pack'], ['news', 'News'], ['qa', 'Ask the desk (classic)']];
  M.bar = function (active) {
    M.TABS.forEach(function (t) {
      const el = document.getElementById('e-mbar-' + t[0]); if (!el) return;
      el.innerHTML = M.TABS.map(function (x) { return '<span class="e-chip' + (x[0] === active ? ' a' : '') + '" onclick="E.go(\'' + x[0] + '\')">' + x[1] + '</span>'; }).join('') + '<span style="flex:1"></span><span style="font-size:11.5px;color:var(--mut);align-self:center">the macro desk — every number computed from official data at every pass</span>';
    });
  };
  M.render = function () {
    const el = document.getElementById('e-macro-head'); if (!el) return;
    const K = (E.lite && E.lite.market) || {};
    /* one source of truth: the view's "names" step and its gate line read the engine, not the old chain */
    try {
      const mv = document.getElementById('macro-view');
      if (mv && E.lite) {
        mv.querySelectorAll('*').forEach(function (n) { if (n.children.length === 0 && /no fresh longs/i.test(n.textContent)) n.textContent = n.textContent.replace(/gate on\s*[—-]\s*no fresh longs/i, 'gate on — sizes halved'); });
        const C = (E.lite.counts || {});
        mv.querySelectorAll('div').forEach(function (d) { if (/^\s*3\s*·\s*NAMES/i.test(d.textContent) && d.children.length <= 3 && d.textContent.length < 120) { d.innerHTML = '<div style="font:600 10px IBM Plex Sans;color:var(--dim);letter-spacing:.5px">3 · NAMES</div><div style="font:600 16px IBM Plex Sans;color:#fff;margin:2px 0">' + (C.buy || 0) + ' to buy · ' + (C.sell || 0) + ' to sell</div><div style="font-size:11px;color:var(--dim)">the engine\'s calls today, each scored</div>'; } });
      }
    } catch (e) { }
    el.innerHTML = '<div class="e-between" style="margin-bottom:10px"><div><div class="e-h2">Macro</div><div class="e-sub">the house view by asset class, written by rules from the regime engine · then the indicators, the note, the folds</div></div>' + (K.regime ? '<div class="e-row"><span class="e-word acc mid">' + F.esc(K.regime).toUpperCase() + '</span>' + (K.gate ? '<span class="e-word avoid">GATE ON</span>' : '') + (K.call ? '<span class="e-tag">' + F.esc(K.call) + '</span>' : '') + '</div>' : '') + '</div>' +
      (function () { try { return E.nowcast.card(false); } catch (e) { return ''; } })() + (function () { try { return E.alloc.card().replace('margin-top:14px', 'margin:0 0 12px'); } catch (e) { return ''; } })() + (function () { try { return '<div style="margin:4px 0 16px">' + E.nowcast.postmortems() + '</div>'; } catch (e) { return ''; } })();
  };
})(window.E);
