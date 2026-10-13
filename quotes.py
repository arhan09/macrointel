#!/usr/bin/env python3
"""v144 · THE FEED — real time without a server, and the arena's minute-by-minute stops. The "Live quotes" workflow runs this in a loop
during the session: every minute, one batched Yahoo download for every name the page moves (the
strip, the fifty, the names the books hold, the five, the most traded, the F&O table) plus the
session's five-minute bars for the index and the most traded, written to quotes.json and
intraday_live.json and force-pushed to the repo's `live` branch (one commit, no history), where
the page reads them over CORS from raw.githubusercontent.com. No key, no secret, no server.

    python quotes.py                 # one pass: writes quotes.json + intraday_live.json
    python quotes.py --loop 570      # loop for 570 s, a pass every 60 s, pushing each time
    python quotes.py --loop 570 --push <remote-url>   # push after each pass (the workflow does this)

Nothing here touches the page or the ledger; a failed pass leaves the last files in place."""
import json, os, re, sys, time, subprocess, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, "macro_intelligence_terminal.html")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STRIP = ["^NSEI", "^BSESN", "^NSEBANK", "^INDIAVIX", "NIFTY_MIDCAP_100.NS", "INR=X", "DX-Y.NYB", "EURUSD=X", "JPY=X",
         "BZ=F", "CL=F", "NG=F", "GC=F", "SI=F", "^GSPC", "^NDX", "^DJI"]
BARS_N = 70   # names that also get five-minute bars (the index, the strip's India legs, the most traded, the held)


def _blk(html, var):
    m = re.search(r"window\.%s\s*=\s*(\{.*?\});" % re.escape(var), html, re.S)
    try:
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def symbols():
    syms = list(STRIP); bars = ["^NSEI", "^BSESN", "^NSEBANK", "^INDIAVIX", "INR=X"]
    html = ""
    try:
        html = open(HTML, encoding="utf-8").read()
    except Exception:
        pass
    if html:
        m = re.search(r"const YSYM=(\{.*?\});", html)
        if m:
            try:
                ys = list(json.loads(m.group(1)).values()); syms += ys; bars += ys[:20]
            except Exception:
                pass
        mv = _blk(html, "MOVERS_LIVE").get("all") or {}
        top = sorted(mv.items(), key=lambda kv: -(kv[1][2] or 0) if isinstance(kv[1], list) and len(kv[1]) > 2 and kv[1][2] is not None else 0)[:80]
        syms += [k + ".NS" for k, _ in top]; bars += [k + ".NS" for k, _ in top[:30]]
        fn = _blk(html, "FNO_LIVE").get("stocks") or []
        syms += [str(r.get("s")).upper() + ".NS" for r in fn if r.get("s")]
    # v144 · the engine's picks and every liquid name on the Markets tab (top 400 by turnover) ride the feed
    try:
        eng = json.load(open(os.path.join(HERE, "engine.json"), encoding="utf-8"))
        for lst in (eng.get("picks") or {}).values():
            for p in lst or []:
                if p.get("sym"):
                    s_ = str(p["sym"]).upper() + ".NS"; syms.append(s_); bars.append(s_)
        N = eng.get("names") or {}
        liq = sorted([k for k, v in N.items() if not v.get("x") and (v.get("turn") or 0) >= 40], key=lambda k: -(N[k].get("turn") or 0))[:400]
        syms += [k + ".NS" for k in liq]
    except Exception:
        pass
    try:
        A = json.load(open(os.path.join(HERE, "history", "agents_latest.json"), encoding="utf-8"))
        for ag in (A.get("agents") or {}).values():
            for p in ag.get("positions") or []:
                s = str(p.get("key") or p.get("name")).upper().replace(".NS", "") + ".NS"; syms.append(s); bars.append(s)
    except Exception:
        pass
    try:
        fs = json.load(open(os.path.join(HERE, "fno_setups.json"), encoding="utf-8"))
        for x in ((fs.get("page_state") or {}).get("watch") or {}).get("top") or []:
            if x.get("sym"):
                s = str(x["sym"]).upper() + ".NS"; syms.append(s); bars.append(s)
        for r in fs.get("rows") or []:
            if r.get("sym"):
                syms.append(str(r["sym"]).upper() + ".NS")
    except Exception:
        pass
    def uniq(a, cap):
        out, seen = [], set()
        for s in a:
            s = str(s).strip()
            if s and s not in seen:
                seen.add(s); out.append(s)
        return out[:cap]
    return uniq(syms, 400), uniq(bars, BARS_N)


