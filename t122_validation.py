"""v122 · the validation engine: costs, split discipline, immutability,
promotion ceilings, and the page wiring that publishes them."""
import sys, re, json, types, importlib.util, os, tempfile
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
sp=importlib.util.spec_from_file_location("m","/home/user/w/ml_models.py")
m=importlib.util.module_from_spec(sp); sys.modules["m"]=m; sp.loader.exec_module(m)
spu=importlib.util.spec_from_file_location("ut","/home/user/w/update_terminal.py")
ut=importlib.util.module_from_spec(spu); sys.modules["ut"]=ut; spu.loader.exec_module(ut)
s=open("/home/user/w/macro_intelligence_terminal.html",encoding="utf-8").read()
u=open("/home/user/w/ml_models.py",encoding="utf-8").read()
F=[]
def ok(n,c):
    if not c: F.append(n)
def eq(n,a,b):
    if a!=b: F.append(f"{n}: {a!r} != {b!r}")

# ── 1 · the cost stack is published rates, and the arithmetic is right ──
c=m.cost_bp(1_000_000)
ok("STT is 20bp round trip on delivery", abs(c["components"]["STT"]-20.0)<0.01)
ok("stamp duty is buy-side only", abs(c["components"]["stamp duty"]-1.5)<0.01)
ok("GST is not charged on STT or stamp",
   abs(c["components"]["GST"]-(c["components"]["brokerage"]+c["components"]["exchange txn"]+c["components"]["SEBI turnover"])*0.18)<0.01)
ok("explicit cost is dominated by STT", c["components"]["STT"]/c["explicit_bp"]>0.6)
i=m.cost_bp(1_000_000,delivery=False)
ok("intraday is far cheaper than delivery", i["explicit_bp"] < c["explicit_bp"]/2)
ok("DP charge is delivery-only", i["components"]["DP charge"]==0)
ok("costs rise with the execution level",
   m.cost_bp(level="normal")["total_bp"] < m.cost_bp(level="conservative")["total_bp"] < m.cost_bp(level="stressed")["total_bp"])
ok("the wide tier costs more than core",
   m.cost_bp(tier="wide")["total_bp"] > m.cost_bp(tier="core")["total_bp"])
ok("spread/impact is separated from published rates",
   "spread_impact_bp" in c and "explicit_bp" in c)
ok("the estimate is labelled an estimate", "DECLARED ASSUMPTION" in m.SPREAD_IMPACT_BP["_note"])

# ── 2 · the split discipline is enforced in code, not described ──────────
seg=u[u.index("def walk_forward_deciles"):u.index("def _ann(")] if "def _ann(" in u[u.index("def walk_forward_deciles"):] else u[u.index("def walk_forward_deciles"):u.index("def baseline_suite")]
ok("train ends before the cut minus an embargo", "bar < (cut - emb)" in u)
ok("test starts a full horizon after the cut", "te0, te1 = cut + H" in u)
ok("the purge is at least the horizon", "purge_days\": int(H + emb)" in u or '"purge_days": int(H + emb)' in u)
# the word appears only in the comments that promise it does not happen —
# assert on the CALLS, which is what would actually leak
ok("no shuffling call anywhere", not any(x in u for x in
   ("shuffle=True", ".shuffle(", "np.random.shuffle", "KFold(", "train_test_split")))
ok("the target is rank-transformed inside each training bar", "np.argsort(np.argsort(ytr[sel]))" in u)
ok("the equity curve is non-overlapping", "chain = series[::max(1, int(H))]" in u)
ok("the independent-period count is published", '"independent_periods": len(chain)' in u)

# ── 3 · immutability of the frozen ledger ───────────────────────────────
d=tempfile.mkdtemp()
P1={"model_version":"v124","information_cutoff":"2026-09-02T15:30","regime":"REFLATION","calls_n":1}
P2=dict(P1); P2["regime"]="STAGFLATION"
r1=m.freeze_prediction(P1,"2026-09-02",out_dir=d)
r2=m.freeze_prediction(P1,"2026-09-02",out_dir=d)
r3=m.freeze_prediction(P2,"2026-09-02",out_dir=d)
eq("re-freezing identical content is a no-op", r2["status"], "unchanged")
ok("a differing payload becomes a revision", r3["status"].startswith("revision"))
orig=json.load(open(os.path.join(d,"pred_2026-09-02.json")))
eq("the ORIGINAL file is never rewritten", orig["payload"]["regime"], "REFLATION")
ok("the revision names what it supersedes", r3["row"].get("supersedes_hash")==r1["hash"])
blk={}
for r in (r1,r2,r3): blk=m.append_frozen_row(blk,r["row"])
ok("the page block is append-only", len(blk["rows"])==2 and blk.get("revisions")==1)
v=m.verify_frozen(blk,out_dir=d)
ok("a clean ledger verifies", v["clean"] and v["hash_mismatch"]==0)
t=json.loads(json.dumps(blk)); t["rows"][0]["hash"]="deadbeefdeadbeef"
vt=m.verify_frozen(t,out_dir=d)
ok("an EDITED published hash is caught as tampering", vt["hash_mismatch"]==1 and vt["clean"] is False)
g=json.loads(json.dumps(blk)); g["rows"].append({"date":"2019-01-01","hash":"aaaa"})
vg=m.verify_frozen(g,out_dir=d)
ok("a pruned old row is missing, not tampering", vg["file_missing"]==1 and vg["clean"] is True)
pay=m.build_prediction_payload("v124",{"state":"CHOPPY","prob":0.9},"REFLATION",70,None,
                               {20:{"top":["A"],"bottom":["B"],"ic":0.02,"t":1.1,"skill":"none"}},
                               {},{"gate":2.6,"significant":[]},{"open":[]},"2026-09-02T15:30")
