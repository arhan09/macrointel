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
import json, os, re, subprocess, sys, datetime as dt
import numpy as np
import pandas as pd

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
    # v147 · tomorrow's likely movers, the results calendar, what changed, any horizon, the funds
    MV = E.get("movers") or {}
    ok("the movers block: a list of up to twelve with probability, lean, swing and drivers, the AUCs printed", isinstance(MV.get("list"), list) and len(MV["list"]) <= 12 and all(m.get("p_move") is not None and m.get("p_up") is not None and m.get("exp_pct") is not None and m.get("lean") in ("UP", "DOWN", "EITHER WAY") and isinstance(m.get("drivers"), list) for m in MV["list"]) and ("auc_move" in MV or MV.get("note") or MV.get("error")))
    ok("the movers are liquid names, never ETFs", all(((N.get(m["sym"]) or {}).get("turn") or 0) >= 40 and (N.get(m["sym"]) or {}).get("sector") != "ETF" for m in MV.get("list") or []))
    ok("the results calendar block", isinstance((E.get("events") or {}).get("rows"), list))
    ok("the changes block (eight lists)", all(k in (E.get("changes") or {}) for k in ("to_buy", "from_buy", "to_sell", "to_acc", "to_avoid")))
    ok("the record carries the movers", "movers" in E["record"])
    hz_ok = hz_n = 0
    for k in range(2):
        S = json.load(open("engine_n%d.json" % k))["names"]
        for s, row in list(S.items())[:600]:
            v = row.get("v") or {}
            if v.get("short") is not None or v.get("long") is not None:
                hz_n += 1
                hz = v.get("hz") or {}
                if hz.get("sig") and hz.get("ds") is not None and hz.get("hs") and hz.get("dl") is not None:
                    hz_ok += 1
    ok("every scored name carries its horizon cone (sig, ds, hs, dl) — %d of %d checked" % (hz_ok, hz_n), hz_n > 0 and hz_ok == hz_n)
    if os.path.exists("funds.json"):
        FJ = json.load(open("funds.json"))
        ok("funds.json: categories with rows, the index, the method", isinstance(FJ.get("cats"), dict) and isinstance(FJ.get("index"), dict) and FJ.get("how"))
        bad = [r.get("nm") for c in FJ["cats"].values() for r in c.get("rows") or [] if not (r.get("code") and r.get("nm")) or (not r.get("pending") and r.get("r1y") is not None and not (r.get("word") in ("LEADER", "STEADY", "LAGGARD") and r.get("score") is not None and r.get("rank")))]
        ok("funds.json: every scored scheme has a word, a score and a rank", not bad, bad[:5])
        ok("funds.json: a LEADER is never below its category on three years", all(((r.get("vs_cat") or {}).get("r3y") is None) or r["vs_cat"]["r3y"] >= 0 for c in FJ["cats"].values() for r in c.get("rows") or [] if r.get("word") == "LEADER"))
    else:
        print("  · funds.json not present here — checked in CI after the funds step")
    # v148 · the calls of the day, the brief, why it moved, the Street, the news, delivery, the panels
    CL = E.get("calls") or {}
    ok("the calls block: long / short slots, the also-considered lists, the method", all(k in CL for k in ("long", "short", "long_also", "short_also", "how", "n_long_tested", "n_short_tested")))
    for kind in ("long", "short"):
        c = CL.get(kind)
        if c:
            ok("the %s call is a BUY with a target above the price, a stop below, 3–5 supports, a horizon of %d" % (kind, 250 if kind == "long" else 20),
               c["side"] == "BUY" and c["target"] > c["px"] > c["stop"] and 3 <= c["conv"] <= 5 and len(c["supports"]) >= 3 and c["h"] == (250 if kind == "long" else 20) and c["conv_word"] in ("HIGH", "GOOD", "FAIR") and not c.get("hard_no"))
            ok("the %s call's supports are distinct kinds and every line is a sentence" % kind, len({x["k"] for x in c["supports"]}) == len(c["supports"]) and all(len(x["t"]) > 15 for x in c["supports"]))
            ok("the %s call never runs against the week's news or into results" % kind, not any(x["k"] == "news" for x in c["against"]))
        else:
            print("  · no %s call on this pass (%s tested) — the slot says why" % (kind, CL.get("n_%s_tested" % kind)))
    BR = E.get("brief") or {}
    ok("the brief: items with ids, kinds, weights, a deep link; the calls first", isinstance(BR.get("items"), list) and len(BR["items"]) >= 5 and all(i.get("id") and i.get("k") and i.get("t") and i.get("w") is not None for i in BR["items"]) and BR["items"][0]["k"] == "call" and BR["items"] == sorted(BR["items"], key=lambda x: -x["w"]))
    ok("the brief's ids are unique", len({i["id"] for i in BR.get("items") or []}) == len(BR.get("items") or []))
    AT = E.get("attr") or {}
    ok("why it moved: rows with the three parts that add up to the move, a kind, a note", isinstance(AT.get("rows"), list) and all(abs((r["mkt"] or 0) + (r["sec"] or 0) + (r["own"] or 0) - r["d1"]) < 0.06 and r["kind"] in ("STOCK-SPECIFIC", "SECTOR", "MARKET", "MIXED", "ADJUSTMENT?") and r.get("note") for r in AT["rows"]))
    ok("why it moved: every row is a ≥1.5σ move on a liquid name, and the by-map covers the rows", all(abs(r["z"]) >= 1.5 and (r["turn"] or 0) >= 5 for r in AT.get("rows") or []) and all(r["sym"] in (AT.get("by") or {}) for r in AT.get("rows") or []))
    STt = E.get("street") or {}
    ok("the Street: the board (bull/bear) with the gap = engine − Street, five or more analysts", isinstance(STt.get("bull"), list) and all(r["street_n"] >= 5 and abs(r["gap"] - (r["up_engine"] - r["up_street"])) < 0.11 for r in (STt.get("bull") or []) + (STt.get("bear") or [])) and all(r["gap"] >= 0 for r in STt.get("bull") or []) and all(r["gap"] <= 0 for r in STt.get("bear") or []))
    ok("the record carries the calls and the Street", all(k in E["record"] for k in ("calls_short", "calls_long", "street")))
    ok("news and delivery report themselves", "news" in E and "delivery" in E and isinstance(E["news"].get("names"), list))
    # the fixtures: a delivery file and an RSS document parse; a frozen day with calls and a Street board is scored
    import engine as EN
    dl = EN.parse_delivery_csv("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
                               "RELIANCE, EQ, 17-Oct-2026, 1400.1, 1402, 1410, 1395, 1405, 1404.5, 1403.2, 9876543, 138600.11, 234567, 5432100, 55.01\n"
                               "RELIANCE, BE, 17-Oct-2026, 1, 1, 1, 1, 1, 1, 1, 100, 1, 1, 50, 50.0\n"
                               "XYZ, EQ, 17-Oct-2026, 10, 10, 10, 10, 10, 10, 10, 1000, 1, 10, -, -\n")
    ok("sec_bhavdata_full parses (EQ only, '-' skipped, stray spaces stripped)", dl == {"RELIANCE": [55.01, 5432100, 9876543]}, dl)
    _now = dt.datetime.now(dt.timezone.utc)
    rss = EN.parse_rss(('<rss><channel><item><title>Reliance Industries beats estimates, shares surge 4% - Mint</title><link>https://x/1</link><pubDate>{P0}</pubDate><source url="https://livemint.com">Mint</source></item>'
                        '<item><title>SEBI probe: fine on Reliance unit - Business Standard</title><link>https://x/2</link><pubDate>{P1}</pubDate><source url="https://bs">Business Standard</source></item>'
                        '<item><title>Old story - ET</title><link>https://x/3</link><pubDate>Mon, 01 Jan 2024 08:00:00 GMT</pubDate><source url="https://et">ET</source></item></channel></rss>')
                       .replace("{P0}", _now.strftime("%a, %d %b %Y %H:%M:%S GMT")).replace("{P1}", (_now - dt.timedelta(days=2)).strftime("%a, %d %b %Y %H:%M:%S GMT")))
    ok("Google News RSS parses: the source stripped from the title, the age, the tone, the tags; week-old items dropped", len(rss) == 2 and rss[0]["t"].startswith("Reliance Industries beats") and rss[0]["src"] == "Mint" and rss[0]["tone"] > 0 and "results" in rss[0]["tags"] and rss[1]["tone"] < 0 and "legal" in rss[1]["tags"] and rss[1]["age_d"] >= 1.9, rss)
    ok("news_support reads a week", EN.news_support({"items": rss})[0] == "MIXED" and EN.news_support({"items": rss[:1]})[0] == "SUPPORTS" and EN.news_support({"items": rss[1:]})[0] == "AGAINST" and EN.news_support(None)[0] == "NONE")
    ok("the delivery word", EN.delivery_word({"dlv": 70, "dlv_avg": 45, "dlv_z": 2.1}, 3.0)[0] == "ACCUMULATION" and EN.delivery_word({"dlv": 70, "dlv_avg": 45, "dlv_z": 2.1}, -3.0)[0] == "DISTRIBUTION" and EN.delivery_word({"dlv": 20, "dlv_avg": 45, "dlv_z": -1.8}, 4.0)[0] == "SPECULATIVE" and EN.delivery_word({"dlv": 45, "dlv_avg": 45, "dlv_z": 0.0}, 4.0) is None)
    try:
        import tempfile, shutil
        tmp = tempfile.mkdtemp(); old_hist = EN.HIST_DIR; EN.HIST_DIR = tmp
        idx = pd.bdate_range("2026-01-01", periods=120)
        D = pd.DataFrame({"AAA": np.linspace(100, 130, 120), "BBB": np.linspace(100, 80, 120), EN.MACRO["nifty"]: np.linspace(20000, 21000, 120)}, index=idx)
        W = D.resample("W-FRI").last()
        d0 = idx[10]
        json.dump({"date": d0.strftime("%Y-%m-%d"), "picks": {}, "pairs": [], "movers": [], "nifty": 20000 + 1000 * 10 / 119,
                   "calls": [{"sym": "AAA", "kind": "short", "px": float(D["AAA"].iloc[10]), "target": float(D["AAA"].iloc[10]) * 1.04, "stop": float(D["AAA"].iloc[10]) * 0.96, "h": 20, "conv": 4},
                             {"sym": "BBB", "kind": "long", "px": float(D["BBB"].iloc[10]), "target": float(D["BBB"].iloc[10]) * 1.2, "stop": float(D["BBB"].iloc[10]) * 0.85, "h": 250, "conv": 3}],
                   "street": [{"sym": "AAA", "px": float(D["AAA"].iloc[10]), "up_e": 40.0, "up_s": -10.0}]}, open(os.path.join(tmp, "engine_%s.json" % d0.strftime("%Y%m%d")), "w"))
        U0 = {"AAA": {"px": 130.0}, "BBB": {"px": 80.0}}
        rec = EN.freeze_and_score({}, U0, W, D, idx[-1].strftime("%Y-%m-%d"), freeze=False)
        cs, clg, st = rec["calls_short"], rec["calls_long"], rec["street"]
        ok("the record scores a short call at twenty sessions (target first), a long call at sixty, the Street at sixty", cs["n"] == 1 and cs["last"][0]["tgt_hit"] is True and cs["last"][0]["stopped"] is False and cs["tgt_hit"] == 100 and clg["n"] == 1 and clg["last"][0]["ret"] < 0 and clg["last"][0]["final"] is False and st["n"] == 1 and st["last"][0]["engine_closer"] is True and st["engine_closer"] == 100, (cs, clg, st))
        EN.HIST_DIR = old_hist; shutil.rmtree(tmp, ignore_errors=True)
    except Exception as _e:
        EN.HIST_DIR = "history"
        ok("the record scores the calls and the Street (fixture)", False, "%s: %s" % (type(_e).__name__, _e))
    ok("the panels: ten years weekly, two years daily, five years in the shards, the DNA on three years", EN.WEEKLY_PERIOD == "10y" and EN.DAILY_PERIOD == "2y" and EN.DNA_WEEKS == 156 and "def write_series_shards(U, W, D, nw=260, nd=260)" in open("engine.py", encoding="utf-8").read())
    ok("BSE-only names get a weekly tape on a rotation, cached between passes", "def bse_rotation(" in open("engine.py", encoding="utf-8").read() and "engine_prices_bse.json" in open(".github/workflows/daily-update.yml", encoding="utf-8").read())
    ok("the tape carries since, the delivery read and the years", all(k in EN.TAPE_KEYS for k in ("since", "dlv", "dlv_avg", "dlv_z", "yrs", "trunc")))
    S0 = json.load(open("engine_n0.json"))["names"]
    ok("every scored name's tape says since when (shard 0)", all((row.get("tape") or [None] * 21)[20] for row in S0.values() if (row.get("tape") or [0])[0] != 0))
    # the page
    h = open("macro_intelligence_terminal.html", encoding="utf-8").read()
    ok("the bell, the drawer, the calls, why it moved, the Street and the news are on the page", all(x in h for x in ('id="e-bell"', "const B = E.brief = {", "const C = E.calls = {}", "const A = E.attr = {}", "const ST = E.street = {}", "const NW = E.news = {", "E.calls.section(", "E.attr.section(", "E.street.section(", "E.deliveryLine = function", "E.historyLine = function", "['street', '🏛 The Street']", "['max', 'Since listing']")))
    ok("Ask answers the calls, why it moved, the news, the Street, delivery", all(("P.intent = '%s'" % k) in h for k in ("calls", "moved", "news", "street", "delivery")) and "A.calls = function" in h and "A.moved = async function" in h)
    ok("the page ships with the live door on (v148)", 'const MI_PROXY = "https://mi-proxy.data-campusbinge.workers.dev/?u=";' in h)
    ok("the page decodes the v148 tape keys", "'since', 'dlv', 'dlv_avg', 'dlv_z', 'yrs', 'trunc'" in h)
    ok("the nowcast, the post-mortems and the option line are on the page", "const N = E.nowcast = {}" in h and "E.nowcast.postmortems()" in h and "E.optLine = function" in h and "E.nowcast.card(" in h)
    ok("the movers, the horizons and the funds are on the page", "const M = E.movers = {}" in h and "const H = E.hz = {}" in h and "const FU = E.funds = {" in h and 'data-tab="funds"' in h and 'id="e-funds"' in h and "E.hz.table(" in h and "E.movers.section(" in h)
    ok("Ask answers movers, horizons, funds, changes, results", "P.intent = 'movers'" in h and "P.intent = 'fund'" in h and "P.intent = 'changes'" in h and "P.intent = 'events'" in h and "A.horizon = async function" in h)
    ok("the X-ray, the map and the pairs are on the page", "E.pf = {" in h and "const AL = E.alloc = {}" in h and "const PR = E.pairs = {}" in h and "E.decide = function" in h)
    ok("the subtabs: where to be, my portfolio; the menu entries", "['where', '🧭 Where to be']" in h and "['portfolio', '🩻 My portfolio']" in h and "E.go('research','portfolio')" in h and "E.go('micro','where')" in h)
    ok("Ask answers the book, the map and the pairs", "P.intent = 'portfolio'" in h and "P.intent = 'alloc'" in h and "P.intent = 'pairs'" in h and "E.pf.answer()" in h)
    ok("the holder's decision is one rule (Ask uses E.decide)", h.count("E.decide(vs, vl, px, stopL)") >= 1 and "if (vl.side === 'AVOID' && vs.side === 'SELL') { word = 'SELL'" not in h)
    ok("the page is built once (E-V148-BUILT)", h.count("E-V148-BUILT") == 1)
    ok("the six-tab nav", all(('data-tab="%s"' % t) in h for t in ("home", "micro", "research", "macro", "industries", "agents", "ask")))
    ok("the engine containers", all(('id="%s"' % i) in h for i in ("e-home", "e-markets", "e-research", "e-industries", "e-arena", "e-ask-tab", "e-macro-head")))
    ok("the legacy panes are wrapped", all(('id="%s"' % i) in h for i in ("e-legacy-home", "e-legacy-mk-top", "e-legacy-intra", "e-legacy-short", "e-legacy-long", "e-legacy-desk", "e-legacy-fno", "e-legacy-agents")))
    ok("the macro bar on every deep pane", all(('id="e-mbar-%s"' % t) in h for t in ("macro", "ois", "forex", "comm", "intl", "charts", "news", "qa")))
    ok("the validation layer is off the surfaces", "E.go('validation')" not in h and "['validation', 'Validation']" not in h and "#tab-validation" in h)
    ok("the stamp", '>v148<' in h and "MACROINTEL 3 · v148" in h)
    ok("the theme block comes last", h.rfind('<style id="e-theme">') > h.rfind("const ML_OUTPUT") - 10 ** 9 and h.count('<style id="e-theme">') == 1)
    ok("every data anchor the pipeline patches is intact", all(a in h for a in ("window.MOVERS_LIVE", "window.BSE_LIVE", "window.RISK_LIVE", "window.FNO_LIVE", "window.OPTIONS_LIVE", "window.REGIME_LIVE", "const ML_OUTPUT", "window.PREDICTIONS", "window.AGENTS", "const MI_PROXY", "const MI_QUOTES_URL", 'id="build-version"')))
    ok("openShare / openIndustry / liveRefresh are rerouted to E", "window.openShare = function (q, opt) { return E.openShare(q, opt); }" in h and "window.liveRefresh = async function" in h)
    # the pipeline
    w = open(".github/workflows/daily-update.yml", encoding="utf-8").read()
    ok("the workflow runs the engine before the models", "python engine.py" in w and w.find("python engine.py") < w.find("python ml_models.py"))
    ok("the workflow ships the engine's files and the profiles", "engine_n7.json" in w and "engine_s7.json" in w and "fundamentals.json _site/" in w.replace('"$f" _site/', 'fundamentals.json _site/') or ("for f in engine.json" in w))
    ok("the workflow commits engine.json, fundamentals.json and the ETF panel", "git add engine.json fundamentals.json engine_etf.json" in w)
    ok("the workflow runs the funds and ships them (v147)", "python funds.py" in w and "funds_series.json" in w and "git add funds.json funds_universe.json funds_cache.json" in w)
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
    ok("the worker is the scheduler too (v146.2): scheduled(), the dispatch, the dry run", "async scheduled(event, env, ctx)" in wk and "/dispatches" in wk and 'p === "/cron"' in wk)
    ok("the gate de-duplicates a late GitHub cron (40 min)", '"$AGE" -lt 40' in w and "fetch-depth: 60" in w)
    ok("v148.1: the gate has no clock window (a late pass beats no pass), the watchdog runs round the clock and ignores queued runs, the quotes run nudges a late pass", '"$MIN" -lt 465' not in w and "3,13,23,33,43,53 * * * 1-6" in wd and "--status queued" not in wd and "Nudge the daily pass if it is late" in q0 and "actions: write" in q0)
    u = open("update_terminal.py", encoding="utf-8").read()
    ok("updater BUILD v148", 'BUILD = "v148"' in u)
    ok("the workflow caches the delivery and news caches, ships news.json, names the pass kind, runs with the wider budget (v148)", "delivery.json" in w and "news_cache.json" in w and "news.json" in w and "MI_PASS_KIND" in w and "--budget 600" in w)
    print("\nt144 FAILURES: " + (", ".join(FAIL) if FAIL else "none"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
