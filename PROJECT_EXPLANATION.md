# Sokoban Puzzle Solver — Detailed Project Explanation

This document walks through the entire project **step by step**, explaining every module, every data structure, and the full execution flow from start to finish.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [Step 1 — Entry Point (`main.py`)](#3-step-1--entry-point-mainpy)
4. [Step 2 — Level Files (`sokoban/levels/`)](#4-step-2--level-files-sokobanlevels)
5. [Step 3 — The Puzzle Model (`sokoban_puzzle.py`)](#5-step-3--the-puzzle-model-sokoban_puzzlepy)
6. [Step 4 — The Search Node (`node.py`)](#6-step-4--the-search-node-nodepy)
7. [Step 5 — BFS Search Algorithm (`search.py`)](#7-step-5--bfs-search-algorithm-searchpy)
8. [Step 6 — The GUI (`gui.py`)](#8-step-6--the-gui-guipy)
9. [Step 7 — Tests (`tests/test_sokoban.py`)](#9-step-7--tests-teststest_sokobanpy)
10. [Full Execution Flow — End to End](#10-full-execution-flow--end-to-end)
11. [Key Concepts Summary](#11-key-concepts-summary)

---

## 1. Project Overview

This project is a **Sokoban puzzle solver** built in Python. Sokoban is a classic puzzle game where a player (`R`) must push boxes (`B`) onto target positions (`S`) inside a warehouse bounded by walls (`O`). The player can only **push** boxes (not pull), and can only push **one box at a time** into an empty space.

The project:
- **Models** the Sokoban puzzle as a state-space search problem.
- **Solves** it using **Breadth-First Search (BFS)**, guaranteeing an optimal (shortest) solution.
- **Visualizes** the solving process through a **Pygame GUI** with playback controls.
- Includes 5 bundled levels and a full **test suite**.

---

## 2. Project Structure

```
Projet_1/
├── main.py                        # Root entry point (convenience wrapper)
├── README.md                      # Project documentation
├── Project 1 Part 1.pdf           # Original assignment PDF
└── sokoban/                       # Main Python package
    ├── __init__.py                 # Package init — exports SokobanPuzzle
    ├── sokoban_puzzle.py           # Puzzle state model (core logic)
    ├── node.py                     # Search tree node
    ├── search.py                   # BFS algorithm + SearchResult
    ├── main.py                     # CLI/GUI launcher
    ├── gui.py                      # Pygame graphical interface
    ├── levels/                     # Bundled puzzle levels
    │   ├── level1.txt
    │   ├── level2.txt
    │   ├── level3.txt
    │   ├── level4.txt
    │   └── level5.txt
    └── tests/
        └── test_sokoban.py         # Unit test suite
```

---

## 3. Step 1 — Entry Point (`main.py`)

### Root `main.py` (project root)

```python
from sokoban.main import main

if __name__ == "__main__":
    main()
```

This is a **convenience wrapper**. It simply imports and calls the real `main()` function from the `sokoban` package. You run the project with:

```sh
python main.py          # Launches the Pygame GUI
python main.py --cli    # Solves all 5 levels in the terminal
```

### `sokoban/main.py` (package entry point)

This module does the actual work:

1. **Parses command-line arguments** using `argparse`:
   - `--cli` → run in console mode (solve all 5 levels and print results).
   - `--level N` → choose starting level for the GUI (1–5).

2. **CLI mode** (`--cli`):
   - Loops through levels 1–5.
   - Loads each level from a `.txt` file using `SokobanPuzzle.from_file()`.
   - Runs BFS on each level.
   - Prints: cost, expanded nodes, generated nodes, max frontier size, search time, and the solution action sequence.

3. **GUI mode** (default):
   - Imports `SokobanGUI` (lazy import to avoid requiring pygame in CLI mode).
   - Calls `SokobanGUI().run(args.level)`.

---

## 4. Step 2 — Level Files (`sokoban/levels/`)

Each level is a plain text file using this encoding:

| Symbol | Meaning |
|--------|---------|
| `O`    | Wall |
| `R`    | Player |
| `B`    | Box |
| `S`    | Target (storage location) |
| ` ` (space) | Empty floor |
| `.`    | Player standing on a target |
| `*`    | Box placed on a target (goal state for that box) |

### Example — Level 1 (`level1.txt`):

```
OOOOOOOO
OS B   O
O OO R O
O      O
O      O
O      O
O      O
OOOOOOOO
```

Reading this grid:
- The board is 8×8, surrounded by walls (`O`).
- There is **1 target** (`S`) at position (row 1, col 1).
- There is **1 box** (`B`) at position (row 1, col 3).
- The **player** (`R`) is at position (row 2, col 5).
- The goal is to push the box onto the target.

---

## 5. Step 3 — The Puzzle Model (`sokoban_puzzle.py`)

This is the **heart of the project**. It defines how the Sokoban puzzle is represented and how states transition.

### 5.1 Constants and Types

```python
Position = tuple[int, int]                      # (row, col)
UP, DOWN, LEFT, RIGHT = "UP", "DOWN", "LEFT", "RIGHT"
ACTIONS = ((UP, (-1, 0)), (DOWN, (1, 0)), (LEFT, (0, -1)), (RIGHT, (0, 1)))
```

- `Position` is a `(row, col)` tuple.
- `ACTIONS` maps each direction name to a `(Δrow, Δcol)` delta vector.

### 5.2 `BoardLayout` — Static Board Data

```python
@dataclass(frozen=True)
class BoardLayout:
    rows: tuple[str, ...]            # Normalized static rows containing walls and floor
    width: int                        # Number of columns
    height: int                       # Number of rows
    walls: frozenset[Position]        # Set of wall positions
    targets: frozenset[Position]      # Set of target positions
```

This stores the **immutable parts** of the board — the walls and targets never change during gameplay. It is created **once** when a level is loaded and **shared** across all successor states. This is a key optimization: instead of duplicating the entire board for every state in the search, only the player and box positions change.

### 5.3 `SokobanPuzzle` — A Single Game State

A `SokobanPuzzle` represents **one snapshot** of the game. It contains:

| Attribute | Type | Description |
|-----------|------|-------------|
| `layout`  | `BoardLayout` | Shared reference to static board data |
| `player`  | `Position` | Current player `(row, col)` |
| `boxes`   | `frozenset[Position]` | Current set of box positions |

#### Construction

There are **two ways** to create a `SokobanPuzzle`:

1. **From text lines** (initial loading):
   ```python
   state = SokobanPuzzle.from_lines(["OOOOOO", "ORBS O", "OOOOOO"])
   state = SokobanPuzzle.from_file("sokoban/levels/level1.txt")
   ```
   This calls `_parse_lines()` which:
   - Strips line endings.
   - Validates all symbols are in `{R, O, ' ', S, B, ., *}`.
   - Pads ragged rows with walls so all rows have equal width.
   - Extracts walls, targets, player position, and box positions.
   - Validates exactly **1 player** and **equal box/target counts**.

2. **From internal constructor** (successor generation):
   ```python
   SokobanPuzzle(layout=self.layout, player=new_pos, boxes=new_boxes)
   ```
   Used by `successorFunction()` to create child states efficiently by reusing the shared `BoardLayout`.

#### `isGoal()` — Goal Test

```python
def isGoal(self) -> bool:
    return self.boxes == self.layout.targets
```

The puzzle is solved when every box position matches a target position. Since both are `frozenset`s, this is a simple set equality check.

#### `successorFunction()` — Generating Legal Moves

This is the **transition function** that generates all reachable states from the current one:

```python
def successorFunction(self) -> list[tuple[str, SokobanPuzzle]]:
```

For each of the 4 directions (UP, DOWN, LEFT, RIGHT):

1. Compute the **adjacent cell** (where the player would move to).
2. If the adjacent cell is a **wall** or out of bounds → skip (illegal move).
3. If the adjacent cell is **empty** → the player moves there (simple move).
4. If the adjacent cell contains a **box**:
   - Compute the cell **beyond** the box (where the box would be pushed to).
   - If beyond is a wall, out of bounds, or contains another box → skip (can't push).
   - Otherwise → the player moves to the box's position, and the box moves to beyond.

Each legal move produces a new `SokobanPuzzle` with:
- Updated `player` position.
- Updated `boxes` frozenset (only if a push occurred).
- Same shared `layout`.

#### `__eq__` and `__hash__` — State Identity

```python
def __eq__(self, other):
    return (self.layout == other.layout and
            self.player == other.player and
            self.boxes == other.boxes)

def __hash__(self):
    return hash((self.layout, self.player, self.boxes))
```

Two states are equal if they share the same board layout, player position, and box positions. This is **essential** for graph search — it allows the BFS to detect already-visited states using sets.

#### `__str__()` — Board Rendering

Reconstructs the board from static walls and floor, then overlays targets and the current player and box positions, using composite symbols (`.` for player-on-target, `*` for box-on-target). A previous version copied the original text rows and left stale player or box characters behind after moves; rebuilding from static cells fixes that ghost-symbol bug and makes successor states round-trip through the text parser.

---

## 6. Step 4 — The Search Node (`node.py`)

The `Node` class wraps a `SokobanPuzzle` state with search metadata to form a **search tree**.

```python
class Node:
    state: SokobanPuzzle     # The puzzle state at this node
    parent: Node | None      # Link to the parent node (None for root)
    action: str | None       # The action that led here ("UP", "DOWN", etc.)
    g: int                   # Path cost from root (number of moves)
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `getPath()` | Walk the parent chain back to root, return list of states |
| `getSolution()` | Walk the parent chain back to root, return list of actions |
| `expand()` | Call `state.successorFunction()`, wrap each child in a new `Node` |

#### `getPath()` — Trace the Solution States

```python
def getPath(self) -> list[SokobanPuzzle]:
    path = []
    node = self
    while node is not None:
        path.append(node.state)
        node = node.parent
    path.reverse()
    return path
```

Follows parent pointers from the goal node up to the root, collecting every state along the way. After reversing, you get the sequence: `[initial_state, state_after_move_1, ..., goal_state]`.

#### `getSolution()` — Trace the Solution Actions

Same idea, but collects the `action` strings instead of states. Returns something like `["RIGHT", "DOWN", "LEFT", "DOWN"]`.

#### `expand()` — Generate Children

```python
def expand(self) -> list[Node]:
    return [Node(state, self, action) for action, state in self.state.successorFunction()]
```

Calls the puzzle's successor function and wraps each `(action, new_state)` pair in a `Node`, linking back to `self` as the parent.

---

## 7. Step 5 — BFS Search Algorithm (`search.py`)

### 7.1 `SearchResult` — Output Container

```python
@dataclass
class SearchResult:
    solution: Node | None           # The goal node (None if unsolvable)
    actions: list[str]              # Sequence of actions to reach the goal
    path: list[SokobanPuzzle]       # Sequence of states from start to goal
    cost: int | None                # Number of moves in the solution
    expanded: int                   # How many nodes were popped from the frontier
    generated: int                  # Total child nodes created (including duplicates)
    max_frontier: int               # Peak size of the frontier queue
    elapsed_seconds: float          # Wall-clock search time
```

### 7.2 `bfs()` — Breadth-First Search (Graph Search)

```python
def bfs(initial_state: SokobanPuzzle) -> SearchResult:
```

This implements **graph-search BFS** — the standard textbook algorithm for finding the shortest path in an unweighted graph.

#### Step-by-step walkthrough:

```
1. START TIMER
2. Create root Node from initial_state
3. Initialize:
   - frontier       = FIFO queue containing [root]
   - frontier_states = set containing {initial_state}  (for O(1) membership test)
   - explored        = empty set
   - generated       = 1  (the root counts)
   - expanded        = 0
4. If initial_state is already the goal → return immediately

5. WHILE frontier is not empty:
   a. Pop the FRONT node from the queue (FIFO order)
   b. Remove its state from frontier_states
   c. Add its state to explored
   d. expanded += 1

   e. For each child in node.expand():
      - generated += 1
      - If child.state is in explored OR frontier_states → SKIP (already seen)
      - If child.state.isGoal() → FOUND! Save solution, clear frontier, break
      - Otherwise → add child to frontier and frontier_states

   f. Update max_frontier

6. STOP TIMER
7. Return SearchResult with solution (or None if frontier emptied)
```

#### Why BFS guarantees optimality:

BFS explores states **level by level** — all states reachable in 1 move before any state reachable in 2 moves, and so on. Since every move has **unit cost** (cost = 1), the first time BFS reaches the goal state, it has found the **shortest** path.

#### Why graph search (not tree search):

Without the `explored` set, BFS would revisit states it has already processed, leading to:
- **Infinite loops** (moving back and forth).
- **Exponential blowup** in memory and time.

The `explored` set ensures each state is expanded at most once. The `frontier_states` set prevents adding duplicate states to the queue.

#### Performance characteristics for bundled levels:

| Level | Solution cost | Expanded | Generated | Time |
|-------|--------------|----------|-----------|------|
| 1     | 4            | 11       | 35        | ~0.3ms |
| 2     | 14           | 171      | 548       | ~5ms |
| 3     | 19           | 3,713    | 10,606    | ~94ms |
| 4     | 20           | 3,197    | 10,172    | ~100ms |
| 5     | 20           | 21,090   | 61,394    | ~640ms |

---

## 8. Step 6 — The GUI (`gui.py`)

The GUI is built with **Pygame** and provides an interactive way to load levels, solve them, and watch the solution play back.

### 8.1 Architecture

```
┌─────────────────────────────────────────────┐
│                SokobanGUI                    │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Level    │  │ Solver   │  │ Playback  │  │
│  │ Manager  │  │ Thread   │  │ Engine    │  │
│  └──────────┘  └──────────┘  └───────────┘  │
│        │              │             │        │
│        ▼              ▼             ▼        │
│  ┌─────────────────────────────────────────┐ │
│  │           Pygame Render Loop            │ │
│  │   - Controls bar (level/playback btns)  │ │
│  │   - Board drawing (tiles, player, box)  │ │
│  │   - Info panel (stats, step counter)    │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 8.2 Key Components

#### Level Management
- All 5 levels are pre-loaded at startup into `self.levels`.
- `_change_level(index)` switches levels and resets all playback state.

#### Background Solving
- When the user clicks "Solve" or presses `S`, `_start_solve()` launches BFS in a **worker thread** (`threading.Thread`).
- The solver puts its result in a `queue.Queue`.
- The main loop checks `self.result_queue` every frame — when a result arrives, it updates the display and unlocks playback controls.
- **Why a thread?** BFS can take hundreds of milliseconds. Running it on the main thread would freeze the window.

#### Playback Engine
- After solving, `result.path` contains every state from start to goal.
- `self.step` is an index into this path.
- **Play/Pause** (`Space`): auto-advances `self.step` at `self.delay_ms` intervals.
- **Step Forward** (`→` or `N`): advance one step.
- **Step Back** (`←` or `B`): go back one step.
- **Reset** (`R`): go back to step 0.
- **Speed** (`+`/`-`): adjust `delay_ms` (60ms to 1500ms range).

### 8.3 Board Rendering (`_draw_board`)

The board is drawn using Pygame primitives (no sprite images):

| Element | Visual |
|---------|--------|
| Wall (`O`) | Gray rectangles with brick-line pattern |
| Floor (` `) | Light tan rectangles |
| Target (`S`) | Tan floor + small brown circle |
| Box (`B`) | Brown rounded rectangle with diagonal cross |
| Box on target (`*`) | Golden/yellow rounded rectangle (signals correct placement) |
| Player (`R`) | Blue body circle + skin-colored head circle |

The board automatically **scales** to fit the window, computing a tile size from the available space.

### 8.4 Info Panel (`_draw_info`)

Displays on the right side:
- Algorithm name, level name, status message.
- Solution cost, action count, expanded/generated nodes, max frontier, search time.
- Current step index and action at that step.
- If multiple solvers are registered, a comparison table.

### 8.5 Controls

| Control | Mouse | Keyboard |
|---------|-------|----------|
| Choose level | Click level button | `1`–`5` |
| Solve | Click "Solve" | `S` |
| Play/Pause | Click "Play" | `Space` |
| Step forward | Click "Step" | `→` or `N` |
| Step back | Click "Back" | `←` or `B` |
| Reset | Click "Reset" | `R` |
| Speed up | — | `+` |
| Slow down | — | `-` |

---

## 9. Step 7 — Tests (`tests/test_sokoban.py`)

The test suite validates correctness using `unittest`. It covers:

| Test | What It Verifies |
|------|------------------|
| `test_round_trip_goal_and_state_hash` | A state can be serialized to text and parsed back to an equal state; goal detection works; hash consistency. |
| `test_moves_pushes_and_blocking` | A push moves the box correctly; blocked directions are excluded from successors; two adjacent boxes block a push. |
| `test_plain_move_no_pull_and_push_blocked_by_wall` | Moving into empty space works; walls block movement; pushing a box into a wall is disallowed. |
| `test_player_and_box_on_target_transitions` | Composite symbols (`.` and `*`) appear correctly and transitions preserve them. |
| `test_node_path_solution_and_minimal_bfs` | Node path/solution tracing works; BFS on a trivial 1-move puzzle returns cost 1. |
| `test_validation` | A level with no player raises `ValueError`. |
| `test_bundled_levels_solve_and_replay` | All 5 bundled levels are solvable; solution cost matches action count; replaying the actions reaches the goal. |

Run with:
```sh
python -m unittest discover -s sokoban/tests -v
```

---

## 10. Full Execution Flow — End to End

Here is the complete execution trace when you run `python main.py` (GUI mode) and solve Level 1:

```
                    ┌──────────────────────┐
                    │   python main.py     │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  sokoban.main.main() │
                    │  Parse args (no --cli)│
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  SokobanGUI.__init__ │
                    │  Load levels 1-5     │
                    │  from .txt files     │
                    └──────────┬───────────┘
                               │
                   ┌───────────▼───────────┐
                   │    SokobanGUI.run()   │
                   │  pygame.init()        │
                   │  Create window 1180×760│
                   │  Enter main loop      │
                   └───────────┬───────────┘
                               │
                ┌──────────────▼──────────────┐
                │      MAIN LOOP (60 FPS)     │
                │                              │
                │  1. Process pygame events    │
                │  2. Check result queue       │
                │  3. Advance playback if      │
                │     playing                  │
                │  4. Draw: controls, board,   │
                │     info panel               │
                │  5. pygame.display.flip()    │
                └──────────────┬──────────────┘
                               │
            User presses 'S'   │
                               │
                ┌──────────────▼──────────────┐
                │     _start_solve()           │
                │  Launch worker thread        │
                │  thread → bfs(level_state)   │
                └──────────────┬──────────────┘
                               │
                     ┌─────────▼─────────┐
                     │  WORKER THREAD     │
                     │                    │
                     │  bfs(initial):     │
                     │  1. root = Node()  │
                     │  2. frontier = [r] │
                     │  3. explored = {}  │
                     │  4. LOOP:          │
                     │     pop → expand   │
                     │     → check goal   │
                     │  5. FOUND!         │
                     │  6. queue.put()    │
                     └─────────┬─────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Main loop picks up result  │
                │  result_queue.get()          │
                │  self.results["BFS"] = res   │
                │  message = "Solution found." │
                └──────────────┬──────────────┘
                               │
            User presses Space │
                               │
                ┌──────────────▼──────────────┐
                │  PLAYBACK                    │
                │  self.playing = True         │
                │  Every delay_ms:             │
                │    self.step += 1            │
                │    Draws result.path[step]   │
                │  Until step == len(path)-1   │
                │    → auto-pause              │
                └─────────────────────────────┘
```

### Detailed BFS trace for Level 1 (4-move solution):

```
Initial state:              Step 0 (root node)
  OOOOOOOO
  OS B   O                  Player at (2,5), Box at (1,3), Target at (1,1)
  O OO R O
  O      O
  ...

BFS explores 11 nodes, generates 35 children.

Solution found: UP → LEFT → LEFT → LEFT
  Step 1 (UP):    Player moves (2,5) → (1,5)
  Step 2 (LEFT):  Player moves (1,5) → (1,4)
  Step 3 (LEFT):  Player pushes box: Player (1,4)→(1,3), Box (1,3)→(1,2)
  Step 4 (LEFT):  Player pushes box: Player (1,3)→(1,2), Box (1,2)→(1,1) ← ON TARGET!

Final state:
  OOOOOOOO
  O*R    O                  Box on target (*) at (1,1), Player at (1,2)
  O OO   O
  ...
```

---

## 11. Key Concepts Summary

### State-Space Search Formulation

| Component | Sokoban Implementation |
|-----------|----------------------|
| **State** | `(player_position, box_positions)` on a fixed board |
| **Initial State** | Loaded from level `.txt` file |
| **Actions** | `{UP, DOWN, LEFT, RIGHT}` |
| **Transition Model** | `successorFunction()` — moves player, pushes box if adjacent |
| **Goal Test** | `isGoal()` — all boxes on all targets |
| **Path Cost** | Number of moves (each move costs 1) |

### Design Patterns Used

| Pattern | Where |
|---------|-------|
| **Flyweight** | `BoardLayout` is shared across all states from the same level |
| **Immutable State** | `frozenset` for boxes enables hashing and safe set membership |
| **Producer-Consumer** | Worker thread produces `SearchResult` → main thread consumes via `Queue` |
| **Strategy** | `self.solvers` dict allows registering multiple search algorithms |

### How to Extend — Adding a New Search Algorithm

1. Write a function with signature `(SokobanPuzzle) -> SearchResult` in `search.py`.
2. Register it in `SokobanGUI.solvers`:
   ```python
   self.solvers["A*"] = a_star
   ```
3. The GUI automatically displays comparison stats for all registered solvers.

---

> **Note**: This project uses only the Python standard library + `pygame`. No external AI or search libraries are needed. The BFS implementation is from scratch, following the textbook graph-search algorithm.
