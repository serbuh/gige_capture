
# should run with sudo per

import serial

def do_NUC():
    def open_serial_connection(port, baud):
        s = serial.Serial()
        s.port = port
        s.baudrate = baud
        s.open()
        s.flushInput()
        s.flushOutput()
        return s

    def write_read_cmd(con, cmd_write, cmd_read):
        con.write(bytearray.fromhex(cmd_write))
        data = con.read(int(len(cmd_read) / 2))
        if data.hex() == cmd_read:
            return True
        return False

    def init(con):
        cmd_write = 'aa11f0000055'
        cmd_read = '5511f00b00013800120c0e05030c4001e5'
        return write_read_cmd(con, cmd_write, cmd_read)

    def nuc(con):
        cmd_write = 'aa1685040010000000a7'
        cmd_read = '551685000010'
        return write_read_cmd(con, cmd_write, cmd_read)
    

    serial_connection = open_serial_connection('/dev/ttyUSB0', 115200)
    init(serial_connection)
    nuc(serial_connection)

if __name__ == "__main__":
    do_NUC()
   