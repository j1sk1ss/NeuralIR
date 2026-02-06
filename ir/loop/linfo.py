from dataclasses import dataclass
from ir.loop.ltree import LoopNode

@dataclass
class LoopInfo:
    loop_size_bb: int
    loop_size_ir: int
    loop_nested: int

def gather_loop_info(loops: list[LoopNode], trg: LoopNode) -> LoopInfo:
    def _dfs(node: LoopNode, depth: int) -> LoopInfo | None:
        if node is trg:
            bb_count = len(node.blocks)
            ir_count = sum(len(bb.instrs) for bb in node.blocks)

            return LoopInfo(
                loop_size_bb=bb_count,
                loop_size_ir=ir_count,
                loop_nested=depth
            )

        for child in node.childs:
            res = _dfs(child, depth + 1)
            if res is not None:
                return res

        return None

    for root in loops:
        info = _dfs(root, 0)
        if info is not None:
            return info

    return None
