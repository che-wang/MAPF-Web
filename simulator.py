from typing import List, Dict, Optional, Tuple
from grid import Grid, Cell
from agent import Agent
from algorithms.base import MAPFAlgorithm


class Simulator:
    """仿真器：负责运行算法、驱动智能体按路径移动、检测冲突。"""

    def __init__(self, grid: Grid, agents: List[Agent], algorithm: MAPFAlgorithm):
        self.grid = grid
        self.agents = agents
        self.algorithm = algorithm
        self.step = 0
        self.max_step = 500
        self.conflicts: List[dict] = []
        self.solved = False

    def reset(self):
        self.step = 0
        self.conflicts = []
        self.solved = False
        for agent in self.agents:
            agent.path = []
            agent.current_step = 0

    def plan(self) -> bool:
        paths = self.algorithm.solve(self.grid, self.agents)
        for agent in self.agents:
            if agent.agent_id in paths and paths[agent.agent_id]:
                agent.path = paths[agent.agent_id]
                agent.reset()
            else:
                self.conflicts.append({
                    'type': 'no_path',
                    'agent_id': agent.agent_id,
                    'msg': f'Agent {agent.agent_id} has no valid path'
                })
        self.solved = len(self.conflicts) == 0
        return self.solved

    def detect_conflicts(self) -> List[dict]:
        conflicts = []
        occupied: Dict[tuple, int] = {}
        t = self.step

        for agent in self.agents:
            if agent.path and t < len(agent.path):
                pos = agent.path[t]
            elif agent.path:
                pos = agent.path[-1]
            else:
                pos = agent.start

            key = (pos, t)
            if key in occupied:
                conflicts.append({
                    'type': 'vertex',
                    'agents': [occupied[key], agent.agent_id],
                    'pos': pos,
                    'time': t
                })
            else:
                occupied[key] = agent.agent_id

        return conflicts

    def all_done(self) -> bool:
        return all(a.is_done() for a in self.agents)

    def run_step(self) -> bool:
        if self.all_done():
            return False
        if self.step >= self.max_step:
            return False

        for agent in self.agents:
            if not agent.is_done():
                agent.step()

        self.step += 1
        return True

    def set_step(self, t: int):
        self.step = max(0, min(t, self.makespan()))
        for agent in self.agents:
            if agent.path:
                agent.current_step = min(self.step, len(agent.path) - 1)

    def step_forward(self):
        if self.step < self.makespan():
            self.set_step(self.step + 1)

    def step_backward(self):
        if self.step > 0:
            self.set_step(self.step - 1)

    def total_path_length(self) -> int:
        return sum(a.path_length() for a in self.agents)

    def makespan(self) -> int:
        if not self.agents:
            return 0
        return max((len(a.path) - 1) if a.path else 0 for a in self.agents)

    def summary(self) -> dict:
        return {
            'solved': self.solved,
            'algorithm': self.algorithm.name,
            'num_agents': len(self.agents),
            'total_path_length': self.total_path_length(),
            'makespan': self.makespan(),
            'conflicts': self.conflicts,
        }