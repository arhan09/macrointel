"""v126 · Evaluate the F&O desk's setups exactly as the page computes them.

Loads the built terminal headless (the page's own JS, its own blocks, the
published history) and calls fnoSetupsForLedger(), so the ledger scores the
rule the desk showed — one source of truth, no Python re-implementation to
drift. Writes fno_setups.json. Needs: pip install playwright && python -m
playwright install chromium. Runs in the daily workflow right before
ml_models.py; on any failure it writes nothing and the ML pass carries on.
"""
import json, os, sys, threading, http.server, socketserver, datetime as dt
from functools import partial

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
PORT = int(os.environ.get("FNO_PORT", "8791"))
HTML = "macro_intelligence_terminal.html"

def serve():
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=HERE)
    handler.log_message = lambda *a, **k: None
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def main():
    if not os.path.exists(os.path.join(HERE, HTML)):
        print("fno_setups: no terminal html — nothing to evaluate"); return 0
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"fno_setups: playwright unavailable ({type(e).__name__}) — skipped"); return 0
    srv = serve()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1400, "height": 900})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{PORT}/{HTML}", wait_until="networkidle", timeout=120000)
            pg.wait_for_timeout(4000)
            out = pg.evaluate("() => (typeof fnoSetupsForLedger==='function') ? fnoSetupsForLedger() : null")
            b.close()
    finally:
        srv.shutdown()
    if not out:
        print("fno_setups: the page did not expose fnoSetupsForLedger — skipped"); return 0
    out["generated"] = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M UTC")
    out["page_errors"] = errs[:5]
    # the date the ledger keys on is IST
    out["date"] = (dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
    json.dump(out, open(os.path.join(HERE, "fno_setups.json"), "w"), indent=1)
    rows = out.get("rows") or []
    print(f"fno_setups: {len(rows)} setups ({sum(1 for r in rows if r['side']=='LONG')} long / "
          f"{sum(1 for r in rows if r['side']=='SHORT')} short) · gate {'ON' if out.get('gate') else 'off'} · "
          f"stance {out.get('stance')} · {out.get('n_futures')} futures scanned")
    return 0

if __name__ == "__main__":
    sys.exit(main())
