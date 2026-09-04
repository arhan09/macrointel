# MacroIntel v124 — HMM out, CCIL in, Ask the Desk

**Upload:** these files at the repo root, then Actions → *daily-update* → **Run workflow**. No push trigger.

`macro_intelligence_terminal.html` · `update_terminal.py` · `ml_models.py` · `README-v124.md` · `t121_safety.py` · `t122_validation.py` *(tests optional)*

Overlay on the existing repo. Cumulative from v118. **41 data contracts** (adds `ASK_CORPUS`).

---

## 1 · The HMM is out of every decision path

It was governing risk: capping size, setting the portfolio stance, changing the micro watchlist's wording and setting the trade planner's reward multiple. Then this terminal's own validation engine measured it — forward-return t-statistics of **0.29, 0.13 and 0.02** across its three states, `separates: false`. It describes volatility well and does not separate returns.

A fitted latent-state model with no measured forward edge should not decide how much risk a book carries. It no longer does.

**What replaced it — a mechanical tape score.** Six checks, each worth exactly ±1, each computed from price alone, each publishing the number that decided it: index vs its 50- and 200-session means, 20-session momentum, breadth (share of the published universe above its own 50-day), midcaps vs the index, and whether realised vol is falling. Nothing fitted, so nothing can overfit; a reader can recompute the whole thing by hand.

**`marketState()` now reads two things, in this order:**

| condition | state | ceiling |
|---|---|---|
| stress ≥ 60 | `STRESS` | RISK OFF — stand down |
| stress 35–59 | `ELEVATED` | reduced size |
| tape ≥ +3 | `CONSTRUCTIVE` | none |
| tape −1…+2 | `MIXED` | reduced size |
| tape ≤ −2 | `DEFENSIVE` | reduced size |

Stress is checked first because it is a **gate, not an opinion** — when correlations go to one the tape's direction stops meaning what it normally means, so no tape reading may override it. `_stanceRead()` now uses only market confirmation + tape state + stress, and a ceiling can only ever *lower* the answer.

**Everywhere else it touched:** the trade planner's reward multiple, the micro texture note, the micro watchlist caption (which now keys off the ranker's own out-of-sample significance — the only thing that ever should have decided it), and the footer's model list. The HMM is still calculated and still shown, on the Model Desk and under Validation, labelled **EXPERIMENTAL · INERT**, with the measurement that demoted it printed beside it.

## 2 · OIS sourcing: CCIL primary, FBIL as the benchmark reference

FBIL administers the official MIBOR benchmark and is the authority — but it publishes through a browser application with no server endpoint (the apex `fbil.org.in` has no A record; `www.` serves an empty shell that fills over XHR). A scheduled job cannot read it.

CCIL is where the swaps actually trade and it serves server-side. So: **displayed curve = CCIL weighted-average / last traded rate; benchmark reference = FBIL**, and the page says which answered. The distinction is printed rather than blurred — a traded rate and an administered fixing are different objects, and on an illiquid tenor they can differ by more than the spread a desk would pay.

Per tenor the page now carries **as-on date, notional, trade count, previous close**, and a status of `TRADED` / `NO TRADE · INDICATIVE` / `CARRIED`. Tenors are combined onto one curve only when they share an as-on date; where a tenor did not print, the previous verified close is shown and labelled, never silently interpolated.

**Two parser bugs died in testing, both of which would have published wrong rates:**
- "Last sane number on the row" took the **trade count** as the swap rate — 1M came out at 4.0000% from a row ending `... 1,250  4 trades`.
- Stripping the notional with a loose `\d{3,}` pattern matched the **decimal half of a rate**, turning `5.2700` into `5.` and leaving the row with no rate at all.

Fixed by classifying whole tokens by shape instead of regex-and-replace. Seven tenors now parse exactly, with the 10Y correctly flagged NO TRADE because it carries a level and no volume.

## 3 · Ask the Desk

A question box on the DESK. You type, it classifies intent, and a handler computes the answer from live blocks and names the blocks it used. All eight of your example questions have first-class handlers: what changed today · the macro environment · which assets benefit · is price confirming · the best expression · why now · what invalidates · how much risk.

**It changes every day because its inputs do**, not because it re-words itself.

**On the RAG part, stated plainly.** This page is static HTML on GitHub Pages: no backend, no key. It **cannot** call a model or search the web at question time — anything that appeared to would be embedding a secret in public source or inventing text. So retrieval happens where the network actually is: `update_terminal.py` runs in Actions, already reads the RBI wire, PIB and the news feeds, and now publishes a dated corpus (`ASK_CORPUS`) the page searches. Every passage carries its source and date, and nothing is rewritten on the way in.

Three answer kinds, always labelled: **COMPUTED** from live blocks, **RETRIEVED** from the dated corpus with its term-overlap score shown, or **NOT ANSWERABLE** — which says so and lists what the desk *can* answer. On a terminal a book is sized from, a confident wrong answer is the worst possible failure, so the miss path refuses rather than generates.

---

## A mistake I made, and what it cost

Building this, my own patch script bounded a function replacement on `function renderTodaysBook(){` — which sits **134KB later** in the file, because the v122 validation renderers and the v123 chart pack were both inserted between the two anchors. The splice silently deleted all of it. Deterministic, so it produced a byte-identical broken file twice, which I initially misread as evidence of an external process modifying my working directory. It was not; it was me.

Function bodies are now replaced by **brace matching** with a byte-count ceiling that refuses an oversized cut, and the build asserts every renderer and all 13 pack pages survive before it writes anything. The verified v123 artifact was never affected.

