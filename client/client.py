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
            self.logger.info(f">> Got:\n{msg}") # Client

        receive_reports_channel = ("127.0.0.1", 5111)
        send_cmds_channel = ("127.0.0.1", 5100)

        self.communicator = Communicator(logger, receive_reports_channel, send_cmds_channel, handle_msg)
        self.communicator.start_receiver_thread() # Start receiver loop

    def init_gui(self):
        # Create the main window
        window = tk.Tk()

        self.fps_1_stringvar, self.fps_2_stringvar, \
        self.bitrate_1_stringvar, self.bitrate_2_stringvar, \
        self.active_cam_1_intvar, self.active_cam_2_intvar = \
            self.create_command_frame(window, frame_row=0, frame_column=0)

        window.mainloop()

    def create_command_frame(self, window, frame_row, frame_column):
        # Create a frame
        command_frame = tk.Frame(window)
        command_frame.grid(row=frame_row, column=frame_column)

        # Create the button
        command_button = tk.Button(command_frame, text="Send command", command=self.change_cam_params)
        command_button.grid(row=0, column=0)

        # Row labels
        row_1_label = tk.Label(command_frame, text="Cam 1:")
        row_1_label.grid(row=1, column=0)
        row_1_label = tk.Label(command_frame, text="Cam 2:")
        row_1_label.grid(row=2, column=0)

        # FPS
        fps_label = tk.Label(command_frame, text="FPS")
        fps_label.grid(row=0, column=1)
        fps_1_stringvar = tk.StringVar()
        fps_1_stringvar.set("25")
        fps_1_textbox = tk.Entry(command_frame, width=10, textvariable=fps_1_stringvar)
        fps_1_textbox.grid(row=1, column=1)
        fps_2_stringvar = tk.StringVar()
        fps_2_stringvar.set("25")
        fps_2_textbox = tk.Entry(command_frame, width=10, textvariable=fps_2_stringvar)
        fps_2_textbox.grid(row=2, column=1)
        
        # Bitrate
        bitrate_label = tk.Label(command_frame, text="Bitrate [KBs]")
        bitrate_label.grid(row=0, column=2)
        bitrate_1_stringvar = tk.StringVar()
        bitrate_1_stringvar.set("10")
        bitrate_1_textbox = tk.Entry(command_frame, width=10, textvariable=bitrate_1_stringvar)
        bitrate_1_textbox.grid(row=1, column=2)
        bitrate_2_stringvar = tk.StringVar()
        bitrate_2_stringvar.set("10")
        bitrate_2_textbox = tk.Entry(command_frame, width=10, textvariable=bitrate_2_stringvar)
        bitrate_2_textbox.grid(row=2, column=2)
        
        # Active cam
        active_cam_label = tk.Label(command_frame, text="Active")
        active_cam_label.grid(row=0, column=3)
        active_cam_1_intvar = tk.IntVar()
        active_cam_1_intvar.set(1)
        active_cam_1_checkbutton = tk.Checkbutton(command_frame, variable=active_cam_1_intvar, onvalue=1, offvalue=0)
        active_cam_1_checkbutton.grid(row=1, column=3)
        active_cam_2_intvar = tk.IntVar()
        active_cam_2_intvar.set(0)
        active_cam_2_checkbutton = tk.Checkbutton(command_frame, variable=active_cam_2_intvar, onvalue=1, offvalue=0)
        active_cam_2_checkbutton.grid(row=2, column=3)

        return fps_1_stringvar, fps_2_stringvar, bitrate_1_stringvar, bitrate_2_stringvar, active_cam_1_intvar, active_cam_2_intvar

    
    def change_cam_params(self):
        fps_1 = int(self.fps_1_stringvar.get())
        fps_2 = int(self.fps_2_stringvar.get())
        bitrate_1 = int(self.bitrate_1_stringvar.get())
        bitrate_2 = int(self.bitrate_2_stringvar.get())
        active_1 = self.active_cam_1_intvar.get()
        active_2 = self.active_cam_2_intvar.get()
        active_1_str = "(Active)" if active_1 else "(Inactive)"
        active_2_str = "(Active)" if active_2 else "(Inactive)"
        self.logger.info(f"Set new params:\nCam 1 FPS {fps_1} bitrate {bitrate_1} {active_1_str}\nCam 2 FPS {fps_2} bitrate {bitrate_2} {active_2_str}")
        if active_1 and active_2:
            active_cam = 0
        elif active_1:
            active_cam = 1 # Only 1
        elif active_2:
            active_cam = 2 # Only 2
        else:
            active_cam = 1 # By default the one is active
        cv_command = cv_structs.create_cv_command(fps_1, fps_2, bitrateKBs_1=bitrate_1, bitrateKBs_2=bitrate_2, active_sensor=active_cam)
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
