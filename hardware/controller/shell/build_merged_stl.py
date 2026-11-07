"""Build ready-to-print STLs of both shell halves.

The top shell comes out with the two reference brackets (D-pad and A/B
collars, ribs and all four membrane posts) already boolean-unioned in, so
there is nothing to import or Combine in Fusion.

Parameters are read straight out of build_controller_shell.py rather than
duplicated here, so this can't silently drift from the parametric model.
Run with a python that has trimesh + manifold3d + shapely installed.
"""
import math
import os
import re
import sys

import numpy as np
import shapely.geometry as sg
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
EXTRACTS = os.path.join(HERE, 'reference-extracts')
OUT = os.path.join(HERE, 'stl')

ARC_SEGMENTS = 256   # stadium arc resolution
CYL_SEGMENTS = 96


def load_params():
    """Exec the parameter section of the Fusion script, stubbing the adsk API."""
    src = open(os.path.join(HERE, 'build_controller_shell.py')).read()
    head = src.split('def stadium_profile_sketch')[0]
    head = head.replace('import adsk.core', '').replace('import adsk.fusion', '')
    head = re.sub(r'def pt\(.*?\n\n', 'def pt(*a, **k):\n    return None\n\n', head, flags=re.S)
    head = re.sub(r'def mmv\(.*?\n\n', 'def mmv(*a, **k):\n    return None\n\n', head, flags=re.S)
    ns = {}
    exec(head, ns)
    return ns


P = load_params()


def stadium(cx, cy, length, width):
    r = width / 2.0
    hs = (length - width) / 2.0
    pts = []
    for i in range(ARC_SEGMENTS + 1):          # right cap, -90 -> +90
        a = -math.pi / 2 + math.pi * i / ARC_SEGMENTS
        pts.append((cx + hs + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(ARC_SEGMENTS + 1):          # left cap, +90 -> +270
        a = math.pi / 2 + math.pi * i / ARC_SEGMENTS
        pts.append((cx - hs + r * math.cos(a), cy + r * math.sin(a)))
    return sg.Polygon(pts)


def cross(cx, cy, span, arm):
    hs, ha = span / 2.0, arm / 2.0
    return sg.Polygon([
        (cx + ha, cy + hs), (cx + ha, cy + ha), (cx + hs, cy + ha),
        (cx + hs, cy - ha), (cx + ha, cy - ha), (cx + ha, cy - hs),
        (cx - ha, cy - hs), (cx - ha, cy - ha), (cx - hs, cy - ha),
        (cx - hs, cy + ha), (cx - ha, cy + ha), (cx - ha, cy + hs),
    ])


def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, height=z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def cyl(cx, cy, dia, z0, z1):
    m = trimesh.creation.cylinder(radius=dia / 2.0, height=z1 - z0, sections=CYL_SEGMENTS)
    m.apply_translation([cx, cy, (z0 + z1) / 2.0])
    return m


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0])
    return m


def diff(a, b):
    return trimesh.boolean.difference([a, b], engine='manifold')


def union(a, b):
    return trimesh.boolean.union([a, b], engine='manifold')


EPS = 1.0   # overshoot so cuts break cleanly through faces


def build_top():
    cx, cy = P['PCB_CENTER_X'], P['PCB_CENTER_Y']
    top_outer, top_inner = P['TOP_OUTER_Z'], P['TOP_INNER_Z']

    m = prism(stadium(cx, cy, P['OUTER_LENGTH'], P['OUTER_WIDTH']), 0, top_outer)
    m = diff(m, prism(stadium(cx, cy, P['INNER_LENGTH'], P['INNER_WIDTH']), -EPS, top_inner))

    # D-pad cross + A/B button holes, straight through the ceiling
    m = diff(m, prism(cross(P['DPAD_CENTER'][0], P['DPAD_CENTER'][1],
                            P['DPAD_SPAN'] + P['DPAD_CUTOUT_CLEARANCE'],
                            P['DPAD_ARM_W'] + P['DPAD_CUTOUT_CLEARANCE']), -EPS, top_outer + EPS))
    for b in (P['BTN_A'], P['BTN_B']):
        m = diff(m, cyl(b[0], b[1], P['BTN_DIA'] + P['BUTTON_CUTOUT_CLEARANCE'],
                        -EPS, top_outer + EPS))

    # micro-USB notch through the +Y (top) end wall
    yw = cy + P['OUTER_WIDTH'] / 2.0
    m = diff(m, box(P['USB_CENTER_X'] - P['USB_WIDTH'] / 2.0,
                    P['USB_CENTER_X'] + P['USB_WIDTH'] / 2.0,
                    yw - P['WALL_T'] - EPS, yw + EPS,
                    P['USB_Z_BOTTOM'], P['USB_Z_TOP']))

    # ...and the outer counterbore that lets the plug's overmold sink in
    usb_mid_z = (P['USB_Z_BOTTOM'] + P['USB_Z_TOP']) / 2.0
    m = diff(m, box(P['USB_CENTER_X'] - P['USB_CB_WIDTH'] / 2.0,
                    P['USB_CENTER_X'] + P['USB_CB_WIDTH'] / 2.0,
                    yw - P['USB_CB_DEPTH'], yw + EPS,
                    usb_mid_z - P['USB_CB_HEIGHT'] / 2.0,
                    usb_mid_z + P['USB_CB_HEIGHT'] / 2.0))

    # M2.5 pilot bosses down onto the PCB
    for (hx, hy) in P['MOUNT_HOLES']:
        m = union(m, cyl(hx, hy, P['BOSS_OD'], P['PCB_THICKNESS'], top_inner))
    for (hx, hy) in P['MOUNT_HOLES']:
        m = diff(m, cyl(hx, hy, P['SCREW_PILOT_DIA'],
                        P['PCB_THICKNESS'] - EPS,
                        P['PCB_THICKNESS'] + P['SCREW_PILOT_DEPTH']))

    # Membrane mounts (D-pad and A/B collars, ribs and posts). They aren't
    # published: they're adapted from the Lensless GBP shell, whose licence
    # (CC BY-NC-ND) doesn't allow sharing adaptations. Make your own with
    # build_brackets.py from your own download; without them this builds
    # the bare top shell.
    names = ('dpad_bracket_positioned.stl', 'ab_bracket_positioned.stl')
    if all(os.path.exists(os.path.join(EXTRACTS, n)) for n in names):
        for name in names:
            m = union(m, trimesh.load(os.path.join(EXTRACTS, name)))
            print(f'  unioned {name}')
    else:
        print('  no reference-extracts/: building the top shell WITHOUT membrane mounts')
        print('  (run build_brackets.py on your own Lensless download first, see README.md)')
    return m


