#!/usr/bin/env python3
"""
================================================================================
 MACRO INTELLIGENCE TERMINAL  ·  DAILY AUTO-UPDATER
================================================================================
Fetches live market data (Yahoo Finance via yfinance) and patches the data
objects inside macro_intelligence_terminal.html in place, then stamps the
update time. Because the terminal's back-engine reads the ENERGY / FX / IN_IDX
objects live in the browser, refreshing those objects automatically re-runs the
regime model — no separate model step is needed.

--------------------------------------------------------------------------------
 WHAT IT UPDATES (price-type data, fully automatic)
   • IN_IDX   — Nifty / Sensex / Bank Nifty
   • FX       — USD/INR, DXY, EUR/USD, GBP/USD, USD/JPY
   • ENERGY   — Brent, WTI, Natural Gas
   • PREC     — Gold, Silver, Platinum, Palladium
   • IDX      — S&P 500, Nasdaq 100, Dow, Russell, Nikkei
   • CRYPTO   — Bitcoin, Ethereum
   • IN_STK   — Indian large-caps (prices + daily %)
   • sparkline tails + the header "Data:" timestamp

 WHAT IT DOES NOT TOUCH (needs human / Claude judgement)
   • News items, AI commentary, trade verdicts, conviction scores
   • CPI / IIP / GDP prints, RBI / Fed decisions, regime narrative
   For those, run a Claude pass on the file (see DATA_SOURCES.md).
--------------------------------------------------------------------------------
 USAGE
   pip install yfinance
   python update_terminal.py macro_intelligence_terminal.html

 The script writes the result back to the SAME file (in place) so the deploy
 step can publish it directly. A timestamped copy is also written to ./history/.
================================================================================
"""

import sys
import re
import os
import json
import datetime as dt
import urllib.request
import urllib.error

try:
    import yfinance as yf
except ImportError:
    sys.exit("ERROR: pip install yfinance")

# ── Yahoo Finance ticker map ────────────────────────────────────────────────
MARKET = {
    # India indices
    "Nifty 50": "^NSEI", "BSE Sensex": "^BSESN", "Bank Nifty": "^NSEBANK",
    "Midcap 100": "NIFTY_MIDCAP_100.NS",
    # FX
    "USD/INR": "INR=X", "DXY": "DX-Y.NYB", "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X", "AUD/USD": "AUDUSD=X",
    # Commodities
    "Brent Oil": "BZ=F", "WTI Oil": "CL=F", "Nat Gas": "NG=F",
    "Gold": "GC=F", "Silver": "SI=F", "Platinum": "PL=F", "Palladium": "PA=F",
    # US indices
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI",
    "Russell 2000": "^RUT", "Nikkei 225": "^N225", "VIX": "^VIX",
    # Crypto
    "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD",
    "India VIX": "^INDIAVIX", "Copper": "HG=F", "Nifty IT": "^CNXIT",
    "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA",
}

# Indian large-caps in the IN_STK table  (name -> NSE Yahoo symbol)
STOCKS = {
    "Reliance": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS", "ICICI Bank": "ICICIBANK.NS", "Airtel": "BHARTIARTL.NS",
    "ITC": "ITC.NS", "SBI": "SBIN.NS", "HUL": "HINDUNILVR.NS", "L&T": "LT.NS",
    "Adani Ports": "ADANIPORTS.NS", "Wipro": "WIPRO.NS", "Maruti": "MARUTI.NS",
    "Titan": "TITAN.NS", "Coal India": "COALINDIA.NS", "HCL Tech": "HCLTECH.NS",
    "Sun Pharma": "SUNPHARMA.NS", "Tata Steel": "TATASTEEL.NS",
    "Bajaj Fin": "BAJFINANCE.NS", "Axis Bank": "AXISBANK.NS",
    "Nestle India": "NESTLEIND.NS", "Kotak Bank": "KOTAKBANK.NS",
    "Apollo Hospitals": "APOLLOHOSP.NS", "Federal Bank": "FEDERALBNK.NS",
    "Zydus Life": "ZYDUSLIFE.NS", "NTPC": "NTPC.NS",
    "Adani Ent": "ADANIENT.NS", "IndiGo": "INDIGO.NS", "DLF": "DLF.NS",
    "Cipla": "CIPLA.NS", "Dr Reddys": "DRREDDY.NS", "JSW Steel": "JSWSTEEL.NS", "Persistent": "PERSISTENT.NS", "M&M": "M&M.NS", "Bharti Airtel": "BHARTIARTL.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "BPCL": "BPCL.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "Britannia": "BRITANNIA.NS",
    "Divis Labs": "DIVISLAB.NS",
    "Eicher Motors": "EICHERMOT.NS",
    "Eternal": "ETERNAL.NS",
    "Grasim": "GRASIM.NS",
    "HDFC Life": "HDFCLIFE.NS",
    "Hero Moto": "HEROMOTOCO.NS",
    "Hindalco": "HINDALCO.NS",
    "IndusInd Bank": "INDUSINDBK.NS",
    "M&M": "M&M.NS",
    "ONGC": "ONGC.NS",
    "Power Grid": "POWERGRID.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Tech Mahindra": "TECHM.NS",
    "UltraTech": "ULTRACEMCO.NS",
}


