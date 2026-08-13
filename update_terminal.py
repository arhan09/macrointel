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
import gzip
import zlib

try:
    import yfinance as yf
except ImportError:
    sys.exit("ERROR: pip install yfinance")

# ── Yahoo Finance ticker map ────────────────────────────────────────────────
MARKET = {
    # India indices
    "Nifty 50": "^NSEI", "BSE Sensex": "^BSESN", "Bank Nifty": "^NSEBANK",
    "Midcap 100": "NIFTY_MIDCAP_100.NS",
    "BSE Midcap": "BSE-MIDCAP.BO", "BSE Smallcap": "BSE-SMLCAP.BO",
    # v107: the daily read on the long end of the India curve
    "India Gilt ETF": "LTGILTBEES.NS",
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


#  v95 · the date of the last bar each tier actually served, keyed by the
#  code that tier was asked for. Without this a quote has no age, and a quote
#  with no age is indistinguishable from a quote that is current.
_BARDATE = {}


def _stooq_closes(code):
    """Daily closes, oldest first, from Stooq's keyless CSV. [] on failure.
    Records the last bar's date in _BARDATE as a side effect."""
    try:
        raw = _get(f"https://stooq.com/q/d/l/?s={code}&i=d", timeout=20, tries=2)
    except Exception:
        return []
    out, last = [], ""
    for line in raw.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            out.append(float(parts[4]))
        except Exception:
            continue
        last = parts[0].strip()[:10]
    if last:
        _BARDATE[code] = last
    return out[-70:]


def _hist_closes(sym):
    """Closes for one symbol out of the history file this pipeline publishes.
    Same numbers the browser is already being served, so a fallback here can
    never disagree with the charts."""
    try:
        with open("history_1y.json", encoding="utf-8") as f:
            h = json.load(f)
        raw = h.get("series", {}).get(sym) or []
        ds = h.get("dates") or []
        v, last = [], ""
        for i, x in enumerate(raw):
            if x is None:
                continue
            v.append(x)
            if i < len(ds):
                last = str(ds[i])
        if len(last) == 8 and last.isdigit():        # 20260804 -> 2026-08-04
            last = f"{last[:4]}-{last[4:6]}-{last[6:]}"
        if last:
            _BARDATE[sym] = last
        return v[-70:]
    except Exception:
        return []


#  v95 · {name: {"s": tier, "b": "YYYY-MM-DD"}} — filled by fetch(), published
#  to the page as window.PRICE_SRC, rendered under every quote.
PRICE_SRC = {}


def _bar_of(series):
    """Date of the last bar in a pandas series, as YYYY-MM-DD. '' if unknown."""
    try:
        return str(series.index[-1])[:10]
    except Exception:
        return ""


def fetch(symbols):
    """Return {name: (last, day_pct, month_pct)} from ~2 months of history.

    v88: BATCH download first — the exact code path ml_models.py uses, which
    has kept working in CI while the old per-ticker Ticker().history() loop
    (~90 sequential calls) started failing. Per-ticker remains only as a
    fallback for symbols the batch missed.

    v95: also records PRICE_SRC[name] = {"s": tier, "b": bar date}. Which tier
    answered is not a diagnostic detail — tier 4 reads this pipeline's own
    published history, so it always succeeds and is never fresh, and a page
    that cannot tell tier 1 from tier 4 cannot tell a quote from an echo."""
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
                    _s = close[sym].dropna()
                    v = _pack(_s)
                    if v:
                        out[name] = v
                        PRICE_SRC[name] = {"s": "Yahoo", "b": _bar_of(_s)}
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
                PRICE_SRC[name] = {"s": "Yahoo", "b": _bar_of(hist.dropna())}
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
                PRICE_SRC[name] = {"s": "Stooq", "b": _BARDATE.get(code, "")}
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
                # tier 4 is this pipeline reading its own homework back. It is
                # named on the tile so nobody mistakes it for a market feed.
                PRICE_SRC[name] = {"s": "own history",
                                   "b": _BARDATE.get(symbols[name], "")}
                got += 1
        if got:
            print(f"  fallback: {got} names recovered from history_1y.json")

    still = [n for n in symbols if n not in out]
    if still:
        print(f"  ! {len(still)} names unresolved after all tiers: "
              f"{', '.join(sorted(still)[:8])}"
              f"{' …' if len(still) > 8 else ''}")
    return out


def _same_num(published, fresh):
    """Is the text already on the page the same number we are about to write?"""
    try:
        return float(published) == float(fresh)
    except (TypeError, ValueError):
        return str(published) == str(fresh)


def patch_obj(html, var, data):
    """Update p/d/m fields for matching keys inside `const VAR={...};`.

    Returns (html, matched, moved).

    v95: `matched` is what this used to return alone, and PRICE_HEALTH was
    reporting it as "fields refreshed". It counts regex hits. A run that
    rewrote every quote with the identical stale number scored full marks and
    the page announced prices verified fresh. `moved` counts the keys whose
    published value actually differs from what was there."""
    m = re.search(r"const " + var + r"=\{(.*?)\};", html, re.DOTALL)
    if not m:
        return html, 0, 0
    body = m.group(1)
    n = moved = 0
    for name, (p, d, mo) in data.items():
        pat = (r'("' + re.escape(name) + r'":\{p:)([\d.]+)(,d:)([-\d.]+)'
               r'(,m:)([-\d.]+)')
        hit = {"moved": False}

        def _rep(x, p=p, d=d, mo=mo, hit=hit):
            if not (_same_num(x.group(2), p) and _same_num(x.group(4), d)
                    and _same_num(x.group(6), mo)):
                hit["moved"] = True
            return f"{x.group(1)}{p}{x.group(3)}{d}{x.group(5)}{mo}"

        new, count = re.subn(pat, _rep, body)
        if count:
            body = new
            n += 1
            if hit["moved"]:
                moved += 1
    return (html[: m.start()] + "const " + var + "={" + body + "};"
            + html[m.end():], n, moved)


def patch_stocks(html, data):
    """IN_STK rows are [name, price, d1, m1, q1] — update first 3 numerics.

    Returns (html, matched, moved); see patch_obj for why those differ."""
    n = moved = 0
    for name, (p, d, _mo) in data.items():
        pat = r'(\["' + re.escape(name) + r'",)([\d.]+),([-\d.]+)'
        hit = {"moved": False}

        def _rep(x, p=p, d=d, hit=hit):
            if not (_same_num(x.group(2), p) and _same_num(x.group(3), d)):
                hit["moved"] = True
            return f"{x.group(1)}{p},{d}"

        new, count = re.subn(pat, _rep, html)
        if count:
            html = new
            n += 1
            if hit["moved"]:
                moved += 1
    return html, n, moved


def patch_spark(html, name, value):
    m = re.search(r'("' + name + r'":\s*\[)([^\]]*)(\])', html)
    if not m:
        return html
    try:
        arr = [float(x) for x in m.group(2).split(",") if x.strip()]
    except Exception:
        arr = []
    # v109: a newly seeded (short or empty) spark GROWS to 20 points before
    # it starts rolling — so Silver fills organically pass by pass.
    arr = (arr + [value])[-20:]
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
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
            # v108: FRED (and some CDNs) started compressing replies no
            # matter what Accept-Encoding asks for. A gzip payload decoded
            # as utf-8 is silent garbage — every parser downstream returns
            # empty and no exception is ever raised. Inflate explicitly.
            if b[:2] == b"\x1f\x8b" or "gzip" in enc:
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            elif "deflate" in enc:
                try:
                    b = zlib.decompress(b, -zlib.MAX_WBITS)
                except Exception:
                    try:
                        b = zlib.decompress(b)
                    except Exception:
                        pass
            return b.decode("utf-8", "ignore")
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
                   "Weighted Average Call Rate", "Call Money Rate", "WACR",
                   "Call Rates", "Call Rate"],
     (0, 15), True, "Call rate (WACR)", "overnight"),
    ("gdp_growth", ["GDP Growth Rate", "Real GDP Growth", "GDP Growth"],
     (-20, 20), True, "Real GDP growth", "y/y"),
    ("iip_p", ["Index of Industrial Production", "IIP Growth", "IIP"],
     (-30, 30), True, "IIP", "y/y"),
    ("usdinr_ref", ["INR/1 USD", "INR / 1 USD", "INR-USD",
                    "Reference Rate", "Exchange Rate"],
     (50, 150), False, "RBI reference rate", "₹ per $"),
    # v94 · read off www.rbi.org.in, which the portal never carried
    ("rev_repo", ["Fixed Reverse Repo Rate", "Reverse Repo Rate"],
     (0, 15), True, "Reverse repo (fixed)", "corridor floor"),
    ("mclr_on", ["MCLR (Overnight)", "MCLR Overnight", "MCLR"],
     (2, 20), True, "MCLR (overnight)", "banks' lending floor"),
    ("base_rate", ["Base Rate"], (2, 20), True, "Base rate", "legacy loans"),
    ("savings_rate", ["Savings Deposit Rate"], (0, 15), True,
     "Savings deposit rate", "banks"),
    ("term_dep", ["Term Deposit Rate (> 1 Year)", "Term Deposit Rate > 1 Year",
                  "Term Deposit Rate >1 Year", "Term Deposit Rate"],
     (0, 15), True, "Term deposit (>1yr)", "banks"),
]

RBI_HOME_URLS = ("https://www.rbi.org.in/", "https://rbi.org.in/",
                 "https://website.rbi.org.in/")


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


def _win_num(txt, labels, lo, hi, pct, width=160):
    """(value, was_a_range) for the first label variant that yields a number
    inside the sanity band within `width` characters after it.

    _rbi_num demands the number sit immediately after its label. That holds
    for the portal's one-line header string and fails for a rendered table,
    where the value is in the next cell. Hence a window, the same shape the
    reserves parser uses on pages the RBI actually serves.

    Ranges are collapsed to their midpoint rather than to their floor: the
    home page publishes MCLR, base rate, term deposits and the call rate as
    "7.80% - 8.00%", and reporting 7.80 as the MCLR is a quiet falsehood."""
    for lab in labels:
        for mm in _re.finditer(_re.escape(lab), txt, _re.I):
            win = txt[mm.end(): mm.end() + width]
            for nm in _re.finditer(r"([\d][\d,]*(?:\.\d+)?)\s*(%?)", win):
                if pct and not nm.group(2):
                    continue
                try:
                    v = float(nm.group(1).replace(",", ""))
                except ValueError:
                    continue
                if not (lo <= v <= hi):
                    continue
                rest = win[nm.end():]
                rm = _re.match(r"\s*(?:-|\u2013|\u2014|to)\s*"
                               r"([\d][\d,]*(?:\.\d+)?)\s*%?", rest)
                if rm:
                    try:
                        hi2 = float(rm.group(1).replace(",", ""))
                    except ValueError:
                        hi2 = None
                    if hi2 is not None and lo <= hi2 <= hi and hi2 >= v:
                        return round((v + hi2) / 2.0, 2), True
                return round(v, 2), False
    return None, False


def scan_rbi_home(txt):
    """{key: {v, label, unit}} off the RBI's own front page, detagged."""
    out = {}
    for key, labels, (lo, hi), pct, label, unit in RBI_EXTRA:
        v, rng = _win_num(txt, labels, lo, hi, pct)
        if v is not None:
            out[key] = {"v": v, "label": label,
                        "unit": (unit + " \u00b7 range mid") if rng else unit,
                        "pct": bool(pct)}
    return out


RBI_HOME_HEAD = (
    ("repo", ["Policy Repo Rate", "Repo Rate"], (0, 15)),
    ("sdf", ["Standing Deposit Facility Rate",
             "Standing Deposit Facility (SDF) Rate", "SDF Rate"], (0, 15)),
)


def fetch_rbi_home():
    """The RBI front page still renders its rate tables server-side. Returns
    (blocks, headline_fields); both empty if every host refuses."""
    for u in RBI_HOME_URLS:
        try:
            txt = _detag(_get(u, timeout=25))
        except Exception as e:                      # noqa: BLE001
            print(f"  macro blocks: {u} refused ({type(e).__name__})")
            continue
        blocks = scan_rbi_home(txt)
        head = {}
        for k, labels, (lo, hi) in RBI_HOME_HEAD:
            v, _ = _win_num(txt, labels, lo, hi, True)
            if v is not None:
                head[k] = v
        if blocks or head:
            print(f"  macro blocks: RBI home page carried {len(blocks)} block(s)"
                  f" ({', '.join(sorted(blocks)) or 'none'})"
                  + (f" + {', '.join(sorted(head))}" if head else ""))
            return blocks, head
        print(f"  macro blocks: {u} answered but carried no rate table")
    return {}, {}


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


def fetch_macro(page=""):
    """Return a dict of macro values. Each field independently falls back to
    MACRO_DEFAULTS if its source fails — so partial success still helps.

    `page` is the terminal HTML. It is needed only so the reserves guard can
    see the figure already published: a weekly series is best validated
    against its own previous value, and that value lives on the page, not in
    anything the RBI hands back."""
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
        sdf  = (grab("Standing Deposit Facility (SDF) Rate")
                or grab("Standing Deposit Facility Rate"))
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
        # v94: the portal now serves a JavaScript shell — 200, no table,
        # and a bundled script full of numbers. If not one headline rate was
        # found above, this is that shell, and anything the reserves regex
        # matches in it is a coincidence. $300.0bn was one.
        for lbl in (("Foreign Exchange Reserves", "Forex Reserves",
                     "FX Reserves", "Foreign Exchange Reserves (US$ Million)",
                     "Total Reserves", "Foreign Currency Assets")
                    if live else ()):
            mm = _re.search(_re.escape(lbl) +
                            r"[^\d$]{0,40}\$?\s*([\d,]+(?:\.\d+)?)\s*([BbMm]?)",
                            html)
            if mm:
                v = float(mm.group(1).replace(",", ""))
                unit = mm.group(2).lower()
                if unit == "m" or v > 50000:      # quoted in $ million
                    v = v / 1000.0
                # v94: a band alone let $300.0bn through against a stored
                # $702.0bn. Distance from the figure already on the page is
                # the test a magnitude band cannot perform.
                if _rsv_plausible(v, *_rsv_anchor(page)):
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
    # v94: the portal is now the fallback, not the source. Whatever it still
    # carries wins on a key-by-key basis — it is the more precise document —
    # and the home page fills everything it left empty, which is currently
    # all of it.
    _hblocks, _hhead = fetch_rbi_home()
    for _k, _v in _hblocks.items():
        m["_blocks"].setdefault(_k, _v)
    # and the headline rates the portal header used to supply
    for _k, _v in _hhead.items():
        if _k not in m:
            m[_k] = _v
            live.add(_k)

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
        _bn, _asof, _src = fetch_reserves_rbi(*_rsv_anchor(page))
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
    "Flexi cap (equity)":     122639,   # Parag Parikh Flexi Cap - Direct - Growth
    "Small cap (equity)":     118778,   # Nippon India Small Cap - Direct - Growth
    "Gilt (long)":            120487,   # SBI Magnum Gilt Fund - Direct - Growth
    "Gold (FoF)":             119773,   # Nippon India Gold Savings - Direct - Growth
    "Liquid (cash)":          119807,   # HDFC Liquid Fund - Direct - Growth
}


def _mfapi_date(d):
    """'04-08-2026' -> '04-Aug-2026' — AMFI's own date style, so a trail
    written by either door keys identically and never double-appends."""
    try:
        p = str(d).split("-")
        mo = ("Jan Feb Mar Apr May Jun Jul Aug Sep "
              "Oct Nov Dec").split()[int(p[1]) - 1]
        return p[0] + "-" + mo + "-" + p[2]
    except Exception:
        return str(d)


def _mfapi_fresh(d, days=12):
    """Is a DD-MM-YYYY NAV date recent enough to publish as current? A
    mirror can lag; a lagging mirror must read as a failure, not a NAV."""
    try:
        p = str(d).split("-")
        then = dt.datetime(int(p[2]), int(p[1]), int(p[0]),
                           tzinfo=dt.timezone(dt.timedelta(hours=5,
                                                           minutes=30)))
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
        return (now - then).days <= days
    except Exception:
        return False


def _amfi_via_mfapi():
    """v97: the primary fund door. Per-scheme JSON, full NAV history, no
    key. The /latest endpoint lags its cache by weeks, so this reads the
    full endpoint and takes row zero — verified current against the AMFI
    file itself. A scheme whose newest row is older than 12 days is
    dropped: a stale mirror must fail loudly, not publish quietly."""
    out, stale = {}, []
    for cat, code in MFAPI.items():
        try:
            j = json.loads(_get(f"https://api.mfapi.in/mf/{code}",
                                timeout=25, tries=2))
        except Exception:
            continue
        rows = j.get("data") or []
        if len(rows) < 25:
            continue
        if not _mfapi_fresh(rows[0].get("date", "")):
            stale.append(cat)
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
                    "date": _mfapi_date(rows[0].get("date", "")),
                    "src": "mfapi.in (AMFI data)"}
    if stale:
        print(f"  amfi: mfapi served {len(stale)} scheme(s) older than 12 "
              f"days ({', '.join(stale)}) — dropped rather than published")
    return out


