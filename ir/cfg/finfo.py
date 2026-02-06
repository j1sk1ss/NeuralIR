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

@dataclass
class CFGInstructionInfo:
    is_dominated: bool    # this instruction dominated by someone? 
    same_inst_after: int  # how many similar instructions after this instruction?
    same_inst_before: int # hiw many similar instructions before this instruction?
    near_break: int = -1  # distance to the near break. -1 - There is no 'BREAK' in a block

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

def _flatten_function(f: CFGFunction) -> list[IRBlock]:
    instrs: list[IRBlock] = []
    for bb in f.blocks:
        instrs.extend(bb.instrs)
    return instrs

def _distance_to_nearest_break( # TODO: Find a break based on CFG over than linear instructions
    f: CFGFunction,
    inst: IRBlock
) -> int:
    instrs: list[IRBlock] = []
    for bb in f.blocks:
        instrs.extend(bb.instrs)

    try:
        idx = instrs.index(inst)
    except ValueError:
        return -1

    distances: list[int] = []
    for i in range(idx - 1, -1, -1):
        if instrs[i].a == IRAction.BREAK:
            distances.append(idx - i)
            break

    for i in range(idx + 1, len(instrs)):
        if instrs[i].a == IRAction.BREAK:
            distances.append(i - idx)
            break

    return min(distances) if distances else -1

def _is_dominated(bb: CFGBlock) -> bool:
    return len(bb.pred) > 1

def _count_same_before_after_func(
    f: CFGFunction,
    inst: IRBlock
) -> tuple[int, int]:
    instrs = _flatten_function(f)

    try:
        idx = instrs.index(inst)
    except ValueError:
        return 0, 0

    op = inst.a

    before = 0
    for i in range(idx - 1, -1, -1):
        if instrs[i].a == op:
            before += 1
        else:
            break

    after = 0
    for i in range(idx + 1, len(instrs)):
        if instrs[i].a == op:
            after += 1
        else:
            break

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
        near_break=near_break,        # FIXME
        is_dominated=is_dominated,    # FIXME
        same_inst_before=same_before, # FIXME
        same_inst_after=same_after    # FIXME
    )
