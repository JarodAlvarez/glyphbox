"""
Glyphbox console case generator.

Run via Fusion 360 -> Utilities -> Scripts and Add-Ins -> Scripts -> Run.

Builds two bodies in the active design's root component (FrontShellBody
and RearShellBody), translated from the cardboard prototype layout:

  - FrontShellBody : the front panel slab. Carries the display window,
    the card slot opening, the guide rails + stop tab the card slides
    along, the controller dock recess (magnetic puck docking, no
    connectors), the slot LED channel, and the M3 closure holes.
  - RearShellBody  : back + sides + floor + ceiling. Carries the inner
    cavity, Pi mounting bosses (default: ceiling mount, out of the camera
    bay's way), the camera bay baffle + bracket, the bottom speaker well
    + grille, rear/side wall pass-throughs (USB-C, micro-HDMI, power
    switch, controller cable), and the top vents.

The two shells close flush at z = FRONT_T, held by M3 screws through the
panel into heat-set-insert bosses on the rim.

The geometry is fully parametric: every cardboard-prototype measurement
lives in the PARAMS block below (see measures.md for the checklist).
Nothing below PARAMS/DERIVED should need touching for a first pass.

FRAME: origin = bottom-center of the front face. X = width (case centered
on x=0), Y = height (y=0 is the floor), Z = depth (z=0 = front panel outer
face; rear wall outer at z = EXTERIOR_D). Built from XY-plane sketches
extruded in Z, XZ-plane sketches extruded in Y, and YZ-plane sketches
extruded in X, so all three construction planes are used.

KNOWN PLACEHOLDERS (verify before printing):
  - Rear-wall port offsets (USB-C, 2x micro-HDMI) and the controller-cable
    exit are approximate Pi 4B connector positions. Measure your Pi during
    fit-check and update the PORT table in PARAMS.
  - PI_MOUNT defaults to 'ceiling' (floor real estate belongs to the
    camera bay). If the cardboard prototype mounts the Pi on the floor,
    switch PI_MOUNT and adjust PI_CX/PI_CY.
  - CAM_LENS_STACK, display board dims and DOCK magnet pocket positions:
    verify with calipers on the real parts.

KNOWN PLACEHOLDERS -- none in the API layer: like the controller shell,
every length value is funneled through mm()/pt()/mmv() (Fusion's API
interprets raw numbers in centimeters).
"""

import adsk.core
import adsk.fusion
import traceback
import math

# Fusion's Python API interprets raw length numbers -- Point3D coordinates,
# sketchCircle radii, ValueInput.createByReal() for distances -- in its
# internal unit, which is CENTIMETERS, regardless of the document's display
# unit. Every dimension in this script is authored in mm, so all of it is
# funneled through mm()/pt()/mmv() below. Angles are radians -- no conversion.

def mm(v):
    return v * 0.1


def pt(x, y, z=0.0):
    return adsk.core.Point3D.create(mm(x), mm(y), mm(z))


def mmv(v):
    return adsk.core.ValueInput.createByReal(mm(v))


# ---------------------------------------------------------------------------
# PARAMS -- cardboard prototype measurements (see measures.md)
# ---------------------------------------------------------------------------

# ── Exterior envelope ───────────────────────────────────────────────────────
EXTERIOR_W = 150.0     # TBD-cardboard: outer width
EXTERIOR_H = 200.0     # TBD-cardboard: outer height
EXTERIOR_D = 100.0     # TBD-cardboard: outer depth
WALL_T = 3.0           # wall thickness (print)
FRONT_T = WALL_T       # front panel thickness

# ── Display: OSOOYOO 3.5" HDMI LCD (board ~86x56x12, view 73.4x49) ─────────
DISPLAY_VIEW_W = 73.4          # LCD view area (spec)
DISPLAY_VIEW_H = 49.0
DISPLAY_CUTOUT_CLEAR = 1.0     # margin added around the view area
DISPLAY_BOARD_W = 86.0         # TBD-cardboard: verify board dims
DISPLAY_BOARD_H = 56.0
DISPLAY_BOARD_T = 12.0
DISPLAY_CY = 140.0             # TBD-cardboard: board center height on face
DISPLAY_BOSS_H = 6.0           # standoff bosses behind the board

