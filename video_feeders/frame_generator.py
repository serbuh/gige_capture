import time
import cv2
import numpy as np

from video_feeders.video_feeder_interface import VideoFeeder

class FrameGenerator(VideoFeeder):
    def __init__(self, logger, cam_config):
        VideoFeeder.__init__(self, True)
        self.logger = logger
        self.cam_model = "Artificial"
        self.frames = []  # List of frames to be sent
        self.frame_counter = 0
        self.frame_width  = cam_config.width
        self.frame_height = cam_config.height
        self.grab_fps     = cam_config.grab_fps
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 2
        self.font_thickness = 3
        self.text_color = (255, 255, 255)  # White color
        self.bg_color = (0, 0, 0)  # Black color
    
    def get_next_frame(self):
        # Sleep
        time.sleep(1/self.grab_fps)

        # Create a black image
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        frame.fill(0)

        # Add counter text
        counter_text = f"Counter: {self.frame_counter}"
        text_size, _ = cv2.getTextSize(counter_text, self.font, self.font_scale, self.font_thickness)
        text_x = (self.frame_width - text_size[0]) // 2
        text_y = (self.frame_height + text_size[1]) // 2
        cv2.putText(frame, counter_text, (text_x, text_y), self.font, self.font_scale, self.text_color, self.font_thickness, cv2.LINE_AA)
        
        self.frame_counter += 1
        cam_buffer = None # In order to be generic and support aravis buffers

        return frame, cam_buffer
    
    def release_cam_buffer(self, cam_buffer):
        pass