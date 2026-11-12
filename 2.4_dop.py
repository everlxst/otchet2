import sys
import platform
import math
import tkinter as tk
from tkinter import font as tkfont
import os
import winreg

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

HAS_AUDIO = False
try:
    from pycaw.pycaw import AudioUtilities
    import comtypes
    HAS_AUDIO = True
except ImportError:
    print("[OK] pycaw не найден — управление звуком отключено")

HAS_NOTIFY = False
try:
    from plyer import notification
    HAS_NOTIFY = True
except ImportError:
    print("[OK] plyer не найден — уведомления будут только в статус-баре")


class RealControlsApp:
    # ---------- Палитра ----------
    BG_TOP      = "#0F0B1E"
    BG_BOTTOM   = "#1A1035"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    
    ACCENT      = "#A78BFA"
    ACCENT_HOV  = "#C4B5FD"
    ACCENT_PRS  = "#7C5CE6"
    
    CB_ON       = "#22D3EE"
    CB_OFF      = "#3B2E66"
    
    RB_ON       = "#22C55E"
    RB_OFF      = "#3B2E66"

    W, H = 700, 600
    CARD_MX, CARD_MT, CARD_MB = 30, 30, 30
    CARD_RADIUS = 24

    def __init__(self, root):
        self.root = root
        self.root.title("Рабочие настройки Windows")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        # --- Инициализация аудио ---
        self.volume_interface = None
        music_state = True
        if HAS_AUDIO:
            try:
                comtypes.CoInitialize()
                self.volume_interface = AudioUtilities.GetSpeakers().EndpointVolume
                is_muted = self.volume_interface.GetMute()
                music_state = not is_muted
            except Exception:
                music_state = True

        # --- Состояние ---
        self._anim_after_id = None
        self._running = True
        
        auto_state = self._is_in_autostart()
        
        # Чекбоксы
        self.checkboxes = {
            "music": {"state": music_state, "target": 1.0 if music_state else 0.0, "cur": 1.0 if music_state else 0.0, "rect": None, "check": None, "label": "Включить музыку"},
            "notify": {"state": False, "target": 0.0, "cur": 0.0, "rect": None, "check": None, "label": "Уведомления"},
            "auto": {"state": auto_state, "target": 1.0 if auto_state else 0.0, "cur": 1.0 if auto_state else 0.0, "rect": None, "check": None, "label": "Автозапуск"},
        }
        
        # Радиокнопки
        self.radio_selected = "medium"
        self.radios = {
            "small": {"rect": None, "dot": None, "label": "Маленький шрифт"},
            "medium": {"rect": None, "dot": None, "label": "Средний шрифт"},
            "large": {"rect": None, "dot": None, "label": "Большой шрифт"},
        }

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
        self._draw_checkboxes()
        self._draw_radios()
        self._draw_status_bar()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._anim_loop()

    def _init_fonts(self):
        self.title_font  = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self.lbl_font    = tkfont.Font(family="Segoe UI", size=14)
        self.sub_font    = tkfont.Font(family="Segoe UI", size=10)
        self.status_font = tkfont.Font(family="Segoe UI", size=10)

    def _is_in_autostart(self):
        app_name = "MyRealControlsApp"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, app_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def _set_autostart(self, enabled):
        app_name = "MyRealControlsApp"
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                script_path = os.path.abspath(sys.argv[0])
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{sys.executable}" "{script_path}"')
                msg = "Автозапуск ВКЛЮЧЁН"
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    msg = "Автозапуск ВЫКЛЮЧЕН"
                except FileNotFoundError:
                    msg = "Автозапуск уже был выключен"
            winreg.CloseKey(key)
            self.canvas.itemconfigure(self.status_id, text=msg)
        except Exception as e:
            print(f"[ERR] Ошибка реестра: {e}")
            self.canvas.itemconfigure(self.status_id, text="Ошибка автозапуска")

    def _make_abstract_background(self, w, h):
        img = Image.new("RGB", (w, h), (5, 5, 15))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            r = int(5 + (18 - 5) * t)
            g = int(5 + (10 - 5) * t)
            b = int(15 + (35 - 15) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        for cx, cy, rad, color in [(100, 100, 250, (120, 40, 200)),
                                   (w - 100, h - 100, 250, (30, 180, 220))]:
            layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=color + (60,))
            layer = layer.filter(ImageFilter.GaussianBlur(80))
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
        self.canvas.create_text(cx, y0 + 50, text="⚙️  СИСТЕМНЫЕ НАСТРОЙКИ",
                                font=self.title_font, fill=self.TEXT_LIGHT, tags=("card",))
        self.canvas.create_text(cx, y0 + 75, text="Реально работающие чекбоксы Windows",
                                font=self.sub_font, fill=self.TEXT_DIM, tags=("card",))

    def _draw_checkboxes(self):
        x0, y0, x1, _ = self.card
        start_x = x0 + 80
        start_y = y0 + 130
        gap = 60
        
        for i, (key, data) in enumerate(self.checkboxes.items()):
            y = start_y + i * gap
            bx0 = start_x
            bx1 = start_x + 28
            by0 = y - 14
            by1 = y + 14
            
            rect_id = self._rounded_rect(bx0, by0, bx1, by1, radius=6,
                                          fill=self.CB_OFF, outline=self.ACCENT, width=2,
                                          tags=("card", f"cb_{key}"))
            
            cx = (bx0 + bx1) / 2
            cy = (by0 + by1) / 2
            check_id = self.canvas.create_line(
                cx - 6, cy,
                cx - 2, cy + 4,
                cx + 7, cy - 5,
                fill=self.CB_ON, width=3, capstyle="round", joinstyle="round",
                state="normal" if data["state"] else "hidden",
                tags=("card", f"cb_{key}_check")
            )
            
            self.canvas.create_text(start_x + 40, y, text=data["label"],
                                    font=self.lbl_font, fill=self.TEXT_LIGHT, anchor="w",
                                    tags=("card", f"cb_{key}_label"))
            
            data["rect"] = rect_id
            data["check"] = check_id
            
            self.canvas.tag_bind(f"cb_{key}", "<ButtonRelease-1>", lambda e, k=key: self._toggle_checkbox(k))
            self.canvas.tag_bind(f"cb_{key}_label", "<ButtonRelease-1>", lambda e, k=key: self._toggle_checkbox(k))
            self.canvas.tag_bind(f"cb_{key}", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(f"cb_{key}_label", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(f"cb_{key}", "<Leave>", lambda e: self.canvas.config(cursor=""))
            self.canvas.tag_bind(f"cb_{key}_label", "<Leave>", lambda e: self.canvas.config(cursor=""))

    def _toggle_checkbox(self, key):
        data = self.checkboxes[key]
        data["state"] = not data["state"]
        data["target"] = 1.0 if data["state"] else 0.0
        
        state = "normal" if data["state"] else "hidden"
        self.canvas.itemconfigure(data["check"], state=state)
        
        if key == "music":
            if self.volume_interface:
                try:
                    self.volume_interface.SetMute(not data["state"], None)
                    self.canvas.itemconfigure(self.status_id, 
                        text=f"Музыка {'ВКЛ' if data['state'] else 'ВЫКЛ'}")
                except Exception as e:
                    print(f"[ERR] Ошибка звука: {e}")
            else:
                self.canvas.itemconfigure(self.status_id, text="Ошибка: pycaw не установлен")
        
        elif key == "auto":
            self._set_autostart(data["state"])
            
        elif key == "notify":
            if data["state"]:
                if HAS_NOTIFY:
                    try:
                        notification.notify(title="Мои настройки", message="Уведомления включены!", timeout=3)
                        self.canvas.itemconfigure(self.status_id, text="Уведомление отправлено")
                    except Exception:
                        self.canvas.itemconfigure(self.status_id, text="Ошибка уведомления")
                else:
                    self.canvas.itemconfigure(self.status_id, text="Уведомления ВКЛ (plyer не установлен)")

    def _draw_radios(self):
        x0, y0, x1, _ = self.card
        start_x = x0 + 80
        start_y = y0 + 340
        gap = 50
        
        for i, (key, data) in enumerate(self.radios.items()):
            y = start_y + i * gap
            bx0 = start_x
            bx1 = start_x + 28
            by0 = y - 14
            by1 = y + 14
            
            rect_id = self.canvas.create_oval(bx0, by0, bx1, by1,
                                              fill=self.RB_OFF, outline=self.ACCENT, width=2,
                                              tags=("card", f"rb_{key}"))
            
            cx = (bx0 + bx1) / 2
            cy = (by0 + by1) / 2
            r = 6
            dot_id = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                              fill=self.RB_ON, outline="",
                                              state="normal" if key == self.radio_selected else "hidden",
                                              tags=("card", f"rb_{key}_dot"))
            
            self.canvas.create_text(start_x + 40, y, text=data["label"],
                                    font=self.lbl_font, fill=self.TEXT_LIGHT, anchor="w",
                                    tags=("card", f"rb_{key}_label"))
            
            data["rect"] = rect_id
            data["dot"] = dot_id
            
            self.canvas.tag_bind(f"rb_{key}", "<ButtonRelease-1>", lambda e, k=key: self._select_radio(k))
            self.canvas.tag_bind(f"rb_{key}_label", "<ButtonRelease-1>", lambda e, k=key: self._select_radio(k))
            self.canvas.tag_bind(f"rb_{key}", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(f"rb_{key}_label", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(f"rb_{key}", "<Leave>", lambda e: self.canvas.config(cursor=""))
            self.canvas.tag_bind(f"rb_{key}_label", "<Leave>", lambda e: self.canvas.config(cursor=""))

    def _select_radio(self, key):
        self.radio_selected = key
        for k, data in self.radios.items():
            state = "normal" if k == key else "hidden"
            self.canvas.itemconfigure(data["dot"], state=state)
            
        sizes = {"small": 10, "medium": 14, "large": 18}
        new_size = sizes.get(key, 14)
        
        self.lbl_font.configure(size=new_size)
        self.sub_font.configure(size=max(8, new_size - 4))
        
        self.canvas.itemconfigure(self.status_id, 
                                  text=f"Шрифт изменён на '{self.radios[key]['label']}'")

    def _draw_status_bar(self):
        self.canvas.create_rectangle(0, self.H - 34, self.W, self.H,
                                     fill=self._mix_color(self.BG_TOP, "#000000", 0.2),
                                     outline="", tags=("status_bg",))
        self.status_id = self.canvas.create_text(
            22, self.H - 17, text="Готово",
            anchor="w", font=self.status_font, fill=self.TEXT_DIM, tags=("status",))
        self.canvas.create_oval(self.W - 28, self.H - 21, self.W - 20, self.H - 13,
                                fill=self.ACCENT, outline="", tags=("status",))

    def _anim_loop(self):
        if not self._running: return
        for key, data in self.checkboxes.items():
            d = data["target"] - data["cur"]
            if abs(d) > 0.01:
                data["cur"] += d * 0.2
            else:
                data["cur"] = data["target"]
            current_color = self._mix_color(self.CB_OFF, self.CB_ON, data["cur"])
            self.canvas.itemconfigure(data["rect"], fill=current_color)
        self._anim_after_id = self.root.after(16, self._anim_loop)

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
        app = RealControlsApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[FATAL] Не удалось запустить приложение: {e}")