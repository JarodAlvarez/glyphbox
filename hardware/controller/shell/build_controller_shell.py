"""
Glyphbox controller shell generator.

Run via Fusion 360 -> Utilities -> Scripts and Add-Ins -> Scripts -> Run.

Builds two bodies in the active design's root component (BottomShellBody
and TopShellBody -- not sub-components, so this works in both "Part" and
"Assembly" type Fusion documents):
  - BottomShellBody (back half: standoffs the PCB rests on, screw
    clearance holes, magnet pocket)
  - TopShellBody (front half: D-pad cross cutout, A/B button holes,
    micro-USB notch, screw pilot bosses)

NONE of the membrane posts, collars or ribs are built by this script.
They come from two pre-positioned meshes in reference-extracts/, both
extracted directly out of the Lensless GBP reference shell rather than
parametrically approximated (earlier attempts at approximating them never
matched the real part):
  - dpad_bracket_positioned.stl : D-pad collar + cross plate + 2 posts
  - ab_bracket_positioned.stl   : A/B housings + rib + 2 posts
Insert Mesh each (units = mm), leave them where they land, and
boolean-Join onto TopShellBody. See the run() completion message.

The two shells close with M2.5 screws through the existing PCB mounting
holes: a clearance hole up through the bottom shell's standoff into a
blind pilot boss in the top shell.

The shell is built centered on the origin (PCB_CENTER_X/Y = 0,0) so it
lands in the middle of the Fusion viewport. To bring in the real PCB for
fit-checking, insert glyphbox-controller.step and translate it by
(-150.358, +101.445, 0) -- a pure translation, no rotation or mirroring
(see _to_local() for why that works out so cleanly).

All dimensions are in mm. Everything you'd plausibly need to tune before
printing is collected in the PARAMS section below -- nothing else in the
file should need touching for a first pass.

UNITS FIX (2026-07-17): earlier versions of this script passed raw mm
numbers straight to Point3D.create() / addByCenterRadius() /
ValueInput.createByReal(), which Fusion's API always interprets in its
internal unit -- centimeters -- regardless of the document's display
unit. That built everything at 10x the intended size. Every length value
now goes through mm()/pt()/mmv() (defined right after the imports) to
convert mm -> cm before it reaches the API. If you have bodies from a
version of this script predating this fix, delete them before re-running.

KNOWN PLACEHOLDERS -- verify these once you have real parts in hand:
  - STANDOFF_H: based on a direct caliper measurement (4.0mm pin
    protrusion below the assembled Glyphbox PCB) plus 0.3mm margin.
    Solid unless the measurement changes.
  - SCREW_PILOT_DIA: sized for M2.5 self-tapping directly into printed
    plastic. Switch to a heat-set-insert hole size if you go that route.
  - BUTTON_CUTOUT_CLEARANCE / DPAD_CUTOUT_CLEARANCE: added on top of the
    reference GBP shell's hole dimensions for our own fit margin.
  - The ceiling height now comes from the reference's own front-shell
    thickness (REF_FRONT_SHELL_THICKNESS), so the membrane posts fit at
    full height. That leaves ~2.5mm of air above the Pico, more than it
    needs -- if you'd rather have a slimmer controller than exactly
    reference-height posts, this is the trade-off to revisit.
"""

import adsk.core
import adsk.fusion
import traceback
import math

# Fusion's Python API always interprets raw length numbers -- Point3D
# coordinates, sketchCircle radii, ValueInput.createByReal() for distances --
# in its internal unit, which is CENTIMETERS, regardless of the document's
# display unit. Every dimension in this script is authored in mm, so all of
# it is funneled through mm()/pt()/mmv() below to convert. Do NOT apply this
# to angles -- Fusion takes those in radians, which need no conversion.

def mm(v):
    return v * 0.1


def pt(x, y, z=0.0):
    return adsk.core.Point3D.create(mm(x), mm(y), mm(z))


def mmv(v):
    return adsk.core.ValueInput.createByReal(mm(v))


# ---------------------------------------------------------------------------
# PARAMS
# ---------------------------------------------------------------------------

# PCB reference (measured from glyphbox-controller.step, in the PCB's own
# native sketch frame, centered at _PCB_NATIVE_CENTER). The shell itself is
# built centered at the origin instead so it lands in the middle of the
# Fusion viewport -- every absolute position measured from the PCB's native
# frame is converted via _to_local() as it's defined below.
PCB_LENGTH = 114.047
PCB_WIDTH = 58.536
_PCB_NATIVE_CENTER = (150.358, 101.445)
PCB_CENTER_X = 0.0
PCB_CENTER_Y = 0.0
PCB_THICKNESS = 1.6


