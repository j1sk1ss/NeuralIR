from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from typing import Any

from pycparser import c_ast, c_generator
from funcextractor import (
    _parse_file,
    add_extra_define,
    add_include_dir,
    set_cpp_extra_args,
    set_cpp_path,
    set_fake_libc_path,
    set_fake_types_header,
)

GEN = c_generator.CGenerator()


def _norm(path: str | Path | None, project_root: Path) -> str | None:
    if path is None:
        return None
    p = Path(str(path))
    try:
        if p.is_absolute():
            return str(p.resolve().relative_to(project_root.resolve()))
        return str(p)
    except Exception:
        return str(p)


def _coord_dict(coord: Any, project_root: Path) -> dict[str, Any]:
    if coord is None:
        return {"file": None, "line": None, "column": None}
    return {
        "file": _norm(getattr(coord, "file", None), project_root),
        "line": getattr(coord, "line", None),
        "column": getattr(coord, "column", None),
    }


def _max_line(node: c_ast.Node | None) -> int | None:
    max_seen = None

    def walk(cur: c_ast.Node | None) -> None:
        nonlocal max_seen
        if cur is None:
            return
        coord = getattr(cur, "coord", None)
        line = getattr(coord, "line", None)
        if isinstance(line, int):
            max_seen = line if max_seen is None else max(max_seen, line)
        for _, child in cur.children():
            walk(child)

    walk(node)
    return max_seen


def _get_decl_typename(type_node: c_ast.Node | None) -> str | None:
    if type_node is None:
        return None
    try:
        return GEN.visit(type_node)
    except Exception:
        return None


class FunctionAndCallCollector(c_ast.NodeVisitor):
    def __init__(self, tu_path: Path, project_root: Path):
        self.tu_path = tu_path
        self.project_root = project_root
        self.functions: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.function_stack: list[dict[str, Any]] = []
        self._function_seen_keys: set[tuple[Any, ...]] = set()
        self._call_index = 0
        self._function_index = 0

    def visit_FuncDef(self, node: c_ast.FuncDef) -> None:
        decl = node.decl
        coord = _coord_dict(decl.coord, self.project_root)
        end_line = _max_line(node)
        func_type = decl.type
        params = []
        arg_decls = getattr(func_type, "args", None)
        if arg_decls and getattr(arg_decls, "params", None):
            for param in arg_decls.params:
                if isinstance(param, c_ast.EllipsisParam):
                    params.append({"name": "...", "type": "..."})
                    continue
                params.append(
                    {
                        "name": getattr(param, "name", None),
                        "type": _get_decl_typename(param),
                    }
                )

        func_info = {
            "id": f"func_{self._function_index}",
            "name": decl.name,
            "file": coord["file"],
            "decl_line": coord["line"],
            "decl_column": coord["column"],
            "end_line": end_line,
            "translation_unit": _norm(self.tu_path, self.project_root),
            "storage": list(getattr(decl, "storage", []) or []),
            "qualifiers": list(getattr(decl, "quals", []) or []),
            "return_type": _get_decl_typename(getattr(func_type, "type", None)),
            "signature": _get_decl_typename(func_type),
            "params": params,
            "code": GEN.visit(node),
        }
        self._function_index += 1

        dedupe_key = (
            func_info["name"],
            func_info["file"],
            func_info["decl_line"],
            func_info["decl_column"],
        )
        if dedupe_key not in self._function_seen_keys:
            self._function_seen_keys.add(dedupe_key)
            self.functions.append(func_info)

        self.function_stack.append(func_info)
        self.visit(node.body)
        self.function_stack.pop()

    def visit_FuncCall(self, node: c_ast.FuncCall) -> None:
        caller = self.function_stack[-1] if self.function_stack else None
        call_coord = _coord_dict(node.coord, self.project_root)
        callee_name, callee_kind = self._resolve_callee(node.name)

        args_rendered: list[str | None] = []
        argc = 0
        if node.args and getattr(node.args, "exprs", None):
            for expr in node.args.exprs:
                argc += 1
                try:
                    args_rendered.append(GEN.visit(expr))
                except Exception:
                    args_rendered.append(None)

        try:
            call_expr = GEN.visit(node)
        except Exception:
            call_expr = None

        call_info = {
            "id": f"call_{self._call_index}",
            "file": call_coord["file"],
            "line": call_coord["line"],
            "column": call_coord["column"],
            "translation_unit": _norm(self.tu_path, self.project_root),
            "caller": caller["name"] if caller else None,
            "caller_file": caller["file"] if caller else None,
            "caller_decl_line": caller["decl_line"] if caller else None,
            "callee": callee_name,
            "callee_expr_kind": callee_kind,
            "expression": call_expr,
            "argc": argc,
            "args": args_rendered,
        }
        self._call_index += 1
        self.calls.append(call_info)

        self.generic_visit(node)

    def _resolve_callee(self, node: c_ast.Node | None) -> tuple[str | None, str]:
        if node is None:
            return None, "unknown"
        if isinstance(node, c_ast.ID):
            return node.name, "direct"
        if isinstance(node, c_ast.StructRef):
            try:
                return GEN.visit(node), "member"
            except Exception:
                return None, "member"
        if isinstance(node, c_ast.PtrDecl):
            try:
                return GEN.visit(node), "pointer"
            except Exception:
                return None, "pointer"
        if isinstance(node, c_ast.UnaryOp):
            try:
                return GEN.visit(node), "indirect"
            except Exception:
                return None, "indirect"
        if isinstance(node, c_ast.ArrayRef):
            try:
                return GEN.visit(node), "indirect"
            except Exception:
                return None, "indirect"
        try:
            return GEN.visit(node), type(node).__name__
        except Exception:
            return None, type(node).__name__


