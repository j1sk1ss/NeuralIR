from ir.instr.ir_block import (
    IRBlock, IRAction, IRSubject, IRLabel, IROperation,
    IRFunction
)

from parser.uast import (
    UastNode, FunctionNode, FunctionCallNode,
    RExitNode, LoopNode, SwitchNode, DeclarationNode,
    BinaryNode, UnaryNode, ConditionNode, ElseNode, 
    ConditionElseNode, BreakNode
)

class Translator:
    def __init__(self, root: UastNode) -> None:
        self.root: UastNode = root
        self.ctx: list[IRBlock] = []
        self.brk_ctx: list[IRLabel] = []
        
    def translate(self) -> list[IRBlock]:
        self.translate_uast_node(self.root)
        return self.ctx
    
    def translate_uast_node(self, node: UastNode) -> None:
        if not node:
            return
        
        if isinstance(node, FunctionNode):
            self.translate_function_node(node)
        elif isinstance(node, FunctionCallNode):
            self.translate_funccall_node(node)
        elif isinstance(node, RExitNode):
            self.translate_rexit_node(node)
        elif isinstance(node, LoopNode):
            self.translate_loop_node(node)
        elif isinstance(node, SwitchNode):
            self.translate_switch_node(node)
        elif isinstance(node, DeclarationNode):
            self.translate_declaration_node(node)
        elif isinstance(node, BinaryNode):
            self.translate_binary_node(node)
        elif isinstance(node, UnaryNode):
            self.translate_unary_node(node)
        elif isinstance(node, ConditionNode):
            self.translate_condition_node(node)
        elif isinstance(node, ConditionElseNode):
            self.translate_conditionelse_node(node)
        elif isinstance(node, ElseNode):
            self.translate_else_node(node)
        elif isinstance(node, BreakNode):
            self.translate_break_node(node)
        else:
            if node.childs:
                for child in node.childs:
                    self.translate_uast_node(child)
            else:
                self.ctx.append(IRBlock(a=IRAction.NOTHING))
    
    def translate_function_node(self, node: FunctionNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.FDECL, x=IRFunction(name=node.get_name())))
        self.translate_uast_node(node.get_body())
        self.ctx.append(IRBlock(a=IRAction.FEND))
    
    def translate_funccall_node(self, node: FunctionCallNode) -> None:
        self.translate_uast_node(node.get_args())
        self.ctx.append(IRBlock(a=IRAction.FCALL, x=IRFunction(name=node.get_name())))
    
    def translate_rexit_node(self, node: RExitNode) -> None:
        self.translate_uast_node(node.get_retval())
        self.ctx.append(IRBlock(a=IRAction.TERM))
    
    def translate_break_node(self, node: BreakNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.BREAK))
        self.ctx.append(IRBlock(a=IRAction.JMP, x=self.brk_ctx.pop()))
    
    def translate_loop_node(self, node: LoopNode) -> None:
        entry_lb: IRSubject = IRLabel()
        body_lb: IRSubject  = IRLabel()
        exit_lb: IRSubject  = IRLabel()
        self.ctx.append(IRBlock(a=IRAction.MKLB, x=entry_lb))
        # self.ctx.append(IRBlock(a=IRAction.LOOP))
        
        self.translate_uast_node(node.get_cond())
        self.ctx.append(IRBlock(a=IRAction.IF, x=body_lb, y=exit_lb))
        
        self.ctx.append(IRBlock(a=IRAction.MKLB, x=body_lb))
        self.brk_ctx.append(exit_lb)
        self.translate_uast_node(node.get_body())
        self.ctx.append(IRBlock(a=IRAction.JMP, x=entry_lb))
        
        self.ctx.append(IRBlock(a=IRAction.MKLB, x=exit_lb))
    
    def translate_switch_node(self, node: SwitchNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.SWITCH))
        self.translate_uast_node(node.get_cond())
        
        case_index: int = 0
        while node.get_case(case_index):
            true_lb: IRSubject  = IRLabel()
            false_lb: IRSubject = IRLabel()
            self.ctx.append(IRBlock(a=IRAction.IF, x=true_lb, y=false_lb))
            self.ctx.append(IRBlock(a=IRAction.MKLB, x=true_lb))
            self.brk_ctx.append(false_lb)
            self.translate_uast_node(node.get_case(case_index))
            self.ctx.append(IRBlock(a=IRAction.MKLB, x=false_lb))
            case_index += 1
    
    def translate_declaration_node(self, node: DeclarationNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.DECL, x=IROperation(op=node.get_type())))
        self.translate_uast_node(node.get_val())
    
    def translate_binary_node(self, node: BinaryNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.BINARY, x=IROperation(op=node.get_op().name)))
    
    def translate_unary_node(self, node: UnaryNode) -> None:
        self.ctx.append(IRBlock(a=IRAction.UNARY, x=IROperation(op=node.get_op().name)))
    
    def translate_condition_node(self, node: ConditionNode) -> None:
        true_lb: IRSubject  = IRLabel()
        false_lb: IRSubject = IRLabel()
        self.ctx.append(IRBlock(a=IRAction.IF, x=true_lb, y=false_lb))
        self.translate_uast_node(node.get_cond())
        
        if node.get_true():
            self.ctx.append(IRBlock(a=IRAction.MKLB, x=true_lb))
            self.translate_uast_node(node.get_true())
            
        if node.get_false():
            self.ctx.append(IRBlock(a=IRAction.MKLB, x=false_lb))
            self.translate_uast_node(node.get_false())
    
    def translate_conditionelse_node(self, node: ConditionElseNode) -> None:
        self.translate_condition_node(node.get_cond())
    
    def translate_else_node(self, node: ElseNode) -> None:
        self.translate_uast_node(node.get_body())
    