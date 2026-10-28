from dataclasses import dataclass, field
from typing import List, Optional
from grid import Cell


@dataclass
class Agent:
    agent_id: int
    start: Cell
    goal: Cell
    color: tuple = (255, 100, 100)
    path: List[Cell] = field(default_factory=list)
    current_step: int = 0

    def position(self) -> Cell:
        if not self.path:
            return self.start
        idx = min(self.current_step, len(self.path) - 1)
        return self.path[idx]

    def next_position(self) -> Optional[Cell]:
        if self.current_step + 1 < len(self.path):
            return self.path[self.current_step + 1]
        return None

    def is_done(self) -> bool:
        return bool(self.path) and self.current_step >= len(self.path) - 1

    def step(self):
        if not self.is_done():
            self.current_step += 1

    def reset(self):
        self.current_step = 0

    def path_length(self) -> int:
        return len(self.path) - 1 if self.path else 0