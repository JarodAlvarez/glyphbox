#!/usr/bin/env python3
"""Build the docs and Learn pages of the site from markdown.

    python3 tools/build_site.py        # writes site/docs/ and site/learn/

docs/*.md        -> site/docs/<name>.html  (plus site/docs/index.html)
docs/learn/*.md  -> site/learn/<name>.html (site/learn/index.html = lesson 1)

Each page starts with a front-matter block (title, order). Fenced blocks
written as ```lua run become live editors that run on the page's console;
plain ```lua blocks stay as code. Needs the `markdown` package.
"""
import html
import json
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
DOCS, SITE = ROOT / "docs", ROOT / "site"

NAV = [("PLAY", "play/"), ("LEARN", "learn/"), ("DOCS", "docs/"), ("PLAYGROUND", "playground/"),
       ("GITHUB", "https://github.com/JarodAlvarez/glyphbox")]


def front_matter(text):
    meta = {}
    if text.startswith("---\n"):
        head, text = text[4:].split("\n---\n", 1)
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, text


def px_text(s):
    """Heading text for the console font: uppercase printable ASCII."""
    s = s.upper().replace("—", "-").replace("’", "'").replace("×", "X")
    return "".join(c for c in s if 32 <= ord(c) <= 126)


RUN_BLOCK = re.compile(r"^```lua run\n(.*?)^```\n", re.S | re.M)


def render(md_text):
    """Markdown to HTML, with ```lua run blocks turned into live editors."""
    blocks = []

    def stash(m):
        blocks.append(m.group(1).rstrip("\n"))
        return f"\n\nGLYPHRUN{len(blocks) - 1}\n\n"

    body = markdown.markdown(RUN_BLOCK.sub(stash, md_text),
                             extensions=["tables", "fenced_code", "toc"],
                             extension_configs={"toc": {"permalink": False}})

    def unstash(m):
        code = blocks[int(m.group(1))]
        return (f'<div class="try"><div class="try-bar"><span>TRY IT</span>'
                f'<button class="try-run">RUN</button><button class="try-reset">RESET</button></div>'
                f'<textarea spellcheck="false">{html.escape(code)}</textarea></div>')

    body = re.sub(r"<p>GLYPHRUN(\d+)</p>", unstash, body)

    # Headings in the console's language: h1 is a title bar, h2 pixel text over a rule
    def h1(m):
        t = re.sub("<[^>]+>", "", m.group(2))
        return (f'<h1 class="bar bar-title" id="{m.group(1)}" aria-label="{html.escape(t)}">'
                f'<canvas data-px="{html.escape(px_text(t))}" data-scale="3"></canvas>'
                f'<span class="mark" data-logo="mark"></span></h1>')

    def h2(m):
        t = re.sub("<[^>]+>", "", m.group(2))
        return (f'<h2 id="{m.group(1)}" aria-label="{html.escape(t)}">'
                f'<canvas data-px="{html.escape(px_text(t))}" data-scale="2"></canvas></h2>')

    body = re.sub(r'<h1 id="([^"]*)">(.*?)</h1>', h1, body)
    body = re.sub(r'<h2 id="([^"]*)">(.*?)</h2>', h2, body)
    return body, len(blocks) > 0


def page(title, crumb, body, runnable, depth, extra_top="", extra_bottom="", active=""):
    up = "../" * depth
    nav = "".join(f'<a href="{href if href.startswith("http") else up + href}"'
                  f'{" class=on" if label == active else ""}>{label}</a>' for label, href in NAV)
    console = ""
    if runnable:
        console = f"""
  <aside class="dock">
    <div class="screen framed"><canvas id="canvas" tabindex="0" aria-label="GLYPHBOX screen" oncontextmenu="event.preventDefault()"></canvas></div>
    <p class="keys">CLICK THE SCREEN, THEN: ARROWS MOVE · Z ACTION</p>
    <pre class="out" id="out">Press RUN on any example.</pre>
  </aside>"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#080808">
<title>{html.escape(title)} · GLYPHBOX</title>
<link rel="icon" href="{up}logo/glyphbox.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<link rel="stylesheet" href="{up}assets/site.css?v=VERSION">
</head>
<body>
<header class="bar top">
  <a class="brand" href="{up}" data-logo="horizontal" aria-label="GLYPHBOX home"></a>
  <canvas data-px="{crumb}" data-scale="2" class="crumb"></canvas>
  <nav>{nav}</nav>
</header>
<main class="doc{' runnable' if runnable else ''}">
  <article class="prose">
{extra_top}
{body}
{extra_bottom}
  </article>{console}
</main>
<footer class="foot"><span>(C) GUREEDO 2026</span><span>GLYPHBOX</span></footer>
<script src="{up}font.js"></script>
<script src="{up}glyph-ui.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/lua/lua.min.js"></script>
<script>window.GB_ROOT = "{up}";</script>
<script src="{up}assets/site.js?v=VERSION"></script>
{'<script src="' + up + 'console/glyphbox.js?v=VERSION" async></script>' if runnable else ''}
</body>
</html>
"""


