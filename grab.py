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
import gi
import numpy as np
import cv2
import logging
import pathlib
import datetime
import queue
import traceback
import tomli
import pprint

gi.require_version('Aravis', '0.8')
from gi.repository import Aravis

from gst_handler import GstSender
from frame_generator import FrameGenerator
from ICD import cv_structs
from communication.udp_communicator import Communicator

Aravis.enable_interface("Fake")

class Configurator():
    def __init__(self, logger, proj_path):
        self.logger = logger
        self.config_file_path = os.path.join(proj_path, "config", "config.toml")
        self.file_dir=pathlib.Path().resolve()
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
        
        # Cam 1
        self.cam_1_ip = self.config['Cams']['cam_1_ip']
        self.cam1 = None

        # Cam 2
        self.cam_2_ip = self.config['Cams']['cam_2_ip']
        self.cam2 = None
        
        # Grabber
        self.save_frames = self.config['Grabber']['save_frames']
        self.recordings_basedir = os.path.join(self.file_dir, self.config['Grabber']['recordings_dir'])
        self.enable_gst = self.config['Grabber']['enable_gst']
        self.send_not_show = self.config['Grabber']['send_not_show']
        self.show_frames_cv2 = self.config['Grabber']['show_frames_cv2']
        self.enable_messages_interface = self.config['Grabber']['enable_messages_interface']
        self.send_status = self.config['Grabber']['send_status']

        # Com
        self.gst_destination      = (str(self.config['Com']['gst_destination_ip']), int(self.config['Com']['gst_destination_port']))
        self.receive_cmds_channel = (str(self.config['Com']['receive_cmds_ip']), int(self.config['Com']['receive_cmds_port']))
        self.send_reports_channel = (str(self.config['Com']['send_reports_ip']), int(self.config['Com']['send_reports_port']))
    
    def get_cam_settings(self, cam_model):
        cam_config = self.config.get(cam_model, None)
        if cam_config is None:
            self.logger.error(f"No config for {cam_model}")
            exit()
        else:
            self.logger.info(f"\n> {cam_model} <\n{pprint.pformat(cam_config, indent=4, sort_dicts=False)}\n")
        return cam_config

class Stream():
    def __init__(self, logger, config, ip):
        self.logger = logger
        self.config = config
        self.ip = ip

        if ip == "Artificial":
            self.artificial = True
        else:
            self.artificial = False

        self.logger.info(f"CAM {ip}")

        # Init FPS variables
        self.frame_count_tot = 0
        self.frame_count_fps = 0
        self.last_fps = 0
        self.start_time = time.time()

        # Init grabber
        self.cam_model = None
        self.initialized, self.artificial = self.init_grabber(ip)
        if self.initialized:
            self.logger.info(f"CAM {ip} initialized SUCCESSFULLY")
        else:
            self.logger.error(f"CAM {ip} initialize FAIL")
    
    def init_grabber(self, ip):
        
        if ip == "Artificial":
            artificial = True
            self.grab_fps = 20 # TODO put in streams
            self.frame_generator = FrameGenerator(640, 480, grab_fps=self.grab_fps)
            self.cam_model = ip
        else:
            artificial = False
            self.arv_camera, self.cam_model = self.get_aravis_cam(ip)
            if self.arv_camera is None:
                return False, artificial
        
        # Get config
        self.cam_config = self.config.get_cam_settings(self.cam_model)
        
        # Get cam params
        x = int(self.cam_config['offset_x'])
        y = int(self.cam_config['offset_y'])
        w = int(self.cam_config['width'])
        h = int(self.cam_config['height'])
        pixel_format = self.cam_config['pixel_format']
        self.pixel_format = getattr(Aravis, pixel_format)
        self.grab_fps = self.cam_config['send_fps'] # TODO add grab_fps
        
        # Stop here in case of artificial frames
        if artificial:
            return True, artificial

        # Set camera params
        try:
            self.arv_camera.set_region(x,y,w,h)
        except gi.repository.GLib.Error as e:
            self.logger.info(f"{e}\nCould not set camera params. Camera is already in use?")
            return False, artificial
        try:
            #self.arv_camera.set_frame_rate(fps)
            self.arv_camera.set_pixel_format(self.pixel_format)
        except gi.repository.GLib.Error as e:
            self.logger.info(f"{e}\nCould not set frame rate / pixel format params.")
            return False, artificial

        payload = self.arv_camera.get_payload ()
        self.pixel_format_string = self.arv_camera.get_pixel_format_as_string()

        [offset_x, offset_y, self.width, self.height] = self.arv_camera.get_region()

        print (f"ROI           : {self.width}x{self.height} at {offset_x},{offset_y}")
        print (f"Payload       : {payload}")
        print (f"Pixel format  : {self.pixel_format_string}")

        self.arv_stream = self.arv_camera.create_stream(None, None)

        # Allocate aravis buffers
        for i in range(0,10):
            self.arv_stream.push_buffer(Aravis.Buffer.new_allocate(payload))

        print ("Start acquisition")
        self.arv_camera.start_acquisition()

        return True, artificial
    
    def get_aravis_cam(self, cam_ip):
        self.logger.info(f"Connecting to camera on IP {cam_ip}")
        try:
            camera = Aravis.Camera.new(None)
            
        except TypeError:
            self.logger.info(f"No camera found ({cam_ip})")
            return None, None
        except Exception as e:
            self.logger.info(f"Some problem with camera ({cam_ip}): {e}")
            return None, None
        
        cam_vendor = camera.get_vendor_name()
        self.logger.info(f"Camera vendor : {cam_vendor}")
        
        cam_model = camera.get_model_name()
        self.logger.info(f"Camera model  : {cam_model}")

        return camera, cam_model

