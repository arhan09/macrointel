# MacroIntel v127 — the arena, the chain, tomorrow's risk

**Upload** at the repo root (replace same names), then Actions → *daily-update* → **Run workflow**:
`macro_intelligence_terminal.html` · `update_terminal.py` · `ml_models.py` · `fno_setups.py` · `tearsheet.py` · `.github/workflows/daily-update.yml` · `t121_safety.py` · `t122_validation.py` · `t125_desk.py` · `t126_desk.py` · **`t127_env.py`** · `README-v127.md`

**Built on the deployed v126** — the reviewer's build, pulled from the repo and verified against the live page before a line was changed. Every v126 feature is carried (the F&O desk, the bootstrapped OIS curve, the FBIL feed, the path-scored ledger, NOTES OFF). Five suites green: `t121` · `t122` · `t125` · `t126` · **`t127` (73 checks)**. 43 data contracts (adds `OPTIONS_LIVE`, `RISK_LIVE`). Page stamps **v127**; `ml_models.BUILD_TAG` moves to **v127** because the model changed (below), so the frozen record starts a new version — the promotion framework working, not a cost to avoid.

---

## What you asked for, and what it honestly is

**"Nifty fell, ICICI was down 2%, we need to predict that."** No model on this page can call a −2% single-stock day two sessions ahead, and the VALIDATION tab's own findings — no cross-sectional edge, buy-and-hold beats the ranker — are still the findings. What the page *can* do the evening before, and be scored on the morning after, is now built, in three parts (§3), and the first post-mortem case is 7 → 8 September: the record frozen at 21:08 on the 7th shows the tape at −2 DEFENSIVE, a six-week low, breadth 46% — and the model desk **long HDFC Bank** into a bank-led selloff. The page had the warning and did not act on it. That is now a panel, not a memory.

**"Make validation like RL — an environment where an agent trades on the model and we see returns after 7/14/28 sessions."** Built as **THE ARENA** (§1). The agent is the page's own decision chain; the environment is the market; the reward is what every call earned at 7 · 14 · 28 · 56 sessions net of costs, beside the index over the same window. One bounded sizing multiplier per (model, regime) learns from forward reward only. It is a contextual bandit with its rule printed, not a trained policy — a static page and a six-times-a-day job cannot train anything on this sample, and any "learning" from sixty days of record is noise.

**"For F&O add every option available, with detailed insight."** Every strike, every expiry, every underlying in the bhavcopy, priced for implied vol (§2). The full chain is a separate file loaded on demand; the insights ride on the page.

**"Macro aligned, sub-elements, alfie-like thinking."** The TRANSMISSION table (§4): every macro sub-element the page carries, the sectors it reaches, and the theme board's current action on each — so the chain from a CPI group to a position is one line long and checkable. The sub-elements are frozen into the daily record as the environment's state.

---

## 1 · THE ARENA — VALIDATION tab, section 0

**The agent** is regime → theme board → confirmation → sizing → names, exactly as the DESK and the F&O desk show it. **The action set** is every call the ledger already carries (stock rankers, wide ranker, metals, the Nifty rule, and v126's F&O setups). **The reward** is the fixed-horizon net return at **7 · 14 · 28 · 56 sessions** after entry — one round trip at the normal core cost level deducted, the Nifty's return over the identical window beside it, and the R-multiple where the call carried a stop. Marks are persisted on the ledger row; a horizon is scored once and never rescored.

**The forward record** aggregates per horizon, per model, per regime-at-entry and per market-state-at-entry (mean net, median, hit, t discounted for calls sharing a window, mean R, share that beat the Nifty), and chains **non-overlapping** calls into a paper-desk curve at 0.25% of capital at risk per call. It is empty at upload: the first 7-session marks appear a week after the first pass, the first 56-session marks eleven weeks later. That is the honest speed of a forward record, and the tab says so.

**The one thing that learns.** Per (model, regime): `m = clip(1 + 0.25 × mean net R at 14 sessions, 0.5, 1.5)`, **inactive until the cell holds 20 scored calls**, printed as a table with n. The page sizes by the promotion ladder alone until a cell activates.

**The backtest**, labelled and in its own block: the same policy through the purged walk-forward the decile study already runs — one decision per out-of-sample bar: the ranker's top decile, minus the names whose sector the *point-in-time* regime prior × 60-session sector RS reads UNDERWEIGHT or AVOID, at half size unless the reconstructed tape reads CONSTRUCTIVE — scored at each horizon beside the ranker with no macro layer and beside the index; curves chain every h-th bar. **The cross-asset stress gate is not reconstructed** (no MOVE/HYG history in the model pass) and the block says so. Null-tested on a 60-name × 1,400-day random-walk panel: policy t 0.03–0.79 across horizons, policy−ranker t ≤ 0.73 — no spurious edge.

**The record now describes the page.** Every row frozen through 8 Sep says `market_state: CHOPPY` — the demoted HMM's label — while the DESK that day read DEFENSIVE. `fno_setups.py` (v126's headless evaluation) now returns `page_state` — the mechanical state, tape, stress and its trust flag, the size cap, the stance, the theme board, the macro sub-elements — and `ml_models.py` freezes *that*, naming the source (`page:mechanical`, or `hmm (page state unavailable)` as a labelled fallback). Rows from before this build show *hmm label · pre-v127* on the tab. The one seeded row (2026-09-02, frozen on a build machine in a v122 test, payload never in the repo) is **marked and struck through, not deleted** — the ledger is append-only — and the workflow's new verification step excludes it and fails the run if any *other* published row has no payload on the site.

