# GLYPHBOX — Physical Prototype Fabrication Brief
### Revision 1.0 · March 2026

---

## HOW TO USE THIS DOCUMENT

This document is self-contained. It provides full project context and fabrication specifications for planning and executing the GLYPHBOX physical prototype. Bring this into a design/fabrication planning session; no prior context is required.

---

## 1. Project Overview

GLYPHBOX is a custom fantasy console in the tradition of PICO-8 and TIC-80 — a dedicated hardware device for playing a curated library of small Lua-scripted games. The distinguishing feature is its cartridge system: games are distributed as physical cards with Aztec QR codes printed on the rear. The console has an integrated camera that scans the card to load the game.

**Core specifications (fixed, not negotiable):**

| Property | Value |
|---|---|
| Display resolution | 128 × 128 pixels, 1-bit monochrome |
| Input | 4-way D-pad + 1 action button |
| Audio | 2-channel chiptune (square wave + noise) |
| Scripting | Lua 5.4 / LuaJIT, sandboxed |
| Host SBC | Raspberry Pi 4B or 5 |
| Runtime | C99 + SDL2, 30 fps hard cap |
| Cartridge format | `.gbcart` binary encoded as Aztec QR code on physical card |
| Camera | Arducam IMX708 75D autofocus (CSI ribbon) |
| Input device | Custom wired puck controller (target) or USB gamepad (interim) |

**The vision:** A compact desktop unit with a premium, slightly retro-industrial aesthetic — dark gunmetal finish, a small square display, and a front-facing card slot with green LED underlighting. The card slot is the signature UX element: insert a card and the game loads automatically. No app stores, no screens to navigate, no internet required. Physical games, physical hardware.

---

## 2. Design Language & Aesthetic Reference

The target aesthetic is a miniature retro computer / CRT hybrid. Think late-1980s personal computer meets modern industrial design.

**Key visual attributes:**

- **Form factor:** Small boxy desktop unit. Target envelope: approximately 150mm wide × 200mm tall × 100mm deep. The unit sits on a desk and faces the user like a tiny CRT monitor.
- **Color:** Dark charcoal / gunmetal gray throughout. Matte or satin finish. No gloss. The display bezel may be slightly darker than the body.
- **Material feel:** Anodized aluminum aesthetic — even if the prototype uses high-quality dark PLA or resin, the finish should not look like hobbyist 3D printing.
- **Proportions:** Upper 60% of the front face is display. Lower 40% contains the card slot and ventilation slots.
- **Card slot:** Horizontal slot centered in the lower section of the front face. Card slides in from the left or right (TBD). Green LED glow emanates from the slot — this is the console's signature lighting element.
- **Ventilation:** Horizontal louver slots on the upper rear or top surface.
- **Controller:** Small round or slightly oval puck. Same dark matte finish as the console. Coiled/curly cable in matching dark color (3.5mm coiled cable aesthetic). Very minimal button layout.
- **Game cards:** Credit-card to A6 size. Dark background, colored accent bars (red/blue). Game title and pixel art on front. Aztec code on rear with title and card number.

The unit should look like it belongs in a design museum — not a maker fair. Every visible surface is considered.

---

## 3. Bill of Materials — Internal Electronics

### 3.1 Primary Compute

| Component | Recommendation | Notes |
|---|---|---|
| SBC | Raspberry Pi 5 (4GB) | Pi 5 preferred for boot speed and CPU headroom. Pi 4B works. Avoid Pi Zero — too slow for camera processing. |
| Storage | SanDisk Endurance microSD 32GB (SDSDQUA2-032G) or Samsung Pro Endurance | Endurance-rated cards matter; Pi is always-on and boots/writes frequently. Alternatively: USB SSD boot via Pi 5 NVMe HAT. |

**Pi 5 advantages over Pi 4B for this project:**
- Faster camera ISP (important for Aztec decode speed)
- RP1 I/O chip reduces USB latency for controller
- PCIe slot enables NVMe boot (eliminates SD card reliability concern)
- Faster cold boot

### 3.2 Camera

| Component | Recommendation | Notes |
|---|---|---|
| Camera module | Arducam IMX708 75D Autofocus (B0401) | Already owned. CSI ribbon. 12MP, autofocus, 75° FOV. This is the correct module for the fixed-slot geometry. |
| Cable | Arducam CSI cable 150mm or 200mm | Measure routing path from camera mount position to Pi CSI port. |
| Camera mount | Custom 3D printed bracket | See Section 5 — camera mounts facing upward inside the unit, beneath the card slot. |

### 3.3 Display

