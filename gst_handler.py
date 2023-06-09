import gi
import sys
gi.require_version('Gst', '1.0')
from gi.repository import Gst

class GstSender:
    def __init__(self, logger, gst_destination, bitrate_h265, send_fps, show_frames_gst, send_frames_gst, from_testvideo):
        self.logger = logger
        self.host = gst_destination[0]
        self.port = gst_destination[1]
        self.send_fps = send_fps
        self.send_frames_gst = send_frames_gst
        self.show_frames_gst = show_frames_gst
        self.from_testvideo = from_testvideo

        self.pipeline_video_read() # Create the video read part of the pipeline
        
        self.pipeline_splitter()

        if self.show_frames_gst:
            self.create_show_pipeline()
        if self.send_frames_gst:
            self.create_send_pipeline(bitrate_h265)
        
        # start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.info("ERROR: Unable to set the pipeline to the playing state")
            sys.exit(1)

        self.bus = self.pipeline.get_bus()

    def add_element_and_link(self, element_type, element_name, link_to=None):
        if self.pipeline is None:
            self.logger.info(f"ERROR: {element_name} ({element_type}) not initialized")
            sys.exit(1)

        # Create element
        new_element = Gst.ElementFactory.make(element_type, element_name)
        if not new_element:
            self.logger.info(f"ERROR: Can not create {element_name} ({element_type})")
            sys.exit(1)
        
        # Add element to pipeline
        self.pipeline.add(new_element)
        
        # Link elements
        if link_to is not None:
            element_to_link_to = self.pipeline.get_by_name(link_to)
            if not element_to_link_to:
                self.logger.info(f"ERROR: Could not retrive an element to link to ({link_to}) for {element_name} ({element_type})")
                sys.exit(1)
            if not element_to_link_to.link(new_element):
                self.logger.info(f"ERROR: Could not link {element_name} ({element_type}) to {element_to_link_to}")
                sys.exit(1)

    def pipeline_video_read(self):
        # Initialize GStreamer
        Gst.init(None)

        # Create the empty pipeline
        self.pipeline = Gst.Pipeline.new("super-pipeline")
        if not self.pipeline:
            self.logger.info("ERROR: Could not create pipeline")
            sys.exit(1)

        if self.from_testvideo:
            self.add_element_and_link("videotestsrc", "source") # Add source
            self.pipeline.get_by_name('source').set_property("pattern", 0)
        else:
            self.add_element_and_link("appsrc", "source") # Add source

        self.add_element_and_link("capsfilter", "capsfilter", link_to="source") # Create capsfilter
        self.pipeline.get_by_name('capsfilter').set_property('caps', Gst.Caps.from_string(f'video/x-raw,format=(string)BGR,width=640,height=480,framerate={int(self.send_fps)}/1'))
        self.add_element_and_link("videoconvert", "videoconvert_after_read", link_to="capsfilter") # Create videoconvert

    def pipeline_splitter(self):
        self.add_element_and_link("tee", "splitter", link_to="videoconvert_after_read") # Create splitter

    def create_send_pipeline(self, bitrate_h265):
        self.add_element_and_link("queue", "send_video_queue", link_to="splitter") # Create queue
        self.add_element_and_link("capsfilter", "capsfilter2", link_to="send_video_queue") # Create capsfilter2
        self.pipeline.get_by_name('capsfilter2').set_property('caps', Gst.Caps.from_string(f'video/x-raw,format=(string)I420,width=640,height=480,framerate={int(self.send_fps)}/1'))
        self.add_element_and_link("queue", "queue", link_to="capsfilter2") # Create queue
        self.add_element_and_link("x265enc", "x265enc", link_to="queue") # Create x265enc
        self.pipeline.get_by_name("x265enc").set_property('tune', 'zerolatency') # x265enc tune=zerolatency to ensure less delay
        self.pipeline.get_by_name("x265enc").set_property('bitrate', bitrate_h265)
        #self.pipeline.get_by_name("x265enc").set_property('intra-refresh', 'true') # TODO

        self.add_element_and_link("capsfilter", "capsfilter3", link_to="x265enc") # Create capsfilter3
        self.pipeline.get_by_name('capsfilter3').set_property('caps', Gst.Caps.from_string('video/x-h265, stream-format=byte-stream'))
        self.add_element_and_link("rtph265pay", "rtph265pay", link_to="capsfilter3") # Create rtph265pay
        self.pipeline.get_by_name("rtph265pay").set_property('config-interval', 1) # Send VPS, SPS, PPS in order to tell receiver to get the frames even if it started after sender
        self.add_element_and_link("udpsink", "udpsink", link_to="rtph265pay") # Create udpsink
        self.logger.info(f"udpsink set to: {self.host}:{self.port}")
        self.pipeline.get_by_name("udpsink").set_property('host', self.host)
        self.pipeline.get_by_name("udpsink").set_property('port', self.port)

    def create_show_pipeline(self):
        self.add_element_and_link("queue", "show_video_queue", link_to="splitter") # Create queue
        self.add_element_and_link("autovideosink", "sink", link_to="show_video_queue") # Create autovideosink

    def change_bitrate(self, new_bitrate):
        # NOTE: Not in use
        self.logger.info(f"Changing bitrate to {new_bitrate}")
        #self.pipeline.get_by_name("x265enc").set_property('bitrate', new_bitrate)
        #self.pipeline.get_by_name('capsfilter').set_property('caps', Gst.Caps.from_string(f'video/x-raw,format=(string)BGR,width=640,height=480,framerate=10/1'))
        #self.pipeline.get_by_name('capsfilter2').set_property('caps', Gst.Caps.from_string(f'video/x-raw,format=(string)I420,width=640,height=480,framerate=10/1'))
        self.logger.info("Changed (maybe)")     


    def send_frame(self, frame_np):
    
        # Convert frame to GStreamer buffer
        frame_data = frame_np.tobytes()
        gst_buffer = Gst.Buffer.new_allocate(None, len(frame_data), None)
        gst_buffer.fill(0, frame_data)
        
        # Push buffer to the appsrc element
        if self.from_testvideo:
            pass
        else:
            self.pipeline.get_by_name('source').emit('push-buffer', gst_buffer)

        terminate = False
        msg = self.bus.timed_pop_filtered(
            0,
            Gst.MessageType.STATE_CHANGED | Gst.MessageType.EOS | Gst.MessageType.ERROR)

        if not msg:
            return

        t = msg.type
        if t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            self.logger.info("ERROR:", msg.src.get_name(), " ", err.message)
            if dbg:
                self.logger.info("debugging info:", dbg)
            terminate = True
        elif t == Gst.MessageType.EOS:
            self.logger.info("End-Of-Stream reached")
            terminate = True
        elif t == Gst.MessageType.STATE_CHANGED:
            # we are only interested in STATE_CHANGED messages from
            # the pipeline
            if msg.src == self.pipeline:
                old_state, new_state, pending_state = msg.parse_state_changed()
                self.logger.info("Pipeline state changed from {0:s} to {1:s}".format(
                    Gst.Element.state_get_name(old_state),
                    Gst.Element.state_get_name(new_state)))
        else:
            # should not get here
            self.logger.info("ERROR: Unexpected message received")
            return

        if terminate:
                self.destroy()
        
    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)
