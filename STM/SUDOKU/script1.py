import serial
import time

# Налаштування порту
port = "COM3"
baudrate = 115200
timeout = 2

try:
   
    ser = serial.Serial(port, baudrate, timeout=timeout)


    data_to_send = bytes([0x01, 5, 0, 2, 0x10])

    print(f"Відправка даних: {[hex(b) for b in data_to_send]}")
    ser.write(data_to_send)


    received_data = ser.read(5)

    if received_data:
        # Дешифруємо
        decoded_list = [hex(b) for b in received_data]
        print(f"Отримано назад: {decoded_list}")
    else:
        print("Помилка: Відповідь не отримана (timeout)")

    ser.close()

except Exception as e:
    print(f"Сталася помилка: {e}")