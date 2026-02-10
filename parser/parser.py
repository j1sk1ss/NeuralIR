from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

from parser.uast import UastNode
from parser.c.pyc_to_uast import c_code_to_uast
from parser.cpl.cpl_to_uast import cpl_code_to_uast

class Language(Enum):
    C       = 1
    CPL     = 2
    UNKNOWN = 3
    
    def from_string(name: str) -> Language:
        if name == 'C':
            return Language.C
        elif name == 'CPL':
            return Language.CPL
        else:
            return Language.UNKNOWN

@dataclass
class ParserConfig:
    file: str | None = None
    code: str | None = None
    lang: Language   = Language.C

class Parser:
    def __init__(self, conf: ParserConfig) -> None:
        self.conf: ParserConfig = conf

    def parse(self) -> UastNode:
        if not self.conf.code and not self.conf.file:
            raise FileNotFoundError("Neither file nor code is provided!")
        
        if not self.conf.code:
            with open(self.conf.file, 'r') as f:
                self.conf.code = f.read()

        if self.conf.lang == Language.C:
            return c_code_to_uast(code=self.conf.code)
        elif self.conf.lang == Language.CPL:
            return cpl_code_to_uast(code=self.conf.code)
        
        return None
