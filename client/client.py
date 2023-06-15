import logging
import time
import threading

from ICD import cu_mrg
from communication.udp import UDP

if __name__=='__main__':
    
    # Set logger
    logger = logging.getLogger("Client Simulator")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    clear_with_time_msec_format = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s', datefmt='%H:%M:%S')
    ch.setFormatter(clear_with_time_msec_format)
    logger.addHandler(ch)
    logger.info("Welcome to Client Simulator")

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
                print(f"Got\n{UDP.deserialize(msg_serialized)}")
            time.sleep(0.5)
            

    send_thread = threading.Thread(target=send_loop)
    send_thread.start()

    receive_thread = threading.Thread(target=receiver_loop)
    receive_thread.start()
