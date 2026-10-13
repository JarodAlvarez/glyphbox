# GLYPHBOX console case

Parametric 3D-printable case based on the cardboard prototype and the mockup
renders. Everything is driven by the PARAMS block at the top of
`glyphbox_case.py` (each value is tagged `M` = measured on the prototype or
`A` = assumed).

```bash
.venv/bin/python glyphbox_case.py   # stl/*.stl + envelope + interference report
.venv/bin/python render.py          # preview/*.png
```

The venv needs `trimesh manifold3d shapely numpy matplotlib pillow`.

## Parts

| File | Qty | Notes |
|---|---|---|
| `stl/glyphbox_body.stl` | 1 | Front, sides, top, floor and all internal mounts |
| `stl/glyphbox_rear_panel.stl` | 1 | 6 x M3 self-tapping screws; carries the power jack |
| `stl/glyphbox_screen_clip.stl` | 5 | M3 self-tapping; 3 hold the display, 2 hold the speaker |
| `stl/glyphbox_usb_clamp.stl` | 1 | 2 x M3 self-tapping from inside; clamps the controller USB socket, no screws on the front |
| `stl/glyphbox_faceplate.stl` | 0 | Only for `FRONT_STYLE = 'faceplate'` (not the default) |

## Layout

- Frame: X = width (+X is the viewer's right), Y = depth (0 = front face),
  Z = height (0 = bottom).
- Display in a pocket behind the front window; right-angle HDMI plug fully
  enclosed above it.
- Card slides short-edge first into a sleeve (ledges, roof, end stop). The LED
  strip sticks to the wall hanging below the end stop, facing the front.
- Camera on four floor posts (M2), lens up, under the card centre.
- Pi 3 on the right wall (M2.5), HDMI edge up, USB/Ethernet facing the rear
  panel with 34 mm of plug room, SD card toward the front.
- Controller dock: 6 mm recess, dimple for the puck's stacked magnets, one
  10 x 2 mm magnet glued into the pocket behind it from the inside.
- Controller USB-A socket: panel-mount extension (HCFeng B0DDH91CWV, 30 cm,
  angled male) screwed to the inside of the front wall, lower left.
- Power: panel-mount micro-USB on the rear panel.
- Speaker: Game Boy DMG type (28 mm assumed) in a locating ring on the inside
  of the left wall, behind a grille shaped like the logo mark; two clips hold it. The amp
  has no dedicated mount (tape it to the floor or wall).
- Feet: four 19.6 mm x 1 mm recesses in the underside for MacBook Pro
  replacement pads (about 19 mm; size taken from listings, not measured).

## Not yet verified against real parts

USB-A socket nose size and screw spacing (taken from the listing drawing), display lit-area position,
camera lens offset from its mounting holes, card thickness, speaker diameter
and thickness.

`archive-2026-08-31/` holds the earlier, superseded attempt.
