"""GLYPHBOX console case -- parametric model, STL export and fit checks.

Single source of truth for the printable case. Edit the PARAMS block and
re-run; everything else is derived.

    .venv/bin/python glyphbox_case.py        # STLs + fit report
    .venv/bin/python render.py               # PNG previews

Frame (mm): X = width, +X is the viewer's right when facing the console.
            Y = depth, y=0 is the front outer face, y=D the rear outer face.
            Z = height, z=0 is the outer bottom.

Parts written to stl/:
    glyphbox_body.stl        front + sides + top + floor, open at the rear
    glyphbox_rear_panel.stl  screws into six bosses, carries the power jack
    glyphbox_screen_clip.stl print 5 -- 3 hold the display, 2 hold the speaker
    glyphbox_usb_clamp.stl   holds the controller USB socket from inside
    glyphbox_faceplate.stl   print in black, glue into the front recess
"""
import math
import os

import numpy as np
import shapely.affinity as sa
import shapely.geometry as sg
import shapely.ops as so
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'stl')
IN = 25.4

# ---------------------------------------------------------------------------
# PARAMS  (M = measured by Jarod on the cardboard prototype, A = assumed)
# ---------------------------------------------------------------------------
W = 140.0                 # M  5.5 in box width
T = 3.0                   # A  wall thickness
R = 8.0                   # A  outer corner radius (mockup styling)

# Card + camera (the validated scan geometry)
CARD_W, CARD_L = 2 * IN, 3 * IN   # M  card 2 x 3 in, short edge leads
CARD_T = 3.0              # A  "standard cardboard thickness"
CARD_FLOOR_H = 5 * IN     # M  card underside above the inside floor
CARD_PROTRUDE = 8.0       # A  left outside the slot to grab ("not much")
SLOT_CLEAR_W = 4.2        # A  total side play in the slot
SLOT_CLEAR_H = 2.0        # A  play above the card
CAM_STANDOFF = 3.0        # A  camera PCB above the floor: lies nearly flat, room for the ribbon connector underneath
CAM_STACK = 11.5          # A  lens top above the camera PCB underside
CAM_LENS_H = CAM_STANDOFF + CAM_STACK   # lens top above the inside floor
CAM_LENS_OFF_Y = 0.0      # A  lens centre vs centre of the 4 mounting holes
LED_WALL_W = 90.0         # A  LED strip face width (strip is adhesive)
LED_WALL_H = 15.0         # A  LED strip face height, just below the card

# Display (OSOYOO 3.5in HDMI)
DISP_W, DISP_H = 83.0, 56.0   # M  glass / board outline
DISP_T = 6.0              # M  thickness
DISP_BOTTOM_Z = 5.5 * IN  # M  screen bottom edge above the outer bottom
DISP_CLEAR = 0.75         # A  pocket play per side (no calipers -> generous)
WIN_W, WIN_H = 78.0, 52.0 # A  front window; glass border hides behind the lip
FACE_W, FACE_H = 120.0, 60.0   # A  recessed black faceplate around the screen
FACE_T = 1.2              # A  recess depth = faceplate insert thickness

# Front styling around the screen:
#   'flat'      plain window
#   'faceplate' recessed panel + separate black insert
#   'scoop'     screen set back behind a sloped, body-colour bezel
#   'frame'     raised plate around screen + slot (as in the mockup)
#   'grille'    horizontal grooves flanking the screen
FRONT_STYLE = 'frame'
SCOOP_SETBACK = 5.0       # how far the glass sits behind the normal position
SCOOP_FLARE_X, SCOOP_FLARE_Z = 9.0, 4.0
FRAME_PROUD = 2.0
# Detail cut into the raised frame around the screen:
#   'none'   plain plate
#   'ring'   thin groove tracing the screen window
#   'recess' screen sits in a shallow stepped recess
#   'face'   one groove centred on the plate, bottom run through the card slot
SCREEN_GROOVE = 'face'
GROOVE_W, GROOVE_D = 1.2, 0.8
GRILLE_PITCH, GRILLE_W, GRILLE_D = 5.0, 2.0, 1.0
HDMI_RISE = 1 * IN        # M  right-angle HDMI plug above the PCB top edge
HDMI_BACK = 1 * IN        # M  ... and behind the PCB

# Raspberry Pi 3 -- on the right wall (as in the prototype), HDMI edge up,
# USB/Ethernet facing the rear panel, component side facing inward
PI_L, PI_WD = 85.0, 56.0
PI_Z0 = 16.0              # A  board bottom edge height
PI_USB_CLEAR = 34.0       # A  room between the USB ports and the rear panel for plugs
PI_SD_CLEAR = 4.0         # A  SD card overhang at the front (behind the dock)
PI_STANDOFF = 14.0        # tall: the controller cable's angled plug points toward this wall and needs room to bend