A related trap bit twice more: assertions written as raw substring tests trip on the build's **own comments** — a comment reading *"this used to read `ML_OUTPUT.hmm`"* satisfies a test for `ML_OUTPUT.hmm`. Same class of bug as the v122 patcher that silently no-opped because its guard matched a code comment. Those checks now strip comments and count code.

---

## Verification

- 8 suites, `FAILURES: none` — `t121_safety` realigned to assert the mechanical guarantee (stress gates first, no state is labelled RISK-ON, every state carries a ceiling) rather than the retired implementation's variable names
- cross-block audit: **155 checks, 0 failures**, on both the live page and the blackout-mock output
- blackout mock: **41/41 contracts**, CCIL tried first and its refusal reported, fallback labelled, cross-block check clean
- 11 tabs render, 13 chart-pack pages render, **zero page errors**
- ask engine: 8/8 example questions computed, corpus retrieval verified, refusal path verified on an out-of-scope question

---

## What this build adds

An eleventh tab: a **paginated India chart pack**, built to the structure of the Capital Flows daily pack but mapped onto what India actually trades. Thirteen pages across seven sections, its own internal navigation, its own visual register — pure black, one accent colour per section, condensed titles, wide-tracked mono labels.

| § | Section | Pages |
|---|---|---|
| 01 | Policy & short rates | The priced policy path · Money market & the corridor · Swap curve & spreads |
| 02 | Rate decomposition | The curve complex · The swap spread |
| 03 | Curve regimes | Curve regime history |
| 04 | India term structure | The full term structure · The curve through time |
| 05 | Cross-asset regimes | Regime timeline · Market linkage |
| 06 | Equities & earnings | Sector attribution · Breadth & dispersion |
| 07 | FX & external | USD/INR rate differential model |

**Nothing here is a new data path.** Every page reads the same live block the desk reads, with the same as-on date, through one accessor. There is no second copy of any number and no door was added — which is why the pack could be built in a session without adding data risk.

## Where the India mapping had to differ, and why

**There is no "Global Rates" section.** The source pack lines the US up against six other markets. Lining India up against markets it does not trade against would be filler, so that space goes into India's own term structure at every point it actually prices — bills at 91/182/364 days, the benchmark bonds out to 2055, and the forward curve implied between every consecutive pair.

**There is no inflation-swap leg, and the pack says so.** The source decomposes every nominal yield into a traded real yield plus a traded inflation swap — an exact identity, because both legs price. India has neither a liquid inflation-linked curve nor an inflation-swap market. Inventing a breakeven would have been the single most dishonest thing in this build, so the pack does two real things side by side instead:

- **Ex-post real curve** — nominal minus the latest CPI print, and minus the terminal's nowcast (dashed). Arithmetic on a published statistic, backward-looking by construction, and labelled as such.
- **G-sec minus MIBOR-OIS** — both legs traded, so the spread is a genuine market price of term premium, collateral and supply. Currently −12bp at 91 days widening to +116bp at the 2055 bond.

**The cross-asset regime map is Nifty / 10-year / rupee**, eight states, each leg divided by its own volatility. The rupee leg is signed so positive always means a *stronger* rupee rather than a higher USD/INR quote — a regime map with one axis running backwards is unreadable.

---

## The MIBOR search, and what it found

You asked me to search again for MIBOR data. The answer is worth stating plainly because it constrains the build:

- **`fbil.org.in` has no DNS A record** — the apex domain does not resolve. Verified against Google's resolver: `Status:0`, SOA only, no answer.
- **`www.fbil.org.in` is a hash-routed single-page app.** It serves an empty shell and pulls every rate over XHR. Every indexed data URL (`/download?op=miborois`, `/securities?mq=o&op=mibor`) 404s.
- **FIMMDA's mirror is behind a login wall.** **CCIL's ASTROID OIS page** returns 200 with the right table headers and every value cell empty — JS-populated. **Cbonds** has the real numbers and paywalls them.

**So no free server-fetchable door for FBIL MIBOR or MIBOR-OIS exists.** The hand-seeded snapshot is genuinely the best available free source, and it lags. The pack now says so on the page rather than in a footnote: the swap page carries the limitation in its own banner, and `cpAgeDays()` computes the fixing's real age so a block that was *read* today but carries a nine-day-old *fixing* still warns. That distinction was a bug in the first cut — the warning only fired on the carried flag, so the most misleading case, a fresh read of a stale fixing, showed nothing at all.

**Two doors that did verify**, both upgrades worth wiring next:

- **RBI Money Market Operations via `pressreleases_rss.xml`** — official, daily, server-rendered, ~20-year-stable pattern. Call money, TREPS, market repo, corporate bond repo, SDF/MSF/reverse repo with weighted averages and ranges. The corridor page is built for exactly this shape.
- **A full India G-sec curve 3M→40Y**, server-rendered and fetchable: 3M 5.21 · 1Y 5.57 · 2Y 6.19 · 5Y 6.59 · 10Y 6.96 · 30Y 7.56 · 40Y 7.63. Its 10Y matches our RBI read of 6.96 and its 30Y matches GS 2055 at 7.55 — independent corroboration of numbers already on the terminal, at ten tenors instead of eight.

**The five-minute fix that would end the lag:** open `fbil.org.in/#/home` in Chrome with DevTools on Network, click the MIBOR-OIS table, and capture the XHR. If it is a plain GET returning JSON it drops straight into the updater as a real daily door.

---

## Design decisions worth knowing

