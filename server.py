import asyncio
import json
import random
from typing import Optional, Set, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from grid import Grid, Cell
from agent import Agent
from simulator import Simulator
from algorithms.base import MAPFAlgorithm
from main import discover_algorithms, create_agents as _create_agents


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


DEFAULT_COLORS = [
    (231, 76, 60), (52, 152, 219), (46, 204, 113), (241, 196, 15),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (142, 168, 209),
    (255, 105, 180), (178, 34, 34), (0, 139, 139), (218, 165, 32),
    (127, 255, 212), (255, 165, 0), (199, 21, 133), (70, 130, 180),
]


def _pick_starts(grid: Grid, num: int, seed: int) -> List[Cell]:
    rng = random.Random(seed)
    cells = grid.largest_component_cells()
    n = min(num, len(cells))
    return rng.sample(cells, n)


def _pick_goals(grid: Grid, starts: List[Cell], num: int, seed: int) -> List[Cell]:
    rng = random.Random(seed)
    cells = grid.largest_component_cells()
    remaining = [c for c in cells if c not in starts]
    n = min(num, len(remaining))
    if n == 0:
        n = min(num, len(cells))
        remaining = cells
    return rng.sample(remaining, n)


def _make_agents(starts: List[Cell], goals: List[Cell]) -> List[Agent]:
    agents = []
    for i in range(min(len(starts), len(goals))):
        agents.append(Agent(
            agent_id=i,
            start=starts[i],
            goal=goals[i],
            color=DEFAULT_COLORS[i % len(DEFAULT_COLORS)],
        ))
    return agents


class Session:
    def __init__(self):
        self.grid: Optional[Grid] = None
        self.agents: list[Agent] = []
        self.sim: Optional[Simulator] = None
        self.algos: dict[str, type[MAPFAlgorithm]] = {}
        self.config = {
            "width": 20,
            "height": 20,
            "obstacle_ratio": 0.20,
            "num_agents": 5,
            "algo": "Prioritized Planning",
            "obstacle_seed": random.randint(0, 100000),
            "start_seed": random.randint(0, 100000),
            "goal_seed": random.randint(0, 100000),
        }
        self._lock = asyncio.Lock()
        self._init_sync()

    def _init_sync(self):
        self.algos = discover_algorithms()
        cfg = self.config
        algo_cls = self.algos.get(cfg["algo"], list(self.algos.values())[0])
        cfg["algo"] = algo_cls().name
        self.grid = Grid(cfg["width"], cfg["height"], cfg["obstacle_ratio"],
                         seed=cfg["obstacle_seed"])
        starts = _pick_starts(self.grid, cfg["num_agents"], cfg["start_seed"])
        goals = _pick_goals(self.grid, starts, cfg["num_agents"], cfg["goal_seed"])
        self.agents = _make_agents(starts, goals)
        self.sim = Simulator(self.grid, self.agents, algo_cls())
        self.sim.plan()

    def _build_grid(self):
        cfg = self.config
        self.grid = Grid(cfg["width"], cfg["height"], cfg["obstacle_ratio"],
                         seed=cfg["obstacle_seed"])

    def _build_agents(self):
        cfg = self.config
        starts = _pick_starts(self.grid, cfg["num_agents"], cfg["start_seed"])
        goals = _pick_goals(self.grid, starts, cfg["num_agents"], cfg["goal_seed"])
        self.agents = _make_agents(starts, goals)

    def _new_sim(self):
        cfg = self.config
        algo_cls = self.algos.get(cfg["algo"], list(self.algos.values())[0])
        cfg["algo"] = algo_cls().name
        self.sim = Simulator(self.grid, self.agents, algo_cls())

    def _reset_all_sync(self):
        self._build_grid()
        self._build_agents()
        self._new_sim()

    def _reset_plan_sync(self):
        self._build_grid()
        self._build_agents()
        self._new_sim()

    async def plan_async(self) -> dict:
        async with self._lock:
            self._reset_plan_sync()
            await asyncio.to_thread(self.sim.plan)
            return self.state_snapshot()

    def state_snapshot(self) -> dict:
        g = self.grid
        s = self.sim
        comp_map = g.connected_components()
        num_comps = len(set(comp_map.values())) if comp_map else 0
        free_count = len(comp_map)

        agent_list = []
        for a in self.agents:
            path_cells = [{"x": c.x, "y": c.y} for c in a.path] if a.path else []
            agent_list.append({
                "id": a.agent_id,
                "start": {"x": a.start.x, "y": a.start.y},
                "goal": {"x": a.goal.x, "y": a.goal.y},
                "color": list(a.color),
                "path": path_cells,
                "pathLength": len(path_cells),
                "done": a.is_done(),
                "currentStep": a.current_step,
            })

        obs_list = [{"x": c.x, "y": c.y} for c in g.obstacles]

        soc = sum(a.path_length() for a in self.agents)
        makespan = s.makespan() if s else 0

        return {
            "grid": {
                "width": g.width,
                "height": g.height,
                "obstacles": obs_list,
                "obstacleRatio": g.obstacle_ratio,
                "freeCells": free_count,
                "components": num_comps,
            },
            "simulation": {
                "algorithm": s.algorithm.name if s else "",
                "solved": s.solved if s else False,
                "makespan": makespan,
                "totalPathLength": soc,
                "totalCost": soc,
                "step": s.step if s else 0,
                "conflicts": list(s.conflicts) if s else [],
            },
            "agents": agent_list,
            "config": dict(self.config),
            "algorithms": list(self.algos.keys()),
        }

    async def step_to_async(self, t: int):
        async with self._lock:
            self.sim.set_step(t)

    async def reset_steps_async(self):
        async with self._lock:
            self.sim.set_step(0)


session = Session()


