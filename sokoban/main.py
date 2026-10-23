"""Command-line and graphical entry point for Sokoban."""

import argparse
from pathlib import Path
from .benchmark import benchmark_all
from .search import SOLVERS
from .sokoban_puzzle import SokobanPuzzle

LEVEL_DIR = Path(__file__).parent / "levels"


def main() -> None:
    """Parse options and launch the CLI or pygame interface."""
    parser = argparse.ArgumentParser(description="Solve and animate Sokoban levels")
    parser.add_argument("--cli", action="store_true", help="solve all bundled levels in the console")
    parser.add_argument("--benchmark", action="store_true", help="benchmark all registered solvers and write results.md")
    parser.add_argument("--algorithm", action="append", choices=tuple(SOLVERS),
                        help="solver to use in CLI mode (repeat to compare; defaults to all)")
    parser.add_argument("--level", type=int, default=1, choices=range(1, 6), help="level number")
    args = parser.parse_args()
    if args.benchmark:
        print(benchmark_all())
        return
    if args.cli:
        algorithms = args.algorithm or list(SOLVERS)
        for number in range(1, 6):
            path = LEVEL_DIR / f"level{number}.txt"
            state = SokobanPuzzle.from_file(path)
            print(f"\nLevel {number}:\n{state}")
            for name in algorithms:
                result = SOLVERS[name](state)
                print(f"{name}: cost={result.cost}, expanded={result.expanded}, "
                      f"generated={result.generated}, max_frontier={result.max_frontier}, "
                      f"time={result.elapsed_seconds:.4f}s")
                if result.found:
                    print("solution:", " ".join(result.actions))
                else:
                    print("No solution found")
        return
    from .gui import SokobanGUI
    SokobanGUI().run(args.level)


if __name__ == "__main__":
    main()
