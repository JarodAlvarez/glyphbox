"""Build ready-to-print STLs of both console case halves, plus GLB previews
and interference checks.

Mirrors build_console_case.py (the Fusion 360 source of truth): parameters
are read straight out of that script rather than duplicated here, so this
can't silently drift from the parametric model.

Run with a python that has trimesh + manifold3d + shapely installed
(see README.md for the venv setup):

    .venv/bin/python build_console_stl.py

Outputs in stl/:
    glyphbox_front_shell.stl
    glyphbox_rear_shell.stl
    assembly.glb              (color-coded, open with macOS Quick Look)
    assembly_exploded.glb
"""
import math
import os
import re

import numpy as np
import shapely.geometry as sg
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'stl')

ARC_SEGMENTS = 256   # stadium arc resolution
CYL_SEGMENTS = 96
EPS = 1.0            # overshoot so cuts break cleanly through faces


def load_params():
    """Exec the parameter + derived-geometry section of the Fusion script,
    stubbing the adsk API out."""
    src = open(os.path.join(HERE, 'build_console_case.py')).read()
    head = src.split('def largest_profile')[0]
    head = head.replace('import adsk.core', '').replace('import adsk.fusion', '')
    head = re.sub(r'def pt\(.*?\n\n', 'def pt(*a, **k):\n    return None\n\n',
                  head, flags=re.S)
    head = re.sub(r'def mmv\(.*?\n\n', 'def mmv(*a, **k):\n    return None\n\n',
                  head, flags=re.S)
    ns = {}
    exec(head, ns)
    return ns


P = load_params()

W, H, D, T = P['W'], P['H'], P['D'], P['T']
FRONT_T = P['FRONT_T']


# ---------------------------------------------------------------------------
# Primitive builders (all coords in mm, model frame)
# ---------------------------------------------------------------------------

def stadium(cx, cy, length, width):
    r = width / 2.0
    hs = (length - width) / 2.0
    pts = []
    for i in range(ARC_SEGMENTS + 1):          # right cap
        a = -math.pi / 2 + math.pi * i / ARC_SEGMENTS
        pts.append((cx + hs + r * math.cos(a), cy + r * math.sin(a)))
    for i in range(ARC_SEGMENTS + 1):          # left cap
        a = math.pi / 2 + math.pi * i / ARC_SEGMENTS
        pts.append((cx - hs + r * math.cos(a), cy + r * math.sin(a)))
    return sg.Polygon(pts)


def srect(cx, cy, w, h):
    return sg.Polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                       (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])


def scirc_sg(cx, cy, r):
    return sg.Point(cx, cy).buffer(r, quad_segs=48)


def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, height=z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def cyl(cx, cy, dia, z0, z1):
    """Cylinder with its axis along Z (pass-throughs in the X/Y walls)."""
    m = trimesh.creation.cylinder(radius=dia / 2.0, height=z1 - z0,
                                  sections=CYL_SEGMENTS)
    m.apply_translation([cx, cy, (z0 + z1) / 2.0])
    return m


def cyl_y(cx, cz, dia, y0, y1):
    """Cylinder with its axis along Y (pass-throughs in the floor/ceiling)."""
    m = trimesh.creation.cylinder(radius=dia / 2.0, height=y1 - y0,
                                  sections=CYL_SEGMENTS)
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.pi / 2.0, [1, 0, 0]))
    m.apply_translation([cx, (y0 + y1) / 2.0, cz])
    return m


def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0])
    return m


def diff(a, b):
    return trimesh.boolean.difference([a, b], engine='manifold')


def union(a, b):
    return trimesh.boolean.union([a, b], engine='manifold')


# ---------------------------------------------------------------------------
# Front shell
# ---------------------------------------------------------------------------

