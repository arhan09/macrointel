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

# ══ 5c · v128 · LESS ON THE SCREEN, MORE ANSWERS ═════════════════════════
ok("the Q&A tab exists and is registered", 'id="tab-qa"' in s and "renderQA," in s and "function renderQA(" in s)
ok("the ask-a-share bar leads the F&O desk", s.index('id="fno-ask"') < s.index('id="options-desk"') and "function nameAnalysis(" in s)
ok("the name analysis walks the chain", "1 · INDUSTRY — MACRO → MICRO" in s and "5 · WHAT THE MODEL DOES WITH IT" in s)
ok("a reason on every ranked share", "function reasonFor(" in s and "reasonLine(t.name)" in s and "reasonLine(p.name)" in s)
ok("SIMPLE / FULL mode exists and boots", 'id="mi-mode"' in s and "body.simple .deep{display:none!important}" in s and "miModeBoot,startLive]" in s)
ok("the chart views exist", 'data-c2="comm"' in s and "function renderCharts2(" in s and "GOLDBEES.NS" in code(fn("function renderCharts2(){")))
ok("the demoted HMM card is off the model desk", "HMM MARKET STATE <span" not in s)
ok("the model and the book are separated in words", "Calls are the information, the book is the test" in s)
ok("ten questions are answered on the Q&A tab", s.count("askReg('") >= 18)

# ══ 5d · v129 · THE DIALS AND THE CROSS-ASSET BOOK ═══════════════════════
ok("the dials panel exists and is registered", 'id="dials"' in s and "renderDials," in s and "function marketDials(" in s)
ok("the dials read the three pillars off prices", "cyclicals vs defensives 60d" in s and "copper / gold 60d" in s and "OIS 1Y minus 1M" in s and "call rate vs repo" in s)
ok("disagreement with the data regime sizes the book down", "clash===0?1.0:clash===1?0.85:0.7" in s)
ok("the dials name the rates, rupee and gold expressions", "BEAR STEEPENER" in s and "LONG USD/INR" in s and "share_of_equity" in s)
ok("pageState carries the dials into the record", "dials:(typeof dialsState==='function')?dialsState():{}" in code(fn("function pageState(){")))
ok("the Q&A answers the agreement question", "askReg('dials'" in s)

# ══ 5e · v130 · THE LABOUR MARKET ═════════════════════════════════════════
ok("the labour card leads the MACRO tab", 'id="labour"' in s and s.index('id="labour"') < s.index('id="macro-sub"') and "function renderLabour(" in s)
ok("the LABOUR_LIVE anchor exists", "window.LABOUR_LIVE = {" in s)
ok("the labour chart view exists", 'data-c2="labour"' in s and "function renderLabourCharts(" in s)
ok("labour votes in the growth dial", "unemployment, 3-month change (sign flipped)" in code(fn("function marketDials(){")))
ok("labour is answered on the Q&A tab", "askReg('labour'" in s and "'labour','risk_on'" in s)
ok("copper leads the RESERVES & FX tab", 'id="fx-copper"' in s and "function renderCopperFx(" in s and "renderCopperFx," in s)

