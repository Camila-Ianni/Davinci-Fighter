"""
intro_cutscene.py - Secuencia oficial completa de introducción arcade de Street Fighter II.

Fases continuas (100% fiel al arranque arcade original y Street Fighters.mov):
1. FASE 1 - RAM Diagnostic / Boot Test (0.0s .. 1.8s): Aparecen secuencialmente las comprobaciones:
   SCR 1   RAM OK
   SCR 2   RAM OK
   SCR 3   RAM OK
   OBJECT  RAM OK
   WORK    RAM OK
2. FASE 2 - Title Code & Revision (1.8s .. 3.8s): Fade in suave de opaco a nítido:
   S T R E E T   F I G H T E R   2 '
             9 2 0 5 1 3
               E T C
3. FASE 3 - Warning / Legal Screen (3.8s .. 8.5s):
   Efecto de máquina de escribir de izquierda a derecha (typewriter effect) con el texto legal de advertencia.
4. FASE 4 - Street Brawl Punch Cutscene & Skyscraper Pan a 60 FPS (8.5s .. fin):
   Animación de los luchadores en la calle, golpe certero, paneo por el rascacielos y caída del logotipo.

Soporta salto inmediato (skip) en cualquier momento con ESPACIO, ENTER, ESCAPE o clic de ratón.
"""

import os
import json
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_YELLOW, COLOR_RED, FPS
from sprite_font import get_boot_font, get_warning_font

_CACHED_OPENING_ASSETS = None


