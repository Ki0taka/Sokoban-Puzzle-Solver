"""Immutable-state Sokoban model with shared static board layouts."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
    """Static maze data shared by all states derived from one level."""

    rows: tuple[str, ...]
    width: int
    height: int
    walls: frozenset[Position]
    targets: frozenset[Position]


class SokobanPuzzle:
    """A Sokoban state; only player and box locations change between states.

    Construct from encoded board lines or use ``from_lines``/``from_file``.
    ``lines`` and ``layout`` are mutually exclusive; internal construction
    with a layout is intended for generating successor states.
    """

    __slots__ = ("layout", "player", "boxes")

    def __setattr__(self, name: str, value: object) -> None:
        """Allow each state field to be initialized once, then keep it immutable."""
        if name not in self.__slots__ or hasattr(self, name):
            raise AttributeError(f"{type(self).__name__} attribute {name!r} is immutable")
        object.__setattr__(self, name, value)

    def __init__(self, lines: Iterable[str] | None = None, *, layout: BoardLayout | None = None,
                 player: Position | None = None, boxes: Iterable[Position] = ()) -> None:
        """Create a validated board state from text or internal static data."""
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
        """Parse and validate encoded rows, padding ragged rows with walls."""
        source = [line.rstrip("\r\n") for line in lines]
        if not source:
            raise ValueError("A level must contain at least one row")
        if any(symbol not in VALID_SYMBOLS for row in source for symbol in row):
            raise ValueError("Level contains an unsupported cell symbol")
        width = max(map(len, source))
        # Ragged text rows are padded as walls so missing cells cannot be entered.
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
        static_rows = tuple(
            "".join(WALL if symbol == WALL else EMPTY for symbol in row)
            for row in rows
        )
        return BoardLayout(static_rows, width, len(rows), frozenset(walls), frozenset(targets)), players[0], frozenset(boxes)

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> "SokobanPuzzle":
        """Create a puzzle from encoded rows; raises ValueError for invalid levels."""
        return cls(lines)

    @classmethod
    def from_file(cls, path: str | Path) -> "SokobanPuzzle":
        """Load a text level from ``path`` using UTF-8 encoding."""
        return cls.from_lines(Path(path).read_text(encoding="utf-8").splitlines())

    def _validate_dynamic_state(self) -> None:
        """Reject internal states that place objects in blocked or overlapping cells."""
        walkable = {(r, c) for r in range(self.layout.height) for c in range(self.layout.width)} - self.layout.walls
        if self.player not in walkable or self.player in self.boxes:
            raise ValueError("Player must occupy an unblocked cell distinct from all boxes")
        if not self.boxes <= walkable or self.player in self.boxes:
            raise ValueError("Boxes must occupy unblocked cells distinct from the player")
        if len(self.boxes) != len(self.layout.targets):
            raise ValueError("Internal state must preserve the level's number of boxes")

    def isGoal(self) -> bool:
        """Return whether every box occupies a target."""
        return self.boxes == self.layout.targets

    def successorFunction(self) -> list[tuple[str, "SokobanPuzzle"]]:
        """Return all legal moves and pushes as independent successor states."""
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
            successors.append((action, SokobanPuzzle(layout=self.layout, player=adjacent, boxes=new_boxes)))
        return successors

    def _is_walkable(self, position: Position) -> bool:
        """Return whether a position is inside the board and not a wall."""
        row, column = position
        return (0 <= row < self.layout.height and 0 <= column < self.layout.width
                and position not in self.layout.walls)

    def __eq__(self, other: object) -> bool:
        """Compare dynamic state values on the same static board."""
        return isinstance(other, SokobanPuzzle) and self.layout == other.layout and self.player == other.player and self.boxes == other.boxes

    def __hash__(self) -> int:
        """Hash player and box locations together with the board identity."""
        return hash((self.layout, self.player, self.boxes))

    def __str__(self) -> str:
        """Render the board with the required Sokoban symbols."""
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
        """Return the printable board representation."""
        return str(self)
