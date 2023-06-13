#!/bin/bash

# Default vals
IP="127.0.0.1"
PORT=5000
H264=false

# Parse args
while [[ $# -ge 1 ]]
do
  key="$1"
  case $key in
    -h264)
    H264=true
    ;;
    
    -ip)
    IP="$2"
    ;;
  esac
  shift
done


if $H264 ; then
    echo "Sending H264 stream to $IP"
    gst-launch-1.0 videotestsrc ! videoconvert ! queue ! x264enc tune=zerolatency ! video/x-h264, stream-format=byte-stream ! rtph264pay config-interval=1 ! udpsink host=$IP port=$PORT
else
    echo "Sending H265 stream to $IP"
    gst-launch-1.0 videotestsrc ! videoconvert ! queue ! x265enc tune=zerolatency ! video/x-h265, stream-format=byte-stream ! rtph265pay config-interval=1 ! udpsink host=$IP port=$PORT
fi