# ══ 5f · v131 · TOP 5 TO WATCH ════════════════════════════════════════════
ok("the watch list leads the F&O desk", 'id="watch-fno"' in s and s.index('id="watch-fno"') < s.index('id="fno-ask"'))
ok("the watch list leads STOCKS", 'id="watch-stocks"' in s and s.index('id="watch-stocks"') < s.index('id="regime-micro"'))
ok("the watch module exists and is registered", "function topWatch(" in s and "function renderWatch(" in s and "renderCopperFx,renderWatch," in s)
ok("the watch list re-renders with the F&O sub-tab", "if(t==='fno'){try{renderWatch();}catch(e){}" in s)
ok("the chain is scored leg by leg", all(("_wLeg('%s'" % k) in s for k in ("prior","board","dials","future","tape","screen","options","risk","ledger")))
ok("a gated long never makes the list", "if(gate&&c.side==='LONG'&&c.tag!=='OPEN CALL')return;" in code(fn("function topWatch(scope){")))
ok("the watch stop is the desk's stop", "Math.min(12,Math.max(3,2.5*sig))" in code(fn("function _wStop(sym,T){")))
ok("the top five ride into the record", "watch:(typeof watchState==='function')?watchState():{}" in code(fn("function pageState(){")))
ok("what to watch is answered on the Q&A tab", "askReg('watch'" in s)

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
    ok("the book carries its own version", 'BOOK_VERSION = "v127.1"' in u)
    ok("the book's sleeves are capped and include gold", '"gold": 12.0' in u and '"rates": 12.0' in u)
    ok("the book trades gold through GOLDBEES", '("GOLDBEES.NS", "gold")' in u)
    ok("the book pays the cost stack and slippage", "BOOK_SLIP_BP" in u and "_book_cost_bp(" in u)
    ok("the book is snapshotted daily", 'os.path.join(out_dir, "book_%s.json"' in u)
    ok("the book is patched into the page", '_patch_window_block(h, "PAPER_BOOK", _book)' in u)
    ok("a deploy cannot roll the record back", "def recover_frozen_block(" in u and "recover_ledger(read_recs_block(_html0))" in u and "snapshot_ledger(ledger)" in u and "recover_book(" in u)
    ok("the book carries rates, rupee and hedge sleeves", '"rates": 12.0' in u and '"fx": 8.0' in u and "BOOK_FX_STOP_PCT" in u and "gold as the policy-error hedge" in u)
    ok("the dials scale every size", "(6.0 + sc) * m * dmult" in u)
    ok("the payload freezes the dials", '"dials": (_PAGE_STATE or {}).get("dials")' in u)
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
            _px = {k: _pd.Series(_np.linspace(100, 110, len(_ix)) + 0.01 * (j + 1) * _np.arange(len(_ix)) % 1.0, index=_ix)
                   for j, k in enumerate(("A", "B", "C", "GOLDBEES.NS", "NIFTY", "LTGILTBEES.NS"))}
            _px = {k: (v.round(2)) for k, v in _px.items()}
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
            # one position per share: a display name and its NSE symbol are the same instrument
            _px["Bharat Co"] = _px["A"]
            _led_dup = {"open": _led["open"] + [{"id": "stock-short|Bharat Co|2026-09-09", "model": "stock-short", "name": "Bharat Co", "key": "Bharat Co", "side": "LONG", "entry": 110.0, "entry_date": "2026-09-09", "date": "2026-09-09"}], "closed": []}
            _bkd = mm.paper_book_roll({}, _led_dup, _ps, _g, "2026-09-09")
            ok("a share is held once across agents", sum(1 for p in _bkd["positions"] if p["key"] in ("A", "Bharat Co")) == 1 and any("already held" in x["why"] for x in _bkd["skipped"]))
            # an older call is never backdated: it fills at the entering pass's close
            _led_old = {"open": [{"id": "stock-short|B|2026-09-01", "model": "stock-short", "name": "B", "key": "B", "side": "LONG", "entry": 100.0, "entry_date": "2026-09-01", "date": "2026-09-01"}], "closed": []}
            _bko = mm.paper_book_roll({}, _led_old, _ps, _g, "2026-09-09")
            _pb = next((p for p in _bko["positions"] if p["key"] == "B"), None)
            ok("an older call fills at this pass's close, not its call-date close", _pb is not None and abs(_pb["entry"] - float(_px["B"].iloc[-1])) < 1e-6 and _pb["late"])
            # a rules change restarts the book and says why
            _bkr = mm.paper_book_roll(dict(_bk, book_version="v127.0"), _led, _ps, _g, "2026-09-10")
            ok("a rules change restarts the book, and says so", _bkr["restarts"] and _bkr["inception"] == "2026-09-10")
            # v129 · the dials: a bear steepener, a long rupee, gold as the hedge, and ×0.85 on one clash
            _px["GILT5YBEES.NS"] = _pd.Series(_np.linspace(60, 61, len(_ix)), index=_ix).round(2)
            _px["INR=X"] = _pd.Series(_np.linspace(94, 95.5, len(_ix)), index=_ix).round(3)
            _psd = dict(_ps, dials={"mult": 0.85, "strong": False, "rates_view": "BEAR STEEPENER", "fx_view": "LONG USD/INR", "fx_score": 3, "fx_prem_pct": 1.4, "hedge_share": 0.2, "quad_market": "GOLDILOCKS", "clash": 1})
            _bkd2 = mm.paper_book_roll({}, _led, _psd, _g, "2026-09-09")
            _ag = {p["agent"]: p for p in _bkd2["positions"]}
            _rl = [p for p in _bkd2["positions"] if p["agent"] == "rates"]
            ok("the steepener is two legs, long 5y short 10y+", len(_rl) == 2 and {(p["key"], p["side"]) for p in _rl} == {("GILT5YBEES.NS", "LONG"), ("LTGILTBEES.NS", "SHORT")})
            ok("the rupee is held long on the dials", "fx" in _ag and _ag["fx"]["side"] == "LONG" and _ag["fx"]["key"] == "USDINR")
            _gd = next((p for p in _bkd2["positions"] if p["key"] == "GOLDBEES.NS"), None)
            ok("gold is sized as the hedge against equity exposure", _gd is not None and _gd["size_pct"] >= 4.0)
            _a = next((p for p in _bkd2["positions"] if p["name"] == "A"), None); _a0 = next((p for p in _bk["positions"] if p["name"] == "A"), None)
            ok("one clash sizes the equity book down", _a is not None and _a0 is not None and _a["size_pct"] < _a0["size_pct"])
            _psd2 = dict(_psd, dials=dict(_psd["dials"], rates_view="CASH", fx_view="FLAT"))
            _bkd3 = mm.paper_book_roll(_bkd2, _led, _psd2, _g, "2026-09-09")   # same day, fresh panel
            ok("a changed view closes the expression", not any(p["agent"] in ("rates", "fx") for p in _bkd3["positions"]) and any("view now" in t["why_out"] for t in _bkd3["trades"]))
            # v130 · a pass before today's close enters nothing
            _bks = mm.paper_book_roll({}, _led, _ps, _g, "2026-09-10")   # the synthetic panel ends 2026-09-09
            ok("no close for today means no entries", not _bks["positions"] and _bks.get("fresh") is False and any("wait for the post-close" in x["why"] for x in _bks["skipped"]))
            _bk2 = mm.paper_book_roll(_bk, _led, _ps, _g, "2026-09-09")
            ok("a second pass on the same day re-enters nothing", len(_bk2["today"]) == len(_bk["today"]) and len(_bk2["positions"]) == len(_bk["positions"]) and len(_bk2["trades"]) == len(_bk["trades"]))
            _ps_off = dict(_ps, market_state="STRESS", cap="off")
            _bk3 = mm.paper_book_roll(_bk, _led, _ps_off, _g, "2026-09-09")   # same day, fresh panel
            ok("STRESS stands the risk sleeves down", not any(p["sleeve"] in ("stocks", "fno") for p in _bk3["positions"]) and any("gate off" in t["why_out"] for t in _bk3["trades"]))
        except Exception as e:
            F.append("paper book test threw: %s" % e)
        # v131 · the watch list's own record: target, stop, pending — scored from the frozen lists
        try:
            import tempfile as _tf, json as _js
            _wd = _tf.mkdtemp(); _wix = _pd.bdate_range("2026-06-01", "2026-09-09")
            _wpx = {"UP": _pd.Series(_np.linspace(100, 160, len(_wix)), index=_wix),          # +60% over the window: a LONG hits 2R fast
                    "FLAT": _pd.Series(_np.full(len(_wix), 100.0), index=_wix),
                    "NIFTY": _pd.Series(_np.linspace(100, 101, len(_wix)), index=_wix)}
            _wg = lambda k: _wpx.get(k)
            _js.dump({"watch": {"top": [{"sym": "UP", "name": "Up Co", "side": "LONG", "stop_pct": 5.0},
                                        {"sym": "UP", "name": "Up Co", "side": "SHORT", "stop_pct": 5.0},
                                        {"sym": "FLAT", "name": "Flat Co", "side": "LONG", "stop_pct": 5.0}]}},
                     open(os.path.join(_wd, "pred_2026-07-01.json"), "w"))
            _js.dump({"watch": {"top": [{"sym": "FLAT", "name": "Flat Co", "side": "LONG", "stop_pct": 5.0}]}},
                     open(os.path.join(_wd, "pred_2026-09-01.json"), "w"))
            _wr = mm.score_watch_lists(_wg, "2026-09-09", _wd)
            _by = {(r["sym"], r["side"]): r for r in _wr["rows"]}
            ok("a long through 2R closes at the target", _by[("UP", "LONG")]["closed_by"] == "target" and _by[("UP", "LONG")]["ret_pct"] >= 10.0)
            ok("a short against the move closes at the stop", _by[("UP", "SHORT")]["closed_by"] == "stop" and _by[("UP", "SHORT")]["ret_pct"] <= -5.0)
            ok("a flat name closes at the due session", _by[("FLAT", "LONG")]["closed_by"] == "due" and abs(_by[("FLAT", "LONG")]["ret_pct"]) < 1e-9)
            ok("a list without 15 sessions is pending, not scored", _wr["pending_lists"] == 1 and _wr["n_lists"] == 1 and _wr["first_due"] is not None)
            ok("the record prints hit rate and average", _wr["n_names"] == 3 and _wr["hit_pct"] is not None and _wr["avg_nifty_pct"] is not None)
            ok("the record is carried in the ledger block", 'ledger["watch_record"] = score_watch_lists(_get, _today)' in u)
        except Exception as e:
            F.append("watch record: %s" % e)
    except Exception as e:
        F.append("ml_models.py would not import: %s" % e)
