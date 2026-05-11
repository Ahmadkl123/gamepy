# ============================================================
# assets/generate_assets.py — Procedural placeholder art
# Called once at startup to create all needed surfaces.
# ============================================================
import os
import pygame, math, random
from settings import *


def _circle_surf(radius, color, glow_color=None):
    s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    if glow_color:
        for r in range(radius, 0, -2):
            a = int(120 * (1 - r/radius))
            pygame.draw.circle(s, (*glow_color, a), (radius, radius), r)
    pygame.draw.circle(s, color, (radius, radius), radius)
    return s


def _fit_frame_to_canvas(frame, target_height=None, canvas_size=None):
    """Trim transparent padding, preserve aspect ratio, and bottom-align on a canvas."""
    bounds = frame.get_bounding_rect()
    if bounds.width > 0 and bounds.height > 0:
        trimmed = pygame.Surface(bounds.size, pygame.SRCALPHA)
        trimmed.blit(frame, (0, 0), bounds)
    else:
        trimmed = frame

    if target_height:
        scale = target_height / max(1, trimmed.get_height())
        scaled_w = max(1, round(trimmed.get_width() * scale))
        scaled_h = max(1, round(trimmed.get_height() * scale))
        trimmed = pygame.transform.scale(trimmed, (scaled_w, scaled_h))

    if not canvas_size:
        return trimmed

    canvas = pygame.Surface(canvas_size, pygame.SRCALPHA)
    x = (canvas_size[0] - trimmed.get_width()) // 2
    y = canvas_size[1] - trimmed.get_height()
    canvas.blit(trimmed, (x, y))
    return canvas


def _load_strip_frames(sheet_path, frame_count, target_height=None, canvas_size=None):
    """Load a horizontal sprite strip using an explicit frame count."""
    if not os.path.exists(sheet_path):
        return None

    sheet = pygame.image.load(sheet_path).convert_alpha()
    sheet_w, sheet_h = sheet.get_size()
    frame_w = sheet_w // frame_count
    frames = []

    for i in range(frame_count):
        rect = pygame.Rect(i * frame_w, 0, frame_w, sheet_h)
        frame = pygame.Surface((frame_w, sheet_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), rect)
        frames.append(_fit_frame_to_canvas(frame, target_height, canvas_size))

    return frames


