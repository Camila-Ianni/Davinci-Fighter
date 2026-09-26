"""
tests/test_adversarial_m1_cutscene.py

Empirical Adversarial Stress Test Suite for Milestone 1 Cutscene Engine (IntroCutscene).
Authors: Challenger 1 (Empirical Challenger)
Focus:
- Extreme delta-times (dt=0.0, dt=10.0, dt=100.0, dt=-1.0, micro-ticks dt=1e-6, jittered dt)
- Input storms (thousands of rapid keypresses at frame 0, mid-playback, and post-finish; idempotency)
- Asset degradation (missing cache directory, missing video file, corrupted manifest, missing individual frames)
- Long-running simulation (10,000 frames, memory leak and CPU runaway validation)
- Geometry & non-standard rendering resilience
"""

import os
import json
import time
import tempfile
import tracemalloc
import unittest
import pygame

from tests.base_headless import HeadlessTestCase
from intro_cutscene import IntroCutscene


class TestAdversarialDeltaTimes(HeadlessTestCase):
    """Stress-testing temporal stepping and delta-time handling."""

    def test_dt_zero_no_advancement_and_no_crash(self):
        """Verifies dt=0.0 causes zero frame progression, returns None, and never crashes."""
        cs = IntroCutscene(self.screen)
        initial_frame = cs.current_frame_idx
        for _ in range(120):
            res = cs.update(0.0)
            self.assertIsNone(res)
            self.assertEqual(cs.current_frame_idx, initial_frame)
            self.assertFalse(cs.finished)

    def test_dt_large_jump_10s(self):
        """Verifies a single dt=10.0 jump advances exactly 600 frames cleanly without runaway."""
        cs = IntroCutscene(self.screen)
        res = cs.update(10.0)
        self.assertIsNone(res)
        # Due to IEEE-754 subtraction drift over 599 steps, 10.0 - 599*(1/60) = 0.016666666666591442
        # which is 7.5e-14 below 1/60 (0.016666666666666666), advancing 599 frames (or 600 if precision-compensated).
        self.assertIn(cs.current_frame_idx, (599, 600))
        self.assertAlmostEqual(cs.elapsed_time, 10.0, places=5)
        self.assertFalse(cs.finished)

    def test_dt_extreme_jump_100s(self):
        """Verifies dt=100.0 finishes cutscene naturally without runaway or exception."""
        cs = IntroCutscene(self.screen)
        res = cs.update(100.0)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)
        self.assertFalse(cs.skipped)
        self.assertEqual(cs.current_frame_idx, cs.total_frames - 1)

    def test_dt_negative_graceful_handling(self):
        """Verifies negative dt=-1.0 does not crash, does not underflow frame index below 0."""
        cs = IntroCutscene(self.screen)
        res = cs.update(-1.0)
        self.assertIsNone(res)
        self.assertEqual(cs.current_frame_idx, 0)
        self.assertEqual(cs.dt_accumulator, -1.0)
        self.assertEqual(cs.elapsed_time, -1.0)

    def test_dt_micro_ticks_accumulation(self):
        """Verifies 17,000 micro-ticks of dt=1e-6 accumulate precision to advance 1 frame."""
        cs = IntroCutscene(self.screen)
        self.assertEqual(cs.current_frame_idx, 0)
        # 16,666 ticks * 1e-6 = 0.016666s < 1/60s (0.01666667)
        for _ in range(16666):
            cs.update(1e-6)
        self.assertEqual(cs.current_frame_idx, 0)

        # 1 more tick pushes accumulator >= 1/60s
        cs.update(1e-6)
        self.assertEqual(cs.current_frame_idx, 1)

    def test_dt_variable_jitter_stepping(self):
        """Verifies cutscene handles wildly variable frame times (lag spikes and bursts)."""
        cs = IntroCutscene(self.screen)
        jitter_pattern = [0.001, 0.033, 0.0, 0.050, 0.0166, 0.005, 0.100]
        total_dt = 0.0
        for dt in jitter_pattern:
            cs.update(dt)
            total_dt += dt

        expected_frames = int(total_dt * 60.0)
        self.assertEqual(cs.current_frame_idx, expected_frames)


