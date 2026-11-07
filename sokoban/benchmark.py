"""Run the solvers and save their results as a Markdown table."""

from pathlib import Path
from typing import Iterable

from .search import SOLVERS, SearchResult
from .sokoban_puzzle import SokobanPuzzle

LEVEL_DIR = Path(__file__).parent / "levels"
EXPANSION_CAP = 500_000
ACTION_MAP = {"UP": "U", "DOWN": "D", "LEFT": "L", "RIGHT": "R"}


def benchmark_all(
    output_path: str | Path | None = None,
    algorithms: Iterable[str] | None = None,
) -> str:
    """Run each selected solver on the bundled levels and save a table.

    Runs that hit the expansion cap are marked ``limit``. Returns the table.
    """
    keys = list(algorithms) if algorithms is not None else list(SOLVERS)
    rows: list[str] = []
    level_solutions: dict[int, dict[str, tuple[int | None, int, str]]] = {6: {}, 7: {}}

    for level_number in range(1, 8):
        state = SokobanPuzzle.from_file(LEVEL_DIR / f"level{level_number}.txt")
        for key in keys:
            try:
                results = [
                    SOLVERS[key](state, max_expanded=EXPANSION_CAP)
                    for _ in range(3)
                ]
                representative = results[0]
                median_time = sorted(r.elapsed_seconds for r in results)[1]
                cost = (
                    "limit"
                    if representative.incomplete
                    else (
                        "—"
                        if representative.cost is None
                        else str(representative.cost)
                    )
                )
                pruned = getattr(representative, "pruned", 0)
                level_label = f"Fig 7 Ex {level_number - 5}" if level_number > 5 else f"Example {level_number}"
                rows.append(
                    f"| {level_label} | {key} | {cost} | {representative.expanded} | "
                    f"{representative.generated} | {representative.max_frontier} | {pruned} | {median_time:.6f} |"
                )
                if level_number in level_solutions and representative.found:
                    move_seq = " ".join(
                        ACTION_MAP.get(a, a) for a in representative.actions
                    )
                    level_solutions[level_number][key] = (
                        representative.cost,
                        representative.expanded,
                        move_seq,
                    )
            except Exception as error:
                rows.append(
                    f"| Example {level_number} | {key} | error: {type(error).__name__}: {error} | — | — | — | — | — |"
                )

    table = "\n".join([
        "| Level | Algorithm | Solution cost | Expanded | Generated | Max frontier | Pruned | Time (s) |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows,
    ])

    solutions_md = ["## Solutions for Figure 7 Examples\n"]
    for lvl in (6, 7):
        lvl_name = f"Fig 7 Ex {lvl - 5}"
        solutions_md.append(f"### {lvl_name}")
        for key, (cost, iters, moves) in level_solutions[lvl].items():
            solutions_md.append(
                f"- **{key}** (cost={cost}, iterations={iters}):\n  `{moves}`"
            )
        solutions_md.append("")

    report = (
        "# Sokoban Search Benchmark — Part 3 Results\n\n"
        f"Expansion safety cap: {EXPANSION_CAP} nodes per run. `limit` means the cap "
        "was reached before the frontier was exhausted; it is not a completed result.\n\n"
        + table
        + "\n\n"
        + "\n".join(solutions_md)
        + "\n"
    )

    dest_p3 = (
        Path(output_path)
        if output_path is not None
        else Path(__file__).parents[1] / "results_part3.md"
    )
    dest_p3.write_text(report, encoding="utf-8")

    # Also update results.md for convenience
    dest_p2 = Path(__file__).parents[1] / "results.md"
    dest_p2.write_text(report, encoding="utf-8")

    return table


def main() -> None:
    """Run the benchmarks and print the table."""
    print(benchmark_all())


if __name__ == "__main__":
    main()
