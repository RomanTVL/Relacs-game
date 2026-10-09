# -*- coding: utf-8 -*-
"""
ЗВЁЗДНЫЙ ШТОРМ — космический рогалик по мотивам режима «Космический шторм» из Relacs.

Управление (по умолчанию):
    WASD / стрелки        — полёт в любую сторону
    Мышь                  — прицел (стрельба автоматическая)
    Пробел / Shift / ПКМ  — рывок (рывок сквозь вражескую пулю — «уклонение»)
    Q / СКМ               — эхо-импульс
    E                     — «Звёздный шторм», когда шкала заполнена
    Esc / P               — пауза
    F12                   — скриншот
В настройках: классическое управление (тяга к курсору, как в «Космическом шторме»),
автоприцел, тряска экрана, цифры урона, громкость, язык.
Геймпад: левый стик — полёт, правый — прицел, A/RB — рывок, X/LB — импульс, Y — шторм, Start — пауза.
"""
import pygame
import random
import math
import os
import sys
import json
import time
import array
import atexit

# === Пути: работает и из .py, и из собранного .exe ===
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
if os.name == "nt":
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "StarStorm")
else:
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".starstorm")
SAVE_PATH = os.path.join(DATA_DIR, "save.json")
SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "StarStorm")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pygame.mixer.quit()
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    pygame.mixer.init()
pygame.mixer.set_num_channels(28)
pygame.joystick.init()

try:
    pygame.display.set_icon(pygame.image.load("star_icon.png"))
except (pygame.error, FileNotFoundError):
    pass
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Звёздный шторм")
pygame.mouse.set_visible(False)
clock = pygame.time.Clock()
UI = HEIGHT / 1080

# === Цвета «Космического шторма» ===
BLACK = (0, 0, 0)
WHITE = (200, 200, 255)
GLOW_BLUE = (70, 100, 200)
FLAME_PARTICLE = (255, 120, 0)
SHOOTING_STAR_COLOR = (255, 255, 200)
SHIP_BLUE = (100, 140, 255)
HUD_TITLE = (100, 200, 255)
HUD_TEXT = (130, 180, 255)
PORTAL_PURPLE = (200, 150, 255)
DANGER = (255, 90, 120)
GOLD = (255, 215, 110)
HEAL_GREEN = (110, 255, 160)
RARITY_COLORS = {"common": (130, 180, 255), "rare": (200, 150, 255), "epic": (255, 200, 90)}

# =====================================================================
#  Сохранение и настройки
# =====================================================================
DEFAULT_SAVE = {
    "language": "ru", "volume": 0.6, "sfx": 0.7, "shards": 0, "meta": {}, "ships": ["wanderer"], "ship": "wanderer",
    "best_sector": 0, "best_kills": 0, "runs": 0, "wins": 0,
    "controls": "wasd", "aim": "mouse", "shake": True, "numbers": True,
}