def _to_local(kicad_x, kicad_y):
    """Convert a KiCad-frame coordinate to this shell's local frame.

    KiCad's Y axis points DOWN (smaller y = physically up -- e.g. the D-pad's
    UP switch is at y=92.5 while DOWN is at y=110.3), but Fusion's Y points
    UP. So Y must be negated, not just offset. Without the negation the whole
    shell comes out mirrored top-to-bottom: mounting holes at the top and the
    USB port at the bottom, the reverse of the real board.

    Cross-check: with this negation, aligning glyphbox-controller.step to
    this shell is a pure translation of (-150.358, +101.445, 0) with no
    mirroring -- the STEP's native Y is already -(kicad_y), so
    local_y = -(kicad_y - c) = native_y + c.
    """
    return (kicad_x - _PCB_NATIVE_CENTER[0], _PCB_NATIVE_CENTER[1] - kicad_y)

# Shell construction
FIT_CLEARANCE = 0.3        # gap between PCB edge and inner shell wall
WALL_T = 1.6               # nominal wall thickness everywhere
# Standoff height. CONFIRMED: the soldered pins protrude exactly 4.0mm below
# the underside of the Glyphbox PCB, so 4.3mm of standoff leaves a 0.30mm
# gap. Verified against the real pin geometry in PICO_PinsDown.STEP (40 pins,
# 0.8mm square posts, rows 17.78mm apart at X = -8.94 / +8.84) -- those clear
# both the floor and the magnet backing boss.
#
# Note that PICO_PinsDown.STEP models UNTRIMMED headers, which stand 9.0mm
# below the Pico's own board = 7.405mm below ours, and would foul the floor
# by 3.10mm. If a future build uses untrimmed pins, STANDOFF_H must go to
# 7.70mm, adding 3.4mm to the overall thickness.
STANDOFF_H = 4.0 + 0.3  # confirmed protrusion + margin

# Mounting holes (from PCB spec / STEP, KiCad frame). The two shells close
# with M2.5 screws through these: the bottom shell has a bearing standoff
# the PCB rests on with a clearance hole straight through, and the top
# shell has a matching boss with a blind pilot hole the screw threads into.
MOUNT_HOLES = [_to_local(123.5, 122.5), _to_local(174.5, 122.5)]
BOSS_OD = 5.5
SCREW_CLEARANCE_DIA = 2.8  # through the bottom shell -- screw passes freely
SCREW_PILOT_DIA = 2.1      # blind pilot in the top boss, for M2.5 self-tapping
                           # into printed plastic (placeholder, see docstring)
SCREW_PILOT_DEPTH = 5.0

# Pico footprint (from the PCB STEP, converted to this shell's local
# frame) -- needed to keep the D-pad collar clear of it.
PICO_X_RANGE = (139.810 - _PCB_NATIVE_CENTER[0], 160.810 - _PCB_NATIVE_CENTER[0])
PICO_Y_RANGE = (_to_local(0, 124.650)[1], _to_local(0, 72.350)[1])

# D-pad (measured from Lensless GBP reference shell: 21x21mm cross, 7mm arms)
DPAD_CENTER = _to_local(122.589, 101.430)
DPAD_SPAN = 21.0
DPAD_ARM_W = 7.0
DPAD_CUTOUT_CLEARANCE = 0.4   # added to both span and arm width for our own fit margin

# A/B buttons (measured from Lensless GBP reference shell: 9.75mm dia)
BTN_A = _to_local(185.303, 101.430)
BTN_B = _to_local(171.459, 101.430)
BTN_DIA = 9.75
BUTTON_CUTOUT_CLEARANCE = 0.4  # added to diameter for our own fit margin

# Membrane locating posts are NOT built parametrically at all anymore.
# Both the D-pad and A/B posts (and the collars/ribs they sit on) come from
# geometry extracted directly out of the Lensless GBP reference mesh --
# see reference-extracts/ and the run() completion message. Earlier versions
# approximated them with tapered extrudes; that never matched the real part.

