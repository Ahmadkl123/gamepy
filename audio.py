# ============================================================
# audio.py - Procedural sound effects (no external files needed)
# ============================================================
#
# Generates short SFX as PCM int16 buffers and hands them to
# pygame.mixer.Sound. No numpy required - just stdlib `array`.
#
import math
import random
from array import array

import pygame

from settings import dbg

SAMPLE_RATE = 22050
MAX_AMP     = 28000   # leave headroom below int16 max (32767)


def _silence(duration):
    return array('h', [0] * int(SAMPLE_RATE * duration))


def _envelope(i, total, attack=0.05, release=0.2):
    """Linear attack/release envelope, 0..1."""
    a = int(total * attack)
    r = int(total * release)
    if i < a:
        return i / max(1, a)
    if i > total - r:
        return max(0.0, (total - i) / max(1, r))
    return 1.0


def _tone(freq, duration, amp=0.6, wave='sine', sweep=0.0,
          attack=0.05, release=0.3):
    """One waveform burst with optional pitch sweep (sweep>0 rises)."""
    n = int(SAMPLE_RATE * duration)
    buf = array('h', [0] * n)
    for i in range(n):
        t = i / SAMPLE_RATE
        f = freq * (1.0 + sweep * (i / n))
        phase = 2 * math.pi * f * t
        if wave == 'sine':
            s = math.sin(phase)
        elif wave == 'square':
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == 'saw':
            s = 2 * ((f * t) - math.floor(0.5 + f * t))
        elif wave == 'triangle':
            s = 2 * abs(2 * ((f * t) - math.floor(0.5 + f * t))) - 1
        else:
            s = 0.0
        env = _envelope(i, n, attack, release)
        buf[i] = int(s * amp * env * MAX_AMP)
    return buf


def _noise(duration, amp=0.4, lowpass=0.0, attack=0.01, release=0.25):
    """White noise burst with optional simple lowpass (0..1)."""
    n = int(SAMPLE_RATE * duration)
    buf = array('h', [0] * n)
    prev = 0.0
    for i in range(n):
        s = random.uniform(-1.0, 1.0)
        if lowpass > 0:
            s = prev * lowpass + s * (1 - lowpass)
            prev = s
        env = _envelope(i, n, attack, release)
        buf[i] = int(s * amp * env * MAX_AMP)
    return buf


def _mix(*bufs):
    """Sum equal-length buffers, clamped to int16."""
    n = max(len(b) for b in bufs)
    out = array('h', [0] * n)
    for b in bufs:
        for i in range(len(b)):
            v = out[i] + b[i]
            if v >  32767: v =  32767
            if v < -32768: v = -32768
            out[i] = v
    return out


def _concat(*bufs):
    out = array('h')
    for b in bufs:
        out.extend(b)
    return out


def _make_sound(buf):
    """Wrap a mono int16 buffer in a pygame Sound."""
    # pygame.mixer.Sound accepts a buffer object that supports the
    # buffer protocol. array('h') qualifies.
    return pygame.mixer.Sound(buffer=buf.tobytes())


# ─────────────────────────────────────────────
#  SOUND RECIPES
# ─────────────────────────────────────────────
def _sfx_jump():
    return _tone(420, 0.14, amp=0.45, wave='triangle', sweep=0.9,
                 attack=0.02, release=0.45)


def _sfx_dash():
    a = _noise(0.18, amp=0.42, lowpass=0.55, attack=0.01, release=0.6)
    b = _tone(180, 0.18, amp=0.25, wave='saw', sweep=-0.4)
    return _mix(a, b)


def _sfx_coin():
    a = _tone(880, 0.07, amp=0.40, wave='sine', attack=0.01, release=0.3)
    b = _tone(1320, 0.12, amp=0.35, wave='sine', attack=0.01, release=0.5)
    silence = _silence(0.05)
    return _concat(a, silence, b)


def _sfx_attack():
    a = _noise(0.12, amp=0.35, lowpass=0.3, attack=0.005, release=0.7)
    b = _tone(620, 0.10, amp=0.20, wave='triangle', sweep=-0.5)
    return _mix(a, b)


def _sfx_hit():
    a = _noise(0.18, amp=0.55, lowpass=0.75, attack=0.005, release=0.6)
    b = _tone(120, 0.16, amp=0.45, wave='square', sweep=-0.6)
    return _mix(a, b)


def _sfx_enemy_die():
    a = _tone(330, 0.22, amp=0.45, wave='saw', sweep=-0.65,
              attack=0.01, release=0.6)
    b = _noise(0.22, amp=0.35, lowpass=0.4)
    return _mix(a, b)


