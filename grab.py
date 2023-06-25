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

from gst_handler import GstSender
from video_feeders.frame_generator import FrameGenerator
from video_feeders.arv_cam import ArvCamera
from ICD import cv_structs
from communication.udp_communicator import Communicator



class CamParams():
    def __init__(self, pixel_format_str, offset_x, offset_y, width, height, scale_x, scale_y, grab_fps, send_fps):
        self.pixel_format_str = pixel_format_str
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.width    = width
        self.height   = height
        self.scale_x  = scale_x
        self.scale_y  = scale_y
        self.grab_fps = grab_fps
        self.send_fps = send_fps

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
        try:
            self.active_camera = cv_structs.activateCameraSensors[self.config['Cams']['active_camera']]
        except Exception as e:
            self.logger.error(f"{e}\nFailed to get active_camera from toml")
            exit()

        # Config cams
        class CamConfig():
            def __init__(self, cam_config_section, file_dir):
                self.ip                  = cam_config_section['ip']
                self.show_frames_cv2     = cam_config_section['show_frames_cv2']
                self.show_frames_gst     = cam_config_section['show_frames_gst']
                self.save_frames         = cam_config_section['save_frames']
                self.recordings_basedir  = os.path.join(file_dir, cam_config_section['recordings_dir'])
                self.enable_gst          = cam_config_section['enable_gst']
                self.gst_destination     = (str(cam_config_section['gst_destination_ip']), int(cam_config_section['gst_destination_port']))
                self.send_not_show       = cam_config_section['send_not_show']

        # Cam 1
        self.cam_first = CamConfig(self.config['Cams']['first'], self.file_dir)

        # Cam 2
        self.cam_second = CamConfig(self.config['Cams']['second'], self.file_dir)
        
        # Grabber
        self.enable_messages_interface = self.config['Grabber']['enable_messages_interface']
        self.send_status               = self.config['Grabber']['send_status']
        self.print_messages            = self.config['Grabber']['print_messages']

        # Com
        self.receive_cmds_channel = (str(self.config['Com']['receive_cmds_ip']), int(self.config['Com']['receive_cmds_port']))
        self.send_reports_channel = (str(self.config['Com']['send_reports_ip']), int(self.config['Com']['send_reports_port']))
    
    def get_cam_settings(self, cam_model):
        cam_config_dict = self.config.get(cam_model, None)
        if cam_config_dict is None:
            self.logger.error(f"No config for {cam_model}")
            exit()
        else:
            self.logger.info(f"\n> {cam_model} <\n{pprint.pformat(cam_config_dict, indent=4, sort_dicts=False)}\n")
            stream_params = CamParams(
                pixel_format_str = cam_config_dict["pixel_format"],
                offset_x = int(cam_config_dict["offset_x"]),
                offset_y = int(cam_config_dict["offset_y"]),
                width    = int(cam_config_dict["width"]),
                height   = int(cam_config_dict["height"]),
                scale_x  = int(cam_config_dict["scale_x"]),
                scale_y  = int(cam_config_dict["scale_y"]),
                grab_fps = int(cam_config_dict["grab_fps"]),
                send_fps = int(cam_config_dict["send_fps"]),
            )
        return stream_params

class Streams():
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config

        # Init streams
        self.list = [Stream(logger, self.config, self.config.cam_first), Stream(logger, self.config, self.config.cam_second)]
        
        # Print streams status
        stream_names = [x.get_stream_name() for x in self.list]
        init_status = ["OK" if x.initialized else "BAD" for x in self.list]
        res_str = "\n"
        for name_status in zip(stream_names, init_status):
            res_str += f"{name_status[0]:30}: {name_status[1]}\n"
        self.logger.info(res_str)

        
        for stream in self.get_streams():
            # Show frames with cv2
            if False and stream.stream_params.show_frames_cv2:
                cv2.namedWindow(stream.get_stream_name(), cv2.WINDOW_AUTOSIZE)

            # Prepare save folder
            if stream.stream_params.save_frames and stream.stream_params.recordings_basedir is not None:
                now = datetime.datetime.now().strftime("%y_%m_%d__%H_%M_%S")
                stream.recordings_full_path = os.path.join(stream.stream_params.recordings_basedir, now)
                pathlib.Path(stream.recordings_full_path).mkdir(parents=True, exist_ok=True) # Ensure dir existense
                self.logger.info(f"Saving frames to:\n{stream.recordings_full_path}")

            # Send frames options
            if stream.stream_params.enable_gst:
                stream.gst_sender = GstSender(self.logger, stream.stream_params.gst_destination, stream.cam_config.send_fps, stream.stream_params.show_frames_gst, stream.stream_params.send_not_show, from_testvideo=False)
            else:
                stream.gst_sender = None
    
    def get_streams(self):
        return self.list

class Stream():
    def __init__(self, logger, config, stream_params):
        self.logger = logger
        self.config = config
        self.stream_params = stream_params
        self.recordings_full_path = None
        self.gst_sender = None
        self.loop_thread = None

        self.logger.info(f"   Init stream   {self.stream_params.ip}   ".center(70, "#"))

        # Init FPS variables
        self.frame_count_tot = 0
        self.frame_count_fps = 0
        self.last_fps = 0
        self.start_time = time.time()

        # Init grabber
        self.initialized = self.init_grabber(self.stream_params.ip)
        self.artificial = self.video_feeder.is_artificial()
        if self.initialized:
            result_str = "INITIALIZED"
        else:
            result_str = "FAILED to initialized"
        
        self.logger.info(f"   Stream   {self.stream_params.ip}   {result_str}   ".center(70, "#"))

    def init_grabber(self, ip):
        
        if ip == "Artificial":
            self.cam_config = self.config.get_cam_settings(ip)
            self.video_feeder = FrameGenerator(self.logger, self.cam_config)
            return True
        
        else:
            self.video_feeder = ArvCamera(self.logger)
            connected = self.video_feeder.connect_to_cam(ip)
            if connected is False:
                return False
            
            self.cam_config = self.config.get_cam_settings(self.video_feeder.cam_model)
            self.video_feeder.set_cam_config(self.cam_config)
            initialized = self.video_feeder.initialize()
            
            return initialized
    
    def get_stream_name(self):
        return self.video_feeder.cam_model
    
