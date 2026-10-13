# GLYPHBOX Console Case — Cardboard Prototype Measurements

The 3D-printable case is fully parametric. Every dimension below is a named
parameter in `build_console_case.py`. Measure the **cardboard prototype** once
and fill in the "Measured" column — every value flows straight into the model.

**A few golden rules for measuring:**

- Measure **outside-to-outside** for exterior dims; **inside-to-inside** for openings.
- Take each measurement 2–3 times and average. 0.5 mm matters for sliding-card fit.
- Where the brief gives a target (marked `brief:`), the cardboard value overrides it.
- Use digital calipers if you have them; a ruler is fine for the big boxes.

---

## 1. Exterior envelope (all mm)

| Param | Default (brief) | Measured | Notes |
|---|---|---|---|
| `EXTERIOR_W` | 150 | ____ | Case width, outside face to outside face |
| `EXTERIOR_H` | 200 | ____ | Case height, floor to top |
| `EXTERIOR_D` | 100 | ____ | Case depth, front face to rear wall |
| `WALL_T` / `FRONT_T` | 3 / 3 | ____ | Cardboard is ambiguous — this becomes print wall thickness |

## 2. Front face layout (origin = bottom-center of front face, Y up)

| Param | Default | Measured | Notes |
|---|---|---|---|
| `DISPLAY_CY` | 140 | ____ | **Height of the display board's vertical center** on the front face |
| `DISPLAY_BOARD_W/H/T` | 86 / 56 / 12 | ____ / ____ / ____ | OSOOYOO 3.5" HDMI board — verify these three against your unit |
| `SLOT_CY` | 85 | ____ | **Height of the card slot opening's center** |
| `SLOT_OPEN_H` | 5 | ____ | Card slot opening height (card thickness + play) |
| `SLOT_W` | 120 | ____ | Card slot opening width |
| `SLOT_POCKET_D` | 45 | ____ | How far the card slides into the case before the stop |
| `DOCK_CY` | (derived: below slot) | ____ | Height of the controller dock recess center (optional — only if you want the dock in v1) |

Dock recess is already sized from the **fabricated puck shells** (measured
from `~/Documents/glyphbox-controller/fusion-shell/stl/`): 117.85 × 62.34 ×
15.29 mm, single 10 mm magnet at dead center. The case recess is 118.4 ×
62.8 × 2 mm with one centered magnet pocket — verify the puck still docks
flush once you have it assembled.

Front face sketch (Y from bottom in mm):

```
200 ┤  ████ DISPLAY VIEW 73.4×49 (board 86×56, centered ±X)   DISPLAY_CY=___
    │
140 ┤  ───────────────────────────────── (slot zone)            SLOT_CY=___
  85┤  ═══════════════ SLOT ============  (120 ≈ full width)
    │
  44┤  (   controller dock recess   118.4×62.8 oval )          DOCK_CY=___
   0┴─────────────────────────────────────────────────── X: -75 … +75
```

## 3. The critical one — camera geometry (already validated in cardboard)

This is the pair of numbers your cardboard prototype locked in. Everything
else in the camera bay derives from them.

| Param | Default | Measured | Notes |
|---|---|---|---|
| `CARD_BOTTOM_Y` | `SLOT_CY - 3` | ____ | **Height of the card's bottom face (Aztec side) when seated** in the slot |
| `CAM_DIST` | 90 | ____ | **Lens → card distance** (vertical gap between camera lens and the card face). Your prototype already proved this WORKS — trust it over the brief's 80–100 guess |
| `CAM_LENS_STACK` | 4 | ____ | Lens collar height above the camera PCB (calipers on your IMX708) |
| `CAM_BAY_W` | 48 | ____ | Camera bay interior width (baffle walls around the camera) |
| `CAM_BAY_Z` (span) | 46 | ____ | Bay depth along case depth — needs to clear the card pocket above it |

## 4. Internal fit (measure off the cardboard layout)

| Param | Default | Measured | Notes |
|---|---|---|---|
| `PI_CX` | -43 | ____ | Pi board center X (offset to one side of the camera bay) |
| `PI_CZ` | 51 | ____ | Pi board center Z (depth, measured from front panel plane) |
| `PI_STANDOFF_H` | 8 | ____ | Gap between case floor and Pi PCB bottom (clearance for whatever's underneath) |
| `LED_RECESS` | 80×6×2.5 | ____ | LED strip recess size — measure the strip you glued into the cardboard |
| `LED_CY` | `SLOT_CY + 5.5` | ____ | LED recess center height (under the slot's upper lip, per brief) |
| `SPEAKER_CX/CZ` | 0 / 60 | ____ | Bottom-mounted speaker center (X into width, Z into depth) |
| `SPEAKER_DIA` | 80 | ____ | Speaker + recess diameter |

## 5. Rear panel / side cutouts (measure the cardboard holes)

| Param | Default | Measured / Verify | Notes |
|---|---|---|---|
| `PWR_BTN_X` | +40 | ____ | Latching power switch center on rear wall |
| `PWR_BTN_DIA` | 10.2 | ____ | Switch mounting hole |
| USB-A strip | left wall, 37×9.5 | ____ | Pi's 4 USB-A ports exit the left side wall |
| USB-C + 2× micro-HDMI | rear wall | ____ | **Verify positions against your Pi 4B** — the PARAMS are placeholders; check connector centers with the Pi in place before printing |
| Fan (`FAN_OPTION`) | 0 (vents only) | ____ | 1 = add 40×10 recess + mounts on the top wall (needed if you run a Pi 5) |

---

## Why defaults where cardboard has no answer

Anything left blank above that the cardboard doesn't constrain keeps the
`brief:` default. If a default is wrong, **edit one line in the PARAMS block**
of `build_console_case.py` and re-run both scripts — that's the whole
iteration loop (same as the controller shell project).