# ── Card slot (internal, card face-down over the camera) ───────────────────
SLOT_W = 120.0                 # opening width
SLOT_OPEN_H = 5.0              # TBD-cardboard: opening height
SLOT_CY = 102.0                # TBD-cardboard: opening center height
CARD_W = 85.6                  # printed cards are ISO ID-1 (card-print.py)
CARD_T = 0.9                   # 0.76mm card + lamination
CARD_BOTTOM_Y = SLOT_CY - 2.0  # card's bottom face (Aztec side) when seated
SLOT_POCKET_D = 45.0           # TBD-cardboard: card insertion depth in the case

# ── Camera: Arducam IMX708 75D (25x24 board) ───────────────────────────────
CAM_BOARD_W = 25.0
CAM_BOARD_H = 24.0
CAM_DIST = 90.0            # TBD-cardboard: lens-to-card distance (VALIDATED)
CAM_LENS_STACK = 4.0       # lens collar height above the camera PCB (verify)
CAM_BRACKET_TOP_Y = 4.4    # top of the floor bracket the camera PCB sits on
CAM_BAY_W = 48.0           # baffle interior width
CAM_BAY_Z0 = FRONT_T + SLOT_POCKET_D + 4.0   # baffle front wall z
CAM_BAY_Z1 = EXTERIOR_D - WALL_T - 6.0       # baffle rear wall z
CAM_BAY_TOP_Y = CARD_BOTTOM_Y - 12.0         # baffle top (below the card)

# ── Slot LED channel (under the opening's upper lip, per fabrication brief) ─
LED_CY = SLOT_CY + 5.5     # TBD-cardboard: strip center height
LED_HALF_W = 40.0          # half strip width
LED_HALF_H = 3.0           # half channel height
LED_DEPTH = 2.5            # channel depth into the panel interior face

# ── Controller dock (puck MEASURED from the fabricated shells at
#    117.85 x 62.34 x 15.29 mm, single 10mm magnet at dead center) ─────────
DOCK_CX = 0.0             # dock center X (centered on the front face)
DOCK_LEN = 118.4           # puck shell length (117.85) + 0.55 clearance
DOCK_WID = 62.8            # puck shell width (62.34) + 0.46 clearance
DOCK_DEPTH = 2.0           # recess depth into the panel outer face
DOCK_CY = SLOT_CY - SLOT_OPEN_H / 2.0 - 6.0 - DOCK_WID / 2.0  # below slot
MAGNET_DIA = 10.0
MAGNET_DEPTH = 2.2         # blind pocket depth (0.8mm backing in panel)
MAGNET_Y = [DOCK_CY]       # single centered pocket: nests the puck's own
                           # centered magnet (see build_controller_shell.py)

# ── Raspberry Pi 4B ─────────────────────────────────────────────────────────
PI_W = 85.6
PI_H = 56.5
PI_T = 1.6
PI_MOUNT = 'ceiling'       # 'ceiling' keeps the floor clear for the camera
PI_CX = 0.0                # board center X
PI_CZ = 55.0               # board center Z (depth; ports face the rear wall)
PI_STANDOFF_H = 8.0        # gap between mounting surface and board underside
PI_HOLE_DX = 29.0          # mount-hole offsets from board center
PI_HOLE_DY = 24.5

# Rear-wall pass-throughs, in the Pi board frame (dx from PI_CX, w x h).
# PORT OFFSETS ARE PLACEHOLDERS -- verify against the real Pi 4B before
# printing (see file docstring).
PORTS = [
    ('USB-C',        dict(dx=-6.0, w=9.0,  h=7.5)),
    ('MICRO-HDMI-0', dict(dx= 5.0, w=6.6,  h=5.4)),
    ('MICRO-HDMI-1', dict(dx=13.0, w=6.6,  h=5.4)),
]
PWR_BTN_X = 40.0           # latching power switch center on rear wall
PWR_BTN_DIA = 10.2
CTRL_CABLE_X = -40.0       # controller cable exit on the rear wall
CTRL_CABLE_DIA = 6.0

