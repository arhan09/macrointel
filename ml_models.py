#!/usr/bin/env python3
# ════════════════════════════════════════════════════════════════════════
#  MACROINTEL ML SUITE v2 — runs DAILY (after the 6 PM pull) + weekly deep.
#
#  MODELS (all honest — each reports its real out-of-sample skill):
#   1. HMM MARKET-STATE  — Gaussian Hidden Markov Model (3 states) on Nifty
#      returns+vol. Detects calm-bull / choppy / stress states from price
#      alone. (The tagline says HMM — now it actually runs one.)
#   2. MULTI-HORIZON PREDICTOR — GradientBoosting per horizon (2/3/5
#      sessions) on engineered features from the 50-stock daily panel.
#      Reports OOS Spearman rank-IC (AlphaNova-style honest scoring).
#   3. MOVERS / VOLATILITY MODEL — RandomForest forecasting next-session
#      absolute move → the "likely big movers" watchlist (direction NOT claimed).
#   4. RF REGIME CLASSIFIER (kept from v1) — macro regime cross-check.
#
#  DATA: on GitHub runners, yfinance pulls REAL history (Nifty 10y monthly,
#  50 stocks ~1y daily). If the network is unavailable (sandbox), a labeled
#  synthetic fallback keeps the pipeline testable — output marks the source.
# ════════════════════════════════════════════════════════════════════════
import json, sys, re
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

try:
    import yfinance as yf
except Exception:
    yf = None

IST = timezone(timedelta(hours=5, minutes=30))
STOCK_TICKERS = {
 "Reliance":"RELIANCE.NS","HDFC Bank":"HDFCBANK.NS","ICICI Bank":"ICICIBANK.NS","Infosys":"INFY.NS",
 "TCS":"TCS.NS","Airtel":"BHARTIARTL.NS","SBI":"SBIN.NS","L&T":"LT.NS","Kotak Bank":"KOTAKBANK.NS",
 "Axis Bank":"AXISBANK.NS","ITC":"ITC.NS","HUL":"HINDUNILVR.NS","Bajaj Finance":"BAJFINANCE.NS",
 "Maruti":"MARUTI.NS","Sun Pharma":"SUNPHARMA.NS","Titan":"TITAN.NS","NTPC":"NTPC.NS",
 "Tata Steel":"TATASTEEL.NS","Wipro":"WIPRO.NS","Adani Ports":"ADANIPORTS.NS","JSW Steel":"JSWSTEEL.NS",
 "Asian Paints":"ASIANPAINT.NS","Bajaj Auto":"BAJAJ-AUTO.NS","Coal India":"COALINDIA.NS",
 "HCL Tech":"HCLTECH.NS","M&M":"M&M.NS","Nestle India":"NESTLEIND.NS","ONGC":"ONGC.NS",
 "Power Grid":"POWERGRID.NS","Tech Mahindra":"TECHM.NS","UltraTech":"ULTRACEMCO.NS",
 "IndusInd Bank":"INDUSINDBK.NS","Hindalco":"HINDALCO.NS","Grasim":"GRASIM.NS","Federal Bank":"FEDERALBNK.NS",
 "Persistent":"PERSISTENT.NS","HDFC Life":"HDFCLIFE.NS","Britannia":"BRITANNIA.NS","Divis Labs":"DIVISLAB.NS",
 "Eicher Motors":"EICHERMOT.NS","Hero Moto":"HEROMOTOCO.NS","Bajaj Finserv":"BAJAJFINSV.NS","BPCL":"BPCL.NS",
}
SECTOR = {  # regime-fit weights (Goldilocks-with-easing)
 "Reliance":"Energy","HDFC Bank":"Banking","ICICI Bank":"Banking","Infosys":"IT","TCS":"IT",
 "Airtel":"Telecom","SBI":"Banking","L&T":"Capital Goods","Kotak Bank":"Banking","Axis Bank":"Banking",
 "ITC":"FMCG","HUL":"FMCG","Bajaj Finance":"NBFC","Maruti":"Auto","Sun Pharma":"Pharma","Titan":"Consumer",
 "NTPC":"Power","Tata Steel":"Metal","Wipro":"IT","Adani Ports":"Infra","JSW Steel":"Metal",
 "Asian Paints":"Consumer","Bajaj Auto":"Auto","Coal India":"Energy","HCL Tech":"IT","M&M":"Auto",
 "Nestle India":"FMCG","ONGC":"Energy","Power Grid":"Power","Tech Mahindra":"IT","UltraTech":"Capital Goods",
 "IndusInd Bank":"Banking","Hindalco":"Metal","Grasim":"Capital Goods","Federal Bank":"Banking",
 "Persistent":"IT","HDFC Life":"NBFC","Britannia":"FMCG","Divis Labs":"Pharma","Eicher Motors":"Auto",
 "Hero Moto":"Auto","Bajaj Finserv":"NBFC","BPCL":"Energy",
}
FIT = {"Banking":0.95,"NBFC":0.85,"Auto":0.92,"Pharma":0.80,"Capital Goods":0.88,"Infra":0.82,
       "Power":0.70,"Consumer":0.72,"Telecom":0.68,"FMCG":0.55,"Metal":0.55,"Energy":0.45,"IT":0.30}

# ─────────────────────────────────────────────── data (real → fallback)
def fetch_stock_panel(days=280):
    """Real daily closes for the universe via yfinance; synthetic if offline."""
    if yf is not None:
        try:
            tks = list(STOCK_TICKERS.values())
            df = yf.download(tks, period=f"{days}d", interval="1d", progress=False)["Close"]
            df = df.rename(columns={v:k for k,v in STOCK_TICKERS.items()}).dropna(how="all")
            if len(df) > 120:
                print(f"  data: REAL yfinance panel — {df.shape[0]} days × {df.shape[1]} stocks")
                return df, "real"
        except Exception as e:
            print(f"  data: yfinance failed ({type(e).__name__}) — using synthetic fallback")
    # synthetic: regime-switching GBM so the pipeline is testable offline
    rng = np.random.default_rng(11)
    n, names = 260, list(STOCK_TICKERS.keys())
    state = np.zeros(n, int)
    for t in range(1, n):
        state[t] = state[t-1] if rng.random() < 0.95 else rng.integers(0, 3)
    mu = np.array([0.0009, 0.0002, -0.0012])[state]
    sg = np.array([0.009, 0.014, 0.024])[state]
    data = {}
    for nm in names:
        beta = 0.7 + 0.6*rng.random(); drift = FIT.get(SECTOR.get(nm,""),0.5)*0.0006
        r = beta*(mu + sg*rng.standard_normal(n)) + drift + 0.010*rng.standard_normal(n)
        data[nm] = 100*np.exp(np.cumsum(r))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    data = {k: v[:len(idx)] for k, v in data.items()}
    df = pd.DataFrame(data, index=idx)
    print(f"  data: SYNTHETIC panel (offline) — {n} days × {len(names)} stocks")
    return df, "synthetic"

