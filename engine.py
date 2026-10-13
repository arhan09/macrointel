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

VERSION = "v146"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
PAGE = "macro_intelligence_terminal.html"
OUT = "engine.json"
FUND_FILE = "fundamentals.json"
PRICES_FILE = "engine_prices.json"
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
TAPE_KEYS = ["src", "r1", "r5", "r20", "r60", "r120", "r250", "vs50", "vs200", "pos52", "sig1d", "sig5d", "ext20", "dd", "hi52", "lo52", "m50", "m200", "vol_ratio", "n"]
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
        if time.time() - t0 > budget * 0.6:
            log("weekly: budget reached at %d symbols" % (len(W) and sum(x.shape[1] for x in W)))
            break
        try:
            raw = yf.download(ch, period="3y", interval="1wk", progress=False, threads=True, auto_adjust=True, group_by="column")
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
    try:
        Dl = []
        dsyms = [s + ".NS" for s in syms_d] + list(MACRO.values())
        for ch in _chunks(dsyms, 180):
            if time.time() - t0 > budget:
                log("daily: budget reached")
                break
            raw = yf.download(ch, period="1y", interval="1d", progress=False, threads=True, auto_adjust=True, group_by="column")
            df = _close_frame(raw, ch)
            if df is not None:
                Dl.append(df)
        if Dl:
            D = pd.concat(Dl, axis=1)
            D = D.loc[:, ~D.columns.duplicated()]
            D.columns = [str(c).replace(".NS", "") for c in D.columns]
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


def get_prices(U, offline, budget, max_age_h=6):
    liquid = [s for s, u in U.items() if u["x"] == "NSE" and ((u["turn"] or 0) >= 0.5 or u["fno"])]
    top = sorted([s for s in liquid if U[s]["turn"]], key=lambda s: -U[s]["turn"])[:450]
    daily = list(dict.fromkeys(top + [s for s in liquid if U[s]["fno"]]))
    if not offline:
        # a panel pulled less than max_age_h ago is reused (the workflow caches it between passes):
        # weekly betas do not move in an hour, and the day's print rides in from the bhavcopy
        W, D, src = load_prices_cache(max_age_h=max_age_h)
        if W is not None and W.shape[1] >= 200:
            return W, D, src
        try:
            W, D = fetch_yahoo(liquid, daily, budget=budget)
            W = W.dropna(axis=1, thresh=26)
            if W.shape[1] >= 200:
                save_prices(W, D)
                return W, D, "Yahoo · %d names weekly (3y) · %d daily (1y)" % (W.shape[1], (D.shape[1] if D is not None else 0))
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
    else:
        T["src"] = "bhavcopy"
        T["r5"] = u.get("w1"); T["r20"] = T["r60"] = T["r120"] = T["r250"] = None
        T["vs50"] = T["vs200"] = None; T["sig1d"] = 2.0; T["sig5d"] = 4.5; T["ext20"] = None
        T["pos52"] = None; T["dd"] = None; T["vol_ratio"] = None; T["n"] = 0; T["hi52"] = T["lo52"] = None
        T["m50"] = T["m200"] = None; T["up20"] = None
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
    X = df[cols].values.astype(float); yv = df["y"].values.astype(float)
    try:
        b, t, r2 = ridge(yv, X)
    except Exception:
        return None
    out = {"n": int(len(df)), "r2": _f(r2, 2), "b": {}, "t": {}}
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
             "recommendationKey": "street_rec"}


