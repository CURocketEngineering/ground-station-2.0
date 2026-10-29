from tabulate import tabulate
from src.ground_station.backend.data_sources.CSVDataSource import CSVDataSource

source = CSVDataSource(
    file_path="data/flight_data.csv",
    timestamp_unit="ms",
    realtime=False,
)

if source.connect():
    try:
        readings = []

        for _ in range(5):
            reading = source.get_data()
            if reading is None:
                break
            readings.append(reading)

        columns = ["TIMESTAMP", "ACCELEROMETER_X", "ACCELEROMETER_Y", "ACCELEROMETER_Z"]

        print(tabulate(
            [{key: row[key] for key in columns} for row in readings],
            headers="keys",
            tablefmt="simple_grid",
            floatfmt=".3f",
        ))
    finally:
        source.disconnect()
else:
    print("Failed to load CSV:", source.last_error)