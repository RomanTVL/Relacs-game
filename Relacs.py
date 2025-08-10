import pygame
import random
import math
import os
import time
import colorsys
import numpy as np
import threading
import queue
import pyaudio
pygame.init()
pygame.mixer.init()


screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("🔥 Огонь за курсором")
game_flags = {
    "relax_done": False,
    "cosmic_done": False,
    "main_done": False
}
# Музыка
if os.path.exists("Relacs.mp3"):
    pygame.mixer.music.load("Relacs.mp3")
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
else:
    print("Файл burning.mp3 не найден!")
clock = pygame.time.Clock()
pygame.mouse.set_visible(False)
# Глобальные переменные
language = "ru"  # Язык по умолчанию
flag_is_russian = True  # Флаг: True — Россия, False — США
# Темы
THEMES = {
    "classic": {
        "bg": (10, 10, 20),
        "colors": [(255, 120, 0), (255, 60, 0), (255, 200, 50), (255, 255, 255)],
        "spark": (255, 255, 100)
    },
    "blue": {
        "bg": (5, 10, 30),
        "colors": [(100, 180, 255), (50, 120, 255), (200, 230, 255), (255, 255, 255)],
        "spark": (150, 200, 255)
    },
    "violet": {
        "bg": (20, 5, 30),
        "colors": [(200, 50, 255), (150, 30, 200), (255, 200, 255), (255, 255, 255)],
        "spark": (255, 150, 255)
    }
}
theme_names = list(THEMES.keys())
current_theme = 0
theme_last_swap = time.time()
THEME_SWAP_INTERVAL = 30
input_mode = False
input_buffer = ""
emotion_mode = None
emotion_timer = 0
slow_motion = False
show_menu = False
show_sparks = True
gravity_enabled = False
show_stars = True
show_life = True
intensity = 1.0
chaos_mode = False
floating_texts = []
creatures = []
comets = []
class FloatingText:
    def __init__(self):
        self.text = random.choice(["🔥", "АГОНИЯ", "ВСЁ ГОРИТ", "КРАСОТА", "КАША", "БРЕД", "ПОЖАР"])
        self.font = pygame.font.SysFont("consolas", random.randint(20, 40))
        self.x = random.randint(0, WIDTH)
        self.y = HEIGHT + 20
        self.vy = random.uniform(-1.5, -0.5)
        self.life = random.randint(60, 150)
        self.color = [random.randint(100, 255) for _ in range(3)]

    def update(self):
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        surf = self.font.render(self.text, True, self.color)
        surface.blit(surf, (self.x, self.y))
class Creature:
    def __init__(self):
        self.x = random.choice([-50, WIDTH + 50])
        self.y = random.randint(HEIGHT // 3, HEIGHT - 100)
        self.vx = random.choice([-1, 1]) * random.uniform(0.5, 1.5)
        self.size = random.randint(20, 40)
        self.color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))

    def update(self):
        self.x += self.vx
        return -100 < self.x < WIDTH + 100

    def draw(self, surface):
        pygame.draw.ellipse(surface, self.color, (self.x, self.y, self.size, self.size / 2))
def update_and_draw_fire_particles(particles, mx, my, intensity=1.0):
    for _ in range(int(5 * intensity)):
        particles.append({
            "pos": [mx, my],
            "vel": [random.uniform(-1, 1), random.uniform(-2, -0.5)],
            "life": random.randint(30, 60),
            "color": (255, random.randint(100, 180), 50)
        })

    for p in particles[:]:
        p["pos"][0] += p["vel"][0]
        p["pos"][1] += p["vel"][1]
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)
        else:
            alpha = max(0, min(255, int(255 * (p["life"] / 60))))
            pygame.draw.circle(screen, p["color"] + (alpha,), (int(p["pos"][0]), int(p["pos"][1])), 4)