def fetch_amfi():
    """Official AMFI NAV file — all schemes, plain text, no key, no anti-bot.
    v88: format-proof matcher — names are normalized (lowercase, punctuation
    collapsed) and matched on tokens, with preferred-AMC patterns first and a
    generic category fallback, so AMFI renaming can't zero the table."""
    # v97: API first. mfapi.in serves the same AMFI data as small
    # per-scheme JSON with full history — so 1M/1Y returns arrive computed
    # instead of waiting 23 passes for the trail. The 7MB official file
    # (which has been timing out from the runner since v93) drops to
    # fallback and fills whatever the API missed.
    out = _amfi_via_mfapi()
    if len(out) == len(MFAPI):
        print(f"  amfi: mfapi.in carried all {len(out)}/{len(MFAPI)} "
              f"categories (full history — 1M/1Y computed)")
        return out
    raw = None
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
        if out:
            print(f"  amfi: official file refused; mfapi.in carried "
                  f"{len(out)}/{len(MFAPI)} categories")
            return out
        print("  amfi: EVERY door refused — no NAVs this run. The fund table "
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
        "Flexi cap (equity)": (["parag parikh flexi cap"], ["flexi cap fund"]),
        "Small cap (equity)": (["nippon india small cap"], ["small cap fund"]),
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
    for cat, (pref, generic) in CATS.items():
        if cat in out:          # the API already carried this category
            continue
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
    print(f"  amfi: {len(out)}/{len(CATS)} categories carried "
          f"(mfapi + official file; {len(rows)} direct-growth schemes "
          f"scanned" + (f"; sample: {sample[:60]}" if sample and not out
                        else "") + ")")
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
        # v97: the API door computes 1M/1Y off its own history — carry them
        # so the table shows returns from the first pass, and name the door
        for k in ("m1", "y1", "src"):
            if v.get(k) is not None:
                c[k] = v[k]
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
    # WSS section 2 on the legacy site. NOT the table — this is an index of
    # weekly files running back to 1999, whose only numbers are download
    # sizes. Kept because it is one redirect from the real thing and costs
    # nothing now that _rsv_is_table refuses it.
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


BUILD = "v111"     # patched into the page header on every run.

RSV_STEP = 0.08   # India's reserves have never moved 8% in a week.


RSV_ATH_FLOOR = 0.60   # reserves have never sat below 60% of their own ATH


def _prev_reserves(page):
    """(last figure, all-time high) off the TERMINAL page — or (None, None).

    The argument is deliberately not called `html`: inside fetch_macro that
    name holds the RBI portal page, and handing this the wrong one silently
    disables the guard rather than failing.

    Both numbers are returned because the first cannot be trusted on its own.
    `total_bn` is whatever the last run wrote, mis-parse included. `ath_bn` is
    a running maximum, so a single bad weekly read cannot move it — which
    makes it the only thing on the page fit to audit the anchor."""
    m = _re.search(r"window\.RESERVES_LIVE\s*=\s*(\{.*?\});", page)
    if not m:
        return None, None
    try:
        d = json.loads(m.group(1))
        v = d.get("total_bn")
        a = d.get("ath_bn")
        return (float(v) if v else None), (float(a) if a else None)
    except Exception:
        return None, None


def _rsv_anchor(page):
    """The baseline a candidate is measured against, or None if the stored
    figure is not fit to be one. Without this, a guard anchored on a bad value
    rejects every correct read that follows and locks the error in forever."""
    prev, ath = _prev_reserves(page)
    if prev and ath and prev < RSV_ATH_FLOOR * ath:
        print(f"  reserves: the stored ${prev}bn is itself implausible against "
              f"an ATH of ${ath}bn \u2014 ignoring it as a baseline so a good "
              f"read can repair the page")
        return None, ath
    return prev, ath


def _rsv_plausible(v, prev, ath=None):
    """A magnitude band alone cannot tell a reserves figure from a page number
    that happens to be in the hundreds of thousands. Two things can: distance
    from the value we already hold, and distance from the all-time high. The
    second still works when the first has been poisoned."""
    if v is None or not (300 <= v <= 1500):
        return False
    if ath and ath > 0 and v < RSV_ATH_FLOOR * ath:
        return False
    if prev and prev > 0 and abs(v / prev - 1.0) > RSV_STEP:
        return False
    return True


#  The furniture of a real reserves table. The WSS extract carries all of
#  these; an index page, a search result and a nav stub carry none. Requiring
#  one of them is what separates "this document contains the number" from
#  "this document contains the words".
_RSV_TABLE_MARKS = ("Foreign Currency Assets", "Reserve Position in the IMF",
                    "US$ Mn", "US$ Million", "SDRs", "Special Drawing Rights")

#  kb / mb / gb / kib / bytes only. NOT a bare "b" or "bn", which is how a
#  page legitimately writes billions.
_RSV_SIZE = _re.compile(r"\s*(?:[kmg]i?b\b|bytes\b)", _re.I)


def _rsv_is_table(txt):
    return any(mk.lower() in txt.lower() for mk in _RSV_TABLE_MARKS)


def _rsv_from_text(txt, prev=None, ath=None):
    """Pull (value_in_usd_bn, as_on_string) out of WSS-shaped text.

    The unit is never guessed from a letter glued to the number — that is the
    bug that made this fail silently for weeks. It is decided by magnitude:
    India's reserves are ~700 in $bn and ~700,000 in $mn, three orders apart,
    and the rupee-crore column is ~60,00,000, another order beyond that. Any
    reading that does not land inside the $bn sanity band is discarded rather
    than rounded into one."""
    # v94r8: the words are not the table. www.rbi.org.in/Scripts/
    # WSSViewDetail.aspx says "Foreign Exchange Reserves" on every one of its
    # several hundred index rows and carries no reserves figure anywhere — the
    # only numbers on it are download sizes in kilobytes. That page published
    # $300.0bn.
    if not _rsv_is_table(txt):
        return None, ""
    cands, seen = [], 0
    for lbl in _RSV_LABELS:
        for mm in _re.finditer(_re.escape(lbl), txt):
            window = txt[mm.end(): mm.end() + 400]
            for nm in _re.finditer(r"([\d][\d,]{2,}(?:\.\d+)?)", window):
                # a download size is not a national reserve
                if _RSV_SIZE.match(window[nm.end():]):
                    continue
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
                seen += 1
                if not _rsv_plausible(bn, prev, ath):
                    continue
                back = txt[max(0, mm.start() - 300): mm.end() + 400]
                dm = _re.search(r"as on\s+([A-Za-z]{3,9}\.?\s*\d{1,2},?\s*\d{4}"
                                r"|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", back, _re.I)
                cands.append((round(bn, 1), (dm.group(1).strip() if dm else "")))
    if not cands:
        if seen:
            _base = (f"the ${prev}bn already on the page" if prev
                     else f"an ATH of ${ath}bn" if ath
                     else "the magnitude band")
            print(f"  reserves: {seen} candidate(s) in range, none plausible "
                  f"against {_base} \u2014 rejected rather than published")
        return None, ""
    # a dated candidate beats an undated one; among equals, the one closest to
    # what we already hold.
    #
    # v94r8: "what we already hold" now falls back to the all-time high when
    # the page's own figure is not trusted. Order of appearance is not a good
    # enough tie-break for a headline number: in the real WSS extract the
    # rupee-crore column of a neighbouring row lands inside the dollar-billion
    # band by coincidence — gold at ₹785,302 crore reads as $785.3bn — and an
    # anchor is the only thing that reliably prefers the right column.
    _near = prev or ath
    cands.sort(key=lambda c: (c[1] == "",
                              abs(c[0] - _near) if _near else 0.0))
    return cands[0]


PRESS_INDEX = ("https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
                "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx")


def fetch_wss_release(prev=None, ath=None):
    """The Weekly Statistical Supplement extract — the one RBI page that still
    server-renders the reserves table. Returns (bn, as_on, source).

    The index is scraped rather than the RSS feed because the feed holds only
    the most recent couple of dozen releases and the supplement scrolls off it
    within days; that is why the existing RSS fallback has never once fired."""
    for base in PRESS_INDEX:
        try:
            idx = _get(base, timeout=30)
        except Exception as e:                       # noqa: BLE001
            print(f"  reserves: {base.split('/')[2]} press index refused "
                  f"({type(e).__name__})")
            continue
        prids = []
        for mm in _re.finditer(r"Weekly Statistical Supplement", idx, _re.I):
            back = idx[max(0, mm.start() - 2500): mm.start()]
            pm = _re.findall(r"prid=(\d{3,7})", back)
            if pm:
                prids.append(int(pm[-1]))
        # newest first: the prid is monotonic, so the largest is the latest
        for pid in sorted(set(prids), reverse=True)[:3]:
            u = f"{base}?prid={pid}"
            try:
                bn, asof = _rsv_from_text(_detag(_get(u, timeout=30)), prev, ath)
            except Exception:                        # noqa: BLE001
                continue
            if bn:
                print(f"  reserves: ${bn}bn read from the WSS extract"
                      + (f", as on {asof}" if asof else "")
                      + f" (release {pid})")
                return bn, asof, "RBI weekly statistical supplement"
        if prids:
            print(f"  reserves: {len(set(prids))} WSS release(s) listed, none "
                  f"carried a plausible total")
    return None, "", ""


def fetch_reserves_rbi(prev=None, ath=None):
    """Weekly forex reserves from the RBI, tried across four transports plus
    the press-release feed. Returns (bn, as_on, source) or (None, '', '').

    `prev` is the figure already on the page; a candidate far away from it is
    a mis-parse, not news."""
    # v94r8: the weekly release goes first. The URLs below are section and
    # landing pages; one of them is a file index that published a kilobyte
    # count as a dollar figure for at least one run.
    _bn, _asof, _src = fetch_wss_release(prev, ath)
    if _bn:
        return _bn, _asof, _src
    for url in RESERVE_URLS:
        try:
            raw = _get(url, timeout=30)
        except Exception as e:
            print(f"  reserves: {url.split('/')[2]} refused ({type(e).__name__})")
            continue
        bn, asof = _rsv_from_text(_detag(raw), prev, ath)
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
                bn, asof = _rsv_from_text(_detag(_get(l, timeout=30)), prev, ath)
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
    # v94: a head poisoned by an earlier mis-parse must not survive merely
    # because today's read failed. `total` has just fallen back to whatever is
    # on the page, and what is on the page may be the artefact. Audited against
    # the ATH floor, which a single bad weekly read cannot move.
    _ath0 = float(cur.get("ath_bn") or 0)
    if not fresh and _ath0 and total < RSV_ATH_FLOOR * _ath0:
        _good = [p for p in (cur.get("trail") or [])
                 if isinstance(p, list) and len(p) == 2
                 and isinstance(p[1], (int, float))
                 and p[1] >= RSV_ATH_FLOOR * _ath0]
        if _good:
            print(f"  reserves: the published ${round(total, 1)}bn sits below "
                  f"{RSV_ATH_FLOOR:.0%} of the ${_ath0}bn ATH \u2014 restoring "
                  f"${_good[-1][1]}bn from {_good[-1][0]}, the last figure in "
                  f"the trail that is not a mis-parse")
            total = float(_good[-1][1])
        else:
            print(f"  reserves: the published ${round(total, 1)}bn sits below "
                  f"{RSV_ATH_FLOOR:.0%} of the ${_ath0}bn ATH and the trail "
                  f"holds nothing better \u2014 it stands, flagged stale")
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
    # v94: the guard cannot un-publish a figure an earlier run already wrote,
    # so the trail is swept too — a point that disagrees with its neighbour by
    # more than the weekly guard is a parse artefact, not a capital flight.
    #
    # This runs BEFORE today's point is appended, and the order matters. The
    # other way round, an artefact already carrying today's tag occupies the
    # slot, the duplicate-tag guard refuses the good read as a repeat, and the
    # sweep then deletes the artefact — so the bad number blocks the good one
    # and then removes itself, leaving the day empty.
    _ath = float(cur.get("ath_bn") or 0)
    if _ath:
        drop = [p for p in trail if p[1] < RSV_ATH_FLOOR * _ath]
        for p in drop:
            print(f"  reserves: dropped trail point {p[0]} ${p[1]}bn "
                  f"\u2014 below {RSV_ATH_FLOOR:.0%} of the ${_ath}bn ATH")
        trail = [p for p in trail if p[1] >= RSV_ATH_FLOOR * _ath]
    if len(trail) >= 2:
        def _chain(seq):
            keep = [seq[0]]
            for pt in seq[1:]:
                base = keep[-1][1]
                if base and abs(pt[1] / base - 1.0) > RSV_STEP:
                    continue
                keep.append(pt)
            return keep
        # chained from BOTH ends: the first point is not automatically the
        # trustworthy one, and a forward-only sweep anchored on an artefact
        # keeps the artefact and throws away the real history behind it.
        _fwd = _chain(trail)
        _bwd = list(reversed(_chain(list(reversed(trail)))))
        keep = _fwd if len(_fwd) >= len(_bwd) else _bwd
        for pt in trail:
            if pt not in keep:
                print(f"  reserves: dropped trail point {pt[0]} ${pt[1]}bn "
                      f"\u2014 out of line with the series either side of it")
        trail = keep
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
    # v94r8: MACRO_LIVE carries its own copy of reserves_bn, and it was NOT
    # covered by the repair in patch_reserves — that function runs later and
    # only touches RESERVES_LIVE. So a page recovering from a mis-parse healed
    # the forex tab and left the macro tab still quoting the bad figure: two
    # different reserve numbers on one site, which is worse than one wrong one.
    # Same test as everywhere else — below 60% of the recorded ATH is not a
    # drawdown, it is a parse artefact — and the same repair, off the trail
    # RESERVES_LIVE already holds.
    _ml_ath = cur_ml.get("reserves_ath") or 0
    if (cur_ml.get("reserves_bn") and _ml_ath
            and cur_ml["reserves_bn"] < RSV_ATH_FLOOR * _ml_ath):
        _bad = cur_ml["reserves_bn"]
        _fix = None
        _rl = _re.search(r'window\.RESERVES_LIVE = (\{.*?\});', html)
        if _rl:
            try:
                for _p in (json.loads(_rl.group(1)).get("trail") or []):
                    if (isinstance(_p, list) and len(_p) == 2
                            and isinstance(_p[1], (int, float))
                            and _p[1] >= RSV_ATH_FLOOR * _ml_ath):
                        _fix = float(_p[1])
            except Exception:                        # noqa: BLE001
                pass
        if _fix:
            cur_ml["reserves_bn"] = _fix
            print(f"  macro: MACRO_LIVE was carrying the same ${_bad}bn "
                  f"mis-parse — repaired to ${_fix}bn from the reserves trail")
        else:
            cur_ml.pop("reserves_bn", None)
            print(f"  macro: MACRO_LIVE was carrying ${_bad}bn, below 60% of "
                  f"the ${_ml_ath}bn ATH, and the trail holds nothing better "
                  f"— dropped rather than republished")

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
    # v97: the RSS holds ~20 items and Commerce releases scroll off within
    # hours — which is why this fetcher has never once fired. The day
    # listing catches release day itself.
    try:
        hits += [(p, t) for p, t in _pib_today()
                 if any(k in t.lower() for k in ("trade", "export",
                                                 "merchandise"))]
    except Exception:
        pass
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
    "PRICE_SRC":     "window.PRICE_SRC",
    "REGIME_LIVE":   "window.REGIME_LIVE",
    "SECTOR_INFL":   "window.SECTOR_INFL",
    "GOLD_INR":      "window.GOLD_INR",
    "FNO_LIVE":      "window.FNO_LIVE",
    "CURVES_LIVE":   "window.CURVES_LIVE",
    "VALUATION":     "window.VALUATION",
    "MOVERS_LIVE":   "window.MOVERS_LIVE",
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



# ═══════════════════════════════════════════════════════════════════════
#  v96 · THE MINISTRY WIRE. CPI, WPI, IIP and GST come out monthly as
#  server-rendered PIB press releases. The data portal that used to carry
#  them is a browser application now; the releases themselves never moved.
#  Discovery is two doors — the PIB RSS and the day's all-releases listing —
#  and every parse is sanity-banded, because the last unbanded parser this
#  pipeline had reported a file size as a country's reserves.
# ═══════════════════════════════════════════════════════════════════════

PIB_ALLREL = ("https://www.pib.gov.in/Allrel.aspx?reg=3&lang=1",
              "https://pib.gov.in/Allrel.aspx?reg=3&lang=1",
              "https://www.pib.gov.in/Allrel.aspx?reg=3&lang=2",
              "https://www.pib.gov.in/Allrel.aspx",
              "https://pib.gov.in/Allrel.aspx")


def _pib_today():
    """[(prid, title)] off today's all-releases listing. The listing is
    server-rendered and keyless; the date form on it is not, so this door
    only sees the current day — which is enough five crons a day."""
    for u in PIB_ALLREL:
        try:
            raw = _get(u, timeout=25, tries=1)
        except Exception:
            continue
        hits = _re.findall(
            r"PRID=(\d+)[^>]*>\s*([^<]{8,240}?)\s*<", raw)
        if hits:
            return [(p, _re.sub(r"\s+", " ", t)) for p, t in hits]
    return []


def _pib_pool():
    """One pool of (prid, title) from both doors, deduped, RSS first."""
    pool, seen = [], set()
    for kws in (["consumer price index"], ["\u0909\u092a\u092d\u094b\u0915\u094d\u0924\u093e \u092e\u0942\u0932\u094d\u092f \u0938\u0942\u091a\u0915\u093e\u0902\u0915"],
                ["wholesale price"], ["\u0925\u094b\u0915 \u092e\u0942\u0932\u094d\u092f"],
                ["industrial production"], ["\u0914\u0926\u094d\u092f\u094b\u0917\u093f\u0915 \u0909\u0924\u094d\u092a\u093e\u0926\u0928"],
                ["gst"], ["\u091c\u0940\u090f\u0938\u091f\u0940"],
                ["\u0935\u0938\u094d\u0924\u0941 \u090f\u0935\u0902 \u0938\u0947\u0935\u093e \u0915\u0930"]):
        for prid, title in _pib_recent(kws):
            if prid not in seen:
                seen.add(prid)
                pool.append((prid, title))
    for prid, title in _pib_today():
        if prid not in seen:
            seen.add(prid)
            pool.append((prid, title))
    return pool


def _pn(txt):
    """PIB writes negatives as '(-)1.6'. Normalise so one regex reads both."""
    return txt.replace("(-)", "-").replace("(−)", "-")


_MONTH = ("January February March April May June July August September "
          "October November December").split()


def _cpi_from_text(txt):
    """MoSPI: 'Retail inflation based on Consumer Price Index in June, 2026
    is 4.38%'. Previous month sits in the (Final) table when present."""
    txt = _pn(txt)
    m = _re.search(
        r"[Rr]etail inflation based on\s+Consumer Price Index\s+in\s+"
        r"([A-Z][a-z]+),?\s*(\d{4})\s+is\s+(-?[\d.]+)\s*%", txt)
    if not m:
        # 2026 phrasing: "Year-on-year inflation rate based on All India
        # Consumer Price Index (CPI) with base year 2024 for the month of
        # July, 2026 over July, 2025 is 4.45%(Provisional)."
        m = _re.search(
            r"inflation\s+rate\s+based\s+on[^.]{0,160}?Consumer\s+Price\s+"
            r"Index[^.]{0,160}?for\s+the\s+month\s+of\s+([A-Z][a-z]+),?\s*"
            r"(\d{4})[^.]{0,120}?\bis\s+(-?[\d.]+)\s*%", txt)
    if not m:
        m = _re.search(
            r"Consumer Price Index[^.]{0,120}?for\s+([A-Z][a-z]+),?\s*"
            r"(\d{4})[^.]{0,80}?\bis\s+(-?[\d.]+)\s*%", txt)
    if not m or m.group(1) not in _MONTH:
        return {}
    try:
        v = float(m.group(3))
    except Exception:
        return {}
    if not (-5.0 <= v <= 25.0):
        return {}
    out = {"v": v, "month": m.group(1), "year": int(m.group(2)),
           "period": f"{m.group(1)[:3]} {m.group(2)}"}
    f = _re.search(r"Consumer Food Price Index[^.]{0,140}?\bis\s+"
                   r"(-?[\d.]+)\s*%", txt)
    if f:
        try:
            fv = float(f.group(1))
            if -20.0 <= fv <= 40.0:
                out["food"] = fv
        except Exception:
            pass
    # the previous month's combined figure, from the '(Final)' table row
    p = _re.search(r"\(Final\).{0,200}?CPI \(General\)\s+(-?[\d.]+)\s+"
                   r"(-?[\d.]+)\s+(-?[\d.]+)", txt, _re.S)
    if p:
        try:
            pv = float(p.group(3))
            if -5.0 <= pv <= 25.0:
                out["prev"] = pv
        except Exception:
            pass
    return out


def _wpi_from_text(txt):
    """OEA: 'All India Wholesale Price Index (WPI) inflation for June 2026 is
    9.87 per cent ... compared to 9.68 per cent in May 2026.'"""
    txt = _pn(txt)
    m = _re.search(
        r"WPI\)?\s*inflation\s+for\s+([A-Z][a-z]+),?\s*(\d{4})\s+is\s+"
        r"(-?[\d.]+)\s*(?:per\s*cent|%)"
        r"(?:[^.]{0,120}?compared to\s+(-?[\d.]+)\s*(?:per\s*cent|%)\s*"
        r"in\s+([A-Z][a-z]+))?", txt)
    if not m or m.group(1) not in _MONTH:
        return {}
    try:
        v = float(m.group(3))
    except Exception:
        return {}
    if not (-15.0 <= v <= 40.0):
        return {}
    out = {"v": v, "month": m.group(1), "year": int(m.group(2)),
           "period": f"{m.group(1)[:3]} {m.group(2)}"}
    # v100: the same release names the group rates — primary articles,
    # fuel & power, manufactured products, in that order. This is the
    # industry-price layer: farm-gate costs, energy costs, output prices.
    g = _re.search(r"major groups are\s+(-?[\d.]+)\s*per\s*cent,?\s+"
                   r"(-?[\d.]+)\s*per\s*cent,?\s*(?:and\s+)?"
                   r"(-?[\d.]+)\s*per\s*cent", txt)
    if g:
        try:
            gp = [float(g.group(i)) for i in (1, 2, 3)]
            if all(-30.0 <= x <= 80.0 for x in gp):
                out["groups"] = {"primary": gp[0], "fuel": gp[1],
                                 "manuf": gp[2]}
        except Exception:
            pass
    if m.group(4):
        try:
            pv = float(m.group(4))
            if -15.0 <= pv <= 40.0:
                out["prev"] = pv
        except Exception:
            pass
    return out


def _iip_from_text(txt):
    """MoSPI, two phrasings: 'In May 2026, Index of Industrial Production
    recorded a 5.1% year-on-year growth' and the title form 'records growth
    of 5.1% in May 2026'."""
    txt = _pn(txt)
    m = _re.search(
        r"In\s+([A-Z][a-z]+),?\s*(\d{4}),?\s*(?:the\s+)?Index of Industrial "
        r"Production recorded a\s+(-?[\d.]+)\s*%", txt)
    if m:
        mo, yr, vv = m.group(1), m.group(2), m.group(3)
    else:
        m = _re.search(
            r"[Ii]ndex of [Ii]ndustrial [Pp]roduction records?\s+(?:a\s+)?"
            r"growth of\s+(-?[\d.]+)\s*%\s*in\s+(?:the\s+)?"
            r"([A-Z][a-z]+),?\s*(\d{4})", txt)
        if not m:
            return {}
        vv, mo, yr = m.group(1), m.group(2), m.group(3)
    if mo not in _MONTH:
        return {}
    try:
        v = float(vv)
    except Exception:
        return {}
    if not (-25.0 <= v <= 35.0):
        return {}
    return {"v": v, "month": mo, "year": int(yr),
            "period": f"{mo[:3]} {yr}"}


def _gst_from_text(txt):
    """FinMin, phrasing drifts year to year: '... GST revenue for March 2024
    ... at Rs.1.78 lakh crore' / 'Gross GST collections ... Rs 2,11,000
    crore in July 2026', growth as '11.5% year-on-year' or 'y-o-y'."""
    txt = _pn(txt).replace("₹", "Rs ")
    v = None
    m = _re.search(r"[Gg]ross\s+(?:Good and Services Tax\s*)?\(?GST\)?"
                   r"[^.]{0,160}?Rs\.?\s*([\d.]+)\s*lakh\s+crore", txt)
    if m:
        try:
            v = float(m.group(1))
        except Exception:
            v = None
    if v is None:
        m = _re.search(r"[Gg]ross\s+(?:Good and Services Tax\s*)?\(?GST\)?"
                       r"[^.]{0,160}?Rs\.?\s*([\d,]{6,})\s*crore", txt)
        if m:
            try:
                v = float(m.group(1).replace(",", "")) / 1e5
            except Exception:
                v = None
    if v is None or not (0.8 <= v <= 6.0):
        return {}
    out = {"v": round(v, 2)}
    g = _re.search(r"(-?[\d.]+)\s*%\s*(?:year.on.year|y.?o.?y|YoY)", txt)
    if g:
        try:
            gy = float(g.group(1))
            if -30.0 <= gy <= 60.0:
                out["yoy"] = gy
        except Exception:
            pass
    pm = _re.search(r"(?:for|in)\s+(?:the month of\s+)?([A-Z][a-z]+),?\s*"
                    r"(\d{4})", txt)
    if pm and pm.group(1) in _MONTH:
        out["month"] = pm.group(1)
        out["year"] = int(pm.group(2))
        out["period"] = f"{pm.group(1)[:3]} {pm.group(2)}"
    return out


# v108: PIB's RSS and day listing flipped to Hindi-by-default in August
# 2026 and the reg/lang query forms started returning empty pages. Each
# indicator therefore matches on EITHER language's title; a release found
# by its Hindi title is parsed off its English sibling page (every PIB
# release links its translations).
PIB_PARSERS = {
    "cpi": ((("consumer price index",),
             ("\u0909\u092a\u092d\u094b\u0915\u094d\u0924\u093e \u092e\u0942\u0932\u094d\u092f \u0938\u0942\u091a\u0915\u093e\u0902\u0915",)), _cpi_from_text),
    "wpi": ((("wholesale price",), ("\u0925\u094b\u0915 \u092e\u0942\u0932\u094d\u092f",)), _wpi_from_text),
    "iip": ((("industrial production",),
             ("\u0914\u0926\u094d\u092f\u094b\u0917\u093f\u0915 \u0909\u0924\u094d\u092a\u093e\u0926\u0928",)), _iip_from_text),
    "gst": ((("gst",), ("\u091c\u0940\u090f\u0938\u091f\u0940",),
             ("\u0935\u0938\u094d\u0924\u0941 \u090f\u0935\u0902 \u0938\u0947\u0935\u093e \u0915\u0930",),
             ("\u092e\u093e\u0932 \u090f\u0935\u0902 \u0938\u0947\u0935\u093e \u0915\u0930",)), _gst_from_text),
}


def _pib_english_sibling(raw):
    """The English sibling's PRID out of a release page's language links."""
    for pat in (r"PRID=(\d+)[^<>]{0,200}?>\s*English\s*<",
                r">\s*English\s*<[^<>]{0,300}?PRID=(\d+)",
                r"value=[\"'][^\"']*PRID=(\d+)[^\"']*[\"'][^>]*>\s*English"):
        mm = _re.search(pat, raw, _re.I)
        if mm:
            return mm.group(1)
    return ""


def fetch_pib_stats():
    """{indicator: parsed dict} for whatever the wire carries right now.
    Each indicator takes the first release that parses; a page that matches
    the keyword but not the parser (a backgrounder, an anniversary note) is
    skipped rather than guessed at."""
    pool = _pib_pool()
    if not pool:
        print("  pib stats: neither the RSS nor the day listing answered")
        return {}
    out = {}
    for key, (kws, parser) in PIB_PARSERS.items():
        cands = [(p, t) for p, t in pool
                 if any(all(k in t.lower() for k in alt) for alt in kws)][:3]
        for prid, title in cands:
            raw = ""
            for tmpl in PIB_PAGE:
                try:
                    raw = _get(tmpl % prid, timeout=30, tries=1)
                    break
                except Exception:
                    continue
            body = _detag(raw) if raw else ""
            got = parser(title + " . " + body) if body else parser(title)
            if not got and raw:
                sib = _pib_english_sibling(raw)
                if sib and sib != prid:
                    for tmpl in PIB_PAGE:
                        try:
                            got = parser(_detag(_get(tmpl % sib,
                                                     timeout=30, tries=1)))
                            break
                        except Exception:
                            continue
                    if got:
                        print(f"  pib stats: {key.upper()} parsed off the "
                              f"English sibling {sib} of {prid}")
                        prid = sib
            if got:
                got["src"] = "PIB " + prid
                out[key] = got
                print(f"  pib stats: {key.upper()} {got['v']}"
                      f"{'%' if key != 'gst' else ' lakh cr'}"
                      f" ({got.get('period', '?')}, PIB {prid})")
                break
    if not out:
        print("  pib stats: wire answered but no CPI/WPI/IIP/GST release "
              "was on it this pass — monthly tiles keep their last read "
              "and say which month it was")
    return out


# ═══════════════════════════════════════════════════════════════════════
#  v96 · THE REGIME ENGINE. Growth direction x inflation direction — the
#  four-quadrant read the page has always drawn, now computed server-side
#  from the prints themselves, with every input named, dated, and flagged
#  live or carried. Direction beats level: a 4.4% CPI falling and a 3.8%
#  CPI rising are different regimes, whatever the levels say.
# ═══════════════════════════════════════════════════════════════════════

REGIME_QUADS = {(1, 1): "REFLATION", (1, -1): "GOLDILOCKS",
                (-1, 1): "STAGFLATION", (-1, -1): "DISINFLATION"}


def _dirn(now, prev, eps=0.05):
    """+1 rising, -1 falling, 0 flat/unknown."""
    if now is None or prev is None:
        return 0
    d = now - prev
    return 1 if d > eps else (-1 if d < -eps else 0)


def _page_ml(page, key):
    """A single numeric field out of the page's MACRO_LIVE line."""
    try:
        mm = _re.search(r"window\.MACRO_LIVE\s*=\s*\{([^}]*)\};", page)
        kk = _re.search(key + r":\s*(-?[\d.]+)", mm.group(1)) if mm else None
        return float(kk.group(1)) if kk else None
    except Exception:
        return None


def _page_mx(page, key, field):
    """A field out of one MACRO_X block on the page."""
    try:
        mm = _re.search(r"window\.MACRO_X\s*=\s*(\{.*?\});", page, _re.S)
        d = json.loads(mm.group(1)) if mm else {}
        return (d.get(key) or {}).get(field)
    except Exception:
        return None


def _page_trail(page):
    """The six-print CPI trail off the page, oldest first."""
    try:
        mm = _re.search(r"cpi_trail:\s*\[([^\]]*)\]", page)
        return [float(x) for x in mm.group(1).split(",")] if mm else []
    except Exception:
        return []


def _page_mlout_regime(page):
    """The RF classifier's own published call, off the page's ML_OUTPUT."""
    try:
        mm = _re.search(r"const ML_OUTPUT = (\{.*?\});", page, _re.S)
        d = json.loads(mm.group(1)) if mm else {}
        r = d.get("regime") or {}
        return {"prediction": r.get("prediction"),
                "prob": (r.get("probabilities") or {}).get(
                    r.get("prediction")),
                "generated": d.get("generated", "")}
    except Exception:
        return {}


# the RF's label set maps onto the engine's quadrants; "Slowflation" is its
# name for the both-falling corner
RF_MAP = {"Goldilocks": "GOLDILOCKS", "Reflation": "REFLATION",
          "Stagflation": "STAGFLATION", "Slowflation": "DISINFLATION",
          "Disinflation": "DISINFLATION"}


def _level_quad(cpi, iip):
    """The level-method read on CURRENT prints — same thresholds the RF was
    trained on (CPI vs 4%, IIP vs 3%). A cross-check, not the engine."""
    if cpi is None or iip is None:
        return None
    if cpi >= 4 and iip >= 3:
        return "REFLATION"
    if cpi < 4 and iip >= 3:
        return "GOLDILOCKS"
    if cpi >= 4:
        return "STAGFLATION"
    return "DISINFLATION"


def classify_regime(pib, page):
    """The quadrant, from CPI momentum x IIP momentum.

    v99: the inflation axis reads the 3-print trail first — the same speed
    number the page has always shown — so one noisy release cannot flip the
    axis on its own. Release-pair, WPI momentum and level-vs-target remain
    as ordered fallbacks, and the basis in use is always named. Both
    corroborator directions are recorded so patch_regime can demand
    agreement before honouring a regime FLIP."""
    cpi = (pib.get("cpi") or {})
    wpi = (pib.get("wpi") or {})
    iip = (pib.get("iip") or {})
    gst = (pib.get("gst") or {})

    cpi_now = cpi.get("v")
    cpi_prev = cpi.get("prev")
    if cpi_now is None:
        cpi_now = _page_ml(page, "cpi")
    if cpi_prev is None:
        cpi_prev = _page_ml(page, "cpi_prev")
    wpi_now = wpi.get("v")
    wpi_prev = wpi.get("prev")
    if wpi_now is None:
        wpi_now = _page_mx(page, "wpi", "v")
    if wpi_prev is None:
        wpi_prev = _page_mx(page, "wpi", "prev")
    iip_now = iip.get("v")
    if iip_now is None:
        iip_now = _page_mx(page, "iip_p", "v")
        if iip_now is None:
            iip_now = _page_ml(page, "iip")
        iip_prev = _page_mx(page, "iip_p", "prev")
    else:
        iip_prev = _page_mx(page, "iip_p", "v")
        if iip_prev is not None and abs(iip_prev - iip_now) < 1e-9:
            iip_prev = _page_mx(page, "iip_p", "prev")
    gst_yoy = gst.get("yoy")
    if gst_yoy is None:
        gst_yoy = _page_mx(page, "gst", "yoy")
        gst_prev_yoy = _page_mx(page, "gst", "prev_yoy")
    else:
        gst_prev_yoy = _page_mx(page, "gst", "yoy")
        if gst_prev_yoy is not None and gst_prev_yoy == gst_yoy:
            gst_prev_yoy = _page_mx(page, "gst", "prev_yoy")

    # ── inflation axis: trail speed first ────────────────────────────────
    trail = _page_trail(page)
    if (cpi.get("v") is not None and trail
            and abs(trail[-1] - cpi["v"]) > 1e-9):
        trail = (trail + [cpi["v"]])[-6:]
    speed = round(trail[-1] - trail[-4], 2) if len(trail) >= 4 else None
    idir = 0
    ibasis = ""
    if speed is not None:
        idir = 1 if speed > 0.10 else (-1 if speed < -0.10 else 0)
        ibasis = f"CPI 3-print momentum ({speed:+.2f}pp)"
    if idir == 0:
        d2 = _dirn(cpi_now, cpi_prev)
        if d2 != 0:
            idir = d2
            ibasis = "CPI release pair"
    if idir == 0:
        d2 = _dirn(wpi_now, wpi_prev)
        if d2 != 0:
            idir = d2
            ibasis = "WPI momentum (CPI flat)"
    if idir == 0 and cpi_now is not None:
        idir = 1 if cpi_now >= 4.0 else -1
        ibasis = "CPI level vs 4% target (momentum flat)"

    # ── growth axis ──────────────────────────────────────────────────────
    gdir = _dirn(iip_now, iip_prev)
    gbasis = "IIP momentum"
    if gdir == 0:
        gdir = _dirn(gst_yoy, gst_prev_yoy, eps=0.3)
        gbasis = "GST momentum (IIP flat)"
    if gdir == 0 and iip_now is not None:
        gdir = 1 if iip_now >= 3.5 else -1
        gbasis = "IIP level vs 3.5% threshold (momentum flat)"

    if idir == 0 or gdir == 0:
        return {}

    # corroborator agreement, for the flip rule
    g_corrob = _dirn(gst_yoy, gst_prev_yoy, eps=0.3)
    i_corrob = _dirn(wpi_now, wpi_prev)

    quad = REGIME_QUADS[(gdir, idir)]
    arrows = {1: "↑", -1: "↓"}
    live_in = sorted(k for k in ("cpi", "wpi", "iip", "gst") if pib.get(k))
    periods = {
        "cpi": cpi.get("period", ""),
        "wpi": wpi.get("period") or _page_mx(page, "wpi", "period") or "",
        "iip": iip.get("period") or _page_mx(page, "iip_p", "period") or "",
        "gst": gst.get("period") or _page_mx(page, "gst", "period") or "",
    }
    lvl = _level_quad(cpi_now, iip_now)
    rf = _page_mlout_regime(page)
    rf_mapped = RF_MAP.get(rf.get("prediction") or "", None)
    out = {
        "quad": quad,
        "growth": {"dir": gdir, "arrow": arrows[gdir], "basis": gbasis,
                   "iip": iip_now, "iip_prev": iip_prev,
                   "iip_period": periods["iip"],
                   "gst_yoy": gst_yoy, "gst_period": periods["gst"],
                   "corrob": g_corrob},
        "inflation": {"dir": idir, "arrow": arrows[idir], "basis": ibasis,
                      "cpi": cpi_now, "cpi_prev": cpi_prev,
                      "cpi_period": periods["cpi"],
                      "wpi": wpi_now, "wpi_prev": wpi_prev,
                      "wpi_period": periods["wpi"],
                      "speed": speed, "corrob": i_corrob},
        "live_inputs": live_in,
        "carried_inputs": sorted(k for k in ("cpi", "wpi", "iip", "gst")
                                 if not pib.get(k)),
        "src": {k: pib[k].get("src", "") for k in live_in},
        "inputs_sig": "|".join(periods[k] for k in ("cpi", "wpi", "iip",
                                                    "gst")),
        "crosscheck": {
            "level": {"quad": lvl, "cpi": cpi_now, "iip": iip_now,
                      "agrees": (lvl == quad) if lvl else None},
            "rf": ({"quad_raw": rf.get("prediction"), "quad": rf_mapped,
                    "prob": rf.get("prob"),
                    "vintage": rf.get("generated", ""),
                    "agrees": (rf_mapped == quad) if rf_mapped else None}
                   if rf.get("prediction") else None),
        },
    }
    return out


def _merge_pib_mx(mx, pib, page):
    """Fold the wire's monthly prints into the MACRO_X payload, and carry
    forward the page's previous monthly blocks when this pass read nothing —
    a monthly figure that names its month is honest to carry; losing it to a
    failed fetch is not."""
    if pib.get("wpi"):
        w = pib["wpi"]
        mx["wpi"] = {"v": w["v"], "pct": True, "prev": w.get("prev"),
                     "period": w.get("period", ""),
                     "unit": ("yoy · " + w.get("period", "")).strip()}
    if pib.get("iip"):
        i = pib["iip"]
        prev = _page_mx(page, "iip_p", "v")
        mx["iip_p"] = {"v": i["v"], "pct": True,
                       "prev": (prev if prev is not None and
                                abs(prev - i["v"]) > 1e-9 else
                                _page_mx(page, "iip_p", "prev")),
                       "period": i.get("period", ""),
                       "unit": ("yoy · " + i.get("period", "")).strip()}
    if pib.get("gst"):
        g = pib["gst"]
        prev_yoy = _page_mx(page, "gst", "yoy")
        mx["gst"] = {"v": g["v"], "yoy": g.get("yoy"),
                     "prev_yoy": (prev_yoy if prev_yoy is not None and
                                  g.get("yoy") != prev_yoy else
                                  _page_mx(page, "gst", "prev_yoy")),
                     "period": g.get("period", ""),
                     "unit": ("₹ lakh crore · "
                              + g.get("period", "")
                              + (" · %+.1f%% yoy" % g["yoy"]
                                 if g.get("yoy") is not None else "")).strip()}
    carried = []
    for k in ("wpi", "iip_p", "gst"):
        if k not in mx:
            old = None
            try:
                mm = _re.search(r"window\.MACRO_X\s*=\s*(\{.*?\});", page,
                                _re.S)
                old = (json.loads(mm.group(1)) if mm else {}).get(k)
            except Exception:
                old = None
            if old and old.get("v") is not None:
                mx[k] = old
                carried.append(k)
    if carried:
        print("  macro blocks: carried " + ", ".join(carried)
              + " forward (each names its own month)")
    return mx


def _pib_log_msg(pib):
    if not pib:
        return "no CPI/WPI/IIP/GST release parsed off the PIB wire"
    bits = []
    for k in ("cpi", "wpi", "iip", "gst"):
        if pib.get(k):
            u = " lakh cr" if k == "gst" else "%"
            bits.append(k.upper() + " " + str(pib[k]["v"]) + u
                        + " (" + pib[k].get("period", "?") + ")")
    return ", ".join(bits) + " read off the ministry releases"


def _regime_log_msg(reg, html):
    if reg.get("quad"):
        return (reg["quad"] + " — growth " + reg["growth"]["arrow"]
                + ", inflation " + reg["inflation"]["arrow"]
                + (", all inputs live" if not reg.get("carried_inputs")
                   else ", carried: " + ", ".join(reg["carried_inputs"])))
    blk = _re.search(r"window\.REGIME_LIVE\s*=\s*(\{.*?\});", html, _re.S)
    try:
        prev = json.loads(blk.group(1)) if blk else {}
    except Exception:
        prev = {}
    return ("held at " + prev["quad"] + " (not recomputable this pass)"
            if prev.get("quad") else "no axis inputs available")


def patch_regime(html, reg, stamp):
    """window.REGIME_LIVE — the quadrant plus everything it was computed
    from, with hysteresis on regime CHANGES.

    A new quadrant is published immediately only when both corroborators
    (GST for growth, WPI for inflation) agree with their axis. Otherwise the
    standing regime holds and the page shows the flip as PENDING; it is
    honoured on a later pass that computes the same new quadrant from a
    fresh set of release periods. One noisy print can therefore propose a
    flip, but never execute one alone. A pass that cannot compute at all
    keeps the previous read and bumps only `checked`."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.REGIME_LIVE\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}

    def _publish(payload):
        newtxt = ("window.REGIME_LIVE = "
                  + json.dumps(payload, separators=(",", ":"),
                               ensure_ascii=False) + ";")
        if blk:
            return html[:blk.start()] + newtxt + html[blk.end():]
        i = html.find("window.PRICE_SRC")
        if i < 0:
            print("  regime: anchor missing (skipped)")
            return html
        return html[:i] + newtxt + "\n" + html[i:]

    if not reg or not reg.get("quad"):
        if not prev:
            return html
        prev["checked"] = now
        out = _publish(prev)
        print("  regime: not computable this pass — page keeps "
              + (prev.get("quad") or "its previous read")
              + " and bumps only checked")
        return out

    payload = dict(reg)
    payload["computed"] = now
    payload["checked"] = now
    new_q, old_q = reg["quad"], prev.get("quad")
    flip_note = ""

    if not old_q or old_q == new_q:
        payload["since"] = (prev.get("since") or now) if old_q == new_q \
            else now
        payload["prev_quad"] = prev.get("prev_quad")
        payload["pending"] = None
    else:
        g, f = reg["growth"], reg["inflation"]
        strong = (g.get("corrob") == g.get("dir")
                  and f.get("corrob") == f.get("dir"))
        pend = prev.get("pending") or {}
        confirmed = (pend.get("quad") == new_q
                     and pend.get("sig")
                     and pend.get("sig") != reg.get("inputs_sig"))
        if strong or confirmed:
            payload["since"] = now
            payload["prev_quad"] = old_q
            payload["pending"] = None
            flip_note = (" · FLIP from " + old_q + " ("
                         + ("both corroborators agree" if strong
                            else "confirmed by a later release") + ")")
        else:
            # the standing regime holds; the proposal is displayed, dated,
            # and waits for corroboration or a fresh release
            held = dict(prev)
            held["checked"] = now
            held["pending"] = {"quad": new_q, "first": pend.get("first")
                               or now, "sig": reg.get("inputs_sig"),
                               "growth": reg["growth"],
                               "inflation": reg["inflation"]}
            held["crosscheck"] = reg.get("crosscheck")
            out = _publish(held)
            print("  regime: " + old_q + " HELD — this pass computes "
                  + new_q + " but neither corroborator set agrees and no "
                  "later release has confirmed it yet (pending, shown on "
                  "the page)")
            return out

    out = _publish(payload)
    g, f = payload["growth"], payload["inflation"]
    cc = payload.get("crosscheck") or {}
    ccbits = []
    lv = (cc.get("level") or {})
    if lv.get("quad"):
        ccbits.append("level-method "
                      + ("agrees" if lv.get("agrees") else
                         "says " + lv["quad"]))
    rf = cc.get("rf") or {}
    if rf and rf.get("quad"):
        ccbits.append("RF " + ("agrees" if rf.get("agrees") else
                               "says " + rf["quad"]))
    print(f"  regime: {payload['quad']} — growth {g['arrow']} ({g['basis']})"
          f", inflation {f['arrow']} ({f['basis']})" + flip_note
          + (f" · held since {payload['since'][:11].strip()}"
             if payload["since"] != now else "")
          + (" · cross-checks: " + ", ".join(ccbits) if ccbits else "")
          + (" · inputs live: " + ", ".join(payload["live_inputs"])
             if payload["live_inputs"] else
             " · every input carried from the page's own last reads"))
    return out



# ═══════════════════════════════════════════════════════════════════════
#  v100 · INFLATION -> SECTORS. One headline CPI hides four different
#  businesses: the company whose INPUT is fuel, the one whose input is the
#  farm gate, the one whose OUTPUT is the manufactured-products index, and
#  the bank for whom inflation is a rate path. The release data carries all
#  of it. Every verdict below is arithmetic on named prints — the sector
#  MAP is framework (which industries live on which index) and says so;
#  the NUMBERS are never typed.
# ═══════════════════════════════════════════════════════════════════════

def build_sector_infl(pib, page):
    """window.SECTOR_INFL payload: inputs + per-sector verdicts, or {} when
    neither this pass nor the page carries the needed prints."""
    cpi = pib.get("cpi") or {}
    wpi = pib.get("wpi") or {}
    old = {}
    try:
        mm = _re.search(r"window\.SECTOR_INFL\s*=\s*(\{.*?\});", page, _re.S)
        old = json.loads(mm.group(1)) if mm else {}
    except Exception:
        old = {}
    oldin = old.get("inputs") or {}

    cv = cpi.get("v")
    if cv is None:
        cv = _page_ml(page, "cpi")
    cf = cpi.get("food", oldin.get("cpi_food"))
    cper = cpi.get("period") or oldin.get("cpi_period") or ""
    wv = wpi.get("v")
    if wv is None:
        wv = _page_mx(page, "wpi", "v")
    groups = wpi.get("groups") or oldin.get("wpi_groups")
    wper = (wpi.get("period") or _page_mx(page, "wpi", "period")
            or oldin.get("wpi_period") or "")
    if cv is None or wv is None or not groups:
        return {}

    fuel = groups.get("fuel")
    prim = groups.get("primary")
    man = groups.get("manuf")
    wedge = round(wv - cv, 2)

    def V(name, inp, out_, verdict, why):
        return {"sector": name, "input": inp, "output": out_,
                "verdict": verdict, "why": why}

    cards = []
    if fuel is not None and man is not None:
        d = round(fuel - man, 1)
        vd = ("SQUEEZE" if d > 3 else "PRESSURE" if d > 0.5 else
              "RELIEF" if fuel < 0 else "NEUTRAL")
        cards.append(V("Cement · Metals · Paints · Aviation",
                       f"fuel & power WPI {fuel}%",
                       f"manufactured-output WPI {man}%", vd,
                       f"energy costs are growing {d:+.1f}pp "
                       f"{'faster' if d > 0 else 'slower'} than what "
                       f"manufacturers are getting for output ({wper})"))
        cards.append(V("Upstream energy · Coal · OMC refiners",
                       f"fuel & power WPI {fuel}%", "realisations",
                       "BENEFIT" if fuel > 5 else "NEUTRAL",
                       f"the same {fuel}% that squeezes energy users is the "
                       f"revenue line here — the transfer is zero-sum"))
    if prim is not None and cf is not None:
        d = round(prim - cf, 1)
        vd = ("SQUEEZE" if d > 2 else "PRESSURE" if d > 0.5 else "MARGIN OK")
        cards.append(V("FMCG · Food processing",
                       f"farm-gate (primary articles WPI) {prim}%",
                       f"food CPI {cf}%", vd,
                       f"input food inflation vs what the shelf price is "
                       f"rising at: {d:+.1f}pp ({wper} vs {cper})"))
    if man is not None:
        vd = ("PRICING POWER" if man > cv + 0.5 else
              "WEAK PRICING" if man < cv - 0.5 else "NEUTRAL")
        cards.append(V("Industrials · Capital goods",
                       f"manufactured WPI {man}%", f"headline CPI {cv}%", vd,
                       f"output prices {'outrunning' if man > cv else 'lagging'} "
                       f"consumer inflation by {abs(round(man - cv, 1))}pp — "
                       f"the pricing-power proxy"))
    cards.append(V("Banks · NBFCs", f"CPI {cv}% vs the 4% target",
                   "the rate path",
                   "WATCH" if cv >= 4 else "TAILWIND",
                   (f"CPI at/above target argues against further cuts — "
                    f"NIMs hold but credit demand cools"
                    if cv >= 4 else
                    f"CPI below target keeps the cutting cycle alive — "
                    f"good for credit growth, watch NIMs")))
    cards.append(V("IT · Pharma exporters", "commodity-light cost base",
                   "INR channel", "INSULATED",
                   f"little direct commodity input; the WPI-CPI wedge "
                   f"({wedge:+.1f}pp) matters to them mainly through what "
                   f"it does to rates and the rupee"))

    return {"inputs": {"cpi": cv, "cpi_food": cf, "cpi_period": cper,
                       "wpi": wv, "wpi_groups": groups,
                       "wpi_period": wper, "wedge": wedge},
            "cards": cards}


def patch_sector_infl(html, data, stamp):
    """window.SECTOR_INFL — carry-forward on an empty pass, same rule as
    every monthly block: keep the last real read, bump only checked."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.SECTOR_INFL\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.SECTOR_INFL = "
               + json.dumps(prev, separators=(",", ":"),
                            ensure_ascii=False) + ";")
        html = html[:blk.start()] + new + html[blk.end():]
        print("  sector infl: no fresh prints — page keeps its last "
              "derivations and bumps only checked")
        return html
    payload = dict(data)
    payload["updated"] = now
    payload["checked"] = now
    new = ("window.SECTOR_INFL = "
           + json.dumps(payload, separators=(",", ":"),
                        ensure_ascii=False) + ";")
    if blk:
        html = html[:blk.start()] + new + html[blk.end():]
    else:
        i = html.find("window.PRICE_SRC")
        if i < 0:
            print("  sector infl: anchor missing (skipped)")
            return html
        html = html[:i] + new + "\n" + html[i:]
    print(f"  sector infl: {len(payload['cards'])} sector verdicts derived "
          f"(wedge {payload['inputs']['wedge']:+.1f}pp, "
          f"fuel {payload['inputs']['wpi_groups'].get('fuel')}%)")
    return html



