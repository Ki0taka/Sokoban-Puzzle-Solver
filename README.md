# Sokoban Search Lab

A Python implementation of the USTHB Master 1 Visual Computing Sokoban
project. It models the puzzle as immutable, hashable states and compares
Breadth-First Search (BFS) with A* using three heuristics. A Pygame interface
lets you choose an algorithm, animate its solution, and compare measured search
results.

> **Requirements:** Python 3.10 or later. The GUI requires Pygame; the model,
> search algorithms, CLI, benchmark, and tests use only the standard library.

## Features

- Sokoban model with shared static layouts, enclosure validation, and immutable
  dynamic states.
- Optimal unit-cost BFS and lecture-style graph-search A* with Open replacement
  and Closed re-opening.
- Three heuristics: misplaced boxes, the assignment's Manhattan formula, and a
  wall-aware push-distance assignment with deadlock detection.
- Pygame selectors for BFS/A*, h1/h2/h3, playback, and all-algorithm comparison.
- Five reconstructed Figure 4 levels, unit tests, and a repeatable benchmark.

## Quick start

```bash
python -m venv .venv
# Activate: Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Choose a level using `1`–`5`, select BFS or A*, choose a heuristic for A*, then
press Solve. Press Compare to run every registered solver on the current level.

### GUI controls

| Input | Action |
| --- | --- |
| `1`–`5` | Select a level |
| `A` | Toggle BFS / A* |
| `H` | Cycle A* heuristic (`h1`, `h2`, `h3`) |
| `S` | Solve with the selected algorithm |
| `C` | Compare all registered solvers on this level |
| `Space` | Play or pause; Play restarts when playback is at the end |
| `→` / `N` | Step forward |
| `←` / `B` | Step backward |
| `R` | Reset playback |
| `+` / `-` | Change playback speed |

Results are cached by level and algorithm. Switching levels or algorithms
returns to any solution already computed for that selection.

## Console and benchmark

Solve all levels with all registered algorithms:

```bash
python main.py --cli
```

Select one or more algorithms in CLI mode:

```bash
python main.py --cli --algorithm "A* (h1)" --algorithm "A* (h3)"
```

Run the bounded benchmark and write the full Markdown report to `results.md`:

```bash
python main.py --benchmark
```

The benchmark caps each run at 500,000 expanded nodes. Capped runs are labeled
`limit`; none of the runs in the table below hit the cap.

## Tests

```bash
python -m unittest discover -s sokoban/tests -v
```

Coverage includes state parsing and rendering, wall enclosure, move/push rules,
hashing and immutability, heuristic values, exhaustive admissibility checks on
a small state space, A* re-opening, optimality comparisons, and replay of
solutions on all bundled levels.

## Project structure

```text
main.py                       Root application entry point
README.md                     Project overview and benchmark analysis
LEVEL_RECONSTRUCTIONS.md      Text grids and Figure 4 reconstruction notes
results.md                    Output from the most recent benchmark
sokoban/
  sokoban_puzzle.py            Model, parser, enclosure, and static push maps
  node.py                      Search node, g/f, and path reconstruction
  heuristics.py                h1, h2, h3, descriptions
  search.py                    BFS, A*, SearchResult, and solver registry
  benchmark.py                 Bounded comparison and Markdown reporting
  gui.py                       Pygame algorithm/heuristic comparison UI
  levels/                      Five text maps
  tests/                       Model, heuristic, and A* test suites
PROJECT_EXPLANATION.md         Detailed project walkthrough
```

## State and search design

`SokobanPuzzle` holds a shared immutable `BoardLayout` (walls, targets, and
precomputed per-target push distances) and dynamic data (player coordinate and
`frozenset` of box coordinates). Successors reuse the layout and never mutate
their parent state. The loader flood-fills from the player, rejects a reachable
route to the grid edge, and converts unreachable non-wall cells into walls.

BFS uses a FIFO frontier and returns a minimum-move solution because each move
costs one. A* uses `f(n) = g(n) + h(n)`, a heap ordered by `(f, h, insertion
order)`, and tests for a goal when a node is dequeued. Better Open entries
replace older ones lazily; lower-cost paths can re-open Closed states. Both
algorithms return the same `SearchResult` fields. To add a solver, implement a
function accepting a `SokobanPuzzle` and returning a `SearchResult`, then add it
to the solver registry.

## Heuristic properties

The lecture defines admissibility as `h(n) <= h*(n)` and consistency as
`h(n) <= c(n,a,n') + h(n')`. In graph-search A*, a consistent heuristic makes
`f` non-decreasing along a path and guarantees optimality when the goal is
dequeued. The implementation also supports re-opening Closed states for
inconsistent heuristics.

| Heuristic | Definition | Admissible? | Consistent? | Reason |
| --- | --- | --- | --- | --- |
| `h1` | Number of boxes not on targets | Yes | Yes | Each such box needs at least one push; one action can reduce the count by at most one. |
| `h2` | `2 × unplaced boxes + sum of each box's nearest-target Manhattan distance` | **No** | **No** | One box one push from its target has true remaining cost 1 but `h2 = 3`; this also violates the consistency inequality on that edge. |
| `h3` | Minimum one-to-one wall-aware push assignment plus a lower bound on walking to the first box | Yes | Yes | Push assignment underestimates required pushes; approach steps happen before the first push and are disjoint. The approach bound uses the nearest box, including one already on a target, to remain safe. |