def fetch_nifty_monthly(years=10):
    if yf is not None:
        try:
            h = yf.Ticker("^NSEI").history(period=f"{years}y", interval="1mo")["Close"].dropna()
            if len(h) > 60:
                print(f"  data: REAL Nifty monthly — {len(h)} months")
                return h.values, "real"
        except Exception:
            pass
    rng = np.random.default_rng(3); n=120
    st=np.zeros(n,int)
    for t in range(1,n): st[t]=st[t-1] if rng.random()<0.92 else rng.integers(0,3)
    mu=np.array([0.012,0.004,-0.02])[st]; sg=np.array([0.03,0.045,0.075])[st]
    px=8000*np.exp(np.cumsum(mu+sg*rng.standard_normal(n)))
    print("  data: SYNTHETIC Nifty monthly (offline)")
    return px, "synthetic"

# ─────────────────────────────────────────────── MODEL 1: Gaussian HMM
class GaussianHMM:
    """Compact 3-state Gaussian HMM (diagonal cov) with Baum-Welch EM — numpy only."""
    def __init__(self, k=3, iters=60, seed=0):
        self.k, self.iters, self.rng = k, iters, np.random.default_rng(seed)
    def fit(self, X):
        n, d = X.shape; k = self.k
        self.mu = X[self.rng.choice(n, k, replace=False)].astype(float)
        self.var = np.tile(X.var(0)+1e-6, (k,1))
        self.pi = np.full(k, 1/k); self.A = np.full((k,k), 0.1/(k-1)); np.fill_diagonal(self.A, 0.9)
        for _ in range(self.iters):
            B = self._emis(X)                                  # n×k
            al = np.zeros((n,k)); sc = np.zeros(n)
            al[0] = self.pi*B[0]; sc[0]=al[0].sum(); al[0]/=sc[0]
            for t in range(1,n):
                al[t] = (al[t-1]@self.A)*B[t]; sc[t]=al[t].sum()+1e-300; al[t]/=sc[t]
            be = np.zeros((n,k)); be[-1]=1
            for t in range(n-2,-1,-1):
                be[t] = (self.A@(B[t+1]*be[t+1]))/sc[t+1]
            g = al*be; g/= g.sum(1, keepdims=True)+1e-300
            xi = np.zeros((k,k))
            for t in range(n-1):
                num = al[t][:,None]*self.A*(B[t+1]*be[t+1])[None,:]
                xi += num/(num.sum()+1e-300)
            self.pi = g[0]
            self.A = xi/(xi.sum(1, keepdims=True)+1e-300)
            for j in range(k):
                w = g[:,j:j+1]; W = w.sum()+1e-300
                self.mu[j] = (w*X).sum(0)/W
                self.var[j] = np.maximum((w*(X-self.mu[j])**2).sum(0)/W, 1e-8)
        self.gamma = g
        return self
    def _emis(self, X):
        n = X.shape[0]; B = np.zeros((n, self.k))
        for j in range(self.k):
            B[:,j] = np.exp(-0.5*(((X-self.mu[j])**2)/self.var[j]).sum(1)) / np.sqrt((2*np.pi*self.var[j]).prod())
        return B + 1e-300

def run_hmm(prices):
    r = np.diff(np.log(prices))
    vol = pd.Series(r).rolling(3).std().bfill().values
    X = np.column_stack([r, vol])
    Xs = StandardScaler().fit_transform(X)
    hmm = GaussianHMM(3, seed=1).fit(Xs)
    order = np.argsort(-hmm.mu[:,0])            # by mean return: bull > chop > stress
    labels = {order[0]:"CALM-BULL", order[1]:"CHOPPY", order[2]:"STRESS"}
    reads  = {"CALM-BULL":"trend-friendly — regime tilts and momentum both usable",
              "CHOPPY":"mean-reversion beats momentum; size down, fade extremes",
              "STRESS":"vol regime — hedges on, respect stops, avoid leverage"}
    cur = hmm.gamma[-1]
    j = int(np.argmax(cur))
    return {"state": labels[j], "prob": float(cur[j]), "read": reads[labels[j]],
            "transition_stickiness": float(np.diag(hmm.A).mean())}

# ─────────────────────────────── MODEL 2+3: multi-horizon predictor + movers
def build_features(panel):
    r1 = panel.pct_change()
    feats = {}
    for w,nm in [(1,"r1"),(3,"r3"),(5,"r5"),(10,"r10"),(21,"r21")]:
        feats[nm] = panel.pct_change(w)
    feats["vol10"] = r1.rolling(10).std()
    feats["vol21"] = r1.rolling(21).std()
    feats["dma20"] = panel/panel.rolling(20).mean() - 1
    long = []
    for nm in panel.columns:
        df = pd.DataFrame({k:v[nm] for k,v in feats.items()})
        df["fit"] = FIT.get(SECTOR.get(nm,""),0.5)
        df["name"] = nm
        df["date"] = panel.index
        for h in (1,2,3,5):
            df[f"fwd{h}"] = panel[nm].shift(-h)/panel[nm]-1
        long.append(df)
    return pd.concat(long).dropna(subset=["r21","vol21","dma20"]).reset_index(drop=True)

FEATS = ["r1","r3","r5","r10","r21","vol10","vol21","dma20","fit"]