# ═══════════════════════════════════════════════════════════════════════
#  v104 · THE IBJA FIX. India's official bullion association publishes an
#  AM and PM gold fix (999 fine, per 10g, ex-GST) every working day, in
#  server-rendered HTML with no key. This is the number the landed-cost
#  estimate was approximating; now the page carries the print itself, and
#  the import wedge over parity is computed rather than decomposed.
# ═══════════════════════════════════════════════════════════════════════

def _ibja_from_text(txt):
    """{g10_am, g10_pm, g22_10, silver_kg, date} off the IBJA page text.
    Bands: gold-999 per 10g must sit 60k-400k; silver per kg 50k-1000k —
    a parse outside those is a mis-read, not a market."""
    out = {}
    d = _re.search(r"(\d{2}/\d{2}/\d{4})", txt)
    if d:
        try:
            dd, mm, yy = d.group(1).split("/")
            out["date"] = (dd + " " + ("Jan Feb Mar Apr May Jun Jul Aug Sep "
                                       "Oct Nov Dec").split()[int(mm) - 1]
                           + " " + yy)
        except Exception:
            out["date"] = d.group(1)
    # segment = this date's block only, truncated at the NEXT date so an
    # older day's rows can never bleed into today's parse
    if d:
        nxt = _re.search(r"\d{2}/\d{2}/\d{4}", txt[d.end():])
        seg = txt[d.start():d.end() + nxt.start()] if nxt \
            else txt[d.start():d.start() + 1200]
    else:
        seg = txt[:1200]
    g999 = []
    for m in _re.finditer(r"\b999\b\D{0,30}?([\d,]{6,7})", seg):
        try:
            v = float(m.group(1).replace(",", ""))
        except Exception:
            continue
        pre = seg[max(0, m.start() - 12):m.start()]
        if "ilver" in pre:
            if 50000 <= v <= 1000000:
                out.setdefault("silver_kg", v)
            continue
        if 60000 <= v <= 400000:
            g999.append(v)
    if not g999:
        return {}
    out["g10_am"] = g999[0]
    if len(g999) > 1:
        out["g10_pm"] = g999[1]
    g916 = [float(m.group(1).replace(",", ""))
            for m in _re.finditer(r"\b916\b\D{0,30}?([\d,]{6,7})", seg)
            if 55000 <= float(m.group(1).replace(",", "")) <= 370000]
    if g916:
        out["g22_10"] = g916[-1]
    return out