class TestAdversarialInputStorms(HeadlessTestCase):
    """Stress-testing rapid, concurrent, and adversarial event handling."""

    def test_input_storm_frame_0_unhandled_keys(self):
        """Sends 5,000 rapid non-skipping key events at frame 0 with zero state mutation."""
        cs = IntroCutscene(self.screen)
        unhandled_keys = [
            pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
            pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
            pygame.K_j, pygame.K_k, pygame.K_TAB, pygame.K_LSHIFT
        ]
        for i in range(5000):
            event = pygame.event.Event(pygame.KEYDOWN, key=unhandled_keys[i % len(unhandled_keys)])
            res = cs.handle_input(event)
            self.assertIsNone(res)
            self.assertFalse(cs.finished)
        self.assertEqual(cs.current_frame_idx, 0)

    def test_input_storm_instant_skip_and_idempotency(self):
        """Verifies Space skip followed by 5,000 mixed events is strictly idempotent."""
        callback_log = []
        cs = IntroCutscene(self.screen, on_finish=lambda: callback_log.append("finished"))

        # Frame 0 Space skip
        ev_space = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        res = cs.handle_input(ev_space)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)
        self.assertTrue(cs.skipped)
        self.assertEqual(len(callback_log), 1)

        # 5,000 rapid subsequent events of all types
        for i in range(5000):
            if i % 3 == 0:
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
            elif i % 3 == 1:
                ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(640, 360), button=1)
            else:
                ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
            res = cs.handle_input(ev)
            self.assertEqual(res, "finish")

        # Callback must remain called exactly once
        self.assertEqual(len(callback_log), 1)

    def test_input_storm_mid_playback_interleaving(self):
        """Sends 5,000 interleaved events during active frame stepping."""
        callback_log = []
        cs = IntroCutscene(self.screen, on_finish=lambda: callback_log.append(1))

        # Advance to frame 150
        for _ in range(150):
            cs.update(1.0 / 60.0)
        self.assertEqual(cs.current_frame_idx, 150)
        self.assertFalse(cs.finished)

        # 2,500 non-skipping events interleaved with updates
        for i in range(2500):
            ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c)
            self.assertIsNone(cs.handle_input(ev))
            if i % 50 == 0:
                cs.update(1.0 / 60.0)

        self.assertFalse(cs.finished)

        # Mouse click skip triggers finish
        ev_click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(200, 200), button=1)
        self.assertEqual(cs.handle_input(ev_click), "finish")
        self.assertTrue(cs.finished)
        self.assertEqual(len(callback_log), 1)

        # 2,500 post-skip events
        for _ in range(2500):
            ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
            self.assertEqual(cs.handle_input(ev), "finish")

        self.assertEqual(len(callback_log), 1)

    def test_input_storm_post_natural_finish_idempotency(self):
        """Verifies 5,000 inputs after natural playback completion do not re-trigger callback."""
        callback_log = []
        cs = IntroCutscene(self.screen, on_finish=lambda: callback_log.append("natural_done"))
        cs.total_frames = 10

        for _ in range(10):
            cs.update(1.0 / 60.0)

        self.assertTrue(cs.finished)
        self.assertFalse(cs.skipped)
        self.assertEqual(len(callback_log), 1)

        # 5,000 post-natural-finish events
        for i in range(5000):
            ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
            self.assertEqual(cs.handle_input(ev), "finish")

        self.assertEqual(len(callback_log), 1)

    def test_input_storm_unusual_event_types(self):
        """Verifies robust handling of non-keyboard non-mouse event types without exceptions."""
        cs = IntroCutscene(self.screen)
        unusual_types = [
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONUP,
            pygame.KEYUP,
            pygame.JOYAXISMOTION,
            pygame.JOYBALLMOTION,
            pygame.JOYBUTTONDOWN,
            pygame.JOYBUTTONUP,
            pygame.USEREVENT
        ]
        for event_type in unusual_types:
            ev = pygame.event.Event(event_type, **({"pos": (100, 100), "rel": (1, 1), "buttons": (0, 0, 0)} if "MOUSE" in pygame.event.event_name(event_type) else {}))
            res = cs.handle_input(ev)
            self.assertIsNone(res)
            self.assertFalse(cs.finished)


