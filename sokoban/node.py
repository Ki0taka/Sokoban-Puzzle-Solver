"""Search-tree node for unit-cost search algorithms."""

from __future__ import annotations
from typing import Optional
from .sokoban_puzzle import SokobanPuzzle


class Node:
    """A search node storing state, parent link, action, and path cost."""

    def __init__(self, state: SokobanPuzzle, parent: Optional["Node"] = None,
                 action: str | None = None, g: int | None = None) -> None:
        """Create a node and derive its path cost from its parent when omitted."""
        self.state = state
        self.parent = parent
        self.action = action
        self.g = (parent.g + 1 if parent is not None else 0) if g is None else g

    def getPath(self) -> list[SokobanPuzzle]:
        """Return states from the root node through this node."""
        path: list[SokobanPuzzle] = []
        node: Node | None = self
        while node is not None:
            path.append(node.state)
            node = node.parent
        path.reverse()
        return path

    def getSolution(self) -> list[str]:
        """Return actions from the root node through this node."""
        actions: list[str] = []
        node: Node | None = self
        while node is not None and node.parent is not None:
            if node.action is not None:
                actions.append(node.action)
            node = node.parent
        actions.reverse()
        return actions

    def expand(self) -> list["Node"]:
        """Create child nodes from the state's legal successor pairs."""
        return [Node(state, self, action) for action, state in self.state.successorFunction()]
