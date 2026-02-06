from ir.cfg.cfg import CFGBlock, CFGFunction
from ir.instr.ir_block import (
    IRBlock, IRAction, IRLabel, IRFunction, IRBaseBlockLabel
)

def _split_by_function(instructions: list[IRBlock]) -> dict[str, list[IRBlock]]:
    output: dict[str, list[IRBlock]] = {}

    cur: list[IRBlock] = []
    cur_func: IRFunction | None = None

    for inst in instructions:
        if inst.a == IRAction.FDECL:
            if cur_func is not None:
                output[cur_func.name] = cur

            cur_func = inst.subjects[0]
            cur = []
            continue

        cur.append(inst)

    if cur_func is not None:
        output[cur_func.name] = cur

    return output

_global_func_id: int = 0
_global_block_id: int = 0

def get_blocks_from_ir(instructions: list[IRBlock]) -> list[CFGFunction]:
    global _global_block_id, _global_func_id
    output: list[CFGFunction] = []
    prepared: dict[str, list[IRBlock]] = _split_by_function(instructions=instructions)

    for fname, instrs in prepared.items():
        func = CFGFunction(id=_global_func_id, func=fname, blocks=[])
        output.append(func)
        _global_func_id += 1

        if not instrs:
            continue

        current_block: list[IRBlock] = []
        start_idx = 0
        
        for idx, inst in enumerate(instrs):
            if idx == 0 or inst.a == IRAction.MKLB:
                if current_block:
                    func.blocks.append(CFGBlock(
                        id=_global_block_id,
                        start=start_idx,
                        end=idx - 1,
                        instrs=current_block.copy()
                    ))
                    _global_block_id += 1
                    current_block.clear()
                
                start_idx = idx
            
            current_block.append(inst)
            
            if inst.a in {IRAction.JMP, IRAction.IF} or (idx + 1 < len(instrs) and instrs[idx + 1].a == IRAction.MKLB):
                func.blocks.append(CFGBlock(
                    id=_global_block_id,
                    start=start_idx,
                    end=idx,
                    instrs=current_block.copy()
                ))
                _global_block_id += 1
                current_block.clear()
        
        if current_block:
            func.blocks.append(CFGBlock(
                id=_global_block_id,
                start=start_idx,
                end=len(instrs) - 1,
                instrs=current_block.copy()
            ))
            _global_block_id += 1

    return output

def _find_labeled_block(blocks: list[CFGBlock], label: IRLabel) -> CFGBlock | None:
    for block in blocks:
        if not block.instrs:
            continue
        first = block.instrs[0]
        if isinstance(first, IRBaseBlockLabel):
            first = block.instrs[1]
        if first.a == IRAction.MKLB and first.subjects and first.subjects[0] == label:
            return block
    return None

def link_blocks(funcs: list[CFGFunction]) -> None:
    for func in funcs:
        for b in func.blocks:
            b.jmp = None
            b.lin = None

        for i, block in enumerate(func.blocks):
            if not block.instrs:
                if i + 1 < len(func.blocks):
                    block.lin = func.blocks[i + 1]
                continue

            last = block.instrs[-1]

            if last.a == IRAction.JMP:
                block.jmp = _find_labeled_block(func.blocks, last.subjects[0])
            elif last.a == IRAction.IF:
                block.lin = _find_labeled_block(func.blocks, last.subjects[0])
                block.jmp = _find_labeled_block(func.blocks, last.subjects[1])
            elif last.a not in { IRAction.TERM, IRAction.FEND } and i + 1 < len(func.blocks):
                block.lin = func.blocks[i + 1]
                
            block.instrs.insert(0, IRBaseBlockLabel(block.id))
            
def give_flatten_instructions(f: CFGFunction) -> list[IRBlock]:
    instrs: list[IRBlock] = []
    for bb in f.blocks:
        instrs.extend(bb.instrs)
    return instrs
            