import socket
import struct
import math
import os
import time
import threading
from zlib import crc32

keepAlive = True
kat = None

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

                self.client_socket.sendto(createHeader(1), (server_ip, server_port))
                self.client_socket.settimeout(10)
                try:
                    data = self.client_socket.recv(1500)
                    data = unpackHeader(data)
                    if data[0] == 1:
                        print('Connection established successfully.')
                        self.client_socket.settimeout(None)
                        keepAlive_thread(self.client_socket, (server_ip, server_port), 15)
                        self.sendMessage((server_ip, server_port))

                except socket.timeout:
                    print('Connection could not be established.')
                    continue

            elif opt == '2':
                return


    def sendMessage(self, to_whom):
        global keepAlive, kat

        number_of_fragments = 0
        frag_id = 1
        msgLength = 0
        msg = ''

        msg_type = input('Type of message: (t) Text message; (f) File: ')
        fragment_size = int(input('Enter fragment size (Bytes): '))

        while fragment_size > 1463:
            print('Maximum size of fragment is 1463 B')
            fragment_size = int(input('Enter fragment size (Bytes): '))

        # init message
        if msg_type == 't':
            msg = input('Content: ')
            msg = msg.encode('utf-8')
            msgLength = msgLength
            killThread()
            while True:
                self.client_socket.sendto(createHeader(3), to_whom)
                data = self.client_socket.recv(1500)
                data = unpackHeader(data)
                if data[0] == 3:
                    break
                else:
                    continue

        elif msg_type == 'f':
            file_path = input('Enter absolute file path: ')
            file = open(file_path, 'rb')
            msg = file.read()
            msgLength = len(msg)
            killThread()

            # zeroth packet with file name
            zeroMsg = file_path[file_path.rfind('\\')+1:]
            zeroMsg = zeroMsg.encode()
            zeroCrc = crc32(zeroMsg)
            zeroLength = len(zeroMsg)
            zeroHeader = createHeader(4, zeroLength, 0, zeroCrc)

            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(zeroHeader + zeroMsg, to_whom)
                    data = self.client_socket.recv(1500)
                    data = unpackHeader(data)
                    if data[0] == 5:
                        self.client_socket.settimeout(None)
                        break
                    else:
                        continue
                except socket.timeout:
                    print('Timed out')
                    continue

        number_of_fragments = math.ceil(msgLength / fragment_size) # count fragments

        while True:
            message = msg[:fragment_size]
            msgLength = len(message)
            crc = crc32(message)

            if frag_id == number_of_fragments:
                if msg_type == 't':
                    header = createHeader(11, msgLength, frag_id, crc) # LAST TEXT PACKET
                elif msg_type == 'f':
                    header = createHeader(12, msgLength, frag_id, crc) # LAST FILE PACKET
            else:
                if msg_type == 't':
                    header = createHeader(3, msgLength, frag_id, crc) # TEXT PACKET
                elif msg_type == 'f':
                    header = createHeader(4, msgLength, frag_id, crc) # FILE PACKET

            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(header + message, to_whom)
                    response = self.client_socket.recv(1500)
                    response = unpackHeader(response)
                    if response[0] == 6:
                        print('Error while sending packet')
                        continue
                    elif response[0] == 5:
                        frag_id += 1
                        msg = msg[fragment_size:]
                        break
                    elif response[0] == 7:
                        print('Message sent successfully')
                        return

                except socket.timeout:
                    print('Message not sent')
                    continue


def keep_alive(clientSocket, server_addr, period):
    while True:
        if keepAlive != True:
            break

        clientSocket.sendto(createHeader(2), server_addr)
        response = clientSocket.recv(1500)
        response = unpackHeader(response)
        if response[0] != 2:
            print('Session got terminated')

        time.sleep(period)


def keepAlive_thread(clientSocket, server_addr, period):
    global keepAlive, kat
    keepAlive = True

    newThread = threading.Thread(target=keep_alive, args=(clientSocket, server_addr, period))
    newThread.daemon = True
    newThread.start()

    kat = newThread


def killThread():
    global kat, keepAlive
    keepAlive = False
    kat.join()


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
                data = unpackHeader(data)
                if data[0] == 1:
                    print(f'Connection requested from {addr[0]}:{addr[1]}')
                    self.server_socket.sendto(createHeader(1), addr)
                    self.receiveMessage(addr)

            elif opt == '2':
                return


    def receiveMessage(self, addr):
        while True:
            self.server_socket.settimeout(20)
            try:
                data = None
                pcktType = None

                while True:
                    data = self.server_socket.recv(1500)
                    pcktType = unpackHeader(data)
                    if  pcktType[0] == 2:
                        print('I\'m still alive!')
                        self.server_socket.sendto(createHeader(2), addr)
                        continue
                    else:
                        break

                if pcktType[0] == 3:
                    self.server_socket.sendto(createHeader(3), addr)
                    self.processMessage('t', data)
                    return
                elif pcktType[0] == 4:
                    self.server_socket.sendto(createHeader(5), addr)
                    self.processMessage('f', data)
                    return

            except socket.timeout:
                print('Idle for too long...\nClosing session.')
                self.server_socket.settimeout(None)
                return


    def processMessage(self, type, header_data):
        full_message = []
        file_name = ''
        last_packetId = 0

        if type == 'f':
            header = unpackHeader(header_data)
            if header[2] == 0:
                file_name = header_data[9:]
                file_name = file_name.decode()
                print(file_name)

        while True:
            data, addr = self.server_socket.recvfrom(1500)
            flag, length, flag_id, crc = unpackHeader(data)
            msg = data[9:]

            this_crc = crc32(msg)

            if crc != this_crc:
                print(f'Packet {flag_id} rejected')
                self.server_socket.sendto(createHeader(6), addr)
                continue
            else:
                print(f'Packet {flag_id} accepted')

                if type == 't':
                    full_message.append(msg.decode('utf-8'))
                elif type == 'f':
                    full_message.append(msg)

                if flag == 3 or flag == 4:
                    self.server_socket.sendto(createHeader(5), addr)
                elif flag > 10:
                    self.server_socket.sendto(createHeader(7), addr)
                    print('Message received successfully')
                    break

        if type == 't':
            print('Message: ', ''.join(full_message))

        elif type == 'f':
            transFile = open(file_name, 'wb')

            for part in full_message:
                transFile.write(part)
            transFile.close()

            file_size = os.path.getsize(file_name)
            file_path = os.path.abspath(file_name)
            print(f'File {file_name} with size of {file_size} B was saved at {file_path}')



def createHeader(flag, length=0, fragId=0, crc=0):
    header = struct.pack('B', flag) + struct.pack('HH', length, fragId) + struct.pack('I', crc)
    return header


def unpackHeader(header):
    data1 = struct.unpack('B', header[:1])[0]
    data2, data3 = struct.unpack('HH', header[1:5])
    data4 = struct.unpack('I', header[5:9])[0]

    return data1, data2, data3, data4


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