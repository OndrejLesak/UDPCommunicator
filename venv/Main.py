import socket
import struct
import math
import os
from zlib import crc32


client_socket = None
server_socket = None


# ############## CLIENT SECTION ##############
class Sender():
    client_socket = None

    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            opt = input('Type: (1) Request connection; (2) Switch application: ')

            if opt == '1':
                server_ip = input('Enter server ip: ')
                server_port = int(input('Enter server port: '))

                self.client_socket.sendto('1'.encode(), (server_ip, server_port))
                self.client_socket.settimeout(10)
                try:
                    data = self.client_socket.recv(1500)
                    if data.decode()[0] == '1':
                        print('Connection established successfully.')
                        self.sendMessage((server_ip, server_port))

                except socket.timeout:
                    print('Connection could not be established.')
                    continue

            elif opt == '2':
                return


    def sendMessage(self, to_whom):
        msg_type = input('Type of message: (t) Text message; (f) File: ')
        fragment_size = int(input('Enter fragment size (Bytes): '))
        frag_id = 1
        msgLength = 0
        msg = None

        while fragment_size > 1463:
            print('Maximum size of fragment is 1463 B')
            fragment_size = int(input('Enter fragment size (Bytes): '))

        # init message
        if msg_type == 't':
            msg = input('Content: ')
            msgLength = len(msg)

        elif msg_type == 'f':
            file_path = input('Enter absolute file path: ')
            file = open(file_path, 'rb')
            msgLength = os.path.getsize(file_path)
            msg = file.read()

        while True:
            message = msg[:fragment_size]
            message = message.encode()
            crc = crc32(message)

            if frag_id == number_of_fragments:
                header = struct.pack('cHHI', '8'.encode(), msgLength, frag_id, crc)
            else:
                if msg_type == 't':
                    header = struct.pack('cHHI', '3'.encode(), msgLength, frag_id, crc)
                elif msg_type == 'f':
                    header = struct.pack('cHHI', '4'.encode(), msgLength, frag_id, crc)

            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(header + message, to_whom)
                    repsonse = self.client_socket.recv(1500)
                    response = response.decode()[0]
                    if response == '6':
                        print('Error while sending packet')
                        continue
                    elif response == '5':
                        frag_id += 1
                        msg = msg[fragment_size:]
                        message = msg
                        break
                    elif response == '7':
                        print('Message sent successfully')
                        return

                except socket.timeout:
                    print('Message not sent')
                    continue

            number_of_fragments = 0
            frag_id = 1

            if msgLength > fragment_size:
                number_of_fragments = math.ceil(msgLength / fragment_size)

            elif msg_type == 'f':
                path = input('Enter absolute file\'s path: ')






# ############## SERVER SECTION ##############
class Receiver():
    server_socket = None

    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server_port = int(input('Input server port number: '))
        self.server_socket.bind(('', server_port))

        while True:
            opt = input('Type: (1) Wait for the connection; (2) Switch application: ')

            if opt == '1':
                data, addr = self.server_socket.recvfrom(1500)
                print(data.decode())
                if data.decode()[0] == '1':
                    print(f'Connection requested from {addr[0]}:{addr[1]}')
                    self.server_socket.sendto('1'.encode(), addr)
                    self.receiveMessage(addr)

            elif opt == '2':
                return


    def receiveMessage(self, addr):
        while True:
            self.server_socket.settimeout(20)
            try:
                data = None

                while True:
                    data = self.server_socket.recv(1500)
                    if data.decode()[0] == '2':
                        print('I\'m still alive!')
                        self.server_socket.sendto('2'.encode(), addr)
                        data = ''
                        break
                    else:
                        break

                pcktType = data.decode()[0]
                if pcktType == '3':
                    break
                elif pcktType == '4':
                    break

            except socket.timeout:
                print('Idle for too long...\nClosing session.')
                self.server_socket.settimeout(None)
                return


def menu():
    print(
        '1 - Sender application',
        '2 - Receiver application',
        'q - Exit application',
    sep='\n')


def main():

    try:
        while True:
            menu()
            app = input('Choose an application from the menu: ')

            if app == '1':
                Sender()
            elif app == '2':
                Receiver()
            elif app == 'q':
                exit(0)


    except KeyboardInterrupt:
        print('The application has been unexpectedly interrupted.')
        exit(-1)


if __name__ == '__main__':
    main()