def load_fund():
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
    # the rotation: priority names first, then the stalest; a name is fresh for 7 days
    def age(s):
        a = (names.get(s) or {}).get("asof")
        if not a:
            return 10 ** 6
        try:
            return (pd.Timestamp(today) - pd.Timestamp(a)).days
        except Exception:
            return 10 ** 6
    order = [s for s in priority if age(s) >= 7]
    rest = sorted([s for s in U if U[s]["x"] == "NSE" and s not in order and (U[s]["turn"] or 0) >= 1.0], key=lambda s: -age(s))
    order += [s for s in rest if age(s) >= 7]
    t0 = time.time(); n = 0
    for s in order:
        if time.time() - t0 > budget:
            break
        try:
            info = yf.Ticker(s + ".NS").info or {}
        except Exception:
            info = {}
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
            n += 1
        else:
            names.setdefault(s, {})["asof"] = today   # tried; nothing came — retry in a week
            names[s]["empty"] = True
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
    scorable = np.array([(T.get(s) or {}).get("src") != "bhavcopy" and U[s]["x"] == "NSE" for s in syms])
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
    tb = [(s, v["short"]) for s, v in V.items() if (v.get("short") or {}).get("side") == "BUY" and (U[s]["turn"] or 0) >= 25 and U[s]["sector"] != "ETF"]
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


