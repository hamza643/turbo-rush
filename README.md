# Turbo Rush

An endless top-down car racing game built with **Python and Pygame**, in a single file.
Dodge traffic, collect coins, grab shields and race through day and night.

![Gameplay at night](screenshots/gameplay-night.png)

## Features

- Fullscreen gameplay (toggle with `F11`), 1280x720 scaled to any screen
- Main menu, pause menu with **Resume / Restart / Main Menu**
- Glossy cars, trucks and taxis with smooth sprites
- Day/night cycle with headlights, street lamps and glowing taillights
- Nitro boost, shield power-up, coins, 3 lives
- Particle effects, screen shake, speedometer HUD
- Sound effects (generated in code, no asset files needed)
- High score saved locally

![Main menu](screenshots/main-menu.png)

## Install and run

```bash
git clone https://github.com/<your-username>/turbo-rush.git
cd turbo-rush
pip install -r requirements.txt
python car_game.py
```

Requires Python 3.8+.

## Controls

| Key | Action |
|---|---|
| Left / Right or A / D | Steer |
| Space / Up / W | Nitro boost (hold) |
| P or Esc | Pause menu |
| F11 or F | Fullscreen on/off |
| M | Mute |
| Up / Down + Enter | Navigate menus (mouse works too) |

## Gameplay tips

- Each coin is worth 10 points, distance adds to your score.
- The cyan shield lets you smash through cars for a few seconds.
- Nitro refills while you are not using it.

## License

MIT