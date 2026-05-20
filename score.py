# ============================================================
# score.py — Score persistence (read / write highscore)
# ============================================================
import json, os
from settings import HIGHSCORE_FILE, dbg


def load_highscore():
    """Return saved highscore, or 0 if none."""
    try:
        if os.path.exists(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE, 'r') as f:
                data = json.load(f)
                hs = int(data.get('highscore', 0))
                dbg(f"load_highscore -> {hs} (from {HIGHSCORE_FILE})")
                return hs
    except Exception as e:
        dbg(f"load_highscore -> failed ({e}), defaulting to 0")
        return 0
    dbg("load_highscore -> no save file, defaulting to 0")
    return 0


def save_highscore(score):
    """Save a new highscore if it beats the current one."""
    current = load_highscore()
    if score > current:
        os.makedirs(os.path.dirname(HIGHSCORE_FILE), exist_ok=True)
        with open(HIGHSCORE_FILE, 'w') as f:
            json.dump({'highscore': score}, f)
        dbg(f"save_highscore -> NEW highscore {score} (beat {current})")
        return True   # new highscore
    dbg(f"save_highscore -> {score} did not beat {current}, not saved")
    return False
