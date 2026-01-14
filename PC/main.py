import tkinter as tk
from tkinter import messagebox

class GameInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Sudoku Controller")
        self.root.geometry("700x500") # Трохи ширше для зручності

        # --- Статус-бар (спільний для всіх екранів) ---
        self.status_label = tk.Label(root, text="Waiting for connection...", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Запускаємо створення меню
        self.create_menu_screen()

    def create_menu_screen(self):
        """Створює екран меню"""
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack(fill="both", expand=True)

        # Великий заголовок
        lbl_title = tk.Label(self.menu_frame, text="СУДОКУ", font=("Arial", 40, "bold"))
        lbl_title.pack(pady=(40, 20))

        # Кнопка Старт
        btn_start = tk.Button(self.menu_frame, text="Start Game", font=("Arial", 16), 
                              bg="#4CAF50", fg="white", width=15,
                              command=self.start_game_transition) # Викликає перехід
        btn_start.pack(pady=20)

        # Лог (текстове поле)
        self.log_text = tk.Text(self.menu_frame, height=8, width=50)
        self.log_text.pack(pady=10)
        self.log_text.insert(tk.END, "System ready. Press Start to play.\n")

    def start_game_transition(self):
        """Функція переходу: видаляє меню і будує гру"""
        # 1. Знищуємо фрейм меню (очищаємо вікно)
        self.menu_frame.destroy()
        
        # 2. Оновлюємо статус
        self.status_label.config(text="Game Started")
        
        # 3. Будуємо екран гри
        self.create_game_screen()

    def create_game_screen(self):
        """Створює екран гри: зліва цифри, справа сітка"""
        self.game_frame = tk.Frame(self.root)
        self.game_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- ЛІВА ПАНЕЛЬ (Клавіатура 0-9) ---
        left_panel = tk.Frame(self.game_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=20)

        tk.Label(left_panel, text="Ввід:", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        # Створюємо кнопки 1-9 сіткою 3x3
        btn_frame = tk.Frame(left_panel)
        btn_frame.pack()

        # Кнопки 1-9
        for i in range(1, 10):
            btn = tk.Button(btn_frame, text=str(i), width=4, height=2, font=("Arial", 12))
            # Математика для розміщення в 3 колонки:
            # i-1 дає 0..8. Ділення на 3 дає рядок, залишок - стовпець.
            btn.grid(row=(i-1)//3, column=(i-1)%3, padx=2, pady=2)

        # Кнопка 0 (окремо знизу)
        btn_0 = tk.Button(left_panel, text="0", width=14, height=2, font=("Arial", 12))
        btn_0.pack(pady=5)
        
        # Кнопка "Назад в меню" (опціонально)
        btn_back = tk.Button(left_panel, text="Exit", bg="#ffcccc", command=self.back_to_menu)
        btn_back.pack(side=tk.BOTTOM, pady=20)


        # --- ПРАВА ПАНЕЛЬ (Сітка Судоку) ---
        right_panel = tk.Frame(self.game_frame)
        right_panel.pack(side=tk.RIGHT, expand=True)

        self.cells = [[None for _ in range(9)] for _ in range(9)]

        # Малюємо сітку 9x9
        for r in range(9):
            for c in range(9):
                # Додаємо відступи, щоб відділити квадрати 3x3
                pady = (0, 0)
                padx = (0, 0)
                if r % 3 == 0 and r != 0: pady = (5, 0)
                if c % 3 == 0 and c != 0: padx = (5, 0)

                cell = tk.Entry(right_panel, width=2, font=('Arial', 18), justify='center')
                cell.grid(row=r, column=c, padx=padx, pady=pady)
                self.cells[r][c] = cell

    def back_to_menu(self):
        """Повернення назад (видаляє гру, створює меню)"""
        self.game_frame.destroy()
        self.status_label.config(text="System ready.")
        self.create_menu_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = GameInterface(root)
    root.mainloop()