# ============================================================
# levels.py — Level definitions and Platform class
# ============================================================
import pygame, random
from settings import *
from entities.powerup import Coin, PowerUp, Checkpoint, Chest


# ─────────────────────────────────────────────
#  PLATFORM / TILE SPRITE
# ─────────────────────────────────────────────
class Platform(pygame.sprite.Sprite):
    """A static solid platform tile."""

    def __init__(self, x, y, w, h, tile_surf):
        super().__init__()
        self.image = pygame.Surface((w, h))
        # Tile the surface texture
        for tx in range(0, w, TILE):
            for ty in range(0, h, TILE):
                self.image.blit(tile_surf, (tx, ty))
        # Top highlight
        pygame.draw.rect(self.image, (255, 255, 255, 40), (0, 0, w, 3))
        self.rect = pygame.Rect(x, y, w, h)


class HazardTile(pygame.sprite.Sprite):
    """Lava / spike tile that damages the player on contact."""

    def __init__(self, x, y, w, h, tile_surf):
        super().__init__()
        self.image = pygame.Surface((w, h))
        for tx in range(0, w, TILE):
            for ty in range(0, h, TILE):
                self.image.blit(tile_surf, (tx, ty))
        self.rect = pygame.Rect(x, y, w, h)


# ─────────────────────────────────────────────
#  LEVEL DATA
# ─────────────────────────────────────────────
# Each level dict:
#   platforms : list of (x, y, w, h, tile_key)
#   hazards   : list of (x, y, w, h)
#   enemies   : list of (type, x, y)   type = 'crawler'|'flyer'|'golem'
#   coins     : list of (x, y)
#   powerups  : list of (kind, x, y)
#   player_start : (x, y)
#   world_w, world_h
#   exit_rect : pygame.Rect  — area player must reach

LEVEL_1 = {
    'name'        : "The Entrance Cavern",
    'world_w'     : 3840,
    'world_h'     : 960,
    'bg_tint'     : (10, 5, 25),
    'player_start': (80, 700),
    'exit_rect'   : pygame.Rect(3594, 212, EXIT_W, EXIT_H),

    'platforms': [
        # Ground
        (0,   840, 3840, 120, 'stone'),

        # Lower platforms
        (200,  760, 200, 24, 'top'),
        (500,  720, 160, 24, 'top'),
        (750,  680, 240, 24, 'top'),
        (1050, 650, 180, 24, 'top'),
        (1300, 610, 200, 24, 'top'),
        (1600, 650, 160, 24, 'top'),
        (1850, 680, 280, 24, 'top'),

        # Mid platforms
        (300,  580, 160, 24, 'crystal'),
        (550,  540, 200, 24, 'crystal'),
        (840,  500, 240, 24, 'crystal'),
        (1150, 470, 180, 24, 'crystal'),
        (1400, 440, 200, 24, 'crystal'),
        (1700, 420, 160, 24, 'crystal'),
        (2000, 450, 220, 24, 'crystal'),
        (2300, 480, 200, 24, 'crystal'),

        # Ceiling platforms / walls
        (2500, 380, 300, 24, 'stone'),
        (2900, 340, 260, 24, 'stone'),
        (3200, 380, 200, 24, 'stone'),
        (3500, 340, 260, 24, 'stone'),

        # Walls
        (3780, 500, 60, 340, 'stone'),
        (0,    500, 60, 340, 'stone'),

        # Cave ceiling
        (0, 0, 3840, 96, 'stone'),
    ],

    'hazards': [],

    'enemies': [
        ('crawler', 600,  790),
        ('crawler', 900,  790),
        ('crawler', 1200, 790),
        ('crawler', 1600, 790),
        ('flyer',   700,  520),
        ('flyer',   1100, 480),
        ('flyer',   1700, 430),
        ('crawler', 2100, 790),
        ('crawler', 2500, 790),
        ('flyer',   2700, 400),
        ('crawler', 3100, 790),
        ('flyer',   3300, 400),
    ],

    'coins': [
        (250, 730), (520, 690), (770, 650), (1070, 620), (1320, 580),
        (1620, 620), (1870, 650), (360, 550), (640, 510), (920, 470),
        (1200, 440), (1470, 410), (1770, 390), (2100, 420), (2400, 450),
        (2600, 350), (2950, 310), (3250, 350), (3550, 310), (3650, 790),
    ],

    'powerups': [
        ('speed', 1000, 440),
        ('shield', 2600, 310),
    ],

    # Checkpoint torches - x is the torch FOOT center (must sit inside a platform)
    'checkpoints': [
        (1320, 840),   # mid-stage ground
        (2520, 840),   # late-stage ground
    ],
}

