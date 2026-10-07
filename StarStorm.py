# -*- coding: utf-8 -*-
"""
ЗВЁЗДНЫЙ ШТОРМ — космический рогалик по мотивам режима «Космический шторм» из Relacs.

Управление:
    Мышь          — направление корабля
    W / ЛКМ       — тяга (как в «Космическом шторме»)
    S             — торможение
    Пробел / ПКМ  — рывок
    Q             — эхо-импульс
    Esc           — пауза
    F12           — скриншот
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
pygame.mixer.set_num_channels(24)

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
RARITY_COLORS = {"common": (130, 180, 255), "rare": (200, 150, 255), "epic": (255, 200, 90)}

# =====================================================================
#  Сохранение
# =====================================================================
DEFAULT_SAVE = {
    "language": "ru", "volume": 0.6, "shards": 0, "meta": {}, "ships": ["wanderer"], "ship": "wanderer",
    "best_sector": 0, "best_kills": 0, "runs": 0, "wins": 0,
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
        if len(_text_cache) > 1500:
            _text_cache.clear()
        surf = font(size, bold).render(s, True, color)
        _text_cache[key] = surf
    return surf


def blit_text(surf, s, size, color, pos, anchor="topleft", bold=False, alpha=None):
    t = text(s, size, color, bold)
    if alpha is not None and alpha < 255:
        t = t.copy()
        t.set_alpha(alpha)
    r = t.get_rect(**{anchor: pos})
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
        if len(_glow_cache) > 400:
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


def lerp_color(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


# =====================================================================
#  Звук: синтезированные эффекты + музыка Relacs
# =====================================================================
def make_sound(kind, duration, volume=0.3, freqs=(440,), decay=10.0, noise=0.0, sweep=0.0):
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
    SOUNDS["shot"] = make_sound("shot", 0.07, 0.10, (1400, 2100), 45, 0.15, -2.5)
    SOUNDS["hit"] = make_sound("hit", 0.05, 0.12, (600,), 60, 0.4)
    SOUNDS["boom"] = make_sound("boom", 0.45, 0.35, (90, 60), 9, 0.75, -0.6)
    SOUNDS["pickup"] = make_sound("pickup", 0.08, 0.10, (1760, 2640), 35)
    SOUNDS["level"] = make_sound("level", 0.7, 0.25, (523, 659, 784, 1046), 5)
    SOUNDS["dash"] = make_sound("dash", 0.22, 0.22, (300,), 14, 0.7, 2.0)
    SOUNDS["hurt"] = make_sound("hurt", 0.3, 0.35, (110, 80), 12, 0.5)
    SOUNDS["pulse"] = make_sound("pulse", 0.6, 0.35, (70, 140), 6, 0.35, 1.0)
    SOUNDS["click"] = make_sound("click", 0.12, 0.2, (660, 990), 25)
    SOUNDS["portal"] = make_sound("portal", 0.5, 0.15, (220, 330, 440), 6, 0.1, 1.5)
    SOUNDS["shield"] = make_sound("shield", 0.2, 0.2, (880, 1320), 18, 0.2)


_last_play = {}


def sfx(name, volume=1.0, throttle=0):
    snd = SOUNDS.get(name)
    if not snd:
        return
    now = pygame.time.get_ticks()
    if throttle and now - _last_play.get(name, -99999) < throttle:
        return
    _last_play[name] = now
    snd.set_volume(min(1.0, volume * (0.2 + SAVE["volume"])))
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


def get_events():
    events = []
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            quit_game()
        if e.type == pygame.KEYDOWN and e.key == pygame.K_F12:
            take_screenshot()
            continue
        events.append(e)
    return events


# =====================================================================
#  Фон из «Космического шторма»: звёзды, пыль, падающие звёзды, сияние,
#  облака снов, порталы, эхо-волны, вихри
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
    def __init__(self):
        self.x = random.randint(-100, WIDTH + 100)
        self.y = random.randint(-100, HEIGHT + 100)
        self.radius = random.randint(110, 200)
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


def draw_portal(surface, x, y, radius, rotation, pulse, particles, alpha_k=1.0):
    """Портал в точности как в «Космическом шторме» (масштабируемый)."""
    if radius < 2:
        return
    pygame.draw.circle(surface, (100, 200, 255, int(100 * alpha_k)), (int(x), int(y)), int(radius + pulse), 2)
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


SECTORS = [
    {"name": ("Глубокая ночь", "Deep Night"), "music": "Relacs2.mp3", "boss_music": "haos.mp3",
     "pool": ["drifter", "swarm", "shooter"], "bg": "night"},
    {"name": ("Вечный дождь", "Eternal Rain"), "music": "burning.mp3", "boss_music": "haos.mp3",
     "pool": ["drifter", "swarm", "shooter", "comet", "vortex"], "bg": "rain"},
    {"name": ("Режим снов", "Dream Mode"), "music": "under the moon.mp3", "boss_music": "Glitc.mp3",
     "pool": ["drifter", "swarm", "shooter", "comet", "vortex", "phantom"], "bg": "dream"},
]


class Background:
    """Весь задник «Космического шторма» в одном объекте."""

    def __init__(self, theme="night"):
        self.theme = theme
        self.stars = [ParallaxStar(1) for _ in range(100)] + [ParallaxStar(2) for _ in range(70)] + \
                     [ParallaxStar(3) for _ in range(50)]
        self.dust = [DustParticle() for _ in range(100)]
        self.aurora = Aurora()
        self.clouds = [CosmicCloud() for _ in range(7)]
        self.rain = []
        self.shooting = []
        self.brightness = 1.0
        self.frozen = False

    def update(self, ship_dx, ship_dy):
        for s in self.stars:
            s.update(ship_dx, ship_dy)
        for d in self.dust:
            d.update(ship_dx, ship_dy)
        if self.theme == "dream":
            for c in self.clouds:
                c.update()
        if self.theme == "rain":
            if random.random() < 0.06:
                star = ShootingStar(background=True)
                star.color = (120, 120, 100)
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
        if self.theme == "night":
            surface.fill((5, 3, 20))
            self.aurora.draw(surface, ship_x, ship_y)
        elif self.theme == "dream":
            surface.fill((4, 2, 14))
        else:
            surface.fill(BLACK)
        if self.theme == "dream":
            for c in self.clouds:
                c.draw(layer)
        for s in self.rain:
            s.draw(layer)
        for s in self.stars:
            s.draw(layer, self.brightness, self.theme == "dream", self.frozen)
        for d in self.dust:
            d.draw(layer, self.theme == "dream")
        for s in self.shooting:
            s.draw(layer)


# =====================================================================
#  Улучшения
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
        self.size = 1.6
        ship = SHIPS[ship_key]
        ship["apply"](self)


SHIPS = {
    "wanderer": {"name": ("Странник", "Wanderer"), "color": SHIP_BLUE, "cost": 0,
                 "desc": ("Корабль из «Космического шторма». Сбалансирован.", "The ship from Cosmic Storm. Balanced."),
                 "apply": lambda s: None},
    "comet": {"name": ("Комета", "Comet"), "color": SHOOTING_STAR_COLOR, "cost": 120,
              "desc": ("Быстрая и скорострельная, но хрупкая. Рывок чаще.", "Fast and rapid-firing, but fragile. Dashes more often."),
              "apply": lambda s: (setattr(s, "max_hp", s.max_hp - 30), setattr(s, "max_speed", s.max_speed * 1.25),
                                  setattr(s, "thrust", s.thrust * 1.25), setattr(s, "fire_delay", s.fire_delay * 0.75),
                                  setattr(s, "damage", s.damage * 0.85), setattr(s, "dash_cd", 100), setattr(s, "size", 1.4))},
    "nebula": {"name": ("Туманность", "Nebula"), "color": PORTAL_PURPLE, "cost": 180,
               "desc": ("Тяжёлая и медленная. Щит и орбитальная звезда со старта.", "Heavy and slow. Starts with a shield and an orbital star."),
               "apply": lambda s: (setattr(s, "max_hp", s.max_hp + 50), setattr(s, "max_speed", s.max_speed * 0.85),
                                   setattr(s, "shield_max", 30), setattr(s, "orbitals", 1), setattr(s, "size", 1.9))},
}


def _mul(attr, k):
    return lambda s: setattr(s, attr, getattr(s, attr) * k)


def _add(attr, v):
    return lambda s: setattr(s, attr, getattr(s, attr) + v)


def _hp_up(p):
    p.stats.max_hp += 25
    p.hp = min(p.stats.max_hp, p.hp + 25)


UPGRADES = [
    # common
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
    # rare
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
    # epic
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
        self.angle = 0.0
        self.trail = []
        self.fire_timer = 0
        self.dash_timer = 0
        self.dash_frames = 0
        self.dash_dir = (0, 0)
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
        return k

    def fire_delay(self):
        d = self.stats.fire_delay
        if self.stats.night_fury and self.hp < self.stats.max_hp * 0.35:
            d *= 0.7
        return max(3, d)

    def take_damage(self, amount, g):
        if self.invuln > 0 or self.dash_frames > 0:
            return False
        amount = max(1, amount - self.stats.armor)
        self.since_hit = 0
        if self.shield > 0:
            absorbed = min(self.shield, amount)
            self.shield -= absorbed
            amount -= absorbed
            sfx("shield", 0.7, 80)
        if amount > 0:
            self.hp -= amount
            sfx("hurt", 0.8, 100)
            g.shake = max(g.shake, 10)
        self.invuln = 40
        g.texts.append(FloatText(self.x, self.y - 30, f"-{int(amount)}", DANGER))
        return True

    def draw_ship(self, surf, x, y, angle, scale, color, alpha=255):
        tip = (x + 14 * scale * math.cos(angle), y + 14 * scale * math.sin(angle))
        left = (x + 10 * scale * math.cos(angle + 2.9), y + 10 * scale * math.sin(angle + 2.9))
        right = (x + 10 * scale * math.cos(angle - 2.9), y + 10 * scale * math.sin(angle - 2.9))
        pygame.draw.polygon(surf, (*color, alpha), [tip, left, right])


# =====================================================================
#  Снаряды, частицы, надписи
# =====================================================================
class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "dmg", "pierce", "life", "r", "crit", "echo", "bounces", "hit_ids", "trail")

    def __init__(self, x, y, angle, speed, dmg, pierce, crit, echo, bounces):
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.dmg = dmg
        self.pierce = pierce
        self.life = 90
        self.r = 5
        self.crit = crit
        self.echo = echo
        self.bounces = bounces
        self.hit_ids = set()
        self.trail = []


class EnemyBullet:
    __slots__ = ("x", "y", "vx", "vy", "dmg", "r", "life", "color")

    def __init__(self, x, y, vx, vy, dmg, r=7, color=PORTAL_PURPLE, life=420):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dmg, self.r, self.life, self.color = dmg, r, life, color


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color, speed=4, life=30, size=3):
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(0.3, 1) * speed
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.life = self.max_life = random.randint(life // 2, life)
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
    __slots__ = ("x", "y", "vx", "vy", "value", "phase")

    def __init__(self, x, y, value):
        a = random.uniform(0, 2 * math.pi)
        s = random.uniform(1, 4)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.value = value
        self.phase = random.uniform(0, 6.28)


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
    "drifter": {"hp": 22, "r": 11, "dmg": 10, "drop": 2, "cost": 1},
    "swarm": {"hp": 7, "r": 6, "dmg": 6, "drop": 1, "cost": 3},
    "shooter": {"hp": 42, "r": 15, "dmg": 12, "drop": 3, "cost": 3},
    "comet": {"hp": 32, "r": 12, "dmg": 18, "drop": 3, "cost": 3},
    "vortex": {"hp": 95, "r": 24, "dmg": 14, "drop": 6, "cost": 6},
    "phantom": {"hp": 38, "r": 14, "dmg": 12, "drop": 4, "cost": 4},
}

_enemy_ids = [0]


class Enemy:
    def __init__(self, kind, x, y, elite, hp_mult, dmg_mult):
        info = ENEMY_INFO[kind]
        _enemy_ids[0] += 1
        self.id = _enemy_ids[0]
        self.kind = kind
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.elite = elite
        self.max_hp = info["hp"] * hp_mult * (3.5 if elite else 1)
        self.hp = self.max_hp
        self.r = info["r"] * (1.45 if elite else 1)
        self.dmg = info["dmg"] * dmg_mult * (1.3 if elite else 1)
        self.drop = info["drop"] * (4 if elite else 1)
        self.flash = 0
        self.slow = 0
        self.timer = random.randint(30, 90)
        self.state = 0
        self.angle = random.uniform(0, 2 * math.pi)
        self.orbit_cd = 0
        self.alpha = 255
        self.boss = False

    def speed_k(self):
        return 0.5 if self.slow > 0 else 1.0

    def steer_to(self, tx, ty, accel, max_speed):
        a = math.atan2(ty - self.y, tx - self.x)
        k = self.speed_k()
        self.vx += math.cos(a) * accel * k
        self.vy += math.sin(a) * accel * k
        sp = math.hypot(self.vx, self.vy)
        if sp > max_speed * k:
            self.vx *= max_speed * k / sp
            self.vy *= max_speed * k / sp

    def update(self, g):
        p = g.player
        self.timer -= 1
        if self.flash > 0:
            self.flash -= 1
        if self.slow > 0:
            self.slow -= 1
        k = self.kind
        if k == "drifter":
            self.steer_to(p.x, p.y, 0.12, 3.0)
            self.angle = math.atan2(self.vy, self.vx)
        elif k == "swarm":
            self.steer_to(p.x + math.sin(self.id + g.t * 0.05) * 60, p.y + math.cos(self.id * 1.7 + g.t * 0.05) * 60, 0.25, 4.2)
        elif k == "shooter":
            d = math.hypot(p.x - self.x, p.y - self.y)
            a = math.atan2(p.y - self.y, p.x - self.x)
            side = a + math.pi / 2 * (1 if self.id % 2 else -1)
            if d > 460:
                self.steer_to(p.x, p.y, 0.08, 2.2)
            elif d < 300:
                self.steer_to(self.x * 2 - p.x, self.y * 2 - p.y, 0.1, 2.4)
            else:
                self.steer_to(self.x + math.cos(side) * 50, self.y + math.sin(side) * 50, 0.06, 1.6)
            self.angle += 0.04
            if self.timer <= 0:
                self.timer = int(100 / self.speed_k() * (0.7 if self.elite else 1))
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
        self.x += self.vx
        self.y += self.vy
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

    def draw(self, layer, screen_surf, t):
        x, y, r = self.x, self.y, self.r
        flash = self.flash > 0
        frozen = self.slow > 0
        k = self.kind
        if self.elite:
            draw_glow(screen_surf, (x, y), r * 3, GOLD, 70)
        if k == "drifter":
            color = (255, 255, 255) if flash else FLAME_PARTICLE
            a = self.angle
            pts = [(x + math.cos(a) * r * 1.4, y + math.sin(a) * r * 1.4),
                   (x + math.cos(a + 2.5) * r, y + math.sin(a + 2.5) * r),
                   (x + math.cos(a - 2.5) * r, y + math.sin(a - 2.5) * r)]
            pygame.draw.polygon(layer, (*color, 230), pts)
            if random.random() < 0.6:
                bx, by = x - math.cos(a) * r, y - math.sin(a) * r
                pygame.draw.circle(layer, (255, 180, 80, 160), (int(bx + random.uniform(-2, 2)), int(by + random.uniform(-2, 2))), random.randint(2, 4))
        elif k == "swarm":
            color = (255, 255, 255) if flash else (100, 150, 255)
            pygame.draw.circle(layer, (*color, 230), (int(x), int(y)), int(r))
            draw_glow(screen_surf, (x, y), r * 3, (60, 90, 200), 90)
        elif k == "shooter":
            color = (255, 255, 255) if flash else (150, 100, 255)
            pts = [(x + math.cos(self.angle + i * math.pi / 2) * r * 1.2, y + math.sin(self.angle + i * math.pi / 2) * r * 1.2) for i in range(4)]
            pygame.draw.polygon(layer, (*color, 220), pts)
            pygame.draw.circle(layer, (200, 150, 255, 120), (int(x), int(y)), int(r * 1.7), 1)
        elif k == "comet":
            color = (255, 255, 255) if flash else SHOOTING_STAR_COLOR
            if self.state == 1:
                ex, ey = x + math.cos(self.angle) * 900, y + math.sin(self.angle) * 900
                a = 60 + int(100 * (1 - self.timer / 45))
                pygame.draw.line(layer, (255, 120, 100, a), (x, y), (ex, ey), 2)
            pygame.draw.circle(layer, (*color, 240), (int(x), int(y)), int(r))
            draw_glow(screen_surf, (x, y), r * 3, (200, 200, 120), 100)
        elif k == "vortex":
            color = (255, 255, 255) if flash else (100, 200, 255)
            draw_spiral(layer, x, y, r * 2.4, self.angle, (*color, 160), 30, 2, 0.4)
            pygame.draw.circle(layer, (50, 150, 255, 200), (int(x), int(y)), int(r * 0.5))
            pygame.draw.circle(layer, (100, 200, 255, 50), (int(x), int(y)), 280, 1)
        elif k == "phantom":
            color = (255, 255, 255) if flash else (255, 150, 230)
            al = self.alpha
            pts = [(x, y - r * 1.3), (x + r, y), (x, y + r * 1.3), (x - r, y)]
            pygame.draw.polygon(layer, (*color, int(al * 0.85)), pts)
            pygame.draw.circle(layer, (40, 10, 60, al), (int(x), int(y)), int(r * 0.35))
        if frozen:
            pygame.draw.circle(layer, (200, 255, 255, 120), (int(x), int(y)), int(r * 1.4), 2)
        if self.hp < self.max_hp and not self.boss:
            w = int(r * 2.2)
            pygame.draw.rect(layer, (40, 40, 70, 200), (x - w / 2, y - r - 12, w, 4))
            pygame.draw.rect(layer, (*(GOLD if self.elite else DANGER), 230), (x - w / 2, y - r - 12, w * max(0, self.hp) / self.max_hp, 4))

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
        self.max_hp = self.hp = 1500 * hp_mult
        self.dmg = 20 * dmg_mult
        self.r = 26
        self.drop = 70
        self.tt = 0.0
        self.history = []
        self.segments = []
        self.n_seg = 16

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

    def draw(self, layer, screen_surf, t):
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
        self.max_hp = self.hp = 2300 * hp_mult
        self.dmg = 22 * dmg_mult
        self.r = 62
        self.drop = 90
        self.spin = 0.0
        self.target = (WIDTH / 2, HEIGHT / 3)
        self.particles = []
        self.rotation = 0.0

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
        if phase2 and g.t % 400 == 0:
            g.portals.append(SpawnPortal(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100), [("swarm", False)] * 6))

    def draw(self, layer, screen_surf, t):
        pulse = math.sin(pygame.time.get_ticks() * 0.003) * 8
        draw_glow(screen_surf, (self.x, self.y), self.r * 3, (90, 60, 200), 120)
        draw_portal(layer, self.x, self.y, self.r, self.rotation, pulse, self.particles)
        draw_spiral(layer, self.x, self.y, self.r * 1.2, -self.rotation * 1.3, (100, 200, 255, 140), 30, 2, 0.35)
        a = math.atan2(t.player.y - self.y, t.player.x - self.x)
        ex, ey = self.x + math.cos(a) * self.r * 0.35, self.y + math.sin(a) * self.r * 0.35
        pygame.draw.circle(layer, (255, 255, 255, 255) if self.flash else (230, 220, 255, 255), (int(self.x), int(self.y)), int(self.r * 0.45))
        pygame.draw.circle(layer, (40, 0, 70, 255), (int(ex), int(ey)), int(self.r * 0.2))


class HeartStar(Enemy):
    """Сектор 3: Сердце шторма — пульсирующая звезда («звезда-сердцебиение»)."""

    def __init__(self, hp_mult, dmg_mult):
        super().__init__("phantom", WIDTH / 2, HEIGHT / 2, False, 1, 1)
        self.boss = True
        self.name = L("Сердце шторма", "Heart of the Storm")
        self.max_hp = self.hp = 3200 * hp_mult
        self.dmg = 24 * dmg_mult
        self.r = 55
        self.drop = 120
        self.beat = 0.0
        self.beat_timer = 120
        self.rings = []
        self.rot = 0.0

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
            g.shake = max(g.shake, 5)
        if g.t % (110 if frac > 0.33 else 70) == 0:
            a = math.atan2(g.player.y - self.y, g.player.x - self.x)
            for i in range(5):
                sa = a + (i - 2) * 0.18
                g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(sa) * 5.2, math.sin(sa) * 5.2, self.dmg * 0.5, 7, (255, 170, 200)))
        if frac < 0.33 and g.t % 8 == 0:
            a = self.rot * 6
            g.ebullets.append(EnemyBullet(self.x, self.y, math.cos(a) * 2.6, math.sin(a) * 2.6, self.dmg * 0.4, 6, (255, 220, 240)))
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
                    if p.take_damage(self.dmg * 0.8, g):
                        ring["hit"] = True

    def draw(self, layer, screen_surf, t):
        size = self.r * (1 + 0.25 * self.beat)
        draw_glow(screen_surf, (self.x, self.y), size * 3.2, (255, 120, 160), int(100 + 120 * self.beat))
        for ring in self.rings:
            alpha = max(30, int(200 * (1 - ring["r"] / max(WIDTH, HEIGHT))))
            g0 = ring["gap"] + ring["w"]
            g1 = ring["gap"] - ring["w"] + 2 * math.pi
            rect = pygame.Rect(0, 0, ring["r"] * 2, ring["r"] * 2)
            rect.center = (self.x, self.y)
            # pygame.draw.arc рисует против часовой стрелки при перевёрнутой оси Y
            pygame.draw.arc(layer, (255, 180, 210, alpha), rect, -g1, -g0, 6)
        pts = []
        for i in range(10):
            a = self.rot + i * math.pi / 5 - math.pi / 2
            rr = size if i % 2 == 0 else size * 0.45
            pts.append((self.x + math.cos(a) * rr, self.y + math.sin(a) * rr))
        color = (255, 255, 255) if self.flash else (255, 210, 230)
        pygame.draw.polygon(layer, (*color, 245), pts)


BOSSES = [AuroraSerpent, StormEye, HeartStar]


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
        sector = SECTORS[run.sector]
        self.bg = Background(sector["bg"])
        self.layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.enemies, self.bullets, self.ebullets, self.pickups = [], [], [], []
        self.sparks, self.texts, self.echoes, self.portals, self.trails = [], [], [], [], []
        self.rain_strikes = []
        self.t = 0
        self.shake = 0
        self.boss = None
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
        if node.type == "boss":
            play_music(sector["boss_music"])
        else:
            play_music(sector["music"])

    def build_waves(self):
        node, run = self.node, self.run
        if node.type == "boss":
            return []
        pool = SECTORS[run.sector]["pool"]
        n_waves = 3
        budget = 6 + 2.4 * node.col + 5 * run.sector
        waves = []
        for w in range(n_waves):
            b = budget * (0.8 + 0.25 * w)
            entries = []
            while b > 0:
                kind = random.choice(pool)
                cost = ENEMY_INFO[kind]["cost"]
                if kind == "swarm":
                    entries += [("swarm", False)] * random.randint(4, 7)
                else:
                    entries.append((kind, False))
                b -= cost
            if node.type == "elite" and w == n_waves - 1:
                for _ in range(1 + (run.sector >= 1)):
                    entries.append((random.choice([k for k in pool if k != "swarm"]), True))
            random.shuffle(entries)
            waves.append(entries)
        return waves

    def open_wave(self):
        self.wave_index += 1
        entries = self.waves[self.wave_index]
        n_portals = min(len(entries), random.randint(2, 3))
        chunks = [entries[i::n_portals] for i in range(n_portals)]
        p = self.player
        for chunk in chunks:
            for _ in range(30):
                x, y = random.randint(90, WIDTH - 90), random.randint(90, HEIGHT - 90)
                if math.hypot(x - p.x, y - p.y) > 320:
                    break
            self.portals.append(SpawnPortal(x, y, chunk))
        sfx("portal", 0.8)

    def spawn_enemy(self, kind, x, y, elite):
        e = Enemy(kind, x, y, elite, self.hp_mult, self.dmg_mult)
        if self.slow_enemies:
            e.slow = 99999
        a = random.uniform(0, 2 * math.pi)
        e.vx, e.vy = math.cos(a) * 2, math.sin(a) * 2
        self.enemies.append(e)

    def kill_enemy(self, e):
        p = self.player
        if e in self.enemies:
            self.enemies.remove(e)
        p.kills += 1
        if p.stats.lifesteal:
            p.hp = min(p.stats.max_hp, p.hp + p.stats.lifesteal)
        n = max(1, int(e.drop))
        value_each = 1
        if n > 12:
            value_each = n / 12
            n = 12
        for _ in range(n):
            self.pickups.append(Pickup(e.x, e.y, value_each))
        color = {"drifter": FLAME_PARTICLE, "swarm": (100, 150, 255), "shooter": (150, 100, 255),
                 "comet": SHOOTING_STAR_COLOR, "vortex": (100, 200, 255), "phantom": (255, 150, 230)}.get(e.kind, WHITE)
        for _ in range(int(14 + e.r)):
            self.sparks.append(Spark(e.x, e.y, color, 5 if not e.boss else 9, 40, 3))
        self.echoes.append(EchoWave(e.x, e.y, e.r * 4, color, 2))
        sfx("boom", 0.5 if not e.boss else 1.0, 60)
        if e.boss:
            self.shake = 30
            for _ in range(120):
                self.sparks.append(Spark(e.x, e.y, random.choice([WHITE, GOLD, PORTAL_PURPLE]), 12, 80, 4))

    def damage_enemy(self, e, dmg, crit=False, from_bullet=True):
        if e.hp <= 0:
            return
        e.hp -= dmg
        e.flash = 4
        if from_bullet and random.random() < self.player.stats.freeze:
            e.slow = max(e.slow, 120)
        self.texts.append(FloatText(e.x, e.y - e.r, str(int(dmg)), GOLD if crit else (220, 220, 255), 22 if crit else 16))
        if e.hp <= 0:
            self.kill_enemy(e)
        else:
            sfx("hit", 0.4, 40)

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
            self.bullets.append(Bullet(tip_x, tip_y, a, st.bullet_speed, dmg, st.pierce, crit, echo, st.ricochet))
        sfx("shot", 0.35, 50)

    def do_pulse(self):
        p = self.player
        st = p.stats
        p.pulse_timer = int(st.pulse_cd)
        sfx("pulse", 1.0)
        self.shake = max(self.shake, 8)
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
        self.ebullets = [b for b in self.ebullets if math.hypot(b.x - p.x, b.y - p.y) > st.pulse_radius]

    def do_dash(self):
        p = self.player
        st = p.stats
        p.dash_timer = int(st.dash_cd)
        p.dash_frames = 9
        p.dash_dir = (math.cos(p.angle), math.sin(p.angle))
        sfx("dash", 0.9)
        self.echoes.append(EchoWave(p.x, p.y, 60))

    def update(self):
        p = self.player
        st = p.stats
        self.t += 1
        mx, my = pygame.mouse.get_pos()
        p.angle = math.atan2(my - p.y, mx - p.x)
        keys = pygame.key.get_pressed()
        mb = pygame.mouse.get_pressed()
        p.thrusting = keys[pygame.K_w] or mb[0]
        if p.thrusting:
            p.vx += st.thrust * math.cos(p.angle)
            p.vy += st.thrust * math.sin(p.angle)
        else:
            p.vx *= 0.95
            p.vy *= 0.95
        if keys[pygame.K_s]:
            p.vx *= 0.85
            p.vy *= 0.85
        sp = math.hypot(p.vx, p.vy)
        if sp > st.max_speed:
            p.vx *= st.max_speed / sp
            p.vy *= st.max_speed / sp
        prev = (p.x, p.y)
        if p.dash_frames > 0:
            p.dash_frames -= 1
            step = st.dash_dist / 9
            p.x += p.dash_dir[0] * step
            p.y += p.dash_dir[1] * step
            if st.dream_dash:
                self.trails.append([p.x, p.y, 70, None, 6])
            p.vx, p.vy = p.dash_dir[0] * st.max_speed, p.dash_dir[1] * st.max_speed
        else:
            p.x += p.vx
            p.y += p.vy
        p.x = max(20, min(WIDTH - 20, p.x))
        p.y = max(20, min(HEIGHT - 20, p.y))
        dx, dy = p.x - prev[0], p.y - prev[1]
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
        # огонь
        p.fire_timer -= 1
        if p.fire_timer <= 0 and (self.enemies or self.boss):
            p.fire_timer = p.fire_delay()
            self.player_fire()
        # орбиты
        p.orbit_angle += 0.055
        orbit_pos = []
        for i in range(st.orbitals):
            a = p.orbit_angle + i * 2 * math.pi / st.orbitals
            orbit_pos.append((p.x + math.cos(a) * 75, p.y + math.sin(a) * 75))
        # звёздный дождь
        if st.star_rain and self.enemies and self.t % max(40, int(170 / st.star_rain)) == 0:
            target = random.choice(self.enemies)
            self.rain_strikes.append({"x": target.x - 250, "y": -40, "tx": target.x, "ty": target.y, "k": 0.0, "trail": []})
        for s in self.rain_strikes[:]:
            s["k"] += 0.05
            s["x"] = (s["tx"] - 250) + 250 * s["k"]
            s["y"] = -40 + (s["ty"] + 40) * s["k"]
            s["trail"].append((s["x"], s["y"]))
            del s["trail"][:-12]
            if s["k"] >= 1:
                self.rain_strikes.remove(s)
                self.echoes.append(EchoWave(s["tx"], s["ty"], 90, SHOOTING_STAR_COLOR, 3))
                for e in self.enemies[:]:
                    if math.hypot(e.x - s["tx"], e.y - s["ty"]) < 90 + e.r:
                        self.damage_enemy(e, st.damage * 3 * p.damage_mult(), True, False)
        # волны
        if not self.boss and self.node.type == "boss" and self.t == 90:
            self.boss = BOSSES[self.run.sector](self.hp_mult / (1 + 0.12 * self.node.col), self.dmg_mult)
            self.enemies.append(self.boss)
            sfx("portal", 1.0)
            self.shake = 20
        if self.node.type != "boss":
            if self.wave_index < len(self.waves) - 1:
                alive = len(self.enemies) + sum(len(pt.queue) for pt in self.portals)
                self.wave_timer -= 1
                if self.wave_timer <= 0 and (alive <= 2 or self.wave_timer < -1500):
                    self.open_wave()
                    self.wave_timer = 150
        # враги
        for e in self.enemies[:]:
            e.update(self)
            if p.dash_frames == 0 and e.hit_test(p.x, p.y, 10 * st.size * 0.8):
                if p.take_damage(e.dmg, self) and not e.boss:
                    a = math.atan2(p.y - e.y, p.x - e.x)
                    p.vx += math.cos(a) * 6
                    p.vy += math.sin(a) * 6
                    self.damage_enemy(e, st.damage, False, False)
            for i, (ox, oy) in enumerate(orbit_pos):
                if e.hit_test(ox, oy, 9):
                    key = (e.id, i)
                    if self.t - self.orbit_hits.get(key, -999) > 20:
                        self.orbit_hits[key] = self.t
                        self.damage_enemy(e, st.damage * 0.8 * p.damage_mult(), False, False)
        for pt in self.portals[:]:
            if not pt.update(self):
                self.portals.remove(pt)
        # пули игрока
        for b in self.bullets[:]:
            if st.homing and self.enemies:
                best, bd = None, 340 ** 2
                for e in self.enemies:
                    d = (e.x - b.x) ** 2 + (e.y - b.y) ** 2
                    if d < bd and e.id not in b.hit_ids:
                        best, bd = e, d
                if best:
                    cur = math.atan2(b.vy, b.vx)
                    want = math.atan2(best.y - b.y, best.x - b.x)
                    diff = (want - cur + math.pi) % (2 * math.pi) - math.pi
                    cur += max(-0.07 * st.homing, min(0.07 * st.homing, diff))
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
            for e in self.enemies[:]:
                if e.id in b.hit_ids:
                    continue
                if e.hit_test(b.x, b.y, b.r):
                    b.hit_ids.add(e.id)
                    self.damage_enemy(e, b.dmg, b.crit)
                    for _ in range(3):
                        self.sparks.append(Spark(b.x, b.y, SHOOTING_STAR_COLOR, 3, 14, 2))
                    if b.echo:
                        self.echoes.append(EchoWave(b.x, b.y, 85, (100, 150, 255), 2))
                        for e2 in self.enemies[:]:
                            if e2 is not e and math.hypot(e2.x - b.x, e2.y - b.y) < 85 + e2.r:
                                self.damage_enemy(e2, b.dmg * 0.6, False, False)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        if b in self.bullets:
                            self.bullets.remove(b)
                        break
        # пули врагов
        for b in self.ebullets[:]:
            b.x += b.vx
            b.y += b.vy
            b.life -= 1
            if b.life <= 0 or b.x < -50 or b.x > WIDTH + 50 or b.y < -50 or b.y > HEIGHT + 50:
                self.ebullets.remove(b)
                continue
            blocked = False
            for ox, oy in orbit_pos:
                if (ox - b.x) ** 2 + (oy - b.y) ** 2 < (b.r + 9) ** 2:
                    blocked = True
                    break
            if blocked:
                self.ebullets.remove(b)
                self.sparks.append(Spark(b.x, b.y, b.color, 3, 12, 2))
                continue
            if (p.x - b.x) ** 2 + (p.y - b.y) ** 2 < (b.r + 8 * st.size * 0.8) ** 2:
                if p.take_damage(b.dmg, self):
                    self.ebullets.remove(b)
        # следы (кометы и «сон наяву»)
        for tr in self.trails[:]:
            tr[2] -= 1
            if tr[3] is None and self.t % 6 == 0:
                for e in self.enemies[:]:
                    if e.hit_test(tr[0], tr[1], 12):
                        self.damage_enemy(e, st.damage * 0.5, False, False)
            if tr[2] <= 0:
                self.trails.remove(tr)
        # пыль
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
                p.dust += pk.value
                p.xp += pk.value
                sfx("pickup", 0.4, 45)
        for s in self.sparks[:]:
            s.x += s.vx
            s.y += s.vy
            s.vx *= 0.95
            s.vy *= 0.95
            s.life -= 1
            if s.life <= 0:
                self.sparks.remove(s)
        self.texts = [t for t in self.texts if t.update()]
        self.echoes = [w for w in self.echoes if w.update()]
        if self.shake > 0:
            self.shake -= 1
        # исход
        if p.hp <= 0:
            if p.revive:
                p.revive = False
                p.hp = p.stats.max_hp * 0.5
                p.invuln = 180
                self.texts.append(FloatText(p.x, p.y - 40, L("ВТОРОЙ ШАНС", "SECOND CHANCE"), GOLD, 30))
                self.do_pulse()
            else:
                self.result = "dead"
                return
        cleared = (not self.enemies and not self.portals and
                   (self.node.type == "boss" and self.boss is not None or
                    self.node.type != "boss" and self.wave_index >= len(self.waves) - 1))
        if cleared:
            self.done_timer += 1
            if self.done_timer > 100 and not self.pickups:
                self.result = "win"

    def draw(self):
        p = self.player
        st = p.stats
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        self.bg.draw(screen, layer, p.x, p.y)
        # след корабля (как в оригинале)
        n = len(p.trail)
        for i, (x, y) in enumerate(p.trail):
            alpha = int(150 * (i / n) ** 1.5)
            pygame.draw.circle(layer, (*GLOW_BLUE, alpha), (int(x), int(y)), 2)
        for tr in self.trails:
            if tr[3] is None:
                hue = (tr[0] * 0.002 + pygame.time.get_ticks() * 0.0005) % 1
                r, g, b = hue_to_rgb(hue)
                pygame.draw.circle(layer, (int(r * 255), int(g * 255), int(b * 255), int(180 * tr[2] / 70)), (int(tr[0]), int(tr[1])), tr[4])
            else:
                pygame.draw.circle(layer, (*tr[3], int(140 * tr[2] / 18)), (int(tr[0]), int(tr[1])), tr[4])
        for pt in self.portals:
            pt.draw(layer)
        for pk in self.pickups:
            tw = 0.6 + 0.4 * math.sin(self.t * 0.15 + pk.phase)
            pygame.draw.circle(layer, (255, 230, 150, int(220 * tw)), (int(pk.x), int(pk.y)), 3)
            draw_glow(screen, (pk.x, pk.y), 10, (180, 150, 60), 120)
        for e in self.enemies:
            e.draw(layer, screen, self)
        for b in self.ebullets:
            draw_glow(screen, (b.x, b.y), b.r * 2.6, b.color, 110)
            pygame.draw.circle(layer, (*b.color, 240), (int(b.x), int(b.y)), b.r)
            pygame.draw.circle(layer, (255, 255, 255, 220), (int(b.x), int(b.y)), max(1, b.r // 2))
        for b in self.bullets:
            col = GOLD if b.crit else SHOOTING_STAR_COLOR
            for i, (x, y) in enumerate(b.trail):
                pygame.draw.circle(layer, (*col, 40 + 25 * i), (int(x), int(y)), 1 + i // 2)
            pygame.draw.circle(layer, (*col, 255), (int(b.x), int(b.y)), 4 if not b.echo else 5)
            draw_glow(screen, (b.x, b.y), 12, (120, 120, 80), 120)
        for s in self.rain_strikes:
            for i, (x, y) in enumerate(s["trail"]):
                pygame.draw.circle(layer, SHOOTING_STAR_COLOR, (int(x), int(y)), 2 + i // 4)
        for s in self.sparks:
            pygame.draw.circle(layer, (*s.color, int(255 * s.life / s.max_life)), (int(s.x), int(s.y)), s.size)
        for w in self.echoes:
            w.draw(layer)
        # орбитальные звёзды
        for i in range(st.orbitals):
            a = p.orbit_angle + i * 2 * math.pi / st.orbitals
            ox, oy = p.x + math.cos(a) * 75, p.y + math.sin(a) * 75
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
        if p.shield > 0:
            pygame.draw.circle(layer, (100, 200, 255, int(60 + 100 * p.shield / max(1, st.shield_max))), (int(p.x), int(p.y)), int(22 * st.size), 2)
        if not blink:
            p.draw_ship(layer, p.x, p.y, p.angle, st.size, (255, 255, 255) if p.dash_frames else p.color)
        if (p.thrusting or p.dash_frames) and not blink:
            back_x = p.x - 10 * st.size * math.cos(p.angle)
            back_y = p.y - 10 * st.size * math.sin(p.angle)
            for i in range(4):
                offset = random.uniform(-1, 1)
                px = back_x - (i * 7 + offset) * math.cos(p.angle)
                py = back_y - (i * 7 + offset) * math.sin(p.angle)
                size = random.randint(2, 5)
                pygame.draw.circle(layer, (*FLAME_PARTICLE, random.randint(150, 200)), (int(px), int(py)), size)
        for t in self.texts:
            blit_text(layer, t.s, t.size, t.color, (t.x, t.y), "center", alpha=min(255, t.life * 8))
        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-self.shake, self.shake) // 2, random.randint(-self.shake, self.shake) // 2
        screen.blit(layer, (ox, oy))
        self.draw_hud()
        # прицел
        mx, my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (130, 180, 255), (mx, my), 9, 1)
        pygame.draw.circle(screen, (200, 220, 255), (mx, my), 2)

    def draw_hud(self):
        p = self.player
        st = p.stats
        x0, y0 = int(24 * UI), int(20 * UI)
        bw, bh = int(320 * UI), int(14 * UI)
        # корпус
        pygame.draw.rect(screen, (25, 25, 50), (x0, y0, bw, bh), border_radius=4)
        pygame.draw.rect(screen, (90, 220, 160) if p.hp > st.max_hp * 0.35 else DANGER,
                         (x0, y0, int(bw * max(0, p.hp) / st.max_hp), bh), border_radius=4)
        if st.shield_max:
            pygame.draw.rect(screen, (100, 200, 255), (x0, y0 + bh + 3, int(bw * p.shield / st.shield_max), 4), border_radius=2)
        blit_text(screen, f"{L('Корпус', 'Hull')} {int(max(0, p.hp))}/{int(st.max_hp)}", 16, (220, 230, 255), (x0 + bw + 12, y0 - 2))
        # опыт
        y1 = y0 + bh + 14
        pygame.draw.rect(screen, (25, 25, 50), (x0, y1, bw, 6), border_radius=3)
        pygame.draw.rect(screen, HUD_TEXT, (x0, y1, int(bw * min(1, p.xp / p.xp_needed())), 6), border_radius=3)
        blit_text(screen, f"{L('Ур.', 'Lv')} {p.level}", 16, HUD_TEXT, (x0 + bw + 12, y1 - 6))
        blit_text(screen, f"{L('Пыль', 'Dust')}: {int(p.dust)}", 18, GOLD, (x0, y1 + 14))
        # способности
        def ability(ix, label, key, timer, cd):
            x = x0 + ix * int(70 * UI)
            y = y1 + int(48 * UI)
            r = int(24 * UI)
            ready = timer <= 0
            pygame.draw.circle(screen, (25, 25, 50), (x + r, y + r), r)
            if not ready:
                k = timer / cd
                rect = pygame.Rect(x, y, r * 2, r * 2)
                pygame.draw.arc(screen, HUD_TEXT, rect, math.pi / 2, math.pi / 2 + 2 * math.pi * (1 - k), 3)
            else:
                pygame.draw.circle(screen, HUD_TITLE, (x + r, y + r), r, 2)
            blit_text(screen, key, 13, (220, 230, 255) if ready else (110, 120, 160), (x + r, y + r), "center", True)
            blit_text(screen, label, 13, (140, 150, 190), (x + r, y + r * 2 + 10), "center")
        ability(0, L("Рывок", "Dash"), "Space", p.dash_timer, st.dash_cd)
        ability(1, L("Эхо", "Echo"), "Q", p.pulse_timer, st.pulse_cd)
        # сектор / волна
        sector = SECTORS[self.run.sector]
        top = f"{L('Сектор', 'Sector')} {self.run.sector + 1} — {sector['name'][0 if SAVE['language'] == 'ru' else 1]}"
        blit_text(screen, top, 18, HUD_TITLE, (WIDTH - int(24 * UI), y0), "topright")
        if self.node.type != "boss":
            w = f"{L('Волна', 'Wave')} {max(0, self.wave_index + 1)}/{len(self.waves)}"
            blit_text(screen, w, 16, HUD_TEXT, (WIDTH - int(24 * UI), y0 + int(26 * UI)), "topright")
        if self.boss and self.boss.hp > 0:
            bw2 = int(WIDTH * 0.5)
            bx = WIDTH // 2 - bw2 // 2
            by = int(HEIGHT - 60 * UI)
            blit_text(screen, self.boss.name, 22, (255, 220, 240), (WIDTH // 2, by - 8), "midbottom", True)
            pygame.draw.rect(screen, (30, 20, 50), (bx, by, bw2, int(12 * UI)), border_radius=5)
            pygame.draw.rect(screen, (255, 120, 170), (bx, by, int(bw2 * self.boss.hp / self.boss.max_hp), int(12 * UI)), border_radius=5)
        if self.show_help and self.t < 600:
            lines = [L("Управление:", "Controls:"), L("Мышь — направление", "Mouse — Direction"),
                     L("W / ЛКМ — ускорение", "W / LMB — Thrust"), L("S — торможение", "S — Brake"),
                     L("Пробел / ПКМ — рывок", "Space / RMB — Dash"), L("Q — эхо-импульс", "Q — Echo pulse"),
                     L("Стрельба — автоматическая", "Firing is automatic"), L("Esc — пауза", "Esc — Pause")]
            a = 255 if self.t < 480 else int(255 * (600 - self.t) / 120)
            for i, s in enumerate(lines):
                blit_text(screen, s, 17, HUD_TITLE if i == 0 else HUD_TEXT, (x0, int(HEIGHT * 0.35) + i * int(22 * UI)), alpha=a)
        if self.done_timer > 0:
            blit_text(screen, L("Сектор зачищен", "Area cleared"), 34, (180, 255, 220), (WIDTH // 2, HEIGHT // 3), "center", True,
                      alpha=min(255, self.done_timer * 6))


def snapshot_overlay(snap, dim=150):
    screen.blit(snap, (0, 0))
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((0, 0, 10, dim))
    screen.blit(veil, (0, 0))


def draw_cursor():
    mx, my = pygame.mouse.get_pos()
    draw_glow(screen, (mx, my), 18, (90, 120, 220), 140)
    pygame.draw.circle(screen, (220, 230, 255), (mx, my), 3)


class Button:
    def __init__(self, label, center, w=None, color=HUD_TITLE, size=24, enabled=True):
        self.label = label
        self.size = size
        self.color = color
        self.enabled = enabled
        tw = font(size, True).size(label)[0]
        self.rect = pygame.Rect(0, 0, w or tw + int(60 * UI), int((size + 26) * UI))
        self.rect.center = center
        self.hover_k = 0.0

    def draw(self):
        mx, my = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mx, my) and self.enabled
        self.hover_k += ((1 if hover else 0) - self.hover_k) * 0.25
        base = self.color if self.enabled else (80, 80, 110)
        panel = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 18, 40, 190 + int(40 * self.hover_k)), panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (*base, 120 + int(135 * self.hover_k)), panel.get_rect(), 2, border_radius=10)
        screen.blit(panel, self.rect.topleft)
        if self.hover_k > 0.05:
            draw_glow(screen, self.rect.center, self.rect.w * 0.45, tuple(int(c * 0.35) for c in base), int(120 * self.hover_k))
        blit_text(screen, self.label, self.size, (235, 240, 255) if self.enabled else (120, 120, 150), self.rect.center, "center", True)

    def clicked(self, event):
        return (self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and
                self.rect.collidepoint(event.pos))


# =====================================================================
#  Экраны внутри забега
# =====================================================================
def upgrade_cards(player, title, picks, snap, allow_reroll=True, luck=0.0, min_rarity=None):
    """Выбор 1 из 3 улучшений. Возвращает выбранное улучшение или None."""
    sfx("level", 0.9)
    cw, ch = int(330 * UI), int(380 * UI)
    gap = int(40 * UI)
    t0 = pygame.time.get_ticks()
    while True:
        rects = []
        total = len(picks) * cw + (len(picks) - 1) * gap
        for i in range(len(picks)):
            r = pygame.Rect(0, 0, cw, ch)
            r.topleft = (WIDTH // 2 - total // 2 + i * (cw + gap), HEIGHT // 2 - ch // 2 + int(20 * UI))
            rects.append(r)
        reroll_cost = 15
        can_reroll = allow_reroll and player.dust >= reroll_cost
        for e in get_events():
            if e.type == pygame.KEYDOWN:
                if pygame.K_1 <= e.key <= pygame.K_3 and e.key - pygame.K_1 < len(picks):
                    sfx("click")
                    return picks[e.key - pygame.K_1]
                if e.key == pygame.K_r and can_reroll:
                    player.dust -= reroll_cost
                    picks = roll_upgrades(player, 3, luck, min_rarity)
                    sfx("portal", 0.6)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and pygame.time.get_ticks() - t0 > 250:
                for i, r in enumerate(rects):
                    if r.collidepoint(e.pos):
                        sfx("click")
                        return picks[i]
        if not picks:
            return None
        snapshot_overlay(snap, 175)
        blit_text(screen, title, 40, (230, 235, 255), (WIDTH // 2, HEIGHT // 2 - ch // 2 - int(50 * UI)), "center", True)
        mx, my = pygame.mouse.get_pos()
        tt = pygame.time.get_ticks()
        for i, (u, r) in enumerate(zip(picks, rects)):
            col = RARITY_COLORS[u["rarity"]]
            hover = r.collidepoint(mx, my)
            rr = r.move(0, -int(10 * UI) if hover else 0)
            draw_glow(screen, rr.center, cw * (0.75 if hover else 0.6), tuple(int(c * 0.3) for c in col), 140 if hover else 80)
            panel = pygame.Surface(rr.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 235), panel.get_rect(), border_radius=16)
            pygame.draw.rect(panel, (*col, 255 if hover else 170), panel.get_rect(), 3, border_radius=16)
            screen.blit(panel, rr.topleft)
            # символ улучшения: звезда/спираль/портал
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
            name = u["name"][0 if SAVE["language"] == "ru" else 1]
            blit_text(screen, name, 22, (240, 240, 255), (cx, rr.y + int(170 * UI)), "center", True)
            rarity = {"common": L("обычное", "common"), "rare": L("редкое", "rare"), "epic": L("эпическое", "epic")}[u["rarity"]]
            blit_text(screen, rarity, 14, col, (cx, rr.y + int(198 * UI)), "center")
            desc = u["desc"][0 if SAVE["language"] == "ru" else 1]
            for j, line in enumerate(wrap_lines(desc, 17, cw - int(40 * UI))):
                blit_text(screen, line, 17, (200, 205, 235), (cx, rr.y + int(235 * UI) + j * int(24 * UI)), "center")
            have = player.upgrades.get(u["id"], 0)
            if u["max"] < 99:
                blit_text(screen, f"{have}/{u['max']}", 15, (140, 150, 190), (cx, rr.bottom - int(52 * UI)), "center")
            blit_text(screen, f"[{i + 1}]", 16, (140, 150, 190), (cx, rr.bottom - int(26 * UI)), "center")
        if allow_reroll:
            col = (220, 230, 255) if can_reroll else (110, 110, 140)
            blit_text(screen, L(f"R — перебросить ({reroll_cost} пыли)", f"R — reroll ({reroll_cost} dust)"), 18, col,
                      (WIDTH // 2, HEIGHT // 2 + ch // 2 + int(70 * UI)), "center")
        blit_text(screen, f"{L('Пыль', 'Dust')}: {int(player.dust)}", 20, GOLD, (WIDTH // 2, HEIGHT // 2 + ch // 2 + int(100 * UI)), "center")
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def pause_menu(snap):
    b_cont = Button(L("Продолжить", "Continue"), (WIDTH // 2, HEIGHT // 2 - int(20 * UI)), int(360 * UI))
    b_quit = Button(L("Покинуть забег", "Abandon run"), (WIDTH // 2, HEIGHT // 2 + int(60 * UI)), int(360 * UI), DANGER)
    confirm = False
    while True:
        for e in get_events():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "continue"
            if b_cont.clicked(e):
                return "continue"
            if b_quit.clicked(e):
                if confirm:
                    return "quit"
                confirm = True
                b_quit.label = L("Точно? Нажми ещё раз", "Sure? Click again")
        snapshot_overlay(snap, 170)
        blit_text(screen, L("Пауза", "Paused"), 48, (230, 235, 255), (WIDTH // 2, HEIGHT // 2 - int(120 * UI)), "center", True)
        b_cont.draw()
        b_quit.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def run_battle(run, node):
    g = Battle(run, node)
    while True:
        for e in get_events():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if pause_menu(screen.copy()) == "quit":
                        return "quit"
                elif e.key in (pygame.K_SPACE, pygame.K_LSHIFT) and g.player.dash_timer <= 0:
                    g.do_dash()
                elif e.key == pygame.K_q and g.player.pulse_timer <= 0:
                    g.do_pulse()
                elif e.key == pygame.K_TAB:
                    g.show_help = not g.show_help
                    g.t = min(g.t, 100)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and g.player.dash_timer <= 0:
                g.do_dash()
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
    "boss": {"name": ("Босс", "Boss"), "color": (255, 120, 170)},
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
                    t = random.choices(["battle", "elite", "anomaly", "station"], [52, 16 if c >= 2 else 0, 18, 14])[0]
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
    elif node.type == "boss":
        s = size * (1.0 + 0.1 * math.sin(t * 0.006))
        pts = [(x + math.cos(t * 0.0005 + k * math.pi / 5) * s * (0.95 if k % 2 == 0 else 0.42),
                y + math.sin(t * 0.0005 + k * math.pi / 5) * s * (0.95 if k % 2 == 0 else 0.42)) for k in range(10)]
        pygame.draw.polygon(surf, col, pts)


def map_screen(run):
    bg = Background(SECTORS[run.sector]["bg"])
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    play_music("night.mp3")
    cols = run.map
    if run.current is None:
        reachable = list(cols[0])
    else:
        reachable = [cols[run.current.col + 1][j] for j in run.current.next]
    drift = [0.3, 0.1]
    while True:
        t = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()
        size = int(20 * UI)
        hovered = None
        for n in reachable:
            if math.hypot(n.pos[0] - mx, n.pos[1] - my) < size * 1.6:
                hovered = n
        for e in get_events():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if pause_menu(screen.copy()) == "quit":
                    return None
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and hovered:
                sfx("click")
                return hovered
        bg.update(*drift)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        screen.blit(layer, (0, 0))
        # связи
        for c in range(6):
            for n in cols[c]:
                for j in n.next:
                    m = cols[c + 1][j]
                    active = (n is run.current or (run.current is None and c == 0 and False)) and m in reachable
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
                draw_node_icon(screen, n, n.pos, size * (1.25 if n is hovered else 1), t, hl)
                if n is run.current:
                    run.player.draw_ship(screen, n.pos[0], n.pos[1] - size * 2.2, math.pi / 2, 1.3, run.player.color)
        # подсказка
        if hovered:
            info = NODE_INFO[hovered.type]
            blit_text(screen, info["name"][0 if SAVE["language"] == "ru" else 1], 22, info["color"],
                      (hovered.pos[0], hovered.pos[1] + size * 2.2), "midtop", True)
        sector = SECTORS[run.sector]
        blit_text(screen, f"{L('Сектор', 'Sector')} {run.sector + 1} / 3", 22, HUD_TEXT, (WIDTH // 2, int(40 * UI)), "center")
        blit_text(screen, sector["name"][0 if SAVE["language"] == "ru" else 1], 44, (230, 235, 255), (WIDTH // 2, int(85 * UI)), "center", True)
        blit_text(screen, L("Выбери следующую точку маршрута", "Choose your next waypoint"), 18, (150, 160, 200),
                  (WIDTH // 2, int(125 * UI)), "center")
        draw_run_panel(run)
        legend_y = HEIGHT - int(40 * UI)
        lx = int(30 * UI)
        for key in ("battle", "elite", "anomaly", "station", "boss"):
            fake = Node(0, 0, 1, key)
            draw_node_icon(screen, fake, (lx + int(12 * UI), legend_y), int(10 * UI), t, False)
            r = blit_text(screen, NODE_INFO[key]["name"][0 if SAVE["language"] == "ru" else 1], 15, (170, 180, 210),
                          (lx + int(32 * UI), legend_y), "midleft")
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
    blit_text(screen, SHIPS[p.ship_key]["name"][0 if SAVE["language"] == "ru" else 1], 20, HUD_TITLE, (x + int(18 * UI), yy), bold=True)
    yy += lh + 6
    rows = [(f"{L('Корпус', 'Hull')}: {int(p.hp)}/{int(p.stats.max_hp)}", (90, 220, 160)),
            (f"{L('Уровень', 'Level')}: {p.level}", HUD_TEXT),
            (f"{L('Пыль', 'Dust')}: {int(p.dust)}", GOLD),
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
        name = u["name"][0 if SAVE["language"] == "ru" else 1]
        blit_text(screen, f"{name}" + (f" x{n}" if n > 1 else ""), 15, RARITY_COLORS[u["rarity"]], (x + int(18 * UI), yy))
        yy += int(20 * UI)


# --- Аномалии ---
def _rand_upgrade(run, rarity=None):
    picks = [u for u in UPGRADES if run.player.upgrades.get(u["id"], 0) < u["max"] and (rarity is None or u["rarity"] == rarity)]
    if not picks:
        return L("ничего не произошло", "nothing happened")
    u = random.choice(picks)
    run.player.add_upgrade(u)
    return L("Получено: ", "Gained: ") + u["name"][0 if SAVE["language"] == "ru" else 1]


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
]


def anomaly_screen(run):
    ev = random.choice(EVENTS)
    bg = Background("dream" if random.random() < 0.5 else "night")
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    li = 0 if SAVE["language"] == "ru" else 1
    w = int(820 * UI)
    buttons = [Button(opt[0][li], (WIDTH // 2, int(HEIGHT * 0.58) + i * int(70 * UI)), w, PORTAL_PURPLE, 20)
               for i, opt in enumerate(ev["options"])]
    result = None
    cont = Button(L("Продолжить", "Continue"), (WIDTH // 2, int(HEIGHT * 0.72)), int(360 * UI))
    rot = 0.0
    particles = []
    while True:
        for e in get_events():
            if result is None:
                for b, opt in zip(buttons, ev["options"]):
                    if b.clicked(e):
                        sfx("click")
                        result = opt[1](run)
            elif cont.clicked(e) or (e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE)):
                return
        bg.update(0.2, 0.05)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        rot += 0.03
        cx, cy = WIDTH // 2, int(HEIGHT * 0.22)
        update_portal_particles(particles, cx, cy, 60 * UI)
        draw_glow(screen, (cx, cy), 160 * UI, (80, 50, 160), 120)
        draw_portal(layer, cx, cy, 60 * UI, rot, math.sin(rot * 3) * 5, particles)
        screen.blit(layer, (0, 0))
        blit_text(screen, ev["title"][li], 42, (235, 225, 255), (WIDTH // 2, int(HEIGHT * 0.36)), "center", True)
        for i, line in enumerate(wrap_lines(ev["text"][li], 20, int(900 * UI))):
            blit_text(screen, line, 20, (190, 195, 230), (WIDTH // 2, int(HEIGHT * 0.43) + i * int(30 * UI)), "center")
        if result is None:
            for b in buttons:
                b.draw()
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
    bg = Background("night")
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    k = 1 + 0.25 * run.sector
    prices = {"common": int(45 * k), "rare": int(75 * k), "epic": int(120 * k)}
    offers = roll_upgrades(p, 3, 0.2)
    repair_cost = int(30 * k)
    reroll_cost = int(20 * k)
    msg = ""
    rot = 0.0
    while True:
        cw, ch = int(300 * UI), int(300 * UI)
        gap = int(30 * UI)
        total = 3 * cw + 2 * gap
        rects = [pygame.Rect(WIDTH // 2 - total // 2 + i * (cw + gap) - int(140 * UI), int(HEIGHT * 0.3), cw, ch) for i in range(3)]
        b_repair = Button(L(f"Ремонт +35%  ({repair_cost} пыли)", f"Repair +35%  ({repair_cost} dust)"),
                          (WIDTH // 2 - int(140 * UI) - int(260 * UI), int(HEIGHT * 0.72)), int(440 * UI), (120, 255, 200), 20,
                          p.dust >= repair_cost and p.hp < p.stats.max_hp)
        b_reroll = Button(L(f"Новый товар  ({reroll_cost} пыли)", f"Restock  ({reroll_cost} dust)"),
                          (WIDTH // 2 - int(140 * UI) + int(260 * UI), int(HEIGHT * 0.72)), int(440 * UI), PORTAL_PURPLE, 20,
                          p.dust >= reroll_cost)
        b_leave = Button(L("Улететь", "Depart"), (WIDTH // 2 - int(140 * UI), int(HEIGHT * 0.82)), int(320 * UI))
        mx, my = pygame.mouse.get_pos()
        for e in get_events():
            if b_leave.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                return
            if b_repair.clicked(e):
                p.dust -= repair_cost
                p.hp = min(p.stats.max_hp, p.hp + p.stats.max_hp * 0.35)
                sfx("shield")
                msg = L("Корпус отремонтирован", "Hull repaired")
            if b_reroll.clicked(e):
                p.dust -= reroll_cost
                offers = roll_upgrades(p, 3, 0.2)
                sfx("portal", 0.6)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(rects):
                    if i < len(offers) and offers[i] and r.collidepoint(e.pos):
                        u = offers[i]
                        cost = prices[u["rarity"]]
                        if p.dust >= cost:
                            p.dust -= cost
                            p.add_upgrade(u)
                            offers[i] = None
                            sfx("level", 0.6)
                            msg = L("Куплено: ", "Bought: ") + u["name"][0 if SAVE["language"] == "ru" else 1]
                        else:
                            msg = L("Не хватает пыли", "Not enough dust")
        bg.update(0.15, 0.0)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        screen.blit(layer, (0, 0))
        rot += 0.01
        cx, cy = WIDTH // 2 - int(140 * UI), int(HEIGHT * 0.15)
        draw_glow(screen, (cx, cy), 120 * UI, (40, 120, 100), 120)
        pts = [(cx + math.cos(rot + k2 * math.pi / 3) * 46 * UI, cy + math.sin(rot + k2 * math.pi / 3) * 46 * UI) for k2 in range(6)]
        pygame.draw.polygon(screen, (120, 255, 200), pts, 3)
        pygame.draw.circle(screen, (120, 255, 200), (cx, cy), int(14 * UI))
        blit_text(screen, L("Станция «Тихая гавань»", "Station “Quiet Harbor”"), 34, (220, 255, 240), (cx, int(HEIGHT * 0.24)), "center", True)
        for i, r in enumerate(rects):
            u = offers[i] if i < len(offers) else None
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            if u is None:
                pygame.draw.rect(panel, (12, 14, 34, 150), panel.get_rect(), border_radius=14)
                screen.blit(panel, r.topleft)
                blit_text(screen, L("продано", "sold"), 18, (100, 100, 130), r.center, "center")
                continue
            col = RARITY_COLORS[u["rarity"]]
            hover = r.collidepoint(mx, my)
            pygame.draw.rect(panel, (12, 14, 34, 230), panel.get_rect(), border_radius=14)
            pygame.draw.rect(panel, (*col, 255 if hover else 150), panel.get_rect(), 2, border_radius=14)
            screen.blit(panel, r.topleft)
            name = u["name"][0 if SAVE["language"] == "ru" else 1]
            blit_text(screen, name, 20, (240, 240, 255), (r.centerx, r.y + int(40 * UI)), "center", True)
            desc = u["desc"][0 if SAVE["language"] == "ru" else 1]
            for j, line in enumerate(wrap_lines(desc, 16, cw - int(30 * UI))):
                blit_text(screen, line, 16, (190, 195, 230), (r.centerx, r.y + int(90 * UI) + j * int(22 * UI)), "center")
            cost = prices[u["rarity"]]
            blit_text(screen, L(f"{cost} пыли", f"{cost} dust"), 24, GOLD if p.dust >= cost else (130, 110, 80), (r.centerx, r.bottom - int(40 * UI)), "center", True)
        b_repair.draw()
        b_reroll.draw()
        b_leave.draw()
        if msg:
            blit_text(screen, msg, 20, (180, 255, 220), (WIDTH // 2 - int(140 * UI), int(HEIGHT * 0.9)), "center")
        draw_run_panel(run)
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


def sector_intro(run):
    sector = SECTORS[run.sector]
    bg = Background(sector["bg"])
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    li = 0 if SAVE["language"] == "ru" else 1
    for f in range(200):
        for e in get_events():
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and f > 30:
                return
        bg.update(0, -2.5)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        screen.blit(layer, (0, 0))
        a = min(255, f * 5, (200 - f) * 6)
        blit_text(screen, f"{L('СЕКТОР', 'SECTOR')} {run.sector + 1}", 28, HUD_TEXT, (WIDTH // 2, HEIGHT // 2 - int(50 * UI)), "center", alpha=a)
        blit_text(screen, sector["name"][li], 60, (235, 240, 255), (WIDTH // 2, HEIGHT // 2 + int(10 * UI)), "center", True, alpha=a)
        pygame.display.flip()
        clock.tick(60)


# =====================================================================
#  Забег
# =====================================================================
class Run:
    def __init__(self, ship_key):
        self.player = Player(ship_key)
        self.sector = 0
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
            bonus = 10 + 4 * node.col
            p.dust += bonus
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
    bg = Background("dream" if outcome == "win" else "night")
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
        (L("Уровень", "Level"), str(p.level)),
        (L("Время", "Time"), f"{mins}:{secs:02d}"),
    ]
    btn = Button(L("В меню", "To menu"), (WIDTH // 2, int(HEIGHT * 0.82)), int(320 * UI))
    t0 = pygame.time.get_ticks()
    while True:
        for e in get_events():
            if btn.clicked(e) or (e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_ESCAPE)
                                  and pygame.time.get_ticks() - t0 > 600):
                return
        bg.update(0.3, 0.1)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        screen.blit(layer, (0, 0))
        blit_text(screen, title, 56, color, (WIDTH // 2, int(HEIGHT * 0.2)), "center", True)
        for i, (k, v) in enumerate(rows):
            y = int(HEIGHT * 0.34) + i * int(42 * UI)
            blit_text(screen, k, 24, (170, 180, 220), (WIDTH // 2 - int(20 * UI), y), "midright")
            blit_text(screen, v, 24, (235, 240, 255), (WIDTH // 2 + int(20 * UI), y), "midleft", True)
        blit_text(screen, L(f"Получено звёздных осколков: +{shards}", f"Star shards earned: +{shards}"), 28, GOLD,
                  (WIDTH // 2, int(HEIGHT * 0.66)), "center", True)
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
    {"id": "revive", "name": ("Второй шанс", "Second Chance"), "desc": ("Один раз за забег воскрешает", "Revives you once per run"), "max": 1},
]


def meta_cost(m, level):
    if m["id"] == "revive":
        return 150
    return [20, 35, 55, 80, 110][min(level, 4)]


def observatory():
    bg = Background("night")
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    back = Button(L("Назад", "Back"), (WIDTH // 2, HEIGHT - int(70 * UI)), int(280 * UI))
    msg = ""
    t0 = pygame.time.get_ticks()
    while True:
        li = 0 if SAVE["language"] == "ru" else 1
        row_h = int(64 * UI)
        x0 = int(WIDTH * 0.08)
        w = int(WIDTH * 0.42)
        y0 = int(HEIGHT * 0.24)
        meta_rects = [pygame.Rect(x0, y0 + i * (row_h + 10), w, row_h) for i in range(len(META))]
        sx = int(WIDTH * 0.56)
        sw = int(WIDTH * 0.36)
        ship_keys = list(SHIPS.keys())
        ship_rects = [pygame.Rect(sx, y0 + i * int(150 * UI), sw, int(135 * UI)) for i in range(len(ship_keys))]
        mx, my = pygame.mouse.get_pos()
        for e in get_events():
            if back.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                write_save()
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and pygame.time.get_ticks() - t0 > 200:
                for m, r in zip(META, meta_rects):
                    if r.collidepoint(e.pos):
                        lvl = SAVE["meta"].get(m["id"], 0)
                        if lvl >= m["max"]:
                            msg = L("Уже максимум", "Already maxed")
                        else:
                            cost = meta_cost(m, lvl)
                            if SAVE["shards"] >= cost:
                                SAVE["shards"] -= cost
                                SAVE["meta"][m["id"]] = lvl + 1
                                write_save()
                                sfx("level", 0.6)
                                msg = L("Улучшено: ", "Upgraded: ") + m["name"][li]
                            else:
                                msg = L("Не хватает осколков", "Not enough shards")
                for k, r in zip(ship_keys, ship_rects):
                    if r.collidepoint(e.pos):
                        if k in SAVE["ships"]:
                            SAVE["ship"] = k
                            sfx("click")
                        elif SAVE["shards"] >= SHIPS[k]["cost"]:
                            SAVE["shards"] -= SHIPS[k]["cost"]
                            SAVE["ships"].append(k)
                            SAVE["ship"] = k
                            sfx("level", 0.7)
                            msg = L("Новый корабль: ", "New ship: ") + SHIPS[k]["name"][li]
                        else:
                            msg = L("Не хватает осколков", "Not enough shards")
                        write_save()
        bg.update(0.2, 0.05)
        layer.fill((0, 0, 0, 0))
        bg.draw(screen, layer, WIDTH / 2, HEIGHT / 2)
        screen.blit(layer, (0, 0))
        blit_text(screen, L("Обсерватория", "Observatory"), 48, (230, 235, 255), (WIDTH // 2, int(HEIGHT * 0.08)), "center", True)
        blit_text(screen, L(f"Звёздные осколки: {SAVE['shards']}", f"Star shards: {SAVE['shards']}"), 26, GOLD,
                  (WIDTH // 2, int(HEIGHT * 0.14)), "center", True)
        blit_text(screen, L("Вечные улучшения", "Permanent upgrades"), 22, HUD_TITLE, (x0, y0 - int(36 * UI)))
        for m, r in zip(META, meta_rects):
            lvl = SAVE["meta"].get(m["id"], 0)
            hover = r.collidepoint(mx, my)
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 210), panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (*HUD_TEXT, 230 if hover else 110), panel.get_rect(), 2, border_radius=12)
            screen.blit(panel, r.topleft)
            blit_text(screen, m["name"][li], 20, (235, 240, 255), (r.x + int(18 * UI), r.y + int(10 * UI)), bold=True)
            blit_text(screen, m["desc"][li], 15, (170, 180, 215), (r.x + int(18 * UI), r.y + int(36 * UI)))
            for k in range(m["max"]):
                cx = r.right - int(170 * UI) + k * int(20 * UI)
                pygame.draw.circle(screen, HUD_TITLE if k < lvl else (50, 60, 100), (cx, r.centery), int(6 * UI))
            cost_s = L("макс.", "max") if lvl >= m["max"] else L(f"{meta_cost(m, lvl)} оск.", f"{meta_cost(m, lvl)} shards")
            blit_text(screen, cost_s, 18, GOLD if lvl < m["max"] and SAVE["shards"] >= meta_cost(m, lvl) else (130, 120, 100),
                      (r.right - int(16 * UI), r.centery), "midright", True)
        blit_text(screen, L("Корабли", "Ships"), 22, HUD_TITLE, (sx, y0 - int(36 * UI)))
        tt = pygame.time.get_ticks()
        for k, r in zip(ship_keys, ship_rects):
            ship = SHIPS[k]
            owned = k in SAVE["ships"]
            sel = SAVE["ship"] == k
            hover = r.collidepoint(mx, my)
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (12, 14, 34, 220), panel.get_rect(), border_radius=14)
            border = GOLD if sel else ship["color"]
            pygame.draw.rect(panel, (*border, 255 if (hover or sel) else 120), panel.get_rect(), 3 if sel else 2, border_radius=14)
            screen.blit(panel, r.topleft)
            scx, scy = r.x + int(70 * UI), r.centery
            draw_glow(screen, (scx, scy), 60 * UI, tuple(int(c * 0.4) for c in ship["color"]), 140)
            Player.draw_ship(None, screen, scx, scy, tt * 0.001, 3.0 * UI, ship["color"])
            blit_text(screen, ship["name"][li], 22, (240, 240, 255), (r.x + int(140 * UI), r.y + int(16 * UI)), bold=True)
            for j, line in enumerate(wrap_lines(ship["desc"][li], 15, r.w - int(160 * UI))):
                blit_text(screen, line, 15, (180, 190, 220), (r.x + int(140 * UI), r.y + int(50 * UI) + j * int(20 * UI)))
            status = L("выбран", "selected") if sel else L("выбрать", "select") if owned else L(f"{ship['cost']} осколков", f"{ship['cost']} shards")
            blit_text(screen, status, 17, GOLD if not owned else (180, 255, 220) if sel else HUD_TEXT,
                      (r.right - int(16 * UI), r.bottom - int(14 * UI)), "bottomright", True)
        if msg:
            blit_text(screen, msg, 20, (180, 255, 220), (WIDTH // 2, HEIGHT - int(130 * UI)), "center")
        back.draw()
        draw_cursor()
        pygame.display.flip()
        clock.tick(60)


# =====================================================================
#  Главное меню — живой «Космический шторм» на фоне
# =====================================================================
def main_menu():
    play_music("night.mp3")
    bg = Background("night")
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    # корабль на фоне летает сам — как в «Космическом шторме»
    sx, sy, svx, svy = WIDTH * 0.3, HEIGHT * 0.6, 0.0, 0.0
    target = (WIDTH * 0.7, HEIGHT * 0.4)
    trail = []
    echoes = []
    slider = pygame.Rect(WIDTH - int(250 * UI), int(40 * UI), int(170 * UI), int(8 * UI))
    flag_rect = pygame.Rect(WIDTH - int(62 * UI), int(26 * UI), int(40 * UI), int(28 * UI))
    dragging = False
    while True:
        cy = int(HEIGHT * 0.5)
        bw = int(380 * UI)
        b_play = Button(L("Новый забег", "New run"), (WIDTH // 2, cy), bw, HUD_TITLE, 26)
        b_obs = Button(L("Обсерватория", "Observatory"), (WIDTH // 2, cy + int(80 * UI)), bw, GOLD, 24)
        b_quit = Button(L("Выход", "Quit"), (WIDTH // 2, cy + int(160 * UI)), bw, (180, 180, 210), 24)
        for e in get_events():
            if b_play.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN):
                sfx("click")
                return "play"
            if b_obs.clicked(e):
                sfx("click")
                return "observatory"
            if b_quit.clicked(e) or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                return "quit"
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if slider.inflate(20, 30).collidepoint(e.pos):
                    dragging = True
                elif flag_rect.collidepoint(e.pos):
                    SAVE["language"] = "en" if SAVE["language"] == "ru" else "ru"
                    write_save()
                    sfx("click")
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and dragging:
                dragging = False
                write_save()
        if dragging:
            SAVE["volume"] = max(0.0, min(1.0, (pygame.mouse.get_pos()[0] - slider.x) / slider.w))
            apply_volume()
        # автопилот
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
        Player.draw_ship(None, layer, sx, sy, heading, 1.0, SHIP_BLUE)
        bx, by = sx - 10 * math.cos(heading), sy - 10 * math.sin(heading)
        for i in range(3):
            px, py = bx - (i * 6) * math.cos(heading), by - (i * 6) * math.sin(heading)
            pygame.draw.circle(layer, (*FLAME_PARTICLE, random.randint(150, 200)), (int(px), int(py)), random.randint(2, 4))
        screen.blit(layer, (0, 0))
        # заголовок
        t = pygame.time.get_ticks()
        title = L("ЗВЁЗДНЫЙ ШТОРМ", "STAR STORM")
        ty = int(HEIGHT * 0.25)
        draw_glow(screen, (WIDTH // 2, ty), 340 * UI, (40, 60, 140), 110)
        blit_text(screen, title, 84, (int(200 + 30 * math.sin(t * 0.002)), 210, 255), (WIDTH // 2, ty), "center", True)
        blit_text(screen, L("космический рогалик", "a cosmic roguelite"), 22, HUD_TEXT, (WIDTH // 2, ty + int(66 * UI)), "center")
        b_play.draw()
        b_obs.draw()
        b_quit.draw()
        # статистика
        info = L(f"Осколки: {SAVE['shards']}   Забегов: {SAVE['runs']}   Побед: {SAVE['wins']}   Лучший сектор: {min(3, SAVE['best_sector'])}",
                 f"Shards: {SAVE['shards']}   Runs: {SAVE['runs']}   Wins: {SAVE['wins']}   Best sector: {min(3, SAVE['best_sector'])}")
        blit_text(screen, info, 17, (150, 160, 200), (WIDTH // 2, HEIGHT - int(70 * UI)), "center")
        blit_text(screen, L("по мотивам «Космического шторма» из Relacs", "based on Cosmic Storm from Relacs"), 14,
                  (90, 100, 140), (WIDTH // 2, HEIGHT - int(40 * UI)), "center")
        blit_text(screen, f"{L('Громкость', 'Volume')} {int(SAVE['volume'] * 100)}%", 15, (180, 190, 220), (slider.x, slider.y - int(26 * UI)))
        pygame.draw.rect(screen, (50, 60, 100), slider, border_radius=4)
        pygame.draw.rect(screen, HUD_TEXT, (slider.x, slider.y, int(slider.w * SAVE["volume"]), slider.h), border_radius=4)
        pygame.draw.circle(screen, (220, 230, 255), (slider.x + int(slider.w * SAVE["volume"]), slider.centery), int(9 * UI))
        fx, fy, fs = flag_rect.x, flag_rect.y, flag_rect.w
        if SAVE["language"] == "ru":
            pygame.draw.rect(screen, (255, 255, 255), (fx, fy, fs, flag_rect.h // 3))
            pygame.draw.rect(screen, (0, 57, 166), (fx, fy + flag_rect.h // 3, fs, flag_rect.h // 3))
            pygame.draw.rect(screen, (213, 43, 30), (fx, fy + 2 * flag_rect.h // 3, fs, flag_rect.h - 2 * (flag_rect.h // 3)))
        else:
            stripe = flag_rect.h / 13
            for i in range(13):
                pygame.draw.rect(screen, (178, 34, 52) if i % 2 == 0 else (255, 255, 255), (fx, int(fy + i * stripe), fs, int(stripe) + 1))
            pygame.draw.rect(screen, (60, 59, 110), (fx, fy, fs * 2 // 5, int(stripe * 7)))
        pygame.draw.rect(screen, (200, 200, 220), flag_rect.inflate(4, 4), 1, border_radius=3)
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
        else:
            break
    quit_game()


if __name__ == "__main__":
    main()