# MICRO-USB cutout (confirmed -- the Pico on this board is an original
# Pico with a micro-USB port, NOT USB-C; the 8.0 x 2.589mm shell matches a
# micro-USB B receptacle, whereas USB-C would be 8.94 x 3.26mm).
# Connector shell measured off the Pico in glyphbox-controller.step:
# 8.0mm wide x 2.589mm tall, spanning Z 2.706..5.295 (PCB bottom = Z 0).
# Its outer face sits at Y=29.095, i.e. 2.073mm back from the shell's outer
# surface -- see the plug-seating note in the docstring.
USB_CLEARANCE = 0.7
USB_CENTER_X = PCB_CENTER_X
USB_WIDTH = 8.0 + 2 * USB_CLEARANCE
USB_Z_BOTTOM = 2.706 - USB_CLEARANCE
USB_Z_TOP = 5.295 + USB_CLEARANCE
USB_HEIGHT = USB_Z_TOP - USB_Z_BOTTOM

# Plug-seating counterbore. The receptacle face sits 2.073mm behind the
# shell's outer surface (1.6mm wall + 0.473mm air gap). A micro-USB plug
# only has ~1.0-1.7mm of metal shell to spare once it's latched, so on a
# plain 1.6mm wall the cable's overmold bottoms out ~0.4-1.1mm before the
# plug seats. Measured cable: 6.0mm of exposed shell -> needs ~0.6mm of
# relief. This shallow pocket in the OUTER face lets the overmold sink in.
# 1.0mm deep leaves a 0.6mm rim around the port.
# Widen USB_CB_WIDTH/HEIGHT if your cable's overmold is larger than this.
USB_CB_WIDTH = 12.0
USB_CB_HEIGHT = 6.0
USB_CB_DEPTH = 1.0

# Pico height (from STEP). NOTE: the Pico is no longer what sets the
# ceiling height -- the membrane-post thickness budget below is taller and
# governs. This is kept to verify the Pico still clears.
PICO_TOP_Z = 5.295

# Front-shell thickness budget, measured off the Lensless reference:
#   outer cosmetic face -> collar bottom face : 4.993mm
#   collar bottom -> membrane post tip        : 2.800mm  (the full post)
#   total                                     : 7.793mm
# The reference's posts reach all the way to the plane its PCB butts
# against, so for full-height posts our post tip must land on our PCB's top
# surface (Z = PCB_THICKNESS) and the outer face must sit a full 7.793mm
# above that. With the old 7.395mm outer face the tip landed at Z=-0.4,
# i.e. 2.0mm *inside* the PCB -- which is why every earlier attempt had to
# clip the posts short. Raising the shell 2.0mm fixes the root cause.
REF_FRONT_SHELL_THICKNESS = 7.793
REF_POST_BELOW_COLLAR = 2.800

# Magnet (10mm x 2mm N42 disc, flush-recessed into the bottom exterior).
# The pocket is BLIND: 2.0mm of pocket is deeper than the 1.6mm floor, so a
# local backing boss is added on the inside of the floor to close it off.
# Without that the pocket breaks through into the cavity and the magnet has
# nothing behind it. Backing thickness is what's left after the pocket:
#   local floor = WALL_T + MAGNET_BOSS_H = 1.6 + 1.2 = 2.8mm
#   backing     = 2.8 - MAGNET_DEPTH     = 0.8mm
MAGNET_DIA = 10.0
MAGNET_DEPTH = 2.0
MAGNET_BACKING = 0.8
MAGNET_CENTER = (PCB_CENTER_X, PCB_CENTER_Y)
# Boss OD is kept at 13mm so it stays clear of the Pico's header pins, which
# come down to Z=-4.0 at X = -8.94 and +8.84: a 6.5mm radius leaves ~2.3mm.
MAGNET_BOSS_DIA = 13.0

# ---------------------------------------------------------------------------
# Derived geometry
# ---------------------------------------------------------------------------

INNER_LENGTH = PCB_LENGTH + 2 * FIT_CLEARANCE
INNER_WIDTH = PCB_WIDTH + 2 * FIT_CLEARANCE
OUTER_LENGTH = INNER_LENGTH + 2 * WALL_T
OUTER_WIDTH = INNER_WIDTH + 2 * WALL_T

# Ceiling heights, driven by the membrane-post thickness budget above.
# TOP_OUTER_Z is the front cosmetic face; the imported collar meshes are
# pre-positioned to land their own outer faces exactly here.
TOP_OUTER_Z = PCB_THICKNESS + REF_FRONT_SHELL_THICKNESS   # 9.393
TOP_INNER_Z = TOP_OUTER_Z - WALL_T                        # 7.793

