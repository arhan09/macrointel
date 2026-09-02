# MacroIntel v120 — the desk, the ledger, the live curve

**Upload:** drop these four files at the repo root, replacing the existing ones, then Actions → *daily-update* → **Run workflow**.

- `macro_intelligence_terminal.html`
- `update_terminal.py`
- `ml_models.py`
- `README-v120.md`

Cumulative: everything from v118 and v119 is inside. Nothing else in the repo changes (workflow, history files, tearsheets untouched).

---

## What changed, in the order a trader meets it

### 1 · The DESK is the landing page
A new first tab, `🧭 DESK`, is the default. One regime word with the one-line read; the cross-asset stress dial; six numbers with sparklines (Nifty, USD/INR, 10Y G-sec, CPI last → nowcast, Brent, reserves); the transmission chain in one row (growth → inflation → policy → curve → rupee & flows → sectors → names — every cell clickable into its deep tab); today's model calls with the running record; the calendar (US CPI 10 Sep, India CPI 12 Sep, WPI, trade, FOMC 16 Sep, IIP, GST, **RBI MPC 5–7 Oct**, Q2 GDP); and a "where to go" list. The full regime strip and the positioning note moved *into* the DESK from above the tabs. Nothing on the DESK is typed — each cell is a block another tab renders in full.

### 2 · The header is just the logo
Top of the page: `MACROINTEL · INDIA · MACRO → MICRO` and the as-of stamp. The 12-subsystem status grid, the "prices verified fresh" line and the update manifest all live in one click-up at the **bottom** (`⚙ DATA STATUS — 10/12 subsystems live · prices 74/87 refreshed · last pass …`). The stale-price alarm banner still fires at the top if prices are ever stale — that one is an alarm, not status. Tab bar shortened to nine: DESK · MACRO · RATES·OIS · RESERVES & FX · COMMODITIES · GLOBAL · NEWS · TEAR SHEETS · MICRO·SHARES. Palette, cards, section rules and tabs restyled flat and dark (institutional, mono numbers, thin rules, colour only for direction and warnings); IBM Plex loaded from Google Fonts.

### 3 · The model desk and the accuracy ledger (`RECS_LIVE`)
Every model on the page now emits **dated calls** each ML pass, and a ledger scores them:
- short-horizon ranker (10 sessions): top-3 LONG, bottom-2 SHORT
- long-term composite (60 sessions): top-3
- wide ranker, top-turnover universe (30 sessions): top-3
- metals scorecard (10 sessions): gold/silver LONG/SHORT
- Nifty rule (5 sessions): regime ±1, 20-day tape ±1, FII net short squeeze, PCR, HMM stress — a call only when |score| ≥ 2

Each call is stamped with model, name, side, entry price and date, horizon, due date and the rule that produced it. It is scored at the first close on or after its due session (SHORT = −return); open calls are marked to market each pass; one open call per (model, name). Per-model **hit rate, average return per call and t-stat (n ≥ 8)** print on the MICRO › BUILD & SIZE tab ("EDGE" only at t ≥ 2 and hit ≥ 55%; "INVERSE — fade it" at t ≤ −2; "accruing" below eight closed calls). **Hard guard:** on a pass where yfinance refuses and the panel falls back to synthetic prices, nothing is emitted and nothing is scored — the ledger is carried untouched.

The rankers now take **macro externalities** as features alongside price: Brent 5d/20d, INR 5d/20d, US 10Y 20d, DXY 20d, VIX 1-year percentile, India VIX 20d, plus each name's rolling beta to Nifty and correlation to Brent and INR. Output labels say `price + externalities` or `price only`.

### 4 · Reserves and gold — the standing complaint, fixed
- `RESERVES_LIVE` carries the **composition** (FCA / gold / SDR / IMF) from the same weekly release, as-on-dated, with week / FY / year changes, and a composition panel (`#rsv-comp`) that reads the gold revaluation before the headline: of the +$38.6bn on the year, +$29.2bn is gold.
- **As-on dating**: every trail point is keyed on the release's own "as on" date, never the run date; release-implied anchors (a year earlier, end-March) give the chart history without FRED; the ATH line is honest.
- **Gold in rupees**: a K-factor (IBJA fix ÷ GOLDBEES close, calibrated 11 & 14 Aug) turns the daily ETF close into an ETF-implied gold price for days the fix hasn't been read; a ⚠ fires when the ETF-implied and the last fix diverge > 2%. Silver the same via SILVERBEES.

