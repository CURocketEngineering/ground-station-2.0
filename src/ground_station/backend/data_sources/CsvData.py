import time
import pandas as pd


class CSVSource:

    def __init__(self):
        self.path = "src/ground_station/backend/data_sources/data_11-06-26_16-50-20.csv"
        self.realtime = True
        self.speed = 1.0
        self.connected = False

        self.rows = []
        self.index = 0
        self.start_time = None
        self.last_values = {}

    def connect(self):
        df = pd.read_csv(self.path)
        df.columns = [c.strip() for c in df.columns]
        df = df.dropna(subset=["TIMESTAMP"])
        df = df.sort_values("TIMESTAMP", kind="stable")

        self.rows = df.to_dict("records")
        self.restart()
        self.connected = True
        print(f"Connected to csv: {self.path} ({len(self.rows)} rows)")

    def disconnect(self):
        self.rows = []
        self.index = 0
        self.connected = False

    def restart(self):
        self.index = 0
        self.start_time = None
        self.last_values = {}

    def is_connected(self):
        return self.connected

    @property
    def finished(self):
        return self.index >= len(self.rows)

    def get_data(self):
        if not self.connected or self.finished:
            return {}

        row = self.rows[self.index]

        # block until this row's timestamp is due (like the radio's serial read)
        if self.realtime:
            now = time.monotonic()
            if self.start_time is None:
                self.start_time = now
            due_ms = row["TIMESTAMP"] - self.rows[0]["TIMESTAMP"]
            elapsed_ms = (now - self.start_time) * 1000 * self.speed
            if elapsed_ms < due_ms:
                time.sleep((due_ms - elapsed_ms) / 1000 / self.speed)

        # blank cells (NaN) carry forward the last known value
        result = {}
        for name, value in row.items():
            if pd.isna(value):
                if name in self.last_values:
                    result[name] = self.last_values[name]
            else:
                result[name] = value
                self.last_values[name] = value

        self.index += 1
        return result