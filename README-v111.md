# MacroIntel v111 — layout fix, model selection, long horizons, the positioning note

Supersedes v110 (contains it: CPI 4.45 graft, deposits 12.7, IBJA current +
ibja.co door). Upload all four files, run the workflow once.

## New / fixed

1. **Movers panel overlap (your screenshot).** Rows are hard grid cells now
   (symbols ellipsize, nothing bleeds into the next column), the four
   boards wrap 2x2 on narrow screens, big turnovers print "₹2.1k cr", and
   verdict chips get their own right-aligned column.

2. **🎯 POSITIONING note — the answer to "will it tell Gautam".** A new
   panel at the top of the macro tab composes the whole read into one desk
   note, every line naming its live source block: EQUITY (macro quadrant x
   market lens -> what to do), RATES/DURATION (curve regime + playbook),
   GOLD and SILVER (model stance, stop, target, sizing rule, edge status),
   VALUATION (ERP vs the daily 10Y), RISK DIALS (VIX, LAF, PCR, basis).
   It sits above the existing "0 · POSITIONING — the book" table, which is
   unchanged. Metals lines refresh every ML pass (11:15/15:15/18:00 IST) —
   the same math as the morning gold/silver note, now permanent.

3. **The ranker picks its best model per horizon** (GBR / HistGB / RF /
   Ridge on the same purged walk-forward; winner named in the footnote).
   Skill bar carries a measured selection tax: 2.0 -> 2.4 (nine null
   panels all read "none"; planted momentum still caught at 10d and 90d).

4. **Planner honest at any horizon** (up to 500 sessions): past 30
   sessions the stop scales 2.5σ·√(H/30), capped 45% — a daily-sized stop
   held for a year would be stopped by noise with near-certainty. Odds,
   targets and 1%-risk sizing use the scaled numbers.

## Tests
14 suites green, calibration re-run (null 9/9 none), node --check clean,
headless renders: grid layout, footnote model names, positioning note AND
the original book table both rendering in their own containers.