if os.path.exists(utp):
    u2 = open(utp, encoding="utf-8").read()
    ok("BUILD moved", 'BUILD = "v131"' in u2)
    ok("the frozen row carries the watch list", '"watch": (_PAGE_STATE or {}).get("watch")' in open(R("ml_models.py"), encoding="utf-8").read())
    ok("series health is a run-log subsystem", "def series_health(" in u2 and '"gate series health": _sh_log' in u2)
    ok("hstats is fail-safe", "write_history_json(stamp) or {}" in u2)
    ok("the chain is priced with Black-76", "def _iv76(" in u2 and "def options_chain_from_rows(" in u2)
    ok("OPTIONS_LIVE and RISK_LIVE are data contracts", '"OPTIONS_LIVE":  "window.OPTIONS_LIVE"' in u2 and '"RISK_LIVE":     "window.RISK_LIVE"' in u2)
    ok("the risk forecast never narrows on an event", "max(1.0, ev[\"mult\"])" in u2)
    ok("the warning list is drawn from tradeable names", "tradeable" in u2 and "hi_tradeable" in u2)
    ok("GVA by sector and IIP parts are parsed", '"gva_sectors"' in u2 and '"parts"' in u2)
    ok("the labour market is fetched off the wire", "def fetch_labour(" in u2 and "def _plfs_from_text(" in u2 and "def _epfo_from_text(" in u2 and '"LABOUR_LIVE":   "window.LABOUR_LIVE"' in u2)
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
        # the PLFS parser on the July 2026 bulletin's own sentences
        _pl = ut._plfs_from_text("PRESS NOTE ON PERIODIC LABOUR FORCE SURVEY (PLFS) MONTHLY BULLETIN July, 2026 . Overall LFPR (15 years and above) increased to 55.4% in July 2026, from 54.4% in June 2026. Rural LFPR (15 years and above) increased by 1.4 percentage points over the previous month, reaching 58.0%. In urban areas, LFPR increased marginally, from 50.1% in June, 2026 to 50.4%. Overall WPR (15 years and above) increased to 52.5% in July 2026, marking the first increase since February 2026. Rural WPR (15 years and above) stood at 55.4% in July 2026. WPR in urban areas increased marginally to 47.0% from 46.8%. Overall UR (15 years and above) declined to 5.1% in July 2026, lower than both the previous month and the corresponding month. the urban UR remained almost steady at 6.7%.")
        ok("the PLFS parser reads the bulletin", _pl is not None and _pl.get("m") == "2026-07" and _pl.get("ur") == 5.1 and _pl.get("lfpr") == 55.4 and _pl.get("wpr") == 52.5 and _pl.get("ur_urban") == 6.7 and _pl.get("lfpr_rural") == 58.0)
        _ep = ut._epfo_from_text("Payroll Data: EPFO adds 19.29 lakh net members during June 2026 . Around 10.25 lakh new members joined; the 18-25 age group accounted for 59.14% of new members")
        ok("the EPFO parser reads the release", _ep is not None and _ep.get("m") == "2026-06" and _ep.get("net_lakh") == 19.29 and _ep.get("new_lakh") == 10.25)
        ok("a backgrounder is not a print", ut._plfs_from_text("Periodic Labour Force Survey: a backgrounder on methodology") is None)
        ok("the seed is a year of months", len(ut.LABOUR_SEED["plfs"]) >= 13 and ut.LABOUR_SEED["plfs"][-1]["m"] == "2026-07")
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
