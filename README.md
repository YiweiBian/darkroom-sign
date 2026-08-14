# NanoLumens R&D Dark Room Sign

A dual-display room status sign for the R&D dark room, built on a Raspberry Pi Zero WH. Lets test engineers change the room status from inside using a Bluetooth numpad without leaving the room.

## Hardware
- Raspberry Pi Zero WH
- Waveshare 2.13" e-Paper HAT V4 (inside mirror)
- 160x40 LED panel via HDMI (outside sign)
- Havit SMART26 Bluetooth Numpad

## Key Mapping
| Key | Message |
|-----|---------|
| 1 | Clock |
| 2 | TEST IN PROGRESS / DO NOT ENTER |
| 3 | OCCUPIED / OTHER TESTING |
| 4 | ROOM NOT AVAILABLE |
| 5 | OPEN / COME ON IN |
| 6 | ON BREAK / BACK SOON |
| 7 | COME BACK IN 5 MIN |
| 8 | COME BACK IN 10 MIN |
| 9 | COME BACK IN 20 MIN |
| 0 | R&D DARK ROOM (idle) |
| Enter | Blank / Off |

## Versions
- v1.0 — Stable numpad-only version
- v2.0 — (planned) Flask web UI for browser-based control

## Author
Yiwei B. — NanoLumens R&D Engineering, 2026