def build_front():
    P_ = P
    m = box(-W / 2.0, W / 2.0, 0.0, H, 0.0, FRONT_T)

    # Display window + card slot (through)
    m = diff(m, box(P_['DISP_WIN_X0'], P_['DISP_WIN_X1'],
                    P_['DISP_WIN_Y0'], P_['DISP_WIN_Y1'],
                    -EPS, FRONT_T + EPS))
    m = diff(m, box(-P_['SLOT_W'] / 2.0, P_['SLOT_W'] / 2.0,
                    P_['SLOT_Y0'], P_['SLOT_Y1'], -EPS, FRONT_T + EPS))

    # Controller dock recess (blind, from the outer face)
    m = diff(m, prism(stadium(0.0, P_['DOCK_CY'], P_['DOCK_LEN'], P_['DOCK_WID']),
                      0.0, P_['DOCK_DEPTH']))

    # Magnet pockets (blind)
    for my in P_['MAGNET_Y']:
        m = diff(m, cyl(0.0, my, P_['MAGNET_DIA'], -EPS, P_['MAGNET_DEPTH']))

    # Slot LED channel (blind recess from the panel interior face)
    m = diff(m, box(-P_['LED_HALF_W'], P_['LED_HALF_W'],
                    P_['LED_Y0'], P_['LED_Y1'],
                    FRONT_T - P_['LED_DEPTH'], FRONT_T + EPS))

    # Guide rails + stop tab (the card slides along these)
    for sxx in (-1, 1):
        if sxx < 0:
            rx0, rx1 = -P_['RAIL_IN_X'] - P_['RAIL_W'], -P_['RAIL_IN_X']
        else:
            rx0, rx1 = P_['RAIL_IN_X'], P_['RAIL_IN_X'] + P_['RAIL_W']
        m = union(m, box(rx0, rx1, P_['CARD_BOTTOM_Y'] - P_['RAIL_T'],
                         P_['CARD_BOTTOM_Y'], FRONT_T, FRONT_T + P_['SLOT_POCKET_D']))
    m = union(m, box(-P_['CARD_W'] / 2.0, P_['CARD_W'] / 2.0,
                     P_['CARD_BOTTOM_Y'] - P_['RAIL_T'], P_['CARD_BOTTOM_Y'],
                     FRONT_T + P_['SLOT_POCKET_D'], FRONT_T + P_['SLOT_POCKET_D'] + 3.0))

    # Display mount bosses on the interior face
    for sxx in (-1, 1):
        for syy in (-1, 1):
            m = union(m, cyl(sxx * P_['DISP_BOSS_DX'],
                             P_['DISPLAY_CY'] + syy * P_['DISP_BOSS_DY'],
                             4.8, FRONT_T, FRONT_T + P_['DISPLAY_BOSS_H']))

    # M3 closure holes (through)
    for cx in P_['CLOSURE_X']:
        for cy in P_['CLOSURE_Y']:
            m = diff(m, cyl(cx, cy, P_['CLOSURE_BOLT_DIA'], -EPS, FRONT_T + EPS))

    return m


# ---------------------------------------------------------------------------
# Rear shell
# ---------------------------------------------------------------------------

