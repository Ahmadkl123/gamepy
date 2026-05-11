# ============================================================
# entities/boss.py - Boss enemy with advanced attack patterns
# ============================================================
import pygame
import math
import random
from settings import *
from utils import draw_bar


class BossProjectile(pygame.sprite.Sprite):
    """Projectile fired by the boss."""
    
    def __init__(self, x, y, vx, vy, frames):
        super().__init__()
        self.frames = frames
        self.frame_idx = 0
        self.image = self.frames[self.frame_idx]
        self.rect = self.image.get_rect(center=(x, y))
        self.vel_x = vx
        self.vel_y = vy
        self.lifetime = 300
        self.anim_timer = 0
    
    def update(self):
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y
        self.lifetime -= 1
        # Animate projectile
        self.anim_timer += 1
        if self.anim_timer >= 4:
            self.anim_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
            self.image = self.frames[self.frame_idx]
        if self.lifetime <= 0:
            self.kill()


class BossLaser(pygame.sprite.Sprite):
    """Laser beam attack from boss."""
    
    def __init__(self, x, y, length, angle, frames):
        super().__init__()
        self.x = x
        self.y = y
        self.length = length
        self.angle = angle
        self.frames = frames
        self.frame_idx = 0
        self.lifetime = 120
        self.image = None
        self.rect = None
        self._update_image()
    
    def _update_image(self):
        # Use frame cycling for laser
        self.frame_idx = int((120 - self.lifetime) / 10) % len(self.frames)
        base_img = self.frames[self.frame_idx]
        self.image = pygame.transform.scale(base_img, (self.length, 24))
        self.image = pygame.transform.rotate(self.image, -math.degrees(self.angle))
        self.rect = self.image.get_rect(center=(self.x, self.y))
    
    def update(self):
        self.lifetime -= 1
        self._update_image()
        if self.lifetime <= 0:
            self.kill()
    
    def get_collision_rect(self):
        """Return a rect for collision detection."""
        return pygame.Rect(self.x - 20, self.y - 20, 40, 40)


