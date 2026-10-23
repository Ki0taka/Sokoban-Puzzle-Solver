"""Graph-search algorithms and shared result records for Sokoban."""

from collections import deque
from dataclasses import dataclass
import heapq
from itertools import count
import math
from time import perf_counter
from functools import partial
from types import MappingProxyType
from typing import Callable, Mapping

from .heuristics import h1, h2, h3
from .node import Node
from .sokoban_puzzle import SokobanPuzzle

Heuristic = Callable[[SokobanPuzzle], int | float]


@dataclass
class SearchResult:
    """Solution and performance counters from a search run."""

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

    @property
    def found(self) -> bool:
        """Return whether a solution node was found."""
        return self.solution is not None


def _result(solution: Node | None, expanded: int, generated: int, maximum: int,
            started: float, algorithm: str, incomplete: bool = False,
            reopened: int = 0) -> SearchResult:
    """Build a result record and reconstruct its path when a goal was found."""
    elapsed = perf_counter() - started
    if solution is None:
        return SearchResult(None, [], [], None, expanded, generated, maximum,
                            elapsed, incomplete=incomplete, reopened=reopened,
                            algorithm=algorithm)
    return SearchResult(solution, solution.getSolution(), solution.getPath(), solution.g,
                        expanded, generated, maximum, elapsed, reopened=reopened,
                        algorithm=algorithm)


def bfs(initial_state: SokobanPuzzle, *, max_expanded: int | None = None) -> SearchResult:
    """Find an optimal solution with graph-search BFS and unit step costs.

    ``max_expanded`` is an optional safety cap used by benchmarks. If reached
    before the frontier is exhausted, the result is marked ``incomplete``.
    """
    started = perf_counter()
    root = Node(initial_state)
    frontier: deque[Node] = deque([root])
    frontier_states = {initial_state}
    explored: set[SokobanPuzzle] = set()
    generated = 1
    expanded = 0
    maximum = 1
    if initial_state.isGoal():
        return _result(root, expanded, generated, maximum, started, "BFS")
    while frontier:
        if max_expanded is not None and expanded >= max_expanded:
            return _result(None, expanded, generated, maximum, started, "BFS", True)
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
            # The course's BFS tests a goal when its node is generated.
            if state.isGoal():
                return _result(child, expanded, generated, maximum, started, "BFS")
            frontier.append(child)
            frontier_states.add(state)
            maximum = max(maximum, len(frontier))
    return _result(None, expanded, generated, maximum, started, "BFS")


def astar(initial_state: SokobanPuzzle, heuristic: Heuristic, *,
          max_expanded: int | None = None) -> SearchResult:
    """Run graph-search A* using the lecture's Open/Closed update rules.

    Open is a min-priority heap ordered by ``(f, h, insertion_order)`` plus a
    state-to-best-node dictionary. Closed maps expanded states to their best
    expanded node. The goal test occurs when a node is dequeued. Better paths
    replace Open entries lazily or reopen a Closed state, which is required for
    inconsistent heuristics.
    """
    started = perf_counter()
    heuristic_name = getattr(heuristic, "__name__", "custom")
    algorithm = f"A* ({heuristic_name})"
    root = Node(initial_state)
    root.setF(heuristic)
    if initial_state.isGoal():
        return _result(root, 0, 1, 1, started, algorithm)
    if math.isinf(root.f):
        return _result(None, 0, 1, 1, started, algorithm)

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
            return _result(None, expanded, generated, maximum, started, algorithm, True)
        _, _, _, current = heapq.heappop(open_heap)
        if open_nodes.get(current.state) is not current:
            continue  # stale heap entry superseded by a lower-f node
        del open_nodes[current.state]

        # Figure 1.29 tests the goal after dequeuing current from Open.
        if current.state.isGoal():
            return _result(current, expanded, generated, maximum, started, algorithm,
                           reopened=reopened)

        closed_nodes[current.state] = current
        expanded += 1
        successors = current.state.successorFunction()
        generated += len(successors)
        for action, successor in successors:
            child = Node(successor, current, action)
            child.setF(heuristic)
            if math.isinf(child.f):
                continue  # h3 uses infinity to identify proven dead squares

            open_node = open_nodes.get(successor)
            if open_node is not None:
                if child.f >= open_node.f:
                    continue
                # Lazy deletion: replace the dictionary value and push a new heap entry.
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
                   reopened=reopened)


SOLVERS: Mapping[str, Callable[..., SearchResult]] = MappingProxyType({
    "BFS": bfs,
    "A* (h1)": partial(astar, heuristic=h1),
    "A* (h2)": partial(astar, heuristic=h2),
    "A* (h3)": partial(astar, heuristic=h3),
})