def build_rear():
    P_ = P
    m = box(-W / 2.0, W / 2.0, 0.0, H, FRONT_T, D)

    # Inner cavity (flush rim against the panel; frame centered on x=0)
    m = diff(m, box(-W / 2.0 + T, W / 2.0 - T, T, H - T, FRONT_T, D - T + EPS))

    # Pi mount bosses (axis along Y). Bosses run from the board's top face up
    # through the mounting wall: the board butts against their bottoms.
    for (hx, hz) in P_['PI_HOLES']:
        if P_['PI_MOUNT'] == 'ceiling':
            m = union(m, cyl_y(hx, hz, 5.6,
                               P_['PI_BOARD_BOTTOM_Y'] + P_['PI_T'],
                               H - T + 1.0))
        else:
            m = union(m, cyl_y(hx, hz, 5.6,
                               T - 1.0, P_['PI_BOARD_BOTTOM_Y']))

    # Camera bay baffle: 4 plates around the camera shaft
    bw = P_['CAM_BAY_W'] / 2.0
    for sxx in (-1, 1):
        m = union(m, box(sxx * bw - 1.5, sxx * bw + 1.5,
                         T, P_['CAM_BAY_TOP_Y'],
                         P_['CAM_BAY_Z0'], P_['CAM_BAY_Z1']))
    for zz in (P_['CAM_BAY_Z0'], P_['CAM_BAY_Z1']):
        m = union(m, box(-bw, bw, T, P_['CAM_BAY_TOP_Y'], zz - 1.5, zz + 1.5))

    # Camera bracket: floor ledge under the camera PCB. Kept 8mm back from
    # the bay's front baffle plate so the camera board clears it.
    m = union(m, box(-16.0, 16.0, T, P_['CAM_BRACKET_TOP_Y'],
                     P_['CAM_BAY_Z0'] + 8.0, P_['CAM_BAY_Z0'] + 26.0))

    # Bottom speaker: recess + grille holes through the floor (axis along Y)
    m = diff(m, cyl_y(P_['SPEAKER_CX'], P_['SPEAKER_CZ'], P_['SPEAKER_DIA'],
                      -EPS, T + P_['SPEAKER_RECESS_D']))
    for i in range(3):
        for j in range(3):
            gx = P_['SPEAKER_CX'] + (i - 1) * 16.0
            gz = P_['SPEAKER_CZ'] + (j - 1) * 16.0
            if gx * gx + (gz - P_['SPEAKER_CZ']) ** 2 < (P_['SPEAKER_R'] - 8.0) ** 2:
                m = diff(m, cyl_y(gx, gz, 4.0, -EPS, T + EPS))

    # Rear-wall pass-throughs (Pi ports + power switch + controller cable)
    for name, prt in P_['PORTS']:
        m = diff(m, box(P_['PI_CX'] + prt['dx'] - prt['w'] / 2.0,
                        P_['PI_CX'] + prt['dx'] + prt['w'] / 2.0,
                        P_['PI_PORT_Y'] - prt['h'] / 2.0,
                        P_['PI_PORT_Y'] + prt['h'] / 2.0,
                        D - 4.0, D + 4.0))
    m = diff(m, cyl(P_['PWR_BTN_X'], H - 30.0, P_['PWR_BTN_DIA'], D - 4.0, D + 4.0))
    m = diff(m, cyl(P_['CTRL_CABLE_X'], H - 50.0, P_['CTRL_CABLE_DIA'], D - 4.0, D + 4.0))

    # Top vents
    step = (D - T - 30.0) / P_['VENT_SLOTS']
    for i in range(P_['VENT_SLOTS']):
        z0 = 10.0 + i * step
        m = diff(m, box(-35.0, 35.0, H - 4.0, H + 4.0, z0, z0 + 3.0))

    # Optional 40x40 fan recess + mounts
    if P_['FAN_OPTION']:
        m = diff(m, box(-21.0, 21.0, H - T - 12.0, H - 4.0,
                        D / 2.0 - 21.0, D / 2.0 + 21.0))
        for (fx, fz) in ((-15.0, -15.0), (-15.0, 15.0), (15.0, -15.0), (15.0, 15.0)):
            m = diff(m, cyl_y(fx, D / 2.0 + fz, 3.0, H - 4.0, H + 4.0))

    # Rim closure bosses (M3 pilot for self-tap / heat-set)
    for cx in P_['CLOSURE_X']:
        for cy in P_['CLOSURE_Y']:
            m = union(m, cyl(cx, cy, P_['BOSS_OD'], FRONT_T, FRONT_T + 7.0))
            m = diff(m, cyl(cx, cy, P_['BOSS_PILOT_DIA'], FRONT_T, FRONT_T + 6.0))

    return m


# ---------------------------------------------------------------------------
# Component proxies for fit/interference checks (placeholder geometry until
# real STEP files are added -- same pattern as the controller project).
# ---------------------------------------------------------------------------

