#!/usr/bin/env python

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

gi.require_version('Aravis', '0.8')
gi.require_version('Gst', '1.0')
from gi.repository import Aravis, Gst

Aravis.enable_interface("Fake")

class GstSender():
    def __init__(self, fps):
        host = "127.0.0.1"
        port = 5000
        self.fps = fps

        # Initialize GStreamer
        Gst.init(None)

        # Create a GStreamer pipeline
        #self.pipeline = Gst.parse_launch("appsrc name=src ! videoconvert ! video/x-raw,format=I420 ! xvimagesink")
        self.pipeline = Gst.parse_launch("appsrc name=src ! videoconvert ! queue ! x264enc tune=zerolatency ! video/x-h264, stream-format=byte-stream ! rtph264pay ! udpsink host=127.0.0.1 port=5000")

        # Get the appsrc element from the pipeline
        self.appsrc = self.pipeline.get_by_name("src")
        self.appsrc.set_property("format", Gst.Format.TIME)

        # Start the pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        
        #self.udp_writer = cv2.VideoWriter(f'appsrc ! queue ! videoconvert ! queue ! video/x-raw, width=(int){self.width}, height=(int){self.height}, framerate=(fraction){int(self.fps)}/1, format=(string)BAYER_GR8 ! x265enc speed-preset=superfast tune=zerolatency ! h265parse ! rtph265pay ! udpsink host={host} port={port} sync=false', cv2.CAP_GSTREAMER, 0, 20, (self.width, self.height), True)
        #
    
    def send_frame(self, frame_to_show):
        # Convert the frame to a GStreamer buffer
        gst_buffer = Gst.Buffer.new_wrapped(frame_to_show.tobytes())

        # Set the timestamp and duration of the buffer
        gst_buffer.pts = gst_buffer.dts = Gst.CLOCK_TIME_NONE
        gst_buffer.duration = int(1e9 / self.fps)

        # Push the buffer to the appsrc element
        self.appsrc.emit("push-buffer", gst_buffer)
        #self.udp_writer.write(frame_to_show)
    
    def destroy(self):
        self.pipeline.set_state(Gst.State.NULL)
        

class Grabber():
    def __init__(self, send_frames, show_frames, arv_debug=False):
        if arv_debug:
            os.environ["ARV_DEBUG"]="all"

        try:
            if len(sys.argv) > 1:
                self.camera = Aravis.Camera.new (sys.argv[1])
            else:
                self.camera = Aravis.Camera.new (None)
        except TypeError:
            print("No camera found")
            exit()
        except Exception as e:
            print(f"Some problem with camera: {e}")
            exit()
        
        cam_vendor = self.camera.get_vendor_name()
        cam_model = self.camera.get_model_name()
        print (f"Camera vendor : {cam_vendor}")
        print (f"Camera model  : {cam_model}")

        if cam_model == "Blackfly BFLY-PGE-20E4C": # FLIR
            x, y, w, h = 0, 0, 1280, 1024
            self.fps = 20.0
            self.pixel_format = Aravis.PIXEL_FORMAT_MONO_8
        
        elif cam_model == "mvBlueCOUGAR-X102eC": #BlueCOUGAR-X
            x, y, w, h = 0, 0, 1280, 1024
            self.fps = 20.0
            self.pixel_format = Aravis.PIXEL_FORMAT_BAYER_GR_8
            #self.pixel_format = Aravis.PIXEL_FORMAT_RGB_8_PACKED
            #self.pixel_format = Aravis.PIXEL_FORMAT_YUV_422_PACKED
            #self.pixel_format = Aravis.PIXEL_FORMAT_YUV_422_YUYV_PACKED
            
        else: # Default
            x, y, w, h = 0, 0, 640, 480
            self.fps = 10.0
            self.pixel_format = Aravis.PIXEL_FORMAT_MONO_8
        
        # Set camera params
        try:
            self.camera.set_region(x,y,w,h)
        except gi.repository.GLib.Error as e:
            print(f"{e}\nCould not set camera params. Camera is already in use?")
            exit()
        self.camera.set_frame_rate(self.fps)
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
    
        # Show frames options
        self.show_frames = show_frames
        if self.show_frames:
            self.window_name = "Frames"
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        
        # Send frames options
        if send_frames:
            self.gst_sender = GstSender(self.fps)
        else:
            self.gst_sender = None

    def grab_loop(self):
        count = 0
            
        while True:
            try:

                # Get frame
                image = self.stream.pop_buffer()

                ts = time.time()
                count += 1
                print(f"{count}")

                self.do_things_with_frame(image)
                
                if image:
                    self.stream.push_buffer(image)
                
                # cv2 window key
                key = cv2.waitKey(1)&0xff
                if key == ord('q'):
                    break
                
            except KeyboardInterrupt:
                print("Interrupted by Ctrl+C")
                self.camera.stop_acquisition()
                if self.gst_sender is not None:
                    self.gst_sender.destroy()
                exit()
            except Exception:
                import traceback; traceback.print_exc()
                print(f'Exception on frame {count}')
    
    def do_things_with_frame(self, image):
        # Get raw buffer
        buf = image.get_data()
        #print(f"Bits per pixel {len(buf)/self.height/self.width}")
        if self.pixel_format == Aravis.PIXEL_FORMAT_BAYER_GR_8:
            frame_raw = np.frombuffer(buf, dtype='uint8').reshape( (self.height, self.width) )

            # Bayer2RGB
            frame_to_show = cv2.cvtColor(frame_raw, cv2.COLOR_BayerGR2GRAY)
            
            # Take only Y
            #buf=buf[:self.height*self.width]
        else:
            print(f"Convertion from {self.pixel_format_string} not supported")
            frame_to_show = None
                
        if self.show_frames and frame_to_show is not None:
            #rawFrame = cv2.cvtColor(rawFrame, cv2.COLOR_GRAY2BGR)
            cv2.imshow(self.window_name, frame_to_show)
        
        if self.gst_sender is not None:
            self.gst_sender.send_frame(frame_to_show)
        
        

####################################################################

grabber = Grabber(send_frames=True, show_frames=True, arv_debug=True)
grabber.grab_loop()