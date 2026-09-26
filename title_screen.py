"""
title_screen.py - Pantalla de título oficial para Da Vinci Fighters II Special Champion Edition.

Características:
- Carga y escala assets/backgrounds/home.png a resolución 1280x720.
- Bounding box del logotipo: pygame.Rect(99, 42, 1090, 376).
- Shader de destello metálico continuo: inclinación 25° forward slant, ancho de banda 120px,
  atenuación coseno (cosine alpha falloff), ciclo de 2.8s (1.0s barrido activo, 1.8s reposo).
- Pipeline de renderizado de dos etapas con cero sangrado (zero-bleed): multiplicación con máscara
  precalculada (logo_mask) mediante BLEND_RGBA_MULT y blit aditivo a pantalla mediante BLEND_ADD.
- Prompt parpadeante 'PRESS ANY KEY TO START' a 2 Hz centrado en Y=580 con drop shadow y pill box.
- Sincronización de Opening Theme.mp3 en bucle mediante audio_manager.play_music("menu").
- Transición al menú principal ante cualquier tecla (Space, Return, Esc) o click con SFX menu_confirm.
"""

import os
import math
import pygame
import numpy as np
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_YELLOW,
    COLOR_WHITE,
    FPS,
)
from audio_manager import audio_manager


class TitleScreen:
    """
    Pantalla de inicio oficial con la imagen home.png.
    Incluye shader de brillo metálico animado con dos etapas de blend y prompt parpadeante.
    """
    LOGO_RECT = pygame.Rect(99, 42, 1090, 376)
    SWEEP_CYCLE_SEC = 2.8
    SWEEP_ACTIVE_SEC = 1.0
    SWEEP_REST_SEC = 1.8
    BAND_HALF_WIDTH = 60
    SLANT_ANGLE_DEG = 25

    def __init__(self, screen):
        self.screen = screen
        self.image = None
        self.logo_rect = pygame.Rect(99, 42, 1090, 376)
        self.logo_mask = None

        # Superficie de destello con canal alfa per-pixel (SRCALPHA)
        self.sheen_surf = pygame.Surface(
            (self.logo_rect.width, self.logo_rect.height),
            pygame.SRCALPHA
        )

        # Parámetros y estado de animación del destello
        self.sweep_width = 1200
        self.sheen_speed = 15.0
        self.sheen_period = 120  # frames para wraparound en tests
        self.sheen_offset = 0.0
        self.sheen_frame = 0

        # Temporizadores internos
        self.time = 0.0
        self.blink_timer = 0
        self._updated_this_frame = False

        # Configuración visual del prompt
        self.prompt_y = 580
        self.font = pygame.font.Font(None, 38)

        # Geometría precalculada de barrido diagonal (inclinación 25° forward slant)
        self.slant_offset = int(self.logo_rect.height * math.tan(math.radians(self.SLANT_ANGLE_DEG)))
        half_slant = self.slant_offset // 2
        self.sweep_start_c = -self.BAND_HALF_WIDTH - half_slant - 20
        self.sweep_end_c = self.logo_rect.width + self.BAND_HALF_WIDTH + half_slant + 20
        self.sweep_distance = self.sweep_end_c - self.sweep_start_c

        # Cargar home.png, construir máscara y arrancar música
        self._load_image()
        self._build_logo_mask()
        audio_manager.play_music("menu", loop=True)

    def _load_image(self):
        """Carga y escala assets/backgrounds/home.png a 1280x720."""
        path = os.path.join("assets", "backgrounds", "home.png")
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                self.image = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception as e:
                print(f"[TitleScreen] Error cargando home.png: {e}")
                self.image = None
        else:
            self.image = None

    def _build_logo_mask(self):
        """
        Precalcula una máscara RGBA de 4 canales de la región del logotipo
        para aislar el texto dorado/cromo del fondo azul marino (1, 9, 114)
        y garantizar sangrado cero (0 bleed) al aplicar BLEND_ADD.
        """
        if not self.image:
            return

        try:
            logo_sub = self.image.subsurface(self.logo_rect)
            arr = pygame.surfarray.array3d(logo_sub)
            bg = np.array([1, 9, 114], dtype=np.float32)
            diff = np.linalg.norm(arr.astype(np.float32) - bg, axis=-1)
            is_logo = (diff > 25)

            self.logo_mask = pygame.Surface(
                (self.logo_rect.width, self.logo_rect.height),
                pygame.SRCALPHA
            )
            val = np.where(is_logo, 255, 0).astype(np.uint8)
            pygame.surfarray.pixels3d(self.logo_mask)[:] = val[:, :, None]
            pygame.surfarray.pixels_alpha(self.logo_mask)[:] = val
        except Exception as e:
            print(f"[TitleScreen] Error construyendo logo_mask: {e}")
            self.logo_mask = None

    def handle_input(self, event):
        """
        Al presionar cualquier tecla (Space, Return, Esc) o click del mouse,
        emite SFX de confirmación y retorna 'continue'.
        Ignora eventos KEYUP, MOUSEMOTION, etc.
        """
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            audio_manager.play_sfx("menu_confirm")
            return "continue"
        return None

    def update(self, dt=1.0 / 60):
        """
        Actualiza el desplazamiento del destello del logo, el tiempo de ciclo
        y el contador de parpadeo del prompt.
        """
        frames = max(1, int(round(dt * 60))) if dt > 0 else 1
        self.time += dt
        self.blink_timer += frames
        self.sheen_frame = (self.sheen_frame + frames) % self.sheen_period
        self.sheen_offset = (self.sheen_frame * self.sheen_speed) % self.sweep_width
        self._updated_this_frame = True

    def _render_sheen(self, target):
        """
        Renderiza el destello metálico mediante el pipeline de 2 etapas:
        1. Multiplicación de la franja diagonal con logo_mask (BLEND_RGBA_MULT)
           para anular completamente los píxeles de fondo azul marino.
        2. Blit aditivo (BLEND_ADD) sobre el target asegurando cero sangrado.
        """
        if not self.logo_mask or not self.sheen_surf:
            return

        cycle_pos = self.time % self.SWEEP_CYCLE_SEC
        if cycle_pos >= self.SWEEP_ACTIVE_SEC:
            return  # Fase de reposo entre barridos (1.8s sin costo de renderizado)

        # Progreso normalizado [0.0 .. 1.0] con interpolación suave (smoothstep)
        tau = cycle_pos / self.SWEEP_ACTIVE_SEC
        tau_eased = 3.0 * (tau ** 2) - 2.0 * (tau ** 3)
        c = self.sweep_start_c + tau_eased * self.sweep_distance

        H = self.logo_rect.height
        self.sheen_surf.fill((0, 0, 0, 0))

        # Franja luminosa diagonal (25° forward slant, 120px de ancho) con caída coseno
        half_slant = self.slant_offset // 2
        for dx in range(-self.BAND_HALF_WIDTH, self.BAND_HALF_WIDTH + 1, 2):
            t = abs(dx) / self.BAND_HALF_WIDTH
            alpha = int(240 * 0.5 * (1.0 + math.cos(math.pi * t)))
            scale = alpha / 255.0
            r = int(255 * scale)
            g = int((235 + 20 * (1.0 - t)) * scale)
            b = int((140 + 115 * (1.0 - t)) * scale)

            p_top = (int(c + dx + half_slant), 0)
            p_bot = (int(c + dx - half_slant), H)
            pygame.draw.line(self.sheen_surf, (r, g, b, alpha), p_top, p_bot, 2)

        # Etapa 1: Filtrar píxeles que no pertenecen al logotipo
        self.sheen_surf.blit(self.logo_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Etapa 2: Aplicar destello iluminado al lienzo con adición pura
        target.blit(self.sheen_surf, (self.logo_rect.x, self.logo_rect.y), special_flags=pygame.BLEND_ADD)

    def draw(self, screen=None):
        """
        Renderiza la imagen de inicio home.png, el destello metálico del logo
        y el mensaje parpadeante 'PRESS ANY KEY TO START'.
        Soporta llamada sin argumentos (usa self.screen) o con screen explícito.
        """
        target = screen if screen is not None else self.screen
        if target is None:
            return

        # Auto-avance de reloj si update() no fue invocado externamente este frame
        if not self._updated_this_frame:
            self.blink_timer += 1
            self.time += 1.0 / 60.0
            self.sheen_frame = (self.sheen_frame + 1) % self.sheen_period
            self.sheen_offset = (self.sheen_frame * self.sheen_speed) % self.sweep_width
        self._updated_this_frame = False

        # 1. Fondo principal o fallback azul oscuro si home.png falta
        if self.image:
            target.blit(self.image, (0, 0))
        else:
            target.fill((10, 10, 40))

        # 2. Destello metálico animado con cero sangrado
        self._render_sheen(target)

        # 3. Prompt arcade parpadeante a 2 Hz (30 frames ON, 30 frames OFF)
        if (self.blink_timer // 30) % 2 == 0:
            prompt_str = "PRESS ANY KEY TO START"
            txt_fg = self.font.render(prompt_str, True, COLOR_YELLOW)
            txt_shadow = self.font.render(prompt_str, True, (10, 10, 10))

            pad_x, pad_y = 16, 7
            w = txt_fg.get_width() + pad_x * 2
            h = txt_fg.get_height() + pad_y * 2

            pill = pygame.Surface((w, h), pygame.SRCALPHA)
            pill.fill((0, 0, 0, 180))
            pygame.draw.rect(pill, (255, 200, 40, 120), pill.get_rect(), width=2, border_radius=6)

            pos_x = SCREEN_WIDTH // 2 - w // 2
            pos_y = self.prompt_y - pad_y

            target.blit(pill, (pos_x, pos_y))
            target.blit(txt_shadow, (pos_x + pad_x + 2, pos_y + pad_y + 2))
            target.blit(txt_fg, (pos_x + pad_x, pos_y + pad_y))
