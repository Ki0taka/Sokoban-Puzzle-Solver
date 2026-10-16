"""Graph-search algorithms for Sokoban."""

from collections import deque
from dataclasses import dataclass
from time import perf_counter
from .node import Node
from .sokoban_puzzle import SokobanPuzzle


@dataclass
class SearchResult:
    """Outcome and performance counters for one search run."""

    solution: Node | None
    actions: list[str]
    path: list[SokobanPuzzle]
    cost: int | None
    expanded: int
    generated: int
    max_frontier: int
    elapsed_seconds: float

    @property
    def found(self) -> bool:
        """Return whether a solution node was found."""
        return self.solution is not None


def bfs(initial_state: SokobanPuzzle) -> SearchResult:
    """Find an optimal solution using graph-search breadth-first search."""
    started = perf_counter()
    root = Node(initial_state)
    frontier: deque[Node] = deque([root])
    frontier_states = {initial_state}
    explored: set[SokobanPuzzle] = set()
    generated = 1
    expanded = 0
    maximum = 1
    if initial_state.isGoal():
        return SearchResult(root, [], [initial_state], 0, 0, 1, 1, perf_counter() - started)
    solution: Node | None = None
    while frontier:
        node = frontier.popleft()
        frontier_states.remove(node.state)
        explored.add(node.state)
        expanded += 1
        for child in node.expand():
            generated += 1
            state = child.state
            if state in explored or state in frontier_states:
                continue
            if state.isGoal():
                solution = child
                frontier.clear()
                break
            frontier.append(child)
            frontier_states.add(state)
        maximum = max(maximum, len(frontier))
        if solution is not None:
            break
    elapsed = perf_counter() - started
    if solution is None:
        return SearchResult(None, [], [], None, expanded, generated, maximum, elapsed)
    return SearchResult(solution, solution.getSolution(), solution.getPath(), solution.g,
                        expanded, generated, maximum, elapsed)