For h3, reverse BFS from each target follows only geometrically possible
predecessor pushes (the prior box cell and its required player support cell must
both be floor). The distance vectors are computed once per layout. A bitmask
assignment finds the minimum sum over one-to-one box/target matches. A box that
cannot reach any target in the reverse-push graph is a dead square; an unplaced
box there gives h3 infinity and is pruned.

**h2 is not an admissible lower bound**, so it cannot be guaranteed to return
the shortest solution. The tested levels happen to produce BFS-optimal costs
with h2; that is an observation about these maps, not a guarantee. The h3
approach term is intentionally measured to the nearest box of any status. Using
only unplaced boxes could overestimate if a box already on a target must be
pushed before the player can approach another box.

## Benchmark results

One local run on the five Figure 4 reconstructions. Generated counts include
the root and every successor generated, including duplicate states. Times are
machine-dependent; frontier size is a useful proxy for the memory held by the
search.

| Level | Algorithm | Solution cost | Expanded | Generated | Max frontier | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Example 1 | BFS | 4 | 11 | 32 | 5 | 0.000084 |
| Example 1 | A* (h1) | 4 | 11 | 32 | 5 | 0.000112 |
| Example 1 | A* (h2) | 4 | 8 | 24 | 6 | 0.000109 |
| Example 1 | A* (h3) | 4 | 5 | 15 | 6 | 0.000080 |
| Example 2 | BFS | 29 | 1,079 | 3,246 | 89 | 0.006955 |
| Example 2 | A* (h1) | 29 | 1,079 | 3,246 | 89 | 0.010657 |
| Example 2 | A* (h2) | 29 | 679 | 2,080 | 78 | 0.008248 |
| Example 2 | A* (h3) | 29 | 353 | 1,115 | 121 | 0.005198 |
| Example 3 | BFS | 20 | 1,854 | 5,163 | 244 | 0.011794 |
| Example 3 | A* (h1) | 20 | 1,701 | 4,750 | 218 | 0.017010 |
| Example 3 | A* (h2) | 20 | 650 | 1,835 | 159 | 0.008802 |
| Example 3 | A* (h3) | 20 | 445 | 1,247 | 188 | 0.007384 |
| Example 4 | BFS | 19 | 3,446 | 9,969 | 955 | 0.023378 |
| Example 4 | A* (h1) | 19 | 2,115 | 6,161 | 679 | 0.022599 |
| Example 4 | A* (h2) | 19 | 632 | 1,854 | 220 | 0.009918 |
| Example 4 | A* (h3) | 19 | 561 | 1,646 | 309 | 0.011177 |
| Example 5 | BFS | 30 | 315,127 | 1,029,632 | 41,050 | 3.170892 |
| Example 5 | A* (h1) | 30 | 213,074 | 699,183 | 40,459 | 3.273552 |
| Example 5 | A* (h2) | 30 | 24,394 | 81,189 | 9,947 | 0.525434 |
| Example 5 | A* (h3) | 30 | 18,247 | 61,699 | 13,163 | 0.491570 |

> **Phase 0 Baseline Note:** In Part 2's initial implementation, `h3` returned `math.inf`
> for boxes on unreachable reverse-push tiles, implicitly pruning dead squares during search.
> In Part 3, `h3` was clarified to be strictly deadlock-agnostic by providing a finite Manhattan
> distance fallback for unreachable cells. This raised the baseline node expansions for pure A*(h3)
> (e.g. from 135 to 353 on Example 2, and 9,537 to 18,247 on Example 5), ensuring all subsequent
> comparisons against explicit deadlock pruning are fair and scientifically valid.

