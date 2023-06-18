import threading
import time
import ctypes
import logging


from ICD import cu_mrg
from communication.udp import UDP
from ICD import cv_structs

class Communicator():
    def __init__(self, logger, receive_channel, send_channel, handle_ctypes_msg_callback):
        self.logger = logger
        self.handle_ctypes_msg_callback = handle_ctypes_msg_callback
        self.logger.info("Init Communicator")

        # Check receive channel validity
        if self.__is_valid_channel__(receive_channel):
            self.logger.info(f"Open receive channel: {receive_channel}")
        else:
            raise Exception(f"Invalid receive channel definition: {receive_channel}")
        
        # Check send channel validity
        if self.__is_valid_channel__(send_channel):
            self.logger.info(f"Open send channel: {send_channel}")
        else:
            raise Exception(f"Invalid send channel definition: {send_channel}")
        
        
        # Init udp sockets
        self.UDP_conn = UDP(receive_channel, send_channel)

        self.keep_receiving = True
        self.received_msg_queue = None
        self.receive_thread = None

    def __is_valid_channel__(self, channel):
        return isinstance(channel, tuple) and len(channel) == 2 and isinstance(channel[0], str) and isinstance(channel[1], int)

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
        msg_serialized = self.serialize_ctypes(ctypes_msg)
        self.UDP_conn.send(msg_serialized) # Send status

    def receive_loop(self):
        '''
        receive commands and put them to Q
        '''
        while self.keep_receiving:
            msg_serialized_list = self.UDP_conn.recv_select()
            for msg_serialized in msg_serialized_list:
                msg = self.deserialize_to_ctypes(msg_serialized) # Try to deserialize
                self.handle_ctypes_msg_callback(msg)

            time.sleep(0.01)

    def register_callback(self, name, func):
        self.logger.info(f"TODO: Registering function for callback {name}")
    
    def serialize_ctypes(self, ctypes_struct):
        status_msg_buffer = ctypes.create_string_buffer(ctypes.sizeof(ctypes_struct))
        ctypes.memmove(status_msg_buffer, ctypes.addressof(ctypes_struct), ctypes.sizeof(ctypes_struct))
        return status_msg_buffer.raw
    
    def get_header_opcode(self, msg_serialized):
        # Decode header
        header_len = ctypes.sizeof(cu_mrg.headerStruct)
        header = cu_mrg.headerStruct.from_buffer_copy(msg_serialized[:header_len])
        return header.opCode
    
    def deserialize_to_ctypes(self, msg_serialized):
        header_opcode = self.get_header_opcode(msg_serialized)
        
        if False:
            self.logger.debug(f"Got msg with opcode {hex(header_opcode)}:\n{msg_serialized}")

        # Get msg_type
        if header_opcode == cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage:
            msg_type = cu_mrg.CvStatusMessage
        elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage:
            msg_type = cu_mrg.SetCvParamsCmdMessage
        elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage:
            msg_type = cu_mrg.SetCvParamsAckMessage
        else:
            self.logger.error(f"opCode {header_opcode} unknown")
            return None

        msg = self.deserialize_to_known_type(msg_serialized, msg_type)

        return msg

    def deserialize_to_known_type(self, msg_buffer, structure_type: ctypes.Structure):
        expected_buffer_len = ctypes.sizeof(structure_type)
        if len(msg_buffer) != expected_buffer_len:
            self.logger.error(f"len(msg_buffer) = {len(msg_buffer)} != {expected_buffer_len} = expected_buffer_len")

        msg = structure_type.from_buffer_copy(msg_buffer)
        return msg

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

    def handle_ctypes_msg_callback(msg):
        print(f"Got {msg}")

    receive_channel = ("127.0.0.1", 5101)
    send_channel = ("127.0.0.1", 5101)

    communicator = Communicator(logger, receive_channel, send_channel, handle_ctypes_msg_callback)
    communicator.start_receiver_thread() # Start receiver loop
    
    # Simulate sending
    def simulate_status_loop():
        for frame_number in range(2):
            status_msg = cv_structs.create_status(frame_number, frame_number+100)
            communicator.send_ctypes_msg(status_msg)
            time.sleep(2.5)
            
    if simulate_send_loop:
        send_thread = threading.Thread(target=simulate_status_loop)
        send_thread.start()
