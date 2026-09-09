"""v127 · the arena, the option chain, the risk forecast, the record's state
source, and the v125 items ported onto v126 — one assertion per guarantee.

    MI_ROOT=$PWD python t127_env.py        (CI)
    python t127_env.py                      (from the repo root)
"""
import os, re, sys, json, types, importlib.util

_ROOT = (os.environ.get("MI_ROOT")
         or (sys.argv[1] if len(sys.argv) > 1 else None)
         or os.path.dirname(os.path.abspath(__file__)) or ".")
def R(n): return os.path.join(_ROOT, n)

F = []
def ok(n, c):
    if not c: F.append(n)
def eq(n, a, b):
    if a != b: F.append("%s: %r != %r" % (n, a, b))

s = open(R("macro_intelligence_terminal.html"), encoding="utf-8").read()

def fn(sig, src=None):
    """one function body by BRACE MATCHING — never bounded on the next name"""
    t = src if src is not None else s
    a = t.index(sig); i = t.index("{", a); d = 0
    while i < len(t):
        c = t[i]
        if c in '"\'`':
            q = c; i += 1
            while i < len(t) and t[i] != q: i += 2 if t[i] == '\\' else 1
        elif t[i:i+2] == '//': i = t.index("\n", i)
        elif t[i:i+2] == '/*': i = t.index("*/", i) + 1
        elif c == '{': d += 1
        elif c == '}':
            d -= 1
            if d == 0: return t[a:i+1]
        i += 1
    raise AssertionError("unbalanced: " + sig)
def code(x):
    x = re.sub(r"/\*.*?\*/", "", x, flags=re.S)
    return re.sub(r"//[^\n]*", "", x)

# ══ 1 · THE GATE IS COMPUTED OUTSIDE THE RENDERER ═════════════════════════
ms = code(fn("function marketState(){"))
ok("marketState computes the gate itself", "stressCompute()" in ms)
ok("a partial composite is quoted as partial", "thin" in ms and "gauges" in ms)
ok("stressCompute publishes trust and a minimum", "stress_min_gauges" in code(fn("function stressCompute(){")) and "trusted" in code(fn("function stressCompute(){")))
ok("the cross-asset panel renders from the same object", "stressCompute()" in code(fn("function renderCrossAsset(){")))
ok("the desk carries the gate banner", "stressBanner()" in code(fn("function renderTodaysBook(){")))
ok("the risk cell reads UNMEASURED when the gate is down", "['UNMEASURED','var(--red)']" in s)

# ══ 2 · PRINTS, NOT ROWS ═══════════════════════════════════════════════════
ok("series health reports absence and staleness separately", "not in the published history" in fn("function serHealth(") and "rows behind the index" in fn("function serHealth("))
ok("symPick walks the page's own proxy table", "SERIES_PROXY" in code(fn("function symPick(")))
ok("_rel measures over prints", "_v9ret(" in code(fn("function _rel(sym,win){")))
ok("_absRet measures over prints", "_v9ret(" in code(fn("function _absRet(sym,win){")))
tb = code(fn("function themeBoard(){"))
ok("both horizons must agree", "r20>=th&&r60>=th" in tb and "r20<=-th&&r60<=-th" in tb)
ok("SPLIT is an action, not a caveat", "split=" in tb and "action='WAIT'" in tb)
ok("two horizon columns", "<th>20d</th><th>60d</th>" in s)
ok("a null 20-session median is dropped, not zeroed", "if(x.med20!=null)" in code(fn("function _themeMarket(t){")))

# ══ 3 · THE NOWCAST BELONGS TO THE MEETING ════════════════════════════════
ok("the MPC's print is chosen by publication date", "r.pub&&r.pub<=dt" in code(fn("function _cpiAtMPC(){")))
ok("_cpiNext keeps v126's shape but picks by date", "_cpiAtMPC()" in code(fn("function _cpiNext(){")))
ok("oil enters at the published lag", "i===oilAt" in code(fn("function _v9nowcast(){")))
cs = code(s)
ok("no site still says 'by Oct'", "CPI by Oct" not in cs and "nowcast by Oct" not in cs and "% by Oct" not in cs)

