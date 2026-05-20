# ============================================================
# settings.py — Global constants for Whispering Caverns
# ============================================================

# --- Window ---
TITLE       = "Whispering Caverns"
SCREEN_W    = 1280
SCREEN_H    = 720
FPS         = 60

# --- Colors ---
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
RED         = (200, 50,  50)
GREEN       = (60,  200, 80)
BLUE        = (60,  120, 220)
YELLOW      = (255, 220, 50)
ORANGE      = (255, 140, 0)
PURPLE      = (140, 60,  200)
DARK_PURPLE = (30,  10,  50)
CYAN        = (80,  220, 220)
DARK_TEAL   = (20,  60,  70)
GREY        = (100, 100, 110)
DARK_GREY   = (40,  40,  50)
GOLD        = (255, 200, 30)
LIGHT_BLUE  = (140, 200, 255)

# Cavern palette
BG_COLOR     = (10,  5,   20)   # Very dark void
CAVE_DARK    = (25,  15,  40)
CAVE_MID     = (45,  30,  65)
CRYSTAL_GLOW = (120, 60,  220)
BIOLUM_GREEN = (60,  255, 120)
LAVA_RED     = (255, 80,  30)

# --- Tile sizes ---
TILE        = 48

# --- Physics ---
GRAVITY     = 0.65
MAX_FALL    = 18
JUMP_POWER  = -15
PLAYER_SPAX = 5      # base horizontal speed
DASH_SPEED  = 14
DASH_DUR    = 12     # frames
DASH_CD     = 40    # frames

# --- Player ---
PLAYER_HP        = 5
PLAYER_INVINCIBLE = 60  # frames of iframes after hit
ATTACK_RANGE     = 70
ATTACK_DUR       = 15
ATTACK_CD        = 25

# --- Enemies ---
CRAWLER_HP    = 2
CRAWLER_SPEED = 1.8
CRAWLER_DMG   = 1
CRAWLER_SCORE = 50

FLYER_HP      = 1
FLYER_SPEED   = 2.5
FLYER_DMG     = 1
FLYER_SCORE   = 75

GOLEM_HP      = 6
GOLEM_SPEED   = 0.9
GOLEM_DMG     = 2
GOLEM_SCORE   = 200

# --- Coins ---
COIN_VALUE    = 10
COIN_SPIN_SPD = 4   # animation frames per frame

# --- Score ---
HIGHSCORE_FILE = "data/highscore.json"
LEVEL_BONUS    = 500

# --- Treasure chest (final-stage reward) ---
CHEST_SCORE    = 1000   # score granted when the chest is opened
CHEST_LIVES    = 1      # extra lives granted when the chest is opened

# --- Camera ---
CAM_SMOOTH    = 0.12   # 0=instant, 1=never moves

# --- Particles ---
MAX_PARTICLES = 200

# --- Level ---
LEVEL_COUNT   = 4
EXIT_W        = 72
EXIT_H        = 128

# --- Lives & checkpoints ---
START_LIVES   = 3

# --- Debug ---
# Flip DEBUG to False to silence all the flow-tracing echoes at once.
DEBUG = True

def dbg(*args):
    """Echo a flow-tracing message to the console when DEBUG is on."""
    if DEBUG:
        print("[WC]", *args)
