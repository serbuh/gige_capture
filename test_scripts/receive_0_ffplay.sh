#!/bin/bash
#PORT=50010
#set GST_DEBUG=*:3 && gst-launch-1.0 -e -v udpsrc port=$PORT caps="application/x-rtp, media=(string)video, encoding-name=(string)H265" ! rtph265depay ! avdec_h265 ! videoconvert ! xvimagesink


ffplay -udp 127.0.0.1:50010