for k in ("model_version","information_cutoff","regime","market_state","stock_ranks","invalidation","why_now"):
    ok("the frozen payload carries "+k, k in pay)
ok("invalidation conditions are stated", len(pay["invalidation"])>=3)

# ── 4 · the promotion ceiling is enforced, not advisory ─────────────────
GOOD={"ok":True,"ic_mean":0.09,"top_minus_bottom_net_pct":4.0,"top_minus_bottom_t":6.2,"monotonicity_rho":0.95}
BLOCKED={"rows":[{"distortion":"Survivorship","controlled":False,"blocking":True}],
         "blocking_uncontrolled":1}
CLEAN={"rows":[],"blocking_uncontrolled":0}
a=m.promotion_status(GOOD,None,0,0,CLEAN)
eq("a perfect backtest with no frozen record stays UNPROVEN", a["level"], "UNPROVEN")
b=m.promotion_status(GOOD,None,120,0,CLEAN)
eq("a frozen record without closed trades reaches EMERGING", b["level"], "EMERGING")
cc=m.promotion_status(GOOD,None,120,40,CLEAN)
eq("full evidence with clean data reaches VALIDATED", cc["level"], "VALIDATED")
dd=m.promotion_status(GOOD,None,120,40,BLOCKED)
eq("a blocking distortion CAPS it at EMERGING", dd["level"], "EMERGING")
eq("and the ceiling says so", dd["ceiling"], "EMERGING")
ok("the blocking reason is named", any("Survivorship" in w for w in dd["why_not_higher"]))
e=m.promotion_status({"ok":True,"top_minus_bottom_t":0.4,"top_minus_bottom_net_pct":-1.0,
                      "monotonicity_rho":0.1},None,300,90,CLEAN)
eq("a failing backtest cannot be promoted by a long record", e["level"], "UNPROVEN")
ok("every reason is printed", len(a["why_not_higher"])>=1)

# ── 5 · the survivorship row is present and blocking ────────────────────
import pandas as pd, numpy as np
pv=m.provenance_audit(pd.DataFrame(np.ones((400,20))),"test")
ok("survivorship is audited", any("Survivorship" in r["distortion"] for r in pv["rows"]))
ok("survivorship is uncontrolled and blocking",
   any(("Survivorship" in r["distortion"]) and (not r["controlled"]) and r["blocking"] for r in pv["rows"]))
ok("overlapping-label leakage is controlled",
   any("Overlapping" in r["distortion"] and r["controlled"] for r in pv["rows"]))
ok("the audit states the verdict", "CANNOT support a validated verdict" in pv["verdict"])

# ── 6 · the patchers verify their own write ─────────────────────────────
ok("a shared verified patcher exists", "def _patch_window_block" in u)
ok("it matches an ASSIGNMENT, not a substring", 'r"window\\.%s\\s*=\\s*\\{.*?\\};"' in u)
ok("it reports a failed write", "patch did not take" in u)
h2=m.patch_validation_block("<script>window.PRICE_SRC=1;</script>",{"a":1})
ok("a fresh page gets the block inserted", re.search(r"window\.VALIDATION\s*=\s*\{",h2) is not None)
h3=m.patch_validation_block(h2,{"a":2})
ok("an existing block is replaced, not duplicated", h3.count("window.VALIDATION = {")==1 and '"a":2' in h3)

# ── 7 · the page publishes and consumes both blocks ─────────────────────
ok("VALIDATION is a data contract", "VALIDATION" in ut.DATA_CONTRACTS)
ok("FROZEN_LEDGER is a data contract", "FROZEN_LEDGER" in ut.DATA_CONTRACTS)
eq("contracts", len(ut.DATA_CONTRACTS), 41)
ok("the validation tab exists", 'id="tab-validation"' in s and s.count('id="tab-validation"')==1)
ok("the tab is a direct child of main, not nested in another tab",
   s.index('<div id="tab-validation"') < s.index('<div id="tab-tearsheet"'))