# Controller dock (puck 117.85 x 62.34 x 15.29, from its shell STLs)
PUCK_L, PUCK_W, PUCK_T = 117.85, 62.34, 15.29
DOCK_CLEAR = 0.4          # per side
DOCK_DEPTH = 6.0          # A  recess depth; puck stands ~9 mm proud to grip
DOCK_Z = 58.0             # A  dock centre height
MAG_DIA, MAG_T = 10.0, 2.0    # M  10 x 2 mm discs
PUCK_MAG_PROUD = 4.0      # M  two stacked on the puck back
MAG_SKIN = 1.3            # plastic between the two magnets (print service minimum wall is 0.8)

# Controller USB-A socket: panel-mount extension (HCFeng B0DDH91CWV), flange
# held against the inside of the front wall by a printed clamp frame, so no
# screws show on the front.
USB_X, USB_Z = -36.0, 15.0
USB_NOSE_W, USB_NOSE_H = 17.0, 9.5   # A  opening: admits the socket mouth and a mating plug's overmould
USB_POST_DX = 24.0                   # clamp screw posts, either side of the flange
USB_POST_H = 2.0                     # shorter than the flange so the clamp bites
USB_FLANGE_W, USB_FLANGE_H, USB_BODY_L = 39.0, 13.0, 30.0   # listing drawing
USB_BODY_W, USB_BODY_BELOW = 20.0, 6.5   # A  socket casing behind the flange: width, and extent below the port centre
USB_CLAMP_PLAY = 0.75                # clearance each side of the casing

# Rear panel
PWR_X, PWR_Z = -35.0, 24.0    # A  panel-mount micro-USB position
PWR_HOLE_SPACING = 28.0       # M
PWR_OPEN_W, PWR_OPEN_H = 15.0, 9.0   # A  opening for the jack nose
PANEL_CLEAR = 0.5         # generous: large resin shells can bow at the open rim
RIM_LIP_W, RIM_LIP_D = 3.0, 8.0   # stiffening lip inside the rear opening; the panel seats on it

# Fasteners (self-tapping into printed pilots)
M3_PILOT, M3_CLEAR = 2.6, 3.4
M25_PILOT = 2.1
M2_PILOT = 1.7

# Rubber feet: shallow round recesses in the underside for stick-on bumpers
FOOT_DIA, FOOT_RECESS = 19.0, 1.0      # A  MacBook Pro replacement pads (~0.75 in per listings); recess depth
FOOT_INSET_X, FOOT_INSET_Y = 19.0, 19.0   # centre distance from the side / front / rear faces

# Speaker: Game Boy DMG type, on the inside of the left wall behind a grille
SPK_DIA = 28.0            # A  DMG speaker diameter
SPK_T = 5.0               # A  rim-to-back height where the clips bear (unmeasured)
SPK_Y, SPK_Z = None, 62.0 # centre on the left wall (Y defaults to mid-depth)
SPK_LOGO_U = 2.4          # grille = the logo mark; unit size (mark is 9 units wide)
SPK_LOGO_BRIDGE = 1.6     # solid left at each ring corner so the centre stays attached

SEAM_Z = 112.0            # cosmetic groove between dock and slot (mockup)
SEAM_W, SEAM_D = 1.2, 0.8
LOGO_DEPTH = 0.6
REAR_TEXT = ['Designed by Greedo', 'in San Diego', 'Model GLB-001']
REAR_TEXT_FONT = 'DejaVu Sans'   # open letter shapes: smallest size that keeps every ridge >= 0.8 mm
REAR_TEXT_GAP = 1.1              # mm of solid between letters   # rear-panel engraving
REAR_TEXT_SIZE, REAR_TEXT_Z, REAR_ENGRAVE_DEPTH = 4.5, 103.0, 0.5   # cap height (mm); 4.5 is the practical minimum

# ---------------------------------------------------------------------------
# Derived
# ---------------------------------------------------------------------------
H = round(DISP_BOTTOM_Z + DISP_H + HDMI_RISE + 2.0 + T, 1)
PI_Y0 = DOCK_DEPTH + 2.5 + PI_SD_CLEAR + 0.5   # SD end of the board (clears the dock)
PI_Y1 = PI_Y0 + PI_L                      # USB end
D = round(PI_Y1 + 2.0 + PI_USB_CLEAR + T, 1)
XI = W / 2 - T                            # inner half width

CARD_Z = T + CARD_FLOOR_H                 # card underside
CARD_END = CARD_L - CARD_PROTRUDE         # y of the card's leading edge
SLOT_W = CARD_W + SLOT_CLEAR_W
SLOT_Z0, SLOT_Z1 = CARD_Z - 0.3, CARD_Z + CARD_T + SLOT_CLEAR_H
CAM_Y = (T + CARD_END) / 2                # lens under the card centre
CAM_PCB_Z = T + CAM_LENS_H - CAM_STACK    # camera PCB underside

