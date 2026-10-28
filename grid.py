import random
from dataclasses import dataclass
from typing import List, Tuple, Set, Optional, Dict


@dataclass(frozen=True)
class Cell:
    x: int
    y: int


class Grid:
    def __init__(self, width: int, height: int, obstacle_ratio: float = 0.0,
                 seed: Optional[int] = None, obstacles: Optional[Set[Cell]] = None):
        self.width = width
        self.height = height
        self.obstacles: Set[Cell] = set()
        self.obstacle_ratio = obstacle_ratio

        if obstacles is not None:
            self.obstacles = set(obstacles)
        elif obstacle_ratio > 0:
            self._generate_obstacles(obstacle_ratio, seed)

    def regenerate_obstacles(self, ratio: float = 0.0, seed: Optional[int] = None):
        self.obstacle_ratio = ratio
        self.obstacles.clear()
        if ratio > 0:
            self._generate_obstacles(ratio, seed)

    def resize(self, width: int, height: int, ratio: float = 0.0, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.obstacle_ratio = ratio
        self.obstacles.clear()
        if ratio > 0:
            self._generate_obstacles(ratio, seed)

    def _generate_obstacles(self, ratio: float, seed: Optional[int]):
        rng = random.Random(seed)
        total_cells = self.width * self.height
        num_obstacles = int(total_cells * ratio)
        all_cells = [Cell(x, y) for x in range(self.width) for y in range(self.height)]
        self.obstacles = set(rng.sample(all_cells, num_obstacles))

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell.x < self.width and 0 <= cell.y < self.height

    def is_passable(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and cell not in self.obstacles

    def neighbors(self, cell: Cell) -> List[Cell]:
        dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        result = []
        for dx, dy in dirs:
            n = Cell(cell.x + dx, cell.y + dy)
            if self.is_passable(n):
                result.append(n)
        return result

    def free_cells(self) -> List[Cell]:
        return [Cell(x, y) for x in range(self.width)
                for y in range(self.height)
                if self.is_passable(Cell(x, y))]

    def random_free_cell(self, rng: Optional[random.Random] = None) -> Optional[Cell]:
        rng = rng or random
        free = self.free_cells()
        if not free:
            return None
        return rng.choice(free)

    def connected_components(self) -> Dict[Cell, int]:
        comp_id = 0
        comp_map: Dict[Cell, int] = {}
        for cell in self.free_cells():
            if cell in comp_map:
                continue
            stack = [cell]
            comp_map[cell] = comp_id
            while stack:
                c = stack.pop()
                for n in self.neighbors(c):
                    if n not in comp_map:
                        comp_map[n] = comp_id
                        stack.append(n)
            comp_id += 1
        return comp_map

    def component_of(self, cell: Cell, comp_map: Optional[Dict[Cell, int]] = None) -> Optional[int]:
        if not self.is_passable(cell):
            return None
        if comp_map is None:
            comp_map = self.connected_components()
        return comp_map.get(cell)

    def largest_component_cells(self) -> List[Cell]:
        comp_map = self.connected_components()
        if not comp_map:
            return []
        from collections import Counter
        counts = Counter(comp_map.values())
        largest_id = counts.most_common(1)[0][0]
        return [c for c, comp in comp_map.items() if comp == largest_id]

    def save_to_file(self, path: str):
        with open(path, 'w') as f:
            f.write(f"{self.width} {self.height}\n")
            for y in range(self.height):
                row = []
                for x in range(self.width):
                    row.append('@' if Cell(x, y) in self.obstacles else '.')
                f.write(''.join(row) + '\n')

    @classmethod
    def load_from_file(cls, path: str) -> 'Grid':
        with open(path) as f:
            w, h = map(int, f.readline().split())
            obs = set()
            for y in range(h):
                row = f.readline().strip()
                for x, ch in enumerate(row):
                    if ch == '@':
                        obs.add(Cell(x, y))
        return cls(w, h, obstacles=obs)

    def __repr__(self):
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                row.append('@' if Cell(x, y) in self.obstacles else '.')
            lines.append(''.join(row))
        return '\n'.join(lines)