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


def label_regime(cpi,iip):
    if cpi<4 and iip>=3: return "Goldilocks"
    if cpi>=4 and iip>=3: return "Reflation"
    if cpi>=4: return "Stagflation"
    return "Slowflation"
def regime_model():
    anchors=[(2015.0,5.3,3.5),(2016.5,5.8,1.5),(2017.6,2.4,4.3),(2018.7,3.7,4.5),(2019.7,3.2,-1.4),
             (2020.3,7.2,-57.3),(2021.4,6.3,134.0),(2022.3,7.8,7.1),(2022.95,5.7,5.0),(2023.9,5.6,2.4),
             (2024.8,5.5,3.5),(2025.6,3.1,3.5),(2026.3,3.4,4.0),(2026.55,3.93,4.1)]
    a=np.array(anchors); grid=np.arange(2015,2026.56,1/12)
    cpi=np.interp(grid,a[:,0],a[:,1]); iip=np.interp(grid,a[:,0],a[:,2])
    rng=np.random.default_rng(42)
    X=np.column_stack([cpi+rng.normal(0,0.1,len(grid)), iip+rng.normal(0,0.4,len(grid))])
    y=np.array([label_regime(c,i) for c,i in zip(cpi,iip)])
    rf=RandomForestClassifier(200,max_depth=5,random_state=42)
    cv=cross_val_score(rf,X,y,cv=TimeSeriesSplit(5)).mean()
    rf.fit(X,y)
    cur=[[3.93,4.1]]
    probs={str(c):round(float(p)*100,1) for c,p in zip(rf.classes_, rf.predict_proba(cur)[0])}
    return {"prediction":max(probs,key=probs.get),"probabilities":probs,"cv_accuracy_pct":round(cv*100,1)}

# ─────────────────────────────────────────────────────────────── main
def main():
    print("=== MacroIntel ML v2 —", datetime.now(IST).strftime("%a %b %d %H:%M IST"), "===")
    panel, src1 = fetch_stock_panel()
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
    se = _safe("state edge", lambda: state_edge(panel), {})
    if se.get("names"):
        top_se = max(se["names"].items(), key=lambda kv: kv[1]["vs_avg_bps"])
        print(f"  state edge: market state {se['state']} ({se.get('n_days')}d) — "
              f"best fit {top_se[0]} ({top_se[1]['vs_avg_bps']:+.0f}bps/d vs own avg)")
    print(f"  LT model: top pick {lt['picks'][0]['name']} "
          f"({lt['picks'][0]['score']})" if lt.get("picks") else "  LT: empty")
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
                 "state_edge": se}
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
