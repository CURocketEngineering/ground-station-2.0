import serial
import struct
import yaml


class Radio:

    def __init__(self, port = "/tmp/fake_radio"):
        self.port = port
        self.baudRate = 57600
        self.connected = False
        self.serial = None

        self.raw_data = None
        self.buffer = bytearray()

        self.START_SEQ = b"\x00\x00\x00\x33"
        self.END_SEQUENCE = b"\x00\x00\x00\x34"

        self.data_names = "src/ground_station/backend/data_sources/data_names/data_names_v03.yaml"

        with open(self.data_names) as f:
            items = yaml.safe_load(f)["data_names"]

        self.tags = {item["id"]: item for item in items}


    def connect(self):
        self.serial = serial.Serial(
            self.port, self.baudRate, timeout=0.1
        )
        self.connected = True
        print(f"Connected to radio: {self.port}")

    def disconnect(self):
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False

    def data(self):
        self.raw_data = self.serial.read(
            self.serial.in_waiting or 1
        )

        self.buffer.extend(self.raw_data)
        return self.raw_data

    def decode_payload(self, payload):
        result = {}
        i = 0

        while i < len(payload):

            tag_id = payload[i]
            spec = self.tags.get(tag_id)

            if spec is None:
                break

            axes = 3 if spec.get("type") == "group" else 1
            size = axes * 4

            if i + 1 + size > len(payload):
                break

            values = struct.unpack(
                ">" + "f" * axes,
                payload[i + 1:i + 1 + size]
            )

            if axes == 3:
                components = [
                    self.tags[c]["name"]
                    for c in spec.get("data", [])
                    if c in self.tags
                ]

                for name, value in zip(components, values):
                    result[name] = value
            else:
                result[spec["name"]] = values[0]

            i += 1 + size

        return result

    def decode_raw(self):
        result = {}

        while True:

            start = self.buffer.find(self.START_SEQ)

            if start == -1:
                self.buffer[:] = self.buffer[-3:]
                break

            if start > 0:
                del self.buffer[:start]

            end = self.buffer.find(self.END_SEQUENCE, 12)

            if end == -1:
                break

            timestamp, packet_count = struct.unpack(">II", self.buffer[4:12])

            packet = self.buffer[12:end]

            result.update(self.decode_payload(packet))

            result["TIMESTAMP"] = timestamp
            result["NUM_PACKETS_SENT"] = packet_count

            del self.buffer[:end + 4]

        return result

    def get_data(self):
        self.data()
        return self.decode_raw()