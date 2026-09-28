"""
character_select.py - Pantalla oficial de Selección de Personajes estilo Street Fighter II.

Características:
- Renderizado de assets/backgrounds/player select.png (mapa mundial y cuadrícula de 8 casillas).
- Renderizado auténtico de países: en blanco y negro por defecto, y en COLOR al ser seleccionados.
- Reproducción de voz del locutor oficial para cada país desde assets/audio/Sounds/paises/*.mp3:
  al pasar sobre un país (vía teclado o ratón), se reproduce su audio exactamente una vez.
- Retratos de gran tamaño estilo arcade: Jugador 1 a la izquierda y Jugador 2/CPU a la derecha,
  mostrando únicamente la foto del luchador y su nombre, sin tarjetas de estadísticas ni barras de info.
- Soporte para navegación por teclado (WASD, flechas, Enter/Espacio) y selección por ratón (hover y click).
- Modos 1P vs IA (autoselección y bloqueo de IA) y 2P PVP.
"""

import os
import pygame
import numpy as np
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
from arcade_font import get_arcade_font


# Coordenadas y banderas de país para cada profesor en el mapa mundial
# Calculadas con máxima precisión en resolución 1280x720
CHARACTER_LOCATIONS = {
    "carloni": {"country": "JAPÓN", "flag": "🇯🇵", "stage_name": "Database Suzaku Dojo", "map_pos": (702, 165), "country_key": "japan"},
    "cavasso": {"country": "EE. UU.", "flag": "🇺🇸", "stage_name": "Airbase Hangar", "map_pos": (1068, 171), "country_key": "usa"},
    "romero": {"country": "TAILANDIA", "flag": "🇹🇭", "stage_name": "Corporate Ayutthaya Ruins", "map_pos": (620, 272), "country_key": "thailand"},
    "gamaliel": {"country": "BRASIL", "flag": "🇧🇷", "stage_name": "OOP Amazon Basin", "map_pos": (1110, 305), "country_key": "brazil"},
    "sellanes": {"country": "ESPAÑA", "flag": "🇪🇸", "stage_name": "Requirements Palace", "map_pos": (218, 119), "country_key": "spain"},
    "china": {"country": "CHINA", "flag": "🇨🇳", "stage_name": "Corporate Ayutthaya Ruins", "map_pos": (563, 147), "country_key": "china"},
    "ussr": {"country": "U.S.S.R.", "flag": "☭", "stage_name": "Airbase Hangar", "map_pos": (392, 120), "country_key": "ussr"},
    "india": {"country": "INDIA", "flag": "🇮🇳", "stage_name": "Database Suzaku Dojo", "map_pos": (467, 239), "country_key": "india"},
}

# Cuadrícula arcade 2x4 (8 casillas exactamente alineadas con player select.png a 1280x720)
GRID_SLOTS = [
    # Fila 0 (Superior)
    {"char_id": "carloni", "name": "CARLONI", "row": 0, "col": 0, "grid_rect": (408, 449, 115, 95), "country": "japan", "sound": "japan"},
    {"char_id": "cavasso", "name": "CAVASSO", "row": 0, "col": 1, "grid_rect": (523, 449, 116, 95), "country": "usa", "sound": "usa"},
    {"char_id": "romero",  "name": "ROMERO",  "row": 0, "col": 2, "grid_rect": (639, 449, 115, 95), "country": "thailand", "sound": "thailand"},
    {"char_id": "gamaliel","name": "GAMALIEL","row": 0, "col": 3, "grid_rect": (754, 449, 115, 95), "country": "brazil", "sound": "brazil"},
    # Fila 1 (Inferior)
    {"char_id": "sellanes","name": "SELLANES","row": 1, "col": 0, "grid_rect": (408, 544, 115, 96), "country": "spain", "sound": "spain"},
    {"char_id": "carloni", "name": "CHINA",   "row": 1, "col": 1, "grid_rect": (523, 544, 116, 96), "country": "china", "sound": "china"},
    {"char_id": "cavasso", "name": "U.S.S.R.","row": 1, "col": 2, "grid_rect": (639, 544, 115, 96), "country": "ussr", "sound": "ussr"},
    {"char_id": "romero",  "name": "INDIA",   "row": 1, "col": 3, "grid_rect": (754, 544, 115, 96), "country": "india", "sound": "india"},
]

