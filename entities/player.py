# ============================================================
# entities/player.py - Player character with full mechanics
# ============================================================
import math
import pygame
from settings import *
from utils import draw_bar, draw_chip, draw_ring, heart_icon, measure_chip


class Player(pygame.sprite.Sprite):
    """
    Full-featured player:
    - Left/Right movement, Jump, Double-jump, Dash
    - Attack (melee sword slash)
    - Health / invincibility frames
    - Speed bonus & Shield bonus
    """

    def __init__(self, x, y, frames):
        super().__init__()
        self.frames = frames

        # Geometry
        self.image = self.frames['idle'][0]
        self.rect = pygame.Rect(x, y, 40, 48)

        # Physics
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.jumps_left = 2

        # Dash
        self.dashing = False
        self.dash_timer = 0
        self.dash_cd = 0
        self.dash_dir = 1

        # Attack
        self.attacking = False
        self.attack_timer = 0
        self.attack_cd = 0
        self.facing = 1

        # Health
        self.hp = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.inv_timer = 0
        self.alive = True
        self.death_finished = False
        self.hurt_timer = 0

        # Bonuses
        self.speed_boost = 0
        self.shielded = False

        # Score / stats
        self.score = 0
        self.coins = 0

        # Animation
        self.anim_state = 'idle'
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 6

        # Hitbox for attack
        self.attack_rect = pygame.Rect(0, 0, 0, 0)

        # Optional SoundManager (set by Game after construction)
        self.sfx = None

    def _play(self, name):
        if self.sfx is not None:
            self.sfx.play(name)

    def handle_input(self, keys, mouse_buttons, particles):
        if not self.alive:
            return

        spd = PLAYER_SPAX * (1.8 if self.speed_boost > 0 else 1)

        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            if not self.dashing:
                self.vel_x = -spd
            self.facing = -1
            moving = True
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            if not self.dashing:
                self.vel_x = spd
            self.facing = 1
            moving = True
        else:
            if not self.dashing:
                self.vel_x *= 0.75

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            self._try_dash(particles)

        if keys[pygame.K_f] or mouse_buttons[0]:
            self._try_attack(particles)

        if self.attacking:
            new_state = 'attack'
        elif self.dashing:
            new_state = 'dash'
        elif not self.on_ground:
            new_state = 'jump'
        elif moving:
            new_state = 'run'
        else:
            new_state = 'idle'

        if new_state != self.anim_state:
            self.anim_state = new_state
            self.anim_frame = 0
            self.anim_timer = 0

    def jump(self):
        if self.jumps_left > 0:
            self.vel_y = JUMP_POWER
            self.on_ground = False
            self.jumps_left -= 1
            self._play('jump')
            dbg(f"Player.jump -> jumped, {self.jumps_left} jump(s) left")

    def _try_dash(self, particles):
        if self.dash_cd == 0 and not self.dashing:
            self.dashing = True
            self.dash_timer = DASH_DUR
            self.dash_cd = DASH_CD
            self.dash_dir = self.facing
            for _ in range(6):
                particles.emit(self.rect.centerx, self.rect.centery,
                               CYAN, count=3, speed=4, life=18, size=4, gravity=0)
            self._play('dash')
            dbg(f"Player._try_dash -> dashing dir={self.dash_dir}")

    def _try_attack(self, particles):
        if self.attack_cd == 0:
            self.attacking = True
            self.attack_timer = ATTACK_DUR
            self.attack_cd = ATTACK_CD
            w, h = ATTACK_RANGE, 36
            if self.facing == 1:
                ax = self.rect.right
            else:
                ax = self.rect.left - w
            self.attack_rect = pygame.Rect(ax, self.rect.centery - h // 2, w, h)
            for _ in range(5):
                particles.emit(self.attack_rect.centerx, self.attack_rect.centery,
                               (255, 240, 140), count=4, speed=5, life=12, size=3)
            self._play('attack')
            dbg(f"Player._try_attack -> attacking facing={self.facing}")

    def update(self, platforms, particles):
        if self.inv_timer > 0:
            self.inv_timer -= 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.dash_cd > 0:
            self.dash_cd -= 1
        if self.attack_cd > 0:
            self.attack_cd -= 1
        if self.speed_boost > 0:
            self.speed_boost -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        else:
            self.attacking = False
            self.attack_rect = pygame.Rect(0, 0, 0, 0)

        if not self.alive:
            self.vel_x *= 0.85
            self.vel_y += GRAVITY
            self.vel_y = min(self.vel_y, MAX_FALL)
            self.rect.x += int(self.vel_x)
            self._collide_x(platforms)
            self.rect.y += int(self.vel_y)
            self._collide_y(platforms)
            self.anim_state = 'dead'
            self._animate(loop=False)
            dead_frames = self.frames.get('dead', [])
            if dead_frames and self.anim_frame >= len(dead_frames) - 1 and self.anim_timer == 0:
                self.death_finished = True
            return

        if self.dashing:
            self.dash_timer -= 1
            self.vel_x = self.dash_dir * DASH_SPEED
            self.vel_y = 0
            if self.dash_timer <= 0:
                self.dashing = False

        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, MAX_FALL)

        self.rect.x += int(self.vel_x)
        self._collide_x(platforms)

        self.rect.y += int(self.vel_y)
        self._collide_y(platforms)

        self._animate()

    def _collide_x(self, platforms):
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_x > 0:
                    self.rect.right = p.rect.left
                elif self.vel_x < 0:
                    self.rect.left = p.rect.right
                self.vel_x = 0

    def _collide_y(self, platforms):
        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_y > 0:
                    self.rect.bottom = p.rect.top
                    self.on_ground = True
                    self.jumps_left = 2
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0

    def _animate(self, loop=True):
        self.anim_timer += 1
        frames = self.frames.get(self.anim_state, self.frames['idle'])
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            if loop:
                self.anim_frame = (self.anim_frame + 1) % len(frames)
            else:
                self.anim_frame = min(self.anim_frame + 1, len(frames) - 1)

        self.anim_frame = self.anim_frame % len(frames)
        img = frames[self.anim_frame]
        if self.facing == -1:
            img = pygame.transform.flip(img, True, False)

        self.image = img

    def take_damage(self, amount, particles):
        if self.inv_timer > 0 or not self.alive:
            return
        if self.shielded:
            self.shielded = False
            particles.emit(self.rect.centerx, self.rect.centery,
                           CYAN, count=12, speed=5, life=25, size=4)
            self._play('shield_block')
            dbg("Player.take_damage -> shield absorbed the hit")
            return
        self.hp -= amount
        dbg(f"Player.take_damage -> took {amount}, hp = {self.hp}/{self.max_hp}")
        self.inv_timer = PLAYER_INVINCIBLE
        self.hurt_timer = 14
        self.dashing = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_rect = pygame.Rect(0, 0, 0, 0)
        particles.emit(self.rect.centerx, self.rect.centery,
                       RED, count=10, speed=4, life=20, size=4)
        if self.hp <= 0:
            self.hp = 0
            self.die()
        else:
            self._play('hit')

    def die(self, immediate=False):
        dbg(f"Player.die -> player dead (immediate={immediate})")
        self.alive = False
        self.dashing = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_rect = pygame.Rect(0, 0, 0, 0)
        self.hurt_timer = 0
        self.anim_state = 'dead'
        self.anim_frame = 0
        self.anim_timer = 0
        self.death_finished = immediate
        if immediate:
            self.vel_x = 0
            self.vel_y = 0
        self._play('player_die')

    def collect_coin(self, particles):
        self.score += COIN_VALUE
        self.coins += 1
        particles.emit(0, 0, GOLD, count=0)

    def apply_speed_bonus(self, particles):
        self.speed_boost = 300
        particles.emit(self.rect.centerx, self.rect.centery,
                       YELLOW, count=12, speed=5, life=25, size=4)
        self._play('powerup')
        dbg("Player.apply_speed_bonus -> speed boost active (300 frames)")

    def apply_shield_bonus(self, particles):
        self.shielded = True
        particles.emit(self.rect.centerx, self.rect.centery,
                       CYAN, count=12, speed=5, life=25, size=4)
        self._play('powerup')
        dbg("Player.apply_shield_bonus -> shield active")

    def add_score(self, pts):
        self.score += pts

    def draw_hud(self, surface, coin_icon=None):
        font_small = pygame.font.SysFont("Arial", 14, bold=True)
        font_med   = pygame.font.SysFont("Arial", 20, bold=True)
        font_big   = pygame.font.SysFont("Arial", 26, bold=True)

        # ── HP HEARTS (top-left) ─────────────────────────
        heart_size = 26
        gap = 4
        for i in range(self.max_hp):
            hx = 20 + i * (heart_size + gap)
            surface.blit(heart_icon(heart_size, filled=(i < self.hp)), (hx, 16))

        # ── SCORE CHIP (top-center) ───────────────────────
        score_text = f"SCORE   {self.score}"
        sw, _ = measure_chip(score_text, font_big)
        draw_chip(surface, SCREEN_W // 2 - sw // 2, 12, score_text, font_big,
                  fg=GOLD, bg=(20, 14, 32), border=(180, 140, 60))

        # ── COIN CHIP (top-right) ─────────────────────────
        coin_text = f"{self.coins}"
        cw, _ = measure_chip(coin_text, font_med, icon=coin_icon)
        draw_chip(surface, SCREEN_W - cw - 20, 14, coin_text, font_med,
                  fg=YELLOW, bg=(20, 14, 32),
                  border=(200, 160, 50), icon=coin_icon)

        # ── ACTIVE BONUS BADGES (under hearts) ────────────
        bonus_x = 20
        bonus_y = 16 + heart_size + 22  # below hearts and the lives strip
        if self.speed_boost > 0:
            pct = self.speed_boost / 300.0
            self._draw_bonus_badge(surface, bonus_x, bonus_y,
                                   label="SPD", color=YELLOW,
                                   icon_shape='bolt', pct=pct)
            bonus_x += 70
        if self.shielded:
            self._draw_bonus_badge(surface, bonus_x, bonus_y,
                                   label="SHD", color=CYAN,
                                   icon_shape='shield', pct=1.0)

        # ── DASH COOLDOWN RING (bottom-left) ──────────────
        ring_cx, ring_cy = 50, SCREEN_H - 50
        if self.dash_cd > 0:
            pct = 1 - self.dash_cd / DASH_CD
            draw_ring(surface, ring_cx, ring_cy, 22, pct,
                      color=CYAN, bg=(30, 50, 70), width=5)
            label_col = (140, 200, 220)
        else:
            # Ready: solid bright ring
            draw_ring(surface, ring_cx, ring_cy, 22, 1.0,
                      color=(120, 220, 220), bg=(30, 50, 70), width=5)
            # Soft pulse halo when ready
            t = pygame.time.get_ticks() / 200.0
            halo_r = 26 + int(abs(math.sin(t)) * 3)
            halo = pygame.Surface((halo_r * 2, halo_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(halo, (120, 220, 220, 35), (halo_r, halo_r), halo_r)
            surface.blit(halo, (ring_cx - halo_r, ring_cy - halo_r),
                         special_flags=pygame.BLEND_RGBA_ADD)
            label_col = (180, 230, 240)
        label = font_small.render("DASH", True, label_col)
        surface.blit(label, (ring_cx - label.get_width() // 2, ring_cy + 28))

    def _draw_bonus_badge(self, surface, x, y, label, color, icon_shape, pct):
        """Small badge with icon + countdown ring + caption."""
        size = 38
        # Backdrop
        bd = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(bd, (20, 14, 32, 220), (0, 0, size, size), border_radius=8)
        pygame.draw.rect(bd, (*color, 255), (0, 0, size, size), 2, border_radius=8)
        surface.blit(bd, (x, y))

        cx, cy = x + size // 2, y + size // 2
        # Icon
        if icon_shape == 'bolt':
            pts = [(cx - 4, cy - 9), (cx + 5, cy - 2),
                   (cx + 1, cy - 2), (cx + 4, cy + 9),
                   (cx - 5, cy + 1), (cx - 1, cy + 1)]
            pygame.draw.polygon(surface, color, pts)
        elif icon_shape == 'shield':
            pygame.draw.polygon(surface, color, [
                (cx, cy - 10), (cx + 9, cy - 4), (cx + 7, cy + 7),
                (cx, cy + 10), (cx - 7, cy + 7), (cx - 9, cy - 4)
            ])
            pygame.draw.polygon(surface, (20, 14, 32), [
                (cx, cy - 6), (cx + 5, cy - 2), (cx + 4, cy + 4),
                (cx, cy + 6), (cx - 4, cy + 4), (cx - 5, cy - 2)
            ], 1)

        # Countdown ring around the badge
        draw_ring(surface, cx, cy, size // 2 + 4, pct,
                  color=color, bg=(40, 30, 60), width=3)

        # Caption below
        cap_font = pygame.font.SysFont("Arial", 11, bold=True)
        cap = cap_font.render(label, True, color)
        surface.blit(cap, (x + (size - cap.get_width()) // 2, y + size + 2))
