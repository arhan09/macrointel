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

## v128 (12 Sep 2026) — less on the screen, more answers

- **SIMPLE / FULL switch** (top right, default SIMPLE, remembered per browser). SIMPLE
  shows what a desk needs; FULL shows every panel. Nothing was deleted.
- **❓ Q&A tab** (second tab): ten questions answered from the live blocks in plain
  language — regime and why · is it a market to take risk in · long / short / avoid ·
  which F&O setups are live · how far can it move tomorrow · what is driving it (oil,
  rupee, rates, positioning) · what will the RBI do · gold and silver · what the book is
  doing · what the model has got wrong. Plus the ask box: a question, or a share name.
- **Ask about a share** (top of the F&O sub-tab, and in Q&A): type a symbol → the chain
  industry (regime → prior → transmission → board action) → the name's own tape →
  derivatives (future, OI, options) → tomorrow's risk → what the model does with it →
  the read.
- **A reason on every ranked share** (MICRO short and long lists): 1m/3m, vs 50/200-day,
  52-week position, sector → board action with the prior, risk score.
- **CHARTS**: three new views beside the pack — SHARES (any name, with the ledger's
  entry/stop/target drawn), F&O (Nifty/Bank Nifty with walls and max pain, today's setups
  with stop and target, who is positioned where), COPPER · GOLD · SILVER · OIL (copper,
  GOLDBEES, SILVERBEES, gold, silver, Brent, WTI, gas, USD/INR, long gilts).
- The demoted HMM card is off the model desk. The model and the book are stated as
  separate: calls are the information, the book is the test.
- **State recovery** (`ml_models.py`): the frozen ledger is rebuilt from
  `history/pred_*.json`, the calls ledger from `history/ledger_latest.json` (new, written
  every pass), the book from `history/book_*.json` — whichever is newer than the page. A
  zip uploaded with older data blocks can no longer roll the record back.
- This zip's HTML carries the live site's frozen ledger (19 rows to 11 Sep), calls
  ledger, book and arena as of 12 Sep 12:58 UTC, so nothing is lost on upload.
- Page stamp v128, updater BUILD v128; the model tag stays v127 (no methodology change).

## v129 (12 Sep 2026) — the dials: macro decides the whole book, not just the sectors

- **THE DIALS** (DESK, under the book; also on Q&A): liquidity, growth and inflation read off
  prices every day, beside the regime read off monthly data. Liquidity: call rate vs repo,
  OIS 1M vs repo, HYG/LQD 60d, MOVE 60d, the stress composite, rupee-vol percentile.
  Growth: India 3y–10y slope change, cyclicals vs defensives, copper/gold, midcaps vs Nifty,
  credit minus deposit growth, Russell/Dow. Inflation: Brent 60d, USD/INR 60d, US breakeven
  change, gold in ₹ 60d, India 10y change, OIS 1Y−1M. Each vote ±1 against a fixed
  threshold; a dial is UP/LOOSE at +2, DOWN/TIGHT at −2.
- **Disagreement sizes the book**: one axis against the data regime ×0.85, both ×0.70; both
  dials strong and agreed +1 conviction. Frozen into the payload as `dials`.
- **Three cross-asset sleeves in the paper book** (positions carried, no restart):
  RATES 12% — DURATION (long LTGILTBEES) / BEAR STEEPENER (long GILT5YBEES, short LTGILTBEES)
  / FLATTENER (the reverse) / CASH, from OIS 1M→1Y and the dials; replaced only when the view
  changes. THE RUPEE 8% — USD/INR (NSE future, marked on INR=X) long/short on a 6-vote rupee
  dial (trend, Brent, DXY, FII flows, reserves, real-rate gap), a long pays the forward
  premium daily, 2.5% stop. GOLD AS THE HEDGE — GOLDBEES sized at 10% of equity exposure,
  20% when policy-error risk is live (inflation dial up, stress ≥ 35 or liquidity tight),
  rebalanced at 2% moves; one gold position in the book (max of call size and hedge target).
- The macro-board duration sleeve is retired (the rates sleeve covers it).
- Page stamp v129, updater BUILD v129, model tag stays v127.

