# ============================================================
# game.py — Core game engine: states, update, render
# ============================================================
import pygame, math, random, sys
from settings import *
from utils     import (Camera, ParticleSystem, draw_text, draw_glow,
                       lerp_color, draw_chip, draw_keycap, heart_icon,
                       measure_chip)
from score     import load_highscore, save_highscore
from levels    import ALL_LEVELS, build_level
from entities.player  import Player
from entities.enemy   import Crawler, Flyer, Golem
from entities.boss    import Boss
from audio            import SoundManager
from echo_guidance    import EchoGuidanceSystem
from assets.generate_assets import (
    make_player_frames, make_crawler_frames, make_flyer_frames,
    make_golem_frames, make_coin_frames, make_powerup_surfaces,
    make_tile_surfaces, make_bg_layers, make_projectile_frames,
    make_exit_surface, make_boss_frames, make_boss_projectile_frames,
    make_boss_laser_frames, make_boss_shield_frames, make_chest_frames
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
        dbg("Game.__init__ -> initializing pygame + display")
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        self.state       = 'MENU'
        self.highscore   = load_highscore()
        self.level_index = 0
        self.total_score = 0
        self.lives       = START_LIVES
        self.new_highscore = False

        # Hit-stop: freezes game logic for N frames after impactful events
        self.hitstop_frames = 0

        # Level-transition fade overlay (alpha 0..255). >0 = fade is active.
        self.fade_alpha = 0
        self.fade_dir   = 0   # +1 = fading to black, -1 = fading back in

        # Audio
        self.sfx = SoundManager()

        self._load_assets()
        self.whisper = WhisperDisplay()

        # Echo Guidance System — atmospheric "find your way" mechanic.
        # Fully modular: press E in-game to enable/disable at will.
        self.echo_guidance = EchoGuidanceSystem(self.sfx,
                                                on_echo=self._on_echo_pulse)

        self._build_current_level()
        dbg("Game.__init__ -> ready, state =", self.state)

    # ── ASSETS ────────────────────────────────────────────
    def _load_assets(self):
        dbg("Game._load_assets -> generating sprite frames + fonts")
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
        self.chest_frames   = make_chest_frames()

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
        dbg(f"Game._build_current_level -> level {self.level_index+1}/{LEVEL_COUNT}: {ld['name']!r}")
        (self.player,
         self.platforms,
         self.hazards,
         self.enemies,
         self.coins,
         self.powerups,
         self.checkpoints,
         self.chests) = build_level(
            ld, self.tile_surfs, self.coin_frames, self.powerup_surfs,
            self.enemy_frames, Player, None,
            chest_frames=self.chest_frames)

        # Hand the player our SoundManager so it can play jump/dash/etc.
        self.player.sfx = self.sfx

        # Default respawn = player start. Updated when a checkpoint is touched.
        self.respawn_pos = ld['player_start']

        self.camera   = Camera(ld['world_w'], ld['world_h'])
        self.particles= ParticleSystem()
        self.exit_rect= ld['exit_rect']
        self.level_name = ld['name']
        self.bg_tint  = ld['bg_tint']
        self.bg_layers = make_bg_layers(self.level_index)
        self.level_flash_timer = 120   # show level name on entry

        # Boss spawning
        self.boss = None
        if ld.get('has_boss', False):
            # Default to mid-world; sit just above the lowest platform top so the
            # boss doesn't tumble through the air on spawn.
            default_spawn = (ld['world_w'] // 2, ld['world_h'] - 280)
            boss_x, boss_y = ld.get('boss_spawn', default_spawn)
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

        # Fresh level -> wipe the guidance system's live effects + memory.
        self.echo_guidance.reset()

        dbg(f"Game._build_current_level -> done: {len(self.enemies)} enemies, "
            f"{len(self.coins)} coins, {len(self.checkpoints)} checkpoints, "
            f"{len(self.chests)} chests, boss={'yes' if self.boss else 'no'}")

    # ── MAIN LOOP ─────────────────────────────────────────
    def run(self):
        dbg("Game.run -> main loop started")
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
                dbg("Game._handle_events -> QUIT requested, exiting")
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == 'PLAYING':
                        self.state = 'PAUSED'
                        dbg("Game._handle_events -> state PLAYING -> PAUSED")
                    elif self.state == 'PAUSED':
                        self.state = 'PLAYING'
                        dbg("Game._handle_events -> state PAUSED -> PLAYING")

                if self.state == 'MENU':
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        self._start_game()
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

                if self.state == 'PLAYING':
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.player.jump()
                    if event.key == pygame.K_e:
                        # Toggle the Echo Guidance System on/off.
                        self.echo_guidance.toggle()

                if self.state == 'GAME_OVER':
                    if event.key == pygame.K_RETURN:
                        self._start_game()
                    if event.key == pygame.K_m:
                        dbg("Game._handle_events -> state GAME_OVER -> MENU")
                        self.state = 'MENU'
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

                if self.state == 'VICTORY':
                    if event.key == pygame.K_RETURN:
                        self._next_level()
                    if event.key == pygame.K_m:
                        dbg("Game._handle_events -> state VICTORY -> MENU")
                        self.state = 'MENU'

                if self.state == 'PAUSED':
                    if event.key == pygame.K_m:
                        dbg("Game._handle_events -> state PAUSED -> MENU")
                        self.state = 'MENU'
                    if event.key == pygame.K_q:
                        pygame.quit(); sys.exit()

    # ── DAMAGE WRAPPER (sfx + shake + hit-stop) ───────────
    def _damage_player(self, amount, source_rect=None):
        """Damage the player and trigger SFX, screen shake, and hit-stop."""
        if self.player.inv_timer > 0 or not self.player.alive:
            return
        was_shielded = self.player.shielded
        prev_hp      = self.player.hp
        self.player.take_damage(amount, self.particles)
        # Player took an actual hit (not absorbed by shield) and is alive.
        if not was_shielded and self.player.hp < prev_hp and self.player.alive:
            self.camera.shake(6)
            self.hitstop_frames = max(self.hitstop_frames, 3)

    # ── ECHO GUIDANCE HELPERS ─────────────────────────────
    def _current_objective(self):
        """Resolve where the Echo Guidance System should point right now.

        Priority order:
          1. the next un-lit checkpoint (preferring ones ahead of the player),
          2. a living boss — it seals the exit, so guide into the fight,
          3. the level exit.

        Returns (world_pos, is_dynamic). `is_dynamic` is True for moving
        targets (the boss) so the guidance system doesn't mistake their
        motion for the player reaching a waypoint.
        """
        pending = [cp for cp in self.checkpoints if not cp.active]
        if pending:
            px = self.player.rect.centerx
            ahead = [cp for cp in pending if cp.rect.centerx >= px]
            pool  = ahead if ahead else pending
            target = min(pool, key=lambda cp: abs(cp.rect.centerx - px))
            return target.rect.center, False

        if self.boss and self.boss.alive:
            return self.boss.rect.center, True

        return self.exit_rect.center, False

    def _on_echo_pulse(self, intensity):
        """Callback fired by the Echo Guidance System on every pulse.

        When the player is badly lost, let a whisper bleed through — tying
        the navigation mechanic into the cavern's own voice.
        """
        if intensity > 0.6:
            self.whisper.trigger()

    # ── UPDATE ────────────────────────────────────────────
    def _update(self):
        # Level-transition fade advances independent of state pause.
        if self.fade_dir != 0:
            self.fade_alpha += self.fade_dir * 14
            if self.fade_alpha >= 255 and self.fade_dir > 0:
                self.fade_alpha = 255
                self._apply_pending_level_change()
            elif self.fade_alpha <= 0 and self.fade_dir < 0:
                self.fade_alpha = 0
                self.fade_dir = 0

        if self.state != 'PLAYING':
            return

        # Hit-stop: skip game logic for a few frames after impact.
        if self.hitstop_frames > 0:
            self.hitstop_frames -= 1
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

        # Echo Guidance System — point the player at the current objective.
        obj_pos, obj_dynamic = self._current_objective()
        self.echo_guidance.set_objective(obj_pos, dynamic=obj_dynamic)
        self.echo_guidance.update(self.player.rect, plat_list)

        # Let the death animation finish before switching states.
        if not self.player.alive:
            self.particles.update()
            self.whisper.update()
            if self.player.death_finished:
                self._handle_player_death()
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
                self.sfx.play('coin')
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

        # Checkpoints
        for cp in self.checkpoints:
            cp.update()
            if not cp.active and self.player.rect.colliderect(cp.rect):
                if cp.activate(self.particles):
                    self.respawn_pos = cp.respawn_pos
                    self.sfx.play('checkpoint')

        # Treasure chest(s) — final-stage reward: score bonus + extra life.
        for chest in self.chests:
            chest.update()
            if not chest.opened and self.player.rect.colliderect(chest.rect):
                if chest.open(self.particles):
                    self.player.add_score(CHEST_SCORE)
                    self.lives += CHEST_LIVES
                    self.sfx.play('level_complete')
                    self.camera.shake(5)
                    dbg(f"Game._update -> chest opened: +{CHEST_SCORE} score, "
                        f"+{CHEST_LIVES} life (lives={self.lives})")

        # Enemies
        from entities.enemy import Flyer as FlyerCls
        for enemy in list(self.enemies):
            enemy_alive_before = enemy.alive
            enemy.update(plat_list, self.player, self.particles)

            # Enemy body hits player
            touching_enemy = self.player.rect.colliderect(enemy.rect)
            if touching_enemy and hasattr(enemy, 'on_player_contact'):
                enemy.on_player_contact()
            if touching_enemy and enemy.alive and self.player.inv_timer == 0:
                self._damage_player(enemy.dmg)
                self.whisper.trigger()

            # Flyer projectiles hit player
            if isinstance(enemy, FlyerCls):
                for proj in list(enemy.projectiles):
                    if self.player.rect.colliderect(proj.rect):
                        self._damage_player(1)
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
                    self.sfx.play('enemy_die')
                    self.camera.shake(4)
                    self.hitstop_frames = max(self.hitstop_frames, 2)

        # Hazards
        for haz in self.hazards:
            if self.player.rect.colliderect(haz.rect):
                self.camera.shake(8)
                self.player.take_damage(PLAYER_HP, self.particles)  # instant kill

        # Boss
        if self.boss:
            self.boss.update(plat_list, self.player.rect)

            # Boss projectiles hit player
            for proj in list(self.boss.projectiles):
                if self.player.rect.colliderect(proj.rect):
                    if self.player.inv_timer == 0:
                        self._damage_player(1)
                    proj.kill()

            # Boss lasers hit player
            for laser in list(self.boss.lasers):
                if self.player.rect.colliderect(laser.get_collision_rect()):
                    if self.player.inv_timer == 0:
                        self._damage_player(1)

            # Player attack hits boss
            if (self.boss.alive and self.player.attacking
                    and self.player.attack_rect.colliderect(self.boss.rect)):
                boss_alive_before = self.boss.alive
                blocked = self.boss.take_damage(1, self.particles)
                if blocked:
                    self.sfx.play('shield_block')
                if not self.boss.alive and boss_alive_before:
                    self.player.add_score(500)
                    self.camera.shake(14)
                    self.hitstop_frames = max(self.hitstop_frames, 6)
                    self.sfx.play('enemy_die')

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

    # ── DEATH / RESPAWN ───────────────────────────────────
    def _handle_player_death(self):
        """Called once when the player's death animation finishes."""
        self.lives -= 1
        dbg(f"Game._handle_player_death -> player died, lives left = {self.lives}")
        if self.lives > 0:
            self._respawn_at_checkpoint()
        else:
            # Out of lives - end the run.
            self.total_score += self.player.score
            self.new_highscore = save_highscore(self.total_score)
            self.highscore     = load_highscore()
            self.sfx.play('game_over')
            self.state = 'GAME_OVER'
            dbg(f"Game._handle_player_death -> out of lives, state -> GAME_OVER "
                f"(total_score={self.total_score}, new_highscore={self.new_highscore})")

    def _respawn_at_checkpoint(self):
        """Resurrect the player at the last checkpoint with full HP."""
        rx, ry = self.respawn_pos
        dbg(f"Game._respawn_at_checkpoint -> respawning at {self.respawn_pos}")
        kept_score = self.player.score
        kept_coins = self.player.coins

        self.player = Player(rx, ry, self.enemy_frames['player'])
        self.player.sfx   = self.sfx
        self.player.score = kept_score
        self.player.coins = kept_coins
        self.player.inv_timer = PLAYER_INVINCIBLE * 2  # brief grace period

        # Visual: blue puff at respawn point
        self.particles.emit(rx + 20, ry + 24, CYAN,
                            count=18, speed=4, life=28, size=4, gravity=-0.05)
        self.sfx.play('checkpoint')

    # ── LEVEL PROGRESSION ─────────────────────────────────
    def _start_game(self):
        dbg("Game._start_game -> new run, state -> PLAYING")
        self.level_index  = 0
        self.total_score  = 0
        self.lives        = START_LIVES
        self.fade_alpha   = 0
        self.fade_dir     = 0
        self.hitstop_frames = 0
        self._pending_action = None
        self.state        = 'PLAYING'
        self._build_current_level()

    def _complete_level(self):
        bonus = LEVEL_BONUS * (self.level_index + 1)
        self.player.add_score(bonus)
        self.total_score += self.player.score
        self.sfx.play('level_complete')
        dbg(f"Game._complete_level -> level {self.level_index+1} cleared, "
            f"bonus +{bonus}, total_score={self.total_score}, state -> VICTORY")

        if self.level_index >= LEVEL_COUNT - 1:
            # All levels complete
            self.new_highscore = save_highscore(self.total_score)
            self.highscore     = load_highscore()
        self.state = 'VICTORY'

    def _next_level(self):
        if self.level_index < LEVEL_COUNT - 1:
            # Start a fade-to-black; the level swap happens at fade peak.
            dbg("Game._next_level -> fade-out queued for next level")
            self._pending_action = 'next_level'
            self.fade_dir   = 1
            self.fade_alpha = 0
        else:
            dbg("Game._next_level -> no more levels, state -> MENU")
            self.state = 'MENU'

    def _apply_pending_level_change(self):
        """Run the queued level transition when fade hits black."""
        action = getattr(self, '_pending_action', None)
        if action == 'next_level':
            self.level_index += 1
            dbg(f"Game._apply_pending_level_change -> advancing to level {self.level_index+1}")
            self._build_current_level()
            self.state = 'PLAYING'
        self._pending_action = None
        self.fade_dir = -1   # fade back in

    # ── DRAW ──────────────────────────────────────────────
    def _draw(self):
        if   self.state == 'MENU':      self._draw_menu()
        elif self.state == 'PLAYING':   self._draw_playing()
        elif self.state == 'PAUSED':    self._draw_playing(); self._draw_pause_overlay()
        elif self.state == 'GAME_OVER': self._draw_game_over()
        elif self.state == 'VICTORY':   self._draw_victory()

        # Transition fade goes on top of everything.
        if self.fade_alpha > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(self.fade_alpha)
            self.screen.blit(overlay, (0, 0))

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

        # Checkpoint torches (with glow when active)
        for cp in self.checkpoints:
            cp.draw_glow(self.screen, self.camera)
            self.screen.blit(cp.image, self.camera.apply(cp.rect))

        # Treasure chest(s) — golden glow + sprite
        for chest in self.chests:
            chest.draw_glow(self.screen, self.camera)
            self.screen.blit(chest.image, self.camera.apply(chest.rect))

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

        # Echo Guidance System — rings, motes and edge-resonance, drawn in
        # world space beneath the player so it reads as part of the cavern.
        self.echo_guidance.draw(self.screen, self.camera)

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

        # Level name banner (entry flash)
        if self.level_flash_timer > 0:
            self._draw_level_banner()

        # Highscore chip (top-right, under coin chip)
        font_xs = pygame.font.SysFont("Arial", 13, bold=True)
        hs_text = f"BEST  {self.highscore}"
        hs_w, _ = measure_chip(hs_text, font_xs, padding=8)
        draw_chip(self.screen, SCREEN_W - hs_w - 20, 56, hs_text, font_xs,
                  fg=(220, 180, 255), bg=(20, 14, 32),
                  border=(120, 80, 200), padding=8, radius=8)

        # Lives row (top-left, below HP hearts) - outline hearts to distinguish
        # them visually from the filled HP hearts above.
        for i in range(self.lives):
            x = 22 + i * 22
            self.screen.blit(heart_icon(18, filled=True,
                                        color=(255, 120, 120)),
                             (x, 50))
        # Plus dim slots for lost lives
        for i in range(self.lives, START_LIVES):
            x = 22 + i * 22
            self.screen.blit(heart_icon(18, filled=False), (x, 50))

    def _draw_level_banner(self):
        a = min(255, self.level_flash_timer * 4)
        title = self.font_big.render(
            f"Level {self.level_index+1}", True, (220, 200, 255))
        name  = self.font_mid.render(self.level_name, True, CYAN)

        bw = max(title.get_width(), name.get_width()) + 80
        bh = title.get_height() + name.get_height() + 28

        banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(banner, (15, 8, 30, 200), (0, 0, bw, bh),
                         border_radius=12)
        pygame.draw.rect(banner, (140, 90, 220, 255), (0, 0, bw, bh),
                         2, border_radius=12)
        banner.blit(title, ((bw - title.get_width()) // 2, 10))
        banner.blit(name,  ((bw - name.get_width()) // 2,
                            14 + title.get_height()))
        banner.set_alpha(a)
        self.screen.blit(banner,
                         (SCREEN_W // 2 - bw // 2, SCREEN_H // 2 - bh // 2 - 50))

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

        t = pygame.time.get_ticks() / 1000.0

        # ── TITLE with halo glow ──────────────────────────
        title_y = 88
        cx = SCREEN_W // 2
        # Soft radial halo (outer-only fade, no additive pile-up)
        halo_r = 260 + int(abs(math.sin(t * 0.6)) * 25)
        halo = pygame.Surface((halo_r * 2, halo_r * 2), pygame.SRCALPHA)
        # Single non-additive radial gradient
        for step in range(halo_r, 0, -2):
            # bell-curve falloff peaks at ~70% radius, fades to 0 at edges
            d = step / halo_r
            falloff = max(0.0, 1.0 - ((d - 0.0) ** 1.6))
            a = int(falloff * 18)   # very subtle
            if a <= 0:
                continue
            pygame.draw.circle(halo, (90, 40, 180, a),
                               (halo_r, halo_r), step)
        self.screen.blit(halo, (cx - halo_r, title_y - 30))

        # Pulse-colored title text with soft drop shadow
        pulse = int(abs(math.sin(t)) * 30) + 200
        title_a = self.font_title.render("WHISPERING", True, (pulse, 110, 255))
        title_b = self.font_title.render("CAVERNS",    True, (110, pulse, 255))
        shadow_a = self.font_title.render("WHISPERING", True, (8, 4, 18))
        shadow_b = self.font_title.render("CAVERNS",    True, (8, 4, 18))

        self.screen.blit(shadow_a, (cx - title_a.get_width()//2 + 3, title_y + 3))
        self.screen.blit(title_a,  (cx - title_a.get_width()//2,    title_y))
        self.screen.blit(shadow_b, (cx - title_b.get_width()//2 + 3, title_y + 71))
        self.screen.blit(title_b,  (cx - title_b.get_width()//2,    title_y + 68))

        # Tagline
        tag_font = pygame.font.SysFont("Georgia", 18, italic=True)
        tag = tag_font.render(
            "The deeper you go, the louder the whispers...",
            True, (170, 140, 220))
        self.screen.blit(tag, (cx - tag.get_width()//2, title_y + 150))

        # ── BEST SCORE chip (under tagline) ───────────────
        if self.highscore > 0:
            coin_icon = self.coin_frames[
                (pygame.time.get_ticks() // 90) % len(self.coin_frames)]
            hs_text = f"BEST  {self.highscore}"
            hs_font = pygame.font.SysFont("Arial", 22, bold=True)
            hw, _ = measure_chip(hs_text, hs_font, icon=coin_icon)
            draw_chip(self.screen, cx - hw // 2, title_y + 188,
                      hs_text, hs_font,
                      fg=GOLD, bg=(20, 12, 32),
                      border=(200, 160, 60), icon=coin_icon)

        # ── PLAY PILL (breathing) ─────────────────────────
        play_w, play_h = 280, 64
        pulse_a = int(70 + abs(math.sin(t * 1.5)) * 60)   # 70..130
        play_y = 460
        play_x = cx - play_w // 2

        # Soft outer glow (one pass, alpha-faded outline rings)
        glow_pad = 30
        glow = pygame.Surface((play_w + glow_pad * 2,
                               play_h + glow_pad * 2), pygame.SRCALPHA)
        for r_step in range(glow_pad, 0, -1):
            falloff = (r_step / glow_pad) ** 2
            a = int(pulse_a * (1 - falloff) * 0.18)
            if a <= 0:
                continue
            pygame.draw.rect(glow, (120, 200, 255, a),
                             (glow_pad - r_step, glow_pad - r_step,
                              play_w + r_step * 2, play_h + r_step * 2),
                             1, border_radius=play_h // 2 + r_step)
        self.screen.blit(glow, (play_x - glow_pad, play_y - glow_pad))

        # Pill body
        pill = pygame.Surface((play_w, play_h), pygame.SRCALPHA)
        pygame.draw.rect(pill, (24, 16, 44, 240), (0, 0, play_w, play_h),
                         border_radius=play_h // 2)
        pygame.draw.rect(pill, (120, 220, 255, 255), (0, 0, play_w, play_h),
                         3, border_radius=play_h // 2)
        self.screen.blit(pill, (play_x, play_y))

        play_font = pygame.font.SysFont("Arial", 28, bold=True)
        play_text = play_font.render("PRESS  ENTER", True, (220, 245, 255))
        self.screen.blit(play_text,
                         (cx - play_text.get_width() // 2,
                          play_y + (play_h - play_text.get_height()) // 2))

        # ── CONTROLS GRID ─────────────────────────────────
        self._draw_menu_controls(cx, play_y + play_h + 24)

        # ── FOOTER (credits + quit) ───────────────────────
        foot_font = pygame.font.SysFont("Arial", 13)
        cred = foot_font.render(
            "Abdellah Bouabdli  &  Ahmed ELKALAI   ·   Genie Info 3   ·   2026",
            True, (110, 90, 160))
        self.screen.blit(cred,
                         (cx - cred.get_width() // 2, SCREEN_H - 28))

        q_font = pygame.font.SysFont("Arial", 14, bold=True)
        q_cap = draw_keycap(self.screen, 24, SCREEN_H - 44, "Q", q_font,
                            border=(180, 90, 90))
        q_lab = q_font.render("Quit", True, (200, 130, 130))
        self.screen.blit(q_lab,
                         (q_cap.right + 8,
                          q_cap.y + (q_cap.h - q_lab.get_height()) // 2))

    def _draw_menu_controls(self, cx, y_top):
        """Render a 2-column controls grid with key caps."""
        rows = [
            ("← →  /  A D", "Move"),
            ("Space / W / ↑", "Jump  (double)"),
            ("Shift",         "Dash"),
            ("F  /  LMB",     "Attack"),
            ("Esc",           "Pause"),
            ("E",             "Echo Guidance"),
        ]
        font_key   = pygame.font.SysFont("Arial", 13, bold=True)
        font_label = pygame.font.SysFont("Arial", 14)

        # Pre-measure widest key cap text for alignment
        col_gap   = 36
        row_h     = 28
        n_rows    = (len(rows) + 1) // 2
        max_kw    = max(font_key.size(k)[0] for k, _ in rows) + 18
        max_lw    = max(font_label.size(l)[0] for _, l in rows) + 6
        cell_w    = max_kw + 10 + max_lw
        total_w   = cell_w * 2 + col_gap
        x0        = cx - total_w // 2

        # Panel backdrop
        pad = 16
        panel = pygame.Surface((total_w + pad * 2, row_h * n_rows + pad * 2),
                               pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 8, 30, 180),
                         (0, 0, panel.get_width(), panel.get_height()),
                         border_radius=12)
        pygame.draw.rect(panel, (100, 70, 180, 180),
                         (0, 0, panel.get_width(), panel.get_height()),
                         1, border_radius=12)
        self.screen.blit(panel, (x0 - pad, y_top - pad))

        for idx, (key, label) in enumerate(rows):
            col = idx % 2
            row = idx // 2
            rx = x0 + col * (cell_w + col_gap)
            ry = y_top + row * row_h
            cap = draw_keycap(self.screen, rx, ry, key, font_key,
                              min_w=max_kw, h=22)
            lab = font_label.render(label, True, (210, 200, 230))
            self.screen.blit(lab,
                             (cap.right + 10,
                              ry + (cap.h - lab.get_height()) // 2))

    def _draw_menu_bg(self):
        """Vignette + drifting upward 'embers'."""
        # Background ember field
        t = pygame.time.get_ticks() / 1000.0
        for i in range(45):
            seed = random.Random(i)
            base_x = seed.randint(0, SCREEN_W)
            speed  = seed.uniform(15, 45)
            life   = seed.uniform(6, 14)
            phase  = (t * speed / 80 + i * 0.37) % 1.0
            x = int(base_x + math.sin(t * 0.3 + i) * 30)
            y = int(SCREEN_H - phase * SCREEN_H - 20)
            r = 2 + seed.randint(0, 3)
            col_choices = [(140, 60, 220), (90, 50, 180),
                           (180, 100, 255), (60, 160, 220)]
            col = col_choices[i % len(col_choices)]
            a = int(180 * (1 - phase))
            dot = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            for rr in range(r * 2, 0, -1):
                pygame.draw.circle(dot, (*col, a // (rr + 1)),
                                   (r * 2, r * 2), rr)
            self.screen.blit(dot, (x - r * 2, y - r * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # Vignette
        vign = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for step in range(80):
            a = int(step * 1.6)
            pygame.draw.rect(vign, (0, 0, 0, a),
                             (step, step,
                              SCREEN_W - step * 2, SCREEN_H - step * 2),
                             1)
        self.screen.blit(vign, (0, 0))

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
