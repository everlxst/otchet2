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

HAS_OPENPYXL = False
try:
    import openpyxl
    from openpyxl.chart import BarChart, LineChart, Reference
    HAS_OPENPYXL = True
except ImportError:
    print("[OK] openpyxl не найден — будет сохранён CSV")


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
    
    DOT_DEFAULT = "#A78BFA"
    DOT_YELLOW  = "#FBBF24"
    DOT_RED     = "#EF4444"
    
    PLOT_BG     = "#100A1F"
    PLOT_GRID   = "#2A1F45"

    W, H = 760, 800
    CARD_MX, CARD_MT, CARD_MB = 40, 30, 50
    CARD_RADIUS = 30

    RAND_MIN = 0
    RAND_MAX = 100
    COUNT = 1000
    CHUNK_SIZE = 100
    DOT_RADIUS = 3

    ANIM_INTERVAL_MS = 16

    def __init__(self, root):
        self.root = root
        self.root.title("График случайных чисел")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        self._generating = False
        self._current_chunk = 0
        self._dots = []
        self._raw_values = []
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
        
        badge_w, badge_h = 240, 28
        bx0 = cx - badge_w / 2
        by0 = y0 + 78
        self._rounded_rect(bx0, by0, bx0 + badge_w, by0 + badge_h, radius=badge_h/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.15),
                           outline=self.ACCENT, width=1, tags=("card",))
        self.canvas.create_text(cx, by0 + badge_h/2,
                                text=f"1000 точек · диапазон {self.RAND_MIN} … {self.RAND_MAX}",
                                font=self.badge_font, fill=self.ACCENT, tags=("card",))

    # ============================================================
    #                ОБЛАСТЬ ГРАФИКА
    # ============================================================
    def _draw_plot_area(self):
        x0, y0, x1, y1 = self.card
        self.plot_pad = 50
        self.plot_x0 = x0 + self.plot_pad
        self.plot_x1 = x1 - self.plot_pad
        self.plot_y0 = y0 + 120
        self.plot_y1 = y1 - 250
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

        for i, val in enumerate([100, 75, 50, 25, 0]):
            y = self.plot_y0 + self.plot_h * i / 4
            self.canvas.create_text(self.plot_x0 - 10, y, anchor="e",
                                    text=str(val), font=self.status_font,
                                    fill=self.TEXT_DIM, tags=("card",))

    def _draw_stats_area(self):
        x0, y0, x1, y1 = self.card
        self.stats_y = self.plot_y1 + 30
        cx = (x0 + x1) / 2
        self.stats_id = self.canvas.create_text(
            cx, self.stats_y,
            text="Статистика появится после генерации",
            font=self.stat_font, fill=self.TEXT_DIM, anchor="center",
            tags=("card",)
        )

    def _update_stats(self):
        if not self._raw_values:
            self.canvas.itemconfigure(self.stats_id, text="Статистика появится после генерации")
            return
        vals = self._raw_values
        n = len(vals)
        avg = sum(vals) / n
        mx = max(vals)
        mn = min(vals)
        variance = sum((v - avg) ** 2 for v in vals) / n
        stddev = math.sqrt(variance)
        text = f"Среднее: {avg:.1f}  ·  Мин: {mn}  ·  Макс: {mx}  ·  σ: {stddev:.1f}"
        self.canvas.itemconfigure(self.stats_id, text=text, fill=self.TEXT_LIGHT)

    # ============================================================
    #                КНОПКИ
    # ============================================================
    def _draw_buttons(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        cy = y1 - 105

        bw, bh = 180, 44
        gap = 10

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

        ex_cy = cy + 40
        ex_w, ex_h = 180, 30
        ex_x0 = cx - ex_w/2
        ex_x1 = cx + ex_w/2
        ex_y0 = ex_cy - ex_h/2
        ex_y1 = ex_cy + ex_h/2
        self._rounded_rect(ex_x0, ex_y0, ex_x1, ex_y1, radius=ex_h/2,
                           fill=self._mix_color(self.CARD_BOTTOM, self.ACCENT, 0.1),
                           outline=self.ACCENT, width=1, tags=("card", "exp_btn"))
        self.canvas.create_text(cx, ex_cy, text="💾 ЭКСПОРТ В EXCEL",
                                font=self.status_font, fill=self.ACCENT, tags=("card", "exp_btn"))

        self.canvas.tag_bind("gen_btn", "<Enter>", self._btn_enter)
        self.canvas.tag_bind("gen_btn", "<Leave>", self._btn_leave)
        self.canvas.tag_bind("gen_btn", "<ButtonPress-1>", self._btn_press)
        self.canvas.tag_bind("gen_btn", "<ButtonRelease-1>", self._btn_release)

        self.canvas.tag_bind("clr_btn", "<ButtonRelease-1>", lambda e: self._clear_plot())
        self.canvas.tag_bind("clr_btn", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("clr_btn", "<Leave>", lambda e: self.canvas.config(cursor=""))

        self.canvas.tag_bind("exp_btn", "<ButtonRelease-1>", lambda e: self._export_to_excel())
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
            22, self.H - 17, text="Готово  ·  нажмите «Сгенерировать»",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM, tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    # ============================================================
    #                ЛОГИКА
    # ============================================================
    def _clear_plot(self):
        if self._generating: return
        for dot in self._dots:
            self.canvas.delete(dot["id"])
        self._dots = []
        self._raw_values = []
        self.canvas.itemconfigure(self.status_id, text="Очищено")
        self.canvas.itemconfigure(self.stats_id, text="Статистика появится после генерации", fill=self.TEXT_DIM)

    def _generate_async(self):
        if self._generating: return
        self._generating = True
        self._current_chunk = 0
        self._clear_plot()

        self.canvas.itemconfigure(self.btn_text_id, text="ГЕНЕРАЦИЯ...")
        self.canvas.itemconfigure(self.btn_body, fill=self._mix_color(self.ACCENT, "#000000", 0.3))
        self.canvas.itemconfigure(self.status_id, text=f"Выведено: 0 из {self.COUNT}")

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

            for _ in range(count):
                val = random.randint(self.RAND_MIN, self.RAND_MAX)
                self._raw_values.append(val)
                y = self.plot_y1 - (val / self.RAND_MAX) * self.plot_h
                x = self.plot_x0 + random.uniform(0, 1) * self.plot_w

                if val >= 90:
                    color = self.DOT_RED
                elif val >= 80:
                    color = self.DOT_YELLOW
                else:
                    color = self.DOT_DEFAULT

                r = self.DOT_RADIUS
                dot_id = self.canvas.create_oval(
                    x - r, y - r, x + r, y + r,
                    fill=color, outline=color, tags=("card", "dot")
                )
                self._dots.append({"id": dot_id, "color": color, "life": 1.0})

            self._current_chunk += 1
            self.canvas.itemconfigure(self.status_id, text=f"Выведено: {end} из {self.COUNT}")
            self.root.after(15, self._next_chunk)
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
            self.canvas.itemconfigure(self.status_id, text=f"Готово · {self.COUNT} точек · диапазон {self.RAND_MIN}–{self.RAND_MAX}")
            self._update_stats()

    # ============================================================
    #                ЭКСПОРТ В EXCEL / CSV
    # ============================================================
    def _export_to_excel(self):
        if not self._raw_values:
            self.canvas.itemconfigure(self.status_id, text="Нет данных для экспорта")
            return
        try:
            if HAS_OPENPYXL:
                self._save_xlsx()
            else:
                self._save_csv()
        except PermissionError:
            self.canvas.itemconfigure(self.status_id, text="Файл открыт в Excel — закройте его")
        except Exception as e:
            print(f"[ERR] Экспорт: {e}")
            self.canvas.itemconfigure(self.status_id, text=f"Ошибка: {e}")

    def _save_csv(self):
        filename = "random_data.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#,Value\n")
            for i, v in enumerate(self._raw_values, 1):
                f.write(f"{i},{v}\n")
        self.canvas.itemconfigure(self.status_id, text=f"Сохранено в {filename} (CSV)")

    def _save_xlsx(self):
        filename = "random_data.xlsx"
        wb = openpyxl.Workbook()

        # --- Лист 1: Данные ---
        ws = wb.active
        ws.title = "Данные"
        ws.cell(row=1, column=1, value="№")
        ws.cell(row=1, column=2, value="Значение")
        for i, v in enumerate(self._raw_values, 1):
            ws.cell(row=i+1, column=1, value=i)
            ws.cell(row=i+1, column=2, value=v)

        # --- Лист 2: Гистограмма (частоты) ---
        ws_hist = wb.create_sheet("Гистограмма")
        ws_hist.cell(row=1, column=1, value="Диапазон")
        ws_hist.cell(row=1, column=2, value="Количество")

        bins = [(i, i+9) for i in range(0, 100, 10)]
        counts = [0] * len(bins)
        for v in self._raw_values:
            idx = min(v // 10, len(bins) - 1)
            counts[idx] += 1

        for i, (lo, hi) in enumerate(bins):
            ws_hist.cell(row=i+2, column=1, value=f"{lo}-{hi}")
            ws_hist.cell(row=i+2, column=2, value=counts[i])

        bar_chart = BarChart()
        bar_chart.type = "col"
        bar_chart.title = "Распределение случайных чисел"
        bar_chart.x_axis.title = "Диапазон"
        bar_chart.y_axis.title = "Количество"
        bar_chart.width = 20
        bar_chart.height = 12
        bar_chart.legend = None  # Убираем легенду

        data = Reference(ws_hist, min_col=2, min_row=1, max_row=len(bins)+1)
        cats = Reference(ws_hist, min_col=1, min_row=2, max_row=len(bins)+1)
        bar_chart.add_data(data, titles_from_data=True)
        bar_chart.set_categories(cats)
        ws_hist.add_chart(bar_chart, "D2")

        # --- Лист 3: Линейный график динамики ---
        ws_line = wb.create_sheet("Динамика")
        ws_line.cell(row=1, column=1, value="Порядковый номер")
        ws_line.cell(row=1, column=2, value="Значение")
        
        N_LINE = min(200, len(self._raw_values))
        for i in range(N_LINE):
            ws_line.cell(row=i+2, column=1, value=i+1)
            ws_line.cell(row=i+2, column=2, value=self._raw_values[i])

        line_chart = LineChart()
        line_chart.title = f"Динамика выпадения (первые {N_LINE} чисел)"
        line_chart.x_axis.title = "Порядковый номер"
        line_chart.y_axis.title = "Значение"
        line_chart.width = 22
        line_chart.height = 12
        line_chart.legend = None  # Убираем легенду
        
        data_line = Reference(ws_line, min_col=2, min_row=1, max_row=N_LINE+1)
        cats_line = Reference(ws_line, min_col=1, min_row=2, max_row=N_LINE+1)
        line_chart.add_data(data_line, titles_from_data=True)
        line_chart.set_categories(cats_line)
        
        # Только точки без линии
        if line_chart.series:
            s = line_chart.series[0]
            s.marker.symbol = "circle"
            s.marker.size = 4
            s.graphicalProperties.line.noFill = True
        
        ws_line.add_chart(line_chart, "D2")

        wb.save(filename)
        self.canvas.itemconfigure(self.status_id, text=f"Сохранено в {filename}")

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
        self._anim_after_id = self.root.after(self.ANIM_INTERVAL_MS, self._anim_loop)

    def _on_close(self):
        self._generating = False
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