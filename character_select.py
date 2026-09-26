"""
character_select.py - Pantalla oficial de Selección de Personajes de Street Fighter II y Da Vinci Fighters.
Soporta:
- Renderizado de assets/backgrounds/player select.png (mapa mundial y cuadrícula de retratos).
- Cuadrícula de selección para los 5 profesores de Da Vinci (Carloni, Cavasso, Romero, Gamaliel, Sellanes).
- Selectores animados con parpadeo arcade (P1 en Rojo, P2/IA en Azul).
- Tarjetas laterales de previsualización con estadísticas (Salud, Velocidad, Materias, Cita y Ataque Especial).
- Soporte para modo 1P vs IA (autoselección de IA) y 2P PVP.
- Sincronización de audio con Character Select.mp3 y efectos de sonido arcade.
"""

import os
import pygame
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_WHITE,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_BG,
    COLOR_GREEN,
    MODE_PVAI,
    MODE_PVP,
    FPS,
)
from character_data import CHARACTERS, get_character_data
from audio_manager import audio_manager


# Coordenadas y banderas de país para cada profesor en el mapa mundial
CHARACTER_LOCATIONS = {
    "carloni": {"country": "JAPÓN", "flag": "🇯🇵", "stage_name": "Database Suzaku Dojo", "map_pos": (1040, 260)},
    "cavasso": {"country": "EE. UU.", "flag": "🇺🇸", "stage_name": "Airbase Hangar", "map_pos": (300, 250)},
    "romero": {"country": "TAILANDIA", "flag": "🇹🇭", "stage_name": "Corporate Ayutthaya Ruins", "map_pos": (920, 350)},
    "gamaliel": {"country": "BRASIL", "flag": "🇧🇷", "stage_name": "OOP Amazon Basin", "map_pos": (420, 460)},
    "sellanes": {"country": "TAILANDIA", "flag": "🇹🇭", "stage_name": "Requirements Palace", "map_pos": (880, 340)},
}

# Cuadrícula arcade 2x4 (8 casillas de Street Fighter II)
GRID_SLOTS = [
    # Fila 0 (Superior)
    {"char_id": "carloni", "name": "CARLONI", "row": 0, "col": 0, "grid_rect": (380, 475, 115, 100)},
    {"char_id": "cavasso", "name": "CAVASSO", "row": 0, "col": 1, "grid_rect": (510, 475, 115, 100)},
    {"char_id": "romero",  "name": "ROMERO",  "row": 0, "col": 2, "grid_rect": (640, 475, 115, 100)},
    {"char_id": "gamaliel","name": "GAMALIEL","row": 0, "col": 3, "grid_rect": (770, 475, 115, 100)},
    # Fila 1 (Inferior)
    {"char_id": "sellanes","name": "SELLANES","row": 1, "col": 0, "grid_rect": (380, 585, 115, 100)},
    {"char_id": "carloni", "name": "CARLONI 2","row": 1, "col": 1, "grid_rect": (510, 585, 115, 100)},
    {"char_id": "cavasso", "name": "RANDOM",  "row": 1, "col": 2, "grid_rect": (640, 585, 115, 100)},
    {"char_id": "romero",  "name": "BONUS",   "row": 1, "col": 3, "grid_rect": (770, 585, 115, 100)},
]


