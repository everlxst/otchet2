import sys
import platform
import random
import tkinter as tk
from tkinter import font as tkfont

# --- DPI-awareness на Windows ---
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"[WARN] DPI awareness недоступен: {e}")

# --- Опциональные зависимости ---
HAS_PIL = False
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    print("[OK] Pillow не найден — используется упрощённый фон")


class RandomCountApp:
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
    BTN_FG      = "#0F0B1E"
    
    # Цвета для чисел
    NUM_DEFAULT = "#E8E0FF"
    NUM_YELLOW  = "#FBBF24"
    NUM_RED     = "#EF4444"
    
    MEMO_BG     = "#100A1F"
    MEMO_SELECT = "#7C5CE6"
    MEMO_SEP    = "#3B2E66"

    W, H = 760, 760
    CARD_MX, CARD_MT, CARD_MB = 40, 30, 50
    CARD_RADIUS = 30

    # Параметры
    RAND_MIN = 0
    RAND_MAX = 100
    COUNT_MIN = 1
    COUNT_MAX = 1000
    COUNT_START = 100
    
    CHUNK_SIZE = 100
    MAX_LINES = 5000
    NUMBERS_PER_LINE = 20

    ANIM_INTERVAL_MS = 16
    ANIM_SMOOTHING   = 0.25
    ANIM_EPS         = 0.5

    def __init__(self, root):
        self.root = root
        self.root.title("Количество случайных чисел · TrackBar")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Состояние ---
        self.count_cur = float(self.COUNT_START)
        self.count_tgt = float(self.COUNT_START)
        
        self._drag = None
        self._generating = False
        self._current_chunk = 0
        self._anim_after_id = None

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
        self._create_memo()
        self._draw_slider()
        self._draw_buttons()
        self._draw_status_bar()

        # Клавиатурное управление
        self.root.bind("<Left>",  lambda e: self._change_count(-10))
        self.root.bind("<Right>", lambda e: self._change_count(+10))
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._anim_loop()

    def _init_fonts(self):
        self.title_font   = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.sub_font     = tkfont.Font(family="Segoe UI", size=10)
        self.lbl_font     = tkfont.Font(family="Segoe UI", size=10)
        self.badge_font   = tkfont.Font(family="Consolas", size=12, weight="bold")
        self.val_font     = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.memo_font    = tkfont.Font(family="Consolas", size=11)
        self.sep_font     = tkfont.Font(family="Consolas", size=9)
        self.btn_font     = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.status_font  = tkfont.Font(family="Segoe UI", size=9)

    # ============================================================
    #                ФОН И КАРТОЧКА
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
        if not HAS_PIL: return
        try:
            img = self._make_abstract_background(self.W, self.H)
            self._bg_photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo, tags=("bg_image",))
            self.canvas.tag_lower("bg_image")
        except Exception as e:
            print(f"[WARN] Ошибка фона: {e}")

    def _draw_gradient_background(self):
        for y in range(self.H):
            t = y / self.H
            self.canvas.create_line(0, y, self.W, y,
                                    fill=self._mix_color(self.BG_TOP, self.BG_BOTTOM, t),
                                    tags="bg")

    def _draw_card(self):
        x0, y0 = self.CARD_MX, self.CARD_MT
        x1, y1 = self.W - self.CARD_MX, self.H - self.CARD_MB
        self.card = (x0, y0, x1, y1)
        self._rounded_rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3, radius=self.CARD_RADIUS + 3,
                           fill=self._mix_color(self.ACCENT, "#000000", 0.55), outline="", tags=("card_bg",))
        self._rounded_rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1, radius=self.CARD_RADIUS + 1,
                           fill="#4B3B7A", outline="", tags=("card_bg",))
        self._rounded_rect(x0, y0, x1, y1, radius=self.CARD_RADIUS,
                           fill=self._mix_color(self.CARD_BOTTOM, self.CARD_TOP, 0.4),
                           outline="#5B4A8A", width=1, tags=("card_inner",))
        self.canvas.tag_raise("card_inner")

    def _draw_header(self):
        x0, y0, x1, _ = self.card
        cx = (x0 + x1) / 2
        self.canvas.create_rectangle(cx - 24, y0 + 22, cx + 24, y0 + 25,
                                     fill=self.ACCENT, outline="", tags=("card",))
        self.canvas.create_text(cx, y0 + 50, text="🎲  СЛУЧАЙНЫЕ ЧИСЛА",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))
        
        # Бейдж с диапазоном
        badge_w, badge_h = 200, 28
        bx0 = cx - badge_w / 2
        by0 = y0 + 78
        self._rounded_rect(bx0, by0, bx0 + badge_w, by0 + badge_h, radius=badge_h/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.15),
                           outline=self.ACCENT, width=1, tags=("card",))
        
        self.canvas.create_text(cx, by0 + badge_h/2,
                                text=f"Диапазон: {self.RAND_MIN} … {self.RAND_MAX}",
                                font=self.badge_font, fill=self.ACCENT, tags=("card",))

    # ============================================================
    #                MEMO
    # ============================================================
    def _create_memo(self):
        x0, y0, x1, y1 = self.card
        memo_pad_x = 50
        memo_top = y0 + 120
        memo_bottom = y1 - 190  # Немного больше отступа, чтобы дать воздух

        self._rounded_rect(
            x0 + memo_pad_x - 6, memo_top - 6,
            x1 - memo_pad_x + 6, memo_bottom + 6,
            radius=14, fill=self._mix_color(self.ACCENT, "#000000", 0.6),
            outline="#5B4A8A", width=1, tags=("card",)
        )

        inner = tk.Frame(self.root, bg=self.MEMO_BG, bd=0, highlightthickness=0)
        self.memo = tk.Text(
            inner, font=self.memo_font, bg=self.MEMO_BG, fg=self.NUM_DEFAULT,
            insertbackground=self.NUM_DEFAULT, selectbackground=self.MEMO_SELECT,
            bd=0, highlightthickness=0, wrap="none", padx=12, pady=8, state="normal"
        )
        self.memo.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(inner, command=self.memo.yview, bd=0, highlightthickness=0)
        scrollbar.pack(side="right", fill="y")
        self.memo.configure(yscrollcommand=scrollbar.set)

        self.memo.tag_configure("sep_line", foreground=self.MEMO_SEP, font=self.sep_font, justify="right", spacing1=10, spacing3=10)
        self.memo.tag_configure("num", foreground=self.NUM_DEFAULT, font=self.memo_font)
        self.memo.tag_configure("num_yellow", foreground=self.NUM_YELLOW, font=self.memo_font)
        self.memo.tag_configure("num_red", foreground=self.NUM_RED, font=self.memo_font)

        self.canvas.create_window(
            (x0 + memo_pad_x + (x1 - memo_pad_x)) / 2,
            (memo_top + memo_bottom) / 2,
            window=inner, width=(x1 - x0) - 2 * memo_pad_x,
            height=(memo_bottom - memo_top), tags=("card",)
        )

    # ============================================================
    #                ПОЛЗУНОК
    # ============================================================
    def _draw_slider(self):
        x0, y0, x1, _ = self.card
        pad = 60
        self.len_x0 = x0 + pad
        self.len_x1 = x1 - pad
        self.len_y = y0 + 550  # Опущен ещё ниже для «воздуха»
        self.len_h = 10
        self.len_r = self.len_h / 2
        self.len_knob_r = 14

        self.canvas.create_text(self.len_x0, self.len_y - 32, anchor="w",
                                text="КОЛИЧЕСТВО ЧИСЕЛ", font=self.lbl_font, fill=self.TEXT_DIM, tags=("card",))
        self.count_val_id = self.canvas.create_text(self.len_x1, self.len_y - 32, anchor="e",
                                text=str(int(self.count_cur)), font=self.val_font, fill=self.ACCENT, tags=("card",))

        self._fill_polygon(self.len_x0, self.len_y - self.len_r, self.len_x1, self.len_y + self.len_r, self.len_r,
                           fill=self._mix_color(self.CARD_BOTTOM, "#000000", 0.6), outline="#5B4A8A", width=1, tags=("card", "len_bg"))
        self.len_fill_id = self._fill_polygon(self.len_x0, self.len_y - self.len_r, self.len_x0 + 10, self.len_y + self.len_r, self.len_r,
                           fill=self.ACCENT, outline="", tags=("card", "len_fill"))
        self.len_knob = self.canvas.create_oval(0, 0, 0, 0, fill=self.TEXT_LIGHT, outline=self.ACCENT, width=3, tags=("card", "len_knob"))

        for tag in ("len_bg", "len_fill", "len_knob"):
            self.canvas.tag_bind(tag, "<ButtonPress-1>",   self._len_press)
            self.canvas.tag_bind(tag, "<B1-Motion>",       self._len_drag)
            self.canvas.tag_bind(tag, "<ButtonRelease-1>", self._len_release)

    def _len_val_from_x(self, x):
        t = (x - self.len_x0) / (self.len_x1 - self.len_x0)
        t = max(0.0, min(1.0, t))
        return self.COUNT_MIN + (self.COUNT_MAX - self.COUNT_MIN) * t

    def _len_press(self, event):
        self._drag = "LEN"
        self.count_tgt = float(self._len_val_from_x(event.x))

    def _len_drag(self, event):
        if self._drag == "LEN":
            self.count_tgt = float(self._len_val_from_x(event.x))

    def _len_release(self, event):
        self._drag = None

    # ============================================================
    #                КНОПКИ
    # ============================================================
    def _draw_buttons(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        cy = y1 - 75

        bw, bh = 180, 48
        gap = 20

        bx0 = cx - gap/2 - bw
        bx1 = bx0 + bw
        by0 = cy - bh / 2
        by1 = cy + bh / 2

        for i, a in [(8, 0.10), (4, 0.15)]:
            self._rounded_rect(bx0 - i, by0 - i, bx1 + i, by1 + i,
                               radius=bh / 2 + i,
                               fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, a),
                               outline="", tags=("card", "btn_glow"))

        self.btn_body = self._rounded_rect(bx0, by0, bx1, by1,
                                           radius=bh / 2, fill=self.ACCENT, outline="", tags=("card", "gen_btn"))
        self.btn_text_id = self.canvas.create_text((bx0+bx1)/2, cy, text="СГЕНЕРИРОВАТЬ",
                                                   font=self.btn_font, fill=self.BTN_FG, tags=("card", "gen_btn"))

        bx0 = cx + gap/2
        bx1 = bx0 + bw
        self._rounded_rect(bx0, by0, bx1, by1, radius=bh/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.2),
                           outline=self.ACCENT, width=1, tags=("card", "clr_btn"))
        self.canvas.create_text((bx0+bx1)/2, cy, text="ОЧИСТИТЬ",
                                font=self.btn_font, fill=self.ACCENT, tags=("card", "clr_btn"))

        ex_cy = y1 - 25
        ex_w, ex_h = 140, 30
        ex_x0 = cx - ex_w/2
        ex_x1 = cx + ex_w/2
        ex_y0 = ex_cy - ex_h/2
        ex_y1 = ex_cy + ex_h/2
        self._rounded_rect(ex_x0, ex_y0, ex_x1, ex_y1, radius=ex_h/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.1),
                           outline=self.ACCENT, width=1, tags=("card", "exp_btn"))
        self.canvas.create_text(cx, ex_cy, text="💾 ЭКСПОРТ В TXT",
                                font=self.status_font, fill=self.ACCENT, tags=("card", "exp_btn"))

        self.canvas.tag_bind("gen_btn", "<Enter>", self._btn_enter)
        self.canvas.tag_bind("gen_btn", "<Leave>", self._btn_leave)
        self.canvas.tag_bind("gen_btn", "<ButtonPress-1>", self._btn_press)
        self.canvas.tag_bind("gen_btn", "<ButtonRelease-1>", self._btn_release)

        self.canvas.tag_bind("clr_btn", "<ButtonRelease-1>", lambda e: self._clear_memo())
        self.canvas.tag_bind("clr_btn", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("clr_btn", "<Leave>", lambda e: self.canvas.config(cursor=""))

        self.canvas.tag_bind("exp_btn", "<ButtonRelease-1>", lambda e: self._export_to_file())
        self.canvas.tag_bind("exp_btn", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("exp_btn", "<Leave>", lambda e: self.canvas.config(cursor=""))

    def _btn_enter(self, _):
        if self._generating: return
        self.canvas.config(cursor="hand2")
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_HOV)

    def _btn_leave(self, _):
        self.canvas.config(cursor="")
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT)

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
            22, self.H - 17, text="Готово  ·  ←/→ — количество",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM, tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                ЛОГИКА ГЕНЕРАЦИИ
    # ============================================================
    def _clear_memo(self):
        if self._generating: return
        try:
            self.memo.configure(state="normal")
            self.memo.delete("1.0", "end")
            self.canvas.itemconfigure(self.status_id, text="Очищено")
        except Exception as e:
            print(f"[WARN] Ошибка очистки: {e}")

    def _export_to_file(self):
        if self._generating: return
        try:
            content = self.memo.get("1.0", "end-1c")
            if not content.strip():
                self.canvas.itemconfigure(self.status_id, text="Нет данных для экспорта")
                return
            
            filename = "numbers.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            self.canvas.itemconfigure(self.status_id, text=f"Сохранено в {filename}")
        except Exception as e:
            print(f"[ERR] Экспорт: {e}")
            self.canvas.itemconfigure(self.status_id, text="Ошибка сохранения файла")

    def _generate_async(self):
        if self._generating: return
        self._generating = True
        self._current_chunk = 0
        
        target_count = int(round(self.count_cur))
        self.canvas.itemconfigure(self.btn_text_id, text="ГЕНЕРАЦИЯ...")
        self.canvas.itemconfigure(self.btn_body, fill=self._mix_color(self.ACCENT, "#000000", 0.3))
        self.canvas.itemconfigure(self.status_id, text=f"Выведено: 0 из {target_count}")

        try:
            self.memo.configure(state="normal")
            self.memo.delete("1.0", "end")
        except Exception as e:
            print(f"[WARN] Ошибка очистки Memo: {e}")

        self._next_chunk()

    def _next_chunk(self):
        try:
            if not self._generating: return
            target_count = int(round(self.count_cur))
            start = self._current_chunk * self.CHUNK_SIZE
            if start >= target_count:
                self._finish_generation()
                return

            end = min(start + self.CHUNK_SIZE, target_count)
            count = end - start

            nums = [random.randint(self.RAND_MIN, self.RAND_MAX) for _ in range(count)]
            
            if start % 100 == 0:
                sep_text = f"── блок {start+1:04d}–{end:04d} ──\n"
                self.memo.insert("end", sep_text, "sep_line")

            for i in range(0, len(nums), self.NUMBERS_PER_LINE):
                chunk = nums[i:i+self.NUMBERS_PER_LINE]
                for n in chunk:
                    text = f"{n:>3}  " 
                    if n >= 90:
                        tag = "num_red"
                    elif n >= 80:
                        tag = "num_yellow"
                    else:
                        tag = "num"
                    self.memo.insert("end", text, tag)
                self.memo.insert("end", "\n")

            self.memo.see("end")

            self._current_chunk += 1
            self.canvas.itemconfigure(self.status_id, text=f"Выведено: {end} из {target_count}")

            try:
                total_lines = int(self.memo.index("end-1c").split(".")[0])
                if total_lines > self.MAX_LINES:
                    self.memo.delete("1.0", f"{total_lines - self.MAX_LINES + 1}.0")
            except Exception:
                pass

            self.root.after(20, self._next_chunk)
        except Exception as e:
            print(f"[ERR] Генерация: {e}")
            self._finish_generation(error=True)

    def _finish_generation(self, error=False):
        self._generating = False
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT)
        self.canvas.itemconfigure(self.btn_text_id, text="СГЕНЕРИРОВАТЬ")
        if error:
            self.canvas.itemconfigure(self.status_id, text="Ошибка генерации")
        else:
            target_count = int(round(self.count_cur))
            self.canvas.itemconfigure(self.status_id, text=f"Готово · {target_count} чисел · диапазон {self.RAND_MIN}–{self.RAND_MAX}")

    def _change_count(self, delta):
        self.count_tgt = max(self.COUNT_MIN, min(self.COUNT_MAX, self.count_tgt + delta))

    # ============================================================
    #                АНИМАЦИЯ И ЗАКРЫТИЕ
    # ============================================================
    def _anim_loop(self):
        dc = self.count_tgt - self.count_cur
        if abs(dc) < 0.5: self.count_cur = self.count_tgt
        else: self.count_cur += dc * self.ANIM_SMOOTHING

        self._redraw()
        self._anim_after_id = self.root.after(self.ANIM_INTERVAL_MS, self._anim_loop)

    def _redraw(self):
        shown_count = int(round(self.count_cur))
        self.canvas.itemconfigure(self.count_val_id, text=str(shown_count))

        t = (self.count_cur - self.COUNT_MIN) / (self.COUNT_MAX - self.COUNT_MIN)
        t = max(0.0, min(1.0, t))
        kx = self.len_x0 + (self.len_x1 - self.len_x0) * t
        fill_right = max(self.len_x0 + self.len_h * 2, kx)
        
        self._update_pill(self.len_fill_id, self.len_x0, self.len_y - self.len_r,
                          fill_right, self.len_y + self.len_r, self.len_r)
        self.canvas.coords(self.len_knob,
                           kx - self.len_knob_r, self.len_y - self.len_knob_r,
                           kx + self.len_knob_r, self.len_y + self.len_knob_r)

    def _on_close(self):
        self._generating = False
        if self._anim_after_id:
            try: self.root.after_cancel(self._anim_after_id)
            except: pass
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
        return self.canvas.create_polygon(self._pill_points(x0, y0, x1, y1, radius), smooth=True, **kwargs)

    def _fill_polygon(self, x0, y0, x1, y1, r, **kwargs):
        return self._rounded_rect(x0, y0, x1, y1, r, **kwargs)

    def _update_pill(self, item_id, x0, y0, x1, y1, r):
        self.canvas.coords(item_id, *self._pill_points(x0, y0, x1, y1, r))

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    @classmethod
    def _mix_color(cls, c1, c2, t):
        r1, g1, b1 = cls._hex_to_rgb(c1)
        r2, g2, b2 = cls._hex_to_rgb(c2)
        return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"

    def _center_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = RandomCountApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")