def fetch(symbols):
    """Return {name: (last, day_pct, month_pct)} from ~2 months of history.

    v88: BATCH download first — the exact code path ml_models.py uses, which
    has kept working in CI while the old per-ticker Ticker().history() loop
    (~90 sequential calls) started failing. Per-ticker remains only as a
    fallback for symbols the batch missed."""
    out = {}

    def _pack(s):
        s = s.dropna()
        if len(s) < 2:
            return None
        last, prev = float(s.iloc[-1]), float(s.iloc[-2])
        mago = float(s.iloc[-22]) if len(s) >= 22 else float(s.iloc[0])
        return (round(last, 2), round((last / prev - 1) * 100, 2),
                round((last / mago - 1) * 100, 2))

    try:
        df = yf.download(list(symbols.values()), period="2mo", interval="1d",
                         auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if hasattr(df.columns, "levels") else df[["Close"]]
        for name, sym in symbols.items():
            try:
                if sym in close.columns:
                    v = _pack(close[sym])
                    if v:
                        out[name] = v
            except Exception:
                pass
    except Exception as exc:
        print(f"  batch fetch failed ({type(exc).__name__}) — per-ticker fallback")

    for name, sym in symbols.items():
        if name in out:
            continue
        try:
            hist = yf.Ticker(sym).history(period="2mo")["Close"]
            v = _pack(hist)
            if v:
                out[name] = v
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {name} ({sym}): {type(exc).__name__}")
    return out


def patch_obj(html, var, data):
    """Update p/d/m fields for matching keys inside `const VAR={...};`."""
    m = re.search(r"const " + var + r"=\{(.*?)\};", html, re.DOTALL)
    if not m:
        return html, 0
    body = m.group(1)
    n = 0
    for name, (p, d, mo) in data.items():
        pat = r'("' + re.escape(name) + r'":\{p:)[\d.]+(,d:)[-\d.]+(,m:)[-\d.]+'
        new, count = re.subn(
            pat, lambda x: f"{x.group(1)}{p}{x.group(2)}{d}{x.group(3)}{mo}", body
        )
        if count:
            body = new
            n += 1
    return html[: m.start()] + "const " + var + "={" + body + "};" + html[m.end():], n


def patch_stocks(html, data):
    """IN_STK rows are [name, price, d1, m1, q1] — update first 3 numerics."""
    n = 0
    for name, (p, d, _mo) in data.items():
        pat = r'(\["' + re.escape(name) + r'",)[\d.]+,[-\d.]+'
        new, count = re.subn(pat, lambda x: f"{x.group(1)}{p},{d}", html)
        if count:
            html = new
            n += 1
    return html, n


def patch_spark(html, name, value):
    m = re.search(r'("' + name + r'":\s*\[)([^\]]+)(\])', html)
    if not m:
        return html
    arr = [float(x) for x in m.group(2).split(",")]
    arr = arr[1:] + [value]
    return html[: m.start()] + m.group(1) + ", ".join(f"{x:g}" for x in arr) + m.group(3) + html[m.end():]




# ════════════════════════════════════════════════════════════════════════
#  MACRO-RELEASE FETCHER — CPI / repo / reserves / GDP / IIP.
#  Yahoo has none of these. They come from MoSPI/RBI on a monthly/weekly
#  cadence. This tries lightweight public sources; if any is blocked or the
#  shape changed, it logs and KEEPS THE EXISTING VALUE (never breaks deploy).
#
#  IMPORTANT design choice: these numbers appear dozens of times in prose, so
#  we do NOT blind-replace. We patch (a) the MODEL's source constants so the
#  regime engine always computes on fresh data, and (b) a SMALL set of clearly
#  anchored display strings. Everything else (the narrative) is left to the
#  human — a wrong global replace is worse than a slightly stale sentence.
# ════════════════════════════════════════════════════════════════════════
# (json/urllib/re already imported above)
import re as _re

MACRO_DEFAULTS = {           # last-known-good; only overwritten on a successful fetch
    "cpi": 4.38, "cpi_month": "Jun", "cpi_prev": 3.93,
    "repo": 5.25, "sdf": 5.00, "msf": 5.50,
    "reserves_bn": 702.0, "reserves_week": "Jul",
    "iip": 4.1, "gdp_q4": 6.2, "gdp_fy": 6.8, "gdp_ny": 6.6,
    "nominal_gdp": 9.8, "real_10y": 2.62, "mibor_3m": 6.63, "mibor_on": 5.85,
    "cpi_trail": [3.61, 3.34, 3.16, 3.48, 3.93, 4.38],
}

def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MacroIntelBot/1.0)",
        "Accept": "text/html,application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def fetch_macro():
    """Return a dict of macro values. Each field independently falls back to
    MACRO_DEFAULTS if its source fails — so partial success still helps."""
    m = dict(MACRO_DEFAULTS)

    # --- RBI data portal: one header string carries repo/SDF/CPI/FX ---
    # Format seen: "Policy Repo Rate : 5.25% | ... SDF Rate : 5.00% | CPI Inflation : 3.94% (May-26) | ..."
    try:
        html = _get("https://data.rbi.org.in/")
        def grab(label, pat=r"([\d.]+)\s*%"):
            mm = _re.search(_re.escape(label) + r"\s*:\s*" + pat, html)
            return float(mm.group(1)) if mm else None
        repo = grab("Policy Repo Rate")
        sdf  = grab("Standing Deposit Facility (SDF) Rate")
        cpi  = grab("CPI Inflation")
        if repo: m["repo"] = repo
        if sdf:  m["sdf"]  = sdf
        if cpi:  m["cpi"]  = cpi
        # forex reserves headline — label variants seen on the portal over time
        for lbl in ("Foreign Exchange Reserves", "Forex Reserves", "FX Reserves"):
            mm = _re.search(_re.escape(lbl) + r"[^\d$]{0,20}\$?\s*([\d,]+(?:\.\d+)?)\s*([BbMm])",
                            html)
            if mm:
                v = float(mm.group(1).replace(",", ""))
                if mm.group(2).lower() == "m":
                    v = v / 1000.0
                if 300 < v < 2000:          # sanity: India reserves in $bn
                    m["reserves_bn"] = round(v, 1)
                    md = _re.search(_re.escape(lbl) + r".{0,80}?as on ([A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4})",
                                    html)
                    if md:
                        m["reserves_asof"] = md.group(1)
                    break
        # CPI month tag e.g. "(May-26)"
        mt = _re.search(r"CPI Inflation\s*:\s*[\d.]+%\s*\(([A-Za-z]{3})-\d{2}\)", html)
        if mt: m["cpi_month"] = mt.group(1)
        print(f"  macro: RBI portal OK (repo {m['repo']}, cpi {m['cpi']})")
    except Exception as e:
        print(f"  macro: RBI portal unavailable ({type(e).__name__}) — keeping last-known repo/CPI")

    # --- Trading Economics calendar JSON (often blocked without key; try anyway) ---
    # Left as a best-effort; if it 403s we just keep what we have.
    # (No-op placeholder: TE's public pages are JS-rendered / rate-limited.
    #  Wire a TE API key here when you have one: ?c=YOUR_KEY)

    return m


# ═══════════════════════════════════════════════════════════════════════════
#  v91 · FULL-MARKET UNIVERSE — every listed Indian share we can reach
#  ---------------------------------------------------------------------
#  The terminal used to know 50 shares. This block widens it to the whole
#  listed market: NSE publishes the official constituent lists and the full
#  equity master as CSVs, so the universe is FETCHED, never typed. For every
#  name we then publish (a) a weekly close series for charting and (b) the
#  ten factors the page's own judgeDual() model consumes — so the browser
#  scores the entire market with the exact same code it uses for one share.
#
#  All of it rides inside history_1y.json, which the workflow already copies
#  to _site and commits. No new published file, no workflow change.
# ═══════════════════════════════════════════════════════════════════════════
UNIV_CAP = 1200          # how many names get price series + model factors
UNIV_BUDGET_S = 540      # wall-clock ceiling for the universe download
UNIV_CHUNK = 80          # symbols per yfinance batch call

