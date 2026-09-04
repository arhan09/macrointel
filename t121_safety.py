"""v121.1 · the five blockers, each with a regression test that fails if it returns."""
import sys, re, json, types, importlib.util
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
sp=importlib.util.spec_from_file_location("ut","/home/user/w/update_terminal.py")
ut=importlib.util.module_from_spec(sp); sys.modules["ut"]=ut; sp.loader.exec_module(ut)
F=[]
def ok(n,c):
    if not c: F.append(n)
def eq(n,a,b):
    if a!=b: F.append(f"{n}: {a!r} != {b!r}")
s=open("/home/user/w/macro_intelligence_terminal.html",encoding="utf-8").read()
u=open("/home/user/w/update_terminal.py",encoding="utf-8").read()

# 1 · v124: the HMM is GONE from the decision path. The v121.1 blocker was
#     "a stress state could fall through to RISK-ON"; the guarantee survives,
#     but it is now delivered mechanically, so the test asserts the PROPERTY
#     rather than the old implementation's variable names.
seg_ms=s[s.index("function marketState(){"):s.index("function renderTodaysBook(){")]
# count CODE, not prose: the function's own comment explains that it USED
# to read ML_OUTPUT.hmm, and a raw substring test trips on that sentence.
import re as _re3
_seg_code=_re3.sub(r"/\*.*?\*/","",seg_ms,flags=_re3.S)
_seg_code=_re3.sub(r"//[^\n]*","",_seg_code)
ok("no fitted state model in the decision path", "ML_OUTPUT.hmm" not in _seg_code)
ok("stress is a gate and is tested first",
   seg_ms.index("S.comp>=hiT") < seg_ms.index("T.score>=3"))
ok("stress at or above the high threshold forces STRESS and cap off",
   "name='STRESS';tone='var(--red)';cap='off';" in seg_ms)
ok("the middle stress band caps size rather than standing down",
   "name='ELEVATED'" in seg_ms and "cap='moderate'" in seg_ms)
ok("stance stands down on STRESS", "String(ms.name||'')==='STRESS'" in s and "RISK OFF" in s)
ok("no tape reading can override a stress gate",
   seg_ms.index("cap='off'") < seg_ms.index("name='CONSTRUCTIVE'"))

# 2 · the measured regime edge reaches the theme board and can demote
seg=s[s.index("function themeBoard"):s.index("function marketConfirmation")]
ok("themeBoard reads the regime edge", "_regEdge(" in seg)
ok("a contrary significant edge demotes LONG to WAIT", "action='WAIT'" in seg and "against" in seg)
ok("edge has its own column", "<th>measured edge</th>" in s)

# 3 · direction-aware validation exists and aggregates exclude invalid rows
ok("validator present", "function bookValidate" in s)
for r in ["a LONG needs the stop BELOW the entry","a SHORT needs the stop ABOVE the entry",
          "a LONG needs the target ABOVE the entry","a SHORT needs the target BELOW the entry",
          "the stop cannot equal the entry","single-position limit"]:
    ok("validator rule: "+r, r in s)
ok("aggregates use only valid rows", "const valid=rows.filter" in s and "const withW=valid.filter" in s)
ok("risk budget is used, not hard-coded", "P0budget()" in s and "B.riskUsed>P0budget()" in s and "B.riskUsed>300?" not in s)
ok("limits are declared parameters", "max_position_pct:{" in s and "book_risk_budget_bp:{" in s)

# 4 · policy pricing averages the front end and does not sum three correlated legs
seg4=s[s.index("function renderPolicyPricing"):s.index("function renderINREngine")]
ok("front-end legs flagged", "front:true" in seg4 and seg4.count("front:true")==2)
ok("ten-year excluded from the signal", "front:false" in seg4)
ok("headline is a mean, not a sum", "const hawk=mean(" in seg4 and "reduce(function(a,l){return a+l.d1;},0)" not in seg4)
ok("window labelled by dated points", "spanTxt" in seg4 and "not yet measurable" in seg4)

# 5 · version
eq("updater BUILD", ut.BUILD, "v124")
ok("page build tag", '>v124<' in s)

# extras the review raised
ok("oil-to-CPI derived, not a second constant", "function brent10CpiBp" in s and "brent10_cpi_bp:" not in s)
ok("corridor claim softened", "cannot leave it" not in s and "breached the corridor" in s)
ok("liquidity wording fixed", "cleanest liquidity proxy" not in s and "real rates are the price of liquidity" in s)
ok("vol buckets not called safe/aggressive", "lower-vol" in s and "safe ≤" not in s)
ok("oil list multiple-testing stated", "Multiple testing:" in s and "by chance alone" in s)
ok("news freshness rule", "NEWS_MAX_AGE_H" in open("/home/user/w/update_terminal.py",encoding="utf-8").read())
eq("news max age", ut.NEWS_MAX_AGE_H, 72)
eq("undated stamp", ut._rss_age_hours("garbage"), ("", None))
w,a=ut._rss_age_hours("Tue, 01 Sep 2026 18:25:00 +0530"); ok("dated stamp parses", w=="01 Sep 18:25" and a is not None)
print("FAILURES:", "\n  ".join(F) if F else "none")

