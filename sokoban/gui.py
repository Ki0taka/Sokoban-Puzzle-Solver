"""Pygame interface for choosing, solving, and animating Sokoban levels."""

from __future__ import annotations
import queue
import sys
import threading
from pathlib import Path
from typing import Callable

from .search import SearchResult, bfs
from .sokoban_puzzle import SokobanPuzzle

Solver = Callable[[SokobanPuzzle], SearchResult]


class _FreeTypeFontAdapter:
    """Give Pygame's freetype renderer the small font API used by this GUI."""

    def __init__(self, freetype: object, size: int) -> None:
        """Create a freetype font using its bundled default face."""
        self._font = freetype.Font(None, size)

    def render(self, text: str, antialias: bool, color: tuple[int, int, int]) -> object:
        """Render text and return only the surface, matching pygame.font.Font."""
        surface, _ = self._font.render(text, color)
        return surface


class SokobanGUI:
    """Responsive board viewer with background solver execution and playback."""

    def __init__(self) -> None:
        """Prepare level data and a registry for search algorithms."""
        self.level_dir = Path(__file__).parent / "levels"
        self.levels = [SokobanPuzzle.from_file(self.level_dir / f"level{i}.txt") for i in range(1, 6)]
        self.level_names = [f"Example {i}" for i in range(1, 6)]
        self.solvers: dict[str, Solver] = {"BFS": bfs}
        self.results: dict[str, SearchResult] = {}
        self.level_index = 0
        self.result_queue: queue.Queue[tuple[str, SearchResult, int]] = queue.Queue()
        self._solve_generation = 0
        self.solving = False
        self.playing = False
        self.step = 0
        self.delay_ms = 450
        self.last_step_time = 0
        self.message = "Select Solve to run BFS."

    def _solve_in_background(self, name: str, solver: Solver, state: SokobanPuzzle,
                             generation: int) -> None:
        """Run a solver away from pygame's event thread and post its result."""
        self.result_queue.put((name, solver(state), generation))

    def _current_result(self) -> SearchResult | None:
        """Return the latest BFS result for the selected level."""
        return self.results.get("BFS")

    def _change_level(self, index: int) -> None:
        """Select a level and clear playback state."""
        self.level_index = index
        self.results.clear()
        self.step = 0
        self.playing = False
        self.solving = False
        self._solve_generation += 1
        self.message = "Select Solve to run BFS."

    def run(self, initial_level: int = 1) -> None:
        """Start the pygame event loop; requires pygame to be installed."""
        try:
            import pygame
        except ImportError as error:
            raise RuntimeError("Pygame is required for the GUI. Install it with: pip install pygame") from error
        pygame.init()
        width, height = 1180, 760
        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Sokoban — Problem Solving")
        clock = pygame.time.Clock()
        font, small = self._create_fonts(pygame)
        self._change_level(max(0, min(4, initial_level - 1)))
        running = True
        while running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if pygame.K_1 <= event.key <= pygame.K_5:
                        self._change_level(event.key - pygame.K_1)
                    elif event.key == pygame.K_s and not self.solving:
                        self._start_solve()
                    elif event.key == pygame.K_SPACE and self._current_result() and self._current_result().found:
                        self.playing = not self.playing
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
                    mx, my = event.pos
                    if my < 54 and 18 <= mx < 18 + 5 * 86:
                        self._change_level(min(4, (mx - 18) // 86))
                    elif my < 105:
                        if 18 <= mx < 120 and not self.solving:
                            self._start_solve()
                        elif 128 <= mx < 230:
                            self.playing = not self.playing
                        elif 238 <= mx < 330:
                            self._step_forward()
                        elif 338 <= mx < 430:
                            self.step = max(0, self.step - 1)
                        elif 438 <= mx < 520:
                            self.step, self.playing = 0, False
            while not self.result_queue.empty():
                name, result, generation = self.result_queue.get()
                if generation != self._solve_generation:
                    continue
                self.results[name] = result
                self.solving = False
                self.step = 0
                self.message = "Solution found." if result.found else "No solution found for this level."
            result = self._current_result()
            if self.playing and result and result.found and now - self.last_step_time >= self.delay_ms:
                if self.step < len(result.path) - 1:
                    self.step += 1
                    self.last_step_time = now
                else:
                    self.playing = False

            screen.fill((242, 239, 229))
            self._draw_controls(pygame, screen, font, small)
            state = result.path[self.step] if result and result.found else self.levels[self.level_index]
            panel_x = min(810, screen.get_width() - 310)
            self._draw_board(pygame, screen, state, panel_x, screen.get_height())
            self._draw_info(pygame, screen, font, small, panel_x, result)
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    @staticmethod
    def _create_fonts(pygame: object) -> tuple[object, object]:
        """Create GUI fonts, falling back to freetype if pygame.font is unavailable."""
        # Pygame 2.6.1 has a pygame.font/sysfont circular import under Python 3.14.
        if sys.version_info >= (3, 14) and pygame.version.vernum <= (2, 6, 1):
            import pygame._freetype as freetype

            freetype.init()
            return _FreeTypeFontAdapter(freetype, 18), _FreeTypeFontAdapter(freetype, 15)
        try:
            pygame_font = pygame.font
            pygame_font.init()
            return pygame_font.SysFont("arial", 18), pygame_font.SysFont("arial", 15)
        except (ImportError, NotImplementedError):
            # Pygame 2.6.1's pygame.font module can fail to import on Python 3.14
            # because pygame.sysfont imports Font before pygame.font defines it.
            import pygame._freetype as freetype

            freetype.init()
            return _FreeTypeFontAdapter(freetype, 18), _FreeTypeFontAdapter(freetype, 15)

    def _start_solve(self) -> None:
        """Launch each registered solver in a worker thread."""
        self.solving = True
        self.results.clear()
        self.message = "Solving..."
        self._solve_generation += 1
        generation = self._solve_generation
        for name, solver in self.solvers.items():
            worker = threading.Thread(target=self._solve_in_background,
                                      args=(name, solver, self.levels[self.level_index], generation), daemon=True)
            worker.start()

    def _step_forward(self) -> None:
        """Advance one state when a solution is available."""
        result = self._current_result()
        if result and result.found:
            self.step = min(len(result.path) - 1, self.step + 1)

    @staticmethod
    def _draw_controls(pygame: object, screen: object, font: object, small: object) -> None:
        """Draw level and playback controls with their shortcuts."""
        def button(rect: tuple[int, int, int, int], label: str, active: bool = False) -> None:
            pygame.draw.rect(screen, (75, 107, 92) if active else (205, 198, 179), rect, border_radius=5)
            text = font.render(label, True, (255, 255, 255) if active else (38, 43, 39))
            screen.blit(text, text.get_rect(center=(rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)))
        for i in range(5):
            button((18 + i * 86, 12, 78, 34), f"Level {i+1}")
        for rect, label in [((18, 60, 102, 36), "Solve (S)"), ((128, 60, 102, 36), "Play (Space)"),
                            ((238, 60, 92, 36), "Step (→)"), ((338, 60, 92, 36), "Back (←)"),
                            ((438, 60, 82, 36), "Reset (R)")]:
            button(rect, label)
        screen.blit(small.render("Speed: + / -", True, (70, 75, 72)), (540, 70))

    def _draw_board(self, pygame: object, screen: object, state: SokobanPuzzle,
                    panel_x: int, screen_height: int) -> None:
        """Draw a centered, fit-to-window board using primitive shapes."""
        layout = state.layout
        area_w, area_h = max(250, panel_x - 42), max(250, screen_height - 145)
        tile = max(12, min(52, area_w // layout.width, area_h // layout.height))
        ox = max(18, (panel_x - layout.width * tile) // 2)
        oy = 125 + max(0, (area_h - layout.height * tile) // 2)
        for row in range(layout.height):
            for col in range(layout.width):
                rect = pygame.Rect(ox + col * tile, oy + row * tile, tile, tile)
                pos = (row, col)
                if pos in layout.walls:
                    pygame.draw.rect(screen, (125, 128, 125), rect)
                    pygame.draw.rect(screen, (79, 81, 79), rect, 1)
                    pygame.draw.line(screen, (164, 166, 161), (rect.left + 2, rect.top + tile // 2),
                                     (rect.right - 2, rect.top + tile // 2), max(1, tile // 15))
                    if row % 2 == 0:
                        pygame.draw.line(screen, (164, 166, 161), (rect.left + tile // 2, rect.top + 1),
                                         (rect.left + tile // 2, rect.top + tile // 2), max(1, tile // 15))
                else:
                    pygame.draw.rect(screen, (238, 218, 181), rect)
                    pygame.draw.rect(screen, (248, 236, 211), rect, 1)
                    if pos in layout.targets:
                        pygame.draw.circle(screen, (184, 131, 80), rect.center, max(3, tile // 7), max(1, tile // 14))
                    if pos in state.boxes:
                        color = (239, 194, 69) if pos in layout.targets else (139, 80, 42)
                        box_rect = rect.inflate(-tile // 5, -tile // 5)
                        pygame.draw.rect(screen, color, box_rect, border_radius=3)
                        pygame.draw.rect(screen, (78, 49, 31), box_rect, max(1, tile // 18), border_radius=3)
                        pygame.draw.line(screen, (93, 58, 34), box_rect.topleft, box_rect.bottomright, max(1, tile // 18))
                    if pos == state.player:
                        radius = max(5, tile // 3)
                        pygame.draw.circle(screen, (54, 130, 171), (rect.centerx, rect.centery + tile // 7), radius)
                        pygame.draw.circle(screen, (245, 207, 148), (rect.centerx, rect.centery - tile // 5), max(4, tile // 5))

    def _draw_info(self, pygame: object, screen: object, font: object, small: object,
                   panel_x: int, result: SearchResult | None) -> None:
        """Show solver statistics, playback state, and algorithm comparison."""
        x, y = max(650, panel_x + 20), 132
        rows = [f"Algorithm: {', '.join(self.solvers)}", f"Level: {self.level_names[self.level_index]}", self.message]
        if result:
            if result.found:
                current_action = "Start" if self.step == 0 else result.actions[self.step - 1]
                rows += [f"Solution cost: {result.cost}", f"Actions: {len(result.actions)}",
                         f"Nodes expanded: {result.expanded}", f"Nodes generated: {result.generated}",
                         f"Max frontier: {result.max_frontier}", f"Search time: {result.elapsed_seconds:.6f}s",
                         f"Step: {self.step} / {len(result.actions)}", f"Current action: {current_action}"]
            else:
                rows += ["Solution cost: —", f"Nodes expanded: {result.expanded}",
                         f"Nodes generated: {result.generated}", "No solution found"]
        for text in rows:
            screen.blit(font.render(text, True, (41, 49, 45)), (x, y))
            y += 31
        if len(self.results) > 1:
            y += 16
            screen.blit(font.render("Algorithm comparison", True, (41, 49, 45)), (x, y))
            y += 32
            screen.blit(small.render("Name       Cost    Expanded    Generated    Time", True, (62, 68, 64)), (x, y))
            y += 24
            for name, item in self.results.items():
                line = f"{name:<10} {str(item.cost):<8} {item.expanded:<12} {item.generated:<12} {item.elapsed_seconds:.4f}s"
                screen.blit(small.render(line, True, (62, 68, 64)), (x, y))
                y += 23
