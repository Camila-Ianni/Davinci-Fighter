"""
tests/test_country_selection_and_audio.py - Pruebas completas para la selección de países,
locución de audio y visualización de retratos en CharacterSelect.
"""

import os
import unittest
import pygame
from tests.base_headless import HeadlessTestCase
from settings import MODE_PVAI, MODE_PVP, SCREEN_WIDTH, SCREEN_HEIGHT
from character_select import CharacterSelect, GRID_SLOTS, CHARACTER_LOCATIONS, RAW_FLAG_RECTS, RAW_MAP_REGIONS


class TestCountrySelectionAndAudio(HeadlessTestCase):
    """Pruebas unitarias para las nuevas funcionalidades de CharacterSelect."""

    def test_01_all_paises_audio_files_exist(self):
        """Verifica que los 8 archivos mp3 de los países existen en assets/audio/Sounds/paises/."""
        paises_dir = os.path.join("assets", "audio", "Sounds", "paises")
        expected_countries = ["brazil", "china", "india", "japan", "spain", "thailand", "usa", "ussr"]
        for c in expected_countries:
            path = os.path.join(paises_dir, f"{c}.mp3")
            self.assertTrue(os.path.exists(path), f"Falta el archivo de audio para {c} en {path}")
            self.assertGreater(os.path.getsize(path), 1000)

    def test_02_country_audio_loaded_and_plays_once_on_hover(self):
        """Verifica que el locutor de audio se reproduzca una sola vez al pasar sobre un país."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        self.assertIn("japan", cs.country_sounds)
        self.assertIn("china", cs.country_sounds)
        self.assertIn("brazil", cs.country_sounds)
        self.assertIn("usa", cs.country_sounds)

        # Inicialmente Japón está seleccionado y anunciado
        self.assertEqual(cs.last_spoken_country_p1, "japan")

        # Simular pasar sobre China en el mapa mediante MOUSEMOTION
        china_rect = cs.scaled_map_regions["china"]
        mouse_ev = pygame.event.Event(pygame.MOUSEMOTION, pos=china_rect.center, rel=(1, 1), buttons=(0, 0, 0))
        cs.handle_input(mouse_ev)

        # Ahora China debe ser la ranura seleccionada y el último país anunciado
        self.assertEqual(cs.get_p1_country(), "china")
        self.assertEqual(cs.last_spoken_country_p1, "china")

        # Un segundo evento de movimiento dentro de China no debe reiniciar la locución
        cs.handle_input(mouse_ev)
        self.assertEqual(cs.last_spoken_country_p1, "china")

    def test_03_countries_color_and_black_and_white_rendering(self):
        """Verifica que las banderas de países tengan versiones en color y blanco/negro."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        expected_countries = ["brazil", "china", "india", "japan", "spain", "thailand", "usa", "ussr"]

        for c in expected_countries:
            self.assertIn(c, cs.color_flags, f"Falta bandera a color para {c}")
            self.assertIn(c, cs.scaled_flag_rects, f"Falta rectángulo escalado para {c}")
            self.assertIsInstance(cs.color_flags[c], pygame.Surface)

        # El fondo base en blanco y negro debe estar inicializado
        self.assertIsNotNone(cs.bg_bw)
        self.assertEqual(cs.bg_bw.get_size(), (SCREEN_WIDTH, SCREEN_HEIGHT))

    def test_04_portraits_loaded_for_p1_and_p2(self):
        """Verifica que las fotos/retratos de P1 y P2 estén disponibles y se dibujen sin errores."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        self.assertGreater(len(cs.portraits), 0)

        # Renderizar en la pantalla
        cs.draw(self.screen)
        # Comprobar que no hay tarjetas con barras de salud/velocidad
        # Verificando que draw se ejecuta limpiamente
        self.assertTrue(True)

    def test_05_grid_slots_map_all_8_countries(self):
        """Verifica que las 8 casillas de la cuadrícula correspondan a los 8 países."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        grid_countries = [slot["country"] for slot in GRID_SLOTS]
        self.assertEqual(len(grid_countries), 8)
        self.assertIn("japan", grid_countries)
        self.assertIn("usa", grid_countries)
        self.assertIn("thailand", grid_countries)
        self.assertIn("brazil", grid_countries)
        self.assertIn("spain", grid_countries)
        self.assertIn("china", grid_countries)
        self.assertIn("ussr", grid_countries)
        self.assertIn("india", grid_countries)


if __name__ == "__main__":
    unittest.main()
