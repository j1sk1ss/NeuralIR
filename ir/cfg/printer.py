from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Any

def _escape_dot(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
         .replace("{", "\\{")
         .replace("}", "\\}")
         .replace("|", "\\|")
         .replace("<", "\\<")
         .replace(">", "\\>")
         .replace('"', '\\"')
    )

def cfg_to_dot(
    blocks: list[Any],
    *,
    graph_name: str = "CFG",
    show_instrs: bool = True,
    max_instrs: int = 25,
    prefer_succ: bool = True,
) -> str:
    by_id = {}
    for b in blocks:
        by_id[getattr(b, "id", id(b))] = b

    lines: list[str] = []
    lines.append(f'digraph {graph_name} {{')
    lines.append('  rankdir=TB;')
    lines.append('  node [shape=box, fontname="Consolas", fontsize=10];')
    lines.append('  edge [fontname="Consolas", fontsize=9];')

    for b in blocks:
        bid = getattr(b, "id", id(b))
        func = getattr(b, "func", "")
        start = getattr(b, "start", None)
        end = getattr(b, "end", None)

        header = f"B{bid}"
        meta = []
        if func:
            meta.append(f"func: {func}")
        if start is not None or end is not None:
            meta.append(f"range: {start}..{end}")

        instrs_txt = ""
        if show_instrs:
            instrs = getattr(b, "instrs", []) or []
            shown = instrs[:max_instrs]
            instr_lines = [str(x) for x in shown]
            if len(instrs) > max_instrs:
                instr_lines.append(f"... (+{len(instrs) - max_instrs})")
            
            if instr_lines:
                instrs_txt = "instrs:\\l" + "\\l".join(instr_lines) + "\\l"

        label_parts = [header]
        if meta:
            label_parts.append("\\l".join(meta) + "\\l")
        if instrs_txt:
            label_parts.append(instrs_txt)

        label = _escape_dot("\\l".join(label_parts) + "\\l")
        lines.append(f'  "B{bid}" [label="{label}"];')

    def add_edge(src_id: int, dst_id: int, label: str | None = None):
        if label:
            lines.append(f'  "B{src_id}" -> "B{dst_id}" [label="{_escape_dot(label)}"];')
        else:
            lines.append(f'  "B{src_id}" -> "B{dst_id}";')

    for b in blocks:
        src = getattr(b, "id", id(b))

        succ = getattr(b, "succ", None)
        used_any = False

        if prefer_succ and succ:
            for k, dsts in succ.items():
                for dst in dsts:
                    add_edge(src, dst, label=f"succ:{k}")
                    used_any = True

        should_draw_jmp_lin = (not prefer_succ) or (not used_any)

        if should_draw_jmp_lin:
            jmp = getattr(b, "jmp", None)
            lin = getattr(b, "lin", None)

            if jmp is not None:
                dst = getattr(jmp, "id", id(jmp))
                add_edge(src, dst, label="jmp")
            if lin is not None:
                dst = getattr(lin, "id", id(lin))
                add_edge(src, dst, label="lin")

        if (not prefer_succ) and succ:
            for k, dsts in succ.items():
                for dst in dsts:
                    add_edge(src, dst, label=f"succ:{k}")

    lines.append("}")
    return "\n".join(lines)
