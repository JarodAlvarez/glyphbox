# GLYPHBOX — Console Case (3D Printable)

Parametric, print-ready case for the physical GLYPHBOX console, translated
from the cardboard prototype. Built the same way as the controller shell in
`~/Documents/glyphbox-controller/fusion-shell/`:

1. **`build_console_case.py`** — the source of truth. A Fusion 360 Python
   script (adsk API): run it in Fusion to build two bodies in the active
   design, then export STLs.
2. **`build_console_stl.py`** — a local re-implementation that reads the same
   PARAMS (single source of truth), emits watertight print-ready STLs,
   GLBs for Quick Look, and runs interference checks against placeholder
   component models.

> **Start here:** `measures.md` is the checklist of cardboard-prototype
> measurements. Every `TBD-cardboard` value in the PARAMS defaults to the
> fabrication brief's target; replace them with your real numbers.

## Decisions locked in (from the design session)

| Question | Decision |
|---|---|
| Display | **OSOYOO 3.5" HDMI LCD touch screen** (board ≈86×56×12, view 73.4×49) — matches the "OSOYOO display" scaler compensation in `src/renderer.c` under `PLATFORM_PI_HDMI` |
| Card presentation | **Internal slot, card face-down** over the camera (the signature look: 120×5 opening, green LED under the upper lip) |
| Controller dock | **Front recess below the card slot** — oval indentation matching the fabricated puck (**117.85×62.34×15.29 mm** — measured from its printed shell STLs), single centered magnet, no connectors |
| Deliverable | Both: Fusion script + local STL/GLB builder |
| Source of truth | **The cardboard prototype**, not the March brief's spec envelope. Its validated camera-to-card distance and layout override the brief's guesses |

## Workflow

```bash
# 1. Fill in measures.md from the cardboard prototype
# 2. Edit the PARAMS block in build_console_case.py with the measured values

# 3. Local verification (no Fusion needed):
python3 -m venv .venv
.venv/bin/pip install trimesh manifold3d shapely numpy
.venv/bin/python build_console_stl.py
#   -> stl/glyphbox_front_shell.stl, glyphbox_rear_shell.stl, assembly.glb

# 4. In Fusion 360 (optional, same geometry):
#    Utilities -> Scripts and Add-Ins -> Scripts -> Run build_console_case.py
#    Then export front/rear bodies as STL.
```

## Coordinate frame

Origin = **bottom-center of the front face**. X = width (case centered at
x=0), Y = height (y=0 is the floor), Z = depth (z=0 is the front panel outer
face, rear wall at z=`EXTERIOR_D`). Two bodies that close flush at z=`FRONT_T`:

- **FrontShellBody** — the front panel slab (display window, card slot
  opening, controller dock recess, LED channel, M3 closure holes).
- **RearShellBody** — back + sides + floor + ceiling (cavity cut, Pi
  standoffs, camera bay + bracket, speaker well + grille, rear/side wall
  cutouts, top vents).

## Known placeholders (verify before printing — same culture as the
controller project's `SCREW_PILOT_DIA`)

- Rear-wall port positions (USB-C, 2× micro-HDMI) and the left-wall USB-A
  strip are **approximate Pi 4B connector offsets**. Measure your Pi during
  fit-check and update the port table.
- `CAM_LENS_STACK`, display board dims — verify with calipers on the real
  parts.
- Fan recess (`FAN_OPTION`) defaults off (vent slots only) — switch on if
  you run a Pi 5.
- The dock recess is the ONE feature already verified against real prints:
  `build_console_stl.py` loads the fabricated controller shells
  (top+bottom STL from `~/Documents/glyphbox-controller/fusion-shell/stl/`)
  and fits them into the recess — currently 0.000% interference.
- Real fit-check STEP files (Pi, camera, display) can be added to
  `build_console_stl.py` interference checks once you have them (the
  controller project uses the same pattern with `glyphbox-controller.step`).

## Print settings (from the fabrication brief)

PETG or ASA, 0.15 mm layers for exterior faces, 3 mm walls, M3 heat-set
inserts in the rim bosses, M2.5 self-tappers for the Pi standoffs. Print face
down with the panel flat for clean cutouts.