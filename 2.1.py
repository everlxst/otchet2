import sys
import platform
import random
import tkinter as tk
from tkinter import font as tkfont

# --- DPI-awareness на Windows (чёткость на HiDPI) ---
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"[WARN] DPI awareness недоступен: {e}")

# --- Опциональные зависимости с fallback ---
HAS_PIL = False
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    print("[OK] Pillow не найден — используется упрощённый фон")


class RandomNumbersApp:
    # ---------- Палитра ----------
    BG_TOP      = "#0F0B1E"
    BG_BOTTOM   = "#1A1035"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    CARD_EDGE   = "#3B2E66"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    
    ACCENT      = "#A78BFA"
    ACCENT_HOV  = "#C4B5FD"
    ACCENT_PRS  = "#7C5CE6"
    BTN_C1      = "#22D3EE"  # бирюзовый для градиента кнопки
    BTN_C2      = "#A78BFA"  # фиолетовый
    BTN_FG      = "#0F0B1E"

    MEMO_BG     = "#100A1F"
    MEMO_FG     = "#E8E0FF"
    MEMO_SELECT = "#7C5CE6"
    MEMO_SEP    = "#3B2E66"

    W, H = 760, 720
    CARD_MX, CARD_MT, CARD_MB = 40, 30, 50
    CARD_RADIUS = 30

    # Параметры генерации
    RAND_MIN = 0
    RAND_MAX = 100
    COUNT = 1000
    CHUNK_SIZE = 100       # сколько чисел генерируем за один шаг (100 = 5 строк)
    MAX_LINES = 5000       # защита Memo от переполнения
    NUMBERS_PER_LINE = 20

    def __init__(self, root):
        self.root = root
        self.root.title("1000 случайных чисел")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Состояние ---
        self._generating = False
        self._current_chunk = 0

        self._init_fonts()

        # --- Холст ---
        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        # --- Фон ---
        self._bg_photo = None
        self._draw_image_background()
        if not HAS_PIL or self._bg_photo is None:
            self._draw_gradient_background()

        self._draw_card()
        self._draw_header()

        # --- Memo (поле для вывода) ---
        self._create_memo()

        # --- Прогресс-бар и Кнопка ---
        self._draw_progress_bar()
        self._draw_button()

        # --- Статус-бар ---
        self._draw_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _init_fonts(self):
        self.title_font   = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.sub_font     = tkfont.Font(family="Segoe UI", size=10)
        self.memo_font    = tkfont.Font(family="Consolas", size=11)
        self.sep_font     = tkfont.Font(family="Consolas", size=9, weight="bold")
        self.btn_font     = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.status_font  = tkfont.Font(family="Segoe UI", size=9)

    # ============================================================
    #                ФОН
    # ============================================================
    def _make_abstract_background(self, w, h):
        img = Image.new("RGB", (w, h), (5, 5, 15))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            r = int(5 + (18 - 5) * t)
            g = int(5 + (10 - 5) * t)
            b = int(15 + (35 - 15) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        for cx, cy, rad, color in [(100, 100, 300, (120, 40, 200)),
                                   (w - 100, h - 100, 300, (30, 180, 220))]:
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=color + (60,))
            layer = layer.filter(ImageFilter.GaussianBlur(100))
            img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
        return img

    def _draw_image_background(self):
        if not HAS_PIL:
            return
        try:
            img = self._make_abstract_background(self.W, self.H)
            self._bg_photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw",
                                     image=self._bg_photo, tags=("bg_image",))
            self.canvas.tag_lower("bg_image")
        except Exception as e:
            print(f"[WARN] Не удалось создать фон: {e}")
            self._bg_photo = None

    def _draw_gradient_background(self):
        for y in range(self.H):
            t = y / self.H
            self.canvas.create_line(0, y, self.W, y,
                                    fill=self._mix_color(self.BG_TOP, self.BG_BOTTOM, t),
                                    tags="bg")

    # ============================================================
    #                КАРТОЧКА И ЗАГОЛОВОК
    # ============================================================
    def _draw_card(self):
        x0, y0 = self.CARD_MX, self.CARD_MT
        x1, y1 = self.W - self.CARD_MX, self.H - self.CARD_MB
        self.card = (x0, y0, x1, y1)

        self._rounded_rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3,
                           radius=self.CARD_RADIUS + 3,
                           fill=self._mix_color(self.ACCENT, "#000000", 0.55),
                           outline="", tags=("card_bg",))
        self._rounded_rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1,
                           radius=self.CARD_RADIUS + 1,
                           fill="#4B3B7A", outline="", tags=("card_bg",))

        self._rounded_rect(x0, y0, x1, y1,
                           radius=self.CARD_RADIUS,
                           fill=self._mix_color(self.CARD_BOTTOM, self.CARD_TOP, 0.4),
                           outline="#5B4A8A", width=1,
                           tags=("card_inner",))
        self.canvas.tag_raise("card_inner")

    def _draw_header(self):
        x0, y0, x1, _ = self.card
        cx = (x0 + x1) / 2
        self.canvas.create_rectangle(cx - 24, y0 + 22, cx + 24, y0 + 25,
                                     fill=self.ACCENT, outline="", tags=("card",))
        self.canvas.create_text(cx, y0 + 50,
                                text="🎲  1000 СЛУЧАЙНЫХ ЧИСЕЛ",
                                font=self.title_font, fill=self.TEXT_LIGHT,
                                tags=("card",))
        sub_text = f"по нажатию на кнопку в поле Memo появятся 1000 чисел от {self.RAND_MIN} до {self.RAND_MAX}"
        self.canvas.create_text(cx, y0 + 74,
                                text=sub_text, font=self.sub_font,
                                fill=self.TEXT_DIM, tags=("card",))

    # ============================================================
    #                MEMO (поле вывода)
    # ============================================================
    def _create_memo(self):
        x0, y0, x1, y1 = self.card

        memo_pad_x = 50
        memo_top = y0 + 105
        memo_bottom = y1 - 150

        self._rounded_rect(
            x0 + memo_pad_x - 6, memo_top - 6,
            x1 - memo_pad_x + 6, memo_bottom + 6,
            radius=14,
            fill=self._mix_color(self.ACCENT, "#000000", 0.6),
            outline="#5B4A8A", width=1,
            tags=("card",)
        )

        inner = tk.Frame(self.root, bg=self.MEMO_BG, bd=0, highlightthickness=0)

        self.memo = tk.Text(
            inner,
            font=self.memo_font,
            bg=self.MEMO_BG,
            fg=self.MEMO_FG,
            insertbackground=self.MEMO_FG,
            selectbackground=self.MEMO_SELECT,
            bd=0,
            highlightthickness=0,
            wrap="none",  # Отключаем перенос, чтобы строки не ломались
            padx=12, pady=10,
            state="normal",
        )
        self.memo.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(inner, command=self.memo.yview,
                                 bd=0, highlightthickness=0)
        scrollbar.pack(side="right", fill="y")
        self.memo.configure(yscrollcommand=scrollbar.set)

        # Настраиваем теги для разделителей и подсветки
        self.memo.tag_configure("separator", foreground=self.MEMO_SEP,
                                font=self.sep_font, justify="center",
                                spacing1=8, spacing3=8)
        self.memo.tag_configure("num", foreground=self.MEMO_FG,
                                font=self.memo_font)

        self.canvas.create_window(
            (x0 + memo_pad_x + (x1 - memo_pad_x)) / 2,
            (memo_top + memo_bottom) / 2,
            window=inner,
            width=(x1 - x0) - 2 * memo_pad_x,
            height=(memo_bottom - memo_top),
            tags=("card",)
        )

    # ============================================================
    #                ПРОГРЕСС-БАР И КНОПКА
    # ============================================================
    def _draw_progress_bar(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        self.pb_y = y1 - 100
        self.pb_w = 280
        self.pb_h = 6
        
        self.pb_x0 = cx - self.pb_w / 2
        self.pb_x1 = cx + self.pb_w / 2

        # Фон полоски
        self._rounded_rect(
            self.pb_x0, self.pb_y - self.pb_h/2,
            self.pb_x1, self.pb_y + self.pb_h/2,
            radius=self.pb_h/2,
            fill=self._mix_color(self.CARD_BOTTOM, "#000000", 0.6),
            outline="", tags=("card", "pb_bg")
        )
        
        # Заполнение (изначально скрыто)
        self.pb_fill_id = self._rounded_rect(
            self.pb_x0, self.pb_y - self.pb_h/2,
            self.pb_x0 + 1, self.pb_y + self.pb_h/2,
            radius=self.pb_h/2,
            fill=self.ACCENT, outline="", tags=("card",)
        )

    def _draw_button(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        cy = y1 - 60

        self.btn_w, self.btn_h = 280, 52
        self.btn_x0 = cx - self.btn_w / 2
        self.btn_y0 = cy - self.btn_h / 2
        self.btn_x1 = cx + self.btn_w / 2
        self.btn_y1 = cy + self.btn_h / 2

        # Свечение
        for i, a in [(8, 0.10), (4, 0.15)]:
            self._rounded_rect(
                self.btn_x0 - i, self.btn_y0 - i,
                self.btn_x1 + i, self.btn_y1 + i,
                radius=self.btn_h / 2 + i,
                fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, a),
                outline="", tags=("card", "btn_glow"))

        # Сама кнопка (градиент)
        self.btn_body = self._fill_polygon(
            self.btn_x0, self.btn_y0, self.btn_x1, self.btn_y1,
            self.btn_h / 2,
            fill=self.BTN_C1, outline="",
            tags=("card", "gen_btn"))
        
        # Внутренняя заливка (второй слой градиента)
        self.btn_inner = self._fill_polygon(
            self.btn_x0 + 2, self.btn_y0 + 2, self.btn_x1 - 2, self.btn_y1 - 2,
            self.btn_h / 2 - 1,
            fill=self.BTN_C2, outline="",
            tags=("card", "gen_btn"))

        self.btn_text_id = self.canvas.create_text(
            cx, cy, text="СГЕНЕРИРОВАТЬ",
            font=self.btn_font, fill=self.BTN_FG,
            tags=("card", "gen_btn"))

        self.canvas.tag_bind("gen_btn", "<Enter>", self._btn_enter)
        self.canvas.tag_bind("gen_btn", "<Leave>", self._btn_leave)
        self.canvas.tag_bind("gen_btn", "<ButtonPress-1>", self._btn_press)
        self.canvas.tag_bind("gen_btn", "<ButtonRelease-1>", self._btn_release)

    def _btn_enter(self, _):
        if self._generating: return
        self.canvas.config(cursor="hand2")
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_HOV)

    def _btn_leave(self, _):
        self.canvas.config(cursor="")
        self.canvas.itemconfigure(self.btn_body, fill=self.BTN_C1)

    def _btn_press(self, _):
        if self._generating: return
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_PRS)

    def _btn_release(self, event):
        if self._generating: return
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_HOV)
        self._generate_async()

    # ============================================================
    #                СТАТУС-БАР
    # ============================================================
    def _draw_status_bar(self):
        self.canvas.create_rectangle(0, self.H - 34, self.W, self.H,
                                     fill=self._mix_color(self.BG_TOP, "#000000", 0.2),
                                     outline="", tags=("status_bg",))
        self.status_id = self.canvas.create_text(
            22, self.H - 17,
            text="Готово  ·  нажмите кнопку",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM,
            tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21,
                                self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                ГЕНЕРАЦИЯ
    # ============================================================
    def _generate_async(self):
        if self._generating: return

        self._generating = True
        self._current_chunk = 0
        self.canvas.itemconfigure(self.btn_text_id, text="ГЕНЕРАЦИЯ...")
        self.canvas.itemconfigure(self.btn_body, fill=self._mix_color(self.BTN_C1, "#000000", 0.5))
        self.canvas.itemconfigure(self.btn_inner, fill=self._mix_color(self.BTN_C2, "#000000", 0.5))
        self.canvas.itemconfigure(self.status_id, text="Генерация 0 / 1000...")
        
        # Сброс прогресс-бара
        self._update_progress(0)

        try:
            self.memo.configure(state="normal")
            self.memo.delete("1.0", "end")
        except Exception as e:
            print(f"[WARN] Ошибка очистки Memo: {e}")

        self._next_chunk()

    def _next_chunk(self):
        try:
            if not self._generating: return

            start = self._current_chunk * self.CHUNK_SIZE
            if start >= self.COUNT:
                self._finish_generation()
                return

            end = min(start + self.CHUNK_SIZE, self.COUNT)
            count = end - start

            # --- Форматируем числа ---
            nums = [f"{random.randint(self.RAND_MIN, self.RAND_MAX):3d}" for _ in range(count)]
            
            # Разбиваем на строки по 20 штук
            lines = []
            for i in range(0, len(nums), self.NUMBERS_PER_LINE):
                line = "  ".join(nums[i:i + self.NUMBERS_PER_LINE])
                lines.append(line)
            
            text = "\n".join(lines)

            # Добавляем разделитель, если это начало нового блока
            if start % 100 == 0:
                sep_text = f"\n{'—' * 20} {start+1:04d} … {end:04d} {'—' * 20}\n"
                self.memo.insert("end", sep_text, "separator")

            self.memo.insert("end", text + "\n", "num")
            self.memo.see("end")

            # Обновляем прогресс
            self._current_chunk += 1
            progress = end / self.COUNT
            self._update_progress(progress)
            
            self.canvas.itemconfigure(self.status_id, text=f"Генерация {end} / {self.COUNT}...")

            # Защита от переполнения
            try:
                total_lines = int(self.memo.index("end-1c").split(".")[0])
                if total_lines > self.MAX_LINES:
                    self.memo.delete("1.0", f"{total_lines - self.MAX_LINES + 1}.0")
            except Exception:
                pass

            self.root.after(20, self._next_chunk) # 20мс — чтобы UI не завис

        except Exception as e:
            print(f"[ERR] Генерация: {e}")
            self._finish_generation(error=True)

    def _update_progress(self, value):
        val = max(0.0, min(1.0, value))
        if val == 0:
            self.canvas.coords(self.pb_fill_id, *self._pill_points(
                self.pb_x0, self.pb_y - self.pb_h/2,
                self.pb_x0 + 1, self.pb_y + self.pb_h/2,
                self.pb_h/2
            ))
        else:
            fill_x1 = self.pb_x0 + self.pb_w * val
            self.canvas.coords(self.pb_fill_id, *self._pill_points(
                self.pb_x0, self.pb_y - self.pb_h/2,
                fill_x1, self.pb_y + self.pb_h/2,
                self.pb_h/2
            ))

    def _finish_generation(self, error=False):
        self._generating = False
        self.canvas.itemconfigure(self.btn_body, fill=self.BTN_C1)
        self.canvas.itemconfigure(self.btn_inner, fill=self.BTN_C2)
        self.canvas.itemconfigure(self.btn_text_id, text="СГЕНЕРИРОВАТЬ")
        
        if error:
            self.canvas.itemconfigure(self.status_id, text="Ошибка генерации — попробуйте ещё раз")
            self._update_progress(0)
        else:
            self._update_progress(1.0)
            self.canvas.itemconfigure(self.status_id, text=f"Готово · {self.COUNT} чисел · диапазон {self.RAND_MIN}…{self.RAND_MAX}")

    def _on_close(self):
        self._generating = False
        try:
            self.root.destroy()
        except Exception:
            pass

    # ============================================================
    #                УТИЛИТЫ
    # ============================================================
    def _pill_points(self, x0, y0, x1, y1, r):
        if x1 - x0 < 2 * r: x1 = x0 + 2 * r
        if y1 - y0 < 2 * r: y1 = y0 + 2 * r
        rr = min(r, (y1 - y0) / 2, (x1 - x0) / 2)
        return [x0 + rr, y0, x1 - rr, y0, x1, y0, x1, y0 + rr,
                x1, y1 - rr, x1, y1, x1 - rr, y1, x0 + rr, y1,
                x0, y1, x0, y1 - rr, x0, y0 + rr, x0, y0]

    def _rounded_rect(self, x0, y0, x1, y1, radius, **kwargs):
        return self.canvas.create_polygon(
            self._pill_points(x0, y0, x1, y1, radius),
            smooth=True, **kwargs)

    def _fill_polygon(self, x0, y0, x1, y1, r, **kwargs):
        return self._rounded_rect(x0, y0, x1, y1, r, **kwargs)

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    @classmethod
    def _mix_color(cls, c1, c2, t):
        r1, g1, b1 = cls._hex_to_rgb(c1)
        r2, g2, b2 = cls._hex_to_rgb(c2)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _center_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = RandomNumbersApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")