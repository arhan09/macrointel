/* MacroIntel · the live-quote door — a Cloudflare Worker, free tier, three minutes to set up.
   It forwards the page's Yahoo Finance requests with a CORS header so the browser can read
   them. No key, no secret, no data of yours; the URL is public and goes into a repository
   VARIABLE (not a secret) called MI_PROXY.

   1. dash.cloudflare.com → Workers & Pages → Create → "Hello World" worker → Edit code
   2. replace the code with this file → Deploy → copy the URL (https://<name>.<you>.workers.dev)
   3. GitHub → the repo → Settings → Secrets and variables → Actions → Variables → New repository variable
      name MI_PROXY · value https://<name>.<you>.workers.dev/?u=
   4. the next pipeline pass writes it into the page; the badge then reads "⚡ live … your worker". */
export default {
  async fetch(request) {
    const u = new URL(request.url).searchParams.get("u");
    if (!u || !/^https:\/\/(query1|query2)\.finance\.yahoo\.com\//.test(u)) {
      return new Response("only Yahoo Finance chart/spark URLs are forwarded", { status: 400, headers: { "access-control-allow-origin": "*" } });
    }
    const r = await fetch(u, { headers: { "user-agent": "Mozilla/5.0 (MacroIntel live door)" }, cf: { cacheTtl: 20, cacheEverything: true } });
    const h = new Headers();
    h.set("content-type", r.headers.get("content-type") || "application/json");
    h.set("access-control-allow-origin", "*");
    h.set("cache-control", "public, max-age=20");
    return new Response(r.body, { status: r.status, headers: h });
  }
};
