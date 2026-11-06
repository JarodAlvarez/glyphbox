# Console case

`glyphbox_case.py` is the parametric source of the case. Every dimension is in the `PARAMS` block at the top, and each value is tagged **M** (measured on the prototype) or **A** (assumed from a listing or photo). Running it writes the STLs to `stl/` and prints an interference report against stand-in blocks for the parts.

```bash
python3 -m venv .venv && .venv/bin/pip install trimesh manifold3d shapely numpy matplotlib
.venv/bin/python glyphbox_case.py
```

| File | Qty | Notes |
|---|---|---|
| `stl/glyphbox_body.stl` | 1 | Front, sides, top, floor and all internal mounts |
| `stl/glyphbox_rear_panel.stl` | 1 | 6 × M3 into tapped holes. Carries the power socket |
| `stl/glyphbox_screen_clip.stl` | 5 | M3. Three hold the display, two hold the speaker |
| `stl/glyphbox_usb_clamp.stl` | 1 | 2 × M3 from inside. Clamps the controller's USB socket |

The envelope is 140 × 139 × 226 mm. Resin parts use machine screws in **tapped** holes, never self-tapping screws.

**Not yet checked against real parts:** the USB socket casing width (the current fork clamp hasn't been printed), the display's lit area, the camera lens offset, card thickness, and the speaker's size. Values that aren't right are easy to change: edit `PARAMS` and run the script again.

The front wordmark uses Futura when the system has it (macOS) and falls back to DejaVu Sans otherwise.
