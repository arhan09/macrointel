# v107 — the India yield curve, its regime, and a daily pulse

**Supersedes every earlier zip. Three code files to the repo root, workflow
untouched, Run workflow. Header v107 confirms.**

## The India curve, and the honest problem behind it

You asked for yield curves for India that update every day. Here is what I
found and what I did about it.

India has no free, machine-readable, daily par yield curve. FBIL and CCIL
both publish exactly the thing — and both refuse automated access (FBIL by
robots policy, CCIL with a 403). So the curve on the new panel is
**assembled**, and every single point carries its own source and its own
update cadence on the chart itself, because a curve built from four
different frequencies and presented as one live object would be the most
elegant lie on this site:

    ON     RBI Money Market Operations release        DAILY  (green dot)
    3M     term MIBOR carried on the page             build-dated
    1Y/2Y/5Y   the MIBOR-OIS curve                    build-dated
    10Y    FRED benchmark print, walked forward each
           day by the long-gilt ETF                   level monthly,
                                                      direction DAILY

The dots are colour-coded: green means that point genuinely refreshed today,
blue means it is build-dated. The 10-year's construction is spelled out on
the tile, including the one assumption it rests on (7.5-year modified
duration for the gilt ETF, used only to convert its price move into a yield
move — a labelled constant, in the same class as the corridor width).

## What updates every day for India macro — the new daily door

**RBI's Money Market Operations press release**, read off the same press
index the reserves fetcher already walks. Published every session, and it
gives the three things that actually move day to day:

- **Call rate (WACR)** — where overnight money genuinely traded
- **Triparty repo** — where most overnight cash actually clears
- **System liquidity** — net absorbed or injected under the LAF, in lakh
  crore, with the direction spelled out: a surplus pins money to the floor,
  a deficit pushes it to the ceiling. This is the number that explains the
  call-rate-versus-repo spread the OIS tab has been displaying without
  being able to explain.

## The curve regime — four states, each with its own playbook

The curve is not a chart, it is a classifier. BULL means yields falling,
BEAR means rising; STEEPENER means the long-minus-short spread widening,
FLATTENER narrowing:

- **BULL STEEPENER** — easing priced into a recovering economy. The
  friendliest state there is: duration works AND cyclicals work, and banks
  get a widening lend-long borrow-short spread.
- **BEAR STEEPENER** — growth and inflation expectations building at the long
  end, or a term-premium and fiscal worry. Cyclicals and commodities; long
  duration is what hurts.
- **BULL FLATTENER** — a growth scare and a flight to quality. Long duration
  and defensives; cyclicals bleed even while yields fall, which is what
  catches people out.
- **BEAR FLATTENER** — a central bank tightening into the cycle. Cash and
  defensives; the state that precedes most inversions.

Computed for India and for the US, and when the two are in DIFFERENT regimes
the panel says so, because that is the interesting case — the carry and the
rupee do the reconciling.

## The rest of the macro completion

- **India minus US 10-year carry** — what a dollar earns for coming here; the
  driver behind both the rupee and foreign flows
- **US curve, complete and daily** from FRED: 3M, 2Y, 5Y, 10Y, 30Y, 2s10s,
  3m10y, with an inversion flag
- **The 10-year breakeven and the TIPS real yield** — what inflation is
  priced INSIDE the nominal yield, and the global cost of capital in real
  terms
- **Credit spreads** (US high-yield and investment-grade OAS) as the
  cross-check: credit either confirms the curve's story or denies it
- **Real 10-year for India** — the new 10-year minus live CPI
- **THE EQUITY RISK PREMIUM** — the gap I flagged as the most important one
  left. NSE publishes a daily indices close file carrying P/E for every
  index (static CSV, same archive host as the bhavcopy that works). Nifty
  earnings yield minus the 10-year is the single best answer to "is this
  market cheap", and the terminal could never compute it because it had
  neither number. Now it has both, daily, with a 60-point trail.
- **System liquidity** also parsed out of the Weekly Statistical Supplement
  as a second door
- The long-gilt ETF joined the price universe, so the long end has a daily
  read at all

Contract audit is now **30/30**.

## Verified

    twelve suites (new t107: all four regime states by definition, the
    sign-sanity check, FRED single and multi-series parsers, the daily
    money-market parser incl. injected-vs-absorbed sign and rate bands,
    the assembled curve with per-point frequency tags, the gilt-ETF
    duration conversion in BOTH directions, the no-anchor case, NSE index
    P/E with an absurd-P/E rejection, the ERP arithmetic, and
    carry-forward on every new block)          all FAILURES: none
    node --check                               0 failures
    contract audit                             30/30
    dry run                                    every new fetcher fails
                                               correctly and says so
    headless render                            curve drawn with per-point
                                               cadence dots, regime card,
                                               daily pulse, US cross-check,
                                               ERP — zero page errors

## Still open, honestly

PMI (licensed; press release the only free door, unverified), core CPI
(needs deeper parsing of MoSPI's subgroup tables), quarterly GDP, trade and
BoP (parsers written, still never met a live release), SIP flows (AMFI PDF
only). A daily official India par curve remains the one thing I would buy if
anything on this site were worth paying for.