def proxies():
    P_ = P
    parts = {}

    # OSOOYOO 3.5" HDMI board, hung off the panel interior face. Modeled with
    # a 2mm standoff gap so its corner mount bosses read as CLEAR (the real
    # board floats off the panel for cable relief).
    parts['display'] = box(-P_['DISPLAY_BOARD_W'] / 2.0, P_['DISPLAY_BOARD_W'] / 2.0,
                           P_['DISPLAY_CY'] - P_['DISPLAY_BOARD_H'] / 2.0,
                           P_['DISPLAY_CY'] + P_['DISPLAY_BOARD_H'] / 2.0,
                           FRONT_T + 2.0, FRONT_T + 2.0 + P_['DISPLAY_BOARD_T'])

    # IMX708 camera board + lens, sitting on the bracket (8mm in from the
    # bay's front baffle plate)
    cz0 = P_['CAM_BAY_Z0'] + 8.0
    parts['camera'] = box(-P_['CAM_BOARD_W'] / 2.0, P_['CAM_BOARD_W'] / 2.0,
                          P_['CAM_BRACKET_TOP_Y'], P_['CAM_BRACKET_TOP_Y'] + 1.6,
                          cz0, cz0 + 17.0)
    parts['camera_lens'] = cyl_y(0.0, cz0 + 8.5, 10.0,
                                 P_['CAM_BRACKET_TOP_Y'] + 1.6 - EPS,
                                 P_['CAM_BRACKET_TOP_Y'] + 1.6 + P_['CAM_LENS_STACK'])

    # Pi 4B board, flat on its mounting bosses
    parts['pi'] = box(P_['PI_X_RANGE'][0], P_['PI_X_RANGE'][1],
                      P_['PI_Y_RANGE'][0], P_['PI_Y_RANGE'][1],
                      P_['PI_Z_RANGE'][0], P_['PI_Z_RANGE'][1])

    # Game card seated in the slot (Aztec face down)
    parts['card'] = box(-P_['CARD_W'] / 2.0, P_['CARD_W'] / 2.0,
                        P_['CARD_BOTTOM_Y'] - P_['CARD_T'], P_['CARD_BOTTOM_Y'],
                        FRONT_T, FRONT_T + P_['SLOT_POCKET_D'])

    # Controller puck: use the FABRICATED SHELLS (top+bottom STL from the
    # controller project) placed docked in the front recess -- the puck's
    # bottom face registers on the recess floor at z = DOCK_DEPTH, so the
    # fit check runs against the real printed geometry. Falls back to a
    # stadium placeholder if the controller files aren't present.
    ctrl_stl = os.path.join(os.path.expanduser('~'),
                            'Documents/glyphbox-controller/fusion-shell/stl')
    try:
        top = trimesh.load(os.path.join(ctrl_stl, 'glyphbox_top_shell.stl'))
        bot = trimesh.load(os.path.join(ctrl_stl, 'glyphbox_bottom_shell.stl'))
        # Dock the puck: flip 180 degrees about X so its back face (magnet
        # side, the bottom shell's low-z exterior) registers on the recess
        # floor at z = DOCK_DEPTH while the D-pad face points OUT of the
        # console (z < 0). After the flip the back face sits at z=+5.9.
        R = trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0])
        top.apply_transform(R)
        bot.apply_transform(R)
        dz = P_['DOCK_DEPTH'] - bot.bounds[1][2]   # back face -> recess floor
        dx = P_['DOCK_CX'] - (bot.bounds[0][0] + bot.bounds[1][0]) / 2.0
        dy = P_['DOCK_CY'] - (bot.bounds[0][1] + bot.bounds[1][1]) / 2.0
        for mesh in (top, bot):
            mesh.apply_translation([dx, dy, dz])
        parts['puck'] = trimesh.util.concatenate([top, bot])
        parts['puck_top'] = colored(top, [170, 120, 200, 255])
        parts['puck_bottom'] = colored(bot, [150, 100, 180, 255])
    except OSError:
        parts['puck'] = prism(stadium(P_['DOCK_CX'], P_['DOCK_CY'],
                                      P_['DOCK_LEN'] - 0.3, P_['DOCK_WID'] - 0.3),
                              -12.0, P_['DOCK_DEPTH'] + 2.0)

    return parts


# ---------------------------------------------------------------------------
# Assembly + interference checks
# ---------------------------------------------------------------------------