# ══ 4 · THE RECORD DESCRIBES THE PAGE ═════════════════════════════════════
ok("pageState publishes the mechanical state", "function pageState(" in s and "market_state:M.name" in code(fn("function pageState(){")))
ok("fno setups carry page_state", "page_state:pageState()" in code(fn("function fnoSetupsForLedger(")))
ok("pageState carries the macro sub-elements", "macro_sub:" in code(fn("function pageState(){")))
m = re.search(r"window\.FROZEN_LEDGER = (\{.*?\});", s, re.S)
ok("the frozen ledger block parses", bool(m))
if m:
    blk = json.loads(m.group(1))
    ok("the seeded row is marked, not deleted", "3a5cca9bd2777302" in ((blk.get("seeded") or {}).get("hashes") or []))
    ok("the block names the state-source change", "state_note" in blk)
ok("the frozen table strikes the seeded row", "SEEDED · NOT A PREDICTION" in s)

# ══ 5 · THE ARENA ═════════════════════════════════════════════════════════
ok("the arena section exists on the VALIDATION tab", 'id="validation-arena"' in s)
ok("the arena renderer is registered", "renderArena," in s and "function renderArena(" in s)
ok("the ARENA anchor exists for the pipeline", "window.ARENA = {" in s)
ok("the arena distinguishes forward from backtest", "FORWARD RECORD" in s and "BACKTEST</span> — the same policy" in s)
ok("the bandit rule is printed", "THE ONE THING THAT LEARNS" in s)
ok("the desk reads the forward record", "Forward record at 14 sessions" in s)

# ══ 5b · THE PAPER BOOK ═══════════════════════════════════════════════════
ok("the paper book panel leads the DESK", s.index('id="paper-book"') < s.index('id="todays-book"'))
ok("the PAPER_BOOK anchor exists", "window.PAPER_BOOK = {" in s)
ok("the book renderer is registered", "renderPaperBook," in s and "function renderPaperBook(" in s)
ok("the book prints what the agents did today", "WHAT THE AGENTS DID TODAY" in s)
ok("the book's rule is printed on the page", "The rule.</b>" in s)

# ══ 6 · THE OPTION CHAIN ══════════════════════════════════════════════════
ok("the options desk exists", 'id="options-desk"' in s and "function renderOptions(" in s)
ok("the OPTIONS_LIVE anchor exists", "window.OPTIONS_LIVE = {" in s)
ok("the chain is loaded on demand", "fetch('options_chain.json'" in s)
ok("the F&O card carries the option read", "optCardLine(sym)" in code(fn("function fnoCard(sym){")))
ok("no vol is fabricated", "no vol fabricated" in s)

# ══ 7 · TOMORROW'S RISK AND THE POST-MORTEM ═══════════════════════════════
ok("the risk desk exists", 'id="risk-desk"' in s and "function renderRiskDesk(" in s)
ok("the post-mortem exists", 'id="post-mortem"' in s and "function renderPostMortem(" in s)
ok("the post-mortem reads the frozen payload", "history/pred_'+pIso+'.json" in code(fn("function renderPostMortem(){")))
ok("the post-mortem names a pre-v127 state source", "the demoted model" in fn("function renderPostMortem(){"))
ok("the RISK_LIVE anchor exists", "window.RISK_LIVE = {" in s)
ok("the risk desk claims only its record", "That is the whole claim" in s)

# ══ 8 · TRANSMISSION ══════════════════════════════════════════════════════
ok("the transmission table exists", 'id="macro-sub"' in s and "function renderMacroSub(" in s)
ok("every sub-element maps to themes", s.count("to:[[") >= 20)

# ══ 9 · confirmation panel measures rotation ══════════════════════════════
ok("rotation, not direction", "IS THE ROTATION CONFIRMING" in s and "_tapeInline()" in s)
ok("WATCH is not a pass", "S.comp<(P('stress_watch')||35)" in s)

