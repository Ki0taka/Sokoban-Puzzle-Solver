"""Run the solvers and save their results as a Markdown table."""

from pathlib import Path
from typing import Iterable

from .search import SOLVERS, SearchResult
from .sokoban_puzzle import SokobanPuzzle

LEVEL_DIR = Path(__file__).parent / "levels"
EXPANSION_CAP = 500_000


def benchmark_all(output_path: str | Path | None = None,
                  algorithms: Iterable[str] | None = None) -> str:
    """Run each selected solver on the bundled levels and save a table.

    Runs that hit the expansion cap are marked ``limit``. Returns the table.
    """
    keys = list(algorithms) if algorithms is not None else list(SOLVERS)
    rows: list[str] = []
    for level_number in range(1, 6):
        state = SokobanPuzzle.from_file(LEVEL_DIR / f"level{level_number}.txt")
        for key in keys:
            try:
                results = [SOLVERS[key](state, max_expanded=EXPANSION_CAP) for _ in range(3)]
                representative = results[0]
                median_time = sorted(r.elapsed_seconds for r in results)[1]
                cost = "limit" if representative.incomplete else (
                    "—" if representative.cost is None else str(representative.cost)
                )
                rows.append(
                    f"| Example {level_number} | {key} | {cost} | {representative.expanded} | "
                    f"{representative.generated} | {representative.max_frontier} | {median_time:.6f} |"
                )
            except Exception as error:
                rows.append(
                    f"| Example {level_number} | {key} | error: {type(error).__name__}: {error} | — | — | — | — |"
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
    """Run the benchmarks and print the table."""
    print(benchmark_all())


if __name__ == "__main__":
    main()