# NSE constituent lists, most-liquid first — this ordering is the priority
# order for the download, so a partial run still covers the tradeable market.
NSE_LISTS = [
    ("https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv", "Nifty 50"),
    ("https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv", "Nifty 200"),
    ("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "Nifty 500"),
    ("https://nsearchives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv", "Nifty Total Market"),
]
NSE_MASTER = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

# NSE's macro-industry vocabulary → the 14 sectors the page's models speak.
# A translation table, not data: the industry value itself is fetched live.
SECTOR_XLATE = {
    "information technology": "IT",
    "oil gas & consumable fuels": "Energy",
    "automobile and auto components": "Auto",
    "healthcare": "Pharma",
    "fast moving consumer goods": "FMCG",
    "metals & mining": "Metal",
    "capital goods": "Capital Goods",
    "construction": "Infra",
    "construction materials": "Infra",
    "power": "Power",
    "consumer durables": "Consumer",
    "consumer services": "Consumer",
    "realty": "Realty",
    "telecommunication": "Telecom",
}


def _nse_opener():
    """NSE blocks bare requests — hit the homepage first to bank cookies."""
    import http.cookiejar
    hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/126.0 Safari/537.36",
           "Accept": "text/csv,*/*", "Accept-Language": "en-US,en;q=0.9",
           "Referer": "https://www.nseindia.com/"}
    op = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    try:
        op.open(urllib.request.Request("https://www.nseindia.com", headers=hdr),
                timeout=15).read()
    except Exception:
        pass
    return op, hdr


def _csv_rows(op, hdr, url):
    import csv as _csv
    raw = op.open(urllib.request.Request(url, headers=hdr), timeout=25).read()
    txt = raw.decode("utf-8", "replace").lstrip("﻿")
    return list(_csv.DictReader(txt.splitlines()))


def _col(row, *cands):
    for k in row:
        if k and k.strip().lower() in cands:
            v = (row[k] or "").strip()
            if v:
                return v
    return ""


def fetch_universe():
    """(order, names, sect) — the listed universe, scraped from NSE.

    order : symbols in priority sequence (index members first, then the rest
            of the equity master) — a truncated download still covers what
            anyone actually trades.
    names : symbol -> company name, for EVERY listed equity we can see, so
            search resolves a company even when the model hasn't screened it.
    sect  : symbol -> our sector vocabulary (or NSE's raw industry when it
            doesn't map), for the long-term model's sector tilt.
    """
    order, names, sect, seen = [], {}, {}, set()
    try:
        op, hdr = _nse_opener()
    except Exception as e:
        print(f"  universe: NSE opener failed ({type(e).__name__})")
        return [], {}, {}

    def take(sym, nm, ind):
        sym = sym.upper().strip().replace(" ", "")
        if not sym or "-" in sym[:1]:
            return
        y = sym + ".NS"
        if nm:
            names[y] = nm
        if ind:
            key = ind.strip().lower()
            if key == "financial services":
                sect[y] = "Banking" if "bank" in (nm or "").lower() else "NBFC"
            else:
                sect[y] = SECTOR_XLATE.get(key, ind.strip())
        if y not in seen:
            seen.add(y)
            order.append(y)

    for url, label in NSE_LISTS:
        try:
            rows = _csv_rows(op, hdr, url)
            n0 = len(order)
            for r in rows:
                take(_col(r, "symbol"), _col(r, "company name", "name of company"),
                     _col(r, "industry"))
            print(f"  universe: {label} +{len(order)-n0} (total {len(order)})")
        except Exception as e:
            print(f"  universe: {label} unavailable ({type(e).__name__})")

    try:
        rows = _csv_rows(op, hdr, NSE_MASTER)
        n0 = len(order)
        for r in rows:
            if _col(r, "series", " series").upper() not in ("EQ", "BE", ""):
                continue
            take(_col(r, "symbol", " symbol"),
                 _col(r, "name of company", " name of company"), "")
        print(f"  universe: NSE equity master +{len(order)-n0} "
              f"(total {len(order)} listed, {len(names)} named)")
    except Exception as e:
        print(f"  universe: equity master unavailable ({type(e).__name__})")

    return order, names, sect


def _factors(v):
    """Mirror of the page's judgeFactors() — same ten numbers, same math, so
    the market-wide screen and the single-share verdict cannot disagree."""
    import math
    n = len(v)
    if n < 130:
        return None
    px = v[-1]
    if not px or px <= 0:
        return None
    s50 = sum(v[-50:]) / len(v[-50:])
    w200 = min(200, n - 2)
    s200 = sum(v[-w200:]) / w200
    rets = []
    for i in range(1, n):
        a, b = v[i], v[i - 1]
        if not a or not b or a <= 0 or b <= 0:
            return None
        rets.append(math.log(a / b))

    def sd(arr):
        if not arr:
            return 0.0
        m = sum(arr) / len(arr)
        return math.sqrt(sum((x - m) ** 2 for x in arr) / len(arr))

    sd20 = sd(rets[-20:])
    r20 = px / v[-21] - 1
    z20 = (r20 / (sd20 * math.sqrt(20))) if sd20 > 0 else 0.0
    h126 = rets[-126:]
    s126 = sd(h126)
    sh6 = ((sum(h126) / len(h126)) / s126 * math.sqrt(252)) if s126 > 0 else 0.0
    hi = max(v)
    dd = (px / hi - 1) * 100
    rv30 = sd(rets[-30:]) * math.sqrt(252) * 100
    rv100 = sd(rets[-100:]) * math.sqrt(252) * 100
    r126 = (px / v[-126] - 1) * 100
    return [round(x, 4) for x in
            (px, s50, s200, z20, sh6, dd, rv30, rv100, r20 * 100, r126)]


def _rnd(x):
    """Adaptive precision — a ₹3,412 share needs no paise in a 1-y chart."""
    a = abs(x)
    return round(x, 2) if a < 100 else (round(x, 1) if a < 1000 else round(x))


