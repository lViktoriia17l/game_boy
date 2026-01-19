import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading

# ================= PROTOCOL =================
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

# ================= GUI =================
class SudokuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Sudoku")
        self.root.geometry("920x620")

        self.ser = None
        self.selected_cell = (0, 0)
        self.cells = [[None]*9 for _ in range(9)]

        self.status = tk.Label(root, text="Не підключено",
                               relief=tk.SUNKEN, anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_menu()

    # ========== SERIAL ==========
    def checksum(self, *data):
        return sum(data) & 0xFF

    def send_cmd(self, cmd, b1=0, b2=0, b3=0):
        if not self.ser or not self.ser.is_open:
            return
        pkt = bytes([cmd, b1, b2, b3, self.checksum(cmd, b1, b2, b3)])
        self.ser.write(pkt)

    def rx_thread(self):
        while self.ser and self.ser.is_open:
            try:
                cmd = self.ser.read(1)
                if not cmd:
                    continue

                cmd = cmd[0]

                if cmd == CMD_FIELD:
                    field = self.ser.read(81)
                    status = self.ser.read(1)[0]
                    chk = self.ser.read(1)[0]

                    if chk != self.checksum(cmd, *field, status):
                        continue

                    self.root.after(0, self.update_field, field, status)

            except serial.SerialException:
                break

    # ========== MENU ==========
    def create_menu(self):
        self.menu = tk.Frame(self.root)
        self.menu.pack(expand=True)

        tk.Label(self.menu, text="SUDOKU",
                 font=("Segoe UI", 36, "bold")).pack(pady=20)

        port_bar = tk.Frame(self.menu)
        port_bar.pack(pady=10)

        tk.Label(port_bar, text="COM порт:").pack(side=tk.LEFT)

        self.port_combo = ttk.Combobox(port_bar, width=15, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=5)

        tk.Button(port_bar, text="Оновити",
                  command=self.update_ports).pack(side=tk.LEFT)

        self.btn_connect = tk.Button(self.menu, text="CONNECT",
                                     width=20, command=self.connect)
        self.btn_connect.pack(pady=10)

        self.btn_start = tk.Button(self.menu, text="START GAME",
                                   font=("Arial", 14, "bold"),
                                   bg="#4CAF50", fg="white",
                                   state=tk.DISABLED,
                                   command=self.start_game)
        self.btn_start.pack(pady=20)

        self.log = tk.Text(self.menu, height=8, width=60)
        self.log.pack()

        self.update_ports()

    def update_ports(self):
        ports = []
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            if "bluetooth" in desc:
                continue
            if "usb" in desc or "stm" in desc or "serial" in desc:
                ports.append(p.device)

        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def connect(self):
        port = self.port_combo.get()
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()

            self.ser = serial.Serial(port, 115200, timeout=0.1)
            self.log_msg(f"Connected to {port}")
            self.status.config(text=f"Підключено: {port}")
            self.btn_connect.config(text="Connected", state=tk.DISABLED)
            self.btn_start.config(state=tk.NORMAL)

            threading.Thread(target=self.rx_thread,
                             daemon=True).start()

        except PermissionError:
            messagebox.showerror(
                "Access denied",
                f"Порт {port} зайнятий.\nЗакрий STM32CubeProgrammer / Serial Monitor."
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    # ========== GAME ==========
    def start_game(self):
        self.send_cmd(CMD_START)
        self.menu.destroy()
        self.create_game()

    def create_game(self):
        self.game = tk.Frame(self.root)
        self.game.pack(expand=True, fill="both", padx=20, pady=20)

        # LEFT PANEL
        left = tk.Frame(self.game)
        left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left, text="Цифри",
                 font=("Segoe UI", 14)).pack(pady=5)

        pad = tk.Frame(left)
        pad.pack()
        for i in range(1, 10):
            tk.Button(pad, text=str(i),
                      width=5, height=2,
                      command=lambda n=i: self.set_value(n))\
                .grid(row=(i-1)//3, column=(i-1)%3, padx=2, pady=2)

        tk.Button(left, text="CLEAR CELL", width=18,
                  command=lambda: self.set_value(0)).pack(pady=8)

        tk.Button(left, text="CLEAR ALL", width=18,
                  command=lambda: self.send_cmd(CMD_CLEARALL)).pack(pady=4)

        tk.Button(left, text="RESTART", width=18,
                  command=lambda: self.send_cmd(CMD_RESTART)).pack(pady=4)

        tk.Button(left, text="GIVE UP", width=18,
                  command=lambda: self.send_cmd(CMD_GIVEUP)).pack(pady=4)

        tk.Button(left, text="FIELD / PROGRESS", width=18,
                  command=lambda: self.send_cmd(CMD_FIELD)).pack(pady=12)

        # GRID
        grid = tk.Frame(self.game, bg="black", bd=3)
        grid.pack(side=tk.RIGHT, padx=20)

        for r in range(9):
            for c in range(9):
                cell = tk.Label(
                    grid, text="", width=2, height=1,
                    font=("Segoe UI", 20, "bold"),
                    bg="white", fg="black",
                    relief="solid", bd=1
                )

                padx = (1, 4) if (c+1) % 3 == 0 else (1, 1)
                pady = (1, 4) if (r+1) % 3 == 0 else (1, 1)

                cell.grid(row=r, column=c, padx=padx, pady=pady)
                cell.bind("<Button-1>",
                          lambda e, rr=r, cc=c: self.select_cell(rr, cc))
                self.cells[r][c] = cell

    def select_cell(self, r, c):
        pr, pc = self.selected_cell
        self.cells[pr][pc].config(bg="white")
        self.selected_cell = (r, c)
        self.cells[r][c].config(bg="#bbdefb")
        self.status.config(text=f"Клітинка: {r},{c}")

    def set_value(self, val):
        r, c = self.selected_cell
        if val == 0:
            self.send_cmd(CMD_CLEAR, r, c)
        else:
            self.send_cmd(CMD_SET, r, c, val)

    # ========== FIELD UPDATE ==========
    def update_field(self, field, status):
        for i, v in enumerate(field):
            r = i // 9
            c = i % 9
            self.cells[r][c].config(text="" if v == 0 else str(v))

        self.status.config(
            text=STATUS_MAP.get(status, "UNKNOWN")
        )


# ================= START =================
if __name__ == "__main__":
    root = tk.Tk()
    SudokuGUI(root)
    root.mainloop()
