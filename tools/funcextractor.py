from pathlib import Path
from pycparser import parse_file, c_ast, c_generator
import pycparser

_cpp_path = "gcc"
_cpp_extra_args = []
_ast_cache = {}
_func_cache = {}
_inc_cache = None
_fake_libc_path = None
_additional_include_dirs = []
_extra_defines = []
_fake_types_header = None

def set_cpp_path(path: str):
    global _cpp_path
    _cpp_path = path

def set_cpp_extra_args(args: list[str]):
    global _cpp_extra_args
    _cpp_extra_args = args

def set_fake_libc_path(path: str | None):
    global _fake_libc_path
    _fake_libc_path = Path(path) if path else None

def add_include_dir(path: str):
    _additional_include_dirs.append(str(Path(path).resolve()))

def add_extra_define(define: str):
    _extra_defines.append(define)

def set_fake_types_header(path: str | None):
    global _fake_types_header
    _fake_types_header = Path(path).resolve() if path else None

def _collect_include_dirs(project_root: Path):
    global _inc_cache
    if _inc_cache is not None:
        return _inc_cache
    incs = set()
    incs.add(str(project_root / "include"))
    incs.add(str(project_root))
    for p in project_root.rglob("*.h"):
        incs.add(str(p.parent))
    for d in _additional_include_dirs:
        incs.add(d)
    _inc_cache = sorted(str(d) for d in incs if Path(d).exists())
    return _inc_cache

def _get_fake_libc():
    if _fake_libc_path:
        return _fake_libc_path
    raise FileNotFoundError("Set fakelibs! Download them from: https://github.com/eliben/pycparser/tree/main/utils/fake_libc_include")

def _parse_file(path: Path, project_root: Path):
    if path in _ast_cache:
        return _ast_cache[path]
    fake_libc = _get_fake_libc()
    incs = _collect_include_dirs(project_root)
    cpp_args = [
        "-E",
        "-nostdinc",
        f"-I{fake_libc}",
        "-D__attribute__(x)=",
        "-D__extension__=",
        "-D__inline__=inline",
        "-D__restrict__=",
        "-D__restrict=",
        "-Drestrict=",
    ]
    for d in incs:
        cpp_args.append(f"-I{d}")
    for define in _extra_defines:
        cpp_args.append(f"-D{define}")
    if _fake_types_header:
        cpp_args.append(f"-include{_fake_types_header}")
    cpp_args += _cpp_extra_args
    try:
        ast = parse_file(str(path), use_cpp=True, cpp_path=_cpp_path, cpp_args=cpp_args)
    except Exception as ex:
        with open(str(path), "r") as f:
            print(f"Parse error in {path}! Code:\n{f.read()}")
        raise Exception("Parse error!") from ex
    _ast_cache[path] = ast
    return ast

class _FuncDefVisitor(c_ast.NodeVisitor):
    def __init__(self, name):
        self.name = name
        self.node = None

    def visit_FuncDef(self, node):
        if node.decl.name == self.name:
            self.node = node

def _generate_function_code(funcdef_node):
    generator = c_generator.CGenerator()
    return generator.visit(funcdef_node)

def _find_function_in_project(project_root: Path, name: str):
    if name in _func_cache:
        return _func_cache[name]
    for path in project_root.rglob("*.c"):
        ast = _parse_file(path, project_root)
        visitor = _FuncDefVisitor(name)
        visitor.visit(ast)
        if visitor.node:
            code = _generate_function_code(visitor.node)
            _func_cache[name] = (code, path)
            return code, path
    _func_cache[name] = (None, None)
    return None, None

def _collect_type_definitions(ast):
    definitions = []
    generator = c_generator.CGenerator()

    for node in ast.ext:
        if isinstance(node, c_ast.Typedef):
            code = generator.visit(node)
            if not code.rstrip().endswith(';'):
                code += ';'
            key = f"typedef:{node.name}"
            definitions.append((key, code))

        elif isinstance(node, c_ast.Decl):
            typ = node.type
            if isinstance(typ, (c_ast.Struct, c_ast.Union, c_ast.Enum)) and typ.fields is not None:
                kind = type(typ).__name__.lower()
                if typ.name:
                    key = f"{kind}:{typ.name}"
                else:
                    code = generator.visit(node)
                    if not code.rstrip().endswith(';'):
                        code += ';'
                    key = code
                code = generator.visit(node)
                if not code.rstrip().endswith(';'):
                    code += ';'
                definitions.append((key, code))

    return definitions

def extract_inlined_pair(event: dict, project_root: str) -> str | None:
    project_root = Path(project_root)
    caller_path = project_root / event["file"]
    caller_ast = _parse_file(caller_path, project_root)

    callee_code, callee_path = _find_function_in_project(project_root, event["callee"])
    if not callee_code:
        return None

    callee_ast = _parse_file(callee_path, project_root)

    caller_visitor = _FuncDefVisitor(event["caller"])
    caller_visitor.visit(caller_ast)
    if not caller_visitor.node:
        return None
    caller_code = _generate_function_code(caller_visitor.node)

    caller_defs = _collect_type_definitions(caller_ast)
    callee_defs = _collect_type_definitions(callee_ast)

    seen = set()
    defs_code_lines = []
    for key, code in caller_defs + callee_defs:
        if key not in seen:
            seen.add(key)
            defs_code_lines.append(code)

    defs_code = "\n".join(defs_code_lines)

    result = []
    if defs_code:
        result.append(defs_code)
    result.append(callee_code)
    result.append(caller_code)
    return "\n".join(result)