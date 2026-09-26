"""
stage_manager.py - Gestor de escenarios de combate de Street Fighter II y Da Vinci Fighters.
Soporta:
- Carga y ensamble de los 5 escenarios oficiales a partir de los assets Sega Genesis en assets/backgrounds/.
- Mundo expandido a STAGE_WIDTH = 2200 px con soporte para desplazamiento horizontal de cámara (camera_x).
- Público y personajes de fondo 100% animados con colorkey de transparencia (186, 254, 202).
"""

import os
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y, COLOR_GROUND_LINE

STAGE_WIDTH = 2200       # Ancho total del escenario en coordenadas de mundo
STAGE_HEIGHT = 720       # Alto del escenario
SPRITE_KEY_COLOR = (186, 254, 202)  # Color verde menta de fondo de los sprite sheets


class BackgroundCharacter:
    """
    Personaje o elemento animado del público de fondo (espectadores, aldeanos, monjes).
    """
    def __init__(self, frames, world_x, world_y, anim_speed=0.15, scale=2.8):
        self.frames = []
        for f in frames:
            w, h = f.get_size()
            scaled = pygame.transform.scale(f, (int(w * scale), int(h * scale)))
            self.frames.append(scaled)
        
        self.world_x = world_x
        self.world_y = world_y
        self.anim_speed = anim_speed
        self.current_frame = 0.0

    def update(self, dt=1.0 / 60.0):
        if self.frames:
            self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)

    def draw(self, screen, camera_x=0):
        if not self.frames:
            return
        frame_idx = int(self.current_frame) % len(self.frames)
        surf = self.frames[frame_idx]
        screen_x = int(self.world_x - camera_x)
        if -surf.get_width() <= screen_x <= SCREEN_WIDTH:
            screen.blit(surf, (screen_x, self.world_y))


class Stage:
    """
    Escenario de combate de Street Fighter II con base recortada y escalada a 2200x720,
    con público animado sobrepuesto y soporte para scrolling de cámara.
    """
    def __init__(self, name, sheet_file, crop_rect, crowd_defs=None):
        self.name = name
        self.sheet_file = sheet_file
        self.crop_rect = crop_rect
        self.crowd_defs = crowd_defs or []
        self.surface = None
        self.crowd_characters = []
        self._loaded = False

    def load(self):
        """Carga y ensambla el escenario limpio y sus personajes de público animados."""
        if self._loaded and self.surface:
            return

        path = os.path.join("assets", "backgrounds", self.sheet_file)
        if os.path.exists(path):
            try:
                sheet = pygame.image.load(path)
                if pygame.display.get_surface():
                    sheet = sheet.convert()

                # 1. Recortar la escena base limpia
                cropped = sheet.subsurface(self.crop_rect)
                self.surface = pygame.transform.scale(cropped, (STAGE_WIDTH, STAGE_HEIGHT))

                # 2. Extraer sprites del público animado
                self.crowd_characters = []
                for (world_x, world_y, rect_list, speed, scale) in self.crowd_defs:
                    frames = []
                    for rect in rect_list:
                        # Verificar límites dentro del sheet
                        if (rect[0] + rect[2] <= sheet.get_width() and 
                            rect[1] + rect[3] <= sheet.get_height()):
                            f = sheet.subsurface(rect).copy()
                            f.set_colorkey(SPRITE_KEY_COLOR)
                            frames.append(f)
                    if frames:
                        bg_char = BackgroundCharacter(frames, world_x, world_y, speed, scale)
                        self.crowd_characters.append(bg_char)

                self._loaded = True
            except Exception as e:
                print(f"[Stage] Error cargando escenario {self.sheet_file}: {e}")

    def update(self, dt=1.0 / 60.0):
        """Actualiza las animaciones del público del escenario."""
        for bg_char in self.crowd_characters:
            bg_char.update(dt)

    def draw(self, screen, camera_x=0):
        """Renderiza el fondo expandido y el público aplicando el desplazamiento horizontal de la cámara."""
        if not self._loaded:
            self.load()

        if self.surface:
            screen.blit(self.surface, (int(-camera_x), 0))
        else:
            screen.fill((30, 30, 45))

        # Dibujar público animado sobre el fondo
        for bg_char in self.crowd_characters:
            bg_char.draw(screen, camera_x)


