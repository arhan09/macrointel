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

# ══ 5g · v132 · THE CALL, THE RECORD, THE PUSH ════════════════════════════
ok("the page opens on HOME; the call page is kept, off the bar", "let CUR_TAB='home';" in s and '<div id="tab-home" class="tp a">' in s and '<div id="tab-call" class="tp">' in s)
ok("HOME leads the bar", re.findall(r'onclick="sw\(this,\'([a-z]+)\'\)"', s)[0] == 'home')
ok("the call module exists and is registered", "function renderCall(" in s and "function callState(" in s and "renderCall,renderTomorrowAll,renderRecord," in s)
ok("the call carries the five, the record and the ask bar", all(k in code(fn("function renderCall(){")) for k in ("call-watch", "_clRecord()", "call-ask-q")))
ok("the records live on BUILD & SIZE — the models' own validation, regardless of the agents", 'id="record-body"' in s and "function renderRecord(" in s and s.index('<div id="sub-build"') < s.index('id="record-body"') < s.index('id="model-desk"') and "regardless of the agents" in s)
ok("the record keeps the four records apart", all(k in s for k in ("1 · THE LIST", "2 · THE CALLS", "3 · THE PAPER BOOK", "4 · THE DAYS")))
ok("no tab hides in SIMPLE — macro is the product", "body.simple .tab[data-deep]" not in s and s.count('data-deep="1"') == 0)
ok("at most two names per theme make the five", "function _wPick(" in s and "if((cnt[k]||0)>=2){x.capped=true;continue;}" in s and "top5:_wPick(out,5)" in s)
ok("the pushed call is the page's own state", os.path.exists(R("push_call.py")) and "fno_setups.json" in open(R("push_call.py"), encoding="utf-8").read())
ok("no token lives in the source", not re.search(r"\d{8,10}:[A-Za-z0-9_-]{30,}", open(R("push_call.py"), encoding="utf-8").read() + s))

# ══ 5h · v133 · THE F&O DESK MADE CLEAR, 1D/1W, THE RECORD LAST ═══════════
# v139 · the search leads, THE TRADE stays in view, the lists fold behind one line
ok("the search leads the F&O desk, the trade stays in view, the lists fold", all(k in s for k in ('id="fno-search"', 'id="fno-trade"', 'id="fno-overview"', 'id="fno-next"', 'id="fno-lists"')) and s.index('id="fno-search"') < s.index('id="fno-trade"') < s.index('id="fno-lists"') < s.index('id="watch-fno"') < s.index('id="fno-next"') < s.index('id="fno-overview"') < s.index('id="fno-ask"'))
ok("the trade prices the option off the chain", "function _optPick(" in s and "options_chain.json" in code(fn("function _chainLoad(){")) and "function renderFnoTrade(" in s)
ok("the industries are read in plain words", "function renderFnoOverview(" in s and "THE INDUSTRIES IN PLAIN WORDS" in s)
ok("next week's contenders read the 5-session ranker", "function renderFnoNext(" in s and "Wd.horizons['5']" in s)
ok("the F&O cards are registered and re-render with the sub-tab", "renderFnoClear,renderCall," in s and "if(t==='fno'){try{renderWatch();}catch(e){}try{renderFnoClear();}catch(e){}" in s)
ok("the lookup has 1D and 1W — the door, then the feed's bars, then the snapshot", "['1d','5d','1mo','6mo','1y','5y']" in s and "function intraQ(" in s and "if(range==='1d'){" in s and "const fb=await feedBars(sym);" in s and "const iq=await intraQ(sym);" in s and "range==='5d'?5" in s)
ok("SIMPLE no longer hides the lookup, the verdict or the options desk", all(("'%s'" % k) not in fn("const MI_DEEP=[") for k in ("q-result", "q-verdict", "q-result2", "q-verdict2", "options-desk", "regime-micro", "fno-panel")))
ok("VALIDATION is off the bar but its panel stays behind the RECORD", "sw(this,'validation')" not in s and 'id="tab-validation"' in s and ("callGo(\\'validation\\')" in s or "callGo('validation')" in s) and "callGo('agents')" in s)
ok("Q&A closes the bar; the positioning table is retired", re.findall(r'onclick="sw\(this,\'([a-z]+)\'\)"', s)[-1] == 'qa' and "where it was five sessions later" not in s and "sw(this,'record')" not in s)
ok("the workflow publishes the intraday snapshot", ("intraday.json" in open(R(".github/workflows/daily-update.yml"), encoding="utf-8").read()) if os.path.exists(R(".github/workflows/daily-update.yml")) else True)

# ══ 5i · v134 · FEWER WORDS, EARLY MOVERS ═════════════════════════════════
ok("the early movers screen exists and leads from STOCKS", 'id="early-stocks"' in s and "function earlyMovers(" in s and "function renderEarly(" in s and "renderWatch,renderEarly," in s)
ok("the early rule is the printed one", "hi20=Math.max.apply(null,v.slice(L-21,L-1))" in code(fn("function earlyMovers(n){")) and "rs4<0.03||ext>0.20" in code(fn("function earlyMovers(n){")) and "if(wk>3)return;" in code(fn("function earlyMovers(n){")))
ok("the early movers ride into the record", "early:(typeof earlyState==='function')?earlyState():{}" in code(fn("function pageState(){")))
ok("the trade is a ticket, not a paragraph", "function _wChips(" in s and "▸ why" in s and "spread '+_ftFmt(O.K,0)+'/'" in s)
ok("the industries lead with numbers", "20d <b>'+_v9s(b.r20,1)+'%</b> · 60d <b>" in s and "THE INDUSTRIES IN PLAIN WORDS · regime" in s)
ok("every leg has a short form", "function _wLeg(k,v,txt,short)" in s and "'OI flat'" in s and "'dials '+(D.quad_market===REG.quad?'agree'" in s)

# ══ 5j · v135 · TOMORROW, SECOND OPINION, THE COMPUTED EDITORIAL ══════════
ok("tomorrow sits on THE CALL and is answered on Q&A", "call-tomorrow" in code(fn("function renderCall(){")) and "function renderTomorrow(" in s and "askReg('tomorrow'" in s and "renderTomorrowAll," in s)
ok("the second opinion sits beside gold, silver, copper and the index", all(k in s for k in ('id="voices-metals"', 'id="voices-copper"', 'voices-nifty')) and "function voicesCard(" in s and "window.VOICES = " in s)
ok("the editorial is computed, the typed one dated", 'id="week-data"' in s and "function renderWeekData(" in s and "THE 1 SEP EDITORIAL — dated prose" in s and "THIS WEEK IN THE DATA — editorial refresh" not in s)
ok("VOICES is a data contract", '"VOICES":        "window.VOICES"' in open(R("update_terminal.py"), encoding="utf-8").read())

