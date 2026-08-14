#!/usr/bin/env python3
"""
NanoLumens Dark Room Sign — HDMI version
Drives the 160x40 LED sign panel via HDMI using pygame.

Mirrors the same mode set as sign_eink.py, but in color and with a live
seconds-updating clock (no refresh penalty like e-ink).

Numpad bindings  (identical to sign_eink.py)
---------------
  1     -> Clock (live HH:MM:SS)
  2     -> TESTING IN PROGRESS / DO NOT ENTER   (white / red, flashing)
  3     -> OCCUPIED - OTHER TESTING              (white / red, flashing)
  4     -> ROOM NOT AVAILABLE                    (amber)
  5     -> OPEN / COME ON IN                     (green)
  6     -> ON BREAK / BACK SOON                  (white)
  7     -> COME BACK IN 5 MIN                    (white)
  8     -> COME BACK IN 10 MIN                   (white)
  9     -> COME BACK IN 20 MIN                   (white)
  0     -> R&D DARK ROOM (idle / default)        (white)
  Enter -> Blank / off
  *     -> reserved (no-op)
"""

import time
import threading
import datetime
import os
import pygame
from evdev import InputDevice, categorize, ecodes, list_devices

# -- Panel dimensions ----------------------------------------------------------
SIGN_W, SIGN_H = 160, 40
FPS = 30

# Test mode: set SIGN_TEST_SCALE env var to run windowed at N times size
# on a regular monitor instead of fullscreen at native 160x40 on the panel.
# Example:  SIGN_TEST_SCALE=4 python3 sign_hdmi.py
TEST_SCALE = int(os.environ.get("SIGN_TEST_SCALE", "0"))

# -- Colours ---------------------------------------------------------------------
C_BLACK  = (0, 0, 0)
C_WHITE  = (255, 255, 255)
C_RED    = (220, 30, 30)
C_AMBER  = (240, 170, 30)
C_GREEN  = (60, 200, 90)
C_CYAN   = (0, 210, 200)

# -- Shared state -----------------------------------------------------------------
state_lock = threading.Lock()
state = {
    "mode":    "idle",
    "running": True,
}

# -- Mode -> (line1, line2, line1_color, line2_color, flash) -----------------------
# line2_color also doubles as the "urgent flash" color when flash=True
MODE_CONTENT = {
    "idle":        ("R&D DARK ROOM",     "",               C_WHITE, C_WHITE, False),
    "testing":     ("TEST IN PROGRESS",  "DO NOT ENTER",   C_WHITE, C_RED,   True),
    "occupied":    ("OCCUPIED",          "OTHER TESTING",  C_WHITE, C_RED,   True),
    "unavailable": ("ROOM",              "NOT AVAILABLE",  C_WHITE, C_AMBER, False),
    "open":        ("OPEN",              "COME ON IN",     C_WHITE, C_GREEN, False),
    "break":       ("ON BREAK",          "BACK SOON",      C_WHITE, C_WHITE, False),
    "back5":       ("COME BACK IN",      "5 MIN",          C_WHITE, C_WHITE, False),
    "back10":      ("COME BACK IN",      "10 MIN",         C_WHITE, C_WHITE, False),
    "back20":      ("COME BACK IN",      "20 MIN",         C_WHITE, C_WHITE, False),
    "off":         (None,                None,             C_BLACK, C_BLACK, False),
}

# -- Font loader -------------------------------------------------------------------
def build_font(size, bold=True):
    return pygame.font.SysFont("dejavusansmono,monospace", size, bold=bold)

