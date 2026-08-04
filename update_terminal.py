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
import time as _time

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


# ═══════════════════════════════════════════════════════════════════════
#  v92e: WHAT TO DO WHEN YAHOO SAYS NO.
#  Stooq serves the same daily closes as a plain keyless CSV with no auth,
#  no key and no rate limit worth the name. It does not cover NSE single
#  names, which is fine — those are the ones history_1y.json already holds.
#  Between the two, a Yahoo outage costs us nothing rather than costing us
#  every price on the page.
# ═══════════════════════════════════════════════════════════════════════
STOOQ = {
    "^NSEI": "^nsei", "^BSESN": "^snx",
    "INR=X": "usdinr", "DX-Y.NYB": "^dxy", "EURUSD=X": "eurusd",
    "GBPUSD=X": "gbpusd", "JPY=X": "usdjpy", "AUDUSD=X": "audusd",
    "BZ=F": "cb.f", "CL=F": "cl.f", "NG=F": "ng.f",
    "GC=F": "gc.f", "SI=F": "si.f", "PL=F": "pl.f", "PA=F": "pa.f",
    "HG=F": "hg.f",
    "^GSPC": "^spx", "^NDX": "^ndx", "^DJI": "^dji", "^RUT": "^rut",
    "^N225": "^nkx", "^VIX": "^vix",
    "BTC-USD": "btcusd", "ETH-USD": "ethusd",
}


def _stooq_closes(code):
    """Daily closes, oldest first, from Stooq's keyless CSV. [] on failure."""
    try:
        raw = _get(f"https://stooq.com/q/d/l/?s={code}&i=d", timeout=20, tries=2)
    except Exception:
        return []
    out = []
    for line in raw.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            out.append(float(parts[4]))
        except Exception:
            continue
    return out[-70:]


def _hist_closes(sym):
    """Closes for one symbol out of the history file this pipeline publishes.
    Same numbers the browser is already being served, so a fallback here can
    never disagree with the charts."""
    try:
        with open("history_1y.json", encoding="utf-8") as f:
            h = json.load(f)
        v = [x for x in (h.get("series", {}).get(sym) or []) if x is not None]
        return v[-70:]
    except Exception:
        return []


def fetch(symbols):
    """Return {name: (last, day_pct, month_pct)} from ~2 months of history.

    v88: BATCH download first — the exact code path ml_models.py uses, which
    has kept working in CI while the old per-ticker Ticker().history() loop
    (~90 sequential calls) started failing. Per-ticker remains only as a
    fallback for symbols the batch missed."""
    out = {}

    def _pack_list(v):
        v = [x for x in v if x is not None and x == x]
        if len(v) < 2:
            return None
        last, prev = float(v[-1]), float(v[-2])
        mago = float(v[-22]) if len(v) >= 22 else float(v[0])
        if not prev or not mago:
            return None
        return (round(last, 2), round((last / prev - 1) * 100, 2),
                round((last / mago - 1) * 100, 2))

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
        except Exception:  # noqa: BLE001
            pass

    # tier 3 — Stooq, keyless CSV. Covers commodities, FX and world indices,
    # i.e. exactly the block that froze.
    miss = [n for n in symbols if n not in out]
    if miss:
        got = 0
        for name in miss:
            code = STOOQ.get(symbols[name])
            if not code:
                continue
            v = _pack_list(_stooq_closes(code))
            if v:
                out[name] = v
                got += 1
        if got:
            print(f"  fallback: {got} names recovered from Stooq (Yahoo missed them)")

    # tier 4 — our own published history. Not a new source, just the closes
    # the browser is already reading, so nothing can drift out of agreement.
    miss = [n for n in symbols if n not in out]
    if miss:
        got = 0
        for name in miss:
            v = _pack_list(_hist_closes(symbols[name]))
            if v:
                out[name] = v
                got += 1
        if got:
            print(f"  fallback: {got} names recovered from history_1y.json")

    still = [n for n in symbols if n not in out]
    if still:
        print(f"  ! {len(still)} names unresolved after all tiers: "
              f"{', '.join(sorted(still)[:8])}"
              f"{' …' if len(still) > 8 else ''}")
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
    # v92e: reserves_bn is deliberately ABSENT. It used to default to 702.0,
    # which meant a failed RBI scrape re-published a hard-coded constant on
    # every run and the tab has read $702.0bn since July 20 while calling
    # itself live. Absent means downstream keeps the last real read and says
    # so, which is the only honest thing to print.
    "reserves_week": "Jul",
    "iip": 4.1, "gdp_q4": 6.2, "gdp_fy": 6.8, "gdp_ny": 6.6,
    "nominal_gdp": 9.8, "real_10y": 2.62, "mibor_3m": 6.63, "mibor_on": 5.85,
    "cpi_trail": [3.61, 3.34, 3.16, 3.48, 3.93, 4.38],
}

# A GitHub-hosted runner is a datacenter IP, and Yahoo / FRED / the RBI
# portal all rate-limit or 403 a self-identifying bot from one. The UA below
# is the single change that keeps them answering; the retry covers the 429s
# that remain. Nothing here spoofs a human session — it is a plain GET with a
# UA that the CDNs in front of these hosts will serve.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


