from parser.parser import (
  Parser, ParserConfig, Language
)

from ir.translate import Translator
from ir.instr.ir_block import IRBlock, IRAction
from ir.printer import pretty_print_ir, PrintStyle

from ir.cfg.printer import cfg_to_dot, dom_tree_to_dot
from ir.cfg.cfg import CFGFunction
from ir.cfg.cfggen import (
  get_blocks_from_ir,
  give_flatten_instructions,
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

from ir.loop.linfo import (
  gather_loop_info
)

from ir.cfg.finfo import (
  gather_function_info,
  gather_instruction_info
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
  print(pretty_print_ir(instructions, style=PrintStyle(show_index=False)))

  print("4. CFG:")
  funcs: list[CFGFunction] = get_blocks_from_ir(instructions=instructions)
  link_blocks(funcs=funcs)
  complete_successors(funcs=funcs)
  for func in funcs:
    print(f"4.1 {func.func}:")
    print(cfg_to_dot(blocks=func.blocks, show_instrs=False))
    
    print(f"4.2 Dominators:")
    compute_function_dom(f=func)
    compute_strict_dom(f=func)
    print(dom_tree_to_dot(f=func))
    
    print("4.3 UIRv2:")
    print(pretty_print_ir(give_flatten_instructions(f=func), style=PrintStyle(show_index=True)))
    
  print("5. LOOP:")
  loops: list[LoopNode] = generate_loop_tree(funcs=funcs)
  def _print_loop(loop: LoopNode, loops: list[LoopNode]) -> None:
    print(f"loop: {str(loop)}, Info: {gather_loop_info(loops=loops, trg=loop)}")
    for child in loop.childs:
      _print_loop(loop=child, loops=loops)
  
  for loop in loops:
    _print_loop(loop=loop, loops=loops)
    
  print("6. Funcs info:")
  for func in funcs:
    print(f"{func.func} / {gather_function_info(f=func)}")
    
  print("7. FOO() instruction:")
  for func in funcs:
    for block in func.blocks:
      for inst in block.instrs:
        if inst.a == IRAction.FCALL:
          print(f"fcall / {gather_instruction_info(f=func, bb=block, inst=inst)}")
