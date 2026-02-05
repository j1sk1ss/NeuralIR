from dataclasses import dataclass

@dataclass
class Token:
    kind: str     = ""
    value: str    = ""
    line: int     = 0
    col: int      = 0
    filename: str = ""

class ScopeToken(Token):
    def __init__(self) -> None:
        super().__init__(None)

class Tokenizer:
    def __init__(self, file: str) -> list[Token]:
        pass
    