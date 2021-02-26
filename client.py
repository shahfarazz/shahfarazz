'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util
import queue
from random import randrange


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.window = window_size
        self.comms_completed = False
        self.q = queue.Queue()
        # self.
        self.seq_no = randrange(10)

    def chunkstring(self,string, length):
        return (string[0+i:length+i] for i in range(0, len(string), length))
    def end_comms(self):
        self.seq_no = int(self.seq_no) + 1
        end_packet = util.make_packet("end",self.seq_no, )
        self.sock.sendto(end_packet.encode("utf-8"),
                            ("localhost", self.server_port))
        self.comms_completed = True
    def start_comms(self):
        self.seq_no = randrange(10)
        start_packet = util.make_packet("start",self.seq_no, )
        self.sock.sendto(start_packet.encode("utf-8"),
                         ("localhost", self.server_port))
        self.comms_completed = False
    def comms_handler(self,catch_message):
        counter = 0
        chunks = list(self.chunkstring(catch_message,util.CHUNK_SIZE))
        # print('comms handler called',chunks)
        while not self.comms_completed and len(chunks) != 0:
            if not self.q.empty():
                is_ack = self.q.get(timeout=util.TIME_OUT)
                if is_ack:
                    
                    counter +=1
                    self.seq_no = int(self.seq_no) + counter
                    catch_packet = util.make_packet("data",self.seq_no,msg=chunks[0])
                    # print('comms handler recieved ack did its job',catch_packet)
                    self.sock.sendto(catch_packet.encode("utf-8"),
                                    (self.server_addr, self.server_port))
                    chunks.remove(chunks[0])
                    print('chunks are now',chunks)
        self.comms_completed = True
            
    def start(self):
        '''
        Main Loop is here
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''
        #SOCK_DGRAM means UDP 
        '''soc = socket.socket( type=socket.SOCK_DGRAM)'''
        self.start_comms()
        # print(is_ack)
        first_run = True
        while not self.comms_completed:
            if not self.q.empty():
                is_ack = self.q.get(timeout=util.TIME_OUT)
                if is_ack and first_run:
                    catch_message = util.make_message('join', 1, self.name)
                    catch_packet = util.make_packet('data',int(self.seq_no)+1,msg=catch_message)
                    self.seq_no = int(self.seq_no) + 1
                    self.sock.sendto(catch_packet.encode("utf-8"),
                                    ("localhost", self.server_port))
                    is_ack = False
                    first_run = False
                    self.comms_completed = True
        if self.comms_completed:
            self.end_comms()
            while True:
                
                # In python3 you can only send bytes over connection, encode and decode inter-convert between bytes and string
                to_send = input()
                split = to_send.split(' ')
                if split[0] == 'list':
                    self.start_comms()
                    catch_message = util.make_message('request_users_list', 2)
                    self.comms_handler(catch_message)
                    self.end_comms()
                elif split[0] == 'msg':
                    catch_message = util.make_message(
                        'send_message', 4, ' '.join(split[1:]))
                    self.start_comms()
                    print(self.comms_completed)
                    self.comms_handler(catch_message)
                    self.end_comms()
                elif split[0] == 'help':
                    print('Your options are the following:')
                    print('\t1) msg <number_of_users> <username1> <username2> … <message>')
                    print('\t2) list')
                    print(
                        '\t3) file <number_of_users> <username1> <username2> … <file_name>')
                    print('\t4) quit')
                elif split[0] == 'quit':
                    print('quitting', end='')
                    catch_message = util.make_message('disconnect', 1, self.name)
                    self.start_comms()
                    print(self.comms_completed)
                    self.comms_handler(catch_message)
                    self.end_comms()
                    return
                elif split[0] == 'file': 
                    try:
                        file_name = split[-1]
                        f = open(file_name)
                        catch_message = util.make_message(
                            'send_file', 4, ' '.join(split[1:]) + ' ' + f.read())
                        self.start_comms()
                        print(self.comms_completed)
                        self.comms_handler(catch_message)
                        self.end_comms()
                    except:
                        print('incorrect userinput format')
                else:
                    print('incorrect userinput format')


    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
        new_msg = ''
        
        while True:
            catch_packet = self.sock.recv(4096).decode("utf-8")
            msg_type,seq_no, msg,checksum = util.parse_packet(catch_packet)
            self.seq_no = seq_no
            
            print(catch_packet)
            
            
            if msg_type == 'ack':
                is_ack = True
                self.q.put(is_ack)
                print('received an ack put it into the client queue')
            elif msg_type == 'data':
                new_msg += msg
                print('new_msg concatenated')
            elif msg_type == 'end':
                msg_list = new_msg.split(' ')
                new_msg = ''
                if msg_list[0] == "response_users_list":
                    my_list = []
                    my_list = msg_list[3:]
                    my_list.sort()
                    str_out = ' '.join(my_list)
                    print('list:', str_out[2:])

                elif msg_list[0] == "disconnect":
                    print('disconnected')
                    self.sock.close()
                    sys.exit()
                    return

                elif msg_list[0] == 'forward_message':
                    print('msg:', msg_list[2] + ':', ' '.join(msg_list[3:]))

                elif msg_list[0] == 'err_username_unavailable':
                    print('disconnected: username not available')
                    self.sock.close()
                    sys.exit()
                    return
                elif msg_list[0] == 'err_server_full':
                    print('disconnected: server full')
                    self.sock.close()
                    sys.exit()
                    return
                elif msg_list[0] == 'err_unknown_message':
                    print('disconnected: server recieved an unknown command')
                    self.sock.close()
                    sys.exit()
                    return
                elif msg_list[0] == 'forward_file':
                    new_file_name = self.name + '_' + msg_list[3]
                    print('file:', msg_list[2] + ':', msg_list[3])
                    f = open(new_file_name, "x")
                    f.write(' '.join(msg_list[4:]))
                    f.close()
                else:
                    if len(new_msg) != 0:
                        print(new_msg)

        # raise NotImplementedError#



# Do not change this part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
