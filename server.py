'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import threading
import queue





class Server:
    '''
    This is the main Server Class. You will have to write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.window = window
        self.q = queue.Queue()
        self.comms_completed = False
    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
        clients_dictionary = {}
        new_msg = ""
        
        def acker():
            ack_packet = util.make_packet("ack",seq_no, )
            self.sock.sendto(ack_packet.encode('utf-8'),address)
        
        while True:
            message, address = self.sock.recvfrom(4096)
            decodedPacket = message.decode("utf-8")
            msg_type,seq_no, msg,checksum = util.parse_packet(decodedPacket)
            
            
            seq_no = int(seq_no)
                
            if msg_type == 'start':
                try:
                    seq_no +=1
                    # print('start of a new thread',seq_no)
                    acker()
                    T = threading.Thread(target=Server.receive_handler,args=(self,new_msg,address,seq_no,checksum,clients_dictionary),)
                    T.daemon = True
                    T.start()
                except (KeyboardInterrupt, SystemExit):
                    sys.exit()
            elif msg_type == 'data': # start data end
                new_msg += msg
                # print(new_msg)
                acker()
                
            else:
                # print('this many timesz',seq_no)
                seq_no +=1
                acker()
                temp_tuple = (msg_type,seq_no,new_msg,checksum)
                self.q.put(temp_tuple)
                new_msg = ""

    def join_handler(self,msg_list,address,clients_dictionary,client_counter,seq_no):
        is_present = False

        for key in clients_dictionary:
            if key == msg_list[2]:
                is_present = True
        if is_present:
            print('disconnected: username not available')
            catch_message = util.make_message(
                'err_username_unavailable', 2)
            seq_no = self.comms_handler(catch_message,address,seq_no)
            return seq_no
        elif client_counter == util.MAX_NUM_CLIENTS:
            print('disconnected: server full')
            catch_message = util.make_message('err_server_full', 2)
            seq_no = self.comms_handler(catch_message,address,seq_no)
            return seq_no
        else:
            # client_counter = client_counter + 1
            decoded_name = msg_list[2]
            print("join:", decoded_name)
            clients_dictionary[decoded_name] = address[1]
            return seq_no

    def list_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no):
        string_list = []
        string_list.append(len(clients_dictionary))
        for key in clients_dictionary:
            string_list.append(key)
        list_to_str = ' '.join(str(key) for key in string_list)
        list_to_str = str(client_counter) + ' ' + list_to_str
        catch_message = util.make_message(
            'response_users_list', 3, list_to_str)
        print("request_users_list:", port_name)
        seq_no = self.comms_handler(catch_message,address,seq_no)
        return seq_no

    def disconnect_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no):
        clients_dictionary.pop(port_name)
        print("disconnected:", port_name)

    def send_message_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no):
        size_msg = len(msg_list)
        try:
            num_receivers = int(msg_list[2])
        except:
            print('Incorrect format for number of receivers entered')
            return
        receivers = msg_list[3:num_receivers+3]
        message = msg_list[num_receivers+3:]
        message = ' '.join(message)
        message = port_name + ' ' + message
        if size_msg > 3: 

            print('msg:', port_name)
            for x in receivers:
                if x in clients_dictionary.keys():

                    address_to_send = clients_dictionary[x]
                    catch_message = util.make_message(
                        'forward_message', 4, message)
                    seq_no = self.comms_handler(catch_message,('localhost',address_to_send),seq_no)
                    self.end_comms(('localhost',address_to_send),seq_no)
                    return seq_no

                else:
                    print('msg:', port_name, 'to non-existent user', x)

        else:
            catch_message = util.make_message('err_unknown_message', 2)
            print('disconnected:', port_name, 'sent unknown command')
            seq_no = self.comms_handler(catch_message,address,seq_no)
            return seq_no

    def send_file_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no):
            
            size_file_msg = len(msg_list)
            try:
                num_receivers = int(msg_list[2])
            except:
                print('Incorrect format for number of receivers entered')
                return
            receivers = msg_list[3:num_receivers+3]
            file_name = msg_list[num_receivers+3]
            file_message = msg_list[num_receivers+3+1:]

            file_message = port_name + ' ' + \
                file_name + ' ' + ' '.join(file_message)

            if(size_file_msg > 3):

                print('file:', port_name)
                for x in receivers:

                    if x in clients_dictionary.keys():
                        address_to_send = clients_dictionary[x]
                        catch_message = util.make_message(
                            'forward_file', 4, file_message)
                        seq_no = self.comms_handler(catch_message,('localhost',address_to_send),seq_no)
                        self.end_comms(('localhost',address_to_send),seq_no)
                        return seq_no
                    else:
                        print('file:', port_name, 'to non-existent user', x)
            else:
                catch_message = util.make_message('err_unknown_message', 2)
                seq_no = self.comms_handler(catch_message,address,seq_no)
                return seq_no
    
    def comms_handler(self,catch_message,address,seq_no):
        counter = 0
        chunks = list(self.chunkstring(catch_message,util.CHUNK_SIZE))
        print('comms handler called',chunks)
        while len(chunks) != 0:
            counter +=1
            seq_no = int(seq_no) + counter
            catch_packet = util.make_packet("data",seq_no,msg=chunks[0])
            # print('comms handler recieved ack did its job',catch_packet)
            self.sock.sendto(catch_packet.encode("utf-8"),
                            address)
            chunks.remove(chunks[0])
            # print('chunks are now',chunks)
        # self.comms_completed = True
        return seq_no
    def end_comms(self,address,seq_no):
        seq_no = int(seq_no) + 1
        end_packet = util.make_packet("end",seq_no, )
        self.sock.sendto(end_packet.encode("utf-8"),
                            (address))
        # self.comms_completed = True
        return seq_no    
    def chunkstring(self,string, length):
        return (string[0+i:length+i] for i in range(0, len(string), length))              
      
    def receive_handler(self,msg,address,seq_no,checksum,clients_dictionary):
            
        msg_list = msg.split(' ')
        is_handled = False
        # print('hello this works',seq_no)
        client_counter = len(clients_dictionary)
        # print(msg_list)
        port_name = ''
        msg_type = ''
        
        
        while True:
            if not self.q.empty():
                temp_tuple = self.q.get(timeout=util.TIME_OUT)
                msg_type,seq_no,msg,checksum = temp_tuple
                # print(msg_type,msg)
                print('a msg of type that was not start but was in the queue was received')
                msg_list = msg.split(' ')
            
            if msg_type == 'end' and is_handled: # already ack-ed
                print('destruction of thread')
                break
            
            for (key, value) in clients_dictionary.items():
                if value == address[1]:
                    port_name = key

            if msg_list[0] == "request_users_list":

                seq_no = Server.list_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no)
                is_handled = True
                seq_no = self.end_comms(address,seq_no)

            elif msg_list[0] == "disconnect":
                Server.disconnect_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no)
                is_handled = True
                seq_no = self.end_comms(address,seq_no)

            elif msg_list[0] == "send_message":

                seq_no = Server.send_message_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no)
                is_handled = True
                seq_no = self.end_comms(address,seq_no)

            elif msg_list[0] == 'join':
                seq_no =Server.join_handler(self,msg_list,address,clients_dictionary,client_counter,seq_no)
                is_handled = True
                self.end_comms(address,seq_no)

            elif msg_list[0] == 'send_file':

                seq_no = Server.send_file_handler(self,msg_list,address,clients_dictionary,client_counter,port_name,seq_no)
                is_handled = True
                seq_no = self.end_comms(address,seq_no) 
            
            
            
            
        

# Do not change this part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
        
