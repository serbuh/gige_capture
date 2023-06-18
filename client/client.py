import logging
import time
import threading

from ICD import cv_structs
from communication.udp_communicator import Communicator

import tkinter as tk

class Client():
    def __init__(self, logger):
        self.logger = logger

        def handle_msg(msg):
            print(f"Got {msg}")

        receive_reports_channel = ("127.0.0.1", 5111)
        send_cmds_channel = ("127.0.0.1", 5100)

        self.communicator = Communicator(logger, receive_reports_channel, send_cmds_channel, handle_msg)
        self.communicator.start_receiver_thread() # Start receiver loop

    def init_gui(self):
        # Create the main window
        window = tk.Tk()

        # Create the button
        fps_button = tk.Button(window, text="Change FPS", command=self.change_fps)
        fps_button.grid(row=0, column=0)

        # Create the textbox
        self.fps_1_textbox = tk.Text(window, height=1, width=10)
        self.fps_1_textbox.grid(row=0, column=1)

        self.fps_2_textbox = tk.Text(window, height=1, width=10)
        self.fps_2_textbox.grid(row=0, column=2)

        window.mainloop()
    
    def change_fps(self):
        fps_1 = int(self.fps_1_textbox.get("1.0", "end-1c"))
        fps_2 = int(self.fps_2_textbox.get("1.0", "end-1c"))
        print(f"New FPS: {fps_1}, {fps_2}")
        cv_command = cv_structs.create_cv_command(fps_1, fps_2, bitrateKBs_1=1000, bitrateKBs_2=1000, active_sensor=1)
        self.communicator.send_ctypes_msg(cv_command)


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
    
    
    client = Client(logger)
    client.init_gui()
    
    logger.info("Bye")
