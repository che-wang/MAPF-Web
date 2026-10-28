from grid import Grid, Cell
from agent import Agent
from algorithms.prioritized import PrioritizedPlanning
from algorithms.cbs import CBS
from algorithms.sipp import CBS_SIPP
from algorithms.pbs import PBS
import time

def test_algo(name, algo, g, agents):
    t0 = time.time()
    paths = algo.solve(g, agents)
    dt = time.time() - t0
    n_solved = len(paths)
    makespan = max((len(p) - 1 for p in paths.values()), default=0)
    soc = sum(len(p) - 1 for p in paths.values())
    print(f"  {name:20s}: solved={n_solved}/{len(agents)}  makespan={makespan}  SoC={soc}  time={dt*1000:.1f}ms")
    return paths

algos = [PrioritizedPlanning(), CBS(), CBS_SIPP(), PBS()]

print("=" * 60)
print("Test 1: 10x10, 8 agents, 20% obstacles")
print("=" * 60)
g = Grid(width=10, height=10, obstacle_ratio=0.2)
cells = g.largest_component_cells()
import random
random.seed(42)
agents = []
used = set()
for i in range(8):
    start = random.choice([c for c in cells if c not in used])
    goal = random.choice([c for c in cells if c != start and c not in used])
    used.add(start)
    used.add(goal)
    agents.append(Agent(i, start, goal))

for algo in algos:
    test_algo(algo.name, algo, g, agents)

print()
print("=" * 60)
print("Test 2: 20x20, 15 agents, 25% obstacles")
print("=" * 60)
g2 = Grid(width=20, height=20, obstacle_ratio=0.25)
cells2 = g2.largest_component_cells()
random.seed(99)
agents2 = []
used2 = set()
for i in range(15):
    start = random.choice([c for c in cells2 if c not in used2])
    goal = random.choice([c for c in cells2 if c != start and c not in used2])
    used2.add(start)
    used2.add(goal)
    agents2.append(Agent(i, start, goal))

for algo in algos:
    test_algo(algo.name, algo, g2, agents2)

print()
print("=" * 60)
print("Test 3: 20x20, 30 agents, 30% obstacles")
print("=" * 60)
g3 = Grid(width=20, height=20, obstacle_ratio=0.30)
cells3 = g3.largest_component_cells()
random.seed(7)
agents3 = []
used3 = set()
for i in range(30):
    start = random.choice([c for c in cells3 if c not in used3])
    goal = random.choice([c for c in cells3 if c != start and c not in used3])
    used3.add(start)
    used3.add(goal)
    agents3.append(Agent(i, start, goal))

for algo in algos:
    test_algo(algo.name, algo, g3, agents3)

print()
print("All tests done!")