## v129.1 (14 Sep 2026) — small fixes from the live review
- Dials: the cyclicals-vs-defensives basket is forward-filled over gaps (it read "unmeasured" live).
- The rates line prints the OIS fixing date and flags it stale when the FBIL feed has not updated for a week.
- Post-mortem lists a name once per side, however many agents called it.
- Positions carry the pass they were entered on (marked "intraday" when the pass ran before the close).
- Calendar: India CPI (Aug) on Monday 14 Sep (the 12th is a Saturday).
- Carries the live record as of 14 Sep 14:12 IST (20 frozen rows, 56 open calls, the restarted book).

## v130 (14 Sep 2026) — the labour market, and the book waits for the close

- **THE LABOUR MARKET** (leads the MACRO tab; 👷 LABOUR view on CHARTS; "How is the labour
  market" on Q&A): India's monthly PLFS — unemployment rate, labour-force participation,
  worker-population ratio (15+, current weekly status), urban/rural and female where the
  release prints them — plus EPFO's net payroll additions, read off the PIB wire every pass
  (`fetch_labour`, `_plfs_from_text`, `_epfo_from_text`) and kept as a monthly trail
  (`LABOUR_LIVE`, a new data contract). Seeded from the bulletins' own tables (Jun 2025 →
  Jul 2026; PIB 2284814, 2300447, 2240676). The read (TIGHTENING / LOOSENING / STABLE) is the
  three-month change in unemployment against participation; it votes in the growth dial and
  is tied to the consumption themes on the card.
- **The book waits for today's close.** A pass that runs before the print exists (11:15,
  15:15, or a manual run before 15:30) marks positions but enters nothing and applies no
  rule exit — the 14 Sep restart had filled at Friday's closes at 13:58. Ledger-driven exits
  keep their own dated prices.
- `.sub` lines (the essentials under every tile) are always visible; `.note` stays behind
  NOTES ON. `.grid4` tiles are a real grid.
- Page stamp v130, updater BUILD v130, model tag v127.
- (15 Sep) Copper leads the RESERVES & FX tab: price, 20d/60d, copper/gold 60d (the dials' growth vote), the rupee and the dollar over 60d, a one-line read, and two charts. Carries the live record as of 15 Sep 09:54 IST (24 frozen rows, 56 open calls, the book).

## v131 (15 Sep 2026) — TOP 5 TO WATCH

- **TOP 5 TO WATCH** leads the F&O desk (`#watch-fno`) and the STOCKS tab (`#watch-stocks`).
  One printed rule: every name with a mechanical side — a desk SETUP, an open ledger call, or
  the board's action confirmed by the screen — is scored leg by leg on how much of the chain
  agrees with that side: regime prior → board → dials → the future's own book → the name's
  tape → the screen → options (max pain) → tomorrow's risk → the ledger. Each leg votes +1 / −1
  / 0 (unmeasured legs are shown grey, never counted). The five with the most agreement lead;
  "show all" opens the whole ranked list. Spot, the desk's own stop (2.5σ of 20 weekly log
  returns, 3–12%), the 2R target, the agreeing legs as the reason, and what would take it off
  the list. A gated long never makes the list (the same rule as the desk). Clicking a name
  runs the full macro→micro chain in the ask bar.
- The top five ride into the day's frozen record (`pageState().watch` →
  `history/pred_<date>.json` `"watch"`), so the list can be audited against what happened.
- "What should I watch / top 5 / watch list" is answered on the Q&A tab.
- Page stamp v131, updater BUILD v131, model tag v127. Carries the live record as of 15 Sep.
- **The list's own record.** The footer under the list scores the list, not the ledger: every
  frozen top five is entered at the first close on/after its date and closed at the first close
  through the card's stop or 2R target, else at the 15th session (SHORTs as −return); a list
  counts once all five are closed. Computed on the pass (`score_watch_lists`, from
  `history/pred_*.json`) and carried in the ledger block as `RECS_LIVE.watch_record` (no new
  contract). Until the first list closes the footer says so and names the date; the ledger's
  record of the model calls stays on the DESK and VALIDATION tabs.

## v132 (15 Sep 2026) — THE CALL, the RECORD, the push