def build_bottom():
    cx, cy = P['PCB_CENTER_X'], P['PCB_CENTER_Y']
    floor_z = -(P['WALL_T'] + P['STANDOFF_H'])

    m = prism(stadium(cx, cy, P['OUTER_LENGTH'], P['OUTER_WIDTH']), floor_z, 0)
    m = diff(m, prism(stadium(cx, cy, P['INNER_LENGTH'], P['INNER_WIDTH']),
                      -P['STANDOFF_H'], EPS))

    for (hx, hy) in P['MOUNT_HOLES']:
        m = union(m, cyl(hx, hy, P['BOSS_OD'], -P['STANDOFF_H'], 0))

    # magnet backing boss, then the blind pocket from outside
    m = union(m, cyl(P['MAGNET_CENTER'][0], P['MAGNET_CENTER'][1], P['MAGNET_BOSS_DIA'],
                     -P['STANDOFF_H'], -P['STANDOFF_H'] + P['MAGNET_BOSS_H']))
    for (hx, hy) in P['MOUNT_HOLES']:
        m = diff(m, cyl(hx, hy, P['SCREW_CLEARANCE_DIA'], floor_z - EPS, EPS))
    m = diff(m, cyl(P['MAGNET_CENTER'][0], P['MAGNET_CENTER'][1], P['MAGNET_DIA'],
                    floor_z - EPS, floor_z + P['MAGNET_DEPTH']))
    return m


def report(name, m, expect_z=None):
    b = m.bounds
    ok = 'watertight' if m.is_watertight else '*** NOT WATERTIGHT ***'
    print(f'  {name}: {ok}  X[{b[0][0]:.2f},{b[1][0]:.2f}] '
          f'Y[{b[0][1]:.2f},{b[1][1]:.2f}] Z[{b[0][2]:.2f},{b[1][2]:.2f}]  '
          f'vol={m.volume/1000:.2f}cm3  bodies={m.body_count}')
    if expect_z is not None and abs(b[1][2] - expect_z) > 1e-6:
        print(f'    WARNING: expected max Z {expect_z}')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    print('params: TOP_OUTER_Z=%.3f  TOP_INNER_Z=%.3f  STANDOFF_H=%.2f'
          % (P['TOP_OUTER_Z'], P['TOP_INNER_Z'], P['STANDOFF_H']))

    print('\nTOP SHELL')
    top = build_top()
    report('top', top, expect_z=P['TOP_OUTER_Z'])
    top.export(os.path.join(OUT, 'glyphbox_top_shell.stl'))

    print('\nBOTTOM SHELL')
    bot = build_bottom()
    report('bottom', bot)
    bot.export(os.path.join(OUT, 'glyphbox_bottom_shell.stl'))

    # magnet pocket must be blind
    zc = -(P['WALL_T'] + P['STANDOFF_H']) + P['MAGNET_DEPTH'] + P['MAGNET_BACKING'] / 2.0
    solid = bot.contains(np.array([[P['MAGNET_CENTER'][0], P['MAGNET_CENTER'][1], zc]]))[0]
    print(f'\n  magnet backing present at Z={zc:.2f}: {solid}')

    print('\nwrote', OUT)