def build_universe_block(stamp, prev):
    """The wide block published inside history_1y.json.

    Rebuilt at most once a day (the first pass that manages it); every other
    pass carries the existing block forward untouched, which also keeps the
    git objects small. Any failure preserves whatever was there before."""
    import time
    today = f"{stamp:%Y%m%d}"
    keep = {k: prev[k] for k in ("wide", "wdates", "wf", "names", "sect",
                                 "wide_date", "wide_updated") if k in prev}
    if prev.get("wide_date") == today and prev.get("wf"):
        print(f"  universe: already built today ({len(prev.get('wf', {}))} "
              f"screened) — carried forward")
        return keep

    order, names, sect = fetch_universe()
    if not order:
        # NSE unreachable: fall back to the universe we already published
        order = list((prev.get("wf") or {}).keys()) or sorted(STOCKS.values())
        names = prev.get("names") or {}
        sect = prev.get("sect") or {}
        print(f"  universe: NSE lists unreachable — reusing last known "
              f"{len(order)} symbols")

    targets = order[:UNIV_CAP]
    frames, t0, tried = [], time.time(), 0
    for i in range(0, len(targets), UNIV_CHUNK):
        if time.time() - t0 > UNIV_BUDGET_S:
            print(f"  universe: {UNIV_BUDGET_S}s budget reached after "
                  f"{tried} symbols — publishing what we have")
            break
        part = targets[i:i + UNIV_CHUNK]
        tried += len(part)
        try:
            df = yf.download(part, period="1y", interval="1d",
                             auto_adjust=True, progress=False, threads=True)
            cl = df["Close"] if hasattr(df.columns, "levels") else df[["Close"]]
            frames.append(cl)
        except Exception as e:
            print(f"  universe: chunk {i//UNIV_CHUNK+1} failed "
                  f"({type(e).__name__})")

    if not frames:
        print("  universe: no data this pass — previous block kept")
        return keep

    import pandas as _pd
    close = _pd.concat(frames, axis=1)
    close = close.loc[:, ~close.columns.duplicated(keep="last")]
    close = close.dropna(how="all").sort_index()

    wf, wide = {}, {}
    for sym in close.columns:
        col = close[sym].dropna()
        if col.shape[0] < 130:
            continue
        f = _factors([float(x) for x in col.tolist()])
        if not f:
            continue
        wf[sym] = f
        wk = col.resample("W-FRI").last().dropna()
        wide[sym] = [_rnd(float(x)) for x in wk.tolist()[-53:]]

    if len(wf) < 100:
        print(f"  universe: only {len(wf)} names cleared the 130-day bar — "
              f"previous block kept")
        return keep

    # one shared weekly date axis (the longest series wins; shorter ones are
    # left-padded with null so the client never mis-aligns a chart)
    ref = close.resample("W-FRI").last().dropna(how="all").index[-53:]
    wdates = [int(d.strftime("%Y%m%d")) for d in ref]
    for sym, vals in wide.items():
        if len(vals) < len(wdates):
            wide[sym] = [None] * (len(wdates) - len(vals)) + vals
        elif len(vals) > len(wdates):
            wide[sym] = vals[-len(wdates):]

    names = {k: v for k, v in (names or {}).items()}
    sect = {k: v for k, v in (sect or {}).items() if k in wf}
    print(f"  universe: {len(wf)} shares screened × {len(wdates)} weekly "
          f"points · {len(names)} companies searchable")
    return {"wide": wide, "wdates": wdates, "wf": wf, "names": names,
            "sect": sect, "wide_date": today,
            "wide_updated": f"{stamp:%a %b %d, %Y %H:%M} IST"}