# Back-compat aliases (older names used throughout the build functions).
PICO_CHAN_OUTER_Z = TOP_OUTER_Z
PICO_CHAN_INNER_Z = TOP_INNER_Z

# Sanity: the Pico must still fit under the raised ceiling.
PICO_ACTUAL_CLEARANCE = TOP_INNER_Z - PICO_TOP_Z           # 2.498

# How far the magnet backing boss stands proud of the cavity floor.
MAGNET_BOSS_H = MAGNET_DEPTH + MAGNET_BACKING - WALL_T     # 1.2


def stadium_profile_sketch(sketch, cx, cy, length, width):
    """Draw a stadium (pill) outline as lines+arcs in one closed profile."""
    r = width / 2.0
    half_straight = (length - width) / 2.0
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs

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


def cross_profile_sketch(sketch, cx, cy, span, arm_w):
    """Draw a 12-point plus/cross polygon as one closed profile."""
    hs = span / 2.0
    ha = arm_w / 2.0
    pts = [
        (cx + ha, cy + hs), (cx + ha, cy + ha), (cx + hs, cy + ha),
        (cx + hs, cy - ha), (cx + ha, cy - ha), (cx + ha, cy - hs),
        (cx - ha, cy - hs), (cx - ha, cy - ha), (cx - hs, cy - ha),
        (cx - hs, cy + ha), (cx - ha, cy + ha), (cx - ha, cy + hs),
    ]
    lines = sketch.sketchCurves.sketchLines
    for i in range(len(pts)):
        p1 = pt(pts[i][0], pts[i][1])
        p2 = pt(pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1])
        lines.addByTwoPoints(p1, p2)


def extrude_new_body(comp, profile, start_z, height):
    """Extrude a new body and return the created BRepBody directly."""
    extrudes = comp.features.extrudeFeatures
    ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, mmv(height))
    ext_input.startExtent = adsk.fusion.OffsetStartDefinition.create(mmv(start_z))
    feature = extrudes.add(ext_input)
    return feature.bodies.item(0)


def extrude_join(comp, profile, start_z, height, target_body):
    extrudes = comp.features.extrudeFeatures
    ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input.setDistanceExtent(False, mmv(height))
    ext_input.startExtent = adsk.fusion.OffsetStartDefinition.create(mmv(start_z))
    ext_input.participantBodies = [target_body]
    return extrudes.add(ext_input)


def extrude_cut(comp, profile, start_z, height, target_body):
    extrudes = comp.features.extrudeFeatures
    ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input.setDistanceExtent(False, mmv(height))
    ext_input.startExtent = adsk.fusion.OffsetStartDefinition.create(mmv(start_z))
    ext_input.participantBodies = [target_body]
    return extrudes.add(ext_input)


def largest_profile(sketch):
    profs = sketch.profiles
    best, best_area = None, -1.0
    for i in range(profs.count):
        p = profs.item(i)
        props = p.areaProperties()
        if props.area > best_area:
            best, best_area = p, props.area
    return best


