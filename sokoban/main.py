"""Command-line and graphical entry point for Sokoban."""

import argparse
from pathlib import Path
from .search import bfs
from .sokoban_puzzle import SokobanPuzzle

LEVEL_DIR = Path(__file__).parent / "levels"


def main() -> None:
    """Parse options and launch the CLI or pygame interface."""
    parser = argparse.ArgumentParser(description="Solve and animate Sokoban levels")
    parser.add_argument("--cli", action="store_true", help="solve all bundled levels in the console")
    parser.add_argument("--level", type=int, default=1, choices=range(1, 6), help="level number")
    args = parser.parse_args()
    if args.cli:
        for number in range(1, 6):
            path = LEVEL_DIR / f"level{number}.txt"
            state = SokobanPuzzle.from_file(path)
            print(f"\nLevel {number}:\n{state}")
            result = bfs(state)
            print(f"cost={result.cost}, expanded={result.expanded}, generated={result.generated}, "
                  f"max_frontier={result.max_frontier}, time={result.elapsed_seconds:.4f}s")
            if result.found:
                print("solution:", " ".join(result.actions))
            else:
                print("No solution found")
        return
    from .gui import SokobanGUI
    SokobanGUI().run(args.level)


if __name__ == "__main__":
    main()
