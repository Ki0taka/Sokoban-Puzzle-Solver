"""A* behavior, path replay, re-opening, and optimality tests."""

from pathlib import Path
import unittest

from sokoban.heuristics import h1, h2, h3
from sokoban.node import Node
from sokoban.search import astar, bfs
from sokoban.sokoban_puzzle import SokobanPuzzle


class AStarTests(unittest.TestCase):
    """Verify A* results and their relationship to BFS."""

    @staticmethod
    def replay(initial: SokobanPuzzle, actions: list[str]) -> SokobanPuzzle:
        """Apply an action list independently using the model transitions."""
        state = initial
        for action in actions:
            state = dict(state.successorFunction())[action]
        return state

    def test_node_set_f(self):
        """Node.setF stores and returns g + h(state)."""
        state = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        root = Node(state)
        child_state = dict(state.successorFunction())["RIGHT"]
        child = Node(child_state, root, "RIGHT")
        self.assertEqual(child.setF(lambda _: 7), child.g + 7)
        self.assertEqual(child.f, child.g + 7)
        self.assertIsNone(root.f)

    def test_tiny_solution_initial_goal_and_unsolvable(self):
        tiny = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        for heuristic in (h1, h2, h3):
            result = astar(tiny, heuristic)
            self.assertTrue(result.found)
            self.assertTrue(self.replay(tiny, result.actions).isGoal())
            self.assertEqual(result.cost, len(result.actions))

        goal = SokobanPuzzle.from_lines(["OOOOO", "OR* O", "OOOOO"])
        result = astar(goal, h3)
        self.assertEqual(result.cost, 0)
        self.assertEqual(result.actions, [])
        self.assertEqual(len(result.path), 1)

        deadlock = SokobanPuzzle.from_lines(["OOOOOO", "OB  SO", "O R  O", "OOOOOO"])
        result = astar(deadlock, h3)
        self.assertFalse(result.found)

    def test_inconsistent_h2_reopens_closed_states_and_finds_solution(self):
        """The bundled third example exercises A*'s Closed-state re-opening."""
        initial = SokobanPuzzle.from_file(Path(__file__).parents[1] / "levels" / "level3.txt")
        result = astar(initial, h2)
        self.assertGreater(result.reopened, 0)
        self.assertTrue(result.found)
        self.assertTrue(self.replay(initial, result.actions).isGoal())

    def test_h1_and_h3_match_bfs_cost_on_every_bundled_level(self):
        """Admissible h1 and h3 preserve BFS's optimal solution costs."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            optimal = bfs(initial)
            for heuristic in (h1, h3):
                result = astar(initial, heuristic)
                self.assertEqual(result.cost, optimal.cost, f"level {index}, {heuristic.__name__}")
                self.assertTrue(self.replay(initial, result.actions).isGoal())

    def test_h2_paths_are_valid_without_assuming_optimality(self):
        """h2 is intentionally not constrained to BFS's cost."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            result = astar(initial, h2)
            self.assertTrue(result.found)
            self.assertTrue(self.replay(initial, result.actions).isGoal())


if __name__ == "__main__":
    unittest.main()
