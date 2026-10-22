#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MacroIntel v145 · THE ENGINE — one score, three horizons, every listed share; the regime → asset map; the pairs.

Why this file exists
    v143 printed "NO TRADE" on most names because five separate lists each waited for a
    mechanical rule to fire. This is the one place every verdict on the page comes from:
    the Markets cards, the research page, the top picks, Ask MacroIntel and the arena's
    candidate pool all read engine.json. One score → no contradictions.

What it computes, for every NSE name with a bhavcopy line (≈2,200) and every F&O name:
    the tape        1/5/20/60/120/250-session returns, distance from the 50/200-day,
                    52-week position, realised volatility, extension, drawdown
    macro DNA       the share's measured betas to the Nifty, the rupee, Brent, the gilt
                    (rates) and India VIX (ridge on weekly returns), its R², and its record
                    in each macro regime (Reflation / Goldilocks / Stagflation /
                    Disinflation, labelled off the same CPI×IIP anchor path ml_models uses)
    the wind        what the last month's macro moves explained of the share's move
    fundamentals    Yahoo's profile (P/E, P/B, ROE, margins, growth, debt, promoter
                    holding, dividend yield, the business in a paragraph) — refreshed on a
                    rotation, cached in fundamentals.json, never required
    the scores      Trend · Macro · Quality · Flow · Risk · the contenders model →
                    one 0–100 score per horizon
    the verdicts    INTRADAY (today) · SHORT TERM (5–60 sessions) · LONG TERM (12 months):
                    BUY / SELL / ACCUMULATE / AVOID with entry, stop, target, size and the
                    reasons — never WAIT, never HOLD (HOLD exists only when you ask about
                    a share you already own, in Ask MacroIntel)
    F&O             buy N lots or nothing, ₹ risk and ₹ profit potential per lot
    the picks       5 intraday · 5 F&O · 5 short-term buys · 5 short-term sells · 5 long-term
                    accumulates — the short and long lists are sticky (hysteresis), so they
                    do not churn every day
    the sectors     every industry: breadth, equal-weight returns vs the Nifty, the average
                    DNA, the regime edge, the leaders, a sector verdict
    the record      every pick frozen in history/engine_<date>.json and scored at 5, 20 and
                    60 sessions — the hit rate is printed on the page
    the shock       the coefficients the page's simulator uses (crude to $120, RBI +50bp,
                    rupee to 100, FII selling) for every share and sector

