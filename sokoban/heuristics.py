"""Admissible and experimental heuristic functions for Sokoban A*."""

from functools import lru_cache
import math
from types import MappingProxyType
from typing import Callable, Mapping
from .sokoban_puzzle import SokobanPuzzle

Heuristic = Callable[[SokobanPuzzle], int | float]


def h1(state: SokobanPuzzle) -> int:
    """Return the number of boxes not currently on a target.

    Every such box needs at least one push, and each push costs one move, so
    this is both admissible and consistent for unit-cost Sokoban actions.
    """
    return sum(1 for box in state.boxes if box not in state.layout.targets)


def h2(state: SokobanPuzzle) -> int:
    """Return the assignment-specified Manhattan estimate from Part 2.

    This is deliberately the formula given in the assignment. The doubled
    misplaced-box term can overestimate, so this heuristic is not admissible
    and does not guarantee optimal A* solutions.
    """
    unplaced = h1(state)
    distance_sum = 0
    for box in state.boxes:
        if box in state.layout.targets:
            continue
        distance_sum += min(
            abs(box[0] - target[0]) + abs(box[1] - target[1])
            for target in state.layout.targets
        )
    return 2 * unplaced + distance_sum


def h3(state: SokobanPuzzle) -> float:
    """Estimate remaining pushes with wall-aware assignment plus approach cost.

    The push-distance matrix was precomputed once when the shared layout was
    parsed. A minimum one-to-one box/target assignment lower-bounds the pushes
    still required. A further walk lower bound is the distance to the nearest
    box minus one, because at least that many player steps are needed to stand
    adjacent before the first push. We measure approach to *any* box, including
    one already on a target: using only unplaced boxes would not be admissible
    when an already-placed box can be pushed first. These move costs are
    disjoint (walk before the first push versus pushes), so their sum is
    admissible. A box on a reverse-push dead square makes the state unsolvable.
    """
    if state.isGoal():
        return 0.0
    layout = state.layout
    for box in state.boxes:
        if box not in layout.targets and box in layout.dead_squares:
            return math.inf

    boxes = tuple(sorted(state.boxes))
    targets = tuple(sorted(layout.targets))

    @lru_cache(maxsize=None)
    def assign(box_index: int, used_targets: int) -> float:
        """Return the cheapest push-distance assignment for remaining boxes."""
        if box_index == len(boxes):
            return 0.0
        box = boxes[box_index]
        row = layout.push_distances[box]
        best = math.inf
        for target_index in range(len(targets)):
            bit = 1 << target_index
            if used_targets & bit:
                continue
            remaining = assign(box_index + 1, used_targets | bit)
            candidate = row[target_index] + remaining
            if candidate < best:
                best = candidate
        return best

    push_lower_bound = assign(0, 0)
    if math.isinf(push_lower_bound):
        return math.inf
    # This bound is zero when standing adjacent to any box; on a push action
    # the parent therefore cannot lose more than the one move being charged.
    approach = max(0, min(
        abs(state.player[0] - box[0]) + abs(state.player[1] - box[1])
        for box in boxes
    ) - 1)
    return push_lower_bound + approach


HEURISTICS: Mapping[str, Heuristic] = MappingProxyType({"h1": h1, "h2": h2, "h3": h3})
HEURISTIC_DESCRIPTIONS: Mapping[str, str] = MappingProxyType({
    "h1": "One lower-bound push for each box not on a target.",
    "h2": "Twice the unplaced boxes plus nearest-target Manhattan distances; not admissible.",
    "h3": "Minimum wall-aware box/target push assignment plus a player approach lower bound.",
})
