NoGui Demo frontend for emulation station
===================
This is an emulation station script that switches to a new random game after a predefined period of time unless someone is playing (input is detected).

Games volume stays low when nobody is playing and raises when input is detected.

Any game that exits in less than 10 seconds is considered corrupted and moved to "doesntwork" subfolder.


Installation
---

 1. Copy rungames.py to /home/pi/RetroPie/roms/rungames.py
 2. Make sure it's executable
 3. Copy emulators.cfg to /opt/retropie/configs/ports/nogui/emulators.cfg
 4. Restart emulation station

Disclaimer
---
This is a hack I put together in a couple hours. As of today I can only claim it works for me. I'll improve it as I find the time, but don't hold your breath.
