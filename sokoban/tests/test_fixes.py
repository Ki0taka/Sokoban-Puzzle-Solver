"""Checks for search behavior, heuristics, GUI comparisons, and board layouts."""

import math
import queue
import unittest
from collections import deque
from pathlib import Path

from sokoban.heuristics import h1, h3
from sokoban.search import SOLVERS, SearchResult, astar, bfs
from sokoban.sokoban_puzzle import BoardLayout, SokobanPuzzle


class FixVerificationTests(unittest.TestCase):
    """Check the search fixes and GUI comparison behavior."""

    # A* with h1 and h3 should match BFS on every bundled level.

    def test_astar_h1_matches_bfs_cost_on_all_levels(self):
        """A* with h1 should find the same cost as BFS on every level."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(initial)
            astar_result = astar(initial, h1)
            self.assertEqual(astar_result.cost, bfs_result.cost,
                             f"A*(h1) cost differs from BFS on level {index}")

    def test_astar_h3_matches_bfs_cost_on_all_levels(self):
        """A* with h3 should find the same cost as BFS on every level."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            bfs_result = bfs(initial)
            astar_result = astar(initial, h3)
            self.assertEqual(astar_result.cost, bfs_result.cost,
                             f"A*(h3) cost differs from BFS on level {index}")

    # h3 should stay below the remaining solution cost.

    def test_h3_admissible_on_bfs_path_levels_1_to_4(self):
        """h3 should not overestimate along the BFS solution path."""
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

    # Check h1's consistency along a solution path.

    def test_h1_consistency_on_bfs_solution_path(self):
        """h1 should not drop by more than one move at a time."""
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

    # Batch solving should return one result per solver.

    def test_compare_produces_one_result_per_solver(self):
        """The batch run should queue one result for each solver."""
        from sokoban.gui import SokobanGUI
        gui = SokobanGUI()
        gui.level_index = 0
        keys = list(gui.solvers)
        # Set up the same batch used by _start_solve.
        batch = []
        for key in keys:
            gui._next_generation += 1
            gen = gui._next_generation
            gui._request_generations[(0, key)] = gen
            gui.solving_keys.add((0, key))
            batch.append((0, key, gui.solvers[key], gui.levels[0], gen))
        # Run the solvers one after another.
        gui._solve_batch_in_background(batch)
        # Collect the queued results.
        collected: dict[str, SearchResult] = {}
        while not gui.result_queue.empty():
            level_index, key, generation, result, error = gui.result_queue.get()
            self.assertIsNone(error, f"Solver {key} errored: {error}")
            self.assertNotIn(key, collected, f"Duplicate result for {key}")
            collected[key] = result
        self.assertEqual(set(collected), set(keys))

    # Layouts parsed from the same text should compare equal.

    def test_board_layout_equal_for_same_text(self):
        """Parsing the same board twice should give equal layouts."""
        lines = ["OOOOO", "ORBSO", "OOOOO"]
        a = SokobanPuzzle.from_lines(lines)
        b = SokobanPuzzle.from_lines(lines)
        self.assertEqual(a.layout, b.layout)
        self.assertEqual(hash(a.layout), hash(b.layout))

    def test_board_layout_rows_reflect_void_walls(self):
        """Show cells outside the maze as walls."""
        # The top-left corners of level 4 are outside the maze.
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
