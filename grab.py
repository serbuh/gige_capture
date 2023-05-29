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

import gi
import numpy as np
import cv2

gi.require_version('Aravis', '0.8')

from gi.repository import Aravis

Aravis.enable_interface("Fake")

class Grabber():
    def __init__(self, show_frames):
        self.show_frames = show_frames
        if show_frames:
            pass#self.win = cv2.namedWindow("Frames", 0)

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

        self.camera.set_region (0,0,1600,1200)
        self.camera.set_frame_rate (20.0)
        self.camera.set_pixel_format (Aravis.PIXEL_FORMAT_MONO_8)

        payload = self.camera.get_payload ()

        [x, y, self.width, self.height] = self.camera.get_region ()

        print (f"Camera vendor : {self.camera.get_vendor_name()}")
        print (f"Camera model  : {self.camera.get_model_name()}")
        print (f"ROI           : {self.width,}x{self.height} at {x},{y}")
        print (f"Payload       : {payload}")
        print (f"Pixel format  : {self.camera.get_pixel_format_as_string()}")

        self.stream = self.camera.create_stream (None, None)

        # Allocate aravis buffers
        for i in range(0,10):
            self.stream.push_buffer (Aravis.Buffer.new_allocate (payload))

        print ("Start acquisition")

        self.camera.start_acquisition ()

        print ("Acquisition")
    
    def grab_loop(self):
        count = 0
        try:
            
            while True:
                # Get frame
                image = self.stream.pop_buffer()

                ts = time.time()
                count += 1
                print(f"{count}")

                # Get MONO8 raw frame
                rawFrame = np.frombuffer(image.get_data(), dtype='uint8').reshape( (self.height, self.width) )
                
                if self.show_frames:
                    self.show_frame(rawFrame)


                #import ipdb; ipdb.set_trace()
                        #print (image)
                if image:
                    self.stream.push_buffer(image)
                
                if count>100:
                    break
        except KeyboardInterrupt:
            print("Interrupted by Ctrl+C")
        except Exception:
            import traceback; traceback.print_exc()
            print('exc..')
        finally:
            print ("Stop acquisition")
            self.camera.stop_acquisition ()
    
    def show_frame(self, rawFrame):
        rawFrame

####################################################################

grabber = Grabber(show_frames=True)
grabber.grab_loop()