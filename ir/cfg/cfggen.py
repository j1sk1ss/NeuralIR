from ir.cfg.cfg import CFGBlock
from ir.instr.ir_block import IRBlock, IRAction, IRLabel

def _split_by_function(instructions: list[IRBlock]) -> list[list[IRBlock]]:
    output: list[list[IRBlock]] = []
    cur: list[IRBlock] = []

    for inst in instructions:
        if inst.a == IRAction.FDECL:
            if cur:
                output.append(cur)
            cur = []
            continue
        cur.append(inst)

    if cur:
        output.append(cur)

    return output

_global_block_id: int = 0

def get_blocks_from_ir(instructions: list[IRBlock]) -> list[CFGBlock]:
    global _global_block_id

    output: list[CFGBlock] = []
    start_counter, end_counter = 0, 0

    prepared = _split_by_function(instructions=instructions)

    for func in prepared:
        block_instructions: list[IRBlock] = []

        for inst in func:
            end_counter += 1
            block_instructions.append(inst)

            if inst.a in { IRAction.JMP, IRAction.IF, IRAction.MKLB }:
                output.append(CFGBlock(
                    id=_global_block_id,
                    start=start_counter,
                    end=end_counter,
                    instrs=block_instructions.copy()
                ))
                
                _global_block_id += 1
                block_instructions.clear()
                start_counter = end_counter

        if block_instructions:
            output.append(CFGBlock(
                id=_global_block_id,
                start=start_counter,
                end=end_counter,
                instrs=block_instructions.copy()
            ))
            
            _global_block_id += 1
            block_instructions.clear()
            start_counter = end_counter

    return output

def _find_labeled_block(blocks: list[CFGBlock], label: IRLabel) -> CFGBlock | None:
    for block in blocks:
        if not block.instrs:
            continue
        first = block.instrs[0]
        if first.a == IRAction.MKLB and first.subjects and first.subjects[0] == label:
            return block
    return None

def link_blocks(blocks: list[CFGBlock]) -> None:
    for b in blocks:
        b.jmp = None
        b.lin = None

    for i, block in enumerate(blocks):
        if not block.instrs:
            if i + 1 < len(blocks):
                block.lin = blocks[i + 1]
            continue

        last = block.instrs[-1]

        if last.a == IRAction.JMP:
            block.jmp = _find_labeled_block(blocks, last.subjects[0])

        elif last.a == IRAction.IF:
            block.lin = _find_labeled_block(blocks, last.subjects[0])
            block.jmp = _find_labeled_block(blocks, last.subjects[1])

        elif last.a not in {IRAction.TERM, IRAction.FEND} and i + 1 < len(blocks):
            block.lin = blocks[i + 1]
            