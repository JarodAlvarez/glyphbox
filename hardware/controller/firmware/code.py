import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

kbd = Keyboard(usb_hid.devices)

BUTTONS = [
    (board.GP2, Keycode.UP_ARROW),
    (board.GP3, Keycode.DOWN_ARROW),
    (board.GP4, Keycode.LEFT_ARROW),
    (board.GP5, Keycode.RIGHT_ARROW),
    (board.GP6, Keycode.Z),
    (board.GP7, Keycode.F2),
]

pins = []
for pin, _ in BUTTONS:
    p = digitalio.DigitalInOut(pin)
    p.direction = digitalio.Direction.INPUT
    p.pull = digitalio.Pull.UP
    pins.append(p)

held = [False] * len(BUTTONS)

while True:
    for i, (p, key) in enumerate(zip(pins, [k for _, k in BUTTONS])):
        pressed = not p.value
        if pressed and not held[i]:
            kbd.press(key)
            held[i] = True
        elif not pressed and held[i]:
            kbd.release(key)
            held[i] = False