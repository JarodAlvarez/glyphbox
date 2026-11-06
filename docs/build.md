---
title: Build a console
order: 3
---

# Build a console

A GLYPHBOX is a Raspberry Pi 3 in a 3D-printed case, with a 3.5" screen, a camera under the card slot and a controller that docks on magnets. This guide covers the whole build. The [bill of materials](https://github.com/JarodAlvarez/glyphbox/blob/main/hardware/BOM.csv) lists every part.

Expect a weekend, plus the wait for printed parts and the controller board. You'll need a soldering iron for the amplifier and the controller, a small screwdriver, and an M3 tap.

## 1. Order the parts

- **Electronics:** everything in the BOM. The display, camera, LED strip and cables are the exact models the prototype uses. Others may work, but the case is sized for these.
- **Printed parts:** the case STLs in [hardware/case/stl](https://github.com/JarodAlvarez/glyphbox/tree/main/hardware/case/stl). The prototype was printed in SLA resin by an online service. Resin gives crisp corners and engraving. FDM should work but hasn't been tested.

| Part | Qty |
|---|---|
| `glyphbox_body.stl` | 1 |
| `glyphbox_rear_panel.stl` | 1 |
| `glyphbox_screen_clip.stl` | 5 |
| `glyphbox_usb_clamp.stl` | 1 |

- **Controller board:** a custom PCB. Upload [`glyphbox-controller-v2-gerbers.zip`](https://github.com/JarodAlvarez/glyphbox/tree/main/hardware/controller/pcb) to a PCB maker such as JLCPCB: 2 layers, default options. The KiCad project is next to it.

> **Print services:** some reject walls thinner than 0.8 mm, or files that contain more than one separate body. The case is designed to pass both checks.

## 2. Prepare the printed parts

- **Tap the screw holes.** Resin is brittle, so the case uses machine screws in tapped holes, never self-tapping screws. Run an M3 tap through the holes in the rear panel posts, the screen clips and the USB clamp posts. Run an M2.5 tap through the Pi standoffs and an M2 tap through the camera posts.
- **Clean up.** Remove support marks from the card slot so a card slides in smoothly. The slot's floor and roof are what hold the card flat over the camera.

## 3. Wire the sound

The speaker is a Game Boy DMG speaker, driven by a small PAM8403 amplifier board from the Pi's headphone jack.

1. Cut a 3.5 mm stereo cable, and strip the white (left), red (right) and bare copper (ground) wires. Check which is which with a multimeter: tip is left, ring is right, sleeve is ground.
2. Solder white to the amp's **L** input and copper to its **G** pad. Tape off the red wire.
3. Solder the speaker's two wires to the amp's **L OUT** `+` and `−` pads.
4. Solder two jumper wires to the amp's **5V** `+` and `−` pads. They plug onto the Pi's **pin 2** (5 V) and **pin 6** (ground).
5. Wrap the solder joints with tape or a dab of hot glue, so a tug can't break them.

## 4. Assemble the console

1. **Display:** set the display in its pocket behind the front window, and hold it with three screen clips (M3). Connect the right-angle HDMI cable to it. Its plug sits above the display inside the case.
2. **Camera:** mount the camera lens-up on the four floor posts (M2), under the middle of the card slot. Run its ribbon cable to the Pi's camera connector.
3. **Raspberry Pi:** mount the Pi on the right-hand wall (M2.5 standoffs), with its USB and Ethernet ports facing the back. Connect the HDMI cable, the camera ribbon, and the display's USB power.
4. **LED strip:** stick it to the wall below the far end of the card slot, facing the front, so it lights the card from above. Plug it into a Pi USB port. If cards read badly, diffuse it with a layer of tape or paper: direct glare on the card stops the camera reading it.
5. **Speaker:** set it in the ring on the inside of the left wall, behind the logo-shaped grille, and hold it with the two remaining screen clips. Tape the amp to the floor or wall. Plug the 3.5 mm cable into the Pi.
6. **Controller socket:** fit the USB-A panel-mount extension in the clamp inside the front wall, lower left, with two M3 screws from the inside. Plug its other end into a Pi USB port.
7. **Power:** fit the panel-mount micro-USB socket in the rear panel, and plug its other end into the Pi's power input.
8. **Dock magnets:** glue two stacked 10 × 2 mm magnets into the pocket behind the controller dock, from the inside.
9. **Close up:** fit the rear panel with six M3 screws. Stick the four rubber feet into the recesses underneath.

> **Known fit issues on the prototype:**
> - **The printed USB clamp didn't fit:** the real socket's casing is wider than the clamp's opening. The current model uses an open-top fork clamp, which hasn't been printed yet. On a print of the old clamp, washers on the posts, filing the opening or glue all work.
> - **The audio plug** ends very close to the LED wall. A right-angle 3.5 mm plug avoids it.
> - **Measurements:** some dimensions came from photos and listings rather than calipers. If a part is tight, `hardware/case/glyphbox_case.py` is parametric: change the value and regenerate the STLs.

## 5. Build the controller

1. Order the controller PCB with its Gerber files.
2. Solder the Raspberry Pi Pico flat onto the board by its castellated edges. Use flux, tack two opposite corners first to line it up, then work around the edge.
3. Install CircuitPython on the Pico. Hold BOOTSEL while plugging it in, then drag the CircuitPython `.uf2` file onto the drive that appears.
4. Copy `adafruit_hid` from the Adafruit CircuitPython library bundle into the Pico's `lib/` folder, and [`code.py`](https://github.com/JarodAlvarez/glyphbox/blob/main/hardware/controller/firmware/code.py) to its root.
5. Before fitting the membranes, test it: plug it into any computer and short each button's pads with tweezers. The arrows, Z and F2 keys should register.
6. Fit the reproduction Game Boy Pocket membranes and buttons, then close the printed shell with two M2.5 screws. Glue two stacked 10 × 2 mm magnets into the shell's magnet pocket.

> **The controller shell isn't published yet.** Its button mounts are being redesigned, because the originals are adapted from a shell under a no-derivatives license. Until then, the board works as a bare controller.

The controller is a USB keyboard, so it needs no driver:

| Button | Pico pin | Key |
|---|---|---|
| Up | GP2 | Up arrow |
| Down | GP3 | Down arrow |
| Left | GP4 | Left arrow |
| Right | GP5 | Right arrow |
| Action | GP6 | Z |
| Menu | GP7 | F2 |

## 6. Set up the software

1. **Flash the SD card** with Raspberry Pi OS Lite (64-bit). In Raspberry Pi Imager, set a user, Wi-Fi and SSH before writing.
2. **Install what the console needs:**

```bash
sudo apt update
sudo apt install -y libsdl2-2.0-0 libluajit-5.1-2 python3-picamera2 python3-opencv python3-pil python3-pip
python3 -m pip install --user --break-system-packages "zxing-cpp==3.1.1"
```

zxing-cpp reads the cards. Version 3.1.1 matters: an older version on the prototype failed to read cards that 3.1.1 reads every time.

3. **Install the console software:** download `glyphbox-pi-arm64.tar.gz` from [Releases](https://github.com/JarodAlvarez/glyphbox/releases) and unpack it in your home folder:

```bash
tar xzf glyphbox-pi-arm64.tar.gz
mv glyphbox-pi-arm64 ~/glyphbox
```

4. **Send sound to the headphone jack:** run `sudo raspi-config`, then choose System Options → Audio → Headphones.
5. **Start it on boot:** `glyphbox.service` in the download starts the console when the Pi powers up. Edit its `User`, `WorkingDirectory` and `ExecStart` lines to match your user and folder, then:

```bash
sudo cp ~/glyphbox/glyphbox.service /etc/systemd/system/
sudo systemctl enable --now glyphbox
```

The console boots straight into its splash screen. To update it later, download the new release and replace the folder.

## 7. Play

Print a game's cards (see [Carts and cards](carts.html)), press the action button on the splash screen, and slide each card into the slot. The screen shows each card as it's read.

**If cards don't read:**
- Check the zxing-cpp version first: `python3 -m pip show zxing-cpp`.
- Diffuse the LED strip.
- Make sure the card lies flat in the slot. Cards printed on thin paper can bow.
- Print at 100% scale, not "fit to page".
