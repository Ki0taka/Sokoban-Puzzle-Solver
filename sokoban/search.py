"""Search algorithms and their result record."""

from collections import deque
from dataclasses import dataclass
import heapq
from itertools import count
import math
from time import perf_counter
from functools import partial
from types import MappingProxyType
from typing import Callable, Mapping

from .deadlock import deadlock_positions, hasDeadlock
from .heuristics import h1, h2, h3, h3_exact
from .node import Node
from .sokoban_puzzle import SokobanPuzzle

Heuristic = Callable[[SokobanPuzzle], int | float]


@dataclass
class SearchResult:
    """The solution, if found, and a few search counters."""

    solution: Node | None
    actions: list[str]
    path: list[SokobanPuzzle]
    cost: int | None
    expanded: int
    generated: int
    max_frontier: int
    elapsed_seconds: float
    incomplete: bool = False
    reopened: int = 0
    algorithm: str = ""
    pruned: int = 0

    @property
    def found(self) -> bool:
        """Whether the search found a solution."""
        return self.solution is not None


def _result(solution: Node | None, expanded: int, generated: int, maximum: int,
            started: float, algorithm: str, incomplete: bool = False,
            reopened: int = 0, pruned: int = 0) -> SearchResult:
    """Build the result and collect the path if a goal was found."""
    elapsed = perf_counter() - started
    if solution is None:
        return SearchResult(None, [], [], None, expanded, generated, maximum,
                            elapsed, incomplete=incomplete, reopened=reopened,
                            algorithm=algorithm, pruned=pruned)
    return SearchResult(solution, solution.getSolution(), solution.getPath(), solution.g,
                        expanded, generated, maximum, elapsed, reopened=reopened,
                        algorithm=algorithm, pruned=pruned)


def bfs(initial_state: SokobanPuzzle, *, use_deadlock: bool = False,
        max_expanded: int | None = None) -> SearchResult:
    """Find a shortest solution with BFS (each move costs one).

    The optional expansion cap is used by benchmarks. Hitting it marks the
    result as incomplete.
    """
    started = perf_counter()
    root = Node(initial_state)
    frontier: deque[Node] = deque([root])
    frontier_states = {initial_state}
    explored: set[SokobanPuzzle] = set()
    generated = 1
    expanded = 0
    maximum = 1
    pruned = 0
    dead = deadlock_positions(initial_state.layout) if use_deadlock else frozenset()
    if initial_state.isGoal():
        return _result(root, expanded, generated, maximum, started, "BFS", pruned=pruned)
    if use_deadlock and hasDeadlock(initial_state):
        return _result(None, expanded, generated, maximum, started, "BFS", pruned=pruned)
    while frontier:
        if max_expanded is not None and expanded >= max_expanded:
            return _result(None, expanded, generated, maximum, started, "BFS", True, pruned=pruned)
        node = frontier.popleft()
        frontier_states.remove(node.state)
        explored.add(node.state)
        expanded += 1
        children = node.expand()
        generated += len(children)
        for child in children:
            state = child.state
            if state in explored or state in frontier_states:
                continue
            if dead:
                new_boxes = child.state.boxes - node.state.boxes
                if new_boxes and next(iter(new_boxes)) in dead:
                    pruned += 1
                    continue
            # Check for a goal as soon as we generate the state.
            if state.isGoal():
                return _result(child, expanded, generated, maximum, started, "BFS", pruned=pruned)
            frontier.append(child)
            frontier_states.add(state)
            maximum = max(maximum, len(frontier))
    return _result(None, expanded, generated, maximum, started, "BFS", pruned=pruned)


def astar(initial_state: SokobanPuzzle, heuristic: Heuristic, *,
          use_deadlock: bool = False,
          max_expanded: int | None = None) -> SearchResult:
    """Run A* with Open and Closed sets.

    Better paths replace Open entries or reopen a state in Closed. Reopening
    matters when the heuristic is inconsistent.
    """
    started = perf_counter()
    heuristic_name = getattr(heuristic, "__name__", "custom")
    algorithm = f"A* ({heuristic_name})"
    root = Node(initial_state)
    root.setF(heuristic)
    pruned = 0
    dead = deadlock_positions(initial_state.layout) if use_deadlock else frozenset()
    if initial_state.isGoal():
        return _result(root, 0, 1, 1, started, algorithm, pruned=pruned)
    if use_deadlock and hasDeadlock(initial_state):
        return _result(None, 0, 1, 1, started, algorithm, pruned=pruned)
    if math.isinf(root.f):
        return _result(None, 0, 1, 1, started, algorithm, pruned=pruned)

    tie_breaker = count()
    open_heap: list[tuple[float, float, int, Node]] = []
    open_nodes: dict[SokobanPuzzle, Node] = {initial_state: root}
    closed_nodes: dict[SokobanPuzzle, Node] = {}
    heapq.heappush(open_heap, (root.f, float(root.f - root.g), next(tie_breaker), root))
    generated = 1
    expanded = 0
    maximum = 1
    reopened = 0

    while open_heap:
        if max_expanded is not None and expanded >= max_expanded:
            return _result(None, expanded, generated, maximum, started, algorithm, True,
                           reopened=reopened, pruned=pruned)
        _, _, _, current = heapq.heappop(open_heap)
        if open_nodes.get(current.state) is not current:
            continue  # stale heap entry superseded by a lower-f node
        del open_nodes[current.state]

        # Test the goal when it comes off the Open heap.
        if current.state.isGoal():
            return _result(current, expanded, generated, maximum, started, algorithm,
                           reopened=reopened, pruned=pruned)

        closed_nodes[current.state] = current
        expanded += 1
        successors = current.state.successorFunction()
        generated += len(successors)
        for action, successor in successors:
            child = Node(successor, current, action)
            child.setF(heuristic)
            if math.isinf(child.f):
                continue  # Only fires for heuristics that return infinity (e.g. h3_exact).

            if dead:
                new_boxes = successor.boxes - current.state.boxes
                if new_boxes and next(iter(new_boxes)) in dead:
                    pruned += 1
                    continue

            open_node = open_nodes.get(successor)
            if open_node is not None:
                if child.f >= open_node.f:
                    continue
                # Leave the old heap entry in place; it will be skipped later.
            else:
                closed_node = closed_nodes.get(successor)
                if closed_node is not None:
                    if child.f >= closed_node.f:
                        continue
                    del closed_nodes[successor]
                    reopened += 1

            open_nodes[successor] = child
            heuristic_value = child.f - child.g
            heapq.heappush(open_heap, (child.f, float(heuristic_value), next(tie_breaker), child))
            maximum = max(maximum, len(open_nodes))

    return _result(None, expanded, generated, maximum, started, algorithm,
                   reopened=reopened, pruned=pruned)


SOLVERS: Mapping[str, Callable[..., SearchResult]] = MappingProxyType({
    "BFS": bfs,
    "BFS + deadlock": partial(bfs, use_deadlock=True),
    "A* (h1)": partial(astar, heuristic=h1),
    "A* (h1) + deadlock": partial(astar, heuristic=h1, use_deadlock=True),
    "A* (h2)": partial(astar, heuristic=h2),
    "A* (h2) + deadlock": partial(astar, heuristic=h2, use_deadlock=True),
    "A* (h3)": partial(astar, heuristic=h3),
    "A* (h3) + deadlock": partial(astar, heuristic=h3, use_deadlock=True),
    "A* (h3) + exact dead squares": partial(astar, heuristic=h3_exact),
})
