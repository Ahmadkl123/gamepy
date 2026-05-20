#!/usr/bin/env python3
# ============================================================
# main.py — Entry point for Whispering Caverns
# ============================================================
#
# INSTALL:  pip install pygame
# RUN:      python main.py
#
# Controls:
#   Arrow / WASD     — Move
#   Space / W / Up   — Jump (double-jump supported)
#   Shift            — Dash
#   F / Left Mouse   — Attack
#   Esc              — Pause / Resume
#   M (when paused)  — Main Menu
#   Q                — Quit
#
from game import Game
from settings import dbg

if __name__ == '__main__':
    dbg("main.py -> starting Whispering Caverns")
    g = Game()
    dbg("main.py -> Game created, entering main loop")
    g.run()
