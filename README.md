
# 🕯️ Whispering Caverns

> *"The deeper you go, the louder the whispers become..."*

A 2D Metroidvania platformer built with **Python + PyGame**.  
Made by **Abdellah Bouabdli & Ahmed ELKALAI** — Génie Info 3 — Encadrant: HAJJI TARIK

---

## 🎮 About the Game

**Whispering Caverns** is a 2D side-scrolling platformer where you play as a lone explorer
descending into a vast underground world of ancient caves filled with forgotten civilizations,
dangerous creatures, and mysterious voices that echo through the stone.

Navigate 3 hand-crafted cave levels, collect coins, defeat enemies, and reach the exit
before your health runs out — all while the caverns whisper their secrets around you.

---

## 🚀 Installation & Running

### Requirements
- Python 3.8+
- PyGame 2.x

### Install PyGame
```bash
pip install pygame
```

### Run the Game
```bash
cd whispering_caverns
python main.py
```

---

## 🕹️ Controls

| Key | Action |
|-----|--------|
| `←` / `A` | Move Left |
| `→` / `D` | Move Right |
| `Space` / `W` / `↑` | Jump (double-jump supported!) |
| `Shift` | Dash (quick burst of speed) |
| `F` / Left Mouse | Attack (melee slash) |
| `Esc` | Pause / Resume |
| `M` (paused) | Back to Main Menu |
| `Q` | Quit |
| `Enter` | Confirm / Start |

---

## 📁 Project Structure

```
whispering_caverns/
│
├── main.py              ← Entry point — run this!
├── settings.py          ← All constants (physics, colors, speeds)
├── game.py              ← Game engine: states, loop, rendering
├── utils.py             ← Camera, ParticleSystem, draw helpers
├── levels.py            ← Level definitions & builder (3 levels)
├── score.py             ← High score persistence (JSON)
│
├── entities/
│   ├── player.py        ← Player: movement, dash, attack, HP
│   ├── enemy.py         ← Crawler (bat), Flyer (ghost), Golem
│   └── powerup.py       ← Coin (spinning), Speed & Shield orbs
│
├── assets/
│   ├── generate_assets.py  ← Procedural art (no external images needed!)
│   ├── images/          ← (place real sprites here later)
│   ├── sounds/          ← (place .ogg/.wav files here later)
│   └── fonts/           ← (place .ttf files here later)
│
└── data/
    └── highscore.json   ← Auto-created on first save
```

---

## 🗺️ Levels

| # | Name | Theme |
|---|------|-------|
| 1 | The Entrance Cavern | Dark stone, intro difficulty |
| 2 | Crystal Depths | Crystal platforms, harder jumps |
| 3 | The Whispering Core | Lava hazards, maximum enemies |

---

## 👾 Enemies

| Enemy | Behavior | HP | Score |
|-------|----------|----|-------|
| **Crawler** (Bat) | Patrols platforms, reverses at edges | 2 | 50 |
| **Flyer** (Ghost) | Sine-wave hover, chases player | 1 | 75 |
| **Golem** (Rock) | Slow but tanky, jumps at player | 6 | 200 |

---

## ⭐ Scoring

| Event | Points |
|-------|--------|
| Coin collected | +10 |
| Crawler defeated | +50 |
| Flyer defeated | +75 |
| Golem defeated | +200 |
| Level 1 complete | +500 |
| Level 2 complete | +1,000 |
| Level 3 complete | +1,500 |

---

## 🎁 Power-ups

- **⚡ Speed Boost** — Doubles movement speed for 5 seconds (yellow orb)
- **🛡️ Shield** — Absorbs one hit completely (blue orb)

---

## 🎨 Visual Style

All art is procedurally generated using PyGame drawing — no external image files required.
To add real sprites, place PNG files in `assets/images/` and update the frame-loading
functions in `assets/generate_assets.py`.

### Adding Real Assets Later
- **Sprites**: Replace functions in `generate_assets.py` with `pygame.image.load()`
- **Music**: Add `.ogg` files to `assets/sounds/` and call `pygame.mixer.music.load()`
- **Sound effects**: Use `pygame.mixer.Sound()` for hit, jump, coin, dash sounds
- **Fonts**: Place `.ttf` files in `assets/fonts/` and load with `pygame.font.Font()`

---

## 🔧 Modifying the Game

### Change difficulty
Edit `settings.py`:
- `PLAYER_HP` — Player health
- `CRAWLER_SPEED`, `FLYER_SPEED`, `GOLEM_HP` — Enemy stats
- `GRAVITY`, `JUMP_POWER` — Physics feel

### Add a new level
Add a new dict to `ALL_LEVELS` in `levels.py` following the existing pattern,
and increment `LEVEL_COUNT` in `settings.py`.

### Add new enemy types
Subclass `BaseEnemy` in `entities/enemy.py` and add entries in `levels.py`.

---

## 📋 Technical Stack

- **Language**: Python 3.8+
- **Library**: PyGame 2.x
- **Architecture**: Object-Oriented, modular files
- **Art**: Procedural (PyGame drawing primitives)
- **Persistence**: JSON (high score)
- **Platform**: PC (Windows / macOS / Linux)

---

*Whispering Caverns — A student project by Abdellah Bouabdli & Ahmed ELKALAI, 2026*
#
