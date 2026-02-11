import re
import csv
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from parser.parser import Parser, ParserConfig, Language
from analysis.analyzer import ProgramAnalysis

class SimpleInlineMarkerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NeuralIR: inliner")
        self.geometry("1000x600")
        
        self.analyzer: ProgramAnalysis | None = None
        self.all_calls = []
        self.line_decisions = {}
        self.function_calls_by_line = {}
        self.original_lines = []
        
        self.setup_ui()
        
    def setup_ui(self):
        control_panel = ttk.Frame(self, padding=10)
        control_panel.pack(fill="x")
        
        ttk.Button(control_panel, text="Analyze Code", 
                  command=self.analyze_code, width=15).pack(side="left", padx=5)
        ttk.Button(control_panel, text="Load from File", 
                  command=self.load_code_file, width=15).pack(side="left", padx=5)
        ttk.Button(control_panel, text="Save to CSV", 
                  command=self.save_decisions, width=15).pack(side="left", padx=5)
        
        ttk.Label(control_panel, text="Language:").pack(side="left", padx=(20, 5))
        
        self.lang = tk.StringVar(value="C")
        self.lang_box = ttk.Combobox(
            control_panel,
            textvariable=self.lang,
            values=["C", "CPL", "RUST", "GO"],
            width=8,
            state="readonly",
        )
        self.lang_box.pack(side="left", padx=5)
        
        code_frame = ttk.Frame(self)
        code_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.text_frame = ttk.Frame(code_frame)
        self.text_frame.pack(fill="both", expand=True)
        
        self.line_numbers = tk.Text(self.text_frame, width=4, padx=5, pady=5, 
                                   takefocus=0, border=0, background='lightgrey',
                                   state='disabled')
        self.line_numbers.pack(side="left", fill="y")
        
        self.code_text = tk.Text(self.text_frame, wrap="none", font=("Courier", 10),
                                padx=5, pady=5, undo=True)
        self.code_text.pack(side="left", fill="both", expand=True)
        
        v_scrollbar = ttk.Scrollbar(code_frame, orient="vertical", 
                                   command=self.on_scroll)
        h_scrollbar = ttk.Scrollbar(code_frame, orient="horizontal",
                                   command=self.code_text.xview)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        self.code_text.configure(yscrollcommand=self.update_scroll)
        self.code_text.configure(xscrollcommand=h_scrollbar.set)
        
        self.code_text.bind("<Button-1>", self.on_text_click)
        self.code_text.bind("<KeyRelease>", self.update_line_numbers)
        
        self.status_label = ttk.Label(self, text="Ready")
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=5)
        
    def update_line_numbers(self, event=None):
        lines = self.code_text.get("1.0", "end-1c").split("\n")
        line_count = len(lines)
        
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        
        for i in range(1, line_count + 1):
            self.line_numbers.insert("end", f"{i}\n")
            
        self.line_numbers.config(state="disabled")
        
    def on_scroll(self, *args):
        self.code_text.yview(*args)
        self.line_numbers.yview(*args)
        
    def update_scroll(self, *args):
        self.on_scroll("moveto", args[0])
        
    def analyze_code(self):
        code = self.code_text.get("1.0", "end-1c")
        if not code.strip():
            messagebox.showwarning("Warning", "Please enter code to analyze")
            return
            
        try:
            self.analyzer = ProgramAnalysis(
                parser=Parser(
                    conf=ParserConfig(
                        code=code,
                        lang=Language.from_string(self.lang.get()),
                    )
                )
            )
            
            self.all_calls = self.analyzer.all_calls()
            
            self.line_decisions.clear()
            self.function_calls_by_line.clear()
            self.original_lines = code.split('\n')
            
            self.clear_highlights()
            self.map_calls_to_lines()
            self.highlight_calls()
            
            self.status_label.config(
                text=f"Found {len(self.all_calls)} function calls in {len(self.function_calls_by_line)} lines"
            )
            
        except Exception as e:
            messagebox.showerror("Analysis Error", str(e))
            self.status_label.config(text=f"Error: {str(e)}")
            
    def map_calls_to_lines(self):
        if not self.all_calls or not self.original_lines:
            return
            
        call_index = 0
        lines = self.original_lines
        
        for line_num, line in enumerate(lines, 1):
            line_calls = []
            
            if call_index < len(self.all_calls):
                call = self.all_calls[call_index]
                called_func = call.called_function
                
                if called_func and called_func in line:
                    if self.is_function_call_in_line(line, called_func):
                        line_calls.append(call)
                        call_index += 1
            
            if line_calls:
                self.function_calls_by_line[line_num] = line_calls
                
    def is_function_call_in_line(self, line, func_name):
        line = re.sub(r'//.*|/\*.*?\*/', '', line)

        pattern = rf'\b{func_name}\s*(?:<[^<>]*>)?\s*\('
        match = re.search(pattern, line)
        if not match:
            return False

        if re.match(r'.*\)\s*\{', line):
            return False

        before = line[:match.start()].strip()
        if re.match(r'^[\w:\*&<>\s]+$', before) and not any(
            sym in before for sym in ['=', 'return', '(', ',', ';']
        ):
            return False

        return True
    
    def clear_highlights(self):
        for tag in ["call_line", "inline_mark", "noinline_mark"]:
            self.code_text.tag_remove(tag, "1.0", "end")
            
    def highlight_calls(self):
        self.code_text.tag_config("call_line", background="#f0f0f0")
        self.code_text.tag_config("inline_mark", background="#d4edda")
        self.code_text.tag_config("noinline_mark", background="#f8d7da")
        
        for line_num in self.function_calls_by_line.keys():
            start = f"{line_num}.0"
            end = f"{line_num}.end"
            
            decision = self.line_decisions.get(line_num)
            if decision == "inline":
                self.code_text.tag_add("inline_mark", start, end)
            elif decision == "noinline":
                self.code_text.tag_add("noinline_mark", start, end)
            else:
                self.code_text.tag_add("call_line", start, end)
                
    def on_text_click(self, event):
        index = self.code_text.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        
        if line_num not in self.function_calls_by_line:
            return
            
        current = self.line_decisions.get(line_num)
        if current == "inline":
            new_decision = "noinline"
        elif current == "noinline":
            new_decision = None
        else:
            new_decision = "inline"
            
        if new_decision is None:
            if line_num in self.line_decisions:
                del self.line_decisions[line_num]
        else:
            self.line_decisions[line_num] = new_decision
            
        self.clear_highlights()
        self.highlight_calls()
        
        calls_in_line = self.function_calls_by_line[line_num]
        func_names = ", ".join(set(call.called_function for call in calls_in_line))
        decision_text = "INLINE" if new_decision == "inline" else "NOINLINE" if new_decision == "noinline" else "UNMARKED"
        self.status_label.config(
            text=f"Line {line_num}: {func_names} - {decision_text}"
        )
        
    def load_code_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("C files", "*.c"),
                ("C++ files", "*.cpp;*.cc;*.cxx;*.h;*.hpp"),
                ("Rust files", "*.rs"),
                ("Go files", "*.go"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    
                self.code_text.delete("1.0", "end")
                self.code_text.insert("1.0", code)
                self.update_line_numbers()
                
                ext = file_path.lower().split('.')[-1]
                lang_map = {
                    'c': 'C', 'cpp': 'C', 'cc': 'C', 'cxx': 'C',
                    'h': 'C', 'hpp': 'C',
                    'rs': 'RUST',
                    'go': 'GO',
                    'cpl': 'CPL'
                }
                
                if ext in lang_map:
                    self.lang.set(lang_map[ext])
                    
                self.status_label.config(text=f"Loaded: {file_path}")
                
                self.analyzer = None
                self.all_calls = []
                self.line_decisions.clear()
                self.function_calls_by_line.clear()
                self.clear_highlights()
                
            except Exception as e:
                messagebox.showerror("Load Error", str(e))
                
    def save_decisions(self):
        if not self.function_calls_by_line:
            messagebox.showwarning("Warning", "No function calls to save. Please run analysis first.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"inline_decisions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                writer.writerow([
                    'line_number', 'line_content', 'owner_function', 
                    'called_function', 'block_id', 'action',
                    'is_dominated', 'similar_after', 'similar_before', 
                    'distance_to_break', 'has_loop_info', 'inline_decision'
                ])
                
                for line_num, calls in self.function_calls_by_line.items():
                    line_content = self.original_lines[line_num-1] if line_num-1 < len(self.original_lines) else ""
                    decision = self.line_decisions.get(line_num, "unmarked")
                    
                    for call in calls:
                        writer.writerow([
                            line_num,
                            line_content.strip(),
                            call.function if hasattr(call, 'function') else 'unknown',
                            call.called_function,
                            call.block_id,
                            call.action.name,
                            call.instruction_info.is_dominated,
                            call.instruction_info.same_inst_after,
                            call.instruction_info.same_inst_before,
                            call.instruction_info.near_break if call.instruction_info.near_break != -1 else 'N/A',
                            'YES' if call.loop_info else 'NO',
                            decision.upper() if decision != "unmarked" else "UNMARKED"
                        ])
            
            function_file_path = file_path.replace('.csv', '_functions.csv')
            self.save_function_analysis(function_file_path)
            
            messagebox.showinfo("Success", f"Decisions saved to:\n{file_path}\nFunction analysis saved to:\n{function_file_path}")
            self.status_label.config(text=f"Saved to: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save CSV: {str(e)}")
            
    def save_function_analysis(self, file_path):
        if not self.analyzer:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                writer.writerow([
                    'function_name', 'basic_blocks', 'ir_instructions',
                    'is_start_function', 'function_calls', 'system_calls',
                    'total_instructions', 'call_count'
                ])
                
                all_called_functions = set()
                for calls in self.function_calls_by_line.values():
                    for call in calls:
                        if call.called_function:
                            all_called_functions.add(call.called_function)
                
                for func_name in all_called_functions:
                    if func_name in self.analyzer.functions:
                        func = self.analyzer.functions[func_name]
                        calls_count = len(func.calls())
                        
                        writer.writerow([
                            func.name,
                            func.info.bb_count,
                            func.info.ir_count,
                            func.info.is_start,
                            func.info.funccalls,
                            func.info.syscalls if func.info.syscalls != -1 else 'N/A',
                            len(func.instructions),
                            calls_count
                        ])
                        
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save function analysis: {str(e)}")
            
if __name__ == "__main__":
    app = SimpleInlineMarkerApp()
    app.mainloop()
    