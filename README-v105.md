# v105 — the trade planner: entry, stop, target, odds

**Supersedes every earlier zip. Three code files to the repo root, workflow
untouched, Run workflow. Header v105 confirms.**

## The answer to "does the model show targets and stop losses?"

It did not. Now it does — and no new server-side ML was needed, deliberately:
a per-name return distribution you can verify beats a neural net you cannot,
and the state-conditioning already comes from the HMM the site runs daily.

**The TRADE PLANNER box (shares tab, above the Industry Read), built for the
10-day-to-2-week positional horizon:**

- Type any share (or hit "Scan for asymmetric setups") and it returns the
  whole position: ENTRY (last close), STOP at 2.5 daily sigma (where the
  position is statistically wrong, not a round number), TARGET as a multiple
  of the stop — 1.5R when the HMM says CHOPPY (chop pays mean-reversion,
  punishes runners), 2.5R in trending states — over your chosen horizon.
- Monte-Carlo odds (4,000 paths from the share's own last year of returns,
  drift shrunk 70% toward zero): P(target first), P(stop first), P(neither)
  with its average P&L at horizon. First-passage, not end-point — the order
  in which barriers get hit is the whole game at 12 sessions.
- EXPECTANCY per ₹100 risked — the asymmetry test in one number — and the
  share count that keeps risk at 1% of capital.
- The SCAN runs the same maths across the daily-history names and ranks by
  expectancy: the asymmetric-bets list, state-aware. Verification run:
  58 names scanned, Federal Bank on top — agreeing with the long-term model
  independently, which is exactly the kind of agreement worth acting on.
- The maths was validated against an independent 200k-path reference
  implementation (three parameter sets, all within tolerance).

Honesty on the tin: close-based (gaps and slippage not modelled), drift
shrunk, probabilities are frequencies under the fitted distribution. A
planner, not advice.

## On the priorities

- 10d-2wk positional trading: the planner IS that workflow — plan, size,
  know the odds, know where you are wrong before entering. Swing trading is
  the same box with the horizon input changed.
- Asymmetric bets: the scan ranks by probability-weighted payoff per rupee
  risked. Asymmetry that survives the Monte Carlo, not lottery tickets.
- Cash flow management: the allocator's safe/liquid bucket plus the fund
  route (liquid fund NAV) already cover the parking leg; sized risk (1%
  rule) in the planner is the cash-preservation discipline.
- Yield curve regimes: already on the site — the Yield-Curve Regime Panel
  (macro tab, external-accounts pack), the computed curve-shape implications,
  and the OIS tab's legend and MPC-dated curve.

## Verified

    node --check 0 failures · MC engine matches the numpy reference on all
    three test cases · headless: RELIANCE plan renders (entry 1,335 / stop
    1,292 / target 1,399 / P(t) 21% / P(s) 38% / +3 per ₹100), scan returns
    ranked setups over 58 names · zero page errors · all suites green