DISP_ZC = DISP_BOTTOM_Z + DISP_H / 2
POCK_W, POCK_H = DISP_W + 2 * DISP_CLEAR, DISP_H + 2 * DISP_CLEAR
DOCK_L, DOCK_W = PUCK_L + 2 * DOCK_CLEAR, PUCK_W + 2 * DOCK_CLEAR
DOCK_BACK = DOCK_DEPTH + 2.5              # y of the recess shell's back
MAG_DIMPLE_Y = DOCK_DEPTH + PUCK_MAG_PROUD + 0.5
MAG_BOSS_Y = MAG_DIMPLE_Y + MAG_SKIN + MAG_T + 0.5

BOSS = 9.0
BOSS_XZ = [(sx * (XI - BOSS / 2), z) for sx in (-1, 1)
           for z in (T + BOSS / 2, H / 2, H - T - BOSS / 2)]
PI_HOLES = [(PI_Y0 + 3.5 + dy, PI_Z0 + 3.5 + dz) for dy in (0, 58) for dz in (0, 49)]
CAM_HOLES = [(sx * 10.5, CAM_Y + CAM_LENS_OFF_Y + sy * 6.25)
             for sx in (-1, 1) for sy in (-1, 1)]
CLIP_BOSSES = [(-(POCK_W / 2 + 6.0), DISP_ZC), (POCK_W / 2 + 6.0, DISP_ZC - 12),
               (-28.0, DISP_ZC + POCK_H / 2 + 4.0)]
CLIP_ANGLE = [0, 180, 270]                # which way each clip points (deg)


def DY():
    """y of the surface the display glass rests against."""
    return T + (SCOOP_SETBACK if FRONT_STYLE == 'scoop' else 0.0)


def frustum(cx, cz, w0, h0, y0, w1, h1, y1):
    pts = [(cx + sx * w / 2, y, cz + sz * h / 2) for (w, h, y) in ((w0, h0, y0), (w1, h1, y1))
           for sx in (-1, 1) for sz in (-1, 1)]
    return trimesh.convex.convex_hull(np.array(pts))


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return m


def cyl(axis, a, b, dia, lo, hi):
    """Cylinder along 'x', 'y' or 'z'; (a, b) are the other two coords in
    x,y,z order."""
    m = trimesh.creation.cylinder(radius=dia / 2, height=hi - lo, sections=64)
    mid = (lo + hi) / 2
    if axis == 'x':
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
        m.apply_translation([mid, a, b])
    elif axis == 'y':
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
        m.apply_translation([a, mid, b])
    else:
        m.apply_translation([a, b, mid])
    return m


def prism_xz(poly, y0, y1):
    """Extrude a shapely polygon drawn in the X-Z plane along Y."""
    m = trimesh.creation.extrude_polygon(poly, height=y1 - y0)
    m.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    m.apply_translation([0, y1, 0])
    return m


def prism_yz(poly, x0, x1):
    """Extrude a shapely polygon drawn in the Y-Z plane along X."""
    m = trimesh.creation.extrude_polygon(poly, height=x1 - x0)
    m.apply_transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]))
    return m


def spk_centre():
    return (D / 2 if SPK_Y is None else SPK_Y), SPK_Z


def spk_posts():
    y, z = spk_centre()
    off = SPK_DIA / 2 + 0.3 + 2.2 + 3.75
    return [(y - off, z), (y + off, z)]


def rrect(cx, cz, w, h, r):
    return sg.box(cx - w / 2 + r, cz - h / 2 + r, cx + w / 2 - r, cz + h / 2 - r).buffer(r, quad_segs=24)


def stadium(cx, cz, length, width):
    r = width / 2
    return sg.LineString([(cx - length / 2 + r, cz), (cx + length / 2 - r, cz)]).buffer(r, quad_segs=48)


def union(parts):
    return trimesh.boolean.union(parts, engine='manifold')


def diff(a, cuts):
    return trimesh.boolean.difference([a] + list(cuts), engine='manifold')


def shell_solid(inset):
    """Rounded tower: every edge filleted except the flat rear."""
    r = R - inset
    pts = []
    for sx in (-1, 1):
        for z in (R, H - R):
            for y in (R, D + R):
                s = trimesh.creation.icosphere(subdivisions=3, radius=r)
                pts.append(s.vertices + [sx * (W / 2 - R), y, z])
    hull = trimesh.convex.convex_hull(np.vstack(pts))
    keep = box(-W, W, inset, D + (1 if inset else 0), -1, H + 1)
    return trimesh.boolean.intersection([hull, keep], engine='manifold')


WORDMARK_FONT = '/System/Library/Fonts/Supplemental/Futura.ttc'   # Futura Medium, as in the official lock-up


