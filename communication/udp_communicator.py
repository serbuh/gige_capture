import threading
import time
import ctypes
import logging


from ICD import cu_mrg
from communication.udp import UDP
from ICD import cv_structs

class Communicator():
    def __init__(self, logger, parse_msg_callback, print_received=False):
        self.logger = logger
        self.parse_msg_callback = parse_msg_callback
        self.print_received = print_received
        self.logger.info("Init Communicator")

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
        self.receive_thread = None

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
                
                self.parse_msg_callback(msg_serialized)

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

        
    ### Messages
    def send_status(self, frame_number):
        status_msg = cv_structs.create_status(frame_number, frame_number+100) # Create ctypes status
        #self.logger.info(f"Sending status (frame_id {status_msg.cvStatus.camera2Status.frameId})")
        self.send_ctypes_msg(status_msg) # Send status

    

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

    def parse_msg_callback(item):
        print(f"Got {item}")

    communicator = Communicator(logger, parse_msg_callback, print_received=True)
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