class Grabber():
    def __init__(self, logger, proj_path):
        self.logger = logger
        self.keep_going = True
        self.config = Configurator(logger, proj_path)
        
        self.active_camera = self.config.active_camera

        # Init streams
        self.streams = Streams(logger, self.config)
        
        # UDP ctypes messages interface
        if self.config.enable_messages_interface:
            self.communicator = Communicator(self.logger, self.config.print_messages, self.config.receive_cmds_channel, self.config.send_reports_channel, self.handle_ctypes_msg_callback)
            self.new_messages_queue = queue.Queue()
            self.communicator.set_receive_queue(self.new_messages_queue)
            self.communicator.register_callback("change_fps", self.change_fps)
            self.communicator.start_receiver_thread() # Start receiver loop
            
        else:
            self.communicator = None

    def start_loops(self):
        try:
            for stream in self.streams.get_streams():
                self.logger.info(f"Starting loop for stream {stream.get_stream_name()}")
                stream.loop_thread = threading.Thread(target=self.stream_thread, args=(stream,))
                stream.loop_thread.start()

            self.logger.info("Starting status loop")
            
            while self.keep_going:
                frame_number = 300 # TODO

                # Receive commands / Send reports # TODO separate from stream loop
                if self.config.enable_messages_interface:
                    # Send status
                    if self.config.send_status:
                        status_msg = cv_structs.create_status(frame_number, frame_number, int(stream.last_fps), int(stream.last_fps), bitrateKBs_1=10, bitrateKBs_2=10, active_camera=self.active_camera) # Create ctypes status
                        self.communicator.send_ctypes_msg(status_msg) # Send status
                    
                    # Read receive queue
                    while not self.new_messages_queue.empty():
                        item = self.new_messages_queue.get_nowait()
                        self.handle_command(item)
                
                time.sleep(1)
        
        except KeyboardInterrupt:
                self.logger.info("Interrupted from main thread by Ctrl+C")
                self.destroy_all()
            
    def stream_thread(self, stream):
        self.logger.info(f"Stream thread started ({stream.get_stream_name()})")
        frame_number = 0
        while self.keep_going:
            try:
                frame_np, cam_buffer = stream.video_feeder.get_next_frame()
                
                if frame_np is None:
                    self.logger.warning("None frame")
                    continue

            
                # # Show frame
                if False and stream.stream_params.show_frames_cv2 and frame_np is not None:
                    cv2.imshow(stream.get_stream_name(), frame_np)

                # Save frame
                if stream.stream_params.save_frames:
                    cv2.imwrite(os.path.join(stream.recordings_full_path, f"{frame_number}.tiff"), frame_np)
                    #self.logger.info(os.path.join(stream.recordings_full_path, f"{frame_number}.tiff"))

                # Send frames
                if stream.gst_sender is not None:
                    stream.gst_sender.send_frame(frame_np)
            
                # Release cam_buffer
                if cam_buffer:
                    stream.video_feeder.release_cam_buffer(cam_buffer)
            
                # Print FPS
                stream.frame_count_fps += 1
                stream.frame_count_tot += 1
                now = time.time()
                elapsed_time = now-stream.start_time
                if elapsed_time >= 3.0:
                    stream.last_fps = stream.frame_count_fps / elapsed_time
                    self.logger.info(f"FPS: {stream.last_fps:.2f} Hz  ({stream.get_stream_name()})")
                    # Reset FPS counter
                    stream.start_time = now
                    stream.frame_count_fps = 0
                
                if False:
                    # cv2 window key
                    key = cv2.waitKey(1)&0xff
                    if key == ord('q'):
                        self.destroy_all()
                        break

                frame_number+=1
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by Ctrl+C")
                self.destroy_all()
                break
            
            except Exception:
                traceback.print_exc()
                self.logger.info(f'Exception on frame {stream.frame_count_tot}')
    
    def handle_command(self, item):
        self.logger.info(f">> Handle {type(item)}") # Server

    def change_fps(self, new_fps):
        self.logger.info(f"TODO: Change fps to {new_fps}")

    def destroy_all(self):
        self.logger.info("Stop the messages receiver thread")
        self.keep_going = False
        try:
            if self.communicator is not None:
                self.communicator.stop_receiver_thread()
        except:
            traceback.print_exc()
            self.logger.info("Exception during stopping the receiver thread")

        self.logger.info("Stop the camera grabbing")
        try:
            for stream in self.streams.get_streams():
                if not stream.artificial:
                    stream.video_feeder.stop_acquisition()
        except:
            traceback.print_exc()
            self.logger.info("Exception during closing camera grabbing")
        
        self.logger.info("Stop the gstreamer")
        try:
            for stream in self.streams.get_streams():
                if stream.gst_sender is not None:
                    stream.gst_sender.destroy()
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

    def handle_ctypes_msg_callback(self, msg):
        self.logger.info(f">> Got:\n{msg}") # Server
        
        if msg is None:
            self.logger.error("Invalid message. Ignoring")
            return

        elif isinstance(msg, cv_structs.client_set_params_msg):
            
            # TODO do things
            
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
    grabber = Grabber(logger, proj_path)
    grabber.start_loops()
    logger.info("Bye!")
