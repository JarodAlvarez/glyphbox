"""Inline the rendered preview PNGs into preview/index.html as data URIs.

The thread preview server serves a single HTML file only (no sibling
assets), so the images are base64-embedded to make the page self-contained.

    .venv/bin/python build_preview_html.py
"""
import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PREVIEW = os.path.join(HERE, 'preview')
OUT = os.path.join(PREVIEW, 'index.html')

SECTIONS = [
    ('view_front.png',
     'Front / rear / side / oblique',
     'Front, rear, side and oblique views'),
    ('view_exploded.png',
     'Exploded - panel pulled away, internals between',
     'Exploded view'),
    ('view_ghosted_front.png',
     'Ghosted front - internals through translucent shells',
     'Ghosted internal view'),
]


def data_uri(name):
    with open(os.path.join(PREVIEW, name), 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()


rows = []
for name, caption, alt in SECTIONS:
    rows.append(f'''  <div class="row">
    <div class="caption">{caption}</div>
    <img src="{data_uri(name)}" alt="{alt}">
  </div>''')

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>GLYPHBOX Console Case - Parametric Preview</title>
<style>
  body {{ margin:0; padding:24px; background:#141414; color:#e8e8e8;
         font-family:-apple-system, "SF Mono", Consolas, monospace; }}
  h1 {{ font-size:15px; letter-spacing:.2em; color:#3ef57a; text-transform:uppercase; }}
  p  {{ font-size:12px; color:#999; max-width:1000px; line-height:1.6; }}
  img {{ width:100%; max-width:1000px; border:1px solid #2a2a2a; border-radius:6px;
        display:block; background:#000; }}
  .row {{ margin:28px auto; }}
  .caption {{ font-size:11px; color:#777; letter-spacing:.1em; margin:8px 0 4px; text-transform:uppercase; }}
</style>
</head>
<body>
  <h1>GLYPHBOX Console Case - parametric preview</h1>
  <p>Rendered straight from the PARAMS in <code>hardware/case/build_console_case.py</code>.
  Estimates are the fabrication brief's target envelope (150x200x100 mm, 3 mm walls) plus
  measured component specs - the cardboard measurements from <code>measures.md</code> will
  update every number. Colors: light gray = shells, blue = OSOOYOO display, gray = IMX708
  camera, green = Pi 4B, amber = game card, purple = the <em>actual fabricated controller
  shells</em> docked in the front recess.</p>
{chr(10).join(rows)}
</body>
</html>'''

with open(OUT, 'w') as f:
    f.write(page)
print(f'wrote {OUT} ({len(page) // 1024} KB, images inlined)')