#!/usr/bin/env python3
"""Regenerate SEO + AI-discoverability files from tools.json.
Idempotent: injects head tags between <!--seo--> markers, static crawlable lists
between <!--static--> markers, and rewrites sitemap.xml, robots.txt, llms.txt."""
import json, re, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://aitooldirectory-beta.vercel.app"
d = json.loads((ROOT/"tools.json").read_text())
E = lambda s: html.escape(str(s or ""), quote=True)
cats = {c["id"]: c for c in d["categories"]}
by_cat = {c: sorted([t for t in d["tools"] if t["category"] == c], key=lambda t: t["rank"]) for c in cats}
new = sorted([t for t in d["tools"] if t.get("isNew")], key=lambda t: t.get("released") or "", reverse=True)

PAGES = {
 "index.html": ("AI Tool Rank: Best AI tools by use case",
   f"Ranked picks of {len(d['tools'])} AI tools across {len(cats)} use cases, from video and coding to agents and music, plus verified new releases and deals."),
 "new.html": ("New AI Tool Releases | AI Tool Rank", "The newest AI tool releases, each checked against the maker's own launch post with a release date and source link."),
 "compare.html": ("Compare AI Tools Side by Side | AI Tool Rank", "Compare up to three AI tools side by side on use case, features, pricing notes, free option and editorial rating."),
 "deals.html": ("AI Tool Deals: Student, Startup and Free-Tier Offers | AI Tool Rank", "Verified AI tool deals for students, startups and free-tier users, each with eligibility, source link and date checked."),
 "methodology.html": ("How We Rank AI Tools | AI Tool Rank", "How AI Tool Rank picks and rates AI tools: editorial ratings, sourcing rules for new releases, and how sponsorships are labeled."),
 "advertise.html": ("Advertise on AI Tool Rank", "Sponsor a clearly labeled placement on AI Tool Rank to reach builders, vibe coders and AI agent enthusiasts."),
 "submit.html": ("Submit an AI Tool | AI Tool Rank", "Suggest an AI tool for AI Tool Rank's directory and rankings."),
 "newsletter.html": ("AI Tool Rank Newsletter: New AI Tools Weekly", "A weekly email with the newest AI tool releases and ranking changes from AI Tool Rank."),
 "tool.html": ("AI Tool Details | AI Tool Rank", "Write-up of an AI tool: what it's best for, standout features, who should skip it, pricing notes and editorial rating."),
}
for c in cats.values():
    PAGES[f"category/{c['id']}.html"] = (f"Best AI Tools for {c['name']} ({len(by_cat[c['id']])} ranked) | AI Tool Rank",
        f"Ranked AI tools for {c['name'].lower()}: {c['intro'].rstrip('.')}. Top picks: " + ", ".join(t['name'] for t in by_cat[c['id']][:4]) + ".")

def ld(obj): return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + '</script>'
def tool_ld(t, i):
    o = {"@type": "ListItem", "position": i, "item": {"@type": "SoftwareApplication", "name": t["name"], "url": t["url"],
         "applicationCategory": cats[t["category"]]["name"], "description": t["blurb"]}}
    return o
def static_list(ts, prefix):
    return "".join(f'<div class="card"><h3><a href="{prefix}tool.html?id={E(t["id"])}">{E(t["name"])}</a></h3><p class="muted">Best for: {E(t["bestFor"])}. {E(t["blurb"])}</p></div>' for t in ts)

