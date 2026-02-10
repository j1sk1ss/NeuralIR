import traceback
import tkinter as tk
from tkinter import ttk

from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

class CodeTab(ttk.Frame):
    def __init__(self, master, title: str):
        super().__init__(master)
        self.master = master
        self.title = title
        self.analyzer: ProgramAnalysis | None = None
        self.function_calls_map = {}
        
        top = ttk.Frame(self)
        top.pack(fill="x", padx=5, pady=5)

        ttk.Label(top, text="Language:").pack(side="left")

        self.lang = tk.StringVar(value="CPL")
        self.lang_box = ttk.Combobox(
            top,
            textvariable=self.lang,
            values=[l.name for l in Language],
            width=10,
            state="readonly",
        )
        self.lang_box.pack(side="left", padx=5)

        ttk.Button(top, text="-", width=3, command=self.close_tab).pack(side="right")

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=5, pady=5)

        left = ttk.Frame(main)
        main.add(left, weight=1)

        ttk.Label(left, text="Function Calls").pack(anchor="w")

        self.tree = ttk.Treeview(left, columns=("info",), show="tree")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        right = ttk.Frame(main)
        main.add(right, weight=3)

        ttk.Label(right, text="Source Code").pack(anchor="w")

        self.editor = tk.Text(right, height=12)
        self.editor.pack(fill="x", expand=False)

        ttk.Button(right, text="Analyze", command=self.run_analysis).pack(pady=5)

        ttk.Label(right, text="Analysis Output").pack(anchor="w")

        self.output = tk.Text(right, height=15)
        self.output.pack(fill="both", expand=True)

    def close_tab(self):
        self.master.forget(self)

    def run_analysis(self):
        self.tree.delete(*self.tree.get_children())
        self.output.delete("1.0", tk.END)
        self.analyzer = None
        self.function_calls_map.clear()

        code = self.editor.get("1.0", tk.END)

        try:
            analyzer = ProgramAnalysis(
                parser=Parser(
                    ParserConfig(
                        code=code,
                        lang=Language.from_string(self.lang.get()),
                    )
                )
            )
            
            self.analyzer = analyzer
            
            try:
                self.populate_tree(analyzer)
            except Exception as ex:
                raise Exception(f"populate_tree error: {str(ex)}\n{traceback.format_exc()}")
            
            self.output.insert(tk.END, "Analysis completed successfully.")
        except Exception as e:
            self.output.insert(tk.END, str(e))

    def populate_tree(self, analyzer: ProgramAnalysis):
        for fn, info in analyzer.functions.items():
            fn_id = self.tree.insert(
                "", "end", text=f"Function: {fn}", values=(fn,)
            )

            for call in info.calls():
                call_key = f"{fn}:{call.block_id}:{call.action}:{call.called_function}"
                self.function_calls_map[call_key] = call
                self.tree.insert(
                    fn_id,
                    "end",
                    text=f"call {call.called_function}",
                    values=(call_key,),
                )

    def format_function_info(self, func_name: str) -> str:
        if not self.analyzer or func_name not in self.analyzer.functions:
            return f"Function '{func_name}' not found"
        
        func = self.analyzer.functions[func_name]
        lines = [
            "=" * 50,
            f"FUNCTION: {func.name}",
            "=" * 50,
            f"Basic blocks: {func.info.bb_count}",
            f"IR instructions: {func.info.ir_count}",
            f"Is start function: {func.info.is_start}",
            f"Function calls: {func.info.funccalls}",
            f"System calls: {func.info.syscalls if func.info.syscalls != -1 else 'Not supported'}",
            "",
            f"Total instructions: {len(func.instructions)}",
            f"Calls to other functions: {len(func.calls())}",
            "",
            "Instructions by action type:"
        ]
        
        action_counts = {}
        for instr in func.instructions:
            action_name = instr.action.name
            action_counts[action_name] = action_counts.get(action_name, 0) + 1
        
        for action, count in sorted(action_counts.items()):
            lines.append(f"  {action}: {count}")
        
        return "\n".join(lines)

    def format_instruction_info(self, instr) -> str:
        if not hasattr(instr, 'action'):
            return f"Invalid instruction object: {instr}"
        
        lines = [
            "=" * 50,
            f"FUNCTION CALL ANALYSIS",
            "=" * 50,
            f"Function: {instr.function}",
            f"Block ID: {instr.block_id}",
            f"Action: {instr.action.name}",
        ]
        
        if instr.called_function:
            lines.append(f"Called function: {instr.called_function}")
        
        lines.extend([
            "",
            "Instruction Info:",
            f"  Is dominated: {instr.instruction_info.is_dominated}",
            f"  Similar instructions after: {instr.instruction_info.same_inst_after}",
            f"  Similar instructions before: {instr.instruction_info.same_inst_before}",
        ])
        
        if instr.instruction_info.near_break != -1:
            lines.append(f"  Distance to nearest break: {instr.instruction_info.near_break}")
        else:
            lines.append(f"  Distance to nearest break: No break in block")
        
        if instr.loop_info:
            lines.extend([
                "",
                "Loop Info:",
                f"  Loop size (basic blocks): {instr.loop_info.loop_size_bb}",
                f"  Loop size (IR instructions): {instr.loop_info.loop_size_ir}",
                f"  Loop nesting depth: {instr.loop_info.loop_nested}",
            ])
        
        return "\n".join(lines)

    def on_tree_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        item_values = self.tree.item(sel[0], "values")
        if not item_values:
            return
            
        obj_key = item_values[0]
        
        self.output.delete("1.0", tk.END)
        
        if obj_key in self.function_calls_map:
            instruction = self.function_calls_map[obj_key]
            formatted = self.format_instruction_info(instruction)
        else:
            formatted = self.format_function_info(obj_key)
        
        self.output.insert(tk.END, formatted)

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NeuralIR")
        self.geometry("1000x600")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.add_tab()
        self.add_plus_tab()

    def add_tab(self):
        title = f"Tab {len(self.notebook.tabs())}"
        tab = CodeTab(self.notebook, title)
        self.notebook.insert("end", tab, text=title)
        self.notebook.select(tab)

    def add_plus_tab(self):
        self.plus_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.plus_tab, text="+")

    def on_tab_change(self, _):
        if self.notebook.select() == str(self.plus_tab):
            self.notebook.forget(self.plus_tab)
            self.add_tab()
            self.add_plus_tab()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
