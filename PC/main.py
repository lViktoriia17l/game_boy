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
if name == "main":
    root = tk.Tk()
    SudokuGUI(root)
    root.mainloop()