### Results analysis

- **Expanded nodes:** h3 expands the fewest nodes on every tested level. On
  Example 5 it expands 9,537 nodes versus 315,127 for BFS. h2 is second-lowest
  in this benchmark, despite having no optimality guarantee.
- **Solution quality:** all algorithms returned costs 4, 29, 20, 19, and 30 on
  the respective levels in this run. No h2 cost was above BFS, so its measured
  cost difference was zero for these five maps. The tests verify h2's
  non-admissibility separately.
- **Frontier/memory:** h3 has the smallest maximum frontier on Examples 2–5.
  Example 1's tiny frontier is 5 for BFS/h1 and 6 for h2/h3. On Example 5, h3's
  frontier peak is 6,499 compared with BFS's 41,050.
- **Time:** h3's stronger estimate reduces work, but computing assignments has
  overhead. It is faster than h2 on Example 2 and slower on Examples 1, 3, 4,
  and 5 in this run. h2 is the fastest on Examples 1, 3, 4, and 5.
  Thus h3 beats h1 and h2 in node count and usually frontier size, not in every
  wall-clock measurement.

## Figure 4 map notes

The example boards are reconstructed from raster figures with faint grid lines,
not supplied as coordinate tables. The corrected visible object placements and
the remaining uncertain one-cell wall details are documented in
[`LEVEL_RECONSTRUCTIONS.md`](LEVEL_RECONSTRUCTIONS.md). Every bundled map is
validated for enclosure and equal box/target counts, and its solution is
independently replayed in the tests.

## Deadlock detection

### Definitions and detection rules
In Sokoban, a **deadlock** is a state from which no solution can be reached because one or more boxes cannot be placed onto targets. Section D of the specification distinguishes two static deadlock patterns:

1. **Corner deadlock (Figure 5):** A floor cell that is *not* a target and is bounded by walls on two perpendicular adjacent sides (one vertical in `{UP, DOWN}` and one horizontal in `{LEFT, RIGHT}`). A box pushed into such a corner cannot move again.
2. **Line deadlock (Figure 6):** A segment of floor cells connecting two corner-deadlock cells along a row or column where:
   - Every cell of the segment is walkable floor and **none is a target** (if a target were present, a box could slide along the wall into it).
   - Both endpoints are corner deadlocks.
   - One entire perpendicular side of the segment is solid wall (all cells directly above/below for horizontal lines, or directly left/right for vertical lines).
   A box pushed against such a wall cannot be pushed away because the player cannot access the wall side to push in the opposite direction.

These deadlocks depend solely on static board geometry (walls and targets), not on dynamic crate positions, and are computed once per `BoardLayout` and cached.

### Soundness and limitations
- **Soundness:** A lone box placed on a corner or line deadlock position can never reach any target, meaning $h^*(s) = \infty$. Pruning any state with a box on these positions discards only unsolvable subtrees; it never removes an optimal path, preserving admissibility and solution cost.
- **What they do NOT catch:** These rules are static single-box rules. They miss:
  - **Dynamic freeze deadlocks:** e.g., a 2×2 block of 4 boxes (or boxes and walls) where no box can move even though none is in a corner.
  - **Corridor deadlocks:** two boxes stuck face-to-face in a tunnel.
  - **Dead squares without corner lines:** cells that cannot reach a target due to complex wall geometry without forming a full straight wall segment between two corners.

### Diagnostic comparison with exact dead squares
Computing the exact dead-square set via reverse-pull BFS from targets shows:

| Level | Corner deadlocks | Line deadlocks | Detected union | Exact dead squares | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Level 1 | 3 | 4 | 7 | 7 | 100% |
| Level 2 | 7 | 19 | 26 | 26 | 100% |
| Level 3 | 6 | 2 | 8 | 8 | 100% |
| Level 4 | 8 | 2 | 10 | 10 | 100% |
| Level 5 | 8 | 4 | 12 | 12 | 100% |
| Level 6 | 6 | 3 | 9 | 9 | 100% |
| Level 7 | 5 | 2 | 7 | 7 | 100% |

On all 7 bundled levels, the professor's corner and line rules identify 100% of the single-box dead squares (`detected == exact`).

### Part 3 benchmark results