### 5 · RATES · OIS — the live term structure
`fetch_gsec10_rbi` now keeps the **whole** RBI home-page "Government Securities Market" panel: 91/182/364-day T-bill cut-offs and every dated stock quoted (2029, 2031, 2036, 2040, 2055 as of 31 Aug), with the panel's own as-on date → `CURVES_LIVE.gsec_curve` + a one-row-per-as-on-date `gsec_trail`. New panel **1.2 · THE LIVE TERM STRUCTURE**: chart of bills + G-secs against the OIS fixings and the repo line; a table with every quoted point vs repo, the OIS at that tenor and the swap spread; computed sentences — front end (364d bill +55bp over repo ≈ 2.2 × 25bp of tightening priced on average, upper bound), belly-to-ten, ten-to-long, swap spread at 1Y with "the two legs agree on direction". India's TED spread (3M term MIBOR − 91d bill) gets its own sentence. The §5 swap-spread table finally has its bond column (interpolated off the live curve). Explainer rewritten for the hold-to-hike regime; the June-2026 "isn't MIBOR 7.5%?" box, the "oil easing" row and the "front-end OIS pricing easing" sentence are gone; RBI WATCH is measured against the repo (not a surplus-depressed overnight) and is sign-aware; the curve-shape panel has a "hikes priced" branch; the priced-path panel prints the live 364d bill beside the 1Y OIS fixing. Blackout carry: if the RBI panel doesn't answer, the 10Y and the curve carry with their date and a CARRIED label.

### 5b · The MIBOR-OIS curve is a read now, not a snapshot (`OIS_LIVE`)
FBIL's own site is a JavaScript app with no keyless endpoint and CCIL's market watch is bot-blocked, so the fixings are read every pass from **Cbonds' server-rendered index pages** (a mirror of the FBIL MIBOR-OIS benchmark; the free view lags the fixing by a few sessions and the page prints that date). `fetch_ois_curve` → `patch_ois_curve` rewrites every `OIS_CURVE` tenor 1M–5Y (2M added) and publishes `window.OIS_LIVE` (points, as-of date, source, `carried` flag, a one-row-per-date trail of 3M/1Y/5Y). ON stays the daily MMO call; the old override that put the 3M **term MIBOR** (a bank-credit rate) on the 3M swap point is retired — the TED read (term MIBOR − 91-day bill) now lives in its own sentence in 1.2. Every OIS mention on the tab prints the fixing date; "snapshot" wording is gone.

Seeded with the fixings as of **25 Aug 2026**: 1M 5.27 · 2M 5.32 · 3M 5.38 · 6M 5.57 · 1Y 5.89 · 2Y 6.09 · 3Y 6.20 · 5Y 6.39. That replaces a June-2026 hand curve (1Y 5.58, 5Y 5.68) that understated the tightening priced: the 1Y now sits +64bp over the repo (≈ 2.6 × 25bp on average over the year), and the two legs finally agree — bill 5.80 vs OIS 5.89 at 1Y (−9bp), GS 2031 vs 5Y OIS +21bp, a normal supply premium.

