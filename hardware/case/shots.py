"""Packaging / advertising product shots.

    .venv/bin/python shots.py      -> preview/shot_*.png
"""
import math
import os

import numpy as np
import shapely.affinity as sa
import trimesh

import glyphbox_case as G
import promo as P

COLORS = {            # body, controller shell, buttons
    'white': ((0.93, 0.93, 0.92), (0.95, 0.95, 0.94), (0.90, 0.90, 0.89)),
    'beige': ((0.84, 0.80, 0.72), (0.86, 0.82, 0.74), (0.80, 0.76, 0.68)),
    'black': ((0.13, 0.13, 0.14), (0.15, 0.15, 0.16), (0.11, 0.11, 0.12)),
    'yellow': ((0.93, 0.72, 0.20), (0.95, 0.75, 0.24), (0.88, 0.67, 0.17)),
    'blue': ((0.20, 0.32, 0.72), (0.23, 0.36, 0.76), (0.17, 0.28, 0.66)),
    'red': ((0.62, 0.13, 0.18), (0.66, 0.16, 0.21), (0.56, 0.11, 0.16)),
}
for name, (b, s, k) in COLORS.items():
    P.MAT['body_' + name] = (b, 0.10, 0)
    P.MAT['puck_' + name] = (s, 0.12, 0)
    P.MAT['btn_' + name] = (k, 0.18, 0)

BODY = G.build_body()


def moved(parts, off):
    out = []
    for m, mat in parts:
        m = m.copy(); m.apply_translation([off[0], off[1], 0]); out.append((m, mat))
    return out


def console(color, off=(0, 0), docked=True, card=True):
    mats = ('puck_' + color, 'btn_' + color)
    parts = [(BODY, 'body_' + color)] + P.screen_parts()
    if docked:
        parts += P.puck_parts(mats)
    if card:
        parts += P.card_parts()
    return moved(parts, off)


def loose_puck(color, pos, rot):
    out = []
    Rx = trimesh.transformations.rotation_matrix(math.radians(-90), [1, 0, 0])
    Rz = trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1])
    for m, mat in P.puck_parts(('puck_' + color, 'btn_' + color)):
        if mat == 'magnet':
            continue
        m = m.copy()
        m.apply_translation([0, -G.DOCK_DEPTH, -G.DOCK_Z])
        m.apply_transform(Rx); m.apply_transform(Rz)
        m.apply_translation([pos[0], pos[1], 0])
        out.append((m, mat))
    return out


def flat_card(pos, rot, label='HELLO'):
    """Game card lying face-up: kraft card, black label, white title."""
    c = G.box(-G.CARD_W / 2, G.CARD_W / 2, -G.CARD_L / 2, G.CARD_L / 2, 0, G.CARD_T)
    ink = G.box(-G.CARD_W / 2 + 4, G.CARD_W / 2 - 4, -G.CARD_L / 2 + 5, G.CARD_L / 2 - 12, G.CARD_T - 0.05, G.CARD_T + 0.08)
    t = sa.rotate(G.text_poly(label, 5.5), -90, origin=(0, 0))
    txt = trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, 0.08) for g in getattr(t, 'geoms', [t])])
    txt.apply_translation([-2, -4, G.CARD_T + 0.08])
    Rz = trimesh.transformations.rotation_matrix(math.radians(rot), [0, 0, 1])
    out = []
    for m, mat in ((c, 'card'), (ink, 'cardink'), (txt, 'lit')):
        m.apply_transform(Rz); m.apply_translation([pos[0], pos[1], 0]); out.append((m, mat))
    return out


def main():
    out = lambda n: os.path.join(P.OUT, n)
    R = P.render

    # 1. colour line-up
    P.BG = np.array([0.88, 0.88, 0.87])
    order = ['red', 'yellow', 'white', 'beige', 'blue', 'black']
    offs = [((i - 2.5) * 190, 110 if i % 2 else 0) for i in range(len(order))]
    scene = []
    for c, o in zip(order, offs):
        scene += console(c, o)
    R.consoles, R.extra_shadows, R.ground = offs, [], (1300, 700, 1100)
    R(scene, out('shot_lineup.png'), az=14, el=15, dist=2400, fov=28, width=2200, aspect=0.5,
      target=[0, 90, G.H / 2 - 15])

    # 2. hero: white console, controller and a card on the table in front
    P.BG = np.array([0.80, 0.81, 0.83])
    R.consoles, R.ground = [(0, 0)], (700, 500, 700)
    R.extra_shadows = [(-52, -88, 50, 26), (78, -70, 22, 34)]
    scene = console('white', docked=False, card=False) + loose_puck('white', (-52, -88), 14) + flat_card((78, -70), -20)
    R(scene, out('shot_hero_white.png'), az=-24, el=17, dist=1050, fov=19, width=1600, aspect=1.15,
      target=[5, 10, G.H / 2 - 28])

    # 3. controller close-up, docked
    R.extra_shadows = []
    P.BG = np.array([0.90, 0.89, 0.87])
    R.ground = (400, 200, 500)                 # keep the ground quad in front of the close camera
    R(console('beige'), out('shot_controller_detail.png'), az=32, el=20, dist=520, fov=22, width=1600, aspect=0.7,
      target=[0, 0, G.DOCK_Z + 6])

    # 4. straight-on front elevation for box art
    R.ground = (700, 500, 700)
    R(console('beige'), out('shot_front_flat.png'), az=0, el=0, dist=2600, fov=7.5, width=1400, aspect=1.5)
    P.BG = np.array([0.80, 0.81, 0.83])
    R(console('white'), out('shot_front_flat_white.png'), az=0, el=0, dist=2600, fov=7.5, width=1400, aspect=1.5)


if __name__ == '__main__':
    main()
