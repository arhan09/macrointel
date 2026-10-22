/* ═══ v144 · BOOT — after the page's own boot: load the engine, route every click here ═══ */
(function (E) {
  const TABS = ['home', 'micro', 'research', 'macro', 'industries', 'funds', 'agents', 'ask', 'ois', 'forex', 'comm', 'intl', 'charts', 'news', 'qa', 'tearsheet'];
  async function start() {
    try { window.__oldOpenShare = window.openShare; } catch (e) { }
    window.openShare = function (q, opt) { return E.openShare(q, opt); };
    try { if (typeof openIndustry === 'function') { window.__oldOpenIndustry = openIndustry; window.openIndustry = function (s, opt) { return E.industry.open(s, opt); }; } } catch (e) { }
    try { const old = window.liveRefresh; if (typeof old === 'function') window.liveRefresh = async function (f) { try { await old(f); } catch (e) { } E.onLive(); }; } catch (e) { }
    try { const osw = window.sw; if (typeof osw === 'function') window.sw = function (b, t) { osw(b, t); try { const tt = ({ call: 'home', desk: 'agents', pack: 'charts', tearsheet: 'charts' })[t] || t; document.querySelectorAll('.e-nav .tab').forEach(function (x) { x.classList.toggle('a', x.getAttribute('data-tab') === tt); }); E.macro.bar(tt); if (tt === 'macro') E.macro.render(); } catch (e) { } }; } catch (e) { }
    await E.load();
    try { await E.pipe.load(); } catch (e) { }
    /* v148 · the bell, the new-pass watcher, the headlines */
    try { E.brief.mount(); E.brief.badge(); E.brief.watch(); } catch (e) { }
    try { E.news.load(); } catch (e) { }
    try { if (E.lite && E.lite.version) { const bv = document.getElementById('build-version'); if (bv) bv.textContent = 'v148'; } } catch (e) { }
    const h = (location.hash || '').replace(/^#/, '');
    if (h.indexOf('s=') === 0) { E.go('home'); E.openShare(decodeURIComponent(h.slice(2)), { nopush: true }); }
    else if (h.indexOf('i=') === 0) { E.go('industries'); E.industry.open(decodeURIComponent(h.slice(2)), { nopush: true }); }
    else if (h.indexOf('funds/') === 0) { E.funds.code = h.slice(6); E.go('funds'); }
    else { const p = h.split('/'); E.go(TABS.indexOf(p[0]) >= 0 ? p[0] : 'home', p[1]); }
    try { E.funds.load().then(function () { const el = document.getElementById('e-funds-strip'); if (el) el.innerHTML = E.funds.strip(); }); } catch (e) { }
    E.onLive();
    setInterval(function () { E.onLive(); }, 30000);
    E.onLiveHook(function () { try { if (E.tab === 'micro' && E.markets.sub === 'today' && document.getElementById('e-markets')) { /* repaint the live movers block only */ const lm = E.markets.liveMovers(); if (lm) { const secs = document.querySelectorAll('#e-markets .e-sec'); } } } catch (e) { } });
    E.markets.afterRender();
    /* the markets tab re-hydrates its cards after each render */
    const orender = E.markets.render; E.markets.render = function () { orender(); E.markets.afterRender(); };
    /* the phone's bottom bar: ours, with the new tabs (the old one is hidden) */
    try {
      if (!document.getElementById('e-bnav')) {
        const n = document.createElement('div'); n.id = 'e-bnav'; n.className = 'mi-bnav';
        const main = [['home', '🏠', 'Home'], ['micro', '📈', 'Markets'], ['research', '🔬', 'Research'], ['macro', '🏦', 'Macro'], ['ask', '💬', 'Ask']];
        n.innerHTML = main.map(function (t) { return '<button data-t="' + t[0] + '" onclick="E.go(\'' + t[0] + '\')"><span class="i">' + t[1] + '</span>' + t[2] + '</button>'; }).join('') + '<button onclick="window.scrollTo({top:0});document.querySelector(\'.e-more\').classList.toggle(\'open\')"><span class="i">⋯</span>More</button>';
        document.body.appendChild(n);
      }
    } catch (e) { }
    document.body.classList.add('e-ready');
  }
  if (document.readyState === 'complete') setTimeout(start, 50); else window.addEventListener('load', function () { setTimeout(start, 50); });
})(window.E);
