"""Nodes used by the search algorithms."""

from __future__ import annotations
from typing import Callable
from typing import Optional
from .sokoban_puzzle import SokobanPuzzle


class Node:
    """One state in the search tree, with a link to its parent."""

    def __init__(self, state: SokobanPuzzle, parent: Optional["Node"] = None,
                 action: str | None = None, g: int | None = None) -> None:
        """Set up a node, using the parent's cost if none was given."""
        self.state = state
        self.parent = parent
        self.action = action
        self.g = (parent.g + 1 if parent is not None else 0) if g is None else g
        self.f: int | float | None = None

    def setF(self, heuristic: Callable[[SokobanPuzzle], int | float]) -> int | float:
        """Store and return this node's A* score, ``g + h``."""
        self.f = self.g + heuristic(self.state)
        return self.f

    def getPath(self) -> list[SokobanPuzzle]:
        """Return the states along the path to this node."""
        path: list[SokobanPuzzle] = []
        node: Node | None = self
        while node is not None:
            path.append(node.state)
            node = node.parent
        path.reverse()
        return path

    def getSolution(self) -> list[str]:
        """Return the moves that lead here."""
        actions: list[str] = []
        node: Node | None = self
        while node is not None and node.parent is not None:
            if node.action is not None:
                actions.append(node.action)
            node = node.parent
        actions.reverse()
        return actions

    def expand(self) -> list["Node"]:
        """Make a child for each legal move."""
        return [Node(state, self, action) for action, state in self.state.successorFunction()]