def _get(url, timeout=20, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA,
                "Accept": "text/html,application/xhtml+xml,application/json,*/*",
                "Accept-Language": "en-IN,en;q=0.9",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:            # noqa: BLE001
            last = e
            if attempt + 1 < tries:
                _time.sleep(1.5 * (attempt + 1))
    raise last

# ═══════════════════════════════════════════════════════════════════════
#  v92: THE MISSING MACRO BLOCKS — credit, money, prices, the bond yield.
#  Each row: key, label variants seen on data.rbi.org.in, sanity range,
#  whether the value is a percentage, and the human label the page prints.
#  A field that does not match, or matches out of range, is ABSENT from the
#  payload — never defaulted, because a stale credit-growth number presented
#  as live is worse than an empty tile that says the portal did not carry it.
# ═══════════════════════════════════════════════════════════════════════
RBI_EXTRA = [
    ("credit_growth", ["Bank Credit Growth", "Non-food Credit Growth",
                       "Non-Food Credit Growth", "Credit Growth"],
     (-10, 45), True, "Bank credit growth", "y/y"),
    ("deposit_growth", ["Aggregate Deposits Growth", "Deposit Growth",
                        "Bank Deposit Growth", "Aggregate Deposits"],
     (-10, 45), True, "Deposit growth", "y/y"),
    ("m3", ["Money Supply (M3) Growth", "M3 Growth", "Broad Money (M3)",
            "Money Supply"], (-10, 35), True, "Money supply M3", "y/y"),
    ("wpi", ["WPI Inflation", "Inflation (WPI)", "WPI"],
     (-15, 35), True, "WPI inflation", "y/y"),
    ("gsec10", ["10-Year G-Sec Yield", "10 Year G-Sec Yield", "G-Sec Yield",
                "10-year G-sec", "Government Security Yield"],
     (3, 15), True, "10-year G-sec", "nominal"),
    ("crr", ["Cash Reserve Ratio (CRR)", "Cash Reserve Ratio", "CRR"],
     (0, 15), True, "CRR", "of NDTL"),
    ("slr", ["Statutory Liquidity Ratio (SLR)", "Statutory Liquidity Ratio",
             "SLR"], (5, 40), True, "SLR", "of NDTL"),
    ("bank_rate", ["Bank Rate"], (2, 15), True, "Bank rate", "penal"),
    ("msf", ["Marginal Standing Facility (MSF) Rate",
             "Marginal Standing Facility Rate", "MSF Rate"],
     (2, 15), True, "MSF", "corridor ceiling"),
    ("call_rate", ["Weighted Average Call Rate (WACR)",
                   "Weighted Average Call Rate", "Call Money Rate", "WACR"],
     (0, 15), True, "Call rate (WACR)", "overnight"),
    ("gdp_growth", ["GDP Growth Rate", "Real GDP Growth", "GDP Growth"],
     (-20, 20), True, "Real GDP growth", "y/y"),
    ("iip_p", ["Index of Industrial Production", "IIP Growth", "IIP"],
     (-30, 30), True, "IIP", "y/y"),
    ("usdinr_ref", ["Exchange Rate", "Reference Rate", "INR / 1 USD",
                    "INR-USD"], (50, 150), False, "RBI reference rate",
     "₹ per $"),
]


def _rbi_num(html, labels, lo, hi, pct):
    """First label variant that yields a number inside the sanity range."""
    tail = (r"\s*[:\-]?\s*\$?\s*([\d,]+(?:\.\d+)?)\s*%" if pct else
            r"\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d+)?)")
    for lab in labels:
        for mm in _re.finditer(_re.escape(lab) + tail, html):
            try:
                v = float(mm.group(1).replace(",", ""))
            except Exception:
                continue
            if lo <= v <= hi:
                return round(v, 2)
    return None


def scan_rbi_extra(html):
    """{key: {v, label, unit}} for every block the portal actually carries."""
    out = {}
    for key, labels, (lo, hi), pct, label, unit in RBI_EXTRA:
        v = _rbi_num(html, labels, lo, hi, pct)
        if v is not None:
            out[key] = {"v": v, "label": label, "unit": unit,
                        "pct": bool(pct)}
    if out:
        print(f"  macro blocks: RBI portal carried {len(out)}/{len(RBI_EXTRA)} "
              f"({', '.join(sorted(out))})")
    else:
        print("  macro blocks: RBI portal carried none of the extended set "
              "today — those tiles will say so rather than show a stale number")
    return out


def _pct_rank(vals, x):
    """Where x sits in vals, 0-100. None if there is nothing to rank against."""
    v = [z for z in vals if z is not None and z == z]
    if len(v) < 20 or x is None:
        return None
    return round(sum(1 for z in v if z <= x) / len(v) * 100)


def fetch_india_extras():
    """India VIX and the rupee oil price — computed, not scraped. Same
    yfinance transport the rest of the pipeline runs on."""
    out = {}
    try:
        df = yf.download(["^INDIAVIX", "BZ=F", "INR=X"], period="1y",
                         interval="1d", auto_adjust=True, progress=False,
                         threads=True)
        close = df["Close"] if hasattr(df.columns, "levels") else df
        col = {c: [None if (v != v) else float(v) for v in close[c].tolist()]
               for c in close.columns}
    except Exception as e:
        print(f"  india extras: yfinance failed ({type(e).__name__}) — "
              f"VIX and rupee-crude tiles will show as unavailable")
        return out

    vx = [v for v in col.get("^INDIAVIX", []) if v]
    if len(vx) >= 20:
        out["vix"] = {"v": round(vx[-1], 2),
                      "pct": _pct_rank(vx, vx[-1]),
                      "chg": (round((vx[-1] / vx[-21] - 1) * 100, 1)
                              if len(vx) > 21 and vx[-21] else None)}

    br, fx = col.get("BZ=F", []), col.get("INR=X", [])
    if br and fx and len(br) == len(fx):
        rc = [(b * f) if (b and f) else None for b, f in zip(br, fx)]
        v = [z for z in rc if z]
        if len(v) >= 20:
            out["crude_inr"] = {
                "v": round(v[-1], 0), "pct": _pct_rank(v, v[-1]),
                "usd": round([z for z in br if z][-1], 2),
                "fx": round([z for z in fx if z][-1], 2),
                "chg": (round((v[-1] / v[-64] - 1) * 100, 1)
                        if len(v) > 64 and v[-64] else None)}
    if out:
        print(f"  india extras: {', '.join(sorted(out))} computed from live closes")
    return out


def patch_macro_x(html, mx, stamp):
    """One JSON blob, one anchored line. Absent fields stay absent."""
    payload = dict(mx)
    payload["updated"] = f"{stamp:%a %b %d, %Y %H:%M} IST"
    new = "window.MACRO_X = " + json.dumps(payload, separators=(",", ":")) + ";"
    # A lambda, not a plain replacement string: json.dumps escapes the rupee
    # sign to \u20b9 and re.sub reads a backslash in a replacement as a group
    # reference, so the whole patch raised re.error and silently kept the seed.
    html, c = _re.subn(r"window\.MACRO_X\s*=\s*\{.*?\};", lambda _m: new,
                       html, count=1, flags=_re.S)
    if c:
        print(f"  patch MACRO_X: {len(payload)-1} live macro blocks published")
    else:
        print("  patch MACRO_X: anchor not found (skipped)")
    return html


def fetch_macro():
    """Return a dict of macro values. Each field independently falls back to
    MACRO_DEFAULTS if its source fails — so partial success still helps."""
    # v92g: this used to be `dict(MACRO_DEFAULTS)`. That one line is why the
    # macro tab has been showing the same CPI, repo, GDP and IIP since July
    # 20 while calling itself live: a completely failed scrape still returned
    # a full dict of literals, and every downstream consumer treated it as a
    # reading. Now the dict starts empty and `live` records what was truly
    # read. A field that is absent stays absent all the way to the page.
    m = {}
    live = set()

    # --- RBI data portal: one header string carries repo/SDF/CPI/FX ---
    # Format seen: "Policy Repo Rate : 5.25% | ... SDF Rate : 5.00% | CPI Inflation : 3.94% (May-26) | ..."
    rbi_html = ""
    try:
        html = _get("https://data.rbi.org.in/")
        rbi_html = html
        def grab(label, pat=r"([\d.]+)\s*%"):
            mm = _re.search(_re.escape(label) + r"\s*:\s*" + pat, html)
            return float(mm.group(1)) if mm else None
        repo = grab("Policy Repo Rate")
        sdf  = grab("Standing Deposit Facility (SDF) Rate")
        cpi  = grab("CPI Inflation")
        if repo: m["repo"] = repo; live.add("repo")
        if sdf:  m["sdf"]  = sdf;  live.add("sdf")
        if cpi:  m["cpi"]  = cpi;  live.add("cpi")
        # forex reserves headline — label variants seen on the portal over time
        # v92e: the old pattern demanded a B/M letter glued to the number
        # ("$702.0B"). The portal writes the unit in a separate column header
        # ("US$ Million"), so this branch never once matched and the tab fell
        # through to a hard-coded default for weeks. Now: accept the number on
        # its own, and decide the unit from its magnitude — India's reserves
        # are ~700 in $bn and ~700,000 in $mn, three orders apart, so there is
        # no ambiguity to get wrong.
        for lbl in ("Foreign Exchange Reserves", "Forex Reserves",
                    "FX Reserves", "Foreign Exchange Reserves (US$ Million)",
                    "Total Reserves", "Foreign Currency Assets"):
            mm = _re.search(_re.escape(lbl) +
                            r"[^\d$]{0,40}\$?\s*([\d,]+(?:\.\d+)?)\s*([BbMm]?)",
                            html)
            if mm:
                v = float(mm.group(1).replace(",", ""))
                unit = mm.group(2).lower()
                if unit == "m" or v > 50000:      # quoted in $ million
                    v = v / 1000.0
                if 300 < v < 2000:          # sanity: India reserves in $bn
                    m["reserves_bn"] = round(v, 1)
                    live.add("reserves_bn")
                    md = _re.search(_re.escape(lbl) + r".{0,80}?as on ([A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4})",
                                    html)
                    if md:
                        m["reserves_asof"] = md.group(1)
                    break
        # CPI month tag e.g. "(May-26)"
        mt = _re.search(r"CPI Inflation\s*:\s*[\d.]+%\s*\(([A-Za-z]{3})-\d{2}\)", html)
        if mt: m["cpi_month"] = mt.group(1)
        print(f"  macro: RBI portal OK ("
              + ", ".join(f"{k} {m[k]}" for k in sorted(live)) + ")"
              if live else "  macro: RBI portal answered but carried none of "
                           "the fields we read — nothing published")
    except Exception as e:
        print(f"  macro: RBI portal unavailable ({type(e).__name__}) — keeping last-known repo/CPI")

    # v92: the same page, read properly — credit, money, prices, the yield
    m["_blocks"] = scan_rbi_extra(rbi_html) if rbi_html else {}

    # ── v92g: the extended sweep feeds the headline macro object ──────────
    # These were literals in MACRO_DEFAULTS for months. The portal carries
    # them; we simply were not reading them into the object the page uses.
    _b = m["_blocks"]

    def _bv(k):
        x = _b.get(k)
        return x["v"] if x and x.get("v") is not None else None

    for _src, _dst in (("iip_p", "iip"), ("gdp_growth", "gdp_fy"),
                       ("call_rate", "mibor_on"), ("msf", "msf"),
                       ("gsec10", "gsec10")):
        _v = _bv(_src)
        if _v is not None:
            m[_dst] = _v
            live.add(_dst)
    # the real yield is arithmetic on two live numbers, so it is live whenever
    # both of its inputs are — never a stored constant
    if "gsec10" in live and "cpi" in live:
        m["real_10y"] = round(m["gsec10"] - m["cpi"], 2)
        live.add("real_10y")

    # ── v92j: reserves get their own transports rather than riding on a
    # regex against the portal landing page, which never once matched.
    if "reserves_bn" not in m:
        _bn, _asof, _src = fetch_reserves_rbi()
        if _bn:
            m["reserves_bn"] = _bn
            live.add("reserves_bn")
            if _asof:
                m["reserves_asof"] = _asof
            m["reserves_src"] = _src

    m["_live"] = sorted(live)
    if live:
        print(f"  macro: {len(live)} field(s) read live this run "
              f"({', '.join(sorted(live))})")
    else:
        print("  macro: NOTHING read live this run — every macro value on the "
              "page is carried forward and will be flagged as such")

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


# ═══════════════════════════════════════════════════════════════════════
#  v92: REGIME HISTORY — the long weekly series behind "given this macro
#  regime, how does the micro behave". India inputs only: each one has a
#  direct transmission channel into Indian equities.
# ═══════════════════════════════════════════════════════════════════════
REGIME_MACRO = {
    "^NSEI":      "Nifty 50",       # the trend/growth axis
    "^INDIAVIX":  "India VIX",      # domestic risk pricing
    "INR=X":      "USD/INR",        # external pressure on the rupee
    "BZ=F":       "Brent",          # the import bill — India's terms of trade
}
SECTOR_IDX = {   # NSE sector indices Yahoo carries — the micro side
    "^NSEBANK":    "Bank",
    "^CNXIT":      "IT",
    "^CNXAUTO":    "Auto",
    "^CNXPHARMA":  "Pharma",
    "^CNXFMCG":    "FMCG",
    "^CNXMETAL":   "Metal",
    "^CNXENERGY":  "Energy",
    "^CNXREALTY":  "Realty",
    "^CNXPSUBANK": "PSU Bank",
    "^CNXINFRA":   "Infra",
    "^CNXMEDIA":   "Media",
    "^CNXFIN":     "Fin Services",
    "^CNXCONSUM":  "Consumption",
}
REGIME_MIN_WK = 120      # a series must have this many weeks to be usable


def build_regime_history(stamp, prev):
    """{long, ldates, lnames, lsect, long_date, long_updated} or the previous
    block. Rebuilt once a day like the universe; any failure preserves what
    was published before, so the page never loses its history."""
    today = f"{stamp:%Y%m%d}"
    KEYS = ("long", "ldates", "lnames", "lsect", "long_date", "long_updated")
    keep = {k: prev[k] for k in KEYS if k in prev}
    if prev.get("long_date") == today and prev.get("long"):
        print(f"  regime history: already built today "
              f"({len(prev.get('long', {}))} series) — carried forward")
        return keep

    syms = list(REGIME_MACRO) + list(SECTOR_IDX)
    try:
        df = yf.download(syms, period="5y", interval="1wk",
                         auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if hasattr(df.columns, "levels") else df[["Close"]]
        close = close.dropna(how="all").sort_index()
    except Exception as e:
        print(f"  regime history: download failed ({type(e).__name__}) — "
              f"previous block kept")
        return keep

    if close.shape[0] < REGIME_MIN_WK:
        print(f"  regime history: only {close.shape[0]} weekly rows — "
              f"previous block kept")
        return keep

    ldates = [int(d.strftime("%Y%m%d")) for d in close.index]
    long_ = {}
    for sym in close.columns:
        col = close[sym]
        if col.dropna().shape[0] < REGIME_MIN_WK:
            continue
        long_[sym] = [None if (v != v) else _rnd(float(v))
                      for v in col.tolist()]

    have_macro = [k for k in REGIME_MACRO if k in long_]
    if "^NSEI" not in long_ or len(have_macro) < 2:
        print(f"  regime history: regime inputs incomplete "
              f"({', '.join(have_macro) or 'none'}) — previous block kept")
        return keep

    lsect = {k: v for k, v in SECTOR_IDX.items() if k in long_}
    lnames = {k: v for k, v in
              list(REGIME_MACRO.items()) + list(SECTOR_IDX.items())
              if k in long_}
    print(f"  regime history: {len(long_)} series × {len(ldates)} weekly "
          f"points ({len(lsect)} sector indices, "
          f"{len(have_macro)}/{len(REGIME_MACRO)} regime inputs)")
    return {"long": long_, "ldates": ldates, "lnames": lnames, "lsect": lsect,
            "long_date": today,
            "long_updated": f"{stamp:%a %b %d, %Y %H:%M} IST"}


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
        # v92: the long weekly history behind the regime -> micro engine
        try:
            out.update(build_regime_history(stamp, prev) or {})
        except Exception as e:
            print(f"  regime history: failed ({type(e).__name__}) — core "
                  f"history unaffected, previous block kept")
            for k in ("long", "ldates", "lnames", "lsect", "long_date",
                      "long_updated"):
                if k in prev:
                    out[k] = prev[k]
        with open("history_1y.json", "w") as f:
            json.dump(out, f, separators=(",", ":"))
        print(f"  history: history_1y.json written ({len(series)} core series "
              f"× {len(dates)} days + {len(out.get('wf', {}))} screened shares "
              f"+ {len(out.get('names', {}))} searchable companies "
              f"+ {len(out.get('long', {}))} × {len(out.get('ldates', []))}wk "
              f"regime history)")
        return {"core": len(series), "screened": len(out.get("wf", {})),
                "searchable": len(out.get("names", {})),
                "regime_series": len(out.get("long", {})),
                "regime_weeks": len(out.get("ldates", []))}
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

# v93: AMFI's own NAVAll.txt is a 7MB single file; mfapi.in serves the
# same AMFI numbers per scheme as a few KB of JSON off a CDN. Scheme codes
# are AMFI's own, so this is the same source read through a lighter pipe —
# not a different, disagreeing provider.
MFAPI = {
    "Index \u00b7 Nifty 50": 120716,   # UTI Nifty 50 Index Fund - Direct - Growth
    "Gilt (long)":            120487,   # SBI Magnum Gilt Fund - Direct - Growth
    "Gold (FoF)":             119773,   # Nippon India Gold Savings - Direct - Growth
    "Liquid (cash)":          119807,   # HDFC Liquid Fund - Direct - Growth
}


def _amfi_via_mfapi():
    out = {}
    for cat, code in MFAPI.items():
        try:
            j = json.loads(_get(f"https://api.mfapi.in/mf/{code}",
                                timeout=20, tries=2))
        except Exception:
            continue
        rows = j.get("data") or []
        if len(rows) < 25:
            continue
        try:
            nav = float(rows[0]["nav"])
            m1 = float(rows[min(21, len(rows) - 1)]["nav"])
            y1 = float(rows[min(250, len(rows) - 1)]["nav"])
        except Exception:
            continue
        if not (nav > 0 and m1 > 0 and y1 > 0):
            continue
        out[cat] = {"name": (j.get("meta") or {}).get("scheme_name", cat),
                    "nav": round(nav, 4),
                    "m1": round((nav / m1 - 1) * 100, 2),
                    "y1": round((nav / y1 - 1) * 100, 2),
                    "date": rows[0].get("date", ""),
                    "src": "mfapi.in (AMFI data)"}
    if out:
        print(f"  amfi: official file refused; mfapi.in mirror carried "
              f"{len(out)}/{len(MFAPI)} categories")
    return out


def fetch_amfi():
    """Official AMFI NAV file — all schemes, plain text, no key, no anti-bot.
    v88: format-proof matcher — names are normalized (lowercase, punctuation
    collapsed) and matched on tokens, with preferred-AMC patterns first and a
    generic category fallback, so AMFI renaming can't zero the table."""
    raw = None
    # v93: the official file is ~7MB off AMFI's own origin and has been
    # timing out from the runner — which is why the fund table has been
    # empty, not the redirect (the portal host was already first in this
    # list). mfapi.in mirrors the same AMFI data as small per-scheme JSON
    # off a CDN and is tried below if every official mirror refuses.
    for url in ("https://portal.amfiindia.com/spages/NAVAll.txt",
                "https://www.amfiindia.com/spages/NAVAll.txt",
                "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
                "?frmdt=&todt=",
                "https://www.amfiindia.com/spages/NAVOpen.txt"):
        try:
            raw = _get(url, timeout=90)
            if raw and ";" in raw:
                break
        except Exception as e:
            print(f"  amfi: {url.split('/')[2]} failed ({type(e).__name__})")
            raw = None
    if not raw:
        mm = _amfi_via_mfapi()
        if mm:
            return mm
        print("  amfi: EVERY mirror refused — no NAVs this run. The fund table "
              "will say so rather than showing yesterday's number as today's.")
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
    fresh = bool(mf)
    for cat, v in (mf or {}).items():
        c = cur["cats"].get(cat, {"trail": []})
        c["name"], c["nav"], c["date"] = v["name"], v["nav"], v["date"]
        tr = [t for t in (c.get("trail") or []) if isinstance(t, list)]
        if not tr or tr[-1][0] != v["date"]:
            tr.append([v["date"], v["nav"]])
        c["trail"] = tr[-400:]
        cur["cats"][cat] = c
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    # v92g: `updated` used to advance whether or not anything was fetched,
    # which is the same lie the price constants were telling. It now means
    # "when a NAV was last actually read"; `checked` is the run stamp.
    if fresh:
        cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    cur["stale"] = not fresh
    cur["checked"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    new_blk = "window.MF_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  amfi: MF_LIVE patched ({len(cur['cats'])} categories"
              + ("" if fresh else ", NOTHING fetched — flagged stale") + ")")
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
        print(f"  flows: NSE unavailable ({type(e).__name__}) — trying mirrors")
    # v93: NSE refuses datacenter IPs whatever the cookie dance, which is why
    # FLOWS_LIVE has been empty on the live site since it was written. These
    # four render the same NSE/BSE provisional numbers. Whichever answers is
    # named in the run log, so the page never implies a source it did not use.
    for name, url in FLOW_HTML:
        try:
            txt = _detag(_get(url, timeout=25, tries=1))
        except Exception:
            continue
        got = _flows_from_text(txt)
        if got:
            fii, dii, asof = got
            print(f"  flows: {name} OK (FII {fii:+,.0f} Cr, DII {dii:+,.0f} Cr"
                  + (f", {asof}" if asof else "") + ")")
            return {"fii": fii, "dii": dii, "asof": asof, "src": name}
    print("  flows: NSE and all four mirrors refused — the table will say so "
          "rather than showing a remembered number")
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
    if fl.get("fii") is not None:
        cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    cur["stale"] = fl.get("fii") is None
    cur["checked"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    new_blk = "window.FLOWS_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  flows: FLOWS_LIVE patched (trail {len(cur['trail'])})")
    else:
        print("  flows: FLOWS_LIVE block not found (skipped)")
    return html


# ── v92j · FOREX RESERVES, ACTUALLY SCRAPED ────────────────────────────────
#  The weekly headline lives in the RBI's Weekly Statistical Supplement,
#  published every Friday evening. Until now the only attempt to read it was
#  a regex against the data.rbi.org.in landing page, which does not carry the
#  number in that shape — so RESERVES_LIVE has been a default with a fresh
#  timestamp bolted on. These are four independent doors into the same table.
#  All are RBI, all are keyless, none is Cloudflare.
RESERVE_URLS = [
    # the new RBI site (rbi.org.in content migrated here in 2024)
    "https://website.rbi.org.in/web/rbi/statistics/weekly-statistical-supplement",
    # WSS section 2 on the legacy site — this is the reserves table itself
    "https://www.rbi.org.in/Scripts/WSSViewDetail.aspx?TYPE=Section&PARAM1=2",
    "https://rbi.org.in/Scripts/WSSViewDetail.aspx?TYPE=Section&PARAM1=2",
    # the data portal landing page, kept as the last door rather than the first
    "https://data.rbi.org.in/",
]
RESERVE_RSS = "https://www.rbi.org.in/pressreleases_rss.xml"

_RSV_LABELS = ("Total Reserves", "Foreign Exchange Reserves", "Forex Reserves",
               "FX Reserves", "Total reserves", "Reserves (US$")


def _detag(s):
    """HTML to whitespace-normalised text. The WSS tables are plain markup —
    no JS rendering — so the numbers survive this intact."""
    s = _re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    s = _re.sub(r"(?s)<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return _re.sub(r"\s+", " ", s)


def _rsv_from_text(txt):
    """Pull (value_in_usd_bn, as_on_string) out of WSS-shaped text.

    The unit is never guessed from a letter glued to the number — that is the
    bug that made this fail silently for weeks. It is decided by magnitude:
    India's reserves are ~700 in $bn and ~700,000 in $mn, three orders apart,
    and the rupee-crore column is ~60,00,000, another order beyond that. Any
    reading that does not land inside the $bn sanity band is discarded rather
    than rounded into one."""
    for lbl in _RSV_LABELS:
        for mm in _re.finditer(_re.escape(lbl), txt):
            window = txt[mm.end(): mm.end() + 400]
            for nm in _re.finditer(r"([\d][\d,]{2,}(?:\.\d+)?)", window):
                try:
                    v = float(nm.group(1).replace(",", ""))
                except ValueError:
                    continue
                if 300 <= v <= 1500:              # already $bn
                    bn = v
                elif 300_000 <= v <= 1_500_000:   # $ million
                    bn = v / 1000.0
                else:
                    continue                      # rupee crore, or noise
                back = txt[max(0, mm.start() - 300): mm.end() + 400]
                dm = _re.search(r"as on\s+([A-Za-z]{3,9}\.?\s*\d{1,2},?\s*\d{4}"
                                r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", back, _re.I)
                return round(bn, 1), (dm.group(1).strip() if dm else "")
    return None, ""


def fetch_reserves_rbi():
    """Weekly forex reserves from the RBI, tried across four transports plus
    the press-release feed. Returns (bn, as_on, source) or (None, '', '')."""
    for url in RESERVE_URLS:
        try:
            raw = _get(url, timeout=30)
        except Exception as e:
            print(f"  reserves: {url.split('/')[2]} refused ({type(e).__name__})")
            continue
        bn, asof = _rsv_from_text(_detag(raw))
        if bn:
            print(f"  reserves: ${bn}bn read from {url.split('/')[2]}"
                  + (f" (as on {asof})" if asof else " — no as-on date in the page"))
            return bn, asof, url.split("/")[2]
    # last door: the weekly press release, found through the RSS feed
    try:
        feed = _get(RESERVE_RSS, timeout=25)
        links = _re.findall(r"<link>\s*([^<\s]+)\s*</link>", feed)
        titles = _re.findall(r"<title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</title>", feed, _re.S)
        for t, l in zip(titles, links):
            if "weekly statistical supplement" in t.lower() or "foreign exchange reserve" in t.lower():
                bn, asof = _rsv_from_text(_detag(_get(l, timeout=30)))
                if bn:
                    print(f"  reserves: ${bn}bn read from the weekly press release")
                    return bn, asof, "rbi press release"
                break
    except Exception as e:
        print(f"  reserves: press-release feed unavailable ({type(e).__name__})")
    print("  reserves: every RBI transport failed — the tab will say the figure "
          "is carried forward rather than restamp it as today's")
    return None, "", ""


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
    cur = {"total_bn": 0, "asof": "", "ath_bn": 0,
           "trail": [], "monthly": [], "updated": "", "stale": False}
    if blk:
        try:
            cur.update(json.loads(_re.sub(r"(\w+):", r'"\1":', blk.group(1))))
        except Exception:
            try:
                cur.update(json.loads(blk.group(1)))
            except Exception:
                pass
    fresh = m.get("reserves_bn")
    total = float(fresh if fresh else (cur.get("total_bn") or 0))
    if not total:
        print("  reserves: no figure has ever been read and none today — "
              "the tab will say so rather than invent one")
        return html
    cur["total_bn"] = round(total, 1)
    # the flag the page renders off: True means "this is the last number we
    # genuinely read, not a number we read today".
    cur["stale"] = not bool(fresh)
    if m.get("reserves_asof"):
        cur["asof"] = m["reserves_asof"]
    cur["ath_bn"] = round(max(float(cur.get("ath_bn", 0) or 0), total), 1)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    tag = stamp.strftime("%Y-%m-%d")
    trail = [t for t in (cur.get("trail") or []) if isinstance(t, list) and len(t) == 2]
    if fresh and (not trail or abs(trail[-1][1] - total) >= 0.05):
        if not trail or trail[-1][0] != tag:
            trail.append([tag, round(total, 1)])
    cur["trail"] = trail[-30:]
    fred = fetch_fred_reserves()
    if fred:
        cur["monthly"] = fred
    # v92j: `updated` used to be written unconditionally, which is how a
    # default came to wear today's timestamp for weeks. It now moves only on
    # a run that genuinely read a figure. `checked` records that we tried.
    if fresh:
        cur["updated"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    cur["checked"] = stamp.strftime("%a %b %d, %Y %H:%M IST")
    if m.get("reserves_src"):
        cur["src"] = m["reserves_src"]
    new_blk = "window.RESERVES_LIVE = " + json.dumps(cur) + ";"
    if blk:
        html = html[:blk.start()] + new_blk + html[blk.end():]
        print(f"  reserves: RESERVES_LIVE patched (${cur['total_bn']}bn, "
              f"trail {len(cur['trail'])}, monthly {len(cur['monthly'])})")
    else:
        print("  reserves: RESERVES_LIVE block not found (skipped)")
    return html


def patch_macro(html, m, stamp=None):
    """Patch the MODEL constants (so the regime engine recomputes) plus a few
    clearly-anchored display values. Conservative by design."""
    if stamp is None:
        stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    n = 0
    live = set(m.get("_live") or [])
    if m.get("reserves_bn"):
        live.add("reserves_bn")
    # v92g: every one of these used to carry a literal default, so a dead
    # scrape rewrote the visible page with typed-in numbers and counted it as
    # a patch. A field is now written only if this run actually read it.
    subs = []
    if "cpi" in live:
        subs += [
            (r"(RC_CPI\s*=\s*)[\d.]+",          rf"\g<1>{m['cpi']}"),
            (r"(cpi:\s*)[\d.]+(,\s*//\s*live)", rf"\g<1>{m['cpi']}\g<2>"),
            (r"(CPI )[\d.]+(% " + m.get('cpi_month', 'May')
             + r" \(Jun 12 print\))", rf"\g<1>{m['cpi']}\g<2>"),
        ]
    if "iip" in live:
        subs.append((r"(RC_IIP\s*=\s*)[\d.]+", rf"\g<1>{m['iip']}"))
    if "repo" in live:
        subs += [
            (r"(REPO_NOW\s*=\s*)[\d.]+", rf"\g<1>{m['repo']}"),
            (r"(Repo Rate</[^>]+>\s*<[^>]+>)[\d.]+%", rf"\g<1>{m['repo']}%"),
        ]
    if "sdf" in live:
        subs.append((r"(SDF \(floor\)</[^>]+>\s*<[^>]+>)[\d.]+%",
                     rf"\g<1>{m['sdf']}%"))
    if "msf" in live:
        subs.append((r"(MSF \(ceiling\)</[^>]+>\s*<[^>]+>)[\d.]+%",
                     rf"\g<1>{m['msf']}%"))
    # v92e: only rewrite the reserves headline when this run actually read one.
    if m.get("reserves_bn"):
        subs.append(
            (r"\$" + r"\d{3}\.\d" + r"bn(</[^>]*>\s*<[^>]*>\+?\$?[\d.]+M? WoW)",
             rf"${m['reserves_bn']}bn\g<1>"))
    for pat, rep in subs:
        try:
            html, c = _re.subn(pat, rep, html)
            n += c
        except Exception:
            pass
    # ── v92g: MACRO_LIVE is MERGED, never re-minted ───────────────────────
    # The old code rebuilt the whole object from m.get(field, <literal>), so
    # a failed scrape re-published a full set of hard-coded numbers under a
    # fresh timestamp. Now: read what is on the page, overwrite only the
    # fields this run genuinely read, and record when each was last read.
    ML_FIELDS = ["reserves_bn", "reserves_ath", "cpi", "cpi_prev", "repo",
                 "gdp_fy", "gdp_ny", "iip", "nominal_gdp", "real_10y",
                 "mibor_3m", "mibor_on"]
    # fields no free Indian source publishes in machine-readable form; they
    # are shipped constants and the page says so rather than implying a feed
    STATIC = ["reserves_ath", "gdp_ny", "nominal_gdp", "mibor_3m"]

    cur_ml = {}
    _mlm = _re.search(r"window\.MACRO_LIVE\s*=\s*\{([^}]*)\};", html)
    if _mlm:
        for k in ML_FIELDS:
            kk = _re.search(k + r":\s*(-?[\d.]+)", _mlm.group(1))
            if kk:
                try:
                    cur_ml[k] = float(kk.group(1))
                except Exception:
                    pass
    trail = []
    _tr = _re.search(r"cpi_trail:\s*\[([^\]]*)\]", html)
    if _tr:
        for t in _tr.group(1).split(","):
            try:
                trail.append(float(t.strip()))
            except Exception:
                pass

    # a genuinely NEW CPI print rolls the six-month path forward. This is how
    # cpi_trail stops being a typed list and becomes accrued observation.
    if "cpi" in live and m.get("cpi") is not None:
        if not trail or abs(trail[-1] - m["cpi"]) > 1e-9:
            if trail:
                cur_ml["cpi_prev"] = trail[-1]
                live.add("cpi_prev")
            trail = (trail + [m["cpi"]])[-6:]

    out = {}
    for k in ML_FIELDS:
        if k in live and m.get(k) is not None:
            out[k] = m[k]
        elif k in cur_ml:
            out[k] = cur_ml[k]
    ml_new = ("window.MACRO_LIVE = { "
              + ", ".join(f"{k}: {out[k]}" for k in ML_FIELDS if k in out)
              + (f", cpi_trail: {trail}" if trail else "") + " };")
    html, ml_c = _re.subn(r"window\.MACRO_LIVE\s*=\s*\{[^}]*\};",
                          ml_new.replace("\\", "\\\\"), html, count=1)
    if ml_c:
        n += ml_c

    # ── provenance: per field, when it was last genuinely read ────────────
    prov = {"seen": {}, "live": sorted(live), "static": STATIC,
            "run": f"{stamp:%a %b %d, %Y %H:%M} IST"}
    _pm = _re.search(r"window\.MACRO_PROV\s*=\s*(\{.*?\});", html)
    if _pm:
        try:
            old = json.loads(_pm.group(1))
            if isinstance(old.get("seen"), dict):
                prov["seen"] = dict(old["seen"])
        except Exception:
            pass
    for k in live:
        prov["seen"][k] = prov["run"]
    prov["never"] = sorted(k for k in ML_FIELDS
                           if k not in prov["seen"] and k not in STATIC)
    if _pm:
        html = (html[:_pm.start()] + "window.MACRO_PROV = "
                + json.dumps(prov, separators=(",", ":")) + ";"
                + html[_pm.end():])

    print(f"  patch macro: {n} anchored values · "
          + (f"{len(live)} read live ({', '.join(sorted(live))})" if live
             else "NOTHING read live — page keeps its last real values and "
                  "flags every one of them as carried forward")
          + f" · {len(prov['never'])} field(s) never read live so far")
    return html, n



# ═══════════════════════════════════════════════════════════════════════
#  CONTRACT AUDIT — the updater writes into named structures in the HTML.
#  If a rebuild renames or removes one, the patcher silently does nothing and
#  the page quietly serves the last-good numbers for ever. This check runs
#  every pass and names anything that has gone missing, so a broken contract
#  shows up in the Action log the same day it breaks — not months later.

# ═══════════════════════════════════════════════════════════════════════
#  v93 · THE EXTERNAL AND FISCAL ACCOUNTS.
#  Three series the terminal has been reasoning around without ever
#  carrying: the monthly trade balance, the monthly fiscal deficit, and the
#  quarterly current account. All three are published free, on schedule, by
#  the Government of India in plain markup. There was never a paywall — we
#  simply were not reading them.
#
#  These are monthly/quarterly, not tick data. They legitimately carry
#  forward between releases, and that is NOT the failure mode v92g fixed:
#  each one carries its own reference period, so a figure that has stopped
#  advancing says which month it is for. A stale monthly print that names
#  its month is honest; a stale one wearing today's date is not.
# ═══════════════════════════════════════════════════════════════════════

PIB_RSS = [
    "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=2&Regid=3",
    "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
    "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=2&Regid=3",
]
PIB_PAGE = ("https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=%s",
            "https://www.pib.gov.in/PressReleasePage.aspx?PRID=%s&reg=3&lang=1")


def _pib_recent(keywords):
    """[(prid, title)] for RSS items whose title carries every keyword."""
    hits = []
    for feed in PIB_RSS:
        try:
            xml = _get(feed, timeout=25, tries=2)
        except Exception:
            continue
        for mm in _re.finditer(r"<item>(.*?)</item>", xml, _re.S | _re.I):
            blk = mm.group(1)
            t = _re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>",
                           blk, _re.S)
            l = _re.search(r"PRID=(\d+)", blk)
            if not (t and l):
                continue
            title = _re.sub(r"\s+", " ", t.group(1)).strip()
            low = title.lower()
            if all(k in low for k in keywords):
                hits.append((l.group(1), title))
        if hits:
            break
    return hits


def _trade_from_text(txt):
    """(exports_bn, imports_bn, period) from a Commerce Ministry release.

    The sentence form has been stable for years:
      "Merchandise exports during June 2026 were US$ 40.41 Billion as
       compared to US$ 34.98 Billion in June 2025."
    Sanity: India's monthly merchandise trade runs roughly $20-120bn a side.
    Anything outside that is a mis-parse, not a surprise, and is discarded.
    """
    out = {}
    for key, word in (("exports", "exports"), ("imports", "imports")):
        mm = _re.search(r"Merchandise\s+" + word +
                        r"\s+(?:during|in|for)\s+([A-Z][a-z]+\s+\d{4})\s+"
                        r"(?:were|was|stood at|is estimated at)\s*"
                        r"US\$?\s*([\d.]+)\s*[Bb]illion", txt)
        if not mm:
            mm = _re.search(r"Merchandise\s+" + word +
                            r"[^.]{0,60}?([A-Z][a-z]+\s+\d{4})[^.]{0,40}?"
                            r"US\$?\s*([\d.]+)\s*[Bb]illion", txt)
        if mm:
            try:
                v = float(mm.group(2))
            except Exception:
                continue
            if 10 <= v <= 150:
                out[key] = round(v, 2)
                out.setdefault("period", mm.group(1))
    if "exports" in out and "imports" in out:
        out["deficit"] = round(out["imports"] - out["exports"], 2)
        return out
    return {}


def fetch_trade():
    """Monthly merchandise trade — exports, imports, the deficit, and the
    month they are for. Discovery through PIB's RSS, which is the actual
    Indian release wire and replaces the Trading Economics placeholder."""
    hits = _pib_recent(["trade"]) + _pib_recent(["exports"])
    seen = set()
    for prid, title in hits:
        if prid in seen:
            continue
        seen.add(prid)
        for tmpl in PIB_PAGE:
            try:
                txt = _detag(_get(tmpl % prid, timeout=30, tries=2))
            except Exception:
                continue
            t = _trade_from_text(txt)
            if t:
                t["src"] = "PIB " + prid
                print(f"  trade: {t['period']} exports ${t['exports']}bn, "
                      f"imports ${t['imports']}bn, deficit ${t['deficit']}bn "
                      f"(PIB {prid})")
                return t
    print("  trade: no Commerce Ministry release on the wire this run — the "
          "page keeps the last month it read AND says which month that is")
    return {}


def _fy_tag(y, m):
    """India's FY runs April-March. (fy_start_year, 'YYZZ')."""
    fs = y if m >= 4 else y - 1
    return fs, f"{fs % 100:02d}{(fs + 1) % 100:02d}"


def fetch_fiscal():
    """Union fiscal deficit from the CGA's monthly accounts.

    The URL is fully predictable, which is rare enough to be worth saying:
      cga.nic.in/writereaddata/MonthAccount/{month}{year}/DATA{fy}.htm
    Walk backwards from this month — the accounts publish about a month in
    arrears, so the current month is normally a 404 and the one before it
    is the live one."""
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    y, m = now.year, now.month
    for _ in range(7):
        fs, fy = _fy_tag(y, m)
        for host in ("https://cga.nic.in", "https://cga.gov.in"):
            url = f"{host}/writereaddata/MonthAccount/{m}{y}/DATA{fy}.htm"
            try:
                txt = _detag(_get(url, timeout=25, tries=1))
            except Exception:
                continue
            # the label is followed by CGA's own line reference "(12-7)",
            # which carries digits — so this cannot be [^\d]* to the number
            mm = _re.search(r"Fiscal\s*Deficit\b.{0,25}?"
                            r"([\d,]{5,})\s+([\d,]{3,})\s+([\d.]+)\s*%"
                            r"(?:\s*\(\s*([\d.]+)\s*%\s*\))?", txt)
            if not mm:
                continue
            try:
                be = float(mm.group(1).replace(",", ""))
                act = float(mm.group(2).replace(",", ""))
                pct = float(mm.group(3))
            except Exception:
                continue
            # sanity: the BE runs ~₹15-25 lakh crore; actuals cannot exceed
            # it by much this early, and a percentage over 200 is a mis-read
            if not (5e5 <= be <= 5e6 and 0 < act <= be * 1.5 and 0 < pct <= 200):
                continue
            hdr = _re.search(r"END OF\s+([A-Z]+)\s+(\d{4})", txt, _re.I)
            out = {"be_cr": round(be), "actual_cr": round(act),
                   "pct_be": round(pct, 1),
                   "pct_be_ly": (round(float(mm.group(4)), 1)
                                 if mm.group(4) else None),
                   "period": (f"{hdr.group(1).title()} {hdr.group(2)}"
                              if hdr else f"{m}/{y}"),
                   "fy": f"FY{fs % 100:02d}-{(fs + 1) % 100:02d}",
                   "src": url}
            print(f"  fiscal: {out['period']} deficit ₹{act:,.0f} Cr = "
                  f"{pct}% of the {out['fy']} BE (CGA)")
            return out
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    print("  fiscal: no CGA monthly account answered — the page keeps the "
          "last month it read AND says which month that is")
    return {}


def fetch_bop():
    """Quarterly current account balance from RBI's BoP press release."""
    urls = ["https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
            "https://www.rbi.org.in/pressreleases_rss.xml",
            "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"]
    for u in urls:
        try:
            raw = _get(u, timeout=25, tries=1)
        except Exception:
            continue
        txt = _detag(raw)
        mm = _re.search(r"current account (?:deficit|balance|surplus)[^.]{0,120}?"
                        r"US\$?\s*([\d.]+)\s*billion[^.]{0,60}?"
                        r"([\d.]+)\s*per cent of GDP", txt, _re.I)
        if not mm:
            mm = _re.search(r"[Cc]urrent [Aa]ccount [Dd]eficit \(CAD\)[^.]{0,120}?"
                            r"US\$?\s*([\d.]+)\s*billion[^.]{0,80}?"
                            r"([\d.]+)\s*per cent", txt)
        if mm:
            try:
                bn, pct = float(mm.group(1)), float(mm.group(2))
            except Exception:
                continue
            if 0 <= bn <= 80 and 0 <= pct <= 8:
                q = _re.search(r"(Q[1-4])[^.]{0,20}(\d{4}-\d{2})", txt)
                out = {"cad_bn": round(bn, 1), "cad_pct_gdp": round(pct, 2),
                       "period": (f"{q.group(1)} {q.group(2)}" if q else ""),
                       "src": u}
                print(f"  bop: current account ${bn}bn ({pct}% of GDP)"
                      + (f" {out['period']}" if out["period"] else ""))
                return out
    print("  bop: no parseable BoP release — the page keeps the last quarter "
          "it read AND says which quarter that is")
    return {}


# ── FII/DII: NSE blocks datacenter IPs, so it cannot be the only transport ──
FLOW_HTML = [
    ("groww",   "https://groww.in/fii-dii-data"),
    ("5paisa",  "https://www.5paisa.com/share-market-today/fii-dii-data"),
    ("bstd",    "https://www.business-standard.com/markets/fii-dii-activity"),
    ("nifttr",  "https://www.niftytrader.in/fii-dii-data"),
]
_MON = ("jan feb mar apr may jun jul aug sep oct nov dec")


def _flows_from_text(txt):
    """(fii, dii, asof) in ₹ Cr from a rendered FII/DII page.

    Deliberately conservative: both legs must be present, both must be
    inside a sane daily band, and they must not be identical (which is what
    a broken parse that matched the same number twice looks like)."""
    def leg(word):
        for pat in (word + r"[^\d\-+₹]{0,80}?([-+]?\s*₹?\s*[\d,]+(?:\.\d+)?)\s*(?:Cr|crore)",
                    word + r"[^\d\-+₹]{0,80}?\(₹\s*Cr\)\s*([-+]?\s*[\d,]+(?:\.\d+)?)",
                    word + r"[^\d\-+₹]{0,120}?([-+]\s*[\d,]+(?:\.\d+)?)"):
            mm = _re.search(pat, txt, _re.I)
            if mm:
                try:
                    return float(mm.group(1).replace(",", "")
                                 .replace("₹", "").replace(" ", ""))
                except Exception:
                    continue
        return None
    fii = leg(r"FII(?:/FPI)?")
    if fii is None:
        fii = leg(r"FPI")
    dii = leg(r"DII")
    if fii is None or dii is None:
        return None
    if abs(fii) > 200000 or abs(dii) > 200000 or fii == dii:
        return None
    d = _re.search(r"(\d{1,2}[ \-/](?:" + "|".join(_MON.split()) +
                   r")[a-z]*[ \-/]\d{2,4})", txt, _re.I)
    return fii, dii, (d.group(1) if d else "")


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
    "MACRO_X":       "window.MACRO_X",
    "PRICE_HEALTH":  "window.PRICE_HEALTH",
    "MACRO_PROV":    "window.MACRO_PROV",
    "RUN_LOG":       "window.RUN_LOG",
    "regime panel":  'id="regime-micro"',
    "RESERVES_LIVE": "window.RESERVES_LIVE",
    "MF_LIVE":       "window.MF_LIVE",
    "FLOWS_LIVE":    "window.FLOWS_LIVE",
    "TRADE_LIVE":    "window.TRADE_LIVE",
    "FISCAL_LIVE":   "window.FISCAL_LIVE",
    "BOP_LIVE":      "window.BOP_LIVE",
    "news slot":     "<!--NEWSLIVE_START-->",
    "manifest slot": "<!--MANIFEST_START-->",
    "header stamp":  "· Models:",
}


# ═══════════════════════════════════════════════════════════════════════
#  v92g · THE RUN LOG.
#  The manifest on the live page said "Last run: Fri Jul 24, 13:27 IST" while
#  the header said Mon Jul 28 09:00 — two stamps written forty lines apart in
#  the same function, disagreeing by four days, which can only happen if the
#  pipeline stopped between them. Nobody noticed for a week and a half,
#  because the page had no way to notice on its own.
#
#  RUN_LOG fixes that permanently: each subsystem records what it managed on
#  this run AND the last run it actually succeeded on. The page renders the
#  difference. A dead pipeline now announces itself on the front page the
#  same day, in the reader's face, instead of hiding behind a fresh header.
# ═══════════════════════════════════════════════════════════════════════
def patch_extern(html, var, new, stamp):
    """Maintain window.<var> for a monthly/quarterly series.

    The carry-forward rule that makes this honest: `updated` advances ONLY
    on a real read. `checked` always advances, so the page can show the gap
    between when we last looked and when the number last changed — and every
    one of these objects carries its own `period`, so a figure that has not
    moved says which month or quarter it is for."""
    mm = _re.search(r"window\." + var + r"\s*=\s*(\{.*?\});", html)
    cur = {}
    if mm:
        try:
            cur = json.loads(mm.group(1)) or {}
        except Exception:
            cur = {}
    run = f"{stamp:%a %b %d, %Y %H:%M} IST"
    if new:
        cur.update(new)
        cur["updated"] = run
        cur["stale"] = False
    else:
        cur["stale"] = bool(cur.get("period"))
    cur["checked"] = run
    blob = "window." + var + " = " + json.dumps(cur, separators=(",", ":")) + ";"
    if mm:
        return html[:mm.start()] + blob + html[mm.end():], bool(new)
    print(f"  {var}: anchor not found (skipped)")
    return html, False


def patch_run_log(html, results, stamp):
    """results: {subsystem: (ok: bool, detail: str)}"""
    run = f"{stamp:%a %b %d, %Y %H:%M} IST"
    cur = {"run": run, "sub": {}}
    mm = _re.search(r"window\.RUN_LOG\s*=\s*(\{.*?\});", html)
    if mm:
        try:
            old = json.loads(mm.group(1))
            if isinstance(old.get("sub"), dict):
                cur["sub"] = dict(old["sub"])
        except Exception:
            pass
    for name, (ok, detail) in results.items():
        prev = cur["sub"].get(name) or {}
        cur["sub"][name] = {
            "ok": bool(ok),
            "detail": detail,
            "last_ok": run if ok else (prev.get("last_ok") or ""),
        }
    cur["ok_n"] = sum(1 for v in cur["sub"].values() if v.get("ok"))
    cur["n"] = len(cur["sub"])
    new = "window.RUN_LOG = " + json.dumps(cur, separators=(",", ":")) + ";"
    if mm:
        html = html[:mm.start()] + new + html[mm.end():]
        bad = [k for k, v in cur["sub"].items() if not v.get("ok")]
        print(f"  run log: {cur['ok_n']}/{cur['n']} subsystems live"
              + (f" · degraded: {', '.join(bad)}" if bad else ""))
    else:
        print("  run log: window.RUN_LOG anchor not found (skipped)")
    return html


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

def patch_price_health(html, patched, total, stamp):
    """window.PRICE_HEALTH — how many price fields this run actually moved,
    and when prices were last genuinely refreshed. `asof` only advances on a
    run that patched something, so a dead upstream shows up on the page as a
    date that stops moving instead of a timestamp that keeps lying."""
    prev = {}
    blk = _re.search(r"window\.PRICE_HEALTH\s*=\s*(\{.*?\});", html, _re.S)
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    live = patched > 0
    payload = {
        "n": patched, "total": total, "live": live,
        "asof": now if live else (prev.get("asof") or ""),
        "asof_epoch": (int(stamp.timestamp()) if live
                       else int(prev.get("asof_epoch") or 0)),
        "checked": now,
    }
    new = "window.PRICE_HEALTH = " + json.dumps(payload, separators=(",", ":")) + ";"
    if blk:
        html = html[:blk.start()] + new + html[blk.end():]
    else:
        anc = "window.MACRO_LIVE = {"
        i = html.find(anc)
        if i < 0:
            print("  price health: anchor missing (skipped)")
            return html
        html = html[:i] + new + "\n" + html[i:]
    if live:
        print(f"  price health: {patched}/{total} price fields refreshed")
    else:
        print(f"  price health: *** NOTHING REFRESHED *** every upstream "
              f"refused this run — prices on the page are still from "
              f"{payload['asof'] or 'an unknown earlier run'} and the page "
              f"will say so in red")
    return html


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

    # v92e: the page is told the truth about its own prices. Until now a run
    # that fetched nothing still stamped itself with the current time, which
    # is how four days of frozen commodities went unnoticed.
    html = patch_price_health(html, _obj_total + ns,
                              len(MARKET) + len(STOCKS), stamp)

    # --- macro releases (CPI/repo/reserves) from RBI portal, best-effort ---
    macro = fetch_macro()
    html, nmac = patch_macro(html, macro, stamp)
    # v92: the extended macro blocks — RBI portal sweep + computed India series
    try:
        _mx = dict(macro.get("_blocks") or {})
        _mx.update(fetch_india_extras())
        html = patch_macro_x(html, _mx, stamp)
    except Exception as e:
        print(f"  macro blocks: skipped ({type(e).__name__}) — page keeps "
              f"its previous MACRO_X")
    html = patch_reserves(html, macro)
    _amfi = fetch_amfi()
    html = patch_mf(html, _amfi)
    _flows = fetch_flows()
    html = patch_flows(html, _flows)

    # v93: the external and fiscal accounts. Each is best-effort and each
    # fails to an ABSENT field rather than a default.
    try:
        _trade = fetch_trade()
    except Exception as e:
        print(f"  trade: skipped ({type(e).__name__})"); _trade = {}
    try:
        _fisc = fetch_fiscal()
    except Exception as e:
        print(f"  fiscal: skipped ({type(e).__name__})"); _fisc = {}
    try:
        _bop = fetch_bop()
    except Exception as e:
        print(f"  bop: skipped ({type(e).__name__})"); _bop = {}
    html, _ = patch_extern(html, "TRADE_LIVE", _trade, stamp)
    html, _ = patch_extern(html, "FISCAL_LIVE", _fisc, stamp)
    html, _ = patch_extern(html, "BOP_LIVE", _bop, stamp)

    # v92g: what actually worked this run, published to the page itself
    _mlive = macro.get("_live") or []
    _pfields = _obj_total + ns
    _ptotal = len(MARKET) + len(STOCKS)
    html = patch_run_log(html, {
        "prices": (_pfields > 0,
                   f"{_pfields} of {_ptotal} price fields refreshed"),
        "universe": (hstats.get("screened", 0) > 0,
                     f"{hstats.get('screened', 0)} names scored, "
                     f"{hstats.get('searchable', 0)} searchable"),
        "macro": (bool(_mlive),
                  (", ".join(_mlive) + " read from the RBI portal") if _mlive
                  else "the RBI portal returned none of the headline fields"),
        "macro blocks": (bool(macro.get("_blocks")),
                         f"{len(macro.get('_blocks') or {})} of "
                         f"{len(RBI_EXTRA)} extended blocks carried"),
        "reserves": (bool(macro.get("reserves_bn")),
                     f"${macro['reserves_bn']}bn read" if macro.get("reserves_bn")
                     else "no parseable weekly figure on the RBI portal"),
        "mutual funds": (bool(_amfi),
                         f"{len(_amfi)} AMFI category NAVs read" if _amfi
                         else "every AMFI mirror refused the request"),
        "FII/DII flows": (_flows.get("fii") is not None,
                          f"read from {_flows.get('src', 'NSE')}"
                          if _flows.get("fii") is not None
                          else "NSE and all four mirrors refused"),
        "trade balance": (bool(_trade),
                          f"{_trade.get('period', '')} deficit "
                          f"${_trade.get('deficit')}bn read from PIB" if _trade
                          else "no Commerce Ministry release on the PIB wire"),
        "fiscal deficit": (bool(_fisc),
                           f"{_fisc.get('period', '')} at "
                           f"{_fisc.get('pct_be')}% of BE (CGA)" if _fisc
                           else "no CGA monthly account answered"),
        "current account": (bool(_bop),
                            f"${_bop.get('cad_bn')}bn, "
                            f"{_bop.get('cad_pct_gdp')}% of GDP" if _bop
                            else "no parseable RBI BoP release"),
    }, stamp)

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
