from __future__ import annotations
from dataclasses import dataclass, field
from ir.cfg.cfg import CFGBlock, CFGFunction

@dataclass
class LoopNode:
    blocks: set[CFGBlock]
    childs: set[LoopNode] = field(default_factory=set)

    def __hash__(self):
        hashed = 0
        for block in self.blocks:
            hashed ^= hash(block)
            
        for loop in self.childs:
            hashed ^= hash(loop)
            
        return hashed
    
    def __str__(self) -> str:
        return f"loop_node(childs={len(self.childs)},blocks={len(self.blocks)})"
            
def build_block_index(func: CFGFunction) -> dict[int, CFGBlock]:
    return {block.id: block for block in func.blocks}

def find_natural_loop(
    header_id: int,
    back_id: int,
    block_map: dict[int, CFGBlock]
) -> set[CFGBlock]:
    header = block_map[header_id]
    back   = block_map[back_id]

    loop_blocks: set[CFGBlock] = {header}
    stack: list[CFGBlock] = [back]

    while stack:
        b = stack.pop()
        if b not in loop_blocks:
            loop_blocks.add(b)
            for pid in b.pred:
                if pid != header_id:
                    stack.append(block_map[pid])

    return loop_blocks

def generate_loop_tree(funcs: list[CFGFunction]) -> list[LoopNode]:
    all_loops: list[LoopNode] = []

    for func in funcs:
        block_map = build_block_index(func)

        for b in func.blocks:
            for succ_id in b.succ:
                if succ_id in b.dom:
                    blocks = find_natural_loop(
                        header_id=succ_id,
                        back_id=b.id,
                        block_map=block_map
                    )

                    all_loops.append(LoopNode(blocks=blocks))

    roots: list[LoopNode] = []

    for loop in all_loops:
        parent = None

        for other in all_loops:
            if loop is other:
                continue

            if loop.blocks < other.blocks:
                if parent is None or other.blocks < parent.blocks:
                    parent = other

        if parent:
            parent.childs.add(loop)
        else:
            roots.append(loop)

    return roots

def find_loop(block: CFGBlock, loops: list[LoopNode]) -> LoopNode | None:
    def _dfs(node: LoopNode) -> LoopNode | None:
        if block not in node.blocks:
            return None

        for child in node.childs:
            res = _dfs(child)
            if res is not None:
                return res

        return node

    for root in loops:
        res = _dfs(root)
        if res is not None:
            return res

    return None