# ══ 5k · v136 · AGENTS · LIVE MARKETS, THE DIP, EVERY LISTED NAME, THE SCHEDULE ══
ok("three agents on the last tab, printed from the ML pass", "function renderAgents(" in s and "function renderAgentsDesk(" in s and 'id="agents-body"' in s and "window.AGENTS = {" in s and "renderRecord,renderAgentsAll,renderDipAll,renderGoldCheck," in s)
ok("the agents' balances sit on AGENTS, the paper book on BUILD & SIZE", 'id="desk-agents"' in s and s.index('id="agents-body"') < s.index('id="desk-agents"') and s.index('<div id="sub-build"') < s.index('id="paper-book"') and "cash" in code(fn("function renderAgentsDesk(){")))
ok("the agents' leaderboard is against a crore in the Nifty", "nifty_ret_pct" in code(fn("function renderAgents(){")) and "leaderboard" in code(fn("function renderAgents(){")))
ok("the dip is on STOCKS, THE CALL and the lookup", 'id="dip-watch"' in s and "call-dip" in code(fn("function renderCall(){")) and "function dipLine(" in s and "dipLine(sym)" in code(fn("function nameAnalysis(q){")) and "function renderDipWatch(" in s)
ok("the dip names its level and its record", "fades above" in s and "run over below" in s and "dip_record" in s and "ML_OUTPUT" in code(fn("function _dpM(){")))
ok("the dip rides beside early movers and long tickets", "dipChip(x.sym)" in code(fn("function renderEarly(){")) and "dipChip(x.sym)" in code(fn("function _ftRow(x,O){")))
ok("BSE-only names resolve on the lookup", "BSE_LIVE" in code(fn("function _anResolve(q){")) and "BSE-only listing" in s and "window.BSE_LIVE = {" in s)
ok("the watch list reaches beyond the core", "x.sv==='BUY'&&(x.st||0)>=70" in code(fn("function topWatch(scope){")))
ok("a crash is not a contender: the ranker's picks carry their tape and an event tag", "function _fnTape(" in s and "not contenders:" in s and "p.fno!==false&&!p.event" in s)
# ══ 5l · v137 · OIS · MIBOR LIVE, THE LISTS IN THEIR PAGES, THE AGENTS' TAPE, WHY TRUST IT ══
ok("the swap curve is nowcast, pathed by meeting and differenced", 'id="ois-live-x"' in s and "function oisNowcast(" in s and "function oisPath(" in s and "function oisChanges(" in s and "renderOisLive," in s and "THE PATH BY MEETING" in s)
ok("the nowcast carries the fixing by the official bill move, labelled", "91-day bill" in code(fn("function oisNowcast(){")) and "FBIL LAGS" in s and "upper bound" in code(fn("function renderOisLive(){")))
ok("the OIS prose is folded, the empty placeholder too", '<div class="deep" style="font-size:12px;color:var(--dim);margin-bottom:14px;line-height:1.6">This is India' in s and '<div class="cd deep" style="padding:13px;border:1px solid var(--amb)' in s and '<div id="rates-signal" class="deep"' in s)
ok("intraday, then the short lists inside SHORT TERM, the ideas and the regime read inside LONG TERM", s.index('<div id="sub-intraday">') < s.index('id="why-moved"') < s.index('<div id="sub-short"') < s.index('id="watch-stocks"') < s.index('id="early-stocks"') < s.index('id="dip-watch"') < s.index('<div id="sub-long"') < s.index('id="lt-ideas"') < s.index('id="regime-micro"') < s.index('<div id="sub-build"'))
ok("nothing static sits above the MARKETS sub-tabs but the search", s.index('<div id="tab-micro" class="tp">') < s.index('<div class="subtabs">\n<button class="subtab a" onclick="msw(this,\'intraday\')">') and "id=\"watch-stocks\"" not in s[s.index('<div id="tab-micro" class="tp">'):s.index('<div class="subtabs">\n<button class="subtab a" onclick="msw(this,\'intraday\')">')])
ok("the sub-tabs say their horizon, each defined", "⚡ INTRADAY · today" in s and "📅 SHORT TERM · 5–60 sessions" in s and "🌱 LONG TERM · months" in s and "📈 F&amp;O" in s and "🧰 BUILD &amp; SIZE" in s and s.count('class="mi-defn"') >= 5)
ok("the agents' holdings move on a tape, marked live, on AGENTS and the DESK", 'id="agents-tape"' in s and 'id="desk-tape"' in s and "function agentsLive(" in s and "function renderAgentsTape(" in s and "startAgentsLive," in s and "@keyframes agtape" in s)
ok("the tape says where its prices come from", "browser-live" in code(fn("function _atSrc(){")) and "5-minute snapshot" in code(fn("function _atSrc(){")))
ok("why trust it sits on THE CALL, computed", "call-trust" in code(fn("function renderCall(){")) and "function trustRows(" in s and "function renderTrust(" in s and "renderTrust," in s and all(k in code(fn("function trustRows(){")) for k in ("'DATA'", "'REGIME'", "'SECTORS'", "'NAMES'", "'THE CALL'", "'SIZING'", "'THE BOOKS'", "'NOT'")))
# ══ 5m · v138 · CONVICTION, THE ANALYSTS, THE WIRE, THE MAIL ══════════════
ok("every name carries a conviction and the day has one", "function convictionFor(" in s and "function convictionToday(" in s and "convictionChip(convictionFor(x),true)" in code(fn("function _wCard(scope,elId){")) and "call-conviction" in code(fn("function renderCall(){")) and "renderConvictionToday," in s)
ok("conviction rides into the frozen record", "conv:cv?cv.score:null" in code(fn("function watchState(){")))
ok("the conviction penalises an event, the gate, a dials disagreement and dip risk", all(k in code(fn("function convictionFor(x){")) for k in ("event in the tape", "gate on", "dials disagree", "dip risk")))
ok("the analysts are printed on HOME and NEWS", "['call-alerts','home-alerts','desk-alerts']" in s and 'id="agents-analysts"' in s and s.index('<div id="tab-news"') < s.index('id="agents-analysts"') and "call-alerts" in code(fn("function renderCall(){")) and "function renderAlerts(" in s and "window.ALERTS = {" in s and "renderAlerts," in s)
ok("the wire is grouped by topic with its lean", 'id="wire-topics"' in s and "function renderWire(" in s and "function renderWireMini(" in s and "window.NEWS_LIVE = {" in s and "renderWire," in s)
# ══ 5n · v139 · SEARCH FIRST, THE VERDICT IN BOLD, THE CHART WITH THE MODEL'S LAYERS ══
ok("one search answers with a verdict in bold", "function verdictFor(" in s and "function searchAny(" in s and 'id="stocks-search"' in s and 'id="fno-search"' in s and "renderSearchBoxes," in s and "font-size:30px;font-weight:900" in s)
ok("the verdict is one of five words with a stop, a target, a size and a horizon", all(k in code(fn("function verdictFor(R){")) for k in ("out.act='BUY'", "out.act='SHORT'", "out.act='WAIT'", "out.act='AVOID'", "out.act='NO TRADE'", "out.stop=", "out.target=", "out.cap=", "out.horizon=")))
ok("an event, the gate and the dip risk downgrade the verdict", all(k in code(fn("function verdictFor(R){")) for k in ("a repricing in the tape", "the gate is on", "dip risk")))
ok("a sector or theme answers with the board's verdict and every member's own", "function sectorCard(" in s and "BUY THE SECTOR" in s and "members by turnover" in s)
ok("the performance table stands against the Nifty and the sector", "function _sqPerf(" in s and "function _sqSectorRet(" in s and "vs Nifty" in code(fn("function _sqPerfHtml(sym,sector){")))
ok("the chart engine carries the model's layers", "function mchart(" in s and "function shareLayers(" in s and all(k in code(fn("function shareLayers(sym,name,pairs,freq){")) for k in ("layer:'calls'", "layer:'levels'", "layer:'events'", "fades above")) and "function mchartToggle(" in s)
ok("the floater searches from every tab", "f.id='mi-float'" in s and "function floatToggle(" in s and "e.key==='/'" in s)
ok("every old ask-a-name link lands on the research page", "window.askName=window.askName||function(q,outId)" in s and "window.askName=function(q){try{if(q)openShare(q);" in s)
ok("rupee gold is drawn three ways", 'id="gold-chart"' in s and "function goldPairs(" in s and "function renderGoldChart(" in s and "renderGoldChart," in s and "GOLDBEES-implied" in s)
ok("rupee gold is checked, dated and labelled stale when it is", 'id="gold-check"' in s and "function goldCheck(" in s and "IBJA FIX STALE" in s and "ETF-IMPLIED" in s)