- **The page opens on THE CALL.** Today's date; the regime and the state in one line (with the
  dials' agreement, the rates and rupee views, the themes with a full signal); what changed
  since the last frozen pass (regime, state, stance, stress, tape, new and closed calls, the
  book's trades, the labour read); the index (Nifty, the straddle's expected move, the walls
  and max pain, the index rule); TOP 5 TO WATCH; the record — three records, each labelled
  for what it is (the list as printed, every model call, the paper book); the ask bar. The
  deep tabs (MACRO, RATES, VALIDATION, GLOBAL, NEWS) sit behind FULL; SIMPLE shows THE CALL,
  DESK, Q&A, MICRO, CHARTS, RECORD, RESERVES & FX (copper, the rupee) and COMMODITIES.
- **RECORD tab** — what the page said, and what happened: the list's record (summary + every
  scored name), the calls (totals, per model, by month, the last 25), the paper book (equity vs
  the Nifty since inception, by agent, the daily curve), and the frozen days (regime, state,
  stance, stress, tape, calls, hash). Nothing on it is revised after the fact.
- **The five are five ideas:** at most two names per theme make the five (the ranked list is
  untouched; a name held back by the cap says so under "show all"). The cap applies on THE
  CALL, the F&O desk, the STOCKS longs and shorts, the Q&A answer and the frozen record.
