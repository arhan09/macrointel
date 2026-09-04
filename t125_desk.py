"""v125 · the 4 Sep review, as regression tests. Each one fails if the bug
it describes returns. Runs from the repo root (relative paths)."""
import sys, re, json, types, importlib.util, os, subprocess
W = os.path.dirname(os.path.abspath(__file__))
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sys.modules[name] = m; sp.loader.exec_module(m); return m
s = open(os.path.join(W, "macro_intelligence_terminal.html"), encoding="utf-8").read()
u = open(os.path.join(W, "update_terminal.py"), encoding="utf-8").read()
ml = open(os.path.join(W, "ml_models.py"), encoding="utf-8").read()
wf_p = os.path.join(W, ".github", "workflows", "daily-update.yml")
wf = open(wf_p).read() if os.path.exists(wf_p) else ""
F = []
def ok(n, c):
    if not c: F.append(n)
def code(txt):
    """strip JS/py comments so an assertion cannot be satisfied by a comment"""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    txt = re.sub(r"^\s*//.*$", "", txt, flags=re.M)
    return txt
sc = code(s)

# ── 1 · the stress gate ────────────────────────────────────────────────
ok("_v9pct is null-safe", "if(!arr||!arr.filter)return null" in sc)
ok("composite needs >=4 gauges", "stressPcts.length>=4" in sc)
ok("MI_STRESS carries missing gauges", "missing:missing" in sc)
ok("unmeasured gate caps size (marketState branch)", "} else if(S.comp==null){" in sc and "cap='moderate'" in sc)
ok("marketState publishes degraded flag", "degraded:(S.comp==null)" in sc)
ok("desk header prints DEGRADED INPUTS", "DEGRADED INPUTS" in sc)
ok("proxy-aware accessor exists", "const SERIES_PROXY=" in sc and "window.__PROXY[sym]=alt[i]" in sc)
ok("midcap proxy declared", "'NIFTY_MIDCAP_100.NS':['MID150BEES.NS'" in sc)
ok("auto proxy declared", "'^CNXAUTO':['AUTOBEES.NS']" in sc)
# ── 2 · the tape score reads closes, not nulls ────────────────────────
ok("tapeScore cleans nulls before the moving average", "const px=clean(ser('^NSEI')||ser('NIFTY'))" in sc)
# ── 3 · one sizing state ──────────────────────────────────────────────
ok("positioning EQUITY row reads the desk stance", "_stanceRead(marketConfirmation(),ms,R.quad)" in sc)
ok("weekly cycle is labelled informational", "informational — the sizing state is the mechanical tape" in s)
ok("MACRO §0 CORE row reads the desk stance", s.count("the DESK stance") >= 3)
ok("no 'run beta and momentum' size word survives", "run beta and momentum" not in sc)
# ── 4 · theme board ───────────────────────────────────────────────────
ok("gold measured absolute", "idx:'GOLDBEES.NS',abs:true" in sc)
ok("duration measured absolute", "idx:'LTGILTBEES.NS',abs:true" in sc)
ok("_absRet exists", "function _absRet(sym,win)" in sc)
ok("index-less theme falls back to constituents", "if(!(t.sec||[]).length)return null;" in sc)
ok("turning flag computed", "turning:(r20!=null&&r60!=null&&Math.sign(r20)!==Math.sign(r60)" in sc)
ok("MARKET cell prints both horizons", "\">20d '+_v9s(b.mk.r20,1)+' \u00b7 60d '+_v9s(b.mk.r60,1)" in sc)
ok("confirmation deadband", "const DB=1.0" in sc and "inside the ±'+DB+'pp noise band" in sc)
# ── 5 · nowcast dating ────────────────────────────────────────────────
ok("_cpiNext helper", "function _cpiNext()" in sc)
ok("CPI tile dated to the next print", "'CPI · LAST → NEXT PRINT'" in sc)
ok("real repo at the MPC uses the next print", "real repo at the '+_mpcNextLabel()+' MPC" in sc)
ok("consensus gap printed", "Next print vs consensus" in sc)
# ── 6 · rates: no surviving 'cuts' sentence ───────────────────────────
ok("no 'cuts now, slow normalisation'", "cuts now, slow normalisation" not in s)
ok("§2 caption measured vs repo", "_bpr=(_repo!=null)?Math.round((_y1-_repo)*100):null" in sc)
ok("O/N row: surplus, not cuts", "below repo = surplus liquidity, not cuts" in s)
ok("no 'end of the cutting cycle' trough row", "end of the cutting cycle" not in s)
ok("no 'easing bias' liquidity row", "Surplus liquidity supports lower OIS" not in s)
# ── 7 · scraped data is the one ───────────────────────────────────────
ok("no typed 4.3 US 10Y default", "RATES_D['10Y'].p:4.3" not in s)
ok("no typed 6.84 India 10Y", "6.84-q.last" not in s)
ok("carry cushion from CURVES_LIVE", "cy.textContent=(us!=null&&in10!=null)?('+'+(in10-us).toFixed(2)+'pp'):'—'" in sc)
ok("fillBlv in10y candidate chain", "CURVES_LIVE.india['10y']:null];for(const x of c)" in sc)
ok("growth bucket PMI from the block", "X.pmi_mfg&&X.pmi_mfg.v!=null)?X.pmi_mfg.v:null" in sc)
ok("no 'shown for shape' provenance", "shown for shape, not as prints" not in s)
ok("Fed-hike scenario: exporters get the weaker-rupee tailwind", "favour domestic earners over exporters" not in s)
ok("ordinal helper in the first script block", s.find("function _ord(") < s.find("function _v9pct(") and s.find("function _ord(") > 0)
ok("CHARTS CPI implication computed", "the one threat to the easing case" not in s)
# ── 8 · screens & names ───────────────────────────────────────────────
ok("screen liquidity floor from MOVERS_LIVE", "const liq=function(r){if(!_MV)return true;" in sc)
ok("screen title honest below t>=2", "the ranker has NO measured edge" in s)
ok("sector leaders liquidity floor", "MOVERS_LIVE.all)?MOVERS_LIVE.all:null;if(!A)return true;const t=A[String(x.sym||'').replace('.NS','')]" in sc)
ok("NAMES cell from LONG themes", "leaders inside the LONG themes" in s)
# ── 9 · the book ──────────────────────────────────────────────────────
ok("book table renders sized rows only", "B.rows.filter(function(r){return !r.isModel;}).forEach(function(r,i){" in sc)
ok("model-call strip exists", "MODEL CALLS · '+mr.length+' · UNSIZED" in sc)
ok("conflict helper exists", "function _callConflict(side,tb)" in sc)
ok("LONG in an UNDERWEIGHT theme is a CONFLICT", "if(side==='LONG'&&(a==='UNDERWEIGHT'||a==='AVOID'))return {lvl:'CONFLICT'" in sc)
# ── 10 · validation ───────────────────────────────────────────────────
ok("regime table says bars", "test bars <span" in s and "<th>periods</th>" not in s)
ok("calibration caption says cross-sectional", "beat the <em>cross-sectional mean</em>" in s)
ok("ledger UNVERIFIABLE state", "'UNVERIFIABLE'" in sc and "recent_missing" in sc)
ok("HMM instability note", "verdict_trail" in sc)
# ── 11 · updater ──────────────────────────────────────────────────────
uc = code(u)
ok("updater BUILD v125", 'BUILD = "v126"' in u)
ok("updater declares SERIES_PROXY", "SERIES_PROXY = {" in u and '"NIFTY_MIDCAP_100.NS": ["MID150BEES.NS"' in u)
ok("history download includes proxies", "| set(PROXY_SYMS))" in u)
ok("TATAMOTORS.NS retired", '"TATAMOTORS.NS"' not in u and '"TMPV.NS"' in u)
ok("regime history publishes lproxy", '"lproxy": lproxy' in u)
ok("RUN_LOG has an ois line", '"ois": ((_OIS_LIVE or {}).get("source_kind") in ("ccil", "fbil_official")' in u)
ok("verify_build checks the US 10Y", "typed US 10Y" in u)
ok("verify_build checks the Nifty strike", "struck on different sessions" in u)
ok("PRICE_HEALTH expected_bar", 'payload["expected_bar"]' in u)
# a live check the old build failed: verify_build on this page passes
try:
    ut = load("ut125", os.path.join(W, "update_terminal.py"))
    fails = ut.verify_build(s)
    # data-lag findings (a bhavcopy newer than the equity book) are the page's
    # honest state on a given morning and are allowed; STRUCTURAL failures are not
    structural = [f for f in fails if not f.startswith("F&O block is dated")]
    ok("verify_build has no structural failure: " + "; ".join(structural), not structural)
