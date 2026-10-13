"""Render PNG previews of the parametric console case.

Loads the exact geometry from build_console_stl.py (same single PARAMS
source of truth) and rasterizes front / rear / side / oblique / exploded /
ghosted-front views with matplotlib.

ORIENTATION: the model frame is X = width, Y = height (y=0 is the floor,
y=200 the top), Z = depth (z=0 is the FRONT panel outer face, rear wall at
z=100). matplotlib's elevation/azimuth camera can't look straight down the Z
axis (except top-down), so each view rotates the MODEL into a friendly
frame first -- front and rear views apply R90 about Y (front face lands in
the X-Y plane), side views leave the model as-is with the camera on the
+X/-X axis. Axis limits are then derived from the rotated bounds, so views
always frame the model regardless of rotation.

    .venv/bin/python preview_case.py

Outputs PNGs in preview/:
    view_front.png  (FRONT / REAR / SIDE / OBLIQUE in one sheet)
    view_exploded.png
    view_ghosted_front.png
"""
import math
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

from build_console_stl import P, build_front, build_rear, proxies

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'preview')
os.makedirs(OUT, exist_ok=True)

MAX_FACES = 30000

# Fixed light direction (normalized), used for all views
LIGHT = np.array([0.35, 0.45, 0.85])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT = 0.42

PALETTE = {
    'front_shell': (0.82, 0.83, 0.87),
    'rear_shell': (0.72, 0.73, 0.79),
    'display': (0.35, 0.55, 0.86),
    'camera': (0.42, 0.42, 0.46),
    'camera_lens': (0.20, 0.20, 0.22),
    'pi': (0.24, 0.63, 0.24),
    'card': (0.78, 0.67, 0.24),
    'puck_top': (0.67, 0.47, 0.78),
    'puck_bottom': (0.58, 0.40, 0.69),
}


