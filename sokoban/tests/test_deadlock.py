"""Tests for deadlock detection: corner, line, soundness, and search integration."""

import os
from pathlib import Path
import unittest

from sokoban.deadlock import (
    corner_deadlocks,
    deadlock_positions,
    deadlockBoxes,
    has_deadlock_incremental,
    hasDeadlock,
    line_deadlocks,
)
from sokoban.heuristics import h1, h2, h3
from sokoban.search import astar, bfs
from sokoban.sokoban_puzzle import SokobanPuzzle


class CornerDeadlockTests(unittest.TestCase):
    """Test static corner deadlock detection on handmade boards."""

    def test_box_in_corner_detected(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "OB  SO", "O R  O", "OOOOOO"])
        corners = corner_deadlocks(state.layout)
        # (1, 1) has wall above (0, 1) and wall left (1, 0)
        self.assertIn((1, 1), corners)

    def test_corner_that_is_target_not_detected(self):
        state = SokobanPuzzle.from_lines(["OOOOO", "OS  O", "O R O", "O B O", "OOOOO"])
        corners = corner_deadlocks(state.layout)
        self.assertNotIn((1, 1), corners)

    def test_box_next_to_only_one_wall_not_detected(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "O    O", "O BS O", "O R  O", "OOOOOO"])
        corners = corner_deadlocks(state.layout)
        # (2, 2) has wall above but not left or right
        self.assertNotIn((2, 2), corners)

    def test_deadlock_boxes_identifies_deadlocked_subset(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "OB  SO", "O R  O", "OOOOOO"])
        self.assertEqual(deadlockBoxes(state), frozenset({(1, 1)}))
        self.assertTrue(hasDeadlock(state))


class LineDeadlockTests(unittest.TestCase):
    """Test line deadlock detection along continuous walls."""

    def test_horizontal_line_along_wall(self):
        state = SokobanPuzzle.from_lines([
            "OOOOOO", "O    O", "O R  O", "O B SO", "OOOOOO",
        ])
        corners = corner_deadlocks(state.layout)
        self.assertIn((3, 1), corners)

    def test_segment_with_target_not_detected(self):
        # Target at (3, 3) between corners (3, 1) and (3, 5) breaks the line deadlock
        state = SokobanPuzzle.from_lines([
            "OOOOOOO", "OS B BO", "O R   O", "O  S  O", "OOOOOOO",
        ])
        lines = line_deadlocks(state.layout)
        # Row 3 segment has a target at (3, 3); it must not be marked as a line deadlock
        self.assertNotIn((3, 2), lines)
        self.assertNotIn((3, 3), lines)
        self.assertNotIn((3, 4), lines)

    def test_segment_with_wall_gap_not_detected(self):
        # A wall with a gap does not form a solid wall side
        state = SokobanPuzzle.from_lines([
            "OOOOOOO",
            "O     O",
            "O R B O",
            "O   B O",
            "OO O SO",
            "OOOO SO",
            "OOOOOOO",
        ])
        # In row 3, cells (3, 1) to (3, 5) do NOT have a solid wall above or below
        lines = line_deadlocks(state.layout)
        self.assertNotIn((3, 2), lines)

    def test_segment_interrupted_by_wall_not_detected(self):
        # A wall tile placed inside the segment prevents line deadlock formation across it
        state = SokobanPuzzle.from_lines([
            "OOOOOOO",
            "O  O  O",
            "OB O SO",
            "O  R  O",
            "OOOOOOO",
        ])
        lines = line_deadlocks(state.layout)
        # (2, 2) and (2, 4) separated by wall (2, 3) cannot form a single line segment
        self.assertNotIn((2, 2), lines)
        self.assertNotIn((2, 4), lines)