# -- Renderers -----------------------------------------------------------------------
def render_message(surface, font1, font2, font_single, mode, flash_on):
    line1, line2, c1, c2_base, flash = MODE_CONTENT[mode]
    surface.fill(C_BLACK)

    if line1 is None:
        return   # off mode — blank screen

    c2 = c2_base if (not flash or flash_on) else C_BLACK

    if not line2:
        # Single line — use larger font, vertically centered
        t1 = font_single.render(line1, True, c1)
        x = (SIGN_W - t1.get_width()) // 2
        y = (SIGN_H - t1.get_height()) // 2
        surface.blit(t1, (x, y))
    else:
        # Two lines — top and bottom
        t1 = font1.render(line1, True, c1)
        surface.blit(t1, ((SIGN_W - t1.get_width()) // 2, 3))

        t2 = font2.render(line2, True, c2)
        surface.blit(t2, ((SIGN_W - t2.get_width()) // 2, 20))

    if flash and flash_on:
        pygame.draw.rect(surface, c2_base, (0, 0, SIGN_W, SIGN_H), 2)

def render_clock(surface, font_time, font_date):
    surface.fill(C_BLACK)
    now = datetime.datetime.now()
    t_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%a %d %b")

    t_surf = font_time.render(t_str, True, C_CYAN)
    surface.blit(t_surf, ((SIGN_W - t_surf.get_width()) // 2,
                           (SIGN_H - t_surf.get_height()) // 2 - 4))

    d_surf = font_date.render(date_str, True, C_WHITE)
    surface.blit(d_surf, ((SIGN_W - d_surf.get_width()) // 2, SIGN_H - 11))

# -- Main display loop ---------------------------------------------------------------
def display_loop():
    pygame.init()
    pygame.display.set_caption("Dark Room Sign")

    if TEST_SCALE > 0:
        window = pygame.display.set_mode((SIGN_W * TEST_SCALE, SIGN_H * TEST_SCALE))
        screen = pygame.Surface((SIGN_W, SIGN_H))   # logical 160x40 draw target
        print(f"Test mode: windowed at {TEST_SCALE}x scale "
              f"({SIGN_W*TEST_SCALE}x{SIGN_H*TEST_SCALE})")
    else:
        pygame.mouse.set_visible(False)
        window = pygame.display.set_mode((SIGN_W, SIGN_H), pygame.NOFRAME | pygame.FULLSCREEN)
        screen = window   # draw directly, no scaling needed

    font_line1   = build_font(14)
    font_line2   = build_font(16)
    font_single  = build_font(20)   # larger font for single-line messages
    font_time    = build_font(20)
    font_date    = build_font(9, bold=False)

    clock = pygame.time.Clock()
    flash_timer = 0.0
    flash_on = True
    last_mode = None
    last_second = None   # for clock mode, only redraw once per second
    last_flash_on = None

    # Static modes (no flash, not clock) only need ONE render until mode changes
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

        with state_lock:
            mode = state["mode"]
            running = state["running"]

        if not running:
            break

        # Tick at a low rate — we don't need 30fps, just enough to catch
        # mode changes and the 0.5s flash boundary promptly
        dt = clock.tick(10) / 1000.0
        flash_timer += dt
        if flash_timer >= 0.5:
            flash_on = not flash_on
            flash_timer = 0.0

        needs_redraw = False

        if mode != last_mode:
            needs_redraw = True
            last_mode = mode
            last_second = None   # force clock redraw too

        if mode == "clock":
            now_second = datetime.datetime.now().second
            if now_second != last_second:
                needs_redraw = True
                last_second = now_second
        else:
            is_flashing_mode = MODE_CONTENT.get(mode, (None,)*5)[4]
            if is_flashing_mode and flash_on != last_flash_on:
                needs_redraw = True
            last_flash_on = flash_on

        if needs_redraw:
            if mode == "clock":
                render_clock(screen, font_time, font_date)
            else:
                render_message(screen, font_line1, font_line2, font_single, mode, flash_on)

            if TEST_SCALE > 0:
                scaled = pygame.transform.scale(screen, (SIGN_W * TEST_SCALE, SIGN_H * TEST_SCALE))
                window.blit(scaled, (0, 0))

            pygame.display.flip()

    pygame.quit()

# -- Numpad listener -------------------------------------------------------------------
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
            dev = InputDevice(path)
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

                if key in ("*", "/"):
                    print(f"-> Key '{key}' pressed (no-op, reserved)")
                    continue

                mode = KEY_TO_MODE.get(key)
                if mode is None:
                    continue

                with state_lock:
                    state["mode"] = mode
                print(f"-> Mode: {mode}")

        except OSError as e:
            print(f"Numpad disconnected ({e}). Will look for it again...")
            time.sleep(2)
            continue   # loop back to find_numpad()

# -- Entry point -------------------------------------------------------------------------
if __name__ == "__main__":
    print("NanoLumens Dark Room Sign (HDMI)")
    print("  1=Clock 2=Testing 3=Occupied 4=Unavailable 5=Open 6=Break")
    print("  7/8/9=Back in 5/10/20  0=Idle  Enter=Off")

    t_input = threading.Thread(target=input_loop, daemon=True)
    t_input.start()

    try:
        display_loop()
    except KeyboardInterrupt:
        print("\nShutting down.")
