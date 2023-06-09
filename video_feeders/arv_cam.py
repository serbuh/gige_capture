import time
import cv2
import numpy as np
import gi

from video_feeders.video_feeder_interface import VideoFeeder

gi.require_version('Aravis', '0.8')
from gi.repository import Aravis


Aravis.enable_interface("Fake")

class ArvCamera(VideoFeeder):
    def __init__(self, logger):
        VideoFeeder.__init__(self, False)
        self.logger = logger
        
        self.arv_camera = None
        self.cam_model = None

        self.cam_config = None
        self.arv_stream = None
    
    def connect_to_cam(self, ip):
        self.arv_camera, self.cam_model = self.get_arv_cam(ip)
        if self.arv_camera is None:
            self.logger.error("Aravis failed to initialize cam")
            return False
        else:
            return True

    def set_cam_config(self, cam_config):
        self.cam_config = cam_config
        
    def initialize(self):
        # Set Aravis camer params
        initialized, payload = self.set_arv_params() # Assumes self.cam_config
        if initialized:
            self.arv_stream = self.init_arv_stream(payload)

        return initialized
    
    def get_arv_cam(self, cam_ip):
        self.logger.info(f"Connecting to camera on IP {cam_ip}")
        try:
            camera = Aravis.Camera.new(cam_ip)
            
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

    def set_arv_params(self):
        # Set binning
        try:
            if self.cam_config.binning >= 0:
                self.arv_camera.set_integer("BinningVertical", int(self.cam_config.binning))
                binning_x, binning_y = self.arv_camera.get_binning()
                self.logger.info(f"Binning       : {binning_x}, {binning_y}")
        except gi.repository.GLib.Error as e:
            self.logger.error(f"{e}\nCould not set binning")
            return False, None

        # Set decimation
        # try:
        #     if self.cam_config.binning >= 0:
        #         self.arv_camera.set_integer("DecimationVertical", int(self.cam_config.binning))
        # except gi.repository.GLib.Error as e:
        #     self.logger.error(f"{e}\nCould not set binning")
        #     return False, None

        # Set ROI
        try:
            self.arv_camera.set_region(
                self.cam_config.offset_x,
                self.cam_config.offset_y,
                self.cam_config.width,
                self.cam_config.height
            )
        except gi.repository.GLib.Error as e:
            self.logger.error(f"{e}\nCould not set camera params. Camera is already in use?")
            return False, None
        
        [offset_x, offset_y, width, height] = self.arv_camera.get_region()
        if offset_x != self.cam_config.offset_x or \
           offset_y != self.cam_config.offset_y or \
           width    != self.cam_config.width or \
           height   != self.cam_config.height:
            self.logger.error(f"Wrong camera region.\nExpected: ({self.cam_config.offset_x}, {self.cam_config.offset_y}, {self.cam_config.width}, {self.cam_config.height})\nGot:     ({offset_x}, {offset_y}, {width}, {height})")
            return False, None
        
        self.logger.info(f"ROI           : {width}x{height} at {offset_x},{offset_y}")
        
        # Remove pattern from pleora
        try:
            self.arv_camera.set_string("TestImageSelector", "Off")
        except gi.repository.GLib.Error as e:
            self.logger.error(f"{e}\nCould not remove pattern")
            return False, None
        
        # Set frame rate
        try:
            if self.cam_config.grab_fps >= 0:
                self.logger.info(f"Set frame rate to {self.cam_config.grab_fps}")
                self.arv_camera.set_frame_rate(self.cam_config.grab_fps)
            else:
                self.logger.info("Frame rate is untouched")
            
        except gi.repository.GLib.Error as e:
            self.logger.error(f"{e}\nCould not set frame rate")
            return False, None

        # Set Pixel format
        try:
            pixel_format_arv = getattr(Aravis, self.cam_config.pixel_format_str)
            self.arv_camera.set_pixel_format(pixel_format_arv)
            
        except gi.repository.GLib.Error as e:
            self.logger.error(f"{e}\nCould not set pixel format {self.cam_config.pixel_format_str}")
            return False, None
        
        pixel_format_string = self.arv_camera.get_pixel_format_as_string()

        self.logger.info(f"Pixel format  : {pixel_format_string} ({self.cam_config.pixel_format_str})")

        # Get payload
        payload = self.arv_camera.get_payload()
        
        self.logger.info(f"Payload       : {payload}")
        
        return True, payload
    
    def init_arv_stream(self, payload):
        arv_stream = self.arv_camera.create_stream(None, None)

        # Allocate aravis buffers
        for i in range(0,10):
            arv_stream.push_buffer(Aravis.Buffer.new_allocate(payload))

        self.logger.info("Start acquisition")
        self.arv_camera.start_acquisition()

        return arv_stream
    
    def release_cam_buffer(self, cam_buffer):
        self.arv_stream.push_buffer(cam_buffer)

    def get_next_frame(self):
        frame_flag = True
        # Get frame
        cam_buffer = self.arv_stream.pop_buffer()

        # Get raw buffer
        buf = cam_buffer.get_data()
        if len(buf) == 0:
            frame_np = None
            frame_flag = False

        if frame_flag:
            #self.logger.info(f"Bits per pixel {len(buf)/self.height/self.width}")
            if self.cam_config.pixel_format_str == "PIXEL_FORMAT_BAYER_GR_8":
                frame_raw = np.frombuffer(buf, dtype='uint8').reshape((self.cam_config.height, self.cam_config.width))
                # Bayer2RGB
                frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_BayerGR2RGB)
            elif self.cam_config.pixel_format_str == "PIXEL_FORMAT_MONO_8":
                    frame_raw = np.frombuffer(buf, dtype='uint8').reshape((self.cam_config.height, self.cam_config.width))
                    # Bayer2RGB
                    frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_GRAY2RGB)
            else:
                self.logger.info(f"Convertion from {self.cam_config.pixel_format_str} not supported")
                frame_np = None
        
        return frame_np, cam_buffer
    
    def stop_acquisition(self):
        try:
            self.arv_camera.stop_acquisition()
        except Exception as e:
            self.logger.error(f"Could not stop acquisition: {e}")
