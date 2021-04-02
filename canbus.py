#!/usr/bin/env python3
# Joseph Schroedl
# Updated March 25, 2021

import math
import os
import time

import can
import cantools

from influxdb import InfluxDBClient
from pprintpp import pprint as pp

# Enable extra print messages
verbose = False

# If this variable is true then the program will store all 82 variables into the database
all_keys = True

if all_keys:
    # Here is a list of each piece of data that could be received from the RMS.
    allowed_keys_RMS = ["D1_Modulation_Index", "D2_Flux_Weakening_Output", "D3_Id_Command", "D4_Iq_Command", "D1_Commanded_Torque", "D2_Torque_Feedback", "D3_Power_On_Timer", "D1_Post_Fault_Lo", "D2_Post_Fault_Hi", "D3_Run_Fault_Lo", "D4_Run_Fault_Hi", "D1_VSM_State", "D1_PWM_Frequency", "D2_Inverter_State", "D3_Relay_1_Status", "D3_Relay_2_Status", "D3_Relay_3_Status", "D3_Relay_4_Status", "D3_Relay_5_Status", "D3_Relay_6_Status", "D4_Inverter_Run_Mode", "D4_Inverter_Discharge_State",
                    "D5_Inverter_Command_Mode", "D5_Rolling_Counter", "D6_Inverter_Enable_State", "D6_Inverter_Enable_Lockout", "D7_Direction_Command", "D7_BMS_Active", "D7_BMS_Torque_Limiting", "D7_Max_Speed_Limiting", "D7_Low_Speed_Limiting", "D1_Flux_Command", "D2_Flux_Feedback", "D3_Id", "D4_Iq", "D1_DC_Bus_Voltage", "D2_Output_Voltage", "D3_VAB_Vd_Voltage", "D4_VBC_Vq_Voltage", "D1_Phase_A_Current", "D2_Phase_B_Current", "D3_Phase_C_Current", "D4_DC_Bus_Current", "D1_Motor_Angle_Electrical",
                    "D2_Motor_Speed", "D3_Electrical_Output_Frequency", "D4_Delta_Resolver_Filtered", "D1_Digital_Input_1", "D2_Digital_Input_2", "D3_Digital_Input_3", "D4_Digital_Input_4", "D5_Digital_Input_5", "D6_Digital_Input_6", "D7_Digital_Input_7", "D8_Digital_Input_8", "D1_Analog_Input_1", "D2_Analog_Input_2", "D3_Analog_Input_3", "D4_Analog_Input_4", "D5_Analog_Input_5", "D6_Analog_Input_6", "D1_Project_Code_EEP_Ver", "D2_SW_Version",
                    "D1_Reference_Voltage_1_5", "D2_Reference_Voltage_2_5", "D3_Reference_Voltage_5_0", "D4_Reference_Voltage_12_0", "D1_RTD4_Temperature", "D2_RTD5_Temperature", "D3_Motor_Temperature", "D4_Torque_Shudder", "D1_Control_Board_Temperature", "D2_RTD1_Temperature", "D3_RTD2_Temperature", "D4_RTD3_Temperature", "D1_Module_A", "D2_Module_B", "D3_Module_C", "D4_Gate_Driver_Board"]

    allowed_keys_BMS = ["Pack_Current", "Pack_Inst_Voltage", "Pack_SOC", "Relay_State", "CRC_Checksum", "Avg_Cell_Voltage", "High_Cell_Voltage", "DTC_Flags_1", "DTC_Flags_2", "Populated_Cells", "Max_Cell_Number", "HEM_Mode", "Low_Opencell_ID", "High_Opencell_ID", "High_Intres_ID", "Low_Intres_ID", "Input_Supply_Voltage", "J1772_AC_Power_Limit", "J1772_AC_Voltage", "Low_Opencell_Voltage", "High_Opencell_Voltage", "Avg_Opencell_Voltage", "Low_Cell_Resistance",
                        "High_Cell_Resistance", "Avg_Cell_Resistance", "Low_Cell_Voltage_ID", "Total_Pack_Cycles", "Average_Temperature", "Internal_Temperature", "J1772_Plug_State", "J1772_AC_Current_Limit", "Low_Cell_Voltage", "Pack_CCL", "Pack_Open_Voltage", "Pack_Amphours", "Pack_Resistance", "Pack_DOD", "Pack_Summed_Voltage", "Pack_Abs_Current_Unsigned", "Pack_DCL", "Blank", "High_Temperature", "Low_Temperature", "Failsafe_Statuses", "CellId", "CellVoltage",
                        "CellResistance", "CellBalancing", "CellOpenVoltage", "Checksum"]

else:
    # Key filter. Only these values will be written to the database
    allowed_keys_RMS = ["D1_Control_Board_Temperature"]

    allowed_keys_BMS = []

# Keeps track of last time the loop ran
prev_time = 0

# Dictionary to hold values parsed form CAN messages from the RMS.
dataRMS = {}

# Dictionary to hold values parsed form CAN messages from the BMS.
dataBMS = {}

dataCELLS = {}

# Fill the dictionary with keys
for i in allowed_keys_RMS:
    dataRMS[i] = None

for i in allowed_keys_BMS:
    dataBMS[i] = None

for i in range(0, 164):
    dataCELLS[i] = {"CellId":i, "CellVoltage":0, "CellResistance":0, "CellBalancing":0, "CellOpenVoltage":0}

# This variable is used to tell if we have collected a good amount of cell data such that we shouldn't have any empty information in "dataCELLS"
cell_count = 0