def inject(path, title, desc):
    p = ROOT/path; s = p.read_text()
    url = BASE + "/" + ("" if path == "index.html" else path)
    prefix = "../" if path.startswith("category/") else ""
    extra = ""
    if path == "index.html":
        extra = ld({"@context": "https://schema.org", "@type": "WebSite", "name": "AI Tool Rank", "url": BASE + "/", "description": desc})
    elif path.startswith("category/"):
        cid = path.split("/")[1][:-5]
        extra = ld({"@context": "https://schema.org", "@type": "ItemList", "name": f"Best AI Tools for {cats[cid]['name']}",
                    "itemListOrder": "https://schema.org/ItemListOrderAscending",
                    "itemListElement": [tool_ld(t, i+1) for i, t in enumerate(by_cat[cid])]})
        s = re.sub(r'<h1 id="t">.*?</h1>', f'<h1 id="t">Best AI Tools for {E(cats[cid]["name"])}</h1>', s)
        s = re.sub(r'<p id="i" class="muted">.*?</p>', f'<p id="i" class="muted">{E(cats[cid]["intro"])}</p>', s)
        s = fill(s, "list", static_list(by_cat[cid], prefix))
    elif path == "new.html":
        extra = ld({"@context": "https://schema.org", "@type": "ItemList", "name": "New AI Tool Releases",
                    "itemListElement": [tool_ld(t, i+1) for i, t in enumerate(new)]})
        s = fill(s, "list", static_list(new, prefix))
    if path == "index.html":
        s = fill(s, "cats", "".join(f'<a class="card" href="category/{c["id"]}.html"><h3>{E(c["name"])}</h3><p class="muted">{E(c["intro"])}</p></a>' for c in cats.values()))
    head = (f'<!--seo--><meta name="description" content="{E(desc)}"><link rel="canonical" href="{url}">'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="AI Tool Rank"><meta property="og:title" content="{E(title)}">'
            f'<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta name="twitter:card" content="summary">{extra}<!--/seo-->')
    s = re.sub(r'<!--seo-->.*?<!--/seo-->', '', s, flags=re.S)
    s = re.sub(r'<title>.*?</title>', f'<title>{E(title)}</title>', s, count=1)
    s = s.replace('</title>', '</title>' + head, 1)
    links = [("index.html","Home"),("new.html","New releases"),("compare.html","Compare"),("deals.html","Deals"),("methodology.html","Methodology"),
             ("newsletter.html","Newsletter"),("submit.html","Submit a tool"),("advertise.html","Advertise")]
    nav = ('<!--sitelinks--><nav class="sitelinks" aria-label="Site links">' + "".join(f'<a href="{prefix}{h}">{n}</a>' for h, n in links) +
           "".join(f'<a href="{prefix}category/{c["id"]}.html">{E(c["name"])}</a>' for c in cats.values()) + '</nav><!--/sitelinks-->')
    s = re.sub(r'<!--sitelinks-->.*?<!--/sitelinks-->', '', s, flags=re.S)
    s = s.replace('</main>', '</main>' + nav, 1)
    p.write_text(s)

def fill(s, el_id, content):
    s = re.sub(rf'(id="{el_id}">)<!--static-->.*?<!--/static-->', r'\1', s, flags=re.S)
    return s.replace(f'id="{el_id}">', f'id="{el_id}"><!--static-->{content}<!--/static-->', 1)

for path, (t, ds) in PAGES.items(): inject(path, t, ds)

urls = [u for u in PAGES if u != "tool.html"]
(ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    "".join(f"  <url><loc>{BASE}/{'' if u=='index.html' else u}</loc><lastmod>{d['updated']}</lastmod></url>\n" for u in urls) +
    "".join(f"  <url><loc>{BASE}/tool.html?id={t['id']}</loc><lastmod>{d['updated']}</lastmod></url>\n" for t in d["tools"]) + "</urlset>\n")
(ROOT/"robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

L = [f"# AI Tool Rank", "", f"> A directory that recommends AI tools by use case, with editorial ratings, verified new releases and verified deals. Last updated {d['updated']}.", "",
     "Ratings are editorial opinions, not benchmarks. Pricing changes often; the directory does not list prices it hasn't confirmed, so check each official site. New releases are only added after checking the maker's own launch post, which is linked as the source.", "",
     "## Pages", f"- [New releases]({BASE}/new.html): newest verified AI tool launches with dates and source posts",
     f"- [Deals]({BASE}/deals.html): verified student, startup and free-tier offers", f"- [Compare]({BASE}/compare.html): side-by-side tool comparison",
     f"- [Methodology]({BASE}/methodology.html): how tools are rated", ""]
for c in cats.values():
    L += [f"## {c['name']}", f"{c['intro']} Full ranking: {BASE}/category/{c['id']}.html", ""]
    for t in by_cat[c["id"]]:
        r = f"rated {t['rating']}/10" if t.get("rating") is not None else "not yet rated"
        ft = {True: "free option offered", False: "primarily paid", None: "free option not confirmed"}[t.get("freeTier")]
        rel = f", released {t['released']} ([launch post]({t['source']}))" if t.get("released") and t.get("source") else ""
        L.append(f"- #{t['rank']} [{t['name']}]({t['url']}): best for {t['bestFor'].lower()}. {t['blurb']} ({r}, {ft}{rel})")
    L.append("")
(ROOT/"llms.txt").write_text("\n".join(L))
print("built", len(PAGES), "pages")
