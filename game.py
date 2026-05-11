# ============================================================
# game.py — Core game engine: states, update, render
# ============================================================
import pygame, math, random, sys
from settings import *
from utils     import Camera, ParticleSystem, draw_text, draw_glow, lerp_color
from score     import load_highscore, save_highscore
from levels    import ALL_LEVELS, build_level
from entities.player  import Player
from entities.enemy   import Crawler, Flyer, Golem
from entities.boss    import Boss
from assets.generate_assets import (
    make_player_frames, make_crawler_frames, make_flyer_frames,
    make_golem_frames, make_coin_frames, make_powerup_surfaces,
    make_tile_surfaces, make_bg_layers, make_projectile_frames,
    make_exit_surface, make_boss_frames, make_boss_projectile_frames,
    make_boss_laser_frames, make_boss_shield_frames
)


# ─────────────────────────────────────────────
#  WHISPER MESSAGE POOL
# ─────────────────────────────────────────────
WHISPER_MSGS = [
    "The darkness breathes...",
    "Turn back while you can.",
    "They are watching you.",
    "Trust no echo.",
    "Hidden paths await the brave.",
    "The crystals remember.",
    "Something stirs in the deep.",
    "The whispers grow louder...",
    "Follow the glow.",
    "Danger lurks above.",
    "Coins call to the greedy.",
    "You are not alone down here.",
]


class WhisperDisplay:
    """Fades in/out mysterious text on screen."""

    def __init__(self):
        self.text     = ""
        self.alpha    = 0.0
        self.timer    = 0
        self.cooldown = 0

    def trigger(self):
        if self.cooldown <= 0:
            self.text     = random.choice(WHISPER_MSGS)
            self.alpha    = 0.0
            self.timer    = 220
            self.cooldown = random.randint(300, 600)

    def update(self):
        if self.cooldown > 0: self.cooldown -= 1
        if self.timer > 0:
            self.timer -= 1
            if self.timer > 180:
                self.alpha = min(255, self.alpha + 8)
            elif self.timer < 60:
                self.alpha = max(0, self.alpha - 6)
        # Auto-trigger occasionally
        if self.cooldown == 0 and random.random() < 0.002:
            self.trigger()

    def draw(self, surface):
        if self.alpha > 0 and self.text:
            font = pygame.font.SysFont("Georgia", 20, italic=True)
            img  = font.render(self.text, True, (180, 120, 255))
            img.set_alpha(int(self.alpha))
            x = SCREEN_W//2 - img.get_width()//2
            y = SCREEN_H - 80
            surface.blit(img, (x, y))


