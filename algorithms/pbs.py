import heapq
import time
import random
from typing import List, Dict, Set, Tuple, Optional
from grid import Grid, Cell
from agent import Agent
from algorithms.base import MAPFAlgorithm
from algorithms.a_star import a_star


def _find_conflict(paths: Dict[int, List[Cell]]) -> Optional[Dict]:
    agent_ids = list(paths.keys())
    if not agent_ids:
        return None
    max_len = max(len(p) for p in paths.values())
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


def _prioritized_plan(grid: Grid, agents: List[Agent],
                     blocked_cells_extra: Optional[Dict[int, Set]] = None,
                     blocked_edges_extra: Optional[Dict[int, Set]] = None,
                     horizon: int = 0, timeout: float = 2.0,
                     start_time: float = 0) -> Dict[int, List[Cell]]:
    result: Dict[int, List[Cell]] = {}
    blocked_cells: Set[Tuple[Cell, int]] = set()
    blocked_edges: Set[Tuple[Cell, Cell, int]] = set()
    goal_cells: List[Tuple[Cell, int]] = []

    for a in agents:
        if time.time() - start_time > timeout:
            return {}
        path = a_star(grid, a.start, a.goal,
                      blocked_cells=blocked_cells,
                      blocked_edges=blocked_edges)
        if path is None:
            continue
        result[a.agent_id] = path
        for t, cell in enumerate(path):
            blocked_cells.add((cell, t))
        for t in range(len(path) - 1):
            blocked_edges.add((path[t], path[t + 1], t))
            blocked_edges.add((path[t + 1], path[t], t))
        goal_cells.append((path[-1], len(path) - 1))

    if not result:
        return result

    baseline_makespan = max(len(p) - 1 for p in result.values())
    h = horizon if horizon > 0 else max(baseline_makespan, grid.width * grid.height * 4)

    result = {}
    blocked_cells.clear()
    blocked_edges.clear()
    for gc, gt in goal_cells:
        for t in range(gt + 1, h + 1):
            blocked_cells.add((gc, t))

    for a in agents:
        if time.time() - start_time > timeout:
            return result
        path = a_star(grid, a.start, a.goal,
                      blocked_cells=blocked_cells,
                      blocked_edges=blocked_edges,
                      max_time_steps=h)
        if path is None:
            continue
        result[a.agent_id] = path
        for t, cell in enumerate(path):
            blocked_cells.add((cell, t))
        for t in range(len(path) - 1):
            blocked_edges.add((path[t], path[t + 1], t))
            blocked_edges.add((path[t + 1], path[t], t))

    return result


def _plan_independent_with_constraints(grid: Grid, agents: List[Agent],
                                       vc_map: Dict[int, Set],
                                       ec_map: Dict[int, Set],
                                       horizon: int,
                                       timeout: float,
                                       start_time: float) -> Dict[int, List[Cell]]:
    paths = {}
    for a in agents:
        if time.time() - start_time > timeout:
            return {}
        aid = a.agent_id
        vc = vc_map.get(aid, set())
        ec = ec_map.get(aid, set())
        path = a_star(grid, a.start, a.goal,
                      blocked_cells=vc, blocked_edges=ec,
                      max_time_steps=horizon, timeout=2.0)
        if path is None:
            return {}
        paths[aid] = path
    return paths


class PBS(MAPFAlgorithm):
    """
    PBS (Priority-Based Search) - 基于优先级搜索的 MAPF 算法。

    初始用 Prioritized Planning 得到无冲突路径。若有 agent 规划失败或路径有冲突，
    进入 CBS 风格的约束搜索：每次处理一个冲突，为两个 agent 同时加约束并重规划。
    比 CBS 快很多（初始路径已很好），比纯 Prioritized Planning 更完备。
    """

    name = "PBS"

    def solve(self, grid: Grid, agents: List[Agent], timeout: float = 10.0) -> Dict[int, List[Cell]]:
        start_time = time.time()
        horizon = grid.width * grid.height * 4

        root_paths = _prioritized_plan(grid, agents, horizon=horizon,
                                       timeout=timeout, start_time=start_time)

        if root_paths and len(root_paths) == len(agents):
            conflict = _find_conflict(root_paths)
            if conflict is None:
                return root_paths

        class Node:
            __slots__ = ('cost', 'paths', 'vc_map', 'ec_map')
            def __init__(self, cost, paths, vc_map, ec_map):
                self.cost = cost
                self.paths = paths
                self.vc_map = vc_map
                self.ec_map = ec_map

        vc_map: Dict[int, Set] = {a.agent_id: set() for a in agents}
        ec_map: Dict[int, Set] = {a.agent_id: set() for a in agents}

        if not root_paths:
            root_paths = _plan_independent_with_constraints(
                grid, agents, vc_map, ec_map, horizon, timeout, start_time)
        if not root_paths or len(root_paths) < len(agents):
            return root_paths if root_paths else {}

        all_ok_paths = root_paths.copy()
        open_list = []
        visited: Set[Tuple] = set()
        heap_counter = 0
        root_node = Node(_sum_of_costs(root_paths), root_paths, vc_map, ec_map)
        heapq.heappush(open_list, (root_node.cost, heap_counter, root_node))
        heap_counter += 1
        visited.add(_hash_paths(root_paths))

        while open_list:
            if time.time() - start_time > timeout:
                break

            _, _, node = heapq.heappop(open_list)
            conflict = _find_conflict(node.paths)
            if conflict is None:
                if len(node.paths) == len(agents):
                    return node.paths
                for aid in node.paths:
                    all_ok_paths[aid] = node.paths[aid]
                continue

            a1, a2 = conflict['agents']
            new_vc = {aid: vc.copy() for aid, vc in node.vc_map.items()}
            new_ec = {aid: ec.copy() for aid, ec in node.ec_map.items()}

            if conflict['type'] == 'vertex':
                pos, t = conflict['pos'], conflict['t']
                new_vc[a1].add((pos, t))
                new_vc[a2].add((pos, t))
            else:
                (c_from, c_to), t = conflict['edge'], conflict['t']
                new_ec[a1].add((c_from, c_to, t))
                new_ec[a2].add((c_to, c_from, t))

            new_paths: Dict[int, List[Cell]] = {}
            all_ok = True
            for a in agents:
                if time.time() - start_time > timeout:
                    break
                aid = a.agent_id
                if aid in (a1, a2):
                    path = a_star(grid, a.start, a.goal,
                                  blocked_cells=new_vc[aid],
                                  blocked_edges=new_ec[aid],
                                  max_time_steps=horizon, timeout=2.0)
                    if path is None:
                        all_ok = False
                        break
                    new_paths[aid] = path
                else:
                    new_paths[aid] = node.paths.get(aid)

            if not all_ok:
                continue

            path_hash = _hash_paths(new_paths)
            if path_hash in visited:
                continue
            visited.add(path_hash)

            new_cost = _sum_of_costs(new_paths)
            child = Node(new_cost, new_paths, new_vc, new_ec)
            heapq.heappush(open_list, (new_cost, heap_counter, child))
            heap_counter += 1

        return all_ok_paths if all_ok_paths else {}