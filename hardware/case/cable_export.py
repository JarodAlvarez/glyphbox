"""Render-only props for the 'plugged in' shot: coiled USB cable, both plugs,
and the dock magnet. Positions in mm, console frame (see glyphbox_case.py).

    .venv/bin/python cable_export.py      -> render_assets/{cable,plug_a,plug_micro,dock_magnet}.stl
"""
import math

import numpy as np
import trimesh

import glyphbox_case as G
from blender_export import save

LOOSE = (20.0, -100.0, -10.0)          # controller placement used by the Blender shot (mm, mm, deg)
WIRE_R, COIL_R, PITCH = 1.5, 3.6, 3.4  # cable radius, coil radius, coil pitch


def catmull(pts, n):
    pts = np.asarray(pts, float)
    P = np.vstack([pts[0] * 2 - pts[1], pts, pts[-1] * 2 - pts[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1:i + 3]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return np.array(out)


def resample(path, step):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    return np.column_stack([np.interp(t, s, path[:, k]) for k in range(3)]), t, s[-1]


def frames(path):
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.zeros_like(T)
    a = np.cross(T[0], [0, 0, 1.0])
    N[0] = a / np.linalg.norm(a)
    for i in range(1, len(T)):                 # parallel transport
        v = N[i - 1] - T[i] * (N[i - 1] @ T[i])
        N[i] = v / np.linalg.norm(v)
    return T, N, np.cross(T, N)


def tube(path, r, sides=14):
    T, N, B = frames(path)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    rings = path[:, None, :] + r * (np.cos(ang)[None, :, None] * N[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    V = rings.reshape(-1, 3)
    F = []
    for i in range(len(path) - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            c, d = a + sides, b + sides
            F += [[a, c, b], [b, c, d]]
    m = trimesh.Trimesh(V, F)
    caps = [trimesh.creation.icosphere(2, r).apply_translation(p) for p in (path[0], path[-1])]
    return trimesh.util.concatenate([m] + caps)


def main():
    lx, ly, rot = LOOSE
    th = math.radians(rot)
    u = np.array([-math.sin(th), math.cos(th), 0.0])            # controller's "up" edge, pointing at the console
    port = np.array([lx, ly, 0.0]) + 31.2 * u + [0, 0, 7.4]

    # micro-USB plug: 11 x 6.5 overmould, 17 mm long, sticking out of the controller's top edge
    pm = trimesh.creation.box(extents=[11, 17, 6.5])
    pm.apply_translation([0, 8.5 + 0.5, 0])
    pm.apply_transform(trimesh.transformations.rotation_matrix(th, [0, 0, 1]))
    pm.apply_translation(port)
    save('plug_micro', pm)
    m_end = port + 18 * u

    # USB-A plug in the front socket: 15.5 x 7.5 overmould, 24 mm long, front of it 21 mm proud
    ax, az = G.USB_X, G.USB_Z
    pa = trimesh.creation.box(extents=[15.5, 24, 7.5])
    pa.apply_translation([ax, 3 - 12, az])
    save('plug_a', pa)
    a_end = np.array([ax, -22.0, az])

    # cable centreline: lazy S on the table between controller and console
    ctrl = [m_end, m_end + 6 * u + [0, 0, -1.5], [5, -34, 5.2], [-12, -47, 5.2], [-30, -50, 5.2],
            [-40, -40, 6.5], [ax, -30, 11], a_end]
    path = catmull(ctrl, 30)
    path, s, L = resample(path, 0.25)
    lead = 9.0                                    # straight leads at each end, coiled in between
    w = np.clip(np.minimum(s - lead, L - lead - s) / 6.0, 0, 1)
    T, N, B = frames(path)
    phase = 2 * math.pi * s / PITCH
    coil = path + (COIL_R * w)[:, None] * (np.cos(phase)[:, None] * N + np.sin(phase)[:, None] * B)
    coil[:, 2] = np.maximum(coil[:, 2], WIRE_R)   # never below the table
    save('cable', tube(coil, WIRE_R))

    # case magnet showing in the dock dimple
    save('dock_magnet', G.cyl('y', 0, G.DOCK_Z, G.MAG_DIA, G.MAG_DIMPLE_Y - 2.0, G.MAG_DIMPLE_Y))
    print('cable length along path %.0f mm' % L)


if __name__ == '__main__':
    main()