def mark_polys(x0, z0, u):
    """Official GLYPHBOX mark on its 9 x 11 unit grid; lower-left corner at
    (x0, z0), u = unit size in mm. Rings are 1 unit thick with 1 unit gaps,
    and five 1-unit dots sit one unit below."""
    def sq(cx, cz, half):
        return sg.box(x0 + (cx - half) * u, z0 + (cz - half) * u, x0 + (cx + half) * u, z0 + (cz + half) * u)
    c = (4.5, 6.5)                                     # centre of the square part
    return [sq(*c, 4.5).difference(sq(*c, 3.5)), sq(*c, 2.5).difference(sq(*c, 1.5)), sq(*c, 0.5)] + \
           [sg.box(x0 + 2 * i * u, z0, x0 + (2 * i + 1) * u, z0 + u) for i in range(5)]


def wordmark(cap, text='GLYPHBOX', gap=0.38, family=None):
    """Letter-spaced wordmark; left edge at x=0, baseline at z=0, cap height
    `cap` mm, `gap` between letters as a fraction of the cap height."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    try:
        prop = FontProperties(family=family) if family else FontProperties(fname=WORDMARK_FONT)
        TextPath((0, 0), 'H', size=10, prop=prop)
    except Exception:                                   # font missing: fall back
        prop = FontProperties(family='DejaVu Sans')
    size = cap * 10 / TextPath((0, 0), 'H', size=10, prop=prop).get_extents().y1
    out, x = [], 0.0
    for ch in text:
        if ch == ' ':
            x += 0.9 * cap
            continue
        tp = TextPath((0, 0), ch, size=size, prop=prop)
        g = sg.Polygon()
        for ring in sorted((sg.Polygon(p) for p in tp.to_polygons() if len(p) > 3), key=lambda p: -p.area):
            g = g.symmetric_difference(ring.buffer(0))
        b = g.bounds
        out.append(sa.translate(g, x - b[0], 0))
        x += (b[2] - b[0]) + gap * cap
    # closing fills needle-thin wedges of solid left in acute letter corners
    return so.unary_union(out).buffer(0.46, quad_segs=4).buffer(-0.46, quad_segs=4), x - gap * cap


def logo_polys(x_right, z0, u):
    """Corner lock-up: mark on the left, wordmark to its right, right-aligned
    at x_right with the mark's bottom at z0."""
    cap = 5.0 * u
    text, tw = wordmark(cap)
    x0 = x_right - tw - 3.5 * u - 9 * u
    return mark_polys(x0, z0, u) + [sa.translate(text, x0 + 12.5 * u, z0 + (11 * u - cap) / 2)]


