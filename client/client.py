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

        receive_reports_1_channel = ("127.0.0.1", 5010)
        send_cmds_1_channel = ("127.0.0.1", 5011)
        receive_reports_2_channel = ("127.0.0.1", 5020)
        send_cmds_2_channel = ("127.0.0.1", 5021)
        print_messages = True
        send_from_port = None

        self.communicator_1 = Communicator(logger, print_messages, receive_reports_1_channel, send_cmds_1_channel, send_from_port, handle_msg)
        self.communicator_1.start_receiver_thread() # Start receiver loop

        self.communicator_2 = Communicator(logger, print_messages, receive_reports_2_channel, send_cmds_2_channel, send_from_port, handle_msg)
        self.communicator_2.start_receiver_thread() # Start receiver loop

    def init_gui(self):
        # Create the main window
        window = tk.Tk()

        self.fps_1_stringvar, self.fps_2_stringvar, \
        self.bitrate_1_stringvar, self.bitrate_2_stringvar, \
        self.calibration_1_intvar, self.calibration_2_intvar, \
        self.addOverlay_1_intvar, self.addOverlay_2_intvar = \
            self.create_command_frame(window, frame_row=0, frame_column=0)

        window.mainloop()

    def create_command_frame(self, window, frame_row, frame_column):
        # Create a frame
        command_frame = tk.Frame(window)
        command_frame.grid(row=frame_row, column=frame_column)
        
        # Buttons
        col = 0
        cam_1_button = tk.Button(command_frame, text="Cam 1", command=self.change_cam_1_params)
        cam_1_button.grid(row=1, column=col)
        cam_2_button = tk.Button(command_frame, text="Cam 2", command=self.change_cam_2_params)
        cam_2_button.grid(row=2, column=col)

        # FPS
        col += 1
        fps_label = tk.Label(command_frame, text="FPS")
        fps_label.grid(row=0, column=col)
        fps_1_stringvar = tk.StringVar()
        fps_1_stringvar.set("25")
        fps_1_textbox = tk.Entry(command_frame, width=10, textvariable=fps_1_stringvar)
        fps_1_textbox.grid(row=1, column=col)
        fps_2_stringvar = tk.StringVar()
        fps_2_stringvar.set("25")
        fps_2_textbox = tk.Entry(command_frame, width=10, textvariable=fps_2_stringvar)
        fps_2_textbox.grid(row=2, column=col)
        
        # Bitrate
        col += 1
        bitrate_label = tk.Label(command_frame, text="Bitrate [KBs]")
        bitrate_label.grid(row=0, column=col)
        bitrate_1_stringvar = tk.StringVar()
        bitrate_1_stringvar.set("10")
        bitrate_1_textbox = tk.Entry(command_frame, width=10, textvariable=bitrate_1_stringvar)
        bitrate_1_textbox.grid(row=1, column=col)
        bitrate_2_stringvar = tk.StringVar()
        bitrate_2_stringvar.set("10")
        bitrate_2_textbox = tk.Entry(command_frame, width=10, textvariable=bitrate_2_stringvar)
        bitrate_2_textbox.grid(row=2, column=col)
        
        # Calibration
        col += 1
        calibration_label = tk.Label(command_frame, text="Calibration")
        calibration_label.grid(row=0, column=col)
        calibration_1_intvar = tk.IntVar()
        calibration_1_intvar.set(0)
        calibration_1_checkbutton = tk.Checkbutton(command_frame, variable=calibration_1_intvar, onvalue=1, offvalue=0)
        calibration_1_checkbutton.grid(row=1, column=col)
        calibration_2_intvar = tk.IntVar()
        calibration_2_intvar.set(0)
        calibration_2_checkbutton = tk.Checkbutton(command_frame, variable=calibration_2_intvar, onvalue=1, offvalue=0)
        calibration_2_checkbutton.grid(row=2, column=col)

        # AddOverlay
        col += 1
        addOverlay_label = tk.Label(command_frame, text="addOverlay")
        addOverlay_label.grid(row=0, column=col)
        addOverlay_1_intvar = tk.IntVar()
        addOverlay_1_intvar.set(0)
        addOverlay_1_checkbutton = tk.Checkbutton(command_frame, variable=addOverlay_1_intvar, onvalue=1, offvalue=0)
        addOverlay_1_checkbutton.grid(row=1, column=col)
        addOverlay_2_intvar = tk.IntVar()
        addOverlay_2_intvar.set(0)
        addOverlay_2_checkbutton = tk.Checkbutton(command_frame, variable=addOverlay_2_intvar, onvalue=1, offvalue=0)
        addOverlay_2_checkbutton.grid(row=2, column=col)
        
        return fps_1_stringvar, fps_2_stringvar, bitrate_1_stringvar, bitrate_2_stringvar, calibration_1_intvar, calibration_2_intvar, addOverlay_1_intvar, addOverlay_2_intvar

    def change_cam_1_params(self):
        self.change_cam_params(1)
    
    def change_cam_2_params(self):
        self.change_cam_params(2)

    def change_cam_params(self, cam_id):
        # TODO Get right values form GUI
        frameId = 0
        
        fps = int(getattr(self, f"fps_{cam_id}_stringvar").get())
        bitrateKBs = int(getattr(self, f"bitrate_{cam_id}_stringvar").get())
        calibration = getattr(self, f"calibration_{cam_id}_intvar").get()
        calibration_str = "(V)" if calibration else "(X)"
        addOverlay = getattr(self, f"addOverlay_{cam_id}_intvar").get()
        addOverlay_str = "(V)" if addOverlay else "(X)"

        self.logger.info(f"Cam {cam_id} FPS {fps} bitrate {bitrateKBs} calibration {calibration_str} addOverlay {addOverlay_str}")

        cv_command = cv_structs.create_cv_command(frameId, fps, bitrateKBs, calibration, addOverlay)
        if cam_id == 1:
            self.communicator_1.send_ctypes_msg(cv_command)
        elif cam_id == 2:
            self.communicator_2.send_ctypes_msg(cv_command)
        else:
            self.logger.error(f"BAD cam_id {cam_id}")


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
