from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from grid import Grid, Cell
from agent import Agent


class MAPFAlgorithm(ABC):
    """MAPF 算法基类。所有算法都必须实现 solve 方法。"""

    name: str = "base"

    @abstractmethod
    def solve(self, grid: Grid, agents: List[Agent]) -> Dict[int, List[Cell]]:
        """
        求解所有智能体的路径。

        Returns:
            Dict[int, List[Cell]]: key 是 agent_id，value 是从起点到终点的路径（包含起点和终点）
                                   如果某个智能体无解，可以不包含它或返回空列表。
        """
        ...