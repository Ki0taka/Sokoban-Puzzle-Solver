"""Tests for the issue fixes: search correctness, heuristic properties,
GUI compare logic, and BoardLayout consistency."""

import math
import queue
import unittest
from collections import deque
from pathlib import Path

from sokoban.heuristics import h1, h3
from sokoban.search import SOLVERS, SearchResult, astar, bfs
from sokoban.sokoban_puzzle import BoardLayout, SokobanPuzzle


class FixVerificationTests(unittest.TestCase):
    """Verify that each issue fix works correctly."""

    # --- A* with h1 and h3 matches BFS on all bundled levels ---

    def test_astar_h1_matches_bfs_cost_on_all_levels(self):
        """A* (h1) must return the same optimal cost as BFS on every level."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(initial)
            astar_result = astar(initial, h1)
            self.assertEqual(astar_result.cost, bfs_result.cost,
                             f"A*(h1) cost differs from BFS on level {index}")

    def test_astar_h3_matches_bfs_cost_on_all_levels(self):
        """A* (h3) must return the same optimal cost as BFS on every level."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(initial)
            astar_result = astar(initial, h3)
            self.assertEqual(astar_result.cost, bfs_result.cost,
                             f"A*(h3) cost differs from BFS on level {index}")

    # --- h3 admissibility: h3(state) <= remaining optimal cost on BFS path ---

    def test_h3_admissible_on_bfs_path_levels_1_to_4(self):
        """h3(state) <= remaining optimal cost for every state on BFS solution."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 5):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            result = bfs(initial)
            self.assertTrue(result.found)
            for step, state in enumerate(result.path):
                remaining = result.cost - step
                h = h3(state)
                self.assertLessEqual(h, remaining,
                    f"h3 overestimates on level {index}, step {step}: "
                    f"h3={h}, remaining={remaining}")

    # --- h1 consistency on BFS solution path ---

    def test_h1_consistency_on_bfs_solution_path(self):
        """h1(parent) - h1(child) <= 1 for consecutive states on BFS path."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            result = bfs(initial)
            self.assertTrue(result.found)
            for step in range(len(result.path) - 1):
                parent = result.path[step]
                child = result.path[step + 1]
                diff = h1(parent) - h1(child)
                self.assertLessEqual(diff, 1,
                    f"h1 inconsistency on level {index}, step {step}: "
                    f"h1(parent)={h1(parent)}, h1(child)={h1(child)}")

    # --- Compare path produces one result per solver, no duplicates ---

    def test_compare_produces_one_result_per_solver(self):
        """The batch solver path queues exactly one result per requested key."""
        from sokoban.gui import SokobanGUI
        gui = SokobanGUI()
        gui.level_index = 0
        keys = list(gui.solvers)
        # Build batch manually (mimicking _start_solve with multiple keys).
        batch = []
        for key in keys:
            gui._next_generation += 1
            gen = gui._next_generation
            gui._request_generations[(0, key)] = gen
            gui.solving_keys.add((0, key))
            batch.append((0, key, gui.solvers[key], gui.levels[0], gen))
        # Run sequentially in current thread.
        gui._solve_batch_in_background(batch)
        # Drain queue and collect results.
        collected: dict[str, SearchResult] = {}
        while not gui.result_queue.empty():
            level_index, key, generation, result, error = gui.result_queue.get()
            self.assertIsNone(error, f"Solver {key} errored: {error}")
            self.assertNotIn(key, collected, f"Duplicate result for {key}")
            collected[key] = result
        self.assertEqual(set(collected), set(keys))

    # --- BoardLayout equality and hash for same text ---

    def test_board_layout_equal_for_same_text(self):
        """Two layouts parsed independently from identical text must be equal."""
        lines = ["OOOOO", "ORBSO", "OOOOO"]
        a = SokobanPuzzle.from_lines(lines)
        b = SokobanPuzzle.from_lines(lines)
        self.assertEqual(a.layout, b.layout)
        self.assertEqual(hash(a.layout), hash(b.layout))

    def test_board_layout_rows_reflect_void_walls(self):
        """BoardLayout.rows must show void cells (outside the maze) as walls."""
        # Level 4 has void cells (top-left corners are outside the maze).
        state = SokobanPuzzle.from_file(
            Path(__file__).parents[1] / "levels" / "level4.txt"
        )
        for r, row in enumerate(state.layout.rows):
            for c, symbol in enumerate(row):
                if (r, c) in state.layout.walls:
                    self.assertEqual(symbol, "O",
                        f"rows[{r}][{c}] should be wall 'O' but is '{symbol}'")
                else:
                    self.assertEqual(symbol, " ",
                        f"rows[{r}][{c}] should be empty ' ' but is '{symbol}'")


if __name__ == "__main__":
    unittest.main()
