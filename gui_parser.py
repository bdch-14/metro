import re
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

class GroovyMetricsParser:
    def __init__(self):
        self.re_single_comment = re.compile(r'//.*$')
        self.re_multi_comment = re.compile(r'/\*.*?\*/', re.DOTALL)

    def remove_comments_and_strings(self, code: str) -> str:
        code = self.re_multi_comment.sub('', code)
        clean_lines = []
        for line in code.splitlines():
            line_no_str = re.sub(r'(".*?"|\'.*?\')', '""', line)
            line_clean = self.re_single_comment.sub('', line_no_str)
            clean_lines.append(line_clean)
        return '\n'.join(clean_lines)

    def analyze(self, raw_code: str):
        cleaned_code = self.remove_comments_and_strings(raw_code)
        lines = [line.strip() for line in cleaned_code.splitlines()]
        
        total_statements = 0
        cl_count = 0
        current_nesting = 0
        max_cli = 0
        details = []

        block_stack = []

        for line_idx, line in enumerate(lines, 1):
            if not line:
                continue

            stmts_in_line = len([s for s in line.split(';') if s.strip()])
            if stmts_in_line > 0:
                total_statements += max(1, stmts_in_line)
            else:
                total_statements += 1

            is_branch = False
            branch_type = ""

            if re.search(r'\b(if|else\s+if)\b', line):
                is_branch = True
                branch_type = "Условие IF"
            elif re.search(r'\b(while|for)\b', line):
                is_branch = True
                branch_type = f"Цикл {re.search(r'\b(while|for)\b', line).group(0).upper()}"
            elif re.search(r'\bcase\b', line):
                if not re.search(r'\bdefault\b', line):
                    is_branch = True
                    branch_type = "Ветка CASE"

            open_braces = line.count('{')
            close_braces = line.count('}')

            for _ in range(close_braces):
                if block_stack:
                    kind = block_stack.pop()
                    if kind == 'branch' and current_nesting > 0:
                        current_nesting -= 1

            if is_branch:
                cl_count += 1
                current_nesting += 1
                if current_nesting > max_cli:
                    max_cli = current_nesting
                details.append((line_idx, line, branch_type, current_nesting))
                if open_braces > 0:
                    block_stack.append('branch')
                    for _ in range(open_braces - 1):
                        block_stack.append('block')
            else:
                for _ in range(open_braces):
                    block_stack.append('block')

        rel_complexity = (cl_count / total_statements) if total_statements > 0 else 0.0

        return {
            "CL": cl_count,
            "N": total_statements,
            "cl": round(rel_complexity, 3),
            "CLI": max_cli,
            "details": details
        }


class LightMetricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CodeFlow Analyzer - Groovy Complexity Toolkit")
        self.root.geometry("1020x680")
        self.root.minsize(850, 550)
        self.root.configure(bg="#eef2f6")

        self.parser = GroovyMetricsParser()
        self.setup_ui()
        self.load_sample()

    def setup_ui(self):
        # Верхняя навигационная панель
        nav_bar = tk.Frame(self.root, bg="#ffffff", height=50, bd=1, relief=tk.SOLID)
        nav_bar.pack(fill=tk.X, side=tk.TOP)
        nav_bar.pack_propagate(False)

        title_lbl = tk.Label(
            nav_bar, 
            text="Анализ метрик Джилба (Groovy)", 
            font=("Helvetica", 13, "bold"), 
            fg="#1e293b", 
            bg="#ffffff"
        )
        title_lbl.pack(side=tk.LEFT, padx=15)

        btn_open = tk.Button(
            nav_bar, 
            text="📂 Открыть .groovy", 
            command=self.load_file, 
            bg="#f1f5f9", 
            fg="#334155", 
            relief=tk.GROOVE, 
            bd=1,
            font=("Helvetica", 9, "bold"),
            padx=10, 
            pady=4
        )
        btn_open.pack(side=tk.RIGHT, padx=10, pady=8)

        btn_run = tk.Button(
            nav_bar, 
            text="▶ Выполнить анализ", 
            command=self.calculate, 
            bg="#2563eb", 
            fg="#ffffff", 
            activebackground="#1d4ed8", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            font=("Helvetica", 9, "bold"),
            padx=14, 
            pady=5, 
            cursor="hand2"
        )
        btn_run.pack(side=tk.RIGHT, padx=5, pady=8)

        # Главный контейнер
        content = tk.Frame(self.root, bg="#eef2f6")
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Левая часть: вкладки редактора и таблицы ветвлений
        left_box = tk.Frame(content, bg="#ffffff", bd=1, relief=tk.SOLID)
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.notebook = ttk.Notebook(left_box)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка 1: Редактор
        tab_editor = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(tab_editor, text=" Исходный текст программы ")

        self.txt_code = scrolledtext.ScrolledText(
            tab_editor, 
            wrap=tk.NONE, 
            font=("DejaVu Sans Mono", 10), 
            bg="#f8fafc", 
            fg="#0f172a", 
            insertbackground="#0f172a",
            bd=0,
            padx=8,
            pady=8
        )
        self.txt_code.pack(fill=tk.BOTH, expand=True)

        # Вкладка 2: Таблица ветвлений
        tab_table = tk.Frame(self.notebook, bg="#ffffff")
        self.notebook.add(tab_table, text=" Таблица ветвлений и глубина ")

        cols = ("line", "type", "nesting", "content")
        self.tree = ttk.Treeview(tab_table, columns=cols, show='headings', selectmode="browse")
        self.tree.heading("line", text="Строка")
        self.tree.heading("type", text="Конструкция")
        self.tree.heading("nesting", text="Глубина (CLI)")
        self.tree.heading("content", text="Фрагмент кода")

        self.tree.column("line", width=65, anchor=tk.CENTER)
        self.tree.column("type", width=140, anchor=tk.W)
        self.tree.column("nesting", width=90, anchor=tk.CENTER)
        self.tree.column("content", width=380, anchor=tk.W)

        scr_tree = ttk.Scrollbar(tab_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scr_tree.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr_tree.pack(side=tk.RIGHT, fill=tk.Y)

        # Правая панель: Сводные карточки метрик
        right_panel = tk.Frame(content, bg="#ffffff", width=280, bd=1, relief=tk.SOLID)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)

        side_title = tk.Label(
            right_panel, 
            text="МЕТРИКИ ДЖИЛБА", 
            font=("Helvetica", 10, "bold"), 
            fg="#64748b", 
            bg="#ffffff"
        )
        side_title.pack(anchor=tk.W, padx=15, pady=(15, 10))

        self.val_cl = self.create_metric_row(right_panel, "Абсолютная сложность (CL)", "0", "#0284c7")
        self.val_cli = self.create_metric_row(right_panel, "Макс. глубина (CLI)", "0", "#7c3aed")
        self.val_n = self.create_metric_row(right_panel, "Всего операторов (N)", "0", "#334155")
        self.val_cl_rel = self.create_metric_row(right_panel, "Относительная сложность (cl)", "0.000", "#059669")

        # Блок методических пояснений
        info_frame = tk.LabelFrame(right_panel, text=" Формулы ", bg="#ffffff", fg="#475569", font=("Helvetica", 8, "bold"), padx=10, pady=8)
        info_frame.pack(fill=tk.X, padx=12, pady=(15, 5))

        formula_text = (
            "• CL = сумма всех условий и циклов\n"
            "• CLI = максимальная вложенность\n"
            "• cl = CL / N (насыщенность ветвлениями)\n"
            "• case развернут в n-1 условий"
        )
        lbl_formula = tk.Label(info_frame, text=formula_text, justify=tk.LEFT, font=("Helvetica", 8), bg="#ffffff", fg="#64748b")
        lbl_formula.pack(anchor=tk.W)

        # Статусная панель
        self.status_bar = tk.Label(
            self.root, 
            text="Готов к работе. Введите код или загрузите файл.", 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W, 
            font=("Helvetica", 8), 
            bg="#e2e8f0", 
            fg="#475569",
            padx=10,
            pady=3
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_metric_row(self, parent, title, init_value, accent_color):
        block = tk.Frame(parent, bg="#f8fafc", bd=1, relief=tk.SOLID, padx=10, pady=8)
        block.pack(fill=tk.X, padx=12, pady=5)

        t_lbl = tk.Label(block, text=title, font=("Helvetica", 8), fg="#64748b", bg="#f8fafc")
        t_lbl.pack(anchor=tk.W)

        v_lbl = tk.Label(block, text=init_value, font=("Helvetica", 16, "bold"), fg=accent_color, bg="#f8fafc")
        v_lbl.pack(anchor=tk.W, pady=(2, 0))

        return v_lbl

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Файлы Groovy", "*.groovy"), ("Все файлы", "*.*")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.txt_code.delete("1.0", tk.END)
                self.txt_code.insert(tk.END, f.read())
            self.calculate()
            self.status_bar.config(text=f"Загружен файл: {file_path}")

    def load_sample(self):
        sample_code = """def status = 2
def totalScore = 0
def attempts = 0

if (status > 0) {
    switch (status) {
        case 1:
            // Цикл while
            while (attempts < 4) {
                if (attempts % 2 != 0) {
                    totalScore += 5
                } else {
                    totalScore += 2
                }
                attempts++
            }
            break

        case 2:
            // Цикл for-in по диапазону (Range)
            for (step in 1..3) {
                if (totalScore < 15) {
                    totalScore += step * 3
                } else {
                    totalScore -= 2
                }
            }
            break

        case 3:
            // Классический цикл for
            for (int k = 0; k < 3; k++) {
                if (totalScore == 0) {
                    totalScore = 10
                }
            }
            break

        default:
            totalScore = -1
            break
    }
} else {
    totalScore = 0
}"""
        self.txt_code.delete("1.0", tk.END)
        self.txt_code.insert(tk.END, sample_code)
        self.calculate()

    def calculate(self):
        code = self.txt_code.get("1.0", tk.END)
        if not code.strip():
            messagebox.showwarning("Предупреждение", "Поле исходного кода пустое!")
            return

        res = self.parser.analyze(code)

        # Обновление показателей
        self.val_cl.config(text=str(res["CL"]))
        self.val_cli.config(text=str(res["CLI"]))
        self.val_n.config(text=str(res["N"]))
        self.val_cl_rel.config(text=f"{res['cl']:.3f}")

        # Обновление таблицы ветвлений
        for row in self.tree.get_children():
            self.tree.delete(row)

        for line_num, line_txt, b_type, nesting in res["details"]:
            clean_snippet = line_txt.replace('\t', ' ').strip()
            self.tree.insert("", tk.END, values=(line_num, b_type, nesting, clean_snippet))

        self.status_bar.config(text=f"Анализ завершён: найдено {res['CL']} ветвлений, {res['N']} операторов.")


if __name__ == "__main__":
    root = tk.Tk()
    app = LightMetricsApp(root)
    root.mainloop()
