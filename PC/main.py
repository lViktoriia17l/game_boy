import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import serial
import serial.tools.list_ports

class GameInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Sudoku Controller")
        self.root.geometry("700x550")

        self.ser = None

        self.status_label = tk.Label(root, text="Waiting for connection...", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_menu_screen()

    def create_menu_screen(self):
        """Створює екран меню"""
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack(fill="both", expand=True)

        lbl_title = tk.Label(self.menu_frame, text="СУДОКУ", font=("Arial", 40, "bold"))
        lbl_title.pack(pady=(30, 10))

        # --- БЛОК ПІДКЛЮЧЕННЯ ---
        conn_frame = tk.LabelFrame(self.menu_frame, text="Налаштування з'єднання", padx=10, pady=10)
        conn_frame.pack(pady=10)

        tk.Label(conn_frame, text="Порт:").pack(side=tk.LEFT, padx=5)
        
        self.port_combo = ttk.Combobox(conn_frame, width=10)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        btn_refresh = tk.Button(conn_frame, text="⟳", width=3, command=self.update_ports)
        btn_refresh.pack(side=tk.LEFT, padx=2)

        self.btn_connect = tk.Button(conn_frame, text="Connect", bg="#2196F3", fg="white", 
                                     command=self.connect_serial)
        self.btn_connect.pack(side=tk.LEFT, padx=10)

        self.btn_start = tk.Button(self.menu_frame, text="Start Game", font=("Arial", 16), 
                             bg="#4CAF50", fg="white", width=15,
                             state=tk.DISABLED, 
                             command=self.start_game_transition)
        self.btn_start.pack(pady=20)

        self.log_text = tk.Text(self.menu_frame, height=8, width=50)
        self.log_text.pack(pady=10)
        
        self.update_ports()
        self.log_text.insert(tk.END, "System ready. Please connect to device.\n")

    def update_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.current(0)
            self.log_text.insert(tk.END, f"Found ports: {port_list}\n")
        else:
            self.log_text.insert(tk.END, "No COM ports found.\n")
        self.log_text.see(tk.END)

    def connect_serial(self):
        selected_port = self.port_combo.get()
        if not selected_port:
            messagebox.showwarning("Warning", "Please select a COM port!")
            return
        try:
            self.ser = serial.Serial(selected_port, 115200, timeout=1)
            if self.ser.is_open:
                self.status_label.config(text=f"Connected to {selected_port}", bg="#d4edda")
                self.log_text.insert(tk.END, f"Successfully connected to {selected_port}\n")
                self.btn_connect.config(text="Connected", state=tk.DISABLED, bg="grey")
                self.btn_start.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not open port: {e}")

    def start_game_transition(self):
        self.menu_frame.destroy()
        self.status_label.config(text="Game Started")
        self.create_game_screen()

    def create_game_screen(self):
        """Екран гри: клавіатура зліва, сітка справа"""
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- ЛІВА ПАНЕЛЬ (Кнопки 1-9 та порожня) ---
        left_panel = tk.Frame(self.game_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(left_panel, text="Ввід:", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        btn_grid = tk.Frame(left_panel)
        btn_grid.pack()

        # Кнопки 1-9
        for i in range(1, 10):
            btn = tk.Button(btn_grid, text=str(i), width=4, height=2, font=("Arial", 12),
                            command=lambda x=i: self.send_data(x))
            btn.grid(row=(i-1)//3, column=(i-1)%3, padx=2, pady=2)

        # ПОРОЖНЯ КНОПКА (замість 0)
        self.btn_empty = tk.Button(left_panel, text="", width=14, height=2, font=("Arial", 12),
                                   bg="#eeeeee", command=lambda: self.send_data(0))
        self.btn_empty.pack(pady=5)
        
        btn_back = tk.Button(left_panel, text="Exit to Menu", bg="#ffcccc", command=self.back_to_menu)
        btn_back.pack(side=tk.BOTTOM, pady=20)

        # --- ПРАВА ПАНЕЛЬ (Сітка 9x9) ---
        right_panel = tk.Frame(self.game_frame)
        right_panel.pack(side=tk.RIGHT, expand=True)

        self.cells = [[None for _ in range(9)] for _ in range(9)]
        for r in range(9):
            for c in range(9):
                pady, padx = (0, 0), (0, 0)
                if r % 3 == 0 and r != 0: pady = (5, 0)
                if c % 3 == 0 and c != 0: padx = (5, 0)

                cell = tk.Entry(right_panel, width=2, font=('Arial', 18), justify='center')
                cell.grid(row=r, column=c, padx=padx, pady=pady)
                self.cells[r][c] = cell

    def send_data(self, number):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(str(number).encode())
                print(f"Sent to STM32: {number}")
            except Exception as e:
                print(f"Send error: {e}")
        else:
            print(f"No connection. Action for: {number}")

    def back_to_menu(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.game_frame.destroy()
        self.status_label.config(text="Waiting for connection...", bg="#f0f0f0")
        self.create_menu_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = GameInterface(root)
    root.mainloop()