def load_save():
    data = json.loads(json.dumps(DEFAULT_SAVE))
    try:
        with open(SAVE_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            data.update({k: v for k, v in stored.items() if k in DEFAULT_SAVE})
    except (OSError, ValueError):
        pass
    return data


def write_save():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = SAVE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(SAVE, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SAVE_PATH)
    except OSError as e:
        print(f"Не удалось сохранить: {e}")


SAVE = load_save()
atexit.register(write_save)


def L(ru, en):
    return ru if SAVE["language"] == "ru" else en


def LI():
    return 0 if SAVE["language"] == "ru" else 1


def quit_game():
    write_save()
    pygame.quit()
    sys.exit()


# =====================================================================
#  Графика: шрифты, текст, свечение
# =====================================================================
_fonts = {}
_text_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("consolas", max(10, int(size * UI)), bold=bold)
    return _fonts[key]


def text(s, size, color, bold=False):
    key = (s, size, color, bold)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 2000:
            _text_cache.clear()
        surf = font(size, bold).render(s, True, color)
        _text_cache[key] = surf
    return surf


def blit_text(surf, s, size, color, pos, anchor="topleft", bold=False, alpha=None):
    t = text(s, size, color, bold)
    if alpha is not None and alpha < 255:
        t = t.copy()
        t.set_alpha(max(0, alpha))
    r = t.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surf.blit(t, r)
    return r


def wrap_lines(s, size, max_w):
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font(size).size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


_glow_cache = {}


def glow(radius, color, strength=120):
    radius = max(2, int(radius))
    key = (radius, color, strength)
    surf = _glow_cache.get(key)
    if surf is None:
        if len(_glow_cache) > 600:
            _glow_cache.clear()
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        steps = 14
        for i in range(steps, 0, -1):
            r = int(radius * i / steps)
            k = (1 - i / steps) ** 1.8
            c = tuple(min(255, int(ch * k * strength / 255)) for ch in color)
            pygame.draw.circle(surf, c, (radius, radius), r)
        _glow_cache[key] = surf
    return surf


def draw_glow(surf, pos, radius, color, strength=120):
    g = glow(radius, color, strength)
    surf.blit(g, (pos[0] - g.get_width() // 2, pos[1] - g.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)


def hue_to_rgb(hue):
    h_i = int(hue * 6) % 6
    f = hue * 6 - int(hue * 6)
    p, q, t = 0, 1 - f, f
    return [(1, t, p), (q, 1, p), (p, 1, t), (p, q, 1), (t, p, 1), (1, p, q)][h_i]


def rainbow(phase, k=255):
    r, g, b = hue_to_rgb(phase % 1.0)
    return int(r * k), int(g * k), int(b * k)


def lerp_color(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
    return math.hypot(px - (x1 + dx * t), py - (y1 + dy * t))


def draw_ship(surf, x, y, angle, scale, color, alpha=255):
    """Корабль из «Космического шторма»: острый треугольник."""
    tip = (x + 14 * scale * math.cos(angle), y + 14 * scale * math.sin(angle))
    left = (x + 10 * scale * math.cos(angle + 2.9), y + 10 * scale * math.sin(angle + 2.9))
    right = (x + 10 * scale * math.cos(angle - 2.9), y + 10 * scale * math.sin(angle - 2.9))
    pygame.draw.polygon(surf, (*color, alpha), [tip, left, right])


# =====================================================================
#  Звук: синтезированные эффекты + музыка Relacs
# =====================================================================
def make_sound(duration, volume=0.3, freqs=(440,), decay=10.0, noise=0.0, sweep=0.0):
    try:
        rate = pygame.mixer.get_init()[0]
    except (pygame.error, TypeError):
        return None
    rnd = random.Random(len(freqs) * 7 + int(duration * 1000))
    n = int(rate * duration)
    buf = array.array("h")
    phase = [0.0] * len(freqs)
    for i in range(n):
        t = i / rate
        env = math.exp(-decay * t) * min(1.0, i / (rate * 0.003))
        v = 0.0
        for j, f in enumerate(freqs):
            phase[j] += 2 * math.pi * f * (1 + sweep * t) / rate
            v += math.sin(phase[j])
        v = v / len(freqs) * (1 - noise) + (rnd.uniform(-1, 1) * noise)
        s = int(32767 * volume * env * max(-1, min(1, v)))
        buf.append(s)
        buf.append(s)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except pygame.error:
        return None


SOUNDS = {}


def init_sounds():
    SOUNDS["shot"] = make_sound(0.07, 0.10, (1400, 2100), 45, 0.15, -2.5)
    SOUNDS["hit"] = make_sound(0.05, 0.12, (600,), 60, 0.4)
    SOUNDS["boom"] = make_sound(0.45, 0.35, (90, 60), 9, 0.75, -0.6)
    SOUNDS["pickup"] = make_sound(0.08, 0.10, (1760, 2640), 35)
    SOUNDS["level"] = make_sound(0.7, 0.25, (523, 659, 784, 1046), 5)
    SOUNDS["dash"] = make_sound(0.22, 0.22, (300,), 14, 0.7, 2.0)
    SOUNDS["hurt"] = make_sound(0.3, 0.35, (110, 80), 12, 0.5)
    SOUNDS["pulse"] = make_sound(0.6, 0.35, (70, 140), 6, 0.35, 1.0)
    SOUNDS["click"] = make_sound(0.12, 0.2, (660, 990), 25)
    SOUNDS["portal"] = make_sound(0.5, 0.15, (220, 330, 440), 6, 0.1, 1.5)
    SOUNDS["shield"] = make_sound(0.2, 0.2, (880, 1320), 18, 0.2)
    SOUNDS["missile"] = make_sound(0.25, 0.14, (500, 750), 10, 0.5, 1.5)
    SOUNDS["beam"] = make_sound(0.5, 0.22, (180, 270, 360), 6, 0.25, -0.4)
    SOUNDS["dodge"] = make_sound(0.6, 0.25, (1046, 1568, 2093), 6, 0.0, -0.3)
    SOUNDS["storm"] = make_sound(1.4, 0.3, (130, 196, 261, 392), 2.5, 0.3, 0.5)
    SOUNDS["meteor"] = make_sound(0.7, 0.4, (60, 45), 6, 0.85, -0.5)
    SOUNDS["mine"] = make_sound(0.35, 0.3, (140, 90), 10, 0.7)
    SOUNDS["reflect"] = make_sound(0.1, 0.15, (2400, 3200), 30, 0.1)
    SOUNDS["nav"] = make_sound(0.05, 0.08, (900,), 50)


_last_play = {}


def sfx(name, volume=1.0, throttle=0):
    snd = SOUNDS.get(name)
    if not snd:
        return
    now = pygame.time.get_ticks()
    if throttle and now - _last_play.get(name, -99999) < throttle:
        return
    _last_play[name] = now
    snd.set_volume(min(1.0, volume * SAVE["sfx"]))
    snd.play()


_current_music = [None]


def play_music(track, loops=-1):
    if _current_music[0] == track:
        return
    _current_music[0] = track
    if not os.path.exists(track):
        return
    try:
        pygame.mixer.music.load(track)
        pygame.mixer.music.set_volume(SAVE["volume"] * 0.7)
        pygame.mixer.music.play(loops)
    except pygame.error as e:
        print(f"Музыка не играет: {e}")


def apply_volume():
    pygame.mixer.music.set_volume(SAVE["volume"] * 0.7)


def take_screenshot():
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOT_DIR, time.strftime("starstorm_%Y%m%d_%H%M%S.png"))
        pygame.image.save(screen, path)
    except (OSError, pygame.error) as e:
        print(f"Скриншот не удался: {e}")


# =====================================================================
#  Ввод: клавиатура, мышь, геймпад
# =====================================================================
INPUT = {"pad": False}
JOYSTICKS = []
PAD_BUTTONS = {0: pygame.K_RETURN, 1: pygame.K_BACKSPACE, 2: pygame.K_q, 3: pygame.K_e,
               4: pygame.K_q, 5: pygame.K_SPACE, 6: pygame.K_TAB, 7: pygame.K_ESCAPE}
_stick_menu = {"x": 0, "y": 0}


def refresh_joysticks():
    JOYSTICKS.clear()
    for i in range(pygame.joystick.get_count()):
        try:
            j = pygame.joystick.Joystick(i)
            j.init()
            JOYSTICKS.append(j)
        except pygame.error:
            pass


refresh_joysticks()


def _key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)


def pad_axes():
    """(левый x, левый y, правый x, правый y) с мёртвой зоной."""
    if not JOYSTICKS:
        return 0.0, 0.0, 0.0, 0.0
    j = JOYSTICKS[0]
    n = j.get_numaxes()

    def ax(i):
        if i >= n:
            return 0.0
        v = j.get_axis(i)
        return v if abs(v) > 0.22 else 0.0
    return ax(0), ax(1), ax(2), ax(3)


def get_events():
    events = []
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            quit_game()
        if e.type == pygame.KEYDOWN and e.key == pygame.K_F12:
            take_screenshot()
            continue
        if e.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            refresh_joysticks()
            continue
        if e.type == pygame.JOYBUTTONDOWN:
            INPUT["pad"] = True
            key = PAD_BUTTONS.get(e.button)
            if key:
                events.append(_key_event(key))
            continue
        if e.type == pygame.JOYHATMOTION:
            INPUT["pad"] = True
            hx, hy = e.value
            if hx:
                events.append(_key_event(pygame.K_RIGHT if hx > 0 else pygame.K_LEFT))
            if hy:
                events.append(_key_event(pygame.K_UP if hy > 0 else pygame.K_DOWN))
            continue
        if e.type == pygame.JOYAXISMOTION:
            if e.axis in (0, 1):
                name = "x" if e.axis == 0 else "y"
                if abs(e.value) > 0.6 and _stick_menu[name] == 0:
                    _stick_menu[name] = 1 if e.value > 0 else -1
                    INPUT["pad"] = True
                    if name == "x":
                        events.append(_key_event(pygame.K_RIGHT if e.value > 0 else pygame.K_LEFT))
                    else:
                        events.append(_key_event(pygame.K_DOWN if e.value > 0 else pygame.K_UP))
                elif abs(e.value) < 0.3:
                    _stick_menu[name] = 0
            elif abs(e.value) > 0.4 and e.axis in (2, 3):
                INPUT["pad"] = True
            continue
        if e.type == pygame.MOUSEMOTION:
            INPUT["pad"] = False
        events.append(e)
    return events


def key_dir(e):
    if e.type != pygame.KEYDOWN:
        return None
    return {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}.get(e.key)


def is_confirm(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)


def is_back(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)


def move_vector():
    keys = pygame.key.get_pressed()
    x = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
    y = (1 if (keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0) - (1 if (keys[pygame.K_w] or keys[pygame.K_UP]) else 0)
    lx, ly, _, _ = pad_axes()
    if lx or ly:
        x, y = lx, ly
    mag = math.hypot(x, y)
    if mag > 1:
        x, y = x / mag, y / mag
    return x, y


# =====================================================================
#  Фон из «Космического шторма»: звёзды, пыль, падающие звёзды, сияние,
#  облака снов, порталы, эхо-волны — плюс туманности и планеты
# =====================================================================
class ParallaxStar:
    def __init__(self, layer):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.layer = layer
        self.speed = 0.2 + layer * 0.3
        self.size = 0.7 + layer * 0.8
        self.twinkle_phase = random.uniform(0, 2 * math.pi)
        self.twinkle_speed = 0.0003 + layer * 0.0001
        self.is_wobbling = random.random() < 0.2
        self.wobble_phase = random.uniform(0, 2 * math.pi)
        self.color_phase = random.uniform(0, 2 * math.pi)
        self.flare = layer == 3 and random.random() < 0.3

    def update(self, ship_dx, ship_dy):
        self.x -= ship_dx * self.speed
        self.y -= ship_dy * self.speed
        if self.x < -20: self.x += WIDTH + 40
        if self.x > WIDTH + 20: self.x -= WIDTH + 40
        if self.y < -20: self.y += HEIGHT + 40
        if self.y > HEIGHT + 20: self.y -= HEIGHT + 40

    def draw(self, surface, base_brightness=1.0, dream=False, frozen=False):
        now = pygame.time.get_ticks()
        t = now * self.twinkle_speed + self.twinkle_phase
        alpha = (math.sin(t) + 1) / 2
        brightness = base_brightness * (0.6 + 0.4 * alpha)
        if dream:
            hue = (now * 0.0001 + self.color_phase) % 1.0
            r, g, b = hue_to_rgb(hue)
            color = (int(r * 255 * brightness), int(g * 255 * brightness), int(b * 255 * brightness))
        else:
            color = (min(255, int(WHITE[0] * brightness)), min(255, int(WHITE[1] * brightness)),
                     min(255, int(WHITE[2] * brightness)))
        x, y = self.x, self.y
        if self.is_wobbling and not frozen:
            wobble = 1.5 * math.sin(now * 0.002 + self.wobble_phase)
            x += wobble
            y -= wobble * 0.5
        pygame.draw.circle(surface, color, (int(x), int(y)), self.size)
        if self.flare and alpha > 0.55:
            ln = int(3 + 7 * (alpha - 0.55) / 0.45)
            c2 = (*color, 120)
            pygame.draw.line(surface, c2, (x - ln, y), (x + ln, y))
            pygame.draw.line(surface, c2, (x, y - ln), (x, y + ln))


class DustParticle:
    def __init__(self):
        self.x = random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.size = random.uniform(0.2, 0.5)
        self.speed = 0.1
        self.layer = random.choice([1, 2, 3])

    def update(self, ship_dx, ship_dy):
        self.x += ship_dx * self.speed * self.layer
        self.y += ship_dy * self.speed * self.layer
        if self.x < -10: self.x += WIDTH + 20
        if self.x > WIDTH + 10: self.x -= WIDTH + 20
        if self.y < -10: self.y += HEIGHT + 20
        if self.y > HEIGHT + 10: self.y -= HEIGHT + 20

    def draw(self, surface, dream=False):
        color = (180, 180, 220, 100)
        if dream:
            hue = (pygame.time.get_ticks() * 0.00005 + self.x * 0.0001) % 1.0
            r, g, b = hue_to_rgb(hue)
            color = (int(r * 255), int(g * 255), int(b * 255), 120)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), max(1, self.size))


class ShootingStar:
    def __init__(self, background=False, dream=False):
        self.background = background
        if background:
            self.x = random.randint(0, WIDTH)
            self.y = random.randint(-100, -20)
            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(2, 6)
        else:
            side = random.choice(['left', 'top', 'right'])
            if side == 'left':
                self.x, self.y = -20, random.randint(20, HEIGHT // 2)
                self.vx, self.vy = random.uniform(6, 10), random.uniform(2, 6)
            elif side == 'top':
                self.x, self.y = random.randint(50, WIDTH - 50), -20
                self.vx, self.vy = random.uniform(-2, 2), random.uniform(6, 10)
            else:
                self.x, self.y = WIDTH + 20, random.randint(20, HEIGHT // 2)
                self.vx, self.vy = random.uniform(-10, -6), random.uniform(2, 6)
        self.trail = []
        self.active = True
        self.color = (200, 255, 255) if dream else SHOOTING_STAR_COLOR

    def update(self):
        if not self.active:
            return
        self.x += self.vx
        self.y += self.vy
        self.trail.append((self.x, self.y))
        if len(self.trail) > 12:
            self.trail.pop(0)
        if self.x < -100 or self.x > WIDTH + 100 or self.y > HEIGHT + 100:
            self.active = False

    def draw(self, surface):
        for i, (x, y) in enumerate(self.trail):
            pygame.draw.circle(surface, self.color, (int(x), int(y)), 2 + i // 4)
        if self.active:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 4)


class EchoWave:
    def __init__(self, x, y, max_radius=80, color=(100, 150, 255), width=1):
        self.x, self.y = x, y
        self.radius = 0
        self.max_radius = max_radius
        self.lifetime = 0
        self.max_lifetime = 45
        self.color = color
        self.width = width
        self.grow = max_radius / (self.max_lifetime * 0.7)

    def update(self):
        self.lifetime += 1
        if self.lifetime < self.max_lifetime * 0.7:
            self.radius += self.grow
        else:
            self.radius -= self.grow * 0.4
        return self.radius > 0 and self.lifetime < self.max_lifetime

    def draw(self, surface):
        if self.radius > 1:
            alpha = int(140 * (1 - self.lifetime / self.max_lifetime))
            pygame.draw.circle(surface, (*self.color, alpha), (int(self.x), int(self.y)), int(self.radius), self.width)


class Aurora:
    def __init__(self):
        self.layers = [{
            'offset': random.uniform(0, 100), 'speed': random.uniform(0.2, 0.8),
            'height': random.uniform(0.1, 0.4), 'color_shift': random.uniform(0, 2 * math.pi)
        } for _ in range(5)]
        self.surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def draw(self, surface, ship_x, ship_y, strength=1.0):
        time_factor = pygame.time.get_ticks() * 0.001
        nx, ny = ship_x / WIDTH, ship_y / HEIGHT
        base_r = int(80 + 120 * abs(math.sin(time_factor * 0.7 + nx * 3)))
        base_g = int(120 + 100 * abs(math.cos(time_factor * 0.5 + ny * 2)))
        base_b = int(180 + 70 * abs(math.sin(time_factor * 0.9 + nx * ny)))
        self.surf.fill((0, 0, 0, 0))
        for layer in self.layers:
            layer_offset = layer['offset'] + time_factor * layer['speed']
            base_height = HEIGHT * layer['height']
            height_variation = 50 * math.sin(time_factor * 0.3 + layer['color_shift'])
            points = []
            for x in range(0, WIDTH + 40, 40):
                wave = math.sin((x + layer_offset * 20) * 0.01 + layer['color_shift']) * 30
                points.append((x, base_height + wave + height_variation))
            for i in range(len(points) - 1):
                color_shift = math.sin(time_factor * 0.4 + i * 0.1 + layer['color_shift'])
                r = int(base_r * (0.8 + 0.2 * color_shift))
                g = int(base_g * (0.8 + 0.2 * color_shift))
                b = int(base_b * (0.8 + 0.2 * color_shift))
                alpha = int(45 * strength * (0.7 + 0.3 * math.sin(time_factor * 0.6 + i * 0.2)))
                pygame.draw.line(self.surf, (r, g, b, alpha), points[i], points[i + 1], 10)
        surface.blit(self.surf, (0, 0))


class CosmicCloud:
    def __init__(self, palette=None):
        self.x = random.randint(-100, WIDTH + 100)
        self.y = random.randint(-100, HEIGHT + 100)
        self.radius = random.randint(110, 200)
        if palette:
            base = lerp_color(random.choice(palette), (255, 255, 255), 0.15)
            self.color = (*base, random.randint(20, 45))
        else:
            self.color = (random.randint(50, 150), random.randint(50, 150), random.randint(100, 200), random.randint(20, 50))
        self.drift_x = random.uniform(-0.5, 0.5)
        self.drift_y = random.uniform(-0.5, 0.5)
        self.surf = pygame.Surface((self.radius * 2 + 30, self.radius * 2 + 30), pygame.SRCALPHA)
        for i in range(5):
            radius = int(self.radius * (1 - i * 0.15))
            alpha = max(0, self.color[3] - i * 8)
            layer = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(layer, (*self.color[:3], alpha), (self.radius + 15, self.radius + 15), radius)
            self.surf.blit(layer, (0, 0))

    def update(self):
        self.x += self.drift_x
        self.y += self.drift_y
        if self.x < -250: self.x = WIDTH + 250
        if self.x > WIDTH + 250: self.x = -250
        if self.y < -250: self.y = HEIGHT + 250
        if self.y > HEIGHT + 250: self.y = -250

    def draw(self, surface):
        pulse = 1 + math.sin(pygame.time.get_ticks() * 0.002) * 0.05
        size = int(self.surf.get_width() * pulse)
        s = pygame.transform.scale(self.surf, (size, size))
        surface.blit(s, (int(self.x - size / 2), int(self.y - size / 2)))


def draw_spiral(surface, x, y, radius, rotation, color, count=20, width=2, step=0.3):
    points = []
    for i in range(count):
        angle = rotation + i * step
        r = radius * (i / float(count))
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    if len(points) > 1:
        pygame.draw.lines(surface, color, False, points, width)


def draw_portal(surface, x, y, radius, rotation, pulse, particles, alpha_k=1.0, tint=None):
    """Портал в точности как в «Космическом шторме» (масштабируемый)."""
    if radius < 2:
        return
    ring = tint or (100, 200, 255)
    pygame.draw.circle(surface, (*ring, int(100 * alpha_k)), (int(x), int(y)), int(radius + pulse), 2)
    draw_spiral(surface, x, y, radius - 5, rotation, (150, 100, 255, int(150 * alpha_k)))
    pygame.draw.circle(surface, (200, 150, 255, int(200 * alpha_k)), (int(x), int(y)), max(1, int(8 * radius / 30 + pulse * 0.5)))
    for p in particles:
        pygame.draw.circle(surface, (200, 150, 255, int(150 * (p['life'] / 30) * alpha_k)), (int(p['x']), int(p['y'])), 2)


def update_portal_particles(particles, x, y, radius):
    if random.random() < 0.4:
        angle = random.uniform(0, 2 * math.pi)
        distance = radius + random.uniform(-5, 5)
        particles.append({'x': x + distance * math.cos(angle), 'y': y + distance * math.sin(angle),
                          'life': 30, 'vx': random.uniform(-1, 1), 'vy': random.uniform(-1, 1)})
    for p in particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['life'] -= 1
        if p['life'] <= 0:
            particles.remove(p)


# --- Туманности и планеты (рисуются один раз, потом просто выводятся) ---
_bg_cache = {}

NEBULA = {
    "night": {"base": (3, 4, 16), "colors": [(25, 50, 120), (15, 90, 110), (50, 25, 110), (20, 40, 90)]},
    "rain": {"base": (9, 5, 8), "colors": [(130, 60, 20), (110, 35, 35), (60, 30, 80), (150, 105, 40)]},
    "dream": {"base": (8, 3, 18), "colors": [(120, 35, 130), (35, 80, 150), (150, 55, 100), (50, 130, 130), (90, 60, 170)]},
}

PLANETS = {
    "night": {"r": 0.30, "pos": (0.06, 0.98), "lit": (75, 115, 170), "atmo": (50, 100, 210), "light": (-0.05, -1.0),
              "bands": [(160, 205, 240), (70, 110, 170)], "band_alpha": (12, 30), "ring": None, "craters": False},
    "rain": {"r": 0.19, "pos": (0.87, 0.19), "lit": (200, 125, 70), "atmo": (210, 110, 40), "light": (-0.7, 0.55),
             "bands": [(230, 150, 80), (130, 70, 35), (250, 200, 140)], "band_alpha": (30, 70), "ring": (225, 185, 140),
             "craters": False},
    "dream": {"r": 0.13, "pos": (0.84, 0.78), "lit": (215, 175, 225), "atmo": (210, 110, 220), "light": (-0.6, -0.65),
              "bands": None, "band_alpha": (0, 0), "ring": None, "craters": True},
}


def make_vignette(size, color=(0, 0, 0), strength=210):
    key = ("vig", size, color, strength)
    if key in _bg_cache:
        return _bg_cache[key]
    vw, vh = 96, 54
    v = pygame.Surface((vw, vh), pygame.SRCALPHA)
    for y in range(vh):
        for x in range(vw):
            dx = (x - vw / 2) / (vw / 2)
            dy = (y - vh / 2) / (vh / 2)
            d = math.sqrt(dx * dx * 0.85 + dy * dy)
            a = max(0.0, min(1.0, (d - 0.5) / 0.65))
            v.set_at((x, y), (*color, int(strength * a ** 1.5)))
    surf = pygame.transform.smoothscale(v, size)
    if len(_bg_cache) > 60:
        for k in [k for k in _bg_cache if k[0] == "vig"]:
            del _bg_cache[k]
    _bg_cache[key] = surf
    return surf


def make_nebula(theme, seed):
    key = ("neb", theme, seed)
    if key in _bg_cache:
        return _bg_cache[key]
    pal = NEBULA[theme]
    rng = random.Random(seed * 7919 + sum(map(ord, theme)))
    sw, sh = max(192, WIDTH // 5), max(108, HEIGHT // 5)
    small = pygame.Surface((sw, sh))
    small.fill(pal["base"])
    centers = [(rng.uniform(0.1, 0.9) * sw, rng.uniform(0.2, 0.8) * sh) for _ in range(3)]
    for ccx, ccy in centers:
        base_col = rng.choice(pal["colors"])
        for _ in range(26):
            r = int(rng.uniform(0.04, 0.22) * sw)
            x = ccx + rng.gauss(0, sw * 0.16)
            y = ccy + rng.gauss(0, sh * 0.2)
            col = lerp_color(base_col, rng.choice(pal["colors"]), rng.random() * 0.6)
            small.blit(glow(r, col, rng.randint(40, 90)), (x - r, y - r), special_flags=pygame.BLEND_RGB_ADD)
    for _ in range(16):
        r = int(rng.uniform(0.03, 0.12) * sw)
        x, y = rng.uniform(0, sw), rng.uniform(0, sh)
        small.blit(glow(r, (40, 40, 40), 255), (x - r, y - r), special_flags=pygame.BLEND_RGB_SUB)
    for _ in range(14):
        r = rng.randint(2, 6)
        x, y = rng.uniform(0, sw), rng.uniform(0, sh)
        small.blit(glow(r, (220, 220, 255), 200), (x - r, y - r), special_flags=pygame.BLEND_RGB_ADD)
    small = pygame.transform.smoothscale(pygame.transform.smoothscale(small, (sw // 2, sh // 2)), (sw, sh))
    big = pygame.transform.smoothscale(small, (int(WIDTH * 1.06), int(HEIGHT * 1.06)))
    big.blit(make_vignette(big.get_size()), (0, 0))
    big = big.convert()
    neb_keys = [k for k in _bg_cache if k[0] == "neb"]
    if len(neb_keys) > 8:
        del _bg_cache[neb_keys[0]]
    _bg_cache[key] = big
    return big


def make_planet(theme):
    key = ("planet", theme)
    if key in _bg_cache:
        return _bg_cache[key]
    cfg = PLANETS[theme]
    rng = random.Random(len(theme) * 13)
    R = int(HEIGHT * cfg["r"])
    size = int(R * 2.9)
    c = size // 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    lx, ly = cfg["light"]
    front = None
    if cfg["ring"]:
        ring_s = pygame.Surface((size, size), pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, int(R * 2.7), int(R * 0.62))
        rect.center = (c, c)
        for i in range(7):
            pygame.draw.ellipse(ring_s, (*cfg["ring"], 60 + i * 18), rect.inflate(-i * int(R * 0.06), -i * int(R * 0.018)), 3)
        back = ring_s.copy()
        back.fill((0, 0, 0, 0), (0, c, size, size - c))
        front = ring_s.copy()
        front.fill((0, 0, 0, 0), (0, 0, size, c))
        back = pygame.transform.rotate(back, 14)
        front = pygame.transform.rotate(front, 14)
        surf.blit(back, back.get_rect(center=(c, c)))
    body = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(body, cfg["lit"], (c, c), R)
    if cfg["bands"]:
        bands = pygame.Surface((size, size), pygame.SRCALPHA)
        y = c - R
        while y < c + R:
            h = rng.randint(max(2, R // 25), max(4, R // 8))
            col = rng.choice(cfg["bands"])
            pygame.draw.rect(bands, (*col, rng.randint(*cfg["band_alpha"])), (0, y, size, h))
            y += h + rng.randint(0, max(1, R // 18))
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (c, c), R)
        bands.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        body.blit(bands, (0, 0))
    if cfg["craters"]:
        for _ in range(11):
            a = rng.uniform(0, 2 * math.pi)
            d = rng.uniform(0, 0.75) * R
            rr = int(rng.uniform(0.05, 0.15) * R)
            cx, cy = int(c + math.cos(a) * d), int(c + math.sin(a) * d)
            pygame.draw.circle(body, lerp_color(cfg["lit"], (60, 40, 80), 0.25), (cx, cy), rr)
            pygame.draw.circle(body, lerp_color(cfg["lit"], (255, 255, 255), 0.2), (cx, cy), rr, max(1, rr // 5))
    shade = pygame.Surface((size, size))
    shade.fill((0, 0, 0))
    steps = 46
    for i in range(steps):
        k = i / steps
        r = R * (1.02 - k)
        cx = c + lx * k * R * 0.55
        cy = c + ly * k * R * 0.55
        g = int(18 + 237 * min(1.0, (k * 1.3) ** 0.85))
        pygame.draw.circle(shade, (g, g, g), (int(cx), int(cy)), max(1, int(r)))
    body.blit(shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    la = math.atan2(ly, lx)
    rim = pygame.Rect(0, 0, R * 2, R * 2)
    rim.center = (c, c)
    pygame.draw.arc(body, (*cfg["atmo"], 220), rim, -la - 1.1, -la + 1.1, max(2, R // 45))
    surf.blit(body, (0, 0))
    if front is not None:
        surf.blit(front, front.get_rect(center=(c, c)))
    result = {"surf": surf, "R": R, "atmo": cfg["atmo"], "pos": cfg["pos"]}
    _bg_cache[key] = result
    return result


SECTORS = [
    {"name": ("Глубокая ночь", "Deep Night"), "music": "Relacs2.mp3", "boss_music": "haos.mp3", "bg": "night",
     "hazard": ("Ледяные астероиды", "Ice asteroids"),
     "pool": [("drifter", 5, 0), ("swarm", 3, 0), ("shooter", 4, 0), ("miner", 2, 1), ("lancer", 2, 3), ("hive", 1, 4)]},
    {"name": ("Вечный дождь", "Eternal Rain"), "music": "burning.mp3", "boss_music": "haos.mp3", "bg": "rain",
     "hazard": ("Метеоритный дождь", "Meteor shower"),
     "pool": [("drifter", 4, 0), ("swarm", 3, 0), ("shooter", 3, 0), ("comet", 4, 0), ("vortex", 2, 1),
              ("lancer", 3, 0), ("twins", 3, 1), ("miner", 2, 0), ("hive", 1, 3)]},
    {"name": ("Режим снов", "Dream Mode"), "music": "under the moon.mp3", "boss_music": "Glitc.mp3", "bg": "dream",
     "hazard": ("Пузыри сна и разломы", "Dream bubbles and rifts"),
     "pool": [("drifter", 3, 0), ("swarm", 3, 0), ("shooter", 2, 0), ("comet", 3, 0), ("vortex", 2, 0),
              ("phantom", 4, 0), ("lancer", 3, 0), ("twins", 3, 0), ("miner", 2, 0), ("mirror", 4, 0), ("hive", 2, 1)]},
]


class Background:
    """Весь задник «Космического шторма» в одном объекте + туманность и планета сектора."""

    def __init__(self, theme="night", seed=7):
        self.theme = theme
        self.stars = [ParallaxStar(1) for _ in range(100)] + [ParallaxStar(2) for _ in range(70)] + \
                     [ParallaxStar(3) for _ in range(50)]
        self.dust = [DustParticle() for _ in range(100)]
        self.aurora = Aurora() if theme == "night" else None
        self.clouds = [CosmicCloud(NEBULA["dream"]["colors"]) for _ in range(7)] if theme == "dream" else []
        self.rain = []
        self.shooting = []
        self.brightness = 1.0
        self.frozen = False
        self.dream_override = False
        self.nebula = make_nebula(theme, seed)
        self.planet = make_planet(theme)

    def update(self, ship_dx, ship_dy):
        for s in self.stars:
            s.update(ship_dx, ship_dy)
        for d in self.dust:
            d.update(ship_dx, ship_dy)
        for c in self.clouds:
            c.update()
        if self.theme == "rain":
            if random.random() < 0.06:
                star = ShootingStar(background=True)
                star.color = (120, 110, 90)
                self.rain.append(star)
            if random.random() < 0.006:
                for _ in range(random.randint(1, 3)):
                    self.shooting.append(ShootingStar())
        elif random.random() < 0.003:
            self.shooting.append(ShootingStar(dream=self.theme == "dream"))
        for lst in (self.rain, self.shooting):
            for s in lst[:]:
                s.update()
                if not s.active:
                    lst.remove(s)

    def draw(self, surface, layer, ship_x, ship_y):
        ox = -(ship_x - WIDTH / 2) * 0.03 - WIDTH * 0.03
        oy = -(ship_y - HEIGHT / 2) * 0.03 - HEIGHT * 0.03
        surface.blit(self.nebula, (int(ox), int(oy)))
        pl = self.planet
        px = WIDTH * pl["pos"][0] - (ship_x - WIDTH / 2) * 0.05
        py = HEIGHT * pl["pos"][1] - (ship_y - HEIGHT / 2) * 0.05
        draw_glow(surface, (px, py), pl["R"] * 1.4, tuple(c // 2 for c in pl["atmo"]), 110)
        surface.blit(pl["surf"], pl["surf"].get_rect(center=(int(px), int(py))))
        if self.aurora:
            self.aurora.draw(surface, ship_x, ship_y, 0.85)
        dream = self.theme == "dream" or self.dream_override
        for c in self.clouds:
            c.draw(layer)
        for s in self.rain:
            s.draw(layer)
        for s in self.stars:
            s.draw(layer, self.brightness, dream, self.frozen)
        for d in self.dust:
            d.draw(layer, dream)
        for s in self.shooting:
            s.draw(layer)


# =====================================================================
#  Корабли и улучшения
# =====================================================================
class Stats:
    def __init__(self, ship_key):
        meta = SAVE["meta"]
        self.max_hp = 100 + 10 * meta.get("hull", 0)
        self.damage = 10 * (1 + 0.06 * meta.get("guns", 0))
        self.fire_delay = 14.0
        self.bullet_speed = 13.0
        self.multishot = 1
        self.pierce = 0
        self.crit = 0.05
        self.crit_mult = 2.0
        self.thrust = 0.45 * (1 + 0.04 * meta.get("engine", 0))
        self.max_speed = 7.0 * (1 + 0.04 * meta.get("engine", 0))
        self.magnet = 130 * (1 + 0.12 * meta.get("magnet", 0))
        self.dash_cd = 150
        self.dash_dist = 190
        self.pulse_cd = 600
        self.pulse_dmg = 30.0
        self.pulse_radius = 270
        self.shield_max = 0
        self.lifesteal = 0
        self.orbitals = 0
        self.echo_shots = 0
        self.star_rain = 0
        self.homing = 0
        self.ricochet = 0
        self.freeze = 0.0
        self.armor = 0
        self.night_fury = False
        self.dream_dash = False
        self.missiles = 0
        self.prism = False
        self.beam = 0
        self.dash_strike = False
        self.reflector = False
        self.storm_rate = 1.0 + 0.1 * meta.get("storm", 0)
        self.storm_dur = 360
        self.combo_dmg = 0
        self.pulse_recharge = 0
        self.size = 1.6
        SHIPS[ship_key]["apply"](self)


SHIPS = {
    "wanderer": {"name": ("Странник", "Wanderer"), "color": SHIP_BLUE, "cost": 0,
                 "desc": ("Корабль из «Космического шторма». Сбалансирован.", "The ship from Cosmic Storm. Balanced."),
                 "apply": lambda s: None},
    "comet": {"name": ("Комета", "Comet"), "color": SHOOTING_STAR_COLOR, "cost": 120,
              "desc": ("Быстрая и скорострельная, но хрупкая. Рывок чаще.", "Fast and rapid-firing, but fragile. Dashes more often."),
              "apply": lambda s: (setattr(s, "max_hp", s.max_hp - 30), setattr(s, "max_speed", s.max_speed * 1.2),
                                  setattr(s, "thrust", s.thrust * 1.2), setattr(s, "fire_delay", s.fire_delay * 0.75),
                                  setattr(s, "damage", s.damage * 0.85), setattr(s, "dash_cd", 100), setattr(s, "size", 1.4))},
    "nebula": {"name": ("Туманность", "Nebula"), "color": PORTAL_PURPLE, "cost": 180,
               "desc": ("Тяжёлая и медленная. Щит и орбитальная звезда со старта.", "Heavy and slow. Starts with a shield and an orbital star."),
               "apply": lambda s: (setattr(s, "max_hp", s.max_hp + 50), setattr(s, "max_speed", s.max_speed * 0.87),
                                   setattr(s, "shield_max", 30), setattr(s, "orbitals", 1), setattr(s, "size", 1.9))},
    "eclipse": {"name": ("Затмение", "Eclipse"), "color": (255, 130, 160), "cost": 260,
                "desc": ("Кометные ракеты со старта, шторм копится вдвое быстрее, но корпус слабее.",
                         "Starts with comet missiles, storm charges twice as fast, weaker hull."),
                "apply": lambda s: (setattr(s, "max_hp", s.max_hp - 15), setattr(s, "missiles", 1),
                                    setattr(s, "storm_rate", s.storm_rate * 2), setattr(s, "size", 1.6))},
}


def _mul(attr, k):
    return lambda s: setattr(s, attr, getattr(s, attr) * k)


def _add(attr, v):
    return lambda s: setattr(s, attr, getattr(s, attr) + v)


def _hp_up(p):
    p.stats.max_hp += 25
    p.hp = min(p.stats.max_hp, p.hp + 25)


UPGRADES = [
    # обычные
    {"id": "dmg", "rarity": "common", "max": 6, "name": ("Калибровка лазера", "Laser Calibration"),
     "desc": ("+20% урона", "+20% damage"), "fn": lambda p: _mul("damage", 1.2)(p.stats)},
    {"id": "rate", "rarity": "common", "max": 6, "name": ("Разгон затвора", "Rapid Breech"),
     "desc": ("+18% скорострельности", "+18% fire rate"), "fn": lambda p: _mul("fire_delay", 0.85)(p.stats)},
    {"id": "hull", "rarity": "common", "max": 6, "name": ("Укреплённый корпус", "Reinforced Hull"),
     "desc": ("+25 к прочности и ремонт на 25", "+25 max hull and repair 25"), "fn": _hp_up},
    {"id": "engine", "rarity": "common", "max": 4, "name": ("Форсаж", "Afterburner"),
     "desc": ("+12% скорости и тяги", "+12% speed and thrust"),
     "fn": lambda p: (_mul("max_speed", 1.12)(p.stats), _mul("thrust", 1.12)(p.stats))},
    {"id": "magnet", "rarity": "common", "max": 4, "name": ("Магнитное поле", "Magnetic Field"),
     "desc": ("+40% радиус сбора пыли", "+40% dust pickup radius"), "fn": lambda p: _mul("magnet", 1.4)(p.stats)},
    {"id": "velocity", "rarity": "common", "max": 3, "name": ("Скоростные снаряды", "Fast Bolts"),
     "desc": ("+25% скорости снарядов, +10% урона", "+25% bolt speed, +10% damage"),
     "fn": lambda p: (_mul("bullet_speed", 1.25)(p.stats), _mul("damage", 1.1)(p.stats))},
    {"id": "repair", "rarity": "common", "max": 99, "name": ("Ремонтные дроны", "Repair Drones"),
     "desc": ("Мгновенно чинит 40% корпуса", "Instantly repairs 40% hull"),
     "fn": lambda p: setattr(p, "hp", min(p.stats.max_hp, p.hp + p.stats.max_hp * 0.4))},
    {"id": "recharge", "rarity": "common", "max": 3, "name": ("Эхо-перезарядка", "Echo Recharge"),
     "desc": ("Каждое убийство ускоряет эхо-импульс", "Every kill speeds up the echo pulse"),
     "fn": lambda p: _add("pulse_recharge", 1)(p.stats)},
    # редкие
    {"id": "multi", "rarity": "rare", "max": 3, "name": ("Двойной залп", "Twin Volley"),
     "desc": ("+1 снаряд в залпе", "+1 bolt per volley"), "fn": lambda p: _add("multishot", 1)(p.stats)},
    {"id": "pierce", "rarity": "rare", "max": 3, "name": ("Пробивающие лучи", "Piercing Rays"),
     "desc": ("Снаряды пробивают ещё 1 врага", "Bolts pierce 1 more enemy"), "fn": lambda p: _add("pierce", 1)(p.stats)},
    {"id": "shield", "rarity": "rare", "max": 3, "name": ("Энергощит", "Energy Shield"),
     "desc": ("+30 щита, восстанавливается вне боя", "+30 shield, regenerates when safe"),
     "fn": lambda p: (_add("shield_max", 30)(p.stats), setattr(p, "shield", p.shield + 30))},
    {"id": "crit", "rarity": "rare", "max": 4, "name": ("Острый взгляд", "Keen Eye"),
     "desc": ("+10% шанс крита, +25% крит. урона", "+10% crit chance, +25% crit damage"),
     "fn": lambda p: (_add("crit", 0.1)(p.stats), _add("crit_mult", 0.25)(p.stats))},
    {"id": "orbital", "rarity": "rare", "max": 4, "name": ("Орбитальная звезда", "Orbital Star"),
     "desc": ("Звезда кружит вокруг корабля, ранит врагов и гасит пули", "A star orbits you, hurting foes and blocking bullets"),
     "fn": lambda p: _add("orbitals", 1)(p.stats)},
    {"id": "echo", "rarity": "rare", "max": 3, "name": ("Эхо пространства", "Echo of Space"),
     "desc": ("Каждый 6-й снаряд взрывается эхо-волной", "Every 6th bolt bursts into an echo wave"),
     "fn": lambda p: _add("echo_shots", 1)(p.stats)},
    {"id": "dash", "rarity": "rare", "max": 3, "name": ("Короткий рывок", "Quick Dash"),
     "desc": ("Рывок на 25% чаще и на 20% дальше", "Dash 25% more often and 20% farther"),
     "fn": lambda p: (_mul("dash_cd", 0.75)(p.stats), _mul("dash_dist", 1.2)(p.stats))},
    {"id": "leech", "rarity": "rare", "max": 3, "name": ("Вампирская пыль", "Leeching Dust"),
     "desc": ("Каждое убийство чинит 1 ед. корпуса", "Each kill repairs 1 hull"), "fn": lambda p: _add("lifesteal", 1)(p.stats)},
    {"id": "freeze", "rarity": "rare", "max": 3, "name": ("Заморозка времени", "Time Freeze"),
     "desc": ("20% шанс замедлить врага вдвое", "20% chance to slow a foe by half"), "fn": lambda p: _add("freeze", 0.2)(p.stats)},
    {"id": "armor", "rarity": "rare", "max": 3, "name": ("Обшивка", "Plating"),
     "desc": ("-2 к любому полученному урону", "-2 to all damage taken"), "fn": lambda p: _add("armor", 2)(p.stats)},
    {"id": "missiles", "rarity": "rare", "max": 3, "name": ("Кометные ракеты", "Comet Missiles"),
     "desc": ("Самонаводящиеся ракеты с взрывом по площади", "Homing missiles that explode in an area"),
     "fn": lambda p: _add("missiles", 1)(p.stats)},
    {"id": "dashstrike", "rarity": "rare", "max": 1, "name": ("Кинетический рывок", "Kinetic Dash"),
     "desc": ("Рывок наносит огромный урон всем на пути", "Dashing deals heavy damage to everything in your path"),
     "fn": lambda p: setattr(p.stats, "dash_strike", True)},
    {"id": "reflector", "rarity": "rare", "max": 1, "name": ("Отражатель", "Reflector"),
     "desc": ("Уклонение разворачивает ближние вражеские пули", "A perfect dodge turns nearby enemy bullets around"),
     "fn": lambda p: setattr(p.stats, "reflector", True)},
    {"id": "stormcaller", "rarity": "rare", "max": 2, "name": ("Буревестник", "Stormcaller"),
     "desc": ("Шкала шторма копится на 35% быстрее, шторм длится дольше", "Storm charges 35% faster and lasts longer"),
     "fn": lambda p: (_mul("storm_rate", 1.35)(p.stats), _add("storm_dur", 120)(p.stats))},
    {"id": "thrill", "rarity": "rare", "max": 2, "name": ("Азарт", "Thrill"),
     "desc": ("Комбо усиливает урон: +1% за каждое убийство в серии", "Combo boosts damage: +1% per kill in the chain"),
     "fn": lambda p: _add("combo_dmg", 1)(p.stats)},
    # эпические
    {"id": "rain", "rarity": "epic", "max": 3, "name": ("Вечный дождь", "Eternal Rain"),
     "desc": ("Падающие звёзды бьют по врагам", "Shooting stars strike your foes"), "fn": lambda p: _add("star_rain", 1)(p.stats)},
    {"id": "homing", "rarity": "epic", "max": 2, "name": ("Самонаведение", "Homing"),
     "desc": ("Снаряды доворачивают к цели", "Bolts curve toward targets"), "fn": lambda p: _add("homing", 1)(p.stats)},
    {"id": "ricochet", "rarity": "epic", "max": 2, "name": ("Рикошет", "Ricochet"),
     "desc": ("Снаряды отскакивают от краёв", "Bolts bounce off the edges"), "fn": lambda p: _add("ricochet", 1)(p.stats)},
    {"id": "fury", "rarity": "epic", "max": 1, "name": ("Ночная ярость", "Night Fury"),
     "desc": ("Ниже 35% корпуса: +60% урона и +30% скорострельности", "Below 35% hull: +60% damage, +30% fire rate"),
     "fn": lambda p: setattr(p.stats, "night_fury", True)},
    {"id": "dreamdash", "rarity": "epic", "max": 1, "name": ("Сон наяву", "Waking Dream"),
     "desc": ("Рывок оставляет жгучий радужный след", "Dashing leaves a burning rainbow trail"),
     "fn": lambda p: setattr(p.stats, "dream_dash", True)},
    {"id": "nova", "rarity": "epic", "max": 2, "name": ("Сверхновая", "Supernova"),
     "desc": ("Эхо-импульс: x2 урон, на 30% чаще", "Echo pulse: x2 damage, 30% more often"),
     "fn": lambda p: (_mul("pulse_dmg", 2)(p.stats), _mul("pulse_cd", 0.7)(p.stats))},
    {"id": "prism", "rarity": "epic", "max": 1, "name": ("Призма", "Prism"),
     "desc": ("Снаряд при попадании раскалывается на 3 осколка", "Bolts split into 3 shards on hit"),
     "fn": lambda p: setattr(p.stats, "prism", True)},
    {"id": "beam", "rarity": "epic", "max": 2, "name": ("Звёздный луч", "Star Beam"),
     "desc": ("Периодически бьёт пронзающим лучом в прицел", "Periodically fires a piercing beam where you aim"),
     "fn": lambda p: _add("beam", 1)(p.stats)},
]
UPGRADE_BY_ID = {u["id"]: u for u in UPGRADES}


def roll_upgrades(player, count=3, luck=0.0, min_rarity=None):
    weights = {"common": 60 * (1 - luck), "rare": 32 + 20 * luck, "epic": 8 + 25 * luck}
    if min_rarity == "rare":
        weights["common"] = 0
    pool = [u for u in UPGRADES if player.upgrades.get(u["id"], 0) < u["max"]]
    picks = []
    for _ in range(count):
        cand = [u for u in pool if u not in picks]
        if not cand:
            break
        w = [weights[u["rarity"]] + 0.01 for u in cand]
        picks.append(random.choices(cand, weights=w)[0])
    return picks


# =====================================================================
#  Игрок
# =====================================================================
class Player:
    def __init__(self, ship_key):
        self.ship_key = ship_key
        self.stats = Stats(ship_key)
        self.color = SHIPS[ship_key]["color"]
        self.hp = self.stats.max_hp
        self.shield = self.stats.shield_max
        self.x, self.y = WIDTH / 2, HEIGHT / 2
        self.vx = self.vy = 0.0
        self.angle = -math.pi / 2
        self.move_angle = -math.pi / 2
        self.trail = []
        self.fire_timer = 0
        self.dash_timer = 0
        self.dash_frames = 0
        self.dash_dir = (0, 0)
        self.dash_hits = set()
        self.dodged = False
        self.pulse_timer = 0
        self.invuln = 0
        self.since_hit = 999
        self.shot_count = 0
        self.thrusting = False
        self.upgrades = {}
        self.level = 1
        self.xp = 0
        self.dust = 30 + 15 * SAVE["meta"].get("start", 0)
        self.revive = SAVE["meta"].get("revive", 0) > 0
        self.orbit_angle = 0.0
        self.kills = 0
        self.storm = 0.0
        self.storm_active = 0
        self.combo = 0
        self.combo_timer = 0
        self.best_combo = 0
        self.missile_timer = 60
        self.beam_timer = 120

    def xp_needed(self):
        n = self.level - 1
        return int(18 + 14 * n + 2.2 * n * n)

    def add_upgrade(self, up):
        self.upgrades[up["id"]] = self.upgrades.get(up["id"], 0) + 1
        up["fn"](self)

    def damage_mult(self):
        k = 1.0
        if self.stats.night_fury and self.hp < self.stats.max_hp * 0.35:
            k *= 1.6
        if self.stats.combo_dmg:
            k *= 1 + min(self.combo, 30) * 0.01 * self.stats.combo_dmg
        return k

    def fire_delay(self):
        d = self.stats.fire_delay
        if self.stats.night_fury and self.hp < self.stats.max_hp * 0.35:
            d *= 0.7
        if self.storm_active:
            d *= 0.45
        return max(3, d)

    def dust_mult(self):
        return 1 + min(self.combo, 50) * 0.02

    def take_damage(self, amount, g):
        if self.invuln > 0 or self.dash_frames > 0:
            return False
        amount = max(1, amount - self.stats.armor)
        if self.storm_active:
            amount *= 0.5
        self.since_hit = 0
        if self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
            sfx("shield", 0.7, 80)
        if amount > 0:
            self.hp -= amount
            sfx("hurt", 0.8, 100)
            g.add_shake(10)
            g.hurt_flash = 20
        self.invuln = 40
        g.texts.append(FloatText(self.x, self.y - 30, f"-{int(amount)}", DANGER))
        return True


# =====================================================================
#  Снаряды, частицы, надписи, опасности
# =====================================================================
class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "dmg", "pierce", "life", "r", "crit", "echo", "bounces", "hit_ids", "trail",
                 "prism", "rainbow")

    def __init__(self, x, y, angle, speed, dmg, pierce, crit, echo, bounces, prism=False, life=90):
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.dmg = dmg
        self.pierce = pierce
        self.life = life
        self.r = 5
        self.crit = crit
        self.echo = echo
        self.bounces = bounces
        self.hit_ids = set()
        self.trail = []
        self.prism = prism
        self.rainbow = False


class EnemyBullet:
    __slots__ = ("x", "y", "vx", "vy", "dmg", "r", "life", "color")

    def __init__(self, x, y, vx, vy, dmg, r=7, color=PORTAL_PURPLE, life=420):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.r, self.life, self.color = dmg, r, life, color


class Missile:
    __slots__ = ("x", "y", "vx", "vy", "life", "trail")

    def __init__(self, x, y, angle):
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * 5, math.sin(angle) * 5
        self.life = 160
        self.trail = []


class Beam:
    """Луч: сначала тонкое предупреждение, затем удар. Бывает вражеским и своим."""

    def __init__(self, x, y, angle, owner, dmg, warn=40, active=12, width=10, color=(255, 120, 140),
                 length=None, spin=0.0, follow=None):
        self.x, self.y, self.angle = x, y, angle
        self.owner, self.dmg = owner, dmg
        self.warn = self.warn_max = warn
        self.active = self.active_max = active
        self.width = width
        self.color = color
        self.length = length or math.hypot(WIDTH, HEIGHT) * 1.2
        self.spin = spin
        self.follow = follow
        self.hit = set()

    def ends(self):
        if self.follow is not None:
            self.x, self.y = self.follow.x, self.follow.y
        return (self.x, self.y), (self.x + math.cos(self.angle) * self.length, self.y + math.sin(self.angle) * self.length)

    @property
    def live(self):
        return self.warn <= 0 and self.active > 0

    def update(self):
        self.angle += self.spin
        if self.warn > 0:
            self.warn -= 1
            if self.warn == 0:
                sfx("beam", 0.6, 80)
        else:
            self.active -= 1
        if self.follow is not None and getattr(self.follow, "hp", 1) <= 0:
            return False
        return self.active > 0

    def draw(self, layer):
        p1, p2 = self.ends()
        if self.warn > 0:
            k = 1 - self.warn / max(1, self.warn_max)
            pygame.draw.line(layer, (*self.color, int(50 + 130 * k)), p1, p2, 1 if k < 0.6 else 2)
        else:
            k = self.active / max(1, self.active_max)
            w = max(2, int(self.width * (0.4 + 0.6 * k)))
            pygame.draw.line(layer, (*self.color, 190), p1, p2, w)
            pygame.draw.line(layer, (255, 255, 255, 230), p1, p2, max(1, w // 3))


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color, speed=4, life=30, size=3):
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(0.3, 1) * speed
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.life = self.max_life = random.randint(max(1, life // 2), life)
        self.color = color
        self.size = size


class FloatText:
    def __init__(self, x, y, s, color, size=18):
        self.x, self.y = x + random.uniform(-8, 8), y
        self.s, self.color, self.size = s, color, size
        self.life = 50

    def update(self):
        self.y -= 0.8
        self.life -= 1
        return self.life > 0


class Pickup:
    __slots__ = ("x", "y", "vx", "vy", "value", "phase", "kind")

    def __init__(self, x, y, value, kind="dust"):
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(1, 4)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.value = value
        self.phase = random.uniform(0, 6.28)
        self.kind = kind


class Rock:
    """Ледяной астероид: гасит любые пули, раскалывается и роняет пыль."""

    def __init__(self, x, y, r, hp, color=(70, 95, 140)):
        self.x, self.y, self.r = x, y, r
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(0.2, 0.7)
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.hp = self.max_hp = hp
        n = random.randint(7, 11)
        angles = sorted(random.uniform(0, 2 * math.pi) for _ in range(n))
        self.shape = [(ang, r * random.uniform(0.75, 1.12)) for ang in angles]
        self.rot = random.uniform(0, 6.28)
        self.vr = random.uniform(-0.012, 0.012)
        self.flash = 0
        self.color = color

    def points(self):
        return [(self.x + math.cos(a + self.rot) * d, self.y + math.sin(a + self.rot) * d) for a, d in self.shape]

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rot += self.vr
        if self.flash > 0:
            self.flash -= 1
        if self.x < self.r or self.x > WIDTH - self.r:
            self.vx = -self.vx
            self.x = max(self.r, min(WIDTH - self.r, self.x))
        if self.y < self.r or self.y > HEIGHT - self.r:
            self.vy = -self.vy
            self.y = max(self.r, min(HEIGHT - self.r, self.y))

    def draw(self, layer):
        pts = self.points()
        base = (255, 255, 255) if self.flash else self.color
        pygame.draw.polygon(layer, (*base, 235), pts)
        hi = lerp_color(base, (220, 235, 255), 0.5)
        pygame.draw.polygon(layer, (*hi, 255), pts, 2)
        cx, cy = self.x - self.r * 0.25, self.y - self.r * 0.3
        pygame.draw.circle(layer, (*lerp_color(base, (255, 255, 255), 0.35), 120), (int(cx), int(cy)), int(self.r * 0.22))


class SpawnPortal:
    def __init__(self, x, y, queue):
        self.x, self.y = x, y
        self.queue = list(queue)
        self.scale = 0.0
        self.rotation = 0.0
        self.particles = []
        self.emit_timer = 50
        self.closing = False
        self.base_radius = 34

    def update(self, g):
        self.rotation += 0.08
        if self.closing:
            self.scale = max(0.0, self.scale - 0.04)
        else:
            self.scale = min(1.0, self.scale + 0.035)
        update_portal_particles(self.particles, self.x, self.y, self.base_radius * self.scale)
        if self.scale >= 1 and not self.closing:
            self.emit_timer -= 1
            if self.emit_timer <= 0:
                if self.queue:
                    kind, elite = self.queue.pop(0)
                    g.spawn_enemy(kind, self.x, self.y, elite)
                    self.emit_timer = 16
                else:
                    self.closing = True
        return not (self.closing and self.scale <= 0)

    def draw(self, layer):
        pulse = math.sin(pygame.time.get_ticks() * 0.003) * 5
        draw_portal(layer, self.x, self.y, self.base_radius * self.scale, self.rotation, pulse * self.scale, self.particles)


# =====================================================================
#  Враги
# =====================================================================
ENEMY_INFO = {
    "drifter": {"hp": 22, "r": 11, "dmg": 10, "drop": 2, "cost": 1, "color": FLAME_PARTICLE},
    "swarm": {"hp": 7, "r": 6, "dmg": 6, "drop": 1, "cost": 3, "color": (100, 150, 255)},
    "shooter": {"hp": 42, "r": 15, "dmg": 12, "drop": 3, "cost": 3, "color": (150, 100, 255)},
    "comet": {"hp": 32, "r": 12, "dmg": 18, "drop": 3, "cost": 3, "color": SHOOTING_STAR_COLOR},
    "vortex": {"hp": 95, "r": 24, "dmg": 14, "drop": 6, "cost": 6, "color": (100, 200, 255)},
    "phantom": {"hp": 38, "r": 14, "dmg": 12, "drop": 4, "cost": 4, "color": (255, 150, 230)},
    "lancer": {"hp": 34, "r": 13, "dmg": 20, "drop": 3, "cost": 3, "color": (255, 120, 140)},
    "mirror": {"hp": 55, "r": 16, "dmg": 12, "drop": 4, "cost": 4, "color": (215, 235, 255)},
    "hive": {"hp": 130, "r": 26, "dmg": 12, "drop": 7, "cost": 7, "color": (255, 190, 90)},
    "miner": {"hp": 36, "r": 13, "dmg": 10, "drop": 3, "cost": 3, "color": (255, 170, 60)},
    "twins": {"hp": 40, "r": 12, "dmg": 10, "drop": 3, "cost": 4, "color": (120, 255, 230)},
}

AFFIXES = {
    "shielded": (("Щит", "Shielded"), (120, 200, 255)),
    "splitter": (("Делящийся", "Splitter"), (255, 170, 90)),
    "explosive": (("Взрывной", "Explosive"), (255, 100, 80)),
    "haste": (("Стремительный", "Swift"), (255, 255, 140)),
    "regen": (("Живучий", "Regenerating"), (120, 255, 150)),
}

_enemy_ids = [0]


class Enemy:
    def __init__(self, kind, x, y, elite, hp_mult, dmg_mult, sector=0):
        info = ENEMY_INFO[kind]
        _enemy_ids[0] += 1
        self.id = _enemy_ids[0]
        self.kind = kind
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.elite = elite
        self.max_hp = info["hp"] * hp_mult * ((2.4 if kind == "hive" else 3.5) if elite else 1)
        self.hp = self.max_hp
        self.r = info["r"] * (1.45 if elite else 1)
        self.dmg = info["dmg"] * dmg_mult * (1.3 if elite else 1)
        self.drop = info["drop"] * (4 if elite else 1)
        self.color = info["color"]
        self.flash = 0
        self.slow = 0
        self.timer = random.randint(30, 90)
        self.state = 0
        self.angle = random.uniform(0, 2 * math.pi)
        self.aim = 0.0
        self.alpha = 255
        self.boss = False
        self.zone_k = 1.0
        self.parent = None
        self.partner = None
        self.is_a = False
        self.enraged = False
        self.wp = None
        self.affixes = []
        self.shield = 0.0
        self.shield_max = 0.0
        self.shield_cd = 0
        self.since_hit = 999
        if elite:
            options = [a for a in AFFIXES if not (a == "splitter" and kind in ("hive", "twins"))]
            self.affixes = random.sample(options, 1 if sector == 0 else 2)
            if "shielded" in self.affixes:
                self.shield = self.shield_max = self.max_hp * 0.6

    def speed_k(self):
        k = 0.5 if self.slow > 0 else 1.0
        if "haste" in self.affixes:
            k *= 1.45
        if self.enraged:
            k *= 1.4
        return k

    def steer_to(self, tx, ty, accel, max_speed):
        a = math.atan2(ty - self.y, tx - self.x)
        k = self.speed_k()
        self.vx += math.cos(a) * accel * k
        self.vy += math.sin(a) * accel * k
        sp = math.hypot(self.vx, self.vy)
        if sp > max_speed * k:
            self.vx *= max_speed * k / sp
            self.vy *= max_speed * k / sp

    def keep_distance(self, p, near, far, accel, speed, strafe=0.06):
        d = math.hypot(p.x - self.x, p.y - self.y)
        a = math.atan2(p.y - self.y, p.x - self.x)
        side = a + math.pi / 2 * (1 if self.id % 2 else -1)
        if d > far:
            self.steer_to(p.x, p.y, accel, speed)
        elif d < near:
            self.steer_to(self.x * 2 - p.x, self.y * 2 - p.y, accel * 1.2, speed * 1.1)
        else:
            self.steer_to(self.x + math.cos(side) * 50, self.y + math.sin(side) * 50, strafe, speed * 0.7)
        return d, a

    def update(self, g):
        p = g.player
        self.timer -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.slow > 0:
            self.slow -= 1
        self.since_hit += 1
        if "regen" in self.affixes and self.hp < self.max_hp and self.since_hit > 120:
            self.hp = min(self.max_hp, self.hp + self.max_hp * 0.0005)
        if self.shield_max:
            self.shield_cd -= 1
            if self.shield_cd <= 0 and self.shield < self.shield_max:
                self.shield = min(self.shield_max, self.shield + self.shield_max / 300)
        k = self.kind
        fire_k = 0.7 if self.elite else 1.0
        if k == "drifter":
            self.steer_to(p.x, p.y, 0.12, 3.0)
            self.angle = math.atan2(self.vy, self.vx)
        elif k == "swarm":
            self.steer_to(p.x + math.sin(self.id + g.t * 0.05) * 60, p.y + math.cos(self.id * 1.7 + g.t * 0.05) * 60, 0.25, 4.2)
        elif k == "shooter":
            d, a = self.keep_distance(p, 300, 460, 0.09, 2.3)
            self.angle += 0.04
            if self.timer <= 0:
                self.timer = int(100 / self.speed_k() * fire_k)
                shots = 3 if self.elite else 1
                for i in range(shots):
                    sa = a + (i - (shots - 1) / 2) * 0.22
                    g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(sa) * 4.6, math.sin(sa) * 4.6, self.dmg))
        elif k == "comet":
            if self.state == 0:  # прицеливание
                self.vx *= 0.9
                self.vy *= 0.9
                self.angle = math.atan2(p.y - self.y, p.x - self.x)
                if self.timer <= 0:
                    self.state = 1
                    self.timer = 45
            elif self.state == 1:  # предупреждение
                self.vx *= 0.8
                self.vy *= 0.8
                if self.timer <= 0:
                    self.state = 2
                    self.timer = 36
                    sp = 15 * self.speed_k()
                    self.vx, self.vy = math.cos(self.angle) * sp, math.sin(self.angle) * sp
            else:  # бросок
                g.trails.append([self.x, self.y, 18, SHOOTING_STAR_COLOR, 3])
                if self.timer <= 0:
                    self.state = 0
                    self.timer = random.randint(60, 110)
        elif k == "vortex":
            self.steer_to(p.x, p.y, 0.03, 0.9)
            self.angle += 0.1
            d = math.hypot(p.x - self.x, p.y - self.y)
            if d < 280 and p.dash_frames == 0:
                pull = 0.18 * (1 - d / 280)
                p.vx += (self.x - p.x) / max(1, d) * pull * 3
                p.vy += (self.y - p.y) / max(1, d) * pull * 3
            if self.timer <= 0:
                self.timer = 170
                n = 12 if self.elite else 8
                for i in range(n):
                    a = self.angle + i * 2 * math.pi / n
                    g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 3.2, math.sin(a) * 3.2, self.dmg * 0.8, 6, (100, 200, 255)))
        elif k == "phantom":
            self.vx *= 0.95
            self.vy *= 0.95
            if self.state == 0 and self.timer <= 0:
                self.state = 1
                self.timer = 30
            elif self.state == 1:
                self.alpha = max(40, self.alpha - 10)
                if self.timer <= 0:
                    a = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(220, 320)
                    g.echoes.append(EchoWave(self.x, self.y, 50, PORTAL_PURPLE))
                    self.x = max(40, min(WIDTH - 40, p.x + math.cos(a) * dist))
                    self.y = max(40, min(HEIGHT - 40, p.y + math.sin(a) * dist))
                    g.echoes.append(EchoWave(self.x, self.y, 50, PORTAL_PURPLE))
                    self.state = 2
                    self.timer = 25
            elif self.state == 2:
                self.alpha = min(255, self.alpha + 16)
                if self.timer <= 0:
                    a = math.atan2(p.y - self.y, p.x - self.x)
                    for i in range(3 if not self.elite else 5):
                        sa = a + (i - 1) * 0.25
                        g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(sa) * 5, math.sin(sa) * 5, self.dmg, 6, (255, 150, 230)))
                    self.state = 0
                    self.timer = random.randint(110, 170)
        elif k == "lancer":
            if self.state == 0:  # занимает позицию
                d, a = self.keep_distance(p, 420, 650, 0.08, 2.6)
                self.aim = a
                if self.timer <= 0:
                    self.state = 1
                    self.timer = 60
            else:  # целится: линия видна заранее
                self.vx *= 0.85
                self.vy *= 0.85
                want = math.atan2(p.y - self.y, p.x - self.x)
                if self.timer > 16:
                    diff = (want - self.aim + math.pi) % (2 * math.pi) - math.pi
                    self.aim += max(-0.045, min(0.045, diff))
                if self.timer <= 0:
                    g.beams.append(Beam(self.x, self.y, self.aim, "enemy", self.dmg, warn=0, active=12, width=10))
                    sfx("beam", 0.5, 60)
                    self.state = 0
                    self.timer = int(random.randint(120, 170) * fire_k)
        elif k == "mirror":
            if self.state == 0:
                d, a = self.keep_distance(p, 260, 420, 0.08, 2.2)
                diff = (a - self.angle + math.pi) % (2 * math.pi) - math.pi
                self.angle += max(-0.07, min(0.07, diff))
                if self.timer <= 0:
                    self.state = 1
                    self.timer = 70
            else:  # заряд: щит опущен
                self.vx *= 0.9
                self.vy *= 0.9
                if self.timer <= 0:
                    n = 14 if self.elite else 10
                    for i in range(n):
                        a = self.angle + i * 2 * math.pi / n
                        g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 3.6, math.sin(a) * 3.6, self.dmg * 0.8, 6, (215, 235, 255)))
                    self.state = 0
                    self.timer = random.randint(170, 230)
        elif k == "hive":
            d = math.hypot(p.x - self.x, p.y - self.y)
            if d > 300:
                self.steer_to(p.x, p.y, 0.02, 0.6)
            else:
                self.vx *= 0.96
                self.vy *= 0.96
            self.angle += 0.02
            if self.timer <= 0:
                self.timer = 220
                children = sum(1 for e in g.enemies if e.parent == self.id)
                if children < 12:
                    for _ in range(3):
                        g.spawn_enemy("swarm", self.x + random.uniform(-20, 20), self.y + random.uniform(-20, 20), False, parent=self.id)
                    g.echoes.append(EchoWave(self.x, self.y, 60, self.color, 2))
        elif k == "miner":
            d = math.hypot(p.x - self.x, p.y - self.y)
            if self.wp is None or math.hypot(self.wp[0] - self.x, self.wp[1] - self.y) < 40 or d < 200:
                for _ in range(10):
                    self.wp = (random.randint(80, WIDTH - 80), random.randint(80, HEIGHT - 80))
                    if math.hypot(self.wp[0] - p.x, self.wp[1] - p.y) > 260:
                        break
            self.steer_to(*self.wp, 0.08, 2.4)
            self.angle += 0.06
            if self.timer <= 0:
                self.timer = int(130 * fire_k)
                if sum(1 for m in g.mines if m["owner"] == self.id) < 5:
                    g.mines.append({"x": self.x, "y": self.y, "arm": 60, "life": 900, "owner": self.id,
                                    "dmg": self.dmg * 1.4})
        elif k == "twins":
            partner_alive = self.partner is not None and self.partner.hp > 0
            if not partner_alive:
                self.enraged = True
                self.steer_to(p.x, p.y, 0.14, 3.2)
            else:
                orbit = g.t * 0.018 + (0 if self.is_a else math.pi)
                self.steer_to(p.x + math.cos(orbit) * 190, p.y + math.sin(orbit) * 190, 0.11, 2.8)
                if self.is_a and p.dash_frames == 0:
                    if seg_dist(p.x, p.y, self.x, self.y, self.partner.x, self.partner.y) < 10:
                        p.take_damage(self.dmg, g)
        self.x += self.vx * self.zone_k
        self.y += self.vy * self.zone_k
        if self.x < self.r or self.x > WIDTH - self.r:
            self.vx *= -0.6
            self.x = max(self.r, min(WIDTH - self.r, self.x))
            if k == "comet" and self.state == 2:
                self.timer = 0
        if self.y < self.r or self.y > HEIGHT - self.r:
            self.vy *= -0.6
            self.y = max(self.r, min(HEIGHT - self.r, self.y))
            if k == "comet" and self.state == 2:
                self.timer = 0

    def reflects(self, bx, by):
        """Зеркало отражает пули, прилетевшие спереди, пока щит поднят."""
        if self.kind != "mirror" or self.state != 0 or self.boss:
            return False
        a = math.atan2(by - self.y, bx - self.x)
        diff = (a - self.angle + math.pi) % (2 * math.pi) - math.pi
        return abs(diff) < 1.15

    def draw(self, layer, screen_surf, g):
        x, y, r = self.x, self.y, self.r
        flash = self.flash > 0
        k = self.kind
        color = (255, 255, 255) if flash else self.color
        if self.elite:
            draw_glow(screen_surf, (x, y), r * 3, GOLD, 70)
        if k == "drifter":
            a = self.angle
            pts = [(x + math.cos(a) * r * 1.4, y + math.sin(a) * r * 1.4),
                   (x + math.cos(a + 2.5) * r, y + math.sin(a + 2.5) * r),
                   (x + math.cos(a - 2.5) * r, y + math.sin(a - 2.5) * r)]
            pygame.draw.polygon(layer, (*color, 230), pts)
            if random.random() < 0.6:
                bx, by = x - math.cos(a) * r, y - math.sin(a) * r
                pygame.draw.circle(layer, (255, 180, 80, 160), (int(bx + random.uniform(-2, 2)), int(by + random.uniform(-2, 2))), random.randint(2, 4))
        elif k == "swarm":
            pygame.draw.circle(layer, (*color, 230), (int(x), int(y)), int(r))
            draw_glow(screen_surf, (x, y), r * 3, (60, 90, 200), 90)
        elif k == "shooter":
            pts = [(x + math.cos(self.angle + i * math.pi / 2) * r * 1.2, y + math.sin(self.angle + i * math.pi / 2) * r * 1.2) for i in range(4)]
            pygame.draw.polygon(layer, (*color, 220), pts)
            pygame.draw.circle(layer, (200, 150, 255, 120), (int(x), int(y)), int(r * 1.7), 1)
        elif k == "comet":
            if self.state == 1:
                ex, ey = x + math.cos(self.angle) * 900, y + math.sin(self.angle) * 900
                a = 60 + int(100 * (1 - self.timer / 45))
                pygame.draw.line(layer, (255, 120, 100, max(0, min(255, a))), (x, y), (ex, ey), 2)
            pygame.draw.circle(layer, (*color, 240), (int(x), int(y)), int(r))
            draw_glow(screen_surf, (x, y), r * 3, (200, 200, 120), 100)
        elif k == "vortex":
            draw_spiral(layer, x, y, r * 2.4, self.angle, (*color, 160), 30, 2, 0.4)
            pygame.draw.circle(layer, (50, 150, 255, 200), (int(x), int(y)), int(r * 0.5))
            pygame.draw.circle(layer, (100, 200, 255, 50), (int(x), int(y)), 280, 1)
        elif k == "phantom":
            al = self.alpha
            pts = [(x, y - r * 1.3), (x + r, y), (x, y + r * 1.3), (x - r, y)]
            pygame.draw.polygon(layer, (*color, int(al * 0.85)), pts)
            pygame.draw.circle(layer, (40, 10, 60, al), (int(x), int(y)), int(r * 0.35))
        elif k == "lancer":
            a = self.aim
            pts = [(x + math.cos(a) * r * 1.8, y + math.sin(a) * r * 1.8),
                   (x + math.cos(a + 2.4) * r, y + math.sin(a + 2.4) * r),
                   (x - math.cos(a) * r * 0.4, y - math.sin(a) * r * 0.4),
                   (x + math.cos(a - 2.4) * r, y + math.sin(a - 2.4) * r)]
            pygame.draw.polygon(layer, (*color, 235), pts)
            if self.state == 1:
                kk = 1 - max(0, self.timer) / 60
                ex, ey = x + math.cos(a) * 2400, y + math.sin(a) * 2400
                pygame.draw.line(layer, (255, 100, 120, int(40 + 160 * kk)), (x, y), (ex, ey), 1 if kk < 0.7 else 2)
                draw_glow(screen_surf, (x, y), r * 2.5, (200, 60, 80), int(80 + 120 * kk))
        elif k == "mirror":
            pts = [(x + math.cos(self.angle + i * math.pi / 3) * r, y + math.sin(self.angle + i * math.pi / 3) * r) for i in range(6)]
            pygame.draw.polygon(layer, (*lerp_color(color, (90, 110, 160), 0.5), 220), pts)
            if self.state == 0:
                rect = pygame.Rect(0, 0, r * 4, r * 4)
                rect.center = (x, y)
                pygame.draw.arc(layer, (230, 245, 255, 240), rect, -self.angle - 1.15, -self.angle + 1.15, 4)
                draw_glow(screen_surf, (x + math.cos(self.angle) * r * 2, y + math.sin(self.angle) * r * 2), r * 1.6, (120, 140, 170), 120)
            else:
                pulse = 0.5 + 0.5 * math.sin(g.t * 0.5)
                pygame.draw.circle(layer, (255, 255, 255, int(150 + 100 * pulse)), (int(x), int(y)), int(r * 0.45))
        elif k == "hive":
            pulse = 1 + 0.06 * math.sin(g.t * 0.08)
            pts = [(x + math.cos(self.angle + i * math.pi / 3) * r * pulse, y + math.sin(self.angle + i * math.pi / 3) * r * pulse) for i in range(6)]
            pygame.draw.polygon(layer, (*lerp_color(color, (90, 60, 20), 0.55), 230), pts)
            pygame.draw.polygon(layer, (*color, 255), pts, 2)
            for i in range(6):
                a = -self.angle * 2 + i * math.pi / 3
                pygame.draw.circle(layer, (*color, 220), (int(x + math.cos(a) * r * 0.55), int(y + math.sin(a) * r * 0.55)), max(2, int(r * 0.16)))
            draw_glow(screen_surf, (x, y), r * 2.2, (120, 80, 20), 100)
        elif k == "miner":
            for i in range(4):
                a = self.angle + i * math.pi / 2
                pygame.draw.line(layer, (*color, 230), (x, y), (x + math.cos(a) * r * 1.3, y + math.sin(a) * r * 1.3), 4)
            pygame.draw.circle(layer, (*color, 240), (int(x), int(y)), int(r * 0.6))
            if (g.t // 10) % 2 == 0:
                pygame.draw.circle(layer, (255, 60, 60, 255), (int(x), int(y)), max(2, int(r * 0.25)))
        elif k == "twins":
            if self.is_a and self.partner is not None and self.partner.hp > 0:
                flick = 140 + int(80 * math.sin(g.t * 0.4))
                pygame.draw.line(layer, (120, 255, 230, flick), (x, y), (self.partner.x, self.partner.y), 3)
                for i in range(1, 6):
                    f = (i / 6 + g.t * 0.02) % 1
                    pygame.draw.circle(layer, (220, 255, 250, 220),
                                       (int(x + (self.partner.x - x) * f), int(y + (self.partner.y - y) * f)), 3)
            col = (255, 140, 120) if self.enraged and not flash else color
            pygame.draw.circle(layer, (*col, 240), (int(x), int(y)), int(r))
            pygame.draw.circle(layer, (20, 60, 60, 255), (int(x), int(y)), int(r * 0.45))
            draw_glow(screen_surf, (x, y), r * 2.6, (40, 120, 110), 110)
        if self.slow > 0:
            pygame.draw.circle(layer, (200, 255, 255, 120), (int(x), int(y)), int(r * 1.4), 2)
        if self.shield > 1:
            pygame.draw.circle(layer, (120, 200, 255, int(70 + 120 * self.shield / self.shield_max)), (int(x), int(y)), int(r * 1.75), 2)
        if self.hp < self.max_hp and not self.boss:
            w = int(r * 2.2)
            pygame.draw.rect(layer, (40, 40, 70, 200), (x - w / 2, y - r - 12, w, 4))
            pygame.draw.rect(layer, (*(GOLD if self.elite else DANGER), 230), (x - w / 2, y - r - 12, w * max(0, self.hp) / self.max_hp, 4))
        if self.affixes:
            label = " · ".join(AFFIXES[a][0][LI()] for a in self.affixes)
            blit_text(layer, label, 12, AFFIXES[self.affixes[0]][1], (x, y - r - 16), "midbottom")

    def hit_test(self, x, y, r):
        return (self.x - x) ** 2 + (self.y - y) ** 2 < (self.r + r) ** 2


# =====================================================================
#  Боссы
# =====================================================================
class AuroraSerpent(Enemy):
    """Сектор 1: змей из северного сияния."""

    def __init__(self, hp_mult, dmg_mult):
        super().__init__("drifter", WIDTH / 2, -100, False, 1, 1)
        self.boss = True
        self.name = L("Аврора — змей сияния", "Aurora, the Light Serpent")
        self.sub = L("Сияние ожило и голодно", "The aurora came alive — and it is hungry")
        self.max_hp = self.hp = 1500 * hp_mult
        self.dmg = 20 * dmg_mult
        self.r = 26
        self.drop = 70
        self.tt = 0.0
        self.history = []
        self.segments = []
        self.n_seg = 16
        self.curtain_timer = 420

    def update(self, g):
        if self.flash > 0:
            self.flash -= 1
        if self.slow > 0:
            self.slow -= 1
        phase2 = self.hp < self.max_hp * 0.5
        self.tt += 0.011 * self.speed_k() * (1.3 if phase2 else 1)
        tx = WIDTH / 2 + WIDTH * 0.38 * math.sin(self.tt * 0.9)
        ty = HEIGHT / 2 + HEIGHT * 0.33 * math.sin(self.tt * 1.4 + 1)
        self.x += (tx - self.x) * 0.06
        self.y += (ty - self.y) * 0.06
        self.history.insert(0, (self.x, self.y))
        del self.history[self.n_seg * 7:]
        self.segments = [self.history[i * 7] for i in range(1, self.n_seg) if i * 7 < len(self.history)]
        self.timer -= 1
        if self.timer <= 0:
            self.timer = 95 if phase2 else 130
            n = 16 if phase2 else 12
            off = random.uniform(0, 1)
            for i in range(n):
                a = (i + off) * 2 * math.pi / n
                g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 3.6, math.sin(a) * 3.6, self.dmg * 0.6, 7, (100, 255, 200)))
        if phase2 and g.t % 50 == 0 and self.segments:
            sx, sy = random.choice(self.segments)
            a = math.atan2(g.player.y - sy, g.player.x - sx)
            g.ebullets.append(EnemyBullet(sx, sy, math.cos(a) * 5, math.sin(a) * 5, self.dmg * 0.5, 6, (120, 100, 255)))
        if phase2:
            self.curtain_timer -= 1
            if self.curtain_timer <= 0:
                # Занавес сияния: стена пуль с одним проходом
                self.curtain_timer = 480
                gap = random.uniform(HEIGHT * 0.2, HEIGHT * 0.8)
                left = random.random() < 0.5
                for yy in range(20, HEIGHT, int(40 * UI) + 6):
                    if abs(yy - gap) < 110 * UI + 20:
                        continue
                    g.ebullets.append(EnemyBullet(-10 if left else WIDTH + 10, yy, 3.2 if left else -3.2, 0,
                                                  self.dmg * 0.6, 8, (100, 255, 200), 900))
        if g.t % 600 == 300:
            g.portals.append(SpawnPortal(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), [("swarm", False)] * 5))

    def hit_test(self, x, y, r):
        if (self.x - x) ** 2 + (self.y - y) ** 2 < (self.r + r) ** 2:
            return True
        for i, (sx, sy) in enumerate(self.segments):
            sr = max(8, self.r * (1 - i / self.n_seg) * 0.8)
            if (sx - x) ** 2 + (sy - y) ** 2 < (sr + r) ** 2:
                return True
        return False

    def draw(self, layer, screen_surf, g):
        tf = pygame.time.get_ticks() * 0.001
        for i in range(len(self.segments) - 1, -1, -1):
            sx, sy = self.segments[i]
            k = i / self.n_seg
            c = lerp_color((100, 255, 200), (120, 100, 255), (math.sin(tf + k * 4) + 1) / 2)
            sr = max(8, self.r * (1 - k) * 0.8)
            draw_glow(screen_surf, (sx, sy), sr * 2.5, c, 80)
            pygame.draw.circle(layer, (*c, 200), (int(sx), int(sy)), int(sr))
        c = (255, 255, 255) if self.flash else (180, 255, 230)
        draw_glow(screen_surf, (self.x, self.y), self.r * 3.5, (100, 255, 200), 120)
        pygame.draw.circle(layer, (*c, 240), (int(self.x), int(self.y)), int(self.r))
        pygame.draw.circle(layer, (20, 40, 60, 255), (int(self.x + 8), int(self.y - 6)), 5)
        pygame.draw.circle(layer, (20, 40, 60, 255), (int(self.x - 8), int(self.y - 6)), 5)


class StormEye(Enemy):
    """Сектор 2: Око бури — огромный портал."""

    def __init__(self, hp_mult, dmg_mult):
        super().__init__("vortex", WIDTH / 2, HEIGHT / 3, False, 1, 1)
        self.boss = True
        self.name = L("Око бури", "Eye of the Storm")
        self.sub = L("Сердцевина вечного дождя", "The core of the eternal rain")
        self.max_hp = self.hp = 2300 * hp_mult
        self.dmg = 22 * dmg_mult
        self.r = 62
        self.drop = 90
        self.spin = 0.0
        self.target = (WIDTH / 2, HEIGHT / 3)
        self.particles = []
        self.rotation = 0.0
        self.beam_timer = 360

    def update(self, g):
        if self.flash > 0:
            self.flash -= 1
        if self.slow > 0:
            self.slow -= 1
        phase2 = self.hp < self.max_hp * 0.5
        self.rotation += 0.05
        if math.hypot(self.target[0] - self.x, self.target[1] - self.y) < 20:
            self.target = (random.randint(200, WIDTH - 200), random.randint(150, HEIGHT - 150))
        self.steer_to(*self.target, 0.03, 1.1)
        self.x += self.vx
        self.y += self.vy
        update_portal_particles(self.particles, self.x, self.y, self.r)
        if g.t % (6 if not phase2 else 5) == 0:
            self.spin += 0.23 * self.speed_k()
            arms = 2 if phase2 else 1
            for k in range(arms):
                a = self.spin + k * math.pi
                g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 4, math.sin(a) * 4, self.dmg * 0.5, 7, (150, 100, 255)))
        if g.t % 260 == 130:
            n = 3 if phase2 else 2
            g.portals.append(SpawnPortal(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), [("comet", False)] * n))
        if phase2:
            if g.t % 400 == 0:
                g.portals.append(SpawnPortal(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), [("swarm", False)] * 6))
            self.beam_timer -= 1
            if self.beam_timer <= 0:
                # Вращающиеся лучи бури
                self.beam_timer = 600
                base = math.atan2(g.player.y - self.y, g.player.x - self.x) + math.pi / 2
                spin = random.choice([-1, 1]) * 0.012
                for i in range(2):
                    g.beams.append(Beam(self.x, self.y, base + i * math.pi, "enemy", self.dmg * 0.8, warn=60, active=150,
                                        width=14, color=(170, 120, 255), spin=spin, follow=self))

    def draw(self, layer, screen_surf, g):
        pulse = math.sin(pygame.time.get_ticks() * 0.003) * 8
        draw_glow(screen_surf, (self.x, self.y), self.r * 3, (90, 60, 200), 120)
        draw_portal(layer, self.x, self.y, self.r, self.rotation, pulse, self.particles)
        draw_spiral(layer, self.x, self.y, self.r * 1.2, -self.rotation * 1.3, (100, 200, 255, 140), 30, 2, 0.35)
        a = math.atan2(g.player.y - self.y, g.player.x - self.x)
        ex, ey = self.x + math.cos(a) * self.r * 0.35, self.y + math.sin(a) * self.r * 0.35
        pygame.draw.circle(layer, (255, 255, 255, 255) if self.flash else (230, 220, 255, 255), (int(self.x), int(self.y)), int(self.r * 0.45))
        pygame.draw.circle(layer, (40, 0, 70, 255), (int(ex), int(ey)), int(self.r * 0.2))


class HeartStar(Enemy):
    """Сектор 3: Сердце шторма — пульсирующая звезда («звезда-сердцебиение»)."""

    def __init__(self, hp_mult, dmg_mult):
        super().__init__("phantom", WIDTH / 2, HEIGHT / 2, False, 1, 1)
        self.boss = True
        self.name = L("Сердце шторма", "Heart of the Storm")
        self.sub = L("Звезда, что бьётся в центре всего", "The star that beats at the center of everything")
        self.max_hp = self.hp = 3200 * hp_mult
        self.dmg = 24 * dmg_mult
        self.r = 55
        self.drop = 120
        self.beat = 0.0
        self.beat_timer = 120
        self.rings = []
        self.rot = 0.0
        self.flat_timer = 300

    def update(self, g):
        if self.flash > 0:
            self.flash -= 1
        if self.slow > 0:
            self.slow -= 1
        frac = self.hp / self.max_hp
        period = 100 if frac > 0.66 else 78 if frac > 0.33 else 60
        self.rot += 0.01
        self.beat *= 0.9
        self.beat_timer -= 1
        if self.beat_timer <= 0:
            self.beat_timer = period
            self.beat = 1.0
            gap = random.uniform(0, 2 * math.pi)
            self.rings.append({"r": self.r, "gap": gap, "hit": False, "w": 0.55 if frac > 0.33 else 0.45})
            g.add_shake(5)
        if g.t % (110 if frac > 0.33 else 70) == 0:
            a = math.atan2(g.player.y - self.y, g.player.x - self.x)
            for i in range(5):
                sa = a + (i - 2) * 0.18
                g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(sa) * 5.2, math.sin(sa) * 5.2, self.dmg * 0.5, 7, (255, 170, 200)))
        if frac < 0.33 and g.t % 8 == 0:
            a = self.rot * 6
            g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 2.6, math.sin(a) * 2.6, self.dmg * 0.4, 6, (255, 220, 240)))
        if frac < 0.66:
            self.flat_timer -= 1
            if self.flat_timer <= 0:
                # «Линия пульса»: горизонтальный луч на высоте игрока
                self.flat_timer = 330 if frac > 0.33 else 240
                g.beams.append(Beam(-20, g.player.y, 0.0, "enemy", self.dmg * 0.7, warn=55, active=14, width=12,
                                    color=(255, 160, 200), length=WIDTH + 40))
        p = g.player
        for ring in self.rings[:]:
            ring["r"] += 4.2 * self.speed_k()
            if ring["r"] > max(WIDTH, HEIGHT):
                self.rings.remove(ring)
                continue
            d = math.hypot(p.x - self.x, p.y - self.y)
            if not ring["hit"] and abs(d - ring["r"]) < 14:
                a = math.atan2(p.y - self.y, p.x - self.x)
                diff = (a - ring["gap"] + math.pi) % (2 * math.pi) - math.pi
                if abs(diff) > ring["w"]:
                    if p.dash_frames > 0:
                        g.perfect_dodge()
                        ring["hit"] = True
                    elif p.take_damage(self.dmg * 0.8, g):
                        ring["hit"] = True

    def draw(self, layer, screen_surf, g):
        size = self.r * (1 + 0.25 * self.beat)
        draw_glow(screen_surf, (self.x, self.y), size * 3.2, (255, 120, 160), int(100 + 120 * self.beat))
        for ring in self.rings:
            alpha = max(30, int(200 * (1 - ring["r"] / max(WIDTH, HEIGHT))))
            g0 = ring["gap"] + ring["w"]
            g1 = ring["gap"] - ring["w"] + 2 * math.pi
            rect = pygame.Rect(0, 0, ring["r"] * 2, ring["r"] * 2)
            rect.center = (self.x, self.y)
            pygame.draw.arc(layer, (255, 180, 210, alpha), rect, -g1, -g0, 6)
        pts = []
        for i in range(10):
            a = self.rot + i * math.pi / 5 - math.pi / 2
            rr = size if i % 2 == 0 else size * 0.45
            pts.append((self.x + math.cos(a) * rr, self.y + math.sin(a) * rr))
        color = (255, 255, 255) if self.flash else (255, 210, 230)
        pygame.draw.polygon(layer, (*color, 245), pts)


BOSSES = [AuroraSerpent, StormEye, HeartStar]
BOSS_NAMES = [("Аврора", "Aurora"), ("Око бури", "Eye of the Storm"), ("Сердце шторма", "Heart of the Storm")]


# =====================================================================
#  Бой
# =====================================================================
class Battle:
    def __init__(self, run, node):
        self.run = run
        self.node = node
        self.player = run.player
        p = self.player
        p.x, p.y = WIDTH / 2, HEIGHT * 0.7
        p.vx = p.vy = 0
        p.trail.clear()
        p.invuln = 60
        p.combo = 0
        p.combo_timer = 0
        p.storm_active = 0
        if run.flags.pop("storm_start", False):
            p.storm = max(p.storm, 50)
        sector = SECTORS[run.sector]
        self.theme = sector["bg"]
        self.bg = Background(self.theme, run.seed + run.sector)
        self.layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.enemies, self.bullets, self.ebullets, self.pickups = [], [], [], []
        self.sparks, self.texts, self.echoes, self.portals, self.trails = [], [], [], [], []
        self.rain_strikes, self.beams, self.missiles, self.mines = [], [], [], []
        self.rocks, self.meteors, self.bubbles, self.rifts = [], [], [], []
        self.t = 0
        self.shake = 0
        self.slowmo = 0
        self.flash = 0
        self.flash_color = (255, 255, 255)
        self.hurt_flash = 0
        self.banner = None
        self.boss = None
        self.target = None
        col = node.col
        self.hp_mult = (1 + 0.12 * col + 0.65 * run.sector) * run.hard_k
        self.dmg_mult = 1 + 0.05 * col + 0.3 * run.sector
        self.waves = self.build_waves()
        self.wave_index = -1
        self.wave_timer = 60
        self.done_timer = 0
        self.result = None
        self.orbit_hits = {}
        self.show_help = run.first_battle
        run.first_battle = False
        self.slow_enemies = run.flags.pop("slow_next", False)
        self.meteor_timer = 360
        self.rock_timer = 700
        if node.type != "boss":
            self.setup_hazards()
        play_music(sector["boss_music"] if node.type == "boss" else sector["music"])

    # --- подготовка ---
    def far_point(self, min_dist=280, margin=90):
        p = self.player
        x, y = WIDTH // 2, HEIGHT // 4
        for _ in range(40):
            x, y = random.randint(margin, WIDTH - margin), random.randint(margin, HEIGHT - margin)
            if math.hypot(x - p.x, y - p.y) > min_dist:
                return x, y
        return x, y

    def add_rock(self, x=None, y=None, r=None):
        r = r or random.randint(int(28 * UI) + 10, int(50 * UI) + 12)
        if x is None:
            x, y = self.far_point(260, r + 20)
        color = (70, 95, 140) if self.theme == "night" else (110, 80, 65)
        self.rocks.append(Rock(x, y, r, r * 2.2 * (1 + 0.3 * self.run.sector), color))

    def setup_hazards(self):
        if self.theme == "night":
            for _ in range(random.randint(3, 5)):
                self.add_rock()
        elif self.theme == "rain":
            for _ in range(2):
                self.add_rock()
        elif self.theme == "dream":
            for _ in range(3):
                x, y = self.far_point(150)
                a = random.uniform(0, 2 * math.pi)
                self.bubbles.append({"x": x, "y": y, "r": random.randint(110, 170) * UI + 20,
                                     "vx": math.cos(a) * 0.35, "vy": math.sin(a) * 0.35, "ph": random.uniform(0, 6)})
            a = (random.uniform(WIDTH * 0.1, WIDTH * 0.3), random.uniform(HEIGHT * 0.2, HEIGHT * 0.8))
            b = (random.uniform(WIDTH * 0.7, WIDTH * 0.9), random.uniform(HEIGHT * 0.2, HEIGHT * 0.8))
            self.rifts.append({"a": list(a), "b": list(b), "rot": 0.0, "pa": [], "pb": [], "cd": 0})

    def build_waves(self):
        node, run = self.node, self.run
        if node.type == "boss":
            return []
        pool = [(k, w) for k, w, min_col in SECTORS[run.sector]["pool"] if node.col >= min_col]
        kinds = [k for k, _ in pool]
        weights = [w for _, w in pool]
        n_waves = 3
        budget = 6 + 2.4 * node.col + 5 * run.sector
        waves = []
        for w in range(n_waves):
            b = budget * (0.8 + 0.25 * w)
            entries = []
            while b > 0:
                kind = random.choices(kinds, weights)[0]
                cost = ENEMY_INFO[kind]["cost"]
                if kind == "swarm":
                    entries += [("swarm", False)] * random.randint(4, 7)
                else:
                    entries.append((kind, False))
                b -= cost
            if node.type == "elite" and w == n_waves - 1:
                elites = [k for k in kinds if k != "swarm"]
                for _ in range(1 + (run.sector >= 1)):
                    entries.append((random.choice(elites), True))
            random.shuffle(entries)
            waves.append(entries)
        return waves

    def open_wave(self):
        self.wave_index += 1
        entries = self.waves[self.wave_index]
        n_portals = min(len(entries), random.randint(2, 3))
        chunks = [entries[i::n_portals] for i in range(n_portals)]
        for chunk in chunks:
            x, y = self.far_point(320)
            self.portals.append(SpawnPortal(x, y, chunk))
        sfx("portal", 0.8)

    def spawn_enemy(self, kind, x, y, elite, parent=None):
        sector = self.run.sector
        if kind == "twins":
            a = Enemy("twins", x - 30, y, elite, self.hp_mult, self.dmg_mult, sector)
            b = Enemy("twins", x + 30, y, elite, self.hp_mult, self.dmg_mult, sector)
            a.partner, b.partner = b, a
            a.is_a = True
            group = [a, b]
        else:
            e = Enemy(kind, x, y, elite, self.hp_mult, self.dmg_mult, sector)
            e.parent = parent
            group = [e]
        for e in group:
            if self.slow_enemies:
                e.slow = 99999
            ang = random.uniform(0, 2 * math.pi)
            e.vx, e.vy = math.cos(ang) * 2, math.sin(ang) * 2
            self.enemies.append(e)

    # --- полезное ---
    def add_shake(self, v):
        if SAVE["shake"]:
            self.shake = max(self.shake, v)

    def add_storm(self, v):
        p = self.player
        if not p.storm_active and p.storm < 100:
            p.storm = min(100.0, p.storm + v * p.stats.storm_rate)
            if p.storm >= 100:
                self.texts.append(FloatText(p.x, p.y - 50, L("ШТОРМ ГОТОВ — E", "STORM READY — E"), (255, 220, 255), 24))
                sfx("level", 0.5)

    def nearest_enemy(self, max_dist=900):
        p = self.player
        best, bd = None, max_dist * max_dist
        for e in self.enemies:
            d = (e.x - p.x) ** 2 + (e.y - p.y) ** 2
            if d < bd:
                best, bd = e, d
        return best

    def zone_factor(self, x, y):
        for b in self.bubbles:
            if (b["x"] - x) ** 2 + (b["y"] - y) ** 2 < b["r"] ** 2:
                return 0.35
        return 1.0

    def kill_enemy(self, e):
        p = self.player
        if e in self.enemies:
            self.enemies.remove(e)
        p.kills += 1
        st = p.stats
        if st.lifesteal:
            p.hp = min(st.max_hp, p.hp + st.lifesteal)
        if st.pulse_recharge:
            p.pulse_timer = max(0, p.pulse_timer - 24 * st.pulse_recharge)
        p.combo += 1
        p.combo_timer = 150
        p.best_combo = max(p.best_combo, p.combo)
        if not e.boss:
            self.add_storm(12 if e.elite else 3)
        total = e.drop * p.dust_mult()
        n = max(1, min(12, int(total)))
        for _ in range(n):
            self.pickups.append(Pickup(e.x, e.y, total / n))
        if random.random() < (0.3 if e.elite else 0.025):
            self.pickups.append(Pickup(e.x, e.y, 0.08, "heal"))
        color = e.color
        for _ in range(int(14 + e.r)):
            self.sparks.append(Spark(e.x, e.y, color, 5 if not e.boss else 9, 40, 3))
        self.echoes.append(EchoWave(e.x, e.y, e.r * 4, color, 2))
        sfx("boom", 0.5 if not e.boss else 1.0, 60)
        if "splitter" in e.affixes:
            for i in range(2):
                child = Enemy(e.kind, e.x + (i * 2 - 1) * 20, e.y, False, self.hp_mult * 0.6, self.dmg_mult, self.run.sector)
                child.r *= 0.8
                self.enemies.append(child)
        if "explosive" in e.affixes:
            for i in range(14):
                a = i * 2 * math.pi / 14
                self.ebullets.append(EnemyBullet(e.x, e.y, math.cos(a) * 3.8, math.sin(a) * 3.8, e.dmg * 0.6, 7, (255, 110, 80)))
        if e.kind == "twins" and e.partner is not None and e.partner.hp > 0:
            e.partner.enraged = True
            self.texts.append(FloatText(e.partner.x, e.partner.y - 20, L("ЯРОСТЬ", "ENRAGED"), (255, 140, 120), 16))
        if e.boss:
            self.add_shake(30)
            self.slowmo = 60
            for _ in range(120):
                self.sparks.append(Spark(e.x, e.y, random.choice([WHITE, GOLD, PORTAL_PURPLE]), 12, 80, 4))

    def damage_enemy(self, e, dmg, crit=False, from_bullet=True):
        if e.hp <= 0:
            return
        if e.shield > 0:
            absorbed = min(e.shield, dmg)
            e.shield -= absorbed
            dmg -= absorbed
            e.shield_cd = 180
            if dmg <= 0:
                e.flash = 2
                return
        e.hp -= dmg
        e.flash = 4
        e.since_hit = 0
        if e.boss:
            self.add_storm(min(2.0, dmg * 0.012))
        if from_bullet and random.random() < self.player.stats.freeze:
            e.slow = max(e.slow, 120)
        if SAVE["numbers"]:
            self.texts.append(FloatText(e.x, e.y - e.r, str(int(dmg)), GOLD if crit else (220, 220, 255), 22 if crit else 16))
        if e.hp <= 0:
            self.kill_enemy(e)
        else:
            sfx("hit", 0.4, 40)

    def area_damage(self, x, y, radius, dmg, color, hurt_player=0):
        self.echoes.append(EchoWave(x, y, radius, color, 3))
        for _ in range(18):
            self.sparks.append(Spark(x, y, color, 6, 30, 3))
        for e in self.enemies[:]:
            if math.hypot(e.x - x, e.y - y) < radius + e.r:
                self.damage_enemy(e, dmg, False, False)
        for rock in self.rocks[:]:
            if math.hypot(rock.x - x, rock.y - y) < radius + rock.r:
                self.damage_rock(rock, dmg)
        if hurt_player and math.hypot(self.player.x - x, self.player.y - y) < radius:
            self.player.take_damage(hurt_player, self)

    def damage_rock(self, rock, dmg):
        rock.hp -= dmg
        rock.flash = 3
        if rock.hp <= 0 and rock in self.rocks:
            self.rocks.remove(rock)
            for _ in range(20):
                self.sparks.append(Spark(rock.x, rock.y, lerp_color(rock.color, (255, 255, 255), 0.4), 5, 35, 3))
            for _ in range(int(rock.r // 12) + 1):
                self.pickups.append(Pickup(rock.x, rock.y, 1))
            sfx("boom", 0.4, 60)
            if rock.r > 30:
                for _ in range(2):
                    child = Rock(rock.x + random.uniform(-10, 10), rock.y + random.uniform(-10, 10), rock.r * 0.6,
                                 rock.max_hp * 0.4, rock.color)
                    child.vx *= 2.5
                    child.vy *= 2.5
                    self.rocks.append(child)

    def explode_mine(self, m):
        if m not in self.mines:
            return
        self.mines.remove(m)
        sfx("mine", 0.7, 50)
        self.add_shake(6)
        self.area_damage(m["x"], m["y"], 90, 30, (255, 150, 60), m["dmg"])

    # --- действия игрока ---
    def compute_aim(self, mv):
        p = self.player
        if SAVE["controls"] == "classic":
            mx, my = pygame.mouse.get_pos()
            self.target = None
            return math.atan2(my - p.y, mx - p.x)
        _, _, rx, ry = pad_axes()
        if abs(rx) > 0.35 or abs(ry) > 0.35:
            INPUT["pad"] = True
            self.target = None
            return math.atan2(ry, rx)
        if SAVE["aim"] == "auto" or INPUT["pad"]:
            t = self.nearest_enemy(1000)
            self.target = t
            if t is not None:
                return math.atan2(t.y - p.y, t.x - p.x)
            if mv[0] or mv[1]:
                return math.atan2(mv[1], mv[0])
            return p.angle
        self.target = None
        mx, my = pygame.mouse.get_pos()
        return math.atan2(my - p.y, mx - p.x)

    def try_dash(self):
        p = self.player
        if p.dash_timer > 0 or p.dash_frames > 0:
            return
        st = p.stats
        mv = move_vector()
        if SAVE["controls"] != "classic" and (mv[0] or mv[1]):
            a = math.atan2(mv[1], mv[0])
        else:
            a = p.angle
        p.dash_timer = int(st.dash_cd)
        p.dash_frames = 9
        p.dash_dir = (math.cos(a), math.sin(a))
        p.dash_hits = set()
        p.dodged = False
        sfx("dash", 0.9)
        self.echoes.append(EchoWave(p.x, p.y, 60))

    def try_pulse(self):
        p = self.player
        if p.pulse_timer > 0:
            return
        st = p.stats
        p.pulse_timer = int(st.pulse_cd)
        sfx("pulse", 1.0)
        self.add_shake(8)
        for i in range(4):
            w = EchoWave(p.x, p.y, st.pulse_radius * (1 - i * 0.15), (100, 150, 255), 3)
            w.lifetime = -i * 4
            self.echoes.append(w)
        for e in self.enemies[:]:
            d = math.hypot(e.x - p.x, e.y - p.y)
            if d < st.pulse_radius + e.r:
                if not e.boss:
                    a = math.atan2(e.y - p.y, e.x - p.x)
                    e.vx += math.cos(a) * 9
                    e.vy += math.sin(a) * 9
                self.damage_enemy(e, st.pulse_dmg * p.damage_mult(), False, False)
        for m in self.mines[:]:
            if math.hypot(m["x"] - p.x, m["y"] - p.y) < st.pulse_radius:
                self.explode_mine(m)
        self.ebullets = [b for b in self.ebullets if math.hypot(b.x - p.x, b.y - p.y) > st.pulse_radius]

    def try_storm(self):
        p = self.player
        if p.storm < 100 or p.storm_active:
            return
        p.storm = 0
        p.storm_active = int(p.stats.storm_dur)
        self.bg.dream_override = True
        self.flash = 30
        self.flash_color = (200, 160, 255)
        self.add_shake(14)
        sfx("storm", 1.0)
        for i in range(6):
            w = EchoWave(p.x, p.y, 200 + i * 70, rainbow(i / 6), 3)
            w.lifetime = -i * 5
            self.echoes.append(w)
        self.banner = {"text": L("ЗВЁЗДНЫЙ ШТОРМ", "STAR STORM"), "sub": "", "t": 0, "dur": 90, "color": (235, 210, 255)}

    def perfect_dodge(self):
        p = self.player
        if p.dodged:
            return
        p.dodged = True
        self.slowmo = 36
        p.dash_timer = int(p.dash_timer * 0.5)
        self.add_storm(8)
        sfx("dodge", 0.9)
        self.texts.append(FloatText(p.x, p.y - 40, L("УКЛОНЕНИЕ!", "PERFECT DODGE!"), (180, 255, 255), 24))
        self.echoes.append(EchoWave(p.x, p.y, 120, (180, 255, 255), 2))
        if p.stats.reflector:
            for b in self.ebullets[:]:
                if math.hypot(b.x - p.x, b.y - p.y) < 170:
                    self.ebullets.remove(b)
                    a = math.atan2(b.y - p.y, b.x - p.x)
                    self.bullets.append(Bullet(b.x, b.y, a, p.stats.bullet_speed, p.stats.damage * 1.5, 0, False, False, 0))

    def player_fire(self):
        p = self.player
        st = p.stats
        n = st.multishot
        spread = 0.13
        dm = p.damage_mult()
        for i in range(n):
            a = p.angle + (i - (n - 1) / 2) * spread
            crit = random.random() < st.crit
            dmg = st.damage * dm * (st.crit_mult if crit else 1)
            p.shot_count += 1
            echo = st.echo_shots > 0 and p.shot_count % max(2, 7 - st.echo_shots) == 0
            tip_x = p.x + math.cos(p.angle) * 14 * st.size
            tip_y = p.y + math.sin(p.angle) * 14 * st.size
            b = Bullet(tip_x, tip_y, a, st.bullet_speed, dmg, st.pierce, crit, echo, st.ricochet, st.prism)
            b.rainbow = p.storm_active > 0
            self.bullets.append(b)
        sfx("shot", 0.35, 50)

    # --- обновление ---
    def update(self):
        self.t += 1
        self.update_player()
        self.update_weapons()
        self.update_waves()
        self.update_enemies()
        self.update_player_bullets()
        self.update_enemy_bullets()
        self.update_hazards()
        self.update_pickups()
        self.update_fx()
        self.check_outcome()

    def update_player(self):
        p = self.player
        st = p.stats
        mv = move_vector()
        p.angle = self.compute_aim(mv)
        classic = SAVE["controls"] == "classic"
        max_speed = st.max_speed * (1.15 if p.storm_active else 1.0)
        if classic:
            keys = pygame.key.get_pressed()
            p.thrusting = keys[pygame.K_w] or keys[pygame.K_UP] or pygame.mouse.get_pressed()[0]
            if p.thrusting:
                p.vx += st.thrust * math.cos(p.angle)
                p.vy += st.thrust * math.sin(p.angle)
            else:
                p.vx *= 0.95
                p.vy *= 0.95
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                p.vx *= 0.85
                p.vy *= 0.85
            p.move_angle = p.angle
        else:
            if mv[0] or mv[1]:
                p.vx += mv[0] * st.thrust * 1.5
                p.vy += mv[1] * st.thrust * 1.5
                p.thrusting = True
                p.move_angle = math.atan2(mv[1], mv[0])
            else:
                p.vx *= 0.86
                p.vy *= 0.86
                p.thrusting = False
        sp = math.hypot(p.vx, p.vy)
        if sp > max_speed:
            p.vx *= max_speed / sp
            p.vy *= max_speed / sp
        prev = (p.x, p.y)
        if p.dash_frames > 0:
            p.dash_frames -= 1
            step = st.dash_dist / 9
            p.x += p.dash_dir[0] * step
            p.y += p.dash_dir[1] * step
            if st.dream_dash:
                self.trails.append([p.x, p.y, 70, None, 6])
            p.vx, p.vy = p.dash_dir[0] * max_speed, p.dash_dir[1] * max_speed
            # уклонение: вражеская пуля или луч рядом во время рывка
            if not p.dodged:
                for b in self.ebullets:
                    if (b.x - p.x) ** 2 + (b.y - p.y) ** 2 < (b.r + 30) ** 2:
                        self.perfect_dodge()
                        break
            if not p.dodged:
                for bm in self.beams:
                    if bm.owner == "enemy" and bm.live:
                        (x1, y1), (x2, y2) = bm.ends()
                        if seg_dist(p.x, p.y, x1, y1, x2, y2) < bm.width + 22:
                            self.perfect_dodge()
                            break
            if st.dash_strike:
                for e in self.enemies[:]:
                    if e.id not in p.dash_hits and e.hit_test(p.x, p.y, 22):
                        p.dash_hits.add(e.id)
                        self.damage_enemy(e, st.damage * 3.5 * p.damage_mult(), True, False)
        else:
            p.x += p.vx
            p.y += p.vy
        p.x = max(20, min(WIDTH - 20, p.x))
        p.y = max(20, min(HEIGHT - 20, p.y))
        # разломы снов: телепорт между парными порталами
        for rf in self.rifts:
            if rf["cd"] > 0:
                continue
            for src, dst in (("a", "b"), ("b", "a")):
                if math.hypot(p.x - rf[src][0], p.y - rf[src][1]) < 34:
                    self.echoes.append(EchoWave(p.x, p.y, 70, PORTAL_PURPLE, 2))
                    p.x, p.y = rf[dst][0], rf[dst][1]
                    rf["cd"] = 90
                    for i in range(4):
                        w = EchoWave(p.x, p.y, 60 + i * 25, PORTAL_PURPLE, 2)
                        w.lifetime = -i * 4
                        self.echoes.append(w)
                    sfx("portal", 0.7)
                    break
        dx, dy = p.x - prev[0], p.y - prev[1]
        if abs(dx) > 60 or abs(dy) > 60:
            dx, dy = 0, 0
        self.bg.update(dx, dy)
        p.trail.append((p.x, p.y))
        if len(p.trail) > 120:
            p.trail.pop(0)
        for attr in ("dash_timer", "pulse_timer", "invuln"):
            if getattr(p, attr) > 0:
                setattr(p, attr, getattr(p, attr) - 1)
        p.since_hit += 1
        if st.shield_max and p.since_hit > 180 and p.shield < st.shield_max:
            p.shield = min(st.shield_max, p.shield + st.shield_max / 240)
        if p.combo_timer > 0:
            p.combo_timer -= 1
            if p.combo_timer == 0:
                p.combo = 0
        if p.storm_active:
            p.storm_active -= 1
            if self.t % 14 == 0 and self.enemies:
                self.add_star_strike(random.choice(self.enemies), 2.5)
            if p.storm_active == 0:
                self.bg.dream_override = False

    def add_star_strike(self, target, mult):
        self.rain_strikes.append({"x": target.x - 250, "y": -40, "tx": target.x, "ty": target.y, "k": 0.0,
                                  "trail": [], "mult": mult})

    def update_weapons(self):
        p = self.player
        st = p.stats
        dm = p.damage_mult()
        p.fire_timer -= 1
        if p.fire_timer <= 0 and (self.enemies or self.boss):
            p.fire_timer = p.fire_delay()
            self.player_fire()
        p.orbit_angle += 0.055
        if st.star_rain and self.enemies and self.t % max(40, int(170 / st.star_rain)) == 0:
            self.add_star_strike(random.choice(self.enemies), 3)
        for s in self.rain_strikes[:]:
            s["k"] += 0.05
            s["x"] = (s["tx"] - 250) + 250 * s["k"]
            s["y"] = -40 + (s["ty"] + 40) * s["k"]
            s["trail"].append((s["x"], s["y"]))
            del s["trail"][:-12]
            if s["k"] >= 1:
                self.rain_strikes.remove(s)
                self.area_damage(s["tx"], s["ty"], 90, st.damage * s["mult"] * dm, SHOOTING_STAR_COLOR)
        if st.missiles and self.enemies:
            p.missile_timer -= 1
            if p.missile_timer <= 0:
                p.missile_timer = max(50, 140 - 25 * (st.missiles - 1))
                for i in range(st.missiles):
                    a = p.angle + math.pi + (i - (st.missiles - 1) / 2) * 0.6
                    self.missiles.append(Missile(p.x, p.y, a))
                sfx("missile", 0.5, 100)
        for m in self.missiles[:]:
            m.life -= 1
            target, bd = None, 1e12
            for e in self.enemies:
                d = (e.x - m.x) ** 2 + (e.y - m.y) ** 2
                if d < bd:
                    target, bd = e, d
            spd = math.hypot(m.vx, m.vy)
            cur = math.atan2(m.vy, m.vx)
            if target is not None:
                want = math.atan2(target.y - m.y, target.x - m.x)
                diff = (want - cur + math.pi) % (2 * math.pi) - math.pi
                cur += max(-0.13, min(0.13, diff))
            spd = min(11, spd + 0.3)
            m.vx, m.vy = math.cos(cur) * spd, math.sin(cur) * spd
            m.x += m.vx
            m.y += m.vy
            m.trail.append((m.x, m.y))
            del m.trail[:-10]
            hit = target is not None and target.hit_test(m.x, m.y, 8)
            if hit or m.life <= 0 or not (0 < m.x < WIDTH and 0 < m.y < HEIGHT):
                self.missiles.remove(m)
                self.area_damage(m.x, m.y, 75, st.damage * 2.2 * dm, (255, 160, 90))
        if st.beam and self.enemies:
            p.beam_timer -= 1
            if p.beam_timer <= 0:
                p.beam_timer = max(120, 260 - 70 * (st.beam - 1))
                self.beams.append(Beam(p.x, p.y, p.angle, "player", st.damage * 5 * dm, warn=14, active=10, width=16,
                                       color=(170, 220, 255), follow=p))

    def update_waves(self):
        if not self.boss and self.node.type == "boss" and self.t == 90:
            self.boss = BOSSES[self.run.sector](1.3 * self.hp_mult / (1 + 0.12 * self.node.col), self.dmg_mult)
            self.enemies.append(self.boss)
            sfx("portal", 1.0)
            self.add_shake(20)
            self.banner = {"text": self.boss.name, "sub": self.boss.sub, "t": 0, "dur": 200, "color": (255, 220, 240)}
        if self.node.type != "boss" and self.wave_index < len(self.waves) - 1:
            alive = len(self.enemies) + sum(len(pt.queue) for pt in self.portals)
            self.wave_timer -= 1
            if self.wave_timer <= 0 and (alive <= 2 or self.wave_timer < -1500):
                self.open_wave()
                self.wave_timer = 150

    def orbit_positions(self):
        p = self.player
        n = p.stats.orbitals
        return [(p.x + math.cos(p.orbit_angle + i * 2 * math.pi / n) * 75,
                 p.y + math.sin(p.orbit_angle + i * 2 * math.pi / n) * 75) for i in range(n)]

    def update_enemies(self):
        p = self.player
        st = p.stats
        orbit_pos = self.orbit_positions()
        for e in self.enemies[:]:
            if e.hp <= 0:
                continue
            e.zone_k = self.zone_factor(e.x, e.y) if self.bubbles else 1.0
            e.update(self)
            if p.dash_frames == 0 and e.hit_test(p.x, p.y, 10 * st.size * 0.8):
                if p.take_damage(e.dmg, self) and not e.boss:
                    a = math.atan2(p.y - e.y, p.x - e.x)
                    p.vx += math.cos(a) * 6
                    p.vy += math.sin(a) * 6
                    self.damage_enemy(e, st.damage, False, False)
            for i, (ox, oy) in enumerate(orbit_pos):
                if e.hp > 0 and e.hit_test(ox, oy, 9):
                    key = (e.id, i)
                    if self.t - self.orbit_hits.get(key, -999) > 20:
                        self.orbit_hits[key] = self.t
                        self.damage_enemy(e, st.damage * 0.8 * p.damage_mult(), False, False)
        for pt in self.portals[:]:
            if not pt.update(self):
                self.portals.remove(pt)
        for bm in self.beams[:]:
            if not bm.update():
                self.beams.remove(bm)
                continue
            if not bm.live:
                continue
            (x1, y1), (x2, y2) = bm.ends()
            if bm.owner == "enemy":
                if "p" not in bm.hit and p.dash_frames == 0 and seg_dist(p.x, p.y, x1, y1, x2, y2) < bm.width / 2 + 8:
                    if p.take_damage(bm.dmg, self):
                        bm.hit.add("p")
            else:
                for e in self.enemies[:]:
                    if e.id not in bm.hit and seg_dist(e.x, e.y, x1, y1, x2, y2) < bm.width / 2 + e.r:
                        bm.hit.add(e.id)
                        self.damage_enemy(e, bm.dmg, True, False)
                for rock in self.rocks[:]:
                    if id(rock) not in bm.hit and seg_dist(rock.x, rock.y, x1, y1, x2, y2) < bm.width / 2 + rock.r:
                        bm.hit.add(id(rock))
                        self.damage_rock(rock, bm.dmg)

    def update_player_bullets(self):
        p = self.player
        st = p.stats
        homing = st.homing + (1 if p.storm_active else 0)
        for b in self.bullets[:]:
            if homing and self.enemies:
                best, bd = None, 340 ** 2
                for e in self.enemies:
                    d = (e.x - b.x) ** 2 + (e.y - b.y) ** 2
                    if d < bd and e.id not in b.hit_ids:
                        best, bd = e, d
                if best:
                    cur = math.atan2(b.vy, b.vx)
                    want = math.atan2(best.y - b.y, best.x - b.x)
                    diff = (want - cur + math.pi) % (2 * math.pi) - math.pi
                    cur += max(-0.07 * homing, min(0.07 * homing, diff))
                    spd = math.hypot(b.vx, b.vy)
                    b.vx, b.vy = math.cos(cur) * spd, math.sin(cur) * spd
            b.x += b.vx
            b.y += b.vy
            b.life -= 1
            b.trail.append((b.x, b.y))
            if len(b.trail) > 6:
                b.trail.pop(0)
            if b.x < 0 or b.x > WIDTH or b.y < 0 or b.y > HEIGHT:
                if b.bounces > 0:
                    b.bounces -= 1
                    if b.x < 0 or b.x > WIDTH:
                        b.vx = -b.vx
                    if b.y < 0 or b.y > HEIGHT:
                        b.vy = -b.vy
                    b.x = max(0, min(WIDTH, b.x))
                    b.y = max(0, min(HEIGHT, b.y))
                    b.life = max(b.life, 40)
                else:
                    b.life = 0
            if b.life <= 0:
                self.bullets.remove(b)
                continue
            gone = False
            for rock in self.rocks:
                if (rock.x - b.x) ** 2 + (rock.y - b.y) ** 2 < (rock.r * 0.9 + b.r) ** 2:
                    self.damage_rock(rock, b.dmg)
                    self.sparks.append(Spark(b.x, b.y, (200, 220, 255), 3, 12, 2))
                    gone = True
                    break
            if not gone:
                for m in self.mines:
                    if (m["x"] - b.x) ** 2 + (m["y"] - b.y) ** 2 < 14 ** 2:
                        self.explode_mine(m)
                        gone = True
                        break
            if gone:
                if b in self.bullets:
                    self.bullets.remove(b)
                continue
            for e in self.enemies[:]:
                if e.id in b.hit_ids or e.hp <= 0:
                    continue
                if e.hit_test(b.x, b.y, b.r):
                    if e.reflects(b.x, b.y):
                        a = math.atan2(-b.vy, -b.vx) + random.uniform(-0.2, 0.2)
                        self.ebullets.append(EnemyBullet(b.x, b.y, math.cos(a) * 6, math.sin(a) * 6, e.dmg * 0.6, 5, (230, 245, 255)))
                        sfx("reflect", 0.4, 60)
                        if b in self.bullets:
                            self.bullets.remove(b)
                        break
                    b.hit_ids.add(e.id)
                    self.damage_enemy(e, b.dmg, b.crit)
                    for _ in range(3):
                        self.sparks.append(Spark(b.x, b.y, SHOOTING_STAR_COLOR, 3, 14, 2))
                    if b.echo:
                        self.echoes.append(EchoWave(b.x, b.y, 85, (100, 150, 255), 2))
                        for e2 in self.enemies[:]:
                            if e2 is not e and math.hypot(e2.x - b.x, e2.y - b.y) < 85 + e2.r:
                                self.damage_enemy(e2, b.dmg * 0.6, False, False)
                    if b.prism:
                        b.prism = False
                        heading = math.atan2(b.vy, b.vx)
                        for da in (-0.55, 0.0, 0.55):
                            shard = Bullet(b.x, b.y, heading + da, st.bullet_speed * 0.9, b.dmg * 0.4, 0, False, False, 0,
                                           False, 40)
                            shard.hit_ids = set(b.hit_ids)
                            self.bullets.append(shard)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        if b in self.bullets:
                            self.bullets.remove(b)
                        break

    def update_enemy_bullets(self):
        p = self.player
        st = p.stats
        orbit_pos = self.orbit_positions()
        for b in self.ebullets[:]:
            k = self.zone_factor(b.x, b.y) if self.bubbles else 1.0
            b.x += b.vx * k
            b.y += b.vy * k
            b.life -= 1
            if b.life <= 0 or b.x < -60 or b.x > WIDTH + 60 or b.y < -60 or b.y > HEIGHT + 60:
                self.ebullets.remove(b)
                continue
            blocked = False
            for ox, oy in orbit_pos:
                if (ox - b.x) ** 2 + (oy - b.y) ** 2 < (b.r + 9) ** 2:
                    blocked = True
                    break
            if not blocked:
                for rock in self.rocks:
                    if (rock.x - b.x) ** 2 + (rock.y - b.y) ** 2 < (rock.r * 0.9 + b.r) ** 2:
                        blocked = True
                        rock.flash = 2
                        break
            if blocked:
                self.ebullets.remove(b)
                self.sparks.append(Spark(b.x, b.y, b.color, 3, 12, 2))
                continue
            if (p.x - b.x) ** 2 + (p.y - b.y) ** 2 < (b.r + 8 * st.size * 0.8) ** 2:
                if p.take_damage(b.dmg, self):
                    self.ebullets.remove(b)

    def update_hazards(self):
        p = self.player
        for rock in self.rocks:
            rock.update()
            if p.dash_frames == 0 and (rock.x - p.x) ** 2 + (rock.y - p.y) ** 2 < (rock.r * 0.9 + 10) ** 2:
                a = math.atan2(p.y - rock.y, p.x - rock.x)
                p.vx += math.cos(a) * 5
                p.vy += math.sin(a) * 5
                p.x = max(20, min(WIDTH - 20, rock.x + math.cos(a) * (rock.r * 0.9 + 12)))
                p.y = max(20, min(HEIGHT - 20, rock.y + math.sin(a) * (rock.r * 0.9 + 12)))
                p.take_damage(8 * self.dmg_mult, self)
        if self.theme == "night" and self.node.type != "boss" and len(self.rocks) < 2 and self.done_timer == 0:
            self.rock_timer -= 1
            if self.rock_timer <= 0:
                self.rock_timer = 700
                self.add_rock()
        if self.theme == "rain" and self.node.type != "boss" and self.result is None and self.done_timer == 0:
            self.meteor_timer -= 1
            if self.meteor_timer <= 0:
                self.meteor_timer = random.randint(280, 420)
                for i in range(random.randint(2, 4)):
                    if i == 0:
                        x, y = p.x + random.uniform(-80, 80), p.y + random.uniform(-80, 80)
                    else:
                        x, y = random.uniform(80, WIDTH - 80), random.uniform(80, HEIGHT - 80)
                    self.meteors.append({"x": x, "y": y, "t": 80 + i * 12, "max": 80 + i * 12, "r": 90})
        for m in self.meteors[:]:
            m["t"] -= 1
            if m["t"] <= 0:
                self.meteors.remove(m)
                sfx("meteor", 0.8, 80)
                self.add_shake(9)
                self.area_damage(m["x"], m["y"], m["r"], 45, (255, 190, 120), 18 * self.dmg_mult)
        for mine in self.mines[:]:
            mine["arm"] -= 1
            mine["life"] -= 1
            if mine["arm"] <= 0 and math.hypot(mine["x"] - p.x, mine["y"] - p.y) < 75:
                self.explode_mine(mine)
            elif mine["life"] <= 0:
                self.explode_mine(mine)
        for b in self.bubbles:
            b["x"] += b["vx"]
            b["y"] += b["vy"]
            b["ph"] += 0.03
            if b["x"] < b["r"] * 0.5 or b["x"] > WIDTH - b["r"] * 0.5:
                b["vx"] = -b["vx"]
            if b["y"] < b["r"] * 0.5 or b["y"] > HEIGHT - b["r"] * 0.5:
                b["vy"] = -b["vy"]
        for rf in self.rifts:
            rf["rot"] += 0.06
            if rf["cd"] > 0:
                rf["cd"] -= 1
            update_portal_particles(rf["pa"], rf["a"][0], rf["a"][1], 32)
            update_portal_particles(rf["pb"], rf["b"][0], rf["b"][1], 32)

    def update_pickups(self):
        p = self.player
        st = p.stats
        for pk in self.pickups[:]:
            d = math.hypot(p.x - pk.x, p.y - pk.y)
            if d < st.magnet or self.done_timer > 0:
                a = math.atan2(p.y - pk.y, p.x - pk.x)
                pull = 0.9 if self.done_timer == 0 else 1.6
                pk.vx += math.cos(a) * pull
                pk.vy += math.sin(a) * pull
            pk.vx *= 0.92
            pk.vy *= 0.92
            pk.x += pk.vx
            pk.y += pk.vy
            if d < 22:
                self.pickups.remove(pk)
                if pk.kind == "heal":
                    heal = st.max_hp * pk.value
                    p.hp = min(st.max_hp, p.hp + heal)
                    self.texts.append(FloatText(p.x, p.y - 30, f"+{int(heal)}", HEAL_GREEN, 18))
                    sfx("shield", 0.6)
                else:
                    p.dust += pk.value
                    p.xp += pk.value
                    sfx("pickup", 0.4, 45)

    def update_fx(self):
        for s in self.sparks[:]:
            s.x += s.vx
            s.y += s.vy
            s.vx *= 0.95
            s.vy *= 0.95
            s.life -= 1
            if s.life <= 0:
                self.sparks.remove(s)
        for tr in self.trails[:]:
            tr[2] -= 1
            if tr[3] is None and self.t % 6 == 0:
                for e in self.enemies[:]:
                    if e.hit_test(tr[0], tr[1], 12):
                        self.damage_enemy(e, self.player.stats.damage * 0.5, False, False)
            if tr[2] <= 0:
                self.trails.remove(tr)
        self.texts = [t for t in self.texts if t.update()]
        self.echoes = [w for w in self.echoes if w.update()]
        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.hurt_flash > 0:
            self.hurt_flash -= 1
        if self.banner:
            self.banner["t"] += 1
            if self.banner["t"] > self.banner["dur"]:
                self.banner = None

    def check_outcome(self):
        p = self.player
        if p.hp <= 0:
            if p.revive:
                p.revive = False
                p.hp = p.stats.max_hp * 0.5
                p.invuln = 180
                self.texts.append(FloatText(p.x, p.y - 40, L("ВТОРОЙ ШАНС", "SECOND CHANCE"), GOLD, 30))
                p.pulse_timer = 0
                self.try_pulse()
            else:
                self.result = "dead"
                return
        cleared = (not self.enemies and not self.portals and
                   (self.node.type == "boss" and self.boss is not None or
                    self.node.type != "boss" and self.wave_index >= len(self.waves) - 1))
        if cleared:
            if self.done_timer == 0:
                self.mines.clear()
                self.meteors.clear()
                self.beams.clear()
            self.done_timer += 1
            if self.done_timer > 100 and not any(pk.kind == "dust" for pk in self.pickups):
                self.result = "win"

    # --- отрисовка ---
    def draw(self):
        p = self.player
        st = p.stats
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        self.bg.draw(screen, layer, p.x, p.y)
        for b in self.bubbles:
            r = int(b["r"] + 4 * math.sin(b["ph"]))
            pygame.draw.circle(layer, (150, 110, 230, 22), (int(b["x"]), int(b["y"])), r)
            pygame.draw.circle(layer, (190, 150, 255, 110), (int(b["x"]), int(b["y"])), r, 2)
            rect = pygame.Rect(0, 0, r * 1.5, r * 1.5)
            rect.center = (b["x"], b["y"])
            pygame.draw.arc(layer, (230, 210, 255, 120), rect, b["ph"], b["ph"] + 1.2, 2)
        for rf in self.rifts:
            for key, parts in (("a", rf["pa"]), ("b", rf["pb"])):
                k = 0.45 if rf["cd"] > 0 else 1.0
                draw_glow(screen, rf[key], 70, (60, 30, 120), int(120 * k))
                draw_portal(layer, rf[key][0], rf[key][1], 32, rf["rot"], math.sin(rf["rot"] * 2) * 4, parts, k)
        n = len(p.trail)
        for i, (x, y) in enumerate(p.trail):
            alpha = int(150 * (i / n) ** 1.5)
            col = rainbow(i / 40 + self.t * 0.01) if p.storm_active else GLOW_BLUE
            pygame.draw.circle(layer, (*col, alpha), (int(x), int(y)), 2)
        for tr in self.trails:
            if tr[3] is None:
                hue = (tr[0] * 0.002 + pygame.time.get_ticks() * 0.0005) % 1
                r, g, b = hue_to_rgb(hue)
                pygame.draw.circle(layer, (int(r * 255), int(g * 255), int(b * 255), int(180 * tr[2] / 70)), (int(tr[0]), int(tr[1])), tr[4])
            else:
                pygame.draw.circle(layer, (*tr[3], int(140 * tr[2] / 18)), (int(tr[0]), int(tr[1])), tr[4])
        for m in self.meteors:
            k = 1 - m["t"] / m["max"]
            pygame.draw.circle(layer, (255, 90, 60, int(25 + 50 * k)), (int(m["x"]), int(m["y"])), m["r"])
            pygame.draw.circle(layer, (255, 140, 100, 200), (int(m["x"]), int(m["y"])), m["r"], 2)
            pygame.draw.circle(layer, (255, 200, 160, 220), (int(m["x"]), int(m["y"])), max(2, int(m["r"] * (1 - k))), 1)
            if m["t"] < 16:
                f = m["t"] / 16
                hx, hy = m["x"] - 320 * f, m["y"] - 520 * f
                pygame.draw.line(layer, (255, 230, 180, 220), (hx - 60, hy - 100), (hx, hy), 4)
                pygame.draw.circle(layer, (255, 255, 220, 255), (int(hx), int(hy)), 7)
                draw_glow(screen, (hx, hy), 40, (200, 140, 60), 160)
        for rock in self.rocks:
            rock.draw(layer)
        for pt in self.portals:
            pt.draw(layer)
        for mine in self.mines:
            armed = mine["arm"] <= 0
            blink = armed and (self.t // 8) % 2 == 0
            col = (255, 80, 60) if blink else (255, 170, 60)
            pts = [(mine["x"] + math.cos(self.t * 0.05 + i * math.pi / 3) * (9 if i % 2 == 0 else 5),
                    mine["y"] + math.sin(self.t * 0.05 + i * math.pi / 3) * (9 if i % 2 == 0 else 5)) for i in range(6)]
            pygame.draw.polygon(layer, (*col, 240), pts)
            if armed:
                pygame.draw.circle(layer, (255, 120, 80, 50), (int(mine["x"]), int(mine["y"])), 75, 1)
        for pk in self.pickups:
            if pk.kind == "heal":
                pygame.draw.circle(layer, (*HEAL_GREEN, 240), (int(pk.x), int(pk.y)), 6)
                pygame.draw.line(layer, (20, 60, 30, 255), (pk.x - 3, pk.y), (pk.x + 3, pk.y), 2)
                pygame.draw.line(layer, (20, 60, 30, 255), (pk.x, pk.y - 3), (pk.x, pk.y + 3), 2)
                draw_glow(screen, (pk.x, pk.y), 16, (40, 140, 70), 140)
                continue
            tw = 0.6 + 0.4 * math.sin(self.t * 0.15 + pk.phase)
            pygame.draw.circle(layer, (255, 230, 150, int(220 * tw)), (int(pk.x), int(pk.y)), 3)
            draw_glow(screen, (pk.x, pk.y), 10, (180, 150, 60), 120)
        for e in self.enemies:
            e.draw(layer, screen, self)
        for bm in self.beams:
            bm.draw(layer)
        for b in self.ebullets:
            draw_glow(screen, (b.x, b.y), b.r * 2.6, b.color, 110)
            pygame.draw.circle(layer, (*b.color, 240), (int(b.x), int(b.y)), b.r)
            pygame.draw.circle(layer, (255, 255, 255, 220), (int(b.x), int(b.y)), max(1, b.r // 2))
        for b in self.bullets:
            if b.rainbow:
                col = rainbow(self.t * 0.02 + b.x * 0.002)
            else:
                col = GOLD if b.crit else SHOOTING_STAR_COLOR
            for i, (x, y) in enumerate(b.trail):
                pygame.draw.circle(layer, (*col, 40 + 25 * i), (int(x), int(y)), 1 + i // 2)
            pygame.draw.circle(layer, (*col, 255), (int(b.x), int(b.y)), 4 if not b.echo else 5)
            draw_glow(screen, (b.x, b.y), 12, (120, 120, 80), 120)
        for m in self.missiles:
            for i, (x, y) in enumerate(m.trail):
                pygame.draw.circle(layer, (255, 140, 60, 30 + 18 * i), (int(x), int(y)), 1 + i // 3)
            pygame.draw.circle(layer, (255, 240, 200, 255), (int(m.x), int(m.y)), 4)
            draw_glow(screen, (m.x, m.y), 18, (180, 90, 30), 140)
        for s in self.rain_strikes:
            for i, (x, y) in enumerate(s["trail"]):
                pygame.draw.circle(layer, SHOOTING_STAR_COLOR, (int(x), int(y)), 2 + i // 4)
        for s in self.sparks:
            pygame.draw.circle(layer, (*s.color, int(255 * s.life / s.max_life)), (int(s.x), int(s.y)), s.size)
        for w in self.echoes:
            w.draw(layer)
        for ox, oy in self.orbit_positions():
            draw_glow(screen, (ox, oy), 18, (150, 150, 120), 140)
            pts = []
            for k in range(10):
                aa = p.orbit_angle * 3 + k * math.pi / 5
                rr = 9 if k % 2 == 0 else 4
                pts.append((ox + math.cos(aa) * rr, oy + math.sin(aa) * rr))
            pygame.draw.polygon(layer, (*SHOOTING_STAR_COLOR, 255), pts)
        # корабль
        blink = p.invuln > 0 and (self.t // 4) % 2 == 0
        if p.stats.night_fury and p.hp < p.stats.max_hp * 0.35:
            draw_glow(screen, (p.x, p.y), 50, (200, 40, 60), 120)
        if p.storm_active:
            draw_glow(screen, (p.x, p.y), 60, rainbow(self.t * 0.01, 140), 160)
        if p.shield > 0:
            pygame.draw.circle(layer, (100, 200, 255, int(60 + 100 * p.shield / max(1, st.shield_max))), (int(p.x), int(p.y)), int(22 * st.size), 2)
        if (p.thrusting or p.dash_frames) and not blink:
            fa = p.angle if SAVE["controls"] == "classic" else (p.move_angle if p.thrusting else p.angle)
            back_x = p.x - 10 * st.size * math.cos(fa)
            back_y = p.y - 10 * st.size * math.sin(fa)
            for i in range(4):
                offset = random.uniform(-1, 1)
                px = back_x - (i * 7 + offset) * math.cos(fa)
                py = back_y - (i * 7 + offset) * math.sin(fa)
                size = random.randint(2, 5)
                pygame.draw.circle(layer, (*FLAME_PARTICLE, random.randint(150, 200)), (int(px), int(py)), size)
        if not blink:
            ship_col = (255, 255, 255) if p.dash_frames else (rainbow(self.t * 0.01) if p.storm_active else p.color)
            draw_ship(layer, p.x, p.y, p.angle, st.size, ship_col)
        for t in self.texts:
            blit_text(layer, t.s, t.size, t.color, (t.x, t.y), "center", alpha=min(255, t.life * 8))
        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-self.shake, self.shake) // 2, random.randint(-self.shake, self.shake) // 2
        screen.blit(layer, (ox, oy))
        if self.flash > 0:
            veil = pygame.Surface((WIDTH, HEIGHT))
            veil.fill(self.flash_color)
            veil.set_alpha(int(4 * self.flash))
            screen.blit(veil, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        low = p.hp < st.max_hp * 0.3
        if self.hurt_flash > 0 or low:
            v = make_vignette((WIDTH, HEIGHT), (150, 0, 30), 230)
            k = self.hurt_flash / 20 if self.hurt_flash else 0
            if low:
                k = max(k, 0.35 + 0.25 * math.sin(self.t * 0.12))
            v.set_alpha(int(170 * min(1, k)))
            screen.blit(v, (0, 0))
        if p.storm_active:
            hue = (self.t // 6) % 12 / 12
            edge = make_vignette((WIDTH, HEIGHT), rainbow(hue, 200), 70)
            screen.blit(edge, (0, 0))
        self.draw_hud()
        self.draw_aim()

    def draw_aim(self):
        if self.target is not None and self.target.hp > 0:
            t = self.target
            r = t.r + 10
            c = (255, 220, 120)
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                x, y = t.x + sx * r, t.y + sy * r
                pygame.draw.line(screen, c, (x, y), (x - sx * 8, y), 2)
                pygame.draw.line(screen, c, (x, y), (x, y - sy * 8), 2)
        if SAVE["controls"] == "classic" or (SAVE["aim"] == "mouse" and not INPUT["pad"]):
            mx, my = pygame.mouse.get_pos()
            pygame.draw.circle(screen, (130, 180, 255), (mx, my), 11, 1)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pygame.draw.line(screen, (180, 210, 255), (mx + dx * 6, my + dy * 6), (mx + dx * 15, my + dy * 15), 2)
            pygame.draw.circle(screen, (220, 235, 255), (mx, my), 2)

    def draw_hud(self):
        p = self.player
        st = p.stats
        x0, y0 = int(24 * UI), int(20 * UI)
        bw, bh = int(320 * UI), int(14 * UI)
        pygame.draw.rect(screen, (25, 25, 50), (x0, y0, bw, bh), border_radius=4)
        pygame.draw.rect(screen, (90, 220, 160) if p.hp > st.max_hp * 0.35 else DANGER,
                         (x0, y0, int(bw * max(0, p.hp) / st.max_hp), bh), border_radius=4)
        if st.shield_max:
            pygame.draw.rect(screen, (100, 200, 255), (x0, y0 + bh + 3, int(bw * p.shield / st.shield_max), 4), border_radius=2)
        blit_text(screen, f"{L('Корпус', 'Hull')} {int(max(0, p.hp))}/{int(st.max_hp)}", 16, (220, 230, 255), (x0 + bw + 12, y0 - 2))
        y1 = y0 + bh + 14
        pygame.draw.rect(screen, (25, 25, 50), (x0, y1, bw, 6), border_radius=3)
        pygame.draw.rect(screen, HUD_TEXT, (x0, y1, int(bw * min(1, p.xp / p.xp_needed())), 6), border_radius=3)
        blit_text(screen, f"{L('Ур.', 'Lv')} {p.level}", 16, HUD_TEXT, (x0 + bw + 12, y1 - 6))
        blit_text(screen, f"{L('Пыль', 'Dust')}: {int(p.dust)}", 18, GOLD, (x0, y1 + 14))

        def ability(ix, label, key, frac, ready, color=HUD_TITLE, special=False):
            x = x0 + ix * int(76 * UI)
            y = y1 + int(48 * UI)
            r = int(24 * UI)
            center = (x + r, y + r)
            pygame.draw.circle(screen, (25, 25, 50), center, r)
            rect = pygame.Rect(x, y, r * 2, r * 2)
            if ready:
                col = rainbow(self.t * 0.01) if special else color
                pygame.draw.circle(screen, col, center, r, 3 if special else 2)
                if special:
                    draw_glow(screen, center, r * 2, tuple(c // 3 for c in col), 140)
            elif frac > 0:
                pygame.draw.arc(screen, color, rect, math.pi / 2, math.pi / 2 + 2 * math.pi * min(1, frac), 3)
            blit_text(screen, key, 13, (220, 230, 255) if ready else (110, 120, 160), center, "center", True)
            blit_text(screen, label, 13, (140, 150, 190), (x + r, y + r * 2 + 10), "center")
        ability(0, L("Рывок", "Dash"), "Space", 1 - p.dash_timer / max(1, st.dash_cd), p.dash_timer <= 0)
        ability(1, L("Эхо", "Echo"), "Q", 1 - p.pulse_timer / max(1, st.pulse_cd), p.pulse_timer <= 0)
        if p.storm_active:
            ability(2, L("Шторм", "Storm"), f"{p.storm_active // 60 + 1}", p.storm_active / st.storm_dur, False, (255, 200, 255))
        else:
            ability(2, L("Шторм", "Storm"), "E", p.storm / 100, p.storm >= 100, (200, 160, 255), True)
        sector = SECTORS[self.run.sector]
        rx = WIDTH - int(24 * UI)
        top = f"{L('Сектор', 'Sector')} {self.run.sector + 1} — {sector['name'][LI()]}"
        blit_text(screen, top, 18, HUD_TITLE, (rx, y0), "topright")
        yy = y0 + int(26 * UI)
        if self.node.type != "boss":
            w = f"{L('Волна', 'Wave')} {max(0, self.wave_index + 1)}/{len(self.waves)}"
            blit_text(screen, w, 16, HUD_TEXT, (rx, yy), "topright")
            yy += int(22 * UI)
            blit_text(screen, sector["hazard"][LI()], 14, (150, 160, 200), (rx, yy), "topright")
            yy += int(22 * UI)
        if p.combo >= 3:
            ck = p.combo_timer / 150
            col = lerp_color((180, 200, 255), (255, 200, 120), min(1, p.combo / 30))
            blit_text(screen, f"{L('КОМБО', 'COMBO')} {p.combo}", 26, col, (rx, yy + int(6 * UI)), "topright", True)
            blit_text(screen, f"x{p.dust_mult():.2f} {L('пыли', 'dust')}", 15, GOLD, (rx, yy + int(40 * UI)), "topright")
            bw2 = int(140 * UI)
            pygame.draw.rect(screen, (40, 40, 70), (rx - bw2, yy + int(62 * UI), bw2, 4))
            pygame.draw.rect(screen, col, (rx - int(bw2 * ck), yy + int(62 * UI), int(bw2 * ck), 4))
        if self.boss and self.boss.hp > 0:
            bw2 = int(WIDTH * 0.5)
            bx = WIDTH // 2 - bw2 // 2
            by = int(HEIGHT - 60 * UI)
            blit_text(screen, self.boss.name, 22, (255, 220, 240), (WIDTH // 2, by - 8), "midbottom", True)
            pygame.draw.rect(screen, (30, 20, 50), (bx, by, bw2, int(12 * UI)), border_radius=5)
            pygame.draw.rect(screen, (255, 120, 170), (bx, by, int(bw2 * self.boss.hp / self.boss.max_hp), int(12 * UI)), border_radius=5)
            for frac in (0.66, 0.5, 0.33):
                pygame.draw.line(screen, (60, 40, 80), (bx + bw2 * frac, by), (bx + bw2 * frac, by + int(12 * UI)), 1)
        if self.banner:
            bnr = self.banner
            a = min(255, bnr["t"] * 10, (bnr["dur"] - bnr["t"]) * 8)
            blit_text(screen, bnr["text"], 54, bnr["color"], (WIDTH // 2, HEIGHT // 3), "center", True, alpha=a)
            if bnr["sub"]:
                blit_text(screen, bnr["sub"], 20, (190, 190, 225), (WIDTH // 2, HEIGHT // 3 + int(50 * UI)), "center", alpha=a)
        if self.show_help and self.t < 720:
            if SAVE["controls"] == "classic":
                lines = [L("Управление (классика):", "Controls (classic):"), L("Мышь — направление", "Mouse — Direction"),
                         L("W / ЛКМ — тяга, S — тормоз", "W / LMB — Thrust, S — Brake")]
            else:
                lines = [L("Управление:", "Controls:"), L("WASD / стрелки — полёт", "WASD / arrows — Fly"),
                         L("Мышь — прицел (стрельба сама)", "Mouse — Aim (auto-fire)")]
            lines += [L("Пробел / Shift / ПКМ — рывок", "Space / Shift / RMB — Dash"),
                      L("  рывок сквозь пулю = уклонение", "  dash through a bullet = perfect dodge"),
                      L("Q — эхо-импульс", "Q — Echo pulse"),
                      L("E — звёздный шторм (когда шкала полна)", "E — Star storm (when the meter is full)"),
                      L("Esc — пауза и настройки", "Esc — Pause & settings")]
            a = 255 if self.t < 600 else int(255 * (720 - self.t) / 120)
            for i, s in enumerate(lines):
                blit_text(screen, s, 17, HUD_TITLE if i == 0 else HUD_TEXT, (x0, int(HEIGHT * 0.33) + i * int(22 * UI)), alpha=a)
        if self.done_timer > 0:
            blit_text(screen, L("Сектор зачищен", "Area cleared"), 34, (180, 255, 220), (WIDTH // 2, HEIGHT // 3), "center", True,
                      alpha=min(255, self.done_timer * 6))


# =====================================================================
#  Общие элементы интерфейса
# =====================================================================
def snapshot_overlay(snap, dim=150):
    screen.blit(snap, (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((0, 0, 10, dim))
    screen.blit(veil, (0, 0))


def draw_cursor():
    if INPUT["pad"]:
        return
    mx, my = pygame.mouse.get_pos()
    draw_glow(screen, (mx, my), 18, (90, 120, 220), 140)
    pygame.draw.circle(screen, (220, 230, 255), (mx, my), 3)


class Button:
    def __init__(self, label, center, w=None, color=HUD_TITLE, size=24, enabled=True):
        self.label = label
        self.size = size
        self.color = color
        self.enabled = enabled
        self.focused = False
        tw = font(size, True).size(label)[0]
        self.rect = pygame.Rect(0, 0, w or tw + int(60 * UI), int((size + 26) * UI))
        self.rect.center = center
        self.hover_k = 0.0

    def draw(self):
        on = self.focused and self.enabled
        self.hover_k += ((1 if on else 0) - self.hover_k) * 0.25
        base = self.color if self.enabled else (80, 80, 110)
        panel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 18, 40, 190 + int(40 * self.hover_k)), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (*base, 120 + int(135 * self.hover_k)), panel.get_rect(), 2, border_radius=10)
        screen.blit(panel, self.rect.topleft)
        if self.hover_k > 0.05:
            draw_glow(screen, self.rect.center, self.rect.w * 0.45, tuple(int(c * 0.35) for c in base), int(120 * self.hover_k))
        if self.focused:
            pygame.draw.polygon(screen, base, [(self.rect.x - 16, self.rect.centery - 7), (self.rect.x - 6, self.rect.centery),
                                               (self.rect.x - 16, self.rect.centery + 7)])
        blit_text(screen, self.label, self.size, (235, 240, 255) if self.enabled else (120, 120, 150), self.rect.center, "center", True)

    def clicked(self, event):
        return (self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and
                self.rect.collidepoint(event.pos))


class FocusList:
    """Навигация стрелками/геймпадом по списку кнопок + мышь."""

    def __init__(self, buttons, index=0):
        self.buttons = buttons
        self.index = index

    def handle(self, e):
        """Возвращает индекс нажатой кнопки или None."""
        d = key_dir(e)
        if d and (d[1] or d[0]):
            step = d[1] if d[1] else d[0]
            for _ in range(len(self.buttons)):
                self.index = (self.index + step) % len(self.buttons)
                if self.buttons[self.index].enabled:
                    break
            sfx("nav", 0.6)
            return None
        if e.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.index = i
        if is_confirm(e) and self.buttons and self.buttons[self.index].enabled:
            sfx("click")
            return self.index
        for i, b in enumerate(self.buttons):
            if b.clicked(e):
                self.index = i
                sfx("click")
                return i
        return None

    def draw(self):
        for i, b in enumerate(self.buttons):
            b.focused = i == self.index
            b.draw()


def menu_background(theme="night"):
    key = ("menubg", theme)
    if key not in _bg_cache:
        _bg_cache[key] = Background(theme, 7)
    return _bg_cache[key]


def draw_bg_frame(bg, layer, drift=(0.2, 0.05)):
    bg.update(*drift)
    layer.fill((0, 0, 0, 0))
    bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
    screen.blit(layer, (0, 0))


# =====================================================================
#  Экраны внутри забега
# =====================================================================
def upgrade_cards(player, title, picks, snap, allow_reroll=True, luck=0.0, min_rarity=None):
    """Выбор 1 из 3 улучшений: мышь, клавиши 1-3, стрелки + Enter, геймпад."""
    sfx("level", 0.9)
    cw, ch = int(330 * UI), int(380 * UI)
    gap = int(40 * UI)
    t0 = pygame.time.get_ticks()
    focus = 0
    pygame.event.clear()
    while True:
        rects = []
        total = len(picks) * cw + (len(picks) - 1) * gap
        for i in range(len(picks)):
            r = pygame.Rect(0, 0, cw, ch)
            r.topleft = (WIDTH // 2 - total // 2 + i * (cw + gap), HEIGHT // 2 - ch // 2 + int(20 * UI))
            rects.append(r)
        reroll_cost = 15
        can_reroll = allow_reroll and player.dust >= reroll_cost
        ready = pygame.time.get_ticks() - t0 > 350
        for e in get_events():
            if not ready:
                continue
            d = key_dir(e)
            if d and d[0]:
                focus = (focus + d[0]) % max(1, len(picks))
                sfx("nav", 0.6)
            if e.type == pygame.KEYDOWN:
                if pygame.K_1 <= e.key <= pygame.K_3 and e.key - pygame.K_1 < len(picks):
                    sfx("click")
                    return picks[e.key - pygame.K_1]
                if is_confirm(e) and picks:
                    sfx("click")
                    return picks[focus]
                if e.key in (pygame.K_r, pygame.K_e) and can_reroll:
                    player.dust -= reroll_cost
                    picks = roll_upgrades(player, 3, luck, min_rarity)
                    focus = min(focus, max(0, len(picks) - 1))
                    sfx("portal", 0.6)
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        focus = i
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos) and i < len(picks):
                        sfx("click")
                        return picks[i]
        if not picks:
            return None
        snapshot_overlay(snap, 175)
        blit_text(screen, title, 40, (230, 235, 255), (WIDTH // 2, HEIGHT // 2 - ch // 2 - int(50 * UI)), "center", True)
        tt = pygame.time.get_ticks()
        for i, (u, r) in enumerate(zip(picks, rects)):
            col = RARITY_COLORS[u["rarity"]]
            hover = i == focus
            rr = r.move(0, -int(10 * UI) if hover else 0)
            draw_glow(screen, rr.center, cw * (0.75 if hover else 0.6), tuple(int(c * 0.3) for c in col), 140 if hover else 80)
            panel = pygame.Surface(rr.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 235), panel.get_rect(), border_radius=16)
            pygame.draw.rect(panel, (*col, 255 if hover else 150), panel.get_rect(), 3, border_radius=16)
            screen.blit(panel, rr.topleft)
            cx, cy = rr.centerx, rr.y + int(95 * UI)
            draw_glow(screen, (cx, cy), 60 * UI, col, 160)
            if u["rarity"] == "epic":
                pts = [(cx + math.cos(tt * 0.001 + k * math.pi / 5) * (34 if k % 2 == 0 else 15) * UI,
                        cy + math.sin(tt * 0.001 + k * math.pi / 5) * (34 if k % 2 == 0 else 15) * UI) for k in range(10)]
                pygame.draw.polygon(screen, col, pts)
            elif u["rarity"] == "rare":
                draw_spiral(screen, cx, cy, 36 * UI, tt * 0.003, col, 24, 3, 0.4)
            else:
                pygame.draw.circle(screen, col, (cx, cy), int(26 * UI), 3)
                pygame.draw.circle(screen, col, (cx, cy), int(8 * UI))
            blit_text(screen, u["name"][LI()], 22, (240, 240, 255), (cx, rr.y + int(170 * UI)), "center", True)
            rarity = {"common": L("обычное", "common"), "rare": L("редкое", "rare"), "epic": L("эпическое", "epic")}[u["rarity"]]
            blit_text(screen, rarity, 14, col, (cx, rr.y + int(198 * UI)), "center")
            for j, line in enumerate(wrap_lines(u["desc"][LI()], 17, cw - int(40 * UI))):
                blit_text(screen, line, 17, (200, 205, 235), (cx, rr.y + int(235 * UI) + j * int(24 * UI)), "center")
            have = player.upgrades.get(u["id"], 0)
            if u["max"] < 99:
                blit_text(screen, f"{have}/{u['max']}", 15, (140, 150, 190), (cx, rr.bottom - int(52 * UI)), "center")
            blit_text(screen, f"[{i + 1}]", 16, (140, 150, 190), (cx, rr.bottom - int(26 * UI)), "center")
        hint = L("1/2/3, ←→ + Enter или клик", "1/2/3, ←→ + Enter or click")
        blit_text(screen, hint, 16, (150, 160, 200), (WIDTH // 2, HEIGHT // 2 + ch // 2 + int(45 * UI)), "center")
        if allow_reroll:
            col = (220, 230, 255) if can_reroll else (110, 110, 140)
            blit_text(screen, L(f"R — перебросить ({reroll_cost} пыли)", f"R — reroll ({reroll_cost} dust)"), 18, col,
                      (WIDTH // 2, HEIGHT // 2 + ch // 2 + int(75 * UI)), "center")
        blit_text(screen, f"{L('Пыль', 'Dust')}: {int(player.dust)}", 20, GOLD, (WIDTH // 2, HEIGHT // 2 + ch // 2 + int(105 * UI)), "center")
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def settings_screen(snap=None):
    rows = ["controls", "aim", "shake", "numbers", "volume", "sfx", "language"]
    focus = 0
    back = Button(L("Назад", "Back"), (WIDTH // 2, int(HEIGHT * 0.86)), int(300 * UI))
    bg = None if snap is not None else menu_background()
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dragging = None

    def label(key):
        return {"controls": L("Управление", "Controls"), "aim": L("Прицел", "Aiming"),
                "shake": L("Тряска экрана", "Screen shake"), "numbers": L("Цифры урона", "Damage numbers"),
                "volume": L("Музыка", "Music"), "sfx": L("Звуки", "Sounds"), "language": L("Язык", "Language")}[key]

    def value(key):
        v = SAVE[key]
        if key == "controls":
            return L("WASD + мышь", "WASD + mouse") if v == "wasd" else L("Классика: тяга к курсору", "Classic: thrust to cursor")
        if key == "aim":
            return L("Мышью", "Mouse") if v == "mouse" else L("Автоприцел", "Auto-aim")
        if key in ("shake", "numbers"):
            return L("Вкл", "On") if v else L("Выкл", "Off")
        if key in ("volume", "sfx"):
            return f"{int(v * 100)}%"
        return "Русский" if v == "ru" else "English"

    def hint(key):
        return {"controls": L("WASD — полёт в любую сторону, мышь — прицел. Классика — как в «Космическом шторме».",
                              "WASD flies in any direction, mouse aims. Classic works like Cosmic Storm."),
                "aim": L("Автоприцел сам наводится на ближайшего врага — можно играть одной клавиатурой.",
                         "Auto-aim targets the nearest enemy — play with just the keyboard."),
                "shake": L("Встряска камеры при ударах и взрывах.", "Camera shake on hits and explosions."),
                "numbers": L("Показывать урон над врагами.", "Show damage above enemies."),
                "volume": L("←→ или потяни ползунок.", "←→ or drag the slider."),
                "sfx": L("←→ или потяни ползунок.", "←→ or drag the slider."),
                "language": "Русский / English"}[key]

    def change(key, d):
        if key == "controls":
            SAVE[key] = "classic" if SAVE[key] == "wasd" else "wasd"
        elif key == "aim":
            SAVE[key] = "auto" if SAVE[key] == "mouse" else "mouse"
        elif key in ("shake", "numbers"):
            SAVE[key] = not SAVE[key]
        elif key in ("volume", "sfx"):
            SAVE[key] = round(max(0.0, min(1.0, SAVE[key] + 0.1 * (d or 1))), 2)
            if key == "volume":
                apply_volume()
            else:
                sfx("pickup", 1.0)
        elif key == "language":
            SAVE[key] = "en" if SAVE[key] == "ru" else "ru"
            back.label = L("Назад", "Back")
        sfx("nav", 0.8)

    pygame.event.clear()
    while True:
        row_h = int(62 * UI)
        w = int(min(980, WIDTH * 0.62))
        x0 = WIDTH // 2 - w // 2
        y0 = int(HEIGHT * 0.22)
        rects = [pygame.Rect(x0, y0 + i * (row_h + 8), w, row_h) for i in range(len(rows))]
        sliders = {}
        for i, key in enumerate(rows):
            if key in ("volume", "sfx"):
                sr = pygame.Rect(0, 0, int(260 * UI), int(8 * UI))
                sr.midright = (rects[i].right - int(110 * UI), rects[i].centery)
                sliders[key] = sr
        for e in get_events():
            if is_back(e) or back.clicked(e):
                write_save()
                return
            d = key_dir(e)
            if d:
                if d[1]:
                    focus = (focus + d[1]) % (len(rows) + 1)
                    sfx("nav", 0.6)
                elif d[0] and focus < len(rows):
                    change(rows[focus], d[0])
            if is_confirm(e):
                if focus == len(rows):
                    write_save()
                    return
                change(rows[focus], 1)
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        focus = i
                if back.rect.collidepoint(e.pos):
                    focus = len(rows)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for key, sr in sliders.items():
                    if sr.inflate(20, 30).collidepoint(e.pos):
                        dragging = key
                if dragging is None:
                    for i, r in enumerate(rects):
                        if r.collidepoint(e.pos) and rows[i] not in ("volume", "sfx"):
                            change(rows[i], 1)
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and dragging:
                if dragging == "sfx":
                    sfx("pickup", 1.0)
                dragging = None
        if dragging:
            sr = sliders[dragging]
            SAVE[dragging] = round(max(0.0, min(1.0, (pygame.mouse.get_pos()[0] - sr.x) / sr.w)), 2)
            if dragging == "volume":
                apply_volume()
        if snap is not None:
            snapshot_overlay(snap, 200)
        else:
            draw_bg_frame(bg, layer)
        blit_text(screen, L("Настройки", "Settings"), 48, (230, 235, 255), (WIDTH // 2, int(HEIGHT * 0.11)), "center", True)
        for i, key in enumerate(rows):
            r = rects[i]
            on = i == focus
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 215), panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (*HUD_TEXT, 230 if on else 90), panel.get_rect(), 2, border_radius=12)
            screen.blit(panel, r.topleft)
            if on:
                pygame.draw.polygon(screen, HUD_TITLE, [(r.x - 16, r.centery - 7), (r.x - 6, r.centery), (r.x - 16, r.centery + 7)])
            blit_text(screen, label(key), 20, (235, 240, 255), (r.x + int(20 * UI), r.centery), "midleft", True)
            if key in sliders:
                sr = sliders[key]
                pygame.draw.rect(screen, (50, 60, 100), sr, border_radius=4)
                pygame.draw.rect(screen, HUD_TEXT, (sr.x, sr.y, int(sr.w * SAVE[key]), sr.h), border_radius=4)
                pygame.draw.circle(screen, (220, 230, 255), (sr.x + int(sr.w * SAVE[key]), sr.centery), int(9 * UI))
                blit_text(screen, value(key), 18, (220, 230, 255), (r.right - int(20 * UI), r.centery), "midright", True)
            else:
                blit_text(screen, f"‹  {value(key)}  ›", 18, GOLD if on else (220, 230, 255), (r.right - int(20 * UI), r.centery), "midright", True)
        if focus < len(rows):
            blit_text(screen, hint(rows[focus]), 16, (160, 170, 210), (WIDTH // 2, rects[-1].bottom + int(28 * UI)), "center")
        back.focused = focus == len(rows)
        back.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def pause_menu(snap):
    def labels():
        return [(L("Продолжить", "Continue"), HUD_TITLE), (L("Настройки", "Settings"), GOLD),
                (L("Покинуть забег", "Abandon run"), DANGER)]
    buttons = [Button(t, (WIDTH // 2, HEIGHT // 2 - int(40 * UI) + i * int(78 * UI)), int(380 * UI), c)
               for i, (t, c) in enumerate(labels())]
    fl = FocusList(buttons)
    confirm = False
    pygame.event.clear()
    while True:
        for e in get_events():
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                return "continue"
            i = fl.handle(e)
            if i == 0:
                return "continue"
            if i == 1:
                settings_screen(snap)
                for b, (t, _) in zip(buttons, labels()):
                    b.label = t
                confirm = False
            if i == 2:
                if confirm:
                    return "quit"
                confirm = True
                buttons[2].label = L("Точно? Нажми ещё раз", "Sure? Press again")
        snapshot_overlay(snap, 170)
        blit_text(screen, L("Пауза", "Paused"), 48, (230, 235, 255), (WIDTH // 2, HEIGHT // 2 - int(150 * UI)), "center", True)
        fl.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def run_battle(run, node):
    g = Battle(run, node)
    frame = 0
    while True:
        for e in get_events():
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_p):
                    if pause_menu(screen.copy()) == "quit":
                        return "quit"
                elif e.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_RETURN):
                    g.try_dash()
                elif e.key == pygame.K_q:
                    g.try_pulse()
                elif e.key == pygame.K_e:
                    g.try_storm()
                elif e.key == pygame.K_TAB:
                    g.show_help = not g.show_help
                    if g.show_help:
                        g.t = min(g.t, 100)
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 3:
                    g.try_dash()
                elif e.button == 2:
                    g.try_pulse()
        frame += 1
        step = True
        if g.slowmo > 0:
            g.slowmo -= 1
            step = frame % 2 == 0
        if step:
            g.update()
        g.draw()
        pygame.display.flip()
        clock.tick(60)
        p = g.player
        while p.xp >= p.xp_needed() and g.result is None:
            p.xp -= p.xp_needed()
            p.level += 1
            up = upgrade_cards(p, L(f"Уровень {p.level}!", f"Level {p.level}!"), roll_upgrades(p), screen.copy())
            if up:
                p.add_upgrade(up)
            pygame.event.clear()
        if g.result == "dead":
            death_animation(g)
            return "dead"
        if g.result == "win":
            g.player.storm_active = 0
            g.bg.dream_override = False
            return "win"


def death_animation(g):
    p = g.player
    for _ in range(160):
        g.sparks.append(Spark(p.x, p.y, random.choice([SHIP_BLUE, FLAME_PARTICLE, WHITE]), 10, 90, 4))
    for i in range(6):
        w = EchoWave(p.x, p.y, 200 + i * 60, (100, 150, 255), 3)
        w.lifetime = -i * 6
        g.echoes.append(w)
    sfx("boom", 1.0)
    p.hp = -999
    for f in range(120):
        get_events()
        g.t += 1
        for s in g.sparks[:]:
            s.x += s.vx
            s.y += s.vy
            s.vx *= 0.96
            s.vy *= 0.96
            s.life -= 1
            if s.life <= 0:
                g.sparks.remove(s)
        g.echoes = [w for w in g.echoes if w.update()]
        for e in g.enemies:
            e.vx *= 0.9
            e.vy *= 0.9
        g.player.invuln = 999
        g.draw()
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, min(220, f * 2)))
        screen.blit(veil, (0, 0))
        pygame.display.flip()
        clock.tick(60)


# --- Карта сектора ---
NODE_INFO = {
    "battle": {"name": ("Бой", "Battle"), "color": HUD_TEXT},
    "elite": {"name": ("Элита", "Elite"), "color": GOLD},
    "anomaly": {"name": ("Аномалия", "Anomaly"), "color": PORTAL_PURPLE},
    "station": {"name": ("Станция", "Station"), "color": (120, 255, 200)},
    "treasure": {"name": ("Сокровище", "Treasure"), "color": (255, 240, 160)},
    "boss": {"name": ("Босс", "Boss"), "color": (255, 120, 170)},
}
NODE_DESC = {
    "battle": ("Три волны врагов. Пыль и опыт.", "Three waves of enemies. Dust and experience."),
    "elite": ("Сильные враги с особыми свойствами. Награда — реликвия.", "Strong enemies with special traits. Reward: a relic."),
    "anomaly": ("Странное событие с выбором.", "A strange event with a choice."),
    "station": ("Ремонт и магазин улучшений.", "Repairs and an upgrade shop."),
    "treasure": ("Бесплатное улучшение и немного пыли.", "A free upgrade and some dust."),
    "boss": ("Хозяин сектора.", "The master of this sector."),
}


class Node:
    def __init__(self, col, row, n_rows, type_):
        self.col, self.row, self.type = col, row, type_
        self.next = []
        self.visited = False
        self.fx = 0.07 + 0.66 * col / 6
        self.fy = 0.5 if n_rows == 1 else 0.28 + 0.44 * row / (n_rows - 1)
        self.fy += random.uniform(-0.03, 0.03) if n_rows > 1 else 0
        self.fx += random.uniform(-0.015, 0.015) if 0 < col < 6 else 0

    @property
    def pos(self):
        return int(WIDTH * self.fx), int(HEIGHT * self.fy)


def gen_map():
    cols = []
    for c in range(7):
        if c == 0:
            types = ["battle"]
        elif c == 6:
            types = ["boss"]
        else:
            n = random.choice([2, 3, 3])
            types = []
            for _ in range(n):
                if c == 1:
                    t = random.choice(["battle", "battle", "anomaly"])
                else:
                    t = random.choices(["battle", "elite", "anomaly", "station", "treasure"],
                                       [50, 16 if c >= 2 else 0, 17, 12, 6])[0]
                types.append(t)
            if c == 5 and "station" not in types:
                types[random.randrange(n)] = "station"
        cols.append([Node(c, i, len(types), t) for i, t in enumerate(types)])
    for c in range(6):
        cur, nxt = cols[c], cols[c + 1]
        for node in cur:
            ranked = sorted(range(len(nxt)), key=lambda j: abs(nxt[j].fy - node.fy))
            node.next = ranked[:2] if len(nxt) > 1 and random.random() < 0.6 else ranked[:1]
        for j in range(len(nxt)):
            if not any(j in n.next for n in cur):
                closest = min(cur, key=lambda n: abs(n.fy - nxt[j].fy))
                closest.next.append(j)
    return cols


def draw_node_icon(surf, node, pos, size, t, highlight):
    x, y = pos
    info = NODE_INFO[node.type]
    col = info["color"] if not node.visited else (90, 100, 130)
    if highlight:
        draw_glow(surf, pos, size * 3, tuple(int(c * 0.5) for c in col), 160)
    pygame.draw.circle(surf, (10, 12, 30), pos, int(size * 1.25))
    pygame.draw.circle(surf, col, pos, int(size * 1.25), 2)
    if node.type == "battle":
        a = -math.pi / 2
        pts = [(x + math.cos(a) * size * 0.8, y + math.sin(a) * size * 0.8),
               (x + math.cos(a + 2.5) * size * 0.65, y + math.sin(a + 2.5) * size * 0.65),
               (x + math.cos(a - 2.5) * size * 0.65, y + math.sin(a - 2.5) * size * 0.65)]
        pygame.draw.polygon(surf, col, pts)
    elif node.type == "elite":
        pts = [(x + math.cos(-math.pi / 2 + k * math.pi / 5) * size * (0.8 if k % 2 == 0 else 0.35),
                y + math.sin(-math.pi / 2 + k * math.pi / 5) * size * (0.8 if k % 2 == 0 else 0.35)) for k in range(10)]
        pygame.draw.polygon(surf, col, pts)
    elif node.type == "anomaly":
        draw_spiral(surf, x, y, size * 0.85, t * 0.003, col, 20, 2, 0.45)
    elif node.type == "station":
        pts = [(x + math.cos(k * math.pi / 3) * size * 0.7, y + math.sin(k * math.pi / 3) * size * 0.7) for k in range(6)]
        pygame.draw.polygon(surf, col, pts, 2)
        pygame.draw.circle(surf, col, pos, int(size * 0.25))
    elif node.type == "treasure":
        pts = [(x, y - size * 0.8), (x + size * 0.6, y - size * 0.15), (x, y + size * 0.8), (x - size * 0.6, y - size * 0.15)]
        pygame.draw.polygon(surf, col, pts)
        pygame.draw.line(surf, (10, 12, 30), (x - size * 0.6, y - size * 0.15), (x + size * 0.6, y - size * 0.15), 2)
    elif node.type == "boss":
        s = size * (1.0 + 0.1 * math.sin(t * 0.006))
        pts = [(x + math.cos(t * 0.0005 + k * math.pi / 5) * s * (0.95 if k % 2 == 0 else 0.42),
                y + math.sin(t * 0.0005 + k * math.pi / 5) * s * (0.95 if k % 2 == 0 else 0.42)) for k in range(10)]
        pygame.draw.polygon(surf, col, pts)


def map_screen(run):
    bg = Background(SECTORS[run.sector]["bg"], run.seed + run.sector)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    play_music("night.mp3")
    cols = run.map
    if run.current is None:
        reachable = list(cols[0])
    else:
        reachable = [cols[run.current.col + 1][j] for j in run.current.next]
    reachable.sort(key=lambda n: n.fy)
    focus = 0
    legend_nodes = {key: Node(0, 0, 1, key) for key in NODE_INFO}
    pygame.event.clear()
    while True:
        t = pygame.time.get_ticks()
        size = int(20 * UI)
        for e in get_events():
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_p):
                if pause_menu(screen.copy()) == "quit":
                    return None
            d = key_dir(e)
            if d and reachable:
                focus = (focus + (d[1] or d[0])) % len(reachable)
                sfx("nav", 0.6)
            if is_confirm(e) and reachable:
                sfx("click")
                return reachable[focus]
            if e.type == pygame.MOUSEMOTION:
                for i, n in enumerate(reachable):
                    if math.hypot(n.pos[0] - e.pos[0], n.pos[1] - e.pos[1]) < size * 1.6:
                        focus = i
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for n in reachable:
                    if math.hypot(n.pos[0] - e.pos[0], n.pos[1] - e.pos[1]) < size * 1.6:
                        sfx("click")
                        return n
        hovered = reachable[focus] if reachable else None
        draw_bg_frame(bg, layer, (0.3, 0.1))
        for c in range(6):
            for n in cols[c]:
                for j in n.next:
                    m = cols[c + 1][j]
                    active = (n is run.current or (run.current is None and c == 0)) and m in reachable
                    col = (130, 180, 255) if active else (55, 65, 110)
                    a, b = n.pos, m.pos
                    steps = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 12)
                    for k in range(1, steps):
                        f = k / steps
                        if active and ((k + t // 80) % 4 == 0):
                            continue
                        pygame.draw.circle(screen, col, (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f)), 2 if active else 1)
        for c in range(7):
            for n in cols[c]:
                hl = n in reachable
                draw_node_icon(screen, n, n.pos, size * (1.3 if n is hovered else 1), t, hl)
                if n is run.current:
                    draw_ship(screen, n.pos[0], n.pos[1] - size * 2.2, math.pi / 2, 1.3, run.player.color)
        if hovered:
            info = NODE_INFO[hovered.type]
            name = info["name"][LI()]
            if hovered.type == "boss":
                name += ": " + BOSS_NAMES[run.sector][LI()]
            blit_text(screen, name, 22, info["color"], (hovered.pos[0], hovered.pos[1] + size * 2.2), "midtop", True)
            blit_text(screen, NODE_DESC[hovered.type][LI()], 15, (170, 180, 215),
                      (hovered.pos[0], hovered.pos[1] + size * 2.2 + int(28 * UI)), "midtop")
        sector = SECTORS[run.sector]
        blit_text(screen, f"{L('Сектор', 'Sector')} {run.sector + 1} / 3", 22, HUD_TEXT, (WIDTH // 2, int(40 * UI)), "center")
        blit_text(screen, sector["name"][LI()], 44, (230, 235, 255), (WIDTH // 2, int(85 * UI)), "center", True)
        blit_text(screen, L("Выбери следующую точку маршрута  (мышь или ↑↓ + Enter)", "Choose your next waypoint  (mouse or ↑↓ + Enter)"),
                  18, (150, 160, 200), (WIDTH // 2, int(125 * UI)), "center")
        draw_run_panel(run)
        legend_y = HEIGHT - int(40 * UI)
        lx = int(30 * UI)
        for key in NODE_INFO:
            draw_node_icon(screen, legend_nodes[key], (lx + int(12 * UI), legend_y), int(10 * UI), t, False)
            r = blit_text(screen, NODE_INFO[key]["name"][LI()], 15, (170, 180, 210), (lx + int(32 * UI), legend_y), "midleft")
            lx = r.right + int(30 * UI)
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def draw_run_panel(run):
    p = run.player
    x = WIDTH - int(300 * UI)
    y = int(170 * UI)
    panel = pygame.Surface((int(280 * UI), int(HEIGHT - 260 * UI)), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 12, 30, 180), panel.get_rect(), border_radius=14)
    pygame.draw.rect(panel, (70, 90, 160, 160), panel.get_rect(), 1, border_radius=14)
    screen.blit(panel, (x, y))
    lh = int(24 * UI)
    yy = y + int(16 * UI)
    blit_text(screen, SHIPS[p.ship_key]["name"][LI()], 20, HUD_TITLE, (x + int(18 * UI), yy), bold=True)
    yy += lh + 6
    rows = [(f"{L('Корпус', 'Hull')}: {int(p.hp)}/{int(p.stats.max_hp)}", (90, 220, 160)),
            (f"{L('Уровень', 'Level')}: {p.level}", HUD_TEXT),
            (f"{L('Пыль', 'Dust')}: {int(p.dust)}", GOLD),
            (f"{L('Шторм', 'Storm')}: {int(p.storm)}%", (210, 170, 255)),
            (f"{L('Убито', 'Kills')}: {p.kills}", (200, 200, 230))]
    for s, c in rows:
        blit_text(screen, s, 17, c, (x + int(18 * UI), yy))
        yy += lh
    yy += 8
    blit_text(screen, L("Улучшения:", "Upgrades:"), 17, HUD_TITLE, (x + int(18 * UI), yy))
    yy += lh
    for uid, n in p.upgrades.items():
        u = UPGRADE_BY_ID[uid]
        if yy > y + panel.get_height() - lh:
            blit_text(screen, "…", 16, (150, 150, 180), (x + int(18 * UI), yy))
            break
        blit_text(screen, u["name"][LI()] + (f" x{n}" if n > 1 else ""), 15, RARITY_COLORS[u["rarity"]], (x + int(18 * UI), yy))
        yy += int(20 * UI)


# --- Аномалии ---
def _rand_upgrade(run, rarity=None):
    picks = [u for u in UPGRADES if run.player.upgrades.get(u["id"], 0) < u["max"] and (rarity is None or u["rarity"] == rarity)]
    if not picks:
        return L("ничего не произошло", "nothing happened")
    u = random.choice(picks)
    run.player.add_upgrade(u)
    return L("Получено: ", "Gained: ") + u["name"][LI()]


def _hurt(run, amount):
    run.player.hp = max(1, run.player.hp - amount)


def _heal(run, frac):
    p = run.player
    p.hp = min(p.stats.max_hp, p.hp + p.stats.max_hp * frac)


def ev_wreck_search(run):
    if random.random() < 0.6:
        v = random.randint(35, 60)
        run.player.dust += v
        return L(f"Среди обломков нашлось {v} пыли.", f"You found {v} dust in the debris.")
    _hurt(run, 18)
    return L("Обломок взорвался. -18 к корпусу.", "The wreck exploded. -18 hull.")


def ev_portal_enter(run):
    loss = int(run.player.stats.max_hp * 0.1)
    run.player.stats.max_hp -= loss
    run.player.hp = min(run.player.hp, run.player.stats.max_hp)
    return _rand_upgrade(run, random.choice(["rare", "rare", "epic"])) + L(f". Портал забрал {loss} прочности.", f". The portal took {loss} max hull.")


def ev_heart_touch(run):
    _heal(run, 1.0)
    run.hard_k *= 1.15
    return L("Корпус полностью восстановлен. Но шторм стал злее (+15% к прочности врагов).",
             "Hull fully restored. But the storm grew angrier (+15% enemy hull).")


def ev_echo_listen(run):
    run.player.xp += run.player.xp_needed()
    return L("Эхо подсказало новое знание. (+1 уровень в следующем бою)", "The echo taught you something. (+1 level next battle)")


def ev_echo_mute(run):
    run.player.stats.max_hp += 15
    run.player.hp += 15
    return L("Тишина укрепила корпус. +15 к прочности.", "Silence reinforced the hull. +15 max hull.")


def ev_rain_collect(run):
    v = random.randint(30, 70)
    d = random.randint(0, 22)
    run.player.dust += v
    _hurt(run, d)
    return L(f"+{v} пыли, но звёзды задели корпус: -{d}.", f"+{v} dust, but the stars grazed you: -{d}.")


def ev_freeze(run):
    run.flags["slow_next"] = True
    return L("Время застыло. В следующем бою враги будут вдвое медленнее.", "Time froze. Enemies will be twice as slow next battle.")


def ev_gravity_dive(run):
    st = run.player.stats
    st.damage *= 1.15
    st.max_speed *= 0.92
    return L("+15% урона, -8% скорости.", "+15% damage, -8% speed.")


def ev_dream_sleep(run):
    _heal(run, 0.5)
    return L("Сон восстановил 50% корпуса.", "Sleep restored 50% of your hull.")


def ev_trade(run):
    if run.player.dust < 40:
        return L("Не хватает пыли. Торговец растворился.", "Not enough dust. The trader vanished.")
    run.player.dust -= 40
    return _rand_upgrade(run, "rare")


def ev_graveyard_salvage(run):
    _hurt(run, 10)
    a = _rand_upgrade(run, "common")
    b = _rand_upgrade(run, "common")
    return f"{a}; {b}. " + L("Острые обломки: -10 к корпусу.", "Sharp debris: -10 hull.")


def ev_graveyard_honor(run):
    run.flags["storm_start"] = True
    return L("Павшие пилоты делятся силой: следующий бой начнётся с половиной шкалы шторма.",
             "Fallen pilots share their strength: next battle starts with half a storm meter.")


def ev_voice_accept(run):
    st = run.player.stats
    st.storm_rate *= 1.25
    st.max_hp -= 10
    run.player.hp = min(run.player.hp, st.max_hp)
    return L("Шторм теперь копится на 25% быстрее. Корпус -10.", "Storm now charges 25% faster. Max hull -10.")


def ev_leave(run):
    return L("Ты продолжил путь.", "You moved on.")


EVENTS = [
    {"title": ("Дрейфующий обломок", "Drifting Wreck"),
     "text": ("Среди звёздной пыли медленно вращается обломок чужого корабля. Его отсеки ещё светятся.",
              "A wreck of an alien ship slowly spins in the stardust. Its compartments still glow."),
     "options": [(("Обыскать (60% — пыль, 40% — урон)", "Search (60% dust, 40% damage)"), ev_wreck_search),
                 (("Пролететь мимо", "Fly past"), ev_leave)]},
    {"title": ("Тихий портал", "Silent Portal"),
     "text": ("Портал вращается беззвучно. Изнутри доносится свет — но плата за вход неизвестна.",
              "The portal spins silently. Light pours from inside — but the price of entry is unknown."),
     "options": [(("Войти (редкое улучшение, -10% прочности)", "Enter (rare upgrade, -10% max hull)"), ev_portal_enter),
                 (("Не рисковать", "Don't risk it"), ev_leave)]},
    {"title": ("Звезда-сердцебиение", "Heartbeat Star"),
     "text": ("Одна из звёзд бьётся, как сердце. Её свет может исцелить — или разбудить шторм.",
              "One of the stars beats like a heart. Its light could heal you — or wake the storm."),
     "options": [(("Прикоснуться (полный ремонт, враги сильнее)", "Touch it (full repair, stronger foes)"), ev_heart_touch),
                 (("Уйти", "Leave"), ev_leave)]},
    {"title": ("Эхо пространства", "Echo of Space"),
     "text": ("Из пустоты возвращается эхо твоих же сигналов, но немного изменённое.",
              "An echo of your own signals returns from the void — slightly changed."),
     "options": [(("Слушать (+1 уровень)", "Listen (+1 level)"), ev_echo_listen),
                 (("Заглушить (+15 прочности)", "Mute it (+15 max hull)"), ev_echo_mute)]},
    {"title": ("Вечный дождь", "Eternal Rain"),
     "text": ("Мимо проносится поток падающих звёзд. Их хвосты оставляют драгоценную пыль.",
              "A stream of shooting stars rushes past. Their tails leave precious dust."),
     "options": [(("Собирать пыль (+30–70 пыли, риск урона)", "Collect dust (+30–70 dust, risk damage)"), ev_rain_collect),
                 (("Укрыться", "Take cover"), ev_leave)]},
    {"title": ("Заморозка времени", "Time Freeze"),
     "text": ("Здесь время течёт иначе. Можно унести его частицу с собой.",
              "Time flows differently here. You could take a piece of it with you."),
     "options": [(("Остановить время (враги медленнее в следующем бою)", "Stop time (slower enemies next battle)"), ev_freeze),
                 (("Не трогать", "Leave it"), ev_leave)]},
    {"title": ("Гравитационный вихрь", "Gravity Vortex"),
     "text": ("Космический вихрь затягивает всё вокруг. В его центре орудия заряжаются сильнее.",
              "A cosmic vortex pulls everything in. At its core, weapons charge stronger."),
     "options": [(("Нырнуть (+15% урона, -8% скорости)", "Dive in (+15% damage, -8% speed)"), ev_gravity_dive),
                 (("Облететь", "Go around"), ev_leave)]},
    {"title": ("Режим снов", "Dream Mode"),
     "text": ("Звёзды переливаются всеми цветами. Хочется закрыть глаза.",
              "The stars shimmer in every color. You want to close your eyes."),
     "options": [(("Уснуть (ремонт 50%)", "Sleep (repair 50%)"), ev_dream_sleep),
                 (("Не спать", "Stay awake"), ev_leave)]},
    {"title": ("Странник-торговец", "Wandering Trader"),
     "text": ("Корабль-призрак предлагает обмен: немного пыли на редкую технологию.",
              "A ghost ship offers a trade: some dust for a rare technology."),
     "options": [(("Обменять 40 пыли на редкое улучшение", "Trade 40 dust for a rare upgrade"), ev_trade),
                 (("Отказаться", "Decline"), ev_leave)]},
    {"title": ("Кладбище кораблей", "Ship Graveyard"),
     "text": ("Сотни погасших кораблей дрейфуют в тишине. Кто-то из них был таким же, как ты.",
              "Hundreds of dead ships drift in silence. Some of them were just like you."),
     "options": [(("Собрать запчасти (2 обычных улучшения, -10 корпуса)", "Salvage parts (2 common upgrades, -10 hull)"), ev_graveyard_salvage),
                 (("Почтить память (полшкалы шторма в следующем бою)", "Pay respects (half storm meter next battle)"), ev_graveyard_honor)]},
    {"title": ("Голос шторма", "Voice of the Storm"),
     "text": ("Шторм шепчет твоё имя и предлагает часть своей силы.",
              "The storm whispers your name and offers a piece of its power."),
     "options": [(("Принять (шторм копится на 25% быстрее, -10 корпуса)", "Accept (storm charges 25% faster, -10 max hull)"), ev_voice_accept),
                 (("Отказаться", "Refuse"), ev_leave)]},
]


def anomaly_screen(run):
    ev = random.choice(EVENTS)
    bg = Background("dream" if random.random() < 0.5 else "night", run.seed + 99)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    li = LI()
    w = int(860 * UI)
    buttons = [Button(opt[0][li], (WIDTH // 2, int(HEIGHT * 0.6) + i * int(70 * UI)), w, PORTAL_PURPLE, 20)
               for i, opt in enumerate(ev["options"])]
    fl = FocusList(buttons)
    result = None
    cont = Button(L("Продолжить", "Continue"), (WIDTH // 2, int(HEIGHT * 0.74)), int(360 * UI))
    cont.focused = True
    rot = 0.0
    particles = []
    pygame.event.clear()
    while True:
        for e in get_events():
            if result is None:
                i = fl.handle(e)
                if i is not None:
                    result = ev["options"][i][1](run)
            elif cont.clicked(e) or is_confirm(e) or is_back(e):
                sfx("click")
                return
        draw_bg_frame(bg, layer, (0.2, 0.05))
        rot += 0.03
        cx, cy = WIDTH // 2, int(HEIGHT * 0.22)
        update_portal_particles(particles, cx, cy, 60 * UI)
        draw_glow(screen, (cx, cy), 160 * UI, (80, 50, 160), 120)
        layer.fill((0, 0, 0, 0))
        draw_portal(layer, cx, cy, 60 * UI, rot, math.sin(rot * 3) * 5, particles)
        screen.blit(layer, (0, 0))
        blit_text(screen, ev["title"][li], 42, (235, 225, 255), (WIDTH // 2, int(HEIGHT * 0.36)), "center", True)
        for i, line in enumerate(wrap_lines(ev["text"][li], 20, int(900 * UI))):
            blit_text(screen, line, 20, (190, 195, 230), (WIDTH // 2, int(HEIGHT * 0.43) + i * int(30 * UI)), "center")
        if result is None:
            fl.draw()
        else:
            for i, line in enumerate(wrap_lines(result, 22, int(900 * UI))):
                blit_text(screen, line, 22, (180, 255, 220), (WIDTH // 2, int(HEIGHT * 0.6) + i * int(32 * UI)), "center", True)
            cont.draw()
        draw_run_panel(run)
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


# --- Станция ---
def station_screen(run):
    p = run.player
    bg = Background("night", run.seed + 55)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    k = 1 + 0.25 * run.sector
    prices = {"common": int(45 * k), "rare": int(75 * k), "epic": int(120 * k)}
    state = {"offers": roll_upgrades(p, 3, 0.2), "msg": ""}
    repair_cost = int(30 * k)
    reroll_cost = int(20 * k)
    rot = 0.0
    focus = 0
    pygame.event.clear()
    while True:
        cw, ch = int(300 * UI), int(300 * UI)
        gap = int(30 * UI)
        total = 3 * cw + 2 * gap
        cx0 = WIDTH // 2 - int(140 * UI)
        rects = [pygame.Rect(cx0 - total // 2 + i * (cw + gap), int(HEIGHT * 0.3), cw, ch) for i in range(3)]
        b_repair = Button(L(f"Ремонт +35%  ({repair_cost} пыли)", f"Repair +35%  ({repair_cost} dust)"),
                          (cx0 - int(260 * UI), int(HEIGHT * 0.72)), int(440 * UI), (120, 255, 200), 20,
                          p.dust >= repair_cost and p.hp < p.stats.max_hp)
        b_reroll = Button(L(f"Новый товар  ({reroll_cost} пыли)", f"Restock  ({reroll_cost} dust)"),
                          (cx0 + int(260 * UI), int(HEIGHT * 0.72)), int(440 * UI), PORTAL_PURPLE, 20, p.dust >= reroll_cost)
        b_leave = Button(L("Улететь", "Depart"), (cx0, int(HEIGHT * 0.82)), int(320 * UI))

        def activate(i):
            offers = state["offers"]
            if i < 3:
                u = offers[i] if i < len(offers) else None
                if u is None:
                    return
                cost = prices[u["rarity"]]
                if p.dust >= cost:
                    p.dust -= cost
                    p.add_upgrade(u)
                    offers[i] = None
                    sfx("level", 0.6)
                    state["msg"] = L("Куплено: ", "Bought: ") + u["name"][LI()]
                else:
                    state["msg"] = L("Не хватает пыли", "Not enough dust")
            elif i == 3 and b_repair.enabled:
                p.dust -= repair_cost
                p.hp = min(p.stats.max_hp, p.hp + p.stats.max_hp * 0.35)
                sfx("shield")
                state["msg"] = L("Корпус отремонтирован", "Hull repaired")
            elif i == 4 and b_reroll.enabled:
                p.dust -= reroll_cost
                state["offers"] = roll_upgrades(p, 3, 0.2)
                sfx("portal", 0.6)
        for e in get_events():
            if b_leave.clicked(e) or is_back(e) or (is_confirm(e) and focus == 5):
                sfx("click")
                return
            d = key_dir(e)
            if d:
                if d[0]:
                    focus = (focus + d[0]) % 6
                elif d[1] > 0:
                    focus = 3 if focus < 3 else 5
                elif d[1] < 0:
                    focus = 0 if focus in (3, 4) else (3 if focus == 5 else focus)
                sfx("nav", 0.6)
            if is_confirm(e):
                activate(focus)
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(rects + [b_repair.rect, b_reroll.rect, b_leave.rect]):
                    if r.collidepoint(e.pos):
                        focus = i
            if b_repair.clicked(e):
                activate(3)
            if b_reroll.clicked(e):
                activate(4)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        activate(i)
        draw_bg_frame(bg, layer, (0.15, 0.0))
        rot += 0.01
        sx, sy = cx0, int(HEIGHT * 0.15)
        draw_glow(screen, (sx, sy), 120 * UI, (40, 120, 100), 120)
        pts = [(sx + math.cos(rot + k2 * math.pi / 3) * 46 * UI, sy + math.sin(rot + k2 * math.pi / 3) * 46 * UI) for k2 in range(6)]
        pygame.draw.polygon(screen, (120, 255, 200), pts, 3)
        pygame.draw.circle(screen, (120, 255, 200), (sx, sy), int(14 * UI))
        blit_text(screen, L("Станция «Тихая гавань»", "Station “Quiet Harbor”"), 34, (220, 255, 240), (sx, int(HEIGHT * 0.24)), "center", True)
        offers = state["offers"]
        for i, r in enumerate(rects):
            u = offers[i] if i < len(offers) else None
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            on = focus == i
            if u is None:
                pygame.draw.rect(panel, (12, 14, 34, 150), panel.get_rect(), border_radius=14)
                screen.blit(panel, r.topleft)
                blit_text(screen, L("продано", "sold"), 18, (100, 100, 130), r.center, "center")
                continue
            col = RARITY_COLORS[u["rarity"]]
            pygame.draw.rect(panel, (12, 14, 34, 230), panel.get_rect(), border_radius=14)
            pygame.draw.rect(panel, (*col, 255 if on else 150), panel.get_rect(), 3 if on else 2, border_radius=14)
            screen.blit(panel, r.topleft)
            blit_text(screen, u["name"][LI()], 20, (240, 240, 255), (r.centerx, r.y + int(40 * UI)), "center", True)
            for j, line in enumerate(wrap_lines(u["desc"][LI()], 16, cw - int(30 * UI))):
                blit_text(screen, line, 16, (190, 195, 230), (r.centerx, r.y + int(90 * UI) + j * int(22 * UI)), "center")
            cost = prices[u["rarity"]]
            blit_text(screen, L(f"{cost} пыли", f"{cost} dust"), 24, GOLD if p.dust >= cost else (130, 110, 80),
                      (r.centerx, r.bottom - int(40 * UI)), "center", True)
        b_repair.focused = focus == 3
        b_reroll.focused = focus == 4
        b_leave.focused = focus == 5
        b_repair.draw()
        b_reroll.draw()
        b_leave.draw()
        if state["msg"]:
            blit_text(screen, state["msg"], 20, (180, 255, 220), (cx0, int(HEIGHT * 0.9)), "center")
        draw_run_panel(run)
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def treasure_screen(run):
    p = run.player
    bg = Background(SECTORS[run.sector]["bg"], run.seed + run.sector)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_bg_frame(bg, layer)
    cx, cy = WIDTH // 2, HEIGHT // 2
    draw_glow(screen, (cx, cy), 220 * UI, (120, 100, 40), 160)
    s = 60 * UI
    pygame.draw.polygon(screen, (255, 240, 160), [(cx, cy - s), (cx + s * 0.7, cy - s * 0.2), (cx, cy + s), (cx - s * 0.7, cy - s * 0.2)])
    p.dust += 25
    up = upgrade_cards(p, L("Сокровище! +25 пыли", "Treasure! +25 dust"), roll_upgrades(p, 3, 0.5), screen.copy(), True, 0.5)
    if up:
        p.add_upgrade(up)


def sector_intro(run):
    sector = SECTORS[run.sector]
    bg = Background(sector["bg"], run.seed + run.sector)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    li = LI()
    pygame.event.clear()
    for f in range(200):
        for e in get_events():
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and f > 30:
                return
        draw_bg_frame(bg, layer, (0, -2.5))
        a = min(255, f * 5, (200 - f) * 6)
        blit_text(screen, f"{L('СЕКТОР', 'SECTOR')} {run.sector + 1}", 28, HUD_TEXT, (WIDTH // 2, HEIGHT // 2 - int(50 * UI)), "center", alpha=a)
        blit_text(screen, sector["name"][li], 60, (235, 240, 255), (WIDTH // 2, HEIGHT // 2 + int(10 * UI)), "center", True, alpha=a)
        blit_text(screen, L("Опасность: ", "Hazard: ") + sector["hazard"][li], 20, (200, 170, 150),
                  (WIDTH // 2, HEIGHT // 2 + int(70 * UI)), "center", alpha=a)
        pygame.display.flip()
        clock.tick(60)


# =====================================================================
#  Забег
# =====================================================================
class Run:
    def __init__(self, ship_key):
        self.player = Player(ship_key)
        self.sector = 0
        self.seed = random.randint(0, 9999)
        self.map = gen_map()
        self.current = None
        self.hard_k = 1.0
        self.flags = {}
        self.first_battle = True
        self.bosses = 0
        self.start = time.time()


def run_game():
    run = Run(SAVE["ship"])
    SAVE["runs"] += 1
    write_save()
    sector_intro(run)
    # Дар шторма: стартовое улучшение на выбор
    bg = Background(SECTORS[0]["bg"], run.seed)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_bg_frame(bg, layer)
    up = upgrade_cards(run.player, L("Дар шторма — выбери стартовое улучшение", "Storm's gift — choose a starting upgrade"),
                       roll_upgrades(run.player, 3, 0.4, "rare"), screen.copy(), False)
    if up:
        run.player.add_upgrade(up)
    outcome = "dead"
    while True:
        node = map_screen(run)
        if node is None:
            outcome = "quit"
            break
        node.visited = True
        run.current = node
        if node.type in ("battle", "elite", "boss"):
            res = run_battle(run, node)
            if res in ("dead", "quit"):
                outcome = res
                break
            p = run.player
            p.dust += 10 + 4 * node.col
            if node.type == "elite":
                up = upgrade_cards(p, L("Реликвия элиты", "Elite relic"), roll_upgrades(p, 3, 0.6, "rare"), screen.copy(), False)
                if up:
                    p.add_upgrade(up)
            if node.type == "boss":
                run.bosses += 1
                _heal(run, 0.35)
                up = upgrade_cards(p, L("Сила побеждённого босса", "Power of the fallen boss"), roll_upgrades(p, 3, 1.0, "rare"),
                                   screen.copy(), False)
                if up:
                    p.add_upgrade(up)
                if run.sector == 2:
                    outcome = "win"
                    break
                run.sector += 1
                run.map = gen_map()
                run.current = None
                sector_intro(run)
        elif node.type == "anomaly":
            anomaly_screen(run)
        elif node.type == "station":
            station_screen(run)
        elif node.type == "treasure":
            treasure_screen(run)
    summary_screen(run, outcome)


def summary_screen(run, outcome):
    p = run.player
    reached = run.sector + 1
    shards = reached * 10 + run.bosses * 25 + p.kills // 15 + (60 if outcome == "win" else 0)
    SAVE["shards"] += shards
    SAVE["best_sector"] = max(SAVE["best_sector"], reached if outcome != "win" else 4)
    SAVE["best_kills"] = max(SAVE["best_kills"], p.kills)
    if outcome == "win":
        SAVE["wins"] += 1
    write_save()
    play_music("harmony_music.mp3" if outcome == "win" else "night.mp3")
    bg = Background("dream" if outcome == "win" else "night", 3)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    mins = int(time.time() - run.start) // 60
    secs = int(time.time() - run.start) % 60
    title = {"win": L("ШТОРМ УСМИРЁН", "THE STORM IS CALMED"),
             "dead": L("КОРАБЛЬ УНИЧТОЖЕН", "SHIP DESTROYED"),
             "quit": L("ЗАБЕГ ПРЕРВАН", "RUN ABANDONED")}[outcome]
    color = (180, 255, 220) if outcome == "win" else (255, 150, 170)
    rows = [
        (L("Сектор", "Sector"), f"{min(reached, 3)} / 3"),
        (L("Боссов повержено", "Bosses defeated"), str(run.bosses)),
        (L("Врагов уничтожено", "Enemies destroyed"), str(p.kills)),
        (L("Лучшее комбо", "Best combo"), str(p.best_combo)),
        (L("Уровень", "Level"), str(p.level)),
        (L("Время", "Time"), f"{mins}:{secs:02d}"),
    ]
    btn = Button(L("В меню", "To menu"), (WIDTH // 2, int(HEIGHT * 0.84)), int(320 * UI))
    btn.focused = True
    t0 = pygame.time.get_ticks()
    pygame.event.clear()
    while True:
        for e in get_events():
            if btn.clicked(e) or ((is_confirm(e) or is_back(e)) and pygame.time.get_ticks() - t0 > 600):
                return
        draw_bg_frame(bg, layer, (0.3, 0.1))
        blit_text(screen, title, 56, color, (WIDTH // 2, int(HEIGHT * 0.18)), "center", True)
        for i, (k, v) in enumerate(rows):
            y = int(HEIGHT * 0.32) + i * int(42 * UI)
            blit_text(screen, k, 24, (170, 180, 220), (WIDTH // 2 - int(20 * UI), y), "midright")
            blit_text(screen, v, 24, (235, 240, 255), (WIDTH // 2 + int(20 * UI), y), "midleft", True)
        blit_text(screen, L(f"Получено звёздных осколков: +{shards}", f"Star shards earned: +{shards}"), 28, GOLD,
                  (WIDTH // 2, int(HEIGHT * 0.7)), "center", True)
        btn.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


# =====================================================================
#  Обсерватория (вечные улучшения и корабли)
# =====================================================================
META = [
    {"id": "hull", "name": ("Прочный корпус", "Sturdy Hull"), "desc": ("+10 к прочности", "+10 max hull"), "max": 5},
    {"id": "guns", "name": ("Калибровка орудий", "Gun Calibration"), "desc": ("+6% урона", "+6% damage"), "max": 5},
    {"id": "engine", "name": ("Двигатели", "Engines"), "desc": ("+4% скорости", "+4% speed"), "max": 5},
    {"id": "magnet", "name": ("Магнитное поле", "Magnetic Field"), "desc": ("+12% сбор пыли", "+12% dust radius"), "max": 5},
    {"id": "start", "name": ("Стартовый запас", "Starting Supply"), "desc": ("+15 пыли в начале забега", "+15 dust at run start"), "max": 5},
    {"id": "storm", "name": ("Сердце бури", "Storm Heart"), "desc": ("+10% к накоплению шторма", "+10% storm charge rate"), "max": 5},
    {"id": "revive", "name": ("Второй шанс", "Second Chance"), "desc": ("Один раз за забег воскрешает", "Revives you once per run"), "max": 1},
]


def meta_cost(m, level):
    if m["id"] == "revive":
        return 150
    return [20, 35, 55, 80, 110][min(level, 4)]


def observatory():
    bg = menu_background()
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    state = {"msg": ""}
    t0 = pygame.time.get_ticks()
    ship_keys = list(SHIPS.keys())
    focus = 0  # сначала вечные улучшения, затем корабли, затем «Назад»
    n_meta, n_ship = len(META), len(ship_keys)
    total = n_meta + n_ship + 1

    def buy_meta(m):
        lvl = SAVE["meta"].get(m["id"], 0)
        if lvl >= m["max"]:
            state["msg"] = L("Уже максимум", "Already maxed")
            return
        cost = meta_cost(m, lvl)
        if SAVE["shards"] >= cost:
            SAVE["shards"] -= cost
            SAVE["meta"][m["id"]] = lvl + 1
            write_save()
            sfx("level", 0.6)
            state["msg"] = L("Улучшено: ", "Upgraded: ") + m["name"][LI()]
        else:
            state["msg"] = L("Не хватает осколков", "Not enough shards")

    def pick_ship(k):
        if k in SAVE["ships"]:
            SAVE["ship"] = k
            sfx("click")
        elif SAVE["shards"] >= SHIPS[k]["cost"]:
            SAVE["shards"] -= SHIPS[k]["cost"]
            SAVE["ships"].append(k)
            SAVE["ship"] = k
            sfx("level", 0.7)
            state["msg"] = L("Новый корабль: ", "New ship: ") + SHIPS[k]["name"][LI()]
        else:
            state["msg"] = L("Не хватает осколков", "Not enough shards")
        write_save()

    def activate(i):
        if i < n_meta:
            buy_meta(META[i])
        elif i < n_meta + n_ship:
            pick_ship(ship_keys[i - n_meta])

    pygame.event.clear()
    while True:
        li = LI()
        back = Button(L("Назад", "Back"), (WIDTH // 2, HEIGHT - int(60 * UI)), int(280 * UI))
        row_h = int(60 * UI)
        x0 = int(WIDTH * 0.08)
        w = int(WIDTH * 0.42)
        y0 = int(HEIGHT * 0.22)
        meta_rects = [pygame.Rect(x0, y0 + i * (row_h + 8), w, row_h) for i in range(n_meta)]
        sx = int(WIDTH * 0.56)
        sw = int(WIDTH * 0.36)
        ship_h = int(118 * UI)
        ship_rects = [pygame.Rect(sx, y0 + i * (ship_h + 12), sw, ship_h) for i in range(n_ship)]
        ready = pygame.time.get_ticks() - t0 > 200
        for e in get_events():
            if back.clicked(e) or is_back(e) or (is_confirm(e) and focus == total - 1):
                write_save()
                return
            d = key_dir(e)
            if d:
                if d[1]:
                    if focus < n_meta:
                        nf = focus + d[1]
                        focus = nf if 0 <= nf < n_meta else (total - 1 if d[1] > 0 else focus)
                    elif focus < n_meta + n_ship:
                        j = focus - n_meta + d[1]
                        focus = n_meta + j if 0 <= j < n_ship else (total - 1 if d[1] > 0 else focus)
                    elif d[1] < 0:
                        focus = n_meta - 1
                elif d[0]:
                    if focus < n_meta and d[0] > 0:
                        focus = n_meta + min(n_ship - 1, focus * n_ship // n_meta)
                    elif n_meta <= focus < n_meta + n_ship and d[0] < 0:
                        focus = min(n_meta - 1, (focus - n_meta) * n_meta // n_ship)
                sfx("nav", 0.6)
            if is_confirm(e) and ready:
                activate(focus)
            if e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(meta_rects + ship_rects + [back.rect]):
                    if r.collidepoint(e.pos):
                        focus = i
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and ready:
                for i, r in enumerate(meta_rects + ship_rects):
                    if r.collidepoint(e.pos):
                        activate(i)
        draw_bg_frame(bg, layer)
        blit_text(screen, L("Обсерватория", "Observatory"), 48, (230, 235, 255), (WIDTH // 2, int(HEIGHT * 0.08)), "center", True)
        blit_text(screen, L(f"Звёздные осколки: {SAVE['shards']}", f"Star shards: {SAVE['shards']}"), 26, GOLD,
                  (WIDTH // 2, int(HEIGHT * 0.14)), "center", True)
        blit_text(screen, L("Вечные улучшения", "Permanent upgrades"), 22, HUD_TITLE, (x0, y0 - int(36 * UI)))
        for i, (m, r) in enumerate(zip(META, meta_rects)):
            lvl = SAVE["meta"].get(m["id"], 0)
            on = focus == i
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 210), panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (*HUD_TEXT, 230 if on else 110), panel.get_rect(), 2, border_radius=12)
            screen.blit(panel, r.topleft)
            blit_text(screen, m["name"][li], 20, (235, 240, 255), (r.x + int(18 * UI), r.y + int(9 * UI)), bold=True)
            blit_text(screen, m["desc"][li], 15, (170, 180, 215), (r.x + int(18 * UI), r.y + int(34 * UI)))
            for k in range(m["max"]):
                cx = r.right - int(190 * UI) + k * int(20 * UI)
                pygame.draw.circle(screen, HUD_TITLE if k < lvl else (50, 60, 100), (cx, r.centery), int(6 * UI))
            cost_s = L("макс.", "max") if lvl >= m["max"] else L(f"{meta_cost(m, lvl)} оск.", f"{meta_cost(m, lvl)} shards")
            blit_text(screen, cost_s, 18, GOLD if lvl < m["max"] and SAVE["shards"] >= meta_cost(m, lvl) else (130, 120, 100),
                      (r.right - int(16 * UI), r.centery), "midright", True)
        blit_text(screen, L("Корабли", "Ships"), 22, HUD_TITLE, (sx, y0 - int(36 * UI)))
        tt = pygame.time.get_ticks()
        for i, (k, r) in enumerate(zip(ship_keys, ship_rects)):
            ship = SHIPS[k]
            owned = k in SAVE["ships"]
            sel = SAVE["ship"] == k
            on = focus == n_meta + i
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 220), panel.get_rect(), border_radius=14)
            border = GOLD if sel else ship["color"]
            pygame.draw.rect(panel, (*border, 255 if (on or sel) else 120), panel.get_rect(), 3 if (sel or on) else 2, border_radius=14)
            screen.blit(panel, r.topleft)
            scx, scy = r.x + int(66 * UI), r.centery
            draw_glow(screen, (scx, scy), 55 * UI, tuple(int(c * 0.4) for c in ship["color"]), 140)
            draw_ship(screen, scx, scy, tt * 0.001, 2.8 * UI, ship["color"])
            blit_text(screen, ship["name"][li], 21, (240, 240, 255), (r.x + int(130 * UI), r.y + int(12 * UI)), bold=True)
            for j, line in enumerate(wrap_lines(ship["desc"][li], 15, r.w - int(150 * UI))):
                blit_text(screen, line, 15, (180, 190, 220), (r.x + int(130 * UI), r.y + int(44 * UI) + j * int(20 * UI)))
            status = L("выбран", "selected") if sel else L("выбрать", "select") if owned else L(f"{ship['cost']} осколков", f"{ship['cost']} shards")
            blit_text(screen, status, 17, GOLD if not owned else (180, 255, 220) if sel else HUD_TEXT,
                      (r.right - int(16 * UI), r.bottom - int(12 * UI)), "bottomright", True)
        if state["msg"]:
            blit_text(screen, state["msg"], 20, (180, 255, 220), (WIDTH // 2, HEIGHT - int(115 * UI)), "center")
        back.focused = focus == total - 1
        back.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


# =====================================================================
#  Главное меню — живой «Космический шторм» на фоне
# =====================================================================
def main_menu():
    play_music("night.mp3")
    bg = menu_background()
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    sx, sy, svx, svy = WIDTH * 0.3, HEIGHT * 0.6, 0.0, 0.0
    target = (WIDTH * 0.7, HEIGHT * 0.4)
    trail = []
    echoes = []
    focus_idx = 0
    pygame.event.clear()
    while True:
        cy = int(HEIGHT * 0.48)
        bw = int(380 * UI)
        items = [(L("Новый забег", "New run"), HUD_TITLE, 26, "play"),
                 (L("Обсерватория", "Observatory"), GOLD, 24, "observatory"),
                 (L("Настройки", "Settings"), (180, 160, 255), 24, "settings"),
                 (L("Выход", "Quit"), (180, 180, 210), 24, "quit")]
        buttons = [Button(t, (WIDTH // 2, cy + i * int(76 * UI)), bw, c, s) for i, (t, c, s, _) in enumerate(items)]
        fl = FocusList(buttons, focus_idx)
        for e in get_events():
            if is_back(e):
                fl.index = len(items) - 1
                sfx("nav", 0.6)
                continue
            i = fl.handle(e)
            if i is not None:
                return items[i][3]
        focus_idx = fl.index
        if math.hypot(target[0] - sx, target[1] - sy) < 80:
            target = (random.uniform(WIDTH * 0.1, WIDTH * 0.9), random.uniform(HEIGHT * 0.15, HEIGHT * 0.85))
        ang = math.atan2(target[1] - sy, target[0] - sx)
        svx += 0.08 * math.cos(ang)
        svy += 0.08 * math.sin(ang)
        sp = math.hypot(svx, svy)
        if sp > 2.5:
            svx, svy = svx * 2.5 / sp, svy * 2.5 / sp
        sx += svx
        sy += svy
        trail.append((sx, sy))
        del trail[:-200]
        if random.random() < 0.01:
            echoes.append(EchoWave(sx, sy))
        echoes = [w for w in echoes if w.update()]
        bg.update(svx, svy)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, sx, sy)
        for i, (x, y) in enumerate(trail):
            pygame.draw.circle(layer, (*GLOW_BLUE, int(150 * (i / len(trail)) ** 1.5)), (int(x), int(y)), 2)
        for w in echoes:
            w.draw(layer)
        heading = math.atan2(svy, svx)
        draw_ship(layer, sx, sy, heading, 1.0, SHIP_BLUE)
        bx, by = sx - 10 * math.cos(heading), sy - 10 * math.sin(heading)
        for i in range(3):
            px, py = bx - (i * 6) * math.cos(heading), by - (i * 6) * math.sin(heading)
            pygame.draw.circle(layer, (*FLAME_PARTICLE, random.randint(150, 200)), (int(px), int(py)), random.randint(2, 4))
        screen.blit(layer, (0, 0))
        t = pygame.time.get_ticks()
        ty = int(HEIGHT * 0.24)
        draw_glow(screen, (WIDTH // 2, ty), 340 * UI, (40, 60, 140), 110)
        blit_text(screen, L("ЗВЁЗДНЫЙ ШТОРМ", "STAR STORM"), 84, (int(200 + 30 * math.sin(t * 0.002)), 210, 255), (WIDTH // 2, ty), "center", True)
        blit_text(screen, L("космический рогалик", "a cosmic roguelite"), 22, HUD_TEXT, (WIDTH // 2, ty + int(66 * UI)), "center")
        fl.draw()
        info = L(f"Осколки: {SAVE['shards']}   Забегов: {SAVE['runs']}   Побед: {SAVE['wins']}   Лучший сектор: {min(3, SAVE['best_sector'])}",
                 f"Shards: {SAVE['shards']}   Runs: {SAVE['runs']}   Wins: {SAVE['wins']}   Best sector: {min(3, SAVE['best_sector'])}")
        blit_text(screen, info, 17, (150, 160, 200), (WIDTH // 2, HEIGHT - int(70 * UI)), "center")
        hint = L("Мышь или ↑↓ + Enter", "Mouse or ↑↓ + Enter")
        if JOYSTICKS:
            hint += L("   ·   геймпад подключён", "   ·   gamepad connected")
        blit_text(screen, hint, 14, (110, 120, 160), (WIDTH // 2, HEIGHT - int(42 * UI)), "center")
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def main():
    init_sounds()
    apply_volume()
    while True:
        choice = main_menu()
        if choice == "play":
            run_game()
        elif choice == "observatory":
            observatory()
        elif choice == "settings":
            settings_screen()
        else:
            break
    quit_game()


if __name__ == "__main__":
    main()
