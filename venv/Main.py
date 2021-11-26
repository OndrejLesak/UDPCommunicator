import socket
from zlib import crc32


client_socket = None
server_socket = None


# ############## CLIENT SECTION ##############
def initClient():
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        pass



def sendMessage(addr, type):
    pass


# ############## SERVER SECTION ##############
def initServer():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_port = int(input('Input server port number: '))
    server_socket.bind(('', server_port))

    while True:
        server_socket.settimeout(None)
        opt = input('Type: (1) Wait for the connection; (2) Switch application: ')

        if opt == '1':
            while True:
                data, addr = server_socket.recvfrom(1500)
                if data == '1':
                    print(f'Connection requested from {addr[0]}:{addr[1]}')
                    server_socket.sendto('1'.encode(), addr)


        elif opt == '2':
            return



def menu():
    print(
        '1 - Client application',
        '2 - Server application',
        'q - Exit application',
    sep='\n')


def main():

    try:
        while True:
            menu()
            app = input('Choose an application from the menu: ')

            if app == '1':
                initClient()
            elif app == '2':
                initServer()
            elif app == 'q':
                exit(0)


    except KeyboardInterrupt:
        print('The application has been unexpectedly interrupted.')
        exit(-1)


if __name__ == '__main__':
    main()