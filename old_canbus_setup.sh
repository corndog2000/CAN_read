#!/bin/bash

sudo ip link set can0 down
sudo ip link set can0 type can restart
sudo ip link set can0 type can bitrate 500000 
sudo ip link set can0 up
