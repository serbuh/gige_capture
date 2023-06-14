import threading
import time
import ctypes
import logging


from ICD import cu_mrg
from communication.udp import UDP

class MessagesHandler():
    def __init__(self, logger, print_received=False):
        self.logger = logger
        self.print_received = print_received
        self.logger.info("Init Messages Handler")

        # receive_channel_ip = "192.168.132.212"
        # receive_channel_port = 5100
        # send_channel_ip = "192.168.132.60"
        # send_channel_port = 5101
        receive_channel_ip = "127.0.0.1"
        receive_channel_port = 5101
        send_channel_ip = "127.0.0.1"
        send_channel_port = 5101
        self.UDP_conn = UDP(receive_channel=(receive_channel_ip, receive_channel_port), send_channel=(send_channel_ip, send_channel_port)) # UDP connection object

        self.keep_receiving = True
        self.received_msg_queue = None

    def start_receiver_thread(self):
        self.receive_thread = threading.Thread(target=self.receive_loop)
        self.receive_thread.start()
    
    def stop_receiver_thread(self):
        self.keep_receiving = False
        self.receive_thread.join()
    
    def set_receive_queue(self, queue):
        self.received_msg_queue = queue
    
    def send_ctypes_msg(self, ctypes_msg):
        # Serialize ctypes
        msg_serialized = MessagesHandler.serialize_ctypes(ctypes_msg)
        self.UDP_conn.send(msg_serialized) # Send status

    def receive_loop(self):
        '''
        receive commands and put them to Q
        '''
        while self.keep_receiving:
            msg_serialized_list = self.UDP_conn.recv_select()
            for msg_serialized in msg_serialized_list:
                header_opcode = MessagesHandler.get_header_opcode(msg_serialized)
                
                if self.print_received:
                    self.logger.debug(f"Got msg with opcode {hex(header_opcode)}:\n{msg_serialized}")

                if header_opcode == cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage: # NOTE: should not get status. We are sending it, not receiving
                    msg = self.parse_msg(msg_serialized, cu_mrg.CvStatusMessage)
                    #self.logger.debug(f"Received frame_id {msg.cvStatus.camera2Status.frameId}")
                elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage:
                    msg = self.parse_msg(msg_serialized, cu_mrg.SetCvParamsCmdMessage)
                    
                    # TODO reply from grab.py
                    # Create ack
                    params_result_msg = MessagesHandler.create_reply(isOk=True)
                    # Send Ack
                    messages_handler.send_ctypes_msg(params_result_msg)
                    
                else:
                    print(f"opCode {header_opcode} unknown")
                    msg = None
                    continue
                
                # in case of existing opcode put the item in the queue
                if self.received_msg_queue is not None:
                    self.received_msg_queue.put_nowait(msg)

            time.sleep(0.01)

    def register_callback(self, name, func):
        pass
    
    @staticmethod
    def serialize_ctypes(ctypes_struct):
        status_msg_buffer = ctypes.create_string_buffer(ctypes.sizeof(ctypes_struct))
        ctypes.memmove(status_msg_buffer, ctypes.addressof(ctypes_struct), ctypes.sizeof(ctypes_struct))
        return status_msg_buffer.raw
    
    @staticmethod
    def get_header_opcode(msg_serialized):
        # Decode header
        header_len = ctypes.sizeof(cu_mrg.headerStruct)
        header = cu_mrg.headerStruct.from_buffer_copy(msg_serialized[:header_len])
        return header.opCode

    def parse_msg(self, msg_buffer, structure_type: ctypes.Structure):
        expected_buffer_len = ctypes.sizeof(structure_type)
        if len(msg_buffer) != expected_buffer_len:
            self.logger.error(f"len(msg_buffer) = {len(msg_buffer)} != {expected_buffer_len} = expected_buffer_len")

        msg = structure_type.from_buffer_copy(msg_buffer)
        return msg
    
    ### Messages
    def send_status(self, frame_number):
        status_msg = MessagesHandler.create_status(frame_number) # Create ctypes status
        #self.logger.info(f"Sending status (frame_id {status_msg.cvStatus.camera2Status.frameId})")
        self.send_ctypes_msg(status_msg) # Send status

    # Create status
    @staticmethod
    def create_status(frame_number):
        header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage)

        # Cam 1 status
        cam1_status= cu_mrg.cameraControlStruct(frameId=frame_number, cameraOffsetX=2, cameraOffsetY=3, fps=20, bitrateKBs=1000)
        
        # Cam 2 status
        cam2_status= cu_mrg.cameraControlStruct(frameId=frame_number+100, cameraOffsetX=4, cameraOffsetY=5, fps=25, bitrateKBs=1500)

        # Active sensor
        active_sensor = cu_mrg.activateCameraSensors.camera1

        cvStatus = cu_mrg.cvStatusStruct(camera1Status=cam1_status, camera2Status=cam2_status, selectedCameraSensors=active_sensor)
        status_msg = cu_mrg.CvStatusMessage(header=header, cvStatus=cvStatus)
        return status_msg

    # Create params reply
    @staticmethod
    def create_reply(isOk, errorCode=0):
        header = cu_mrg.headerStruct(opCode=cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage)
        result = cu_mrg.setCvParamsResultStruct(isOk=isOk, errorCode=errorCode)
        params_ack_msg = cu_mrg.SetCvParamsAckMessage(header=header, result=result)
        return params_ack_msg
    
    

if __name__ == "__main__":

    simulate_send_loop = True
    enable_receive = True

    # Set logger
    logger = logging.getLogger("MessageHandler")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(clear_with_time_msec_format)
    logger.addHandler(ch)
    logger.info("Welcome to MessageHandler")

    messages_handler = MessagesHandler(logger, print_received=True)
    
    # Start receiver loop
    if enable_receive:
        messages_handler.start_receiver_thread()

    # Simulate sending
    def simulate_status_loop():
        for frame_number in range(2):
            status_msg = MessagesHandler.create_status(frame_number)
            messages_handler.send_ctypes_msg(status_msg)
            time.sleep(2.5)
            
    if simulate_send_loop:
        send_thread = threading.Thread(target=simulate_status_loop)
        send_thread.start()
