#!/bin/bash
set GST_DEBUG=*:3 && gst-launch-1.0 -e -v udpsrc port=5000 caps="application/x-rtp, media=(string)video, encoding-name=(string)H265" ! rtph265depay ! avdec_h265 ! videoconvert ! xvimagesink
