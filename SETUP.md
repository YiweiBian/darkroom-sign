# Dark Room Sign — Setup Guide

Raspberry Pi Zero WH · Waveshare 2.13" e-Paper HAT V4 · 160x40 HDMI LED Panel · Havit SMART26 Bluetooth Numpad

**Version 2.0** — numpad control + Flask web UI for message and color customization.

---

## 1. Architecture

```
[Raspberry Pi Zero WH]
       |
       |-- HDMI ------------> 160x40 LED panel   (outside the dark room)
       |                      pygame via SDL KMS/DRM, color text on black
       |
       |-- GPIO 40-pin -----> Waveshare e-ink HAT (inside the lab)
       |                      PIL-rendered B&W images via SPI
       |
       |-- Bluetooth -------> Havit SMART26 numpad
       |                      evdev input, BlueZ handles reconnection
       |
       +-- Wi-Fi -----------> Flask web UI on port 5000
                              (optional — system runs fully offline)
```

Three systemd services, all auto-starting on boot:

| Service | Script | Purpose |
|---------|--------|---------|
| `led-sign` | `sign_eink.py` | e-ink HAT (inside mirror) |
| `led-sign-hdmi` | `sign_hdmi.py` | 160x40 LED panel (outside sign) |
| `led-sign-server` | `sign_server.py` | Flask web UI |

Both display scripts watch two files and redraw when either changes:

- `state.json` — current mode (written by numpad handler or web UI)
- `config.json` — message text, colors, flash settings

Because both are on the SD card, all customization survives reboots and power loss.

---

## 2. Flash the SD card

Raspberry Pi Imager -> **Raspberry Pi OS (32-bit, Debian Trixie with Desktop)**.

In OS Customisation before flashing:
- Hostname: `darkroom-sign`
- Enable SSH
- Wi-Fi SSID + password (Pi Zero WH is **2.4GHz only**)
- Username / password

> The desktop image is used, but the Pi boots to **console** (see step 4). The desktop packages are present but the GUI never starts.

---

## 3. Configure `/boot/config.txt`

Before first boot, edit `config.txt` on the `bootfs` partition.

Comment out these two lines in the middle of the file:

```
# dtoverlay=vc4-kms-v3d
# disable_fw_kms_setup=1
```

Add at the bottom, inside the `[all]` section:

```
hdmi_force_hotplug=1
dtoverlay=vc4-kms-v3d
hdmi_cvt=160 40 60 1 0 0 0
```

**What these do:**
- `hdmi_force_hotplug=1` — output HDMI even if no display is detected at boot
- `dtoverlay=vc4-kms-v3d` — load the KMS display driver (moved to `[all]` so it applies on any Pi model)
- `hdmi_cvt=160 40 60 1 0 0 0` — custom video timing: 160px wide, 40px tall, 60Hz

> When the actual 160x40 panel is connected, KMS reads the panel's native resolution directly, so the `hdmi_cvt` line is a fallback rather than the primary mechanism.

---

## 4. First boot

SSH in: `ssh <username>@darkroom-sign.local`

```bash
# Enable SPI (required for the e-ink HAT)
sudo raspi-config    # -> Interface Options -> SPI -> Yes

# Boot to console, not desktop
sudo raspi-config    # -> System Options -> Boot / Auto Login -> Console Autologin
```

**Console boot is required.** pygame uses the KMS/DRM framebuffer directly. With the desktop running, the sign competes with the desktop session and Wi-Fi auth popups can appear over the panel.

Reboot after both changes.

---

## 5. Install dependencies

```bash
sudo apt update
sudo apt install python3-pil python3-numpy -y
sudo pip3 install evdev pygame flask --break-system-packages
```

`--break-system-packages` is required on Debian Trixie, which protects the system Python by default. Safe for this single-purpose device.

Clone the Waveshare e-Paper library and copy the driver into the project:

```bash
git clone https://github.com/waveshare/e-Paper.git ~/e-Paper
mkdir -p ~/led-sign
cp -r ~/e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd ~/led-sign/
```

Driver in use: **`epd2in13_V4`** — confirmed working with this hardware. Other `epd2in13*` variants in that folder will not initialize correctly.

---

## 6. Grant framebuffer access

```bash
sudo usermod -a -G video,render <username>
```

pygame's `kmsdrm` driver needs access to `/dev/dri/card0`. Without these groups, `pygame.init()` fails silently and the script exits with `video system not initialized`. Reboot for the group change to apply.

Verify:

```bash
groups <username>     # should list video and render
SDL_VIDEODRIVER=kmsdrm python3 -c "import pygame; pygame.init(); print(pygame.display.Info())"
```

---

## 7. Pair the Bluetooth numpad

```bash
sudo rfkill unblock bluetooth
sudo bluetoothctl
```

Inside `bluetoothctl`:

```
power on
agent on
scan on
# put the numpad into pairing mode, note its MAC
pair  <MAC>
trust <MAC>
connect <MAC>
quit
```

`trust` matters — it lets BlueZ accept the numpad's reconnection automatically when it wakes from sleep. No reconnect watchdog script is needed; this was tested with `btmon` and confirmed the numpad initiates the connection itself.

The numpad sleeps after inactivity. Press any key and it reconnects within a few seconds.

---

## 8. Deploy

```bash
scp sign_eink.py sign_hdmi.py sign_server.py config.json <user>@darkroom-sign.local:~/led-sign/
scp led-sign.service led-sign-hdmi.service led-sign-server.service <user>@darkroom-sign.local:~/led-sign/
```

