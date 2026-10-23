"""Run the registered search algorithms and write a Markdown report."""

from pathlib import Path
from typing import Iterable

from .search import SOLVERS, SearchResult
from .sokoban_puzzle import SokobanPuzzle

LEVEL_DIR = Path(__file__).parent / "levels"
EXPANSION_CAP = 500_000


def benchmark_all(output_path: str | Path | None = None,
                  algorithms: Iterable[str] | None = None) -> str:
    """Benchmark every selected solver on all bundled levels and save a table.

    The expansion cap limits memory and runtime. Capped runs are reported as
    ``limit`` rather than being presented as failed or completed searches.
    Returns the generated Markdown table.
    """
    keys = list(algorithms) if algorithms is not None else list(SOLVERS)
    rows: list[str] = []
    for level_number in range(1, 6):
        state = SokobanPuzzle.from_file(LEVEL_DIR / f"level{level_number}.txt")
        for key in keys:
            try:
                result: SearchResult = SOLVERS[key](state, max_expanded=EXPANSION_CAP)
                cost = "limit" if result.incomplete else (
                    "—" if result.cost is None else str(result.cost)
                )
                rows.append(
                    f"| Example {level_number} | {key} | {cost} | {result.expanded} | "
                    f"{result.generated} | {result.max_frontier} | {result.elapsed_seconds:.6f} |"
                )
            except Exception as error:
                rows.append(
                    f"| Example {level_number} | {key} | error: {type(error).__name__} | — | — | — | — |"
                )
    table = "\n".join([
        "| Level | Algorithm | Solution cost | Expanded | Generated | Max frontier | Time (s) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        *rows,
    ])
    report = (
        "# Sokoban Search Benchmark\n\n"
        f"Expansion safety cap: {EXPANSION_CAP} nodes per run. `limit` means the cap "
        "was reached before the frontier was exhausted; it is not a completed result.\n\n"
        + table + "\n"
    )
    destination = Path(output_path) if output_path is not None else Path(__file__).parents[1] / "results.md"
    destination.write_text(report, encoding="utf-8")
    return table


def main() -> None:
    """Run all algorithms and print the generated Markdown table."""
    print(benchmark_all())


if __name__ == "__main__":
    main()