# ══ 10 · python side ══════════════════════════════════════════════════════
mlp, utp = R("ml_models.py"), R("update_terminal.py")
if os.path.exists(mlp):
    u = open(mlp, encoding="utf-8").read()
    ok("BUILD_TAG moved", 'BUILD_TAG = "v127"' in u)
    ok("the payload records the page's state", '"market_state_source"' in u and "_PAGE_STATE" in u)
    ok("the payload freezes the evening's risk", '"risk": _RISK_SNAP' in u)
    ok("the arena marks every horizon", "def arena_marks(" in u and "ARENA_H = (7, 14, 28, 56)" in u)
    ok("the bandit is bounded and gated", "ARENA_MIN_CELL = 20" in u and "np.clip(1 + ARENA_ETA * mr, 0.5, 1.5)" in u)
    ok("the backtest says the gate is not reconstructed", "NOT reconstructed" in u)
    ok("the HMM verdict is gated", '"separates_at_gate"' in u and '"decision_use": "none"' in u)
    ok("by_regime publishes independent periods", '"n_periods": round(len(a) / float(H), 1)' in u)
    ok("the walk-forward keeps names for the arena", "per_bar_named" in u)
    ok("the book is a crore, positions 4–12%", "BOOK_CAPITAL = 10_000_000.0" in u and "BOOK_POS_MIN = 4.0" in u and "BOOK_POS_MAX = 12.0" in u)
    ok("the book's sleeves are capped and include gold", '"gold": 12.0' in u and '"duration": 10.0' in u)
    ok("the book trades gold through GOLDBEES", '("GOLDBEES.NS", "gold")' in u)
    ok("the book pays the cost stack and slippage", "BOOK_SLIP_BP" in u and "_book_cost_bp(" in u)
    ok("the book is snapshotted daily", 'os.path.join(out_dir, "book_%s.json"' in u)
    ok("the book is patched into the page", '_patch_window_block(h, "PAPER_BOOK", _book)' in u)
    ok("the ledger rows carry the state source", '"state_source": (row.get("payload") or {}).get("market_state_source")' in u)
    sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
    sp = importlib.util.spec_from_file_location("ml127", mlp); mm = importlib.util.module_from_spec(sp); sys.modules["ml127"] = mm
    try:
        sp.loader.exec_module(mm)
        eq("the three-state gate is the Bonferroni z", round(mm._norm_ppf(1 - 0.05 / (2 * 3)), 2), 2.39)
        ok("THEME_MACRO mirrors the page's priors", mm.THEME_MACRO["IT"]["REFLATION"] == -1 and mm.THEME_MACRO["Banking"]["STAGFLATION"] == -1)
        # the book on a synthetic ledger: sizes land in [4, 12], sleeves respect their caps, a veto is honoured
        try:
            import pandas as _pd, numpy as _np
            _ix = _pd.bdate_range("2026-06-01", "2026-09-09")
            _px = {k: _pd.Series(_np.linspace(100, 110, len(_ix)), index=_ix) for k in ("A", "B", "C", "GOLDBEES.NS", "NIFTY", "LTGILTBEES.NS")}
            _g = lambda k: _px.get(k)
            _led = {"open": [{"id": "fno|A|2026-09-09", "model": "fno", "name": "A", "key": "A", "side": "LONG", "entry": 110.0, "entry_date": "2026-09-09", "date": "2026-09-09", "theme": "Capital goods & infra", "stop": 100.0, "target": 130.0, "due": "2026-09-30"},
                            {"id": "stock-short|B|2026-09-09", "model": "stock-short", "name": "B", "key": "B", "side": "LONG", "entry": 110.0, "entry_date": "2026-09-09", "date": "2026-09-09"},
                            {"id": "stock-short|C|2026-09-09", "model": "stock-short", "name": "C", "key": "C", "side": "LONG", "entry": 110.0, "entry_date": "2026-09-09", "date": "2026-09-09", "theme": "IT / exporters"}], "closed": []}
            _ps = {"market_state": "CONSTRUCTIVE", "cap": "none", "regime": "REFLATION",
                   "board": [{"k": "capgoods", "nm": "Capital goods & infra", "action": "LONG", "conv": "HIGH"},
                             {"k": "it", "nm": "IT / exporters", "action": "UNDERWEIGHT", "conv": "LOW"},
                             {"k": "gold", "nm": "Gold (in rupees)", "action": "LONG", "conv": "MED", "r20": 3, "r60": 5},
                             {"k": "duration", "nm": "Duration (long gilts)", "action": "WAIT", "conv": "LOW"}]}
            _bk = mm.paper_book_roll({}, _led, _ps, _g, "2026-09-09")
            _sz = [p["size_pct"] for p in _bk["positions"]]
            ok("book sizes stay inside 4–12%", bool(_sz) and min(_sz) >= 4.0 and max(_sz) <= 12.0)
            ok("a vetoed long is not taken", not any(p["name"] == "C" for p in _bk["positions"]) and any(x["name"] == "C" for x in _bk["skipped"]))
            ok("the gold theme LONG buys GOLDBEES", any(p["key"] == "GOLDBEES.NS" for p in _bk["positions"]))
            ok("duration on WAIT is not bought", not any(p["key"] == "LTGILTBEES.NS" for p in _bk["positions"]))
            ok("the HIGH-conviction F&O call is the largest", max(_bk["positions"], key=lambda p: p["size_pct"])["name"] == "A")
            ok("cash + positions is the capital less costs", abs(_bk["equity"] - 10_000_000.0) < 20_000)
            _bk2 = mm.paper_book_roll(_bk, _led, _ps, _g, "2026-09-09")
            ok("a second pass on the same day re-enters nothing", len(_bk2["today"]) == 0 and len(_bk2["positions"]) == len(_bk["positions"]))
            _ps_off = dict(_ps, market_state="STRESS", cap="off")
            _bk3 = mm.paper_book_roll(_bk, _led, _ps_off, _g, "2026-09-10")
            ok("STRESS stands the risk sleeves down", not any(p["sleeve"] in ("stocks", "fno") for p in _bk3["positions"]) and any("gate off" in t["why_out"] for t in _bk3["trades"]))
        except Exception as e:
            F.append("paper book test threw: %s" % e)
    except Exception as e:
        F.append("ml_models.py would not import: %s" % e)