**The model version deliberately did not move.** `update_terminal.BUILD` is now `v123`; `ml_models.BUILD_TAG` stays at `v122`. The chart pack changed no model, and the promotion framework says a methodology change starts a new frozen out-of-sample record — so bumping the model tag for a presentation change would reset the only clock that can promote the models, for nothing. A regression test now asserts the two are allowed to diverge and that the divergence is in the right direction.

**A page that throws says so.** Each page renders inside a guard that prints *"this page did not render"* with the error, rather than dropping silently. A chart pack that quietly loses a page is worse than one that admits it.

**Thin sectors are kept out of headlines.** Utilities has four names in the universe and the best six-month median. It stays in the table with its count beside it, and it is excluded from the BEST/WORST callout — a median of four names is one or two stocks wearing a sector's label.

**Narrow charts get a matching viewBox.** `preserveAspectRatio="none"` scales X and Y independently, so in a three-column layout the axis text was being smeared horizontally. Charts in narrow columns now pass a viewBox width close to their render width.

---

## Verification

- 9 suites, `FAILURES: none` — `t122_validation` now also covers the pack (unique page keys, valid sections, single data accessor, error surfacing, age-based staleness, the thin-sector guard, no duplicate renderers, scoped CSS)
- cross-block audit: **149 checks, 0 failures**, on both the live page and the blackout-mock output
- blackout mock: **40/40 contracts**, cross-block check clean
- **all 13 pack pages render, zero page errors**; 11-tab sweep clean
- pack CSS is scoped under `#tab-pack` so it cannot leak into the ten existing tabs

---

## What this build is

v121.2 closed the last decision bug. This one answers the question that decides whether any of it may size a position:

> **do the names and sectors this system ranks highly subsequently outperform the ones it ranks poorly — consistently, out of sample, and after costs?**

The honest answer today is **we do not know yet**, and the terminal now says so in a way it cannot wriggle out of. `regime_edge` publishes `skill: "none"`; the frozen out-of-sample record is empty because it starts on the next pass; and the universe is survivorship-biased, which caps what any backtest run on it is allowed to conclude. So the model status reads **UNPROVEN**, model-sourced signals are capped at **0.25R**, and the page is described as a *macro trading research and decision-support system*, not a proven return-generating model.

Nothing was rebuilt. This is an evidence layer around what already existed.

---

## The three rules the tab is built on

**1 · Nothing is recomputed.** Each ML pass writes the full prediction — model version, information cutoff, regime and confidence, market state, sector and stock ranks, the dated calls with entry/stop/target, *why now*, and the conditions that would prove the thesis wrong — to `history/pred_YYYY-MM-DD.json` **before any outcome exists**, then publishes a sha256 of the canonical payload. `freeze_prediction()` will not overwrite an existing file: a pass that disagrees is written as `pred_<date>.r2.json` and the original stands. `verify_frozen()` recomputes every published hash against the files, and distinguishes an old pruned row (benign) from **an edited published row** (`hash_mismatch`, `clean: false`, dates named) — the one failure that would make the whole tab worthless.

**2 · Nothing is shuffled.** Every split is time-ordered:

```
train  = bars [0, cut − embargo)
PURGE  = [cut − embargo, cut + H)      ← never trained on, never tested
test   = bars [cut + H, next_cut)
```

The purge is at least the forward-return horizon because a 20-day label written one day before the boundary contains 19 days of test-period prices. The fold table publishes real dates so the discipline can be checked, not believed.

**3 · Nothing is claimed that the data cannot support.** `provenance_audit()` enumerates eleven known backtest distortions with a verdict on each. Survivorship and historical index membership are marked **BLOCKING** and uncontrolled, and `promotion_status()` enforces that in code: **no combination of good numbers can reach VALIDATED while a blocking row is outstanding.** The ceiling is EMERGING, and the tab says why.

---

## The engine, and how it was checked

Before it was pointed at anything real, `walk_forward_deciles()` was run on **three independent random-walk panels**. An engine that finds edge in noise is worse than no engine:

| panel | rank IC | top−bottom, gross | net | t | monotonicity ρ |
|---|---|---|---|---|---|
| random walk, seed 11 | +0.027 | +0.79% | +0.13% | 0.91 | 0.248 |
| random walk, seed 22 | −0.004 | −0.50% | −1.17% | −0.61 | −0.401 |
| random walk, seed 33 | −0.041 | −0.76% | −1.42% | −1.05 | −0.806 |
| **planted 12-1 momentum** | **+0.231** | **+8.55%** | **+7.89%** | **10.71** | **0.964** |

No noise panel clears |t| 2, and all three go negative after costs. The planted panel produces the ladder −2.1, −1.9, −1.6, −1.5, −1.8, −0.6, −0.3, +0.3, +1.0, +6.4. The engine finds signal where signal exists and not where it doesn't.

**Two bugs it caught in itself, both found by testing rather than by reading:**

- The first equity curve **compounded overlapping 20-day returns daily**, ending at 3.1 *billion*× on a 3.9%-per-period spread. That is the exact shape of a backtest that has fooled its author. The curve, its drawdown and its Sharpe now use every H-th bar only, and the tab publishes **independent periods** (36) next to test bars (708), because the second number looks like evidence and the first one is it.
- `patch_validation_block()` tested `if "window.VALIDATION" in html`, which was true because the *renderer's own comment* mentions the variable — so the regex found no assignment, replaced nothing, and reported success. The page then said "the validation engine has not run yet" after a run in which it had. Both patchers now verify their own write and say so when it fails.

---

