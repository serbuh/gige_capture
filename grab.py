#!/usr/bin/env python

# NOTE: to debug Aravis:
# Run ARV_DEBUG=all python grab.py

# NOTE: to debug Gstreamer:
# RUN GST_DEBUG=LOG/TRACE/MEMDUMP

#  If you have installed aravis in a non standard location, you may need
#   to make GI_TYPELIB_PATH point to the correct location. For example:
#
#   export GI_TYPELIB_PATH=$GI_TYPELIB_PATH:/opt/bin/lib/girepositry-1.0/
#
#  You may also have to give the path to libaravis.so, using LD_PRELOAD or
#  LD_LIBRARY_PATH.

import sys
import time
import os
import numpy as np
import cv2
import logging
import pathlib
import datetime
import queue
import traceback
import tomli
import pprint
import threading
import argparse

from gst_handler import GstSender
from video_feeders.frame_generator import FrameGenerator
from video_feeders.arv_cam import ArvCamera
from ICD import cv_structs
from communication.udp_communicator import Communicator


class CamParams():
    def __init__(self, pixel_format_str, offset_x, offset_y, width, height, binning, scale_x, scale_y, grab_fps, send_fps):
        self.pixel_format_str = pixel_format_str
        self.offset_x  = offset_x
        self.offset_y  = offset_y
        self.width     = width
        self.height    = height
        self.binning = binning
        self.scale_x   = scale_x
        self.scale_y   = scale_y
        self.grab_fps  = grab_fps
        self.send_fps  = send_fps

class Configurator():
    def __init__(self, logger, proj_path, stream_index):
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
        try:
            self.active_camera = cv_structs.activateCameraSensors[self.config['Cams']['active_camera']]
        except Exception as e:
            self.logger.error(f"{e}\nFailed to get active_camera from toml")
            exit()

        # Config cams
        class CamParams():
            def __init__(self, cam_config_section, file_dir):
                self.cam_ip               = cam_config_section['cam_ip']
                self.show_frames_gst      = cam_config_section['show_frames_gst']
                self.save_frames          = cam_config_section['save_frames']
                self.recordings_basedir   = os.path.join(file_dir, cam_config_section['recordings_dir'])
                self.enable_gst           = cam_config_section['enable_gst']
                self.gst_destination      = (str(cam_config_section['gst_destination_ip']), int(cam_config_section['gst_destination_port']))
                self.send_frames_gst      = cam_config_section['send_frames_gst']
                # Messages communication
                self.receive_cmds_channel = (str(cam_config_section['receive_cmds_ip']), int(cam_config_section['receive_cmds_port']))
                self.send_reports_channel = (str(cam_config_section['send_reports_ip']), int(cam_config_section['send_reports_port']))
                self.send_from_port       = int(cam_config_section['send_from_port'])
                self.enable_messages_interface = cam_config_section['enable_messages_interface']
                self.send_status               = cam_config_section['send_status']
                self.print_messages            = cam_config_section['print_messages']

        # Cam params
        self.cam_params = CamParams(self.config['Cams'][str(stream_index)], self.file_dir)
    
    def get_cam_settings(self, cam_model):
        cam_config_dict = self.config.get(cam_model, None)
        if cam_config_dict is None:
            self.logger.error(f"No config for {cam_model}")
            exit()
        else:
            self.logger.info(f"\n> {cam_model} <\n{pprint.pformat(cam_config_dict, indent=4, sort_dicts=False)}\n")
            stream_params = CamParams(
                pixel_format_str = cam_config_dict["pixel_format"],
                offset_x  = int(cam_config_dict["offset_x"]),
                offset_y  = int(cam_config_dict["offset_y"]),
                width     = int(cam_config_dict["width"]),
                height    = int(cam_config_dict["height"]),
                binning = int(cam_config_dict["binning"]),
                scale_x   = int(cam_config_dict["scale_x"]),
                scale_y   = int(cam_config_dict["scale_y"]),
                grab_fps  = int(cam_config_dict["grab_fps"]),
                send_fps  = int(cam_config_dict["send_fps"]),
            )
        return stream_params

