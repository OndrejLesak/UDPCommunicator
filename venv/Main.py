import socket
import struct
import math
import os
import time
import threading
import random
from zlib import crc32

keepAlive = True # keep-alive semafor
kat = None # actual keep-alive thread

# ############## CLIENT SECTION ##############
class Sender():
    client_socket = None

    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            opt = input('Type: (1) Request connection; (2) Exit application: ')

            if opt == '1':
                server_ip = input('Enter server ip: ')
                server_port = int(input('Enter server port: '))

                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(createHeader(1), (server_ip, server_port))
                    data = self.client_socket.recv(1500)
                    data = unpackHeader(data)
                    if data[0] == 17:
                        print('Connection established successfully.')
                        self.client_socket.settimeout(None)
                        while True:
                            keepAlive_thread(self.client_socket, (server_ip, server_port), 7) # initialize keep-alive thread

                            msg_type = input('Type of message: (t) Text message; (f) File; (e) To exit application: ')
                            if msg_type == 'e':
                                killThread()
                                break
                            else:
                                self.sendMessage((server_ip, server_port), msg_type)

                except socket.timeout:
                    print('Connection could not be established.')
                    continue

            elif opt == '2':
                return


    def sendMessage(self, to_whom, msg_type):
        number_of_fragments = 0
        frag_id = 1
        msgLength = 0
        msg = ''

        fragment_size = int(input('Enter fragment size (Bytes): '))

        while fragment_size > 1463 or fragment_size <= 0:
            print('The size of fragment should be between 1B and 1463B')
            fragment_size = int(input('Enter fragment size (Bytes): '))

        # init message
        if msg_type == 't':
            msg = input('Content: ')
            msg = msg.encode('utf-8')
            msgLength = len(msg)
            killThread()

            # SEND INITIALIZATION PACKET
            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(createHeader(5), to_whom) # text message initialization packet (INIT, TEXT)
                    data = self.client_socket.recv(1500) # expects 16 (ACK)
                    data = unpackHeader(data)
                    if data[0] == 16:
                        self.client_socket.settimeout(None)
                        break
                    else:
                        continue
                except socket.timeout:
                    print('Timed out')
                    return

        elif msg_type == 'f':
            while True:
                file_path = input('Enter absolute file path: ')

                try:
                    file = open(file_path, 'rb')
                    msg = file.read()
                    break
                except FileNotFoundError:
                    print('File does not exist, try again')
                    continue

            msgLength = len(msg)
            killThread()

            # zeroth packet with file name
            zeroMsg = file_path[file_path.rfind('\\')+1:]
            zeroMsg = zeroMsg.encode()
            zeroCrc = crc32(zeroMsg)
            zeroLength = len(zeroMsg)
            zeroHeader = createHeader(9, zeroLength, 0, zeroCrc)

            # SEND INITIALIZATION PACKET WITH THE FILE NAME
            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(zeroHeader + zeroMsg, to_whom)
                    data = self.client_socket.recv(1500)
                    data = unpackHeader(data)
                    if data[0] == 16:
                        self.client_socket.settimeout(None)
                        break
                    else:
                        continue
                except socket.timeout:
                    print('Timed out')
                    return

        number_of_fragments = math.ceil(msgLength / fragment_size) # get all the fragments

        print(f'{number_of_fragments} will be send.')
        err = int(input('Enter how many errors do you expect: '))

        while True:
            message = msg[:fragment_size]
            msgLength = len(message)
            crc = crc32(message)

            if frag_id == number_of_fragments:
                if msg_type == 't':
                    header = createHeader(68, msgLength, frag_id, crc) # LAST TEXT PACKET
                elif msg_type == 'f':
                    header = createHeader(72, msgLength, frag_id, crc) # LAST FILE PACKET
            else:
                if msg_type == 't':
                    header = createHeader(4, msgLength, frag_id, crc) # TEXT PACKET
                elif msg_type == 'f':
                    header = createHeader(8, msgLength, frag_id, crc) # FILE PACKET

            if err > 0: # error simulation
                if random.random() < 0.5:
                    message = self.createError(message)
                    err -= 1

            while True:
                try:
                    self.client_socket.settimeout(10)
                    self.client_socket.sendto(header + message, to_whom)
                    response = self.client_socket.recv(1500)
                    response = unpackHeader(response)
                    if response[0] == 32: # NACK
                        print('Error while sending packet')
                        break
                    elif response[0] == 16: # ACK
                        frag_id += 1
                        msg = msg[fragment_size:]
                        break
                    elif response[0] == 80: # FIN ACK
                        print('Message sent successfully')
                        return

                except socket.timeout:
                    print('Message not sent')
                    continue


    def createError(self, message):
        i = random.randint(1, len(message)-1)
        if message[i] >= 255:
            message = message.replace(message[i-1:i], (int.from_bytes(message[i-1:i], byteorder='big')-1).to_bytes(1, byteorder='big'), 1)
        else:
            message = message.replace(message[i-1:i], (int.from_bytes(message[i-1:i], byteorder='big')+1).to_bytes(1, byteorder='big'), 1)
        return message


