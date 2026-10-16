"""Tests for Sokoban modeling, nodes, and BFS optimality."""

import unittest
from pathlib import Path
from sokoban.node import Node
from sokoban.search import bfs
from sokoban.sokoban_puzzle import SokobanPuzzle


class ModelTests(unittest.TestCase):
    """Exercise basic transition and representation rules."""

    def test_round_trip_goal_and_state_hash(self):
        state = SokobanPuzzle.from_lines(["OOOOO", "OR* O", "OOOOO"])
        self.assertEqual(SokobanPuzzle.from_lines(str(state).splitlines()), state)
        self.assertTrue(state.isGoal())
        self.assertEqual(hash(state), hash(SokobanPuzzle.from_lines(str(state).splitlines())))

    def test_moves_pushes_and_blocking(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "ORBS O", "OOOOOO"])
        moves = dict(state.successorFunction())
        self.assertIn("RIGHT", moves)  # pushes the box into free space
        self.assertEqual(moves["RIGHT"].player, (1, 2))
        self.assertEqual(moves["RIGHT"].boxes, frozenset({(1, 3)}))
        self.assertNotIn("UP", moves)
        blocked = SokobanPuzzle.from_lines(["OOOOOO", "ORBBSS", "OOOOOO"])
        self.assertNotIn("RIGHT", dict(blocked.successorFunction()))

    def test_plain_move_no_pull_and_push_blocked_by_wall(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "OR BSO", "OOOOOO"])
        successors = dict(state.successorFunction())
        self.assertIn("RIGHT", successors)  # entering an empty cell
        self.assertNotIn("LEFT", successors)  # wall blocks movement
        # Moving away never changes a box unless the player steps into it.
        self.assertEqual(successors["RIGHT"].boxes, state.boxes)
        against_wall = SokobanPuzzle.from_lines(["OOOOOO", "ORBOOO", "OOSOOO"])
        self.assertNotIn("RIGHT", dict(against_wall.successorFunction()))

    def test_player_and_box_on_target_transitions(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "O B*.O", "O    O", "OOOOOO"])
        self.assertIn(".", str(state))
        self.assertIn("*", str(state))
        moved = dict(state.successorFunction())["DOWN"]
        self.assertNotIn(".", str(moved))
        self.assertIn("S", str(moved))
        self.assertIn("*", str(moved))

    def test_node_path_solution_and_minimal_bfs(self):
        initial = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        root = Node(initial)
        child = Node(dict(initial.successorFunction())["RIGHT"], root, "RIGHT")
        self.assertEqual(child.getPath(), [initial, child.state])
        self.assertEqual(child.getSolution(), ["RIGHT"])
        result = bfs(initial)
        self.assertEqual(result.cost, 1)
        self.assertTrue(result.path[-1].isGoal())
        self.assertEqual(result.cost, result.solution.g)

    def test_validation(self):
        with self.assertRaisesRegex(ValueError, "exactly one player"):
            SokobanPuzzle.from_lines(["OOO", "O O", "OOO"])

    def test_bundled_levels_solve_and_replay(self):
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            initial = SokobanPuzzle.from_file(root / f"level{index}.txt")
            result = bfs(initial)
            self.assertTrue(result.found, f"Level {index} has no solution")
            self.assertEqual(result.cost, len(result.actions))
            self.assertTrue(result.path[-1].isGoal())
            replay = initial
            for action in result.actions:
                replay = dict(replay.successorFunction())[action]
            self.assertTrue(replay.isGoal())


if __name__ == "__main__":
    unittest.main()