class Boss(pygame.sprite.Sprite):
    """
    Boss enemy with multiple attack patterns:
    - Projectile spray
    - Laser beam
    - Shield barrier
    """
    
    def __init__(self, x, y, frames, projectile_frames, laser_frames, shield_frames):
        super().__init__()
        self.frames = frames
        self.projectile_frames = projectile_frames
        self.laser_frames = laser_frames
        self.shield_frames = shield_frames
        
        # Geometry
        self.image = self.frames['idle'][0]
        self.rect = pygame.Rect(x, y, 150, 150)
        
        # Physics
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.target_x = x
        
        # Health
        self.hp = 30
        self.max_hp = 30
        self.alive = True
        self.death_timer = 0
        
        # Animation
        self.anim_state = 'idle'
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 6  # Faster animation
        
        # Attacks
        self.attack_timer = 0
        self.attack_type = 'projectile'  # 'projectile', 'laser', 'shield'
        self.attack_cooldown = 0
        
        # Movement
        self.move_timer = 0
        self.move_direction = 1
        self.shielded = False
        self.shield_timer = 0
        
        # Sprite groups for boss attacks
        self.projectiles = pygame.sprite.Group()
        self.lasers = pygame.sprite.Group()
    
    def update(self, platforms, player_rect):
        """Update boss behavior."""
        if not self.alive:
            self.death_timer += 1
            if self.death_timer > 120:
                self.kill()
            self.anim_state = 'dead'
            self._animate(loop=False)
            return
        
        # Movement pattern - patrol back and forth
        self.move_timer += 1
        if self.move_timer > 180:
            self.move_timer = 0
            self.move_direction = -self.move_direction
        
        self.target_x = self.rect.centerx + self.move_direction * 2
        self.rect.centerx += (self.target_x - self.rect.centerx) * 0.02
        
        # Gravity
        self.vel_y += GRAVITY
        self.vel_y = min(self.vel_y, MAX_FALL)
        self.rect.y += int(self.vel_y)
        
        # Collision with platforms
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vel_y > 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0
        
        # Attack pattern
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        else:
            self._perform_attack(player_rect)
        
        # Shield cooldown
        if self.shield_timer > 0:
            self.shield_timer -= 1
            self.shielded = self.shield_timer > 0
        
        # Update projectiles and lasers
        self.projectiles.update()
        self.lasers.update()
        
        # Animation
        if self.attack_timer > 0:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.anim_state = 'idle'
        
        if self.anim_state != 'attack':
            self.anim_state = 'idle'
        
        self._animate()
    
    def _perform_attack(self, player_rect):
        """Boss performs an attack."""
        attack_choice = random.choice(['projectile', 'projectile', 'laser', 'shield'])
        
        if attack_choice == 'projectile':
            self._attack_projectile(player_rect)
        elif attack_choice == 'laser':
            self._attack_laser(player_rect)
        elif attack_choice == 'shield':
            self._activate_shield()
        
        self.anim_state = 'attack'
        self.attack_timer = 20
        self.attack_cooldown = 80
    
    def _attack_projectile(self, player_rect):
        """Fire a spray of projectiles."""
        boss_cx = self.rect.centerx
        boss_cy = self.rect.centery
        
        # Calculate direction to player
        dx = player_rect.centerx - boss_cx
        dy = player_rect.centery - boss_cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        
        # Spray pattern
        for angle_offset in range(-2, 3):
            angle = math.atan2(dy, dx) + (angle_offset * 0.3)
            vx = math.cos(angle) * 6
            vy = math.sin(angle) * 6
            proj = BossProjectile(boss_cx, boss_cy, vx, vy, self.projectile_frames)
            self.projectiles.add(proj)
    
    def _attack_laser(self, player_rect):
        """Fire a laser beam."""
        boss_cx = self.rect.centerx
        boss_cy = self.rect.centery
        
        dx = player_rect.centerx - boss_cx
        dy = player_rect.centery - boss_cy
        angle = math.atan2(dy, dx)
        
        laser = BossLaser(boss_cx, boss_cy, 400, angle, self.laser_frames)
        self.lasers.add(laser)
    
    def _activate_shield(self):
        """Activate protective shield."""
        self.shielded = True
        self.shield_timer = 120
    
    def take_damage(self, amount, particles):
        """Boss takes damage from player attack."""
        if self.shielded:
            # Shield absorbs damage
            return True
        
        self.hp -= amount
        if particles:
            particles.emit(self.rect.centerx, self.rect.centery,
                          RED, count=8, speed=5, life=20, size=3)
        
        if self.hp <= 0:
            self.die()
        return False
    
    def die(self):
        """Boss death."""
        self.alive = False
        self.death_timer = 0
        self.anim_state = 'dead'
        self.anim_frame = 0
        self.anim_timer = 0
    
    def _animate(self, loop=True):
        """Handle animation."""
        self.anim_timer += 1
        frames = self.frames.get(self.anim_state, self.frames['idle'])
        
        if self.anim_timer >= self.anim_speed:
            self.anim_timer = 0
            if loop:
                self.anim_frame = (self.anim_frame + 1) % len(frames)
            else:
                self.anim_frame = min(self.anim_frame + 1, len(frames) - 1)
        
        self.anim_frame = self.anim_frame % len(frames)
        self.image = frames[self.anim_frame].copy()
        
        # Draw shield effect if shielded
        if self.shielded:
            shield_alpha = int(100 + 50 * math.sin(pygame.time.get_ticks() / 100))
            self.image.set_alpha(200)
    
    def draw_hp(self, surface, camera):
        """Draw boss health bar."""
        r = camera.apply(self.rect)
        draw_bar(surface, r.centerx - 40, r.top - 30, 80, 12,
                self.hp, self.max_hp, (255, 100, 100), (50, 50, 50))
    
    def draw_attacks(self, surface, camera):
        """Draw projectiles and lasers."""
        for proj in self.projectiles:
            surface.blit(proj.image, camera.apply(proj.rect))
        for laser in self.lasers:
            surface.blit(laser.image, laser.rect)
