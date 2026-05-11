# ============================================================
# utils.py — Helpers: Camera, Particles, Drawing utilities
# ============================================================
import pygame, math, random
from settings import *


# ─────────────────────────────────────────────
#  CAMERA
# ─────────────────────────────────────────────
class Camera:
    """Smooth-follow camera that offsets all world objects."""

    def __init__(self, world_w, world_h):
        self.x = 0.0
        self.y = 0.0
        self.world_w = world_w
        self.world_h = world_h

    def update(self, target_rect):
        # Target: center of screen on player
        tx = target_rect.centerx - SCREEN_W // 2
        ty = target_rect.centery - SCREEN_H // 2
        # Clamp inside world bounds
        tx = max(0, min(tx, self.world_w - SCREEN_W))
        ty = max(0, min(ty, self.world_h - SCREEN_H))
        # Smooth lerp
        self.x += (tx - self.x) * CAM_SMOOTH * 8
        self.y += (ty - self.y) * CAM_SMOOTH * 8

    def apply(self, rect):
        """Return a rect shifted to screen space."""
        return pygame.Rect(rect.x - int(self.x), rect.y - int(self.y),
                           rect.w, rect.h)

    def apply_pos(self, x, y):
        return x - int(self.x), y - int(self.y)


# ─────────────────────────────────────────────
#  PARTICLE SYSTEM
# ─────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','life','max_life','color','size','gravity')

    def __init__(self, x, y, color, vx=0, vy=0, life=30, size=3, gravity=0.1):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    def update(self):
        self.vy += self.gravity
        self.x  += self.vx
        self.y  += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface, cam):
        alpha = self.life / self.max_life
        r, g, b = self.color
        col = (int(r*alpha), int(g*alpha), int(b*alpha))
        sx, sy = cam.apply_pos(self.x, self.y)
        s = max(1, int(self.size * alpha))
        pygame.draw.circle(surface, col, (int(sx), int(sy)), s)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit(self, x, y, color, count=8, speed=3,
             life=30, size=3, gravity=0.1, spread=360):
        for _ in range(count):
            angle = math.radians(random.uniform(0, spread))
            spd   = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd + random.uniform(-0.5, 0.5)
            vy = math.sin(angle) * spd + random.uniform(-0.5, 0.5)
            if len(self.particles) < MAX_PARTICLES:
                self.particles.append(
                    Particle(x, y, color, vx, vy, life, size, gravity))

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface, cam):
        for p in self.particles:
            p.draw(surface, cam)


# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────
def draw_text(surface, text, x, y, color=WHITE, size=24, font=None, center=False):
    if font is None:
        font = pygame.font.SysFont("Arial", size, bold=True)
    img = font.render(str(text), True, color)
    if center:
        x -= img.get_width() // 2
        y -= img.get_height() // 2
    surface.blit(img, (x, y))


def draw_glow(surface, color, pos, radius, alpha=80):
    """Draw a soft glowing circle."""
    glow = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
    for r in range(radius, 0, -4):
        a = int(alpha * (1 - r/radius))
        pygame.draw.circle(glow, (*color, a), (radius, radius), r)
    surface.blit(glow, (pos[0]-radius, pos[1]-radius), special_flags=pygame.BLEND_RGBA_ADD)


def draw_bar(surface, x, y, w, h, value, maxval, color, bg=DARK_GREY):
    """Draw a health/energy bar."""
    pygame.draw.rect(surface, bg,    (x, y, w, h), border_radius=4)
    fill = int(w * max(0, value) / maxval)
    if fill > 0:
        pygame.draw.rect(surface, color, (x, y, fill, h), border_radius=4)
    pygame.draw.rect(surface, WHITE, (x, y, w, h), 1, border_radius=4)


def lerp_color(c1, c2, t):
    return tuple(int(a + (b-a)*t) for a, b in zip(c1, c2))
