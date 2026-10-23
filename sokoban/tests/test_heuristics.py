"""Tests for heuristic values and admissibility on small Sokoban spaces."""

import math
from collections import deque
from pathlib import Path
import unittest

from sokoban.heuristics import h1, h2, h3
from sokoban.sokoban_puzzle import SokobanPuzzle


class HeuristicTests(unittest.TestCase):
    """Check hand-computed values and compare estimates with exact distances."""

    def test_goal_values_and_hand_computed_single_box(self):
        goal = SokobanPuzzle.from_lines(["OOOOO", "OR* O", "OOOOO"])
        self.assertEqual(h1(goal), 0)
        self.assertEqual(h2(goal), 0)
        self.assertEqual(h3(goal), 0)

        one_push_away = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        self.assertEqual(h1(one_push_away), 1)
        self.assertEqual(h2(one_push_away), 3)
        self.assertEqual(h3(one_push_away), 1)

    def test_box_already_on_target_contributes_zero(self):
        state = SokobanPuzzle.from_lines(["OOOOOOO", "O R*BSO", "OOOOOOO"])
        self.assertEqual(h1(state), 1)
        self.assertEqual(h2(state), 3)
        self.assertEqual(h3(state), 1)

    def test_h3_detects_deadlocked_box_and_is_never_negative(self):
        deadlock = SokobanPuzzle.from_lines([
            "OOOOOO", "OB  SO", "O R  O", "OOOOOO",
        ])
        self.assertTrue(math.isinf(h3(deadlock)))
        root = SokobanPuzzle.from_file(Path(__file__).parents[1] / "levels" / "level1.txt")
        pending = deque([root])
        visited = {root}
        while pending:
            state = pending.popleft()
            self.assertGreaterEqual(h3(state), 0)
            for _, successor in state.successorFunction():
                if successor not in visited:
                    visited.add(successor)
                    pending.append(successor)

    def test_h1_and_h3_are_admissible_on_exhaustive_small_state_space(self):
        """Compare estimates against exact reverse distances to any goal state."""
        initial = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        forward: dict[SokobanPuzzle, list[SokobanPuzzle]] = {}
        reverse: dict[SokobanPuzzle, list[SokobanPuzzle]] = {}
        pending = deque([initial])
        states = {initial}
        goals: list[SokobanPuzzle] = []
        while pending:
            state = pending.popleft()
            if state.isGoal():
                goals.append(state)
            children = [successor for _, successor in state.successorFunction()]
            forward[state] = children
            for child in children:
                reverse.setdefault(child, []).append(state)
                if child not in states:
                    states.add(child)
                    pending.append(child)

        exact: dict[SokobanPuzzle, int] = {goal: 0 for goal in goals}
        pending = deque(goals)
        while pending:
            state = pending.popleft()
            for parent in reverse.get(state, []):
                if parent not in exact:
                    exact[parent] = exact[state] + 1
                    pending.append(parent)

        saw_h2_overestimate = False
        for state in states:
            true_cost = exact.get(state, math.inf)
            self.assertLessEqual(h1(state), true_cost)
            self.assertLessEqual(h3(state), true_cost)
            if h2(state) > true_cost:
                saw_h2_overestimate = True
        self.assertTrue(saw_h2_overestimate)

    def test_h1_and_h3_are_consistent_on_small_state_space(self):
        """Check h(n) <= 1 + h(n') for every reachable unit-cost edge."""
        initial = SokobanPuzzle.from_lines(["OOOOO", "ORBSO", "OOOOO"])
        pending = deque([initial])
        visited = {initial}
        while pending:
            state = pending.popleft()
            for _, successor in state.successorFunction():
                self.assertLessEqual(h1(state), 1 + h1(successor))
                self.assertLessEqual(h3(state), 1 + h3(successor))
                if successor not in visited:
                    visited.add(successor)
                    pending.append(successor)


if __name__ == "__main__":
    unittest.main()
