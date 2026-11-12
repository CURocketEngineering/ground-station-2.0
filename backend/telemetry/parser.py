import math
import struct
import time
from collections import Counter

from .packet import PacketField, TelemetryPacket


# Provisional registry from legacy data_names_v03.yaml. Verify against firmware.
_SCALARS = (
    "ACCELEROMETER_X", "ACCELEROMETER_Y", "ACCELEROMETER_Z",
    "GYROSCOPE_X", "GYROSCOPE_Y", "GYROSCOPE_Z", "TEMPERATURE",
    "PRESSURE", "ALTITUDE", "MAGNETOMETER_X", "MAGNETOMETER_Y",
    "MAGNETOMETER_Z", "MEDIAN_ACCELERATION_SQUARED", "CYCLE_RATE",
    "TIMESTAMP", "STATE_CHANGE", "FLIGHT_ID", "EST_APOGEE",
    "EST_VERTICAL_VELOCITY", "EST_ALTITUDE", "BATT",
    "FIN_DEPLOYMENT_AMOUNT", "TIME_TO_APOGEE", "CURRENT_STATE",
)
LEGACY_FIELDS = {tag: (name,) for tag, name in enumerate(_SCALARS)}
LEGACY_FIELDS.update({102: _SCALARS[0:3], 105: _SCALARS[3:6], 111: _SCALARS[9:12]})


class PacketParser:
    """Incremental MARTHA 1.4 framing; provisional big-endian float32 values.

    One owner/thread. No I/O, cached readings, or GUI dependencies.
    Call feed(b'') periodically to expire an incomplete candidate on idle.
    Structural validation cannot detect every corruption without a checksum.
    """

    START = b"\x00\x00\x00\x33"
    END = b"\x00\x00\x00\x34"
    MAX_PACKET = 120

    def __init__(self, fields=None, *, partial_timeout=1.0):
        if not math.isfinite(partial_timeout) or partial_timeout <= 0:
            raise ValueError("partial_timeout must be finite and positive")
        self.fields = {}
        for tag, names in (LEGACY_FIELDS if fields is None else fields).items():
            if type(tag) is not int or not 0 <= tag <= 255:
                raise ValueError("Tags must be integers from 0 through 255")
            if not isinstance(names, (list, tuple)) or len(names) not in (1, 3):
                raise ValueError("Each tag needs one scalar name or three axis names")
            if not all(isinstance(name, str) and name.strip() for name in names):
                raise ValueError("Field names must be nonempty strings")
            self.fields[tag] = (tuple(names), struct.Struct(">" + "f" * len(names)))
        if not self.fields:
            raise ValueError("Field registry cannot be empty")
        self.partial_timeout = partial_timeout
        self.buffer = bytearray()
        self.stats = Counter()
        self.last_error = None
        self._last_received = None

    def _reject(self, reason):
        self.stats[reason] += 1
        self.last_error = reason
        del self.buffer[:1]

    def feed(self, chunk: bytes, *, now=None) -> list[TelemetryPacket]:
        now = time.monotonic() if now is None else now
        # Expire old bytes before joining them to a new arrival.
        if (self.buffer and self._last_received is not None
                and now - self._last_received >= self.partial_timeout):
            self.stats["expired_bytes"] += len(self.buffer)
            self.buffer.clear()
            self.stats["timeouts"] += 1
            self.last_error = "partial_frame_timeout"
        packets = []
        # Process bounded slices even if a caller supplies a huge capture.
        for offset in range(0, len(chunk), 4096):
            part = chunk[offset:offset + 4096]
            self.stats["bytes_received"] += len(part)
            self._last_received = now
            self.buffer.extend(part)
            packets.extend(self._drain())
        return packets

    def _drain(self):
        packets = []
        while self.buffer:
            start = self.buffer.find(self.START)
            if start < 0:
                discard = max(0, len(self.buffer) - 3)
                self.stats["discarded_bytes"] += discard
                del self.buffer[:discard]
                break
            if start:
                self.stats["discarded_bytes"] += start
                del self.buffer[:start]
            if len(self.buffer) < 12:
                break
            timestamp, count = struct.unpack_from(">II", self.buffer, 4)
            cursor, fields = 12, []
            while True:
                if cursor + 4 > self.MAX_PACKET:
                    self._reject("oversized_frames")
                    break
                if len(self.buffer) < cursor + 4:
                    return packets
                marker = self.buffer[cursor:cursor + 4]
                if marker == self.END:
                    end = cursor + 4
                    packets.append(TelemetryPacket(timestamp, count, tuple(fields),
                                                   bytes(self.buffer[:end])))
                    del self.buffer[:end]
                    self.stats["packets"] += 1
                    break
                if marker == self.START:
                    self._reject("truncated_frames")
                    break
                tag = self.buffer[cursor]
                definition = self.fields.get(tag)
                if definition is None:
                    self._reject("unknown_tags")
                    self.last_error = f"unknown_tag_{tag}"
                    break
                names, decoder = definition
                end = cursor + 1 + decoder.size
                if end + 4 > self.MAX_PACKET:
                    self._reject("oversized_frames")
                    break
                if len(self.buffer) < end:
                    return packets
                values = decoder.unpack_from(self.buffer, cursor + 1)
                if not all(math.isfinite(value) for value in values):
                    self._reject("nonfinite_fields")
                    break
                fields.append(PacketField(tag, names, values))
                cursor = end
        return packets
