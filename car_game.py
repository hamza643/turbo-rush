"""
TURBO RUSH  -  Endless Car Racing Game  (single file)
-----------------------------------------------------
Install :  pip install pygame
Run     :  python car_game.py

Controls
  LEFT / RIGHT or A / D ... steer
  SPACE / UP / W .......... nitro boost (hold)
  P or ESC ................ pause menu
  F11 or F ................ fullscreen on/off
  M ....................... mute
  Menus: UP/DOWN + ENTER, or use the mouse
"""
import array
import math
import os
import random
import sys

os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")
import pygame

# ------------------------------------------------------------------ settings
W, H = 1280, 720
FPS = 60
LANES = 4
LANE_W = 128
ROAD_W = LANES * LANE_W
EDGE_L = (W - ROAD_W) // 2
EDGE_R = EDGE_L + ROAD_W
PLAYER_Y = H - 170
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

HIT = {"sport": (44, 100), "sedan": (48, 112), "taxi": (48, 112), "truck": (58, 178)}
CAR_SIZES = {"sport": (66, 126), "sedan": (70, 138), "taxi": (70, 138), "truck": (82, 210)}


def lane_x(i):
    return EDGE_L + LANE_W * i + LANE_W // 2


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp_c(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighten(c, v):
    return tuple(min(255, x + v) for x in c[:3])


def darken(c, v):
    return tuple(max(0, x - v) for x in c[:3])


# ------------------------------------------------------------ drawing helpers
def vgrad(w, h, top, bot, radius=0):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        pygame.draw.line(s, lerp_c(top, bot, y / max(1, h - 1)), (0, y), (w, y))
    if radius:
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(m, (255, 255, 255, 255), (0, 0, w, h), border_radius=radius)
        s.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return s


def glow(radius, color, strength=1.0):
    """Additive light sprite (black background, use BLEND_RGB_ADD)."""
    s = pygame.Surface((radius * 2, radius * 2))
    for i in range(radius, 0, -1):
        k = ((1 - i / radius) ** 2) * strength
        pygame.draw.circle(s, tuple(min(255, int(v * k)) for v in color), (radius, radius), i)
    return s


def soft_shadow(w, h, alpha=110, pad=14, corner=18):
    sw, sh = max(2, (w + pad * 2) // 4), max(2, (h + pad * 2) // 4)
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, alpha), (pad // 4, pad // 4, max(1, w // 4), max(1, h // 4)),
                     border_radius=max(1, corner // 4))
    return pygame.transform.smoothscale(s, (w + pad * 2, h + pad * 2))


def rect_glow(w, h, color, pad=26):
    s = pygame.Surface(((w + pad * 2) // 4, (h + pad * 2) // 4))
    pygame.draw.rect(s, tuple(int(v * 0.8) for v in color),
                     (pad // 4, pad // 4, w // 4, h // 4), border_radius=6)
    return pygame.transform.smoothscale(s, (w + pad * 2, h + pad * 2))


def grad_text(text, font, top, bottom, outline=(14, 8, 30), op=4):
    base = font.render(text, True, (255, 255, 255))
    w, h = base.get_size()
    out = pygame.Surface((w + op * 2 + 8, h + op * 2 + 8), pygame.SRCALPHA)
    ol = font.render(text, True, outline)
    for dx in range(-op, op + 1):
        for dy in range(-op, op + 1):
            if dx * dx + dy * dy <= op * op:
                out.blit(ol, (op + 4 + dx, op + 4 + dy))
    base.blit(vgrad(w, h, top, bottom), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(base, (op + 4, op + 4))
    return out


# ------------------------------------------------------------------ car sprite
def make_car(kind, color, cargo=(222, 226, 234)):
    """Glossy top-down car, supersampled 3x for smooth edges. Front is at the top."""
    w, h = CAR_SIZES[kind]
    S = 3
    big = pygame.Surface((w * S, h * S), pygame.SRCALPHA)

    def rect(x, y, ww, hh, c, r=0):
        if ww > 0 and hh > 0:
            pygame.draw.rect(big, c, (int(x * S), int(y * S), int(ww * S), int(hh * S)),
                             border_radius=max(0, int(r * S)))

    def over(x, y, ww, hh, rgba, r=0):
        t = pygame.Surface((int(ww * S), int(hh * S)), pygame.SRCALPHA)
        pygame.draw.rect(t, rgba, t.get_rect(), border_radius=max(0, int(r * S)))
        big.blit(t, (int(x * S), int(y * S)))

    def shaded(x, y, ww, hh, c, r, layers=6, inset=2.0, dk=45, lt=40):
        for i in range(layers):
            col = lerp_c(darken(c, dk), lighten(c, lt), i / (layers - 1))
            rect(x + i * inset, y + i * inset * 0.6, ww - 2 * i * inset, hh - 2 * i * inset * 0.6,
                 col, r - i * inset * 0.7)

    ys = [h * 0.14, h * 0.70] if kind != "truck" else [h * 0.06, h * 0.60, h * 0.80]
    for wy in ys:
        rect(0, wy, 10, 26, (12, 12, 16), 3)
        rect(w - 10, wy, 10, 26, (12, 12, 16), 3)
        rect(1, wy + 5, 3, 16, (70, 70, 78), 1)
        rect(w - 4, wy + 5, 3, 16, (70, 70, 78), 1)
    bx, bw = 6, w - 12
    glass, glass2 = (16, 20, 32), (72, 124, 176)

    if kind == "truck":
        ch = h * 0.28
        shaded(bx, 0, bw, ch, color, 14, 5, 2.0)
        rect(bx + 6, h * 0.09, bw - 12, h * 0.07, glass, 6)
        rect(bx + 8, h * 0.10, bw - 16, h * 0.04, glass2, 4)
        shaded(bx - 1, ch + 4, bw + 2, h - ch - 4, cargo, 6, 5, 2.2, 40, 18)
        for i in range(1, 9):
            rect(bx + 4, ch + 4 + i * (h - ch - 4) / 9, bw - 6, 1.3, darken(cargo, 55))
        rect(bx + 3, 3, 12, 8, (255, 248, 210), 3)
        rect(w - bx - 15, 3, 12, 8, (255, 248, 210), 3)
        rect(bx + 2, h - 7, 14, 5, (255, 50, 50), 2)
        rect(w - bx - 16, h - 7, 14, 5, (255, 50, 50), 2)
    else:
        shaded(bx, 0, bw, h, color, 20, 7, 2.2, 55, 45)
        wy, wh = h * 0.27, h * 0.15
        rect(bx + 5, wy, bw - 10, wh, glass, 8)
        rect(bx + 7, wy + 2, bw - 14, wh - 5, glass2, 6)
        over(bx + 9, wy + 3, 9, wh - 8, (230, 245, 255, 90), 3)
        shaded(bx + 5, h * 0.44, bw - 10, h * 0.22, lerp_c(color, (20, 20, 30), 0.12), 8, 4, 1.5, 25, 25)
        rect(bx + 5, h * 0.68, bw - 10, h * 0.08, glass, 6)
        rect(bx + 7, h * 0.69, bw - 14, h * 0.05, (50, 92, 132), 4)
        rect(bx - 4, wy + 4, 6, 8, darken(color, 45), 2)
        rect(w - bx - 2, wy + 4, 6, 8, darken(color, 45), 2)
        rect(bx + 3, 2, 12, 9, (255, 248, 210), 4)
        rect(w - bx - 15, 2, 12, 9, (255, 248, 210), 4)
        rect(bx + 3, h - 7, 13, 5, (255, 50, 50), 2)
        rect(w - bx - 16, h - 7, 13, 5, (255, 50, 50), 2)
        if kind == "sport":
            for sx in (w / 2 - 5, w / 2 + 1.5):
                rect(sx, 3, 3.5, wy - 4, (245, 245, 250), 1)
                rect(sx, h * 0.44, 3.5, h * 0.22, (245, 245, 250), 1)
                rect(sx, h * 0.77, 3.5, h * 0.12, (245, 245, 250), 1)
            rect(bx - 3, h - 15, bw + 6, 8, darken(color, 75), 2)
            rect(bx - 3, h - 15, bw + 6, 3, lighten(color, 20), 1)
        if kind == "taxi":
            rect(w / 2 - 10, h * 0.50, 20, 8, (250, 250, 225), 2)
            rect(w / 2 - 6, h * 0.52, 12, 3, (30, 30, 30), 1)
    return pygame.transform.smoothscale(big, (w, h))


# --------------------------------------------------------------- scenery sprites
def make_tree(r, base, seed):
    S, size = 2, r * 2 + 34
    big = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
    cx = cy = size * S // 2
    sh = soft_shadow(int(r * 1.9), int(r * 1.9), 100, 16, r)
    sh = pygame.transform.scale(sh, (sh.get_width() * S, sh.get_height() * S))
    big.blit(sh, (cx - sh.get_width() // 2 + 9 * S, cy - sh.get_height() // 2 + 11 * S))
    rng = random.Random(seed)
    pygame.draw.circle(big, darken(base, 30), (cx, cy), r * S)
    blobs = []
    for _ in range(10):
        a, d = rng.uniform(0, math.tau), rng.uniform(0, r * 0.55)
        blobs.append((cx + math.cos(a) * d * S, cy + math.sin(a) * d * S, rng.uniform(.38, .62) * r * S))
    blobs.sort(key=lambda b: -(b[0] + b[1]))
    for bx, by, br in blobs:
        t = clamp(1 - ((bx + by) - 2 * cx + r * S) / (2.2 * r * S), 0, 1)
        col = lerp_c(darken(base, 14), lighten(base, 42), t)
        pygame.draw.circle(big, col, (int(bx), int(by)), int(br))
        pygame.draw.circle(big, lighten(col, 22), (int(bx - br * .3), int(by - br * .3)), int(br * .45))
    return pygame.transform.smoothscale(big, (size, size))


def make_pine(r, base):
    S, size = 2, r * 2 + 34
    big = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
    cx = cy = size * S // 2
    sh = soft_shadow(int(r * 1.8), int(r * 1.8), 100, 16, r)
    sh = pygame.transform.scale(sh, (sh.get_width() * S, sh.get_height() * S))
    big.blit(sh, (cx - sh.get_width() // 2 + 9 * S, cy - sh.get_height() // 2 + 11 * S))
    for k in range(5):
        rr = r * (1 - k * 0.18) * S
        pts = []
        for i in range(16):
            a = math.tau * i / 16 + k * 0.2
            d = rr if i % 2 == 0 else rr * 0.55
            pts.append((cx + math.cos(a) * d, cy + math.sin(a) * d))
        pygame.draw.polygon(big, lerp_c(darken(base, 25), lighten(base, 38), k / 4), pts)
    return pygame.transform.smoothscale(big, (size, size))


def make_bush(seed):
    rng = random.Random(seed)
    S, size = 2, 74
    big = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
    c = size * S // 2
    sh = soft_shadow(34, 34, 90, 14, 16)
    sh = pygame.transform.scale(sh, (sh.get_width() * S, sh.get_height() * S))
    big.blit(sh, (c - sh.get_width() // 2 + 6 * S, c - sh.get_height() // 2 + 8 * S))
    green = rng.choice([(40, 130, 62), (52, 146, 72), (34, 112, 58)])
    for _ in range(6):
        x, y = c + rng.randint(-14, 14) * S, c + rng.randint(-14, 14) * S
        rr = rng.randint(11, 16) * S
        pygame.draw.circle(big, darken(green, 15), (x, y), rr)
        pygame.draw.circle(big, lighten(green, 24), (x - 3 * S, y - 3 * S), int(rr * .7))
    if rng.random() < 0.6:
        fc = rng.choice([(255, 90, 120), (255, 220, 70), (255, 255, 255)])
        for _ in range(7):
            pygame.draw.circle(big, fc, (c + rng.randint(-18, 18) * S, c + rng.randint(-18, 18) * S), 2 * S)
    return pygame.transform.smoothscale(big, (size, size))


def make_rock(seed):
    rng = random.Random(seed)
    s = pygame.Surface((56, 56), pygame.SRCALPHA)
    s.blit(soft_shadow(26, 20, 100, 10, 10), (4, 8))
    for i in range(3):
        x, y, rw, rh = 14 + i * 6, 16 + rng.randint(-4, 4), rng.randint(16, 22), rng.randint(12, 18)
        pygame.draw.ellipse(s, (96, 98, 106), (x, y, rw, rh))
        pygame.draw.ellipse(s, (138, 140, 150), (x + 2, y + 1, rw - 6, rh - 6))
    return s


def make_house(seed, roof):
    rng = random.Random(seed)
    w, h = rng.choice([(86, 104), (96, 84), (78, 96)])
    pad = 22
    s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    s.blit(soft_shadow(w, h, 120, pad, 4), (9, 11))
    x, y, half = pad, pad, w // 2
    pygame.draw.rect(s, darken(roof, 75), (x - 2, y - 2, w + 4, h + 4), border_radius=3)
    pygame.draw.rect(s, roof, (x, y, half, h))
    pygame.draw.rect(s, darken(roof, 38), (x + half, y, w - half, h))
    for ty in range(y + 7, y + h, 9):
        pygame.draw.line(s, darken(roof, 22), (x, ty), (x + half - 1, ty))
        pygame.draw.line(s, darken(roof, 60), (x + half, ty), (x + w - 1, ty))
    pygame.draw.line(s, lighten(roof, 40), (x + half, y), (x + half, y + h), 3)
    pygame.draw.rect(s, (60, 55, 52), (x + int(w * .68), y + int(h * .2), 13, 13))
    pygame.draw.rect(s, (125, 115, 108), (x + int(w * .68) + 2, y + int(h * .2) + 2, 9, 9))
    return s


# ---------------------------------------------------------------- misc sprites
def make_coin_frames():
    frames, S, R, size = [], 3, 15, 36
    for i in range(12):
        w = max(3.0, abs(math.cos(i / 12 * math.tau)) * R)
        big = pygame.Surface((size * S, size * S), pygame.SRCALPHA)
        c = size * S // 2

        def ell(ww, hh, col):
            pygame.draw.ellipse(big, col, (int(c - ww * S), int(c - hh * S), int(ww * 2 * S), int(hh * 2 * S)))
        ell(w + 1, R + 1, (150, 95, 0))
        ell(w, R, (255, 196, 30))
        ell(max(1, w * .72), R * .78, (255, 226, 96))
        ell(max(1, w * .5), R * .55, (255, 196, 40))
        if w > 7:
            pygame.draw.rect(big, (205, 135, 0), (c - int(w * .12 * S), c - int(R * .4 * S),
                                                  int(w * .24 * S), int(R * .8 * S)), border_radius=S * 2)
        frames.append(pygame.transform.smoothscale(big, (size, size)))
    return frames


def make_heart(col, shine):
    S = 4
    big = pygame.Surface((30 * S, 28 * S), pygame.SRCALPHA)
    pygame.draw.circle(big, col, (int(9.5 * S), int(9.5 * S)), 8 * S)
    pygame.draw.circle(big, col, (int(20.5 * S), int(9.5 * S)), 8 * S)
    pygame.draw.polygon(big, col, [(int(2.2 * S), 12 * S), (int(27.8 * S), 12 * S), (15 * S, 26 * S)])
    if shine:
        pygame.draw.circle(big, lighten(col, 70), (int(8 * S), int(7 * S)), int(2.6 * S))
    return pygame.transform.smoothscale(big, (30, 28))


def make_shield_icon():
    s = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.circle(s, (20, 70, 100, 170), (28, 28), 26)
    pygame.draw.circle(s, (120, 225, 255), (28, 28), 26, 3)
    pts = [(28, 11), (43, 17), (41, 34), (28, 46), (15, 34), (13, 17)]
    pygame.draw.polygon(s, (70, 200, 255), pts)
    pygame.draw.polygon(s, (215, 248, 255), pts, 3)
    pygame.draw.polygon(s, (170, 235, 255), [(28, 16), (37, 20), (28, 40), (19, 20)])
    return s


def make_beam(bw=150, bh=340):
    s = pygame.Surface((bw, bh))
    cx = bw // 2
    for y in range(bh):
        d = 1 - y / (bh - 1)
        hw = 10 + d * 62
        base = (1 - d) ** 1.2 * 0.85
        for x in range(int(cx - hw), int(cx + hw) + 1):
            e = abs(x - cx) / hw
            if e < 1:
                v = base * (1 - e * e) ** 1.5
                s.set_at((x, y), (int(255 * v), int(245 * v), int(205 * v)))
    return s


def make_grass():
    s = pygame.Surface((W, 256))
    for i, y in enumerate(range(0, 256, 64)):
        pygame.draw.rect(s, (52, 142, 84) if i % 2 == 0 else (47, 134, 78), (0, y, W, 64))
    rng = random.Random(5)
    for _ in range(2600):
        x, y = rng.randrange(W), rng.randrange(256)
        c = rng.choice([(40, 120, 70), (64, 160, 96), (58, 150, 90), (36, 112, 66)])
        pygame.draw.line(s, c, (x, y), (x + rng.choice((-1, 0, 1)), y + rng.randint(2, 5)))
    return s


def make_road():
    s = pygame.Surface((ROAD_W, 256))
    s.fill((56, 58, 68))
    rng = random.Random(9)
    for _ in range(5500):
        v = rng.randint(-16, 16)
        pygame.draw.rect(s, (56 + v, 58 + v, 68 + v), (rng.randrange(ROAD_W), rng.randrange(256), 2, 2))
    ov = pygame.Surface((ROAD_W, 256), pygame.SRCALPHA)
    for i in range(LANES):
        for off in (-26, 26):
            pygame.draw.rect(ov, (0, 0, 0, 34), (i * LANE_W + LANE_W // 2 + off - 8, 0, 16, 256))
    for _ in range(7):
        x, y = rng.randrange(ROAD_W), rng.randrange(20, 220)
        pts = [(x, y)]
        for _ in range(5):
            x += rng.randint(-8, 8)
            y += rng.randint(6, 14)
            pts.append((x, y))
        pygame.draw.lines(ov, (30, 32, 40, 150), False, pts, 1)
    s.blit(ov, (0, 0))
    return s


# ======================================================================= GAME
MENU_TOP = {"menu": 300, "paused": 262, "over": 456, "controls": 618}


def F(size, name="segoeui,helveticaneue,arial,dejavusans", bold=True):
    return pygame.font.SysFont(name, size, bold=bold)


class Game:
    # ------------------------------------------------------------------ setup
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.fullscreen = True
        self.set_display()
        pygame.display.set_caption("TURBO RUSH")
        self.clock = pygame.time.Clock()
        self.canvas = pygame.Surface((W, H)).convert()
        self.lightmap = pygame.Surface((W, H)).convert()
        self.build_assets()
        self.init_sound()
        self.high = self.load_high()
        self.t = 0
        self.scroll = 0.0
        self.menu_night = 0.62
        self.muted = False
        self.demo_cars, self.demo_timer = [], 0
        self.lamp_pts = []
        self.dim_cache, self.panel_cache, self.btn_cache, self.glow_cache = {}, {}, {}, {}
        self.reset()
        self.scenery = [self.new_scenery(random.randint(-120, H + 120)) for _ in range(40)]
        self.game_active = False
        self.state, self.sel = "menu", 0
        self.set_state("menu")

    def set_display(self):
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        try:
            self.screen = pygame.display.set_mode((W, H), flags, vsync=1)
        except Exception:
            try:
                self.screen = pygame.display.set_mode((W, H), flags)
            except Exception:
                self.fullscreen = False
                self.screen = pygame.display.set_mode((W, H))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.set_display()

    def build_assets(self):
        self.f_lbl, self.f_small, self.f_mid = F(15), F(18), F(26)
        self.f_btn, self.f_hud, self.f_big = F(27), F(50), F(76)
        self.f_num = F(190)
        f_title = F(104, "impact,arialblack,franklingothicheavy,arial")
        self.title1 = grad_text("TURBO", f_title, (255, 240, 100), (255, 135, 20))
        self.title2 = grad_text("RUSH", f_title, (255, 255, 255), (255, 70, 95))
        self.player_spr = make_car("sport", (228, 36, 56))
        cars = []
        for col in [(40, 120, 235), (60, 60, 72), (235, 235, 240), (50, 190, 95), (150, 70, 220)]:
            cars.append(("sedan", make_car("sedan", col)))
        for col in [(250, 190, 20), (240, 120, 40), (30, 190, 170), (235, 60, 150)]:
            cars.append(("sport", make_car("sport", col)))
        cars.append(("taxi", make_car("taxi", (255, 205, 20))))
        self.car_sprites = cars
        self.truck_sprites = [("truck", make_car("truck", c, g)) for c, g in
                              [((200, 50, 50), (225, 228, 235)), ((40, 100, 190), (240, 240, 245)),
                               ((60, 140, 80), (210, 190, 150))]]
        self.shadows = {k: soft_shadow(w - 4, h - 4, 120, 18, 18) for k, (w, h) in CAR_SIZES.items()}
        trees = [make_tree(r, b, i) for i, (r, b) in enumerate([
            (26, (38, 128, 66)), (32, (46, 140, 72)), (38, (30, 112, 60)), (30, (70, 150, 60)),
            (34, (52, 132, 90)), (28, (200, 125, 40)), (30, (185, 80, 45))])]
        self.scn = {
            "tree": trees, "pine": [make_pine(r, (24, 96, 62)) for r in (26, 32, 38)],
            "bush": [make_bush(i) for i in range(4)], "rock": [make_rock(i) for i in range(2)],
            "house": [make_house(i, c) for i, c in enumerate([(190, 70, 60), (70, 110, 170), (200, 150, 70), (120, 90, 150)])],
        }
        self.grass, self.road = make_grass().convert(), make_road().convert()
        self.edge_shadow = pygame.Surface((40, H), pygame.SRCALPHA)
        for x in range(40):
            pygame.draw.line(self.edge_shadow, (0, 0, 0, int(105 * (x / 39) ** 1.6)), (x, 0), (x, H))
        self.coin_frames = make_coin_frames()
        self.heart_on, self.heart_off = make_heart((236, 56, 86), True), make_heart((66, 70, 86), False)
        self.shield_icon = make_shield_icon()
        ring = pygame.Surface((118, 176), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (60, 200, 255, 46), ring.get_rect())
        pygame.draw.ellipse(ring, (150, 236, 255, 210), ring.get_rect(), 3)
        self.shield_ring = ring
        self.beam = make_beam()
        self.G = {"red": glow(22, (255, 50, 40), .9), "head": glow(26, (255, 240, 190), .8),
                  "gold": glow(26, (255, 200, 40), .55), "cyan": glow(60, (60, 200, 255), .8),
                  "lamp": glow(150, (255, 214, 140), .95), "car": glow(130, (255, 245, 220), .45)}
        self.pglow = {}
        for kind, (rad, col) in {"fire": (14, (255, 140, 40)), "blue": (14, (80, 180, 255)),
                                 "spark": (7, (255, 230, 150)), "gold": (9, (255, 215, 60))}.items():
            self.pglow[kind] = [glow(rad, col, 1.0 - i * 0.16) for i in range(6)]
        self.smoke = [[self.make_smoke(r, int(150 * (1 - a / 6))) for a in range(6)] for r in (10, 14, 18, 22)]
        # vignette (grey multiplier)
        sm = pygame.Surface((128, 72))
        for x in range(128):
            for y in range(72):
                d = math.hypot((x - 64) / 64, (y - 36) / 36) / 1.414
                v = int(255 - 120 * d ** 2.2)
                sm.set_at((x, y), (v, v, v))
        self.vig = pygame.transform.smoothscale(sm, (W, H)).convert()
        # speedometer dial
        d = pygame.Surface((220, 220), pygame.SRCALPHA)
        pygame.draw.circle(d, (10, 13, 24, 210), (110, 110), 106)
        pygame.draw.circle(d, (255, 255, 255, 70), (110, 110), 106, 2)
        for v in range(0, 301, 10):
            a = math.radians(135 + 270 * v / 300)
            ln = 13 if v % 50 == 0 else 6
            col = (255, 80, 70) if v >= 240 else (225, 230, 245)
            p1 = (110 + math.cos(a) * 98, 110 + math.sin(a) * 98)
            p2 = (110 + math.cos(a) * (98 - ln), 110 + math.sin(a) * (98 - ln))
            pygame.draw.line(d, col, p1, p2, 3 if v % 50 == 0 else 1)
            if v % 50 == 0:
                im = self.f_lbl.render(str(v), True, col)
                d.blit(im, im.get_rect(center=(110 + math.cos(a) * 72, 110 + math.sin(a) * 72)))
        self.dial = d

    @staticmethod
    def make_smoke(r, alpha):
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (95, 95, 102, int(alpha * .35)), (r, r), r)
        pygame.draw.circle(s, (88, 88, 95, int(alpha * .65)), (r, r), int(r * .72))
        pygame.draw.circle(s, (80, 80, 88, alpha), (r, r), int(r * .45))
        return s

    def init_sound(self):
        self.sounds = {}
        info = pygame.mixer.get_init()
        if not info or info[1] != -16:
            return
        rate, _, ch = info

        def synth(parts):
            buf = array.array("h")
            for f, ms, vol, slide, noise, decay in parts:
                n = int(rate * ms / 1000)
                for i in range(n):
                    t = i / rate
                    env = (1 - i / n) ** decay
                    v = math.sin(math.tau * (f * t + 0.5 * slide * t * t)) * (1 - noise) + random.uniform(-1, 1) * noise
                    s = int(32767 * vol * env * v)
                    for _ in range(ch):
                        buf.append(s)
            return pygame.mixer.Sound(buffer=buf.tobytes())
        try:
            self.sounds = {
                "click": synth([(700, 35, .25, 0, 0, 1)]),
                "select": synth([(520, 60, .3, 0, 0, 1), (780, 90, .3, 0, 0, 1)]),
                "coin": synth([(988, 60, .28, 0, 0, 1), (1319, 140, .28, 0, 0, 1.5)]),
                "shield": synth([(440, 80, .3, 900, 0, 1), (880, 160, .3, 0, 0, 1)]),
                "crash": synth([(120, 420, .55, -120, .65, 1.3)]),
                "beep": synth([(660, 120, .3, 0, 0, 1)]),
                "go": synth([(990, 350, .35, 0, 0, 1)]),
            }
        except Exception:
            self.sounds = {}

    def sfx(self, name):
        if not self.muted and name in self.sounds:
            self.sounds[name].play()

    def load_high(self):
        try:
            with open(HS_FILE) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_high(self):
        try:
            with open(HS_FILE, "w") as f:
                f.write(str(self.high))
        except Exception:
            pass

    # ------------------------------------------------------------- game state
    def reset(self):
        self.px, self.py, self.vx = float(lane_x(1)), PLAYER_Y, 0.0
        self.lives, self.invuln, self.shield = 3, 0, 0
        self.base, self.mult = 6.0, 1.0
        self.speed = self.base
        self.distance, self.coins, self.nitro, self.boosting = 0.0, 0, 100.0, False
        self.enemies, self.items, self.particles, self.rings = [], [], [], []
        self.lane_speed = [random.uniform(1.5, 3.6) for _ in range(LANES)]
        self.spawn_timer, self.shake, self.flash = 40, 0, 0
        self.night_v, self.needle = 0.0, 0.0
        self.countdown, self.go_timer, self.over_t, self.new_high = 0, 0, 0, False

    @property
    def score(self):
        return int(self.distance) + self.coins * 10

    def set_state(self, st):
        self.state = st
        items = self.menu_items()
        self.sel = 0
        if st == "menu" and self.game_active:
            self.sel = 1
        for i, it in enumerate(items):
            if i >= self.sel and it[2]:
                self.sel = i
                break
        pygame.mouse.set_visible(st != "play")

    def new_game(self):
        self.reset()
        self.game_active = True
        self.set_state("play")
        self.countdown = 180

    def resume(self):
        if self.game_active:
            self.set_state("play")
            self.countdown = 120

    def pause(self):
        if self.state == "play":
            self.set_state("paused")

    def quit(self):
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------ menus
    def menu_items(self):
        fs = f"FULLSCREEN: {'ON' if self.fullscreen else 'OFF'}"
        if self.state == "menu":
            return [("START GAME", "new", True), ("RESUME", "resume", self.game_active),
                    ("CONTROLS", "controls", True), (fs, "fs", True), ("QUIT", "quit", True)]
        if self.state == "paused":
            return [("RESUME", "resume", True), ("RESTART", "new", True), (fs, "fs", True),
                    ("MAIN MENU", "menu", True)]
        if self.state == "over":
            return [("PLAY AGAIN", "new", True), ("MAIN MENU", "menu", True)] if self.over_t >= 50 else []
        if self.state == "controls":
            return [("BACK", "menu", True)]
        return []

    def layout(self, items):
        top = MENU_TOP.get(self.state, 300)
        return [pygame.Rect(W // 2 - 190, top + i * 68, 380, 58) for i in range(len(items))]

    def do(self, act):
        self.sfx("select")
        if act == "new":
            self.new_game()
        elif act == "resume":
            self.resume()
        elif act == "menu":
            self.set_state("menu")
        elif act == "controls":
            self.set_state("controls")
        elif act == "fs":
            self.toggle_fullscreen()
        elif act == "quit":
            self.quit()

    def move_sel(self, d):
        items = self.menu_items()
        if not items:
            return
        i = self.sel
        for _ in range(len(items)):
            i = (i + d) % len(items)
            if items[i][2]:
                if i != self.sel:
                    self.sfx("click")
                self.sel = i
                return

    def handle_event(self, ev):
        st = self.state
        if ev.type == pygame.QUIT:
            self.quit()
        if ev.type == pygame.WINDOWFOCUSLOST and st == "play":
            self.pause()
        if ev.type == pygame.KEYDOWN:
            k = ev.key
            if k in (pygame.K_F11, pygame.K_f):
                self.toggle_fullscreen()
            elif k == pygame.K_m:
                self.muted = not self.muted
            elif st == "play" and k in (pygame.K_ESCAPE, pygame.K_p):
                self.pause()
            elif st == "paused" and k in (pygame.K_ESCAPE, pygame.K_p):
                self.resume()
            elif st == "controls" and k == pygame.K_ESCAPE:
                self.set_state("menu")
            elif st in ("menu", "paused", "over", "controls"):
                if k in (pygame.K_UP, pygame.K_w):
                    self.move_sel(-1)
                elif k in (pygame.K_DOWN, pygame.K_s):
                    self.move_sel(1)
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    items = self.menu_items()
                    if 0 <= self.sel < len(items) and items[self.sel][2]:
                        self.do(items[self.sel][1])
        if st in ("menu", "paused", "over", "controls") and ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            items = self.menu_items()
            for i, r in enumerate(self.layout(items)):
                if r.collidepoint(ev.pos) and items[i][2]:
                    if ev.type == pygame.MOUSEMOTION:
                        if self.sel != i:
                            self.sfx("click")
                        self.sel = i
                    elif ev.button == 1:
                        self.sel = i
                        self.do(items[i][1])
                    break

    # ----------------------------------------------------------------- update
    def new_scenery(self, y):
        r = random.random()
        kind = "tree" if r < .46 else "pine" if r < .68 else "bush" if r < .86 else "rock" if r < .92 else "house"
        spr = random.choice(self.scn[kind])
        hw = spr.get_width() // 2
        if random.random() < 0.5:
            x = random.randint(hw + 8, max(hw + 9, EDGE_L - 52 - hw))
        else:
            x = random.randint(min(W - hw - 9, EDGE_R + 52 + hw), W - hw - 8)
        return {"x": x, "y": y, "spr": spr}

    def move_scenery(self, dy):
        for it in self.scenery:
            it["y"] += dy
            if it["y"] > H + 130:
                it.update(self.new_scenery(-random.randint(130, 260)))

    def pick_car(self):
        if random.random() < 0.17:
            return random.choice(self.truck_sprites)
        return random.choice(self.car_sprites)

    def add_enemy(self, lst, lane, own):
        kind, spr = self.pick_car()
        lst.append({"lane": lane, "x": lane_x(lane), "y": -170.0, "own": own, "kind": kind, "spr": spr})

    def add_p(self, x, y, vx, vy, life, kind, road=False):
        self.particles.append([x, y, vx, vy, life, life, kind, road])

    def crash_fx(self, x, y, big=False):
        n = 2 if big else 1
        for _ in range(40 * n):
            a, v = random.uniform(0, math.tau), random.uniform(1, 9 * n)
            self.add_p(x, y, math.cos(a) * v, math.sin(a) * v, random.randint(18, 40), "spark")
        for _ in range(16 * n):
            a, v = random.uniform(0, math.tau), random.uniform(.5, 5 * n)
            self.add_p(x, y, math.cos(a) * v, math.sin(a) * v, random.randint(16, 30), "fire")
        for _ in range(12 * n):
            a, v = random.uniform(0, math.tau), random.uniform(.3, 3)
            self.add_p(x, y, math.cos(a) * v, math.sin(a) * v, random.randint(40, 75), "smoke", True)
        self.rings.append([x, y, 0])

    def update_particles(self):
        sp = self.speed if self.state == "play" else 0
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3] + (sp if p[7] else 0)
            if p[6] == "smoke":
                p[2] *= .97
                p[3] *= .97
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for r in self.rings:
            r[2] += 1
        self.rings = [r for r in self.rings if r[2] < 22]

    def update(self):
        self.t += 1
        st = self.state
        if st in ("menu", "controls"):
            self.scroll += 6
            self.move_scenery(6)
            self.demo_timer -= 1
            if self.demo_timer <= 0:
                lane = random.randrange(LANES)
                if not any(e["lane"] == lane and e["y"] < 300 for e in self.demo_cars):
                    self.add_enemy(self.demo_cars, lane, random.uniform(1.0, 3.0))
                self.demo_timer = random.randint(22, 50)
            for e in self.demo_cars:
                e["y"] += 6 - e["own"]
            self.demo_cars = [e for e in self.demo_cars if e["y"] < H + 220]
        elif st == "play":
            if self.countdown > 0:
                if self.countdown % 60 == 0:
                    self.sfx("beep")
                self.countdown -= 1
                if self.countdown == 0:
                    self.sfx("go")
                    self.go_timer = 45
                return
            self.go_timer = max(0, self.go_timer - 1)
            self.update_play()
        elif st == "over":
            self.over_t += 1
            self.update_particles()
            self.shake = max(0, self.shake - 1)
            self.flash = max(0, self.flash - 1)

    def spawn(self):
        blocked = {e["lane"] for e in self.enemies if e["y"] < 330}
        if len(blocked) >= LANES - 1:
            return
        free = [i for i in range(LANES) if i not in blocked]
        lane = random.choice(free)
        self.add_enemy(self.enemies, lane, self.lane_speed[lane])
        others = [i for i in free if i != lane]
        if others and random.random() < 0.6:
            cl = random.choice(others)
            if random.random() < 0.07 and self.shield == 0 and not any(i["type"] == "shield" for i in self.items):
                self.items.append({"type": "shield", "x": lane_x(cl), "y": -60.0})
            else:
                for k in range(random.randint(1, 5)):
                    self.items.append({"type": "coin", "x": lane_x(cl), "y": -50.0 - k * 62})

    def update_play(self):
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if left and not right:
            self.vx -= 1.0
        elif right and not left:
            self.vx += 1.0
        else:
            self.vx *= 0.82
        self.vx = clamp(self.vx, -8.5, 8.5)
        self.px += self.vx
        lo, hi = EDGE_L + 34, EDGE_R - 34
        if self.px < lo or self.px > hi:
            self.px, self.vx = clamp(self.px, lo, hi), 0

        want = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]
        self.boosting = bool(want and self.nitro > 0.5)
        self.nitro = max(0, self.nitro - 0.6) if self.boosting else min(100, self.nitro + 0.13)
        self.mult += ((1.5 if self.boosting else 1.0) - self.mult) * 0.07
        self.base = min(15.0, self.base + 0.002)
        self.speed = self.base * self.mult
        self.scroll += self.speed
        self.distance += self.speed * 0.06
        night = (math.sin(self.distance / 420.0 - 1.2) + 1) / 2
        self.night_v = clamp((night - 0.42) / 0.45, 0, 1)
        self.needle += (self.speed * 13 - self.needle) * 0.12
        self.move_scenery(self.speed)

        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn()
            self.spawn_timer = max(30, int(random.randint(55, 95) - self.speed * 2.4))

        pr = pygame.Rect(0, 0, 46, 102)
        pr.center = (int(self.px), int(self.py))
        for e in self.enemies[:]:
            e["y"] += self.speed - e["own"]
            if e["y"] > H + 240:
                self.enemies.remove(e)
                continue
            hw, hh = HIT[e["kind"]]
            er = pygame.Rect(0, 0, hw, hh)
            er.center = (int(e["x"]), int(e["y"]))
            if pr.colliderect(er):
                if self.shield > 0:
                    self.crash_fx(e["x"], e["y"])
                    self.coins += 2
                    self.shake, self.flash = 12, 4
                    self.sfx("crash")
                    self.enemies.remove(e)
                elif self.invuln == 0:
                    self.lives -= 1
                    self.invuln, self.shake, self.flash = 120, 26, 8
                    self.crash_fx((e["x"] + self.px) / 2, (e["y"] + self.py) / 2)
                    self.sfx("crash")
                    self.enemies.remove(e)
                    self.vx = 0
                    if self.lives <= 0:
                        self.game_over()
                        return
        for it in self.items[:]:
            it["y"] += self.speed
            if it["y"] > H + 60:
                self.items.remove(it)
            elif abs(it["x"] - self.px) < 36 and abs(it["y"] - self.py) < 60:
                self.items.remove(it)
                if it["type"] == "coin":
                    self.coins += 1
                    self.sfx("coin")
                    for _ in range(10):
                        a, v = random.uniform(0, math.tau), random.uniform(1, 4)
                        self.add_p(it["x"], it["y"], math.cos(a) * v, math.sin(a) * v, 20, "gold")
                else:
                    self.shield = 480
                    self.sfx("shield")
        if self.boosting:
            for dx in (-14, 14):
                self.add_p(self.px + dx, self.py + 62, random.uniform(-.5, .5), random.uniform(3, 6),
                           random.randint(10, 17), "blue")
        self.update_particles()
        self.invuln = max(0, self.invuln - 1)
        self.shield = max(0, self.shield - 1)
        self.shake = max(0, self.shake - 1)
        self.flash = max(0, self.flash - 1)

    def game_over(self):
        self.state = "over"
        self.sel = 0
        self.game_active = False
        self.over_t = 0
        self.shake, self.flash = 34, 12
        self.crash_fx(self.px, self.py, True)
        self.new_high = self.score > self.high
        if self.new_high:
            self.high = self.score
            self.save_high()
        pygame.mouse.set_visible(True)

    # ---------------------------------------------------------------- helpers
    def txt(self, s, font, color, pos, anchor="topleft", shadow=True):
        img = font.render(s, True, color)
        r = img.get_rect(**{anchor: pos})
        if shadow:
            sh = font.render(s, True, (0, 0, 0))
            sh.set_alpha(150)
            self.canvas.blit(sh, (r.x + 2, r.y + 2))
        self.canvas.blit(img, r)
        return r

    def dim(self, color, alpha):
        key = (color, alpha)
        if key not in self.dim_cache:
            s = pygame.Surface((W, H), pygame.SRCALPHA)
            s.fill((*color, alpha))
            self.dim_cache[key] = s
        self.canvas.blit(self.dim_cache[key], (0, 0))

    def panel(self, rect, alpha=165, radius=20, border=(255, 255, 255, 55)):
        key = (rect.w, rect.h, alpha, radius, border)
        if key not in self.panel_cache:
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (10, 13, 26, alpha), s.get_rect(), border_radius=radius)
            pygame.draw.rect(s, border, s.get_rect(), 2, border_radius=radius)
            self.panel_cache[key] = s
        self.canvas.blit(self.panel_cache[key], rect.topleft)

    def add(self, spr, x, y, surf=None):
        (surf or self.canvas).blit(spr, (int(x - spr.get_width() // 2), int(y - spr.get_height() // 2)),
                                   special_flags=pygame.BLEND_RGB_ADD)

    def draw_car(self, spr, kind, x, y, tilt=0.0):
        sh = self.shadows[kind]
        if tilt:
            sh, spr = pygame.transform.rotate(sh, tilt), pygame.transform.rotate(spr, tilt)
        self.canvas.blit(sh, sh.get_rect(center=(x + 8, y + 11)))
        self.canvas.blit(spr, spr.get_rect(center=(x, y)))

    def bar(self, x, y, w, h, frac, c1, c2):
        c = self.canvas
        pygame.draw.rect(c, (18, 22, 36), (x, y, w, h), border_radius=h // 2)
        fw = int(w * clamp(frac, 0, 1))
        if fw > h:
            c.blit(vgrad(fw, h, c1, c2, h // 2), (x, y))
        elif fw > 0:
            pygame.draw.rect(c, c2, (x, y, fw, h), border_radius=h // 2)
        pygame.draw.rect(c, (90, 100, 132), (x, y, w, h), 2, border_radius=h // 2)

    # ------------------------------------------------------------------ scene
    def draw_scene(self, demo):
        c, sc = self.canvas, self.scroll
        y0 = int(sc) % 256
        for y in range(y0 - 256, H, 256):
            c.blit(self.grass, (0, y))
            c.blit(self.road, (EDGE_L, y))
        if not hasattr(self, "edge_r"):
            self.edge_r = pygame.transform.flip(self.edge_shadow, True, False)
        c.blit(self.edge_shadow, (EDGE_L - 54, 0))
        c.blit(self.edge_r, (EDGE_R + 14, 0))
        P = 40
        base, idx = int(sc % P), int(sc // P)
        for k in range(-1, H // P + 2):
            col = (214, 48, 52) if (k - idx) % 2 == 0 else (240, 240, 244)
            pygame.draw.rect(c, col, (EDGE_L - 14, base + k * P, 14, P))
            pygame.draw.rect(c, col, (EDGE_R, base + k * P, 14, P))
        pygame.draw.rect(c, (236, 238, 244), (EDGE_L + 8, 0, 3, H))
        pygame.draw.rect(c, (236, 238, 244), (EDGE_R - 11, 0, 3, H))
        pygame.draw.rect(c, (240, 196, 40), (EDGE_L + 2 * LANE_W - 5, 0, 3, H))
        pygame.draw.rect(c, (240, 196, 40), (EDGE_L + 2 * LANE_W + 2, 0, 3, H))
        base = int(sc % 90)
        for i in (1, 3):
            for k in range(-1, H // 90 + 2):
                pygame.draw.rect(c, (228, 231, 238), (EDGE_L + i * LANE_W - 2, base + k * 90, 4, 52), border_radius=2)
        for it in self.scenery:
            if -150 < it["y"] < H + 150:
                s = it["spr"]
                c.blit(s, (it["x"] - s.get_width() // 2, int(it["y"]) - s.get_height() // 2))
        self.lamp_pts = []
        base = int(sc % 300)
        for k in range(-1, H // 300 + 2):
            y = base + k * 300
            for side in (-1, 1):
                px = EDGE_L - 46 if side < 0 else EDGE_R + 46
                hx = px - side * 28
                pygame.draw.line(c, (46, 50, 60), (px, y), (hx, y), 4)
                pygame.draw.circle(c, (40, 44, 52), (px, y), 6)
                pygame.draw.circle(c, (255, 246, 205), (hx, y), 7)
                self.lamp_pts.append((hx, y))
        if demo:
            for e in self.demo_cars:
                self.draw_car(e["spr"], e["kind"], e["x"], e["y"])
        else:
            for it in self.items:
                if it["type"] == "coin":
                    f = self.coin_frames[(self.t // 3 + int(it["y"] // 25)) % 12]
                    c.blit(f, f.get_rect(center=(it["x"], int(it["y"]))))
                else:
                    c.blit(self.shield_icon, self.shield_icon.get_rect(
                        center=(it["x"], int(it["y"] + math.sin(self.t * .1) * 4))))
            for e in self.enemies:
                self.draw_car(e["spr"], e["kind"], e["x"], e["y"])
            if self.state in ("play", "paused") and not (self.invuln and (self.invuln // 5) % 2):
                self.draw_car(self.player_spr, "sport", self.px, self.py, -self.vx * 2.4)
                if self.shield > 0 and (self.shield > 120 or (self.shield // 6) % 2 == 0):
                    c.blit(self.shield_ring, self.shield_ring.get_rect(center=(int(self.px), int(self.py))))
        for p in self.particles:
            if p[6] == "smoke":
                age = 1 - p[4] / p[5]
                s = self.smoke[min(3, int(age * 4))][min(5, int(age * 6))]
                c.blit(s, s.get_rect(center=(int(p[0]), int(p[1]))))
        if self.state == "play" and self.mult > 1.2:
            for _ in range(10):
                x, y = random.randint(EDGE_L, EDGE_R), random.randint(0, H)
                pygame.draw.line(c, (150, 165, 205), (x, y), (x, y + random.randint(40, 110)), 1)

    def apply_light(self, demo):
        c, lm = self.canvas, self.lightmap
        nv = self.menu_night if demo else self.night_v
        lm.blit(self.vig, (0, 0))
        if nv > 0.01:
            lm.fill(lerp_c((255, 255, 255), (46, 58, 106), nv), special_flags=pygame.BLEND_RGB_MULT)
            if nv > 0.12:
                bw, bh = self.beam.get_size()
                for x, y in self.lamp_pts:
                    self.add(self.G["lamp"], x, y, lm)
                cars = self.demo_cars if demo else self.enemies
                for e in cars:
                    self.add(self.G["car"], e["x"], e["y"], lm)
                    lm.blit(self.beam, (int(e["x"] - bw // 2), int(e["y"] - CAR_SIZES[e["kind"]][1] // 2 - bh + 10)),
                            special_flags=pygame.BLEND_RGB_ADD)
                if not demo and self.state in ("play", "paused"):
                    self.add(self.G["car"], self.px, self.py, lm)
                    for dx in (-14, 14):
                        lm.blit(self.beam, (int(self.px + dx - bw // 2), int(self.py - 62 - bh + 10)),
                                special_flags=pygame.BLEND_RGB_ADD)
        c.blit(lm, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def draw_emissive(self, demo):
        c = self.canvas
        cars = self.demo_cars if demo else self.enemies
        for e in cars:
            w, h = CAR_SIZES[e["kind"]]
            for dx in (-(w / 2 - 14), w / 2 - 14):
                self.add(self.G["red"], e["x"] + dx, e["y"] + h / 2 - 6)
        if not demo:
            for it in self.items:
                self.add(self.G["gold"] if it["type"] == "coin" else self.G["cyan"], it["x"], it["y"])
            if self.state in ("play", "paused"):
                for dx in (-17, 17):
                    self.add(self.G["red"], self.px + dx, self.py + 57)
                    self.add(self.G["head"], self.px + dx, self.py - 56)
                if self.shield > 0:
                    self.add(self.G["cyan"], self.px, self.py)
        for p in self.particles:
            if p[6] != "smoke":
                self.add(self.pglow[p[6]][min(5, int((1 - p[4] / p[5]) * 6))], p[0], p[1])
        for r in self.rings:
            rad = 20 + r[2] * 9
            s = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 230, 170, int(210 * (1 - r[2] / 22))), (rad + 4, rad + 4), rad, 4)
            c.blit(s, s.get_rect(center=(int(r[0]), int(r[1]))))
        if self.flash > 0:
            self.dim((255, 255, 255), min(170, self.flash * 14))

    # -------------------------------------------------------------------- HUD
    def draw_hud(self):
        c = self.canvas
        self.panel(pygame.Rect(24, 24, 310, 188))
        self.txt("SCORE", self.f_lbl, (150, 165, 200), (46, 38))
        self.txt(f"{self.score:,}", self.f_hud, (255, 255, 255), (46, 52))
        self.txt("BEST", self.f_lbl, (150, 165, 200), (46, 124))
        self.txt(f"{self.high:,}", self.f_small, (255, 214, 10), (96, 120))
        for i in range(3):
            c.blit(self.heart_on if i < self.lives else self.heart_off, (46 + i * 38, 152))
        c.blit(self.coin_frames[0], (196, 148))
        self.txt(f"x {self.coins}", self.f_mid, (255, 214, 10), (238, 150))
        self.panel(pygame.Rect(24, H - 130, 310, 106))
        self.txt("NITRO", self.f_lbl, (150, 165, 200), (46, H - 118))
        if self.boosting:
            self.bar(46, H - 98, 266, 16, self.nitro / 100, (255, 200, 70), (255, 110, 30))
        else:
            self.bar(46, H - 98, 266, 16, self.nitro / 100, (110, 225, 255), (40, 130, 255))
        self.txt("SHIELD", self.f_lbl, (150, 165, 200), (46, H - 72))
        self.bar(46, H - 50, 266, 12, self.shield / 480, (130, 240, 255), (40, 170, 230))
        cx, cy = W - 130, H - 130
        c.blit(self.dial, (cx - 110, cy - 110))
        a = math.radians(135 + 270 * clamp(self.needle / 300, 0, 1))
        pygame.draw.line(c, (255, 90, 60), (cx - math.cos(a) * 14, cy - math.sin(a) * 14),
                         (cx + math.cos(a) * 80, cy + math.sin(a) * 80), 4)
        pygame.draw.circle(c, (230, 235, 245), (cx, cy), 8)
        pygame.draw.circle(c, (255, 90, 60), (cx, cy), 4)
        self.txt(str(int(self.needle)), self.f_mid, (255, 255, 255), (cx, cy + 40), "center")
        self.txt("km/h", self.f_lbl, (150, 165, 200), (cx, cy + 62), "center")
        self.txt("ESC pause   |   F11 fullscreen   |   M sound", self.f_lbl, (175, 185, 210),
                 (W - 24, 28), "topright")

    # ---------------------------------------------------------------- overlays
    def get_button(self, w, h, mode):
        key = (w, h, mode)
        if key not in self.btn_cache:
            top, bot, brd = {"sel": ((255, 208, 72), (255, 126, 30), (255, 245, 210)),
                             "norm": ((52, 62, 96), (28, 33, 56), (112, 124, 172)),
                             "dis": ((36, 38, 50), (30, 32, 42), (60, 64, 80))}[mode]
            s = vgrad(w, h, top, bot, 14)
            pygame.draw.rect(s, brd, s.get_rect(), 2, border_radius=14)
            pygame.draw.rect(s, (255, 255, 255, 26), (8, 3, w - 16, h // 3), border_radius=10)
            self.btn_cache[key] = s
        return self.btn_cache[key]

    def draw_buttons(self, items):
        for i, ((label, act, en), r) in enumerate(zip(items, self.layout(items))):
            selected = i == self.sel and en
            rr = r.inflate(22, 8) if selected else r
            if selected:
                key = (rr.w, rr.h)
                if key not in self.glow_cache:
                    self.glow_cache[key] = rect_glow(rr.w, rr.h, (255, 150, 40))
                g = self.glow_cache[key]
                self.canvas.blit(g, g.get_rect(center=rr.center), special_flags=pygame.BLEND_RGB_ADD)
            self.canvas.blit(self.get_button(rr.w, rr.h, "sel" if selected else ("norm" if en else "dis")), rr.topleft)
            col = (40, 24, 6) if selected else ((228, 233, 247) if en else (115, 120, 138))
            self.txt(label, self.f_btn, col, rr.center, "center", shadow=(not selected and en))

    def draw_keys(self, keys, x, y):
        for k in keys:
            if k == "/":
                self.txt("/", self.f_mid, (150, 160, 190), (x + 4, y + 2))
                x += 22
                continue
            tw = self.f_small.size(k)[0] + 24
            pygame.draw.rect(self.canvas, (22, 26, 44), (x, y + 5, tw, 38), border_radius=9)
            pygame.draw.rect(self.canvas, (72, 80, 118), (x, y, tw, 38), border_radius=9)
            pygame.draw.rect(self.canvas, (150, 162, 205), (x, y, tw, 38), 2, border_radius=9)
            self.txt(k, self.f_small, (240, 244, 255), (x + tw // 2, y + 19), "center", False)
            x += tw + 8

    def draw_overlays(self):
        c, st = self.canvas, self.state
        mid = W // 2
        if st == "menu":
            self.dim((8, 10, 18), 120)
            self.panel(pygame.Rect(mid - 260, 36, 520, 650), 170, 26, (255, 170, 60, 120))
            bob = math.sin(self.t * .05) * 5
            c.blit(self.title1, self.title1.get_rect(center=(mid, 100 + bob)))
            c.blit(self.title2, self.title2.get_rect(center=(mid, 192 + bob)))
            self.txt(f"BEST   {self.high:,}", self.f_mid, (255, 214, 10), (mid, 268), "center")
            self.draw_buttons(self.menu_items())
            self.txt("UP / DOWN + ENTER   or   use the mouse", self.f_lbl, (150, 160, 190), (mid, 662), "center")
        elif st == "controls":
            self.dim((8, 10, 18), 150)
            self.panel(pygame.Rect(mid - 380, 40, 760, 640), 190, 26, (255, 170, 60, 120))
            self.txt("CONTROLS", self.f_big, (255, 214, 10), (mid, 100), "center")
            rows = [(["LEFT", "RIGHT", "/", "A", "D"], "Steer"), (["SPACE", "/", "UP", "/", "W"], "Nitro boost"),
                    (["P", "/", "ESC"], "Pause menu"), (["F11", "/", "F"], "Fullscreen on / off"),
                    (["M"], "Mute sound"), (["ENTER"], "Select in menus")]
            for i, (keys, desc) in enumerate(rows):
                y = 172 + i * 58
                self.draw_keys(keys, mid - 330, y)
                self.txt(desc, self.f_mid, (230, 235, 250), (mid + 90, y + 6))
            self.txt("Dodge traffic, collect coins (+10 points).", self.f_small, (170, 180, 208), (mid, 535), "center")
            self.txt("Grab the SHIELD to smash through cars. Nitro refills when released.", self.f_small,
                     (170, 180, 208), (mid, 563), "center")
            self.draw_buttons(self.menu_items())
        elif st == "paused":
            self.dim((8, 10, 18), 150)
            self.panel(pygame.Rect(mid - 240, 120, 480, 470), 190, 26, (255, 170, 60, 120))
            self.txt("PAUSED", self.f_big, (255, 255, 255), (mid, 190), "center")
            self.draw_buttons(self.menu_items())
        elif st == "over":
            self.dim((8, 10, 18), min(170, self.over_t * 4))
            if self.over_t >= 50:
                self.panel(pygame.Rect(mid - 260, 110, 520, 530), 200, 26, (255, 90, 100, 130))
                self.txt("GAME OVER", self.f_big, (255, 80, 95), (mid, 168), "center")
                self.txt("SCORE", self.f_lbl, (150, 165, 200), (mid, 222), "center")
                self.txt(f"{self.score:,}", self.f_hud, (255, 255, 255), (mid, 262), "center")
                self.txt(f"Coins: {self.coins}      Distance: {int(self.distance)} m", self.f_small,
                         (255, 214, 10), (mid, 318), "center")
                if self.new_high:
                    col = (120, 255, 160) if (self.t // 20) % 2 == 0 else (255, 255, 255)
                    self.txt("NEW HIGH SCORE!", self.f_mid, col, (mid, 380), "center")
                else:
                    self.txt(f"Best: {self.high:,}", self.f_mid, (190, 200, 222), (mid, 380), "center")
                self.draw_buttons(self.menu_items())
        if st == "play" and self.countdown > 0:
            self.dim((8, 10, 18), 70)
            n, frac = (self.countdown + 59) // 60, ((self.countdown - 1) % 60) / 60
            img = grad_text(str(n), self.f_num, (255, 255, 255), (255, 200, 80), op=6)
            sc = 1 + frac * .5
            img = pygame.transform.smoothscale(img, (int(img.get_width() * sc), int(img.get_height() * sc)))
            img.set_alpha(int(255 * (0.45 + 0.55 * (1 - frac))))
            c.blit(img, img.get_rect(center=(mid, H // 2 - 10)))
            self.txt("GET READY", self.f_mid, (255, 255, 255), (mid, H // 2 - 170), "center")
        if st == "play" and self.go_timer > 0:
            img = grad_text("GO!", self.f_big, (190, 255, 190), (40, 200, 90))
            img.set_alpha(int(255 * self.go_timer / 45))
            c.blit(img, img.get_rect(center=(mid, H // 2 - 60)))

    # ------------------------------------------------------------ render / run
    def render(self):
        st = self.state
        demo = st in ("menu", "controls")
        self.draw_scene(demo)
        self.apply_light(demo)
        self.draw_emissive(demo)
        if not demo:
            self.draw_hud()
        self.draw_overlays()
        ox = oy = 0
        if self.shake > 0 and not demo:
            s = self.shake // 3
            ox, oy = random.randint(-s, s), random.randint(-s, s)
            self.screen.fill((0, 0, 0))
        self.screen.blit(self.canvas, (ox, oy))
        pygame.display.flip()

    def run(self):
        while True:
            for ev in pygame.event.get():
                self.handle_event(ev)
            self.update()
            self.render()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()