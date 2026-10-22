/* MacroIntel · THE LIVE DOOR + THE SCHEDULER · v146.2 — a Cloudflare Worker, free tier.
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
     /health                    "ok"
     /cron                      what the scheduler would do right now (a dry run; ?go=1 fires it — add a CRON_KEY secret
                                to the worker and pass ?key=… if you want that locked)

   THE SCHEDULER (v146.2) — GitHub's own cron does not deliver this repo's scheduled runs in the IST morning
   (02:00–10:00 UTC): for days the 08:07–14:07 passes never ran, and yesterday's arrived at 1 a.m. Cloudflare's
   Cron Triggers are reliable, so the worker fires the pipeline itself through the GitHub API:
     1. GitHub → (your avatar) Settings → Developer settings → Personal access tokens → Fine-grained tokens →
        Generate: name macrointel-cron · expiry 1 year · Only select repositories: macrointel ·
        Repository permissions → Actions: Read and write → Generate → copy (github_pat_…)
     2. Cloudflare → Workers & Pages → mi-proxy → Settings → Variables and Secrets → Add →
        type Secret · name GH_TOKEN · value = the token → Deploy
     3. Cloudflare → mi-proxy → Settings → Triggers → Cron Triggers → add these three (UTC):
          37 2-14 * * 1-5      the hourly pass, 08:07 → 20:07 IST
          7 10 * * 1-5         the 15:37 IST close pass
          0,10,20,30,40,50 3-10 * * 1-5    the live feed, every ten minutes 08:30 → 16:20 IST
     4. Edit code → replace with this file → Deploy.  Test: open <worker url>/cron (a dry run).
   GitHub's own crons stay as a backup; the daily workflow's gate skips a scheduled run that lands within
   40 minutes of the last pass, so the two never double up. */
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

const GH_REPO_DEFAULT = "arhan09/macrointel";

async function ghDispatch(env, wf, inputs) {
  const repo = env.GH_REPO || GH_REPO_DEFAULT;
  const headers = { "authorization": "Bearer " + env.GH_TOKEN, "accept": "application/vnd.github+json", "x-github-api-version": "2022-11-28", "user-agent": "MacroIntel scheduler", "content-type": "application/json" };
  const r = await fetch("https://api.github.com/repos/" + repo + "/actions/workflows/" + wf + "/dispatches", { method: "POST", headers, body: JSON.stringify({ ref: "main", inputs: inputs || {} }) });
  return r.status;   // 204 = dispatched
}

async function ghBusy(env, wf) {
  const repo = env.GH_REPO || GH_REPO_DEFAULT;
  const headers = { "authorization": "Bearer " + env.GH_TOKEN, "accept": "application/vnd.github+json", "x-github-api-version": "2022-11-28", "user-agent": "MacroIntel scheduler" };
  try {
    const r = await fetch("https://api.github.com/repos/" + repo + "/actions/workflows/" + wf + "/runs?per_page=6", { headers });
    const j = await r.json();
    return (j.workflow_runs || []).some(x => x.status === "in_progress" || x.status === "queued" || x.status === "waiting" || x.status === "pending" || x.status === "requested");
  } catch (e) { return false; }
}

async function runSchedule(env, cron, go) {
  if (!env.GH_TOKEN) return { ok: false, note: "no GH_TOKEN secret on the worker — the scheduler is off" };
  const feed = /^(\*\/|0,10,20)/.test(cron || "");
  if (feed) {
    const busy = await ghBusy(env, "quotes.yml");
    if (!go) return { ok: true, would: "dispatch quotes.yml" + (busy ? " (a feed loop is already running — skip)" : ""), cron };
    if (busy) return { ok: true, did: "skip — a feed loop is already running", cron };
    const st = await ghDispatch(env, "quotes.yml", { minutes: "10" });
    return { ok: st === 204, did: "dispatch quotes.yml → " + st, cron };
  }
  const busy = await ghBusy(env, "daily-update.yml");
  if (!go) return { ok: true, would: "dispatch daily-update.yml" + (busy ? " (a pass is already running or queued — skip)" : ""), cron };
  if (busy) return { ok: true, did: "skip — a pass is already running or queued", cron };
  const st = await ghDispatch(env, "daily-update.yml", { reason: "worker" });
  return { ok: st === 204, did: "dispatch daily-update.yml → " + st, cron };
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runSchedule(env, event.cron, true));
  },
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const url = new URL(request.url);
    const p = url.pathname;
    try {
      if (p === "/health") return new Response("ok", { headers: CORS });
      if (p === "/cron") {
        const go = url.searchParams.get("go") === "1";
        if (go && env && env.CRON_KEY && url.searchParams.get("key") !== env.CRON_KEY) return new Response("forbidden (set ?key=…)", { status: 403, headers: CORS });
        const out = await runSchedule(env || {}, url.searchParams.get("cron") || "37 2-14 * * 1-5", go);
        return new Response(JSON.stringify(out), { headers: Object.assign({ "content-type": "application/json" }, CORS) });
      }
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
