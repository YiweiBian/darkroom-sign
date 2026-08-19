# Dark Room Sign — Handover Notes

**From:** Yiwei Bian
**To:** Carlos
**Date:** August 2026
**Repo:** https://github.com/YiweiBian/nanolumens-darkroom-sign (branch `main`, tag `v2.0`)

---

## What it is

A status sign for the R&D dark room. A Bluetooth numpad inside the room switches the message on a 160x40 LED panel mounted outside, so people know whether they can walk in without interrupting a test. A small e-ink screen on the Pi itself mirrors the message so whoever is inside can confirm what the sign says without going out to look.

There is also a web UI for editing the messages and colors — see below.

---

## Day-to-day use

Nothing is required. The Pi runs 24/7 and everything auto-starts on boot.

To change the sign: press a key on the numpad.

| Key | Message |
|-----|---------|
| 1 | Clock |
| 2 | Test in progress / Do not enter |
| 3 | Occupied / Other testing |
| 4 | Room not available |
| 5 | Open / Come on in |
| 6 | On break / Back soon |
| 7 / 8 / 9 | Come back in 5 / 10 / 20 min |
| 0 | R&D Dark Room (default) |
| Enter | Blank |

The numpad sleeps to save battery. The first keypress after a while wakes it and reconnects — allow a few seconds, then press again.

---

## Editing messages and colors

`http://darkroom-sign.local:5000` in a browser, on the same network as the Pi.

- **Control tab** — buttons to change the sign, same as the numpad
- **Edit Messages tab** — change the text, colors, and flashing per mode

Changes save to the SD card and apply immediately. They survive reboots and power loss. Colors only affect the LED panel — the e-ink screen is black and white and only picks up the text.

The web UI is optional. If nobody touches it the sign keeps working with whatever was last saved.

---

## Getting the sign off Wi-Fi (recommended)

The sign works fully offline, so Wi-Fi is only needed to reach the web UI. Since IT flagged the wireless connection, the intended fix is to put the Pi on wired Ethernet instead.

**Status:** the USB-to-Ethernet adapter is recognized by the Pi (`lsusb` shows a Realtek RTL8153), but the link never came up — `eth0` stayed at `NO-CARRIER`. Most likely the cable or the switch port, since the adapter itself is detected and RTL8153 needs no driver install. It was not resolved before I left.

**To finish it:**

1. Connect the Pi's USB port (the data one, not PWR IN) to a USB hub or OTG adapter, then a USB-to-Ethernet adapter, then a cable to the NETGEAR switch.

2. Check the adapter is seen:
   ```bash
   lsusb
   ```
   Expect a line mentioning an Ethernet adapter. ASIX AX88772 and Realtek RTL8152/8153 chipsets work without any driver installation.

3. Check for a link:
   ```bash
   ip addr show eth0
   ```
   - `state UP` with an IP — done, the Pi is on the wired network
   - `NO-CARRIER` — the adapter is fine but there's no physical link. Try a different cable and a different switch port. Confirm the switch port LED lights up when the cable is seated.

4. Once wired works, disable Wi-Fi:
   ```bash
   sudo nmcli radio wifi off
   ```
   This persists across reboots. Re-enable with `sudo nmcli radio wifi on` if you ever need it.

5. Reach the web UI the same way as before — `http://darkroom-sign.local:5000`. Nothing in the software changes; the scripts don't care which interface carries the traffic.

**Note on power:** the Pi Zero's USB port supplies limited current. If the adapter is detected intermittently or the link is unstable, use a **powered** USB hub (one with its own adapter) rather than a bus-powered one.

---

## Changing the Wi-Fi network

If the Pi needs to move to a different network or a hotspot:

**Option A — over SSH, if you can still reach the Pi:**
```bash
sudo nmcli device wifi connect "<SSID>" password "<password>"
```
The connection may drop for a few seconds while it switches. If you lose SSH and it doesn't come back, use Option B.

**Option B — via the SD card, if the Pi is unreachable:**
1. Power down, remove the SD card, put it in a Windows machine
2. The `bootfs` partition will mount (the Linux partition won't — that's normal)
3. Create a file called `wpa_supplicant.conf` on `bootfs`:
   ```
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   country=US

   network={
       ssid="<SSID>"
       psk="<password>"
   }
   ```
4. Eject, reinsert into the Pi, power on

If that doesn't take, re-flash the card with Raspberry Pi Imager using the correct credentials and redeploy from the repo — the setup guide covers the full process and nothing is lost, since all the code is in Git.

---

## If something breaks

**First check:**
```bash
sudo systemctl status led-sign led-sign-hdmi led-sign-server --no-pager
```

All three should be `active (running)`. Restart anything that isn't:
```bash
sudo systemctl restart <service-name>
```

**Logs:**
```bash
sudo journalctl -u led-sign-hdmi -f
```

`SETUP.md` in the repo has a full troubleshooting section covering every failure mode hit during development — GPIO conflicts, the pygame/KMS framebuffer issue, systemd target problems, Bluetooth pairing. Worth reading through the first time something goes wrong; most of it has been seen before.

**Two things that look wrong but aren't:**
- Services showing a restart counter of 5-10 after boot — they lose a race with SPI or the framebuffer during startup and systemd restarts them automatically. They settle within a minute.
- Flask printing `WARNING: This is a development server` — expected, and fine at this scale.

---

## Rebuilding from scratch

Everything needed is in the repo. `SETUP.md` walks through it from flashing the SD card to installing the services. Three things there are easy to miss and each one costs an afternoon:

- **Console boot, not desktop** — pygame writes to the KMS framebuffer directly; the desktop session fights it
- **User must be in the `video` and `render` groups** — otherwise pygame exits with `video system not initialized`
- **Service symlinks must be in `multi-user.target.wants`** — if one lands in `graphical.target.wants` it never starts on a console-boot system

---

## Possible next steps

None of these are required — the system is complete as-is.

- **Enclosure** — the Pi and e-ink HAT are unhoused. Search Thingiverse or Printables for "Raspberry Pi Zero Waveshare 2.13 e-ink case"; several have wall-mount variants.
- **RTC module** — a DS3231 (~$5, I2C) would give accurate time offline. Right now clock mode shows "OFFLINE / INTERNET NEEDED" when there's no network, since the Pi Zero has no battery-backed clock.
- **Panel preview in the web UI** — render the actual pygame frame server-side and serve it as a PNG, so you can see what the panel shows without walking to it. Needs the render functions moved into a shared module both scripts import.
- **The `*` and `/` keys** — currently no-ops, reserved for brightness or a blink toggle if that's ever useful.

---

## Contact

The full development history, including every problem hit and how it was resolved, is in `NanoLumens_DarkRoom_Sign_Report.docx` in the repo.
