# Hardware

Everything needed to build a GLYPHBOX console and its controller. The [build guide](https://jarodalvarez.github.io/glyphbox/docs/build.html) walks through it step by step.

| Folder | What's in it |
|---|---|
| [BOM.csv](BOM.csv) | Every part, with quantities and notes |
| [case/](case/) | The console case: STLs to print, and the parametric script that makes them |
| [controller/pcb/](controller/pcb/) | The controller board: KiCad project, footprints, 3D model and Gerbers ready to order |
| [controller/firmware/](controller/firmware/) | `code.py` for the Raspberry Pi Pico (CircuitPython) |
| [controller/shell/](controller/shell/) | The printed controller shell, and the scripts that build it |

**One part you add yourself:** the controller shell's membrane mounts come from the Lensless Game Boy Pocket shell, whose licence doesn't allow sharing adaptations. The shell here is published without them, and [controller/shell/](controller/shell/) shows how to add them from your own download.

## Licence

The hardware files are licensed **CC BY-NC-SA 4.0**. You can build, modify and share them, but not sell consoles, kits or parts made from them, and changes you share must use the same licence. The GLYPHBOX name and logo are covered separately, see [TRADEMARK.md](../TRADEMARK.md).

## Credits

- The controller's membrane pad shapes are adapted from Natalie the Nerd's [YAPoco](https://github.com/nataliethenerd) Game Boy Pocket reference.
- The controller shell's membrane mounts come from the [Lensless Gameboy Pocket / Pocket Color Shell](http://pcbway.com/project/shareproject/Lensless_Gameboy_Pocket_Pocket_Color_Shell_243a0f87.html) (CC BY-NC-ND), added by each builder from their own copy.
- The controller uses reproduction Game Boy Pocket buttons and membranes.