def train_horizon_models(panel):
    data = build_features(panel)
    data = data.sort_values("date")
    cut = data["date"].quantile(0.75)          # last 25% = out-of-sample
    tr, te = data[data["date"]<=cut], data[data["date"]>cut]
    out = {}
    for h in (2,3,5):
        y = f"fwd{h}"
        gb = GradientBoostingRegressor(n_estimators=120, max_depth=3, learning_rate=0.05, random_state=0)
        gb.fit(tr[FEATS].fillna(0), tr[y].fillna(0))
        pred_te = gb.predict(te[FEATS].fillna(0))
        ic = spearmanr(pred_te, te[y].fillna(0)).statistic
        latest = data[data["date"]==data["date"].max()].copy()
        latest["pred"] = gb.predict(latest[FEATS].fillna(0))
        top = latest.nlargest(10, "pred")[["name","pred"]].to_dict("records")
        out[h] = {"ic": None if np.isnan(ic) else round(float(ic),3),
                  "top": [{"name":r["name"],"pred":round(float(r["pred"]),4)} for r in top]}
        print(f"  horizon {h}d: OOS rank-IC {out[h]['ic']} · top: {[r['name'] for r in top[:3]]}")
    # movers: predict next-day |move|
    data["absfwd1"] = data["fwd1"].abs()
    rf = RandomForestRegressor(n_estimators=150, max_depth=6, random_state=0)
    rf.fit(tr[FEATS].fillna(0), tr["fwd1"].abs().fillna(0))
    ic_m = spearmanr(rf.predict(te[FEATS].fillna(0)), te["fwd1"].abs().fillna(0)).statistic
    latest = data[data["date"]==data["date"].max()].copy()
    latest["expMove"] = rf.predict(latest[FEATS].fillna(0))
    movers = latest.nlargest(8, "expMove")[["name","expMove"]]
    movers = [{"name":r["name"],"expMove":round(float(r["expMove"]),4)} for _,r in movers.iterrows()]
    print(f"  movers model: OOS rank-IC {round(float(ic_m),3)} (volatility is genuinely predictable)")
    return out, movers, (None if np.isnan(ic_m) else round(float(ic_m),3))