def _ibja_co(raw):
    """The association's other domain serves the latest fix per GRAM —
    'Fine Gold (999) ₹ 15342' with a DD/MM/YYYY date. 999 only; the
    ibjarates.com door stays primary because it carries AM/PM, 916 and
    silver. Returns the same field shape, PM-only."""
    mm = _re.search(r"Fine\s*Gold\s*\(?999\)?[^\d]{0,120}?([\d,]{4,7})", raw,
                    _re.I | _re.S)
    if not mm:
        return {}
    try:
        g = float(mm.group(1).replace(",", "")) * 10.0
    except Exception:
        return {}
    if not (50000.0 <= g <= 500000.0):
        return {}
    out = {"g10_pm": g, "g10_am": None}
    dm = _re.search(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if dm:
        try:
            d = dt.date(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)))
            out["date"] = f"{d:%d %b %Y}"
        except Exception:
            pass
    return out


def fetch_ibja():
    for u in ("https://www.ibjarates.com", "https://ibjarates.com"):
        try:
            txt = _detag(_get(u, timeout=25, tries=1))
        except Exception:
            continue
        got = _ibja_from_text(txt)
        if got.get("g10_am") or got.get("g10_pm"):
            fix = got.get("g10_pm") or got.get("g10_am")
            print(f"  ibja: 999 fix ₹{fix:,.0f}/10g"
                  + (" (PM)" if got.get("g10_pm") else " (AM)")
                  + (f", silver ₹{got['silver_kg']:,.0f}/kg"
                     if got.get("silver_kg") else "")
                  + f" — {got.get('date', '?')}")
            return got
    try:
        got = _ibja_co(_get("https://ibja.co/", timeout=25, tries=1))
        if got.get("g10_pm"):
            print(f"  ibja: {got['g10_pm']:.0f}/10g off ibja.co"
                  + (f" ({got['date']})" if got.get("date") else "")
                  + " — PM only, the full fix door was refused")
            return got
    except Exception:
        pass
    print("  ibja: no fix parsed this pass (weekends and central holidays "
          "publish nothing) — page carries the last fix with its date")
    return {}


