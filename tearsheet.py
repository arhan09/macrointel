#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 MACROINTEL · INDIA DAILY TEAR SHEET GENERATOR
================================================================================
Bloomberg-style daily tear sheet for India, in the "Market Macro Hub" visual
language: dark landscape pages, dashboard tables with LEVEL / CHANGE / CONTEXT,
"what's stretched" callouts, and 2x2 chart grids per instrument.

SECTIONS
  1. India Equities   — Nifty / Sensex / Bank Nifty / Midcap / sectors / India VIX
  2. Nifty Heavyweights — Mag7-style cross-sectional dashboard (9 largest names)
  3. FX · INR Complex — USD/INR, EUR/INR, GBP/INR, JPY/INR, DXY, majors
  4. Commodities      — Brent, WTI, Gold, Silver, Copper, NatGas + Gold in INR
  5. Crypto           — BTC, ETH, ETH/BTC + macro cross-correlations

OUTPUTS (written to --outdir, default ".")
  tearsheet.pdf                  — the full multi-page tear sheet
  tearsheet.html                 — self-contained browsable version (PNG pages)
  tearsheets/tearsheet_YYYYMMDD.pdf — dated archive copy

USAGE
  pip install yfinance pandas numpy matplotlib
  python tearsheet.py                  # live data from Yahoo Finance
  python tearsheet.py --demo           # synthetic data (offline layout test)
  python tearsheet.py --data dump.json # inject pre-fetched data
                                       # {"TICKER": {"ts":[unix..], "close":[..]}}

