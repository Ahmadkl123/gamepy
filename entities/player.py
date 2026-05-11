# ============================================================
# entities/player.py - Player character with full mechanics
# ============================================================
import pygame
from settings import *
from utils import draw_bar


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

    def _try_dash(self, particles):
        if self.dash_cd == 0 and not self.dashing:
            self.dashing = True
            self.dash_timer = DASH_DUR
            self.dash_cd = DASH_CD
            self.dash_dir = self.facing
            for _ in range(6):
                particles.emit(self.rect.centerx, self.rect.centery,
                               CYAN, count=3, speed=4, life=18, size=4, gravity=0)

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
            return
        self.hp -= amount
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

    def die(self, immediate=False):
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

    def collect_coin(self, particles):
        self.score += COIN_VALUE
        self.coins += 1
        particles.emit(0, 0, GOLD, count=0)

    def apply_speed_bonus(self, particles):
        self.speed_boost = 300
        particles.emit(self.rect.centerx, self.rect.centery,
                       YELLOW, count=12, speed=5, life=25, size=4)

    def apply_shield_bonus(self, particles):
        self.shielded = True
        particles.emit(self.rect.centerx, self.rect.centery,
                       CYAN, count=12, speed=5, life=25, size=4)

    def add_score(self, pts):
        self.score += pts

    def draw_hud(self, surface, coin_icon=None):
        draw_bar(surface, 20, 20, 180, 18, self.hp, self.max_hp, RED)
        font = pygame.font.SysFont("Arial", 15, bold=True)
        surface.blit(font.render(f"HP: {self.hp}/{self.max_hp}", True, WHITE), (28, 22))

        font_big = pygame.font.SysFont("Arial", 22, bold=True)
        surface.blit(font_big.render(f"Score: {self.score}", True, GOLD),
                     (SCREEN_W // 2 - 70, 14))

        if coin_icon:
            icon_rect = coin_icon.get_rect(topleft=(SCREEN_W - 150, 10))
            surface.blit(coin_icon, icon_rect)
            surface.blit(font_big.render(f"{self.coins}", True, YELLOW),
                         (icon_rect.right + 8, 14))
        else:
            surface.blit(font_big.render(f"{self.coins}", True, YELLOW),
                         (SCREEN_W - 110, 14))

        y = 48
        if self.speed_boost > 0:
            surface.blit(font.render("SPEED", True, YELLOW), (20, y))
            y += 18
        if self.shielded:
            surface.blit(font.render("SHIELD", True, CYAN), (20, y))

        if self.dash_cd > 0:
            pct = 1 - self.dash_cd / DASH_CD
            draw_bar(surface, 20, SCREEN_H - 30, 80, 8, pct, 1, CYAN, DARK_GREY)
            surface.blit(font.render("DASH", True, CYAN), (20, SCREEN_H - 44))
