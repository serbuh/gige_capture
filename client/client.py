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

        receive_reports_channel = ("127.0.0.1", 5101)
        send_cmds_channel = ("127.0.0.1", 5100)

        self.communicator = Communicator(logger, receive_reports_channel, send_cmds_channel, handle_msg)
        self.communicator.start_receiver_thread() # Start receiver loop

    def init_gui(self):
        def print_text():
            text = fps_textbox.get("1.0", "end-1c")
            print(text)

        # Create the main window
        window = tk.Tk()

        # Create the button
        fps_button = tk.Button(window, text="Change FPS", command=print_text)
        fps_button.grid(row=0, column=0)

        # Create the textbox
        fps_textbox = tk.Text(window, height=1)
        fps_textbox.grid(row=0, column=1)

        window.mainloop()


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
