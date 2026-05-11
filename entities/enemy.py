# ============================================================
# entities/enemy.py — All enemy types
# ============================================================
import pygame, math, random
from settings import *


class BaseEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y, hp, speed, dmg, score_val, frames):
        super().__init__()
        self.hp         = hp
        self.max_hp     = hp
        self.speed      = speed
        self.dmg        = dmg
        self.score_val  = score_val
        self.frames     = frames
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 8
        self.facing     = -1
        self.alive      = True

        self.image = self.frames[0]
        self.rect  = self.image.get_rect(topleft=(x, y))

    def _animate(self):
        self.anim_timer += 1
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % len(self.frames)
        img = self.frames[self.anim_frame]
        if self.facing == 1:
            img = pygame.transform.flip(img, True, False)
        self.image = img

    def take_damage(self, amount, particles):
        if not self.alive:
            return False

        self.hp -= amount
        particles.emit(self.rect.centerx, self.rect.centery,
                       RED, count=8, speed=3, life=18, size=3)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            particles.emit(self.rect.centerx, self.rect.centery,
                           ORANGE, count=16, speed=6, life=35, size=5)
            self.kill()
            return True
        return False

    def draw_hp(self, surface, cam):
        if self.alive and self.hp < self.max_hp:
            r = cam.apply(self.rect)
            pygame.draw.rect(surface, RED,   (r.x, r.y-8, r.w, 5))
            fill = int(r.w * self.hp / self.max_hp)
            pygame.draw.rect(surface, GREEN, (r.x, r.y-8, fill, 5))


