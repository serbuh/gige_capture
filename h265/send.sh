#!/bin/bash
IP="127.0.0.1"
PORT=5000
WIDTH=640
HEIGHT=480
RATE=25
gst-launch-1.0 videotestsrc ! video/x-raw,width=$WIDTH,height=$HEIGHT,framerate=$RATE/1 ! videoconvert ! queue ! x265enc tune=zerolatency ! video/x-h265, stream-format=byte-stream ! rtph265pay config-interval=1 ! udpsink host=$IP port=$PORT

