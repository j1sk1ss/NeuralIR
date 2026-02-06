from __future__ import annotations
from typing import List

from parser.tokenizer import ScopeToken, Token
from parser.uast import (
    UastNode, FunctionNode, FunctionCallNode,
    RExitNode, LoopNode, SwitchNode, DeclarationNode,
    BinaryNode, UnaryNode, ConditionNode, ElseNode,
    Operations
)

CPL_BINARY_OPERATOR_MAP = {
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

CPL_UNARY_OPERATOR_MAP = {
    "+": Operations.POS,       # +a
    "-": Operations.NEG,       # -a
    "not": Operations.NOT,     # !a
    "~": Operations.BITNOT,    # ~a
    "dref": Operations.DREF,   # *ptr
    "ref": Operations.REF,     # &var
    "as": Operations.CAST
}

def _make_token(kind: str, value: str) -> Token:
    return Token(kind=kind, value=value)

class ParseError(Exception):
    pass

class CplParser:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    def _skip_trivia_from(self, idx: int) -> int:
        n = len(self.toks)
        while idx < n and self.toks[idx].kind in {"EOL", "COMMENT"}:
            idx += 1
        return idx

    def _peek_idx(self, k: int = 0) -> int:
        idx = self._skip_trivia_from(self.i)
        while k > 0:
            idx += 1
            idx = self._skip_trivia_from(idx)
            k -= 1
        return idx

    def peek(self, k: int = 0) -> Token:
        idx = self._peek_idx(k)
        if idx >= len(self.toks):
            return Token("EOF", "<EOF>", 0, 0)
        return self.toks[idx]

    def consume(self) -> Token:
        idx = self._peek_idx(0)
        if idx >= len(self.toks):
            return Token("EOF", "<EOF>", 0, 0)
        t = self.toks[idx]
        self.i = idx + 1
        return t

    def at(self, body: str) -> bool:
        return self.peek().value == body

    def at_kind(self, kind: str) -> bool:
        return self.peek().kind == kind

    def expect(self, body: str) -> Token:
        t = self.peek()
        if t.value != body:
            raise ParseError(f"Expected '{body}', got '{t.value}' at {t.line}:{t.col}")
        return self.consume()

    def expect_kind(self, kind: str) -> Token:
        t = self.peek()
        if t.kind != kind:
            raise ParseError(f"Expected kind {kind}, got {t.kind}('{t.value}') at {t.line}:{t.col}")
        return self.consume()

    def parse_program(self) -> UastNode:
        self.expect("{")
        root = UastNode(ScopeToken())

        while not self.at("}"):
            root.add_child(self.parse_top_item())

        self.expect("}")
        return root

    def parse_top_item(self) -> UastNode:
        t: Token = self.peek()

        if t.value == "start":
            return self.parse_start_function()
        if t.value == "from":
            return self.parse_import()
        if t.value == "extern":
            return self.parse_extern()
        if t.value == "#":
            return self.parse_pp_directive()
        
        if t.value in ("glob", "ro"):
            self.consume()

        return self.parse_top_decl()

    def parse_top_decl(self) -> UastNode:
        if self.at("function"):
            return self.parse_function_def_or_proto()
        return self.parse_var_decl()

    def parse_import(self) -> UastNode:
        kw = self.expect("from")
        n = UastNode(kw)
        n.add_child(UastNode(self.expect_kind("STRING_LITERAL")))
        self.expect("import")
        if self.at_kind("IDENTIFIER"):
            n.add_child(self.parse_import_list())
        return n

    def parse_import_list(self) -> UastNode:
        n = UastNode(Token("NODE", "import_list"))
        n.add_child(UastNode(self.expect_kind("IDENTIFIER")))
        while self.at(","):
            self.consume()
            n.add_child(UastNode(self.expect_kind("IDENTIFIER")))
        return n

    def parse_extern(self) -> UastNode:
        kw = self.expect("extern")
        n = UastNode(kw)
        if self.at("exfunc"):
            n.add_child(self.parse_function_prototype())
        else:
            n.add_child(self.parse_var_prototype())
        return n

    def parse_function_prototype(self) -> UastNode:
        self.expect("exfunc")
        name = self.expect_kind("IDENTIFIER")
        return FunctionNode(name)

    def parse_var_prototype(self) -> UastNode:
        ty = self.parse_type()
        name = self.expect_kind("IDENTIFIER")
        d = DeclarationNode(name, type=ty)
        return d

    def parse_pp_directive(self) -> UastNode:
        hash_tok = self.expect("#")
        n = UastNode(hash_tok)
        while self.peek().kind not in ("EOL", "EOF") and not self.at(";"):
            n.add_child(UastNode(self.consume()))
        if self.at(";"):
            self.consume()
        else:
            self.expect_kind("EOL")
        return n

    def parse_start_function(self) -> UastNode:
        kw = self.expect("start")
        fn = FunctionNode(kw)
        self.expect("(")
        if not self.at(")"):
            fn.add_child(self.parse_param_list())
        self.expect(")")
        fn.add_child(self.parse_block())
        return fn

    def parse_function_def_or_proto(self) -> UastNode:
        self.expect("function")
        name = self.expect_kind("IDENTIFIER")
        fn = FunctionNode(name)

        self.expect("(")
        if not self.at(")"):
            fn.add_child(self.parse_param_list())
        self.expect(")")

        if self.at("=>"):
            self.consume()
            self.parse_type()

        if self.at("{"):
            fn.add_child(self.parse_block())
            return fn

        self.expect(";")
        return fn

    def parse_param_list(self) -> UastNode:
        n = UastNode(Token("NODE", "params"))
        n.add_child(self.parse_param())
        while self.at(","):
            self.consume()
            n.add_child(self.parse_param())
        return n

    def parse_param(self) -> UastNode:
        if self.at("..."):
            return UastNode(self.consume())

        ty = self.parse_type()
        name = self.expect_kind("IDENTIFIER")
        d = DeclarationNode(name, type=ty)
        if self.at("="):
            self.consume()
            d.add_child(self.parse_expression())
        return d

    def parse_block(self) -> UastNode:
        self.expect("{")
        b = UastNode(ScopeToken())
        while not self.at("}"):
            b.add_child(self.parse_statement())
        self.expect("}")
        return b

    def parse_statement(self) -> UastNode:
        t = self.peek()

        if t.value == "#":
            return self.parse_pp_directive()
        if t.kind == "COMMENT":
            return UastNode(self.consume())
        if t.value == "{":
            return self.parse_block()
        if t.value == "if":
            return self.parse_if()
        if t.value == "loop":
            return self.parse_loop()
        if t.value == "while":
            return self.parse_while()
        if t.value == "switch":
            return self.parse_switch()
        if t.value == "return":
            return self.parse_return()
        if t.value == "exit":
            return self.parse_exit()
        if t.value == "break":
            return self.parse_break()
        if t.value == "syscall":
            return self.parse_syscall()
        if t.value == "asm":
            return self.parse_asm()

        if t.value == "arr":
            if self.peek(1).kind == "IDENTIFIER":
                return self.parse_arr_decl()
            return self.parse_var_decl()

        if self.is_type_start(t):
            return self.parse_var_decl()

        e = self.parse_expression()
        self.expect(";")
        return e

    def is_type_start(self, t: Token) -> bool:
        return t.value in {
            "ptr", "str",
            "f64","i64","u64","f32","i32","u32","i16","u16","i8","u8",
            "arr"
        }

    def parse_var_decl(self) -> UastNode:
        ty = self.parse_type()
        name = self.expect_kind("IDENTIFIER")
        d = DeclarationNode(name, type=ty)
        if self.at("="):
            self.consume()
            d.add_child(self.parse_expression())
        self.expect(";")
        return d

    def parse_arr_decl(self) -> UastNode:
        kw = self.expect("arr")
        name = self.expect_kind("IDENTIFIER")
        d = DeclarationNode(name, type="arr")
        d.add_child(UastNode(kw))

        self.expect("[")
        d.add_child(UastNode(self.expect_kind("INTEGER_LITERAL")))
        self.expect(",")
        inner_ty = self.parse_type()
        d.add_child(UastNode(Token("TYPE", inner_ty)))
        self.expect("]")

        if self.at("="):
            self.consume()
            if self.at("{"):
                d.add_child(self.parse_arr_value())
            else:
                d.add_child(self.parse_expression())

        self.expect(";")
        return d

    def parse_arr_value(self) -> UastNode:
        self.expect("{")
        n = UastNode(ScopeToken())
        if not self.at("}"):
            n.add_child(self.parse_expression())
            while self.at(","):
                self.consume()
                n.add_child(self.parse_expression())
        self.expect("}")
        return n

    def parse_if(self) -> UastNode:
        kw = self.expect("if")
        n = ConditionNode(kw)
        n.add_child(self.parse_expression())
        self.expect(";")
        n.add_child(self.parse_block())
        if self.at("else"):
            elkw = self.consume()
            e = ElseNode(elkw)
            e.add_child(self.parse_block())
            n.add_child(e)
        return n

    def parse_loop(self) -> UastNode:
        kw = self.expect("loop")
        n = LoopNode(kw)
        n.add_child(self.parse_block())
        return n

    def parse_while(self) -> UastNode:
        kw = self.expect("while")
        n = LoopNode(kw)
        n.add_child(self.parse_expression())
        self.expect(";")
        n.add_child(self.parse_block())
        return n

    def parse_switch(self) -> UastNode:
        kw = self.expect("switch")
        n = SwitchNode(kw)
        n.add_child(self.parse_expression())
        self.expect(";")
        self.expect("{")
        while self.at("case"):
            n.add_child(self.parse_case_block())
        if self.at("default"):
            n.add_child(self.parse_default_block())
        self.expect("}")
        return n

    def parse_case_block(self) -> UastNode:
        kw = self.expect("case")
        c = UastNode(kw)
        c.add_child(self.parse_literal())
        self.expect(";")
        c.add_child(self.parse_block())
        return c

    def parse_default_block(self) -> UastNode:
        kw = self.expect("default")
        d = UastNode(kw)
        if self.at(";"):
            self.consume()
        d.add_child(self.parse_block())
        return d

    def parse_return(self) -> UastNode:
        kw = self.expect("return")
        n = RExitNode(kw)
        if not self.at(";"):
            n.add_child(self.parse_expression())
        self.expect(";")
        return n

    def parse_exit(self) -> UastNode:
        kw = self.expect("exit")
        n = RExitNode(kw)
        n.add_child(self.parse_expression())
        self.expect(";")
        return n

    def parse_syscall(self) -> UastNode:
        kw = self.expect("syscall")
        call = FunctionCallNode(kw)
        self.expect("(")
        if not self.at(")"):
            call.add_child(self.parse_expression())
            while self.at(","):
                self.consume()
                call.add_child(self.parse_expression())
        self.expect(")")
        self.expect(";")
        return call

    def parse_asm(self) -> UastNode:
        kw = self.expect("asm")
        n = UastNode(kw)
        self.expect("(")
        while not self.at(")"):
            n.add_child(UastNode(self.consume()))
            if self.at(","):
                self.consume()
        self.expect(")")
        self.expect("{")
        while not self.at("}"):
            n.add_child(UastNode(self.consume()))
        self.expect("}")
        return n

    def parse_type(self) -> str:
        if self.at("ptr"):
            self.consume()
            return "ptr " + self.parse_type()

        if self.at("arr"):
            self.consume()
            self.expect("[")
            n = self.expect_kind("INTEGER_LITERAL").value
            self.expect(",")
            inner = self.parse_type()
            self.expect("]")
            return f"arr[{n},{inner}]"

        t = self.peek()
        if t.value in ("str","f64","i64","u64","f32","i32","u32","i16","u16","i8","u8"):
            return self.consume().value

        raise ParseError(f"Expected type, got {t.kind}('{t.value}') at {t.line}:{t.col}")

    def parse_break(self) -> UastNode:
        kw = self.expect("break")
        self.expect(";")
        return UastNode(kw)

    def parse_literal(self) -> UastNode:
        t = self.peek()
        if t.kind in ("INTEGER_LITERAL", "STRING_LITERAL", "CHAR_LITERAL"):
            return UastNode(self.consume())
        raise ParseError(f"Expected literal, got {t.kind}('{t.value}')")

    def parse_expression(self) -> UastNode:
        return self.parse_assign()

    def parse_assign(self) -> UastNode:
        left = self.parse_logical_or()
        if self.peek().value in ("=","+=","-=","*=","/=","%=","|=","^=","&=","||=","&&="):
            op = self.consume()
            right = self.parse_assign()
            n = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            n.add_child(left)
            n.add_child(right)
            return n
        return left

    def parse_logical_or(self) -> UastNode:
        n = self.parse_logical_and()
        while self.at("||"):
            op = self.consume()
            r = self.parse_logical_and()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD)) 
            b.add_child(n) 
            b.add_child(r)
            n = b
        return n

    def parse_logical_and(self) -> UastNode:
        n = self.parse_bit_or()
        while self.at("&&"):
            op = self.consume()
            r = self.parse_bit_or()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_bit_or(self) -> UastNode:
        n = self.parse_bit_xor()
        while self.at("|"):
            op = self.consume()
            r = self.parse_bit_xor()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_bit_xor(self) -> UastNode:
        n = self.parse_bit_and()
        while self.at("^"):
            op = self.consume()
            r = self.parse_bit_and()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_bit_and(self) -> UastNode:
        n = self.parse_equality()
        while self.at("&"):
            op = self.consume()
            r = self.parse_equality()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_equality(self) -> UastNode:
        n = self.parse_relational()
        while self.peek().value in ("==","!="):
            op = self.consume()
            r = self.parse_relational()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_relational(self) -> UastNode:
        n = self.parse_shift()
        while self.peek().value in ("<","<=",">",">="):
            op = self.consume()
            r = self.parse_shift()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_shift(self) -> UastNode:
        n = self.parse_add()
        while self.peek().value in ("<<",">>"):
            op = self.consume()
            r = self.parse_add()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_add(self) -> UastNode:
        n = self.parse_mul()
        while self.peek().value in ("+","-"):
            op = self.consume()
            r = self.parse_mul()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_mul(self) -> UastNode:
        n = self.parse_unary()
        while self.peek().value in ("*","/","%"):
            op = self.consume()
            r = self.parse_unary()
            b = BinaryNode(op, op=CPL_BINARY_OPERATOR_MAP.get(op.value, Operations.ADD))
            b.add_child(n)
            b.add_child(r)
            n = b
        return n

    def parse_unary(self) -> UastNode:
        if self.peek().value in ("not","+","-","ref","dref"):
            op = self.consume()
            expr = self.parse_unary()
            u = UnaryNode(op, op=CPL_UNARY_OPERATOR_MAP.get(op.value, Operations.DREF))
            u.add_child(expr)
            return u
        return self.parse_postfix()

    def parse_postfix(self) -> UastNode:
        n = self.parse_primary()
        while True:
            if self.at("("):
                self.consume()

                call = FunctionCallNode(n.token)

                args = UastNode(Token("Args", "args"))
                if not self.at(")"):
                    call.add_child(self.parse_expression())
                    while self.at(","):
                        self.consume()
                        call.add_child(self.parse_expression())
                call.add_child(args)
                self.expect(")")

                n = call
                continue

            if self.at("["):
                op = self.consume()
                idx = BinaryNode(op, op=Operations.INDEX)

                idx.add_child(n)
                idx.add_child(self.parse_expression())
                while self.at(","):
                    self.consume()
                    idx.add_child(self.parse_expression())
                self.expect("]")
                n = idx
                continue

            if self.at("as"):
                op = self.consume()
                ty = self.parse_type()
                cast = UnaryNode(op, op=Operations.CAST)
                cast.add_child(n)
                cast.add_child(UastNode(Token("TYPE", ty)))
                n = cast
                continue

            break
        return n

    def parse_primary(self) -> UastNode:
        t = self.peek()
        if t.kind in ("INTEGER_LITERAL","STRING_LITERAL","CHAR_LITERAL"):
            return UastNode(self.consume())
        if t.kind == "IDENTIFIER":
            return UastNode(self.consume())
        if self.at("("):
            self.consume()
            e = self.parse_expression()
            self.expect(")")
            return e
        raise ParseError(f"Expected primary, got {t.kind}('{t.value}') at {t.line}:{t.col}")

