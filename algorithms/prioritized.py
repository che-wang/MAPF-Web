from typing import List, Dict, Set
from grid import Grid, Cell
from agent import Agent
from algorithms.base import MAPFAlgorithm
from algorithms.a_star import a_star


class PrioritizedPlanning(MAPFAlgorithm):
    """
    基于优先级的规划 (Prioritized Planning)。
    按顺序为每个智能体规划路径，规划时考虑之前已规划智能体的时空占用约束。
    智能体到达终点后永久占据该格子直到所有智能体都完成，其他智能体必须绕行。
    """

    name = "Prioritized Planning"

    def solve(self, grid: Grid, agents: List[Agent]) -> Dict[int, List[Cell]]:
        result: Dict[int, List[Cell]] = {}
        blocked_cells: Set[tuple] = set()
        blocked_edges: Set[tuple] = set()
        goal_cells: List[tuple] = []

        for agent in agents:
            path = a_star(grid, agent.start, agent.goal,
                          blocked_cells=blocked_cells,
                          blocked_edges=blocked_edges)
            if path is None:
                continue

            result[agent.agent_id] = path

            for t, cell in enumerate(path):
                blocked_cells.add((cell, t))

            for t in range(len(path) - 1):
                blocked_edges.add((path[t], path[t + 1], t))
                blocked_edges.add((path[t + 1], path[t], t))

            goal_cell = path[-1]
            goal_t = len(path) - 1
            goal_cells.append((goal_cell, goal_t))

        if not result:
            return result

        baseline_makespan = max(len(p) - 1 for p in result.values())
        horizon = max(baseline_makespan, grid.width * grid.height * 4)

        result = {}
        blocked_cells.clear()
        blocked_edges.clear()
        for goal_cell, goal_t in goal_cells:
            for t in range(goal_t + 1, horizon + 1):
                blocked_cells.add((goal_cell, t))

        for agent in agents:
            path = a_star(grid, agent.start, agent.goal,
                          blocked_cells=blocked_cells,
                          blocked_edges=blocked_edges,
                          max_time_steps=horizon)
            if path is None:
                continue

            result[agent.agent_id] = path

            for t, cell in enumerate(path):
                blocked_cells.add((cell, t))

            for t in range(len(path) - 1):
                blocked_edges.add((path[t], path[t + 1], t))
                blocked_edges.add((path[t + 1], path[t], t))

        return result