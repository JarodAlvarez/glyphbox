"""Promotional-style renders (soft studio lighting, smooth shading, ground
shadow) of the case with a detailed controller stand-in.

    .venv/bin/python promo.py      -> preview/promo_*.png
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import shapely.affinity as sa
import shapely.geometry as sg
import trimesh

import glyphbox_case as G

OUT = os.path.join(G.HERE, 'preview')
SS = 2
BG = np.array([0.93, 0.925, 0.91])

# name -> (rgb, specular, emissive)
MAT = {
    'body': ((0.84, 0.80, 0.72), 0.10, 0), 'puck': ((0.86, 0.82, 0.74), 0.12, 0),
    'btn': ((0.80, 0.76, 0.68), 0.18, 0), 'glass': ((0.02, 0.02, 0.025), 0.9, 0),
    'lit': ((1.0, 1.0, 0.97), 0.0, 1), 'card': ((0.80, 0.63, 0.34), 0.03, 0),
    'cardink': ((0.06, 0.06, 0.06), 0.05, 0), 'magnet': ((0.75, 0.75, 0.78), 0.6, 0),
    'screw': ((0.55, 0.55, 0.58), 0.7, 0), 'dark': ((0.08, 0.08, 0.09), 0.3, 0),
    'engrave': ((0.5, 0.5, 0.5), 0.0, 0),
    'ground': ((1, 1, 1), 0, 0),
}


# --------------------------------------------------------------------------- models
def puck_parts(mats=('puck', 'btn')):
    """Controller stand-in modelled on the real shell: rounded front edge,
    D-pad in a cross-shaped opening, two round buttons, micro-USB on the top
    edge. Docked pose: back at y=DOCK_DEPTH, face toward -y."""
    L, Wd, Tk = G.PUCK_L, G.PUCK_W, G.PUCK_T
    yb, yf = G.DOCK_DEPTH, G.DOCK_DEPTH - Tk
    z = G.DOCK_Z

    def ring(inset, y):
        s = G.stadium(0, z, L - 2 * inset, Wd - 2 * inset)
        return [(x, y, zz) for x, zz in s.exterior.coords]
    pts = []
    rf = 1.2                                                 # small edge round: the real face is flat
    for a in np.linspace(0, math.pi / 2, 7):
        pts += ring(rf * (1 - math.cos(a)), yf + rf * (1 - math.sin(a)))
    for a in np.linspace(0, math.pi / 2, 5):                 # 1.5 mm back fillet
        pts += ring(1.5 * (1 - math.cos(a)), yb - 1.5 * (1 - math.sin(a)))
    body = trimesh.convex.convex_hull(np.array(pts))
    dx, bx, ax = -26.4, 22.5, 36.3            # D-pad / B / A centres from the KiCad layout
    cross = sg.box(dx - 11.2, z - 3.6, dx + 11.2, z + 3.6).union(sg.box(dx - 3.6, z - 11.2, dx + 3.6, z + 11.2))
    cross = cross.buffer(-0.8).buffer(0.8, quad_segs=8)
    seam_y = yb - 5.5
    body = G.diff(body, [G.prism_xz(cross.buffer(0.7, quad_segs=8), yf - 1, yf + 1.6),
                         G.cyl('y', bx, z, 11.4, yf - 1, yf + 1.4),
                         G.cyl('y', ax, z, 11.4, yf - 1, yf + 1.4),
                         G.box(-6.5, 6.5, seam_y - 4.2, seam_y + 0.2, z + Wd / 2 - 2.5, z + Wd / 2 + 1),
                         G.diff(G.box(-80, 80, seam_y - 0.25, seam_y + 0.25, z - 40, z + 40),
                                [G.prism_xz(G.stadium(0, z, L - 0.9, Wd - 0.9), yf, yb)])])
    pad = G.union([G.prism_xz(cross, yf - 1.2, yf + 1.6), G.prism_xz(cross.buffer(-0.5), yf - 1.7, yf - 1.1)])
    marks = [G.cyl('y', dx, z, 3.2, yf - 2.0, yf - 1.4)]
    for k in range(4):                                       # arrow on each arm
        tri = sa.rotate(sg.Polygon([(dx - 1.3, z + 7.2), (dx + 1.3, z + 7.2), (dx, z + 9.2)]), 90 * k, origin=(dx, z))
        marks.append(G.prism_xz(tri, yf - 2.0, yf - 1.45))
    btns = [G.diff(pad, marks)]
    for cx in (bx, ax):
        r = [(cx + rr * math.cos(a), y, z + rr * math.sin(a))
             for (rr, y) in ((5.3, yf + 1.4), (5.3, yf - 1.6), (5.0, yf - 2.1), (4.3, yf - 2.3))
             for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]
        btns.append(trimesh.convex.convex_hull(np.array(r)))
    port = G.box(-4, 4, seam_y - 3.2, seam_y - 0.6, z + Wd / 2 - 3.5, z + Wd / 2 - 2.4)
    mag = G.cyl('y', 0, z, G.MAG_DIA, yb - 0.1, yb + G.PUCK_MAG_PROUD)
    return [(body, mats[0]), (trimesh.util.concatenate(btns), mats[1]), (port, 'dark'), (mag, 'magnet')]


def screen_parts():
    y0 = G.DY()
    glass = G.box(-G.DISP_W / 2, G.DISP_W / 2, y0, y0 + 2, G.DISP_BOTTOM_Z, G.DISP_BOTTOM_Z + G.DISP_H)
    u, cap = 2.2, 4.2                          # official stacked lock-up
    text, tw = G.wordmark(cap)
    z0 = G.DISP_ZC - (11 * u + 4.0 + cap) / 2
    polys = G.mark_polys(-4.5 * u, z0 + cap + 4.0, u) + [sa.translate(text, -tw / 2, z0)]
    lit = [G.prism_xz(g, y0 - 0.3, y0 + 0.1) for p in polys for g in getattr(p, 'geoms', [p]) if g.area > 0.005]
    return [(glass, 'glass'), (trimesh.util.concatenate(lit), 'lit')]


def card_parts(y_shift=0.0):
    c = G.box(-G.CARD_W / 2, G.CARD_W / 2, -G.CARD_PROTRUDE - G.FRAME_PROUD, G.CARD_END - 0.2,
              G.CARD_Z, G.CARD_Z + G.CARD_T)
    c.apply_translation([0, y_shift, 0])
    return [(c, 'card')]


def rear_parts():
    """Rear panel with screw heads and the power jack nose."""
    D, T = G.D, G.T
    heads = [G.cyl('y', x, z, 5.6, D - 0.1, D + 1.8) for (x, z) in G.BOSS_XZ]
    heads += [G.cyl('y', G.PWR_X + s * G.PWR_HOLE_SPACING / 2, G.PWR_Z, 5.6, D - 0.1, D + 1.8) for s in (-1, 1)]
    jack = G.box(G.PWR_X - G.PWR_OPEN_W / 2 + 0.3, G.PWR_X + G.PWR_OPEN_W / 2 - 0.3, D - T - 4, D - 0.8,
                 G.PWR_Z - G.PWR_OPEN_H / 2 + 0.3, G.PWR_Z + G.PWR_OPEN_H / 2 - 0.3)
    ink = trimesh.util.concatenate([G.prism_xz(g, D - G.REAR_ENGRAVE_DEPTH - 0.05, D - G.REAR_ENGRAVE_DEPTH + 0.05)
                                    for g in G.rear_engraving()])
    return [(G.build_panel(), 'body'), (trimesh.util.concatenate(heads), 'screw'), (jack, 'dark'),
            (ink, 'engrave')]


# --------------------------------------------------------------------------- renderer
def corner_normals(m, angle=35):
    """Per-face-corner normals, smoothed only across edges below `angle`."""
    fn, fa = m.face_normals, m.area_faces
    vf = m.vertex_faces                         # (V, K) padded with -1
    out = np.zeros((len(m.faces), 3, 3))
    cosang = math.cos(math.radians(angle))
    for c in range(3):
        nb = vf[m.faces[:, c]]                  # (F, K)
        for k in range(nb.shape[1]):
            j = nb[:, k]
            ok = j >= 0
            if not ok.any():
                break
            nn = fn[j]
            w = ok & ((nn * fn).sum(1) > cosang)
            out[:, c] += nn * (fa[j] * w)[:, None]
    ln = np.linalg.norm(out, axis=2, keepdims=True)
    return np.where(ln > 1e-12, out / np.maximum(ln, 1e-12), fn[:, None, :])


def render(parts, path, az=28, el=14, dist=900, fov=18, width=1400, aspect=1.25, target=None):
    MID = {k: i + 1 for i, k in enumerate(MAT)}
    Wp, Hp = width * SS, int(width * aspect) * SS
    target = np.array(target if target is not None else [0, G.D / 2, G.H / 2 - 8])
    a, e = math.radians(az), math.radians(el)
    fwd = np.array([-math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    eye = target - fwd * dist
    f = (Wp / 2) / math.tan(math.radians(fov) / 2)

    gx_, gy0_, gy1_ = getattr(render, 'ground', (700, 500, 700))
    ground = trimesh.Trimesh(vertices=[[-gx_, -gy0_, 0], [gx_, -gy0_, 0], [gx_, gy1_, 0], [-gx_, gy1_, 0]],
                             faces=[[0, 1, 2], [0, 2, 3]])
    zbuf = np.full((Hp, Wp), 1e9); nbuf = np.zeros((Hp, Wp, 3)); pbuf = np.zeros((Hp, Wp, 3))
    mbuf = np.zeros((Hp, Wp), np.int32)
    for m, mat in parts + [(ground, 'ground')]:
        tri = m.triangles
        cn = corner_normals(m) if mat != 'ground' else np.tile([0, 0, 1.0], (len(tri), 3, 1))
        rel = tri - eye
        depth = rel @ fwd
        sx = Wp / 2 + f * (rel @ right) / depth
        sy = Hp / 2 - f * (rel @ up) / depth
        for i in range(len(tri)):
            if (depth[i] < 1).any():
                continue
            px_, py_ = sx[i], sy[i]
            x0, x1 = int(max(px_.min(), 0)), int(min(px_.max() + 1, Wp - 1))
            y0, y1 = int(max(py_.min(), 0)), int(min(py_.max() + 1, Hp - 1))
            if x1 < x0 or y1 < y0:
                continue
            d = (py_[1] - py_[2]) * (px_[0] - px_[2]) + (px_[2] - px_[1]) * (py_[0] - py_[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            wa = ((py_[1] - py_[2]) * (gx - px_[2]) + (px_[2] - px_[1]) * (gy - py_[2])) / d
            wb = ((py_[2] - py_[0]) * (gx - px_[2]) + (px_[0] - px_[2]) * (gy - py_[2])) / d
            wc = 1 - wa - wb
            # perspective-correct weights
            ia, ib, ic = wa / depth[i, 0], wb / depth[i, 1], wc / depth[i, 2]
            s = ia + ib + ic
            z = 1.0 / np.where(s > 1e-12, s, 1)
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            hit = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6) & (z < sub)
            if not hit.any():
                continue
            ia, ib, ic = (ia * z)[hit], (ib * z)[hit], (ic * z)[hit]
            sub[hit] = z[hit]
            mbuf[y0:y1 + 1, x0:x1 + 1][hit] = MID[mat]
            nbuf[y0:y1 + 1, x0:x1 + 1][hit] = ia[:, None] * cn[i, 0] + ib[:, None] * cn[i, 1] + ic[:, None] * cn[i, 2]
            pbuf[y0:y1 + 1, x0:x1 + 1][hit] = ia[:, None] * tri[i, 0] + ib[:, None] * tri[i, 1] + ic[:, None] * tri[i, 2]

    # ---- shading
    n = nbuf / np.maximum(np.linalg.norm(nbuf, axis=2, keepdims=True), 1e-9)
    view = eye - pbuf; view /= np.maximum(np.linalg.norm(view, axis=2, keepdims=True), 1e-9)
    n = np.where((n * view).sum(2, keepdims=True) < 0, -n, n)
    # lights follow the camera so every angle is lit the same way
    lights = [(-0.60 * right + 0.55 * up - 0.60 * fwd, 0.78), (0.80 * right + 0.25 * up - 0.50 * fwd, 0.30),
              (np.array([0.0, 0.0, 1.0]) - 0.2 * fwd, 0.22)]
    diffuse = np.full((Hp, Wp), 0.30); spec = np.zeros((Hp, Wp))
    for i, (l, k) in enumerate(lights):
        l = l / np.linalg.norm(l)
        nl = (n * l).sum(2)
        diffuse += k * np.clip(nl * 0.75 + 0.25, 0, 1) ** 1.3
        if i < 2:
            h = view + l; h /= np.maximum(np.linalg.norm(h, axis=2, keepdims=True), 1e-9)
            spec += k * np.clip((n * h).sum(2), 0, 1) ** 40
    # screen-space AO from depth
    zl = np.where(mbuf > 0, zbuf, zbuf[mbuf > 0].max())
    ao = np.ones((Hp, Wp))
    for sig, k in ((3 * SS, 0.10), (9 * SS, 0.05), (25 * SS, 0.02)):
        ao -= np.clip((zl - gaussian_filter(zl, sig)) * k, 0, 0.35)
    ao = gaussian_filter(np.clip(ao, 0.45, 1), SS)

    img = np.zeros((Hp, Wp, 3)) + BG
    for name, (rgb, ks, em) in MAT.items():
        mk = mbuf == MID[name]
        if not mk.any() or name == 'ground':
            continue
        if em:
            img[mk] = rgb
        else:
            img[mk] = (np.array(rgb)[None, :] * (diffuse[mk] * ao[mk])[:, None] + (ks * spec[mk])[:, None])
    # ground: soft contact shadow from the case footprint, light from front-left
    g = mbuf == MID['ground']
    gx, gy = pbuf[..., 0], pbuf[..., 1]
    def sdf(cx, cy, hx, hy):
        qx, qy = np.abs(gx - cx) - hx, np.abs(gy - cy) - hy
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    sh = np.zeros((Hp, Wp))
    for (ox, oy) in getattr(render, 'consoles', [(0, 0)]):
        sh += 0.42 * np.exp(-sdf(ox + 8, oy + G.D / 2 + 8, G.W / 2 - 6, G.D / 2 - 4) / 28.0) \
            + 0.30 * np.exp(-sdf(ox, oy + G.D / 2, G.W / 2 - 4, G.D / 2 - 4) / 5.0)
    for (cx, cy, hx, hy) in getattr(render, 'extra_shadows', []):
        sh += 0.35 * np.exp(-sdf(cx, cy, hx, hy) / 9.0)
    vign = 1 - 0.10 * (np.hypot(*np.meshgrid(np.linspace(-1, 1, Wp), np.linspace(-1, 1, Hp))) ** 2)
    img[g] = BG * (1 - np.clip(sh[g], 0, 0.7))[:, None]
    img[mbuf == 0] = BG
    img *= vign[..., None]
    img = np.clip(img, 0, 1) ** (1 / 1.15)
    im = Image.fromarray((img * 255).astype(np.uint8)).resize((Wp // SS, Hp // SS), Image.LANCZOS)
    im.save(path)
    print('wrote', path)


COLORWAYS = {'beige': ((0.84, 0.80, 0.72), (0.86, 0.82, 0.74), (0.80, 0.76, 0.68)),
             'white': ((0.93, 0.93, 0.92), (0.95, 0.95, 0.94), (0.90, 0.90, 0.89))}


def main(color='beige'):
    os.makedirs(OUT, exist_ok=True)
    for k, rgb in zip(('body', 'puck', 'btn'), COLORWAYS[color]):
        MAT[k] = (rgb,) + MAT[k][1:]
    global BG
    if color == 'white':
        BG = np.array([0.80, 0.81, 0.83])
    sfx = '' if color == 'beige' else '_' + color
    MAT['engrave'] = (tuple(0.72 * c for c in MAT['body'][0]), 0.0, 0)
    only = sys.argv[2] if len(sys.argv) > 2 else None
    body = [(G.build_body(), 'body')]
    scene = body + screen_parts() + puck_parts() + card_parts()
    if only == 'rear':
        full = scene + rear_parts()
        render(full, os.path.join(OUT, 'promo_rear' + sfx + '.png'), az=180, el=4, aspect=1.45)
        render(full, os.path.join(OUT, 'promo_rear_right' + sfx + '.png'), az=208, el=14)
        return
    render.extra_shadows = []
    render(scene, os.path.join(OUT, 'promo_hero' + sfx + '.png'), az=27, el=13)
    render(scene, os.path.join(OUT, 'promo_front' + sfx + '.png'), az=-18, el=6, aspect=1.3)

    full = scene + rear_parts()
    render(full, os.path.join(OUT, 'promo_rear_left' + sfx + '.png'), az=152, el=14)
    render(full, os.path.join(OUT, 'promo_rear_right' + sfx + '.png'), az=208, el=14)
    render(full, os.path.join(OUT, 'promo_rear' + sfx + '.png'), az=180, el=4, aspect=1.45)
    render(full, os.path.join(OUT, 'promo_side' + sfx + '.png'), az=80, el=8, aspect=1.3)

    # controller undocked, lying face-up in front of the console
    loose = []
    Rx = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    Rz = trimesh.transformations.rotation_matrix(math.radians(-18), [0, 0, 1])
    for m, mat in puck_parts():
        if mat == 'magnet':
            continue
        m = m.copy()
        m.apply_translation([0, -G.DOCK_DEPTH, -G.DOCK_Z])   # back face on y=0, centred
        m.apply_transform(Rx)                                 # face up, back on z=0
        m.apply_transform(Rz)
        m.apply_translation([55, -85, 0])
        loose.append((m, mat))
    render.extra_shadows = [(57, -83, 50, 26)]
    render(body + screen_parts() + card_parts(-40) + loose, os.path.join(OUT, 'promo_undocked' + sfx + '.png'),
           az=30, el=22, dist=1050, target=[15, 20, G.H / 2 - 25], aspect=1.1)


if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else 'beige')
