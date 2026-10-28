import heapq
import time
from typing import Optional, List, Set, Tuple
from grid import Grid, Cell


def a_star(grid: Grid, start: Cell, goal: Cell,
           blocked_cells: Optional[Set[Tuple[Cell, int]]] = None,
           blocked_edges: Optional[Set[Tuple[Cell, Cell, int]]] = None,
           max_time_steps: Optional[int] = None,
           timeout: float = 2.0) -> Optional[List[Cell]]:
    if blocked_cells is None:
        blocked_cells = set()
    if blocked_edges is None:
        blocked_edges = set()

    if not grid.is_passable(start) or not grid.is_passable(goal):
        return None

    if start == goal:
        return [start]

    if max_time_steps is None:
        max_time_steps = grid.width * grid.height * 4

    start_time = time.time()

    def h(c: Cell) -> int:
        return abs(c.x - goal.x) + abs(c.y - goal.y)

    start_state = (start, 0)
    g_score = {start_state: 0}
    tie = 0
    open_set = [(h(start), 0, tie, start_state)]
    came_from = {}

    while open_set:
        if time.time() - start_time > timeout:
            return None

        f, g, _, state = heapq.heappop(open_set)
        cell, t = state

        if cell == goal:
            path = [cell]
            cur = state
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur[0])
            path.reverse()
            return path

        if t >= max_time_steps:
            continue

        neighbors = grid.neighbors(cell) + [cell]
        for next_cell in neighbors:
            next_t = t + 1
            if (next_cell, next_t) in blocked_cells:
                continue
            if (cell, next_cell, t) in blocked_edges:
                continue

            tentative_g = g + 1
            next_state = (next_cell, next_t)
            if tentative_g < g_score.get(next_state, float('inf')):
                came_from[next_state] = state
                g_score[next_state] = tentative_g
                tie += 1
                f_new = tentative_g + h(next_cell)
                heapq.heappush(open_set, (f_new, tentative_g, tie, next_state))

    return None