def write_history_json(stamp):
    """v84: publish a compact same-origin 1-year daily-close history for every
    symbol the page's client features need (search/verdict/rotation/charts).
    Browsers cannot call Yahoo directly (CORS), so the site serves its own
    data. Fully fail-safe: any error leaves the previous file in place."""
    try:
        syms = sorted(set(MARKET.values()) | set(STOCKS.values()) |
                      {"LTGILTBEES.NS", "GILT5YBEES.NS", "GOLDBEES.NS",
                       "SILVERBEES.NS", "^MOVE", "^TNX", "EEM",
                       # bond types — duration, PSU credit, global credit
                       "EBBETF0430.NS", "EBBETF0433.NS",
                       "LQD", "HYG"})
        df = yf.download(syms, period="1y", interval="1d",
                         auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if hasattr(df.columns, "levels") else df[["Close"]]
        close = close.dropna(how="all")
        if len(close) < 60:
            print("  history: too few rows — kept previous file")
            return
        # v88: one retry pass for symbols the batch missed (partial rate-limits
        # in CI were leaving the file alphabetically truncated)
        missing = [s for s in syms if s not in close.columns
                   or close[s].dropna().shape[0] < 60]
        if missing:
            try:
                df2 = yf.download(missing, period="1y", interval="1d",
                                  auto_adjust=True, progress=False,
                                  threads=False)
                close2 = df2["Close"] if hasattr(df2.columns, "levels") \
                    else df2[["Close"]]
                import pandas as _pd
                close = _pd.concat([close, close2], axis=1)
                close = close.loc[:, ~close.columns.duplicated(keep="last")]
                print(f"  history: retry recovered "
                      f"{sum(1 for s in missing if s in close.columns and close[s].dropna().shape[0] >= 60)}"
                      f"/{len(missing)} missing symbols")
            except Exception as e:
                print(f"  history: retry failed ({type(e).__name__})")
        dates = [int(d.strftime("%Y%m%d")) for d in close.index]
        series = {}
        for sym in close.columns:
            col = close[sym]
            if col.dropna().shape[0] < 60:
                continue
            series[sym] = [None if (v != v) else round(float(v), 4)
                           for v in col.tolist()]
        out = {"updated": f"{stamp:%a %b %d, %Y %H:%M} IST",
               "dates": dates, "series": series}
        # v91: the whole listed market rides inside this same file — the
        # workflow already copies it to _site, so no new file is published.
        prev = {}
        try:
            with open("history_1y.json") as f:
                prev = json.load(f)
        except Exception:
            pass
        try:
            out.update(build_universe_block(stamp, prev) or {})
        except Exception as e:
            print(f"  universe: failed ({type(e).__name__}) — core history "
                  f"unaffected, previous universe kept")
            for k in ("wide", "wdates", "wf", "names", "sect", "wide_date",
                      "wide_updated"):
                if k in prev:
                    out[k] = prev[k]
        with open("history_1y.json", "w") as f:
            json.dump(out, f, separators=(",", ":"))
        print(f"  history: history_1y.json written ({len(series)} core series "
              f"× {len(dates)} days + {len(out.get('wf', {}))} screened shares "
              f"+ {len(out.get('names', {}))} searchable companies)")
        return {"core": len(series), "screened": len(out.get("wf", {})),
                "searchable": len(out.get("names", {}))}
    except Exception as e:
        print(f"  history: failed ({type(e).__name__}) — kept previous file")
    return {}


# ═══ v85: AMFI mutual-fund NAVs (official, keyless) ═══════════════════════
MF_PATTERNS = {   # category -> candidate scheme-name substrings (direct-growth)
    "Index · Nifty 50": ["uti nifty 50 index fund", "hdfc index fund-nifty 50",
                         "sbi nifty index fund"],
    "Gilt (long)":      ["sbi magnum gilt fund", "icici prudential gilt fund",
                         "hdfc gilt fund"],
    "Gold (FoF)":       ["nippon india gold savings fund", "sbi gold fund",
                         "hdfc gold fund"],
    "Liquid (cash)":    ["parag parikh liquid fund", "hdfc liquid fund",
                         "sbi liquid fund"],
}

def fetch_amfi():
    """Official AMFI NAV file — all schemes, plain text, no key, no anti-bot.
    v88: format-proof matcher — names are normalized (lowercase, punctuation
    collapsed) and matched on tokens, with preferred-AMC patterns first and a
    generic category fallback, so AMFI renaming can't zero the table."""
    raw = None
    for url in ("https://portal.amfiindia.com/spages/NAVAll.txt",
                "https://www.amfiindia.com/spages/NAVAll.txt"):
        try:
            raw = _get(url, timeout=90)
            if raw and ";" in raw:
                break
        except Exception as e:
            print(f"  amfi: {url.split('/')[2]} failed ({type(e).__name__})")
            raw = None
    if not raw:
        print("  amfi: unavailable — keeping last NAVs")
        return {}

    def norm(s):
        return " ".join(_re.sub(r"[^a-z0-9]+", " ", s.lower()).split())

    CATS = {   # category -> (preferred substrings, generic fallback substrings)
        "Index · Nifty 50": (["uti nifty 50 index fund",
                              "hdfc index fund nifty 50",
                              "sbi nifty index fund"],
                             ["nifty 50 index fund"]),
        "Gilt (long)":      (["sbi magnum gilt fund",
                              "icici prudential gilt fund", "hdfc gilt fund"],
                             ["gilt fund"]),
        "Gold (FoF)":       (["nippon india gold savings fund", "sbi gold fund",
                              "hdfc gold"], ["gold savings fund", "gold fund"]),
        "Liquid (cash)":    (["parag parikh liquid fund", "hdfc liquid fund",
                              "sbi liquid fund"], ["liquid fund"]),
    }
    rows = []
    sample = None
    for line in raw.splitlines():
        parts = line.split(";")
        if len(parts) < 6:
            continue
        name = parts[3].strip()
        n = norm(name)
        if "direct" not in n or "growth" not in n:
            continue
        if "idcw" in n or "dividend" in n or " etf" in " " + n:
            continue
        try:
            nav = round(float(parts[4]), 4)
        except Exception:
            continue
        rows.append((n, name, nav, parts[5].strip()))
        if sample is None:
            sample = name
    out = {}
    for cat, (pref, generic) in CATS.items():
        hit = None
        for p in pref:
            hit = next((r for r in rows if p in r[0]), None)
            if hit:
                break
        if not hit:
            for p in generic:
                hit = next((r for r in rows if p in r[0]
                            and "etf" not in r[0]), None)
                if hit:
                    break
        if hit:
            out[cat] = {"name": hit[1], "nav": hit[2], "date": hit[3]}
    print(f"  amfi: {len(out)}/{len(CATS)} categories matched "
          f"({len(rows)} direct-growth schemes scanned"
          + (f"; sample: {sample[:60]}" if sample and not out else "") + ")")
    return out


def patch_mf(html, mf):
    """Maintain window.MF_LIVE — official NAVs + an accruing trail (≤400)."""
    blk = _re.search(r"window\.MF_LIVE\s*=\s*(\{.*?\});", html)
    cur = {"cats": {}, "updated": ""}
    if blk:
        try:
            cur.update(json.loads(blk.group(1)))
        except Exception:
            pass
    for cat, v in (mf or {}).items():
        c = cur["cats"].get(cat, {"trail": []})
        c["name"], c["nav"], c["date"] = v["name"], v["nav"], v["date"]
        tr = [t for t in (c.get("trail") or []) if isinstance(t, list)]
        if not tr or tr[-1][0] != v["date"]:
            tr.append([v["date"], v["nav"]])
        c["trail"] = tr[-400:]
        cur["cats"][cat] = c
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    new_blk = "window.MF_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  amfi: MF_LIVE patched ({len(cur['cats'])} categories)")
    else:
        print("  amfi: MF_LIVE block not found (skipped)")
    return html


# ═══ v85: FII / DII daily flows (NSE, best-effort with cookie preflight) ═══
def fetch_flows():
    try:
        import http.cookiejar
        hdr = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/126.0 Safari/537.36",
               "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
               "Referer": "https://www.nseindia.com/reports/fii-dii"}
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        opener.open(urllib.request.Request("https://www.nseindia.com",
                                           headers=hdr), timeout=15)
        raw = opener.open(urllib.request.Request(
            "https://www.nseindia.com/api/fiidiiTradeReact", headers=hdr),
            timeout=15).read().decode()
        data = json.loads(raw)
        out = {}
        for row in data:
            cat = str(row.get("category", ""))
            try:
                net = float(str(row.get("netValue", "0")).replace(",", ""))
            except Exception:
                continue
            if "FII" in cat.upper() or "FPI" in cat.upper():
                out["fii"] = net
                out["asof"] = str(row.get("date", ""))
            elif "DII" in cat.upper():
                out["dii"] = net
        if "fii" in out:
            print(f"  flows: NSE OK (FII {out['fii']:+,.0f} Cr, "
                  f"DII {out.get('dii', 0):+,.0f} Cr, {out.get('asof', '')})")
        return out
    except Exception as e:
        print(f"  flows: NSE unavailable ({type(e).__name__}) — keeping last")
        return {}


