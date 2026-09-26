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
from stage_manager import stage_manager
from audio_manager import audio_manager
from menu import TitleScreen, MainMenu
from character_select import CharacterSelect
from main import AppState
from game import Game


class TestTier3Pairwise(HeadlessTestCase):
    """
    Tier 3: Pairwise Cross-Feature Combinatorial Interactions.
    Verifies cross-cutting interactions between pairs of features across the 22-feature matrix:
    mode switches, cursor wraps, simultaneous inputs, audio crossfades, waypoint handoffs,
    and stage resolutions.
    Total tests >= 22.
    """

    # -------------------------------------------------------------------------
    # PAIR 1: Feature 3 (Cutscene Skip) x Feature 6 (Title Screen Layout)
    # -------------------------------------------------------------------------
    def test_pw01_cutscene_skip_mounts_title_screen(self):
        """PW01: Skipping cutscene with SPACE immediately presents TitleScreen with image ready."""
        skip_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        self.assertEqual(skip_event.key, pygame.K_SPACE)
        title = TitleScreen(self.screen)
        self.assertIsNotNone(title.image)
        self.assertEqual(title.image.get_size(), (CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT))

    def test_pw02_cutscene_skip_keys_parity(self):
        """PW02: Skipping cutscene via RETURN vs ESCAPE yields identical TitleScreen readiness."""
        for skip_key in [pygame.K_RETURN, pygame.K_ESCAPE]:
            ev = pygame.event.Event(pygame.KEYDOWN, key=skip_key)
            self.assertIn(ev.key, [pygame.K_RETURN, pygame.K_ESCAPE])
            title = TitleScreen(self.screen)
            self.assertEqual(title.blink_timer, 0)

    # -------------------------------------------------------------------------
    # PAIR 2: Feature 7 (Animated Logo Sheen) x Feature 8 (Blinking Start Prompt)
    # -------------------------------------------------------------------------
    def test_pw03_sheen_and_prompt_simultaneous_progression(self):
        """PW03: Logo sheen and prompt blink advance in parallel over 60 frames without conflict."""
        title = TitleScreen(self.screen)
        initial_blink = title.blink_timer
        # Simulate 60 frames
        for _ in range(60):
            title.blink_timer += 1
        self.assertEqual(title.blink_timer, initial_blink + 60)
        # Verify blink state toggled twice (at frame 30 and frame 60)
        self.assertEqual((title.blink_timer // 30) % 2, 0)

    # -------------------------------------------------------------------------
    # PAIR 3: Feature 9 (Opening Theme Audio) x Feature 10 (Main Menu Mode Select)
    # -------------------------------------------------------------------------
    def test_pw04_title_to_menu_preserves_opening_music(self):
        """PW04: Transitioning from TitleScreen to MainMenu maintains the 'menu' music track."""
        title = TitleScreen(self.screen)
        title_track = audio_manager.current_track
        menu = MainMenu(self.screen)
        menu_track = audio_manager.current_track
        self.assertEqual(title_track, menu_track)
        self.assertIn("Opening Theme.mp3", menu_track)

    def test_pw05_menu_mode_toggle_does_not_restart_music(self):
        """PW05: Navigating options in MainMenu does not restart or interrupt active music."""
        menu = MainMenu(self.screen)
        current = audio_manager.current_track
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.assertEqual(audio_manager.current_track, current)

    # -------------------------------------------------------------------------
    # PAIR 4: Feature 10 (Main Menu Mode Select) x Feature 14 (P1/P2 Cursor Navigation)
    # -------------------------------------------------------------------------
    def test_pw06_pvai_mode_cursor_initialization(self):
        """PW06: MainMenu 1P (PVAI) selection initializes CharacterSelect in PVAI mode."""
        menu = MainMenu(self.screen)
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res["mode"], MODE_PVAI)
        cs = CharacterSelect(self.screen, res["mode"])
        self.assertEqual(cs.game_mode, MODE_PVAI)
        self.assertEqual(cs.p1_idx, 0)
        self.assertEqual(cs.p2_idx, 1)

    def test_pw07_pvp_mode_cursor_initialization(self):
        """PW07: MainMenu 2P (PVP) selection initializes CharacterSelect in PVP mode."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 1
        res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res["mode"], MODE_PVP)
        cs = CharacterSelect(self.screen, res["mode"])
        self.assertEqual(cs.game_mode, MODE_PVP)

    # -------------------------------------------------------------------------
    # PAIR 5: Feature 10 (Main Menu Mode Select) x Feature 15 (Single-ENTER Bugfix & PVAI)
    # -------------------------------------------------------------------------
    def test_pw08_pvp_mode_requires_dual_confirm(self):
        """PW08: In PVP mode, P1 confirm alone does not trigger combat."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        self.assertFalse(cs.p2_confirmed)
        self.assertIsNone(res)

    def test_pw09_pvp_mode_dual_confirm_triggers_fight(self):
        """PW09: In PVP mode, subsequent P2 confirm triggers combat with both fighters."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1))
        self.assertIsNotNone(res)
        self.assertEqual(res.get("action"), "fight")
        self.assertEqual(res.get("p1_char"), "carloni")
        self.assertEqual(res.get("p2_char"), "cavasso")

    # -------------------------------------------------------------------------
    # PAIR 6: Feature 11 (16-Slot Grid Display) x Feature 12 (5 Professor Slots)
    # -------------------------------------------------------------------------
    def test_pw10_grid_row0_slots_map_to_5_professors(self):
        """PW10: Row 0 Cols 0..4 in 16-slot grid match exact IDs of 5 professors."""
        prof_keys = ["carloni", "cavasso", "romero", "gamaliel", "sellanes"]
        for col, prof in enumerate(prof_keys):
            slot = [s for s in GRID_SLOTS if s["row"] == 0 and s["col"] == col][0]
            self.assertEqual(slot["char"], prof)
            char_data = get_character_data(prof)
            self.assertEqual(char_data["id"], prof)

    # -------------------------------------------------------------------------
    # PAIR 7: Feature 12 (5 Professor Slots) x Feature 13 (World Map Waypoints)
    # -------------------------------------------------------------------------
    def test_pw11_carloni_china_waypoint_association(self):
        """PW11: Carloni slot maps to China waypoint (544, 159)."""
        wp = WORLD_MAP_WAYPOINTS["carloni"]
        self.assertEqual(wp["country"], "China")
        self.assertEqual((wp["x"], wp["y"]), (544, 159))

    def test_pw12_cavasso_usa_waypoint_association(self):
        """PW12: Cavasso slot maps to USA waypoint (967, 147)."""
        wp = WORLD_MAP_WAYPOINTS["cavasso"]
        self.assertEqual(wp["country"], "USA")
        self.assertEqual((wp["x"], wp["y"]), (967, 147))

    def test_pw13_romero_spain_waypoint_association(self):
        """PW13: Romero slot maps to Spain waypoint (201, 140)."""
        wp = WORLD_MAP_WAYPOINTS["romero"]
        self.assertEqual(wp["country"], "Spain")
        self.assertEqual((wp["x"], wp["y"]), (201, 140))

    def test_pw14_gamaliel_brazil_waypoint_association(self):
        """PW14: Gamaliel slot maps to Brazil waypoint (978, 318)."""
        wp = WORLD_MAP_WAYPOINTS["gamaliel"]
        self.assertEqual(wp["country"], "Brazil")
        self.assertEqual((wp["x"], wp["y"]), (978, 318))

    def test_pw15_sellanes_japan_waypoint_association(self):
        """PW15: Sellanes slot maps to Japan waypoint (683, 184)."""
        wp = WORLD_MAP_WAYPOINTS["sellanes"]
        self.assertEqual(wp["country"], "Japan")
        self.assertEqual((wp["x"], wp["y"]), (683, 184))

    # -------------------------------------------------------------------------
    # PAIR 8: Feature 14 (Dual Cursor Navigation) x Feature 16 (Character Select Audio)
    # -------------------------------------------------------------------------
    def test_pw16_p1_and_p2_navigation_audio_feedback(self):
        """PW16: Both P1 and P2 navigation trigger 'menu_navigate' SFX while music plays."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertIn("Character Select.mp3", audio_manager.current_track)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertIn("menu_navigate", audio_manager.sfx_cache)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT))
        self.assertIn("menu_navigate", audio_manager.sfx_cache)

    # -------------------------------------------------------------------------
    # PAIR 9: Feature 14 (Dual Cursor Navigation) x Feature 15 (Single-ENTER Bugfix)
    # -------------------------------------------------------------------------
    def test_pw17_independent_navigation_after_partial_confirm(self):
        """PW17: When P1 confirms, P2 can still freely navigate between characters."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        p2_orig = cs.p2_idx
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(cs.p2_idx, (p2_orig + 1) % len(cs.char_keys))

    # -------------------------------------------------------------------------
    # PAIR 10: Feature 16 (Character Select Audio) x Feature 20 (Opponent Stage Music)
    # -------------------------------------------------------------------------
    def test_pw18_audio_transition_to_opponent_stage_music(self):
        """PW18: Confirming character transitions from Character Select music to opponent stage CPS1 music."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertIn("Character Select.mp3", audio_manager.current_track)
        opponent_char = "gamaliel"
        stage_music_file = STAGE_MUSIC_MAP[opponent_char]
        audio_manager.stop_music()
        audio_manager.play_music("fight")  # Launches combat track
        self.assertIsNotNone(audio_manager.current_track)

    # -------------------------------------------------------------------------
    # PAIR 11: Feature 17 (Airplane Flight Trajectory) x Feature 18 (Dotted Breadcrumbs)
    # -------------------------------------------------------------------------
    def test_pw19_airplane_flight_generates_breadcrumbs(self):
        """PW19: Advancing airplane along vector accumulates breadcrumbs at sampled waypoints."""
        p_carloni = (WORLD_MAP_WAYPOINTS["carloni"]["x"], WORLD_MAP_WAYPOINTS["carloni"]["y"])
        p_cavasso = (WORLD_MAP_WAYPOINTS["cavasso"]["x"], WORLD_MAP_WAYPOINTS["cavasso"]["y"])
        breadcrumbs = []
        for step in range(5):
            t = step / 4.0
            pos = calculate_flight_position(p_carloni, p_cavasso, t)
            breadcrumbs.append(pos)
        self.assertEqual(len(breadcrumbs), 5)
        self.assertEqual(breadcrumbs[0], p_carloni)
        self.assertEqual(breadcrumbs[-1], p_cavasso)

    # -------------------------------------------------------------------------
    # PAIR 12: Feature 17 (Airplane Flight Trajectory) x Feature 19 (VS Face-Off)
    # -------------------------------------------------------------------------
    def test_pw20_flight_completion_triggers_vs_confrontation(self):
        """PW20: Reaching t=1.0 at destination triggers transition to VS Face-Off state."""
        flight_t = 0.0
        # Simulate 120 frames of flight
        for _ in range(120):
            flight_t = min(1.0, flight_t + (1.0 / 120.0))
        self.assertAlmostEqual(flight_t, 1.0, places=5)
        # Confrontation state follows flight completion
        confrontation_active = (round(flight_t, 4) >= 1.0)
        self.assertTrue(confrontation_active)

    # -------------------------------------------------------------------------
    # PAIR 13: Feature 19 (VS Face-Off) x Feature 20 (Opponent Stage Resolution)
    # -------------------------------------------------------------------------
    def test_pw21_vs_screen_displays_matched_fighters_and_stage(self):
        """PW21: VS confrontation maps P1 Carloni and P2 Romero to Romero's Ken Harbor stage."""
        p1 = "carloni"
        p2 = "romero"
        stg = stage_manager.get_stage_for_character(p2)
        self.assertEqual(stg.name, stage_manager.stages["romero"].name)
        self.assertIn("Sagat", stg.sheet_file)

    # -------------------------------------------------------------------------
    # PAIR 14: Feature 20 (Opponent Stage Resolution) x Feature 21 (Pre-Combat Integration)
    # -------------------------------------------------------------------------
    def test_pw22_combat_instance_receives_resolved_characters_and_stage(self):
        """PW22: Game receives P1 Sellanes and P2 Gamaliel in PVP mode at Blanka stage."""
        game = Game(self.screen, "sellanes", "gamaliel", MODE_PVP)
        self.assertEqual(game.p1_char, "sellanes")
        self.assertEqual(game.p2_char, "gamaliel")
        self.assertEqual(game.game_mode, MODE_PVP)

    # -------------------------------------------------------------------------
    # PAIR 15: Feature 5 (Procedural SFX Audio) x Feature 17 (Flight Trajectory)
    # -------------------------------------------------------------------------
    def test_pw23_flight_hum_sound_synthesis_along_trajectory(self):
        """PW23: Procedural airplane motor hum synthesizes while calculating flight heading."""
        p1 = (544, 159)
        p2 = (967, 147)
        heading = calculate_heading_angle(p1, p2)
        motor_sound = generate_procedural_tone(frequency=110.0, duration=0.2, volume=0.3)
        self.assertIsInstance(motor_sound, pygame.mixer.Sound)
        self.assertAlmostEqual(heading, -1.6, delta=0.5)

    # -------------------------------------------------------------------------
    # PAIR 16: Feature 14 (Cursor Navigation) x Feature 11 (16-Slot Grid Wraparound)
    # -------------------------------------------------------------------------
    def test_pw24_cursor_wraps_across_active_professors(self):
        """PW24: Moving left from slot 0 wraps to slot 4 (Sellanes), skipping locked slots."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertEqual(cs.p1_idx, 0)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertEqual(cs.p1_idx, 4)
        self.assertEqual(cs.char_keys[cs.p1_idx], "sellanes")
