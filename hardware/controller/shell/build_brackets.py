"""Extract the D-pad and A/B bracket geometry from the Lensless GBP front
shell and transform each into the Glyphbox controller shell's frame.

Both transforms are proper rigid motions (rotation + translation, det = +1).
Nothing is mirrored and nothing is scaled: the reference and our board are
both real millimetres, so the parts must come across 1:1 or the GBP repro
membranes won't seat.
"""
import math
import numpy as np
import trimesh

import sys as _sys, os as _os
if len(_sys.argv) < 2:
    _sys.exit('usage: python build_brackets.py path/to/Lensless_Front_Rev8.stl\n'
              '  (download the Lensless Gameboy Pocket shell from PCBWay first, see README.md)')
REF = _sys.argv[1]
OUT = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'reference-extracts')
_os.makedirs(OUT, exist_ok=True)

# ---- our shell frame ------------------------------------------------------
PCB_TOP = 1.6            # post tips land here
TOP_OUTER_Z = 9.393      # front cosmetic face
DPAD_CENTER = (-27.769, 0.015)
BTN_A = (34.945, 0.015)
BTN_B = (21.101, 0.015)
PICO_MIN_X = -10.548     # bracket must stay clear of the Pico
PICO_MAX_X = 10.452
PICO_CLEAR = 0.45

# ---- reference frame ------------------------------------------------------
REF_OUTER_FACE_Y = -7.29289   # cosmetic face
REF_POST_TIP_Y = 0.50         # rear-most extent of the membrane posts
REF_DPAD_CENTER = (-73.152, 40.500)
REF_BTN_A = (-24.664, 41.974)
REF_BTN_B = (-37.651, 37.972)
REF_SCREW_POSTS = [(-83.589, 26.000), (-63.079, 24.993), (-56.652, 36.354),
                   (-39.044, 24.849), (-18.365, 32.032)]

# Thickness alignment is shared by both brackets: ref Y maps to our Z as
# Z = -y + C, and we want the post tips (ref y = +0.5) to land on the PCB
# top surface, so C = PCB_TOP + REF_POST_TIP_Y.
Z_SHIFT = PCB_TOP + REF_POST_TIP_Y      # 2.1

m = trimesh.load(REF)
print('reference loaded, watertight:', m.is_watertight)


def box(xr, yr, zr):
    b = trimesh.creation.box(extents=[xr[1]-xr[0], yr[1]-yr[0], zr[1]-zr[0]])
    b.apply_translation([(xr[0]+xr[1])/2, (yr[0]+yr[1])/2, (zr[0]+zr[1])/2])
    return b


# The screw bosses are BLIND (they bottom out around ref Y = -5.0; the
# cosmetic plate runs -7.29..-5.0 and is solid across them). So the
# subtraction must start behind the plate, not run full depth -- a
# full-depth cut punches a visible hole straight through the front face.
SCREW_CUT_Y = (-5.5, 0.6)


def drop_screw_posts(mesh, locs, radius=3.5):
    """Remove the shell-assembly screw bosses, leaving the front plate intact.

    Radius chosen by measurement, not by eye. Where the cut circle runs
    tangent to another surface it leaves a razor-thin crescent; a sweep of
    2.4/2.6/3.0/3.5/4.0 showed 3.5 produces roughly a quarter as many
    sub-0.5mm slivers as 3.0 while still clearing every membrane post by
    0.36mm. 4.0 would clip a post, so 3.5 is the practical ceiling.
    """
    out = mesh
    y0, y1 = SCREW_CUT_Y
    for (sx, sz) in locs:
        cyl = trimesh.creation.cylinder(radius=radius, height=(y1-y0)+1, sections=64)
        cyl.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2, [1, 0, 0]))
        cyl.apply_translation([sx, (y0+y1)/2, sz])
        out = trimesh.boolean.difference([out, cyl], engine='manifold')
    return out


