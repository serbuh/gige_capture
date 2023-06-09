import threading
import time
import ctypes
import logging


from ICD import cu_mrg
from communication.udp_imp import UDP
from ICD import cv_structs

class Communicator():
    def __init__(self, logger, print_messages, receive_channel, send_channel, send_from_port, handle_ctypes_msg_callback):
        self.logger = logger
        self.print_messages = print_messages
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
        self.UDP_conn = UDP(receive_channel, send_channel, send_from_port=send_from_port)

        self.keep_receiving = True
        self.received_msg_queue = None
        self.receive_thread = None

    def __is_valid_channel__(self, channel):
        return isinstance(channel, tuple) and len(channel) == 2 and isinstance(channel[0], str) and isinstance(channel[1], int)

    def start_receiver_thread(self):
        self.logger.info("Starting receiving thread")
        self.receive_thread = threading.Thread(target=self.receive_loop)
        self.receive_thread.start()
    
    def stop_receiver_thread(self):
        self.keep_receiving = False
        self.receive_thread.join()
    
    def set_receive_queue(self, queue):
        self.received_msg_queue = queue
    
    def send_ctypes_msg(self, ctypes_msg, sender_address=None):
        # Serialize ctypes
        if self.print_messages:
            self.logger.debug(f"Sending:\n{ctypes_msg}")
        msg_serialized = self.serialize_ctypes(ctypes_msg)
        self.UDP_conn.send(msg_serialized, sender_address) # Send status/reply

    def receive_loop(self):
        '''
        receive commands and put them to Q
        '''
        try:
            while self.keep_receiving:
                msg_serialized_with_addr_list = self.UDP_conn.recv_select()
                for (msg_serialized, sender_address) in msg_serialized_with_addr_list:
                    msg = self.deserialize_to_ctypes(msg_serialized) # Try to deserialize
                    self.handle_ctypes_msg_callback(msg, sender_address)

                time.sleep(0.01)
        except KeyboardInterrupt:
            self.logger.info("Interrupted by Ctrl+C (in Client)")
            exit()

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
            msg_type = cv_structs.vision_status_msg
        elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage:
            msg_type = cv_structs.client_set_params_msg
        elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsAckMessage:
            msg_type = cv_structs.vision_set_params_ack_msg
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
        logger.info(f"Got {msg}")

    receive_channel = ("127.0.0.1", 5101)
    send_channel = ("127.0.0.1", 5101)
    send_from_port = None
    
    communicator = Communicator(logger, receive_channel, send_channel, send_from_port, handle_ctypes_msg_callback)
    communicator.start_receiver_thread() # Start receiver loop
    
    # Simulate sending
    def simulate_status_loop():
        for frame_number in range(2):
            active_camera = cv_structs.activateCameraSensors.camera1
            status_msg = cv_structs.create_status(frame_number, fps=25, bitrateKBs=10, calibration=False, addOverlay=False)
            communicator.send_ctypes_msg(status_msg)
            time.sleep(2.5)
            
    if simulate_send_loop:
        send_thread = threading.Thread(target=simulate_status_loop)
        send_thread.start()
