#!/bin/bash

# Default vals
H264=false

# Parse args
while [[ $# -ge 1 ]]
do
  key="$1"
  case $key in
    -h264)
    H264=true
    ;;
  esac
  shift
done


if $H264 ; then
    echo "Receiving H264 stream"
    set GST_DEBUG=*:3 && gst-launch-1.0 -e -v udpsrc port=5000 caps="application/x-rtp, media=(string)video, encoding-name=(string)H264" ! rtph264depay ! avdec_h264 ! videoconvert ! xvimagesink
else
    echo "Receiving H265 stream"
    set GST_DEBUG=*:3 && gst-launch-1.0 -e -v udpsrc port=5000 caps="application/x-rtp, media=(string)video, encoding-name=(string)H265" ! rtph265depay ! avdec_h265 ! videoconvert ! xvimagesink
fi