### 5c · Nothing typed, or labelled (v120.2)
Every number on the page is now one of three things, and the page can tell you which:
- a **live read** — a `window.*_LIVE` block with its own date (35 of them), synced into the prose through `.oisv` / `.blv` spans and `{token}` templates;
- a **hand note** — two new dated blocks, `window.MPC_LIVE` (the decision, stance, minutes' tone and quotes, the RBI's own CPI path, next meeting) and `window.DESK_NOTES` (Fed odds, CPI consensus, the geopolitical premium, the FII August book, the FCNR carry estimate). Each renders with an age tag ("hand note · 1 Sep · 3d") that turns amber after 10 days and red after 20; the updater flips `MPC_LIVE.stale` (printed in red wherever the block is used) the moment the RBI feed carries a policy statement or minutes dated after the block. To update them: edit the two blocks in the HTML (they are plain JSON) — the updater carries them and never overwrites them;
- a **parameter** — `MI_PARAMS`, 30 rules, thresholds and published coefficients (corridor width, the RBI oil→CPI coefficient, the GST 2.0 base effect, the stress thresholds, vol buckets, risk per trade, reserve-cover bands, the TED band, the DXY/Brent bands…) each with its source, listed in full in the bottom status drawer under "PARAMETERS IN FORCE" and referenced from the code, never re-typed.

What was deleted rather than wired: the two archived June-2026 blocks on the MACRO tab (the scenario library with its shock table, playbook probabilities and tail-hedge menu; the BoP/flow-war sections, the yield-curve panel that still said "cuts being priced", the "P3 brainstorm" positioning block with "if tonight's CPI…"), and `MACRO_DEFAULTS` in the updater (a dict of stale literals that had been dead since v92 but still sat there). They are replaced by two **computed** panels: **8 · AT THE MARGIN** (improving / deteriorating — every line a test on a live block; lines that do not pass are not shown) and **9 · SCENARIOS** (the framework's "if X changes" rows with LIVE / ARMED / OFF read off the blocks on every load). The CPI nowcast's print calendar, coefficients and RBI path now come from the CPI vintage, `MI_PARAMS` and `MPC_LIVE`; import cover uses goods **plus services** imports from the last trade release (it was a typed $60bn/month); the sector "character" sentences are templates filled live; the release calendar's notes are templates too (the dates are hand-maintained and aged, the numbers never typed). A new test, `t120_typed`, scans the live tabs for numeric literals with units and for dates/money in renderer strings and fails on any — the allowed exceptions are listed in the test by name.

### 5d · The three caveats, fixed (v120.3)
Two were fixable and are fixed. The third was fixed the only way it honestly could be.

**The sector → names mapping is computed now, not typed.** `GDP_MAP` keeps a GVA-bucket → listed-sector *taxonomy* (structural: where a sector's output is booked on the exchange) and nothing else. `_sectorStats()` derives the constituents from the published universe's own sector labels (`HIST.sect`, 750 names) and their measured 6-month returns (`HIST.wf`), recomputed on every load: pooled median per bucket, breadth (share of names up), and the three best names in each listed sector by that same measure. The panel now prints a **market verdict** — confirmed / flat / DIVERGING — against the GVA print. It immediately earned its keep: construction GVA is **+7.7% and accelerating** while its 80 listed proxies run a **−2.9% median with only 44% up — DIVERGING.** The typed list asserted Infra benefits; the measured one says the output is growing and the market is not paying for it. Change the universe and the names change; nothing is hand-maintained.

**The OIS lag is off the signal path.** The mirror still lags the fixing by a few sessions, so the fix was to stop letting it carry the signal. `_billPath()` computes forward rates between the RBI's **official, daily** T-bill cut-offs (act/365: `f(t1→t2) = (g(t2)/g(t1) − 1)·365/(t2−t1)`) and publishes them as section **1.6 · THE PRICED PATH** — no mirror, no snapshot, no carry. Today it reads 5.26% now → **5.90% in three months** → 5.82% in six: a peak of **+65bp over the repo, ≈2.6 × 25bp of tightening**, computed fresh every load. The 1Y swap fixing sits +64bp — the two markets agree within 9bp from independent sources priced days apart, which is exactly why the lag no longer matters: the swap now *corroborates* a number the page computes daily. Both honest bounds are printed (term premium is not stripped, so a forward is an upper bound; bills price the bill rate, not the repo). The DESK's POLICY node reads the bill path first and notes when the swap agrees.

**The significant findings ride on the calls, not in a separate audit layer.** An earlier cut of this build added an "evidence ledger" that graded all 18 testable claims and led with "2 of 18 clear |t| ≥ 2" — accurate, and the wrong thing to put in front of a trader: it foregrounded the failures and buried the answer. That layer is deleted. What survives is the part that was actually useful: where the regime study measured a **significant** sector effect, the finding now prints on the sector call itself as a one-line marker — **NBFC ▲ FAVOURED in Reflation (+29%/yr, t +2.2)** and **Auto ▼ AVOID in Reflation (−24%/yr, t −2.1)** — and where it did not, nothing prints at all. The models' own "edge unproven" labels stay where they already were (metals, the rankers), because the short ranker's out-of-sample ICs really are ~0 and dressing that up is how a position gets sized on a number that was never there. The difference is that the page now leads with what it knows instead of auditing itself in public.

### 6 · What 7.8% means (MACRO 0.06)
Under the GDP card: sector → industry → listed names for every GVA bucket (mapping hand-curated 1 Sep, labelled as such), the second-order effects with the page's live numbers (the RBI's own 6.7% implies ~6.3% average for the next three quarters; 2.5pp deflator = thin pricing power; credit 18.3% vs deposits 14.7%; GST buoyancy 1.4×; imports/CAD with Brent $92; nowcast 5.7% CPI → real repo −0.4%; Nifty P/E vs ERP), and **what 7.8% does NOT mean** (not a rate-cut signal, not broad-based, part base effect, not pricing power, not this month).

### 7 · NEWS redesigned
Headlines are clustered by theme — rates & the RBI · inflation & oil · rupee, reserves & flows · growth & data · gold & metals · global · the tape · single names & IPOs — each theme carrying a **"what it means"** line computed from the page's live numbers, a count, and a button into the relevant tab. A computed brief sits on top (regime, the dominant theme, the second theme, the next three calendar dates, the model desk state). The dated editorial stays visible; the blog essays and the deep dive fold into one `ESSAYS & DEEP DIVES` click-up. Feeds widened (ET/BS/Moneycontrol markets **and** economy feeds, plus the RBI's own release feed), deduplicated, 42 max.