def patch_gold_inr(html, data, stamp):
    """window.GOLD_INR — the IBJA fix, carry-forward with its own date."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.GOLD_INR\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.GOLD_INR = "
               + json.dumps(prev, separators=(",", ":")) + ";")
        return html[:blk.start()] + new + html[blk.end():]
    # v110: the ibja.co fallback serves 999 only — carry the silver and
    # 22k figures forward from the previous read rather than nulling them,
    # and date the carried silver separately so the report cannot pass an
    # old silver fix off under a new gold date.
    _carry = lambda k: (data.get(k) if data.get(k) is not None
                        else prev.get(k if k != "g10_am" else "am"))
    payload = {"g10": data.get("g10_pm") or data.get("g10_am"),
               "am": _carry("g10_am"), "pm": data.get("g10_pm"),
               "g22_10": _carry("g22_10"),
               "silver_kg": _carry("silver_kg"),
               "fix_date": data.get("date", ""),
               "src": "IBJA " + ("PM" if data.get("g10_pm") else "AM")
                      + " fix (ex-GST)",
               "updated": now, "checked": now}
    if data.get("silver_kg") is None and prev.get("silver_kg") is not None:
        payload["silver_date"] = prev.get("silver_date") or prev.get("fix_date", "")
    new = ("window.GOLD_INR = "
           + json.dumps(payload, separators=(",", ":")) + ";")
    if blk:
        html = html[:blk.start()] + new + html[blk.end():]
    else:
        i = html.find("window.PRICE_SRC")
        if i < 0:
            return html
        html = html[:i] + new + "\n" + html[i:]
    return html



# ═══════════════════════════════════════════════════════════════════════
#  v106 · DERIVATIVES. The bhavcopy is a static ZIP on NSE's archive host,
#  which is a different animal from the JSON APIs that refuse this pipeline
#  four times out of five. Everything below is computed from that one file;
#  nothing is typed, and a failed fetch leaves the block untouched with its
#  own date on it rather than inventing a snapshot.
# ═══════════════════════════════════════════════════════════════════════

FNO_URLS = (
    "https://nsearchives.nseindia.com/content/fo/"
    "BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip",
    "https://archives.nseindia.com/content/fo/"
    "BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip",
)


def _get_bytes(url, timeout=45, tries=2):
    """Binary sibling of _get — the bhavcopy is a ZIP, not text."""
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": _UA,
                "Accept": "*/*",
                "Accept-Language": "en-IN,en;q=0.9",
                "Referer": "https://www.nseindia.com/all-reports",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                        # noqa: BLE001
            last = e
            if attempt + 1 < tries:
                _time.sleep(1.5 * (attempt + 1))
    raise last


def _fno_rows(raw_csv):
    """[dict] of the bhavcopy rows, keyed by the UDiFF column names. Columns
    are looked up BY NAME, never by position — NSE has reordered this file
    before and a positional parser would have silently mis-read it."""
    lines = raw_csv.strip().splitlines()
    if len(lines) < 2:
        return []
    hdr = [h.strip() for h in lines[0].split(",")]
    out = []
    for ln in lines[1:]:
        parts = ln.split(",")
        if len(parts) < len(hdr):
            continue
        out.append(dict(zip(hdr, [p.strip() for p in parts])))
    return out


def _f(row, *keys):
    for k in keys:
        v = row.get(k)
        if v not in (None, "", "-"):
            try:
                return float(v)
            except Exception:
                continue
    return None


def _fno_from_rows(rows):
    """The derivatives read: index basis, PCR, option OI walls, and the
    OI-vs-price quadrant for every stock future on its near-month contract."""
    if not rows:
        return {}
    # near-month = the earliest expiry present for each symbol
    fut, opt = {}, []
    for r in rows:
        tp = (r.get("FinInstrmTp") or "").upper()
        sym = (r.get("TckrSymb") or "").upper()
        xp = r.get("XpryDt") or ""
        if not sym or not xp:
            continue
        if tp in ("STF", "IDF", "FUTSTK", "FUTIDX"):
            cur = fut.get(sym)
            if cur is None or xp < cur["xp"]:
                fut[sym] = {"xp": xp, "cls": _f(r, "ClsPric", "SttlmPric"),
                            "prv": _f(r, "PrvsClsgPric"),
                            "oi": _f(r, "OpnIntrst"),
                            "doi": _f(r, "ChngInOpnIntrst"),
                            "und": _f(r, "UndrlygPric"),
                            "vol": _f(r, "TtlTradgVol"),
                            "idx": tp in ("IDF", "FUTIDX")}
        elif tp in ("STO", "IDO", "OPTSTK", "OPTIDX") and sym in ("NIFTY",
                                                                  "BANKNIFTY"):
            opt.append({"sym": sym, "xp": xp,
                        "ot": (r.get("OptnTp") or "").upper(),
                        "k": _f(r, "StrkPric"), "oi": _f(r, "OpnIntrst"),
                        "doi": _f(r, "ChngInOpnIntrst")})

    out = {"n_contracts": len(rows)}

    # ── index futures basis ───────────────────────────────────────────────
    idxs = {}
    for sym in ("NIFTY", "BANKNIFTY"):
        f = fut.get(sym)
        if f and f.get("cls") and f.get("und") and f["und"] > 0:
            bps = round((f["cls"] / f["und"] - 1) * 10000, 1)
            idxs[sym] = {"fut": round(f["cls"], 2), "spot": round(f["und"], 2),
                         "basis_bp": bps, "oi": f.get("oi"),
                         "doi": f.get("doi"), "expiry": f["xp"][:10]}
    if idxs:
        out["index"] = idxs

    # ── put-call ratio and the OI walls, near-month only ─────────────────
    for sym in ("NIFTY", "BANKNIFTY"):
        o = [x for x in opt if x["sym"] == sym and x["k"] and x["oi"]]
        if not o:
            continue
        near = min(x["xp"] for x in o)
        o = [x for x in o if x["xp"] == near]
        ce = sum(x["oi"] for x in o if x["ot"] == "CE")
        pe = sum(x["oi"] for x in o if x["ot"] == "PE")
        if ce <= 0:
            continue
        blk = {"pcr": round(pe / ce, 2), "expiry": near[:10]}
        top = lambda t: max(((x["k"], x["oi"]) for x in o if x["ot"] == t),
                            key=lambda z: z[1], default=(None, None))
        ck, cv = top("CE")
        pk, pv = top("PE")
        if ck:
            blk["call_wall"] = ck
        if pk:
            blk["put_wall"] = pk
        out.setdefault("options", {})[sym] = blk

    # ── the OI quadrant, per stock future ────────────────────────────────
    quads = {"long_buildup": [], "short_buildup": [],
             "short_covering": [], "long_unwinding": []}
    for sym, f in fut.items():
        if f["idx"] or not (f.get("cls") and f.get("prv") and f["prv"] > 0):
            continue
        doi = f.get("doi")
        if doi is None or not f.get("oi"):
            continue
        dp = (f["cls"] / f["prv"] - 1) * 100
        if abs(dp) < 0.15 or abs(doi) < 1:
            continue
        pct_oi = (doi / (f["oi"] - doi) * 100) if (f["oi"] - doi) > 0 else 0
        rec = {"sym": sym, "dp": round(dp, 2), "doi_pct": round(pct_oi, 1),
               "oi": int(f["oi"])}
        if dp > 0 and doi > 0:
            quads["long_buildup"].append(rec)
        elif dp < 0 and doi > 0:
            quads["short_buildup"].append(rec)
        elif dp > 0 and doi < 0:
            quads["short_covering"].append(rec)
        else:
            quads["long_unwinding"].append(rec)
    for k in quads:
        quads[k] = sorted(quads[k], key=lambda r: -abs(r["doi_pct"]))[:6]
    if any(quads.values()):
        out["quadrants"] = quads
        out["n_stocks"] = sum(len(v) for v in quads.values())
    return out


def fetch_fno():
    """Walk back up to six sessions — weekends, holidays and the evening
    publication lag all mean today's file may not exist yet."""
    import zipfile, io
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    for back in range(0, 7):
        day = now - dt.timedelta(days=back)
        if day.weekday() >= 5:
            continue
        ds = day.strftime("%Y%m%d")
        for tmpl in FNO_URLS:
            try:
                blob = _get_bytes(tmpl.format(d=ds))
                with zipfile.ZipFile(io.BytesIO(blob)) as z:
                    name = z.namelist()[0]
                    raw = z.read(name).decode("utf-8", "ignore")
            except Exception:
                continue
            got = _fno_from_rows(_fno_rows(raw))
            if got.get("index") or got.get("quadrants"):
                got["date"] = f"{ds[6:]} " + ("Jan Feb Mar Apr May Jun Jul "
                                              "Aug Sep Oct Nov Dec"
                                              ).split()[int(ds[4:6]) - 1] \
                              + f" {ds[:4]}"
                nb = (got.get("index", {}).get("NIFTY", {})
                      .get("basis_bp"))
                pcr = got.get("options", {}).get("NIFTY", {}).get("pcr")
                print(f"  fno: {got['n_contracts']} contracts read for "
                      f"{got['date']}"
                      + (f" · Nifty basis {nb:+.0f}bp" if nb is not None else "")
                      + (f" · PCR {pcr}" if pcr else "")
                      + (f" · {got.get('n_stocks', 0)} stock signals"
                         if got.get("n_stocks") else ""))
                return got
    print("  fno: no bhavcopy answered in the last six sessions — the "
          "derivatives block keeps its previous read AND its date")
    return {}