## The cost model — published rates, and one honest estimate

Verified against primary sources on 2 Sep 2026. Round trip on a ₹10 lakh delivery trade:

| component | bp | |
|---|---:|---|
| STT | 20.00 | 0.10% both sides |
| brokerage | 4.00 | 2bp/side — the SEBI 2026 MF cash-segment cap, not retail |
| stamp duty | 1.50 | buy side only, uniform since 1 Jul 2020 |
| GST | 0.83 | 18%, on brokerage + exchange + SEBI fees only, never on STT or stamp |
| exchange txn | 0.61 | ₹307/cr per side (NSE/FA/73061) |
| DP charge | 0.15 | CDSL ₹3.50 + broker markup, sell leg |
| SEBI turnover | 0.02 | ₹10/cr per side |
| **explicit** | **27.12** | |

**STT alone is 74% of it.** For a delivery strategy the explicit cost is "20bp plus change", and refining the rest is rounding error next to the spread assumption.

**Spread and market impact are NOT published rates and are labelled as an assumption everywhere they appear.** No exchange, regulator or index provider publishes a bp-by-liquidity-tier table for Indian equities; NSE publishes only index-eligibility *ceilings* (≤0.50% for Nifty 50 on a ₹10 crore basket), which are upper bounds on the worst constituent and would wildly overstate a normal fill. So three conditions are shown, not one: **normal / conservative / stressed**, per tier, and the tab reports whether the edge survives each. If it only survives the optimistic column, it is not an edge.

---

## What it has to beat — with itself in the table

The system's own top-decile and long-short lines sit in the baseline table on the same rebalance clock and the same costs, against buy & hold, equal weight, 12-1 momentum, sector-neutral momentum, low volatility and SMA 50/200. A verdict line states the head-to-head in words, and it is written to be able to say the uncomfortable thing:

> *"buy & hold the benchmark beats this model on Sharpe (3.59 vs 0.78). A ranker that does not beat the cheapest alternative is not earning its complexity, and that is the finding, not a presentation problem."*

**And the overlay test**, which is the comparison most likely to embarrass the system, so it is on the page: `ml_only` (rank, always invested) vs `macro_only` (whole universe, only while the trend filter is risk-on) vs `ml_plus` (both). Deliberately the cheapest possible version of each leg, so it measures the *idea* of macro confirmation rather than this page's implementation of it. If confirmation does not improve risk-adjusted return, the layer is complexity that costs money — and knowing that is worth more than defending it.

---

## Sizing is now a function of proven edge

The promotion ladder is not decoration; it sets how much risk a model signal may carry, enforced in `bookValidate()`:

| status | evidence required | permitted usage |
|---|---|---|
| **UNPROVEN** | backtest only, or `skill: none` | paper / experimental — **0.10–0.25R** |
| **EMERGING** | positive **frozen** OOS results across several periods | reduced size — 0.25–0.50R |
| **VALIDATED** | stable net edge across regimes *and* cost conditions, no blocking distortion | normal risk budget — 1R |
| **DEGRADED** | live results materially below the historical expectation | reduce or suspend |

