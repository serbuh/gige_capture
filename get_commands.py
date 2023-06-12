import threading
import time
import ctypes

from ICD import cu_mrg
from communication.udp import UDP


# Create reply
def create_reply(isOk, errorCode=0):
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
    result = cu_mrg.setCvParamsResultStruct(isOk=True, errorCode=errorCode)
    params_ack_msg = cu_mrg.SetCvParamsAckMessage(header=header, result=result)
    return params_ack_msg

def create_status():
    header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

    # Cam 1 status
    cam1_status= cu_mrg.cameraControlStruct(frameId=123, cameraOffsetX=2, cameraOffsetY=3, fps=20, bitrateKBs=1000)
    
    # Cam 2 status
    cam2_status= cu_mrg.cameraControlStruct(frameId=456, cameraOffsetX=4, cameraOffsetY=5, fps=25, bitrateKBs=1500)

    # Active sensor
    active_sensor = cu_mrg.activateCameraSensors.camera1

    cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor)
    status_msg = cu_mrg.CvStatusMessage(header=header, cvStatus=cvStatus)
    return status_msg

params_result_msg = create_reply(isOk=True)
status_msg = create_status()

print(f"Sending frame_id {status_msg.cvStatus.camera2Status.frameId}")


# Decode status
status_msg_buffer = ctypes.create_string_buffer(ctypes.sizeof(status_msg))
ctypes.memmove(status_msg_buffer, ctypes.addressof(status_msg), ctypes.sizeof(status_msg))
serialized_buffer = status_msg_buffer.raw

# Encode
status_msg_buf_len = ctypes.sizeof(cu_mrg.CvStatusMessage)
if len(serialized_buffer) != status_msg_buf_len:
    print(f"len(serialized_buffer) = {len(serialized_buffer)} != {status_msg_buf_len} = status_msg_buf_len")

status_msg_received = cu_mrg.CvStatusMessage.from_buffer_copy(serialized_buffer)
print(f"Received frame_id {status_msg_received.cvStatus.camera2Status.frameId}")


# TODO get 
# class SetCvParamsCmdMessage(Structure):                     # (Opcode 0x32) Message 3250
#     _fields_ = [("header", headerStruct),
#                 ("cvParams", setCvParamsCmdStruct)]


receive_channel_ip = "127.0.0.1"
receive_channel_port = 5005
send_channel_ip = "127.0.0.1"
send_channel_port = 5005
UDP_conn = UDP(receive_channel=(receive_channel_ip, receive_channel_port), send_channel=(send_channel_ip, send_channel_port)) # UDP connection object

def send_loop():
    for i in range(10):
        msg_serialized = UDP.serialize(i)
        UDP_conn.send(msg_serialized)
        time.sleep(0.5)

def receiver_loop():
    for i in range(12):
        msg_serialized_list = UDP_conn.recv_select()
        #print(f"listening {i}: {msg_serialized_list}")
        for msg_serialized in msg_serialized_list:
            print(f"Got {UDP.deserialize(msg_serialized)}")
        time.sleep(0.5)
        

send_thread = threading.Thread(target=send_loop)
send_thread.start()

receive_thread = threading.Thread(target=receiver_loop)
receive_thread.start()