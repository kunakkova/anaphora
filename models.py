import tkinter as tk
from tkinter import messagebox, ttk
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
from anaphora.resolver import resolve_pronouns
import threading


PINK_BG = "#ffd1e6"
PINK_DARK = "#ff6fa1"
PINK_MED = "#ff9fc0"
PINK_LIGHT = "#ffe4ef"
TEXT_FG = "#4a4a4a"
FONT_MAIN = ("Segoe UI", 14)
FONT_BTN = ("Segoe UI Semibold", 13)
FONT_HDR = ("Segoe UI", 20, "bold")


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = r"D:\Мои загрузки\anaphora-main (3)\anaphora-main_new_version\anaphora_resolution_model"

try:
    neural_model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
    neural_tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH, legacy=False)
    neural_model.to(DEVICE)
    neural_model.eval()
    MODEL_LOADED = True
except Exception as e:
    print(f"Не удалось загрузить нейросетевую модель: {e}")
    neural_model = None
    neural_tokenizer = None
    MODEL_LOADED = False


def resolve_with_neural(text: str, max_length=128) -> str:
    if not MODEL_LOADED:
        return "[Нейросетевая модель не загружена]"
    try:
        inputs = neural_tokenizer(text.strip(), return_tensors="pt",
                                  truncation=True, max_length=max_length).to(DEVICE)
        with torch.no_grad():
            outputs = neural_model.generate(
                **inputs,
                max_length=max_length,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3,
                repetition_penalty=1.2
            )
        resolved = neural_tokenizer.decode(outputs[0], skip_special_tokens=True)
        return resolved
    except Exception as e:
        return f"[Ошибка нейросети: {e}]"


def resolve_with_logical(text: str) -> str:
    try:
        return resolve_pronouns(text)
    except Exception as e:
        return f"[Ошибка логической модели: {e}]"


class AnaphoraDoubleGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Разрешение анафоры: логический и нейросетевой подходы")
        self.configure(bg=PINK_BG)
        self.geometry("1100x700")
        self.minsize(900, 600)
        self._build_style()
        self._build_layout()
        self._update_model_status()

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Pink.TButton", font=FONT_BTN, foreground="white",
                        background=PINK_DARK)
        style.map("Pink.TButton",
                  background=[("active", PINK_MED)])

    def _build_layout(self):
        header = tk.Label(self, text="Разрешение анафоры",
                          bg=PINK_BG, fg=TEXT_FG, font=FONT_HDR)
        header.pack(pady=(18, 6))

        desc = tk.Label(self,
                        text="Введите текст → нажмите «Аннотировать» → получите результаты двух моделей.",
                        bg=PINK_BG, fg=TEXT_FG, font=("Segoe UI", 12))
        desc.pack(pady=(0, 12))

        main_frame = tk.Frame(self, bg=PINK_BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=12)

        input_frame = tk.Frame(main_frame, bg=PINK_BG)
        input_frame.pack(side=tk.TOP, fill=tk.X, expand=False, pady=(0, 15))

        tk.Label(input_frame, text="Входной текст", bg=PINK_BG,
                 fg=TEXT_FG, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 5))
        in_container = tk.Frame(input_frame, bg=PINK_BG)
        in_container.pack(fill=tk.BOTH, expand=True)
        self.input_text = tk.Text(in_container, wrap=tk.WORD, font=FONT_MAIN,
                                  bg=PINK_LIGHT, fg=TEXT_FG, insertbackground=TEXT_FG,
                                  relief=tk.FLAT, bd=8, height=6)
        in_scroll = tk.Scrollbar(in_container, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=in_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        in_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(main_frame, bg=PINK_BG)
        btn_frame.pack(side=tk.TOP, fill=tk.X, expand=False, pady=8)
        self.annotate_btn = ttk.Button(btn_frame, text="Аннотировать",
                                       style="Pink.TButton", command=self.on_annotate)
        self.annotate_btn.pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Очистить", style="Pink.TButton",
                   command=self.on_clear).pack(side=tk.LEFT, padx=(12, 0))
        self.copy_logical_btn = ttk.Button(btn_frame, text="Копировать (логическая)",
                                           style="Pink.TButton", command=self.on_copy_logical)
        self.copy_logical_btn.pack(side=tk.LEFT, padx=(12, 0))
        self.copy_neural_btn = ttk.Button(btn_frame, text="Копировать (нейронная)",
                                          style="Pink.TButton", command=self.on_copy_neural)
        self.copy_neural_btn.pack(side=tk.LEFT, padx=(12, 0))

        self.status_label = tk.Label(main_frame, text="Готово", bg=PINK_BG,
                                     fg=TEXT_FG, font=("Segoe UI", 10))
        self.status_label.pack(side=tk.TOP, fill=tk.X, pady=(5, 0))

        output_panel = tk.Frame(main_frame, bg=PINK_BG)
        output_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(12, 0))

        output_panel.grid_columnconfigure(0, weight=1)
        output_panel.grid_columnconfigure(1, weight=1)
        output_panel.grid_rowconfigure(0, weight=1)

        left_frame = tk.Frame(output_panel, bg=PINK_BG)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left_frame, text="Результат логической модели",
                 bg=PINK_BG, fg=TEXT_FG, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 5))
        left_container = tk.Frame(left_frame, bg=PINK_BG)
        left_container.pack(fill=tk.BOTH, expand=True)
        self.output_logical = tk.Text(left_container, wrap=tk.WORD, font=FONT_MAIN,
                                      bg="#fff7fb", fg=TEXT_FG, relief=tk.FLAT, bd=8)
        left_scroll = tk.Scrollbar(left_container, command=self.output_logical.yview)
        self.output_logical.configure(yscrollcommand=left_scroll.set)
        self.output_logical.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        right_frame = tk.Frame(output_panel, bg=PINK_BG)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(right_frame, text="Результат нейросетевой модели",
                 bg=PINK_BG, fg=TEXT_FG, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 5))
        right_container = tk.Frame(right_frame, bg=PINK_BG)
        right_container.pack(fill=tk.BOTH, expand=True)
        self.output_neural = tk.Text(right_container, wrap=tk.WORD, font=FONT_MAIN,
                                     bg="#fff7fb", fg=TEXT_FG, relief=tk.FLAT, bd=8)
        right_scroll = tk.Scrollbar(right_container, command=self.output_neural.yview)
        self.output_neural.configure(yscrollcommand=right_scroll.set)
        self.output_neural.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _update_model_status(self):
        if MODEL_LOADED:
            self.status_label.config(text=f"Нейронная модель загружена")
        else:
            self.status_label.config(text=f"Нейронная модель НЕ загружена")

    def on_annotate(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Пустой ввод", "Введите текст для аннотирования.")
            return

        self.annotate_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Обработка (может занять несколько секунд)")

        thread = threading.Thread(target=self._process_in_thread, args=(text,))
        thread.daemon = True
        thread.start()

    def _process_in_thread(self, text):
        try:
            logical_result = resolve_with_logical(text)
            neural_result = resolve_with_neural(text)
            self.after(0, self._update_outputs, logical_result, neural_result)
        except Exception as e:
            self.after(0, self._show_error, f"Ошибка при обработке: {e}")
        finally:
            self.after(0, self._enable_button_and_reset_status)

    def _update_outputs(self, logical_text, neural_text):
        self.output_logical.delete("1.0", tk.END)
        self.output_logical.insert("1.0", logical_text)
        self.output_neural.delete("1.0", tk.END)
        self.output_neural.insert("1.0", neural_text)

    def _show_error(self, msg):
        messagebox.showerror("Ошибка", msg)

    def _enable_button_and_reset_status(self):
        self.annotate_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Готов")

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self.output_logical.delete("1.0", tk.END)
        self.output_neural.delete("1.0", tk.END)
        self.status_label.config(text="Очищено")

    def on_copy_logical(self):
        result = self.output_logical.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Пусто", "Нет результата логической модели для копирования.")
            return
        self.clipboard_clear()
        self.clipboard_append(result)
        messagebox.showinfo("Скопировано", "Результат логической модели скопирован в буфер обмена.")

    def on_copy_neural(self):
        result = self.output_neural.get("1.0", tk.END).strip()
        if not result:
            messagebox.showinfo("Пусто", "Нет результата нейросетевой модели для копирования.")
            return
        self.clipboard_clear()
        self.clipboard_append(result)
        messagebox.showinfo("Скопировано", "Результат нейросетевой модели скопирован в буфер обмена.")


def main():
    app = AnaphoraDoubleGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
