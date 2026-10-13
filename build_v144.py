#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_v144.py — the v144/v145 surgery on the page, reproducibly (v145 adds the X-ray, WHERE TO BE and the pairs).

Reads the v143 page (every data anchor the pipeline patches is kept, byte for byte), and:
  · appends the v144 theme to the page's <style>
  · adds the new six-tab nav (the old one stays in the DOM, hidden — sw() reads it)
  · puts the engine-driven panes first in HOME · RESEARCH · MARKETS · AGENTS and new INDUSTRIES
    and ASK tabs; the legacy panes stay underneath, hidden, and are shown where they still
    earn their place (the F&O index cards and the option chain, BUILD & SIZE, the books in full)
  · gives every deep macro pane the one macro bar
  · appends the v144 scripts (E.*) after the page's own script
  · stamps v144

Usage: python build_v144.py [in.html] [out.html]
"""
import re, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else "macro_intelligence_terminal.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else SRC
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v144")


def rd(f):
    return open(os.path.join(V, f), encoding="utf-8").read()


def must(html, old, new, label, count=1):
    if old not in html:
        raise SystemExit("anchor not found: " + label)
    return html.replace(old, new, count)


h = open(SRC, encoding="utf-8").read()
if "E-V144-BUILT" in h or "E-V145-BUILT" in h or "E-V146-BUILT" in h:
    raise SystemExit("already built — start from the v143 page")

# 1 · the theme — its own block after the page's last <style>, so it wins on order as well as specificity
k = h.rfind("</style>")
if k < 0:
    raise SystemExit("no </style>")
h = h[:k + len("</style>")] + "\n<style id=\"e-theme\">\n/* ═══ v144 THEME ═══ */\n" + rd("theme.css") + "\n</style>" + h[k + len("</style>"):]

# 2 · the nav
NAV = '''<!-- ═══ NAV · v144 ═══ -->
<div class="e-nav" id="e-nav">
<button class="tab a" data-tab="home" onclick="E.go('home')">Home</button>
<button class="tab" data-tab="micro" onclick="E.go('micro')">Markets</button>
<button class="tab" data-tab="research" onclick="E.go('research')">Research</button>
<button class="tab" data-tab="macro" onclick="E.go('macro')">Macro</button>
<button class="tab" data-tab="industries" onclick="E.go('industries')">Industries</button>
<button class="tab" data-tab="agents" onclick="E.go('agents')">Arena</button>
<button class="tab" data-tab="ask" onclick="E.go('ask')">Ask</button>
<span class="sp"></span>
<div class="e-more"><button onclick="this.parentNode.classList.toggle('open')">More ▾</button><div class="e-more-menu">
<div class="h">The macro desk</div>
<button onclick="E.go('ois')">Rates · OIS, the corridor, the curve</button>
<button onclick="E.go('forex')">The rupee · reserves, flows</button>
<button onclick="E.go('comm')">Gold &amp; oil · MCX, the shock</button>
<button onclick="E.go('intl')">Global · cross-asset stress</button>
<button onclick="E.go('charts')">Chart pack &amp; tear sheets</button>
<div class="h">The desk</div>
<button onclick="E.go('research','portfolio')">🩻 My portfolio · the X-ray</button>
<button onclick="E.go('micro','where')">🧭 Where to be · the regime map</button>
<button onclick="E.go('micro','records')">Records · BUILD &amp; SIZE</button>
<button onclick="E.go('news')">News wire</button>
<button onclick="E.go('qa')">Ask the desk (classic)</button>
<button onclick="try{openLens()}catch(e){}">The regime lens</button>
<div class="h">Live quotes</div>
<button onclick="try{setLiveDoor()}catch(e){}">⚙ Paste your live door (worker URL)</button>
<button onclick="try{E.ask.settings()}catch(e){}">✦ Claude key for Ask (optional)</button>
<button onclick="document.body.classList.toggle('verbose')">Toggle the desk's notes</button>
</div></div>
</div>
'''
h = must(h, '<!-- ═══ NAV · v141 ═══ -->', NAV + '<!-- ═══ NAV · v141 (hidden; sw() reads it) ═══ -->', "nav")

# 3 · HOME · RESEARCH · new tabs
h = must(h, '<div id="tab-home" class="tp a">\n<div id="home-body"></div>\n</div>',
         '<div id="tab-home" class="tp a">\n<div id="e-home"></div>\n<div class="e-legacy" id="e-legacy-home"><div id="home-body"></div></div>\n</div>\n'
         '<div id="tab-industries" class="tp">\n<div id="e-industries"></div>\n</div>\n'
         '<div id="tab-ask" class="tp">\n<div id="e-ask-tab"></div>\n</div>', "home pane")
h = must(h, '<div id="tab-research" class="tp">\n<div id="research-body"></div>\n</div>',
         '<div id="tab-research" class="tp">\n<div id="e-research"></div>\n<div class="e-legacy" id="e-legacy-research"><div id="research-body"></div></div>\n</div>', "research pane")

# 4 · MARKETS: the engine pane first; the old search + subtabs hidden; INTRADAY/SHORT/LONG hidden; F&O and BUILD shown on demand
h = must(h, '<div id="tab-micro" class="tp">\n<div id="stocks-search"></div>',
         '<div id="tab-micro" class="tp">\n<div id="e-markets"></div>\n<div class="e-legacy" id="e-legacy-mk-top"><div id="stocks-search"></div>', "markets top")
h = must(h, '<!-- ── INTRADAY ── -->\n<div id="sub-intraday">', '</div>\n<!-- ── INTRADAY ── -->\n<div class="e-legacy" id="e-legacy-intra"><div id="sub-intraday">', "intraday")
h = must(h, '<!-- ── SHORT TERM ── -->\n<div id="sub-short" style="display:none">', '</div>\n<!-- ── SHORT TERM ── -->\n<div class="e-legacy" id="e-legacy-short"><div id="sub-short" style="display:none">', "short")
# find the start of the long block and the build block and the fno block
h = must(h, '<div id="sub-long" style="display:none">', '</div>\n<div class="e-legacy" id="e-legacy-long"><div id="sub-long" style="display:none">', "long")
h = must(h, '<div id="sub-build" style="display:none">', '</div>\n<div class="e-legacy" id="e-legacy-desk"><div id="sub-build" style="display:none">', "build")
h = must(h, '<div id="sub-fno" style="display:none">', '</div>\n<div class="e-legacy" id="e-legacy-fno"><div id="sub-fno" style="display:none">', "fno")
# close the last wrapper (fno) before the AGENTS tab
h = must(h, '</details>\n</details>\n</div>\n</div>\n\n<!-- ══════════════ TAB · AGENTS (v143 · the arena) ══════════════ -->',
         '</details>\n</details>\n</div>\n</div>\n</div>\n\n<!-- ══════════════ TAB · AGENTS (v143 · the arena) ══════════════ -->', "markets end")

# 5 · AGENTS
h = must(h, '<div id="tab-agents" class="tp">\n<div id="agents-feed" style="margin-bottom:12px"></div>',
         '<div id="tab-agents" class="tp">\n<div id="e-arena"></div>\n<div class="e-legacy" id="e-legacy-agents">\n<div id="agents-feed" style="margin-bottom:12px"></div>', "agents")
h = must(h, '<div id="desk-tape" style="display:none"></div>\n</div>\n\n<div id="tab-news" class="tp">',
         '<div id="desk-tape" style="display:none"></div>\n</div>\n</div>\n\n<div id="tab-news" class="tp">', "agents end")

# 6 · the macro bar on every deep pane
for tab, anchor in [("macro", '<div id="tab-macro" class="tp">\n'), ("charts", '<div id="tab-charts" class="tp">\n'), ("ois", '<div id="tab-ois" class="tp">\n'),
                    ("forex", '<div id="tab-forex" class="tp">\n'), ("comm", '<div id="tab-comm" class="tp">\n'), ("intl", '<div id="tab-intl" class="tp">\n'),
                    ("news", '<div id="tab-news" class="tp">'), ("qa", '<div id="tab-qa" class="tp">\n'), ("validation", '<div id="tab-validation" class="tp">\n')]:
    extra = '<div id="e-macro-head"></div>\n' if tab == "macro" else ""
    h = must(h, anchor, anchor + extra + '<div class="e-macrobar" id="e-mbar-' + tab + '"></div>\n', "bar " + tab)

# 7 · the scripts, after the page's own
JS = "\n".join(rd(f) for f in ("e-core.js", "e-markets.js", "e-share.js", "e-industry.js", "e-ask.js", "e-arena.js", "e-macro.js", "e-nowcast.js", "e-alloc.js", "e-portfolio.js", "e-pipe.js", "e-boot.js"))
h = must(h, "</script>\n</body>", "</script>\n<!-- E-V146-BUILT -->\n<script>\n" + JS + "\n</script>\n</body>", "script end") if "</script>\n</body>" in h else must(h, "</body>", "<!-- E-V146-BUILT -->\n<script>\n" + JS + "\n</script>\n</body>", "body end")

# 7b · the live loop batches 80 names a call instead of 40 (the spark endpoint takes it; half the calls a minute)
h = h.replace("for(let i=0;i<syms.length;i+=40){const chunk=syms.slice(i,i+40)", "for(let i=0;i<syms.length;i+=80){const chunk=syms.slice(i,i+80)", 1)

# 7c · index lot sizes as revised by NSE in late 2025 (the page's constant was a year old)
h = h.replace("const MK_IDX_LOT={NIFTY:75,BANKNIFTY:35,FINNIFTY:65,MIDCPNIFTY:140,NIFTYNXT50:25};", "const MK_IDX_LOT={NIFTY:65,BANKNIFTY:30,FINNIFTY:60,MIDCPNIFTY:120,NIFTYNXT50:25};", 1)

# 7d · the one-line disclaimer under every pane
h = must(h, '</main>', '<div class="e-disc">A personal research tool, free, not SEBI-registered · model output, not investment advice · prices may be delayed · F&amp;O can lose all your money</div>\n</main>', "main end")

# 8 · the stamp
h = re.sub(r'(<span id="build-version"[^>]*>)[^<]*(</span>)', r'\g<1>v146\g<2>', h, count=1)
h = h.replace("MACROINTEL 3 · v143", "MACROINTEL 3 · v146")
open(OUT, "w", encoding="utf-8").write(h)
print("built %s (%.2f MB)" % (OUT, len(h) / 1e6))
