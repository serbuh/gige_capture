#!/bin/bash

# Default vals
IP="127.0.0.1"
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
    gst-launch-1.0 videotestsrc ! videoconvert ! queue ! x264enc tune=zerolatency ! video/x-h264, stream-format=byte-stream ! rtph264pay ! udpsink host=$IP port=5000
else
    echo "Sending H265 stream to $IP"
    gst-launch-1.0 videotestsrc ! videoconvert ! queue ! x265enc tune=zerolatency ! video/x-h265, stream-format=byte-stream ! rtph265pay ! udpsink host=$IP port=5000
fi

