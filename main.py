from parser.parser import (
  Parser, ParserConfig, Language
)

from ir.translate import Translator
from ir.instr.ir_block import IRBlock
from ir.printer import pretty_print_ir

from ir.cfg.printer import cfg_to_dot
from ir.cfg.cfg import CFGBlock
from ir.cfg.cfggen import (
  get_blocks_from_ir,
  link_blocks
)

if __name__ == "__main__":
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

  print(f"1. Code: {code}")
  parser: Parser = Parser(
    conf=ParserConfig(code=code, lang=Language.CPL)
  )

  print("2. UAST:")
  uast = parser.parse()
  uast.print_uast()

  print("3. UIR:")
  translator: Translator = Translator(root=uast)
  instructions: list[IRBlock] = translator.translate()
  print(pretty_print_ir(instructions))

  print("3. CFG:")
  bblocks: list[CFGBlock] = get_blocks_from_ir(instructions=instructions)
  link_blocks(blocks=bblocks)
  print(cfg_to_dot(blocks=bblocks, show_instrs=False))
