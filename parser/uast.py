from __future__ import annotations
from enum import Enum

from abc import abstractmethod
from parser.tokenizer import Token

class UastNode:
    def __init__(self, token: Token) -> None:
        self.token: Token = token
        self.childs: list[UastNode] = []
        
    def add_child(self, child: UastNode) -> None:
        self.childs.append(child)

    def remove_child(self, child: UastNode) -> None:
        self.childs.remove(child)
        
    @abstractmethod
    def __str__(self) -> str:
        return f"UastNode({self.token.value})"

    def uast_to_string(self, prefix: str = "", is_last: bool = True) -> str:
        lines = []

        connector = "└── " if is_last else "├── "
        lines.append(prefix + connector + str(self))

        child_prefix = prefix + ("    " if is_last else "│   ")

        for i, child in enumerate(self.childs):
            last = i == len(self.childs) - 1
            lines.append(child.uast_to_string(child_prefix, last))

        return "\n".join(lines)

    def print_uast(root: UastNode) -> None:
        print(str(root))
        for i, child in enumerate(root.childs):
            last = i == len(root.childs) - 1
            print(child.uast_to_string("", last))

class FunctionNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_name(self) -> str:
        return self.token.value
        
    def get_body(self) -> UastNode:
        if not self.childs:
            return None
        return self.childs[-1]
        
    def __str__(self) -> str:
        return f"FunctionNode(name={self.token.value})"
        
class FunctionCallNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_name(self) -> str:
        return self.token.value
        
    def get_args(self) -> UastNode | None:
        if not self.childs:
            return None
        return self.childs[0]
        
    def __str__(self) -> str:
        return f"FunctionCallNode(name={self.token.value})"
        
class RExitNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
       
    def get_retval(self) -> UastNode:
        if len(self.childs) == 0:
            return None
        return self.childs[0]
       
    def __str__(self) -> str:
        return "RExitNode"
        
class LoopNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)

    def get_cond(self) -> UastNode:
        return self.childs[0]

    def get_body(self) -> UastNode:
        return self.childs[-1]

    def __str__(self) -> str:
        return "LoopNode"

class SwitchNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_cond(self) -> UastNode:
        return self.childs[0]
        
    def get_case(self, index: int) -> UastNode | None:
        cases: UastNode = self.childs[1]
        for i in cases.childs:
            index -= 1
            if index < 0:
                return i
            
        return None
        
    def __str__(self) -> str:
        return "SwitchNode"

class BreakNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return "BreakNode"

class ConditionNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_cond(self) -> UastNode:
        return self.childs[0]
        
    def get_true(self) -> UastNode:
        return self.childs[1]
        
    def get_false(self) -> UastNode | None:
        if len(self.childs) > 2:
            return self.childs[2]
        return None
        
    def __str__(self) -> str:
        return "ConditionNode"

class ConditionElseNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_cond(self) -> ConditionNode:
        return self.childs[0]
        
    def __str__(self) -> str:
        return "ConditionElseNode"

class ElseNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def get_body(self) -> UastNode:
        return self.childs[0]
        
    def __str__(self) -> str:
        return "ElseNode"

class DeclarationNode(UastNode):
    def __init__(self, token: Token, type: str) -> None:
        super().__init__(token)
        self.type: str = type
        
    def get_type(self) -> str:
        return self.type
        
    def get_val(self) -> UastNode | None:
        if not self.childs:
            return None
        return self.childs[0]
        
    def __str__(self) -> str:
        return "DeclarationNode"

class Operations(Enum):
    DREF = 1
    REF = 2
    ADD = 3
    SUB = 4
    DIV = 5
    ASSIGN = 6
    ADDASSIGN = 7

    MUL = 8
    MOD = 9
    POW = 10

    SUBASSIGN = 11
    MULASSIGN = 12
    DIVASSIGN = 13
    MODASSIGN = 14

    AND = 15          # &&
    OR = 16           # ||
    XOR = 17          # ^
    NOT = 18          # !

    SHL = 19          # <<
    SHR = 20          # >>

    ANDASSIGN = 21    # &=
    ORASSIGN = 22     # |=
    XORASSIGN = 23    # ^=
    SHLASSIGN = 24    # <<=
    SHRASSIGN = 25    # >>=

    EQ = 26
    NE = 27
    LT = 28
    LE = 29
    GT = 30
    GE = 31

    BITAND = 32       # &
    BITOR = 33        # |

    INC = 34          # ++
    DEC = 35          # --

    NEG = 36          # -
    POS = 37          # +

    BITNOT = 38       # ~

    COMMA = 39        # ,
    TERNARY = 40      # ?:
    INDEX = 41        # []
    CALL = 42         # ()
    MEMBER = 43       # .
    PTR_MEMBER = 44   # ->
    
    CAST = 45

class BinaryNode(UastNode):
    def __init__(self, token: Token, op: Operations) -> None:
        super().__init__(token)
        self.op: Operations = op
        
    def get_op(self) -> Operations:
        return self.op
        
    def get_left(self) -> UastNode:
        return self.childs[0]
        
    def get_right(self) -> UastNode:
        return self.childs[1]
        
    def __str__(self) -> str:
        return f"BinaryNode(op={self.op.name})"

class UnaryNode(UastNode):
    def __init__(self, token: Token, op: Operations) -> None:
        super().__init__(token)
        self.op: Operations = op
        
    def get_op(self) -> Operations:
        return self.op
        
    def __str__(self) -> str:
        return f"UnaryOp(op={self.op.name})"
