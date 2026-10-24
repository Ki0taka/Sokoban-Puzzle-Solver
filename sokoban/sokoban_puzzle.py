"""Sokoban board and state representation."""

from dataclasses import dataclass, field
from collections import deque
import math
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

Position = tuple[int, int]
UP = "UP"
DOWN = "DOWN"
LEFT = "LEFT"
RIGHT = "RIGHT"
ACTIONS: tuple[tuple[str, Position], ...] = (
    (UP, (-1, 0)), (DOWN, (1, 0)), (LEFT, (0, -1)), (RIGHT, (0, 1)),
)
PLAYER, WALL, EMPTY, TARGET, BOX = "R", "O", " ", "S", "B"
PLAYER_ON_TARGET, BOX_ON_TARGET = ".", "*"
VALID_SYMBOLS = {PLAYER, WALL, EMPTY, TARGET, BOX, PLAYER_ON_TARGET, BOX_ON_TARGET}


@dataclass(frozen=True)
class BoardLayout:
    """Board details shared by states from the same level."""

    rows: tuple[str, ...]
    width: int
    height: int
    walls: frozenset[Position]
    targets: frozenset[Position]
    walkable: frozenset[Position] = field(default_factory=frozenset, compare=False, hash=False, repr=False)
    push_distances: Mapping[Position, tuple[float, ...]] = field(
        default_factory=lambda: MappingProxyType({}), compare=False, hash=False, repr=False
    )
    dead_squares: frozenset[Position] = field(default_factory=frozenset, compare=False, hash=False, repr=False)


