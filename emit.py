import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
from PIL import Image
import numpy as np
import cv2
import time
import sys

Gst.init(None)

class Gstreamer:
    def __init__(self, from_testvideo):
        self.from_testvideo = from_testvideo
        # GStreamer pipeline

        # create the elements
        if from_testvideo:
            self.source = Gst.ElementFactory.make("videotestsrc", "source")
        else:
            self.source = Gst.ElementFactory.make("appsrc", "appsrc")
            
        videoconvert = Gst.ElementFactory.make("videoconvert", "video-convert")
        capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        sink = Gst.ElementFactory.make("autovideosink", "sink")

        # create the empty pipeline
        self.pipeline = Gst.Pipeline.new("super-pipeline")

        if not self.pipeline or not self.source or not capsfilter or not videoconvert or not sink:
            print("ERROR: Not all elements could be created")
            sys.exit(1)

        # build the pipeline
        self.pipeline.add(self.source)
        self.pipeline.add(videoconvert)
        self.pipeline.add(capsfilter)
        self.pipeline.add(sink)

        if not self.source.link(capsfilter):
            print("ERROR: Could not link source to capsfilter")
            sys.exit(1)

        if not capsfilter.link(videoconvert):
            print("ERROR: Could not link capsfilter to videoconvert")
            sys.exit(1)

        if not videoconvert.link(sink):
            print("ERROR: Could not link videoconvert to sink")
            sys.exit(1)

        # modify the source's properties
        if from_testvideo:
            self.source.set_property("pattern", 0)
            capsfilter.set_property('caps', Gst.Caps.from_string('video/x-raw,format=(string)BGR,width=640,height=480,framerate=1/1'))
        else:
            capsfilter.set_property('caps', Gst.Caps.from_string('video/x-raw,format=(string)BGR,width=640,height=480,framerate=1/1'))
            # caps = Gst.Caps.from_string("video/x-raw,format=(string)BGR,width=640,height=480,framerate=1/1")
            # self.source.set_property("caps", caps)
            # self.source.set_property("format", Gst.Format.TIME)
        
        
        # start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)

        self.bus = self.pipeline.get_bus()


    def send_frame(self, frame_np):
    
        # Convert frame to GStreamer buffer
        frame_data = frame_np.tobytes()
        gst_buffer = Gst.Buffer.new_allocate(None, len(frame_data), None)
        gst_buffer.fill(0, frame_data)
        
        # Push buffer to the appsrc element
        if self.from_testvideo:
            pass
        else:
            self.source.emit('push-buffer', gst_buffer)

        terminate = False
        msg = self.bus.timed_pop_filtered(
            0,
            Gst.MessageType.STATE_CHANGED | Gst.MessageType.EOS | Gst.MessageType.ERROR)

        if not msg:
            return

        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            print("ERROR:", msg.src.get_name(), " ", err.message)
            if dbg:
                print("debugging info:", dbg)
            terminate = True
        elif t == Gst.MessageType.EOS:
            print("End-Of-Stream reached")
            terminate = True
        elif t == Gst.MessageType.STATE_CHANGED:
            # we are only interested in STATE_CHANGED messages from
            # the pipeline
            if msg.src == self.pipeline:
                old_state, new_state, pending_state = msg.parse_state_changed()
                print("Pipeline state changed from {0:s} to {1:s}".format(
                    Gst.Element.state_get_name(old_state),
                    Gst.Element.state_get_name(new_state)))
        else:
            # should not get here
            print("ERROR: Unexpected message received")
            return

        if terminate:
                self.destroy()
        
    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)
        sys.exit()
        
class FrameGenerator:
    def __init__(self, from_testvideo):
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

        self.gst = Gstreamer(from_testvideo)
    
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
    generator = FrameGenerator(from_testvideo=False)
    generator.frames_loop()