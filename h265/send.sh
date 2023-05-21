#!/bin/bash
IP="127.0.0.1"
gst-launch-1.0 videotestsrc ! videoconvert ! queue ! x265enc tune=zerolatency ! video/x-h265, stream-format=byte-stream ! rtph265pay ! udpsink host=$IP port=5000