## 2 · THE OPTION CHAIN — MICRO › F&O

`options_chain_from_rows()` prices every option contract in the bhavcopy: **Black-76 on the near future** with the page's own 91-day bill as the carry, bisection for implied vol, delta per contract. A settlement print outside the no-arbitrage band gets **no vol rather than a fabricated one**; dead strikes (no OI, no volume) are dropped. Per underlying × expiry: ATM strike and IV, the **ATM straddle as the market's own expected move** to expiry and per session, **25-delta skew**, the **IV term structure**, PCR by OI and by volume, **max pain**, and the OI walls above and below the future.

The full chain (a few MB) goes to `options_chain.json` — copied to the site by the workflow, regenerated every pass, not committed. The insights ride on the page as `OPTIONS_LIVE`. The F&O sub-tab opens with index tiles (Nifty, Bank Nifty, FinNifty, Midcap where present), a stock table ranked by implied move with **IV ÷ realised** (above 1.5 = the market is paying for a move the last month did not deliver), and a "chain" button that renders the strike ladder — OI bars, ATM row, walls, max pain, in-the-money shading. Every F&O card carries the name's option read beside its trade expression.

The straddle is the one forecast on this terminal that is not ours: it is what other people are paying for the range, and §3 reads it beside the page's own number.

## 3 · TOMORROW'S RISK and the POST-MORTEM — DESK

**The range.** Per name, a RiskMetrics EWMA (λ 0.94) of daily log returns where daily history exists, else the weekly-derived vol ÷ √252, labelled; one-session and five-session 1σ; the option market's implied per-session move beside it; **P(−2% day)** from the normal tail. On sessions the calendar flags, the range is scaled by a multiplier **measured on the page's own history** — mean |Nifty return| on the session after an India CPI release ÷ every other session, with n printed — and **floored at 1**: twelve observations are not enough to trade a calmer CPI day.

**The warning score**, 0–6 per name from the name's own tape: below the 50- and 200-session means, negative 20-session momentum, weaker than the Nifty over 20 sessions, volatility rising, and the derivatives market leaning short (put skew ≥ 1.5 vol, or a short build-up in its future). Scored across the whole 1,100-name universe; **listed from the tradeable universe** (the F&O futures table, else the liquid core), because a 5-of-5 on an illiquid micro-cap is noise. On 1 Sep data: HUL and Power Grid 5/5, Airtel, ITC, Maruti and **HDFC Bank 4/5** — the bank the model desk was long.

**The record.** Every day's HIGH and LOW lists are kept on the page; once an entry is seven sessions old it is scored — mean 7-session return of HIGH names minus LOW names, from the weekly history — and the panel prints the mean spread, the share of days it was negative, and n. Until n exists the panel says: *the score is a screen, not a forecast.* That sentence is the whole claim.

**The post-mortem** reads `history/pred_<previous session>.json` from the site (v126 made them fetchable) and prints: what the page said at its cutoff — regime, state (and *which model wrote it*), tape, stress, stance, cap — the open calls **signed by side against the day's move**, and, from this build on, whether the index move landed inside the range the page had published and how the HIGH-warning names did against the index. The evening's ranges and warning list are frozen into the payload (`risk`), so the morning scores a number that existed before the session.

## 4 · TRANSMISSION — MACRO tab, section 0.15

Twenty-three sub-elements: the twelve CPI groups the pipeline already parses (food, housing, transport, health, personal care — which carries gold — and the rest), rural vs urban CPI, the three WPI groups, IIP by sector and use-based class, GVA by sector, credit and deposit growth. Each row: the live reading and period, the sectors it transmits to with sign, and **the theme board's current action on each** — so "food CPI 5.24% → FMCG (WATCH) · NBFC (WATCH) · duration (WAIT)" is one line. The map is the framework and does not change with the data; the readings do; the readings are frozen into the day's payload as `macro_sub`, so the arena can condition on them once the record is long enough.

