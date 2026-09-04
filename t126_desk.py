"""v126 · structure, declutter, the F&O desk, the bootstrapped OIS analytics,
nominal-only regimes. Runs from the repo root."""
import sys, re, os
W = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(W, "macro_intelligence_terminal.html"), encoding="utf-8").read()
u = open(os.path.join(W, "update_terminal.py"), encoding="utf-8").read()
t = open(os.path.join(W, "tearsheet.py"), encoding="utf-8").read() if os.path.exists(os.path.join(W, "tearsheet.py")) else ""
F = []
def ok(n, c):
    if not c: F.append(n)
sc = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
# tabs
tabs = re.findall(r'onclick="sw\(this,\'([a-z]+)\'\)"', s)
ok("tab order desk→macro→ois→micro→pack→validation→forex→comm→intl→news", tabs == ['desk','macro','ois','micro','pack','validation','forex','comm','intl','news'])
ok("tear-sheet tab removed from the bar", "sw(this,'tearsheet')" not in s)
ok("notes toggle present", "NOTES OFF" in s)
ok("notes hidden by default (css)", "body:not(.verbose) .note{display:none!important}" in s)
# declutter engine
ok("cutSections defined", "function cutSections()" in sc and "const CUT_SECS=" in sc)
for p in ["'THE LIVE BOOK'", "'THE REGIME IN FULL'", "'0.35 ·'", "'5 · Real rates'", "'8 · AT THE MARGIN'", "'0.3 · DERIVATIVES'"]:
    ok(f"cut list has {p}", p in sc)
ok("scenarios (9) kept", "'9 · SCENARIOS'" not in sc)
ok("book moves to BUILD & SIZE", "mv('THE LIVE BOOK','desk','sub-build'" in sc)
ok("derivatives move to the F&O tab", "mv('0.3 · DERIVATIVES','macro','sub-fno'" in sc)
ok("tear sheets become a chart-pack appendix", "id='cp-appendix'" in sc or 'cp-appendix' in sc)
ok("desk-top retitled", "THE MODEL DESK · THE CALENDAR · WHERE TO GO NEXT" in s and "THE READ BEHIND IT" not in s)
ok("six tiles + chain are verbose-only", sc.count("document.body.classList.contains('verbose')") >= 4)
# F&O desk
ok("fno subtab button", "msw(this,'fno')" in s)
ok("msw knows fno", "['short','long','fno','build']" in sc and "fno:2,build:3" in sc)
ok("sub-fno container", 'id="sub-fno"' in s and 'id="fno-desk"' in s and 'id="fno-card"' in s)
for fn in ["_fnoRows", "renderFnoDesk", "fnoCard", "fnoSort", "_fnoWeeklyChart"]:
    ok(f"{fn} defined", f"function {fn}(" in sc)
ok("fno entry points exported from the IIFE", "window.renderFnoDesk=renderFnoDesk;window.fnoCard=fnoCard" in sc)
ok("setup labels are the feedback's chain", all(x in sc for x in ["'LONG SETUP'", "'SHORT SETUP'", "'TACTICAL'", "'WAIT · GATE'"]))
ok("gate caps longs", "if(gateOn&&(setup==='LONG SETUP'||setup==='PRICE ONLY'))" in sc)
ok("card has THESIS BREAKS IF", "THESIS BREAKS IF" in s and "WHY NOW" in s)
ok("card reads the theme board", "3 · THE BOARD" in s and "1 · MACRO PRIOR" in s)
ok("rule-based and unproven, said", "Rule-based and unproven" in s)
# OIS analytics
ok("2.7 section", "2.7 · THE CURVE, BOOTSTRAPPED" in s)
for fn in ["_oisPar", "_oisBoot", "_oisSvg", "renderOisAnalytics"]:
    ok(f"{fn} defined", f"function {fn}(" in sc)
