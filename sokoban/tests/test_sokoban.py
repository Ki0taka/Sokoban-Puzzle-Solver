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

    def test_str_round_trip_on_successor(self):
        """__str__ must produce a valid, parseable board on successor states."""
        state = SokobanPuzzle.from_lines(["OOOOOO", "O R  O", "O B  O", "O S  O", "OOOOOO"])
        after = dict(state.successorFunction())["DOWN"]
        round_tripped = SokobanPuzzle.from_lines(str(after).splitlines())
        self.assertEqual(round_tripped, after)
        text = str(after)
        self.assertEqual(text.count("R"), 1)
        self.assertEqual(text.count("B"), 0)
        self.assertEqual(text.count("*"), 1)

    def test_state_immutability(self):
        """SokobanPuzzle attributes should not be reassignable."""
        state = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        with self.assertRaises(AttributeError):
            state.boxes = frozenset()
        with self.assertRaises(AttributeError):
            state.player = (0, 0)
        with self.assertRaises(AttributeError):
            state.layout = None

    def test_moves_pushes_and_blocking(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "ORBS O", "OOOOOO"])
        moves = dict(state.successorFunction())
        self.assertIn("RIGHT", moves)  # pushes the box into free space
        self.assertEqual(moves["RIGHT"].player, (1, 2))
        self.assertEqual(moves["RIGHT"].boxes, frozenset({(1, 3)}))
        self.assertNotIn("UP", moves)
        blocked = SokobanPuzzle.from_lines(["OOOOOOO", "ORBBSSO", "OOOOOOO"])
        self.assertNotIn("RIGHT", dict(blocked.successorFunction()))

    def test_plain_move_no_pull_and_push_blocked_by_wall(self):
        state = SokobanPuzzle.from_lines(["OOOOOO", "OR BSO", "OOOOOO"])
        successors = dict(state.successorFunction())
        self.assertIn("RIGHT", successors)  # entering an empty cell
        self.assertNotIn("LEFT", successors)  # wall blocks movement
        # Moving away never changes a box unless the player steps into it.
        self.assertEqual(successors["RIGHT"].boxes, state.boxes)
        against_wall = SokobanPuzzle.from_lines(["OOOOOOO", "ORBOOOO", "OSOOOOO", "OOOOOOO"])
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

    def test_bfs_unsolvable_level(self):
        """BFS should return found=False on an unsolvable level without crashing."""
        state = SokobanPuzzle.from_lines(["OOOOO", "OB  O", "OOR O", "O  SO", "OOOOO"])
        result = bfs(state)
        self.assertFalse(result.found)
        self.assertIsNone(result.cost)
        self.assertEqual(result.actions, [])
        self.assertEqual(result.path, [])

    def test_bfs_already_solved(self):
        """BFS on an already-solved puzzle should return cost 0."""
        state = SokobanPuzzle.from_lines(["OOOOO", "OR* O", "OOOOO"])
        result = bfs(state)
        self.assertTrue(result.found)
        self.assertEqual(result.cost, 0)
        self.assertEqual(result.actions, [])
        self.assertEqual(len(result.path), 1)

    def test_multiple_players_rejected(self):
        """A level with more than one player should be rejected."""
        with self.assertRaisesRegex(ValueError, "exactly one player"):
            SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OROOO"])

    def test_bundled_levels_are_enclosed(self):
        """Reachable floor on every bundled board stays inside wall boundaries."""
        root = Path(__file__).parents[1] / "levels"
        for index in range(1, 6):
            state = SokobanPuzzle.from_file(root / f"level{index}.txt")
            for row in range(state.layout.height):
                for column in range(state.layout.width):
                    if row in (0, state.layout.height - 1) or column in (0, state.layout.width - 1):
                        self.assertIn((row, column), state.layout.walls)

    def test_bundled_level_encodings_match_the_figure_reconstruction(self):
        """Guard the five explicitly documented text reconstructions."""
        root = Path(__file__).parents[1] / "levels"
        expected = {
            1: ["OOOOOO", "OS B O", "O OR O", "O    O", "O    O", "OOOOOO"],
            2: ["OOOOOOOOO", "O       O", "O       O", "O  OOO  O", "O    O. O",
                "O     O O", "O  B  O O", "O     O O", "OOOOOOOOO"],
            3: ["OOOOOOOO", "O   O  O", "O  BR  O", "O      O", "OOOOO BO",
                "OOOOO SO", "OOOOO SO", "OOOOOOOO"],
            4: ["OOOOOOOOO", "OO  OOOOO", "OO  OOOOO", "OO *   OO", "OOBOB  OO",
                "O SRS  OO", "O      OO", "OO  OOOOO", "OO  OOOOO", "OOOOOOOOO"],
            5: ["OOOOOOOOOO", "OOO S  OOO", "O        O", "O B R B  O", "O      S O",
                "OOO    OOO", "OOOB   OOO", "OOO  S OOO", "OOO    OOO", "OOOOOOOOOO"],
        }
        for index, lines in expected.items():
            self.assertEqual((root / f"level{index}.txt").read_text(encoding="utf-8").splitlines(), lines)
            state = SokobanPuzzle.from_lines(lines)
            self.assertEqual(len(state.boxes), len(state.layout.targets))

    def test_open_maze_rejected_as_not_enclosed(self):
        """Reachable floor touching the outer grid edge is an invalid level."""
        with self.assertRaisesRegex(ValueError, "level is not enclosed"):
            SokobanPuzzle.from_lines(["R"])

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
