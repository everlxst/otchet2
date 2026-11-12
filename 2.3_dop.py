import sys
import platform
import random
import math
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


class RadioTunerApp:
    # ---------- Палитра ----------
    BG_TOP      = "#0F0B1E"
    BG_BOTTOM   = "#1A1035"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    
    ACCENT      = "#A78BFA"
    
    # Цвета шкалы
    SCALE_BG    = "#E8D9B8"  # Старая бумага
    SCALE_TEXT  = "#1A1A1A"  # Тёмно-коричневый (основной текст)
    SCALE_RED   = "#B22222"  # Для стрелки
    
    # Диапазон частот
    FREQ_MIN = 87.5
    FREQ_MAX = 108.0

    W, H = 900, 500
    CARD_MX, CARD_MT, CARD_MB = 30, 30, 30
    CARD_RADIUS = 24

    def __init__(self, root):
        self.root = root
        self.root.title("Радио-шкала · Анимация")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Состояние ---
        self._freq_cur = 98.0
        self._freq_tgt = 98.0
        self._anim_after_id = None
        self._running = True
        self._dragging = False

        self._init_fonts()

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        self._bg_photo = None
        self._draw_image_background()
        if not HAS_PIL or self._bg_photo is None:
            self._draw_gradient_background()

        self._draw_card()
        self._draw_radio_scale()
        self._draw_status_bar()

        self.root.bind("<Left>",  lambda e: self._nudge(-0.5))
        self.root.bind("<Right>", lambda e: self._nudge(+0.5))
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._anim_loop()

    def _init_fonts(self):
        self.title_font  = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.scale_font  = tkfont.Font(family="Consolas", size=24, weight="bold")
        self.scale_sub   = tkfont.Font(family="Consolas", size=14, weight="bold")
        self.scale_small = tkfont.Font(family="Consolas", size=10)
        self.status_font = tkfont.Font(family="Segoe UI", size=10)

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
        for cx, cy, rad, color in [(150, 150, 300, (120, 40, 200)),
                                   (w - 150, h - 150, 300, (30, 180, 220))]:
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

    # ============================================================
    #                ГЕНЕРАЦИЯ ШКАЛЫ (PIL)
    # ============================================================
    def _generate_scale_image(self, w, h):
        if not HAS_PIL: return None
        
        img = Image.new("RGB", (w, h), self.SCALE_BG)
        draw = ImageDraw.Draw(img)
        
        for _ in range(500):
            x = random.randint(0, w)
            y = random.randint(0, h)
            draw.point((x, y), fill=(random.randint(180, 220), random.randint(160, 200), random.randint(120, 160)))
            
        for _ in range(20):
            x0 = random.randint(0, w)
            y0 = random.randint(0, h)
            x1 = x0 + random.randint(-50, 50)
            y1 = y0 + random.randint(-5, 5)
            draw.line([(x0, y0), (x1, y1)], fill=(150, 130, 100), width=1)
            
        vignette = Image.new("L", (w, h), 0)
        vd = ImageDraw.Draw(vignette)
        vd.ellipse([-w*0.2, -h*0.2, w*1.2, h*1.2], fill=255)
        vignette = vignette.filter(ImageFilter.GaussianBlur(50))
        
        dark = Image.new("RGB", (w, h), (50, 40, 30))
        img = Image.composite(img, dark, vignette)
        
        return img

    # ============================================================
    #                РАДИО-ШКАЛА
    # ============================================================
    def _draw_radio_scale(self):
        x0, y0, x1, y1 = self.card
        
        self.scale_x0 = x0 + 40
        self.scale_x1 = x1 - 40
        self.scale_y0 = y0 + 40
        self.scale_y1 = y1 - 60
        self.scale_w = self.scale_x1 - self.scale_x0
        self.scale_h = self.scale_y1 - self.scale_y0

        # 1. Корпус радио (металлическая рамка)
        self._rounded_rect(self.scale_x0 - 5, self.scale_y0 - 5,
                           self.scale_x1 + 5, self.scale_y1 + 5,
                           radius=6, fill="#3B3B4A", outline="#1A1A25", width=2,
                           tags=("card",))

        # 2. Фон шкалы (текстура)
        if HAS_PIL:
            tex_img = self._generate_scale_image(int(self.scale_w), int(self.scale_h))
            self.scale_photo = ImageTk.PhotoImage(tex_img)
            self.canvas.create_image(self.scale_x0, self.scale_y0, anchor="nw", 
                                     image=self.scale_photo, tags=("card",))
        else:
            self.canvas.create_rectangle(self.scale_x0, self.scale_y0,
                                         self.scale_x1, self.scale_y1,
                                         fill=self.SCALE_BG, outline="", tags=("card",))

        # 3. Линии и цифры
        # Верхняя полоса с большими цифрами
        self.canvas.create_line(self.scale_x0, self.scale_y0 + 60,
                                self.scale_x1, self.scale_y0 + 60,
                                fill=self.SCALE_TEXT, width=2, tags=("card",))
        
        # Основная шкала (деления)
        self.canvas.create_line(self.scale_x0, self.scale_y0 + 95,
                                self.scale_x1, self.scale_y0 + 95,
                                fill=self.SCALE_TEXT, width=1, tags=("card",))
        
        # Нижняя полоса
        self.canvas.create_line(self.scale_x0, self.scale_y0 + 130,
                                self.scale_x1, self.scale_y0 + 130,
                                fill=self.SCALE_TEXT, width=1, tags=("card",))

        # Рисуем крупные метки (каждые 2 МГц)
        freq = 88
        last_x = self.scale_x0
        while freq <= 108:
            t = (freq - self.FREQ_MIN) / (self.FREQ_MAX - self.FREQ_MIN)
            x = self.scale_x0 + t * self.scale_w
            last_x = x
            
            self.canvas.create_text(x, self.scale_y0 + 30,
                                    text=str(freq), font=self.scale_font,
                                    fill=self.SCALE_TEXT, tags=("card",))
            
            self.canvas.create_line(x, self.scale_y0 + 85,
                                    x, self.scale_y0 + 105,
                                    fill=self.SCALE_TEXT, width=2, tags=("card",))
            
            if freq < 108:
                for sub in range(1, 10):
                    sub_freq = freq + sub * 0.2
                    if sub_freq >= 108: break
                    st = (sub_freq - self.FREQ_MIN) / (self.FREQ_MAX - self.FREQ_MIN)
                    sx = self.scale_x0 + st * self.scale_w
                    line_h = 5 if sub % 5 == 0 else 3
                    self.canvas.create_line(sx, self.scale_y0 + 95,
                                            sx, self.scale_y0 + 95 + line_h,
                                            fill=self.SCALE_TEXT, width=1, tags=("card",))
            
            freq += 2

        # Текст MHz
        self.canvas.create_text(last_x + 35, self.scale_y0 + 30,
                                text="MHz", font=self.scale_sub,
                                fill=self.SCALE_TEXT, anchor="w", tags=("card",))
        
        # Текст HIGH SELECTIVITY
        self.canvas.create_text(self.scale_x0 + 100, self.scale_y1 - 20,
                                text="HIGH SELECTIVITY", font=self.scale_sub,
                                fill=self.SCALE_TEXT, anchor="w", tags=("card",))
        
        # Текст LOG
        self.canvas.create_text(self.scale_x1 - 20, self.scale_y0 + 115,
                                text="LOG", font=self.scale_small,
                                fill=self.SCALE_TEXT, anchor="e", tags=("card",))

        # 4. Стрелка (линия + треугольная головка)
        self.arrow_x = self.scale_x0 + self.scale_w * 0.5
        
        self.arrow_line_id = self.canvas.create_line(
            self.arrow_x, self.scale_y0 + 10,
            self.arrow_x, self.scale_y0 + 120,
            fill=self.SCALE_RED, width=3, tags=("card", "arrow")
        )
        
        self.arrow_head_id = self.canvas.create_polygon(
            self.arrow_x - 8, self.scale_y0 + 5,
            self.arrow_x + 8, self.scale_y0 + 5,
            self.arrow_x, self.scale_y0 + 20,
            fill=self.SCALE_RED, outline="", tags=("card", "arrow")
        )

        # Текст частоты
        self.freq_text_id = self.canvas.create_text(
            self.arrow_x, self.scale_y0 + 155,
            text="98.0 MHz", font=self.scale_font,
            fill=self.SCALE_TEXT, tags=("card", "arrow_text")
        )

        # Привязка клика
        self.canvas.tag_bind("card", "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind("card", "<B1-Motion>", self._on_drag)
        self.canvas.tag_bind("card", "<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        if self.scale_x0 <= event.x <= self.scale_x1 and self.scale_y0 <= event.y <= self.scale_y1:
            self._dragging = True
            self._update_freq_from_x(event.x)

    def _on_drag(self, event):
        if self._dragging:
            self._update_freq_from_x(event.x)

    def _on_release(self, event):
        self._dragging = False

    def _update_freq_from_x(self, x):
        x = max(self.scale_x0, min(self.scale_x1, x))
        t = (x - self.scale_x0) / self.scale_w
        self._freq_tgt = self.FREQ_MIN + t * (self.FREQ_MAX - self.FREQ_MIN)

    def _nudge(self, delta):
        self._freq_tgt = max(self.FREQ_MIN, min(self.FREQ_MAX, self._freq_tgt + delta))

    # ============================================================
    #                СТАТУС-БАР
    # ============================================================
    def _draw_status_bar(self):
        self.canvas.create_rectangle(0, self.H - 34, self.W, self.H,
                                     fill=self._mix_color(self.BG_TOP, "#000000", 0.2),
                                     outline="", tags=("status_bg",))
        self.status_id = self.canvas.create_text(
            22, self.H - 17, text="Готово  ·  ←/→ или тяните мышью",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM, tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                АНИМАЦИЯ
    # ============================================================
    def _anim_loop(self):
        if not self._running: return

        # Плавное движение к цели
        d = self._freq_tgt - self._freq_cur
        if abs(d) > 0.01:
            self._freq_cur += d * 0.2
        else:
            self._freq_cur = self._freq_tgt

        # Вычисляем X
        t = (self._freq_cur - self.FREQ_MIN) / (self.FREQ_MAX - self.FREQ_MIN)
        self.arrow_x = self.scale_x0 + t * self.scale_w

        # Двигаем линию и головку
        self.canvas.coords(self.arrow_line_id,
                           self.arrow_x, self.scale_y0 + 10,
                           self.arrow_x, self.scale_y0 + 120)
        
        self.canvas.coords(self.arrow_head_id,
                           self.arrow_x - 8, self.scale_y0 + 5,
                           self.arrow_x + 8, self.scale_y0 + 5,
                           self.arrow_x, self.scale_y0 + 20)
        
        # --- Исправление: прижимаем текст к границам шкалы ---
        text_half_w = 70  # Примерная половина ширины текста "108.0 MHz" в 24pt
        text_x = max(self.scale_x0 + text_half_w, min(self.scale_x1 - text_half_w, self.arrow_x))
        
        self.canvas.coords(self.freq_text_id, text_x, self.scale_y0 + 155)
        self.canvas.itemconfigure(self.freq_text_id, text=f"{self._freq_cur:.1f} MHz")

        self._anim_after_id = self.root.after(16, self._anim_loop)

    # ============================================================
    #                УТИЛИТЫ
    # ============================================================
    def _on_close(self):
        self._running = False
        if self._anim_after_id:
            try: self.root.after_cancel(self._anim_after_id)
            except: pass
        try: self.root.destroy()
        except Exception: pass

    def _pill_points(self, x0, y0, x1, y1, r):
        if x1 - x0 < 2 * r: x1 = x0 + 2 * r
        if y1 - y0 < 2 * r: y1 = y0 + 2 * r
        rr = min(r, (y1 - y0) / 2, (x1 - x0) / 2)
        return [x0 + rr, y0, x1 - rr, y0, x1, y0, x1, y0 + rr,
                x1, y1 - rr, x1, y1, x1 - rr, y1, x0 + rr, y1,
                x0, y1, x0, y1 - rr, x0, y0 + rr, x0, y0]

    def _rounded_rect(self, x0, y0, x1, y1, radius, **kwargs):
        return self.canvas.create_polygon(self._pill_points(x0, y0, x1, y1, radius), smooth=True, **kwargs)

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
        app = RadioTunerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")