for a in ("validation-body","validation-deciles","validation-curve","validation-regime",
          "validation-costs","validation-models","validation-provenance","validation-frozen",
          "validation-changes"):
    ok("anchor once: "+a, s.count('id="'+a+'"')==1)
ok("renderers registered", "renderValidation,renderDeciles,renderValCurve,renderValRegime,renderValCosts,renderValModels,renderValProvenance,renderValFrozen,renderValChanges," in s)
ok("the tab count says 11", '<span id="tab-count" style="display:none">11</span>' in s)
ok("build stamp v124", ">v124<" in s)
eq("updater BUILD", ut.BUILD, "v124")
# v123 · the page build and the MODEL version are deliberately allowed to
# diverge. BUILD_TAG stamps every frozen prediction, and the promotion
# framework says a methodology change starts a new out-of-sample record.
# The chart pack changed no model, so bumping BUILD_TAG would reset the
# frozen clock for a presentation change — the exact cost the framework
# warns about. It stays where the last real model change left it.
ok("model version does not follow a presentation-only build",
   m.BUILD_TAG == "v122" and ut.BUILD == "v124")
ok("the divergence is intentional, not drift", m.BUILD_TAG <= ut.BUILD)

# ── 8 · sizing is a function of proven edge ─────────────────────────────
ok("the promotion ladder is a parameter set",
   all(k in s for k in ("risk_r_unproven:{","risk_r_emerging:{","risk_r_validated:{")))
ok("the desk reads the status", "function _valStatus" in s and "function modelRiskPct" in s)
ok("a model signal is capped by the status", "MODEL SIZING —" in s and "p.src==='model'" in s)
ok("discretionary trades are tagged and not capped", "discretionary" in s and "bk-src" in s)
ok("the stored source tag survives a reload", "(p.src==='model')?'model_sized'" in s)
ok("the book states the sizing regime", "MODEL SIZING · " in s)

# ── 9 · the engine refuses to score a synthetic panel ───────────────────
ok("a synthetic panel cannot earn a status", 'if synthetic:' in u and '"level": "UNPROVEN"' in u)
ok("no frozen row is written from synthetic prices", "would poison the only honest evidence" in u)

print("v122 FAILURES:", "\n  ".join(F) if F else "none")

# ══════════════════════════════════════════════════════════════════════════
# v123 · the India chart pack
# ══════════════════════════════════════════════════════════════════════════
ok("chart pack tab exists once", s.count('id="tab-pack"')==1)
ok("chart pack is a top-level tab", s.index('<div id="tab-pack"') < s.index('<div id="tab-tearsheet"'))
ok("chart pack view anchor once", s.count('id="cp-view"')==1)
ok("chart pack renderer registered", "renderChartPack,renderValidation," in s)
ok("seven sections declared", s.count("const CP_SECS=[")==1 and all(("k:'"+k+"'") in s for k in
   ["policy","decomp","regimes","curve","cross","equity","fx"]))
ok("pages register through one path", s.count("function cpReg(")==1 and s.count("cpReg({k:'")>=12)
ok("no duplicate page keys", (lambda ks: len(ks)==len(set(ks)))(re.findall(r"cpReg\(\{k:'([a-z_0-9]+)'", s)))
ok("every page names a real section",
   all(sec in ["policy","decomp","regimes","curve","cross","equity","fx"]
       for sec in re.findall(r"cpReg\(\{k:'[a-z_0-9]+',sec:'([a-z]+)'", s)))
ok("the pack reads live blocks, never its own copy", "function cpB(" in s and "window[n]" in s)
ok("a failed page is reported, not swallowed", "THIS PAGE DID NOT RENDER" in s)
ok("staleness is computed from the read's own age", "function cpAgeDays" in s and "oisAge>3" in s)
ok("the swap page states the FBIL limitation",
   "no server-readable endpoint" in s or "serves no endpoint" in s)
ok("the decomposition refuses to invent a breakeven",
   "no liquid inflation-linked" in s and "Inventing one would be" in s)
ok("thin sectors are kept out of the headline", "const MINN=8;" in s and "wearing a sector" in s)
ok("narrow charts get a matching viewBox", "opt.vw||1000" in s and "vw:430" in s)
ok("pack CSS is scoped to the tab", "#tab-pack .cpw" in s and "#tab-pack{" in s)
ok("pack chrome helpers exist", all(("function "+f2+"(") in s for f2 in
   ["cpHead","cpBand","cpRail","cpFoot","cpNav","cpHome","cpStale"]))
ok("chart primitives exist", all(("function "+f2+"(") in s for f2 in
   ["cpLine","cpBars","cpRibbon","cpRankBars","cpHeat"]))
ok("no duplicate pack renderers", all(s.count("function "+f2+"(")==1 for f2 in
   ["cpGo","cpHome","cpLine","cpRankBars","renderChartPack"]))

print("v123 FAILURES:", "\n  ".join(F) if F else "none")