At UNPROVEN, a model signal with a 5% stop is capped at 5% of book and the refusal names the permitted size and the reason. Positions now carry a **source tag** — `discretionary` or `model signal`. Discretionary trades are *not* capped by this (they are the trader's own call) and are tagged so they stay out of the model's record and cannot flatter or contaminate it.

**A methodology change starts a new record.** Every frozen prediction is stamped with the model version that made it, so a change to the features, the gate or the universe cannot be quietly credited with the previous model's results — and a losing stretch cannot be deleted by shipping a new version. That also makes changing the model expensive: it resets the clock on the only evidence that can promote it.

---

## The tab

Ten tabs now. **VALIDATION** carries: the status header (status, ceiling, OOS period, predictions frozen, closed trades, rank IC, top-decile excess, net Sharpe, max drawdown, turnover, independent periods, live-vs-backtest) with **every reason it is not rated higher, printed in full**; the decile ladder with gross and net bars; the cumulative curve and drawdown; performance by macro regime; rank calibration; the cost grid; baselines with the head-to-head verdict; the overlay test; a per-model scorecard (stock ranker, sector model, HMM transitions *and* forward returns by state, trade expectancy in R, combined); the provenance audit; the frozen ledger with hash verification; and model-change history.

The HMM panel is worth one note: returns measured *inside* a state describe the state — a stress state has bad returns by construction, which proves nothing. The predictive content is whether a state **persists** (the transition-matrix diagonal, published alongside the empirical count as a cross-check) and what the **next** 20 sessions did. Both are shown, and on current samples the states separate volatility well and forward returns poorly. That is stated on the page.

---

## Verification run on this build

- 9 suites, `FAILURES: none` — including `t122_validation` (cost arithmetic, split discipline, ledger immutability and tamper detection, promotion ceilings, patcher verification, sizing caps) and the random-walk null test above
- cross-block audit: **141 checks, 0 failures**, on both the live page and the blackout-mock output
- blackout mock (every door refused): **40/40 contracts intact**, `build check: cross-block values agree`, and the synthetic-panel guard confirmed — **no frozen row is written from invented prices**, and a synthetic pass can never earn a status
- end-to-end: freeze 3 days → walk-forward → baselines → audit → patch → render, with `3/3 hashes verified, tampering none`
- 10-tab headless sweep: every tab renders, zero page errors

---

## v121.2 — three decision blockers, closed (third review)

The v121.1 build fixed five blockers; a second pass found three more, all of the same species — **a label the desk would size a position on, computed by a rule looser than the one the page's own model publishes.** All three reproduced exactly as described before anything was changed.

### 1 · The empirical-edge gate contradicted the model it was reading

`regime_edge` runs ~10 sector tests, so `ml_models.py` sets its own multiple-testing bar and publishes it: `gate: 2.6`, plus `significant: []` and `skill: "none"` — the model stating that **nothing cleared**. The page's `_regEdge()` used `|t| >= 2`, a *laxer* bar than the study it was reading. So Auto at t −2.12 and NBFC at t +2.22 — neither significant by the model's own rule — could override a trade. Reproduced: `{modelGate: 2.6, modelSkill: "none", modelSignificant: 0, regEdgeAcceptsAuto: true, autosAction: "WAIT", autosConv: "LOW"}`.

`_regEdge()` now reads `RE.gate` and `RE.significant` — and treats an **empty** significant list as authoritative, because that is the model saying nothing cleared. Findings are graded:

| grade | condition | what it may do |
|---|---|---|
| **SIGNIFICANT** | in the published `significant` list (or `\|t\| ≥ gate` where none is published) | demote an action, or lift conviction |
| **nominal** | `\|t\| ≥ 2` but under the gate | **neither.** Caps conviction at MED when contrary; written into the reason in words |
| — | `\|t\| < 2` | nothing is returned at all |

The asymmetry is deliberate: a weak contrary signal may make a book *smaller*, never larger. Post-fix, autos reads **LONG · MED** with the reason naming the nominal evidence and the bar it failed. The table column and the GDP-panel badge both print `SIGNIFICANT · gate 2.6` or `nominal · under gate 2.6`, with the 95% CI beside it.

### 2 · CHOPPY could still produce full risk

`marketState()` printed `RISK-ON · CHOPPY` whenever the *separate* cross-asset composite was calm, and `_stanceRead()` tested only for the word `STRESS`. Reproduced: HMM **CHOPPY at 99.9%**, stress composite 22, 5 of 6 confirmations → **`RISK-ON · CHOPPY`** and **`+RISK · CYCLICAL BIAS`** — full size, on the same screen as the model's own instruction to *size down, fade extremes*.

Each market state now carries the ceiling it implies (`cap: 'off' | 'moderate' | 'none'`), and the stance is the **stricter of two independent reads**: how much of the macro prior the tape confirms, and what the state model says the tape *is*. A ceiling can only ever lower the answer. Post-fix: **`CHOPPY`** → **`MODERATE RISK · REDUCED SIZE`**, with the reason naming the confirmation count, the state, its confidence, and why chop is exactly the condition in which a high confirmation count misleads a trend book. `DEFENSIVE` (HMM bear/down) is capped identically — it had the same contradiction and was not in the review.

### 3 · Live Book validation was only partial

Every rule was guarded by `if (field != null)`, so an entry price alone passed. Reproduced — four cases, **zero errors on all four**: target equal to entry; no stop, target or weight; weight only; stop only. Worse, incomplete positions contributed `null` to the risk sum, so a book of stop-less positions read **`0bp of 300bp used`** — full risk, reported as none.

- **Complete geometry is required.** Entry, stop, target and size, all four. A target equal to the entry is rejected as a flat trade.
- **Nothing sits silently outside the numbers.** Rows are classified: valid, *contradictory* (struck through), *incomplete* (dimmed — a book saved by an earlier build), and *model calls* (dated calls, legitimately unsized). Only complete rows reach any aggregate, and the header prints how many positions are excluded. `RISK BUDGET USED` never renders green while any position carries uncounted risk; with nothing sized it reads **`NOT MEASURED`**, not `0bp`.
- **The budget blocks, it does not warn.** An addition that would breach `book_risk_budget_bp` is refused with the size that *would* fit: *"this position risks 100bp and the book already uses 250bp of 300bp, putting it 50bp over. Cut the size to 5.0% or less, tighten the stop, or tick override."* The override is an explicit checkbox, so the limit is a decision on the record rather than a label.

---

## Pre-deployment items from the same review

**Cross-block rate values — fixed structurally, not by hand.** `OIS_LIVE` and `OIS_CURVE` carried 1Y OIS at 5.89% while `CURVES_LIVE` carried 5.58%. The cause was ordering: `fetch_curves()` and `build_india_curve()` read `const OIS_CURVE` off the **pre-patch** page, and `patch_ois_curve()` rewrites that const later in the same run — so `CURVES_LIVE.india` was permanently one pass behind, and would have been again next run. `resync_ois_into_curves()` now re-reads the freshly written const at the end of the curve stage and touches only OIS-sourced points.

**And a post-build assertion, as asked.** `verify_build()` runs after every patcher and checks what no single door could: that the swap blocks agree on every shared tenor, that the 10-year is the same number in all three places it appears, that the derived slopes equal their own components, and that the page's build tag matches `BUILD`. It found **five** mismatches, not the two reported — `india_curve.2Y` was 5.52 against a true 6.09, which had the 2-year printing *below* the 1-year, an inverted segment that was purely an artefact of the stale block. Result is written into `RUN_LOG` as `cross-block checks`, so a failure is visible on the page and not only in the Actions log. Non-fatal by design: a page that fails a consistency check still beats no page.

**The FCNR(B) window — and a parser bug found while checking it.** The RBI published the 31 Aug provisionals on 2 Sep: FCNR(B) **$127.226bn**, OFCB $5.260bn, ECB $3.891bn, total **$136.377bn** — against $65.4bn / $72.85bn as on 21 Aug. The final ten days of the window drew **$61.8bn**, nearly as much as its first eleven weeks: a deadline surge into the close. Verified against `rbi.org.in` directly and applied.

Testing the parser against the real release exposed a live bug: RBI writes these in Indian lakh grouping (`1,27,226`), and every leg label also appears in the release's own *title* (`... via FCNR(B) Deposits, External Commercial Borrowings (ECBs) and Overseas Foreign Currency Borrowings (OFCBs) as on August 31, 2026`). Taking the first regex hit, `OFCBs` matched the **date** and would have published **$0.03bn** instead of $5.26bn — a wrong number with no symptom, because nothing checked it. The parser now collects every candidate and publishes the combination that satisfies the release's own identity, `FCNR + OFCB + ECB = Total`; a split that cannot be reconciled is flagged rather than shipped. Both the 21 Aug and 31 Aug releases now parse and reconcile.

The two figures were also **typed into two essay paragraphs**. They now resolve from `EXTERNAL_LIVE` like every other live value on the page — a number that moves $61.8bn in ten days is the last thing that should live in prose.

**News freshness — the rule is now a rule.** Two problems. `strptime`'s `%Z` accepts only UTC/GMT, so `IST` — the stamp half the Indian feeds publish — never parsed, and those items fell through *undated*; and undated items were merely *labelled* while still sitting in a feed captioned LIVE. Named zones are now mapped to numeric offsets before parsing (IST, GMT, UTC, BST, the US and EU zones), a zoneless stamp is read as IST rather than UTC (assuming UTC made every such item look 5½ hours fresher than it was), a stamp from the future is treated as a broken feed clock and not as a fresh story, and **undated items are dropped from the feed** — with a flagged fallback if a pass ever yields no dated headline at all, so the tab is never blank.

**Stale statements, removed.** `$10 Brent ≈ 30–40bp CPI` (the last hard-typed copy; it now states the published RBI coefficient the whole page prices oil with) · `Safe %` → **`Lower-vol %`**, a label that had been contradicting its own note two lines below · `Institutional-grade` → *"Full-page tear sheets"* · `Liquidity = Real Rates` → the two are now named as what they are, the *price* of money and its *quantity*, which usually move together and are not the same lever · *"reserves rising = the RBI is buying dollars"* → three causes, intervention, valuation and **borrowed**, with a note that this year the third has dominated · *"that feed isn't wired yet"* → the WSS component split has been wired since v120 and is on screen · and a curve point labelled `(OIS-implied)` while carrying a term MIBOR.

**`t121_safety.py` now ships**, as the review noted it should.

---

## What this build still does NOT claim

Stated plainly, because the last review's closing line is the right one: *do not present every trade recommendation or position size as statistically proven.*

- **The regime framework carries no t-statistic.** It is a lens for organising evidence. It is not, and does not claim to be, a tested predictor.
- **`regime_edge` currently publishes `skill: "none"`.** Nothing on the page clears its own multiple-testing bar today. Every finding shown is therefore labelled *nominal*, and none of them may override a trade. If a future pass produces a genuinely significant sector, the machinery to act on it is already wired — but it is the model that decides that, not the page.
- **The share rankers are screens, not alpha.** Rank-IC t-statistics under 2 mean the ordering narrows a candidate list; it does not predict returns.
- **Position sizes are arithmetic, not evidence.** The book's risk numbers are `stop distance × weight` against a declared budget. That the arithmetic is correct says nothing about whether the trade is good.
- **The live ledger is the only forward-looking test on the page**, because it dates its calls before the outcome exists — and it is still accruing. Under `ledger_min_n` closed calls it returns no verdict at all.
- Prices and Yahoo series are not individually audited. Model scores, probabilities, stress composites and nowcasts are **computed outputs**, not official numbers, and are labelled as such wherever they appear.

---


## v121 — the console stops being a dashboard (answering the trading-desk review)

The review's thesis: the workflow is **MACRO → MARKET → TRADE → RISK**, not "forecast GDP perfectly". Macro produces a *prior*; price is asked whether it *confirms*; only then does a view become a trade, and only then does it get size. Seven builds, all on the DESK or feeding it.

**1 · TODAY'S BOOK is now the first thing on the page.** Six headline numbers — Macro Regime, Regime Confidence, **Market Confirmation X/6**, Market State, Risk Environment, Portfolio Stance — then the theme board: `theme | macro | market | conviction | action`, sorted so the actionable rows are on top. The **macro** column is the regime prior (the one structural input, and it moves only when the regime word moves). The **market** column is measured — a sector index against the Nifty over 20 and 60 sessions, or where no index trades, the median of that sector's constituents against the median of the whole published universe. Intersecting them produces the reviewer's 2×2 exactly: macro+/market+ → **LONG**, macro+/market− → **WAIT** (a macro view the tape is arguing with is not a trade), macro−/market+ → **TACTICAL ONLY**, macro−/market− → **UNDERWEIGHT**.

**2 · Market confirmation, scored.** Six independent checks that the tape is behaving as the regime says it should — cyclicals vs defensives, banks leading, the commodity complex, curve shape off the page's own dated trail, breadth, and risk appetite. Each prints the number that decided it. The score drives Portfolio Stance: below half and the stance is "WAIT FOR CONFIRMATION", which is the state where a macro book does most of its damage.

**3 · Click any theme for the full chain.** MACRO → RATES → LIQUIDITY → MARKET → MICRO (the best names in that theme by measured 6-month return), then **WHY NOW** (the specific combination that makes it a trade today) and **WHAT CHANGES MY MIND** (the regime word leaving the quadrant, the relative score crossing back, confirmation dropping below half, the market state turning STRESS, and — where measured — Brent breaking higher against a negative oil beta). The panel ends by saying it is a *view, not a position*, and routes to the planner.

**4 · THE LIVE BOOK — the position engine.** The review called this the #1 missing product, and it is now the second panel on the DESK. Positions come from two places: hand-entered (what you actually hold, stored in that browser only) and the model desk's dated calls. Everything else is computed off the published history — mark, P&L, **R multiple** (profit in units of risk taken), **risk in basis points** (weight × stop distance, summed into a risk-budget line), 1-day **portfolio volatility** from the full covariance matrix, **average pairwise correlation**, largest sector, and the book's **net oil beta**. Two warnings fire on their own: average correlation above 0.5 ("the book is closer to one position than to N — size it as though it were") and a net negative oil factor.

**5 · WHAT CHANGED.** Levels are a state; changes are the news. Eleven series with 1-day and 1-week moves, each divided by its *own* average daily move so a 1% day in the Nifty and a 1% day in Brent are not treated as the same event, ranked by that σ, coloured by whether the move helps the current stance, with a one-line summary of what broke a normal day.

**6 · POLICY PRICING as a change (RATES 1.55).** The review's point exactly: a trader needs "has pricing turned hawkish since yesterday", not "+64bp versus repo". Three legs — the 364-day bill, the 10-year, the 1-year swap — each with level, spread to repo, 1-day and 1-week change, and a composite headline (**HAWKISHER ↑ +8bp this week**), then the implications (duration −, high-duration equities −, realty and NBFC −, rupee +). Legs with fewer than three banked dates say so.

**7 · INR PRESSURE ENGINE (RESERVES & FX).** Not "reserves = $729bn" but the decomposition: dollar, oil and US 10Y each with their *measured* beta to the rupee and the contribution of their 20-day move, plus FII flows, the RBI buffer and carry — netting to a DEPRECIATION / BALANCED / APPRECIATION bias and the expressions that follow. A driver whose daily correlation to the rupee is below 0.15 is reported as having **no measured link** and left out of the total, because a coefficient fitted on noise is worse than an admission.

**8 · BRENT SHOCK (COMMODITIES).** Transmission first — inflation (+20bp per +10%), import bill and CAD, rupee, the goods-deficit base — then the **measured** candidate list: every name in the published history whose oil beta survives a joint regression on the Nifty and Brent at |t| ≥ 1.8. It independently reproduced the review's own example: hurt by a spike — IndiGo (−0.136, t −4.0), IndusInd (−0.118), Asian Paints (−0.085), Maruti (−0.078); helped — Infosys (+0.101), ONGC (+0.087), Coal India (+0.069).

**9 · HMM re-read as MARKET STATE.** Not "does it identify the economy" but RISK-ON / CHOPPY / DEFENSIVE / STRESS, combined with the cross-asset composite, and fed into conviction: regime + market state + tape confirming = size; STRESS = stand down regardless of the macro view.

The five morning questions the review ends on are now answered top-to-bottom on one page: what regime (header), what changed (panel 2), what that makes me long (theme board), which of those price confirms (the market column and the 6 checks), and how much goes behind each (the book, the risk budget, the planner).

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

### 5e · The correlated-shock check (v120.5 — answering an external reviewer)
A reviewer pointed out the terminal's real vulnerability: the book is tilted to high-beta cyclicals, so an exogenous energy spike breaks the Expansion lens and forces a Stagflation flip, hurting several positions at once. The critique was right, and measuring it made it sharper. A new panel on the DESK, under the positioning note, regresses each sector's daily returns on the Nifty **and** Brent together, so the oil beta is what survives after the market move is removed (|t| ≥ 2 to count):

- **Banks −0.045 (t −4.3)** and **Autos −0.069 (t −3.5)** — both measurably hurt by oil, and both are exactly what the playbook is pointing at. Autos already carry the ▼ AVOID marker from the regime study, so two independent measurements agree.
- **Energy producers +0.087 (t +2.3)** — the one measured offset, and the smallest line in the book. IT/exporters and gold lean positive (the weaker-rupee channel) but miss the bar, so they are labelled a lean, not a hedge.
- **The rates leg is not a co-loser.** Short duration is what a bear steepener already implies and an inflation shock steepens it further, so the curve position hedges the equity book on the first move rather than compounding it. The panel says so.

The deeper point the panel makes in one line: the regime call, the market lens and the curve regime are **three readings of one growth-and-inflation impulse, not three independent votes** — so the page no longer lets their agreement read as free conviction. Everything is computed from the published daily history on each load; nothing is asserted.

### 5f · TODAY'S BOOK and WHAT CHANGED (v121 — answering the dashboard review)
A detailed external review argued the console should be **MACRO → MARKET → TRADE → RISK**, and that the DESK must answer five questions each morning. Audited against them, the terminal answered 1, 3 and 4 partially, 5 one trade at a time, and **2 not at all**. Two new panels sit at the top of the DESK:

**TODAY'S BOOK** — the reviewer's centrepiece: one table, ten themes (banks, autos, IT, pharma, midcaps, metals, upstream energy, gold, duration, INR), with three inputs kept deliberately separate. **MACRO** is the quadrant playbook's prior (structural — what normally works in this regime). **MARKET** is measured — 20-session relative performance against the Nifty, absolute for gold/gilts/the rupee. **EDGE** is the regime study, applied only where |t| ≥ 2. Conviction is their intersection and the action follows the reviewer's matrix: macro+/market+ → **LONG**, macro+/market− → **WAIT**, macro−/market+ → **TACTICAL ONLY**, macro−/market− → **UNDERWEIGHT**. It works: today it clears only **midcaps and gold** for size, and it puts **autos in WAIT despite the strongest relative move on the board (+9.4%)** because the regime study measures −24%/yr against that prior (t −2.1). A macro view is not a trade until the market confirms it, and the table is where that rule is enforced rather than described.

**WHAT CHANGED** — the missing question. Levels are a state; changes are news. Tiles compute the delta between the last two dated readings the page holds and print the transmission beside each. The headline is exactly the reviewer's ask — not "+64bp versus repo" but **"MARKET-IMPLIED POLICY STANCE · HAWKISHER ↑ +11bp"** (364-day bill 5.80% → 5.91%, 31 Aug → 1 Sep) with its implications (INR +, duration −, high-duration equities −, bond proxies −, banks mixed). That repricing also lifted the bill-implied path from 2.6 to **3.0 × 25bp of tightening**, and the 10-year to 6.96%.

Seeded with the RBI panel **as on 1 Sep 2026** (91d 5.26 · 182d 5.66 · 364d 5.91; 6.20% GS 2029 6.44 · 6.94% GS 2036 6.96 · 7.06% GS 2041 7.11 · 7.24% GS 2055 7.55) — note the benchmark stock itself changed at the belly and the long end, which the parser absorbed without a code change. Trail assertions in the tests are now date-agnostic, since these dates move on every pass.

Still open from that review, in priority order: a full position engine (the ledger already carries entry/side/horizon/mark — it needs stop, target, R-multiple, risk % and book-level aggregates: gross, net, risk budget used, largest macro factor, average correlation); the INR pressure decomposition (DXY / oil / FII / carry contributions netting to a bias); and "WHY NOW / WHAT CHANGES MY MIND" per open call.

### 6 · What 7.8% means (MACRO 0.06)
Under the GDP card: sector → industry → listed names for every GVA bucket (mapping hand-curated 1 Sep, labelled as such), the second-order effects with the page's live numbers (the RBI's own 6.7% implies ~6.3% average for the next three quarters; 2.5pp deflator = thin pricing power; credit 18.3% vs deposits 14.7%; GST buoyancy 1.4×; imports/CAD with Brent $92; nowcast 5.7% CPI → real repo −0.4%; Nifty P/E vs ERP), and **what 7.8% does NOT mean** (not a rate-cut signal, not broad-based, part base effect, not pricing power, not this month).