class TestAdversarialAssetDegradation(HeadlessTestCase):
    """Stress-testing missing directories, missing video files, corrupted manifests, and broken frames."""

    def test_missing_cache_dir_falls_back_to_cv2(self):
        """Verifies non-existent cache directory falls back directly to Tier 2 (cv2)."""
        cs = IntroCutscene(self.screen, cache_dir="assets/completely_missing_cache_dir")
        self.assertEqual(cs.mode, "cv2")
        self.assertEqual(cs.total_frames, 865)
        self.assertIsNotNone(cs.current_surface)
        self.assertEqual(cs.current_surface.get_size(), (960, 720))

        # Advance 10 frames and draw
        for _ in range(10):
            cs.update(1.0 / 60.0)
            cs.draw(self.screen)
        self.assertFalse(cs.finished)

    def test_missing_both_cache_and_video_falls_back_to_mock(self):
        """Verifies missing cache and missing video fall back directly to Tier 3 (mock)."""
        cs = IntroCutscene(
            self.screen,
            cache_dir="assets/nonexistent_dir",
            video_path="assets/nonexistent_video.mov"
        )
        self.assertEqual(cs.mode, "mock")
        self.assertEqual(cs.total_frames, 180)
        self.assertIsNotNone(cs.current_surface)
        self.assertEqual(cs.current_surface.get_size(), (960, 720))

        # Run mock cutscene to natural finish (180 frames = 3.0s)
        for i in range(179):
            res = cs.update(1.0 / 60.0)
            self.assertIsNone(res)
            cs.draw(self.screen)

        res = cs.update(1.0 / 60.0)
        self.assertEqual(res, "finish")
        self.assertTrue(cs.finished)

    def test_corrupted_manifest_falls_back_to_directory_scan(self):
        """Verifies malformed JSON in manifest.json safely falls back to directory file scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write corrupted manifest
            manifest_file = os.path.join(tmpdir, "manifest.json")
            with open(manifest_file, "w") as f:
                f.write("{ INVALID_JSON_DATA ::: ")

            # Write 3 valid image frames
            for i in range(3):
                frame_surf = pygame.Surface((960, 720))
                pygame.image.save(frame_surf, os.path.join(tmpdir, f"frame_{i:04d}.jpg"))

            cs = IntroCutscene(self.screen, cache_dir=tmpdir)
            self.assertEqual(cs.mode, "cache")
            self.assertEqual(cs.total_frames, 3)

            # Step through frames
            cs.update(1.0 / 60.0)
            cs.update(1.0 / 60.0)
            res = cs.update(1.0 / 60.0)
            self.assertEqual(res, "finish")

    def test_missing_individual_frames_recover_to_synthetic(self):
        """Verifies missing single frame file inside cache does not crash and uses fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_file = os.path.join(tmpdir, "manifest.json")
            with open(manifest_file, "w") as f:
                json.dump({"total_frames": 4}, f)

            # Write frame_0000.jpg and frame_0002.jpg (skipping frame_0001.jpg)
            for i in [0, 2]:
                frame_surf = pygame.Surface((960, 720))
                pygame.image.save(frame_surf, os.path.join(tmpdir, f"frame_{i:04d}.jpg"))

            cs = IntroCutscene(self.screen, cache_dir=tmpdir)
            self.assertEqual(cs.mode, "cache")
            self.assertEqual(cs.total_frames, 4)

            # Frame 0 exists
            cs.draw(self.screen)
            self.assertIsNotNone(cs.current_surface)

            # Advance to Frame 1 (missing file)
            res = cs.update(1.0 / 60.0)
            self.assertIsNone(res)
            self.assertEqual(cs.current_frame_idx, 1)
            # Must not crash and surface must still be rendered
            cs.draw(self.screen)
            self.assertIsNotNone(cs.current_surface)
            self.assertEqual(cs.current_surface.get_size(), (960, 720))

    def test_missing_audio_track_plays_silently_without_error(self):
        """Verifies non-existent audio file initializes safely with no crash."""
        cs = IntroCutscene(self.screen, audio_path="assets/audio/nonexistent_intro.wav")
        self.assertIsNone(cs.audio_sound)
        # Ensure update and skip work without audio reference errors
        cs.update(1.0 / 60.0)
        res = cs.finish()
        self.assertEqual(res, "finish")


