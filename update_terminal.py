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
    """Return {name: (last, day_pct, month_pct)} from ~2 months of history."""
    out = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="2mo")["Close"].dropna()
            if len(hist) < 2:
                continue
            last = float(hist.iloc[-1])
            prev = float(hist.iloc[-2])
            mago = float(hist.iloc[-22]) if len(hist) >= 22 else float(hist.iloc[0])
            out[name] = (
                round(last, 2),
                round((last / prev - 1) * 100, 2),
                round((last / mago - 1) * 100, 2),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {name} ({sym}): {exc}")
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




def patch_lookup_macro(html, mkt):
    """Refresh the 'cur' value of the Lookup-tab macro instruments (USD/INR, etc.)
    so their curves stay anchored to live values. History is from the data pack;
    only the latest point updates here."""
    macro_map = {
        "USD/INR (rupee)": mkt.get("USD/INR"),
    }
    n = 0
    for name, val in macro_map.items():
        if not val:
            continue
        cur = val[0]
        pat = r'(' + re.escape('"' + name + '":{"cat":"macro"') + r'.*?"cur":)[\d.]+'
        new, c = re.subn(pat, lambda m: m.group(1) + str(cur), html)
        if c:
            html = new
            n += 1
    return html, n



def compute_india_prices(mkt):
    """Derive India-specific MCX prices from Yahoo USD spot × INR.
    Yahoo has no MCX feed, so we compute ₹ prices the same way the in-browser
    model does. Returns a dict of {label: value}."""
    OZ = 31.1035
    def g(k):  # safe getter -> price float or None
        v = mkt.get(k)
        return v[0] if v else None
    inr   = g("USD/INR")
    gold  = g("Gold")      # USD/oz (GC=F)
    silver= g("Silver")    # USD/oz (SI=F)
    brent = g("Brent Oil") # USD/bbl (BZ=F)
    out = {}
    if inr and gold:
        out["mcx_gold_10g"]  = round(gold/OZ*inr*10*1.162)     # ₹/10g (calibrated to MCX retail+duty)
        out["mcx_gold_g"]    = round(gold/OZ*inr*1.162)        # ₹/g 24K
        out["gold_usd_oz"]   = round(gold)
    if inr and silver:
        out["mcx_silver_kg"] = round(silver/OZ*inr*1000*1.246) # ₹/kg
        out["silver_usd_oz"] = round(silver, 1)
    if inr and brent:
        out["mcx_crude_bbl"] = round(brent*inr*0.901)          # ₹/bbl
        out["brent_usd"]     = round(brent, 1)
    if inr:
        out["inr"] = round(inr, 2)
    return out


def patch_india_comm(html, mkt):
    """Patch the India Comm tab + commodity-positioning MCX prices from computed
    India prices. Uses anchored replacements so only the right numbers change."""
    p = compute_india_prices(mkt)
    if not p:
        return html, 0
    n = 0
    def fmt(x):
        return f"{x:,}"  # Indian-style grouping is close enough with comma for these magnitudes

    subs = []
    # Robust: read whatever value is currently baked in, replace ALL its occurrences globally.
    def _swap_all(h, old_val, new_val):
        # old_val/new_val like "₹1,43,670" — replace every occurrence, count them
        if old_val and old_val != new_val and old_val in h:
            return h.replace(old_val, new_val), h.count(old_val)
        return h, 0

    total = 0
    if "mcx_gold_10g" in p:
        new_g = "\u20b9{:,}".format(p["mcx_gold_10g"])
        import re as _r
        for cur in set(_r.findall(r"\u20b91,[2-7][0-9],[0-9]{3}", html)):
            if cur != new_g:
                html, c = _swap_all(html, cur, new_g); total += c
    if "mcx_gold_g" in p:
        cur = re.search(r"\u20b9\d2,\d{3}(?=/g\b)", html)
        if cur:
            html, c = _swap_all(html, cur.group(0), f"\u20b9{p['mcx_gold_g']:,}")
            total += c
    if "mcx_silver_kg" in p:
        cur = re.search(r"\u20b9\d,\d2,\d{3}(?=/kg)", html)
        if cur:
            html, c = _swap_all(html, cur.group(0), f"\u20b9{p['mcx_silver_kg']:,}")
            total += c
    if "mcx_crude_bbl" in p:
        cur = re.search(r"\u20b9\d,\d{3}(?=/bbl)", html)
        if cur:
            html, c = _swap_all(html, cur.group(0), f"\u20b9{p['mcx_crude_bbl']:,}")
            total += c
    if "gold_usd_oz" in p:
        html, c = _swap_all(html, "$4,073", f"${p['gold_usd_oz']:,}"); total += c
    n = total
    print(f"  patch India-Comm MCX: {total} values (gold {p.get('mcx_gold_10g')}, silver {p.get('mcx_silver_kg')}, crude {p.get('mcx_crude_bbl')})")
    return html, n

def _unused_old_patch(html, p):
    subs = []



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


def write_history_json(stamp):
    """v84: publish a compact same-origin 1-year daily-close history for every
    symbol the page's client features need (search/verdict/rotation/charts).
    Browsers cannot call Yahoo directly (CORS), so the site serves its own
    data. Fully fail-safe: any error leaves the previous file in place."""
    try:
        syms = sorted(set(MARKET.values()) | set(STOCKS.values()) |
                      {"LTGILTBEES.NS", "GILT5YBEES.NS", "GOLDBEES.NS",
                       "SILVERBEES.NS", "^MOVE", "^TNX", "EEM"})
        df = yf.download(syms, period="1y", interval="1d",
                         auto_adjust=True, progress=False, threads=True)
        close = df["Close"] if hasattr(df.columns, "levels") else df[["Close"]]
        close = close.dropna(how="all")
        if len(close) < 60:
            print("  history: too few rows — kept previous file")
            return
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
        with open("history_1y.json", "w") as f:
            json.dump(out, f, separators=(",", ":"))
        print(f"  history: history_1y.json written ({len(series)} series × "
              f"{len(dates)} days)")
    except Exception as e:
        print(f"  history: failed ({type(e).__name__}) — kept previous file")


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
    Picks one direct-growth scheme per category by name pattern."""
    try:
        raw = _get("https://portal.amfiindia.com/spages/NAVAll.txt", timeout=60)
    except Exception as e:
        print(f"  amfi: unavailable ({type(e).__name__}) — keeping last NAVs")
        return {}
    out = {}
    for line in raw.splitlines():
        parts = line.split(";")
        if len(parts) < 6:
            continue
        name = parts[3].strip()
        low = name.lower()
        if "direct" not in low or "growth" not in low or "idcw" in low:
            continue
        for cat, pats in MF_PATTERNS.items():
            if cat in out:
                continue
            if any(p in low for p in pats):
                try:
                    out[cat] = {"name": name, "nav": round(float(parts[4]), 4),
                                "date": parts[5].strip()}
                except Exception:
                    pass
    print(f"  amfi: {len(out)}/{len(MF_PATTERNS)} categories matched")
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
        f"patched {counts.get('obj',0)} price fields, {counts.get('stocks',0)} stocks, {counts.get('incomm',0)} MCX values, {counts.get('macro',0)} macro values.</div>"
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



def patch_trade_desk_stocks(html, mkt):
    """Patch the Trade Desk STOCKS array prices/changes from the Yahoo pull, so
    the Trade Desk cards auto-update alongside IN_STK. Anchored per stock name."""
    # map Trade Desk display names -> the MARKET dict keys (same Yahoo data)
    name_map = {
        "ICICI Bank":"ICICI Bank", "HDFC Bank":"HDFC Bank", "L&T":"L&T",
        "Sun Pharma":"Sun Pharma", "Maruti":"Maruti", "M&M":"M&M",
        "Bharti Airtel":"Airtel", "Coal India":"Coal India", "Titan":"Titan",
        "ITC":"ITC", "Axis Bank":"Axis Bank", "Infosys":"Infosys",
        "Persistent":"Persistent", "Tata Steel":"Tata Steel",
    }
    n = 0
    for disp, mkey in name_map.items():
        v = mkt.get(mkey)          # 'mkt' here receives the stocks dict (called with stk)
        if not v:
            continue
        price, dpct = v[0], v[1]   # fetch returns (last, day%, month%) — take first two
        # patch price: {name:"ICICI Bank",price:1402.0,d1:2.72,...
        pat = r'(\{name:"' + re.escape(disp) + r'",price:)[\d.]+(,d1:)[-\d.]+'
        rep = rf'\g<1>{round(price,1)}\g<2>{round(dpct,2)}'
        html, c = re.subn(pat, rep, html)
        n += c
    print(f"  patch Trade-Desk stocks: {n} updated")
    return html, n


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
    write_history_json(stamp)   # same-origin data for the browser (CORS fix)

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
    html, ntd = patch_trade_desk_stocks(html, stk)
    print(f"  patch IN_STK: {ns} rows")

    html, nm = patch_lookup_macro(html, mkt)
    print(f"  patch Lookup-macro: {nm} instruments")

    html, nic = patch_india_comm(html, mkt)

    # --- macro releases (CPI/repo/reserves) from RBI portal, best-effort ---
    macro = fetch_macro()
    html, nmac = patch_macro(html, macro)
    html = patch_reserves(html, macro)
    html = patch_mf(html, fetch_amfi())
    html = patch_flows(html, fetch_flows())

    counts = {"obj": _obj_total, "stocks": ns, "incomm": nic, "macro": nmac}
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