class StageManager:
    """
    Gestor de escenarios de los 5 profesores con recortes y animaciones de fondo fieles.
    """
    def __init__(self):
        self.stages = {}
        self._init_stages()

    def _init_stages(self):
        # 1. Carloni - Ryu Stage (Castillo Suzaku, Japón)
        self.stages["carloni"] = Stage(
            name="Carloni Database Dojo (Japan)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Ryu Stage.png",
            crop_rect=(4, 196, 504, 216),
            crowd_defs=[]
        )

        # 2. Cavasso - Guile Stage (Base Aérea con Avión y Mecánicos, USA)
        # Espectadores animándose en la pista del hangar
        self.stages["cavasso"] = Stage(
            name="Cavasso Mobile Airbase (USA)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Guile Stage.png",
            crop_rect=(4, 388, 512, 224),
            crowd_defs=[
                # Soldado animado 1 (izquierda)
                (320, 260, [(4, 204, 48, 96), (60, 204, 48, 96), (116, 204, 48, 96)], 0.12, 2.6),
                # Soldado animado 2 (centro-izquierda)
                (550, 270, [(172, 204, 48, 96), (228, 204, 48, 96)], 0.15, 2.5),
                # Oficial / Espectador 3 (centro-derecha)
                (1450, 265, [(284, 204, 48, 96), (340, 204, 48, 96)], 0.14, 2.5),
                # Espectador 4 (derecha)
                (1780, 260, [(396, 204, 46, 96), (452, 204, 44, 96)], 0.10, 2.6),
            ]
        )

        # 3. Romero - Sagat Stage (Ruinas de Ayutthaya con Buda reclinado, Tailandia)
        self.stages["romero"] = Stage(
            name="Romero Corporate Ruins (Thailand)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Sagat Stage.png",
            crop_rect=(8, 224, 512, 224),
            crowd_defs=[]
        )

        # 4. Gamaliel - Blanka Stage (Cuenca del Amazonas con aldeanos y serpiente, Brasil)
        self.stages["gamaliel"] = Stage(
            name="Gamaliel OOP Amazon River (Brazil)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - Blanka Stage.png",
            crop_rect=(8, 240, 512, 216),
            crowd_defs=[
                # Aldeano saltando / animado 1
                (420, 290, [(8, 878, 26, 82), (48, 878, 41, 82)], 0.14, 2.6),
                # Aldeano 2
                (700, 295, [(96, 878, 35, 82), (144, 878, 24, 82)], 0.12, 2.5),
                # Aldeano 3
                (1520, 290, [(176, 878, 48, 82), (232, 878, 36, 82)], 0.16, 2.5),
                # Aldeano 4
                (1820, 295, [(280, 878, 24, 82), (48, 878, 41, 82)], 0.11, 2.6),
            ]
        )

        # 5. Sellanes - M. Bison Stage (Templo Real de Tailandia, Bells & Statues)
        self.stages["sellanes"] = Stage(
            name="Sellanes Requirements Palace (Thailand)",
            sheet_file="Sega Genesis - Street Fighter 2_ Special Champion Edition - Stages - M. Bison Stage.png",
            crop_rect=(8, 880, 512, 224),
            crowd_defs=[
                # Monje / estatua dorada izquierda
                (460, 280, [(8, 184, 24, 168), (40, 184, 24, 168)], 0.08, 2.2),
                # Monje / estatua dorada derecha
                (1680, 280, [(65, 184, 23, 168), (96, 184, 32, 168)], 0.08, 2.2),
            ]
        )

    def get_stage_for_character(self, char_id):
        """Retorna el escenario recortado correspondiente al personaje."""
        stage = self.stages.get(char_id, self.stages["carloni"])
        stage.load()
        return stage


# Instancia global del gestor de escenarios
stage_manager = StageManager()
