from dataclasses import dataclass


@dataclass(frozen=True)
class PacketField:
    tag: int
    names: tuple[str, ...]
    values: tuple[float, ...]


@dataclass(frozen=True)
class TelemetryPacket:
    timestamp_raw: int
    packet_count: int
    fields: tuple[PacketField, ...]
    raw_frame: bytes

    def get_fields(self, tag: int) -> tuple[PacketField, ...]:
        """Preserve repeated tags rather than silently overwriting them."""
        return tuple(field for field in self.fields if field.tag == tag)
