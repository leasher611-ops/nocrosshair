import time
from evdev import uinput, ecodes as e

cap = {
    e.EV_KEY: [e.BTN_A, e.BTN_B, e.BTN_X, e.BTN_Y],
    e.EV_ABS: [(e.ABS_X, [0, -32768, 32767, 0, 15, 0])]
}
try:
    ui = uinput.UInput(events=cap, name="Test Controller", vendor=0x045E, product=0x028E)
    time.sleep(1)
    print("Writing BTN_B=1")
    ui.write(e.EV_KEY, e.BTN_B, 1)
    ui.syn()
    time.sleep(1)
    print("Writing BTN_B=0")
    ui.write(e.EV_KEY, e.BTN_B, 0)
    ui.syn()
    print("Success!")
except Exception as ex:
    print(f"Failed: {ex}")
