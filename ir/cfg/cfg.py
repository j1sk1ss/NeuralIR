from __future__ import annotations
from dataclasses import dataclass, field
from ir.instr.ir_block import IRBlock

@dataclass
class CFGBlock:
    id: int = 0
    
    func: str = ""
    start: int = 0
    end: int = 0
    instrs: list[IRBlock] = field(default_factory=list)
    
    succ: dict[int, list[int]] = field(default_factory=dict)
    pred: dict[int, list[int]] = field(default_factory=dict)
    
    jmp: CFGBlock | None = None
    lin: CFGBlock | None = None
    