# ── Bottom speaker ──────────────────────────────────────────────────────────
SPEAKER_CX = 0.0           # TBD-cardboard: center X
SPEAKER_CZ = 25.0          # TBD-cardboard: center Z (depth from front plane)
SPEAKER_DIA = 78.0
SPEAKER_RECESS_D = 8.0     # recess depth into the cavity above the floor

# ── Ventilation / fan ───────────────────────────────────────────────────────
FAN_OPTION = 0             # 1 = 40x40 fan recess + mounts on the top wall
VENT_SLOTS = 5             # top-wall vent slots (always on)

# ── Misc ────────────────────────────────────────────────────────────────────
CLOSURE_BOLTS = 6          # M3 screws panel -> rim bosses
CLOSURE_EDGE = 6.0         # boss inset from panel edges
EPS = 1.0                  # geometry overshoot so cuts break through cleanly

# ---------------------------------------------------------------------------
# DERIVED geometry
# ---------------------------------------------------------------------------

W = EXTERIOR_W
H = EXTERIOR_H
D = EXTERIOR_D
T = WALL_T

# Display window (view area + clearance), centered on the panel
DISP_WIN_X0, DISP_WIN_X1 = -(DISPLAY_VIEW_W / 2 + DISPLAY_CUTOUT_CLEAR), \
                            (DISPLAY_VIEW_W / 2 + DISPLAY_CUTOUT_CLEAR)
DISP_WIN_Y0, DISP_WIN_Y1 = DISPLAY_CY - (DISPLAY_VIEW_H / 2 + DISPLAY_CUTOUT_CLEAR), \
                            DISPLAY_CY + (DISPLAY_VIEW_H / 2 + DISPLAY_CUTOUT_CLEAR)

# Display mount bosses: 4x M2.5 standoffs at the board corners
DISP_BOSS_DX = DISPLAY_BOARD_W / 2 - 4.0
DISP_BOSS_DY = DISPLAY_BOARD_H / 2 - 4.0

# Slot opening + card seat geometry
SLOT_Y0, SLOT_Y1 = SLOT_CY - SLOT_OPEN_H / 2.0, SLOT_CY + SLOT_OPEN_H / 2.0
RAIL_W = 5.0                            # guide rail width (x direction)
RAIL_IN_X = CARD_W / 2.0 + 0.5          # rail inner edge (card + play)
RAIL_T = 3.0                            # rail vertical thickness

# Camera frame (derived from the validated working distance)
LENS_Y = CARD_BOTTOM_Y - CAM_DIST       # lens plane height above the floor
CAM_BOARD_BOTTOM_Y = CAM_BRACKET_TOP_Y  # board sits directly on the bracket
CAM_BOARD_TOP_Y = CAM_BOARD_BOTTOM_Y + 1.6

# LED channel (rect, centered on LED_CY)
LED_Y0, LED_Y1 = LED_CY - LED_HALF_H, LED_CY + LED_HALF_H

# Dock + magnet pockets
DOCK_Y0 = DOCK_CY - DOCK_WID / 2.0
DOCK_Y1 = DOCK_CY + DOCK_WID / 2.0

# Pi frame
PI_BOARD_BOTTOM_Y = (H - T - PI_STANDOFF_H) if PI_MOUNT == 'ceiling' \
                    else (T + PI_STANDOFF_H)
PI_PORT_Y = PI_BOARD_BOTTOM_Y + PI_T / 2.0   # rear-wall connector height
PI_HOLES = [(PI_CX + dx, PI_CZ + dy)
            for dx in (-PI_HOLE_DX, PI_HOLE_DX)
            for dy in (-PI_HOLE_DY, PI_HOLE_DY)]
PI_Y_RANGE = (PI_BOARD_BOTTOM_Y, PI_BOARD_BOTTOM_Y + PI_T)
PI_X_RANGE = (PI_CX - PI_W / 2.0, PI_CX + PI_W / 2.0)
PI_Z_RANGE = (PI_CZ - PI_H / 2.0, PI_CZ + PI_H / 2.0)

