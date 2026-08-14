#!/usr/bin/env python3
"""
NanoLumens Dark Room Sign — e-Ink version
Waveshare 2.13" e-Paper HAT V4 (250x122, black & white)

Numpad bindings
---------------
  1     -> Clock (static HH:MM, updates on keypress)
  2     -> TESTING IN PROGRESS / DO NOT ENTER
  3     -> OCCUPIED - OTHER TESTING
  4     -> ROOM NOT AVAILABLE
  5     -> OPEN / COME ON IN
  6     -> ON BREAK / BACK SOON
  7     -> COME BACK IN 5 MIN
  8     -> COME BACK IN 10 MIN
  9     -> COME BACK IN 20 MIN
  0     -> R&D DARK ROOM (idle / default)
  Enter -> Blank / off
  *     -> reserved (no-op)
"""

import time
import threading
import datetime
import os
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd2in13_V4
from evdev import InputDevice, categorize, ecodes, list_devices

# -- Display dimensions (landscape) -------------------------------------------
EPD_W = 250
EPD_H = 122

# -- Shared state ---------------------------------------------------------------
state_lock = threading.Lock()
state = {
    "mode":        "idle",   # see MODE keys below
    "running":     True,
    "needs_update": True,
}

# -- Font loader -----------------------------------------------------------------
def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

# -- Image builders ----------------------------------------------------------------
BORDER  = 6
PADDING = 10

def build_two_line_image(line1, line2, thick_border=True, show_divider=True):
    """Generic two-line centered message with optional thick border."""
    img  = Image.new("1", (EPD_W, EPD_H), 255)
    draw = ImageDraw.Draw(img)

    b = BORDER if thick_border else 2
    for i in range(b):
        draw.rectangle([i, i, EPD_W - 1 - i, EPD_H - 1 - i], outline=0)

    inner_x = b + PADDING

    font1 = load_font(20, bold=True)
    font2 = load_font(22, bold=True)

    bbox1 = draw.textbbox((0, 0), line1, font=font1)
    w1, h1 = bbox1[2] - bbox1[0], bbox1[3] - bbox1[1]
    bbox2 = draw.textbbox((0, 0), line2, font=font2)
    w2, h2 = bbox2[2] - bbox2[0], bbox2[3] - bbox2[1]

    divider_gap_top    = 6
    divider_gap_bottom = 8
    divider_h = 1 if show_divider else 0
    block_h = h1 + divider_gap_top + divider_h + divider_gap_bottom + h2

    y1 = (EPD_H - block_h) // 2
    x1 = (EPD_W - w1) // 2
    draw.text((x1, y1), line1, font=font1, fill=0)

    div_y = y1 + h1 + divider_gap_top
    if show_divider:
        draw.line([(inner_x, div_y), (EPD_W - inner_x, div_y)], fill=0, width=1)

    y2 = div_y + divider_h + divider_gap_bottom - (0 if show_divider else divider_gap_top - 2)
    x2 = (EPD_W - w2) // 2
    draw.text((x2, y2), line2, font=font2, fill=0)

    return img

