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
8. [Step 6 — A\* Search Algorithm (`search.py`)](#8-step-6--a-search-algorithm-searchpy)
9. [Step 7 — Heuristic Functions (`heuristics.py`)](#9-step-7--heuristic-functions-heuristicspy)
10. [Step 8 — How A\* Behaves with Each Heuristic](#10-step-8--how-a-behaves-with-each-heuristic)
11. [Step 9 — The GUI (`gui.py`)](#11-step-9--the-gui-guipy)
12. [Step 10 — Tests](#12-step-10--tests)
13. [Full Execution Flow — End to End](#13-full-execution-flow--end-to-end)
14. [Key Concepts Summary](#14-key-concepts-summary)

---

## 1. Project Overview

This project is a **Sokoban puzzle solver** built in Python. Sokoban is a classic puzzle game where a player (`R`) must push boxes (`B`) onto target positions (`S`) inside a warehouse bounded by walls (`O`). The player can only **push** boxes (not pull), and can only push **one box at a time** into an empty space.

The project:
- **Models** the Sokoban puzzle as a state-space search problem.
- **Solves** it using **Breadth-First Search (BFS)** and **A\* Search** with three heuristics (h1, h2, h3).
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
    ├── search.py                   # BFS + A* algorithms + SearchResult
    ├── heuristics.py               # h1, h2, h3 heuristic functions
    ├── benchmark.py                # Benchmark runner (results.md generator)
    ├── main.py                     # CLI/GUI launcher
    ├── gui.py                      # Pygame graphical interface
    ├── levels/                     # Bundled puzzle levels
    │   ├── level1.txt
    │   ├── level2.txt
    │   ├── level3.txt
    │   ├── level4.txt
    │   └── level5.txt
    └── tests/
        ├── test_sokoban.py         # Core model + BFS tests
        ├── test_astar.py           # A* correctness and optimality tests
        ├── test_heuristics.py      # Heuristic admissibility/consistency tests
        └── test_fixes.py           # Integration and regression tests
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
   - Runs **BFS**, **A\*(h1)**, **A\*(h2)**, and **A\*(h3)** on each level.
   - Prints: cost, expanded nodes, generated nodes, max frontier size, search time, and the solution action sequence for each algorithm.

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

| Level | Solution cost | Expanded | Generated | Max Frontier | Time |
|-------|--------------|----------|-----------|-------------|------|
| 1     | 4            | 11       | 32        | 5           | ~0.2ms |
| 2     | 29           | 1,079    | 3,246     | 89          | ~13ms |
| 3     | 20           | 1,854    | 5,163     | 244         | ~19ms |
| 4     | 19           | 3,446    | 9,969     | 955         | ~38ms |
| 5     | 30           | 315,127  | 1,029,632 | 41,050      | ~3.2s |

---

## 8. Step 6 — A\* Search Algorithm (`search.py`)

A\* is an **informed** graph-search algorithm that uses a heuristic function $h(n)$ to estimate the remaining cost from any state $n$ to the goal. It expands nodes in order of **$f(n) = g(n) + h(n)$**, where $g(n)$ is the actual path cost from the start.

### 8.1 How A\* Works (Graph Search)

The implementation follows the lecture's **Open/Closed** framework:

```
1. START TIMER
2. Create root Node from initial_state, compute f(root) = 0 + h(initial_state)
3. Initialize:
   - Open (priority queue)  = min-heap containing [root], ordered by (f, h, insertion_order)
   - open_nodes             = dict {initial_state → root}   (for O(1) lookup)
   - closed_nodes           = empty dict                     (expanded states)
   - generated = 1, expanded = 0, reopened = 0

4. If initial_state is already the goal → return immediately
5. If f(root) = ∞ (dead state detected by heuristic) → return no solution

6. WHILE Open is not empty:
   a. Pop the node with LOWEST f from the heap
   b. If this node was superseded by a better one (lazy deletion check) → skip
   c. Remove from open_nodes, add to closed_nodes
   d. **Goal test**: If current.state.isGoal() → FOUND! Return solution
   e. expanded += 1

   f. For each successor of current:
      - Create child Node, compute f(child) = g(child) + h(child.state)
      - If f(child) = ∞ → skip (proven dead state)
      - If child.state is in Open with a LOWER or equal f → skip
      - If child.state is in Open with a HIGHER f → REPLACE (lazy: update dict, push new heap entry)
      - If child.state is in Closed with a LOWER or equal f → skip
      - If child.state is in Closed with a HIGHER f → REOPEN (remove from Closed, add to Open, reopened += 1)
      - Otherwise → add to Open

7. STOP TIMER
8. Return SearchResult (or None if Open emptied)
```

### 8.2 Key Implementation Details

#### Priority Queue with Lazy Deletion

The Open list is a **min-heap** of `(f, h, insertion_order, node)` tuples:
- **`f`**: primary sort key — lower f is expanded first.
- **`h`**: tiebreaker — among nodes with equal f, prefer lower h (closer to goal).
- **`insertion_order`**: second tiebreaker — FIFO order among equal f and h.

When a better path to the same state is found, instead of removing the old entry from the heap (which is $O(n)$), the code **pushes a new entry** and updates `open_nodes[state]` to the new node. When the stale entry is later popped, the check `open_nodes.get(state) is not current` catches it and skips it. This is called **lazy deletion**.

#### Re-opening Closed States

With **consistent** heuristics (h1, h3), a state is never expanded more than once. But with **inconsistent** heuristics (h2), a state already in Closed may be reached via a cheaper path. The algorithm detects this (`child.f < closed_node.f`), removes the state from Closed, and adds it back to Open. This counter is tracked by `reopened`.

#### Goal Test at Expansion (not Generation)

Unlike BFS (which tests the goal when a child is generated), A\* tests the goal **when a node is dequeued** from Open. This is important because a child with `isGoal() == True` might not have the cheapest $f$ — a different path might reach the goal with lower cost.

### 8.3 Why A\* Guarantees Optimality (with Admissible Heuristics)

A heuristic $h(n)$ is **admissible** if $h(n) \leq h^*(n)$ for all states, where $h^*(n)$ is the true optimal remaining cost. If $h$ is admissible, then $f(n) = g(n) + h(n) \leq g(n) + h^*(n) = g^*(n)$. This means A\* never overestimates the total cost, so the first goal node dequeued must be optimal.

A heuristic is **consistent** (monotone) if $h(n) \leq c(n, n') + h(n')$ for every edge. Consistency implies admissibility and also guarantees that once a state is expanded (moved to Closed), its $g$-value is already optimal — so no re-opening is ever needed.

---

## 9. Step 7 — Heuristic Functions (`heuristics.py`)

Three heuristic functions are provided, each making a different trade-off between accuracy and computational cost.

### 9.1 Heuristic h1 — Misplaced Boxes Count

```python
def h1(state: SokobanPuzzle) -> int:
    return sum(1 for box in state.boxes if box not in state.layout.targets)
```

**Idea**: Count how many boxes are **not** on a target. Each such box needs **at least one push**, and each push costs one move.

**Example** — Level 1 initial state (1 box not on target):
```
OOOOOO
OS B O      Box at (1,3), Target at (1,1)
O OR O      → h1 = 1 (the box is not on the target)
O    O
```

**Properties**:
- **Admissible**: ✅ Every misplaced box needs ≥ 1 push → h1 ≤ true cost.
- **Consistent**: ✅ A single move changes at most one box's placement, so $h_1(n) - h_1(n') \leq 1 = c(n, n')$.
- **Fast**: $O(|boxes|)$ per call — just a set membership check per box.
- **Weakness**: Very coarse. It says "3 boxes are off target" but doesn't know if they need 3 pushes or 30 pushes. This makes A\*(h1) expand almost as many nodes as BFS.

### 9.2 Heuristic h2 — Assignment Formula (Non-Admissible)

```python
def h2(state: SokobanPuzzle) -> int:
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
```

**Idea**: This is the formula from the assignment: $h_2 = 2 \times |\text{unplaced boxes}| + \sum_{\text{unplaced box}} \min_{\text{target}} \text{Manhattan}(box, target)$.

The **Manhattan distance** between a box and a target is $|r_{box} - r_{target}| + |c_{box} - c_{target}|$ — the minimum number of grid steps ignoring walls.

**Example** — Level 1 initial state:
```
Box at (1,3), Target at (1,1)
unplaced = 1
Manhattan((1,3), (1,1)) = |1-1| + |3-1| = 2
h2 = 2×1 + 2 = 4
```

**Properties**:
- **Admissible**: ❌ The **$2 \times$ unplaced** term can overestimate. Consider a single box 1 push from the target: the true cost might be 1, but h2 = 2×1 + 1 = 3.
- **Consistent**: ❌ Since it's not admissible, it cannot be consistent.
- **Effect**: Because h2 can overestimate, A\*(h2) may not find optimal solutions. However, it prunes more aggressively — it expands fewer nodes and runs faster than h1, often finding the same optimal path, but without any guarantee.
- **Re-opening**: The A\* implementation handles h2's inconsistency by re-opening Closed states when a cheaper path is found.

### 9.3 Heuristic h3 — Wall-Aware Push Assignment + Approach

h3 is the most sophisticated heuristic. It consists of **three components**:

#### Component 1: Dead-Square Detection

```python
for box in state.boxes:
    if box not in layout.targets and box in layout.dead_squares:
        return math.inf
```

A **dead square** is a floor cell from which no sequence of pushes can ever move a box to any target. These are precomputed once per level by running a **reverse BFS** from each target: starting from the target, simulate pulling a box backwards in every direction, and mark all reachable cells. Any floor cell NOT reached by this reverse process is a dead square.

If any box sits on a dead square (and it's not already on a target), the state is **unsolvable** → return $\infty$. A\* will never expand this node.

#### Component 2: Minimum-Cost Push Assignment (Bitmask DP)

```python
boxes = tuple(sorted(state.boxes))
cost_rows = tuple(layout.push_distances[box] for box in boxes)
push_lower_bound = _min_assignment(cost_rows)
```

This computes the **minimum total push cost** to assign each box to a distinct target, using wall-aware push distances instead of simple Manhattan distances.

**Push distances** are precomputed per level: for each floor cell, a reverse BFS simulates pulling a box backwards (the pull-source cell must be walkable and not a wall). The resulting `push_distances[cell]` is a tuple of distances from that cell to each target. If a cell can't reach a target via pushes, the distance is $\infty$.

The assignment problem (each box goes to a different target, minimizing total push cost) is solved by **bitmask dynamic programming**:

```
For n boxes and n targets:
- prev = {0: 0.0}   (bitmask 0 = no targets assigned yet, cost = 0)
- For each box i (0 to n-1):
    - For each previously computed (mask, cost):
        - For each target t not in mask:
            - new_mask = mask | (1 << t)
            - candidate = cost + push_distance(box_i, target_t)
            - Keep the minimum for each new_mask
- Result = min over all final masks with n bits set
```

This runs in $O(n^2 \cdot 2^n)$ time, which is fast for Sokoban's typical 2–5 boxes.

**Example** — Level 3 (2 boxes, 2 targets):
```
Box₁ at (2,3), Box₂ at (4,6)
Target₁ at (5,6), Target₂ at (6,6)

push_distances[Box₁][Target₁] = 5   push_distances[Box₁][Target₂] = 6
push_distances[Box₂][Target₁] = 1   push_distances[Box₂][Target₂] = 2

Assignment 1: Box₁→T₁, Box₂→T₂ = 5 + 2 = 7
Assignment 2: Box₁→T₂, Box₂→T₁ = 6 + 1 = 7
→ push_lower_bound = 7
```

The result is **cached** at module level with `@lru_cache` — identical box configurations across different search nodes reuse the same result.

#### Component 3: Player Approach Cost

```python
approach = max(0, min(
    abs(state.player[0] - box[0]) + abs(state.player[1] - box[1])
    for box in boxes
) - 1)
```

The player must **walk** to an adjacent cell of a box before the first push. The minimum walk distance is the Manhattan distance to the nearest box minus 1 (because the player pushes from an adjacent cell, not from the box cell itself).

This cost is **disjoint** from push costs — walking happens before the first push — so adding it to the push lower bound remains admissible.

**Final formula**: $h_3(n) = \text{push\_lower\_bound} + \text{approach}$

**Properties**:
- **Admissible**: ✅ Push distances are exact (walls respected), and the optimal assignment lower-bounds the actual pushes. Approach is also a lower bound.
- **Consistent**: ✅ Any single move changes the approach by at most 1 and doesn't reduce the optimal assignment by more than the 1-step cost.
- **Strong pruning**: Dead-square detection ($\infty$) immediately eliminates provably unsolvable states.
- **Cost**: More expensive per call ($O(n^2 \cdot 2^n)$), but the aggressive pruning means far fewer nodes are expanded, leading to much faster total search time.

---

## 10. Step 8 — How A\* Behaves with Each Heuristic

### 10.1 A\*(h1) — Guided by Misplaced Box Count

With $f(n) = g(n) + h_1(n)$, A\* prefers states where fewer boxes are off-target. But since h1 only tells "how many boxes are wrong", not "how far they are from the target", the guidance is weak. A\*(h1) explores almost the same number of nodes as BFS.

**Behavior**: Acts like a slightly informed BFS. It always finds the **optimal** solution (h1 is admissible and consistent). No re-opening occurs.

### 10.2 A\*(h2) — Aggressive but Non-Optimal

With $f(n) = g(n) + h_2(n)$, A\* aggressively prunes states because h2 returns larger values. The $2 \times \text{unplaced}$ multiplier inflates the estimate, making non-goal states look more expensive.

**Behavior**: Expands significantly fewer nodes than BFS or A\*(h1). However, because h2 is **not admissible**, A\*(h2) may:
- Find a **suboptimal** solution (expanded a non-cheapest goal first).
- **Re-open** states from Closed when a cheaper path is discovered later.

On the bundled levels, A\*(h2) happens to find the same optimal cost on most levels, but this is **not guaranteed** — it's a coincidence of the level geometry.

### 10.3 A\*(h3) — Best of Both Worlds

With $f(n) = g(n) + h_3(n)$, A\* gets a tight, admissible estimate that accounts for wall geometry, dead squares, and the optimal box-to-target assignment.

**Behavior**: Expands far fewer nodes than BFS/A\*(h1), while still guaranteeing **optimality** (h3 is admissible and consistent). Dead-square pruning means entire branches of the search tree are skipped instantly.

### 10.4 Performance Comparison

| Level | Algorithm | Solution Cost | Expanded | Generated | Max Frontier | Time |
|-------|-----------|:------------:|:--------:|:---------:|:----------:|:----:|
| 1     | BFS       | **4**  | 11       | 32       | 5      | ~0.2ms |
| 1     | A\*(h1)   | **4**  | 11       | 32       | 5      | ~0.2ms |
| 1     | A\*(h2)   | **4**  | 8        | 24       | 6      | ~0.2ms |
| 1     | A\*(h3)   | **4**  | 5        | 15       | 6      | ~0.3ms |
| 3     | BFS       | **20** | 1,854    | 5,163    | 244    | ~19ms |
| 3     | A\*(h1)   | **20** | 1,701    | 4,750    | 218    | ~25ms |
| 3     | A\*(h2)   | **20** | 650      | 1,835    | 159    | ~13ms |
| 3     | A\*(h3)   | **20** | 327      | 925      | 123    | ~27ms |
| 5     | BFS       | **30** | 315,127  | 1,029,632| 41,050 | ~3.2s |
| 5     | A\*(h1)   | **30** | 213,074  | 699,183  | 40,459 | ~3.3s |
| 5     | A\*(h2)   | **30** | 24,394   | 81,189   | 9,947  | ~0.5s |
| 5     | A\*(h3)   | **30** | 9,537    | 32,865   | 6,499  | ~0.5s |

**Key observations**:
- **h1** provides minimal improvement over BFS because it barely distinguishes states.
- **h2** dramatically reduces expansions (~13× fewer on Level 5) by being more aggressive, at the risk of non-optimality.
- **h3** achieves the **best reduction** (~33× fewer on Level 5) while preserving optimality. The wall-aware push distances and dead-square pruning make a decisive difference.
- On small levels (1–2), all algorithms perform similarly because the search space is tiny.
- A\*(h3) per-node cost is higher (bitmask DP), but the drastic reduction in expanded nodes more than compensates.

### 10.5 Visualization of Search Reduction

```
Level 5 — Expanded nodes comparison:

  BFS       ████████████████████████████████████████████████████  315,127
  A*(h1)    ██████████████████████████████████████                213,074
  A*(h2)    ████                                                   24,394
  A*(h3)    ██                                                      9,537
            └──────────────────────────────────────────────────┘
```

---

## 11. Step 9 — The GUI (`gui.py`)

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

## 12. Step 10 — Tests

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

Additionally, `test_astar.py` verifies A\* optimality (h1 and h3 match BFS cost), re-opening behavior (h2 on Level 3), and `Node.setF` correctness. `test_heuristics.py` exhaustively checks admissibility and consistency on small state spaces.

---

## 13. Full Execution Flow — End to End

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

## 14. Key Concepts Summary

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
| **Strategy** | `SOLVERS` dict registers BFS, A\*(h1), A\*(h2), A\*(h3) — GUI iterates all of them |
| **Precomputation** | Push distances and dead squares computed once per level, reused by h3 across all states |

### How to Extend — Adding a New Search Algorithm

1. Write a function with signature `(SokobanPuzzle) -> SearchResult` in `search.py`.
2. Register it in `SokobanGUI.solvers`:
   ```python
   self.solvers["A*"] = a_star
   ```
3. The GUI automatically displays comparison stats for all registered solvers.

---

> **Note**: This project uses only the Python standard library + `pygame`. No external AI or search libraries are needed. Both BFS and A\* are implemented from scratch, following the textbook graph-search algorithms. The heuristics (h1, h2, h3) are hand-crafted for the Sokoban domain.