def clip_min_y(mesh, y_limit):
    b = mesh.bounds
    keep = box((b[0][0]-2, b[1][0]+2), (y_limit, b[1][1]+2), (b[0][2]-2, b[1][2]+2))
    return trimesh.boolean.intersection([mesh, keep], engine='manifold')


def clip_max_x(mesh, x_limit):
    b = mesh.bounds
    keep = box((b[0][0]-2, x_limit), (b[0][1]-2, b[1][1]+2), (b[0][2]-2, b[1][2]+2))
    return trimesh.boolean.intersection([mesh, keep], engine='manifold')


def clip_min_x(mesh, x_limit):
    b = mesh.bounds
    keep = box((x_limit, b[1][0]+2), (b[0][1]-2, b[1][1]+2), (b[0][2]-2, b[1][2]+2))
    return trimesh.boolean.intersection([mesh, keep], engine='manifold')


def report(name, mesh):
    b = mesh.bounds
    print(f'  {name}: watertight={mesh.is_watertight}  '
          f'X[{b[0][0]:.2f},{b[1][0]:.2f}] Y[{b[0][1]:.2f},{b[1][1]:.2f}] Z[{b[0][2]:.2f},{b[1][2]:.2f}]')


# ===========================================================================
# D-PAD BRACKET
# ===========================================================================
print('\n--- D-pad ---')
# ref xmax chosen so the piece stops at our X = -11.0, clearing the Pico
DPAD_X = (-86.5, -56.4)
DPAD_Y = (-8.0, 0.6)
DPAD_Z = (20.0, 54.0)

dpad = trimesh.boolean.intersection([m, box(DPAD_X, DPAD_Y, DPAD_Z)], engine='manifold')
dpad = drop_screw_posts(dpad, [p for p in REF_SCREW_POSTS if p[0] < -50])
report('extracted', dpad)

T_dpad = np.array([
    [1, 0, 0, DPAD_CENTER[0] - REF_DPAD_CENTER[0]],
    [0, 0, 1, DPAD_CENTER[1] - REF_DPAD_CENTER[1]],
    [0, -1, 0, Z_SHIFT],
    [0, 0, 0, 1.0]])
assert abs(np.linalg.det(T_dpad[:3, :3]) - 1.0) < 1e-9, 'D-pad transform is not a proper rotation'
dpad.apply_transform(T_dpad)
report('positioned', dpad)

# ===========================================================================
# A/B BRACKET
# ===========================================================================
print('\n--- A/B ---')
AB_X = (-44.0, -16.5)
AB_Y = (-8.0, 0.6)
AB_Z = (24.0, 50.0)

ab = trimesh.boolean.intersection([m, box(AB_X, AB_Y, AB_Z)], engine='manifold')
ab = drop_screw_posts(ab, [p for p in REF_SCREW_POSTS if p[0] > -50])
report('extracted', ab)

ref_mid = ((REF_BTN_A[0]+REF_BTN_B[0])/2, (REF_BTN_A[1]+REF_BTN_B[1])/2)
our_mid = ((BTN_A[0]+BTN_B[0])/2, (BTN_A[1]+BTN_B[1])/2)
ref_ang = math.atan2(REF_BTN_A[1]-REF_BTN_B[1], REF_BTN_A[0]-REF_BTN_B[0])
our_ang = math.atan2(BTN_A[1]-BTN_B[1], BTN_A[0]-BTN_B[0])
theta = our_ang - ref_ang
print(f'  ref A-B angle {math.degrees(ref_ang):.3f}deg, ours {math.degrees(our_ang):.3f}deg '
      f'-> rotate {math.degrees(theta):.3f}deg')
print(f'  ref spacing {math.dist(REF_BTN_A, REF_BTN_B):.3f}mm, '
      f'ours {math.dist(BTN_A, BTN_B):.3f}mm')