def _sfx_player_die():
    a = _tone(440, 0.55, amp=0.45, wave='triangle', sweep=-0.7,
              attack=0.01, release=0.55)
    b = _tone(220, 0.55, amp=0.30, wave='sine', sweep=-0.5)
    return _mix(a, b)


def _sfx_powerup():
    a = _tone(660, 0.10, amp=0.30, wave='sine', attack=0.01, release=0.5)
    b = _tone(880, 0.10, amp=0.30, wave='sine', attack=0.01, release=0.5)
    c = _tone(1320, 0.18, amp=0.35, wave='sine', attack=0.01, release=0.6)
    pad = _silence(0.03)
    return _concat(a, pad, b, pad, c)


def _sfx_checkpoint():
    a = _tone(523, 0.10, amp=0.32, wave='sine', attack=0.01, release=0.5)
    b = _tone(784, 0.18, amp=0.34, wave='sine', attack=0.01, release=0.6)
    pad = _silence(0.04)
    return _concat(a, pad, b)


def _sfx_level_complete():
    notes = [523, 659, 784, 1047]   # C E G C
    parts = []
    for f in notes:
        parts.append(_tone(f, 0.16, amp=0.32, wave='triangle',
                           attack=0.01, release=0.4))
        parts.append(_silence(0.02))
    return _concat(*parts)


def _sfx_game_over():
    return _tone(220, 0.9, amp=0.42, wave='triangle', sweep=-0.6,
                 attack=0.02, release=0.7)


def _sfx_shield_block():
    return _mix(
        _tone(880, 0.10, amp=0.35, wave='sine', attack=0.005, release=0.4),
        _noise(0.10, amp=0.25, lowpass=0.7, attack=0.005, release=0.6),
    )


def _sfx_echo_pulse():
    """Sonar-style ping used by the Echo Guidance System — a mid tone with
    a long, hollow tail and a faint lower octave for cavern depth."""
    a = _tone(620, 0.55, amp=0.20, wave='sine', sweep=-0.25,
              attack=0.005, release=0.88)
    b = _tone(310, 0.55, amp=0.13, wave='sine', sweep=-0.20,
              attack=0.02, release=0.92)
    return _mix(a, b)


def _sfx_echo_resonance():
    """Soft rising shimmer played when the player reaches a new waypoint."""
    a = _tone(523, 0.40, amp=0.18, wave='sine', sweep=0.40,
              attack=0.02, release=0.82)
    b = _tone(784, 0.50, amp=0.16, wave='triangle', sweep=0.30,
              attack=0.05, release=0.88)
    return _concat(a, _silence(0.04), b)


# ─────────────────────────────────────────────
#  PUBLIC MANAGER
# ─────────────────────────────────────────────
class SoundManager:
    """
    Lazy proxy for SFX. Generates sounds on first init.
    Falls back to silent no-ops if mixer can't initialize
    (e.g. headless CI, missing audio device).
    """

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            dbg("SoundManager -> mixer unavailable, running silent")
            return

        recipes = {
            'jump'          : _sfx_jump,
            'dash'          : _sfx_dash,
            'coin'          : _sfx_coin,
            'attack'        : _sfx_attack,
            'hit'           : _sfx_hit,
            'enemy_die'     : _sfx_enemy_die,
            'player_die'    : _sfx_player_die,
            'powerup'       : _sfx_powerup,
            'checkpoint'    : _sfx_checkpoint,
            'level_complete': _sfx_level_complete,
            'game_over'     : _sfx_game_over,
            'shield_block'  : _sfx_shield_block,
            'echo_pulse'    : _sfx_echo_pulse,
            'echo_resonance': _sfx_echo_resonance,
        }
        for name, fn in recipes.items():
            try:
                self.sounds[name] = _make_sound(fn())
            except Exception:
                pass

        dbg(f"SoundManager -> ready, {len(self.sounds)}/{len(recipes)} SFX generated")

        # Default volumes per category
        for key, vol in {
            'jump': 0.35, 'dash': 0.4, 'coin': 0.45,
            'attack': 0.35, 'hit': 0.55, 'enemy_die': 0.45,
            'player_die': 0.6, 'powerup': 0.55, 'checkpoint': 0.5,
            'level_complete': 0.55, 'game_over': 0.55,
            'shield_block': 0.5,
            'echo_pulse': 0.4, 'echo_resonance': 0.5,
        }.items():
            s = self.sounds.get(key)
            if s is not None:
                s.set_volume(vol)

    def play(self, name):
        if not self.enabled:
            return
        s = self.sounds.get(name)
        if s is not None:
            s.play()