class Crawler(BaseEnemy):
    """Ground skeleton that patrols, reacts to the player, attacks, and dies."""

    def __init__(self, x, y, frames):
        anim_sets = frames if isinstance(frames, dict) else {
            'idle'  : [frames[0]],
            'walk'  : frames,
            'attack': frames,
            'hit'   : frames[:2],
            'react' : frames[:2],
            'dead'  : frames[:2],
        }
        super().__init__(x, y, CRAWLER_HP, CRAWLER_SPEED,
                         CRAWLER_DMG, CRAWLER_SCORE, anim_sets['idle'])

        self.anim_sets    = anim_sets
        self.anim_state   = 'walk'
        self.direction    = random.choice([-1, 1])
        self.vel_y        = 0.0
        self.on_ground    = False
        self.patrol_timer = 0
        self.attack_timer = 0
        self.attack_cd    = random.randint(25, 65)
        self.hit_timer    = 0
        self.react_timer  = 0
        self.pause_timer  = random.randint(24, 60)
        self.alerted      = False
        self.aggro_range  = 180
        self.attack_range = 52
        self.anim_speeds  = {
            'idle'  : 10,
            'walk'  : 6,
            'attack': 4,
            'hit'   : 5,
            'react' : 6,
            'dead'  : 7,
        }
        self.facing = 1
        self.image = self.anim_sets['idle'][0]
        self.rect  = self.image.get_rect(topleft=(x, y))

    def _set_state(self, state, restart=False):
        if restart or state != self.anim_state:
            self.anim_state = state
            self.anim_frame = 0
            self.anim_timer = 0
        self.anim_speed = self.anim_speeds.get(self.anim_state, 8)

    def _animate_state(self, loop=True):
        frames = self.anim_sets.get(self.anim_state, self.anim_sets['walk'])
        if not frames:
            return

        self.anim_timer += 1
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            if loop:
                self.anim_frame = (self.anim_frame + 1) % len(frames)
            else:
                self.anim_frame = min(self.anim_frame + 1, len(frames) - 1)

        anchor = self.rect.midbottom
        img = frames[self.anim_frame]
        if self.facing == -1:
            img = pygame.transform.flip(img, True, False)
        self.image = img
        self.rect = self.image.get_rect(midbottom=anchor)

    def trigger_attack(self):
        if not self.alive or self.attack_timer > 0:
            return
        self.attack_timer = len(self.anim_sets.get('attack', [])) * self.anim_speeds['attack']
        self.attack_cd = 50
        self._set_state('attack', restart=True)

    def on_player_contact(self):
        self.trigger_attack()

    def take_damage(self, amount, particles):
        if not self.alive or self.hit_timer > 0:
            return False

        self.hp -= amount
        particles.emit(self.rect.centerx, self.rect.centery,
                       RED, count=8, speed=3, life=18, size=3)

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.attack_timer = 0
            self.hit_timer = 0
            self.react_timer = 0
            self._set_state('dead', restart=True)
            particles.emit(self.rect.centerx, self.rect.centery,
                           ORANGE, count=16, speed=6, life=35, size=5)
            return True

        self.hit_timer = len(self.anim_sets.get('hit', [])) * self.anim_speeds['hit']
        self._set_state('hit', restart=True)
        return False

    def update(self, platforms, player, particles):
        if self.attack_cd > 0:
            self.attack_cd -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1
        if self.react_timer > 0:
            self.react_timer -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        if self.pause_timer > 0:
            self.pause_timer -= 1

        if not self.alive:
            self._set_state('dead')
            self._animate_state(loop=False)
            dead_frames = self.anim_sets.get('dead', [])
            if dead_frames and self.anim_frame >= len(dead_frames) - 1 and self.anim_timer == 0:
                self.kill()
            return

        px = player.rect.centerx
        py = player.rect.centery
        dist_x = px - self.rect.centerx
        dist_y = abs(py - self.rect.centery)
        player_near = abs(dist_x) < self.aggro_range and dist_y < 80

        if player_near:
            self.direction = 1 if dist_x > 0 else -1
            self.facing = self.direction
            self.pause_timer = 0
            if not self.alerted and self.react_timer == 0:
                self.react_timer = len(self.anim_sets.get('react', [])) * self.anim_speeds['react']
                self._set_state('react', restart=True)
            self.alerted = True
        elif abs(dist_x) > self.aggro_range * 1.5:
            self.alerted = False

        move_speed = self.speed
        if self.hit_timer > 0:
            move_speed = 0
        elif self.attack_timer > 0:
            move_speed = self.speed * 0.35
        elif self.react_timer > 0:
            move_speed = 0
        elif not player_near and self.pause_timer > 0:
            move_speed = 0
        elif player_near:
            move_speed = self.speed * 1.15

        if (player_near and abs(dist_x) < self.attack_range and dist_y < 60
                and self.attack_cd == 0 and self.hit_timer == 0):
            self.trigger_attack()
            move_speed = 0

        self.vel_y += GRAVITY * 0.8
        self.vel_y  = min(self.vel_y, MAX_FALL)
        self.on_ground = False

        move_x = int(self.direction * move_speed)
        self.rect.x += move_x
        self.facing  = self.direction

        hit_wall = False
        if move_x != 0:
            for p in platforms:
                if self.rect.colliderect(p.rect):
                    if move_x > 0:
                        self.rect.right = p.rect.left
                    else:
                        self.rect.left = p.rect.right
                    hit_wall = True
                    break

        self.rect.y += int(self.vel_y)
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_y > 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0

        edge_missing = False
        if self.on_ground and move_speed > 0 and not player_near:
            foot_probe_x = self.rect.centerx + self.direction * (self.rect.w // 2 + 4)
            foot_probe_y = self.rect.bottom + 2
            edge_missing = not any(p.rect.collidepoint(foot_probe_x, foot_probe_y)
                                   for p in platforms)

        if hit_wall or edge_missing:
            self.direction *= -1
            self.pause_timer = random.randint(12, 28)

        self.patrol_timer += 1
        if self.patrol_timer > 180 and not player_near and self.attack_timer == 0:
            self.patrol_timer = 0
            self.pause_timer = random.randint(24, 54)
            if random.random() < 0.3:
                self.direction *= -1

        if self.hit_timer > 0:
            self._set_state('hit')
        elif self.attack_timer > 0:
            self._set_state('attack')
        elif self.react_timer > 0:
            self._set_state('react')
        elif abs(move_speed) > 0.1:
            self._set_state('walk')
        else:
            self._set_state('idle')

        self._animate_state(loop=self.anim_state not in ('attack', 'hit', 'react'))


class Projectile(pygame.sprite.Sprite):
    """Spore/projectile fired by the Flyer."""

    def __init__(self, x, y, dx, dy, frames):
        super().__init__()
        self.frames     = frames
        self.anim_frame = 0
        self.anim_timer = 0
        self.image      = self.frames[0]
        self.rect       = self.image.get_rect(center=(x, y))
        speed = 4.5
        mag   = max(0.01, math.hypot(dx, dy))
        self.vx = dx / mag * speed
        self.vy = dy / mag * speed
        self.life = 120

    def update(self):
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)
        self.life -= 1
        self.anim_timer += 1
        if self.anim_timer >= 3:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % len(self.frames)
        self.image = self.frames[self.anim_frame]
        if self.life <= 0:
            self.kill()


