# Sokoban Puzzle — Part 1

Python 3.10+ implementation of the modeling and BFS parts of the USTHB Visual
Computing project. It uses only the Python standard library and `pygame` for the
graphical interface.

## Run

```sh
pip install pygame
python main.py
```

The GUI supports levels 1–5, Solve, Play/Pause, Step forward/back, Reset, and
speed controls. Keyboard shortcuts are shown in the window: `1`–`5` choose a
level, `S` solves, `Space` plays/pauses, arrows or `N`/`B` step, `R` resets,
and `+`/`-` adjust playback speed. Search runs on a worker thread so the window
continues to respond.

Console mode prints each encoded level and solves all five:

```sh
python main.py --cli
```

Run the test suite with:

```sh
python -m unittest discover -s sokoban/tests -v
```

## Design

`SokobanPuzzle` stores the immutable board layout (walls and targets) once and
shares it among successor states. Each state contains only a player coordinate
and a `frozenset` of box coordinates; its hash and equality support graph search.
The text encoding is `R` player, `O` wall, space floor, `S` target, `B` box,
`.` player on target, and `*` box on target. Ragged input rows are padded with
walls. The loader rejects invalid player and box/target counts.

`Node` contains a state, its parent, its generating action, and unit path cost.
`search.bfs` is graph-search BFS with a FIFO queue, an explored set, a frontier
membership set, and goal testing when a new child is generated. It returns a
`SearchResult` containing the solution node, actions, states, and performance
counters.

To add a search algorithm, implement a function accepting a `SokobanPuzzle` and
returning `SearchResult`, then register it in `SokobanGUI.solvers`. The GUI uses
the same result fields for playback and comparison.

## Bundled levels

The PDF's Figure 4 provides raster drawings rather than text grids or explicit
cell coordinates. The maps in `sokoban/levels/` are careful grid reconstructions
of the depicted walls and objects, but a few cell boundaries are ambiguous at
the source image resolution. Each reconstruction is validated for one player
and equal box/target counts, and is solvable by BFS.

The table below records a local run of the bundled BFS implementation. Time is
machine-dependent; counts are the search's generated successor attempts
(including duplicates) and expanded nodes.

| Level | Solution cost | Expanded | Generated | Search time (s) |
|---|---:|---:|---:|---:|
| Example 1 | 4 | 11 | 35 | 0.0003 |
| Example 2 | 14 | 171 | 548 | 0.0047 |
| Example 3 | 19 | 3,713 | 10,606 | 0.0944 |
| Example 4 | 20 | 3,197 | 10,172 | 0.0998 |
| Example 5 | 20 | 21,090 | 61,394 | 0.6402 |

All five complete quickly with plain BFS on the measured run. Timing values are
rounded from one invocation and will vary across machines.
