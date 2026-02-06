from parser.parser import (
  Parser, ParserConfig, Language
)

from ir.translate import Translator
from ir.instr.ir_block import IRBlock
from ir.printer import pretty_print_ir

from ir.cfg.printer import cfg_to_dot, dom_tree_to_dot
from ir.cfg.cfg import CFGFunction
from ir.cfg.cfggen import (
  get_blocks_from_ir,
  link_blocks
)

from ir.cfg.dom import (
  complete_successors,
  compute_function_dom,
  compute_strict_dom
)

from ir.loop.ltree import (
  LoopNode,
  generate_loop_tree
)

if __name__ == "__main__":
  code = r"""
  {
    function foo();
    function main() {
      while 1; {
        while 1; {
          foo();
          break;
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
  funcs: list[CFGFunction] = get_blocks_from_ir(instructions=instructions)
  link_blocks(funcs=funcs)
  complete_successors(funcs=funcs)
  for func in funcs:
    print(f"3.1 func{func.id}:")
    print(cfg_to_dot(blocks=func.blocks, show_instrs=False))
    
    print(f"3.2 Dominators:")
    compute_function_dom(f=func)
    compute_strict_dom(f=func)
    print(dom_tree_to_dot(f=func))
    
  print("4. LOOP:")
  loops: list[LoopNode] = generate_loop_tree(funcs=funcs)
  def _print_loop(loop: LoopNode) -> None:
    print(f"loop: {str(loop)}")
    for child in loop.childs:
      _print_loop(loop=child)
  
  for loop in loops:
    _print_loop(loop=loop)