def keep_alive(clientSocket, server_addr, period):
    while True:
        try:
            if keepAlive != True:
                break

            clientSocket.settimeout(10)
            clientSocket.sendto(createHeader(2), server_addr)
            response = clientSocket.recv(1500)
            response = unpackHeader(response)
            if response[0] != 18:
                print('Session got terminated')
                break

            time.sleep(period)
        except socket.timeout:
            print('Connection terminated')
            break


def keepAlive_thread(clientSocket, server_addr, period):
    global keepAlive, kat
    keepAlive = True

    newThread = threading.Thread(target=keep_alive, args=(clientSocket, server_addr, period))
    newThread.daemon = True
    newThread.start()

    kat = newThread


# method to terminate the keep-alive thread
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
            opt = input('Type: (1) Wait for the connection; (2) Exit application: ')

            try:
                if opt == '1':
                    self.server_socket.settimeout(None)
                    data, addr = self.server_socket.recvfrom(1500)
                    data = unpackHeader(data)
                    if data[0] == 1:
                        print(f'Connection requested from {addr[0]}:{addr[1]}')
                        self.server_socket.sendto(createHeader(17), addr)
                        self.receiveMessage(addr)

                elif opt == '2':
                    return

            except (KeyboardInterrupt, socket.timeout):
                print('Interrupted')
                return

    def receiveMessage(self, addr):
        while True:
            self.server_socket.settimeout(10)
            try:
                data = None
                pcktType = None

                while True:
                    data = self.server_socket.recv(1500)
                    pcktType = unpackHeader(data)
                    if  pcktType[0] == 2:
                        print('I\'m still alive!')
                        self.server_socket.sendto(createHeader(18), addr)
                        continue
                    else:
                        break

                if pcktType[0] == 5:
                    self.server_socket.sendto(createHeader(16), addr)
                    self.processMessage('t', data)
                    continue
                elif pcktType[0] == 9: # check crc
                    self.server_socket.sendto(createHeader(16), addr)
                    self.processMessage('f', data)
                    continue

            except socket.timeout:
                print('Idle for too long...\nClosing session.')
                self.server_socket.settimeout(None)
                return


    def processMessage(self, type, header_data):
        full_message = []
        file_name = ''
        last_packetId = 0
        total_packets = 0
        accepted_packets = 0
        total_bytes = 0

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
                total_packets += 1
                print(f'Packet {flag_id} rejected')
                self.server_socket.sendto(createHeader(32), addr)
                continue
            else:
                total_packets += 1
                accepted_packets += 1
                total_bytes += length
                print(f'Packet {flag_id} accepted')

                if type == 't':
                    full_message.append(msg.decode('utf-8'))
                elif type == 'f':
                    full_message.append(msg)

                if flag == 4 or flag == 8:
                    self.server_socket.sendto(createHeader(16), addr)
                elif flag > 64:
                    self.server_socket.sendto(createHeader(80), addr)
                    print('Message received successfully')
                    break

        if type == 't':
            print('Message: ', ''.join(full_message))

        elif type == 'f':
            transFile = open(file_name, 'wb')

            for part in full_message:
                transFile.write(part)
            transFile.close()

            file_size = os.path.getsize(file_name)/1024**2
            file_path = os.path.abspath(file_name)
            print(f'File {file_name} with size of {file_size:.2f} MB was saved at {file_path}')

        print(f'Total received packets: {total_packets}')
        print(f'Accepted out of total: {accepted_packets}/{total_packets}')
        print(f'Total size of accepted packets {(total_bytes / 1024 ** 2):.2f} MB')


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