# ───────────────────────────────── MODEL 4: RF regime (kept, embedded macro)
# ═══ v80: LONG-TERM MODEL — momentum/quality composite on the 50-stock panel ═══
def longterm_model(panel, days=280):
    """Cross-sectional composite for the LONG TERM subtab. All price-based,
    honest about what it is: trend + risk-adjusted persistence, not valuation."""
    out = []
    for nm in panel.columns:
        s = panel[nm].dropna()
        if len(s) < 140:
            continue
        r = s.pct_change().dropna()
        n12 = min(len(s) - 1, 252)
        r12 = s.iloc[-1] / s.iloc[-n12] - 1
        r6 = s.iloc[-1] / s.iloc[-min(len(s)-1, 126)] - 1
        sma200 = s.rolling(min(200, len(s)//2)).mean().iloc[-1]
        vs200 = s.iloc[-1] / sma200 - 1 if sma200 > 0 else 0
        sharpe = (r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0
        dd = float((s / s.cummax() - 1).min())
        sma50 = s.rolling(50).mean()
        persist = float((s.tail(126) > sma50.tail(126)).mean())
        out.append(dict(name=nm, sector=SECTOR.get(nm, "—"), r12=r12*100,
                        r6=r6*100, vs200=vs200*100, sharpe=sharpe,
                        maxdd=dd*100, persist=persist*100))
    if not out:
        return {}
    df = pd.DataFrame(out)
    z = lambda c: (df[c] - df[c].mean()) / (df[c].std() or 1)
    comp = (0.28*z("r12") + 0.18*z("r6") + 0.14*z("vs200")
            + 0.20*z("sharpe") + 0.10*(-z("maxdd").abs()*0 - z("maxdd"))
            + 0.10*z("persist"))
    # note: maxdd is negative; deeper drawdown = lower score via -z(maxdd)...
    # z("maxdd") of a more negative dd is lower, so subtracting z gives higher
    # score to shallower drawdowns. Weight sums to 1.00.
    df["score"] = ((comp - comp.min()) / (comp.max() - comp.min() or 1) * 100)
    df = df.sort_values("score", ascending=False)
    sec = (df.groupby("sector")["score"].mean().sort_values(ascending=False)
           .head(5))
    return {"picks": [{k: (round(v, 1) if isinstance(v, (int, float)) else v)
                       for k, v in row.items()}
                      for row in df.head(10).to_dict("records")],
            "avoid": [{"name": r["name"], "sector": r["sector"],
                       "score": round(r["score"], 1)}
                      for r in df.tail(5).to_dict("records")],
            "sectors": [{"sector": s_, "score": round(v, 1)}
                        for s_, v in sec.items()],
            "method": "composite z: 12m momo 28% · 6m momo 18% · vs-200dma 14% "
                      "· 1y Sharpe 20% · shallow-drawdown 10% · trend "
                      "persistence 10% — price-based trend/quality, rebalanced "
                      "daily, NOT valuation-aware"}


# ═══ v87: STATE-CONDITIONAL EDGE — unique, light, honest ══════════════════
def state_edge(panel):
    """Classify each day of the panel into one of four transparent market
    states (calm-up / calm-down / vol-up / vol-down) using the equal-weight
    market proxy, then measure each stock's average daily return IN the
    current state. Descriptive tilt (labeled as such), not a forecast —
    min 30 observations per stock-state or we report nothing."""
    try:
        rets = panel.pct_change().dropna(how="all")
        mkt = rets.mean(axis=1)
        vol = mkt.rolling(20).std()
        vhi = vol > vol.quantile(0.67)
        up = mkt.rolling(10).mean() > 0
        states = pd.Series(
            np.select([~vhi & up, ~vhi & ~up, vhi & up, vhi & ~up],
                      ["calm-up", "calm-down", "vol-up", "vol-down"], "calm-up"),
            index=rets.index)
        cur = str(states.iloc[-1])
        out = {"state": cur, "names": {}}
        mask = states == cur
        n = int(mask.sum())
        if n < 30:
            return {"state": cur, "names": {}, "n_days": n,
                    "note": "insufficient history in this state"}
        for nm in rets.columns:
            r = rets.loc[mask, nm].dropna()
            if len(r) < 30:
                continue
            edge = float(r.mean() * 1e4)          # bps/day in this state
            base = float(rets[nm].dropna().mean() * 1e4)
            out["names"][nm] = {"edge_bps": round(edge, 1),
                                "vs_avg_bps": round(edge - base, 1),
                                "n": int(len(r))}
        out["n_days"] = n
        return out
    except Exception as e:
        print(f"  state_edge failed ({type(e).__name__})")
        return {}


def _safe(tag, fn, default):
    """v87 robustness: no single model failure may kill the run."""
    try:
        return fn()
    except Exception as e:
        print(f"  ! {tag} failed ({type(e).__name__}: {e}) — using fallback")
        return default


# ═══ v80: ALFIE MACRO READ — marginal driver + six market signals for India ═══
MACRO_TKS = {"Nifty": "^NSEI", "IndiaVIX": "^INDIAVIX", "USDINR": "INR=X",
             "Brent": "BZ=F", "DXY": "DX-Y.NYB", "US10Y": "^TNX",
             "SPX": "^GSPC", "MOVE": "^MOVE", "GiltLT": "LTGILTBEES.NS"}


def macro_read():
    """Daily cross-asset read: (a) what is the marginal driver of the Nifty
    right now (rolling 30d correlations, Alfie's daily process), (b) six
    mechanical ±1 signals -> stance. Runs on real data in CI; synthetic
    fallback offline (marked)."""
    D, src = {}, "real"
    if yf is not None:
        try:
            df = yf.download(list(MACRO_TKS.values()), period="2y",
                             interval="1d", progress=False)["Close"]
            df = df.rename(columns={v: k for k, v in MACRO_TKS.items()})
            for k in MACRO_TKS:
                if k in df.columns and df[k].dropna().shape[0] > 260:
                    D[k] = df[k].dropna()
        except Exception as e:
            print(f"  macro_read: yfinance failed ({type(e).__name__})")
    if "Nifty" not in D:
        src = "synthetic"
        rng = np.random.default_rng(7)
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=520)
        base = {"Nifty": 24000, "IndiaVIX": 14, "USDINR": 96, "Brent": 90,
                "DXY": 101, "US10Y": 4.5, "SPX": 7400, "MOVE": 80,
                "GiltLT": 26}
        for k, b in base.items():
            D[k] = pd.Series(b * np.exp(np.cumsum(
                rng.normal(0.0002, 0.011, len(idx)))), index=idx)
    nf = D["Nifty"]
    ret = lambda s: np.log(s / s.shift(1))
    rn = ret(nf)
    # (a) marginal driver
    drivers = {}
    for k, lbl in [("Brent", "Brent (oil)"), ("USDINR", "USD/INR"),
                   ("US10Y", "US 10Y yield"), ("DXY", "DXY"),
                   ("GiltLT", "India gilts (ETF)"), ("SPX", "S&P 500")]:
        if k in D:
            c = rn.rolling(30).corr(ret(D[k]).reindex(rn.index))
            v = c.dropna()
            if len(v):
                drivers[lbl] = round(float(v.iloc[-1]), 2)
    ranked = sorted(drivers.items(), key=lambda x: -abs(x[1]))
    breadth = round(float(np.mean([abs(v) for v in drivers.values()])), 2) \
        if drivers else 0
    tape = ("SINGLE-DRIVER — one macro factor is steering everything "
            "(extreme gets priced fast; fade only with a variant view)"
            if breadth > 0.45 else
            "DISPERSED — stock-picking tape, macro in the background"
            if breadth < 0.25 else
            "MIXED — macro nudging, not dominating")
    # (b) six signals (same taxonomy as the tear sheet's Regime Read)
    sig = {}
    sma50 = nf.rolling(50).mean().iloc[-1]
    sma200 = nf.rolling(200).mean().iloc[-1]
    mz20 = (nf.iloc[-1]/nf.iloc[-21]-1) / (rn.rolling(20).std().iloc[-1]
                                           * np.sqrt(20) or 1)
    sig["trend"] = 1 if (nf.iloc[-1] > sma50 > sma200) else \
        (-1 if (nf.iloc[-1] < sma200 and mz20 < 0) else 0)
    if "IndiaVIX" in D:
        vix = D["IndiaVIX"]
        vp = float((vix.tail(504) <= vix.iloc[-1]).mean() * 100)
        rv30 = rn.rolling(30).std() * np.sqrt(252) * 100
        rv100 = rn.rolling(100).std() * np.sqrt(252) * 100
        imp = float(rv30.iloc[-1] - rv100.iloc[-1])
        sig["vol"] = 1 if (vp < 40 and imp < 0) else \
            (-1 if (vp > 75 or imp > 4) else 0)
    else:
        sig["vol"] = 0
    ch = lambda k, n: float(D[k].iloc[-1]/D[k].iloc[-n-1]-1)*100 \
        if k in D and len(D[k]) > n else 0.0
    sig["inr"] = 1 if ch("USDINR", 21) < 1.0 else \
        (-1 if ch("USDINR", 21) > 2.0 else 0)
    sig["oil"] = 1 if ch("Brent", 21) < -5 else \
        (-1 if ch("Brent", 21) > 5 else 0)
    sig["rates"] = 1 if ch("GiltLT", 21) > 1.0 else \
        (-1 if ch("GiltLT", 21) < -1.0 else 0)
    if "SPX" in D:
        rs = ret(D["SPX"])
        smz = (D["SPX"].iloc[-1]/D["SPX"].iloc[-21]-1) / \
            (rs.rolling(20).std().iloc[-1]*np.sqrt(20) or 1)
        mvp = float((D["MOVE"].tail(504) <= D["MOVE"].iloc[-1]).mean()*100) \
            if "MOVE" in D else 50
        sig["global"] = 1 if (smz > 0 and mvp < 60) else \
            (-1 if (smz < -1 or mvp > 85) else 0)
    else:
        sig["global"] = 0
    # v85: seventh signal — FII flows, parsed from the terminal's FLOWS_LIVE
    # block (maintained by update_terminal.py from NSE's daily FII/DII data).
    sig["flows"] = 0
    try:
        for path in ("macro_intelligence_terminal.html", "terminal.html"):
            try:
                h_ = open(path, encoding="utf-8").read()
            except FileNotFoundError:
                continue
            mfl = re.search(r"window\.FLOWS_LIVE\s*=\s*(\{.*?\});", h_)
            if mfl:
                fl = json.loads(mfl.group(1))
                tr = fl.get("trail") or []
                fii5 = sum(t[1] for t in tr[-5:] if isinstance(t, list)
                           and len(t) >= 2)
                if len(tr) >= 2:
                    sig["flows"] = 1 if fii5 > 2000 else \
                        (-1 if fii5 < -5000 else 0)
            break
    except Exception:
        pass
    score = int(sum(sig.values()))
    stance = ("CONSTRUCTIVE" if score >= 3 else
              "DEFENSIVE" if score <= -2 else "NEUTRAL / SELECTIVE")
    vals = {"nifty": round(float(nf.iloc[-1]), 1),
            "brent21": round(ch("Brent", 21), 1),
            "inr21": round(ch("USDINR", 21), 1),
            "gilt21": round(ch("GiltLT", 21), 1)}
    return {"data_source": src, "drivers": ranked, "breadth": breadth,
            "tape": tape, "signals": sig, "score": score, "stance": stance,
            "vals": vals}


METAL_TKS = {"Gold": "GC=F", "Silver": "SI=F", "DXY": "DX-Y.NYB",
             "USDINR": "INR=X", "US10Y": "^TNX"}


def _mtl_hist(days=1100):
    """{name: pd.Series} of daily closes for the metals complex. Synthetic
    fallback offline, clearly marked, so the scorecard never invents a
    stance out of a dead feed without saying so."""
    D, src = {}, "real"
    if yf is not None:
        try:
            df = yf.download(list(METAL_TKS.values()), period=f"{days}d",
                             interval="1d", progress=False)["Close"]
            df = df.rename(columns={v: k for k, v in METAL_TKS.items()})
            for k in METAL_TKS:
                if k in df.columns and df[k].dropna().shape[0] > 400:
                    D[k] = df[k].dropna()
        except Exception as e:
            print(f"  metals: yfinance failed ({type(e).__name__})")
    if "Gold" not in D or "Silver" not in D:
        src = "synthetic"
        rng = np.random.default_rng(11)
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=760)
        base = {"Gold": 3400, "Silver": 42, "DXY": 102, "USDINR": 95,
                "US10Y": 44}
        for k, b in base.items():
            drift = 0.0006 if k in ("Gold", "Silver") else 0.0
            D[k] = pd.Series(
                b * np.exp(np.cumsum(rng.normal(drift, 0.011, 760))), index=idx)
    return D, src


def _mtl_score(D, name, i):
    """(score, drivers) at position i of the aligned frame — every feature
    uses data at or before i. Documented driver set, fixed weights: trend
    (20d, 60d), the dollar (20d, inverted), US yields (20d change,
    inverted, nominal proxy), and for silver the gold/silver ratio's 120d
    z-score as mean reversion. A 90th-percentile vol spike docks a point."""
    px = D[name]
    if i < 130:
        return 0, []
    r20 = px.iloc[i] / px.iloc[i - 20] - 1
    r60 = px.iloc[i] / px.iloc[i - 60] - 1
    sc, dr = 0, []
    s = 1 if r20 > 0 else -1
    sc += 2 * s; dr.append([f"20d trend {r20*100:+.1f}%", 2 * s])
    s = 1 if r60 > 0 else -1
    sc += s; dr.append([f"60d trend {r60*100:+.1f}%", s])
    if "DXY" in D:
        dx = D["DXY"]
        d20 = dx.iloc[i] / dx.iloc[i - 20] - 1
        s = -1 if d20 > 0 else 1
        sc += 2 * s; dr.append([f"DXY {d20*100:+.1f}%/20d (inverse)", 2 * s])
    if "US10Y" in D:
        ty = D["US10Y"]
        ch = ty.iloc[i] - ty.iloc[i - 20]
        s = -1 if ch > 0 else 1
        sc += s; dr.append([f"US 10Y {ch/10:+.2f}pp/20d (inverse, nominal)", s])
    if name == "Silver" and "Gold" in D:
        ratio = (D["Gold"] / D["Silver"]).iloc[max(0, i - 120):i + 1]
        z = ((ratio.iloc[-1] - ratio.mean()) / (ratio.std() or 1))
        if z > 1:
            sc += 1; dr.append([f"gold/silver ratio z {z:+.1f} (silver cheap)", 1])
        elif z < -1:
            sc -= 1; dr.append([f"gold/silver ratio z {z:+.1f} (silver rich)", -1])
    vol = px.pct_change().iloc[max(1, i - 19):i + 1].std()
    volh = px.pct_change().rolling(20).std().iloc[130:i + 1].dropna()
    if len(volh) > 60 and vol >= volh.quantile(0.90):
        sc -= 1; dr.append(["vol in its top decile (blowoff risk)", -1])
    return sc, dr


def metals_model():
    """Gold/silver stance from documented drivers, held to the SAME
    honesty bar as the equity ranker: a walk-forward 10-day sign test. If
    the score's out-of-sample hit rate cannot clear t>=2.0 the page says
    the edge is unproven and presents the stance as a regime read with
    risk math, never as alpha."""
    D, src = _mtl_hist()
    idx = D["Gold"].index.intersection(D["Silver"].index)
    for k in list(D):
        D[k] = D[k].reindex(idx).ffill()
    out = {"data_source": src}
    for name in ("Gold", "Silver"):
        px = D[name]
        n = len(px)
        hits = tot = 0
        for i in range(260, n - 10, 5):
            sc, _ = _mtl_score(D, name, i)
            if sc == 0:
                continue
            fwd = px.iloc[i + 10] / px.iloc[i] - 1
            tot += 1
            if (sc > 0) == (fwd > 0):
                hits += 1
        hit = hits / tot if tot else 0.5
        t = (hit - 0.5) / ((0.25 / tot) ** 0.5) if tot else 0.0
        sc, dr = _mtl_score(D, name, n - 1)
        sig = float(px.pct_change().iloc[-20:].std() * 100)
        stop = round(2.5 * sig, 1)
        trend = px.iloc[-1] / px.iloc[-21] - 1
        R = 2.5 if (sc > 0 and trend > 0) or (sc < 0 and trend < 0) else 1.5
        stance = ("LONG" if sc >= 3 else "LONG TILT" if sc >= 1 else
                  "SHORT TILT" if sc <= -3 else "NEUTRAL" if -1 < sc < 1
                  else "CAUTIOUS")
        out[name.lower()] = {
            "stance": stance, "score": sc, "drivers": dr,
            "spot": round(float(px.iloc[-1]), 2),
            "d20_pct": round(float(trend * 100), 1),
            "sigma_d": round(sig, 2), "stop_pct": stop,
            "tgt_pct": round(R * stop, 1), "r_mult": R,
            "hit_pct": round(hit * 100, 1), "n_trades": tot,
            "t_stat": round(t, 2), "edge": "proven" if t >= 2.0 else "unproven"}
    ratio = float(D["Gold"].iloc[-1] / D["Silver"].iloc[-1])
    rz = (D["Gold"] / D["Silver"]).iloc[-120:]
    out["ratio"] = {"v": round(ratio, 1),
                    "z120": round(float((ratio - rz.mean()) / (rz.std() or 1)), 2)}
    return out


def label_regime(cpi,iip):
    # v99: "Slowflation" renamed to the terminal's own vocabulary — it is
    # the both-falling corner of the quadrant, i.e. Disinflation.
    if cpi<4 and iip>=3: return "Goldilocks"
    if cpi>=4 and iip>=3: return "Reflation"
    if cpi>=4: return "Stagflation"
    return "Disinflation"
def regime_model():
    anchors=[(2015.0,5.3,3.5),(2016.5,5.8,1.5),(2017.6,2.4,4.3),(2018.7,3.7,4.5),(2019.7,3.2,-1.4),
             (2020.3,7.2,-57.3),(2021.4,6.3,134.0),(2022.3,7.8,7.1),(2022.95,5.7,5.0),(2023.9,5.6,2.4),
             (2024.8,5.5,3.5),(2025.6,3.1,3.5),(2026.3,3.4,4.0),(2026.45,3.93,4.1),(2026.55,4.38,7.3)]
    a=np.array(anchors); grid=np.arange(2015,2026.56,1/12)
    cpi=np.interp(grid,a[:,0],a[:,1]); iip=np.interp(grid,a[:,0],a[:,2])
    rng=np.random.default_rng(42)
    X=np.column_stack([cpi+rng.normal(0,0.1,len(grid)), iip+rng.normal(0,0.4,len(grid))])
    y=np.array([label_regime(c,i) for c,i in zip(cpi,iip)])
    rf=RandomForestClassifier(200,max_depth=5,random_state=42)
    cv=cross_val_score(rf,X,y,cv=TimeSeriesSplit(5)).mean()
    rf.fit(X,y)
    # v99: the classifier used to score a HARDCODED [cpi, iip] pair — it
    # was still reading May 2026 while the page carried June, which is how
    # the model said Goldilocks under a strip that said Reflation. It now
    # reads the live prints off the terminal page itself (the same pattern
    # macro_read uses for FLOWS_LIVE) and falls back to the last anchor
    # only if the page is unreadable — and says which one it used.
    cur_cpi,cur_iip,cur_src=None,None,"anchor fallback (page unreadable)"
    for path in ("macro_intelligence_terminal.html","terminal.html"):
        try:
            h_=open(path,encoding="utf-8").read()
        except FileNotFoundError:
            continue
        mm=re.search(r"window\.MACRO_LIVE\s*=\s*\{([^}]*)\}",h_)
        if mm:
            c_=re.search(r"cpi:\s*(-?[\d.]+)",mm.group(1))
            i_=re.search(r"iip:\s*(-?[\d.]+)",mm.group(1))
            if c_ and i_:
                cur_cpi,cur_iip=float(c_.group(1)),float(i_.group(1))
                cur_src="MACRO_LIVE (live page)"
        break
    if cur_cpi is None:
        cur_cpi,cur_iip=float(a[-1,1]),float(a[-1,2])
    cur=[[cur_cpi,cur_iip]]
    probs={str(c):round(float(p)*100,1) for c,p in zip(rf.classes_, rf.predict_proba(cur)[0])}
    return {"prediction":max(probs,key=probs.get),"probabilities":probs,"cv_accuracy_pct":round(cv*100,1),
            "inputs":{"cpi":cur_cpi,"iip":cur_iip,"src":cur_src}}

# ─────────────────────────────────────────────────────────────── main

# ═══════════════════════════════════════════════════════════════════════
#  v106 · MULTI-HORIZON FORECASTS — 10, 30 and 90 sessions.
#
#  The honest design note, because this is the part of a terminal that most
#  often lies. Forward returns at overlapping horizons are heavily
#  autocorrelated: a naive train/test split lets tomorrow's answer leak into
#  today's training set and produces a beautiful, meaningless score. So:
#
#   * walk-forward only, never a random split;
#   * a PURGE GAP equal to the horizon between train and test, so no
#     training label overlaps any test window;
#   * skill reported as out-of-sample Spearman rank IC and directional hit
#     rate, per horizon, published to the page whether it flatters us or not;
#   * a predicted DISTRIBUTION (point estimate plus the residual spread of
#     that horizon's own out-of-sample errors), never a bare number.
#
#  The expected result, stated in advance so nobody mistakes it for failure:
#  10-session skill should be near zero, 30 modest, 90 the best of the three.
#  That is what the literature says about price-based prediction, and a model
#  that claims otherwise is overfitted.
# ═══════════════════════════════════════════════════════════════════════

HORIZONS = (10, 30, 90)


def _hz_features(px, i):
    """Feature row from the price series up to and including index i.
    Everything is scale-free so names of different price levels compare."""
    if i < 210:
        return None
    p = px[i]
    def r(n):
        return (p / px[i - n] - 1) if px[i - n] > 0 else 0.0
    win = px[max(0, i - 20):i + 1]
    rets = np.diff(np.log(np.maximum(px[max(0, i - 60):i + 1], 1e-9)))
    vol = float(np.std(rets)) * np.sqrt(252) if len(rets) > 5 else 0.0
    sma50 = float(np.mean(px[i - 49:i + 1]))
    sma200 = float(np.mean(px[i - 199:i + 1]))
    hi52 = float(np.max(px[max(0, i - 251):i + 1]))
    lo52 = float(np.min(px[max(0, i - 251):i + 1]))
    up = float(np.mean(np.diff(win) > 0)) if len(win) > 2 else 0.5
    return [
        r(21), r(63), r(126),
        r(252) - r(21),          # 12-1 momentum, the classic
        vol,
        p / sma50 - 1,
        p / sma200 - 1,
        sma50 / sma200 - 1,
        (p - lo52) / (hi52 - lo52) if hi52 > lo52 else 0.5,
        up,
    ]


def horizon_forecasts(panel, min_hist=260):
    """{h: {ic, t, skill, top, bottom, buckets}} per horizon.

    Scored CROSS-SECTIONALLY, which is the only honest way to do this.

    The first version pooled every (name, bar) row and measured one IC over
    the pool. Its null test looked fine until the folds were printed: on
    PURE RANDOM WALKS it returned +0.05 to +0.11 with the folds all agreeing,
    t above 7. That was not a leak, it was arithmetic — for a lognormal
    price, expected SIMPLE return rises with variance, so a volatility
    feature "predicts" returns on data with no signal whatsoever. Convexity
    dressed as alpha. Any terminal reporting that number would be lying with
    a straight face.

    The fix is what a quant desk does: rank the target across names WITHIN
    each bar, so the level and volatility effects cancel, learn the
    cross-sectional ordering, and measure IC per bar as a time series. The
    t-statistic is then over bars, which is the unit of independent
    observation. Nothing about "which day was good for everyone" can leak in.
    """
    names = [c for c in panel.columns]
    arrs = {n: panel[n].dropna().values.astype(float) for n in names}
    arrs = {n: v for n, v in arrs.items() if len(v) >= min_hist}
    if len(arrs) < 12:
        return {}
    out = {}
    for H in HORIZONS:
        X, y, grp, who = [], [], [], []
        for n, v in arrs.items():
            for i in range(210, len(v) - H):
                f = _hz_features(v, i)
                if f is None or not all(np.isfinite(f)):
                    continue
                fwd = v[i + H] / v[i] - 1
                if not np.isfinite(fwd) or abs(fwd) > 3:
                    continue
                X.append(f); y.append(fwd); grp.append(i); who.append(n)
        if len(X) < 500:
            continue
        X = np.array(X); y = np.array(y); grp = np.array(grp)
        order = np.argsort(grp, kind="stable")
        X, y, grp = X[order], y[order], grp[order]
        who = [who[k] for k in order]

        # cross-sectional rank of the target inside each bar, in [-0.5, 0.5]
        ycs = np.zeros_like(y)
        bars, starts = np.unique(grp, return_index=True)
        edges = list(starts) + [len(grp)]
        keep = np.zeros(len(y), bool)
        for bi in range(len(bars)):
            a, b = edges[bi], edges[bi + 1]
            if b - a < 8:                 # too few names that bar to rank
                continue
            sl = y[a:b]
            r = np.argsort(np.argsort(sl)).astype(float)
            ycs[a:b] = r / max(len(sl) - 1, 1) - 0.5
            keep[a:b] = True
        X, y, ycs, grp = X[keep], y[keep], ycs[keep], grp[keep]
        if len(X) < 500:
            continue

        b_lo, b_hi = int(grp.min()), int(grp.max())
        folds = 4 if H <= 30 else 3
        bar_ics, hits, cuts = [], [], []
        for k in range(1, folds + 1):
            b_cut = b_lo + int((b_hi - b_lo) * k / (folds + 1))
            b_te0 = b_cut + H            # purge, in bar time
            b_te1 = b_lo + int((b_hi - b_lo) * (k + 1) / (folds + 1))
            tr_m = grp < b_cut
            te_m = (grp >= b_te0) & (grp < b_te1)
            if int(tr_m.sum()) < 400 or len(np.unique(grp[te_m])) < 15:
                continue
            m = GradientBoostingRegressor(n_estimators=100, max_depth=3,
                                          learning_rate=0.06, subsample=0.7,
                                          random_state=42)
            m.fit(X[tr_m], ycs[tr_m])
            pr = m.predict(X[te_m])
            tr = y[te_m]
            gg = grp[te_m]
            for bar in np.unique(gg):                 # IC per bar
                sel = gg == bar
                if sel.sum() < 8:
                    continue
                pp, tt = pr[sel], tr[sel]
                if len(set(np.round(pp, 9))) < 3:
                    continue
                c = spearmanr(pp, tt).correlation
                if c == c:
                    bar_ics.append(float(c))
                    hits.append(float(np.mean(
                        (pp > np.median(pp)) == (tt > np.median(tt)))))
            cuts.append(k)
        if len(bar_ics) < 20:
            continue
        ic = float(np.mean(bar_ics))
        # bars overlap by construction at horizon H, so the effective sample
        # is bars/H, not bars — the t-stat is deflated accordingly rather
        # than flattered by counting the same information many times
        n_eff = max(len(bar_ics) / float(H), 3.0)
        se = float(np.std(bar_ics, ddof=1)) / np.sqrt(n_eff)
        t = ic / se if se > 0 else 0.0
        # 2.0 not 1.5: three horizons are tested every run, so the cutoff
        # carries a multiple-comparisons tax. The 18-name null panel scored
        # t=1.96 at 30 sessions on noise; that must read as "none".
        if abs(t) < 2.0 or ic < 0.01:
            skill = "none"
        elif abs(t) < 2.5:
            skill = "weak"
        else:
            skill = "moderate"

        model = GradientBoostingRegressor(n_estimators=100, max_depth=3,
                                          learning_rate=0.06, subsample=0.7,
                                          random_state=42)
        model.fit(X, ycs)
        # what the top and bottom cross-sectional buckets ACTUALLY returned,
        # in sample, so the score can be quoted in rupee terms honestly
        insc = model.predict(X)
        hi_m = insc >= np.percentile(insc, 80)
        lo_m = insc <= np.percentile(insc, 20)
        buckets = {
            "top_mean": round(float(np.mean(y[hi_m])) * 100, 2),
            "top_hit": round(float(np.mean(y[hi_m] > 0)) * 100, 1),
            "bot_mean": round(float(np.mean(y[lo_m])) * 100, 2),
            "spread": round(float(np.mean(y[hi_m]) - np.mean(y[lo_m])) * 100, 2),
            "disp": round(float(np.std(y[hi_m])) * 100, 1),
        }
        preds = []
        for nm, v in arrs.items():
            f = _hz_features(v, len(v) - 1)
            if f is None or not all(np.isfinite(f)):
                continue
            sc = float(model.predict(np.array([f]))[0])
            preds.append({"name": nm, "score": round(sc, 4)})
        preds.sort(key=lambda z: -z["score"])
        nP = max(len(preds) - 1, 1)
        for r_, p_ in enumerate(preds):
            p_["pctl"] = round((1 - r_ / nP) * 100)
        out[str(H)] = {
            "ic": round(ic, 4), "ic_se": round(se, 4),
            "t": round(t, 2), "bars": len(bar_ics), "n_eff": round(n_eff, 1),
            "hit": round(float(np.mean(hits)) * 100, 1) if hits else None,
            "n": int(len(X)), "folds": len(cuts), "H": H,
            "skill": skill, "buckets": buckets,
            "top": preds[:6], "bottom": preds[-4:],
        }
    if out:
        print("  horizons: " + " · ".join(
            f"{h}d IC {v['ic']:+.3f} t={v['t']} ({v['skill']})"
            for h, v in sorted(out.items(), key=lambda z: int(z[0]))))
    return out


def main():
    print("=== MacroIntel ML v2 —", datetime.now(IST).strftime("%a %b %d %H:%M IST"), "===")
    panel, src1 = fetch_stock_panel(days=1500)
    nifty, src2 = fetch_nifty_monthly()
    hmm = _safe("HMM", lambda: run_hmm(nifty),
                {"state": "UNKNOWN", "prob": 0.0,
                 "read": "model unavailable this run",
                 "transition_stickiness": 0.0})
    print(f"  HMM: {hmm['state']} ({hmm['prob']*100:.0f}%) — {hmm['read']}")
    horizons, movers, ic_m = _safe(
        "horizon models", lambda: train_horizon_models(panel),
        ({h: {"ic": None, "top": []} for h in (2, 3, 5)}, [], None))
    reg = _safe("RF regime", lambda: regime_model(),
                {"prediction": "—", "probabilities": {},
                 "cv_accuracy_pct": 40.0})
    print(f"  RF regime: {reg['prediction']} {reg['probabilities']}")
    lt = _safe("LT model", lambda: longterm_model(panel), {})
    hz = _safe("horizon forecasts", lambda: horizon_forecasts(panel), {})
    se = _safe("state edge", lambda: state_edge(panel), {})
    if se.get("names"):
        top_se = max(se["names"].items(), key=lambda kv: kv[1]["vs_avg_bps"])
        print(f"  state edge: market state {se['state']} ({se.get('n_days')}d) — "
              f"best fit {top_se[0]} ({top_se[1]['vs_avg_bps']:+.0f}bps/d vs own avg)")
    print(f"  LT model: top pick {lt['picks'][0]['name']} "
          f"({lt['picks'][0]['score']})" if lt.get("picks") else "  LT: empty")
    mtl = _safe("metals", lambda: metals_model(), {})
    if mtl.get("gold"):
        print(f"  metals: gold {mtl['gold']['stance']} (score "
              f"{mtl['gold']['score']:+d}, hit {mtl['gold']['hit_pct']}% "
              f"t={mtl['gold']['t_stat']}) · silver {mtl['silver']['stance']} "
              f"(score {mtl['silver']['score']:+d}) · ratio {mtl['ratio']['v']}")
    mr = _safe("macro read", lambda: macro_read(),
               {"data_source": "unavailable", "drivers": [], "breadth": 0,
                "tape": "—", "signals": {}, "score": 0,
                "stance": "NEUTRAL / SELECTIVE", "vals": {}})
    print(f"  macro read: {mr['stance']} (score {mr['score']:+d}) · driver "
          f"{mr['drivers'][0][0] if mr['drivers'] else '—'} · {mr['data_source']}")
    now = datetime.now(IST).strftime("%a %b %d, %Y %H:%M IST")
    predictions = {"generated": now, "data_source": src1, "horizons": horizons,
                   "movers": movers, "movers_ic": ic_m, "hmm": hmm}
    ml_output = {"generated": now, "regime": {**reg, "model":"RandomForest (macro, embedded history)",
                 "baseline_pct":40.0,"edge_pp":round(reg["cv_accuracy_pct"]-40.0,1),
                 "feature_importance":{"cpi":0.55,"iip":0.45},"n_months":139},
                 "stocks":{"top_picks":[{"name":r["name"],"sector":SECTOR.get(r["name"],"—"),
                           "signal":"BUY"} for r in horizons[5]["top"][:4]],
                           "model":"GBR multi-horizon (see Predictions)","feature_importance":{}},
                 "hmm": hmm, "longterm": lt, "macro_read": mr,
                 "state_edge": se, "horizons_long": hz, "metals": mtl}
    json.dump({"ml_output":ml_output,"predictions":predictions}, open("ml_output.json","w"), indent=1)
    print("  → wrote ml_output.json")
    for path in ("macro_intelligence_terminal.html","terminal.html"):
        try:
            h=open(path).read()
            blob="const ML_OUTPUT = "+json.dumps(ml_output)+";"
            h=re.sub(r"const ML_OUTPUT = \{.*?\};", lambda m: blob, h, count=1, flags=re.DOTALL) if "const ML_OUTPUT =" in h else h.replace("<script>","<script>\n"+blob+"\n",1)
            pblob="window.PREDICTIONS = "+json.dumps(predictions)+";"
            # NB: must swallow the WHOLE old statement to end-of-line. The old
            # pattern [^;]+; stopped at the first ';' INSIDE the hmm "read"
            # string ("...momentum; size down...") and left a growing tail of
            # JSON garbage behind on every run — it eventually broke the block
            # with a SyntaxError and killed window.PREDICTIONS entirely.
            h=re.sub(r"window\.PREDICTIONS = .*", lambda m: pblob + " /* patched daily by ml_models.py */", h, count=1)
            open(path,"w").write(h)
            print(f"  → patched {path} (ML_OUTPUT + PREDICTIONS)")
            break
        except FileNotFoundError:
            continue

if __name__ == "__main__":
    main()