def one_pass(syms, bars):
    import yfinance as yf
    import pandas as pd
    now = dt.datetime.now(IST)
    q = {}
    try:
        df = yf.download(syms, period="5d", interval="1d", group_by="ticker", threads=True, progress=False, auto_adjust=False)
        for s in syms:
            try:
                ser = (df[s]["Close"] if len(syms) > 1 else df["Close"]).dropna()
                if len(ser) < 1:
                    continue
                last = float(ser.iloc[-1]); prev = float(ser.iloc[-2]) if len(ser) > 1 else None
                q[s] = {"p": round(last, 4 if last < 10 else 2), "prev": (round(prev, 4 if prev < 10 else 2) if prev else None),
                        "d": (round((last / prev - 1) * 100, 2) if prev else None), "t": ser.index[-1].strftime("%Y-%m-%d")}
            except Exception:
                continue
    except Exception as e:
        print("quotes: download failed (%s: %s)" % (type(e).__name__, e))
    if q:
        out = {"asof": now.strftime("%a %d %b %Y %H:%M IST"), "ts": int(now.timestamp()), "n": len(q), "src": "Yahoo Finance via yfinance, batched every minute of the session", "q": q}
        json.dump(out, open(os.path.join(HERE, "quotes.json"), "w", encoding="utf-8"), separators=(",", ":"))
    # the session's five-minute bars for the names that get a chart
    series, prev = {}, {}
    try:
        db = yf.download(bars, period="1d", interval="5m", group_by="ticker", threads=True, progress=False, auto_adjust=False)
        for s in bars:
            try:
                ser = (db[s]["Close"] if len(bars) > 1 else db["Close"]).dropna()
                if len(ser) < 2:
                    continue
                series[s] = [[int(t.timestamp()), round(float(v), 2)] for t, v in ser.items()]
                if s in q and q[s].get("prev") is not None:
                    prev[s] = q[s]["prev"]
            except Exception:
                continue
    except Exception as e:
        print("bars: download failed (%s: %s)" % (type(e).__name__, e))
    if series:
        json.dump({"asof": now.strftime("%a %d %b %Y %H:%M IST"), "ts": int(now.timestamp()), "date": now.strftime("%Y-%m-%d"), "n": len(series), "series": series, "prev": prev},
                  open(os.path.join(HERE, "intraday_live.json"), "w", encoding="utf-8"), separators=(",", ":"))
    print("feed: %d quotes · %d bar series · %s" % (len(q), len(series), now.strftime("%H:%M:%S IST")))
    try:
        if q:
            agents_tick(q, now)
    except Exception as e:
        print("agents tick: skipped (%s)" % type(e).__name__)
    return bool(q)


