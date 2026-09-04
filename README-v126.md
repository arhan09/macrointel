# MacroIntel v126 — the desk reads clean, F&O has a desk, the curve is bootstrapped

**Upload** at the repo root (replace same names), then Actions → *daily-update* → **Run workflow**:
`macro_intelligence_terminal.html` · `update_terminal.py` · `ml_models.py` · `fno_setups.py` · `tearsheet.py` · `.github/workflows/daily-update.yml` · `t121_safety.py` · `t122_validation.py` · `t125_desk.py` · `t126_desk.py` · `README-v126.md`

Built on v125 (all v125 fixes carried; see the v125 README in the repo history). Three suites green: `t121`, `t125`, `t126`. 11 tabs render headless with zero errors and zero warnings.

---

## 1 · Less on the page

**Tabs, in reading order:** DESK · MACRO · RATES · MICRO · CHARTS · VALIDATION · RESERVES & FX · COMMODITIES · GLOBAL · NEWS. The TEAR SHEETS tab is gone: the PDF pages now sit as an appendix at the bottom of CHARTS (same blocks, same numbers, no second place to look).

**Notes are off by default.** A `📝 NOTES OFF` toggle at the right of the tab bar shows every methodology paragraph again. Nothing was deleted from the file; the page just stops explaining itself unless asked.

**Sections cut** (hidden by header text at boot, renderers untouched):
- DESK: *THE LIVE BOOK* → moved into MICRO › BUILD & SIZE, under the planner. *THE REGIME IN FULL* → gone (MACRO has it). *THE READ BEHIND IT* → now *THE MODEL DESK · THE CALENDAR · WHERE TO GO NEXT*: the six repeated tiles and the transmission chain are verbose-only; the model calls, the calendar and the routes stay.
- MACRO keeps: 0.05 growth · 0.1 the macro blocks · 0.21 nowcast · 0.25 the curve · 1 regime quadrant · 2 market cross-check · 9 scenarios. Cut: 0 positioning (the DESK stance is the stance), 0.06, 0.2, 0.3 (→ F&O tab), 0.35, 0.5, 0.6, 0.7, the charts panel, 3–8.
- RATES: the three explainer sections (📡, 3, 4) cut. RESERVES: unchanged. COMMODITIES: auto-read and the pass-through arithmetic cut. GLOBAL: keeps stress + dollar/US rates. NEWS: the eleven-section essay cut; headlines and raw feed stay.

## 2 · MICRO › F&O

A fourth sub-tab. One row per near-month stock future (the updater now publishes the full table, `FNO_LIVE.stocks`: fut, spot, basis bp, day %, OI, ΔOI %, quadrant, expiry, same ₹-liquidity floor as the movers). Each name is read against the macro board before it is a trade:

`SETUP = theme board (macro prior × price) ∩ the future's own OI quadrant ∩ the short-horizon screen`, capped by the desk stance and the stress gate. Labels: LONG SETUP · SHORT SETUP · WAIT · WAIT · GATE · TACTICAL · PRICE ONLY · NO TRADE. Sortable, searchable.

Click a name → the card: a 52-week chart, then the chain the feedback asked for — **1 MACRO PRIOR → 2 MARKET CONFIRMATION → 3 THE BOARD → 4 THE NAME** (OI read, basis, screen scores, oil beta) — then **WHY LONG/SHORT · WHY NOW**, **THESIS BREAKS IF** (board flip, stress ≥ 60, Nifty under its 200-dma, basis inversion, ΔOI against, a 2.5σ stop off 20 weekly returns) and a **TRADE EXPRESSION** (side, entry on the near-month, stop, 2R target, horizon, the 0.25% model cap) that stays unsized until it goes through BUILD & SIZE.

It is rule-based and says so on every screen — and it is in the ledger (see §5).

Until the first Actions run after upload, the desk shows only the 34 names the previous updater carried (quadrant + movers boards); the 200-name table arrives on the next pass.

## 3 · RATES › 2.7 the curve, bootstrapped

