import argparse
import importlib
import inspect
import os
import random
import sys
from typing import List, Optional, Dict, Type

from grid import Grid, Cell
from agent import Agent
from simulator import Simulator
from algorithms.base import MAPFAlgorithm


def discover_algorithms() -> Dict[str, Type[MAPFAlgorithm]]:
    algo_dir = os.path.join(os.path.dirname(__file__), "algorithms")
    algos: Dict[str, Type[MAPFAlgorithm]] = {}
    for fname in os.listdir(algo_dir):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        mod_name = fname[:-3]
        try:
            mod = importlib.import_module(f"algorithms.{mod_name}")
        except Exception:
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if (issubclass(obj, MAPFAlgorithm)
                    and obj is not MAPFAlgorithm
                    and not inspect.isabstract(obj)):
                instance = obj()
                algos[instance.name] = obj
    return algos


DEFAULT_COLORS = [
    (231, 76, 60), (52, 152, 219), (46, 204, 113), (241, 196, 15),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (142, 168, 209),
    (255, 105, 180), (178, 34, 34), (0, 139, 139), (218, 165, 32),
    (127, 255, 212), (255, 165, 0), (199, 21, 133), (70, 130, 180),
]


def create_agents(grid: Grid, num_agents: int,
                  seed: Optional[int] = None,
                  start_from_zero: bool = True) -> List[Agent]:
    rng = random.Random(seed)
    comp_map = grid.connected_components()
    if not comp_map:
        return []

    from collections import Counter
    counts = Counter(comp_map.values())
    largest_id = counts.most_common(1)[0][0]
    component_cells = [c for c, comp in comp_map.items() if comp == largest_id]

    if len(component_cells) < num_agents * 2:
        num_agents = len(component_cells) // 2

    if num_agents <= 0:
        return []

    starts = rng.sample(component_cells, num_agents)
    remaining = [c for c in component_cells if c not in starts]
    goals = rng.sample(remaining, num_agents) if len(remaining) >= num_agents else remaining[:num_agents]

    agents = []
    for i in range(min(len(starts), len(goals))):
        agents.append(Agent(
            agent_id=i,
            start=starts[i],
            goal=goals[i],
            color=DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        ))

    return agents


def run_text_only(sim: Simulator):
    print("=" * 50)
    print(f"Algorithm: {sim.algorithm.name}")
    print(f"Grid: {sim.grid.width}x{sim.grid.height}, obstacles: {len(sim.grid.obstacles)}")
    print(f"Agents: {len(sim.agents)}")
    print("=" * 50)

    if sim.plan():
        print("Planning succeeded!")
    else:
        print("Planning failed for some agents.")

    for agent in sim.agents:
        path_str = " -> ".join(f"({c.x},{c.y})" for c in agent.path) if agent.path else "NO PATH"
        print(f"  Agent {agent.agent_id}: {path_str}")

    summary = sim.summary()
    print("-" * 50)
    print(f"Makespan: {summary['makespan']}")
    print(f"Total Path Length: {summary['total_path_length']}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="MAPF Simulation Framework")
    parser.add_argument("--width", type=int, default=20)
    parser.add_argument("--height", type=int, default=20)
    parser.add_argument("--obstacles", type=float, default=0.2)
    parser.add_argument("--agents", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--algo", type=str, default=None)
    parser.add_argument("--cell-size", type=int, default=35)
    parser.add_argument("--no-vis", action="store_true")
    parser.add_argument("--show-static", action="store_true")
    parser.add_argument("--load-map", type=str, default=None)
    parser.add_argument("--save-map", type=str, default=None)

    args = parser.parse_args()
    algorithms = discover_algorithms()

    if args.load_map:
        grid = Grid.load_from_file(args.load_map)
    else:
        grid = Grid(args.width, args.height, args.obstacles, seed=args.seed)

    if args.save_map:
        grid.save_to_file(args.save_map)
        print(f"Map saved to {args.save_map}")

    agents = create_agents(grid, args.agents, seed=args.seed)

    algo_name = args.algo or (list(algorithms.keys())[0] if algorithms else "prioritized")
    algo_cls = algorithms.get(algo_name)
    if algo_cls is None:
        print(f"Warning: algorithm '{algo_name}' not found. Available: {list(algorithms.keys())}")
        algo_cls = list(algorithms.values())[0]

    sim = Simulator(grid, agents, algo_cls())
    run_text_only(sim)

    if args.no_vis:
        return

    from visualizer import Visualizer
    vis = Visualizer(grid, agents, sim, cell_size=args.cell_size,
                     algorithms=list(algorithms.values()),
                     algorithm_names=list(algorithms.keys()),
                     initial_algo_name=algo_name,
                     config={
                         'width': grid.width,
                         'height': grid.height,
                         'obstacle_ratio': grid.obstacle_ratio,
                         'num_agents': len(agents),
                         'seed': args.seed,
                     })

    if args.show_static:
        vis.show_static()
    else:
        vis.run()


if __name__ == "__main__":
    main()