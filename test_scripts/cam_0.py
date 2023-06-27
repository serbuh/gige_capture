import logging
import gi
import numpy as np
import cv2

gi.require_version('Aravis', '0.8')
from gi.repository import Aravis

# Set logger
logger = logging.getLogger("Grabber")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
ch.setFormatter(clear_with_time_msec_format)
logger.addHandler(ch)
logger.info("Welcome to Grabber")

# Connect to camera
arv_camera = Aravis.Camera.new("192.168.132.210")
cam_vendor = arv_camera.get_vendor_name()
logger.info(f"Camera vendor : {cam_vendor}")
cam_model = arv_camera.get_model_name()
logger.info(f"Camera model  : {cam_model}")

# Set params
x = 320
y = 240
w = 640
h = 480
arv_camera.set_region(x, y, w, h)
arv_camera.set_frame_rate(20)
pixel_format = Aravis.PIXEL_FORMAT_BAYER_GR_8
arv_camera.set_pixel_format(pixel_format)
payload = arv_camera.get_payload()
logger.info(f"Payload       : {payload}")

# Init stream
arv_stream = arv_camera.create_stream(None, None)

# Allocate aravis buffers
for i in range(0,10):
    arv_stream.push_buffer(Aravis.Buffer.new_allocate(payload))

logger.info("Start acquisition")
arv_camera.start_acquisition()

frame_number = 0
while True:
    print(frame_number)
    # Get frame
    cam_buffer = arv_stream.pop_buffer()

    # Get raw buffer
    buf = cam_buffer.get_data()
    if len(buf) == 0: continue
    
    if pixel_format == Aravis.PIXEL_FORMAT_BAYER_GR_8:
        frame_raw = np.frombuffer(buf, dtype='uint8').reshape((h, w))
        # Bayer2RGB
        frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_BayerGR2RGB)
    elif pixel_format == Aravis.PIXEL_FORMAT_MONO_8:
        frame_raw = np.frombuffer(buf, dtype='uint8').reshape((h, w))
        # Bayer2RGB
        frame_np = cv2.cvtColor(frame_raw, cv2.COLOR_GRAY2RGB)
    else:
        logger.error("AAA")
        frame_np = None

    # Show frame
    if True:
        cv2.imshow("0", frame_np)

    # Release buffer
    arv_stream.push_buffer(cam_buffer)

    # cv2 window key
    key = cv2.waitKey(1)&0xff
    if key == ord('q'):
        logger.error("Bye")
        arv_camera.stop_acquisition()
        exit()
    
    frame_number+=1
