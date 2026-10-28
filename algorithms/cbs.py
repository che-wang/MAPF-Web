import heapq
import time
from typing import List, Dict, Set, Tuple, Optional
from grid import Grid, Cell
from agent import Agent
from algorithms.base import MAPFAlgorithm
from algorithms.a_star import a_star


def _find_conflict(paths: Dict[int, List[Cell]]) -> Optional[Dict]:
    agent_ids = list(paths.keys())
    max_len = max(len(p) for p in paths.values()) if paths else 0
    for t in range(max_len):
        for i, a1 in enumerate(agent_ids):
            p1 = paths[a1]
            pos1 = p1[min(t, len(p1) - 1)]
            for a2 in agent_ids[i + 1:]:
                p2 = paths[a2]
                pos2 = p2[min(t, len(p2) - 1)]
                if pos1 == pos2:
                    return {'type': 'vertex', 'agents': (a1, a2), 'pos': pos1, 't': t}
                if t > 0 and t - 1 < len(p1) and t - 1 < len(p2):
                    if p1[t - 1] == pos2 and p2[t - 1] == pos1:
                        return {'type': 'edge', 'agents': (a1, a2),
                                'edge': (p1[t - 1], pos1), 't': t - 1}
    return None


def _sum_of_costs(paths: Dict[int, List[Cell]]) -> int:
    return sum(len(p) - 1 for p in paths.values())


def _hash_paths(paths: Dict[int, List[Cell]]) -> Tuple:
    return tuple(sorted((aid, tuple((c.x, c.y) for c in p)) for aid, p in paths.items()))


class CBS(MAPFAlgorithm):
    """
    CBS (Conflict-Based Search) - 经典最优 MAPF 算法。
    低层：时空 A* 为每个 agent 单独规划满足约束的路径。
    高层：搜索冲突约束树，遇到冲突时为两个 agent 分别加约束并分叉。
    使用 sum of costs 作为目标函数。内置 visited 去重避免重复搜索。
    """

    name = "CBS"

    def solve(self, grid: Grid, agents: List[Agent], timeout: float = 15.0) -> Dict[int, List[Cell]]:
        start_time = time.time()
        horizon = grid.width * grid.height * 4

        root_paths: Dict[int, List[Cell]] = {}
        root_constraints: Dict[int, Tuple[Set, Set]] = {}
        for a in agents:
            root_constraints[a.agent_id] = (set(), set())

        for a in agents:
            vc, ec = root_constraints[a.agent_id]
            path = a_star(grid, a.start, a.goal,
                          blocked_cells=vc, blocked_edges=ec,
                          max_time_steps=horizon, timeout=2.0)
            if path is None:
                return {}
            root_paths[a.agent_id] = path

        if len(root_paths) < len(agents):
            return {}

        class Node:
            __slots__ = ('cost', 'paths', 'constraints')
            def __init__(self, cost, paths, constraints):
                self.cost = cost
                self.paths = paths
                self.constraints = constraints

        open_list = []
        visited: Set[Tuple] = set()
        root_node = Node(_sum_of_costs(root_paths), root_paths, root_constraints)
        heapq.heappush(open_list, (root_node.cost, 0, root_node))
        visited.add(_hash_paths(root_paths))
        heap_counter = 1

        while open_list:
            if time.time() - start_time > timeout:
                break

            _, _, node = heapq.heappop(open_list)
            conflict = _find_conflict(node.paths)
            if conflict is None:
                return node.paths

            a1, a2 = conflict['agents']

            for agent_id in [a1, a2]:
                if time.time() - start_time > timeout:
                    break

                new_constraints = {aid: (vc.copy(), ec.copy())
                                   for aid, (vc, ec) in node.constraints.items()}

                if conflict['type'] == 'vertex':
                    pos, t = conflict['pos'], conflict['t']
                    new_constraints[agent_id][0].add((pos, t))
                else:
                    (c_from, c_to), t = conflict['edge'], conflict['t']
                    if agent_id == a1:
                        new_constraints[a1][1].add((c_from, c_to, t))
                    else:
                        new_constraints[a2][1].add((c_to, c_from, t))

                vc, ec = new_constraints[agent_id]
                agent_obj = next(a for a in agents if a.agent_id == agent_id)
                new_path = a_star(grid, agent_obj.start, agent_obj.goal,
                                  blocked_cells=vc, blocked_edges=ec,
                                  max_time_steps=horizon, timeout=2.0)
                if new_path is None:
                    continue

                new_paths = dict(node.paths)
                new_paths[agent_id] = new_path
                path_hash = _hash_paths(new_paths)
                if path_hash in visited:
                    continue
                visited.add(path_hash)

                new_cost = _sum_of_costs(new_paths)
                child = Node(new_cost, new_paths, new_constraints)
                heapq.heappush(open_list, (new_cost, heap_counter, child))
                heap_counter += 1

        return {}