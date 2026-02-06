from __future__ import annotations
from dataclasses import dataclass, field
from ir.instr.ir_block import IRBlock

@dataclass
class CFGBlock:
    id: int = 0
    start: int = 0
    end: int = 0
    instrs: list[IRBlock] = field(default_factory=list)
    
    succ: set[int] = field(default_factory=set)
    pred: set[int] = field(default_factory=set)
    dom: set[int]  = field(default_factory=set)
    sdom: CFGBlock | None = None
    
    jmp: CFGBlock | None = None
    lin: CFGBlock | None = None
    
    def __hash__(self):
        return hash((self.id, self.start, self.end))
    
@dataclass
class CFGFunction:
    id: int = 0
    func: str = ""
    blocks: list[CFGBlock] = field(default_factory=list)
    