import tkinter as tk
import numpy as np
import serial
import time

try:
    ser = serial.Serial('COM10', 115200, timeout=2)
    print("Порт відкрито успішно.")
except Exception as e:
    print(f"Не вдалося відкрити порт: {e}")
    ser = None


def send_and_receive():
    if ser is None:
        print("Помилка: Порт не доступний!")
        return

    try:

        bytes_to_send = [0x01, 0x00, 0x00, 0x00, 0x01]
        ser.write(bytes(bytes_to_send))
        
        print("\n" + "="*50)
        print(f"---> ВІДПРАВЛЕНО: {[hex(b) for b in bytes_to_send]}")


        time.sleep(0.1)
        received_data = ser.read(84)

        if not received_data:
            print("<--- ПОМИЛКА: Дані не отримано (Timeout)")
            return

        received_list = list(received_data)


        print(f"<--- ОТРИМАНО ({len(received_list)} байт):")
        print(f"HEX формат: {' '.join([f'{b:02X}' for b in received_list])}")
        print(f"DEC формат: {received_list}")
        print("-" * 50)

        matrix_data = received_list[2:83]

        
        if len(matrix_data) < 81:
            print(f"Увага: Отримано лише {len(matrix_data)} байт для матриці. Доповнюємо нулями.")
            matrix_data.extend([0] * (81 - len(matrix_data)))
        elif len(matrix_data) > 81:
            matrix_data = matrix_data[:81]

      
        matrix = np.array(matrix_data).reshape(9, 9)

        for i in range(9):
            for j in range(9):
                val = matrix[i, j]
               
                labels[i][j].config(text=str(val))
                labels[i][j].config(bg="white" if val == 0 else "#e0f0ff")

    except Exception as e:
        print(f"Помилка під час обміну даними: {e}")



root = tk.Tk()
root.title("UART Matrix Viewer")
root.configure(padx=10, pady=10)


button = tk.Button(
    root, 
    text="ОТРИМАТИ ДАНІ З ПОРТУ", 
    command=send_and_receive, 
    height=2, 
    bg="#4CAF50", 
    fg="white", 
    font=("Arial", 10, "bold")
)
button.grid(row=0, column=0, columnspan=9, sticky="we", padx=5, pady=10)


labels = []
for i in range(9):
    row_labels = []
    for j in range(9):
        lbl = tk.Label(
            root, 
            text="0", 
            width=5, 
            height=2, 
            borderwidth=1, 
            relief="solid", 
            font=("Consolas", 11)
        )
        lbl.grid(row=i + 1, column=j, padx=1, pady=1)
        row_labels.append(lbl)
    labels.append(row_labels)


try:
    root.mainloop()
finally:
    if ser and ser.is_open:
        ser.close()
        print("Порт закрито. Програму завершено.")