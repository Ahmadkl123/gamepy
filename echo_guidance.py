# ============================================================
# echo_guidance.py — "Echo Guidance System"
# ------------------------------------------------------------
# An atmospheric navigation aid for Whispering Caverns.
#
# Instead of a hard arrow / marker UI, the cavern itself "echoes":
# soft rings of light pulse out from the player and a stream of
# glowing motes drifts toward the current objective, ricocheting
# off the terrain the way sound bounces inside a cave. The further
# the player strays — or the longer they wander without progress —
# the louder, faster and brighter the echo becomes.
#
# The whole system is modular and self-contained:
#
#     eg = EchoGuidanceSystem(sfx, on_echo=callback)  # build once
#     eg.reset()                                      # per level load
#     eg.set_objective((x, y), dynamic=False)         # feed a target/frame
#     eg.update(player_rect, platforms)               # advance simulation
#     eg.draw(world_surface, camera)                  # render (world space)
#     eg.toggle()                                     # enable / disable
#
# Performance: every spawned element is stored in a plain list and
# hard-capped (see EchoConfig). All compositing happens on ONE reused
# screen-sized surface — no per-element allocations per frame. On
# low-end / mobile targets set EchoConfig.quality = 0 to halve mote
# counts and skip the wall-bounce broad-phase.
# ============================================================
import math
import random

import pygame

from settings import SCREEN_W, SCREEN_H, dbg


# ─────────────────────────────────────────────
#  TUNING
#  Every magic number lives here so the system
#  can be re-balanced or down-scaled for low-end
#  hardware from a single place.
# ─────────────────────────────────────────────
class EchoConfig:
    enabled_by_default = True

    # Render quality. 1 = full fidelity, 0 = reduced (mobile / low-end):
    # halves mote counts and disables the wall-bounce broad-phase.
    quality = 1

    # --- cadence (frames between echo pulses) ---
    base_cooldown = 165      # calm: a slow, occasional pulse
    min_cooldown  = 60       # lost: rapid, urgent pulses

    # --- distance thresholds (world pixels) ---
    near_dist = 280          # within this -> echoes are barely there
    far_dist  = 1500         # beyond this -> full intensity

    # --- "lost" detection ---
    stagnation_frames = 540  # ~9s of no progress -> treated as fully lost

    # --- hard caps (keep per-frame cost bounded) ---
    max_rings = 7
    max_motes = 96
    trail_len = 7

    # --- ring look ---
    ring_grow  = 2.7
    ring_life  = 78
    ring_start = 16.0

    # --- mote look ---
    mote_speed   = 4.0
    mote_life    = 165
    mote_homing  = 0.045     # how hard motes curve toward the objective
    mote_bounces = 2

    # --- palette (mysterious cavern tones) ---
    calm_color = (120, 70, 220)   # soft violet — "all is well"
    lost_color = (90, 230, 240)   # cold cyan  — "you have strayed"


# ─────────────────────────────────────────────
#  SMALL MATH HELPERS
# ─────────────────────────────────────────────
def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return (int(_lerp(c1[0], c2[0], t)),
            int(_lerp(c1[1], c2[1], t)),
            int(_lerp(c1[2], c2[2], t)))


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def _clamp01(v):
    return _clamp(v, 0.0, 1.0)