# ref (x,y,z) -> our frame with the A/B midpoint at the origin
M0 = np.array([
    [1, 0, 0, -ref_mid[0]],
    [0, 0, 1, -ref_mid[1]],
    [0, -1, 0, Z_SHIFT],
    [0, 0, 0, 1.0]])
c, s = math.cos(theta), math.sin(theta)
RZ = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
T1 = np.array([[1, 0, 0, our_mid[0]], [0, 1, 0, our_mid[1]], [0, 0, 1, 0], [0, 0, 0, 1.0]])
T_ab = T1 @ RZ @ M0
assert abs(np.linalg.det(T_ab[:3, :3]) - 1.0) < 1e-9, 'A/B transform is not a proper rotation'

# where do the button centres actually land?
for nm, refc, ours in (('A', REF_BTN_A, BTN_A), ('B', REF_BTN_B, BTN_B)):
    p = T_ab @ np.array([refc[0], 0.0, refc[1], 1.0])
    print(f'  button {nm}: lands ({p[0]:.3f},{p[1]:.3f})  target ({ours[0]:.3f},{ours[1]:.3f})  '
          f'err {math.dist((p[0], p[1]), ours):.3f}mm')

ab.apply_transform(T_ab)
report('positioned', ab)

# ===========================================================================
# Pico clearance + export
# ===========================================================================
# The top shell's M2.5 pilot bosses sit at Y = -21.055 with OD 5.5, so they
# reach up to Y = -18.305. Trim both brackets clear of that: otherwise the
# bracket plate overlaps the boss and, because the meshes get joined AFTER
# the script cuts the pilot holes, it would partially refill them.
BOSS_TOP_Y = -18.305
TRIM_Y = -18.0
print('\n--- clear the screw bosses ---')
if dpad.bounds[0][1] < TRIM_Y:
    dpad = clip_min_y(dpad, TRIM_Y)
    print(f'  D-pad trimmed to Y >= {TRIM_Y}')
if ab.bounds[0][1] < TRIM_Y:
    ab = clip_min_y(ab, TRIM_Y)
    print(f'  A/B trimmed to Y >= {TRIM_Y}')
print(f'  D-pad min Y {dpad.bounds[0][1]:.3f}, A/B min Y {ab.bounds[0][1]:.3f} '
      f'(boss top {BOSS_TOP_Y})')

print('\n--- Pico clearance ---')
if dpad.bounds[1][0] > PICO_MIN_X - PICO_CLEAR:
    dpad = clip_max_x(dpad, PICO_MIN_X - PICO_CLEAR)
    print(f'  D-pad clipped to X <= {PICO_MIN_X - PICO_CLEAR:.3f}')
print(f'  D-pad max X {dpad.bounds[1][0]:.3f}  (Pico starts {PICO_MIN_X})  '
      f'gap {PICO_MIN_X - dpad.bounds[1][0]:.3f}mm')

if ab.bounds[0][0] < PICO_MAX_X + PICO_CLEAR:
    ab = clip_min_x(ab, PICO_MAX_X + PICO_CLEAR)
    print(f'  A/B clipped to X >= {PICO_MAX_X + PICO_CLEAR:.3f}')
print(f'  A/B min X   {ab.bounds[0][0]:.3f}  (Pico ends   {PICO_MAX_X})  '
      f'gap {ab.bounds[0][0] - PICO_MAX_X:.3f}mm')

print('\n--- checks ---')
for nm, mesh in (('dpad', dpad), ('ab', ab)):
    b = mesh.bounds
    print(f'  {nm}: outer face Z={b[1][2]:.3f} (want {TOP_OUTER_Z})  '
          f'post tip Z={b[0][2]:.3f} (want {PCB_TOP})  watertight={mesh.is_watertight}')

dpad.export(f'{OUT}/dpad_bracket_positioned.stl')
ab.export(f'{OUT}/ab_bracket_positioned.stl')
print('\nexported both')