# ══ 5o · v141 · MACROINTEL 3 — THE PRODUCT, THE RATIONAL AGENTS ═══════════
ok("HOME is the product's front door, animated, with the chain and the pulse", 'id="home-body"' in s and "function renderHome(" in s and "Welcome to <span>MacroIntel</span>" in s and "function marketPulse(" in s and "WHAT PACES THE MARKET" in s and ",renderShell,renderMacroTop,renderTabTops," in s and ",renderIdeas,renderHome," in s)
ok("the app bar carries the stamp the updater patches, once, before the page", 'id="mi-stamp"' in s and len(re.findall(r"Data: [A-Za-z]{3} [A-Za-z]{3} \d+, \d{4} \d{2}:\d{2} IST \(auto\)", s[:s.index("<main")])) == 1 and 'id="mi-next"' in s)
ok("the nav is the product's twelve, the lens and the modes as utilities", re.findall(r'onclick="sw\(this,\'([a-z]+)\'\)"', s) == ['home','research','macro','charts','ois','forex','comm','intl','micro','agents','news','qa'] and 'id="mi-lens-btn"' in s and "class=\"tab util\" onclick=\"openLens()\"" in s)
ok("legacy tab names land on their new pages", "t=({call:'home',desk:'agents',pack:'charts',tearsheet:'charts'})[t]||t;" in code(fn("function sw(b,t){")))
ok("MACRO opens on the view, then the repo move, the flow, the pace, the charts; the detail folds; the pack is the CHARTS tab", 'id="macro-view"' in s and 'id="macro-top"' in s and "function repoMoved(" in s and "function thePace(" in s and "THE FLOW ·" in s and 'id="macro-detail"' in s and s.index('id="macro-view"') < s.index('id="macro-top"') < s.index('id="macro-dials"') < s.index('id="macro-detail"') < s.index('<div id="tab-charts"') < s.index('id="charts-top"') < s.index('id="tab-pack"'))
ok("RATES, the rupee, gold and global each open with what the tab tells you", all(('id="%s"' % k) in s for k in ("ois-plain", "fx-plain", "gold-plain", "intl-plain")) and "function renderRatesPlain(" in s and "WHAT THIS TAB TELLS YOU" in s and s.index('<div id="tab-ois"') < s.index('id="ois-plain"') < s.index('id="ois-live-x"'))
ok("MARKETS → INTRADAY explains the day's moves by rules and carries tomorrow's call and range", 'id="sub-intraday"' in s and "function whyMoved(" in s and 'id="why-moved"' in s and 'id="intra-tomorrow"' in s and s.index('<div id="sub-intraday">') < s.index('id="risk-desk"') < s.index('<div id="sub-short"') and "['call-tomorrow','intra-tomorrow']" in s)
ok("the search card speaks in plain words and explains the move", "function plainWords(" in s and "function plainCard(" in s and "copy for WhatsApp" in s and "h+=plainCard(R,V,_sqPerf(R.sym));" in code(fn("function searchAny(q,outId){")) and "whyMoved(R.sym)" in code(fn("function searchAny(q,outId){")))
ok("every listed share is searchable, NSE and BSE, the tabs uncluttered", "n>7000" in code(fn("function _sqDatalist(){")) and "BSE_LIVE" in code(fn("function _sqDatalist(){")) and s.count('class="mi-fold"') >= 10 and "4,600+ listed shares" in s)
ok("investment ideas carry a thesis and the real world, at most two a theme", "function ideasList(" in s and 'id="lt-ideas"' in s and "screener.in/company/" in s and "nseindia.com/get-quotes/equity" in s and "(perTheme[x.theme]||0)>=2" in s)
ok("the trust table sits on BUILD & SIZE as well", "['call-trust','build-trust']" in s and 'id="build-trust"' in s)
ok("the desk's calendar and dials sit under MACRO, the ask bar on Q&A, the book on BUILD & SIZE", s.index('<div id="tab-macro"') < s.index('id="dials"') < s.index('id="desk-top"') < s.index('<div id="tab-ois"') and s.index('<div id="tab-qa"') < s.index('id="ask-desk"') and s.index('<div id="tab-desk">') > s.index('<div id="sub-build"'))
ok("the chart engine draws without layer chips where there are no layers", "const chips=spec.nochips?'':[" in s and "nochips:true" in s)
ok("the page state carries the tape the agents read", all(k in code(fn("function pageState(){")) for k in ("vix:", "vix_pct:", "nifty_d1:", "ad:")))
ok("six agents print their mood, their answer, every reason and the line", "function _agChart(" in s and "WHY I ACTED" in s and "MY MOOD TODAY" in s and "THE TAPE THE AGENTS READ" in s and "why I took it" in s and "function _agEmo(" in s)
ok("the agents' tab holds the books and the balances only; the analysts are on NEWS", s.index('<div id="tab-agents"') < s.index('id="agents-body"') < s.index('id="desk-agents"') < s.index('<div id="tab-news"') < s.index('id="agents-analysts"'))
ok("the trade print is August, dated, not stale", '"period":"Aug 2026"' in s and '"stale":false' in s[s.index("window.TRADE_LIVE"):s.index("window.TRADE_LIVE") + 900] and "(T.overall_deficit_yoy>=0?'+':'')" in s)
ok("the footer says what this is", "MACROINTEL 3 · v148" in s)
_mm = open(R("ml_models.py"), encoding="utf-8").read()
ok("the agents are twelve, each with its capital and its emotion level, a mood and a reason for every action", 'AGENTS_VERSION = "v144.0"' in _mm and "def _ag_mood(" in _mm and "def _ag_answer(" in _mm and "def _ag_market(" in _mm and '"respects_gate"' in _mm and '"emo"' in _mm and '"reason": reason' in _mm and all(('"%s":' % k) in _mm for k in ("cautious", "balanced", "aggressive", "fno", "calls", "tape", "contender", "scalper", "dipbuyer", "contrarian", "macro", "learner")))
ok("the mood changes only the bar, the cap, the size, the ramp and the stops", all(k in _mm[_mm.index("def _ag_mood("):_mm.index("def _ag_answer(")] for k in ("bar =", "cap =", "max_new =", "size_mult =", "stop_mult =")) and "the source decides, the rule sizes" in _mm)
ok("the gate is respected by the careful and crossed by the aggressive, and both say so", "the gate is on — no fresh longs, and I respect it" in _mm and "I took the long anyway" in _mm)
ok("the books restart on a version change, dated and explained", "A.get(\"version\") != AGENTS_VERSION" in _mm and '"restarts"' in _mm)
if os.path.exists(R(".github/workflows/daily-update.yml")):
    _w = open(R(".github/workflows/daily-update.yml"), encoding="utf-8").read()
    ok("the five suites run in CI", all(("python %s" % t) in _w for t in ("t121_safety.py", "t122_validation.py", "t125_desk.py", "t126_desk.py", "t127_env.py")))