# ─────────────────────────────────────────────
#  GAME CLASS
# ─────────────────────────────────────────────
class Game:
    """
    States: MENU | PLAYING | PAUSED | GAME_OVER | VICTORY
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        self.state       = 'MENU'
        self.highscore   = load_highscore()
        self.level_index = 0
        self.total_score = 0
        self.new_highscore = False

        self._load_assets()
        self.whisper = WhisperDisplay()
        self._build_current_level()

    # ── ASSETS ────────────────────────────────────────────
    def _load_assets(self):
        self.enemy_frames = {
            'player' : make_player_frames(),
            'crawler': make_crawler_frames(),
            'flyer'  : make_flyer_frames(),
            'golem'  : make_golem_frames(),
            'boss'   : make_boss_frames(),
        }
        self.projectile_frames = make_projectile_frames()
        self.boss_projectile_frames = make_boss_projectile_frames()
        self.boss_laser_frames = make_boss_laser_frames()
        self.boss_shield_frames = make_boss_shield_frames()
        self.coin_frames    = make_coin_frames()
        self.powerup_surfs  = make_powerup_surfaces()
        self.tile_surfs     = make_tile_surfaces()
        self.bg_layers      = make_bg_layers(self.level_index)
        self.exit_surf      = make_exit_surface()

        # Fonts
        self.font_title  = pygame.font.SysFont("Georgia",   64, bold=True)
        self.font_big    = pygame.font.SysFont("Arial",     36, bold=True)
        self.font_mid    = pygame.font.SysFont("Arial",     24, bold=True)
        self.font_small  = pygame.font.SysFont("Arial",     16)

        # Parallax offsets
        self.bg_offsets = [0.0, 0.0, 0.0]
        self.bg_speeds  = [0.1, 0.25, 0.4]

    # ── LEVEL BUILD ───────────────────────────────────────
    def _build_current_level(self):
        ld = ALL_LEVELS[self.level_index]
        (self.player,
         self.platforms,
         self.hazards,
         self.enemies,
         self.coins,
         self.powerups) = build_level(
            ld, self.tile_surfs, self.coin_frames, self.powerup_surfs,
            self.enemy_frames, Player, None)

        self.camera   = Camera(ld['world_w'], ld['world_h'])
        self.particles= ParticleSystem()
        self.exit_rect= ld['exit_rect']
        self.level_name = ld['name']
        self.bg_tint  = ld['bg_tint']
        self.level_flash_timer = 120   # show level name on entry

        # Boss spawning
        self.boss = None
        if ld.get('has_boss', False):
            boss_x = ld['world_w'] // 2
            boss_y = 600
            self.boss = Boss(boss_x, boss_y, 
                            self.enemy_frames['boss'],
                            self.boss_projectile_frames,
                            self.boss_laser_frames,
                            self.boss_shield_frames)

        # Inject projectile sprite frames into every Flyer instance
        from entities.enemy import Flyer as FlyerCls
        for enemy in self.enemies:
            if isinstance(enemy, FlyerCls):
                enemy.set_projectile_frames(self.projectile_frames)

    # ── MAIN LOOP ─────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()
            pygame.display.flip()

    # ── EVENTS ────────────────────────────────────────────
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == 'PLAYING':
                        self.state = 'PAUSED'
                    elif self.state == 'PAUSED':
                        self.state = 'PLAYING'

                if self.state == 'MENU':
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self._start_game()
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

                if self.state == 'PLAYING':
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.player.jump()

                if self.state == 'GAME_OVER':
                    if event.key == pygame.K_RETURN:
                        self._start_game()
                    if event.key == pygame.K_m:
                        self.state = 'MENU'
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

                if self.state == 'VICTORY':
                    if event.key == pygame.K_RETURN:
                        self._next_level()
                    if event.key == pygame.K_m:
                        self.state = 'MENU'

                if self.state == 'PAUSED':
                    if event.key == pygame.K_m:
                        self.state = 'MENU'
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

    # ── UPDATE ────────────────────────────────────────────
    def _update(self):
        if self.state != 'PLAYING':
            return

        keys   = pygame.key.get_pressed()
        mouse  = pygame.mouse.get_pressed()
        plat_list = list(self.platforms)

        # Player
        self.player.handle_input(keys, mouse, self.particles)
        self.player.update(plat_list, self.particles)

        # Camera
        self.camera.update(self.player.rect)

        # Parallax
        for i in range(3):
            self.bg_offsets[i] = self.camera.x * self.bg_speeds[i]

        # Let the death animation finish before switching states.
        if not self.player.alive:
            self.particles.update()
            self.whisper.update()
            if self.player.death_finished:
                self.total_score += self.player.score
                self.new_highscore = save_highscore(self.total_score)
                self.highscore     = load_highscore()
                self.state = 'GAME_OVER'
            if self.level_flash_timer > 0:
                self.level_flash_timer -= 1
            return

        # Coins
        self.coins.update()
        for coin in list(self.coins):
            if self.player.rect.colliderect(coin.rect):
                self.player.score += COIN_VALUE
                self.player.coins += 1
                self.particles.emit(coin.rect.centerx, coin.rect.centery,
                                    GOLD, count=8, speed=4, life=22, size=3,
                                    gravity=0.05)
                coin.kill()

        # Power-ups
        self.powerups.update()
        for pu in list(self.powerups):
            if self.player.rect.colliderect(pu.rect):
                if pu.kind == 'speed':
                    self.player.apply_speed_bonus(self.particles)
                else:
                    self.player.apply_shield_bonus(self.particles)
                pu.kill()

        # Enemies
        from entities.enemy import Flyer as FlyerCls
        for enemy in list(self.enemies):
            enemy.update(plat_list, self.player, self.particles)

            # Enemy body hits player
            touching_enemy = self.player.rect.colliderect(enemy.rect)
            if touching_enemy and hasattr(enemy, 'on_player_contact'):
                enemy.on_player_contact()
            if touching_enemy and enemy.alive and self.player.inv_timer == 0:
                self.player.take_damage(enemy.dmg, self.particles)
                self.whisper.trigger()

            # Flyer projectiles hit player
            if isinstance(enemy, FlyerCls):
                for proj in list(enemy.projectiles):
                    if self.player.rect.colliderect(proj.rect):
                        self.player.take_damage(1, self.particles)
                        self.particles.emit(proj.rect.centerx, proj.rect.centery,
                                            (200, 100, 50), count=8, speed=4,
                                            life=18, size=3)
                        proj.kill()

            # Player attack hits enemy
            if (enemy.alive and self.player.attacking
                    and self.player.attack_rect.colliderect(enemy.rect)):
                died = enemy.take_damage(1, self.particles)
                if died:
                    self.player.add_score(enemy.score_val)

        # Hazards
        for haz in self.hazards:
            if self.player.rect.colliderect(haz.rect):
                self.player.take_damage(PLAYER_HP, self.particles)  # instant kill

        # Boss
        if self.boss:
            self.boss.update(plat_list, self.player.rect)
            
            # Boss projectiles hit player
            for proj in list(self.boss.projectiles):
                if self.player.rect.colliderect(proj.rect):
                    if self.player.inv_timer == 0:
                        self.player.take_damage(1, self.particles)
                    proj.kill()
            
            # Boss lasers hit player
            for laser in list(self.boss.lasers):
                if self.player.rect.colliderect(laser.get_collision_rect()):
                    if self.player.inv_timer == 0:
                        self.player.take_damage(1, self.particles)
            
            # Player attack hits boss
            if (self.boss.alive and self.player.attacking
                    and self.player.attack_rect.colliderect(self.boss.rect)):
                self.boss.take_damage(1, self.particles)
                if not self.boss.alive:
                    self.player.add_score(500)

        # Fall out of world
        if self.player.rect.top > ALL_LEVELS[self.level_index]['world_h'] + 100:
            self.player.hp = 0
            self.player.die(immediate=True)

        # Particles
        self.particles.update()
        self.whisper.update()

        # Level exit
        if self.player.rect.colliderect(self.exit_rect):
            # Only exit if no boss or boss is defeated
            if not self.boss or not self.boss.alive:
                self._complete_level()

        # Level flash
        if self.level_flash_timer > 0:
            self.level_flash_timer -= 1

    # ── LEVEL PROGRESSION ─────────────────────────────────
    def _start_game(self):
        self.level_index  = 0
        self.total_score  = 0
        self.state        = 'PLAYING'
        self._build_current_level()

    def _complete_level(self):
        bonus = LEVEL_BONUS * (self.level_index + 1)
        self.player.add_score(bonus)
        self.total_score += self.player.score

        if self.level_index >= LEVEL_COUNT - 1:
            # All levels complete
            self.new_highscore = save_highscore(self.total_score)
            self.highscore     = load_highscore()
            self.state = 'VICTORY'
        else:
            self.state = 'VICTORY'

    def _next_level(self):
        if self.level_index < LEVEL_COUNT - 1:
            self.level_index += 1
            self._build_current_level()
            self.state = 'PLAYING'
        else:
            self.state = 'MENU'

    # ── DRAW ──────────────────────────────────────────────
    def _draw(self):
        if   self.state == 'MENU':      self._draw_menu()
        elif self.state == 'PLAYING':   self._draw_playing()
        elif self.state == 'PAUSED':    self._draw_playing(); self._draw_pause_overlay()
        elif self.state == 'GAME_OVER': self._draw_game_over()
        elif self.state == 'VICTORY':   self._draw_victory()

    # ── PLAYING ───────────────────────────────────────────
    def _draw_playing(self):
        # Background
        self.screen.fill(self.bg_tint)
        self._draw_bg_layers()

        # Hazards
        for haz in self.hazards:
            self.screen.blit(haz.image, self.camera.apply(haz.rect))

        # Platforms
        for plat in self.platforms:
            self.screen.blit(plat.image, self.camera.apply(plat.rect))

        # Exit door
        self._draw_exit()

        # Power-ups (with glow)
        for pu in self.powerups:
            pu.draw_glow(self.screen, self.camera)
            self.screen.blit(pu.image, self.camera.apply(pu.rect))

        # Coins
        for coin in self.coins:
            self.screen.blit(coin.image, self.camera.apply(coin.rect))

        # Enemies + HP bars + Flyer projectiles
        from entities.enemy import Flyer as FlyerCls
        for enemy in self.enemies:
            # Draw projectiles behind enemy
            if isinstance(enemy, FlyerCls):
                for proj in enemy.projectiles:
                    self.screen.blit(proj.image, self.camera.apply(proj.rect))
            self.screen.blit(enemy.image, self.camera.apply(enemy.rect))
            enemy.draw_hp(self.screen, self.camera)

        # Boss (if present)
        if self.boss:
            # Draw boss projectiles and lasers
            self.boss.draw_attacks(self.screen, self.camera)
            # Draw boss sprite
            self.screen.blit(self.boss.image, self.camera.apply(self.boss.rect))
            # Draw boss HP bar
            self.boss.draw_hp(self.screen, self.camera)

        # Particles
        self.particles.draw(self.screen, self.camera)

        # Player (with invincibility blinking)
        player_img = self.player.image.copy()
        if self.player.inv_timer > 0:
            # Smooth blink: 3 on/off cycles during invincibility
            blink_phase = (self.player.inv_timer / PLAYER_INVINCIBLE) * 6
            if int(blink_phase) % 2 == 1:
                player_img.set_alpha(80)
        self.screen.blit(player_img, self.camera.apply(self.player.rect))

        # Attack hitbox debug (optional — remove for release)
        # if self.player.attacking:
        #     pygame.draw.rect(self.screen, (255,255,0),
        #                      self.camera.apply(self.player.attack_rect), 1)

        # HUD
        hud_coin = self.coin_frames[(pygame.time.get_ticks() // 90) % len(self.coin_frames)]
        self.player.draw_hud(self.screen, coin_icon=hud_coin)

        # Level name flash
        if self.level_flash_timer > 0:
            a = min(255, self.level_flash_timer * 4)
            img = self.font_big.render(
                f"Level {self.level_index+1}: {self.level_name}", True, CYAN)
            img.set_alpha(a)
            self.screen.blit(img, (SCREEN_W//2 - img.get_width()//2, SCREEN_H//2 - 30))

        # Highscore
        hs_img = self.font_small.render(
            f"Best: {self.highscore}", True, (160, 120, 220))
        self.screen.blit(hs_img, (SCREEN_W - 130, 44))

        # Whispers
        self.whisper.draw(self.screen)

    def _draw_bg_layers(self):
        for i, layer in enumerate(self.bg_layers):
            off = int(self.bg_offsets[i]) % SCREEN_W
            lw  = layer.get_width()
            x   = -off
            while x < SCREEN_W:
                self.screen.blit(layer, (x, 0))
                x += lw

    def _draw_exit(self):
        r = self.camera.apply(self.exit_rect)
        t = pygame.time.get_ticks() / 1000.0
        pulse = 18 + int(abs(math.sin(t * 2.2)) * 26)

        glow = pygame.Surface((r.w + 26, r.h + 24), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (120, 210, 170, 55), (4, glow.get_height() - 20, glow.get_width() - 8, 16))
        pygame.draw.rect(glow, (90, 180, 140, pulse), (8, 6, glow.get_width() - 16, glow.get_height() - 18), border_radius=10)
        self.screen.blit(glow, (r.x - 13, r.y - 10))
        self.screen.blit(self.exit_surf, r.topleft)

    # ── MENU ──────────────────────────────────────────────
    def _draw_menu(self):
        self.screen.fill(BG_COLOR)
        self._draw_menu_bg()

        # Title
        t = pygame.time.get_ticks() / 1000.0
        glow_r = int(abs(math.sin(t)) * 30) + 180

        title = self.font_title.render("WHISPERING", True, (glow_r, 80, 255))
        sub   = self.font_title.render("CAVERNS",    True, (80, glow_r, 255))
        self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 100))
        self.screen.blit(sub,   (SCREEN_W//2 - sub.get_width()//2,   168))

        # Tagline
        tag = self.font_small.render(
            "Welcome to Whispers Caverns!", True, GREY)
        self.screen.blit(tag, (SCREEN_W//2 - tag.get_width()//2, 244))

        # Buttons
        self._draw_menu_button("PRESS ENTER TO START", SCREEN_H//2 + 30,  CYAN)
        self._draw_menu_button("Controls: Arrow/WASD  Space=Jump  Shift=Dash  F=Attack  Esc=Pause",
                               SCREEN_H//2 + 90, GREY, size=16)
        self._draw_menu_button("[Q] Quit", SCREEN_H//2 + 140, (150, 80, 80), size=18)

        # Highscore
        if self.highscore > 0:
            hs = self.font_mid.render(f"🏆 Best Score: {self.highscore}", True, GOLD)
            self.screen.blit(hs, (SCREEN_W//2 - hs.get_width()//2, SCREEN_H//2 - 40))

        if self.highscore > 0:
            coin_icon = self.coin_frames[(pygame.time.get_ticks() // 90) % len(self.coin_frames)]
            hs = self.font_mid.render(f"Best Score: {self.highscore}", True, GOLD)
            total_w = coin_icon.get_width() + 10 + hs.get_width()
            x = SCREEN_W // 2 - total_w // 2
            clear_rect = pygame.Rect(x - 12, SCREEN_H // 2 - 48, total_w + 24, coin_icon.get_height() + 18)
            pygame.draw.rect(self.screen, BG_COLOR, clear_rect, border_radius=8)
            self.screen.blit(coin_icon, (x, SCREEN_H // 2 - 44))
            self.screen.blit(hs, (x + coin_icon.get_width() + 10, SCREEN_H // 2 - 40))

    def _draw_menu_bg(self):
        """Animated crystal particles in background."""
        t = pygame.time.get_ticks() / 1000.0
        for i in range(30):
            x = int((math.sin(t*0.3 + i*0.7) * 0.5 + 0.5) * SCREEN_W)
            y = int((math.cos(t*0.2 + i*0.5) * 0.5 + 0.5) * SCREEN_H)
            r = random.Random(i).randint(2, 6)
            col = [(80, 40, 200), (40, 160, 200), (140, 60, 255)][i % 3]
            pygame.draw.circle(self.screen, col, (x, y), r)

    def _draw_menu_button(self, text, y, color, size=22):
        font = pygame.font.SysFont("Arial", size, bold=True)
        img  = font.render(text, True, color)
        self.screen.blit(img, (SCREEN_W//2 - img.get_width()//2, y))

    # ── PAUSE ─────────────────────────────────────────────
    def _draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, "PAUSED", SCREEN_W//2, SCREEN_H//2 - 60,
                  CYAN, size=54, center=True)
        draw_text(self.screen, "ESC — Resume",   SCREEN_W//2, SCREEN_H//2 + 20,
                  WHITE, size=24, center=True)
        draw_text(self.screen, "M — Main Menu",  SCREEN_W//2, SCREEN_H//2 + 60,
                  WHITE, size=24, center=True)
        draw_text(self.screen, "Q — Quit",       SCREEN_W//2, SCREEN_H//2 + 100,
                  (200, 80, 80), size=24, center=True)

    # ── GAME OVER ─────────────────────────────────────────
    def _draw_game_over(self):
        self.screen.fill((8, 0, 4))
        t = pygame.time.get_ticks() / 1000.0
        r = int(abs(math.sin(t)) * 80) + 150

        draw_text(self.screen, "GAME OVER", SCREEN_W//2, 180,
                  (r, 30, 30), size=72, center=True)
        draw_text(self.screen, f"Score: {self.total_score}",
                  SCREEN_W//2, 290, WHITE, size=36, center=True)

        if self.new_highscore:
            draw_text(self.screen, "🏆 NEW HIGH SCORE!",
                      SCREEN_W//2, 345, GOLD, size=28, center=True)

        draw_text(self.screen, f"Best: {self.highscore}",
                  SCREEN_W//2, 390, GREY, size=22, center=True)

        draw_text(self.screen, "ENTER — Try Again",
                  SCREEN_W//2, 470, CYAN, size=26, center=True)
        draw_text(self.screen, "M — Main Menu",
                  SCREEN_W//2, 516, WHITE, size=22, center=True)
        draw_text(self.screen, "Q — Quit",
                  SCREEN_W//2, 558, (180, 70, 70), size=22, center=True)

        # Whisper at bottom
        whisp = self.font_small.render(
            random.choice(WHISPER_MSGS), True, (120, 60, 180))
        self.screen.blit(whisp, (SCREEN_W//2 - whisp.get_width()//2, SCREEN_H - 60))

    # ── VICTORY ───────────────────────────────────────────
    def _draw_victory(self):
        self.screen.fill((5, 15, 5))
        t = pygame.time.get_ticks() / 1000.0
        g = int(abs(math.sin(t)) * 80) + 160

        if self.level_index >= LEVEL_COUNT - 1:
            draw_text(self.screen, "YOU ESCAPED THE CAVERNS!", SCREEN_W//2, 130,
                      BIOLUM_GREEN, size=48, center=True)
            draw_text(self.screen, "The whispers are silent at last.",
                      SCREEN_W//2, 200, (120, 220, 140), size=24, center=True)
        else:
            next_name = ALL_LEVELS[self.level_index + 1]['name']
            draw_text(self.screen, f"Level {self.level_index+1} Complete!",
                      SCREEN_W//2, 140, (80, g, 80), size=52, center=True)
            draw_text(self.screen, f"Next: {next_name}",
                      SCREEN_W//2, 210, CYAN, size=26, center=True)

        draw_text(self.screen, f"Total Score: {self.total_score}",
                  SCREEN_W//2, 290, GOLD, size=36, center=True)

        if self.new_highscore:
            draw_text(self.screen, "🏆 NEW HIGH SCORE!", SCREEN_W//2, 345,
                      GOLD, size=28, center=True)

        bonus = LEVEL_BONUS * (self.level_index + 1)
        draw_text(self.screen, f"Level Bonus: +{bonus}",
                  SCREEN_W//2, 390, YELLOW, size=22, center=True)

        if self.level_index < LEVEL_COUNT - 1:
            draw_text(self.screen, "ENTER — Next Level",
                      SCREEN_W//2, 460, CYAN, size=26, center=True)
        else:
            draw_text(self.screen, "ENTER — Back to Menu",
                      SCREEN_W//2, 460, CYAN, size=26, center=True)
        draw_text(self.screen, "M — Main Menu",
                  SCREEN_W//2, 506, WHITE, size=22, center=True)
