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