class IntroCutscene:
    """
    Motor de reproducción de la secuencia completa de apertura pre-título.
    """
    CANVAS_WIDTH = 1280
    CANVAS_HEIGHT = 720
    TARGET_WIDTH = 960
    TARGET_HEIGHT = 720
    PILLARBOX_WIDTH = 160

    # Fases de la introducción
    PHASE_RAM_CHECK = "ram_check"
    PHASE_TITLE_CODE = "title_code"
    PHASE_WARNING = "warning"
    PHASE_BRAWL = "brawl"
    PHASE_FINISHED = "finished"

    def __init__(
        self,
        screen,
        on_finish=None,
        on_finish_callback=None,
        cache_dir=None,
        video_path=None,
        audio_path=None,
    ):
        self.screen = screen
        self.on_finish = on_finish or on_finish_callback
        self.explicit_cache_dir = cache_dir is not None
        self.explicit_video_path = video_path is not None
        self.explicit_audio_path = audio_path is not None

        self.cache_dir = cache_dir or os.path.join("assets", "intro_frames")
        self.video_path = video_path or os.path.join("assets", "Street Fighters.mov")
        self.audio_path = audio_path or os.path.join("assets", "audio", "intro_cutscene.wav")

        self.screen_width = screen.get_width() if screen else self.CANVAS_WIDTH
        self.screen_height = screen.get_height() if screen else self.CANVAS_HEIGHT
        self.dest_x = (self.screen_width - self.TARGET_WIDTH) // 2
        self.dest_y = (self.screen_height - self.TARGET_HEIGHT) // 2

        # Fuentes Sprite exclusivas para las pantallas iniciales
        self.boot_font = get_boot_font()
        self.warning_font = get_warning_font()

        # Imagen oficial de Title Code & Revision (DAVINCI FIGHTERS 920513 ETC)
        self.title_code_img = None
        davinci_candidates = [
            os.path.join("assets", "fonts", "streetfighter davinci.PNG"),
            os.path.join("assets", "fonts", "streetfighter davinci.png"),
        ]
        for p in davinci_candidates:
            if os.path.exists(p):
                try:
                    raw_img = pygame.image.load(p).convert()
                    self.title_code_img = pygame.transform.smoothscale(raw_img, (self.screen_width, self.screen_height))
                    break
                except Exception as e:
                    print(f"[IntroCutscene] Error cargando title code image: {e}")

        # Fuentes oficiales arcade
        self.arcade_color_font = None
        self.arcade_color_font_small = None
        font_colr_path = os.path.join("assets", "fonts", "super-street-fighter-ii-large-colour", "super-street-fighter-ii-large-colour.colr.ttf")
        if os.path.exists(font_colr_path):
            try:
                self.arcade_color_font = pygame.font.Font(font_colr_path, 34)
                self.arcade_color_font_small = pygame.font.Font(font_colr_path, 22)
            except Exception as e:
                print(f"[IntroCutscene] Error cargando arcade colr font: {e}")

        # Fuentes seguras de Pygame para fallback
        self.font_ram = pygame.font.Font(None, 44)
        self.font_code = pygame.font.Font(None, 48)
        self.font_warn_hdr = pygame.font.Font(None, 46)
        self.font_warn_body = pygame.font.Font(None, 34)

        # Temporizadores y estados
        self.fps = 60.0
        self.dt_accumulator = 0.0
        self.elapsed_time = 0.0
        self.current_frame_idx = 0
        self.total_frames = 0
        self.finished = False
        self.skipped = False

        # Datos de FASE 1: RAM Check (0.0s .. 3.5s)
        self.ram_lines = [
            "SCR 1       RAM OK",
            "SCR 2       RAM OK",
            "SCR 3       RAM OK",
            "OBJECT      RAM OK",
            "WORK        RAM OK",
        ]
        self.ram_line_delay = 0.45

        # Datos de FASE 2: Title Code (3.5s .. 7.5s)
        self.code_lines = [
            "S T R E E T   F I G H T E R   2 '",
            "9 2 0 5 1 3",
            "E T C",
        ]

        # Datos de FASE 3: Warning Screen (7.5s .. 17.5s)
        self.warn_lines = [
            "This game is for use in all countries",
            "excluding the United States of America,",
            "Canada, Mexico and Japan.",
            "Sales, export or operation inside these",
            "countries may be construed as copyright",
            "and trademark infringement and is strictly",
            "prohibited.",
            "Violators are subject to severe penalties",
            "and will be prosecuted to the full extent",
            "of the law.",
        ]

        # Datos de FASE 4: Brawl Cutscene (60 FPS frames) (17.5s .. fin)
        self.frame_files = []
        self.current_surface = None
        self.audio_sound = None
        self._cv2_cap = None
        self._cv2_start_frame = 892

        self.mode = "mock"
        self._init_frame_provider()
        self._init_audio()

    @property
    def is_finished(self):
        return self.finished

    @is_finished.setter
    def is_finished(self, val):
        self.finished = bool(val)

    @property
    def phase(self):
        if self.finished:
            return self.PHASE_FINISHED
        if self.elapsed_time < 3.5:
            return self.PHASE_RAM_CHECK
        elif self.elapsed_time < 7.5:
            return self.PHASE_TITLE_CODE
        elif self.elapsed_time < 14.5:
            return self.PHASE_WARNING
        else:
            return self.PHASE_BRAWL

    def _clean_sprite(self, sheet, rect):
        """Extrae un sprite eliminando fondo teal/blanco mediante flood-fill de bordes y defringing limpio."""
        sub = sheet.subsurface(pygame.Rect(*rect)).copy()
        w, h = sub.get_size()
        surf_alpha = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # 1. Identificar candidatos a fondo (teal o blanco de borde)
        bg_candidates = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                r, g, b, _ = sub.get_at((x, y))
                is_teal = (r <= 45 and 50 <= g <= 140 and 50 <= b <= 140 and abs(g - b) <= 28)
                is_white = (r >= 220 and g >= 220 and b >= 220)
                if is_teal or is_white:
                    bg_candidates[y][x] = True

        # 2. Flood-fill desde todos los bordes exteriores
        is_bg = [[False] * w for _ in range(h)]
        queue = []
        for x in range(w):
            if bg_candidates[0][x]: queue.append((x, 0))
            if bg_candidates[h-1][x]: queue.append((x, h-1))
        for y in range(h):
            if bg_candidates[y][0]: queue.append((0, y))
            if bg_candidates[y][w-1]: queue.append((w-1, y))

        while queue:
            cx, cy = queue.pop(0)
            if is_bg[cy][cx]:
                continue
            is_bg[cy][cx] = True
            for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                if 0 <= nx < w and 0 <= ny < h and not is_bg[ny][nx]:
                    if bg_candidates[ny][nx]:
                        queue.append((nx, ny))

        # 3. Llenar superficie con transparencia
        for y in range(h):
            for x in range(w):
                if is_bg[y][x]:
                    surf_alpha.set_at((x, y), (0, 0, 0, 0))
                else:
                    r, g, b, _ = sub.get_at((x, y))
                    surf_alpha.set_at((x, y), (r, g, b, 255))

        # 4. Defringing de bordes exteriores para halos verdes/teal
        for _ in range(2):
            to_clear = []
            for y in range(h):
                for x in range(w):
                    if surf_alpha.get_at((x, y))[3] == 255:
                        is_border = False
                        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
                            if 0 <= nx < w and 0 <= ny < h and surf_alpha.get_at((nx, ny))[3] == 0:
                                is_border = True
                                break
                        if is_border:
                            r, g, b, _ = sub.get_at((x, y))
                            if (g > r + 12 and b > r + 12 and r < 150) or (r < 50 and g > 40):
                                to_clear.append((x, y))
            for cx, cy in to_clear:
                surf_alpha.set_at((cx, cy), (0, 0, 0, 0))

        return surf_alpha

    def _clean_crowd_frame(self, sheet, rect):
        """Extrae un frame de multitud eliminando el cielo superior y cualquier padding teal inferior."""
        sub = sheet.subsurface(pygame.Rect(*rect)).copy()
        w, h = sub.get_size()
        surf_alpha = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # 1. Identificar candidatos a fondo (teal)
        bg_candidates = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                r, g, b, _ = sub.get_at((x, y))
                is_teal = (r <= 45 and 45 <= g <= 145 and 45 <= b <= 145 and abs(g - b) <= 30)
                if is_teal:
                    bg_candidates[y][x] = True

        # 2. Flood-fill desde bordes superior e inferior
        is_bg = [[False] * w for _ in range(h)]
        queue = []
        for x in range(w):
            for y_edge in range(min(5, h)):
                if bg_candidates[y_edge][x]:
                    queue.append((x, y_edge))
                if bg_candidates[h - 1 - y_edge][x]:
                    queue.append((x, h - 1 - y_edge))
        for y in range(h):
            if bg_candidates[y][0]:
                queue.append((0, y))
            if bg_candidates[y][w - 1]:
                queue.append((w - 1, y))

        while queue:
            cx, cy = queue.pop(0)
            if is_bg[cy][cx]:
                continue
            is_bg[cy][cx] = True
            for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                if 0 <= nx < w and 0 <= ny < h and not is_bg[ny][nx]:
                    if bg_candidates[ny][nx]:
                        queue.append((nx, ny))

        for y in range(h):
            for x in range(w):
                if is_bg[y][x]:
                    surf_alpha.set_at((x, y), (0, 0, 0, 0))
                else:
                    r, g, b, _ = sub.get_at((x, y))
                    surf_alpha.set_at((x, y), (r, g, b, 255))

        # 3. Defringing en bordes superior e inferior
        for _ in range(2):
            to_clear = []
            for y in range(h):
                for x in range(w):
                    if surf_alpha.get_at((x, y))[3] == 255:
                        is_border = False
                        for nx, ny in [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]:
                            if 0 <= nx < w and 0 <= ny < h and surf_alpha.get_at((nx, ny))[3] == 0:
                                is_border = True
                                break
                        if is_border:
                            r, g, b, _ = sub.get_at((x, y))
                            if (g > r + 10 and b > r + 10 and r < 140) or (r < 45 and g > 35):
                                to_clear.append((x, y))
            for cx, cy in to_clear:
                surf_alpha.set_at((cx, cy), (0, 0, 0, 0))

        return surf_alpha

    def _init_opening_assets(self):
        """Inicializa los sprites oficiales de la apertura y el título con caché en memoria."""
        global _CACHED_OPENING_ASSETS
        if _CACHED_OPENING_ASSETS is not None:
            self.building_surf = _CACHED_OPENING_ASSETS["building_surf"]
            self.crowd_frames = _CACHED_OPENING_ASSETS["crowd_frames"]
            self.op_spark = _CACHED_OPENING_ASSETS["op_spark"]
            self.op_blonde_idle = _CACHED_OPENING_ASSETS["op_blonde_idle"]
            self.op_blonde_punch = _CACHED_OPENING_ASSETS["op_blonde_punch"]
            self.op_brown_stance = _CACHED_OPENING_ASSETS["op_brown_stance"]
            self.op_fight_hit = _CACHED_OPENING_ASSETS["op_fight_hit"]
            self.op_brown_fall = _CACHED_OPENING_ASSETS["op_brown_fall"]
            self.logo_title = _CACHED_OPENING_ASSETS.get("logo_title")
            self.banner_sc = _CACHED_OPENING_ASSETS.get("banner_sc")
            self.banner_ed = _CACHED_OPENING_ASSETS.get("banner_ed")
            self.banner_full = _CACHED_OPENING_ASSETS.get("banner_full")
            self.credits_surf = _CACHED_OPENING_ASSETS.get("credits_surf")
            return

        self.building_surf = None
        self.crowd_frames = []
        self.logo_title = None
        self.banner_sc = None
        self.banner_ed = None
        self.banner_full = None
        self.credits_surf = None

        opening_assets_paths = [
            os.path.join("assets", "backgrounds", "opening assets (1).png"),
            os.path.join("assets", "backgrounds", "opening assets.PNG"),
            os.path.join("assets", "backgrounds", "opening assets.png"),
        ]
        chosen_opening_asset = None
        for p in opening_assets_paths:
            if os.path.exists(p):
                chosen_opening_asset = p
                break

        if chosen_opening_asset:
            try:
                # Verificar si la imagen ya tiene canal alfa nativo transparente
                raw_sheet = pygame.image.load(chosen_opening_asset)
                has_native_alpha = (raw_sheet.get_bytesize() == 4) or bool(raw_sheet.get_flags() & pygame.SRCALPHA)
                if has_native_alpha:
                    raw_sheet = raw_sheet.convert_alpha()
                else:
                    raw_sheet = raw_sheet.convert()

                # 1. Edificio completo + Cielo + Cartel DAVINCI FIGHTER II
                building_surf = raw_sheet.subsurface(pygame.Rect(731, 0, 473, 860)).copy()
                
                # 2. Multitud (3 frames de animación limpios y sólidos)
                h_crowd = 446
                if has_native_alpha:
                    crowd_frames = [
                        raw_sheet.subsurface(pygame.Rect(731, 860, 473, 148)).copy(),
                        raw_sheet.subsurface(pygame.Rect(731, 1008, 473, 149)).copy(),
                        raw_sheet.subsurface(pygame.Rect(731, 1157, 473, 149)).copy(),
                    ]
                else:
                    h_sub = int(h_crowd / 3.0)
                    crowd_frames = [
                        self._clean_crowd_frame(raw_sheet, (731, int(860 + i * (h_crowd / 3.0)), 473, h_sub - 10))
                        for i in range(3)
                    ]
                
                # 3. Luchadores y efectos con transparencia limpia
                if has_native_alpha:
                    op_spark = raw_sheet.subsurface(pygame.Rect(184, 663, 57, 57)).copy()
                    op_blonde_idle = raw_sheet.subsurface(pygame.Rect(559, 651, 169, 151)).copy()
                    op_blonde_punch = raw_sheet.subsurface(pygame.Rect(247, 662, 308, 140)).copy()
                    op_brown_stance = raw_sheet.subsurface(pygame.Rect(560, 1143, 168, 145)).copy()
                    op_fight_hit = raw_sheet.subsurface(pygame.Rect(157, 1077, 393, 211)).copy()
                    op_brown_fall = raw_sheet.subsurface(pygame.Rect(0, 1042, 151, 245)).copy()
                else:
                    op_spark = self._clean_sprite(raw_sheet, (184, 663, 57, 57))
                    op_blonde_idle = self._clean_sprite(raw_sheet, (559, 651, 169, 151))
                    op_blonde_punch = self._clean_sprite(raw_sheet, (247, 662, 308, 140))
                    op_brown_stance = self._clean_sprite(raw_sheet, (560, 1143, 168, 145))
                    op_fight_hit = self._clean_sprite(raw_sheet, (157, 1077, 393, 211))
                    op_brown_fall = self._clean_sprite(raw_sheet, (0, 1042, 151, 245))

                # 4. Title assets para las fases de Zoom, Achicar/Agrandar y Textos Animados
                title_logo_path = os.path.join("assets", "title", "logo_davinci_fighters.png")
                banner_sc_path = os.path.join("assets", "title", "banner_special_champion.png")
                banner_ed_path = os.path.join("assets", "title", "banner_edition.png")
                banner_full_path = os.path.join("assets", "title", "banner_full.png")
                credits_path = os.path.join("assets", "title", "credits_block.png")

                logo_title = pygame.image.load(title_logo_path).convert_alpha() if os.path.exists(title_logo_path) else None
                banner_sc = pygame.image.load(banner_sc_path).convert_alpha() if os.path.exists(banner_sc_path) else None
                banner_ed = pygame.image.load(banner_ed_path).convert_alpha() if os.path.exists(banner_ed_path) else None
                banner_full = pygame.image.load(banner_full_path).convert_alpha() if os.path.exists(banner_full_path) else None
                credits_surf = pygame.image.load(credits_path).convert_alpha() if os.path.exists(credits_path) else None

                _CACHED_OPENING_ASSETS = {
                    "building_surf": building_surf,
                    "crowd_frames": crowd_frames,
                    "op_spark": op_spark,
                    "op_blonde_idle": op_blonde_idle,
                    "op_blonde_punch": op_blonde_punch,
                    "op_brown_stance": op_brown_stance,
                    "op_fight_hit": op_fight_hit,
                    "op_brown_fall": op_brown_fall,
                    "logo_title": logo_title,
                    "banner_sc": banner_sc,
                    "banner_ed": banner_ed,
                    "banner_full": banner_full,
                    "credits_surf": credits_surf,
                }
                self.building_surf = building_surf
                self.crowd_frames = crowd_frames
                self.op_spark = op_spark
                self.op_blonde_idle = op_blonde_idle
                self.op_blonde_punch = op_blonde_punch
                self.op_brown_stance = op_brown_stance
                self.op_fight_hit = op_fight_hit
                self.op_brown_fall = op_brown_fall
                self.logo_title = logo_title
                self.banner_sc = banner_sc
                self.banner_ed = banner_ed
                self.banner_full = banner_full
                self.credits_surf = credits_surf
            except Exception as e:
                print(f"[IntroCutscene] Error cargando opening assets: {e}")

    def _init_frame_provider(self):
        """Inicializa el proveedor de frames respetando la jerarquía cache -> cv2 -> mock."""
        self._init_opening_assets()

        # Default en runtime (sin parámetros explícitos): usar el motor de sprites oficial puro
        if not self.explicit_cache_dir and not self.explicit_video_path and self.building_surf is not None:
            self.mode = "assets"
            self.total_frames = int(48.0 * self.fps)
            return

        # 1. Cache de frames pre-extraídos
        if os.path.isdir(self.cache_dir):
            valid_exts = (".jpg", ".jpeg", ".png")
            manifest_path = os.path.join(self.cache_dir, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    total_m = manifest.get("total_frames", 0)
                    if total_m > 0:
                        self.frame_files = [
                            os.path.join(self.cache_dir, f"frame_{i:04d}.jpg")
                            for i in range(total_m)
                        ]
                        self.total_frames = total_m if self.explicit_cache_dir else int(48.0 * self.fps)
                        self.mode = "cache"
                        self._load_current_brawl_frame()
                        return
                except Exception:
                    pass

            files = sorted([
                os.path.join(self.cache_dir, f)
                for f in os.listdir(self.cache_dir)
                if f.lower().endswith(valid_exts)
            ])
            if files:
                self.frame_files = files
                self.total_frames = len(files) if self.explicit_cache_dir else int(48.0 * self.fps)
                self.mode = "cache"
                self._load_current_brawl_frame()
                return

        # 2. Video directo (cv2)
        if self.explicit_video_path:
            video_candidates = [self.video_path]
        else:
            video_candidates = [
                self.video_path,
                os.path.join("assets", "opening video.mov"),
                os.path.join("assets", "Street Fighters.mov"),
            ]
        for vp in video_candidates:
            if vp and os.path.exists(vp):
                try:
                    import cv2
                    self._cv2_cap = cv2.VideoCapture(vp)
                    if self._cv2_cap.isOpened():
                        self.total_frames = 865 if (self.explicit_cache_dir or self.explicit_video_path) else int(48.0 * self.fps)
                        self.mode = "cv2"
                        self._load_current_brawl_frame()
                        return
                except Exception:
                    pass

        # 3. Fallback sintético (mock)
        self.mode = "mock"
        self.total_frames = 180 if (self.explicit_cache_dir or self.explicit_video_path) else int(48.0 * self.fps)
        self._load_current_brawl_frame()

    def _init_audio(self):
        """Inicializa la pista de audio del opening."""
        self._brawl_audio_played = False
        self.audio_sound = None
        if self.explicit_audio_path:
            if self.audio_path and os.path.exists(self.audio_path) and pygame.mixer.get_init():
                try:
                    self.audio_sound = pygame.mixer.Sound(self.audio_path)
                except Exception:
                    self.audio_sound = None
            return

        audio_candidates = [
            os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3"),
            os.path.join("assets", "audio", "Opening Theme.mp3"),
            self.audio_path,
        ]
        for ap in audio_candidates:
            if ap and os.path.exists(ap) and pygame.mixer.get_init():
                try:
                    self.audio_sound = pygame.mixer.Sound(ap)
                    break
                except Exception:
                    self.audio_sound = None

    def _load_current_brawl_frame(self):
        """Carga el frame actual de la fase brawl."""
        if self.mode == "assets":
            return

        if self.mode == "cache" and self.frame_files:
            if self.explicit_cache_dir:
                idx = min(len(self.frame_files) - 1, max(0, self.current_frame_idx))
            else:
                brawl_t = max(0.0, self.elapsed_time - 14.5)
                brawl_fps = 54.02 if len(self.frame_files) == 545 else self.fps
                idx = min(len(self.frame_files) - 1, int(brawl_t * brawl_fps))
            frame_path = self.frame_files[idx]
            if os.path.exists(frame_path):
                try:
                    surf = pygame.image.load(frame_path)
                    if surf.get_size() != (self.TARGET_WIDTH, self.TARGET_HEIGHT):
                        surf = pygame.transform.scale(surf, (self.TARGET_WIDTH, self.TARGET_HEIGHT))
                    self.current_surface = surf
                    return
                except Exception:
                    pass

        if self.mode == "cv2" and self._cv2_cap is not None and self._cv2_cap.isOpened():
            try:
                import cv2
                ret, frame = self._cv2_cap.read()
                if ret:
                    crop = frame[100:2060, 400:3050] if frame.shape[0] > 1000 else frame
                    resized = cv2.resize(
                        crop, (self.TARGET_WIDTH, self.TARGET_HEIGHT), interpolation=cv2.INTER_LINEAR
                    )
                    self.current_surface = pygame.image.frombuffer(
                        resized.tobytes(), (self.TARGET_WIDTH, self.TARGET_HEIGHT), "BGR"
                    )
                    return
                else:
                    self._trigger_finish(skipped=False)
                    return
            except Exception:
                pass

        surf = pygame.Surface((self.TARGET_WIDTH, self.TARGET_HEIGHT))
        surf.fill((10, 15, 30))
        self.current_surface = surf

    def handle_input(self, event) -> str | None:
        """Salto inmediato al presionar cualquier tecla o clic."""
        if self.finished:
            return "finish"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                return self._trigger_finish(skipped=True)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._trigger_finish(skipped=True)

        return None

    def update(self, dt: float = 1.0 / FPS) -> str | None:
        """Actualiza la progresión temporal y avance de frames a 60 FPS."""
        if self.finished:
            return "finish"

        self.elapsed_time += dt
        self.dt_accumulator += dt
        frame_duration = 1.0 / self.fps

        # Iniciar audio del opening en la fase de brawl
        if self.elapsed_time >= 14.5 and not getattr(self, "_brawl_audio_played", False):
            self._brawl_audio_played = True
            audio_paths = [
                os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3"),
                os.path.join("assets", "audio", "Opening Theme.mp3"),
            ]
            played = False
            for ap in audio_paths:
                if os.path.exists(ap) and pygame.mixer.get_init():
                    try:
                        pygame.mixer.music.load(ap)
                        pygame.mixer.music.play()
                        played = True
                        break
                    except Exception:
                        pass
            if not played and self.audio_sound is not None:
                try:
                    self.audio_sound.play()
                except Exception:
                    pass

        advanced = False
        while self.dt_accumulator >= frame_duration:
            self.dt_accumulator -= frame_duration
            self.current_frame_idx += 1
            advanced = True

        if advanced:
            if self.current_frame_idx >= self.total_frames:
                self.current_frame_idx = max(0, self.total_frames - 1)
                return self._trigger_finish(skipped=False)
            elif self.mode != "assets" and hasattr(self, "frame_files") and self.frame_files:
                self._load_current_brawl_frame()

        return None

    def _draw_arcade_text(self, surf, text, center_x, center_y, small=False):
        """Renderiza texto usando la fuente oficial arcade Super Street Fighter II Large Colour."""
        f = self.arcade_color_font_small if small else self.arcade_color_font
        if f is not None:
            txt_surf = f.render(text, True, (255, 255, 255))
            surf.blit(txt_surf, (center_x - txt_surf.get_width() // 2, center_y - txt_surf.get_height() // 2))
        else:
            fb = self.font_warn_body if small else self.font_warn_hdr
            txt_surf = fb.render(text, True, (240, 70, 20))
            surf.blit(txt_surf, (center_x - txt_surf.get_width() // 2, center_y - txt_surf.get_height() // 2))

    def draw(self, screen=None) -> None:
        """Renderiza la pantalla correspondiente a la fase activa según elapsed_time."""
        target = screen if screen is not None else self.screen
        if target is None:
            return

        target.fill((0, 0, 0))
        current_phase = self.phase

        # 1. FASE 1: RAM Check Diagnostic (0.0s .. 3.5s)
        if current_phase == self.PHASE_RAM_CHECK:
            t = self.elapsed_time
            num_lines_visible = min(len(self.ram_lines), int(t / self.ram_line_delay) + 1)
            y_start = 220
            scale = 0.65
            line_height = int(66 * scale) + 10
            
            ref_line = "OBJECT      RAM OK"
            if self.boot_font and self.boot_font.sheet is not None:
                block_w, _ = self.boot_font.get_text_size(ref_line, scale=scale)
            else:
                block_w = 480
            start_x = (self.screen_width - block_w) // 2

            for i in range(num_lines_visible):
                line_str = self.ram_lines[i]
                if self.boot_font and self.boot_font.sheet is not None:
                    self.boot_font.draw_text(target, line_str, start_x, y_start + i * line_height, scale=scale)
                else:
                    parts = line_str.split("RAM OK")
                    left_part = parts[0]
                    surf_left = self.font_ram.render(left_part, True, (230, 190, 50))
                    surf_ok = self.font_ram.render("RAM OK", True, (240, 210, 60))
                    target.blit(surf_left, (start_x, y_start + i * line_height))
                    target.blit(surf_ok, (start_x + int(block_w * 0.65), y_start + i * line_height))

        # 2. FASE 2: Title Code (3.5s .. 7.5s) Fade in de opaco a nítido
        elif current_phase == self.PHASE_TITLE_CODE:
            t = self.elapsed_time - 3.5
            if t < 1.0:
                alpha = int(255 * (t / 1.0))
            elif t < 3.2:
                alpha = 255
            else:
                alpha = max(0, int(255 * (1.0 - (t - 3.2) / 0.8)))

            if self.title_code_img is not None:
                temp_surf = self.title_code_img.copy()
                temp_surf.set_alpha(alpha)
                target.blit(temp_surf, (0, 0))
            else:
                temp_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                y_start = 270
                for i, line_str in enumerate(self.code_lines):
                    txt_surf = self.font_code.render(line_str, True, (65, 115, 240))
                    txt_surf.set_alpha(alpha)
                    temp_surf.blit(txt_surf, (self.screen_width // 2 - txt_surf.get_width() // 2, y_start + i * 52))
                target.blit(temp_surf, (0, 0))

        # 3. FASE 3: Warning Screen (7.5s .. 14.5s) con efecto de máquina de escribir de izq a derecha
        elif current_phase == self.PHASE_WARNING:
            t = self.elapsed_time - 7.5
            chars_typed = int(t * 55.0)
            scale = 0.32
            letter_spacing = 2
            line_height = 38

            if self.warning_font and self.warning_font.sheet is not None:
                max_w = 0
                for line_str in self.warn_lines:
                    lw, _ = self.warning_font.get_text_size(line_str, scale=scale, letter_spacing=letter_spacing)
                    if lw > max_w:
                        max_w = lw
                start_x = self.PILLARBOX_WIDTH + (self.TARGET_WIDTH - max_w) // 2
                hdr_w, _ = self.warning_font.get_text_size("WARNING", scale=scale * 1.2, letter_spacing=letter_spacing)
                self.warning_font.draw_text(target, "WARNING", self.screen_width // 2 - hdr_w // 2, 70, scale=scale * 1.2, letter_spacing=letter_spacing)
            else:
                start_x = self.PILLARBOX_WIDTH + 80
                hdr_surf = self.font_warn_hdr.render("WARNING", True, (245, 170, 40))
                target.blit(hdr_surf, (self.screen_width // 2 - hdr_surf.get_width() // 2, 70))

            remaining_chars = chars_typed
            y_start = 145

            for line_str in self.warn_lines:
                if remaining_chars <= 0:
                    break
                chars_for_this_line = min(len(line_str), remaining_chars)
                visible_text = line_str[:chars_for_this_line]
                remaining_chars -= len(line_str)

                if self.warning_font and self.warning_font.sheet is not None:
                    self.warning_font.draw_text(target, visible_text, start_x, y_start, scale=scale, letter_spacing=letter_spacing)
                else:
                    line_surf = self.font_warn_body.render(visible_text, True, (235, 175, 75))
                    target.blit(line_surf, (start_x, y_start))
                y_start += line_height

        # 4. FASE 4: Brawl, Pan, Zoom, Achicar/Agrandar y Textos Animados (14.5s .. fin)
        elif current_phase == self.PHASE_BRAWL:
            if (self.explicit_cache_dir or self.explicit_video_path) and self.current_surface is not None:
                target.blit(self.current_surface, (self.dest_x, self.dest_y))
            elif getattr(self, "building_surf", None) is not None:
                import math
                t = self.elapsed_time - 14.5
                target_w = self.TARGET_WIDTH
                target_h = self.TARGET_HEIGHT
                
                # Crear superficie de trabajo para la escena arcade (960x720)
                scene_surf = pygame.Surface((target_w, target_h))
                scene_surf.fill((0, 0, 0))

                scale_b = target_w / 473.0
                total_b_h = int(860 * scale_b)
                max_cam_y = total_b_h - target_h

                # Subfase A: Pelea callejera frente a la multitud (0.0 .. 6.0s)
                if t < 6.0:
                    cam_y = max_cam_y
                    scaled_building = pygame.transform.scale(self.building_surf, (target_w, total_b_h))
                    scene_surf.blit(scaled_building, (0, -int(cam_y)))

                    sc_f = scale_b * 1.05

                    # Multitud animada al fondo (extendida al borde inferior)
                    crowd_idx = int(t * 3.5) % 3
                    if 5.2 <= t <= 6.0:
                        crowd_idx = 2  # Brazos arriba celebrando el K.O.
                    if hasattr(self, "crowd_frames") and self.crowd_frames:
                        c_frame = self.crowd_frames[crowd_idx]
                        sc_crowd_h = int(c_frame.get_height() * scale_b)
                        sc_crowd = pygame.transform.scale(c_frame, (target_w, sc_crowd_h))
                        scene_surf.blit(sc_crowd, (0, target_h - sc_crowd_h))

                    # 1. Postura inicial de guardia (Luchador moreno a la IZQUIERDA, rubio a la DERECHA)
                    if t < 4.8:
                        bob = int(math.sin(t * 6.0) * 3)
                        sbr = pygame.transform.scale(self.op_brown_stance, (int(self.op_brown_stance.get_width() * sc_f), int(self.op_brown_stance.get_height() * sc_f)))
                        sb = pygame.transform.scale(self.op_blonde_idle, (int(self.op_blonde_idle.get_width() * sc_f), int(self.op_blonde_idle.get_height() * sc_f)))
                        scene_surf.blit(sbr, (100, target_h - sbr.get_height() + 8 - bob))
                        scene_surf.blit(sb, (540, target_h - sb.get_height() + 8 + bob))
                    # 2. Puñetazo certero de impacto hacia la izquierda (4.8s .. 5.2s)
                    elif t < 5.2:
                        shake_x = (int(t * 50) % 3 - 1) * 4
                        sb_p = pygame.transform.scale(self.op_blonde_punch, (int(self.op_blonde_punch.get_width() * sc_f), int(self.op_blonde_punch.get_height() * sc_f)))
                        sbr_f = pygame.transform.scale(self.op_brown_fall, (int(self.op_brown_fall.get_width() * sc_f), int(self.op_brown_fall.get_height() * sc_f)))
                        scene_surf.blit(sbr_f, (60 + shake_x, target_h - sbr_f.get_height() + 8))
                        scene_surf.blit(sb_p, (240 + shake_x, target_h - sb_p.get_height() + 8))
                        if (int(t * 30) % 2) == 0 and hasattr(self, "op_spark") and self.op_spark is not None:
                            ssp = pygame.transform.scale(self.op_spark, (int(self.op_spark.get_width() * sc_f * 2.2), int(self.op_spark.get_height() * sc_f * 2.2)))
                            scene_surf.blit(ssp, (260 + shake_x, target_h - 260))
                    # 3. Caída del rival hacia la izquierda y celebración (5.2s .. 6.0s)
                    else:
                        fall_prog = (t - 5.2) / 0.8
                        sbr_f = pygame.transform.scale(self.op_brown_fall, (int(self.op_brown_fall.get_width() * sc_f), int(self.op_brown_fall.get_height() * sc_f)))
                        fall_x = 60 - int(fall_prog * 220)
                        fall_y = target_h - sbr_f.get_height() + 8 + int(fall_prog * 130)
                        sb_p = pygame.transform.scale(self.op_blonde_punch, (int(self.op_blonde_punch.get_width() * sc_f), int(self.op_blonde_punch.get_height() * sc_f)))
                        scene_surf.blit(sbr_f, (fall_x, fall_y))
                        scene_surf.blit(sb_p, (240, target_h - sb_p.get_height() + 8))

                    # INSERT COIN parpadeante centrado en pantalla durante la pelea
                    if int(t * 4.0) % 2 == 0:
                        self._draw_arcade_text(scene_surf, "INSERT COIN.", target_w // 2, 540)

                # Subfase B: Paneo por el rascacielos hacia la cima (6.0 .. 9.8s)
                elif t < 9.8:
                    prog = (t - 6.0) / 3.8
                    ease = prog * prog * (3.0 - 2.0 * prog)
                    cam_y = max_cam_y * (1.0 - ease)

                    scaled_building = pygame.transform.scale(self.building_surf, (target_w, total_b_h))
                    scene_surf.blit(scaled_building, (0, -int(cam_y)))

                # Subfase C: Cartel en la cima del rascacielos y Fade to Black suave (9.8 .. 11.4s)
                elif t < 11.4:
                    scaled_building = pygame.transform.scale(self.building_surf, (target_w, total_b_h))
                    scene_surf.blit(scaled_building, (0, 0))

                    if t >= 10.4:
                        fade_black = min(1.0, (t - 10.4) / 1.0)
                        dim = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
                        dim.fill((0, 0, 0, int(255 * fade_black)))
                        scene_surf.blit(dim, (0, 0))

                # Subfase D: Pantalla en negro con solo el título centrado y parpadeo de INSERT COIN (11.4 .. 13.3s)
                elif t < 13.3:
                    scene_surf.fill((0, 0, 0))
                    if getattr(self, "logo_title", None) is not None:
                        lw, lh = 720, int(720 * self.logo_title.get_height() / self.logo_title.get_width())
                        s_logo = pygame.transform.smoothscale(self.logo_title, (lw, lh))
                        scene_surf.blit(s_logo, (target_w // 2 - lw // 2, 170))

                    if int(t * 4.0) % 2 == 0:
                        self._draw_arcade_text(scene_surf, "INSERT COIN.", target_w // 2, 540)

                # Subfase E: Pantalla azul marino de Capcom con título centrado (13.3 .. 13.8s)
                elif t < 13.8:
                    scene_surf.fill((1, 9, 114))
                    if getattr(self, "logo_title", None) is not None:
                        lw, lh = 720, int(720 * self.logo_title.get_height() / self.logo_title.get_width())
                        s_logo = pygame.transform.smoothscale(self.logo_title, (lw, lh))
                        scene_surf.blit(s_logo, (target_w // 2 - lw // 2, 170))

                # Subfase F: El logotipo se achica rápidamente hacia el centro (13.8 .. 14.5s)
                elif t < 14.5:
                    scene_surf.fill((1, 9, 114))
                    prog_s = (t - 13.8) / 0.7
                    sc = max(0.12, 1.0 - 0.88 * (prog_s ** 2))
                    if getattr(self, "logo_title", None) is not None:
                        base_h = int(720 * self.logo_title.get_height() / self.logo_title.get_width())
                        lw, lh = max(1, int(720 * sc)), max(1, int(base_h * sc))
                        s_logo = pygame.transform.smoothscale(self.logo_title, (lw, lh))
                        start_y = 170
                        center_y = target_h // 2 - base_h // 2 - 40
                        curr_y = int(start_y + (center_y - start_y) * prog_s)
                        scene_surf.blit(s_logo, (target_w // 2 - lw // 2, curr_y))

                # Subfase G: El logotipo se agranda y sube mientras vuelan los banners (14.5 .. 16.0s)
                elif t < 16.0:
                    scene_surf.fill((1, 9, 114))

                    # Logotipo agrandándose y subiendo a su posición superior (y = 65)
                    prog_e = (t - 14.5) / 1.5
                    sc = max(0.15, min(1.0, 0.15 + 0.85 * math.sin(min(1.0, prog_e * 1.5) * math.pi / 2.0)))
                    if getattr(self, "logo_title", None) is not None:
                        base_h = int(740 * self.logo_title.get_height() / self.logo_title.get_width())
                        lw, lh = max(1, int(740 * sc)), max(1, int(base_h * sc))
                        s_logo = pygame.transform.smoothscale(self.logo_title, (lw, lh))
                        start_y = target_h // 2 - base_h // 2 - 40
                        target_y = 65
                        curr_y = int(start_y + (target_y - start_y) * min(1.0, prog_e * 1.3))
                        scene_surf.blit(s_logo, (target_w // 2 - lw // 2, curr_y))

                    # Animación auténtica del banner SPECIAL CHAMPION EDITION volando en zig-zag (14.5 .. 16.0s)
                    if getattr(self, "banner_full", None) is not None:
                        w_full = 580
                        h_full = int(w_full * self.banner_full.get_height() / self.banner_full.get_width())
                        s_bfull = pygame.transform.smoothscale(self.banner_full, (w_full, h_full))
                        dest_x = target_w // 2 - w_full // 2
                        y_banner = 310
                        t_b = t - 14.5

                        if t_b < 0.35:
                            # Pase 1: Izquierda a Derecha
                            p = t_b / 0.35
                            curr_bx = int(-w_full + (target_w + w_full) * p)
                        elif t_b < 0.70:
                            # Pase 2: Derecha a Izquierda
                            p = (t_b - 0.35) / 0.35
                            curr_bx = int(target_w - (target_w + w_full) * p)
                        elif t_b < 1.05:
                            # Pase 3: Izquierda a Derecha
                            p = (t_b - 0.70) / 0.35
                            curr_bx = int(-w_full + (target_w + w_full) * p)
                        else:
                            # Pase 4: Derecha hacia el Centro y Slam
                            p = min(1.0, (t_b - 1.05) / 0.45)
                            ease = 1.0 - math.pow(1.0 - p, 3)
                            curr_bx = int(target_w + (dest_x - target_w) * ease)

                        scene_surf.blit(s_bfull, (curr_bx, y_banner))

                        # Destello blanco de impacto al encajar (t = 15.90 .. 16.00)
                        if 15.90 <= t <= 16.00:
                            flash_surf = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
                            flash_surf.fill((255, 255, 255, 180))
                            scene_surf.blit(flash_surf, (0, 0))

                # Subfase H: Créditos rojos, Copyright y Pantalla de Título Oficial (16.0 .. 32.0s)
                else:
                    scene_surf.fill((1, 9, 114))

                    # 1. Logotipo oficial
                    if getattr(self, "logo_title", None) is not None:
                        lw, lh = 740, int(740 * self.logo_title.get_height() / self.logo_title.get_width())
                        s_logo = pygame.transform.smoothscale(self.logo_title, (lw, lh))
                        logo_x = target_w // 2 - lw // 2
                        logo_y = 65
                        scene_surf.blit(s_logo, (logo_x, logo_y))

                    # 2. Banner SPECIAL CHAMPION EDITION encajado
                    if getattr(self, "banner_full", None) is not None:
                        w_full = 580
                        h_full = int(w_full * self.banner_full.get_height() / self.banner_full.get_width())
                        s_bfull = pygame.transform.smoothscale(self.banner_full, (w_full, h_full))
                        scene_surf.blit(s_bfull, (target_w // 2 - w_full // 2, 310))

                    # 3. Textos rojos de créditos y copyright oficiales limpios
                    if getattr(self, "credits_surf", None) is not None:
                        w_cred = 640
                        h_cred = int(w_cred * self.credits_surf.get_height() / self.credits_surf.get_width())
                        s_cred = pygame.transform.smoothscale(self.credits_surf, (w_cred, h_cred))
                        scene_surf.blit(s_cred, (target_w // 2 - w_cred // 2, 395))

                    # 4. Prompt arcade parpadeante oficial
                    if int(t * 4.0) % 2 == 0:
                        self._draw_arcade_text(scene_surf, "PRESS ANY KEY TO START", target_w // 2, 590)

                # Renderizar escena centrada con pillarboxes
                target.blit(scene_surf, (self.dest_x, self.dest_y))
            elif self.current_surface is not None:
                target.blit(self.current_surface, (self.dest_x, self.dest_y))
            else:
                rect = pygame.Rect(self.dest_x, self.dest_y, self.TARGET_WIDTH, self.TARGET_HEIGHT)
                pygame.draw.rect(target, (2, 20, 120), rect)

        # Pillarboxes arcade de 160px a los lados (formato 4:3 en canvas 1280x720)
        pygame.draw.rect(target, (0, 0, 0), (0, 0, self.PILLARBOX_WIDTH, self.CANVAS_HEIGHT))
        pygame.draw.rect(
            target,
            (0, 0, 0),
            (self.screen_width - self.PILLARBOX_WIDTH, 0, self.PILLARBOX_WIDTH, self.CANVAS_HEIGHT),
        )

    def finish(self) -> str:
        """Finaliza inmediatamente toda la secuencia."""
        return self._trigger_finish(skipped=True)

    def _trigger_finish(self, skipped: bool = False) -> str:
        """Detiene recursos y emite la señal de finalización."""
        if not self.finished:
            self.finished = True
            self.skipped = skipped
            if pygame.mixer.get_init():
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
            if self.audio_sound is not None:
                try:
                    self.audio_sound.stop()
                except Exception:
                    pass
                self.audio_sound = None
            if self._cv2_cap is not None:
                try:
                    self._cv2_cap.release()
                except Exception:
                    pass
                self._cv2_cap = None
            if self.on_finish is not None and callable(self.on_finish):
                self.on_finish()
        return "finish"
