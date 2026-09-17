#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v132 · push_call.py — THE CALL, delivered.

Runs in the daily-update workflow after the post-close pass and sends the
day's call — the regime and state line, the five names with stop and target,
the record — to a Telegram channel or group. Reads only what the pass has
already written (fno_setups.json's page_state, ml_output.json); computes
nothing new, so the message can never disagree with the page.

Configuration is two repository secrets (Settings → Secrets and variables →
Actions), never anything in this file or on the page:
    TELEGRAM_BOT_TOKEN   from @BotFather (/newbot)
    TELEGRAM_CHAT_ID     the channel/group id (add the bot as an admin of a
                         channel, or to a group; for a channel use @channelname
                         or the numeric -100… id)
With either missing the script prints one line and exits 0 — the page is
never affected by delivery.
"""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
SITE = "https://arhan09.github.io/macrointel/"


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _n(x, d=0):
    try:
        return ("{:,.%df}" % d).format(float(x))
    except Exception:
        return "—"


def compose(fs, ml, now=None):
    """the message, from the pass's own files — None when there is no page state today"""
    now = now or datetime.now(IST)
    ps = (fs or {}).get("page_state") if isinstance(fs, dict) else None
    if not isinstance(ps, dict):
        return None
    if str((fs or {}).get("date", ""))[:10] != now.strftime("%Y-%m-%d"):
        return None                                   # yesterday's state is not today's call
    D = ps.get("dials") or {}
    W = ps.get("watch") or {}
    top = W.get("top") or []
    reg = ps.get("regime") or "—"
    dl = D.get("quad_market")
    agree = ("the market agrees" if dl == reg else ("market dials read %s" % dl)) if dl else ""
    lines = ["MacroIntel · %s · post-close" % now.strftime("%a %d %b %Y")]
    line = "%s%s · %s (size %s%s)" % (reg, (", " + agree) if agree else "", ps.get("market_state") or "—",
                                      ps.get("cap") or "—", (" × %s" % D["mult"]) if D.get("mult") not in (None, 1, 1.0) else "")
    if D.get("rates_view"):
        line += " · rates %s" % D["rates_view"]
    if D.get("fx_view"):
        line += " · rupee %s" % D["fx_view"]
    lines.append(line)
    board = [b for b in (ps.get("board") or []) if b.get("action") in ("LONG", "UNDERWEIGHT")]
    board.sort(key=lambda b: {"HIGH": 3, "MED": 2}.get(b.get("conv"), 1), reverse=True)
    if board:
        lines.append("Board: " + ", ".join("%s %s (%s)" % (b["action"], b.get("nm"), b.get("conv")) for b in board[:3]))
    lines.append("")
    if top:
        lines.append("Top 5 to watch (≤2 per theme, 15 sessions):")
        for i, x in enumerate(top[:5], 1):
            spot, sp = x.get("spot"), x.get("stop_pct")
            sg = 1 if x.get("side") == "LONG" else -1
            stop = spot * (1 - sg * sp / 100) if (spot and sp) else None
            tgt = spot * (1 + sg * 2 * sp / 100) if (spot and sp) else None
            lines.append("%d. %s %s · %s · stop %s (%s%%) · target %s · %s/%s of the chain agree"
                         % (i, x.get("name") or x.get("sym"), x.get("side"), _n(spot, 2), _n(stop, 2),
                            _n(sp, 1), _n(tgt, 2), x.get("agree"), x.get("n")))
    else:
        lines.append("Top 5 to watch: nothing carries a mechanical side today%s." % (" (gate on)" if W.get("gate") else ""))
    T = (ml or {}).get("tomorrow") or {}
    if T.get("direction"):
        pu = T.get("p_up") or 0.5
        lines.append("Tomorrow: %s %d%% (%s) · out-of-sample %s%% vs base %s%%" % (T["direction"], round((pu if T["direction"] == "UP" else 1 - pu) * 100),
                     "a lean" if T.get("conviction") == "lean" else "a call", _n(T.get("acc_oos"), 1), _n(T.get("base_rate"), 1)))
    lines.append("")
    recs = (ml or {}).get("recs") or {}
    tot = recs.get("total") or {}
    if tot.get("n"):
        lines.append("Record — model calls: %s closed · hit %s%% · avg %s%% · %s open"
                     % (tot["n"], _n(tot.get("hit_pct"), 0), _n(tot.get("avg_ret_pct"), 2), recs.get("open_n", 0)))
    else:
        lines.append("Record — model calls: none closed yet · %s open" % recs.get("open_n", 0))
    lines.append("The list's own record and the full chain: " + SITE)
    lines.append("Rule: side from the desk, rank by how much of the chain agrees. Computed, not written.")
    return "\n".join(lines)


def send(text, token, chat_id):
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=20) as r:
        return r.status


def main():
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    msg = compose(_load("fno_setups.json"), _load("ml_output.json"))
    if msg is None:
        print("push: no page state for today — nothing to send"); return 0
    if not token or not chat:
        print("push: no channel configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) — the call was:\n" + msg); return 0
    try:
        st = send(msg, token, chat)
        print("push: sent (%s)" % st)
    except Exception as e:
        print("push: failed (%s: %s) — the page is unaffected" % (type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