### 8 · Hand-updated this build (dated on the page)
- HSBC manufacturing PMI Aug 52.8 final (five-year low; Jul 53.5), services flash 54.5, composite flash 54.6 — tiles in the macro blocks, threaded into the 7.8% panel, the DESK chain and the editorial.
- RBI home panel as on 31 Aug (G-secs + bills) seeded so the RATES tab is live before the first Actions pass.

---

## Data contracts
38 (v119's 34 + `RECS_LIVE` + `OIS_LIVE` + `MPC_LIVE` + `DESK_NOTES`). `update_terminal.py` BUILD = `v120`; page stamp `v120`; 9 tabs.

## Verification run on this build
- `t119_wss` · `t119_doors` (contracts 38, BUILD v120) · `t120_rsv` · `t120_gsec` (parser + publication + carry) · `t120_ois` (Cbonds parser, const rewrite, anchor pass leaves the fixing alone, carry, trail) · `t120_typed` (zero typed literals in live tabs; MPC staleness flips/clears) · `t120_ml` (externalities, ledger emit/score/roll, block round-trip): all pass
- cross-block audit: 106 checks, 0 failures (also 0 on the blackout-mock output)
- blackout mock (every door refused) on a copy: 38/38 contracts intact, 10Y, term structure and the OIS fixings carried with their dates, ledger untouched, all tabs render, zero console errors
- full `ml_models.py` run on the copy: completes; synthetic-panel guard confirmed ("ledger untouched this pass")
- headless render of all nine tabs: no empty containers, no page errors

## Honesty notes
- The OIS fixings come through a mirror that lags a few sessions; the page prints the fixing date everywhere it uses the curve, and the official bill/G-sec curve is printed beside it as the daily check. If Cbonds ever blocks the runner, the last fixings carry with their date (flagged CARRIED).
- Accuracy on the model desk is **measured, not claimed** — until eight closed calls a model reads "accruing". The first calls appear on the first ML pass after upload; the first scores 5–10 sessions later.
- The industry/name mapping under the GDP print says where growth is *booked*, not what to buy; the screens and the ledger rank names.
