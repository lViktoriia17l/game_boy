# game_boy
sudoku game test git
# ===== Checksum =====
def checksum(cmd,data):
    s = cmd + len(data)
    for b in data:
        s += b
    return s & 0xFF



# ===== Protocol =====
STX = 0x55
ETX = 0xAA

CMD_START    = 0x01
CMD_RESTART  = 0x02
CMD_GIVEUP   = 0x03
CMD_SET      = 0x10
CMD_CLEAR    = 0x11
CMD_CLEARALL = 0x12
CMD_FIELD    = 0x20
CMD_STATUS   = 0x21
CMD_TIMER    = 0x30

STATUS_OK      = 0x00
STATUS_INVALID = 0x06
STATUS_LOCKED  = 0x07
STATUS_CHKERR  = 0x08
STATUS_LOSE    = 0x04
STATUS_WIN     = 0x05
