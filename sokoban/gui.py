"""Pygame interface for playing and solving Sokoban levels."""

from __future__ import annotations
import queue
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .heuristics import HEURISTICS
from .search import SOLVERS, SearchResult
from .sokoban_puzzle import SokobanPuzzle

Solver = Callable[[SokobanPuzzle], SearchResult]

# Short labels for the solver names shown in the interface.
_SOLVER_SHORT_NAMES: dict[str, str] = {
    "BFS": "BFS", "A* (h1)": "A*h1", "A* (h2)": "A*h2", "A* (h3)": "A*h3",
}


@dataclass(frozen=True)
class UIButton:
    """A button's position and the action it triggers."""

    rect: object
    label: str
    action: str
    selected: bool = False
    primary: bool = False


class SokobanGUI:
    """Sokoban window with solver controls and playback."""

    def __init__(self) -> None:
        """Load the levels and set up the solver controls."""
        self.level_dir = Path(__file__).parent / "levels"
        self.levels = [SokobanPuzzle.from_file(self.level_dir / f"level{i}.txt") for i in range(1, 6)]
        self.level_names = [f"Example {i}" for i in range(1, 6)]
        self.solvers = dict(SOLVERS)
        self.heuristics = dict(HEURISTICS)
        self.selected_algorithm = "BFS"
        self.selected_heuristic = "h1"
        self.results: dict[tuple[int, str], SearchResult] = {}
        self.errors: dict[tuple[int, str], str] = {}
        self.solving_keys: set[tuple[int, str]] = set()
        self._request_generations: dict[tuple[int, str], int] = {}
        self._next_generation = 0
        self.level_index = 0
        self.result_queue: queue.Queue[tuple[int, str, int, SearchResult | None, str | None]] = queue.Queue()
        self.playing = False
        self.step = 0
        self.delay_ms = 450
        self.last_step_time = 0
        self.message = ""  # Status messages apply to every solver.
        self._font_cache: dict[tuple[int, bool], object] = {}
        self._freetype_font_keys: set[tuple[int, bool]] = set()

    def _selected_key(self) -> str:
        """Get the solver selected in the controls."""
        if self.selected_algorithm == "BFS":
            return "BFS"
        return f"A* ({self.selected_heuristic})"

    def _solve_in_background(self, level_index: int, key: str, solver: Solver,
                             state: SokobanPuzzle, generation: int) -> None:
        """Run a solver in the background and queue its result or error."""
        try:
            result = solver(state)
            self.result_queue.put((level_index, key, generation, result, None))
        except Exception as error:
            self.result_queue.put((level_index, key, generation, None,
                                   f"{type(error).__name__}: {error}"))

    def _solve_batch_in_background(
        self,
        batch: list[tuple[int, str, Solver, SokobanPuzzle, int]],
    ) -> None:
        """Run several solvers in order, queuing each result as it finishes.

        Running the batch in sequence makes the solver timings easier to compare.
        """
        for level_index, key, solver, state, generation in batch:
            self._solve_in_background(level_index, key, solver, state, generation)

    def _current_result(self) -> SearchResult | None:
        """Get the latest BFS result for this level."""
        return self.results.get((self.level_index, self._selected_key()))

    def _current_error(self) -> str | None:
        """Get the selected solver's error, if it failed."""
        return self.errors.get((self.level_index, self._selected_key()))

    def _change_level(self, index: int) -> None:
        """Switch levels and reset playback."""
        self.level_index = index
        self.step = 0
        self.playing = False
        self.message = ""  # The message applies to every solver.

    def run(self, initial_level: int = 1) -> None:
        """Start the window's event loop."""
        try:
            import pygame
        except ImportError as error:
            raise RuntimeError("Pygame is required for the GUI. Install it with: pip install pygame") from error
        pygame.init()
        width, height = 1180, 760
        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Sokoban Search Lab")
        clock = pygame.time.Clock()
        # Text rendering picks the best font backend available.
        self._change_level(max(0, min(4, initial_level - 1)))
        running = True
        while running:
            now = pygame.time.get_ticks()
            buttons = self._layout_buttons(pygame, screen.get_width())
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if pygame.K_1 <= event.key <= pygame.K_5:
                        self._change_level(event.key - pygame.K_1)
                    elif event.key == pygame.K_a:
                        self._set_algorithm("A*" if self.selected_algorithm == "BFS" else "BFS")
                    elif event.key == pygame.K_h:
                        self._cycle_heuristic()
                    elif event.key == pygame.K_s:
                        self._start_solve()
                    elif event.key == pygame.K_c:
                        self._start_solve(list(self.solvers))
                    elif event.key == pygame.K_SPACE and self._current_result() and self._current_result().found:
                        self._toggle_play()
                    elif event.key in (pygame.K_RIGHT, pygame.K_n):
                        self._step_forward()
                    elif event.key in (pygame.K_LEFT, pygame.K_b):
                        self.step = max(0, self.step - 1)
                    elif event.key == pygame.K_r:
                        self.step, self.playing = 0, False
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        self.delay_ms = max(60, self.delay_ms - 60)
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                        self.delay_ms = min(1500, self.delay_ms + 60)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in buttons:
                        if button.rect.collidepoint(event.pos):
                            self._activate_button(button.action)
                            break
            while True:
                try:
                    level_index, key, generation, result, error = self.result_queue.get_nowait()
                except queue.Empty:
                    break
                cache_key = (level_index, key)
                if self._request_generations.get(cache_key) != generation:
                    continue
                self.solving_keys.discard(cache_key)
                if error is not None:
                    self.errors[cache_key] = error
                    self.results.pop(cache_key, None)
                elif result is not None:
                    self.results[cache_key] = result
                    self.errors.pop(cache_key, None)
                if level_index == self.level_index and key == self._selected_key():
                    self.step = 0
                    self.playing = False
                    self.message = error or ("Solution found." if result and result.found else "No solution found.")
            result = self._current_result()
            if self.playing and result and result.found and now - self.last_step_time >= self.delay_ms:
                if self.step < len(result.path) - 1:
                    self.step += 1
                    self.last_step_time = now
                else:
                    self.playing = False

            screen.fill((17, 24, 39))
            self._draw_controls(pygame, screen, buttons)
            state = result.path[self.step] if result and result.found else self.levels[self.level_index]
            panel_x = min(810, screen.get_width() - 310)
            self._draw_board(pygame, screen, state, panel_x, screen.get_height())
            self._draw_info(pygame, screen, panel_x, result)
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    def _layout_buttons(self, pygame: object, width: int) -> list[UIButton]:
        """Lay out the controls for the current window size and selection.

        Scale button positions on narrow windows so the controls stay visible.
        """
        ref = 1180
        scale = min(1.0, width / ref) if width < 900 else 1.0

        def sx(x: int) -> int:
            return int(x * scale)

        def sw(w: int) -> int:
            return max(36, int(w * scale))

        buttons = [UIButton(pygame.Rect(sx(18 + index * 86), 67, sw(78), 36),
                            f"LEVEL {index + 1}", f"level:{index}", index == self.level_index)
                   for index in range(5)]
        buttons.extend([
            UIButton(pygame.Rect(sx(540), 67, sw(72), 36), "BFS", "algorithm:BFS",
                     self.selected_algorithm == "BFS"),
            UIButton(pygame.Rect(sx(618), 67, sw(72), 36), "A*", "algorithm:A*",
                     self.selected_algorithm == "A*"),
        ])
        if self.selected_algorithm == "A*":
            for index, name in enumerate(("h1", "h2", "h3")):
                buttons.append(UIButton(pygame.Rect(sx(704 + index * 48), 67, sw(42), 36),
                                        name, f"heuristic:{name}", self.selected_heuristic == name))
        buttons.extend([
            UIButton(pygame.Rect(sx(18), 116, sw(102), 42), "SOLVE  S", "solve", primary=True),
            UIButton(pygame.Rect(sx(128), 116, sw(102), 42),
                     "PAUSE  SPACE" if self.playing else "PLAY  SPACE", "play", self.playing),
            UIButton(pygame.Rect(sx(238), 116, sw(92), 42), "STEP  N", "forward"),
            UIButton(pygame.Rect(sx(338), 116, sw(92), 42), "BACK  B", "back"),
            UIButton(pygame.Rect(sx(438), 116, sw(82), 42), "RESET  R", "reset"),
            UIButton(pygame.Rect(sx(742), 116, sw(116), 42), "COMPARE  C", "compare"),
        ])
        return buttons

    def _activate_button(self, action: str) -> None:
        """Run the action attached to a button."""
        if action.startswith("level:"):
            self._change_level(int(action.split(":", 1)[1]))
        elif action.startswith("algorithm:"):
            self._set_algorithm(action.split(":", 1)[1])
        elif action.startswith("heuristic:"):
            self._set_heuristic(action.split(":", 1)[1])
        elif action == "solve":
            self._start_solve()
        elif action == "compare":
            self._start_solve(list(self.solvers))
        elif action == "play":
            self._toggle_play()
        elif action == "forward":
            self._step_forward()
        elif action == "back":
            self.step = max(0, self.step - 1)
        elif action == "reset":
            self.step, self.playing = 0, False

    def _set_algorithm(self, algorithm: str) -> None:
        """Select BFS or A* and show its saved path."""
        if algorithm not in ("BFS", "A*") or algorithm == self.selected_algorithm:
            return
        self.selected_algorithm = algorithm
        self.step = 0
        self.playing = False

    def _set_heuristic(self, name: str) -> None:
        """Pick an A* heuristic and show its saved path."""
        if name not in self.heuristics or name == self.selected_heuristic:
            return
        self.selected_heuristic = name
        self.step = 0
        self.playing = False

    def _cycle_heuristic(self) -> None:
        """Move to the next heuristic."""
        names = list(self.heuristics)
        next_index = (names.index(self.selected_heuristic) + 1) % len(names)
        self._set_heuristic(names[next_index])

    def _toggle_play(self) -> None:
        """Start or pause playback; restart if the path has ended."""
        result = self._current_result()
        if result is None or not result.found:
            return
        if not self.playing and self.step >= len(result.path) - 1:
            self.step = 0
        self.playing = not self.playing

    def _start_solve(self, keys: list[str] | None = None) -> None:
        """Run the selected solver, or a batch of solvers, in the background.

        A batch runs in sequence in one worker, making the solver timings
        easier to compare. Single-solver requests use the same path.
        """
        level_index = self.level_index
        keys = keys or [self._selected_key()]
        self.message = "Solving..."
        self.step = 0
        self.playing = False
        batch: list[tuple[int, str, Solver, SokobanPuzzle, int]] = []
        for key in keys:
            cache_key = (level_index, key)
            if cache_key in self.solving_keys:
                continue  # avoid duplicate in-flight solve
            solver = self.solvers[key]
            self._next_generation += 1
            generation = self._next_generation
            self._request_generations[cache_key] = generation
            self.solving_keys.add(cache_key)
            self.errors.pop(cache_key, None)
            batch.append((level_index, key, solver, self.levels[level_index], generation))
        if not batch:
            return
        if len(batch) == 1:
            li, k, s, st, g = batch[0]
            worker = threading.Thread(
                target=self._solve_in_background,
                args=(li, k, s, st, g),
                daemon=True,
            )
            worker.start()
        else:
            worker = threading.Thread(
                target=self._solve_batch_in_background,
                args=(batch,),
                daemon=True,
            )
            worker.start()

    def _step_forward(self) -> None:
        """Move playback forward by one state."""
        result = self._current_result()
        if result and result.found:
            self.step = min(len(result.path) - 1, self.step + 1)

    def _draw_controls(self, pygame: object, screen: object,
                       buttons: list[UIButton]) -> None:
        """Draw the title and buttons."""
        width = screen.get_width()
        screen.blit(self._render_text(pygame, "SOKOBAN", 27, (245, 247, 250), bold=True), (24, 15))
        subtitle = f"SEARCH LAB  /  {self._selected_key().upper()}"
        screen.blit(self._render_text(pygame, subtitle, 14, (155, 171, 191)), (27, 46))
        right_label = self._render_text(pygame, "MASTER 1  •  VISUAL COMPUTING", 14, (155, 171, 191))
        screen.blit(right_label, (width - right_label.get_width() - 25, 27))

        for button in buttons:
            x, y, button_width, button_height = button.rect
            is_solving = button.action == "solve" and (
                self.level_index, self._selected_key()
            ) in self.solving_keys
            fill = (50, 115, 96) if button.primary else (
                (49, 77, 110) if button.selected else (34, 45, 63))
            if is_solving:
                fill = (109, 80, 40)
            edge = (84, 174, 145) if button.primary or button.selected else (59, 73, 94)
            pygame.draw.rect(screen, (10, 16, 27), button.rect.move(0, 3), border_radius=9)
            pygame.draw.rect(screen, fill, button.rect, border_radius=9)
            pygame.draw.rect(screen, edge, button.rect, 1, border_radius=9)
            color = (246, 250, 248) if button.primary or button.selected else (202, 211, 222)
            text = self._render_text(pygame, "SOLVING..." if is_solving else button.label, 17, color)
            screen.blit(text, text.get_rect(center=(x + button_width // 2, y + button_height // 2)))
        screen.blit(self._render_text(pygame, "SPEED   −   /   +", 14, (155, 171, 191)), (540, 130))

    def _draw_board(self, pygame: object, screen: object, state: SokobanPuzzle,
                    panel_x: int, screen_height: int) -> None:
        """Draw the board centered and scaled to fit the window."""
        layout = state.layout
        card = pygame.Rect(20, 180, panel_x - 34, screen_height - 200)
        pygame.draw.rect(screen, (10, 16, 27), card.move(0, 5), border_radius=18)
        pygame.draw.rect(screen, (27, 37, 54), card, border_radius=18)
        pygame.draw.rect(screen, (48, 63, 85), card, 1, border_radius=18)
        # Keep the title and legend close to the board.
        screen.blit(self._render_text(pygame, "PUZZLE BOARD", 16, (226, 232, 240), bold=True),
                    (card.x + 22, card.y + 17))
        screen.blit(self._render_text(pygame, "WALL", 13, (152, 166, 184)), (card.x + 22, card.y + 48))
        screen.blit(self._render_text(pygame, "FLOOR", 13, (152, 166, 184)), (card.x + 92, card.y + 48))
        board_rect = pygame.Rect(card.x + 22, card.y + 77, card.width - 44, card.height - 99)
        pygame.draw.rect(screen, (20, 29, 43), board_rect, border_radius=13)
        pygame.draw.rect(screen, (39, 53, 73), board_rect, 1, border_radius=13)
        area_w, area_h = board_rect.width - 32, board_rect.height - 32
        tile = max(12, min(54, area_w // layout.width, area_h // layout.height))
        ox = board_rect.x + (board_rect.width - layout.width * tile) // 2
        oy = board_rect.y + (board_rect.height - layout.height * tile) // 2
        for row in range(layout.height):
            for col in range(layout.width):
                rect = pygame.Rect(ox + col * tile, oy + row * tile, tile - 2, tile - 2)
                pos = (row, col)
                if pos in layout.walls:
                    self._draw_wall_tile(pygame, screen, rect, tile, row, col)
                else:
                    pygame.draw.rect(screen, (220, 207, 180), rect, border_radius=5)
                    pygame.draw.rect(screen, (231, 220, 198), rect, 1, border_radius=5)
                    if pos in layout.targets:
                        pygame.draw.circle(screen, (166, 111, 68), rect.center, max(4, tile // 5), 2)
                        pygame.draw.circle(screen, (166, 111, 68), rect.center, max(2, tile // 13))
                    if pos in state.boxes:
                        self._draw_box(pygame, screen, rect, tile, pos in layout.targets)
                    if pos == state.player:
                        self._draw_player(pygame, screen, rect, tile)

    def _draw_info(self, pygame: object, screen: object,
                   panel_x: int, result: SearchResult | None) -> None:
        """Show details for the selected solver and level."""
        screen_width, screen_height = screen.get_size()
        card = pygame.Rect(panel_x + 14, 180, screen_width - panel_x - 34, screen_height - 200)
        pygame.draw.rect(screen, (10, 16, 27), card.move(0, 5), border_radius=18)
        pygame.draw.rect(screen, (27, 37, 54), card, border_radius=18)
        pygame.draw.rect(screen, (48, 63, 85), card, 1, border_radius=18)
        x, width = card.x + 20, card.width - 40
        y = card.y + 20
        screen.blit(self._render_text(pygame, "SEARCH RESULTS", 16, (226, 232, 240), bold=True), (x, y))
        y += 36
        selected_key = self._selected_key()
        screen.blit(self._render_text(pygame, selected_key.upper(), 13,
                                      (152, 166, 184)), (x, y))
        y += 25

        is_solving = (self.level_index, selected_key) in self.solving_keys
        error = self._current_error()
        if is_solving:
            status, status_color = "SEARCHING", (221, 164, 76)
        elif result and result.found:
            status, status_color = "SOLUTION FOUND", (85, 190, 148)
        elif error:
            status, status_color = "SOLVER ERROR", (226, 112, 104)
        elif result:
            status, status_color = "NO SOLUTION", (226, 112, 104)
        else:
            status, status_color = "READY TO SOLVE", (123, 157, 208)
        pill = pygame.Rect(x, y, min(width, 160), 27)
        status_background = (35, 76, 67) if result and result.found else (
            (77, 60, 38) if is_solving else ((78, 48, 48) if result or error else (39, 57, 82)))
        pygame.draw.rect(screen, status_background, pill, border_radius=13)
        pygame.draw.rect(screen, status_color, pill, 1, border_radius=13)
        screen.blit(self._render_text(pygame, status, 12, status_color, bold=True),
                    (pill.x + 11, pill.y + 6))
        y += 34

        # Put status messages just below the status label.
        if self.message:
            screen.blit(self._render_text(pygame, self.message, 11, (181, 194, 211)), (x, y))
        y += 18

        if error:
            screen.blit(self._render_text(pygame, "Search failed:", 15, (226, 132, 123)), (x, y))
            y += 25
            error_text = error[:34]
            screen.blit(self._render_text(pygame, error_text, 11, (226, 160, 151)), (x, y))
            y += 50
        elif result and result.found:
            screen.blit(self._render_text(pygame, str(result.cost), 42, (245, 247, 250), bold=True), (x, y))
            screen.blit(self._render_text(pygame, "MOVES TO SOLVE", 12, (152, 166, 184)), (x + 4, y + 49))
            y += 82
            current_action = "START" if self.step == 0 else result.actions[self.step - 1]
            action_card = pygame.Rect(x, y, width, 61)
            pygame.draw.rect(screen, (35, 49, 68), action_card, border_radius=11)
            screen.blit(self._render_text(pygame, "CURRENT ACTION", 11, (152, 166, 184)),
                        (action_card.x + 12, action_card.y + 9))
            screen.blit(self._render_text(pygame, current_action, 17, (245, 247, 250), bold=True),
                        (action_card.x + 12, action_card.y + 29))
            y += 75
            progress_width = max(0, int(width * self.step / max(1, len(result.actions))))
            pygame.draw.rect(screen, (50, 65, 86), (x, y + 12, width, 6), border_radius=3)
            if progress_width:
                pygame.draw.rect(screen, (85, 190, 148), (x, y + 12, progress_width, 6), border_radius=3)
            screen.blit(self._render_text(pygame, f"STEP  {self.step} / {len(result.actions)}", 12,
                                          (181, 194, 211)), (x, y + 26))
            y += 56
            metrics = [("EXPANDED", f"{result.expanded:,}"),
                       ("GENERATED", f"{result.generated:,}"),
                       ("MAX FRONTIER", f"{result.max_frontier:,}"),
                       ("SEARCH TIME", f"{result.elapsed_seconds:.4f}s")]
            self._draw_metric_grid(pygame, screen, x, y, width, metrics)
            y += 108
        elif result:
            screen.blit(self._render_text(pygame, "No solution found", 17, (226, 132, 123)), (x, y))
            y += 36
            metrics = [("EXPANDED", f"{result.expanded:,}"), ("GENERATED", f"{result.generated:,}"),
                       ("MAX FRONTIER", f"{result.max_frontier:,}"),
                       ("SEARCH TIME", f"{result.elapsed_seconds:.4f}s")]
            self._draw_metric_grid(pygame, screen, x, y, width, metrics)
            y += 108
        elif result is None:
            screen.blit(self._render_text(pygame, "Choose a search strategy", 18,
                                          (220, 228, 238), bold=True), (x, y))
            y += 30
            screen.blit(self._render_text(pygame, "Press S to solve with", 13,
                                          (152, 166, 184)), (x, y))
            y += 29
            screen.blit(self._render_text(pygame, selected_key, 17,
                                          (85, 190, 148), bold=True), (x, y))
            y += 29
            screen.blit(self._render_text(pygame, "A toggles BFS / A*; H changes h1–h3.", 11,
                                          (152, 166, 184)), (x, y))
            y += 20
            screen.blit(self._render_text(pygame, "C compares all registered solvers.", 11,
                                          (152, 166, 184)), (x, y))
            y += 51

        level_results = [
            (key, item) for (level, key), item in self.results.items()
            if level == self.level_index
        ]
        if len(level_results) > 1:
            screen.blit(self._render_text(pygame, "ALGORITHM COMPARISON", 12,
                                          (226, 232, 240), bold=True), (x, y))
            y += 22
            # Fixed offsets keep the columns lined up with proportional fonts.
            col_offsets = (0, 45, 95, 145, 195, 245)
            for label, offset in zip(("ALG", "COST", "EXP", "GEN", "OPEN", "TIME"), col_offsets):
                screen.blit(self._render_text(pygame, label, 9, (143, 161, 183)), (x + offset, y))
            y += 17
            minimum_cost = min((item.cost for _, item in level_results
                                if item.found and item.cost is not None), default=None)
            for key, item in sorted(level_results, key=lambda entry: entry[0]):
                active = key == selected_key
                row = pygame.Rect(x - 5, y - 2, width + 10, 20)
                if active:
                    pygame.draw.rect(screen, (45, 63, 85), row, border_radius=5)
                # Use the short label defined above.
                short_name = _SOLVER_SHORT_NAMES.get(key, key[:6])
                if item.incomplete:
                    cost_label, marker = "LIMIT", ""
                elif not item.found:
                    cost_label, marker = "—", ""
                else:
                    cost_label = str(item.cost)
                    marker = "*" if item.cost == minimum_cost else (
                        "!" if minimum_cost is not None and item.cost > minimum_cost else "")
                row_color = (245, 247, 250) if active else (181, 194, 211)
                cells = (short_name, f"{cost_label}{marker}",
                         str(item.expanded), str(item.generated),
                         str(item.max_frontier), f"{item.elapsed_seconds:.3f}")
                for cell, offset in zip(cells, col_offsets):
                    screen.blit(self._render_text(pygame, cell, 9, row_color), (x + offset, y))
                y += 21
            screen.blit(self._render_text(pygame, "* best cost   ! higher than best", 9,
                                          (143, 161, 183)), (x, y + 2))
        screen.blit(self._render_text(pygame, "SPACE  play / pause     R  reset", 11,
                                      (120, 139, 162)), (x, card.bottom - 28))

    def _render_text(self, pygame: object, text: str, size: int,
                     color: tuple[int, int, int], bold: bool = False) -> object:
        """Draw text using whichever font backend is available.

        Try freetype first, then fall back to pygame's regular font module.
        """
        font_key = (size, bold)
        if font_key not in self._font_cache:
            use_freetype = (sys.version_info >= (3, 14)
                            and pygame.version.vernum <= (2, 6, 1))
            if use_freetype:
                import pygame._freetype as freetype

                freetype.init()
                cached_font = freetype.Font(None, size)
                cached_font.strong = bold
                self._font_cache[font_key] = cached_font
                self._freetype_font_keys.add(font_key)
            else:
                try:
                    self._font_cache[font_key] = pygame.font.SysFont("arial", size, bold=bold)
                except (ImportError, NotImplementedError):
                    import pygame._freetype as freetype

                    freetype.init()
                    cached_font = freetype.Font(None, size)
                    cached_font.strong = bold
                    self._font_cache[font_key] = cached_font
                    self._freetype_font_keys.add(font_key)
        font = self._font_cache[font_key]
        if font_key in self._freetype_font_keys:
            return font.render(text, color)[0]
        return font.render(text, True, color)

    def _draw_metric_grid(self, pygame: object, screen: object,
                          x: int, y: int, width: int,
                          metrics: list[tuple[str, str]]) -> None:
        """Draw the small statistic cards."""
        gap, card_height = 8, 43
        card_width = (width - gap) // 2
        for index, (label, value) in enumerate(metrics):
            col, row = index % 2, index // 2
            rect = pygame.Rect(x + col * (card_width + gap), y + row * (card_height + gap),
                               card_width, card_height)
            pygame.draw.rect(screen, (35, 49, 68), rect, border_radius=9)
            screen.blit(self._render_text(pygame, label, 9, (143, 161, 183)),
                        (rect.x + 9, rect.y + 6))
            screen.blit(self._render_text(pygame, value, 14, (232, 237, 244), bold=True),
                        (rect.x + 9, rect.y + 21))

    @staticmethod
    def _draw_wall_tile(pygame: object, screen: object, rect: object, tile: int,
                        row: int, col: int) -> None:
        """Draw a brick wall tile."""
        base = (90, 105, 120) if (row + col) % 2 else (82, 97, 113)
        pygame.draw.rect(screen, base, rect, border_radius=4)
        pygame.draw.rect(screen, (123, 139, 153), rect, 1, border_radius=4)
        joint = (55, 69, 84)
        pygame.draw.line(screen, joint, (rect.left + 3, rect.centery),
                         (rect.right - 3, rect.centery), max(1, tile // 18))
        offset = tile // 2 if row % 2 else 0
        seam_x = rect.left + offset
        if rect.left + 3 < seam_x < rect.right - 3:
            pygame.draw.line(screen, joint, (seam_x, rect.top + 2),
                             (seam_x, rect.centery - 1), max(1, tile // 18))
        seam_x = rect.left + (tile // 2 - offset)
        if rect.left + 3 < seam_x < rect.right - 3:
            pygame.draw.line(screen, joint, (seam_x, rect.centery + 1),
                             (seam_x, rect.bottom - 2), max(1, tile // 18))

    @staticmethod
    def _draw_box(pygame: object, screen: object, rect: object, tile: int,
                  on_target: bool) -> None:
        """Draw a crate with panel lines and a shadow."""
        box_rect = rect.inflate(-tile // 5, -tile // 5)
        shadow = box_rect.move(2, 3)
        pygame.draw.rect(screen, (71, 55, 43), shadow, border_radius=6)
        color = (223, 174, 67) if on_target else (153, 91, 53)
        edge = (255, 218, 119) if on_target else (198, 132, 83)
        pygame.draw.rect(screen, color, box_rect, border_radius=6)
        pygame.draw.rect(screen, edge, box_rect, max(1, tile // 18), border_radius=6)
        inset = box_rect.inflate(-max(6, tile // 4), -max(6, tile // 4))
        pygame.draw.rect(screen, edge, inset, max(1, tile // 15), border_radius=3)

    @staticmethod
    def _draw_player(pygame: object, screen: object, rect: object, tile: int) -> None:
        """Draw the player."""
        center_x, center_y = rect.centerx, rect.centery
        pygame.draw.ellipse(screen, (42, 53, 65),
                            (center_x - tile // 4, center_y + tile // 5,
                             tile // 2, max(4, tile // 5)))
        body = pygame.Rect(center_x - tile // 4, center_y - tile // 8,
                           tile // 2, tile // 2)
        pygame.draw.rect(screen, (57, 139, 173), body, border_radius=max(4, tile // 5))
        pygame.draw.rect(screen, (117, 198, 215), body, 1, border_radius=max(4, tile // 5))
        head_center = (center_x, center_y - tile // 5)
        pygame.draw.circle(screen, (237, 190, 143), head_center, max(4, tile // 5))
        pygame.draw.circle(screen, (255, 224, 181),
                           (head_center[0] - tile // 18, head_center[1] - tile // 18), max(2, tile // 7))
        eye_y = head_center[1]
        pygame.draw.circle(screen, (48, 53, 61), (center_x - tile // 14, eye_y), max(1, tile // 28))
        pygame.draw.circle(screen, (48, 53, 61), (center_x + tile // 14, eye_y), max(1, tile // 28))
