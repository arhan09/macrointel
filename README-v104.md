# v104 — the gold box goes live, anchored on India's official print

**Supersedes every earlier zip (v94-v103 all included). Three code files to
the repo root, workflow untouched, Run workflow. Header v104 confirms.**

## What changed

**The IBJA fix is now a live source.** India's official bullion association
publishes an AM and PM fix (999 fine, per 10g, ex-GST) every working day in
plain server-rendered HTML. The pipeline now reads it (new GOLD_INR block,
contract 27 of 27), carries it with its date on weekends and holidays, and
the gold box anchors on the print instead of an estimate. The import wedge
over parity is COMPUTED and displayed, not decomposed into guessed duty
lines. Parser unit-tested against the real page text, including the trap
where an older date's rows sat inside the parse window.

**The chain your Kolkata quote sits on, every link visible:**

    Gold $/oz (live, browser-refreshed)
    USD/INR (live — its own tile now, as asked)
    Import parity ₹/10g          = spot x FX (recomputes live)
    IBJA official fix ₹/10g      = ₹1,49,621 (07 Aug PM, ex-GST)
    With 3% GST                  = ₹1,54,110
    22K (916) IBJA fix           = ₹1,37,053
    Silver IBJA ₹/kg             = ₹2,31,381 (+ world $/oz)
    Real repo                    = the driver

Your ₹1,55,610 Kolkata board = the GST-inclusive line plus a local premium —
and note gold moved: during verification the live streamer pulled spot at
$4,414 (+4%), lifting parity to ₹1,35,086, which is exactly why Monday's fix
will print above Friday's. The box shows that happening in real time.

**Real time, properly.** The page already streams quotes in the browser
every 4 minutes during market hours (that is where the $ gold, silver and
USD/INR tiles come from — Yahoo, client-side). The gold and commodities
boxes now sit on that refresh list, so parity, the GST line and rupee-crude
recompute live as the dollar tiles tick. The IBJA fix stays what it is: a
once-a-day official print with its date on it.

**Shares research is written, not tabulated.** The regime-favours section is
now flowing prose — a few names with their scores and 12-month numbers woven
into sentences — and the sentences are GENERATED from the model's daily
output at render time, so the paragraph rewrites itself when the ranks
change. Nothing typed. Current read: Federal Bank at the top of the
in-regime set, Bajaj Auto and Bajaj Finance close behind, Eicher rounding it
out; Divis and Titan as trend-vs-macro; the weakest composites named as
avoid-not-short.

## Verified

    t104 (IBJA parser, doors, carry) + all prior suites   FAILURES: none
    contract audit                                        27/27
    node --check                                          0 failures
    dry run                                               weekend behaviour
                                                          correct (no fix
                                                          published -> carried
                                                          with its date)
    headless render                                       live streamer fired
                                                          during the test: spot
                                                          ticked to $4,414 and
                                                          parity recomputed in
                                                          the box; prose section
                                                          renders; zero errors
