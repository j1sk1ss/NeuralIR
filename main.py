from parser.parser import (
  Parser, ParserConfig, Language
)

from ir.translate import Translator
from ir.printer import pretty_print_ir
from ir.instr.ir_block import IRBlock

code = r"""
{
  function foo();
  function main() {
    while 1; {
      while 1; {
        foo();
      }
    }
  }
}
"""

parser: Parser = Parser(
  conf=ParserConfig(code=code, lang=Language.CPL)
)

uast = parser.parse()
uast.print_uast()

translator: Translator = Translator(root=uast)
instructions: list[IRBlock] = translator.translate()
print(pretty_print_ir(instructions))
