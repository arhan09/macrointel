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

try:
    import yfinance as yf
except ImportError:
    sys.exit("ERROR: pip install yfinance")

# ── Yahoo Finance ticker map ────────────────────────────────────────────────
MARKET = {
    # India indices
    "Nifty 50": "^NSEI", "BSE Sensex": "^BSESN", "Bank Nifty": "^NSEBANK",
    "Midcap 100": "^NSEMDCP100",
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
    "Cipla": "CIPLA.NS", "Dr Reddys": "DRREDDY.NS", "JSW Steel": "JSWSTEEL.NS",
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


def main(path):
    stamp = dt.datetime.now()
    print(f"=== Terminal updater · {stamp:%Y-%m-%d %H:%M} ===")
    print("Fetching market data ...")
    mkt = fetch(MARKET)
    print(f"  market: {len(mkt)}/{len(MARKET)} OK")
    print("Fetching stocks ...")
    stk = fetch(STOCKS)
    print(f"  stocks: {len(stk)}/{len(STOCKS)} OK")

    html = open(path, encoding="utf-8").read()

    groups = {
        "IN_IDX": {k: v for k, v in mkt.items() if k in ("Nifty 50", "BSE Sensex", "Bank Nifty", "Midcap 100")},
        "FX": {k: v for k, v in mkt.items() if k in ("USD/INR", "DXY", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD")},
        "ENERGY": {k: v for k, v in mkt.items() if k in ("Brent Oil", "WTI Oil", "Nat Gas")},
        "PREC": {k: v for k, v in mkt.items() if k in ("Gold", "Silver", "Platinum", "Palladium")},
        "IDX": {k: v for k, v in mkt.items() if k in ("S&P 500", "Nasdaq 100", "Dow Jones", "Russell 2000", "Nikkei 225")},
        "CRYPTO": {k: v for k, v in mkt.items() if k in ("Bitcoin", "Ethereum", "Solana")},
    }
    for var, data in groups.items():
        html, n = patch_obj(html, var, data)
        print(f"  patch {var}: {n} fields")

    html, ns = patch_stocks(html, stk)
    print(f"  patch IN_STK: {ns} rows")

    html, nm = patch_lookup_macro(html, mkt)
    print(f"  patch Lookup-macro: {nm} instruments")

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
        f"Data: {stamp:%a %b %d, %Y %H:%M} (auto) · Models:",
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
