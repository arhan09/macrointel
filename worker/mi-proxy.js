/* MacroIntel · THE LIVE DOOR · v144 — a Cloudflare Worker, free tier, three minutes to set up.
   A static page on GitHub Pages cannot call Yahoo Finance from the browser (no CORS). This worker
   forwards the page's Yahoo requests with the CORS header, caches each answer at the edge for 20
   seconds (a thousand readers = one upstream call), and offers a batch endpoint. No key, no secret,
   no data of yours; the URL is public and goes into a repository VARIABLE (not a secret), MI_PROXY.

   SET-UP (once):
     1. dash.cloudflare.com → Workers & Pages → Create application → Create Worker → Deploy
     2. Edit code → replace everything with this file → Deploy → copy the URL
        (https://<name>.<you>.workers.dev)
     3. GitHub → your repo → Settings → Secrets and variables → Actions → Variables →
        New repository variable:  name MI_PROXY   value https://<name>.<you>.workers.dev/?u=
        (the trailing "?u=" matters). The next pipeline pass writes it into the page and every
        device is live. Until then, on any device: More ▾ → "Paste your live door" → the same URL.

   ENDPOINTS
     /?u=<yahoo url>            pass-through for query1/query2.finance.yahoo.com (what the page uses)
     /q?s=ITC.NS,RELIANCE.NS    batch quotes → {ts, q:{SYM:{p,d,t}}}  (up to 400 symbols a call)
     /chart?s=ITC.NS&range=1d&interval=1m   one chart, cached
     /health                    "ok" */
const Y = "https://query1.finance.yahoo.com";
const CORS = { "access-control-allow-origin": "*", "access-control-allow-methods": "GET,OPTIONS", "access-control-allow-headers": "*", "cache-control": "public, max-age=20" };
const UA = { "user-agent": "Mozilla/5.0 (MacroIntel live door)", "accept": "application/json" };

async function viaCache(req, url, ttl) {
  const cache = caches.default;
  const key = new Request(url, { method: "GET" });
  let r = await cache.match(key);
  if (r) return r;
  const up = await fetch(url, { headers: UA, cf: { cacheTtl: ttl || 20, cacheEverything: true } });
  const body = await up.arrayBuffer();
  r = new Response(body, { status: up.status, headers: { "content-type": up.headers.get("content-type") || "application/json", "cache-control": "public, max-age=" + (ttl || 20) } });
  if (up.ok) await cache.put(key, r.clone());
  return r;
}

function withCors(r) {
  const h = new Headers(r.headers);
  for (const k in CORS) h.set(k, CORS[k]);
  return new Response(r.body, { status: r.status, headers: h });
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const url = new URL(request.url);
    const p = url.pathname;
    try {
      if (p === "/health") return new Response("ok", { headers: CORS });
      if (p === "/q") {
        const syms = (url.searchParams.get("s") || "").split(",").map(s => s.trim()).filter(Boolean).slice(0, 400);
        if (!syms.length) return new Response(JSON.stringify({ error: "s=SYM,SYM" }), { status: 400, headers: CORS });
        const chunks = [];
        for (let i = 0; i < syms.length; i += 100) chunks.push(syms.slice(i, i + 100));
        const out = {}; const ts = Math.floor(Date.now() / 1000);
        await Promise.all(chunks.map(async ch => {
          const r = await viaCache(request, Y + "/v8/finance/spark?symbols=" + ch.map(encodeURIComponent).join(",") + "&range=1d&interval=5m", 20);
          if (!r.ok) return;
          const j = await r.json();
          for (const x of ((j.spark || {}).result || [])) {
            try {
              const res = x.response && x.response[0]; if (!res) continue; const m = res.meta || {};
              const cl = (((res.indicators || {}).quote || [{}])[0].close) || []; const lastC = cl.filter(v => v != null).pop();
              const last = m.regularMarketPrice != null ? m.regularMarketPrice : lastC; const prev = m.chartPreviousClose != null ? m.chartPreviousClose : m.previousClose;
              if (last == null) continue;
              out[x.symbol] = { p: +last, d: prev ? +(((last / prev) - 1) * 100).toFixed(3) : null, t: (m.regularMarketTime || 0) * 1000 || Date.now() };
            } catch (e) { }
          }
        }));
        return new Response(JSON.stringify({ ts, n: Object.keys(out).length, q: out }), { headers: Object.assign({ "content-type": "application/json" }, CORS) });
      }
      if (p === "/chart") {
        const s = url.searchParams.get("s") || "^NSEI"; const range = url.searchParams.get("range") || "1d"; const iv = url.searchParams.get("interval") || "1m";
        const r = await viaCache(request, Y + "/v8/finance/chart/" + encodeURIComponent(s) + "?range=" + encodeURIComponent(range) + "&interval=" + encodeURIComponent(iv), range === "1d" ? 20 : 300);
        return withCors(r);
      }
      const u = url.searchParams.get("u");
      if (!u || !/^https:\/\/(query1|query2)\.finance\.yahoo\.com\//.test(u)) {
        return new Response("MacroIntel live door · use ?u=<yahoo url>, /q?s=…, /chart?s=…", { status: 400, headers: CORS });
      }
      const r = await viaCache(request, u, /interval=1m|range=1d/.test(u) ? 20 : 120);
      return withCors(r);
    } catch (e) {
      return new Response(JSON.stringify({ error: String(e && e.message || e) }), { status: 502, headers: Object.assign({ "content-type": "application/json" }, CORS) });
    }
  }
};
