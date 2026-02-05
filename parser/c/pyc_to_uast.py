from pycparser import CParser, c_ast
from typing import Optional

from parser.tokenizer import Token, ScopeToken
from parser.uast import (
    UastNode, FunctionNode, FunctionCallNode,
    RExitNode, LoopNode, SwitchNode, DeclarationNode,
    BinaryNode, UnaryNode, ConditionNode, ElseNode, 
    ConditionElseNode, Operations
)

C_BINARY_OPERATOR_MAP = {
    "+": Operations.ADD,
    "-": Operations.SUB,
    "*": Operations.MUL,
    "/": Operations.DIV,
    "%": Operations.MOD,

    "=": Operations.ASSIGN,
    "+=": Operations.ADDASSIGN,
    "-=": Operations.SUBASSIGN,
    "*=": Operations.MULASSIGN,
    "/=": Operations.DIVASSIGN,
    "%=": Operations.MODASSIGN,

    "==": Operations.EQ,
    "!=": Operations.NE,
    "<": Operations.LT,
    "<=": Operations.LE,
    ">": Operations.GT,
    ">=": Operations.GE,

    "&&": Operations.AND,
    "||": Operations.OR,

    "&": Operations.BITAND,
    "|": Operations.BITOR,
    "^": Operations.XOR,
    "<<": Operations.SHL,
    ">>": Operations.SHR,

    "&=": Operations.ANDASSIGN,
    "|=": Operations.ORASSIGN,
    "^=": Operations.XORASSIGN,
    "<<=": Operations.SHLASSIGN,
    ">>=": Operations.SHRASSIGN,
}

C_UNARY_OPERATOR_MAP = {
    "+": Operations.POS,       # +a
    "-": Operations.NEG,       # -a
    "!": Operations.NOT,       # !a
    "~": Operations.BITNOT,    # ~a
    "*": Operations.DREF,      # *ptr
    "&": Operations.REF,       # &var
    "++": Operations.INC,
    "--": Operations.DEC
}

def _decl_type_to_str(type_node: c_ast.Node) -> str:
    if type_node is None:
        return "<?>"
    if isinstance(type_node, c_ast.PtrDecl):
        return _decl_type_to_str(type_node.type) + "*"
    if isinstance(type_node, c_ast.ArrayDecl):
        dim = ""
        if type_node.dim is not None:
            dim = _expr_to_str(type_node.dim)
        return f"{_decl_type_to_str(type_node.type)}[{dim}]"
    if isinstance(type_node, c_ast.TypeDecl):
        return _decl_type_to_str(type_node.type)
    if isinstance(type_node, c_ast.IdentifierType):
        return " ".join(type_node.names)
    if isinstance(type_node, c_ast.Struct):
        return f"struct {type_node.name or ''}".strip()
    if isinstance(type_node, c_ast.Union):
        return f"union {type_node.name or ''}".strip()
    if isinstance(type_node, c_ast.Enum):
        return f"enum {type_node.name or ''}".strip()
    if isinstance(type_node, c_ast.FuncDecl):
        return f"{_decl_type_to_str(type_node.type)}()"

    return type_node.__class__.__name__

def _expr_to_str(node: Optional[c_ast.Node]) -> str:
    if node is None:
        return ""
    if isinstance(node, c_ast.Constant):
        return str(node.value)
    if isinstance(node, c_ast.ID):
        return node.name
    if isinstance(node, c_ast.BinaryOp):
        return f"({_expr_to_str(node.left)} {node.op} {_expr_to_str(node.right)})"
    if isinstance(node, c_ast.UnaryOp):
        return f"({node.op}{_expr_to_str(node.expr)})"
    return node.__class__.__name__

def _make_token(kind: str, value: str, coord) -> Token:
    if coord is None:
        return Token(kind=kind, value=value)
    
    return Token(
        kind=kind, value=value, 
        line=coord.line or 0, 
        col=coord.column or 0, 
        filename=getattr(coord, "file", "") or ""
    )

