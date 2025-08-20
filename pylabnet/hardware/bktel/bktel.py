import serial
from pylabnet.utils.logging.logger import LogHandler


class Driver:
    READ_TIMEOUT_S = 1.0
    WRITE_TIMEOUT_S = 1.0

    def __init__(self, port, baud, logger=None):
        self.port = port
        self.baud = int(baud)
        self.log = LogHandler(logger=logger)
        self.ser = None
        try:
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=self.READ_TIMEOUT_S,
                write_timeout=self.WRITE_TIMEOUT_S,
            )
            self.log.info(f"Connected to {self.port} @ {self.baud} baud")
        except Exception as e:
            msg = f"Serial open failed on {self.port}: {e}"
            self.log.error(msg)
            print(msg)

    def close(self):
        try:
            if self.ser and self.ser.is_open:
                self.log.info("Close requested — keeping serial port open.")
            else:
                self.log.info("Close requested — port already not open.")
        except Exception as e:
            self.log.error(f"Close check failed: {e}")

    def force_close(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.log.info("Serial port forcibly closed.")
                return True
        except Exception as e:
            self.log.error(f"Serial force_close failed: {e}")
        return False

    def read_ra(self):
        return self._send("RA")

    def read_rmode(self):
        return self._send("RMODE")

    def read_rpc(self):
        return self._send("RPC")

    def smode_off(self):
        return self._send("SMODE OFF")

    def smode_pc(self):
        return self._send("SMODE PC")

    def set_spc(self, value):
        cmd = f"SPC {float(value):.2f}"
        return self._send(cmd)

    def _send(self, cmd):
        if not self.ser or not self.ser.is_open:
            msg = "Serial port not open."
            self.log.error(msg)
            print(msg)
            return ""
        try:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + "\r\n").encode())
            resp = self.ser.read(4096)
            text = resp.decode(errors="replace").strip() if resp else ""
            if text:
                self.log.info(f"{cmd} -> {text}")
            else:
                self.log.info(f"{cmd} -> <no response>")
            return text
        except Exception as e:
            msg = f"Communication failed during '{cmd}': {e}"
            self.log.error(msg)
            print(msg)
            return ""
