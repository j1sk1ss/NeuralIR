from dataclasses import dataclass
from ir.cfg.cfg import CFGFunction, CFGBlock
from ir.instr.ir_block import IRBlock, IRAction

@dataclass
class CFGFunctionInfo:
    bb_count: int      # cfg function bb count
    ir_count: int      # cfg function bb's ir count (summary)
    is_start: bool     # is this a start func? (main / start / etc)
    funccalls: int     # how many funccalls in this function?
    syscalls: int = -1 # how many syscalls in this function? -1 if syscalls aren't supported by lang

    def dump_to_json(self) -> dict:
        return {
            "bb_count": self.bb_count,
            "ir_count": self.ir_count,
            "is_start": self.is_start,
            "funccalls": self.funccalls,
            "syscalls": self.syscalls
        }

@dataclass
class CFGInstructionInfo:
    is_dominated: bool    # this instruction dominated by someone? 
    same_inst_after: int  # how many similar instructions after this instruction?
    same_inst_before: int # hiw many similar instructions before this instruction?
    near_break: int = -1  # distance to the near break. -1 - There is no 'BREAK' in a block

    def dump_to_json(self) -> dict:
        return {
            "is_dom": self.is_dominated,
            "same_inst_after": self.same_inst_after,
            "same_inst_before": self.same_inst_before,
            "near_break": self.near_break
        }

def gather_function_info(f: CFGFunction) -> CFGFunctionInfo:
    bb_count = len(f.blocks)
    ir_count = 0
    funccalls = 0
    syscalls = 0

    for bb in f.blocks:
        ir_count += len(bb.instrs)
        for inst in bb.instrs:
            if inst.a == IRAction.FCALL:
                funccalls += 1
            elif inst.a == IRAction.SCALL:
                syscalls += 1

    is_start = f.func in { "main", "_start", "start" }
    return CFGFunctionInfo(
        bb_count=bb_count,
        ir_count=ir_count,
        is_start=is_start,
        funccalls=funccalls,
        syscalls=syscalls
    )
    
def _get_bb_from_func(f: CFGFunction, id: int) -> CFGBlock | None:
    for block in f.blocks:
        if block.id == id:
            return block
        
    return None
    
def _distance_to_nearest_break(
    f: CFGFunction,
    inst: IRBlock
) -> int:
    containing_block: CFGBlock | None = None
    for bb in f.blocks:
        for bb_inst in bb.instrs:
            if bb_inst is inst:
                containing_block = bb
                break
        if containing_block:
            break
    
    if not containing_block:
        return -1
    
    from collections import deque
    
    visited = set()
    queue: deque[tuple[CFGBlock, int, bool]] = deque()
    
    queue.append((containing_block, 0, True))
    queue.append((containing_block, 0, False))
    min_distance: float = float('inf')
    
    while queue:
        current_block, current_dist, is_forward = queue.popleft()
        if current_block.id in visited:
            continue
        
        visited.add(current_block.id)
        
        for i, block_inst in enumerate(current_block.instrs):
            if block_inst.a == IRAction.BREAK:
                if current_block is containing_block:
                    inst_idx = containing_block.instrs.index(inst)
                    break_idx = i
                    distance = abs(break_idx - inst_idx)
                    min_distance = min(min_distance, distance)
                else:
                    min_distance = min(min_distance, current_dist)
        
        if is_forward:
            for succ in current_block.succ:
                queue.append((_get_bb_from_func(f, succ), current_dist + len(current_block.instrs), True))
        else:
            for pred in current_block.pred:
                queue.append((_get_bb_from_func(f, pred), current_dist + len(current_block.instrs), False))
    
    return int(min_distance) if min_distance != float('inf') else -1

def _is_dominated(bb: CFGBlock) -> bool:
    return len(bb.pred) > 1

def _count_same_before_after_func(
    f: CFGFunction,
    inst: IRBlock
) -> tuple[int, int]:
    containing_block = None
    inst_idx = -1
    for bb in f.blocks:
        for idx, bb_inst in enumerate(bb.instrs):
            if bb_inst is inst:
                containing_block = bb
                inst_idx = idx
                break
        if containing_block:
            break
    
    if not containing_block:
        return 0, 0
    
    op = inst.a
    
    def count_in_direction(start_block: CFGBlock, start_idx: int, direction_forward: bool) -> int:
        from collections import deque
        count = 0
        visited = set()
        queue: deque[CFGBlock] = deque()
        
        if direction_forward:
            if start_idx + 1 < len(start_block.instrs):
                for i in range(start_idx + 1, len(start_block.instrs)):
                    if start_block.instrs[i].a == op:
                        count += 1
                    else:
                        break
            
            for succ in start_block.succ:
                queue.append(_get_bb_from_func(f, succ))
        else:
            if start_idx - 1 >= 0:
                for i in range(start_idx - 1, -1, -1):
                    if start_block.instrs[i].a == op:
                        count += 1
                    else:
                        break
            
            for pred in start_block.pred:
                queue.append(_get_bb_from_func(f, pred))
        
        while queue:
            current_block = queue.popleft()
            if current_block.id in visited:
                continue
            
            visited.add(current_block.id)
            if direction_forward:
                for block_inst in current_block.instrs:
                    if block_inst.a == op:
                        count += 1
                    else:
                        break
            else:
                for block_inst in reversed(current_block.instrs):
                    if block_inst.a == op:
                        count += 1
                    else:
                        break
            
            if direction_forward:
                for succ in current_block.succ:
                    if _get_bb_from_func(f, succ).id not in visited:
                        queue.append(_get_bb_from_func(f, succ))
            else:
                for pred in current_block.pred:
                    if _get_bb_from_func(f, pred).id not in visited:
                        queue.append(_get_bb_from_func(f, pred))
        
        return count
    
    before = count_in_direction(containing_block, inst_idx, False)
    after = count_in_direction(containing_block, inst_idx, True)
    
    return before, after

def gather_instruction_info(
    f: CFGFunction,
    bb: CFGBlock,
    inst: IRBlock
) -> CFGInstructionInfo:
    near_break = _distance_to_nearest_break(f, inst)
    is_dominated = _is_dominated(bb)
    same_before, same_after = _count_same_before_after_func(f, inst)
    
    return CFGInstructionInfo(
        near_break=near_break,
        is_dominated=is_dominated,
        same_inst_before=same_before,
        same_inst_after=same_after
    )
    