LEVEL_2 = {
    'name'        : "Crystal Depths",
    'world_w'     : 4320,
    'world_h'     : 1056,
    'bg_tint'     : (8, 3, 35),
    'player_start': (80, 900),
    'exit_rect'   : pygame.Rect(4044, 292, EXIT_W, EXIT_H),

    'platforms': [
        (0,   960, 4320, 96, 'stone'),
        # Ground islands
        (0, 960, 400, 96, 'stone'),
        (500, 880, 200, 24, 'crystal'),
        (800, 820, 240, 24, 'crystal'),
        (1100, 760, 200, 24, 'crystal'),
        (1400, 700, 240, 24, 'crystal'),
        (1700, 640, 200, 24, 'crystal'),
        (2000, 580, 300, 24, 'crystal'),
        (2400, 540, 200, 24, 'crystal'),
        (2700, 500, 240, 24, 'crystal'),
        (3000, 460, 200, 24, 'crystal'),
        (3300, 420, 240, 24, 'crystal'),
        (3600, 380, 200, 24, 'crystal'),
        (3900, 420, 360, 24, 'crystal'),
        # Walls
        (4260, 650, 60, 400, 'stone'),
        (0, 0, 4320, 96, 'stone'),
        # Floating stones
        (650, 680, 140, 24, 'stone'),
        (950, 600, 160, 24, 'stone'),
        (1300, 540, 140, 24, 'stone'),
        (1850, 500, 180, 24, 'stone'),
        (2250, 440, 140, 24, 'stone'),
        (2650, 380, 160, 24, 'stone'),
        (2950, 340, 140, 24, 'stone'),
        (3250, 300, 180, 24, 'stone'),
    ],

    'hazards': [],

    'enemies': [
        ('crawler', 550, 850),
        ('flyer',   850, 680),
        ('crawler', 1150, 730),
        ('golem',   1500, 670),
        ('flyer',   1800, 580),
        ('crawler', 2050, 550),
        ('flyer',   2450, 490),
        ('golem',   2750, 470),
        ('flyer',   3050, 400),
        ('crawler', 3350, 390),
        ('flyer',   3650, 350),
        ('golem',   3950, 390),
        ('flyer',   700,  600),
        ('flyer',   1400, 500),
    ],

    'coins': [
        (530, 850), (820, 790), (1120, 730), (1420, 670),
        (1720, 610), (2020, 550), (2420, 510), (2720, 470),
        (3020, 430), (3320, 390), (3620, 350), (3920, 390),
        (680, 650), (980, 570), (1330, 510), (1870, 470),
        (2270, 410), (2670, 350), (2970, 310), (3270, 270),
    ],

    'powerups': [
        ('speed',  1600, 620),
        ('shield', 3000, 300),
        ('speed',  3700, 340),
    ],

    'checkpoints': [
        (1500, 700),   # centered on the 1400-1640 / y=700 platform
        (2800, 500),   # centered on the 2700-2940 / y=500 platform
        (4060, 420),   # centered on the 3900-4260 / y=420 platform
    ],
}

