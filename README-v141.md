# MacroIntel v141 — MACROINTEL 3: the product, the rational agents, real time, the research front, the rupee, the macro note

**Upload** at the repo root (replace same names; delete `README-v139.md`), then Actions → *daily-update* → **Run workflow**:
`macro_intelligence_terminal.html` · `update_terminal.py` · `ml_models.py` · `fno_setups.py` · `push_call.py` · `send_mail.py` · `tearsheet.py` · **`quotes.py`** · `.github/workflows/daily-update.yml` · **`.github/workflows/quotes.yml`** · **`worker/mi-proxy.js`** · `t121_safety.py` · `t122_validation.py` · `t125_desk.py` · `t126_desk.py` · `t127_env.py` · `README-v141.md`

**Built on the deployed v139** (cloned from the repo on 9 Oct; the v140 zip never reached you, so everything v140 carried is in here). Five suites green: `t121` · `t122` · `t125` · `t126` · `t127` (+43 v141 checks). 48 data contracts, unchanged. Page stamps **v141**; `update_terminal.BUILD` → v141; the agents' engine moves to **v141.1** (the six books restart on the first post-close pass, dated and explained on the tab; the three old books stay in `history/`). No secret in the source; mail needs the `MAIL_*` repo secrets as before; Telegram stays optional.

---

## The page, tab by tab

