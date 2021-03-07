#!/usr/bin/env python3
# Joseph Schroedl
# Updated March 5, 2021

import math
import os

import can
import cantools

from influxdb import InfluxDBClient
from pprintpp import pprint as pp

# Here is a list of each piece of data that could be received from the RMS.
keys = ["D1_Modulation_Index", "D2_Flux_Weakening_Output", "D3_Id_Command", "D4_Iq_Command", "D1_Commanded_Torque", "D2_Torque_Feedback", "D3_Power_On_Timer", "D1_Post_Fault_Lo", "D2_Post_Fault_Hi", "D3_Run_Fault_Lo", "D4_Run_Fault_Hi", "D1_VSM_State", "D1_PWM_Frequency", "D2_Inverter_State", "D3_Relay_1_Status", "D3_Relay_2_Status", "D3_Relay_3_Status", "D3_Relay_4_Status", "D3_Relay_5_Status", "D3_Relay_6_Status", "D4_Inverter_Run_Mode", "D4_Inverter_Discharge_State",
        "D5_Inverter_Command_Mode", "D5_Rolling_Counter", "D6_Inverter_Enable_State", "D6_Inverter_Enable_Lockout", "D7_Direction_Command", "D7_BMS_Active", "D7_BMS_Torque_Limiting", "D7_Max_Speed_Limiting", "D7_Low_Speed_Limiting", "D1_Flux_Command", "D2_Flux_Feedback", "D3_Id", "D4_Iq", "D1_DC_Bus_Voltage", "D2_Output_Voltage", "D3_VAB_Vd_Voltage", "D4_VBC_Vq_Voltage", "D1_Phase_A_Current", "D2_Phase_B_Current", "D3_Phase_C_Current", "D4_DC_Bus_Current", "D1_Motor_Angle_Electrical",
        "D2_Motor_Speed", "D3_Electrical_Output_Frequency", "D4_Delta_Resolver_Filtered", "D1_Digital_Input_1", "D2_Digital_Input_2", "D3_Digital_Input_3", "D4_Digital_Input_4", "D5_Digital_Input_5", "D6_Digital_Input_6", "D7_Digital_Input_7", "D8_Digital_Input_8", "D1_Analog_Input_1", "D2_Analog_Input_2", "D3_Analog_Input_3", "D4_Analog_Input_4", "D5_Analog_Input_5", "D6_Analog_Input_6", "D1_Project_Code_EEP_Ver", "D2_SW_Version", "D3_DateCode_MMDD", "D4_DateCode_YYYY",
        "D1_Reference_Voltage_1_5", "D2_Reference_Voltage_2_5", "D3_Reference_Voltage_5_0", "D4_Reference_Voltage_12_0", "D1_RTD4_Temperature", "D2_RTD5_Temperature", "D3_Motor_Temperature", "D4_Torque_Shudder", "D1_Control_Board_Temperature", "D2_RTD1_Temperature", "D3_RTD2_Temperature", "D4_RTD3_Temperature", "D1_Module_A", "D2_Module_B", "D3_Module_C", "D4_Gate_Driver_Board"]


# Dictionary to hold values parsed form CAN messages.
data = {}

# Fill the dictionary with keys
for i in keys:
    data[i] = None


db = cantools.database.load_file("/home/pi/Documents/CAN_read/DBC.dbc")
# pp(db.messages)

# Before doing anything close the interface if it's already open.
# This could happen if the script crashed and didn't get to execute the closing function.
os.system("sudo ifconfig can0 down")

# OLD -> The bitrate parameter needs to be set to 250000 to talk to the RMS (Motor Controller).
# The bitrate parameter needs to be set to 500000 to talk to the BMS
# (Battery Management System).
os.system("sudo ip link set can0 type can bitrate 500000")
os.system("sudo ifconfig can0 up")

can0 = can.interface.Bus(channel="can0", bustype="socketcan",
                         bitrate=500000)  # socketcan_native

# Connect to the Influx Database
client = InfluxDBClient(host="localhost", port=8086,
                        username="pi", password="solarpack", database="TELEMETRY")

def all_equal(input_dict, expected_value):
    return all(value == expected_value for value in input_dict.values())

def get_data():
    msg = can0.recv(10.0)
    if msg is not None:
        #print(msg.arbitration_id, msg.data)
        if msg.arbitration_id - 0x0A0 >= 0:
            decoded_msg = db.decode_message(msg.arbitration_id, msg.data)
            for k in decoded_msg.keys():
                data[k] = decoded_msg[k]
            # pp(decoded_msg)


def write_data():
    # If every value in data is None, meaning we have nothing to write, then skip writing to DB.
    if all_equal(data, None):
        return
    # Must have a space after message to tell the query that you are entering fields
    line = "RMS"
    sep = " "
    for k, v in data.items():
        if v != None:    
            if type(v) == str:
                toAdd = (sep + str(k) + "=\"" + str(v) + "\"")
            else:
                toAdd = (sep + str(k) + "=" + str(v))
            sep = ","
            line = (line + toAdd)
    line = [line]
    #print(line)
    client.write_points(points=line, time_precision="ms", protocol="line")

try:
    while True:
        get_data()
        write_data()
except KeyboardInterrupt:
    os.system("sudo ifconfig can0 down")
    print("\nExiting")