ok("dealer screen reference block", "window.OIS_REF=window.OIS_REF||{asof:'2026-09-04 12:14 IST'" in sc)
ok("fixing vs screen gap printed", "THE FIXING AGAINST THE DEALER SCREEN" in s)
ok("level shift from the screen", "const shift=gaps.length?" in sc)
ok("forward-starting swaps", "B.fs(12,24)" in sc and "B.fs(60,120)" in sc)
ok("vol cone waits for 60 sessions", "tr.length>=60" in sc)
ok("ois analytics exported", "window.renderOisAnalytics=renderOisAnalytics" in sc)
# chart pack regimes: nominal 2s10s
ok("r_hist titled nominal 2s10s", "India · 2s10s Nominal Regime History" in s)
ok("r_hist uses gsec_trail belly/10Y legs", "r[0],r[3],r[4]" in sc and "usingG?gtr:" in sc)
# updater
ok("updater BUILD v126", 'BUILD = "v126"' in u)
ok("updater publishes the full F&O table", 'out["stocks"] = sorted(stocks, key=lambda r: r["s"])' in u)
ok("F&O rows carry basis and quadrant", '"b": (round((f["cls"] / und - 1) * 10000, 1) if und else None)' in u and '"q": q' in u)
# tearsheet
if t:
    ok("tearsheet p21 nominal-only title", "nominal 2s10s only" in t)
    ok("tearsheet p21 drops inflation/real rows", "v126: nominal only" in t)
# stamp
ok("page stamp v126", ">v126<" in s)
print("v126 FAILURES:", "none" if not F else "")
for f in F: print("  ! " + f)

# ── v126 final · the two things that were still open ──
s2 = open(os.path.join(W, "macro_intelligence_terminal.html"), encoding="utf-8").read()
u2 = open(os.path.join(W, "update_terminal.py"), encoding="utf-8").read()
m2 = open(os.path.join(W, "ml_models.py"), encoding="utf-8").read()
wf = open(os.path.join(W, ".github", "workflows", "daily-update.yml")).read()
F2 = []
def ok2(n, c):
    if not c: F2.append(n)
ok2("FBIL door: keyless endpoint wired", 'FBIL_OIS_URL = "https://www.fbil.org.in/wasdm/miborois/fetch?authenticated=false"' in u2 and "def fetch_ois_fbil()" in u2)
ok2("FBIL before the mirror, after CCIL", u2.find("fb = fetch_ois_fbil()") > u2.find("ccil = fetch_ois_ccil()") and u2.find("fb = fetch_ois_fbil()") < u2.find("for label, u in OIS_DOORS:"))
ok2("RUN_LOG treats the official fixing as ok", '("ccil", "fbil_official")' in u2 and "def _ois_runlog_text(o)" in u2)
ok2("page exposes fnoSetupsForLedger", "function fnoSetupsForLedger()" in s2 and "window.fnoSetupsForLedger=fnoSetupsForLedger" in s2)
ok2("fno_setups.py present", os.path.exists(os.path.join(W, "fno_setups.py")))
ok2("ledger emits model fno from fno_setups.json", '"model": "fno"' in m2 and 'REC_H = {"fno": 15' in m2)
ok2("ledger scores the path (stop/target/due)", '"closed_by": kind' in m2 and 'hit_path = ("stop", float(px), d)' in m2)
ok2("card shows ledger status", "IN THE LEDGER" in s2)
ok2("workflow installs playwright and runs fno_setups before ml_models", "playwright install --with-deps chromium" in wf and wf.find("python fno_setups.py") < wf.find("python ml_models.py"))
ok2("rates header no longer names the mirror as the source", "FBIL fixings via Cbonds" not in s2)
try:
    import types, importlib.util, pandas as pd
    sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
    sp = importlib.util.spec_from_file_location("mm126", os.path.join(W, "ml_models.py")); mm = importlib.util.module_from_spec(sp); sp.loader.exec_module(mm)
    idx = pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-03"]); ser = pd.Series([100.0, 106.0, 90.0], index=idx)
    out = mm.score_ledger({"open": [{"id": "fno|B|2026-09-01", "date": "2026-09-01", "model": "fno", "name": "B", "side": "SHORT", "entry": 100.0, "entry_date": "2026-09-01", "h": 15, "due": "2026-09-22", "stop": 105.0, "target": 80.0, "key": "B"}], "closed": []}, [], lambda k: ser, "2026-09-03")
    ok2("runtime: a short through its stop closes at the stop", out["closed"] and out["closed"][0].get("closed_by") == "stop")
except Exception as e:
    F2.append(f"runtime: {type(e).__name__}: {e}")
print("v126-final FAILURES:", "none" if not F2 else "")
for f in F2: print("  ! " + f)
sys.exit(1 if (F or F2) else 0)