def build_bottom_shell(root):
    # Built directly in the root component (as a separate body, not a
    # sub-component/occurrence) so this works in both "Part" and "Assembly"
    # type Fusion documents -- Part documents reject addNewComponent().
    comp = root
    xy = comp.xYConstructionPlane

    # Outer stadium, floor to top rim
    sk_outer = comp.sketches.add(xy)
    stadium_profile_sketch(sk_outer, PCB_CENTER_X, PCB_CENTER_Y, OUTER_LENGTH, OUTER_WIDTH)
    body = extrude_new_body(comp, largest_profile(sk_outer), -(WALL_T + STANDOFF_H), WALL_T + STANDOFF_H)
    body.name = 'BottomShellBody'

    # Inner cavity, cut from -STANDOFF_H upward through the floor thickness
    # (this hollows out everything above the floor, leaving a WALL_T-thick floor slab)
    sk_inner = comp.sketches.add(xy)
    stadium_profile_sketch(sk_inner, PCB_CENTER_X, PCB_CENTER_Y, INNER_LENGTH, INNER_WIDTH)
    extrude_cut(comp, largest_profile(sk_inner), -STANDOFF_H, STANDOFF_H, body)

    # Standoff posts (bearing boss the PCB rests on) + a screw clearance
    # hole straight through the boss and the shell floor, so an M2.5 screw
    # can pass up through the PCB into the top shell's pilot boss.
    for (mx, my) in MOUNT_HOLES:
        sk_boss = comp.sketches.add(xy)
        sk_boss.sketchCurves.sketchCircles.addByCenterRadius(pt(mx, my), mm(BOSS_OD / 2.0))
        extrude_join(comp, largest_profile(sk_boss), -STANDOFF_H, STANDOFF_H, body)

        sk_hole = comp.sketches.add(xy)
        sk_hole.sketchCurves.sketchCircles.addByCenterRadius(
            pt(mx, my), mm(SCREW_CLEARANCE_DIA / 2.0))
        extrude_cut(comp, largest_profile(sk_hole),
                    -(WALL_T + STANDOFF_H), WALL_T + STANDOFF_H, body)

    # Magnet backing boss: local thickening on the INSIDE of the floor so the
    # magnet pocket below can be blind instead of breaking through. Must be
    # added before the pocket is cut.
    sk_mboss = comp.sketches.add(xy)
    sk_mboss.sketchCurves.sketchCircles.addByCenterRadius(
        pt(MAGNET_CENTER[0], MAGNET_CENTER[1]), mm(MAGNET_BOSS_DIA / 2.0))
    extrude_join(comp, largest_profile(sk_mboss), -STANDOFF_H, MAGNET_BOSS_H, body)

    # Magnet pocket, recessed flush into the exterior (bottom-facing) face.
    # Blind, thanks to the boss above: MAGNET_BACKING of material is left
    # behind the magnet so it seats against a solid face and can't push
    # through into the cavity.
    sk_mag = comp.sketches.add(xy)
    sk_mag.sketchCurves.sketchCircles.addByCenterRadius(
        pt(MAGNET_CENTER[0], MAGNET_CENTER[1]), mm(MAGNET_DIA / 2.0))
    extrude_cut(comp, largest_profile(sk_mag), -(WALL_T + STANDOFF_H), MAGNET_DEPTH, body)

    return comp, body


