# MacroIntel v146 — the nowcast (the regime as probabilities), the option on every F&O idea, the macro post-mortems

A drop-in over v145 / v145.1 (same file names). Everything in `README-v145.md` still holds — the X-ray, Where to be, the pairs, the pipeline fixes (the watchdog, the gate, the pass log) — this file covers only what v146 adds.

**Upload** at the repo root: `macro_intelligence_terminal.html` · `engine.py` · `update_terminal.py` · `t121_safety.py` · `t122_validation.py` · `t125_desk.py` · `t126_desk.py` · `t127_env.py` · `t144_engine.py` · `build_v144.py` + the `v144/` folder *(new: `e-nowcast.js`)* · `.github/workflows/` (all three) · `README-v146.md` (delete `README-v145.md`). `ml_models.py`, `quotes.py`, `fno_setups.py`, `push_call.py`, `send_mail.py`, `tearsheet.py`, `worker/mi-proxy.js` are unchanged from v145 — upload them too if you are coming straight from v141. Then **Actions → Daily Terminal Update → Run workflow**. Six suites green; t144 carries 7 more checks.

---

## 1 · The nowcast — the regime as four probabilities (Macro tab, Home, Where to be)

The official regime label (CPI × IIP) is monthly and late. v146 measures what the market is pricing *this quarter* and turns the quadrant into probabilities:

- **Three impulses**, each a thirteen-week change z-scored against its own history since 2015 (the twelve-year panel behind Where to be, now carrying Brent, India VIX, the dollar index and the US 10-year too):
  - *growth* — cyclicals against defensives (auto, metals, banks, realty, infra vs FMCG, pharma, IT), midcaps against the Nifty, the Nifty itself;
  - *inflation* — Brent in rupees, USD/INR, gold in rupees, the 5-year gilt (price down = yields up);
  - *liquidity* — the gilt bid, India VIX (down = easier), banks against the Nifty, the dollar (down = easier for EM).
- **The nowcast**: official CPI and IIP are the anchor; one σ of inflation impulse nudges CPI by 0.4 points, one σ of growth impulse nudges IIP by 1.2 points (a judgment, printed as such). The quadrant lines (CPI 4, IIP 3) become probabilities through a logistic with the series' own noise: P(inflation above 4%) × P(growth above 3%) and the three complements → Reflation · Goldilocks · Stagflation · Disinflation, adding to 100.
- **What it changes, and what it does not**: the label on the page stays the official one — the sector edges, the regime record on every share, the shock presets all read it, so nothing contradicts. The probabilities are the market's lean: the **model book on Where to be blends its base weights by them** (so it never jumps on a label change), and the lean is shown next to the label ("official Reflation · the market leans Reflation 82% — in agreement" or "— against the label"). Ask: "where are we", "regime".

## 2 · The option on every F&O idea (F&O & pairs, Research → Top picks, the research page, Ask)

Every futures idea now carries a defined-risk spread **priced off the real chain** (`options_chain.json`, written by `update_terminal.py` every pass from the bhavcopy's closing premiums — every strike, every expiry): a BUY becomes a **bull call spread** (buy the strike at the spot, sell the strike at the engine's target), a SELL a **bear put spread**. The line gives the expiry chosen for the idea's horizon, both strikes, the debit per lot, the maximum per lot, reward-to-risk, the breakeven, the probability the spot settles past breakeven (lognormal, ATM IV), the IV, and the naked alternative. Lots are sized so the debit is the 1% rule; when one lot already risks more than that the line says so and points back to the future as the sized expression. On a pass where the chain is not on disk the same spread is priced by Black-Scholes off the ATM IV the page already carries, and is labelled *theoretical*.

## 3 · The macro post-mortems (Macro tab, Markets → Records)

Every pass freezes the macro call with the day: the regime, its probabilities, the session's call (BUY DIPS / SELL RALLIES / RANGE), the gate, the OVERWEIGHT and UNDERWEIGHT sleeves, the model book and the sleeves' prices (`history/engine_<date>.json → macro`). Five sessions later it is scored: was the call right (BUY DIPS → the Nifty rose; SELL RALLIES → fell; RANGE → moved under 1.5%), what the model book paid against the Nifty, and the OVERWEIGHT sleeves minus the UNDERWEIGHT ones. The Macro tab shows the hit rate, the averages and the last twelve rows with each day's probability bar; the record strip on Home and Research carries *The macro call · 5 sessions*. The first row prints five sessions after the first v146 pass — nothing is graded before its time.

## 4 · Still not there

A broker's real-time feed (the worker gives Yahoo's ~15-minute-delayed quotes; a Zerodha/Upstox/Dhan API key would make the same door real-time — a one-file change when you want it). An official nowcast from GST, PMI, e-way bills and power demand (the market-implied one above is what free data allows reliably every hour).

## 5 · Files that changed

`engine.py` (v146: `option_structure` + `load_chain`, `nowcast_block`, probability-blended `alloc_block`, the macro freeze and score in `freeze_and_score`, `EXTRA_PANEL`) · `v144/e-nowcast.js` *(new)* · `v144/e-macro.js` · `v144/e-markets.js` · `v144/e-alloc.js` · `v144/e-share.js` · `v144/e-ask.js` · `v144/theme.css` · `build_v144.py` · `t144_engine.py` · `update_terminal.py` (`BUILD = "v146"`) · the five older suites (stamp). The arena's rules are unchanged (`AGENTS_VERSION` stays `v144.0`).
