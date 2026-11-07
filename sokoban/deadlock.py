"""Deadlock detection for Sokoban puzzle boards.

This module provides static deadlock detection for Sokoban layouts, including
corner deadlocks and line deadlocks along walls. Deadlock positions are cached
per BoardLayout instance.
"""

from .sokoban_puzzle import ACTIONS, BoardLayout, Position, SokobanPuzzle

__all__ = [
    "corner_deadlocks",
    "line_deadlocks",
    "deadlock_positions",
    "hasDeadlock",
    "deadlockBoxes",
    "has_deadlock_incremental",
]

_deadlock_cache: dict[BoardLayout, frozenset[Position]] = {}


def corner_deadlocks(layout: BoardLayout) -> frozenset[Position]:
    """Identify all floor cells that form corner deadlocks.

    A floor cell is a corner deadlock if:
    - It is in layout.walkable (playable floor cell).
    - It is NOT in layout.targets.
    - It has walls on two perpendicular adjacent sides: at least one of
      {up, down} is a wall AND at least one of {left, right} is a wall.

    Args:
        layout: The static board layout.

    Returns:
        A frozenset of board positions that are corner deadlocks.
    """
    walls = layout.walls
    targets = layout.targets
    deadlocks: set[Position] = set()

    for r, c in layout.walkable:
        if (r, c) in targets:
            continue
        has_vertical_wall = (r - 1, c) in walls or (r + 1, c) in walls
        has_horizontal_wall = (r, c - 1) in walls or (r, c + 1) in walls
        if has_vertical_wall and has_horizontal_wall:
            deadlocks.add((r, c))

    return frozenset(deadlocks)


def line_deadlocks(layout: BoardLayout) -> frozenset[Position]:
    """Identify all floor cells that form line deadlocks along walls.

    Connects pairs of corner-deadlock cells on the same row or column where:
    - Every cell between them (inclusive) is walkable and NOT a target.
    - One side of the entire segment is solid wall: either every cell on
      one perpendicular side is a wall, or every cell on the other side is a wall.

    Endpoints are included in the result.

    Args:
        layout: The static board layout.

    Returns:
        A frozenset of board positions that are line deadlocks.
    """
    corners = corner_deadlocks(layout)
    if not corners:
        return frozenset()

    walls = layout.walls
    targets = layout.targets
    walkable = layout.walkable
    deadlocks: set[Position] = set()

    # Group corner deadlocks by row for horizontal line segments
    row_corners: dict[int, list[int]] = {}
    for r, c in corners:
        row_corners.setdefault(r, []).append(c)

    for r, cols in row_corners.items():
        if len(cols) < 2:
            continue
        cols.sort()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c1, c2 = cols[i], cols[j]
                segment = [(r, c) for c in range(c1, c2 + 1)]
                # Every cell between them (inclusive) must be walkable and NOT a target
                if not all(pos in walkable and pos not in targets for pos in segment):
                    continue
                # One side of the entire segment must be solid wall
                up_wall = all((r - 1, c) in walls for c in range(c1, c2 + 1))
                down_wall = all((r + 1, c) in walls for c in range(c1, c2 + 1))
                if up_wall or down_wall:
                    deadlocks.update(segment)

    # Group corner deadlocks by column for vertical line segments
    col_corners: dict[int, list[int]] = {}
    for r, c in corners:
        col_corners.setdefault(c, []).append(r)

    for c, rows in col_corners.items():
        if len(rows) < 2:
            continue
        rows.sort()
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                r1, r2 = rows[i], rows[j]
                segment = [(r, c) for r in range(r1, r2 + 1)]
                # Every cell between them (inclusive) must be walkable and NOT a target
                if not all(pos in walkable and pos not in targets for pos in segment):
                    continue
                # One side of the entire segment must be solid wall
                left_wall = all((r, c - 1) in walls for r in range(r1, r2 + 1))
                right_wall = all((r, c + 1) in walls for r in range(r1, r2 + 1))
                if left_wall or right_wall:
                    deadlocks.update(segment)

    # Exclude the corner deadlock endpoints themselves so line_deadlocks returns
    # strictly the interior wall-line cells (yellow in Figure 6).
    return frozenset(deadlocks - corners)


def deadlock_positions(layout: BoardLayout) -> frozenset[Position]:
    """Return all deadlock positions (corners and lines) for a board layout.

    Computes the union of corner deadlocks and line deadlocks. Target cells
    are never included. Results are cached per BoardLayout.

    Args:
        layout: The static board layout.

    Returns:
        A frozenset of all deadlock positions.
    """
    cached = _deadlock_cache.get(layout)
    if cached is not None:
        return cached

    dead = (corner_deadlocks(layout) | line_deadlocks(layout)) - layout.targets
    result = frozenset(dead)
    _deadlock_cache[layout] = result
    return result


def hasDeadlock(state: SokobanPuzzle) -> bool:
    """Check if any box in the puzzle state occupies a deadlock position.

    Args:
        state: The current Sokoban puzzle state.

    Returns:
        True if at least one box sits on a deadlock position, False otherwise.
    """
    dead = deadlock_positions(state.layout)
    return bool(state.boxes & dead)


def deadlockBoxes(state: SokobanPuzzle) -> frozenset[Position]:
    """Return the set of boxes that occupy deadlock positions.

    Args:
        state: The current Sokoban puzzle state.

    Returns:
        A frozenset of box positions that are deadlocked.
    """
    return state.boxes & deadlock_positions(state.layout)


def has_deadlock_incremental(state: SokobanPuzzle, pushed_box: Position | None) -> bool:
    """Quickly check if the last move pushed a box into a deadlock position.

    If pushed_box is None (a simple player move without a push), returns False.
    Otherwise, checks if the pushed box's new position is a deadlock.

    Args:
        state: The current Sokoban puzzle state.
        pushed_box: The new position of the pushed box, or None if no push occurred.

    Returns:
        True if the pushed box is on a deadlock position, False otherwise.
    """
    if pushed_box is None:
        return False
    return pushed_box in deadlock_positions(state.layout)
