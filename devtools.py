import pygame as pg
import logging
from multiprocessing import Queue
from Engine.DOM.element import Element, DevtoolsSubElement
from Ui.scrollbar import VScrollBar
from typing import List, Tuple, Generator
from config import DEVTOOLS_WIN_WIDTH, DEVTOOLS_WIN_HEIGHT, DEVTOOLS_BASE_TITLE

# IF PYTHON VERSION == 3.11+ UNCOMMENT THIS LINE AND COMMENT OUT THE OTHER ONE
#from typing import Self

# IF PYTHON VERSION < 3.11
from typing_extensions import Self

pg.font.init()

class ElementRepresentation:
    """
    The inspector's representation of the `Element` class in the engine.

    It stores the original element's data, but also some data for the inspector's renderer.
    """

    def __init__(self, element: Element, rect: pg.Rect, font: pg.Surface) -> None:
        self.element: Element = element
        self.rect: pg.Rect = rect
        self.font: pg.Surface = font

        self.selected: bool = False

        self.children: List[Self] = []

class HTMLInspector:
    """
    An addon for Plazma Browser that shows all loaded HTML elements in the browser and information about them in a new window
    """

    ELEMENT_VIEW_WIDTH: int = DEVTOOLS_WIN_WIDTH - 10
    ELEMENT_VIEW_HEIGHT: int = DEVTOOLS_WIN_HEIGHT - 10

    ELEMENT_VIEW_RECT: pg.Rect = pg.Rect(0, 0, ELEMENT_VIEW_WIDTH, ELEMENT_VIEW_HEIGHT)

    DEPTH_INDENT: int = 10

    FONT: pg.Font = pg.font.Font("./Engine/STR/fonts/arial.ttf", 15)

    def __init__(self, master_element: Element, update_queue: Queue, patch_queue: Queue) -> None:
        logging.debug(f"[DEVTOOLS] Initializing DevTools...")

        self.update_queue: Queue = update_queue
        self.patch_queue: Queue = patch_queue
        
        # TODO: Make the screen resizable
        self.screen: pg.Surface = pg.display.set_mode((DEVTOOLS_WIN_WIDTH, DEVTOOLS_WIN_HEIGHT))

        self.display_surface: pg.Surface = pg.Surface((self.ELEMENT_VIEW_WIDTH, self.ELEMENT_VIEW_HEIGHT))

        self.master_element: Element = master_element
        self.master_element_representation: ElementRepresentation = ElementRepresentation(self.master_element, pg.Rect(0, 0, self.ELEMENT_VIEW_WIDTH, 10), pg.Surface((0, 0)))

        self.scroll_y: float = 0.0

        logging.debug("[DEVTOOLS] " + DEVTOOLS_BASE_TITLE + "Welcome! (Queues setup, Pygame display online)")

    def iterative_dfs(self, root: Element) -> Generator[Element, None, None]:
        if root is None: yield [None]

        stack: List[Element] = [root]

        while len(stack) > 0:
            node = stack.pop()

            yield node

            stack.extend(reversed(node.children))

    def load_element_tree(self) -> None:
        curr_y: int = 0

        for element in self.iterative_dfs(self.master_element):
            indent: int = element.depth * self.DEPTH_INDENT

            element.devtools_attrs = DevtoolsSubElement(pg.Rect(indent, curr_y, DEVTOOLS_WIN_WIDTH-indent, 20), self.FONT.render(f"<{element.tag}>", True, (255, 255, 255)))

            curr_y += 20

    def render_element_tree(self) -> None:
        self.display_surface.fill((100, 100, 100))

        if self.master_element is None: return

        mouse_pos = pg.mouse.get_pos()
        mouse_pos = (mouse_pos[0], mouse_pos[1]+self.scroll_y)
        mouse_pressed: bool = pg.mouse.get_pressed()

        for element in self.iterative_dfs(self.master_element):
            devtools_sub_elem: DevtoolsSubElement = element.devtools_attrs

            if devtools_sub_elem.rect.y + devtools_sub_elem.rect.width > self.scroll_y and devtools_sub_elem.rect.y < self.scroll_y + self.ELEMENT_VIEW_HEIGHT:
                rect_color: Tuple[int, int, int] = (100, 100, 100)
                devtools_sub_elem.selected = False
                
                if devtools_sub_elem.rect.collidepoint(mouse_pos):
                    if mouse_pressed: devtools_sub_elem.selected = True
                    else: rect_color = (150, 150, 150)

                if devtools_sub_elem.selected: rect_color = (200, 200, 200)

                if devtools_sub_elem.rect.y + devtools_sub_elem.rect.height > self.display_surface.get_height():
                    new_display_surface: pg.Surface = pg.Surface((self.ELEMENT_VIEW_WIDTH, self.display_surface.get_height()+self.ELEMENT_VIEW_HEIGHT))
                    new_display_surface.fill((100, 100, 100))
                    new_display_surface.blit(self.display_surface, (0, 0))
                    self.display_surface = new_display_surface

                pg.draw.rect(self.display_surface, rect_color, devtools_sub_elem.rect, border_radius=2)
                self.display_surface.blit(devtools_sub_elem.font, (devtools_sub_elem.rect.x + 10, devtools_sub_elem.rect.y))

    def render(self) -> None:
        self.render_element_tree()

        self.screen.blit(self.display_surface, (0, -self.scroll_y))

    def main(self) -> None:
        pg.display.set_caption(DEVTOOLS_BASE_TITLE + "[PAGE TITLE NOT GIVEN]")

        clock: pg.time.Clock = pg.time.Clock()

        frame_count: int = 0

        while 1:
            self.screen.fill((0, 0, 0))

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    exit()

                elif event.type == pg.MOUSEWHEEL:
                    self.scroll_y -= event.y * 10

            frame_count %= 100

            if frame_count == 0:
                try: master_element: Element | None = self.update_queue.get(block=False, timeout=1)
                except: master_element = None
                
                if master_element is not None:
                    logging.debug("[DEVTOOLS] Recieved top level element!")
                    self.master_element = master_element
                    self.master_element_representation = ElementRepresentation(self.master_element, pg.Rect(0, 0, self.ELEMENT_VIEW_WIDTH, 10), pg.Surface((0, 0)))
                    self.load_element_tree()

            self.render()

            clock.tick(100)
            pg.display.flip()

def start_inspector(update_queue: Queue, patch_queue: Queue):
    html_inspector: HTMLInspector = HTMLInspector(None, update_queue, patch_queue)
    html_inspector.main()