class SokobanPuzzle:
    """A board state; only the player and box positions change.

    Construct from encoded board lines or use ``from_lines``/``from_file``.
    ``lines`` and ``layout`` are mutually exclusive; internal construction
    with a layout is intended for generating successor states.
    """

    __slots__ = ("layout", "player", "boxes")

    def __setattr__(self, name: str, value: object) -> None:
        """Let fields be set during setup, then keep the state fixed."""
        if name not in self.__slots__ or hasattr(self, name):
            raise AttributeError(f"{type(self).__name__} attribute {name!r} is immutable")
        object.__setattr__(self, name, value)

    def __init__(self, lines: Iterable[str] | None = None, *, layout: BoardLayout | None = None,
                 player: Position | None = None, boxes: Iterable[Position] = ()) -> None:
        """Create a board state from text or existing board data."""
        if layout is None:
            if lines is None:
                raise ValueError("Provide board lines or a shared layout")
            parsed, parsed_player, parsed_boxes = self._parse_lines(lines)
            self.layout = parsed
            self.player = parsed_player
            self.boxes = frozenset(parsed_boxes)
        else:
            if lines is not None or player is None:
                raise ValueError("Internal states require layout and player only")
            self.layout = layout
            self.player = player
            self.boxes = frozenset(boxes)
            self._validate_dynamic_state()

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> tuple[BoardLayout, Position, frozenset[Position]]:
        """Parse the rows, padding shorter ones with walls."""
        source = [line.rstrip("\r\n") for line in lines]
        if not source:
            raise ValueError("A level must contain at least one row")
        if any(symbol not in VALID_SYMBOLS for row in source for symbol in row):
            raise ValueError("Level contains an unsupported cell symbol")
        width = max(map(len, source))
        # Treat missing cells in short rows as walls.
        rows = tuple(row.ljust(width, WALL) for row in source)
        walls: set[Position] = set()
        targets: set[Position] = set()
        players: list[Position] = []
        boxes: set[Position] = set()
        for r, row in enumerate(rows):
            for c, symbol in enumerate(row):
                pos = (r, c)
                if symbol == WALL:
                    walls.add(pos)
                elif symbol in (TARGET, PLAYER_ON_TARGET, BOX_ON_TARGET):
                    targets.add(pos)
                    if symbol == PLAYER_ON_TARGET:
                        players.append(pos)
                    elif symbol == BOX_ON_TARGET:
                        boxes.add(pos)
                elif symbol == PLAYER:
                    players.append(pos)
                elif symbol == BOX:
                    boxes.add(pos)
        if len(players) != 1:
            raise ValueError(f"A level must contain exactly one player; found {len(players)}")
        if len(boxes) != len(targets):
            raise ValueError(f"Level has {len(boxes)} boxes and {len(targets)} targets")
        walkable = {
            (r, c)
            for r in range(len(rows))
            for c in range(width)
            if (r, c) not in walls
        }
        reached: set[Position] = {players[0]}
        pending: deque[Position] = deque([players[0]])
        while pending:
            row, column = pending.popleft()
            for _, (dr, dc) in ACTIONS:
                neighbor = (row + dr, column + dc)
                if neighbor in walkable and neighbor not in reached:
                    reached.add(neighbor)
                    pending.append(neighbor)
        if any(row in (0, len(rows) - 1) or column in (0, width - 1)
               for row, column in reached):
            raise ValueError("level is not enclosed")
        if (set(boxes) | targets) - reached:
            raise ValueError("level contains a box or target outside the playable maze")
        # Disconnected floor cells are outside the playable maze.
        walls.update(walkable - reached)
        walkable = frozenset(reached)
        push_distances = _compute_push_distances(
            width, len(rows), frozenset(walls), frozenset(targets)
        )
        static_rows = tuple(
            "".join(WALL if (r, c) in walls else EMPTY for c in range(width))
            for r in range(len(rows))
        )
        dead_squares = frozenset(
            cell for cell, distances in push_distances.items()
            if not any(math.isfinite(distance) for distance in distances)
        )
        layout = BoardLayout(
            static_rows, width, len(rows), frozenset(walls), frozenset(targets),
            walkable, MappingProxyType(push_distances), frozenset(dead_squares),
        )
        return layout, players[0], frozenset(boxes)

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "SokobanPuzzle":
        """Build a puzzle from rows, or raise ValueError if they are invalid."""
        return cls(lines)

    @classmethod
    def from_file(cls, path: str | Path) -> "SokobanPuzzle":
        """Read a level file as UTF-8."""
        return cls.from_lines(Path(path).read_text(encoding="utf-8").splitlines())

    def _validate_dynamic_state(self) -> None:
        """Check that no objects overlap or sit in blocked cells."""
        walkable = {(r, c) for r in range(self.layout.height) for c in range(self.layout.width)} - self.layout.walls
        if self.player not in walkable or self.player in self.boxes:
            raise ValueError("Player must occupy an unblocked cell distinct from all boxes")
        if not self.boxes <= walkable or self.player in self.boxes:
            raise ValueError("Boxes must occupy unblocked cells distinct from the player")
        if len(self.boxes) != len(self.layout.targets):
            raise ValueError("Internal state must preserve the level's number of boxes")

    def isGoal(self) -> bool:
        """Check whether all boxes are on targets."""
        return self.boxes == self.layout.targets

    def successorFunction(self) -> list[tuple[str, "SokobanPuzzle"]]:
        """Return the legal moves and the states they lead to."""
        successors: list[tuple[str, SokobanPuzzle]] = []
        for action, (dr, dc) in ACTIONS:
            adjacent = (self.player[0] + dr, self.player[1] + dc)
            if not self._is_walkable(adjacent):
                continue
            new_boxes = self.boxes
            if adjacent in self.boxes:
                beyond = (adjacent[0] + dr, adjacent[1] + dc)
                if not self._is_walkable(beyond) or beyond in self.boxes:
                    continue
                new_boxes = (self.boxes - {adjacent}) | {beyond}
            successors.append((action, self._from_successor(self.layout, adjacent, new_boxes)))
        return successors

    @classmethod
    def _from_successor(cls, layout: BoardLayout, player: Position,
                        boxes: frozenset[Position]) -> "SokobanPuzzle":
        """Make a successor using the board data already in memory."""
        state = cls.__new__(cls)
        object.__setattr__(state, "layout", layout)
        object.__setattr__(state, "player", player)
        object.__setattr__(state, "boxes", boxes)
        return state

    def _is_walkable(self, position: Position) -> bool:
        """Check whether a position is on open floor."""
        row, column = position
        return (0 <= row < self.layout.height and 0 <= column < self.layout.width
                and position not in self.layout.walls)

    def __eq__(self, other: object) -> bool:
        """Compare states on the same board."""
        return isinstance(other, SokobanPuzzle) and self.layout == other.layout and self.player == other.player and self.boxes == other.boxes

    def __hash__(self) -> int:
        """Hash the player, boxes, and board."""
        return hash((self.layout, self.player, self.boxes))

    def __str__(self) -> str:
        """Draw the board using Sokoban's text symbols."""
        board = [
            [WALL if (r, c) in self.layout.walls else EMPTY
             for c in range(self.layout.width)]
            for r in range(self.layout.height)
        ]
        for r, c in self.layout.targets:
            board[r][c] = TARGET
        for r, c in self.boxes:
            board[r][c] = BOX_ON_TARGET if (r, c) in self.layout.targets else BOX
        r, c = self.player
        board[r][c] = PLAYER_ON_TARGET if self.player in self.layout.targets else PLAYER
        return "\n".join("".join(row) for row in board)

    def display(self) -> str:
        """Return the board as text."""
        return str(self)


def _compute_push_distances(width: int, height: int, walls: frozenset[Position],
                            targets: frozenset[Position]) -> dict[Position, tuple[float, ...]]:
    """Precompute push distances from floor cells to each target.

    Reverse edges correspond to a legal forward push: if a box could move from
    ``previous`` to ``current``, the support cell behind ``previous`` must also
    be floor. A multi-source BFS from all targets computes the nearest-target
    push distance once for this layout.
    """
    walkable = {(row, column) for row in range(height) for column in range(width)} - walls
    result: dict[Position, list[float]] = {cell: [] for cell in walkable}
    for target in sorted(targets):
        distances: dict[Position, int] = {target: 0}
        pending: deque[Position] = deque([target])
        while pending:
            row, column = pending.popleft()
            for _, (dr, dc) in ACTIONS:
                previous = (row - dr, column - dc)
                support = (row - 2 * dr, column - 2 * dc)
                if previous not in walkable or support not in walkable or previous in distances:
                    continue
                distances[previous] = distances[(row, column)] + 1
                pending.append(previous)
        for cell in walkable:
            result[cell].append(float(distances.get(cell, math.inf)))
    return {cell: tuple(distances) for cell, distances in result.items()}
