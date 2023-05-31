import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from PIL import Image
import numpy as np
import cv2
import time

Gst.init(None)

class Gstreamer:
    def __init__(self):
        # GStreamer pipeline
        pipeline_str = f"appsrc name=source is-live=true ! videoconvert ! video/x-raw,format=BGR ! videoconvert ! xvimagesink"
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsrc = self.pipeline.get_by_name("source")
        self.pipeline.set_state(Gst.State.PLAYING)

    def send_frame(self, frame_np):
        # Convert frame to GStreamer buffer
        frame_data = frame_np.tobytes()
        gst_buffer = Gst.Buffer.new_allocate(None, len(frame_data), None)
        gst_buffer.fill(0, frame_data)

        # Push buffer to the appsrc element
        self.appsrc.emit('push-buffer', gst_buffer)
    
    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)
        
class FrameGenerator:
    def __init__(self):
        self.frames = []  # List of frames to be sent
        self.frame_num = 100
        self.frame_counter = 0
        self.frame_width = 640
        self.frame_height = 480
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 2
        self.font_thickness = 3
        self.text_color = (255, 255, 255)  # White color
        self.bg_color = (0, 0, 0)  # Black color

        self.gst = Gstreamer()
    
    def get_next_frame(self):
        if self.frame_counter < self.frame_num:
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
            return frame
        
        return None
    
    def show_frame(self, frame):
        # Display the frame
        cv2.imshow('Frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            exit()

    def frames_loop(self):
        # Run the frame generation and pipeline
        while True:
            frame_np = self.get_next_frame()
            if frame_np is None:
                break

            self.gst.send_frame(frame_np)

            # Show the frame
            self.show_frame(frame_np)
            time.sleep(1)

        # Stop the pipeline
        self.gst.destroy()

        # Close windows
        cv2.destroyAllWindows()



if __name__ == "__main__":
    generator = FrameGenerator()
    generator.frames_loop()