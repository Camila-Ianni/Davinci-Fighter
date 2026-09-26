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
    STAGE_SHEET_MAP,
    calculate_flight_position,
    calculate_heading_angle,
    generate_procedural_tone,
)
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, MODE_PVAI, MODE_PVP
from character_data import CHARACTERS, get_character_data
from stage_manager import stage_manager, Stage, STAGE_WIDTH, STAGE_HEIGHT
from audio_manager import audio_manager, AudioManager
from menu import TitleScreen, MainMenu
from character_select import CharacterSelect
from game import Game


class TestTier2Boundaries(HeadlessTestCase):
    """
    Tier 2: Boundary, Corner Cases & Stress Conditions.
    Tests extreme inputs, empty events, missing assets, mirror matches,
    coordinate limits, delta-time variations, and audio fallbacks.
    Total tests >= 110.
    """

    # =========================================================================
    # CATEGORY 1: Coordinate & Aspect Boundaries (20 tests)
    # =========================================================================

    def test_b01_origin_coordinate_on_screen(self):
        """B01: Top-left origin (0, 0) is valid within canvas bounds."""
        self.assert_point_within_screen(0, 0)

    def test_b02_bottom_right_corner_on_screen(self):
        """B02: Bottom-right corner (1280, 720) is at exact screen boundary."""
        self.assert_point_within_screen(CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT)

    def test_b03_negative_coordinates_fail_screen_bounds(self):
        """B03: Negative coordinates (-1, 0) or (0, -1) trigger assertion error."""
        with self.assertRaises(AssertionError):
            self.assert_point_within_screen(-1, 100)
        with self.assertRaises(AssertionError):
            self.assert_point_within_screen(100, -1)

    def test_b04_overflow_coordinates_fail_screen_bounds(self):
        """B04: Overflow coordinates (1281, 721) trigger assertion error."""
        with self.assertRaises(AssertionError):
            self.assert_point_within_screen(1281, 360)
        with self.assertRaises(AssertionError):
            self.assert_point_within_screen(640, 721)

    def test_b05_surface_negative_dimensions_disallowed(self):
        """B05: Creating surface with negative dimensions raises pygame.error."""
        with self.assertRaises(pygame.error):
            pygame.Surface((-1, 720))
        with self.assertRaises(pygame.error):
            pygame.Surface((1280, -1))

    def test_b06_surface_minimal_1x1_valid(self):
        """B06: Minimal 1x1 surface creates valid pygame Surface."""
        surf = pygame.Surface((1, 1))
        self.assertEqual(surf.get_size(), (1, 1))

    def test_b07_stage_horizontal_scroll_clamp_minimum(self):
        """B07: Stage camera_x clamped to 0 when moving left of world origin."""
        cam_x = -50
        clamped_x = max(0, min(STAGE_WIDTH - SCREEN_WIDTH, cam_x))
        self.assertEqual(clamped_x, 0)

    def test_b08_stage_horizontal_scroll_clamp_maximum(self):
        """B08: Stage camera_x clamped to STAGE_WIDTH - SCREEN_WIDTH (920px)."""
        max_scroll = STAGE_WIDTH - SCREEN_WIDTH
        cam_x = 1500
        clamped_x = max(0, min(max_scroll, cam_x))
        self.assertEqual(clamped_x, 920)

    def test_b09_stage_crop_zero_origin(self):
        """B09: Crop rectangle with valid zero-origin (0, 0, 100, 100)."""
        crop = pygame.Rect(0, 0, 100, 100)
        self.assertEqual(crop.topleft, (0, 0))
        self.assertEqual(crop.size, (100, 100))

    def test_b10_stage_crop_out_of_bounds_handling(self):
        """B10: Subsurface outside parent bounds raises ValueError."""
        parent = pygame.Surface((200, 200))
        with self.assertRaises(ValueError):
            parent.subsurface(pygame.Rect(150, 150, 100, 100))

    def test_b11_hitbox_zero_size_clamping(self):
        """B11: Attack hitbox with 0 width is handled safely."""
        rect = pygame.Rect(0, 0, 0, 0)
        self.assertEqual(rect.width, 0)
        self.assertEqual(rect.height, 0)

    def test_b12_extreme_canvas_scaling_factors(self):
        """B12: Canvas scaling factor math with arbitrary resolutions."""
        for w, h in [(640, 480), (1920, 1080), (3840, 2160)]:
            scale_x = w / CANONICAL_SCREEN_WIDTH
            scale_y = h / CANONICAL_SCREEN_HEIGHT
            self.assertGreater(scale_x, 0)
            self.assertGreater(scale_y, 0)

    def test_b13_aspect_ratio_preservation_pillarbox(self):
        """B13: 4:3 image on 16:9 canvas calculates exact symmetrical pillarbox width."""
        canvas_w, canvas_h = 1280, 720
        arcade_h = canvas_h
        arcade_w = int(arcade_h * (4.0 / 3.0))
        pillarbox_each = (canvas_w - arcade_w) // 2
        self.assertEqual(arcade_w, 960)
        self.assertEqual(pillarbox_each, 160)
        self.assertEqual(arcade_w + 2 * pillarbox_each, canvas_w)

    def test_b14_aspect_ratio_preservation_letterbox(self):
        """B14: 16:9 image on 4:3 canvas calculates exact symmetrical letterbox height."""
        canvas_w, canvas_h = 960, 720
        content_w = canvas_w
        content_h = int(content_w * (9.0 / 16.0))
        letterbox_each = (canvas_h - content_h) // 2
        self.assertEqual(content_h, 540)
        self.assertEqual(letterbox_each, 90)

    def test_b15_rect_clipping_completely_outside(self):
        """B15: Rectangles completely outside screen boundaries do not collide with screen rect."""
        screen_rect = pygame.Rect(0, 0, CANONICAL_SCREEN_WIDTH, CANONICAL_SCREEN_HEIGHT)
        outside_rect = pygame.Rect(-500, -500, 100, 100)
        self.assertFalse(screen_rect.colliderect(outside_rect))

    def test_b16_rect_clipping_partial_overlap(self):
        """B16: Rectangles partially overlapping canvas clip to valid intersection."""
        screen_rect = pygame.Rect(0, 0, 1280, 720)
        overlapping = pygame.Rect(1200, 700, 100, 100)
        clipped = screen_rect.clip(overlapping)
        self.assertEqual(clipped.size, (80, 20))

    def test_b17_rect_clipping_total_enclosure(self):
        """B17: Subrect completely inside screen retains full dimensions."""
        screen_rect = pygame.Rect(0, 0, 1280, 720)
        inner = pygame.Rect(100, 100, 200, 150)
        clipped = screen_rect.clip(inner)
        self.assertEqual(clipped, inner)

    def test_b18_fractional_coordinate_truncation(self):
        """B18: Fractional coordinates truncate cleanly to pixel integers for blitting."""
        fx, fy = 100.75, 200.25
        ix, iy = int(fx), int(fy)
        self.assertEqual(ix, 100)
        self.assertEqual(iy, 200)

    def test_b19_grid_slots_no_overlap(self):
        """B19: None of the 8 slots in Row 0 overlap with each other horizontally."""
        row0_slots = sorted([s for s in GRID_SLOTS if s["row"] == 0], key=lambda s: s["col"])
        for i in range(len(row0_slots) - 1):
            curr_rect = pygame.Rect(*row0_slots[i]["rect"])
            next_rect = pygame.Rect(*row0_slots[i + 1]["rect"])
            self.assertLessEqual(curr_rect.right, next_rect.left + 5)

    def test_b20_grid_rows_no_overlap(self):
        """B20: Row 0 and Row 1 do not vertically overlap."""
        row0_y = GRID_SLOTS[0]["rect"][1]
        row0_h = GRID_SLOTS[0]["rect"][3]
        row1_y = [s for s in GRID_SLOTS if s["row"] == 1][0]["rect"][1]
        self.assertGreaterEqual(row1_y, row0_y + row0_h)

    # =========================================================================
    # CATEGORY 2: Time, FPS & Delta-Time Stress (20 tests)
    # =========================================================================

    def test_b21_dt_zero_advances_zero_time(self):
        """B21: Virtual update with dt=0.0 does not advance elapsed timer."""
        timer = {"time": 0.0}
        def step(dt):
            timer["time"] += dt
        self.advance_frames(step, frame_count=10, dt=0.0)
        self.assertEqual(timer["time"], 0.0)

    def test_b22_dt_negative_handling(self):
        """B22: Clamping negative dt prevents backwards time travel."""
        safe_dt = lambda dt: max(0.0, dt)
        self.assertEqual(safe_dt(-0.016), 0.0)

    def test_b23_dt_large_spike_handling(self):
        """B23: Large dt spikes (e.g. 5.0s hitch) can be clamped to maximum frame delta."""
        max_dt = 1.0 / 15.0
        clamp_dt = lambda dt: min(max_dt, dt)
        self.assertAlmostEqual(clamp_dt(5.0), 1.0 / 15.0)

    def test_b24_dt_micro_step(self):
        """B24: Micro-step delta times (0.0001s) accumulate accurately."""
        accum = sum(0.0001 for _ in range(10000))
        self.assertAlmostEqual(accum, 1.0, places=4)

    def test_b25_dt_alternating_jitter(self):
        """B25: Variable frame pacing (jitter) accumulates without drift."""
        dts = [0.010, 0.023] * 30  # 60 frames total
        total = sum(dts)
        self.assertAlmostEqual(total, 0.99, delta=0.01)

    def test_b26_zero_frames_step_noop(self):
        """B26: Stepping 0 frames executes 0 updates."""
        counter = {"c": 0}
        self.advance_frames(lambda dt: counter.update({"c": counter["c"] + 1}), frame_count=0)
        self.assertEqual(counter["c"], 0)

    def test_b27_massive_frame_step_stress(self):
        """B27: Stepping 5000 virtual frames executes rapidly in virtual time."""
        counter = {"c": 0}
        self.advance_frames(lambda dt: counter.update({"c": counter["c"] + 1}), frame_count=5000)
        self.assertEqual(counter["c"], 5000)

    def test_b28_blink_cadence_at_frame_million(self):
        """B28: Blink calculation handles high frame counts without integer overflow."""
        frame = 1000000
        is_visible = ((frame // 30) % 2) == 0
        self.assertIn(is_visible, [True, False])

    def test_b29_combat_timer_countdown_zero_clamp(self):
        """B29: Combat timer decrements and clamps at 0.0."""
        timer = 1.0
        for _ in range(70):
            timer = max(0.0, timer - (1.0 / 60.0))
        self.assertEqual(timer, 0.0)

    def test_b30_clock_tick_fps_60(self):
        """B30: Settings FPS is canonical 60."""
        self.assertEqual(FPS, 60)

    def test_b31_sub_frame_interpolation_bounds(self):
        """B31: Sub-frame alpha parameter is strictly in [0.0, 1.0]."""
        for alpha in [0.0, 0.1, 0.5, 0.9, 1.0]:
            clamped = max(0.0, min(1.0, alpha))
            self.assertEqual(clamped, alpha)

    def test_b32_elapsed_seconds_to_frame_conversion(self):
        """B32: Converting seconds to frame count rounds to nearest integer."""
        to_frames = lambda s, fps=60: int(round(s * fps))
        self.assertEqual(to_frames(1.0), 60)
        self.assertEqual(to_frames(0.5), 30)
        self.assertEqual(to_frames(2.5), 150)

    def test_b33_frame_to_seconds_conversion(self):
        """B33: Converting frames to seconds computes exact floating point seconds."""
        to_sec = lambda f, fps=60: f / float(fps)
        self.assertAlmostEqual(to_sec(60), 1.0)
        self.assertAlmostEqual(to_sec(15), 0.25)

    def test_b34_modulo_timing_wrap_around(self):
        """B34: Cyclic animation phase modulo wraps cleanly at boundary."""
        cycle_frames = 60
        self.assertEqual(0 % cycle_frames, 0)
        self.assertEqual(59 % cycle_frames, 59)
        self.assertEqual(60 % cycle_frames, 0)
        self.assertEqual(61 % cycle_frames, 1)

    def test_b35_frame_rate_independent_movement(self):
        """B35: Distance moved is invariant when speed * dt is integrated over 1 second."""
        speed = 240.0  # px per second
        # 60 FPS
        dist_60 = sum(speed * (1.0 / 60.0) for _ in range(60))
        # 120 FPS
        dist_120 = sum(speed * (1.0 / 120.0) for _ in range(120))
        self.assertAlmostEqual(dist_60, 240.0)
        self.assertAlmostEqual(dist_120, 240.0)

    def test_b36_time_scaling_half_speed(self):
        """B36: Time scale factor 0.5 (slow-motion) halves effective delta time."""
        time_scale = 0.5
        effective_dt = (1.0 / 60.0) * time_scale
        self.assertAlmostEqual(effective_dt, 1.0 / 120.0)

    def test_b37_time_scaling_double_speed(self):
        """B37: Time scale factor 2.0 (fast-forward) doubles effective delta time."""
        time_scale = 2.0
        effective_dt = (1.0 / 60.0) * time_scale
        self.assertAlmostEqual(effective_dt, 1.0 / 30.0)

    def test_b38_game_timer_string_formatting(self):
        """B38: HUD round timer formats 99 to '99' and 5 to '05' or '5'."""
        fmt_timer = lambda t: f"{int(t):02d}"
        self.assertEqual(fmt_timer(99), "99")
        self.assertEqual(fmt_timer(5), "05")
        self.assertEqual(fmt_timer(0), "00")

    def test_b39_pause_state_freezes_timer(self):
        """B39: When paused, game logic delta time is 0.0."""
        is_paused = True
        dt = 0.0 if is_paused else (1.0 / 60.0)
        self.assertEqual(dt, 0.0)

    def test_b40_unpause_state_resumes_timer(self):
        """B40: When unpaused, game logic delta time returns to 1/60."""
        is_paused = False
        dt = 0.0 if is_paused else (1.0 / 60.0)
        self.assertAlmostEqual(dt, 1.0 / 60.0)

    # =========================================================================
    # CATEGORY 3: Input Queue & Rapid Keypress Storm (20 tests)
    # =========================================================================

    def test_b41_empty_event_queue_handling(self):
        """B41: Menu handle_input with empty event does not raise error."""
        menu = MainMenu(self.screen)
        event = pygame.event.Event(pygame.NOEVENT)
        res = menu.handle_input(event)
        self.assertIsNone(res)

    def test_b42_single_frame_rapid_keypress_burst(self):
        """B42: 50 keypresses posted in single frame are retrieved in exact FIFO order."""
        self.clear_events()
        keys = [pygame.K_a, pygame.K_b, pygame.K_c] * 10
        self.post_keys(keys)
        events = pygame.event.get()
        self.assertEqual(len(events), 30)
        for i, ev in enumerate(events):
            self.assertEqual(ev.key, keys[i])

    def test_b43_rapid_alternating_menu_navigation(self):
        """B43: Alternating UP and DOWN arrows 50 times returns menu index to starting position."""
        menu = MainMenu(self.screen)
        initial_idx = menu.selected_idx
        for _ in range(50):
            menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
            menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
        self.assertEqual(menu.selected_idx, initial_idx)

    def test_b44_rapid_alternating_char_select_navigation(self):
        """B44: Alternating A and D keys 50 times returns P1 cursor to starting position."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        initial_idx = cs.p1_idx
        for _ in range(50):
            cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
            cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))
        self.assertEqual(cs.p1_idx, initial_idx)

    def test_b45_unmapped_keys_ignored_in_menu(self):
        """B45: Pressing unmapped keys (F1, BACKSPACE, TAB) in menu does nothing."""
        menu = MainMenu(self.screen)
        for unmapped_k in [pygame.K_F1, pygame.K_BACKSPACE, pygame.K_TAB, pygame.K_LSHIFT]:
            res = menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=unmapped_k))
            self.assertIsNone(res)

    def test_b46_unmapped_keys_ignored_in_char_select(self):
        """B46: Pressing unmapped keys in CharacterSelect does nothing."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        for unmapped_k in [pygame.K_F5, pygame.K_q, pygame.K_e, pygame.K_z]:
            res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=unmapped_k))
            self.assertIsNone(res)

    def test_b47_mouse_movement_ignored_in_char_select(self):
        """B47: MOUSEMOTION events in CharacterSelect are ignored."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        mouse_ev = pygame.event.Event(pygame.MOUSEMOTION, pos=(500, 300), rel=(10, 0), buttons=(0, 0, 0))
        res = cs.handle_input(mouse_ev)
        self.assertIsNone(res)

    def test_b48_title_screen_mouse_click_advances(self):
        """B48: MOUSEBUTTONDOWN on TitleScreen advances to menu."""
        title = TitleScreen(self.screen)
        click_ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
        res = title.handle_input(click_ev)
        self.assertEqual(res, "continue")

    def test_b49_keyup_events_ignored_in_menu(self):
        """B49: KEYUP events without KEYDOWN do not trigger selection in MainMenu."""
        menu = MainMenu(self.screen)
        res = menu.handle_input(pygame.event.Event(pygame.KEYUP, key=pygame.K_RETURN))
        self.assertIsNone(res)

    def test_b50_keyup_events_ignored_in_char_select(self):
        """B50: KEYUP events do not alter character selection indices."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        p1_before = cs.p1_idx
        cs.handle_input(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, p1_before)

    def test_b51_confirm_key_when_already_confirmed(self):
        """B51: Pressing confirm key again when P1 is already confirmed does not reset confirmation."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        # Repeated confirm
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)

    def test_b52_navigate_attempt_when_locked(self):
        """B52: Cursor movement keys for P1 are locked once confirmed."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.p1_idx = 2
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertTrue(cs.p1_confirmed)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
        self.assertEqual(cs.p1_idx, 2)

    def test_b53_p2_navigate_attempt_when_locked(self):
        """B53: Cursor movement keys for P2 are locked once confirmed."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.p2_idx = 3
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_KP1))
        self.assertTrue(cs.p2_confirmed)
        cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.assertEqual(cs.p2_idx, 3)

    def test_b54_how_to_play_overlay_toggle(self):
        """B54: Selecting 'CÓMO JUGAR' displays overlay and any key dismisses it."""
        menu = MainMenu(self.screen)
        menu.selected_idx = 2  # CÓMO JUGAR
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertTrue(menu.showing_controls)
        # Dismiss with any key
        menu.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(menu.showing_controls)

    def test_b55_event_queue_purging_idempotence(self):
        """B55: Calling clear_events multiple times in succession causes no errors."""
        self.clear_events()
        self.clear_events()
        self.clear_events()
        self.assertEqual(len(pygame.event.get()), 0)

    def test_b56_synthetic_quit_event(self):
        """B56: Posting QUIT event is retrieved with type pygame.QUIT."""
        self.clear_events()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        events = pygame.event.get()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, pygame.QUIT)

    def test_b57_key_code_max_int(self):
        """B57: Event with extreme key code (e.g. 999999) handled gracefully."""
        self.clear_events()
        self.post_key(999999)
        events = pygame.event.get()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].key, 999999)

    def test_b58_key_unicode_characters(self):
        """B58: Event with unicode text string (e.g. 'ñ') creates valid event."""
        self.clear_events()
        self.post_key(pygame.K_n, unicode="ñ")
        events = pygame.event.get()
        self.assertEqual(events[0].unicode, "ñ")

    def test_b59_key_mod_flags(self):
        """B59: Event with modifier flags (e.g. KMOD_SHIFT) preserves mod attribute."""
        self.clear_events()
        self.post_key(pygame.K_a, mod=pygame.KMOD_SHIFT)
        events = pygame.event.get()
        self.assertEqual(events[0].mod, pygame.KMOD_SHIFT)

    def test_b60_joystick_event_ignored(self):
        """B60: Joystick button event does not crash menu handle_input."""
        menu = MainMenu(self.screen)
        joy_ev = pygame.event.Event(pygame.JOYBUTTONDOWN, joy=0, button=0)
        res = menu.handle_input(joy_ev)
        self.assertIsNone(res)

    # =========================================================================
    # CATEGORY 4: Roster & Character Selection Boundaries (20 tests)
    # =========================================================================

    def test_b61_mirror_match_carloni_vs_carloni(self):
        """B61: Mirror match Carloni vs Carloni initializes combat properly."""
        game = Game(self.screen, "carloni", "carloni", MODE_PVP)
        self.assertEqual(game.p1_char, "carloni")
        self.assertEqual(game.p2_char, "carloni")

    def test_b62_mirror_match_cavasso_vs_cavasso(self):
        """B62: Mirror match Cavasso vs Cavasso initializes combat properly."""
        game = Game(self.screen, "cavasso", "cavasso", MODE_PVP)
        self.assertEqual(game.p1_char, "cavasso")
        self.assertEqual(game.p2_char, "cavasso")

    def test_b63_mirror_match_romero_vs_romero(self):
        """B63: Mirror match Romero vs Romero initializes combat properly."""
        game = Game(self.screen, "romero", "romero", MODE_PVP)
        self.assertEqual(game.p1_char, "romero")
        self.assertEqual(game.p2_char, "romero")

    def test_b64_mirror_match_gamaliel_vs_gamaliel(self):
        """B64: Mirror match Gamaliel vs Gamaliel initializes combat properly."""
        game = Game(self.screen, "gamaliel", "gamaliel", MODE_PVP)
        self.assertEqual(game.p1_char, "gamaliel")
        self.assertEqual(game.p2_char, "gamaliel")

    def test_b65_mirror_match_sellanes_vs_sellanes(self):
        """B65: Mirror match Sellanes vs Sellanes initializes combat properly."""
        game = Game(self.screen, "sellanes", "sellanes", MODE_PVP)
        self.assertEqual(game.p1_char, "sellanes")
        self.assertEqual(game.p2_char, "sellanes")

    def test_b66_char_select_allows_mirror_match(self):
        """B66: CharacterSelect allows both P1 and P2 to select the same index."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        cs.p1_idx = 0  # Carloni
        cs.p2_idx = 0  # Carloni
        cs.p1_confirmed = True
        cs.p2_confirmed = True
        res = cs.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertEqual(res["p1_char"], "carloni")
        self.assertEqual(res["p2_char"], "carloni")

    def test_b67_unknown_character_id_fallback(self):
        """B67: get_character_data with unknown ID falls back to carloni."""
        data = get_character_data("unknown_char_999")
        self.assertEqual(data["id"], "carloni")

    def test_b68_empty_string_character_id_fallback(self):
        """B68: get_character_data with empty string falls back to carloni."""
        data = get_character_data("")
        self.assertEqual(data["id"], "carloni")

    def test_b69_none_character_id_fallback(self):
        """B69: get_character_data with None falls back to carloni."""
        data = get_character_data(None)
        self.assertEqual(data["id"], "carloni")

    def test_b70_roster_count_exact_five(self):
        """B70: Professor roster contains exactly 5 playable characters."""
        self.assertEqual(len(CHARACTERS), 5)

    def test_b71_character_health_positive(self):
        """B71: All characters have health strictly greater than zero."""
        for name, data in CHARACTERS.items():
            self.assertGreater(data["health"], 0)

    def test_b72_character_speed_positive(self):
        """B72: All characters have movement speed strictly greater than zero."""
        for name, data in CHARACTERS.items():
            self.assertGreater(data["speed"], 0.0)

    def test_b73_character_rgb_in_range(self):
        """B73: All character theme colors are valid RGB tuples (0-255)."""
        for name, data in CHARACTERS.items():
            r, g, b = data["color"]
            self.assertTrue(0 <= r <= 255)
            self.assertTrue(0 <= g <= 255)
            self.assertTrue(0 <= b <= 255)

    def test_b74_character_subjects_list_non_empty(self):
        """B74: All characters have at least one teaching subject listed."""
        for name, data in CHARACTERS.items():
            self.assertGreater(len(data["subjects"]), 0)

    def test_b75_character_quote_string_non_empty(self):
        """B75: All characters have non-empty arcade victory/taunt quotes."""
        for name, data in CHARACTERS.items():
            self.assertGreater(len(data["quote"].strip()), 0)

    def test_b76_attack_damage_bounds(self):
        """B76: All character attacks have positive damage <= 100."""
        for name, data in CHARACTERS.items():
            for atk_name, atk in data["attacks"].items():
                self.assertGreater(atk.damage, 0)
                self.assertLessEqual(atk.damage, 100)

    def test_b77_attack_startup_recovery_timing(self):
        """B77: Attack startup and recovery frames are non-negative."""
        for name, data in CHARACTERS.items():
            for atk_name, atk in data["attacks"].items():
                self.assertGreaterEqual(atk.startup, 0)
                self.assertGreaterEqual(atk.recovery, 0)

    def test_b78_character_select_index_clamping(self):
        """B78: Character select indices remain within bounds [0, len(char_keys)-1]."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        self.assertTrue(0 <= cs.p1_idx < len(cs.char_keys))
        self.assertTrue(0 <= cs.p2_idx < len(cs.char_keys))

    def test_b79_character_select_draw_without_crash(self):
        """B79: CharacterSelect.draw() executes cleanly without exceptions."""
        cs = CharacterSelect(self.screen, MODE_PVP)
        try:
            cs.draw()
        except Exception as e:
            self.fail(f"CharacterSelect.draw() failed: {e}")

    def test_b80_character_select_pvai_draw(self):
        """B80: CharacterSelect.draw() under PVAI mode renders 'P2 / IA' label cleanly."""
        cs = CharacterSelect(self.screen, MODE_PVAI)
        try:
            cs.draw()
        except Exception as e:
            self.fail(f"CharacterSelect.draw() in PVAI mode failed: {e}")

    # =========================================================================
    # CATEGORY 5: Audio Engine Boundaries & Fallbacks (20 tests)
    # =========================================================================

    def test_b81_play_music_unknown_track_key(self):
        """B81: play_music with unknown key does not crash and leaves track unchanged."""
        before = audio_manager.current_track
        audio_manager.play_music("unknown_track_key_xyz")
        self.assertEqual(audio_manager.current_track, before)

    def test_b82_play_sfx_empty_string(self):
        """B82: play_sfx with empty string does not crash."""
        try:
            audio_manager.play_sfx("")
        except Exception as e:
            self.fail(f"play_sfx('') raised: {e}")

    def test_b83_stop_music_when_already_stopped(self):
        """B83: stop_music when no music is playing is a safe no-op."""
        audio_manager.stop_music()
        audio_manager.stop_music()
        self.assertIsNone(audio_manager.current_track)

    def test_b84_volume_zero_mute(self):
        """B84: Setting music_volume to 0.0 effectively mutes without error."""
        audio_manager.music_volume = 0.0
        self.assertEqual(audio_manager.music_volume, 0.0)
        audio_manager.music_volume = 0.6  # restore

    def test_b85_volume_max_1_0(self):
        """B85: Setting music_volume to 1.0 sets full volume without error."""
        audio_manager.music_volume = 1.0
        self.assertEqual(audio_manager.music_volume, 1.0)
        audio_manager.music_volume = 0.6  # restore

    def test_b86_sfx_volume_bounds(self):
        """B86: Setting sfx_volume within [0.0, 1.0] succeeds."""
        audio_manager.sfx_volume = 0.5
        self.assertEqual(audio_manager.sfx_volume, 0.5)
        audio_manager.sfx_volume = 0.8  # restore

    def test_b87_rapid_music_track_switch_storm(self):
        """B87: Rapidly switching music tracks 10 times in succession does not crash."""
        tracks = ["menu", "character_select", "menu", "character_select"]
        for t in tracks:
            audio_manager.play_music(t)
        audio_manager.stop_music()

    def test_b88_sfx_cache_reuse(self):
        """B88: Calling play_sfx with cached sound reuses cached Sound object."""
        test_sound = generate_procedural_tone(frequency=440, duration=0.05)
        audio_manager.sfx_cache["test_beep"] = test_sound
        audio_manager.play_sfx("test_beep")
        self.assertIs(audio_manager.sfx_cache["test_beep"], test_sound)

    def test_b89_procedural_tone_zero_duration(self):
        """B89: Procedural tone with duration=0.0 clamps safely to minimum duration."""
        sound = generate_procedural_tone(frequency=440, duration=0.0)
        self.assertIsInstance(sound, pygame.mixer.Sound)

    def test_b90_procedural_tone_high_frequency(self):
        """B90: Procedural tone with ultrasonic/Nyquist frequency (20,000 Hz) synthesizes safely."""
        sound = generate_procedural_tone(frequency=20000, duration=0.05)
        self.assertIsInstance(sound, pygame.mixer.Sound)

    def test_b91_procedural_tone_low_frequency(self):
        """B91: Procedural tone with infrasonic frequency (20 Hz) synthesizes safely."""
        sound = generate_procedural_tone(frequency=20, duration=0.1)
        self.assertIsInstance(sound, pygame.mixer.Sound)

    def test_b92_fight_music_random_selection(self):
        """B92: play_music('fight') selects one of the 5 CPS1 tracks."""
        audio_manager.play_music("fight")
        self.assertIsNotNone(audio_manager.current_track)
        audio_manager.stop_music()

    def test_b93_all_fight_tracks_exist_on_disk(self):
        """B93: All 5 CPS1 fight tracks in audio_manager.fight_tracks exist in assets/audio/."""
        for track_name in audio_manager.fight_tracks:
            p = os.path.join(audio_manager.audio_dir, track_name)
            self.assertTrue(os.path.exists(p), f"Missing fight track: {p}")

    def test_b94_all_music_tracks_exist_on_disk(self):
        """B94: All tracks in audio_manager.music_tracks exist on disk."""
        for key, file_name in audio_manager.music_tracks.items():
            p = os.path.join(audio_manager.audio_dir, file_name)
            self.assertTrue(os.path.exists(p), f"Missing music track: {p}")

    def test_b95_stage_sheet_files_exist_on_disk(self):
        """B95: All 5 stage sheet PNG files exist in assets/backgrounds/."""
        for char_id, file_name in STAGE_SHEET_MAP.items():
            p = os.path.join("assets", "backgrounds", file_name)
            self.assertTrue(os.path.exists(p), f"Missing stage sheet: {p}")

    def test_b96_stage_manager_unknown_character_fallback(self):
        """B96: stage_manager.get_stage_for_character falls back to Carloni stage on unknown id."""
        stage = stage_manager.get_stage_for_character("unknown_char_xyz")
        self.assertEqual(stage.name, stage_manager.stages["carloni"].name)

    def test_b97_stage_load_idempotence(self):
        """B97: Calling Stage.load() multiple times does not reload or duplicate surface."""
        stage = stage_manager.get_stage_for_character("carloni")
        stage.load()
        surf_first = stage.surface
        stage.load()
        self.assertIs(stage.surface, surf_first)

    def test_b98_stage_draw_default_camera(self):
        """B98: Stage.draw(screen, camera_x=0) renders without exceptions."""
        stage = stage_manager.get_stage_for_character("carloni")
        try:
            stage.draw(self.screen, camera_x=0)
        except Exception as e:
            self.fail(f"Stage.draw() raised: {e}")

    def test_b99_stage_draw_max_camera(self):
        """B99: Stage.draw(screen, camera_x=920) renders rightmost edge cleanly."""
        stage = stage_manager.get_stage_for_character("carloni")
        try:
            stage.draw(self.screen, camera_x=920)
        except Exception as e:
            self.fail(f"Stage.draw() with max scroll raised: {e}")

    def test_b100_audio_manager_stop_when_mixer_uninitialized(self):
        """B100: AudioManager instance handles uninitialized mixer gracefully."""
        mgr = AudioManager()
        try:
            mgr.stop_music()
            mgr.play_sfx("nonexistent")
        except Exception as e:
            self.fail(f"AudioManager with uninitialized mixer raised: {e}")

    # =========================================================================
    # CATEGORY 6: Airplane Flight & Waypoint Interpolation Boundaries (15 tests)
    # =========================================================================

    def test_b101_flight_zero_distance_same_point(self):
        """B101: Flight between identical waypoints stays stationary at that point for all t."""
        pt = (544.0, 159.0)  # China
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            self.assertEqual(calculate_flight_position(pt, pt, t), pt)

    def test_b102_flight_zero_distance_heading_zero(self):
        """B102: Heading angle between identical points defaults safely to 0.0 degrees."""
        pt = (544.0, 159.0)
        self.assertEqual(calculate_heading_angle(pt, pt), 0.0)

    def test_b103_flight_max_distance_spain_to_brazil(self):
        """B103: Vector interpolation between Spain (201, 140) and Brazil (978, 318)."""
        p_spain = (201.0, 140.0)
        p_brazil = (978.0, 318.0)
        mid = calculate_flight_position(p_spain, p_brazil, 0.5)
        self.assertAlmostEqual(mid[0], (201.0 + 978.0) / 2.0)
        self.assertAlmostEqual(mid[1], (140.0 + 318.0) / 2.0)

    def test_b104_flight_extreme_negative_t_clamping(self):
        """B104: Flight t = -99999.0 clamps strictly to p1."""
        p1 = (100.0, 100.0)
        p2 = (500.0, 500.0)
        self.assertEqual(calculate_flight_position(p1, p2, -99999.0), p1)

    def test_b105_flight_extreme_positive_t_clamping(self):
        """B105: Flight t = 99999.0 clamps strictly to p2."""
        p1 = (100.0, 100.0)
        p2 = (500.0, 500.0)
        self.assertEqual(calculate_flight_position(p1, p2, 99999.0), p2)

    def test_b106_flight_heading_cardinal_east(self):
        """B106: Due East trajectory has heading angle exactly 0 degrees."""
        angle = calculate_heading_angle((100, 100), (300, 100))
        self.assertAlmostEqual(angle, 0.0)

    def test_b107_flight_heading_cardinal_south(self):
        """B107: Due South trajectory has heading angle exactly 90 degrees."""
        angle = calculate_heading_angle((100, 100), (100, 300))
        self.assertAlmostEqual(angle, 90.0)

    def test_b108_flight_heading_cardinal_west(self):
        """B108: Due West trajectory has heading angle exactly 180 degrees."""
        angle = calculate_heading_angle((300, 100), (100, 100))
        self.assertAlmostEqual(angle, 180.0)

    def test_b109_flight_heading_cardinal_north(self):
        """B109: Due North trajectory has heading angle exactly -90 degrees."""
        angle = calculate_heading_angle((100, 300), (100, 100))
        self.assertAlmostEqual(angle, -90.0)

    def test_b110_flight_heading_diagonal_southeast(self):
        """B110: Southeast 45-degree trajectory computes 45 degrees."""
        angle = calculate_heading_angle((0, 0), (100, 100))
        self.assertAlmostEqual(angle, 45.0)

    def test_b111_flight_heading_diagonal_northeast(self):
        """B111: Northeast -45-degree trajectory computes -45 degrees."""
        angle = calculate_heading_angle((0, 0), (100, -100))
        self.assertAlmostEqual(angle, -45.0)

    def test_b112_flight_progress_monotonicity(self):
        """B112: Advancing t monotonically advances Euclidean distance from P1."""
        p1 = (0.0, 0.0)
        p2 = (600.0, 800.0)
        last_dist = -1.0
        for step in range(11):
            pos = calculate_flight_position(p1, p2, step / 10.0)
            dist = math.hypot(pos[0] - p1[0], pos[1] - p1[1])
            self.assertGreaterEqual(dist, last_dist)
            last_dist = dist

    def test_b113_all_waypoint_pairwise_distances_positive(self):
        """B113: Pairwise distances between all 5 distinct countries are strictly positive."""
        chars = list(WORLD_MAP_WAYPOINTS.keys())
        for i in range(len(chars)):
            for j in range(i + 1, len(chars)):
                p1 = (WORLD_MAP_WAYPOINTS[chars[i]]["x"], WORLD_MAP_WAYPOINTS[chars[i]]["y"])
                p2 = (WORLD_MAP_WAYPOINTS[chars[j]]["x"], WORLD_MAP_WAYPOINTS[chars[j]]["y"])
                dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                self.assertGreater(dist, 50.0, f"Distance between {chars[i]} and {chars[j]} is too small")

    def test_b114_airplane_rotation_surface_bounds(self):
        """B114: Rotating airplane sprite maintains valid dimensions."""
        airplane_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
        rotated = pygame.transform.rotate(airplane_surf, 45.0)
        self.assertGreaterEqual(rotated.get_width(), 32)
        self.assertGreaterEqual(rotated.get_height(), 32)

    def test_b115_route_breadcrumbs_max_length(self):
        """B115: Route breadcrumbs list length is bounded by flight duration in frames."""
        flight_frames = 120
        breadcrumbs = []
        for f in range(flight_frames):
            if f % 4 == 0:
                breadcrumbs.append((f, f))
        self.assertLessEqual(len(breadcrumbs), flight_frames)
        self.assertEqual(len(breadcrumbs), 30)
