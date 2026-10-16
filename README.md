# Sokoban Puzzle Solver

A Python implementation of the Sokoban modeling and search project for the
USTHB Master 1 Visual Computing course. It includes a validated puzzle model,
an optimal Breadth-First Search (BFS) solver, five example levels, and a Pygame
interface for viewing solutions step by step.

> **Requirements:** Python 3.10 or later. The graphical interface requires
> Pygame; the puzzle model, BFS solver, and CLI use only the standard library.

## Features

- Immutable, hashable puzzle states with shared static board layouts.
- Legal movement and box-pushing rules, including player and box target cells.
- Graph-search BFS with path reconstruction and search statistics.
- Responsive Pygame UI with background solving and solution playback.
- Five text-based example levels and automated tests.
- Solver registry designed to support future algorithms such as DFS, UCS, and A*.

## Quick start

Clone the repository, enter its directory, then install Pygame and launch the
interface:

```bash
python -m pip install pygame
python main.py
```

Select a level with the on-screen buttons or keys `1`–`5`, then choose **Solve**.
The interface shows the board, solution path, current action, cost, and BFS
statistics.

### Controls

| Input | Action |
| --- | --- |
| `1`–`5` | Select a level |
| `S` | Solve with BFS |
| `Space` | Play or pause the solution animation |
| `→` / `N` | Step forward |
| `←` / `B` | Step backward |
| `R` | Reset playback |
| `+` / `-` | Increase or decrease playback speed |

## Console mode

Print and solve all five levels without opening the GUI:

```bash
python main.py --cli
```

Choose the level shown when the GUI starts:

```bash
python main.py --level 3
```

## Tests

Run the unit tests from the project root:

```bash
python -m unittest discover -s sokoban/tests -v
```

The tests cover parsing and rendering, goal recognition, movement and push
constraints, state hashing, node path reconstruction, BFS optimality on a small
board, and independent replay of the solutions for all bundled levels.

## Project structure

```text
main.py                      Application entry point
sokoban/
  sokoban_puzzle.py           Puzzle state, validation, and transitions
  node.py                     Search-tree node and path reconstruction
  search.py                   BFS and SearchResult
  gui.py                      Pygame interface and animation
  main.py                     CLI and GUI launcher
  levels/                     Five text-based example levels
  tests/                      Unit and solver tests
PROJECT_WALKTHROUGH.md        Detailed implementation guide
```

## Design overview

`SokobanPuzzle` separates the immutable layout (walls and targets) from the
dynamic state (player position and a `frozenset` of box positions). Successors
share the same layout, create new dynamic states, and can be stored in sets for
graph search.

BFS uses a FIFO queue, an explored set, and a set for fast frontier membership
checks. Since each action costs one move, BFS returns a shortest solution. The
`SearchResult` reports the solution node, actions, state path, cost, expanded
and generated node counts, maximum frontier size, and elapsed time.

To add a solver, implement a function accepting a `SokobanPuzzle` and returning
a `SearchResult`, then register it in `SokobanGUI.solvers`. The existing model
and GUI are shared across algorithms.

## BFS results

These are one local run of the bundled levels. Node counts follow this
implementation's convention: generated includes duplicate successor attempts.
Search times vary by machine.

| Level | Solution cost | Expanded | Generated | Time (seconds) |
| --- | ---: | ---: | ---: | ---: |
| Example 1 | 4 | 11 | 35 | 0.0003 |
| Example 2 | 14 | 171 | 548 | 0.0047 |
| Example 3 | 19 | 3,713 | 10,606 | 0.0944 |
| Example 4 | 20 | 3,197 | 10,172 | 0.0998 |
| Example 5 | 20 | 21,090 | 61,394 | 0.6402 |

## Example levels

The five supplied examples are based on Figure 4 of the course project PDF.
That figure is a raster drawing without explicit grid coordinates, so the text
maps are careful reconstructions and some cell boundaries are necessarily
estimated. The loader checks that each map has exactly one player and equal
numbers of boxes and targets; the test suite confirms that every bundled map
has a BFS solution.
