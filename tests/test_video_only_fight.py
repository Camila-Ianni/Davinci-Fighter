import os
import unittest

import pygame

from tests.base_headless import HeadlessTestCase
from intro_cutscene import IntroCutscene


class TestVideoOnlyFightAnimation(HeadlessTestCase):
    """Protege la fase de pelea contra recursos que no provienen de Pelea.mov."""

    def test_default_provider_uses_only_canonical_video_frames(self):
        cutscene = IntroCutscene(self.screen)

        self.assertEqual(cutscene.mode, "cache")
        self.assertTrue(cutscene.cache_dir.endswith(os.path.join("assets", "pelea_frames")))
        self.assertEqual(len(cutscene.frame_files), 408)
        self.assertTrue(all(os.path.dirname(path).endswith(os.path.join("assets", "pelea_frames"))
                            for path in cutscene.frame_files))
        self.assertFalse(any(os.path.join("assets", "intro_frames") in path
                             for path in cutscene.frame_files))
        self.assertTrue(all(os.path.basename(path).startswith("frame_")
                            and os.path.basename(path).endswith(".jpg")
                            for path in cutscene.frame_files))

    def test_initial_surface_is_the_first_extracted_fight_frame(self):
        cutscene = IntroCutscene(self.screen)
        expected = pygame.image.load(os.path.join("assets", "pelea_frames", "frame_0000.jpg")).convert()

        self.assertIsNotNone(cutscene.current_surface)
        self.assertEqual(cutscene.current_surface.get_size(), (960, 720))
        self.assertEqual(cutscene.current_surface.get_at((640, 360)), expected.get_at((640, 360)))

    def test_brawl_draw_does_not_use_sprite_or_building_fallback(self):
        cutscene = IntroCutscene(self.screen)
        cutscene.elapsed_time = 14.5
        cutscene.current_surface = None
        cutscene.building_surf = pygame.Surface((960, 720))
        cutscene.building_surf.fill((255, 0, 255))

        self.screen.fill((255, 255, 255))
        cutscene.draw(self.screen)

        self.assertEqual(self.screen.get_at((640, 360))[:3], (0, 0, 0))

    def test_missing_video_frame_never_falls_back_to_intro_frames(self):
        cutscene = IntroCutscene(self.screen)
        cutscene.frame_files = [os.path.join("assets", "pelea_frames", "missing.jpg")]
        cutscene.mode = "cache"
        cutscene.current_surface = None
        cutscene.elapsed_time = 14.5
        cutscene._load_current_brawl_frame()

        self.assertIsNotNone(cutscene.current_surface)
        self.assertEqual(cutscene.current_surface.get_at((640, 360))[:3], (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