def build_clock_image():
    now    = datetime.datetime.now()
    t_str  = now.strftime("%H:%M")
    img    = Image.new("1", (EPD_W, EPD_H), 255)
    draw   = ImageDraw.Draw(img)
    for i in range(BORDER):
        draw.rectangle([i, i, EPD_W - 1 - i, EPD_H - 1 - i], outline=0)

    font = load_font(60, bold=True)
    bbox = draw.textbbox((0, 0), t_str, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (EPD_W - w) // 2
    y = 8
    draw.text((x, y), t_str, font=font, fill=0)

    date_str  = now.strftime("%a %d %b")
    date_font = load_font(13)
    dbbox     = draw.textbbox((0, 0), date_str, font=date_font)
    dx        = (EPD_W - (dbbox[2] - dbbox[0])) // 2
    dy        = y + h + 10
    draw.text((dx, dy), date_str, font=date_font, fill=0)
    return img

def build_off_image():
    return Image.new("1", (EPD_W, EPD_H), 255)

def build_idle_image():
    """R&D Dark Room — default screen, single centered line."""
    img  = Image.new("1", (EPD_W, EPD_H), 255)
    draw = ImageDraw.Draw(img)
    for i in range(BORDER):
        draw.rectangle([i, i, EPD_W - 1 - i, EPD_H - 1 - i], outline=0)

    font = load_font(22, bold=True)
    text = "R&D DARK ROOM"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (EPD_W - w) // 2
    y = (EPD_H - h) // 2 - 8
    draw.text((x, y), text, font=font, fill=0)
    return img

# -- Mode -> renderer map -----------------------------------------------------------
def render_for_mode(mode):
    if mode == "clock":
        return build_clock_image()
    if mode == "testing":
        return build_two_line_image("TEST IN PROGRESS", "DO NOT ENTER")
    if mode == "occupied":
        return build_two_line_image("OCCUPIED", "OTHER TESTING")
    if mode == "unavailable":
        return build_two_line_image("ROOM", "NOT AVAILABLE", show_divider=False)
    if mode == "open":
        return build_two_line_image("OPEN", "COME ON IN", thick_border=False)
    if mode == "break":
        return build_two_line_image("ON BREAK", "BACK SOON", thick_border=False)
    if mode == "back5":
        return build_two_line_image("COME BACK IN", "5 MIN", thick_border=False)
    if mode == "back10":
        return build_two_line_image("COME BACK IN", "10 MIN", thick_border=False)
    if mode == "back20":
        return build_two_line_image("COME BACK IN", "20 MIN", thick_border=False)
    if mode == "off":
        return build_off_image()
    # default / idle
    return build_idle_image()

# -- Display loop ------------------------------------------------------------------
def display_loop():
    print("Initialising e-ink display...")
    epd = epd2in13_V4.EPD()
    epd.init()
    epd.Clear(0xFF)

    last_mode = None

    while True:
        with state_lock:
            mode         = state["mode"]
            running      = state["running"]
            needs_update = state["needs_update"]
            if needs_update:
                state["needs_update"] = False

        if not running:
            break

        redraw = needs_update or (mode != last_mode)

        if redraw:
            print(f"  Rendering: {mode}")
            img = render_for_mode(mode)
            img = img.rotate(180)   # flip if hat is mounted upside down

            epd.init()
            epd.display(epd.getbuffer(img))
            epd.sleep()
            last_mode = mode

        time.sleep(1)

    epd.init()
    epd.Clear(0xFF)
    epd.sleep()

# -- Numpad listener -----------------------------------------------------------------
NUMPAD_MAP = {
    ecodes.KEY_KP0:        "0",
    ecodes.KEY_KP1:        "1",
    ecodes.KEY_KP2:        "2",
    ecodes.KEY_KP3:        "3",
    ecodes.KEY_KP4:        "4",
    ecodes.KEY_KP5:        "5",
    ecodes.KEY_KP6:        "6",
    ecodes.KEY_KP7:        "7",
    ecodes.KEY_KP8:        "8",
    ecodes.KEY_KP9:        "9",
    ecodes.KEY_KPASTERISK: "*",
    ecodes.KEY_KPSLASH:    "/",
    ecodes.KEY_KPENTER:    "enter",
}

KEY_TO_MODE = {
    "1": "clock",
    "2": "testing",
    "3": "occupied",
    "4": "unavailable",
    "5": "open",
    "6": "break",
    "7": "back5",
    "8": "back10",
    "9": "back20",
    "0": "idle",
    "enter": "off",
}

def find_numpad():
    for path in list_devices():
        try:
            dev  = InputDevice(path)
            caps = dev.capabilities()
            keys = caps.get(ecodes.EV_KEY, [])
            if ecodes.KEY_KP1 in keys and ecodes.KEY_KP2 in keys:
                return dev
        except Exception:
            continue
    return None

def input_loop():
    while True:
        print("Waiting for Bluetooth numpad...")
        dev = None
        attempts = 0
        while dev is None:
            dev = find_numpad()
            if dev is None:
                attempts += 1
                if attempts % 5 == 0:
                    print(f"  Still looking for numpad... ({attempts*2}s)")
                time.sleep(2)
        print(f"Numpad found: {dev.name}")

        try:
            for event in dev.read_loop():
                if event.type != ecodes.EV_KEY:
                    continue
                ke = categorize(event)
                if ke.keystate != ke.key_down:
                    continue
                key = NUMPAD_MAP.get(event.code)
                if key is None:
                    continue

                if key == "*" or key == "/":
                    print(f"-> Key '{key}' pressed (no-op, reserved for future use)")
                    continue

                mode = KEY_TO_MODE.get(key)
                if mode is None:
                    continue

                with state_lock:
                    state["mode"]         = mode
                    state["needs_update"] = True
                print(f"-> Mode: {mode}")

        except OSError as e:
            print(f"Numpad disconnected ({e}). Will look for it again...")
            time.sleep(2)
            continue

# -- Entry point -----------------------------------------------------------------------
if __name__ == "__main__":
    print("NanoLumens Dark Room Sign (e-ink)")
    print("  1=Clock 2=Testing 3=Occupied 4=Unavailable 5=Open 6=Break")
    print("  7/8/9=Back in 5/10/20  0=Idle  Enter=Off")

    t_input = threading.Thread(target=input_loop, daemon=True)
    t_input.start()

    try:
        display_loop()
    except KeyboardInterrupt:
        print("\nShutting down.")
