from backend.data.fake_radio import main as radio
from backend.IncomingData.IncomingData import incoming_data

import threading
import time


def test_radio_with_fake():
    D = incoming_data()

    thread1 = threading.Thread(target=radio)
    thread2 = threading.Thread(target=D.test2)


    print("starting radio")
    thread1.start()
    time.sleep(1)
    print("starting connection")
    thread2.start()

    thread1.join()
    thread2.join()

    print("\nBoth threads finished\n")

def test_with_real_radio():
    D = incoming_data()
    D.test2()

#test_with_real_radio()
test_radio_with_fake()