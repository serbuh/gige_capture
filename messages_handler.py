import logging
import pathlib
import traceback
import tomli
import os
import sys
import queue
import time
from ICD import cv_structs
from communication.udp_communicator import Communicator


class Configurator():
    def __init__(self, logger, proj_path):
        self.logger = logger
        self.config_file_path = os.path.join(proj_path, "config", "config.toml")
        self.file_dir = pathlib.Path().resolve()
        self.logger.info(f"Loading configuration from:\n{self.config_file_path}")
        with open(self.config_file_path, mode="rb") as config_f:
            try:
                self.config = tomli.load(config_f)
            except:
                traceback.print_exc()
                self.logger.error("Failed to read toml")
                exit()
        
        # MessagesHandler
        self.enable_messages_interface = self.config['MessagesHandler']['enable_messages_interface']
        self.send_status               = self.config['MessagesHandler']['send_status']
        self.print_messages            = self.config['MessagesHandler']['print_messages']

        # Com
        self.receive_cmds_channel = (str(self.config['Com']['receive_cmds_ip']), int(self.config['Com']['receive_cmds_port']))
        self.send_reports_channel = (str(self.config['Com']['send_reports_ip']), int(self.config['Com']['send_reports_port']))
        self.send_from_port = self.config['Com']['send_from_port']

class MessagesHandler():
    def __init__(self, logger, proj_path):
        self.logger = logger
        self.keep_going = True
        self.config = Configurator(logger, proj_path)

        # Init external communicator
        self.communicator = Communicator(self.logger, self.config.print_messages, self.config.receive_cmds_channel, self.config.send_reports_channel, self.config.send_from_port, self.handle_ctypes_msg_callback)
        self.new_messages_queue = queue.Queue()
        self.communicator.set_receive_queue(self.new_messages_queue)
        self.communicator.register_callback("change_fps", self.change_fps)
        self.communicator.start_receiver_thread() # Start receiver loop

    def handler_loop(self):
        if self.config.enable_messages_interface:
            self.logger.info(f"Start messages handler loop")
        else:
            self.logger.info(f"Interface disabled in configuration")
            return
        
        while self.keep_going:
            try:
                # Send status
                if self.config.send_status:
                    frame_number = 100
                    last_fps = 25
                    status_msg = cv_structs.create_status(frame_number, frame_number, last_fps, last_fps, bitrateKBs_1=10, bitrateKBs_2=10, active_camera=self.active_camera) # Create ctypes status
                    self.communicator.send_ctypes_msg(status_msg) # Send status
                
                # Read receive queue
                while not self.new_messages_queue.empty():
                    item = self.new_messages_queue.get_nowait()
                    self.handle_command(item)
                
                time.sleep(1)
        
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by Ctrl+C")
                self.destroy_all()
            
            except Exception:
                traceback.print_exc()
                self.logger.info(f'General Exception')
            
    def handle_command(self, item):
        self.logger.info(f">> Handle {type(item)}") # Server

    def change_fps(self, new_fps):
        self.logger.info(f"TODO: Change fps to {new_fps}")

    def destroy_all(self):
        self.logger.info("Commanding the messages handler to stop")
        self.keep_going = False
        
    def handle_ctypes_msg_callback(self, msg):
        self.logger.info(f">> Got:\n{msg}") # Server
        
        if msg is None:
            self.logger.error("Invalid message. Ignoring")
            return

        elif isinstance(msg, cv_structs.client_set_params_msg):
            
            # TODO do things
            self.logger.info("Sending ack")
            # Create ack
            params_result_msg = cv_structs.create_cv_command_ack(isOk=True)
            # Send Ack
            self.communicator.send_ctypes_msg(params_result_msg)
        
        elif isinstance(msg, cv_structs.vision_status_msg):
            self.logger.warning(f"got vision status from ourselves?")
        
        else:
            self.logger.warning(f"Trying to handle unknown msg type {type(msg)}")
        
        # Put in Queue (if valid opcode)
        if self.communicator.received_msg_queue is not None:
            self.communicator.received_msg_queue.put_nowait(msg)


####################################################################
if __name__ == "__main__":
    # Set logger
    logger = logging.getLogger("Grabber")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(clear_with_time_msec_format)
    logger.addHandler(ch)
    logger.info("Welcome to Grabber")

    # Project path
    proj_path=pathlib.Path().resolve()
    
    # Start grabber
    grabber = MessagesHandler(logger, proj_path)
    grabber.handler_loop()
    logger.info("Bye!")
