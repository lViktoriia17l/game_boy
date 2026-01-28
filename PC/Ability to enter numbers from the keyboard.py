import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
from functools import reduce

# ================= PROTOCOL CONSTANTS =================
CMD_START       = 0x01
CMD_RESTART     = 0x02
CMD_GIVEUP      = 0x03
CMD_SET         = 0x04
CMD_CLEAR       = 0x05
CMD_FIELD       = 0x07
CMD_DIFFICULTY  = 0x8
CMD_HELP        = 0x98
CMD_CHEAT       = 0x99

CMD_NAMES = {
    0x01: "START", 0x02: "RESTART", 0x03: "GIVEUP",
    0x04: "SET", 0x05: "CLEAR", 0x07: "FIELD",
    0x8: "DIFFICULTY", 0x98: "HELP", 0x99: "CHEAT"
}

STATUS_MAP = {
    0x10: "OK", 0x11: "INVALID", 0x12: "LOCKED",
    0x13: "CRC ERROR", 0x14: "YOU LOSE", 0x15: "YOU WIN",
    0x16: "SETDIF", 0x65: "NOOB", 0x66: "OK_CHEAT"
}


class SudokuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Sudoku Debug Mode")
        self.root.geometry("750x450")
        # Встановлюємо загальний фон вікна, щоб уникнути артефактів
        self.root.configure(bg="#f1f2f6")

        self.ser = None
        self.last_port = None
        self.is_reconnecting = False
        
        self.overlay = None
        self.rx_running = True
        
        self.selected_cell = (0, 0)
        self.cells = [[None] * 9 for _ in range(9)]
        self.initial_field = None
        self.initial_zeros_count = 0
        self.progress_var = tk.StringVar(value="Прогрес: 0%")
        self.game_started = False

        self.status_bar = tk.Label(root, text="Очікування підключення...", relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_menu()
        self.root.bind("<Key>", self.handle_keypress)
        self.root.bind("<Up>", lambda e: self.navigate(-1, 0))
        self.root.bind("<Down>", lambda e: self.navigate(1, 0))
        self.root.bind("<Left>", lambda e: self.navigate(0, -1))
        self.root.bind("<Right>", lambda e: self.navigate(0, 1))

    def handle_keypress(self, event):
        if not self.game_started: return
        char = event.char
        if char in "123456789":
            self.set_val(int(char))
        elif event.keysym in ("BackSpace", "Delete") or char == "0":
            self.clear_cell()

    def navigate(self, dr, dc):
        if not self.game_started: return
        r, c = self.selected_cell
        new_r = max(0, min(8, r + dr))
        new_c = max(0, min(8, c + dc))
        self.select_cell(new_r, new_c)

    # ========== LOGGING & CHECKSUM ==========
    def calculate_crc(self, data_list):
        return reduce(lambda x, y: x ^ y, data_list) if data_list else 0

    def log_tx(self, pkt):
        cmd_name = CMD_NAMES.get(pkt[0], "UNKNOWN")
        print(f"\033[94m[TX] SENDING {cmd_name}:\033[0m {pkt.hex(' ').upper()} | CRC: {hex(pkt[-1])}")

    def log_rx_packet(self, packet, is_long=False):
        color = "\033[92m" if not is_long else "\033[96m"  # Зелений для коротких, бірюзовий для поля
        p_type = "LONG (FIELD)" if is_long else "SHORT (STATUS)"
        print(f"{color}[RX PACKET {p_type}]:\033[0m {bytes(packet).hex(' ').upper()}")

    # ========== SERIAL CORE ==========
    def send_cmd(self, cmd, b1=0, b2=0, b3=0):
        # Додаткова перевірка перед відправкою
        if self.is_reconnecting: return
        
        if not self.ser or not self.ser.is_open:
            self.handle_disconnect()
            return
            
        try:
            payload = [cmd, b1, b2, b3]
            crc = self.calculate_crc(payload)
            pkt = bytes(payload + [crc])
            self.ser.write(pkt)
            self.log_tx(pkt)
        except Exception as e:
            print(f"\033[91m[ERROR TX]: {e}\033[0m")
            self.handle_disconnect()

    def rx_thread(self):
        buffer = bytearray()
        print("\033[93m[SYSTEM] Listening for STM32 data...\033[0m")

        while self.rx_running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting)
                    buffer.extend(chunk)

                    while len(buffer) >= 6:
                        cmd_type = buffer[0]

                        # Повне поле (84 байти)
                        if cmd_type in [CMD_START, CMD_RESTART, CMD_CHEAT]:
                            if len(buffer) < 84: break

                            packet = list(buffer[:84])
                            buffer = buffer[84:]
                            self.log_rx_packet(packet, is_long=True)

                            calc_crc = self.calculate_crc(packet[:83])
                            if calc_crc == packet[83]:
                                print(f"    \033[92m[CRC OK]\033[0m field received")
                                print("=============================")
                                self.root.after(0, self.update_field, packet[2:83], packet[1])
                                self.root.after(100, lambda: self.send_cmd(CMD_FIELD))
                            else:
                                print(f"    \033[91m[CRC ERROR]\033[0m")

                        # Коротка відповідь (6 байт)
                        elif cmd_type in [CMD_SET, CMD_CLEAR, CMD_GIVEUP, CMD_FIELD, CMD_HELP, CMD_DIFFICULTY]:
                            if len(buffer) < 6: break
                            
                            packet = list(buffer[:6])
                            buffer = buffer[6:]
                            self.log_rx_packet(packet, is_long=False)

                            calc_crc = self.calculate_crc(packet[:5])
                            if calc_crc == packet[5]:
                                print(f"    \033[92m[CRC OK]\033[0m status: {STATUS_MAP.get(packet[1])}")
                                print("=============================")
                                status = packet[1]
                                self.root.after(0, self.update_status_only, status)
                                
                                if cmd_type == CMD_SET:
                                    if status == 0x10:
                                        b1, b2, b3 = packet[2], packet[3], packet[4]
                                        self.root.after(0, self.update_single_cell, b1, b2, b3)
                                    if status == 0x11:
                                        b1, b2 = packet[2], packet[3]
                                        self.root.after(0, self.invalid, b1, b2)
                                    if status == 0x12:
                                        b1, b2, b3 = packet[2], packet[3], packet[4]
                                        self.root.after(0, self.locked_cell, b1, b2, b3)
                                    if status == 0x15:
                                        self.root.after(0, self.mega_win)
                                
                                if cmd_type == 0x05:
                                    b1, b2 = packet[2], packet[3]
                                    if status == 0x10:
                                        self.root.after(0, self.clear, b1, b2)
                                    elif status == 0x12:
                                        self.root.after(0, self.locked_cell, b1, b2, 0)
                                
                                if cmd_type == CMD_FIELD:
                                    total = packet[2]
                                    current = packet[3]
                                    self.root.after(0, self.refresh_progress, total, current)
                                
                                if cmd_type == CMD_GIVEUP:
                                    if status == 0x14:
                                        self.root.after(0, self.give_up)
                                
                                if cmd_type == CMD_HELP:
                                    b1, b2, b3 = packet[2], packet[3], packet[4]
                                    if status == 0x65:
                                        self.root.after(0, self.apply_hint_result, b1, b2, b3)
                                    else:
                                        self.root.after(0, self.locked_cell, b1, b2, 0)
                                
                                if cmd_type == CMD_DIFFICULTY:
                                    if status == 0x16:
                                        level = packet[2]
                                        self.root.after(0, self.apply_difficulty_confirmed, level)
                            else:
                                print(f"    \033[91m[CRC ERROR]\033[0m")
                time.sleep(0.01)
            except Exception as e:
                # Якщо виникла помилка читання (кабель висмикнули), викликаємо disconnect
                print(f"RX Thread error (Connection Lost): {e}")
                self.root.after(0, self.handle_disconnect)
                break

    # ========== GUI LOGIC ==========
    def update_field(self, field_data, status):
        if self.game_started and self.initial_field is None:
            self.initial_field = list(field_data)
            self.initial_zeros_count = sum(1 for v in self.initial_field if v == 0)

        for i in range(81):
            val = field_data[i]
            r, c = i // 9, i % 9
            color = "#2d3436" if self.initial_field and self.initial_field[i] != 0 else "#0984e3"
            self.cells[r][c].config(text=str(val) if val != 0 else "", fg=color)

        self.update_status_only(status)

    def apply_hint_result(self, r, c, val):
        if 0 <= r < 9 and 0 <= c < 9:
            display_text = str(val) if val != 0 else ""
            self.cells[r][c].config(text=display_text, fg="#8e44ad")
            original_bg = self.cells[r][c].cget("bg")
            self.cells[r][c].config(bg="#fff9c4")
            self.root.after(300, lambda: self.cells[r][c].config(bg=original_bg))
            self.status_bar.config(text=f"STATUS: Використано підказку для ({r + 1}, {c + 1})", fg="#8e44ad")
            self.send_cmd(CMD_FIELD)

    def apply_difficulty_confirmed(self, level):
        colors = {1: "#2ecc71", 2: "#f1c40f", 3: "#e74c3c"}
        for i, btn in enumerate(self.diff_buttons, 1):
            if i == level:
                btn.config(font=("Arial", 35, "bold"), fg=colors.get(level, "black"))
            else:
                btn.config(font=("Arial", 20), fg="#bdc3c7")
        self.btn_start.config(state=tk.NORMAL, bg="#2ecc71")
        self.status_bar.config(text=f"STATUS: Рівень {level} підтверджено", fg="green")

    def update_single_cell(self, b1, b2, b3):
        display_text = str(b3)
        self.cells[b1][b2].config(text=display_text, fg="#0984e3")

    def clear(self, r, c):
        self.cells[r][c].config(text="")

    def give_up(self):
        messagebox.showinfo("Game Over", "Ви здалися! Повертаємось до головного меню.")
        if hasattr(self, 'main_ui'):
            self.main_ui.destroy()
        self.game_started = False
        self.initial_field = None
        self.progress_var.set("Прогрес: 0%")
        self.create_menu()

    def invalid(self, r, c):
        self.cells[r][c].config(bg="#ffeaa7")
        self.root.after(400, lambda: self.cells[r][c].config(bg="white"))

    def update_status_only(self, status):
        msg = STATUS_MAP.get(status, f"Code: {hex(status)}")
        color = "red" if status in [0x11, 0x12, 0x13] else "black"
        self.status_bar.config(text=f"STATUS: {msg}", fg=color)

    def locked_cell(self, r, c, val):
        if 0 <= r < 9 and 0 <= c < 9:
            original_color = self.cells[r][c].cget("bg")
            self.cells[r][c].config(bg="#ff7675")
            self.root.after(500, lambda: self.cells[r][c].config(bg=original_color))

    def refresh_progress(self, total_zeros, current_zeros):
        if total_zeros == 0: return
        filled = total_zeros - current_zeros
        pct = int((filled / total_zeros) * 100)
        pct = max(0, min(100, pct))
        self.progress_var.set(f"Прогрес: {pct}%")
        self.progressbar["value"] = pct

    def mega_win(self):
        # Створення модального вікна перемоги
        win_window = tk.Toplevel(self.root)
        win_window.title("ПЕРЕМОГА! 🎉")
        win_window.geometry("400x250")
        win_window.configure(bg="#f1f2f6")
        win_window.transient(self.root)
        win_window.grab_set()

        # Центрування вікна перемоги відносно головного
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 125
        win_window.geometry(f"+{x}+{y}")

        tk.Label(win_window, text="ВІТАЄМО! ✨", font=("Arial", 24, "bold"), bg="#f1f2f6", fg="#2ecc71").pack(pady=20)
        tk.Label(win_window, text="Ви успішно розв'язали Судоку!", font=("Arial", 12), bg="#f1f2f6").pack(pady=10)

        btn_frame = tk.Frame(win_window, bg="#f1f2f6")
        btn_frame.pack(pady=20)
        
        # Функція для повного скидання гри та повернення в меню
        def reset_and_return():
            win_window.destroy()
            if hasattr(self, 'main_ui'):
                self.main_ui.destroy()
            self.game_started = False
            self.initial_field = None
            self.progress_var.set("Прогрес: 0%")
            self.create_menu()
            self.status_bar.config(text="Гру завершено. Оберіть новий рівень.", fg="black")

        # Кнопка тільки для виходу в меню (трохи збільшив її і зробив зеленою для краси)
        tk.Button(btn_frame, text="У МЕНЮ", font=("Arial", 12, "bold"), bg="#2ecc71", fg="white", width=20,
                  command=reset_and_return).pack(padx=10)

    # ========== INITIALIZATION ==========
    def connect(self):
        port = self.port_combo.get()
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
            self.last_port = port
            self.btn_connect.config(state=tk.DISABLED, text="CONNECTED")
            for btn in self.diff_buttons:
                btn.config(state=tk.NORMAL)
            
            self.rx_running = True
            threading.Thread(target=self.rx_thread, daemon=True).start()
            print(f"\033[92m[CONNECTED]\033[0m to {port}")
            
        except Exception as e:
            messagebox.showerror("Port Error", str(e))

    def create_menu(self):
        self.menu_frame = tk.Frame(self.root, bg="#f1f2f6")
        self.menu_frame.pack(expand=True, fill="both")

        tk.Label(self.menu_frame, text="SUDOKU STM32", font=("Arial", 30, "bold"), bg="#f1f2f6").pack(pady=(50, 20))

        self.btn_start = tk.Button(self.menu_frame, text="START GAME", state=tk.DISABLED, command=self.start_game,
                                   bg="#2ecc71", fg="white", font=("Arial", 12, "bold"), width=20)
        self.btn_start.pack(pady=10)

        tk.Label(self.menu_frame, text="Оберіть рівень складності:", font=("Arial", 10), bg="#f1f2f6").pack(pady=(10, 5))
        diff_frame = tk.Frame(self.menu_frame, bg="#f1f2f6")
        diff_frame.pack(pady=5)

        self.diff_buttons = []
        levels = [("🙂", 1), ("😐", 2), ("😡", 3)]
        init_state = tk.NORMAL if self.ser and self.ser.is_open else tk.DISABLED

        for emoji, level in levels:
            btn = tk.Button(diff_frame, text=emoji, font=("Arial", 20), width=3, bd=0, cursor="hand2",
                            state=init_state, command=lambda l=level: self.select_difficulty_request(l))
            btn.pack(side=tk.LEFT, padx=10)
            self.diff_buttons.append(btn)

        tk.Frame(self.menu_frame, bg="#f1f2f6").pack(expand=True) # Spacer

        tk.Label(self.menu_frame, text="Налаштування зв'язку:", font=("Arial", 10), bg="#f1f2f6").pack(pady=(10, 0))
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_combo = ttk.Combobox(self.menu_frame, values=ports, width=27)
        if ports: self.port_combo.current(0)
        self.port_combo.pack(pady=10)

        conn_text = "CONNECTED" if self.ser and self.ser.is_open else "CONNECT"
        conn_state = tk.DISABLED if self.ser and self.ser.is_open else tk.NORMAL
        self.btn_connect = tk.Button(self.menu_frame, text=conn_text, state=conn_state, command=self.connect, width=20)
        self.btn_connect.pack(pady=(0, 50))

    def start_game(self):
        self.game_started = True
        self.menu_frame.destroy()
        self.create_game_ui()
        self.send_cmd(CMD_START)
        self.root.after(300, lambda: self.send_cmd(CMD_FIELD))

    def create_game_ui(self):
        # задаємо колір фону явно, щоб не було синіх артефактів після реконекту
        self.main_ui = tk.Frame(self.root, bg="#f1f2f6")
        self.main_ui.pack(expand=True, fill="both", padx=20, pady=20)

        side = tk.Frame(self.main_ui, bg="#f1f2f6")
        side.pack(side=tk.LEFT, padx=20)

        tk.Label(side, textvariable=self.progress_var, font=("Arial", 12, "bold"), bg="#f1f2f6").pack()
        self.progressbar = ttk.Progressbar(side, length=150, mode='determinate')
        self.progressbar.pack(pady=10)

        for i in range(1, 10):
            if (i - 1) % 3 == 0: 
                f = tk.Frame(side, bg="#f1f2f6")
                f.pack()
            tk.Button(f, text=str(i), width=4, height=2, command=lambda n=i: self.set_val(n)).pack(side=tk.LEFT, padx=2, pady=2)

        tk.Button(side, text="CLEAR", bg="#fab1a0", command=self.clear_cell, width=15).pack(pady=20)
        tk.Button(side, text="RESTART", command=lambda: self.send_cmd(CMD_RESTART)).pack(fill="x")
        tk.Button(side, text="GIVE UP", bg="#e67e22", fg="white", font=("Arial", 10, "bold"),
                  command=self.give_up_action, width=15).pack(pady=(40, 10))

        # right_panel тепер має колір фону, а не прозора
        right_panel = tk.Frame(self.main_ui, bg="#f1f2f6")
        right_panel.pack(side=tk.RIGHT, expand=True, fill="both", padx=20)

        self.hint_btn = tk.Button(right_panel, text="💡", font=("Arial", 30), fg="#f1c40f", bg="#f1f2f6",
                                  activebackground="#f1f2f6", bd=0, cursor="hand2", command=self.noob_help)
        self.hint_btn.pack(pady=(0, 10))

        grid_container = tk.Frame(right_panel, bg="#f1f2f6")
        grid_container.pack(expand=True)

        grid = tk.Frame(self.main_ui, bg="#2c3e50", bd=2)   
        grid.pack()

        for r in range(9):
            for c in range(9):
                lbl = tk.Label(grid, text="", width=2, height=1, font=("Arial", 20, "bold"), bg="white")
                lbl.grid(row=r, column=c, padx=(1, 4 if (c + 1) % 3 == 0 else 1),
                         pady=(1, 4 if (r + 1) % 3 == 0 else 1))
                lbl.bind("<Button-1>", lambda e, row=r, col=c: self.select_cell(row, col))
                self.cells[r][c] = lbl
        self.select_cell(0, 0)

    def select_cell(self, r, c):
        self.cells[self.selected_cell[0]][self.selected_cell[1]].config(bg="white")
        self.selected_cell = (r, c)
        self.cells[r][c].config(bg="#74b9ff")

    def set_val(self, val):
        self.send_cmd(CMD_SET, self.selected_cell[0], self.selected_cell[1], val)
        self.root.after(100, lambda: self.send_cmd(CMD_FIELD))

    def select_difficulty_request(self, level):
        self.send_cmd(0x08, level, 0, 0)

    def noob_help(self):
        self.hint_btn.config(fg="white")
        self.root.after(200, lambda: self.hint_btn.config(fg="#f1c40f"))
        r, c = self.selected_cell
        self.send_cmd(0x98, r, c, 0)

    def give_up_action(self):
        if messagebox.askyesno("Здатися?", "Ви впевнені? Прогрес буде втрачено."):
            self.send_cmd(0x03)
            self.root.after(200, lambda: self.send_cmd(CMD_FIELD))

    def clear_cell(self):
        self.send_cmd(CMD_CLEAR, self.selected_cell[0], self.selected_cell[1])
        self.root.after(100, lambda: self.send_cmd(CMD_FIELD))

    def handle_disconnect(self):
        if self.is_reconnecting:
            return

        print("\033[91m[DISCONNECTED FROM STM]\033[0m")
        self.is_reconnecting = True
        self.rx_running = False

        try:
            if self.ser:
                self.ser.close()
        except:
            pass

        self.show_overlay()
        threading.Thread(target=self.reconnect_loop, daemon=True).start()

    def show_overlay(self):
        if self.overlay: return
        self.overlay = tk.Frame(self.root, bg="#2c3e50")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(self.overlay, text="ЗВ'ЯЗОК ВТРАЧЕНО", font=("Arial", 26, "bold"), fg="#e74c3c", bg="#2c3e50").pack(expand=True)
        tk.Label(self.overlay, text=f"Очікування {self.last_port}...", fg="white", bg="#2c3e50").pack(pady=20)

    def reconnect_loop(self):
        print("[SYSTEM] Searching STM...")
        while self.is_reconnecting:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            if self.last_port in ports:
                try:
                    self.ser = serial.Serial(self.last_port, 115200, timeout=0.1)
                    print("[SYSTEM] STM reconnected!")
                    self.is_reconnecting = False
                    self.root.after(0, self.on_reconnect_success)
                    return
                except:
                    pass
            time.sleep(1)

    def on_reconnect_success(self):
        print("[SYSTEM] Restoring game session...")
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None

        self.status_bar.config(text="Зв'язок відновлено", fg="green")
        self.rx_running = True
        threading.Thread(target=self.rx_thread, daemon=True).start()
        
        # Запит актуального стану поля
        self.root.after(300, lambda: self.send_cmd(CMD_FIELD))

if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()