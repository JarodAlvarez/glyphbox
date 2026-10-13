"""Studio-style product photography renders: seamless light backdrop, overhead
softbox lighting, soft grounded shadows, a faint floor reflection and glossy
screen glass.

    .venv/bin/python studio.py            # everything -> preview/studio_*.png
    .venv/bin/python studio.py test       # one quick hero only
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, map_coordinates
import trimesh

import glyphbox_case as G
import promo as P

OUT = os.path.join(G.HERE, 'preview')
SS = 2
BG = np.array([0.955, 0.955, 0.965])

COLORS = {            # body albedo
    'yellow': (0.97, 0.78, 0.22),
    'red': (0.80, 0.15, 0.18),
    'white': (0.93, 0.93, 0.92),
    'lilac': (0.74, 0.67, 0.89),
    'indigo': (0.25, 0.24, 0.56),
    'black': (0.10, 0.10, 0.11),
    'lime': (0.60, 0.83, 0.27),
}
# fixed materials: name -> (albedo, kind, specular)
MAT = {
    'glass': ((0.012, 0.012, 0.016), 'glass', 1.0), 'lit': ((1.0, 1.0, 0.98), 'lit', 0),
    'card': ((0.80, 0.63, 0.36), 'plastic', 0.02), 'cardink': ((0.05, 0.05, 0.05), 'plastic', 0.10),
    'dark': ((0.05, 0.05, 0.06), 'plastic', 0.2), 'magnet': ((0.70, 0.70, 0.73), 'plastic', 0.8),
    'screw': ((0.55, 0.55, 0.58), 'plastic', 0.7), 'engrave': ((0.5, 0.5, 0.5), 'plastic', 0),
}


def set_color(tag, rgb):
    c = np.array(rgb)
    dark = c.mean() < 0.3
    MAT['body' + tag] = (tuple(c), 'plastic', 0.30 if dark else 0.16)
    MAT['puck' + tag] = (tuple(np.clip(c * 1.03 + 0.012, 0, 1)), 'plastic', 0.34 if dark else 0.18)
    MAT['btn' + tag] = (tuple(np.clip(c * 0.94, 0, 1)), 'plastic', 0.40 if dark else 0.24)


# --------------------------------------------------------------------------- scene helpers
BODY = None
_NORMALS = {}


def console(tag='', off=(0, 0), docked=True, card=True):
    """List of (mesh, material, xy offset). Meshes are shared between instances."""
    global BODY
    if BODY is None:
        BODY = G.build_body()
    key = ('console', docked, card)
    if key not in _NORMALS:
        parts = [(BODY, 'body')] + P.screen_parts()
        # USB socket stand-in so the opening is not a see-through hole
        parts.append((G.box(G.USB_X - G.USB_NOSE_W / 2, G.USB_X + G.USB_NOSE_W / 2, 1.2, G.T + 2,
                            G.USB_Z - G.USB_NOSE_H / 2, G.USB_Z + G.USB_NOSE_H / 2), 'dark'))
        if docked:
            parts += P.puck_parts(('puck', 'btn'))
        if card:
            parts += P.card_parts()
        _NORMALS[key] = parts
    out = []
    for m, mat in _NORMALS[key]:
        out.append((m, mat + tag if mat in ('body', 'puck', 'btn') else mat, off))
    return out


def corner_normals(m):
    k = id(m)
    if k not in _NORMALS:
        _NORMALS[k] = P.corner_normals(m).astype(np.float32)
    return _NORMALS[k]


class Camera:
    def __init__(self, az, el, dist, fov, width, aspect, target):
        self.Wp, self.Hp = width * SS, int(width * aspect) * SS
        a, e = math.radians(az), math.radians(el)
        self.fwd = np.array([-math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
        self.right = np.cross(self.fwd, [0, 0, 1]); self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.fwd)
        self.eye = np.array(target, float) - self.fwd * dist
        self.f = (self.Wp / 2) / math.tan(math.radians(fov) / 2)


def raster(scene, cam, mats, mirror=False):
    """Z-buffer rasterise. With mirror=True the scene is reflected in the floor
    (z -> -z) but the buffers store the real-world position and normal."""
    Wp, Hp, f = cam.Wp, cam.Hp, cam.f
    mid = {k: i + 1 for i, k in enumerate(mats)}
    zbuf = np.full((Hp, Wp), 1e9, np.float32)
    nbuf = np.zeros((Hp, Wp, 3), np.float32); pbuf = np.zeros((Hp, Wp, 3), np.float32)
    mbuf = np.zeros((Hp, Wp), np.int16)
    flip = np.array([1, 1, -1.0])
    for m, mat, off in scene:
        tri = m.triangles + np.array([off[0], off[1], 0.0])
        cn = corner_normals(m)
        vis = tri * flip if mirror else tri
        rel = vis - cam.eye
        depth = rel @ cam.fwd
        sx = Wp / 2 + f * (rel @ cam.right) / depth
        sy = Hp / 2 - f * (rel @ cam.up) / depth
        x0s = np.clip(np.floor(sx.min(1)), 0, Wp - 1).astype(int); x1s = np.clip(np.ceil(sx.max(1)), 0, Wp - 1).astype(int)
        y0s = np.clip(np.floor(sy.min(1)), 0, Hp - 1).astype(int); y1s = np.clip(np.ceil(sy.max(1)), 0, Hp - 1).astype(int)
        ok = (depth.min(1) > 1) & (sx.max(1) >= 0) & (sx.min(1) < Wp) & (sy.max(1) >= 0) & (sy.min(1) < Hp)
        for i in np.nonzero(ok)[0]:
            px_, py_ = sx[i], sy[i]
            x0, x1, y0, y1 = x0s[i], x1s[i], y0s[i], y1s[i]
            d = (py_[1] - py_[2]) * (px_[0] - px_[2]) + (px_[2] - px_[1]) * (py_[0] - py_[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            wa = ((py_[1] - py_[2]) * (gx - px_[2]) + (px_[2] - px_[1]) * (gy - py_[2])) / d
            wb = ((py_[2] - py_[0]) * (gx - px_[2]) + (px_[0] - px_[2]) * (gy - py_[2])) / d
            wc = 1 - wa - wb
            ia, ib, ic = wa / depth[i, 0], wb / depth[i, 1], wc / depth[i, 2]
            s = ia + ib + ic
            z = 1.0 / np.where(s > 1e-12, s, 1)
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            hit = (wa >= -1e-6) & (wb >= -1e-6) & (wc >= -1e-6) & (z < sub)
            if not hit.any():
                continue
            ia, ib, ic = (ia * z)[hit], (ib * z)[hit], (ic * z)[hit]
            sub[hit] = z[hit]
            mbuf[y0:y1 + 1, x0:x1 + 1][hit] = mid[mat]
            nbuf[y0:y1 + 1, x0:x1 + 1][hit] = ia[:, None] * cn[i, 0] + ib[:, None] * cn[i, 1] + ic[:, None] * cn[i, 2]
            pbuf[y0:y1 + 1, x0:x1 + 1][hit] = ia[:, None] * tri[i, 0] + ib[:, None] * tri[i, 1] + ic[:, None] * tri[i, 2]
    return zbuf, nbuf, pbuf, mbuf


def floor_shadow(scene, light, res=1.5):
    """Footprint of the scene projected along the light onto z=0, as a blurred
    occlusion texture. Returns (texture, x0, y0, res)."""
    pts = np.vstack([m.bounds + np.array([o[0], o[1], 0.0]) for m, _, o in scene])
    x0, y0 = pts[:, 0].min() - 260, pts[:, 1].min() - 260
    x1, y1 = pts[:, 0].max() + 260, pts[:, 1].max() + 260
    w, h = int((x1 - x0) / res), int((y1 - y0) / res)
    img = Image.new('L', (w, h), 0)
    dr = ImageDraw.Draw(img)
    for m, _, o in scene:
        v = m.vertices + np.array([o[0], o[1], 0.0])
        g = v[:, :2] - light[:2] * (v[:, 2:3] / light[2])
        g = (g - [x0, y0]) / res
        for fidx in m.faces:
            dr.polygon([tuple(g[k]) for k in fidx], fill=255)
    occ = np.asarray(img, np.float32) / 255
    tex = 0.26 * gaussian_filter(occ, 4.0 / res) + 0.22 * gaussian_filter(occ, 18.0 / res) \
        + 0.18 * gaussian_filter(occ, 60.0 / res)
    return tex, x0, y0, res


def wrap(x, w):
    return np.clip((x + w) / (1 + w), 0, 1)


def shade(cam, eye, nbuf, pbuf, mbuf, ao, mats):
    """Soft overhead-softbox look. Returns an RGB image (unlit where mbuf==0)."""
    Hp, Wp = mbuf.shape
    n = nbuf / np.maximum(np.linalg.norm(nbuf, axis=2, keepdims=True), 1e-9)
    v = eye - pbuf; v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-9)
    n = np.where((n * v).sum(2, keepdims=True) < 0, -n, n)
    zup = np.array([0, 0, 1.0])
    key = -0.45 * cam.right - 0.35 * cam.fwd + 0.95 * zup; key /= np.linalg.norm(key)
    fill = 0.80 * cam.right - 0.45 * cam.fwd + 0.25 * zup; fill /= np.linalg.norm(fill)
    nk, nf = (n * key).sum(2), (n * fill).sum(2)
    ncam = -(n * cam.fwd).sum(2)
    diffuse = 0.30 * (0.80 + 0.20 * n[..., 2]) + 0.36 * wrap(nk, 0.45) + 0.34 * wrap(ncam, 0.3) \
        + 0.14 * wrap(nf, 0.6)
    nv = np.clip((n * v).sum(2), 0, 1)
    hk = v + key; hk /= np.maximum(np.linalg.norm(hk, axis=2, keepdims=True), 1e-9)
    hf = v + fill; hf /= np.maximum(np.linalg.norm(hf, axis=2, keepdims=True), 1e-9)
    spec = 0.75 * np.clip((n * hk).sum(2), 0, 1) ** 22 + 0.30 * np.clip((n * hf).sum(2), 0, 1) ** 10
    rim = (1 - nv) ** 4
    refl = 2 * nv[..., None] * n - v                      # for the glass
    img = np.zeros((Hp, Wp, 3), np.float32)
    for i, (name, (rgb, kind, ks)) in enumerate(mats.items()):
        mk = mbuf == i + 1
        if not mk.any():
            continue
        rgb = np.array(rgb)
        if kind == 'lit':
            img[mk] = rgb
        elif kind == 'glass':
            r = refl[mk]
            sheen = 0.20 * np.clip(r @ key, 0, 1) ** 3 + 0.10 * np.clip(r[:, 2], 0, 1) ** 2
            q = pbuf[mk].astype(np.float64) @ (cam.right + 0.8 * zup)
            band = np.clip(0.5 + 0.012 * (q - q.mean()), 0, 1)
            img[mk] = rgb + (sheen + 0.055 * band ** 2 + 0.25 * (1 - nv[mk]) ** 5)[:, None]
        else:
            col = rgb[None, :] * (diffuse[mk] * ao[mk])[:, None]
            img[mk] = col + (ks * (spec[mk] * ao[mk] + 0.45 * rim[mk]))[:, None]
    return img


def render(scene, path_fn, variants, az=26, el=9, dist=1000, fov=18.5, width=1500, aspect=1.25, target=None):
    """Rasterise once, then shade + composite once per colour variant.
    variants: list of (name, fn) where fn() mutates MAT for that variant."""
    cam = Camera(az, el, dist, fov, width, aspect, target if target is not None else [0, G.D / 2, G.H / 2 - 12])
    Wp, Hp = cam.Wp, cam.Hp
    variants[0][1]()
    mats = dict(MAT)
    zb, nb, pb, mb = raster(scene, cam, mats)
    zr, nr, pr, mr = raster(scene, cam, mats, mirror=True)

    # floor under every pixel's ray
    xs, ys = np.meshgrid(np.arange(Wp) + 0.5, np.arange(Hp) + 0.5)
    dirs = cam.fwd[None, None, :] + ((xs - Wp / 2) / cam.f)[..., None] * cam.right - ((ys - Hp / 2) / cam.f)[..., None] * cam.up
    dz = dirs[..., 2]
    t = np.where(dz < -1e-6, -cam.eye[2] / np.minimum(dz, -1e-6), 1e9)
    floor = cam.eye[None, None, :2] + t[..., None] * dirs[..., :2]
    on_floor = (mb == 0) & (dz < -1e-6)

    light = np.array([-0.04, -0.06, 1.0])
    tex, tx0, ty0, res = floor_shadow(scene, light)
    u, w_ = (floor[..., 0] - tx0) / res, (floor[..., 1] - ty0) / res
    shadow = map_coordinates(tex, [w_.clip(0, tex.shape[0] - 1), u.clip(0, tex.shape[1] - 1)], order=1, mode='nearest')
    shadow[(u < 0) | (w_ < 0) | (u > tex.shape[1] - 1) | (w_ > tex.shape[0] - 1)] = 0

    # ambient occlusion from the depth buffer (floor included, so the base grounds itself)
    zl = np.where(mb > 0, zb, np.where(on_floor, t, zb[mb > 0].max())).astype(np.float32)
    zl = np.minimum(zl, zb[mb > 0].max() + 400)
    ao = np.ones((Hp, Wp), np.float32)
    for sig, k in ((2.5 * SS, 0.11), (8 * SS, 0.05), (24 * SS, 0.022)):
        ao -= np.clip((zl - gaussian_filter(zl, sig)) * k, 0, 0.34)
    ao = gaussian_filter(np.clip(ao, 0.40, 1), SS * 0.8)

    vy = np.linspace(0, 1, Hp)[:, None]
    backdrop = BG[None, None, :] * (1.0 - 0.035 * vy ** 2)[..., None] * np.ones((Hp, Wp, 1))
    eye_m = cam.eye * np.array([1, 1, -1.0])
    for name, fn in variants:
        fn()
        mats = dict(MAT)
        obj = shade(cam, cam.eye, nb, pb, mb, ao, mats)
        ref = shade(cam, eye_m, nr, pr, mr, np.ones_like(ao), mats)
        img = backdrop.copy()
        img[on_floor] *= (1 - np.clip(shadow[on_floor], 0, 0.80))[:, None]
        # floor reflection: fades with height above the floor, softened
        k = np.where((mr > 0) & on_floor, 0.15 * np.exp(-np.abs(pr[..., 2]) / 55.0), 0).astype(np.float32)
        k = gaussian_filter(k, 1.5 * SS)
        refb = np.dstack([gaussian_filter(ref[..., c], 1.6 * SS) for c in range(3)])
        img = img * (1 - k[..., None]) + refb * k[..., None]
        hit = mb > 0
        img[hit] = obj[hit]
        img = np.clip(img, 0, 1)
        img = img * img * (3 - 2 * img) * 0.25 + img * 0.75          # gentle contrast curve
        im = Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((Wp // SS, Hp // SS), Image.LANCZOS)
        im.save(path_fn(name))
        print('wrote', path_fn(name), flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    names = list(COLORS)
    test = 'test' in sys.argv

    # per-colour hero
    todo = names[:1] if test else names
    render(console(), lambda n: os.path.join(OUT, f'studio_hero_{n}.png'),
           [(n, (lambda n=n: set_color('', COLORS[n]))) for n in todo])
    if test:
        return

    def all_colors():
        for i, n in enumerate(names):
            set_color(f'#{i}', COLORS[n])

    # straight-on line-up of all seven
    scene = []
    for i in range(len(names)):
        scene += console(f'#{i}', ((i - 3) * 176.0, 0))
    render(scene, lambda n: os.path.join(OUT, 'studio_lineup_front.png'), [('all', all_colors)],
           az=0, el=5, dist=3400, fov=22.5, width=2600, aspect=0.34, target=[0, G.D / 2, G.H / 2 - 18])

    # receding diagonal line-up
    scene = []
    for i in range(len(names)):
        scene += console(f'#{i}', (i * 128.0, i * 104.0))
    render(scene, lambda n: os.path.join(OUT, 'studio_lineup_fan.png'), [('all', all_colors)],
           az=-27, el=9, dist=2300, fov=24, width=2400, aspect=0.6, target=[360, 300, G.H / 2 - 15])

    # controller out of the dock, two colours
    loose = []
    Rx = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    Rz = trimesh.transformations.rotation_matrix(math.radians(12), [0, 0, 1])
    for m, mat in P.puck_parts(('puck', 'btn')):
        if mat == 'magnet':
            continue
        m = m.copy()
        m.apply_translation([0, -G.DOCK_DEPTH, -G.DOCK_Z]); m.apply_transform(Rx); m.apply_transform(Rz)
        loose.append((m, mat, (-48, -92)))
    render(console(docked=False) + loose, lambda n: os.path.join(OUT, f'studio_undocked_{n}.png'),
           [(n, (lambda n=n: set_color('', COLORS[n]))) for n in ('lilac', 'lime', 'black')],
           az=-22, el=13, dist=1100, fov=18, width=1600, aspect=1.1, target=[0, 0, G.H / 2 - 30])


if __name__ == '__main__':
    main()