# ─────────────────────────────────────────────
#  ECHO RING
# ─────────────────────────────────────────────
class _EchoRing:
    """A soft ring of light expanding outward from the player.

    It is drawn as a faint *full* circle (an omni-directional sense of
    "presence") with a brighter arc baked onto the side that faces the
    objective — so it reads as guidance without ever becoming a literal
    arrow. Rings spawn with a small `delay` so a burst forms a cascade.
    """
    __slots__ = ('x', 'y', 'radius', 'life', 'max_life',
                 'intensity', 'angle', 'delay')

    def __init__(self, x, y, intensity, angle, delay=0):
        self.x = x
        self.y = y
        self.radius   = EchoConfig.ring_start
        self.max_life = EchoConfig.ring_life
        self.life     = self.max_life
        self.intensity = intensity      # 0..1 master strength
        self.angle     = angle          # radians, screen-space dir of objective
        self.delay     = delay          # frames to wait before expanding

    def update(self):
        """Advance one frame. Returns False once the ring should be culled."""
        if self.delay > 0:
            self.delay -= 1
            return True
        self.radius += EchoConfig.ring_grow
        self.life   -= 1
        return self.life > 0

    def draw(self, layer, camera, color):
        if self.delay > 0:
            return
        # ease-out fade: bright at birth, gentle lingering tail
        t = self.life / self.max_life
        fade = t * t
        sx, sy = camera.apply_pos(self.x, self.y)
        r = int(self.radius)
        if r < 2:
            return

        # faint full ring — the "presence"
        base_a = int(70 * fade * self.intensity)
        if base_a > 0:
            pygame.draw.circle(layer, (*color, base_a), (sx, sy), r, 2)

        # brighter guiding arc on the side facing the objective
        arc_a = int(180 * fade * (0.35 + 0.65 * self.intensity))
        if arc_a > 0:
            rect = pygame.Rect(sx - r, sy - r, r * 2, r * 2)
            half = math.pi * 0.42                # ~75 deg half-width
            # screen-space angle (y-down) -> pygame arc space (y-up)
            start = -self.angle - half
            end   = -self.angle + half
            try:
                pygame.draw.arc(layer, (*color, arc_a), rect, start, end, 3)
            except (TypeError, ValueError):
                pass


