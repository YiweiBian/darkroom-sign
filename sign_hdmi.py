#!/usr/bin/env python3
"""
NanoLumens Dark Room Sign — HDMI version
Drives the 160x40 LED sign panel via HDMI using pygame.
Colors, flash, and border controlled via config.json / web UI.
"""
import json
import time
import threading
import datetime
import os
import pygame
from evdev import InputDevice, categorize, ecodes, list_devices

# -- Panel dimensions ----------------------------------------------------------
SIGN_W, SIGN_H = 160, 40
TEST_SCALE = int(os.environ.get("SIGN_TEST_SCALE", "0"))

# -- Base colours --------------------------------------------------------------
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_AMBER = (240, 170, 30)

# -- Shared state --------------------------------------------------------------
state_lock = threading.Lock()
state = {"mode": "idle", "running": True}

STATE_FILE  = '/home/nano_yiweib/led-sign/state.json'
CONFIG_FILE = '/home/nano_yiweib/led-sign/config.json'
_last_state_mtime = 0
_last_config_mtime = 0

def check_config_changed():
    global _last_config_mtime
    try:
        mtime = os.path.getmtime(CONFIG_FILE)
        if mtime != _last_config_mtime:
            _last_config_mtime = mtime
            return True
    except:
        pass
    return False

def hex_to_rgb(hex_str):
    """Convert #rrggbb to (r, g, b) tuple."""
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def check_state_file():
    global _last_state_mtime
    try:
        mtime = os.path.getmtime(STATE_FILE)
        if mtime != _last_state_mtime:
            _last_state_mtime = mtime
            with open(STATE_FILE) as f:
                data = json.load(f)
                return data.get('mode')
    except:
        pass
    return None