def patch_fno(html, data, stamp):
    """window.FNO_LIVE — same carry-forward honesty as every other block."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.FNO_LIVE\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.FNO_LIVE = "
               + json.dumps(prev, separators=(",", ":")) + ";")
        return html[:blk.start()] + new + html[blk.end():]
    payload = dict(data)
    payload["updated"] = now
    payload["checked"] = now
    payload["src"] = "NSE F&O bhavcopy"
    # a short basis trail, so the page can say whether the premium is
    # widening or draining rather than just what it is today
    trail = [t for t in (prev.get("basis_trail") or [])
             if isinstance(t, list) and len(t) == 2]
    nb = (data.get("index", {}).get("NIFTY", {}) or {}).get("basis_bp")
    if nb is not None and (not trail or trail[-1][0] != data.get("date")):
        trail.append([data.get("date", ""), nb])
    payload["basis_trail"] = trail[-40:]
    new = ("window.FNO_LIVE = "
           + json.dumps(payload, separators=(",", ":")) + ";")
    if blk:
        return html[:blk.start()] + new + html[blk.end():]
    i = html.find("window.PRICE_SRC")
    if i < 0:
        return html
    return html[:i] + new + "\n" + html[i:]


# ═══════════════════════════════════════════════════════════════════════
#  v106 · THE BANKING SYSTEM, out of the document we were already opening.
#  The WSS carries scheduled-bank deposits and credit and the money stock.
#  Credit growth is the channel every Reflation claim on this page runs
#  through; it has been dark since the data portal was rebuilt.
# ═══════════════════════════════════════════════════════════════════════

def _wss_banking(txt):
    """{credit_growth, deposit_growth, m3} in percent, from the WSS text.
    Bands are wide but real: India's credit and deposit growth have lived
    between -5% and 40% across every cycle since 1970, and M3 likewise."""
    out = {}

    # v108: on the real WSS 'Extract' page these live as TABLE rows, not
    # sentences — a label row of levels, then a 'Growth (Per cent)' row
    # whose LAST figure is the current year-on-year print:
    #   Aggregate Deposits 26284574 ... Growth (Per cent) -1.0 3.3 0.2 10.1 12.7
    def _grow_after(label):
        mm = _re.search(label + r"\b.{0,260}?Growth\s*\(\s*Per\s*cent\s*\)",
                        txt, _re.I | _re.S)
        if not mm:
            return None
        seg = txt[mm.end():mm.end() + 90]
        nums = _re.findall(r"-?\d{1,3}\.\d{1,2}", seg)
        if not nums:
            return None
        # v110: the WSS variation grid is five columns wide and the FIFTH
        # is the current year-on-year print. Row numbers like '2.1.1' bleed
        # into any last-number rule (that is how deposits once read 2.1),
        # so the position rule wins; 'last' only when the grid is short.
        return float(nums[4]) if len(nums) >= 5 else float(nums[-1])

    for key, label in (("deposit_growth", r"Aggregate\s+Deposits"),
                       ("credit_growth", r"Bank\s+Credit")):
        v = _grow_after(label)
        if v is not None and -5.0 <= v <= 40.0:
            out[key] = v
    # M3's row interleaves amounts and percents; the last decimal-pointed
    # figure inside the band is the current y/y print.
    mm = _re.search(r"\bM3\b((?:\s+\(?-?[\d,]+(?:\.\d+)?\)?){4,26})",
                    txt, _re.S)
    if mm:
        # v110: M3's row interleaves (amount, percent) pairs — take the last
        # percent that directly follows a big amount, so a bleeding section
        # number ('6.1 Currency…') can never pose as the print.
        pairs = _re.findall(r"(\d[\d,]{4,11})\s+(-?\d{1,2}\.\d{1,2})",
                            mm.group(1))
        cand = [float(p) for _a, p in pairs if abs(float(p)) <= 40.0]
        if cand and -5.0 <= cand[-1] <= 40.0:
            out["m3"] = cand[-1]
        else:
            loose = [t for t in _re.findall(r"-?[\d,]+\.\d+", mm.group(1))
                     if "," not in t and abs(float(t)) <= 40.0]
            if loose and -5.0 <= float(loose[-1]) <= 40.0:
                out["m3"] = float(loose[-1])

    # older sentence phrasings, kept as the fallback door
    pats = (
        ("credit_growth", r"Bank\s+Credit\b.{0,400}?"
                          r"(-?\d{1,2}\.\d)\s*(?:%|per\s*cent)"),
        ("deposit_growth", r"Aggregate\s+Deposits\b.{0,400}?"
                           r"(-?\d{1,2}\.\d)\s*(?:%|per\s*cent)"),
        ("m3", r"(?:Money\s+Stock|M3)\b.{0,400}?"
               r"(-?\d{1,2}\.\d)\s*(?:%|per\s*cent)"),
    )
    # v107: system liquidity, from the same document. This is the number
    # that explains the WACR-repo spread the OIS tab displays: a surplus
    # pins overnight money to the floor, a deficit pushes it to the ceiling.
    lm = _re.search(r"(?:Net\s+(?:Liquidity\s+)?(?:Injected|Absorbed)"
                    r"|Liquidity\s+Adjustment\s+Facility)"
                    r"[^\d\-]{0,120}(-?[\d,]{4,12})", txt, _re.I)
    if lm:
        try:
            v = float(lm.group(1).replace(",", "")) / 1e5   # cr -> lakh cr
            if 0.01 <= abs(v) <= 30.0:
                out["laf_lakh_cr"] = round(v, 2)
        except Exception:
            pass
    for key, pat in pats:
        mm = _re.search(pat, txt, _re.I | _re.S)
        if not mm:
            continue
        try:
            v = float(mm.group(1))
        except Exception:
            continue
        if -5.0 <= v <= 40.0:
            out[key] = v
    return out


def fetch_wss_banking():
    """Re-open the newest WSS release and read the banking aggregates.
    Shares the press-release index the reserves fetcher already walks."""
    for base in PRESS_INDEX:
        try:
            idx = _get(base, timeout=30)
        except Exception:
            continue
        prids = []
        for mm in _re.finditer(r"Weekly Statistical Supplement", idx, _re.I):
            back = idx[max(0, mm.start() - 2500): mm.start()]
            pm = _re.findall(r"prid=(\d{3,7})", back)
            if pm:
                prids.append(int(pm[-1]))
        for pid in sorted(set(prids), reverse=True)[:2]:
            try:
                got = _wss_banking(_detag(_get(f"{base}?prid={pid}",
                                               timeout=30)))
            except Exception:
                continue
            if got:
                print("  wss banking: "
                      + ", ".join(f"{k} {v}%" for k, v in sorted(got.items()))
                      + f" (release {pid})")
                return got
    print("  wss banking: no aggregates parsed — those tiles keep their "
          "last read")
    return {}


def fetch_gsec10_rbi():
    """The 10-year benchmark yield read DAILY off the RBI home page's
    'Government Securities Market' panel, which quotes the traded stock by
    name — '6.94% GS 2036 : 6.7820%'. The parser picks the bond maturing
    closest to ten years out and says which one it used. Official, daily,
    keyless — FRED's monthly OECD series becomes the fallback, not the
    anchor."""
    yr = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).year
    for u in RBI_HOME_URLS:
        try:
            raw = _get(u, timeout=25, tries=1)
        except Exception:
            continue
        best = {}
        for mm in _re.finditer(
                r"(\d{1,2}\.\d{2})\s*%\s*GS\s*(20\d{2})[^0-9%]{0,120}?"
                r"(\d{1,2}\.\d{1,4})\s*%", raw):
            mat = int(mm.group(2))
            try:
                y = float(mm.group(3))
            except Exception:
                continue
            if not (3.0 <= y <= 15.0):
                continue
            gap = abs(mat - (yr + 10))
            if gap <= 3 and (not best or gap < best["gap"]):
                best = {"v": round(y, 2), "gap": gap,
                        "bond": f"{mm.group(1)}% GS {mat}"}
        if best:
            best.pop("gap", None)
            now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5,
                                                           minutes=30)))
            best["period"] = f"{now:%d %b %Y}"
            best["src"] = f"RBI home \u00b7 {best['bond']} (secondary market)"
            best["freq"] = "daily"
            print(f"  gsec10: {best['v']}% \u2014 {best['bond']} "
                  f"(RBI home, daily)")
            return best
    return {}


def fetch_gsec10():
    """India's 10-year benchmark yield from FRED's keyless CSV (OECD series).
    Monthly, and the tile says monthly — a dated real print beats the
    model-derived number this page has carried since v92."""
    for sid in ("INDIRLTLT01STM", "IRLTLT01INM156N"):
        try:
            raw = _get("https://fred.stlouisfed.org/graph/fredgraph.csv?id="
                       + sid, timeout=30)
        except Exception:
            continue
        rows = []
        for line in raw.strip().splitlines()[1:]:
            try:
                d, v = line.split(",")[:2]
                if v and v != ".":
                    rows.append((d[:7], float(v)))
            except Exception:
                continue
        rows = [r for r in rows if 3.0 <= r[1] <= 15.0]
        if rows:
            d, v = rows[-1]
            prev = rows[-2][1] if len(rows) > 1 else None
            print(f"  gsec10: {v}% ({d}, FRED {sid})")
            return {"v": round(v, 2), "period": d, "prev": prev,
                    "src": f"FRED {sid} (monthly)"}
    print("  gsec10: FRED refused — the 10-year stays model-derived")
    return {}



# ═══════════════════════════════════════════════════════════════════════
#  v109 · MOVERS. The full-market equity bhavcopy — every listed name's
#  close, previous close and traded value in one keyless static ZIP on the
#  archive host the F&O door already reads. Day moves come from one file;
#  week moves from joining it against the file five trading sessions back.
#  A turnover floor keeps illiquid microcaps from topping the boards on a
#  five-lakh trade.
# ═══════════════════════════════════════════════════════════════════════

CM_URLS = (
    "https://nsearchives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip",
    "https://archives.nseindia.com/content/cm/"
    "BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip",
)
MOVERS_FLOOR_CR = 5.0     # list floor: ₹5cr traded — labelled on the page
MOVERS_MAP_CR = 0.5       # search-map floor: thinner names still findable


def _cm_bhavcopy(day):
    """{sym: (close, prev_close, turnover_cr)} for one session, EQ series
    only. Empty dict when the archive has no file for that date."""
    import zipfile, io
    tag = f"{day:%Y%m%d}"
    for u in CM_URLS:
        try:
            blob = _get_bytes(u.format(d=tag))
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                raw = z.read(z.namelist()[0]).decode("utf-8", "ignore")
        except Exception:
            continue
        out = {}
        for r in _fno_rows(raw):
            if (r.get("SctySrs") or "").strip().upper() != "EQ":
                continue
            sym = (r.get("TckrSymb") or "").strip()
            try:
                cls = float(r.get("ClsPric") or 0)
                prv = float(r.get("PrvsClsgPric") or 0)
                trf = float(r.get("TtlTrfVal") or 0) / 1e7
            except Exception:
                continue
            if not sym or cls <= 0:
                continue
            out[sym] = (cls, prv, trf)
        if out:
            return out
    return {}


def fetch_movers():
    """MOVERS_LIVE: intraday and intraweek boards plus a full search map.
    Walks back over holidays for the anchor session, then five trading
    sessions further for the week base."""
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    day = dt.datetime.now(ist)
    anchor, cur = None, {}
    for _ in range(7):
        if day.weekday() < 5:
            cur = _cm_bhavcopy(day)
            if cur:
                anchor = day
                break
        day -= dt.timedelta(days=1)
    if not cur:
        print("  movers: no equity bhavcopy answered in the last week — "
              "the boards keep their previous session AND its date")
        return {}
    base, bday, back = {}, anchor, 0
    probe = anchor
    for _ in range(15):
        probe -= dt.timedelta(days=1)
        if probe.weekday() >= 5:
            continue
        back += 1
        if back < 5:
            continue
        base = _cm_bhavcopy(probe)
        if base:
            bday = probe
            break
    boards = {"top_day": [], "bot_day": [], "top_wk": [], "bot_wk": []}
    allmap, rows = {}, []
    for sym, (cls, prv, trf) in cur.items():
        d_pct = round((cls / prv - 1) * 100, 2) if prv > 0 else None
        w_pct = None
        b = base.get(sym)
        if b and b[0] > 0:
            w_pct = round((cls / b[0] - 1) * 100, 2)
        if trf >= MOVERS_MAP_CR and (d_pct is not None or w_pct is not None):
            allmap[sym] = [d_pct, w_pct, round(trf, 1), round(cls, 2)]
        if d_pct is not None and abs(d_pct) <= 35.0:
            rows.append((sym, cls, d_pct, w_pct, trf))
    liq = [r for r in rows if r[4] >= MOVERS_FLOOR_CR]
    tile = lambda r: {"s": r[0], "c": round(r[1], 2), "d": r[2],
                      "w": r[3], "t": round(r[4], 1)}
    boards["top_day"] = [tile(r) for r in sorted(
        liq, key=lambda r: r[2], reverse=True)[:8]]
    boards["bot_day"] = [tile(r) for r in sorted(liq, key=lambda r: r[2])[:8]]
    wk = [r for r in liq if r[3] is not None and abs(r[3]) <= 80.0]
    boards["top_wk"] = [tile(r) for r in sorted(
        wk, key=lambda r: r[3], reverse=True)[:8]]
    boards["bot_wk"] = [tile(r) for r in sorted(wk, key=lambda r: r[3])[:8]]
    out = {"date": f"{anchor:%d %b %Y}",
           "wk_base": f"{bday:%d %b %Y}" if base else "",
           "n": len(cur), "n_liquid": len(liq), "n_map": len(allmap),
           "floor_cr": MOVERS_FLOOR_CR, "map_floor_cr": MOVERS_MAP_CR,
           "all": allmap,
           "src": "NSE equity bhavcopy (UDiFF), EQ series",
           **boards}
    print(f"  movers: {len(cur)} names, {len(liq)} above the "
          f"\u20b9{MOVERS_FLOOR_CR:g}cr floor; day board "
          + (f"+{boards['top_day'][0]['d']}% {boards['top_day'][0]['s']}"
             if boards["top_day"] else "empty")
          + (f", week base {out['wk_base']}" if base else ", week base MISSING"))
    return out


def patch_movers(html, data, stamp):
    """window.MOVERS_LIVE — same carry-forward contract as every block."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.MOVERS_LIVE\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.MOVERS_LIVE = "
               + json.dumps(prev, separators=(",", ":")) + ";")
        return html[:blk.start()] + new + html[blk.end():]
    payload = dict(data)
    payload["updated"] = now
    payload["checked"] = now
    new = ("window.MOVERS_LIVE = "
           + json.dumps(payload, separators=(",", ":")) + ";")
    if blk:
        return html[:blk.start()] + new + html[blk.end():]
    i = html.find("window.PRICE_SRC")
    if i < 0:
        return html
    return html[:i] + new + "\n" + html[i:]


# ═══════════════════════════════════════════════════════════════════════
#  v107 · CURVES. FRED serves every US Treasury tenor, the breakeven, the
#  real yield and both credit-spread indices as keyless daily CSVs, on the
#  transport this pipeline already uses for the reserves history. India's
#  10-year comes from the same place. Everything else on the India curve is
#  assembled from prints this terminal already reads live — the policy
#  corridor and the OIS path — and the page says so rather than implying an
#  official par curve it does not have.
# ═══════════════════════════════════════════════════════════════════════

FRED_CURVE = {
    "us3m": "DGS3MO", "us2y": "DGS2", "us5y": "DGS5",
    "us10y": "DGS10", "us30y": "DGS30",
    "us_2s10s": "T10Y2Y", "us_3m10y": "T10Y3M",
    "us_be10": "T10YIE", "us_real10": "DFII10",
    "hy_oas": "BAMLH0A0HYM2", "ig_oas": "BAMLC0A0CM",
    "in10y": "INDIRLTLT01STM",
}


def _fred_series(raw):
    """[(date, value)] from a FRED single-series CSV, '.' rows dropped."""
    out = []
    for line in raw.strip().splitlines()[1:]:
        p = line.split(",")
        if len(p) < 2:
            continue
        v = p[1].strip()
        if not v or v == ".":
            continue
        try:
            out.append((p[0].strip()[:10], float(v)))
        except Exception:
            continue
    return out


def _fred_multi(raw):
    """{series_id: [(date, value)]} from a multi-series FRED CSV. FRED will
    take comma-separated ids in one request; if that ever stops working the
    caller falls back to one request per series, which is why both shapes
    are parsed here."""
    lines = raw.strip().splitlines()
    if len(lines) < 2:
        return {}
    hdr = [h.strip() for h in lines[0].split(",")]
    if len(hdr) < 2:
        return {}
    out = {h: [] for h in hdr[1:]}
    for line in lines[1:]:
        p = [x.strip() for x in line.split(",")]
        if len(p) < 2:
            continue
        d = p[0][:10]
        for i, h in enumerate(hdr[1:], start=1):
            if i >= len(p):
                continue
            v = p[i]
            if not v or v == ".":
                continue
            try:
                out[h].append((d, float(v)))
            except Exception:
                continue
    return {k: v for k, v in out.items() if v}


TSY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/"
           "interest-rates/daily-treasury-rates.csv/{y}/all?type="
           "daily_treasury_{kind}&field_tdr_date_value={y}&page&_format=csv")


def _tsy_csv(raw, cols):
    """{key: [(iso_date, v)] ascending} off a treasury.gov daily-rates CSV.
    Rows arrive newest first, dates are MM/DD/YYYY, headers are quoted."""
    lines = raw.strip().splitlines()
    if len(lines) < 2:
        return {}
    hdr = [h.strip().strip('"') for h in lines[0].split(",")]
    idx = {}
    for want, names in cols.items():
        for n in names:
            if n in hdr:
                idx[want] = hdr.index(n)
                break
    if not idx:
        return {}
    out = {k: [] for k in idx}
    for ln in lines[1:]:
        p = [x.strip().strip('"') for x in ln.split(",")]
        if len(p) < 2 or "/" not in p[0]:
            continue
        try:
            mth, day, yr = p[0].split("/")
            iso = f"{int(yr):04d}-{int(mth):02d}-{int(day):02d}"
        except Exception:
            continue
        for k, i in idx.items():
            if i < len(p) and p[i]:
                try:
                    v = float(p[i])
                except Exception:
                    continue
                if -5.0 < v < 25.0:
                    out[k].append((iso, v))
    return {k: sorted(v) for k, v in out.items() if v}


def _treasury_curves():
    """FRED-keyed series off the US Treasury's own daily CSVs — the
    resilience door for when FRED won't serve. Nominal par fills the five
    tenors, the real curve carries the 10-year TIPS yield. Keyless static
    files, one per calendar year; early in January the current year is
    thin, so the previous year is appended for the one-month deltas."""
    yr = dt.datetime.now(dt.timezone.utc).year
    out = {}
    NOM = {"DGS3MO": ("3 Mo",), "DGS2": ("2 Yr",), "DGS5": ("5 Yr",),
           "DGS10": ("10 Yr",), "DGS30": ("30 Yr",)}
    REAL = {"DFII10": ("10 YR", "10 Yr")}
    for kind, cols in (("yield_curve", NOM), ("real_yield_curve", REAL)):
        got = {}
        try:
            got = _tsy_csv(_get(TSY_URL.format(y=yr, kind=kind),
                                timeout=45, tries=2), cols)
        except Exception as e:
            print(f"  curves: treasury.gov {kind} refused "
                  f"({type(e).__name__})")
        if got and len(next(iter(got.values()))) < 25:
            try:
                prev = _tsy_csv(_get(TSY_URL.format(y=yr - 1, kind=kind),
                                     timeout=45, tries=1), cols)
                for k in got:
                    got[k] = sorted((prev.get(k) or []) + got[k])
            except Exception:
                pass
        out.update(got)
    return out