LEVEL_3 = {
    'name'        : "The Whispering Core",
    'world_w'     : 4800,
    'world_h'     : 1152,
    'bg_tint'     : (20, 3, 10),
    'player_start': (80, 1000),
    'exit_rect'   : pygame.Rect(4664, 352, EXIT_W, EXIT_H),

    'platforms': [
        (0,   1056, 4800, 96, 'stone'),
        # Large sections
        (0, 1056, 300, 96, 'stone'),
        (400, 960, 200, 24, 'crystal'),
        (700, 880, 240, 24, 'crystal'),
        (1000, 800, 280, 24, 'crystal'),
        (1350, 720, 200, 24, 'crystal'),
        (1650, 640, 240, 24, 'crystal'),
        (1950, 560, 200, 24, 'crystal'),
        (2250, 480, 280, 24, 'crystal'),
        (2600, 420, 240, 24, 'crystal'),
        (2950, 360, 200, 24, 'crystal'),
        (3250, 300, 280, 24, 'crystal'),
        (3600, 360, 240, 24, 'crystal'),
        (3950, 400, 200, 24, 'crystal'),
        (4250, 440, 280, 24, 'crystal'),
        (4600, 480, 200, 96, 'stone'),
        # Ceiling
        (0, 0, 4800, 96, 'stone'),
        # Bridge platforms
        (550,  760, 120, 24, 'stone'),
        (850,  680, 120, 24, 'stone'),
        (1150, 600, 140, 24, 'stone'),
        (1500, 520, 120, 24, 'stone'),
        (1800, 440, 140, 24, 'stone'),
        (2100, 360, 120, 24, 'stone'),
        (2450, 280, 140, 24, 'stone'),
        (2800, 220, 160, 24, 'stone'),
        (3100, 180, 140, 24, 'stone'),
        (3400, 160, 200, 24, 'stone'),
        (3700, 200, 160, 24, 'stone'),
        (4000, 240, 200, 24, 'stone'),
        (4300, 280, 260, 24, 'stone'),
    ],

    'hazards': [],

    'enemies': [
        ('crawler', 450, 930), ('flyer', 750, 760),
        ('golem',   1050, 770), ('flyer', 1400, 670),
        ('crawler', 1700, 610), ('golem', 2000, 530),
        ('flyer',   2300, 430), ('crawler', 2650, 390),
        ('golem',   3000, 330), ('flyer', 3300, 250),
        ('golem',   3650, 240), ('flyer', 3950, 210),
        ('golem',   4300, 250), ('crawler', 4550, 380),
        # Extra flyers in the dark
        ('flyer', 600, 600), ('flyer', 1200, 500),
        ('flyer', 1900, 380), ('flyer', 2700, 300),
        ('flyer', 3500, 200), ('flyer', 4100, 220),
    ],

    'coins': [
        (420, 930), (720, 850), (1020, 770), (1370, 690),
        (1670, 610), (1970, 530), (2270, 450), (2620, 390),
        (2970, 330), (3270, 270), (3620, 230), (3970, 210),
        (4270, 250), (4520, 350), (570, 730), (870, 650),
        (1170, 570), (1520, 490), (1820, 410), (2120, 330),
        (2470, 250), (2820, 190), (3120, 150), (3420, 130),
        (3720, 170), (4020, 210), (4320, 250),
    ],

    'powerups': [
        ('speed',  1400, 660),
        ('shield', 2500, 400),
        ('speed',  3300, 230),
        ('shield', 4100, 180),
    ],

    'checkpoints': [
        (1450, 720),   # centered on the 1350-1550 / y=720 platform
        (2720, 420),   # centered on the 2600-2840 / y=420 platform
        (3780, 200),   # centered on the 3700-3860 / y=200 platform
    ],

    # Treasure chest — (foot_center_x, foot_center_y). Sits on the exit
    # ledge (4600-4800 / y=480) just right of the door: a final reward
    # before escaping the caverns.
    'chests': [
        (4770, 480),
    ],
}