def load_config():
    defaults = {
        "idle":        {"line1": "R&D DARK ROOM",    "line2": "", "color1": "#ffffff", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "testing":     {"line1": "TEST IN PROGRESS", "line2": "DO NOT ENTER",  "color1": "#ffffff", "color2": "#ff0000", "border_color": "#ff0000", "flash": True},
        "occupied":    {"line1": "OCCUPIED",          "line2": "OTHER TESTING", "color1": "#ffffff", "color2": "#ff0000", "border_color": "#ff0000", "flash": True},
        "unavailable": {"line1": "ROOM",              "line2": "NOT AVAILABLE", "color1": "#ffffff", "color2": "#f4a261", "border_color": "#f4a261", "flash": False},
        "open":        {"line1": "OPEN",              "line2": "COME ON IN",    "color1": "#ffffff", "color2": "#2a9d8f", "border_color": "#2a9d8f", "flash": False},
        "break":       {"line1": "ON BREAK",          "line2": "BACK SOON",     "color1": "#ffffff", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "back5":       {"line1": "COME BACK IN",      "line2": "5 MIN",         "color1": "#ffffff", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "back10":      {"line1": "COME BACK IN",      "line2": "10 MIN",        "color1": "#ffffff", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "back20":      {"line1": "COME BACK IN",      "line2": "20 MIN",        "color1": "#ffffff", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "clock":       {"line1": "CLOCK",             "line2": "",              "color1": "#00d2d8", "color2": "#ffffff", "border_color": "#ffffff", "flash": False},
        "off":         {"line1": "",                  "line2": "",              "color1": "#000000", "color2": "#000000", "border_color": "#000000", "flash": False},
    }
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            modes = data.get('modes', {})
            for key in defaults:
                if key in modes:
                    defaults[key].update(modes[key])
    except:
        pass
    return defaults

# -- Font loader ---------------------------------------------------------------
def build_font(size, bold=True):
    return pygame.font.SysFont("dejavusansmono,monospace", size, bold=bold)

# -- Connectivity check --------------------------------------------------------
_last_connectivity_check = 0
_connectivity_cache = False

def is_connected():
    global _last_connectivity_check, _connectivity_cache
    now = time.time()
    if now - _last_connectivity_check < 30:
        return _connectivity_cache
    try:
        import socket
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        _connectivity_cache = True
    except:
        _connectivity_cache = False
    _last_connectivity_check = now
    return _connectivity_cache

# -- Renderers -----------------------------------------------------------------
def render_message(surface, font1, font2, font_single, mode, flash_on):
    config = load_config()
    cfg = config.get(mode, config["idle"])

    line1        = cfg.get("line1", "")
    line2        = cfg.get("line2", "")
    c1           = hex_to_rgb(cfg.get("color1", "#ffffff"))
    c2_base      = hex_to_rgb(cfg.get("color2", "#ffffff"))
    border_color = hex_to_rgb(cfg.get("border_color", "#ffffff"))
    flash        = cfg.get("flash", False)

    surface.fill(C_BLACK)

    if mode == "off" or not line1:
        return

    c2 = c2_base if (not flash or flash_on) else C_BLACK
    border_show = border_color if (not flash or flash_on) else C_BLACK

    if not line2:
        t1 = font_single.render(line1, True, c1)
        x = (SIGN_W - t1.get_width()) // 2
        y = (SIGN_H - t1.get_height()) // 2
        surface.blit(t1, (x, y))
    else:
        t1 = font1.render(line1, True, c1)
        surface.blit(t1, ((SIGN_W - t1.get_width()) // 2, 3))
        t2 = font2.render(line2, True, c2)
        surface.blit(t2, ((SIGN_W - t2.get_width()) // 2, 20))

    pygame.draw.rect(surface, border_show, (0, 0, SIGN_W, SIGN_H), 2)

def render_clock(surface, font_time, font_date, font_line1, font_line2):
    if not is_connected():
        surface.fill(C_BLACK)
        t1 = font_line1.render("OFFLINE", True, C_WHITE)
        t2 = font_line2.render("INTERNET NEEDED", True, C_AMBER)
        surface.blit(t1, ((SIGN_W - t1.get_width()) // 2, 8))
        surface.blit(t2, ((SIGN_W - t2.get_width()) // 2, 22))
        return
    surface.fill(C_BLACK)
    now = datetime.datetime.now()
    t_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%a %d %b")
    config = load_config()
    clock_color = hex_to_rgb(config["clock"].get("color1", "#00d2d8"))
    t_surf = font_time.render(t_str, True, clock_color)
    surface.blit(t_surf, ((SIGN_W - t_surf.get_width()) // 2,
                           (SIGN_H - t_surf.get_height()) // 2 - 4))
    d_surf = font_date.render(date_str, True, C_WHITE)
    surface.blit(d_surf, ((SIGN_W - d_surf.get_width()) // 2, SIGN_H - 11))

# -- Main display loop ---------------------------------------------------------
def display_loop():
    pygame.init()
    pygame.display.set_caption("Dark Room Sign")

    if TEST_SCALE > 0:
        window = pygame.display.set_mode((SIGN_W * TEST_SCALE, SIGN_H * TEST_SCALE))
        screen = pygame.Surface((SIGN_W, SIGN_H))
        print(f"Test mode: {TEST_SCALE}x scale")
    else:
        pygame.mouse.set_visible(False)
        window = pygame.display.set_mode((SIGN_W, SIGN_H), pygame.NOFRAME | pygame.FULLSCREEN)
        screen = window

    font_line1  = build_font(14)
    font_line2  = build_font(16)
    font_single = build_font(20)
    font_time   = build_font(20)
    font_date   = build_font(9, bold=False)

    clock       = pygame.time.Clock()
    flash_timer = 0.0
    flash_on    = True
    last_mode   = None
    last_second = None
    last_flash_on = None

    while True:
        web_mode = check_state_file()
        if web_mode:
            with state_lock:
                state["mode"] = web_mode

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

        with state_lock:
            mode    = state["mode"]
            running = state["running"]

        if not running:
            break

        dt = clock.tick(10) / 1000.0
        flash_timer += dt
        if flash_timer >= 0.5:
            flash_on    = not flash_on
            flash_timer = 0.0

        needs_redraw = False

        if check_config_changed():
            needs_redraw = True
            last_second  = None

        if mode != last_mode:
            needs_redraw = True
            last_mode    = mode
            last_second  = None

        if mode == "clock":
            now_second = datetime.datetime.now().second
            if now_second != last_second:
                needs_redraw = True
                last_second  = now_second
        else:
            config = load_config()
            is_flashing = config.get(mode, {}).get("flash", False)
            if is_flashing and flash_on != last_flash_on:
                needs_redraw = True
            last_flash_on = flash_on

        if needs_redraw:
            if mode == "clock":
                render_clock(screen, font_time, font_date, font_line1, font_line2)
            else:
                render_message(screen, font_line1, font_line2, font_single, mode, flash_on)

            if TEST_SCALE > 0:
                scaled = pygame.transform.scale(screen, (SIGN_W * TEST_SCALE, SIGN_H * TEST_SCALE))
                window.blit(scaled, (0, 0))

            pygame.display.flip()

    pygame.quit()

# -- Numpad listener -----------------------------------------------------------
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
    "1": "clock", "2": "testing", "3": "occupied", "4": "unavailable",
    "5": "open",  "6": "break",   "7": "back5",    "8": "back10",
    "9": "back20","0": "idle",    "enter": "off",
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
                if key in ("*", "/"):
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
            continue

# -- Entry point ---------------------------------------------------------------
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