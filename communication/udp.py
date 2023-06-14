import socket
import select
import json
import threading
import time

class UDP():
    def __init__(self, receive_channel, send_channel):
        self.bind_recv(receive_channel)
        self.bind_send(send_channel)
        
    def bind_recv(self, receive_channel):
        self.receive_channel = receive_channel
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_sock.bind(receive_channel)
        self.recv_sock.setblocking(0)
    
    def bind_send(self, send_channel):
        self.send_channel = send_channel
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8388608)
        self.send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8388608)

    def send(self, msg_serialized):
        print(f"Sending to {self.send_channel}:\n'{msg_serialized}'")
        self.send_sock.sendto(msg_serialized, self.send_channel)

    def recv(self): # Not in use
        try:
            recv_data, address = self.recv_sock.recvfrom(4096)
            return json.loads(recv_data) # return dict
        except BlockingIOError as e:
            print("Socket error: {}".format(e))
    
    def recv_select(self): # returns a list of a new messages [msg_0, msg_1, ...]
        '''
        NOTE: non-blocking receive
        '''
        msg_serialized_list = []
        new_data_available = True
        while new_data_available:
            readable, writable, exceptional = select.select([self.recv_sock], [], [self.recv_sock], 0)
            if len(readable) == 0:
                new_data_available = False
            for s in readable:
                if s is self.recv_sock:
                    msg_serialized_data, address = s.recvfrom(4*1024)
                    # if isinstance(msg_serialized_data, bytes):
                    #     msg_serialized_data = msg_serialized_data.decode() # recvfrom returnes bytes in python3. json.loads() receives str.
                    msg_serialized_list.append(msg_serialized_data)
        
        return msg_serialized_list # return dict
    
    @staticmethod
    def serialize(msg):
        return str.encode(json.dumps(msg))

    @staticmethod
    def deserialize(msg_serialized):
        return json.loads(msg_serialized)
    
if __name__=='__main__':
    
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