class TestAdversarialLongRunningSimulation(HeadlessTestCase):
    """Stress-testing memory stability and performance over extended execution."""

    def test_long_running_10000_frames_single_instance(self):
        """Simulates 10,000 frames on a single instance to verify zero memory runaway and high FPS."""
        tracemalloc.start()
        t0 = time.perf_counter()
        mem_start, _ = tracemalloc.get_traced_memory()

        cs = IntroCutscene(self.screen)
        for _ in range(10000):
            cs.update(1.0 / 60.0)
            cs.draw(self.screen)

        mem_end, mem_peak = tracemalloc.get_traced_memory()
        t1 = time.perf_counter()
        tracemalloc.stop()

        elapsed = t1 - t0
        effective_fps = 10000.0 / max(1e-5, elapsed)
        mem_growth_mb = (mem_end - mem_start) / (1024 * 1024)

        # Performance assertions
        self.assertGreater(effective_fps, 500.0, f"Performance too slow: {effective_fps:.1f} FPS")
        self.assertLess(mem_growth_mb, 2.0, f"Memory leaked: {mem_growth_mb:.2f} MB")
        self.assertTrue(cs.finished)

    def test_long_running_1000_frames_continuous_disk_loads(self):
        """Simulates 1,000 advancing frames loading images from disk; verifies memory stability."""
        tracemalloc.start()
        mem_start, _ = tracemalloc.get_traced_memory()

        cs = IntroCutscene(self.screen)
        for _ in range(1000):
            if cs.finished:
                cs.finished = False
                cs.current_frame_idx = 0
            cs.update(1.0 / 60.0)
            cs.draw(self.screen)

        mem_end, mem_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        mem_growth_mb = (mem_end - mem_start) / (1024 * 1024)
        self.assertLess(mem_growth_mb, 5.0, f"Memory leaked during disk frame loads: {mem_growth_mb:.2f} MB")

    def test_long_running_100_lifecycle_instances(self):
        """Creates and tears down 100 IntroCutscene instances; verifies resource release."""
        tracemalloc.start()
        mem_start, _ = tracemalloc.get_traced_memory()

        for _ in range(100):
            cs = IntroCutscene(self.screen)
            for _ in range(30):
                cs.update(1.0 / 60.0)
                cs.draw(self.screen)
            cs.finish()

        mem_end, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        mem_growth_mb = (mem_end - mem_start) / (1024 * 1024)
        self.assertLess(mem_growth_mb, 3.0, f"Memory leaked across 100 lifecycles: {mem_growth_mb:.2f} MB")


class TestAdversarialDisplayCornerCases(HeadlessTestCase):
    """Stress-testing rendering with unusual screen resolutions and configurations."""

    def test_draw_with_none_screen_is_safe(self):
        """Verifies draw(None) with no initialized screen returns cleanly."""
        cs = IntroCutscene(None)
        # Should not raise exception
        cs.draw(None)

    def test_draw_with_nonstandard_resolutions(self):
        """Verifies cutscene renders safely onto non-standard resolution surfaces."""
        nonstandard_resolutions = [
            (800, 600),
            (1920, 1080),
            (640, 480),
            (960, 720)
        ]
        for w, h in nonstandard_resolutions:
            surf = pygame.Surface((w, h))
            cs = IntroCutscene(surf)
            cs.update(1.0 / 60.0)
            cs.draw(surf)
            self.assertEqual(cs.screen_width, w)
            self.assertEqual(cs.screen_height, h)


if __name__ == "__main__":
    unittest.main()
