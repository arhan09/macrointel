# MacroIntel v148.1 — the pipeline that runs late rather than never · the bell · the calls of the day · why it moved · the Street · the full history

A drop-in over whatever is on the repo (v141 → v148 in one upload works; the files keep their names). This file replaces every older `README-v1xx.md`.

## 0 · Host it

**Why the page has been stale since Oct 16 (and what changed).** GitHub delivers this repo's scheduled runs hours late — the five-minute quotes cron for 10:55 UTC ran at 14:00 UTC on Oct 21, the Monday 01:30 UTC weekly-ML cron ran at 06:33. The v145.1 gate threw a late daily run away when it landed outside 07:45–21:30 IST, and the watchdog stood aside whenever GitHub showed a run as "queued" (its backlog keeps them queued for hours). Late became never: no pass at all on Oct 17, 20 or 21. **v148.1** fixes that in the three workflow files: the gate keeps only the 40-minute duplicate check (a pass at 03:00 is a stale page refreshed), the watchdog runs round the clock and only a run actually *in progress* holds it back, and the quotes workflow nudges a late daily pass too. Passes will come — late, when GitHub gets round to the crons. The Cloudflare worker's cron (C below) is what makes them come on time.

**Two ways to get this onto the repo:**
- **Connect GitHub to Claude** (claude.ai → Settings → Connectors → GitHub, authorise `arhan09/macrointel`). Then say "go" and the upload, the workflow run and the first checks are done for you — nothing to click on GitHub.
- **Or upload yourself:** everything in this zip at the repo root, keeping the folders: `v144/` (17 files — for the record; the page is already built), `worker/mi-proxy.js`, `.github/workflows/` (3 files). Delete the old `README-v1xx.md` files. Then Actions → Daily Terminal Update → Run workflow (the first pass is ~40 min: ten years of weekly prices for every NSE name).

**B. The live door is now ON by default.** The page ships with the worker's URL baked in (`const MI_PROXY = "https://mi-proxy.data-campusbinge.workers.dev/?u="`), so every browser streams quotes and draws full charts without pasting anything. The repository variable `MI_PROXY` is no longer needed; if it is ever set, it still wins.

**C. The scheduler — the one thing that makes the passes land on the hour (ten minutes, once, in your Cloudflare dashboard):**
1. GitHub → avatar → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate: name `macrointel-cron`, expiry 1 year, Repository access *Only select repositories* → `macrointel`, Repository permissions → **Actions: Read and write** → copy the `github_pat_…`.
2. Cloudflare → Workers & Pages → `mi-proxy` → Settings → **Variables and Secrets** → Add → type **Secret**, name `GH_TOKEN`, value = the token → Deploy.
3. Settings → **Triggers → Cron Triggers** → add three (UTC): `37 2-14 * * 1-5` · `7 10 * * 1-5` · `0,10,20,30,40,50 3-10 * * 1-5`.
4. Edit code → replace all with `worker/mi-proxy.js` from this zip → Deploy. Test: `https://mi-proxy.data-campusbinge.workers.dev/cron` answers `"would":"dispatch daily-update.yml"`; `?go=1` fires one now.

---

## 1 · The bell — today's major updates (every tab, top right)

A 🔔 with a count. Behind it, the day's updates as the engine saw them at the last pass, the calls first: the market and the session's call, the regime and the nowcast (and whether it shifted since the last pass), FII/DII flows, every verdict that flipped, tomorrow's likely movers, results today and tomorrow, the stock-specific moves, what was scored, the Street, where to be, the pairs, the market's headlines, the pass itself. Each item deep-links (a share, a tab). What you have read stays read in that browser. **Desktop notifications**: a toggle in the drawer; while the page is open in a tab, each new pass raises a notification with the calls and the top three updates (the page checks every ten minutes and refreshes its numbers by itself).

## 2 · The calls of the day (Home, under the hero · the bell · Ask "the calls of the day")

**One long call — "Buy X, target ₹T in 12 months" — and one short call — "Buy Y, target ₹T in 1 month."** Not the top of a list: a call is made only when independent supports stack and nothing objects. The supports, each written out on the card:

- the trend (six months and the 200-day for the long; twenty sessions, the 50-day and not extended for the short)
- **the company's numbers** — the quality score and what drives it (ROE, margins, growth, leverage, P/E against the sector, promoter holding)
- **the regime fit** — the name's own record in the current regime over ten years of weekly history (or the sector's edge where the name is young)
- **the Street** — the analysts' mean target above the price (five or more analysts)
- **the news** — the week's headlines supportive and none against (Google News, scored by a finance lexicon; the headlines ride on the card with their links)
- **the delivery read** — accumulation: delivery well above the name's own average on an up day
- **the engine's own record on the name** — its past calls on this name in the money
- the horizon cone's odds of being higher at the horizon
- for the short call also: the contenders model, a futures long build-up, the twelve-month side agreeing

