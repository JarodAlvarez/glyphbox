# Controller shell

Two printed halves that close around the controller board with two M2.5 screws.

| File | What it is |
|---|---|
| `stl/glyphbox_bottom_shell.stl` | Back half: standoffs the board rests on, screw holes, magnet pocket. Ready to print |
| `stl/glyphbox_top_shell.stl` | Front half: D-pad and button openings, USB notch, screw bosses. **Without the membrane mounts** (see below) |
| `build_merged_stl.py` | Builds both STLs (needs `trimesh manifold3d shapely numpy`) |
| `build_controller_shell.py` | The same shell as a Fusion 360 script, for editing |
| `build_brackets.py` | Adds the membrane mounts from your own copy of the Lensless shell |

## The membrane mounts

The collars, ribs and posts that hold the Game Boy Pocket D-pad and A/B membranes come from the **[Lensless Gameboy Pocket / Pocket Color Shell](http://pcbway.com/project/shareproject/Lensless_Gameboy_Pocket_Pocket_Color_Shell_243a0f87.html)**. Its licence, CC BY-NC-ND, doesn't allow sharing adapted versions, so they aren't included here. You can add them to your own copy:

1. Download the Lensless shell from PCBWay.
2. Extract the mounts from its front shell, lined up for this controller:

```bash
python build_brackets.py "path/to/Lensless_Front_Rev8.stl"
```

3. Build the shell again. The top shell now includes the mounts:

```bash
python build_merged_stl.py
```

Keep the result for your own build: the Lensless licence doesn't allow sharing it.

The bare top shell prints and closes fine, but without the mounts the membranes have nothing to seat in.

## Licence

The files in this folder are CC BY-NC-SA 4.0, like the rest of the hardware. The Lensless shell keeps its own licence.
