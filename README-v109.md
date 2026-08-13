# MacroIntel v109 — movers for the full market, a metals model, live-er news

Supersedes v108 (contains everything in it: the yield-curve fixes, the
gzip transport repair, the Hindi-wire hop that catches July CPI 4.45%, the
RBI-home daily 10-year, the WSS banking tables). Upload all four files to
the repo root, then Actions -> Run workflow.

## New in v109

1. **Movers & momentum, full market.** A new pipeline door reads NSE's
   full-market equity bhavcopy (every listed EQ name — ~2,000, not our
   58-name universe) for the session and for five trading sessions back:
   intraday and intraweek boards (top/worst 8 each) above a labelled ₹5cr
   turnover floor, plus a search map (₹0.5cr floor) behind a search bar —
   type any NSE symbol for its day move, week move, turnover and a
   BUY-style verdict (RIDE / HOLD-TRAIL / WATCH / AVOID / NEUTRAL). The
   verdict is a momentum screen crossed with the macro quadrant and the
   price-side market regime — labelled a filter, not a forecast. Moves like
   Ellenbarrie's +14% day now surface automatically.

2. **SKILL: NONE is gone.** The forecasts box is now the movers panel; the
   ranker's honesty moved to one muted footnote (it publishes picks only
   when walk-forward IC clears t >= 2.0). Same discipline, no banner.

3. **A metals model (gold + silver).** ml_models.py now scores both off
   documented drivers — 20d/60d trend, the dollar (inverse), US yields
   (inverse, nominal proxy), the gold/silver ratio z-score for silver, and
   a vol-blowoff check — and holds itself to the same honesty bar as the
   equity ranker: a walk-forward 10-day sign test with hit-rate and t-stat.
   Below t>=2 the page says "edge unproven — a regime read with risk math,
   not alpha". Each metal gets stance, drivers, 2.5-sigma stop, R-multiple
   target. Runs on ML passes (11:15 / 15:15 / 18:00 IST).

4. **Commodities tab: charts + a detailed metals report.** Rolling-session
   SVG charts (Gold, Silver, Brent, WTI, Copper, USDINR) off the page's
   spark history (Silver newly seeded — it grows to 20 sessions pass by
   pass and says how many it has). Below them, the ₹ price chain computed
   live (spot -> parity -> IBJA fix -> wedge -> GST) and the model cards.

5. **Regime strip: the market lens.** The price-side regime the Shares tab
   computes (EXPANSION / OVERHEAT / DRAWDOWN / REPAIR off trend x stress)
   now appears inside the macro regime box as a cross-check row — macro
   quadrant and market state, read together.

6. **News tab refreshed.** A dated editorial block (13 Aug) on July CPI
   4.45%, the credit-deposit wedge (17.7 vs 12.7), the daily 10Y, metals at
   records; the stale "Next RBI MPC: Aug 4-6" line now points at the
   Sep 29 - Oct 1 meeting. Charts around it remain live-computed.

## What you should see change after upload + one workflow run
- Yield-curve tab fills (India curve guaranteed; US via FRED or treasury.gov)
- CPI tile: 4.38 -> 4.45 (Jul), food 5.52; regime inputs go live again
- 10-year tile: ~6.78% daily off the RBI home page; ERP recomputes against it
- Credit / deposits / M3 tiles fill: 17.7 / 12.7 / 12.5
- Gold box: fresh IBJA fix replaces the 07-Aug seed (gzip fix)
- Movers boards + search go live; commodities charts start extending
- After the next ML pass (11:15/15:15/18:00): metals cards fill

## Tests
15 suites green (through t109_movers), dead-network mock run (31/31
contracts intact; movers/curves carry honestly), node --check clean,
headless render of movers, charts, metals report, regime lens, editorial.
