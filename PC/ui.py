import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
from functools import reduce

# ================= PROTOCOL CONSTANTS =================
CMD_START    = 0x01
CMD_RESTART  = 0x02
CMD_GIVEUP   = 0x03
CMD_SET      = 0x04
CMD_CLEAR    = 0x05
CMD_CLEARALL = 0x06
CMD_FIELD    = 0x07

STATUS_MAP = {
    0x10: "OK",
    0x11: "INVALID",
    0x12: "LOCKED",
    0x14: "YOU LOSE",
    0x15: "YOU WIN"
}

class SudokuGUI:
    def init(self, root):
        self.root = root
        self.root.title("STM32 Sudoku - Full Debug Mode")
        self.root.geometry("950x670")

        self.ser = None
        self.last_port = None
        self.is_reconnecting = False

        self.selected_cell = (0, 0)
        self.cells = [[None]*9 for _ in range(9)]
        self.locked_cells = set() # Зберігаємо координати заблокованих клітинок
        
        self.status_bar = tk.Label(root, text="Підключіть мікроконтролер",
                                   relief=tk.SUNKEN, anchor="w", font=("Arial", 10))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.overlay = None
        self.create_menu()

    # ========== SERIAL CORE (XOR CHECKSUM) ==========
    def checksum(self, *data):
        return reduce(lambda x, y: x ^ y, data)

    def send_cmd(self, cmd, b1=0, b2=0, b3=0):
        if not self.ser or not self.ser.is_open:
            return
        try:
            crc = self.checksum(cmd, b1, b2, b3)
            pkt = bytes([cmd, b1, b2, b3, crc])
            self.ser.write(pkt)
            print(f"[TX] -> {pkt.hex(' ').upper()} (XOR CRC: {hex(crc)})")
        except (serial.SerialException, OSError):
            self.handle_disconnect()

    def rx_thread(self):
        buffer = bytearray()
        while self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting)
                    buffer.extend(chunk)
                    
                    while len(buffer) >= 84:
                        packet = list(buffer[:84])
                        buffer = buffer[84:]
                        
                        matrix_data = packet[2:83]
                        status_byte = packet[1]
                        self.root.after(0, self.update_field, matrix_data, status_byte)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if not self.is_reconnecting:
                    self.root.after(0, self.handle_disconnect)
                break

    # ========== RECONNECT SYSTEM ==========
    def handle_disconnect(self):
        self.is_reconnecting = True
        if self.ser:
            try: self.ser.close()
            except: pass
        self.ser = None
        self.show_reconnect_overlay()
        threading.Thread(target=self.reconnect_loop, daemon=True).start()

    def show_reconnect_overlay(self):
        if self.overlay: return
        self.overlay = tk.Frame(self.root, bg="#2c3e50")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(self.overlay, text="ЗВ'ЯЗОК ВТРАЧЕНО", font=("Arial", 28, "bold"), fg="#e74c3c", bg="#2c3e50").pack(expand=True)
        tk.Label(self.overlay, text=f"Очікування порту {self.last_port}...", fg="white", bg="#2c3e50").pack(pady=20)

    def reconnect_loop(self):
        while self.is_reconnecting:
            if self.last_port in [p.device for p in serial.tools.list_ports.comports()]:
                try:
                    self.ser = serial.Serial(self.last_port, 115200, timeout=0.1)
                    self.is_reconnecting = False
                    self.root.after(0, self.on_reconnect_success)
                    return
                except: pass
            time.sleep(1)
            def on_reconnect_success(self):
        if self.overlay: self.overlay.destroy(); self.overlay = None
        self.status_bar.config(text=f"Зв'язок відновлено: {self.last_port}", fg="green")
        threading.Thread(target=self.rx_thread, daemon=True).start()
        self.locked_cells.clear() # Очищуємо при перепідключенні
        self.root.after(500, lambda: self.send_cmd(CMD_FIELD))

    # ========== GUI SETUP ==========
    def update_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports() if "bluetooth" not in p.description.lower()]
        self.port_combo["values"] = ports
        if ports: self.port_combo.current(0)

    def connect(self):
        port = self.port_combo.get()
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.1)
            self.last_port = port
            self.btn_start.config(state=tk.NORMAL)
            self.btn_connect.config(state=tk.DISABLED, text="Підключено")
            threading.Thread(target=self.rx_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    def create_menu(self):
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack(expand=True)
        tk.Label(self.menu_frame, text="SUDOKU STM32", font=("Arial", 36, "bold")).pack(pady=20)
        
        self.port_combo = ttk.Combobox(self.menu_frame, state="readonly", width=20)
        self.port_combo.pack(pady=10)
        tk.Button(self.menu_frame, text="Оновити список портів", command=self.update_ports).pack()

        self.btn_connect = tk.Button(self.menu_frame, text="ПІДКЛЮЧИТИСЯ", width=25, height=2, command=self.connect)
        self.btn_connect.pack(pady=20)

        self.btn_start = tk.Button(self.menu_frame, text="ПОЧАТИ ГРУ", font=("Arial", 14, "bold"), 
                                   bg="#2ecc71", fg="white", state=tk.DISABLED, command=self.start_game)
        self.btn_start.pack()
        self.update_ports()

    def start_game(self):
        self.send_cmd(CMD_START)
        self.menu_frame.destroy()
        self.create_game_ui()

    def create_game_ui(self):
        self.game_container = tk.Frame(self.root)
        self.game_container.pack(expand=True, fill="both", padx=20, pady=20)

        ctrl = tk.Frame(self.game_container)
        ctrl.pack(side=tk.LEFT, padx=20)

        tk.Label(ctrl, text="Оберіть цифру:", font=("Arial", 11, "bold")).grid(row=0, column=0, columnspan=3, pady=5)

        for i in range(1, 10):
            tk.Button(ctrl, text=str(i), width=6, height=2, font=("Arial", 12, "bold"),
                            command=lambda n=i: self.set_value_action(n)).grid(row=((i-1)//3)+1, column=(i-1)%3, padx=2, pady=2)
        
        tk.Button(ctrl, text="СТЕРТИ", width=22, height=2, bg="#fab1a0", font=("Arial", 9, "bold"),
                  command=lambda: self.set_value_action(0)).grid(row=4, column=0, columnspan=3, pady=(15, 5))

        tk.Button(ctrl, text="ОНОВИТИ ЕКРАН", width=22, bg="#ecf0f1",
                  command=lambda: self.send_cmd(CMD_FIELD)).grid(row=5, column=0, columnspan=3, pady=5)
        
        tk.Button(ctrl, text="RESTART", width=22, bg="#ffeaa7",
                  command=lambda: self.restart_action()).grid(row=6, column=0, columnspan=3, pady=5)

        grid_frame = tk.Frame(self.game_container, bg="#2c3e50", bd=2)
        grid_frame.pack(side=tk.RIGHT)

        for r in range(9):
            for c in range(9):
                cell = tk.Label(grid_frame, text="", width=2, height=1, 
                                font=("Arial", 22, "bold"), bg="white", fg="#2c3e50")
                px = 4 if (c+1) % 3 == 0 and c < 8 else 1
                py = 4 if (r+1) % 3 == 0 and r < 8 else 1
                cell.grid(row=r, column=c, padx=(1, px), pady=(1, py))
                cell.bind("<Button-1>", lambda e, row=r, col=c: self.select_cell(row, col))
                self.cells[r][c] = cell
        
        self.select_cell(0, 0)
        # ========== LOGIC ACTIONS ==========
    def restart_action(self):
        self.locked_cells.clear() # Скидаємо блокування при рестарті
        self.send_cmd(CMD_RESTART)

    def select_cell(self, r, c):
        # Повертаємо попередній клітинці її колір (білий або сірий)
        prev_r, prev_c = self.selected_cell
        bg_color = "#f0f0f0" if (prev_r, prev_c) in self.locked_cells else "white"
        self.cells[prev_r][prev_c].config(bg=bg_color)
        
        self.selected_cell = (r, c)
        self.cells[r][c].config(bg="#74b9ff") # Колір виділення
        
        status_text = f"Клітинка: [{r+1}, {c+1}]"
        if (r, c) in self.locked_cells:
            status_text += " (ЗАБЛОКОВАНО)"
        self.status_bar.config(text=status_text)

    def set_value_action(self, val):
        r, c = self.selected_cell
        
        # ЗАБОРОНА: якщо клітинка в списку заблокованих, нічого не робимо
        if (r, c) in self.locked_cells:
            self.status_bar.config(text=f"Помилка: Клітинка [{r+1}, {c+1}] згенерована системою!", fg="red")
            return

        # Візуальна зміна (синім кольором як "чернетка")
        self.cells[r][c].config(text=str(val) if val != 0 else "", fg="#0984e3")
        
        if val == 0:
            self.send_cmd(CMD_CLEAR, r, c)
        else:
            self.send_cmd(CMD_SET, r, c, val)
        
        # Оновлення через 150мс для підтвердження від МК
        self.root.after(150, lambda: self.send_cmd(CMD_FIELD))

    def update_field(self, field_data, status):
        if len(field_data) < 81: return
        
        for i in range(81):
            val = field_data[i]
            r, c = i // 9, i % 9
            
            # Якщо ми отримали початкове поле, і в клітинці вже є цифра
            # вважаємо її заблокованою (locked)
            if val != 0 and status == 0x10 and not self.locked_cells:
                # Це відбувається зазвичай лише при першому отриманні поля після Start
                # (якщо locked_cells ще порожня)
                pass

            # Оновлюємо текст
            self.cells[r][c].config(text=str(val) if val != 0 else "")
            
            # Якщо статус 0x12 прийшов від МК — додаємо клітинку в locked на льоту
            if status == 0x12 and r == self.selected_cell[0] and c == self.selected_cell[1]:
                self.locked_cells.add((r, c))

            # Візуальне оформлення заблокованих клітинок
            if (r, c) in self.locked_cells:
                self.cells[r][c].config(fg="#2d3436", bg="#f0f0f0") # Темно-сірий текст, сірий фон
            else:
                # Звичайні клітинки, які ввів користувач
                if self.cells[r][c].cget("bg") != "#74b9ff": # Якщо не виділена зараз
                    self.cells[r][c].config(fg="#0984e3", bg="white")

        # Якщо контролер прямо каже, що ми наступили на заблоковану клітинку
        if status == 0x12:
            self.locked_cells.add(self.selected_cell)
            self.cells[self.selected_cell[0]][self.selected_cell[1]].config(bg="#f0f0f0")

        txt = STATUS_MAP.get(status, f"Код: {hex(status)}")
        color = "red" if status == 0x12 else "black"
        self.status_bar.config(text=f"Статус гри: {txt}", fg=color)

if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuGUI(root)
    root.mainloop()