# Speaker
SPEAKER_R = SPEAKER_DIA / 2.0

# Closure positions (M3 through-panel -> boss on rim)
CLOSURE_X = [-(W / 2.0 - CLOSURE_EDGE), (W / 2.0 - CLOSURE_EDGE)]
CLOSURE_Y = [10.0, H / 2.0, H - 10.0]
CLOSURE_BOLT_DIA = 3.4      # clearance through the panel
BOSS_OD = 6.0               # rim boss outer diameter
BOSS_PILOT_DIA = 2.1        # pilot for M2.5 self-tapping / heat-set


# ---------------------------------------------------------------------------
# Sketch + extrude helpers (adsk; all values in mm)
# ---------------------------------------------------------------------------

def largest_profile(sketch):
    profs = sketch.profiles
    best, best_area = None, -1.0
    for i in range(profs.count):
        p = profs.item(i)
        props = p.areaProperties()
        if props.area > best_area:
            best, best_area = p, props.area
    return best


def offset_plane(comp, base_plane, dist):
    """Construction plane offset `dist` (mm) along `base_plane`'s normal."""
    inp = comp.constructionPlanes.createInput()
    inp.setByOffset(base_plane, mmv(dist))
    return comp.constructionPlanes.add(inp)


def srect(sk, x0, y0, x1, y1):
    """Two-point rectangle on the sketch's plane (coords in the plane frame)."""
    sk.sketchCurves.sketchLines.addTwoPointRectangle(pt(x0, y0), pt(x1, y1))


def scirc(sk, cx, cy, r):
    sk.sketchCurves.sketchCircles.addByCenterRadius(pt(cx, cy), mm(r))


def stadium_profile_sketch(sk, cx, cy, length, width):
    """Stadium (pill) outline as one closed profile -- used for the dock."""
    r = width / 2.0
    half_straight = (length - width) / 2.0
    lines = sk.sketchCurves.sketchLines
    arcs = sk.sketchCurves.sketchArcs
    p_top_left = pt(cx - half_straight, cy + r)
    p_top_right = pt(cx + half_straight, cy + r)
    p_bot_left = pt(cx - half_straight, cy - r)
    p_bot_right = pt(cx + half_straight, cy - r)
    c_right = pt(cx + half_straight, cy)
    c_left = pt(cx - half_straight, cy)
    lines.addByTwoPoints(p_top_left, p_top_right)
    arcs.addByCenterStartSweep(c_right, p_top_right, -math.pi)
    lines.addByTwoPoints(p_bot_right, p_bot_left)
    arcs.addByCenterStartSweep(c_left, p_bot_left, -math.pi)


def extrude(comp, profile, start, height, op, target=None):
    """Extrude from `start` (plane offset) by `height`, joining/cutting `target`."""
    feats = comp.features.extrudeFeatures
    inp = feats.createInput(profile, op)
    inp.setDistanceExtent(False, mmv(height))
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(mmv(start))
    if target is not None:
        inp.participantBodies = [target]
    return feats.add(inp)


def extrude_sym(comp, profile, half, op, target=None):
    """Extrude symmetrically about the sketch plane (immune to normal dir)."""
    feats = comp.features.extrudeFeatures
    inp = feats.createInput(profile, op)
    inp.setDistanceExtent(True, mmv(half))
    if target is not None:
        inp.participantBodies = [target]
    return feats.add(inp)


