import tkinter as tk
from tkinter import font as tkfont, messagebox, simpledialog
import random
import copy

class ChessGame:
    # ---------- Палитра ----------
    COLOR_LIGHT = "#F0D9B5"
    COLOR_DARK  = "#B58863"
    BG_TOP      = "#0F0B1E"
    CARD_TOP    = "#221A3D"
    CARD_BOTTOM = "#15102A"
    TEXT_LIGHT  = "#F2EEFF"
    TEXT_DIM    = "#C8BEE0"
    ACCENT      = "#A78BFA"
    ACCENT_HOV  = "#C4B5FD"  # <-- Добавили эту строку
    SELECT_COLOR = "#F6F669"
    MOVE_COLOR  = "#B5E61D"
    CHECK_COLOR = "#EF4444"

    CELL_SIZE = 70
    BOARD_SIZE = 8 * CELL_SIZE
    W = BOARD_SIZE + 80
    H = BOARD_SIZE + 160

    def __init__(self, root):
        self.root = root
        self.root.title("Шахматы · Полные правила + ИИ")
        self.root.geometry(f"{self.W}x{self.H}")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG_TOP)
        self._center_window(self.W, self.H)

        self._init_fonts()

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                highlightthickness=0, bd=0, bg=self.BG_TOP)
        self.canvas.pack(fill="both", expand=True)

        # --- Меню ---
        self._show_menu()

    def _init_fonts(self):
        self.piece_font = tkfont.Font(family="Segoe UI Symbol", size=36)
        self.status_font = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self.menu_title_font = tkfont.Font(family="Segoe UI", size=28, weight="bold")
        self.menu_btn_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")

    # ============================================================
    #                МЕНЮ
    # ============================================================
    def _show_menu(self):
        self.canvas.delete("all")
        self._draw_background()

        cx = self.W / 2
        cy = self.H / 2

        # Заголовок
        self.canvas.create_text(cx, cy - 150, text="♟ ШАХМАТЫ",
                                font=self.menu_title_font, fill=self.TEXT_LIGHT)
        self.canvas.create_text(cx, cy - 100, text="Выберите режим игры",
                                font=self.status_font, fill=self.TEXT_DIM)

        # Кнопки
        self._draw_menu_button(cx, cy - 20, "👥 ИГРАТЬ С ДРУГОМ", self._start_pvp)
        self._draw_menu_button(cx, cy + 70, "🤖 ИГРАТЬ С ИИ (Сложно)", self._start_pve)
        self._draw_menu_button(cx, cy + 160, "🎲 ИГРАТЬ С ИИ (Случайно)", self._start_pve_random)

    def _draw_menu_button(self, cx, cy, text, command):
        bw, bh = 320, 60
        x0, y0 = cx - bw/2, cy - bh/2
        x1, y1 = cx + bw/2, cy + bh/2

        tag = f"btn_{id(command)}"
        
        # Тень
        self.canvas.create_rectangle(x0 + 4, y0 + 4, x1 + 4, y1 + 4,
                                     fill="#000000", outline="", tags=("menu_btn",))
        
        # Кнопка
        btn_id = self.canvas.create_rectangle(x0, y0, x1, y1,
                                              fill=self.ACCENT, outline=self.ACCENT_HOV, width=2,
                                              tags=("menu_btn", tag))
        
        self.canvas.create_text(cx, cy, text=text,
                                font=self.menu_btn_font, fill="#0F0B1E",
                                tags=("menu_btn", tag))

        # Привязка
        self.canvas.tag_bind(tag, "<ButtonRelease-1>", lambda e: command())
        self.canvas.tag_bind(tag, "<Enter>", 
                             lambda e: self.canvas.itemconfigure(btn_id, fill=self.ACCENT_HOV))
        self.canvas.tag_bind(tag, "<Leave>", 
                             lambda e: self.canvas.itemconfigure(btn_id, fill=self.ACCENT))

    def _start_pvp(self):
        self._start_game(mode="pvp")

    def _start_pve(self):
        self._start_game(mode="pve_minimax")

    def _start_pve_random(self):
        self._start_game(mode="pve_random")

    # ============================================================
    #                СТАРТ ИГРЫ
    # ============================================================
    def _start_game(self, mode):
        self.mode = mode
        self.canvas.delete("all")

        self.board = [['' for _ in range(8)] for _ in range(8)]
        self.turn = 'w'
        self.selected_square = None
        self.possible_moves = []
        self.castling = {'w': {'K': True, 'Q': True}, 'b': {'K': True, 'Q': True}}
        self.en_passant_target = None
        self.game_over = False
        
        self._init_board()

        self._draw_background()
        self._draw_board()
        self._draw_pieces()
        self._draw_status_bar()
        self._update_status()

        self.canvas.bind("<Button-1>", self._on_click)

    def _init_board(self):
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['', '', '', '', '', '', '', ''],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],
        ]

    # ============================================================
    #                ОТРИСОВКА
    # ============================================================
    def _draw_background(self):
        for y in range(self.H):
            t = y / self.H
            r = int(15 + (26 - 15) * t)
            g = int(11 + (16 - 11) * t)
            b = int(30 + (53 - 30) * t)
            self.canvas.create_line(0, y, self.W, y, fill=f"#{r:02x}{g:02x}{b:02x}", tags="bg")

    def _draw_board(self):
        self.board_x0 = 40
        self.board_y0 = 40
        for row in range(8):
            for col in range(8):
                x1 = self.board_x0 + col * self.CELL_SIZE
                y1 = self.board_y0 + row * self.CELL_SIZE
                x2 = x1 + self.CELL_SIZE
                y2 = y1 + self.CELL_SIZE
                color = self.COLOR_LIGHT if (row + col) % 2 == 0 else self.COLOR_DARK
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="", tags="board")

        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for i in range(8):
            x = self.board_x0 + i * self.CELL_SIZE + self.CELL_SIZE/2
            y = self.board_y0 + self.BOARD_SIZE + 15
            self.canvas.create_text(x, y, text=letters[i], fill=self.TEXT_DIM, font=("Segoe UI", 10), tags="coords")
            x = self.board_x0 - 15
            y = self.board_y0 + i * self.CELL_SIZE + self.CELL_SIZE/2
            self.canvas.create_text(x, y, text=str(8 - i), fill=self.TEXT_DIM, font=("Segoe UI", 10), tags="coords")

    def _draw_pieces(self):
        self.canvas.delete("piece")
        unicode_map = {
            'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
            'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
        }
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    x = self.board_x0 + col * self.CELL_SIZE + self.CELL_SIZE/2
                    y = self.board_y0 + row * self.CELL_SIZE + self.CELL_SIZE/2
                    fill_color = "#FFFFFF" if piece.isupper() else "#000000"
                    self.canvas.create_text(x + 2, y + 2, text=unicode_map[piece], font=self.piece_font, 
                                            fill="#444444", tags="piece")
                    self.canvas.create_text(x, y, text=unicode_map[piece], font=self.piece_font, 
                                            fill=fill_color, tags="piece")

    def _draw_status_bar(self):
        panel_y = self.H - 50
        self.canvas.create_rectangle(0, panel_y, self.W, self.H, 
                                     fill=self.CARD_BOTTOM, outline="", tags="status_bg")
        self.status_id = self.canvas.create_text(
            self.W / 2, panel_y + 25, anchor="center", text="",
            font=self.status_font, fill=self.TEXT_LIGHT, tags="status_text"
        )

    def _update_status(self):
        if self.game_over: return
        turn_str = "Ход белых" if self.turn == 'w' else "Ход чёрных"
        if self._is_in_check(self.turn):
            self.canvas.itemconfigure(self.status_id, text=f"{turn_str}  (ШАХ!)", fill=self.CHECK_COLOR)
        else:
            self.canvas.itemconfigure(self.status_id, text=turn_str, fill=self.TEXT_LIGHT)

    # ============================================================
    #                КЛИКИ
    # ============================================================
    def _on_click(self, event):
        if self.game_over: return
        if self.mode != "pvp" and self.turn == 'b': return

        if not (self.board_x0 <= event.x <= self.board_x0 + self.BOARD_SIZE and
                self.board_y0 <= event.y <= self.board_y0 + self.BOARD_SIZE):
            return

        col = int((event.x - self.board_x0) // self.CELL_SIZE)
        row = int((event.y - self.board_y0) // self.CELL_SIZE)
        
        if not (0 <= row < 8 and 0 <= col < 8):
            return

        piece = self.board[row][col]
        
        if self.selected_square:
            old_row, old_col = self.selected_square
            if (row, col) == (old_row, old_col):
                self._clear_selection()
                return
            if (row, col) in self.possible_moves:
                self._make_move(old_row, old_col, row, col)
                return
            if piece and ((self.turn == 'w' and piece.isupper()) or 
                          (self.turn == 'b' and piece.islower())):
                self._clear_selection()
                self._select_square(row, col)
                return
            self._clear_selection()
            return
        
        if piece and ((self.turn == 'w' and piece.isupper()) or 
                      (self.turn == 'b' and piece.islower())):
            self._select_square(row, col)

    def _select_square(self, row, col):
        self.selected_square = (row, col)
        self.possible_moves = self._get_legal_moves(row, col)
        
        self.canvas.delete("highlight")
        x1 = self.board_x0 + col * self.CELL_SIZE
        y1 = self.board_y0 + row * self.CELL_SIZE
        self.canvas.create_rectangle(x1, y1, x1 + self.CELL_SIZE, y1 + self.CELL_SIZE, 
                                     outline=self.SELECT_COLOR, width=4, tags="highlight")
        
        for (r, c) in self.possible_moves:
            cx = self.board_x0 + c * self.CELL_SIZE + self.CELL_SIZE/2
            cy = self.board_y0 + r * self.CELL_SIZE + self.CELL_SIZE/2
            if self.board[r][c]:
                self.canvas.create_oval(cx - 25, cy - 25, cx + 25, cy + 25, 
                                         outline=self.MOVE_COLOR, width=4, tags="highlight")
            else:
                self.canvas.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, 
                                         fill=self.MOVE_COLOR, outline="", tags="highlight")
        self.canvas.tag_raise("piece")

    def _clear_selection(self):
        self.selected_square = None
        self.possible_moves = []
        self.canvas.delete("highlight")

    # ============================================================
    #                ХОДЫ
    # ============================================================
    def _make_move(self, from_row, from_col, to_row, to_col, is_ai=False):
        piece = self.board[from_row][from_col]
        target = self.board[to_row][to_col]
        
        # Специальные ходы
        if piece.lower() == 'k' and abs(to_col - from_col) == 2:
            if to_col > from_col:
                self.board[to_row][to_col - 1] = self.board[to_row][7]
                self.board[to_row][7] = ''
            else:
                self.board[to_row][to_col + 1] = self.board[to_row][0]
                self.board[to_row][0] = ''
        
        if piece.lower() == 'p' and self.en_passant_target == (to_row, to_col):
            self.board[from_row][to_col] = ''
        
        # Превращение
        if piece.lower() == 'p' and (to_row == 0 or to_row == 7):
            if is_ai:
                self.board[to_row][to_col] = 'q' if piece.islower() else 'Q'
            else:
                choice = simpledialog.askstring("Превращение", 
                    "Выберите фигуру:\nQ - Ферзь, R - Ладья, B - Слон, N - Конь",
                    initialvalue="Q")
                if choice and choice.upper() in ['Q', 'R', 'B', 'N']:
                    self.board[to_row][to_col] = choice.upper() if piece.isupper() else choice.lower()
                else:
                    self.board[to_row][to_col] = 'Q' if piece.isupper() else 'q'
        else:
            self.board[to_row][to_col] = piece
        
        self.board[from_row][from_col] = ''
        
        # Рокировка (права)
        if piece.lower() == 'k':
            self.castling[self.turn]['K'] = False
            self.castling[self.turn]['Q'] = False
        if piece.lower() == 'r':
            if from_col == 0:
                self.castling[self.turn]['Q'] = False
            elif from_col == 7:
                self.castling[self.turn]['K'] = False
        if target and target.lower() == 'r':
            if to_col == 0:
                self.castling['b' if self.turn == 'w' else 'w']['Q'] = False
            elif to_col == 7:
                self.castling['b' if self.turn == 'w' else 'w']['K'] = False
        
        # En passant
        self.en_passant_target = None
        if piece.lower() == 'p' and abs(to_row - from_row) == 2:
            self.en_passant_target = ((from_row + to_row) // 2, from_col)
        
        self.turn = 'b' if self.turn == 'w' else 'w'
        self._clear_selection()
        self._draw_pieces()
        self._update_status()
        
        if self._check_game_over():
            return
        
        # Ход ИИ
        if not is_ai and self.mode != "pvp" and self.turn == 'b':
            self.root.after(300, self._ai_move)

    # ============================================================
    #                ИИ
    # ============================================================
    def _ai_move(self):
        if self.game_over: return
        if self.mode == "pve_random":
            self._ai_random_move()
        else:
            self._ai_minimax_move()

    def _ai_random_move(self):
        moves = self._get_all_moves('b')
        if not moves: return
        from_pos, to_pos = random.choice(moves)
        self._make_move(from_pos[0], from_pos[1], to_pos[0], to_pos[1], is_ai=True)

    def _ai_minimax_move(self):
        moves = self._get_all_moves('b')
        if not moves: return
        
        best_move = None
        best_score = -9999
        
        for from_pos, to_pos in moves:
            saved_board = copy.deepcopy(self.board)
            saved_castling = copy.deepcopy(self.castling)
            saved_en_passant = self.en_passant_target
            
            self._make_silent_move(from_pos[0], from_pos[1], to_pos[0], to_pos[1])
            score = -self._evaluate_board()
            
            self.board = saved_board
            self.castling = saved_castling
            self.en_passant_target = saved_en_passant
            self.turn = 'b'
            
            if score > best_score:
                best_score = score
                best_move = (from_pos, to_pos)
        
        if best_move:
            self._make_move(best_move[0][0], best_move[0][1], 
                            best_move[1][0], best_move[1][1], is_ai=True)

    def _make_silent_move(self, from_row, from_col, to_row, to_col):
        piece = self.board[from_row][from_col]
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = ''
        self.turn = 'w' if self.turn == 'b' else 'b'

    def _evaluate_board(self):
        values = {'p': 100, 'n': 300, 'b': 300, 'r': 500, 'q': 900, 'k': 10000}
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p:
                    val = values[p.lower()]
                    if p.isupper():
                        score += val
                    else:
                        score -= val
        return score

    def _get_all_moves(self, color):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and ((color == 'w' and p.isupper()) or (color == 'b' and p.islower())):
                    for move in self._get_legal_moves(r, c):
                        moves.append(((r, c), move))
        return moves

    # ============================================================
    #                ПРАВИЛА
    # ============================================================
    def _get_legal_moves(self, row, col):
        piece = self.board[row][col]
        if not piece: return []
        is_white = piece.isupper()
        if (is_white and self.turn != 'w') or (not is_white and self.turn != 'b'):
            return []
        pseudo = self._get_pseudo_moves(row, col)
        legal = []
        for (r, c) in pseudo:
            saved_target = self.board[r][c]
            self.board[r][c] = piece
            self.board[row][col] = ''
            if not self._is_in_check(self.turn):
                legal.append((r, c))
            self.board[row][col] = piece
            self.board[r][c] = saved_target
        return legal

    def _get_pseudo_moves(self, row, col):
        piece = self.board[row][col]
        moves = []
        is_white = piece.isupper()
        p = piece.lower()
        
        def add_move(r, c):
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if not target:
                    moves.append((r, c))
                    return True
                elif target.isupper() != is_white:
                    moves.append((r, c))
                    return False
                return False
            return False
        
        if p == 'p':
            direction = -1 if is_white else 1
            start_row = 6 if is_white else 1
            r = row + direction
            if 0 <= r < 8 and not self.board[r][col]:
                moves.append((r, col))
                if row == start_row and not self.board[r + direction][col]:
                    moves.append((r + direction, col))
            for dc in [-1, 1]:
                r = row + direction
                c = col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    target = self.board[r][c]
                    if target and target.isupper() != is_white:
                        moves.append((r, c))
                    elif self.en_passant_target == (r, c):
                        moves.append((r, c))
        elif p == 'n':
            for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), 
                           (1, -2), (1, 2), (2, -1), (2, 1)]:
                add_move(row + dr, col + dc)
        elif p == 'b':
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    if not add_move(r, c): break
                    r += dr; c += dc
        elif p == 'r':
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    if not add_move(r, c): break
                    r += dr; c += dc
        elif p == 'q':
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    if not add_move(r, c): break
                    r += dr; c += dc
        elif p == 'k':
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    add_move(row + dr, col + dc)
            if not self._is_in_check(self.turn):
                if self.castling[self.turn]['K']:
                    if (not self.board[row][5] and not self.board[row][6] and
                        self.board[row][7] == ('R' if is_white else 'r')):
                        if not self._is_square_attacked(row, 5, not is_white) and \
                           not self._is_square_attacked(row, 6, not is_white):
                            moves.append((row, 6))
                if self.castling[self.turn]['Q']:
                    if (not self.board[row][1] and not self.board[row][2] and not self.board[row][3] and
                        self.board[row][0] == ('R' if is_white else 'r')):
                        if not self._is_square_attacked(row, 3, not is_white) and \
                           not self._is_square_attacked(row, 2, not is_white):
                            moves.append((row, 2))
        return moves

    def _is_in_check(self, color):
        is_white = (color == 'w')
        king_pos = None
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and ((is_white and p == 'K') or (not is_white and p == 'k')):
                    king_pos = (r, c)
                    break
            if king_pos: break
        if not king_pos: return False
        return self._is_square_attacked(king_pos[0], king_pos[1], not is_white)

    def _is_square_attacked(self, row, col, by_white):
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if not p: continue
                if (by_white and p.isupper()) or (not by_white and p.islower()):
                    if self._can_attack(r, c, row, col):
                        return True
        return False

    def _can_attack(self, from_row, from_col, to_row, to_col):
        piece = self.board[from_row][from_col]
        p = piece.lower()
        is_white = piece.isupper()
        dr = to_row - from_row
        dc = to_col - from_col
        if p == 'p':
            direction = -1 if is_white else 1
            return dr == direction and abs(dc) == 1
        if p == 'n':
            return (abs(dr), abs(dc)) in [(1, 2), (2, 1)]
        if p == 'b':
            return abs(dr) == abs(dc) and dr != 0 and self._is_path_clear(from_row, from_col, to_row, to_col)
        if p == 'r':
            return (dr == 0 or dc == 0) and (dr != 0 or dc != 0) and self._is_path_clear(from_row, from_col, to_row, to_col)
        if p == 'q':
            return ((abs(dr) == abs(dc) or dr == 0 or dc == 0) and 
                    (dr != 0 or dc != 0) and 
                    self._is_path_clear(from_row, from_col, to_row, to_col))
        if p == 'k':
            return max(abs(dr), abs(dc)) == 1
        return False

    def _is_path_clear(self, from_row, from_col, to_row, to_col):
        dr = (to_row - from_row)
        dc = (to_col - from_col)
        steps = max(abs(dr), abs(dc))
        if steps <= 1: return True
        step_r = dr // steps
        step_c = dc // steps
        for i in range(1, steps):
            r = from_row + step_r * i
            c = from_col + step_c * i
            if self.board[r][c]:
                return False
        return True

    # ============================================================
    #                КОНЕЦ ИГРЫ
    # ============================================================
    def _check_game_over(self):
        has_moves = False
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and ((self.turn == 'w' and p.isupper()) or (self.turn == 'b' and p.islower())):
                    if self._get_legal_moves(r, c):
                        has_moves = True
                        break
            if has_moves: break
        
        if not has_moves:
            self.game_over = True
            if self._is_in_check(self.turn):
                winner = "Чёрные" if self.turn == 'w' else "Белые"
                self.canvas.itemconfigure(self.status_id, text=f"МАТ! Победили {winner}", fill=self.CHECK_COLOR)
                messagebox.showinfo("Игра окончена", f"МАТ! Победили {winner}!")
            else:
                self.canvas.itemconfigure(self.status_id, text="ПАТ! Ничья", fill=self.TEXT_DIM)
                messagebox.showinfo("Игра окончена", "ПАТ! Ничья!")
            return True
        return False

    # ============================================================
    #                УТИЛИТЫ
    # ============================================================
    def _center_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ChessGame(root)
    root.mainloop()