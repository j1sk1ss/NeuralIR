from dataclasses import dataclass

from parser.parser import Parser

from ir.translate import Translator
from ir.cfg.cfg import CFGFunction
from ir.instr.ir_block import IRAction
from ir.printer import PrintStyle, pretty_print_ir
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
    generate_loop_tree,
    find_loop
)
from ir.loop.linfo import (
    LoopInfo,
    gather_loop_info
)
from ir.cfg.finfo import (
    CFGFunctionInfo,
    CFGInstructionInfo,
    gather_function_info,
    gather_instruction_info
)

@dataclass
class InstructionAnalysis:
    function: str                           # Function owner name
    block_id: int                           # CFG block owner Id
    action: IRAction                        # IRAction of this instruction
    called_function: str | None             # If this is the FCALL action, the name of which function is called
    instruction_info: CFGInstructionInfo    # Instruction basic information
    loop_info: LoopInfo | None              # Loop basic information

@dataclass
class FunctionAnalysis:
    name: str                               # Function name
    cfg: CFGFunction                        # Function's CFG
    info: CFGFunctionInfo                   # Function basic information
    instructions: list[InstructionAnalysis] # Info about each function's instruction

    def calls(self) -> list[InstructionAnalysis]:
        return [ i for i in self.instructions if i.action == IRAction.FCALL ]

class ProgramAnalysis:
    def __init__(self, parser: Parser):
        self.parser: Parser = parser
        self.functions: dict[str, FunctionAnalysis] = {}
        self.loops: list = []
        self.ir_form_debug: str = ""
        self._analyze()

    def _analyze(self) -> None:
        uast = self.parser.parse()

        translator = Translator(root=uast)
        ir_blocks = translator.translate()
        self.ir_form_debug = pretty_print_ir(blocks=ir_blocks, style=PrintStyle(show_index=True))

        funcs = get_blocks_from_ir(ir_blocks)
        link_blocks(funcs)
        complete_successors(funcs)

        for f in funcs:
            compute_function_dom(f)
            compute_strict_dom(f)

        self.loops = generate_loop_tree(funcs)

        for f in funcs:
            self.functions[f.func] = self._build_function_analysis(f)

    def _build_function_analysis(self, f: CFGFunction) -> FunctionAnalysis:
        instructions = []

        for bb in f.blocks:
            loop = find_loop(bb, self.loops)
            for inst in bb.instrs:
                instructions.append(
                    InstructionAnalysis(
                        function=f.func,
                        block_id=bb.id,
                        action=inst.a,
                        called_function=(
                            inst.subjects[0].name
                            if inst.a == IRAction.FCALL
                            else None
                        ),
                        instruction_info=gather_instruction_info(
                            f=f, bb=bb, inst=inst
                        ),
                        loop_info=(
                            gather_loop_info(self.loops, loop)
                            if loop else None
                        )
                    )
                )

        return FunctionAnalysis(
            name=f.func,
            cfg=f,
            info=gather_function_info(f),
            instructions=instructions
        )

    def print_ir(self) -> None:
        """Print the IR form of the code.
        """
        print(self.ir_form_debug)

    def get_function(self, name: str) -> FunctionAnalysis:
        """Get information about a function by the provided name.

        Args:
            name (str): Name of a function to search.

        Returns:
            FunctionAnalysis: Information about the found function.
        """
        return self.functions[name]

    def all_calls(self) -> list[InstructionAnalysis]:
        """Get all function calls from the provided code snippet.

        Returns:
            list[InstructionAnalysis]: List of analysis of function calls.
        """
        calls = []
        for f in self.functions.values():
            calls.extend(f.calls())
            
        return calls
