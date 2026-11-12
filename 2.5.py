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


class RandomScatterApp:
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
    
    INPUT_BG    = "#100A1F"
    INPUT_BORDER= "#4B3B7A"
    ERROR_RED   = "#EF4444"
    
    DOT_DEFAULT = "#A78BFA"
    DOT_YELLOW  = "#FBBF24"
    DOT_RED     = "#EF4444"
    
    PLOT_BG     = "#100A1F"
    PLOT_GRID   = "#2A1F45"

    W, H = 760, 820
    CARD_MX, CARD_MT, CARD_MB = 40, 30, 50
    CARD_RADIUS = 30

    # Параметры
    COUNT_MIN = 1
    COUNT_MAX = 1000
    COUNT_START = 200
    
    VAL_MIN = -9999
    VAL_MAX = 9999
    
    DOT_RADIUS = 3

    def __init__(self, root):
        self.root = root
        self.root.title("График случайных чисел")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        self._generating = False
        self._dots = []
        
        self._anim_after_id = None
        self._anim_running = False

        self._init_fonts()

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        self._bg_photo = None
        self._draw_image_background()
        if not HAS_PIL or self._bg_photo is None:
            self._draw_gradient_background()

        self._draw_card()
        self._draw_header()
        self._draw_inputs()
        self._draw_plot_area()
        self._draw_stats_area()
        self._draw_buttons()
        self._draw_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._anim_running = True
        self._anim_loop()

    def _init_fonts(self):
        self.title_font   = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.lbl_font     = tkfont.Font(family="Segoe UI", size=10)
        self.input_font   = tkfont.Font(family="Consolas", size=14, weight="bold")
        self.badge_font   = tkfont.Font(family="Consolas", size=12, weight="bold")
        self.stat_font    = tkfont.Font(family="Consolas", size=11)
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
        self.canvas.create_text(cx, y0 + 50, text="🎯  ГРАФИК СЛУЧАЙНЫХ ЧИСЕЛ",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))

    # ============================================================
    #                ПОЛЯ ВВОДА
    # ============================================================
    def _draw_inputs(self):
        x0, y0, x1, _ = self.card
        cx = (x0 + x1) / 2
        inp_y = y0 + 95

        # Поле "От"
        lbl_from = self.canvas.create_text(cx - 150, inp_y - 15, text="От", font=self.lbl_font,
                                           fill=self.TEXT_DIM, tags=("card",))
        self.entry_from = tk.Entry(self.root, font=self.input_font, bg=self.INPUT_BG,
                                   fg=self.TEXT_LIGHT, insertbackground=self.TEXT_LIGHT,
                                   justify="center", bd=0, highlightthickness=1,
                                   highlightbackground=self.INPUT_BORDER,
                                   highlightcolor=self.ACCENT, width=8)
        self.entry_from.insert(0, "0")
        self.canvas.create_window(cx - 150, inp_y + 12, window=self.entry_from,
                                  width=90, height=32, tags=("card",))

        # Поле "До"
        lbl_to = self.canvas.create_text(cx, inp_y - 15, text="До", font=self.lbl_font,
                                         fill=self.TEXT_DIM, tags=("card",))
        self.entry_to = tk.Entry(self.root, font=self.input_font, bg=self.INPUT_BG,
                                 fg=self.TEXT_LIGHT, insertbackground=self.TEXT_LIGHT,
                                 justify="center", bd=0, highlightthickness=1,
                                 highlightbackground=self.INPUT_BORDER,
                                 highlightcolor=self.ACCENT, width=8)
        self.entry_to.insert(0, "100")
        self.canvas.create_window(cx, inp_y + 12, window=self.entry_to,
                                  width=90, height=32, tags=("card",))

        # Поле "Количество"
        lbl_count = self.canvas.create_text(cx + 150, inp_y - 15, text="Кол-во (1–1000)",
                                            font=self.lbl_font, fill=self.TEXT_DIM, tags=("card",))
        self.entry_count = tk.Entry(self.root, font=self.input_font, bg=self.INPUT_BG,
                                    fg=self.TEXT_LIGHT, insertbackground=self.TEXT_LIGHT,
                                    justify="center", bd=0, highlightthickness=1,
                                    highlightbackground=self.INPUT_BORDER,
                                    highlightcolor=self.ACCENT, width=8)
        self.entry_count.insert(0, str(self.COUNT_START))
        self.canvas.create_window(cx + 150, inp_y + 12, window=self.entry_count,
                                  width=90, height=32, tags=("card",))

    # ============================================================
    #                ОБЛАСТЬ ГРАФИКА
    # ============================================================
    def _draw_plot_area(self):
        x0, y0, x1, y1 = self.card
        self.plot_pad = 55
        self.plot_x0 = x0 + self.plot_pad
        self.plot_x1 = x1 - self.plot_pad
        self.plot_y0 = y0 + 160
        self.plot_y1 = y1 - 220
        self.plot_w = self.plot_x1 - self.plot_x0
        self.plot_h = self.plot_y1 - self.plot_y0

        self._rounded_rect(
            self.plot_x0, self.plot_y0, self.plot_x1, self.plot_y1,
            radius=10, fill=self.PLOT_BG, outline="#5B4A8A", width=1,
            tags=("card", "plot_bg"))

        for i in range(1, 4):
            y = self.plot_y0 + self.plot_h * i / 4
            self.canvas.create_line(self.plot_x0, y, self.plot_x1, y,
                                    fill=self.PLOT_GRID, width=1, tags=("card",))
        for i in range(1, 4):
            x = self.plot_x0 + self.plot_w * i / 4
            self.canvas.create_line(x, self.plot_y0, x, self.plot_y1,
                                    fill=self.PLOT_GRID, width=1, tags=("card",))

    def _draw_stats_area(self):
        x0, y0, x1, y1 = self.card
        self.stats_y = self.plot_y1 + 30
        cx = (x0 + x1) / 2
        self.stats_id = self.canvas.create_text(
            cx, self.stats_y,
            text="Введите данные и нажмите «Построить»",
            font=self.stat_font, fill=self.TEXT_DIM, anchor="center",
            tags=("card",)
        )

    # ============================================================
    #                КНОПКИ
    # ============================================================
    def _draw_buttons(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        cy = y1 - 75

        bw, bh = 220, 48
        bx0 = cx - bw/2
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
        self.btn_text_id = self.canvas.create_text(cx, cy, text="ПОСТРОИТЬ ГРАФИК",
                                                   font=self.btn_font, fill=self.BTN_FG, tags=("card", "gen_btn"))

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
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT)

    def _btn_press(self, _):
        if self._generating: return
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_PRS)

    def _btn_release(self, event):
        if self._generating: return
        self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT_HOV)
        self._generate_plot()

    # ============================================================
    #                СТАТУС-БАР
    # ============================================================
    def _draw_status_bar(self):
        self.canvas.create_rectangle(0, self.H - 34, self.W, self.H,
                                     fill=self._mix_color(self.BG_TOP, "#000000", 0.2),
                                     outline="", tags=("status_bg",))
        self.status_id = self.canvas.create_text(
            22, self.H - 17, text="Готово",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM, tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                ЛОГИКА
    # ============================================================
    def _validate_inputs(self):
        """Проверяем ввод. Возвращает (val_min, val_max, count) или None."""
        try:
            v_from = int(self.entry_from.get().strip())
            v_to = int(self.entry_to.get().strip())
            count = int(self.entry_count.get().strip())
        except ValueError:
            self._show_error("Введите целые числа!")
            return None

        if v_from >= v_to:
            self._show_error("«От» должно быть меньше «До»!")
            return None
        
        if count < self.COUNT_MIN or count > self.COUNT_MAX:
            self._show_error(f"Количество от {self.COUNT_MIN} до {self.COUNT_MAX}!")
            return None
        
        if v_from < self.VAL_MIN or v_to > self.VAL_MAX:
            self._show_error(f"Диапазон от {self.VAL_MIN} до {self.VAL_MAX}!")
            return None
            
        # Успешная валидация — сбрасываем подсветку
        self._reset_error_highlight()
        return v_from, v_to, count

    def _show_error(self, msg):
        self.canvas.itemconfigure(self.status_id, text=msg, fill=self.ERROR_RED)
        for entry in (self.entry_from, self.entry_to, self.entry_count):
            entry.configure(highlightbackground=self.ERROR_RED, highlightcolor=self.ERROR_RED)

    def _reset_error_highlight(self):
        for entry in (self.entry_from, self.entry_to, self.entry_count):
            entry.configure(highlightbackground=self.INPUT_BORDER, highlightcolor=self.ACCENT)
        self.canvas.itemconfigure(self.status_id, fill=self.TEXT_DIM)

    def _clear_plot(self):
        for dot in self._dots:
            self.canvas.delete(dot["id"])
        self._dots = []

    def _generate_plot(self):
        if self._generating: return
        
        validated = self._validate_inputs()
        if not validated:
            return
        
        v_min, v_max, count = validated
        self._clear_plot()
        
        self._generating = True
        self.canvas.itemconfigure(self.btn_text_id, text="ПОСТРОЕНИЕ...")
        self.canvas.itemconfigure(self.btn_body, fill=self._mix_color(self.ACCENT, "#000000", 0.3))
        self.canvas.itemconfigure(self.status_id, text="Генерация...")
        
        self.root.update_idletasks()

        try:
            # Цветовые пороги относительно нового диапазона
            thresh_yellow = v_min + (v_max - v_min) * 0.8
            thresh_red = v_min + (v_max - v_min) * 0.9
            
            values = []
            for _ in range(count):
                val = random.randint(v_min, v_max)
                values.append(val)
                
                # Нормализуем Y
                y_ratio = (val - v_min) / (v_max - v_min)
                y = self.plot_y1 - y_ratio * self.plot_h
                # Случайный X
                x = self.plot_x0 + random.uniform(0, 1) * self.plot_w
                
                if val >= thresh_red:
                    color = self.DOT_RED
                elif val >= thresh_yellow:
                    color = self.DOT_YELLOW
                else:
                    color = self.DOT_DEFAULT
                    
                r = self.DOT_RADIUS
                dot_id = self.canvas.create_oval(
                    x - r, y - r, x + r, y + r,
                    fill=color, outline=color, tags=("card", "dot")
                )
                self._dots.append({"id": dot_id, "color": color, "life": 1.0})

            # Обновляем подписи оси Y
            self._update_y_labels(v_min, v_max)
            
            # Статистика
            avg = sum(values) / count
            mx = max(values)
            mn = min(values)
            variance = sum((v - avg) ** 2 for v in values) / count
            stddev = math.sqrt(variance)
            text = f"Среднее: {avg:.1f}  ·  Мин: {mn}  ·  Макс: {mx}  ·  σ: {stddev:.1f}"
            self.canvas.itemconfigure(self.stats_id, text=text, fill=self.TEXT_LIGHT)
            
            self.canvas.itemconfigure(self.status_id, text=f"Готово · {count} чисел · диапазон {v_min}…{v_max}")
            
        except Exception as e:
            print(f"[ERR] {e}")
            self.canvas.itemconfigure(self.status_id, text=f"Ошибка: {e}")
        finally:
            self._generating = False
            self.canvas.itemconfigure(self.btn_body, fill=self.ACCENT)
            self.canvas.itemconfigure(self.btn_text_id, text="ПОСТРОИТЬ ГРАФИК")

    def _update_y_labels(self, v_min, v_max):
        # Удаляем старые подписи (они были с тегом y_label)
        self.canvas.delete("y_label")
        
        for i in range(5):
            ratio = i / 4  # 0.0 ... 1.0
            y = self.plot_y0 + self.plot_h * ratio
            val = v_max - (v_max - v_min) * ratio
            self.canvas.create_text(self.plot_x0 - 10, y, anchor="e",
                                    text=f"{int(val)}", font=self.status_font,
                                    fill=self.TEXT_DIM, tags=("card", "y_label"))

    # ============================================================
    #                АНИМАЦИЯ
    # ============================================================
    def _anim_loop(self):
        if not self._anim_running: return
        for dot in self._dots:
            if dot["life"] <= 0: continue
            dot["life"] -= 0.06
            if dot["life"] <= 0:
                self.canvas.itemconfigure(dot["id"], fill=dot["color"], outline=dot["color"])
            else:
                mix = dot["life"]
                current = self._mix_color(dot["color"], "#FFFFFF", mix)
                self.canvas.itemconfigure(dot["id"], fill=current, outline=current)
        self._anim_after_id = self.root.after(16, self._anim_loop)

    def _on_close(self):
        self._anim_running = False
        if self._anim_after_id:
            try: self.root.after_cancel(self._anim_after_id)
            except: pass
        try: self.root.destroy()
        except Exception: pass

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
        app = RandomScatterApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")