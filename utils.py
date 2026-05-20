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
        self.shake_intensity = 0.0
        self.shake_decay     = 0.85
        self._shake_ox = 0
        self._shake_oy = 0

    def shake(self, intensity):
        """Trigger a screen shake. Larger = more violent."""
        self.shake_intensity = max(self.shake_intensity, float(intensity))

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

        # Shake offset (applied additively at render time via apply/apply_pos)
        if self.shake_intensity > 0.2:
            self._shake_ox = random.randint(-int(self.shake_intensity),
                                             int(self.shake_intensity))
            self._shake_oy = random.randint(-int(self.shake_intensity),
                                             int(self.shake_intensity))
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_intensity = 0.0
            self._shake_ox = 0
            self._shake_oy = 0

    def apply(self, rect):
        """Return a rect shifted to screen space."""
        return pygame.Rect(rect.x - int(self.x) + self._shake_ox,
                           rect.y - int(self.y) + self._shake_oy,
                           rect.w, rect.h)

    def apply_pos(self, x, y):
        return (x - int(self.x) + self._shake_ox,
                y - int(self.y) + self._shake_oy)


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


# ─────────────────────────────────────────────
#  UI WIDGETS (chips, keycaps, ring gauges, hearts)
# ─────────────────────────────────────────────
def measure_chip(text, font, padding=10, icon=None, icon_gap=8):
    """Return (w, h) the chip will take WITHOUT drawing it."""
    text_img = font.render(text, True, (0, 0, 0))
    h = max(text_img.get_height(), icon.get_height() if icon else 0) + padding
    icon_w = (icon.get_width() + icon_gap) if icon else 0
    w = text_img.get_width() + icon_w + padding * 2
    return w, h


def draw_chip(surface, x, y, text, font, fg=WHITE,
              bg=(20, 14, 32), border=(120, 80, 200),
              padding=10, radius=10, icon=None, icon_gap=8):
    """Draw a rounded pill 'chip' with text (+ optional icon on the left).
    Returns the chip rect for layout chaining."""
    text_img = font.render(text, True, fg)
    h = max(text_img.get_height(), icon.get_height() if icon else 0) + padding
    icon_w = (icon.get_width() + icon_gap) if icon else 0
    w = text_img.get_width() + icon_w + padding * 2

    rect = pygame.Rect(x, y, w, h)
    chip = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(chip, (*bg, 220), (0, 0, w, h), border_radius=radius)
    pygame.draw.rect(chip, (*border, 255), (0, 0, w, h), 2, border_radius=radius)
    surface.blit(chip, (x, y))

    cy = y + (h - text_img.get_height()) // 2
    cx = x + padding
    if icon:
        iy = y + (h - icon.get_height()) // 2
        surface.blit(icon, (cx, iy))
        cx += icon.get_width() + icon_gap
    surface.blit(text_img, (cx, cy))
    return rect


def draw_keycap(surface, x, y, text, font,
                fg=(240, 240, 250), bg=(35, 28, 55),
                border=(140, 110, 200), min_w=32, h=32, radius=8):
    """Render a key cap (e.g. ENTER, F, ←). Returns the cap rect."""
    text_img = font.render(text, True, fg)
    w = max(min_w, text_img.get_width() + 14)
    cap = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(cap, (*bg, 240), (0, 0, w, h), border_radius=radius)
    pygame.draw.rect(cap, (*border, 255), (0, 0, w, h), 2, border_radius=radius)
    # bottom shading line
    pygame.draw.line(cap, (10, 6, 18), (4, h - 3), (w - 4, h - 3), 1)
    surface.blit(cap, (x, y))
    surface.blit(text_img,
                 (x + (w - text_img.get_width()) // 2,
                  y + (h - text_img.get_height()) // 2))
    return pygame.Rect(x, y, w, h)


def draw_ring(surface, cx, cy, radius, pct,
              color=WHITE, bg=(40, 30, 60), width=4):
    """Draw a circular progress ring. pct in [0..1]."""
    pct = max(0.0, min(1.0, pct))
    # background ring
    pygame.draw.circle(surface, bg, (cx, cy), radius, width)
    if pct <= 0:
        return
    # foreground arc
    rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
    start = -math.pi / 2
    end   = start + 2 * math.pi * pct
    try:
        pygame.draw.arc(surface, color, rect, start, end, width)
    except TypeError:
        # fallback: full circle when arc isn't supported
        pygame.draw.circle(surface, color, (cx, cy), radius, width)


_HEART_CACHE = {}

def heart_icon(size=22, filled=True, color=(235, 60, 80), dim=(50, 24, 30)):
    """Return a (cached) heart-shaped surface."""
    key = (size, filled, color, dim)
    if key in _HEART_CACHE:
        return _HEART_CACHE[key]

    s = pygame.Surface((size, size), pygame.SRCALPHA)
    r = size // 4
    base = color if filled else dim
    border = (255, 220, 220) if filled else (110, 60, 70)

    # Two lobes + triangle body
    cx1, cy = r + 1, r + 2
    cx2     = size - r - 1
    pygame.draw.circle(s, base, (cx1, cy), r)
    pygame.draw.circle(s, base, (cx2, cy), r)
    pts = [(1, cy), (size - 1, cy), (size // 2, size - 2)]
    pygame.draw.polygon(s, base, pts)

    # Outline
    pygame.draw.circle(s, border, (cx1, cy), r, 1)
    pygame.draw.circle(s, border, (cx2, cy), r, 1)
    pygame.draw.polygon(s, border, pts, 1)

    # Highlight
    if filled:
        hl = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(hl, (255, 220, 230, 110), (cx1 - 1, cy - 1), r // 2)
        s.blit(hl, (0, 0))

    _HEART_CACHE[key] = s
    return s