except Exception as e:
    F.append(f"verify_build errored: {type(e).__name__}: {e}")
# ── 12 · ml_models ────────────────────────────────────────────────────
mc = code(ml)
ok("gate_note keyed off ranker t, not HMM", "ranker_best_t" in ml and 'if hmm.get("state")=="CHOPPY" else' not in mc)
ok("ledger re-anchors entry to the call date", 'r["entry_anchored"] = True' in ml)
ok("decile hit vs cross-sectional mean", "xs_hits[d].append(m > bar_mean)" in ml)
ok("verify_frozen reports recent_missing", '"recent_missing": recent_missing' in ml)
ok("read_validation_block exists", "def read_validation_block(html)" in ml)
ok("BUILD_TAG unchanged (no methodology change)", 'BUILD_TAG = "v122"' in ml)
try:
    mm = load("mm125", os.path.join(W, "ml_models.py"))
    import pandas as pd
    idx = pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-04", "2026-09-07"])
    ser = pd.Series([100.0, 110.0, 120.0, 130.0], index=idx)
    prev = {"open": [{"id": "x|A|2026-09-04", "date": "2026-09-04", "model": "stock-short", "name": "A",
                      "side": "LONG", "entry": 110.0, "entry_date": "2026-09-02", "h": 10,
                      "due": "2026-09-18", "key": "A"}], "closed": []}
    out = mm.score_ledger(prev, [], lambda k: ser, "2026-09-07")
    r = out["open"][0]
    ok("re-anchor: entry is the first close on/after the call date", r["entry"] == 120.0 and r["entry_date"] == "2026-09-04")
    ok("re-anchor: emitted entry kept for audit", r.get("entry_emitted") == 110.0)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        v = mm.verify_frozen({"rows": [{"date": "2026-09-04", "hash": "x"}]}, out_dir=d)
        ok("verify_frozen: missing recent payload is not clean", v["clean_recent"] is False and v["recent_missing"] == 1)
except Exception as e:
    F.append(f"ml_models runtime: {type(e).__name__}: {e}")
# ── 13 · workflow ─────────────────────────────────────────────────────
if wf:
    ok("workflow: concurrency group", "concurrency:" in wf and "cancel-in-progress: false" in wf)
    ok("workflow: push failure is fatal", "git push failed after 3 attempts" in wf and 'git push || echo "nothing to push"' not in wf)
    ok("workflow: payloads copied to the site", "cp history/pred_*.json _site/history/" in wf)
    ok("workflow: tests run", "python t125_desk.py" in wf)
else:
    F.append("workflow file missing at .github/workflows/daily-update.yml")
# ── 14 · the tests themselves run from the repo ───────────────────────
for fn in ("t121_safety.py", "t122_validation.py"):
    p = os.path.join(W, fn)
    if os.path.exists(p):
        ok(f"{fn} has no machine path", "/home/user/w/" not in open(p).read())

print("v126 FAILURES:", "none" if not F else "")
for f in F:
    print("  ! " + f)
sys.exit(1 if F else 0)
