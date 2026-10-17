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
        self._font_cache: dict[tuple[int, bool], object] = {}
        self._freetype_font_keys: set[tuple[int, bool]] = set()

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
        pygame.display.set_caption("Sokoban Search Lab")
        clock = pygame.time.Clock()
        title_font, font, small = self._create_fonts(pygame)
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
                    if 64 <= my < 108 and 18 <= mx < 18 + 5 * 86:
                        self._change_level(min(4, (mx - 18) // 86))
                    elif 112 <= my < 162:
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

            screen.fill((17, 24, 39))
            self._draw_controls(pygame, screen, title_font, font, small,
                                self.level_index, self.playing, self.solving)
            state = result.path[self.step] if result and result.found else self.levels[self.level_index]
            panel_x = min(810, screen.get_width() - 310)
            self._draw_board(pygame, screen, state, panel_x, screen.get_height())
            self._draw_info(pygame, screen, small, panel_x, result)
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()

    @staticmethod
    def _create_fonts(pygame: object) -> tuple[object, object, object]:
        """Create GUI fonts, falling back to freetype if pygame.font is unavailable."""
        # Pygame 2.6.1 has a pygame.font/sysfont circular import under Python 3.14.
        if sys.version_info >= (3, 14) and pygame.version.vernum <= (2, 6, 1):
            import pygame._freetype as freetype

            freetype.init()
            return (_FreeTypeFontAdapter(freetype, 27), _FreeTypeFontAdapter(freetype, 17),
                    _FreeTypeFontAdapter(freetype, 14))
        try:
            pygame_font = pygame.font
            pygame_font.init()
            return (pygame_font.SysFont("arial", 27, bold=True), pygame_font.SysFont("arial", 17),
                    pygame_font.SysFont("arial", 14))
        except (ImportError, NotImplementedError):
            # Pygame 2.6.1's pygame.font module can fail to import on Python 3.14
            # because pygame.sysfont imports Font before pygame.font defines it.
            import pygame._freetype as freetype

            freetype.init()
            return (_FreeTypeFontAdapter(freetype, 27), _FreeTypeFontAdapter(freetype, 17),
                    _FreeTypeFontAdapter(freetype, 14))

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

    def _draw_controls(self, pygame: object, screen: object, title_font: object,
                       font: object, small: object, selected_level: int,
                       playing: bool, solving: bool) -> None:
        """Draw the title, level selector, and playback control bar."""
        width = screen.get_width()
        screen.blit(title_font.render("SOKOBAN", True, (245, 247, 250)), (24, 15))
        screen.blit(small.render("SEARCH LAB  /  BREADTH-FIRST SEARCH", True, (155, 171, 191)), (27, 46))
        right_label = small.render("MASTER 1  •  VISUAL COMPUTING", True, (155, 171, 191))
        screen.blit(right_label, (width - right_label.get_width() - 25, 27))

        def button(rect: tuple[int, int, int, int], label: str, selected: bool = False,
                   primary: bool = False) -> None:
            x, y, button_width, button_height = rect
            fill = (50, 115, 96) if primary else ((49, 77, 110) if selected else (34, 45, 63))
            edge = (84, 174, 145) if primary or selected else (59, 73, 94)
            pygame.draw.rect(screen, (10, 16, 27), (x, y + 3, button_width, button_height), border_radius=9)
            pygame.draw.rect(screen, fill, rect, border_radius=9)
            pygame.draw.rect(screen, edge, rect, 1, border_radius=9)
            color = (246, 250, 248) if primary or selected else (202, 211, 222)
            text = font.render(label, True, color)
            screen.blit(text, text.get_rect(center=(x + button_width // 2, y + button_height // 2)))

        for i in range(5):
            button((18 + i * 86, 67, 78, 36), f"LEVEL {i + 1}", selected=(i == selected_level))
        solve_label = "SOLVING..." if solving else "SOLVE  S"
        play_label = "PAUSE  SPACE" if playing else "PLAY  SPACE"
        controls = [((18, 116, 102, 42), solve_label, False, True),
                    ((128, 116, 102, 42), play_label, playing, False),
                    ((238, 116, 92, 42), "STEP  N", False, False),
                    ((338, 116, 92, 42), "BACK  B", False, False),
                    ((438, 116, 82, 42), "RESET  R", False, False)]
        for rect, label, selected, primary in controls:
            button(rect, label, selected, primary)
        speed_label = small.render("SPEED   −   /   +", True, (155, 171, 191))
        screen.blit(speed_label, (540, 130))

    def _draw_board(self, pygame: object, screen: object, state: SokobanPuzzle,
                    panel_x: int, screen_height: int) -> None:
        """Draw a centered, fit-to-window board using primitive shapes."""
        layout = state.layout
        card = pygame.Rect(20, 180, panel_x - 34, screen_height - 200)
        pygame.draw.rect(screen, (10, 16, 27), card.move(0, 5), border_radius=18)
        pygame.draw.rect(screen, (27, 37, 54), card, border_radius=18)
        pygame.draw.rect(screen, (48, 63, 85), card, 1, border_radius=18)
        # Title and a compact legend give the board a clear visual frame.
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

    def _draw_info(self, pygame: object, screen: object, small: object,
                   panel_x: int, result: SearchResult | None) -> None:
        """Display solution status and search metrics in a dedicated panel."""
        screen_width, screen_height = screen.get_size()
        card = pygame.Rect(panel_x + 14, 180, screen_width - panel_x - 34, screen_height - 200)
        pygame.draw.rect(screen, (10, 16, 27), card.move(0, 5), border_radius=18)
        pygame.draw.rect(screen, (27, 37, 54), card, border_radius=18)
        pygame.draw.rect(screen, (48, 63, 85), card, 1, border_radius=18)
        x, width = card.x + 20, card.width - 40
        y = card.y + 20
        screen.blit(self._render_text(pygame, "SEARCH RESULTS", 16, (226, 232, 240), bold=True), (x, y))
        y += 36
        screen.blit(self._render_text(pygame, self.level_names[self.level_index].upper(), 13,
                                      (152, 166, 184)), (x, y))
        y += 25

        if self.solving:
            status, status_color = "SEARCHING", (221, 164, 76)
        elif result and result.found:
            status, status_color = "SOLUTION FOUND", (85, 190, 148)
        elif result:
            status, status_color = "NO SOLUTION", (226, 112, 104)
        else:
            status, status_color = "READY TO SOLVE", (123, 157, 208)
        pill = pygame.Rect(x, y, min(width, 160), 27)
        status_background = (35, 76, 67) if result and result.found else (
            (77, 60, 38) if self.solving else ((78, 48, 48) if result else (39, 57, 82)))
        pygame.draw.rect(screen, status_background, pill, border_radius=13)
        pygame.draw.rect(screen, status_color, pill, 1, border_radius=13)
        screen.blit(self._render_text(pygame, status, 12, status_color, bold=True),
                    (pill.x + 11, pill.y + 6))
        y += 44

        if result and result.found:
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
            self._draw_metric_grid(pygame, screen, small, x, y, width, metrics)
            y += 108
        elif result:
            screen.blit(self._render_text(pygame, "No solution found", 17, (226, 132, 123)), (x, y))
            y += 36
            metrics = [("EXPANDED", f"{result.expanded:,}"), ("GENERATED", f"{result.generated:,}"),
                       ("MAX FRONTIER", f"{result.max_frontier:,}"),
                       ("SEARCH TIME", f"{result.elapsed_seconds:.4f}s")]
            self._draw_metric_grid(pygame, screen, small, x, y, width, metrics)
            y += 108
        else:
            screen.blit(self._render_text(pygame, "Find the shortest route", 19,
                                          (220, 228, 238), bold=True), (x, y))
            y += 30
            screen.blit(self._render_text(pygame, "BFS explores states by move count.", 13,
                                          (152, 166, 184)), (x, y))
            y += 29
            screen.blit(self._render_text(pygame, "Search runs in the background,", 13,
                                          (152, 166, 184)), (x, y))
            y += 20
            screen.blit(self._render_text(pygame, "so playback controls stay responsive.", 13,
                                          (152, 166, 184)), (x, y))
            y += 51

        if len(self.results) > 1:
            screen.blit(self._render_text(pygame, "ALGORITHM COMPARISON", 13,
                                          (226, 232, 240), bold=True), (x, y))
            y += 24
            for name, item in self.results.items():
                line = f"{name}  ·  cost {item.cost}  ·  {item.expanded:,} expanded"
                screen.blit(self._render_text(pygame, line, 12, (181, 194, 211)), (x, y))
                y += 20
        screen.blit(self._render_text(pygame, "SPACE  play / pause     R  reset", 11,
                                      (120, 139, 162)), (x, card.bottom - 28))

    def _render_text(self, pygame: object, text: str, size: int,
                     color: tuple[int, int, int], bold: bool = False) -> object:
        """Render one text label with the best font backend available."""
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

    def _draw_metric_grid(self, pygame: object, screen: object, small: object,
                          x: int, y: int, width: int,
                          metrics: list[tuple[str, str]]) -> None:
        """Draw compact two-column statistic cards."""
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
        """Draw a subtly shaded brick tile with staggered mortar joints."""
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
        """Draw a wooden crate with inset panel lines and a soft shadow."""
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
        """Draw a friendly, high-contrast player sprite."""
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