def make_player_frames():
    """Return dict of animation frames for the player."""
    player_dir = os.path.join(os.path.dirname(__file__), 'images', 'player')
    sheet_specs = {
        'idle'  : 'idle_right_down.png',
        'run'   : 'walk_right_down.png',
        'jump'  : 'jump_right_up.png',
        'attack': 'dash_right_down.png',
        'dash'  : 'dash_right_up.png',
        'hurt'  : 'jump_right_down.png',
        'dead'  : 'death_right_down.png',
    }

    frames = {}
    for state, filename in sheet_specs.items():
        loaded = _load_strip_frames(
            os.path.join(player_dir, filename),
            frame_count=8,
            target_height=46,
            canvas_size=(40, 48),
        )
        if loaded:
            frames[state] = loaded

    if len(frames) == len(sheet_specs):
        return frames

    # Fallback procedural player
    frames = {}
    W, H = 32, 48

    def _body(color, eye_x_offset=0, attacking=False):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (60, 30, 90), (2, 8, W-4, H-4))
        pygame.draw.rect(s, color, (8, 12, 16, 28), border_radius=4)
        pygame.draw.circle(s, (220, 185, 150), (W//2, 10), 10)
        pygame.draw.arc(s, CYAN, (W//2-9, 2, 18, 16), 0, math.pi, 3)
        ex = W//2 + eye_x_offset
        pygame.draw.circle(s, CYAN,  (ex, 10), 3)
        pygame.draw.circle(s, WHITE, (ex, 10), 1)
        if attacking:
            pygame.draw.line(s, (255, 255, 180), (W-4, 20), (W+10, 8), 3)
            pygame.draw.line(s, WHITE, (W-2, 22), (W+8, 10), 1)
        return s

    frames['idle']   = [_body((80, 50, 130))]
    frames['run']    = [_body((80, 50, 130), eye_x_offset=i % 2) for i in range(4)]
    frames['jump']   = [_body((100, 70, 160))]
    frames['attack'] = [_body((120, 60, 100), attacking=True),
                        _body((100, 50, 80), attacking=True)]
    frames['dash']   = [_body((60, 200, 220))]
    frames['hurt']   = [_body((220, 80, 80))]
    frames['dead']   = [_body((60, 40, 80))]
    return frames


def make_crawler_frames():
    """Load the ground enemy as a skeleton sprite pack, fall back to a bat."""
    skeleton_dir = os.path.join(os.path.dirname(__file__), 'images', 'skeleton')
    sheet_specs = {
        'attack': ('Skeleton Attack.png', 18),
        'dead'  : ('Skeleton Dead.png', 15),
        'hit'   : ('Skeleton Hit.png', 8),
        'idle'  : ('Skeleton Idle.png', 11),
        'react' : ('Skeleton React.png', 4),
        'walk'  : ('Skeleton Walk.png', 13),
    }

    frames = {}
    for state, (filename, frame_count) in sheet_specs.items():
        loaded = _load_strip_frames(
            os.path.join(skeleton_dir, filename),
            frame_count=frame_count,
            target_height=58,
            canvas_size=(72, 64),
        )
        if loaded:
            frames[state] = loaded

    if len(frames) == len(sheet_specs):
        return frames

    bat_frames = []
    W, H = 40, 28
    for i in range(4):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        wing_y = 6 + (i % 2) * 4
        pts_l = [(W//2, H//2), (0, wing_y), (8, H-4)]
        pts_r = [(W//2, H//2), (W, wing_y), (W-8, H-4)]
        pygame.draw.polygon(s, (120, 40, 40), pts_l)
        pygame.draw.polygon(s, (120, 40, 40), pts_r)
        pygame.draw.ellipse(s, (80, 20, 20), (W//2-8, H//2-6, 16, 14))
        pygame.draw.circle(s, RED, (W//2-3, H//2-2), 3)
        pygame.draw.circle(s, RED, (W//2+3, H//2-2), 3)
        pygame.draw.circle(s, (255, 160, 160), (W//2-3, H//2-2), 1)
        bat_frames.append(s)

    return {
        'idle'  : [bat_frames[0]],
        'walk'  : bat_frames,
        'attack': bat_frames,
        'hit'   : bat_frames[:2],
        'react' : bat_frames[:2],
        'dead'  : [pygame.transform.rotate(frame, 90) for frame in bat_frames[:2]],
    }


def make_flyer_frames():
    """Load Flyer from Attack3.png (900x150, 6 frames of 150x150). Falls back to procedural."""
    sheet_path = os.path.join(os.path.dirname(__file__), 'images', 'Attack3.png')
    if os.path.exists(sheet_path):
        sheet = pygame.image.load(sheet_path).convert()
        sheet.set_colorkey((0, 0, 0))
        FRAME_W, FRAME_H = 150, 150
        NUM_FRAMES = 6
        DISPLAY_W, DISPLAY_H = 80, 80
        frames = []
        for i in range(NUM_FRAMES):
            rect  = pygame.Rect(i * FRAME_W, 0, FRAME_W, FRAME_H)
            frame = pygame.Surface((FRAME_W, FRAME_H), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frame = pygame.transform.scale(frame, (DISPLAY_W, DISPLAY_H))
            frames.append(frame)
        return frames
    # Fallback procedural ghost
    frames = []
    W, H = 36, 44
    for i in range(4):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        pulse = math.sin(i * math.pi / 2) * 4
        r = int(W//2 - 2 + pulse)
        for layer in range(5):
            a = 180 - layer * 30
            pygame.draw.ellipse(s, (80, 40, 180, a),
                (W//2 - r + layer, 4 + layer, (r-layer)*2, H - 8))
        for t in range(3):
            tx = W//4 + t * W//4
            ty_off = int(math.sin(i + t) * 4)
            pygame.draw.line(s, (60, 30, 140), (tx, H-10), (tx, H+ty_off), 3)
        pygame.draw.circle(s, (200, 80, 255), (W//2-5, H//3), 5)
        pygame.draw.circle(s, (200, 80, 255), (W//2+5, H//3), 5)
        pygame.draw.circle(s, WHITE, (W//2-5, H//3), 2)
        pygame.draw.circle(s, WHITE, (W//2+5, H//3), 2)
        frames.append(s)
    return frames


def make_projectile_frames():
    """Load spinning projectile from projectile_sprite.png (384x48, 8 frames of 48x48)."""
    sheet_path = os.path.join(os.path.dirname(__file__), 'images', 'projectile_sprite.png')
    if os.path.exists(sheet_path):
        sheet = pygame.image.load(sheet_path).convert()
        sheet.set_colorkey((0, 0, 0))
        FRAME_W, FRAME_H = 48, 48
        NUM_FRAMES = 8
        DISPLAY_SIZE = 24
        frames = []
        for i in range(NUM_FRAMES):
            rect  = pygame.Rect(i * FRAME_W, 0, FRAME_W, FRAME_H)
            frame = pygame.Surface((FRAME_W, FRAME_H), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), rect)
            frame = pygame.transform.scale(frame, (DISPLAY_SIZE, DISPLAY_SIZE))
            frames.append(frame)
        return frames
    # Fallback procedural orb
    frames = []
    for i in range(8):
        s = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(s, (180, 80, 40), (12, 12), 10)
        pygame.draw.circle(s, (255, 160, 80), (12, 12), 6)
        pygame.draw.circle(s, WHITE, (12, 12), 3)
        frames.append(s)
    return frames


def make_golem_frames():
    """Rock golem boss-tier enemy frames."""
    frames = []
    W, H = 56, 72
    for i in range(4):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        shake = i % 2
        # Body
        pygame.draw.rect(s, (70, 55, 45), (8+shake, 16, 40, 50), border_radius=6)
        # Head
        pygame.draw.rect(s, (85, 65, 50), (12+shake, 4, 32, 28), border_radius=4)
        # Cracks
        for cx, cy in [(18, 20), (30, 30), (22, 44)]:
            pygame.draw.line(s, (40, 30, 20), (cx, cy), (cx+8, cy+6), 2)
        # Glowing core
        pygame.draw.circle(s, LAVA_RED, (W//2, 40), 8)
        pygame.draw.circle(s, ORANGE,   (W//2, 40), 5)
        # Eyes
        pygame.draw.circle(s, ORANGE, (W//2-8, 14), 5)
        pygame.draw.circle(s, ORANGE, (W//2+8, 14), 5)
        frames.append(s)
    return frames


def make_coin_frames():
    """Spinning coin animation."""
    sheet_path = os.path.join(os.path.dirname(__file__), 'images', 'coins', 'coin1_16x16.png')
    if os.path.exists(sheet_path):
        frames = _load_strip_frames(
            sheet_path,
            frame_count=15,
            target_height=22,
            canvas_size=(28, 28),
        )
        if frames:
            return frames

    frames = []
    for i in range(8):
        W = max(4, int(24 * abs(math.cos(i * math.pi / 8))))
        s = pygame.Surface((28, 28), pygame.SRCALPHA)
        cx = 14
        pygame.draw.ellipse(s, GOLD,  (cx - W//2, 4, W, 20))
        pygame.draw.ellipse(s, YELLOW,(cx - W//2+2, 6, max(1,W-4), 16))
        pygame.draw.ellipse(s, WHITE, (cx - W//2+W//2-2, 9, 4, 10))
        frames.append(s)
    return frames


def make_powerup_surfaces():
    """Speed orb and shield orb surfaces."""
    speed = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(speed, (255, 200, 50), (14, 14), 12)
    pygame.draw.circle(speed, WHITE,           (14, 14), 8)
    # Lightning bolt
    pts = [(10,6),(16,12),(12,12),(18,22),(13,14),(17,14)]
    pygame.draw.polygon(speed, ORANGE, pts)

    shield = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(shield, (50, 150, 255), (14, 14), 12)
    pygame.draw.circle(shield, WHITE,           (14, 14), 8)
    pygame.draw.polygon(shield, CYAN,
        [(14,4),(22,10),(20,20),(14,24),(8,20),(6,10)])

    return {'speed': speed, 'shield': shield}


def make_exit_surface():
    """Load the level exit door art, preserving its aspect ratio."""
    door_path = os.path.join(os.path.dirname(__file__), 'images', 'doors', 'Door 6.png')
    if os.path.exists(door_path):
        door = pygame.image.load(door_path).convert_alpha()
        return _fit_frame_to_canvas(door, target_height=EXIT_H - 4, canvas_size=(EXIT_W, EXIT_H))

    fallback = pygame.Surface((EXIT_W, EXIT_H), pygame.SRCALPHA)
    pygame.draw.rect(fallback, (60, 55, 60), (8, 6, EXIT_W - 16, EXIT_H - 10), border_radius=6)
    pygame.draw.rect(fallback, (35, 30, 35), (14, 14, EXIT_W - 28, EXIT_H - 24), border_radius=4)
    pygame.draw.rect(fallback, (120, 120, 130), (EXIT_W - 22, EXIT_H // 2, 8, 8), border_radius=4)
    return fallback


def make_tile_surfaces():
    """Return dict of platform tile surfaces."""
    tiles = {}

    # --- Stone wall tile ---
    stone = pygame.Surface((TILE, TILE))
    stone.fill((55, 45, 60))
    for _ in range(10):
        rx, ry = random.randint(0, TILE-4), random.randint(0, TILE-4)
        rw, rh = random.randint(2, 6),       random.randint(1, 3)
        c = random.randint(35, 70)
        pygame.draw.rect(stone, (c, c-10, c+5), (rx, ry, rw, rh))
    pygame.draw.rect(stone, (80, 65, 90), (0, 0, TILE, TILE), 1)
    tiles['stone'] = stone

    # --- Crystal platform tile ---
    crystal = pygame.Surface((TILE, TILE))
    crystal.fill((35, 20, 55))
    for _ in range(6):
        x1, y1 = random.randint(0, TILE), random.randint(0, TILE)
        length = random.randint(6, 14)
        angle  = random.uniform(0, math.pi)
        x2 = int(x1 + math.cos(angle)*length)
        y2 = int(y1 + math.sin(angle)*length)
        col = random.choice([(100, 60, 200), (60, 200, 220), (180, 80, 255)])
        pygame.draw.line(crystal, col, (x1, y1), (x2, y2), 2)
    pygame.draw.rect(crystal, (120, 60, 200), (0, 0, TILE, TILE), 1)
    tiles['crystal'] = crystal

    # --- Lava tile ---
    lava = pygame.Surface((TILE, TILE))
    lava.fill((180, 40, 10))
    for i in range(0, TILE, 4):
        h = random.randint(2, 6)
        col = random.choice([LAVA_RED, ORANGE, (255, 200, 50)])
        pygame.draw.ellipse(lava, col, (i-2, TILE//2-h, 8, h*2))
    tiles['lava'] = lava

    # --- Top-surface grass/moss tile ---
    top = stone.copy()
    pygame.draw.rect(top, BIOLUM_GREEN, (0, 0, TILE, 6))
    tiles['top'] = top

    return tiles


def make_bg_layers(level_index=0):
    """Load or generate scrolling parallax background layers."""
    layers = []
    W, H = SCREEN_W * 3, SCREEN_H
    
    # Try to load custom background images for the level
    bg_dir = os.path.join(os.path.dirname(__file__), 'images', 'bg')
    layer_files = [
        f'level_{level_index}_bg_layer_0.png',
        f'level_{level_index}_bg_layer_1.png',
        f'level_{level_index}_bg_layer_2.png',
    ]
    
    # Attempt to load all layer images
    custom_layers_found = True
    for layer_file in layer_files:
        path = os.path.join(bg_dir, layer_file)
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            # Scale to fit the screen dimensions
            scaled = pygame.transform.scale(img, (W, H))
            layers.append(scaled)
        else:
            custom_layers_found = False
            break
    
    if custom_layers_found and len(layers) == 3:
        return layers

    # Fallback: generate procedural layers if custom ones not found
    for depth in range(3):
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        alpha = 80 + depth * 40

        if depth == 0:
            # Far: dark void with tiny distant stars / spores
            surf.fill((5, 3, 12))
            for _ in range(200):
                x, y = random.randint(0, W-1), random.randint(0, H-1)
                r = random.randint(1, 3)
                c = random.choice([(80, 40, 160), (40, 140, 180), (180, 100, 255)])
                pygame.draw.circle(surf, c, (x, y), r)

        elif depth == 1:
            # Mid: cave silhouette stalactites / stalagmites
            surf.fill((0,0,0,0))
            for i in range(0, W, 60):
                # Stalactite
                h = random.randint(30, 120)
                w = random.randint(10, 30)
                pts = [(i+w//2, 0), (i, h), (i+w, h)]
                pygame.draw.polygon(surf, (20, 12, 35), pts)
                # Stalagmite
                h2 = random.randint(20, 80)
                pts2 = [(i+w//2, H), (i, H-h2), (i+w, H-h2)]
                pygame.draw.polygon(surf, (20, 12, 35), pts2)

        else:
            # Front: crystal glow patches
            surf.fill((0,0,0,0))
            for _ in range(40):
                x, y = random.randint(0, W-1), random.randint(H//2, H-1)
                r = random.randint(15, 40)
                col = random.choice([(60, 30, 140, 50), (30, 120, 80, 40)])
                pygame.draw.circle(surf, col, (x, y), r)

        layers.append(surf)
    return layers


def make_boss_frames():
    """Load boss sprite sheets from Character_sheet.png."""
    boss_dir = os.path.join(os.path.dirname(__file__), 'images', 'boss')
    character_path = os.path.join(boss_dir, 'Character_sheet.png')
    
    frames = {}
    
    if os.path.exists(character_path):
        try:
            sheet = pygame.image.load(character_path).convert_alpha()
            sheet_w, sheet_h = sheet.get_size()
            
            # Character sheet layout: ~10 columns, 9 rows
            frame_w = sheet_w // 10
            frame_h = sheet_h // 9
            
            # Helper to extract and SCALE to consistent size (BIGGER - 150x150)
            def extract_frame(col, row):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame_img = sheet.subsurface(rect)
                # Directly scale to 150x150 for BIG BOSS
                scaled = pygame.transform.scale(frame_img, (150, 150))
                return scaled
            
            # Row 0: Idle frames (first 4 columns)
            idle_frames = [extract_frame(i, 0) for i in range(4)]
            frames['idle'] = idle_frames
            
            # Row 2: Attack frames with weapon (first 9 columns) 
            attack_frames = [extract_frame(i, 2) for i in range(9)]
            frames['attack'] = attack_frames
            
            # Row 8: Death frames (first 4 columns)
            dead_frames = [extract_frame(i, 8) for i in range(4)]
            frames['dead'] = dead_frames
            
            return frames
        except Exception as e:
            print(f"Error loading boss frames from {character_path}: {e}")
    
    # Fallback procedural boss - BIG 150x150
    frames = {}
    W, H = 150, 150

    def _body(color):
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        # Main body
        pygame.draw.ellipse(s, color, (30, 45, W-60, H-75))
        # Head
        pygame.draw.circle(s, color, (W//2, 35), 22)
        # Eyes
        pygame.draw.circle(s, (255, 100, 100), (W//2-15, 28), 6)
        pygame.draw.circle(s, (255, 100, 100), (W//2+15, 28), 6)
        # Legs
        pygame.draw.rect(s, color, (W//4-8, H-45, 16, 45))
        pygame.draw.rect(s, color, (3*W//4-8, H-45, 16, 45))
        return s

    frames['idle']   = [_body((100, 60, 80))]
    frames['attack'] = [_body((120, 80, 100)) for _ in range(4)]
    frames['dead']   = [_body((60, 40, 50))]
    return frames


def make_boss_projectile_frames():
    """Create large boss projectile frames."""
    boss_dir = os.path.join(os.path.dirname(__file__), 'images', 'boss')
    frames = []
    
    # Try to load projectile sprites
    projectile_files = ['arm_projectile.png', 'arm_projectile_glowing.png']
    for proj_file in projectile_files:
        proj_path = os.path.join(boss_dir, proj_file)
        if os.path.exists(proj_path):
            img = pygame.image.load(proj_path).convert_alpha()
            # Scale to BIG projectile size (was 24, now 48)
            scaled = pygame.transform.scale(img, (48, 48))
            frames.append(scaled)
    
    if frames:
        return frames
    
    # Fallback - big projectiles
    frames = []
    for i in range(3):
        s = pygame.Surface((48, 48), pygame.SRCALPHA)
        # Large glowing orbs
        pygame.draw.circle(s, (80, 40, 100), (24, 24), 16)
        pygame.draw.circle(s, (140, 80, 180), (24, 24), 10)
        pygame.draw.circle(s, (200, 150, 255), (24, 24), 5)
        frames.append(s)
    return frames


def make_boss_laser_frames():
    """Load laser frames from Laser_sheet.png."""
    boss_dir = os.path.join(os.path.dirname(__file__), 'images', 'boss')
    laser_path = os.path.join(boss_dir, 'Laser_sheet.png')
    
    frames = []
    if os.path.exists(laser_path):
        # Load laser animation strip (assuming 4 frames across)
        loaded = _load_strip_frames(laser_path, frame_count=4, target_height=32, canvas_size=(300, 40))
        if loaded:
            frames = loaded
            return frames
    
    # Fallback laser frames
    for i in range(3):
        s = pygame.Surface((200, 24), pygame.SRCALPHA)
        col_alpha = max(80, 200 - i*40)
        pygame.draw.line(s, (80, 200, 255, col_alpha), (0, 12), (200, 12), 8)
        pygame.draw.circle(s, (150, 220, 255), (0, 12), 6)
        frames.append(s)
    return frames


def make_boss_shield_frames():
    """Generate shield burst effect frames."""
    frames = []
    
    # Create animated shield effect with pulsing rings
    for i in range(6):
        s = pygame.Surface((120, 120), pygame.SRCALPHA)
        center = 60
        
        # Multiple rings for shield effect
        for ring in range(3):
            r = 15 + i * 8 + ring * 12
            alpha = int(200 * (1 - i/6)) if i < 6 else 0
            pygame.draw.circle(s, (80, 200, 220, alpha), (center, center), r, 3)
        
        # Core glow
        core_alpha = int(255 * (1 - i/6))
        pygame.draw.circle(s, (120, 220, 255, core_alpha), (center, center), 8)
        
        frames.append(s)
    
    return frames