# ══ 5p · v141.2 · REAL TIME — four doors a minute, the five-minute file as the floor ══
ok("the browser has four doors to a quote and remembers the first that answers", "const MI_GATEWAYS=" in s and "function _openDoor(" in s and "async function _viaDoor(" in s and "'direct'" in s and "'proxy'" in s and "'gateway'" in s and "NET_FAILED_AT" in s)
ok("one batch call carries every name (spark), per-name chart calls behind it", "async function liveQuotes(" in s and "v8/finance/spark?symbols=" in s and "_chartUrl(s,'1d','5m')" in code(fn("async function liveQuotes(symbols){")))
ok("the sweep never blocks the boot and a door that dies is re-probed", "_openDoor().catch(function(){});" in code(fn("async function netProbe(){")) and "NET_OK=true;" not in code(fn("async function yqNet(url){")) and "NET_DOOR=null;d=await _openDoor();" in code(fn("async function _viaDoor(url){")))
ok("the five-minute file is the floor, accepted only while fresh, under the live door", "async function quotesFile(" in s and 'const MI_QUOTES_URL = "' in s and "age<1200" in code(fn("async function quotesFile(){")) and "L[sym]||Q[sym]" in code(fn("async function liveRefresh(full){")))
ok("the page pulls every minute in the session, every five off it, and on returning to the tab", ",60000);" in code(fn("function startLive(){")) and ",300000);" in code(fn("function startLive(){")) and "visibilitychange" in code(fn("function startLive(){")))
ok("every price says where it came from and when", "function liveBadge(" in s and "⚡ live '+hh+' IST · '+liveDoorName()" in s and "● feed " in s and "no live door from this browser" in s and "function renderHomeTiles(" in s and "live via a public gateway" in s)
ok("the agents' tape reads the batch door first, the file, then the snapshot", "L=await liveQuotes(syms.map(" in code(fn("async function agentsLive(){")) and "Q=await quotesFile();" in code(fn("async function agentsLive(){")) and "src:'snapshot'" in code(fn("async function agentsLive(){")))
ok("the quotes file has its script, its workflow and no secret", os.path.exists(R("quotes.py")) and os.path.exists(R(".github/workflows/quotes.yml")) and all(k in open(R(".github/workflows/quotes.yml"), encoding="utf-8").read() for k in ("*/5 3-10 * * 1-5", "--push", "cancel-in-progress: true", "secrets.GITHUB_TOKEN", "live")) and "yf.download(syms, period=\"5d\"" in open(R("quotes.py"), encoding="utf-8").read() and "[\"git\", \"push\", \"-f\"" in open(R("quotes.py"), encoding="utf-8").read())
ok("the worker door ships with its three steps", os.path.exists(R("worker/mi-proxy.js")) and "access-control-allow-origin" in open(R("worker/mi-proxy.js"), encoding="utf-8").read() and "MI_PROXY" in open(R("worker/mi-proxy.js"), encoding="utf-8").read())
ok("the updater writes the quotes file's URL from the repository", "MI_QUOTES_URL" in open(R("update_terminal.py"), encoding="utf-8").read() and "GITHUB_REPOSITORY" in open(R("update_terminal.py"), encoding="utf-8").read())

# ══ 5q · v142 · THE BROKER FRONT, THE RUPEE, THE MACRO NOTE ═════════════════
ok("HOME opens on the breadth bar and the research recommendations with four rows and MY LIST", "function renderRecs(" in s and 'id="home-recs"' in s and "function _rcBreadth(" in s and all(k in s for k in ("'invest'", "'trade'", "'basket'", "'early'", "'mine'")) and "function miBook(" in s and "localStorage.getItem('mi_list'" in s and "Research Recommendations" in s)
ok("a card carries the live price, the word, the potential, the target, the stop and the horizon", all(k in code(fn("function _rcCard(c){")) for k in ("rc-p", "_rcWord(", "Profit potential", "Target", "Stop", "rc-h")) and "rc-word" in s and "function _rcPx(" in s and "window.LIVE_Q" in s)
ok("investment ideas aim at the 52-week high with the 200-day as the stop; trading ideas carry the desk's stop and 2R", "To the 52-week high" in s and "Stop · 200-day" in s and "x.spot*(1+sg*2*sp/100)" in code(fn("function _rcTrade(){")))
ok("the baskets are the board's themes, equal weight, by turnover", "function _rcBaskets(" in s and "BUY THE BASKET" in s and "AVOID THE BASKET" in s)
ok("the news has three chips, the one-minute read is the note's", "function renderHomeNews(" in s and all(k in s for k in ("'trend'", "'one'", "On my stocks")) and "function noteShort(" in s)
ok("the cards' names ride in the live batch and move in place", "window.__LIVE_EXTRA" in code(fn("async function liveRefresh(full){")) and "function renderRecsLive(" in s)
ok("the macro note is written by rules with a scorecard, the gap table, what would change our mind, the calendar", "function renderMacroNote(" in s and 'id="macro-note"' in s and "function noteScorecard(" in s and "function noteText(" in s and all(k in s for k in ("WHAT THE MARKET PRICES · WHAT THE DATA SAYS · THE GAP", "WHAT WOULD CHANGE OUR MIND", "THE CALENDAR AHEAD", "Our read:")) and s.index('id="macro-top"') < s.index('id="macro-note"') < s.index('id="macro-dials"'))
ok("the rupee tab carries the analysis: measured betas by day and week, the month decomposed, the RBI's hand, the scenarios, the note", "function renderRupee(" in s and 'id="rupee-note"' in s and "function rupeeBetas(" in s and "function rupeeHand(" in s and "function rupeeNote(" in s and all(k in s for k in ("THE BETAS · measured, not assumed", "THE SCENARIOS · the average co-move, not a forecast", "WHAT MOVED IT · the last 20 sessions decomposed", "DEFENDING", "ACCUMULATING", "THE RUPEE NOTE")) and s.index('id="fx-plain"') < s.index('id="rupee-note"'))
ok("the note and the rupee render before HOME so the one-minute read has its line", ",renderShell,renderMacroTop,renderTabTops,renderMacroNote,renderRupee,renderWhyMoved,renderIdeas,renderHome," in s)