def fetch_curves(page="", g10=None):
    """Everything curve-shaped, in one place. v108: three independent
    sections — FRED, the treasury.gov fallback, and the India assembly —
    so a refused US source can no longer silence the India curve."""
    g10 = g10 or {}
    ids = list(dict.fromkeys(FRED_CURVE.values()))
    data = {}
    try:
        data = _fred_multi(_get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
            + ",".join(ids), timeout=45, tries=2))
    except Exception:
        data = {}
    missing = [i for i in ids if i not in data]
    for sid in missing:                       # per-series fallback
        try:
            got = _fred_series(_get(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + sid,
                timeout=30, tries=1))
            if got:
                data[sid] = got
        except Exception:
            continue
    if data:
        print(f"  curves: FRED answered {len(data)} of {len(ids)} series")
    else:
        print("  curves: FRED refused every series — trying treasury.gov "
              "for the US curve; the India side does not depend on it")
    CORE = ("DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30")
    if any(k not in data for k in CORE + ("DFII10",)):
        tsy = _treasury_curves()
        filled = [k for k in CORE + ("DFII10",)
                  if k not in data and tsy.get(k)]
        for k in filled:
            data[k] = tsy[k]
        if filled:
            print(f"  curves: treasury.gov filled {len(filled)} series "
                  f"({', '.join(filled)})")
    if data.get("DGS10") and data.get("DFII10") and "T10YIE" not in data:
        nom = dict(data["DGS10"])
        be = [(d, round(v_n - v_r, 2)) for d, v_r in data["DFII10"]
              for v_n in (nom.get(d),) if v_n is not None]
        if be:
            data["T10YIE"] = be
            print("  curves: 10y breakeven computed as nominal minus real")

    def S(key):
        return data.get(FRED_CURVE[key]) or []

    def lastv(key):
        ser = S(key)
        return ser[-1][1] if ser else None

    def delta(key, back):
        ser = S(key)
        if len(ser) > back:
            return round(ser[-1][1] - ser[-(back + 1)][1], 2)
        return None

    # ── the US curve, its shape, and how it got here ─────────────────────
    us = {}
    for k, lab in (("us3m", "3m"), ("us2y", "2y"), ("us5y", "5y"),
                   ("us10y", "10y"), ("us30y", "30y")):
        v = lastv(k)
        if v is not None:
            us[lab] = v
    out = {}
    if len(us) >= 3:
        out["us"] = us
        ser = S("us10y")
        if ser:
            out["us_date"] = ser[-1][0]
    s2, s10 = lastv("us2y"), lastv("us10y")
    if s2 is not None and s10 is not None:
        out["us_2s10s"] = round(s10 - s2, 2)
    else:
        v = lastv("us_2s10s")
        if v is not None:
            out["us_2s10s"] = v
    v = lastv("us_3m10y")
    if v is not None:
        out["us_3m10y"] = v
    elif s10 is not None and lastv("us3m") is not None:
        out["us_3m10y"] = round(s10 - lastv("us3m"), 2)

    # ── the regime, from one month of change in the two anchors ──────────
    # 21 observations back on a daily series is a month of trading.
    d2, d10 = delta("us2y", 21), delta("us10y", 21)
    if d2 is None or d10 is None:
        d2 = d2 if d2 is not None else delta("us_2s10s", 21)
        d10 = d10 if d10 is not None else 0.0
    if d2 is not None and d10 is not None:
        avg = (d2 + d10) / 2.0
        slope = d10 - d2
        if abs(avg) < 0.03 and abs(slope) < 0.03:
            name, why = "FLAT / RANGE", ("neither end has moved enough in a "
                                         "month to call a direction")
        else:
            bull = avg < 0
            steep = slope > 0
            name = ("BULL " if bull else "BEAR ") + \
                   ("STEEPENER" if steep else "FLATTENER")
            why = (f"2-year {d2:+.2f}pp and 10-year {d10:+.2f}pp over a month: "
                   f"yields {'falling' if bull else 'rising'} and the curve "
                   f"{'steepening' if steep else 'flattening'}")
        out["us_regime"] = {"name": name, "why": why, "d2": d2, "d10": d10,
                            "window": "1 month"}
    if out.get("us_2s10s") is not None and out["us_2s10s"] < 0:
        out["us_inverted"] = True

    # ── what the curve is pricing INSIDE the nominal yield ───────────────
    be, real = lastv("us_be10"), lastv("us_real10")
    if be is not None:
        out["us_breakeven10"] = be
        out["us_be_chg"] = delta("us_be10", 21)
    if real is not None:
        out["us_real10"] = real

    # ── credit, as the cross-check on the curve's story ──────────────────
    hy, ig = lastv("hy_oas"), lastv("ig_oas")
    cr = {}
    if hy is not None:
        cr["hy_oas"] = hy
        cr["hy_chg"] = delta("hy_oas", 21)
    if ig is not None:
        cr["ig_oas"] = ig
    if cr:
        out["credit"] = cr

    # ── India: the 10-year anchor, and the carry over the US ─────────────
    # v108: the anchor prefers the RBI home page's DAILY secondary-market
    # quote (passed in as g10); FRED's monthly OECD series is the fallback
    # and, when both serve, the monthly print rides along as a cross-check.
    inr = {}
    anchor = dict(g10) if g10.get("v") is not None else {}
    i10 = lastv("in10y")
    if anchor:
        inr["10y"] = anchor["v"]
        inr["10y_period"] = anchor.get("period", "")
        inr["10y_src"] = anchor.get("src", "")
        if i10 is not None:
            inr["10y_fred"] = i10
    elif i10 is not None:
        ser = S("in10y")
        anchor = {"v": i10, "period": ser[-1][0][:7],
                  "src": f"FRED {FRED_CURVE['in10y']} (monthly)"}
        inr["10y"] = i10
        inr["10y_period"] = anchor["period"]
        inr["10y_prev"] = ser[-2][1] if len(ser) > 1 else None
    if anchor and s10 is not None:
        out["carry_in_us"] = round(anchor["v"] - s10, 2)
    # the short end from prints this terminal already reads live
    try:
        wacr = _page_ml(page, "mibor_on")
        repo = _page_ml(page, "repo")
        if wacr is not None:
            inr["on"] = wacr
        if repo is not None:
            inr["repo"] = repo
        mm = _re.search(r"const OIS_CURVE\s*=\s*\[(.*?)\];", page, _re.S)
        if mm:
            pts = _re.findall(r"\{m:\s*([\d.]+)\s*,\s*r:\s*([\d.]+)\s*\}",
                              mm.group(1))
            for m_, r_ in pts:
                if abs(float(m_) - 12) < 0.01:
                    inr["1y_ois"] = float(r_)
                if abs(float(m_) - 60) < 0.01:
                    inr["5y_ois"] = float(r_)
    except Exception:
        pass
    if inr.get("10y") is not None and inr.get("1y_ois") is not None:
        inr["1s10s"] = round(inr["10y"] - inr["1y_ois"], 2)
    if inr:
        out["india"] = inr
    cpi = _page_ml(page, "cpi")
    if anchor.get("v") is not None and cpi is not None:
        out["india_real10"] = round(anchor["v"] - cpi, 2)

    # ── India, assembled and labelled ────────────────────────────────────
    try:
        mmo = fetch_rbi_mmo()
    except Exception as e:
        print(f"  mmo: skipped ({type(e).__name__})")
        mmo = {}
    try:
        icv = build_india_curve(page, mmo, anchor)
        if icv.get("points"):
            out["india_curve"] = icv
            # India's regime: the overnight end against the 10-year end, both
            # measured over a month — the only window on which every
            # component of this assembled curve genuinely moves
            d_sh = d_lg = None
            base_d = ""
            try:
                pm = _re.search(r"window\.CURVES_LIVE\s*=\s*(\{.*?\});",
                                page, _re.S)
                pv = json.loads(pm.group(1)) if pm else {}
                tr = [t for t in (pv.get("india_trail") or [])
                      if isinstance(t, list) and len(t) == 3]
                base = tr[-21] if len(tr) >= 21 else (tr[0] if tr else None)
                pts_now = icv["points"]
                if base and pts_now.get("ON") is not None \
                        and pts_now.get("10Y") is not None \
                        and base[1] is not None and base[2] is not None:
                    d_sh = pts_now["ON"] - base[1]
                    d_lg = pts_now["10Y"] - base[2]
                    base_d = base[0]
                elif pv:
                    p0 = (pv.get("india_curve") or {}).get("points") or {}
                    if p0.get("ON") is not None \
                            and pts_now.get("ON") is not None:
                        d_sh = pts_now["ON"] - p0["ON"]
                    d_lg = (icv.get("ten_year") or {}).get("adj_pp")
            except Exception:
                d_sh = d_lg = None
            reg = classify_curve(d_sh, d_lg)
            if reg:
                if base_d:
                    reg["window"] = f"since {base_d}"
                out["india_regime"] = reg
    except Exception as e:
        print(f"  india curve: skipped ({type(e).__name__})")

    bits = []
    if out.get("india_curve", {}).get("points"):
        _p = out["india_curve"]["points"]
        bits.append("IN curve " + "/".join(
            f"{k} {_p[k]}" for k in ("ON", "1Y", "10Y") if k in _p))
    if out.get("india_regime"):
        bits.append("IN " + out["india_regime"]["name"])
    if out.get("us_regime"):
        bits.append(out["us_regime"]["name"])
    if out.get("us_2s10s") is not None:
        bits.append(f"US 2s10s {out['us_2s10s']:+.2f}")
    if out.get("carry_in_us") is not None:
        bits.append(f"IN-US carry {out['carry_in_us']:+.2f}pp")
    if cr.get("hy_oas") is not None:
        bits.append(f"HY OAS {cr['hy_oas']}")
    print("  curves: " + " · ".join(bits) if bits
          else "  curves: parsed but empty")
    return out


def patch_curves(html, data, stamp):
    """window.CURVES_LIVE — carry-forward with its own date, as ever."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.CURVES_LIVE\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.CURVES_LIVE = "
               + json.dumps(prev, separators=(",", ":")) + ";")
        return html[:blk.start()] + new + html[blk.end():]
    payload = dict(data)
    payload["updated"] = now
    payload["checked"] = now
    payload["src"] = ("FRED / treasury.gov (US curve, breakeven, credit) "
                      "+ RBI home & money-market ops + this terminal's own "
                      "corridor and OIS reads (India)")
    trail = [t for t in (prev.get("slope_trail") or [])
             if isinstance(t, list) and len(t) == 2]
    if data.get("us_2s10s") is not None:
        d = data.get("us_date", "")
        if not trail or trail[-1][0] != d:
            trail.append([d, data["us_2s10s"]])
    payload["slope_trail"] = trail[-60:]
    # v108: one India point per day — [date, ON, 10Y] — so the curve regime
    # can be measured over a real month of THIS page's own reads
    itr = [t for t in (prev.get("india_trail") or [])
           if isinstance(t, list) and len(t) == 3]
    icp = (data.get("india_curve") or {}).get("points") or {}
    if icp.get("ON") is not None:
        d = f"{stamp:%Y-%m-%d}"
        pt = [d, icp.get("ON"), icp.get("10Y")]
        if itr and itr[-1][0] == d:
            itr[-1] = pt          # the last pass of the day wins
        else:
            itr.append(pt)
    payload["india_trail"] = itr[-90:]
    new = ("window.CURVES_LIVE = "
           + json.dumps(payload, separators=(",", ":")) + ";")
    if blk:
        return html[:blk.start()] + new + html[blk.end():]
    i = html.find("window.PRICE_SRC")
    if i < 0:
        return html
    return html[:i] + new + "\n" + html[i:]


# ═══════════════════════════════════════════════════════════════════════
#  v107 · THE EQUITY RISK PREMIUM. NSE publishes a daily indices close file
#  carrying P/E, P/B and dividend yield for every index — a static CSV on
#  the same archive host as the bhavcopy. Earnings yield minus the 10-year
#  is the single best answer to "is this market cheap", and the terminal
#  has never been able to compute it because it had neither number.
# ═══════════════════════════════════════════════════════════════════════

IDX_URLS = (
    "https://nsearchives.nseindia.com/content/indices/ind_close_all_{d}.csv",
    "https://archives.nseindia.com/content/indices/ind_close_all_{d}.csv",
)


def _idx_from_csv(raw, want=("NIFTY 50", "NIFTY BANK", "NIFTY MIDCAP 100")):
    """{index: {close, pe, pb, dy}} from NSE's daily indices close file."""
    lines = raw.strip().splitlines()
    if len(lines) < 2:
        return {}
    hdr = [h.strip().strip('"').upper() for h in lines[0].split(",")]

    def col(*names):
        for n in names:
            if n in hdr:
                return hdr.index(n)
        return None
    ci = col("INDEX NAME", "INDEXNAME")
    cc = col("CLOSING INDEX VALUE", "CLOSE")
    cp = col("P/E", "PE")
    cb = col("P/B", "PB")
    cd = col("DIV YIELD", "DIVIDEND YIELD", "DIV_YIELD")
    if ci is None or cc is None:
        return {}
    out = {}
    for ln in lines[1:]:
        p = [x.strip().strip('"') for x in ln.split(",")]
        if len(p) <= max(x for x in (ci, cc, cp, cb, cd) if x is not None):
            continue
        nm = p[ci].upper()
        if nm not in want:
            continue
        rec = {}
        for key, idx in (("close", cc), ("pe", cp), ("pb", cb), ("dy", cd)):
            if idx is None:
                continue
            try:
                v = float(p[idx])
            except Exception:
                continue
            if key == "pe" and not (3 <= v <= 120):
                continue
            if key == "pb" and not (0.2 <= v <= 30):
                continue
            if key == "dy" and not (0 <= v <= 15):
                continue
            rec[key] = v
        if rec.get("close"):
            out[nm] = rec
    return out


def fetch_index_valuation():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    for back in range(0, 7):
        day = now - dt.timedelta(days=back)
        if day.weekday() >= 5:
            continue
        ds = day.strftime("%d%m%Y")
        for tmpl in IDX_URLS:
            try:
                got = _idx_from_csv(_get(tmpl.format(d=ds), timeout=30,
                                         tries=1))
            except Exception:
                continue
            if got.get("NIFTY 50", {}).get("pe"):
                got["date"] = day.strftime("%d %b %Y")
                pe = got["NIFTY 50"]["pe"]
                print(f"  valuation: Nifty P/E {pe} (earnings yield "
                      f"{round(100 / pe, 2)}%) — {got['date']}")
                return got
    print("  valuation: no NSE indices file answered — the ERP tile keeps "
          "its last read")
    return {}


def patch_valuation(html, data, gsec10, stamp):
    """window.VALUATION — P/E, earnings yield, and the equity risk premium
    against whatever 10-year the page currently holds."""
    now = f"{stamp:%a %b %d, %Y %H:%M} IST"
    blk = _re.search(r"window\.VALUATION\s*=\s*(\{.*?\});", html, _re.S)
    prev = {}
    if blk:
        try:
            prev = json.loads(blk.group(1))
        except Exception:
            prev = {}
    if not data:
        if not blk or not prev:
            return html
        prev["checked"] = now
        new = ("window.VALUATION = "
               + json.dumps(prev, separators=(",", ":")) + ";")
        return html[:blk.start()] + new + html[blk.end():]
    payload = {"date": data.get("date", ""), "indices": {},
               "updated": now, "checked": now, "src": "NSE daily indices file"}
    for k, v in data.items():
        if isinstance(v, dict) and v.get("pe"):
            payload["indices"][k] = v
    n50 = payload["indices"].get("NIFTY 50") or {}
    if n50.get("pe"):
        ey = round(100.0 / n50["pe"], 2)
        payload["earnings_yield"] = ey
        if gsec10:
            payload["gsec10"] = gsec10
            payload["erp"] = round(ey - gsec10, 2)
    trail = [t for t in (prev.get("erp_trail") or [])
             if isinstance(t, list) and len(t) == 2]
    if payload.get("erp") is not None and (
            not trail or trail[-1][0] != payload["date"]):
        trail.append([payload["date"], payload["erp"]])
    payload["erp_trail"] = trail[-60:]
    new = ("window.VALUATION = "
           + json.dumps(payload, separators=(",", ":")) + ";")
    if blk:
        return html[:blk.start()] + new + html[blk.end():]
    i = html.find("window.PRICE_SRC")
    if i < 0:
        return html
    return html[:i] + new + "\n" + html[i:]



# ═══════════════════════════════════════════════════════════════════════
#  v107 · THE INDIA CURVE, AND A DAILY PULSE.
#
#  FBIL and CCIL publish exactly the daily par yield curve this needs and
#  both refuse automated access. So the India curve is ASSEMBLED, and every
#  point carries its own source and its own frequency on the tile — because
#  a curve drawn from four different update cadences and presented as one
#  live object would be the most elegant lie on the site.
#
#    overnight   RBI Money Market Operations press release   DAILY
#    1M / 3M     term MIBOR carried on the page              build-dated
#    1Y / 5Y     the OIS curve                               build-dated
#    10Y         FRED benchmark print, moved each day by the
#                long-gilt ETF                               level MONTHLY,
#                                                            direction DAILY
#
#  The regime classifier needs DIRECTION at each end, and direction is what
#  the daily pieces genuinely give.
# ═══════════════════════════════════════════════════════════════════════

#  labelled assumption, in the same class as the SDF/MSF corridor width:
#  modified duration of the long-gilt ETF, used only to convert its daily
#  price move into a yield move. Stated on the tile, never hidden.
GILT_ETF_DURATION = 7.5


def _mmo_from_text(txt):
    """{call, treps, repo, laf} from an RBI Money Market Operations release.
    Rates band 0-20%; the LAF number is in rupee crore in the release."""
    out = {}
    # v108: the release is a table — "I. Call Money | 13,301.83 | 5.09 |
    # 4.60-5.15" — volume first, weighted average rate second. Read that
    # shape first; the older sentence-styled patterns stay as fallbacks.
    pats = (("call", r"Call\s+Money\s+[\d,]+(?:\.\d+)?\s+"
                     r"(\d{1,2}\.\d{1,2})(?:\s|$)"),
            ("call", r"Call\s+Money\b.{0,300}?"
                     r"(?:Weighted\s+Average\s+Rate|WAR)\D{0,40}(\d{1,2}\.\d{1,2})"),
            ("call", r"Weighted\s+Average\s+Rate\D{0,40}(\d{1,2}\.\d{1,2})"),
            ("treps", r"Triparty\s+Repo\s+[\d,]+(?:\.\d+)?\s+"
                      r"(\d{1,2}\.\d{1,2})(?:\s|$)"),
            ("treps", r"Triparty\s+Repo\b.{0,300}?(\d{1,2}\.\d{1,2})"),
            ("repo", r"Market\s+Repo\s+[\d,]+(?:\.\d+)?\s+"
                     r"(\d{1,2}\.\d{1,2})(?:\s|$)"),
            ("repo", r"Market\s+Repo\b.{0,300}?(\d{1,2}\.\d{1,2})"))
    for key, pat in pats:
        if key in out:
            continue
        mm = _re.search(pat, txt, _re.I | _re.S)
        if not mm:
            continue
        try:
            v = float(mm.group(1))
        except Exception:
            continue
        if 0.0 < v <= 20.0:
            out[key] = v
    # v108: the real rows read "F. Net liquidity injected (outstanding
    # including today's operations) [injection (+)/absorption (-)]*
    # -3,19,400.34" — the sign legend sits between the label and the
    # figure, and a negative injection IS absorption. Page convention
    # stays: positive = absorbed (system surplus).
    lm = None
    for pat in (r"Net\s+liquidity\s+injected\s*\(outstanding[^)]*\)\s*"
                r"(?:\[[^\]]*\])?\s*\*?\s*(-?)\s*([\d,]+(?:\.\d+)?)",
                r"Net\s+liquidity\s+injected\s+from\s+today[\u2019']?s"
                r"\s+operations\s*(?:\[[^\]]*\])?\s*\*?\s*"
                r"(-?)\s*([\d,]+(?:\.\d+)?)"):
        lm = _re.search(pat, txt, _re.I)
        if lm:
            try:
                raw_v = float((lm.group(1) + lm.group(2)).replace(",", ""))
            except Exception:
                lm = None
                continue
            v = -raw_v / 1e5          # injected -> deficit -> negative
            if 0.005 <= abs(v) <= 30.0:
                out["laf_lakh_cr"] = round(v, 2)
            break
    if "laf_lakh_cr" not in out:
        lm = _re.search(r"Net\s+liquidity\s+(injected|absorbed)"
                        r"[^\d\-]{0,120}([\d,]{4,12})", txt, _re.I)
        if lm:
            try:
                v = float(lm.group(2).replace(",", "")) / 1e5
                if 0.005 <= v <= 30.0:
                    out["laf_lakh_cr"] = round(
                        v if lm.group(1).lower() == "absorbed" else -v, 2)
            except Exception:
                pass
    dm = _re.search(r"as\s+on\s+([A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4})", txt)
    if dm:
        out["date"] = dm.group(1)
    return out