See Section 4 for full display selection rationale. The display connects via HDMI mini or DSI ribbon depending on choice.

### 3.4 LED Lighting (Card Slot)

| Component | Recommendation | Notes |
|---|---|---|
| LED strip | Adafruit NeoPixel Stick 8x5050 (Product #1426) or single-color 5050 LED strip | Green (525nm). NeoPixels allow brightness control from Pi GPIO. Single-color strip + PWM resistor is simpler. |
| LED driver | Pi GPIO + MOSFET (2N7000 or similar) for single-color | NeoPixel Stick needs a level shifter (3.3V → 5V) on the data line. |
| Alternative | WS2812B LED strip, 30 LEDs/m, cut to ~80mm | Pre-wired 3-pin JST connector available. Controlled via rpi-ws281x library. |

**Recommendation:** Use a simple non-addressable green 5050 LED strip (60 LEDs/m, cut to 3–4 LEDs) driven by a 2N7000 MOSFET on a GPIO pin. Simpler wiring, no library dependency, still supports PWM brightness control. PWM brightness is useful for the "scanning" pulse animation.

### 3.5 Audio

| Component | Recommendation | Notes |
|---|---|---|
| DAC / amplifier | Adafruit MAX98357 I2S 3W mono amp breakout (Product #3006) | I2S direct to Pi GPIO. No USB audio dongle needed. 3W into 4Ω is adequate for a small enclosed speaker. |
| Speaker | Dayton Audio CE32A-8 3-inch full range 8Ω, or generic 2.5" 4Ω 3W speaker | See Section 8 for placement. |
| Alternative DAC | HiFiBerry MiniAmp HAT | Cleaner audio, slightly larger, sits on Pi GPIO header. |

The runtime uses ALSA via SDL2. Both MAX98357 and HiFiBerry expose as standard ALSA devices.

### 3.6 Power

See Section 9. Summary: Official Raspberry Pi 5 USB-C PSU (5V 5A, 27W) externally routed, or an internal 5V DC-DC regulator from a 12V wall brick.

### 3.7 Controller Interface

See Section 7. The target is a custom RP2040-based USB HID puck controller. Interim solution: PlayStation Classic USB dongle passes through the enclosure.

### 3.8 Miscellaneous Internal Hardware

| Component | Quantity | Notes |
|---|---|---|
| M2.5 × 6mm brass standoffs | 8 | Pi mounting |
| M2.5 × 4mm screws | 16 | Pi + display mounting |
| M3 × 8mm screws + heat-set inserts | 20 | Enclosure assembly |
| 22 AWG stranded wire (black, red, green) | 1m each | Internal wiring |
| JST-PH 2-pin connectors | 4 | Speaker, LED quick-disconnect |
| JST-XH 3-pin connectors | 2 | Camera, LED data |
| Kapton tape | 1 roll | Cable management, thermal isolation |
| Thermal pad 1mm (for Pi CPU heatsink) | 1 | Pi 5 runs hot |
| Small passive heatsink set for Pi 5 | 1 | Pimoroni Heatsink Kit or official Pi active cooler |

---

## 4. Display Selection

### Requirements

- Square or near-square aspect ratio (the console renders 128×128)
- At least 3.5" diagonal — large enough to be legible at arm's length
- Works with Raspberry Pi via HDMI or DSI
- SDL2 renders at native resolution via `SDL_RenderSetLogicalSize(128, 128)` and letterboxes automatically — so any resolution works, but square panels avoid black bars
- Sunlight readability not required (indoor desktop use)

### Option A — 4.0" 480×480 Round/Square HDMI Display (Recommended for Prototype)

**Part:** Waveshare 4inch Square LCD, 720×720, HDMI (SKU: 28089) or the 4.0" 480×480 variant.

- 480×480 or 720×720 resolution, square panel
- HDMI input — plug-and-play with Pi, no driver needed
- Integrated HDMI driver board with micro-HDMI connector
- Touch version available but not needed
- Dimensions: ~100mm × 100mm panel, driver board adds ~15mm to rear depth
- Available from Waveshare directly or Amazon (~$35–55 USD)
- Pi config: `hdmi_cvt=480 480 60 1` in `/boot/config.txt` sets 480×480 custom mode; alternatively leave at default and let SDL2 letterbox

**Pros:** No driver complexity, proven with Pi, square native resolution, good pixel density.
**Cons:** Driver board adds depth; micro-HDMI cable routing inside enclosure.

### Option B — 3.5" DSI Display

**Part:** Raspberry Pi Official 7" DSI Display is too large. For DSI at 3.5–4": Waveshare 3.5inch DSI LCD (480×320, not square — avoid unless tilted) or the Pimoroni HyperPixel 4.0 Square (720×720, DSI).

**Pimoroni HyperPixel 4.0 Square:**
- 720×720, IPS panel, DSI ribbon, 4.0" diagonal
- Sits directly on Pi GPIO/DSI — very compact, no trailing HDMI cable
- Excellent color and sharpness
- SKU: PIM369, ~$65 USD
- Requires Pimoroni DSI driver (overlays for Pi OS)
- Touch version available

**Pros:** Compact, clean internal routing (ribbon cable), square native resolution, premium panel quality.
**Cons:** DSI driver adds a layer of dependency; GPIO pins consumed by DSI interface reduce expansion options.

### Option C — Small HDMI Monitor (Interim / Testing Only)

Any small HDMI monitor (7" or larger) works for development. Not a target for the enclosure design.

### Recommendation

**Use the Pimoroni HyperPixel 4.0 Square for the final prototype.** The DSI ribbon eliminates the micro-HDMI cable routing problem inside a tight enclosure. The 720×720 resolution means SDL2's 128×128 logical size upscales to a clean integer multiple (approximately 5.6×). Panel quality is excellent for 1-bit pixel art.

For initial bring-up and cardboard mock-up testing, use a Waveshare 4" HDMI panel — driver-free, risk-free.

**Pi config for HyperPixel 4.0 Square:**
```
# /boot/config.txt additions
dtoverlay=vc4-kms-dsi-hyperpixel4sq
```

---

## 5. Card Slot Mechanism Design

This is the central engineering challenge of the prototype. The slot must:

1. Accept a physical card (credit-card thickness: 0.76mm, or up to 1.5mm for a custom card with backing)
2. Position the card at a fixed, repeatable distance above the camera
3. Allow the camera to image the Aztec code through a transparent or open window
4. Illuminate the code with green LEDs for consistent contrast
5. Allow the card to be removed cleanly (no grabbing, no jam)

### 5.1 Camera Geometry

The Arducam IMX708 in this application points **upward** from inside the enclosure toward the card slot opening.

**Working distance calculation:**

- IMX708 field of view: 75° diagonal
- Target: frame the 95mm Aztec code on the card rear with margin
- Card rear Aztec code: approximately 95mm × 95mm (per the current card design)
- Required image footprint at slot: ~110mm × 110mm (with margin)
- At 75° diagonal FOV, for a 4:3 sensor (12MP IMX708): horizontal ~62°, vertical ~49°
- For 110mm horizontal coverage at 62° horizontal FOV: distance = 110 / (2 × tan(31°)) ≈ 91mm

**Target camera-to-card distance: 80–100mm.** This is the vertical distance from the camera lens to the bottom face of the inserted card.

This sets a constraint on the internal enclosure depth: the camera mount must be 80–100mm below the card slot aperture.

### 5.2 Slot Construction

**Design A — Open-bottom slot (recommended for prototype):**

- Two horizontal guide rails spaced ~87mm apart (standard credit-card width is 85.6mm; A6 is 105mm wide)
- Card slides in horizontally; rests on the rails with the barcode side down facing the camera
- Bottom of the slot channel is open (just air) — camera sees through
- A stop tab at the far end prevents the card from sliding through
- LED strip runs along the underside of the front rail, shining downward onto the card

Card is suspended across the rails, Aztec code visible through the open channel. Camera looks up through this gap.

**Rail material:** 3D printed guide channels integrated into the enclosure front panel, or small aluminum angle extrusion (12mm × 12mm × 1mm wall) cut and bonded in.

**Card retention:** A very light spring detent (0.5mm spring steel leaf) that clicks the card into the stop position. Prevents card from vibrating out but releases easily.

**Card sizes to support:**
- Standard credit card: 85.6mm × 54mm × 0.76mm
- A6 card with backing: 105mm × 148mm × ~1.2mm (front half of card only may be inserted, leaving rear code portion in slot)

**Recommendation:** Design slot for standard credit-card width (86mm interior gap) and up to 1.5mm thickness. A6 cards would be inserted only to the depth of the Aztec code area — the card sticks out the front. This is fine; it adds to the physical character.

### 5.3 LED Illumination

- Mount LED strip on the underside of the upper card slot rail, facing downward
- Green LEDs (525nm) provide maximum contrast on black toner printed Aztec codes
- Aim for ~500–1000 lux at card surface (verify with lux meter during calibration)
- LED driven via Pi GPIO + MOSFET; PWM at 1kHz for flicker-free brightness control
- During scanning: pulse LED brightness in a slow sine wave for visual feedback that scanning is active

### 5.4 Camera Mount

- Camera mounts to a small 3D-printed bracket, facing upward
- Bracket fastens to the enclosure floor with M2.5 screws
- Camera ribbon routes horizontally to the Pi CSI connector
- Include a camera tilt adjustment: 1–2 degree adjustment range via slotted mounting holes (to correct for optical axis deviation from vertical)
- After calibration, tighten down permanently — this is a fixed-geometry system

### 5.5 Transparent Window Option

Consider a 1mm clear acrylic sheet bonded over the slot aperture from below (inside the enclosure). This:
- Keeps dust off the camera
- Provides a physical bottom to the card channel (card rests on acrylic, not suspended)
- May reduce contrast slightly (test required)

If using acrylic, polish it to optical clarity and verify Aztec decode reliability before committing.

---

## 6. Enclosure Fabrication Options

### 6.1 Prototype Approach — 3D Printing (Recommended First Pass)

**Material:** PETG or ASA preferred over PLA for:
- Better dimensional stability at Pi operating temperature (~40–50°C inside enclosure)
- Less warping during print for large flat panels
- Better layer adhesion for press-fit and snap features

**Print orientation:** Split the enclosure into 4–5 parts to minimize support material:
1. Main body rear shell (back + sides + bottom)
2. Front panel (display cutout + card slot + vent slots)
3. Top cap with ventilation slots
4. Card slot inner liner / guide rails (separate part for fine tuning)
5. Stand / tilt foot (optional)

**Finish:** Sand to 400 grit, prime with Rustoleum filler primer (gray), sand to 800 grit, paint with Rustoleum Painter's Touch 2X matte black or Duplicolor Metalcast charcoal. Wet sand between coats. This produces a surface that looks nothing like 3D-printed plastic.

**Recommended printer:** Bambu Lab X1C or Prusa MK4 for dimensional accuracy on PETG. Layer height 0.15mm for visible exterior surfaces.

**Print time estimate:** 18–28 hours total for all parts.

### 6.2 Production Approach — Options

**CNC Aluminum:**
- 6061-T6 aluminum billet, machined and anodized
- Produces the exact premium feel of the design reference
- Cost: $300–800 USD for one-off prototype from an online CNC service (Fictiv, Xometry, SendCutSend for sheet + bending)
- Lead time: 2–4 weeks
- Not recommended for initial prototype — iterate in plastic first

**Sheet Metal:**
- 1.5mm cold-rolled steel, laser cut + CNC brake formed + powder coated
- Excellent rigidity, good thermal mass, very clean aesthetic
- SendCutSend or OSH Cut for laser cutting (~$50–100 for cut parts)
- Bending: local sheet metal shop or manual brake tool
- Powder coat: local shop, RAL 7021 (black-gray) matte

**Resin Casting:**
- Vacuum cast polyurethane from a 3D-printed master
- Very smooth surface straight from mold
- Good for small batches (5–20 units)
- Requires silicone mold making — significant time investment

### 6.3 Recommended Sequence

1. **Phase 1:** Cardboard mock-up to verify camera geometry and card slot ergonomics (1 day)
2. **Phase 2:** FDM prototype in PETG, unfinished (verify all PCB mounting, cable routing, display fit) (~1 week)
3. **Phase 3:** FDM prototype painted and finished (final form verification, photography)
4. **Phase 4:** CNC aluminum or sheet metal if moving beyond personal prototype

### 6.4 Enclosure Dimensions (Target)

| Dimension | Target |
|---|---|
| Width | 150mm |
| Height | 200mm |
| Depth | 100mm |
| Display cutout | ~100mm × 100mm (for 4" square panel) |
| Card slot width | 120mm (for A6 card + margin) |
| Card slot height | 5mm (clear card + play) |
| Card slot position | Centered horizontally, 50mm from bottom of front face |
| Wall thickness (3D print) | 3mm minimum |
| Internal clearance, camera bay | 100mm depth from slot to floor |

---

## 7. Controller Design

### 7.1 Design Intent

- Small puck — approximately 80mm × 60mm × 25mm oval footprint
- D-pad + 1 action button (A button)
- Optional: Start/Select for menu navigation (currently handled by ESC key, but physical hardware needs at least one system button)
- Coiled cable, ~1m extended length, 3.5mm coil diameter
- Connects via USB-A to the Pi
- Same dark matte finish as console

### 7.2 Electronics: RP2040-Based Custom HID

**Microcontroller:** Raspberry Pi Pico (RP2040) or the smaller Waveshare RP2040-Zero.

The RP2040 natively presents as a USB HID gamepad with no drivers required on any OS. The existing input.c code already supports any SDL2-compatible gamepad via SDL_GameController, so a standard HID gamepad will work immediately.

**Recommended approach:** Use the Waveshare RP2040-Zero (12mm × 18mm, USB-C) or a SparkFun Pro Micro RP2040. Program with CircuitPython + `usb_hid` library, or C SDK with TinyUSB. The CircuitPython approach is faster to prototype.

**CircuitPython HID sketch (concept):**
```python
import usb_hid
from adafruit_hid.gamepad import Gamepad
import board, digitalio, time

gp = Gamepad(usb_hid.devices)
# Wire D-pad and button to GPIO pins, poll at 1ms, report button state
```

**Button hardware:**
- D-pad: 4 individual tact switches in a cross arrangement, or a dedicated D-pad dome switch (Alps RKJXK series) — the Alps part provides the best tactile feel
- A button: Sanwa OBSC-24 24mm arcade button (if space allows) or a smaller dome switch like the Omron B3F series
- PCB: Custom KiCad layout, or use a small perfboard for prototype

**PCB services:** OSH Park (USA, ~$5 for 3 boards), JLCPCB ($2 for 5 boards + PCBA available).

### 7.3 Shell Design

- 3D printed in PETG, two halves (top + bottom) joined by M2.5 screws or snap fits
- Soft-touch spray paint or TPU overmold around grip area
- Strain relief for the coiled cable at the entry point (inline zip tie anchor inside shell)
- D-pad cutout: 28mm × 28mm square with rounded corners; fits standard D-pad cap
- A button cutout: 24mm hole if using Sanwa cap, or 12mm for dome button with printed cap

### 7.4 Coiled Cable

Source pre-made coiled USB cables, or coil your own:

**Pre-made:** Search "coiled USB-C cable black" — many keyboard enthusiast cables are available in 1m coiled length from vendors like Mechcables, Clacking Factory, or AliExpress. Cut and re-terminate with USB-A on one end.

**DIY coiling:** Wrap standard 28 AWG USB cable around a 3mm dowel, heat with heat gun at 120°C, cool, remove — produces a clean coil.

### 7.5 Interim Solution

Use the PlayStation Classic USB controller (already owned) passing through a USB port on the rear of the enclosure. This is fully functional today; the custom puck is a polish item.

---

## 8. Audio Integration

### 8.1 Speaker Placement Options

- **Front-facing:** Speaker grille in lower front panel, below card slot. Best sound projection, most aesthetically prominent. Requires a grille cut-out (laser-cut metal mesh or 3D printed hex pattern).
- **Bottom-facing:** Speaker faces downward, bounces off desk. Provides omnidirectional sound, hides the grille. Easier to implement in 3D print (rectangular cutout, speaker recessed into floor of enclosure).
- **Rear-facing:** Speaker fires out the back. Easiest to implement, worst sound.

**Recommendation:** Bottom-facing speaker with a perforated panel (3mm holes in a grid pattern, ~40% open area). The desk surface acts as a reflector and the sound spreads naturally. This also simplifies the front panel design.

### 8.2 Speaker Selection

For a 150mm × 100mm enclosure with limited internal volume (~500cc), a small full-range driver is appropriate:

- **Dayton Audio CE32A-4 3-inch 4Ω** — compact, good frequency response, rated 3W RMS, $8 USD
- **Peerless by Tymphany 830860 2.5-inch** — excellent for size, tighter bass, ~$15 USD
- Generic 2.5" 8Ω 3W speaker from DigiKey/Mouser for prototype

Pair with a MAX98357 I2S amplifier (3W into 4Ω). Provide approximately 200cc of sealed internal volume behind the speaker for a bit of low-frequency reinforcement.

### 8.3 Software Note

The runtime uses ALSA via SDL2. Set the default ALSA output device to the I2S DAC in `/etc/asound.conf`. The SDL_AUDIODRIVER environment variable can force ALSA if needed:

```
export SDL_AUDIODRIVER=alsa
export AUDIODEV=hw:0,0
```

Volume control: configure via `amixer` in the startup script, or let the SDL2 audio callback manage it in software.

---

## 9. Power System

### 9.1 Options

**Option A — External USB-C PSU (Recommended for Prototype)**

Use the official Raspberry Pi 5 USB-C Power Supply (5V 5A, 27W). Route the USB-C cable through a rear panel cutout.

Pros: Simplest, no internal power electronics, safe, Pi 5 power management handles everything.
Cons: USB-C cable exits rear of unit (acceptable).

Additional internal loads: LED strip (~0.5W), MAX98357 (~2W peak), fan if used (~0.5W). Total load under 10W typical; Pi 5 PSU handles this easily.

**Option B — Internal DC-DC Regulation from 12V Wall Brick**

Use a 12V 3A wall brick (IEC C14 inlet on rear), then:
- DC-DC step-down (buck) to 5V 5A for Pi: Pololu D24V50F5 or similar ($16 USD)
- 5V rail also powers LED strip and amp
- 12V rail can optionally power a Noctua fan directly

Pros: Single cable to the unit (12V barrel), cleaner cable aesthetic, no USB-C dangling.
Cons: More internal components, shock/safety concerns with mains-adjacent wiring (use an external wall brick, not internal mains).

**Recommendation for prototype:** Option A (external USB-C PSU). Use Option B only if cable aesthetics become a priority.

### 9.2 Power Switch

Include a latching push switch on the rear panel. Wire in series with the +5V supply rail to the Pi. This provides a hard power cut for edge cases. Do not use a momentary switch wired to Pi GPIO for primary power control — always include a hard cut switch.

**Switch:** E-Switch RP3502ABLK or similar 10mm panel-mount latching pushbutton, rated 5A.

### 9.3 Cable Routing

All internal wiring should use JST-PH or JST-XH connectors for quick-disconnect during disassembly. Label all connectors with heat-shrink labels. Keep high-current wires (5V main) as short as practical and away from the camera ribbon cable.

---

## 10. Assembly Sequence

This is the recommended order of operations for the first prototype build. Each step should be verified before proceeding.

### Phase 0 — Preparation
1. Print all enclosure parts (estimate 24 hours print time total)
2. Gather all components against BOM
3. Flash Pi OS (64-bit Lite) to SD card; confirm Pi boots headless
4. Clone GLYPHBOX repository, build runtime, confirm it runs on Pi with USB gamepad and HDMI monitor

### Phase 1 — Internal Chassis Mock-up (Cardboard)
5. Cut cardboard to enclosure interior dimensions (144mm × 194mm × 94mm interior)
6. Mount camera on a temporary stand at 80–100mm below a simulated card slot
7. Hold a printed card above the slot and run `cart-daemon.py` — verify Aztec decode works at target distance
8. Adjust camera height until decode is reliable (this locks the camera-to-slot distance)
9. Note the exact working distance — this becomes a fixed dimension in the enclosure design

### Phase 2 — Electronics Integration (Before Enclosure)
10. Wire MAX98357 I2S amp to Pi GPIO (I2S pins: BCM 18, 19, 21)
11. Wire LED strip via MOSFET to a Pi GPIO pin (BCM 12 recommended for hardware PWM)
12. Confirm I2S audio output (`speaker-test -t wav`)
13. Confirm LED control via GPIO (quick Python `RPi.GPIO` test)
14. Connect display (HyperPixel 4.0 Square via DSI, or HDMI panel); configure `/boot/config.txt`
15. Confirm GLYPHBOX runtime launches fullscreen on the target display
16. Run a full end-to-end test: scan a card, load a game, hear audio, verify input

### Phase 3 — Enclosure Assembly
17. Install heat-set inserts in all M3 holes (soldering iron at 200°C)
18. Mount Pi to standoffs on rear shell floor
19. Mount camera bracket at calibrated height; route ribbon cable
20. Install LED strip on card slot rail
21. Install speaker; connect to MAX98357
22. Route all power wiring; install power switch on rear panel
23. Mount display in front panel cutout; connect DSI ribbon
24. Test fit front panel to rear shell — check all cutout alignments
25. Route controller USB cable through rear panel; confirm game loads and plays

### Phase 4 — Finishing
26. Label all internal connectors
27. Apply Kapton tape to protect ribbon cables from sharp edges
28. Final cable dress; use cable ties and 3M adhesive mounts
29. Close and fasten enclosure
30. Configure systemd auto-boot (see Section 12)
31. Final functional test: cold boot, card scan, game play, eject, rescan

---

## 11. Open Questions — Decisions Required Before Fabrication

These items require a decision before final enclosure dimensions and parts are locked.

### 11.1 Card Standard
**Question:** Will GLYPHBOX cards be credit-card size (85.6mm × 54mm) or A6 size (105mm × 148mm)?
**Impact:** Slot width, slot depth, card guide rail geometry, and Aztec code size (larger card = larger code = easier decode).
**Recommendation:** Credit-card size for the slot mechanism (cleaner UX, card fully disappears into slot). A6 for the printed card art (larger canvas). Design the card such that the Aztec code occupies the bottom-half of the A6 rear, and only that half inserts into the slot.

### 11.2 Display Selection
**Question:** HyperPixel 4.0 Square (DSI) vs Waveshare 4" HDMI?
**Impact:** Internal routing, driver complexity, Pi GPIO availability.
**Recommendation:** Prototype with HDMI panel for simplicity; migrate to HyperPixel for final build.

### 11.3 Camera-to-Slot Distance (Requires Physical Test)
**Question:** What exact height produces reliable Aztec decode on a credit-card-size code?
**Impact:** Enclosure internal height, camera mount design.
**Action required:** Conduct working-distance test with IMX708 before finalizing enclosure CAD. Set camera on an adjustable stand, run `cart-daemon.py`, scan a printed card at various heights, record success rate.

### 11.4 Single-Card vs Multi-Card Scan Flow
**Question:** For single-card games, does the user insert once and the game loads? For 2-card games, do they insert card 1, wait for "Code A" beep, then card 2?
**Impact:** UI feedback (LED behavior, display text), slot design (does it need to hold two cards?).
**Recommendation:** Sequential single-card insert — one card at a time, display shows "INSERT CARD 2" after card 1 is scanned.

### 11.5 Controller Cable Entry Point
**Question:** Does the coiled cable exit from the left side of the console, from the rear, or from the bottom?
**Impact:** Enclosure cutout location.
**Recommendation:** Left side of rear panel — keeps desk surface clear and cable arcs naturally to the user's left hand.

### 11.6 Ventilation / Passive vs Active Cooling
**Question:** Will the enclosure rely on passive convection (vent slots only) or include a small fan?
**Impact:** Pi 5 runs at 60–75°C under typical load. In a sealed 100mm-deep enclosure, passive cooling may be insufficient.
**Recommendation:** Include one 40mm × 10mm fan (Noctua NF-A4x10 5V PWM, $15) exhausting through the top. Wire to Pi 5 PWM fan header. Run quiet mode via Pi fan config. The Noctua is nearly silent at low RPM.

### 11.7 Physical Power Indication
**Question:** Is there a power LED? Where?
**Recommendation:** A single 3mm green LED on the rear panel (always-on when powered). Avoid front-panel LEDs that compete with the display and card slot glow.

### 11.8 SD Card Access Without Disassembly
**Question:** Can the SD card (or NVMe, if Pi 5 NVMe HAT is used) be accessed without opening the enclosure?
**Recommendation:** Design a small access door or slot in the bottom panel aligned with the Pi's microSD slot. Required for OS updates and troubleshooting.

---

## 12. Software Integration Notes — Fixed Card Slot Changes

When the physical slot is built, several software changes become relevant. The current code (`tools/cart-daemon.py` and `tools/qr-decode.py`) assumes a hand-held card in front of a free-pointing camera. The fixed slot changes the assumptions significantly.

### 12.1 Camera Configuration Changes

In `tools/cart-daemon.py`, the `_open_picamera2()` function currently uses `create_still_configuration()` with auto-exposure settling time of 1.5 seconds. For the fixed slot:

```python
# Replace create_still_configuration with a tuned still config:
cfg = cam.create_still_configuration(
    main={"size": (1920, 1080), "format": "RGB888"},  # or (2028, 1520) full sensor
    buffer_count=2,
)
# Add fixed focus distance (no autofocus hunting):
cam.set_controls({
    "AfMode": 0,              # Manual focus
    "LensPosition": 7.0,      # Tune this value: ~7 = ~100mm focus distance
    "ExposureTime": 15000,    # Fixed 15ms exposure (tune for LED brightness)
    "AnalogueGain": 1.5,      # Fixed gain
    "AwbEnable": False,       # No auto white balance (LEDs are fixed color)
    "ColourGains": (1.0, 1.0) # Neutral white balance (LEDs are green — adjust)
})
```

**LensPosition calibration:** The IMX708 LensPosition control is in diopters. For 100mm working distance: 1000mm/100mm = 10 diopters. Start at `LensPosition: 10.0` and adjust until sharp. A value of 7–10 is typical for 80–120mm working distance.

### 12.2 Scan Pipeline Simplification

Current pipeline in `qr-decode.py` uses multiple passes including CLAHE (contrast limited adaptive histogram equalization) and adaptive thresholding to handle poor lighting and perspective distortion. With fixed, controlled LED lighting and perpendicular card geometry:

- Pass 1 (zxing native binarizer): will succeed nearly always
- Pass 2 (hard threshold at 128): keep as fallback
- Remove CLAHE pass entirely — adds latency, not needed with controlled lighting
- Remove perspective correction / undistortion — card is always flat and perpendicular
- Reduce `_SCAN_INTERVAL` from 0.5s to 0.2s — scan twice as fast

**Target: decode in one pass, <200ms total latency from card insertion to code detected.**

### 12.3 LED Trigger Integration

Add LED control to the scan loop:

```python
import RPi.GPIO as GPIO
LED_PIN = 12  # BCM 12, hardware PWM

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
pwm = GPIO.PWM(LED_PIN, 1000)  # 1kHz
pwm.start(80)  # 80% duty cycle during scan

# After successful decode:
pwm.ChangeDutyCycle(100)  # full brightness on success
time.sleep(0.5)
pwm.ChangeDutyCycle(0)    # off when game launches
```

### 12.4 Card Presence Detection

Rather than scanning continuously (wasteful), consider adding a card-present sensor:

- **Option 1:** IR break-beam sensor across the slot aperture. Card insertion breaks the beam → triggers scan. Simple, reliable, costs ~$3 (Adafruit #2167).
- **Option 2:** A microswitch physical contact when card reaches the stop position. Most reliable, completely analog.
- **Option 3:** Software detection — scan at low frequency (1 fps), start high-frequency scanning when a code region is detected in frame.

**Recommendation:** Microswitch at the card stop position. Card insertion triggers the switch → GPIO interrupt → daemon starts scan loop → green LED pulses → decode → game loads. Zero wasted CPU cycles when no card is present.

GPIO interrupt setup:
```python
GPIO.add_event_detect(CARD_SWITCH_PIN, GPIO.RISING, callback=on_card_inserted, bouncetime=100)
```

### 12.5 Systemd Auto-Boot Configuration

The systemd service (`glyphbox.service`, present in the repository root) needs to be installed:

```
sudo cp glyphbox.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable glyphbox
sudo systemctl start glyphbox
```

The service should start `cart-daemon.py` (which manages both camera and runtime launch), not the runtime directly. The runtime is launched by the daemon as a subprocess when a valid cart is scanned.

Verify the `glyphbox.service` `ExecStart` line points to the correct Python path and script location on the Pi.

### 12.6 Display Output Configuration

On Pi with KMS/DRM (Pi OS Bookworm), the runtime is compiled with `PLATFORM_PI_HDMI` defined (see `main.c` line 289–295), which causes SDL2 to create a `SDL_WINDOW_FULLSCREEN_DESKTOP` window. This is correct behavior for both HDMI and DSI displays — SDL2 fills the physical display regardless of resolution.

For the HyperPixel 4.0 Square on Pi 5, ensure:
```
# /boot/firmware/config.txt (Pi 5 path)
dtoverlay=vc4-kms-dsi-hyperpixel4sq
display_auto_detect=0
```

The 128×128 logical size will letterbox to a 720×720 square on the HyperPixel, producing a clean 5.6× upscale with no black bars.

---

## 13. Reference Dimensions Summary

| Item | Dimension |
|---|---|
| Enclosure exterior | 150mm W × 200mm H × 100mm D |
| Display opening | 100mm × 100mm |
| Card slot opening | 120mm W × 5mm H |
| Card slot position (from bottom of front face) | 50mm center |
| Camera-to-slot working distance | 80–100mm (calibrate during Phase 1) |
| Speaker | 2.5–3 inch, bottom-mounted |
| Controller puck | ~80mm × 60mm × 25mm |
| Game card (target) | 85.6mm × 54mm (credit card) or A6 half-insert |
| Aztec code on card rear | ~95mm × 95mm |
| Internal volume | ~1,200 cc |
| Wall thickness (3D print) | 3mm |

---

## 14. Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Camera working distance too short for enclosure depth | Medium | Calibrate before CAD lock (Section 10, Phase 1) |
| HyperPixel DSI overlay incompatible with Pi 5 | Low–Medium | Test before ordering enclosure; fallback to HDMI panel |
| Pi 5 thermal throttling in sealed enclosure | Medium | Include 40mm fan; monitor with `vcgencmd measure_temp` |
| Aztec decode failure with fixed geometry | Low | Controlled lighting eliminates primary failure mode; test in cardboard prototype |
| Coiled cable USB signal integrity | Low | Keep cable under 2m; use 28 AWG cable; test with `lsusb` during input test |
| Card jam / retention issue | Medium | Prototype slot geometry in multiple iterations; adjust rail clearance |
| I2S audio driver conflict with DSI display | Low | Known working combination; test early |

---

*Document prepared March 2026. All part numbers and prices are indicative; verify availability before ordering.*
