#!/bin/bash

echo "Welcome to the Vision Launcher"

tmux_session_name=vision

usage="
Usage

options:
  -h, --help               = Show help
  -k, --kill               = Kill tmux session
  -c, --client             = Run with client
  "

kill_and_exit=false
run_client=false

# Parse args
while [[ $# -ge 1 ]]; do
  key="$1"
  case $key in
    
    -h|--help)
      echo "$usage"
      exit
      ;;

    -k|--kill)
      kill_and_exit=true
      ;;
    
    -c|--client)
      run_client=true
      ;;

  esac
  shift
done

echo "Kill previous tmux session ($tmux_session_name)"
tmux kill-session -t $tmux_session_name >/dev/null 2>&1

if $kill_and_exit; then
  echo "Born to kill."
  exit 0
fi

sleep 0.1s

echo "Create new tmux session ($tmux_session_name)"
tmux new -d -s $tmux_session_name

# Run server
run_cmd='python grab.py'
tmux new-window -n main -t $tmux_session_name $run_cmd
tmux set-option -w -t 0 remain-on-exit on

if $run_client; then
  # Run client
  run_cmd='python client.py'
  tmux split-window -t $tmux_session_name $run_cmd

  # Return to server's pane
  tmux select-pane -t 0
fi

# Attach
tmux a