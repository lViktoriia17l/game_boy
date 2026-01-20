import serial
import threading
import time

# ================= CMD =================
CMD_START     = 0x01
CMD_RESTART   = 0x02
CMD_GIVEUP    = 0x03
CMD_SET       = 0x04
CMD_CLEAR     = 0x05
CMD_CLEARALL  = 0x06
CMD_FIELD     = 0x07

# ================= STATUS =================
STATUS_OK       = 0x10
STATUS_INVALID  = 0x11
STATUS_LOCKED   = 0x12
STATUS_CHKERR   = 0x13
STATUS_LOSE     = 0x14
STATUS_WIN      = 0x15

STATUS_TEXT = {
    STATUS_OK:      "OK",
    STATUS_INVALID: "INVALID",
    STATUS_LOCKED:  "LOCKED",
    STATUS_LOSE:    "YOU LOSE",
    STATUS_WIN:     "YOU WIN",
    STATUS_CHKERR:  "CHECKSUM ERROR"
}

# ================= UART GAME CONTROLLER =================
class UARTSudokuGame:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=0.1)
        self.running = True

        # -------- callbacks (ПОДІЇ) --------
        self.on_field      = None   # def f(field_9x9)
        self.on_status     = None   # def f(text)
        self.on_win        = None
        self.on_lose       = None
        self.on_invalid    = None
        self.on_locked     = None

        self.rx_thread = threading.Thread(
            target=self._rx_loop, daemon=True
        )
        self.rx_thread.start()

    # ================= UTILS =================
    @staticmethod
    def xor(data):
        c = 0
        for b in data:
            c ^= b
        return c & 0xFF

    # ================= SEND =================
    def _send(self, cmd, b1=0, b2=0, b3=0):
        pkt = bytes([cmd, b1, b2, b3, cmd ^ b1 ^ b2 ^ b3])
        self.ser.write(pkt)

    def start_game(self):
        self._send(CMD_START)

    def restart_game(self):
        self._send(CMD_RESTART)

    def give_up(self):
        self._send(CMD_GIVEUP)

    def request_field(self):
        self._send(CMD_FIELD)

    def clear_all(self):
        self._send(CMD_CLEARALL)

    def set_cell(self, r, c, v):
        self._send(CMD_SET, r, c, v)

    def clear_cell(self, r, c):
        self._send(CMD_CLEAR, r, c, 0)

    # ================= RX =================
    def _rx_loop(self):
        while self.running and self.ser.is_open:
            try:
                first = self.ser.read(1)
                if not first:
                    continue

                cmd = first[0]

                # -------- FIELD --------
                if cmd == CMD_FIELD:
                    payload = self.ser.read(82)
                    if len(payload) != 82:
                        continue

                    status = payload[0]
                    field  = payload[1:82]
                    chk    = payload[81]

                    if chk != self.xor([cmd, status, *field]):
                        self._emit_status(STATUS_CHKERR)
                        continue

                    self._handle_field(status, field)

                # -------- SHORT --------
                else:
                    payload = self.ser.read(5)
                    if len(payload) != 5:
                        continue

                    status, b1, b2, b3, chk = payload

                    if chk != (cmd ^ status ^ b1 ^ b2 ^ b3):
                        self._emit_status(STATUS_CHKERR)
                        continue

                    self._handle_status(status)

            except serial.SerialException:
                break

    # ================= HANDLERS =================
    def _handle_field(self, status, field):
        # поле 81 → 9x9
        matrix = [
            list(field[i*9:(i+1)*9]) for i in range(9)
        ]

        if self.on_field:
            self.on_field(matrix)

        if status == STATUS_WIN and self.on_win:
            self.on_win()

        elif status == STATUS_LOSE and self.on_lose:
            self.on_lose()

        elif status == STATUS_INVALID and self.on_invalid:
            self.on_invalid()

        elif status == STATUS_LOCKED and self.on_locked:
            self.on_locked()

        elif status != STATUS_OK:
            self._emit_status(status)

def _handle_status(self, status):
    if status == STATUS_INVALID and self.on_invalid:
        self.on_invalid()
    elif status == STATUS_LOCKED and self.on_locked:
        self.on_locked()
    elif status == STATUS_WIN and self.on_win:
        self.on_win()
    elif status == STATUS_LOSE and self.on_lose:
        self.on_lose()
    else:
        self._emit_status(status)

def _emit_status(self, status):
    if self.on_status:
        self.on_status(STATUS_TEXT.get(status, "UNKNOWN"))

# ================= CLOSE =================
def close(self):
    self.running = False
    time.sleep(0.1)
    if self.ser.is_open:
        self.ser.close()