def _collect_translation_units(project_root: Path) -> list[Path]:
    exts = {".c"}
    tus = [p for p in project_root.rglob("*") if p.suffix.lower() in exts and p.is_file()]
    return sorted(set(p.resolve() for p in tus))


def _load_inline_calls(inline_json_paths: list[str], project_root: Path) -> tuple[set[tuple[Any, ...]], list[dict[str, Any]]]:
    matched_keys: set[tuple[Any, ...]] = set()
    raw_events: list[dict[str, Any]] = []

    for inline_json in inline_json_paths:
        path = Path(inline_json).resolve()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if isinstance(data.get("inlining_events"), list):
                events = data["inlining_events"]
            elif isinstance(data.get("calls"), list):
                events = data["calls"]
            else:
                events = []
        elif isinstance(data, list):
            events = data
        else:
            events = []

        for ev in events:
            if not isinstance(ev, dict):
                continue
            key = (
                _norm(ev.get("file"), project_root),
                ev.get("line"),
                ev.get("column"),
                ev.get("caller"),
                ev.get("callee"),
            )
            matched_keys.add(key)
            raw_events.append(
                {
                    "source_json": str(path),
                    "file": key[0],
                    "line": key[1],
                    "column": key[2],
                    "caller": key[3],
                    "callee": key[4],
                    "raw": ev.get("raw"),
                }
            )

    return matched_keys, raw_events


