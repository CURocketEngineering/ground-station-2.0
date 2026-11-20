from ..data_sources import RadioData as Data

from ..data_sources import CsvData as CSV
import time

class incoming_data():
    def __init__(self):
        self.ACCELEROMETER_X = None
        self.ACCELEROMETER_Y = None
        self.ACCELEROMETER_Z = None
        self.ACCELEROMETER = None
        self.GYROSCOPE_X = None
        self.GYROSCOPE_Y = None
        self.GYROSCOPE_Z = None
        self.GYROSCOPE = None
        self.TEMPERATURE = None
        self.PRESSURE = None
        self.ALTITUDE = None
        self.MAGNETOMETER_X = None
        self.MAGNETOMETER_Y = None
        self.MAGNETOMETER_Z = None
        self.MAGNETOMETER = None
        self.MEDIAN_ACCELERATION_SQUARED = None
        self.CYCLE_RATE = None
        self.TIMESTAMP = None
        self.STATE_CHANGE = None
        self.FLIGHT_ID = None
        self.EST_APOGEE = None
        self.EST_VERTICAL_VELOCITY = None
        self.EST_ALTITUDE = None
        self.BATT = None
        self.FIN_DEPLOYMENT_AMOUNT = None
        self.TIME_TO_APOGEE = None
        self.CURRENT_STATE = None
        self.NUM_PACKETS_SENT = None
        self.PITCH = None
        self.ROLL = None
        self.YAW = None
        self.ORIENTATION = None
        self.EXTERNAL_SPI = None

    #change the object to change the data source
    def update_data(self, ClassObject):
        data = ClassObject.get_data()

        if not data:
            return

        for name, value in data.items():
            if hasattr(self, name):
                setattr(self, name, value)

        # Build combined vectors
        self.ACCELEROMETER = (
            self.ACCELEROMETER_X,
            self.ACCELEROMETER_Y,
            self.ACCELEROMETER_Z
        )

        self.GYROSCOPE = (
            self.GYROSCOPE_X,
            self.GYROSCOPE_Y,
            self.GYROSCOPE_Z
        )

        self.MAGNETOMETER = (
            self.MAGNETOMETER_X,
            self.MAGNETOMETER_Y,
            self.MAGNETOMETER_Z
        )

        self.ORIENTATION = (
            self.PITCH,
            self.ROLL,
            self.YAW
        )




    def print_data(self):
        print("\n========== INCOMING TELEMETRY ==========")

        print("\n--- Accelerometer ---")
        print(f"X: {self.ACCELEROMETER_X}")
        print(f"Y: {self.ACCELEROMETER_Y}")
        print(f"Z: {self.ACCELEROMETER_Z}")
        print(f"Combined: {self.ACCELEROMETER}")

        print("\n--- Gyroscope ---")
        print(f"X: {self.GYROSCOPE_X}")
        print(f"Y: {self.GYROSCOPE_Y}")
        print(f"Z: {self.GYROSCOPE_Z}")
        print(f"Combined: {self.GYROSCOPE}")

        print("\n--- Magnetometer ---")
        print(f"X: {self.MAGNETOMETER_X}")
        print(f"Y: {self.MAGNETOMETER_Y}")
        print(f"Z: {self.MAGNETOMETER_Z}")
        print(f"Combined: {self.MAGNETOMETER}")

        print("\n--- Environmental ---")
        print(f"Temperature: {self.TEMPERATURE}")
        print(f"Pressure: {self.PRESSURE}")
        print(f"Altitude: {self.ALTITUDE}")
        print(f"EXTERNAL_SPI: {self.EXTERNAL_SPI}")

        print("\n--- Flight Estimates ---")
        print(f"Estimated Apogee: {self.EST_APOGEE}")
        print(f"Vertical Velocity: {self.EST_VERTICAL_VELOCITY}")
        print(f"Estimated Altitude: {self.EST_ALTITUDE}")
        print(f"Time to Apogee: {self.TIME_TO_APOGEE}")

        print("\n--- Orientation ---")
        print(f"Pitch: {self.PITCH}")
        print(f"Roll: {self.ROLL}")
        print(f"Yaw: {self.YAW}")
        print(f"Orientation: {self.ORIENTATION}")

        print("\n--- Flight Status ---")
        print(f"Current State: {self.CURRENT_STATE}")
        print(f"State Change: {self.STATE_CHANGE}")
        print(f"Flight ID: {self.FLIGHT_ID}")
        print(f"Fin Deployment: {self.FIN_DEPLOYMENT_AMOUNT}")

        print("\n--- System ---")
        print(f"Battery: {self.BATT}")
        print(f"Cycle Rate: {self.CYCLE_RATE}")
        print(f"Timestamp: {self.TIMESTAMP}")
        print(f"Packets Sent: {self.NUM_PACKETS_SENT}")
        print(f"Median Acceleration Squared: {self.MEDIAN_ACCELERATION_SQUARED}")

        print("\n========================================\n")

    #debug
    def print_raw():
        R = Data.Radio()
        
        R.connect()

        try:
            while True:
                raw = R.data()

                if raw:
                    print("Raw bytes:", raw)
                    print("Hex:", raw.hex(" "))
                    print("Length:", len(raw))
                    print("-------------------------")

        except KeyboardInterrupt:
            print("Stopping reader.")

        finally:
            R.disconnect()

    def test(self, r):
        print(r.get_data())

    def test2(self):
        try:
            R = Data.Radio()
            R.connect()
            while True:
                self.update_data(R)
                self.print_data()

        except:
            print("radio has stopped")
            R.disconnect()
        
# R = Data.Radio()
# C = CSV.CSVSource()
I = incoming_data()
# #C.connect()
# R.connect()
# for i in range(1, 800):
#     I.update_data(R)
#     I.print_data()
#     #I.test(R)