On the Pi:

```bash
sudo cp ~/led-sign/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable led-sign led-sign-hdmi led-sign-server
sudo systemctl start  led-sign led-sign-hdmi led-sign-server
```

**Verify the symlinks landed in the right target:**

```bash
ls -la /etc/systemd/system/multi-user.target.wants/ | grep led
```

All three must appear here. If one is in `graphical.target.wants` instead, it will never start on a console-boot system — `disable` then `enable` it to fix.

---

## 9. Numpad reference

| Key | Mode |
|-----|------|
| 1 | Clock |
| 2 | Test in progress / Do not enter |
| 3 | Occupied / Other testing |
| 4 | Room not available |
| 5 | Open / Come on in |
| 6 | On break / Back soon |
| 7 | Come back in 5 min |
| 8 | Come back in 10 min |
| 9 | Come back in 20 min |
| 0 | R&D Dark Room (idle default) |
| Enter | Blank / off |
| `*` `/` | Reserved (no-op) |

Message text for keys 2-9 and 0 is editable via the web UI. The key mapping itself is fixed in code.

---

## 10. Web UI

`http://darkroom-sign.local:5000` from any browser on the same network.

**Control tab** — one button per mode. Click to change the sign immediately. The current mode is shown at the top and polls every 3 seconds.

**Edit Messages tab** — per mode:
- Line 1 and line 2 text (auto-uppercased, 30 char limit)
- Line 1, line 2, and border colors — 8 quick swatches plus a hex field for custom values
- Flash toggle — flashes line 2 and the border together at 2Hz

Saving writes to `config.json`. Both displays detect the file change and redraw within a second.

**Colors apply to the HDMI panel only.** The e-ink HAT is black and white, so it takes the text but ignores color and flash settings.

---

## 11. Offline behaviour

The sign is fully functional with no network:

- Numpad control works (Bluetooth, not network)
- All saved messages and colors load from `config.json` on the SD card
- Clock mode shows **"OFFLINE / INTERNET NEEDED"** instead of a wrong time — the Pi Zero has no battery-backed RTC, so without NTP the clock is unreliable

Only the web UI requires network. Connect a hotspot when you want to reconfigure, then disconnect; settings persist indefinitely.

A DS3231 RTC module (~$5, I2C) would give accurate offline time if clock mode becomes important.

---

## Troubleshooting

### `lgpio.error: GPIO busy`
Another process holds the SPI pins. Stop the service before running the script by hand:
```bash
sudo systemctl stop led-sign
```

### `pygame.error: video system not initialized`
pygame can't reach the framebuffer. Check in order:
1. `SDL_VIDEODRIVER=kmsdrm` in `led-sign-hdmi.service` (not `x11`)
2. Pi is booting to console, not desktop
3. User is in the `video` and `render` groups
4. `ls -la /dev/dri/` shows `card0`

### A service shows `inactive (dead)` after boot
The symlink is in the wrong systemd target:
```bash
sudo systemctl disable <service>
sudo systemctl enable  <service>
ls -la /etc/systemd/system/multi-user.target.wants/ | grep led
```

### Services restart several times during boot
Normal. The restart counter in `systemctl status` reflects boot-time races (SPI or the framebuffer not ready yet). `Restart=on-failure` recovers automatically within a minute. Only investigate if a service never reaches `active (running)`.

### Numpad not responding
It's asleep — press any key and wait a few seconds. If it stays dead:
```bash
bluetoothctl info <MAC>     # expect Paired: yes, Trusted: yes
sudo rfkill unblock bluetooth
```
Both scripts recover from numpad disconnects automatically via an `OSError` handler; the input thread restarts and re-scans.

### Panel shows console text or the wrong resolution
Connect only the 160x40 panel — KMS reads whatever the attached display reports. A regular monitor will report its own native resolution and the sign will render tiny in the corner.

### Web UI unreachable
```bash
sudo systemctl status led-sign-server
```
Confirm the Pi and your machine are on the same network. If `.local` doesn't resolve, use the IP from `ip addr show wlan0`.

### Wi-Fi drops after an `nmcli` command
Wait 60 seconds — it usually recovers. If not, remove the SD card, create `wpa_supplicant.conf` on the `bootfs` partition with the correct SSID and password, then reboot.

### Flask "development server" warning
Expected. Flask prints this whenever it isn't behind a production WSGI server. Fine for a single sign on a lab network.

---

## File locations

| Path | Description |
|------|-------------|
| `~/led-sign/sign_eink.py` | e-ink display script |
| `~/led-sign/sign_hdmi.py` | HDMI panel script |
| `~/led-sign/sign_server.py` | Flask web server |
| `~/led-sign/config.json` | Message text, colors, flash settings |
| `~/led-sign/state.json` | Current mode |
| `~/led-sign/waveshare_epd/` | Waveshare e-Paper driver library |
| `/etc/systemd/system/led-sign*.service` | Service definitions |
| `/boot/config.txt` | HDMI resolution and KMS driver |

---

## Command reference

```bash
# Status
sudo systemctl status led-sign led-sign-hdmi led-sign-server --no-pager

# Restart
sudo systemctl restart led-sign led-sign-hdmi led-sign-server

# Live logs
sudo journalctl -u led-sign-hdmi -f

# Clean shutdown — always use this rather than pulling power
sudo shutdown -h now
```

Pulling power without shutting down risks SD card corruption. The Pi is designed to run 24/7; power cycling should be rare.