# ══ 5r · v143 · THE RESEARCH PAGE, THE CONTENDERS, THE ARENA, THE ASK, THE FEED ═══
ok("tap any name and the research page builds itself in stages, as an overlay, never a tab", "function openShare(" in s and "function _shStages(" in s and "WORKING · building the research on" in s and "el.id='mi-share'" in s and "history.pushState({mi_share:" in s and "function closeShare(" in s and "window.askName=function(q){try{if(q)openShare(q);" in s)
ok("every card, tile and verdict word opens the research page; nothing navigates to MARKETS", "searchAny(\\''+_rcEsc(c.sym)+'\\',\\'float-out\\');floatToggle()" not in s and "openShare(\\''+_rcEsc(c.sym)+'\\')" in s and "openShare(\\''+r.s+'\\')" in s and "onclick=\"openShare(\\''+r.sym+'\\')\"" in s and "window.askName=window.askName||function(q,outId){" in code(fn("function renderSearchBoxes(){")))
ok("the search submit is reachable from the inline handlers and opens the research page (the verdict button works)", "window._sqSubmit=_sqSubmit;" in s and "if(typeof openShare==='function'){openShare(v);" in code(fn("function _sqSubmit(inp,outId){")))
ok("the research page carries the verdict, the long term, the levels, the ask box, three charts, the contenders, the overview, the peers, the industry, the wire, the chain, what would change it", all(k in code(fn("function _shBody(R){")) for k in ("_sqBanner(V,R)", "longTermFor(R,P)", "sh-levels", "assistBox('sh-ask',R)", "shareChart(\\'1d\\')", "shareChart(\\'5y\\')", "contenderCard(R,c,true)", "_shOverview(R,V,P,L)", "_shPeersHtml(R)", "openIndustry(", "_shWireHtml(R)", "nameAnalysis(R.sym)", "WHAT WOULD CHANGE THIS")))
ok("the research page is live: the header price moves with the pass, the 1D chart is the session's bars", "function renderShareLive(" in s and "renderShareLive()" in code(fn("async function liveRefresh(full){")) and "function _shIntraSvg(" in s and "yq(sym,'1d','5m')" in code(fn("function shareChart(which){")))
ok("ask MacroIntel reads the name, the quantity and the cost from a sentence and answers in rupees", "function assistParse(" in s and "function assistDecide(" in s and "function askAssist(" in s and "SELL · THE STOP HAS PRINTED" in s and "BOOK HALF · TRAIL THE REST" in s and "YOUR POSITION" in s and "A DAY\\'S SWING" in s and 'id="home-ask"' in s and "askAssist(question):null)||askAnswer(question)" in code(fn("function askRun(q){")))
ok("MARKETS → INTRADAY is the search, the session, the big movers (last session and live), the contenders and the session's call", 'id="session-card"' in s and 'id="movers-last"' in s and 'id="movers-live"' in s and 'id="contenders"' in s and "function sessionCall(" in s and "RANGE · FADE THE EDGES" in s and "BUY DIPS" in s and "SELL RALLIES" in s and s.index('<div id="sub-intraday">') < s.index('id="session-card"') < s.index('id="movers-last"') < s.index('id="contenders"') < s.index('id="intra-next"'))
ok("SHORT TERM is 5–60 sessions of BUY and SELL cards; the desk's tables say BUY and SELL, never longs and shorts", 'id="short-cards"' in s and "function renderShortCards(" in s and "'▲ BUY · '" in s and "'▼ SELL · '" in s and "'▲ LONGS — '" not in s and "BUY THE SECTOR · 60 sessions" in s and 'id="short-desk"' in s)
ok("LONG TERM is ACCUMULATE cards with the 200-day as the line", 'id="long-cards"' in s and "function renderLongCards(" in s and "Stop · 200-day" in s and 'id="long-desk"' in s)
ok("F&O is the index cards, the chain a tap away, ideas per lot; the desk folded", 'id="fno-index"' in s and 'id="fno-chain-lite"' in s and 'id="fno-ideas"' in s and "function optChainLite(" in s and "function fnoIdeas(" in s and "'FUT-'+r.s+'-'" in s and "pot_lot" in s and "/ lot" in s and 'id="fno-desk-fold"' in s and s.index('id="fno-index"') < s.index('id="fno-ideas"') < s.index('id="fno-desk-fold"') < s.index('id="fno-card"'))
ok("the market lot rides from the bhavcopy", "NewBrdLotQty" in open(R("update_terminal.py"), encoding="utf-8").read())
ok("RESEARCH is a tab with every list, chips, a side filter and the industries", 'id="tab-research"' in s and 'id="research-body"' in s and "function renderResearch(" in s and "function researchLists(" in s and all(k in s for k in ("'invest'", "'trade'", "'cont'", "'fno'", "'basket'", "'early'", "'ind'", "'mine'")) and "buys only" in s)
ok("every industry has an overview: the board, the regime study, the equal-weight index vs the Nifty, the breadth, the squeeze, the leaders", "function openIndustry(" in s and "function industryRow(" in s and "function industryHtml(" in s and "function _inChart(" in s and "function renderIndustries(" in s and "SECTOR_WHY[sec]" in s and "_liveQualify(t)" in code(fn("function industryRow(sec){")) and "EVERY MEMBER WITH A VERDICT" in s)
ok("MACRO opens on THE VIEW by asset class and the indicators that read themselves; CHARTS has them large with the pack", 'id="macro-view"' in s and "function macroView(" in s and "function macroIndicators(" in s and "function renderMacroView(" in s and "function renderChartsTop(" in s and 'id="tab-charts"' in s and 'id="charts-top"' in s and "RATES · DURATION" in s and "OIL · THE SHOCK" in s and "EVERY CHART ON THIS PAGE READS ITSELF" in s.upper())
ok("the arena: twelve books on their own capital, the feed of every action with its minute, what they agree on, the learner's weights", 'id="agents-feed"' in s and "function renderAgentsFeed(" in s and "THE FEED · every action today" in s and "function agentsConsensus(" in s and "THE LEARNER\\'S WEIGHTS" in s and "function agentsLiveFile(" in s and "agents_live.json" in s and "ag.capital||A.capital" in s)
ok("the boot renders the view, the markets, the research and the arena after HOME", ",renderIdeas,renderHome,renderMacroView,renderChartsTop,renderMarkets,renderResearch,renderAgentsFeed,miModeBoot,startLive];" in s)
ok("the page state carries the baskets the macro book trades", "baskets:(typeof basketState==='function')?basketState():[]," in code(fn("function pageState(){")) and "function basketState(" in s)
_mm = open(R("ml_models.py"), encoding="utf-8").read()
ok("the contenders model: movers, direction, Monte Carlo, walk-forward, frozen and scored", "def contenders_model(" in _mm and "def _cont_mc(" in _mm and "def _cont_score_record(" in _mm and "HistGradientBoostingClassifier" in _mm and "CONT_SIG = 1.5" in _mm and "CONT_PATHS = 2000" in _mm and '"contenders": _cont' in _mm and "contenders_%s.json" in _mm and "_WIDE_VOL" in _mm)
ok("the arena in the pipeline: live fills in the session, the floor and the cap, the bandit, the feed's exits reconciled once", "def agents_live_quotes(" in _mm and "def apply_live_exits(" in _mm and "def agents_feed_exits(" in _mm and "AG_BUST_FRAC" in _mm and "AG_CAP_MAX" in _mm and "def _ag_learn(" in _mm and "def _ag_learn_pick(" in _mm and '"intraday": True' in _mm and "the day is over — I never carry a name overnight" in _mm and "mark_at" in _mm and '"env"' in _mm)
ok("the emotion level scales the mood; emotion 0 is an algorithm", "emo = float(D.get(\"emo\") or 0)" in _mm and "kf = 12.0 * (emo / 5.0)" in _mm and "emotion 0 — an algorithm" in _mm)
ok("the quotes feed ticks the arena's stops every minute and never writes the state", "def agents_tick(" in open(R("quotes.py"), encoding="utf-8").read() and "agents_live.json" in open(R("quotes.py"), encoding="utf-8").read() and "never writes it" in open(R("quotes.py"), encoding="utf-8").read())
ok("the live badge offers a door you can paste", "function setLiveDoor(" in s and "localStorage.getItem('mi_proxy')" in s and "onclick=\"setLiveDoor()\"" in s)

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
            os.environ["MI_FORCE_CLOSE"] = "1"      # v137 · the mocks run at any hour; the gate is tested on its own below
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
            ok("tomorrow is modelled, frozen and scored", "def tomorrow_call(" in u and "def score_tomorrow(" in u and '"tomorrow": _TOMORROW' in u and 'ledger["tomorrow_record"] = score_tomorrow(_get, _today)' in u and '"tomorrow": _tmw' in u)
            try:
                _rng = _np.random.default_rng(7); _tix = _pd.bdate_range("2023-09-01", "2026-09-09")
                _wk = lambda mu, sg, p0: _pd.Series(p0 * _np.exp(_np.cumsum(_rng.normal(mu, sg, len(_tix)))), index=_tix)
                _TM = {"nifty": _wk(0.0004, 0.009, 20000), "spx": _wk(0.0004, 0.01, 5000), "inr": _wk(0.0001, 0.003, 88), "brent": _wk(0, 0.02, 80), "ivix": _wk(0, 0.05, 14)}
                mm.yf = None
                _tc = mm.tomorrow_call(_TM, mm.datetime(2026, 9, 9, 18, 5, tzinfo=mm.IST))
                ok("the tomorrow call is a probability with an out-of-sample score", _tc is not None and 0 < _tc["p_up"] < 1 and _tc["direction"] in ("UP", "DOWN") and _tc["n_oos"] >= 200 and _tc["acc_oos"] is not None and _tc["for_session_after"] == "2026-09-09")
                _tc2 = mm.tomorrow_call(_TM, mm.datetime(2026, 9, 9, 11, 20, tzinfo=mm.IST))
                ok("a pass before the close never uses a partial session", _tc2 is not None and _tc2["for_session_after"] < "2026-09-09")
                _wd3 = _tf.mkdtemp()
                _js.dump({"tomorrow": {"for_session_after": "2026-09-01", "direction": "UP", "p_up": 0.6}}, open(os.path.join(_wd3, "pred_2026-09-01.json"), "w"))
                _tr = mm.score_tomorrow(lambda k: _TM["nifty"], "2026-09-09", _wd3)
                ok("the tomorrow record scores against the next close", _tr["n"] == 1 and _tr["rows"][0]["session"] == "2026-09-02" and isinstance(_tr["rows"][0]["hit"], bool))
            except Exception as e:
                F.append("tomorrow: %s" % e)
            ok("the early movers are frozen and scored", '"early": (_PAGE_STATE or {}).get("early")' in u and "def score_early_flags(" in u and 'ledger["early_record"] = score_early_flags(_get, _today)' in u)
            try:
                _wd2 = _tf.mkdtemp()
                _js.dump({"early": {"top": [{"sym": "UP", "name": "Up Co", "side": "LONG", "spot": 100, "stop_pct": 8}, {"sym": "FLAT", "name": "Flat Co", "side": "LONG", "spot": 100, "stop_pct": 8}]}}, open(os.path.join(_wd2, "pred_2026-07-01.json"), "w"))
                _er = mm.score_early_flags(_wg, "2026-09-09", _wd2)
                _eb = {r["sym"]: r for r in _er["rows"]}
                ok("an early mover that runs is scored long (target or the 20th session)", _eb["UP"]["closed_by"] in ("target", "due") and _eb["UP"]["ret_pct"] >= 10.0)
                ok("a flat early mover closes at the 20th session", _eb["FLAT"]["closed_by"] == "due" and _er["h"] == 20)
            except Exception as e:
                F.append("early record: %s" % e)
            # v136 · the three agents roll on synthetic closes: a full setup fills at 5%, a call leaves when the ledger closes it, nothing enters without a close today
            try:
                _ag_led = {"open": [{"id": "stock-long|A|2026-09-09", "model": "stock-long", "name": "A", "key": "A", "side": "LONG", "entry": 100.0, "entry_date": "2026-09-09", "date": "2026-09-09", "stop": 90.0, "target": 120.0, "due": "2026-09-30"}], "closed": []}
                _ag_fs = [{"sym": "B", "name": "B Co", "setup": "SHORT SETUP", "side": "SHORT", "stop_pct": 4.0, "why": "prior + board + book"}]
                _ag_ps = {"early": {"top": [{"sym": "C", "name": "C Co", "side": "LONG", "spot": float(_px["C"].iloc[-1]), "stop_pct": 8}]}}
                _ag_px = dict(_px); _ag_px["NIFTY"] = _px["A"] * 200.0
                _ag_g = lambda k: _ag_px.get(k)
                _A1 = mm.agents_roll({}, _ag_led, _ag_ps, _ag_fs, {"bottom": [{"name": "B", "fno": True}]}, _ag_g, "2026-09-09", "Wed Sep 09, 2026 15:40 IST")
                _nm = lambda k: [p["name"] for p in _A1["agents"][k]["positions"]]
                ok("F&O ONLY takes the setup, MODEL CALLS the call, THE TAPE the early mover", "B Co" in _nm("fno") and "A" in _nm("calls") and "C Co" in _nm("tape"))
                ok("every book sizes its position as a share of its own capital on an unread tape", all(abs(p["notional"] - {"fno": 500000.0, "calls": 500000.0, "tape": 125000.0, "cautious": 150000.0, "balanced": 250000.0, "aggressive": 800000.0}[k]) < 1.0 for k in ("fno", "calls", "tape", "cautious", "balanced", "aggressive") for p in _A1["agents"][k]["positions"]) and all(p.get("reason") for k in _A1["agents"] for p in _A1["agents"][k]["positions"]))
                ok("cash + positions is each book's own capital less costs", all(abs(v["equity"] - v["capital"]) < 5_000 for v in _A1["agents"].values()))
                _A2 = mm.agents_roll(_A1, {"open": [], "closed": [dict(_ag_led["open"][0], closed_by="target", exit=120.0, exit_date="2026-09-09")]}, _ag_ps, [], {}, _ag_g, "2026-09-09", "x")
                ok("MODEL CALLS leaves when the ledger closes the call", "A" not in [p["name"] for p in _A2["agents"]["calls"]["positions"]] and any("ledger closed" in (t.get("why") or "") for t in _A2["agents"]["calls"]["today"]))
                _A3 = mm.agents_roll(_A2, _ag_led, _ag_ps, _ag_fs, {}, _ag_g, "2026-09-10", "x")
                ok("no close today: marked, nothing entered", (not _A3["fresh"]) and not any(t["act"] in ("BUY", "SHORT") for k in _A3["agents"] for t in _A3["agents"][k]["today"]))
                try:
                    os.environ["MI_FORCE_CLOSE"] = "0"
                    _A4 = mm.agents_roll({}, _ag_led, _ag_ps, _ag_fs, {}, _ag_g, "2026-09-09", "x")
                    _gate_ok = (not _A4["fresh"]) if not mm._after_close_ist() else True
                    os.environ["MI_FORCE_CLOSE"] = "1"
                    ok("before 15:35 IST a pass marks and waits — nothing fills on a partial session", "def _after_close_ist(" in u and u.count("and _after_close_ist(") == 2 and _gate_ok)
                except Exception as e:
                    os.environ["MI_FORCE_CLOSE"] = "1"; F.append("close gate: %s" % e)
                ok("the agents block is written and recoverable", "def agents_snapshot(" in u and "def recover_agents(" in u and '_patch_window_block(h, "AGENTS", _agents)' in u)
            except Exception as e:
                F.append("agents: %s" % e)
            # v136 · the dip: a name built to give back after it runs is flagged, with a level, and the flag is scored
            try:
                _rng = _np.random.default_rng(3); _dn, _dk = 700, 30
                _didx = _pd.bdate_range("2023-06-01", periods=_dn); _dX = _np.zeros((_dn, _dk))
                for _j in range(_dk):
                    _r = _rng.normal(0.0006, 0.011, _dn); _p = 100 * _np.exp(_np.cumsum(_r))
                    for _t in range(60, _dn - 12):
                        if _p[_t] > 1.07 * _p[_t-20:_t].mean() and _rng.random() < 0.8:
                            _p[_t+1:_t+11] *= _np.exp(_np.linspace(0, -0.09, 10))
                    _dX[:, _j] = _p
                _dpn = _pd.DataFrame(_dX, index=_didx, columns=["D%02d" % i for i in range(_dk)])
                _dip = mm.dip_model([_dpn, None], "2026-09-09")
                ok("the dip model finds the give-back it was shown", _dip is not None and _dip["auc"] is not None and _dip["auc"] > 0.65 and _dip["n_names"] == _dk)
                ok("every name gets a level at or above the price", all((v["trig_px"] is None) or (v["trig_px"] >= v["last"]) for v in _dip["names"].values()))
                ok("the top flags are frozen and scored at 10 sessions", '"dip": _DIP' in u and 'ledger["dip_record"] = score_dip_flags(_get, _today)' in u and '"dip": _dip' in u)
                _wd3 = _tf.mkdtemp(); _d0 = _didx[-30].strftime("%Y-%m-%d")
                _js.dump({"dip": {"top": [{"sym": "D00", "p": 0.7}, {"sym": "D01", "p": 0.7}]}}, open(os.path.join(_wd3, "pred_%s.json" % _d0), "w"))
                _dr = mm.score_dip_flags(lambda k: _dpn[k] if k in _dpn.columns else None, "2026-09-09", _wd3)
                ok("the dip record scores every flag against the next ten closes", _dr["n"] == 2 and _dr["h"] == 10 and all(isinstance(r["hit"], bool) for r in _dr["rows"]))
            except Exception as e:
                F.append("dip: %s" % e)
            ok("the ledger and the tape agent never take an event name", "def _tape_tag(" in u and 'if x.get("fno") and not x.get("event")][:3]' in u and 'b.get("fno") and not b.get("event")' in u and "EVENT_1D = 12.0" in u)
            try:
                _ev = _pd.DataFrame({"CRASH": [100.0]*20 + [64.0], "CALM": [100.0 + 0.1*i for i in range(21)]}, index=_pd.bdate_range("2026-08-28", periods=21))
                _tg = mm._tape_tag(_ev, "CRASH"); _tc = mm._tape_tag(_ev, "CALM")
                ok("a −36% day is tagged as an event, a quiet tape is not", _tg.get("event") is True and abs(_tg["r1"] + 36.0) < 0.01 and _tc.get("event") is False)
            except Exception as e:
                F.append("event tag: %s" % e)
            ok("next week's contenders: the 5-session horizon over the F&O universe", "horizons=(5, 10, 30)" in u and '"fno-5": 5' in u and 'add("fno-5", p["name"], "LONG"' in u and 'add("fno-5", p["name"], "SHORT"' in u and "_FNO_SYMS" in u)
        except Exception as e:
            F.append("watch record: %s" % e)
        # v132 · the push composes the page's own state and stays silent without a channel
        try:
            spp = importlib.util.spec_from_file_location("pushc", R("push_call.py")); pc = importlib.util.module_from_spec(spp); spp.loader.exec_module(pc)
            _nowp = pc.datetime.now(pc.IST)
            _fs = {"date": _nowp.strftime("%Y-%m-%d"), "page_state": {"regime": "REFLATION", "market_state": "ELEVATED", "cap": "0.75",
                   "dials": {"quad_market": "REFLATION", "mult": 1, "rates_view": "BEAR STEEPENER", "fx_view": "NEUTRAL"},
                   "board": [{"nm": "FMCG / defensives", "action": "UNDERWEIGHT", "conv": "HIGH"}],
                   "watch": {"top": [{"sym": "HINDUNILVR", "name": "Hindustan Unilever", "side": "SHORT", "spot": 2000.0, "stop_pct": 5.0, "agree": 6, "n": 7}]}}}
            _msg = pc.compose(_fs, {"recs": {"total": {"n": 0}, "open_n": 19}})
            ok("the push carries the line, the five and the record", _msg is not None and "REFLATION, the market agrees" in _msg and "Hindustan Unilever SHORT" in _msg and "stop 2,100.00 (5.0%)" in _msg and "target 1,800.00" in _msg and "none closed yet" in _msg)
            ok("a stale page state is not pushed", pc.compose(dict(_fs, date="2020-01-01"), {}) is None)
        except Exception as e:
            F.append("push: %s" % e)
    except Exception as e:
        F.append("ml_models.py would not import: %s" % e)