if os.path.exists(utp):
    u2 = open(utp, encoding="utf-8").read()
    ok("BUILD moved", 'BUILD = "v127"' in u2)
    ok("series health is a run-log subsystem", "def series_health(" in u2 and '"gate series health": _sh_log' in u2)
    ok("hstats is fail-safe", "write_history_json(stamp) or {}" in u2)
    ok("the chain is priced with Black-76", "def _iv76(" in u2 and "def options_chain_from_rows(" in u2)
    ok("OPTIONS_LIVE and RISK_LIVE are data contracts", '"OPTIONS_LIVE":  "window.OPTIONS_LIVE"' in u2 and '"RISK_LIVE":     "window.RISK_LIVE"' in u2)
    ok("the risk forecast never narrows on an event", "max(1.0, ev[\"mult\"])" in u2)
    ok("the warning list is drawn from tradeable names", "tradeable" in u2 and "hi_tradeable" in u2)
    ok("GVA by sector and IIP parts are parsed", '"gva_sectors"' in u2 and '"parts"' in u2)
    sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
    sp2 = importlib.util.spec_from_file_location("ut127", utp); ut = importlib.util.module_from_spec(sp2); sys.modules["ut127"] = ut
    try:
        sp2.loader.exec_module(ut)
        # the IV solver round-trips a known vol
        F0, K, T, r, sig = 24000.0, 24100.0, 22 / 365, 0.0526, 0.14
        px = ut._bs76(F0, K, T, r, sig, "CE")
        iv = ut._iv76(px, F0, K, T, r, "CE")
        ok("Black-76 IV round-trips", iv is not None and abs(iv - sig) < 1e-3)
        ok("a price below intrinsic gets no vol", ut._iv76(1.0, 25000.0, 24000.0, T, r, "CE") is None)
    except Exception as e:
        F.append("update_terminal.py would not import: %s" % e)

# ══ 11 · the workflow ═════════════════════════════════════════════════════
wf = R(".github/workflows/daily-update.yml")
if os.path.exists(wf):
    w = open(wf, encoding="utf-8").read()
    ok("t127 runs in CI", "python t127_env.py" in w)
    ok("the chain rides to the site", "cp options_chain.json _site/" in w)
    ok("the book snapshots ride to the site", "cp history/book_*.json _site/history/" in w)
    ok("a published row without a payload fails the run", "Verify the published ledger" in w)
    ok("the frozen payloads ride to the site", "cp history/pred_*.json _site/history/" in w)
    ok("a rejected push fails the run", "exit 1" in w and "git push" in w)

print("v127 FAILURES: " + ("none" if not F else "\n  - " + "\n  - ".join(F)))
sys.exit(1 if F else 0)