class Grabber():
    def __init__(self, logger, proj_path):
        self.logger = logger
        
        self.config = Configurator(logger, proj_path)
        
        self.active_camera = self.config.active_camera

        # Init streams (cameras / artificial frames)
        self.streams = [Stream(logger, self.config, self.config.cam_1_ip), Stream(logger, self.config, self.config.cam_2_ip)]
        
        # Show frames options
        if self.config.show_frames_cv2:
            self.window_name = "Frames"
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        
        # Prepare save folder
        if self.config.save_frames and self.config.recordings_basedir is not None:
            now = datetime.datetime.now().strftime("%y_%m_%d__%H_%M_%S")
            self.recordings_full_path = os.path.join(self.config.recordings_basedir, now)
            pathlib.Path(self.recordings_full_path).mkdir(parents=True, exist_ok=True) # Ensure dir existense
            self.logger.info(f"Saving frames to:\n{self.recordings_full_path}")

        # Send frames options
        if self.config.enable_gst:
            self.gst_sender = GstSender(self.logger, self.config.gst_destination, self.streams[0].grab_fps, self.config.send_not_show, from_testvideo=False)
        else:
            self.gst_sender = None
        
        # UDP ctypes messages interface
        if self.config.enable_messages_interface:
            self.communicator = Communicator(self.logger, self.config.receive_cmds_channel, self.config.send_reports_channel, self.handle_ctypes_msg_callback)
            self.new_messages_queue = queue.Queue()
            self.communicator.set_receive_queue(self.new_messages_queue)
            self.communicator.register_callback("change_fps", self.change_fps)
            self.communicator.start_receiver_thread() # Start receiver loop
            
        else:
            self.communicator = None

    def get_next_frame(self, artificial):
        if artificial:
            frame_np = self.streams[0].frame_generator.get_next_frame()
            cam_buffer = None
        else:
            # Get frame
            cam_buffer = self.streams[0].arv_stream.pop_buffer()

            # Get raw buffer
            buf = cam_buffer.get_data()
            #self.logger.info(f"Bits per pixel {len(buf)/self.height/self.width}")
            if self.streams[0].pixel_format == Aravis.PIXEL_FORMAT_BAYER_GR_8:
                frame_raw = np.frombuffer(buf, dtype='uint8').reshape( (self.streams[0].height, self.streams[0].width) )

                # Bayer2RGB
                frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_BayerGR2RGB)
            elif self.streams[0].pixel_format == Aravis.PIXEL_FORMAT_MONO_8:
                frame_raw = np.frombuffer(buf, dtype='uint8').reshape( (self.streams[0].height, self.streams[0].width) )

                # Bayer2RGB
                frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_GRAY2RGB)
            else:
                self.logger.info(f"Convertion from {self.streams[0].pixel_format_string} not supported")
                frame_np = None
        
        return frame_np, cam_buffer

    def main_loop(self):
        
        for stream in self.streams:
            self.logger.info(f"Starting loop for stream {stream.ip}")

        frame_number = 0
        while True:
            try:
                frame_np, cam_buffer = self.get_next_frame(self.streams[0].artificial)
                
                if frame_np is None:
                    self.logger.warning("None frame")
                    continue

                # Show frame
                if self.config.show_frames_cv2 and frame_np is not None:
                    cv2.imshow(self.window_name, frame_np)

                if self.config.save_frames:
                    cv2.imwrite(os.path.join(self.recordings_full_path, f"{frame_number}.tiff"), frame_np)
                    #self.logger.info(os.path.join(self.recordings_full_path, f"{frame_number}.tiff"))
                
                if self.gst_sender is not None:
                    self.gst_sender.send_frame(frame_np)
                
                # Release cam_buffer
                if cam_buffer:
                    self.streams[0].arv_stream.push_buffer(cam_buffer)
                
                # Print FPS
                self.streams[0].frame_count_fps += 1
                self.streams[0].frame_count_tot += 1
                now = time.time()
                elapsed_time = now-self.streams[0].start_time
                if elapsed_time >= 3.0:
                    self.streams[0].last_fps = self.streams[0].frame_count_fps / elapsed_time
                    self.logger.info(f"FPS: {self.streams[0].last_fps}")
                    # Reset FPS counter
                    self.streams[0].start_time = now
                    self.streams[0].frame_count_fps = 0
                
                # cv2 window key
                key = cv2.waitKey(1)&0xff
                if key == ord('q'):
                    self.destroy_all()
                    break

                frame_number+=1

                # Receive commands / Send reports
                if self.config.enable_messages_interface:
                    # Send status
                    if self.config.send_status:
                        status_msg = cv_structs.create_status(frame_number, frame_number, int(self.streams[0].last_fps), int(self.streams[0].last_fps), bitrateKBs_1=10, bitrateKBs_2=10, active_camera=self.active_camera) # Create ctypes status
                        self.communicator.send_ctypes_msg(status_msg) # Send status
                    
                    # Read receive queue
                    while not self.new_messages_queue.empty():
                        item = self.new_messages_queue.get_nowait()
                        self.handle_command(item)
                
            except KeyboardInterrupt:
                self.logger.info("Interrupted by Ctrl+C")
                self.destroy_all()
                break
            
            except Exception:
                traceback.print_exc()
                self.logger.info(f'Exception on frame {self.streams[0].frame_count_tot}')
    
    def handle_command(self, item):
        self.logger.info(f">> Handle {type(item)}") # Server

    def change_fps(self, new_fps):
        self.logger.info(f"TODO: Change fps to {new_fps}")

    def destroy_all(self):
        
        self.logger.info("Stop the messages receiver thread")
        try:
            if self.communicator is not None:
                self.communicator.stop_receiver_thread()
        except:
            traceback.print_exc()
            self.logger.info("Exception during stopping the receiver thread")

        self.logger.info("Stop the camera grabbing")
        try:
            if not self.streams[0].artificial:
                self.streams[0].arv_camera.stop_acquisition()
        except:
            traceback.print_exc()
            self.logger.info("Exception during closing camera grabbing")
        
        self.logger.info("Stop the gstreamer")
        try:
            if self.gst_sender is not None:
                self.gst_sender.destroy()
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
    grabber.main_loop()
    logger.info("Bye!")
