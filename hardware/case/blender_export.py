"""Export the case + stand-in components as per-material STLs for Blender.

    .venv/bin/python blender_export.py      -> render_assets/*.stl (mm)
"""
import math
import os

import trimesh

import glyphbox_case as G
import promo as P

OUT = os.path.join(G.HERE, 'render_assets')


def save(name, meshes):
    m = meshes if isinstance(meshes, trimesh.Trimesh) else trimesh.util.concatenate(meshes)
    m.export(os.path.join(OUT, name + '.stl'))
    print(f'{name:14s} {len(m.faces):7d} faces')


def usb_parts():
    """USB-A receptacle seen through the front opening: black surround, steel
    shell, tongue and four contacts."""
    x, z = G.USB_X, G.USB_Z
    nose = G.diff(G.box(x - G.USB_NOSE_W / 2 + 0.15, x + G.USB_NOSE_W / 2 - 0.15, 0.6, G.T + 2,
                        z - G.USB_NOSE_H / 2 + 0.15, z + G.USB_NOSE_H / 2 - 0.15),
                  [G.box(x - 6.55, x + 6.55, 0, 20, z - 2.85, z + 2.85)])
    shell = G.diff(G.box(x - 6.55, x + 6.55, 0.9, 14, z - 2.85, z + 2.85),
                   [G.box(x - 6.25, x + 6.25, 0, 13.5, z - 2.55, z + 2.55)])
    # two small retention windows on the top of the shell, as on real sockets
    tongue = G.box(x - 5.6, x + 5.6, 2.2, 13.6, z + 0.35, z + 2.25)
    back = G.box(x - 6.25, x + 6.25, 12.0, 13.6, z - 2.55, z + 2.55)
    pins = [G.box(x + px - 0.5, x + px + 0.5, 3.0, 10.5, z + 0.22, z + 0.37) for px in (-3.5, -1.0, 1.0, 3.5)]
    save('usb_nose', nose); save('usb_shell', shell)
    save('usb_tongue', [tongue, back]); save('usb_pins', pins)


def rear_parts():
    """Rear dressing: power jack in its opening and the screw heads."""
    D, T = G.D, G.T
    x, z = G.PWR_X, G.PWR_Z
    nose = G.diff(G.box(x - G.PWR_OPEN_W / 2 + 0.2, x + G.PWR_OPEN_W / 2 - 0.2, D - T - 3, D - 0.5,
                        z - G.PWR_OPEN_H / 2 + 0.2, z + G.PWR_OPEN_H / 2 - 0.2),
                  [G.box(x - 3.9, x + 3.9, D - 8, D + 1, z - 1.5, z + 1.5)])
    shell = G.diff(G.box(x - 3.9, x + 3.9, D - 7, D - 0.7, z - 1.5, z + 1.5),
                   [G.box(x - 3.65, x + 3.65, D - 6.5, D + 1, z - 1.25, z + 1.25)])
    inner = G.box(x - 3.0, x + 3.0, D - 6.5, D - 1.6, z - 0.9, z - 0.3)
    save('pwr_nose', [nose, inner]); save('pwr_shell', shell)
    heads = []
    for (hx, hz) in list(G.BOSS_XZ) + [(x + s * G.PWR_HOLE_SPACING / 2, z) for s in (-1, 1)]:
        h = G.cyl('y', hx, hz, 5.6, D - 0.05, D + 1.7)
        slot = [G.box(hx - 2.0, hx + 2.0, D + 0.9, D + 2, hz - 0.4, hz + 0.4),
                G.box(hx - 0.4, hx + 0.4, D + 0.9, D + 2, hz - 2.0, hz + 2.0)]
        heads.append(G.diff(h, slot))
    save('rear_screws', heads)


def main():
    os.makedirs(OUT, exist_ok=True)
    save('body', G.build_body())
    keep = G.SCREEN_GROOVE
    for v in ('ring', 'recess', 'face'):          # screen-surround options for comparison renders
        G.SCREEN_GROOVE = v
        save('body_' + v, G.build_body())
    G.SCREEN_GROOVE = keep
    save('panel', G.build_panel())
    scr = dict((mat, m) for m, mat in P.screen_parts())
    save('glass', scr['glass']); save('lit', scr['lit'])
    save('card', P.card_parts()[0][0])
    usb_parts()
    sy, sz = G.spk_centre()                       # dark speaker cone behind the grille
    save('speaker', G.cyl('x', sy, sz, G.SPK_DIA, -G.XI + 0.2, -G.XI + 3.0))
    rear_parts()
    puck = P.puck_parts(('puck', 'btn'))
    for m, mat in puck:
        if mat != 'magnet':
            save('puck_' + {'puck': 'shell', 'btn': 'btn', 'dark': 'port'}[mat], m)
    # same controller lying face-up, back on z=0, centred on the origin
    Rx = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    for m, mat in puck:
        if mat == 'magnet':
            continue
        m = m.copy()
        m.apply_translation([0, -G.DOCK_DEPTH, -G.DOCK_Z]); m.apply_transform(Rx)
        save('loose_' + {'puck': 'shell', 'btn': 'btn', 'dark': 'port'}[mat], m)
    with open(os.path.join(OUT, 'dims.txt'), 'w') as f:
        sy, sz = G.spk_centre()
        f.write(f'{G.W} {G.D} {G.H} {G.DOCK_Z} {G.USB_X} {G.USB_Z} {sy} {sz}\n')


if __name__ == '__main__':
    main()