# Rectángulos de banderas y regiones interactivas en la imagen original (1561 x 1007)
RAW_FLAG_RECTS = {
    "spain":    (230, 142, 72, 49),
    "ussr":     (443, 144, 72, 49),
    "china":    (651, 181, 72, 50),
    "japan":    (821, 207, 72, 49),
    "india":    (534, 311, 72, 49),
    "thailand": (721, 356, 72, 49),
    "usa":      (1266, 215, 73, 51),
    "brazil":   (1318, 403, 73, 49),
}

RAW_MAP_REGIONS = {
    "spain":    (200, 125, 150, 110),
    "ussr":     (410, 125, 145, 110),
    "china":    (630, 165, 135, 135),
    "japan":    (780, 190, 155, 110),
    "india":    (515, 295, 135, 105),
    "thailand": (680, 340, 180, 105),
    "usa":      (1220, 200, 155, 110),
    "brazil":   (1260, 390, 175, 110),
}


class CharacterSelect:
    """
    Pantalla arcade de Selección de Personajes con mapa mundial, países dinámicos
    (color/blanco y negro), locutor de audio por país y fotos de los jugadores.
    """
    def __init__(self, screen, game_mode=MODE_PVAI):
        self.screen = screen
        self.game_mode = game_mode
        self.char_keys = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]

        self.font_title = pygame.font.Font(None, 44)
        self.font_header = pygame.font.Font(None, 34)
        self.font_name = pygame.font.Font(None, 38)
        self.font_info = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 18)
        self.arcade_font = get_arcade_font()

        # Selección de casillas (0 a 7 en GRID_SLOTS)
        self.p1_slot_idx = 0
        self.p2_slot_idx = 1
        self.p1_confirmed = False
        self.p2_confirmed = False
        self.transition_timer = 0.0
        self.blink_timer = 0.0

        # Mapeo de país a ranura de la cuadrícula
        self.country_to_slot = {
            "japan": 0,
            "usa": 1,
            "thailand": 2,
            "brazil": 3,
            "spain": 4,
            "china": 5,
            "ussr": 6,
            "india": 7,
        }

        # Cargar y preparar fondos de mapa mundial
        self.bg_color = None
        self.bg_bw = None
        self.color_flags = {}
        self.scaled_flag_rects = {}
        self.scaled_map_regions = {}
        self._init_map_surfaces()

        # Cache de retratos de personajes (fotos de jugadores)
        self.portraits = {}
        self._init_character_portraits()

        # Cargar archivos de audio del locutor para cada país
        self.country_sounds = {}
        self.country_voice_channel = None
        self.audio_enabled = True
        self._init_country_audio()

        # Rastreador del último país anunciado para reproducir el audio sólo una vez
        self.last_spoken_country_p1 = None
        self.last_spoken_country_p2 = None

        # Iniciar música oficial de Character Select
        audio_manager.play_music("character_select", loop=-1)

        # Reproducir el audio del país inicial (Japón) una sola vez
        initial_country = self.get_p1_country()
        self._play_country_audio(initial_country)
        self.last_spoken_country_p1 = initial_country

    @property
    def p1_idx(self):
        return self.p1_slot_idx % len(self.char_keys)

    @p1_idx.setter
    def p1_idx(self, val):
        self.p1_slot_idx = val % len(self.char_keys)

    @property
    def p2_idx(self):
        return self.p2_slot_idx % len(self.char_keys)

    @p2_idx.setter
    def p2_idx(self, val):
        self.p2_slot_idx = val % len(self.char_keys)

    @property
    def p1_char(self):
        return GRID_SLOTS[self.p1_slot_idx]["char_id"]

    @property
    def p2_char(self):
        return GRID_SLOTS[self.p2_slot_idx]["char_id"]

    def get_p1_country(self):
        return GRID_SLOTS[self.p1_slot_idx]["country"]

    def get_p2_country(self):
        return GRID_SLOTS[self.p2_slot_idx]["country"]

    def _init_map_surfaces(self):
        """Escala player select.png y precalcula versiones a color y blanco/negro de las banderas."""
        bg_path = os.path.join("assets", "backgrounds", "player select.png")
        if not os.path.exists(bg_path):
            return

        try:
            try:
                raw_bg = pygame.image.load(bg_path).convert()
            except Exception:
                raw_bg = pygame.image.load(bg_path)

            raw_w, raw_h = raw_bg.get_size()
            sx = SCREEN_WIDTH / float(raw_w)
            sy = SCREEN_HEIGHT / float(raw_h)

            self.bg_color = pygame.transform.scale(raw_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.bg_bw = self.bg_color.copy()

            # Escalar rectángulos y precomputar versiones en blanco y negro
            for country_key, (rx, ry, rw, rh) in RAW_FLAG_RECTS.items():
                rect = pygame.Rect(int(rx * sx), int(ry * sy), int(rw * sx), int(rh * sy))
                self.scaled_flag_rects[country_key] = rect
                
                # Guardar recorte a color
                sub_color = self.bg_color.subsurface(rect).copy()
                self.color_flags[country_key] = sub_color

                # Convertir la bandera en el fondo base a blanco y negro (grayscale)
                sub_bw = self.bg_bw.subsurface(rect)
                arr = pygame.surfarray.pixels3d(sub_bw)
                gray = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.uint8)
                del arr  # Desbloquear superficie antes de blit
                gray_3d = np.stack([gray, gray, gray], axis=2)
                gray_surf = pygame.surfarray.make_surface(gray_3d)
                self.bg_bw.blit(gray_surf, rect.topleft)

            # Escalar regiones interactivas del mapa
            for country_key, (rx, ry, rw, rh) in RAW_MAP_REGIONS.items():
                self.scaled_map_regions[country_key] = pygame.Rect(
                    int(rx * sx), int(ry * sy), int(rw * sx), int(rh * sy)
                )

        except Exception as e:
            print(f"[CharacterSelect] Error inicializando superficies de mapa: {e}")

    def _init_character_portraits(self):
        """Carga las fotos/retratos de gran tamaño de los luchadores."""
        portrait_dir = os.path.join("assets", "characters", "portraits")
        char_ids = ["carloni", "cavasso", "romero", "gamaliel", "sellanes", "china", "ussr", "india", "default"]

        for cid in char_ids:
            # Buscar primero arte personalizado en carpeta del personaje
            custom_path = os.path.join("assets", "characters", cid, "portrait.png")
            alt_path = os.path.join("assets", "characters", cid, "photo.png")
            cached_path = os.path.join(portrait_dir, f"{cid}.png")
            default_path = os.path.join(portrait_dir, "default.png")

            chosen_path = None
            for p in [custom_path, alt_path, cached_path, default_path]:
                if os.path.exists(p):
                    chosen_path = p
                    break

            if chosen_path:
                try:
                    try:
                        surf = pygame.image.load(chosen_path).convert_alpha()
                    except Exception:
                        surf = pygame.image.load(chosen_path)
                    # Escalar al tamaño arcade adecuado para la vista lateral (~260x340)
                    scaled = pygame.transform.scale(surf, (260, 340))
                    self.portraits[cid] = scaled
                except Exception as e:
                    print(f"[CharacterSelect] Error cargando retrato de {cid}: {e}")

    def _init_country_audio(self):
        """Carga los efectos de audio del locutor para cada uno de los 8 países."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                self.audio_enabled = False
                return

        paises_dir = os.path.join("assets", "audio", "Sounds", "paises")
        countries = ["brazil", "china", "india", "japan", "spain", "thailand", "usa", "ussr"]
        
        for c in countries:
            file_path = os.path.join(paises_dir, f"{c}.mp3")
            if os.path.exists(file_path):
                try:
                    sound = pygame.mixer.Sound(file_path)
                    sound.set_volume(0.85)
                    self.country_sounds[c] = sound
                except Exception as e:
                    print(f"[CharacterSelect] Error cargando audio para {c}: {e}")

    def _play_country_audio(self, country_key):
        """Reproduce el audio del locutor para el país seleccionado una sola vez."""
        if not self.audio_enabled or not country_key:
            return
        sound = self.country_sounds.get(country_key)
        if sound:
            try:
                if self.country_voice_channel and self.country_voice_channel.get_busy():
                    self.country_voice_channel.stop()
                self.country_voice_channel = sound.play()
            except Exception as e:
                print(f"[CharacterSelect] Error reproduciendo voz de país {country_key}: {e}")

    def _on_p1_slot_changed(self):
        """Se ejecuta al cambiar de ranura P1: emite SFX de navegación y voz del país si cambia."""
        audio_manager.play_sfx("menu_navigate")
        country = self.get_p1_country()
        if country != self.last_spoken_country_p1:
            self._play_country_audio(country)
            self.last_spoken_country_p1 = country

    def _on_p2_slot_changed(self):
        """Se ejecuta al cambiar de ranura P2 en modo PVP."""
        audio_manager.play_sfx("menu_navigate")
        country = self.get_p2_country()
        if country != self.last_spoken_country_p2:
            self._play_country_audio(country)
            self.last_spoken_country_p2 = country

    def handle_input(self, event):
        """Maneja la navegación por teclado y selección por ratón para P1 y P2."""
        # 1. Movimiento del ratón (Hover sobre países en mapa o casillas de cuadrícula)
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if not self.p1_confirmed:
                # Comprobar si el cursor del ratón pasa sobre un país en el mapa mundial
                for country_key, rect in self.scaled_map_regions.items():
                    if rect.collidepoint(mx, my):
                        slot_target = self.country_to_slot.get(country_key)
                        if slot_target is not None and slot_target != self.p1_slot_idx:
                            self.p1_slot_idx = slot_target
                            self._on_p1_slot_changed()
                        break

                # Comprobar si el cursor del ratón pasa sobre una casilla de la cuadrícula
                for idx, slot in enumerate(GRID_SLOTS):
                    r = pygame.Rect(slot["grid_rect"])
                    if r.collidepoint(mx, my):
                        if idx != self.p1_slot_idx:
                            self.p1_slot_idx = idx
                            self._on_p1_slot_changed()
                        break
            return None

        # 2. Clic del ratón para confirmar
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.p1_confirmed:
                self.p1_confirmed = True
                audio_manager.play_sfx("select")
                if self.game_mode == MODE_PVAI:
                    if self.p2_slot_idx == self.p1_slot_idx:
                        self.p2_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                    self.p2_confirmed = True
                    return {
                        "action": "fight",
                        "action_alt": "vs",
                        "p1_char": self.p1_char,
                        "p2_char": self.p2_char,
                    }
                elif self.p2_confirmed:
                    return {
                        "action": "fight",
                        "action_alt": "vs",
                        "p1_char": self.p1_char,
                        "p2_char": self.p2_char,
                    }
            return None

        # 3. Teclado
        if event.type == pygame.KEYDOWN:
            # Controles de Jugador 1
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
                        self._on_p1_slot_changed()

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

                else:  # MODE_PVP
                    if event.key == pygame.K_a:
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key == pygame.K_d:
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)
                    elif event.key == pygame.K_w:
                        self.p1_slot_idx = (self.p1_slot_idx - 1) % len(self.char_keys)
                    elif event.key == pygame.K_s:
                        self.p1_slot_idx = (self.p1_slot_idx + 1) % len(self.char_keys)

                    if self.p1_slot_idx != prev_slot:
                        self._on_p1_slot_changed()

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

            # Controles de Jugador 2 (Sólo en modo PVP)
            if self.game_mode == MODE_PVP and not self.p2_confirmed:
                prev_p2 = self.p2_slot_idx
                if event.key == pygame.K_LEFT:
                    self.p2_slot_idx = (self.p2_slot_idx - 1) % len(self.char_keys)
                elif event.key == pygame.K_RIGHT:
                    self.p2_slot_idx = (self.p2_slot_idx + 1) % len(self.char_keys)
                elif event.key == pygame.K_UP:
                    self.p2_slot_idx = (self.p2_slot_idx - 1) % len(self.char_keys)
                elif event.key == pygame.K_DOWN:
                    self.p2_slot_idx = (self.p2_slot_idx + 1) % len(self.char_keys)

                if self.p2_slot_idx != prev_p2:
                    self._on_p2_slot_changed()

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

    def update(self, dt=1.0 / FPS):
        """Actualiza animaciones de parpadeo y temporizadores de transición."""
        self.blink_timer += dt

        if self.p1_confirmed and self.p2_confirmed:
            self.transition_timer += dt
            if self.transition_timer >= 0.4:
                return {
                    "action": "vs",
                    "p1_char": self.p1_char,
                    "p2_char": self.p2_char,
                }
        return None

    def draw(self, screen=None):
        """Renderiza la pantalla oficial de selección de personajes."""
        target = screen or self.screen
        if target is None:
            return

        # 1. Fondo del mapa mundial (con países no seleccionados en blanco y negro)
        if self.bg_bw:
            target.blit(self.bg_bw, (0, 0))
        else:
            target.fill(COLOR_BG)

        # 2. Restaurar en COLOR únicamente los países actualmente seleccionados
        p1_country = self.get_p1_country()
        p2_country = self.get_p2_country()

        # Bandera de P1 en color
        if p1_country in self.color_flags and p1_country in self.scaled_flag_rects:
            target.blit(self.color_flags[p1_country], self.scaled_flag_rects[p1_country].topleft)

        # Bandera de P2/CPU en color (si es diferente a P1)
        if p2_country != p1_country and p2_country in self.color_flags and p2_country in self.scaled_flag_rects:
            target.blit(self.color_flags[p2_country], self.scaled_flag_rects[p2_country].topleft)

        # 3. Dibujar soportes/marcos arcade (brackets) sobre las banderas de los países en el mapa
        is_blink_on = (int(self.blink_timer * 6) % 2 == 0)

        # Indicador P1 en el mapa
        if p1_country in self.scaled_flag_rects:
            p1_flag_rect = self.scaled_flag_rects[p1_country]
            p1_bracket_color = (60, 140, 255) if (not self.p1_confirmed or is_blink_on) else (50, 255, 50)
            self._draw_arcade_bracket(target, p1_flag_rect.inflate(14, 12), p1_bracket_color, tag="1P")

        # Indicador P2 / CPU en el mapa
        if p2_country in self.scaled_flag_rects and (p2_country != p1_country or self.game_mode == MODE_PVP):
            p2_flag_rect = self.scaled_flag_rects[p2_country]
            p2_bracket_color = (255, 70, 70) if (not self.p2_confirmed or is_blink_on) else (50, 255, 50)
            p2_tag = "2P" if self.game_mode == MODE_PVP else "CPU"
            # Si ambos coinciden en el mismo país, desplazar ligeramente la etiqueta
            offset_tag = 16 if p2_country == p1_country else 0
            self._draw_arcade_bracket(target, p2_flag_rect.inflate(18, 16), p2_bracket_color, tag=p2_tag, y_offset=offset_tag)

        # 4. Marcos selectores en la cuadrícula de 8 casillas (Bottom Grid)
        for i, slot in enumerate(GRID_SLOTS):
            x, y, w, h = slot["grid_rect"]
            rect = pygame.Rect(x, y, w, h)

            # Selector de Jugador 1 (AZUL / VERDE al confirmar)
            if i == self.p1_slot_idx:
                c1 = (60, 140, 255) if (not self.p1_confirmed or is_blink_on) else (50, 255, 50)
                self._draw_arcade_bracket(target, rect.inflate(8, 8), c1, tag="1P")

            # Selector de Jugador 2 / CPU (ROJO / VERDE al confirmar)
            if i == self.p2_slot_idx:
                c2 = (255, 70, 70) if (not self.p2_confirmed or is_blink_on) else (50, 255, 50)
                tag2 = "2P" if self.game_mode == MODE_PVP else "CPU"
                self._draw_arcade_bracket(target, rect.inflate(14, 14), c2, tag=tag2, y_offset=-18 if i == self.p1_slot_idx else 0)

        # 5. Banner arcade superior derecho ("PUSH START" o información de modo)
        if self.game_mode == MODE_PVAI or not self.p2_confirmed:
            if is_blink_on:
                push_text = "PUSH START"
                if self.arcade_font and self.arcade_font.loaded:
                    self.arcade_font.render_to(target, (SCREEN_WIDTH - 220, 30), push_text, scale=0.9, align="center")
                else:
                    push_s = self.font_header.render(push_text, True, (255, 80, 80))
                    target.blit(push_s, (SCREEN_WIDTH - 220 - push_s.get_width() // 2, 25))

        # 6. Foto del Jugador 1 (Izquierda) - Únicamente la foto y su nombre arriba
        self._draw_player_portrait(target, self.p1_char, is_player_1=True)

        # 7. Foto del Jugador 2 / CPU (Derecha) - Únicamente la foto y su nombre arriba
        self._draw_player_portrait(target, self.p2_char, is_player_1=False)

    def _draw_player_portrait(self, screen, char_id, is_player_1=True):
        """Dibuja la foto del luchador a la izquierda o derecha sin tarjetas de información."""
        data = get_character_data(char_id)
        cid = data.get("id", char_id)

        # Obtener retrato cargado o por defecto
        portrait_surf = self.portraits.get(cid) or self.portraits.get("default")

        # Dimensiones y posición
        pw, ph = 260, 340
        y = SCREEN_HEIGHT - ph

        if is_player_1:
            x = 35
            # P1 mira hacia la derecha
            if portrait_surf:
                screen.blit(portrait_surf, (x, y))
            else:
                # Fallback con el color del luchador
                pygame.draw.rect(screen, data.get("color", (40, 140, 220)), (x, y, pw, ph), border_radius=6)

            # Nombre de P1 en tipografía arcade SF2 encima de la foto
            display_name = GRID_SLOTS[self.p1_slot_idx]["name"]
            if self.arcade_font and self.arcade_font.loaded:
                self.arcade_font.render_to(screen, (x + pw // 2, y - 44), display_name, scale=0.9, align="center")
            else:
                s_sh = self.font_name.render(display_name, True, (0, 0, 0))
                s_fg = self.font_name.render(display_name, True, COLOR_YELLOW)
                screen.blit(s_sh, (x + pw // 2 - s_sh.get_width() // 2 + 2, y - 42))
                screen.blit(s_fg, (x + pw // 2 - s_fg.get_width() // 2, y - 44))

        else:
            x = SCREEN_WIDTH - pw - 35
            # P2 mira hacia la izquierda (volteado horizontalmente)
            if portrait_surf:
                flipped = pygame.transform.flip(portrait_surf, True, False)
                screen.blit(flipped, (x, y))
            else:
                pygame.draw.rect(screen, data.get("color", (220, 50, 50)), (x, y, pw, ph), border_radius=6)

            display_name = GRID_SLOTS[self.p2_slot_idx]["name"]
            if self.arcade_font and self.arcade_font.loaded:
                self.arcade_font.render_to(screen, (x + pw // 2, y - 44), display_name, scale=0.9, align="center")
            else:
                s_sh = self.font_name.render(display_name, True, (0, 0, 0))
                s_fg = self.font_name.render(display_name, True, COLOR_YELLOW)
                screen.blit(s_sh, (x + pw // 2 - s_sh.get_width() // 2 + 2, y - 42))
                screen.blit(s_fg, (x + pw // 2 - s_fg.get_width() // 2, y - 44))

    def _draw_arcade_bracket(self, target, rect, color, tag="1P", y_offset=0):
        """Dibuja esquinas de selección arcade (brackets en 4 esquinas) y etiqueta de jugador."""
        x, y, w, h = rect
        lw = min(14, w // 4)
        th = 3

        # Esquina superior izquierda
        pygame.draw.line(target, color, (x, y), (x + lw, y), th)
        pygame.draw.line(target, color, (x, y), (x, y + lw), th)

        # Esquina superior derecha
        pygame.draw.line(target, color, (x + w, y), (x + w - lw, y), th)
        pygame.draw.line(target, color, (x + w, y), (x + w, y + lw), th)

        # Esquina inferior izquierda
        pygame.draw.line(target, color, (x, y + h), (x + lw, y + h), th)
        pygame.draw.line(target, color, (x, y + h), (x, y + h - lw), th)

        # Esquina inferior derecha
        pygame.draw.line(target, color, (x + w, y + h), (x + w - lw, y + h), th)
        pygame.draw.line(target, color, (x + w, y + h), (x + w, y + h - lw), th)

        # Etiqueta "1P" / "2P" / "CPU"
        if tag:
            lbl = self.font_small.render(tag, True, color)
            target.blit(lbl, (x + w // 2 - lbl.get_width() // 2, y - 18 + y_offset))