class PycparserToUast:
    def convert(self, node: Optional[c_ast.Node]) -> Optional[UastNode]:
        if node is None:
            return None

        if isinstance(node, c_ast.FuncDef):
            fn_tok = _make_token("Function", node.decl.name, node.coord)
            u = FunctionNode(fn_tok)

            func_decl = node.decl.type
            if isinstance(func_decl, c_ast.FuncDecl) and func_decl.args:
                params_u = UastNode(_make_token("Params", "params", func_decl.args.coord))
                for p in func_decl.args.params or []:
                    pu = self.convert(p)
                    if pu:
                        params_u.add_child(pu)
                u.add_child(params_u)

            body_u = self.convert(node.body)
            if body_u:
                u.add_child(body_u)
            return u

        if isinstance(node, c_ast.FuncCall):
            name_str = _expr_to_str(node.name) if node.name else "<?>"
            u = FunctionCallNode(_make_token("Call", name_str, node.coord))

            if node.args:
                args_u = self.convert(node.args)
                if args_u:
                    u.add_child(args_u)
            return u

        if isinstance(node, c_ast.Return):
            u = RExitNode(_make_token("Return", "return", node.coord))
            if node.expr:
                expr_u = self.convert(node.expr)
                if expr_u:
                    u.add_child(expr_u)
            return u

        if isinstance(node, c_ast.For):
            u = LoopNode(_make_token("Loop", "for", node.coord))
            for part, label in [(node.init, "init"), (node.cond, "cond"), (node.next, "next"), (node.stmt, "body")]:
                part_u = self.convert(part)
                if part_u:
                    wrapper = UastNode(_make_token("ForPart", label, getattr(part, "coord", node.coord)))
                    wrapper.add_child(part_u)
                    u.add_child(wrapper)
            return u

        if isinstance(node, c_ast.While):
            u = LoopNode(_make_token("Loop", "while", node.coord))
            cond_u = self.convert(node.cond)
            body_u = self.convert(node.stmt)
            if cond_u:
                u.add_child(cond_u)
            if body_u:
                u.add_child(body_u)
            return u

        if isinstance(node, c_ast.DoWhile):
            u = LoopNode(_make_token("Loop", "do_while", node.coord))
            body_u = self.convert(node.stmt)
            cond_u = self.convert(node.cond)
            if body_u:
                u.add_child(body_u)
            if cond_u:
                u.add_child(cond_u)
            return u

        if isinstance(node, c_ast.If):
            return self._convert_if(node)

        if isinstance(node, c_ast.Switch):
            u = SwitchNode(_make_token("Switch", "switch", node.coord))
            cond_u = self.convert(node.cond)
            stmt_u = self.convert(node.stmt)
            if cond_u:
                u.add_child(cond_u)
            if stmt_u:
                u.add_child(stmt_u)
            return u

        if isinstance(node, c_ast.Decl):
            name = node.name or "<?>"
            typ = _decl_type_to_str(node.type)
            u = DeclarationNode(_make_token("Decl", name, node.coord), type=typ)
            if node.init:
                init_u = self.convert(node.init)
                if init_u:
                    u.add_child(init_u)
            return u

        if isinstance(node, c_ast.Assignment):
            u = BinaryNode(_make_token("Assign", node.op, node.coord), op=C_BINARY_OPERATOR_MAP.get(node.op, Operations.ADD))
            l = self.convert(node.lvalue)
            r = self.convert(node.rvalue)
            if l:
                u.add_child(l)
            if r:
                u.add_child(r)
            return u

        if isinstance(node, c_ast.BinaryOp):
            u = BinaryNode(_make_token("BinOp", node.op, node.coord), op=C_BINARY_OPERATOR_MAP.get(node.op, Operations.ADD))
            l = self.convert(node.left)
            r = self.convert(node.right)
            if l:
                u.add_child(l)
            if r:
                u.add_child(r)
            return u

        if isinstance(node, c_ast.UnaryOp):
            u = UnaryNode(_make_token("UnOp", node.op, node.coord), op=C_UNARY_OPERATOR_MAP.get(node.op, Operations.DREF))
            e = self.convert(node.expr)
            if e:
                u.add_child(e)
            return u

        if isinstance(node, c_ast.TernaryOp):
            u = UastNode(_make_token("Ternary", "?:", node.coord))
            for part in [node.cond, node.iftrue, node.iffalse]:
                pu = self.convert(part)
                if pu:
                    u.add_child(pu)
            return u

        if isinstance(node, c_ast.ExprList):
            u = UastNode(_make_token("Args", "args", node.coord))
            for e in node.exprs or []:
                eu = self.convert(e)
                if eu:
                    u.add_child(eu)
            return u

        if isinstance(node, c_ast.ID):
            return UastNode(_make_token("Id", node.name, node.coord))

        if isinstance(node, c_ast.Constant):
            return UastNode(_make_token("Const", str(node.value), node.coord))

        if isinstance(node, c_ast.Compound):
            u = UastNode(ScopeToken())
            for st in node.block_items or []:
                su = self.convert(st)
                if su:
                    u.add_child(su)
            return u

        if isinstance(node, c_ast.Case):
            u = UastNode(_make_token("Case", "case", node.coord))
            ex = self.convert(node.expr)
            if ex:
                u.add_child(ex)
            for st in node.stmts or []:
                su = self.convert(st)
                if su:
                    u.add_child(su)
            return u

        if isinstance(node, c_ast.Default):
            u = UastNode(_make_token("Default", "default", node.coord))
            for st in node.stmts or []:
                su = self.convert(st)
                if su:
                    u.add_child(su)
            return u

        if isinstance(node, c_ast.Break):
            return UastNode(_make_token("Break", "break", node.coord))

        if isinstance(node, c_ast.Continue):
            return UastNode(_make_token("Continue", "continue", node.coord))

        u = UastNode(_make_token("Node", node.__class__.__name__, getattr(node, "coord", None)))
        for _, child in node.children():
            cu = self.convert(child)
            if cu:
                u.add_child(cu)

        return u

    def _convert_if(self, node: c_ast.If) -> UastNode:
        u_if = ConditionNode(_make_token("If", "if", node.coord))

        cond_u = self.convert(node.cond)
        then_u = self.convert(node.iftrue)
        if cond_u:
            u_if.add_child(cond_u)
        if then_u:
            u_if.add_child(then_u)

        if node.iffalse is not None:
            if isinstance(node.iffalse, c_ast.If):
                u_else_if = ConditionElseNode(_make_token("ElseIf", "else if", node.iffalse.coord))
                u_else_if.add_child(self._convert_if(node.iffalse))
                u_if.add_child(u_else_if)
            else:
                u_else = ElseNode(_make_token("Else", "else", getattr(node.iffalse, "coord", node.coord)))
                else_u = self.convert(node.iffalse)
                if else_u:
                    u_else.add_child(else_u)
                u_if.add_child(u_else)

        return u_if
    
def c_code_to_uast(code: str) -> UastNode:
    parser = CParser()
    ast_root: c_ast.Node = parser.parse(code)
    conv = PycparserToUast()
    u = conv.convert(ast_root)
    if u is None:
        u = UastNode(_make_token("Root", "root", getattr(ast_root, "coord", None)))
    return u
    