# Load the CAN database for the BMS
dbBMS = cantools.database.load_file("/home/pi/Documents/CAN_read/DBC_BMS.dbc")

# Load the CAN database for the RMS
dbRMS = cantools.database.load_file("/home/pi/Documents/CAN_read/DBC_RMS.dbc")
# pp(dbRMS.messages)

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

print("\nCreated CAN interfafce connector")

# Connect to the Influx Database
client = InfluxDBClient(host="localhost", port=8086,
                        username="pi", password="solarpack", database="TELEMETRY")
print("\nConnected to TELEMETRY database")

clientCELLS = InfluxDBClient(host="localhost", port=8086,
                        username="pi", password="solarpack", database="CELLS")
print("\nConnected to CELLS database")


def get_time():
    ms = time.time_ns() // 1_000_000
    return ms


def all_equal(input_dict, expected_value):
    return all(value == expected_value for value in input_dict.values())


def get_data():
    msg = can0.recv(10.0)

    if msg is not None:
        # This section is for processing individual battery cell canbus messages
        '''
        if msg.arbitration_id == 0x036:
            cellID = msg.data[0]
            instantVoltage = (msg.data[1] << 8) |  msg.data[2]
            shunting = (msg.data[3] & 128) == 128
            internalResistance = ((msg.data[3] & 127) << 8) | msg.data[4]
            openVoltage = (msg.data[5] << 8) | msg.data[6]

            checksum = 0x036 + 8 + msg.data[0] + msg.data[1] + msg.data[2] + msg.data[3] + msg.data[4] + msg.data[5] + msg.data[6] - 256

            # The checksum byte didn't match the calculated checksum so the canbus message is corrupted.
            if checksum != msg.data[7]:
                print("Bad Checksum")
                return
        '''

        # Parse CELL CAN messages
        if (msg.arbitration_id == 0x36):
            decoded_msg = dbBMS.decode_message(msg.arbitration_id, msg.data)

            try:
                dataCELLS[decoded_msg["CellId"]]["CellVoltage"] = decoded_msg["CellVoltage"]
                dataCELLS[decoded_msg["CellId"]]["CellResistance"] = decoded_msg["CellResistance"]
                dataCELLS[decoded_msg["CellId"]]["CellBalancing"] = decoded_msg["CellBalancing"]
                dataCELLS[decoded_msg["CellId"]]["CellOpenVoltage"] = decoded_msg["CellOpenVoltage"]

                # We will count until we have counted 3 times the number of packs reported by the BMS
                if cell_count < 492:
                    cell_count = cell_count + 1
            except:
                print("Failed to save decoded_msg values into the dataCELLS dictionary. This can happen if the a corrupt CANBUS message is received and treated like a CELL message.")

        # This section will check if the CAN message came from the BMS.
        elif (msg.arbitration_id - 0x6B0 >= 0):
            decoded_msg = dbBMS.decode_message(msg.arbitration_id, msg.data)

            for k in decoded_msg.keys():
                if k in allowed_keys_BMS:
                    dataBMS[k] = decoded_msg[k]

        # This section will check if the CAN message came from the RMS.
        elif msg.arbitration_id - 0x0A0 >= 0:
            decoded_msg = dbRMS.decode_message(msg.arbitration_id, msg.data)

            for k in decoded_msg.keys():
                if k in allowed_keys_RMS:
                    dataRMS[k] = decoded_msg[k]

        # We didn't get a canbus message that matched any of our CAN databases so throw it out
        else:
            return


def write_data(system, dataInput):
    # If every value in data is None, meaning we have nothing to write, then skip writing to DB.
    if all_equal(dataInput, None):
        print("All_equal was True")
        return

    # Start the line with RMS when we are writing RMS data to the database
    if system == "RMS":
        line = "RMS"
        if verbose:
            print("RMS Writing")
    # Start the line with BMS when we are writing BMS data to the database
    elif system == "BMS":
        line = "BMS"
        if verbose:
            print("BMS Writing")

    # Must have a space after the message NAME to tell the query that you are entering fields
    sep = " "

    #/******************** Create lines and write to the database **************************/#

    # Write CELL data to the database
    if system == "CELLS":
        line = ""
        # TODO Better empty dictionary detection
        if dataInput[1]["CellVoltage"] == -500:
            print("EMPTY CELLS")
            return

        if verbose:
            print("CELLS Writing")

        for k, v in dataInput.items():
            newline = 1
            line = line + "CELL" + str(k)
            for j in v.items():
                # Check the value of the j tuple
                if j != None:
                    toAdd = (sep + str(j[0]) + "=" + str(j[1]))
                if newline != 5:
                    sep = ","
                else:
                    sep = " "
                newline = newline + 1
                line = (line + toAdd)
            line = line + "\n"
        line = [line]

        # This function sends the "line" variable to be written to the database
        clientCELLS.write_points(points=line, time_precision="ms", protocol="line")

    else:
        for k, v in dataInput.items():
            if v != None:
                if type(v) == str:
                    toAdd = (sep + str(k) + "=\"" + str(v) + "\"")
                else:
                    toAdd = (sep + str(k) + "=" + str(v))
                sep = ","
                line = (line + toAdd)
        line = [line]

        # This function sends the "line" variable to be written to the database
        client.write_points(points=line, time_precision="ms", protocol="line")


try:
    while True:
        get_data()

        if ((get_time() - prev_time) > 500):
            prev_time = get_time()

            write_data("RMS", dataRMS)

            write_data("BMS", dataBMS)

            if cell_count == 492:
                write_data("CELLS", dataCELLS)

except KeyboardInterrupt:
    os.system("sudo ifconfig can0 down")
    print("\nExiting")
