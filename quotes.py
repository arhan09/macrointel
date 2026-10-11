#!/usr/bin/env python3
"""v141.2 · THE QUOTES FILE — the floor under real time. Every five minutes in the session the
"Live quotes" workflow runs this: one batched Yahoo download for every name the page moves
(the strip, the fifty, the names the books hold, the five, the most traded), written to
quotes.json and force-pushed to the repo's `live` branch (one commit, no history), where the
page reads it over CORS from raw.githubusercontent.com. No key, no secret, no server.

    python quotes.py            # writes quotes.json beside the page

Nothing here touches the page or the ledger; a failed run leaves the last file in place."""
import json, os, re, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "macro_intelligence_terminal.html")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STRIP = ["^NSEI", "^BSESN", "^NSEBANK", "^INDIAVIX", "NIFTY_MIDCAP_100.NS", "INR=X", "DX-Y.NYB", "EURUSD=X", "JPY=X",
         "BZ=F", "CL=F", "NG=F", "GC=F", "SI=F", "^GSPC", "^NDX", "^DJI"]


def _blk(html, var):
    m = re.search(r"window\.%s\s*=\s*(\{.*?\});" % re.escape(var), html, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def symbols():
    syms = list(STRIP)
    html = ""
    try:
        html = open(HTML, encoding="utf-8").read()
    except Exception:
        pass
    if html:
        m = re.search(r"const YSYM=(\{.*?\});", html)
        if m:
            try:
                syms += list(json.loads(m.group(1)).values())
            except Exception:
                pass
        mv = _blk(html, "MOVERS_LIVE").get("all") or {}
        top = sorted(mv.items(), key=lambda kv: -(kv[1][2] or 0) if isinstance(kv[1], list) and len(kv[1]) > 2 and kv[1][2] is not None else 0)[:60]
        syms += [k + ".NS" for k, _ in top]
    try:
        A = json.load(open(os.path.join(HERE, "history", "agents_latest.json"), encoding="utf-8"))
        for ag in (A.get("agents") or {}).values():
            for p in ag.get("positions") or []:
                syms.append(str(p.get("key") or p.get("name")).upper().replace(".NS", "") + ".NS")
    except Exception:
        pass
    try:
        fs = json.load(open(os.path.join(HERE, "fno_setups.json"), encoding="utf-8"))
        for x in ((fs.get("page_state") or {}).get("watch") or {}).get("top") or []:
            if x.get("sym"):
                syms.append(str(x["sym"]).upper() + ".NS")
        for r in fs.get("rows") or []:
            if r.get("sym"):
                syms.append(str(r["sym"]).upper() + ".NS")
    except Exception:
        pass
    out, seen = [], set()
    for s in syms:
        s = str(s).strip()
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out[:240]


def main():
    try:
        import yfinance as yf
        import pandas as pd
    except Exception as e:
        print("quotes: yfinance unavailable (%s)" % type(e).__name__); return 0
    syms = symbols()
    q = {}
    try:
        df = yf.download(syms, period="5d", interval="1d", group_by="ticker", threads=True, progress=False, auto_adjust=False)
    except Exception as e:
        print("quotes: download failed (%s: %s)" % (type(e).__name__, e)); return 0
    for s in syms:
        try:
            ser = df[s]["Close"] if len(syms) > 1 else df["Close"]
            ser = ser.dropna()
            if len(ser) < 1:
                continue
            last = float(ser.iloc[-1]); prev = float(ser.iloc[-2]) if len(ser) > 1 else None
            q[s] = {"p": round(last, 4 if last < 10 else 2), "prev": (round(prev, 4 if prev < 10 else 2) if prev else None),
                    "d": (round((last / prev - 1) * 100, 2) if prev else None), "t": ser.index[-1].strftime("%Y-%m-%d")}
        except Exception:
            continue
    if not q:
        print("quotes: nothing came back — the last file stays"); return 0
    now = dt.datetime.now(IST)
    out = {"asof": now.strftime("%a %d %b %Y %H:%M IST"), "ts": int(now.timestamp()), "n": len(q), "src": "Yahoo Finance via yfinance, batched", "q": q}
    json.dump(out, open(os.path.join(HERE, "quotes.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print("quotes: %d of %d names · %s" % (len(q), len(syms), out["asof"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