def text_poly(txt, size, weight='bold'):
    """Text as a shapely geometry, baseline at z=0, centred on x=0."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), txt, size=size, prop=FontProperties(family='DejaVu Sans', weight=weight))
    t = sg.Polygon()
    for ring in sorted((sg.Polygon(p) for p in tp.to_polygons() if len(p) > 3), key=lambda p: -p.area):
        t = t.symmetric_difference(ring.buffer(0))
    b = t.bounds
    return sa.translate(t, -(b[0] + b[2]) / 2, 0)


def rear_engraving():
    """Logo mark + text for the rear panel, mirrored in X so it reads
    correctly when looking at the back of the console."""
    polys = mark_polys(-6.75, REAR_TEXT_Z + 8.0, 1.5)                # mark only, 13.5 mm wide
    for i, line in enumerate(REAR_TEXT):
        t, tw = wordmark(REAR_TEXT_SIZE, line, gap=REAR_TEXT_GAP / REAR_TEXT_SIZE, family=REAR_TEXT_FONT)
        polys.append(sa.translate(t, -tw / 2, REAR_TEXT_Z - i * REAR_TEXT_SIZE * 1.75))
    out = []
    for p in polys:
        p = sa.scale(p, xfact=-1, origin=(0, 0))
        out += [g for g in getattr(p, 'geoms', [p]) if g.area > 0.01]
    return out


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
def build_body():
    tub = diff(shell_solid(0), [shell_solid(T)])
    e = 0.5                                     # overlap into walls
    adds = []

    # controller dock shell + magnet boss
    adds.append(prism_xz(stadium(0, DOCK_Z, DOCK_L + 5, DOCK_W + 5), e, DOCK_BACK))
    adds.append(cyl('y', 0, DOCK_Z, MAG_DIA + 6, DOCK_BACK - e, MAG_BOSS_Y))

    # card sleeve: rails, ledges, roof, end stop, LED wall
    sx0, sx1 = SLOT_W / 2, SLOT_W / 2 + 3
    for s in (-1, 1):
        adds.append(box(min(s * sx0, s * sx1), max(s * sx0, s * sx1), T - e, CARD_END, CARD_Z - 2.5, SLOT_Z1 + 2))
        adds.append(box(min(s * (sx0 - 4), s * sx0), max(s * (sx0 - 4), s * sx0), T - e, CARD_END, CARD_Z - 2.5, CARD_Z))
    adds.append(box(-sx1, sx1, T - e, CARD_END + 2.5, SLOT_Z1, SLOT_Z1 + 2))
    adds.append(box(-sx1, sx1, CARD_END, CARD_END + 2.5, CARD_Z - 2.5, SLOT_Z1 + 2))
    adds.append(box(-LED_WALL_W / 2, LED_WALL_W / 2, CARD_END, CARD_END + 2.5,
                    CARD_Z - 2.5 - LED_WALL_H, CARD_Z - 2.5 + e))

    # display pocket: bottom rib, lower side nubs, three clip bosses
    pz0 = DISP_ZC - POCK_H / 2
    adds.append(box(-POCK_W / 2 - 2, POCK_W / 2 + 2, T - e, DY() + DISP_T, SLOT_Z1 + 2 - e, pz0))
    for s in (-1, 1):
        adds.append(box(min(s * POCK_W / 2, s * (POCK_W / 2 + 2)), max(s * POCK_W / 2, s * (POCK_W / 2 + 2)),
                        T - e, DY() + DISP_T, pz0 - e, pz0 + 18))
    for (x, z) in CLIP_BOSSES:
        adds.append(cyl('y', x, z, 7.5, T - e, DY() + DISP_T + 0.3))

    # camera posts, Pi standoffs, rear-panel bosses
    for (x, y) in CAM_HOLES:
        adds.append(cyl('z', x, y, 5.0, T - e, CAM_PCB_Z))
    for (y, z) in PI_HOLES:
        adds.append(cyl('x', y, z, 8.0, XI - PI_STANDOFF, XI + e))
    for (x, z) in BOSS_XZ:
        adds.append(box(x - BOSS / 2 - e, x + BOSS / 2 + e, D - T - 12, D - T,
                        z - BOSS / 2, z + BOSS / 2))

    lip = rrect(0, H / 2, W - 2 * T + 2 * e, H - 2 * T + 2 * e, R - T).difference(
        rrect(0, H / 2, W - 2 * T - 2 * RIM_LIP_W, H - 2 * T - 2 * RIM_LIP_W, 2.0))
    adds.append(prism_xz(lip, D - T - RIM_LIP_D, D - T))      # rear rim stiffener / panel seat
    sy, sz = spk_centre()                        # speaker locating ring + clip posts
    ring = sg.Point(sy, sz).buffer(SPK_DIA / 2 + 2.5, quad_segs=32).difference(
        sg.Point(sy, sz).buffer(SPK_DIA / 2 + 0.3, quad_segs=32))
    adds.append(prism_yz(ring, -XI - e, -XI + 3.0))
    for (py, pz) in spk_posts():
        adds.append(cyl('x', py, pz, 7.5, -XI - e, -XI + SPK_T))
    for sx in (-1, 1):                           # USB socket clamp posts
        adds.append(cyl('y', USB_X + sx * USB_POST_DX, USB_Z, 7.5, T - e, T + USB_POST_H))

    if FRONT_STYLE == 'scoop':                   # thicken the wall behind the bezel
        adds.append(box(-POCK_W / 2 - 2, POCK_W / 2 + 2, T - e, DY(), pz0, pz0 + POCK_H))
    if FRONT_STYLE == 'frame':
        z0f, z1f = SEAM_Z + 6, H - R
        adds.append(prism_xz(rrect(0, (z0f + z1f) / 2, W - 2 * R + 4, z1f - z0f, 6.0), -FRAME_PROUD, e))

    body = union([tub] + adds)

    cuts = []
    y_face = -FRAME_PROUD if FRONT_STYLE == 'frame' else 0.0
    cuts.append(prism_xz(rrect(0, DISP_ZC, WIN_W, WIN_H, 2.0), y_face - 1, DY() + 1))   # screen window
    if FRONT_STYLE == 'faceplate':
        cuts.append(prism_xz(rrect(0, DISP_ZC, FACE_W, FACE_H, 4.0), -1, FACE_T))
    elif FRONT_STYLE == 'scoop':
        lip = DY() - 1.5
        cuts.append(frustum(0, DISP_ZC, WIN_W + 2 * SCOOP_FLARE_X, WIN_H + 2 * SCOOP_FLARE_Z, -0.01,
                            WIN_W, WIN_H, lip))
    elif FRONT_STYLE == 'frame':
        cuts.append(frustum(0, DISP_ZC, WIN_W + 5, WIN_H + 5, y_face - 0.01, WIN_W, WIN_H, y_face + 2.5))

        def groove(cx, cz, w, h, r):
            ring = rrect(cx, cz, w + GROOVE_W, h + GROOVE_W, r + GROOVE_W / 2).difference(
                rrect(cx, cz, w - GROOVE_W, h - GROOVE_W, max(r - GROOVE_W / 2, 0.5)))
            return prism_xz(ring, y_face - 1, y_face + GROOVE_D)
        if SCREEN_GROOVE == 'ring':
            cuts.append(groove(0, DISP_ZC, WIN_W + 8, WIN_H + 8, 6.0))
        elif SCREEN_GROOVE == 'recess':
            cuts.append(prism_xz(rrect(0, DISP_ZC, WIN_W + 9, WIN_H + 9, 6.0), y_face - 1, y_face + 1.2))
        elif SCREEN_GROOVE == 'face':
            # centred on the raised plate, equal margin all round, with the
            # bottom run passing through the middle of the card slot
            pz0, pz1, pw = SEAM_Z + 6, H - R, W - 2 * R + 4
            inset = (SLOT_Z0 + SLOT_Z1) / 2 - pz0
            cuts.append(groove(0, (pz0 + pz1) / 2, pw - 2 * inset, (pz1 - pz0) - 2 * inset, 5.0))
    elif FRONT_STYLE == 'grille':
        n = int(WIN_H // GRILLE_PITCH)
        for i in range(n + 1):
            z = DISP_ZC + (i - n / 2) * GRILLE_PITCH
            for sx in (-1, 1):
                g = stadium(sx * (WIN_W / 2 + 6 + 8), z, 16.0, GRILLE_W)
                cuts.append(prism_xz(g, -1, GRILLE_D))
    cuts.append(prism_xz(stadium(0, DOCK_Z, DOCK_L, DOCK_W), -1, DOCK_DEPTH))      # dock recess
    cuts.append(cyl('y', 0, DOCK_Z, MAG_DIA + 1.5, DOCK_DEPTH - 1, MAG_DIMPLE_Y))  # puck magnet dimple
    cuts.append(cyl('y', 0, DOCK_Z, MAG_DIA + 0.3, MAG_DIMPLE_Y + MAG_SKIN, MAG_BOSS_Y + 1))  # case magnet
    cuts.append(box(-SLOT_W / 2, SLOT_W / 2, -FRAME_PROUD - 1, T + 1, SLOT_Z0, SLOT_Z1))        # card slot
    cuts.append(box(USB_X - USB_NOSE_W / 2, USB_X + USB_NOSE_W / 2, -1, T + 1,
                    USB_Z - USB_NOSE_H / 2, USB_Z + USB_NOSE_H / 2))
    for sx in (-1, 1):
        cuts.append(cyl('y', USB_X + sx * USB_POST_DX, USB_Z, M3_PILOT, 1.5, T + USB_POST_H + 1))
    # speaker grille in the shape of the logo mark. Each ring is four slots
    # that stop short of the corners, so the middle stays attached; the centre
    # square is a through-hole; the five dots sit outside the speaker, so they
    # are engraved rather than cut through.
    u, br = SPK_LOGO_U, SPK_LOGO_BRIDGE
    for half in (4.5 * u, 2.5 * u):
        mid, ext = half - u / 2, half - u - br
        for (cy, cz, hy, hz) in ((0, mid, ext, u / 2), (0, -mid, ext, u / 2), (mid, 0, u / 2, ext), (-mid, 0, u / 2, ext)):
            cuts.append(box(-W / 2 - 1, -XI + 0.5, sy + cy - hy, sy + cy + hy, sz + cz - hz, sz + cz + hz))
    cuts.append(box(-W / 2 - 1, -XI + 0.5, sy - u / 2, sy + u / 2, sz - u / 2, sz + u / 2))
    for i in range(5):
        dy = (i - 2) * 2 * u
        cuts.append(box(-W / 2 - 1, -W / 2 + 0.8, sy + dy - u / 2, sy + dy + u / 2, sz - 6.5 * u, sz - 5.5 * u))
    for (py, pz) in spk_posts():
        cuts.append(cyl('x', py, pz, M3_PILOT, -XI - 1.5, -XI + SPK_T + 1))
    for fx in (-1, 1):                           # rubber-foot recesses
        for fy in (FOOT_INSET_Y, D - FOOT_INSET_Y):
            cuts.append(cyl('z', fx * (W / 2 - FOOT_INSET_X), fy, FOOT_DIA + 0.6, -1, FOOT_RECESS))
    # seam groove (front + both sides)
    cuts.append(diff(box(-W, W, -1, D - 6, SEAM_Z - SEAM_W / 2, SEAM_Z + SEAM_W / 2),
                     [shell_solid(SEAM_D)]))
    for p in logo_polys(60.0, 6.5, 1.0):
        for g in getattr(p, 'geoms', [p]):
            if g.area > 0.01:
                cuts.append(prism_xz(g, -1, LOGO_DEPTH))
    # pilots
    for (x, z) in CLIP_BOSSES:
        cuts.append(cyl('y', x, z, M3_PILOT, DY() + 0.8, DY() + DISP_T + 1))
    for (x, y) in CAM_HOLES:
        cuts.append(cyl('z', x, y, M2_PILOT, 1.3, CAM_PCB_Z + 1))
    for (y, z) in PI_HOLES:
        cuts.append(cyl('x', y, z, M25_PILOT, XI - PI_STANDOFF - 1, XI + 1))
    for (x, z) in BOSS_XZ:
        cuts.append(cyl('y', x, z, M3_PILOT, D - T - 10, D + 1))
    return diff(body, cuts)


def build_panel():
    p = prism_xz(rrect(0, H / 2, W - 2 * T - 2 * PANEL_CLEAR, H - 2 * T - 2 * PANEL_CLEAR,
                       R - T - PANEL_CLEAR), D - T, D)
    cuts = [cyl('y', x, z, M3_CLEAR, D - T - 1, D + 1) for (x, z) in BOSS_XZ]
    cuts.append(box(PWR_X - PWR_OPEN_W / 2, PWR_X + PWR_OPEN_W / 2, D - T - 1, D + 1,
                    PWR_Z - PWR_OPEN_H / 2, PWR_Z + PWR_OPEN_H / 2))
    for s in (-1, 1):
        cuts.append(cyl('y', PWR_X + s * PWR_HOLE_SPACING / 2, PWR_Z, M3_CLEAR, D - T - 1, D + 1))
    for g in rear_engraving():
        cuts.append(prism_xz(g, D - REAR_ENGRAVE_DEPTH, D + 1))
    for i in range(6):                           # vents behind the display
        cuts.append(box(-25, 25, D - T - 1, D + 1, 150 + i * 8, 153 + i * 8))
    for i in range(4):                           # vents beside the Pi
        cuts.append(box(5, 45, D - T - 1, D + 1, 30 + i * 8, 33 + i * 8))
    return diff(p, cuts)


def build_faceplate():
    """Thin insert, printed in black and glued into the front recess so the
    screen reads as one large dark panel."""
    p = prism_xz(rrect(0, DISP_ZC, FACE_W - 0.4, FACE_H - 0.4, 3.8), 0, FACE_T)
    return diff(p, [prism_xz(rrect(0, DISP_ZC, WIN_W, WIN_H, 2.0), -1, FACE_T + 1)])


def build_usb_clamp(placed=False):
    """One-piece fork that presses the USB socket's two flange ears against the
    front wall. Open at the top, so it drops over the socket casing from above
    whatever the casing's height, and never has to pass over the cable's plug.
    Only the casing WIDTH has to be right (USB_BODY_W)."""
    w = 2 * USB_POST_DX + 9
    half = USB_BODY_W / 2 + USB_CLAMP_PLAY
    bottom = -(USB_BODY_BELOW + USB_CLAMP_PLAY)
    m = box(-w / 2, w / 2, 0, 2.5, bottom - 3.5, 8.5)
    m = diff(m, [box(-half, half, -1, 4, bottom, 10)] +
             [cyl('y', sx * USB_POST_DX, 0, M3_CLEAR, -1, 4) for sx in (-1, 1)])
    if placed:
        m.apply_translation([USB_X, T + USB_POST_H + 0.3, USB_Z])
    return m


def build_clip():
    """Flat tab: screw through one end, the other end overlaps the display."""
    m = box(-4.5, 12.0, 0, 2.5, -4.5, 4.5)
    return diff(m, [cyl('y', 0, 0, M3_CLEAR, -1, 4)])


def placed_clips():
    out = []
    for (x, z), a in zip(CLIP_BOSSES, CLIP_ANGLE):
        c = build_clip()
        c.apply_transform(trimesh.transformations.rotation_matrix(math.radians(a), [0, 1, 0]))
        c.apply_translation([x, DY() + DISP_T + 0.3, z])
        out.append(c)
    (y0, z0), (y1, _) = spk_posts()              # two more of the same clip hold the speaker
    for py, turn in ((y0, 90), (y1, -90)):
        c = build_clip()
        c.apply_transform(trimesh.transformations.rotation_matrix(math.radians(turn), [0, 0, 1]))
        c.apply_translation([-XI + SPK_T + 0.3 + (2.5 if turn > 0 else 0), py, z0])
        out.append(c)
    return out


def proxies():
    """Stand-in solids for the real components (fit check + renders)."""
    p = {}
    p['display'] = box(-DISP_W / 2, DISP_W / 2, DY(), DY() + DISP_T, DISP_BOTTOM_Z, DISP_BOTTOM_Z + DISP_H)
    top = DISP_BOTTOM_Z + DISP_H
    p['hdmi_plug'] = box(-4, 18, DY() + DISP_T, DY() + DISP_T + HDMI_BACK, top - 8, top + HDMI_RISE)
    px = XI - PI_STANDOFF                     # board back face; components toward -x
    p['pi'] = union([box(px - 1.6, px, PI_Y0, PI_Y1, PI_Z0, PI_Z0 + PI_WD),
                     box(px - 17.6, px - 1.6, PI_Y1 - 19, PI_Y1 + 2, PI_Z0 + 4, PI_Z0 + 52)])
    # camera (CSI) connector: on the component side, between HDMI and audio jack
    sy, sz = spk_centre()
    p['speaker'] = union([cyl('x', sy, sz, SPK_DIA, -XI, -XI + SPK_T), cyl('x', sy, sz, 16, -XI + SPK_T - 0.5, -XI + SPK_T + 5)])
    # 3.5 mm audio plug in the Pi's jack (on the HDMI edge, pointing up)
    p['audio_plug'] = cyl('z', px - 4.6, PI_Y0 + 53.5, 9.0, PI_Z0 + PI_WD, PI_Z0 + PI_WD + 40)
    p['pi_csi'] = box(px - 7.1, px - 1.6, PI_Y0 + 43.5, PI_Y0 + 46.5,
                      PI_Z0 + PI_WD - 22.5, PI_Z0 + PI_WD - 0.5)
    p['pi_hdmi_plug'] = box(px - 12, px - 1.6, PI_Y0 + 21, PI_Y0 + 43, PI_Z0 + PI_WD - 6, PI_Z0 + PI_WD + 38)
    # controller cable's angled plug in the outer port of a stack: its leg points
    # at the wall (+x), plus ~10 mm for the cable to bend toward the front
    p['ctrl_plug'] = box(px - 1.6 - 12.5 - 4, XI - 10, PI_Y1 + 2, PI_Y1 + 16, PI_Z0 + 6, PI_Z0 + 20)
    p['pi_usb_plugs'] = box(px - 17, px - 2, PI_Y1 + 2, PI_Y1 + 2 + PI_USB_CLEAR - 2, PI_Z0 + 6, PI_Z0 + 50)
    p['camera'] = union([box(-12.5, 12.5, CAM_Y - 12, CAM_Y + 12, CAM_PCB_Z, CAM_PCB_Z + 1.2),
                         box(-4.3, 4.3, CAM_Y - 4.3, CAM_Y + 4.3, CAM_PCB_Z + 1.2, T + CAM_LENS_H)])
    p['card'] = box(-CARD_W / 2, CARD_W / 2, -CARD_PROTRUDE, CARD_END - 0.2, CARD_Z, CARD_Z + CARD_T)
    p['puck'] = union([prism_xz(stadium(0, DOCK_Z, PUCK_L, PUCK_W), DOCK_DEPTH - PUCK_T, DOCK_DEPTH),
                       cyl('y', 0, DOCK_Z, MAG_DIA, DOCK_DEPTH - 0.1, DOCK_DEPTH + PUCK_MAG_PROUD)])
    p['power_jack'] = box(PWR_X - 19, PWR_X + 19, D - T - 1.5 * IN, D - T, PWR_Z - 6.4, PWR_Z + 6.4)
    p['usb_socket'] = union([
        box(USB_X - USB_FLANGE_W / 2, USB_X + USB_FLANGE_W / 2, T, T + 2, USB_Z - USB_FLANGE_H / 2, USB_Z + USB_FLANGE_H / 2),
        box(USB_X - USB_BODY_W / 2, USB_X + USB_BODY_W / 2, T + 2, T + USB_BODY_L, USB_Z - USB_BODY_BELOW, USB_Z + 7.5)])
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = {'glyphbox_body': build_body(), 'glyphbox_rear_panel': build_panel(),
             'glyphbox_screen_clip': build_clip(), 'glyphbox_faceplate': build_faceplate(),
             'glyphbox_usb_clamp': build_usb_clamp()}
    print(f'Envelope  W {W:.1f} x D {D:.1f} x H {H:.1f} mm '
          f'({W / IN:.2f} x {D / IN:.2f} x {H / IN:.2f} in)')
    print(f'Lens-to-card distance {CARD_FLOOR_H - CAM_LENS_H:.1f} mm, lens at y={CAM_Y:.1f}')
    for name, m in parts.items():
        m.export(os.path.join(OUT, name + '.stl'))
        print(f'  {name:22s} watertight={m.is_watertight}  volume={m.volume / 1000:7.1f} cm3  '
              f'bbox={np.round(m.extents, 1)}')
    solids = union([parts['glyphbox_body'], parts['glyphbox_rear_panel'], build_usb_clamp(True)] + placed_clips())
    print('Interference (proxy volume inside printed parts, mm3):')
    for name, m in proxies().items():
        v = trimesh.boolean.intersection([solids, m], engine='manifold').volume
        print(f'  {name:14s} {v:8.2f}  {"OK" if v < 1 else "<-- CLASH"}')


if __name__ == '__main__':
    main()
