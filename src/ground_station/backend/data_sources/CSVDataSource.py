import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .DataSource import DataSource

class CSVDataSource(DataSource):
    """Load once, then poll rows in timestamp order without dropping readings.

    Timestamps must be numeric. Units are explicit: 'ms' (default) or 's'.
    Output TIMESTAMP is always milliseconds. Blank values can carry forward.
    A connected source stays connected at EOF; finished distinguishes EOF
    from waiting for the next timestamp. reconnect/restart replays from start.
    """
    class CSVDataSource(DataSource):
        """..."""

        df: pd.DataFrame | None = None

    def __init__(self, file_path: str | Path | None = None, *,
                 timestamp_column: str | None = None, timestamp_unit: str = "ms",
                 realtime: bool = True, speed: float = 1.0,
                 carry_forward: bool = True, trim_launch: bool = False,
                 launch_detector=None):
        if timestamp_unit not in ("ms", "s"):
            raise ValueError("timestamp_unit must be 'ms' or 's'")
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("speed must be finite and positive")
        self.file_path = file_path
        self.timestamp_column = timestamp_column
        self.timestamp_unit = timestamp_unit
        self.realtime = realtime
        self.speed = speed
        self.carry_forward = carry_forward
        self.trim_launch = trim_launch
        self.launch_detector = launch_detector
        self.last_error = None
        self.disconnect()

    # need to correct this error, stating that it's an incompatible override
    # currently forcing it to accept kwargs to fix this error, 
    # but not sure if that is the best way
    def connect(self, file_path: str | Path | None = None, **kwargs) -> bool:
        self.disconnect()
        self.last_error = None
        if file_path is not None:
            self.file_path = file_path
        if self.file_path is None:
            self.last_error = "Choose a CSV file first"
            return False
        try:
            df = pd.read_csv(self.file_path, dtype=str, keep_default_na=False)
            headers = [str(c).strip() for c in df.columns]
            if len(set(headers)) != len(headers):
                raise ValueError("CSV headers must be unique after stripping spaces")
            df.columns = headers
            column = self.timestamp_column
            if column is None:
                column = next((c for c in headers if c.casefold() == "timestamp"), None)
            if column not in headers:
                raise ValueError("CSV needs a timestamp column; set timestamp_column if named differently")
            timestamps = pd.to_numeric(df[column], errors="coerce")
            valid = np.isfinite(timestamps)
            self.skipped_rows = int((~valid).sum())
            df = df.loc[valid].copy()
            df[column] = timestamps.loc[valid] * (1000 if self.timestamp_unit == "s" else 1)
            if df.empty or not np.isfinite(df[column]).all():
                raise ValueError("CSV has no usable finite timestamps")
            df = df.sort_values(column, kind="stable").reset_index(drop=True)
            if column != "TIMESTAMP" and "TIMESTAMP" in df.columns:
                raise ValueError("Selected timestamp column conflicts with TIMESTAMP")
            df = df.rename(columns={column: "TIMESTAMP"})
            if self.trim_launch:
                from .LaunchDetector import LaunchDetector
                detector = self.launch_detector or LaunchDetector()
                df, self.launch_index, self.launch_timestamp = detector.trim_dataframe(df)
            self.df = df
            self._timestamps = df["TIMESTAMP"].to_numpy(dtype=float)
            self.connected = True
            self.restart()
            return True
        except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as exc:
            self.last_error = str(exc)
            self.disconnect()
            return False

    def disconnect(self) -> None:
        self.connected = False
        self.df: pd.DataFrame | None = None
        self.current_index = 0
        self.skipped_rows = 0
        self.launch_index = None
        self.launch_timestamp = None
        self._timestamps = np.array([], dtype=float)
        self._rows = iter(())
        self._started_at = None
        self._last_values = {}

    def restart(self) -> None:
        self.current_index = 0
        self._started_at = None
        self._last_values = {}
        self._rows = self.df.itertuples(index=False, name=None) if self.df is not None else iter(())

    @property
    def finished(self) -> bool:
        return self.connected and self.current_index >= len(self._timestamps)

    def is_connected(self) -> bool:
        return bool(self.connected)

    def get_data(self) -> dict[str, str] | None:
        if not self.connected or self.finished:
            return None
        now = time.monotonic()
        if self._started_at is None:
            self._started_at = now
        due_ms = self._timestamps[self.current_index] - self._timestamps[0]
        if self.realtime and (now - self._started_at) * 1000 * self.speed < due_ms:
            return None
        result = {}
        # columns is coming up as an error, not a known attribute of "none"
        # used a fix from claude for this, we can change it if
        # we decide it's a bad fix later, but it works for now
        df = self.df
        assert df is not None
        for key, value in zip(df.columns, next(self._rows)):
            if key == "TIMESTAMP":
                result[key] = format(float(value), ".15g")
                continue
            text = str(value).strip()
            if text.casefold() in ("", "n/a", "nan", "null", "none"):
                result[key] = self._last_values.get(key, "N/A") if self.carry_forward else "N/A"
            else:
                result[key] = text
                self._last_values[key] = text
        self.current_index += 1
        return result

    def get_available_data(self, max_rows: int = 1000) -> list[dict[str, str]]:
        """Drain up to max_rows due readings; never merge/drop intermediate rows."""
        if max_rows <= 0:
            raise ValueError("max_rows must be positive")
        rows = []
        for _ in range(max_rows):
            row = self.get_data()
            if row is None:
                break
            rows.append(row)
        return rows