def freeze_and_score(P, U, W, D, today, pairs=None, macro=None):
    """freeze today's picks (the pairs, the macro call); score every past file whose horizon has elapsed"""
    os.makedirs(HIST_DIR, exist_ok=True)
    fn = os.path.join(HIST_DIR, "engine_%s.json" % today.replace("-", ""))
    frozen = {"date": today, "picks": {k: [{"sym": p["sym"], "side": p["side"], "px": p["px"]} for p in v] for k, v in P.items()},
              "pairs": [{"a": p["a"], "b": p["b"], "px_a": p["px_a"], "px_b": p["px_b"]} for p in (pairs or [])], "macro": macro}
    nifty_px = None
    try:
        nifty_px = _f(D[MACRO["nifty"]].dropna().iloc[-1]) if (D is not None and MACRO["nifty"] in D.columns) else _f(W[MACRO["nifty"]].dropna().iloc[-1])
    except Exception:
        pass
    frozen["nifty"] = nifty_px
    if not os.path.exists(fn):
        json.dump(frozen, open(fn, "w"), separators=(",", ":"))
    # score
    H = {"intraday": 1, "fno": 10, "today_buys": 10, "short_buy": 20, "short_sell": 20, "long": 60}
    rows = {k: [] for k in H}
    rows["pairs"] = []; rows["macro"] = []
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
        # v145 · the pairs: long leg minus short leg, equal rupees, ten sessions — market-neutral, so no Nifty excess
        for p in o.get("pairs") or []:
            if sessions < 10 or not p.get("px_a") or not p.get("px_b"):
                continue
            pa, howa = px_after(p["a"], d0, 10); pb, _ = px_after(p["b"], d0, 10)
            if pa is None or pb is None:
                continue
            ret = (pa / p["px_a"] - 1) * 100 - (pb / p["px_b"] - 1) * 100
            rows["pairs"].append({"date": o["date"], "sym": p["a"] + " / " + p["b"], "side": "PAIR", "px": p["px_a"], "px1": _f(pa), "ret": _f(ret), "excess": _f(ret), "how": howa})
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
    H["pairs"] = 10; H["macro"] = 5
    for k, rs in rows.items():
        if not rs:
            rec[k] = {"n": 0}
            continue
        r = [x["ret"] for x in rs if x["ret"] is not None]
        ex = [x["excess"] for x in rs if x["excess"] is not None]
        rec[k] = {"n": len(r), "hit": _f(100 * np.mean([1 if x > 0 else 0 for x in r]), 0), "avg": _f(float(np.mean(r)), 2),
                  "avg_excess": (_f(float(np.mean(ex)), 2) if ex else None), "h": H[k], "last": rs[-12:]}
        if k == "macro":
            # the macro record reads differently: the call's hit rate, the model book against the Nifty, over minus under
            co = [x for x in rs if x.get("call_ok") is not None]
            sp = [x["over"] - x["under"] for x in rs if x.get("over") is not None and x.get("under") is not None]
            rec[k].update({"call_hit": (_f(100 * np.mean([1 if x["call_ok"] else 0 for x in co]), 0) if co else None),
                           "book_vs_nifty": rec[k]["avg_excess"], "over_minus_under": (_f(float(np.mean(sp)), 2) if sp else None), "n_spread": len(sp)})
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
        ser = None; es = None
        if X is not None:
            if proxy and proxy in X.columns:
                ser = X[proxy].copy()
                if fx and inr is not None:
                    ser = ser * inr
            if etf + ".NS" in X.columns:
                es = X[etf + ".NS"].dropna()
            if ser is None and es is not None:
                ser = es
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
                      "on": ("the ETF" if (proxy or "").endswith(".NS") else proxy)}
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
    """13-week log change, z-scored against its own history since 2015"""
    try:
        s = series.dropna()
        s = s[s.index >= since]
        if len(s) < 80:
            return None, None
        ch = np.log(s.astype(float)).diff(13).dropna()
        if len(ch) < 60 or float(ch.std()) == 0:
            return None, None
        return float((ch.iloc[-1] - ch.mean()) / ch.std()), float(ch.iloc[-1] * 100)
    except Exception:
        return None, None


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
        cyc = [c for c in ("^CNXAUTO", "^CNXMETAL", "^NSEBANK", "^CNXREALTY", "^CNXINFRA") if c in X.columns]
        dfn = [c for c in ("^CNXFMCG", "^CNXPHARMA", "^CNXIT") if c in X.columns]
        if cyc and dfn:
            sp = np.exp(np.log(X[cyc].astype(float)).mean(axis=1) - np.log(X[dfn].astype(float)).mean(axis=1))
            z, ch = _z13(sp); add("growth", "cyclicals against defensives (auto, metals, banks, realty, infra vs FMCG, pharma, IT)", z, ch, 0.5)
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
    imp = {}
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
            "impulses": imp, "words": words, "now": {"cpi": _f(cpi_now, 2), "iip": _f(iip_now, 2)}, "probs": probs, "lean": lean, "agree": (lean == regime),
            "p_hot": _f(100 * p_hot, 0), "p_grow": _f(100 * p_grow, 0),
            "how": "the official CPI and IIP are the anchor; the market's thirteen-week impulses (z-scored since 2015) nudge them — one σ of inflation impulse = 0.4 CPI points, one σ of growth impulse = 1.2 IIP points over the quarter; the quadrant lines (CPI 4, IIP 3) become probabilities through a logistic with the series' own noise (0.5 and 1.0 points). The label on the page stays the official one; the probabilities are the market's lean, and the model book blends its base weights by them.",
            "source": "MACRO_LIVE · the sleeves panel (twelve years weekly)"}


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
def write_series_shards(U, W, D, nw=160, nd=260):
    Wt = W.iloc[-nw:]; Dt = D.iloc[-nd:] if D is not None else None
    wdates = [d.strftime("%Y%m%d") for d in Wt.index]; ddates = [d.strftime("%Y%m%d") for d in Dt.index] if Dt is not None else []
    shards = {i: {} for i in range(N_SHARDS)}
    n_w = n_d = 0
    for s, u in U.items():
        if u["x"] != "NSE":
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
        if u["x"] == "NSE":
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
    rec = freeze_and_score(P, U, W, D, today, pairs=pairs.get("ideas"), macro=macro_fz)
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
                    "tape": {k: t.get(k) for k in ("src", "r1", "r5", "r20", "r60", "r120", "r250", "vs50", "vs200", "pos52", "sig1d", "sig5d", "ext20", "dd", "hi52", "lo52", "m50", "m200", "vol_ratio", "n")},
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
           "chain_n": len(CHAIN),
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
            row["dna"] = {"n": d.get("n"), "r2": d.get("r2"), "b": {k: _f(v, 2) for k, v in (d.get("b") or {}).items()}, "t": {k: _f(v, 1) for k, v in (d.get("t") or {}).items()},
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