if os.path.exists(utp):
    u2 = open(utp, encoding="utf-8").read()
    ok("BUILD moved", 'BUILD = "v148"' in u2)
    ok("the analysts run every pass with nine rules, dated and deduplicated", "def analysts_run(" in u2 and all(k in u2 for k in ('"us":', '"events":', '"rates":', '"fx":', '"flows":', '"regime":', '"commod":', '"books":', '"wire":')) and "_patch_window_block(html, \"ALERTS\", _al)" in u2 and "ALERT_KEEP_DAYS" in u2)
    ok("the US agent measures the Nifty's beta to the S&P", "def _an_beta(" in u2 and "the S&P's session before India's" in u2)
    ok("the wire is data: topic and lean per headline", "def news_block(" in u2 and '"NEWS_LIVE":     "window.NEWS_LIVE"' in u2 and '"ALERTS":        "window.ALERTS"' in u2)
    ok("a new Monetary Policy Statement is read, not just flagged", "def _mpc_read_release(" in u2 and "got = _mpc_read_release(newer)" in u2 and "unchanged at" in u2)
    ok("the mail reads only what the pass wrote, once a day, secrets only", os.path.exists(R("send_mail.py")) and all(k in open(R("send_mail.py"), encoding="utf-8").read() for k in ("MAIL_USER", "MAIL_TO", "mail_%s.done", "starttls", "alerts.json", "conv_label")) and not re.search(r"@gmail\.com|@[a-z]+\.[a-z]{2,3}[\"']", open(R("send_mail.py"), encoding="utf-8").read()))
    ok("the alerts push once per item", "def push_alerts(" in open(R("push_call.py"), encoding="utf-8").read() and "alerts_pushed.json" in open(R("push_call.py"), encoding="utf-8").read())
    ok("the live-quote proxy comes from the environment, https only", 'os.environ.get("MI_PROXY")' in u2 and '_mp.startswith("https://")' in u2)
    ok("the BSE bhavcopy is fetched, BSE-only names kept, carried forward with its date", "def fetch_bse(" in u2 and "def _bse_bhavcopy(" in u2 and '"BSE_LIVE":      "window.BSE_LIVE"' in u2 and "read_bse_block(html)" in u2)
    ok("the updater reads the wire's lean for four topics", "def fetch_voices(" in u2 and "def _voice_lean(" in u2 and "_vo = fetch_voices(stamp)" in u2 and "VOICES_TOPICS" in u2)
    ok("the updater writes the intraday snapshot, fail-safe", "def intraday_snapshot(" in u2 and "intraday_snapshot(html, stamp)" in u2 and 'interval="5m"' in u2)
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
    # v136 · the schedule: off-peak minutes, the ML work decided by the firing schedule, five post-close attempts, one push a day
    # v137 · every 90 minutes 08:07 → 20:07 IST, models on every pass, the books gated to the close in code
    ok("the crons run every hour 08:07 → 20:07 IST off the peak minutes, the close pass included", all(("cron: '%s * * 1-5'" % c) in w for c in ("37 2", "37 3", "37 4", "37 5", "37 6", "37 7", "37 8", "37 9", "7 10", "37 10", "37 11", "37 12", "37 13", "37 14")) and w.count("cron: '") == 14 and not re.search(r"cron: '(0|15|30|45) ", w))
    ok("the models run on every pass; the push and the tear sheet are decided by the schedule that fired", "python ml_models.py || true" in w and "prices-only pass" not in w and '"7 10 * * 1-5"|"37 10 * * 1-5"|"37 11 * * 1-5"|"37 12 * * 1-5"|"37 13 * * 1-5"|"37 14 * * 1-5") python push_call.py' in w and '[ "$S" = "37 11 * * 1-5" ] || [ "$S" = "37 12 * * 1-5" ]' in w)
    ok("the live-quote proxy is a repository variable, never a secret", "MI_PROXY: ${{ vars.MI_PROXY }}" in w and "secrets.MI_PROXY" not in w)
    ok("the push goes once a day", 'push_%s.done' in open(R("push_call.py"), encoding="utf-8").read() and "PUSH_FORCE" in open(R("push_call.py"), encoding="utf-8").read())
    ok("the agent snapshots ride to the site", "cp history/agents_*.json _site/history/" in w)
    ok("the alerts are mailed every pass (Telegram optional) and the call is mailed post-close, secrets only", "python send_mail.py --alerts" in w and "python push_call.py --alerts" in w and "python send_mail.py" in w and "MAIL_PASS: ${{ secrets.MAIL_PASS }}" in w and "MAIL_TO: ${{ secrets.MAIL_TO }}" in w and "inputs.mail" in w and "def mail_alerts(" in open(R("send_mail.py"), encoding="utf-8").read())

print("v127 FAILURES: " + ("none" if not F else "\n  - " + "\n  - ".join(F)))
sys.exit(1 if F else 0)
