"""Software-rendered PNG previews of the case (no GPU / viewer needed).

    .venv/bin/python render.py      -> preview/*.png
"""
import math
import os

import numpy as np
from PIL import Image
import trimesh

import glyphbox_case as G

OUT = os.path.join(G.HERE, 'preview')
SS = 2                                   # supersampling
LIGHT = np.array([-0.35, 0.55, 0.75]); LIGHT /= np.linalg.norm(LIGHT)

COL = {
    'body': (0.86, 0.83, 0.76), 'panel': (0.78, 0.75, 0.68), 'clip': (0.95, 0.55, 0.15),
    'display': (0.05, 0.05, 0.06), 'hdmi_plug': (0.25, 0.25, 0.28), 'pi': (0.15, 0.55, 0.25),
    'pi_hdmi_plug': (0.25, 0.25, 0.28), 'pi_csi': (1.0, 0.25, 0.2), 'speaker': (0.75, 0.75, 0.78), 'audio_plug': (0.85, 0.7, 0.2), 'pi_usb_plugs': (0.35, 0.35, 0.40),
    'camera': (0.10, 0.45, 0.30), 'card': (0.80, 0.62, 0.30), 'puck': (0.97, 0.97, 0.97),
    'power_jack': (0.2, 0.2, 0.22), 'usb_socket': (0.2, 0.2, 0.22),
}


def view_matrix(az, el):
    """Camera orbiting the model: az=0 looks at the front, +az swings to the
    viewer's right; el raises the camera."""
    a, e = math.radians(az), math.radians(el)
    fwd = np.array([-math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return np.array([right, up, -fwd])       # rows: screen x, screen y, toward camera


def render(meshes, az, el, path, width=900, clip=None):
    """meshes: list of (trimesh, rgb). clip: (axis, sign, value) half-space cut."""
    Rm = view_matrix(az, el)
    tris, cols = [], []
    for m, c in meshes:
        if clip is not None:
            ax, sgn, val = clip
            lo, hi = [-999.0] * 3, [999.0] * 3
            (lo if sgn > 0 else hi)[ax] = val
            m = trimesh.boolean.intersection(
                [m, G.box(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])], engine='manifold')
            if len(m.faces) == 0:
                continue
        t = m.triangles @ Rm.T
        tris.append(t); cols.append(np.tile(c, (len(t), 1)))
    tris = np.vstack(tris); cols = np.vstack(cols)
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    scale = (width * SS - 40 * SS) / (hi[0] - lo[0])
    Wp = width * SS
    Hp = int((hi[1] - lo[1]) * scale) + 40 * SS
    xy = (tris[:, :, :2] - lo[:2]) * scale + 20 * SS
    xy[:, :, 1] = Hp - xy[:, :, 1]
    zz = tris[:, :, 2]
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1); ok = ln > 1e-9
    nrm[ok] /= ln[ok, None]
    lv = Rm @ LIGHT
    shade = 0.35 + 0.65 * np.abs(nrm @ lv)
    zbuf = np.full((Hp, Wp), -1e9); img = np.ones((Hp, Wp, 3)); nb = np.zeros((Hp, Wp, 3))
    for i in np.nonzero(ok)[0]:
        p = xy[i]
        x0, x1 = int(max(p[:, 0].min(), 0)), int(min(p[:, 0].max() + 1, Wp - 1))
        y0, y1 = int(max(p[:, 1].min(), 0)), int(min(p[:, 1].max() + 1, Hp - 1))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
        if abs(d) < 1e-9:
            continue
        a = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
        b = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
        c = 1 - a - b
        z = a * zz[i, 0] + b * zz[i, 1] + c * zz[i, 2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        hit = (a >= -1e-6) & (b >= -1e-6) & (c >= -1e-6) & (z > sub)
        sub[hit] = z[hit]
        img[y0:y1 + 1, x0:x1 + 1][hit] = cols[i] * shade[i]
        nb[y0:y1 + 1, x0:x1 + 1][hit] = nrm[i]
    # outline: depth / normal discontinuities
    edge = np.zeros((Hp, Wp), bool)
    for ax in (0, 1):
        dz = np.abs(np.diff(np.clip(zbuf, -1e4, None), axis=ax))
        dn = np.linalg.norm(np.diff(nb, axis=ax), axis=2)
        e = (dz > 0.4) | (dn > 0.5)
        if ax == 0:
            edge[:-1] |= e
        else:
            edge[:, :-1] |= e
    img[edge] *= 0.45
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    im.resize((Wp // SS, Hp // SS), Image.LANCZOS).save(path)
    print('wrote', path)


def main():
    os.makedirs(OUT, exist_ok=True)
    body, panel = G.build_body(), G.build_panel()
    px = G.proxies()
    comp = [(m, COL[k]) for k, m in px.items()]
    clips = [(c, COL['clip']) for c in G.placed_clips()]
    shell = [(body, COL['body'])]
    if G.FRONT_STYLE == 'faceplate':
        shell = shell + [(G.build_faceplate(), (0.07, 0.07, 0.08))]
    front = shell + [(px[k], COL[k]) for k in ('display', 'puck', 'card')]
    render(front, 28, 18, os.path.join(OUT, 'hero.png'))
    render(shell + [(px['display'], COL['display'])], 0, 0, os.path.join(OUT, 'front_empty_dock.png'), width=700)
    render(shell + comp + clips, 205, 20, os.path.join(OUT, 'rear_open.png'))
    render(shell + [(panel, COL['panel']), (px['power_jack'], COL['power_jack'])], 205, 20,
           os.path.join(OUT, 'rear_closed.png'))
    render(shell + comp + clips + [(panel, COL['panel'])], 90, 0,
           os.path.join(OUT, 'section_side.png'), clip=(0, -1, 0.0))
    render(shell + clips, 180, 0, os.path.join(OUT, 'rear_inside_bare.png'), width=700)
    render(shell + clips + [(px[k], COL[k]) for k in ('speaker', 'pi', 'pi_csi', 'audio_plug', 'camera', 'power_jack')],
           150, 22, os.path.join(OUT, 'speaker_inside.png'))
    pi = [(px[k], COL[k]) for k in ('pi', 'pi_csi', 'camera')]
    render(shell + pi + [(px['pi_usb_plugs'], COL['pi_usb_plugs']), (px['pi_hdmi_plug'], COL['pi_hdmi_plug'])], 210, 25, os.path.join(OUT, 'pi_orientation.png'))


def styles():
    """One sheet per front style: three angles side by side."""
    os.makedirs(OUT, exist_ok=True)
    for st in ('scoop', 'frame', 'grille'):
        G.FRONT_STYLE = st
        body, px = G.build_body(), G.proxies()
        ms = [(body, COL['body'])] + [(px[k], COL[k]) for k in ('display', 'puck', 'card')]
        tiles = []
        for i, (az, el) in enumerate(((28, 18), (0, 0), (-40, 8))):
            p = os.path.join(OUT, f'_tmp{i}.png')
            render(ms, az, el, p, width=620)
            tiles.append(Image.open(p).copy()); os.remove(p)
        hh = max(t.height for t in tiles)
        sheet = Image.new('RGB', (sum(t.width for t in tiles), hh), 'white')
        x = 0
        for t in tiles:
            sheet.paste(t, (x, (hh - t.height) // 2)); x += t.width
        sheet.save(os.path.join(OUT, f'style_{st}.png'))
        print('wrote style', st)


if __name__ == '__main__':
    import sys
    styles() if 'styles' in sys.argv else main()