class Flyer(BaseEnemy):
    """
    Mushroom-bat enemy using the Attack3.png sprite sheet.
    - 6-frame animation (slightly enlarged display size)
    - Sine-wave hover when idle, chases player in range
    - Fires spore projectiles when close enough
    """

    def __init__(self, x, y, frames):
        super().__init__(x, y, FLYER_HP, FLYER_SPEED,
                         FLYER_DMG, FLYER_SCORE, frames)
        self.start_x      = float(x)
        self.start_y      = float(y)
        self.float_x      = float(x)
        self.float_y      = float(y)
        self.sine_t       = random.uniform(0, math.pi * 2)
        self.chase        = False
        self.CHASE_RANGE  = 300
        self.shoot_cd     = random.randint(60, 120)
        self.projectiles  = pygame.sprite.Group()
        self.proj_frames  = None

        # Keep the hitbox a bit smaller than the visible sprite.
        self.rect = pygame.Rect(x, y, 66, 66)

    def set_projectile_frames(self, frames):
        self.proj_frames = frames

    def update(self, platforms, player, particles):
        self.sine_t += 0.04

        px, py = player.rect.centerx, player.rect.centery
        dist = math.hypot(px - self.float_x, py - self.float_y)

        if dist < self.CHASE_RANGE:
            self.chase = True
        if dist > self.CHASE_RANGE * 1.6:
            self.chase = False

        if self.chase:
            dx = px - self.float_x
            dy = py - self.float_y
            mag = max(1, math.hypot(dx, dy))
            self.float_x += dx / mag * self.speed
            self.float_y += dy / mag * self.speed + math.sin(self.sine_t) * 1.0
            self.facing = 1 if dx > 0 else -1

            if self.shoot_cd > 0:
                self.shoot_cd -= 1
            elif self.proj_frames and dist < 260:
                self.shoot_cd = random.randint(90, 150)
                proj = Projectile(self.rect.centerx, self.rect.centery,
                                  dx, dy, self.proj_frames)
                self.projectiles.add(proj)
                particles.emit(self.rect.centerx, self.rect.centery,
                               (180, 90, 40), count=5, speed=3, life=14, size=3)
        else:
            self.float_x += math.cos(self.sine_t * 0.5) * 1.5
            self.float_y = self.start_y + math.sin(self.sine_t) * 28
            if self.shoot_cd > 0:
                self.shoot_cd -= 1

        self.rect.x = int(self.float_x)
        self.rect.y = int(self.float_y)
        self.projectiles.update()
        self._animate()


class Golem(BaseEnemy):
    def __init__(self, x, y, frames):
        super().__init__(x, y, GOLEM_HP, GOLEM_SPEED,
                         GOLEM_DMG, GOLEM_SCORE, frames)
        self.vel_y       = 0.0
        self.on_ground   = False
        self.AGGRO_RANGE = 350
        self.stomp_cd    = 0
        self.stomping    = False

    def update(self, platforms, player, particles):
        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, MAX_FALL)

        px = player.rect.centerx
        dist = abs(px - self.rect.centerx)

        if dist < self.AGGRO_RANGE:
            dx = 1 if px > self.rect.centerx else -1
            self.facing = dx
            self.rect.x += int(dx * self.speed)

        self.rect.y += int(self.vel_y)

        self.on_ground = False
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_y >= 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0
                    self.on_ground = True

        if self.stomp_cd > 0:
            self.stomp_cd -= 1
        if self.on_ground and player.rect.centery < self.rect.centery - 60:
            if self.stomp_cd == 0 and random.random() < 0.01:
                self.vel_y = JUMP_POWER * 0.7
                self.stomp_cd = 120
                particles.emit(self.rect.centerx, self.rect.bottom,
                               ORANGE, count=12, speed=4, life=20, size=5)

        self._animate()
        self.anim_speed = 10
