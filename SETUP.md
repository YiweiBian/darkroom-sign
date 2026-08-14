# Dark Room LED Sign — Setup Guide
Raspberry Pi Zero WH · Unicorn Hat Mini · BT Numpad · 160×40 HDMI LED Panel

---

## Architecture

```
[Raspberry Pi Zero WH]
       │
       ├── HDMI ──────────────→ 160×40 LED sign panel  (outside the lab)
       │                        pygame fullscreen window, exact panel res
       │
       ├── GPIO 40-pin ────────→ Unicorn Hat Mini       (inside the lab)
       │                        status mirror for the tech
       │
       └── Bluetooth ──────────→ Numeric keypad         (inside the lab)
                                 mode control
```

---

## 1. Flash the SD card

Raspberry Pi Imager → **Raspberry Pi OS with desktop (32-bit)**.
*(Pygame needs a display server — use the desktop image, not Lite.)*

In the gear/settings menu before flashing:
- Hostname: `darkroom-sign`
- Enable SSH
- Wi-Fi SSID + password
- Username/password

---

## 2. Force 160×40 HDMI resolution

SSH in, then:

```bash
sudo nano /boot/config.txt
```

Add at the bottom:

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=160 40 60 1 0 0 0
hdmi_drive=2
disable_overscan=1
```

Save, then reboot. After reboot, verify:

```bash
tvservice -s
# Should report: 160x40 @ 60Hz
```

---

## 3. Install dependencies

```bash
sudo apt update
sudo pip3 install unicornhatmini evdev pygame
```

---

## 4. Pair the Bluetooth numpad

```bash
sudo bluetoothctl
  power on
  agent on
  scan on
  # Put numpad into pairing mode, watch for its MAC address
  pair  XX:XX:XX:XX:XX:XX
  trust XX:XX:XX:XX:XX:XX
  connect XX:XX:XX:XX:XX:XX
  quit
```

Confirm it shows up as an input device:
```bash
python3 -c "from evdev import list_devices; print(list_devices())"
```

---

## 5. Deploy and test manually

```bash
mkdir -p /home/pi/led-sign
# From your workstation:
scp sign.py pi@darkroom-sign.local:/home/pi/led-sign/

# On the Pi:
cd /home/pi/led-sign
python3 sign.py
```

Press numpad keys to verify:
- `1` → red scrolling text + flashing white border on the panel
- `2` → cyan HH:MM clock
- `0` → blank
- `*` → cycles brightness
- `/` → toggles testing ↔ clock

---

## 6. Install as a systemd service

```bash
scp led-sign.service pi@darkroom-sign.local:/tmp/
# On the Pi:
sudo cp /tmp/led-sign.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable led-sign
sudo systemctl start led-sign

# Live logs:
sudo journalctl -u led-sign -f
```

The service targets `graphical.target` so it waits for the desktop session
(and therefore the HDMI display server) before launching pygame.

---

## 7. Numpad key reference

| Key | Action                                    |
|-----|-------------------------------------------|
| 1   | Testing in progress (red bg, scroll, border) |
| 2   | Clock mode (cyan HH:MM on black)          |
| 0   | Blank / off                               |
| *   | Cycle brightness (25 % → 50 % → 100 %)   |
| /   | Toggle testing ↔ clock                   |

---

## Troubleshooting

**Panel shows wrong resolution / desktop instead of sign**
- Double-check `/boot/config.txt` edits and reboot
- Run `tvservice -s` to confirm `160x40`
- If pygame opens a tiny window instead of fullscreen, the resolution
  didn't take — the `FULLSCREEN` flag forces the current desktop res

**Sign script can't open display**
- The service needs `DISPLAY=:0` — already set in `led-sign.service`
- If running via SSH manually: `export DISPLAY=:0` before `python3 sign.py`

**Numpad not detected**
- Check pairing: `bluetoothctl info XX:XX:XX:XX:XX:XX`
- The script retries every 2 s — give it ~15 s after boot
- If keys don't trigger modes, run this to inspect raw key codes:
  ```bash
  python3 -c "
  from evdev import InputDevice, list_devices, categorize, ecodes
  dev = InputDevice(list_devices()[0])
  for e in dev.read_loop():
      if e.type == ecodes.EV_KEY: print(categorize(e))
  "
  ```
  Then update `NUMPAD_MAP` in `sign.py` if the codes differ.

**Hat not lighting up**
- Confirm install: `pip3 show unicornhatmini`
- Hat must be fully seated on the 40-pin GPIO header