def patch_flows(html, fl):
    """Maintain window.FLOWS_LIVE — latest FII/DII net (₹ Cr) + trail (≤60)."""
    blk = _re.search(r"window\.FLOWS_LIVE\s*=\s*(\{.*?\});", html)
    cur = {"fii": None, "dii": None, "asof": "", "trail": [], "updated": ""}
    if blk:
        try:
            cur.update(json.loads(blk.group(1)))
        except Exception:
            pass
    if fl.get("fii") is not None:
        cur["fii"], cur["dii"] = fl["fii"], fl.get("dii")
        cur["asof"] = fl.get("asof", "")
        tr = [t for t in (cur.get("trail") or []) if isinstance(t, list)]
        if not tr or tr[-1][0] != cur["asof"]:
            tr.append([cur["asof"], cur["fii"], cur.get("dii") or 0])
        cur["trail"] = tr[-60:]
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    new_blk = "window.FLOWS_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  flows: FLOWS_LIVE patched (trail {len(cur['trail'])})")
    else:
        print("  flows: FLOWS_LIVE block not found (skipped)")
    return html


def fetch_fred_reserves():
    """India total reserves history (monthly, $bn) from FRED's keyless CSV —
    IMF 'total reserves excluding gold'. Used for the Forex tab's chart; the
    weekly headline comes from the RBI portal. Returns [] on any failure."""
    try:
        raw = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGINM052N",
                   timeout=30)
        rows = []
        for line in raw.strip().splitlines()[1:]:
            try:
                d, v = line.split(",")
                if v and v != ".":
                    rows.append([d[:7], round(float(v) / 1e9, 1)])
            except Exception:
                continue
        rows = [r for r in rows if r[1] > 100]
        return rows[-48:]
    except Exception as e:
        print(f"  reserves: FRED history unavailable ({type(e).__name__})")
        return []


def patch_reserves(html, m):
    """Maintain window.RESERVES_LIVE — the single machine-patched source the
    Forex Reserves tab renders from. Preserves the existing block's fields
    when a fetch fails; appends the weekly headline to a trail (keeps 30)."""
    blk = _re.search(r"window\.RESERVES_LIVE\s*=\s*(\{.*?\});", html)
    cur = {"total_bn": m.get("reserves_bn", 702.0), "asof": "", "ath_bn": 728.5,
           "trail": [], "monthly": [], "updated": ""}
    if blk:
        try:
            cur.update(json.loads(_re.sub(r"(\w+):", r'"\1":', blk.group(1))))
        except Exception:
            try:
                cur.update(json.loads(blk.group(1)))
            except Exception:
                pass
    total = float(m.get("reserves_bn", cur.get("total_bn", 702.0)))
    cur["total_bn"] = round(total, 1)
    if m.get("reserves_asof"):
        cur["asof"] = m["reserves_asof"]
    cur["ath_bn"] = round(max(float(cur.get("ath_bn", 0) or 0), total), 1)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    tag = stamp.strftime("%Y-%m-%d")
    trail = [t for t in (cur.get("trail") or []) if isinstance(t, list) and len(t) == 2]
    if not trail or abs(trail[-1][1] - total) >= 0.05:   # append on change (weekly print)
        if not trail or trail[-1][0] != tag:
            trail.append([tag, round(total, 1)])
    cur["trail"] = trail[-30:]
    fred = fetch_fred_reserves()
    if fred:
        cur["monthly"] = fred
    cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    new_blk = "window.RESERVES_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  reserves: RESERVES_LIVE patched (${cur['total_bn']}bn, "
              f"trail {len(cur['trail'])}, monthly {len(cur['monthly'])})")
    else:
        print("  reserves: RESERVES_LIVE block not found (skipped)")
    return html


def patch_macro(html, m):
    """Patch the MODEL constants (so the regime engine recomputes) plus a few
    clearly-anchored display values. Conservative by design."""
    n = 0
    subs = [
        # ---- model source constants (these DRIVE the computation) ----
        (r"(RC_CPI\s*=\s*)[\d.]+",            rf"\g<1>{m.get('cpi', 3.93)}"),
        (r"(RC_IIP\s*=\s*)[\d.]+",            rf"\g<1>{m.get('iip', 4.1)}"),
        (r"(cpi:\s*)[\d.]+(,\s*//\s*live)",   rf"\g<1>{m.get('cpi', 3.93)}\g<2>"),  # only the tagged one in RTE_inputs
        # ---- RBI Watch / rate-anomaly anchors ----
        (r"(REPO_NOW\s*=\s*)[\d.]+",          rf"\g<1>{m.get('repo', 5.25)}"),
        # ---- the India-tab regime header (anchored, single occurrence) ----
        (r"(CPI )[\d.]+(% " + m.get('cpi_month', 'May') + r" \(Jun 12 print\))", rf"\g<1>{m.get('cpi', 3.93)}\g<2>"),
        # ---- OIS-tab corridor cards (anchored) ----
        (r"(Repo Rate</[^>]+>\s*<[^>]+>)[\d.]+%", rf"\g<1>{m.get('repo', 5.25)}%"),
        (r"(SDF \(floor\)</[^>]+>\s*<[^>]+>)[\d.]+%", rf"\g<1>{m.get('sdf', 5.00)}%"),
        (r"(MSF \(ceiling\)</[^>]+>\s*<[^>]+>)[\d.]+%", rf"\g<1>{m.get('msf', 5.50)}%"),
        # ---- forex reserves headline card (anchored) ----
        (r"\$" + r"\d{3}\.\d" + r"bn(</[^>]*>\s*<[^>]*>\+?\$?[\d.]+M? WoW)", rf"${m.get('reserves_bn', 672.6)}bn\g<1>"),
    ]
    for pat, rep in subs:
        try:
            html, c = _re.subn(pat, rep, html)
            n += c
        except Exception:
            pass
    # also update the MACRO_LIVE object that bindLiveValues reads (reserves/CPI/repo)
    ml_pat = r'window\.MACRO_LIVE\s*=\s*\{[^}]*\};'
    # Preserve ALL MACRO_LIVE fields (v65 added nominal_gdp/real_10y/mibor/cpi_prev).
    # Only overwrite what the scrape actually returns; keep the rest at current defaults.
    ml_new = ('window.MACRO_LIVE = { '
              f'reserves_bn: {m.get("reserves_bn", 702.0)}, '
              f'reserves_ath: 728.5, '
              f'cpi: {m.get("cpi", 4.38)}, '
              f'cpi_prev: {m.get("cpi_prev", 3.93)}, '
              f'repo: {m.get("repo", 5.25)}, '
              f'gdp_fy: {m.get("gdp_fy", 6.8)}, '
              f'gdp_ny: {m.get("gdp_ny", 6.6)}, '
              f'iip: {m.get("iip", 4.1)}, '
              f'nominal_gdp: {m.get("nominal_gdp", 9.8)}, '
              f'real_10y: {m.get("real_10y", 2.62)}, '
              f'mibor_3m: {m.get("mibor_3m", 6.63)}, '
              f'mibor_on: {m.get("mibor_on", 5.85)}, '
              f'cpi_trail: {m.get("cpi_trail", [3.61,3.34,3.16,3.48,3.93,4.38])} }};')
    html, ml_c = re.subn(ml_pat, ml_new, html)
    if ml_c:
        n += ml_c
    print(f"  patch macro: {n} anchored values (CPI {m.get('cpi', 3.93)}%, repo {m.get('repo', 5.25)}%, reserves ${m.get('reserves_bn', 672.6)}bn) — model recomputes on these")
    return html, n



