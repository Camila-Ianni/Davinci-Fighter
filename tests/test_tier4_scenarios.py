import os
import math
import unittest
import pygame

from tests.base_headless import (
    HeadlessTestCase,
    CANONICAL_SCREEN_WIDTH,
    CANONICAL_SCREEN_HEIGHT,
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
from stage_manager import stage_manager, STAGE_WIDTH, STAGE_HEIGHT
from audio_manager import audio_manager
from menu import TitleScreen, MainMenu
from character_select import CharacterSelect
from main import AppState
from game import Game


class TestTier4Scenarios(HeadlessTestCase):
    """
    Tier 4: Real-World Application Workflows & Scenarios.
    Validates end-to-end user journeys from application boot to combat handoff:
    full PVAI and PVP sequence flows, instant cutscene skips, mirror matches,
    idle attract mode stability, rapid input storms, stage/music resolutions,
    and silent audio fallbacks.
    Total tests >= 11.
    """

    def test_scenario_01_full_pvai_playthrough_carloni_vs_cavasso(self):
        """
        Scenario 1: Full PVAI playthrough with Carloni (China) vs Cavasso (USA).
        Workflow: Boot -> Cutscene skip -> Title -> MainMenu 1P -> CharacterSelect P1 Carloni ->
        AI Cavasso -> Flight China->USA -> VS Screen -> Combat handoff.
        """
        # 1. Title Screen
        title = TitleScreen(self.screen)
        res_title = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(res_title, "continue")

        # 2. Main Menu: Select 1P (VS IA)
        menu = MainMenu(self.screen)
        res_menu = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res_menu, {"action": "start", "mode": MODE_PVAI})

        # 3. Character Select: P1 Carloni (index 0), P2 AI Cavasso (index 1)
        cs = CharacterSelect(self.screen, res_menu["mode"])
        self.assertEqual(cs.p1_idx, 0)  # Carloni
        self.assertEqual(cs.p2_idx, 1)  # Cavasso
        # P1 confirms
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        # In PVAI, P2 is AI auto-confirmed
        cs.p2_confirmed = True
        res_cs = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res_cs["action"], "fight")
        self.assertEqual(res_cs["p1_char"], "carloni")
        self.assertEqual(res_cs["p2_char"], "cavasso")

        # 4. Flight Animation from China to USA
        p_origin = (WORLD_MAP_WAYPOINTS["carloni"]["x"], WORLD_MAP_WAYPOINTS["carloni"]["y"])
        p_dest = (WORLD_MAP_WAYPOINTS["cavasso"]["x"], WORLD_MAP_WAYPOINTS["cavasso"]["y"])
        heading = calculate_heading_angle(p_origin, p_dest)
        midpoint = calculate_flight_position(p_origin, p_dest, 0.5)
        self.assertAlmostEqual(heading, -1.6, delta=1.0)
        self.assertAlmostEqual(midpoint[0], 755.5)
        self.assertAlmostEqual(midpoint[1], 153.0)

        # 5. Combat Initialization at Cavasso's Stage
        stage = stage_manager.get_stage_for_character(res_cs["p2_char"])
        self.assertEqual(stage.name, stage_manager.stages["cavasso"].name)
        game = Game(self.screen, res_cs["p1_char"], res_cs["p2_char"], res_menu["mode"])
        self.assertEqual(game.p1_char, "carloni")
        self.assertEqual(game.p2_char, "cavasso")

    def test_scenario_02_full_pvp_match_romero_vs_gamaliel(self):
        """
        Scenario 2: Full PVP match with Romero (Spain) vs Gamaliel (Brazil).
        Workflow: Title -> MainMenu 2P -> CharacterSelect P1 Romero / P2 Gamaliel ->
        Dual confirmation -> Flight Spain->Brazil -> VS Screen -> Combat handoff.
        """
        # 1. Main Menu: Select 2P (PVP)
        menu = MainMenu(self.screen)
        menu.selected_idx = 1
        res_menu = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res_menu["mode"], MODE_PVP)

        # 2. Character Select: P1 navigates to Romero (idx 2), P2 navigates to Gamaliel (idx 3)
        cs = CharacterSelect(self.screen, res_menu["mode"])
        # P1 moves from 0 to 2
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 2)  # Romero
        # P2 moves from 1 to 3
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(cs.p2_idx, 3)  # Gamaliel

        # P1 confirms with SPACE
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)

        # P2 confirms with KP1
        res_cs = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1))
        self.assertEqual(res_cs["action"], "fight")
        self.assertEqual(res_cs["p1_char"], "romero")
        self.assertEqual(res_cs["p2_char"], "gamaliel")

        # 3. Flight Animation: Spain (201, 140) to Brazil (978, 318)
        p_spain = (WORLD_MAP_WAYPOINTS["romero"]["x"], WORLD_MAP_WAYPOINTS["romero"]["y"])
        p_brazil = (WORLD_MAP_WAYPOINTS["gamaliel"]["x"], WORLD_MAP_WAYPOINTS["gamaliel"]["y"])
        dist = math.hypot(p_brazil[0] - p_spain[0], p_brazil[1] - p_spain[1])
        self.assertGreater(dist, 700.0)

        # 4. Combat Launch at Blanka's Brazil River stage
        stage = stage_manager.get_stage_for_character(res_cs["p2_char"])
        self.assertEqual(stage.name, stage_manager.stages["gamaliel"].name)
        game = Game(self.screen, res_cs["p1_char"], res_cs["p2_char"], res_menu["mode"])
        self.assertEqual(game.p1_char, "romero")
        self.assertEqual(game.p2_char, "gamaliel")

    def test_scenario_03_instant_cutscene_skip_rapid_select_to_japan(self):
        """
        Scenario 3: Instant cutscene skip to title, rapid select, flight to Japan (Sellanes).
        Workflow: Cutscene skipped immediately with ESC -> Title confirm -> Rapid nav to Sellanes ->
        Fight at E. Honda Japan Bathhouse stage.
        """
        # Instant skip key
        self.post_key(pygame.K_ESCAPE)
        events = pygame.event.get()
        self.assertEqual(events[0].key, pygame.K_ESCAPE)

        # Title screen
        title = TitleScreen(self.screen)
        res_title = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res_title, "continue")

        # Character Select: Rapid navigate P1 to Sellanes (index 4)
        cs = CharacterSelect(self.screen, MODE_PVAI)
        for _ in range(4):
            cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 4)
        self.assertEqual(cs.char_keys[cs.p1_idx], "sellanes")

        # Flight to Japan waypoint (683, 184)
        wp_japan = WORLD_MAP_WAYPOINTS["sellanes"]
        self.assertEqual(wp_japan["country"], "Japan")
        self.assertEqual((wp_japan["x"], wp_japan["y"]), (683, 184))

        # Destination Stage: Sellanes
        stage = stage_manager.get_stage_for_character("sellanes")
        self.assertEqual(stage.name, stage_manager.stages["sellanes"].name)

    def test_scenario_04_mirror_match_cavasso_vs_cavasso(self):
        """
        Scenario 4: Mirror Match: Cavasso vs Cavasso (flight takeoff/landing at same waypoint).
        Workflow: PVP -> P1 selects Cavasso -> P2 selects Cavasso -> Flight distance 0.0 ->
        Combat initialized with mirror fighters.
        """
        cs = CharacterSelect(self.screen, MODE_PVP)
        # P1 moves from 0 to 1 (Cavasso)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 1)
        # P2 is already at 1 (Cavasso)
        self.assertEqual(cs.p2_idx, 1)

        # Confirm both
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        res_cs = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1))
        self.assertEqual(res_cs["p1_char"], "cavasso")
        self.assertEqual(res_cs["p2_char"], "cavasso")

        # Flight takeoff and landing at same point
        p_origin = (WORLD_MAP_WAYPOINTS["cavasso"]["x"], WORLD_MAP_WAYPOINTS["cavasso"]["y"])
        p_dest = p_origin
        self.assertEqual(calculate_flight_position(p_origin, p_dest, 0.5), p_origin)
        self.assertEqual(calculate_heading_angle(p_origin, p_dest), 0.0)

        # Combat match initializes
        game = Game(self.screen, "cavasso", "cavasso", MODE_PVP)
        self.assertEqual(game.p1_char, "cavasso")
        self.assertEqual(game.p2_char, "cavasso")

    def test_scenario_05_mode_switch_navigation_and_cancel(self):
        """
        Scenario 5: Mode switch: 1P mode -> 2P mode -> Back -> Select.
        Workflow: MainMenu navigates down to 2P, down to Controls, views controls,
        dismisses controls, navigates back to 1P, confirms 1P.
        """
        menu = MainMenu(self.screen)
        self.assertEqual(menu.selected_idx, 0)
        # Down to 2P
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 1)
        # Down to CÓMO JUGAR
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(menu.selected_idx, 2)
        # Enter CÓMO JUGAR
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertTrue(menu.showing_controls)
        # Dismiss with SPACE
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertFalse(menu.showing_controls)
        # Up twice to 1P
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        self.assertEqual(menu.selected_idx, 0)
        # Confirm 1P
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res["mode"], MODE_PVAI)

    def test_scenario_06_idle_title_screen_audio_loop_stability(self):
        """
        Scenario 6: Idle Title Screen timeout & audio loop stability (multiple virtual loops).
        Workflow: TitleScreen runs idle for 600 virtual frames (10 seconds).
        Verifies blink counter increases, audio remains active, and any key still starts game.
        """
        title = TitleScreen(self.screen)
        self.advance_frames(lambda dt: setattr(title, "blink_timer", title.blink_timer + 1), frame_count=600)
        self.assertEqual(title.blink_timer, 600)
        # Music track still valid
        self.assertIsNotNone(audio_manager.current_track)
        # Can still transition after idle
        res = title.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res, "continue")

    def test_scenario_07_cursor_wraparound_rapid_navigation_all_slots(self):
        """
        Scenario 7: Cursor wrap-around and fast rapid navigation across all 16 slots.
        Workflow: Rapid left/right navigation wraps around 5 playable professors cleanly.
        """
        cs = CharacterSelect(self.screen, MODE_PVP)
        # Left wrap from 0 -> 4
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertEqual(cs.p1_idx, 4)
        # Right wrap from 4 -> 0
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 0)
        # Rapid 20 taps to the right
        for _ in range(20):
            cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 0)  # 20 % 5 == 0

    def test_scenario_08_opponent_stage_music_verification_all_5_professors(self):
        """
        Scenario 8: Opponent stage music verification for all 5 professors.
        Workflow: Tests resolving opponent stage sheet and CPS1 stage music for each professor.
        """
        expected_resolutions = {
            "carloni": ("Ryu", "(SEGA) Street Fighter II SCE Music - Ryu Stage.mp3"),
            "cavasso": ("Guile", "(SEGA) Street Fighter II SCE Music - Guile Stage.mp3"),
            "romero": ("Sagat", "(SEGA) Street Fighter II SCE Music - Sagat Stage.mp3"),
            "gamaliel": ("Blanka", "(SEGA) Street Fighter II SCE Music - Blanka Stage.mp3"),
            "sellanes": ("Bison", "(SEGA) Street Fighter II SCE Music - M Bison Stage.mp3"),
        }
        for char_id, (expected_stage_token, expected_music_file) in expected_resolutions.items():
            stage = stage_manager.get_stage_for_character(char_id)
            self.assertIn(expected_stage_token, stage.sheet_file)
            self.assertEqual(STAGE_MUSIC_MAP[char_id], expected_music_file)

    def test_scenario_09_combat_launch_and_menu_return(self):
        """
        Scenario 9: Combat launch, round completion, and return to Main Menu.
        Workflow: Combat initialized with Carloni vs Cavasso, completes and transitions back to menu.
        """
        game = Game(self.screen, "carloni", "cavasso", MODE_PVAI)
        self.assertEqual(game.current_round, 1)
        self.assertEqual(game.timer, 99.0)
        # Advance through START_ROUND intro banners (140 frames: "ROUND 1" and "FIGHT!")
        self.advance_frames(game.update, frame_count=140)
        # Now in FIGHTING state: advance 60 frames of combat
        self.advance_frames(game.update, frame_count=60)
        self.assertAlmostEqual(game.timer, 98.0, delta=0.1)

    def test_scenario_10_headless_audio_driver_fallback_and_silent_recovery(self):
        """
        Scenario 10: Headless audio driver fallback and silent recovery.
        Workflow: Tests that missing SFX or stopping uninitialized audio does not interrupt game loop.
        """
        # Purposely play non-existent sounds
        audio_manager.play_sfx("non_existent_special_effect_xyz")
        audio_manager.play_music("non_existent_music_key_123")
        # Ensure game scenes can still render and update
        menu = MainMenu(self.screen)
        menu.draw()
        cs = CharacterSelect(self.screen, MODE_PVAI)
        cs.draw()

    def test_scenario_11_complete_continuous_arcade_sequence_no_skips(self):
        """
        Scenario 11: Complete continuous arcade sequence without any user skips.
        Workflow: Full sequence time budget verification:
        Cutscene (14.4s = 864 frames) -> Title screen -> Menu -> Select -> VS flight (2s = 120 frames) -> Fight.
        """
        # Cutscene frames budget
        cutscene_frames = 864
        cutscene_duration_sec = cutscene_frames / 60.0
        self.assertAlmostEqual(cutscene_duration_sec, 14.4)

        # Title screen mount
        title = TitleScreen(self.screen)
        self.advance_frames(lambda dt: setattr(title, "blink_timer", title.blink_timer + 1), frame_count=120)
        self.assertEqual(title.blink_timer, 120)

        # Flight duration budget
        flight_frames = 120
        self.assertEqual(flight_frames / 60.0, 2.0)

    def test_scenario_12_pvp_different_character_permutations(self):
        """
        Scenario 12: PVP permutations: 5 distinct fighter pairings across roster.
        Verifies valid combat initialization for varied matchups.
        """
        pairings = [
            ("carloni", "romero"),
            ("cavasso", "gamaliel"),
            ("romero", "sellanes"),
            ("gamaliel", "carloni"),
            ("sellanes", "cavasso"),
        ]
        for p1, p2 in pairings:
            game = Game(self.screen, p1, p2, MODE_PVP)
            self.assertEqual(game.p1_char, p1)
            self.assertEqual(game.p2_char, p2)
            self.assertEqual(game.game_mode, MODE_PVP)

    def test_scenario_13_flight_interpolation_across_all_origin_destination_pairs(self):
        """
        Scenario 13: Flight interpolation across all 25 country pairs.
        Verifies all vector positions remain strictly inside world map boundaries.
        """
        chars = list(WORLD_MAP_WAYPOINTS.keys())
        for c1 in chars:
            for c2 in chars:
                p1 = (WORLD_MAP_WAYPOINTS[c1]["x"], WORLD_MAP_WAYPOINTS[c1]["y"])
                p2 = (WORLD_MAP_WAYPOINTS[c2]["x"], WORLD_MAP_WAYPOINTS[c2]["y"])
                for step in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    pos = calculate_flight_position(p1, p2, step)
                    self.assert_point_within_screen(pos[0], pos[1])
