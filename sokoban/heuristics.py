"""Heuristics used by Sokoban's A* search."""

from functools import lru_cache
import math
from types import MappingProxyType
from typing import Callable, Mapping
from .sokoban_puzzle import SokobanPuzzle

Heuristic = Callable[[SokobanPuzzle], int | float]


def h1(state: SokobanPuzzle) -> int:
    """Count boxes that are not on targets.

    Every such box needs at least one push, and each push costs one move, so
    this is both admissible and consistent for unit-cost Sokoban actions.
    """
    return sum(1 for box in state.boxes if box not in state.layout.targets)


def h2(state: SokobanPuzzle) -> int:
    """Compute the Manhattan estimate used in Part 2.

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


@lru_cache(maxsize=8192)
def _min_assignment(cost_rows: tuple[tuple[float, ...], ...]) -> float:
    """Find the cheapest box-to-target assignment using cached bitmask DP."""
    n = len(cost_rows)
    if n == 0:
        return 0.0
    n_targets = len(cost_rows[0])
    # For each mask, keep the cheapest way to assign that many boxes to its targets.
    prev: dict[int, float] = {0: 0.0}
    for box_index in range(n):
        row = cost_rows[box_index]
        curr: dict[int, float] = {}
        for mask, cost in prev.items():
            for t in range(n_targets):
                bit = 1 << t
                if mask & bit:
                    continue
                new_mask = mask | bit
                candidate = cost + row[t]
                if new_mask not in curr or candidate < curr[new_mask]:
                    curr[new_mask] = candidate
        prev = curr
    return min(prev.values()) if prev else math.inf


def h3(state: SokobanPuzzle) -> float:
    """Estimate the remaining pushes, accounting for walls and approach moves.

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
    cost_rows = tuple(layout.push_distances[box] for box in boxes)
    push_lower_bound = _min_assignment(cost_rows)
    if math.isinf(push_lower_bound):
        return math.inf
    # Standing next to a box makes this zero; a push can lower it by at most one.
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