# ══════════════════════════════════════════════════════════════════════════
# v121.2 · the second review: three decision blockers + the deployment checks
# ══════════════════════════════════════════════════════════════════════════

# 6 · the empirical-edge gate is the MODEL'S, not a laxer one written in the page
seg6 = s[s.index("function _regEdge(sc){"):s.index("function _sectorStats(){")]
ok("_regEdge reads the published gate", "RE.gate" in seg6)
ok("_regEdge reads the published significant list", "RE.significant" in seg6)
ok("_regEdge no longer hard-codes its own bar", "Math.abs(v.t)<2)return null" not in seg6)
ok("an empty significant list means nothing cleared", "Array.isArray(RE.significant)" in seg6)
ok("findings are graded", "sig:sig" in seg6 and "grade:" in seg6)
segTB = s[s.index("function themeBoard"):s.index("function marketConfirmation")]
ok("only a significant edge may move an action", "if(edge.sig){" in segTB)
ok("a nominal edge never promotes to HIGH",
   segTB.index("if(edge.sig){") < segTB.index("conv='HIGH'"))
ok("a nominal contrary edge caps conviction", "if(conv==='HIGH')conv='MED';" in segTB)
ok("the grade is shown in the table", "SIGNIFICANT · gate" in s and "nominal · under gate" in s)

# 7 · CHOPPY caps risk however well the tape confirms
seg7 = s[s.index("function marketState(){"):s.index("function renderTodaysBook(){")]
ok("no state is ever labelled RISK-ON", "RISK-ON" not in seg7)
ok("each state carries the ceiling it implies", "cap='moderate'" in seg7 and "cap='off'" in seg7)
ok("a defensive tape caps size", "name='DEFENSIVE'" in seg7)
ok("marketState publishes the cap", "cap:cap" in seg7)
ok("the stance takes the stricter of the two", "const ceil=(ms.cap==='moderate')?1:2;" in seg7)
ok("a capped stance says what capped it", "cappedBy:ms.name" in seg7)
ok("a ceiling can only lower, never raise", "if(lvl>ceil){" in seg7)

# 8 · the book demands complete geometry and enforces the budget up front
seg8 = s[s.index("function bookValidate(p,opts){"):s.index("function bookCompute(){")]
for rule in ["a stop is required", "a target is required", "a size (% of book) is required",
             "the target cannot equal the entry", "BOOK RISK BUDGET"]:
    ok("validator rule: " + rule, rule in seg8)
ok("the budget blocks rather than warns", "o.override" in seg8 and "tick override" in seg8)
ok("the override is offered in the form", 'id="bk-ovr"' in s)
ok("bookAdd passes the override through", "bookValidate(cand,{override:ovr" in s)
seg8b = s[s.index("function bookCompute(){"):s.index("function renderTradeBook(){")]
ok("incomplete rows are classified, not silently zeroed", "const need=[];" in seg8b)
ok("model calls are exempt but excluded", "const isModel=(p.src==='model');" in seg8b)
ok("only complete rows reach the aggregates", "const valid=rows.filter(function(r){return r.counts;});" in seg8b)
ok("the header counts what sits outside the numbers", "nOut:nNeed+nModel" in seg8b)
ok("the risk cell cannot read green with rows outside it", "NOT in this number" in s)

# 9 · the swap blocks agree, and a build check says so
ok("resync exists", "def resync_ois_into_curves" in u)
ok("resync runs after the OIS patch",
   u.index("html = patch_ois_anchor(html)") < u.index("html, _ = resync_ois_into_curves(html)"))
ok("post-build assertions exist", "def verify_build" in u)
ok("build check is recorded on the page", '"cross-block checks"' in u)
ok("build check compares the page tag to BUILD", "page build tag" in u)

# 10 · news freshness: named zones parse, undated items do not reach the feed
ok("named timezones are normalised", "_TZ_NAMED" in u and '"IST": "+0530"' in u)
ok("undated items are dropped, not labelled", "undated_n += 1" in u)
ok("a future clock is not treated as fresh", "if age < -2:" in u)
ok("a zoneless stamp is read as IST, not UTC", "d = d.replace(tzinfo=ist)" in u)

# 11 · the FCNR split reconciles against the release's own total
ok("FCNR legs are reconciled", "reconciled" in u and "abs(sum(legs) - t)" in u)

# 12 · the stale statements are gone
for dead in ["every $10 on Brent ≈ 30-40bp", "Safe %", "Institutional-grade pages",
             "Liquidity = Real Rates", "that feed isn't wired yet",
             "Reserves <em>rising</em> = the RBI is buying dollars",
             "(OIS-implied)"]:
    ok("removed: " + dead[:44], dead not in s)

print("v121.2 FAILURES:", "\n  ".join(F) if F else "none")