class CharacterSelect:
    """
    Pantalla de Selección de Personajes con mapa mundial, casillas animadas y previsualización.
    """
    def __init__(self, screen, game_mode=MODE_PVAI):
        self.screen = screen
        self.game_mode = game_mode
        self.char_keys = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]

        self.font_title = pygame.font.Font(None, 44)
        self.font_header = pygame.font.Font(None, 34)
        self.font_card = pygame.font.Font(None, 26)
        self.font_info = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)

        # Selección de casillas (0 a 7 en GRID_SLOTS)
        self.p1_slot_idx = 0
        self.p2_slot_idx = 1
        self.p1_confirmed = False
        self.p2_confirmed = False
        self.ai_timer = 0
        self.transition_timer = 0

        self.blink_timer = 0.0

        # Cargar fondo de mapa mundial player select.png
        self.bg_image = None
        bg_path = os.path.join("assets", "backgrounds", "player select.png")
        if os.path.exists(bg_path):
            try:
                raw_bg = pygame.image.load(bg_path)
                self.bg_image = pygame.transform.scale(raw_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception as e:
                print(f"[CharacterSelect] Error cargando player select.png: {e}")

        # Iniciar música oficial de Character Select
        audio_manager.play_music("character_select")

    @property
    def p1_idx(self):
        return self.p1_slot_idx % len(self.char_keys)

    @p1_idx.setter
    def p1_idx(self, val):
        self.p1_slot_idx = val % len(GRID_SLOTS)

    @property
    def p2_idx(self):
        return self.p2_slot_idx % len(self.char_keys)

    @p2_idx.setter
    def p2_idx(self, val):
        self.p2_slot_idx = val % len(GRID_SLOTS)

    @property
    def p1_char(self):
        return GRID_SLOTS[self.p1_slot_idx]["char_id"]

    @property
    def p2_char(self):
        return GRID_SLOTS[self.p2_slot_idx]["char_id"]

    def handle_input(self, event):
        """Maneja la navegación por teclado para P1 y P2."""
        if event.type == pygame.KEYDOWN:
            # 1. Controles de Jugador 1
            if not self.p1_confirmed:
                prev_slot = self.p1_slot_idx
                if self.game_mode == MODE_PVAI:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                    elif event.key in (pygame.K_w, pygame.K_UP):
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                    
                    if self.p1_slot_idx != prev_slot:
                        audio_manager.play_sfx("menu_navigate")

                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_j, pygame.K_f):
                        self.p1_confirmed = True
                        audio_manager.play_sfx("select")
                        if self.p2_slot_idx == self.p1_slot_idx:
                            self.p2_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                        self.p2_confirmed = True
                        return {
                            "action": "fight",
                            "action_alt": "vs",
                            "p1_char": self.p1_char,
                            "p2_char": self.p2_char,
                        }
                else: # MODE_PVP
                    if event.key == pygame.K_a:
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key == pygame.K_d:
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                    elif event.key == pygame.K_w:
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key == pygame.K_s:
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)

                    if self.p1_slot_idx != prev_slot:
                        audio_manager.play_sfx("menu_navigate")

                    if event.key in (pygame.K_SPACE, pygame.K_j, pygame.K_f):
                        self.p1_confirmed = True
                        audio_manager.play_sfx("select")
                        if self.p2_confirmed:
                            return {
                                "action": "fight",
                                "action_alt": "vs",
                                "p1_char": self.p1_char,
                                "p2_char": self.p2_char,
                            }

            # 2. Controles de Jugador 2 (Sólo en modo PVP)
            if self.game_mode == MODE_PVP and not self.p2_confirmed:
                prev_slot = self.p2_slot_idx
                if event.key == pygame.K_LEFT:
                    self.p2_slot_idx = (self.p2_slot_idx - 1) % len(self.char_keys)
                elif event.key == pygame.K_RIGHT:
                    self.p2_slot_idx = (self.p2_slot_idx + 1) % len(self.char_keys)
                elif event.key == pygame.K_UP:
                    self.p2_slot_idx = (self.p2_slot_idx - 1) % len(self.char_keys)
                elif event.key == pygame.K_DOWN:
                    self.p2_slot_idx = (self.p2_slot_idx + 1) % len(self.char_keys)

                if self.p2_slot_idx != prev_slot:
                    audio_manager.play_sfx("menu_navigate")

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP1):
                    self.p2_confirmed = True
                    audio_manager.play_sfx("select")
                    if self.p1_confirmed:
                        return {
                            "action": "fight",
                            "action_alt": "vs",
                            "p1_char": self.p1_char,
                            "p2_char": self.p2_char,
                        }

            if self.p1_confirmed and self.p2_confirmed:
                return {
                    "action": "fight",
                    "action_alt": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                }

        return None

        return None

    def update(self, dt=1.0 / FPS):
        """Actualiza animaciones de parpadeo y temporizadores de transición."""
        self.blink_timer += dt

        if self.p1_confirmed and self.p2_confirmed:
            self.transition_timer += dt
            # Transición a la pantalla VS tras 0.4s de confirmación
            if self.transition_timer >= 0.4:
                return {
                    "action": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                }
        return None

    def draw(self, screen=None):
        """Renderiza la pantalla completa de selección de luchadores."""
        target = screen or self.screen
        if target is None:
            return

        # 1. Fondo del mapa mundial
        if self.bg_image:
            target.blit(self.bg_image, (0, 0))
        else:
            target.fill(COLOR_BG)

        # 2. Encabezado Arcade Superior
        banner_rect = pygame.Rect(SCREEN_WIDTH // 2 - 280, 15, 560, 48)
        pygame.draw.rect(target, (20, 20, 35, 220), banner_rect, border_radius=8)
        pygame.draw.rect(target, COLOR_YELLOW, banner_rect, 2, border_radius=8)
        title_surf = self.font_title.render("SELECT YOUR FIGHTER", True, COLOR_YELLOW)
        target.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 22))

        # 3. Marcadores de los profesores en el mapa mundial
        for slot in GRID_SLOTS[:5]:
            char_id = slot["char_id"]
            loc = CHARACTER_LOCATIONS.get(char_id, {})
            pos = loc.get("map_pos", (640, 250))
            data = get_character_data(char_id)
            
            # Punto de mapa
            is_p1_here = (slot == GRID_SLOTS[self.p1_slot_idx])
            is_p2_here = (slot == GRID_SLOTS[self.p2_slot_idx])

            dot_color = (255, 60, 60) if is_p1_here else ((60, 120, 255) if is_p2_here else data["color"])
            pygame.draw.circle(target, dot_color, pos, 9)
            pygame.draw.circle(target, COLOR_WHITE, pos, 9, 2)

            # Nombre de país
            tag_surf = self.font_small.render(loc.get("country", ""), True, COLOR_WHITE)
            target.blit(tag_surf, (pos[0] - tag_surf.get_width() // 2, pos[1] + 12))

        # 4. Cuadrícula de casillas de selección (Bottom Grid)
        is_blink_on = (int(self.blink_timer * 6) % 2 == 0)

        for i, slot in enumerate(GRID_SLOTS):
            x, y, w, h = slot["grid_rect"]
            char_id = slot["char_id"]
            data = get_character_data(char_id)
            rect = pygame.Rect(x, y, w, h)

            # Fondo de la casilla
            pygame.draw.rect(target, (30, 30, 45), rect)
            pygame.draw.rect(target, (60, 60, 80), rect, 2)

            # Miniatura de color / retrato del personaje
            portrait_box = pygame.Rect(x + 10, y + 10, w - 20, h - 35)
            pygame.draw.rect(target, data["color"], portrait_box)
            pygame.draw.rect(target, (220, 220, 220), portrait_box, 1)

            # Nombre en la casilla
            name_text = slot["name"]
            lbl_name = self.font_info.render(name_text, True, COLOR_WHITE)
            target.blit(lbl_name, (x + w // 2 - lbl_name.get_width() // 2, y + h - 22))

            # Resaltado P1 (ROJO)
            if i == self.p1_slot_idx:
                p1_color = (255, 50, 50) if (not self.p1_confirmed or is_blink_on) else (50, 255, 50)
                pygame.draw.rect(target, p1_color, rect.inflate(8, 8), 4, border_radius=4)
                badge_p1 = self.font_card.render("1P", True, p1_color)
                target.blit(badge_p1, (x - 4, y - 18))

            # Resaltado P2 / IA (AZUL)
            if i == self.p2_slot_idx:
                p2_color = (60, 140, 255) if (not self.p2_confirmed or is_blink_on) else (50, 255, 50)
                pygame.draw.rect(target, p2_color, rect.inflate(14, 14), 3, border_radius=6)
                badge_p2 = self.font_card.render("2P" if self.game_mode == MODE_PVP else "CPU", True, p2_color)
                target.blit(badge_p2, (x + w - badge_p2.get_width() + 4, y - 18))

        # 5. Tarjeta de información lateral izquierda (PLAYER 1)
        self._draw_character_card(target, self.p1_char, is_player_1=True)

        # 6. Tarjeta de información lateral derecha (PLAYER 2 / CPU)
        self._draw_character_card(target, self.p2_char, is_player_1=False)

        # 7. Barra de instrucciones inferior
        bottom_bar = pygame.Rect(0, SCREEN_HEIGHT - 32, SCREEN_WIDTH, 32)
        pygame.draw.rect(target, (10, 10, 20), bottom_bar)
        
        status_str = (
            "¡COMBATE CONFIRMADO! PREPARANDO ENFRENTAMIENTO..."
            if (self.p1_confirmed and self.p2_confirmed)
            else "P1: WASD / FLECHAS + ENTER para confirmar  |  ESC: Salir"
        )
        status_color = COLOR_GREEN if (self.p1_confirmed and self.p2_confirmed) else COLOR_YELLOW
        status_surf = self.font_info.render(status_str, True, status_color)
        target.blit(status_surf, (SCREEN_WIDTH // 2 - status_surf.get_width() // 2, SCREEN_HEIGHT - 25))

    def _draw_character_card(self, screen, char_id, is_player_1=True):
        """Dibuja la tarjeta con estadísticas detalladas del luchador a los lados."""
        data = get_character_data(char_id)
        loc = CHARACTER_LOCATIONS.get(char_id, {})

        card_w = 320
        card_h = 580
        x = 30 if is_player_1 else (SCREEN_WIDTH - card_w - 30)
        y = 90

        card_rect = pygame.Rect(x, y, card_w, card_h)
        # Fondo oscuro semi-transparente
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((15, 18, 30, 235))
        screen.blit(card_surf, (x, y))

        border_color = (255, 70, 70) if is_player_1 else (70, 140, 255)
        pygame.draw.rect(screen, border_color, card_rect, 3, border_radius=6)

        # Encabezado 1P / 2P
        header_text = "PLAYER 1" if is_player_1 else ("PLAYER 2" if self.game_mode == MODE_PVP else "COMPUTER")
        header_surf = self.font_header.render(header_text, True, border_color)
        screen.blit(header_surf, (x + 15, y + 15))

        # Retrato grande de personaje
        portrait_rect = pygame.Rect(x + 15, y + 55, card_w - 30, 170)
        pygame.draw.rect(screen, data["color"], portrait_rect)
        pygame.draw.rect(screen, COLOR_WHITE, portrait_rect, 2)

        # Nombre del Profesor
        name_surf = self.font_card.render(data["name"], True, COLOR_YELLOW)
        screen.blit(name_surf, (x + 15, y + 235))

        # País y escenario
        country_str = f"Origen: {loc.get('country', '')} {loc.get('flag', '')}"
        country_surf = self.font_info.render(country_str, True, COLOR_WHITE)
        screen.blit(country_surf, (x + 15, y + 265))

        stage_surf = self.font_info.render(f"Escenario: {loc.get('stage_name', '')[:28]}", True, (180, 200, 240))
        screen.blit(stage_surf, (x + 15, y + 288))

        # Barras de Salud y Velocidad
        hp_lbl = self.font_info.render(f"Salud: {data['health']}", True, COLOR_GREEN)
        screen.blit(hp_lbl, (x + 15, y + 320))
        pygame.draw.rect(screen, (50, 50, 50), (x + 15, y + 342, card_w - 30, 12))
        pygame.draw.rect(screen, COLOR_GREEN, (x + 15, y + 342, int((card_w - 30) * (data['health'] / 120.0)), 12))

        spd_lbl = self.font_info.render(f"Velocidad: {data['speed']}", True, COLOR_YELLOW)
        screen.blit(spd_lbl, (x + 15, y + 365))
        pygame.draw.rect(screen, (50, 50, 50), (x + 15, y + 387, card_w - 30, 12))
        pygame.draw.rect(screen, COLOR_YELLOW, (x + 15, y + 387, int((card_w - 30) * (data['speed'] / 8.0)), 12))

        # Materias
        sub_title = self.font_info.render("Materias:", True, (200, 200, 220))
        screen.blit(sub_title, (x + 15, y + 412))
        for idx, sub in enumerate(data.get("subjects", [])[:3]):
            sub_s = self.font_small.render(f"• {sub}", True, COLOR_WHITE)
            screen.blit(sub_s, (x + 20, y + 432 + idx * 18))

        # Cita / Ataque definitivo
        quote_title = self.font_info.render("Lema de combate:", True, COLOR_YELLOW)
        screen.blit(quote_title, (x + 15, y + 495))
        quote_s = self.font_small.render(f'"{data.get("quote", "")[:35]}"', True, (240, 240, 200))
        screen.blit(quote_s, (x + 15, y + 518))