# ─────────────────────────────────────────────
#  ECHO MOTE
# ─────────────────────────────────────────────
class _EchoMote:
    """A drifting spark that homes toward the objective and ricochets off
    cave geometry — the echo "finding its way" through the cavern.

    Movement is intentionally loose: motes are launched in a fan, gently
    curve toward the target, and bounce off platforms (losing a little
    energy each time). The result is an organic, sonar-like flow rather
    than a rigid line.
    """
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life',
                 'bounces', 'trail', 'intensity')

    def __init__(self, x, y, angle, speed, intensity):
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.max_life = EchoConfig.mote_life
        self.life     = self.max_life
        self.bounces  = EchoConfig.mote_bounces
        self.trail    = []
        self.intensity = intensity

    def update(self, objective, platforms, bounce_enabled):
        """Advance one frame. Returns False once the mote should be culled."""
        # --- gentle homing: curve the velocity toward the objective ---
        ox, oy = objective
        desired = math.atan2(oy - self.y, ox - self.x)
        cur     = math.atan2(self.vy, self.vx)
        # shortest signed angular difference, then ease toward it
        diff = (desired - cur + math.pi) % (2 * math.pi) - math.pi
        cur += diff * EchoConfig.mote_homing
        speed = math.hypot(self.vx, self.vy)
        self.vx = math.cos(cur) * speed
        self.vy = math.sin(cur) * speed

        # --- record trail, then propose the next position ---
        self.trail.append((self.x, self.y))
        if len(self.trail) > EchoConfig.trail_len:
            self.trail.pop(0)

        nx = self.x + self.vx
        ny = self.y + self.vy

        # --- environmental interaction: bounce off terrain ---
        if bounce_enabled and self.bounces > 0:
            point = (int(nx), int(ny))
            for p in platforms:
                if p.rect.collidepoint(point):
                    self._reflect(p.rect)
                    self.bounces -= 1
                    nx = self.x + self.vx
                    ny = self.y + self.vy
                    break

        self.x = nx
        self.y = ny
        self.life -= 1
        return self.life > 0

    def _reflect(self, rect):
        """Flip the velocity component that drove the mote into `rect`,
        bouncing off whichever face is closest."""
        from_left   = abs(self.x - rect.left)
        from_right  = abs(self.x - rect.right)
        from_top    = abs(self.y - rect.top)
        from_bottom = abs(self.y - rect.bottom)
        if min(from_left, from_right) < min(from_top, from_bottom):
            self.vx = -self.vx
        else:
            self.vy = -self.vy
        # lose a little energy on each bounce so motes settle, not pinball
        self.vx *= 0.86
        self.vy *= 0.86

    def draw(self, layer, camera, color):
        t = self.life / self.max_life
        # fade in quickly, fade out slowly
        fade = min(1.0, t * 3.0) * (0.4 + 0.6 * t)

        # --- trail: a string of fading line segments ---
        if len(self.trail) > 1:
            pts = [camera.apply_pos(tx, ty) for tx, ty in self.trail]
            pts = [(int(px), int(py)) for px, py in pts]
            n = len(pts)
            for i in range(n - 1):
                seg = (i + 1) / n
                a = int(90 * fade * seg * self.intensity)
                if a <= 0:
                    continue
                pygame.draw.line(layer, (*color, a),
                                 pts[i], pts[i + 1], max(1, int(2 * seg)))

        # --- head: a bright core wrapped in a soft additive glow ---
        sx, sy = camera.apply_pos(self.x, self.y)
        sx, sy = int(sx), int(sy)
        head_a = int(200 * fade)
        if head_a <= 0:
            return
        glow_r = int(7 + 4 * self.intensity)
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, int(head_a * 0.5)),
                           (glow_r, glow_r), glow_r)
        layer.blit(glow, (sx - glow_r, sy - glow_r),
                   special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(layer, (235, 240, 255, head_a), (sx, sy), 3)


# ─────────────────────────────────────────────
#  ECHO GUIDANCE SYSTEM (public manager)
# ─────────────────────────────────────────────
class EchoGuidanceSystem:
    """Modular, atmospheric navigation aid.

    The game feeds it an objective every frame; it decides — based on
    distance and how long the player has gone without making progress —
    how strong the guidance should be, and emits rings + motes + audio
    on a cooldown that tightens the more lost the player is.

    It also keeps a lightweight *waypoint memory*: every distinct place
    it has guided toward is remembered, and arriving at a new waypoint
    fires a soft resonance cue.
    """

    def __init__(self, sfx=None, on_echo=None):
        self.sfx     = sfx        # SoundManager (optional — system is silent without)
        self.on_echo = on_echo    # callback(intensity) fired on each pulse
        self.enabled = EchoConfig.enabled_by_default

        # One reused compositing layer — no per-frame surface allocations.
        self._layer = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        self.reset()

    # ── lifecycle ───────────────────────────────────────────
    def reset(self):
        """Wipe all live effects and waypoint memory. Call on every level load."""
        self._rings = []
        self._motes = []
        self.objective = None
        self._cooldown = EchoConfig.base_cooldown

        # intensity: raw target this frame + a smoothed value for rendering
        self.intensity = 0.0
        self._intensity_smooth = 0.0

        # "am I lost?" tracking
        self._closest_dist = float('inf')
        self._stagnant = 0

        # waypoint memory — every distinct objective we have guided toward
        self.waypoint_memory = []

        self._beacon_pulse = 0.0

    def toggle(self):
        """Enable / disable the whole system cleanly. Live effects still
        fade out gracefully when disabled — nothing snaps off."""
        self.enabled = not self.enabled
        dbg(f"EchoGuidanceSystem -> {'ENABLED' if self.enabled else 'DISABLED'}")
        return self.enabled

    # ── objective / waypoint memory ─────────────────────────
    def set_objective(self, pos, dynamic=False):
        """Feed the system the current objective center, in world coords.

        `dynamic=True` marks a moving target (e.g. a boss): its constant
        motion is tracked but never mistaken for "reaching a waypoint".
        """
        if pos is None:
            return
        pos = (int(pos[0]), int(pos[1]))

        if dynamic:
            if self.objective is None:
                self._remember(pos)
            self.objective = pos
            return

        if self.objective is None:
            self.objective = pos
            self._remember(pos)
            return

        # objective jumped to a genuinely new place -> a waypoint was reached
        if math.hypot(pos[0] - self.objective[0],
                      pos[1] - self.objective[1]) > 96:
            self._remember(pos)
            self._on_waypoint_reached()
        self.objective = pos

    def _remember(self, pos):
        """Store a waypoint, de-duplicated within a 96px radius."""
        for wx, wy in self.waypoint_memory:
            if math.hypot(pos[0] - wx, pos[1] - wy) < 96:
                return
        self.waypoint_memory.append(pos)

    def _on_waypoint_reached(self):
        # fresh leg of the journey -> reset the "lost" tracking
        self._closest_dist = float('inf')
        self._stagnant = 0
        if self.sfx:
            self.sfx.play('echo_resonance')
        dbg(f"EchoGuidanceSystem -> waypoint reached, "
            f"{len(self.waypoint_memory)} remembered")

    # ── per-frame update ────────────────────────────────────
    def update(self, player_rect, platforms):
        # Live effects advance even while disabled, so they fade out
        # gracefully instead of vanishing the instant the system is off.
        self._advance_effects(platforms)
        self._beacon_pulse += 0.07

        if not self.enabled or self.objective is None:
            return

        px, py = player_rect.center
        ox, oy = self.objective
        dist = math.hypot(ox - px, oy - py)

        # --- intensity cue #1: raw distance to the objective ---
        span = max(1.0, EchoConfig.far_dist - EchoConfig.near_dist)
        dist_factor = _clamp01((dist - EchoConfig.near_dist) / span)

        # --- intensity cue #2: stagnation ("am I making progress?") ---
        if dist < self._closest_dist - 6:
            self._closest_dist = dist
            self._stagnant = 0
        else:
            self._stagnant += 1
        stagnation_factor = _clamp01(
            self._stagnant / EchoConfig.stagnation_frames)

        # a lost player gets the stronger of the two cues
        self.intensity = _clamp01(max(dist_factor, stagnation_factor * 0.9))
        # smooth it so visuals + audio breathe instead of snapping
        self._intensity_smooth += (self.intensity -
                                   self._intensity_smooth) * 0.04

        # --- cadence: pulses arrive faster the more lost the player is ---
        self._cooldown -= 1
        if self._cooldown <= 0:
            self._emit_echo(px, py, ox, oy)
            self._cooldown = int(_lerp(EchoConfig.base_cooldown,
                                       EchoConfig.min_cooldown,
                                       self._intensity_smooth))

    def _advance_effects(self, platforms):
        """Tick every live ring + mote, dropping the dead ones."""
        bounce = (EchoConfig.quality >= 1)
        self._rings = [r for r in self._rings if r.update()]
        live = []
        for m in self._motes:
            # if there's no objective yet, let motes simply drift
            target = self.objective if self.objective else (m.x, m.y)
            if m.update(target, platforms, bounce):
                live.append(m)
        self._motes = live

    def _emit_echo(self, px, py, ox, oy):
        """Spawn one full echo pulse: rings + a mote stream + audio."""
        inten = self._intensity_smooth
        angle = math.atan2(oy - py, ox - px)

        # --- rings: a calm single pulse, a frantic cascade when lost ---
        n_rings = 1 + int(round(inten * 2.5))
        for i in range(n_rings):
            if len(self._rings) >= EchoConfig.max_rings:
                break
            self._rings.append(
                _EchoRing(px, py, 0.5 + 0.5 * inten, angle, delay=i * 8))

        # --- motes: a directed stream toward the objective ---
        n_motes = 5 + int(inten * 16)
        if EchoConfig.quality < 1:
            n_motes = max(2, n_motes // 2)
        spread = math.radians(_lerp(14, 32, inten))   # wander more when lost
        for _ in range(n_motes):
            if len(self._motes) >= EchoConfig.max_motes:
                break
            a   = angle + random.uniform(-spread, spread)
            spd = EchoConfig.mote_speed * random.uniform(0.8, 1.25)
            self._motes.append(_EchoMote(px, py, a, spd, 0.5 + 0.5 * inten))

        # --- audio: a sonar-like pulse ---
        if self.sfx:
            self.sfx.play('echo_pulse')

        # --- hook: let the game react (e.g. trigger a whisper) ---
        if self.on_echo:
            self.on_echo(inten)

    # ── rendering ───────────────────────────────────────────
    def draw(self, surface, camera):
        """Composite every echo element onto one reused layer, blit once."""
        if not self._rings and not self._motes:
            if not (self.enabled and self.objective):
                return  # nothing live and nothing to point at

        color = _lerp_color(EchoConfig.calm_color, EchoConfig.lost_color,
                            self._intensity_smooth)

        layer = self._layer
        layer.fill((0, 0, 0, 0))

        # objective beacon — a faint heartbeat at the destination itself
        if self.enabled and self.objective:
            self._draw_beacon(layer, camera, color)

        for ring in self._rings:
            ring.draw(layer, camera, color)
        for mote in self._motes:
            mote.draw(layer, camera, color)

        # screen-edge resonance when the objective is off-screen
        if self.enabled and self.objective:
            self._draw_edge_resonance(layer, camera, color)

        surface.blit(layer, (0, 0))

    def _draw_beacon(self, layer, camera, color):
        """A soft pulsing glow sitting on the objective itself — drawn only
        when the objective is roughly on-screen. Subtle, never a marker."""
        sx, sy = camera.apply_pos(*self.objective)
        if not (-80 <= sx <= SCREEN_W + 80 and -80 <= sy <= SCREEN_H + 80):
            return
        pulse = 0.5 + 0.5 * math.sin(self._beacon_pulse)
        r = int(_lerp(10, 26, pulse) * (0.6 + 0.4 * self._intensity_smooth))
        a = int(_lerp(30, 90, pulse) * (0.4 + 0.6 * self._intensity_smooth))
        if r < 2 or a <= 0:
            return
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -2):
            ring_a = int(a * (1 - rr / r))
            if ring_a > 0:
                pygame.draw.circle(glow, (*color, ring_a), (r, r), rr)
        layer.blit(glow, (int(sx - r), int(sy - r)),
                   special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_edge_resonance(self, layer, camera, color):
        """When the objective is off-screen, breathe a soft bloom along the
        screen edge in its direction — minimal, modern, never an arrow."""
        sx, sy = camera.apply_pos(*self.objective)
        if -40 <= sx <= SCREEN_W + 40 and -40 <= sy <= SCREEN_H + 40:
            return  # on-screen: the beacon already covers it

        cx, cy = SCREEN_W * 0.5, SCREEN_H * 0.5
        ang = math.atan2(sy - cy, sx - cx)
        # a point pinned to the screen border in the objective's direction
        margin = 46
        ex = _clamp(cx + math.cos(ang) * SCREEN_W, margin, SCREEN_W - margin)
        ey = _clamp(cy + math.sin(ang) * SCREEN_H, margin, SCREEN_H - margin)

        pulse    = 0.55 + 0.45 * math.sin(self._beacon_pulse * 1.3)
        strength = 0.25 + 0.75 * self._intensity_smooth
        r = int(_lerp(60, 150, strength) * pulse)
        a = int(_lerp(18, 70, strength) * pulse)
        if r < 4 or a <= 0:
            return
        bloom = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for rr in range(r, 0, -6):
            ba = int(a * (1 - rr / r))
            if ba > 0:
                pygame.draw.circle(bloom, (*color, ba), (r, r), rr)
        layer.blit(bloom, (int(ex - r), int(ey - r)),
                   special_flags=pygame.BLEND_RGBA_ADD)