def rot_y(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def tri_and_color(mesh, color):
    v = mesh.vertices
    f = mesh.faces
    if len(f) > MAX_FACES:
        f = f[::len(f) // MAX_FACES]
    tri = v[f]
    fin = np.all(np.isfinite(tri), axis=(1, 2))
    tri = tri[fin]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    lens = np.linalg.norm(n, axis=1)
    good = np.isfinite(lens) & (lens > 1e-9)
    tri, n, lens = tri[good], n[good], lens[good]
    n = n / lens[:, None]
    bright = AMBIENT + (1.0 - AMBIENT) * np.clip(n @ LIGHT, 0.0, 1.0)
    rgb = np.array(color) * bright[:, None]
    fc = np.concatenate([rgb, np.ones((len(tri), 1))], axis=1)
    c = tri.mean(axis=1)
    return tri, fc, c


def set_camera(ax, elev, azim, bounds):
    ax.set_facecolor((0.086, 0.086, 0.086))
    ax.view_init(elev=elev, azim=azim)
    mins, maxs = bounds
    pad = 0.06 * (maxs - mins)
    ax.set_xlim(mins[0] - pad[0], maxs[0] + pad[0])
    ax.set_ylim(mins[1] - pad[1], maxs[1] + pad[1])
    ax.set_zlim(mins[2] - pad[2], maxs[2] + pad[2])
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()


def draw_parts(ax, parts, elev, azim, alpha_map=None):
    """Draw parts far-to-near for the current camera direction."""
    # mpl camera direction: at azim=0/elev=0 the camera sits on +X and looks
    # back at the origin; azim rotates it around Z, elev lifts it above the
    # XY plane. This must match matplotlib's own convention or the painter's
    # depth sort disagrees with the projection (front panel stops occluding).
    e = math.radians(elev)
    r = math.radians(azim)
    cam = np.array([math.cos(e) * math.cos(r),
                    math.cos(e) * math.sin(r),
                    math.sin(e)])
    cam = cam / np.linalg.norm(cam)

    painted = []
    for name, mesh in parts.items():
        color = PALETTE.get(name, (0.8, 0.8, 0.8))
        alpha = (alpha_map or {}).get(name, 1.0)
        tri, fc, cent = tri_and_color(mesh, color)
        painted.append((cent @ cam, tri, fc, alpha))
    painted.sort(key=lambda x: float(x[0].max()))     # far first

    items = []
    for depth, tri, fc, alpha in painted:             # noqa: B007
        if alpha < 1.0:
            fc = fc.copy()
            fc[:, 3] = alpha
        items.append(Poly3DCollection(tri, facecolors=fc, edgecolors='none'))
    for poly in items:
        ax.add_collection3d(poly)


def rotate_parts(parts, R):
    if R is None:
        return parts
    out = {}
    for name, mesh in parts.items():
        m = mesh.copy()
        verts = np.asarray(m.vertices)
        m.vertices = verts @ R.T
        out[name] = m
    return out


def parts_bounds(parts):
    lo = np.array([np.inf] * 3)
    hi = np.array([-np.inf] * 3)
    for m in parts.values():
        lo = np.minimum(lo, m.bounds[0])
        hi = np.maximum(hi, m.bounds[1])
    return (lo, hi)


def make_figure():
    fig = plt.figure(figsize=(18, 12))
    fig.patch.set_facecolor('#141414')
    return fig


def core_parts():
    front = build_front()
    rear = build_rear()
    proxy = proxies()
    parts = {
        'rear_shell': rear,
        'front_shell': front,
        'display': proxy['display'],
        'camera': proxy['camera'],
        'camera_lens': proxy['camera_lens'],
        'pi': proxy['pi'],
        'card': proxy['card'],
    }
    if 'puck_top' in proxy:
        parts['puck_top'] = proxy['puck_top']
        parts['puck_bottom'] = proxy['puck_bottom']
    return parts


def scene(parts, elev, azim, R=None, alpha_map=None, title=None):
    fig = make_figure()
    ax = fig.add_subplot(111, projection='3d')
    rotated = rotate_parts(parts, R)
    bounds = parts_bounds(rotated)
    set_camera(ax, elev, azim, bounds)
    draw_parts(ax, rotated, elev, azim, alpha_map)
    if title:
        ax.set_title(title, color='#dddddd', fontsize=14)
    return fig


def render_front():
    parts = core_parts()
    R90 = rot_y(90.0)        # front face (z=0) -> x=0 plane, camera on +X

    fig = make_figure()
    # After rotY(+90) the front face (z=0) lands at x'=0 with its exterior
    # facing -x', so FRONT looks from -x (azim=180) and REAR from +x (azim=0).
    views = [
        (231, parts, 6, 180, R90, 'FRONT'),
        (232, parts, 6, 0, R90, 'REAR'),
        (233, parts, 6, 180, None, 'SIDE (left wall)'),
        (234, parts, 24, -65, R90, 'OBLIQUE'),
    ]
    for (idx, p, elev, azim, R, label) in views:
        ax = fig.add_subplot(idx, projection='3d')
        rotated = rotate_parts(p, R)
        bounds = parts_bounds(rotated)
        set_camera(ax, elev, azim, bounds)
        draw_parts(ax, rotated, elev, azim)
        ax.set_title(label, color='#dddddd', fontsize=13)
    fig.savefig(os.path.join(OUT, 'view_front.png'), dpi=110)
    plt.close(fig)
    print('wrote preview/view_front.png (FRONT/REAR/SIDE/OBLIQUE)')


def render_exploded():
    parts = core_parts()
    parts['front_shell'] = parts['front_shell'].copy().apply_translation([0, 0, -45])
    parts['rear_shell'] = parts['rear_shell'].copy().apply_translation([0, 0, 55])
    fig = scene(parts, 18, -55, R=rot_y(90.0), title='EXPLODED')
    fig.savefig(os.path.join(OUT, 'view_exploded.png'), dpi=110)
    plt.close(fig)
    print('wrote preview/view_exploded.png')


def render_ghosted():
    parts = core_parts()
    fig = scene(parts, 14, -25, R=rot_y(90.0),
                alpha_map={'front_shell': 0.25, 'rear_shell': 0.30},
                title='X-RAY VIEW - internals through the ghosted shells')
    fig.savefig(os.path.join(OUT, 'view_ghosted_front.png'), dpi=110)
    plt.close(fig)
    print('wrote preview/view_ghosted_front.png')


if __name__ == '__main__':
    render_front()
    render_exploded()
    render_ghosted()