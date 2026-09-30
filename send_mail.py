#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v138 · send_mail.py — THE CALL, mailed.

Runs in the daily-update workflow after the post-close pass and mails the
day's call — regime and state, conviction, the five names with stop, target
and conviction, tomorrow's direction, next week's contenders, the dip
flags, the three agents' books, the analysts' alerts, the rates read, the
macro line — to whoever is on MAIL_TO. Reads only what the pass wrote
(fno_setups.json, ml_output.json, alerts.json, the page's own blocks);
computes nothing new, so the mail can never disagree with the page.

Configuration is repository secrets (Settings → Secrets and variables →
Actions), never anything in this file or on the page:
    MAIL_SMTP_HOST   e.g. smtp.gmail.com (default)
    MAIL_SMTP_PORT   587 (default; STARTTLS)
    MAIL_USER        the sending account (for Gmail: the address + an App Password)
    MAIL_PASS        its password / app password
    MAIL_TO          comma-separated recipients (Gautam, Arhan)
    MAIL_FROM        optional; defaults to MAIL_USER
With any of USER / PASS / TO missing the script prints the mail and exits 0.
Sends once a day (history/mail_<date>.done); MAIL_FORCE=1 overrides.
--alerts (every pass): the analysts' new ALERT-severity items, mailed once each.
"""
import json, os, re, sys, smtplib, html as _h
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
SITE = "https://arhan09.github.io/macrointel/"


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _blk(html, var):
    try:
        m = re.search(r"window\.%s\s*=\s*(\{.*?\});" % re.escape(var), html or "", re.S)
        return json.loads(m.group(1)) if m else {}
    except Exception:
        return {}


def _n(x, d=0):
    try:
        return ("{:,.%df}" % d).format(float(x))
    except Exception:
        return "—"


def _inr(v):
    try:
        v = float(v); a = abs(v); s = "−" if v < 0 else ""
        if a >= 1e7: return "%s₹%.2f cr" % (s, a / 1e7)
        if a >= 1e5: return "%s₹%.2f L" % (s, a / 1e5)
        return "%s₹%s" % (s, _n(a))
    except Exception:
        return "—"


def gather(now=None):
    now = now or datetime.now(IST)
    fs = _load("fno_setups.json") or {}
    ml = (_load("ml_output.json") or {})
    ml = ml.get("ml_output") or ml
    al = _load("alerts.json") or {}
    html = ""
    for p in ("macro_intelligence_terminal.html", "terminal.html"):
        try:
            html = open(p, encoding="utf-8").read(); break
        except FileNotFoundError:
            continue
    return {"now": now, "fs": fs, "ps": (fs.get("page_state") if isinstance(fs, dict) else None) or {}, "ml": ml, "al": al,
            "agents": _blk(html, "AGENTS"), "ois": _blk(html, "OIS_LIVE"), "mpc": _blk(html, "MPC_LIVE"), "reg": _blk(html, "REGIME_LIVE"),
            "flows": _blk(html, "FLOWS_LIVE"), "curves": _blk(html, "CURVES_LIVE"), "recs": _blk(html, "RECS_LIVE")}


def compose(G):
    """(subject, text, html) or None when there is no page state for today"""
    now, ps, ml, al = G["now"], G["ps"], G["ml"], G["al"]
    if not ps or str((G["fs"] or {}).get("date", ""))[:10] != now.strftime("%Y-%m-%d"):
        return None
    D = ps.get("dials") or {}; W = ps.get("watch") or {}; top = W.get("top") or []
    reg = ps.get("regime") or "—"; dq = D.get("quad_market")
    lines, rows = [], []
    def sec(t): lines.append(""); lines.append(t.upper()); rows.append('<tr><td colspan="6" style="padding:14px 0 4px;font:700 11px/1 monospace;letter-spacing:2px;color:#888">%s</td></tr>' % _h.escape(t.upper()))
    def row(cells, bold=False):
        lines.append("  " + " · ".join(str(c) for c in cells if c not in (None, "")))
        rows.append("<tr>" + "".join('<td style="padding:4px 8px 4px 0;font:%s13px/1.4 -apple-system,Segoe UI,Helvetica,Arial;color:#ddd;vertical-align:top">%s</td>' % ("700 " if (bold and i == 0) else "", _h.escape(str(c)) if c is not None else "") for i, c in enumerate(cells)) + "</tr>")
    # the line
    subj = "MacroIntel · %s · %s%s · %s" % (now.strftime("%a %d %b"), reg, (" (dials agree)" if dq == reg else (" (dials %s)" % dq if dq else "")), ps.get("market_state") or "—")
    lines.append("MacroIntel · %s · post-close" % now.strftime("%a %d %b %Y"))
    line = "%s%s · %s · size cap %s%s" % (reg, (", the market agrees" if dq == reg else ((", market dials read %s" % dq) if dq else "")), ps.get("market_state") or "—", ps.get("cap") or "—", (" × %s" % D["mult"]) if D.get("mult") not in (None, 1, 1.0) else "")
    if D.get("rates_view"): line += " · rates %s" % D["rates_view"]
    if D.get("fx_view"): line += " · rupee %s" % D["fx_view"]
    lines.append(line); rows.append('<tr><td colspan="6" style="padding:0 0 6px;font:14px/1.5 -apple-system,Segoe UI,Helvetica,Arial;color:#fff">%s</td></tr>' % _h.escape(line))
    # the five
    sec("Top 5 to watch · 15 sessions · ≤2 per theme")
    if top:
        row(["#", "name", "side", "spot", "stop / target", "conviction · chain"], True)
        for i, x in enumerate(top[:5], 1):
            spot, sp = x.get("spot"), x.get("stop_pct"); sg = 1 if x.get("side") == "LONG" else -1
            stop = spot * (1 - sg * sp / 100) if (spot and sp) else None; tgt = spot * (1 + sg * 2 * sp / 100) if (spot and sp) else None
            row([i, x.get("name") or x.get("sym"), x.get("side"), _n(spot, 2), "%s (%s%%) / %s" % (_n(stop, 2), _n(sp, 1), _n(tgt, 2)),
                 "%s%s · %s/%s agree" % ((x.get("conv_label") or "—"), (" %s" % x["conv"]) if x.get("conv") is not None else "", x.get("agree"), x.get("n"))], bold=False)
    else:
        row(["nothing carries a mechanical side today%s" % (" (gate on)" if W.get("gate") else "")])
    # tomorrow
    T = ml.get("tomorrow") or {}
    if T.get("direction"):
        pu = T.get("p_up") or 0.5
        sec("Tomorrow"); row(["%s %d%% (%s) · out of sample %s%% vs base %s%%" % (T["direction"], round((pu if T["direction"] == "UP" else 1 - pu) * 100), "a lean" if T.get("conviction") == "lean" else "a call", _n(T.get("acc_oos"), 1), _n(T.get("base_rate"), 1))])
    # contenders
    h5 = ((ml.get("wide") or {}).get("horizons") or {}).get("5") or {}
    cont = [p for p in (h5.get("top") or []) if p.get("fno") and not p.get("event")][:5]
    if cont:
        sec("Next week's contenders · 5-session ranker, F&O names, no event in the tape · IC %s t %s hit %s%%" % (h5.get("ic"), h5.get("t"), h5.get("hit")))
        for p in cont:
            row([p["name"], "pctl %s" % p.get("pctl"), "score %s" % p.get("score"), ("1d %s%% · 1w %s%%" % (p.get("r1"), p.get("r5"))) if p.get("r1") is not None else ""])
    # the dip
    Dp = ml.get("dip") or {}
    dn = sorted([dict(sym=k, **v) for k, v in (Dp.get("names") or {}).items() if (v.get("ext20") or 0) > 0], key=lambda z: -(z.get("p") or 0))[:5]
    if dn:
        sec("The dip · ≥5%% within 10 sessions · out of sample AUC %s" % Dp.get("auc"))
        for d in dn:
            row([d["sym"], "%d%%" % round(d["p"] * 100), "last %s" % _n(d.get("last"), 2), ("fades above %s" % _n(d["trig_px"], 0)) if d.get("trig_px") and (d.get("trig_pct") or 0) > 0 else ("fading from here" if d.get("trig_px") else "no level"), "run over below %s" % _n(d.get("sma20"), 0)])
    # the agents
    A = G["agents"]
    if A.get("agents"):
        sec("The three agents · ₹1 crore each · %s%s" % (A.get("asof") or "", (" · Nifty %s%%" % _n(A.get("nifty_ret_pct"), 2)) if A.get("nifty_ret_pct") is not None else ""))
        for x in (A.get("leaderboard") or []):
            ag = A["agents"].get(x["k"]) or {}; st = ag.get("stats") or {}
            hold = ", ".join("%s %s %s%%" % (p.get("name"), "L" if p.get("side") == "LONG" else "S", _n(p.get("ret_pct"), 1)) for p in (ag.get("positions") or [])[:8]) or "in cash"
            row([x["nm"], "%s (%s%%)" % (_inr(x["equity"]), _n(x["ret_pct"], 2)), "cash %s" % _inr(ag.get("cash")), "P&L %s" % _inr((st.get("realised") or 0) + (st.get("open_pnl") or 0)), hold])
    # alerts
    its = [it for it in (al.get("items") or []) if it.get("sev") in ("alert", "watch")][:8]
    if its or al.get("items"):
        sec("What is happening · %s alerts · %s new (%s)" % (al.get("n_alert", 0), al.get("n_new", 0), al.get("ts") or ""))
        for it in its:
            row([str(it.get("sev")).upper(), it.get("title")])
        us = next((it for it in (al.get("items") or []) if it.get("agent") == "us"), None)
        if us and us not in its:
            row(["US", us.get("title"), us.get("detail")])
    # rates + macro
    O, M, R, F = G["ois"], G["mpc"], G["reg"], G["flows"]
    pts = O.get("points") or {}
    sec("Rates and macro")
    if pts.get("1Y") and M.get("repo"):
        row(["1Y swap %s%% (%+dbp vs repo %s, fixing %s)" % (pts["1Y"], round((pts["1Y"] - M["repo"]) * 100), M["repo"], O.get("asof") or ""), ("next MPC %s" % M.get("next_meeting")) if M.get("next_meeting") else ""])
    g = R.get("growth") or {}; inf = R.get("inflation") or {}
    row(["regime %s" % (R.get("quad") or "—"), "growth %s %s" % (g.get("arrow") or "", g.get("basis") or ""), "inflation %s CPI %s" % (inf.get("arrow") or "", inf.get("cpi") or "—")])
    if F.get("fii") is not None:
        row(["FII %s₹%s cr · DII %s₹%s cr (%s)" % ("+" if float(F["fii"]) >= 0 else "−", _n(abs(float(F["fii"]))), "+" if float(F.get("dii") or 0) >= 0 else "−", _n(abs(float(F.get("dii") or 0))), F.get("asof") or "")])
    # record
    tot = (G["recs"].get("total") or {})
    sec("The record")
    row(["model calls: %s closed · hit %s%% · avg %s%%" % (tot.get("n", 0), _n(tot.get("hit_pct"), 0), _n(tot.get("avg_ret_pct"), 2)) if tot.get("n") else "model calls: none closed yet", "the lists' own records are on the page"])
    lines.append(""); lines.append("Everything above is the page's own state at the pass, computed, not written: " + SITE)
    text = "\n".join(lines)
    body = ('<div style="background:#0b0e14;padding:18px"><table cellspacing="0" cellpadding="0" style="width:100%%;max-width:760px;background:#0b0e14">'
            '<tr><td colspan="6" style="font:700 12px/1 monospace;letter-spacing:3px;color:#1fd67a;padding-bottom:10px">MACROINTEL · %s · POST-CLOSE</td></tr>%s'
            '<tr><td colspan="6" style="padding-top:16px;font:11px/1.5 -apple-system,Segoe UI,Helvetica,Arial;color:#888">Everything above is the page\'s own state at the pass, computed, not written. <a href="%s" style="color:#3d9cff">%s</a></td></tr></table></div>'
            % (now.strftime("%a %d %b %Y"), "".join(rows), SITE, SITE))
    return subj, text, body


def send(subj, text, body, host, port, user, pw, to, frm):
    msg = MIMEMultipart("alternative"); msg["Subject"] = subj; msg["From"] = frm; msg["To"] = ", ".join(to)
    msg.attach(MIMEText(text, "plain", "utf-8")); msg.attach(MIMEText(body, "html", "utf-8"))
    with smtplib.SMTP(host, port, timeout=40) as s:
        s.ehlo(); s.starttls(); s.ehlo(); s.login(user, pw); s.sendmail(frm, to, msg.as_string())


def mail_alerts():
    """v138.1 · every pass: the analysts' new ALERT-severity items, mailed once each (history/alerts_mailed.json)"""
    now = datetime.now(IST)
    al = _load("alerts.json") or {}
    items = [it for it in (al.get("items") or []) if it.get("sev") == "alert"]
    if not items:
        print("alerts mail: nothing at alert severity this pass"); return 0
    path = os.path.join("history", "alerts_mailed.json")
    done = _load(path) or []
    new = [it for it in items if it.get("key") not in done]
    if not new:
        print("alerts mail: %d alert(s) live, all mailed already" % len(items)); return 0
    subj = "MacroIntel · alert · %s" % "; ".join(str(it.get("title"))[:70] for it in new[:2])
    text = "MacroIntel · alerts · %s\n\n" % (al.get("ts") or now.strftime("%a %d %b %H:%M IST")) + "\n\n".join("• %s\n  %s" % (it.get("title"), str(it.get("detail") or "")) for it in new[:8]) + "\n\n" + SITE
    body = ('<div style="background:#0b0e14;padding:18px;font:13px/1.5 -apple-system,Segoe UI,Helvetica,Arial;color:#ddd"><div style="font:700 12px/1 monospace;letter-spacing:3px;color:#f6b400;padding-bottom:10px">MACROINTEL · ALERTS · %s</div>%s'
            '<div style="padding-top:12px;font-size:11px;color:#888"><a href="%s" style="color:#3d9cff">%s</a></div></div>'
            % (_h.escape(al.get("ts") or ""), "".join('<div style="padding:6px 0;border-top:1px solid #222"><b style="color:#fff">%s</b><div style="color:#999;font-size:12px">%s</div></div>' % (_h.escape(str(it.get("title"))), _h.escape(str(it.get("detail") or ""))) for it in new[:8]), SITE, SITE))
    host = os.environ.get("MAIL_SMTP_HOST") or "smtp.gmail.com"; port = int(os.environ.get("MAIL_SMTP_PORT") or "587")
    user, pw, to = os.environ.get("MAIL_USER"), os.environ.get("MAIL_PASS"), [x.strip() for x in (os.environ.get("MAIL_TO") or "").split(",") if x.strip()]
    frm = os.environ.get("MAIL_FROM") or user or ""
    if not (user and pw and to):
        print("alerts mail: not configured — would have sent:\n" + text); return 0
    try:
        send(subj, text, body, host, port, user, pw, to, frm)
        print("alerts mail: sent %d new to %s" % (len(new), ", ".join(to)))
        try:
            os.makedirs("history", exist_ok=True)
            cut = (now - timedelta(days=4)).strftime("%Y-%m-%d")
            keep = [k for k in done if str(k).rsplit("|", 1)[-1] >= cut] + [it["key"] for it in new]
            with open(path, "w") as f:
                json.dump(keep[-400:], f)
        except Exception:
            pass
    except Exception as e:
        print("alerts mail: failed (%s: %s) — the page is unaffected" % (type(e).__name__, e))
    return 0


def main():
    if "--alerts" in sys.argv:
        return mail_alerts()
    now = datetime.now(IST); today = now.strftime("%Y-%m-%d")
    flag = os.path.join("history", "mail_%s.done" % today)
    if os.path.exists(flag) and os.environ.get("MAIL_FORCE") != "1":
        print("mail: already sent today (%s)" % flag); return 0
    out = compose(gather(now))
    if out is None:
        print("mail: no page state for today — nothing to send"); return 0
    subj, text, body = out
    host = os.environ.get("MAIL_SMTP_HOST") or "smtp.gmail.com"; port = int(os.environ.get("MAIL_SMTP_PORT") or "587")
    user, pw, to = os.environ.get("MAIL_USER"), os.environ.get("MAIL_PASS"), [x.strip() for x in (os.environ.get("MAIL_TO") or "").split(",") if x.strip()]
    frm = os.environ.get("MAIL_FROM") or user or ""
    if not (user and pw and to):
        print("mail: not configured (MAIL_USER / MAIL_PASS / MAIL_TO) — the mail would have been:\n" + subj + "\n" + text); return 0
    try:
        send(subj, text, body, host, port, user, pw, to, frm)
        print("mail: sent to %s — %s" % (", ".join(to), subj))
        try:
            os.makedirs("history", exist_ok=True)
            with open(flag, "w") as f:
                f.write(now.isoformat())
        except Exception:
            pass
    except Exception as e:
        print("mail: failed (%s: %s) — the page is unaffected" % (type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
