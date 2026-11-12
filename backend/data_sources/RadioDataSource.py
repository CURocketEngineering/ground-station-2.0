import struct
from collections import deque

from .SerialDataSource import SerialDataSource


class RadioDataSource(SerialDataSource):
    """Framed radio parser using the format in the OLD RadioDataSource.py.

    Wire: 00 00 00 33 | uint32 timestamp | uint32 sequence |
    repeated (uint8 ID + float32 scalar or group components) | 00 00 00 34.
    All multibyte values are big endian. No checksum exists in this format.
    field_definitions must describe ALL IDs emitted by the transmitter:
    [{'id': 8, 'name': 'ALT'},
     {'id': 102, 'name': 'ACCL', 'components': ['ACCL_X','ACCL_Y','ACCL_Z']}]
    IDs/names above are examples, not verified transmitter definitions.
    The separate legacy 0x51/0x52 format is intentionally not guessed here.
    """

    START_SEQUENCE = b"\x00\x00\x00\x33"
    END_SEQUENCE = b"\x00\x00\x00\x34"
    MAX_RX_BUFFER_BYTES = 65536

    def __init__(self, field_definitions, baudrate=57600, timeout=0,
                 port=None, write_timeout=1.0):
        super().__init__(baudrate, timeout, port, write_timeout)
        self.fields = {}
        output_names = {"TIMESTAMP", "NUM_PACKETS_SENT"}
        for field in field_definitions:
            identifier = field["id"]
            if not isinstance(identifier, int) or not 0 <= identifier <= 255 or identifier in self.fields:
                raise ValueError("Radio IDs must be unique bytes (0..255)")
            names = list(field.get("components") or [field["name"]])
            if not all(isinstance(n, str) and n for n in names) or len(names) != len(set(names)):
                raise ValueError("Component names must be unique nonempty strings")
            if set(names) & output_names:
                raise ValueError("Radio output names must be unique and cannot replace header fields")
            output_names.update(names)
            self.fields[identifier] = (names, struct.Struct(">" + "f" * len(names)))
        if not self.fields:
            raise ValueError("Provide the transmitter field definitions first")
        self._rx_buffer = bytearray()
        self.latest_data = {}
        self._packet_window = deque(maxlen=100)
        self._last_packet_number = None
        self.dropped_bytes = 0
        self.malformed_packets = 0

    def disconnect(self):
        super().disconnect()
        # Also called by the inherited connect() before opening a new port.
        if hasattr(self, "_rx_buffer"):
            self._rx_buffer.clear()
            self.latest_data.clear()
            self._packet_window.clear()
            self._last_packet_number = None
            self.dropped_bytes = 0
            self.malformed_packets = 0

    def feed_bytes(self, data: bytes) -> None:
        """Feed raw bytes without hardware, then call get_data() to parse them."""
        self._rx_buffer.extend(data)
        overflow = len(self._rx_buffer) - self.MAX_RX_BUFFER_BYTES
        if overflow > 0:
            del self._rx_buffer[:overflow]
            self.dropped_bytes += overflow

    def get_data(self) -> dict[str, str] | None:
        if self.is_connected():
            self.feed_bytes(self.read_bytes())
        # One complete packet per call, including when bytes are already buffered.
        # Return None on idle; latest_data remains available as a snapshot.
        while self._align():
            if len(self._rx_buffer) < 12:
                return None
            timestamp, sequence = struct.unpack_from(">II", self._rx_buffer, 4)
            cursor = 12
            result = {"TIMESTAMP": str(timestamp), "NUM_PACKETS_SENT": str(sequence)}
            while True:
                if len(self._rx_buffer) - cursor < 4:
                    return None
                marker = self._rx_buffer[cursor:cursor + 4]
                if marker == self.END_SEQUENCE:
                    del self._rx_buffer[:cursor + 4]
                    self._update_packet_retention(sequence)
                    self.latest_data.update(result)
                    return dict(self.latest_data)
                # A fresh header at a field boundary means a truncated packet.
                if marker == self.START_SEQUENCE:
                    del self._rx_buffer[:cursor]
                    self.malformed_packets += 1
                    break
                identifier = self._rx_buffer[cursor]
                definition = self.fields.get(identifier)
                if definition is None:
                    # Unknown group sizes cannot safely be guessed as scalars.
                    self.last_error = f"Unknown radio ID {identifier}; verify field definitions"
                    self.malformed_packets += 1
                    del self._rx_buffer[:1]
                    break
                names, decoder = definition
                if len(self._rx_buffer) < cursor + 1 + decoder.size:
                    return None
                values = decoder.unpack_from(self._rx_buffer, cursor + 1)
                result.update(zip(names, (str(v) for v in values)))
                cursor += 1 + decoder.size
        return None

    def _align(self) -> bool:
        index = self._rx_buffer.find(self.START_SEQUENCE)
        if index < 0:
            excess = max(0, len(self._rx_buffer) - 3)
            if excess:
                self.dropped_bytes += excess
                del self._rx_buffer[:excess]
            return False
        if index:
            self.dropped_bytes += index
            del self._rx_buffer[:index]
        return True

    def _update_packet_retention(self, sequence):
        if self._last_packet_number is not None:
            delta = (sequence - self._last_packet_number) & 0xFFFFFFFF
            if delta == 0:
                return  # duplicate
            if delta >= 0x80000000:
                # Backwards counter: transmitter restart or out-of-order data.
                self._packet_window.clear()
            else:
                # At most 100 appends even on huge sequence jumps.
                self._packet_window.extend([0] * min(delta - 1, 100))
        self._packet_window.append(1)
        self._last_packet_number = sequence

    def get_packet_retention_ratio(self) -> float:
        return sum(self._packet_window) / len(self._packet_window) if self._packet_window else 1.0
