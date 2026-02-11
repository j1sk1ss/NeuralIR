from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from ir.instr.ir_block import IRBlock, IRAction, IRBaseBlockLabel

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

    index_width = len(str(len(blocks))) 

    def emit(line: str, idx: int | None = None) -> None:
        prefix = style.indent * level
        index_str = f"[{idx:{index_width}d}] " if idx is not None else " " * (index_width + 3)
        lines.append(index_str + prefix + line)

    def action_friendly(b: IRBlock) -> str:
        a, subs = b.a, b.subjects
        if a == IRAction.FDECL and subs[0]:
            return f"define {subs[0]}"
        if a == IRAction.IF:
            return f"if, true: {subs[0]}, else: {subs[1]})"
        if a == IRAction.LOOP:
            return f"loop untill"
        if a == IRAction.SWITCH and subs[0]:
            return f"switch by"
        if a == IRAction.BINOP and subs[0]:
            return f"binary_op"
        if a == IRAction.UNARY and subs[0]:
            return f"unary_op"
        if a == IRAction.DECL and subs[0]:
            return f"declaration({subs[0]})"
        if a == IRAction.FCALL and subs[0]:
            return f"call {subs[0]}()"
        if a == IRAction.SCALL and subs[0]:
            return f"syscall"
        if a == IRAction.JMP and subs[0]:
            return f"jump to {subs[0]}"
        if a == IRAction.BREAK:
            return "break"
        if a == IRAction.DREF and subs[0]:
            return f"dereference of something"
        if a == IRAction.REF and subs[0]:
            return f"reference of something"
        if a == IRAction.MKLB and subs[0]:
            return f"{subs[0]}:"
        if a == IRAction.BB:
            return f"BB({getattr(b, 'id', '?')})"
        if a == IRAction.TERM:
            return "stop"
        if a == IRAction.FEND:
            return "function_end"
        if a == IRAction.NOTHING:
            return "some operation"
        return str(a)

    action_comment_map = {
    }

    for i, b in enumerate(blocks):
        a = b.a

        if a in CLOSERS:
            if level > 0:
                level -= 1
                emit("}")
            
            line = action_friendly(b)
            emit(f"{line} {action_comment_map.get(a,'')}", idx=i)
            continue

        if isinstance(b, IRBaseBlockLabel) and style.show_bb_header:
            if lines:
                lines.append("")
            hdr = f"===== BB{b.id} ====="
            emit(f"{hdr}")
            continue

        line = action_friendly(b)
        if a in OPENERS:
            if style.brace_same_line:
                emit(f"{line} {{ {action_comment_map.get(a,'')}", idx=i)
            else:
                emit(f"{line} {action_comment_map.get(a,'')}", idx=i)
                emit("{")
            level += 1
        else:
            emit(f"{line} {action_comment_map.get(a,'')}", idx=i)

    while level > 0:
        level -= 1
        emit("}")

    return "\n".join(lines)

