import tkinter as tk
from tkinter import font as tkfont
import math
import random

# --- Проверка наличия PIL для генерации настоящего размытия ---
HAS_PIL = False
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
    HAS_PIL = True
except ImportError:
    print("[OK] Pillow не найден — используется упрощённое свечение")


class SmoothVideoPlayerApp:
    # ---------- Палитра ----------
    BG_TOP      = "#0F0B1E"
    BG_BOTTOM   = "#1A1035"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    
    ACCENT      = "#A78BFA"
    ACCENT_DARK = "#7C5CE6"
    ACCENT_LIGHT= "#C4B5FD"
    
    BTN_BASE    = "#2A1F45"
    BTN_TOP     = "#3A2C5E"
    BTN_HOVER   = "#4A3A75"
    BTN_PRESS   = "#1A1230"
    ICON_COLOR  = "#F2EEFF"

    W, H = 700, 600
    CARD_MX, CARD_MT, CARD_MB = 30, 30, 30
    CARD_RADIUS = 24

    def __init__(self, root):
        self.root = root
        self.root.title("Мини-плеер · Плавная анимация")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        self._is_playing = True
        self._progress = 0.0
        self._t = 0
        self._particles = []
        
        # Создаём частицы с плавной физикой
        for _ in range(40):
            self._particles.append({
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "vx": random.uniform(-0.0005, 0.0005),
                "vy": random.uniform(-0.002, -0.001),
                "size": random.uniform(1.5, 3.5),
                "phase": random.uniform(0, math.pi * 2)
            })
        
        # Кэш для пульсирующего шара
        self._ball_cache = {}

        self._init_fonts()

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        self._draw_card()
        self._draw_header()
        self._draw_video_area()
        self._draw_controls()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._anim_loop()

    def _init_fonts(self):
        self.title_font  = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.lbl_font    = tkfont.Font(family="Segoe UI", size=10)
        self.status_font = tkfont.Font(family="Segoe UI", size=10)
        self.time_font   = tkfont.Font(family="Consolas", size=10)

    # ============================================================
    #                КАРТОЧКА И ЗАГОЛОВОК
    # ============================================================
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
        self.canvas.create_text(cx, y0 + 35, text="🎬  МИНИ-ПЛЕЕР",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))
        self.canvas.create_text(cx, y0 + 58, text="Space Ambient · Локальная анимация",
                                font=self.lbl_font, fill=self.TEXT_DIM, tags=("card",))

    # ============================================================
    #                ОБЛАСТЬ ВИДЕО
    # ============================================================
    def _draw_video_area(self):
        x0, y0, x1, _ = self.card
        self.video_x0 = x0 + 30
        self.video_x1 = x1 - 30
        self.video_y0 = y0 + 90
        self.video_y1 = y0 + 340
        
        self._rounded_rect(self.video_x0, self.video_y0, self.video_x1, self.video_y1,
                           radius=12, fill="#050510", outline="#3B2E66", width=2,
                           tags=("card", "video_bg"))

    # ============================================================
    #                УПРАВЛЕНИЕ
    # ============================================================
    def _draw_controls(self):
        x0, y0, x1, _ = self.card
        cx = (x0 + x1) / 2
        self.ctrl_y = self.video_y1 + 65
        
        # --- Кнопка Play/Pause ---
        self.btn_r = 38
        self.btn_cx = cx
        self.btn_cy = self.ctrl_y

        # Тень
        self.canvas.create_oval(
            self.btn_cx - self.btn_r, self.btn_cy - self.btn_r + 4,
            self.btn_cx + self.btn_r, self.btn_cy + self.btn_r + 4,
            fill="#050510", outline="", tags=("card",))

        # Внешнее кольцо
        self.btn_outer_id = self.canvas.create_oval(
            self.btn_cx - self.btn_r, self.btn_cy - self.btn_r,
            self.btn_cx + self.btn_r, self.btn_cy + self.btn_r,
            fill=self.BTN_BASE, outline=self.ACCENT, width=2,
            tags=("card", "btn_outer"))

        # Внутренняя часть (без лишних бликов)
        self.btn_inner_id = self.canvas.create_oval(
            self.btn_cx - self.btn_r + 4, self.btn_cy - self.btn_r + 4,
            self.btn_cx + self.btn_r - 4, self.btn_cy + self.btn_r - 4,
            fill=self.BTN_TOP, outline="", tags=("card", "btn_inner"))

        # Иконки (Play / Pause)
        icon_size = self.btn_r * 0.6
        ix = self.btn_cx + icon_size * 0.15  # лёгкий сдвиг для визуального центра
        iy = self.btn_cy

        self.play_icon_id = self.canvas.create_polygon(
            ix - icon_size * 0.45, iy - icon_size * 0.7,
            ix - icon_size * 0.45, iy + icon_size * 0.7,
            ix + icon_size * 0.75, iy,
            fill=self.ICON_COLOR, outline="", smooth=False,
            tags=("card", "btn_icon"))

        pw = icon_size * 0.25
        ph = icon_size * 1.2
        gap = icon_size * 0.2
        self.pause_icon_ids = [
            self.canvas.create_rectangle(ix - gap - pw, iy - ph/2,
                                          ix - gap, iy + ph/2,
                                          fill=self.ICON_COLOR, outline="", state="hidden",
                                          tags=("card", "btn_icon")),
            self.canvas.create_rectangle(ix + gap, iy - ph/2,
                                          ix + gap + pw, iy + ph/2,
                                          fill=self.ICON_COLOR, outline="", state="hidden",
                                          tags=("card", "btn_icon"))
        ]

        # --- Прогресс-бар ---
        self.pb_y = self.ctrl_y + 60
        self.pb_w = 420
        self.pb_h = 6
        self.pb_x0 = cx - self.pb_w / 2
        self.pb_x1 = cx + self.pb_w / 2
        
        # Фон прогресс-бара
        self._rounded_rect(self.pb_x0, self.pb_y - self.pb_h/2,
                           self.pb_x1, self.pb_y + self.pb_h/2,
                           radius=self.pb_h/2, fill=self._mix_color(self.CARD_BOTTOM, "#000000", 0.6),
                           outline="", tags=("card",))
        
        # Заполнение
        self.pb_fill_id = self._rounded_rect(
            self.pb_x0, self.pb_y - self.pb_h/2,
            self.pb_x0 + 1, self.pb_y + self.pb_h/2,
            radius=self.pb_h/2, fill=self.ACCENT, outline="", tags=("card",)
        )
        
        # Кружок-бегунок
        self.pb_knob_id = self.canvas.create_oval(
            self.pb_x0 - 6, self.pb_y - 6,
            self.pb_x0 + 6, self.pb_y + 6,
            fill=self.TEXT_LIGHT, outline=self.ACCENT, width=2,
            tags=("card",)
        )

        # Время
        self.time_text_id = self.canvas.create_text(
            cx, self.pb_y + 22, text="00:00 / 00:15",
            font=self.time_font, fill=self.TEXT_DIM, tags=("card",)
        )

        # События кнопки
        for tag in ("btn_outer", "btn_inner", "btn_icon"):
            self.canvas.tag_bind(tag, "<Enter>", self._on_enter)
            self.canvas.tag_bind(tag, "<Leave>", self._on_leave)
            self.canvas.tag_bind(tag, "<ButtonPress-1>", self._on_press)
            self.canvas.tag_bind(tag, "<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _):
        self.canvas.config(cursor="hand2")
        self.canvas.itemconfigure(self.btn_inner_id, fill=self.BTN_HOVER)

    def _on_leave(self, _):
        self.canvas.config(cursor="")
        self.canvas.itemconfigure(self.btn_inner_id, fill=self.BTN_TOP)

    def _on_press(self, _):
        self.canvas.itemconfigure(self.btn_outer_id, fill=self.BTN_PRESS)

    def _on_release(self, event):
        self.canvas.itemconfigure(self.btn_outer_id, fill=self.BTN_BASE)
        self._toggle_play()

    def _toggle_play(self):
        self._is_playing = not self._is_playing
        if self._is_playing:
            self.canvas.itemconfigure(self.play_icon_id, state="hidden")
            for pid in self.pause_icon_ids:
                self.canvas.itemconfigure(pid, state="normal")
        else:
            self.canvas.itemconfigure(self.play_icon_id, state="normal")
            for pid in self.pause_icon_ids:
                self.canvas.itemconfigure(pid, state="hidden")

    # ============================================================
    #                ГЕНЕРАЦИЯ ШАРА С РАЗМЫТИЕМ (PIL)
    # ============================================================
    def _generate_glowing_ball(self, size_px):
        """Генерирует шар с настоящим размытым свечением через PIL."""
        if size_px in self._ball_cache:
            return self._ball_cache[size_px]

        pad = int(size_px * 1.5)
        total_size = size_px + pad * 2

        # Слой свечения
        glow = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)
        cx = cy = total_size // 2
        
        draw.ellipse([cx - size_px, cy - size_px, cx + size_px, cy + size_px],
                     fill=(167, 139, 250, 180))
        glow = glow.filter(ImageFilter.GaussianBlur(size_px * 0.4))

        # Резкий шар
        ball = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ball)
        draw.ellipse([cx - size_px, cy - size_px, cx + size_px, cy + size_px],
                     fill=(167, 139, 250, 255))
        ball = ball.filter(ImageFilter.GaussianBlur(1))

        final = Image.alpha_composite(glow, ball)
        photo = ImageTk.PhotoImage(final)
        self._ball_cache[size_px] = photo
        return photo

    # ============================================================
    #                АНИМАЦИЯ
    # ============================================================
    def _anim_loop(self):
        if self._is_playing:
            self._t += 0.03
            self._progress += 0.003
            if self._progress > 1.0:
                self._progress = 0.0
            
            total_sec = 15
            cur_sec = int(self._progress * total_sec)
            self.canvas.itemconfigure(self.time_text_id, 
                                      text=f"00:{cur_sec:02d} / 00:{total_sec:02d}")

        self._draw_video_content()

        if self._is_playing:
            self._update_progress_bar()

        self.root.after(30, self._anim_loop)

    def _draw_video_content(self):
        self.canvas.delete("video_content")

        vx0, vx1 = self.video_x0 + 10, self.video_x1 - 10
        vy0, vy1 = self.video_y0 + 10, self.video_y1 - 10
        vw = vx1 - vx0
        vh = vy1 - vy0
        cx = (vx0 + vx1) / 2
        cy = (vy0 + vy1) / 2

        t = self._t

        # --- Пульсирующий шар ---
        base_r = int(40 + 6 * math.sin(t * 2))
        
        if HAS_PIL:
            ball_photo = self._generate_glowing_ball(base_r)
            self.canvas.create_image(cx, cy, image=ball_photo, 
                                     tags=("card", "video_content", "ball_img"))
            self._current_ball_photo = ball_photo
        else:
            for i in range(5, 0, -1):
                glow_r = base_r + i * 5
                alpha = 0.06 * (6 - i)
                glow_color = self._mix_color("#050510", self.ACCENT, alpha * 3)
                self.canvas.create_oval(cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
                                        fill=glow_color, outline="", tags=("card", "video_content"))
            color_val = int(167 + 30 * math.sin(t * 1.5))
            color = f"#{color_val:02x}8BFA"
            self.canvas.create_oval(cx - base_r, cy - base_r, cx + base_r, cy + base_r,
                                    fill=color, outline="", tags=("card", "video_content"))

        # --- Блик на шаре ---
        self.canvas.create_oval(cx - base_r * 0.5, cy - base_r * 0.6,
                                cx - base_r * 0.1, cy - base_r * 0.2,
                                fill=self._mix_color(self.ACCENT_LIGHT, "#FFFFFF", 0.6),
                                outline="", tags=("card", "video_content"))

        # --- Частицы ---
        if self._is_playing:
            for p in self._particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["x"] += math.sin(t + p["phase"]) * 0.0005

                if p["y"] < 0:
                    p["y"] = 1.0
                    p["x"] = random.uniform(0, 1)

        for p in self._particles:
            px = vx0 + p["x"] * vw
            py = vy0 + p["y"] * vh
            r = p["size"]
            brightness = 0.4 + 0.6 * (1 - p["y"])
            color = self._mix_color("#050510", "#22D3EE", brightness)
            self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                    fill=color, outline="", tags=("card", "video_content"))

    def _update_progress_bar(self):
        fill_x = self.pb_x0 + (self.pb_x1 - self.pb_x0) * self._progress
        
        self.canvas.coords(self.pb_fill_id, *self._pill_points(
            self.pb_x0, self.pb_y - self.pb_h/2,
            fill_x, self.pb_y + self.pb_h/2,
            self.pb_h/2
        ))
        
        self.canvas.coords(self.pb_knob_id,
                           fill_x - 6, self.pb_y - 6,
                           fill_x + 6, self.pb_y + 6)

    # ============================================================
    #                ЗАКРЫТИЕ И УТИЛИТЫ
    # ============================================================
    def _on_close(self):
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
    app = SmoothVideoPlayerApp(root)
    root.mainloop()