BOSS_LEVEL = {
    'name'        : "Guardian of the Depths",
    'world_w'     : 2560,
    'world_h'     : 1024,
    'bg_tint'     : (5, 2, 30),
    'player_start': (100, 800),
    'exit_rect'   : pygame.Rect(2380, 300, EXIT_W, EXIT_H),
    'has_boss'    : True,

    'platforms': [
        # Ground
        (0, 920, 2560, 104, 'stone'),
        
        # Arena layout - spacious for boss fight
        # Left side
        (0, 600, 120, 24, 'crystal'),
        (200, 650, 150, 24, 'crystal'),
        (400, 600, 140, 24, 'crystal'),
        
        # Center arena - open space for boss movement
        (800, 700, 200, 24, 'stone'),
        (1200, 680, 200, 24, 'stone'),
        
        # Right side
        (1600, 650, 150, 24, 'crystal'),
        (1800, 600, 140, 24, 'crystal'),
        (2000, 650, 150, 24, 'crystal'),

        # Walls
        (2480, 400, 80, 620, 'stone'),
        (0, 400, 80, 520, 'stone'),

        # Ceiling
        (0, 0, 2560, 100, 'stone'),

        # Elevated platforms above
        (400, 350, 200, 24, 'crystal'),
        (1100, 300, 200, 24, 'crystal'),
        (1800, 350, 200, 24, 'crystal'),

        # Path to the exit door (right ledge)
        (2100, 540, 200, 24, 'crystal'),
        (2200, 428, 280, 24, 'stone'),
    ],

    'hazards': [],

    'enemies': [],  # Boss replaces normal enemies

    'coins': [
        (300, 570), (600, 570), (900, 670), (1200, 650),
        (1500, 570), (2000, 620), (450, 320), (1150, 270), (1850, 320),
    ],

    'powerups': [
        ('shield', 1000, 250),
        ('speed',  1500, 250),
    ],

    # No mid-arena checkpoints in the boss room - the room is the gauntlet.
    'checkpoints': [],
}

ALL_LEVELS = [LEVEL_1, BOSS_LEVEL, LEVEL_2, LEVEL_3]


# ─────────────────────────────────────────────
#  LEVEL BUILDER
# ─────────────────────────────────────────────
def build_level(level_data, tile_surfs, coin_frames, powerup_surfs,
                enemy_frames, PlayerClass, EnemyCls, chest_frames=None):
    """Instantiate all sprites from a level dict."""
    from entities.enemy import Crawler, Flyer, Golem

    dbg(f"build_level -> assembling {level_data['name']!r} "
        f"({level_data['world_w']}x{level_data['world_h']})")

    platforms   = pygame.sprite.Group()
    hazards     = pygame.sprite.Group()
    enemies     = pygame.sprite.Group()
    coins       = pygame.sprite.Group()
    powerups    = pygame.sprite.Group()
    checkpoints = pygame.sprite.Group()
    chests      = pygame.sprite.Group()

    # --- Platforms ---
    for (x, y, w, h, tile_key) in level_data['platforms']:
        platforms.add(Platform(x, y, w, h, tile_surfs[tile_key]))

    # --- Hazards ---
    for (x, y, w, h) in level_data.get('hazards', []):
        hazards.add(HazardTile(x, y, w, h, tile_surfs['lava']))

    # --- Enemies ---
    etype_map = {'crawler': Crawler, 'flyer': Flyer, 'golem': Golem}
    fnames_map = {'crawler': 'crawler', 'flyer': 'flyer', 'golem': 'golem'}
    for (etype, ex, ey) in level_data['enemies']:
        Cls    = etype_map[etype]
        frames = enemy_frames[fnames_map[etype]]
        enemies.add(Cls(ex, ey, frames))

    # --- Coins ---
    for (cx, cy) in level_data['coins']:
        coins.add(Coin(cx, cy, coin_frames))

    # --- Power-ups ---
    for (kind, px, py) in level_data.get('powerups', []):
        powerups.add(PowerUp(px, py, kind, powerup_surfs[kind]))

    # --- Checkpoint torches ---
    for (cx, cy) in level_data.get('checkpoints', []):
        checkpoints.add(Checkpoint(cx, cy))

    # --- Treasure chests --- (only built if the caller supplied sprites)
    if chest_frames:
        for (cx, cy) in level_data.get('chests', []):
            chests.add(Chest(cx, cy, chest_frames))

    # --- Player ---
    sx, sy = level_data['player_start']
    player = PlayerClass(sx, sy, enemy_frames['player'])

    dbg(f"build_level -> spawned player at {(sx, sy)}, "
        f"{len(platforms)} platforms, {len(hazards)} hazards, "
        f"{len(chests)} chests")

    return (player, platforms, hazards, enemies, coins, powerups,
            checkpoints, chests)
