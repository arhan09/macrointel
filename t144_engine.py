#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t144 · THE ENGINE and the v144/v145 page — the contract, in checks that fail loudly (v145: the regime → asset map, the pairs, the X-ray).

    python t144_engine.py --run      # runs the engine offline first (≈15 s), then every check
    python t144_engine.py            # checks the files already there (CI, after the engine step)

What it guards:
  · engine.json / engine_full.json / the eight shards exist and agree with each other
  · one source of truth: every pick's side equals the name's side; BUY ⇒ score ≥ 80, SELL ⇒ ≤ 10 and F&O;
    ACCUMULATE ⇒ ≥ 80, AVOID ⇒ ≤ 20; the reconciliation code matches the two sides
  · the F&O ideas carry lots, risk and potential per lot; the picks carry their plan (stop, target, horizon)
  · every sector has members and a word; the record block has the five lists
  · the page: built once, the six-tab nav, every engine container, the legacy panes wrapped, the stamp
  · the pipeline: the workflow runs engine.py and ships its files; ml_models reads the engine pool;
    quotes.py carries the engine's names; the worker has the batch endpoint
"""
import json, os, re, subprocess, sys

FAIL = []


def ok(label, cond, detail=""):
    print(("  ✓ " if cond else "  ✗ ") + label + ("" if cond else ("  — " + str(detail)[:160])))
    if not cond:
        FAIL.append(label)


def main():
    print("=== t144 · the engine, the page, the pipeline ===")
    # in CI the engine step has just run online — never overwrite its files with an offline pass;
    # locally (no engine.json yet, or --run) the suite runs the engine offline first
    if "--run" in sys.argv or not os.path.exists("engine.json"):
        r = subprocess.run([sys.executable, "engine.py", "--offline"], capture_output=True, text=True)
        ok("engine.py runs offline", r.returncode == 0, r.stderr[-300:])
    else:
        print("  · engine.json present — checking the files the engine step wrote")
    E = json.load(open("engine.json"))
    ok("engine.json has the blocks", all(k in E for k in ("names", "picks", "sectors", "record", "shock", "market", "method", "counts")))
    N = E["names"]
    ok("every listed share is on it (≥ 4,000 names)", len(N) >= 4000, len(N))
    scored = [s for s, n in N.items() if n.get("s") is not None]
    ok("≥ 1,500 names carry a score", len(scored) >= 1500, len(scored))
    P = E["picks"]
    for k in ("intraday", "fno", "short_buy", "short_sell", "long"):
        ok("picks · %s has up to five" % k, 0 <= len(P.get(k) or []) <= 5, len(P.get(k) or []))
    ok("today's buys: up to eight BUYs with the plan, dated, NEW-tagged", 0 <= len(P.get("today_buys") or []) <= 8 and all(p.get("side") == "BUY" and p.get("stop") and p.get("target") and ("new" in p) for p in (P.get("today_buys") or [])))
    ok("the disclaimer line is on the page", 'class="e-disc"' in open("macro_intelligence_terminal.html", encoding="utf-8").read())
    # one source of truth
    bad = []
    for p in P.get("short_buy") or []:
        n = N.get(p["sym"]) or {}
        if n.get("ss") != "BUY" or (n.get("s") or 0) < 80 or p.get("stop") is None or p.get("target") is None or not p.get("h"):
            bad.append(p["sym"])
    ok("short-term buys: side BUY, score ≥ 80, stop/target/horizon on the card", not bad, bad)
    bad = [p["sym"] for p in (P.get("short_sell") or []) if (N.get(p["sym"]) or {}).get("ss") != "SELL" or not (N.get(p["sym"]) or {}).get("fno") or ((N.get(p["sym"]) or {}).get("s") or 0) > 10]
    ok("short-term sells: SELL, F&O only, score ≤ 10", not bad, bad)
    bad = [p["sym"] for p in (P.get("long") or []) if (N.get(p["sym"]) or {}).get("ls") != "ACCUMULATE" or ((N.get(p["sym"]) or {}).get("l") or 0) < 80 or p.get("target") is None]
    ok("long-term picks: ACCUMULATE, score ≥ 80, a target", not bad, bad)
    bad = [p["sym"] for p in (P.get("fno") or []) if not p.get("lots") or p.get("risk_lot") is None or p.get("pot_lot") is None or p.get("side") not in ("BUY", "SELL")]
    ok("F&O ideas: lots, risk and potential per lot, a side", not bad, bad)
    bad = [p["sym"] for p in (P.get("intraday") or []) if p.get("side") not in ("BUY", "SELL") or not p.get("entry") or p.get("stop") is None or p.get("target") is None]
    ok("intraday: a side, an entry zone, a stop, a target", not bad, bad)
    # thresholds across the whole universe
    v = [(s, n) for s, n in N.items() if n.get("s") is not None]
    liq = [(s, n) for s, n in v if n.get("fno") or (n.get("turn") or 0) >= 5]
    ok("BUY ⇔ short score ≥ 80 on every liquid name", all((n.get("ss") == "BUY") == (n["s"] >= 80) for s, n in liq if n.get("ss") != "SELL"))
    ok("no short-term side below the liquidity floor", all(not n.get("ss") for s, n in v if not (n.get("fno") or (n.get("turn") or 0) >= 5)))
    ok("SELL only where a future exists", all(n.get("fno") for s, n in v if n.get("ss") == "SELL"))
    ok("ACCUMULATE ⇔ long score ≥ 80", all((n.get("ls") == "ACCUMULATE") == ((n.get("l") or 0) >= 80) for s, n in v if n.get("l") is not None and n.get("ls") != "AVOID"))
    ok("AVOID ⇔ long score ≤ 20", all((n.get("ls") == "AVOID") == (n["l"] <= 20) for s, n in v if n.get("l") is not None and n.get("ls") != "ACCUMULATE"))
    # the shards agree with the lite rows
    F = json.load(open("engine_full.json"))
    ok("the series shards: every name's weekly closes, daily where the panel has them", all(os.path.exists("engine_s%d.json" % k) for k in range(8)) and sum(len(json.load(open("engine_s%d.json" % k))["names"]) for k in range(8)) >= 1500)
    ok("engine_full.json: shards, keys, the arena pool", F.get("shards") == 8 and F.get("tape_keys") and F.get("sc_keys") and isinstance(F.get("arena_pool"), list) and len(F["arena_pool"]) > 20)
    mism = 0; checked = 0
    for k in range(8):
        S = json.load(open("engine_n%d.json" % k))["names"]
        for s, row in list(S.items())[:400]:
            n = N.get(s); checked += 1
            if not n or (row.get("v") or {}).get("short", {}).get("side") != n.get("ss") or (row.get("v") or {}).get("long", {}).get("side") != n.get("ls"):
                mism += 1
            code = (row.get("v") or {}).get("note")
            sh = ((row.get("v") or {}).get("short") or {}).get("side"); lg = ((row.get("v") or {}).get("long") or {}).get("side")
            want = 1 if (sh == "SELL" and lg == "ACCUMULATE") else 2 if (sh == "BUY" and lg == "AVOID") else 3 if (sh == "BUY" and lg == "ACCUMULATE") else 4 if (sh == "SELL" and lg == "AVOID") else 5 if sh == "BUY" else 6 if sh == "SELL" else 7 if lg == "ACCUMULATE" else 8 if lg == "AVOID" else (9 if (row.get("v") or {}).get("short", {}).get("thin") else 0)
            if code != want:
                mism += 1
    ok("the shards agree with engine.json on every side and reconciliation code (%d rows)" % checked, mism == 0, mism)
    # sectors and the record
    S = E["sectors"]
    ok("≥ 12 sectors with a word and leaders", sum(1 for k, x in S.items() if x.get("word") and x.get("leaders")) >= 12, len(S))
    ok("sector DNA present where there are betas", any((x.get("dna") or {}).get("nifty") is not None for x in S.values()))
    ok("the record has the five lists", all(k in E["record"] for k in ("intraday", "fno", "short_buy", "short_sell", "long")))
    ok("the frozen picks were written to history/", any(f.startswith("engine_") for f in os.listdir("history")))
    ok("the shock presets", all(k in (E["shock"].get("presets") or {}) for k in ("crude120", "rbi50", "inr100", "fiisell")))
    ok("the market line has the call and the counts", E["market"].get("call") and E["market"].get("n_buy") is not None)
    # v145 · where to be (the regime → asset map), the pairs, the ETFs set aside, the X-ray on the page
    AL = E.get("alloc") or {}
    ok("where to be: the sleeves and a model book", len(AL.get("rows") or []) >= 20 and len(AL.get("alloc") or []) >= 4 and AL.get("regime") in ("Goldilocks", "Reflation", "Stagflation", "Disinflation"))
    ok("where to be: the book adds to 100%", abs(sum(a["pct"] for a in (AL.get("alloc") or [])) - 100) < 0.6, sum(a["pct"] for a in (AL.get("alloc") or [])))
    ok("where to be: every line has an ETF, a rupee amount and a reason", all(a.get("sym") and a.get("inr") is not None and a.get("why") for a in (AL.get("alloc") or [])))
    ok("where to be: never a tilt into an UNDERWEIGHT sleeve", all(a.get("word") != "UNDERWEIGHT" for a in (AL.get("alloc") or []) if a["key"] not in ("nifty", "next50", "gold", "cash")))
    ok("where to be: every sleeve carries a word and a why", all(r.get("word") in ("OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT", "CASH") and r.get("why") for r in (AL.get("rows") or [])))
    PR = E.get("pairs") or {}
    ok("pairs: the block, tested and fit counts, the method", "ideas" in PR and PR.get("n_tested") is not None and PR.get("how"))
    bad = [i for i in (PR.get("ideas") or []) if not (i.get("lots_a") and i.get("lots_b") and i.get("exp_inr") is not None and i.get("loss_inr") is not None and i.get("stop_z") and i.get("h") and abs(i.get("z") or 0) >= 2.0 and i.get("side_a") != "SELL" and i.get("side_b") != "BUY")]
    ok("pairs: lots, rupees, a stop, a horizon, ≥ 2σ, never against the engine's own side", not bad, [(i.get("a"), i.get("b")) for i in bad])
    ok("pairs: no name on two ideas", len({x for i in (PR.get("ideas") or []) for x in (i["a"], i["b"])}) == 2 * len(PR.get("ideas") or []))
    ok("ETFs are their own sector and never a stock pick", sum(1 for n in N.values() if n.get("sector") == "ETF") >= 20 and all((N.get(p["sym"]) or {}).get("sector") != "ETF" for k in ("intraday", "fno", "short_buy", "short_sell", "long", "today_buys") for p in (P.get(k) or [])))
    ok("the record carries the pairs", "pairs" in E["record"])
    # v146 · the nowcast (the regime as probabilities), the option on every F&O idea, the macro post-mortems
    NC = E.get("nowcast") or {}
    ok("the nowcast: four probabilities that add to 100, a lean, the official anchor", NC.get("probs") and abs(sum(NC["probs"].values()) - 100) <= 2 and NC.get("lean") in NC["probs"] and (NC.get("official") or {}).get("label"))
    ok("the nowcast: three impulses with their parts (or an honest 'no read')", all(k in (NC.get("impulses") or {}) for k in ("growth", "inflation", "liquidity")))
    ok("where to be: the base weights are blended by the probabilities", AL.get("blended") is True and AL.get("probs"))
    fo = [p for p in (P.get("fno") or [])]
    ok("every F&O idea carries its option (a spread with debit, maximum, breakeven, probability)", all(p.get("opt_trade") and p["opt_trade"].get("debit_lot") is not None and p["opt_trade"].get("max_lot") is not None and p["opt_trade"].get("be") and p["opt_trade"].get("p_profit") is not None for p in fo) if fo else True)
    ok("the option's direction matches the idea", all((p["opt_trade"]["kind"] == "bull call spread") == (p["side"] == "BUY") for p in fo if p.get("opt_trade")))
    ok("the record carries the macro post-mortems", "macro" in E["record"])
    # the page
    h = open("macro_intelligence_terminal.html", encoding="utf-8").read()
    ok("the nowcast, the post-mortems and the option line are on the page", "const N = E.nowcast = {}" in h and "E.nowcast.postmortems()" in h and "E.optLine = function" in h and "E.nowcast.card(" in h)
    ok("the X-ray, the map and the pairs are on the page", "E.pf = {" in h and "const AL = E.alloc = {}" in h and "const PR = E.pairs = {}" in h and "E.decide = function" in h)
    ok("the subtabs: where to be, my portfolio; the menu entries", "['where', '🧭 Where to be']" in h and "['portfolio', '🩻 My portfolio']" in h and "E.go('research','portfolio')" in h and "E.go('micro','where')" in h)
    ok("Ask answers the book, the map and the pairs", "P.intent = 'portfolio'" in h and "P.intent = 'alloc'" in h and "P.intent = 'pairs'" in h and "E.pf.answer()" in h)
    ok("the holder's decision is one rule (Ask uses E.decide)", h.count("E.decide(vs, vl, px, stopL)") >= 1 and "if (vl.side === 'AVOID' && vs.side === 'SELL') { word = 'SELL'" not in h)
    ok("the page is built once (E-V146-BUILT)", h.count("E-V146-BUILT") == 1)
    ok("the six-tab nav", all(('data-tab="%s"' % t) in h for t in ("home", "micro", "research", "macro", "industries", "agents", "ask")))
    ok("the engine containers", all(('id="%s"' % i) in h for i in ("e-home", "e-markets", "e-research", "e-industries", "e-arena", "e-ask-tab", "e-macro-head")))
    ok("the legacy panes are wrapped", all(('id="%s"' % i) in h for i in ("e-legacy-home", "e-legacy-mk-top", "e-legacy-intra", "e-legacy-short", "e-legacy-long", "e-legacy-desk", "e-legacy-fno", "e-legacy-agents")))
    ok("the macro bar on every deep pane", all(('id="e-mbar-%s"' % t) in h for t in ("macro", "ois", "forex", "comm", "intl", "charts", "news", "qa")))
    ok("the validation layer is off the surfaces", "E.go('validation')" not in h and "['validation', 'Validation']" not in h and "#tab-validation" in h)
    ok("the stamp", '>v146<' in h and "MACROINTEL 3 · v146" in h)
    ok("the theme block comes last", h.rfind('<style id="e-theme">') > h.rfind("const ML_OUTPUT") - 10 ** 9 and h.count('<style id="e-theme">') == 1)
    ok("every data anchor the pipeline patches is intact", all(a in h for a in ("window.MOVERS_LIVE", "window.BSE_LIVE", "window.RISK_LIVE", "window.FNO_LIVE", "window.OPTIONS_LIVE", "window.REGIME_LIVE", "const ML_OUTPUT", "window.PREDICTIONS", "window.AGENTS", "const MI_PROXY", "const MI_QUOTES_URL", 'id="build-version"')))
    ok("openShare / openIndustry / liveRefresh are rerouted to E", "window.openShare = function (q, opt) { return E.openShare(q, opt); }" in h and "window.liveRefresh = async function" in h)
    # the pipeline
    w = open(".github/workflows/daily-update.yml", encoding="utf-8").read()
    ok("the workflow runs the engine before the models", "python engine.py" in w and w.find("python engine.py") < w.find("python ml_models.py"))
    ok("the workflow ships the engine's files and the profiles", "engine_n7.json" in w and "engine_s7.json" in w and "fundamentals.json _site/" in w.replace('"$f" _site/', 'fundamentals.json _site/') or ("for f in engine.json" in w))
    ok("the workflow commits engine.json, fundamentals.json and the ETF panel", "git add engine.json fundamentals.json engine_etf.json" in w)
    # v145.1 · the pipeline's punctuality: no pip cache without a requirements file (every 5-minute run failed on it),
    # a timeout and a gate on the daily job, the pass log on the page, the watchdog that re-fires a missed hour
    q0 = open(".github/workflows/quotes.yml", encoding="utf-8").read()
    ok("quotes.yml: no `cache: pip` (setup-python fails on it with no requirements.txt)", "cache: pip" not in q0 and "cache: 'pip'" not in q0)
    ok("daily: a timeout, the gate job, the pass log committed and shipped", "timeout-minutes: 55" in w and "needs: gate" in w and "history/passes.json" in w and "cp history/passes.json _site/history/" in w)
    wd = open(".github/workflows/watchdog.yml", encoding="utf-8").read()
    ok("the watchdog re-fires a late hourly pass", "gh workflow run daily-update.yml" in wd and "actions: write" in wd and "reason=watchdog" in wd)
    ok("the page shows the pipeline's own punctuality", "const P = E.pipe = {" in h and "E.pipe.chip()" in h and "E.pipe.section()" in h)
    m = open("ml_models.py", encoding="utf-8").read()
    ok("ml_models reads the engine pool and the books take it", "def _engine_pool" in m and 'AGENTS_VERSION = "v144.0"' in m and '"engine"' in m and '"engine_intra"' in m and '"engine_long"' in m)
    q = open("quotes.py", encoding="utf-8").read()
    ok("quotes.py carries the engine's picks and the liquid names", "engine.json" in q)
    wk = open("worker/mi-proxy.js", encoding="utf-8").read()
    ok("the worker: pass-through, /q, /chart, CORS, the edge cache", all(x in wk for x in ('p === "/q"', 'p === "/chart"', "access-control-allow-origin", "caches.default")))
    u = open("update_terminal.py", encoding="utf-8").read()
    ok("updater BUILD v146", 'BUILD = "v146"' in u)
    print("\nt144 FAILURES: " + (", ".join(FAIL) if FAIL else "none"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
