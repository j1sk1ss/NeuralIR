from enum import Enum

class IRAction(Enum):
    MKLB    = "mklable"
    JMP     = "jump"
    BREAK   = "break"
    IF      = "if"
    BINOP   = "binop"
    DREF    = "dref"
    REF     = "ref"
    BB      = "bb"
    NOTHING = "nothing"
    UNARY   = "unary"
    BINARY  = "binary"
    DECL    = "decl"
    SWITCH  = "switch"
    LOOP    = "loop"
    TERM    = "term"
    FCALL   = "fcall"
    SCALL   = "scall" # TODO: CPL syscall support and C/++ code special functions mark as syscalls
    FDECL   = "fdecl"
    FEND    = "fend"

class IRSubject:
    def __str__(self) -> str:
        return "subject"

_global_lb_id: int = 0

class IRLabel(IRSubject):
    def __init__(self) -> None:
        super().__init__()
        global _global_lb_id
        self.id: int = _global_lb_id
        _global_lb_id += 1
        
    def __str__(self) -> str:
        return f"lb{self.id}"

class IROperation(IRSubject):
    def __init__(self, op: str) -> None:
        super().__init__()
        self.op: str = op
        
    def __str__(self) -> str:
        return f"operation({self.op})"

class IRDeclaration(IRSubject):
    def __init__(self, type: str) -> None:
        super().__init__()
        self.type: str = type
        
    def __str__(self) -> str:
        return f"declaration({self.type})"

class IRFunction(IRSubject):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name: str = name
        
    def __str__(self) -> str:
        return f"function({self.name})"

class IRBlock:
    def __init__(
        self, 
        a: IRAction, 
        x: IRSubject | None = None, 
        y: IRSubject | None = None, 
        z: IRSubject | None = None
    ) -> None:
        self.a: IRAction = a
        self.subjects: list[IRSubject | None] = [ x, y, z ]

    def __str__(self) -> str:
        if self.subjects[2]:
            return f"{self.a.value}({self.subjects[0]},{self.subjects[1]},{self.subjects[2]})"
        if self.subjects[1]:
            return f"{self.a.value}({self.subjects[0]},{self.subjects[1]})"
        if self.subjects[0]:
            return f"{self.a.value}({self.subjects[0]})"
        return f"{self.a.value}"

class IRBaseBlockLabel(IRBlock):
    def __init__(self, id: int) -> None:
        super().__init__(IRAction.BB)
        self.id: int = id
        self.a = IRAction.BB
