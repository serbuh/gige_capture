import threading
import time
import ctypes

from ICD import cu_mrg
from communication.udp import UDP

class MessagesHandler():
    def __init__(self, logger):
        self.logger = logger
        self.logger.info("Init Messages Handler")

if __name__ == "__main__":

    send = False
    receive = True

    # Create reply
    def create_reply(isOk, errorCode=0):
        header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
        result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
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


    def parse_msg(msg_buffer, structure_type: ctypes.Structure):
        expected_buffer_len = ctypes.sizeof(structure_type)
        if len(msg_buffer) != expected_buffer_len:
            print(f"len(msg_buffer) = {len(msg_buffer)} != {expected_buffer_len} = expected_buffer_len")

        msg = structure_type.from_buffer_copy(msg_buffer)
        return msg





    receive_channel_ip = "192.168.132.212"
    receive_channel_port = 5100
    send_channel_ip = "192.168.132.60"
    send_channel_port = 5101
    UDP_conn = UDP(receive_channel=(receive_channel_ip, receive_channel_port), send_channel=(send_channel_ip, send_channel_port)) # UDP connection object

    def send_loop():
        for i in range(2):
            status_msg = create_status()
            print(f"Sending status (frame_id {status_msg.cvStatus.camera2Status.frameId})")
            
            # Encode status
            status_msg_buffer = ctypes.create_string_buffer(ctypes.sizeof(status_msg))
            ctypes.memmove(status_msg_buffer, ctypes.addressof(status_msg), ctypes.sizeof(status_msg))
            msg_serialized = status_msg_buffer.raw

            UDP_conn.send(msg_serialized)
            time.sleep(0.5)

    def receiver_loop():
        while True:
            msg_serialized_list = UDP_conn.recv_select()
            #print(f"listening {i}: {msg_serialized_list}")
            for msg_serialized in msg_serialized_list:
                print(f"Got {msg_serialized}")

                # # Decode
                header_len = ctypes.sizeof(cu_mrg.headerStruct)
                header = cu_mrg.headerStruct.from_buffer_copy(msg_serialized[:header_len])
                print(header.opCode)

                if header.opCode == cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage:
                    msg = parse_msg(msg_serialized, cu_mrg.CvStatusMessage)
                    print(f"Received frame_id {msg.cvStatus.camera2Status.frameId}")
                elif header.opCode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage:
                    msg = parse_msg(msg_serialized, cu_mrg.SetCvParamsCmdMessage)
                    
                    # Create ack
                    params_result_msg = create_reply(isOk=True)
                    
                    # Encode ack
                    params_result_buffer = ctypes.create_string_buffer(ctypes.sizeof(params_result_msg))
                    ctypes.memmove(params_result_buffer, ctypes.addressof(params_result_msg), ctypes.sizeof(params_result_msg))
                    msg_serialized = params_result_buffer.raw
                    
                    # Send Ack
                    UDP_conn.send(msg_serialized)
                    
                else:
                    print(f"opCode {header.opCode} unknown")

            time.sleep(0.5)
            
    if send:
        send_thread = threading.Thread(target=send_loop)
        send_thread.start()

    if receive:
        receive_thread = threading.Thread(target=receiver_loop)
        receive_thread.start()