def run_relax_scene():
    relax_running = True
    fire_particles = []
    stars = generate_stars(100)

    while relax_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                relax_running = False

        draw_gradient_background(screen, (10, 10, 20))
        update_and_draw_stars(stars)
        update_and_draw_fire_particles(fire_particles, WIDTH // 2, HEIGHT // 2)

        pygame.display.flip()
        clock.tick(30)
def draw_cosmic_background(screen, time_elapsed):
    base_color = (5, 5, 25)
    pulse = int(20 * math.sin(time_elapsed * 0.3))  # пульсация
    bg_color = (
        max(0, base_color[0] + pulse),
        max(0, base_color[1] + pulse),
        max(0, base_color[2] + pulse * 2)
    )
    screen.fill(bg_color)

    # Нарисуем движущиеся звезды
    star_count = 100
    for i in range(star_count):
        angle = (time_elapsed * 0.05 + i) % (2 * math.pi)
        radius = (i % 30) * 3 + 10
        x = int(WIDTH // 2 + radius * math.cos(angle + i))
        y = int(HEIGHT // 2 + radius * math.sin(angle + i))
        brightness = 100 + int(100 * math.sin(time_elapsed * 0.5 + i))
        pygame.draw.circle(screen, (brightness, brightness, brightness), (x, y), 1)
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.randint(6, 12)
        self.color = (255, 255, random.randint(200, 255))
        self.angle = 0
        self.blink = 255

    def draw(self, surface):
        self.angle += 0.01
        if chaos_mode:
            self.blink = random.randint(50, 255)
        points = []
        for i in range(5):
            outer = (self.x + math.cos(self.angle + i * 2 * math.pi / 5) * self.size,
                     self.y + math.sin(self.angle + i * 2 * math.pi / 5) * self.size)
            inner = (self.x + math.cos(self.angle + i * 2 * math.pi / 5 + math.pi / 5) * self.size / 2,
                     self.y + math.sin(self.angle + i * 2 * math.pi / 5 + math.pi / 5) * self.size / 2)
            points.extend([outer, inner])
        color = (*self.color[:2], self.blink) if chaos_mode else self.color
        pygame.draw.polygon(surface, color, points)
class EnergyWave:
    def __init__(self, pos):
        self.x, self.y = pos
        self.radius = 1
        self.max_radius = 300
        self.width = 4
        self.alpha = 180

    def update(self):
        self.radius += 6
        self.alpha -= 4
        return self.radius < self.max_radius and self.alpha > 0

    def draw(self, surface):
        if self.alpha <= 0:
            return
        color = (100, 200, 255, self.alpha)
        surf = pygame.Surface((self.max_radius*2, self.max_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (self.max_radius, self.max_radius), self.radius, width=self.width)
        surface.blit(surf, (self.x - self.max_radius, self.y - self.max_radius))
def run_illusion_mode():
    glitch_timer = 0
    font = pygame.font.SysFont("consolas", 32, bold=True)
    # === Переводы для Illusion Mode ===
    global language
    trans_illusion = {
        'ru': {
            'messages': [
                "Ничего не реально...",
                "ОНИ НАБЛЮДАЮТ за тобой!",
                "Система нестабильна...",
                "Ты уверен, что это игра?",
                "Реальность тает..."
            ]
        },
        'en': {
            'messages': [
                "Nothing is real...",
                "THEY ARE WATCHING YOU!",
                "System unstable...",
                "Are you sure this is a game?",
                "Reality is dissolving..."
            ]
        }
    }

    def draw_glitch_effect(surface):
        for _ in range(6):  # Увеличил для большей динамики
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            w, h = random.randint(20, 60), random.randint(2, 8)
            color = random.choice([(255, 0, 255, 150), (0, 255, 255, 150), (255, 255, 0, 120)])
            pygame.draw.rect(surface, color, (x, y, w, h))
            pygame.draw.line(surface, (255, 255, 255, 100), (x, y), (x + w, y + h), 2)

    phantom_cursor = pygame.Surface((25, 25), pygame.SRCALPHA)
    pygame.draw.circle(phantom_cursor, (255, 0, 255, 200), (12, 12), 8)
    pygame.draw.circle(phantom_cursor, (0, 255, 255, 100), (12, 12), 4, 1)

    illusion_start_time = pygame.time.get_ticks()
    glitch_sound = pygame.mixer.Sound("glitch.wav") if os.path.exists("glitch.wav") else None

    while True:
        dt = clock.tick(60)
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if pygame.time.get_ticks() - illusion_start_time > 5000:
            if glitch_sound:
                glitch_sound.play()
            run_final_sequence()
            return

        screen.fill((0, 0, 0))
        offset_x, offset_y = math.sin(time.time() * 4) * 8, math.cos(time.time() * 5) * 8

        distorted_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_glitch_effect(distorted_surf)
        distorted_surf.set_alpha(180 + int(75 * math.sin(time.time())))

        if glitch_timer <= 0:
            glitch_timer = random.randint(20, 60)
            current_message = random.choice(trans_illusion[language]['messages'])
            if glitch_sound:
                glitch_sound.play()
        else:
            glitch_timer -= 1

        txt = font.render(current_message, True, random.choice([(255, 0, 255), (0, 255, 255, 200)]))
        txt_shadow = font.render(current_message, True, (0, 0, 0, 150))
        distorted_surf.blit(txt_shadow, (WIDTH // 2 - txt.get_width() // 2 + offset_x + 2, HEIGHT // 2 - txt.get_height() // 2 + offset_y + 2))
        distorted_surf.blit(txt, (WIDTH // 2 - txt.get_width() // 2 + offset_x, HEIGHT // 2 - txt.get_height() // 2 + offset_y))

        screen.blit(distorted_surf, (0, 0))
        screen.blit(phantom_cursor, (mx + random.randint(-15, 15), my + random.randint(-15, 15)))

        pygame.display.flip()
def run_final_sequence():
    end_font = pygame.font.SysFont("consolas", 36, bold=True)
    small_font = pygame.font.SysFont("consolas", 24, italic=True)
    start_time = pygame.time.get_ticks()
    duration = 6000

    # === Переводы для Final Sequence ===
    global language
    trans_final = {
        'ru': {
            'phrases': [
                "…все фрагменты собраны.",
                "ты вспомнил, кто ты есть.",
                "реальность — это ты сам.",
                "освобождение… свет зовёт."
            ],
            'reboot': "REBOOTING..."
        },
        'en': {
            'phrases': [
                "...all fragments are collected.",
                "you remember who you are.",
                "reality — it's you.",
                "liberation… the light calls."
            ],
            'reboot': "REBOOTING..."
        }
    }

    reboot_time = None
    reboot_font = pygame.font.SysFont("consolas", 32)
    pulse_effect = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        now = pygame.time.get_ticks()
        elapsed = now - start_time
        screen.fill((0, 0, 0))

        if elapsed < duration:
            index = min(len(trans_final[language]['phrases']) - 1, elapsed // 1500)
            alpha = 255 - abs(int(math.sin(elapsed * 0.006) * 200))
            pulse = int(100 * math.sin(elapsed * 0.01))
            pulse = max(0, min(255, pulse))  # Безопасное значение

            # Основной текст
            text_content = trans_final[language]['phrases'][index]
            text = end_font.render(text_content, True, (255, 255, 255))
            # Тень (тёмный цвет, не с альфа-каналом)
            shadow = end_font.render(text_content, True, (30, 30, 60))

            x_pos = WIDTH // 2 - text.get_width() // 2
            y_pos = HEIGHT // 2 - 40

            screen.blit(shadow, (x_pos + 2, y_pos + 2))
            screen.blit(text, (x_pos, y_pos))

            # Пульсирующий эффект
            pulse_effect.fill((pulse, pulse, pulse, 50))
            screen.blit(pulse_effect, (0, 0))

        elif reboot_time is None:
            reboot_time = now

        elif now - reboot_time > 1000:
            blink = int((now // 500) % 2) == 0
            if blink:
                reboot_text = trans_final[language]['reboot']
                reboot_txt = reboot_font.render(reboot_text, True, (200, 200, 200))
                reboot_shadow = reboot_font.render(reboot_text, True, (80, 80, 80))

                x_pos = WIDTH // 2 - reboot_txt.get_width() // 2
                y_pos = HEIGHT // 2

                screen.blit(reboot_shadow, (x_pos + 2, y_pos + 2))
                screen.blit(reboot_txt, (x_pos, y_pos))

        if reboot_time and now - reboot_time > 3000:
            void_mode()
            return

        pygame.display.flip()
        clock.tick(60)
def void_mode():
    pygame.mouse.set_visible(False)
    running = True
    clock = pygame.time.Clock()

    font_large = pygame.font.SysFont("consolas", 48, bold=True)
    font_small = pygame.font.SysFont("consolas", 24, italic=True)

    message_timer = pygame.time.get_ticks()
    show_point = True
    text_alpha = 255
    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(50)]

    portal_radius = 20
    choice_made = False

    # === Переводы для Void Mode ===
    global language
    trans_void = {
        'ru': {
            'voice_lines': [
                "Ты всё ещё здесь...",
                "Пустота не отпускает тебя.",
                "Войти или остаться в тени?"
            ],
            'hint': "[SPACE] Войти    [ESC] Остаться"
        },
        'en': {
            'voice_lines': [
                "You're still here...",
                "The void won't let you go.",
                "Enter or remain in the shadows?"
            ],
            'hint': "[SPACE] Enter    [ESC] Stay"
        }
    }

    line_index = 0
    line_timer = pygame.time.get_ticks()
    last_glitch_time = 0
    glitch_alpha = 0

    while running:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if line_index >= len(trans_void[language]['voice_lines']):
                    if event.key == pygame.K_SPACE:
                        choice_made = True
                        run_memory_echo_mode()
                        return
                    elif event.key == pygame.K_ESCAPE:
                        return

        screen.fill((2, 2, 5))

        # Отрисовка звёзд
        for x, y in stars:
            size = random.randint(1, 3)
            alpha = random.randint(150, 250)
            pygame.draw.circle(screen, (100, 150, 255, alpha), (x, y), size)

        # Мигающая точка в центре
        if show_point and now % 1000 < 500:
            pygame.draw.circle(screen, (150, 100, 255, 200), (WIDTH // 2, HEIGHT // 2), 3)
            pygame.draw.circle(screen, (255, 200, 255, 100), (WIDTH // 2, HEIGHT // 2), 6, 1)

        # Обновление реплик
        if now - line_timer > 2000 and line_index < len(trans_void[language]['voice_lines']):
            line_timer = now
            line_index += 1

        # Отрисовка реплик
        if line_index > 0 and line_index <= len(trans_void[language]['voice_lines']):
            text_content = trans_void[language]['voice_lines'][line_index - 1]
            text = font_small.render(text_content, True, (200, 200, 255))
            shadow = font_small.render(text_content, True, (30, 30, 60))  # Тёмная тень
            x_pos = WIDTH // 2 - text.get_width() // 2
            y_pos = HEIGHT - 100
            screen.blit(shadow, (x_pos + 2, y_pos + 2))
            screen.blit(text, (x_pos, y_pos))
            text_alpha = max(0, text_alpha - 1)

        # Анимация портала и подсказка
        if line_index >= len(trans_void[language]['voice_lines']):
            portal_radius += math.sin(pygame.time.get_ticks() * 0.008) * 2
            portal_color = (120, 0, 200, int(150 + 50 * math.sin(now * 0.01)))
            pygame.draw.circle(screen, portal_color, (WIDTH // 2, HEIGHT // 2), int(portal_radius), 3)
            pygame.draw.circle(screen, (255, 100, 255, 50), (WIDTH // 2, HEIGHT // 2), int(portal_radius * 0.7), 1)

            # Подсказка
            hint_text = trans_void[language]['hint']
            hint = font_small.render(hint_text, True, (255, 255, 255))
            hint_shadow = font_small.render(hint_text, True, (80, 80, 100))
            hint_x = WIDTH // 2 - hint.get_width() // 2
            hint_y = HEIGHT - 60
            screen.blit(hint_shadow, (hint_x + 2, hint_y + 2))
            screen.blit(hint, (hint_x, hint_y))

        # Эффект глитча
        if now - last_glitch_time > 1000:
            last_glitch_time = now
            glitch_alpha = random.randint(30, 120)

        if glitch_alpha > 0:
            glitch = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            glitch.fill((255, 0, 255, glitch_alpha))
            offset_x = random.randint(-15, 15)
            offset_y = random.randint(-15, 15)
            screen.blit(glitch, (offset_x, offset_y))
            glitch_alpha -= 3

        pygame.display.flip()
class MemoryFragment:
    def __init__(self, pos, text, callback=None):
        self.pos = pos
        self.text = text
        self.activated = False
        self.rect = pygame.Rect(pos[0] - 100, pos[1] - 50, 230, 130)  # Увеличенные овалы
        self.callback = callback
        self.glow = 0

    def update(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos) and not self.activated:
            self.activated = True
            self.glow = 255
            if self.callback:
                self.callback()

    def draw(self, surface):
        color = (150, 200, 255) if self.activated else (50, 80, 150)
        glow_surface = pygame.Surface((self.rect.width + 10, self.rect.height + 10), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surface, (*color, min(25, self.glow // 10)), glow_surface.get_rect(), 0)  # Ещё более прозрачное свечение
        surface.blit(glow_surface, (self.rect.x - 5, self.rect.y - 5))
        # Сильно прозрачный овал
        oval_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(oval_surface, (*color, 50), (0, 0, self.rect.width, self.rect.height))  # Сильно прозрачный овал
        surface.blit(oval_surface, self.rect.topleft)
        pygame.draw.ellipse(surface, (*color, 150), self.rect, 4)  # Контур с умеренной непрозрачностью
        if self.glow > 0:
            self.glow -= 5
        font = pygame.font.SysFont("consolas", 16)
        text = font.render(self.text, True, (255, 255, 255))
        surface.blit(text, (self.rect.centerx - text.get_width() // 2, self.rect.centery - text.get_height() // 2))
def run_memory_echo_mode():
    font = pygame.font.SysFont("consolas", 28)

    # === Переводы ===
    global language
    trans_memory = {
        'ru': {
            'fragments': [
                "Ты стоял у окна...",
                "Голоса были знакомы",
                "Что-то было забыто",
                "Тени дрожали на стене",
                "Свет резал глаза",
                "Это уже случалось"
            ],
            'final': "Память восстановлена... свет пробивается."
        },
        'en': {
            'fragments': [
                "You stood by the window...",
                "The voices were familiar",
                "Something was forgotten",
                "Shadows trembled on the wall",
                "Light pierced your eyes",
                "This has happened before"
            ],
            'final': "Memory restored... light breaks through."
        }
    }

    # === Фрагменты памяти ===
    fragments = [
        MemoryFragment((200, 180), trans_memory[language]['fragments'][0], callback=memory_scene_1),
        MemoryFragment((WIDTH - 220, 200), trans_memory[language]['fragments'][1], callback=memory_scene_2),
        MemoryFragment((WIDTH // 2, 140), trans_memory[language]['fragments'][2], callback=memory_scene_3),
        MemoryFragment((160, HEIGHT - 160), trans_memory[language]['fragments'][3], callback=memory_scene_4),
        MemoryFragment((WIDTH // 2, HEIGHT - 100), trans_memory[language]['fragments'][4], callback=memory_scene_5),
        MemoryFragment((WIDTH - 200, HEIGHT - 150), trans_memory[language]['fragments'][5], callback=memory_scene_6),
    ]

    glow_timer = 0
    running = True
    finished = False
    finish_timer = 0
    fade_alpha = 0
    stars = generate_stars(30)

    while running:
        screen.fill((10, 10, 30))
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        glow_timer += 1
        glow_radius = 20 + math.sin(glow_timer * 0.05) * 5
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 255, 255, 100), (40, 40), int(glow_radius))
        screen.blit(glow, (mx - 40, my - 40))
        pygame.draw.circle(screen, (255, 255, 255), (mx, my), 5)

        update_and_draw_stars(stars)

        all_activated = all(f.activated for f in fragments)
        for fragment in fragments:
            fragment.update((mx, my))
            fragment.draw(screen)

        if all_activated and not finished:
            finish_timer = pygame.time.get_ticks()
            finished = True

        if finished:
            elapsed = pygame.time.get_ticks() - finish_timer
            if elapsed > 300:
                fade_alpha = min(255, fade_alpha + 2)
                txt = font.render(trans_memory[language]['final'], True, (255, 255, 255))
                txt.set_alpha(fade_alpha)
                txt_shadow = font.render(trans_memory[language]['final'], True, (0, 0, 0, fade_alpha // 2))
                screen.blit(txt_shadow, (WIDTH // 2 - txt.get_width() // 2 + 2, HEIGHT // 2 + 120 + 2))
                screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 + 120))

            if fade_alpha >= 255 and elapsed > 2000:
                run_void_reveal()
                return

        pygame.display.flip()
        clock.tick(60)
def fade_to_memory(text_lines, bg_color, fog_color=(0, 0, 0, 100), glitch=False):
    font = pygame.font.SysFont("consolas", 36, bold=True)
    timer = 0
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    stars = generate_stars(40)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill(bg_color)

        fade_surface.fill(fog_color)
        screen.blit(fade_surface, (0, 0))

        if glitch and random.random() < 0.3:
            for _ in range(6):
                glitch_rect = pygame.Rect(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(10, 100), 3)
                pygame.draw.rect(screen, (random.randint(200, 255), 0, random.randint(0, 100)), glitch_rect)
                pygame.draw.line(screen, (255, 255, 255, 50), (glitch_rect.left, glitch_rect.top), (glitch_rect.right, glitch_rect.bottom), 1)

        if timer > 30:
            for i, line in enumerate(text_lines):
                text = font.render(line, True, (255, 255, 255))
                text_shadow = font.render(line, True, (0, 0, 0, 150))
                screen.blit(text_shadow, (WIDTH // 2 - text.get_width() // 2 + 2, HEIGHT // 2 + i * 40 - 20 + 2))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 + i * 40 - 20))

        timer += 1
        if timer > 250:  # Увеличил до 2.5 секунд для плавности
            return

        pygame.display.flip()
        clock.tick(60)
def memory_scene_1():
    trans = {
        'ru': ["Ты стоял у окна...", "Свет заливал комнату.", "Тишина обнимала."],
        'en': ["You stood by the window...", "Light filled the room.", "Silence embraced you."]
    }
    fade_to_memory(trans[language], (30, 20, 60), fog_color=(80, 60, 120, 100))
def memory_scene_2():
    trans = {
        'ru': ["Голоса знакомы...", "Они звали тебя издалека.", "Тени шептались."],
        'en': ["Voices are familiar...", "They called you from afar.", "Shadows whispered."]
    }
    fade_to_memory(trans[language], (10, 10, 30), fog_color=(0, 0, 50, 160), glitch=True)
def memory_scene_3():
    trans = {
        'ru': ["Забыто...", "Как обрывок сна.", "Но оно медленно возвращается."],
        'en': ["Forgotten...", "Like a dream fragment.", "But it slowly returns."]
    }
    fade_to_memory(trans[language], (0, 0, 0), fog_color=(0, 0, 0, 220), glitch=True)
def memory_scene_4():
    trans = {
        'ru': ["Кто-то звал тебя...", "Обернулся — никого.", "Только эхо в стенах."],
        'en': ["Someone called you...", "You turned — no one.", "Only echoes in the walls."]
    }
    fade_to_memory(trans[language], (20, 0, 40), fog_color=(50, 0, 50, 160))
def memory_scene_5():
    trans = {
        'ru': ["Свет был ярким...", "Резал глаза до слёз.", "Ты не мог отвернуться."],
        'en': ["The light was bright...", "It pierced your eyes to tears.", "You couldn't look away."]
    }
    fade_to_memory(trans[language], (200, 180, 180), fog_color=(255, 240, 240, 100))
def memory_scene_6():
    trans = {
        'ru': ["Дежавю...", "Ты уже видел это.", "Почему оно повторяется снова?"],
        'en': ["Déjà vu...", "You've seen this before.", "Why is it happening again?"]
    }
    fade_to_memory(trans[language], (0, 0, 0), fog_color=(0, 0, 0, 220), glitch=True)
def memory_scene_7():
    trans = {
        'ru': ["Тишина окутала...", "Только эхо звучит.", "Пустота смотрит на тебя."],
        'en': ["Silence enveloped...", "Only echoes remain.", "The void watches you."]
    }
    fade_to_memory(trans[language], (10, 10, 20), fog_color=(20, 20, 40, 180), glitch=True)
def memory_scene_8():
    trans = {
        'ru': ["Кто-то шёл за тобой...", "Тени сливались в темноте.", "Ты слышал шаги."],
        'en': ["Someone followed you...", "Shadows merged in darkness.", "You heard footsteps."]
    }
    fade_to_memory(trans[language], (30, 10, 50), fog_color=(60, 20, 80, 160))
def memory_scene_9():
    trans = {
        'ru': ["Свет исчез во тьме...", "Тьма поглотила всё.", "Остался только холод."],
        'en': ["Light vanished into darkness...", "Darkness consumed everything.", "Only cold remains."]
    }
    fade_to_memory(trans[language], (0, 0, 10), fog_color=(0, 0, 20, 220), glitch=True)
def run_void_reveal():
    fragments_reconstructed = False
    glitch_timer = 0
    reveal_timer = pygame.time.get_ticks()
    font = pygame.font.SysFont("consolas", 28, bold=True)
    message_shown = False
    stars = generate_stars(40)

    # === Переводы для Void Reveal ===
    global language
    trans_reveal = {
        'ru': {
            'loading': "...",
            'discovered': "Система обнаружила глубинный фрагмент.",
            'enter': "Вход в сектор: [ОТКЛИК]."
        },
        'en': {
            'loading': "...",
            'discovered': "System detected deep fragment.",
            'enter': "Enter sector: [ECHO]."
        }
    }

    while True:
        screen.fill((5, 0, 15))
        update_and_draw_stars(stars)

        elapsed = pygame.time.get_ticks() - reveal_timer

        if elapsed < 2000:
            # Медленная загрузка
            txt = font.render(trans_reveal[language]['loading'], True, (180, 180, 255))
            shadow = font.render(trans_reveal[language]['loading'], True, (30, 30, 60))
            x = WIDTH // 2 - txt.get_width() // 2
            y = HEIGHT // 2
            screen.blit(shadow, (x + 2, y + 2))
            screen.blit(txt, (x, y))

        elif elapsed < 5000:
            # Эффект глитча
            glitch_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(60):
                x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                w, h = random.randint(1, 30), random.randint(1, 5)
                color = random.choice([(255, 0, 0, 150), (0, 255, 255, 150)])
                pygame.draw.rect(glitch_surface, color, (x, y, w, h))
                pygame.draw.line(glitch_surface, (255, 255, 255, 80), (x, y), (x + w, y + h), 1)
            screen.blit(glitch_surface, (0, 0))

        else:
            # Сообщение о входе
            if not message_shown:
                message_timer = pygame.time.get_ticks()
                message_shown = True

            txt1 = font.render(trans_reveal[language]['discovered'], True, (255, 255, 255))
            txt2 = font.render(trans_reveal[language]['enter'], True, (255, 100, 255))
            shadow1 = font.render(trans_reveal[language]['discovered'], True, (30, 30, 60))
            shadow2 = font.render(trans_reveal[language]['enter'], True, (30, 30, 60))

            x1 = WIDTH // 2 - txt1.get_width() // 2
            x2 = WIDTH // 2 - txt2.get_width() // 2
            y1 = HEIGHT // 2 - 30
            y2 = HEIGHT // 2 + 10

            screen.blit(shadow1, (x1 + 2, y1 + 2))
            screen.blit(txt1, (x1, y1))
            screen.blit(shadow2, (x2 + 2, y2 + 2))
            screen.blit(txt2, (x2, y2))

            if pygame.time.get_ticks() - message_timer > 3000:
                run_memory_core()
                return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        pygame.display.flip()
        clock.tick(60)
def run_memory_core():
    running = True
    font = pygame.font.SysFont("consolas", 25, bold=True)
    big_font = pygame.font.SysFont("consolas", 40, bold=True)
    clock = pygame.time.Clock()

    portal_width = 150
    portal_spacing = (WIDTH - 5 * portal_width) // 6

    total_width = 5 * portal_width + 4 * portal_spacing
    start_x = (WIDTH - total_width) // 2
    # === Переводы для кнопок ===
    global language
    trans = {
        'ru': {
            'merge': 'Слияние',
            'forget': 'Забвение',
            'escape': 'Выход',
            'harmony': 'Гармония',
            'chaos': 'Хаос',
            'prompt': 'Сделай свой выбор...'
        },
        'en': {
            'merge': 'Merge',
            'forget': 'Forget',
            'escape': 'Escape',
            'harmony': 'Harmony',
            'chaos': 'Chaos',
            'prompt': 'Make your choice...'
        }
    }[language]
    portals = {
        trans['merge']: pygame.Rect(start_x, HEIGHT // 2 - 75, portal_width, 150),
        trans['forget']: pygame.Rect(start_x + portal_width + portal_spacing, HEIGHT // 2 - 75, portal_width, 150),
        trans['escape']: pygame.Rect(start_x + 2 * (portal_width + portal_spacing), HEIGHT // 2 - 75, portal_width,
                                     150),
        trans['harmony']: pygame.Rect(start_x + 3 * (portal_width + portal_spacing), HEIGHT // 2 - 75, portal_width,
                                      150),
        trans['chaos']: pygame.Rect(start_x + 4 * (portal_width + portal_spacing), HEIGHT // 2 - 75, portal_width, 150)
    }

    hover = None
    chosen = None
    current_time = pygame.time.get_ticks()

    # Load hover sound if available
    hover_sound = pygame.mixer.Sound("hover.wav") if os.path.exists("hover.wav") else None

    # Particles and effects
    particles = {
        trans['merge']: [],
        trans['forget']: [],
        trans['harmony']: [],
        trans['chaos']: []
    }
    # Stars effect
    stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3), random.uniform(0.5, 1.5)] for _ in range(50)]  # [x, y, size, brightness]

    while running:
        # Clear screen
        screen.fill((0, 0, 0))

        mx, my = pygame.mouse.get_pos()
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEMOTION:
                hover = None
                for key, rect in portals.items():
                    if rect.collidepoint(event.pos):
                        hover = key
                        if hover_sound and hover != key:
                            hover_sound.play()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for key, rect in portals.items():
                    if rect.collidepoint(event.pos):
                        chosen = key
                        if chosen == trans['merge']:
                            run_merge_ending()
                        elif chosen == trans['forget']:
                            run_forget_ending()
                        elif chosen == trans['escape']:
                            run_escape_ending()
                        elif chosen == trans['harmony']:
                            run_harmony_ending()
                        elif chosen == trans['chaos']:
                            run_chaos_ending()
                        return
        # Draw stars
        r, g, b = 100, 100, 100
        for star in stars:
            x, y, size, brightness = star
            # Заменяем только строку с alpha
            alpha = max(0, min(255, int(200 * brightness * (0.5 + 0.5 * math.sin(current_time * 0.001 + x + y)))))
            pygame.draw.circle(screen, (255, 255, 255, alpha), (int(x), int(y)), size)

        # Draw buttons and effects
        for key, rect in portals.items():
            # Lift effect on hover
            lift_offset = -10 if hover == key else 0
            lifted_rect = rect.move(0, lift_offset)

            # Gradient surface with extra padding for effects
            gradient_button = pygame.Surface((lifted_rect.width + 10, lifted_rect.height + 10), pygame.SRCALPHA)
            for y in range(lifted_rect.height + 10):
                if key == trans['merge']:
                    r = max(0, min(255, int(50 + (0 * y / lifted_rect.height))))  # Увеличена яркость
                    g = max(0, min(255, int(150 + (200 * y / lifted_rect.height))))
                    b = max(0, min(255, int(240 + (50 * y / lifted_rect.height))))
                elif key == trans['forget']:
                    r = max(0, min(255, int(150 + (50 * y / lifted_rect.height))))
                    g = max(0, min(255, int(70 + (100 * y / lifted_rect.height))))
                    b = max(0, min(255, int(200 + (0 * y / lifted_rect.height))))
                elif key == trans['escape']:
                    r = max(0, min(255, int(255 + (0 * y / lifted_rect.height))))
                    g = max(0, min(255, int(255 + (0 * y / lifted_rect.height))))
                    b = max(0, min(255, int(255 + (0 * y / lifted_rect.height))))
                elif key == trans['harmony']:
                    r = max(0, min(255, int(50 + (100 * y / lifted_rect.height))))
                    g = max(0, min(255, int(200 + (50 * y / lifted_rect.height))))
                    b = max(0, min(255, int(140 + (80 * y / lifted_rect.height))))
                elif key == trans['chaos']:
                    r = max(0, min(255, int(255 + (-50 * y / lifted_rect.height))))
                    g = max(0, min(255, int(80 + (0 * y / lifted_rect.height))))
                    b = max(0, min(255, int(20 + (60 * y / lifted_rect.height))))
                alpha = 200 if hover == key else 150
                pygame.draw.line(gradient_button, (r, g, b, alpha), (0, y), (lifted_rect.width + 10, y))
            # Используем rect для квадратных кнопок
            screen.blit(gradient_button, (lifted_rect.x - 5, lifted_rect.y - 5))
            pygame.draw.rect(screen, (r, g, b, alpha), (lifted_rect.x - 5, lifted_rect.y - 5, lifted_rect.width + 10, lifted_rect.height + 10))
            # Square border
            border_color = (220, 220, 220) if hover == key else (180, 180, 180)
            pygame.draw.rect(screen, border_color, (lifted_rect.x - 5, lifted_rect.y - 5, lifted_rect.width + 10, lifted_rect.height + 10), 2)

            # Заменяем секцию с текстом и свечением
            # Text with glow
            text = font.render(key.upper(), True, (30, 30, 30))  # Ярко-белый текст
            screen.blit(text,
                        (lifted_rect.centerx - text.get_width() // 2, lifted_rect.centery - text.get_height() // 2))

            # Unique effects
            if key == trans['chaos']:
                if current_time % 333 < 100:
                    for _ in range(2):
                        if random.choice([True, False]):
                            y_pos = lifted_rect.top + random.randint(10, lifted_rect.height - 10)
                            pygame.draw.line(screen, (255, 0, 0, 150), (lifted_rect.left + 10, y_pos), (lifted_rect.right - 10, y_pos), 3)
                        else:
                            x_pos = lifted_rect.left + random.randint(10, lifted_rect.width - 10)
                            pygame.draw.line(screen, (255, 0, 0, 150), (x_pos, lifted_rect.top + 10), (x_pos, lifted_rect.bottom - 10), 3)
            elif key == trans['harmony']:
                if current_time % 20 == 0:
                    particles[trans['harmony']].append([lifted_rect.centerx + random.randint(-50, 50), lifted_rect.top - 10, random.uniform(-0.5, 0.5), random.uniform(1.5, 3), 40])
                for p in particles[trans['harmony']][:]:
                    p[0] += p[2]
                    p[1] += p[3]
                    p[4] -= 0.4
                    if p[4] <= 0 or p[1] > lifted_rect.bottom + 20:
                        particles[trans['harmony']].remove(p)
                    else:
                        pygame.draw.ellipse(screen, (0, 150, 0, int(p[4] * 6)), (int(p[0]), int(p[1]), 6, 3))
            elif key == trans['merge']:
                # Gradient surface with extra padding for effects
                gradient_button = pygame.Surface((lifted_rect.width + 10, lifted_rect.height + 10), pygame.SRCALPHA)
                for y in range(lifted_rect.height + 10):
                    r = max(0, min(255, int(255 - (100 * y / lifted_rect.height))))
                    g = max(0, min(255, int(120 + (60 * y / lifted_rect.height))))
                    b = max(0, min(255, int(40 + (60 * y / lifted_rect.height))))
                    alpha = 200 if hover == key else 150
                    pygame.draw.line(gradient_button, (r, g, b, alpha), (0, y), (lifted_rect.width + 10, y))
                screen.blit(gradient_button, (lifted_rect.x - 5, lifted_rect.y - 5))

                # Text with glow first
                text = font.render(key.upper(), True, (0, 0, 0))  # Чёрный текст
                screen.blit(text,
                            (lifted_rect.centerx - text.get_width() // 2, lifted_rect.centery - text.get_height() // 2))

                # Particle effects
                if current_time % 50 == 0:
                    particles[trans['merge']].append(
                        [lifted_rect.left + random.choice([10, lifted_rect.width - 10]),
                         lifted_rect.top + random.randint(10, lifted_rect.height - 10),
                         random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 20])
                    particles[trans['merge']].append(
                        [lifted_rect.left + random.randint(10, lifted_rect.width - 10),
                         lifted_rect.top + random.choice([10, lifted_rect.height - 10]),
                         random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), 20])
                for p in particles[trans['merge']][:]:
                    p[0] += p[2]
                    p[1] += p[3]
                    p[4] -= 0.3
                    alpha = int((p[4] / 20) * 150)
                    if p[4] <= 0 or not lifted_rect.collidepoint(p[0], p[1]):
                        particles[trans['merge']].remove(p)
                    else:
                        text_rect = text.get_rect(center=lifted_rect.center)
                        if not text_rect.collidepoint(p[0], p[1]):
                            pygame.draw.circle(screen, (255, 150, 50, alpha), (int(p[0]), int(p[1])), 2)
            elif key == trans['forget']:
                if current_time % 50 == 0:
                    particles[trans['forget']].append([lifted_rect.centerx + random.randint(-30, 30), lifted_rect.centery + random.randint(-30, 30), 0, 0, 20])
                for p in particles[trans['forget']][:]:
                    p[4] -= 0.3
                    alpha = int((p[4] / 20) * 150)
                    if p[4] <= 0:
                        particles[trans['forget']].remove(p)
                    else:
                        pygame.draw.circle(screen, (100, 30, 150, alpha), (int(p[0]), int(p[1])), 2)
            elif key == trans['escape']:
                pulse = int(10 * math.sin(current_time * 0.003))
                pygame.draw.rect(screen, (190, 170, 100, 80), lifted_rect.inflate(pulse, pulse), 3)

        # Create a mask to exclude button areas with extra padding
        mask_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for rect in portals.values():
            lift_offset = -10 if hover == list(portals.keys())[list(portals.values()).index(rect)] else 0
            lifted_rect = rect.move(0, lift_offset)
            # Расширяем область маски для теней и эффектов
            mask_rect = pygame.Rect(lifted_rect.x - 10, lifted_rect.y - 10, lifted_rect.width + 20, lifted_rect.height + 20)
            pygame.draw.rect(mask_surface, (0, 0, 0, 255), mask_rect)

        # Draw semi-transparent gradient background with mask
        gradient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(HEIGHT):
            r = int(50 + (70 * y / HEIGHT))  # Увеличена базовая яркость
            g = int(30 + (40 * y / HEIGHT))
            b = int(40 + (90 * y / HEIGHT))
            pygame.draw.line(gradient, (r, g, b, 100), (0, y), (WIDTH, y))
        gradient.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(gradient, (0, 0))

        # Prompt text
        prompt_alpha = int(200 + 55 * math.sin(current_time * 0.007))
        prompt = big_font.render(trans['prompt'], True, (prompt_alpha, prompt_alpha, prompt_alpha))
        prompt_glow = pygame.Surface((prompt.get_width() + 20, prompt.get_height() + 20), pygame.SRCALPHA)
        pygame.draw.rect(prompt_glow, (prompt_alpha // 2, prompt_alpha // 2, prompt_alpha // 2, 100), prompt_glow.get_rect(), border_radius=10)
        screen.blit(prompt_glow, (WIDTH // 2 - prompt.get_width() // 2 - 10, HEIGHT // 10 - 10))
        screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 10))

        # Custom cursor with gradient
        cursor_size = 10
        cursor_surface = pygame.Surface((cursor_size * 2, cursor_size * 2), pygame.SRCALPHA)
        for r in range(cursor_size * 2):
            alpha = int(255 * (1 - (r / (cursor_size * 2 - 1))))
            pygame.draw.circle(cursor_surface, (255, 255, 255, alpha), (cursor_size, cursor_size), r, 1)
        screen.blit(cursor_surface, (mx - cursor_size, my - cursor_size))

        pygame.display.flip()
def run_merge_ending():
    font_big = pygame.font.SysFont("consolas", 42, bold=True)
    font_small = pygame.font.SysFont("consolas", 28, italic=True)

    timer = 0
    fade = 0
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    particles = []  # Для спирали
    comets = []     # Для падающих комет
    stars = generate_stars(50)
    cloud_radius = 0
    music_on = True

    # === Загрузка музыки ===
    try:
        if os.path.exists("merge_music.mp3"):
            pygame.mixer.music.load("merge_music.mp3")
            pygame.mixer.music.play(-1)
        else:
            print("Файл 'merge_music.mp3' не найден.")
            music_on = False
    except Exception as e:
        print(f"Ошибка при загрузке музыки: {e}")
        music_on = False

    # === Класс: Фиолетовая комета со следом ===
    class Comet:
        def __init__(self):
            self.x = random.randint(0, WIDTH)
            self.y = random.randint(-100, -10)
            self.vx = random.uniform(-1.5, 1.5)  # Небольшой угол
            self.vy = random.uniform(3.0, 6.0)
            self.size = random.randint(2, 4)
            self.trail = []
            self.active = True
            self.hue = 0.7 + random.uniform(-0.1, 0.1)  # Фиолетовый оттенок

        def update(self):
            if not self.active:
                return
            self.x += self.vx
            self.y += self.vy
            self.trail.append((self.x, self.y))
            if len(self.trail) > 15:
                self.trail.pop(0)
            if self.y > HEIGHT + 50:
                self.active = False

        def draw(self, surface):
            if not self.active:
                return

            # Основная голова кометы (светящаяся)
            pygame.draw.circle(surface, (200, 150, 255), (int(self.x), int(self.y)), self.size + 1)

            # След из частиц
            for i, (x, y) in enumerate(self.trail):
                alpha = int(200 * (i / len(self.trail)))
                size = self.size - (i * 0.2)
                if size > 0:
                    glow = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
                    r = int(150 + 50 * math.sin(i * 0.5))
                    g = int(100)
                    b = int(255)
                    pygame.draw.circle(glow, (r, g, b, alpha // 2), (size * 3, size * 3), size * 3)
                    surface.blit(glow, (x - size * 3, y - size * 3))
                    pygame.draw.circle(surface, (200, 150, 255, alpha), (int(x), int(y)), size)

    # === Функция: космическая спираль ===
    def draw_cosmic_spiral(surface, t):
        center_x, center_y = WIDTH // 2, HEIGHT // 2
        for i in range(30):
            angle = t * 0.015 + i * 0.25
            radius = 50 + i * 10 + int(20 * math.sin(t * 0.01 + i))
            x = center_x + int(radius * math.cos(angle))
            y = center_y + int(radius * math.sin(angle))
            r = max(0, min(255, 100 + int(100 * math.sin(t * 0.01 + i))))
            g = max(0, min(255, 50 + int(50 * math.cos(t * 0.01 + i))))
            b = max(0, min(255, 200 + int(55 * math.cos(t * 0.01 + i))))
            a = 150
            color = (r, g, b, a)
            pygame.draw.circle(surface, color, (x, y), 2)

    # === Функция: облако звёзд ===
    def draw_star_cloud(surface, t):
        nonlocal cloud_radius
        cloud_radius = min(300, cloud_radius + 0.5)
        for i in range(20):
            angle = t * 0.01 + i * 0.3
            x = WIDTH // 2 + int(cloud_radius * math.cos(angle))
            y = HEIGHT // 2 + int(cloud_radius * math.sin(angle))
            brightness = max(0, min(255, int(100 + 155 * math.sin(t * 0.02 + i))))
            pygame.draw.circle(surface, (brightness, brightness, brightness, 100), (x, y), 3)

    # === Переводы ===
    global language
    trans_core = {
        'ru': {
            'line1': "Ты слился с вечностью…",
            'line2': "Твой свет теперь в звёздах.",
            'line3': "Всё, что было, стало космосом.",
            'line4': "Твоя душа танцует в бесконечности."
        },
        'en': {
            'line1': "You merged with eternity…",
            'line2': "Your light is now in the stars.",
            'line3': "Everything that was became the cosmos.",
            'line4': "Your soul dances in infinity."
        }
    }

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # === Фон: медленный космический градиент ===
        bg = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            r = int(0 + (20 * math.sin(timer * 0.001) + 20 * y / HEIGHT))
            g = int(0 + (30 * math.cos(timer * 0.001) + 30 * y / HEIGHT))
            b = int(10 + (100 * y / HEIGHT))
            pygame.draw.line(bg, (r, g, b), (0, y), (WIDTH, y))
        screen.blit(bg, (0, 0))

        # === Звёзды ===
        update_and_draw_stars(stars)

        timer += 1

        # === Спираль частиц в центре ===
        if random.random() < 0.03:
            particles.append([WIDTH // 2, HEIGHT // 2, random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5), 80])
        for p in particles[:]:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 0.5
            alpha = int((p[4] / 80) * 200)
            if p[4] <= 0 or not pygame.Rect(0, 0, WIDTH, HEIGHT).collidepoint(p[0], p[1]):
                particles.remove(p)
            else:
                pygame.draw.circle(screen, (100, 150, 255, alpha), (int(p[0]), int(p[1])), 1)

        # === Спавн фиолетовых комет ===
        if random.random() < 0.02 and timer < 400:
            comets.append(Comet())
        for comet in comets[:]:
            comet.update()
            comet.draw(screen)

        # === Эффекты в центре ===
        draw_cosmic_spiral(screen, timer)
        draw_star_cloud(screen, timer)

        # === Текстовые сообщения ===
        if timer > 150:
            txt1 = font_big.render(trans_core[language]['line1'], True, (200, 220, 255, int(255 * min(1, (timer - 150) / 30))))
            screen.blit(txt1, (WIDTH // 2 - txt1.get_width() // 2, HEIGHT // 2 - 50))

        if timer > 250:
            txt2 = font_big.render(trans_core[language]['line2'], True, (180, 200, 240, int(255 * min(1, (timer - 250) / 30))))
            screen.blit(txt2, (WIDTH // 2 - txt2.get_width() // 2, HEIGHT // 2 - 10))

        if timer > 350:
            txt3 = font_big.render(trans_core[language]['line3'], True, (160, 180, 220, int(255 * min(1, (timer - 350) / 30))))
            screen.blit(txt3, (WIDTH // 2 - txt3.get_width() // 2, HEIGHT // 2 + 30))

        if timer > 450:
            txt4 = font_big.render(trans_core[language]['line4'], True, (140, 160, 200, int(255 * min(1, (timer - 450) / 30))))
            screen.blit(txt4, (WIDTH // 2 - txt4.get_width() // 2, HEIGHT // 2 + 70))

        # === Затемнение в конце ===
        if timer > 500:
            fade = min(255, fade + 1)
            fade_surface.fill((0, 0, 0, fade))
            screen.blit(fade_surface, (0, 0))

        if fade >= 255:
            pygame.time.delay(1000)
            show_credits()
            pygame.quit()
            sys.exit()

        pygame.display.flip()
        clock.tick(60)
def run_escape_ending():
    font = pygame.font.SysFont("consolas", 36, bold=True)
    white_overlay = pygame.Surface((WIDTH, HEIGHT))
    white_overlay.fill((255, 255, 255))

    portal_radius = 10
    portal_growth = 2
    max_portal_radius = int((WIDTH ** 2 + HEIGHT ** 2) ** 0.5)

    escape_text_alpha = 0
    text_timer_started = False
    text_timer = 0
    reached_exit = False
    final_scene_timer = 0

    sun_radius_base = 60
    sun_radius_phase = 0
    sky_color = (135, 206, 235)
    grass_color = (100, 200, 120)

    clouds = [{'x': random.randint(0, WIDTH), 'y': random.randint(50, 150)} for _ in range(5)]
    birds = []
    flowers = [{'x': random.randint(50, WIDTH - 50),
                'y': random.randint(HEIGHT // 2 + 40, HEIGHT - 30),
                'color': random.choice([(255, 105, 180), (255, 255, 0), (255, 0, 0), (160, 32, 240)])}
               for _ in range(50)]
    butterflies = []  # Добавим бабочек для красоты

    bird_timer = pygame.time.get_ticks()
    butterfly_timer = pygame.time.get_ticks()
    music_started = False

    try:
        pygame.mixer.music.load("background_music.mp3")
    except:
        print("Музыка не найдена.")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if not reached_exit:
            screen.fill((10, 10, 20))
            portal_radius = min(max_portal_radius, portal_radius + portal_growth)
            pygame.draw.circle(screen, (255, 255, 255), (WIDTH // 2, HEIGHT // 2), portal_radius)
            pygame.draw.circle(screen, (200, 200, 255, 50), (WIDTH // 2, HEIGHT // 2), portal_radius - 10, 2)

            if random.random() < 0.05:
                flicker = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                flicker.fill((255, 255, 255, random.randint(20, 60)))
                screen.blit(flicker, (0, 0))

            if portal_radius > 100:
                white_overlay.set_alpha(min(255, int((portal_radius / max_portal_radius) * 255)))
                screen.blit(white_overlay, (0, 0))

            if portal_radius >= max_portal_radius * 0.6 and not text_timer_started:
                text_timer = pygame.time.get_ticks()
                text_timer_started = True

            if text_timer_started:
                elapsed = pygame.time.get_ticks() - text_timer
                if elapsed > 500:
                    escape_text_alpha = min(255, escape_text_alpha + 3)
                    trans_escapee = {
                        'ru': "…ты вышел в свет.",
                        'en': "...you emerged into the light."
                    }
                    text_surface = font.render(trans_escapee[language], True, (0, 0, 0))
                    text_surface.set_alpha(escape_text_alpha)
                    screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, HEIGHT // 2 - text_surface.get_height() // 2))

            if portal_radius >= max_portal_radius and escape_text_alpha >= 255:
                pygame.time.delay(1000)
                reached_exit = True
                final_scene_timer = pygame.time.get_ticks()
                if not music_started:
                    try:
                        pygame.mixer.music.play(-1)
                        music_started = True
                    except:
                        pass

        else:
            screen.fill(sky_color)
            draw_gradient_background(screen, sky_color)

            pygame.draw.rect(screen, grass_color, (0, HEIGHT // 2, WIDTH, HEIGHT // 2))

            for cloud in clouds:
                pygame.draw.ellipse(screen, (255, 255, 255), (cloud['x'], cloud['y'], 120, 60))
                cloud['x'] += 0.5
                if cloud['x'] > WIDTH:
                    cloud['x'] = -140
                    cloud['y'] = random.randint(50, 150)

            sun_radius_phase += 0.03
            sun_radius = sun_radius_base + math.sin(sun_radius_phase) * 8
            pygame.draw.circle(screen, (255, 255, 180), (WIDTH // 2, HEIGHT // 3), int(sun_radius))
            pygame.draw.circle(screen, (255, 200, 150, 100), (WIDTH // 2, HEIGHT // 3), int(sun_radius * 0.8), 1)

            now = pygame.time.get_ticks()
            if now - bird_timer > random.randint(1500, 4000):
                bird_y = random.randint(80, 200)
                birds.append({'x': WIDTH + 50, 'y': bird_y})
                bird_timer = now

            if now - butterfly_timer > random.randint(2000, 5000):
                butterfly_y = random.randint(HEIGHT // 2 + 50, HEIGHT - 50)
                butterflies.append({'x': WIDTH + 30, 'y': butterfly_y})
                butterfly_timer = now

            # --- Птицы (в виде '<') ---
            for bird in birds[:]:
                bird['x'] -= 2
                # Рисуем птицу как '<'
                x = bird['x']
                y = bird['y']
                size = 8  # Можно менять для разного размера
                pygame.draw.line(screen, (0, 0, 0), (x, y), (x - size, y - size // 1.5), 2)
                pygame.draw.line(screen, (0, 0, 0), (x, y), (x - size, y + size // 1.5), 2)
                if bird['x'] < -20:
                    birds.remove(bird)

            # --- Бабочки (в виде '< >') ---
            for butterfly in butterflies[:]:
                butterfly['x'] -= 1.5
                x = butterfly['x']
                y = butterfly['y']
                color = random.choice([(255, 105, 180), (255, 0, 0), (255, 180, 0)])  # Яркие цвета
                size = random.randint(6, 10)  # Разный размер

                # Левое крыло '<'
                pygame.draw.line(screen, color, (x, y), (x - size, y - size), 2)
                pygame.draw.line(screen, color, (x, y), (x - size, y + size), 2)
                # Правое крыло '>'
                pygame.draw.line(screen, color, (x, y), (x + size, y - size), 2)
                pygame.draw.line(screen, color, (x, y), (x + size, y + size), 2)

                # Тело бабочки
                pygame.draw.line(screen, (50, 50, 50), (x, y - 2), (x, y + 2), 1)

                if butterfly['x'] < -30:
                    butterflies.remove(butterfly)

            for flower in flowers:
                pygame.draw.circle(screen, flower['color'], (flower['x'], flower['y']), 5)
                pygame.draw.line(screen, (0, 100, 0), (flower['x'], flower['y']), (flower['x'], flower['y'] + 10), 2)

            final_elapsed = pygame.time.get_ticks() - final_scene_timer
            if final_elapsed > 1000:
                trans_escape = {
                    'ru': {
                        'final': "Ты свободен среди цветов."
                    },
                    'en': {
                        'final': "You are free among the flowers."
                    }
                }
                text = font.render(trans_escape[language]['final'], True, (0, 0, 0))
                text_shadow = font.render(trans_escape[language]['final'], True, (50, 50, 50))
                screen.blit(text_shadow, (WIDTH // 2 - text.get_width() // 2 + 2, HEIGHT // 2 - 80 + 2))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 80))

            if final_elapsed > 20000:
                show_credits()
                pygame.quit()
                sys.exit()

        pygame.display.flip()
        clock.tick(60)
def run_forget_ending():
    font = pygame.font.SysFont("consolas", 40, bold=True)
    small_font = pygame.font.SysFont("consolas", 28, italic=True)
    timer = 0
    particles = []
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))
    fading_alpha = 0
    phrase_shown = False
    phrase_alpha = 0
    black_hole_radius = 0  # Начальный радиус точки
    target_radius = 50  # Не очень большая точка
    sound_volume = 1.0  # Начальная громкость звука
    sound_playing = False
    trans_forget = {
        'ru': "…тебя больше нет.",
        'en': "...you are no more."
    }
    final_text = trans_forget[language]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Глубокий градиентный фон с пульсацией
        pulse_intensity = int(15 * math.sin(timer * 0.02))
        gradient = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            r = max(0, min(255, int(5 + (10 * y / HEIGHT) + pulse_intensity)))
            g = max(0, min(255, int(5 + (10 * y / HEIGHT) + pulse_intensity)))
            b = max(0, min(255, int(10 + (20 * y / HEIGHT) + pulse_intensity)))
            pygame.draw.line(gradient, (r, g, b), (0, y), (WIDTH, y))
        screen.blit(gradient, (0, 0))

        # Генерация частиц с притяжением к центру
        if len(particles) < 600 and timer < 200:  # Ограничиваем генерацию
            for _ in range(8):
                angle = random.uniform(0, 2 * math.pi)
                distance = random.randint(100, 300)
                x = WIDTH // 2 + int(distance * math.cos(angle))
                y = HEIGHT // 2 + int(distance * math.sin(angle))
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
                size = random.uniform(2, 6)
                life = random.randint(100, 200)
                particles.append([x, y, dx, dy, size, life])

        # Обновление частиц с гравитацией к центру
        for p in particles[:]:
            center_x, center_y = WIDTH // 2, HEIGHT // 2
            dx_to_center = center_x - p[0]
            dy_to_center = center_y - p[1]
            distance = max(1, math.hypot(dx_to_center, dy_to_center))
            accel = 0.15 * (1 - (distance / 300))  # Сильное притяжение
            p[2] += (dx_to_center / distance) * accel
            p[3] += (dy_to_center / distance) * accel
            p[0] += p[2]
            p[1] += p[3]
            p[5] -= 1
            p[4] = max(1, p[4] * 0.97)  # Медленное уменьшение
            alpha = max(0, int((p[5] / 200) * 255))
            color = (100, 100, 100, alpha)
            pygame.draw.circle(screen, color, (int(p[0]), int(p[1])), int(p[4]))

        particles = [p for p in particles if p[5] > 0 and distance > black_hole_radius]

        # Точка слияния и растворение
        if timer < 200:
            black_hole_radius = min(target_radius, black_hole_radius + 0.5)  # Достигаем 50 пикселей
        else:
            black_hole_radius = max(0, black_hole_radius - 0.5)  # Растворение
        hole_pulse = int(5 * math.sin(timer * 0.03))
        pygame.draw.circle(screen, (0, 0, 0), (WIDTH // 2, HEIGHT // 2), int(black_hole_radius + hole_pulse))

        # Затемнение
        if timer > 200:
            fading_alpha = min(255, fading_alpha + 1)
            fade_surface.set_alpha(fading_alpha)
            screen.blit(fade_surface, (0, 0))

        # Текст с эффектом искажения
        if fading_alpha > 180 and not phrase_shown:
            phrase_shown = True
        if phrase_shown:
            phrase_alpha = min(255, phrase_alpha + 2)
            text = font.render(final_text, True, (200, 200, 200, int(phrase_alpha * 0.8)))
            text_shadow = small_font.render(final_text, True, (0, 0, 0, int(phrase_alpha * 0.4)))
            offset_x = int(3 * math.sin(timer * 0.1))
            screen.blit(text_shadow, (WIDTH // 2 - text.get_width() // 2 + offset_x + 3, HEIGHT // 2 - text.get_height() // 2 + 3))
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2 + offset_x, HEIGHT // 2 - text.get_height() // 2))

        # Финал с затуханием звука
        # Финал с затуханием звука
        if phrase_alpha >= 255 and black_hole_radius <= 0:
            if sound_volume > 0:
                sound_volume = max(0, sound_volume - 0.05)  # Плавное затухание
                if os.path.exists("suckk.mp3") and not sound_playing:
                    suck_sound = pygame.mixer.Sound("suckk.mp3")
                    suck_sound.set_volume(sound_volume)
                    suck_sound.play()
                    sound_playing = True
                elif sound_playing:
                    suck_sound.set_volume(sound_volume)
            else:
                # Вместо выхода, показываем титры
                pygame.time.delay(1000)  # Небольшая пауза после затухания
                show_credits()  # Показываем титры
                pygame.quit()  # Выходим после титров
                sys.exit()
        timer += 1
        if os.path.exists("suckk.mp3") and timer % 30 == 0 and timer < 200 and not sound_playing:
            suck_sound = pygame.mixer.Sound("suckk.mp3")
            suck_sound.set_volume(1.0)
            suck_sound.play()
        pygame.display.flip()
        clock.tick(60)
def final_flash():
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    for i in range(0, 256, 5):
        fade_surface.set_alpha(i)
        fade_surface.fill((255, 255, 255))
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)

    pygame.quit()
    sys.exit()
def draw_gradient_background(surface, base_color):
    gradient = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(base_color[0] + (255 - base_color[0]) * ratio * 0.7)
        g = int(base_color[1] + (255 - base_color[1]) * ratio * 0.7)
        b = int(base_color[2] + (255 - base_color[2]) * ratio * 0.7)
        pygame.draw.line(gradient, (r, g, b), (0, y), (WIDTH, y))
    surface.blit(gradient, (0, 0))
def generate_stars(count):
    return [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(count)]
def update_and_draw_stars(stars):
    for x, y in stars:
        size = random.randint(1, 4)
        alpha = random.randint(200, 255)
        pygame.draw.circle(screen, (200, 200, 255, alpha), (x, y), size)
def generate_clouds(count):
    return [{'x': random.randint(0, WIDTH), 'y': random.randint(0, HEIGHT // 2)} for _ in range(count)]
def show_credits():
    # === Параметры шрифтов и цветов ===
    font_big = pygame.font.SysFont("consolas", 48, bold=True)
    font_medium = pygame.font.SysFont("consolas", 36, bold=True)
    font_small = pygame.font.SysFont("consolas", 28)

    WHITE = (200, 200, 255)
    BLUE = (100, 150, 255)
    PINK = (255, 150, 200)

    # === Переводы для титров ===
    global language
    trans_credits = {
        'ru': {
            'creator': 'Создатель',
            'name': 'Роман',
            'subscribe': 'Подпишитесь на канал',
            'channel': '@shymn - Шумные будни',
            'music': 'Музыка',
            'artist': 'C418',
            'thanks': 'Спасибо за игру!'
        },
        'en': {
            'creator': 'Creator',
            'name': 'Roman',
            'subscribe': 'Subscribe to channel',
            'channel': '@shymn - Шумные будни',
            'music': 'Music',
            'artist': 'C418',
            'thanks': 'Thank you for playing!'
        }
    }

    # === Данные титров (структурированные) ===
    credits_data = [
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': trans_credits[language]['creator'], 'type': 'title'},
        {'text': trans_credits[language]['name'], 'type': 'name'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': trans_credits[language]['subscribe'], 'type': 'title'},
        {'text': trans_credits[language]['channel'], 'type': 'channel'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': trans_credits[language]['music'], 'type': 'title'},
        {'text': trans_credits[language]['artist'], 'type': 'artist'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': trans_credits[language]['thanks'], 'type': 'thanks'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'},
        {'text': '', 'type': 'empty'}
    ]

    # === Преобразуем в поверхности с цветами ===
    credit_surfaces = []
    for item in credits_data:
        line = item['text']
        if item['type'] == 'title':
            surf = font_big.render(line, True, BLUE)
        elif item['type'] in ['name', 'channel', 'artist']:
            surf = font_medium.render(line, True, WHITE)
        elif item['type'] == 'thanks':
            surf = font_big.render(line, True, PINK)
        else:  # empty
            surf = font_small.render(line, True, WHITE)
        credit_surfaces.append(surf)

    # === Рассчитываем общую высоту и начальную позицию ===
    total_height = sum(surf.get_height() for surf in credit_surfaces)
    y_position = HEIGHT + 50  # Начинаем за нижним краем экрана

    start_time = time.time()
    duration = 20.0  # 15 секунд анимации

    # === Основной цикл титров ===
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False  # Выход по любому нажатию

        screen.fill((10, 10, 20))

        # Обновляем позицию (медленное движение вверх)
        elapsed = time.time() - start_time
        y_position = HEIGHT + 50 - (elapsed * 50)

        # Отрисовываем строки
        current_y = y_position
        for surf in credit_surfaces:
            x = (WIDTH - surf.get_width()) // 2
            screen.blit(surf, (x, current_y))
            current_y += surf.get_height() + 10

        # Завершение: если титры ушли вверх или время истекло
        if current_y < -100 or elapsed > duration:
            running = False

        pygame.display.flip()
        clock.tick(60)

    # === После титров — возвращение в меню и запуск музыки ===
    show_intro_screen()

    # Настройка и запуск музыки
    music_loaded = False
    music_volume = 0.0
    fade_in_duration = 3000
    fade_in_start_time = pygame.time.get_ticks()

    try:
        if os.path.exists("Relacs.mp3"):
            pygame.mixer.music.load("Relacs.mp3")
            pygame.mixer.music.set_volume(music_volume)
            pygame.mixer.music.play(-1)
            music_loaded = True
            print("Музыка загружена, начинается fade-in...")
    except Exception as e:
        print(f"Ошибка при загрузке звука: {e}")
def update_and_draw_clouds(clouds):
    for cloud in clouds:
        pygame.draw.ellipse(screen, (200, 200, 200), (cloud['x'], cloud['y'], 100, 50))
        cloud['x'] += 0.2
        if cloud['x'] > WIDTH:
            cloud['x'] = -100
            cloud['y'] = random.randint(0, HEIGHT // 2)
class Particless:
    def __init__(self, x, y, dx, dy, life, color):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.life = life
        # Ensure color is a 3-element tuple
        if not isinstance(color, (tuple, list)) or len(color) != 3 or not all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            raise ValueError(f"Invalid color: {color} (must be a 3-element tuple of integers in [0, 255])")
        self.color = tuple(color)  # Convert to tuple to ensure immutability

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int((self.life / 100) * 255)))  # Clamp alpha to [0, 255]
        # Validate and unpack color
        if not isinstance(self.color, (tuple, list)) or len(self.color) != 3 or not all(isinstance(c, int) and 0 <= c <= 255 for c in self.color):
            raise ValueError(f"Invalid self.color in draw: {self.color}")
        r, g, b = self.color
        color = (r, g, b, alpha)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), 4)
class Particlesss:
    def __init__(self, x, y, dx, dy, life, start_color, end_color, size, particle_type):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.initial_life = life  # Сохраняем начальное значение жизни
        self.life = life
        # Validate start_color
        if not isinstance(start_color, (tuple, list)) or len(start_color) != 3 or not all(isinstance(c, int) and 0 <= c <= 255 for c in start_color):
            raise ValueError(f"Invalid start_color: {start_color}")
        self.start_color = tuple(start_color)
        # Validate end_color
        if not isinstance(end_color, (tuple, list)) or len(end_color) != 3 or not all(isinstance(c, int) and 0 <= c <= 255 for c in end_color):
            raise ValueError(f"Invalid end_color: {end_color}")
        self.end_color = tuple(end_color)
        self.size = max(1, min(10, size))  # Ограничение размера
        self.particle_type = particle_type  # "leaf", "glow" и т.д.

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        # Нормализованный прогресс от 1 (начало) до 0 (конец)
        progress = max(0, min(1, 1 - (self.life / self.initial_life)))
        # Интерполяция цвета с ограничением диапазона
        r = max(0, min(255, int(self.start_color[0] + (self.end_color[0] - self.start_color[0]) * progress)))
        g = max(0, min(255, int(self.start_color[1] + (self.end_color[1] - self.start_color[1]) * progress)))
        b = max(0, min(255, int(self.start_color[2] + (self.end_color[2] - self.start_color[2]) * progress)))
        alpha = max(0, min(255, int(progress * 255)))  # Альфа уменьшается от 255 до 0
        color = (r, g, b, alpha)
        # Размер уменьшается с жизнью
        current_size = max(1, self.size * (self.life / self.initial_life))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(current_size))
def generate_cloudss(count):
    clouds = []
    for _ in range(count):
        width = random.randint(120, 200)
        height = random.randint(60, 100)
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT // 4)  # Ограничиваем облака верхней частью
        speed = random.uniform(0.1, 0.4)
        clouds.append({
            'rect': pygame.Rect(x, y, width, height),
            'speed': speed,
            'alpha': random.randint(150, 200)  # Прозрачность для вариаций
        })
    return clouds
def run_harmony_ending():
    # Инициализация шрифтов и переменных
    try:
        font = pygame.font.SysFont("consolas", 40, bold=True)
        title_font = pygame.font.SysFont("consolas", 70, bold=True)
    except Exception:
        font = pygame.font.Font(None, 40)
        title_font = pygame.font.Font(None, 70)

    running = True
    fade_alpha = 0
    phase = 1  # 1 - Успокоение, 2 - Баланс, 3 - Единство, 4 - Бесконечность
    phase_timer = pygame.time.get_ticks()
    rotation_angle = 0
    sphere_radius = 50
    sphere_count = 5

    music_loaded = False
    chime_sound = None  # Объект для воспроизведения
    try:
        if os.path.exists("harmony_music.mp3"):
            pygame.mixer.music.load("harmony_music.mp3")
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            music_loaded = True
    except Exception as e:
        print(f"Критическая ошибка при загрузке звука: {e}")
        # Не прерываем игру, если звук не загрузился
        chime_sound = None

    # === Переводы для Harmony Ending ===
    global language
    trans_harmony = {
        'ru': {
            'messages': [
                "Тишина обнимает твою душу...",
                "Сферы баланса начинают сиять...",
                "Ты растворяешься в единстве...",
                "Бесконечность зовёт тебя..."
            ],
            'final': "Ты воссоединился с гармонией..."
        },
        'en': {
            'messages': [
                "Silence embraces your soul...",
                "Spheres of balance begin to glow...",
                "You dissolve into unity...",
                "Infinity calls to you..."
            ],
            'final': "You have reunited with harmony..."
        }
    }

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Плавный градиентный фон без линий
        gradient = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):  # Уменьшаем шаг до 1 для сглаживания
            r = max(0, min(255, int(10 + (200 * y / HEIGHT))))
            g = max(0, min(255, int(50 + (220 * y / HEIGHT))))
            b = max(0, min(255, int(100 + (245 * y / HEIGHT))))
            # Сглаживание с помощью смешивания соседних цветов
            if y > 0:
                prev_r, prev_g, prev_b = gradient.get_at((0, y-1))[:3]
                r = (r + prev_r) // 2
                g = (g + prev_g) // 2
                b = (b + prev_b) // 2
            pygame.draw.line(gradient, (r, g, b), (0, y), (WIDTH, y))
        screen.blit(gradient, (0, 0))

        # Анимация фаз
        current_time = pygame.time.get_ticks()
        if current_time - phase_timer > 5000 and phase < 4:  # 5 секунд на фазу
            phase += 1
            phase_timer = current_time
            if chime_sound:
                chime_sound.play()

        # Фаза 1: Успокоение - мягкий пульсирующий свет
        if phase == 1:
            pulse = int(50 * math.sin(current_time * 0.002))
            center_light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(center_light, (200, 220, 255, 100 + pulse), (WIDTH // 2, HEIGHT // 2), 150)
            screen.blit(center_light, (0, 0))

        # Фаза 2: Баланс - вращающиеся сферы
        elif phase == 2:
            rotation_angle += 1
            for i in range(sphere_count):
                angle = math.radians(rotation_angle + (360 / sphere_count) * i)
                x = WIDTH // 2 + int(200 * math.cos(angle))
                y = HEIGHT // 2 + int(200 * math.sin(angle))
                radius = max(10, sphere_radius + int(15 * math.sin(current_time * 0.003 + i)))  # Минимальный радиус 10
                glow = pygame.Surface((max(20, radius * 2 + 20), max(20, radius * 2 + 20)), pygame.SRCALPHA)
                pygame.draw.circle(glow, (100, 150, 255, 150), (radius + 10, radius + 10), radius + 10)
                pygame.draw.circle(screen, (150, 200, 255), (x, y), radius)
                screen.blit(glow, (x - radius - 10, y - radius - 10))

        # Фаза 3: Единство - слияние в центральный свет
        elif phase == 3:
            sphere_radius = max(0, sphere_radius - 1)
            for i in range(sphere_count):
                angle = math.radians(rotation_angle + (360 / sphere_count) * i)
                x = WIDTH // 2 + int(200 * math.cos(angle) * (sphere_radius / 50))
                y = HEIGHT // 2 + int(200 * math.sin(angle) * (sphere_radius / 50))
                radius = max(10, sphere_radius + int(15 * math.sin(current_time * 0.003 + i)))
                glow = pygame.Surface((max(20, radius * 2 + 20), max(20, radius * 2 + 20)), pygame.SRCALPHA)
                pygame.draw.circle(glow, (100, 150, 255, 150), (radius + 10, radius + 10), radius + 10)
                pygame.draw.circle(screen, (150, 200, 255), (x, y), radius)
                screen.blit(glow, (x - radius - 10, y - radius - 10))
            if sphere_radius == 0:
                phase = 4
                phase_timer = current_time

        # Фаза 4: Бесконечность - растворение
        elif phase == 4:
            fade_alpha = min(255, fade_alpha + 1)
            fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fade_surface.fill((200, 220, 255, fade_alpha))
            screen.blit(fade_surface, (0, 0))
            if fade_alpha >= 255:
                final_text = title_font.render(trans_harmony[language]['final'], True, (255, 255, 255))
                screen.blit(final_text, (WIDTH // 2 - final_text.get_width() // 2, HEIGHT // 2))
                pygame.display.flip()
                pygame.time.delay(5000)  # Небольшая пауза на финальном тексте
                show_credits()  # Показываем титры
                running = False

        # Текстовая анимация
        if phase <= 4:
            text_alpha = min(255, max(0, (current_time - phase_timer) // 5))
            if text_alpha > 0:
                text = font.render(trans_harmony[language]['messages'][phase - 1], True, (150, 200, 255, text_alpha))
                text_glow = pygame.Surface((text.get_width() + 10, text.get_height() + 10), pygame.SRCALPHA)
                pygame.draw.rect(text_glow, (100, 150, 255, text_alpha // 3), text_glow.get_rect(), border_radius=10)
                screen.blit(text_glow, (WIDTH // 2 - text.get_width() // 2 - 5, HEIGHT * 0.6 - 5))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT * 0.6))

        pygame.display.flip()
        clock.tick(60)

    # Очистка ресурсов
    if music_loaded:
        pygame.mixer.music.stop()
    pygame.quit()
    sys.exit()
def create_explosion(x, y, count=20):
    particles = []
    for _ in range(count):
        dx = random.uniform(-2, 2)
        dy = random.uniform(-2, 2)
        life = random.randint(50, 100)
        color = (255, random.randint(100, 200), 50)
        particles.append(Particless(x, y, dx, dy, life, color))
    return particles
def run_explosion_scene():
    running = True
    particles = []
    explosion_timer = pygame.time.get_ticks()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((0, 0, 0))

        if pygame.time.get_ticks() - explosion_timer > 500:
            particles.extend(create_explosion(WIDTH // 2, HEIGHT // 2))
            explosion_timer = pygame.time.get_ticks()

        particles = [p for p in particles if p.update()]
        for p in particles:
            p.draw(screen)

        if not particles:
            run_void_reveal()
            return

        pygame.display.flip()
        clock.tick(60)
def run_transition_scene():
    running = True
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    alpha = 0
    stars = generate_stars(50)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((10, 10, 20))
        update_and_draw_stars(stars)

        alpha = min(255, alpha + 5)
        fade_surface.fill((0, 0, 0, alpha))
        screen.blit(fade_surface, (0, 0))

        if alpha >= 255:
            run_memory_echo_mode()
            return

        pygame.display.flip()
        clock.tick(60)
def run_chaos_ending():
    font = pygame.font.SysFont("consolas", 36, bold=True)
    running = True
    glitch_timer = 0
    particles = []
    fade_alpha = 0
    phase = 1  # Фазы: 1 - пробуждение, 2 - раскол, 3 - безумие, 4 - разрушение, 5 - растворение
    phase_timer = pygame.time.get_ticks()
    pulse_radius = 0
    distortion_surface = None
    flash_timer = 0
    line_timer = 0

    # === Переводы для Chaos Ending ===
    global language
    trans_chaos = {
        'ru': [
            "Хаос пробуждается...",
            "Реальность раскалывается!",
            "Безумие охватывает...",
            "Всё рушится в пропасть!",
            "Ты растворяешься в пустоте...",
            "Бесконечность поглощает навсегда..."
        ],
        'en': [
            "Chaos awakens...",
            "Reality is cracking!",
            "Madness takes over...",
            "Everything collapses into the abyss!",
            "You dissolve into the void...",
            "Infinity consumes you forever..."
        ]
    }

    # Опциональный звуковой эффект (если файл существует)
    chaos_sound = pygame.mixer.Sound("haos.mp3") if os.path.exists("haos.mp3") else None
    if chaos_sound:
        chaos_sound.play(-1)  # Циклическое воспроизведение

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Пульсирующий и искажённый фон
        pulse_radius = (pulse_radius + 3) % 200
        bg_surface = pygame.Surface((WIDTH, HEIGHT))
        bg_r = max(0, 50 - pulse_radius // 4 + random.randint(-10, 10))
        bg_surface.fill((bg_r, 0, 0))  # Пульсирующий тёмно-красный с вариациями
        if distortion_surface:
            screen.blit(distortion_surface, (random.randint(-10, 10), random.randint(-10, 10)))
        else:
            screen.blit(bg_surface, (0, 0))

        current_time = pygame.time.get_ticks()

        # Переход между фазами
        if current_time - phase_timer > 2500 and phase < 6:  # 2.5 секунды на фазу
            phase += 1
            phase_timer = current_time
            if phase == 2:
                distortion_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            elif phase == 3:
                fade_alpha = 0
            elif phase == 4:
                flash_timer = current_time

        # Генерация частиц
        if random.random() < 0.4 * phase:
            particles.extend(create_explosion(random.randint(0, WIDTH), random.randint(0, HEIGHT), 20 * phase))

        # Глюки и искажения
        if glitch_timer <= 0 and phase < 5:
            glitch_timer = random.randint(15, 40)
            if distortion_surface:
                for _ in range(40 * phase):
                    x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                    w, h = random.randint(10, 100), random.randint(2, 20)
                    color = (255, random.randint(0, 150), 0, 200 - 30 * phase)
                    pygame.draw.rect(distortion_surface, color, (x, y, w, h))
                    # Случайные треугольники
                    if random.random() < 0.3:
                        points = [
                            (x, y),
                            (x + w, y),
                            (x + w // 2, y + h)
                        ]
                        pygame.draw.polygon(distortion_surface, color, points, 2)
        else:
            glitch_timer -= 1

        # Случайные линии
        if line_timer <= 0 and phase > 2:
            line_timer = random.randint(10, 30)
            for _ in range(5 * phase):
                x1, y1 = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                x2, y2 = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                pygame.draw.line(screen, (255, random.randint(0, 100), 0), (x1, y1), (x2, y2), 2 + phase)
        else:
            line_timer -= 1

        # Цветовые вспышки с исправлением
        if flash_timer and current_time - flash_timer < 1000 and phase == 4:
            flash_alpha = max(0, min(255, int(100 * math.sin((current_time - flash_timer) / 100))))  # Clamp to [0, 255]
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, random.randint(0, 100), 0, flash_alpha))
            screen.blit(flash_surface, (0, 0))

        # Обновление и отрисовка частиц
        particles = [p for p in particles if p.update()]
        for p in particles:
            p.draw(screen)

        # Текстовая анимация с предотвращением наложения
        if phase <= 6:
            text_alpha = min(255, max(0, (current_time - phase_timer) // 8)) if phase > 1 else 255
            if text_alpha > 0:  # Отрисовываем только если текст виден
                text = font.render(trans_chaos[language][phase - 1], True,(255, 0, 0, text_alpha))
                text_shadow = font.render(trans_chaos[language][phase - 1], True, (100, 0, 0, text_alpha // 2))
                screen.blit(text_shadow, (WIDTH // 2 - text.get_width() // 2 + 2, HEIGHT // 4 + 2))
                screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 4))

        # Затемнение и финал
        if phase >= 4:
            fade_alpha = min(255, fade_alpha + 1)
            fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fade_surface.fill((0, 0, 0, fade_alpha))
            screen.blit(fade_surface, (0, 0))
            if fade_alpha >= 255 and phase == 5:
                pygame.time.delay(3000)  # Удлинённая задержка
                if chaos_sound:
                    chaos_sound.stop()
                show_credits()
                pygame.quit()
                sys.exit()

        pygame.display.flip()
        clock.tick(60)
def generate_clouds(count):
    clouds = []
    for _ in range(count):
        width = random.randint(100, 200)
        height = random.randint(60, 100)
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT // 2)
        speed = random.uniform(0.1, 0.4)
        clouds.append({
            "rect": pygame.Rect(x, y, width, height),
            "speed": speed
        })
    return clouds
def generate_stars(count):
    return [{
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT),
        "vx": random.uniform(-0.2, 0.2),
        "vy": random.uniform(-0.2, 0.2),
        "radius": random.randint(1, 3),
        "brightness": random.randint(100, 255)
    } for _ in range(count)]
def update_and_draw_stars(stars):
    for star in stars:
        star["x"] += star["vx"]
        star["y"] += star["vy"]

        if star["x"] < 0: star["x"] = WIDTH
        if star["x"] > WIDTH: star["x"] = 0
        if star["y"] < 0: star["y"] = HEIGHT
        if star["y"] > HEIGHT: star["y"] = 0

        pygame.draw.circle(screen, (star["brightness"], star["brightness"], star["brightness"]),
                           (int(star["x"]), int(star["y"])), star["radius"])
def generate_clouds(count):
    return [{
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT // 2),
        "vx": random.uniform(0.1, 0.3),
        "scale": random.uniform(0.6, 1.5)
    } for _ in range(count)]
def update_and_draw_clouds(clouds):
    for cloud in clouds:
        cloud["x"] += cloud["vx"]
        if cloud["x"] > WIDTH:
            cloud["x"] = -200
            cloud["y"] = random.randint(0, HEIGHT // 2)
        cloud_color = (60, 60, 80, 50)
        cloud_surface = pygame.Surface((200, 100), pygame.SRCALPHA)
        pygame.draw.ellipse(cloud_surface, cloud_color, (0, 0, 200, 100))
        scaled = pygame.transform.scale(cloud_surface, (
            int(200 * cloud["scale"]), int(100 * cloud["scale"])) )
        screen.blit(scaled, (cloud["x"], cloud["y"]))
def run_relax_mode():
    total_particles_drawn = 0
    fire_particles = []
    stars_enabled = True
    clouds_enabled = True
    stars = generate_stars(100)
    clouds = generate_clouds(5)
    show_message = True
    message_start = pygame.time.get_ticks()
    show_instructions = True
    current_track = "Relax"  # Start with "Relax" track

    # Инициализация музыки
    pygame.mixer.music.set_volume(0.5)
    if os.path.exists("Relacs.mp3"):
        pygame.mixer.music.load("Relacs.mp3")
        pygame.mixer.music.play(-1)
    elif os.path.exists("Relax2.mp3"):
        pygame.mixer.music.load("Relax2.mp3")
        pygame.mixer.music.play(-1)
    else:
        print("Файлы Relacs.mp3 и Relax2.mp3 не найдены!")

    running = True
    while running:
        now = pygame.time.get_ticks()
        screen.fill((5, 5, 15))
        draw_gradient_background(screen, (5, 5, 15))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    show_intro_screen()
                    return
                elif event.key == pygame.K_TAB:
                    show_instructions = not show_instructions
                elif event.key == pygame.K_s:
                    stars_enabled = not stars_enabled
                elif event.key == pygame.K_c:
                    clouds_enabled = not clouds_enabled
                elif event.key == pygame.K_r:  # Toggle between Relax and Relax2
                    current_track = "Relax2" if current_track == "Relax" else "Relax"
                    if current_track == "Relax" and os.path.exists("Relacs.mp3"):
                        pygame.mixer.music.load("Relacs.mp3")
                        pygame.mixer.music.play(-1)
                    elif current_track == "Relax2" and os.path.exists("Relacs2.mp3"):
                        pygame.mixer.music.load("Relacs2.mp3")
                        pygame.mixer.music.play(-1)
                    else:
                        print(f"Трек {current_track}.mp3 не найден!")

        # Облака
        if clouds_enabled:
            update_and_draw_clouds(clouds)

        # Звёзды
        if stars_enabled:
            update_and_draw_stars(stars)

        # Огонь за курсором
        mx, my = pygame.mouse.get_pos()
        for _ in range(3):
            fire_particles.append({
                "x": mx + random.randint(-5, 5),
                "y": my + random.randint(-5, 5),
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-1.5, -0.5),
                "life": random.randint(20, 40),
                "color": (255, random.randint(100, 150), 50)
            })

        for p in fire_particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            alpha = max(0, min(255, int(p["life"] * 6)))
            pygame.draw.circle(screen, (*p["color"], alpha), (int(p["x"]), int(p["y"])), 4)
            if p["life"] <= 0:
                fire_particles.remove(p)
        # === Переводы для подсказок (как в run_cosmic_storm_mode) ===
        global language
        translations = {
            'ru': {
                'controls': 'Управление:',
                'mouse': 'Мышь — Огонь',
                'modes': 'Режимы:',
                's': 'S — Звёзды',
                'c': 'C — Облака',
                'r': 'R — Сменить трек',
                'system': 'Система:',
                'tab': 'TAB — Скрыть/показать',
                'esc': 'Esc — В меню'
            },
            'en': {
                'controls': 'Controls:',
                'mouse': 'Mouse — Fire',
                'modes': 'Modes:',
                's': 'S — Stars',
                'c': 'C — Clouds',
                'r': 'R — Switch track',
                'system': 'System:',
                'tab': 'TAB — Hide/show',
                'esc': 'Esc — Menu'
            }
        }
        # Инструкция по TAB
        # === Отрисовка подсказок (HUD) ===
        # === HUD для Relax Mode с [ON]/[OFF] и цветами ===
        # === Отрисовка подсказок (HUD) ===
        if show_instructions:
            y_offset = 10
            trans = translations[language]
            font_small = pygame.font.SysFont("consolas", 17)

            def draw_hint(text, color=(180, 255, 200)):
                nonlocal y_offset
                txt = font_small.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 20

            colors = {
                'controls': (100, 200, 255),
                'mouse': (180, 255, 220),
                'modes': (100, 255, 180),
                's': (200, 200, 90),
                'c': (180, 240, 255),
                'r': (200, 100, 255),
                'system': (255, 180, 100),
                'tab': (200, 200, 255),
                'esc': (255, 255, 255)
            }
            # --- Управление ---
            draw_hint(trans['controls'], (100, 200, 255))
            draw_hint(trans['mouse'])
            draw_hint("")

            # --- Режимы ---
            draw_hint(trans['modes'], (100, 255, 180))
            draw_hint(f"{trans['s']} {'[ON]' if stars_enabled else '[OFF]'}", colors['s'])
            draw_hint(f"{trans['c']} {'[ON]' if clouds_enabled else '[OFF]'}", colors['c'])
            draw_hint(f"{trans['r']} {current_track}", colors['r'])
            draw_hint("")

            # --- Система ---
            draw_hint(trans['tab'],colors['tab'])
            draw_hint(trans['esc'],colors['esc'])

        if total_particles_drawn >= 30:
            game_state["relax_done"] = True

        pygame.display.flip()
        clock.tick(60)
def draw_gradient_backgroundd(color1, color2, influence=0, moon_y=0):
    global screen
    bg_surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        moon_influence = max(0, 1 - abs(y - moon_y) / HEIGHT) * influence
        color = (
            int(color1[0] + (color2[0] - color1[0]) * t + moon_influence * 5),  # Уменьшено с 10
            int(color1[1] + (color2[1] - color1[1]) * t + moon_influence * 5),  # Уменьшено с 10
            int(color1[2] + (color2[2] - color1[2]) * t + moon_influence * 10)  # Уменьшено с 20
        )
        color = (
            max(0, min(255, color[0])),
            max(0, min(255, color[1])),
            max(0, min(255, color[2]))
        )
        pygame.draw.line(bg_surface, color, (0, y), (WIDTH, y))
    screen.blit(bg_surface, (0, 0))
class CustomCursor_AM:
    def __init__(self, palette, rainbow_mode):
        self.size = 10
        self.color = palette[0]
        self.alpha = 180
        self.phase = 0
        self.palette = palette
        self.rainbow_mode = rainbow_mode

    def update(self, t, amplitude):
        self.phase += 0.05
        self.size = 10 + 3 * math.sin(self.phase) + 3 * amplitude
        self.alpha = int(180 + 50 * math.sin(self.phase))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )

    def draw(self, mx, my):
        points = [
            (mx, my - self.size),
            (mx + self.size * 0.5, my - self.size * 0.5),
            (mx + self.size, my),
            (mx + self.size * 0.5, my + self.size * 0.5),
            (mx, my + self.size),
            (mx - self.size * 0.5, my + self.size * 0.5),
            (mx - self.size, my),
            (mx - self.size * 0.5, my - self.size * 0.5)
        ]
        pygame.draw.polygon(screen, (*self.color, self.alpha), points)
class SoundSphere_AM:
    def __init__(self, x, y, palette, rainbow_mode):
        self.x = x
        self.y = y
        self.radius = 10
        self.max_radius = 100
        self.color = palette[0] if not rainbow_mode else (
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[0]),
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[1]),
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[2])
        )
        self.alpha = 100
        self.speed = 2
        self.palette = palette
        self.rainbow_mode = rainbow_mode

    def update(self, t, amplitude):
        self.radius += self.speed
        self.max_radius = 100 + amplitude * 50
        self.alpha = int(100 * (1 - self.radius / self.max_radius))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        return self.radius < self.max_radius

    def draw(self):
        surf = pygame.Surface((self.max_radius * 2, self.max_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, self.alpha), (self.max_radius, self.max_radius), int(self.radius), 2)
        screen.blit(surf, (self.x - self.max_radius, self.y - self.max_radius))
class Vortex_AM:
    def __init__(self, x, y, palette, rainbow_mode):
        self.x = x
        self.y = y
        self.radius = 150
        self.life = 3
        self.age = 0
        self.color = palette[1] if not rainbow_mode else (
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[0]),
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[1]),
            int(255 * colorsys.hsv_to_rgb(pygame.time.get_ticks() / 2000 % 1, 0.8, 0.8)[2])
        )
        self.alpha = 100
        self.palette = palette
        self.rainbow_mode = rainbow_mode

    def update(self, t, stars, amplitude):
        self.age += 1 / 60
        if self.age > self.life:
            return False
        self.alpha = int(100 * (1 - self.age / self.life))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        for star in stars:
            dx = star.x - self.x
            dy = star.y - self.y
            dist = (dx**2 + dy**2)**0.5
            if dist < self.radius and dist > 0:
                force = (self.radius - dist) / self.radius * 0.5
                star.vx -= dx / dist * force
                star.vy -= dy / dist * force
        return True

    def draw(self):
        surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        for i in range(10):
            angle = i * math.pi / 5 + self.age * 2
            x = self.radius + math.cos(angle) * self.radius * (1 - self.age / self.life)
            y = self.radius + math.sin(angle) * self.radius * (1 - self.age / self.life)
            pygame.draw.circle(surf, (*self.color, int(self.alpha * 0.5)), (int(x), int(y)), 9)
        screen.blit(surf, (self.x - self.radius, self.y - self.radius))
class Star_AM:
    def __init__(self, x, y, palette):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.size = random.randint(3, 8)
        self.color = palette[0]
        self.alpha = 150
        self.phase = random.uniform(0, 2 * math.pi)
        self.palette = palette
        self.rainbow_mode = False
        self.particle_timer = random.uniform(0, 1)

    def update(self, spheres, rainbow_mode, t, bass):
        self.rainbow_mode = rainbow_mode
        self.x += self.vx
        self.y += self.vy
        if self.x < 0 or self.x > WIDTH:
            self.vx = -self.vx
        if self.y < 0 or self.y > HEIGHT:
            self.vy = -self.vy
        self.alpha = int(150 + 100 * bass)
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        particles = []
        for s in spheres:
            dx = self.x - s.x
            dy = self.y - s.y
            dist = (dx**2 + dy**2)**0.5
            if abs(dist - s.radius) < 10:
                self.color = s.color
                if not rainbow_mode:
                    self.color = s.palette[1]
                for _ in range(int(3 + 5 * s.alpha / 100)):
                    particles.append(GlowParticle_AM(self.x, self.y, self.color, rainbow_mode))
        self.particle_timer += bass * 0.05
        if self.particle_timer > 1:
            self.particle_timer -= 1
            particles.append(GlowParticle_AM(self.x, self.y, self.color, rainbow_mode))
        return particles

    def draw(self):
        points = [
            (self.x, self.y - self.size),
            (self.x + self.size * 0.5, self.y - self.size * 0.5),
            (self.x + self.size, self.y),
            (self.x + self.size * 0.5, self.y + self.size * 0.5),
            (self.x, self.y + self.size),
            (self.x - self.size * 0.5, self.y + self.size * 0.5),
            (self.x - self.size, self.y),
            (self.x - self.size * 0.5, self.y - self.size * 0.5)
        ]
        pygame.draw.polygon(screen, (*self.color, self.alpha), points)
class GlowParticle_AM:
    def __init__(self, x, y, color, rainbow_mode):
        self.x = x
        self.y = y
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)
        self.color = color
        self.rainbow_mode = rainbow_mode
        self.life = random.uniform(0.5, 1)
        self.age = 0
        self.size = random.randint(2, 5)
        self.alpha = 180

    def update(self, t):
        self.age += 1 / 60
        if self.age > self.life:
            return False
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.alpha = int(180 * (1 - self.age / self.life))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        return True

    def draw(self):
        pygame.draw.circle(screen, (*self.color, self.alpha), (int(self.x), int(self.y)), self.size)
class TrailParticle_AM:
    def __init__(self, x, y, color, rainbow_mode):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1, 1)
        self.color = color
        self.rainbow_mode = rainbow_mode
        self.life = random.uniform(0.3, 0.6)
        self.age = 0
        self.size = random.randint(1, 3)
        self.alpha = 150

    def update(self, t):
        self.age += 1 / 60
        if self.age > self.life:
            return False
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9
        self.vy *= 0.9
        self.alpha = int(150 * (1 - self.age / self.life))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        return True

    def draw(self):
        pygame.draw.circle(screen, (*self.color, self.alpha), (int(self.x), int(self.y)), self.size)
class ExplosiveParticle_AM:
    def __init__(self, x, y, color, rainbow_mode):
        self.x = x
        self.y = y
        self.color = color
        self.rainbow_mode = rainbow_mode
        self.life = 2.0  # Живёт 2 секунды
        self.age = 0
        self.size = 10
        self.alpha = 200
        self.phase = random.uniform(0, 2 * math.pi)

    def update(self, t):
        self.age += 1 / 60
        if self.age > self.life:
            return False, []
        self.size = 10 + 5 * math.sin(self.phase + t * 3)  # Пульсация размера
        self.alpha = int(200 * (1 - self.age / self.life))
        if self.rainbow_mode:
            self.color = (
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[0]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[1]),
                int(255 * colorsys.hsv_to_rgb(t / 2 % 1, 0.8, 0.8)[2])
            )
        return True, []

    def explode(self, t, amplitude):
        particles = []
        num_particles = int(10 + 5 * amplitude)  # 10–15 частиц
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 4) * (1 + amplitude)
            p = GlowParticle_AM(self.x, self.y, self.color, self.rainbow_mode)
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            p.size = 3 + 2 * math.sin(t * 2)  # Пульсация размера
            particles.append(p)
        return particles

    def draw(self):
        pygame.draw.circle(screen, (*self.color, self.alpha), (int(self.x), int(self.y)), int(self.size))
def Firefly():
    # Определение цветов и констант
    BLACK = (0, 0, 0)
    NIGHT_BLUE = (10, 20, 50)
    GLOW_COLOR = (200, 255, 100)
    GLOW_COLOR_ALT = (150, 255, 200)
    GLOW_COLOR_THIRD = (100, 200, 255)
    STAR_COLOR = (255, 255, 200)
    CLUSTER_COLOR = (255, 255, 255)
    sparkle_sound = None
    burst_sound = None
    clear_sound = None
    ring_sound = None
    try:
        pygame.mixer.music.load("night.mp3")
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except:
        print("Не удалось загрузить night.mp3")
    class Firefly:
        def __init__(self, x=None, y=None, color=None, orbit_center=None, orbit_radius=0):
            self.x = x if x is not None else random.randint(0, WIDTH)
            self.y = y if y is not None else random.randint(0, HEIGHT)
            self.size = random.uniform(0.5, 0.9)
            self.speed_x = random.uniform(-0.5, 0.5)
            self.speed_y = random.uniform(-0.5, 0.5)
            self.glow = random.uniform(0.4, 1.0)
            self.glow_speed = random.uniform(0.03, 0.07)
            self.color = color if color is not None else random.choice([GLOW_COLOR, GLOW_COLOR_ALT, GLOW_COLOR_THIRD])
            self.phase = random.uniform(0, 2 * math.pi)
            self.particles = []
            self.pulse = random.uniform(0.9, 1.1)
            self.color_shift = 0
            self.orbit_center = orbit_center
            self.orbit_radius = orbit_radius
            self.orbit_angle = random.uniform(0, 2 * math.pi)

        def update(self, attract_to=None, vortex_mode=False, gravity_mode=False, flicker_mode=False, rainbow_mode=False,
                   attractor_mode=False, echo_mode=False, dance_mode=False, cluster_mode=False, clusters=None,
                   spark_mode=False, harmonic_mode=False):
            self.phase += 0.06
            if self.orbit_center:
                self.orbit_angle += 0.05
                self.x = self.orbit_center[0] + math.cos(self.orbit_angle) * self.orbit_radius
                self.y = self.orbit_center[1] + math.sin(self.orbit_angle) * self.orbit_radius
            elif vortex_mode:
                dx, dy = attract_to[0] - self.x, attract_to[1] - self.y
                dist = max(1, math.hypot(dx, dy))
                angle = math.atan2(dy, dx) + 0.1
                self.speed_x = math.cos(angle) * 0.3
                self.speed_y = math.sin(angle) * 0.3
            elif attract_to:
                dx, dy = attract_to[0] - self.x, attract_to[1] - self.y
                dist = max(1, math.hypot(dx, dy))
                self.speed_x += dx / dist * 0.1
                self.speed_y += dy / dist * 0.1
                self.speed_x = max(-0.5, min(0.5, self.speed_x))
                self.speed_y = max(-0.5, min(0.5, self.speed_y))
            elif attractor_mode:
                dx, dy = WIDTH // 2 - self.x, HEIGHT // 2 - self.y
                dist = max(1, math.hypot(dx, dy))
                self.speed_x += dx / dist * 0.1
                self.speed_y += dy / dist * 0.1
                self.speed_x = max(-0.5, min(0.5, self.speed_x))
                self.speed_y = max(-0.5, min(0.5, self.speed_y))
            elif gravity_mode:
                for other in fireflies:
                    if other != self:
                        dx, dy = other.x - self.x, other.y - self.y
                        dist = max(1, math.hypot(dx, dy))
                        if dist < 50:
                            self.speed_x += dx / dist * 0.05
                            self.speed_y += dy / dist * 0.05
                            self.speed_x = max(-0.5, min(0.5, self.speed_x))
                            self.speed_y = max(-0.5, min(0.5, self.speed_y))
            elif cluster_mode and clusters:
                closest_cluster = min(clusters, key=lambda c: math.hypot(c[0] - self.x, c[1] - self.y))
                dx, dy = closest_cluster[0] - self.x, closest_cluster[1] - self.y
                dist = max(1, math.hypot(dx, dy))
                self.speed_x += dx / dist * 0.15
                self.speed_y += dy / dist * 0.15
                self.speed_x = max(-0.5, min(0.5, self.speed_x))
                self.speed_y = max(-0.5, min(0.5, self.speed_y))
            elif dance_mode:
                self.x += math.sin(self.phase) * 0.6 + math.cos(self.phase * 0.5) * 0.4 + math.sin(self.phase * 0.3) * 0.2
                self.y += math.cos(self.phase) * 0.6 + math.sin(self.phase * 0.5) * 0.4 + math.cos(self.phase * 0.3) * 0.2
            elif harmonic_mode:
                self.x += math.sin(self.phase * 0.5) * 0.8 + math.cos(self.phase * 0.3) * 0.4
                self.y += math.cos(self.phase * 0.5) * 0.8 + math.sin(self.phase * 0.3) * 0.4
            else:
                self.x += self.speed_x + math.sin(self.phase) * 0.3
                self.y += self.speed_y + math.cos(self.phase) * 0.3

            if self.x < 0 or self.x > WIDTH:
                self.speed_x *= -1
            if self.y < 0 or self.y > HEIGHT:
                self.speed_y *= -1

            self.glow = math.sin(pygame.time.get_ticks() / 1000.0) * 0.2 + 0.8 if dance_mode else (
                math.sin(pygame.time.get_ticks() / 500.0) * 0.4 + 0.6 if flicker_mode else self.glow + self.glow_speed)
            if not (flicker_mode or dance_mode) and (self.glow > 1.0 or self.glow < 0.4):
                self.glow_speed *= -1

            self.pulse += random.uniform(-0.03, 0.03)
            if self.pulse > 1.1 or self.pulse < 0.9:
                self.pulse = max(0.9, min(1.1, self.pulse))

            self.color_shift += 0.02 if rainbow_mode else 0.01
            if self.color_shift > 2 * math.pi:
                self.color_shift -= 2 * math.pi

            if spark_mode and random.random() < 0.1:
                flashes.append(Flash(self.x, self.y, self.color, radius=7))
                if sparkle_sound:
                    sparkle_sound.play()

            if random.random() < 0.8:
                angle = random.uniform(0, 2 * math.pi)
                self.particles.append({
                    'x': self.x,
                    'y': self.y,
                    'vx': math.cos(angle) * random.uniform(0.2, 0.6),
                    'vy': math.sin(angle) * random.uniform(0.2, 0.6),
                    'life': 1.0,
                    'size': random.uniform(0.2, 0.8)
                })
            self.particles = [p for p in self.particles if p['life'] > 0]
            for p in self.particles:
                p['x'] += p['vx'] * math.cos(self.phase + p['life'] * 2)
                p['y'] += p['vy'] * math.sin(self.phase + p['life'] * 2)
                p['life'] -= 0.04

        def draw(self):
            surface_size = int(self.size * 15)
            surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)

            color_r = int(127 + 128 * math.sin(self.color_shift)) if rainbow_mode else int(
                self.color[0] + math.sin(self.color_shift) * 25)
            color_g = int(127 + 128 * math.cos(self.color_shift)) if rainbow_mode else int(
                self.color[1] + math.cos(self.color_shift) * 25)
            color_b = int(127 + 128 * math.sin(self.color_shift + math.pi)) if rainbow_mode else int(
                self.color[2] + math.sin(self.color_shift + math.pi) * 25)
            base_color = (max(0, min(255, color_r)), max(0, min(255, color_g)), max(0, min(255, color_b)))

            for i in range(30, 0, -1):
                radius = self.size * i * 0.3 * self.pulse
                alpha = int(self.glow * (0.02 * i) * 255)
                pygame.draw.circle(surface, (*base_color, alpha), (surface_size // 2, surface_size // 2), radius)

            if not rainbow_mode:
                core_radius = self.size * self.pulse * 0.6
                pygame.draw.circle(surface, base_color, (surface_size // 2, surface_size // 2), core_radius)

            trail_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
            for i in range(5):
                trail_alpha = int(self.glow * 30 * (1 - i * 0.2))
                pygame.draw.circle(trail_surface, (*base_color, trail_alpha), (surface_size // 2, surface_size // 2),
                                   self.size * 0.6 + i * 1.0)

            for _ in range(5):
                if random.random() < 0.7:
                    angle = random.uniform(0, 2 * math.pi)
                    micro_color = random.choice([GLOW_COLOR, GLOW_COLOR_ALT, GLOW_COLOR_THIRD])
                    micro_alpha = int(self.glow * (50 + random.uniform(0, 50)))
                    micro_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                    pygame.draw.circle(micro_surface, (*micro_color, micro_alpha), (2, 2), random.uniform(0.5, 1.5))
                    screen.blit(micro_surface, (int(self.x - 2 + math.cos(angle) * self.size * 2),
                                               int(self.y - 2 + math.sin(angle) * self.size * 2)),
                                special_flags=pygame.BLEND_RGBA_ADD)

            for particle in self.particles:
                particle_alpha = int(particle['life'] * self.glow * 140)
                particle_surface = pygame.Surface((int(particle['size'] * 6), int(particle['size'] * 6)), pygame.SRCALPHA)
                pygame.draw.circle(particle_surface, (*base_color, particle_alpha),
                                   (particle['size'] * 3, particle['size'] * 3), particle['size'])
                screen.blit(particle_surface,
                            (int(particle['x'] - particle['size'] * 3),
                             int(particle['y'] - particle['size'] * 3)),
                            special_flags=pygame.BLEND_RGBA_ADD)

            glow_surface = pygame.Surface((surface_size * 2, surface_size * 2), pygame.SRCALPHA)
            for i in range(surface_size, 0, -1):
                glow_alpha = int(self.glow * (0.01 * (surface_size - i)) * 255)
                pygame.draw.circle(glow_surface, (*base_color, glow_alpha), (surface_size, surface_size), i)

            fog_surface = pygame.Surface((surface_size * 3, surface_size * 3), pygame.SRCALPHA)
            fog_alpha = int(self.glow * 10 * (1 + 0.2 * math.sin(self.phase)))
            pygame.draw.circle(fog_surface, (*base_color, fog_alpha), (surface_size * 1.5, surface_size * 1.5),
                               surface_size * 1.5)

            surface.blit(trail_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(fog_surface, (int(self.x - surface_size * 1.5), int(self.y - surface_size * 1.5)),
                        special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(glow_surface, (int(self.x - surface_size), int(self.y - surface_size)),
                        special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(surface, (int(self.x - surface_size // 2), int(self.y - surface_size // 2)),
                        special_flags=pygame.BLEND_RGBA_ADD)

    class Flash:
        def __init__(self, x, y, color, radius=5, is_sky_flash=False):
            self.x = x
            self.y = y
            self.color = color
            self.radius = radius if not is_sky_flash else WIDTH
            self.alpha = 255
            self.pulse_phase = 0
            self.particles = [
                {'x': x, 'y': y, 'vx': math.cos(a) * random.uniform(1, 3), 'vy': math.sin(a) * random.uniform(1, 3),
                 'life': 1.0, 'size': random.uniform(0.5, 2)}
                for a in [i * math.pi / 8 for i in range(20 if radius == 7 else 30 if is_sky_flash else 24)]
            ]

        def update(self):
            self.radius += 0.5 if self.radius < WIDTH else 0
            self.alpha -= 15
            self.pulse_phase += 0.1
            self.particles = [p for p in self.particles if p['life'] > 0]
            for p in self.particles:
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['life'] -= 0.05
            return self.alpha > 0 or self.particles

        def draw(self):
            if self.alpha > 0:
                surface = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
                pulse_radius = self.radius * (1 + 0.2 * math.sin(self.pulse_phase))
                pygame.draw.circle(surface, self.color, (self.radius * 2, self.radius * 2), pulse_radius)
                screen.blit(surface, (int(self.x - self.radius * 2), int(self.y - self.radius * 2)),
                            special_flags=pygame.BLEND_RGBA_ADD)
            for p in self.particles:
                p_surface = pygame.Surface((int(p['size'] * 4), int(p['size'] * 4)), pygame.SRCALPHA)
                p_alpha = int(p['life'] * 150)
                pygame.draw.circle(p_surface, self.color, (p['size'] * 2, p['size'] * 2), p['size'])
                screen.blit(p_surface, (int(p['x'] - p['size'] * 2), int(p['y'] - p['size'] * 2)),
                            special_flags=pygame.BLEND_RGBA_ADD)

    def draw_gradient_background():
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            color = (
                int(NIGHT_BLUE[0] * (1 - ratio) + BLACK[0] * ratio),
                int(NIGHT_BLUE[1] * (1 - ratio) + BLACK[1] * ratio),
                int(NIGHT_BLUE[2] * (1 - ratio) + BLACK[2] * ratio)
            )
            pygame.draw.line(screen, color, (0, y), (WIDTH, y))
        for star in stars:
            pygame.draw.circle(screen, STAR_COLOR, star, random.randint(1, 2))
        if cluster_mode:
            for cluster in clusters:
                surface = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(surface, (*CLUSTER_COLOR, 50), (10, 10), 10)
                screen.blit(surface, (int(cluster[0] - 10), int(cluster[1] - 10)), special_flags=pygame.BLEND_RGBA_ADD)

    font_big = pygame.font.SysFont("consolas", 42, bold=True)
    font_small = pygame.font.SysFont("consolas", 28, italic=True)
    timer = 0
    fade = 0
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(100)]
    fireflies = [Firefly() for _ in range(50)]
    flashes = []
    clusters = []
    attract_mode = False
    vortex_mode = False
    flicker_mode = False
    gravity_mode = False
    rainbow_mode = False
    attractor_mode = False
    echo_mode = False
    dance_mode = False
    cluster_mode = False
    spark_mode = False
    harmonic_mode = False
    random_spawn_mode = False
    last_click_time = 0
    click_count = 0
    mouse_held = False
    echo_queue = []
    last_spawn_time = 0
    show_instructions = True
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                color = (
                    int(100 + (x / WIDTH) * 155),
                    int(150 + (y / HEIGHT) * 105),
                    int(100 + ((x + y) / (WIDTH + HEIGHT)) * 155)
                )
                if event.button == 1 and len(fireflies) < 200:
                    mouse_held = True
                    if pygame.time.get_ticks() - last_click_time < 300:
                        click_count += 1
                        if click_count == 2:
                            for i in range(random.randint(8, 10)):
                                angle = i * 2 * math.pi / 8
                                if len(fireflies) < 200:
                                    fireflies.append(Firefly(x + math.cos(angle) * 20, y + math.sin(angle) * 20, color))
                                    flashes.append(Flash(x + math.cos(angle) * 20, y + math.sin(angle) * 20, color, radius=5))
                            if burst_sound:
                                burst_sound.play()
                            click_count = 0
                        if echo_mode:
                            for _ in range(random.randint(2, 3)):
                                echo_queue.append((x + random.uniform(-10, 10), y + random.uniform(-10, 10), color, 0.5, pygame.time.get_ticks()))
                    else:
                        click_count = 1
                        fireflies.append(Firefly(x, y, color))
                        flashes.append(Flash(x, y, color, radius=5))
                        if sparkle_sound:
                            sparkle_sound.play()
                        if echo_mode:
                            for _ in range(random.randint(2, 3)):
                                echo_queue.append((x + random.uniform(-10, 10), y + random.uniform(-10, 10), color, 0.5, pygame.time.get_ticks()))
                    last_click_time = pygame.time.get_ticks()
                elif event.button == 3 and len(fireflies) < 200:
                    for _ in range(random.randint(3, 5)):
                        if len(fireflies) < 200:
                            fireflies.append(Firefly(x, y, color))
                            flashes.append(Flash(x, y, color, radius=5))
                    if burst_sound:
                        burst_sound.play()
                    if echo_mode:
                        for _ in range(random.randint(2, 3)):
                            echo_queue.append((x + random.uniform(-10, 10), y + random.uniform(-10, 10), color, 0.5, pygame.time.get_ticks()))
                elif event.button == 2 and len(fireflies) < 200:
                    for i in range(12):
                        angle = i * 2 * math.pi / 12
                        if len(fireflies) < 200:
                            fireflies.append(Firefly(x + math.cos(angle) * 30, y + math.sin(angle) * 30, color, orbit_center=(x, y), orbit_radius=30))
                            flashes.append(Flash(x + math.cos(angle) * 30, y + math.sin(angle) * 30, color, radius=5))
                    if ring_sound:
                        ring_sound.play()
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_held = False
            if event.type == pygame.MOUSEMOTION and mouse_held and len(fireflies) < 200:
                x, y = event.pos
                color = (
                    int(100 + (x / WIDTH) * 155),
                    int(150 + (y / HEIGHT) * 105),
                    int(100 + ((x + y) / (WIDTH + HEIGHT)) * 155)
                )
                fireflies.append(Firefly(x, y, color))
                flashes.append(Flash(x, y, color, radius=5))
                if sparkle_sound and random.random() < 0.2:
                    sparkle_sound.play()
                if echo_mode:
                    for _ in range(random.randint(2, 3)):
                        echo_queue.append((x + random.uniform(-10, 10), y + random.uniform(-10, 10), color, 0.5, pygame.time.get_ticks()))
            if event.type == pygame.MOUSEWHEEL:
                delta = event.y * 0.1
                for firefly in fireflies:
                    firefly.glow = max(0.2, min(1.2, firefly.glow + delta))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    attract_mode = not attract_mode
                    vortex_mode = False
                    gravity_mode = False
                    attractor_mode = False
                    dance_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                    vortex_mode = not vortex_mode
                    attract_mode = False
                    gravity_mode = False
                    attractor_mode = False
                    dance_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_LCTRL or event.key == pygame.K_RCTRL:
                    new_color = random.choice([GLOW_COLOR, GLOW_COLOR_ALT, GLOW_COLOR_THIRD])
                    for firefly in fireflies:
                        firefly.color = new_color
                elif event.key == pygame.K_r:
                    fireflies.clear()
                    fireflies.extend([Firefly() for _ in range(50)])
                    flashes.append(Flash(WIDTH // 2, HEIGHT // 2, STAR_COLOR, is_sky_flash=True))
                    if burst_sound:
                        burst_sound.play()
                elif event.key == pygame.K_f:
                    flicker_mode = not flicker_mode
                elif event.key == pygame.K_g:
                    gravity_mode = not gravity_mode
                    attract_mode = False
                    vortex_mode = False
                    attractor_mode = False
                    dance_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_c:
                    fireflies.clear()
                    if clear_sound:
                        clear_sound.play()
                elif event.key == pygame.K_t:
                    spark_mode = not spark_mode
                elif event.key == pygame.K_b and fireflies:
                    firefly = random.choice(fireflies)
                    x, y = firefly.x, firefly.y
                    color = firefly.color
                    fireflies.remove(firefly)
                    for _ in range(random.randint(5, 7)):
                        if len(fireflies) < 200:
                            angle = random.uniform(0, 2 * math.pi)
                            fireflies.append(Firefly(x + math.cos(angle) * 10, y + math.sin(angle) * 10, color))
                            flashes.append(Flash(x, y, color, radius=10))
                    if burst_sound:
                        burst_sound.play()
                elif event.key == pygame.K_s:
                    pygame.image.save(screen, "screenshot.png")
                    if clear_sound:
                        clear_sound.play()
                elif event.key == pygame.K_q:
                    rainbow_mode = not rainbow_mode
                elif event.key == pygame.K_d:
                    dance_mode = not dance_mode
                    attract_mode = False
                    vortex_mode = False
                    gravity_mode = False
                    attractor_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_a:
                    attractor_mode = not attractor_mode
                    attract_mode = False
                    vortex_mode = False
                    gravity_mode = False
                    dance_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_e:
                    echo_mode = not echo_mode
                elif event.key == pygame.K_p:
                    cluster_mode = not cluster_mode
                    if cluster_mode:
                        clusters = [(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50)) for _ in range(random.randint(3, 5))]
                    else:
                        clusters.clear()
                elif event.key == pygame.K_w:
                    random_spawn_mode = not random_spawn_mode
                    attract_mode = False
                    vortex_mode = False
                    gravity_mode = False
                    attractor_mode = False
                    dance_mode = False
                    cluster_mode = False
                    harmonic_mode = False
                elif event.key == pygame.K_h:
                    harmonic_mode = not harmonic_mode
                    attract_mode = False
                    vortex_mode = False
                    gravity_mode = False
                    attractor_mode = False
                    dance_mode = False
                    cluster_mode = False
                    random_spawn_mode = False
                elif event.key == pygame.K_TAB:  # Добавлена обработка Tab
                    show_instructions = not show_instructions

        draw_gradient_background()
        mouse_pos = pygame.mouse.get_pos()
        current_time = pygame.time.get_ticks()

        if random_spawn_mode and current_time - last_spawn_time > random.randint(500, 1000) and len(fireflies) < 200:
            for _ in range(random.randint(1, 2)):
                if len(fireflies) < 200:
                    x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
                    color = random.choice([GLOW_COLOR, GLOW_COLOR_ALT, GLOW_COLOR_THIRD])
                    fireflies.append(Firefly(x, y, color))
                    flashes.append(Flash(x, y, color, radius=5))
                    if sparkle_sound:
                        sparkle_sound.play()
                    if echo_mode:
                        for _ in range(random.randint(2, 3)):
                            echo_queue.append((x + random.uniform(-10, 10), y + random.uniform(-10, 10), color, 0.5, current_time))
            last_spawn_time = current_time

        echo_queue = [(x, y, color, glow, time) for x, y, color, glow, time in echo_queue if current_time - time < 100]
        for x, y, color, glow, time in echo_queue[:]:
            if current_time - time >= 100:
                if len(fireflies) < 200:
                    fireflies.append(Firefly(x, y, color))
                    flashes.append(Flash(x, y, color, radius=5))
                    if sparkle_sound:
                        sparkle_sound.play()
                echo_queue.remove((x, y, color, glow, time))

        for firefly in fireflies:
            firefly.update(mouse_pos if attract_mode or vortex_mode else None, vortex_mode, gravity_mode, flicker_mode,
                           rainbow_mode, attractor_mode, echo_mode, dance_mode, cluster_mode, clusters, spark_mode, harmonic_mode)
            firefly.draw()

        flashes[:] = [f for f in flashes if f.update()]
        for f in flashes:
            f.draw()
        global language
        translations = {
            'ru': {
                'controls': 'Управление:',
                'left_click': 'ЛКМ — Добавить',
                'double_click': 'Двойной клик — Взрыв',
                'right_click': 'ПКМ — Группа',
                'middle_click': 'СКМ — Кольцо',
                'hold_move': 'Удержание — Тропа',
                'modes': 'Режимы:',
                'space': 'Пробел — Притяжение',
                'shift': 'Shift — Вихрь',
                'f': 'F — Мерцание',
                'g': 'G — Гравитация',
                'q': 'Q — Радуга',
                'd': 'D — Танец',
                'a': 'A — К центру',
                'e': 'E — Эхо-спавн',
                'p': 'P — Кластеры',
                'w': 'W — Случайный спавн',
                'h': 'H — Петля',
                'system': 'Система:',
                'ctrl': 'Ctrl — Сменить цвет',
                'r': 'R — Перезапуск',
                'c': 'C — Очистить всё',
                't': 'T — Искры',
                'b': 'B — Взрыв случайного',
                's': 'S — Скриншот',
                'tab': 'TAB — Скрыть/показать',
                'esc': 'Esc — Выход'
            },
            'en': {
                'controls': 'Controls:',
                'left_click': 'LMB — Add',
                'double_click': 'Double click — Burst',
                'right_click': 'RMB — Group',
                'middle_click': 'MMB — Ring',
                'hold_move': 'Hold — Trail',
                'modes': 'Modes:',
                'space': 'Space — Attract',
                'shift': 'Shift — Vortex',
                'f': 'F — Flicker',
                'g': 'G — Gravity',
                'q': 'Q — Rainbow',
                'd': 'D — Dance',
                'a': 'A — Attract center',
                'e': 'E — Echo spawn',
                'p': 'P — Clusters',
                'w': 'W — Random spawn',
                'h': 'H — Hook',
                'system': 'System:',
                'ctrl': 'Ctrl — Change color',
                'r': 'R — Restart',
                'c': 'C — Clear all',
                't': 'T — Sparkles',
                'b': 'B — Burst random',
                's': 'S — Screenshot',
                'tab': 'TAB — Hide/show',
                'esc': 'Esc — Exit'
            }
        }
        # === Отрисовка подсказок (HUD) ===
        if show_instructions:
            y_offset = 10
            trans = translations[language]
            font_small = pygame.font.SysFont("consolas", 17)

            def draw_hint(text, color=(180, 255, 200)):
                nonlocal y_offset
                txt = font_small.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 20

            # --- Цвета для каждой строки ---
            colors = {
                'controls': (100, 200, 255),
                'left_click': (180, 255, 220),
                'double_click': (180, 240, 255),
                'right_click': (170, 255, 200),
                'middle_click': (160, 240, 255),
                'hold_move': (190, 255, 230),
                'modes': (100, 255, 180),
                'space': (140, 255, 160),
                'shift': (130, 240, 150),
                'f': (120, 230, 140),
                'g': (110, 220, 130),
                'q': (255, 180, 255),  # Q — Радуга
                'd': (255, 200, 160),  # D — Танец
                'a': (200, 255, 180),  # A — К центру
                'w': (220, 255, 200),  # W — Случайный
                'h': (255, 220, 180),  # H — Гармония
                'system': (255, 180, 100),
                'ctrl': (255, 200, 140),
                'r': (255, 190, 130),
                'c': (255, 170, 120),
                't': (255, 210, 150),
                'b': (255, 160, 140),
                's': (255, 230, 170),
                'tab': (255, 240, 200),
                'esc': (255, 255, 255)
            }

            # --- Управление ---
            draw_hint(trans['controls'], colors['controls'])
            draw_hint(trans['left_click'], colors['left_click'])
            draw_hint(trans['double_click'], colors['double_click'])
            draw_hint(trans['right_click'], colors['right_click'])
            draw_hint(trans['middle_click'], colors['middle_click'])
            draw_hint(trans['hold_move'], colors['hold_move'])
            draw_hint(trans['b'], colors['controls'])
            draw_hint("")  # Отступ

            # --- Режимы ---
            draw_hint(trans['modes'], colors['modes'])
            draw_hint(trans['space'], colors['space'])
            draw_hint(trans['shift'], colors['shift'])
            draw_hint(trans['f'], colors['f'])
            draw_hint(f"{trans['t']} {'[ON]' if spark_mode else '[OFF]'}", colors['t'])
            draw_hint(f"{trans['q']} {'[ON]' if rainbow_mode else '[OFF]'}", colors['q'])
            draw_hint(f"{trans['d']} {'[ON]' if dance_mode else '[OFF]'}", colors['d'])
            draw_hint(f"{trans['w']} {'[ON]' if random_spawn_mode else '[OFF]'}", colors['w'])
            draw_hint(f"{trans['h']} {'[ON]' if harmonic_mode else '[OFF]'}", colors['h'])
            draw_hint("")  # Отступ

            # --- Система ---
            draw_hint(trans['system'], colors['system'])
            draw_hint(trans['ctrl'], colors['ctrl'])
            draw_hint(trans['r'], colors['r'])
            draw_hint(trans['c'], colors['c'])
            draw_hint(trans['s'], colors['s'])
            draw_hint("")

            draw_hint(trans['tab'], colors['tab'])
            draw_hint(trans['esc'], colors['esc'])
        # Отрисовка красивого курсора
        cursor_size = 20
        cursor_surface = pygame.Surface((cursor_size * 2, cursor_size * 2), pygame.SRCALPHA)
        for i in range(cursor_size, 0, -1):
            alpha = int(255 * (i / cursor_size) * 0.7)
            radius = i * 0.5 + 5 * math.sin(pygame.time.get_ticks() / 200.0)
            pygame.draw.circle(cursor_surface, (GLOW_COLOR[0], GLOW_COLOR[1], GLOW_COLOR[2], alpha),
                               (cursor_size, cursor_size), radius, 1)
        pygame.draw.circle(cursor_surface, GLOW_COLOR, (cursor_size, cursor_size), 3)
        screen.blit(cursor_surface, (mouse_pos[0] - cursor_size, mouse_pos[1] - cursor_size))

        pygame.display.flip()
        clock.tick(60)
        timer += 1
def run_cosmic_symphony_mode():
    global screen, clock
    pygame.mouse.set_visible(False)
    tracks = [
        'moog-city-2.mp3', 'danny.mp3', 'sweden.mp3',
        'equinoxe.mp3', 'minecraft.mp3', 'haggstrom.mp3',
        'subwoofer-lullaby.mp3', 'door.mp3',
        'dry-hands.mp3', 'moog-city.mp3'
    ]
    current_track = random.randint(0, len(tracks) - 1)
    spheres = []
    vortices = []
    stars = [Star_AM(random.randint(0, WIDTH), random.randint(0, HEIGHT), [(150, 200, 255), (200, 200, 255)]) for _ in range(30)]
    particles = []
    palette = [(150, 200, 255), (200, 200, 255)]
    rainbow_mode = False
    music_on = True
    font = pygame.font.Font(None, 24)
    amplitude = 0
    bass = 0
    cursor = CustomCursor_AM(palette, rainbow_mode)
    last_trail_time = 0
    last_burst_time = 0
    show_instructions = True
    try:
        pygame.mixer.music.load(tracks[current_track])
        pygame.mixer.music.play(-1)
    except:
        print(f"Failed to load: {tracks[current_track]}")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if music_on:
                    pygame.mixer.music.stop()
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    spheres.append(SoundSphere_AM(event.pos[0], event.pos[1], palette, rainbow_mode))
                elif event.button == 3:
                    vortices.append(Vortex_AM(event.pos[0], event.pos[1], palette, rainbow_mode))
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if music_on:
                        pygame.mixer.music.stop()
                    return
                if event.key == pygame.K_1:
                    palette = [(150, 200, 255), (200, 200, 255)]
                    for s in stars:
                        s.palette = palette
                        s.color = palette[0]
                    cursor.palette = palette
                if event.key == pygame.K_2:
                    palette = [(200, 150, 255), (255, 200, 255)]
                    for s in stars:
                        s.palette = palette
                        s.color = palette[0]
                    cursor.palette = palette
                if event.key == pygame.K_3:
                    palette = [(150, 255, 200), (200, 255, 200)]
                    for s in stars:
                        s.palette = palette
                        s.color = palette[0]
                    cursor.palette = palette
                if event.key == pygame.K_r:
                    rainbow_mode = not rainbow_mode
                    cursor.rainbow_mode = rainbow_mode
                    for s in stars:
                        s.rainbow_mode = rainbow_mode
                if event.key == pygame.K_m:
                    music_on = not music_on
                    if music_on:
                        pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.music.stop()
                if event.key == pygame.K_TAB:  # Добавлена обработка Tab
                    show_instructions = not show_instructions
                if event.key == pygame.K_n:
                    current_track = (current_track + 1) % len(tracks)
                    if music_on:
                        pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.load(tracks[current_track])
                            pygame.mixer.music.play(-1)
                        except:
                            print(f"Failed to load: {tracks[current_track]}")
                if event.key == pygame.K_p:
                    current_track = (current_track - 1) if current_track > 0 else len(tracks) - 1
                    if music_on:
                        pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.load(tracks[current_track])
                            pygame.mixer.music.play(-1)
                        except:
                            print(f"Failed to load: {tracks[current_track]}")
                if event.key == pygame.K_t:
                    current_track = random.randint(0, len(tracks) - 1)
                    if music_on:
                        pygame.mixer.music.stop()
                        try:
                            pygame.mixer.music.load(tracks[current_track])
                            pygame.mixer.music.play(-1)
                        except:
                            print(f"Failed to load: {tracks[current_track]}")
                if event.key == pygame.K_b:
                    if pygame.time.get_ticks() - last_burst_time > 200:
                        mx, my = pygame.mouse.get_pos()
                        # Проверяем, есть ли частица для взрыва
                        for p in particles:
                            if isinstance(p, ExplosiveParticle_AM):
                                dx = p.x - mx
                                dy = p.y - my
                                dist = (dx**2 + dy**2)**0.5
                                if dist < 50:
                                    particles.extend(p.explode(pygame.time.get_ticks() / 1000, amplitude))
                                    particles.remove(p)
                                    last_burst_time = pygame.time.get_ticks()
                                    break
                        else:
                            # Создаём новую частицу, если не взорвали
                            particles.append(ExplosiveParticle_AM(mx, my, cursor.color, rainbow_mode))
                            last_burst_time = pygame.time.get_ticks()

        t = pygame.time.get_ticks() / 1000
        amplitude = 0.5 + 0.5 * math.sin(t * 0.5)
        bass = 0.3 + 0.3 * math.sin(t * 0.7)

        mx, my = pygame.mouse.get_pos()
        mouse_influence = mx / WIDTH
        moon_y = HEIGHT // 2 + 100 * math.sin(t * 0.5)  # Убрана зависимость от amplitude
        color1 = (0, 10, 30)
        color2 = (
            max(0, min(255, int(10 + 5 * math.sin(t) + 5 * mouse_influence))),
            max(0, min(255, int(20 + 5 * math.cos(t) + 5 * mouse_influence))),
            max(0, min(255, int(30 + 10 * math.sin(t + 1) + 5 * mouse_influence)))
        )
        draw_gradient_backgroundd(color1, color2, 0.5, moon_y)  # Фиксированный influence

        if pygame.time.get_ticks() - last_trail_time > 100:
            if random.random() < 0.5 + amplitude:
                particles.append(TrailParticle_AM(mx, my, cursor.color, rainbow_mode))
            last_trail_time = pygame.time.get_ticks()

        for star in stars:
            new_particles = star.update(spheres, rainbow_mode, t, bass)
            particles.extend(new_particles)
        vortices_to_keep = []
        for v in vortices:
            active = v.update(t, stars, amplitude)
            if active:
                vortices_to_keep.append(v)
        vortices[:] = vortices_to_keep
        spheres = [s for s in spheres if s.update(t, amplitude)]
        particles_to_keep = []
        for p in particles:
            active, new_particles = p.update(t) if isinstance(p, ExplosiveParticle_AM) else (p.update(t), [])
            particles.extend(new_particles)
            if active:
                particles_to_keep.append(p)
        particles = particles_to_keep
        if len(spheres) > 10:
            spheres = spheres[-10:]
        if len(particles) > 100:
            particles = particles[-100:]

        cursor.update(t, amplitude)

        for star in stars:
            star.draw()
        for sphere in spheres:
            sphere.draw()
        for vortex in vortices:
            vortex.draw()
        for particle in particles:
            particle.draw()

        cursor.draw(mx, my)
        # === Словарь переводов для подсказок ===
        translations = {
            'ru': {
                'controls': 'Управление:',
                'left_click': 'ЛКМ — Создать сферу',
                'right_click': 'ПКМ — Создать вихрь',
                'palette': '1, 2, 3 — Сменить палитру',
                'track': 'Трек —',
                'modes': 'Режимы:',
                'rainbow': 'R — Радужный режим',
                'music': 'M — Вкл/выкл музыку',
                'random': 'T — Случайный трек',
                'next': 'N — Следующий трек',
                'prev': 'P — Предыдущий трек',
                'burst': 'B — Взрыв частиц',
                'hide_hud': 'TAB — Скрыть/показать подсказки',
                'esc': 'ESC — Вернуться в меню'
            },
            'en': {
                'controls': 'Controls:',
                'left_click': 'LMB — Create sphere',
                'right_click': 'RMB — Create vortex',
                'palette': '1, 2, 3 — Change palette',
                'track': 'Track —',
                'modes': 'Modes:',
                'rainbow': 'R — Rainbow mode',
                'music': 'M — Toggle music',
                'random': 'T — Random track',
                'next': 'N — Next track',
                'prev': 'P — Previous track',
                'burst': 'B — Burst particles',
                'hide_hud': 'TAB — Hide/Show hints',
                'esc': 'ESC — Back to menu'
            }
        }
        # === Красивые подсказки как в cosmic_storm ===
        if show_instructions:
            y_offset = 10
            small_font = pygame.font.SysFont("consolas", 17)

            def draw_text(text, color=(130, 180, 255)):
                nonlocal y_offset
                txt = small_font.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 22

            trans = translations[language]

            # Управление
            draw_text(trans['controls'], (100, 200, 255))
            draw_text(trans['left_click'])
            draw_text(trans['right_click'])
            draw_text(trans['palette'])
            draw_text("")
            draw_text(f"{trans['track']} {tracks[current_track]}", (200, 200, 255))
            draw_text(trans['next'])
            draw_text(trans['prev'])
            draw_text(trans['random'])

            draw_text("")
            draw_text(trans['modes'], (100, 200, 255))
            draw_text(f"{trans['rainbow']} {'[ON]' if rainbow_mode else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['music']} {'[ON]' if music_on else '[OFF]'}", (200, 200, 100))


            draw_text("")
            draw_text(trans['esc'])
            draw_text(trans['hide_hud'])

        pygame.display.flip()
        clock.tick(60)
def run_moon_river_mode():
    # -------------------------------------------------------------
    trail_mode = False
    def draw_gradient_background(color1, color2, moon_x, moon_y, phase_influence=0):
        """Рисует градиентный фон с учетом влияния луны, мыши и фазы"""
        for y in range(HEIGHT):
            # Базовый вертикальный градиент
            ratio = y / HEIGHT
            base_r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            base_g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            base_b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            # Влияние положения мыши и луны
            mx, my = pygame.mouse.get_pos()
            dx_mouse = mx - (WIDTH / 2)
            dy_mouse = my - (HEIGHT / 2)
            dist_mouse_center = max(1, (dx_mouse ** 2 + dy_mouse ** 2) ** 0.5)
            dx_moon = moon_x - (WIDTH / 2)
            dy_moon = moon_y - (HEIGHT / 2)
            dist_moon_center = max(1, (dx_moon ** 2 + dy_moon ** 2) ** 0.5)
            # Пульсирующий эффект от времени
            t = pygame.time.get_ticks() / 10000.0
            pulse = math.sin(t * 2) * 0.1  # Медленная пульсация
            # Комбинируем влияния
            influence_mouse = max(0, 1.0 - dist_mouse_center / (WIDTH * 0.7)) * 0.3
            influence_moon = max(0, 1.0 - dist_moon_center / (WIDTH * 0.7)) * 0.2
            influence_phase = phase_influence * 0.15  # Влияние фазы
            # Применяем все влияния
            final_r = base_r + int((influence_mouse * 20 + influence_moon * 15 + influence_phase * 10) * math.sin(t))
            final_g = base_g + int((influence_mouse * 15 + influence_moon * 10 + influence_phase * 15) * math.cos(t))
            final_b = base_b + int(
                (influence_mouse * 10 + influence_moon * 20 + influence_phase * 5) * math.sin(t + math.pi / 2))
            color = (
                max(0, min(255, int(final_r * (1 + pulse)))),
                max(0, min(255, int(final_g * (1 + pulse)))),
                max(0, min(255, int(final_b * (1 + pulse))))
            )
            pygame.draw.line(screen, color, (0, y), (WIDTH, y))

    # --- Классы частиц ---

    # --- Базовый класс частиц ---
    class BaseParticle:
        """Базовый класс для всех частиц, притягивающихся к луне"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            self.x = float(x)
            self.y = float(y)
            self.vx = random.uniform(-1, 1)
            self.vy = random.uniform(-1, 1)
            self.palette = palette
            self.rainbow_mode = rainbow_mode
            self.moon_phase = moon_phase
            self.life = random.randint(100, 300)  # Живут дольше
            self.max_life = self.life
            self.size = random.randint(2, 6)
            self.update_color()

        def update_color(self):
            """Обновить цвет в зависимости от режима, палитры и фазы"""
            if self.rainbow_mode:
                # Радужный цвет, зависящий от времени и положения
                hue = (pygame.time.get_ticks() / 5000.0 + (self.x + self.y) / (WIDTH + HEIGHT)) % 1.0
                rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.9)
                self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            elif self.palette:
                # Цвет зависит от фазы луны
                palette_index = self.moon_phase % len(self.palette)
                self.color = self.palette[palette_index]
            else:
                self.color = (200, 200, 255)  # Цвет по умолчанию

        def apply_force(self, moon_x, moon_y, dt=1.0):
            """Применить силу притяжения к луне"""
            dx = moon_x - self.x
            dy = moon_y - self.y
            dist_sq = dx * dx + dy * dy
            # Проверка на деление на ноль
            if dist_sq < 0.1:
                dist_sq = 0.1
            dist = math.sqrt(dist_sq)

            # Сила притяжения, модифицируемая фазой луны
            base_force = 150.0
            phase_mod = 1.0 + (self.moon_phase / 4.0)  # Фаза 4 даёт +100% силы
            force = (base_force * phase_mod) / dist_sq * dt
            force = min(force, 10.0)  # Ограничиваем максимальную силу
            self.vx += dx / dist * force
            self.vy += dy / dist * force
            # Затухание скорости для плавности
            self.vx *= 0.98
            self.vy *= 0.98

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            """Базовое обновление частицы"""
            self.life -= 1
            self.moon_phase = moon_phase
            self.update_color()
            dt = 1.0 / 60.0  # Предполагаем 60 FPS для стабильной физики
            self.apply_force(moon_x, moon_y, dt)
            self.x += self.vx
            self.y += self.vy
            return self.life > 0

        def is_alive(self):
            """Проверить, жива ли частица"""
            return self.life > 0

        def draw(self, surface):
            """Базовая отрисовка (круг)"""
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0:
                s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color, alpha // 2), (self.size, self.size), self.size)  # Аура
                pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size * 0.7)
                surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

    # --- Конкретные типы частиц ---
    class GlowParticle(BaseParticle):
        """Светящаяся частица с пульсацией"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            super().__init__(x, y, palette, rainbow_mode, moon_phase)
            self.pulse = 0
            self.oscillation = random.uniform(0, 2 * math.pi)

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            alive = super().update(moon_x, moon_y, palette, rainbow_mode, t, moon_phase)
            self.oscillation += 0.1
            self.pulse = math.sin(self.oscillation) * 0.3
            return alive

        def draw(self, surface):
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0:
                current_size = self.size * (1 + self.pulse)
                s = pygame.Surface((int(current_size * 3), int(current_size * 3)), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color, alpha // 4), (int(current_size * 1.5), int(current_size * 1.5)),
                                   int(current_size * 1.5))  # Большая аура
                pygame.draw.circle(s, (*self.color, alpha // 2), (int(current_size * 1.5), int(current_size * 1.5)),
                                   int(current_size))
                pygame.draw.circle(s, (*self.color, alpha), (int(current_size * 1.5), int(current_size * 1.5)),
                                   int(current_size * 0.7))
                surface.blit(s, (int(self.x - current_size * 1.5), int(self.y - current_size * 1.5)))

    class SparkParticle(BaseParticle):
        """Искрящаяся частица с хвостом"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            super().__init__(x, y, palette, rainbow_mode, moon_phase)
            self.trail = [(self.x, self.y)] * 3
            # Начальная скорость может быть выше
            self.vx *= random.uniform(1.0, 2.0)
            self.vy *= random.uniform(1.0, 2.0)

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            alive = super().update(moon_x, moon_y, palette, rainbow_mode, t, moon_phase)
            self.trail.append((self.x, self.y))
            if len(self.trail) > 6:
                self.trail.pop(0)
            return alive

        def draw(self, surface):
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0:
                # Рисуем хвост
                for i, (tx, ty) in enumerate(self.trail):
                    trail_alpha = int(alpha * (i / len(self.trail)) ** 2)  # Квадрат для быстрого затухания
                    sz = max(1, int(self.size * (i / len(self.trail))))
                    if trail_alpha > 10:
                        pygame.draw.circle(surface, (*self.color, trail_alpha), (int(tx), int(ty)), sz)
                # Рисуем голову
                pygame.draw.circle(surface, (*self.color, alpha), (int(self.x), int(self.y)), self.size)

    class PulseParticle(BaseParticle):
        """Пульсирующая частица"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            super().__init__(x, y, palette, rainbow_mode, moon_phase)
            self.base_size = self.size
            self.pulse_phase = random.uniform(0, 2 * math.pi)
            self.pulse_speed = random.uniform(0.05, 0.15)

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            alive = super().update(moon_x, moon_y, palette, rainbow_mode, t, moon_phase)
            self.pulse_phase += self.pulse_speed
            self.size = self.base_size + math.sin(self.pulse_phase) * (self.base_size * 0.5)
            return alive

        def draw(self, surface):
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0 and self.size > 0:
                # Рисуем несколько концентрических кругов
                for i in range(3):
                    size_mult = 1.0 - i * 0.3
                    current_size = self.size * size_mult
                    if current_size > 0:
                        circle_alpha = int(alpha * size_mult)
                        s = pygame.Surface((int(current_size * 2), int(current_size * 2)), pygame.SRCALPHA)
                        pygame.draw.circle(s, (*self.color, circle_alpha // 3), (int(current_size), int(current_size)),
                                           int(current_size))
                        pygame.draw.circle(s, (*self.color, circle_alpha), (int(current_size), int(current_size)),
                                           int(current_size * 0.7))
                        surface.blit(s, (int(self.x - current_size), int(self.y - current_size)))

    class FlareParticle(BaseParticle):
        """Вспышка - крест и круг"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            super().__init__(x, y, palette, rainbow_mode, moon_phase)
            self.max_size = random.randint(15, 30)
            self.size = 0
            self.grow_speed = random.uniform(0.5, 1.5)

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            self.size += self.grow_speed
            # Вспышки не притягиваются, просто растут и исчезают
            self.life -= 1
            self.moon_phase = moon_phase
            self.update_color()
            return self.size < self.max_size and self.life > 0

        def draw(self, surface):
            alpha = int(255 * (1 - self.size / self.max_size))
            if alpha > 0:
                s = pygame.Surface((self.max_size * 2, self.max_size * 2), pygame.SRCALPHA)
                # Горизонтальная и вертикальная линии
                pygame.draw.line(s, (*self.color, alpha // 2), (0, self.max_size), (self.max_size * 2, self.max_size),
                                 int(self.size // 2))
                pygame.draw.line(s, (*self.color, alpha // 2), (self.max_size, 0), (self.max_size, self.max_size * 2),
                                 int(self.size // 2))
                # Центральный круг
                pygame.draw.circle(s, (*self.color, alpha), (self.max_size, self.max_size), int(self.size * 0.7))
                surface.blit(s, (int(self.x - self.max_size), int(self.y - self.max_size)))

    class OrbitParticle(BaseParticle):
        """Орбитальная частица - движется по спирали вокруг луны, прежде чем достичь её"""

        def __init__(self, x, y, palette, rainbow_mode=False, moon_phase=0):
            super().__init__(x, y, palette, rainbow_mode, moon_phase)
            self.orbit_radius = random.randint(50, 150)
            self.angle = random.uniform(0, 2 * math.pi)
            self.angular_velocity = random.uniform(0.02, 0.05) * (1 if random.random() > 0.5 else -1)
            self.spiral_speed = random.uniform(0.5, 1.5)
            self.target_x = None
            self.target_y = None
            self.in_orbit = True
            self.orbit_time = 0
            self.max_orbit_time = random.randint(200, 400)  # Время в орбите

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            self.life -= 1
            self.moon_phase = moon_phase
            self.update_color()

            if self.in_orbit:
                self.orbit_time += 1
                # Движение по орбите
                self.angle += self.angular_velocity
                # Постепенное приближение к луне (спираль)
                self.orbit_radius -= self.spiral_speed
                self.x = moon_x + self.orbit_radius * math.cos(self.angle)
                self.y = moon_y + self.orbit_radius * math.sin(self.angle)

                if self.orbit_time > self.max_orbit_time or self.orbit_radius <= 5:
                    self.in_orbit = False
                    # После выхода из орбиты начинаем обычное притяжение
                    # Инициализируем скорость для плавного перехода
                    tangent_vx = -self.orbit_radius * self.angular_velocity * math.sin(self.angle)
                    tangent_vy = self.orbit_radius * self.angular_velocity * math.cos(self.angle)
                    self.vx = tangent_vx * 0.1
                    self.vy = tangent_vy * 0.1
            else:
                # Обычное притяжение после орбиты
                dt = 1.0 / 60.0
                self.apply_force(moon_x, moon_y, dt)
                self.x += self.vx
                self.y += self.vy
                # Затухание
                self.vx *= 0.98
                self.vy *= 0.98

            return self.life > 0

        def draw(self, surface):
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0:
                # Если в орбите, рисуем как звезду
                if self.in_orbit:
                    points = []
                    for i in range(5):
                        angle = self.angle + i * 2 * math.pi / 5
                        px = self.x + self.size * math.cos(angle)
                        py = self.y + self.size * math.sin(angle)
                        points.append((px, py))
                        # Внутренние точки
                        inner_angle = angle + math.pi / 5
                        inner_size = self.size * 0.5
                        px = self.x + inner_size * math.cos(inner_angle)
                        py = self.y + inner_size * math.sin(inner_angle)
                        points.append((px, py))
                    if len(points) > 2:
                        pygame.draw.polygon(surface, (*self.color, alpha), points)
                else:
                    # Иначе обычный круг
                    s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*self.color, alpha // 2), (self.size, self.size), self.size)
                    pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size * 0.7)
                    surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

    class CursorTrailParticle:
        """Частица следа курсора"""

        def __init__(self, x, y, palette, rainbow_mode=False):
            self.x = float(x)
            self.y = float(y)
            self.vx = random.uniform(-0.5, 0.5)
            self.vy = random.uniform(-0.5, 0.5)
            self.palette = palette
            self.rainbow_mode = rainbow_mode
            self.life = random.randint(30, 60)  # Живут недолго
            self.max_life = self.life
            self.size = random.randint(1, 3)
            self.update_color()

        def update_color(self):
            """Обновить цвет в зависимости от режима и палитры"""
            if self.rainbow_mode:
                hue = (pygame.time.get_ticks() / 3000.0 + (self.x + self.y) / (WIDTH + HEIGHT)) % 1.0
                rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.9)
                self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            elif self.palette:
                self.color = self.palette[0]  # Берем первый цвет из палитры
            else:
                self.color = (200, 200, 255)  # Цвет по умолчанию

        def update(self, moon_x, moon_y, palette, rainbow_mode, t, moon_phase):
            """Обновление частицы следа курсора"""
            self.life -= 1
            self.update_color()
            # Легкое притяжение к луне
            dx = moon_x - self.x
            dy = moon_y - self.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 1:
                dist = math.sqrt(dist_sq)
                force = 50.0 / dist_sq * (1.0 / 60.0)  # Очень слабое притяжение
                self.vx += dx / dist * force
                self.vy += dy / dist * force
            self.x += self.vx
            self.y += self.vy
            # Затухание
            self.vx *= 0.95
            self.vy *= 0.95
            return self.life > 0

        def draw(self, surface):
            """Отрисовка частицы следа курсора"""
            alpha = int(255 * (self.life / self.max_life))
            if alpha > 0:
                s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color, alpha // 3), (self.size, self.size), self.size)  # Очень легкая аура
                pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size * 0.7)
                surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

    class Star:
        """Звезда на заднем плане"""

        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.base_brightness = random.uniform(0.1, 0.8)
            self.twinkle_speed = random.uniform(0.001, 0.01)
            self.twinkle_offset = random.uniform(0, 2 * math.pi)
            self.size = random.randint(1, 2)

        def update(self, moon_phase=0):
            # Звезды могут мерцать сильнее в зависимости от фазы
            phase_boost = moon_phase / 4.0
            self.twinkle_speed = 0.001 + (0.009 * (1 + phase_boost * 0.5))

        def draw(self, surface):
            t = pygame.time.get_ticks() * self.twinkle_speed + self.twinkle_offset
            brightness = self.base_brightness + 0.2 * math.sin(t)
            brightness = max(0, min(1, brightness))
            r = int(200 * brightness)
            g = int(200 * brightness)
            b = int(255 * brightness)
            pygame.draw.circle(surface, (r, g, b), (int(self.x), int(self.y)), self.size)

    # --- Инициализация ---
    show_instructions = True
    particles = []
    cursor_trail_particles = []  # Для следа курсора
    stars = [Star(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(100)]
    flow_rate = 10.0  # Вероятность создания частицы за кадр (медленнее для атмосферы)
    moon_x = WIDTH // 2
    moon_y = HEIGHT // 4
    rainbow_mode = False
    music_on = True  # Музыка включена по умолчанию
    # Палитра с 5 цветами для 5 фаз
    palette = [
        (150, 200, 255),  # 0: Голубая (Полная луна)
        (200, 150, 255),  # 1: Фиолетовая (Убывающая)
        (150, 255, 200),  # 2: Зелёная (Новолуние)
        (255, 200, 150),  # 3: Оранжевая (Растущая)
        (255, 150, 200)  # 4: Розовая (Полная -> Убывающая)
    ]
    current_palette_color = 0
    moon_phase = 0  # 0 - 4
    last_phase_change = 0
    font = pygame.font.SysFont("consolas", 17)
    clock = pygame.time.Clock()  # Создаем локальные часы
    last_cursor_particle_time = 0  # Для ограничения создания частиц следа
    # === Словарь переводов для подсказок ===
    translations = {
        'ru': {
            'controls': 'Управление:',
            'move_moon': 'ПКМ — Переместить луну',
            'flow': 'Пробел — Увеличить поток',
            'phase': 'C — Сменить фазу луны',
            'palette': '1-5 — Цветовые палитры',
            'rainbow': 'R — Радужный режим',
            'music': 'M — Вкл/выкл музыку',
            'trail': 'T — Режим следа',
            'hide_hud': 'TAB — Скрыть/показать подсказки',
            'esc': 'ESC — Выход',
            'modes': 'Режимы:'
        },
        'en': {
            'controls': 'Controls:',
            'move_moon': 'RMB — Move moon',
            'flow': 'SPACE — Increase flow',
            'phase': 'C — Change moon phase',
            'palette': '1-5 — Color palettes',
            'rainbow': 'R — Rainbow mode',
            'music': 'M — Toggle music',
            'trail': 'T — Trail mode',
            'hide_hud': 'TAB — Hide/Show hints',
            'esc': 'ESC — Exit',
            'modes': 'Modes:'
        }
    }
    # --- Загрузка и воспроизведение музыки ---
    try:
        # Проверяем, существует ли файл
        if os.path.exists('under the moon.mp3'):
            pygame.mixer.music.load('under the moon.mp3')
            pygame.mixer.music.play(-1)  # Воспроизводим бесконечно
        else:
            print("Файл 'under the moon.mp3' не найден.")
            music_on = False  # Отключаем музыку, если файл не найден
    except Exception as e:
        print(f"Ошибка при загрузке музыки: {e}")
        music_on = False  # Отключаем музыку при ошибке

    # --- Основной цикл ---
    running = True
    while running:
        dt = clock.tick(60) / 1000.0  # Дельта-время в секундах
        t = pygame.time.get_ticks() / 1000.0

        # --- Обработка событий ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # ПКМ
                    moon_x, moon_y = event.pos
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_SPACE:
                    flow_rate = 1000.8 if flow_rate == 10.0 else 10.0
                if event.key == pygame.K_1:
                    current_palette_color = 0
                if event.key == pygame.K_2:
                    current_palette_color = 1
                if event.key == pygame.K_3:
                    current_palette_color = 2
                if event.key == pygame.K_4:
                    current_palette_color = 3
                if event.key == pygame.K_5:  # Добавляем 5-ю палитру
                    current_palette_color = 4
                if event.key == pygame.K_r:
                    rainbow_mode = not rainbow_mode
                if event.key == pygame.K_c:
                    # Смена фазы луны по клавише C
                    moon_phase = (moon_phase + 1) % 5
                    last_phase_change = pygame.time.get_ticks()
                if event.key == pygame.K_m:
                    # Переключить музыку по клавише M
                    music_on = not music_on
                    if music_on:
                        pygame.mixer.music.unpause()  # Возобновляем, если была пауза
                    else:
                        pygame.mixer.music.pause()  # Ставим на паузу
                if event.key == pygame.K_TAB:
                    show_instructions = not show_instructions

        # --- Логика ---
        mx, my = pygame.mouse.get_pos()

        # Создание частиц ИЗ КУРСОРА
        if random.random() < flow_rate:
            # Выбираем тип частицы
            particle_type = random.choices(
                ['glow', 'spark', 'pulse', 'flare', 'orbit'],
                weights=[30, 25, 20, 10, 15]  # Вероятности
            )[0]

            # Создаем частицу нужного типа в позиции курсора
            if particle_type == 'glow':
                particles.append(GlowParticle(mx, my, [palette[current_palette_color]], rainbow_mode, moon_phase))
            elif particle_type == 'spark':
                particles.append(SparkParticle(mx, my, [palette[current_palette_color]], rainbow_mode, moon_phase))
            elif particle_type == 'pulse':
                particles.append(PulseParticle(mx, my, [palette[current_palette_color]], rainbow_mode, moon_phase))
            elif particle_type == 'flare':
                particles.append(FlareParticle(mx, my, [palette[current_palette_color]], rainbow_mode, moon_phase))
            elif particle_type == 'orbit':
                particles.append(OrbitParticle(mx, my, [palette[current_palette_color]], rainbow_mode, moon_phase))

        # Создание частиц для следа курсора (ограничиваем частоту)
        if pygame.time.get_ticks() - last_cursor_particle_time > 50:  # 20 частиц в секунду максимум
            cursor_trail_particles.append(CursorTrailParticle(mx, my, [palette[current_palette_color]], rainbow_mode))
            last_cursor_particle_time = pygame.time.get_ticks()

        # Обновление звезд
        for star in stars:
            star.update(moon_phase)

        # Обновление частиц
        particles_to_keep = []
        for p in particles:
            alive = p.update(moon_x, moon_y, [palette[current_palette_color]], rainbow_mode, t, moon_phase)
            if alive:
                particles_to_keep.append(p)
        particles = particles_to_keep

        # Обновление частиц следа курсора
        cursor_trail_to_keep = []
        for p in cursor_trail_particles:
            alive = p.update(moon_x, moon_y, [palette[current_palette_color]], rainbow_mode, t, moon_phase)
            if alive:
                cursor_trail_to_keep.append(p)
        cursor_trail_particles = cursor_trail_to_keep

        # Автоматическая смена фазы луны (каждые 15 секунд)
        if pygame.time.get_ticks() - last_phase_change > 15000:
            moon_phase = (moon_phase + 1) % 5
            last_phase_change = pygame.time.get_ticks()

        # --- Отрисовка ---
        # Фон с влиянием фазы
        phase_influence = moon_phase / 4.0  # 0.0 до 1.0
        color1 = (max(0, 5 + int(15 * phase_influence)), max(0, 10 - int(5 * phase_influence)),
                  max(10, 20 + int(20 * phase_influence)))
        color2 = (max(0, 10 + int(20 * phase_influence)), max(0, 5 + int(10 * phase_influence)),
                  max(10, 20 + int(15 * (1 - phase_influence))))
        draw_gradient_background(color1, color2, moon_x, moon_y, phase_influence)

        # Звезды
        for star in stars:
            star.draw(screen)

        # Луна с 5 фазами (исправленная отрисовка)
        moon_r = 35 + 5 * math.sin(t * 1.5)  # Медленная пульсация
        moon_surf = pygame.Surface((int(moon_r * 4), int(moon_r * 4)), pygame.SRCALPHA)

        # Аура луны, зависящая от фазы
        aura_intensity = 0.5 + (moon_phase / 4.0) * 0.5  # От 0.5 до 1.0
        for i in range(5):
            aura_r = moon_r + i * 5
            aura_alpha = int(80 * (1 - i * 0.2) * aura_intensity)
            pygame.draw.circle(moon_surf, (200, 200, 255, aura_alpha), (int(moon_r * 2), int(moon_r * 2)), int(aura_r))

        # Сама луна с фазами
        base_color = palette[moon_phase]  # Цвет луны зависит от фазы
        moon_alpha = 220

        if moon_phase == 0:  # Полная луна
            pygame.draw.circle(moon_surf, (*base_color, moon_alpha), (int(moon_r * 2), int(moon_r * 2)), int(moon_r))
            # Кратеры (видны лучше на полной/почти полной луне)
            craters = [
                (int(moon_r * 2 - moon_r * 0.4), int(moon_r * 2 - moon_r * 0.3), int(moon_r * 0.2)),
                (int(moon_r * 2 + moon_r * 0.3), int(moon_r * 2), int(moon_r * 0.15)),
                (int(moon_r * 2), int(moon_r * 2 + moon_r * 0.4), int(moon_r * 0.25)),
            ]
            for cx, cy, cr in craters:
                pygame.draw.circle(moon_surf, (180, 180, 200, 100), (cx, cy), cr)
        elif moon_phase == 1:  # Убывающая (левая половина темнее)
            pygame.draw.circle(moon_surf, (*base_color, moon_alpha), (int(moon_r * 2), int(moon_r * 2)), int(moon_r))
            # Темная часть (сегмент круга)
            dark_surf = pygame.Surface((int(moon_r * 4), int(moon_r * 4)), pygame.SRCALPHA)
            pygame.draw.arc(dark_surf, (0, 0, 20, 150),
                            (0, 0, int(moon_r * 4), int(moon_r * 4)),
                            math.pi / 2, 3 * math.pi / 2, int(moon_r * 2))
            moon_surf.blit(dark_surf, (0, 0))
            # Кратеры
            craters = [
                (int(moon_r * 2 - moon_r * 0.4), int(moon_r * 2 - moon_r * 0.3), int(moon_r * 0.2)),
                (int(moon_r * 2 + moon_r * 0.3), int(moon_r * 2), int(moon_r * 0.15)),
                (int(moon_r * 2), int(moon_r * 2 + moon_r * 0.4), int(moon_r * 0.25)),
            ]
            for cx, cy, cr in craters:
                pygame.draw.circle(moon_surf, (180, 180, 200, 100), (cx, cy), cr)
        elif moon_phase == 2:  # Новолуние (очень тусклая)
            pygame.draw.circle(moon_surf, (100, 100, 120, 100), (int(moon_r * 2), int(moon_r * 2)), int(moon_r))
        elif moon_phase == 3:  # Растущая (правая половина темнее)
            pygame.draw.circle(moon_surf, (*base_color, moon_alpha), (int(moon_r * 2), int(moon_r * 2)), int(moon_r))
            # Темная часть (сегмент круга)
            dark_surf = pygame.Surface((int(moon_r * 4), int(moon_r * 4)), pygame.SRCALPHA)
            pygame.draw.arc(dark_surf, (0, 0, 20, 150),
                            (0, 0, int(moon_r * 4), int(moon_r * 4)),
                            -math.pi / 2, math.pi / 2, int(moon_r * 2))
            moon_surf.blit(dark_surf, (0, 0))
            # Кратеры
            craters = [
                (int(moon_r * 2 - moon_r * 0.4), int(moon_r * 2 - moon_r * 0.3), int(moon_r * 0.2)),
                (int(moon_r * 2 + moon_r * 0.3), int(moon_r * 2), int(moon_r * 0.15)),
                (int(moon_r * 2), int(moon_r * 2 + moon_r * 0.4), int(moon_r * 0.25)),
            ]
            for cx, cy, cr in craters:
                pygame.draw.circle(moon_surf, (180, 180, 200, 100), (cx, cy), cr)
        else:  # Полная (эквивалент фазы 4, но с другим цветом)
            pygame.draw.circle(moon_surf, (*base_color, moon_alpha), (int(moon_r * 2), int(moon_r * 2)), int(moon_r))
            # Кратеры
            craters = [
                (int(moon_r * 2 - moon_r * 0.4), int(moon_r * 2 - moon_r * 0.3), int(moon_r * 0.2)),
                (int(moon_r * 2 + moon_r * 0.3), int(moon_r * 2), int(moon_r * 0.15)),
                (int(moon_r * 2), int(moon_r * 2 + moon_r * 0.4), int(moon_r * 0.25)),
            ]
            for cx, cy, cr in craters:
                pygame.draw.circle(moon_surf, (180, 180, 200, 100), (cx, cy), cr)

        screen.blit(moon_surf, (int(moon_x - moon_r * 2), int(moon_y - moon_r * 2)))

        # Волны вокруг луны, зависящие от фазы
        wave_intensity = 0.7 + (moon_phase / 4.0) * 0.3
        wave_t = t * 3 * wave_intensity
        for i in range(4):
            wave_r = moon_r + 15 + 7 * math.sin(wave_t + i * 1.5)
            wave_alpha = int(40 * (1 - i * 0.25) * wave_intensity)
            pygame.draw.circle(screen, (180, 180, 255, wave_alpha), (int(moon_x), int(moon_y)), int(wave_r), 2)

        # Частицы
        for p in particles:
            p.draw(screen)

        # Частицы следа курсора
        for p in cursor_trail_particles:
            p.draw(screen)

        # --- Нарисовать курсор ---
        # Создаем поверхность для курсора
        cursor_size = 20
        cursor_surf = pygame.Surface((cursor_size * 2, cursor_size * 2), pygame.SRCALPHA)

        # Основной круг курсора
        pygame.draw.circle(cursor_surf, (200, 200, 255, 200), (cursor_size, cursor_size), cursor_size)
        pygame.draw.circle(cursor_surf, (255, 255, 255, 255), (cursor_size, cursor_size), cursor_size - 2)

        # Внутренний круг
        pygame.draw.circle(cursor_surf, (150, 150, 255, 150), (cursor_size, cursor_size), cursor_size // 2)

        # Крест в центре
        pygame.draw.line(cursor_surf, (255, 255, 255, 200),
                         (cursor_size - cursor_size // 3, cursor_size),
                         (cursor_size + cursor_size // 3, cursor_size), 2)
        pygame.draw.line(cursor_surf, (255, 255, 255, 200),
                         (cursor_size, cursor_size - cursor_size // 3),
                         (cursor_size, cursor_size + cursor_size // 3), 2)

        # Рисуем курсор на экране
        screen.blit(cursor_surf, (int(mx - cursor_size), int(my - cursor_size)))

        # --- HUD ---
        # === Красивые подсказки как в cosmic_storm ===
        # === Красивые подсказки как в cosmic_storm ===
        if show_instructions:
            y_offset = 10

            def draw_text(text, color=(130, 180, 255)):
                nonlocal y_offset
                txt = font.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 22

            trans = translations[language]

            # Управление
            draw_text(trans['controls'], (100, 200, 255))
            draw_text(trans['move_moon'])
            draw_text(trans['flow'])

            draw_text("")
            draw_text(trans['modes'], (100, 200, 255))
            draw_text(f"{trans['phase']} ({moon_phase + 1}/5)", (100, 78, 200))
            draw_text(f"{trans['palette']}", (200, 200, 100))
            draw_text(f"{trans['rainbow']} {'[ON]' if rainbow_mode else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['music']} {'[ON]' if music_on else '[OFF]'}", (100, 20, 100))

            draw_text("")
            draw_text(trans['esc'])
            draw_text(trans['hide_hud'])

        pygame.display.flip()

    # --- Очистка ---
    particles.clear()
    cursor_trail_particles.clear()
    stars.clear()
    # Останавливаем музыку при выходе
    pygame.mixer.music.stop()
class Comet:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = -50
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(2, 5)
        self.size = random.randint(10, 20)
        self.color = (255, random.randint(100, 200), 0)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y > HEIGHT:
            burst((self.x, self.y), amount=50)
            return False
        return True

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)
class Particle:
    def __init__(self, pos, color_set):
        self.x, self.y = pos
        angle = random.uniform(math.pi, 2 * math.pi)
        speed = random.uniform(1, 3) * (2 if chaos_mode else 1)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2
        self.life = random.randint(30, 60)
        self.size = random.randint(4, 10)
        if chaos_mode:
            self.color = [random.randint(0, 255) for _ in range(3)]
        else:
            self.color = random.choice(color_set)

    def update(self):
        if gravity_enabled:
            self.vy += 0.1
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(1, self.size - 0.15)
        if chaos_mode:
            self.color = [random.randint(0, 255) for _ in range(3)]
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (self.life / 60))))
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(surf, (self.x - self.size, self.y - self.size))
class Spark:
    def __init__(self, pos, color):
        self.x, self.y = pos
        angle = random.uniform(-math.pi / 4, math.pi / 4)
        speed = random.uniform(3, 6)
        self.vx = math.cos(angle) * speed
        self.vy = -abs(math.sin(angle) * speed) - 3
        self.life = random.randint(20, 40)
        self.size = random.randint(2, 4)
        self.color = color

    def update(self):
        if gravity_enabled:
            self.vy += 0.1
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (self.life / 40))))
        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.size // 2, self.size // 2), self.size // 2)
        surface.blit(surf, (self.x, self.y))
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.size = random.randint(6, 12)
        self.color = (255, 255, random.randint(200, 255))
        self.angle = 0
        self.blink = 255

    def draw(self, surface):
        self.angle += 0.01
        if chaos_mode:
            self.blink = random.randint(50, 255)
        points = []
        for i in range(5):
            outer = (self.x + math.cos(self.angle + i * 2 * math.pi / 5) * self.size,
                     self.y + math.sin(self.angle + i * 2 * math.pi / 5) * self.size)
            inner = (self.x + math.cos(self.angle + i * 2 * math.pi / 5 + math.pi / 5) * self.size / 2,
                     self.y + math.sin(self.angle + i * 2 * math.pi / 5 + math.pi / 5) * self.size / 2)
            points.extend([outer, inner])
        color = (*self.color[:2], self.blink) if chaos_mode else self.color
        pygame.draw.polygon(surface, color, points)
stars = [Star() for _ in range(25)]
particles = []
sparks = []
def run_fragments_mode():
    class DustParticle:
        def __init__(self, x, y, color, size=2, life=80):
            self.pos = [x, y]
            self.vel = [random.uniform(-1.5, 1.5), random.uniform(-2, -0.5)]
            self.size = size
            self.life = life
            self.alpha = 120
            self.color = color

        def update(self, push_force=None, pulse_wave=None):
            self.vel[1] += 0.25
            if push_force and isinstance(push_force, tuple) and isinstance(push_force[0], pygame.Vector2):
                direction = push_force[0] - pygame.Vector2(self.pos[0], self.pos[1])
                distance = direction.length()
                if distance > 10:
                    strength = push_force[1] / (distance ** 2)
                    self.vel[0] += direction.x * strength
                    self.vel[1] += direction.y * strength
            if pulse_wave:
                direction = pygame.Vector2(self.pos[0], self.pos[1]) - pulse_wave[0]
                distance = direction.length()
                if 10 < distance < pulse_wave[1]:
                    strength = 200 / (distance ** 2)
                    self.vel[0] += direction.x * strength
                    self.vel[1] += direction.y * strength
            self.pos[0] += self.vel[0]
            self.pos[1] += self.vel[1]
            if self.pos[0] < 0 or self.pos[0] > WIDTH:
                self.vel[0] *= -0.7
                self.pos[0] = max(0, min(WIDTH, self.pos[0]))
            if self.pos[1] < 0 or self.pos[1] > HEIGHT:
                self.vel[1] *= -0.7
                self.pos[1] = max(0, min(HEIGHT, self.pos[1]))
            self.life -= 3
            self.alpha = max(0, self.alpha - 4)
            self.size = max(0, self.size - 0.06)
            return []

        def draw(self, surface, dust_surf):
            if self.life > 0 and self.size > 0:
                dust_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(dust_surf, (*self.color, int(self.alpha)), (int(self.size * 1.5), int(self.size * 1.5)), int(self.size))
                surface.blit(dust_surf, (int(self.pos[0] - self.size * 1.5), int(self.pos[1] - self.size * 1.5)))

    class GlassObject:
        MAX_SHARDS = 25

        def __init__(self, x, y, is_meteor=False):
            self.x = x
            self.y = y
            self.radius = 25
            self.broken = False
            self.shards = []
            self.dust_particles = []
            self.color = random.choice([(200, 220, 255), (255, 200, 200), (200, 255, 200), (255, 255, 200)]) if not is_meteor else (150, 150, 150)
            self.secondary_color = [min(255, max(0, c + random.randint(-50, 50))) for c in self.color]
            self.burst_timer = random.randint(30, 90) if is_meteor else -1
            self.pulse_timer = 0
            self.is_meteor = is_meteor

        def break_apart(self, shard_multiplier=False):
            if self.broken:
                return self.color
            self.broken = True
            self.shards.clear()
            shard_count = self.MAX_SHARDS * 2 if shard_multiplier else self.MAX_SHARDS
            for _ in range(shard_count):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(3, 8 if shard_multiplier else 7)
                shard = {
                    "pos": [self.x, self.y],
                    "vel": [math.cos(angle) * speed, math.sin(angle) * speed - random.uniform(4, 6)],
                    "base_size": random.randint(3, 6),
                    "size": 0.5,
                    "life": 200,
                    "angle": random.uniform(0, 360),
                    "angular_velocity": random.uniform(-8, 8),
                    "shape": random.choice(["rect", "circle", "triangle"]),
                    "growth_speed": random.uniform(0.2, 0.5),
                    "sparkle": random.random() < 0.25,
                    "sparkle_brightness": 255,
                    "flicker": random.random() < 0.15,
                    "flicker_timer": random.randint(10, 30),
                    "break_boost": 20
                }
                self.shards.append(shard)

            for _ in range(15):
                dust = DustParticle(self.x, self.y, self.color, size=random.randint(2, 5), life=random.randint(60, 100))
                dust.vel = [random.uniform(-3, 3), random.uniform(-3, 3)]
                self.dust_particles.append(dust)
            return self.color

        def update(self, push_force=None, pulse_wave=None, rainbow_mode=False):
            if not self.broken:
                if self.burst_timer >= 0:
                    self.burst_timer -= 1
                    if self.burst_timer == 0 or (self.is_meteor and self.y > HEIGHT):
                        return self.break_apart()
                if self.is_meteor:
                    self.y += 5  # Падение метеорита
                self.pulse_timer += 0.1
                return None

            spark_particles = []
            for shard in self.shards:
                shard["vel"][1] += 0.25
                if push_force and isinstance(push_force, tuple) and isinstance(push_force[0], pygame.Vector2):
                    direction = push_force[0] - pygame.Vector2(shard["pos"][0], shard["pos"][1])
                    distance = direction.length()
                    if distance > 10:
                        strength = push_force[1] / (distance ** 2)
                        shard["vel"][0] += direction.x * strength
                        shard["vel"][1] += direction.y * strength
                if pulse_wave:
                    direction = pygame.Vector2(shard["pos"][0], shard["pos"][1]) - pulse_wave[0]
                    distance = direction.length()
                    if 10 < distance < pulse_wave[1]:
                        strength = 200 / (distance ** 2)
                        shard["vel"][0] += direction.x * strength
                        shard["vel"][1] += direction.y * strength
                shard["pos"][0] += shard["vel"][0]
                shard["pos"][1] += shard["vel"][1]
                bounce = False
                if shard["pos"][0] < 0 or shard["pos"][0] > WIDTH:
                    shard["vel"][0] *= -0.7
                    shard["pos"][0] = max(0, min(WIDTH, shard["pos"][0]))
                    bounce = True
                if shard["pos"][1] < 0 or shard["pos"][1] > HEIGHT:
                    shard["vel"][1] *= -0.7
                    shard["pos"][1] = max(0, min(HEIGHT, shard["pos"][1]))
                    bounce = True
                shard["life"] -= 5
                shard["angle"] = (shard["angle"] + shard["angular_velocity"]) % 360
                if shard["sparkle"]:
                    shard["sparkle_brightness"] = random.randint(200, 255)
                if shard["flicker"]:
                    shard["flicker_timer"] -= 1
                    if shard["flicker_timer"] <= 0:
                        shard["flicker"] = False
                if shard["break_boost"] > 0:
                    shard["break_boost"] -= 2
                    shard["size"] = min(shard["base_size"] * 1.2, shard["size"] + 0.3)
                elif shard["size"] < shard["base_size"]:
                    shard["size"] = min(shard["base_size"], shard["size"] + shard["growth_speed"])
                else:
                    shard["size"] = max(0, shard["size"] - 0.08)
                if bounce:
                    for _ in range(2):
                        spark = DustParticle(shard["pos"][0], shard["pos"][1], self.color, size=1, life=random.randint(15, 30))
                        spark.vel = [random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5)]
                        spark_particles.append(spark)

            self.shards = [s for s in self.shards if s["life"] > 0 and s["size"] > 0]
            for dust in self.dust_particles:
                spark_particles.extend(dust.update(push_force, pulse_wave))
            self.dust_particles = [d for d in self.dust_particles if d.life > 0 and d.size > 0]
            self.dust_particles.extend(spark_particles)
            return None

        def draw_shard(self, surface, shard_surf, rainbow_mode=False, time=None):
            for shard in self.shards:
                alpha = max(0, int(shard["life"]))
                size = max(1, int(shard["size"]))
                t = shard["life"] / 200.0
                if rainbow_mode and time is not None:
                    hue = (time * 0.1 + shard["pos"][0] / WIDTH) % 1.0
                    base_color = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, 1.0)]
                else:
                    base_color = [
                        int(self.color[i] * t + self.secondary_color[i] * (1 - t))
                        for i in range(3)
                    ]
                if shard["sparkle"]:
                    base_color = [min(255, max(0, c + (shard["sparkle_brightness"] - 255))) for c in base_color]
                if shard["flicker"]:
                    base_color = [min(255, c + 50) for c in base_color]
                if shard["break_boost"] > 0:
                    base_color = [min(255, c + shard["break_boost"] * 2) for c in base_color]
                blue_shift = int((200 - alpha) * 0.5)
                color = (
                    max(0, base_color[0] - blue_shift // 2),
                    max(0, base_color[1] - blue_shift // 3),
                    min(255, base_color[2] + blue_shift),
                    alpha
                )

                shard_surf.fill((0, 0, 0, 0))
                cx, cy = 25, 25
                glow_color = (*color[:3], int(alpha * 0.15))
                pygame.draw.circle(shard_surf, glow_color, (cx, cy), int(size * 1.5))
                if shard["shape"] == "rect":
                    pygame.draw.rect(shard_surf, color, (cx - size // 2, cy - size // 2, size, size))
                elif shard["shape"] == "circle":
                    pygame.draw.circle(shard_surf, color, (cx, cy), size // 2)
                elif shard["shape"] == "triangle":
                    points = [
                        (cx, cy - size // 2),
                        (cx - size // 2, cy + size // 2),
                        (cx + size // 2, cy + size // 2),
                    ]
                    pygame.draw.polygon(shard_surf, color, points)

                rotated = pygame.transform.rotate(shard_surf, shard["angle"])
                rect = rotated.get_rect(center=(int(shard["pos"][0]), int(shard["pos"][1])))
                surface.blit(rotated, rect.topleft)

        def draw(self, surface, shard_surf, dust_surf, rainbow_mode=False, time=None):
            if not self.broken:
                pulse_size = self.radius * (1 + 0.1 * math.sin(self.pulse_timer))
                if rainbow_mode and time is not None:
                    hue = (time * 0.1 + self.x / WIDTH) % 1.0
                    color = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, 1.0)]
                else:
                    color = self.color
                glow = pygame.Surface((pulse_size * 4, pulse_size * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color[:3], 40), (glow.get_width() // 2, glow.get_height() // 2), pulse_size * 2)
                surface.blit(glow, (int(self.x - glow.get_width() / 2), int(self.y - glow.get_height() / 2)), special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(pulse_size))
            else:
                self.draw_shard(surface, shard_surf, rainbow_mode, time)
                for dust in self.dust_particles:
                    if rainbow_mode and time is not None:
                        hue = (time * 0.1 + dust.pos[0] / WIDTH) % 1.0
                        dust.color = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, 1.0)]
                    dust.draw(surface, dust_surf)

    def create_custom_cursor(push_active=False, multiplier_active=False):
        r = 8 if not push_active else 12
        color = (255, 200, 200) if multiplier_active else (220, 255, 255)
        surf = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*color[:3], 150), (r * 2, r * 2), r * 2)
        pygame.draw.circle(surf, color, (r * 2, r * 2), r)
        return surf

    def distance_sq(x1, y1, x2, y2):
        return (x1 - x2)**2 + (y1 - y2)**2

    def draw_background(surface, pulse_color, pulse_alpha):
        if pulse_alpha > 0:
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((*pulse_color, pulse_alpha))
            surface.blit(flash_surface, (0, 0))
        surface.fill((10, 10, 20))


    # === Словарь переводов для подсказок ===
    translations = {
        'ru': {
            'controls': 'Управление:',
            'click': 'Клик — Разрушить объект',
            'push': 'P — Толчок',
            'burst': 'B — Режим взрыва',
            'multiply': 'M — Умножить осколки',
            'pulse': 'G — Волна разлета',
            'rainbow': 'R — Радужный режим',
            'meteor': 'T — Метеоритный дождь',
            'add': 'N — Добавить объект',
            'hide_hud': 'TAB — Скрыть/показать подсказки',
            'esc': 'ESC — Назад',
            'modes': 'Режимы:'
        },
        'en': {
            'controls': 'Controls:',
            'click': 'Click — Break object',
            'push': 'P — Push',
            'burst': 'B — Burst mode',
            'multiply': 'M — Multiply shards',
            'pulse': 'G — Pulse wave',
            'rainbow': 'R — Rainbow mode',
            'meteor': 'T — Meteor shower',
            'add': 'N — Add object',
            'hide_hud': 'TAB — Hide/Show hints',
            'esc': 'ESC — Back',
            'modes': 'Modes:'
        }
    }
    def draw_tip(surface, font, WIDTH, HEIGHT, show_instructions):
        # В начале основного цикла
        if show_instructions:
            y_offset = 10
            font = pygame.font.SysFont("consolas", 17)

            def draw_text(text, color=(130, 180, 255)):
                nonlocal y_offset
                txt = font.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 22

            trans = translations[language]  # Используем текущий язык

            # Управление
            # Управление
            draw_text(trans['controls'], (100, 200, 255))
            draw_text(trans['click'])
            draw_text(trans['push'])
            draw_text(trans['add'])

            draw_text("")
            draw_text(trans['modes'], (100, 200, 255))
            draw_text(f"{trans['multiply']} {'[ON]' if shard_multiplier else '[OFF]'}", (200, 200, 100))
            draw_text(f"{trans['pulse']} {'[ON]' if pulse_wave_mode else '[OFF]'}", (100, 180, 255))
            draw_text(f"{trans['rainbow']} {'[ON]' if rainbow_mode else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['meteor']} {'[ON]' if meteor_shower else '[OFF]'}", (150, 100, 255))

            draw_text("")
            draw_text(trans['esc'])
            draw_text(trans['hide_hud'])

    def handle_events(objects, WIDTH, HEIGHT, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower):
        push_force = None
        break_color = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True, None, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower, None
                elif event.key == pygame.K_n:
                    obj = GlassObject(random.randint(100, WIDTH - 100), random.randint(100, HEIGHT - 100))
                    if burst_mode:
                        obj.burst_timer = random.randint(30, 90)
                    objects.append(obj)
                elif event.key == pygame.K_TAB:
                    show_instructions = not show_instructions
                elif event.key == pygame.K_p:
                    mx, my = pygame.mouse.get_pos()
                    push_force = (pygame.Vector2(mx, my), 800)
                    break_color = (180, 180, 180)
                    for obj in objects:
                        if not obj.broken:
                            obj.break_apart(shard_multiplier)
                elif event.key == pygame.K_b:
                    return False, None, not burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower, None
                elif event.key == pygame.K_g:
                    return False, None, burst_mode, not pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower, None
                elif event.key == pygame.K_m:
                    return False, None, burst_mode, pulse_wave_mode, not shard_multiplier, show_instructions, rainbow_mode, meteor_shower, None
                elif event.key == pygame.K_r:
                    return False, None, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, not rainbow_mode, meteor_shower, None
                elif event.key == pygame.K_t:
                    return False, None, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, not meteor_shower, None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                for obj in objects:
                    if not obj.broken and distance_sq(mx, my, obj.x, obj.y) <= obj.radius ** 2:
                        break_color = obj.break_apart(shard_multiplier)
                        break
        return False, push_force, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower, break_color

    show_instructions = True
    pygame.mouse.set_visible(False)
    objects = [GlassObject(WIDTH // 2, HEIGHT // 2)]
    pulse_color = (10, 10, 20)
    pulse_alpha = 0
    burst_mode = False
    pulse_wave_mode = False
    shard_multiplier = False
    push_active = False
    rainbow_mode = False
    meteor_shower = False
    cursor_trail = []
    shard_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
    dust_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    wave_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
    wave_radius = 0
    meteor_timer = 0

    while True:
        current_time = pygame.time.get_ticks()
        exit_flag, push_force, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower, break_color = handle_events(objects, WIDTH, HEIGHT, burst_mode, pulse_wave_mode, shard_multiplier, show_instructions, rainbow_mode, meteor_shower)
        if exit_flag:
            break
        if push_force:
            push_active = True
            pulse_alpha = 60
            pulse_color = (180, 180, 180)
        else:
            push_active = False
        if break_color:
            pulse_color = break_color
            pulse_alpha = 50

        cursor_surf = create_custom_cursor(push_active, shard_multiplier)
        mx, my = pygame.mouse.get_pos()
        if pulse_wave_mode:
            wave_radius = (wave_radius + 2) % 100
            wave_center = pygame.Vector2(mx, my)
        else:
            wave_radius = 0

        if random.random() < 0.3:
            trail = DustParticle(mx, my, (180, 220, 255), size=2, life=30)
            trail.vel = [0, 0]
            cursor_trail.append(trail)
        cursor_trail = [t for t in cursor_trail if t.life > 0]

        if meteor_shower and current_time - meteor_timer > 500:  # Метеорит каждые 500 мс
            x = random.randint(0, WIDTH)
            meteor = GlassObject(x, -50, is_meteor=True)
            objects.append(meteor)
            meteor_timer = current_time

        for obj in objects[:]:
            color = obj.update(push_force, (wave_center, wave_radius) if pulse_wave_mode else None, rainbow_mode)
            if color:
                pulse_color = color
                pulse_alpha = 50
            if obj.broken and not obj.shards and not obj.dust_particles:
                objects.remove(obj)

        pulse_alpha = max(0, pulse_alpha - 3)
        draw_background(screen, pulse_color, pulse_alpha)

        if pulse_wave_mode and wave_radius > 0:
            wave_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(wave_surf, (150, 200, 255, 50), (100, 100), wave_radius)
            screen.blit(wave_surf, (mx - 100, my - 100))

        for obj in objects:
            obj.draw(screen, shard_surf, dust_surf, rainbow_mode, current_time / 1000)
        for trail in cursor_trail:
            trail.life -= 5
            trail.draw(screen, dust_surf)

        screen.blit(cursor_surf, (mx - cursor_surf.get_width() // 2, my - cursor_surf.get_height() // 2))
        draw_tip(screen, font, WIDTH, HEIGHT, show_instructions)

        pygame.display.flip()
        clock.tick(60)
def draw_gradient_backgrounddd():
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = (
            int(NIGHT_BLUE[0] * (1 - ratio) + BLACK[0] * ratio),
            int(NIGHT_BLUE[1] * (1 - ratio) + BLACK[1] * ratio),
            int(NIGHT_BLUE[2] * (1 - ratio) + BLACK[2] * ratio)
        )
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))
    for star in stars:
        pygame.draw.circle(screen, STAR_COLOR, star, random.randint(1, 2))
    if cluster_mode:
        for cluster in clusters:
            surface = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*CLUSTER_COLOR, 50), (10, 10), 10)
            screen.blit(surface, (int(cluster[0] - 10), int(cluster[1] - 10)), special_flags=pygame.BLEND_RGBA_ADD)
def run_skyburst_mode():
    class Particle:
        def __init__(self, x, y, angle, speed, color, rainbow=False, sparkle=False, fade_color=None, fizzle=False, trail=False, pulse=False, pulse_color=None):
            self.pos = pygame.Vector2(x, y)
            self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            self.life = 255
            self.color = color
            self.base_size = random.randint(1, 3) if sparkle else random.randint(2, 4)
            self.size = self.base_size
            self.rainbow = rainbow
            self.hue = random.randint(0, 360) if rainbow else None
            self.sparkle = sparkle
            self.brightness = random.randint(200, 255) if sparkle else 255
            self.fade_color = fade_color if fade_color is not None else color
            self.fizzle = fizzle
            self.fizzle_timer = random.randint(20, 100) if fizzle else -1
            self.trail = trail
            self.trail_particles = [] if trail else None
            self.pulse = pulse
            self.pulse_timer = 0
            self.pulse_color = pulse_color
            self.size_timer = 0

        def update(self, wind=(0, 0), gravity_wells=None):
            self.pos += self.vel
            self.vel *= 0.98
            self.vel += wind
            self.vel.y += 0.05
            if gravity_wells:
                for well in gravity_wells:
                    direction = well - self.pos
                    distance = direction.length()
                    if distance > 10:
                        strength = 100 / (distance ** 2)
                        self.vel += direction.normalize() * strength
            self.life -= 3
            self.size_timer += 0.1
            self.size = self.base_size * (1 + 0.2 * math.sin(self.size_timer))
            if self.sparkle:
                self.brightness = random.randint(180, 255)
                self.color = (min(self.color[0] * self.brightness // 255, 255),
                              min(self.color[1] * self.brightness // 255, 255),
                              min(self.color[2] * self.brightness // 255, 255))
            if self.rainbow:
                self.hue = (self.hue + 2) % 360
                r, g, b = colorsys.hsv_to_rgb(self.hue / 360.0, 1, 1)
                self.color = (int(r * 255), int(g * 255), int(b * 255))
            elif self.pulse and self.pulse_color:
                t = (math.sin(self.pulse_timer) + 1) / 2
                self.color = (int(self.color[0] * (1 - t) + self.pulse_color[0] * t),
                              int(self.color[1] * (1 - t) + self.pulse_color[1] * t),
                              int(self.color[2] * (1 - t) + self.pulse_color[2] * t))
                self.pulse_timer += 0.1
            elif self.fade_color != self.color:
                t = self.life / 255.0
                self.color = (int(self.color[0] * t + self.fade_color[0] * (1 - t)),
                              int(self.color[1] * t + self.fade_color[1] * (1 - t)),
                              int(self.color[2] * t + self.fade_color[2] * (1 - t)))
            if self.trail and random.random() < 0.5:
                self.trail_particles.append(Particle(self.pos.x, self.pos.y, 0, 0, self.color, False, False, None, False, False))
                self.trail_particles[-1].life = random.randint(50, 100)
                self.trail_particles[-1].size = 1
            if self.fizzle and self.fizzle_timer > 0:
                self.fizzle_timer -= 1
                if self.fizzle_timer == 0:
                    return [Particle(self.pos.x, self.pos.y, random.uniform(0, 2 * math.pi), random.uniform(1, 3), self.color, self.rainbow, fade_color=self.fade_color, pulse=self.pulse, pulse_color=self.pulse_color) for _ in range(5)]
            return []

        def draw(self, surface):
            if self.life > 0:
                alpha = max(0, min(255, self.life))
                surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*self.color, alpha), (self.size, self.size), self.size)
                surface.blit(surf, (self.pos.x - self.size, self.pos.y - self.size))
            if self.trail:
                for tp in self.trail_particles:
                    tp.life -= 5
                    if tp.life > 0:
                        alpha = max(0, min(255, tp.life))
                        surf = pygame.Surface((2, 2), pygame.SRCALPHA)
                        pygame.draw.circle(surf, (*tp.color, alpha // 2), (1, 1), 1)
                        surface.blit(surf, (tp.pos.x - 1, tp.pos.y - 1))

    class Firework:
        def __init__(self, start_x, start_y, target_x, target_y, color, rainbow=False, pulse=False):
            self.pos = pygame.Vector2(start_x, start_y)
            direction = pygame.Vector2(target_x - start_x, target_y - start_y)
            distance = direction.length()
            if distance > 0:
                direction = direction / distance
            self.vel = direction * 10
            self.color = color
            self.rainbow = rainbow
            self.target = pygame.Vector2(target_x, target_y)
            self.size = 5
            self.trail = []
            self.sparkle_timer = 0
            self.pulse_timer = 0
            self.pulse = pulse
            self.pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
            self.launch_sparks = [Particle(start_x, start_y, random.uniform(0, 2 * math.pi), random.uniform(2, 5), color, rainbow, sparkle=True, pulse=pulse, pulse_color=self.pulse_color) for _ in range(10)]

        def update(self, particles, wind=(0, 0), gravity_wells=None):
            self.pos += self.vel
            self.trail.append(Particle(self.pos.x, self.pos.y, random.uniform(0, 2 * math.pi), random.uniform(1, 3), self.color, self.rainbow, fade_color=self.color, trail=random.random() < 0.3, pulse=self.pulse, pulse_color=self.pulse_color))
            self.sparkle_timer += 1
            if self.sparkle_timer >= 5:
                self.trail.append(Particle(self.pos.x, self.pos.y, random.uniform(0, 2 * math.pi), random.uniform(0.5, 2), self.color, self.rainbow, sparkle=True, pulse=self.pulse, pulse_color=self.pulse_color))
                self.sparkle_timer = 0
            particles.extend(self.trail[-15:])
            for spark in self.launch_sparks:
                spark.update(wind, gravity_wells)
                particles.append(spark)
            self.launch_sparks = [s for s in self.launch_sparks if s.life > 0]
            self.pulse_timer += 0.1
            self.size = 5 + math.sin(self.pulse_timer) * 1.5
            if self.pos.distance_to(self.target) < 10:
                return True, self.color
            return False, None

        def draw(self, surface):
            if self.pulse and self.pulse_color:
                t = (math.sin(self.pulse_timer) + 1) / 2
                color = (int(self.color[0] * (1 - t) + self.pulse_color[0] * t),
                         int(self.color[1] * (1 - t) + self.pulse_color[1] * t),
                         int(self.color[2] * (1 - t) + self.pulse_color[2] * t))
            else:
                color = self.color
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (self.size, self.size), self.size)
            surface.blit(surf, (self.pos.x - self.size, self.pos.y - self.size))
            for particle in self.trail + self.launch_sparks:
                particle.draw(surface)

    def hsv_to_rgb(h, s, v):
        return colorsys.hsv_to_rgb(h, s, v)

    def explode_wave(x, y, color, rainbow=False, amount=1, pulse=False):
        particle_count = random.randint(40, 60) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        return [Particle(x, y, angle, random.uniform(2, 6), color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color)
                for _ in range(particle_count)
                for angle in [random.uniform(0, 2 * math.pi)]]

    def explode_ring(x, y, color, rainbow=False, amount=1, pulse=False):
        particle_count = random.randint(40, 60) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        return [Particle(x, y, angle, random.uniform(3, 5), color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color)
                for _ in range(particle_count)
                for angle in [random.uniform(0, 2 * math.pi)]]

    def explode_star(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(3, 7) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            for i in range(5):
                angle = math.radians(i * 72) + random.uniform(-0.3, 0.3)
                for j in range(5):
                    a = angle + j * 0.08
                    particles.append(Particle(x, y, a, 3 + j * random.uniform(0.4, 0.6), color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_spiral(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(30, 50) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            for i in range(3):
                spiral_angle = angle + i * 0.2
                particles.append(Particle(x, y, spiral_angle, speed + i * 0.5, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_heart(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(20, 40) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            t = random.uniform(0, 2 * math.pi)
            x_offset = 16 * math.sin(t) ** 3
            y_offset = -13 * math.cos(t) + 5 * math.cos(2 * t) + 2 * math.cos(3 * t) + math.cos(4 * t)
            speed = random.uniform(2, 4)
            angle = math.atan2(y_offset, x_offset) + random.uniform(-0.2, 0.2)
            particles.append(Particle(x + x_offset, y + y_offset, angle, speed, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_gradient(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(30, 50) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            hue = random.randint(0, 360) / 360.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
            start_color = (int(r * 255), int(g * 255), int(b * 255))
            next_hue = (hue + 0.2) % 1.0
            r, g, b = colorsys.hsv_to_rgb(next_hue, 1, 1)
            end_color = (int(r * 255), int(g * 255), int(b * 255))
            particles.append(Particle(x, y, angle, speed, start_color, rainbow, fade_color=end_color, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_ultra_chaos(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(50, 100) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            style = random.choice(["wave", "ring", "star", "spiral", "heart"])
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 7)
            if style == "wave":
                particles.append(Particle(x, y, angle, speed, color, rainbow, fizzle=random.random() < 0.3, sparkle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            elif style == "ring":
                particles.append(Particle(x, y, angle, random.uniform(3, 5), color, rainbow, fizzle=random.random() < 0.3, sparkle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            elif style == "star":
                angle = math.radians(random.randint(0, 4) * 72) + random.uniform(-0.3, 0.3)
                particles.append(Particle(x, y, angle, speed, color, rainbow, fizzle=random.random() < 0.3, sparkle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            elif style == "spiral":
                spiral_angle = angle + random.uniform(0, 0.2)
                particles.append(Particle(x, y, spiral_angle, speed + random.uniform(0, 0.5), color, rainbow, fizzle=random.random() < 0.3, sparkle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            elif style == "heart":
                t = random.uniform(0, 2 * math.pi)
                x_offset = 16 * math.sin(t) ** 3
                y_offset = -13 * math.cos(t) + 5 * math.cos(2 * t) + 2 * math.cos(3 * t) + math.cos(4 * t)
                angle = math.atan2(y_offset, x_offset) + random.uniform(-0.2, 0.2)
                particles.append(Particle(x + x_offset, y + y_offset, angle, speed, color, rainbow, fizzle=random.random() < 0.3, sparkle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        for _ in range(particle_count // 2):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            hue = random.randint(0, 360) / 360.0
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 1)
            start_color = (int(r * 255), int(g * 255), int(b * 255))
            next_hue = (hue + 0.2) % 1.0
            r, g, b = colorsys.hsv_to_rgb(next_hue, 1, 1)
            end_color = (int(r * 255), int(g * 255), int(b * 255))
            particles.append(Particle(x, y, angle, speed, start_color, rainbow, fade_color=end_color, fizzle=random.random() < 0.3, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_smiley(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(20, 40) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            t = random.uniform(0, 2 * math.pi)
            r = 10
            if random.random() < 0.3:
                eye_x = x + r * math.cos(t) * 0.5 * (1 if random.random() < 0.5 else -1)
                eye_y = y - r * 0.5
                speed = random.uniform(1, 3)
                angle = random.uniform(0, 2 * math.pi)
                particles.append(Particle(eye_x, eye_y, angle, speed, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            elif random.random() < 0.5:
                mouth_t = random.uniform(-math.pi / 2, math.pi / 2)
                mouth_x = x + r * math.cos(mouth_t) * 0.7
                mouth_y = y + r * math.sin(mouth_t) * 0.7 + 5
                speed = random.uniform(1, 3)
                angle = random.uniform(0, 2 * math.pi)
                particles.append(Particle(mouth_x, mouth_y, angle, speed, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
            else:
                x_offset = r * math.cos(t)
                y_offset = r * math.sin(t)
                speed = random.uniform(2, 4)
                angle = math.atan2(y_offset, x_offset) + random.uniform(-0.2, 0.2)
                particles.append(Particle(x + x_offset, y + y_offset, angle, speed, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def explode_fountain(x, y, color, rainbow=False, amount=1, pulse=False):
        particles = []
        particle_count = random.randint(30, 50) * amount
        pulse_color = random.choice([(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]) if pulse else None
        for _ in range(particle_count):
            angle = random.uniform(-math.pi / 6, math.pi / 6) - math.pi / 2
            speed = random.uniform(4, 8)
            particles.append(Particle(x, y, angle, speed, color, rainbow, fizzle=random.random() < 0.2, trail=random.random() < 0.3, pulse=pulse, pulse_color=pulse_color))
        return particles

    def draw_background(surface, stars, shooting_stars, flash_alpha):
        if flash_alpha > 0:
            flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, flash_alpha))
            surface.blit(flash_surface, (0, 0))
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = (int(5 * (1 - t) + 0 * t), int(5 * (1 - t) + 0 * t), int(30 * (1 - t) + 0 * t))
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))
        for star in stars:
            brightness = random.randint(180, 255) if random.random() < 0.95 else random.randint(220, 255)
            pygame.draw.circle(surface, (brightness, brightness, brightness), (int(star[0]), int(star[1])), 1)
        for star in shooting_stars:
            pygame.draw.line(surface, (255, 255, 255), (int(star[0][0]), int(star[0][1])), (int(star[1][0]), int(star[1][1])), 1)

    pygame.mouse.set_visible(False)
    cursor_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
    cursor_glow = 100
    pygame.draw.circle(cursor_surface, (255, 200, 100, cursor_glow), (16, 16), 10)
    pygame.draw.circle(cursor_surface, (255, 255, 255), (16, 16), 3)

    font = pygame.font.SysFont("consolas", 17)
    show_instruction = True  # Переключатель видимости подсказок

    particles = []
    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(150)]
    shooting_stars = []
    current_type = "wave"
    colors = [(255, 100, 100), (100, 255, 100), (100, 150, 255), (255, 255, 100)]
    color_index = 0
    rainbow_enabled = False
    fireworks = []
    explosion_types = ["wave", "ring", "star", "spiral", "heart", "gradient", "ultra_chaos", "smiley", "fountain"]
    wind_enabled = False
    wind = pygame.Vector2(0.05, 0)
    burst_mode = False
    burst_timer = 0
    gravity_wells = []
    pulse_enabled = False
    flash_alpha = 0

    while True:
        mx, my = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        cursor_glow = 100
        for firework in fireworks:
            if firework.pos.distance_to(pygame.Vector2(mx, my)) < 100:
                cursor_glow = min(255, cursor_glow + 50)
        cursor_surface.fill((0, 0, 0, 0))
        pygame.draw.circle(cursor_surface, (255, 200, 100, cursor_glow), (16, 16), 10)
        pygame.draw.circle(cursor_surface, (255, 255, 255), (16, 16), 3)

        if random.random() < 0.02:
            start_x = random.randint(0, WIDTH)
            start_y = random.randint(0, HEIGHT // 4)
            end_x = start_x + random.randint(-100, 100)
            end_y = start_y + random.randint(50, 150)
            shooting_stars.append(((start_x, start_y), (end_x, end_y), 30))
        shooting_stars = [(start, end, life - 1) for start, end, life in shooting_stars if life > 0]

        if gravity_wells:
            gravity_wells = [pygame.Vector2(mx, my)]
        flash_alpha = max(0, flash_alpha - 5)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_f:
                    many = 30 if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else 1
                    if current_type == "wave":
                        particles += explode_wave(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "ring":
                        particles += explode_ring(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "star":
                        particles += explode_star(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "spiral":
                        particles += explode_spiral(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "heart":
                        particles += explode_heart(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "gradient":
                        particles += explode_gradient(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "ultra_chaos":
                        particles += explode_ultra_chaos(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "smiley":
                        particles += explode_smiley(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                    elif current_type == "fountain":
                        particles += explode_fountain(mx, my, colors[color_index], rainbow_enabled, many, pulse_enabled)
                elif event.key == pygame.K_1:
                    current_type = "wave"
                elif event.key == pygame.K_2:
                    current_type = "ring"
                elif event.key == pygame.K_3:
                    current_type = "star"
                elif event.key == pygame.K_4:
                    current_type = "spiral"
                elif event.key == pygame.K_5:
                    current_type = "heart"
                elif event.key == pygame.K_6:
                    current_type = "gradient"
                elif event.key == pygame.K_7:
                    current_type = "ultra_chaos"
                elif event.key == pygame.K_8:
                    current_type = "smiley"
                elif event.key == pygame.K_9:
                    current_type = "fountain"
                elif event.key == pygame.K_c:
                    color_index = (color_index + 1) % len(colors)
                elif event.key == pygame.K_r:
                    rainbow_enabled = not rainbow_enabled
                elif event.key == pygame.K_w:
                    wind_enabled = not wind_enabled
                elif event.key == pygame.K_b:
                    burst_mode = not burst_mode
                elif event.key == pygame.K_g:
                    gravity_wells = [pygame.Vector2(mx, my)] if not gravity_wells else []
                elif event.key == pygame.K_p:
                    pulse_enabled = not pulse_enabled
                elif event.key == pygame.K_SPACE:
                    fireworks.append(Firework(WIDTH // 2, HEIGHT, mx, my, colors[color_index], rainbow_enabled, pulse_enabled))
                elif event.key == pygame.K_TAB:  # Переключение видимости подсказок
                    show_instruction = not show_instruction
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                random_type = random.choice(explosion_types)
                if random_type == "wave":
                    particles += explode_wave(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "ring":
                    particles += explode_ring(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "star":
                    particles += explode_star(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "spiral":
                    particles += explode_spiral(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "heart":
                    particles += explode_heart(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "gradient":
                    particles += explode_gradient(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "ultra_chaos":
                    particles += explode_ultra_chaos(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "smiley":
                    particles += explode_smiley(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)
                elif random_type == "fountain":
                    particles += explode_fountain(mx, my, colors[color_index], rainbow_enabled, pulse=pulse_enabled)

        if burst_mode:
            burst_timer += 1
            if burst_timer >= 30:
                start_x = random.randint(WIDTH // 4, 3 * WIDTH // 4)
                target_x = random.randint(0, WIDTH)
                target_y = random.randint(0, HEIGHT // 2)
                burst_color = random.choice(colors)
                fireworks.append(Firework(start_x, HEIGHT, target_x, target_y, burst_color, rainbow_enabled, pulse_enabled))
                burst_timer = 0

        new_particles = []
        fireworks_to_remove = []
        for i, firework in enumerate(fireworks):
            exploded, flash_color = firework.update(particles, wind if wind_enabled else (0, 0), gravity_wells)
            if exploded:
                if current_type == "wave":
                    new_particles += explode_wave(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "ring":
                    new_particles += explode_ring(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "star":
                    new_particles += explode_star(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "spiral":
                    new_particles += explode_spiral(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "heart":
                    new_particles += explode_heart(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "gradient":
                    new_particles += explode_gradient(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "ultra_chaos":
                    new_particles += explode_ultra_chaos(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "smiley":
                    new_particles += explode_smiley(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                elif current_type == "fountain":
                    new_particles += explode_fountain(firework.pos.x, firework.pos.y, firework.color, firework.rainbow, pulse=firework.pulse)
                flash_alpha = 50
                fireworks_to_remove.append(i)
        particles.extend(new_particles)
        for i in reversed(fireworks_to_remove):
            fireworks.pop(i)

        for p in particles:
            fizzle_particles = p.update(wind if wind_enabled else (0, 0), gravity_wells)
            particles.extend(fizzle_particles)
        particles = [p for p in particles if p.life > 0]

        draw_background(screen, stars, shooting_stars, flash_alpha)
        for p in particles:
            p.draw(screen)
        for firework in fireworks:
            firework.draw(screen)

        screen.blit(cursor_surface, (mx - 16, my - 16))
        # === HUD ===
        if show_instruction:
            y_offset = 10

            def draw_text(text, color=(130, 180, 255)):
                nonlocal y_offset
                txt = font.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 22

            # Названия цветов на русском и английском
            color_names = {
                'ru': {
                    (255, 100, 100): 'Красный',
                    (100, 255, 100): 'Зелёный',
                    (100, 150, 255): 'Голубой',
                    (255, 255, 100): 'Жёлтый'
                },
                'en': {
                    (255, 100, 100): 'Red',
                    (100, 255, 100): 'Green',
                    (100, 150, 255): 'Cyan',
                    (255, 255, 100): 'Yellow'
                }
            }

            # Словарь переводов
            trans = {
                'ru': {
                    'controls': 'Управление:',
                    'explode': 'F — Взрыв(Попробуй нажать Shift)',
                    'explode_shift': 'Shift+F — Массовый взрыв',
                    'random_click': 'ЛКМ — Случайный взрыв',
                    'firework': 'SPACE — Фейерверк',
                    'modes': 'Режимы:',
                    'type': '1-9 — Тип взрыва',
                    'color': 'C — Смена цвета',
                    'rainbow': 'R — Радужный режим',
                    'wind': 'W — Ветер',
                    'burst': 'B — Авто-режим',
                    'gravity': 'G — Гравитационная точка',
                    'pulse': 'P — Пульсация частиц',
                    'misc': 'Доп:',
                    'hide_hud': 'TAB — Скрыть/показать HUD',
                    'esc': 'ESC — Назад'
                },
                'en': {
                    'controls': 'Controls:',
                    'explode': 'F — Explode(Try pressing Shift)',
                    'explode_shift': 'Shift+F — Mass Explode',
                    'random_click': 'LMB — Random Explosion',
                    'firework': 'SPACE — Firework',
                    'modes': 'Modes:',
                    'type': '1-9 — Explosion Type',
                    'color': 'C — Change Color',
                    'rainbow': 'R — Rainbow Mode',
                    'wind': 'W — Wind',
                    'burst': 'B — Burst Mode',
                    'gravity': 'G — Gravity Well',
                    'pulse': 'P — Pulse Particles',
                    'misc': 'Misc:',
                    'hide_hud': 'TAB — Hide/Show HUD',
                    'esc': 'ESC — Back'
                }
            }[language]

            current_color = colors[color_index]
            color_name = color_names[language].get(tuple(current_color), "Unknown")

            # === Отрисовка подсказок ===
            draw_text(trans['controls'], (100, 200, 255))

            draw_text(trans['explode'])
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                draw_text(trans['explode_shift'], (255, 200, 100))
            else:
                draw_text(trans['random_click'])
            draw_text(trans['firework'])

            draw_text("")
            draw_text(trans['modes'], (100, 200, 255))

            draw_text(f"{trans['type']} ({current_type})", (100, 180, 255))
            draw_text(f"{trans['color']} ({color_name})", (200, 100, 255))
            draw_text(f"{trans['rainbow']} {'[ON]' if rainbow_enabled else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['wind']} {'[ON]' if wind_enabled else '[OFF]'}", (200, 200, 100))
            draw_text(f"{trans['burst']} {'[ON]' if burst_mode else '[OFF]'}", (150, 100, 255))
            draw_text(f"{trans['gravity']} {'[ON]' if gravity_wells else '[OFF]'}", (100, 150, 255))
            draw_text(f"{trans['pulse']} {'[ON]' if pulse_enabled else '[OFF]'}", (255, 150, 100))

            draw_text("")
            draw_text(trans['hide_hud'])
            draw_text(trans['esc'])
        pygame.display.flip()
        clock.tick(60)

def run_cosmic_storm_mode():
    # === Цвета ===
    BLACK = (0, 0, 0)
    WHITE = (200, 200, 255)
    GLOW_BLUE = (70, 100, 200)
    FLAME_PARTICLE = (255, 120, 0)
    SHOOTING_STAR_COLOR = (255, 255, 200)
    AURORA_GREEN = (100, 255, 200, 40)
    AURORA_PURPLE = (120, 100, 255, 30)

    # === Режимы ===
    modes = {
        'night': False,
        'eternal_rain': False,
        'echo': False,
        'gravity': False,
        'dream': False,
        'freeze': False,
        'portals': False,
        'show_hud': True
    }

    small_font = font = pygame.font.SysFont("consolas", 17)


    def hue_to_rgb(hue):
        h_i = int(hue * 6)
        f = hue * 6 - h_i
        p = 0
        q = 1 - f
        t = f
        if h_i == 0: return (1, t, p)
        if h_i == 1: return (q, 1, p)
        if h_i == 2: return (p, 1, t)
        if h_i == 3: return (p, q, 1)
        if h_i == 4: return (t, p, 1)
        if h_i == 5: return (1, p, q)

    # === Параллакс-звёзды ===
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
            self.glow_timer = 0
            self.color_phase = random.uniform(0, 2 * math.pi)

        def update(self, ship_dx, ship_dy):
            self.x -= ship_dx * self.speed
            self.y -= ship_dy * self.speed

            if self.x < -20: self.x += WIDTH + 40
            if self.x > WIDTH + 20: self.x -= WIDTH + 40
            if self.y < -20: self.y += HEIGHT + 40
            if self.y > HEIGHT + 20: self.y -= HEIGHT + 40

        def draw(self, surface, base_brightness=1.0):
            t = pygame.time.get_ticks() * self.twinkle_speed + self.twinkle_phase
            alpha = (math.sin(t) + 1) / 2
            brightness = base_brightness * (0.6 + 0.4 * alpha)

            if modes['dream']:
                hue = (pygame.time.get_ticks() * 0.0001 + self.color_phase) % 1.0
                r, g, b = hue_to_rgb(hue)
                color = (int(r * 255), int(g * 255), int(b * 255))
            else:
                r = min(255, int(WHITE[0] * brightness))
                g = min(255, int(WHITE[1] * brightness))
                b = min(255, int(WHITE[2] * brightness))
                color = (r, g, b)

            x, y = self.x, self.y
            if self.is_wobbling and not modes['freeze']:
                wobble = 1.5 * math.sin(pygame.time.get_ticks() * 0.002 + self.wobble_phase)
                x += wobble
                y -= wobble * 0.5

            pygame.draw.circle(surface, color, (int(x), int(y)), self.size)

    stars_far = [ParallaxStar(1) for _ in range(100)]
    stars_mid = [ParallaxStar(2) for _ in range(70)]
    stars_near = [ParallaxStar(3) for _ in range(50)]
    all_stars = stars_far + stars_mid + stars_near

    heartbeat_star = random.choice(all_stars)
    heartbeat_phase = 0.0

    # === Звёздная пыль ===
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

        def draw(self, surface):
            if modes['freeze']:
                color = (200, 255, 255, 100)
            else:
                color = (180, 180, 220, 100)
                if modes['dream']:
                    hue = (pygame.time.get_ticks() * 0.00005 + self.x * 0.0001) % 1.0
                    r, g, b = hue_to_rgb(hue)
                    color = (int(r * 255), int(g * 255), int(b * 255), 120)
            pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)

    dust = [DustParticle() for _ in range(100)]

    # === Падающая звезда ===
    class ShootingStar:
        def __init__(self, background=False):
            self.background = background
            if background:
                # Фоновые звезды для вечного дождя
                self.x = random.randint(0, WIDTH)
                self.y = random.randint(-100, -20)
                self.vx = random.uniform(-1, 1)
                self.vy = random.uniform(2, 6)
            else:
                side = random.choice(['left', 'top', 'right'])
                if side == 'left':
                    self.x = -20
                    self.y = random.randint(20, HEIGHT // 2)
                    self.vx = random.uniform(6, 10)
                    self.vy = random.uniform(2, 6)
                elif side == 'top':
                    self.x = random.randint(50, WIDTH - 50)
                    self.y = -20
                    self.vx = random.uniform(-2, 2)
                    self.vy = random.uniform(6, 10)
                else:
                    self.x = WIDTH + 20
                    self.y = random.randint(20, HEIGHT // 2)
                    self.vx = random.uniform(-10, -6)
                    self.vy = random.uniform(2, 6)
            self.trail = []
            self.active = True
            self.color = (200, 255, 255) if modes['dream'] else SHOOTING_STAR_COLOR

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
                alpha = int(200 * (i / len(self.trail)))
                pygame.draw.circle(surface, self.color, (int(x), int(y)), 2 + i // 4)
            if self.active:
                pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), 4)

    shooting_stars = []
    background_stars = []  # Для фоновых звезд в вечном дожде

    # === Эхо-волны ===
    class EchoWave:
        def __init__(self, x, y):
            self.x, self.y = x, y
            self.radius = 0
            self.max_radius = 80
            self.lifetime = 0
            self.max_lifetime = 45

        def update(self):
            self.lifetime += 1
            if self.lifetime < self.max_lifetime * 0.7:
                self.radius += 2.5
            else:
                self.radius -= 1
            return self.radius > 0 and self.lifetime < self.max_lifetime

        def draw(self, surface):
            if self.radius > 0:
                alpha = int(60 * (1 - self.lifetime / self.max_lifetime))
                pygame.draw.circle(surface, (100, 150, 255, alpha), (int(self.x), int(self.y)), int(self.radius), 1)

    echo_waves = []
    last_echo_time = 0

    # === Порталы ===
    class Portal:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.radius = 30
            self.rotation = 0
            self.pulse = 0
            self.active = True
            self.cooldown = 0
            self.particle_system = []  # Добавляем систему частиц

        def update(self):
            self.rotation += 0.05
            self.pulse = math.sin(pygame.time.get_ticks() * 0.003) * 5
            if self.cooldown > 0:
                self.cooldown -= 1

            # Обновляем частицы портала
            if random.random() < 0.3:
                angle = random.uniform(0, 2 * math.pi)
                distance = self.radius + random.uniform(-5, 5)
                px = self.x + distance * math.cos(angle)
                py = self.y + distance * math.sin(angle)
                self.particle_system.append({
                    'x': px, 'y': py,
                    'life': 30,
                    'vx': random.uniform(-1, 1),
                    'vy': random.uniform(-1, 1)
                })

            for particle in self.particle_system[:]:
                particle['x'] += particle['vx']
                particle['y'] += particle['vy']
                particle['life'] -= 1
                if particle['life'] <= 0:
                    self.particle_system.remove(particle)

        def draw(self, surface):
            if not self.active:
                return

            # Внешний круг
            pygame.draw.circle(surface, (100, 200, 255, 100), (int(self.x), int(self.y)),
                               int(self.radius + self.pulse), 2)

            # Внутренняя спираль
            points = []
            for i in range(20):
                angle = self.rotation + i * 0.3
                radius = (self.radius - 5) * (i / 20.0)
                x = self.x + radius * math.cos(angle)
                y = self.y + radius * math.sin(angle)
                points.append((x, y))

            if len(points) > 1:
                pygame.draw.lines(surface, (150, 100, 255, 150), False, points, 2)

            # Центральный вихрь
            center_radius = 8 + self.pulse * 0.5
            pygame.draw.circle(surface, (200, 150, 255, 200), (int(self.x), int(self.y)),
                               int(center_radius))

            # Частицы портала
            for particle in self.particle_system:
                alpha = int(150 * (particle['life'] / 30))
                pygame.draw.circle(surface, (200, 150, 255, alpha),
                                   (int(particle['x']), int(particle['y'])), 2)

        def check_collision(self, ship_x, ship_y):
            if self.cooldown > 0:
                return False
            dist = math.hypot(ship_x - self.x, ship_y - self.y)
            return dist < self.radius

        def teleport(self, portals):
            if len(portals) < 2:
                return None, None
            other_portals = [p for p in portals if p != self and p.active]
            if not other_portals:
                return None, None
            target = random.choice(other_portals)
            target.cooldown = 60
            self.cooldown = 60
            return target.x, target.y

    portals = []

    # === Улучшенное северное сияние ===
    class Aurora:
        def __init__(self):
            self.layers = []
            for i in range(5):
                self.layers.append({
                    'offset': random.uniform(0, 100),
                    'speed': random.uniform(0.2, 0.8),
                    'height': random.uniform(0.1, 0.4),
                    'color_shift': random.uniform(0, 2 * math.pi)
                })

        def draw(self, surface, ship_x, ship_y):
            time_factor = pygame.time.get_ticks() * 0.001

            # Цвета зависят от положения корабля
            ship_norm_x = ship_x / WIDTH
            ship_norm_y = ship_y / HEIGHT

            base_r = int(80 + 120 * abs(math.sin(time_factor * 0.7 + ship_norm_x * 3)))
            base_g = int(120 + 100 * abs(math.cos(time_factor * 0.5 + ship_norm_y * 2)))
            base_b = int(180 + 70 * abs(math.sin(time_factor * 0.9 + ship_norm_x * ship_norm_y)))

            aurora_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

            for layer in self.layers:
                layer_offset = layer['offset'] + time_factor * layer['speed']

                # Высота сияния зависит от положения корабля
                base_height = HEIGHT * layer['height']
                height_variation = 50 * math.sin(time_factor * 0.3 + layer['color_shift'])

                # Интенсивность зависит от расстояния до края
                dist_to_edge = min(ship_x, ship_y, WIDTH - ship_x, HEIGHT - ship_y)
                intensity = max(0.2, 1.0 - dist_to_edge / (min(WIDTH, HEIGHT) * 0.3))

                # Создаем волнообразные линии
                points = []
                for x in range(0, WIDTH + 20, 20):
                    wave = math.sin((x + layer_offset) * 0.02 + layer['color_shift']) * 30
                    y_pos = base_height + wave + height_variation
                    points.append((x, y_pos))

                # Рисуем сияние с градиентом
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]

                    # Цвет с плавными переходами
                    color_shift = math.sin(time_factor * 0.4 + i * 0.1 + layer['color_shift'])
                    r = int(base_r * (0.8 + 0.2 * color_shift))
                    g = int(base_g * (0.8 + 0.2 * color_shift))
                    b = int(base_b * (0.8 + 0.2 * color_shift))

                    alpha = int(40 * intensity * (0.7 + 0.3 * math.sin(time_factor * 0.6 + i * 0.2)))
                    pygame.draw.line(aurora_surf, (r, g, b, alpha), (x1, y1), (x2, y2), 8)

            surface.blit(aurora_surf, (0, 0))

    aurora = Aurora()

    # === Космические вихри (дополнительный эффект для гравитации) ===
    class CosmicVortex:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            self.radius = random.randint(40, 80)
            self.rotation = 0
            self.strength = random.uniform(0.5, 2.0)
            self.active = True
            self.lifetime = 300

        def update(self):
            self.rotation += 0.1 * self.strength
            self.lifetime -= 1
            return self.lifetime > 0

        def draw(self, surface):
            # Рисуем спираль
            points = []
            for i in range(30):
                angle = self.rotation + i * 0.4
                radius = self.radius * (i / 30.0)
                x = self.x + radius * math.cos(angle)
                y = self.y + radius * math.sin(angle)
                points.append((x, y))

            if len(points) > 1:
                alpha = int(80 * (self.lifetime / 300))
                pygame.draw.lines(surface, (100, 200, 255, alpha), False, points, 2)

            # Центральный вихрь
            pygame.draw.circle(surface, (50, 150, 255, 100), (int(self.x), int(self.y)), 10)

        def affect_ship(self, ship_x, ship_y, ship_vx, ship_vy):
            dist = math.hypot(ship_x - self.x, ship_y - self.y)
            if dist < self.radius:
                # Притягиваем корабль к центру
                dx = self.x - ship_x
                dy = self.y - ship_y
                pull = self.strength * (1 - dist / self.radius) * 0.05
                return ship_vx + dx * pull, ship_vy + dy * pull
            return ship_vx, ship_vy

    cosmic_vortices = []

    # === Космические облака (дополнительный эффект для режима снов) ===
    class CosmicCloud:
        def __init__(self):
            self.x = random.randint(-100, WIDTH + 100)
            self.y = random.randint(-100, HEIGHT + 100)
            self.radius = random.randint(80, 150)
            self.color = (
                random.randint(50, 150),
                random.randint(50, 150),
                random.randint(100, 200),
                random.randint(20, 50)
            )
            self.drift_x = random.uniform(-0.5, 0.5)
            self.drift_y = random.uniform(-0.5, 0.5)
            self.pulse = 0

        def update(self):
            self.x += self.drift_x
            self.y += self.drift_y
            self.pulse = math.sin(pygame.time.get_ticks() * 0.002) * 10

            # Циклическое движение
            if self.x < -200: self.x = WIDTH + 200
            if self.x > WIDTH + 200: self.x = -200
            if self.y < -200: self.y = HEIGHT + 200
            if self.y > HEIGHT + 200: self.y = -200

        def draw(self, surface):
            # Создаем градиентное облако
            cloud_surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            for i in range(5):
                radius = int((self.radius + self.pulse) * (1 - i * 0.15))
                alpha = self.color[3] - i * 8
                color = (*self.color[:3], max(0, alpha))
                pygame.draw.circle(cloud_surf, color, (self.radius, self.radius), radius)

            surface.blit(cloud_surf, (int(self.x - self.radius), int(self.y - self.radius)))

    cosmic_clouds = [CosmicCloud() for _ in range(8)]

    # === Переменные ===
    trail_positions = []
    trail_max = 200
    ship_x = WIDTH // 2
    ship_y = HEIGHT // 2
    ship_angle = 0
    ship_velocity_x = 0
    ship_velocity_y = 0
    thrust = 0.1
    friction = 0.98
    max_speed = 2.5
    stillness_timer = 0
    brightness_factor = 1.0
    breath_phase = 0.0
    gravity_flash_count = 0
    last_storm_time = 0
    last_vortex_time = 0  # Для создания вихрей

    # === Словари переводов ===
    global language, flag_is_russian
    translations = {
        'ru': {
            'controls': 'Управление:',
            'thrust': 'W / ЛКМ — ускорение',
            'direction': 'Мышь — направление',
            'modes': 'Режимы:',
            'night': 'N — Глубокая ночь',
            'eternal_rain': 'V — Вечный дождь',
            'echo': 'R — Эхо Пространства',
            'gravity': 'E — Гравитация',
            'dream': 'D — Режим Снов',
            'freeze': 'Z — Заморозка времени',
            'portals': 'P — Порталы',
            'toggle_hud': 'TAB — скрыть/показать'
        },
        'en': {
            'controls': 'Controls:',
            'thrust': 'W / LMB — Thrust',
            'direction': 'Mouse — Direction',
            'modes': 'Modes:',
            'night': 'N — Deep Night',
            'eternal_rain': 'V — Eternal Rain',
            'echo': 'R — Echo Space',
            'gravity': 'E — Gravity',
            'dream': 'D — Dream Mode',
            'freeze': 'Z — Time Freeze',
            'portals': 'P — Portals',
            'toggle_hud': 'TAB — Hide/Show HUD'
        }
    }

    # === Основной цикл ===
    running = True
    while running:
        base_dt = clock.tick(60) / 1000
        dt = base_dt * (0.5 if modes['dream'] else 1.0)
        now = pygame.time.get_ticks()

        # === События ===
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_n:
                    modes['night'] = not modes['night']
                if event.key == pygame.K_v:
                    modes['eternal_rain'] = not modes['eternal_rain']
                if event.key == pygame.K_r:
                    modes['echo'] = not modes['echo']
                if event.key == pygame.K_e:
                    modes['gravity'] = not modes['gravity']
                if event.key == pygame.K_d:
                    modes['dream'] = not modes['dream']
                    thrust = 0.05 if modes['dream'] else 0.1
                    friction = 0.99 if modes['dream'] else 0.98
                if event.key == pygame.K_z:
                    modes['freeze'] = not modes['freeze']
                if event.key == pygame.K_p:
                    modes['portals'] = not modes['portals']
                    if modes['portals']:
                        # Создаем порталы
                        portals = []
                        positions = [
                            (WIDTH * 0.2, HEIGHT * 0.3),
                            (WIDTH * 0.8, HEIGHT * 0.3),
                            (WIDTH * 0.5, HEIGHT * 0.7)
                        ]
                        for pos in positions:
                            portals.append(Portal(pos[0], pos[1]))
                if event.key == pygame.K_TAB:
                    modes['show_hud'] = not modes['show_hud']

        # === Управление ===
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - ship_x
        dy = mouse_y - ship_y
        ship_angle = math.atan2(dy, dx)

        keys = pygame.key.get_pressed()
        mouse_btn = pygame.mouse.get_pressed()[0]
        is_thrusting = keys[pygame.K_w] or mouse_btn

        speed_multiplier = 0.3 if modes['freeze'] else 1.0
        if is_thrusting:
            ship_velocity_x += thrust * math.cos(ship_angle) * speed_multiplier
            ship_velocity_y += thrust * math.sin(ship_angle) * speed_multiplier
            if modes['echo'] and now - last_echo_time > 300:
                echo_waves.append(EchoWave(ship_x, ship_y))
                last_echo_time = now
        else:
            ship_velocity_x *= friction
            ship_velocity_y *= friction

        speed = math.hypot(ship_velocity_x, ship_velocity_y)
        if speed > max_speed:
            factor = max_speed / speed
            ship_velocity_x *= factor
            ship_velocity_y *= factor

        prev_ship_x, prev_ship_y = ship_x, ship_y
        if not modes['freeze']:
            ship_x += ship_velocity_x
            ship_y += ship_velocity_y
        else:
            ship_x += ship_velocity_x * 0.3
            ship_y += ship_velocity_y * 0.3

        # Ограничиваем корабль в пределах экрана
        ship_x = max(20, min(WIDTH - 20, ship_x))
        ship_y = max(20, min(HEIGHT - 20, ship_y))

        ship_dx = ship_x - prev_ship_x
        ship_dy = ship_y - prev_ship_y

        # === Обновление ===
        for star in all_stars:
            star.update(ship_dx, ship_dy)
            if modes['gravity'] and not modes['freeze']:
                dist = math.hypot(ship_x - star.x, ship_y - star.y)
                if dist < 25 and star.glow_timer == 0:
                    star.glow_timer = 30
                    gravity_flash_count += 1

        for d in dust:
            d.update(ship_dx, ship_dy)

        if not modes['freeze']:
            if speed < 0.1:
                stillness_timer += 1
                if stillness_timer > 300:
                    brightness_factor = min(1.3, brightness_factor + 0.001)
            else:
                stillness_timer = 0
                brightness_factor = max(1.0, brightness_factor - 0.005)

        breath_phase += 0.02 * (0.5 if modes['dream'] else 1.0)

        if not modes['freeze']:
            trail_positions.append((ship_x, ship_y))
            if len(trail_positions) > trail_max:
                trail_positions.pop(0)

        # === Вечный дождь (с фоновыми звездами) ===
        if modes['eternal_rain'] and not modes['freeze']:
            # Фоновые звезды
            if now % 200 == 0:
                background_stars.append(ShootingStar(background=True))

            # Основные звезды
            if now % 800 == 0:
                shooting_stars.append(ShootingStar())

            if now - last_storm_time > 5000:
                for _ in range(random.randint(8, 15)):
                    shooting_stars.append(ShootingStar())
                last_storm_time = now

        # === Обновление звезд ===
        for star in background_stars[:]:
            star.update()
            if not star.active:
                background_stars.remove(star)

        for star in shooting_stars[:]:
            star.update()
            if not star.active:
                shooting_stars.remove(star)

        # === Обновление эхо-волн ===
        for wave in echo_waves[:]:
            if not wave.update():
                echo_waves.remove(wave)

        # === Обновление порталов ===
        if modes['portals']:
            for portal in portals:
                portal.update()

            # Проверяем столкновение с порталами
            for portal in portals[:]:
                if portal.check_collision(ship_x, ship_y):
                    new_x, new_y = portal.teleport(portals)
                    if new_x is not None and new_y is not None:
                        ship_x, ship_y = new_x, new_y
                        # Эффект телепортации
                        for _ in range(20):
                            echo_waves.append(EchoWave(ship_x, ship_y))
                        break

        # === Обновление космических вихрей (для гравитации) ===
        if modes['gravity']:
            last_vortex_time += 1
            if last_vortex_time > 200 and len(cosmic_vortices) < 3:
                cosmic_vortices.append(CosmicVortex(
                    random.randint(50, WIDTH - 50),
                    random.randint(50, HEIGHT - 50)
                ))
                last_vortex_time = 0

        for vortex in cosmic_vortices[:]:
            if not vortex.update():
                cosmic_vortices.remove(vortex)
            else:
                ship_velocity_x, ship_velocity_y = vortex.affect_ship(
                    ship_x, ship_y, ship_velocity_x, ship_velocity_y
                )

        # === Обновление космических облаков (для режима снов) ===
        if modes['dream']:
            for cloud in cosmic_clouds:
                cloud.update()

        # === Отрисовка ===
        # Ночь с улучшенным сиянием
        if modes['night']:
            screen.fill((5, 3, 20))
            aurora.draw(screen, ship_x, ship_y)
        else:
            screen.fill(BLACK)

        scale = 1.0 + 0.02 * math.sin(breath_phase) * (0.5 if modes['dream'] else 1.0)
        temp_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        temp_surf.fill((0, 0, 0, 10))

        target = temp_surf

        # === Отрисовка объектов ===

        # Космические облака (в режиме снов)
        if modes['dream']:
            for cloud in cosmic_clouds:
                cloud.draw(target)

        # Фоновые звезды (в вечном дожде)
        if modes['eternal_rain']:
            for star in background_stars:
                star.draw(target)

        # Звезды
        for s in all_stars:
            s.draw(target, brightness_factor)

        # Пыль
        for d in dust:
            d.draw(target)

        # Космические вихри (в режиме гравитации)
        if modes['gravity']:
            for vortex in cosmic_vortices:
                vortex.draw(target)

        # След корабля
        trail_color = (100, 150, 255) if modes['night'] else (200, 100, 255) if modes['dream'] else GLOW_BLUE

        for i, (x, y) in enumerate(trail_positions):
            alpha = int(150 * (i / len(trail_positions)) ** 1.5)
            pygame.draw.circle(target, (*trail_color, alpha), (int(x), int(y)), 2)

        # Корабль
        tip = (ship_x + 14 * math.cos(ship_angle), ship_y + 14 * math.sin(ship_angle))
        left = (ship_x + 10 * math.cos(ship_angle + 2.9), ship_y + 10 * math.sin(ship_angle + 2.9))
        right = (ship_x + 10 * math.cos(ship_angle - 2.9), ship_y + 10 * math.sin(ship_angle - 2.9))
        ship_color = (255, 255, 255) if modes['dream'] else (100, 140, 255)
        pygame.draw.polygon(target, ship_color, [tip, left, right])

        # Огонь
        if is_thrusting and not modes['freeze']:
            back_x = ship_x - 10 * math.cos(ship_angle)
            back_y = ship_y - 10 * math.sin(ship_angle)
            flame_color = (100, 150, 255) if modes['echo'] else (255, 180, 100) if modes['dream'] else FLAME_PARTICLE
            for i in range(3):
                offset = random.uniform(-1, 1)
                px = back_x - (i * 6 + offset) * math.cos(ship_angle)
                py = back_y - (i * 6 + offset) * math.sin(ship_angle)
                size = random.randint(2, 4)
                alpha = random.randint(150, 200)
                flame_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(flame_surf, (*flame_color, alpha), (size, size), size)
                target.blit(flame_surf, (px - size, py - size))

        # Падающие звезды
        if modes['eternal_rain']:
            for star in shooting_stars:
                star.draw(target)

        # Эхо-волны
        for wave in echo_waves:
            wave.draw(target)

        # Порталы
        if modes['portals']:
            for portal in portals:
                portal.draw(target)

        # Масштабирование
        scaled = pygame.transform.smoothscale(temp_surf, (int(WIDTH * scale), int(HEIGHT * scale)))
        x = (WIDTH - scaled.get_width()) // 2
        y = (HEIGHT - scaled.get_height()) // 2
        screen.blit(scaled, (x, y))

        # === HUD ===
        if modes['show_hud']:
            y_offset = 10

            def draw_text(text, color=(130, 180, 255)):
                nonlocal y_offset
                txt = small_font.render(text, True, color)
                screen.blit(txt, (10, y_offset))
                y_offset += 22

            # Выбираем переводы в зависимости от языка
            trans = translations[language]

            draw_text(trans['controls'], (100, 200, 255))
            draw_text(trans['thrust'])
            draw_text(trans['direction'])
            draw_text("")
            draw_text(trans['modes'], (100, 200, 255))
            draw_text(f"{trans['night']} {'[ON]' if modes['night'] else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['eternal_rain']} {'[ON]' if modes['eternal_rain'] else '[OFF]'}", (100, 200, 255))
            draw_text(f"{trans['echo']} {'[ON]' if modes['echo'] else '[OFF]'}", (100, 180, 255))
            draw_text(f"{trans['gravity']} {'[ON]' if modes['gravity'] else '[OFF]'}", (200, 100, 255))
            draw_text(f"{trans['dream']} {'[ON]' if modes['dream'] else '[OFF]'}", (100, 255, 200))
            draw_text(f"{trans['freeze']} {'[ON]' if modes['freeze'] else '[OFF]'}", (255, 200, 100))
            draw_text(f"{trans['portals']} {'[ON]' if modes['portals'] else '[OFF]'}", (150, 100, 255))
            draw_text("")
            draw_text(trans['toggle_hud'])

        pygame.display.flip()
def burst(pos, amount=60):
    for _ in range(amount):
        particles.append(Particle(pos, THEMES[theme_names[current_theme]]['colors']))
def draw_menu(surface, font):
    # === Переводы ===
    global language
    trans = {
        'ru': {
            'controls': 'Управление:',
            'tab': 'TAB — показать/скрыть',
            'b': 'B — Буря частиц',
            'f12': 'F12 — Скриншот',
            'esc': 'Esc — Выход',
            'modes': 'Режимы:',
            'space': 'Пробел — Замедление',
            't': 'T — Тема',
            's': 'S — Искры',
            'g': 'G — Гравитация',
            'x': 'X — Режим бреда',
            'z': 'Z — Звёзды',
            'l': 'L — Живые тени',
            'wheel': 'Колесо — Интенсивность'
        },
        'en': {
            'controls': 'Controls:',
            'tab': 'TAB — Show/hide hints',
            'b': 'B — Particle storm',
            'f12': 'F12 — Screenshot',
            'esc': 'Esc — Exit',
            'modes': 'Modes:',
            'space': 'Space — Slow motion',
            't': 'T — Theme',
            's': 'S — Sparks',
            'g': 'G — Gravity',
            'x': 'X — Chaos mode',
            'z': 'Z — Stars',
            'l': 'L — Life trails',
            'wheel': 'Wheel — Intensity'
        }
    }[language]

    # === Цвета для каждой строки ===
    colors = {
        'controls': (100, 200, 255),
        'tab': (180, 255, 220),
        'b': (170, 240, 255),
        'f12': (190, 255, 230),
        'esc': (255, 255, 255),
        'modes': (100, 255, 180),
        'space': (140, 255, 160),
        't': (130, 240, 150),
        's': (120, 230, 140),
        'g': (110, 220, 130),
        'x': (255, 180, 255),
        'z': (255, 200, 160),
        'l': (200, 255, 180),
        'wheel': (180, 220, 255)
    }

    # === Отрисовка фона меню ===

    # === Отрисовка текста ===
    y_offset = 10

    def draw_line(text, color=(180, 255, 200)):
        nonlocal y_offset
        render = font.render(text, True, color)
        surface.blit(render, (0, y_offset))
        y_offset += 26

    # --- Управление ---
    draw_line(trans['controls'], colors['controls'])
    draw_line(trans['b'], colors['b'])
    draw_line(trans['f12'], colors['f12'])
    draw_line("")

    # --- Режимы ---
    draw_line(trans['modes'], colors['modes'])
    draw_line(f"{trans['space']} {'[ON]' if slow_motion else '[OFF]'}", colors['space'])
    draw_line(f"{trans['t']}: {theme_names[current_theme].capitalize()}", colors['t'])
    draw_line(f"{trans['s']} {'[ON]' if show_sparks else '[OFF]'}", colors['s'])
    draw_line(f"{trans['g']} {'[ON]' if gravity_enabled else '[OFF]'}", colors['g'])
    draw_line(f"{trans['x']} {'[ON]' if chaos_mode else '[OFF]'}", colors['x'])
    draw_line(f"{trans['z']} {'[ON]' if show_stars else '[OFF]'}", colors['z'])
    draw_line(f"{trans['l']} {'[ON]' if show_life else '[OFF]'}", colors['l'])
    draw_line(f"{trans['wheel']}: {int(intensity * 100)}%", colors['wheel'])

    draw_line("")
    draw_line(trans['tab'], colors['tab'])
    draw_line(trans['esc'], colors['esc'])
def draw_gradient_background(surface, color):
    r, g, b = color
    for y in range(HEIGHT):
        factor = y / HEIGHT
        faded = (int(r * (1 - factor)), int(g * (1 - factor)), int(b * (1 - factor)))
        pygame.draw.line(surface, faded, (0, y), (WIDTH, y))


def run_main_mode():
    global current_theme, theme_last_swap
    global chaos_mode, show_sparks, gravity_enabled
    global show_life, show_menu, show_stars
    global intensity, particles, sparks, floating_texts, creatures
    global slow_motion, stars

    running = True
    b_press_count = 0
    b_tip_shown = False
    b_tip_time = 0

    floating_texts.clear()
    creatures.clear()

    import colorsys  # Для точной генерации радужных цветов

    class NyanCat:
        def __init__(self):
            self.x = random.randint(0, WIDTH)
            self.y = random.randint(0, HEIGHT)
            self.speed_x = random.uniform(-2, 2)
            self.speed_y = random.uniform(-2, 2)
            self.size = 60  # Большие прямоугольники
            self.color_index = 0  # Для радужного эффекта
            self.font = pygame.font.SysFont("consolas", 20, bold=True)  # Шрифт для :3

        def update(self):
            self.x += self.speed_x
            self.y += self.speed_y
            self.color_index = (self.color_index + 1) % 360  # Циклический сдвиг для радуги
            if self.x < -self.size or self.x > WIDTH + self.size or self.y < -self.size or self.y > HEIGHT + self.size:
                return False
            return True

        def draw(self, surface):
            # Радужный градиент с использованием colorsys
            for i in range(self.size):
                hue = (self.color_index + i * 2) % 360 / 360.0  # Нормализованный hue (0-1)
                r, g, b = [int(255 * x) for x in colorsys.hsv_to_rgb(hue, 1.0, 1.0)]  # Полная насыщенность и яркость
                pygame.draw.line(surface, (r, g, b, 255), (self.x, self.y + i), (self.x + self.size, self.y + i))

            # Рендер смайлика :3
            text = self.font.render(":3", True, (255, 255, 255))  # Ярко-белый текст
            text_rect = text.get_rect(
                center=(self.x + self.size // 2, self.y + self.size // 2))  # Центрируем в прямоугольнике
            surface.blit(text, text_rect)

    while running:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_TAB:
                    show_menu = not show_menu

                elif event.key == pygame.K_SPACE:
                    slow_motion = not slow_motion

                elif event.key == pygame.K_t:
                    current_theme = (current_theme + 1) % len(THEMES)

                elif event.key == pygame.K_s:
                    show_sparks = not show_sparks

                elif event.key == pygame.K_g:
                    gravity_enabled = not gravity_enabled

                elif event.key == pygame.K_b:
                    b_press_count += 1
                    b_tip_shown = True
                    b_tip_time = now
                    for _ in range(8):
                        x = random.randint(0, WIDTH)
                        y = random.randint(0, HEIGHT)
                        burst((x, y), amount=int(40 * intensity))
                    if b_press_count >= 10:
                        game_flags["main_done"] = True

                elif event.key == pygame.K_x:
                    chaos_mode = not chaos_mode

                elif event.key == pygame.K_z:
                    show_stars = not show_stars

                elif event.key == pygame.K_l:
                    show_life = not show_life

                elif event.key == pygame.K_v:
                    floating_texts.append(FloatingText())

                elif event.key == pygame.K_F12:
                    pygame.image.save(screen, f"screenshot_{int(now)}.png")
                    print("Снято!")

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    burst((pygame.mouse.get_pos()), int(80 * intensity))
                elif event.button == 4:
                    intensity = min(5.0, intensity + 0.1)
                elif event.button == 5:
                    intensity = max(0.2, intensity - 0.1)

        mx, my = pygame.mouse.get_pos()

        # Глитчи и существа
        if chaos_mode and random.random() < 0.05:
            floating_texts.append(FloatingText())
        if show_life and random.random() < 0.01:
            creatures.append(Creature())
        # Добавляем нян кетов в хаос режиме
        if chaos_mode and random.random() < 0.02:
            creatures.append(NyanCat())

        # Частицы
        for _ in range(int(1 * intensity)):
            particles.append(Particle((mx, my), THEMES[theme_names[current_theme]]['colors']))
            if not slow_motion:
                particles.append(Particle((mx, my), THEMES[theme_names[current_theme]]['colors']))

        if show_sparks and random.random() < 0.4 * intensity:
            sparks.append(Spark((mx, my), THEMES[theme_names[current_theme]]['spark']))

        particles = [p for p in particles if p.update()]
        sparks = [s for s in sparks if s.update()]
        floating_texts = [t for t in floating_texts if t.update()]
        creatures = [c for c in creatures if c.update()]

        # Эффект хаоса
        if chaos_mode and random.random() < 0.1:
            pulse = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha = random.randint(40, 100)
            pulse.fill((255, 255, 255, alpha))
            screen.blit(pulse, (0, 0))

        bg_color = THEMES[theme_names[current_theme]]['bg']
        if chaos_mode:
            bg_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        draw_gradient_background(screen, bg_color)

        if show_stars:
            for star in stars:
                star.draw(screen)

        for p in particles:
            p.draw(screen)
        for s in sparks:
            s.draw(screen)
        for t in floating_texts:
            t.draw(screen)
        for c in creatures:
            c.draw(screen)

        # Светящийся курсор
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 255, 255, 80), (20, 20), 20)
        screen.blit(glow, (mx - 20, my - 20))
        pygame.draw.circle(screen, (255, 255, 255), (mx, my), 4 + int(intensity))

        # Инструкция
        if not show_menu:
            draw_menu(screen, font)

        pygame.display.flip()
music_state = {
    "track": "Relacs.mp3",
    "index": 0,
    "paused": False,
    "playing": False,
    "volume": 0.5
}
def show_intro_screen():
    title_font = pygame.font.SysFont("segoeui", 56)
    info_font = pygame.font.SysFont("consolas", 22)
    warning_font = pygame.font.SysFont("consolas", 12)
    info_lines_ru = [
        "Перед тобой — не просто экран,",
        "а сборник мини-игр в цифровой тишине.",
        "Каждый режим — своя вселенная.",
        "Но истинный ключ скрыт в красных звёздах…",
    ]

    info_lines_en = [
        "Before you is not just a screen —",
        "but a collection of mini-games in digital silence.",
        "Each mode is a universe of its own.",
        "Yet the true key lies within red stars…",
    ]

    showing = True
    input_buffer = ""
    menu_shown = False
    hint_timer = pygame.time.get_ticks()
    show_hint = True


    button_width, button_height = 360, 70
    gap = 80

    button_labels = {
        "ru": [
            "Светлячки", "Космическая симфония", "Лунная река",
            "Фейрверки-режим", "Релакс-режим", "Космический шторм",
            "Хаос-режим", "Стекло-режим"
        ],
        "en": [
            "Fireflies", "Cosmic Symphony", "Moon River",
            "Fireworks Mode", "Relax Mode", "Cosmic Storm",
            "Chaos Mode", "Glass Mode"
        ]
    }

    buttons = [
        (0, Firefly, (15, 15, 15)),
        (1, run_cosmic_symphony_mode, (2, 86, 105)),
        (2, run_moon_river_mode, (4, 4, 4)),
        (3, run_skyburst_mode, (200, 160, 255)),
        (4, run_relax_mode, (180, 255, 180)),
        (5, run_cosmic_storm_mode, (150, 0, 255)),
        (6, run_main_mode, (255, 120, 120)),
        (7, run_fragments_mode, (200, 100, 255)),
    ]
    epilepsy_warning_ru = "ВНИМАНИЕ: Возможны резкие вспышки света и быстрые визуальные эффекты."
    epilepsy_warning_en = "WARNING: Flashing lights and rapid visual effects may occur."
    # Вычисляем начальную Y-позицию кнопок — по центру
    total_buttons_height = len(buttons) * gap
    info_text_height = 10  # Высота блока с информационным текстом
    start_y = HEIGHT // 3 + gap - 175  # Смещаем кнопки ниже

    secret_button_rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + gap * len(buttons), button_width,
                                     button_height)
    secret_button_data = ("???", run_illusion_mode, (255, 0, 255), "🌀")
    secret_button_offset = [0, 0]

    # Звёзды: 100 обычных
    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(100)]
    red_star_indices = []

    # Зоны, где не должны появляться красные звёзды
    def is_in_exclusion_zone(x, y):
        # Заголовок
        title_rect = pygame.Rect(WIDTH // 2 - 300, 20, 600, 60)
        # Инфо-текст
        for i in range(4):
            if 140 + i * 28 - 15 < y < 140 + i * 28 + 15 and WIDTH // 2 - 200 < x < WIDTH // 2 + 200:
                return True
        # Флаг
        if WIDTH - 50 < x < WIDTH - 10 and 10 < y < 50:
            return True
        # Слайдер громкости
        if WIDTH - 210 < x < WIDTH - 70 and 26 < y < 34:
            return True
        # Трек внизу
        if x < 300 and y > HEIGHT - 100:  # Под треком и предупреждением
            return True
        # Кнопки
        for i in range(len(buttons)):
            btn_y = start_y + i * gap
            if (WIDTH // 2 - button_width // 2 < x < WIDTH // 2 + button_width // 2 and
                    btn_y < y < btn_y + button_height):
                return True
        # Секретная кнопка
        if secret_button_rect.collidepoint(x, y):
            return True
        return title_rect.collidepoint(x, y)

    # Размещаем ровно 4 красные звезды вне зон
    while len(red_star_indices) < 4:
        idx = random.randint(0, len(stars) - 1)
        x, y = stars[idx]
        if not is_in_exclusion_zone(x, y) and idx not in red_star_indices:
            red_star_indices.append(idx)

    red_star_clicked = [False] * 4
    warning_y = HEIGHT - 70  # Предупреждение чуть выше трека
    # Музыка
    track_options = ["Relacs.mp3", "Relacs2.mp3", "Burning.mp3"]
    track_y = HEIGHT - 40

    if not music_state["playing"] and os.path.exists(music_state["track"]):
        pygame.mixer.music.load(music_state["track"])
        pygame.mixer.music.set_volume(music_state["volume"])
        pygame.mixer.music.play(-1)
        music_state["playing"] = True

    # Слайдер громкости
    slider_x = WIDTH - 210
    slider_y = 30
    slider_width = 140
    slider_height = 8
    volume_rect = pygame.Rect(slider_x, slider_y - slider_height // 2, slider_width, slider_height)

    while showing:
        now = pygame.time.get_ticks()
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    showing = False
                elif event.key == pygame.K_n:
                    music_state["index"] = (music_state["index"] + 1) % len(track_options)
                    music_state["track"] = track_options[music_state["index"]]
                    if os.path.exists(music_state["track"]):
                        pygame.mixer.music.load(music_state["track"])
                        pygame.mixer.music.set_volume(music_state["volume"])
                        if not music_state["paused"]:
                            pygame.mixer.music.play(-1)
                            music_state["playing"] = True
                elif event.key == pygame.K_m:
                    if music_state["playing"]:
                        if not music_state["paused"]:
                            pygame.mixer.music.pause()
                            music_state["paused"] = True
                        else:
                            pygame.mixer.music.unpause()
                            music_state["paused"] = False
                    else:
                        if os.path.exists(music_state["track"]):
                            pygame.mixer.music.load(music_state["track"])
                            pygame.mixer.music.set_volume(music_state["volume"])
                            pygame.mixer.music.play(-1)
                            music_state["playing"] = True
                            music_state["paused"] = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Кнопки
                for i, (_, action, _) in enumerate(buttons):
                    btn_rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * gap, button_width,
                                           button_height)
                    if btn_rect.collidepoint(event.pos):
                        saved_music_state = music_state.copy()
                        action()
                        if os.path.exists(saved_music_state["track"]) and not saved_music_state["paused"]:
                            pygame.mixer.music.load(saved_music_state["track"])
                            pygame.mixer.music.set_volume(saved_music_state["volume"])
                            pygame.mixer.music.play(-1)
                            music_state.update(saved_music_state)
                        elif saved_music_state["paused"]:
                            pygame.mixer.music.pause()
                            music_state["paused"] = True

                # Секретная кнопка
                if all(red_star_clicked) and secret_button_rect.collidepoint(event.pos):
                    pygame.mixer.music.load("Glitc.mp3")
                    pygame.mixer.music.play()
                    secret_button_data[1]()

                # Красные звёзды
                for i, idx in enumerate(red_star_indices):
                    x, y = stars[idx]
                    if abs(mx - x) < 8 and abs(my - y) < 8:
                        red_star_clicked[i] = True

                # Переключение языка по клику на флаг
                flag_rect = pygame.Rect(WIDTH - 50, 10, 40, 40)
                if flag_rect.collidepoint(event.pos):
                    global language, flag_is_russian
                    if language == "ru":
                        language = "en"
                        flag_is_russian = False
                    else:
                        language = "ru"
                        flag_is_russian = True

                if volume_rect.collidepoint(event.pos):
                    relative_x = event.pos[0] - slider_x
                    new_volume = max(0.0, min(1.0, relative_x / slider_width))
                    music_state["volume"] = new_volume
                    pygame.mixer.music.set_volume(new_volume)
                # Слайдер
                if volume_rect.collidepoint(event.pos):
                    relative_x = event.pos[0] - slider_x
                    new_volume = max(0.0, min(1.0, relative_x / slider_width))
                    music_state["volume"] = new_volume
                    pygame.mixer.music.set_volume(new_volume)

                menu_shown = True

        # Фон
        draw_gradient_background(screen, (10, 10, 20))

        # Рисуем звёзды
        for i, (x, y) in enumerate(stars):
            if i in red_star_indices and not red_star_clicked[red_star_indices.index(i)]:
                pygame.draw.circle(screen, (255, 80, 80), (x, y), 4)
            else:
                pygame.draw.circle(screen, (200, 200, 255), (x, y), 2)

        # Заголовок
        pulse = 128 + int(127 * math.sin(now * 0.003))
        glow_color = (255, pulse, 50)
        title_text = title_font.render("Меню режимов" if language == "ru" else "Mode Menu", True, glow_color)
        title_rect = title_text.get_rect(center=(WIDTH // 2, 50))
        screen.blit(title_text, title_rect)

        # Инфо-текст
        info_lines = info_lines_en if language == "en" else info_lines_ru
        for i, line in enumerate(info_lines):
            pulse_line = 180 + int(70 * math.sin(now * 0.002 + i))
            info_surf = info_font.render(line, True, (pulse_line, pulse_line, pulse_line))
            info_rect = info_surf.get_rect(center=(WIDTH // 2, 140 + i * 28))
            screen.blit(info_surf, info_rect)

        # Функция рисования кнопки
        def draw_button(rect, text, color, icon=""):
            button_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            for y in range(rect.height):
                ratio = y / rect.height
                r = int(color[0] * (1 - ratio) + 20 * ratio)
                g = int(color[1] * (1 - ratio) + 20 * ratio)
                b = int(color[2] * (1 - ratio) + 40 * ratio)
                pygame.draw.line(button_surface, (r, g, b), (0, y), (rect.width, y))
            shape_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shape_surf, (255, 255, 255, 255), shape_surf.get_rect(), border_radius=20)
            button_surface.blit(shape_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            pygame.draw.rect(button_surface, (255, 255, 255), button_surface.get_rect(), width=3, border_radius=20)
            screen.blit(button_surface, rect.topleft)
            label = info_font.render(text, True, (255, 255, 255))
            screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

        # Кнопки
        for i, (label_idx, action, color) in enumerate(buttons):
            btn_rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * gap, button_width, button_height)
            label = button_labels[language][label_idx]
            draw_button(btn_rect, label, color)

        # Секретная кнопка (с эффектом "дрожания")
        if all(red_star_clicked):
            dist = math.hypot(mx - secret_button_rect.centerx, my - secret_button_rect.centery)
            if dist < 150:
                secret_button_offset = [random.randint(-3, 3), random.randint(-3, 3)]
            else:
                secret_button_offset = [0, 0]
            offset_rect = secret_button_rect.move(secret_button_offset[0], secret_button_offset[1])
            draw_button(offset_rect, secret_button_data[0], secret_button_data[2])

        # Текущий трек
        track_label = info_font.render(
            f"Трек: {music_state['track'].replace('.mp3', '')}" if language == "ru" else f"Track: {music_state['track'].replace('.mp3', '')}",
            True, (200, 200, 200)
        )
        screen.blit(track_label, (20, track_y))

        # Подсказки
        if show_hint and now - hint_timer < 10000:
            hint1 = info_font.render(
                "Нажми 'M' для выкл/вкл музыки" if language == "ru" else "Press 'M' to toggle music", True,
                (180, 255, 180))
            hint2 = info_font.render("Нажми 'N' для смены трека" if language == "ru" else "Press 'N' to change track",
                                     True, (180, 255, 180))
            screen.blit(hint1, (20, track_y - 40))
            screen.blit(hint2, (20, track_y - 20))
        warn_text = warning_font.render(
            epilepsy_warning_ru if language == "ru" else epilepsy_warning_en,
            True, (50, 50, 50)  # Оранжевый цвет
        )
        warn_rect = warn_text.get_rect(center=(WIDTH // 4 - 218, warning_y - 25))
        screen.blit(warn_text, warn_rect)        # Флаг
        flag_x, flag_y = WIDTH - 50, 10
        flag_size = 40
        if flag_is_russian:
            pygame.draw.rect(screen, (255, 255, 255), (flag_x, flag_y, flag_size, flag_size // 3))
            pygame.draw.rect(screen, (0, 0, 255), (flag_x, flag_y + flag_size // 3, flag_size, flag_size // 3))
            pygame.draw.rect(screen, (255, 0, 0), (flag_x, flag_y + 2 * flag_size // 3, flag_size, flag_size // 3))
        else:
            for i in range(13):
                color = (255, 0, 0) if i % 2 == 0 else (255, 255, 255)
                pygame.draw.rect(screen, color, (flag_x, flag_y + i * (flag_size // 13), flag_size, flag_size // 13))
            pygame.draw.rect(screen, (0, 0, 139), (flag_x, flag_y, flag_size // 2, flag_size // 2))
            for row in range(5):
                for col in range(5):
                    if (row + col) % 2 == 0:
                        pygame.draw.polygon(screen, (255, 255, 255), [
                            (flag_x + col * (flag_size // 10) + 2, flag_y + row * (flag_size // 10) + 2),
                            (flag_x + (col + 0.5) * (flag_size // 10), flag_y + (row + 1) * (flag_size // 10) - 2),
                            (flag_x + (col + 1) * (flag_size // 10) - 2, flag_y + row * (flag_size // 10) + 2)
                        ])

        # Слайдер громкости
        pygame.draw.rect(screen, (80, 80, 80), volume_rect, border_radius=4)
        slider_pos = slider_x + int(music_state["volume"] * slider_width)
        pygame.draw.rect(screen, (120, 180, 255),
                         (slider_x, slider_y - slider_height // 2, slider_pos - slider_x, slider_height),
                         border_radius=4)
        pygame.draw.circle(screen, (200, 220, 255), (slider_pos, slider_y), 10)

        vol_label_font = pygame.font.SysFont("consolas", 16)
        screen.blit(vol_label_font.render("0%", True, (180, 180, 180)), (slider_x - 20, slider_y + 10))
        screen.blit(vol_label_font.render("100%", True, (180, 180, 250)), (slider_x + slider_width - 10, slider_y + 10))
        vol_title = vol_label_font.render("Громкость" if language == "ru" else "Volume", True, (200, 200, 200))
        screen.blit(vol_title, (slider_x + slider_width // 2 - vol_title.get_width() // 2, slider_y - 25))

        # Перетаскивание слайдера
        if pygame.mouse.get_pressed()[0]:
            if volume_rect.collidepoint(mx, my):
                relative_x = mx - slider_x
                new_volume = max(0.0, min(1.0, relative_x / slider_width))
                music_state["volume"] = new_volume
                pygame.mixer.music.set_volume(new_volume)

        # Курсор
        pygame.draw.circle(screen, (255, 100, 0), (mx, my), 12)
        pygame.draw.circle(screen, (255, 180, 50), (mx, my), 6)

        pygame.display.flip()
        clock.tick(144)

    # Восстановление музыки
    if music_state["playing"] and not music_state["paused"] and os.path.exists(music_state["track"]):
        pygame.mixer.music.load(music_state["track"])
        pygame.mixer.music.set_volume(music_state["volume"])
        pygame.mixer.music.play(-1)
font = pygame.font.SysFont("consolas", 17)
show_intro_screen()
if __name__ == "__main__":
    show_intro_screen()
    pygame.quit()
    sys.exit()