Conviction = the number of distinct supports: **HIGH 5 · GOOD 4 · FAIR 3**. Nothing is called below three, against the week's news, or into results within three sessions; the objections that remain are printed in orange. The short call's target is the verdict's, scaled to twenty sessions; the long call's is the twelve-month target with the 200-day as the exit. Both are **frozen with the day and scored**: the short call at twenty sessions (did it reach the target before the stop?), the long call at sixty sessions and at 250 when the year is up. Markets → The Street carries the calls' record; the bell's drawer and Ask ("what should I buy", "the calls of the day") carry the calls.

## 3 · Why it moved (Home · Markets → Intraday · every research page · Ask "why did X move?")

Every move of at least 1.5σ on a liquid name is split three ways: **the market's part** (the name's three-year Nifty β × the market's day), **the sector's part** (the sector's median move relative to the market), and **the stock's own**. STOCK-SPECIFIC when the own part is 60% or more — and then the fresh headline sits next to it, or the honest line "no headline found; a results date, a block deal or a broker note usually sits behind a move like this". A print of ±35% or more is flagged ADJUSTMENT? (a split, a demerger, a bonus). Beside it, **the delivery read**: NSE's own figure for how much of the day's volume was taken home (`sec_bhavdata_full`, the last sixty sessions cached), against the name's twenty-session average — ACCUMULATION, DISTRIBUTION or SPECULATIVE (a big move nobody kept). Every research page shows the day's delivery; the movers' cards and the calls use it.

## 4 · The Street against the engine (Markets → The Street · Home · every research page · Ask "what do analysts say about X?")

Yahoo's mean analyst target for every name with five or more analysts, as an upside from today's price, against the engine's twelve-month expectation. Two boards: where the engine is more bullish than the Street, where it is more bearish. The two disagree by construction more often than not (a consensus target lags the price, so the Street's biggest upsides sit on names that have fallen; the engine's lean on momentum, the regime and the company's numbers) — and the page says so, with the rank correlation. **The record**: the twenty widest gaps are frozen each day; sixty sessions on, whose implied path did the price come closer to? A broker never grades his target. This board grades both.

## 5 · The full history (the thing Gautam noticed)

- **Every NSE name** now gets a weekly tape — ten years, not three, and not only the names above ₹0.5 cr a day. More names scored; the regime record on every share spans two cycles instead of one; the research page's chart falls back to five years of weekly history without a door.
- **BSE-only names get a weekly tape too** (`<code>.BO`, ten years), 240 a pass on a rotation, cached between passes — about 2,000 names over the first day. A BSE-only share with a tape is scored like any other (its liquidity floor still keeps it out of the trade lists).
- The daily panel runs two years (the movers model learns on twice the sessions).
- The chart has a new range, **Since listing**, through the door (which is now on by default): the whole history Yahoo has, weekly. The chart's subtitle says since when the engine's tape runs; a listing younger than eighteen months is flagged — "a young listing: the twelve-month side has no full year to lean on".
- The DNA's betas stay measured on the last three years (the regime record uses everything).

## 6 · Ask, new

"the calls of the day" · "what should I buy" · "why did Reliance move?" · "what happened to X today" · "news on X" · "what do analysts say about X?" · "delivery X".

## 7 · Does the model look at the micro of a company?

Yes — it always did, and the calls make it visible. The twelve-month score is 0.27 quality (ROE, net margin, revenue and EPS growth, debt/equity, P/E against the sector median, P/B, promoter holding) on top of 0.33 trend and 0.22 macro; the short-term score carries 0.10 quality; the twelve-month target itself has a quality tilt. The research page shows the leg ("The score, in parts") and the profile. What the models do **not** read is the news — headlines are evidence behind a call and context on a move, never a feature, so a wire's mood cannot move a verdict.

## 8 · Files that changed

`engine.py` (v148: the panels, `bse_rotation`, `fetch_delivery`/`delivery_read`, `fetch_news`/`parse_rss`, `attribution_block`, `street_block`, `conviction_calls`, `brief_block`, `movers_enrich`, the calls and the Street in the record, `freeze_day`) · `v144/e-brief.js` *(new)* · `e-share.js`, `e-markets.js`, `e-ask.js`, `e-core.js`, `e-boot.js`, `theme.css` · `build_v144.py` (the bell, the script, the default door, the stamp) · `.github/workflows/daily-update.yml` (v148.1: the gate without a clock window; the caches, the wider budget, `MI_PASS_KIND`, `news.json`) · `watchdog.yml` (round the clock, queued runs ignored) · `quotes.yml` (nudges a late pass) · `t144_engine.py` (42 more checks) · `update_terminal.py` (`BUILD = "v148"`) · the five older suites (stamp). The arena's rules are unchanged (`AGENTS_VERSION` stays `v144.0`). New files the pass writes: `news.json` (served), `delivery.json`, `news_cache.json`, `engine_prices_bse.json` (caches, kept by Actions between passes).