def load_dir(d):
    pages = []
    for f in sorted(d.glob("*.md")):
        if f.name == "README.md":        # GitHub index, not a site page
            continue
        meta, text = front_matter(f.read_text())
        pages.append({"file": f, "slug": f.stem, "title": meta.get("title", f.stem),
                      "order": int(meta.get("order", 99)), "text": text})
    return sorted(pages, key=lambda p: (p["order"], p["slug"]))


def version():
    import hashlib
    h = hashlib.sha1()
    for p in (sorted(SITE.glob("console/glyphbox.*")) + [SITE / "assets/site.css", SITE / "assets/site.js"]
              + [SITE / f for f in ("play/play.js", "play/play.css", "play/scanner.js",
                                    "playground/playground.js", "playground/playground.css")]):
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


def main():
    ver = version()
    out_learn, out_docs = SITE / "learn", SITE / "docs"
    out_learn.mkdir(exist_ok=True)
    out_docs.mkdir(exist_ok=True)

    # ── Learn: lessons with step pips and prev / next ──
    lessons = load_dir(DOCS / "learn")
    for i, L in enumerate(lessons):
        body, runnable = render(L["text"])
        pips = "".join(
            f'<a href="{x["slug"]}.html" class="{"on" if j <= i else ""}{" cur" if j == i else ""}" '
            f'title="{html.escape(x["title"])}">{j + 1:02d}</a>' for j, x in enumerate(lessons))
        top = f'<nav class="steps" aria-label="Lessons">{pips}</nav>'
        prev = (f'<li><a href="{lessons[i - 1]["slug"]}.html"><span>←</span>'
                f'<canvas data-px="{px_text(lessons[i - 1]["title"])}" data-scale="2"></canvas></a></li>'
                if i > 0 else "")
        nxt = (f'<li class="sel"><a href="{lessons[i + 1]["slug"]}.html">'
               f'<canvas data-px="NEXT: {px_text(lessons[i + 1]["title"])}" data-scale="2"></canvas><span>→</span></a></li>'
               if i + 1 < len(lessons) else
               f'<li class="sel"><a href="../docs/api.html"><canvas data-px="API REFERENCE" data-scale="2"></canvas><span>→</span></a></li>')
        bottom = f'<ul class="menu pager">{prev}{nxt}</ul>'
        doc = page(L["title"], f"LEARN {i + 1:02d}/{len(lessons):02d}", body, runnable, 1,
                   top, bottom, active="LEARN")
        (out_learn / f"{L['slug']}.html").write_text(doc.replace("VERSION", ver))
        if i == 0:
            (out_learn / "index.html").write_text(doc.replace("VERSION", ver))

    # ── Docs ──
    docs = load_dir(DOCS)
    for D in docs:
        body, runnable = render(D["text"])
        doc = page(D["title"], "DOCS", body, runnable, 1, active="DOCS")
        (out_docs / f"{D['slug']}.html").write_text(doc.replace("VERSION", ver))

    rows = [f'<li class="sel"><a href="../learn/"><canvas data-px="LEARN" data-scale="3"></canvas>'
            f'<span>MAKE YOUR FIRST GAME IN {len(lessons)} LESSONS →</span></a></li>']
    blurbs = {"api": "EVERY FUNCTION A GAME CAN CALL", "carts": "PROJECT FILES, THE CARD BUDGET, THE CART FORMAT",
              "build": "PARTS, PRINTING, WIRING AND PI SETUP"}
    for D in docs:
        rows.append(f'<li><a href="{D["slug"]}.html"><canvas data-px="{px_text(D["title"])}" data-scale="3"></canvas>'
                    f'<span>{blurbs.get(D["slug"], "")} →</span></a></li>')
    rows.append('<li><a href="https://github.com/JarodAlvarez/glyphbox/tree/main/devkit">'
                '<canvas data-px="DEVKIT" data-scale="3"></canvas><span>THE GLYPH COMMAND LINE TOOL →</span></a></li>')
    body = ('<h1 class="bar bar-title" aria-label="Docs"><canvas data-px="DOCS" data-scale="3"></canvas>'
            '<span class="mark" data-logo="mark"></span></h1>'
            '<p>Everything you need to make a GLYPHBOX game. New here? Start with the lessons: each example runs on the console beside it.</p>'
            f'<ul class="menu index">{"".join(rows)}</ul>')
    (out_docs / "index.html").write_text(page("Docs", "DOCS", body, False, 1, active="DOCS").replace("VERSION", ver))

    # Hand-written pages: point their ?v= tags at this build too
    for f in ["index.html", "play/index.html", "playground/index.html"]:
        p = SITE / f
        if p.exists():
            p.write_text(re.sub(r"\?v=(?:[0-9a-f]{8}|VERSION)", f"?v={ver}", p.read_text()))

    print(f"built {len(lessons)} lessons and {len(docs)} docs pages (v{ver})")


if __name__ == "__main__":
    main()
