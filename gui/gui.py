import csv
import traceback
import tkinter as tk

from datetime import datetime
from tkinter import ttk, filedialog, messagebox
from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

class CodeTab(ttk.Frame):
    def __init__(self, master, title: str):
        super().__init__(master)
        self.master = master
        self.title = title
        self.analyzer: ProgramAnalysis | None = None
        self.function_calls_map = {}
        self.excluded_items = set()
        
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
        
        tree_controls = ttk.Frame(left)
        tree_controls.pack(fill="x", pady=(0, 5))
        
        ttk.Button(tree_controls, text="Exclude", width=8, 
                  command=self.exclude_selected).pack(side="left", padx=(0, 5))
        ttk.Button(tree_controls, text="Include", width=8,
                  command=self.include_selected).pack(side="left")
        
        ttk.Button(tree_controls, text="Clear All", width=8,
                  command=self.clear_exclusions).pack(side="right")

        self.tree = ttk.Treeview(left, columns=("info",), show="tree")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure('excluded', foreground='gray')
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.show_context_menu)

        right = ttk.Frame(main)
        main.add(right, weight=3)

        ttk.Label(right, text="Source Code").pack(anchor="w")

        self.editor = tk.Text(right, height=12)
        self.editor.pack(fill="x", expand=False)

        button_frame = ttk.Frame(right)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Analyze", command=self.run_analysis).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Save to CSV", command=self.save_to_csv).pack(side="left")

        ttk.Label(right, text="Analysis Output").pack(anchor="w", pady=(10, 0))

        self.output = tk.Text(right, height=15)
        self.output.pack(fill="both", expand=True)

    def close_tab(self):
        self.master.forget(self)

    def run_analysis(self):
        self.tree.delete(*self.tree.get_children())
        self.output.delete("1.0", tk.END)
        self.analyzer = None
        self.function_calls_map.clear()
        self.excluded_items.clear()

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
            tags = ('excluded',) if fn in self.excluded_items else ()
            fn_id = self.tree.insert(
                "", "end", text=f"Function: {fn}", values=(fn,), tags=tags
            )

            for call in info.calls():
                call_key = f"{fn}:{call.block_id}:{call.action}:{call.called_function}"
                self.function_calls_map[call_key] = call
                
                call_tags = ('excluded',) if call_key in self.excluded_items else ()
                self.tree.insert(
                    fn_id,
                    "end",
                    text=f"call {call.called_function}",
                    values=(call_key,),
                    tags=call_tags
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

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Exclude from CSV", command=lambda: self.exclude_selected())
            menu.add_command(label="Include in CSV", command=lambda: self.include_selected())
            menu.add_separator()
            menu.add_command(label="Exclude Function with All Calls", 
                           command=lambda: self.exclude_function_with_calls())
            
            menu.tk_popup(event.x_root, event.y_root)

    def exclude_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
            
        item = sel[0]
        item_values = self.tree.item(item, "values")
        if not item_values:
            return
            
        obj_key = item_values[0]
        self.excluded_items.add(obj_key)
        self.tree.item(item, tags=('excluded',))
        
        if obj_key not in self.function_calls_map:
            children = self.tree.get_children(item)
            for child in children:
                child_values = self.tree.item(child, "values")
                if child_values:
                    child_key = child_values[0]
                    self.excluded_items.add(child_key)
                    self.tree.item(child, tags=('excluded',))
        
        self.output.insert(tk.END, f"\nExcluded: {obj_key}")

    def include_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
            
        item = sel[0]
        item_values = self.tree.item(item, "values")
        if not item_values:
            return
            
        obj_key = item_values[0]
        
        if obj_key in self.excluded_items:
            self.excluded_items.remove(obj_key)
            self.tree.item(item, tags=())
            
            if obj_key not in self.function_calls_map:
                children = self.tree.get_children(item)
                for child in children:
                    child_values = self.tree.item(child, "values")
                    if child_values:
                        child_key = child_values[0]
                        if child_key in self.excluded_items:
                            self.excluded_items.remove(child_key)
                            self.tree.item(child, tags=())
        
        self.output.insert(tk.END, f"\nIncluded: {obj_key}")

    def exclude_function_with_calls(self):
        sel = self.tree.selection()
        if not sel:
            return
            
        item = sel[0]
        item_values = self.tree.item(item, "values")
        if not item_values:
            return
            
        obj_key = item_values[0]
        
        if obj_key in self.function_calls_map:
            messagebox.showwarning("Warning", "Please select a function, not a call")
            return
            
        self.excluded_items.add(obj_key)
        self.tree.item(item, tags=('excluded',))
        
        children = self.tree.get_children(item)
        for child in children:
            child_values = self.tree.item(child, "values")
            if child_values:
                child_key = child_values[0]
                self.excluded_items.add(child_key)
                self.tree.item(child, tags=('excluded',))
        
        self.output.insert(tk.END, f"\nExcluded function with all calls: {obj_key}")

    def clear_exclusions(self):
        self.excluded_items.clear()
        for item in self.tree.get_children():
            self.tree.item(item, tags=())
            children = self.tree.get_children(item)
            for child in children:
                self.tree.item(child, tags=())
        
        self.output.insert(tk.END, "\nAll exclusions cleared")

    def save_to_csv(self):
        if not self.analyzer:
            messagebox.showerror("Error", "No analysis data to save. Please run analysis first.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                writer.writerow([
                    'Type', 'Function Name', 'Called Function', 'Block ID', 'Action',
                    'Basic Blocks', 'IR Instructions', 'Is Start Function', 
                    'Function Calls', 'System Calls', 'Total Instructions',
                    'Is Dominated', 'Similar After', 'Similar Before', 
                    'Distance to Break', 'Loop Size BB', 'Loop Size IR', 'Loop Nested',
                    'Excluded'
                ])
                
                for func_name, func in self.analyzer.functions.items():
                    if func_name in self.excluded_items:
                        continue
                    
                    writer.writerow([
                        'FUNCTION',                                                                                 # Type
                        func.name,                                                                                  # Function Name
                        '', '', '',                                                                                 # Padding #1
                        func.info.bb_count,                                                                         # Basic Blocks
                        func.info.ir_count,                                                                         # IR Instructions
                        func.info.is_start,                                                                         # Is Start Function
                        func.info.funccalls,                                                                        # Function Calls
                        func.info.syscalls if func.info.syscalls != -1 else 'N/A',                                  # System Calls
                        len(func.instructions),                                                                     # Total Instructions
                        '', '', '', '', '', '', '',                                                                 # Padding #2
                        'YES' if func_name in self.excluded_items else 'NO'                                         # Excluded
                    ])
                    
                    for call in func.calls():
                        call_key = f"{func_name}:{call.block_id}:{call.action}:{call.called_function}"
                        
                        if call_key in self.excluded_items:
                            continue
                        
                        writer.writerow([
                            'CALL',                                                                                 # Type
                            call.function,                                                                          # Function Name
                            call.called_function,                                                                   # Called Function
                            call.block_id,                                                                          # Block ID
                            call.action.name,                                                                       # Action
                            '', '', '', '', '', '',                                                                 # Padding
                            call.instruction_info.is_dominated,                                                     # Is Dominated
                            call.instruction_info.same_inst_after,                                                  # Similar After
                            call.instruction_info.same_inst_before,                                                 # Similar Before
                            call.instruction_info.near_break if call.instruction_info.near_break != -1 else 'N/A',  # Distance to Break
                            call.loop_info.loop_size_bb if call.loop_info else '',                                  # Loop Size BB
                            call.loop_info.loop_size_ir if call.loop_info else '',                                  # Loop Size IR
                            call.loop_info.loop_nested if call.loop_info else '',                                   # Loop Nested
                            'YES' if call_key in self.excluded_items else 'NO'                                      # Excluded
                        ])
                
            messagebox.showinfo("Success", f"Analysis saved to:\n{file_path}")
            self.output.insert(tk.END, f"\n\nAnalysis saved to: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV: {str(e)}")
            self.output.insert(tk.END, f"\n\nError saving CSV: {str(e)}")

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