Sources, in order:  Yahoo (yfinance) 3y weekly for the universe + 1y daily for the top
turnover and F&O names → engine_prices.json (the last good panel, carried when Yahoo is
quiet) → history_1y.json (the page's own weekly/daily history). The engine never fails the
pipeline: every stage is wrapped, and an empty stage prints what it could not do.

Usage:
    python engine.py                         # the page in cwd, online if it can
    python engine.py --offline               # cached/page data only (the regression suite)
    python engine.py --budget 420            # seconds for Yahoo (default 480)
    python engine.py --fund-budget 150       # seconds for the fundamentals rotation
    python engine.py --max-age 6             # reuse engine_prices.json if younger than 6 h (the workflow caches it)
"""
import os, re, sys, json, math, time, datetime as dt
import numpy as np
import pandas as pd

VERSION = "v148"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PAGE = "macro_intelligence_terminal.html"
OUT = "engine.json"
FUND_FILE = "fundamentals.json"
PRICES_FILE = "engine_prices.json"
# v148 · the panels: ten years weekly for EVERY NSE name (the regime record needs more than one cycle; a share page needs its
# whole history), two years daily for the traded names (the movers model learns on twice the sessions)
WEEKLY_PERIOD = "10y"
DAILY_PERIOD = "2y"
DNA_WEEKS = 156            # the betas are measured on the last three years; the regime record uses everything
HIST_DIR = "history"
LIQUID_CR = 5.0          # ₹ cr a day — the modelled universe
INTRA_CR = 40.0          # ₹ cr a day — intraday needs liquidity
PICK_CR = 100.0          # ₹ cr a day — the top picks must be investable (≈ the 250 most traded names)
RISK_PCT = 1.0           # % of capital risked per trade (sizing)
BOOK = 1_000_000         # the reference book for lots and sizes (₹10 lakh)
IDX_LOT = {"NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "MIDCPNIFTY": 120, "NIFTYNXT50": 25}   # NSE lots as revised Oct–Dec 2025 — verify against the exchange master; the stock lots ride from the bhavcopy

MACRO = {"nifty": "^NSEI", "inr": "INR=X", "brent": "BZ=F", "vix": "^INDIAVIX", "gilt": "GILT5YBEES.NS",
         "spx": "^GSPC", "dxy": "DX-Y.NYB", "gold": "GC=F", "us10y": "^TNX"}
FACTORS = ["nifty", "inr", "brent", "rates", "vix"]     # the DNA (rates = −gilt price)
FACTOR_LABEL = {"nifty": "the Nifty", "inr": "the rupee (USD/INR)", "brent": "Brent", "rates": "rates (10Y yields)", "vix": "India VIX"}
GILT_DURATION = 4.5       # years — the 5Y gilt ETF; ΔP/P ≈ −D·Δy

# the same CPI × IIP anchor path ml_models.py trains the regime model on (point-in-time shifted)
REGIME_ANCHORS = np.array([(2015.0, 5.3, 3.5), (2016.5, 5.8, 1.5), (2017.6, 2.4, 4.3),
                           (2018.7, 3.7, 4.5), (2019.7, 3.2, -1.4), (2020.3, 7.2, -57.3),
                           (2021.4, 6.3, 134.0), (2022.3, 7.8, 7.1), (2022.95, 5.7, 5.0),
                           (2023.9, 5.6, 2.4), (2024.8, 5.5, 3.5), (2025.6, 3.1, 3.5),
                           (2026.3, 3.4, 4.0), (2026.45, 3.93, 4.1), (2026.55, 4.38, 7.3),
                           (2026.6, 4.45, 7.3), (2026.7, 4.82, 6.7)])

LOG = []
N_SHARDS = 8
CHAIN = {}          # options_chain.json's underlyings (set in main)
REPO_RATE = 5.5     # the carry for the option pricing (MACRO_LIVE.repo, set in main)
TAPE_KEYS = ["src", "r1", "r5", "r20", "r60", "r120", "r250", "vs50", "vs200", "pos52", "sig1d", "sig5d", "ext20", "dd", "hi52", "lo52", "m50", "m200", "vol_ratio", "n",
             "since", "dlv", "dlv_avg", "dlv_z", "yrs", "trunc"]   # v148 · the first date on the tape, the delivery read, the years of history, 1 when the panel (not the listing) sets the start
TAPE_SRC = {"bhavcopy": 0, "weekly": 1, "daily": 2}
SC_KEYS = ["short", "long", "intra", "T", "TL", "M", "ML", "Q", "F", "C", "R"]


def shard_of(sym):
    return sum(ord(c) for c in str(sym)) % N_SHARDS


def log(msg):
    print("  " + msg)
    LOG.append(msg)


def now_ist():
    return dt.datetime.now(IST)


def _f(x, nd=2):
    try:
        v = float(x)
        if not math.isfinite(v):
            return None
        return round(v, nd)
    except Exception:
        return None


def label_regime(cpi, iip):
    if cpi < 4 and iip >= 3:
        return "Goldilocks"
    if cpi >= 4 and iip >= 3:
        return "Reflation"
    if cpi >= 4:
        return "Stagflation"
    return "Disinflation"


def regime_labels(index):
    a = REGIME_ANCHORS
    yrs = index.year + (index.dayofyear / 365.25)
    cpi = np.interp(yrs, a[:, 0] + 0.125, a[:, 1])
    iip = np.interp(yrs, a[:, 0] + 0.125, a[:, 2])
    return pd.Series([label_regime(c, i) for c, i in zip(cpi, iip)], index=index)


# ─────────────────────────────────────────────────────────────────────────────
# 1 · the page's own blocks
# ─────────────────────────────────────────────────────────────────────────────
def _block(html, var):
    m = re.search(r"window\.%s\s*=\s*(\{.*?\});" % re.escape(var), html, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _const(html, var):
    m = re.search(r"const %s\s*=\s*(\{.*?\});\n" % re.escape(var), html, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}


def _loose(html, var):
    """MACRO_LIVE is a JS literal, not JSON: read its scalar fields"""
    m = re.search(r"window\.%s\s*=\s*\{(.*?)\};" % re.escape(var), html, re.S)
    if not m:
        return {}
    out = {}
    for k, v in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(-?[0-9][0-9.]*)", m.group(1)):
        try:
            out[k] = float(v)
        except Exception:
            pass
    return out


def _tiles(html, var):
    """const IN_IDX={"Nifty 50":{p:..,d:..,m:..},...}"""
    m = re.search(r"const %s=\{(.*?)\};" % re.escape(var), html, re.S)
    out = {}
    if not m:
        return out
    for nm, p, d in re.findall(r'"([^"]+)":\{p:([-\d.]+),d:([-\d.]+)', m.group(1)):
        out[nm] = {"p": _f(p), "d": _f(d)}
    return out


def read_page(path=PAGE):
    html = open(path, encoding="utf-8").read()
    B = {v: _block(html, v) for v in ("MOVERS_LIVE", "BSE_LIVE", "RISK_LIVE", "FNO_LIVE", "OPTIONS_LIVE",
                                      "REGIME_LIVE", "MACRO_X", "FLOWS_LIVE", "PREDICTIONS", "RECS_LIVE", "ALERTS", "NEWS_LIVE")}
    B["ML_OUTPUT"] = _const(html, "ML_OUTPUT")
    B["MACRO_LIVE"] = _loose(html, "MACRO_LIVE")
    B["IN_IDX"] = _tiles(html, "IN_IDX")
    B["FX"] = _tiles(html, "FX")
    B["ENERGY"] = _tiles(html, "ENERGY")
    B["html_len"] = len(html)
    return B


# ─────────────────────────────────────────────────────────────────────────────
# 2 · the universe
# ─────────────────────────────────────────────────────────────────────────────
def yahoo_sector(ys, ind):
    """Yahoo's sector/industry → the page's own sector vocabulary"""
    ys = (ys or "").lower(); ind = (ind or "").lower()
    if "bank" in ind:
        return "Banking"
    if any(k in ind for k in ("credit", "capital markets", "insurance", "asset management", "mortgage", "financial", "exchange")):
        return "NBFC"
    if "software" in ind or "information technology" in ind or ys == "technology":
        return "IT"
    if ys == "healthcare" or "drug" in ind or "pharma" in ind or "medical" in ind or "biotech" in ind or "diagnostic" in ind:
        return "Pharma"
    if "auto" in ind or "vehicle" in ind or "tire" in ind:
        return "Auto"
    if "textile" in ind or "apparel manufacturing" in ind:
        return "Textiles"
    if ys == "consumer defensive" or any(k in ind for k in ("packaged food", "beverage", "household", "tobacco", "personal product", "confection", "grocery", "farm product")):
        return "FMCG"
    if ys == "real estate" or "real estate" in ind:
        return "Realty"
    if "telecom" in ind:
        return "Telecom"
    if any(k in ind for k in ("entertainment", "media", "publishing", "broadcasting", "advertising", "gaming")):
        return "Media Entertainment & Publication"
    if "chemical" in ind or "agricultural input" in ind or "fertil" in ind:
        return "Chemicals"
    if any(k in ind for k in ("steel", "aluminum", "copper", "metal", "mining", "gold", "silver")):
        return "Metal"
    if "building material" in ind or "cement" in ind:
        return "Cement & Building"
    if "paper" in ind or "lumber" in ind or "wood" in ind:
        return "Forest Materials"
    if ys == "energy" or "oil" in ind or "coal" in ind or "gas" in ind and "utilit" not in ind:
        return "Energy"
    if "electric" in ind and "utilit" in ind or "renewable" in ind or "power" in ind:
        return "Power"
    if ys == "utilities" or "utilit" in ind or "water" in ind:
        return "Utilities"
    if any(k in ind for k in ("engineering", "construction", "infrastructure", "airport")):
        return "Infra"
    if any(k in ind for k in ("airline", "marine", "shipping", "railroad", "trucking", "logistic", "integrated freight", "consulting", "staffing", "security", "business services", "education", "waste")):
        return "Services"
    if ys == "industrials":
        return "Capital Goods"
    if "conglomerate" in ind:
        return "Diversified"
    if ys == "consumer cyclical" or ys == "communication services":
        return "Consumer"
    if ys == "basic materials":
        return "Chemicals"
    return "Other"


ETF_SYMS = {"MON100", "MONQ50", "MAFANG", "MASPTOP50", "MAHKTECH", "MOM100", "MOM30IETF", "MOM50", "MOMOMENTUM", "MOREALTY", "MOVALUE", "MOQUALITY", "MOLOWVOL",
            "MOHEALTH", "MOGSEC", "MOCAPITAL", "MODEFENCE", "MONIFTY500", "MOSMALL250", "SMALLCAP", "ALPHA", "ALPHAETF", "HEALTHY", "PSUBANK", "ICICIB22", "LIQUIDCASE", "TOP100CASE",
            "HDFCGOLD", "HDFCSILVER", "HDFCNIFTY", "HDFCSENSEX", "HDFCNEXT50", "HDFCMID150", "HDFCSML250", "HDFCNIFBAN", "HDFCPVTBAN", "HDFCPSUBK", "HDFCNIFIT", "HDFCGROWTH",
            "HDFCVALUE", "HDFCLOWVOL", "HDFCMOMENT", "HDFCQUAL", "HDFCBSE500", "HDFCNIF100", "HDFCLIQUID", "TATAGOLD", "TATSILV", "TATANIFTY", "AXISGOLD", "AXISNIFTY", "AXISBNKETF",
            "AXISTECETF", "AXISHCETF", "AXISCETF", "AXISILVER", "AXISBPSETF", "KOTAKGOLD", "KOTAKNIFTY", "KOTAKBKETF", "KOTAKIT", "KOTAKPSUBK", "KOTAKNV20", "KOTAKALPHA", "KOTAKSILVE",
            "KOTAKMNC", "KOTAKLOVOL", "KOTAKCONS", "KOTAKMID50", "QGOLDHALF", "QNIFTY", "SBIETFCON", "SBIETFIT", "SBIETFPB", "SBIETFQLTY", "SBISILVER", "SBIGOLDETF", "SBINEQWETF",
            "SBIETFPVBK", "SETFNIF50", "SETFNIFBK", "SETFNN50", "SETFGOLD", "SETF10GILT", "UTINIFTETF", "UTIBANKETF", "UTISXN50", "UTISENSETF", "UTIGOLDETF", "UTINEXT50",
            "BSLGOLDETF", "BSLNIFTY", "BSLSENETFG", "ABSLBANETF", "ABSLNN50ET", "ABSLLIQUID", "ABSLPSE", "ABGSEC", "LICNETFGSC", "LICNETFN50", "LICNETFSEN", "LICNFNHGP", "LICMFGOLD",
            "IVZINGOLD", "IVZINNIFTY", "GOLDSHARE", "GOLDCASE", "SILVERADD", "SILVRETF", "SILVERCASE", "GROWWGOLD", "GROWWSLVR", "GROWWN200", "GROWWEV",
            "GROWWRAIL", "GROWWDEFNC", "NIFTYQLITY", "NIFTYBETF", "NIFTY50ADD", "NIF100BEES", "LOWVOL1", "MOMENTUM", "MOMENTUM50", "MIDCAPETF", "MIDQ50ADD",
            "MIDSELIETF", "SENSEXADD", "SENSEXETF", "SENSEXIETF", "BANKETF", "BANKETFADD", "BANKNIFTY1", "BANKPSU", "PVTBANKADD", "ITETF", "ITETFADD", "HEALTHIETF",
            "HEALTHADD", "PHARMABEES", "AUTOIETF", "AUTOBEES", "FMCGIETF", "METALIETF", "OILIETF", "INFRAIETF", "COMMOIETF", "ENERGYIETF", "EVINDIA", "MAKEINDIA", "DIVOPPBEES", "QUALITY30", "VALUE30", "EQUAL50ADD", "NIFTYIETF", "NEXT50IETF", "MIDCAPIETF", "SMALLCAPIETF", "LIQUIDIETF", "LIQUIDETF", "LIQUIDADD", "LIQUIDSBI",
            "LIQUIDBETF", "LIQUIDSHRI", "LIQUIDPLUS", "LIQUID1", "GILT5YBEES", "LTGILTBEES", "GSEC10IETF", "GSEC10YEAR", "GSEC5IETF", "SDL26BEES", "LIQGRWBEES", "EBANK",
            "EGOLD", "ESILVER", "CPSEETF", "BBETF0432", "EBBETF0425", "EBBETF0430", "EBBETF0431", "EBBETF0433", "SHARIABEES", "MANUFGBEES", "SNXT50BEES", "SNXT30BEES", "SENSEXBEES",
            "INFRABEES", "CONSUMBEES", "PSUBNKBEES", "HNGSNGBEES", "JUNIORBEES", "BANKBEES", "GOLDBEES", "SILVERBEES", "LIQUIDBEES", "NIFTYBEES", "ITBEES", "MID150BEES", "GOLDIETF",
            "SILVERIETF", "LOWVOLIETF", "QUAL30IETF", "VAL30IETF", "PVTBANIETF", "BANKIETF", "CONSUMIETF", "TNIDETF", "NETFIT", "NPBET", "AONENIFTY", "AONETOTAL"}
ETF_RE = re.compile(r"(BEES|ETF|IETF|CASE)$|ETF")


def is_etf(sym, nm, fund=None):
    s = str(sym).upper(); n = str(nm or "").upper()
    if s in ETF_SYMS or ETF_RE.search(s):
        return True
    if "MUTUAL FUND" in n or " ETF" in (" " + n) or n.endswith(" FUND") or "BEES" in n:
        return True
    try:
        if str((fund or {}).get("qtype") or "").upper() == "ETF":
            return True
    except Exception:
        pass
    return False


def build_universe(B, FUND=None):
    mv = (B["MOVERS_LIVE"] or {}).get("all") or {}
    rk = (B["RISK_LIVE"] or {}).get("names") or {}
    fno = {str(r.get("s")).upper(): r for r in ((B["FNO_LIVE"] or {}).get("stocks") or []) if r.get("s")}
    opt = (B["OPTIONS_LIVE"] or {}).get("u") or {}
    U = {}
    for s, row in mv.items():
        try:
            d1, w1, turn, close = row[0], row[1], row[2], row[3]
        except Exception:
            continue
        if not close:
            continue
        r = rk.get(s) or {}
        U[s] = {"nm": r.get("nm") or s, "sector": r.get("sector") or "Other", "px": _f(close), "d1": _f(d1), "w1": _f(w1),
                "turn": _f(turn, 1), "fno": s in fno, "x": "NSE"}
    for s, r in rk.items():
        if s not in U and r.get("px"):
            U[s] = {"nm": r.get("nm") or s, "sector": r.get("sector") or "Other", "px": _f(r.get("px")), "d1": None, "w1": None,
                    "turn": None, "fno": s in fno, "x": "NSE"}
    for s in fno:
        if s not in U:
            f = fno[s]
            U[s] = {"nm": s, "sector": (rk.get(s) or {}).get("sector") or "Other", "px": _f(f.get("u") or f.get("c")), "d1": _f(f.get("d")), "w1": None,
                    "turn": None, "fno": True, "x": "NSE"}
    # the sector: the page's own map first, Yahoo's profile where the page says Other
    fn = (FUND or {}).get("names") or {}
    n_map = 0
    for s, u in U.items():
        f = fn.get(s) or {}
        if u["sector"] in ("Other", "—", None) and (f.get("ysector") or f.get("industry")):
            ys = yahoo_sector(f.get("ysector"), f.get("industry"))
            if ys != "Other":
                u["sector"] = ys; n_map += 1
        if f.get("industry"):
            u["industry"] = f["industry"]
        if f.get("lname"):
            u["nm"] = f["lname"][:60] if u["nm"] == s else u["nm"]
    if n_map:
        log("sectors: %d names mapped from Yahoo's profile" % n_map)
    # v145 · exchange-traded funds are their own sector: scored like anything else (search finds them), but kept
    # out of the stock lists and the books — they belong to the allocation map (alloc_block)
    n_etf = 0
    for s, u in U.items():
        if is_etf(s, u["nm"], (fn.get(s) or {})):
            u["sector"] = "ETF"; n_etf += 1
    if n_etf:
        log("ETFs: %d names set aside as a sector of their own" % n_etf)
    # BSE-only names: a price, a day, a name — thin, said so on the page
    bse = (B["BSE_LIVE"] or {}).get("all") or {}
    for s, row in bse.items():
        if s in U:
            continue
        try:
            U[s] = {"nm": (row[4] or s).title(), "sector": "Other", "px": _f(row[0]), "d1": _f(row[1]), "w1": None,
                    "turn": _f((row[2] or 0) / 100.0, 2), "fno": False, "x": "BSE", "code": row[3]}
        except Exception:
            continue
    return U, fno, opt


# ─────────────────────────────────────────────────────────────────────────────
# 3 · prices — Yahoo, the carried panel, the page's history
# ─────────────────────────────────────────────────────────────────────────────
def _chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def _vol_frame(raw, syms):
    try:
        if raw is None or len(raw) == 0:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            if "Volume" not in raw.columns.get_level_values(0):
                return None
            df = raw["Volume"]
        else:
            if "Volume" not in raw.columns:
                return None
            df = raw[["Volume"]].rename(columns={"Volume": syms[0]})
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(df.index, "tz", None) is not None else pd.to_datetime(df.index)
        return df
    except Exception:
        return None


DVOL = None   # the daily volume panel (set by fetch / the cache; None offline)


def _close_frame(raw, syms):
    if raw is None or len(raw) == 0:
        return None
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = raw.columns.get_level_values(0)
        if "Close" in lv0:
            df = raw["Close"]
        elif "Adj Close" in lv0:
            df = raw["Adj Close"]
        else:
            return None
    else:
        col = "Close" if "Close" in raw.columns else ("Adj Close" if "Adj Close" in raw.columns else None)
        if col is None:
            return None
        df = raw[[col]].rename(columns={col: syms[0]})
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(df.index, "tz", None) is not None else pd.to_datetime(df.index)
    return df


def fetch_yahoo(syms_w, syms_d, budget=480):
    import yfinance as yf
    t0 = time.time()
    W = []
    ysyms = [s + ".NS" for s in syms_w] + list(MACRO.values())
    for ch in _chunks(ysyms, 180):
        if time.time() - t0 > budget * 0.65:
            log("weekly: budget reached at %d symbols" % (len(W) and sum(x.shape[1] for x in W)))
            break
        try:
            raw = yf.download(ch, period=WEEKLY_PERIOD, interval="1wk", progress=False, threads=True, auto_adjust=True, group_by="column")
            df = _close_frame(raw, ch)
            if df is not None:
                W.append(df)
        except Exception as e:
            log("weekly chunk failed (%s)" % type(e).__name__)
    if not W:
        raise RuntimeError("no weekly data")
    W = pd.concat(W, axis=1)
    W = W.loc[:, ~W.columns.duplicated()]
    W.columns = [str(c).replace(".NS", "") for c in W.columns]
    D = None
    global DVOL
    try:
        Dl = []; Vl = []
        dsyms = [s + ".NS" for s in syms_d] + list(MACRO.values())
        for ch in _chunks(dsyms, 180):
            if time.time() - t0 > budget:
                log("daily: budget reached")
                break
            raw = yf.download(ch, period=DAILY_PERIOD, interval="1d", progress=False, threads=True, auto_adjust=True, group_by="column")
            df = _close_frame(raw, ch)
            if df is not None:
                Dl.append(df)
            dv = _vol_frame(raw, ch)
            if dv is not None:
                Vl.append(dv)
        if Dl:
            D = pd.concat(Dl, axis=1)
            D = D.loc[:, ~D.columns.duplicated()]
            D.columns = [str(c).replace(".NS", "") for c in D.columns]
        if Vl:
            V = pd.concat(Vl, axis=1)
            V = V.loc[:, ~V.columns.duplicated()]
            V.columns = [str(c).replace(".NS", "") for c in V.columns]
            DVOL = V
    except Exception as e:
        log("daily failed (%s)" % type(e).__name__)
    return W, D


def save_prices(W, D):
    try:
        o = {"updated": now_ist().strftime("%Y-%m-%d %H:%M"),
             "wdates": [d.strftime("%Y%m%d") for d in W.index],
             "w": {c: [(_f(v) if pd.notna(v) else None) for v in W[c].values] for c in W.columns}}
        if D is not None:
            o["ddates"] = [d.strftime("%Y%m%d") for d in D.index]
            o["d"] = {c: [(_f(v) if pd.notna(v) else None) for v in D[c].values] for c in D.columns}
        if DVOL is not None:
            o["vdates"] = [d.strftime("%Y%m%d") for d in DVOL.index]
            o["dv"] = {c: [(int(v) if pd.notna(v) else None) for v in DVOL[c].values] for c in DVOL.columns}
        json.dump(o, open(PRICES_FILE, "w"), separators=(",", ":"))
    except Exception as e:
        log("prices cache not written (%s)" % type(e).__name__)


def load_prices_cache(max_age_h=None):
    try:
        o = json.load(open(PRICES_FILE))
        if max_age_h is not None:
            age_h = (now_ist() - dt.datetime.strptime(o["updated"], "%Y-%m-%d %H:%M").replace(tzinfo=IST)).total_seconds() / 3600
            if age_h > max_age_h:
                return None, None, None
        W = pd.DataFrame(o["w"], index=pd.to_datetime(o["wdates"], format="%Y%m%d"))
        D = pd.DataFrame(o["d"], index=pd.to_datetime(o["ddates"], format="%Y%m%d")) if o.get("d") else None
        global DVOL
        if o.get("dv"):
            DVOL = pd.DataFrame(o["dv"], index=pd.to_datetime(o["vdates"], format="%Y%m%d"))
        return W, D, "carried · engine_prices.json %s" % o.get("updated")
    except Exception:
        return None, None, None


def load_page_history():
    """history_1y.json: weekly closes for ~2,200 names (53 weeks) + daily closes for ~100 (368 days)"""
    o = json.load(open("history_1y.json"))
    W = pd.DataFrame({k.replace(".NS", ""): v for k, v in (o.get("wide") or {}).items()},
                     index=pd.to_datetime([str(d) for d in o["wdates"]], format="%Y%m%d"))
    D = pd.DataFrame({k.replace(".NS", ""): v for k, v in (o.get("series") or {}).items()},
                     index=pd.to_datetime([str(d) for d in o["dates"]], format="%Y%m%d"))
    # the macro factors weekly, resampled off the daily series
    for k, sym in MACRO.items():
        if sym in D.columns:
            W[sym] = D[sym].resample("W-FRI").last().reindex(W.index, method="nearest")
    return W, D, "the page's history_1y.json (%d weekly names, %d daily)" % (W.shape[1], D.shape[1])


BSE_FILE = "engine_prices_bse.json"


def bse_rotation(U, W, offline, budget_s=100, n_per_pass=160, fresh_days=7):
    """v148 · BSE-only names get a weekly tape too: <code>.BO from Yahoo, ten years, up to n_per_pass names a pass (the most
    traded first, then the stalest), kept in their own cache — the NSE panel is refetched every six hours, this one lives on
    between passes. Returns W with the BSE columns joined on."""
    C = {"names": {}, "wdates": []}
    try:
        C = json.load(open(BSE_FILE))
        C.setdefault("names", {}); C.setdefault("wdates", [])
    except Exception:
        pass
    names = C["names"]
    old = None
    try:
        if names and C["wdates"]:
            old = pd.DataFrame({sy: r["w"] for sy, r in names.items() if len(r.get("w") or []) == len(C["wdates"])}, index=pd.to_datetime(C["wdates"], format="%Y%m%d"))
    except Exception:
        old = None
    n_new = 0
    if not offline:
        today = now_ist().strftime("%Y-%m-%d")
        def stale(sy):
            at = (names.get(sy) or {}).get("at")
            try:
                return at is None or (dt.datetime.strptime(today, "%Y-%m-%d") - dt.datetime.strptime(at, "%Y-%m-%d")).days >= fresh_days
            except Exception:
                return True
        todo = [sy for sy, u in U.items() if u["x"] == "BSE" and u.get("code") and stale(sy)]
        todo.sort(key=lambda sy: (-(U[sy]["turn"] or 0), (names.get(sy) or {}).get("at") or ""))
        todo = todo[:n_per_pass]
        if todo:
            try:
                import yfinance as yf
                t0 = time.time(); frames = []
                for ch in _chunks(todo, 40):
                    if time.time() - t0 > budget_s:
                        break
                    tick = [str(U[sy]["code"]) + ".BO" for sy in ch]
                    time.sleep(0.5)
                    try:
                        raw = yf.download(tick, period=WEEKLY_PERIOD, interval="1wk", progress=False, threads=True, auto_adjust=True, group_by="column")
                        df = _close_frame(raw, tick)
                        if df is not None:
                            back = {str(U[sy]["code"]) + ".BO": sy for sy in ch}
                            df = df.rename(columns=lambda c: back.get(str(c), str(c)))
                            df = df[[c for c in df.columns if c in back.values()]]
                            frames.append(df)
                    except Exception as e:
                        log("BSE chunk failed (%s)" % type(e).__name__)
                if frames:
                    new = pd.concat(frames, axis=1); new = new.loc[:, ~new.columns.duplicated()]
                    new = new.dropna(axis=1, thresh=12)
                    n_new = new.shape[1]
                    failed_pull = n_new < max(3, int(0.05 * len(todo)))     # v148.1 · Yahoo answered for almost nobody — a refused pull, not 240 absences
                    if old is not None:
                        keep = [c for c in old.columns if c not in new.columns]
                        merged = pd.concat([old[keep], new], axis=1).sort_index()
                    else:
                        merged = new.sort_index()
                    merged = merged.iloc[-560:]
                    at_old = {sy: (names.get(sy) or {}).get("at") for sy in merged.columns}
                    C = {"updated": now_ist().strftime("%Y-%m-%d %H:%M"), "wdates": [d.strftime("%Y%m%d") for d in merged.index],
                         "names": {sy: {"at": (today if sy in new.columns else at_old.get(sy)), "code": U[sy].get("code") if sy in U else None,
                                        "w": [(_f(v) if pd.notna(v) else None) for v in merged[sy].values]} for sy in merged.columns}}
                    for sy in todo:
                        if sy not in merged.columns and not failed_pull:
                            C["names"].setdefault(sy, {"at": today, "code": U[sy].get("code"), "w": [None] * len(C["wdates"])})   # answered nothing: not asked again for a week
                    if failed_pull:
                        log("BSE tapes: Yahoo answered for %d of %d — a refused pull; nothing marked tried" % (n_new, len(todo)))
                    try:
                        json.dump(C, open(BSE_FILE, "w"), separators=(",", ":"))
                    except Exception as e:
                        log("BSE cache not written (%s)" % type(e).__name__)
                    old = merged
            except Exception as e:
                log("BSE rotation skipped (%s: %s)" % (type(e).__name__, str(e)[:60]))
    n_join = 0
    if old is not None and len(old.columns):
        try:
            Wb = old.reindex(W.index)
            cols = [c for c in Wb.columns if c not in W.columns and Wb[c].notna().sum() >= 12]
            if cols:
                W = W.join(Wb[cols]); n_join = len(cols)
        except Exception as e:
            log("BSE join skipped (%s)" % type(e).__name__)
    log("BSE tapes: %d names joined on the weekly panel (%d fetched this pass, %d on file)" % (n_join, n_new, len(C.get("names") or {})))
    return W


def get_prices(U, offline, budget, max_age_h=6):
    liquid = [s for s, u in U.items() if u["x"] == "NSE" and ((u["turn"] or 0) >= 0.5 or u["fno"])]
    # v148 · every NSE name gets a weekly tape (the liquid ones first, so a budget cut costs the thinnest names, not the traded ones)
    weekly_all = liquid + [s for s, u in U.items() if u["x"] == "NSE" and s not in set(liquid)]
    top = sorted([s for s in liquid if U[s]["turn"]], key=lambda s: -U[s]["turn"])[:450]
    daily = list(dict.fromkeys(top + [s for s in liquid if U[s]["fno"]]))
    if not offline:
        # a panel pulled less than max_age_h ago is reused (the workflow caches it between passes):
        # weekly betas do not move in an hour, and the day's print rides in from the bhavcopy
        W, D, src = load_prices_cache(max_age_h=max_age_h)
        if W is not None and W.shape[1] >= 200:
            return W, D, src
        try:
            W, D = fetch_yahoo(weekly_all, daily, budget=budget)
            W = W.dropna(axis=1, thresh=12)
            if W.shape[1] >= 200:
                save_prices(W, D)
                return W, D, "Yahoo · %d names weekly (%s) · %d daily (%s)" % (W.shape[1], WEEKLY_PERIOD, (D.shape[1] if D is not None else 0), DAILY_PERIOD)
            log("Yahoo returned only %d names — carrying" % W.shape[1])
        except Exception as e:
            log("Yahoo unavailable (%s: %s)" % (type(e).__name__, str(e)[:80]))
    W, D, src = load_prices_cache()
    if W is not None and W.shape[1] >= 200:
        return W, D, src
    W, D, src = load_page_history()
    return W, D, src


# ─────────────────────────────────────────────────────────────────────────────
# 4 · the tape
# ─────────────────────────────────────────────────────────────────────────────
def _ret(s, n):
    try:
        if len(s) <= n or not s.iloc[-1 - n] or pd.isna(s.iloc[-1 - n]):
            return None
        return _f((s.iloc[-1] / s.iloc[-1 - n] - 1) * 100)
    except Exception:
        return None


def tape_features(sym, W, D, u):
    T = {}
    d = D[sym].dropna() if (D is not None and sym in D.columns) else None
    w = W[sym].dropna() if sym in W.columns else None
    px = u.get("px")
    if d is not None and len(d) >= 30:
        s = d
        T["src"] = "daily"
        T["r5"], T["r20"], T["r60"], T["r120"], T["r250"] = _ret(s, 5), _ret(s, 20), _ret(s, 60), _ret(s, 120), _ret(s, 250)
        m50 = s.tail(50).mean(); m200 = s.tail(200).mean() if len(s) >= 120 else s.mean()
        T["vs50"] = _f((s.iloc[-1] / m50 - 1) * 100); T["vs200"] = _f((s.iloc[-1] / m200 - 1) * 100)
        r = s.pct_change().dropna()
        T["sig1d"] = _f(r.tail(20).std() * 100); T["sig1d_60"] = _f(r.tail(60).std() * 100)
        T["sig5d"] = _f(r.tail(20).std() * 100 * math.sqrt(5))
        T["ext20"] = _f((s.iloc[-1] - s.tail(20).mean()) / (s.tail(20).std() or 1e-9), 2)
        hi, lo = s.tail(250).max(), s.tail(250).min()
        T["hi52"], T["lo52"] = _f(hi), _f(lo)
        T["pos52"] = _f((s.iloc[-1] - lo) / ((hi - lo) or 1e-9), 2)
        T["dd"] = _f((s.iloc[-1] / hi - 1) * 100)
        T["vol_ratio"] = _f((r.tail(20).std() / (r.tail(100).std() or 1e-9)), 2)
        T["n"] = int(len(s))
        T["m50"], T["m200"] = _f(m50), _f(m200)
        T["up20"] = int((r.tail(20) > 0).sum())
        T["since"] = (w.index[0] if (w is not None and len(w)) else s.index[0]).strftime("%Y%m%d")
        T["yrs"] = _f(((s.index[-1] - pd.Timestamp(T["since"])).days) / 365.25, 1)
        T["trunc"] = 1 if (W is not None and len(W.index) and pd.Timestamp(T["since"]) <= W.index[0] + pd.Timedelta(days=10)) else 0
    elif w is not None and len(w) >= 12:
        s = w
        T["src"] = "weekly"
        T["r5"], T["r20"], T["r60"], T["r120"], T["r250"] = _ret(s, 1), _ret(s, 4), _ret(s, 12), _ret(s, 26), _ret(s, 52)
        m50 = s.tail(10).mean(); m200 = s.tail(40).mean() if len(s) >= 30 else s.mean()
        T["vs50"] = _f((s.iloc[-1] / m50 - 1) * 100); T["vs200"] = _f((s.iloc[-1] / m200 - 1) * 100)
        r = s.pct_change().dropna()
        wk = r.tail(26).std() * 100
        T["sig1d"] = _f(wk / math.sqrt(5)); T["sig1d_60"] = T["sig1d"]; T["sig5d"] = _f(wk)
        T["ext20"] = _f((s.iloc[-1] - s.tail(4).mean()) / (s.tail(8).std() or 1e-9), 2)
        hi, lo = s.tail(52).max(), s.tail(52).min()
        T["hi52"], T["lo52"] = _f(hi), _f(lo)
        T["pos52"] = _f((s.iloc[-1] - lo) / ((hi - lo) or 1e-9), 2)
        T["dd"] = _f((s.iloc[-1] / hi - 1) * 100)
        T["vol_ratio"] = _f((r.tail(8).std() / (r.tail(26).std() or 1e-9)), 2)
        T["n"] = int(len(s))
        T["m50"], T["m200"] = _f(m50), _f(m200)
        T["up20"] = None
        T["since"] = s.index[0].strftime("%Y%m%d")
        T["yrs"] = _f(((s.index[-1] - s.index[0]).days) / 365.25, 1)
        T["trunc"] = 1 if (len(W.index) and s.index[0] <= W.index[0] + pd.Timedelta(days=10)) else 0
    else:
        T["src"] = "bhavcopy"
        T["r5"] = u.get("w1"); T["r20"] = T["r60"] = T["r120"] = T["r250"] = None
        T["vs50"] = T["vs200"] = None; T["sig1d"] = 2.0; T["sig5d"] = 4.5; T["ext20"] = None
        T["pos52"] = None; T["dd"] = None; T["vol_ratio"] = None; T["n"] = 0; T["hi52"] = T["lo52"] = None
        T["m50"] = T["m200"] = None; T["up20"] = None; T["since"] = None; T["yrs"] = None; T["trunc"] = None
    # the day from the bhavcopy (today's print beats the panel's last bar)
    T["r1"] = u.get("d1")
    if T.get("sig1d") in (None, 0):
        T["sig1d"] = 2.0
    if T.get("sig5d") in (None, 0):
        T["sig5d"] = _f(T["sig1d"] * math.sqrt(5))
    return T


# ─────────────────────────────────────────────────────────────────────────────
# 5 · macro DNA — ridge on weekly returns, regime record, the wind
# ─────────────────────────────────────────────────────────────────────────────
def factor_frame(W):
    """weekly % changes of the five factors (rates = −gilt price change, i.e. yields up)"""
    F = pd.DataFrame(index=W.index)
    for k in ("nifty", "inr", "brent", "vix"):
        sym = MACRO[k]
        if sym in W.columns:
            F[k] = W[sym].pct_change() * 100
    if MACRO["gilt"] in W.columns:
        F["rates"] = -W[MACRO["gilt"]].pct_change() * 100
    elif MACRO["us10y"] in W.columns:
        F["rates"] = W[MACRO["us10y"]].diff() * 10   # tenths of a percent → ~ETF-% equivalent
    return F


def ridge(y, X, lam=0.08):
    """standardised ridge; returns betas in raw units, t-stats and R²"""
    n, k = X.shape
    mx, sx = X.mean(axis=0), X.std(axis=0, ddof=1)
    sx[sx == 0] = 1
    Z = (X - mx) / sx
    yc = y - y.mean()
    A = Z.T @ Z + lam * n * np.eye(k)
    b_std = np.linalg.solve(A, Z.T @ yc)
    resid = yc - Z @ b_std
    dof = max(n - k - 1, 1)
    s2 = float(resid @ resid) / dof
    try:
        cov = s2 * np.linalg.inv(A) @ (Z.T @ Z) @ np.linalg.inv(A)
        se = np.sqrt(np.maximum(np.diag(cov), 1e-12))
    except Exception:
        se = np.full(k, np.nan)
    t = b_std / se
    r2 = 1 - float(resid @ resid) / (float(yc @ yc) or 1e-9)
    return b_std / sx, t, max(0.0, r2)


def macro_dna(sym, W, F, labels):
    if sym not in W.columns:
        return None
    y = W[sym].pct_change() * 100
    df = pd.concat([y.rename("y"), F], axis=1).dropna()
    cols = [c for c in FACTORS if c in df.columns]
    if len(df) < 26 or len(cols) < 3:
        return None
    dfb = df.tail(DNA_WEEKS)      # v148 · the betas on the last three years; the regime record below on the whole history
    X = dfb[cols].values.astype(float); yv = dfb["y"].values.astype(float)
    try:
        b, t, r2 = ridge(yv, X)
    except Exception:
        return None
    out = {"n": int(len(dfb)), "n_all": int(len(df)), "since": df.index[0].strftime("%Y%m%d"), "r2": _f(r2, 2), "b": {}, "t": {}}
    for i, c in enumerate(cols):
        out["b"][c] = _f(b[i], 3)
        out["t"][c] = _f(t[i], 1)
    # the record by regime: mean weekly excess return vs the Nifty, annualised
    try:
        ex = (df["y"] - df["nifty"]) if "nifty" in df.columns else df["y"]
        lab = labels.reindex(df.index)
        rec = {}
        for rg in ("Reflation", "Goldilocks", "Stagflation", "Disinflation"):
            m = lab == rg
            if int(m.sum()) >= 6:
                rec[rg] = {"ann": _f(ex[m].mean() * 52, 1), "n": int(m.sum()), "hit": _f((ex[m] > 0).mean() * 100, 0)}
        out["regime"] = rec
    except Exception:
        out["regime"] = {}
    return out


def macro_impulse(F):
    """the last four weeks' move of each factor, and its size in σ units"""
    imp = {}
    for c in F.columns:
        s = F[c].dropna()
        if len(s) < 8:
            continue
        last4 = float(s.tail(4).sum())
        sd4 = float(s.rolling(4).sum().dropna().std() or 1e-9)
        imp[c] = {"move": _f(last4, 2), "z": _f(max(-3, min(3, last4 / sd4)), 2)}
    return imp


def wind_of(dna, imp):
    if not dna or not imp:
        return None
    parts = []
    tot = 0.0
    for c, b in (dna.get("b") or {}).items():
        if c in imp and b is not None:
            v = b * (imp[c]["move"] or 0)
            parts.append([c, _f(v, 2)])
            tot += v
    parts.sort(key=lambda p: -abs(p[1] or 0))
    return {"total": _f(tot, 2), "parts": parts}


# ─────────────────────────────────────────────────────────────────────────────
# 6 · fundamentals — Yahoo's profile, on a rotation, cached
# ─────────────────────────────────────────────────────────────────────────────
FUND_KEYS = {"marketCap": "mcap", "trailingPE": "pe", "forwardPE": "fpe", "priceToBook": "pb", "returnOnEquity": "roe",
             "profitMargins": "margin", "operatingMargins": "opm", "revenueGrowth": "revg", "earningsGrowth": "epsg",
             "debtToEquity": "de", "dividendYield": "divy", "heldPercentInsiders": "promoter", "beta": "beta",
             "fiftyTwoWeekHigh": "hi52", "fiftyTwoWeekLow": "lo52", "trailingEps": "eps", "bookValue": "bv",
             "totalRevenue": "rev", "netIncomeToCommon": "ni", "freeCashflow": "fcf", "enterpriseToEbitda": "ev_ebitda",
             "currentRatio": "cr", "quickRatio": "qr", "sector": "ysector", "industry": "industry",
             "longBusinessSummary": "summary", "website": "web", "fullTimeEmployees": "staff", "longName": "lname",
             "sharesOutstanding": "shares", "targetMeanPrice": "street_tgt", "numberOfAnalystOpinions": "street_n",
             "recommendationKey": "street_rec", "earningsTimestamp": "ern_ts", "earningsTimestampStart": "ern_ts0", "exDividendDate": "exdiv_ts"}


def load_fund():
    """fundamentals.json; v148.1 · a profile that a failed refresh flagged "empty" while it still carried its numbers
    (Yahoo refused the runner from Oct 14 and 268 good profiles — Reliance, TCS, HDFC Bank — were hidden) is unflagged"""
    Fd = _load_fund_raw()
    try:
        n_fix = 0
        for s_, r_ in (Fd.get("names") or {}).items():
            if r_.get("empty") and len([k for k in r_ if k not in ("asof", "empty", "tried")]) >= 3:
                r_.pop("empty", None); r_["tried"] = r_.get("asof"); r_["asof"] = min(r_.get("asof") or "2026-10-13", "2026-10-13"); n_fix += 1
        if n_fix:
            log("fundamentals: %d profiles un-hidden (flagged empty by a failed refresh while still carrying their numbers)" % n_fix)
    except Exception:
        pass
    return Fd


def _load_fund_raw():
    try:
        return json.load(open(FUND_FILE))
    except Exception:
        return {"updated": None, "names": {}}


def fund_refresh(U, priority, budget=150, offline=False):
    Fd = load_fund()
    names = Fd.setdefault("names", {})
    if offline or budget <= 0:
        return Fd, 0
    try:
        import yfinance as yf
    except Exception:
        return Fd, 0
    today = now_ist().strftime("%Y-%m-%d")
    # the rotation: priority names first, then the stalest; a name is fresh for 7 days; a name Yahoo refused waits two days
    def _days(a):
        try:
            return (pd.Timestamp(today) - pd.Timestamp(a)).days
        except Exception:
            return 10 ** 6
    def age(s):
        a = (names.get(s) or {}).get("asof")
        return _days(a) if a else 10 ** 6
    def due(s):
        r = names.get(s) or {}
        return age(s) >= 7 and (not r.get("tried") or _days(r["tried"]) >= 2)
    order = [s for s in priority if due(s)]
    rest = sorted([s for s in U if U[s]["x"] == "NSE" and s not in order and (U[s]["turn"] or 0) >= 1.0], key=lambda s: -age(s))
    order += [s for s in rest if due(s)]
    t0 = time.time(); n = 0; n_tried = 0; run_empty = 0; last_err = None
    for s in order:
        if time.time() - t0 > budget:
            break
        if n == 0 and run_empty >= 4:
            # v148.1 · Yahoo refuses the runner (429 on the crumb, as from Oct 14): stop burning the rotation, keep every profile we have
            log("fundamentals: Yahoo answered none of the first %d profiles (%s) — the rotation pauses this pass; the profiles on file stay" % (n_tried, last_err or "empty"))
            break
        try:
            info = yf.Ticker(s + ".NS").info or {}
        except Exception as e:
            info = {}; last_err = type(e).__name__
        n_tried += 1
        rec = {"asof": today}
        for k, v in FUND_KEYS.items():
            x = info.get(k)
            if x is None:
                continue
            if isinstance(x, (int, float)) and not isinstance(x, bool):
                if k in ("returnOnEquity", "profitMargins", "operatingMargins", "revenueGrowth", "earningsGrowth", "heldPercentInsiders", "dividendYield"):
                    x = x * 100 if abs(x) < 5 and k != "dividendYield" else x
                    if k == "dividendYield" and x > 20:
                        x = x / 100.0
                if k == "dividendYield" and x < 0.05:
                    x = x * 100
                rec[v] = _f(x, 2)
            elif isinstance(x, str):
                rec[v] = (x[:600].rsplit(" ", 1)[0] + "…" if len(x) > 600 else x) if k == "longBusinessSummary" else x[:80]
        if len(rec) > 1:
            names[s] = rec
            n += 1; run_empty = 0
        else:
            run_empty += 1
            old = names.get(s) or {}
            if len([k for k in old if k not in ("asof", "empty", "tried")]) >= 3:
                old["tried"] = today            # v148.1 · nothing came, but the profile on file is good — keep it, retry in two days
            else:
                names.setdefault(s, {})["asof"] = today   # tried; nothing came — retry in a week
                names[s]["empty"] = True
        time.sleep(0.6)
    Fd["updated"] = now_ist().strftime("%a %b %d, %Y %H:%M IST")
    try:
        json.dump(Fd, open(FUND_FILE, "w"), separators=(",", ":"))
    except Exception as e:
        log("fundamentals not written (%s)" % type(e).__name__)
    return Fd, n


def quality_score(fund, sector_pe):
    """0–100 from the profile; 50 and 'unknown' when there is none"""
    if not fund or fund.get("empty"):
        return 50.0, []
    pts, why = [], []
    roe = fund.get("roe"); mg = fund.get("margin"); rg = fund.get("revg"); eg = fund.get("epsg")
    de = fund.get("de"); pe = fund.get("pe"); pb = fund.get("pb"); pr = fund.get("promoter")
    if roe is not None:
        pts.append(min(100, max(0, 50 + roe * 2.0))); why.append("ROE %.0f%%" % roe)
    if mg is not None:
        pts.append(min(100, max(0, 50 + mg * 2.5)))
    if rg is not None:
        pts.append(min(100, max(0, 50 + rg * 1.5))); why.append("revenue %+.0f%%" % rg)
    if eg is not None:
        pts.append(min(100, max(0, 50 + eg * 0.8)))
    if de is not None:
        pts.append(min(100, max(0, 80 - de * 0.25)))
        if de > 150:
            why.append("debt/equity %.0f%%" % de)
    if pe is not None and pe > 0:
        ref = sector_pe or 25.0
        pts.append(min(100, max(0, 50 - (pe / ref - 1) * 40)))
        why.append("P/E %.0f vs sector %.0f" % (pe, ref))
    elif pe is not None and pe < 0:
        pts.append(20); why.append("loss-making")
    if pb is not None and pb > 0:
        pts.append(min(100, max(0, 60 - (pb - 3) * 5)))
    if pr is not None and pr > 0:
        pts.append(min(100, max(0, 30 + pr * 0.6)))
    if not pts:
        return 50.0, []
    return float(np.mean(pts)), why[:3]


# ─────────────────────────────────────────────────────────────────────────────
# 7 · the scores and the verdicts
# ─────────────────────────────────────────────────────────────────────────────
def pct_rank(vals):
    """0–100 percentile rank, NaN-safe (NaN → 50)"""
    s = pd.Series(vals, dtype=float)
    r = s.rank(pct=True) * 100
    return r.fillna(50.0).values


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def score_universe(U, T, DNA, WIND, FUND, cont, dipn, regime, edge, gate, opt, fno, sector_rs):
    syms = list(U.keys())
    n = len(syms)
    g = lambda s, k: (T.get(s) or {}).get(k)
    r5 = np.array([g(s, "r5") if g(s, "r5") is not None else np.nan for s in syms], dtype=float)
    r20 = np.array([g(s, "r20") if g(s, "r20") is not None else np.nan for s in syms], dtype=float)
    r60 = np.array([g(s, "r60") if g(s, "r60") is not None else np.nan for s in syms], dtype=float)
    r120 = np.array([g(s, "r120") if g(s, "r120") is not None else np.nan for s in syms], dtype=float)
    r250 = np.array([g(s, "r250") if g(s, "r250") is not None else np.nan for s in syms], dtype=float)
    vs50 = np.array([g(s, "vs50") if g(s, "vs50") is not None else np.nan for s in syms], dtype=float)
    vs200 = np.array([g(s, "vs200") if g(s, "vs200") is not None else np.nan for s in syms], dtype=float)
    pos52 = np.array([g(s, "pos52") if g(s, "pos52") is not None else np.nan for s in syms], dtype=float)
    ext = np.array([g(s, "ext20") if g(s, "ext20") is not None else 0.0 for s in syms], dtype=float)
    dd = np.array([g(s, "dd") if g(s, "dd") is not None else np.nan for s in syms], dtype=float)
    sig = np.array([g(s, "sig1d") or 2.0 for s in syms], dtype=float)
    # risk-adjusted momentum: return / vol, so a 3%-a-day name does not win by noise
    mom_s = (0.5 * np.nan_to_num(r20 / np.maximum(sig, 0.5) / math.sqrt(20), nan=0.0)
             + 0.5 * np.nan_to_num(r60 / np.maximum(sig, 0.5) / math.sqrt(60), nan=0.0))
    mom_l = (0.4 * np.nan_to_num(r120 / np.maximum(sig, 0.5) / math.sqrt(120), nan=0.0)
             + 0.4 * np.nan_to_num(r250 / np.maximum(sig, 0.5) / math.sqrt(250), nan=0.0)
             + 0.2 * np.nan_to_num(vs200 / 10.0, nan=0.0))
    T_short = 0.55 * pct_rank(mom_s) + 0.25 * pct_rank(np.nan_to_num(vs50, nan=0.0)) + 0.20 * pct_rank(np.nan_to_num(pos52, nan=0.5))
    T_long = 0.5 * pct_rank(mom_l) + 0.3 * pct_rank(np.nan_to_num(vs200, nan=0.0)) + 0.2 * pct_rank(np.nan_to_num(pos52, nan=0.5))
    # extension penalty (short term): > 2σ above the 20-day mean gives back
    T_short = T_short - np.clip(ext - 1.5, 0, 3) * 6
    # macro: the wind + the sector's regime edge + sector relative strength
    wind = np.array([(WIND.get(s) or {}).get("total") or 0.0 for s in syms], dtype=float)
    sec_edge = np.array([((edge.get(U[s]["sector"]) or {}).get("ann_pct") or 0.0) for s in syms], dtype=float)
    sec_t = np.array([abs(((edge.get(U[s]["sector"]) or {}).get("t") or 0.0)) for s in syms], dtype=float)
    sec_edge_w = sec_edge * np.clip(sec_t / 2.0, 0, 1)        # a sector edge counts in proportion to its t
    srs = np.array([(sector_rs.get(U[s]["sector"]) or {}).get("rs12") or 0.0 for s in syms], dtype=float)
    M_short = 0.4 * pct_rank(wind) + 0.3 * pct_rank(sec_edge_w) + 0.3 * pct_rank(srs)
    M_long = 0.2 * pct_rank(wind) + 0.5 * pct_rank(sec_edge_w) + 0.3 * pct_rank(srs)
    # name-level regime record where it exists
    rr = np.array([(((DNA.get(s) or {}).get("regime") or {}).get(regime) or {}).get("ann") or np.nan for s in syms], dtype=float)
    rr_rank = pct_rank(np.nan_to_num(rr, nan=0.0))
    has_rr = ~np.isnan(rr)
    M_long = np.where(has_rr, 0.75 * M_long + 0.25 * rr_rank, M_long)
    M_short = np.where(has_rr, 0.85 * M_short + 0.15 * rr_rank, M_short)
    # quality
    sector_pe = {}
    try:
        by = {}
        for s in syms:
            f = (FUND.get("names") or {}).get(s) or {}
            if f.get("pe") and f["pe"] > 0:
                by.setdefault(U[s]["sector"], []).append(f["pe"])
        sector_pe = {k: float(np.median(v)) for k, v in by.items() if len(v) >= 3}
    except Exception:
        pass
    Q = np.zeros(n); Qwhy = {}
    for i, s in enumerate(syms):
        q, why = quality_score((FUND.get("names") or {}).get(s), sector_pe.get(U[s]["sector"]))
        Q[i] = q; Qwhy[s] = why
    # flow / derivatives (F&O names): long build-up, short covering, basis, PCR
    Fl = np.full(n, 50.0)
    for i, s in enumerate(syms):
        f = fno.get(s)
        if not f:
            continue
        sc = 50.0
        dp = f.get("d") or 0.0; doi = f.get("doi_pct") or 0.0
        if dp > 0 and doi > 0: sc += min(20, doi * 2)          # long build-up
        if dp > 0 and doi < 0: sc += min(10, -doi)              # short covering
        if dp < 0 and doi > 0: sc -= min(20, doi * 2)           # short build-up
        if dp < 0 and doi < 0: sc -= min(10, -doi)              # long unwinding
        o = opt.get(s) or {}
        pcr = o.get("pcr_oi")
        if pcr:
            if pcr > 1.3: sc += 5
            if pcr < 0.5: sc -= 5
        Fl[i] = clamp(sc, 0, 100)
    # the contenders model (when the pass has it)
    C = np.full(n, 50.0); CS = {}
    for x in ((cont or {}).get("top") or []):
        s = str(x.get("sym") or "").upper()
        if s in U:
            try:
                pu = float(x.get("p_up")) if x.get("p_up") is not None else 0.5
                pm = float(x.get("p_move") or 0.3)
            except Exception:
                pu, pm = 0.5, 0.3
            CS[s] = {"p_move": _f(pm, 2), "p_up": _f(pu, 2), "q10": x.get("q10"), "q50": x.get("q50"), "q90": x.get("q90"),
                     "tgt_before_stop": x.get("p_tgt") or x.get("tgt_before_stop"), "stop_pct": x.get("stop_pct")}
            C[syms.index(s)] = clamp(50 + (pu - 0.5) * 120 * min(1.5, pm / 0.3), 0, 100)
    # risk: warn checks and volatility
    warn = np.array([((dipn.get(s) or {}).get("p") or 0.0) for s in syms], dtype=float)   # the dip model's odds of giving back
    R = np.clip(100 - sig * 8 - warn * 40, 0, 100)
    # the composite
    liq = pct_rank(np.log1p(np.array([U[s]["turn"] or 0.0 for s in syms], dtype=float)))
    S_short = 0.40 * T_short + 0.22 * M_short + 0.13 * Fl + 0.15 * C + 0.10 * Q
    S_long = 0.33 * T_long + 0.22 * M_long + 0.27 * Q + 0.08 * pct_rank(np.nan_to_num(-dd, nan=0.0)) + 0.10 * liq
    # the intraday score: the names in play — yesterday's move with turnover, derivatives lean, the contenders' p(move)
    r1 = np.array([g(s, "r1") if g(s, "r1") is not None else 0.0 for s in syms], dtype=float)
    turn = np.array([U[s]["turn"] or 0.0 for s in syms], dtype=float)
    pmv = np.array([((CS.get(s) or {}).get("p_move") or 0.3) for s in syms], dtype=float)
    S_intra = 0.35 * pct_rank(np.abs(r1) / np.maximum(sig, 0.5)) + 0.25 * pct_rank(pmv) + 0.2 * pct_rank(np.log1p(turn)) + 0.2 * np.abs(Fl - 50) * 2
    # the gate lowers every short-term score a notch (sizes halve, the bar rises); it never zeroes the page
    if gate:
        S_short = S_short - 4
    # re-rank to 0–100 among the names with a history, so thresholds mean the same thing every day
    scorable = np.array([(T.get(s) or {}).get("src") != "bhavcopy" for s in syms])   # v148 · a BSE-only name with a tape is scored too
    S_short_r = np.full(n, np.nan); S_long_r = np.full(n, np.nan); S_intra_r = np.full(n, np.nan)
    S_short_r[scorable] = pct_rank(S_short[scorable]); S_long_r[scorable] = pct_rank(S_long[scorable]); S_intra_r[scorable] = pct_rank(S_intra[scorable])
    out = {}
    for i, s in enumerate(syms):
        liquid = (U[s]["turn"] or 0) >= LIQUID_CR or U[s]["fno"]
        thin = not bool(scorable[i])
        out[s] = {"short": (_f(S_short_r[i], 0) if not thin else None), "long": (_f(S_long_r[i], 0) if not thin else None), "intra": (_f(S_intra_r[i], 0) if not thin else None),
                  "T": _f(T_short[i], 0), "TL": _f(T_long[i], 0), "M": _f(M_short[i], 0), "ML": _f(M_long[i], 0), "Q": _f(Q[i], 0), "F": _f(Fl[i], 0),
                  "C": _f(C[i], 0), "R": _f(R[i], 0), "liquid": bool(liquid), "thin": bool(thin), "qwhy": Qwhy.get(s) or [], "cont": CS.get(s)}
    return out, sector_pe


def _why_short(s, U, T, DNA, WIND, sc, fno, edge, regime):
    t = T.get(s) or {}
    w = []
    if t.get("r20") is not None:
        w.append("%s%% over 20 sessions, %s%% over 60" % (("%+.1f" % t["r20"]), ("%+.1f" % t["r60"]) if t.get("r60") is not None else "—"))
    if t.get("vs50") is not None:
        w.append("%s the 50-day (%+.1f%%)" % ("above" if t["vs50"] >= 0 else "below", t["vs50"]))
    wd = WIND.get(s) or {}
    if wd.get("parts"):
        p = wd["parts"][0]
        w.append("macro wind %+.1f%% this month (%s %+.1f%%)" % (wd.get("total") or 0, FACTOR_LABEL.get(p[0], p[0]), p[1] or 0))
    e = edge.get(U[s]["sector"]) or {}
    if e.get("ann_pct") is not None and abs(e.get("t") or 0) >= 1.5:
        w.append("%s has returned %+.0f%%/yr in %s (t %.1f)" % (U[s]["sector"], e["ann_pct"], regime, e.get("t") or 0))
    f = fno.get(s)
    if f and f.get("doi_pct") is not None and f.get("d") is not None:
        dp, doi = f["d"], f["doi_pct"]
        tag = "long build-up" if (dp > 0 and doi > 0) else "short covering" if (dp > 0 and doi < 0) else "short build-up" if (dp < 0 and doi > 0) else "long unwinding"
        w.append("futures: %s (OI %+.1f%%)" % (tag, doi))
    c = (sc.get("cont") or {})
    if c.get("p_move"):
        w.append("contenders: %d%% odds of a ≥1.5σ move in 5 sessions, p(up) %d%%" % (round(100 * c["p_move"]), round(100 * (c.get("p_up") or 0.5))))
    if t.get("ext20") is not None and t["ext20"] > 2:
        w.append("extended %.1fσ above its 20-day mean — chase nothing" % t["ext20"])
    return w[:5]


def _why_long(s, U, T, DNA, sc, FUND, edge, regime):
    t = T.get(s) or {}
    w = []
    if t.get("r250") is not None:
        w.append("%+.0f%% over a year, %+.0f%% over six months" % (t["r250"], t.get("r120") or 0))
    if t.get("vs200") is not None:
        w.append("%s the 200-day (%+.1f%%)" % ("above" if t["vs200"] >= 0 else "below", t["vs200"]))
    w += (sc.get("qwhy") or [])
    d = DNA.get(s) or {}
    rr = (d.get("regime") or {}).get(regime)
    if rr and rr.get("n", 0) >= 10:
        w.append("in %s weeks it has %s the Nifty by %.0f%%/yr (%d weeks)" % (regime, "beaten" if rr["ann"] >= 0 else "lagged", abs(rr["ann"]), rr["n"]))
    else:
        e = edge.get(U[s]["sector"]) or {}
        if e.get("ann_pct") is not None and abs(e.get("t") or 0) >= 1.5:
            w.append("%s: %+.0f%%/yr in %s regimes" % (U[s]["sector"], e["ann_pct"], regime))
    if t.get("dd") is not None and t["dd"] < -25:
        w.append("%.0f%% off its 52-week high" % t["dd"])
    return w[:5]


def _lot_of(s, px, fno):
    f = fno.get(s) or {}
    q = f.get("lot") or f.get("q")
    try:
        q = int(q) if q else 0
    except Exception:
        q = 0
    if q > 0:
        return q, "bhavcopy"
    if not px:
        return 0, "—"
    est = max(25, int(round(1_500_000 / px / 25.0)) * 25)
    return est, "estimated (≈₹15 lakh a lot)"


def verdicts(U, T, DNA, WIND, SC, FUND, fno, opt, edge, regime, gate, prev_picks):
    V = {}
    for s, u in U.items():
        sc = SC[s]; t = T.get(s) or {}
        px = u["px"] or 0
        sig1 = t.get("sig1d") or 2.0; sig5 = t.get("sig5d") or (sig1 * math.sqrt(5))
        thin = sc["thin"]; liquid = sc["liquid"]
        if thin:
            V[s] = {"short": {"side": None, "score": None, "thin": True, "why": ["too little history to score — price and the day only"]},
                    "long": {"side": None, "score": None, "thin": True, "why": []}, "intra": None, "note": 9}
            continue
        v = {"short": None, "long": None, "intra": None}
        # ── SHORT TERM · 5–60 sessions ──
        stop_pct = clamp(1.5 * sig5, 4.0, 14.0)
        h = int(clamp(round(60 - 2.2 * sig1 * 5), 5, 60))          # calmer names get the longer horizon
        if liquid and not thin:
            side = "BUY" if sc["short"] >= 80 else ("SELL" if (sc["short"] <= 10 and u["fno"]) else None)
            conv = "HIGH" if (sc["short"] >= 92 or sc["short"] <= 4) else ("MED" if side else None)
            size = clamp(RISK_PCT / stop_pct * 100, 2, 10) * (0.5 if gate else 1.0)
            sg = 1 if side == "BUY" else -1
            rec = {"side": side, "score": sc["short"], "conv": conv, "entry": _f(px), "stop": _f(px * (1 - sg * stop_pct / 100)),
                   "target": _f(px * (1 + sg * 2 * stop_pct / 100)), "stop_pct": _f(stop_pct, 1), "tgt_pct": _f(2 * stop_pct, 1),
                   "h": h, "size_pct": _f(size, 1), "why": (_why_short(s, U, T, DNA, WIND, sc, fno, edge, regime) if side else None)}
            v["short"] = rec
        else:
            v["short"] = {"side": None, "score": sc["short"], "conv": None, "why": ["below the liquidity floor (₹5 cr a day) — scored from the tape, not traded"], "illiquid": True}
        # ── LONG TERM · 12 months ──
        if not thin:
            side = "ACCUMULATE" if sc["long"] >= 80 else ("AVOID" if sc["long"] <= 20 else None)
            conv = "HIGH" if (sc["long"] >= 92 or sc["long"] <= 6) else ("MED" if side else None)
            # the 12-month expectation: shrunk momentum + the sector's regime edge + a quality tilt, clipped
            exp12 = 0.35 * clamp((t.get("r250") or 0) * 0.5, -20, 30) + clamp(((edge.get(u["sector"]) or {}).get("ann_pct") or 0) * 0.3, -8, 8) + (sc["Q"] - 50) * 0.2
            exp12 = clamp(exp12, -25, 45)
            if side == "ACCUMULATE":
                exp12 = max(exp12, 10.0)
            band = sig1 * math.sqrt(250)
            # the exit: the 200-day or −15%, whichever is closer (a name far above its 200-day gets the trailing line)
            m200 = t.get("m200") if (t.get("m200") and t["m200"] < px) else None
            stop = max(m200, px * 0.85) if m200 else px * 0.85
            stop_is_m200 = bool(m200) and stop == m200
            rec = {"side": side, "score": sc["long"], "conv": conv, "target": _f(px * (1 + exp12 / 100)), "exp_pct": _f(exp12, 1),
                   "band": [_f(px * (1 + (exp12 - band) / 100)), _f(px * (1 + (exp12 + band) / 100))], "stop": _f(stop),
                   "stop_note": "the 200-day" if stop_is_m200 else "−15%",
                   "why": (_why_long(s, U, T, DNA, sc, FUND, edge, regime) if side else None)}
            v["long"] = rec
        else:
            v["long"] = {"side": None, "score": sc["long"], "conv": None, "why": ["too little history to score — price and the day only"], "thin": True}
        # ── INTRADAY · today ──
        if u["fno"] or (u["turn"] or 0) >= INTRA_CR:
            c = sc.get("cont") or {}
            pu = c.get("p_up")
            lean = 0.0
            if pu is not None:
                lean += (pu - 0.5) * 2
            if sc["F"] is not None:
                lean += (sc["F"] - 50) / 50 * 0.6
            if t.get("r1") is not None:
                lean += clamp(t["r1"] / max(sig1, 0.5), -1.5, 1.5) * 0.3   # yesterday's direction, in σ units
            side = "BUY" if lean > 0.35 else ("SELL" if lean < -0.35 else None)
            sg = 1 if side == "BUY" else -1
            rec = {"side": side, "score": sc["intra"], "lean": _f(lean, 2), "range": [_f(px * (1 - sig1 / 100)), _f(px * (1 + sig1 / 100))],
                   "entry": [_f(px * (1 - sg * 0.25 * sig1 / 100)), _f(px * (1 + sg * 0.1 * sig1 / 100))] if side else None,
                   "stop": _f(px * (1 - sg * 0.9 * sig1 / 100)) if side else None, "target": _f(px * (1 + sg * 1.6 * sig1 / 100)) if side else None,
                   "sig1d": _f(sig1, 2), "flat_by": "15:20"}
            v["intra"] = rec
        # ── F&O · lots ──
        if u["fno"] and v["short"] and v["short"].get("side"):
            lot, lot_src = _lot_of(s, px, fno)
            st = v["short"]
            risk_lot = lot * abs(px - (st["stop"] or px))
            pot_lot = lot * abs((st["target"] or px) - px)
            lots = max(1, int((BOOK * RISK_PCT / 100) // risk_lot)) if risk_lot > 0 else 1
            v["fno"] = {"side": st["side"], "lot": lot, "lot_src": lot_src, "lots": lots, "risk_lot": _f(risk_lot, 0), "pot_lot": _f(pot_lot, 0),
                        "risk_pct_book": _f(100 * lots * risk_lot / BOOK, 1), "book": BOOK,
                        "margin_est": _f(lot * px * 0.18, 0), "contract": "FUT-%s-%s" % (s, (fno.get(s) or {}).get("xp") or ""),
                        "basis": (fno.get(s) or {}).get("b"), "oi_chg": (fno.get(s) or {}).get("doi_pct")}
            # v146 · the option on the idea: a defined-risk spread off the real chain
            try:
                ot = option_structure(s, st["side"], px, st.get("stop"), st.get("target"), st.get("h"), lot, CHAIN, opt.get(s), REPO_RATE)
                if ot:
                    v["fno"]["opt_trade"] = ot
            except Exception:
                pass
        # ── reconcile the horizons, one sentence ──
        v["note"] = reconcile(v)
        V[s] = v
    return V


# ─────────────────────────────────────────────────────────────────────────────
# 13 · THE OPTION ON THE IDEA (v146) — a defined-risk spread priced off the real chain
#     update_terminal.py writes options_chain.json every pass (every strike, every expiry, the bhavcopy's
#     closing premiums). A BUY idea becomes a bull call spread (buy the strike at the spot, sell the strike at
#     the target); a SELL idea a bear put spread. Debit, maximum, breakeven, the probability the spot ends past
#     breakeven (lognormal, ATM IV). Where the chain is not on disk the same spread is priced by Black-Scholes
#     off the ATM IV the page carries, and says so.
# ─────────────────────────────────────────────────────────────────────────────
CHAIN_FILE = "options_chain.json"


def load_chain():
    try:
        o = json.load(open(CHAIN_FILE))
        return o.get("underlyings") or {}, o.get("date")
    except Exception:
        return {}, None


def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs(S, K, T, r, sig, kind):
    if S <= 0 or K <= 0 or T <= 0 or sig <= 0:
        return max(0.0, (S - K) if kind == "CE" else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T)); d2 = d1 - sig * math.sqrt(T)
    if kind == "CE":
        return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * _ncdf(-d1)


def _k(x):
    try:
        return str(int(round(x))) if abs(x - round(x)) < 1e-6 else ("%.2f" % x).rstrip("0").rstrip(".")
    except Exception:
        return str(x)


def _strike_step(px):
    for lim, st in ((50, 1), (100, 2.5), (250, 5), (500, 10), (1000, 20), (2500, 50), (5000, 100), (10000, 250)):
        if px < lim:
            return st
    return 500


def option_structure(sym, side, px, stop, target, h, lot, chain_u, opt_row, rf):
    """the spread for one idea; None when there is no chain and no IV"""
    if not px or not target or side not in ("BUY", "SELL") or not lot:
        return None
    want_days = int(round((h or 10) * 7 / 5)) + 2
    kind = "CE" if side == "BUY" else "PE"
    rf = float(rf or 5.5) / 100
    # ── the real chain ──
    U = (chain_u or {}).get(sym)
    if U and U.get("expiries"):
        exps = sorted(((xp, e) for xp, e in U["expiries"].items() if (e.get("dte") or 0) >= 3), key=lambda x: x[1].get("dte") or 0)
        pick = next(((xp, e) for xp, e in exps if (e.get("dte") or 0) >= min(want_days, 25)), exps[-1] if exps else None)
        if pick:
            xp, e = pick
            rows = {r[0]: r for r in (e.get("rows") or []) if r and r[0]}
            ks = sorted(rows)
            def px_of(k):
                r = rows.get(k)
                if not r:
                    return None
                return r[1] if kind == "CE" else r[7]
            spot = e.get("fut") or U.get("spot") or px
            cands = [k for k in ks if px_of(k)]
            if len(cands) >= 2:
                k1 = min(cands, key=lambda k: abs(k - px))
                far = [k for k in cands if (k > k1 if side == "BUY" else k < k1)]
                if far:
                    k2 = min(far, key=lambda k: abs(k - target))
                    p1, p2 = px_of(k1), px_of(k2)
                    debit = p1 - p2
                    if debit > 0:
                        width = abs(k2 - k1); mx = width - debit
                        be = k1 + debit if side == "BUY" else k1 - debit
                        iv = (e.get("atm_iv") or (opt_row or {}).get("atm_iv") or 30) / 100.0; T = max(e.get("dte") or 1, 1) / 365.0
                        d2 = (math.log(px / be) + (rf - 0.5 * iv * iv) * T) / (iv * math.sqrt(T))
                        p_prof = _ncdf(d2) if side == "BUY" else _ncdf(-d2)
                        lots = max(1, int((BOOK * RISK_PCT / 100) // (debit * lot)))
                        return {"kind": "bull call spread" if side == "BUY" else "bear put spread", "src": "the chain · bhavcopy closes", "expiry": xp, "dte": e.get("dte"),
                                "buy": k1, "sell": k2, "buy_px": _f(p1), "sell_px": _f(p2), "debit": _f(debit), "debit_lot": _f(debit * lot, 0), "max_lot": _f(mx * lot, 0),
                                "be": _f(be), "rr": _f(mx / debit, 1) if debit else None, "p_profit": _f(100 * p_prof, 0), "iv": e.get("atm_iv"), "lot": lot, "lots": lots,
                                "naked": {"k": k1, "px": _f(p1), "lot": _f(p1 * lot, 0), "be": _f(k1 + p1 if side == "BUY" else k1 - p1)},
                                "fits_book": bool(debit * lot <= BOOK * RISK_PCT / 100 * 1.5),
                                "note": "buy the %s %s, sell the %s %s (%s) · pay about ₹%s a lot, make up to ₹%s if it settles past %s · breakeven %s · the engine's target is %s" % (
                                    _k(k1), kind, _k(k2), kind, xp, "{:,}".format(int(round(debit * lot))), "{:,}".format(int(round(mx * lot))), _k(k2), _k(be), _k(target))}
    # ── theoretical, off the ATM IV ──
    iv = (opt_row or {}).get("atm_iv")
    if not iv:
        return None
    dte = (opt_row or {}).get("dte") or 20; xp = (opt_row or {}).get("expiry") or ""
    if dte < min(want_days, 25) and (opt_row or {}).get("term"):
        for t in opt_row["term"]:
            if t[2] >= min(want_days, 25):
                xp, iv, dte = t[0], t[1], t[2]; break
    T = max(dte, 1) / 365.0; sig = iv / 100.0; step = _strike_step(px)
    k1 = round(px / step) * step; k2 = round(target / step) * step
    if (side == "BUY" and k2 <= k1) or (side == "SELL" and k2 >= k1):
        k2 = k1 + step if side == "BUY" else k1 - step
    p1 = _bs(px, k1, T, rf, sig, kind); p2 = _bs(px, k2, T, rf, sig, kind); debit = p1 - p2
    if debit <= 0:
        return None
    width = abs(k2 - k1); mx = width - debit; be = k1 + debit if side == "BUY" else k1 - debit
    d2 = (math.log(px / be) + (rf - 0.5 * sig * sig) * T) / (sig * math.sqrt(T)); p_prof = _ncdf(d2) if side == "BUY" else _ncdf(-d2)
    lots = max(1, int((BOOK * RISK_PCT / 100) // (debit * lot)))
    return {"kind": "bull call spread" if side == "BUY" else "bear put spread", "src": "theoretical · Black-Scholes off the ATM IV (no chain on this pass)", "expiry": xp, "dte": dte,
            "buy": k1, "sell": k2, "buy_px": _f(p1), "sell_px": _f(p2), "debit": _f(debit), "debit_lot": _f(debit * lot, 0), "max_lot": _f(mx * lot, 0), "be": _f(be),
            "rr": _f(mx / debit, 1), "p_profit": _f(100 * p_prof, 0), "iv": iv, "lot": lot, "lots": lots,
            "naked": {"k": k1, "px": _f(p1), "lot": _f(p1 * lot, 0), "be": _f(k1 + p1 if side == "BUY" else k1 - p1)}, "fits_book": bool(debit * lot <= BOOK * RISK_PCT / 100 * 1.5),
            "note": "theoretical: buy the %s %s, sell the %s %s (%s) · about ₹%s a lot, up to ₹%s · breakeven %s — check the chain for the real premium" % (_k(k1), kind, _k(k2), kind, xp, "{:,}".format(int(round(debit * lot))), "{:,}".format(int(round(mx * lot))), _k(be))}


NOTE_TEXT = {
    1: "a long-term accumulate inside a short-term decline: wait for the short-term stop or horizon to clear, then buy",
    2: "a trade, not an investment: the tape says buy for the horizon, the long-term case does not hold",
    3: "the tape and the long-term case agree — buy, and the position can stay",
    4: "nothing here for a buyer at any horizon",
    5: "a short-term buy; no long-term view yet",
    6: "a short-term sell; the long-term read is neutral",
    7: "no short-term trade; accumulate for the year",
    8: "no trade; avoid for the year",
    0: "no position at any horizon — scored, watched, not traded",
    9: "not scored: only a price and a day on file",
}


def reconcile(v):
    """one code per name; the page prints NOTE_TEXT — the two horizons never contradict without saying so"""
    sh = (v.get("short") or {}).get("side"); lg = (v.get("long") or {}).get("side")
    if sh == "SELL" and lg == "ACCUMULATE":
        return 1
    if sh == "BUY" and lg == "AVOID":
        return 2
    if sh == "BUY" and lg == "ACCUMULATE":
        return 3
    if sh == "SELL" and lg == "AVOID":
        return 4
    if sh == "BUY":
        return 5
    if sh == "SELL":
        return 6
    if lg == "ACCUMULATE":
        return 7
    if lg == "AVOID":
        return 8
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# 8 · the picks (sticky), the sectors, the record, the shock
# ─────────────────────────────────────────────────────────────────────────────
def pick_lists(U, V, SC, T, prev, fno):
    def rank(side_key, horizon, side, n=5, hyst=5, fno_only=False, min_turn=0):
        pool = []
        for s, v in V.items():
            h = v.get(horizon) or {}
            if h.get("side") != side:
                continue
            if fno_only and not U[s]["fno"]:
                continue
            if (U[s]["turn"] or 0) < min_turn or U[s]["sector"] == "ETF":
                continue
            pool.append((s, h.get("score") or 0))
        pool.sort(key=lambda x: ((-x[1] if side in ("BUY", "ACCUMULATE") else x[1]), -(U[x[0]]["turn"] or 0)))
        keep = []
        prev_syms = [p["sym"] for p in (prev.get(side_key) or [])] if prev else []
        top10 = {s for s, _ in pool[:10]}
        for ps in prev_syms:
            v = (V.get(ps) or {}).get(horizon) or {}
            if v.get("side") == side and ps in top10:
                keep.append(ps)
        for s, _ in pool:
            if len(keep) >= n:
                break
            if s not in keep:
                keep.append(s)
        out = []
        for s in keep[:n]:
            h = V[s].get(horizon) or {}
            row = {"sym": s, "nm": U[s]["nm"], "sector": U[s]["sector"], "px": U[s]["px"], "d1": U[s]["d1"], "score": h.get("score"), "conv": h.get("conv"),
                   "side": side, "held_from": next((p.get("held_from") for p in (prev.get(side_key) or []) if p.get("sym") == s), None) or now_ist().strftime("%Y-%m-%d"),
                   "stop": h.get("stop"), "target": h.get("target"), "why": (h.get("why") or [])[:2]}
            if horizon == "short":
                row["h"] = h.get("h"); row["size_pct"] = h.get("size_pct")
            else:
                row["exp_pct"] = h.get("exp_pct"); row["stop_note"] = h.get("stop_note")
            out.append(row)
        return out
    P = {}
    # today's buys: the engine's strongest short-term BUYs right now, ranked, dated, refreshed every pass — not sticky;
    # a name is NEW when it was not on the last session's list
    # investable: the ₹100 cr floor (the ₹25 cr bar let in micro-caps on a one-day spike) and a year of tape (no fresh listings)
    def seasoned(s):
        t = T.get(s) or {}
        return (t.get("n") or 0) >= (200 if t.get("src") == "daily" else 45)
    tb = [(s, v["short"]) for s, v in V.items() if (v.get("short") or {}).get("side") == "BUY" and (U[s]["turn"] or 0) >= PICK_CR and U[s]["sector"] != "ETF" and seasoned(s)]
    tb.sort(key=lambda x: (-(x[1].get("score") or 0), -(U[x[0]]["turn"] or 0)))
    prev_tb = {p.get("sym") for p in (prev.get("today_buys") or [])}
    P["today_buys"] = [{"sym": s, "nm": U[s]["nm"], "sector": U[s]["sector"], "px": U[s]["px"], "d1": U[s]["d1"], "side": "BUY", "score": h.get("score"), "conv": h.get("conv"),
                        "entry": h.get("entry"), "stop": h.get("stop"), "target": h.get("target"), "h": h.get("h"), "size_pct": h.get("size_pct"), "why": (h.get("why") or [])[:2],
                        "new": s not in prev_tb, "fno": U[s]["fno"], "lots": (v_.get("fno") or {}).get("lots") if (v_ := V.get(s)) else None} for s, h in tb[:8]]
    P["short_buy"] = rank("short_buy", "short", "BUY", min_turn=PICK_CR)
    P["short_sell"] = rank("short_sell", "short", "SELL", fno_only=True)
    P["long"] = rank("long", "long", "ACCUMULATE", min_turn=PICK_CR)
    # intraday: the names in play today with a side, by the intraday score (not sticky — it is today's)
    ip = [(s, (v.get("intra") or {})) for s, v in V.items() if (v.get("intra") or {}).get("side") and U[s]["sector"] != "ETF"]
    ip.sort(key=lambda x: (-(x[1].get("score") or 0), -(U[x[0]]["turn"] or 0)))
    P["intraday"] = [{"sym": s, "nm": U[s]["nm"], "sector": U[s]["sector"], "px": U[s]["px"], "d1": U[s]["d1"], "side": i["side"], "score": i["score"], "lean": i.get("lean"),
                      "entry": i["entry"], "stop": i["stop"], "target": i["target"], "range": i["range"], "sig1d": i["sig1d"]} for s, i in ip[:5]]
    # F&O: the strongest short-term sides among the names with a future, as lots
    fp = [(s, v) for s, v in V.items() if v.get("fno")]
    fp.sort(key=lambda x: -abs((x[1]["short"].get("score") or 50) - 50))
    P["fno"] = [{"sym": s, "nm": U[s]["nm"], "sector": U[s]["sector"], "px": U[s]["px"], "d1": U[s]["d1"], "side": v["fno"]["side"], "lots": v["fno"]["lots"], "lot": v["fno"]["lot"],
                 "risk_lot": v["fno"]["risk_lot"], "pot_lot": v["fno"]["pot_lot"], "risk_pct_book": v["fno"].get("risk_pct_book"), "contract": v["fno"]["contract"], "stop": v["short"]["stop"],
                 "target": v["short"]["target"], "h": v["short"]["h"], "score": v["short"]["score"], "conv": v["short"].get("conv"), "why": (v["short"].get("why") or [])[:2],
                 "opt_trade": v["fno"].get("opt_trade")} for s, v in fp[:5]]
    return P


def sector_table(U, V, SC, T, W, DNA, edge, regime):
    secs = {}
    nifty = W[MACRO["nifty"]].dropna() if MACRO["nifty"] in W.columns else None
    for s, u in U.items():
        if u["x"] != "NSE" or not SC[s]["liquid"] or u["sector"] == "ETF":
            continue
        secs.setdefault(u["sector"], []).append(s)
    out = {}
    for sec, members in secs.items():
        if len(members) < 3:
            continue
        rows = []
        for s in members:
            t = T.get(s) or {}
            rows.append({"sym": s, "nm": U[s]["nm"], "px": U[s]["px"], "d1": U[s]["d1"], "turn": U[s]["turn"], "short": SC[s]["short"], "long": SC[s]["long"],
                         "s_side": (V[s].get("short") or {}).get("side"), "l_side": (V[s].get("long") or {}).get("side"),
                         "r20": t.get("r20"), "r60": t.get("r60"), "r250": t.get("r250"), "vs50": t.get("vs50"), "vs200": t.get("vs200")})
        rows.sort(key=lambda r: -(r["turn"] or 0))
        n = len(rows)
        def ew(k):
            v = [r[k] for r in rows if r.get(k) is not None]
            return _f(float(np.mean(v)), 1) if v else None
        above50 = _f(100 * np.mean([1 if (r["vs50"] or 0) > 0 else 0 for r in rows]), 0)
        above200 = _f(100 * np.mean([1 if (r["vs200"] or 0) > 0 else 0 for r in rows]), 0)
        buys = sum(1 for r in rows if r["s_side"] == "BUY"); sells = sum(1 for r in rows if r["s_side"] == "SELL")
        acc = sum(1 for r in rows if r["l_side"] == "ACCUMULATE"); avoid = sum(1 for r in rows if r["l_side"] == "AVOID")
        # the sector's DNA — turnover-weighted betas of its members
        bsum = {k: 0.0 for k in FACTORS}; wsum = 0.0
        for r in rows:
            d = DNA.get(r["sym"]) or {}
            wgt = (r["turn"] or 1.0)
            if d.get("b"):
                for k in FACTORS:
                    if d["b"].get(k) is not None:
                        bsum[k] += d["b"][k] * wgt
                wsum += wgt
        dna = {k: _f(bsum[k] / wsum, 3) for k in FACTORS} if wsum else None
        e = edge.get(sec) or {}
        avg_short = _f(float(np.mean([r["short"] for r in rows if r["short"] is not None] or [50])), 0)
        avg_long = _f(float(np.mean([r["long"] for r in rows if r["long"] is not None] or [50])), 0)
        nifty_r = {}
        if nifty is not None and len(nifty) > 13:
            nifty_r = {"r20": _f((nifty.iloc[-1] / nifty.iloc[-5] - 1) * 100), "r60": _f((nifty.iloc[-1] / nifty.iloc[-13] - 1) * 100),
                       "r250": _f((nifty.iloc[-1] / nifty.iloc[-min(53, len(nifty))] - 1) * 100)}
        rel60 = (ew("r60") or 0) - (nifty_r.get("r60") or 0)
        if avg_long >= 60 and above200 >= 60 and rel60 > 0:
            word = "BUY THE SECTOR"
        elif avg_long <= 40 and above200 <= 40:
            word = "AVOID"
        elif rel60 > 3:
            word = "LEADING"
        elif rel60 < -3:
            word = "LAGGING"
        else:
            word = "NEUTRAL"
        out[sec] = {"n": n, "word": word, "avg_short": avg_short, "avg_long": avg_long, "above50": above50, "above200": above200,
                    "buys": buys, "sells": sells, "accumulate": acc, "avoid": avoid, "r20": ew("r20"), "r60": ew("r60"), "r250": ew("r250"),
                    "rel60": _f(rel60, 1), "nifty": nifty_r, "dna": dna, "edge": ({"ann_pct": e.get("ann_pct"), "t": e.get("t"), "regime": regime} if e else None),
                    "leaders": rows[:8], "members": [r["sym"] for r in rows]}
    return out


def sector_rs_from(U, T, W):
    """12-week equal-weight sector return minus the Nifty's (the macro score's sector leg)"""
    nifty = W[MACRO["nifty"]].dropna() if MACRO["nifty"] in W.columns else None
    n12 = (nifty.iloc[-1] / nifty.iloc[-13] - 1) * 100 if (nifty is not None and len(nifty) > 13) else 0.0
    by = {}
    for s, u in U.items():
        t = T.get(s) or {}
        if t.get("r60") is not None and (u["turn"] or 0) >= LIQUID_CR and u["sector"] != "ETF":
            by.setdefault(u["sector"], []).append(t["r60"])
    return {k: {"rs12": _f(float(np.mean(v)) - n12, 1), "n": len(v)} for k, v in by.items() if len(v) >= 3}


def _frozen_payload(P, U, W, D, today, pairs=None, macro=None, movers=None, calls=None, street=None):
    frozen = {"date": today, "picks": {k: [{"sym": p["sym"], "side": p["side"], "px": p["px"]} for p in v] for k, v in P.items()},
              "pairs": [{"a": p["a"], "b": p["b"], "px_a": p["px_a"], "px_b": p["px_b"]} for p in (pairs or [])], "macro": macro,
              "movers": [{"sym": m["sym"], "px": m["px"], "p": m["p_move"], "pu": m["p_up"], "sig": m["sig20"], "lean": m["lean"]} for m in (movers or [])[:12]],
              "calls": [{"sym": c["sym"], "kind": c["kind"], "px": c["px"], "target": c["target"], "stop": c["stop"], "h": c["h"], "conv": c["conv"]}
                        for c in [x for x in ((calls or {}).get("long"), (calls or {}).get("short")) if x] + list((calls or {}).get("long_also") or []) + list((calls or {}).get("short_also") or [])],
              "street": [{"sym": r["sym"], "px": r["px"], "up_e": r["up_engine"], "up_s": r["up_street"]} for r in (list((street or {}).get("bull") or [])[:10] + list((street or {}).get("bear") or [])[:10])]}
    nifty_px = None
    try:
        nifty_px = _f(D[MACRO["nifty"]].dropna().iloc[-1]) if (D is not None and MACRO["nifty"] in D.columns) else _f(W[MACRO["nifty"]].dropna().iloc[-1])
    except Exception:
        pass
    frozen["nifty"] = nifty_px
    return frozen


def freeze_day(P, U, W, D, today, pairs=None, macro=None, movers=None, calls=None, street=None):
    """write today's frozen file once (the first pass of the day owns it)"""
    os.makedirs(HIST_DIR, exist_ok=True)
    fn = os.path.join(HIST_DIR, "engine_%s.json" % today.replace("-", ""))
    if not os.path.exists(fn):
        json.dump(_frozen_payload(P, U, W, D, today, pairs, macro, movers, calls, street), open(fn, "w"), separators=(",", ":"))
        return True
    return False


def freeze_and_score(P, U, W, D, today, pairs=None, macro=None, movers=None, calls=None, street=None, freeze=True):
    """freeze today's picks (the pairs, the macro call, the movers, v148: the calls of the day and the Street's widest gaps);
    score every past file whose horizon has elapsed. freeze=False scores only (main scores first, so the calls can lean on
    the engine's record per name, then freezes with freeze_day)"""
    if freeze:
        freeze_day(P, U, W, D, today, pairs, macro, movers, calls, street)
    # score
    H = {"intraday": 1, "fno": 10, "today_buys": 10, "short_buy": 20, "short_sell": 20, "long": 60}
    rows = {k: [] for k in H}
    rows["pairs"] = []; rows["macro"] = []; rows["movers"] = []; rows["calls_short"] = []; rows["calls_long"] = []; rows["street"] = []
    by_sym = {}     # v148 · the engine's record per name across its BUY-side calls — the calls of the day lean on it
    files = sorted(f for f in os.listdir(HIST_DIR) if f.startswith("engine_") and f.endswith(".json"))
    tdy = pd.Timestamp(today)
    def px_after(sym, d0, n):
        """the close n sessions after d0 — the daily panel, else the weekly, else now"""
        try:
            if D is not None and sym in D.columns:
                s = D[sym].dropna(); s = s[s.index > d0]
                if len(s) >= n:
                    return float(s.iloc[n - 1]), "exact"
                return (float(s.iloc[-1]), "to date") if len(s) else (None, None)
            if sym in W.columns:
                s = W[sym].dropna(); s = s[s.index > d0]
                k = max(1, int(round(n / 5)))
                if len(s) >= k:
                    return float(s.iloc[k - 1]), "weekly"
                return (float(s.iloc[-1]), "to date") if len(s) else (None, None)
        except Exception:
            pass
        return (U[sym]["px"], "to date") if sym in U else (None, None)
    for f in files:
        try:
            o = json.load(open(os.path.join(HIST_DIR, f)))
        except Exception:
            continue
        d0 = pd.Timestamp(o.get("date"))
        if d0 >= tdy:
            continue
        sessions = int(len(pd.bdate_range(d0 + pd.Timedelta(days=1), tdy)))
        for k, n in H.items():
            for p in (o.get("picks") or {}).get(k) or []:
                if sessions < n:
                    continue
                px1, how = px_after(p["sym"], d0, n)
                if px1 is None or not p.get("px"):
                    continue
                sg = 1 if p["side"] in ("BUY", "ACCUMULATE") else -1
                ret = sg * (px1 / p["px"] - 1) * 100
                nb, nb1 = o.get("nifty"), None
                try:
                    nb1, _ = px_after(MACRO["nifty"], d0, n) if (D is not None and MACRO["nifty"] in D.columns) else (None, None)
                except Exception:
                    pass
                excess = ret - sg * ((nb1 / nb - 1) * 100) if (nb and nb1) else None
                rows[k].append({"date": o["date"], "sym": p["sym"], "side": p["side"], "px": p["px"], "px1": _f(px1), "ret": _f(ret), "excess": _f(excess), "how": how})
                if k in ("today_buys", "short_buy", "long", "fno") and how != "to date":
                    bs = by_sym.setdefault(p["sym"], {"n": 0, "hits": 0, "sum": 0.0})
                    bs["n"] += 1; bs["hits"] += (1 if ret > 0 else 0); bs["sum"] += ret
        # v145 · the pairs: long leg minus short leg, equal rupees, ten sessions — market-neutral, so no Nifty excess
        for p in o.get("pairs") or []:
            if sessions < 10 or not p.get("px_a") or not p.get("px_b"):
                continue
            pa, howa = px_after(p["a"], d0, 10); pb, _ = px_after(p["b"], d0, 10)
            if pa is None or pb is None:
                continue
            ret = (pa / p["px_a"] - 1) * 100 - (pb / p["px_b"] - 1) * 100
            rows["pairs"].append({"date": o["date"], "sym": p["a"] + " / " + p["b"], "side": "PAIR", "px": p["px_a"], "px1": _f(pa), "ret": _f(ret), "excess": _f(ret), "how": howa})
        # v147 · the movers: did the next session move ≥ 1.5σ, and did the lean hold?
        for m in o.get("movers") or []:
            if sessions < 1 or not m.get("px") or not m.get("sig"):
                continue
            p1, how1 = px_after(m["sym"], d0, 1)
            if p1 is None:
                continue
            ret = (p1 / m["px"] - 1) * 100; moved = abs(ret) >= MOVE_SIG * m["sig"]
            dir_ok = None if m.get("lean") == "EITHER WAY" else ((ret > 0) == (m.get("lean") == "UP"))
            rows["movers"].append({"date": o["date"], "sym": m["sym"], "side": m.get("lean"), "px": m["px"], "px1": _f(p1), "ret": _f(ret), "excess": _f(abs(ret) / m["sig"], 2),
                                   "moved": bool(moved), "dir_ok": dir_ok, "p": m.get("p"), "how": how1})
        # v148 · the calls of the day: the short call at twenty sessions (did it reach the target before the stop?), the long at sixty, final at 250
        for c in o.get("calls") or []:
            try:
                n = 20 if c.get("kind") == "short" else 60
                if sessions < n or not c.get("px"):
                    continue
                p1, how1 = px_after(c["sym"], d0, n)
                if p1 is None:
                    continue
                ret = (p1 / c["px"] - 1) * 100
                nb1, _ = px_after(MACRO["nifty"], d0, n) if (D is not None and MACRO["nifty"] in D.columns) else (None, None)
                nb = o.get("nifty")
                excess = ret - ((nb1 / nb - 1) * 100) if (nb and nb1) else None
                tgt_hit = stopped = None
                if D is not None and c["sym"] in D.columns and c.get("target") and c.get("stop"):
                    path = D[c["sym"]].dropna(); path = path[path.index > d0].iloc[:n]
                    if len(path):
                        it = next((i for i, x in enumerate(path.values) if x >= c["target"]), None)
                        ist_ = next((i for i, x in enumerate(path.values) if x <= c["stop"]), None)
                        tgt_hit = it is not None and (ist_ is None or it < ist_)
                        stopped = ist_ is not None and (it is None or ist_ < it)
                final = sessions >= 250 if c.get("kind") == "long" else True
                if c.get("kind") == "long" and final:
                    p250, _h = px_after(c["sym"], d0, 250)
                    if p250 is not None:
                        ret = (p250 / c["px"] - 1) * 100
                rows["calls_" + ("short" if c.get("kind") == "short" else "long")].append({"date": o["date"], "sym": c["sym"], "side": "BUY", "px": c["px"], "px1": _f(p1), "ret": _f(ret), "excess": _f(excess),
                                                                                              "tgt_hit": tgt_hit, "stopped": stopped, "conv": c.get("conv"), "final": bool(final), "how": how1})
            except Exception:
                continue
        # v148 · the Street: sixty sessions on, whose implied path (pro rata of the twelve-month upside) did the price come closer to?
        for r in o.get("street") or []:
            try:
                if sessions < 60 or not r.get("px") or r.get("up_e") is None or r.get("up_s") is None:
                    continue
                p1, how1 = px_after(r["sym"], d0, 60)
                if p1 is None:
                    continue
                ret = (p1 / r["px"] - 1) * 100
                ie, is_ = r["up_e"] * 60 / 250.0, r["up_s"] * 60 / 250.0
                rows["street"].append({"date": o["date"], "sym": r["sym"], "side": "ENGINE %+.0f%% · STREET %+.0f%%" % (r["up_e"], r["up_s"]), "px": r["px"], "px1": _f(p1), "ret": _f(ret),
                                       "excess": _f(abs(ret - is_) - abs(ret - ie)), "engine_closer": bool(abs(ret - ie) < abs(ret - is_)), "err_e": _f(abs(ret - ie), 1), "err_s": _f(abs(ret - is_), 1), "how": how1})
            except Exception:
                continue
        # v146 · the macro post-mortem: five sessions on, what did the regime call, the session's call and the sleeves pay?
        mz = o.get("macro")
        if mz and sessions >= 5 and mz.get("nifty"):
            try:
                n1, hown = px_after(MACRO["nifty"], d0, 5)
                if n1:
                    nret = (n1 / mz["nifty"] - 1) * 100
                    def sret(sym):
                        p0 = (mz.get("px") or {}).get(sym)
                        if not p0:
                            return None
                        p1, _ = px_after(sym, d0, 5)
                        return (p1 / p0 - 1) * 100 if p1 else None
                    book = [(x["pct"], sret(x["sym"])) for x in (mz.get("book") or [])]
                    bk = [(w, r) for w, r in book if r is not None]
                    book_ret = (sum(w * r for w, r in bk) / 100.0) if bk else None
                    ov = [r for r in (sret(x) for x in (mz.get("over") or [])) if r is not None]
                    un = [r for r in (sret(x) for x in (mz.get("under") or [])) if r is not None]
                    call = mz.get("call") or ""
                    call_ok = (nret > 0) if "BUY" in call else ((nret < 0) if "SELL" in call else (abs(nret) < 1.5))
                    rows["macro"].append({"date": o["date"], "sym": mz.get("regime"), "side": call, "px": mz["nifty"], "px1": _f(n1), "ret": _f(nret),
                                          "excess": (_f(book_ret - nret) if book_ret is not None else None), "book": _f(book_ret), "over": (_f(float(np.mean(ov))) if ov else None),
                                          "under": (_f(float(np.mean(un))) if un else None), "call_ok": bool(call_ok), "probs": mz.get("probs"), "how": hown})
            except Exception:
                pass
    rec = {}
    H["pairs"] = 10; H["macro"] = 5; H["movers"] = 1; H["calls_short"] = 20; H["calls_long"] = 60; H["street"] = 60
    for k, rs in rows.items():
        if not rs:
            rec[k] = {"n": 0}
            continue
        r = [x["ret"] for x in rs if x["ret"] is not None]
        ex = [x["excess"] for x in rs if x["excess"] is not None]
        rec[k] = {"n": len(r), "hit": _f(100 * np.mean([1 if x > 0 else 0 for x in r]), 0), "avg": _f(float(np.mean(r)), 2),
                  "avg_excess": (_f(float(np.mean(ex)), 2) if ex else None), "h": H[k], "last": rs[-12:]}
        if k == "movers":
            # the movers' record: how many moved ≥ 1.5σ (the base rate is ~15–20%), the direction's hit rate where a lean was given, the average |move| in σ
            mv = [x for x in rs if x.get("moved") is not None]; dr = [x for x in rs if x.get("dir_ok") is not None]
            rec[k].update({"hit": (_f(100 * np.mean([1 if x["moved"] else 0 for x in mv]), 0) if mv else None), "dir_hit": (_f(100 * np.mean([1 if x["dir_ok"] else 0 for x in dr]), 0) if dr else None),
                           "avg": (_f(float(np.mean([abs(x["ret"]) for x in rs if x.get("ret") is not None])), 2) if rs else None), "avg_sig": rec[k]["avg_excess"], "n_dir": len(dr)})
        if k in ("calls_short", "calls_long"):
            th = [x for x in rs if x.get("tgt_hit") is not None]
            rec[k].update({"tgt_hit": (_f(100 * np.mean([1 if x["tgt_hit"] else 0 for x in th]), 0) if th else None), "stopped": (_f(100 * np.mean([1 if x.get("stopped") else 0 for x in th]), 0) if th else None),
                           "n_final": sum(1 for x in rs if x.get("final"))})
        if k == "street":
            ec = [x for x in rs if x.get("engine_closer") is not None]
            rec[k].update({"engine_closer": (_f(100 * np.mean([1 if x["engine_closer"] else 0 for x in ec]), 0) if ec else None),
                           "err_engine": (_f(float(np.mean([x["err_e"] for x in rs if x.get("err_e") is not None])), 1) if rs else None),
                           "err_street": (_f(float(np.mean([x["err_s"] for x in rs if x.get("err_s") is not None])), 1) if rs else None)})
        if k == "macro":
            # the macro record reads differently: the call's hit rate, the model book against the Nifty, over minus under
            co = [x for x in rs if x.get("call_ok") is not None]
            sp = [x["over"] - x["under"] for x in rs if x.get("over") is not None and x.get("under") is not None]
            rec[k].update({"call_hit": (_f(100 * np.mean([1 if x["call_ok"] else 0 for x in co]), 0) if co else None),
                           "book_vs_nifty": rec[k]["avg_excess"], "over_minus_under": (_f(float(np.mean(sp)), 2) if sp else None), "n_spread": len(sp)})
    rec["by_sym"] = {s: {"n": v["n"], "hit": _f(100.0 * v["hits"] / v["n"], 0), "avg": _f(v["sum"] / v["n"], 2)} for s, v in by_sym.items() if v["n"] >= 2}
    return rec


def shock_block(B, W):
    lv = {}
    try:
        lv["nifty"] = (B["IN_IDX"].get("Nifty 50") or {}).get("p")
        lv["inr"] = (B["FX"].get("USD/INR") or {}).get("p")
        lv["brent"] = (B["ENERGY"].get("Brent Oil") or {}).get("p")
        lv["vix"] = _f(W[MACRO["vix"]].dropna().iloc[-1]) if MACRO["vix"] in W.columns else (B["MACRO_X"].get("vix") or {}).get("v")
        lv["repo"] = B["MACRO_LIVE"].get("repo")
        lv["gsec10"] = (B["MACRO_X"].get("gsec10") or {}).get("v")
    except Exception:
        pass
    presets = {
        "crude120": {"label": "Crude to $120", "brent": (_f((120 / lv["brent"] - 1) * 100) if lv.get("brent") else 15.0), "inr": 1.5, "rates": 1.0, "vix": 15.0, "nifty": -2.5,
                      "note": "a supply shock: Brent re-prices, the rupee gives 1.5%, yields rise ~20bp, VIX +15%, the index −2.5%"},
        "rbi50": {"label": "RBI hikes 50bp", "rates": GILT_DURATION * 0.5, "nifty": -2.0, "inr": -0.8, "vix": 10.0, "brent": 0.0,
                  "note": "a 50bp surprise: the 5Y gilt falls ~%.1f%% (duration %.1f), the rupee firms, the index −2%%" % (GILT_DURATION * 0.5, GILT_DURATION)},
        "inr100": {"label": "Rupee to 100", "inr": (_f((100 / lv["inr"] - 1) * 100) if lv.get("inr") else 3.5), "rates": 0.8, "vix": 12.0, "nifty": -2.0, "brent": 0.0,
                   "note": "the rupee slides to 100: importers and borrowers in dollars hurt, exporters gain; yields drift up, the index −2%"},
        "fiisell": {"label": "FII selling (₹20,000 cr)", "nifty": -4.0, "inr": 1.2, "vix": 25.0, "rates": 0.5, "brent": 0.0,
                    "note": "a foreign-selling week: the index −4%, the rupee −1.2%, VIX +25%"},
        "goldilocks": {"label": "Goldilocks surprise", "nifty": 3.0, "inr": -1.0, "vix": -15.0, "rates": -1.0, "brent": -5.0,
                       "note": "CPI prints low, growth holds: the index +3%, the rupee firms, yields fall, VIX −15%"},
    }
    return {"levels": lv, "presets": presets, "how": "Δshare% ≈ Σ β_factor × Δfactor% (β from 3 years of weekly returns, ridge); the index leg uses the share's Nifty beta; 'rates' is the 5Y gilt ETF price (−duration × Δyield)"}


# ─────────────────────────────────────────────────────────────────────────────
# 9 · the market line (one source for the session's call)
# ─────────────────────────────────────────────────────────────────────────────
def market_line(B, U, V, W, gate, regime, ps):
    tw = ((B["ML_OUTPUT"] or {}).get("tomorrow") or {})
    nif = (B["IN_IDX"].get("Nifty 50") or {})
    up = sum(1 for u in U.values() if (u["d1"] or 0) > 0 and (u["turn"] or 0) >= LIQUID_CR)
    dn = sum(1 for u in U.values() if (u["d1"] or 0) < 0 and (u["turn"] or 0) >= LIQUID_CR)
    buys = sum(1 for v in V.values() if (v.get("short") or {}).get("side") == "BUY")
    sells = sum(1 for v in V.values() if (v.get("short") or {}).get("side") == "SELL")
    acc = sum(1 for v in V.values() if (v.get("long") or {}).get("side") == "ACCUMULATE")
    pu = tw.get("p_up")
    try:
        vix = _f(W[MACRO["vix"]].dropna().iloc[-1]) if MACRO["vix"] in W.columns else None
    except Exception:
        vix = None
    if pu is not None and pu >= 0.55:
        call, how = "BUY DIPS", "the overnight model leans up (%d%%)" % round(100 * pu)
    elif pu is not None and pu <= 0.45:
        call, how = "SELL RALLIES", "the overnight model leans down (%d%%)" % round(100 * (1 - pu))
    else:
        call, how = "RANGE · TRADE THE EDGES", "no overnight lean"
    if gate:
        call = call + " · HALF SIZE"
        how += " · the gate is on: every size is halved, the bar for a buy is higher"
    return {"nifty": nif.get("p"), "nifty_d1": nif.get("d"), "regime": regime, "gate": bool(gate), "stance": (ps or {}).get("stance"),
            "stress": (ps or {}).get("stress"), "state": (ps or {}).get("market_state"), "vix": vix, "p_up": pu, "call": call, "call_how": how,
            "breadth": {"up": up, "down": dn}, "n_buy": buys, "n_sell": sells, "n_accumulate": acc}


# ─────────────────────────────────────────────────────────────────────────────
# 10 · the arena's candidate pool — one source for the books
# ─────────────────────────────────────────────────────────────────────────────
def arena_pool(U, V, P):
    pool = []
    for s, v in V.items():
        st = v.get("short") or {}
        if st.get("side") in ("BUY", "SELL") and (U[s]["turn"] or 0) >= LIQUID_CR and U[s]["sector"] != "ETF":
            if st["side"] == "SELL" and not U[s]["fno"]:
                continue
            pool.append({"src": "engine", "key": s, "name": U[s]["nm"], "side": "LONG" if st["side"] == "BUY" else "SHORT", "stop_pct": st["stop_pct"],
                         "tgt_pct": st["tgt_pct"], "h": st["h"], "conv": int(st["score"] if st["side"] == "BUY" else 100 - st["score"]),
                         "why": "the engine: short-term %s %d/100 — %s" % (st["side"], st["score"], "; ".join(st.get("why") or [])[:140])})
    for p in P.get("intraday") or []:
        pool.append({"src": "engine_intra", "key": p["sym"], "name": p["nm"], "side": "LONG" if p["side"] == "BUY" else "SHORT", "stop_pct": 1.5, "tgt_pct": 3.0, "h": 1,
                     "conv": int(p.get("score") or 50), "why": "in play today: the intraday screen (σ1d %.1f%%)" % (p.get("sig1d") or 0)})
    for p in P.get("long") or []:
        pool.append({"src": "engine_long", "key": p["sym"], "name": p["nm"], "side": "LONG", "stop_pct": 12.0, "tgt_pct": 24.0, "h": 60,
                     "conv": int(p.get("score") or 50), "why": "the engine's long-term accumulate %d/100" % (p.get("score") or 0)})
    pool.sort(key=lambda c: -c["conv"])
    return pool[:160]


# ─────────────────────────────────────────────────────────────────────────────
# 11 · WHERE TO BE — the regime → asset map (v145)
#     what each Indian asset has paid in each regime since 2015, measured on a long index in rupees (the ETF is
#     what you trade), the trend on the ETF itself, a word, and a model allocation for a ₹10 lakh book
# ─────────────────────────────────────────────────────────────────────────────
ETF_FILE = "engine_etf.json"
#          key         ETF (NSE)     name                   class                 study proxy (Yahoo)   × USD/INR
SLEEVES = [("nifty", "NIFTYBEES", "Nifty 50", "Equity · large caps", "^NSEI", False),
           ("next50", "JUNIORBEES", "Nifty Next 50", "Equity · large caps", "JUNIORBEES.NS", False),
           ("midcap", "MID150BEES", "Midcaps", "Equity · mid caps", "MOM100.NS", False),
           ("smallcap", "SMALLCAP", "Smallcaps", "Equity · small caps", "^CNXSC", False),
           ("banks", "BANKBEES", "Banks", "Equity · sector", "^NSEBANK", False),
           ("psubanks", "PSUBNKBEES", "PSU banks", "Equity · sector", "^CNXPSUBANK", False),
           ("it", "ITBEES", "IT", "Equity · sector", "^CNXIT", False),
           ("pharma", "PHARMABEES", "Pharma", "Equity · sector", "^CNXPHARMA", False),
           ("auto", "AUTOBEES", "Auto", "Equity · sector", "^CNXAUTO", False),
           ("fmcg", "FMCGIETF", "FMCG", "Equity · sector", "^CNXFMCG", False),
           ("metals", "METALIETF", "Metals", "Equity · sector", "^CNXMETAL", False),
           ("energy", "OILIETF", "Oil & gas", "Equity · sector", "^CNXENERGY", False),
           ("cpse", "CPSEETF", "PSUs (CPSE)", "Equity · theme", "CPSEETF.NS", False),
           ("infra", "INFRABEES", "Infrastructure", "Equity · theme", "^CNXINFRA", False),
           ("realty", "MOREALTY", "Realty", "Equity · sector", "^CNXREALTY", False),
           ("consum", "CONSUMBEES", "Consumption", "Equity · theme", "CONSUMBEES.NS", False),
           ("gold", "GOLDBEES", "Gold", "Gold", "GC=F", True),
           ("silver", "SILVERBEES", "Silver", "Silver", "SI=F", True),
           ("gilt5", "GILT5YBEES", "Gilts · 5-year", "Bonds", "GILT5YBEES.NS", False),
           ("giltlong", "LTGILTBEES", "Gilts · long", "Bonds", "LTGILTBEES.NS", False),
           ("cash", "LIQUIDBEES", "Cash (liquid ETF)", "Cash", None, False),
           ("nasdaq", "MON100", "Nasdaq 100 (in ₹)", "Global", "^NDX", True),
           ("spx", "MASPTOP50", "S&P 500 (in ₹)", "Global", "^GSPC", True),
           ("hsi", "HNGSNGBEES", "Hang Seng", "Global", "HNGSNGBEES.NS", False)]
REGIMES = ("Goldilocks", "Reflation", "Stagflation", "Disinflation")
EXTRA_PANEL = ["INR=X", "BZ=F", "^INDIAVIX", "DX-Y.NYB", "^TNX"]     # the nowcast's market series ride with the sleeves (twelve years)
BASE_ALLOC = {"Goldilocks": (70, 10, 15, 5), "Reflation": (65, 15, 5, 15), "Stagflation": (35, 30, 10, 25), "Disinflation": (55, 10, 30, 5)}   # equity · metals · bonds · cash
TILT = {"Goldilocks": ["midcap", "smallcap", "consum", "banks", "auto", "realty"],
        "Reflation": ["banks", "midcap", "metals", "infra", "cpse", "auto", "psubanks"],
        "Stagflation": ["pharma", "fmcg", "it", "energy", "nasdaq"],
        "Disinflation": ["it", "fmcg", "pharma", "nasdaq", "consum"]}


def fetch_sleeves(offline, max_age_h=20):
    """weekly closes, twelve years, for every sleeve's ETF and its study proxy (+ USD/INR) — cached in engine_etf.json
    and committed, so a pass without Yahoo still has the map"""
    cached = None
    try:
        o = json.load(open(ETF_FILE))
        age = (now_ist() - dt.datetime.strptime(o["updated"], "%Y-%m-%d %H:%M").replace(tzinfo=IST)).total_seconds() / 3600
        cached = pd.DataFrame(o["series"], index=pd.to_datetime(o["dates"], format="%Y%m%d"))
        if offline or age <= max_age_h:
            return cached, "cache · %s" % o["updated"]
    except Exception:
        cached = None
    if offline:
        return cached, "none (offline)"
    try:
        import yfinance as yf
        syms = sorted({x for s in SLEEVES for x in ((s[1] + ".NS") if s[1] else None, s[4]) if x} | set(EXTRA_PANEL))
        raw = yf.download(syms, period="12y", interval="1wk", progress=False, threads=True, auto_adjust=True, group_by="column")
        df = _close_frame(raw, syms)
        if df is None or df.shape[1] < 10:
            raise RuntimeError("thin answer")
        df = df.dropna(how="all")
        json.dump({"updated": now_ist().strftime("%Y-%m-%d %H:%M"), "dates": [d.strftime("%Y%m%d") for d in df.index],
                   "series": {str(c): [(_f(v, 4) if pd.notna(v) else None) for v in df[c].values] for c in df.columns}}, open(ETF_FILE, "w"), separators=(",", ":"))
        return df, "Yahoo · %d series · 12y weekly" % df.shape[1]
    except Exception as e:
        log("sleeves: Yahoo unavailable (%s)" % type(e).__name__)
        return cached, ("cache (stale)" if cached is not None else "none")


def _fwd(series, k):
    """forward k-week return in %, aligned to the start week"""
    return (series.shift(-k) / series - 1) * 100


def alloc_block(U, X, regime, gate, repo, probs=None):
    rows = []
    labels = regime_labels(X.index) if (X is not None and len(X)) else None
    inr = X["INR=X"] if (X is not None and "INR=X" in X.columns) else None
    for key, etf, nm, cls, proxy, fx in SLEEVES:
        u = U.get(etf) or {}
        r = {"key": key, "sym": etf, "nm": nm, "cls": cls, "px": u.get("px"), "d1": u.get("d1"), "turn": u.get("turn"), "proxy": proxy,
             "s": (u and None), "thin": bool(u.get("turn") is not None and (u.get("turn") or 0) < 2)}
        if key == "cash":
            rp = float(repo or 5.5)
            r.update({"word": "CASH", "trend": None, "study": {"avg13": _f(rp / 4, 2), "note": "the repo rate, %.2f%% a year" % rp},
                      "why": ["cash pays the repo, %.2f%% a year — it is the residual of every allocation, and the whole of it when nothing else earns a place" % rp]})
            rows.append(r)
            continue
        ser = None; es = None; study_on = None
        if X is not None:
            if proxy and proxy in X.columns and int(X[proxy].notna().sum()) >= 80:     # Yahoo lists some NSE sector indices with no history at all
                ser = X[proxy].copy()
                if fx and inr is not None:
                    ser = ser * inr
                study_on = proxy
            if etf + ".NS" in X.columns:
                es = X[etf + ".NS"].dropna()
            if ser is None and es is not None:
                ser = es; study_on = "the ETF"
        # the trend — on the ETF itself where it has a year, else on the study series
        tr = None
        base = es if (es is not None and len(es) >= 60) else (ser.dropna() if ser is not None else None)
        if base is not None and len(base) >= 14:
            b = base.dropna()
            px = float(r["px"]) if (r.get("px") and es is not None and len(es) >= 60) else float(b.iloc[-1])
            ma40 = float(b.iloc[-40:].mean())
            tr = {"r4": _f((px / float(b.iloc[-5]) - 1) * 100) if len(b) > 5 else None, "r13": _f((px / float(b.iloc[-14]) - 1) * 100) if len(b) > 14 else None,
                  "r26": _f((px / float(b.iloc[-27]) - 1) * 100) if len(b) > 27 else None, "r52": _f((px / float(b.iloc[-53]) - 1) * 100) if len(b) > 53 else None,
                  "vs40": _f((px / ma40 - 1) * 100), "hi52": _f(float(b.iloc[-52:].max())), "lo52": _f(float(b.iloc[-52:].min()))}
            tr["pos52"] = _f((px - tr["lo52"]) / (tr["hi52"] - tr["lo52"]) * 100, 0) if (tr["hi52"] and tr["lo52"] and tr["hi52"] > tr["lo52"]) else None
            tr["up"] = bool((tr["vs40"] or 0) > 0 and (tr["r13"] or 0) > 0)
            tr["down"] = bool((tr["vs40"] or 0) < 0 and (tr["r13"] or 0) < 0)
        # the study — the long series since 2015, labelled by regime
        st = None
        if ser is not None and labels is not None:
            s2 = ser.dropna()
            s2 = s2[s2.index >= "2015-01-01"]
            if len(s2) >= 60:
                f13 = _fwd(s2, 13); f4 = _fwd(s2, 4); lab = labels.reindex(s2.index)
                by = {}
                for R in REGIMES:
                    m = (lab == R) & f13.notna()
                    if int(m.sum()) >= 8:
                        v = f13[m]; v4 = f4[(lab == R) & f4.notna()]
                        by[R] = {"n": int(m.sum()), "avg13": _f(float(v.mean()), 1), "hit13": _f(100 * float((v > 0).mean()), 0), "avg4": (_f(float(v4.mean()), 1) if len(v4) else None)}
                a13 = _f(float(f13.dropna().mean()), 1)
                cur = by.get(regime) or {}
                st = {"since": s2.index[0].strftime("%Y-%m"), "weeks": int(len(s2)), "all13": a13, "by": by, "n13": cur.get("n", 0), "avg13": cur.get("avg13"),
                      "hit13": cur.get("hit13"), "avg4": cur.get("avg4"), "edge13": (_f(cur["avg13"] - a13, 1) if (cur.get("avg13") is not None and a13 is not None) else None),
                      "on": ("the ETF" if (study_on or "").endswith(".NS") else study_on)}
        # the word: the trend on the ETF, confirmed or contradicted by the regime's record
        word = "NEUTRAL"; why = []
        sig = bool(st and (st.get("n13") or 0) >= 26 and st.get("edge13") is not None and abs(st["edge13"]) >= 1.0)
        if tr and tr["up"] and (not sig or st["edge13"] > 0):
            word = "OVERWEIGHT"
        elif tr and tr["down"] and (not sig or st["edge13"] < 0):
            word = "UNDERWEIGHT"
        if tr:
            why.append("trend: %s the 40-week average (%s), %s over 13 weeks" % ("above" if (tr["vs40"] or 0) > 0 else "below", ("%+.1f%%" % tr["vs40"]) if tr["vs40"] is not None else "—", ("%+.1f%%" % tr["r13"]) if tr["r13"] is not None else "—"))
        if st and st.get("avg13") is not None:
            why.append("in %s since %s: %+.1f%% a quarter on average, up %d%% of the time (n = %d weeks) · all regimes %+.1f%%" % (regime, st["since"], st["avg13"], int(st["hit13"] or 0), st["n13"], st["all13"] or 0))
            if sig and tr and ((tr["up"] and st["edge13"] < 0) or (tr["down"] and st["edge13"] > 0)):
                why.append("the regime's record and the trend disagree — neutral until one gives")
        elif st is None:
            why.append("no long study for this sleeve yet" + (" (no price history on this pass)" if X is None else " (short history)"))
        if r["thin"]:
            why.append("thin: under ₹2 cr a day — use limit orders, or the alternative ETF")
        r.update({"trend": tr, "study": st, "word": word, "why": why})
        rows.append(r)
    # ── the model allocation for a ₹10 lakh book ──
    eq, met, bd, cash = BASE_ALLOC.get(regime, BASE_ALLOC["Reflation"])
    blended = False
    if probs and sum(probs.values()):
        tot = float(sum(probs.values()))
        eq, met, bd, cash = [round(sum(probs[R] / tot * BASE_ALLOC[R][i] for R in BASE_ALLOC if R in probs), 1) for i in range(4)]
        blended = True
    if gate:
        eq -= 10; cash += 10
    byk = {r["key"]: r for r in rows}

    def word_rank(k):
        w = (byk.get(k) or {}).get("word")
        return 0 if w == "OVERWEIGHT" else 1 if w == "NEUTRAL" else 2
    pool = [k for k in TILT.get(regime, []) if k in byk and byk[k]["word"] != "UNDERWEIGHT" and not byk[k].get("thin")]
    pool = sorted(pool, key=lambda k: (word_rank(k), -((byk[k].get("study") or {}).get("edge13") or 0), -((byk[k].get("trend") or {}).get("r13") or 0)))
    others = [r["key"] for r in rows if (r["cls"].startswith("Equity") or r["cls"] == "Global") and r["key"] not in ("nifty", "next50") and r["key"] not in pool and r["word"] == "OVERWEIGHT" and not r.get("thin")]
    others = sorted(others, key=lambda k: -((byk[k].get("trend") or {}).get("r13") or 0))
    sats = [k for k in pool if byk[k]["word"] == "OVERWEIGHT"][:3]
    if len(sats) < 3:
        sats += [k for k in others if k not in sats][:3 - len(sats)]
    if len(sats) < 3:
        sats += [k for k in pool if k not in sats][:3 - len(sats)]
    core = eq * 0.5; sat = eq - core
    lines = [["nifty", round(core * 0.7, 1), "the core: the index, whatever the regime"], ["next50", round(core * 0.3, 1), "the core's second leg: the next fifty"]]
    if sats:
        each = round(sat / len(sats), 1)
        for k in sats:
            lines.append([k, each, ("%s tilt" % regime.lower() if k in TILT.get(regime, []) else "trending") + ": " + ((byk[k].get("why") or ["—"])[0])])
    else:
        lines[0][1] = round(core * 0.7 + sat, 1); lines[0][2] = "the core takes the satellite money: nothing earns a tilt today"
    if met:
        if (byk.get("silver") or {}).get("word") == "OVERWEIGHT":
            lines.append(["gold", round(met * 0.7, 1), "the metal sleeve: gold"]); lines.append(["silver", round(met * 0.3, 1), "silver is trending — a third of the metal sleeve"])
        else:
            lines.append(["gold", float(met), "the metal sleeve: gold (silver is not trending)"])
    if bd:
        bk = "giltlong" if regime in ("Disinflation", "Goldilocks") else "gilt5"
        bwhy = ("duration pays in %s" % regime.lower()) if bk == "giltlong" else "short gilts: the carry without the duration risk"
        if (byk.get(bk) or {}).get("word") == "UNDERWEIGHT":
            lines.append([bk, round(bd / 2, 1), "bonds at half size: gilts are trending down"]); cash += bd / 2
        else:
            lines.append([bk, float(bd), bwhy])
    lines.append(["cash", round(cash, 1), "the residual" + (" · the gate moves ten points here" if gate else "")])
    alloc = []
    for k, pct, why in lines:
        r = byk.get(k) or {}
        amt = BOOK * pct / 100
        alloc.append({"key": k, "sym": r.get("sym"), "nm": r.get("nm"), "cls": r.get("cls"), "pct": pct, "inr": round(amt), "units": (int(amt // r["px"]) if r.get("px") else None),
                      "px": r.get("px"), "word": r.get("word"), "why": why})
    return {"regime": regime, "gate": bool(gate), "book": BOOK, "rows": rows, "alloc": alloc, "base": {"equity": round(eq, 1), "metals": round(met, 1), "bonds": round(bd, 1), "cash": round(cash, 1)}, "blended": blended, "probs": probs,
            "rule": "base weights by regime — equity / metals / bonds / cash: Goldilocks 70/10/15/5, Reflation 65/15/5/15, Stagflation 35/30/10/25, Disinflation 55/10/30/5 — blended by the nowcast's regime probabilities (so the book never jumps on a label change); the gate moves ten points from equity to cash. Half the equity is the core (Nifty 50 and Next 50); half goes to three sleeves the regime favours that are also trending — never to an UNDERWEIGHT. Gold is the metal sleeve (silver joins when it trends). Long gilts in Disinflation and Goldilocks, short gilts otherwise, halved when gilts trend down. Cash is the residual.",
            "how": "each sleeve is measured on its long index in rupees since 2015 (the ETF is what you trade), labelled week by week with the same CPI × IIP regime path the rest of the page uses; the number is the average forward 13-week return in that regime and the share of weeks that paid. Windows overlap, so n counts weeks, not independent quarters. Trend is the ETF against its 40-week average and its 13-week return; the word needs the trend, and the regime's record may confirm or veto it. A map of what each regime has paid — not a forecast, not a backtest of the allocation."}


# ─────────────────────────────────────────────────────────────────────────────
# 14 · THE NOWCAST (v146) — what the market is pricing about growth, inflation and liquidity this quarter,
#     and the regime as four probabilities instead of one label. The official print (CPI, IIP, monthly, late)
#     is the anchor; the market's thirteen-week impulses nudge it; the quadrant lines (CPI 4, IIP 3) become
#     probabilities through a logistic with the series' own noise. Prometheus-style measurement with free data.
# ─────────────────────────────────────────────────────────────────────────────
def _z13(series, since="2015-01-01"):
    """13-week log change, z-scored against its own history since 2015; clipped at ±3; a data break (a move the
    series' own history never saw at 5σ) returns no read rather than a wrong one"""
    try:
        s = series.dropna()
        s = s[s.index >= since]
        if len(s) < 80 or s.index[-1] < series.index[-1] - pd.Timedelta(days=21):
            return None, None
        ch = np.log(s.astype(float)).diff(13).dropna()
        if len(ch) < 60 or float(ch.std()) == 0:
            return None, None
        z = float((ch.iloc[-1] - ch.mean()) / ch.std())
        if abs(z) > 5:
            return None, None
        return max(-3.0, min(3.0, z)), float(ch.iloc[-1] * 100)
    except Exception:
        return None, None


def _basket(X, cols, min_n=300):
    """an equal-weight log basket over the columns that have a long, complete history — never a composite whose
    membership changes along the way (that is how a −8σ appears out of nowhere)"""
    use = [c for c in cols if c in X.columns and int(X[c].notna().sum()) >= min_n and pd.notna(X[c].dropna().iloc[-1])]
    if not use:
        return None, []
    df = X[use].dropna()
    if len(df) < min_n:
        return None, []
    return np.exp(np.log(df.astype(float)).mean(axis=1)), use


def _sig(x):
    return 1.0 / (1.0 + math.exp(-x))


def nowcast_block(B, X, regime, repo):
    ML = B["MACRO_LIVE"] or {}
    cpi = ML.get("cpi") if ML.get("cpi") is not None else float(REGIME_ANCHORS[-1][1])
    iip = ML.get("iip") if ML.get("iip") is not None else float(REGIME_ANCHORS[-1][2])
    parts = {"growth": [], "inflation": [], "liquidity": []}

    def add(key, label, z, chg, w, flip=False):
        if z is None:
            return
        z = -z if flip else z; chg = -chg if (flip and chg is not None) else chg
        parts[key].append({"label": label, "z": _f(z, 2), "chg": _f(chg, 1), "w": w})
    if X is not None and len(X):
        inr = X["INR=X"] if "INR=X" in X.columns else None
        def ser(c, fx=False):
            if c not in X.columns:
                return None
            v = X[c]
            return (v * inr) if (fx and inr is not None) else v
        # cyclicals against defensives — long, complete series only (Yahoo's ^CNXAUTO/^CNXMETAL/… carry no history)
        cycb, cycu = _basket(X, ["^NSEBANK", "MOM100.NS", "CPSEETF.NS", "^CNXAUTO", "^CNXMETAL", "^CNXREALTY", "^CNXINFRA"])
        dfnb, dfnu = _basket(X, ["^CNXIT", "^CNXPHARMA", "CONSUMBEES.NS", "^CNXFMCG"])
        if cycb is not None and dfnb is not None:
            sp = (cycb / dfnb).dropna()
            z, ch = _z13(sp); add("growth", "cyclicals against defensives (%s vs %s)" % (", ".join(x.replace(".NS", "").replace("^", "") for x in cycu), ", ".join(x.replace(".NS", "").replace("^", "") for x in dfnu)), z, ch, 0.5)
        if "MOM100.NS" in X.columns and "^NSEI" in X.columns:
            z, ch = _z13(X["MOM100.NS"] / X["^NSEI"]); add("growth", "midcaps against the Nifty", z, ch, 0.25)
        if "^NSEI" in X.columns:
            z, ch = _z13(X["^NSEI"]); add("growth", "the Nifty itself", z, ch, 0.25)
        b = ser("BZ=F", True)
        if b is not None:
            z, ch = _z13(b); add("inflation", "Brent in rupees", z, ch, 0.4)
        if inr is not None:
            z, ch = _z13(inr); add("inflation", "the rupee (USD/INR up = imported inflation)", z, ch, 0.25)
        g = ser("GC=F", True)
        if g is not None:
            z, ch = _z13(g); add("inflation", "gold in rupees", z, ch, 0.15)
        if "GILT5YBEES.NS" in X.columns:
            z, ch = _z13(X["GILT5YBEES.NS"]); add("inflation", "the 5-year gilt (price down = yields up)", z, ch, 0.2, flip=True)
            z, ch = _z13(X["GILT5YBEES.NS"]); add("liquidity", "the 5-year gilt bid", z, ch, 0.25)
        if "^INDIAVIX" in X.columns:
            z, ch = _z13(X["^INDIAVIX"]); add("liquidity", "India VIX (down = easier)", z, ch, 0.35, flip=True)
        if "^NSEBANK" in X.columns and "^NSEI" in X.columns:
            z, ch = _z13(X["^NSEBANK"] / X["^NSEI"]); add("liquidity", "banks against the Nifty", z, ch, 0.2)
        if "DX-Y.NYB" in X.columns:
            z, ch = _z13(X["DX-Y.NYB"]); add("liquidity", "the dollar (DXY down = easier for EM)", z, ch, 0.2, flip=True)
    # v147 · foreign flows: the 20-session cumulative FII net, z-scored against the trail's own history (the trail accrues a row a day; it needs sixty)
    try:
        tr = (B["FLOWS_LIVE"] or {}).get("trail") or []
        if len(tr) >= 60:
            fl = pd.Series([float(x[1]) for x in tr], index=pd.to_datetime([str(x[0]).replace("-", " ") for x in tr], format="mixed", dayfirst=True)).sort_index()
            cum = fl.rolling(20).sum().dropna()
            if len(cum) >= 40 and float(cum.std()) > 0:
                zf = float((cum.iloc[-1] - cum.mean()) / cum.std())
                parts["liquidity"].append({"label": "foreign flows (20-session net FII, ₹ cr)", "z": _f(max(-3.0, min(3.0, zf)), 2), "chg": _f(float(cum.iloc[-1]), 0), "w": 0.3})
        else:
            parts.setdefault("notes", []).append("foreign flows join the liquidity impulse once the FII trail has sixty sessions (%d now)" % len(tr))
    except Exception:
        pass
    imp = {}
    notes = parts.pop("notes", [])
    for k, ps in parts.items():
        wsum = sum(p["w"] for p in ps)
        imp[k] = {"z": (_f(sum(p["z"] * p["w"] for p in ps) / wsum, 2) if wsum else None), "parts": ps, "n": len(ps)}
    gz = imp["growth"]["z"] or 0.0; pz = imp["inflation"]["z"] or 0.0; lz = imp["liquidity"]["z"] or 0.0
    # one σ of market impulse ≈ 1.2 points of IIP growth and 0.4 points of CPI over the quarter — a judgment, printed as such
    iip_now = float(iip) + 1.2 * gz; cpi_now = float(cpi) + 0.4 * pz
    p_hot = _sig((cpi_now - 4.0) / 0.5); p_grow = _sig((iip_now - 3.0) / 1.0)
    probs = {"Reflation": p_hot * p_grow, "Goldilocks": (1 - p_hot) * p_grow, "Stagflation": p_hot * (1 - p_grow), "Disinflation": (1 - p_hot) * (1 - p_grow)}
    probs = {k: _f(100 * v, 0) for k, v in probs.items()}
    lean = max(probs, key=probs.get)
    def word(z, up, down, flat):
        if z is None:
            return "no market read"
        return up if z >= 0.75 else (down if z <= -0.75 else flat)
    words = {"growth": word(gz, "the market is pricing growth up", "the market is pricing growth down", "no strong growth impulse"),
             "inflation": word(pz, "the market is pricing inflation up", "the market is pricing inflation down", "no strong inflation impulse"),
             "liquidity": word(lz, "liquidity easing", "liquidity tightening", "liquidity neutral")}
    return {"official": {"cpi": _f(cpi, 2), "iip": _f(iip, 2), "label": regime, "as_of": (B["REGIME_LIVE"] or {}).get("inputs_sig")},
            "impulses": imp, "words": words, "notes": notes, "now": {"cpi": _f(cpi_now, 2), "iip": _f(iip_now, 2)}, "probs": probs, "lean": lean, "agree": (lean == regime),
            "p_hot": _f(100 * p_hot, 0), "p_grow": _f(100 * p_grow, 0),
            "how": "the official CPI and IIP are the anchor; the market's thirteen-week impulses (z-scored since 2015) nudge them — one σ of inflation impulse = 0.4 CPI points, one σ of growth impulse = 1.2 IIP points over the quarter; the quadrant lines (CPI 4, IIP 3) become probabilities through a logistic with the series' own noise (0.5 and 1.0 points). The label on the page stays the official one; the probabilities are the market's lean, and the model book blends its base weights by them.",
            "source": "MACRO_LIVE · the sleeves panel (twelve years weekly)"}


# ─────────────────────────────────────────────────────────────────────────────
# 15 · TOMORROW'S LIKELY MOVERS (v147) — a model trained every pass on the daily panel, blended with what only
#     today knows (the chain's implied move, futures OI, a results date), frozen and scored the next session
# ─────────────────────────────────────────────────────────────────────────────
MOVE_SIG = 1.5      # a "move" = the next session's |return| ≥ 1.5 × the name's own 20-day σ


def _ern_days(FUND, s, today):
    """days until the next results date on the profile (negative = just reported); None without one"""
    f = (FUND.get("names") or {}).get(s) or {}
    ts = f.get("ern_ts") or f.get("ern_ts0")
    if not ts:
        return None
    try:
        d = pd.Timestamp(dt.datetime.utcfromtimestamp(float(ts)).date())
        return int((d - pd.Timestamp(today)).days)
    except Exception:
        return None


def events_block(U, FUND, today):
    """the results calendar: every name whose next results date is within ten days (yesterday's included)"""
    rows = []
    for s, u in U.items():
        if u["x"] != "NSE" or (u["turn"] or 0) < 2:
            continue
        d = _ern_days(FUND, s, today)
        if d is None or d < -1 or d > 10:
            continue
        rows.append({"sym": s, "nm": u["nm"], "sector": u["sector"], "turn": u["turn"], "days": d, "fno": u["fno"]})
    rows.sort(key=lambda r: (r["days"], -(r["turn"] or 0)))
    return {"asof": today, "n": len(rows), "rows": rows[:120], "how": "results dates from Yahoo's profile (refreshed weekly per name) — the single largest driver of a next-session move"}


def _panel_features(D, DV, names=None):
    """the long frame: one row per name per session — features known at the close, the next session's outcome"""
    frames = []
    cols = [c for c in D.columns if (c in names if names is not None else (not str(c).startswith("^") and "=" not in str(c) and "-" not in str(c)))]
    for c in cols:
        s = D[c].dropna()
        if len(s) < 120 or (s <= 0).any():
            continue
        r = s.pct_change()
        sig20 = r.rolling(20).std()
        sig5 = r.rolling(5).std()
        f = pd.DataFrame(index=s.index)
        f["a1"] = (r.abs() / sig20)
        f["z1"] = r / sig20
        f["z5"] = (s / s.shift(5) - 1) / (sig20 * math.sqrt(5))
        f["z20"] = (s / s.shift(20) - 1) / (sig20 * math.sqrt(20))
        f["vreg"] = sig5 / sig20
        f["d50"] = (s / s.rolling(50).mean() - 1) / (sig20 * math.sqrt(50))
        hi = s.rolling(250, min_periods=120).max(); lo = s.rolling(250, min_periods=120).min()
        f["pos52"] = (s - lo) / ((hi - lo).replace(0, np.nan))
        f["sig20"] = sig20 * 100
        f["dow"] = s.index.dayofweek
        if DV is not None and c in DV.columns:
            v = DV[c].reindex(s.index)
            f["volz"] = v / v.rolling(20).mean()
        else:
            f["volz"] = np.nan
        nxt = r.shift(-1)
        f["y_move"] = (nxt.abs() >= MOVE_SIG * sig20).astype(float)
        f["y_dir"] = (nxt > 0).astype(float)
        f["has_next"] = nxt.notna()
        f["sym"] = c
        frames.append(f)
    if not frames:
        return None
    X = pd.concat(frames)
    X = X.replace([np.inf, -np.inf], np.nan)
    X["a1_rank"] = X.groupby(level=0)["a1"].rank(pct=True)
    return X


FEATS = ["a1", "z1", "z5", "z20", "vreg", "d50", "pos52", "sig20", "dow", "volz", "a1_rank"]


def movers_block(U, T, D, DV, opt, fno, V, FUND, today):
    out = {"asof": today, "list": [], "how": "a gradient-boosted model trained on this year's daily panel (every name with a daily tape): today's move in σ units, its rank across the market, five- and twenty-day momentum in σ, the volatility regime, distance from the 50-day, the 52-week position, volume against its 20-day average, the weekday → the probability that tomorrow's |move| is ≥ %.1fσ, and a second model for the direction. Trained on the first 80%% of the dates, tested on the last 20%% (the AUC printed is out of sample), then refit on everything for today. Then what only today knows: a results date within two sessions, the option chain's implied move above the realised, a futures OI build-up — each a stated bump, not learned." % MOVE_SIG}
    if D is None:
        out["note"] = "no daily panel on this pass"
        return out
    try:
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import roc_auc_score
    except Exception as e:
        out["note"] = "scikit-learn missing (%s)" % type(e).__name__
        return out
    X = _panel_features(D, DV, names=set(s for s, u in U.items() if u["x"] == "NSE"))
    if X is None or len(X) < 5000:
        out["note"] = "too few rows to train (%s)" % (0 if X is None else len(X))
        return out
    feats = [f for f in FEATS if X[f].notna().sum() >= 1000]      # no volume panel → no volume feature (an all-NaN column breaks the binning)
    train = X[X["has_next"]].dropna(subset=["a1", "z1", "z5", "z20", "vreg", "d50", "sig20", "y_move"])
    dates = sorted(train.index.unique())
    if len(dates) < 100:
        out["note"] = "too few sessions to train (%d)" % len(dates)
        return out
    cut = dates[int(len(dates) * 0.8)]
    tr = train[train.index < cut]; te = train[train.index >= cut]
    params = dict(max_iter=160, learning_rate=0.06, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=1.0, random_state=7)
    m_move = HistGradientBoostingClassifier(**params).fit(tr[feats], tr["y_move"])
    m_dir = HistGradientBoostingClassifier(**params).fit(tr[feats], tr["y_dir"])
    try:
        auc_move = float(roc_auc_score(te["y_move"], m_move.predict_proba(te[feats])[:, 1]))
        auc_dir = float(roc_auc_score(te["y_dir"], m_dir.predict_proba(te[feats])[:, 1]))
    except Exception:
        auc_move = auc_dir = None
    base = float(train["y_move"].mean())
    # refit on everything, score the latest session
    m_move = HistGradientBoostingClassifier(**params).fit(train[feats], train["y_move"])
    m_dir = HistGradientBoostingClassifier(**params).fit(train[feats], train["y_dir"])
    counts = X.groupby(level=0).size()
    last = counts[counts >= 20].index.max() if (counts >= 20).any() else X.index.max()     # the latest real session, not a stray date
    cur = X[X.index == last].dropna(subset=["a1", "z1", "z5", "z20", "vreg", "d50", "sig20"]).copy()
    if not len(cur):
        out["note"] = "no rows for the latest session"
        return out
    cur["p_move"] = m_move.predict_proba(cur[feats])[:, 1]
    cur["p_up"] = m_dir.predict_proba(cur[feats])[:, 1]
    rows = []
    for _, r in cur.iterrows():
        sym = r["sym"]; u = U.get(sym)
        if not u or (u["turn"] or 0) < INTRA_CR or u["sector"] == "ETF":
            continue
        p = float(r["p_move"]); drivers = []
        if r["a1"] >= 1.5:
            drivers.append("moved %.1fσ today" % r["a1"])
        if pd.notna(r["volz"]) and r["volz"] >= 2:
            drivers.append("volume %.1f× its 20-day average" % r["volz"])
        if r["vreg"] >= 1.4:
            drivers.append("volatility rising (5-day σ %.1f× the 20-day)" % r["vreg"])
        if r["pos52"] >= 0.98:
            drivers.append("at a 52-week high")
        elif r["pos52"] <= 0.02:
            drivers.append("at a 52-week low")
        ev = None
        ed = _ern_days(FUND, sym, today)
        if ed is not None and 0 <= ed <= 2:
            p = p + 0.25 * (1 - p); ev = "results in %d session%s" % (ed, "" if ed == 1 else "s") if ed else "results today"; drivers.insert(0, ev + " (+25% of the headroom)")
        elif ed is not None and ed == -1:
            p = p + 0.10 * (1 - p); ev = "reported yesterday"; drivers.insert(0, "reported yesterday — the second day often moves too")
        o = opt.get(sym) or {}
        imp = o.get("implied_1d_pct")
        if imp and r["sig20"] and imp / r["sig20"] >= 1.3:
            p = p + 0.10 * (1 - p); drivers.append("the chain prices ±%.1f%% a day, above the realised %.1f%%" % (imp, r["sig20"]))
        f = fno.get(sym) or {}
        if f.get("doi_pct") is not None and abs(f.get("d") or 0) >= 1.5 and (f.get("doi_pct") or 0) >= 5:
            p = p + 0.05 * (1 - p); drivers.append("futures OI +%.1f%% on a %.1f%% day (%s)" % (f["doi_pct"], f["d"], "long build-up" if f["d"] > 0 else "short build-up"))
        # the direction: the model, the engine's intraday lean, the short side
        vi = ((V.get(sym) or {}).get("intra") or {}); vs = ((V.get(sym) or {}).get("short") or {})
        lean_e = vi.get("lean")
        pu = 0.6 * float(r["p_up"]) + 0.4 * (0.5 + max(-1.0, min(1.0, lean_e if lean_e is not None else (0.5 if vs.get("side") == "BUY" else -0.5 if vs.get("side") == "SELL" else 0.0))) / 2)
        exp_pct = max(MOVE_SIG * float(r["sig20"]), float(imp) if imp else 0.0)
        rows.append({"sym": sym, "nm": u["nm"], "sector": u["sector"], "px": u["px"], "d1": u["d1"], "turn": u["turn"], "fno": u["fno"], "p_move": _f(100 * p, 0), "p_ml": _f(100 * float(r["p_move"]), 0),
                     "p_up": _f(100 * pu, 0), "exp_pct": _f(exp_pct, 1), "sig20": _f(float(r["sig20"]), 2), "implied_1d": imp, "event": ev, "ern_days": ed, "drivers": drivers[:4],
                     "lean": ("UP" if pu >= 0.58 else "DOWN" if pu <= 0.42 else "EITHER WAY"), "side": (vs.get("side") or vi.get("side"))})
    rows.sort(key=lambda x: -(x["p_move"] or 0))
    out.update({"list": rows[:16], "n_scored": len(rows), "session": last.strftime("%Y-%m-%d"), "auc_move": _f(auc_move, 3), "auc_dir": _f(auc_dir, 3), "base_rate": _f(100 * base, 1), "n_train": int(len(tr)), "n_test": int(len(te)),
                "sessions": len(dates), "names": int(train["sym"].nunique()), "has_volume": bool("volz" in feats), "features": feats})
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 16 · WHAT CHANGED (v147) — the verdicts that flipped since the last session, from a daily snapshot of every side
# ─────────────────────────────────────────────────────────────────────────────
def sides_snapshot_and_changes(U, V, today):
    os.makedirs(HIST_DIR, exist_ok=True)
    cur = {}
    for s, v in V.items():
        ss = (v.get("short") or {}).get("side"); ls = (v.get("long") or {}).get("side")
        if ss or ls:
            cur[s] = [ss or "", ls or ""]
    fn = os.path.join(HIST_DIR, "sides_%s.json" % today.replace("-", ""))
    files = sorted(f for f in os.listdir(HIST_DIR) if f.startswith("sides_") and f.endswith(".json"))
    prev_f = [f for f in files if f != os.path.basename(fn)]
    prev, since = {}, None
    if prev_f:
        try:
            prev = json.load(open(os.path.join(HIST_DIR, prev_f[-1]))); since = prev_f[-1][6:14]
            since = "%s-%s-%s" % (since[:4], since[4:6], since[6:])
        except Exception:
            prev = {}
    if not os.path.exists(fn):
        json.dump(cur, open(fn, "w"), separators=(",", ":"))
        for f in files[:-12]:
            try:
                os.remove(os.path.join(HIST_DIR, f))
            except Exception:
                pass
    out = {"since": since, "to_buy": [], "from_buy": [], "to_sell": [], "from_sell": [], "to_acc": [], "from_acc": [], "to_avoid": [], "from_avoid": []}
    if not prev:
        return out
    def row(s):
        u = U.get(s) or {}
        return {"sym": s, "nm": u.get("nm", s), "sector": u.get("sector"), "px": u.get("px"), "turn": u.get("turn")}
    for s, (ss, ls) in cur.items():
        if ((U.get(s) or {}).get("turn") or 0) < LIQUID_CR:
            continue
        pss, pls = (prev.get(s) or ["", ""])[0], (prev.get(s) or ["", ""])[1]
        if ss == "BUY" and pss != "BUY":
            out["to_buy"].append(row(s))
        if pss == "BUY" and ss != "BUY":
            out["from_buy"].append(dict(row(s), now=ss or "no trade"))
        if ss == "SELL" and pss != "SELL":
            out["to_sell"].append(row(s))
        if pss == "SELL" and ss != "SELL":
            out["from_sell"].append(dict(row(s), now=ss or "no trade"))
        if ls == "ACCUMULATE" and pls != "ACCUMULATE":
            out["to_acc"].append(row(s))
        if pls == "ACCUMULATE" and ls != "ACCUMULATE":
            out["from_acc"].append(dict(row(s), now=ls or "no view"))
        if ls == "AVOID" and pls != "AVOID":
            out["to_avoid"].append(row(s))
        if pls == "AVOID" and ls != "AVOID":
            out["from_avoid"].append(dict(row(s), now=ls or "no view"))
    for k in list(out.keys()):
        if isinstance(out[k], list):
            out[k].sort(key=lambda r: -(r.get("turn") or 0)); out["n_" + k] = len(out[k]); out[k] = out[k][:12]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 17 · ANY HORIZON (v147) — the four numbers the page needs to draw any horizon for any share
# ─────────────────────────────────────────────────────────────────────────────
def horizon_params(v, t, u):
    """daily σ, the short drift and its horizon, the long drift — all in % per session, consistent with the verdicts"""
    px = u.get("px") or 0
    sig = t.get("sig1d") or 2.0
    vs = v.get("short") or {}; vl = v.get("long") or {}
    hs = vs.get("h") or 20
    if vs.get("side") in ("BUY", "SELL") and vs.get("target") and px:
        ds = (vs["target"] / px - 1) * 100 / max(hs, 1)
    else:
        ds = max(-0.3, min(0.3, 0.25 * (t.get("r20") or 0) / 20))
    if vl.get("exp_pct") is not None:
        dl = vl["exp_pct"] / 250.0
    else:
        dl = max(-0.08, min(0.08, 0.3 * (t.get("r250") or 0) / 250))
    return {"sig": _f(sig, 2), "ds": _f(ds, 4), "hs": int(hs), "dl": _f(dl, 4)}


# ─────────────────────────────────────────────────────────────────────────────
# 12 · PAIRS — market-neutral ideas inside F&O (v145)
# ─────────────────────────────────────────────────────────────────────────────
def pairs_block(U, D, fno, V, max_n=5, z_min=2.0):
    how = ("two F&O names in one sector whose daily returns correlate ≥ 0.6 over a year; the spread is log(A) − β·log(B), β by least squares over 250 sessions; "
           "an idea when the spread sits ≥ 2σ from its 60-session mean and mean-reverts with a half-life of 3–40 sessions. Long the cheap leg, short the rich one in "
           "rupee-balanced lots; target the mean, stop at 3σ (or 0.75σ further out), horizon twice the half-life. Never against the engine's own side on either leg.")
    out = {"ideas": [], "n_tested": 0, "n_fit": 0, "how": how}
    if D is None:
        out["note"] = "no daily panel on this pass"
        return out
    syms = [s for s, u in U.items() if u["fno"] and s in D.columns and u["sector"] not in ("Other", "ETF") and (u["turn"] or 0) >= INTRA_CR and u["px"]]
    by = {}
    for s in syms:
        by.setdefault(U[s]["sector"], []).append(s)
    ideas = []
    for sec, mem in by.items():
        if len(mem) < 2:
            continue
        mem = sorted(mem, key=lambda s: -(U[s]["turn"] or 0))[:16]
        for i in range(len(mem)):
            for j in range(i + 1, len(mem)):
                a, b = mem[i], mem[j]
                df = pd.concat([D[a], D[b]], axis=1).dropna().iloc[-250:]
                if len(df) < 200 or (df <= 0).any().any():
                    continue
                out["n_tested"] += 1
                la = np.log(df.iloc[:, 0].values.astype(float)); lb = np.log(df.iloc[:, 1].values.astype(float))
                ra = np.diff(la); rb = np.diff(lb)
                if np.std(ra) == 0 or np.std(rb) == 0:
                    continue
                corr = float(np.corrcoef(ra, rb)[0, 1])
                if not (corr >= 0.6):
                    continue
                vb = float(np.var(lb))
                if vb <= 0:
                    continue
                beta = float(np.cov(la, lb, bias=True)[0, 1] / vb)
                if beta <= 0.2 or beta > 5:
                    continue
                sp = la - beta * lb; sp = sp - sp.mean()
                m60 = float(sp[-60:].mean()); s60 = float(sp[-60:].std())
                if s60 < 1e-4:
                    continue
                z = float((sp[-1] - m60) / s60)
                x = sp[:-1]; y = np.diff(sp); vx = float(np.var(x))
                if vx <= 0:
                    continue
                phi = float(np.cov(x, y, bias=True)[0, 1] / vx)
                if not (-1 < phi < 0):
                    continue
                hl = -math.log(2) / math.log(1 + phi)
                if not (3 <= hl <= 40):
                    continue
                out["n_fit"] += 1
                if abs(z) < z_min or abs(z) > 4.5:
                    continue
                long_, short_ = (b, a) if z > 0 else (a, b)
                vl = (V.get(long_) or {}).get("short") or {}; vs_ = (V.get(short_) or {}).get("short") or {}
                if vl.get("side") == "SELL" or vs_.get("side") == "BUY":
                    continue
                exp_pct = abs(z) * s60 * 100; stop_z = max(3.0, abs(z) + 0.75); loss_pct = (stop_z - abs(z)) * s60 * 100
                h = int(min(30, max(5, round(2 * hl))))
                px_l, px_s = float(U[long_]["px"]), float(U[short_]["px"])
                lot_l, lsrc_l = _lot_of(long_, px_l, fno); lot_s, lsrc_s = _lot_of(short_, px_s, fno)
                if not lot_l or not lot_s:
                    continue
                not_l, not_s = lot_l * px_l, lot_s * px_s
                ratio = beta if long_ == a else 1.0 / beta      # the short leg's notional against the long leg's
                # the smallest lot count that balances the two legs within 15% (a ₹10 lakh book cannot carry three lots a side)
                best = None; pick = None
                for ll in range(1, 4):
                    ls = max(1, int(round(ratio * ll * not_l / not_s)))
                    if ls > 6:
                        continue
                    mis = abs(ls * not_s - ratio * ll * not_l) / (ratio * ll * not_l)
                    if best is None or mis < best[0]:
                        best = (mis, ll, ls)
                    if mis <= 0.15 and pick is None:
                        pick = (mis, ll, ls)
                if best is None:
                    continue
                mis, ll, ls = pick or best
                ideas.append({"a": long_, "b": short_, "nm_a": U[long_]["nm"], "nm_b": U[short_]["nm"], "sector": sec, "z": _f(z, 2), "corr": _f(corr, 2), "beta": _f(beta, 2),
                              "hl": int(round(hl)), "h": h, "exp_pct": _f(exp_pct, 1), "loss_pct": _f(loss_pct, 1), "stop_z": _f(stop_z, 1), "lots_a": ll, "lots_b": ls,
                              "lot_a": lot_l, "lot_b": lot_s, "px_a": px_l, "px_b": px_s, "not_a": round(ll * not_l), "not_b": round(ls * not_s), "gross": round(ll * not_l + ls * not_s),
                              "exp_inr": round(exp_pct / 100 * ll * not_l), "loss_inr": round(loss_pct / 100 * ll * not_l), "mismatch_pct": _f(mis * 100, 0), "margin_est": round(0.18 * (ll * not_l + ls * not_s)),
                              "conv": ("high" if (corr >= 0.75 and hl <= 20) else "medium"), "side_a": vl.get("side"), "side_b": vs_.get("side"), "lot_src": (lsrc_l if lsrc_l == lsrc_s else lsrc_l + " / " + lsrc_s),
                              "why": ["%s is %.1fσ cheap against %s on a year's relationship (β %.2f)" % (U[long_]["nm"], abs(z), U[short_]["nm"], beta),
                                      "daily correlation %.2f · the spread mean-reverts with a half-life of %d sessions" % (corr, round(hl)),
                                      "the engine's own sides: %s %s · %s %s" % (long_, vl.get("side") or "no trade", short_, vs_.get("side") or "no trade"),
                                      "rupee-balanced: %d lot%s against %d lot%s (%d%% mismatch)" % (ll, "s" if ll > 1 else "", ls, "s" if ls > 1 else "", round(mis * 100))]})
    ideas.sort(key=lambda i: -(abs(i["z"]) * (0.6 + i["corr"])))
    used = set(); keep = []
    for i in ideas:
        if i["a"] in used or i["b"] in used:
            continue
        used.add(i["a"]); used.add(i["b"]); keep.append(i)
        if len(keep) >= max_n:
            break
    out["ideas"] = keep
    out["n_ideas"] = len(ideas)
    return out


# ─────────────────────────────────────────────────────────────────────────────
def write_series_shards(U, W, D, nw=260, nd=260):
    Wt = W.iloc[-nw:]; Dt = D.iloc[-nd:] if D is not None else None
    wdates = [d.strftime("%Y%m%d") for d in Wt.index]; ddates = [d.strftime("%Y%m%d") for d in Dt.index] if Dt is not None else []
    shards = {i: {} for i in range(N_SHARDS)}
    n_w = n_d = 0
    for s, u in U.items():
        if u["x"] != "NSE" and s not in Wt.columns:
            continue
        row = {}
        if s in Wt.columns:
            v = Wt[s].values
            if np.isfinite(v).sum() >= 8:
                row["w"] = [(round(float(x), 2) if np.isfinite(x) else None) for x in v]; n_w += 1
        if Dt is not None and s in Dt.columns:
            v = Dt[s].values
            if np.isfinite(v).sum() >= 30:
                row["d"] = [(round(float(x), 2) if np.isfinite(x) else None) for x in v]; n_d += 1
        if row:
            shards[shard_of(s)][s] = row
    for i, rows in shards.items():
        json.dump({"version": VERSION, "shard": i, "wdates": wdates, "ddates": ddates, "names": rows}, open("engine_s%d.json" % i, "w"), separators=(",", ":"))
    log("series shards: %d names weekly (%d points) · %d daily (%d points) · %.0f KB a shard" % (n_w, len(wdates), n_d, len(ddates), sum(os.path.getsize("engine_s%d.json" % i) for i in range(N_SHARDS)) / N_SHARDS / 1e3))


def _clean(o):
    """drop None values (and empty dicts) recursively — a third of the bytes"""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if v is not None and not (isinstance(v, dict) and not v)}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


# ─────────────────────────────────────────────────────────────────────────────
# 14 · v148 — DELIVERY · THE NEWS · WHY IT MOVED · THE STREET · THE CALLS OF THE DAY · THE BRIEF
#     Five things a quote site does not do, built on what the pass already knows:
#     · delivery — NSE's own figure for how much of today's volume was taken home (sec_bhavdata_full), against the
#       name's own average: accumulation, distribution, or a speculative move
#     · the news — Google News' RSS per name (keyless), scored with a small finance lexicon, tagged by what kind of
#       story it is; the headlines are the evidence behind a call, never a feature the models learn on
#     · why it moved — every big move split into the market's part (β × Nifty), the sector's part and the stock's own,
#       with the delivery read and the fresh headlines next to the stock-specific ones
#     · the Street — the analysts' consensus target (Yahoo) against the engine's twelve-month target, name by name,
#       and a record of who turned out closer
#     · the calls of the day — ONE long call (twelve months) and ONE short call (one month), each made only when the
#       evidence stacks: the verdict, the company's numbers, the regime fit, the Street, the news, the delivery, the
#       engine's own record on the name; frozen with the day and scored
#     · the brief — the day's major updates as a list the page shows behind a bell
# ─────────────────────────────────────────────────────────────────────────────
import urllib.request, urllib.parse, email.utils, hashlib, html as _html

UA_148 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _http(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA_148, "Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
    if b[:2] == b"\x1f\x8b":
        import gzip
        b = gzip.decompress(b)
    return b.decode("utf-8", "ignore")


# ── 14a · delivery ──────────────────────────────────────────────────────────────
DELIV_FILE = "delivery.json"          # the cache (the workflow keeps it between passes, like the price panel)
DELIV_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_%s.csv"   # DDMMYYYY
DELIV_KEEP = 60                       # sessions kept


def parse_delivery_csv(txt):
    """{sym: [deliv_pct, deliv_qty, traded_qty]} for the EQ series of one sec_bhavdata_full file (values carry stray spaces; '-' is NA)"""
    out = {}
    lines = (txt or "").splitlines()
    if not lines:
        return out
    hdr = [h.strip().upper() for h in lines[0].split(",")]
    try:
        i_s, i_ser, i_q, i_dq, i_dp = hdr.index("SYMBOL"), hdr.index("SERIES"), hdr.index("TTL_TRD_QNTY"), hdr.index("DELIV_QTY"), hdr.index("DELIV_PER")
    except ValueError:
        return out
    top = max(i_s, i_ser, i_q, i_dq, i_dp)
    for ln in lines[1:]:
        c = [x.strip() for x in ln.split(",")]
        if len(c) <= top or c[i_ser].upper() != "EQ":
            continue
        try:
            dp = float(c[i_dp]); dq = float(c[i_dq]); tq = float(c[i_q])
        except ValueError:
            continue
        if tq <= 0 or dp < 0 or dp > 100:
            continue
        out[c[i_s].upper()] = [round(dp, 2), int(dq), int(tq)]
    return out


def fetch_delivery(bhav_date, offline, max_new=3, lookback_days=12):
    """the delivery cache topped up with the sessions it lacks (at most max_new files a pass; a date that answers nothing twice is a holiday)"""
    C = {"days": {}, "miss": {}}
    try:
        C = json.load(open(DELIV_FILE))
        C.setdefault("days", {}); C.setdefault("miss", {})
    except Exception:
        pass
    fetched = 0
    if not offline:
        try:
            d = pd.Timestamp(bhav_date) if bhav_date else pd.Timestamp(now_ist().date())
        except Exception:
            d = pd.Timestamp(now_ist().date())
        stop = d - pd.Timedelta(days=lookback_days)
        while fetched < max_new and d >= stop:
            key = d.strftime("%Y%m%d")
            if d.weekday() < 5 and key not in C["days"] and C["miss"].get(key, 0) < 2:
                try:
                    rows = parse_delivery_csv(_http(DELIV_URL % d.strftime("%d%m%Y"), timeout=25))
                except Exception:
                    rows = {}
                if len(rows) >= 500:
                    C["days"][key] = rows; fetched += 1
                else:
                    C["miss"][key] = C["miss"].get(key, 0) + 1
                time.sleep(0.4)
            d -= pd.Timedelta(days=1)
        keep = sorted(C["days"])[-DELIV_KEEP:]
        C["days"] = {k: C["days"][k] for k in keep}
        C["miss"] = {k: v for k, v in C["miss"].items() if k >= (keep[0] if keep else "0")}
        C["updated"] = now_ist().strftime("%Y-%m-%d %H:%M")
        try:
            json.dump(C, open(DELIV_FILE, "w"), separators=(",", ":"))
        except Exception as e:
            log("delivery cache not written (%s)" % type(e).__name__)
    C["fetched"] = fetched
    return C


def delivery_read(C, U, window=20):
    """per name: today's delivery %, its average over the previous sessions, the z, the delivered-quantity ratio"""
    days = C.get("days") or {}
    keys = sorted(days)
    if not keys:
        return {}, None
    last = keys[-1]; prev = keys[:-1][-window:]
    out = {}
    for s in U:
        row = days[last].get(s)
        if not row:
            continue
        hist = [days[k][s][0] for k in prev if s in days[k]]
        dq = [days[k][s][1] for k in prev if s in days[k]]
        avg = float(np.mean(hist)) if len(hist) >= 5 else None
        sd = float(np.std(hist)) if len(hist) >= 5 else None
        z = ((row[0] - avg) / sd) if (avg is not None and sd and sd > 1.0) else None
        qr = (row[1] / float(np.mean(dq))) if (len(dq) >= 5 and float(np.mean(dq)) > 0) else None
        out[s] = {"dlv": row[0], "dlv_avg": _f(avg, 1), "dlv_z": _f(max(-4.0, min(4.0, z)), 2) if z is not None else None, "dlv_qr": _f(qr, 2), "n": len(hist)}
    return out, last


def delivery_word(t, d1):
    """(WORD, sentence) or None — the delivery read against the day's direction"""
    dz = t.get("dlv_z"); dv = t.get("dlv"); av = t.get("dlv_avg")
    if dz is None or dv is None or av is None or d1 is None:
        return None
    if dz >= 1.0 and d1 > 0:
        return "ACCUMULATION", "delivery %.0f%% against its %.0f%% average (%+.1fσ) on an up day — buyers taking stock home" % (dv, av, dz)
    if dz >= 1.0 and d1 < 0:
        return "DISTRIBUTION", "delivery %.0f%% against its %.0f%% average (%+.1fσ) on a down day — holders leaving for keeps" % (dv, av, dz)
    if dz <= -1.0 and abs(d1) >= 2:
        return "SPECULATIVE", "delivery %.0f%% against its %.0f%% average (%+.1fσ) — an intraday move, little of it taken home" % (dv, av, dz)
    return None


# ── 14b · the news ─────────────────────────────────────────────────────────────
NEWS_FILE = "news.json"               # served with the page: the headlines behind the calls, the movers and the brief
NEWS_CACHE = "news_cache.json"        # per-name results for a few hours, so a pass refreshes only what is stale
GNEWS = "https://news.google.com/rss/search?q=%s&hl=en-IN&gl=IN&ceid=IN:en"
NEWS_POS = ["beats", "beat", "record", "surge", "surges", "soars", "jumps", "rallies", "wins", "bags", "order", "orders", "contract", "upgrade", "upgrades", "upgraded",
            "buyback", "bonus", "dividend", "expansion", "approval", "approves", "approved", "strong", "robust", "profit rises", "profit jumps", "profit up", "growth",
            "outperform", "overweight", "raises target", "target raised", "stake buy", "promoter buys", "launch", "launches", "commissioned", "capacity", "all-time high",
            "52-week high", "doubles", "guidance raised", "positive", "gains", "higher"]
NEGS = ["misses", "miss", "falls", "fall", "slumps", "slump", "plunges", "plunge", "crashes", "crash", "tumbles", "downgrade", "downgrades", "downgraded", "probe",
        "fraud", "default", "penalty", "fine", "raid", "ban", "banned", "lawsuit", "notice", "loss", "losses", "weak", "cuts guidance", "guidance cut", "resigns",
        "resignation", "pledge", "pledged", "insolvency", "nclt", "underperform", "underweight", "target cut", "cuts target", "sell-off", "selloff", "52-week low",
        "lower", "declines", "decline", "drops", "drop", "halts", "recall", "strike", "shutdown", "fire at", "explosion", "stake sale", "promoter sells", "warning"]
NEWS_TAGS = [("results", r"\b(q[1-4]|quarter|quarterly|results?|profit|revenue|ebitda|margins?|net loss|earnings|pat|beats?|misses|estimates)\b"),
             ("order", r"\b(orders?|contracts?|wins|bags|awarded|tender|loa|loi|supply agreement)\b"),
             ("deal", r"\b(acquires?|acquisition|stake|merger|demerger|buyout|jv|joint venture|divest|sells .{0,20}business)\b"),
             ("capital", r"\b(buyback|dividend|bonus|stock split|rights issue|qip|fund ?raise|preferential|ipo|listing|ofs|block deal|bulk deal)\b"),
             ("rating", r"\b(upgrades?d?|downgrades?d?|target price|price target|rating|overweight|underweight|outperform|initiates?|brokerage|analysts?)\b"),
             ("legal", r"\b(sebi|probe|penalty|fine|fraud|raid|ed |cbi|lawsuit|court|ban|show-cause|notice|tax demand|default|insolvency|nclt|cci)\b"),
             ("management", r"\b(ceo|cfo|md|chairman|resigns?|resignation|appoints?|steps down|board)\b"),
             ("expansion", r"\b(capex|plant|expansion|launch(es)?|approval|usfda|eir|commission(ed|s)?|capacity|facility)\b"),
             ("promoter", r"\b(promoters?|pledge|insider)\b")]


def news_tone(title):
    """−2 … +2 from a small finance lexicon; a headline with both reads 0"""
    t = " " + (title or "").lower() + " "
    p = sum(1 for w in NEWS_POS if (" " + w + " ") in t or (" " + w + ",") in t or (" " + w + ":") in t)
    n = sum(1 for w in NEGS if (" " + w + " ") in t or (" " + w + ",") in t or (" " + w + ":") in t)
    return int(max(-2, min(2, p - n)))


def news_tags(title):
    t = (title or "").lower()
    return [k for k, rx in NEWS_TAGS if re.search(rx, t)][:3]


def parse_rss(xml, max_age_days=7, limit=6, now=None):
    """[{t, src, link, age_d, tone, tags}] from a Google News RSS document — titles carry ' - Source' which is stripped"""
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for m in re.finditer(r"<item>(.*?)</item>", xml or "", re.S):
        it = m.group(1)
        def tag(name):
            mm = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), it, re.S)
            if not mm:
                return ""
            v = mm.group(1).strip()
            v = re.sub(r"^<!\[CDATA\[(.*?)\]\]>$", r"\1", v, flags=re.S)
            return _html.unescape(v).strip()
        title = tag("title"); link = tag("link"); pub = tag("pubDate"); src = tag("source")
        if not title:
            continue
        if src and title.endswith(" - " + src):
            title = title[: -len(src) - 3].strip()
        elif " - " in title and not src:
            title, src = title.rsplit(" - ", 1)
        age_d = None
        try:
            when = email.utils.parsedate_to_datetime(pub)
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            age_d = round((now - when).total_seconds() / 86400.0, 1)
        except Exception:
            pass
        if age_d is not None and age_d > max_age_days:
            continue
        out.append({"t": title[:160], "src": (src or "")[:40], "link": link[:300], "age_d": age_d, "tone": news_tone(title), "tags": news_tags(title)})
        if len(out) >= limit:
            break
    return out


def _news_name(nm):
    """the company as a search phrase: 'Reliance Industries Ltd.' → 'Reliance Industries'"""
    s = re.sub(r"\b(ltd\.?|limited|india|the)\b", " ", nm or "", flags=re.I)
    s = re.sub(r"[^A-Za-z0-9&' ]+", " ", s)
    s = " ".join(s.split())
    return s or (nm or "")


def fetch_news(cands, offline, budget_s=90, max_age_h=5, market=True):
    """cands: [(sym, nm)] in priority order. Per name: the headlines of the last week with tone and tags, cached for a few
    hours; plus the market's own headlines. Writes news.json; returns {"names": {sym: {...}}, "market": [...]}"""
    t0 = time.time()
    cache = {"names": {}, "market": None}
    try:
        cache = json.load(open(NEWS_CACHE))
        cache.setdefault("names", {}); cache.setdefault("market", None)
    except Exception:
        pass
    now = now_ist(); now_s = now.strftime("%Y-%m-%d %H:%M")
    def fresh(rec):
        try:
            return (now - dt.datetime.strptime(rec["at"], "%Y-%m-%d %H:%M").replace(tzinfo=IST)).total_seconds() < max_age_h * 3600
        except Exception:
            return False
    names = {}; n_fetch = 0; n_cached = 0
    for sym, nm in cands:
        rec = cache["names"].get(sym)
        if rec and fresh(rec):
            names[sym] = rec; n_cached += 1
            continue
        if offline or time.time() - t0 > budget_s:
            if rec:
                names[sym] = rec; n_cached += 1
            continue
        try:
            q = urllib.parse.quote('"%s" shares OR stock' % _news_name(nm))
            items = parse_rss(_http(GNEWS % q, timeout=15))
            rec = {"at": now_s, "nm": nm, "q": _news_name(nm), "items": items, "n": len(items), "tone": int(sum(x["tone"] for x in items)),
                   "pos": sum(1 for x in items if x["tone"] > 0), "neg": sum(1 for x in items if x["tone"] < 0),
                   "fresh": sum(1 for x in items if x.get("age_d") is not None and x["age_d"] <= 1.5)}
            cache["names"][sym] = rec; names[sym] = rec; n_fetch += 1
            time.sleep(0.35)
        except Exception as e:
            if rec:
                names[sym] = rec
            else:
                names[sym] = {"at": now_s, "nm": nm, "items": [], "n": 0, "tone": 0, "pos": 0, "neg": 0, "fresh": 0, "error": type(e).__name__}
    mk = cache.get("market")
    if market and (not mk or not fresh(mk)) and not offline and time.time() - t0 < budget_s + 20:
        items = []
        for q in ("Nifty Sensex stock market today", "RBI rupee bond yields India", "FII DII flows India stocks"):
            try:
                items += parse_rss(_http(GNEWS % urllib.parse.quote(q), timeout=15), max_age_days=2, limit=5)
                time.sleep(0.35)
            except Exception:
                pass
        seen = set(); uniq = []
        for x in items:
            k = x["t"][:60].lower()
            if k in seen:
                continue
            seen.add(k); uniq.append(x)
        uniq.sort(key=lambda x: (x.get("age_d") if x.get("age_d") is not None else 9))
        mk = {"at": now_s, "items": uniq[:10]}
        cache["market"] = mk
    # prune the cache: nothing older than three days
    try:
        cutoff = (now - dt.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        cache["names"] = {k: v for k, v in cache["names"].items() if (v.get("at") or "") >= cutoff}
        json.dump(cache, open(NEWS_CACHE, "w"), separators=(",", ":"), ensure_ascii=False)
    except Exception as e:
        log("news cache not written (%s)" % type(e).__name__)
    out = {"asof": now_s, "n_names": len(names), "n_fetched": n_fetch, "n_cached": n_cached, "names": names, "market": (mk or {}).get("items") or [],
           "how": "Google News' RSS per company (the headlines of the last seven days, up to six, from Indian and global sources), scored −2…+2 by a small finance lexicon and tagged by what the story is (results, order, deal, capital, rating, legal, management, expansion, promoter); the market's own headlines from three standing queries. Headlines are evidence behind a call and context on a move — the models never learn on them."}
    try:
        json.dump(_clean(out), open(NEWS_FILE, "w"), separators=(",", ":"), ensure_ascii=False)
    except Exception as e:
        log("news.json not written (%s)" % type(e).__name__)
    return out


def news_support(nrec):
    """(verdict, sentence, items) — does the week's news support a long? SUPPORTS / AGAINST / NEUTRAL / NONE"""
    if not nrec or not nrec.get("items"):
        return "NONE", "no headline in the last week — the call rests on the numbers alone", []
    items = nrec["items"]
    pos = [x for x in items if x["tone"] > 0]; neg = [x for x in items if x["tone"] < 0]
    if neg and not pos:
        return "AGAINST", "the week's news runs against it: “%s” (%s)" % (neg[0]["t"], neg[0].get("src") or "—"), neg[:2]
    if pos and len(pos) >= len(neg) + 1:
        return "SUPPORTS", "the news supports it: “%s” (%s%s)" % (pos[0]["t"], pos[0].get("src") or "—", (", %s" % ("today" if (pos[0].get("age_d") or 9) <= 1 else "%d days ago" % round(pos[0]["age_d"]))) if pos[0].get("age_d") is not None else ""), pos[:3]
    if neg and pos:
        return "MIXED", "the news is mixed (%d for, %d against)" % (len(pos), len(neg)), (pos + neg)[:3]
    return "NEUTRAL", "%d headline%s this week, none decisive: “%s”" % (len(items), "s" if len(items) != 1 else "", items[0]["t"]), items[:2]


# ── 14c · why it moved ─────────────────────────────────────────────────────────
def attribution_block(U, T, DNA, mkt, N, today):
    """every big move today split three ways: the market's part (β × the Nifty), the sector's part (the sector's move relative to
    the Nifty), the stock's own — with the delivery read and the fresh headlines next to the stock-specific ones"""
    liquid = [s for s, u in U.items() if (u["turn"] or 0) >= LIQUID_CR and u["d1"] is not None and u["sector"] != "ETF"]
    top = sorted(liquid, key=lambda s: -(U[s]["turn"] or 0))[:100]
    nd_u = float(np.median([U[s]["d1"] for s in top])) if top else 0.0
    nd = mkt.get("nifty_d1"); ref = "the Nifty"
    if nd is None or abs(nd - nd_u) > 0.8:
        # the index print and the bhavcopy are from different sessions (or the index is stale) — the market's part must be same-session
        nd = nd_u; ref = "the market (the median of the 100 most traded names)"
    by_sec = {}
    for s in liquid:
        by_sec.setdefault(U[s]["sector"], []).append(U[s]["d1"])
    sec_mv = {k: float(np.median(v)) for k, v in by_sec.items() if len(v) >= 4}
    rows = []
    for s in liquid:
        u = U[s]; t = T.get(s) or {}; d1 = u["d1"]; sig = t.get("sig1d") or 2.0
        if abs(d1) < max(1.5 * sig, 2.0):
            continue
        beta = ((DNA.get(s) or {}).get("b") or {}).get("nifty")
        beta = clamp(beta if beta is not None else 1.0, 0.0, 2.5)
        mpart = beta * nd
        sm = sec_mv.get(u["sector"])
        spart = clamp((sm - nd) if sm is not None else 0.0, -abs(d1), abs(d1))
        own = d1 - mpart - spart
        a = abs(d1) or 1e-9
        if abs(d1) >= 35:
            kind = "ADJUSTMENT?"      # a split, a demerger, a bonus or a listing-day print — not a move anyone traded
        elif abs(own) / a >= 0.6:
            kind = "STOCK-SPECIFIC"
        elif abs(spart) / a >= 0.45:
            kind = "SECTOR"
        elif abs(mpart) / a >= 0.45:
            kind = "MARKET"
        else:
            kind = "MIXED"
        dw = delivery_word(t, d1)
        nrec = (N.get("names") or {}).get(s) or {}
        fresh = [x for x in (nrec.get("items") or []) if x.get("age_d") is not None and x["age_d"] <= 2.5][:2]
        if kind == "ADJUSTMENT?":
            note = "%s%% on the print — a move this size is almost always a split, a demerger, a bonus or a fresh listing being adjusted, not a trade; the tape re-bases over the next sessions" % ("%+.1f" % d1)
        elif kind == "STOCK-SPECIFIC":
            note = "%s%% today of which the market explains %s and the sector %s — %s is the stock's own" % (("%+.1f" % d1), ("%+.1f" % mpart), ("%+.1f" % spart), ("%+.1f" % own))
            note += (": “%s”" % fresh[0]["t"]) if fresh else " — no headline found; a results date, a block deal or a broker note usually sits behind a move like this"
        elif kind == "SECTOR":
            note = "%s%% today, mostly the sector: %s moved %s against the Nifty's %s" % (("%+.1f" % d1), u["sector"], ("%+.1f" % sm) if sm is not None else "—", ("%+.1f" % nd))
        elif kind == "MARKET":
            note = "%s%% today, mostly the market: β %.1f × the Nifty's %s" % (("%+.1f" % d1), beta, ("%+.1f" % nd))
        else:
            note = "%s%% today from all three: market %s · sector %s · own %s" % (("%+.1f" % d1), ("%+.1f" % mpart), ("%+.1f" % spart), ("%+.1f" % own))
        rows.append({"sym": s, "nm": u["nm"], "sector": u["sector"], "px": u["px"], "d1": _f(d1), "sig": _f(sig), "z": _f(d1 / sig, 1), "beta": _f(beta, 2),
                     "mkt": _f(mpart), "sec": _f(spart), "own": _f(own), "kind": kind, "note": note, "dlv": (dw[0] if dw else None), "dlv_note": (dw[1] if dw else None),
                     "news": fresh, "turn": u["turn"], "fno": bool(u["fno"])})
    rows.sort(key=lambda r: (1 if r["kind"] == "ADJUSTMENT?" else 0, -abs(r["z"] or 0)))
    by = {r["sym"]: r for r in rows[:200]}
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    return {"asof": today, "nifty_d1": _f(nd), "ref": ref, "n": len(rows), "kinds": kinds, "rows": rows[:16], "by": by,
            "sectors": {k: _f(v) for k, v in sorted(sec_mv.items(), key=lambda x: -abs(x[1]))},
            "how": "a move counts when it is ≥ 1.5σ (and ≥ 2%) on a liquid name; the market's part is the name's three-year Nifty β times the Nifty's day, the sector's part the sector's median move relative to the Nifty (capped at the move itself), the rest is the stock's own; STOCK-SPECIFIC when the own part is ≥ 60% of the move. The delivery read is NSE's deliverable-quantity figure against the name's own twenty-session average."}


# ── 14d · the Street ───────────────────────────────────────────────────────────
def street_block(U, V, FUND, today, min_n=5):
    """the analysts' mean target against the engine's twelve-month expectation, where at least five analysts cover the name"""
    rows = []
    for s, u in U.items():
        f = (FUND.get("names") or {}).get(s) or {}
        if not f or f.get("empty") or u["sector"] == "ETF":
            continue
        st = f.get("street_tgt"); n = f.get("street_n") or 0; px = u["px"]
        vl = (V.get(s) or {}).get("long") or {}
        if not st or n < min_n or not px or vl.get("exp_pct") is None:
            continue
        up_s = (st / px - 1) * 100
        if abs(up_s) > 100:
            continue        # a stale or split-adjusted target
        up_e = vl["exp_pct"]
        rows.append({"sym": s, "nm": u["nm"], "sector": u["sector"], "px": px, "street": _f(st), "street_n": int(n), "street_rec": f.get("street_rec"),
                     "up_street": _f(up_s, 1), "up_engine": _f(up_e, 1), "gap": _f(up_e - up_s, 1), "eng_tgt": vl.get("target"), "ls": vl.get("side"), "score": vl.get("score"),
                     "turn": u["turn"], "fno": bool(u["fno"])})
    if not rows:
        return {"asof": today, "n": 0, "bull": [], "bear": [], "how": "the Street arrives with the profiles rotation (Yahoo's analyst fields)"}
    a = np.array([r["up_engine"] for r in rows], dtype=float); b = np.array([r["up_street"] for r in rows], dtype=float)
    try:
        ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
        corr = float(np.corrcoef(ra, rb)[0, 1]) if len(rows) >= 8 else None
    except Exception:
        corr = None
    agree = float(np.mean([(1 if (r["up_engine"] > 0) == (r["up_street"] > 0) else 0) for r in rows])) * 100
    inv = [r for r in rows if (r["turn"] or 0) >= PICK_CR / 4]
    bull = sorted(inv, key=lambda r: -r["gap"])[:10]
    bear = sorted(inv, key=lambda r: r["gap"])[:10]
    return {"asof": today, "n": len(rows), "corr": _f(corr, 2), "agree_pct": _f(agree, 0), "med_gap": _f(float(np.median([abs(r["gap"]) for r in rows])), 1),
            "street_up_median": _f(float(np.median(b)), 1), "engine_up_median": _f(float(np.median(a)), 1),
            "bull": bull, "bear": bear, "by": {r["sym"]: {k: r[k] for k in ("street", "street_n", "street_rec", "up_street", "up_engine", "gap")} for r in rows},
            "how": "Yahoo's mean analyst target (names with ≥ %d analysts) as an upside from today's price, against the engine's twelve-month expectation; the gap is engine minus Street in points of upside. The two disagree by construction more often than not: a consensus target lags the price, so the Street's biggest upsides sit on names that have fallen, while the engine's expectation leans on momentum, the regime and the company's numbers. The widest gaps can also be a stale target after a split or a demerger. The record freezes the twenty widest gaps each day and, sixty sessions on, asks whose implied path the price came closer to." % min_n}


# ── 14e · the calls of the day ─────────────────────────────────────────────────
def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def cone_at(hz, h, px):
    """the page's horizon cone in Python: expected price (median path) and P(higher) at h sessions"""
    if not hz or not hz.get("sig") or not px:
        return None
    hs = hz.get("hs") or 20; ds = hz.get("ds") or 0.0; dl = hz.get("dl") or 0.0
    e = 0.0
    for t in range(1, int(h) + 1):
        if t <= hs:
            e += ds
        elif t <= hs + 40:
            w = (t - hs) / 40.0; e += ds * (1 - w) + dl * w
        else:
            e += dl
    sd = hz["sig"] * math.sqrt(h)
    mu = math.log(1 + e / 100.0) - 0.5 * (sd / 100.0) ** 2
    s = sd / 100.0
    return {"h": int(h), "price": _f(px * math.exp(mu)), "exp": _f((math.exp(mu) - 1) * 100, 1), "p_up": _f(_phi(mu / s) * 100, 0), "lo1": _f(px * math.exp(mu - s)), "hi1": _f(px * math.exp(mu + s))}


def _name_record(rec_by_sym, s):
    r = (rec_by_sym or {}).get(s)
    if not r or (r.get("n") or 0) < 2:
        return None
    return r


def conviction_calls(U, T, V, SC, DNA, FUND, regime, edge, fno, opt, N, ev, rec_by_sym, today, gate):
    """ONE long call (twelve months) and ONE short call (one month) — made only when the evidence stacks. Every support and every
    objection is written out; the conviction is the count of independent supports, 1–5."""
    ev_days = {r["sym"]: r["days"] for r in (ev.get("rows") or [])}
    def seasoned(s, n_daily=200, n_weekly=100):
        t = T.get(s) or {}
        return (t.get("n") or 0) >= (n_daily if t.get("src") == "daily" else n_weekly)
    def common(s, side_rec, h):
        u = U[s]; t = T.get(s) or {}; sc = SC.get(s) or {}; f = (FUND.get("names") or {}).get(s) or {}
        sup, agn = [], []
        # the company's numbers (the micro)
        q = sc.get("Q")
        if q is not None and q >= 62:
            sup.append({"k": "quality", "t": "the company's numbers score %d/100: %s" % (q, ", ".join((sc.get("qwhy") or [])[:3]) or "ROE, margins, growth, leverage, valuation against the sector")})
        elif q is not None and q <= 38:
            agn.append({"k": "quality", "t": "the company's numbers score %d/100 (%s)" % (q, ", ".join((sc.get("qwhy") or [])[:2]) or "weak")})
        # the regime fit
        rr = ((DNA.get(s) or {}).get("regime") or {}).get(regime)
        if rr and rr.get("n", 0) >= 10 and rr.get("ann") is not None:
            (sup if rr["ann"] >= 0 else agn).append({"k": "regime", "t": "in %s weeks it has %s the Nifty by %.0f%%/yr (%d weeks of record)" % (regime, "beaten" if rr["ann"] >= 0 else "lagged", abs(rr["ann"]), rr["n"])})
        else:
            e = edge.get(u["sector"]) or {}
            if e.get("ann_pct") is not None and abs(e.get("t") or 0) >= 1.5:
                (sup if e["ann_pct"] >= 0 else agn).append({"k": "regime", "t": "%s has returned %+.0f%%/yr in %s regimes (t %.1f)" % (u["sector"], e["ann_pct"], regime, e.get("t") or 0)})
        # the Street
        st = f.get("street_tgt"); sn = f.get("street_n") or 0
        if st and sn >= 3 and u["px"]:
            ups = (st / u["px"] - 1) * 100
            if ups >= 5:
                sup.append({"k": "street", "t": "the Street's mean target ₹%s (%d analysts) sits %+.0f%% above" % (_inr(st), sn, ups)})
            elif ups <= -3:
                agn.append({"k": "street", "t": "the Street's mean target ₹%s (%d analysts) sits %+.0f%% below today's price" % (_inr(st), sn, ups)})
        # the news
        nv, ns, nitems = news_support((N.get("names") or {}).get(s))
        if nv == "SUPPORTS":
            sup.append({"k": "news", "t": ns})
        elif nv == "AGAINST":
            agn.append({"k": "news", "t": ns})
        # delivery
        dw = delivery_word(t, u["d1"])
        if dw and dw[0] == "ACCUMULATION":
            sup.append({"k": "delivery", "t": dw[1]})
        elif dw and dw[0] == "DISTRIBUTION":
            agn.append({"k": "delivery", "t": dw[1]})
        # the engine's own record on this name
        nr = _name_record(rec_by_sym, s)
        if nr:
            (sup if nr["hit"] >= 60 else agn).append({"k": "record", "t": "the engine's last %d calls on this name: %d%% in the money, %+.1f%% average" % (nr["n"], nr["hit"], nr["avg"])})
        # events
        d = ev_days.get(s)
        if d is not None and 0 <= d <= h:
            agn.append({"k": "results", "t": "results in %d session%s — a results day moves more than any stop allows for; size for it or wait" % (d, "" if d == 1 else "s")})
        return sup, agn, nv, nitems
    # ── the long call ──
    long_pool = []
    for s, v in V.items():
        vl = v.get("long") or {}
        if vl.get("side") != "ACCUMULATE" or (U[s]["turn"] or 0) < PICK_CR / 2 or U[s]["sector"] == "ETF" or not seasoned(s):
            continue
        f = (FUND.get("names") or {}).get(s) or {}
        if not f or f.get("empty"):
            continue
        long_pool.append((s, vl.get("score") or 0))
    long_pool.sort(key=lambda x: (-x[1], -(U[x[0]]["turn"] or 0)))
    def build(s, kind):
        u = U[s]; v = V[s]; t = T.get(s) or {}
        h = 250 if kind == "long" else 20
        vr = v.get("long") if kind == "long" else v.get("short")
        sup, agn, nv, nitems = common(s, vr, 5 if kind == "long" else 20)
        px = u["px"]
        if kind == "long":
            if (t.get("r120") or 0) > 0 and (t.get("vs200") or 0) > 0:
                sup.insert(0, {"k": "trend", "t": "%+.0f%% over six months%s, %+.1f%% above its 200-day" % (t.get("r120") or 0, (", %+.0f%% over a year" % t["r250"]) if t.get("r250") is not None else "", t.get("vs200") or 0)})
            elif (t.get("vs200") or 0) < 0:
                agn.append({"k": "trend", "t": "below its 200-day (%+.1f%%)" % (t.get("vs200") or 0)})
            target = vr.get("target"); stop = vr.get("stop"); exp_pct = vr.get("exp_pct")
            label = "12 months"
        else:
            if (t.get("r20") or 0) > 0 and (t.get("vs50") or 0) > 0 and (t.get("ext20") or 0) <= 2.0:
                sup.insert(0, {"k": "trend", "t": "%+.1f%% over 20 sessions, %+.1f%% above the 50-day, not extended (%.1fσ from its 20-day mean)" % (t.get("r20") or 0, t.get("vs50") or 0, t.get("ext20") or 0)})
            if (t.get("ext20") or 0) > 2.0:
                agn.append({"k": "trend", "t": "extended %.1fσ above its 20-day mean — chase nothing" % t["ext20"]})
            c = (SC.get(s) or {}).get("cont") or {}
            if c.get("p_up") is not None and c["p_up"] >= 0.55:
                sup.append({"k": "models", "t": "the contenders model leans up (p(up) %d%%, %d%% odds of a ≥1.5σ move in five sessions)" % (round(100 * c["p_up"]), round(100 * (c.get("p_move") or 0.3)))})
            fr = fno.get(s) or {}
            if fr.get("d") is not None and fr.get("doi_pct") is not None and fr["d"] > 0 and fr["doi_pct"] > 2:
                sup.append({"k": "futures", "t": "futures: long build-up (OI %+.1f%% on an up day)" % fr["doi_pct"]})
            elif fr.get("d") is not None and fr.get("doi_pct") is not None and fr["d"] < 0 and fr["doi_pct"] > 2:
                agn.append({"k": "futures", "t": "futures: short build-up (OI %+.1f%% on a down day)" % fr["doi_pct"]})
            vl = v.get("long") or {}
            if vl.get("side") == "AVOID":
                agn.append({"k": "long", "t": "the twelve-month side says AVOID — a trade, not a holding"})
            elif vl.get("side") == "ACCUMULATE":
                sup.append({"k": "long", "t": "the twelve-month side agrees (ACCUMULATE, score %s)" % vl.get("score")})
            hs = vr.get("h") or 20; tgt = vr.get("target"); stop = vr.get("stop")
            if tgt and px:
                target = tgt if hs <= 25 else _f(px + (tgt - px) * math.sqrt(20.0 / hs))
            else:
                target = None
            exp_pct = _f((target / px - 1) * 100, 1) if (target and px) else None
            label = "1 month"
        # the cone at the horizon
        cone = cone_at(v.get("hz"), h, px)
        if cone and cone.get("p_up") is not None:
            (sup if cone["p_up"] >= 55 else agn).append({"k": "cone", "t": "the horizon cone puts the odds of being higher in %s at %d%%" % (label, cone["p_up"])})
        keys = {x["k"] for x in sup}
        conv = min(5, len(keys))
        hard_no = any(x["k"] in ("news", "results") and (x["k"] == "news" or (kind == "short" and ev_days.get(s, 99) <= 3)) for x in agn) or any(x["k"] == "trend" for x in agn)
        word = "HIGH" if conv >= 5 else "GOOD" if conv == 4 else "FAIR" if conv == 3 else "THIN"
        out = {"sym": s, "nm": u["nm"], "sector": u["sector"], "side": "BUY", "px": px, "d1": u["d1"], "target": _f(target), "stop": _f(stop), "exp_pct": exp_pct,
               "h": h, "label": label, "kind": kind, "score": vr.get("score"), "verdict": vr.get("side"), "conv": conv, "conv_word": word, "supports": sup[:7], "against": agn[:4],
               "news": nitems[:3], "news_verdict": nv, "cone": cone, "fno": bool(u["fno"]), "lots": (v.get("fno") or {}).get("lots"), "hard_no": bool(hard_no),
               "size_pct": (vr.get("size_pct") if kind == "short" else None), "gate": bool(gate)}
        return out
    longs = []
    for s, _ in long_pool[:12]:
        try:
            c = build(s, "long")
            if not c["hard_no"] and c["conv"] >= 3:
                longs.append(c)
        except Exception:
            continue
        if len(longs) >= 4:
            break
    longs.sort(key=lambda c: (-c["conv"], -(c["score"] or 0)))
    # ── the short call ──
    short_pool = []
    for s, v in V.items():
        vs = v.get("short") or {}
        if vs.get("side") != "BUY" or (U[s]["turn"] or 0) < PICK_CR / 2 or U[s]["sector"] == "ETF" or not seasoned(s, 120, 45):
            continue
        short_pool.append((s, vs.get("score") or 0))
    short_pool.sort(key=lambda x: (-x[1], -(U[x[0]]["turn"] or 0)))
    shorts = []
    for s, _ in short_pool[:14]:
        try:
            c = build(s, "short")
            if not c["hard_no"] and c["conv"] >= 3:
                shorts.append(c)
        except Exception:
            continue
        if len(shorts) >= 4:
            break
    shorts.sort(key=lambda c: (-c["conv"], -(c["score"] or 0)))
    how = ("the long call is the ACCUMULATE with the most independent supports among the twelve highest long scores (investable names, a seasoned tape, a profile on file): "
           "the trend, the company's numbers, its record in this regime, the Street's target, the week's news, the delivery read, the engine's own record on the name, the horizon cone. "
           "The short call is the same test on the BUYs, with the contenders model, the futures build-up and the twelve-month side added; its target is the verdict's, "
           "scaled to twenty sessions. Conviction is the number of distinct supports (1–5): HIGH 5 · GOOD 4 · FAIR 3; nothing is called below three, or against the week's "
           "news, or into results within three sessions. Both are frozen with the day and scored — the short call at twenty sessions, the long at sixty and at 250.")
    return {"asof": today, "regime": regime, "long": (longs[0] if longs else None), "short": (shorts[0] if shorts else None), "long_also": longs[1:3], "short_also": shorts[1:3],
            "n_long_tested": min(12, len(long_pool)), "n_short_tested": min(14, len(short_pool)), "how": how}


def _inr(x):
    try:
        v = float(x)
    except Exception:
        return "—"
    if v >= 1e5:
        return "{:,.0f}".format(v)
    return ("{:,.2f}".format(v)).rstrip("0").rstrip(".") if v < 100 else "{:,.0f}".format(v)


# ── 14f · the brief — the day's major updates ─────────────────────────────────
def _bid(today, k, t):
    return hashlib.md5(("%s|%s|%s" % (today, k, t)).encode("utf-8")).hexdigest()[:10]


def brief_block(B, U, V, mkt, nc, alloc, changes, movers, events, rec, calls, attr, N, street, pairs, today, prev_lite, pass_kind=None):
    items = []
    def add(k, w, t, d=None, sym=None, go=None, n=None):
        items.append(_clean({"id": _bid(today, k, t), "k": k, "w": w, "t": t, "d": d, "sym": sym, "go": go, "n": n}))
    # the calls
    L = (calls or {}).get("long"); S_ = (calls or {}).get("short")
    if L:
        add("call", 100, "LONG · Buy %s — target ₹%s in 12 months" % (L["nm"], _inr(L["target"])), "conviction %d/5 (%s) · at ₹%s · exit ₹%s · %s" % (L["conv"], L["conv_word"], _inr(L["px"]), _inr(L["stop"]), (L["supports"][0]["t"] if L.get("supports") else "")), L["sym"], ["home", "calls"])
    if S_:
        add("call", 99, "SHORT · Buy %s — target ₹%s in 1 month" % (S_["nm"], _inr(S_["target"])), "conviction %d/5 (%s) · at ₹%s · stop ₹%s · %s" % (S_["conv"], S_["conv_word"], _inr(S_["px"]), _inr(S_["stop"]), (S_["supports"][0]["t"] if S_.get("supports") else "")), S_["sym"], ["home", "calls"])
    if not L and not S_:
        add("call", 98, "No call today", "nothing stacked three independent supports without an objection — the desk waits", None, ["home", "calls"])
    # the market
    nd = mkt.get("nifty_d1"); br = mkt.get("breadth") or {}
    add("market", 90, "Nifty %s · %s" % (("%+.2f%%" % nd) if nd is not None else "—", mkt.get("call") or ""), "breadth %s up / %s down among the liquid names · VIX %s · %s" % (br.get("up", "—"), br.get("down", "—"), mkt.get("vix") or "—", mkt.get("call_how") or ""), None, ["micro", "today"])
    # the regime and the nowcast
    probs = (nc or {}).get("probs") or {}
    if probs:
        top = max(probs.items(), key=lambda x: x[1])
        prev_probs = ((prev_lite or {}).get("nowcast") or {}).get("probs") or {}
        shift = ""
        if prev_probs:
            dmax = max(((k, probs.get(k, 0) - prev_probs.get(k, 0)) for k in probs), key=lambda x: abs(x[1]))
            if abs(dmax[1]) >= 8:
                shift = " · %s %+.0f pts since the last pass" % (dmax[0], dmax[1])
        add("regime", 85, "Regime %s · the market's nowcast %s %d%%%s" % (mkt.get("regime"), top[0], round(top[1]), shift), ("the gate is ON — sizes halved" if mkt.get("gate") else "the gate is off") + (" · " + (nc.get("lean") and ("the market leans " + nc["lean"]) or "") if not nc.get("agree") else " · the nowcast agrees with the official regime"), None, ["macro"], None)
    # the flows
    fl = B.get("FLOWS_LIVE") or {}
    if fl.get("fii") is not None:
        add("flows", 70, "FII %s₹%s cr · DII %s₹%s cr (%s)" % ("+" if fl["fii"] >= 0 else "−", _inr(abs(fl["fii"])), "+" if (fl.get("dii") or 0) >= 0 else "−", _inr(abs(fl.get("dii") or 0)), fl.get("asof") or "latest"), None, None, ["forex"])
    # what changed
    C = changes or {}
    for key, word, w in (("to_buy", "turned BUY", 80), ("to_sell", "turned SELL", 79), ("to_acc", "turned ACCUMULATE", 72), ("to_avoid", "turned AVOID", 71), ("from_buy", "left BUY", 68)):
        rows_ = C.get(key) or []
        if rows_:
            add("changes", w, "%d name%s %s since %s" % (C.get("n_" + key, len(rows_)), "" if C.get("n_" + key, len(rows_)) == 1 else "s", word, C.get("since") or "yesterday"), ", ".join(r["nm"] for r in rows_[:4]) + (" …" if len(rows_) > 4 else ""), (rows_[0]["sym"] if len(rows_) == 1 else None), ["micro", "today"], len(rows_))
    # tomorrow's movers
    mv = (movers or {}).get("list") or []
    if mv:
        add("movers", 75, "Tomorrow's likely movers: %s" % ", ".join("%s %d%%" % (m["nm"], m["p_move"]) for m in mv[:3]), "P(move ≥ 1.5σ) · the model's out-of-sample AUC %s" % movers.get("auc_move"), mv[0]["sym"], ["micro", "today"], len(mv))
    # results
    er = [r for r in (events or {}).get("rows") or [] if r.get("days") is not None and 0 <= r["days"] <= 1]
    if er:
        add("results", 74, "Results %s: %s" % ("today / tomorrow", ", ".join(r["nm"] for r in er[:5]) + (" …" if len(er) > 5 else "")), "a results day moves more than any stop allows for", (er[0]["sym"] if len(er) == 1 else None), ["micro", "today"], len(er))
    # why it moved — the biggest stock-specific moves
    own = [r for r in (attr or {}).get("rows") or [] if r.get("kind") == "STOCK-SPECIFIC" and abs(r.get("d1") or 0) < 35][:3]
    if own:
        add("moved", 73, "Stock-specific moves: %s" % ", ".join("%s %+.1f%%" % (r["nm"], r["d1"]) for r in own), (own[0].get("news")[0]["t"] if own[0].get("news") else own[0]["note"]), own[0]["sym"], ["micro", "today"], len(own))
    # the record — what was scored this pass
    last_rows = []
    for k in ("today_buys", "short_buy", "fno", "movers"):
        for x in ((rec or {}).get(k) or {}).get("last") or []:
            last_rows.append((k, x))
    if last_rows:
        dates = sorted({x["date"] for _, x in last_rows})
        d_last = dates[-1]
        rs = [x for k, x in last_rows if x["date"] == d_last and k != "movers"]
        mvr = [x for k, x in last_rows if x["date"] == d_last and k == "movers"]
        if rs:
            hits = sum(1 for x in rs if (x.get("ret") or 0) > 0)
            add("record", 66, "Scored: %d of %d picks from %s closed in the money" % (hits, len(rs), d_last), ("movers: %d of %d moved ≥ 1.5σ" % (sum(1 for x in mvr if x.get("moved")), len(mvr))) if mvr else None, None, ["micro", "records"])
    # the Street
    sb = (street or {}).get("bull") or []; sbr = (street or {}).get("bear") or []
    if sb or sbr:
        add("street", 60, "The Street: the engine is %s" % (("more bullish than the Street on %s (+%s pts)" % (sb[0]["nm"], sb[0]["gap"])) if sb else ("more bearish than the Street on %s (%s pts)" % (sbr[0]["nm"], sbr[0]["gap"]))), "%d names with five or more analysts · the two agree on direction %s%% of the time" % (street.get("n") or 0, street.get("agree_pct")), (sb[0]["sym"] if sb else None), ["micro", "street"])
    # where to be
    rows_ = (alloc or {}).get("rows") or []
    ov = [(r.get("nm") or r.get("sym")) for r in rows_ if r.get("word") == "OVERWEIGHT"]; un = [(r.get("nm") or r.get("sym")) for r in rows_ if r.get("word") == "UNDERWEIGHT"]
    if ov or un:
        add("alloc", 58, "Where to be: overweight %s" % (", ".join(ov[:3]) or "nothing"), ("underweight " + ", ".join(un[:3])) if un else None, None, ["micro", "where"])
    # pairs
    pi = (pairs or {}).get("ideas") or []
    if pi:
        add("pairs", 55, "%d market-neutral pair%s open: %s" % (len(pi), "" if len(pi) == 1 else "s", ", ".join("%s / %s" % (p["a"], p["b"]) for p in pi[:3])), None, None, ["micro", "fno"], len(pi))
    # the news
    for x in ((N or {}).get("market") or [])[:4]:
        add("news", 50, x["t"], (x.get("src") or "") + ((" · %s" % ("today" if (x.get("age_d") or 9) <= 1 else "%d days ago" % round(x["age_d"]))) if x.get("age_d") is not None else ""), None, ["news"])
    # the pass
    add("pass", 10, "Pass %s IST%s" % (now_ist().strftime("%H:%M"), (" · " + pass_kind) if pass_kind else ""), "engine %s" % VERSION, None, ["micro", "records"])
    items.sort(key=lambda x: -x["w"])
    return {"asof": today, "at": now_ist().strftime("%Y-%m-%d %H:%M"), "n": len(items), "items": items,
            "how": "the day's major updates as the engine sees them at this pass: the calls, the market, the regime and the nowcast, flows, the verdicts that flipped, tomorrow's movers, results, the stock-specific moves, what was scored, the Street, where to be, the pairs, the market's headlines. The page keeps what you have seen."}


def movers_enrich(movers, N, T, U):
    """v148 · what the news and the delivery add to the movers: a name in the news today gets +5% of the headroom (stated, not learned);
    the delivery read rides on the card as a driver. Re-ranked, cut to twelve."""
    rows = (movers or {}).get("list") or []
    for m in rows:
        try:
            nrec = (N.get("names") or {}).get(m["sym"]) or {}
            fresh = [x for x in (nrec.get("items") or []) if x.get("age_d") is not None and x["age_d"] <= 1.5]
            if fresh:
                p = (m["p_move"] or 0) / 100.0
                m["p_move"] = _f(100 * (p + 0.05 * (1 - p)), 0)
                m["drivers"] = (["in the news today: “%s”" % fresh[0]["t"][:90]] + (m.get("drivers") or []))[:4]
                m["news"] = fresh[:2]
            dw = delivery_word(T.get(m["sym"]) or {}, U[m["sym"]]["d1"])
            if dw:
                m["dlv"] = dw[0]
                m["drivers"] = ((m.get("drivers") or []) + [dw[1]])[:5]
        except Exception:
            continue
    rows.sort(key=lambda x: -(x["p_move"] or 0))
    if movers is not None:
        movers["list"] = rows[:12]
    return movers


def news_candidates(U, T, V, movers, events, changes, attr_syms, n_long=12, n_short=14):
    """who gets a Google News look this pass, in priority order: the calls' pools, tomorrow's movers, results today/tomorrow, the verdicts that flipped, the day's big movers"""
    def seasoned(s, nd=200, nw=100):
        t = T.get(s) or {}
        return (t.get("n") or 0) >= (nd if t.get("src") == "daily" else nw)
    longs = sorted([s for s, v in V.items() if ((v.get("long") or {}).get("side") == "ACCUMULATE" and (U[s]["turn"] or 0) >= PICK_CR / 2 and U[s]["sector"] != "ETF" and seasoned(s))],
                   key=lambda s: (-((V[s].get("long") or {}).get("score") or 0), -(U[s]["turn"] or 0)))[:n_long]
    shorts = sorted([s for s, v in V.items() if ((v.get("short") or {}).get("side") == "BUY" and (U[s]["turn"] or 0) >= PICK_CR / 2 and U[s]["sector"] != "ETF" and seasoned(s, 120, 45))],
                    key=lambda s: (-((V[s].get("short") or {}).get("score") or 0), -(U[s]["turn"] or 0)))[:n_short]
    out = []
    for s in longs + shorts + [m["sym"] for m in ((movers or {}).get("list") or [])[:12]] + [r["sym"] for r in ((events or {}).get("rows") or []) if r.get("days") is not None and 0 <= r["days"] <= 1][:8] \
            + [r["sym"] for r in ((changes or {}).get("to_buy") or [])[:4]] + [r["sym"] for r in ((changes or {}).get("to_sell") or [])[:3]] + list(attr_syms or [])[:10]:
        if s in U and s not in out:
            out.append(s)
    return [(s, U[s]["nm"]) for s in out[:48]]


def main(argv):
    t0 = time.time()
    offline = "--offline" in argv or os.environ.get("MI_OFFLINE") == "1"
    budget = 480; fbudget = 150; max_age = 6
    for i, a in enumerate(argv):
        if a == "--budget" and i + 1 < len(argv):
            budget = int(argv[i + 1])
        if a == "--fund-budget" and i + 1 < len(argv):
            fbudget = int(argv[i + 1])
        if a == "--max-age" and i + 1 < len(argv):
            max_age = float(argv[i + 1])
    page = next((a for a in argv[1:] if a.endswith(".html")), PAGE)
    today = now_ist().strftime("%Y-%m-%d")
    print("=== MacroIntel ENGINE %s · %s IST%s ===" % (VERSION, now_ist().strftime("%a %b %d %H:%M"), " · offline" if offline else ""))
    B = read_page(page)
    FUND0 = load_fund()
    U, fno, opt = build_universe(B, FUND0)
    log("universe: %d names (%d NSE with a line, %d F&O, %d BSE-only)" % (len(U), sum(1 for u in U.values() if u["x"] == "NSE"), sum(1 for u in U.values() if u["fno"]), sum(1 for u in U.values() if u["x"] == "BSE")))
    W, D, psrc = get_prices(U, offline, budget, max_age_h=max_age)
    log("prices: %s" % psrc)
    try:
        W = bse_rotation(U, W, offline)
    except Exception as _e:
        log("BSE tapes: skipped (%s)" % type(_e).__name__)
    # v148 · delivery: NSE's deliverable quantity per name, the last sixty sessions cached between passes
    DL, dl_date, DLC = {}, None, {}
    try:
        DLC = fetch_delivery((B["MOVERS_LIVE"] or {}).get("date"), offline)
        DL, dl_date = delivery_read(DLC, U)
        log("delivery: %d names for %s (%d sessions on file, %d fetched this pass)" % (len(DL), dl_date, len(DLC.get("days") or {}), DLC.get("fetched") or 0))
    except Exception as _e:
        log("delivery: skipped (%s: %s)" % (type(_e).__name__, str(_e)[:60]))
    # the series shards: every name's weekly closes (3y online, 1y offline) and the daily closes where the panel has them —
    # so the research page draws its charts for every share without a live door
    try:
        write_series_shards(U, W, D)
    except Exception as _e:
        log("series shards: skipped (%s)" % type(_e).__name__)
    F = factor_frame(W)
    labels = regime_labels(W.index)
    imp = macro_impulse(F)
    regime = ((B["REGIME_LIVE"] or {}).get("quad") or "REFLATION").title()
    if regime not in ("Reflation", "Goldilocks", "Stagflation", "Disinflation"):
        regime = "Reflation"
    edge = ((B["ML_OUTPUT"] or {}).get("regime_edge") or {}).get("sectors") or {}
    ps = {}; gate = False
    try:
        fs = json.load(open("fno_setups.json"))
        ps = fs.get("page_state") or {}
        gate = bool(fs.get("gate") if fs.get("gate") is not None else ((ps.get("watch") or {}).get("gate")))
        ps["gate"] = gate
    except Exception:
        pass
    cont = (B["ML_OUTPUT"] or {}).get("contenders") or {}
    dipn = ((B["ML_OUTPUT"] or {}).get("dip") or {}).get("names") or {}
    # v146 · the option chain (written by update_terminal.py this pass) and the carry rate
    global CHAIN, REPO_RATE
    CHAIN, chain_date = load_chain()
    REPO_RATE = float(B["MACRO_LIVE"].get("repo") or 5.5)
    log("option chain: %s" % ("%d underlyings (%s)" % (len(CHAIN), chain_date) if CHAIN else "not on disk — spreads priced off the ATM IV"))
    # the tape and the DNA
    T, DNA, WIND = {}, {}, {}
    n_dna = 0
    for s, u in U.items():
        T[s] = tape_features(s, W, D, u)
        if s in DL:
            T[s]["dlv"], T[s]["dlv_avg"], T[s]["dlv_z"] = DL[s]["dlv"], DL[s]["dlv_avg"], DL[s]["dlv_z"]
        if u["x"] == "NSE" or s in W.columns:
            d = macro_dna(s, W, F, labels)
            if d:
                DNA[s] = d; n_dna += 1
                WIND[s] = wind_of(d, imp)
    log("tape: %d daily · %d weekly · %d bhavcopy-only" % (sum(1 for t in T.values() if t["src"] == "daily"), sum(1 for t in T.values() if t["src"] == "weekly"), sum(1 for t in T.values() if t["src"] == "bhavcopy")))
    log("DNA: %d names with betas (%d weeks of factors) · impulse %s" % (n_dna, len(F.dropna()), {k: v["move"] for k, v in imp.items()}))
    # fundamentals, on a rotation
    prio = sorted([s for s, u in U.items() if u["x"] == "NSE" and (u["turn"] or 0) >= LIQUID_CR], key=lambda s: -(U[s]["turn"] or 0))
    FUND, n_new = fund_refresh(U, prio, budget=fbudget, offline=offline)
    n_f = sum(1 for s in U if (FUND.get("names") or {}).get(s) and not FUND["names"][s].get("empty"))
    log("fundamentals: %d names on file (%d refreshed this pass)" % (n_f, n_new))
    srs = sector_rs_from(U, T, W)
    SC, sector_pe = score_universe(U, T, DNA, WIND, FUND, cont, dipn, regime, edge, gate, opt, fno, srs)
    # the previous pass's engine.json (the brief compares the nowcast against it)
    prev_lite = None
    try:
        prev_lite = json.load(open(OUT))
    except Exception:
        prev_lite = None
    # the previous picks (for stickiness)
    prev = {}
    try:
        files = sorted(f for f in os.listdir(HIST_DIR) if f.startswith("engine_") and f.endswith(".json"))
        prevf = [f for f in files if f != "engine_%s.json" % today.replace("-", "")]
        if prevf:
            prev = json.load(open(os.path.join(HIST_DIR, prevf[-1]))).get("picks") or {}
        try:
            prev_full = json.load(open(OUT)).get("picks") or {}
            for k in prev_full:
                prev[k] = prev_full[k]     # held_from survives
        except Exception:
            pass
    except Exception:
        prev = {}
    V = verdicts(U, T, DNA, WIND, SC, FUND, fno, opt, edge, regime, gate, prev)
    # v147 · the four numbers behind "any horizon" ride on every scored name
    for s_, v_ in V.items():
        if v_.get("short") is not None or v_.get("long") is not None:
            try:
                v_["hz"] = horizon_params(v_, T.get(s_) or {}, U[s_])
            except Exception:
                pass
    P = pick_lists(U, V, SC, T, prev, fno)
    S = sector_table(U, V, SC, T, W, DNA, edge, regime)
    # v145 · the pairs (market-neutral, inside F&O) and WHERE TO BE (the regime → asset map)
    try:
        pairs = pairs_block(U, D, fno, V, z_min=float(os.environ.get("MI_PAIRS_ZMIN") or 2.0))   # the env override exists for local screenshots only
        log("pairs: %d tested · %d fit · %d ideas %s" % (pairs["n_tested"], pairs["n_fit"], len(pairs["ideas"]), [(i["a"], i["b"], i["z"]) for i in pairs["ideas"]]))
    except Exception as _e:
        pairs = {"ideas": [], "n_tested": 0, "n_fit": 0, "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("pairs: failed (%s)" % pairs["error"])
    X = None
    try:
        X, xsrc = fetch_sleeves(offline)
    except Exception as _e:
        X, xsrc = None, "failed (%s)" % type(_e).__name__
    # v146 · the nowcast: the regime as probabilities, the market's impulses
    try:
        nc = nowcast_block(B, X, regime, B["MACRO_LIVE"].get("repo"))
        log("nowcast: growth z %s · inflation z %s · liquidity z %s → %s (official %s) · %s" % (nc["impulses"]["growth"]["z"], nc["impulses"]["inflation"]["z"], nc["impulses"]["liquidity"]["z"], nc["probs"], regime, "agree" if nc["agree"] else "the market leans " + nc["lean"]))
    except Exception as _e:
        nc = {"official": {"label": regime}, "probs": None, "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("nowcast: failed (%s)" % nc["error"])
    try:
        alloc = alloc_block(U, X, regime, gate, B["MACRO_LIVE"].get("repo"), probs=nc.get("probs"))
        alloc["source"] = xsrc
        log("where to be: %d sleeves · %s · %s" % (len(alloc["rows"]), xsrc, " · ".join("%s %s%%" % (a["sym"], a["pct"]) for a in alloc["alloc"])))
    except Exception as _e:
        alloc = {"regime": regime, "gate": bool(gate), "rows": [], "alloc": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("where to be: failed (%s)" % alloc["error"])
    # v147 · the results calendar, tomorrow's likely movers, what changed since yesterday
    try:
        events = events_block(U, FUND, today)
        log("events: %d names report within ten days" % events["n"])
    except Exception as _e:
        events = {"asof": today, "n": 0, "rows": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
    try:
        movers = movers_block(U, T, D, DVOL, opt, fno, V, FUND, today)
        log("movers: %s" % (("AUC move %s · dir %s · base %s%% · %s names · %s sessions%s · top %s" % (movers.get("auc_move"), movers.get("auc_dir"), movers.get("base_rate"), movers.get("names"), movers.get("sessions"), "" if movers.get("has_volume") else " · no volume panel", [(m["sym"], m["p_move"], m["lean"]) for m in movers["list"][:5]])) if movers.get("list") else movers.get("note")))
    except Exception as _e:
        movers = {"asof": today, "list": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("movers: failed (%s)" % movers["error"])
    try:
        changes = sides_snapshot_and_changes(U, V, today)
        log("changes since %s: %d→BUY · %d left BUY · %d→SELL · %d→ACCUMULATE · %d→AVOID" % (changes.get("since"), changes.get("n_to_buy", 0), changes.get("n_from_buy", 0), changes.get("n_to_sell", 0), changes.get("n_to_acc", 0), changes.get("n_to_avoid", 0)))
    except Exception as _e:
        changes = {"since": None, "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
    mkt = market_line(B, U, V, W, gate, regime, ps)
    # v146 · the macro call, frozen with the day (regime, probabilities, the session's call, the sleeves' words and prices)
    macro_fz = None
    try:
        rows_ = alloc.get("rows") or []
        macro_fz = {"regime": regime, "probs": nc.get("probs"), "call": mkt.get("call"), "gate": bool(gate),
                    "over": [r["sym"] for r in rows_ if r.get("word") == "OVERWEIGHT"], "under": [r["sym"] for r in rows_ if r.get("word") == "UNDERWEIGHT"],
                    "book": [{"sym": a["sym"], "pct": a["pct"]} for a in (alloc.get("alloc") or []) if a.get("sym")],
                    "px": {r["sym"]: r["px"] for r in rows_ if r.get("px")}, "nifty": mkt.get("nifty")}
    except Exception:
        macro_fz = None
    # v148 · score first (the calls lean on the engine's record per name), then the news, why it moved, the Street, the calls, the brief — then freeze the day
    rec = freeze_and_score(P, U, W, D, today, pairs=pairs.get("ideas"), macro=macro_fz, movers=movers.get("list"), freeze=False)
    big = []
    try:
        big = sorted([s for s, u in U.items() if u["d1"] is not None and (u["turn"] or 0) >= LIQUID_CR and u["sector"] != "ETF" and abs(u["d1"]) >= max(1.5 * ((T.get(s) or {}).get("sig1d") or 2.0), 2.0)],
                     key=lambda s: -abs(U[s]["d1"]) / ((T.get(s) or {}).get("sig1d") or 2.0))[:10]
    except Exception:
        big = []
    try:
        N = fetch_news(news_candidates(U, T, V, movers, events, changes, big), offline, budget_s=int(os.environ.get("MI_NEWS_BUDGET") or 90))
        log("news: %d names (%d fetched, %d from the cache) · %d market headlines" % (N["n_names"], N["n_fetched"], N["n_cached"], len(N.get("market") or [])))
    except Exception as _e:
        N = {"asof": today, "n_names": 0, "names": {}, "market": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("news: failed (%s)" % N["error"])
    movers = movers_enrich(movers, N, T, U)
    try:
        attr = attribution_block(U, T, DNA, mkt, N, today)
        log("why it moved: %d big moves · %s · %s" % (attr["n"], attr["kinds"], [(r["sym"], r["d1"], r["kind"]) for r in attr["rows"][:4]]))
    except Exception as _e:
        attr = {"asof": today, "n": 0, "rows": [], "by": {}, "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("why it moved: failed (%s)" % attr["error"])
    try:
        street = street_block(U, V, FUND, today)
        log("the Street: %d names · agree %s%% · corr %s · bull %s · bear %s" % (street.get("n") or 0, street.get("agree_pct"), street.get("corr"), [(r["sym"], r["gap"]) for r in street.get("bull", [])[:3]], [(r["sym"], r["gap"]) for r in street.get("bear", [])[:3]]))
    except Exception as _e:
        street = {"asof": today, "n": 0, "bull": [], "bear": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("the Street: failed (%s)" % street["error"])
    try:
        calls = conviction_calls(U, T, V, SC, DNA, FUND, regime, edge, fno, opt, N, events, rec.get("by_sym"), today, gate)
        log("calls: LONG %s · SHORT %s (%d long / %d short tested)" % (("%s %d/5 → ₹%s" % (calls["long"]["sym"], calls["long"]["conv"], calls["long"]["target"])) if calls.get("long") else "none",
                                                                     ("%s %d/5 → ₹%s" % (calls["short"]["sym"], calls["short"]["conv"], calls["short"]["target"])) if calls.get("short") else "none", calls["n_long_tested"], calls["n_short_tested"]))
    except Exception as _e:
        calls = {"asof": today, "long": None, "short": None, "long_also": [], "short_also": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("calls: failed (%s)" % calls["error"])
    try:
        freeze_day(P, U, W, D, today, pairs=pairs.get("ideas"), macro=macro_fz, movers=movers.get("list"), calls=calls, street=street)
    except Exception as _e:
        log("freeze: failed (%s)" % type(_e).__name__)
    try:
        brief = brief_block(B, U, V, mkt, nc, alloc, changes, movers, events, rec, calls, attr, N, street, pairs, today, prev_lite, pass_kind=(os.environ.get("MI_PASS_KIND") or None))
        log("brief: %d items · %s" % (brief["n"], [x["t"][:50] for x in brief["items"][:3]]))
    except Exception as _e:
        brief = {"asof": today, "n": 0, "items": [], "error": "%s: %s" % (type(_e).__name__, str(_e)[:80])}
        log("brief: failed (%s)" % brief["error"])
    shock = shock_block(B, W)
    pool = arena_pool(U, V, P)
    # ── assemble ──
    names = {}
    for s, u in U.items():
        t = T[s]; sc = SC[s]; v = V[s]
        f = (FUND.get("names") or {}).get(s)
        if f and f.get("empty"):
            f = None
        names[s] = {"nm": u["nm"], "sector": u["sector"], "px": u["px"], "d1": u["d1"], "w1": u["w1"], "turn": u["turn"], "fno": u["fno"], "x": u["x"],
                    "tape": {k: t.get(k) for k in TAPE_KEYS},
                    "dna": DNA.get(s), "wind": WIND.get(s), "fund": f,
                    "sc": {k: sc.get(k) for k in ("short", "long", "intra", "T", "TL", "M", "ML", "Q", "F", "C", "R", "liquid", "thin")},
                    "v": v, "cont": sc.get("cont"),
                    "opt": ({k: (opt.get(s) or {}).get(k) for k in ("atm_iv", "implied_move_pct", "implied_1d_pct", "pcr_oi", "max_pain", "call_wall", "put_wall", "skew_25d", "expiry", "dte")} if opt.get(s) else None),
                    "fut": ({k: (fno.get(s) or {}).get(k) for k in ("c", "u", "b", "d", "oi", "doi_pct", "xp", "lot")} if fno.get(s) else None)}
        if u.get("code"):
            names[s]["code"] = u["code"]
    counts = {"buy": mkt["n_buy"], "sell": mkt["n_sell"], "accumulate": mkt["n_accumulate"], "avoid": sum(1 for v in V.values() if (v.get("long") or {}).get("side") == "AVOID"),
              "intraday": sum(1 for v in V.values() if (v.get("intra") or {}).get("side")), "fno": sum(1 for v in V.values() if v.get("fno"))}
    out = {"version": VERSION, "generated": now_ist().strftime("%a %b %d, %Y %H:%M IST"), "asof": today, "bhav_date": (B["MOVERS_LIVE"] or {}).get("date"),
           "universe_n": len(U), "counts": counts, "regime": regime, "gate": gate, "market": mkt, "impulse": imp, "factor_label": FACTOR_LABEL,
           "names": names, "picks": P, "sectors": S, "record": rec, "shock": shock, "arena_pool": pool, "alloc": alloc, "pairs": pairs, "nowcast": nc,
           "movers": movers, "events": events, "changes": changes, "chain_n": len(CHAIN),
           "brief": brief, "calls": calls, "attr": attr, "street": street,
           "news": {"asof": N.get("asof"), "n_names": N.get("n_names"), "names": sorted((N.get("names") or {}).keys()), "n_market": len(N.get("market") or []), "error": N.get("error")},
           "delivery": {"date": dl_date, "n": len(DL), "sessions": len(DLC.get("days") or {}), "fetched": DLC.get("fetched")},
           "fund_updated": FUND.get("updated"), "fund_n": n_f, "sector_pe": sector_pe,
           "method": {"short": "0.40 trend (risk-adjusted 20/60-session momentum, the 50-day, the 52-week position, −extension) + 0.22 macro (the wind, the sector's regime edge × its t, sector RS) + 0.13 futures flow + 0.15 the contenders + 0.10 quality; percentile-ranked; BUY ≥ 80, SELL ≤ 10 (F&O only); stop 1.5 × 5-day σ (4–14%), target 2R, horizon 5–60 sessions by volatility, size = 1% of capital / stop (halved when the gate is on)",
                      "long": "0.35 trend (120/250-session momentum, the 200-day) + 0.25 macro (the sector's regime edge, sector RS, the name's own regime record) + 0.30 quality (ROE, margins, growth, debt, P/E vs sector, P/B, promoter) + 0.10 drawdown; ACCUMULATE ≥ 80, AVOID ≤ 20; the stop is the 200-day; the 12-month target = shrunk momentum + the sector's regime edge + a quality tilt, with a ±1σ band",
                      "intraday": "the names in play: yesterday's move in σ units, turnover, the futures lean, the contenders' p(move); a side only when the lean is clear; entry zone, stop 0.9σ, target 1.6σ, flat by 15:20",
                      "sources": {"prices": psrc, "fundamentals": "Yahoo profile, rotating, cached", "regime": "REGIME_LIVE · " + regime, "edge": "ML_OUTPUT.regime_edge", "contenders": ("ML_OUTPUT.contenders" if cont else "not on this pass")}},
           "log": LOG, "secs": _f(time.time() - t0, 1)}
    # two files: engine.json (the lists, the sectors, the market, a lite row per name) loads with the page;
    # engine_full.json (every name in full) loads on the first research page or Ask
    lite = dict(out)
    lite["names"] = {s: _clean({"nm": r["nm"], "sector": r["sector"], "px": r["px"], "d1": r["d1"], "w1": r["w1"], "turn": r["turn"], "fno": r["fno"] or None, "x": (r["x"] if r["x"] != "NSE" else None),
                                "s": r["sc"].get("short"), "l": r["sc"].get("long"), "i": r["sc"].get("intra"),
                                "ss": (r["v"].get("short") or {}).get("side"), "ls": (r["v"].get("long") or {}).get("side"), "is": (r["v"].get("intra") or {}).get("side"),
                                "lots": (r["v"].get("fno") or {}).get("lots"), "code": r.get("code")}) for s, r in names.items()}
    lite["sectors"] = {k: {kk: vv for kk, vv in v.items() if kk != "members"} for k, v in S.items()}
    lite["arena_pool"] = None
    json.dump(_clean(lite), open(OUT, "w"), separators=(",", ":"), default=str)
    # the full rows, compact (arrays with a fixed key order — the page's decoder mirrors TAPE_KEYS / SC_KEYS), in eight shards by symbol
    shards = {i: {} for i in range(N_SHARDS)}
    for s, r in names.items():
        t = r["tape"] or {}; sc = r["sc"] or {}
        row = dict(r)
        row["tape"] = [TAPE_SRC.get(t.get("src"), 0)] + [t.get(k) for k in TAPE_KEYS[1:]]
        row["sc"] = [sc.get(k) for k in SC_KEYS]
        d = r.get("dna")
        if d:
            row["dna"] = {"n": d.get("n"), "n_all": d.get("n_all"), "since": d.get("since"), "r2": d.get("r2"), "b": {k: _f(v, 2) for k, v in (d.get("b") or {}).items()}, "t": {k: _f(v, 1) for k, v in (d.get("t") or {}).items()},
                          "regime": d.get("regime") or None}
        w = r.get("wind")
        if w:
            row["wind"] = {"total": w.get("total"), "parts": (w.get("parts") or [])[:3]}
        shards[shard_of(s)][s] = _clean(row)
    for i, rows in shards.items():
        json.dump({"version": VERSION, "asof": today, "shard": i, "names": rows}, open("engine_n%d.json" % i, "w"), separators=(",", ":"), default=str)
    json.dump({"version": VERSION, "generated": out["generated"], "asof": today, "sectors_members": {k: v["members"] for k, v in S.items()}, "arena_pool": pool,
               "tape_keys": TAPE_KEYS, "sc_keys": SC_KEYS, "shards": N_SHARDS}, open("engine_full.json", "w"), separators=(",", ":"), default=str)
    sz = os.path.getsize(OUT)
    log("shards: " + " · ".join("n%d %.0f KB" % (i, os.path.getsize("engine_n%d.json" % i) / 1e3) for i in range(N_SHARDS)))
    log("verdicts: %d BUY · %d SELL · %d ACCUMULATE · %d AVOID · %d in play today · %d F&O ideas" % (counts["buy"], counts["sell"], counts["accumulate"], counts["avoid"], counts["intraday"], counts["fno"]))
    log("picks: short %s · sell %s · long %s · intraday %s · F&O %s" % ([p["sym"] for p in P["short_buy"]], [p["sym"] for p in P["short_sell"]], [p["sym"] for p in P["long"]], [p["sym"] for p in P["intraday"]], [p["sym"] for p in P["fno"]]))
    log("record: " + " · ".join("%s n=%s%s" % (k, v.get("n"), (" hit %s%% avg %+.2f%%" % (v.get("hit"), v.get("avg") or 0)) if v.get("n") else "") for k, v in rec.items()))
    print("  → wrote %s (%.1f MB) in %.0fs" % (OUT, sz / 1e6, time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
