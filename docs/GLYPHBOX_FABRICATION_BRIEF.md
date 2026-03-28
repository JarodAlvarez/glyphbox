# GLYPHBOX — Physical Prototype Fabrication Brief

## What Is GLYPHBOX?

GLYPHBOX is a handmade fantasy console — a self-contained Raspberry Pi-based gaming device
inspired by retro consoles like the NES, Game Boy, and Pico-8. Games ("cartridges") are
distributed as printed card sets containing Aztec barcodes. Loading a game means holding the
physical card up to the device's built-in camera. The system scans, assembles, and launches
the game — no files, no internet, no menus.

It runs fullscreen at 512×512 pixels on an HDMI display, with a 30fps Lua-based runtime,
custom chiptune audio, and USB/2.4GHz gamepad support.

---

## Current Hardware Inventory

| Component | Spec | Notes |
|---|---|---|
| Computer | Raspberry Pi 4B | Primary target platform |
| Camera | Arducam 12MP IMX708 75D Autofocus | CSI ribbon, picamera2 |
| Controller | 8BitDo or PlayStation Classic (2018) | USB / 2.4GHz wireless |
| Display | External HDMI monitor | Temporary — final unit needs its own |
| OS | Raspberry Pi OS (64-bit) | Auto-boots directly into GLYPHBOX |

---

## The Cartridge System

- Games are encoded as **Aztec barcodes** printed on A6 (105×148mm) card stock
- Each card has a **front** (title art) and **rear** (barcode)
- Small games fit on **1 card**; larger games span **2, 4, or 8 cards**
- Cards are self-identifying — scan in any order, one at a time
- The system assembles all scanned cards and launches the game automatically
- A short jingle plays and a splash screen appears on successful load

### Card Physical Dimensions
- Card size: A6 — 105mm × 148mm
- Aztec code area: 95mm × 95mm centred on rear face
- Margins: 5mm all sides
- Title strip: top of rear face
- Card indicator: bottom of rear face (e.g. "CARD 2 / 4")

---

## Device Design Requirements

### Must Have
- **Camera window** — the IMX708 camera must have a clear, unobstructed view of cards
  held in front of it. Fixed position, pointing forward or slightly downward.
- **HDMI output** — either a built-in display or a rear HDMI port for an external TV/monitor
- **USB ports** — at least 2 accessible USB-A ports for controllers and power
- **Power button** — clean on/off, ideally with a status LED
- **Ventilation** — Pi 4 generates heat, especially during camera scanning
- **Camera alignment guide** — some visual indicator (recess, frame, LEDs) showing where
  to hold a card for scanning

### Nice to Have
- **Built-in display** — small HDMI-connected display (5"–7") integrated into the unit
- **Cartridge slot aesthetic** — a physical slot or recess the card slides into for scanning,
  even if purely decorative/alignment-only
- **Card storage** — slots, drawer, or pocket to store a small library of cards
- **Indicator LEDs** — scan progress, power state, scanning active
- **Speaker grille** — internal speaker (currently relies on HDMI audio or 3.5mm)
- **Status indicator** — shows scanning vs. running vs. idle

---

## Interaction Flow (for UX reference)

1. Power on → GLYPHBOX logo splash → idle scanning screen
2. User holds rear of card up to camera window
3. On successful scan: card dings, progress indicator fills
4. When all cards scanned: jingle plays, game title splash, game launches
5. Controller input drives game
6. Power off to exit (no software quit menu currently)

---

## Camera Placement Considerations

The IMX708 75D has a ~75° diagonal field of view with autofocus. For reliable scanning:

- **Optimal card distance**: ~15–25cm from lens
- **Card should fill ~50–70% of frame** at scanning distance
- Camera should be **mounted horizontally**, pointing forward
- A **physical card rest or guide** at the correct distance would improve consistency
- Avoid mounting camera pointing straight up (dust, parallax issues)
- Good ambient or supplemental lighting helps; avoid backlighting the card

---

## Form Factor Inspirations

The aesthetic direction is **handmade retro-futurist** — not a clone of any existing console,
but clearly in the lineage of 80s/90s home computers and toy electronics. Think:

- NES / Famicom — boxy, friendly, slot-fed
- Analogue Pocket — premium feel, clean lines
- Teenage Engineering products — exposed PCB aesthetic, honest materials
- Zine/DIY culture — something that looks like it was made with care, not mass-produced

---

## Known Constraints

- Pi 4B form factor: 85mm × 56mm × 17mm (without GPIO header)
- CSI ribbon cable for camera: max practical length ~200mm without signal issues
  (longer cables available with repeater, but adds complexity)
- USB-C power input (5V/3A minimum for Pi 4B stability)
- SDL2 renders at 512×512 — any display must support at least 720p HDMI input
- Gamepad is external (USB/2.4GHz dongle) — no built-in controls required for v1 prototype

---

## Questions for Fabrication Planning

1. **Enclosure material** — 3D printed (FDM/resin), laser-cut acrylic/wood, or hand-formed?
2. **Display** — integrated small panel, or designed around external TV/monitor for v1?
3. **Card scanning UX** — open slot the user reaches into, or external face the user holds
   card up to from outside?
4. **Card storage** — integrated into the device body, or a separate card wallet/sleeve?
5. **Speaker** — integrate a small 8Ω speaker with a PAM8403 amp board, or rely on HDMI audio?
6. **Power** — USB-C passthrough to Pi, or a dedicated power switch/barrel jack?
7. **Production intent** — single one-off prototype, or small batch (5–10 units)?

---

## Software Status (for context)

The software is fully functional:
- ✅ Pi auto-boots into GLYPHBOX via systemd
- ✅ Camera scanning with progress overlay
- ✅ Multi-card assembly (1, 2, 4, 8 card sets)
- ✅ Jingle + splash screen on successful cart load
- ✅ USB/2.4GHz gamepad support (8BitDo, PS Classic)
- ✅ Compressed cart format (up to ~9,600 bytes/game)
- ✅ Chiptune audio, pixel art renderer, Lua runtime

The physical prototype is the next milestone.