| Level | Algorithm | Solution cost | Iterations (expanded) | Generated | Max frontier | Pruned | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Example 1 | BFS | 4 | 11 | 32 | 5 | 0 | 0.000084 |
| Example 1 | BFS + deadlock | 4 | 11 | 32 | 5 | 0 | 0.000089 |
| Example 1 | A* (h3) | 4 | 5 | 15 | 6 | 0 | 0.000080 |
| Example 1 | A* (h3) + deadlock | 4 | 5 | 15 | 6 | 0 | 0.000081 |
| Example 2 | BFS | 29 | 1,079 | 3,246 | 89 | 0 | 0.006955 |
| Example 2 | BFS + deadlock | 29 | 459 | 1,377 | 35 | 13 | 0.003041 |
| Example 2 | A* (h3) | 29 | 353 | 1,115 | 121 | 0 | 0.005198 |
| Example 2 | A* (h3) + deadlock | 29 | 135 | 431 | 65 | 12 | 0.002024 |
| Example 3 | BFS | 20 | 1,854 | 5,163 | 244 | 0 | 0.011794 |
| Example 3 | BFS + deadlock | 20 | 915 | 2,548 | 109 | 38 | 0.005804 |
| Example 3 | A* (h3) | 20 | 445 | 1,247 | 188 | 0 | 0.007384 |
| Example 3 | A* (h3) + deadlock | 20 | 327 | 925 | 123 | 17 | 0.005518 |
| Example 4 | BFS | 19 | 3,446 | 9,969 | 955 | 0 | 0.023378 |
| Example 4 | BFS + deadlock | 19 | 1,685 | 4,905 | 390 | 105 | 0.011679 |
| Example 4 | A* (h3) | 19 | 561 | 1,646 | 309 | 0 | 0.011177 |
| Example 4 | A* (h3) + deadlock | 19 | 439 | 1,310 | 207 | 26 | 0.009015 |
| Example 5 | BFS | 30 | 315,127 | 1,029,632 | 41,050 | 0 | 3.170892 |
| Example 5 | BFS + deadlock | 30 | 122,800 | 401,559 | 14,810 | 4,467 | 1.183871 |
| Example 5 | A* (h3) | 30 | 18,247 | 61,699 | 13,163 | 0 | 0.491570 |
| Example 5 | A* (h3) + deadlock | 30 | 9,537 | 32,865 | 6,499 | 720 | 0.249671 |
| Example 6 | BFS | 41 | 2,307 | 5,650 | 129 | 0 | 0.013525 |
| Example 6 | BFS + deadlock | 41 | 1,128 | 2,780 | 69 | 54 | 0.006823 |
| Example 6 | A* (h3) | 41 | 2,182 | 5,321 | 204 | 0 | 0.041426 |
| Example 6 | A* (h3) + deadlock | 41 | 1,000 | 2,459 | 120 | 54 | 0.018552 |
| Example 7 | BFS | 55 | 54,726 | 146,035 | 2,798 | 0 | 0.415942 |
| Example 7 | BFS + deadlock | 55 | 6,432 | 16,983 | 302 | 829 | 0.045512 |
| Example 7 | A* (h3) | 55 | 49,972 | 133,404 | 3,704 | 0 | 1.359884 |
| Example 7 | A* (h3) + deadlock | 55 | 5,718 | 15,186 | 444 | 790 | 0.136705 |

### Analysis of search improvements
- **Iterations saved:** Deadlock pruning cuts expanded states dramatically across almost all levels:
  - On Example 7, iterations fall from **49,972 down to 5,718** (an 88.6% reduction).
  - On Example 5, iterations fall from **18,247 down to 9,537** (a 47.7% reduction).
  - On Example 6, iterations fall from **2,182 down to 1,000** (a 54.2% reduction).
  - On Example 2, iterations fall from **353 down to 135** (a 61.8% reduction).
- **When pruning does not help:** On Example 1, the shortest solution (cost 4) pushes the box directly to the target without ever pushing any box towards a wall or corner. Hence, 0 nodes are pruned and iterations remain unchanged (5 nodes).
- **Memory footprint:** Maximum frontier size drops substantially (e.g. from 13,163 to 6,499 on Example 5, and from 3,704 to 444 on Example 7).
- **Optimality:** Optimal solution cost is strictly preserved on all levels (verified against BFS).
- **Runtime overhead:** The per-transition lookup cost `pushed_box in deadlocks` is $O(1)$ and negligible compared to state hashing and heap maintenance, delivering net wall-clock speedups of up to **10×** (e.g. 1.36s to 0.136s on Example 7).