The BlueGamma screen you sent is now on the page as a dated reference (`OIS_REF`, hand-dated 4 Sep 12:14: 3Y 6.316 · 5Y 6.470 · 7Y 6.605 · 10Y 6.728). A table prints the fixing against it: on the Sep 4 page the fixing is **8 days old and 10–12bp under the screen** — the source problem, visible instead of implied.

From that curve (level from the screen, shape from the fixing, the shift printed in bp; 7Y/10Y from the screen because the fixing does not quote them): discount factors, the zero curve against par, the **implied 6M forward path** (BlueGamma's "forward curve"), and forward-starting swaps — **1y1y 6.38 · 2y1y 6.46 · 5y5y 7.23** on Sep 4. INR OIS convention approximated: money-market simple to 1Y, semi-annual fixed beyond. A 10Y volatility cone is wired but waits for 60 sessions of the RBI-home 10Y trail (it holds 3); a cone on a shorter trail would be a shape without a distribution.

CCIL stays the first door; FBIL's own fixing feed is second (see §5); the mirror is last.

## 4 · CHARTS

The India chart pack (13 pages, Capital-Flows structure: POLICY · DECOMP · REGIMES · TERM STRUCTURE · CROSS-ASSET · EQUITIES · FX) is kept and is the one place for charts. **REGIMES is nominal 2s10s only**: 10Y minus the 2Y leg (the belly dated stock, 6.20% GS 2029, off the RBI home page), with the ON→10Y fallback labelled while the 2Y trail is shorter than four sessions (it holds 3 and accrues daily). `tearsheet.py` page 21 is retitled *Curve regime · nominal 2s10s only* and the inflation/real rows are dropped — India has no inflation-swap or linker curve, so those layers were US constructs wearing an India label.

## 5 · The two things that were open, closed

**FBIL is the source now.** The keyless endpoint the FBIL site itself calls — `https://www.fbil.org.in/wasdm/miborois/fetch?authenticated=false` — returns the official MIBOR-OIS fixing as JSON (ten tenors, the latest two dates). `fetch_ois_fbil()` sits between CCIL and the old mirror in `fetch_ois_curve`; RUN_LOG reports it as *FBIL official fixing as of … (public feed, delayed)*. The public feed runs a few sessions behind the subscriber feed (latest 27 Aug on 4 Sep), which is the same gap the page showed — so the dealer-screen reference stays as the live level and the mirror is retired from the primary path. The RATES header no longer names Cbonds.

**F&O setups are in the ledger.** `fno_setups.py` loads the built page headless (Playwright, installed in the workflow) and calls the page's own `fnoSetupsForLedger()`, so the ledger scores exactly the rule the desk showed — no Python re-implementation to drift. LONG/SHORT SETUP rows (gated longs excluded: a WAIT is not a call) become model **fno** calls at the ML pass with entry = last spot close, stop = 2.5σ of 20 weekly returns (3–12%), target = 2R, horizon 15 sessions. `score_ledger` now scores any call carrying a stop/target on its **path**: first close through the stop closes at the stop, through the target at the target, else the due date (`closed_by` recorded). Each F&O card shows *IN THE LEDGER*: the open call, its mark, and the model's running hit rate. `fno_setups.json` is committed alongside the ledger so the payload behind every fno call is auditable.

## 6 · Still open

1. First Actions run: fills the F&O table, the ETF proxies (v125), starts the 2Y trail, writes the first fno calls.
2. Sector attribution on the CHARTS equities page needs sector weights (Nifty 50 constituent weights from the NSE factsheet — one keyless PDF/CSV door).
3. The US-style pages still to build for India: an MPC-dated implied policy path (the bill/OIS path by meeting date), a term-structure momentum page (OIS strip 1D/1W/1M changes), and a rotation map (RS ratio vs RS momentum by sector) — all from blocks already on the page.
4. CCIL traded curve: still the door to open for a same-day level (the FBIL public feed is delayed; the screen bridges until then).