class Figure5And6ValidationTests(unittest.TestCase):
    """Validate detected corners and lines against Figure 5 (red) and Figure 6 (yellow)."""

    def test_figure_example_1_corners_and_lines(self):
        state = SokobanPuzzle.from_file(Path(__file__).parents[1] / "levels" / "level6.txt")
        corners = corner_deadlocks(state.layout)
        lines = line_deadlocks(state.layout)
        # Corners (red): 6 corner cells
        expected_corners = {(1, 2), (1, 4), (1, 5), (5, 2), (5, 4), (5, 5)}
        self.assertEqual(corners, expected_corners)
        # Lines (yellow): vertical line along column 5 from row 2 to 4
        expected_lines = {(2, 5), (3, 5), (4, 5)}
        self.assertEqual(lines, expected_lines)

    def test_figure_example_2_corners_and_lines(self):
        state = SokobanPuzzle.from_file(Path(__file__).parents[1] / "levels" / "level7.txt")
        corners = corner_deadlocks(state.layout)
        lines = line_deadlocks(state.layout)
        # Corners (red): 5 corner cells
        expected_corners = {(1, 4), (2, 6), (3, 1), (4, 4), (4, 6)}
        self.assertEqual(corners, expected_corners)
        # Lines (yellow): (3, 6) on right wall, (4, 5) on bottom wall
        expected_lines = {(3, 6), (4, 5)}
        self.assertEqual(lines, expected_lines)