def new_body(comp, plane, start, height, sketch_fn, name):
    sk = comp.sketches.add(plane)
    sketch_fn(sk)
    body = extrude(comp, largest_profile(sk), start, height,
                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    body.name = name
    return body


# ---------------------------------------------------------------------------
# Front panel body
# ---------------------------------------------------------------------------

def build_front(comp):
    xy = comp.xYConstructionPlane

    # Panel slab: z in [0, FRONT_T]
    body = new_body(comp, xy, 0.0, FRONT_T,
                    lambda sk: srect(sk, -W / 2.0, 0.0, W / 2.0, H),
                    'FrontShellBody')

    # Display window (through)
    sk = comp.sketches.add(xy)
    srect(sk, DISP_WIN_X0, DISP_WIN_Y0, DISP_WIN_X1, DISP_WIN_Y1)
    extrude(comp, largest_profile(sk), 0.0, FRONT_T + EPS,  # noqa: F841
            adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # Display mount bosses on the interior face
    for sxx in (-1, 1):
        for syy in (-1, 1):
            sk = comp.sketches.add(xy)
            scirc(sk, sxx * DISP_BOSS_DX, DISPLAY_CY + syy * DISP_BOSS_DY, 2.4)
            extrude(comp, largest_profile(sk), FRONT_T, DISPLAY_BOSS_H,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation, body)

    # Card slot opening (through)
    sk = comp.sketches.add(xy)
    srect(sk, -SLOT_W / 2.0, SLOT_Y0, SLOT_W / 2.0, SLOT_Y1)
    extrude(comp, largest_profile(sk), 0.0, FRONT_T + EPS,  # noqa: F841
            adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # Slot guide rails: two ledges the card slides along, + stop tab at the
    # pocket end so the card seats at a fixed depth.
    for sxx in (-1, 1):
        if sxx < 0:
            rx0, rx1 = -RAIL_IN_X - RAIL_W, -RAIL_IN_X
        else:
            rx0, rx1 = RAIL_IN_X, RAIL_IN_X + RAIL_W
        sk = comp.sketches.add(xy)
        srect(sk, rx0, CARD_BOTTOM_Y - RAIL_T, rx1, CARD_BOTTOM_Y)
        extrude(comp, largest_profile(sk), FRONT_T, SLOT_POCKET_D,
                adsk.fusion.FeatureOperations.JoinFeatureOperation, body)
    sk = comp.sketches.add(xy)
    srect(sk, -CARD_W / 2.0, CARD_BOTTOM_Y - RAIL_T, CARD_W / 2.0, CARD_BOTTOM_Y)
    extrude(comp, largest_profile(sk), FRONT_T + SLOT_POCKET_D, 3.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, body)

    # Controller dock recess (blind pocket from the outer face). The cut is
    # symmetric about a mid-depth plane so the direction is never ambiguous -
    # leaving a blind pocket, not a through hole.
    plane = offset_plane(comp, xy, DOCK_DEPTH / 2.0)
    sk = comp.sketches.add(plane)
    stadium_profile_sketch(sk, 0.0, DOCK_CY, DOCK_LEN, DOCK_WID)
    extrude_sym(comp, largest_profile(sk), DOCK_DEPTH / 2.0,
                adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # Magnet pockets (blind, 0.8mm backing left in the 3mm panel)
    plane = offset_plane(comp, xy, MAGNET_DEPTH / 2.0)
    for my in MAGNET_Y:
        sk = comp.sketches.add(plane)
        scirc(sk, 0.0, my, MAGNET_DIA / 2.0)
        extrude_sym(comp, largest_profile(sk), MAGNET_DEPTH / 2.0,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # Slot LED channel -- blind recess cut from the panel interior face
    # (symmetric about the channel mid-plane: removes [FRONT_T-LED_DEPTH,
    # FRONT_T], never breaking through the outer face).
    plane = offset_plane(comp, xy, FRONT_T - LED_DEPTH / 2.0)
    sk = comp.sketches.add(plane)
    srect(sk, -LED_HALF_W, LED_Y0, LED_HALF_W, LED_Y1)
    extrude_sym(comp, largest_profile(sk), LED_DEPTH / 2.0,
                adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # M3 closure holes (through the panel, into rim bosses on the rear shell)
    for cx in CLOSURE_X:
        for cy in CLOSURE_Y:
            sk = comp.sketches.add(xy)
            scirc(sk, cx, cy, CLOSURE_BOLT_DIA / 2.0)
            extrude(comp, largest_profile(sk), 0.0, FRONT_T + EPS,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    return body


# ---------------------------------------------------------------------------
# Rear shell body
# ---------------------------------------------------------------------------

def build_rear(comp):
    xy = comp.xYConstructionPlane
    xz = comp.xZConstructionPlane
    yz = comp.yZConstructionPlane

    # Outer box: covers z in [FRONT_T, EXTERIOR_D]
    body = new_body(comp, xy, FRONT_T, D - FRONT_T,
                    lambda sk: srect(sk, -W / 2.0, 0.0, W / 2.0, H),
                    'RearShellBody')

    # Inner cavity (walls WALL_T thick; frame is centered on x=0)
    sk = comp.sketches.add(xy)
    srect(sk, -W / 2.0 + T, T, W / 2.0 - T, H - T)
    extrude(comp, largest_profile(sk), FRONT_T, D - T - FRONT_T,
            adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # ── Pi mount bosses (ceiling or floor, per PI_MOUNT) ──────────────────
    # Bosses run from the board's top face up through the mounting wall, so
    # the board butts against their bottoms and never interpenetrates them.
    if PI_MOUNT == 'ceiling':
        lo, hi = PI_BOARD_BOTTOM_Y + PI_T, H - T + 1.0
        plane = offset_plane(comp, xz, (lo + hi) / 2.0)
        half = (hi - lo) / 2.0
    else:
        lo, hi = T - 1.0, PI_BOARD_BOTTOM_Y
        plane = offset_plane(comp, xz, (lo + hi) / 2.0)
        half = (hi - lo) / 2.0
    for (hx, hz) in PI_HOLES:
        sk = comp.sketches.add(plane)
        scirc(sk, hx, hz, 2.8)
        extrude_sym(comp, largest_profile(sk), half,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation, body)

    # ── Camera bay: 4 baffle plates around the camera shaft ───────────────
    for sxx in (-1, 1):
        plane = offset_plane(comp, yz, sxx * CAM_BAY_W / 2.0)
        sk = comp.sketches.add(plane)
        srect(sk, CAM_BAY_Z0, T, CAM_BAY_Z1, CAM_BAY_TOP_Y)
        extrude_sym(comp, largest_profile(sk), 1.5,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation, body)
    for zz in (CAM_BAY_Z0, CAM_BAY_Z1):
        plane = offset_plane(comp, xy, zz)
        sk = comp.sketches.add(plane)
        srect(sk, -CAM_BAY_W / 2.0, T, CAM_BAY_W / 2.0, CAM_BAY_TOP_Y)
        extrude_sym(comp, largest_profile(sk), 1.5,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation, body)

    # Camera bracket: floor ledge under the camera PCB. Kept 8mm back from
    # the bay's front baffle plate so the camera board clears it.
    sk = comp.sketches.add(offset_plane(comp, xy, CAM_BAY_Z0 + 8.0))
    srect(sk, -16.0, T, 16.0, CAM_BRACKET_TOP_Y)
    extrude(comp, largest_profile(sk), CAM_BAY_Z0 + 8.0, 18.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, body)

    # ── Bottom speaker: recess + grille holes through the floor ───────────
    plane = offset_plane(comp, xz, (T + SPEAKER_RECESS_D) / 2.0)
    sk = comp.sketches.add(plane)
    scirc(sk, SPEAKER_CX, SPEAKER_CZ, SPEAKER_R)
    extrude_sym(comp, largest_profile(sk),
                (T + SPEAKER_RECESS_D) / 2.0 + EPS,
                adsk.fusion.FeatureOperations.CutFeatureOperation, body)
    sk = comp.sketches.add(plane)
    count = 3
    for i in range(count):
        for j in range(count):
            gx = SPEAKER_CX + (i - 1) * 16.0
            gz = SPEAKER_CZ + (j - 1) * 16.0
            if gx * gx + (gz - SPEAKER_CZ) ** 2 < (SPEAKER_R - 8.0) ** 2:
                scirc(sk, gx, gz, 2.0)
    extrude_sym(comp, largest_profile(sk), T / 2.0 + EPS,
                adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # ── Rear wall pass-throughs (symmetric cuts: direction-proof) ─────────
    rear = offset_plane(comp, xy, D)
    for name, p in PORTS:   # ports align with the Pi's connector edge height
        sk = comp.sketches.add(rear)
        srect(sk, PI_CX + p['dx'] - p['w'] / 2.0, PI_PORT_Y - p['h'] / 2.0,
              PI_CX + p['dx'] + p['w'] / 2.0, PI_PORT_Y + p['h'] / 2.0)
        extrude_sym(comp, largest_profile(sk), WALL_T / 2.0 + 1.5,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)
    for (cx, cy, dia) in ((PWR_BTN_X, H - 30.0, PWR_BTN_DIA),
                          (CTRL_CABLE_X, H - 50.0, CTRL_CABLE_DIA)):
        sk = comp.sketches.add(rear)
        scirc(sk, cx, cy, dia / 2.0)
        extrude_sym(comp, largest_profile(sk), WALL_T / 2.0 + 1.5,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # ── Top vents + optional fan recess ───────────────────────────────────
    top = offset_plane(comp, xz, H)
    step = (D - T - 10.0 - 20.0) / VENT_SLOTS
    for i in range(VENT_SLOTS):
        sk = comp.sketches.add(top)
        z0 = 10.0 + i * step
        srect(sk, -35.0, z0, 35.0, z0 + 3.0)
        extrude_sym(comp, largest_profile(sk), WALL_T / 2.0 + 1.5,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)
    if FAN_OPTION:
        plane = offset_plane(comp, xz, H - T - 5.0)
        sk = comp.sketches.add(plane)
        srect(sk, -21.0, D / 2.0 - 21.0, 21.0, D / 2.0 + 21.0)
        extrude_sym(comp, largest_profile(sk), 5.0 + EPS,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)
        sk = comp.sketches.add(top)
        for i in range(4):
            fx = [-15.0, -15.0, 15.0, 15.0][i]
            fz = D / 2.0 + [-15.0, 15.0, -15.0, 15.0][i]
            scirc(sk, fx, fz, 1.5)
        extrude_sym(comp, largest_profile(sk), WALL_T / 2.0 + 1.5,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    # ── Rim closure bosses (M2.5 heat-set / self-tap pilots) ──────────────
    rim = offset_plane(comp, xy, FRONT_T)
    for cx in CLOSURE_X:
        for cy in CLOSURE_Y:
            sk = comp.sketches.add(rim)
            scirc(sk, cx, cy, BOSS_OD / 2.0)
            extrude(comp, largest_profile(sk), FRONT_T, 7.0,
                    adsk.fusion.FeatureOperations.JoinFeatureOperation, body)
            sk = comp.sketches.add(rim)
            scirc(sk, cx, cy, BOSS_PILOT_DIA / 2.0)
            extrude(comp, largest_profile(sk), FRONT_T, 6.0,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    return body


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design. Create/open a design first.')
            return
        root = design.rootComponent

        front = build_front(root)
        rear = build_rear(root)

        ui.messageBox(
            'Built FrontShellBody and RearShellBody.\n\n'
            'DELETE ANY BODIES FROM A PREVIOUS RUN FIRST -- this version '
            'only builds on a clean design.\n\n'
            'FRAME: origin = bottom-center of the front face; X width '
            '(case centered on 0), Y height (y=0 floor), Z depth (z=0 = '
            'front face outer; rear wall at z=%.1f).\n\n'
            'NEXT STEPS in Fusion:\n'
            '1. Export both bodies to STL (right-click each body -> Save '
            'as STL) and bring them into your slicer.\n'
            '2. Fit-check: import your OSOOYOO display, IMX708 camera and '
            'Pi 4B STEP files and slide them into the pocket/bracket '
            'geometry. Update the PAGE-TBD params (see measures.md) and '
            're-run -- the whole model rebuilds from the PARAMS block.\n'
            '3. Verify rear-wall port offsets against the real Pi 4B '
            'before printing (PORT table in PARAMS).\n\n'
            'Closure: M3 screws through the front panel into the rim '
            'bosses (self-tap or heat-set inserts). Pi mount: %s.' %
            (D, PI_MOUNT))

    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))