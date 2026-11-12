import tkinter as tk
from tkinter import font as tkfont
import math

class ToggleSwitchApp:
    # ---------- Палитра ----------
    BG_TOP      = "#0F0B1E"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    
    # Цвета тумблера
    SWITCH_BODY   = "#3B3B4A"
    SWITCH_EDGE   = "#5A5A70"
    SWITCH_HOLE   = "#1A1A25"
    LEVER_BASE    = "#8A8A9E"
    LEVER_TOP     = "#D4D4E0"
    
    ON_COLOR      = "#22C55E"
    OFF_COLOR     = "#EF4444"
    
    W, H = 400, 500
    CARD_MX, CARD_MT, CARD_MB = 30, 30, 30
    CARD_RADIUS = 24

    def __init__(self, root):
        self.root = root
        self.root.title("Анимированный тумблер")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Состояние ---
        self._is_on = False
        self._lever_pos = 0.0        # 0.0 = OFF (вниз), 1.0 = ON (вверх)
        self._target_pos = 0.0
        self._anim_after_id = None
        self._running = True

        self._init_fonts()

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        self._draw_card()
        self._draw_header()
        self._draw_switch()
        self._draw_status()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._anim_loop()

    def _init_fonts(self):
        self.title_font  = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.lbl_font    = tkfont.Font(family="Segoe UI", size=10)
        self.status_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")

    # ============================================================
    #                КАРТОЧКА
    # ============================================================
    def _draw_card(self):
        x0, y0 = self.CARD_MX, self.CARD_MT
        x1, y1 = self.W - self.CARD_MX, self.H - self.CARD_MB
        self.card = (x0, y0, x1, y1)
        self._rounded_rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3, radius=self.CARD_RADIUS + 3,
                           fill="#4B3B7A", outline="", tags=("card_bg",))
        self._rounded_rect(x0, y0, x1, y1, radius=self.CARD_RADIUS,
                           fill=self._mix_color(self.CARD_BOTTOM, self.CARD_TOP, 0.4),
                           outline="#5B4A8A", width=1, tags=("card_inner",))
        self.canvas.tag_raise("card_inner")

    def _draw_header(self):
        x0, y0, x1, _ = self.card
        cx = (x0 + x1) / 2
        self.canvas.create_text(cx, y0 + 40, text="⚙️  ТУМБЛЕР",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))
        self.canvas.create_text(cx, y0 + 65, text="Нажмите, чтобы переключить",
                                font=self.lbl_font, fill=self.TEXT_DIM, tags=("card",))

    # ============================================================
    #                ТУМБЛЕР
    # ============================================================
    def _draw_switch(self):
        x0, y0, x1, y1 = self.card
        self.sw_cx = (x0 + x1) / 2
        self.sw_cy = y0 + 200
        
        # Размеры
        self.body_w = 140
        self.body_h = 220
        self.body_r = 20
        
        # 1. Корпус (тень + сам корпус)
        self._rounded_rect(self.sw_cx - self.body_w/2 + 4, self.sw_cy - self.body_h/2 + 4,
                           self.sw_cx + self.body_w/2 + 4, self.sw_cy + self.body_h/2 + 4,
                           radius=self.body_r, fill="#050510", outline="", tags=("card",))
        
        self._rounded_rect(self.sw_cx - self.body_w/2, self.sw_cy - self.body_h/2,
                           self.sw_cx + self.body_w/2, self.sw_cy + self.body_h/2,
                           radius=self.body_r, fill=self.SWITCH_BODY, outline=self.SWITCH_EDGE, width=2,
                           tags=("card",))

        # 2. Верхняя часть (ON)
        self.on_area_id = self._rounded_rect(
            self.sw_cx - self.body_w/2 + 10, self.sw_cy - self.body_h/2 + 10,
            self.sw_cx + self.body_w/2 - 10, self.sw_cy - 30,
            radius=12, fill=self.OFF_COLOR, outline="", tags=("card", "on_area")
        )
        self.on_text_id = self.canvas.create_text(
            self.sw_cx, self.sw_cy - self.body_h/2 + 30,
            text="ON", font=self.status_font, fill="#FFFFFF", tags=("card", "on_text")
        )

        # 3. Нижняя часть (OFF)
        self.off_area_id = self._rounded_rect(
            self.sw_cx - self.body_w/2 + 10, self.sw_cy + 30,
            self.sw_cx + self.body_w/2 - 10, self.sw_cy + self.body_h/2 - 10,
            radius=12, fill=self.OFF_COLOR, outline="", tags=("card", "off_area")
        )
        self.off_text_id = self.canvas.create_text(
            self.sw_cx, self.sw_cy + self.body_h/2 - 30,
            text="OFF", font=self.status_font, fill="#FFFFFF", tags=("card", "off_text")
        )

        # 4. Отверстие (окно, по которому ездит рычажок) — сужаем его
        self.hole_x0 = self.sw_cx - 20
        self.hole_x1 = self.sw_cx + 20
        self.hole_y0 = self.sw_cy - 50
        self.hole_y1 = self.sw_cy + 50
        self._rounded_rect(self.hole_x0, self.hole_y0, self.hole_x1, self.hole_y1,
                           radius=10, fill=self.SWITCH_HOLE, outline="", tags=("card",))

        # 5. Рычажок (создаём элементы, но пока не позиционируем)
        # Основание (металлическая втулка)
        self.lever_base_id = self.canvas.create_oval(0, 0, 0, 0, fill=self.LEVER_BASE, outline="", tags=("card",))
        # Верхушка (шарик)
        self.lever_top_id = self.canvas.create_oval(0, 0, 0, 0, fill=self.LEVER_TOP, outline="", tags=("card",))
        # Блик
        self.lever_highlight_id = self.canvas.create_oval(0, 0, 0, 0, fill="#FFFFFF", outline="", tags=("card",))

        # Клик
        self.canvas.tag_bind("card", "<ButtonPress-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)

    def _on_motion(self, event):
        if (self.sw_cx - self.body_w/2 <= event.x <= self.sw_cx + self.body_w/2 and
            self.sw_cy - self.body_h/2 <= event.y <= self.sw_cy + self.body_h/2):
            self.canvas.config(cursor="hand2")
        else:
            self.canvas.config(cursor="")

    def _on_click(self, event):
        if (self.sw_cx - self.body_w/2 <= event.x <= self.sw_cx + self.body_w/2 and
            self.sw_cy - self.body_h/2 <= event.y <= self.sw_cy + self.body_h/2):
            self._toggle()

    def _toggle(self):
        self._is_on = not self._is_on
        self._target_pos = 1.0 if self._is_on else 0.0
        self._update_colors()

    def _update_colors(self):
        # Подсветка ON
        if self._is_on:
            on_fill = self.ON_COLOR
            on_text_fill = "#FFFFFF"
        else:
            on_fill = self._mix_color(self.SWITCH_BODY, self.ON_COLOR, 0.2)
            on_text_fill = self._mix_color("#FFFFFF", self.SWITCH_BODY, 0.5)
        self.canvas.itemconfigure(self.on_area_id, fill=on_fill)
        self.canvas.itemconfigure(self.on_text_id, fill=on_text_fill)

        # Подсветка OFF
        if not self._is_on:
            off_fill = self.OFF_COLOR
            off_text_fill = "#FFFFFF"
        else:
            off_fill = self._mix_color(self.SWITCH_BODY, self.OFF_COLOR, 0.2)
            off_text_fill = self._mix_color("#FFFFFF", self.SWITCH_BODY, 0.5)
        self.canvas.itemconfigure(self.off_area_id, fill=off_fill)
        self.canvas.itemconfigure(self.off_text_id, fill=off_text_fill)

    # ============================================================
    #                СТАТУС
    # ============================================================
    def _draw_status(self):
        x0, y0, x1, y1 = self.card
        cx = (x0 + x1) / 2
        self.status_id = self.canvas.create_text(
            cx, y1 - 60,
            text="ВЫКЛЮЧЕНО",
            font=self.status_font, fill=self.TEXT_DIM,
            tags=("card",)
        )

    # ============================================================
    #                АНИМАЦИЯ
    # ============================================================
    def _anim_loop(self):
        if not self._running: return

        # Плавное движение рычажка
        d = self._target_pos - self._lever_pos
        if abs(d) > 0.01:
            self._lever_pos += d * 0.2
        else:
            self._lever_pos = self._target_pos

        if abs(self._lever_pos - self._target_pos) < 0.01:
            new_text = "ВКЛЮЧЕНО" if self._is_on else "ВЫКЛЮЧЕНО"
            new_color = self.ON_COLOR if self._is_on else self.TEXT_DIM
            self.canvas.itemconfigure(self.status_id, text=new_text, fill=new_color)

        self._update_lever()

        self._anim_after_id = self.root.after(16, self._anim_loop)

    def _update_lever(self):
        cx = self.sw_cx
        # Позиция центра рычажка: от нижней части отверстия к верхней
        # Ограничиваем движение, чтобы он не вылезал на надписи
        top_y = self.hole_y0 + 15
        bottom_y = self.hole_y1 - 15
        lever_y = bottom_y - (bottom_y - top_y) * self._lever_pos
        
        # Рычажок в виде "таблетки" (сплюснутый эллипс)
        # Размеры подобраны так, чтобы он был шире, чем высокий
        base_w = 30
        base_h = 20
        
        # Основание (втулка)
        self.canvas.coords(self.lever_base_id,
                           cx - base_w/2, lever_y - base_h/2,
                           cx + base_w/2, lever_y + base_h/2)
        self.canvas.itemconfigure(self.lever_base_id, fill=self.LEVER_BASE)

        # Верхушка (шарик) — чуть меньше
        top_r = 14
        self.canvas.coords(self.lever_top_id,
                           cx - top_r, lever_y - top_r - 2,
                           cx + top_r, lever_y + top_r - 2)
        self.canvas.itemconfigure(self.lever_top_id, fill=self.LEVER_TOP)

        # Блик на верхушке (смещён влево-вверх)
        hl_r = 5
        self.canvas.coords(self.lever_highlight_id,
                           cx - top_r*0.4 - hl_r, lever_y - top_r*0.4 - hl_r - 2,
                           cx - top_r*0.4 + hl_r, lever_y - top_r*0.4 + hl_r - 2)
        self.canvas.itemconfigure(self.lever_highlight_id, fill="#FFFFFF")

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
    root = tk.Tk()
    app = ToggleSwitchApp(root)
    root.mainloop()