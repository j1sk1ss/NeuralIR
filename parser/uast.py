from __future__ import annotations
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
        
    def __str__(self) -> str:
        return f"FunctionNode(name={self.token.value})"
        
class FunctionCallNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return f"FunctionCallNode(name={self.token.value})"
        
class RExitNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
       
    def __str__(self) -> str:
        return "RExitNode"
        
class LoopNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)

    def __str__(self) -> str:
        return "LoopNode"

class SwitchNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return "SwitchNode"

class ConditionNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return "ConditionNode"

class ConditionElseNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return "ConditionElseNode"

class ElseNode(UastNode):
    def __init__(self, token: Token) -> None:
        super().__init__(token)
        
    def __str__(self) -> str:
        return "ElseNode"

class DeclarationNode(UastNode):
    def __init__(self, token: Token, type: str) -> None:
        super().__init__(token)
        self.type: str = type
        
    def __str__(self) -> str:
        return "DeclarationNode"

class BinaryNode(UastNode):
    def __init__(self, token: Token, op: str) -> None:
        super().__init__(token)
        self.op: str = op
        
    def __str__(self) -> str:
        return f"BinaryNode(op={self.op})"

class UnaryNode(UastNode):
    def __init__(self, token: Token, op: str) -> None:
        super().__init__(token)
        self.op: str = op
        
    def __str__(self) -> str:
        return f"UnaryOp(op={self.op})"