KEYWORDS = {
    "from","import","extern","exfunc","glob","ro",
    "function","start",
    "arr",
    "if","else","loop","while",
    "switch","case","default",
    "return","exit","break","lis",
    "syscall","asm",
    "not","ref","dref","as",
    "ptr","str",
    "f64","i64","u64","f32","i32","u32","i16","u16","i8","u8",
    "line","include","define","undef","ifdef","ifndef","endif"
}

OPERATORS = [
    "||=","&&=",
    "<<",">>",
    "<=",">=","==","!=",
    "+=","-=","*=","/=","%=",
    "|=","^=","&=",
    "||","&&",
    "=>",
    "=","<",">","+","-","*","/","%","|","^","&"
]

PUNCT = "{}()[];,"

WHITESPACE = " \t\r"

def _tokenize_cpl(code: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    line = 1
    col = 1
    n = len(code)

    def advance(ch: str) -> None:
        nonlocal line, col
        if ch == "\n":
            line += 1
            col = 1
        else:
            col += 1

    def add(kind: str, body: str, l: int, c: int) -> None:
        tokens.append(Token(kind, body, l, c))

    while i < n:
        c = code[i]

        if c in WHITESPACE:
            advance(c)
            i += 1
            continue

        if c == "\n":
            add("EOL", "\\n", line, col)
            advance(c)
            i += 1
            continue

        start_line, start_col = line, col

        if c == ":":
            j = i + 1
            while j < n and code[j] != ":":
                if code[j] == "\n":
                    raise SyntaxError(f"Unterminated comment at {start_line}:{start_col}")
                j += 1
            if j >= n:
                raise SyntaxError(f"Unterminated comment at {start_line}:{start_col}")
            text = code[i : j + 1]
            add("COMMENT", text, start_line, start_col)
            while i <= j:
                advance(code[i])
                i += 1
            continue

        if c == '"':
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == '"':
                    j += 1
                    break
                if code[j] == "\n":
                    raise SyntaxError(f"Unterminated string at {start_line}:{start_col}")
                j += 1
            if j > n:
                raise SyntaxError(f"Unterminated string at {start_line}:{start_col}")
            text = code[i:j]
            add("STRING_LITERAL", text, start_line, start_col)
            while i < j:
                advance(code[i])
                i += 1
            continue

        if c == "'":
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == "'":
                    j += 1
                    break
                if code[j] == "\n":
                    raise SyntaxError(f"Unterminated char literal at {start_line}:{start_col}")
                j += 1
            if j > n:
                raise SyntaxError(f"Unterminated char literal at {start_line}:{start_col}")
            text = code[i:j]
            add("CHAR_LITERAL", text, start_line, start_col)
            while i < j:
                advance(code[i])
                i += 1
            continue

        if c.isdigit():
            j = i
            while j < n and code[j].isdigit():
                j += 1
            text = code[i:j]
            add("INTEGER_LITERAL", text, start_line, start_col)
            while i < j:
                advance(code[i])
                i += 1
            continue

        if c.isalpha() or c == "_":
            j = i
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            text = code[i:j]
            add("KEYWORD" if text in KEYWORDS else "IDENTIFIER", text, start_line, start_col)
            while i < j:
                advance(code[i])
                i += 1
            continue

        matched = False
        for op in OPERATORS:
            if code.startswith(op, i):
                add("OPERATOR", op, start_line, start_col)
                for ch in op:
                    advance(ch)
                i += len(op)
                matched = True
                break
        if matched:
            continue

        if c in PUNCT:
            add("PUNCT", c, start_line, start_col)
            advance(c)
            i += 1
            continue

        raise SyntaxError(f"Unknown character '{c}' at {line}:{col}")

    tokens.append(Token("EOF", "<EOF>", line, col))
    return tokens

def cpl_code_to_uast(code: str) -> UastNode:
    tokens: List[Token] = _tokenize_cpl(code)
    parser = CplParser(tokens)
    uast = parser.parse_program()
    return uast