class SoundnessTests(unittest.TestCase):
    """Verify deadlock_positions is a sound subset of exact dead squares for all levels."""

    def test_deadlock_subset_of_exact_dead_squares(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            detected = deadlock_positions(state.layout)
            exact = state.layout.dead_squares
            self.assertTrue(
                detected <= exact,
                f"Level {index}: detected deadlocks {detected - exact} not in exact dead squares",
            )
            # Log / check difference for comparison
            extra = len(exact) - len(detected)
            self.assertGreaterEqual(extra, 0)

    def test_no_targets_in_deadlock_positions(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            detected = deadlock_positions(state.layout)
            self.assertFalse(
                detected & state.layout.targets,
                f"Level {index}: targets found in deadlock positions",
            )

    def test_initial_states_have_no_deadlock(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            self.assertFalse(
                hasDeadlock(state), f"Level {index} initial state has deadlock"
            )

    def test_initial_box_in_corner_returns_unsolvable_quickly(self):
        # A board where an initial box is placed in a corner
        deadlock_initial = SokobanPuzzle.from_lines([
            "OOOOOO",
            "OB  SO",
            "O R  O",
            "OOOOOO",
        ])
        result = astar(deadlock_initial, h3, use_deadlock=True)
        self.assertFalse(result.found)
        self.assertEqual(result.expanded, 0)


class PruningSoundnessTests(unittest.TestCase):
    """Verify deadlock pruning preserves optimal solutions and prunes effectively."""

    def test_astar_h1_deadlock_matches_bfs_cost(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(state)
            astar_result = astar(state, h1, use_deadlock=True)
            self.assertEqual(
                astar_result.cost,
                bfs_result.cost,
                f"A*(h1)+deadlock cost differs from BFS on level {index}",
            )

    def test_astar_h3_deadlock_matches_bfs_cost(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(state)
            astar_result = astar(state, h3, use_deadlock=True)
            self.assertEqual(
                astar_result.cost,
                bfs_result.cost,
                f"A*(h3)+deadlock cost differs from BFS on level {index}",
            )

    def test_h2_with_and_without_deadlock_finds_valid_solution(self):
        root = Path(__file__).parents[1] / "levels"
        for index in (1, 2, 3, 4, 6):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            res_no_dl = astar(state, h2, use_deadlock=False)
            res_dl = astar(state, h2, use_deadlock=True)
            self.assertTrue(res_no_dl.found)
            self.assertTrue(res_dl.found)

    def test_deadlock_pruning_reduces_or_equals_expanded(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            without = astar(state, h3)
            with_dl = astar(state, h3, use_deadlock=True)
            self.assertLessEqual(
                with_dl.expanded,
                without.expanded,
                f"Level {index}: pruning expanded MORE nodes ({with_dl.expanded} > {without.expanded})",
            )


class IncrementalTests(unittest.TestCase):
    """Verify incremental deadlock check matches full check on all transitions."""

    def test_incremental_agrees_with_full(self):
        """On transitions from valid non-deadlocked parents, incremental matches full check across all 7 levels."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 8):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            from collections import deque

            pending = deque([state])
            visited = {state}
            count = 0
            while pending and count < 500:
                current = pending.popleft()
                for action, successor in current.successorFunction():
                    if successor in visited:
                        continue
                    visited.add(successor)
                    new_boxes = successor.boxes - current.boxes
                    pushed_box = next(iter(new_boxes)) if new_boxes else None
                    full = hasDeadlock(successor)
                    incremental = has_deadlock_incremental(successor, pushed_box)
                    self.assertEqual(
                        incremental,
                        full,
                        f"Level {index}: incremental={incremental} != full={full} for pushed_box={pushed_box}",
                    )
                    count += 1
                    if not incremental:
                        pending.append(successor)


class LevelEncodingTests(unittest.TestCase):
    """Guard the Part 3 level text encodings and puzzle integrity."""

    def test_level6_encoding_and_validity(self):
        root = Path(__file__).parents[1] / "levels"
        lines = (root / "level6.txt").read_text(encoding="utf-8").splitlines()
        state = SokobanPuzzle.from_file(root / "level6.txt")
        self.assertEqual(len(state.boxes), 3)
        self.assertEqual(len(state.layout.targets), 3)
        self.assertIsNotNone(state.player)
        result = bfs(state)
        self.assertTrue(result.found)
        self.assertEqual(result.cost, 41)

    def test_level7_encoding_and_validity(self):
        root = Path(__file__).parents[1] / "levels"
        lines = (root / "level7.txt").read_text(encoding="utf-8").splitlines()
        state = SokobanPuzzle.from_file(root / "level7.txt")
        self.assertEqual(len(state.boxes), 4)
        self.assertEqual(len(state.layout.targets), 4)
        self.assertIsNotNone(state.player)
        result = bfs(state)
        self.assertTrue(result.found)
        self.assertEqual(result.cost, 55)


class HeadlessGUISmokeTests(unittest.TestCase):
    """Run a comprehensive headless GUI test with SDL_VIDEODRIVER=dummy."""

    def test_headless_gui_lifecycle(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((1200, 780))

        from sokoban.gui import SokobanGUI

        gui = SokobanGUI()
        gui._load_tileset(pygame)
        self.assertEqual(len(gui.levels), 7)

        # 1. Test cycling all levels 1 to 7
        for i in range(7):
            gui._activate_button(f"level:{i}")
            self.assertEqual(gui.level_index, i)

        # 2. Toggle deadlock pruning
        self.assertFalse(gui.use_deadlock)
        gui._activate_button("toggle_deadlock")
        self.assertTrue(gui.use_deadlock)
        gui._activate_button("toggle_deadlock")
        self.assertFalse(gui.use_deadlock)

        # 3. Toggle overlay
        self.assertFalse(gui.show_overlay)
        gui._activate_button("toggle_overlay")
        self.assertTrue(gui.show_overlay)

        # 4. Switch algorithms and heuristics
        gui._activate_button("algorithm:A*")
        self.assertEqual(gui.selected_algorithm, "A*")
        gui._activate_button("heuristic:h2")
        self.assertEqual(gui.selected_heuristic, "h2")
        gui._activate_button("heuristic:h3")
        self.assertEqual(gui.selected_heuristic, "h3")
        gui._activate_button("algorithm:BFS")
        self.assertEqual(gui.selected_algorithm, "BFS")

        # 5. Solve on level 0 with BFS + deadlock
        gui._toggle_deadlock()
        gui._change_level(0)
        key = gui._selected_key()
        self.assertEqual(key, "BFS + deadlock")
        res = gui.solvers[key](gui.levels[0])
        self.assertTrue(res.found)
        gui.results[gui._current_cache_key()] = res
        self.assertIsNotNone(gui._current_result())

        # 6. Test rendering pipeline without errors
        buttons = gui._layout_buttons(pygame, 1200)
        self.assertGreaterEqual(len(buttons), 13)
        gui._draw_controls(pygame, screen, buttons)
        panel_x = min(820, screen.get_width() - 360)
        gui._draw_board(pygame, screen, res.path[0], panel_x, screen.get_height())
        gui._draw_info(pygame, screen, panel_x, res)
        pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
