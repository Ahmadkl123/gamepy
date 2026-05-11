# ============================================================
# score.py — Score persistence (read / write highscore)
# ============================================================
import json, os
from settings import HIGHSCORE_FILE


def load_highscore():
    """Return saved highscore, or 0 if none."""
    try:
        if os.path.exists(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE, 'r') as f:
                data = json.load(f)
                return int(data.get('highscore', 0))
    except Exception:
        pass
    return 0


def save_highscore(score):
    """Save a new highscore if it beats the current one."""
    current = load_highscore()
    if score > current:
        os.makedirs(os.path.dirname(HIGHSCORE_FILE), exist_ok=True)
        with open(HIGHSCORE_FILE, 'w') as f:
            json.dump({'highscore': score}, f)
        return True   # new highscore
    return False
