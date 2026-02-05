from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from ir.instr.ir_block import IRBlock, IRAction

@dataclass
class PrintStyle:
    indent: str = "    "
    brace_same_line: bool = True
    show_index: bool = False
    show_bb_header: bool = True

def _fmt_block(b: IRBlock) -> str:
    return str(b)

def pretty_print_ir(
    blocks: Sequence[IRBlock],
    *,
    style: PrintStyle = PrintStyle(),
) -> str:
    OPENERS = {
        IRAction.IF,
        IRAction.LOOP,
        IRAction.SWITCH,
        IRAction.FDECL,
    }
    
    CLOSERS = {
        IRAction.FEND,
        IRAction.TERM,
    }

    lines: list[str] = []
    level = 0

    def emit(line: str) -> None:
        prefix = style.indent * level
        lines.append(prefix + line)

    for i, b in enumerate(blocks):
        a = b.a
        if a in CLOSERS:
            if level > 0:
                level -= 1
                emit("}")
            
            line = _fmt_block(b)
            if style.show_index:
                line = f"[{i}] " + line
            emit(line)
            continue

        if a == IRAction.BB and style.show_bb_header:
            if lines:
                lines.append("")
            
            bb_id = getattr(b, "id", None)
            hdr = f"bb{bb_id}:" if bb_id is not None else "bb:"
            if style.show_index:
                hdr = f"[{i}] " + hdr
            emit(hdr)
            continue

        line = _fmt_block(b)
        if style.show_index:
            line = f"[{i}] " + line

        if a in OPENERS:
            if style.brace_same_line:
                emit(line + " {")
            else:
                emit(line)
                emit("{")
            level += 1
        else:
            emit(line)

    while level > 0:
        level -= 1
        emit("}")

    return "\n".join(lines)
