import threading
import time
import ctypes
import logging


from ICD import cu_mrg
from ICD import cv_structs
from communication.udp_communicator import Communicator


class MessagesHandler():
    def __init__(self, logger, receive_channel, send_channel, print_received=False):
        self.print_received = print_received
        self.logger = logger
        self.logger.info("Init Messages Handler")
        
        self.communicator = Communicator(self.logger, receive_channel, send_channel, self.parse_command, self.print_received)

    def start_receive(self):
        self.communicator.start_receiver_thread()
    
    def set_receive_queue(self, queue):
        self.communicator.set_receive_queue(queue)
    
    def register_callback(self, name, func):
        self.communicator.register_callback(name, func)

    def destroy_communication(self):
        self.communicator.stop_receiver_thread()
    
    def send_ctypes_report(self, ctypes_msg):
        self.communicator.send_ctypes_msg(ctypes_msg)

    def parse_command(self, msg_serialized):
        header_opcode = self.communicator.get_header_opcode(msg_serialized)
                
        if self.print_received:
            self.logger.debug(f"Got msg with opcode {hex(header_opcode)}:\n{msg_serialized}")

        if header_opcode == cu_mrg.cu_mrg_Opcodes.OPCvStatusMessage: # NOTE: should not get status. We are sending it, not receiving
            msg = self.parse_msg(msg_serialized, cu_mrg.CvStatusMessage)
            #self.logger.debug(f"Received frame_id {msg.cvStatus.camera2Status.frameId}")
        elif header_opcode == cu_mrg.cu_mrg_Opcodes.OPSetCvParamsCmdMessage:
            msg = self.parse_msg(msg_serialized, cu_mrg.SetCvParamsCmdMessage)
            
            # TODO reply from grab.py
            # Create ack
            params_result_msg = cv_structs.create_reply(isOk=True)
            # Send Ack
            self.communicator.send_ctypes_msg(params_result_msg)
            
        else:
            print(f"opCode {header_opcode} unknown")
            return
        
        # Put in Queue (if valid opcode)
        if self.communicator.received_msg_queue is not None:
            self.communicator.received_msg_queue.put_nowait(msg)
    
    def parse_msg(self, msg_buffer, structure_type: ctypes.Structure):
        expected_buffer_len = ctypes.sizeof(structure_type)
        if len(msg_buffer) != expected_buffer_len:
            self.logger.error(f"len(msg_buffer) = {len(msg_buffer)} != {expected_buffer_len} = expected_buffer_len")

        msg = structure_type.from_buffer_copy(msg_buffer)
        return msg
    

if __name__ == "__main__":

    simulate_send_loop = True

    # Set logger
    logger = logging.getLogger("MessageHandler")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(clear_with_time_msec_format)
    logger.addHandler(ch)
    logger.info("Welcome to MessageHandler")

    receive_channel = ("127.0.0.1", 5101)
    send_channel = ("127.0.0.1", 5101)

    messages_handler = MessagesHandler(logger, receive_channel, send_channel, print_received=True)
    messages_handler.start_receive()
    
    # Simulate sending
    def simulate_status_loop():
        for frame_number in range(2):
            status_msg = cv_structs.create_status(frame_number, frame_number+100)
            messages_handler.communicator.send_ctypes_msg(status_msg)
            time.sleep(2.5)
            
    if simulate_send_loop:
        send_thread = threading.Thread(target=simulate_status_loop)
        send_thread.start()