### 7 · NEWS redesigned
Headlines are clustered by theme — rates & the RBI · inflation & oil · rupee, reserves & flows · growth & data · gold & metals · global · the tape · single names & IPOs — each theme carrying a **"what it means"** line computed from the page's live numbers, a count, and a button into the relevant tab. A computed brief sits on top (regime, the dominant theme, the second theme, the next three calendar dates, the model desk state). The dated editorial stays visible; the blog essays and the deep dive fold into one `ESSAYS & DEEP DIVES` click-up. Feeds widened (ET/BS/Moneycontrol markets **and** economy feeds, plus the RBI's own release feed), deduplicated, 42 max.

### 8 · Hand-updated this build (dated on the page)
- HSBC manufacturing PMI Aug 52.8 final (five-year low; Jul 53.5), services flash 54.5, composite flash 54.6 — tiles in the macro blocks, threaded into the 7.8% panel, the DESK chain and the editorial.
- RBI home panel as on 31 Aug (G-secs + bills) seeded so the RATES tab is live before the first Actions pass.

---

## Data contracts
40 (v119's 34 + `RECS_LIVE` + `OIS_LIVE` + `MPC_LIVE` + `DESK_NOTES` + `VALIDATION` + `FROZEN_LEDGER`). `update_terminal.py` BUILD = `v124`; page stamp `v124`; **11 tabs**. `ml_models.BUILD_TAG` stays `v122` — see above.

## Verification run on this build
- `t119_wss` · `t119_doors` (contracts 40, BUILD v123) · `t120_rsv` · `t120_gsec` (parser + publication + carry) · `t120_ois` (Cbonds parser, const rewrite, anchor pass leaves the fixing alone, carry, trail) · `t120_typed` (zero typed literals in live tabs; MPC staleness flips/clears) · `t120_ml` (externalities, ledger emit/score/roll, block round-trip) · `t121_safety` (**the eight blockers across all three reviews, 63 assertions**): all pass
- cross-block audit: **149 checks, 0 failures** (also 0 on the blackout-mock output)
- blackout mock (every door refused) on a copy: 38/38 contracts intact, 10Y, term structure and the OIS fixings carried with their dates, ledger untouched, all tabs render, zero console errors
- full `ml_models.py` run on the copy: completes; synthetic-panel guard confirmed ("ledger untouched this pass")
- headless render of all nine tabs: no empty containers, no page errors

## Honesty notes
- The OIS fixings come through a mirror that lags a few sessions; the page prints the fixing date everywhere it uses the curve, and the official bill/G-sec curve is printed beside it as the daily check. If Cbonds ever blocks the runner, the last fixings carry with their date (flagged CARRIED).
- Accuracy on the model desk is **measured, not claimed** — until eight closed calls a model reads "accruing". The first calls appear on the first ML pass after upload; the first scores 5–10 sessions later.
- The industry/name mapping under the GDP print says where growth is *booked*, not what to buy; the screens and the ledger rank names.
