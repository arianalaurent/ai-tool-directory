#!/usr/bin/env python3
"""Render newsletter/YYYY-MM-DD.md issues into newsletter/<date>.html and newsletter/index.html.
Add a new issue: drop the approved .md in newsletter/, run this, then scripts/build_seo.py."""
import re, html, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
NL = ROOT/"newsletter"
BASE = "https://aitooldirectory-beta.vercel.app"
E = lambda s: html.escape(s, quote=True)

def inline(s):
    s = E(s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: f'<a href="{m.group(2).replace(BASE + "/", "../")}">{m.group(1)}</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)

def md(text):
    out, para, ul = [], [], False
    def flush():
        nonlocal para
        if para: out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>"); para = []
    for line in text.splitlines():
        if line.startswith("- "):
            flush()
            if not ul: out.append("<ul>"); ul = True
            out.append(f"<li>{inline(line[2:])}</li>"); continue
        if ul: out.append("</ul>"); ul = False
        if not line.strip(): flush()
        elif m := re.match(r'(#{1,3}) (.*)', line):
            flush(); n = len(m.group(1)); out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        else: para.append(line)
    flush()
    if ul: out.append("</ul>")
    return "\n".join(out)

def page(title, desc, path, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{E(title)}</title><!--seo--><!--/seo--><link rel="preconnect" href="https://rsms.me"><link rel="stylesheet" href="https://rsms.me/inter/inter.css">'
            f'<link rel="stylesheet" href="../style.css"><script>window.va=window.va||function(){{(window.vaq=window.vaq||[]).push(arguments)}};</script>'
            f'<script defer src="/_vercel/insights/script.js"></script>\n</head><body data-page="nl" data-root="../" ><main class="issue">{body}</main><script src="../app.js"></script></body></html>')

def issues():
    res = []
    for f in sorted(NL.glob("????-??-??.md"), reverse=True):
        t = f.read_text(); date = f.stem
        h1 = re.search(r'^# (.*)$', t, re.M).group(1)
        subj = (re.search(r'^\*\*Subject line:\*\* (.*)$', t, re.M) or [None, h1])[1]
        prev = (re.search(r'^\*\*Preview text:\*\* (.*)$', t, re.M) or [None, ""])[1]
        res.append(dict(date=date, file=f, h1=h1, subject=subj, preview=prev, text=t))
    return res

def build():
    iss = issues(); meta = []
    for i in iss:
        nice = datetime.date.fromisoformat(i["date"]).strftime("%b %-d, %Y")
        body = re.sub(r'^\*\*(Subject line|Preview text):\*\*.*\n', '', i["text"], flags=re.M)
        body = re.sub(r'^# .*\n', '', body, count=1, flags=re.M)
        content = (f'<p class="muted"><a href="index.html">← Newsletter archive</a> · {nice}</p><h1>{inline(i["subject"])}</h1>'
                   f'<p class="muted">{inline(i["preview"])}</p>{md(body)}'
                   f'<div class="card"><p><strong>Get the next issue:</strong> <a href="../newsletter.html">subscribe to The Weekly Drop</a>.</p></div>')
        (NL/f'{i["date"]}.html').write_text(page(i["subject"] + " | AI Tool Rank Newsletter", i["preview"] or i["subject"], f'newsletter/{i["date"]}.html', content))
        meta.append((f'newsletter/{i["date"]}.html', f'{i["subject"]} | AI Tool Rank Newsletter', i["preview"] or i["subject"], nice, i))
    lst = "".join(f'<a class="card" href="{p.split("/")[1]}"><p class="muted">{n}</p><h3>{inline(i["subject"])}</h3><p class="muted">{inline(i["preview"])}</p></a>' for p, _, _, n, i in meta)
    (NL/"index.html").write_text(page("Newsletter Archive | AI Tool Rank", "",  "newsletter/index.html",
        f'<h1>📬 The Weekly Drop: archive</h1><p>Every past issue of the AI Tool Rank newsletter, newest first.</p><p><a class="btn" href="../newsletter.html">Subscribe</a></p><div class="grid">{lst}</div>'))
    return meta

if __name__ == "__main__":
    print("built", len(build()), "issues")
