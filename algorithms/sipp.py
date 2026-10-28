from algorithms.cbs import CBS


class CBS_SIPP(CBS):
    """
    CBS-SIPP: CBS 框架 + 安全区间低层。

    当前低层使用时空 A*（与 CBS 相同），保证正确性和稳定性。
    SIPP 低层规划利用安全区间（Safe Intervals）跳过不可行时间步，
    理论上比时空 A* 更快。完整 SIPP 低层实现待后续补充。

    name = "CBS-SIPP"
    """

    name = "CBS-SIPP"