import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from anaphora.resolver import resolve_pronouns


PINK_BG = "#ffd1e6"
PINK_DARK = "#ff6fa1"
PINK_MED = "#ff9fc0"
PINK_LIGHT = "#ffe4ef"
TEXT_FG = "#4a4a4a"
FONT_MAIN = ("Segoe UI", 16)
FONT_BTN = ("Segoe UI Semibold", 16)
FONT_HDR = ("Segoe UI", 20, "bold")


class AnaphoraGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Анафора: аннотирование текста")
        self.configure(bg=PINK_BG)
        self.geometry("820x560")
        self.minsize(620, 460)
        self._build_style()
        self._build_layout()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Pink.TButton", font=FONT_BTN, foreground="white", background=PINK_DARK)
        style.map(
            "Pink.TButton",
            background=[("active", PINK_MED)],
        )

    def _build_layout(self):
        header = tk.Label(self, text="Разрешение анафоры", bg=PINK_BG, fg=TEXT_FG, font=FONT_HDR)
        header.pack(pady=(18, 6))

        desc = tk.Label(
            self,
            text="Введите текст сверху и нажмите 'Аннотировать'. Результат появится снизу.",
            bg=PINK_BG,
            fg=TEXT_FG,
            font=("Segoe UI", 12),
        )
        desc.pack(pady=(0, 12))

        content = tk.Frame(self, bg=PINK_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=18, pady=12)

        # Top panel (input)
        top = tk.Frame(content, bg=PINK_BG)
        top.pack(side=tk.TOP, fill=tk.X, expand=False, pady=(0, 8))
        in_label = tk.Label(top, text="Входной текст", bg=PINK_BG, fg=TEXT_FG, font=("Segoe UI", 14, "bold"))
        in_label.pack(anchor="w", pady=(0, 6))
        in_container = tk.Frame(top, bg=PINK_BG)
        in_container.pack(fill=tk.BOTH, expand=True)
        self.input_text = tk.Text(
            in_container,
            wrap=tk.WORD,
            font=FONT_MAIN,
            bg=PINK_LIGHT,
            fg=TEXT_FG,
            insertbackground=TEXT_FG,
            relief=tk.FLAT,
            bd=8,
            height=5,
        )
        in_scroll = tk.Scrollbar(in_container, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=in_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        in_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Actions
        actions = tk.Frame(content, bg=PINK_BG)
        actions.pack(side=tk.TOP, fill=tk.X, expand=False, pady=(6, 6))
        annotate_btn = ttk.Button(actions, text="Аннотировать", style="Pink.TButton", command=self.on_annotate)
        annotate_btn.pack(side=tk.LEFT)
        clear_btn = ttk.Button(actions, text="Очистить", style="Pink.TButton", command=self.on_clear)
        clear_btn.pack(side=tk.LEFT, padx=(12, 0))
        copy_btn = ttk.Button(actions, text="Копировать результат", style="Pink.TButton", command=self.on_copy)
        copy_btn.pack(side=tk.LEFT, padx=(12, 0))

        # Bottom panel (output)
        bottom = tk.Frame(content, bg=PINK_BG)
        bottom.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(8, 0))
        out_label = tk.Label(bottom, text="Аннотированный текст", bg=PINK_BG, fg=TEXT_FG, font=("Segoe UI", 14, "bold"))
        out_label.pack(anchor="w", pady=(0, 6))
        out_container = tk.Frame(bottom, bg=PINK_BG)
        out_container.pack(fill=tk.BOTH, expand=True)
        self.output_text = tk.Text(
            out_container,
            wrap=tk.WORD,
            font=FONT_MAIN,
            bg="#fff7fb",
            fg=TEXT_FG,
            insertbackground=TEXT_FG,
            relief=tk.FLAT,
            bd=8,
            state=tk.NORMAL,
        )
        out_scroll = tk.Scrollbar(out_container, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=out_scroll.set)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        out_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def on_annotate(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Пустой ввод", "Введите текст для аннотирования.")
            return
        try:
            result = resolve_pronouns(text)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", result)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Произошла ошибка при аннотировании:\n{e}")

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)

    def on_copy(self):
        result = self.output_text.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Пусто", "Нет результата для копирования.")
            return
        self.clipboard_clear()
        self.clipboard_append(result)
        messagebox.showinfo("Скопировано", "Результат скопирован в буфер обмена.")


def main():
    app = AnaphoraGUI()
    app.mainloop()


if __name__ == "__main__":
    main()