def agents_tick(q, now):
    """v143 · between passes the arena's open positions are ticked against the minute's quotes: a stop or a target
    that prints is recorded here (agents_live.json on the live branch) with its minute and its reason, and the next
    pipeline pass closes the position at that price. Reads history/agents_latest.json from the checkout; never writes it."""
    # v144 · the engine's picks and every liquid name on the Markets tab (top 400 by turnover) ride the feed
    try:
        eng = json.load(open(os.path.join(HERE, "engine.json"), encoding="utf-8"))
        for lst in (eng.get("picks") or {}).values():
            for p in lst or []:
                if p.get("sym"):
                    s_ = str(p["sym"]).upper() + ".NS"; syms.append(s_); bars.append(s_)
        N = eng.get("names") or {}
        liq = sorted([k for k, v in N.items() if not v.get("x") and (v.get("turn") or 0) >= 40], key=lambda k: -(N[k].get("turn") or 0))[:400]
        syms += [k + ".NS" for k in liq]
    except Exception:
        pass
    try:
        A = json.load(open(os.path.join(HERE, "history", "agents_latest.json"), encoding="utf-8"))
    except Exception:
        return None
    base = str(A.get("generated") or "")
    out_p = os.path.join(HERE, "agents_live.json")
    LX = {"base": base, "exits": []}
    try:
        old = json.load(open(out_p, encoding="utf-8"))
        if str(old.get("base") or "") == base:
            LX = old
    except Exception:
        pass
    done = {(x.get("agent"), x.get("key"), x.get("entry_at")) for x in (LX.get("exits") or [])}
    hhmm = now.strftime("%H:%M"); today = now.strftime("%Y-%m-%d"); n_new = 0; marks = {}
    for k, ag in (A.get("agents") or {}).items():
        for p in (ag.get("positions") or []):
            key = str(p.get("key") or p.get("name") or "").upper().replace(".NS", "")
            qq = q.get(key + ".NS")
            if not qq or qq.get("p") is None:
                continue
            px = float(qq["p"]); sg = 1 if p.get("side") == "LONG" else -1
            marks[k + ":" + key] = px
            if (k, p.get("key"), p.get("entry_at")) in done:
                continue
            why = None
            if p.get("stop") is not None and ((sg > 0 and px <= float(p["stop"])) or (sg < 0 and px >= float(p["stop"]))):
                why = "the stop at ₹%s printed on the feed at %s" % (format(float(p["stop"]), ",.2f"), hhmm)
            elif p.get("target") is not None and ((sg > 0 and px >= float(p["target"])) or (sg < 0 and px <= float(p["target"]))):
                why = "the target at ₹%s printed on the feed at %s" % (format(float(p["target"]), ",.2f"), hhmm)
            if why:
                LX["exits"].append({"agent": k, "nm": ag.get("nm"), "key": p.get("key"), "name": p.get("name"), "side": p.get("side"), "entry": p.get("entry"), "entry_at": p.get("entry_at"), "qty": p.get("qty"),
                                    "px": round(px, 2), "at": hhmm, "date": today, "why": why, "ret_pct": round(sg * (px / float(p["entry"]) - 1) * 100, 2)})
                n_new += 1
    LX.update({"asof": now.strftime("%a %d %b %Y %H:%M IST"), "ts": int(now.timestamp()), "n": len(LX["exits"]), "marks": marks, "n_marked": len(marks)})
    json.dump(LX, open(out_p, "w", encoding="utf-8"), separators=(",", ":"))
    if n_new:
        print("agents: %d exit%s printed on the feed at %s" % (n_new, "" if n_new == 1 else "s", hhmm))
    return LX


def push(remote):
    """quotes.json + intraday_live.json → the orphan live branch, one commit, force-pushed"""
    try:
        d = "/tmp/mi_live"
        subprocess.run(["rm", "-rf", d]); os.makedirs(d, exist_ok=True)
        for f in ("quotes.json", "intraday_live.json", "agents_live.json"):
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                subprocess.run(["cp", p, d])
        env = dict(os.environ, GIT_AUTHOR_NAME="macrointel-bot", GIT_AUTHOR_EMAIL="bot@users.noreply.github.com",
                   GIT_COMMITTER_NAME="macrointel-bot", GIT_COMMITTER_EMAIL="bot@users.noreply.github.com")
        subprocess.run(["git", "init", "-q"], cwd=d, env=env, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", "live"], cwd=d, env=env, check=True)
        subprocess.run(["git", "add", "."], cwd=d, env=env, check=True)
        subprocess.run(["git", "commit", "-qm", "feed %s" % dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")], cwd=d, env=env, check=True)
        r = subprocess.run(["git", "push", "-f", "-q", remote, "live"], cwd=d, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print("push failed:", (r.stderr or "")[-300:].replace(remote, "<remote>"))
            return False
        return True
    except Exception as e:
        print("push error: %s" % type(e).__name__)
        return False


def main():
    args = sys.argv[1:]
    loop = int(args[args.index("--loop") + 1]) if "--loop" in args else 0
    remote = args[args.index("--push") + 1] if "--push" in args else None
    try:
        import yfinance  # noqa
    except Exception as e:
        print("quotes: yfinance unavailable (%s)" % type(e).__name__); return 0
    syms, bars = symbols()
    print("feed: %d names, %d with bars" % (len(syms), len(bars)))
    t0 = time.time(); n = 0
    while True:
        t1 = time.time()
        ok = one_pass(syms, bars)
        if ok and remote:
            push(remote)
        n += 1
        if not loop or time.time() - t0 + 60 > loop:
            break
        time.sleep(max(5, 60 - (time.time() - t1)))
    print("feed: %d pass%s" % (n, "" if n == 1 else "es"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