class UpdateConfig(BaseModel):
    width: Optional[int] = None
    height: Optional[int] = None
    obstacle_ratio: Optional[float] = None
    num_agents: Optional[int] = None
    algo: Optional[str] = None
    obstacle_seed: Optional[int] = None
    start_seed: Optional[int] = None
    goal_seed: Optional[int] = None


class StepRequest(BaseModel):
    step: int


@app.get("/api/state")
async def get_state():
    return session.state_snapshot()


@app.get("/api/algorithms")
async def list_algorithms():
    return {"algorithms": list(session.algos.keys())}


@app.post("/api/configure")
async def configure(cfg: UpdateConfig):
    async with session._lock:
        if cfg.width is not None:
            session.config["width"] = max(5, min(80, cfg.width))
        if cfg.height is not None:
            session.config["height"] = max(5, min(80, cfg.height))
        if cfg.obstacle_ratio is not None:
            session.config["obstacle_ratio"] = max(0.0, min(0.6, round(cfg.obstacle_ratio, 3)))
        if cfg.num_agents is not None:
            session.config["num_agents"] = max(1, min(60, cfg.num_agents))
        if cfg.algo is not None and cfg.algo in session.algos:
            session.config["algo"] = cfg.algo
        if cfg.obstacle_seed is not None:
            session.config["obstacle_seed"] = cfg.obstacle_seed
        if cfg.start_seed is not None:
            session.config["start_seed"] = cfg.start_seed
        if cfg.goal_seed is not None:
            session.config["goal_seed"] = cfg.goal_seed
        session._reset_plan_sync()
        await asyncio.to_thread(session.sim.plan)
    return session.state_snapshot()


@app.post("/api/plan")
async def plan():
    return await session.plan_async()


@app.post("/api/step")
async def step(req: StepRequest):
    await session.step_to_async(req.step)
    return session.state_snapshot()


@app.post("/api/reset-steps")
async def reset_steps():
    await session.reset_steps_async()
    return session.state_snapshot()


connections: Set[WebSocket] = set()


async def broadcast():
    global connections
    if not connections:
        return
    data = session.state_snapshot()
    msg = json.dumps(data)
    dead = set()
    for ws in list(connections):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    connections -= dead


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global connections
    await ws.accept()
    connections.add(ws)
    print(f"[WS] connected, total={len(connections)}")
    try:
        await ws.send_text(json.dumps(session.state_snapshot()))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action")
                print(f"[WS] got action={action}")

                if action == "plan":
                    cfg = msg.get("config", {})
                    async with session._lock:
                        if "width" in cfg:
                            session.config["width"] = max(5, min(80, int(cfg["width"])))
                        if "height" in cfg:
                            session.config["height"] = max(5, min(80, int(cfg["height"])))
                        if "obstacle_ratio" in cfg:
                            session.config["obstacle_ratio"] = max(0.0, min(0.6, float(cfg["obstacle_ratio"])))
                        if "num_agents" in cfg:
                            session.config["num_agents"] = max(1, min(60, int(cfg["num_agents"])))
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                    await session.plan_async()
                    await broadcast()

                elif action == "step":
                    await session.step_to_async(msg.get("step", 0))
                    await broadcast()

                elif action == "reset-steps":
                    await session.reset_steps_async()
                    await broadcast()

                elif action == "regen-obstacles":
                    cfg = msg.get("config", {})
                    async with session._lock:
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                        session.config["obstacle_seed"] = random.randint(0, 100000)
                        session._build_grid()
                        session._build_agents()
                        session._new_sim()
                    await broadcast()

                elif action == "regen-starts":
                    cfg = msg.get("config", {})
                    async with session._lock:
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                        session.config["start_seed"] = random.randint(0, 100000)
                        session._build_agents()
                        session._new_sim()
                    await broadcast()

                elif action == "regen-goals":
                    cfg = msg.get("config", {})
                    async with session._lock:
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                        session.config["goal_seed"] = random.randint(0, 100000)
                        session._build_agents()
                        session._new_sim()
                    await broadcast()

                elif action == "regen-all":
                    cfg = msg.get("config", {})
                    async with session._lock:
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                        session.config["obstacle_seed"] = random.randint(0, 100000)
                        session.config["start_seed"] = random.randint(0, 100000)
                        session.config["goal_seed"] = random.randint(0, 100000)
                        session._build_grid()
                        session._build_agents()
                        session._new_sim()
                    await broadcast()

                elif action == "configure":
                    cfg = msg.get("config", {})
                    print(f"[WS] configure cfg={cfg}")
                    async with session._lock:
                        if "width" in cfg:
                            session.config["width"] = max(5, min(80, int(cfg["width"])))
                        if "height" in cfg:
                            session.config["height"] = max(5, min(80, int(cfg["height"])))
                        if "obstacle_ratio" in cfg:
                            session.config["obstacle_ratio"] = max(0.0, min(0.6, float(cfg["obstacle_ratio"])))
                        if "num_agents" in cfg:
                            session.config["num_agents"] = max(1, min(60, int(cfg["num_agents"])))
                        if "algo" in cfg and cfg["algo"] in session.algos:
                            session.config["algo"] = cfg["algo"]
                        if cfg.get("newSeed"):
                            session.config["obstacle_seed"] = random.randint(0, 100000)
                            session.config["start_seed"] = random.randint(0, 100000)
                            session.config["goal_seed"] = random.randint(0, 100000)
                        session._reset_plan_sync()
                    print(f"[WS] configure done (no auto-plan)")
                    await broadcast()

                else:
                    await ws.send_text(json.dumps(session.state_snapshot()))
            except Exception as e:
                import traceback
                print(f"[WS] error: {e}")
                traceback.print_exc()
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(ws)
        print(f"[WS] disconnected, total={len(connections)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)