# ═══════════════════════════════════════════════════════════════════════
#  CONTRACT AUDIT — the updater writes into named structures in the HTML.
#  If a rebuild renames or removes one, the patcher silently does nothing and
#  the page quietly serves the last-good numbers for ever. This check runs
#  every pass and names anything that has gone missing, so a broken contract
#  shows up in the Action log the same day it breaks — not months later.
# ═══════════════════════════════════════════════════════════════════════
DATA_CONTRACTS = {
    "IN_IDX":        "const IN_IDX={",
    "FX":            "const FX={",
    "ENERGY":        "const ENERGY={",
    "PREC":          "const PREC={",
    "IDX":           "const IDX={",
    "CRYPTO":        "const CRYPTO={",
    "IN_STK":        "const IN_STK=",
    "SPARKS":        "const SPARKS=",
    "MACRO_LIVE":    "window.MACRO_LIVE",
    "RESERVES_LIVE": "window.RESERVES_LIVE",
    "MF_LIVE":       "window.MF_LIVE",
    "FLOWS_LIVE":    "window.FLOWS_LIVE",
    "news slot":     "<!--NEWSLIVE_START-->",
    "manifest slot": "<!--MANIFEST_START-->",
    "header stamp":  "· Models:",
}


def audit_contracts(html):
    """(ok, missing) — every structure this script writes into, checked."""
    missing = [k for k, needle in DATA_CONTRACTS.items() if needle not in html]
    ok = len(DATA_CONTRACTS) - len(missing)
    if missing:
        print(f"  CONTRACT AUDIT: {ok}/{len(DATA_CONTRACTS)} intact — MISSING: "
              f"{', '.join(missing)}")
        print("     (a patcher above will have reported 0 for each of these; "
              "the page is serving its last-good values for them)")
    else:
        print(f"  contract audit: {ok}/{ok} client data contracts intact")
    return ok, missing


def write_manifest(html, mkt, counts):
    """Stamp a visible update-manifest into the page so each run leaves proof:
    what was fetched, how many values patched, and when. Renders into #update-manifest."""
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist).strftime("%a %b %d, %Y %H:%M IST")
    ok = sum(1 for v in mkt.values() if v)
    total = len(mkt)
    rows = "".join(
        f"<tr><td style='font-size:11px'>{k}</td><td style='font-size:11px;color:#00d26a'>{v[0]:,.2f}</td><td style='font-size:11px;color:{'#00d26a' if v[1]>=0 else '#ff5252'}'>{v[1]:+.2f}%</td></tr>"
        for k, v in list(mkt.items())[:12] if v
    )
    manifest = (
        f"<div style='font-size:11px;color:#888;line-height:1.7;margin-bottom:8px'>"
        f"Last run: <strong style='color:#00d26a'>{now}</strong> · Yahoo fetch: <strong>{ok}/{total}</strong> tickers OK · "
        f"patched {counts.get('obj',0)} price fields, {counts.get('stocks',0)} stocks, {counts.get('macro',0)} macro values · "
        f"model screened <strong style='color:#00d26a'>{counts.get('screened',0):,}</strong> shares of "
        f"<strong>{counts.get('searchable',0):,}</strong> listed companies · "
        f"{counts.get('contracts','?')} data contracts intact.</div>"
        f"<div style='font-size:10px;color:#888;margin-bottom:6px'>Sample of what was pulled this run (first 12):</div>"
        f"<table class='tbl'><thead><tr><th>Ticker</th><th>Price</th><th>1d</th></tr></thead><tbody>{rows}</tbody></table>"
    )
    # inject between unique markers so nested divs in the manifest don't break replacement
    START = "<!--MANIFEST_START-->"
    END = "<!--MANIFEST_END-->"
    wrapped = START + manifest + END
    if START in html and END in html:
        # replace everything between the markers (greedy-safe via split)
        pre = html.split(START)[0]
        post = html.split(END, 1)[1] if END in html else ""
        html = pre + wrapped + post
        print(f"  write manifest: replaced (stamped {now})")
    else:
        # first time: inject inside the container AND add markers
        pat = r'(<div id="update-manifest"[^>]*>)(.*?)(</div>)'
        if re.search(pat, html, re.DOTALL):
            html = re.sub(pat, lambda m: m.group(1) + wrapped + m.group(3), html, count=1, flags=re.DOTALL)
            print(f"  write manifest: first stamp {now}")
        else:
            print("  write manifest: container not found (skipped)")
    return html



def write_history(mkt):
    """Append today's closes to history.json (feeds the EOD sparkline). Keeps ~90 rows."""
    import json as _j
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    today = datetime.now(ist).strftime("%Y-%m-%d")
    def g(k):
        v = mkt.get(k); return round(v[0], 2) if v else None
    row = {"date": today, "nifty": g("Nifty 50"), "sensex": g("BSE Sensex"),
           "inr": g("USD/INR"), "brent": g("Brent Oil"), "gold": g("Gold")}
    try:
        js = _j.load(open("history.json"))
    except Exception:
        js = {"rows": []}
    rows = [r for r in js.get("rows", []) if r.get("date") != today]
    rows.append(row)
    js["rows"] = rows[-90:]
    _j.dump(js, open("history.json", "w"))
    print(f"  history.json: {len(js['rows'])} rows (latest {today})")