All computations use daily closes. RV = annualised stdev of log returns.
Educational information, not investment advice.
================================================================================
"""

import argparse
import base64
import datetime as dt
import io
import json
import math
import os
import sys

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages

# ── palette ─────────────────────────────────────────────────────────────────
BG      = "#0b1110"
CARD    = "#0e1614"
LINE    = "#1c2926"
TXT     = "#e8eeec"
DIM     = "#8aa09a"
TEAL    = "#2fd6ad"
GREEN   = "#25c866"
RED     = "#f04444"
ORANGE  = "#f5a623"
BLUE    = "#7c9cf5"
PURPLE  = "#a78bfa"
PINK    = "#f472b6"
YELLOW  = "#e5c545"
CYAN    = "#4dd0e1"
SERIES_COLORS = [TEAL, ORANGE, BLUE, GREEN, PURPLE, PINK, CYAN, YELLOW, RED]

BRAND      = "MACROINTEL"
BRAND_LONG = "MACROINTEL TERMINAL"
SITE       = "macrointel.in"
PAGE_W, PAGE_H = 11.0, 8.5
DPI_PDF, DPI_PNG = 150, 110

MONO = "DejaVu Sans Mono"
SANS = "DejaVu Sans"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": LINE, "axes.labelcolor": DIM, "text.color": TXT,
    "xtick.color": DIM, "ytick.color": DIM, "font.family": SANS,
    "axes.grid": True, "grid.color": "#ffffff", "grid.alpha": 0.06,
    "grid.linewidth": 0.6, "axes.axisbelow": True,
})

# ── universe ────────────────────────────────────────────────────────────────
TICKERS = {
    # India indices
    "Nifty 50": "^NSEI", "Sensex": "^BSESN", "Bank Nifty": "^NSEBANK",
    "Midcap 100": "NIFTY_MIDCAP_100.NS", "India VIX": "^INDIAVIX",
    "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA",
    "Nifty FMCG": "^CNXFMCG", "Nifty Metal": "^CNXMETAL",
    "Nifty Energy": "^CNXENERGY", "Nifty Realty": "^CNXREALTY",
    # heavyweights
    "RELIANCE": "RELIANCE.NS", "HDFCBANK": "HDFCBANK.NS", "TCS": "TCS.NS",
    "ICICIBANK": "ICICIBANK.NS", "INFY": "INFY.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "LT": "LT.NS", "SBIN": "SBIN.NS", "ITC": "ITC.NS",
    # FX
    "USD-INR": "INR=X", "EUR-INR": "EURINR=X", "GBP-INR": "GBPINR=X",
    "JPY-INR": "JPYINR=X", "DXY": "DX-Y.NYB", "EUR-USD": "EURUSD=X",
    "USD-JPY": "JPY=X",
    # commodities
    "Brent": "BZ=F", "WTI": "CL=F", "Gold": "GC=F", "Silver": "SI=F",
    "Copper": "HG=F", "Nat Gas": "NG=F",
    # global context (crypto removed per v80 scope)
    "S&P 500": "^GSPC", "EEM": "EEM", "US 10Y": "^TNX",
    # rates complex (gilt ETFs = daily duration proxies; MOVE = rates vol)
    "Gilt 5Y ETF": "GILT5YBEES.NS", "Gilt LT ETF": "LTGILTBEES.NS",
    "MOVE": "^MOVE",
}

# FRED series pulled via the keyless fredgraph.csv endpoint (works in CI;
# no API key needed). All daily unless noted.
FRED_SERIES = {
    "US 2Y": "DGS2", "US 5Y": "DGS5", "US 10Y FRED": "DGS10",
    "US 30Y": "DGS30",
    "BE 5Y": "T5YIE", "BE 10Y": "T10YIE", "BE 5Y5Y": "T5YIFR",
    "Real 5Y": "DFII5", "Real 10Y": "DFII10",
    "EFFR": "EFFR", "SOFR": "SOFR",
    "India 10Y (monthly)": "INDIRLTLT01STM",   # OECD, monthly
}

HEAVY = ["RELIANCE", "HDFCBANK", "TCS", "ICICIBANK", "INFY",
         "BHARTIARTL", "LT", "SBIN", "ITC"]

# ── data layer ──────────────────────────────────────────────────────────────

def fetch_live() -> dict:
    import yfinance as yf
    out, symbols = {}, list(TICKERS.values())
    df = yf.download(symbols, period="10y", interval="1d",
                     auto_adjust=True, progress=False, threads=True)
    close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]]
    for name, sym in TICKERS.items():
        if sym in close.columns:
            s = close[sym].dropna()
            if len(s) > 30:
                out[name] = s
    missing = [n for n in TICKERS if n not in out]
    if missing:
        print(f"WARN: no data for {missing}", file=sys.stderr)
    return out


def load_json(path: str) -> dict:
    with open(path) as f:
        raw = json.load(f)
    sym2name = {v: k for k, v in TICKERS.items()}
    out = {}
    for key, obj in raw.items():
        name = sym2name.get(key, key if key in TICKERS else None)
        if name is None:
            continue
        idx = pd.to_datetime(pd.Series(obj["ts"]), unit="s").dt.normalize()
        s = pd.Series(obj["close"], index=idx, dtype=float).dropna()
        s = s[~s.index.duplicated(keep="last")]
        if len(s) > 30:
            out[name] = s
    return out


def fetch_fred() -> dict:
    """Daily US rates complex + India 10Y monthly from FRED (keyless CSV)."""
    import urllib.request
    out = {}
    for name, sid in FRED_SERIES.items():
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            req = urllib.request.Request(url, headers={"User-Agent":
                                                       "MacroIntel/1.0"})
            raw = urllib.request.urlopen(req, timeout=30).read().decode()
            df = pd.read_csv(io.StringIO(raw))
            df.columns = ["date", "v"]
            s = pd.Series(pd.to_numeric(df["v"], errors="coerce").values,
                          index=pd.to_datetime(df["date"])).dropna()
            if len(s) > 24:
                out[name] = s
        except Exception as e:
            print(f"WARN fred {sid}: {type(e).__name__}", file=sys.stderr)
    return out


def demo_fred() -> dict:
    """Synthetic FRED stand-ins for offline layout tests."""
    out = {}
    lv = {"US 2Y": 4.2, "US 5Y": 4.3, "US 10Y FRED": 4.6, "US 30Y": 5.1,
          "BE 5Y": 2.4, "BE 10Y": 2.3, "BE 5Y5Y": 2.3, "Real 5Y": 1.8,
          "Real 10Y": 2.1, "EFFR": 3.6, "SOFR": 3.6}
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=2520)
    for name, base in lv.items():
        rs = np.random.RandomState(abs(hash("F" + name)) % (2**31))
        s = pd.Series(base + np.cumsum(rs.normal(0, .012, len(idx))),
                      index=idx).clip(0.05)
        out[name] = s
    rs = np.random.RandomState(11)
    midx = pd.date_range(end=pd.Timestamp.today().normalize(),
                         periods=200, freq="MS")
    out["India 10Y (monthly)"] = pd.Series(
        7.0 + np.cumsum(rs.normal(0, .08, len(midx))),
        index=midx).clip(5, 9.5)
    return out


def parse_terminal_anchors(path="macro_intelligence_terminal.html") -> dict:
    """India rates the free feeds don't carry, read from the terminal's own
    machine-patched MACRO_LIVE block (RBI-portal scrape) + data-live spans.
    Single source of truth: this runs right after update_terminal.py."""
    A = {}
    try:
        import re as _re
        h = open(path, encoding="utf-8").read()
        m = _re.search(r"window\.MACRO_LIVE = \{ ([^;]*)\};", h)
        if m:
            for k, v in _re.findall(r"(\w+):\s*([\d.]+)", m.group(1)):
                A[k] = float(v)
        m2 = _re.search(r'10Y <span data-live=""[^>]*>([\d.]+)</span>', h)
        if m2:
            A["in10y"] = float(m2.group(1))
        mo = _re.search(r"const OIS_CURVE = \[(.*?)\];", h, _re.DOTALL)
        if mo:
            A["ois"] = [(float(m_), float(r_)) for m_, r_ in
                        _re.findall(r"\{m:([\d.]+),\s*r:([\d.]+)\}",
                                    mo.group(1))]
    except Exception as e:
        print(f"WARN anchors: {type(e).__name__}", file=sys.stderr)
    # optional override: ois_manual.json in repo root — lets Gautam refresh the
    # OIS curve (CCIL daily bulletin values) without touching the terminal.
    # Format: {"curve": [{"m": 1, "r": 5.82}, ...], "asof": "YYYY-MM-DD"}
    try:
        if os.path.exists("ois_manual.json"):
            j = json.load(open("ois_manual.json"))
            if j.get("curve"):
                A["ois"] = [(float(x["m"]), float(x["r"]))
                            for x in j["curve"]]
                A["ois_asof"] = j.get("asof", "")
    except Exception as e:
        print(f"WARN ois_manual.json: {type(e).__name__}", file=sys.stderr)
    return A


def ois_points(A):
    """Convenience: dict tenor-months -> rate from the parsed OIS curve."""
    return {m: r for m, r in A.get("ois", [])}


def demo_data() -> dict:
    """Deterministic synthetic walks so layout can be tested offline."""
    rng_end = pd.Timestamp.today().normalize()
    idx = pd.bdate_range(end=rng_end, periods=2520)
    seeds = {n: abs(hash(n)) % (2**31) for n in TICKERS}
    starts = {"Nifty 50": 8000, "Sensex": 27000, "Bank Nifty": 17000,
              "Midcap 100": 13000, "India VIX": 16, "USD-INR": 64, "DXY": 96,
              "Brent": 50, "WTI": 46, "Gold": 1200, "Silver": 16,
              "Bitcoin": 600, "Ethereum": 12, "S&P 500": 2000, "US 10Y": 2.2}
    out = {}
    for name in TICKERS:
        rs = np.random.RandomState(seeds[name])
        drift = 0.0004 if name != "India VIX" else 0.0
        vol = 0.010 + (rs.rand() * 0.012)
        r = rs.normal(drift, vol, len(idx))
        s = pd.Series(starts.get(name, 100 + rs.rand() * 900) *
                      np.exp(np.cumsum(r)), index=idx)
        if name in ("India VIX",):
            s = 12 + 18 * (s / s.mean() - 0.6).clip(0, None)
        out[name] = s
    return out


# ── derived series ──────────────────────────────────────────────────────────

def add_derived(D: dict) -> dict:
    if "Gold" in D and "USD-INR" in D:
        g = (D["Gold"] * D["USD-INR"].reindex(D["Gold"].index).ffill()).dropna()
        D["Gold (INR)"] = g / 31.1035 * 10  # per 10 g
    if "Ethereum" in D and "Bitcoin" in D:
        D["ETH/BTC"] = (D["Ethereum"] /
                        D["Bitcoin"].reindex(D["Ethereum"].index).ffill()).dropna()
    return D


def logret(s): return np.log(s / s.shift(1))


def rv(s, w):
    return logret(s).rolling(w).std() * math.sqrt(252) * 100


def pct(s, n=1):
    return (s / s.shift(n) - 1) * 100


def ytd(s):
    yr_start = s[s.index.year < s.index[-1].year]
    if len(yr_start) == 0:
        return np.nan
    return (s.iloc[-1] / yr_start.iloc[-1] - 1) * 100


def five_d_z(s):
    r5 = pct(s, 5).dropna()
    if len(r5) < 100:
        return np.nan
    hist = r5.tail(756)
    sd = hist.std()
    return (r5.iloc[-1] - hist.mean()) / sd if sd > 0 else np.nan


def pctile_1y(s):
    w = s.tail(252)
    if len(w) < 60:
        return np.nan
    return float((w <= w.iloc[-1]).mean() * 100)


def stale_days(s):
    return max(0, np.busday_count(s.index[-1].date(), dt.date.today()))


def mom_z(s, w=20):
    r = pct(s, w) / 100
    v = logret(s).rolling(w).std() * math.sqrt(w)
    return (r / v).replace([np.inf, -np.inf], np.nan)


def beta(a, b, w=63):
    ra, rb = logret(a), logret(b).reindex(a.index)
    cov = ra.rolling(w).cov(rb)
    var = rb.rolling(w).var()
    return cov / var


def roll_corr(a, b, w=30):
    ra = logret(a)
    rb = logret(b).reindex(a.index)
    return ra.rolling(w).corr(rb)


def drawdown(s):
    return (s / s.cummax() - 1) * 100


# ── page scaffolding ────────────────────────────────────────────────────────

class Book:
    def __init__(self, asof: str, demo=False):
        self.figs, self.codes, self.titles = [], [], []
        self.asof = asof
        self.demo = demo

    def new_page(self, section, code, title=None, keys=""):
        fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        self.figs.append(fig)
        self.codes.append((section, code))
        self.titles.append((title or "Dashboard · what's stretched", keys))
        # header
        fig.text(0.032, 0.955, "■", color=TEAL, fontsize=11, family=SANS)
        fig.text(0.052, 0.952, section, color=TXT, fontsize=13.5,
                 family=SANS, fontweight="bold")
        fig.text(0.052 + 0.0128 * len(section), 0.9535,
                 f"   Pricing as of {self.asof}", color=DIM, fontsize=7.5,
                 style="italic", family=SANS)
        fig.text(0.968, 0.952, BRAND_LONG, color=TEAL, fontsize=8.5,
                 family=SANS, fontweight="bold", ha="right")
        fig.lines.append(plt.Line2D([0.03, 0.97], [0.938, 0.938],
                                    transform=fig.transFigure,
                                    color=TEAL, lw=1.2, alpha=0.9))
        # watermark
        wm = f"{BRAND} · {self.asof}" + ("  · DEMO DATA" if self.demo else "")
        for x in (0.16, 0.5, 0.84):
            for y in (0.18, 0.5, 0.82):
                fig.text(x, y, wm, color=TXT, alpha=0.035, fontsize=13,
                         rotation=22, ha="center", va="center", family=MONO)
        # footer
        fig.text(0.032, 0.028,
                 f"{SITE} · india daily tear sheet · © {self.asof[-4:]} {BRAND} · "
                 "educational information · not investment advice",
                 color=DIM, fontsize=6.5, family=MONO)
        return fig

    def finish_footers(self):
        for i, (fig, (sec, code)) in enumerate(zip(self.figs, self.codes)):
            fig.text(0.968, 0.028, f"{code} · {i + 1} / {len(self.figs)}",
                     color=DIM, fontsize=6.5, family=MONO, ha="right")


def style_ax(ax, right=True):
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(labelsize=6, length=0)
    if right:
        ax.yaxis.tick_right()
    return ax


def date_axis(ax, s):
    span = (s.index[-1] - s.index[0]).days
    if span > 2400:
        loc = mdates.MonthLocator(interval=9)
    elif span > 1000:
        loc = mdates.MonthLocator(interval=4)
    elif span > 400:
        loc = mdates.MonthLocator(interval=2)
    else:
        loc = mdates.MonthLocator(interval=1)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%y"))
    for lb in ax.get_xticklabels():
        lb.set_rotation(90)
        lb.set_fontsize(5.6)


def panel_title(ax, txt):
    ax.set_title(txt, fontsize=8.5, color=TXT, fontweight="bold", pad=6)


def legend(ax, handles_labels, ncol=None, dy=-0.26):
    hs, ls = handles_labels
    ax.legend(hs, ls, loc="upper center", bbox_to_anchor=(0.5, dy),
              ncol=ncol or len(ls), frameon=False, fontsize=6,
              labelcolor=DIM, handlelength=1.4)


# ── chart primitives ────────────────────────────────────────────────────────

def spot_panel(ax, s, label, color=TEAL, fill=True):
    ax.plot(s.index, s.values, color=color, lw=0.8)
    if fill:
        ax.fill_between(s.index, s.values, s.min(), color=color, alpha=0.12)
    style_ax(ax)
    date_axis(ax, s)
    legend(ax, ([plt.Line2D([], [], color=color, lw=2)], [label]))


def roc_panel(ax, s, label, n=5, days=252):
    r = pct(s, n).tail(days).dropna()
    px = s.reindex(r.index)
    colors = [GREEN if v >= 0 else RED for v in r.values]
    ax.bar(r.index, r.values, color=colors, width=1.0)
    style_ax(ax, right=False)
    ax.yaxis.tick_left()
    ax2 = ax.twinx()
    ax2.plot(px.index, px.values, color=ORANGE, lw=0.8)
    style_ax(ax2)
    ax2.grid(False)
    date_axis(ax, r)
    legend(ax, ([plt.Line2D([], [], color=GREEN, lw=3),
                 plt.Line2D([], [], color=ORANGE, lw=2)],
                [f"{n}d %", label]))


def rv_panel(ax, s, label):
    r30, r100 = rv(s, 30).dropna(), rv(s, 100).dropna()
    ax.plot(r30.index, r30.values, color=ORANGE, lw=0.7)
    ax.plot(r100.index, r100.values, color=BLUE, lw=0.9)
    style_ax(ax)
    ax.set_ylabel("ann. vol %", fontsize=6, color=DIM)
    date_axis(ax, r30)
    legend(ax, ([plt.Line2D([], [], color=ORANGE, lw=2),
                 plt.Line2D([], [], color=BLUE, lw=2)],
                ["RV 30d", "RV 100d"]))


def impulse_panel(ax, s, label="RV30-RV100"):
    d = (rv(s, 30) - rv(s, 100)).dropna()
    ax.fill_between(d.index, d.values, 0, where=d.values >= 0,
                    color=ORANGE, alpha=0.85)
    ax.fill_between(d.index, d.values, 0, where=d.values < 0,
                    color="#b0413e", alpha=0.85)
    style_ax(ax)
    date_axis(ax, d)
    legend(ax, ([plt.Line2D([], [], color=ORANGE, lw=2)], [label]))


def dd_panel(ax, s, label="drawdown"):
    d = drawdown(s)
    ax.fill_between(d.index, d.values, 0, color=RED, alpha=0.75)
    style_ax(ax)
    ax.set_ylabel("%", fontsize=6, color=DIM)
    date_axis(ax, d)
    legend(ax, ([plt.Line2D([], [], color=RED, lw=2)], [label]))


def corr_panel(ax, a, b, title, w=30):
    c = roll_corr(a, b, w).dropna().tail(504)
    ax.plot(c.index, c.values, color=TEAL, lw=0.8)
    ax.axhline(0, color=DIM, lw=0.7, ls="--", alpha=0.6)
    style_ax(ax)
    panel_title(ax, title)
    date_axis(ax, c)
    legend(ax, ([plt.Line2D([], [], color=TEAL, lw=2),
                 plt.Line2D([], [], color=DIM, lw=1, ls="--")],
                ["corr", "zero"]))


# ── dashboard page ──────────────────────────────────────────────────────────

def fmt_num(v, nd=None):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "·"
    if nd is None:
        nd = 4 if abs(v) < 10 else (2 if abs(v) < 1000 else 0)
    return f"{v:,.{nd}f}"


def dashboard_page(book, section, code, rows, note=None):
    """rows: dicts — history rows {name,s,nd,[bp],[regime]} or static rows
    {name,static,unit,ctx} for manually-anchored values with no daily feed."""
    fig = book.new_page(section, code)
    fig.text(0.5, 0.905, "DASHBOARD · LEVEL · CHANGE · CONTEXT", ha="center",
             color=TXT, fontsize=9, fontweight="bold", family=SANS)
    has_regime = any("regime" in r or "ctx" in r for r in rows)
    cols = ["series", "last", "1d", "5d", "ytd", "5d z", "1y %ile",
            "regime" if has_regime else "flags"]
    colx = [0.045, 0.24, 0.35, 0.44, 0.53, 0.62, 0.71, 0.80]
    y0 = 0.872
    for cx, cname in zip(colx, cols):
        fig.text(cx, y0, cname, color=TEAL, fontsize=6.8, family=MONO)
    fig.lines.append(plt.Line2D([0.04, 0.96], [y0 - 0.008], color=LINE, lw=0.8,
                                transform=fig.transFigure))
    stretched = []
    y = y0 - 0.028
    for row in rows:
        name = row["name"]
        fig.patches.append(plt.Rectangle((0.04, y - 0.006), 0.92, 0.021,
                                         transform=fig.transFigure,
                                         facecolor=CARD, edgecolor=LINE,
                                         lw=0.4, zorder=0))
        if "static" in row:                       # manually-anchored row
            vals = [name, f"{row['static']:.2f}{row.get('unit','')}",
                    "·", "·", "·", "·", "·", row.get("ctx", "manual")]
            colors = [TXT, TXT, DIM, DIM, DIM, DIM, DIM, BLUE]
            for cx, v, c in zip(colx, vals, colors):
                fig.text(cx, y, str(v), color=c, fontsize=6.8, family=MONO)
            y -= 0.026
            continue
        s, bp = row["s"], row.get("bp", False)
        if bp:                                    # yields: changes in bp
            ch = lambda n: s.diff(n).iloc[-1] * 100
            d1, d5 = ch(1), ch(5)
            ys = s[s.index.year < s.index[-1].year]
            yt = (s.iloc[-1] - ys.iloc[-1]) * 100 if len(ys) else np.nan
            r5 = (s.diff(5) * 100).dropna().tail(756)
            z5 = ((r5.iloc[-1] - r5.mean()) / r5.std()
                  if len(r5) > 100 and r5.std() > 0 else np.nan)
            f1 = lambda v: f"{v:+.0f}" if np.isfinite(v) else "·"
        else:
            d1, d5 = pct(s, 1).iloc[-1], pct(s, 5).iloc[-1]
            yt, z5 = ytd(s), five_d_z(s)
            f1 = lambda v: f"{v:+.2f}" if np.isfinite(v) else "·"
        pc = pctile_1y(s)
        stl = stale_days(s)
        flags = []
        if stl > 6:
            flags.append(f"STALE d{stl}")
        tail = row.get("regime") or (" ".join(flags) if flags else "·")
        vals = [name, fmt_num(s.iloc[-1], row.get("nd")),
                f1(d1), f1(d5),
                (f"{yt:+.0f}" if bp else f"{yt:+.1f}") if np.isfinite(yt) else "·",
                f"{z5:+.1f}" if np.isfinite(z5) else "·",
                f"{pc:.0f}" if np.isfinite(pc) else "·", tail]
        colors = [TXT, TXT,
                  GREEN if d1 >= 0 else RED, GREEN if d5 >= 0 else RED,
                  GREEN if (np.isfinite(yt) and yt >= 0) else RED,
                  ORANGE if (np.isfinite(z5) and abs(z5) >= 2) else TXT,
                  ORANGE if (np.isfinite(pc) and (pc >= 95 or pc <= 5)) else TXT,
                  TEAL if row.get("regime") else (ORANGE if flags else DIM)]
        for cx, v, c in zip(colx, vals, colors):
            fig.text(cx, y, str(v), color=c, fontsize=6.8, family=MONO)
        unit = "bp" if bp else "%"
        if np.isfinite(z5) and abs(z5) >= 2:
            stretched.append(f"{name} 5d move z {z5:+.1f} ({f1(d5)}{unit})")
        if np.isfinite(pc) and (pc >= 95 or pc <= 5):
            stretched.append(f"{name} at {pc:.0f}th %ile of 1y range")
        if stl > 6:
            stretched.append(f"STALE: {name} · data older than {stl} sessions")
        y -= 0.026
    any_bp = any(r.get("bp") for r in rows if "s" in r)
    fig.text(0.045, y - 0.005,
             ("changes in bp for yield rows, % otherwise · 5d z vs own 3y history"
              " · regime dN = days in state · manual rows: RBI/FBIL anchors from"
              " the terminal (no free daily feed)") if any_bp else
             "changes in % · 5d z vs own 3y history · flags: stretch / staleness",
             color=DIM, fontsize=5.8, family=MONO)
    fig.text(0.5, y - 0.05, "WHAT'S STRETCHED · WHAT CHANGED", ha="center",
             color=TXT, fontsize=9, fontweight="bold", family=SANS)
    yy = y - 0.082
    if not stretched:
        stretched = ["No extremes, flips or staleness flags today · "
                     "a quiet tape is information too."]
    for it in stretched[:10]:
        fig.text(0.05, yy, "• " + it, color=TXT, fontsize=7.2, family=SANS)
        yy -= 0.024
    if note:
        fig.text(0.05, max(yy - 0.02, 0.06), note, color=DIM, fontsize=6.4,
                 family=SANS, va="top", wrap=True)


def quad_page(book, section, code, panels):
    """panels: list of 4 callables(ax)"""
    t = getattr(book, "_next_title", None)
    book._next_title = None
    fig = book.new_page(section, code, title=t[0] if t else None,
                        keys=t[1] if t else "")
    grid = [(0.07, 0.565, 0.40, 0.295), (0.57, 0.565, 0.40, 0.295),
            (0.07, 0.145, 0.40, 0.295), (0.57, 0.145, 0.40, 0.295)]
    for fn, rect in zip(panels, grid):
        if fn is None:
            continue
        ax = fig.add_axes(rect)
        fn(ax)


def duo_page(book, section, code, panels):
    t = getattr(book, "_next_title", None)
    book._next_title = None
    fig = book.new_page(section, code, title=t[0] if t else None,
                        keys=t[1] if t else "")
    grid = [(0.07, 0.585, 0.87, 0.28), (0.07, 0.135, 0.87, 0.28)]
    for fn, rect in zip(panels, grid):
        ax = fig.add_axes(rect)
        fn(ax)


# ── section builders ────────────────────────────────────────────────────────

def instrument_quad(book, section, code, s, label, dd_instead_of_impulse=False):
    book._next_title = (f"{label} · spot / RoC / vol / "
                        + ("drawdown" if dd_instead_of_impulse else "impulse"),
                        label)
    def p1(ax):
        panel_title(ax, f"{label} · Spot")
        spot_panel(ax, s, label)

    def p2(ax):
        panel_title(ax, f"{label} · 5-Day Rate of Change (1 Year)")
        roc_panel(ax, s, label)

    def p3(ax):
        panel_title(ax, f"{label} · Realized Volatility 30d vs 100d")
        rv_panel(ax, s, label)

    def p4(ax):
        if dd_instead_of_impulse:
            panel_title(ax, f"{label} · Drawdown from High")
            dd_panel(ax, s)
        else:
            panel_title(ax, f"{label} · Vol Regime Impulse (RV30 minus RV100)")
            impulse_panel(ax, s)
    quad_page(book, section, code, [p1, p2, p3, p4])


def build_india_equities(book, D):
    SEC, CODE = "India Equities · Daily Tear Sheet", "MITEQ1"
    rows = [{"name": n, "s": D[n], "nd": 0 if D[n].iloc[-1] > 1000 else 2}
            for n in ["Nifty 50", "Sensex", "Bank Nifty", "Midcap 100",
                      "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty FMCG",
                      "Nifty Metal", "India VIX"] if n in D]
    dashboard_page(book, SEC, CODE, rows)
    for n in ["Nifty 50", "Sensex", "Bank Nifty", "Midcap 100"]:
        if n in D:
            instrument_quad(book, SEC, CODE, D[n], n, dd_instead_of_impulse=True)
    # India VIX page
    if "India VIX" in D and "Nifty 50" in D:
        vix, nf = D["India VIX"], D["Nifty 50"]

        def p1(ax):
            panel_title(ax, "India VIX")
            spot_panel(ax, vix.tail(1008), "India VIX")

        def p2(ax):
            panel_title(ax, "India VIX · 5-Day Change (1 Year)")
            r = vix.diff(5).tail(252).dropna()
            ax.bar(r.index, r.values,
                   color=[RED if v >= 0 else GREEN for v in r.values], width=1.0)
            style_ax(ax, right=False); ax.yaxis.tick_left()
            ax2 = ax.twinx(); ax2.plot(vix.reindex(r.index).index,
                                       vix.reindex(r.index).values,
                                       color=ORANGE, lw=0.8)
            style_ax(ax2); ax2.grid(False)
            date_axis(ax, r)
            legend(ax, ([plt.Line2D([], [], color=RED, lw=3),
                         plt.Line2D([], [], color=ORANGE, lw=2)],
                        ["5d Δ", "India VIX"]))

        def p3(ax):
            panel_title(ax, "India VIX minus Nifty 30d Realized · Vol Risk Premium")
            vrp = (vix - rv(nf, 30).reindex(vix.index)).dropna().tail(1008)
            ax.plot(vrp.index, vrp.values, color=PURPLE, lw=0.8)
            ax.axhline(0, color=DIM, lw=0.6, ls="--", alpha=0.6)
            style_ax(ax); ax.set_ylabel("vol pts", fontsize=6, color=DIM)
            date_axis(ax, vrp)
            legend(ax, ([plt.Line2D([], [], color=PURPLE, lw=2)], ["IV–RV proxy"]))

        def p4(ax):
            panel_title(ax, "Nifty 5d % vs ΔIndia VIX 5d (2 Years, weekly)")
            a = pct(nf, 5).reindex(vix.index)
            b = vix.diff(5)
            df = pd.concat([b, a], axis=1).dropna().tail(504).iloc[::5]
            ax.scatter(df.iloc[:, 0], df.iloc[:, 1], s=5, color=BLUE, alpha=0.6)
            if len(df) > 10:
                try:
                    k = np.polyfit(df.iloc[:, 0], df.iloc[:, 1], 1)
                    xs = np.linspace(df.iloc[:, 0].min(),
                                     df.iloc[:, 0].max(), 50)
                    r2 = np.corrcoef(df.iloc[:, 0], df.iloc[:, 1])[0, 1] ** 2
                    ax.plot(xs, np.polyval(k, xs), color=ORANGE, lw=1.2)
                    ax.scatter(df.iloc[-1, 0], df.iloc[-1, 1], s=28,
                               color=TEAL, marker="D", zorder=5)
                    legend(ax, ([plt.Line2D([], [], color=BLUE, marker="o",
                                            lw=0),
                                 plt.Line2D([], [], color=ORANGE, lw=2),
                                 plt.Line2D([], [], color=TEAL, marker="D",
                                            lw=0)],
                                ["weeks", f"fit R2={r2:.2f}", "Recent"]))
                except Exception:
                    pass  # degenerate fit — keep the scatter, drop the line
            style_ax(ax)
            ax.set_xlabel("ΔVIX 5d", fontsize=6, color=DIM)
        book._next_title = ("India VIX · vol risk premium · spot-vol beta", "vix volatility vrp scatter")
        quad_page(book, SEC, CODE, [p1, p2, p3, p4])
    # sector relative strength
    nf = D.get("Nifty 50")
    if nf is not None:
        cyc = [n for n in ["Nifty IT", "Bank Nifty", "Nifty Auto",
                           "Nifty Metal", "Nifty Realty"] if n in D]
        dfn = [n for n in ["Nifty Pharma", "Nifty FMCG", "Nifty Energy"] if n in D]

        def rs_panel(ax, names, ttl):
            panel_title(ax, ttl)
            hs, ls = [], []
            for i, n in enumerate(names):
                ratio = (D[n] / nf.reindex(D[n].index)).dropna().tail(126)
                rb = ratio / ratio.iloc[0] * 100
                c = SERIES_COLORS[i % len(SERIES_COLORS)]
                ax.plot(rb.index, rb.values, color=c, lw=0.9)
                hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
            style_ax(ax); date_axis(ax, rb)
            legend(ax, (hs, ls))
        book._next_title = ("Sector relative strength vs Nifty", "sectors it bank auto metal pharma fmcg rotation")
        duo_page(book, SEC, CODE,
                 [lambda ax: rs_panel(ax, cyc,
                  "Sector Relative Strength vs Nifty · 6m rebased = 100 (cyclicals)"),
                  lambda ax: rs_panel(ax, dfn,
                  "Sector Relative Strength vs Nifty · 6m rebased = 100 (defensives)")])
    # global cross panel
    if all(k in D for k in ["Nifty 50", "S&P 500", "EEM"]):
        nf, spx, eem = D["Nifty 50"], D["S&P 500"], D["EEM"]

        def p1(ax):
            panel_title(ax, "Nifty vs S&P 500 vs EM · 2 Years, Rebased = 100")
            hs, ls = [], []
            for s_, lbl, c in [(nf, "Nifty 50", TEAL), (spx, "S&P 500", BLUE),
                               (eem, "EEM", PINK)]:
                t = s_.tail(504); rb = t / t.iloc[0] * 100
                ax.plot(rb.index, rb.values, color=c, lw=0.9)
                hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(lbl)
            style_ax(ax); date_axis(ax, nf.tail(504)); legend(ax, (hs, ls))

        def p2(ax):
            panel_title(ax, "Nifty / S&P 500 · India vs US Leadership")
            ratio = (nf / spx.reindex(nf.index)).dropna()
            sma = ratio.rolling(100).mean()
            ax.plot(ratio.index, ratio.values, color=TEAL, lw=0.8)
            ax.plot(sma.index, sma.values, color=ORANGE, lw=0.9, ls="--")
            style_ax(ax); date_axis(ax, ratio)
            legend(ax, ([plt.Line2D([], [], color=TEAL, lw=2),
                         plt.Line2D([], [], color=ORANGE, lw=2, ls="--")],
                        ["ratio", "100d SMA"]))

        def p3(ax):
            corr_panel(ax, nf, D["USD-INR"],
                       "Nifty vs USD-INR · Rolling 63d Correlation", w=63)

        def p4(ax):
            if "US 10Y" in D:
                corr_panel(ax, nf, D["US 10Y"],
                           "Nifty vs US 10Y Yield · Rolling 63d Correlation", w=63)
        book._next_title = ("Nifty vs world · SPX EEM · correlations", "global spx eem leadership usdinr us10y correlation")
        quad_page(book, SEC, CODE, [p1, p2, p3, p4])


def build_heavyweights(book, D):
    SEC, CODE = "Nifty Heavyweights · Daily", "MITHW1"
    names = [n for n in HEAVY if n in D]
    nf = D["Nifty 50"]
    # cross-sectional dashboard (table page)
    fig = book.new_page(SEC, CODE, title="Heavyweights cross-sectional dashboard + beta", keys="heavyweights reliance hdfc tcs icici infy momentum beta")
    fig.text(0.5, 0.905, "HEAVYWEIGHTS CROSS-SECTIONAL DASHBOARD · sorted by momentum z",
             ha="center", color=TXT, fontsize=9, fontweight="bold")
    cols = ["name", "last ₹", "5d %", "21d %", "63d %", "63d vs NIFTY (pp)",
            "momo z", "beta 63d", "RV30"]
    colx = [0.045, 0.16, 0.28, 0.375, 0.47, 0.565, 0.72, 0.815, 0.91]
    y0 = 0.87
    for cx, cname in zip(colx, cols):
        fig.text(cx, y0, cname, color=TEAL, fontsize=6.6, family=MONO)
    stats = []
    for n in names:
        s = D[n]
        r63n = pct(nf, 63).iloc[-1]
        stats.append(dict(
            name=n, last=s.iloc[-1], d5=pct(s, 5).iloc[-1],
            d21=pct(s, 21).iloc[-1], d63=pct(s, 63).iloc[-1],
            rel=pct(s, 63).iloc[-1] - r63n,
            mz=mom_z(s).iloc[-1], b=beta(s, nf).iloc[-1],
            rv30=rv(s, 30).iloc[-1]))
    stats.sort(key=lambda x: -(x["mz"] if np.isfinite(x["mz"]) else -9))
    y = y0 - 0.028
    for st in stats:
        vals = [st["name"], fmt_num(st["last"], 0), f"{st['d5']:+.1f}",
                f"{st['d21']:+.1f}", f"{st['d63']:+.1f}", f"{st['rel']:+.1f}",
                f"{st['mz']:+.2f}", f"{st['b']:.2f}", f"{st['rv30']:.0f}%"]
        colors = [TXT, TXT, GREEN if st["d5"] >= 0 else RED,
                  GREEN if st["d21"] >= 0 else RED,
                  GREEN if st["d63"] >= 0 else RED,
                  GREEN if st["rel"] >= 0 else RED,
                  ORANGE if abs(st["mz"]) > 1 else TXT, TXT, TXT]
        fig.patches.append(plt.Rectangle((0.04, y - 0.006), 0.92, 0.021,
                                         transform=fig.transFigure,
                                         facecolor=CARD, edgecolor=LINE,
                                         lw=0.4, zorder=0))
        for cx, v, c in zip(colx, vals, colors):
            fig.text(cx, y, str(v), color=c, fontsize=6.8, family=MONO)
        y -= 0.026
    fig.text(0.045, y - 0.005,
             "momo z = 20d return / (RV20·√(20/252)) · beta vs Nifty daily returns, "
             "63d window · next-earnings column omitted (no reliable free feed)",
             color=DIM, fontsize=5.8, family=MONO)
    # beta chart under table
    ax = fig.add_axes([0.08, 0.135, 0.86, 0.29])
    panel_title(ax, "Rolling 63d Beta to Nifty")
    hs, ls = [], []
    for i, n in enumerate(names):
        b = beta(D[n], nf).dropna().tail(252)
        c = SERIES_COLORS[i % len(SERIES_COLORS)]
        ax.plot(b.index, b.values, color=c, lw=0.8)
        hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
    style_ax(ax); date_axis(ax, b); legend(ax, (hs, ls), ncol=len(names))
    # relative-to-Nifty rebased pages
    blocks = [names[:5], names[5:]]

    def rel_panel(ax, blk, ttl):
        panel_title(ax, ttl)
        hs, ls = [], []
        for i, n in enumerate(blk):
            ratio = (D[n] / nf.reindex(D[n].index)).dropna().tail(252)
            rb = ratio / ratio.iloc[0] * 100
            c = SERIES_COLORS[i % len(SERIES_COLORS)]
            ax.plot(rb.index, rb.values, color=c, lw=0.9)
            hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        style_ax(ax); date_axis(ax, rb); legend(ax, (hs, ls))
    book._next_title = ("Heavyweights relative to Nifty · rebased 12m", "heavyweights relative rebased")
    duo_page(book, SEC, CODE,
             [lambda ax: rel_panel(ax, blocks[0],
              "Relative to Nifty · rebased 12m = 100 (block 1)"),
              lambda ax: rel_panel(ax, blocks[1],
              "Relative to Nifty · rebased 12m = 100 (block 2)")])
    # momo z + RV page
    def momo_panel(ax):
        panel_title(ax, "Vol-Normalised 20d Momentum Z · all names")
        hs, ls = [], []
        for i, n in enumerate(names):
            m = mom_z(D[n]).dropna().tail(252)
            c = SERIES_COLORS[i % len(SERIES_COLORS)]
            ax.plot(m.index, m.values, color=c, lw=0.7, alpha=0.85)
            hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        mN = mom_z(nf).dropna().tail(252)
        ax.plot(mN.index, mN.values, color="#ffffff", lw=1.4)
        hs.append(plt.Line2D([], [], color="#ffffff", lw=2)); ls.append("NIFTY")
        style_ax(ax); date_axis(ax, mN); legend(ax, (hs, ls), ncol=10)

    def rv_all_panel(ax):
        panel_title(ax, "30d Realized Vol · all names")
        hs, ls = [], []
        for i, n in enumerate(names):
            r = rv(D[n], 30).dropna().tail(252)
            c = SERIES_COLORS[i % len(SERIES_COLORS)]
            ax.plot(r.index, r.values, color=c, lw=0.7)
            hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        style_ax(ax); ax.set_ylabel("ann. vol %", fontsize=6, color=DIM)
        date_axis(ax, r); legend(ax, (hs, ls), ncol=10)
    book._next_title = ("Heavyweights momentum z + realized vol", "heavyweights momentum vol rv30")
    duo_page(book, SEC, CODE, [momo_panel, rv_all_panel])


def build_fx(book, D):
    SEC, CODE = "FX · INR Complex · Daily Tear Sheet", "MITFX1"
    order = ["USD-INR", "EUR-INR", "GBP-INR", "JPY-INR", "DXY",
             "EUR-USD", "USD-JPY"]
    rows = [{"name": n, "s": D[n], "nd": 4 if D[n].iloc[-1] < 10 else 2}
            for n in order if n in D]
    dashboard_page(book, SEC, CODE, rows)
    for n in ["USD-INR", "EUR-INR", "GBP-INR", "DXY"]:
        if n in D:
            instrument_quad(book, SEC, CODE, D[n], n)
    # combined RV page
    names = [n for n in order if n in D and n not in ("EUR-USD", "USD-JPY")]

    def rv_full(ax):
        panel_title(ax, "INR Complex · 30-Day Realized Volatility")
        hs, ls = [], []
        for i, n in enumerate(names):
            r = rv(D[n], 30).dropna()
            c = SERIES_COLORS[i % len(SERIES_COLORS)]
            ax.plot(r.index, r.values, color=c, lw=0.6)
            hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        style_ax(ax); ax.set_ylabel("ann. vol %", fontsize=6, color=DIM)
        date_axis(ax, r); legend(ax, (hs, ls))

    def rv_1y(ax):
        panel_title(ax, "INR Complex · 30-Day Realized Volatility (1 Year)")
        hs, ls = [], []
        for i, n in enumerate(names):
            r = rv(D[n], 30).dropna().tail(252)
            c = SERIES_COLORS[i % len(SERIES_COLORS)]
            ax.plot(r.index, r.values, color=c, lw=0.8)
            hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        style_ax(ax); date_axis(ax, r); legend(ax, (hs, ls))
    book._next_title = ("INR complex · 30d realized vol", "fx inr vol rv30 usdinr eurinr gbpinr dxy")
    duo_page(book, SEC, CODE, [rv_full, rv_1y])


def build_commodities(book, D):
    SEC, CODE = "Commodities · Daily Tear Sheet", "MITCM1"
    order = ["Brent", "WTI", "Gold", "Gold (INR)", "Silver", "Copper", "Nat Gas"]
    rows = [{"name": n, "s": D[n], "nd": 2 if D[n].iloc[-1] < 10000 else 0}
            for n in order if n in D]
    dashboard_page(
        book, SEC, CODE, rows,
        note="Gold (INR) = COMEX front month × USD/INR, per 10g · Brent is the "
             "India import benchmark · COT positioning omitted (CFTC covers US "
             "futures only; MCX equivalents have no free feed).")
    pairs = [("Brent", "WTI"), ("Gold", "Silver"), ("Copper", "Nat Gas")]
    for a, b in pairs:
        if a in D and b in D:
            def mk(nm):
                def left(ax, n=nm):
                    panel_title(ax, f"{n} · Front Month")
                    spot_panel(ax, D[n], n)

                def right(ax, n=nm):
                    panel_title(ax, f"{n} · 5-Day Rate of Change (1 Year)")
                    roc_panel(ax, D[n], n)
                return left, right
            a1, a2 = mk(a)
            b1, b2 = mk(b)
            book._next_title = (f"{a} & {b} · front month + RoC", f"{a.lower()} {b.lower()} commodity")
            quad_page(book, SEC, CODE, [a1, a2, b1, b2])
    if "Gold (INR)" in D:
        instrument_quad(book, SEC, CODE, D["Gold (INR)"], "Gold (INR / 10g)",
                        dd_instead_of_impulse=True)
    # correlations (the India lens)
    combos = [("Brent", "WTI", "Brent vs WTI"),
              ("Gold", "Silver", "Gold vs Silver"),
              ("Gold", "Copper", "Gold vs Copper"),
              ("Brent", "USD-INR", "Brent vs USD-INR"),
              ("Gold", "USD-INR", "Gold vs USD-INR"),
              ("Brent", "Nifty 50", "Brent vs Nifty")]
    fig = book.new_page(SEC, CODE, title="Commodity correlations · India lens", keys="correlation brent wti gold silver copper usdinr nifty")
    grid = [(0.07, 0.66, 0.40, 0.20), (0.57, 0.66, 0.40, 0.20),
            (0.07, 0.38, 0.40, 0.20), (0.57, 0.38, 0.40, 0.20),
            (0.07, 0.10, 0.40, 0.20), (0.57, 0.10, 0.40, 0.20)]
    for (a, b, t), rect in zip(combos, grid):
        if a in D and b in D:
            ax = fig.add_axes(rect)
            corr_panel(ax, D[a], D[b], f"{t} · 30-Day Correlation")


def build_crypto(book, D):
    SEC, CODE = "Crypto · Daily Tear Sheet", "MITCR1"
    rows = []
    if "Bitcoin" in D:
        rows.append({"name": "Bitcoin", "s": D["Bitcoin"], "nd": 0})
    if "Ethereum" in D:
        rows.append({"name": "Ethereum", "s": D["Ethereum"], "nd": 0})
    if "ETH/BTC" in D:
        rows.append({"name": "ETH/BTC", "s": D["ETH/BTC"], "nd": 4})
    if "Bitcoin" in D:
        rows.append({"name": "BTC 30d RV", "s": rv(D["Bitcoin"], 30).dropna(),
                     "nd": 1})
    if "DXY" in D:
        rows.append({"name": "DXY", "s": D["DXY"], "nd": 2})
    dashboard_page(book, SEC, CODE, rows)
    btc = D.get("Bitcoin")
    if btc is not None:
        def p1(ax):
            panel_title(ax, "Bitcoin · Daily")
            spot_panel(ax, btc.tail(756), "BTC", color=ORANGE)

        def p2(ax):
            panel_title(ax, "Bitcoin · 1 Year")
            t = btc.tail(252)
            ax.plot(t.index, t.values, color=ORANGE, lw=0.9)
            style_ax(ax); date_axis(ax, t)
            legend(ax, ([plt.Line2D([], [], color=ORANGE, lw=2)], ["BTC"]))

        def p3(ax):
            panel_title(ax, "Bitcoin · Daily % Return (1 Year)")
            r = pct(btc, 1).tail(365).dropna()
            ax.bar(r.index, r.values,
                   color=[GREEN if v >= 0 else RED for v in r.values], width=1.0)
            style_ax(ax); ax.set_ylabel("%", fontsize=6, color=DIM)
            date_axis(ax, r)

        def p4(ax):
            panel_title(ax, "Bitcoin · Drawdown from High (1 Year)")
            t = btc.tail(365)
            dd_panel(ax, t)
        quad_page(book, SEC, CODE, [p1, p2, p3, p4])
        # returns aggregation page
        def wk(ax):
            panel_title(ax, "Weekly Returns (1 Year)")
            w = btc.resample("W").last().pct_change().dropna().tail(52) * 100
            ax.bar(w.index, w.values, width=5.0,
                   color=[ORANGE if v >= 0 else RED for v in w.values])
            style_ax(ax); ax.set_ylabel("%", fontsize=6, color=DIM)
            date_axis(ax, w)

        def mo(ax):
            panel_title(ax, "Monthly Returns (3 Years)")
            m = btc.resample("ME").last().pct_change().dropna().tail(36) * 100
            ax.bar(m.index, m.values, width=20,
                   color=[ORANGE if v >= 0 else RED for v in m.values])
            style_ax(ax); date_axis(ax, m)

        def yr(ax):
            panel_title(ax, "Annual Returns")
            y = btc.resample("YE").last().pct_change().dropna() * 100
            ax.bar(y.index, y.values, width=200,
                   color=[ORANGE if v >= 0 else RED for v in y.values])
            style_ax(ax)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            for lb in ax.get_xticklabels():
                lb.set_rotation(90); lb.set_fontsize(5.6)

        def rv30(ax):
            panel_title(ax, "Bitcoin · 30d Realized Volatility")
            r = rv(btc, 30).dropna().tail(756)
            ax.plot(r.index, r.values, color=PURPLE, lw=0.8)
            style_ax(ax); ax.set_ylabel("ann. vol %", fontsize=6, color=DIM)
            date_axis(ax, r)
            legend(ax, ([plt.Line2D([], [], color=PURPLE, lw=2)], ["RV 30d"]))
        quad_page(book, SEC, CODE, [wk, mo, yr, rv30])
        # macro cross page
        def x1(ax):
            panel_title(ax, "Bitcoin vs DXY (2 Years)")
            t, dx = btc.tail(504), D["DXY"].tail(504)
            ax.plot(dx.index, dx.values, color=BLUE, lw=0.8)
            style_ax(ax, right=False); ax.yaxis.tick_left()
            ax2 = ax.twinx(); ax2.plot(t.index, t.values, color=ORANGE, lw=0.8)
            style_ax(ax2); ax2.grid(False); date_axis(ax, t)
            legend(ax, ([plt.Line2D([], [], color=ORANGE, lw=2),
                         plt.Line2D([], [], color=BLUE, lw=2)], ["BTC", "DXY"]))

        def x2(ax):
            corr_panel(ax, btc, D["DXY"], "BTC-DXY · 30d Rolling Correlation")

        def x3(ax):
            corr_panel(ax, btc, D["Nifty 50"],
                       "BTC-Nifty · 30d Rolling Correlation")

        def x4(ax):
            if "US 10Y" in D:
                corr_panel(ax, btc, D["US 10Y"],
                           "BTC-US 10Y · 30d Rolling Correlation")
        quad_page(book, SEC, CODE, [x1, x2, x3, x4])
    eth = D.get("Ethereum")
    if eth is not None:
        def e1(ax):
            panel_title(ax, "Ethereum · Daily")
            spot_panel(ax, eth.tail(756), "ETH", color=PURPLE)

        def e2(ax):
            panel_title(ax, "Ethereum · Daily % Return (1 Year)")
            r = pct(eth, 1).tail(365).dropna()
            ax.bar(r.index, r.values,
                   color=[GREEN if v >= 0 else RED for v in r.values], width=1.0)
            style_ax(ax); date_axis(ax, r)

        def e3(ax):
            panel_title(ax, "ETH / BTC Ratio · alt leadership (2 Years)")
            r = D["ETH/BTC"].tail(504)
            ax.plot(r.index, r.values, color=CYAN, lw=0.8)
            style_ax(ax); date_axis(ax, r)
            legend(ax, ([plt.Line2D([], [], color=CYAN, lw=2)], ["ETH/BTC"]))

        def e4(ax):
            panel_title(ax, "Ethereum · 30d Realized Vol")
            r = rv(eth, 30).dropna().tail(756)
            ax.plot(r.index, r.values, color=PINK, lw=0.8)
            style_ax(ax); ax.set_ylabel("ann. vol %", fontsize=6, color=DIM)
            date_axis(ax, r)
            legend(ax, ([plt.Line2D([], [], color=PINK, lw=2)], ["RV 30d"]))
        book._next_title = ("Regime evidence · trend, vix bands, ribbon", "regime evidence sma vix ribbon score")
    quad_page(book, SEC, CODE, [e1, e2, e3, e4])


REGIME_COLORS = {"Bull Steepener": GREEN, "Bear Steepener": ORANGE,
                 "Bull Flattener": BLUE, "Bear Flattener": RED,
                 "Steepener Twist": CYAN, "Flattener Twist": PURPLE}


def curve_regime(short, long_, w=20):
    """Classify curve moves over a w-day window (Alfie's taxonomy)."""
    idx = short.index.intersection(long_.index)
    s, l = short.reindex(idx), long_.reindex(idx)
    ds, dl = s.diff(w), l.diff(w)
    dslope = (l - s).diff(w)
    lab = pd.Series("·", index=idx)
    steep, flat = dslope > 0, dslope <= 0
    twist = np.sign(ds) != np.sign(dl)
    lab[steep & (dl > 0) & ~twist] = "Bear Steepener"
    lab[steep & (dl <= 0) & ~twist] = "Bull Steepener"
    lab[flat & (ds > 0) & ~twist] = "Bear Flattener"
    lab[flat & (ds <= 0) & ~twist] = "Bull Flattener"
    lab[steep & twist] = "Steepener Twist"
    lab[flat & twist] = "Flattener Twist"
    return lab.replace("·", np.nan).dropna()


def days_in_state(lab):
    if len(lab) == 0:
        return "·", 0
    cur, n = lab.iloc[-1], 1
    for v in lab.values[-2::-1]:
        if v != cur:
            break
        n += 1
    return cur, n


def regime_bars(ax, level, lab, title):
    panel_title(ax, title)
    lv = level.reindex(lab.index).dropna().tail(504)
    lb = lab.reindex(lv.index)
    for name, c in REGIME_COLORS.items():
        m = lb == name
        if m.any():
            ax.bar(lv.index[m], lv.values[m], color=c, width=1.0)
    style_ax(ax)
    ax.set_ylabel("bp", fontsize=6, color=DIM)
    date_axis(ax, lv)
    legend(ax, ([plt.Line2D([], [], color=c, lw=3)
                 for c in REGIME_COLORS.values()],
                list(REGIME_COLORS.keys())), ncol=6, dy=-0.26)


def build_rates(book, D, F, A):
    """India + US rates. India: RBI/FBIL anchors from the terminal + gilt-ETF
    daily duration proxies + OECD monthly 10Y. US: full daily complex (FRED)."""
    SEC, CODE = "Rates · India & US · Daily Tear Sheet", "MITRT1"
    us2, us10, us30 = F.get("US 2Y"), F.get("US 10Y FRED"), F.get("US 30Y")
    # regimes for dashboard rows
    reg2s10, reg1030 = "·", "·"
    if us2 is not None and us10 is not None:
        lab = curve_regime(us2, us10)
        st, d = days_in_state(lab)
        reg2s10 = f"{st} · d{d}"
    if us10 is not None and us30 is not None:
        st, d = days_in_state(curve_regime(us10, us30))
        reg1030 = f"{st} · d{d}"
    rows = []
    # India block — anchored values (no free daily feed) + ETF proxies
    if A.get("repo"):
        rows.append({"name": "IN Repo Rate", "static": A["repo"], "unit": "%",
                     "ctx": "RBI · policy anchor"})
    if A.get("mibor_on"):
        rows.append({"name": "IN MIBOR O/N", "static": A["mibor_on"],
                     "unit": "%", "ctx": "FBIL · via terminal"})
    if A.get("mibor_3m"):
        rows.append({"name": "IN MIBOR 3M", "static": A["mibor_3m"],
                     "unit": "%", "ctx": "FBIL · via terminal"})
    if A.get("mibor_on") and A.get("repo"):
        sp = (A["mibor_on"] - A["repo"]) * 100
        # MIBOR structurally lives inside the SDF/MSF corridor (±25bp).
        # If the anchor sits well outside it, the anchor is stale — say so
        # rather than printing a false liquidity read.
        if abs(sp) > 35:
            liq = "⚠ outside corridor — refresh MIBOR anchor"
        else:
            liq = ("deficit → toward MSF" if sp > 15 else
                   "surplus → toward SDF" if sp < -15 else "balanced")
        rows.append({"name": "MIBOR−Repo (bp)", "static": sp, "unit": "",
                     "ctx": f"liquidity: {liq}"})
    P = ois_points(A)
    if P.get(12) and A.get("repo"):
        cp = (P[12] - A["repo"]) * 100
        rows.append({"name": "OIS 1Y − Repo (bp)", "static": cp, "unit": "",
                     "ctx": "cuts priced" if cp < 0 else "hikes priced"})
    if P.get(12) and P.get(60):
        rows.append({"name": "OIS 1s5s (bp)", "static": (P[60] - P[12]) * 100,
                     "unit": "", "ctx": "policy-path slope"})
    if A.get("in10y"):
        rows.append({"name": "IN 10Y G-sec", "static": A["in10y"], "unit": "%",
                     "ctx": "terminal anchor"})
        if A.get("cpi"):
            rows.append({"name": "IN real 10Y (-CPI)",
                         "static": A["in10y"] - A["cpi"], "unit": "%",
                         "ctx": f"CPI {A['cpi']:.2f}%"})
            rows.append({"name": "IN real repo (-CPI)",
                         "static": A["repo"] - A["cpi"], "unit": "%",
                         "ctx": "restrictive if >1.5"})
        if us10 is not None:
            rows.append({"name": "IN-US 10Y spread",
                         "static": A["in10y"] - us10.iloc[-1], "unit": "pp",
                         "ctx": "carry cushion"})
    for n, lbl in [("Gilt 5Y ETF", "Gilt 5Y ETF (px)"),
                   ("Gilt LT ETF", "Gilt LT ETF (px)")]:
        if n in D:
            rows.append({"name": lbl, "s": D[n], "nd": 2,
                         "regime": "px up = yields dn"})
    # US block — daily, changes in bp
    for n, s in [("US 2Y", us2), ("US 5Y", F.get("US 5Y")),
                 ("US 10Y", us10), ("US 30Y", us30)]:
        if s is not None:
            rows.append({"name": n + " Yield", "s": s, "nd": 2, "bp": True})
    if us2 is not None and us10 is not None:
        sl = ((us10 - us2) * 100).dropna()
        rows.append({"name": "US 2s10s (bp)", "s": sl / 100, "nd": 0,
                     "bp": True, "regime": reg2s10})
    if us10 is not None and us30 is not None:
        rows.append({"name": "US 10s30s (bp)", "s": (us30 - us10), "nd": 0,
                     "bp": True, "regime": reg1030})
    if "MOVE" in D:
        rows.append({"name": "MOVE", "s": D["MOVE"], "nd": 1})
    if not rows:
        return
    dashboard_page(
        book, SEC, CODE, rows,
        note="India daily G-sec curve has no free feed (FBIL/CCIL licensed) — "
             "levels above are RBI/FBIL anchors carried by the terminal's "
             "auto-scrape; direction is tracked daily via gilt-ETF prices. "
             "US complex is full daily history from FRED. MIBOR is unsecured "
             "(call money) vs the secured repo — its spread to repo is itself "
             "a liquidity signal, unlike SOFR−EFFR.")
    # ── India policy corridor · MIBOR · OIS page ────────────────────────────
    P = ois_points(A)
    if A.get("repo"):
        repo = A["repo"]
        sdf, msf = repo - 0.25, repo + 0.25

        def cor1(ax):
            panel_title(ax, "RBI Policy Corridor · where overnight money sits")
            ax.axhspan(sdf, msf, color=TEAL, alpha=0.06)
            for v, lbl, c in [(msf, f"MSF (ceiling) {msf:.2f}", RED),
                              (repo, f"Repo {repo:.2f}", TEAL),
                              (sdf, f"SDF (floor) {sdf:.2f}", GREEN)]:
                ax.axhline(v, color=c, lw=1.1, ls="--" if v != repo else "-")
                ax.text(0.02, v + 0.008, lbl, transform=ax.get_yaxis_transform(),
                        color=c, fontsize=6.5, family=MONO)
            if A.get("mibor_on"):
                ax.scatter([0.62], [A["mibor_on"]], s=70, color=ORANGE,
                           zorder=5, marker="D")
                ax.text(0.65, A["mibor_on"], f"MIBOR O/N {A['mibor_on']:.2f}",
                        transform=ax.get_yaxis_transform(), color=ORANGE,
                        fontsize=7, family=MONO, va="center")
            if A.get("mibor_3m"):
                ax.scatter([0.30], [A["mibor_3m"]], s=45, color=PURPLE,
                           zorder=5)
                ax.text(0.33, A["mibor_3m"], f"MIBOR 3M {A['mibor_3m']:.2f}",
                        transform=ax.get_yaxis_transform(), color=PURPLE,
                        fontsize=6.5, family=MONO, va="center")
            ax.set_xlim(0, 1)
            ax.set_ylim(sdf - 0.45, max(msf, A.get("mibor_3m", msf)) + 0.45)
            ax.set_xticks([])
            style_ax(ax)

        def cor2(ax):
            panel_title(ax, "MIBOR-OIS Curve · the priced RBI path")
            if not P:
                style_ax(ax)
                return
            ms = sorted(P)
            ax.plot(ms, [P[m] for m in ms], color=TEAL, lw=1.4, marker="o",
                    ms=3.5)
            ax.axhline(repo, color=ORANGE, lw=0.9, ls="--")
            for m in (12, 60):
                if m in P:
                    ax.annotate(f"{'1Y' if m==12 else '5Y'} {P[m]:.2f}",
                                (m, P[m]), textcoords="offset points",
                                xytext=(4, -11), color=TXT, fontsize=6.5,
                                family=MONO)
            ax.set_xscale("symlog", linthresh=1)
            ax.set_xticks([0.03, 1, 3, 6, 12, 24, 36, 60])
            ax.set_xticklabels(["O/N", "1M", "3M", "6M", "1Y", "2Y", "3Y",
                                "5Y"], fontsize=6)
            style_ax(ax)
            legend(ax, ([plt.Line2D([], [], color=TEAL, lw=2),
                         plt.Line2D([], [], color=ORANGE, lw=2, ls="--")],
                        ["OIS (anchor)", f"Repo {repo:.2f}"]))

        def cor3(ax):
            panel_title(ax, "Policy Priced In by Tenor · OIS minus Repo (bp)")
            if not P:
                style_ax(ax)
                return
            ms = [m for m in sorted(P) if m >= 1]
            d = [(P[m] - repo) * 100 for m in ms]
            ax.bar(range(len(ms)), d,
                   color=[GREEN if v <= 0 else RED for v in d], width=0.6)
            ax.axhline(0, color=DIM, lw=0.7)
            ax.set_xticks(range(len(ms)))
            ax.set_xticklabels([f"{int(m)}M" if m < 12 else f"{int(m//12)}Y"
                                for m in ms], fontsize=6)
            style_ax(ax)
            ax.set_ylabel("bp vs repo", fontsize=6, color=DIM)
            legend(ax, ([plt.Line2D([], [], color=GREEN, lw=3),
                         plt.Line2D([], [], color=RED, lw=3)],
                        ["cuts priced", "hikes priced"]))

        def cor4(ax):
            panel_title(ax, "Front-End Read · rules on the anchors")
            ax.set_xticks([]); ax.set_yticks([])
            style_ax(ax)
            ax.grid(False)
            lines = []
            if A.get("mibor_on"):
                sp = (A["mibor_on"] - repo) * 100
                if abs(sp) > 35:
                    liq = ("ANCHOR STALE? MIBOR sits outside the corridor — "
                           "refresh MACRO_LIVE / ois_manual.json")
                else:
                    liq = ("DEFICIT — call money pushed toward MSF"
                           if sp > 15 else
                           "SURPLUS — call money drifting toward SDF"
                           if sp < -15 else
                           "BALANCED — MIBOR hugging the repo rate")
                lines += [f"MIBOR−Repo: {sp:+.0f}bp → {liq}",
                          "  (unsecured vs secured — sign flips vs SOFR−EFFR)"]
            if P.get(12):
                cp = (P[12] - repo) * 100
                lines += [f"1Y OIS − Repo: {cp:+.0f}bp → "
                          + (f"≈{abs(cp)/25:.1f} cuts priced over 1y"
                             if cp < 0 else
                             f"≈{cp/25:.1f} hikes priced over 1y")]
            if P.get(12) and P.get(60):
                sl = (P[60] - P[12]) * 100
                lines += [f"OIS 1s5s: {sl:+.0f}bp → "
                          + ("easing cycle then normalization priced"
                             if sl > 0 else "flat/inverted policy path")]
            lines += ["", "Levels are RBI/FBIL anchors via the terminal",
                      "(or ois_manual.json). Liquid tenors: 1Y & 5Y.",
                      "OIS beyond 5Y is thin — G-sec is the long-end read."]
            for i, ln in enumerate(lines):
                ax.text(0.04, 0.92 - i * 0.10, ln, transform=ax.transAxes,
                        color=TXT if not ln.startswith(" ") else DIM,
                        fontsize=7.2, family=MONO)
        book._next_title = ("RBI corridor · MIBOR · OIS priced path", "corridor repo mibor ois sdf msf policy cuts priced liquidity")
        quad_page(book, SEC, CODE, [cor1, cor2, cor3, cor4])
    # ── three-layer curve regime matrix ─────────────────────────────────────
    def z_strength(spread):
        d20 = spread.diff(20).dropna()
        if len(d20) < 120 or d20.std() == 0:
            return np.nan
        z = (d20.iloc[-1] - d20.mean()) / d20.std()
        return min(10.0, abs(z) * 3.33)

    matrix = []   # (layer, pair, lvl_bp, d20_bp, regime+d, strength, note)
    def add_pair(layer, pair, short, long_, note="·"):
        sp = ((long_ - short.reindex(long_.index)) * 100).dropna()
        if len(sp) < 140:
            return
        st, d = days_in_state(curve_regime(short, long_))
        stg = z_strength(sp)
        matrix.append((layer, pair, f"{sp.iloc[-1]:+.0f}",
                       f"{sp.diff(20).iloc[-1]:+.0f}", f"{st} · d{d}",
                       f"{stg:.0f}/10" if np.isfinite(stg) else "·", note))
    if us2 is not None and us10 is not None:
        add_pair("US · Nominal", "2s10s", us2, us10)
    if us10 is not None and us30 is not None:
        add_pair("US · Nominal", "10s30s", us10, us30)
    be5_, be10_ = F.get("BE 5Y"), F.get("BE 10Y")
    if be5_ is not None and be10_ is not None:
        add_pair("US · Inflation", "BE 5s10s", be5_, be10_,
                 "breakeven curve")
    r5_, r10_ = F.get("Real 5Y"), F.get("Real 10Y")
    if r5_ is not None and r10_ is not None:
        add_pair("US · Real", "TIPS 5s10s", r5_, r10_, "Fisher residual")
    if "Gilt 5Y ETF" in D and "Gilt LT ETF" in D:
        py5 = -np.log(D["Gilt 5Y ETF"])
        pyL = -np.log(D["Gilt LT ETF"])
        st, d = days_in_state(curve_regime(py5, pyL))
        sp = (pyL - py5.reindex(pyL.index)).dropna() * 100
        stg = z_strength(sp)
        matrix.append(("IN · Nominal", "5Y vs LT (ETF)", "·",
                       f"{sp.diff(20).iloc[-1]:+.0f}", f"{st} · d{d}",
                       f"{stg:.0f}/10" if np.isfinite(stg) else "·",
                       "PROXY — gilt-ETF prices"))
    if P.get(12) and P.get(60):
        sl = (P[60] - P[12]) * 100
        matrix.append(("IN · Policy path", "OIS 1s5s", f"{sl:+.0f}", "·",
                       "easing→normalize" if sl > 0 else "flat/inverted",
                       "·", "anchor — no daily history"))
    if A.get("in10y") and A.get("cpi"):
        matrix.append(("IN · Real", "10Y − CPI yoy",
                       f"{(A['in10y']-A['cpi'])*100:+.0f}", "·",
                       "restrictive" if A["in10y"] - A["cpi"] > 1.5
                       else "accommodative-ish", "·",
                       "PROXY — linkers dead since 2016 buyback"))
    if matrix:
        fig = book.new_page(SEC, CODE, title="Curve regime matrix · nominal / inflation / real", keys="matrix curve regime steepener flattener breakeven tips real gilt")
        fig.text(0.5, 0.905, "CURVE REGIME MATRIX · NOMINAL / INFLATION / "
                 "REAL · US DAILY, INDIA VIA HONEST PROXIES", ha="center",
                 color=TXT, fontsize=8.5, fontweight="bold", family=SANS)
        cols = ["layer", "pair", "lvl bp", "20d Δbp", "regime", "strength",
                "note"]
        colx = [0.045, 0.17, 0.30, 0.375, 0.46, 0.66, 0.74]
        y0 = 0.868
        for cx, cn in zip(colx, cols):
            fig.text(cx, y0, cn, color=TEAL, fontsize=6.6, family=MONO)
        fig.lines.append(plt.Line2D([0.04, 0.96], [y0 - 0.008], color=LINE,
                                    lw=0.8, transform=fig.transFigure))
        y = y0 - 0.03
        for layer, pair, lvl, d20, reg, stg, note in matrix:
            fig.patches.append(plt.Rectangle(
                (0.04, y - 0.007), 0.92, 0.024, transform=fig.transFigure,
                facecolor=CARD, edgecolor=LINE, lw=0.4, zorder=0))
            rc = REGIME_COLORS.get(reg.split(" · ")[0], TEAL)
            for cx, v, c in zip(colx, [layer, pair, lvl, d20, reg, stg, note],
                                [TXT, TXT, TXT, TXT, rc, ORANGE,
                                 BLUE if "PROXY" in note or "anchor" in note
                                 else DIM]):
                fig.text(cx, y, str(v), color=c, fontsize=6.4, family=MONO)
            y -= 0.030
        fig.text(0.045, y - 0.008,
                 "Bull/Bear = direction of yields · Steepener/Flattener = "
                 "direction of the spread · strength = |z| of the 20d spread "
                 "move vs its own 3y distribution, capped at 10 · dN = days "
                 "in state", color=DIM, fontsize=5.9, family=MONO)
        expl = [
            "Reading the three layers (US, daily):",
            "  Nominal moves = growth + inflation + term premium, undifferentiated.",
            "  Breakeven layer isolates the inflation-expectations component.",
            "  Real (TIPS) layer is the growth/policy-stance residual — the one equities actually discount.",
            "",
            "India, without self-deception:",
            "  No INR inflation swaps trade; the 2013 linkers were bought back in Feb-2016 — so no daily",
            "  inflation or real curve exists. Nominal direction comes from gilt-ETF prices (5Y vs long-",
            "  duration, classified from price-implied yield moves). The forward-looking policy row is the",
            "  MIBOR-OIS curve (anchors); the real row is 10Y minus trailing CPI. Blue rows = proxy/anchor.",
            "  When a row is a proxy, treat the REGIME as informative and the strength score as absent —",
            "  we do not synthesize confidence we don't have."]
        yy = y - 0.045
        for ln in expl:
            fig.text(0.05, yy, ln, color=TXT if not ln.startswith("  ")
                     else DIM, fontsize=6.8, family=SANS if not
                     ln.startswith("  ") else MONO)
            yy -= 0.023
    # India complex page
    in10m = F.get("India 10Y (monthly)")
    def p_in10(ax):
        panel_title(ax, "India 10Y G-sec · Monthly (OECD via FRED)")
        if in10m is None:
            ax.text(0.5, 0.5, "feed unavailable", transform=ax.transAxes,
                    ha="center", color=DIM, fontsize=8)
            style_ax(ax)
            return
        spot_panel(ax, in10m, "IN 10Y")

    def p_spread(ax):
        panel_title(ax, "India minus US 10Y · Carry Cushion (monthly, pp)")
        if in10m is None or us10 is None:
            style_ax(ax)
            return
        u = us10.resample("MS").last()
        sp = (in10m - u.reindex(in10m.index).ffill()).dropna()
        ax.plot(sp.index, sp.values, color=TEAL, lw=0.9)
        ax.axhline(0, color=DIM, lw=0.6, ls="--")
        style_ax(ax)
        date_axis(ax, sp)
        legend(ax, ([plt.Line2D([], [], color=TEAL, lw=2)], ["IN-US 10Y"]))

    def p_g5(ax):
        panel_title(ax, "Gilt 5Y ETF · Daily Duration Proxy (px up = yields dn)")
        if "Gilt 5Y ETF" in D:
            spot_panel(ax, D["Gilt 5Y ETF"].tail(756), "GILT5YBEES", color=BLUE)
        else:
            style_ax(ax)

    def p_glt(ax):
        panel_title(ax, "Gilt Long-Term ETF · 5-Day RoC (1 Year)")
        if "Gilt LT ETF" in D:
            roc_panel(ax, D["Gilt LT ETF"], "LTGILTBEES")
        else:
            style_ax(ax)
    book._next_title = ("India 10Y · IN-US spread · gilt ETFs", "india 10y gsec spread gilt etf carry")
    quad_page(book, SEC, CODE, [p_in10, p_spread, p_g5, p_glt])
    # transmission page — rates → India equity/FX channels
    def t1(ax):
        panel_title(ax, "Bank Nifty vs Gilt LT ETF · 6m Rebased = 100")
        hs, ls = [], []
        for n, c in [("Bank Nifty", TEAL), ("Gilt LT ETF", ORANGE)]:
            if n in D:
                t = D[n].tail(126)
                rb = t / t.iloc[0] * 100
                ax.plot(rb.index, rb.values, color=c, lw=0.9)
                hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(n)
        style_ax(ax); date_axis(ax, rb); legend(ax, (hs, ls))

    def t2(ax):
        if "Nifty 50" in D and "Gilt LT ETF" in D:
            corr_panel(ax, D["Nifty 50"], D["Gilt LT ETF"],
                       "Nifty vs Gilt ETF · 63d Correlation (stock-bond)", w=63)
        else:
            style_ax(ax)

    def t3(ax):
        if "USD-INR" in D and us10 is not None:
            corr_panel(ax, D["USD-INR"], us10,
                       "USD-INR vs US 10Y · 63d Correlation", w=63)
        else:
            style_ax(ax)

    def t4(ax):
        panel_title(ax, "MOVE Index · US Rates Vol")
        if "MOVE" in D:
            spot_panel(ax, D["MOVE"].tail(756), "MOVE", color=PURPLE)
        else:
            style_ax(ax)
    book._next_title = ("Rates transmission · Bank Nifty · MOVE", "transmission bank nifty gilt correlation move usdinr")
    quad_page(book, SEC, CODE, [t1, t2, t3, t4])
    # US yields quad
    if us2 is not None:
        def u1(ax):
            panel_title(ax, "US 2-Year Yield")
            spot_panel(ax, us2, "US 2Y")

        def u2(ax):
            panel_title(ax, "US 10-Year Yield")
            spot_panel(ax, us10, "US 10Y")

        def u3(ax):
            panel_title(ax, "US 30-Year Yield")
            spot_panel(ax, us30, "US 30Y") if us30 is not None else style_ax(ax)

        def u4(ax):
            panel_title(ax, "US 10Y · 5-Day Change in bp (1 Year)")
            r = (us10.diff(5) * 100).tail(252).dropna()
            px = us10.reindex(r.index)
            ax.bar(r.index, r.values, width=1.0,
                   color=[GREEN if v >= 0 else RED for v in r.values])
            style_ax(ax, right=False); ax.yaxis.tick_left()
            ax2 = ax.twinx()
            ax2.plot(px.index, px.values, color=ORANGE, lw=0.8)
            style_ax(ax2); ax2.grid(False); date_axis(ax, r)
            legend(ax, ([plt.Line2D([], [], color=GREEN, lw=3),
                         plt.Line2D([], [], color=ORANGE, lw=2)],
                        ["5d Δbp", "US 10Y"]))
        book._next_title = ("US yields · 2Y 10Y 30Y", "us yields treasury 2y 10y 30y bp")
        quad_page(book, SEC, CODE, [u1, u2, u3, u4])
        # curve page with regime bars
        sl = (us10 - us2) * 100

        def c1(ax):
            panel_title(ax, "US 2s10s Curve (bp)")
            spot_panel(ax, sl.dropna(), "2s10s")

        def c2(ax):
            panel_title(ax, "US 10s30s Curve (bp)")
            if us30 is not None:
                spot_panel(ax, ((us30 - us10) * 100).dropna(), "10s30s",
                           color=BLUE)
            else:
                style_ax(ax)

        def c3(ax):
            regime_bars(ax, sl, curve_regime(us2, us10),
                        "US 2s10s · Curve Regime (20-Day)")

        def c4(ax):
            if us30 is not None:
                regime_bars(ax, (us30 - us10) * 100, curve_regime(us10, us30),
                            "US 10s30s · Curve Regime (20-Day)")
            else:
                style_ax(ax)
        book._next_title = ("US curve · 2s10s 10s30s + regime bars", "curve 2s10s 10s30s steepener flattener regime")
        quad_page(book, SEC, CODE, [c1, c2, c3, c4])
    # inflation & funding quad
    be5, be10, be55 = F.get("BE 5Y"), F.get("BE 10Y"), F.get("BE 5Y5Y")
    if be5 is not None or F.get("EFFR") is not None:
        def i1(ax):
            panel_title(ax, "US Breakevens · 5Y, 10Y, 5Y5Y Forward")
            hs, ls = [], []
            for s_, lbl, c in [(be5, "5Y BE", TEAL), (be10, "10Y BE", BLUE),
                               (be55, "5Y5Y Fwd", ORANGE)]:
                if s_ is not None:
                    ax.plot(s_.index, s_.values, color=c, lw=0.7)
                    hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(lbl)
            style_ax(ax)
            if be5 is not None:
                date_axis(ax, be5)
            legend(ax, (hs, ls))

        def i2(ax):
            panel_title(ax, "US Real Yields · 5Y and 10Y TIPS")
            hs, ls = [], []
            for s_, lbl, c in [(F.get("Real 5Y"), "5Y Real", GREEN),
                               (F.get("Real 10Y"), "10Y Real", BLUE)]:
                if s_ is not None:
                    ax.plot(s_.index, s_.values, color=c, lw=0.7)
                    hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(lbl)
            ax.axhline(0, color=DIM, lw=0.6, ls="--")
            style_ax(ax)
            if F.get("Real 10Y") is not None:
                date_axis(ax, F["Real 10Y"])
            legend(ax, (hs, ls))

        def i3(ax):
            panel_title(ax, "Funding · EFFR vs SOFR")
            hs, ls = [], []
            for s_, lbl, c in [(F.get("EFFR"), "EFFR", TEAL),
                               (F.get("SOFR"), "SOFR", ORANGE)]:
                if s_ is not None:
                    t = s_.tail(2016)
                    ax.plot(t.index, t.values, color=c, lw=0.7)
                    hs.append(plt.Line2D([], [], color=c, lw=2)); ls.append(lbl)
            style_ax(ax)
            if F.get("EFFR") is not None:
                date_axis(ax, F["EFFR"].tail(2016))
            legend(ax, (hs, ls))

        def i4(ax):
            panel_title(ax, "Funding Stress · SOFR minus EFFR (bp)")
            if F.get("EFFR") is not None and F.get("SOFR") is not None:
                d = ((F["SOFR"] - F["EFFR"].reindex(F["SOFR"].index)) * 100
                     ).dropna().tail(2016)
                ax.fill_between(d.index, d.values, 0,
                                where=d.values >= 0, color=ORANGE, alpha=0.85)
                ax.fill_between(d.index, d.values, 0,
                                where=d.values < 0, color="#b0413e", alpha=0.85)
                style_ax(ax); ax.set_ylabel("bp", fontsize=6, color=DIM)
                date_axis(ax, d)
            else:
                style_ax(ax)
        book._next_title = ("US breakevens · TIPS real · EFFR-SOFR funding", "breakeven tips real yields effr sofr funding stress inflation")
        quad_page(book, SEC, CODE, [i1, i2, i3, i4])


# ── regime read · what's favorable in India ────────────────────────────────

def regime_signals(D, F):
    """Six mechanical daily signals, each +1 / 0 / −1 for Indian risk assets.
    Everything is computed from prices — no editorial input."""
    nf = D["Nifty 50"]
    idx = nf.index
    Z = pd.DataFrame(index=idx)
    sma50, sma200 = nf.rolling(50).mean(), nf.rolling(200).mean()
    mz = mom_z(nf)
    Z["trend"] = np.select(
        [(nf > sma50) & (sma50 > sma200), (nf < sma200) & (mz < 0)],
        [1, -1], 0)
    if "India VIX" in D:
        vix = D["India VIX"].reindex(idx).ffill()
        vp = vix.rolling(504, min_periods=100).rank(pct=True) * 100
        imp = (rv(nf, 30) - rv(nf, 100))
        Z["vol"] = np.select([(vp < 40) & (imp < 0), (vp > 75) | (imp > 4)],
                             [1, -1], 0)
    else:
        Z["vol"] = 0
    inr = D["USD-INR"].reindex(idx).ffill()
    ch21 = pct(inr, 21)
    Z["inr"] = np.select([ch21 < 1.0, ch21 > 2.0], [1, -1], 0)
    if "Brent" in D:
        b21 = pct(D["Brent"], 21).reindex(idx).ffill()
        Z["oil"] = np.select([b21 < -5, b21 > 5], [1, -1], 0)
    else:
        Z["oil"] = 0
    if "Gilt LT ETF" in D:
        g21 = pct(D["Gilt LT ETF"], 21).reindex(idx).ffill()
        Z["rates"] = np.select([g21 > 1.0, g21 < -1.0], [1, -1], 0)
    else:
        Z["rates"] = 0
    gsig = pd.Series(0.0, index=idx)
    if "S&P 500" in D:
        smz = mom_z(D["S&P 500"]).reindex(idx).ffill()
        mv = D["MOVE"].reindex(idx).ffill() if "MOVE" in D else None
        mvp = (mv.rolling(504, min_periods=100).rank(pct=True) * 100
               if mv is not None else pd.Series(50, index=idx))
        gsig = np.select([(smz > 0) & (mvp < 60), (smz < -1) | (mvp > 85)],
                         [1, -1], 0)
    Z["global"] = gsig
    Z = Z.dropna()
    Z["score"] = Z.sum(axis=1)
    return Z


SIGNAL_META = {
    "trend":  ("Nifty trend", "px vs 50/200d SMA + momo z",
               "cyclical beta, momentum longs", "capital preservation, hedges"),
    "vol":    ("Equity vol", "India VIX 2y %ile + RV impulse",
               "carry, high-beta, option selling", "defensives, long gamma"),
    "inr":    ("INR stability", "USD/INR 21d change",
               "FII-flow names, rate-sensitives", "exporters/IT as INR hedge"),
    "oil":    ("Oil (import lens)", "Brent 21d change",
               "OMCs, paints, aviation, CPI relief", "upstream oil, avoid importers"),
    "rates":  ("India yields (proxy)", "Gilt LT ETF 21d px",
               "banks, NBFCs, realty, autos", "duration-heavy, leveraged names"),
    "global": ("Global risk", "S&P momo z + MOVE %ile",
               "IT / export cyclicals", "low-beta, domestic defensives"),
}


def build_regime(book, D, F, A):
    if "Nifty 50" not in D or "USD-INR" not in D:
        return
    SEC, CODE = "Regime Read · What's Favorable in India", "MITRG1"
    Z = regime_signals(D, F)
    last = Z.iloc[-1]
    score = int(last["score"])
    stance = ("CONSTRUCTIVE — risk-on tilt" if score >= 3 else
              "DEFENSIVE — protect capital" if score <= -2 else
              "NEUTRAL / SELECTIVE — pick spots")
    stance_col = GREEN if score >= 3 else (RED if score <= -2 else ORANGE)
    # days in current stance band
    band = np.select([Z["score"] >= 3, Z["score"] <= -2], [1, -1], 0)
    n_days = 1
    for v in band[-2::-1]:
        if v != band[-1]:
            break
        n_days += 1
    fig = book.new_page(SEC, CODE, title="Regime read · six signals · what the tape favors", keys="regime signals stance favorable tilts constructive defensive")
    fig.text(0.5, 0.905, "SIX MECHANICAL SIGNALS · EACH +1 / 0 / −1 · "
             "COMPUTED FROM PRICES, NO EDITORIAL INPUT", ha="center",
             color=TXT, fontsize=8.5, fontweight="bold", family=SANS)
    cols = ["signal", "measured by", "state", "d", "favors when +",
            "favors when −"]
    colx = [0.045, 0.175, 0.395, 0.475, 0.53, 0.765]
    y0 = 0.868
    for cx, cname in zip(colx, cols):
        fig.text(cx, y0, cname, color=TEAL, fontsize=6.6, family=MONO)
    fig.lines.append(plt.Line2D([0.04, 0.96], [y0 - 0.008], color=LINE,
                                lw=0.8, transform=fig.transFigure))
    y = y0 - 0.03
    for key, (nm, how, plus, minus) in SIGNAL_META.items():
        v = int(last[key])
        st, d = ("+1 " + "▲", None) if v > 0 else (("−1 ▼", None) if v < 0
                                                   else ("0 →", None))
        dd = 1
        col = Z[key].values
        for x in col[-2::-1]:
            if x != col[-1]:
                break
            dd += 1
        c = GREEN if v > 0 else (RED if v < 0 else DIM)
        fig.patches.append(plt.Rectangle((0.04, y - 0.007), 0.92, 0.024,
                                         transform=fig.transFigure,
                                         facecolor=CARD, edgecolor=LINE,
                                         lw=0.4, zorder=0))
        for cx, v_, cc in zip(colx, [nm, how, st, f"d{dd}", plus, minus],
                              [TXT, DIM, c, DIM, GREEN, RED]):
            fig.text(cx, y, str(v_), color=cc, fontsize=6.4, family=MONO)
        y -= 0.030
    # net read box
    fig.patches.append(plt.Rectangle((0.04, y - 0.075), 0.92, 0.062,
                                     transform=fig.transFigure,
                                     facecolor=CARD, edgecolor=stance_col,
                                     lw=1.2, zorder=0))
    fig.text(0.06, y - 0.028, f"NET SCORE {score:+d} / ±6  →  {stance}",
             color=stance_col, fontsize=11, fontweight="bold", family=SANS)
    fig.text(0.06, y - 0.056,
             f"in this band {n_days} sessions · signals flip on published "
             "thresholds only — see method line on each row",
             color=DIM, fontsize=6.5, family=MONO)
    # favorable-now bullets (triggered rules, with the numbers that fired them)
    yy = y - 0.105
    fig.text(0.045, yy, "WHAT THE TAPE FAVORS TODAY", color=TXT,
             fontsize=9, fontweight="bold", family=SANS)
    yy -= 0.028
    bullets = []
    nf, inr = D["Nifty 50"], D["USD-INR"]
    if last["trend"] > 0:
        bullets.append(f"Trend up (Nifty {nf.iloc[-1]:,.0f} above rising 50d) "
                       "→ stay long cyclical beta; buy dips over chasing.")
    elif last["trend"] < 0:
        bullets.append("Trend broken (below 200d, momo negative) → cut beta, "
                       "favour FMCG / pharma / cash until the 200d reclaims.")
    if last["oil"] > 0:
        bullets.append(f"Brent down {pct(D['Brent'],21).iloc[-1]:+.1f}% in 21d "
                       "→ oil-importer complex favored: OMCs, paints, aviation; "
                       "CPI pressure eases, helps the RBI-cut case.")
    elif last["oil"] < 0:
        bullets.append(f"Brent up {pct(D['Brent'],21).iloc[-1]:+.1f}% in 21d → "
                       "import-bill headwind: trim OMCs/paints, watch INR and "
                       "CPI pass-through.")
    if last["inr"] > 0:
        bullets.append(f"INR steady/firm ({inr.iloc[-1]:.2f}, 21d "
                       f"{pct(inr,21).iloc[-1]:+.1f}%) → FII-sensitive names "
                       "breathe; rate-sensitives work.")
    elif last["inr"] < 0:
        bullets.append(f"INR weakening ({pct(inr,21).iloc[-1]:+.1f}% / 21d) → "
                       "IT / pharma exporters as the natural hedge.")
    if last["rates"] > 0:
        bullets.append("Gilt prices rising (yields drifting down) → duration "
                       "trade on: banks, NBFCs, realty, autos.")
    elif last["rates"] < 0:
        bullets.append("Gilt prices falling (yields up) → underweight "
                       "leveraged balance sheets; margin pressure for NBFCs.")
    if last["vol"] > 0:
        bullets.append("Vol compressed and decaying → carry-friendly tape; "
                       "hedges are cheap — keep a small tail hedge on.")
    elif last["vol"] < 0:
        bullets.append("Vol stressed → respect it: smaller size, defined-risk "
                       "structures over naked longs.")
    if last["global"] > 0:
        bullets.append("Global risk-on (S&P momo +, rates vol contained) → "
                       "IT and export cyclicals get the tailwind.")
    elif last["global"] < 0:
        bullets.append("Global risk-off → domestic-demand names over "
                       "export-facing; expect FII pressure days.")
    if not bullets:
        bullets = ["All six signals neutral — a genuinely mixed tape; "
                   "position light and let the next dashboard break the tie."]
    for b in bullets[:7]:
        fig.text(0.05, yy, "• " + b, color=TXT, fontsize=7.0, family=SANS)
        yy -= 0.024
    fig.text(0.045, max(yy - 0.012, 0.055),
             "Rules, not opinions: every bullet above is generated by a "
             "threshold on the numbers shown. The terminal's HMM/Goldilocks "
             "engine remains the structural view; this page is the "
             "price-implied cross-check.", color=DIM, fontsize=6.2, family=MONO)
    # evidence page
    def e1(ax):
        panel_title(ax, "Nifty 50 with 50d / 200d SMA · Trend Signal")
        t = D["Nifty 50"].tail(504)
        ax.plot(t.index, t.values, color=TEAL, lw=0.9)
        for w, c, lbl in [(50, ORANGE, "50d"), (200, BLUE, "200d")]:
            m = D["Nifty 50"].rolling(w).mean().tail(504)
            ax.plot(m.index, m.values, color=c, lw=0.9, ls="--")
        style_ax(ax); date_axis(ax, t)
        legend(ax, ([plt.Line2D([], [], color=TEAL, lw=2),
                     plt.Line2D([], [], color=ORANGE, lw=2, ls="--"),
                     plt.Line2D([], [], color=BLUE, lw=2, ls="--")],
                    ["Nifty", "50d", "200d"]))

    def e2(ax):
        panel_title(ax, "India VIX · 2y Percentile Bands · Vol Signal")
        if "India VIX" in D:
            v = D["India VIX"].tail(504)
            ax.plot(v.index, v.values, color=PURPLE, lw=0.9)
            full = D["India VIX"].tail(504)
            for q, c in [(0.4, GREEN), (0.75, RED)]:
                ax.axhline(full.quantile(q), color=c, lw=0.7, ls="--",
                           alpha=0.7)
            style_ax(ax); date_axis(ax, v)
            legend(ax, ([plt.Line2D([], [], color=PURPLE, lw=2),
                         plt.Line2D([], [], color=GREEN, lw=1, ls="--"),
                         plt.Line2D([], [], color=RED, lw=1, ls="--")],
                        ["India VIX", "40th %ile", "75th %ile"]))
        else:
            style_ax(ax)

    def e3(ax):
        panel_title(ax, "Signal Components · Last 1 Year (stacked)")
        zz = Z.tail(252)
        bottom_pos = np.zeros(len(zz))
        bottom_neg = np.zeros(len(zz))
        colors = [TEAL, PURPLE, BLUE, ORANGE, GREEN, PINK]
        hs, ls = [], []
        for (k, c) in zip(["trend", "vol", "inr", "oil", "rates", "global"],
                          colors):
            v = zz[k].values.astype(float)
            pos = np.where(v > 0, v, 0)
            neg = np.where(v < 0, v, 0)
            ax.bar(zz.index, pos, bottom=bottom_pos, color=c, width=1.0)
            ax.bar(zz.index, neg, bottom=bottom_neg, color=c, width=1.0,
                   alpha=0.65)
            bottom_pos += pos
            bottom_neg += neg
            hs.append(plt.Line2D([], [], color=c, lw=3)); ls.append(k)
        style_ax(ax); date_axis(ax, zz)
        legend(ax, (hs, ls), ncol=6)

    def e4(ax):
        panel_title(ax, "Net Score · Regime Ribbon (1 Year)")
        sc = Z["score"].tail(252)
        cols_ = [GREEN if v >= 3 else (RED if v <= -2 else ORANGE)
                 for v in sc.values]
        ax.bar(sc.index, sc.values, color=cols_, width=1.0)
        ax.axhline(3, color=GREEN, lw=0.6, ls="--", alpha=0.6)
        ax.axhline(-2, color=RED, lw=0.6, ls="--", alpha=0.6)
        style_ax(ax); date_axis(ax, sc)
        legend(ax, ([plt.Line2D([], [], color=GREEN, lw=3),
                     plt.Line2D([], [], color=ORANGE, lw=3),
                     plt.Line2D([], [], color=RED, lw=3)],
                    ["constructive ≥+3", "neutral", "defensive ≤−2"]))
    book._next_title = ("Regime evidence · trend, vix bands, ribbon", "regime evidence sma vix ribbon score")
    quad_page(book, SEC, CODE, [e1, e2, e3, e4])


def build_disclaimer(book):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    book.figs.append(fig)
    book.codes.append(("", "MITEND"))
    book.titles.append(("Disclaimer", "legal"))
    fig.patches.append(plt.Rectangle((0.09, 0.885), 0.004, 0.022,
                                     transform=fig.transFigure, facecolor=TEAL))
    fig.text(0.105, 0.888, "Disclaimer", color=TXT, fontsize=11,
             fontweight="bold")
    txt = ("The information in this publication is provided for informational and "
           "educational purposes only and is believed to be reliable, but its "
           "accuracy and completeness are not guaranteed. Nothing herein "
           "constitutes investment advice, an offer, or a solicitation to buy or "
           "sell any security, derivative, digital asset, or other financial "
           "instrument, nor a recommendation suited to any specific reader. All "
           "figures are drawn from the day's computed data set at the time of "
           "generation (Yahoo Finance daily closes) and may be delayed, revised, "
           "or superseded. Markets involve risk, including the possible loss of "
           "principal; past performance and statistical relationships do not "
           "guarantee future results. Readers should conduct their own research "
           "and consult a qualified financial adviser before making any "
           "investment decision. Built by Arhan Boyd & Gautam Nowlakha · "
           f"{BRAND_LONG} · {SITE}.")
    fig.text(0.09, 0.845, "\n".join(_wrap(txt, 96)), color=DIM, fontsize=8,
             va="top", family=SANS, linespacing=1.7)
    fig.text(0.09, 0.09, BRAND_LONG, color=TEAL, fontsize=8, family=MONO)


def _wrap(t, n):
    words, lines, cur = t.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return lines


# ── output ──────────────────────────────────────────────────────────────────

HTML_TMPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MACROINTEL · India Daily Tear Sheet · {asof}</title>
<style>
 body{{margin:0;background:{bg};color:{txt};font-family:'IBM Plex Mono',ui-monospace,monospace}}
 .hd{{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;
     border-bottom:2px solid {teal};position:sticky;top:0;background:{bg};z-index:5}}
 .hd b{{color:{teal};letter-spacing:2px;font-size:13px}}
 .hd span{{color:{dim};font-size:11px}}
 .hd a{{color:{bg};background:{teal};text-decoration:none;font-weight:700;font-size:11px;
     padding:6px 12px;border-radius:4px}}
 .pg{{max-width:1240px;margin:14px auto;display:block;width:calc(100% - 24px);
     border:1px solid {line};border-radius:6px}}
 .nav{{max-width:1240px;margin:10px auto;padding:0 12px;font-size:10px;color:{dim}}}
 .nav a{{color:{teal};text-decoration:none;margin-right:12px}}
</style></head><body>
<div class="hd"><div><b>MACROINTEL</b> <span>· India Daily Tear Sheet · pricing as of {asof}</span></div>
<a href="tearsheet.pdf" download>⬇ PDF</a></div>
<div class="nav">{nav}</div>
{pages}
<div class="nav" style="margin-bottom:30px">macrointel.in · generated {gen} · educational information, not investment advice</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--data")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    if args.demo:
        D, F = demo_data(), demo_fred()
    elif args.data:
        D, F = load_json(args.data), fetch_fred()
    else:
        D, F = fetch_live(), fetch_fred()
    if "Nifty 50" not in D or "USD-INR" not in D:
        sys.exit("FATAL: core series (Nifty 50 / USD-INR) missing — aborting "
                 "so we never publish an empty tear sheet.")
    D = add_derived(D)
    A = parse_terminal_anchors() if not args.demo else {
        "repo": 5.25, "cpi": 4.38, "mibor_on": 5.85, "mibor_3m": 6.63,
        "in10y": 6.84,
        "ois": [(0.03, 5.85), (1, 5.82), (3, 5.78), (6, 5.70), (12, 5.58),
                (24, 5.52), (36, 5.55), (60, 5.68)]}
    asof = max(s.index[-1] for s in D.values()).strftime("%d-%b-%Y")
    book = Book(asof, demo=args.demo)

    build_regime(book, D, F, A)          # the read comes first
    build_india_equities(book, D)
    build_heavyweights(book, D)
    build_fx(book, D)
    build_rates(book, D, F, A)
    build_commodities(book, D)
    build_disclaimer(book)
    book.finish_footers()

    os.makedirs(args.outdir, exist_ok=True)
    pdf_path = os.path.join(args.outdir, "tearsheet.pdf")
    with PdfPages(pdf_path) as pdf:
        for fig in book.figs:
            pdf.savefig(fig, dpi=DPI_PDF)
    # HTML with embedded PNGs + section anchors + per-page files & manifest
    pages_dir = os.path.join(args.outdir, "tearsheet_pages")
    os.makedirs(pages_dir, exist_ok=True)
    for f in os.listdir(pages_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(pages_dir, f))
    manifest = []
    imgs, nav, seen = [], [], set()
    for pi, (fig, (sec, code)) in enumerate(zip(book.figs, book.codes)):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI_PNG)
        png = buf.getvalue()
        fname = f"p{pi+1:02d}.png"
        with open(os.path.join(pages_dir, fname), "wb") as pf:
            pf.write(png)
        t_, k_ = book.titles[pi] if pi < len(book.titles) else ("", "")
        manifest.append({
            "n": pi + 1, "file": f"tearsheet_pages/{fname}",
            "section": sec or "Disclaimer", "code": code,
            "title": t_, "keywords": f"{sec} {code} {t_} {k_}".lower()})
        b64 = base64.b64encode(png).decode()
        anchor = ""
        if sec and code not in seen:
            seen.add(code)
            anchor = f' id="{code}"'
            nav.append(f'<a href="#{code}">{sec.split("·")[0].strip()}</a>')
        imgs.append(f'<img class="pg"{anchor} alt="{sec}" '
                    f'src="data:image/png;base64,{b64}">')
        plt.close(fig)
    html = HTML_TMPL.format(
        asof=asof, bg=BG, txt=TXT, teal=TEAL, dim=DIM, line=LINE,
        nav=" ".join(nav), pages="\n".join(imgs),
        gen=dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    with open(os.path.join(args.outdir, "tearsheet.html"), "w") as f:
        f.write(html)
    with open(os.path.join(args.outdir, "tearsheet_manifest.json"), "w") as f:
        json.dump({"asof": asof, "pages": manifest}, f)
    # dated archive
    arch = os.path.join(args.outdir, "tearsheets")
    os.makedirs(arch, exist_ok=True)
    tag = max(s.index[-1] for s in D.values()).strftime("%Y%m%d")
    import shutil
    shutil.copy(pdf_path, os.path.join(arch, f"tearsheet_{tag}.pdf"))
    # prune archive: keep the 30 most recent dated copies
    old = sorted(f for f in os.listdir(arch)
                 if f.startswith("tearsheet_") and f.endswith(".pdf"))[:-30]
    for f in old:
        os.remove(os.path.join(arch, f))
    print(f"OK: {len(book.figs)} pages · as of {asof} → tearsheet.pdf / "
          f"tearsheet.html / tearsheets/tearsheet_{tag}.pdf")


if __name__ == "__main__":
    main()