`update_terminal.py` gains parsers for **GVA by sector** (the national-accounts table — each sector's growth read by name adjacency, the row cut at the next sector name so nothing is read from the row below) and **IIP by use-based class and sector** (the "Mining, Manufacturing and Electricity … are x%, y% and z% respectively" phrase plus the use-based list). Both print *not yet read* until the pipeline has seen a release that carries the table; nothing is typed.

## 5 · What was ported from my v125 that the deployed v126 did not have

The reviewer and I fixed the same three blockers in parallel (his shipped; mine did not), and his v126 also caught the tape's null-sum bug and did the cross-sectional calibration. What his build still lacked, now on it:

- **The gate is computed outside the renderer** (`stressCompute()`, memoised) — `marketState()` no longer depends on one panel having rendered; the composite carries `trusted` and a minimum-gauge parameter; a partial composite is quoted as partial ("on 6 of 7 gauges — missing …"). Tested at 2-of-7 (unmeasured, banner, reduced size) and 6-of-7.
- **Prints, not rows.** `serHealth()` reports absence and staleness separately; `_rel`/`_absRet` measure over prints and refuse an uncovered window; the proxy chain is v126's own `SERIES_PROXY`, extended to Bank Nifty, IT, Pharma and the Nifty ETFs.
- **Two horizons decide the action.** Both must clear ±1.5% the same way, else **SPLIT → WAIT**; 20d and 60d have their own columns; a sector with no 20-session median is dropped from the aggregate rather than counted as zero.
- **The nowcast belongs to the meeting it names.** v126's `_cpiNext()` hard-coded `rows[0]` — right in September, wrong from 12 October when rows[0] becomes a print published after the 6 October meeting. `_cpiAtMPC()` picks by publication date; `_cpiNext()` keeps v126's return shape for every call site. Oil enters at the published six-week lag. The three remaining "by Oct" sites are gone.
- **The desk opens with evidence:** five measured-edge lines read live from VALIDATION and the arena, above the book. **THE BOOK drops the unsized model calls** (they accrue in the ledger and the arena). The confirmation panel is titled for what it measures — **rotation, not direction** — quotes the tape inline, and its risk-appetite check tests the WATCH threshold, so 42/100 is no longer a tick.
- **The HMM row** carries a Bonferroni bar for its own test count (2.39 for three states) and states it is in-sample end to end; `by_regime` publishes independent periods beside bars; `series_health()` is a RUN_LOG subsystem; `hstats` is fail-safe.

## 6 · Verification

- `node --check` on the page's script: clean. Every tab renders headless with **zero renderer warnings**; 11 tabs; page stamps v127.
- **Five suites, no failures**, all taking `MI_ROOT` so they run in CI: t121, t122, t125, t126 (the reviewer's, brought forward for the version and the two rules that changed shape), t127 (new, 73 checks).
- Arena: null-tested on a random-walk panel (no spurious edge); marks, per-cell aggregation, bandit gating and the backtest rendered from a synthetic block.
- Option chain: the IV solver round-trips a known 14.0% vol to 14.03%; walls, max pain, skew sign and term structure verified on a seeded chain; the desk and the strike ladder rendered from it.
- Risk: ranges, warning list and record computed from the published history; post-mortem rendered against a frozen payload.
- Degraded path: 2 of 7 gauges → unmeasured gate, banner, reduced size, `stress_trusted:false` in the record.
- Mock pipeline on a **copy**, never in place.

## 7 · What this build still does not claim

No measured edge — the VALIDATION findings stand, and the arena's forward record is empty until the sessions pass. The bandit is inactive in every cell. The backtest promotes nothing. The warning score is a screen until its record exists. Every model-sourced position stays capped at 0.25% of capital. Describe it as a macro trading research and decision-support system with an environment that now scores it.

## THE PAPER BOOK (added on Arhan's 9 Sep request) — ₹1 crore, live

`window.PAPER_BOOK` on the page, `history/book_<date>.json` in the repo, rolled by
`paper_book_roll()` in `ml_models.py` on every ML pass (11:15, 15:15, 18:00 IST and any
manual run). **The 18:00 IST pass is the day's book.** The panel leads the DESK.

- **Capital** ₹1,00,00,000. **Every position 4–12 % of equity.** Sleeve caps: stocks 48 %,
  F&O 24 %, gold 12 % (GOLDBEES), silver 6 % (SILVERBEES), duration 10 % (LTGILTBEES); the
  rest is cash at 5.25 % p.a.
- **Who trades:** every ledger agent (fno, stock-short, stock-long, wide-30, metals,
  nifty-rule) plus the macro board itself (gold / duration when the theme reads LONG).
- **Size** = clip((6 + score) × state cap, 4, 12). Score = model base + theme-board
  alignment on the name's sector (LONG HIGH +3 / MED +2 / LOW +1; WAIT or TACTICAL −1;
  UNDERWEIGHT vetoes a long) + arena multiplier (m−1)×4 once the (model, regime) cell is
  active + tomorrow's-risk flag (HIGH −2 on a long). Cap: CONSTRUCTIVE ×1, ELEVATED /
  DEFENSIVE / MIXED ×0.75, STRESS → equity and F&O stand down.
- **Fills** at the close the call was made on, both sides paying half the India cost stack
  plus 10 bp slippage. **Exits:** the ledger's stop / target / due; the board flipping
  against the side; the gate reading STRESS; the book's own −8 % stop on calls with none.
- Idempotent within a day (a second pass re-marks and re-checks exits, never re-enters).
  Nothing is rescored; each day's book is snapshotted.
- GOLDBEES is now a first-class market series in `update_terminal.py` (`MARKET`).