def fetch_news():
    """Pull latest India-market headlines from free RSS (no key). Returns list of {title,src,link,time}."""
    import urllib.request, re as _re
    from datetime import datetime, timezone, timedelta
    feeds = [
        ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
        ("Business Standard", "https://www.business-standard.com/rss/markets-106.rss"),
        ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ]
    items = []
    for src, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MacroIntel/1.0)"})
            xml = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "ignore")
            # crude RSS parse — grab <item><title> and <link>
            for m in list(_re.finditer(r"<item>(.*?)</item>", xml, _re.DOTALL))[:6]:
                block = m.group(1)
                t = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, _re.DOTALL)
                l = _re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, _re.DOTALL)
                if t:
                    import html as _html
                    title = _re.sub(r"<[^>]+>", "", t.group(1))
                    # strip CDATA remnants the lazy regex can leave behind, then
                    # decode entities (twice: some feeds double-encode) and
                    # re-escape for safe HTML insertion
                    title = title.replace("<![CDATA[", "").replace("]]>", "")
                    title = _html.escape(_html.unescape(_html.unescape(title)).strip())[:140]
                    link = (l.group(1).strip() if l else "")
                    link = link.replace("<![CDATA[", "").replace("]]>", "").strip()
                    if title:
                        items.append({"title": title, "src": src, "link": link})
        except Exception as e:
            print(f"  news: {src} failed ({type(e).__name__})")
    print(f"  news: fetched {len(items)} headlines from {len(feeds)} sources")
    return items[:15]

def patch_news(html, items):
    """Refresh the LIVE HEADLINES block in the News tab (between markers)."""
    import re as _re
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    stamp = datetime.now(ist).strftime("%a %b %d, %H:%M IST")
    if not items:
        return html, 0
    rows = "".join(
        f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05)">'
        f'<a href="{it["link"]}" target="_blank" style="color:var(--txt);font-size:12px;text-decoration:none">{it["title"]}</a>'
        f'<div style="font-size:10px;color:var(--dim)">{it["src"]}</div></div>'
        for it in items)
    block = (f'<!--NEWSLIVE_START--><div style="font-size:11px;color:var(--dim);margin-bottom:6px">'
             f'\u26a1 Auto-fetched headlines \u00b7 {stamp} \u00b7 free RSS (ET/BS/Moneycontrol). '
             f'Model-implication analysis below is editorial.</div>{rows}<!--NEWSLIVE_END-->')
    if "<!--NEWSLIVE_START-->" in html:
        html = _re.sub(r"<!--NEWSLIVE_START-->.*?<!--NEWSLIVE_END-->", lambda m: block, html, count=1, flags=_re.DOTALL)
    else:
        # inject at top of the news tab
        i = html.find('id="tab-news"')
        if i >= 0:
            ins = html.find(">", i) + 1
            html = html[:ins] + '<div class="sec">\U0001f4f0 LIVE HEADLINES (auto)</div>' + block + html[ins:]
    print(f"  patch news: {len(items)} headlines")
    return html, len(items)

def main(path):
    # IST everywhere a human reads it — runners are UTC, the audience is not
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    print(f"=== Terminal updater · {stamp:%Y-%m-%d %H:%M} IST ===")
    print("Fetching market data ...")
    mkt = fetch(MARKET)
    print(f"  market: {len(mkt)}/{len(MARKET)} OK")
    print("Fetching stocks ...")
    stk = fetch(STOCKS)
    print(f"  stocks: {len(stk)}/{len(STOCKS)} OK")
    hstats = write_history_json(stamp)  # same-origin data for the browser (CORS)

    html = open(path, encoding="utf-8").read()

    groups = {
        "IN_IDX": {k: v for k, v in mkt.items() if k in ("Nifty 50", "BSE Sensex", "Bank Nifty", "Midcap 100")},
        "FX": {k: v for k, v in mkt.items() if k in ("USD/INR", "DXY", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD")},
        "ENERGY": {k: v for k, v in mkt.items() if k in ("Brent Oil", "WTI Oil", "Nat Gas")},
        "PREC": {k: v for k, v in mkt.items() if k in ("Gold", "Silver", "Platinum", "Palladium")},
        "IDX": {k: v for k, v in mkt.items() if k in ("S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000", "Nikkei 225")},
        "CRYPTO": {k: v for k, v in mkt.items() if k in ("Bitcoin", "Ethereum", "Solana")},
    }
    _obj_total = 0
    for var, data in groups.items():
        html, n = patch_obj(html, var, data)
        _obj_total += n
        print(f"  patch {var}: {n} fields")

    html, ns = patch_stocks(html, stk)
    print(f"  patch IN_STK: {ns} rows")

    # --- macro releases (CPI/repo/reserves) from RBI portal, best-effort ---
    macro = fetch_macro()
    html, nmac = patch_macro(html, macro)
    html = patch_reserves(html, macro)
    html = patch_mf(html, fetch_amfi())
    html = patch_flows(html, fetch_flows())

    _ok, _missing = audit_contracts(html)
    counts = {"obj": _obj_total, "stocks": ns, "macro": nmac,
              "screened": hstats.get("screened", 0),
              "searchable": hstats.get("searchable", 0),
              "contracts": f"{_ok}/{len(DATA_CONTRACTS)}"}
    html = write_manifest(html, mkt, counts)
    write_history(mkt)
    try:
        _news = fetch_news()
        html, _ = patch_news(html, _news)
    except Exception as e:
        print(f"  news: skipped ({type(e).__name__})")

    spark_src = {
        "Nifty": "Nifty 50", "Sensex": "BSE Sensex", "BankNifty": "Bank Nifty",
        "Gold": "Gold", "Brent": "Brent Oil", "WTI": "WTI Oil",
        "USDINR": "USD/INR", "BTC": "Bitcoin", "VIX": "VIX",
    }
    for spark, src in spark_src.items():
        if src in mkt:
            html = patch_spark(html, spark, mkt[src][0])

    # Stamp the header timestamp
    html = re.sub(
        r"Data: [A-Za-z]{3} [A-Za-z]{3} \d+, 2026[^<·]*· Models:",
        f"Data: {stamp:%a %b %d, %Y %H:%M} IST (auto) · Models:",
        html, count=1,
    )

    open(path, "w", encoding="utf-8").write(html)

    # Keep a dated copy
    os.makedirs("history", exist_ok=True)
    open(f"history/terminal_{stamp:%Y%m%d}.html", "w", encoding="utf-8").write(html)

    print(f"\nWrote {path} (in place) + history/terminal_{stamp:%Y%m%d}.html")
    print("Prices updated; narrative/verdicts still need a Claude pass.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "macro_intelligence_terminal.html")