def build_top_shell(root):
    comp = root
    xy = comp.xYConstructionPlane

    # Outer stadium, uniform ceiling height everywhere (flush front, no bump --
    # the whole ceiling is tall enough to clear the Pico, not just a channel
    # over its footprint. This trades a bit of extra thickness over the
    # button/D-pad zone for a smooth, flat front face.)
    sk_outer = comp.sketches.add(xy)
    stadium_profile_sketch(sk_outer, PCB_CENTER_X, PCB_CENTER_Y, OUTER_LENGTH, OUTER_WIDTH)
    body = extrude_new_body(comp, largest_profile(sk_outer), 0, PICO_CHAN_OUTER_Z)
    body.name = 'TopShellBody'

    # Inner cavity, hollowed from the bottom rim up to the ceiling's inner face
    sk_inner = comp.sketches.add(xy)
    stadium_profile_sketch(sk_inner, PCB_CENTER_X, PCB_CENTER_Y, INNER_LENGTH, INNER_WIDTH)
    extrude_cut(comp, largest_profile(sk_inner), 0, PICO_CHAN_INNER_Z, body)

    # D-pad cross cutout, through the ceiling
    sk_dpad = comp.sketches.add(xy)
    cross_profile_sketch(sk_dpad, DPAD_CENTER[0], DPAD_CENTER[1],
                          DPAD_SPAN + DPAD_CUTOUT_CLEARANCE, DPAD_ARM_W + DPAD_CUTOUT_CLEARANCE)
    extrude_cut(comp, largest_profile(sk_dpad), 0, PICO_CHAN_OUTER_Z, body)

    # A/B button holes, through the ceiling
    for (bx, by) in (BTN_A, BTN_B):
        sk_btn = comp.sketches.add(xy)
        sk_btn.sketchCurves.sketchCircles.addByCenterRadius(
            pt(bx, by), mm((BTN_DIA + BUTTON_CUTOUT_CLEARANCE) / 2.0))
        extrude_cut(comp, largest_profile(sk_btn), 0, PICO_CHAN_OUTER_Z, body)

    # Screw bosses with blind pilot holes, reaching down from the ceiling to
    # the PCB's top surface so the boss bottoms out on the board and the
    # screw (up through the bottom shell) clamps the stack together.
    for (mx, my) in MOUNT_HOLES:
        boss_height = TOP_INNER_Z - PCB_THICKNESS
        sk_boss = comp.sketches.add(xy)
        sk_boss.sketchCurves.sketchCircles.addByCenterRadius(pt(mx, my), mm(BOSS_OD / 2.0))
        extrude_join(comp, largest_profile(sk_boss), PCB_THICKNESS, boss_height, body)

        sk_pilot = comp.sketches.add(xy)
        sk_pilot.sketchCurves.sketchCircles.addByCenterRadius(
            pt(mx, my), mm(SCREW_PILOT_DIA / 2.0))
        extrude_cut(comp, largest_profile(sk_pilot), PCB_THICKNESS, SCREW_PILOT_DEPTH, body)

    # micro-USB notch through the TOP end wall (+Y -- the USB end of the board;
    # see _to_local() for why +Y is the top). The cut is SYMMETRIC about the
    # wall's outer-face plane: a one-sided extrude here is a coin flip on
    # whether Fusion's offset-plane normal points into the wall or out into
    # open air, and when it pointed outward the cut silently did nothing and
    # left the case fully enclosed. Symmetric always crosses the wall.
    outer_y_max = PCB_CENTER_Y + OUTER_WIDTH / 2.0
    plane_in = comp.constructionPlanes.createInput()
    plane_in.setByOffset(comp.xZConstructionPlane, mmv(outer_y_max))
    usb_plane = comp.constructionPlanes.add(plane_in)
    sk_usb = comp.sketches.add(usb_plane)
    sk_usb.sketchCurves.sketchLines.addTwoPointRectangle(
        pt(USB_CENTER_X - USB_WIDTH / 2.0, USB_Z_BOTTOM),
        pt(USB_CENTER_X + USB_WIDTH / 2.0, USB_Z_TOP))
    extrudes = comp.features.extrudeFeatures
    usb_input = extrudes.createInput(largest_profile(sk_usb), adsk.fusion.FeatureOperations.CutFeatureOperation)
    usb_input.setDistanceExtent(True, mmv(WALL_T + 2.0))   # True == symmetric
    usb_input.participantBodies = [body]
    extrudes.add(usb_input)

    # Counterbore in the outer face so the plug's overmold can sink in far
    # enough for the connector to latch. Symmetric again, so it removes
    # USB_CB_DEPTH of wall inward and the same amount of empty air outward --
    # the outward half is a no-op, which makes this immune to the offset
    # plane's normal direction.
    sk_cb = comp.sketches.add(usb_plane)
    usb_mid_z = (USB_Z_BOTTOM + USB_Z_TOP) / 2.0
    sk_cb.sketchCurves.sketchLines.addTwoPointRectangle(
        pt(USB_CENTER_X - USB_CB_WIDTH / 2.0, usb_mid_z - USB_CB_HEIGHT / 2.0),
        pt(USB_CENTER_X + USB_CB_WIDTH / 2.0, usb_mid_z + USB_CB_HEIGHT / 2.0))
    cb_input = extrudes.createInput(largest_profile(sk_cb), adsk.fusion.FeatureOperations.CutFeatureOperation)
    cb_input.setDistanceExtent(True, mmv(USB_CB_DEPTH))
    cb_input.participantBodies = [body]
    extrudes.add(cb_input)

    return comp, body


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

        _, bottom_body = build_bottom_shell(root)
        _, top_body = build_top_shell(root)

        ui.messageBox(
            'Built BottomShellBody and TopShellBody, centered on the origin.\n\n'
            'DELETE ANY BODIES FROM A PREVIOUS RUN FIRST -- this version '
            'changes the shell orientation (Y-flip fix) and raises the front '
            'shell 2mm, so old bodies will not line up with the new ones.\n\n'
            'Front shell outer face is now at Z=%.3f (was 7.395), raised so '
            'the reference membrane posts fit at full height.\n\n'
            'NEXT STEPS in Fusion:\n'
            '1. Insert Mesh reference-extracts/dpad_bracket_positioned.stl '
            'and reference-extracts/ab_bracket_positioned.stl (units = mm). '
            'Both are already positioned in this shell frame -- do not move '
            'them. Boolean-Join each onto TopShellBody. They carry the '
            'collars, ribs and ALL membrane posts, taken straight from the '
            'Lensless reference mesh.\n'
            '2. To check fit, insert glyphbox-controller.step and translate '
            'it by (-150.358, +101.445, 0). That is a pure translation -- no '
            'rotation or mirroring. It contains the PCB and the Pico body '
            '(without header pins).\n\n'
            'Closure is M2.5 screws up through the bottom shell into pilot '
            'bosses in the top shell. Verify SCREW_PILOT_DIA against your '
            'actual screws before printing.' % TOP_OUTER_Z)

    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
