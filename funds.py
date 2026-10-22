#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MacroIntel v147 · THE FUNDS — every open-ended Direct-Growth scheme by AMFI category, from AMFI's own NAVs.

    python funds.py --budget 120      # one pass: the universe (once a day), ~200 schemes' NAV history refreshed, the table
    python funds.py --offline         # no network: the cache only

Sources (free, keyless): AMFI's NAVAll.txt for the universe and the categories; mfapi.in (AMFI's numbers per scheme,
full NAV history as JSON) for the history, on a rotation like the company profiles — ~200 schemes a pass, every
scheme fresh within a week. Writes:
  funds.json          the table: every scheme with its returns, risk, consistency, DNA, regime fit, score and word
  funds_series.json   weekly NAVs (3 years) for the charts, by scheme code
  funds_cache.json    the raw weekly history + the last daily NAV (committed; the rotation's memory)
  funds_universe.json the AMFI universe (committed; refreshed once a day)
What a fund gets that nobody gives it: its macro DNA (betas to the Nifty, the rupee, Brent, rates, VIX — the same
ridge as every share), its record in each regime, and the shock simulator.
"""
import json, os, re, sys, time, math, datetime as dt
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as EN   # the factor frame, the ridge, the regime path, the price cache — one method for shares and funds

VERSION = "v147"
UNIVERSE_FILE = "funds_universe.json"
CACHE_FILE = "funds_cache.json"
OUT = "funds.json"
SERIES = "funds_series.json"
NAVALL = "https://www.amfiindia.com/spages/NAVAll.txt"
MFAPI = "https://api.mfapi.in/mf/%s"
MFAPI_ALL = "https://api.mfapi.in/mf"
IST = EN.IST
LOG = []

CATS = [  # (substring of AMFI's category header, our label, class)
    ("Large & Mid", "Large & mid cap", "Equity"), ("Large Cap", "Large cap", "Equity"), ("Mid Cap", "Mid cap", "Equity"), ("Small Cap", "Small cap", "Equity"),
    ("Flexi Cap", "Flexi cap", "Equity"), ("Multi Cap", "Multi cap", "Equity"), ("ELSS", "ELSS (tax saver)", "Equity"), ("Focused", "Focused", "Equity"),
    ("Value", "Value / contra", "Equity"), ("Contra", "Value / contra", "Equity"), ("Dividend Yield", "Dividend yield", "Equity"),
    ("Sectoral", "Sectoral / thematic", "Equity"), ("Thematic", "Sectoral / thematic", "Equity"),
    ("Index Fund", "Index fund", "Index"), ("Other Scheme - Index", "Index fund", "Index"),
    ("FoF Overseas", "International (FoF)", "Global"), ("Fund of Funds", "Fund of funds", "Global"),
    ("Aggressive Hybrid", "Aggressive hybrid", "Hybrid"), ("Balanced Advantage", "Balanced advantage", "Hybrid"), ("Dynamic Asset", "Balanced advantage", "Hybrid"),
    ("Conservative Hybrid", "Conservative hybrid", "Hybrid"), ("Arbitrage", "Arbitrage", "Hybrid"), ("Equity Savings", "Equity savings", "Hybrid"), ("Multi Asset", "Multi asset", "Hybrid"),
    ("Overnight", "Overnight", "Debt"), ("Liquid", "Liquid", "Debt"), ("Money Market", "Money market", "Debt"), ("Ultra Short", "Ultra short / low duration", "Debt"),
    ("Low Duration", "Ultra short / low duration", "Debt"), ("Short Duration", "Short duration", "Debt"), ("Corporate Bond", "Corporate bond", "Debt"),
    ("Banking and PSU", "Banking & PSU", "Debt"), ("Gilt", "Gilt", "Debt"), ("Dynamic Bond", "Dynamic bond", "Debt"), ("Credit Risk", "Credit risk", "Debt"),
    ("Medium Duration", "Medium duration", "Debt"), ("Medium to Long", "Medium duration", "Debt"), ("Long Duration", "Long duration", "Debt"), ("Floater", "Floater", "Debt"),
    ("Gold", "Gold (FoF)", "Commodity"), ("Silver", "Silver (FoF)", "Commodity"),
]
SKIP = ("ETF", "Close Ended", "Interval", "Solution Oriented", "Retirement", "Children")


def log(m):
    print("  " + m); LOG.append(m)


def _f(x, nd=2):
    return EN._f(x, nd)


def _get(url, timeout=30):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MacroIntel funds)", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def category_of(header):
    h = header or ""
    if any(k in h for k in SKIP):
        return None, None
    for key, lab, cls in CATS:
        if key.lower() in h.lower():
            return lab, cls
    return None, None


def wanted(name):
    n = (name or "").lower()
    return ("direct" in n) and ("growth" in n) and not any(x in n for x in ("idcw", "dividend", "bonus", "payout", "reinvest", "regular", "- dir -", "segregated"))


# ─────────────────────────────────────────────────────────────────────────────
# 1 · the universe — AMFI's file, once a day
# ─────────────────────────────────────────────────────────────────────────────
def load_universe():
    try:
        return json.load(open(UNIVERSE_FILE))
    except Exception:
        return None


def fetch_universe(offline):
    U = load_universe()
    if U:
        try:
            age = (EN.now_ist() - dt.datetime.strptime(U["updated"], "%Y-%m-%d %H:%M").replace(tzinfo=IST)).total_seconds() / 3600
        except Exception:
            age = 999
        if offline or age < 20:
            return U, "cache · %s" % U["updated"]
    if offline:
        return U, "none (offline)"
    try:
        txt = _get(NAVALL, timeout=60)
    except Exception as e:
        log("AMFI NAVAll.txt unreachable (%s) — the universe is carried" % type(e).__name__)
        return U, ("cache (stale)" if U else "none")
    schemes = []; cat = cls = None; amc = ""
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("Open Ended Schemes") or ln.startswith("Close Ended") or ln.startswith("Interval"):
            cat, cls = category_of(ln)
            continue
        if ";" not in ln:
            if not ln.startswith("Scheme Code"):
                amc = ln
            continue
        p = ln.split(";")
        if len(p) < 6 or not p[0].isdigit():
            continue
        code, name, nav, date = p[0], p[3].strip(), p[4].strip(), p[5].strip()
        if not cat or not wanted(name):
            continue
        try:
            navf = float(nav)
        except Exception:
            continue
        schemes.append({"code": code, "nm": name, "cat": cat, "cls": cls, "amc": amc, "nav": navf, "date": date})
    if len(schemes) < 200:
        log("AMFI file parsed to only %d schemes — carrying the old universe" % len(schemes))
        return U, ("cache (stale)" if U else "none")
    U = {"updated": EN.now_ist().strftime("%Y-%m-%d %H:%M"), "n": len(schemes), "schemes": schemes}
    json.dump(U, open(UNIVERSE_FILE, "w"), separators=(",", ":"))
    return U, "AMFI · %d Direct-Growth schemes" % len(schemes)


# ─────────────────────────────────────────────────────────────────────────────
# 2 · the history — mfapi.in on a rotation
# ─────────────────────────────────────────────────────────────────────────────
def load_cache():
    try:
        return json.load(open(CACHE_FILE))
    except Exception:
        return {"updated": None, "schemes": {}}


def refresh_history(U, C, budget, offline):
    if offline or budget <= 0 or not U:
        return C, 0
    today = EN.now_ist().strftime("%Y-%m-%d")
    S = C.setdefault("schemes", {})

    def age(code):
        a = (S.get(code) or {}).get("asof")
        if not a:
            return 10 ** 6
        try:
            return (pd.Timestamp(today) - pd.Timestamp(a)).days
        except Exception:
            return 10 ** 6
    order = sorted([x for x in U["schemes"] if age(x["code"]) >= 6], key=lambda x: -age(x["code"]))
    t0 = time.time(); n = 0
    for x in order:
        if time.time() - t0 > budget:
            break
        code = x["code"]
        try:
            j = json.loads(_get(MFAPI % code, timeout=20))
            rows = j.get("data") or []
            if len(rows) < 30:
                S.setdefault(code, {})["asof"] = today; S[code]["thin"] = True
                continue
            ser = pd.Series({pd.to_datetime(r["date"], format="%d-%m-%Y"): float(r["nav"]) for r in rows if r.get("nav") not in (None, "", "0", "0.0")}).sort_index()
            ser = ser[ser > 0]
            wk = ser.resample("W-FRI").last().dropna()
            wk = wk[wk.index >= wk.index[-1] - pd.Timedelta(weeks=260)]      # five years at most
            S[code] = {"nm": x["nm"], "cat": x["cat"], "cls": x["cls"], "amc": x["amc"], "asof": today,
                       "dates": [d.strftime("%Y%m%d") for d in wk.index], "nav": [round(float(v), 4) for v in wk.values],
                       "last": {"date": ser.index[-1].strftime("%Y-%m-%d"), "nav": round(float(ser.iloc[-1]), 4)},
                       "since": ser.index[0].strftime("%Y-%m-%d"), "n_daily": int(len(ser))}
            n += 1
        except Exception as e:
            S.setdefault(code, {})["asof"] = today; S[code]["err"] = type(e).__name__
    C["updated"] = EN.now_ist().strftime("%Y-%m-%d %H:%M")
    try:
        json.dump(C, open(CACHE_FILE, "w"), separators=(",", ":"))
    except Exception as e:
        log("funds cache not written (%s)" % type(e).__name__)
    return C, n


# ─────────────────────────────────────────────────────────────────────────────
# 3 · the table
# ─────────────────────────────────────────────────────────────────────────────
def factor_frame():
    """the engine's weekly factor frame (3y online from the price cache; the page's year offline)"""
    try:
        W, D, src = EN.load_prices_cache()
        if W is None:
            W, D, src = EN.load_page_history()
        F = EN.factor_frame(W)
        return F, src
    except Exception as e:
        return None, "no factors (%s)" % type(e).__name__


def metrics(code, rec, F, labels, repo):
    dates = pd.to_datetime(rec["dates"], format="%Y%m%d"); nav = pd.Series(rec["nav"], index=dates).astype(float)
    nav = nav[nav > 0]
    if len(nav) < 30:
        return None
    last = float(nav.iloc[-1])

    def ret(w):
        return _f((last / float(nav.iloc[-1 - w]) - 1) * 100) if len(nav) > w else None
    r = nav.pct_change().dropna()
    yrs = min(3.0, (nav.index[-1] - nav.index[0]).days / 365.25)
    r3y = _f(((last / float(nav.iloc[max(0, len(nav) - 157)])) ** (1 / max(yrs, 0.5)) - 1) * 100) if len(nav) >= 60 else None
    vol = _f(float(r.tail(52).std()) * math.sqrt(52) * 100) if len(r) >= 26 else None
    dd = None
    if len(nav) >= 26:
        w = nav.tail(52); dd = _f(float((w / w.cummax() - 1).min()) * 100)
    r1y = ret(52)
    sharpe = _f((r1y - repo) / vol, 2) if (r1y is not None and vol) else None
    m = {"nav": _f(last, 4), "r1m": ret(4), "r3m": ret(13), "r6m": ret(26), "r1y": r1y, "r3y": r3y, "vol": vol, "dd": dd, "sharpe": sharpe, "weeks": int(len(nav))}
    # DNA: the same ridge as every share, on weekly returns against the factor frame
    if F is not None and len(r) >= 40:
        try:
            df = pd.concat([(r * 100).rename("y"), F], axis=1, join="inner").dropna()
            if len(df) >= 40:
                b, t, r2 = EN.ridge(df["y"].values, df[[c for c in F.columns]].values)
                m["dna"] = {"b": {k: _f(v, 3) for k, v in zip(F.columns, b)}, "t": {k: _f(v, 1) for k, v in zip(F.columns, t)}, "r2": _f(r2, 2), "n": int(len(df))}
        except Exception:
            pass
    # the record by regime: average weekly return, annualised, in each regime (vs the fund's own mean)
    if labels is not None and len(r) >= 52:
        try:
            lab = labels.reindex(r.index); rec_ = {}
            for R in EN.REGIMES:
                mm = (lab == R)
                if int(mm.sum()) >= 12:
                    rec_[R] = {"ann": _f(float(r[mm].mean()) * 52 * 100, 1), "n": int(mm.sum()), "hit": _f(100 * float((r[mm] > 0).mean()), 0)}
            if rec_:
                m["regime"] = rec_
        except Exception:
            pass
    return m


def build_table(U, C, repo, regime):
    F, fsrc = factor_frame()
    labels = None
    try:
        if F is not None:
            labels = EN.regime_labels(F.index)
    except Exception:
        labels = None
    S = C.get("schemes") or {}
    rows = []
    for x in (U or {}).get("schemes") or []:
        rec = S.get(x["code"])
        if not rec or not rec.get("nav"):
            rows.append({"code": x["code"], "nm": x["nm"], "cat": x["cat"], "cls": x["cls"], "amc": x["amc"], "nav": x.get("nav"), "date": x.get("date"), "pending": True})
            continue
        m = metrics(x["code"], rec, F, labels, repo)
        if not m:
            continue
        row = {"code": x["code"], "nm": x["nm"], "cat": x["cat"], "cls": x["cls"], "amc": x["amc"], "date": (rec.get("last") or {}).get("date"), "since": rec.get("since")}
        row.update(m)
        rows.append(row)
    # within each category: the score, the word, the regime fit
    cats = {}
    for r in rows:
        cats.setdefault(r["cat"], []).append(r)
    out_cats = {}
    for cat, rs in cats.items():
        scored = [r for r in rs if not r.get("pending") and r.get("r1y") is not None]
        if not scored:
            out_cats[cat] = {"n": len(rs), "scored": 0, "cls": rs[0]["cls"], "rows": rs}
            continue
        def pct(key, sign=1):
            vals = [r[key] for r in scored if r.get(key) is not None]
            if len(vals) < 3:
                return {id(r): 50.0 for r in scored}
            srt = sorted(vals)
            out = {}
            for r in scored:
                v = r.get(key)
                out[id(r)] = 50.0 if v is None else 100.0 * (sum(1 for z in srt if (z < v if sign > 0 else z > v)) + 0.5 * sum(1 for z in srt if z == v)) / len(srt)
            return out
        p_sh, p_3, p_dd, p_1 = pct("sharpe"), pct("r3y"), pct("dd"), pct("r1y")
        med = {k: _f(float(np.median([r[k] for r in scored if r.get(k) is not None])), 2) for k in ("r1y", "r3y", "vol", "dd", "sharpe") if any(r.get(k) is not None for r in scored)}
        for r in scored:
            sc = 0.35 * p_sh[id(r)] + 0.30 * p_3[id(r)] + 0.20 * p_1[id(r)] + 0.15 * p_dd[id(r)]
            r["score"] = _f(sc, 0)
            r["vs_cat"] = {"r1y": (_f(r["r1y"] - med["r1y"]) if med.get("r1y") is not None and r.get("r1y") is not None else None),
                           "r3y": (_f(r["r3y"] - med["r3y"]) if med.get("r3y") is not None and r.get("r3y") is not None else None)}
            rg = (r.get("regime") or {}).get(regime)
            cat_r = [z["regime"][regime]["ann"] for z in scored if (z.get("regime") or {}).get(regime)]
            r["rfit"] = (_f(rg["ann"] - float(np.median(cat_r)), 1) if (rg and cat_r) else None)
        scored.sort(key=lambda r: -(r["score"] or 0))
        n = len(scored)
        for i, r in enumerate(scored):
            top = i < max(1, int(round(n * 0.2))); bot = i >= n - max(1, int(round(n * 0.2)))
            r["rank"] = i + 1
            r["word"] = "LEADER" if (top and (r.get("vs_cat") or {}).get("r3y", 0) is not None and (r["vs_cat"]["r3y"] or 0) >= 0) else ("LAGGARD" if bot else "STEADY")
            why = []
            if r.get("sharpe") is not None:
                why.append("1-year return per unit of risk %s (category median %s)" % (r["sharpe"], med.get("sharpe")))
            if r.get("r3y") is not None:
                why.append("3-year %s%% a year%s" % (r["r3y"], (" · %+.1f vs the category" % r["vs_cat"]["r3y"]) if r["vs_cat"].get("r3y") is not None else ""))
            if r.get("dd") is not None:
                why.append("worst 1-year drawdown %s%%" % r["dd"])
            if r.get("rfit") is not None:
                why.append("in %s: %+.1f%% a year against the category" % (regime, r["rfit"]))
            r["why"] = why
        out_cats[cat] = {"n": len(rs), "scored": n, "cls": rs[0]["cls"], "median": med, "rows": scored + [r for r in rs if r.get("pending") or r.get("r1y") is None],
                         "leaders": [r["code"] for r in scored[:5]], "laggards": [r["code"] for r in scored[-3:]]}
    return out_cats, fsrc


def main(argv):
    t0 = time.time()
    offline = "--offline" in argv or os.environ.get("MI_OFFLINE") == "1"
    budget = 120
    for i, a in enumerate(argv):
        if a == "--budget" and i + 1 < len(argv):
            budget = int(argv[i + 1])
    print("=== MacroIntel FUNDS %s · %s IST%s ===" % (VERSION, EN.now_ist().strftime("%a %b %d %H:%M"), " · offline" if offline else ""))
    try:
        B = EN.read_page()
        repo = float((B["MACRO_LIVE"] or {}).get("repo") or 5.5)
        regime = ((B["REGIME_LIVE"] or {}).get("quad") or "REFLATION").title()
    except Exception:
        repo, regime = 5.5, "Reflation"
    U, usrc = fetch_universe(offline)
    log("universe: %s" % usrc)
    C = load_cache()
    C, n_new = refresh_history(U, C, budget, offline)
    S = C.get("schemes") or {}
    n_hist = sum(1 for v in S.values() if v.get("nav"))
    log("history: %d schemes on file (%d refreshed this pass)" % (n_hist, n_new))
    cats, fsrc = build_table(U, C, repo, regime)
    n_rows = sum(c["scored"] for c in cats.values())
    out = {"version": VERSION, "generated": EN.now_ist().strftime("%a %b %d, %Y %H:%M IST"), "asof": EN.now_ist().strftime("%Y-%m-%d"), "regime": regime,
           "n_universe": len((U or {}).get("schemes") or []), "n_scored": n_rows, "n_pending": sum(1 for c in cats.values() for r in c["rows"] if r.get("pending")),
           "cats": cats, "index": {r["code"]: r["cat"] for c in cats.values() for r in c["rows"]},
           "how": {"score": "within each AMFI category, a percentile blend: 0.35 one-year return per unit of risk (Sharpe against the repo), 0.30 three-year CAGR, 0.20 one-year return, 0.15 the one-year drawdown; LEADER = the top fifth with a three-year record at or above the category, LAGGARD = the bottom fifth, STEADY the rest",
                   "dna": "weekly NAV returns against the Nifty, the rupee, Brent, rates and India VIX — the same ridge as every share (factors: %s)" % fsrc,
                   "regime": "the fund's average weekly return, annualised, in each regime of the CPI × IIP path; 'in this regime' is that figure against the category's median",
                   "source": "AMFI NAVAll.txt (the universe, Direct plans, Growth options, open-ended only) · mfapi.in (AMFI's NAV history per scheme) · refreshed on a rotation, every scheme within a week"},
           "log": LOG, "secs": _f(time.time() - t0, 1)}
    json.dump(out, open(OUT, "w"), separators=(",", ":"), default=str)
    # the weekly series for the charts (3 years)
    ser = {code: {"d": v["dates"][-156:], "v": v["nav"][-156:]} for code, v in S.items() if v.get("nav")}
    json.dump({"version": VERSION, "asof": out["asof"], "series": ser}, open(SERIES, "w"), separators=(",", ":"))
    log("table: %d categories · %d scored · %d pending · %.0f KB" % (len(cats), n_rows, out["n_pending"], os.path.getsize(OUT) / 1e3))
    print("  → wrote %s and %s in %.0fs" % (OUT, SERIES, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
