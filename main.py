#!/usr/bin/env python3
# Joseph Schroedl
# Updated February 26, 2021


import os

import can
import cantools
from pprintpp import pprint as pp

# Dictionary to hold values parsed form CAN messages.
data = {}

db = cantools.database.load_file("DBC.dbc")
#pp(db.messages)

# Before doing anything close the interface if it's already open.
# This could happen if the script crashed and didn't get to execute the closing function.
os.system("sudo ifconfig can0 down")

# OLD -> The bitrate parameter needs to be set to 250000 to talk to the RMS (Motor Controller).
# The bitrate parameter needs to be set to 500000 to talk to the BMS
# (Battery Management System).
os.system("sudo ip link set can0 type can bitrate 500000")
os.system("sudo ifconfig can0 up")

can0 = can.interface.Bus(channel="can0", bustype="socketcan", bitrate=500000)  # socketcan_native

def get_data():
    msg = can0.recv(10.0)
    if msg is None:
        print("Timeout occurred, no message.")
    else:
        #print(msg.arbitration_id, msg.data)
        if msg.arbitration_id - 0x0A0 >= 0:
            decoded_msg = db.decode_message(msg.arbitration_id, msg.data)
            data["timestamp"] = msg.timestamp
            for k in decoded_msg.keys():
                data[k] = decoded_msg[k]
            #pp(decoded_msg)
            pp(data)

try:
    while True:
        get_data()
except KeyboardInterrupt:
    os.system("sudo ifconfig can0 down")
    print("\nExiting")
