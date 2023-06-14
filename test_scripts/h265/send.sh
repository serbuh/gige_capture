#!/bin/bash
#IP="127.0.0.1"
#PORT=5000
IP="192.168.132.60"
PORT=1212
WIDTH=640
HEIGHT=480
RATE=20
gst-launch-1.0 videotestsrc pattern=ball ! video/x-raw,width=$WIDTH,height=$HEIGHT,framerate=$RATE/1 ! videoconvert ! queue ! x265enc tune=zerolatency ! video/x-h265, stream-format=byte-stream ! rtph265pay config-interval=1 ! udpsink host=$IP port=$PORT

