# ============================================================
# entities/powerup.py — Coins and Power-up bonuses
# ============================================================
import pygame, math
from settings import *


class Coin(pygame.sprite.Sprite):
    """Spinning collectible coin."""

    def __init__(self, x, y, frames):
        super().__init__()
        self.frames     = frames
        self.anim_frame = 0
        self.anim_timer = 0
        self.image      = self.frames[0]
        self.rect       = self.image.get_rect(center=(x, y))
        self.base_y     = float(y)
        self.bob_t      = 0.0

    def update(self):
        self.anim_timer += 1
        if self.anim_timer >= 3:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % len(self.frames)
        self.image = self.frames[self.anim_frame]

        # Bob up/down
        self.bob_t  += 0.06
        self.rect.y  = int(self.base_y + math.sin(self.bob_t) * 5)


class PowerUp(pygame.sprite.Sprite):
    """Speed boost or Shield pickup."""

    def __init__(self, x, y, kind, surf):
        super().__init__()
        self.kind  = kind   # 'speed' | 'shield'
        self.image = surf
        self.rect  = self.image.get_rect(center=(x, y))
        self.base_y= float(y)
        self.bob_t = 0.0
        self.pulse = 0.0

    def update(self):
        self.bob_t  += 0.05
        self.pulse  += 0.08
        self.rect.y  = int(self.base_y + math.sin(self.bob_t) * 6)

    def draw_glow(self, surface, cam):
        color = YELLOW if self.kind == 'speed' else CYAN
        sx, sy = cam.apply_pos(self.rect.centerx, self.rect.centery)
        r = int(18 + math.sin(self.pulse) * 5)
        glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        for i in range(r, 0, -3):
            a = int(80 * i / r)
            pygame.draw.circle(glow, (*color, a), (r, r), i)
        surface.blit(glow, (sx-r, sy-r), special_flags=pygame.BLEND_RGBA_ADD)


class Checkpoint(pygame.sprite.Sprite):
    """A torch that lights up when the player passes - sets respawn point."""

    INACTIVE_COLOR = (90, 90, 110)
    ACTIVE_CORE    = (255, 200, 80)
    ACTIVE_GLOW    = (255, 140, 40)

    def __init__(self, x, y):
        super().__init__()
        self.active = False
        self.pulse  = 0.0
        # Anchor: x,y is the FOOT of the torch (so it sits on a platform top)
        self.rect = pygame.Rect(x - 14, y - 56, 28, 56)
        self.image = pygame.Surface((28, 56), pygame.SRCALPHA)
        self._rebuild_image()

    def _rebuild_image(self):
        self.image.fill((0, 0, 0, 0))
        # Pole
        pygame.draw.rect(self.image, (60, 35, 20), (12, 18, 4, 38))
        pygame.draw.rect(self.image, (40, 22, 12), (12, 50, 4, 6))
        # Bowl
        pygame.draw.ellipse(self.image, (70, 50, 30), (6, 14, 16, 10))
        # Flame
        if self.active:
            flick = int(math.sin(self.pulse * 6) * 2)
            pygame.draw.polygon(self.image, self.ACTIVE_GLOW,
                                [(14, 0 + flick), (4, 14), (24, 14)])
            pygame.draw.polygon(self.image, self.ACTIVE_CORE,
                                [(14, 4 + flick), (8, 14), (20, 14)])
        else:
            # Wisp of dim smoke
            pygame.draw.circle(self.image, self.INACTIVE_COLOR, (14, 10), 4)

    def activate(self, particles):
        if self.active:
            return False
        self.active = True
        self._rebuild_image()
        particles.emit(self.rect.centerx, self.rect.top + 8,
                       (255, 180, 60), count=18, speed=4,
                       life=28, size=4, gravity=-0.05)
        return True

    def update(self):
        if self.active:
            self.pulse += 0.15
            # Refresh flame every few frames for animated flicker
            if int(self.pulse * 10) % 3 == 0:
                self._rebuild_image()

    def draw_glow(self, surface, cam):
        if not self.active:
            return
        sx, sy = cam.apply_pos(self.rect.centerx, self.rect.top + 8)
        r = int(22 + math.sin(self.pulse) * 4)
        glow = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        for i in range(r, 0, -3):
            a = int(90 * i / r)
            pygame.draw.circle(glow, (255, 140, 40, a), (r, r), i)
        surface.blit(glow, (sx-r, sy-r), special_flags=pygame.BLEND_RGBA_ADD)

    @property
    def respawn_pos(self):
        """Return (x, y) where the player should be placed on respawn."""
        # Player rect is 40x48 with topleft origin; align feet to torch base.
        return (self.rect.centerx - 20, self.rect.bottom - 48)


class Chest(pygame.sprite.Sprite):
    """A treasure chest — opening it grants a score bonus and an extra life.

    Placed once near the end of the final stage as a closing reward. It
    gently bobs and gives off a golden glow (brighter while still shut, to
    beckon the player) and swaps to an 'open' sprite once collected.
    """

    def __init__(self, x, y, frames):
        super().__init__()
        self.frames = frames          # {'closed': surf, 'open': surf}
        self.opened = False
        self.image  = frames['closed']
        # x, y is the FOOT center so the chest sits on a platform top.
        self.rect   = self.image.get_rect(midbottom=(x, y))
        self.base_y = float(self.rect.y)
        self.bob_t  = 0.0
        self.pulse  = 0.0

    def update(self):
        self.pulse += 0.08
        if not self.opened:
            # Bob only while shut — once opened it settles in place.
            self.bob_t += 0.05
            self.rect.y = int(self.base_y + math.sin(self.bob_t) * 3)

    def open(self, particles):
        """Open the chest. Returns True only on the first successful open."""
        if self.opened:
            return False
        self.opened = True
        self.image  = self.frames['open']
        # Burst of golden coins/sparkle.
        particles.emit(self.rect.centerx, self.rect.centery - 4,
                       GOLD, count=30, speed=5, life=34, size=4, gravity=0.05)
        particles.emit(self.rect.centerx, self.rect.centery - 4,
                       (255, 235, 150), count=14, speed=3, life=26, size=3,
                       gravity=-0.04)
        return True

    def draw_glow(self, surface, cam):
        sx, sy = cam.apply_pos(self.rect.centerx, self.rect.centery)
        # Stronger pull while shut; a calmer afterglow once opened.
        peak = 70 if self.opened else 110
        r = int((20 if self.opened else 24) + math.sin(self.pulse) * 4)
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -3):
            a = int(peak * i / r)
            pygame.draw.circle(glow, (255, 200, 60, a), (r, r), i)
        surface.blit(glow, (sx - r, sy - r), special_flags=pygame.BLEND_RGBA_ADD)
