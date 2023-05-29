#!/usr/bin/env python

#  If you have installed aravis in a non standard location, you may need
#   to make GI_TYPELIB_PATH point to the correct location. For example:
#
#   export GI_TYPELIB_PATH=$GI_TYPELIB_PATH:/opt/bin/lib/girepositry-1.0/
#
#  You may also have to give the path to libaravis.so, using LD_PRELOAD or
#  LD_LIBRARY_PATH.

import sys
import gi
import time
import numpy as np

gi.require_version ('Aravis', '0.8')

from gi.repository import Aravis

Aravis.enable_interface ("Fake")

try:
    if len(sys.argv) > 1:
        camera = Aravis.Camera.new (sys.argv[1])
    else:
        camera = Aravis.Camera.new (None)
except TypeError:
    print("No camera found")
    exit()
except Exception as e:
    print(f"Some problem with camera: {e}")
    exit()

camera.set_region (0,0,1600,1200)
camera.set_frame_rate (20.0)
camera.set_pixel_format (Aravis.PIXEL_FORMAT_MONO_8)


####################################################################

payload = camera.get_payload ()

[x,y,width,height] = camera.get_region ()

print ("Camera vendor : %s" %(camera.get_vendor_name ()))
print ("Camera model  : %s" %(camera.get_model_name ()))
print ("ROI           : %dx%d at %d,%d" %(width, height, x, y))
print ("Payload       : %d" %(payload))
print ("Pixel format  : %s" %(camera.get_pixel_format_as_string ()))

stream = camera.create_stream (None, None)

for i in range(0,10):
	stream.push_buffer (Aravis.Buffer.new_allocate (payload))
        
print ("Start acquisition")

camera.start_acquisition ()

print ("Acquisition")
#####################################################################
def grab_loop(stream):
    count = 0
    try:
        
        while True:
            # Get frame
            image = stream.pop_buffer()

            # Get MONO8 raw frame
            rawFrame = np.frombuffer(image.get_data(), dtype='uint8').reshape( (height, width) )
            ts = time.time()
            count += 1
            
            print(f"{count}")

            #import ipdb; ipdb.set_trace()
                    #print (image)
            if image:
                stream.push_buffer(image)
            
            if count>100:
                break
    except KeyboardInterrupt:
        print("Interrupted by Ctrl+C")
    except Exception:
        import traceback; traceback.print_exc()
        print('exc..')
    finally:
        print ("Stop acquisition")
        camera.stop_acquisition ()

grab_loop(stream)