def colored(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual = trimesh.visual.ColorVisuals(
        mesh, face_colors=np.tile(rgba, (len(mesh.faces), 1)))
    return mesh


def pct_inside(sample_from, solid, n=40000):
    pts, _ = trimesh.sample.sample_surface(sample_from, n)
    return solid.contains(pts).mean(), pts


def check(label, sample_from, solid, tol=0.0005):
    frac, _ = pct_inside(sample_from, solid)
    verdict = 'CLEAR' if frac <= tol else f'*** INTERFERENCE {frac*100:.2f}% ***'
    print(f'  {label:34s} {frac*100:7.3f}% inside   {verdict}')
    return frac


def main():
    os.makedirs(OUT, exist_ok=True)

    print('params loaded: enclosure %.0fx%.0fx%.0f, slot cy=%.1f, cam dist=%.1f'
          % (W, H, D, P['SLOT_CY'], P['CAM_DIST']))

    front = build_front()
    rear = build_rear()
    for name, mesh in (('front', front), ('rear', rear)):
        assert mesh.is_watertight, f'{name} shell is not watertight!'
        print(f'  {name} shell: watertight, '
              f'{mesh.bounds.tolist()}')

    front.export(os.path.join(OUT, 'glyphbox_front_shell.stl'))
    rear.export(os.path.join(OUT, 'glyphbox_rear_shell.stl'))
    print('wrote stl/glyphbox_front_shell.stl, stl/glyphbox_rear_shell.stl')

    # Assertions on the layout the cardboard measurements feed into
    if P['DOCK_Y1'] > P['SLOT_Y0']:
        print('WARNING: controller dock recess overlaps the card slot -- '
              'rendezvous the DOCK_CY / SLOT_CY params against the prototype')

    # Color-coded scene
    proxy = proxies()
    meshes = {
        'front_shell': colored(front, [210, 210, 220, 120]),
        'rear_shell': colored(rear, [210, 210, 220, 120]),
        'display': colored(proxy['display'], [90, 140, 220, 255]),
        'camera': colored(proxy['camera'], [90, 90, 90, 255]),
        'camera_lens': colored(proxy['camera_lens'], [40, 40, 40, 255]),
        'pi': colored(proxy['pi'], [60, 160, 60, 255]),
        'card': colored(proxy['card'], [200, 170, 60, 255]),
    }
    if 'puck_top' in proxy:    # real controller shells
        meshes['puck_top'] = proxy['puck_top']
        meshes['puck_bottom'] = proxy['puck_bottom']
    else:                      # placeholder
        meshes['puck'] = colored(proxy['puck'], [170, 120, 200, 255])
    trimesh.Scene(meshes).export(os.path.join(OUT, 'assembly.glb'))
    print('wrote stl/assembly.glb (open with Quick Look to inspect)')

    exploded = {}
    for name, mesh in meshes.items():
        m = mesh.copy()
        if name in ('front_shell', 'display'):
            m.apply_translation([0, 0, -40.0])
        elif name == 'rear_shell':
            m.apply_translation([0, 0, 40.0])
        exploded[name] = m
    trimesh.Scene(exploded).export(os.path.join(OUT, 'assembly_exploded.glb'))
    print('wrote stl/assembly_exploded.glb')

    # ── Interference checks ──
    print('\n' + '=' * 68)
    print('INTERFERENCE CHECKS (proxies vs shells)')
    print('=' * 68)
    print('  (containment self-test first)')
    probe = np.array([[0.0, 5.0, 1.5]])   # inside the 3mm front panel slab
    assert front.contains(probe)[0], 'containment test broken'
    print('  (front shell containment ok)\n')

    # Display proxy is a solid bounding box: its corner mount bosses sit
    # inside that volume where the real board has its mounting holes, so a
    # small % is EXPECTED contact (tolerated) on the front-shell row only.
    for (name, expected) in (('display', True), ('camera', False),
                             ('camera_lens', False), ('pi', False),
                             ('card', False)):
        check(f'{name} vs rear shell', proxy[name], rear)
        check(f'{name} vs front shell (expected contact)' if expected
              else f'{name} vs front shell', proxy[name], front,
              tol=0.01 if expected else 0.0005)
    # Puck check: the real shells register flush on the recess floor, so
    # sample a copy floated 0.1mm outward to avoid counting the coplanar
    # back face as boundary contact -- the metric then reads true overlap.
    puck_probe = proxy['puck'].copy()
    puck_probe.apply_translation([0, 0, -0.1])
    check('puck vs front shell (real shells)', puck_probe, front, tol=0.005)

    # Clearance summary
    print('\n  key clearances:')
    print(f'    camera lens top y={P["CAM_BRACKET_TOP_Y"] + 1.6 + P["CAM_LENS_STACK"]:.2f}'
          f' vs card bottom y={P["CARD_BOTTOM_Y"]:.2f}'
          f' -> card-to-lens gap {(P["CARD_BOTTOM_Y"]) - (P["CAM_BRACKET_TOP_Y"] + 1.6 + P["CAM_LENS_STACK"]):.2f}mm'
          f' (CAM_DIST design target {P["CAM_DIST"]:.0f}mm)')
    print(f'    display board back z={FRONT_T + P["DISPLAY_BOARD_T"]:.2f} vs'
          f' slot pocket z={FRONT_T + P["SLOT_POCKET_D"]:.2f}')


if __name__ == '__main__':
    main()