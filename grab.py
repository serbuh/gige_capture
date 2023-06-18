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

gi.require_version('Aravis', '0.8')
from gi.repository import Aravis

from gst_handler import GstSender
from frame_generator import FrameGenerator
from ICD import cv_structs
from communication.udp_communicator import Communicator
from ICD import cu_mrg
from ICD import cv_structs

Aravis.enable_interface("Fake")


class Grabber():
    def __init__(self, logger, receive_cmds_channel, send_reports_channel, save_frames, recordings_basedir, enable_gst, gst_destination, send_not_show, show_frames_cv2, artificial_frames, enable_messages_interface):
        self.logger = logger
        self.save_frames = save_frames
        self.recordings_basedir = recordings_basedir
        self.enable_gst = enable_gst
        self.gst_destination = gst_destination
        self.send_not_show = send_not_show
        self.show_frames_cv2 = show_frames_cv2
        self.artificial_frames = artificial_frames
        self.enable_messages_interface = enable_messages_interface
        
        # Init FPS variables
        self.frame_count_tot = 0
        self.frame_count_fps = 0
        self.start_time = time.time()

        # Init grabber
        if self.artificial_frames:
            self.fps = 20
            self.init_artificial_grabber(self.fps)
        else:
            self.fps = self.init_camera_grabber()
        
        # Show frames options
        if self.show_frames_cv2:
            self.window_name = "Frames"
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        
        # Prepare save folder
        if self.save_frames and self.recordings_basedir is not None:
            now = datetime.datetime.now().strftime("%y_%m_%d__%H_%M_%S")
            self.recordings_full_path = os.path.join(self.recordings_basedir, now)
            pathlib.Path(self.recordings_full_path).mkdir(parents=True, exist_ok=True) # Ensure dir existense
            self.logger.info(f"Saving frames to:\n{self.recordings_full_path}")

        # Send frames options
        if self.enable_gst:
            self.gst_sender = GstSender(self.logger, self.gst_destination, self.fps, self.send_not_show, from_testvideo=False)
        else:
            self.gst_sender = None
        
        # UDP ctypes messages interface
        if self.enable_messages_interface:
            self.communicator = Communicator(self.logger, receive_cmds_channel, send_reports_channel, self.handle_msg)
            self.new_messages_queue = queue.Queue()
            self.communicator.set_receive_queue(self.new_messages_queue)
            self.communicator.register_callback("change_fps", self.change_fps)
            self.communicator.start_receiver_thread() # Start receiver loop
            
        else:
            self.communicator = None

            
    
    def init_artificial_grabber(self, fps):
        self.frame_generator = FrameGenerator(640, 480, fps)

    def init_camera_grabber(self):
        try:
            if len(sys.argv) > 1:
                self.camera = Aravis.Camera.new (sys.argv[1])
            else:
                self.camera = Aravis.Camera.new (None)
        except TypeError:
            self.logger.info("No camera found")
            exit()
        except Exception as e:
            self.logger.info(f"Some problem with camera: {e}")
            exit()
        
        cam_vendor = self.camera.get_vendor_name()
        cam_model = self.camera.get_model_name()
        print (f"Camera vendor : {cam_vendor}")
        print (f"Camera model  : {cam_model}")

        if cam_model == "Blackfly BFLY-PGE-20E4C": # FLIR
            x, y, w, h = 0, 0, 1280, 1024
            fps = 20.0
            self.pixel_format = Aravis.PIXEL_FORMAT_MONO_8
        
        elif cam_model == "mvBlueCOUGAR-X102eC": #BlueCOUGAR-X
            #x, y, w, h = 0, 0, 1280, 1024
            x, y, w, h = 320, 240, 640, 480
            fps = 20.0
            self.pixel_format = Aravis.PIXEL_FORMAT_BAYER_GR_8
            #self.pixel_format = Aravis.PIXEL_FORMAT_RGB_8_PACKED
            #self.pixel_format = Aravis.PIXEL_FORMAT_YUV_422_PACKED
            #self.pixel_format = Aravis.PIXEL_FORMAT_YUV_422_YUYV_PACKED
            
        else: # Default
            x, y, w, h = 0, 0, 640, 480
            fps = 10.0
            self.pixel_format = Aravis.PIXEL_FORMAT_MONO_8
        
        # Set camera params
        try:
            self.camera.set_region(x,y,w,h)
        except gi.repository.GLib.Error as e:
            self.logger.info(f"{e}\nCould not set camera params. Camera is already in use?")
            exit()
        self.camera.set_frame_rate(fps)
        self.camera.set_pixel_format(self.pixel_format)

        payload = self.camera.get_payload ()
        self.pixel_format_string = self.camera.get_pixel_format_as_string()

        [offset_x, offset_y, self.width, self.height] = self.camera.get_region()

        print (f"ROI           : {self.width}x{self.height} at {offset_x},{offset_y}")
        print (f"Payload       : {payload}")
        print (f"Pixel format  : {self.pixel_format_string}")

        self.stream = self.camera.create_stream (None, None)

        # Allocate aravis buffers
        for i in range(0,10):
            self.stream.push_buffer (Aravis.Buffer.new_allocate (payload))

        print ("Start acquisition")
        self.camera.start_acquisition ()
        
        return fps

    def get_frame_from_camera(self):
        # Get frame
        cam_buffer = self.stream.pop_buffer()

        # Get raw buffer
        buf = cam_buffer.get_data()
        #self.logger.info(f"Bits per pixel {len(buf)/self.height/self.width}")
        if self.pixel_format == Aravis.PIXEL_FORMAT_BAYER_GR_8:
            frame_raw = np.frombuffer(buf, dtype='uint8').reshape( (self.height, self.width) )

            # Bayer2RGB
            frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_BayerGR2RGB)

        else:
            self.logger.info(f"Convertion from {self.pixel_format_string} not supported")
            frame_np = None
        
        return frame_np, cam_buffer
    
    def get_artificial_frames(self):
        # Get frame
        frame_np = self.frame_generator.get_next_frame()
        
        return frame_np, None

    def frames_loop(self):
        frame_number = 0
        while True:
            try:
                if self.artificial_frames:
                    frame_np, cam_buffer = self.get_artificial_frames()
                else:
                    frame_np, cam_buffer = self.get_frame_from_camera()
                
                # Show frame
                if self.show_frames_cv2 and frame_np is not None:
                    cv2.imshow(self.window_name, frame_np)

                if self.save_frames:
                    cv2.imwrite(os.path.join(self.recordings_full_path, f"{frame_number}.tiff"), frame_np)
                    #self.logger.info(os.path.join(self.recordings_full_path, f"{frame_number}.tiff"))
                
                if self.gst_sender is not None:
                    self.gst_sender.send_frame(frame_np)
                
                # Release cam_buffer
                if cam_buffer:
                    self.stream.push_buffer(cam_buffer)
                
                # Print FPS
                self.frame_count_fps += 1
                self.frame_count_tot += 1
                now = time.time()
                elapsed_time = now-self.start_time
                if elapsed_time >= 3.0:
                    fps= self.frame_count_fps / elapsed_time
                    self.logger.info(f"FPS: {fps}")
                    # Reset FPS counter
                    self.start_time = now
                    self.frame_count_fps = 0
                
                # cv2 window key
                key = cv2.waitKey(1)&0xff
                if key == ord('q'):
                    self.destroy_all()
                    break

                frame_number+=1

                # Receive commands / Send reports
                if self.enable_messages_interface:
                    # Send status
                    status_msg = cv_structs.create_status(frame_number, frame_number+100) # Create ctypes status
                    
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
                import traceback; traceback.print_exc()
                self.logger.info(f'Exception on frame {self.frame_count_tot}')
    
    def handle_command(self, item):
        print(f"Handle {item}")
        # TODO apply command

    def change_fps(self, new_fps):
        self.logger.info(f"TODO: Change fps to {new_fps}")

    def destroy_all(self):
        
        self.logger.info("Stop the messages receiver thread")
        try:
            if self.communicator is not None:
                self.communicator.stop_receiver_thread()
        except:
            import traceback; traceback.print_exc()
            self.logger.info("Exception during stopping the receiver thread")

        self.logger.info("Stop the camera grabbing")
        try:
            self.camera.stop_acquisition()
        except:
            import traceback; traceback.print_exc()
            self.logger.info("Exception during closing camera grabbing")
        
        self.logger.info("Stop the gstreamer")
        try:
            if self.gst_sender is not None:
                self.gst_sender.destroy()
        except:
            import traceback; traceback.print_exc()
            self.logger.info("Exception during closing gstreamer")
        
        self.logger.info("Close cv2 windows")
        try:
            cv2.destroyAllWindows()
        except:
            import traceback; traceback.print_exc()
            self.logger.info("Exception during closing cv2 windows")

        self.logger.info("My work here is done")

    def handle_msg(self, msg_serialized):
        msg = self.communicator.deserialize_to_ctypes(msg_serialized)
                
        if msg is None:
            self.logger.error("Invalid message. Ignoring")
            return

        elif type(msg) == cu_mrg.SetCvParamsCmdMessage:
            
            # Create ack
            params_result_msg = cv_structs.create_reply(isOk=True)
            # Send Ack
            self.communicator.send_ctypes_msg(params_result_msg)
        
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

    # Prepare params
    file_dir=pathlib.Path().resolve()
    recordings_basedir = os.path.join(file_dir, "recordings")
    #gst_destination = ("127.0.0.1", 5000)
    gst_destination = ("192.168.132.60", 1212)

    #receive_channel = ("192.168.132.212", 5100)
    #send_channel = ("192.168.132.60", 5101)

    receive_cmds_channel = ("127.0.0.1", 5100)
    send_reports_channel = ("127.0.0.1", 5101)
    
    # Start grabber
    grabber = Grabber(logger, receive_cmds_channel, send_reports_channel, save_frames=False, recordings_basedir=recordings_basedir, enable_gst=True, gst_destination=gst_destination, send_not_show=True, show_frames_cv2=True, artificial_frames=False, enable_messages_interface=True)
    grabber.frames_loop()
    logger.info("Bye!")