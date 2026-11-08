# Sokoban Puzzle Solver — Detailed Project Explanation

This document explains the whole project: how a level is modeled, how the search algorithms (BFS and A\*) work, how the heuristics are built, and — in the most detail — how **deadlock detection** is computed, cached, plugged into the searches, visualized in the GUI, and what it can and cannot detect.

If you only have five minutes, read [Section 1](#1-project-overview), [Section 11 (deadlocks)](#11-deadlock-detection-deadlockpy), and the [Key Concepts Summary](#17-key-concepts-summary).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Structure](#2-project-structure)
3. [Entry Point (`main.py`)](#3-entry-point-mainpy)
4. [Level Files (`sokoban/levels/`)](#4-level-files-sokobanlevels)
5. [The Puzzle Model (`sokoban_puzzle.py`)](#5-the-puzzle-model-sokoban_puzzlepy)
6. [The Search Node (`node.py`)](#6-the-search-node-nodepy)
7. [BFS (`search.py`)](#7-bfs-searchpy)
8. [A\* (`search.py`)](#8-a-searchpy)
9. [Heuristics (`heuristics.py`)](#9-heuristics-heuristicspy)
10. [Push Distances and Dead Squares (computed at parse time)](#10-push-distances-and-dead-squares-computed-at-parse-time)
11. [Deadlock Detection (`deadlock.py`)](#11-deadlock-detection-deadlockpy)
12. [How Deadlock Pruning Plugs Into the Searches](#12-how-deadlock-pruning-plugs-into-the-searches)
13. [Performance Comparison](#13-performance-comparison)
14. [The GUI (`gui.py`)](#14-the-gui-guipy)
15. [Test Suite](#15-test-suite)
16. [Full Execution Flow](#16-full-execution-flow)
17. [Key Concepts Summary](#17-key-concepts-summary)

---

## 1. Project Overview

This is a **Sokoban solver** written in Python for Master 1 Visual Computing (USTHB). In Sokoban a warehouse keeper (`R`) pushes boxes (`B`) onto storage targets (`S`) inside a walled maze (`O`). Two rules make the game hard:

- The keeper can only **push**, never pull.
- The keeper can push only **one box at a time**, into a free cell.

Because boxes can never be pulled back, a single careless push can make a puzzle **unsolvable forever**. Detecting and avoiding such positions is what the deadlock part of the project is about.

The project covers three assignment parts:

| Part | Topic | What was built |
|---|---|---|
| 1 | Modeling and uninformed search | Immutable state model, level parsing and enclosure validation, BFS |
| 2 | Informed search | A\* with Open/Closed sets and re-opening, heuristics `h1`, `h2`, `h3` |
| 3 | Deadlock detection | Corner and line deadlocks, pruning inside BFS and A\*, GUI overlay, benchmark over 7 levels |

### Terminology used throughout

| Term | Meaning |
|---|---|
| **State** | The player position plus the set of box positions. Walls and targets are fixed and shared. |
| **Move / action** | One of `UP`, `DOWN`, `LEFT`, `RIGHT`. Each costs 1. A move that walks into a box is a **push**. |
| **Expanded** | A state taken off the frontier and whose successors were generated. |
| **Generated** | Every successor produced, including duplicates and pruned ones (plus the root). |
| **Deadlock** | A state from which no solution exists (`h*(s) = ∞`). |
| **Dead cell / dead square** | A cell where a box can never reach any target once it stands there. |
| **Pruned** | A generated successor discarded because a box was pushed onto a deadlock cell. |
| **Admissible heuristic** | Never overestimates the true remaining cost (`h ≤ h*`). |
| **Consistent heuristic** | `h(n) ≤ 1 + h(n')` for every move `n → n'`. |

---

## 2. Project Structure

```text
sokoban/
├── main.py                        # Root entry point (convenience launcher)
├── README.md                      # Project documentation and benchmark report
├── results_part3.md               # Part 3 benchmark data and solution sequences
├── LEVEL_RECONSTRUCTIONS.md       # ASCII reconstruction notes for all figures
├── PROJECT_EXPLANATION.md         # This file
└── sokoban/                       # Main Python package
    ├── __init__.py                # Exports SokobanPuzzle
    ├── sokoban_puzzle.py          # State model, parsing, enclosure, push distances, dead squares
    ├── node.py                    # Search tree node (g, f, path/solution reconstruction)
    ├── deadlock.py                # Corner/line deadlock detection and per-layout cache
    ├── heuristics.py              # h1, h2, h3 and h3_exact (none of h1-h3 use deadlock info)
    ├── search.py                  # BFS, A*, SearchResult, SOLVERS registry
    ├── benchmark.py               # Automated 7-level benchmark runner
    ├── main.py                    # CLI / GUI / benchmark dispatcher
    ├── gui.py                     # Pygame interface with deadlock toggle and overlay
    ├── assets/tileset.png         # Sprite sheet used by the GUI (optional; falls back to drawn shapes)
    ├── levels/                    # level1.txt ... level7.txt
    └── tests/                     # 56 unit tests
        ├── test_sokoban.py        # Model and transition validation
        ├── test_astar.py          # A* correctness, path replay, optimality
        ├── test_heuristics.py     # Heuristic admissibility and consistency
        ├── test_deadlock.py       # Corner/line detection, soundness, GUI smoke
        └── test_fixes.py          # Regression and solver-registry checks
```

**Dependency direction** (each arrow means "imports"):

```text
gui.py ───────► search.py ───► deadlock.py ───► sokoban_puzzle.py
   │               │  │
   │               │  └──────► heuristics.py ──► sokoban_puzzle.py
   │               └─────────► node.py ────────► sokoban_puzzle.py
   └─────────► deadlock.py (overlay only), heuristics.py (button names)
```

`sokoban_puzzle.py` imports nothing from the rest of the package, so the model can be tested on its own.

---

## 3. Entry Point (`main.py`)

The root `main.py` simply calls `sokoban.main.main()`.

`sokoban/main.py` parses options with `argparse`:

| Command | Effect |
|---|---|
| `python main.py` | Opens the Pygame GUI at level 1 |
| `python main.py --level N` | Opens the GUI at level `N` (1–7) |
| `python main.py --cli` | Solves levels 1–7 in the console with **every** registered solver |
| `python main.py --cli --algorithm "A* (h3) + deadlock"` | Same, but only with the named solver. `--algorithm` can be repeated to compare several. |
| `python main.py --benchmark` | Runs the benchmark over all solvers and levels and writes the report |

In CLI mode each solver prints `cost`, `expanded`, `generated`, `max_frontier`, time, and the action sequence (or "No solution found").

The solver names accepted by `--algorithm` are the keys of the `SOLVERS` registry (see [Section 8.5](#85-the-solvers-registry)).

---

## 4. Level Files (`sokoban/levels/`)

Levels are plain-text grids:

| Symbol | Meaning |
|:---:|---|
| `O` | Wall |
| `R` | Player |
| `B` | Box |
| `S` | Target |
| ` ` (space) | Empty floor |
| `.` | Player standing on a target |
| `*` | Box standing on a target |

- Levels 1–5 are the five examples of Figure 4 (Part 1).
- Level 6 is **Fig 7 Ex 1**: a 7×7 two-chamber room with a central doorway.
- Level 7 is **Fig 7 Ex 2**: an 8×6 stepped warehouse with a cluster of 4 boxes and 4 targets.

Rows shorter than the widest row are padded with walls on the right.

---

## 5. The Puzzle Model (`sokoban_puzzle.py`)

### 5.1 Flyweight design: `BoardLayout` + `SokobanPuzzle`

A level has **static** data (walls, targets, floor shape) and **dynamic** data (player, boxes). Search creates hundreds of thousands of states, so the static data is stored once and shared.

| Class | Holds | Notes |
|---|---|---|
| `BoardLayout` (frozen dataclass) | `rows`, `width`, `height`, `walls`, `targets`, plus `walkable`, `push_distances`, `dead_squares` | Only `rows/width/height/walls/targets` take part in `==` and `hash` (the other three use `compare=False, hash=False`). |
| `SokobanPuzzle` | `layout` (shared reference), `player` (tuple), `boxes` (`frozenset` of tuples) | Uses `__slots__` and blocks attribute changes, so states are immutable and hashable. |

Why that `compare=False` detail matters: `BoardLayout` is used as a **dictionary key** by the deadlock cache. Equality is decided by the cheap geometric fields, not by the large precomputed tables.

### 5.2 Parsing and validation (`_parse_lines`)

1. Reject unknown symbols; pad short rows with walls.
2. Collect walls, targets, boxes, and the player. Require **exactly one player** and **equal numbers of boxes and targets**.
3. **Flood-fill** (BFS) from the player over non-wall cells.
   - If the fill touches the grid border → `ValueError("level is not enclosed")`.
   - If any box or target is outside the filled region → `ValueError`.
4. Floor cells that the fill did not reach are converted into walls. After this step `layout.walkable` is exactly the playable region.
5. Precompute **push distances** and **dead squares** (Section 10). This happens once per level, not once per state.

### 5.3 Successor function

`successorFunction()` returns a **list** of `(action, new_state)` pairs. For each of the four directions:

1. Compute the adjacent cell. If it is a wall (or outside the grid), skip the direction.
2. If the adjacent cell holds a box, compute the cell beyond it. If that cell is a wall or holds another box, the push is illegal; skip. Otherwise the box moves one cell.
3. Build the successor with `_from_successor`, which reuses the shared layout and **skips re-validation** (a speed optimization for internal states).

```python
def successorFunction(self) -> list[tuple[str, "SokobanPuzzle"]]:
    successors = []
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
```

A move that is not a push leaves `boxes` untouched (the same frozenset object is reused). This is also what the deadlock pruning relies on: if `successor.boxes - current.boxes` is empty, no box moved.

`isGoal()` is simply `boxes == layout.targets`.

---

## 6. The Search Node (`node.py`)

A `Node` is one entry in the search tree:

| Field | Meaning |
|---|---|
| `state` | The `SokobanPuzzle` |
| `parent` | Predecessor node (`None` for the root) |
| `action` | The move that led from parent to this node |
| `g` | Path cost so far = number of moves (`parent.g + 1`) |
| `f` | `g + h(state)`, set by `setF(heuristic)` (A\* only) |

`getSolution()` walks parent links to build the action list; `getPath()` builds the list of states (used by the GUI for playback). `expand()` wraps each successor in a child `Node`.

---

## 7. BFS (`search.py`)

BFS uses a FIFO `deque`. Because every move costs 1, the first goal it reaches is a **shortest** solution.

Data structures:

- `frontier` (deque) and `frontier_states` (set) — the queue and a fast membership test.
- `explored` (set) — states already expanded.

Per expansion, for each child:

```text
1. if child.state in explored or in frontier_states   → skip (duplicate)
2. if deadlock pruning is on and the pushed box is on a dead cell
                                                       → pruned += 1, skip
3. if child.state is goal                              → return (goal test at generation)
4. append to frontier
```

Other details:

- The goal test happens **when a child is generated** (a standard BFS optimization that is still optimal for unit costs).
- With `use_deadlock=True`, a root that already contains a deadlocked box returns "no solution" immediately.
- `max_expanded` is an optional cap used by the benchmark; hitting it marks the result `incomplete=True`.

---

## 8. A\* (`search.py`)

### 8.1 Evaluation and queue

A\* orders nodes by `f(n) = g(n) + h(n)`. The heap holds tuples `(f, h, insertion_counter, node)`:

1. lowest `f` first,
2. then lowest `h` (prefer nodes that look closer to the goal),
3. then insertion order (FIFO) so heap comparison never has to compare `Node` objects.

### 8.2 Open and Closed sets

- `open_nodes: dict[state → Node]` — the best known node for each state on the frontier.
- `closed_nodes: dict[state → Node]` — expanded states.
- **Lazy replacement:** when a cheaper path to a state in Open is found, the new node is pushed and `open_nodes` is updated. The old heap entry stays in the heap and is skipped when popped because `open_nodes.get(state) is not current`.
- **Re-opening:** if a cheaper path reaches a state already in Closed (possible with an inconsistent heuristic such as `h2`), it is removed from Closed and put back in Open, and `reopened` is incremented.

### 8.3 Goal test

Unlike BFS, A\* tests for the goal **when a node is popped**, not when it is generated. This is what guarantees optimality with an admissible heuristic.

### 8.4 Order of checks for each child

```text
1. build child, compute child.f = g + h(state)
2. if child.f is infinity                  → skip   (only h3_exact can return ∞)
3. if deadlock pruning is on and the
   pushed box is on a dead cell            → pruned += 1, skip
4. Open / Closed duplicate handling (replace, re-open, or skip if not better)
5. push on the heap
```

Note that the heuristic is evaluated *before* the deadlock check, so pruned children still cost one heuristic evaluation. They also count toward `generated`.

### 8.5 The `SOLVERS` registry

`SOLVERS` maps a display name to a ready-to-call function. It is built with `functools.partial` and is wrapped in a read-only `MappingProxyType`:

| Registry key | Algorithm | Heuristic | Deadlock pruning |
|---|---|---|:---:|
| `BFS` | BFS | — | no |
| `BFS + deadlock` | BFS | — | yes |
| `A* (h1)` | A\* | `h1` | no |
| `A* (h1) + deadlock` | A\* | `h1` | yes |
| `A* (h2)` | A\* | `h2` | no |
| `A* (h2) + deadlock` | A\* | `h2` | yes |
| `A* (h3)` | A\* | `h3` | no |
| `A* (h3) + deadlock` | A\* | `h3` | yes |
| `A* (h3) + exact dead squares` | A\* | `h3_exact` | via `h = ∞` instead of the pruning flag |

Every solver returns a `SearchResult` with: `solution`, `actions`, `path`, `cost`, `expanded`, `generated`, `max_frontier`, `elapsed_seconds`, `incomplete`, `reopened`, `algorithm`, `pruned`, and a `found` property.

---

## 9. Heuristics (`heuristics.py`)

| Heuristic | Formula | Admissible | Consistent |
|:---:|---|:---:|:---:|
| `h1` | Number of boxes not on a target | Yes | Yes |
| `h2` | `2 × unplaced + Σ (Manhattan distance of each unplaced box to its nearest target)` | **No** | **No** |
| `h3` | Minimum-cost box→target assignment using wall-aware push distances, plus a player-approach term | Yes | Yes |
| `h3_exact` | Like `h3`, but returns `∞` for provably dead states | Yes (∞ only where no solution exists) | — |

### 9.1 `h1`

Each unplaced box needs at least one push and every push costs one move. Fast (`O(B)`) but weak: A\* with `h1` expands almost as much as BFS.

### 9.2 `h2`

Implemented exactly as the assignment's formula. The doubled "misplaced" term can overestimate (a box one cell from its target costs 1 push but contributes 2 + 1 = 3), so A\* with `h2` expands fewer nodes but **may return non-optimal solutions**. This is why A\* supports re-opening.

### 9.3 `h3`

1. Build a cost matrix: row = box, column = target, value = **push distance** from the box's cell to that target (precomputed at parse time, see Section 10).
2. If a push distance is `∞` (the box is on a dead square for that target), replace it with the **Manhattan distance** to that target. Manhattan ignores walls, so it is still a lower bound, and the heuristic stays finite.
3. Solve the minimum-cost one-to-one assignment with a **bitmask dynamic program** (`_min_assignment`, cached with `lru_cache`).
4. Add an **approach term**: `max(0, distance from player to nearest box − 1)`. The player must walk next to some box before the first push. The nearest box is chosen among *all* boxes (including ones already on targets), because an already-placed box might be the first one pushed — restricting to unplaced boxes would break admissibility.

The walking steps and the push steps are disjoint moves, so adding them is still a lower bound.

### 9.4 Why `h3` is deliberately *not* deadlock-aware

An earlier version returned `∞` when a box sat on an unreachable (dead) square. That silently pruned deadlocks inside plain `A* (h3)` and hid the real benefit of Part 3's explicit deadlock detection. The "Phase 0 cleanup" made `h3` **deadlock-agnostic** (finite Manhattan fallback), so that:

- `A* (h3)` vs `A* (h3) + deadlock` is a fair comparison of the *pruning* effect, and
- the original infinity-returning behavior is preserved as `h3_exact`, registered as `A* (h3) + exact dead squares`.

### 9.5 `h3_exact`

Same as `h3` but:

1. If any box is on a **dead square** and not on a target → return `∞` immediately.
2. Uses the raw push-distance rows (no Manhattan fallback). If the best assignment is infinite → return `∞`.

A\* skips children whose `f` is infinite, and also rejects the root if `root.f` is infinite. Because this pruning happens inside the heuristic, the `pruned` counter stays 0 for this solver.

`h3_exact` is **not** in the `HEURISTICS` dictionary (which only contains `h1`, `h2`, `h3`); it is reachable only through its `SOLVERS` entry.

---

## 10. Push Distances and Dead Squares (computed at parse time)

This precomputation is shared by `h3`, `h3_exact`, and the "exact dead squares" solver. It is computed in `_compute_push_distances` and stored in the layout.

### 10.1 Reverse push BFS

For each target, run a BFS **backwards** from the target. A box that is at cell `current` could have come from `previous = current − d` (where `d` is a direction) if:

- `previous` is floor, **and**
- `support = current − 2d` is floor (that is where the player must have stood to push the box from `previous` to `current`).

Each reverse step adds 1. The result for cell `c` and target `t` is the minimum number of pushes needed to bring a box from `c` to `t`, ignoring other boxes and ignoring whether the player can actually walk there. Unreachable cells get `∞`.

`layout.push_distances[cell]` is a tuple with one distance per target (targets sorted).

### 10.2 Dead squares

```python
dead_squares = {cell for cell, distances in push_distances.items()
                if not any(math.isfinite(d) for d in distances)}
```

A cell is a **dead square** if a box on it can never reach *any* target. This is the "exact" static dead set: it is the true set of cells that are useless for a box, considering walls only.

Dead squares are stored in `layout.dead_squares`. They are used by `h3_exact` and in tests as the ground truth against which the simpler corner/line detection is compared.

---

## 11. Deadlock Detection (`deadlock.py`)

### 11.1 What a deadlock is, and why detect it

A **deadlock** is a state from which no sequence of moves can reach the goal. Without detection the search keeps expanding such states, because `h1`, `h2`, and `h3` all return finite numbers for them. Every state below a deadlocked state is wasted work.

The module detects **static deadlocks**: dead cells that depend only on walls and targets, so they can be computed **once per board** and reused for every state.

The module exports:

```python
__all__ = ["corner_deadlocks", "line_deadlocks", "deadlock_positions",
           "hasDeadlock", "deadlockBoxes", "has_deadlock_incremental"]
```

### 11.2 Corner deadlocks (Figure 5) — `corner_deadlocks(layout)`

A cell is a corner deadlock when **all** of these hold:

1. It is a playable floor cell (`in layout.walkable`).
2. It is **not** a target.
3. It has a wall on a vertical side (**up or down**) **and** a wall on a horizontal side (**left or right**).

```python
has_vertical_wall   = (r-1, c) in walls or (r+1, c) in walls
has_horizontal_wall = (r, c-1) in walls or (r, c+1) in walls
if has_vertical_wall and has_horizontal_wall:  # and not a target
    deadlocks.add((r, c))
```

**Why it is dead:** to push a box you must stand on the opposite side. A box in a corner has a wall on one vertical and one horizontal side, so it can move along neither axis. It stays there forever.

Targets are excluded because a box in a corner target is simply solved.

### 11.3 Line deadlocks (Figure 6) — `line_deadlocks(layout)`

A **line deadlock** is a straight run of cells along a wall that a box can never leave, even though it is not itself in a corner.

The algorithm takes the corner set and looks for *pairs of corners that share a row or a column*:

1. Group corner cells by row (for horizontal segments) and by column (for vertical segments).
2. For every pair `(c1, c2)` in the same row, form the segment of cells between them, inclusive.
3. Accept the segment only if:
   - **every cell is floor and none is a target**, and
   - **one whole side is wall**: either every cell directly above is a wall, or every cell directly below is a wall (for vertical segments: every cell to the left, or every cell to the right).
4. Add the segment's cells to the result.
5. Repeat for columns.
6. Finally **remove the corner cells** from the result (`deadlocks - corners`), so `line_deadlocks` returns only the *interior* cells (drawn yellow in the GUI; corners are red).

**Why it is dead:** a box on such a segment touches a solid wall on one side, so it can only be pushed *along* the wall (you cannot stand inside the wall to push it away from it). Sliding along the segment only ever leads to one of the two corner endpoints, and there is no target on the way. So the box can never reach a target.

**Why targets break the rule:** if even one cell of the segment is a target, a box could slide along the wall into it, so the segment is not dead and is rejected.

### 11.4 The combined set — `deadlock_positions(layout)`

```python
dead = (corner_deadlocks(layout) | line_deadlocks(layout)) - layout.targets
```

- Union of corners and lines (corners are re-added here, since `line_deadlocks` removed them).
- The final `- layout.targets` is a safety net: targets can never be deadlock cells.
- **Cached** in a module-level dictionary `_deadlock_cache: dict[BoardLayout, frozenset[Position]]`. Since every state of a level shares the same `BoardLayout` object (and equal layouts hash equally), the detection runs once per level, no matter how many millions of states are examined.

The cache is a global dictionary used purely for memoization. It never changes what the function returns for a given layout, so it does not affect correctness.

### 11.5 State-level helpers

| Function | Returns | Use |
|---|---|---|
| `hasDeadlock(state)` | `bool` — is any box on a dead cell? | Root check at the start of BFS/A\* (`state.boxes & dead`) |
| `deadlockBoxes(state)` | `frozenset` of the offending boxes | Diagnostics / tests |
| `has_deadlock_incremental(state, pushed_box)` | `bool` — is the *just-pushed* box on a dead cell? `False` if `pushed_box is None` | Fast per-move check |

The incremental version exists because a single move changes at most one box. Re-checking all boxes after each move would repeat work already done for the parent state (which was not deadlocked, otherwise it would have been pruned).

### 11.6 Worked example

Take this 7×5 room:

```text
OOOOOOO
O     O
O BS  O      B = box at (2,2),  S = target at (2,3)
O   R O      R = player at (3,4)
OOOOOOO
```

**Corners** (floor, not a target, wall on a vertical side *and* a horizontal side): `(1,1)`, `(1,5)`, `(3,1)`, `(3,5)`.

**Lines:**

- Row 1: corners `(1,1)` and `(1,5)` share the row; cells `(1,1)…(1,5)` are floor, none is a target, and every cell above is wall → `(1,2)`, `(1,3)`, `(1,4)` are line deadlocks.
- Row 3: same reasoning with the wall below → `(3,2)`, `(3,3)`, `(3,4)`.
- Column 1: `(1,1)` and `(3,1)` share the column, left side is all wall → `(2,1)`.
- Column 5: → `(2,5)`.

Deadlock map (`C` = corner/red, `L` = line/yellow, blank = safe):

```text
OOOOOOO
OCLLLCO
OL   LO
OCLLLCO
OOOOOOO
```

Only the three middle cells `(2,2)`, `(2,3)`, `(2,4)` are safe for a box. That matches intuition: any box pushed against a wall with no target along that wall is lost.

**What pruning does here.** The shortest solution is `LEFT, LEFT, LEFT, UP, RIGHT` (5 moves): walk to `(2,1)` and push the box right onto `S`. Every solver finds exactly this solution. While searching, only three distinct pushes land a box on a dead cell:

- player at `(3,2)` pushes **UP** → box goes to `(1,2)`, a line deadlock → **pruned**;
- player at `(1,2)` pushes **DOWN** → box goes to `(3,2)`, a line deadlock → **pruned**;
- player at `(2,3)` pushes **LEFT** → box goes to `(2,1)`, a line deadlock → **pruned**.

The push that solves the puzzle (player at `(2,1)` pushing **RIGHT**, box to `(2,3)`) lands on the target, which is never dead, so it is kept. Every state beneath a pruned child is never generated.

Measured on this room (run against the code; the counters are deterministic):

| Solver | Cost | Expanded | Generated | Pruned |
|---|---:|---:|---:|---:|
| BFS | 5 | 21 | 65 | 0 |
| BFS + deadlock | 5 | 13 | 39 | 3 |
| A\* (h3) | 5 | 11 | 35 | 0 |
| A\* (h3) + deadlock | 5 | 9 | 29 | 3 |

Same cost in every row (optimality preserved), with fewer expansions and generations once the three doomed pushes are cut. In this particular room the corner and line cells (12 cells) happen to equal the exact `dead_squares` set, so the simple patterns lose nothing here. On boards with dead cells that are neither corners nor wall lines, the exact set is larger.

### 11.7 Soundness: why pruning keeps solutions

A pruned state is one where a box stands on a cell proven dead. By the arguments in 11.2 and 11.3 no solution passes through such a state (`h* = ∞`). Hence:

- BFS + deadlock still returns an optimal solution.
- A\* with an admissible heuristic + deadlock still returns an optimal solution.

The benchmark confirms this: every `+ deadlock` row has the same cost as its non-deadlock counterpart (Section 13). The test suite also checks that on the bundled levels **every** corner/line deadlock lies inside the exact `dead_squares` set (100 % precision — no false alarms).

### 11.8 Cost of detection

| Step | Cost |
|---|---|
| Corner detection | `O(W × H)` once per layout |
| Line detection | Per row/column, pairs of corners × segment length — small for real boards; once per layout |
| Per-child lookup | `O(1)` set membership |
| Finding the pushed box in search | `successor.boxes − current.boxes`, which is `O(B)` (B = number of boxes, small) |
| `has_deadlock_incremental` | `O(1)` given the pushed position |

### 11.9 What it does **not** detect (limitations)

The detection is static and local. These deadlock families are *not* covered:

- **Freeze / 2×2 deadlocks** — boxes or walls forming a 2×2 block that cannot be separated.
- **Dynamic deadlocks** — a box that is frozen only because of where *other boxes* currently stand.
- **Corral deadlocks** — regions the player can no longer reach.
- **Dead squares that are not corners or wall lines** — cells that are useless for geometric reasons but do not match the two patterns. The exact `dead_squares` set (Section 10.2) is stronger than corners + lines and can catch more.

Because of that, pruning is *conservative*: it removes only states that are certainly lost, never a state that might still be solvable.

### 11.10 `deadlock.py` vs. exact dead squares

| | Corner + line (`deadlock.py`) | Exact dead squares (`sokoban_puzzle.py` + `h3_exact`) |
|---|---|---|
| Idea | Two geometric patterns from the assignment | Reverse-push reachability from every target |
| Power | Subset of the dead set | Full static dead set |
| Where applied | Search loop (`use_deadlock=True`) | Inside `h3_exact` (returns `∞`) |
| Visible in `pruned` counter | Yes | No (`pruned = 0`) |
| Role in the project | The Part 3 deliverable | Ground truth / extra comparison solver |

---

## 12. How Deadlock Pruning Plugs Into the Searches

Both searches use the same idea: **after generating a child, if the move pushed a box onto a dead cell, drop the child.**

```python
dead = deadlock_positions(initial_state.layout) if use_deadlock else frozenset()
...
if dead:
    new_boxes = child.state.boxes - node.state.boxes     # empty if the move was not a push
    if new_boxes and next(iter(new_boxes)) in dead:
        pruned += 1
        continue
```

- When `use_deadlock=False`, `dead` is an empty frozenset, so `if dead:` is false and the check costs nothing.
- `new_boxes` has exactly one element after a push (the new box location) and is empty after a plain walk.
- This is the same logic as `has_deadlock_incremental`, written inline.

### 12.1 Root check

Before the loop, `hasDeadlock(initial_state)` is called when pruning is on. If the starting position already has a box on a dead cell, the search returns "no solution" without expanding anything.

### 12.2 Where the check sits in each algorithm

| | Order inside the child loop |
|---|---|
| **BFS** | duplicate check → **deadlock check** → goal test → enqueue |
| **A\*** | compute `f` → skip if `f = ∞` → **deadlock check** → Open/Closed handling → push |

Consequences:

- In BFS, duplicates are discarded before the deadlock check, so they are not counted as `pruned`.
- A goal state has every box on a target, and targets are never dead cells, so the deadlock check can never reject the goal.
- In A\*, a pruned child has already had its heuristic computed. Pruning saves **expansions and memory**, not that one evaluation.

### 12.3 Counter definitions

| Counter | Meaning |
|---|---|
| `expanded` | States removed from the frontier and expanded |
| `generated` | Root (1) + all successors produced, **including** duplicates and pruned children |
| `pruned` | Children discarded by the deadlock check |
| `max_frontier` | Largest size of the frontier (BFS deque, or A\* open set) |
| `reopened` | Closed states re-opened by A\* after finding a cheaper path |

### 12.4 Why pruning helps `A* (h3)` even though `h3` is informed

`h3` is deadlock-agnostic: for a box on a dead square it falls back to Manhattan distance and returns a finite value. A\* can therefore still wander through doomed regions whenever their `f` looks competitive. Pruning removes those regions before they enter Open.

---

## 13. Performance Comparison

### 13.1 Benchmark results (levels 1–7)

Numbers are from `results_part3.md` (median of 3 repetitions). Times will vary by machine; the counters are deterministic.

| Level | Algorithm | Cost | Expanded | Generated | Max Frontier | Pruned | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Example 1 | BFS | 4 | 11 | 32 | 5 | 0 | 0.000073 |
| Example 1 | BFS + deadlock | 4 | 11 | 32 | 5 | 0 | 0.000076 |
| Example 1 | A* (h3) | 4 | 5 | 15 | 6 | 0 | 0.000076 |
| Example 1 | A* (h3) + deadlock | 4 | 5 | 15 | 6 | 0 | 0.000081 |
| Example 2 | BFS | 29 | 1,079 | 3,246 | 89 | 0 | 0.006782 |
| Example 2 | BFS + deadlock | 29 | 459 | 1,377 | 35 | 13 | 0.002955 |
| Example 2 | A* (h3) | 29 | 353 | 1,115 | 121 | 0 | 0.005342 |
| Example 2 | A* (h3) + deadlock | 29 | 135 | 431 | 65 | 12 | 0.002075 |
| Example 3 | BFS | 20 | 1,854 | 5,163 | 244 | 0 | 0.011429 |
| Example 3 | BFS + deadlock | 20 | 915 | 2,548 | 109 | 38 | 0.005835 |
| Example 3 | A* (h3) | 20 | 445 | 1,247 | 188 | 0 | 0.007471 |
| Example 3 | A* (h3) + deadlock | 20 | 327 | 925 | 123 | 17 | 0.005502 |
| Example 4 | BFS | 19 | 3,446 | 9,969 | 955 | 0 | 0.023354 |
| Example 4 | BFS + deadlock | 19 | 1,685 | 4,905 | 390 | 105 | 0.011549 |
| Example 4 | A* (h3) | 19 | 561 | 1,646 | 309 | 0 | 0.011360 |
| Example 4 | A* (h3) + deadlock | 19 | 439 | 1,310 | 207 | 26 | 0.008996 |
| Example 5 | BFS | 30 | 315,127 | 1,029,632 | 41,050 | 0 | 2.974520 |
| Example 5 | BFS + deadlock | 30 | 122,800 | 401,559 | 14,810 | 4,467 | 1.103959 |
| Example 5 | A* (h3) | 30 | 18,247 | 61,699 | 13,163 | 0 | 0.498116 |
| Example 5 | A* (h3) + deadlock | 30 | 9,537 | 32,865 | 6,499 | 720 | 0.245331 |
| Fig 7 Ex 1 | BFS | 41 | 2,307 | 5,650 | 129 | 0 | 0.013424 |
| Fig 7 Ex 1 | BFS + deadlock | 41 | 1,128 | 2,780 | 69 | 54 | 0.006826 |
| Fig 7 Ex 1 | A* (h3) | 41 | 2,182 | 5,321 | 204 | 0 | 0.040616 |
| Fig 7 Ex 1 | A* (h3) + deadlock | 41 | 1,000 | 2,459 | 120 | 54 | 0.018281 |
| Fig 7 Ex 2 | BFS | 55 | 54,726 | 146,035 | 2,798 | 0 | 0.416970 |
| Fig 7 Ex 2 | BFS + deadlock | 55 | 6,432 | 16,983 | 302 | 829 | 0.044313 |
| Fig 7 Ex 2 | A* (h3) | 55 | 49,972 | 133,404 | 3,704 | 0 | 1.400845 |
| Fig 7 Ex 2 | A* (h3) + deadlock | 55 | 5,718 | 15,186 | 444 | 790 | 0.135853 |

**Reading the table:** for each level, the cost is identical across all four solvers. That is the optimality check — pruning never changed the answer, it only reduced the work.

### 13.2 Reduction in expanded states from deadlock pruning

| Level | BFS → BFS + deadlock | A\* (h3) → A\* (h3) + deadlock |
|---|---|---|
| Example 1 | 11 → 11 (0 %) | 5 → 5 (0 %) |
| Example 2 | 1,079 → 459 (57.5 %) | 353 → 135 (61.8 %) |
| Example 3 | 1,854 → 915 (50.6 %) | 445 → 327 (26.5 %) |
| Example 4 | 3,446 → 1,685 (51.1 %) | 561 → 439 (21.7 %) |
| Example 5 | 315,127 → 122,800 (61.0 %) | 18,247 → 9,537 (47.7 %) |
| Fig 7 Ex 1 | 2,307 → 1,128 (51.1 %) | 2,182 → 1,000 (54.2 %) |
| Fig 7 Ex 2 | 54,726 → 6,432 (88.2 %) | 49,972 → 5,718 (88.6 %) |

### 13.3 Key insights

1. **Pruning pays off most where deadlocks are plentiful.** On Fig 7 Ex 2, A\* (h3) drops from 49,972 to 5,718 expansions (−88.6 %); on Example 5, from 18,247 to 9,537 (−47.7 %).
2. **No effect on a trivial level.** Example 1 has no reachable deadlock pushes (`pruned = 0`), so the counters are identical and the time is within noise.
3. **`BFS + deadlock` can beat `A* (h3) + deadlock` in wall-clock time on Fig 7.** Fig 7 Ex 1: 0.0068 s vs 0.0183 s; Ex 2: 0.0443 s vs 0.1359 s. Once pruning removes most of the tree, BFS's cheap queue operations outpace the per-node cost of `h3` (cost-matrix build plus the assignment DP).
4. **`h3` gives a decisive edge over weaker heuristics on Examples 2–5**, but on the two Fig 7 levels its advantage over `h2` is small (see `results_part3.md` for the `h1`/`h2` rows).
5. **Pruned vs. frontier:** deadlock pruning also shrinks `max_frontier` (e.g. Fig 7 Ex 2 BFS: 2,798 → 302), which means lower memory use, not just fewer expansions.
6. **`A* (h3) + exact dead squares`** reports `Pruned = 0` because it rejects states through `f = ∞` rather than through the pruning branch.

---

## 14. The GUI (`gui.py`)

A Pygame window (1200×780, resizable) for running solvers and replaying solutions.

### 14.1 Controls

| Control | Keyboard | What it does |
|---|:---:|---|
| Level buttons | `1`–`7` | Switch level (resets playback) |
| Algorithm | `A` | Toggle BFS ↔ A\* |
| Heuristic | `H` | Cycle `h1 → h2 → h3` (buttons only appear when A\* is selected) |
| **Deadlock pruning** | `D` | Toggle `use_deadlock` for the next solve |
| **Deadlock overlay** | `X` | Show/hide the corner and line deadlock tint |
| Solve | `S` | Run the selected solver in a background thread |
| Compare | `C` | Run **all** registered solvers on the current level |
| Play / pause | `Space` | Animate the solution |
| Step forward / back | `→`, `N` / `←`, `B` | Move one state at a time |
| Reset | `R` | Back to step 0 |
| Speed | `+` / `−` | Change animation delay (60–1500 ms) |

### 14.2 Deadlock overlay (`X`)

When the overlay is on, `_draw_board` calls `corner_deadlocks(layout)` and `line_deadlocks(layout)` and tints the cells:

| Colour | Meaning |
|---|---|
| **Red** (semi-transparent, red border) | Corner deadlock |
| **Yellow** (semi-transparent, yellow border) | Line deadlock (interior cells only) |

The tint is drawn **only on empty floor cells** — never over a box, a target, or the player — so the overlay cannot hide anything important. Because targets are excluded from deadlocks by definition, a target is never tinted anyway. The overlay is purely visual: turning it on or off does not change what the solver does. Only the `D` toggle changes the search.

Note that the overlay calls `corner_deadlocks` / `line_deadlocks` directly, which are not cached (only `deadlock_positions` is), so they are recomputed every frame while the overlay is shown. This is cheap on these small boards.

### 14.3 Solving in the background

- `S` starts a **daemon thread** so the window stays responsive.
- Results come back through a `queue.Queue`; the main loop drains it every frame.
- Each request gets a **generation number**. If a stale result arrives (the same configuration was re-requested), it is ignored.
- `C` runs all solvers sequentially in a single batch thread and posts each result as it finishes, so the comparison table fills in row by row.

### 14.4 Result cache

Results are stored under the key `(level_index, algorithm, heuristic, use_deadlock)`. Toggling deadlock pruning therefore switches between two separate cached results and never mixes them up.

The `A* (h3) + exact dead squares` solver is stored under heuristic name `h3_exact`. It has no button of its own; it appears in the comparison table after you press `C`.

**Known quirk in the current code.** Results are written under the key produced by `_key_to_components`, which always labels BFS as heuristic `h1`. The key used to *look results up* (`_current_cache_key`) uses whatever heuristic is currently selected. If you pick A\* with `h2` or `h3`, switch back to BFS, and press `S`, the BFS result is stored under `(level, "BFS", "h1", ...)` but the panel looks under `(level, "BFS", "h3", ...)`, so it shows nothing. Selecting `h1` first, or using `C` (compare) and reading the table, avoids it. A one-line fix is to make `_current_cache_key` return `"h1"` as the heuristic whenever the selected algorithm is BFS.

### 14.5 Info panel

- A status pill: `READY TO SOLVE`, `SEARCHING`, `SOLUTION FOUND`, `NO SOLUTION`, or `SOLVER ERROR`.
- Cost in moves, the current action, a progress bar and step counter.
- Metric cards: iterations (expanded), generated, **pruned (deadlock)**, max frontier, search time.
- **Algorithm comparison table** with columns `ALG, COST, ITER, GEN, PRUN, OPEN, TIME`. A `*` marks the lowest cost among the solvers run, and `!` marks a cost above that minimum (a suboptimal result such as one from `h2`). `LIMIT` is shown for a search stopped by an expansion cap.

### 14.6 Sprites

If `assets/tileset.png` exists it is sliced into a 13×8 grid of sprites (floor, wall, target, box, box-on-target, four player directions). If it is missing, the GUI draws simple shapes instead. The player sprite faces the direction of the last move.

---

## 15. Test Suite

56 unit tests across 5 modules:

| Module | Covers |
|---|---|
| `test_sokoban.py` | Parsing, enclosure validation, move/push rules, state immutability |
| `test_astar.py` | Optimality of `h1`/`h3`, re-opening with `h2`, `Node.setF`, path replay |
| `test_heuristics.py` | Admissibility and consistency on exhaustive small state spaces |
| `test_deadlock.py` | Corner/line detection on the Figure 5/6 layouts, soundness against dead squares, caching, GUI smoke test |
| `test_fixes.py` | Regression checks and verification of the 9-entry solver registry |

Run:

```sh
python3 -m unittest discover -s sokoban/tests -v
```

---

## 16. Full Execution Flow

```text
                     ┌──────────────────────┐
                     │   python main.py     │
                     └──────────┬───────────┘
                                │
                     ┌──────────▼───────────┐
                     │  sokoban.main.main() │
                     │  Parse CLI arguments │
                     └───┬──────────┬───────┘
                         │          │ --cli / --benchmark
                         │          └──► solve in console / write report
                         │
                     ┌───▼──────────────────┐
                     │  SokobanGUI.__init__ │
                     │  Load levels 1–7     │   ← parse once per level:
                     │  Register 9 solvers  │     walls, targets, push distances,
                     └──────────┬───────────┘     dead squares
                                │
                    ┌───────────▼───────────┐
                    │    SokobanGUI.run()   │
                    │  pygame.init()        │
                    └───────────┬───────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │      MAIN LOOP (60 FPS)     │
                 │  - Poll keyboard / mouse    │
                 │  - Drain result queue       │
                 │  - Advance playback timer   │
                 │  - Draw board (+ overlay)   │
                 │  - Draw info + comparison   │
                 └──────────────┬──────────────┘
                                │
              User presses 'S'  │
                                │
                 ┌──────────────▼──────────────┐
                 │  _start_solve()             │
                 │  Spawn background thread    │
                 └──────────────┬──────────────┘
                                │
                      ┌─────────▼──────────┐
                      │  WORKER THREAD     │
                      │  astar() / bfs():  │
                      │  1. root deadlock? │
                      │  2. pop node       │
                      │  3. expand         │
                      │  4. for each child │
                      │     - duplicate?   │
                      │     - pushed box   │
                      │       on dead cell?│
                      │       → PRUNE      │
                      │     - else queue   │
                      │  5. post result    │
                      └─────────┬──────────┘
                                │
                 ┌──────────────▼──────────────┐
                 │  Main thread reads result   │
                 │  Caches under key tuple     │
                 │  Updates metrics and table  │
                 └──────────────┬──────────────┘
                                │
              User presses Space│
                                │
                 ┌──────────────▼──────────────┐
                 │  Step-by-step playback of   │
                 │  result.path                │
                 └─────────────────────────────┘
```

---

## 17. Key Concepts Summary

| Concept | Implementation |
|---|---|
| **State space** | State = `(player, frozenset(boxes))` over a shared `BoardLayout`. Actions `UP/DOWN/LEFT/RIGHT`, unit cost. |
| **Immutability and sharing** | `__slots__` states with blocked setattr; one `BoardLayout` per level shared by all states (flyweight). |
| **BFS** | FIFO queue, goal test at generation, optimal for unit cost. |
| **A\*** | `f = g + h`, Open/Closed dictionaries, lazy heap replacement, re-opening, goal test at expansion. |
| **Admissibility / consistency** | `h1` and `h3` admissible and consistent; `h2` neither, so A\*(h2) may be suboptimal. |
| **Phase 0 cleanup** | `h3` uses a finite Manhattan fallback; the infinity-returning variant is kept as `h3_exact`. |
| **Corner deadlock** | Non-target floor cell with a wall on a vertical side and a wall on a horizontal side. |
| **Line deadlock** | Run of non-target floor cells between two corner deadlocks with one full side of wall; interior cells only. |
| **Combined set + cache** | `(corners ∪ lines) − targets`, computed once per `BoardLayout`, stored in a module-level memo dict. |
| **Incremental pruning** | After a push, test only the one moved box against the dead set; plain walks skip the check. |
| **Soundness** | Pruned states have `h* = ∞`, so optimality is preserved; on bundled levels every detected deadlock is inside the exact dead-square set. |
| **Limitations** | Static only: no freeze (2×2), dynamic, or corral deadlocks. |
| **Exact dead squares** | Reverse push BFS from targets at parse time; powers `h3_exact`. |
| **Modularity** | Model, heuristics, deadlocks, search, GUI, and benchmark are separate modules; the only global state is the deadlock memo cache. |