- **The push** (`push_call.py`, in the workflow after the post-close pass): the call — the
  line, the five with stop and target, the record, the link — to a Telegram channel or group.
  Two repository secrets, never anything in the source: `TELEGRAM_BOT_TOKEN` (from
  @BotFather → /newbot) and `TELEGRAM_CHAT_ID` (add the bot to a channel as admin and use
  @channelname, or the numeric −100… id). Without them the step prints the message in the run
  log and exits clean. A manual run pushes only when "push" is ticked. The message is composed
  from `fno_setups.json` (the page's own state) and `ml_output.json` — it cannot disagree with
  the page.
- Page stamp v132, updater BUILD v132, model tag v127; tab count 14.

## v133 (16 Sep 2026) — the F&O desk made clear, 1D/1W, the RECORD last

- **F&O — THE TRADE** leads the sub-tab: every full setup (the regime prior and the board on one
  side, the future's own book confirming) as a short or a long with the reason, the future's
  read, the stop and 2R target, and **the option that expresses it, priced off the published
  chain**: the at-the-money contract on the nearest expiry that outlives the 15-session horizon
  (premium, % of spot, delta, IV, breakeven vs the target) and the spread to the target strike
  as the cheaper way to say the same thing (net cost, max payoff, ratio), beside the market's
  own forecast (straddle, max pain, PCR). WAIT means no position, and the card says why.
- **THE INDUSTRIES IN PLAIN WORDS** — one card per theme: what the regime does to it (the prior
  and the reason), whether the market dials agree, how it is trading (20/60-session relative,
  today's futures, longs vs shorts building), what feeds it (the transmission rows), what the
  desk sees (setups, waits, tacticals) and the read in one sentence.
- **NEXT WEEK'S CONTENDERS** — the wide ranker now learns a **5-session horizon over the F&O
  universe** (every F&O name joins the ~270-name panel): the ten it likes most and the five
  least, each with its percentile, the desk's setup and the nine-leg chain read; reported with
  its out-of-sample rank-IC, t, hit and skill label. Top three long and bottom two short go on
  the ledger as **fno-5** calls (5 sessions), so the record scores the model.
- **STOCKS** — the lookup, its verdict (the prediction signal) and the industry reads are no
  longer hidden in SIMPLE (that was the "chart isn't working"); the chart has **1D** (the
  session at five-minute bars from `intraday.json`, written by every pass for the core universe,
  every F&O name and the index) and **1W** beside 1M/6M/1Y/5Y.
- **RECORD** is the last tab and opens on **POSITIONING — what the agents bought, and where it
  was five sessions later** (every book entry at its fill vs the close five sessions on, hit and
  average). VALIDATION is off the bar; its panel stays behind the RECORD ("open the validation
  engine →", with a way back). No tab hides in SIMPLE.
- Stamps: page v133, updater BUILD v133, model tag v127; tab count 13.

## v134 (16 Sep 2026) — fewer words; EARLY MOVERS

- **Fewer words.** THE TRADE rows are tickets: name · side · spot · stop (%) · target (%) · legs
  agreeing; the future line; the option in one line (strike, expiry, premium, %, Δ, IV, breakeven)
  and the spread (net, max, ratio); the chain as chips (green/red, one per leg); the words behind
  "▸ why". The industries lead with numbers (board, prior, 20d/60d vs Nifty, today, OI builds,
  setup counts, the feeds as chips) and a one-line read; the theme's reasoning behind "▸ why".
  The watch card's WHY column is chips. Headers and footers cut to one line.
- **EARLY MOVERS** (STOCKS, under the watch card; Q&A "what is breaking out"): over every share
  the pipeline screens weekly — a close at a new 20-week high, ≤3 weeks old, 4-week relative
  strength ≥ +3pp vs the Nifty, <20% above the old high; ranked by RS; last, 4w, RS, 13w, weeks
  at the high, distance above the old high, the screen's verdicts, an 8% stop. Frozen into the
  daily record (`pageState().early`) and scored 20 sessions on (stop 8% / target 16%) →
  `RECS_LIVE.early_record`, printed under the table. Ellenbarrie's August turn (₹264 → ₹380) is
  the kind of move this catches on its first leg.
- Stamps: page v134, updater BUILD v134, model tag v127.

## v135 (17 Sep 2026) — TOMORROW, SECOND OPINION, the computed editorial

- **TOMORROW** (THE CALL, under the index tiles; Q&A "will the market rise tomorrow"; in the
  push): will the Nifty close up or down next session. A walk-forward logistic model on the
  index's own daily history (1/2/5/20-day returns, distance to the 20-day mean, 10-day vol and
  its regime, the previous US session, the rupee, Brent, India VIX level and change, Monday/
  Friday), refit every ten sessions, scored out of sample over the last 250 sessions against
  the base rate. Printed as a probability with what pushed it; **a pass before 15:35 IST never
  uses a partial session**. Frozen into the daily record and scored at the next close
  (`RECS_LIVE.tomorrow_record`: n, hit, last-20, Brier).
- **SECOND OPINION** (COMMODITIES under the metals report; RESERVES & FX under copper; THE CALL
  under TOMORROW): the freshest dated headlines about gold, silver, copper and the index from
  eight free feeds (ET/BS/MC commodities and markets, Mining.com, Kitco), each tagged with its
  lean by a printed rule (the subject's own clause, up-words vs down-words), counted, and set
  beside the page's stance: "the wire seconds the page" / "leans against" / "split". `VOICES`
  is a new data contract (45).
- **THIS WEEK IN THE DATA** is computed from the blocks at every pass (regime, inflation, growth,
  money, external, flows, the tape, the calendar) — the 1 Sep typed editorial is dated, renamed
  and folded with the essays.
- Stamps: page v135, updater BUILD v135, model tag v127.

## v136 (24 Sep 2026) — AGENTS · LIVE MARKETS, THE DIP, the schedule fixed, every listed name

- **The schedule.** The page had stopped moving in the morning because GitHub queued the
  :45/:30 crons for hours at peak and, on days the Nifty moved >0.4% intraday, the regression
  step failed t125's "struck on different sessions" check (a timing finding, not a structural
  one — now filtered). Crons move to off-peak minutes (03:53, 05:23, 07:23, 10:07, 10:41,
  11:19, 12:03, 13:29 UTC = 09:23, 10:53, 12:53, 15:37, 16:11, 16:49, 17:33, 19:59 IST); the
  ML/push/tear-sheet steps are decided by the firing schedule, not the clock, so a late run
  still does the right work; five post-close attempts, the push once a day
  (`history/push_<date>.done`).
- **AGENTS · LIVE MARKETS** (the last tab, in the RECORD's slot; the records ride under it; the
  positioning table is retired): three books of ₹1 crore, 5% a position, at most 20, filled only
  at a real close with 10 bp a side, idle cash at 5.25%. **F&O ONLY** trades every full setup on
  the F&O desk (the desk's stop, 2R, 15 sessions). **MODEL CALLS** takes every open call on the
  ledger, whichever model made it, and leaves when the ledger closes it. **THE TAPE** trades what
  the whole-market screen sees: early movers long (8% / 16% / 20 sessions), the 5-session
  ranker's laggards short where a future exists (6% / 12% / 5 sessions). Leaderboard against
  ₹1 crore left in the Nifty, each book's holdings with entry, mark, P&L, stop/target/due, what
  it did today, what it skipped and why, closed trades, the three equity lines. `window.AGENTS`
  is rolled by `agents_roll` in ml_models (snapshots `history/agents_<date>.json`, recovered
  like the book). The DESK opens with **THE AGENTS**: each book's equity, P&L to date, cash
  balance and holdings.
- **THE DIP** — the question most pages never answer: after a share has run, at what price does
  it usually give some back. A pooled walk-forward logistic over every name the daily panels
  carry (distance over the 20- and 50-day means, the 5/10/20-session run, share of up days, RSI,
  the vol regime, distance to the 52-week high; trained to T−140, tested T−130..T−11, refit on
  all) gives each name the probability of a ≥5% drawdown within 10 sessions, **the price after
  which that crosses 60% ("fades above")** and the 20-day mean under which the run is over.
  On STOCKS (the twelve most at risk), on THE CALL (five among F&O and early movers), on every
  lookup (its own line), as a chip beside early movers and long tickets. The top flags are frozen
  each pass and scored at 10 sessions (`RECS_LIVE.dip_record`); the model prints its
  out-of-sample AUC and accuracy against the base rate.
- **Every listed name.** The lookup already resolved 2,538 NSE names; it now also resolves
  BSE-only listings by symbol, scrip code or name (`window.BSE_LIVE`, contract 46, from the
  BSE equity bhavcopy — only names with no NSE line, so the block stays small; carried forward
  with its own date when BSE refuses the runner). The STOCKS watch list draws on every screened
  name with a decisive weekly verdict (BUY ≥70 / AVOID ≤30), not just the core.
- **Rupee gold checked** (COMMODITIES, above the metals report): the IBJA fix (hand-carried,
  31 Aug — IBJA blocks the runner) is labelled stale when older than three days and set beside
  the two live reads the page already trusts — live $ × the stored wedge, and the GOLDBEES-implied
  price — with the gap between them.
- Stamps: page v136, updater BUILD v136, model tag v127.

## v136.1 (25 Sep 2026) — a crash is not a contender

- PB Fintech fell 36% on 24 Sep on the IRDAI commission paper and topped NEXT WEEK'S CONTENDERS
  the next morning: the 5-session ranker only sees price, and an extreme one-week loss sits at the
  end of its mean-reversion leg, where a tree ensemble extrapolates from a handful of past events.
  It was never on the ledger (fno-5 takes F&O names only, and the page reads PB Fintech as not
  F&O), but the card gave it rank 1 without saying why.
- Every ranker pick now carries its own tape (`r1`, `r5`) and an **event** tag when the move is a
  ≥12% day or a ≥20% five-session move (`_tape_tag`). The card shows the contenders — F&O names
  with no event — ranked, with a 1D · 1W column, and lists the rest apart ("also high on the
  ranker, not contenders: PB Fintech · pctl 100 · not F&O, event −36% in a day"). The ledger's
  fno-5 calls and THE TAPE agent's shorts skip event names. The 5-session slim keeps 20 names so
  the F&O contenders survive the filters.

## v137 (28 Sep 2026) — OIS · MIBOR live, the lists in their pages, the agents' tape, every 90 minutes, why trust it

- **The schedule.** Nine passes a day, every 90 minutes from 08:07 to 20:07 IST (off-peak minutes),
  models on every pass. **The books fill only after 15:35 IST** (`_after_close_ist`, on both the
  paper book and the three agents): an intraday pass marks and waits — a partial session is not a
  print, whatever the panel's last row says. The push still goes once a day; the tear sheet at
  17:07 / 18:37.
- **OIS · MIBOR, live** (`js/oisx.js`, the first card on RATES · OIS). FBIL's fixing lags the
  runner by days; the card carries it forward with the official bill and gilt move since its date
  (1M–3M by the 91-day bill, 6M–9M by both bills, 1Y by the 364-day bill, 2Y–5Y by 0.8 × the 10Y),
  labelled "FBIL LAGS n d", and prints the fixing, the move and today side by side. **The path by
  meeting**: the forward overnight rate between MPC decision dates off that curve, plus the
  repo − MIBOR basis, as the repo the market prices after each meeting — in bp and in 25bp moves,
  with the peak; the next meeting from the page, later ones on the two-month cadence and marked.
  **The direction**: 3M / 1Y / 5Y swap changes over a week and a month, beside the 364-day bill
  and the 10Y gilt, with the one-line positioning read. The tab's prose and the empty
  "what rates are telling you" placeholder are folded (NOTES OFF hides them).
- **STOCKS, separated.** Nothing sits above the sub-tabs any more. SHORT TERM · 1–20 sessions holds
  the five (15 sessions), the early movers (20), the dip (10), today's movers, the sector tape;
  LONG TERM · months opens on REGIME → MICRO and the long-term list; F&O ONLY holds the desk, the
  trade, the industries, next week's contenders, the chain.
- **The agents' tape** (`js/agtape.js`, on AGENTS and the DESK): every holding of the three books
  as a moving line — price, day %, which book, P&L on the position — marked from the browser when
  a live door exists (Yahoo directly, or a Cloudflare Worker whose URL is the repository
  **variable** `MI_PROXY`, injected by the updater; not a secret, it is public in the page), else
  from the last pass's 5-minute snapshot, else the last close; the strip says which, and the three
  books' equity is re-marked live beside it.
- **WHY TRUST IT** (`js/trust.js`, on THE CALL under the dip): the chain macro → regime → sectors →
  names → sizing → the books, one row per link, each with the number that backs it today (what
  was read live, what is hand-carried and how old; the regime's three cross-checks; sectors
  clearing |t|; the rankers' out-of-sample IC/t/hit; each list's own record; the cap and the
  close-only fills; the books against the Nifty) and the caveat that limits it, plus what was
  done about it — and a last row for what the page does not do. Computed from the blocks every
  load: a record that has not scored yet says so.
- Stamps: page v137, updater BUILD v137, model tag v127.

## v138 (29 Sep 2026) — conviction, the analysts, the wire by topic, the mail

- **CONVICTION** (`js/conviction.js`): one number per name from what the page already knows —
  how much of the chain agrees (±25), a full desk setup (+10) or a theme-only / price-only read
  (−5), the regime against the market dials (+5 / −10), the gate (−15 on longs), an event in
  the tape (−25), the dip risk (−7 / −15 on longs, +5 on shorts), the list's own record once it
  has 20 names (±), the 5-session ranker agreeing when its t ≥ 2 (+5), tomorrow's call (±3).
  HIGH ≥ 70, MED 45–69, LOW < 45, as a chip with its reasons on the five, the trade tickets and
  the contenders; carried into the frozen record, the push and the mail. **CONVICTION TODAY**
  on THE CALL: how much to trust any call today (regime vs dials, the gate, India VIX, tomorrow,
  the wire's lean, the list's record, live alerts).
- **THE ANALYSTS** (`analysts_run` in the updater, every pass → `window.ALERTS`, `alerts.json`):
  nine rule-based agents — US MARKETS (S&P, Nasdaq, Dow, the 10-year, DXY, VIX overnight, with
  the Nifty's measured 120-session beta to the S&P's previous session and the implied open;
  printed every pass, quiet or not), EVENTS (≥8% day / ≥20% week on ≥₹25 cr), RATES (1Y swap
  ≥8bp on the week, bills ≥10bp on the day, the MPC inside seven days), RUPEE & RESERVES,
  FLOWS (FII ≥₹3,000 cr), REGIME & STATE (regime / dials / state / cap flips since the last
  pass; India VIX ≥15%), COMMODITIES, THE BOOKS (a held name within 1.5% of stop or target, due
  inside two sessions), THE WIRE (a topic taking a fifth of the tape). Severity alert / watch /
  info, dated, deduplicated over three days, a memo for the flips. WHAT IS HAPPENING on THE CALL
  and the DESK; THE ANALYSTS with the trail on AGENTS. New ALERT-severity items go to Telegram
  once each on every pass (`push_call.py --alerts`, `history/alerts_pushed.json`).
- **THE WIRE, BY TOPIC** (`window.NEWS_LIVE`, `js/wire.js`): every dated headline tagged with a
  topic (RBI & rates, inflation, growth & data, rupee, oil, flows, US & Fed, China, geopolitics,
  earnings) and its lean; grouped on NEWS with counts and leans, one line on THE CALL. THE BRIEF
  (computed) stays.
- **THE MAIL** (`send_mail.py`, post-close, once a day, `history/mail_<date>.done`): the line,
  the five with stop / target / conviction, tomorrow, next week's contenders, the dip flags, the
  three agents' books, what is happening, rates and macro, the record — HTML with a plain-text
  copy. Secrets MAIL_SMTP_HOST / MAIL_SMTP_PORT / MAIL_USER / MAIL_PASS / MAIL_TO / MAIL_FROM;
  without them it prints. Manual runs can tick "mail".
- **The MPC read off the release.** When the RBI feed carries a new Monetary Policy Statement
  the updater fetches it and parses the decision (CUT / HIKE / HOLD), the repo and the stance
  into MPC_LIVE — no hand note needed on 7 Oct.
- Stamps: page v138, updater BUILD v138, model tag v127. Contracts 48.
- **v138.1** · the analysts' new ALERT-severity items are mailed every pass (`send_mail.py --alerts`,
  once each via `history/alerts_mailed.json`); Telegram is optional throughout — without its two
  secrets every push step prints and exits.

## v139 (30 Sep 2026) — search first, the verdict in bold, the chart with the model's layers

- **THE VERDICT.** Type any company, sector or theme (the box leads F&O ONLY and STOCKS; the
  🔎 floater opens it on every tab, `/` focuses it) and one card answers, verdict first, in bold:
  **BUY / SHORT / WAIT / AVOID / NO TRADE** (with · TACTICAL or · PRICE ONLY when that is what it
  is), the price, the stop and the 2R target, the size cap and the dials multiplier, the horizon,
  the conviction with the chain count — then the reasons as chips, whether a book holds it, and
  **what changes it**. The rule is the desk's: a full F&O setup is BUY or SHORT; theme-without-name
  is WAIT; against-the-theme is TACTICAL; no prior is PRICE ONLY and needs the screen at 70 / 30;
  a cash name follows the board and the screen; a repricing in the tape is NO TRADE; the gate
  turns longs into WAIT; dip risk ≥ 60% turns a BUY into WAIT (45–60%: take half).
- **THE PERFORMANCE TABLE** — 1D · 1W · 1M · 3M · 6M · 1Y, the same against the Nifty and against
  the name's sector (the median of its screened members), the 52-week range and where it sits,
  the worst drawdown of the year, 30-day realised vol. A sector or theme answers with the board's
  verdict (BUY THE SECTOR / UNDERWEIGHT / WAIT …), the 20/60-session relative return, the regime
  study's t, and every member by turnover with its own verdict.
- **THE CHART WITH THE MODEL'S LAYERS** (`js/mchart.js`, the page's own SVG engine): a price series
  plus toggleable layers — the means the screen uses, ▲▼ where a model or a book entered and ●
  where a call closed (which model), the open stop and target lines, the dip levels (fades
  above / run over below), × the ≥8% days, the 52-week band, the Nifty on the same scale. Any
  series with any layer list: `mchart({pairs, layers, extra, hlines, marks})` — the flexible way
  to differentiate every chart on the page.
- **RUPEE GOLD, THREE WAYS** (COMMODITIES): COMEX parity, the GOLDBEES-implied price and the IBJA
  fix where it was read, on one chart — the wedge visible instead of asserted.
- BSE-only names answer with the exchange close and the day; a chart for them needs a live door.
- Stamps: page v139, updater BUILD v139, model tag v127.