def extract_project_calls(project_root: Path, inline_json_paths: list[str] | None = None) -> dict[str, Any]:
    translation_units = _collect_translation_units(project_root)
    all_functions: list[dict[str, Any]] = []
    all_calls: list[dict[str, Any]] = []
    parse_failures: list[dict[str, str]] = []
    seen_functions: set[tuple[Any, ...]] = set()
    seen_calls: set[tuple[Any, ...]] = set()

    inline_call_keys: set[tuple[Any, ...]] = set()
    inline_events: list[dict[str, Any]] = []
    if inline_json_paths:
        inline_call_keys, inline_events = _load_inline_calls(inline_json_paths, project_root)

    removed_calls: list[dict[str, Any]] = []

    for tu in translation_units:
        ast = _parse_file(tu, project_root)
        if ast is None:
            parse_failures.append({"file": _norm(tu, project_root), "reason": "pycparser returned None"})
            continue

        collector = FunctionAndCallCollector(tu, project_root)
        collector.visit(ast)

        for fn in collector.functions:
            key = (fn["name"], fn["file"], fn["decl_line"], fn["decl_column"])
            if key not in seen_functions:
                seen_functions.add(key)
                all_functions.append(fn)

        for call in collector.calls:
            inline_key = (
                call["file"],
                call["line"],
                call["column"],
                call["caller"],
                call["callee"],
            )
            if inline_key in inline_call_keys:
                removed_calls.append(call)
                continue

            key = (
                call["file"],
                call["line"],
                call["column"],
                call["caller"],
                call["callee"],
                call["expression"],
            )
            if key not in seen_calls:
                seen_calls.add(key)
                all_calls.append(call)

    direct_calls = sum(1 for c in all_calls if c.get("callee_expr_kind") == "direct")
    unresolved_calls = sum(1 for c in all_calls if not c.get("callee"))

    return {
        "meta": {
            "project_root": str(project_root.resolve()),
            "translation_units_total": len(translation_units),
            "translation_units_parsed": len(translation_units) - len(parse_failures),
            "translation_units_failed": len(parse_failures),
            "functions_total": len(all_functions),
            "calls_total": len(all_calls),
            "direct_calls_total": direct_calls,
            "indirect_or_complex_calls_total": len(all_calls) - direct_calls,
            "unresolved_calls_total": unresolved_calls,
            "inline_json_inputs": [str(Path(p).resolve()) for p in (inline_json_paths or [])],
            "inline_events_loaded": len(inline_events),
            "calls_removed_by_inline_json": len(removed_calls),
        },
        "functions": sorted(
            all_functions,
            key=lambda x: (
                x.get("file") or "",
                x.get("decl_line") or -1,
                x.get("decl_column") or -1,
                x.get("name") or "",
            ),
        ),
        "calls": sorted(
            all_calls,
            key=lambda x: (
                x.get("file") or "",
                x.get("line") or -1,
                x.get("column") or -1,
                x.get("caller") or "",
            ),
        ),
        "removed_calls": sorted(
            removed_calls,
            key=lambda x: (
                x.get("file") or "",
                x.get("line") or -1,
                x.get("column") or -1,
                x.get("caller") or "",
            ),
        ),
        "inline_events": inline_events,
        "parse_failures": parse_failures,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract all function definitions and all function call sites from a C project. Optionally remove callsites present in inline JSON."
    )
    parser.add_argument("--project-root", required=True, help="Path to the C project root")
    parser.add_argument("--fake-libc", required=True, help="Path to pycparser fake_libc_include")
    parser.add_argument("--output-json", required=True, help="Where to write the resulting JSON")
    parser.add_argument(
        "--inline-json",
        action="append",
        default=[],
        help="JSON file with inlined calls to exclude from output. Can be repeated.",
    )
    parser.add_argument("--cpp-path", default="gcc", help="C preprocessor executable")
    parser.add_argument(
        "--cpp-arg",
        action="append",
        default=[],
        help="Extra argument for the preprocessor, can be repeated",
    )
    parser.add_argument(
        "--include-dir",
        action="append",
        default=[],
        help="Additional include directory, can be repeated",
    )
    parser.add_argument(
        "--define",
        action="append",
        default=[],
        help="Extra -D define, can be repeated",
    )
    parser.add_argument("--fake-types-header", default=None, help="Optional forced include header")
    return parser


def _main() -> int:
    args = _build_arg_parser().parse_args()

    project_root = Path(args.project_root).resolve()
    output_json = Path(args.output_json).resolve()

    if not project_root.is_dir():
        print(f"[ERROR] project root does not exist: {project_root}", file=sys.stderr)
        return 1

    set_fake_libc_path(args.fake_libc)
    set_cpp_path(args.cpp_path)
    set_cpp_extra_args(args.cpp_arg)
    if args.fake_types_header:
        set_fake_types_header(args.fake_types_header)
    for inc in args.include_dir:
        add_include_dir(inc)
    for define in args.define:
        add_extra_define(define)

    dataset = extract_project_calls(project_root, args.inline_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    meta = dataset["meta"]
    print(
        "[OK] "
        f"functions={meta['functions_total']} "
        f"calls={meta['calls_total']} "
        f"removed={meta['calls_removed_by_inline_json']} "
        f"parsed={meta['translation_units_parsed']}/{meta['translation_units_total']} "
        f"output={output_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
