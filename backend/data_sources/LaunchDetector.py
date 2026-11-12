import math

import numpy as np
import pandas as pd


class LaunchDetector:
    """Optional replay trimming heuristic, not flight control logic.

    Input: sorted DataFrame with TIMESTAMP in milliseconds, acceleration in
    m/s² by default. Uses the first available axis unless acceleration_column
    is given. Confirm the axis/units for your recordings before enabling it.
    Returns the original sorted-row launch index (None when undetected).
    """

    def __init__(self, threshold_g=2.0, window_size=5, pre_launch_seconds=10,
                 sustained_samples=3, acceleration_column=None,
                 acceleration_unit="m/s2"):
        if (not math.isfinite(threshold_g) or threshold_g <= 0
                or not math.isfinite(pre_launch_seconds) or pre_launch_seconds < 0):
            raise ValueError("Invalid threshold or pre-launch duration")
        if not isinstance(window_size, int) or not isinstance(sustained_samples, int) or min(window_size, sustained_samples) < 1:
            raise ValueError("Window and sustained sample count must be positive integers")
        if acceleration_unit not in ("m/s2", "g"):
            raise ValueError("acceleration_unit must be 'm/s2' or 'g'")
        self.threshold_g = threshold_g
        self.window_size = window_size
        self.pre_launch_seconds = pre_launch_seconds
        self.sustained_samples = sustained_samples
        self.acceleration_column = acceleration_column
        self.acceleration_unit = acceleration_unit

    def trim_dataframe(self, df: pd.DataFrame):
        candidates = [self.acceleration_column] if self.acceleration_column else [
            "ACCELEROMETER_Z", "ACCL_Z", "ACCLZ", "ACCELEROMETER_X",
            "ACCL_X", "ACCLX", "ACCELEROMETER_Y", "ACCL_Y", "ACCLY"]
        column = next((c for c in candidates if c in df and
                       pd.to_numeric(df[c], errors="coerce").notna().any()), None)
        if column is None:
            return df, None, None
        accel = pd.to_numeric(df[column], errors="coerce").abs()
        if self.acceleration_unit == "m/s2":
            accel = accel / 9.80665
        # Missing samples interrupt sustained detection rather than filling them.
        smooth = accel.rolling(self.window_size, min_periods=self.window_size).mean()
        mask = (smooth > self.threshold_g).astype(int)
        sustained = mask.rolling(self.sustained_samples).sum() >= self.sustained_samples
        positions = np.flatnonzero(sustained.to_numpy())
        if not len(positions):
            return df, None, None
        index = int(positions[0]) - self.sustained_samples + 1
        timestamp = float(df["TIMESTAMP"].iloc[index])
        trimmed = df.loc[df["TIMESTAMP"] >= timestamp - self.pre_launch_seconds * 1000]
        return trimmed.reset_index(drop=True), index, timestamp