**🏠 HOME** — the front door. An animated welcome (what MacroIntel is: *most apps show prices; this shows what paces them*), then TODAY (the line, conviction today, tomorrow's call, the Nifty with the option market's range), **WHAT PACES THE MARKET** — the chain data → regime → dials → sectors → names → size → the books, each step with today's value, each a click — **THE MARKET'S PULSE** (India VIX and its percentile, advance/decline on real turnover, % above the 50/200-day, names at 52-week highs/lows, fresh breakouts), what is happening (the analysts' alerts), the wire by topic, **THE TOP SHARES** in three columns (short term: the five with BUY/SHORT in a word; long term: investment ideas; early & the dip), the heatmap of the 60 most traded (1D/1W), the investment ideas in full, and WHY TRUST IT in tiles. Every number is the page's own.

**🏦 MACRO** — opens on **THE REPO WENT UP · 5.25 → 5.50 (+25bp, 7 Oct, neutral)**: the real rate now vs before, what the swap curve prices after the move, the regime, what it means for the book, and a table of who wins and who loses (banks, NBFCs, realty, autos, IT, FMCG — the board's read and 20-session relative performance beside the reason). Then **THE FLOW** — every indicator and where it goes (a flowchart with live values: CPI/WPI/GDP/IIP/GST → regime → repo, the 1Y swap, the rupee, VIX/breadth → dials → sectors → names → size), **THE PACE** — a 0–100 scorecard of growth, inflation, liquidity, external and market legs with its read (not a forecast), and **THE CHARTS** drawn by the page with its own markers (CPI against the 2–6% band, the 1Y swap/91-day bill/10Y gilt/repo with the MPC marked, reserves against the record, the rupee with its means). The full macro tab, the dials and the chart pack fold behind ▸ lines below. Q&A is the last tab, as asked.

**📉 RATES · 💱 RUPEE · 🥇 GOLD & OIL · 🌐 GLOBAL** — each opens with **WHAT THIS TAB TELLS YOU** in three or four plain sentences computed from the blocks (rates: what the RBI did, what the swap market prices, hikes or cuts in, what it means for you, what would change it; the rupee: level, reserves, flows, oil in rupees, the page's view; gold: dollar price, the rupee read and its source, the metals model's stance; global: the US agent's read, the US curve, why it matters here). The detail stays underneath, unchanged.

**📈 MARKETS** — one search first (every one of the 2,538 NSE names and the 2,068 BSE-only names, every sector, every theme), then five sub-tabs, each defined on its own line so nothing overlaps:
- **INTRADAY · today** — the index tiles, **WHY IT MOVED** (today's biggest moves on real turnover, explained by rules: the day against the sector, the futures book, a breakout, a repricing, the dip odds, the wire), the next session's call with the second opinion and the expected range, the movers and the sectors; the momentum screen folds.
- **SHORT TERM · 5–20 sessions** — the five (15 sessions), the early movers (20), the dip (10), the short-horizon model desk; the screen, the industry read and the chart lookup fold.
- **LONG TERM · months** — **INVESTMENT IDEAS** (at most two a theme: the theme's macro case, the regime study, the name's screen and its year against the Nifty, the long-term model's pick, with the NSE quote, the financials and the wire linked), the regime → sector read, the long-term list; the sectors and the long screen fold.
- **F&O** — as v139: one search, one ticket, the lists fold.
- **BUILD & SIZE** — WHY TRUST IT (the full table), **THE RECORDS — the models' own validation, regardless of the agents**, the model desk, the paper book, the post-mortem, what changed, the live book, then the allocator, the planner and the liquid desk.

**🤖 AGENTS** — see below. **📰 NEWS** — the analysts first (what is happening, nine rule-based readers), then the desk. **❓ Q&A** — the ask bar and the questions, last.

**The search card** (from any tab, 🔎 or `/`): the verdict in a word, then **IN PLAIN WORDS** — the short-term and long-term read as a message you could forward (price and the week/month against the Nifty, the 50/200-day with the levels, the futures book, what options expect, the sector view, dip risk, what the models say; the expectation with the target, the stop and the size; the long-term word with its reasons and the flip; a short version) with a **copy for WhatsApp** button — then **WHY IT MOVED** when the name moved ≥3% on the day or ≥6% on the week, the performance table, the chart with the model's layers, the wire, the full chain folded.

**The shell** — an app bar with the stamp, the next pass and the live badge, an index strip with sparklines (Nifty, Sensex, Bank Nifty, VIX, ₹/USD, Brent, gold, DXY, S&P, Nasdaq — click any for its card), pill tabs, a bottom nav on phones, the lens moved into the bar so the search floater owns the corner.

---

## The research front, the rupee, the macro note (v142)

**HOME now opens like the broker apps you showed — and goes further.** A breadth bar (up % / down %, live from the quotes when a door is open, the bhavcopy's full market otherwise), then **Research Recommendations** in five rows: *Investment Ideas* (months: the objective is the 52-week high, the stop is the 200-day — both objective levels, no invented targets), *Trading Ideas* (the five and the F&O setups with the desk's stop and a 2R target, 15 sessions, conviction), *Stock Baskets* (the board's LONG and UNDERWEIGHT themes as equal-weight baskets — four names by turnover, the basket's day, 20/60 sessions against the Nifty, the regime edge), *Early & the Dip*, and **My List** (☆ on any card keeps it in this browser). Every card: name, live price and the day, profit potential, target, stop, horizon, a word (BUY / SHORT / ACCUMULATE / DIP), and a tap opens the full verdict card. "View all" goes to the right sub-tab. **Market News** carries three chips: *Trending* (the biggest clusters on the wire), *One-minute read* (the macro note's line and five bullets), *On my stocks* (headlines naming your list, the five and the books' holdings).

**RUPEE is an analysis now.** Under the three-line summary: tiles (USD/INR with its 52-week percentile, **the RBI's hand** read off the reserves against the rupee over the same week — DEFENDING / ACCUMULATING / LETTING IT GO / HANDS OFF, with the valuation caveat — the carry against the US 2-year with the forward premium and the hedge share, oil in rupees with months of import cover), **the betas** — an OLS of the rupee on the dollar index, Brent and the Nifty measured by the day and by the week (the RBI smooths the day; the week shows the drivers), with t-stats and R², **the month decomposed** into those drivers and the residual that is India itself, **the scenarios** (DXY ±2%, Brent ±10%, Nifty ±5% — the average co-move, labelled as not a forecast), the chart (a year, 20/50/200-day means, the 52-week band, the MPC and the reserves record marked), and **the rupee note**: five paragraphs written by rules every pass — where it is and what moved it, the dollar, oil and the deficit, flows and the carry, the view with the levels, the asymmetry, the book's expression and what would change it.

**THE MACRO NOTE** sits on MACRO under the repo card: a strategist's note written by rules from the blocks at every pass — the line, a seven-leg scorecard (growth, inflation, liquidity, rates, external, market, global — reading, momentum, against its own history, signal), then Growth, Inflation, Liquidity & Rates, The External Account, The Market, each ending in *Our read*; **what the market prices against what the data says and the gap** (rates, growth, the rupee, equity); positioning; **what would change our mind** with the numbers; the calendar ahead (the page's dates plus the usual monthly releases, marked ≈); the record. Every sentence has a number behind it; the words change only when the numbers do. This is the differentiation you asked for: analysis, not a tip sheet.

---

## Real time (v141.2) — not every hour

A GitHub Pages site cannot push a price; the page pulls. Three layers, each labelled on the badge, the strip, the home tile and the agents' tape:

1. **The browser's own door — every minute in the session, every five off it, and the moment you return to the tab.** One batch call (Yahoo's spark endpoint) carries every name on the page — the strip, the fifty, the names the books hold — through the first door that answers: Yahoo directly (works in some browsers), **your Cloudflare worker** (`MI_PROXY`, the robust door — `worker/mi-proxy.js`, three steps in the file, free, no key; the URL goes into a repository *variable*, never a secret), or a **public CORS gateway** (allorigins → corsproxy → codetabs: free, no key, nobody's promise — they come and go, so the page sweeps them in order, remembers the one that works and re-probes when it dies). The old proxy path had a bug that dropped it after the first quote; fixed. The badge reads *⚡ live 13:22:53 IST · your worker · 66 quotes*.
2. **The five-minute file — the floor.** A second, tiny workflow (`quotes.yml`, `quotes.py`) runs every five minutes of the session and force-pushes `quotes.json` (every name above, batched) to an orphan `live` branch — one commit, no history, no Pages build, free on a public repo. The page reads it over CORS from `raw.githubusercontent.com` whenever no door opens, and accepts it only while it is under twenty minutes old. GitHub queues five-minute crons under load, so call it five to fifteen minutes; the badge says *● 5-minute file 14:35 IST*.
3. **The hourly pass** — the models, the books, the blocks, as before. When neither of the above answers the badge says *· pipeline (no live door from this browser)*.

**Do this once for the robust door:** open `worker/mi-proxy.js`, follow its three steps (paste into a free Cloudflare worker, copy its URL, add the repository variable `MI_PROXY = https://<name>.<you>.workers.dev/?u=`), and the next pass turns it on. Nothing else to deploy. The `Live quotes` workflow needs nothing — it runs on upload.

---

## The agents, made rational (v141.1)

Six books of ₹1 crore. Three temperaments share one candidate pool (the F&O setups, the five, the ledger's open calls, the early movers, the ranker's laggards) and differ in nerve; three rule-bound books trade one source each. Nobody deploys the crore at once: each has a deployment cap, a position size, a daily ramp, a stop width and a conviction bar.

| book | base mood | a position | deploys at most | new a day | takes | conviction bar | stop | the gate |
|---|---|---|---|---|---|---|---|---|
| CAUTIOUS | fear 70 · greed 30 | 3% | 30% | 2 | setups, the five | ≥ 70 | 0.7 × desk | respects it |
| BALANCED | fear 50 · greed 50 | 5% | 60% | 3 | + the ledger's calls | ≥ 55 | desk's | respects it |
| AGGRESSIVE | fear 25 · greed 75 | 8% | 90% | 5 | + early movers, laggards | ≥ 40 | 1.4 × desk | takes longs through it, and says so |
| F&O ONLY · MODEL CALLS · THE TAPE | none (rule-bound) | 5% | 70% | 4 | one source each | — | desk's | by the source |

**The mood.** Each pass the page's own tape — the six tape checks, stress, VIX and its percentile, breadth on real turnover, the Nifty's day, the dials' clash — becomes one score (−1…+1, benign/mixed/hostile), printed with every part. Each temperament turns it into fear and greed for the day: CAUTIOUS is scared by a hostile tape (up to +25 fear) and barely tempted by a benign one, AGGRESSIVE the reverse, BALANCED both ways. **The mood changes only five things, and each change is printed:** the conviction bar, the deployment cap, the size of a position, the number of new names a day, the stop width. The rule-bound books have no mood.

**Every action carries its reason**, built from the rule that fired: *BOUGHT A Co, 3.2% of the book at ₹110.11 — on the five to watch: 7 of 9 links of the chain agree; conviction 78 against my bar of 68 today; stop ₹106.20 (3.5% — the desk's 5.0% × 0.71, my rule), target ₹117.93 (2R), out by 2026-11-02; mood: conviction bar 70 → 68, deploy cap 30% → 32%, a position 3.0% → 3.2%.* Exits say which rule closed them (the stop and why it was that wide, the target, time, the ledger). What a book passed on is listed with why (under the bar, the gate, the ramp, the cap, no close).

**Every book answers for itself, first person, from its numbers** (WHY I ACTED): the tape it read, its mood and what changed, the gate, the pool and how many cleared its bar, what it took, what it passed on, what it closed, where it stands, and what would make it act more. **The line** draws each book's equity in ₹ lakh with ▲ ▼ ✕ where the money went in and out, the Nifty dashed beside it; the reason for each mark is in the log above it. The leaderboard and the balances carry the mood. `page_state` now carries the tape the agents read (`vix`, `vix_pct`, `nifty_d1`, `ad`), evaluated headless by `fno_setups.py` every pass; the mail prints each book's mood and its first action's reason.

**Not the models.** The models' lists are frozen and scored on Build & size whatever the agents do; the agents are the validation of the *acting*, the records are the validation of the *calling*. The tab says so in its first line.

---

## Also in this build

- **Trade print** hand-updated to August 2026 (exports $43.81bn +26.1%, imports $70.67bn +14.1%, goods deficit $26.86bn from $31.98bn in July; services $38.87/21.42bn; overall deficit $9.41bn, −19% y/y; Commerce Ministry release of 15 Sep) — replaced automatically when the wire reads the September release. A shrinking deficit now prints with its sign.
- **Workflow**: 14 crons (every hour 08:07 → 20:07 IST plus the 15:37 close pass), the push and the mail on the six post-close passes (once a day), the tear sheet on 17:07/18:07, **t122 joins CI**.
- **Search**: the datalist carries the BSE-only names; the resolver already did. `mchart` draws without layer chips where there are no layers. Legacy tab names (`call`, `desk`, `pack`) land on their new pages, so every old link still works.
- **Validation** and the **tear sheets** stay behind the record (unchanged); the chart pack lives under MACRO with the tear sheets as its appendix.

## What to look at first

Open the site: the welcome, then MACRO for the repo move and the flow, then MARKETS → INTRADAY for why things moved, then AGENTS after the first 15:37 pass for the six books' first answers. Search any name — the plain-words card is what you forward.
