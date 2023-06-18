import logging
import time
import threading

from ICD import cv_structs
from communication.udp_communicator import Communicator

if __name__=='__main__':
    
    # Set logger
    logger = logging.getLogger("Client Simulator")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(clear_with_time_msec_format)
    logger.addHandler(ch)
    logger.info("Welcome to Client Simulator")
    
    receive_reports_channel = ("127.0.0.1", 5101)
    send_cmds_channel = ("127.0.0.1", 5100)

    def parse_msg_callback(item):
        print(f"Got {item}")

    communicator = Communicator(logger, receive_reports_channel, send_cmds_channel, parse_msg_callback, print_received= True)
    communicator.start_receiver_thread() # Start receiver loop

    # Simulate sending
    def simulate_status_loop():
        for frame_number in range(2):
            status_msg = cv_structs.create_status(frame_number, frame_number+100)
            communicator.send_ctypes_msg(status_msg)
            time.sleep(2.5)

    send_thread = threading.Thread(target=simulate_status_loop)
    send_thread.start()