class Stream():
    def __init__(self, logger, configurator, stream_params):
        self.logger = logger
        self.configurator = configurator
        self.stream_params = stream_params
        self.recordings_full_path = None
        self.gst_sender = None
        self.stream_ip = self.stream_params.cam_ip
        
        self.logger.info(f"   Init stream   {self.stream_ip}   ".center(70, "#"))

        # Init FPS variables
        self.frame_count_tot = 0
        self.frame_count_fps = 0
        self.last_fps = 0
        self.start_time = time.time()

        # Init grabber
        self.initialized = self.init_grabber(self.stream_ip)
        self.artificial = self.video_feeder.is_artificial()
        if self.initialized:
            result_str = "INITIALIZED"
        else:
            result_str = "FAILED to initialized"
        
        stream_name = self.video_feeder.cam_model
        self.stream_name = stream_name if stream_name is not None else "No Name"

        # UDP ctypes messages interface
        if stream_params.enable_messages_interface:
            self.communicator = Communicator(self.logger, stream_params.print_messages, stream_params.receive_cmds_channel, stream_params.send_reports_channel, stream_params.send_from_port, self.handle_ctypes_msg_callback)
            self.new_messages_queue = queue.Queue()
            self.communicator.set_receive_queue(self.new_messages_queue)
            #self.communicator.register_callback("change_fps", self.change_fps)
            self.communicator.start_receiver_thread() # Start receiver loop
            
        else:
            self.communicator = None
        
        self.logger.info(f"   Stream   {self.stream_ip}   {result_str}   ".center(70, "#"))

    def init_grabber(self, ip):
        
        if ip == "Artificial":
            self.cam_config = self.configurator.get_cam_settings(ip)
            self.video_feeder = FrameGenerator(self.logger, self.cam_config)
            return True
        
        else:
            self.video_feeder = ArvCamera(self.logger)
            connected = self.video_feeder.connect_to_cam(ip)
            if connected is False:
                return False
            
            self.cam_config = self.configurator.get_cam_settings(self.video_feeder.cam_model)
            self.video_feeder.set_cam_config(self.cam_config)
            initialized = self.video_feeder.initialize()
            
            return initialized
    
    def print_status(self):
        self.logger.info(f"{self.stream_ip:16} {self.stream_name:30} {'OK' if self.initialized else 'BAD'}")
    
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

    
class Grabber():
    def __init__(self, logger, proj_path, stream_index):
        self.logger = logger
        self.stream_index = stream_index
        self.keep_going = True
        self.configurator = Configurator(logger, proj_path, stream_index)
        
        self.active_camera = self.configurator.active_camera # TODO

        # Init stream
        self.stream = Stream(logger, self.configurator, self.configurator.cam_params)

        if not self.stream.initialized:
            self.logger.error(f"Stream[{stream_index}] FAILED to initialize")
            self.destroy_all()
            exit()
        
        # Show frames with cv2
        # NOTE: Deprecated
        # if False and stream.stream_params.show_frames_cv2:
        #     cv2.namedWindow(self.stream.stream_name, cv2.WINDOW_AUTOSIZE)

        # Prepare save folder
        if self.stream.stream_params.save_frames and self.stream.stream_params.recordings_basedir is not None:
            now = datetime.datetime.now().strftime("%y_%m_%d__%H_%M_%S")
            self.stream.recordings_full_path = os.path.join(self.stream.stream_params.recordings_basedir, now)
            pathlib.Path(self.stream.recordings_full_path).mkdir(parents=True, exist_ok=True) # Ensure dir existense
            self.logger.info(f"Saving frames to:\n{self.stream.recordings_full_path}")

        # Send frames options
        if self.stream.stream_params.enable_gst:
            self.stream.gst_sender = GstSender(self.logger, self.stream.stream_params.gst_destination, self.stream.cam_config.send_fps, self.stream.stream_params.show_frames_gst, self.stream.stream_params.send_frames_gst, from_testvideo=False)
        else:
            self.stream.gst_sender = None

    def stream_loop(self):
        self.logger.info(f"Start stream loop ({self.stream.stream_name})")
        frame_number = 0
        while self.keep_going:
            try:
                frame_np, cam_buffer = self.stream.video_feeder.get_next_frame()
                
                if frame_np is None:
                    self.logger.warning("None frame")
                    if cam_buffer:
                        self.stream.video_feeder.release_cam_buffer(cam_buffer)
                    continue

                # Show frame with cv2
                # NOTE: Deprecated
                # if False and stream.stream_params.show_frames_cv2 and frame_np is not None:
                #     cv2.imshow(self.stream.stream_name, frame_np)

                # Save frame
                if self.stream.stream_params.save_frames:
                    cv2.imwrite(os.path.join(self.stream.recordings_full_path, f"{frame_number}.tiff"), frame_np)
                    #self.logger.info(os.path.join(stream.recordings_full_path, f"{frame_number}.tiff"))

                # Send frames
                if self.stream.gst_sender is not None:
                    self.stream.gst_sender.send_frame(frame_np)
            
                # Release cam_buffer
                if cam_buffer:
                    self.stream.video_feeder.release_cam_buffer(cam_buffer)
            
                # Print FPS
                self.stream.frame_count_fps += 1
                self.stream.frame_count_tot += 1
                now = time.time()
                elapsed_time = now-self.stream.start_time
                if elapsed_time >= 3.0:
                    self.stream.last_fps = self.stream.frame_count_fps / elapsed_time
                    self.logger.info(f"FPS: {self.stream.last_fps:.2f} Hz  ({self.stream.stream_name})")
                    # Reset FPS counter
                    self.stream.start_time = now
                    self.stream.frame_count_fps = 0
                
                if False:
                    # cv2 window key
                    key = cv2.waitKey(1)&0xff
                    if key == ord('q'):
                        self.destroy_all()
                        break

                frame_number+=1
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by Ctrl+C (in Grabber)")
                self.destroy_all()
            
            except Exception:
                traceback.print_exc()
                self.logger.info(f'Exception (in Grabber) on frame {self.stream.frame_count_tot}')

        
    def messages_loop(self):
        self.logger.info("Starting messages communication loop")
        
        while self.keep_going:
            try:
                # Receive commands / Send reports
                if self.stream.stream_params.enable_messages_interface:
                    # Send status
                    if self.stream.stream_params.send_status:
                        # TODO fill in the right values
                        frame_number = 300
                        fps = int(self.stream.last_fps)
                        bitrateKBs = 10
                        calibration = False
                        addOverlay = False
                        status_msg = cv_structs.create_status(frame_number, fps, bitrateKBs, calibration, addOverlay) # Create ctypes status
                        self.stream.communicator.send_ctypes_msg(status_msg) # Send status
                    
                    # Read receive queue
                    while not self.stream.new_messages_queue.empty():
                        item = self.stream.new_messages_queue.get_nowait()
                        self.handle_command(item)
                
                time.sleep(1)
            
            except KeyboardInterrupt:
                self.logger.info("Interrupted by Ctrl+C (in Grabber)")
                self.destroy_all()
            
            except Exception:
                traceback.print_exc()
                self.logger.info(f'Exception (in Grabber) on frame {self.stream.frame_count_tot}')

    def handle_command(self, item):
        self.logger.info(f">> Handle {type(item)}") # Server

    def change_fps(self, new_fps):
        self.logger.info(f"TODO: Change fps to {new_fps}")

    def destroy_all(self):
        self.logger.info("Stop the messages receiver thread")
        self.keep_going = False
        try:
            if getattr(self.stream, "communicator", None) is not None and self.stream.communicator is not None:
                self.stream.communicator.stop_receiver_thread()
        except:
            traceback.print_exc()
            self.logger.info("Exception during stopping the receiver thread")

        self.logger.info("Stop the camera grabbing")
        try:
            if not self.stream.artificial:
                self.stream.video_feeder.stop_acquisition()
        except:
            traceback.print_exc()
            self.logger.info("Exception during closing camera grabbing")
        
        self.logger.info("Stop the gstreamer")
        try:
            if self.stream.gst_sender is not None:
                self.stream.gst_sender.destroy()
        except:
            traceback.print_exc()
            self.logger.info("Exception during closing gstreamer")
        
        self.logger.info("Close cv2 windows")
        try:
            cv2.destroyAllWindows()
        except:
            traceback.print_exc()
            self.logger.info("Exception during closing cv2 windows")

        self.logger.info("My work here is done")


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

    # Read args
    parser = argparse.ArgumentParser()
    parser.add_argument("stream_index", type=int, help="stream index", choices=[0,1])
    args = parser.parse_args()
    logger.info(f"Grabber index {args.stream_index}")
    
    # Start grabber
    grabber = Grabber(logger, proj_path, args.stream_index)
    grabber.stream_loop()
    logger.info("Bye!")
