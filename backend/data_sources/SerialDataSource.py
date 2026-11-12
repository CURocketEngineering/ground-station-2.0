import codecs
import math

import serial
from serial.tools import list_ports

from .DataSource import DataSource


class SerialDataSource(DataSource):
    """Serial transport. Generic get_data returns raw TEXT CHUNKS, not packets.

    port can be a device path or pyserial URL (loop:// is useful for practice).
    connect() requires an explicit port: opening a port does not identify a radio.
    """

    def __init__(self, baudrate: int = 115200, timeout: float = 0,
                 port: str | None = None, write_timeout: float = 1.0):
        if baudrate <= 0 or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("baudrate must be positive; timeout finite and nonnegative")
        if not math.isfinite(write_timeout) or write_timeout < 0:
            raise ValueError("write_timeout must be finite and nonnegative")
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.port = port
        self.ser = None
        self.last_error = None
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    @staticmethod
    def get_available_ports() -> list[str]:
        return [p.device for p in list_ports.comports()]

    def connect(self, port: str | None = None) -> bool:
        self.disconnect()
        if port is not None:
            self.port = port
        self.last_error = None
        if not self.port:
            self.last_error = "Choose a serial port first"
            return False
        try:
            self.ser = serial.serial_for_url(
                self.port, baudrate=self.baudrate, timeout=self.timeout,
                write_timeout=self.write_timeout)
            return True
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            except (serial.SerialException, OSError) as exc:
                self.last_error = str(exc)
        self.ser = None
        self._decoder.reset()

    def is_connected(self) -> bool:
        return bool(self.ser is not None and self.ser.is_open)

    def read_bytes(self, max_bytes: int = 65536) -> bytes:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if not self.is_connected():
            return b""
        try:
            available = min(self.ser.in_waiting, max_bytes)
            return self.ser.read(available) if available else b""
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            self.disconnect()
            return b""

    def read_response(self) -> str:
        return self._decoder.decode(self.read_bytes())

    def get_data(self) -> dict[str, str] | None:
        response = self.read_response()
        return {"raw_data": response} if response else None

    def send_command(self, command: str, add_newline: bool = True) -> bool:
        if not self.is_connected():
            self.last_error = "Source is disconnected"
            return False
        payload = (command + ("\n" if add_newline else "")).encode("utf-8")
        try:
            written = self.ser.write(payload)
            if written != len(payload):
                self.last_error = "Only part of the command was written"
                return False
            self.last_error = None
            return True
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            self.disconnect()
            return False

    def clear_buffer(self) -> None:
        self._decoder.reset()
        if self.is_connected():
            try:
                self.ser.reset_input_buffer()
            except (serial.SerialException, OSError) as exc:
                self.last_error = str(exc)
                self.disconnect()
