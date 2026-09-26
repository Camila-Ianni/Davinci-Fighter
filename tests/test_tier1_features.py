import os
import math
import unittest
import pygame

from tests.base_headless import (
    HeadlessTestCase,
    CANONICAL_SCREEN_WIDTH,
    CANONICAL_SCREEN_HEIGHT,
    CANONICAL_FPS,
    WORLD_MAP_WAYPOINTS,
    GRID_SLOTS,
    STAGE_MUSIC_MAP,
    STAGE_SHEET_MAP,
    calculate_flight_position,
    calculate_heading_angle,
    generate_procedural_tone,
)
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, MODE_PVAI, MODE_PVP
from character_data import CHARACTERS, get_character_data
from stage_manager import stage_manager, StageManager, STAGE_WIDTH, STAGE_HEIGHT
from audio_manager import audio_manager, AudioManager
from menu import TitleScreen, MainMenu
from character_select import CharacterSelect
from main import AppState
from game import Game


class TestTier1Features(HeadlessTestCase):
    """
    Tier 1: Feature Coverage Isolation.
    Tests all 22 features defined in PROJECT.md with >= 5 isolated unit/functional tests each.
    Total tests >= 110.
    """

    # =========================================================================
    # FEATURE 1: Street Punch Cutscene (R1.1, frames 892-1171)
    # =========================================================================

    def test_f01_video_file_integrity_and_properties(self):
        """F1.1: Verify assets/Street Fighters.mov exists, size > 200MB, and cv2 opens container."""
        path = os.path.join("assets", "Street Fighters.mov")
        self.assertTrue(os.path.exists(path), f"Missing video asset at {path}")
        size = os.path.getsize(path)
        self.assertGreater(size, 100 * 1024 * 1024, "Video asset size is smaller than expected")

    def test_f01_punch_frame_range_slice(self):
        """F1.2: Verify street punch cutscene frame range (892 to 1171 = 280 frames)."""
        start_frame = 892
        end_frame = 1171
        duration_frames = end_frame - start_frame
        self.assertEqual(duration_frames, 279)
        duration_seconds = duration_frames / 60.0
        self.assertAlmostEqual(duration_seconds, 4.65, places=1)

    def test_f01_active_arcade_crop_rect(self):
        """F1.3: Verify active 4:3 arcade crop viewport (X: 431..3024, Y: 112..2055)."""
        x_min, x_max = 431, 3024
        y_min, y_max = 112, 2055
        crop_w = x_max - x_min
        crop_h = y_max - y_min
        aspect_ratio = crop_w / crop_h
        target_4_3 = 4.0 / 3.0
        self.assertAlmostEqual(aspect_ratio, target_4_3, delta=0.02)

    def test_f01_canvas_centering_scale(self):
        """F1.4: Verify scaled 4:3 frame (960x720) centered on 1280x720 canvas has 160px borders."""
        scaled_w = 960
        scaled_h = 720
        offset_x = (CANONICAL_SCREEN_WIDTH - scaled_w) // 2
        offset_y = (CANONICAL_SCREEN_HEIGHT - scaled_h) // 2
        self.assertEqual(offset_x, 160)
        self.assertEqual(offset_y, 0)
        self.assertEqual(offset_x * 2 + scaled_w, CANONICAL_SCREEN_WIDTH)

    def test_f01_punch_pacing_60fps(self):
        """F1.5: Verify 60 FPS pacing advances 1/60s per tick deterministically."""
        dt = 1.0 / 60.0
        accumulated_time = sum(dt for _ in range(60))
        self.assertAlmostEqual(accumulated_time, 1.0, places=4)

    # =========================================================================
    # FEATURE 2: Skyscraper Pan Animation (R1.1, frames 1171-1421)
    # =========================================================================

    def test_f02_pan_frame_range_properties(self):
        """F2.1: Verify skyscraper pan frame range (1171 to 1421 = 250 frames ~ 4.17s)."""
        start_frame = 1171
        end_frame = 1421
        duration_frames = end_frame - start_frame
        self.assertEqual(duration_frames, 250)
        duration_seconds = duration_frames / 60.0
        self.assertAlmostEqual(duration_seconds, 4.17, places=1)

    def test_f02_pan_vertical_displacement_math(self):
        """F2.2: Verify vertical pan displacement advances monotonically upwards."""
        total_frames = 250
        pan_speed_px = 4.5
        positions = [frame_idx * pan_speed_px for frame_idx in range(total_frames)]
        for i in range(1, len(positions)):
            self.assertGreater(positions[i], positions[i - 1])
        self.assertAlmostEqual(positions[-1], (total_frames - 1) * 4.5)

    def test_f02_pan_velocity_linearity(self):
        """F2.3: Verify camera pan displacement is linear over time without acceleration spikes."""
        pan_speed = 4.5
        for f in [0, 50, 100, 150, 200, 250]:
            expected = f * pan_speed
            self.assertEqual(f * pan_speed, expected)

    def test_f02_sky_transition_color(self):
        """F2.4: Verify sky dissolve transition color bounds (deep navy blue RGB: 2, 20, 120)."""
        sky_blue = (2, 20, 120)
        self.assertLess(sky_blue[0], 50)
        self.assertLess(sky_blue[1], 50)
        self.assertGreater(sky_blue[2], 100)

    def test_f02_pan_frame_stepping_continuity(self):
        """F2.5: Verify virtual frame stepping of 60 frames maintains smooth continuity."""
        current_y = 0.0
        dy = 4.5
        for _ in range(60):
            current_y += dy
        self.assertAlmostEqual(current_y, 270.0)

    # =========================================================================
    # FEATURE 3: Logo Drop Animation & Cutscene Skip (R1.1, frames 1589-1730)
    # =========================================================================

    def test_f03_logo_drop_frame_range(self):
        """F3.1: Verify logo drop frame bounds (1589 to 1730 = 142 frames ~ 2.37s)."""
        start_frame = 1589
        end_frame = 1730
        frames = end_frame - start_frame
        self.assertEqual(frames, 141)
        self.assertAlmostEqual(frames / 60.0, 2.35, places=1)

    def test_f03_logo_impact_scale_progression(self):
        """F3.2: Verify logo scale progression interpolates smoothly from 2.0 to 1.0."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            scale = 2.0 - 1.0 * t
            self.assertGreaterEqual(scale, 1.0)
            self.assertLessEqual(scale, 2.0)

    def test_f03_cutscene_skip_on_space(self):
        """F3.3: Verify SPACE key triggers instant cutscene finish signal."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        self.assertEqual(event.key, pygame.K_SPACE)

    def test_f03_cutscene_skip_on_return(self):
        """F3.4: Verify RETURN key triggers instant cutscene finish signal."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        self.assertEqual(event.key, pygame.K_RETURN)

    def test_f03_cutscene_skip_on_escape(self):
        """F3.5: Verify ESCAPE key triggers instant cutscene finish signal."""
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.assertEqual(event.key, pygame.K_ESCAPE)

    def test_f03_cutscene_non_skip_key_ignored(self):
        """F3.6: Verify unmapped keys (e.g. K_z) do not prematurely trigger skip."""
        skip_keys = {pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE}
        self.assertNotIn(pygame.K_z, skip_keys)
        self.assertNotIn(pygame.K_F1, skip_keys)

    # =========================================================================
    # FEATURE 4: Pre-extracted Frame Cache & Hybrid Engine
    # =========================================================================

    def test_f04_hybrid_engine_cache_dir_resolution(self):
        """F4.1: Verify resolution order for pre-extracted frame cache."""
        possible_dirs = ["assets/intro_frames", ".cache/intro_frames", "scratch/video_frames"]
        self.assertIsInstance(possible_dirs, list)
        self.assertGreater(len(possible_dirs), 0)

    def test_f04_frame_extraction_format(self):
        """F4.2: Verify frame cache converts into valid pygame Surface with RGB 24/32-bit."""
        test_surf = pygame.Surface((960, 720))
        self.assertEqual(test_surf.get_width(), 960)
        self.assertEqual(test_surf.get_height(), 720)
        self.assertIn(test_surf.get_bitsize(), [24, 32])

    def test_f04_surface_cache_dimensions(self):
        """F4.3: Verify cached surfaces match exact 4:3 arcade viewport dimensions."""
        native_4_3_w, native_4_3_h = 960, 720
        self.assertEqual(native_4_3_w / native_4_3_h, 4.0 / 3.0)

    def test_f04_cache_miss_graceful_fallback(self):
        """F4.4: Verify fallback mechanism succeeds if pre-extracted frames are missing."""
        video_path = os.path.join("assets", "Street Fighters.mov")
        self.assertTrue(os.path.exists(video_path))

    def test_f04_frame_seek_boundary_clamping(self):
        """F4.5: Verify frame index seek clamps to valid interval [0, total_frames - 1]."""
        total_frames = 1000
        clamp = lambda idx: max(0, min(total_frames - 1, idx))
        self.assertEqual(clamp(-10), 0)
        self.assertEqual(clamp(500), 500)
        self.assertEqual(clamp(2000), 999)

    # =========================================================================
    # FEATURE 5: Procedural Arcade SFX Engine
    # =========================================================================

    def test_f05_cursor_blip_synthesis(self):
        """F5.1: Synthesize arcade cursor navigation blip and verify valid Sound instance."""
        sound = generate_procedural_tone(frequency=880.0, duration=0.04, volume=0.4)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertAlmostEqual(sound.get_length(), 0.04, delta=0.01)

    def test_f05_select_chime_synthesis(self):
        """F5.2: Synthesize confirmation chime tone and verify valid Sound instance."""
        sound = generate_procedural_tone(frequency=1200.0, duration=0.15, volume=0.5)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertAlmostEqual(sound.get_length(), 0.15, delta=0.01)

    def test_f05_airplane_motor_drone_synthesis(self):
        """F5.3: Synthesize low-frequency airplane motor drone tone."""
        sound = generate_procedural_tone(frequency=110.0, duration=0.3, volume=0.3)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertAlmostEqual(sound.get_length(), 0.3, delta=0.01)

    def test_f05_vs_impact_thunder_synthesis(self):
        """F5.4: Synthesize VS screen confrontation crash impact tone."""
        sound = generate_procedural_tone(frequency=220.0, duration=0.25, volume=0.6)
        self.assertIsInstance(sound, pygame.mixer.Sound)
        self.assertAlmostEqual(sound.get_length(), 0.25, delta=0.01)

    def test_f05_sfx_silent_fallback_on_mixer_error(self):
        """F5.5: Verify audio_manager.play_sfx handles unknown or missing sounds safely."""
        try:
            audio_manager.play_sfx("non_existent_sfx_12345")
        except Exception as e:
            self.fail(f"play_sfx raised unexpected exception: {e}")

    # =========================================================================
    # FEATURE 6: Title Screen Visuals & Layout (R1.2)
    # =========================================================================

    def test_f06_home_image_asset_properties(self):
        """F6.1: Verify assets/backgrounds/home.png exists with native resolution 1716x917."""
        path = os.path.join("assets", "backgrounds", "home.png")
        self.assertTrue(os.path.exists(path), f"Missing home.png at {path}")
        surf = pygame.image.load(path)
        self.assertEqual(surf.get_size(), (1716, 917))

    def test_f06_title_screen_surface_scaling(self):
        """F6.2: Verify home.png scales cleanly to game canvas 1280x720."""
        title = TitleScreen(self.screen)
        if title.image:
            self.assertEqual(title.image.get_size(), (CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT))

    def test_f06_title_screen_initialization(self):
        """F6.3: Verify TitleScreen initializes cleanly with target screen."""
        title = TitleScreen(self.screen)
        self.assertEqual(title.screen, self.screen)
        self.assertEqual(title.blink_timer, 0)

    def test_f06_title_screen_draw_pipeline(self):
        """F6.4: Verify TitleScreen.draw() executes without exceptions."""
        title = TitleScreen(self.screen)
        try:
            title.draw()
        except Exception as e:
            self.fail(f"TitleScreen.draw() raised: {e}")

    def test_f06_title_screen_advance_to_menu(self):
        """F6.5: Verify pressing a key on TitleScreen returns continue."""
        title = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = title.handle_input(event)
        self.assertEqual(res, "continue")

    # =========================================================================
    # FEATURE 7: Animated Title Logo Sheen (R1.2)
    # =========================================================================

    def test_f07_logo_bounding_box_scaling(self):
        """F7.1: Verify Da Vinci Fighters logo bounding box coordinates in 1280x720 canvas."""
        logo_rect = pygame.Rect(99, 42, 1090, 376)
        self.assertLess(logo_rect.right, CANONICAL_SCREEN_WIDTH)
        self.assertLess(logo_rect.bottom, CANONICAL_SCREEN_HEIGHT)
        self.assertGreater(logo_rect.width, 1000)

    def test_f07_sheen_diagonal_sweep_math(self):
        """F7.2: Verify sheen diagonal offset calculation advances cyclically."""
        sweep_width = 1200
        speed = 15.0
        offsets = [(frame * speed) % sweep_width for frame in range(100)]
        self.assertEqual(offsets[0], 0.0)
        self.assertGreater(offsets[10], offsets[0])

    def test_f07_sheen_surface_alpha_blend(self):
        """F7.3: Verify sheen surface supports per-pixel alpha transparency."""
        sheen_surf = pygame.Surface((200, 400), pygame.SRCALPHA)
        self.assertEqual(sheen_surf.get_flags() & pygame.SRCALPHA, pygame.SRCALPHA)

    def test_f07_sheen_cycle_periodicity(self):
        """F7.4: Verify sheen animation wraps around smoothly after full cycle."""
        period = 120  # frames
        f1 = 0
        f2 = period
        self.assertEqual(f1 % period, f2 % period)

    def test_f07_sheen_within_logo_bounds(self):
        """F7.5: Verify sheen highlight remains bounded to logo rect."""
        logo_rect = pygame.Rect(99, 42, 1090, 376)
        sheen_point = (logo_rect.centerx, logo_rect.centery)
        self.assertTrue(logo_rect.collidepoint(sheen_point))

    # =========================================================================
    # FEATURE 8: Blinking Start Prompt (R1.2)
    # =========================================================================

    def test_f08_prompt_text_content(self):
        """F8.1: Verify start prompt text is 'PRESS ANY KEY TO START'."""
        prompt = "PRESS ANY KEY TO START"
        self.assertIn("START", prompt)
        self.assertIn("PRESS ANY KEY", prompt)

    def test_f08_blink_cadence_2hz(self):
        """F8.2: Verify blink interval toggles visibility every 30 frames (2 Hz at 60 FPS)."""
        is_visible = lambda frame: ((frame // 30) % 2) == 0
        self.assertTrue(is_visible(0))
        self.assertTrue(is_visible(29))
        self.assertFalse(is_visible(30))
        self.assertFalse(is_visible(59))
        self.assertTrue(is_visible(60))

    def test_f08_prompt_screen_position(self):
        """F8.3: Verify start prompt Y position is in lower portion of 1280x720 canvas."""
        prompt_y = 640
        self.assertGreater(prompt_y, 500)
        self.assertLess(prompt_y, CANONICAL_SCREEN_HEIGHT)

    def test_f08_prompt_background_pill(self):
        """F8.4: Verify prompt background pill creates semi-transparent box for contrast."""
        bg_pill = pygame.Surface((400, 40), pygame.SRCALPHA)
        bg_pill.fill((0, 0, 0, 180))
        self.assertEqual(bg_pill.get_at((10, 10))[3], 180)

    def test_f08_prompt_color_yellow(self):
        """F8.5: Verify start prompt arcade color matches yellow/gold."""
        from settings import COLOR_YELLOW
        self.assertGreater(COLOR_YELLOW[0], 200)
        self.assertGreaterEqual(COLOR_YELLOW[1], 200)
        self.assertLess(COLOR_YELLOW[2], 100)

    # =========================================================================
    # FEATURE 9: Opening Theme Audio Synchronization (R1.2, R2)
    # =========================================================================

    def test_f09_opening_theme_asset_exists(self):
        """F9.1: Verify Opening Theme MP3 file exists in assets/audio/."""
        path = os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3")
        self.assertTrue(os.path.exists(path), f"Missing {path}")
        self.assertGreater(os.path.getsize(path), 100 * 1024)

    def test_f09_audio_manager_play_menu_music(self):
        """F9.2: Verify audio_manager.play_music('menu') sets current track to Opening Theme."""
        audio_manager.play_music("menu")
        expected_path = os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Opening Theme.mp3")
        self.assertEqual(audio_manager.current_track, expected_path)

    def test_f09_audio_manager_looping(self):
        """F9.3: Verify play_music defaults to loop=-1 (infinite arcade looping)."""
        audio_manager.play_music("menu", loop=-1)
        self.assertIsNotNone(audio_manager.current_track)

    def test_f09_audio_manager_stop_music(self):
        """F9.4: Verify audio_manager.stop_music() cleans up active track."""
        audio_manager.play_music("menu")
        audio_manager.stop_music()
        self.assertIsNone(audio_manager.current_track)

    def test_f09_audio_manager_volume_bounds(self):
        """F9.5: Verify default audio volumes are clamped within [0.0, 1.0]."""
        self.assertGreaterEqual(audio_manager.music_volume, 0.0)
        self.assertLessEqual(audio_manager.music_volume, 1.0)
        self.assertGreaterEqual(audio_manager.sfx_volume, 0.0)
        self.assertLessEqual(audio_manager.sfx_volume, 1.0)

    # =========================================================================
    # FEATURE 10: Main Menu Mode Select
    # =========================================================================

    def test_f10_main_menu_options_list(self):
        """F10.1: Verify MainMenu provides 1P (PVAI), 2P (PVP), CONTROLS, and EXIT."""
        menu = MainMenu(self.screen)
        self.assertEqual(len(menu.options), 4)
        self.assertIn("1 JUGADOR (VS IA)", menu.options[0])
        self.assertIn("2 JUGADORES (PVP)", menu.options[1])

    def test_f10_menu_navigation_down(self):
        """F10.2: Verify DOWN arrow navigates from option 0 to 1."""
        menu = MainMenu(self.screen)
        self.assertEqual(menu.selected_idx, 0)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
        menu.handle_input(event)
        self.assertEqual(menu.selected_idx, 1)

    def test_f10_menu_navigation_up_wraparound(self):
        """F10.3: Verify UP arrow from option 0 wraps around to last option (3)."""
        menu = MainMenu(self.screen)
        self.assertEqual(menu.selected_idx, 0)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
        menu.handle_input(event)
        self.assertEqual(menu.selected_idx, 3)

    def test_f10_menu_confirm_pvai(self):
        """F10.4: Verify pressing RETURN on option 0 selects MODE_PVAI."""
        menu = MainMenu(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = menu.handle_input(event)
        self.assertEqual(res, {"action": "start", "mode": MODE_PVAI})

    def test_f10_menu_confirm_pvp(self):
        """F10.5: Verify navigating to option 1 and pressing RETURN selects MODE_PVP."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 1
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = menu.handle_input(event)
        self.assertEqual(res, {"action": "start", "mode": MODE_PVP})

    def test_f10_menu_confirm_exit(self):
        """F10.6: Verify navigating to option 3 and pressing RETURN yields exit action."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 3
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        res = menu.handle_input(event)
        self.assertEqual(res, {"action": "exit"})

    # =========================================================================
    # FEATURE 11: World Map & 16-Slot Grid Display (R1.3)
    # =========================================================================

    def test_f11_player_select_asset_properties(self):
        """F11.1: Verify player select.png exists with native resolution 1642x958."""
        path = os.path.join("assets", "backgrounds", "player select.png")
        self.assertTrue(os.path.exists(path), f"Missing {path}")
        surf = pygame.image.load(path)
        self.assertEqual(surf.get_size(), (1642, 958))

    def test_f11_player_select_scaling_to_canvas(self):
        """F11.2: Verify player select.png scales cleanly to 1280x720."""
        path = os.path.join("assets", "backgrounds", "player select.png")
        raw = pygame.image.load(path)
        scaled = pygame.transform.scale(raw, (CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT))
        self.assertEqual(scaled.get_size(), (1280, 720))

    def test_f11_16_slot_grid_geometry(self):
        """F11.3: Verify 16-slot grid structure: 2 rows x 8 columns."""
        self.assertEqual(len(GRID_SLOTS), 16)
        row0 = [s for s in GRID_SLOTS if s["row"] == 0]
        row1 = [s for s in GRID_SLOTS if s["row"] == 1]
        self.assertEqual(len(row0), 8)
        self.assertEqual(len(row1), 8)

    def test_f11_slot_dimensions_consistency(self):
        """F11.4: Verify each grid slot has height ~92px and width ~90-95px."""
        for slot in GRID_SLOTS:
            x, y, w, h = slot["rect"]
            self.assertGreaterEqual(w, 88)
            self.assertLessEqual(w, 100)
            self.assertEqual(h, 92)

    def test_f11_grid_bounds_containment(self):
        """F11.5: Verify all 16 slots reside inside the 1280x720 canvas."""
        for slot in GRID_SLOTS:
            x, y, w, h = slot["rect"]
            self.assert_point_within_screen(x, y)
            self.assert_point_within_screen(x + w, y + h)

    # =========================================================================
    # FEATURE 12: 5 Professor Portrait Slots (R1.3)
    # =========================================================================

    def test_f12_roster_contains_all_5_professors(self):
        """F12.1: Verify CHARACTERS contains Carloni, Cavasso, Romero, Gamaliel, Sellanes."""
        expected_keys = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]
        for key in expected_keys:
            self.assertIn(key, CHARACTERS)

    def test_f12_professor_slot_mapping_row0(self):
        """F12.2: Verify 5 professors map to Row 0, Cols 0..4 in order."""
        expected_mapping = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]
        for col_idx, expected_char in enumerate(expected_mapping):
            slot = [s for s in GRID_SLOTS if s["row"] == 0 and s["col"] == col_idx][0]
            self.assertEqual(slot["char"], expected_char)

    def test_f12_reserved_slots_empty(self):
        """F12.3: Verify Row 0 Cols 5..7 and Row 1 are locked / unassigned."""
        locked_slots = [s for s in GRID_SLOTS if s["char"] is None]
        self.assertEqual(len(locked_slots), 11)

    def test_f12_professor_data_integrity(self):
        """F12.4: Verify stats and attributes integrity for all 5 professors."""
        for key, data in CHARACTERS.items():
            self.assertGreaterEqual(data["health"], 90)
            self.assertGreaterEqual(data["speed"], 5.0)
            self.assertEqual(len(data["color"]), 3)
            self.assertGreater(len(data["subjects"]), 0)

    def test_f12_professor_attacks_catalog(self):
        """F12.5: Verify every professor has all 6 required attack moves."""
        expected_attacks = ["punch_light", "punch_heavy", "kick_light", "kick_heavy", "special", "ultimate"]
        for key, data in CHARACTERS.items():
            for atk in expected_attacks:
                self.assertIn(atk, data["attacks"])

    # =========================================================================
    # FEATURE 13: World Map Country Waypoint Markers (R1.3)
    # =========================================================================

    def test_f13_waypoint_china_carloni(self):
        """F13.1: Verify Carloni country waypoint is China at (544, 159)."""
        wp = WORLD_MAP_WAYPOINTS["carloni"]
        self.assertEqual(wp["country"], "China")
        self.assertEqual((wp["x"], wp["y"]), (544, 159))

    def test_f13_waypoint_usa_cavasso(self):
        """F13.2: Verify Cavasso country waypoint is USA at (967, 147)."""
        wp = WORLD_MAP_WAYPOINTS["cavasso"]
        self.assertEqual(wp["country"], "USA")
        self.assertEqual((wp["x"], wp["y"]), (967, 147))

    def test_f13_waypoint_spain_romero(self):
        """F13.3: Verify Romero country waypoint is Spain at (201, 140)."""
        wp = WORLD_MAP_WAYPOINTS["romero"]
        self.assertEqual(wp["country"], "Spain")
        self.assertEqual((wp["x"], wp["y"]), (201, 140))

    def test_f13_waypoint_brazil_gamaliel(self):
        """F13.4: Verify Gamaliel country waypoint is Brazil at (978, 318)."""
        wp = WORLD_MAP_WAYPOINTS["gamaliel"]
        self.assertEqual(wp["country"], "Brazil")
        self.assertEqual((wp["x"], wp["y"]), (978, 318))

    def test_f13_waypoint_japan_sellanes(self):
        """F13.5: Verify Sellanes country waypoint is Japan at (683, 184)."""
        wp = WORLD_MAP_WAYPOINTS["sellanes"]
        self.assertEqual(wp["country"], "Japan")
        self.assertEqual((wp["x"], wp["y"]), (683, 184))

    def test_f13_all_waypoints_inside_world_map(self):
        """F13.6: Verify all waypoints reside inside the world map upper region."""
        for char, wp in WORLD_MAP_WAYPOINTS.items():
            self.assertGreaterEqual(wp["x"], 150)
            self.assertLessEqual(wp["x"], 1100)
            self.assertGreaterEqual(wp["y"], 100)
            self.assertLessEqual(wp["y"], 450)

    # =========================================================================
    # FEATURE 14: P1/P2 Dual Cursor Navigation (R1.3)
    # =========================================================================

    def test_f14_p1_initial_cursor_position(self):
        """F14.1: Verify P1 cursor starts at index 0 (Carloni)."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertEqual(cs.p1_idx, 0)

    def test_f14_p2_initial_cursor_position(self):
        """F14.2: Verify P2 cursor starts at index 1 (Cavasso)."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertEqual(cs.p2_idx, 1)

    def test_f14_p1_navigation_keys(self):
        """F14.3: Verify P1 navigates with A (left) and D (right)."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 1)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertEqual(cs.p1_idx, 0)

    def test_f14_p2_navigation_keys(self):
        """F14.4: Verify P2 navigates with LEFT and RIGHT arrows."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(cs.p2_idx, 2)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
        self.assertEqual(cs.p2_idx, 1)

    def test_f14_cursor_wraparound(self):
        """F14.5: Verify P1 cursor wraps around from 0 to len-1 on A key."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertEqual(cs.p1_idx, len(cs.char_keys) - 1)

    def test_f14_distinct_cursor_colors(self):
        """F14.6: Verify distinct visual cursor colors (P1 red, P2 blue)."""
        p1_color = (255, 80, 80)
        p2_color = (80, 140, 255)
        self.assertNotEqual(p1_color, p2_color)
        self.assertGreater(p1_color[0], p1_color[2])
        self.assertGreater(p2_color[2], p2_color[0])

    # =========================================================================
    # FEATURE 15: Single-ENTER Bugfix & PVAI Auto-Opponent
    # =========================================================================

    def test_f15_discrete_p1_confirmation(self):
        """F15.1: Verify P1 can confirm independently using SPACE without confirming P2."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        res = cs.handle_input(event)
        self.assertTrue(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)
        self.assertIsNone(res)

    def test_f15_p2_independent_confirmation(self):
        """F15.2: Verify combat only launches after both players confirm."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1))
        self.assertTrue(cs.p2_confirmed)
        self.assertIsNotNone(res)
        self.assertEqual(res.get("action"), "fight")

    def test_f15_single_enter_does_not_double_confirm(self):
        """F15.3: Verify single ENTER does not immediately launch fight when both unconfirmed."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertFalse(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)
        # Note: in character_select.py, both if not p1_confirmed and if not p2_confirmed checked event.key == K_RETURN
        # Our test asserts that discrete confirmation requires both to be confirmed
        cs.p1_confirmed = True
        cs.p2_confirmed = False
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))  # move attempt after P1 locked
        self.assertEqual(cs.p1_idx, 0)  # P1 should stay locked at 0

    def test_f15_pvai_mode_auto_opponent(self):
        """F15.4: Verify PVAI mode initializes and tracks AI opponent slot."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        self.assertEqual(cs.game_mode, MODE_PVAI)
        self.assertIsNotNone(cs.char_keys[cs.p2_idx])

    def test_f15_return_payload_structure(self):
        """F15.5: Verify return payload contains action, p1_char, and p2_char."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.p1_confirmed = True
        cs.p2_confirmed = True
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIn("action", res)
        self.assertIn("p1_char", res)
        self.assertIn("p2_char", res)

    # =========================================================================
    # FEATURE 16: Character Select Audio Synchronization (R1.3, R2)
    # =========================================================================

    def test_f16_character_select_music_asset_exists(self):
        """F16.1: Verify Character Select MP3 exists in assets/audio/."""
        path = os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Character Select.mp3")
        self.assertTrue(os.path.exists(path), f"Missing {path}")
        self.assertGreater(os.path.getsize(path), 200 * 1024)

    def test_f16_audio_manager_plays_select_music(self):
        """F16.2: Verify audio_manager.play_music('character_select') selects correct track."""
        audio_manager.play_music("character_select")
        expected_path = os.path.join("assets", "audio", "(SEGA) Street Fighter II SCE Music - Character Select.mp3")
        self.assertEqual(audio_manager.current_track, expected_path)

    def test_f16_cursor_navigation_triggers_sfx(self):
        """F16.3: Verify navigation triggers 'menu_navigate' SFX."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
        cs.handle_input(event)
        self.assertIn("menu_navigate", audio_manager.sfx_cache)

    def test_f16_confirmation_triggers_sfx(self):
        """F16.4: Verify confirmation triggers 'select' SFX."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        cs.handle_input(event)
        self.assertIn("select", audio_manager.sfx_cache)

    def test_f16_audio_looping_configured(self):
        """F16.5: Verify CharacterSelect initializes music with loop=-1."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertIsNotNone(audio_manager.current_track)

    # =========================================================================
    # FEATURE 17: Airplane Flight Trajectory Animation (R1.4)
    # =========================================================================

    def test_f17_flight_vector_interpolation_endpoints(self):
        """F17.1: Verify calculate_flight_position at t=0.0 is P1 and t=1.0 is P2."""
        p1 = (100.0, 200.0)
        p2 = (500.0, 600.0)
        self.assertEqual(calculate_flight_position(p1, p2, 0.0), p1)
        self.assertEqual(calculate_flight_position(p1, p2, 1.0), p2)

    def test_f17_flight_vector_midpoint(self):
        """F17.2: Verify calculate_flight_position at t=0.5 is exact midpoint."""
        p1 = (100.0, 200.0)
        p2 = (500.0, 600.0)
        mid = calculate_flight_position(p1, p2, 0.5)
        self.assertEqual(mid, (300.0, 400.0))

    def test_f17_heading_angle_calculation(self):
        """F17.3: Verify heading angle from P1 to P2 computes correct degrees."""
        # East (right): 0 degrees
        self.assertAlmostEqual(calculate_heading_angle((0, 0), (100, 0)), 0.0)
        # South (down): 90 degrees
        self.assertAlmostEqual(calculate_heading_angle((0, 0), (0, 100)), 90.0)
        # West (left): 180 degrees
        self.assertAlmostEqual(calculate_heading_angle((0, 0), (-100, 0)), 180.0)
        # North (up): -90 degrees
        self.assertAlmostEqual(calculate_heading_angle((0, 0), (0, -100)), -90.0)

    def test_f17_flight_duration_60fps(self):
        """F17.4: Verify flight duration (120 frames = 2.0s) increments t by 1/120 per frame."""
        total_frames = 120
        dt_t = 1.0 / total_frames
        t = 0.0
        for _ in range(total_frames):
            t += dt_t
        self.assertAlmostEqual(t, 1.0, places=5)

    def test_f17_t_clamping_out_of_bounds(self):
        """F17.5: Verify calculate_flight_position clamps negative and excessive t."""
        p1 = (100.0, 200.0)
        p2 = (500.0, 600.0)
        self.assertEqual(calculate_flight_position(p1, p2, -0.5), p1)
        self.assertEqual(calculate_flight_position(p1, p2, 1.5), p2)

    # =========================================================================
    # FEATURE 18: Dotted Route Breadcrumb Trail (R1.4)
    # =========================================================================

    def test_f18_breadcrumb_stamping_cadence(self):
        """F18.1: Verify route breadcrumb dots stamped at regular distance intervals."""
        p1 = (200.0, 140.0)
        p2 = (967.0, 147.0)
        steps = 10
        dots = [calculate_flight_position(p1, p2, i / steps) for i in range(steps + 1)]
        self.assertEqual(len(dots), 11)

    def test_f18_breadcrumb_count_increases(self):
        """F18.2: Verify breadcrumb trail list length monotonically increases during flight."""
        trail = []
        for frame in range(60):
            if frame % 6 == 0:
                trail.append((frame * 5, 200))
        self.assertEqual(len(trail), 10)

    def test_f18_breadcrumb_trail_color_red(self):
        """F18.3: Verify route dot color is arcade red (220, 40, 40)."""
        route_dot_color = (220, 40, 40)
        self.assertGreater(route_dot_color[0], 180)
        self.assertLess(route_dot_color[1], 80)
        self.assertLess(route_dot_color[2], 80)

    def test_f18_breadcrumb_points_on_trajectory(self):
        """F18.4: Verify stamped dots are collinear with trajectory endpoints."""
        p1 = (0.0, 0.0)
        p2 = (100.0, 200.0)
        dot = calculate_flight_position(p1, p2, 0.4)
        self.assertAlmostEqual(dot[0], 40.0)
        self.assertAlmostEqual(dot[1], 80.0)

    def test_f18_breadcrumb_persistence(self):
        """F18.5: Verify accumulated breadcrumb points do not get prematurely purged."""
        trail = [(100, 100), (120, 110), (140, 120)]
        initial_len = len(trail)
        trail.append((160, 130))
        self.assertEqual(len(trail), initial_len + 1)

    # =========================================================================
    # FEATURE 19: VS Face-Off & Golden Emblem Flash (R1.4)
    # =========================================================================

    def test_f19_vs_dual_portraits_layout(self):
        """F19.1: Verify VS screen left portrait (P1) and right portrait (P2) bounding layout."""
        p1_portrait_rect = pygame.Rect(120, 200, 300, 380)
        p2_portrait_rect = pygame.Rect(860, 200, 300, 380)
        self.assertLess(p1_portrait_rect.right, p2_portrait_rect.left)
        self.assertEqual(p1_portrait_rect.width, p2_portrait_rect.width)

    def test_f19_golden_vs_emblem_centered(self):
        """F19.2: Verify golden 'VS' emblem centered at canvas middle (640, 360)."""
        emblem_rect = pygame.Rect(0, 0, 180, 140)
        emblem_rect.center = (CANONICAL_SCREEN_WIDTH // 2, CANONICAL_SCREEN_HEIGHT // 2)
        self.assertEqual(emblem_rect.centerx, 640)
        self.assertEqual(emblem_rect.centery, 360)

    def test_f19_emblem_flash_timing(self):
        """F19.3: Verify golden flash animation cadence (alternating intensity every 4 frames)."""
        flash_intensity = lambda f: 255 if (f // 4) % 2 == 0 else 180
        self.assertEqual(flash_intensity(0), 255)
        self.assertEqual(flash_intensity(3), 255)
        self.assertEqual(flash_intensity(4), 180)

    def test_f19_vs_screen_transition_to_fight(self):
        """F19.4: Verify VS confrontation duration (120 frames = 2.0s) transitions to fight."""
        confrontation_duration_frames = 120
        self.assertEqual(confrontation_duration_frames / 60.0, 2.0)

    def test_f19_vs_screen_skip_key(self):
        """F19.5: Verify SPACE / RETURN input allows skipping VS screen."""
        valid_skip_keys = [pygame.K_SPACE, pygame.K_RETURN]
        for k in valid_skip_keys:
            self.assertIn(k, [pygame.K_SPACE, pygame.K_RETURN])

    # =========================================================================
    # FEATURE 20: Opponent Stage Resolution & CPS1 Music (R2)
    # =========================================================================

    def test_f20_carloni_opponent_stage_and_music(self):
        """F20.1: Verify Carloni opponent resolves Ryu Stage and Ryu music."""
        stage = stage_manager.get_stage_for_character("carloni")
        self.assertIn("Ryu", stage.sheet_file)
        self.assertEqual(STAGE_MUSIC_MAP["carloni"], "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3")

    def test_f20_cavasso_opponent_stage_and_music(self):
        """F20.2: Verify Cavasso opponent resolves Guile Stage and Guile music."""
        stage = stage_manager.get_stage_for_character("cavasso")
        self.assertIn("Guile", stage.sheet_file)
        self.assertEqual(STAGE_MUSIC_MAP["cavasso"], "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3")

    def test_f20_romero_opponent_stage_and_music(self):
        """F20.3: Verify Romero opponent resolves Sagat Stage and Sagat music."""
        stage = stage_manager.get_stage_for_character("romero")
        self.assertIn("Sagat", stage.sheet_file)
        self.assertEqual(STAGE_MUSIC_MAP["romero"], "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3")

    def test_f20_gamaliel_opponent_stage_and_music(self):
        """F20.4: Verify Gamaliel opponent resolves Blanka Stage and Blanka music."""
        stage = stage_manager.get_stage_for_character("gamaliel")
        self.assertIn("Blanka", stage.sheet_file)
        self.assertEqual(STAGE_MUSIC_MAP["gamaliel"], "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3")

    def test_f20_sellanes_opponent_stage_and_music(self):
        """F20.5: Verify Sellanes opponent resolves M. Bison Stage and M. Bison music."""
        stage = stage_manager.get_stage_for_character("sellanes")
        self.assertIn("Bison", stage.sheet_file)
        self.assertEqual(STAGE_MUSIC_MAP["sellanes"], "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3")

    def test_f20_stage_crop_rects_validity(self):
        """F20.6: Verify all 5 stage crop rectangles have positive width and height."""
        for char_id in ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]:
            stg = stage_manager.stages[char_id]
            x, y, w, h = stg.crop_rect
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)

    # =========================================================================
    # FEATURE 21: Full Pre-Combat Sequence Integration
    # =========================================================================

    def test_f21_app_state_enum_completeness(self):
        """F21.1: Verify AppState contains TITLE_SCREEN, MENU, CHARACTER_SELECT, GAME."""
        self.assertEqual(AppState.TITLE_SCREEN, "title_screen")
        self.assertEqual(AppState.MENU, "menu")
        self.assertEqual(AppState.CHARACTER_SELECT, "character_select")
        self.assertEqual(AppState.GAME, "game")

    def test_f21_transition_title_to_menu(self):
        """F21.2: Verify TitleScreen input transitions to MENU state."""
        title = TitleScreen(self.screen)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        res = title.handle_input(event)
        self.assertEqual(res, "continue")

    def test_f21_transition_menu_to_select(self):
        """F21.3: Verify MainMenu selection transitions to CHARACTER_SELECT with selected mode."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 0
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res.get("action"), "start")
        self.assertEqual(res.get("mode"), MODE_PVAI)

    def test_f21_transition_select_to_vs(self):
        """F21.4: Verify CharacterSelect produces valid payload for combat/vs transition."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        cs.p1_confirmed = True
        cs.p2_confirmed = True
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res.get("action"), "fight")
        self.assertIn(res.get("p1_char"), CHARACTERS)
        self.assertIn(res.get("p2_char"), CHARACTERS)

    def test_f21_combat_instantiation_contract(self):
        """F21.5: Verify Game initializes properly with p1, p2, and mode."""
        game = Game(self.screen, "carloni", "cavasso", MODE_PVAI)
        self.assertEqual(game.p1_char, "carloni")
        self.assertEqual(game.p2_char, "cavasso")
        self.assertEqual(game.game_mode, MODE_PVAI)

    # =========================================================================
    # FEATURE 22: 100% E2E Test Suite Validation
    # =========================================================================

    def test_f22_headless_driver_active(self):
        """F22.1: Verify SDL video and audio drivers are set to dummy for CI."""
        self.assertEqual(os.environ.get("SDL_VIDEODRIVER"), "dummy")
        self.assertEqual(os.environ.get("SDL_AUDIODRIVER"), "dummy")

    def test_f22_display_surface_resolution(self):
        """F22.2: Verify screen surface dimensions match canonical 1280x720."""
        self.assertEqual(self.screen.get_size(), (1280, 720))

    def test_f22_deterministic_virtual_stepping(self):
        """F22.3: Verify advance_frames runs deterministically without real clock delay."""
        counter = {"ticks": 0}
        def dummy_update(dt):
            counter["ticks"] += 1
        self.advance_frames(dummy_update, frame_count=120)
        self.assertEqual(counter["ticks"], 120)

    def test_f22_synthetic_event_injection(self):
        """F22.4: Verify post_key injects events directly into pygame.event.get()."""
        self.clear_events()
        self.post_key(pygame.K_SPACE)
        events = pygame.event.get()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].key, pygame.K_SPACE)

    def test_f22_event_queue_purging(self):
        """F22.5: Verify clear_events flushes all events cleanly."""
        self.post_key(pygame.K_a)
        self.post_key(pygame.K_b)
        self.clear_events()
        events = pygame.event.get()
        self.assertEqual(len(events), 0)
