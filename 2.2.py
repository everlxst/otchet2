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


class RandomRangeApp:
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
    
    # Цвета кнопки "Пауза"
    PAUSE_COL   = "#22D3EE"

    W, H = 760, 680
    CARD_MX, CARD_MT, CARD_MB = 40, 30, 50
    CARD_RADIUS = 30

    RANGE_MIN = 1
    RANGE_MAX = 1000
    RANGE_START = 100
    
    TIMER_INTERVAL_MS = 300
    ANIM_INTERVAL_MS = 16
    ANIM_SMOOTHING = 0.25
    ANIM_EPS = 0.5

    def __init__(self, root):
        self.root = root
        self.root.title("Диапазон случайных чисел · TrackBar")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Состояние ---
        self.range_cur = float(self.RANGE_START)
        self.range_tgt = float(self.RANGE_START)
        
        self.num_cur = 0.0
        self.num_tgt = 0.0
        self._num_pulse = 0.0  # для анимации пульсации
        
        self._drag = None
        self._timer_running = False
        self._timer_after_id = None
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
        self._draw_number_display()
        self._draw_slider()
        self._draw_buttons()
        self._draw_status_bar()

        # Клавиатурное управление
        self.root.bind("<Left>",  lambda e: self._change_range(-10))
        self.root.bind("<Right>", lambda e: self._change_range(+10))
        self.root.bind("<space>", lambda e: self._generate_manual())
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Старт анимации
        self._anim_loop()
        # Запускаем таймер
        self._toggle_timer()

    def _init_fonts(self):
        self.title_font   = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.sub_font     = tkfont.Font(family="Segoe UI", size=10)
        self.lbl_font     = tkfont.Font(family="Segoe UI", size=10)
        self.num_font     = tkfont.Font(family="Consolas", size=72, weight="bold")
        self.val_font     = tkfont.Font(family="Consolas", size=15, weight="bold")
        self.btn_font     = tkfont.Font(family="Segoe UI", size=12, weight="bold")
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
        self.canvas.create_text(cx, y0 + 50, text="🎲  СЛУЧАЙНОЕ ЧИСЛО В ДИАПАЗОНЕ",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))
        self.canvas.create_text(cx, y0 + 74, text="двигай ползунок — задай диапазон · число меняется автоматически",
                                font=self.sub_font, fill=self.TEXT_DIM, tags=("card",))

    # ============================================================
    #                ОТОБРАЖЕНИЕ ЧИСЛА
    # ============================================================
    def _draw_number_display(self):
        x0, y0, x1, _ = self.card
        self.num_cy = y0 + 230
        cx = (x0 + x1) / 2

        self.num_text_id = self.canvas.create_text(
            cx, self.num_cy, text="0",
            font=self.num_font, fill=self.ACCENT, anchor="center", tags=("card", "num_text")
        )

    # ============================================================
    #                ПОЛЗУНОК
    # ============================================================
    def _draw_slider(self):
        x0, y0, x1, _ = self.card
        pad = 60
        self.len_x0 = x0 + pad
        self.len_x1 = x1 - pad
        self.len_y = y0 + 370
        self.len_h = 10
        self.len_r = self.len_h / 2
        self.len_knob_r = 14

        self.canvas.create_text(self.len_x0, self.len_y - 30, anchor="w",
                                text="ВЕРХНЯЯ ГРАНИЦА ДИАПАЗОНА", font=self.lbl_font, fill=self.TEXT_DIM, tags=("card",))
        self.range_val_id = self.canvas.create_text(self.len_x1, self.len_y - 30, anchor="e",
                                text=str(int(self.range_cur)), font=self.val_font, fill=self.ACCENT, tags=("card",))

        self._fill_polygon(self.len_x0, self.len_y - self.len_r, self.len_x1, self.len_y + self.len_r, self.len_r,
                           fill=self._mix_color(self.CARD_BOTTOM, "#000000", 0.6), outline="#5B4A8A", width=1, tags=("card", "len_bg",))
        self.len_fill_id = self._fill_polygon(self.len_x0, self.len_y - self.len_r, self.len_x0 + 10, self.len_y + self.len_r, self.len_r,
                           fill=self.ACCENT, outline="", tags=("card", "len_fill",))
        self.len_knob = self.canvas.create_oval(0, 0, 0, 0, fill=self.TEXT_LIGHT, outline=self.ACCENT, width=3, tags=("card", "len_knob",))

        for tag in ("len_bg", "len_fill", "len_knob"):
            self.canvas.tag_bind(tag, "<ButtonPress-1>",   self._len_press)
            self.canvas.tag_bind(tag, "<B1-Motion>",       self._len_drag)
            self.canvas.tag_bind(tag, "<ButtonRelease-1>", self._len_release)

    def _len_val_from_x(self, x):
        t = (x - self.len_x0) / (self.len_x1 - self.len_x0)
        return max(0.0, min(1.0, t)) * (self.RANGE_MAX - self.RANGE_MIN) + self.RANGE_MIN

    def _len_press(self, event):
        self._drag = "LEN"
        self.range_tgt = float(self._len_val_from_x(event.x))
        self._clamp_current_number()

    def _len_drag(self, event):
        if self._drag == "LEN":
            self.range_tgt = float(self._len_val_from_x(event.x))
            self._clamp_current_number()

    def _len_release(self, event):
        self._drag = None

    def _clamp_current_number(self):
        if self.num_tgt > self.range_tgt:
            self.num_tgt = self.range_tgt

    # ============================================================
    #                КНОПКИ
    # ============================================================
    def _draw_buttons(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        cy = y0 + 460

        bw, bh = 170, 46  # Увеличенная ширина, чтобы не было обрезки

        # 1. Кнопка "СГЕНЕРИРОВАТЬ"
        bx0 = cx - 180
        bx1 = bx0 + bw
        by0 = cy - bh / 2
        by1 = cy + bh / 2
        self._rounded_rect(bx0, by0, bx1, by1, radius=bh/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.2),
                           outline=self.ACCENT, width=1, tags=("card", "btn_manual"))
        self.canvas.create_text((bx0+bx1)/2, cy, text="СГЕНЕРИРОВАТЬ",
                                font=self.btn_font, fill=self.ACCENT, tags=("card", "btn_manual"))

        # 2. Кнопка "АВТО / ПАУЗА"
        bx0 = cx + 10
        bx1 = bx0 + bw
        by0 = cy - bh / 2
        by1 = cy + bh / 2
        
        self.btn_timer_body = self._rounded_rect(bx0, by0, bx1, by1, radius=bh/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.2),
                           outline=self.ACCENT, width=1, tags=("card", "btn_timer"))
        
        self.timer_text_id = self.canvas.create_text(
            (bx0+bx1)/2, cy, text="АВТО",
            font=self.btn_font, fill=self.ACCENT, tags=("card", "btn_timer"))

        # Привязка событий
        self.canvas.tag_bind("btn_manual", "<ButtonRelease-1>", lambda e: self._generate_manual())
        self.canvas.tag_bind("btn_manual", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("btn_manual", "<Leave>", lambda e: self.canvas.config(cursor=""))

        self.canvas.tag_bind("btn_timer", "<ButtonRelease-1>", lambda e: self._toggle_timer())
        self.canvas.tag_bind("btn_timer", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("btn_timer", "<Leave>", lambda e: self.canvas.config(cursor=""))

    # ============================================================
    #                СТАТУС-БАР
    # ============================================================
    def _draw_status_bar(self):
        self.canvas.create_rectangle(0, self.H - 34, self.W, self.H,
                                     fill=self._mix_color(self.BG_TOP, "#000000", 0.2),
                                     outline="", tags=("status_bg",))
        self.status_id = self.canvas.create_text(
            22, self.H - 17,
            text="←/→ — диапазон · Space — новое число",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM,
            tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                ЛОГИКА
    # ============================================================
    def _change_range(self, delta):
        self.range_tgt = max(self.RANGE_MIN, min(self.RANGE_MAX, self.range_tgt + delta))
        self._clamp_current_number()

    def _generate_manual(self):
        self._generate_number()

    def _toggle_timer(self):
        self._timer_running = not self._timer_running
        if self._timer_running:
            self.canvas.itemconfigure(self.timer_text_id, text="ПАУЗА")
            self.canvas.itemconfigure(self.btn_timer_body, fill=self._mix_color(self.CARD_BOTTOM, self.PAUSE_COL, 0.2), outline=self.PAUSE_COL)
            self.canvas.itemconfigure(self.status_id, text="Таймер запущен · ←/→ — диапазон")
            self._schedule_timer()
        else:
            self.canvas.itemconfigure(self.timer_text_id, text="АВТО")
            self.canvas.itemconfigure(self.btn_timer_body, fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.2), outline=self.ACCENT)
            self.canvas.itemconfigure(self.status_id, text="Таймер на паузе · Space — новое число")
            if self._timer_after_id:
                try: self.root.after_cancel(self._timer_after_id)
                except: pass
                self._timer_after_id = None

    def _schedule_timer(self):
        if not self._timer_running: return
        self._generate_number()
        self._timer_after_id = self.root.after(self.TIMER_INTERVAL_MS, self._schedule_timer)

    def _generate_number(self):
        max_val = int(round(self.range_tgt))
        if max_val < 0: max_val = 0
        new_val = random.randint(0, max_val)
        self.num_tgt = float(new_val)
        self._num_pulse = 1.0  # Запуск пульсации

    # ============================================================
    #                АНИМАЦИЯ И ОБНОВЛЕНИЕ
    # ============================================================
    def _anim_loop(self):
        # Сглаживаем ползунок
        dr = self.range_tgt - self.range_cur
        if abs(dr) < 0.5: self.range_cur = self.range_tgt
        else: self.range_cur += dr * 0.3
        
        # Сглаживаем число
        dn = self.num_tgt - self.num_cur
        if abs(dn) < self.ANIM_EPS: self.num_cur = self.num_tgt
        else: self.num_cur += dn * self.ANIM_SMOOTHING

        # Затухание пульсации
        if self._num_pulse > 0:
            self._num_pulse = max(0.0, self._num_pulse - 0.08)

        self._redraw()
        self._anim_after_id = self.root.after(self.ANIM_INTERVAL_MS, self._anim_loop)

    def _redraw(self):
        # 1. Обновляем текст и пульсацию числа
        shown_num = int(round(self.num_cur))
        self.canvas.itemconfigure(self.num_text_id, text=str(shown_num))
        
        # Применяем размер шрифта с учётом пульсации
        base_size = 72
        current_size = int(base_size + base_size * 0.08 * self._num_pulse)
        temp_font = tkfont.Font(family="Consolas", size=current_size, weight="bold")
        self.canvas.itemconfigure(self.num_text_id, font=temp_font)

        # 2. Обновляем текст диапазона
        shown_range = int(round(self.range_cur))
        self.canvas.itemconfigure(self.range_val_id, text=str(shown_range))

        # 3. Двигаем ползунок
        t = (self.range_cur - self.RANGE_MIN) / (self.RANGE_MAX - self.RANGE_MIN)
        t = max(0.0, min(1.0, t))
        kx = self.len_x0 + (self.len_x1 - self.len_x0) * t
        fill_right = max(self.len_x0 + self.len_h * 2, kx)
        
        self._update_pill(self.len_fill_id, self.len_x0, self.len_y - self.len_r,
                          fill_right, self.len_y + self.len_r, self.len_r)
        self.canvas.coords(self.len_knob,
                           kx - self.len_knob_r, self.len_y - self.len_knob_r,
                           kx + self.len_knob_r, self.len_y + self.len_knob_r)

    # ============================================================
    #                БЕЗОПАСНОЕ ЗАКРЫТИЕ
    # ============================================================
    def _on_close(self):
        self._timer_running = False
        if self._timer_after_id:
            try: self.root.after_cancel(self._timer_after_id)
            except: pass
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
        app = RandomRangeApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")