def fetch_rbi_mmo():
    """RBI's daily money-market release, off the press index the reserves
    fetcher already walks. This is the one genuinely DAILY India macro read
    the terminal can rely on: where overnight money actually traded, and
    whether the system was in surplus or deficit."""
    for base in PRESS_INDEX:
        try:
            idx = _get(base, timeout=30)
        except Exception:
            continue
        prids = []
        for mm in _re.finditer(r"Money\s+Market\s+Operations", idx, _re.I):
            back = idx[max(0, mm.start() - 2500): mm.start()]
            pm = _re.findall(r"prid=(\d{3,7})", back)
            if pm:
                prids.append(int(pm[-1]))
        for pid in sorted(set(prids), reverse=True)[:3]:
            try:
                got = _mmo_from_text(_detag(_get(f"{base}?prid={pid}",
                                                 timeout=30)))
            except Exception:
                continue
            if got.get("call") is not None:
                print("  mmo: call "
                      + f"{got['call']}%"
                      + (f", TREPS {got['treps']}%" if got.get("treps") else "")
                      + (f", LAF {got['laf_lakh_cr']:+.2f} lakh cr"
                         if got.get("laf_lakh_cr") is not None else "")
                      + (f" — {got['date']}" if got.get("date") else "")
                      + f" (release {pid})")
                return got
    print("  mmo: no Money Market Operations release parsed — the daily "
          "pulse tiles keep their last read")
    return {}


def _page_px(page, name, field="p"):
    """One field off a baked price constant, e.g. the gilt ETF's 1-day move."""
    for var in ("IN_IDX", "IDX", "FX", "ENERGY", "PREC", "CRYPTO"):
        mm = _re.search(r"const " + var + r"=\{(.*?)\};", page, _re.S)
        if not mm:
            continue
        km = _re.search(r'"' + _re.escape(name) + r'":\{p:([\d.]+),'
                        r'd:(-?[\d.]+),m:(-?[\d.]+)', mm.group(1))
        if km:
            return {"p": float(km.group(1)), "d": float(km.group(2)),
                    "m": float(km.group(3))}.get(field)
    return None


def build_india_curve(page, mmo, fred10):
    """The assembled curve, each point tagged with source and frequency."""
    pts, meta = {}, {}

    def put(tenor, val, src, freq):
        if val is None:
            return
        pts[tenor] = round(float(val), 2)
        meta[tenor] = {"src": src, "freq": freq}

    on = (mmo or {}).get("call")
    if on is None:
        on = _page_ml(page, "mibor_on")
        put("ON", on, "MIBOR (page)", "build-dated")
    else:
        put("ON", on, "RBI money market ops", "daily")
    put("3M", _page_ml(page, "mibor_3m"), "term MIBOR", "build-dated")
    try:
        mm = _re.search(r"const OIS_CURVE\s*=\s*\[(.*?)\];", page, _re.S)
        if mm:
            for m_, r_ in _re.findall(
                    r"\{m:\s*([\d.]+)\s*,\s*r:\s*([\d.]+)\s*\}", mm.group(1)):
                lab = {"12": "1Y", "24": "2Y", "60": "5Y"}.get(
                    str(int(float(m_))) if float(m_) >= 1 else "")
                if lab:
                    put(lab, float(r_), "MIBOR-OIS curve", "build-dated")
    except Exception:
        pass

    # the 10-year: an official level, walked forward by the gilt ETF
    out = {"points": pts, "meta": meta}
    lvl = (fred10 or {}).get("v")
    if lvl is not None and (fred10 or {}).get("freq") == "daily":
        # v108: the anchor is already a daily official read (RBI home page,
        # secondary-market benchmark). No ETF walk needed, and the point is
        # tagged with the genuine cadence.
        put("10Y", lvl, (fred10 or {}).get("src", "RBI home"), "daily")
        out["ten_year"] = {"anchor": lvl,
                           "anchor_period": (fred10 or {}).get("period", ""),
                           "adj_pp": 0.0,
                           "note": "read daily off the RBI home page's "
                                   "Government Securities Market panel \u2014 "
                                   "no ETF walk needed",
                           "etf_1d": None, "etf_1m": None,
                           "duration_assumed": None}
    elif lvl is not None:
        d1 = _page_px(page, "India Gilt ETF", "d")
        m1 = _page_px(page, "India Gilt ETF", "m")
        adj, note = 0.0, ""
        if m1 is not None:
            # dP/P = -D * dy  =>  dy = -(dP/P)/D , in percentage points
            adj = -(m1 / 100.0) / GILT_ETF_DURATION * 100.0
            note = (f"level from the {(fred10 or {}).get('period', '')} "
                    f"benchmark print, walked forward by the long-gilt ETF's "
                    f"{m1:+.2f}% month (assumed {GILT_ETF_DURATION}y modified "
                    f"duration)")
        put("10Y", lvl + adj, "FRED print + gilt ETF", "level monthly, "
            "direction daily")
        out["ten_year"] = {"anchor": lvl,
                           "anchor_period": (fred10 or {}).get("period", ""),
                           "adj_pp": round(adj, 2), "note": note,
                           "etf_1d": d1, "etf_1m": m1,
                           "duration_assumed": GILT_ETF_DURATION}
    if "ON" in pts and "10Y" in pts:
        out["slope_on10"] = round(pts["10Y"] - pts["ON"], 2)
    if "1Y" in pts and "10Y" in pts:
        out["slope_1s10s"] = round(pts["10Y"] - pts["1Y"], 2)
    cpi = _page_ml(page, "cpi")
    if "10Y" in pts and cpi is not None:
        out["real10"] = round(pts["10Y"] - cpi, 2)
    if mmo:
        out["daily"] = {k: v for k, v in mmo.items() if k != "date"}
        if mmo.get("date"):
            out["daily_date"] = mmo["date"]
    return out


CURVE_PLAYBOOK = {
    "BULL STEEPENER": ("Easing being priced into a recovering economy — the "
                       "friendliest curve there is. Duration works and "
                       "cyclicals work at the same time; banks get a "
                       "widening lend-long borrow-short spread."),
    "BEAR STEEPENER": ("Growth and inflation expectations building at the "
                       "long end, or a term-premium and fiscal worry. "
                       "Cyclicals and commodity producers; long duration is "
                       "the thing that hurts."),
    "BULL FLATTENER": ("A growth scare and a flight to quality. Long "
                       "duration and defensives; cyclicals bleed even while "
                       "yields fall, which is what catches people out."),
    "BEAR FLATTENER": ("A central bank tightening into the cycle. Cash and "
                       "defensives; this is the state that precedes most "
                       "inversions, and rate-sensitives are the wrong place."),
    "FLAT / RANGE": ("Neither end has moved enough to call a direction. "
                     "Trade the names, not the curve."),
}


def classify_curve(d_short, d_long, eps=0.03):
    """Four states from two changes. Bull = yields falling. Steepener =
    the long-minus-short spread widening."""
    if d_short is None or d_long is None:
        return {}
    avg = (d_short + d_long) / 2.0
    slope = d_long - d_short
    if abs(avg) < eps and abs(slope) < eps:
        name = "FLAT / RANGE"
    else:
        name = ("BULL " if avg < 0 else "BEAR ") + \
               ("STEEPENER" if slope > 0 else "FLATTENER")
    return {"name": name, "d_short": round(d_short, 2),
            "d_long": round(d_long, 2), "slope_chg": round(slope, 2),
            "playbook": CURVE_PLAYBOOK.get(name, "")}


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

def _modal_bar(src):
    """The bar date most of the book shares, how many share it, and how many
    names sit behind it. One number for "what day is this page struck on"."""
    from collections import Counter
    bars = [v.get("b") for v in (src or {}).values() if v.get("b")]
    if not bars:
        return "", 0, 0
    bar, k = Counter(bars).most_common(1)[0]
    return bar, k, sum(1 for x in bars if x < bar)


def patch_price_src(html, src):
    """window.PRICE_SRC — for every quote, the tier that resolved it and the
    date of the bar it came from.

    Knowing 74 fields were rewritten tells you nothing if all 74 were rewritten
    with last Tuesday's close. The bar date tells you, per name. The tier tells
    you whether you are reading a market or reading yourself."""
    payload = {k: {"s": v.get("s", ""), "b": v.get("b", "")}
               for k, v in (src or {}).items() if v.get("s") or v.get("b")}
    blk = _re.search(r"window\.PRICE_SRC\s*=\s*(\{.*?\});", html, _re.S)
    if not payload:
        # nothing resolved this run: keep whatever provenance the page has
        # rather than blanking it, exactly as the reserves tab does
        print("  price src: nothing resolved this run — page keeps its "
              "previous provenance")
        return html
    new = ("window.PRICE_SRC = "
           + json.dumps(payload, separators=(",", ":"), sort_keys=True) + ";")
    if blk:
        html = html[:blk.start()] + new + html[blk.end():]
    else:
        i = html.find("window.PRICE_HEALTH")
        if i < 0:
            print("  price src: anchor missing (skipped)")
            return html
        html = html[:i] + new + "\n" + html[i:]
    bar, k, behind = _modal_bar(payload)
    tiers = sorted({v["s"] for v in payload.values() if v["s"]})
    print(f"  price src: {len(payload)} quotes tagged — {'/'.join(tiers)}"
          + (f", {k} struck on {bar}" if bar else "")
          + (f", {behind} on an older bar" if behind else ""))
    return html


def patch_price_health(html, patched, total, stamp, moved=None, src=None):
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
    bar, nbar, behind = _modal_bar(src)
    payload = {
        "n": patched, "total": total, "live": live,
        "asof": now if live else (prev.get("asof") or ""),
        "asof_epoch": (int(stamp.timestamp()) if live
                       else int(prev.get("asof_epoch") or 0)),
        "checked": now,
    }
    # v95: `n` counts fields written, `moved` counts fields whose value
    # changed. They are not the same claim and the page no longer conflates
    # them. `bar` is the day most of the book is struck on — the only field
    # here that survives a market being shut, and therefore the one to read.
    if moved is not None:
        payload["moved"] = moved
    if bar:
        payload["bar"] = bar
        payload["bar_n"] = nbar
        payload["bar_behind"] = behind
    elif prev.get("bar") and not live:
        payload["bar"] = prev["bar"]
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
        _mv = ("" if moved is None else
               f", {moved} changed value" +
               ("  <- nothing moved: either the market was shut or a feed "
                "served the same bar twice" if moved == 0 else ""))
        _bd = f", book struck {bar}" if bar else ""
        print(f"  price health: {patched}/{total} price fields "
              f"refreshed{_mv}{_bd}")
        if behind:
            print(f"  price health: {behind} name(s) on a bar older than "
                  f"{bar} — flagged red on their own tiles")
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
        "IN_IDX": {k: v for k, v in mkt.items() if k in ("Nifty 50", "BSE Sensex", "Bank Nifty", "Midcap 100", "BSE Midcap", "BSE Smallcap",
                                                       "India Gilt ETF")},
        "FX": {k: v for k, v in mkt.items() if k in ("USD/INR", "DXY", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD")},
        "ENERGY": {k: v for k, v in mkt.items() if k in ("Brent Oil", "WTI Oil", "Nat Gas")},
        "PREC": {k: v for k, v in mkt.items() if k in ("Gold", "Silver", "Platinum", "Palladium")},
        "IDX": {k: v for k, v in mkt.items() if k in ("S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000", "Nikkei 225")},
        "CRYPTO": {k: v for k, v in mkt.items() if k in ("Bitcoin", "Ethereum", "Solana")},
    }
    _obj_total = _obj_moved = 0
    for var, data in groups.items():
        html, n, mv = patch_obj(html, var, data)
        _obj_total += n
        _obj_moved += mv
        print(f"  patch {var}: {n} fields, {mv} moved")

    html, ns, ns_moved = patch_stocks(html, stk)
    print(f"  patch IN_STK: {ns} rows, {ns_moved} moved")

    html = patch_price_src(html, PRICE_SRC)

    # v92e: the page is told the truth about its own prices. Until now a run
    # that fetched nothing still stamped itself with the current time, which
    # is how four days of frozen commodities went unnoticed.
    html = patch_price_health(html, _obj_total + ns,
                              len(MARKET) + len(STOCKS), stamp,
                              moved=_obj_moved + ns_moved, src=PRICE_SRC)

    _page_pre = html   # v96: the page as served, for previous-print reads
    # --- macro releases (CPI/repo/reserves) from RBI portal, best-effort ---
    macro = fetch_macro(html)
    # v96: the ministry wire. CPI and IIP feed the same MACRO_LIVE path the
    # portal used to feed, so the trail, the provenance ledger and the
    # never-read list all update through the one honest door.
    try:
        _pib = fetch_pib_stats()
    except Exception as e:
        print(f"  pib stats: skipped ({type(e).__name__})")
        _pib = {}
    _ml_live = set(macro.get("_live") or [])
    if _pib.get("cpi") and "cpi" not in _ml_live:
        macro["cpi"] = _pib["cpi"]["v"]
        if _pib["cpi"].get("prev") is not None:
            macro["cpi_prev"] = _pib["cpi"]["prev"]
        if _pib["cpi"].get("month"):
            macro["cpi_month"] = _pib["cpi"]["month"][:3]
        _ml_live.add("cpi")
    if _pib.get("iip") and "iip" not in _ml_live:
        macro["iip"] = _pib["iip"]["v"]
        _ml_live.add("iip")
    macro["_live"] = sorted(_ml_live)
    # the regime is computed against the page as it stood BEFORE this pass
    # patches it, so "previous print" means the previous release, not the
    # one being written now
    _regime = classify_regime(_pib, html)
    html, nmac = patch_macro(html, macro, stamp)
    # v92: the extended macro blocks — RBI portal sweep + computed India series
    _g10 = {}
    try:
        _mx = dict(macro.get("_blocks") or {})
        _mx.update(fetch_india_extras())
        _mx = _merge_pib_mx(_mx, _pib, _page_pre)
        # v106: the banking aggregates out of the WSS, and the bond anchor
        try:
            for _k, _v in (fetch_wss_banking() or {}).items():
                _mx[_k] = {"v": _v, "pct": True, "unit": "yoy · RBI WSS"}
        except Exception as _e:
            print(f"  wss banking: skipped ({type(_e).__name__})")
        try:
            _g10 = fetch_gsec10_rbi() or fetch_gsec10()
            if _g10.get("v") is not None:
                _mx["gsec10"] = {"v": _g10["v"], "pct": True,
                                 "prev": _g10.get("prev"),
                                 "period": _g10.get("period", ""),
                                 "unit": _g10.get("src", "")}
        except Exception as _e:
            print(f"  gsec10: skipped ({type(_e).__name__})")
        html = patch_macro_x(html, _mx, stamp)
    except Exception as e:
        print(f"  macro blocks: skipped ({type(e).__name__}) — page keeps "
              f"its previous MACRO_X")
    html = patch_reserves(html, macro)
    html = patch_regime(html, _regime, stamp)
    try:
        html = patch_sector_infl(html,
                                 build_sector_infl(_pib, _page_pre), stamp)
    except Exception as e:
        print(f"  sector infl: skipped ({type(e).__name__})")
    try:
        html = patch_gold_inr(html, fetch_ibja(), stamp)
    except Exception as e:
        print(f"  ibja: skipped ({type(e).__name__})")
    try:
        html = patch_fno(html, fetch_fno(), stamp)
    except Exception as e:
        print(f"  fno: skipped ({type(e).__name__})")
    try:
        html = patch_movers(html, fetch_movers(), stamp)
    except Exception as e:
        print(f"  movers: skipped ({type(e).__name__})")
    _curv = {}
    try:
        _curv = fetch_curves(_page_pre, _g10)
        html = patch_curves(html, _curv, stamp)
    except Exception as e:
        print(f"  curves: skipped ({type(e).__name__})")
    try:
        _g10v = ((_curv.get("india") or {}).get("10y")
                 or _page_mx(_page_pre, "gsec10", "v"))
        html = patch_valuation(html, fetch_index_valuation(), _g10v, stamp)
    except Exception as e:
        print(f"  valuation: skipped ({type(e).__name__})")
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
                  (", ".join(_mlive) + " read live (RBI + ministry wire)")
                  if _mlive
                  else "no headline macro field could be read live"),
        "macro blocks": (bool(macro.get("_blocks")),
                         f"{len(macro.get('_blocks') or {})} of "
                         f"{len(RBI_EXTRA)} extended blocks carried"),
        "ministry wire": (bool(_pib), _pib_log_msg(_pib)),
        "regime": (bool(_regime.get("quad")), _regime_log_msg(_regime, html)),
        "reserves": (bool(macro.get("reserves_bn")),
                     f"${macro['reserves_bn']}bn read" if macro.get("reserves_bn")
                     else "no weekly figure survived the plausibility guard "
                          "\u2014 last good value carried forward"),
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
        "Gold": "Gold", "Silver": "Silver", "Brent": "Brent Oil",
        "WTI": "WTI Oil", "USDINR": "USD/INR", "BTC": "Bitcoin", "VIX": "VIX",
    }
    for spark, src in spark_src.items():
        if src in mkt:
            html = patch_spark(html, spark, mkt[src][0])

    # Stamp the header timestamp. The year is NOT pinned: it was written as
    # a literal 2026, which would have stopped matching on 1 January and left
    # the header frozen at a stale date under a badge that says LIVE.
    html = re.sub(
        r"Data: [A-Za-z]{3} [A-Za-z]{3} \d+, \d{4}[^<·]*· Models:",
        f"Data: {stamp:%a %b %d, %Y %H:%M} IST (auto) · Models:",
        html, count=1,
    )

    # And the build tag, which was static HTML reading v92 while this file was
    # already v93 — a page that understates its own version reads as a page
    # that failed to deploy.
    html = re.sub(
        r'(<span id="build-version"[^>]*>)[^<]*(</span>)',
        lambda mm: mm.group(1) + BUILD + mm.group(2),
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
